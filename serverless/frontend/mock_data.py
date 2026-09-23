"""Sample data used when no backend API is configured (MOCK_MODE).

Lets the storefront be fully browsable before the Lambda APIs exist. The
schema mirrors what the real Products / Order APIs will return.
"""
import random
from datetime import datetime, timezone

MOCK_PRODUCTS = [
    {
        "id": 1,
        "name": "Aurora Wireless Headphones",
        "category": "Audio",
        "price": 129.99,
        "description": "Over-ear ANC headphones with 40-hour battery life and plush memory-foam cushions.",
        "image": "headphones",
        "stock": 24,
        "rating": 4.7,
    },
    {
        "id": 2,
        "name": "Nimbus Mechanical Keyboard",
        "category": "Accessories",
        "price": 89.50,
        "description": "Hot-swappable 75% mechanical keyboard with per-key RGB and a machined aluminium frame.",
        "image": "keyboard",
        "stock": 41,
        "rating": 4.8,
    },
    {
        "id": 3,
        "name": "Solstice Smartwatch",
        "category": "Wearables",
        "price": 199.00,
        "description": "AMOLED fitness smartwatch with GPS, SpO2, and a 7-day battery.",
        "image": "watch",
        "stock": 12,
        "rating": 4.5,
    },
    {
        "id": 4,
        "name": "Cobalt 4K Webcam",
        "category": "Video",
        "price": 74.99,
        "description": "4K UHD webcam with auto-framing, dual noise-cancelling mics and a privacy shutter.",
        "image": "webcam",
        "stock": 33,
        "rating": 4.4,
    },
    {
        "id": 5,
        "name": "Zephyr Portable SSD 1TB",
        "category": "Storage",
        "price": 109.00,
        "description": "Pocket-sized 1TB NVMe SSD with 1050 MB/s reads over USB-C.",
        "image": "ssd",
        "stock": 58,
        "rating": 4.9,
    },
    {
        "id": 6,
        "name": "Lumen Desk Lamp",
        "category": "Home",
        "price": 44.95,
        "description": "Dimmable LED desk lamp with wireless charging base and adjustable colour temperature.",
        "image": "lamp",
        "stock": 27,
        "rating": 4.3,
    },
    {
        "id": 7,
        "name": "Pulse Bluetooth Speaker",
        "category": "Audio",
        "price": 59.99,
        "description": "Rugged IP67 waterproof speaker with 360° sound and 24-hour playback.",
        "image": "speaker",
        "stock": 19,
        "rating": 4.6,
    },
    {
        "id": 8,
        "name": "Vertex Ergonomic Mouse",
        "category": "Accessories",
        "price": 39.99,
        "description": "Vertical ergonomic mouse with silent clicks and 4000 DPI precision sensor.",
        "image": "mouse",
        "stock": 46,
        "rating": 4.2,
    },
]

_STATUSES = ["PENDING", "PROCESSING", "SHIPPED", "DELIVERED"]


def build_mock_order(payload: dict, existing: bool = False) -> dict:
    """Fabricate an order object shaped like the real API response."""
    order_id = payload.get("order_id") or f"ORD-{random.randint(10000, 99999)}"
    items = payload.get("items", [])
    if existing and not items:
        # A looked-up order we didn't create in this process: show a sample.
        items = [
            {"product_id": 1, "name": "Aurora Wireless Headphones", "price": 129.99, "quantity": 1},
            {"product_id": 5, "name": "Zephyr Portable SSD 1TB", "price": 109.00, "quantity": 2},
        ]
    total = sum(float(i.get("price", 0)) * int(i.get("quantity", 1)) for i in items)
    return {
        "order_id": order_id,
        "status": random.choice(_STATUSES) if existing else "PENDING",
        "items": items,
        "total": round(total, 2),
        "customer": payload.get("customer", {}),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "receipt_url": f"s3://shopwave-receipts/{order_id}.pdf",
    }
