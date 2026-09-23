# ShopWave — Serverless E-commerce

A serverless e-commerce app built for the AWS workshop. A Python (Flask) frontend
runs on **ECS** behind an **ALB** and calls three backend **Lambda** functions
through **API Gateway**. Order creation is asynchronous via **SQS**, and the
**Order Processor** writes to **RDS (MySQL)** and files receipts in **S3**.

```
User → ALB → ECS (Python UI) → API Gateway ─┬─ GET  /products      → Products API (Lambda)      → RDS
                                             ├─ POST /orders        → Create Order API (Lambda)  → SQS ─┐
                                             └─ GET  /orders/{id}   → Order Status API (Lambda)  → RDS  │
                                                                                                        ▼
                                                              Order Processor (Lambda) ← SQS ─── writes RDS + S3 receipt
```

## Layout

```
serverless/
├── frontend/                 # ECS Python web UI (Flask)   ← built
│   ├── app.py                # routes + API Gateway calls
│   ├── config.py             # env-driven config
│   ├── mock_data.py          # sample data for MOCK_MODE
│   ├── templates/            # Jinja2 pages
│   ├── static/               # CSS + JS (cart, checkout)
│   ├── requirements.txt
│   └── Dockerfile
├── apis/                     # Lambda functions           ← built
│   ├── products-api/         # GET  /products             → RDS
│   ├── create-order-api/     # POST /orders               → SQS
│   ├── order-status-api/     # GET  /orders/{id}          → RDS
│   └── order-processor/      # SQS-triggered              → RDS + S3
└── db/                       # RDS (MySQL) SQL scripts
    ├── schema.sql            # products, orders, order_items
    └── seed.sql              # sample catalog (mirrors mock_data.py)
```

## Run the frontend locally

```bash
cd frontend
pip install -r requirements.txt
python app.py            # http://localhost:8080
```

With no `API_BASE_URL` set it runs in **MOCK_MODE** with built-in sample
products, so the whole storefront (browse → cart → checkout → track order)
is clickable without any backend.

### Point it at the real backend

```bash
export API_BASE_URL="https://<api-id>.execute-api.eu-west-2.amazonaws.com/prod"
python app.py
```

| Variable       | Default        | Purpose                                   |
|----------------|----------------|-------------------------------------------|
| `API_BASE_URL` | *(empty)*      | API Gateway base URL. Empty → mock data.  |
| `MOCK_MODE`    | `true`         | Serve sample data when no URL configured. |
| `API_TIMEOUT`  | `5`            | Backend request timeout (seconds).        |
| `STORE_NAME`   | `ShopWave`     | Store branding.                           |
| `SECRET_KEY`   | `dev-secret…`  | Flask session secret.                     |

### Docker

```bash
cd frontend
docker build -t shopwave-frontend .
docker run -p 8080:8080 shopwave-frontend
```

## Status

- [x] **Step 1** — Frontend UI + API folder scaffolding
- [x] **Step 2** — Products API (read from RDS)
- [x] **Step 3** — Create Order API (→ SQS) + Order Processor (SQS → RDS + S3)
- [x] **Step 4** — Order Status API (read from RDS)
- [ ] Step 5 — Infra: RDS schema, SQS, API Gateway, ECS task/service, ALB
```
