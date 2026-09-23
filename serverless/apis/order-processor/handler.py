"""
Order Processor — Lambda triggered by SQS (Order Events).

The asynchronous half of order creation. Consumes order events produced by
the Create Order API, writes the order + line items to RDS, and files a
receipt in S3. On success the order row is marked COMPLETED with its
receipt URL.

    Trigger:  SQS (batch of order events)
    Reads:    each record body = {"order_id","status","customer","items",
                                  "total","idempotency_key","created_at"}
    Writes:   RDS (`orders`, `order_items`) and S3 (receipt object)

Idempotency: `orders.order_id` is the primary key and inserts use
INSERT IGNORE, so an SQS re-delivery does not create a duplicate order.

Partial-batch retry: the handler returns `batchItemFailures` for the
records that raised, so only those are re-driven by SQS (requires
"ReportBatchItemFailures" on the event source mapping).

Credentials mirror the Products API:
    Preferred  -> Secrets Manager secret named by env DB_SECRET_NAME
                  ({"host","port","username","password","dbname"}).
    Fallback   -> env vars DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME.

The DB connection, secret, and S3 client are cached at module scope so warm
invocations reuse them.
"""
import json
import os
from datetime import datetime, timezone

import boto3
import pymysql

# Cached across warm invocations.
_connection = None
_db_config = None
_s3 = None


def _load_db_config():
    """Resolve DB credentials once (Secrets Manager, else env vars)."""
    global _db_config
    if _db_config is not None:
        return _db_config

    secret_name = os.getenv("DB_SECRET_NAME")
    if secret_name:
        client = boto3.client("secretsmanager")
        secret = json.loads(
            client.get_secret_value(SecretId=secret_name)["SecretString"]
        )
        _db_config = {
            "host": secret["host"],
            "port": int(secret.get("port", 3306)),
            "user": secret["username"],
            "password": secret["password"],
            "database": secret.get("dbname") or os.getenv("DB_NAME", "shopwave"),
        }
    else:
        _db_config = {
            "host": os.environ["DB_HOST"],
            "port": int(os.getenv("DB_PORT", "3306")),
            "user": os.environ["DB_USER"],
            "password": os.environ["DB_PASSWORD"],
            "database": os.getenv("DB_NAME", "shopwave"),
        }
    return _db_config


def _get_connection():
    """Return a live connection, reconnecting if the cached one dropped."""
    global _connection
    if _connection is not None:
        try:
            _connection.ping(reconnect=True)
            return _connection
        except Exception:
            _connection = None

    cfg = _load_db_config()
    _connection = pymysql.connect(
        host=cfg["host"],
        port=cfg["port"],
        user=cfg["user"],
        password=cfg["password"],
        database=cfg["database"],
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=5,
        read_timeout=5,
        autocommit=False,  # commit per order so a failure rolls back cleanly
    )
    return _connection


def _get_s3():
    global _s3
    if _s3 is None:
        _s3 = boto3.client("s3")
    return _s3


def _render_receipt(order, receipt_ts):
    """Plain-text receipt body for the S3 object."""
    customer = order.get("customer") or {}
    lines = [
        "ShopWave — Order Receipt",
        "=" * 32,
        f"Order:    {order['order_id']}",
        f"Date:     {receipt_ts}",
        f"Customer: {customer.get('name', 'N/A')}",
        f"Email:    {customer.get('email', 'N/A')}",
        "",
        "Items:",
    ]
    for item in order.get("items", []):
        qty = item.get("quantity", 1)
        price = float(item.get("price", 0))
        lines.append(
            f"  {qty} x {item.get('name', item.get('product_id'))} "
            f"@ {price:.2f} = {price * qty:.2f}"
        )
    lines += ["", f"Total:    {float(order.get('total', 0)):.2f}", ""]
    return "\n".join(lines)


def _write_receipt(order):
    """Upload the receipt to S3 and return its s3:// URL (or None if no bucket)."""
    bucket = os.environ.get("RECEIPT_BUCKET")
    if not bucket:
        print("order-processor warning: RECEIPT_BUCKET not set, skipping receipt")
        return None

    key = f"receipts/{order['order_id']}.txt"
    receipt_ts = datetime.now(timezone.utc).isoformat()
    _get_s3().put_object(
        Bucket=bucket,
        Key=key,
        Body=_render_receipt(order, receipt_ts).encode("utf-8"),
        ContentType="text/plain",
    )
    return f"s3://{bucket}/{key}"


def _persist_order(conn, order, receipt_url):
    """Insert the order + items. INSERT IGNORE keeps re-delivery idempotent."""
    customer = order.get("customer") or {}
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT IGNORE INTO orders
                (order_id, status, customer_name, customer_email,
                 customer, total, receipt_url, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                order["order_id"],
                "COMPLETED",
                customer.get("name"),
                customer.get("email"),
                json.dumps(customer),
                order.get("total", 0),
                receipt_url,
                order.get("created_at") or datetime.now(timezone.utc).isoformat(),
            ),
        )
        # rowcount == 0 means this order_id already existed -> already processed.
        if cur.rowcount == 0:
            print(f"order {order['order_id']} already processed, skipping items")
            return

        for item in order.get("items", []):
            cur.execute(
                """
                INSERT INTO order_items
                    (order_id, product_id, name, price, quantity)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    order["order_id"],
                    item.get("product_id"),
                    item.get("name"),
                    item.get("price", 0),
                    item.get("quantity", 1),
                ),
            )


def _process_record(record):
    order = json.loads(record["body"])
    if not order.get("order_id"):
        raise ValueError("order event is missing order_id")

    # Receipt first: it is idempotent (same key) and needs no DB transaction.
    receipt_url = _write_receipt(order)

    conn = _get_connection()
    try:
        _persist_order(conn, order, receipt_url)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    print(f"processed order {order['order_id']}")


def lambda_handler(event, context):
    failures = []
    for record in event.get("Records", []):
        try:
            _process_record(record)
        except Exception as exc:  # noqa: BLE001 — re-drive just this message
            print(f"order-processor error on {record.get('messageId')}: {exc}")
            failures.append({"itemIdentifier": record.get("messageId")})

    return {"batchItemFailures": failures}
