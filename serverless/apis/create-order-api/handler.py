"""
Create Order API — Lambda behind API Gateway  (POST /orders).

Validates the incoming order and pushes an event onto SQS (async). It does
NOT write to RDS directly — the Order Processor consumes the queue and does
that. Returns quickly with a generated order id and PENDING status.

    Request:  {"customer": {...},
               "items": [{"product_id","name","price","quantity"}, ...],
               "idempotency_key": "..."}
    Response 202: {"order_id": "ORD-...", "status": "PENDING"}
    Response 400: {"error": "..."}   (invalid payload)

The SQS message body is the full order event the Order Processor expects:
    {"order_id", "status", "customer", "items", "total",
     "idempotency_key", "created_at"}

The SQS client is cached at module scope so warm invocations reuse it.
"""
import json
import os
import uuid
from datetime import datetime, timezone

import boto3

# Cached across warm invocations.
_sqs = None

CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": os.getenv("CORS_ORIGIN", "*"),
}


def _get_sqs():
    global _sqs
    if _sqs is None:
        _sqs = boto3.client("sqs")
    return _sqs


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": CORS_HEADERS,
        "body": json.dumps(body),
    }


def _parse_body(event):
    """API Gateway delivers the body as a (possibly base64) JSON string."""
    body = event.get("body")
    if body is None:
        return {}
    if isinstance(body, dict):  # direct/test invocation
        return body
    return json.loads(body)


def _validate(payload):
    """Return (order_event, error). error is None when valid."""
    customer = payload.get("customer") or {}
    items = payload.get("items") or []

    if not items:
        return None, "Order must contain at least one item."

    normalized = []
    total = 0.0
    for i, item in enumerate(items):
        product_id = item.get("product_id")
        quantity = item.get("quantity", 1)
        price = item.get("price")
        if product_id is None:
            return None, f"Item {i} is missing product_id."
        try:
            quantity = int(quantity)
            price = float(price)
        except (TypeError, ValueError):
            return None, f"Item {i} has an invalid price or quantity."
        if quantity < 1 or price < 0:
            return None, f"Item {i} has a non-positive quantity or negative price."

        total += price * quantity
        normalized.append({
            "product_id": product_id,
            "name": item.get("name"),
            "price": price,
            "quantity": quantity,
        })

    order_event = {
        "order_id": f"ORD-{uuid.uuid4().hex[:12].upper()}",
        "status": "PENDING",
        "customer": customer,
        "items": normalized,
        "total": round(total, 2),
        "idempotency_key": payload.get("idempotency_key") or str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return order_event, None


def lambda_handler(event, context):
    try:
        payload = _parse_body(event)
    except (json.JSONDecodeError, ValueError):
        return _response(400, {"error": "Request body must be valid JSON."})

    order_event, error = _validate(payload)
    if error:
        return _response(400, {"error": error})

    queue_url = os.environ.get("ORDER_QUEUE_URL")
    if not queue_url:
        print("create-order-api error: ORDER_QUEUE_URL is not set")
        return _response(500, {"error": "Order queue is not configured."})

    try:
        _get_sqs().send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(order_event),
            # Dedupe on the client-supplied key when using a FIFO queue.
            **(
                {
                    "MessageGroupId": "orders",
                    "MessageDeduplicationId": order_event["idempotency_key"],
                }
                if queue_url.endswith(".fifo")
                else {}
            ),
        )
    except Exception as exc:  # noqa: BLE001 — surface a clean 500 to the client
        print(f"create-order-api error: {exc}")
        return _response(502, {"error": "Failed to queue the order."})

    return _response(202, {
        "order_id": order_event["order_id"],
        "status": order_event["status"],
    })
