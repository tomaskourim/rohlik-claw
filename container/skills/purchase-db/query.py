#!/usr/bin/env python3
"""
Query the purchase database. Read-only: the connection is opened in ro mode and
anything that is not a SELECT/WITH is rejected, so a query can never damage data.

    python3 query.py --list                      # show canned queries
    python3 query.py --name spend_by_category
    python3 query.py --name price_history --arg 1413647
    python3 query.py "SELECT SUM(line_total) FROM v_items"
"""
import argparse
import os
import sqlite3
import sys

DEFAULT_DB = os.environ.get("PURCHASE_DB", "/workspace/group/grocery/purchases.db")

CANNED = {
    "total_spend": (
        "Total spend across all orders",
        "SELECT ROUND(SUM(line_total), 2) AS total_czk FROM v_items"),
    "spend_by_category": (
        "Spend per category, biggest first",
        "SELECT COALESCE(category,'(neznámá)') AS category, ROUND(SUM(line_total),2) AS czk,"
        " COUNT(DISTINCT order_id) AS orders"
        " FROM v_items GROUP BY 1 ORDER BY czk DESC"),
    "spend_by_product": (
        "Spend per product, biggest first",
        "SELECT product_id, name, unit, ROUND(SUM(line_total),2) AS czk,"
        " ROUND(SUM(quantity),2) AS qty, COUNT(*) AS times"
        " FROM v_items GROUP BY product_id ORDER BY czk DESC LIMIT 50"),
    "avg_unit_price": (
        "Average price per unit for one product  [--arg product_id]",
        "SELECT name, unit, ROUND(SUM(line_total)/NULLIF(SUM(quantity),0),2) AS avg_czk_per_unit,"
        " ROUND(SUM(quantity),2) AS total_qty"
        " FROM v_items WHERE product_id = ? GROUP BY product_id"),
    "price_history": (
        "Unit price over time for one product  [--arg product_id]",
        "SELECT ordered_at, unit_price, quantity, unit"
        " FROM v_items WHERE product_id = ? ORDER BY ordered_at"),
    "bought_last_month": (
        "Quantity and spend per product in the last 30 days",
        "SELECT name, unit, ROUND(SUM(quantity),2) AS qty, ROUND(SUM(line_total),2) AS czk"
        " FROM v_items WHERE ordered_at >= date('now','-1 month')"
        " GROUP BY product_id ORDER BY czk DESC"),
    "monthly_spend": (
        "Spend per calendar month",
        "SELECT substr(ordered_at,1,7) AS month, ROUND(SUM(line_total),2) AS czk,"
        " COUNT(DISTINCT order_id) AS orders"
        " FROM v_items GROUP BY 1 ORDER BY 1"),
    "search": (
        "Find products by name fragment  [--arg fragment]",
        "SELECT product_id, name, category, unit, ROUND(SUM(line_total),2) AS czk_total"
        " FROM v_items WHERE name LIKE '%'||?||'%' GROUP BY product_id ORDER BY czk_total DESC"),
    "staples": (
        "Products appearing in >=70% of orders",
        "SELECT name, unit, COUNT(DISTINCT order_id) AS in_orders,"
        " ROUND(100.0*COUNT(DISTINCT order_id)/(SELECT COUNT(*) FROM orders),1) AS pct"
        " FROM v_items GROUP BY product_id"
        " HAVING pct >= 70 ORDER BY pct DESC"),
}


def render(cursor):
    rows = cursor.fetchall()
    if not rows:
        print("(no rows)")
        return
    cols = [d[0] for d in cursor.description]
    data = [cols] + [["" if v is None else str(v) for v in r] for r in rows]
    widths = [max(len(r[i]) for r in data) for i in range(len(cols))]
    for idx, row in enumerate(data):
        print("  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)).rstrip())
        if idx == 0:
            print("  ".join("-" * w for w in widths))
    print("(%d row%s)" % (len(rows), "" if len(rows) == 1 else "s"))


def main():
    ap = argparse.ArgumentParser(description="Query the purchase database (read-only)")
    ap.add_argument("sql", nargs="?", help="ad-hoc SELECT statement")
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--name", help="run a canned query by name")
    ap.add_argument("--arg", action="append", default=[], help="parameter for a canned query")
    ap.add_argument("--list", action="store_true", help="list canned queries and exit")
    args = ap.parse_args()

    if args.list:
        width = max(len(k) for k in CANNED)
        for name in sorted(CANNED):
            print("%s  %s" % (name.ljust(width), CANNED[name][0]))
        return

    if args.name:
        if args.name not in CANNED:
            print("query: unknown canned query %r (use --list)" % args.name, file=sys.stderr)
            sys.exit(1)
        sql = CANNED[args.name][1]
    elif args.sql:
        sql = args.sql
    else:
        ap.error("give a SQL statement, --name, or --list")

    if not sql.lstrip().lower().startswith(("select", "with")):
        print("query: only SELECT/WITH statements are allowed", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(args.db):
        print("query: no database at %s — run ingest.py --init first" % args.db, file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect("file:%s?mode=ro" % args.db, uri=True)
    try:
        render(conn.execute(sql, tuple(args.arg)))
    except sqlite3.Error as exc:
        print("query: %s" % exc, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
