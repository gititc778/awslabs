"""
Order Status API — Lambda behind API Gateway  (GET /orders/{id}).

Reads a single order (and its line items) from RDS and returns it in the
shape the frontend renders.

    Response 200: {"order_id", "status", "items": [...], "total",
                   "customer", "created_at", "receipt_url"}
    Response 404: {"error": "not found", "order_id": ...}

Credentials mirror the Products API:
    Preferred  -> Secrets Manager secret named by env DB_SECRET_NAME
                  ({"host","port","username","password","dbname"}).
    Fallback   -> env vars DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME.

The DB connection and secret are cached at module scope so warm invocations
reuse them instead of reconnecting on every request.
"""
import json
import os
from decimal import Decimal

import pymysql

# Cached across warm invocations.
_connection = None
_db_config = None

CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": os.getenv("CORS_ORIGIN", "*"),
}


def _load_db_config():
    """Resolve DB credentials once (Secrets Manager, else env vars)."""
    global _db_config
    if _db_config is not None:
        return _db_config

    secret_name = os.getenv("DB_SECRET_NAME")
    if secret_name:
        import boto3  # provided by the Lambda runtime

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
        autocommit=True,
    )
    return _connection


def _serialize(row):
    """Make a DB row JSON-safe (Decimals -> float)."""
    return {
        k: (float(v) if isinstance(v, Decimal) else v) for k, v in row.items()
    }


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": CORS_HEADERS,
        "body": json.dumps(body, default=str),
    }


def lambda_handler(event, context):
    order_id = (event.get("pathParameters") or {}).get("id")
    if not order_id:
        return _response(400, {"error": "order id is required"})

    try:
        conn = _get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT order_id, status, customer, total,
                       receipt_url, created_at
                FROM orders
                WHERE order_id = %s
                """,
                (order_id,),
            )
            order = cur.fetchone()
            if not order:
                return _response(404, {"error": "not found", "order_id": order_id})

            cur.execute(
                """
                SELECT product_id, name, price, quantity
                FROM order_items
                WHERE order_id = %s
                """,
                (order_id,),
            )
            items = [_serialize(r) for r in cur.fetchall()]

        order = _serialize(order)
        # `customer` is stored as a JSON string -> hand back a real object.
        try:
            order["customer"] = json.loads(order.get("customer") or "{}")
        except (TypeError, ValueError):
            order["customer"] = {}
        order["items"] = items

        return _response(200, order)

    except Exception as exc:  # noqa: BLE001 — surface a clean 500 to the client
        print(f"order-status-api error: {exc}")
        return _response(500, {"error": "Failed to load order"})
