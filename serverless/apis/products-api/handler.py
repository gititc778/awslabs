"""
Products API — Lambda behind API Gateway  (GET /products).

Reads the catalog from RDS (MySQL) and returns it to the frontend.

Response 200:
    {"products": [{"id", "name", "category", "price", "description",
                   "image", "stock", "rating"}, ...]}

Credentials:
    Preferred  -> Secrets Manager secret named by env DB_SECRET_NAME,
                  a JSON blob {"host","port","username","password","dbname"}.
    Fallback   -> individual env vars DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME.

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


def lambda_handler(event, context):
    try:
        conn = _get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, category, price, description,
                       image, stock, rating
                FROM products
                ORDER BY id
                """
            )
            products = [_serialize(r) for r in cur.fetchall()]

        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps({"products": products}),
        }

    except Exception as exc:  # noqa: BLE001 — surface a clean 500 to the client
        print(f"products-api error: {exc}")
        return {
            "statusCode": 500,
            "headers": CORS_HEADERS,
            "body": json.dumps({"error": "Failed to load products"}),
        }
