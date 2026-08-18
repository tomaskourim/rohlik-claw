-- Item-level purchase history for Rohlik orders.
-- Long/tidy format: one row per (order, product). Aggregate into any cube with GROUP BY.

CREATE TABLE IF NOT EXISTS products (
  product_id TEXT PRIMARY KEY,          -- Rohlik product ID, stable across renames
  name       TEXT NOT NULL,
  category   TEXT,
  unit       TEXT NOT NULL,             -- 'kg' | 'ks' | 'l'
  brand      TEXT,
  first_seen TEXT,                      -- ISO date of earliest order containing it
  last_seen  TEXT
);

CREATE TABLE IF NOT EXISTS orders (
  order_id   TEXT PRIMARY KEY,
  ordered_at TEXT NOT NULL,             -- ISO date (YYYY-MM-DD)
  total_czk  REAL,
  item_count INTEGER
);

CREATE TABLE IF NOT EXISTS order_items (
  order_id   TEXT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
  product_id TEXT NOT NULL REFERENCES products(product_id),
  quantity   REAL NOT NULL,             -- in the product's unit
  unit_price REAL NOT NULL,             -- CZK per unit, as paid in THIS order
  line_total REAL NOT NULL,
  PRIMARY KEY (order_id, product_id)
);

CREATE INDEX IF NOT EXISTS idx_orders_date    ON orders(ordered_at);
CREATE INDEX IF NOT EXISTS idx_items_product  ON order_items(product_id);
CREATE INDEX IF NOT EXISTS idx_products_cat   ON products(category);

-- Flattened view — use this for almost every question.
CREATE VIEW IF NOT EXISTS v_items AS
SELECT o.order_id, o.ordered_at,
       p.product_id, p.name, p.category, p.unit, p.brand,
       i.quantity, i.unit_price, i.line_total
FROM order_items i
JOIN orders   o ON o.order_id   = i.order_id
JOIN products p ON p.product_id = i.product_id;
