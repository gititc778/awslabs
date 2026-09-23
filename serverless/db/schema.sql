-- ShopWave — RDS (MySQL) schema
-- =============================================================================
-- Single database shared by all Lambdas (per the architecture diagram).
--   products     read  by  Products API        (GET  /products)
--   orders       write by  Order Processor      (SQS-triggered)
--                read  by  Order Status API     (GET  /orders/{id})
--   order_items  written/read alongside orders
--
-- Apply with:
--   mysql -h <rds-endpoint> -u <user> -p < db/schema.sql
-- =============================================================================

CREATE DATABASE IF NOT EXISTS shopwave
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE shopwave;

-- -----------------------------------------------------------------------------
-- products — the catalog. Columns match what Products API SELECTs and what the
-- frontend renders (see frontend/mock_data.py).
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS products (
    id          INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    name        VARCHAR(255)    NOT NULL,
    category    VARCHAR(100)    NOT NULL,
    price       DECIMAL(10, 2)  NOT NULL,
    description TEXT            NULL,
    image       VARCHAR(100)    NULL,          -- icon/key, not a URL
    stock       INT             NOT NULL DEFAULT 0,
    rating      DECIMAL(2, 1)   NOT NULL DEFAULT 0.0,
    created_at  TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_products_category (category)
) ENGINE=InnoDB;

-- -----------------------------------------------------------------------------
-- orders — one row per placed order. order_id is the natural PK (client/API
-- generated, e.g. "ORD-AB12CD34EF56"); the Order Processor uses INSERT IGNORE
-- on it for idempotent SQS re-delivery. `customer` keeps the full JSON blob;
-- name/email are denormalized for quick display and lookups.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS orders (
    order_id       VARCHAR(40)                              NOT NULL,
    status         ENUM('PENDING','PROCESSING','COMPLETED',
                        'SHIPPED','DELIVERED','FAILED')     NOT NULL DEFAULT 'PENDING',
    customer_name  VARCHAR(255)                             NULL,
    customer_email VARCHAR(255)                             NULL,
    customer       JSON                                     NULL,
    total          DECIMAL(10, 2)                           NOT NULL DEFAULT 0.00,
    receipt_url    VARCHAR(512)                             NULL,   -- s3://bucket/key
    created_at     TIMESTAMP                                NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (order_id),
    KEY idx_orders_email (customer_email),
    KEY idx_orders_status (status)
) ENGINE=InnoDB;

-- -----------------------------------------------------------------------------
-- order_items — line items for an order. Deleted with the parent order.
-- product_id is a soft reference (products.id) — not an FK, so a catalog change
-- never blocks writing an order's historical snapshot (name/price captured here).
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS order_items (
    id         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    order_id   VARCHAR(40)     NOT NULL,
    product_id INT UNSIGNED    NULL,
    name       VARCHAR(255)    NULL,           -- snapshot at time of order
    price      DECIMAL(10, 2)  NOT NULL DEFAULT 0.00,
    quantity   INT             NOT NULL DEFAULT 1,
    PRIMARY KEY (id),
    KEY idx_order_items_order (order_id),
    CONSTRAINT fk_order_items_order
        FOREIGN KEY (order_id) REFERENCES orders (order_id)
        ON DELETE CASCADE
) ENGINE=InnoDB;
