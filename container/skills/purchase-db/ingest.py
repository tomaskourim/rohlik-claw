#!/usr/bin/env python3
"""
Ingest Rohlik order data into the purchase database.

Reads JSON from stdin (or --file) and upserts it. Safe to re-run: an order that
is already present is updated in place, never duplicated.

    python3 ingest.py --init                 # create the DB and schema
    cat order.json | python3 ingest.py       # ingest one order or a list

Input shape (a single object, a bare list, or {"orders": [...]}):

    {
      "order_id": "1127179408",
      "ordered_at": "2026-06-19",
      "total_czk": 818.0,
      "items": [
        {"product_id": "1413647", "name": "Farmářská vejce",
         "category": "Mléčné a chlazené", "unit": "ks", "brand": "Rohlik.cz",
         "quantity": 2, "unit_price": 89.9, "line_total": 179.8}
      ]
    }

Only order_id, ordered_at and the item fields product_id/name/unit/quantity/
unit_price are required; the rest may be omitted or null.
"""
import argparse
import json
import os
import re
import sqlite3
import sys

DEFAULT_DB = os.environ.get("PURCHASE_DB", "/workspace/group/grocery/purchases.db")
SCHEMA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")


def die(msg):
    print("ingest: %s" % msg, file=sys.stderr)
    sys.exit(1)


def num(value, field, where):
    if value is None:
        die("%s: missing required numeric field '%s'" % (where, field))
    try:
        return float(value)
    except (TypeError, ValueError):
        die("%s: field '%s' is not a number: %r" % (where, field, value))


def text(value, field, where, required=True):
    if value is None or value == "":
        if required:
            die("%s: missing required field '%s'" % (where, field))
        return None
    return str(value).strip()


def connect(db_path, init=False):
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    if init:
        with open(SCHEMA, encoding="utf-8") as fh:
            conn.executescript(fh.read())
        conn.commit()
    return conn


def normalize(payload):
    if isinstance(payload, dict) and "orders" in payload:
        payload = payload["orders"]
    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list):
        die("expected an object or a list of orders, got %s" % type(payload).__name__)
    return payload


def ingest_order(conn, order, stats):
    oid = text(order.get("order_id"), "order_id", "order")
    where = "order %s" % oid
    date = text(order.get("ordered_at"), "ordered_at", where)
    if not DATE_RE.match(date):
        die("%s: ordered_at must start with YYYY-MM-DD, got %r" % (where, date))
    date = date[:10]

    items = order.get("items") or []
    if not items:
        die("%s: has no items" % where)

    total = order.get("total_czk")
    total = float(total) if total is not None else None

    existing = conn.execute(
        "SELECT 1 FROM orders WHERE order_id = ?", (oid,)
    ).fetchone()

    conn.execute(
        """INSERT INTO orders (order_id, ordered_at, total_czk, item_count)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(order_id) DO UPDATE SET
             ordered_at = excluded.ordered_at,
             total_czk  = COALESCE(excluded.total_czk, orders.total_czk),
             item_count = excluded.item_count""",
        (oid, date, total, len(items)),
    )
    stats["orders_updated" if existing else "orders_added"] += 1

    # Replace the order's lines wholesale so a corrected re-ingest cannot leave
    # stale items behind.
    conn.execute("DELETE FROM order_items WHERE order_id = ?", (oid,))

    for raw in items:
        iwhere = "%s item %r" % (where, raw.get("product_id"))
        pid = text(raw.get("product_id"), "product_id", iwhere)
        name = text(raw.get("name"), "name", iwhere)
        unit = text(raw.get("unit"), "unit", iwhere)
        qty = num(raw.get("quantity"), "quantity", iwhere)
        price = num(raw.get("unit_price"), "unit_price", iwhere)
        line = raw.get("line_total")
        line = float(line) if line is not None else round(qty * price, 2)

        drift = abs(qty * price - line)
        if drift > 0.5:
            print(
                "ingest: warning: %s: quantity*unit_price=%.2f but line_total=%.2f"
                % (iwhere, qty * price, line),
                file=sys.stderr,
            )
            stats["warnings"] += 1

        is_new = conn.execute(
            "SELECT 1 FROM products WHERE product_id = ?", (pid,)
        ).fetchone() is None
        conn.execute(
            """INSERT INTO products
                 (product_id, name, category, unit, brand, first_seen, last_seen)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(product_id) DO UPDATE SET
                 name       = excluded.name,
                 category   = COALESCE(excluded.category, products.category),
                 unit       = excluded.unit,
                 brand      = COALESCE(excluded.brand, products.brand),
                 first_seen = MIN(products.first_seen, excluded.first_seen),
                 last_seen  = MAX(products.last_seen,  excluded.last_seen)""",
            (pid, name, raw.get("category"), unit, raw.get("brand"), date, date),
        )
        if is_new:
            stats["products_new"] += 1

        conn.execute(
            """INSERT INTO order_items
                 (order_id, product_id, quantity, unit_price, line_total)
               VALUES (?, ?, ?, ?, ?)""",
            (oid, pid, qty, price, line),
        )
        stats["items"] += 1


def main():
    ap = argparse.ArgumentParser(description="Ingest Rohlik orders into the purchase DB")
    ap.add_argument("--db", default=DEFAULT_DB, help="database path (default: %s)" % DEFAULT_DB)
    ap.add_argument("--init", action="store_true", help="create schema if missing, then exit unless input is given")
    ap.add_argument("--file", help="read JSON from this file instead of stdin")
    args = ap.parse_args()

    conn = connect(args.db, init=True)  # schema is idempotent; always ensure it

    if args.file:
        with open(args.file, encoding="utf-8") as fh:
            raw = fh.read()
    elif args.init and sys.stdin.isatty():
        print("ingest: initialized %s" % args.db)
        return
    else:
        raw = sys.stdin.read()

    if not raw.strip():
        if args.init:
            print("ingest: initialized %s" % args.db)
            return
        die("no input on stdin (use --file, or --init to only create the schema)")

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        die("input is not valid JSON: %s" % exc)

    stats = {"orders_added": 0, "orders_updated": 0, "items": 0,
             "products_new": 0, "warnings": 0}
    try:
        for order in normalize(payload):
            ingest_order(conn, order, stats)
        conn.commit()
    except sqlite3.Error as exc:
        conn.rollback()
        die("database error, nothing was written: %s" % exc)

    print("ingest: %d order(s) added, %d updated, %d item rows, %d new product(s), %d warning(s)"
          % (stats["orders_added"], stats["orders_updated"], stats["items"],
             stats["products_new"], stats["warnings"]))


if __name__ == "__main__":
    main()
