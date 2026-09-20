import json
import os
import uuid
import logging
from datetime import datetime, timezone

import boto3
import pymysql
from flask import Flask, request, jsonify

SECRET_NAME = os.environ.get("SECRET_NAME", "db-creds")
REGION      = os.environ.get("AWS_REGION", "eu-west-2")
TABLE       = os.environ.get("TABLE_NAME", "employees")
LOG_BUCKET  = os.environ.get("LOG_BUCKET")           # e.g. my-eks-lab-logs
LOG_PREFIX  = os.environ.get("LOG_PREFIX", "app-logs")
POD         = os.environ.get("HOSTNAME", "unknown-pod")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("app")

# clients (creds come from EKS Pod Identity; same role now also has s3:PutObject)
s3 = boto3.client("s3", region_name=REGION)


def get_db_creds():
    sm = boto3.client("secretsmanager", region_name=REGION)
    return json.loads(sm.get_secret_value(SecretId=SECRET_NAME)["SecretString"])


def connect():
    c = get_db_creds()
    return pymysql.connect(
        host=c["host"], port=int(c.get("port", 3306)),
        user=c["username"], password=c["password"], database=c["dbname"],
        connect_timeout=10, autocommit=True, cursorclass=pymysql.cursors.DictCursor,
    )


def log_to_s3(action, detail):
    """Write one JSON log record to S3. Never breaks the request if it fails."""
    if not LOG_BUCKET:
        log.warning("LOG_BUCKET not set — skipping S3 log")
        return
    now = datetime.now(timezone.utc)
    record = {
        "timestamp": now.isoformat(),
        "pod": POD,
        "action": action,
        "detail": detail,
    }
    key = f"{LOG_PREFIX}/{now:%Y/%m/%d}/{now:%H%M%S}-{uuid.uuid4().hex[:8]}.json"
    try:
        s3.put_object(
            Bucket=LOG_BUCKET, Key=key,
            Body=json.dumps(record).encode(), ContentType="application/json",
        )
        log.info("Logged to s3://%s/%s", LOG_BUCKET, key)
    except Exception as e:
        log.error("S3 log failed: %s", e)


app = Flask(__name__)

# create the employees table once at startup
with connect() as conn, conn.cursor() as cur:
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE} (
            id INT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            department VARCHAR(255) NOT NULL
        )
    """)


@app.get("/health")
def health():
    return "ok", 200


@app.post("/employees")
def add_employee():
    data = request.get_json(silent=True) or {}
    emp_id, name, dept = data.get("id"), data.get("name"), data.get("department")
    if emp_id is None or not name or not dept:
        return jsonify(error='send JSON: {"id": 1, "name": "...", "department": "..."}'), 400
    try:
        with connect() as conn, conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO {TABLE} (id, name, department) VALUES (%s, %s, %s)",
                (emp_id, name, dept),
            )
        log_to_s3("employee_added", data)
        return jsonify(inserted=data), 201
    except pymysql.err.IntegrityError:
        log_to_s3("employee_add_failed", {"id": emp_id, "reason": "duplicate id"})
        return jsonify(error=f"employee id {emp_id} already exists"), 409


@app.get("/employees")
def list_employees():
    with connect() as conn, conn.cursor() as cur:
        cur.execute(f"SELECT * FROM {TABLE} ORDER BY id")
        rows = cur.fetchall()
    log_to_s3("employees_listed", {"count": len(rows)})
    return jsonify(rows)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
