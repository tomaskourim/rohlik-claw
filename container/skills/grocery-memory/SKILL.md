---
name: grocery-memory
description: Analyze Rohlik delivery history to extract taste preferences, staple items, co-purchase patterns, brand preferences, and seasonal trends. Run BEFORE every grocery order to ensure memory is up-to-date. Also use when the user asks to analyze their shopping history, or on first run to bootstrap the grocery profile.
---

# Grocery Memory — Delivery Analysis & Preference Tracking

Analyze past Rohlik deliveries and maintain structured memory files in `/workspace/group/grocery/` so the shopping planner always has up-to-date knowledge about the household.

## CRITICAL: Data Source Rules

- **Only update memory from COMPLETED, DELIVERED orders** — never from planned carts, proposed lists, or confirmed-but-not-yet-delivered orders.
- The shopping planner must NOT write to these files based on what it plans to order. A planned order may never actually be bought.
- The only exception: if the user explicitly states a durable preference during planning (e.g., "I'm vegetarian now", "we stopped buying brand X", "always get organic eggs"), that preference update IS allowed because it reflects the user's intent, not a cart prediction.

## When to Run

**Before every grocery order:** The shopping planner should trigger a memory refresh before building a cart. This means:
1. Fetch recent completed orders from Rohlik
2. Compare against `delivery-log.md` to find unprocessed deliveries
3. Analyze new deliveries and update all memory files
4. Then hand off to the shopping planner with fresh data

This ensures the planner always works with up-to-date preferences, staples, and fridge state.

## Memory Files

All files live in `/workspace/group/grocery/`. Create the directory if it doesn't exist.

| File | Purpose |
|------|---------|
| `preferences.md` | Taste profile, liked/disliked items, brand preferences, dietary restrictions |
| `staples.md` | Items appearing in 70%+ of orders with typical quantities and Rohlik product IDs |
| `patterns.md` | Co-purchase patterns, seasonal trends, order frequency stats |
| `meals.md` | Favorite meals, last cooked dates, required ingredients |
| `planning-feedback.md` | Tracked user corrections during planning sessions (implicit preference signals) |
| `household.md` | Household size, dietary needs, budget range |
| `delivery-log.md` | Compact processed delivery summaries |
| `spending.md` | Average order cost, spending trends |
| `fridge-state.md` | Current estimated contents (managed by fridge-tracker skill) |

## How to Analyze Deliveries

### 1. Fetch order history

```bash
# Use rohlik MCP tools — do NOT scrape the website
```

Call `mcp__rohlik__get_order_history` to get recent orders. Then call `mcp__rohlik__get_order_detail` for each order to get item-level data. Process orders one at a time to avoid context overflow.

### 2. Extract preferences

For each order, record:
- **Items and quantities** — what was bought and how much
- **Brands** — track which brand is chosen when alternatives exist
- **Categories** — group items (dairy, meat, vegetables, bakery, pantry, frozen, drinks, household)

After processing all orders, identify:
- **Staples** — items in 70%+ of orders → write to `staples.md`
- **Brand loyalty** — same brand picked 80%+ of the time → write to `preferences.md`
- **Dislikes** — categories or items never or rarely ordered despite being common → note in `preferences.md`
- **Co-purchase patterns** — items that appear together in 60%+ of orders → write to `patterns.md`
- **Seasonal trends** — items that appear only in certain months → write to `patterns.md`

### 3. File formats

**`preferences.md`:**
```markdown
# Taste Preferences
Last updated: YYYY-MM-DD

## Liked Categories
- Category (specific items, brands)

## Disliked / Avoided
- Items never ordered despite being common staples

## Brand Preferences
| Category | Preferred Brand | Notes |
|----------|----------------|-------|
| Milk | Brand | Fat %, size |

## Dietary Restrictions
- List any detected or user-stated restrictions
```

**`staples.md`:**
```markdown
# Staple Items
Last updated: YYYY-MM-DD

| Product | Rohlik ID | Typical Qty | Frequency | Category |
|---------|-----------|------------|-----------|----------|
| Item name | 12345 | N | every order / every other | Category |
```

When processing orders via `mcp__rohlik__get_order_detail`, extract the Rohlik product ID for each item and store it in `staples.md`. This allows the shopping planner to call `mcp__rohlik__add_to_cart` directly without re-searching. Update IDs if Rohlik changes them (detect by name match with different ID).

**`meals.md`:**
```markdown
# Favorite Meals
Last updated: YYYY-MM-DD

| Meal | Key Ingredients | Times Ordered | Last Cooked | Source |
|------|----------------|---------------|-------------|--------|
| Pasta bolognese | pasta, canned tomatoes, ground beef, parmesan | 5 | 2026-03-15 | co-purchase pattern |
```

Build this from co-purchase patterns and user-stated meals. When the same ingredient combination appears across multiple orders, infer a meal. When the user explicitly mentions a meal ("we're making pizza tonight"), add it with source "user-stated". Track `Last Cooked` from the most recent order containing all key ingredients.

**`planning-feedback.md`:**
```markdown
# Planning Session Feedback
Last updated: YYYY-MM-DD

Tracks repeated user corrections during shopping planning sessions.
Only promote to preferences.md when a pattern is clear (3+ occurrences).

## Removals (user removed from proposed cart)
| Item | Times Removed | Last Session | Promoted |
|------|--------------|--------------|----------|
| Yogurt natural | 3 | 2026-03-23 | yes → preferences.md |

## Additions (user added items not in staples)
| Item | Times Added | Last Session | Promoted |
|------|------------|--------------|----------|
| Sparkling water | 2 | 2026-03-20 | no |

## Quantity Adjustments
| Item | Direction | Times | Last Session |
|------|-----------|-------|--------------|
| Milk | increased (1→2) | 4 | 2026-03-23 |
```

**`patterns.md`:**
```markdown
# Shopping Patterns
Last updated: YYYY-MM-DD

## Co-Purchase Patterns
- Item A + Item B + Item C (reason/meal)

## Seasonal Trends
- Summer: items
- Winter: items

## Order Frequency
- Average interval: N days
- Typical order size: N-M items
- Typical cost: N-M CZK
```

**`spending.md`:**
```markdown
# Spending Patterns
Last updated: YYYY-MM-DD

## Summary
- Average order: N CZK
- Monthly average: N CZK
- Orders per month: N

## Recent Orders
| Date | Items | Total | Notes |
|------|-------|-------|-------|
```

### 4. Pre-delivery analysis (run before every order)

Before building a new grocery order, refresh memory with any unprocessed completed deliveries:

1. Call `mcp__rohlik__get_order_history` to find recent completed/delivered orders
2. Read `delivery-log.md` to identify which orders have already been processed (by order ID or date)
3. For each unprocessed completed order, call `mcp__rohlik__get_order_detail`
4. Merge new data with existing consolidation — update `preferences.md`, `staples.md`, `patterns.md`, `spending.md`
5. Append new orders to `delivery-log.md`
6. Update `fridge-state.md` with delivered items (use actual delivery date, not order date)

This is an incremental process: existing consolidated data + newest deliveries → updated consolidation. No need to re-analyze the entire history each time.

### 5. Consumption model calibration

When processing completed orders, calculate actual consumption rates per product:
- For each staple item, measure the interval between consecutive orders containing it
- Compare against the default category rate from the fridge-tracker skill
- If the actual reorder interval consistently differs (3+ data points), write a calibrated rate to `fridge-state.md` under `## Calibrated Rates`:

```markdown
## Calibrated Rates
| Product | Category Default | Actual Avg | Data Points | Last Updated |
|---------|-----------------|------------|-------------|--------------|
| Milk 1.5% 1L | 5-7 days | 4 days | 6 | 2026-03-23 |
| Eggs 10pc | 14 days | 10 days | 4 | 2026-03-23 |
```

The fridge-tracker skill will use calibrated rates when available, falling back to category defaults.

### 6. Planning feedback promotion

After updating memory from completed orders, check `planning-feedback.md`:
- **Removals with 3+ occurrences**: Add item to `preferences.md` under "## Disliked / Avoided" and mark as `Promoted: yes`
- **Additions with 3+ occurrences**: Add item to `staples.md` (with Rohlik ID if known) and mark as `Promoted: yes`
- **Quantity adjustments with 3+ consistent direction**: Update the typical quantity in `staples.md`

This is the ONLY mechanism for learning from planning sessions — it requires repeated, consistent signals, not one-time corrections.

### 7. Waste detection

Compare reorder intervals against expected consumption:
- If a perishable item was ordered but NOT reordered within 2x its expected consumption period, it was likely wasted
- Note waste-prone items in `preferences.md` under a "## Waste Risk" section
- Consider reducing suggested quantities for these items

### 8. File size management

If any file exceeds 400 lines:
- Summarize older entries (keep last 3 months detailed, compress earlier data)
- For `delivery-log.md`: keep last 20 orders detailed, summarize earlier ones as monthly aggregates

## Bootstrap Flow

If `grocery/` directory is empty or doesn't exist:
1. Create the directory and all files
2. Fetch the last 10-20 orders from Rohlik
3. Process them to build initial profiles
4. Ask the user about household size, dietary restrictions, budget
5. Save to `household.md`
6. Confirm: summarize what you learned about their preferences
