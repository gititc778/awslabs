"""
ShopWave — e-commerce frontend (runs on ECS behind an ALB).

This is the Python web UI from the architecture diagram. It calls three
backend APIs through API Gateway:

    GET  /products        -> Products API      (list catalog)
    POST /orders          -> Create Order API  (place an order, async via SQS)
    GET  /orders/{id}     -> Order Status API  (check an order)

If no API_BASE_URL is configured it falls back to built-in sample data
(MOCK_MODE) so the storefront is fully browsable during development.
"""
import uuid

import requests
from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from config import Config
from mock_data import MOCK_PRODUCTS, build_mock_order

app = Flask(__name__)
app.config.from_object(Config)


# --------------------------------------------------------------------------- #
# Backend API helpers
# --------------------------------------------------------------------------- #
def _api_url(path: str) -> str:
    return f"{app.config['API_BASE_URL']}{path}"


def get_products():
    """Return the product catalog (list of dicts)."""
    if app.config["MOCK_MODE"] and not app.config["API_BASE_URL"]:
        return MOCK_PRODUCTS
    resp = requests.get(_api_url("/products"), timeout=app.config["API_TIMEOUT"])
    resp.raise_for_status()
    data = resp.json()
    # API may return {"products": [...]} or a bare list.
    return data.get("products", data) if isinstance(data, dict) else data


def get_product(product_id):
    for p in get_products():
        if str(p.get("id")) == str(product_id):
            return p
    return None


def create_order(payload: dict) -> dict:
    """POST /orders — returns the created order (with an id/status)."""
    if app.config["MOCK_MODE"] and not app.config["API_BASE_URL"]:
        return build_mock_order(payload)
    resp = requests.post(
        _api_url("/orders"), json=payload, timeout=app.config["API_TIMEOUT"]
    )
    resp.raise_for_status()
    return resp.json()


def get_order(order_id):
    """GET /orders/{id} — returns the order or None if not found."""
    if app.config["MOCK_MODE"] and not app.config["API_BASE_URL"]:
        return build_mock_order({"order_id": order_id}, existing=True)
    resp = requests.get(
        _api_url(f"/orders/{order_id}"), timeout=app.config["API_TIMEOUT"]
    )
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


# --------------------------------------------------------------------------- #
# Template context
# --------------------------------------------------------------------------- #
@app.context_processor
def inject_globals():
    return {"store_name": app.config["STORE_NAME"]}


# --------------------------------------------------------------------------- #
# Routes — storefront (server-rendered)
# --------------------------------------------------------------------------- #
@app.route("/")
def index():
    try:
        products = get_products()
        error = None
    except requests.RequestException as exc:
        products, error = [], f"Could not load products: {exc}"
    categories = sorted({p.get("category", "General") for p in products})
    return render_template(
        "index.html", products=products, categories=categories, error=error
    )


@app.route("/product/<product_id>")
def product_detail(product_id):
    try:
        product = get_product(product_id)
    except requests.RequestException:
        product = None
    if not product:
        abort(404)
    return render_template("product.html", product=product)


@app.route("/cart")
def cart():
    # The cart lives in the browser (localStorage). This page renders it
    # client-side, so we just serve the shell.
    return render_template("cart.html")


@app.route("/checkout", methods=["GET"])
def checkout():
    return render_template("checkout.html")


@app.route("/checkout", methods=["POST"])
def place_order():
    """Accept the checkout form + cart JSON and call the Create Order API."""
    items = request.get_json(silent=True)
    if items is None:
        # Fallback for a classic form post: items come as a JSON string field.
        import json

        raw = request.form.get("items", "[]")
        items = json.loads(raw)
        customer = {
            "name": request.form.get("name", ""),
            "email": request.form.get("email", ""),
            "address": request.form.get("address", ""),
        }
    else:
        customer = items.get("customer", {})
        items = items.get("items", [])

    if not items:
        return jsonify({"error": "Your cart is empty."}), 400

    payload = {
        "customer": customer,
        "items": [
            {
                "product_id": i.get("id"),
                "name": i.get("name"),
                "price": i.get("price"),
                "quantity": i.get("quantity", 1),
            }
            for i in items
        ],
        "idempotency_key": str(uuid.uuid4()),
    }

    try:
        order = create_order(payload)
    except requests.RequestException as exc:
        return jsonify({"error": f"Order could not be placed: {exc}"}), 502

    order_id = order.get("order_id") or order.get("id")
    return jsonify({"order_id": order_id, "redirect": url_for("order_confirmation", order_id=order_id)})


@app.route("/orders/<order_id>/confirmation")
def order_confirmation(order_id):
    try:
        order = get_order(order_id)
    except requests.RequestException:
        order = None
    return render_template("order_confirmation.html", order_id=order_id, order=order)


@app.route("/orders", methods=["GET"])
def order_lookup():
    order_id = request.args.get("order_id", "").strip()
    if order_id:
        return redirect(url_for("order_status", order_id=order_id))
    return render_template("order_status.html", order=None, order_id=None, searched=False)


@app.route("/orders/<order_id>")
def order_status(order_id):
    try:
        order = get_order(order_id)
        error = None
    except requests.RequestException as exc:
        order, error = None, f"Could not load order: {exc}"
    return render_template(
        "order_status.html", order=order, order_id=order_id, searched=True, error=error
    )


# --------------------------------------------------------------------------- #
# Ops
# --------------------------------------------------------------------------- #
@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.errorhandler(404)
def not_found(_):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
