-- ShopWave — sample catalog data
-- =============================================================================
-- Mirrors frontend/mock_data.py so the real backend serves the same products
-- the MOCK_MODE storefront shows. Safe to re-run: clears products first.
--
-- Apply with:
--   mysql -h <rds-endpoint> -u <user> -p shopwave < db/seed.sql
-- =============================================================================

USE shopwave;

-- TRUNCATE clears the table and resets AUTO_INCREMENT in one step, and is not
-- blocked by Workbench "safe update mode" the way a WHERE-less DELETE is.
-- (products has no incoming foreign keys, so this is safe.)
TRUNCATE TABLE products;

INSERT INTO products (id, name, category, price, description, image, stock, rating) VALUES
(1, 'Aurora Wireless Headphones', 'Audio',       129.99, 'Over-ear ANC headphones with 40-hour battery life and plush memory-foam cushions.', 'headphones', 24, 4.7),
(2, 'Nimbus Mechanical Keyboard', 'Accessories',  89.50, 'Hot-swappable 75% mechanical keyboard with per-key RGB and a machined aluminium frame.', 'keyboard', 41, 4.8),
(3, 'Solstice Smartwatch',        'Wearables',    199.00, 'AMOLED fitness smartwatch with GPS, SpO2, and a 7-day battery.', 'watch', 12, 4.5),
(4, 'Cobalt 4K Webcam',           'Video',         74.99, '4K UHD webcam with auto-framing, dual noise-cancelling mics and a privacy shutter.', 'webcam', 33, 4.4),
(5, 'Zephyr Portable SSD 1TB',    'Storage',      109.00, 'Pocket-sized 1TB NVMe SSD with 1050 MB/s reads over USB-C.', 'ssd', 58, 4.9),
(6, 'Lumen Desk Lamp',            'Home',          44.95, 'Dimmable LED desk lamp with wireless charging base and adjustable colour temperature.', 'lamp', 27, 4.3),
(7, 'Pulse Bluetooth Speaker',    'Audio',         59.99, 'Rugged IP67 waterproof speaker with 360° sound and 24-hour playback.', 'speaker', 19, 4.6),
(8, 'Vertex Ergonomic Mouse',     'Accessories',   39.99, 'Vertical ergonomic mouse with silent clicks and 4000 DPI precision sensor.', 'mouse', 46, 4.2);
