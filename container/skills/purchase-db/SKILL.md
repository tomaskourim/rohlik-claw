---
name: purchase-db
description: Item-level purchase history in SQLite. Use it to answer any question about what was bought, how much was spent, how a product's price moved over time, or how much of something was bought in a period — and to record newly delivered Rohlik orders. Covers totals, per-category and per-product spend, average unit prices, price history, and staples.
allowed-tools: Bash, Read, mcp__rohlik__get_order_history, mcp__rohlik__get_order_detail
---

# Purchase database

Every delivered Rohlik order, down to the individual item, in
`/workspace/group/grocery/purchases.db`. Three tables — `products`, `orders`,
`order_items` — plus the flattened view `v_items`, which is what you almost
always want.

The `sqlite3` command-line tool is **not** installed in this container. Use the
two Python helpers in this skill directory; both work without any dependencies.

## Answering a question

```bash
S=~/.claude/skills/purchase-db
python3 $S/query.py --list                          # what's available
python3 $S/query.py --name spend_by_category
python3 $S/query.py --name price_history --arg 1413647
python3 $S/query.py "SELECT SUM(line_total) FROM v_items WHERE category LIKE 'Ovoce%'"
```

`query.py` is read-only — it opens the database in `ro` mode and refuses
anything that is not a `SELECT`/`WITH`, so a query cannot damage the data.

**Find the product ID first, then filter on it.** Matching on the name is a
trap: `name LIKE '%banán%'` also matches banana yoghurt and banana chips, and it
breaks when Rohlik renames a product. The ID is stable.

```bash
python3 $S/query.py --name search --arg banán     # → product_id
python3 $S/query.py --name price_history --arg 1234567
```

**Units matter.** `unit` is `kg`, `ks` or `l`, and `unit_price` is per that
unit. Bananas are sold by weight, so "average price of a banana" is a price per
kilo — you cannot convert to per-piece without knowing what one banana weighs.
Say so rather than inventing a conversion.

## Recording a new order

You are the only one who can reach the Rohlik MCP tools, so ingestion runs
through you. Build the JSON, pipe it into `ingest.py`, and let the script own
the schema and the deduplication.

```bash
python3 ~/.claude/skills/purchase-db/ingest.py <<'JSON'
{"order_id": "1127179408", "ordered_at": "2026-06-19", "total_czk": 818.0,
 "items": [
   {"product_id": "1413647", "name": "Farmářská vejce", "category": "Mléčné a chlazené",
    "unit": "ks", "brand": "Rohlik.cz", "quantity": 2, "unit_price": 89.9, "line_total": 179.8}
 ]}
JSON
```

Accepts one order, a bare list, or `{"orders": [...]}`. Required per order:
`order_id`, `ordered_at` (must start `YYYY-MM-DD`), and `items`. Required per
item: `product_id`, `name`, `unit`, `quantity`, `unit_price`. Everything else
is optional.

**Re-ingesting an order is safe.** Its lines are replaced wholesale, so a
corrected re-run fixes the data instead of duplicating it. Ingest each order
whole — never line by line, or the rewrite drops the earlier lines.

Watch stderr. A `quantity*unit_price != line_total` warning means the parse is
wrong; fix it rather than leaving bad rows in place.

## Which orders still need ingesting

```bash
python3 ~/.claude/skills/purchase-db/query.py "SELECT order_id FROM orders ORDER BY ordered_at DESC LIMIT 20"
```

Compare against `get_order_history` and ingest only what is missing. This is
cheaper and more reliable than `grocery/delivery-log.md`, which is prose.

## Reports

`grocery/spending.md` and `grocery/staples.md` are hand-maintained summaries
that this database can now generate — `--name monthly_spend` and
`--name staples` produce the same figures from the source data. When you
refresh them, derive the numbers from a query rather than re-counting by hand,
and say in the file which query produced them.
