---
name: shopping-planner
description: Plan and build grocery orders on Rohlik. Orchestrates fridge state checking, preference matching, promotion scanning, and cart building. Use when the user wants to order groceries, plan meals, or asks for a shopping list.
---

# Shopping Planner — Grocery Order Orchestrator

Build smart grocery orders by combining fridge state, preferences, promotions, and user requirements.

## Order Type Detection

Before starting the workflow, determine the order type from the user's message:

**Full order** — "prepare a weekly order", "need groceries for the week", "make an order for 5 days"
→ Run the full workflow with all subagents.

**Quick top-up** — "I need milk", "can you add bread and eggs", "forgot to order butter", "we ran out of ham"
→ Skip subagents. Search for the requested items directly via `mcp__rohlik__search_products` (use cached Rohlik IDs from `staples.md` when available). Add to cart. Suggest a delivery slot. Done.
→ Still check `planning-feedback.md` for the item — if user previously adjusted quantities, use their preferred quantity.
→ Do NOT ask household/fridge questions for top-ups.

**Restock check** — "what do we need?", "anything running low?"
→ Run only the Fridge Estimator subagent. Present DEPLETED/LOW items. Ask if the user wants to turn it into an order.

If unclear, default to full order.

## Full Order Workflow

When the user asks to prepare a full grocery order:

### Step 1: Acknowledge and launch subagents

Send an immediate message via `mcp__nanoclaw__send_message`:
> "Working on your order — analyzing your deliveries, fridge, and current deals..."

Then launch **3 background subagents in parallel** using the `Task` tool with `run_in_background: true`:

#### Subagent 1: Delivery Analyzer

```
Description: "Analyze recent Rohlik deliveries and update grocery memory"
Prompt: |
  You are a delivery analysis agent. Your job:
  1. Call mcp__rohlik__get_order_history to get recent completed/delivered orders
  2. Read /workspace/group/grocery/delivery-log.md to find which orders are already processed
  3. For each NEW completed order, call mcp__rohlik__get_order_detail to get item-level data
  4. Update these files with new data merged into existing consolidation:
     - grocery/preferences.md (brand loyalty, liked/disliked categories)
     - grocery/staples.md (items in 70%+ of orders — include Rohlik product ID for each item)
     - grocery/patterns.md (co-purchase patterns, seasonal trends, order frequency)
     - grocery/spending.md (order totals, averages)
     - grocery/delivery-log.md (append new order summaries)
     - grocery/meals.md (infer meals from co-purchase ingredient groups)
  5. If grocery/ directory doesn't exist, create it and bootstrap from last 10-20 orders
  6. Calculate consumption calibration: for staple items, measure actual reorder intervals
     and write calibrated rates to fridge-state.md under "## Calibrated Rates"
  7. Check grocery/planning-feedback.md for items with 3+ repeated corrections:
     - Removals 3+ times → add to preferences.md as disliked, mark promoted
     - Additions 3+ times → add to staples.md, mark promoted
     - Quantity adjustments 3+ times → update typical qty in staples.md

  IMPORTANT: Only process COMPLETED/DELIVERED orders. Never update from pending orders.

  Return a concise summary:
  - How many new orders were processed
  - Any new patterns or preference changes detected
  - Current order frequency and average spend
  - Any planning feedback promoted to preferences/staples
  - Any consumption rates calibrated (product, old default, new calibrated)
```

#### Subagent 2: Fridge Estimator

```
Description: "Estimate current fridge and pantry contents"
Prompt: |
  You are a fridge state estimation agent. Your job:
  1. Read /workspace/group/grocery/fridge-state.md for the last known state
  2. Read /workspace/group/grocery/delivery-log.md for recent deliveries
  3. Read /workspace/group/grocery/household.md for household size (default: 2 adults if missing)
  4. Apply the consumption rate model with this priority:
     a. Check "## Calibrated Rates" in fridge-state.md — if a product has a calibrated
        rate based on actual reorder intervals, use it (do NOT apply household scaling)
     b. Check "## Custom Rates" in fridge-state.md — user manual overrides
     c. Fall back to category defaults:
        Fresh meat/fish: 2-3 days, Deli/ham: 4-5 days
        Milk/kefir: 5-7 days, Yogurt: 7-10 days
        Fresh vegetables: 5-7 days, Root vegetables: 14-21 days
        Fresh fruit: 3-5 days, Citrus/apples: 10-14 days
        Bread: 3-4 days, Eggs: 14 days
        Hard cheese: 14-21 days, Butter: 21-30 days
        Pantry staples (rice, pasta, flour): 60-90 days
        Spices/condiments: 180+ days, Frozen: 60 days
     For category defaults only, scale consumption by (household_size / 2).
  5. Calculate estimated remaining % for each item
  6. Update /workspace/group/grocery/fridge-state.md with current estimates
     (preserve the Calibrated Rates and Custom Rates sections when updating)

  Return a concise summary grouped by status:
  - DEPLETED (0-10%): items that definitely need restocking
  - LOW (10-30%): items that should probably be included
  - OK (30-70%): no action needed
  - FULL (70-100%): recently delivered, skip these

  Also list 2-3 borderline items where you're uncertain and suggest
  questions the main agent should ask the user.
```

**Note on subagent ordering:** The Delivery Analyzer and Fridge Estimator both touch `fridge-state.md`. The Analyzer adds newly delivered items and calibrated rates; the Estimator recalculates remaining percentages. When both run in parallel, the Estimator may read stale data. This is acceptable — the Estimator works with whatever state exists at read time, and both preserve each other's sections. The next run will reconcile.

#### Subagent 3: Promotion Scanner

```
Description: "Find relevant Rohlik promotions matching taste profile"
Prompt: |
  You are a promotion scanning agent. Your job:
  1. Read /workspace/group/grocery/preferences.md for taste profile and brand preferences
  2. Read /workspace/group/grocery/staples.md for always-buy items
  3. Read /workspace/group/grocery/patterns.md for seasonal preferences
  4. Call mcp__rohlik__get_discounted_items to fetch current promotions
  5. Filter promotions to ONLY items matching the household's taste profile:
     - Staple items on sale (direct savings)
     - Preferred brands on sale
     - Items in liked categories
     - Seasonal items appropriate for current time
  6. EXCLUDE deals on disliked items or categories

  Return a concise summary:
  - Top 5-10 most relevant deals with product name, Rohlik product ID, discount %, price, and why it matches
  - Any staple items currently on promotion (highlight these — guaranteed savings)
  - Total potential savings if all suggested deals are taken
```

### Step 2: Gather missing information (while subagents work)

While the 3 subagents run in the background, use this time to ask the user questions.

Check `/workspace/group/grocery/household.md`. If missing or incomplete, ask:
- How many people are you shopping for?
- How many days should this order cover?
- Any dietary restrictions or allergies?
- Any special events, guests, or occasions coming up?
- Anything left over from last time that I shouldn't re-order?
- Budget preference (normal / save where possible / no limit)?

If `household.md` exists and is recent, only ask about the current order:
- How many days should this cover?
- Any special plans or guests?
- Anything you still have plenty of at home?

### Step 3: Collect subagent results

Wait for all 3 subagents to complete (use `TaskOutput` to read results). You now have:

- **From Delivery Analyzer:** Updated memory files + summary of new patterns
- **From Fridge Estimator:** Updated fridge state + DEPLETED/LOW/OK/FULL summary + borderline questions
- **From Promotion Scanner:** Filtered relevant deals + savings potential

If the Fridge Estimator suggested borderline questions, ask them now (max 2-3 questions).

### Step 4: Build the cart proposal

Read the user's answers from Step 2 and the subagent summaries from Step 3. Also read:
- `grocery/preferences.md` — respect likes, dislikes, brand preferences
- `grocery/staples.md` — always-buy items form the baseline
- `grocery/patterns.md` — co-purchase patterns (if adding pasta, add canned tomatoes too)

Combine all inputs into a structured proposal. For each item, add a short reasoning tag so the user knows WHY it's in the cart. Use Rohlik product IDs from `staples.md` when available to avoid re-searching.

Reasoning tags (pick the most relevant one per item):
- `staple` — always-buy item from staples.md
- `low` — fridge tracker shows running low or depleted
- `deal -N%` — currently on promotion
- `pattern` — co-purchase pattern (e.g., goes with pasta)
- `meal` — ingredient for a favorite meal from meals.md
- `seasonal` — seasonal item matching current time
- `requested` — user explicitly asked for it

```
*Weekly order (N days, M people)*

*Dairy*
• Milk 1.5% Madeta 1L x2 — 35 CZK _staple, low_
• Yogurt natural x4 — 60 CZK _staple_
• Eidam 30% — 45 CZK _deal -25%_

*Meat & Fish*
• Chicken breast 500g — 89 CZK _low, meal: stir-fry_

*Pantry*
• Canned tomatoes x2 — 30 CZK _pattern: goes with pasta_

*Total: ~X CZK (saved ~Y CZK on deals)*

Anything to add, remove, or change?
```

Keep WhatsApp messages under 4000 characters. If the order is large, split into 2 messages.

### Step 5: Adjust and finalize

Process user feedback:
- "Remove the yogurt" → remove from cart
- "Add beer" → search via `mcp__rohlik__search_products`, suggest options
- "Make it 2 milks instead of 1" → adjust quantity
- "Looks good" → proceed to add to cart

**Track corrections in `grocery/planning-feedback.md`:**
- If the user removes an item → increment its removal count
- If the user adds an item not in the proposal → increment its addition count
- If the user changes a quantity → record the direction (increased/decreased)
- Do NOT promote these to preferences immediately — that happens during the next delivery analysis (Step 1, Delivery Analyzer subagent) when an item reaches 3+ occurrences

### Step 6: Add to cart

Use Rohlik product IDs from `staples.md` whenever available — call `mcp__rohlik__add_to_cart` with the cached ID directly. Only fall back to `mcp__rohlik__search_products` for items without a cached ID.

**Delivery timing intelligence:**
After adding items to cart, suggest optimal delivery timing based on fridge state:
1. Read `fridge-state.md` for the earliest depletion date among DEPLETED/LOW staple items
2. Call `mcp__rohlik__get_delivery_slots` to get available slots
3. Recommend the slot closest to (but before) the earliest critical depletion date
4. If nothing is critically low, suggest the next convenient slot

Present it as:
> "Your milk and eggs are likely running out by Wednesday. The earliest slot is Tuesday 10-12 — want that one, or prefer a different time?"

Show 2-3 options with context about why the recommended slot makes sense.

### Step 7: Memory rules during planning

**DO NOT update grocery memory files based on the planned or confirmed cart.** A planned order is not a completed delivery — it may be modified, cancelled, or never delivered. Memory must only reflect what was actually bought and delivered.

- Do NOT update `fridge-state.md`, `delivery-log.md`, `spending.md`, `staples.md`, `patterns.md`, or `preferences.md` from cart contents.
- These files will be updated automatically during the next delivery analysis (Step 1 subagent) once the order is completed and delivered.
- `planning-feedback.md` IS allowed to be updated during planning (Step 5) — it's a correction tracker, not a preference file. It only promotes to preferences after 3+ consistent signals during the next delivery analysis.

**Exception — durable user preferences:** If the user explicitly states a lasting preference during the planning conversation, you MAY update `preferences.md` or `household.md`. Examples:
- "I'm vegetarian now" → update dietary restrictions
- "We stopped buying Madeta, switch to Olma" → update brand preferences
- "There are 3 of us now" → update household size

These are user-stated facts about their identity/household, not predictions from a cart. Only save preferences that clearly apply to all future orders, not one-time requests like "add beer for tonight".

## Bootstrap Detection

If `/workspace/group/grocery/` doesn't exist or is mostly empty:
1. Tell the user: "This is our first time planning together — let me analyze your order history first."
2. Launch the Delivery Analyzer subagent (from Step 1) — it will detect the empty state and bootstrap from the last 10-20 orders
3. While it runs, ask the user household questions (size, dietary restrictions, budget)
4. Save answers to `grocery/household.md`
5. Once the analyzer finishes, confirm what was learned about preferences
6. Then proceed with the normal shopping workflow (Step 1 onward)

## Meal Planning Mode

When the user asks for meal suggestions:
1. Read `grocery/meals.md` for favorite meals and when they were last cooked
2. Check fridge state for available ingredients
3. Prioritize meals where most ingredients are already available (fridge state OK/FULL)
4. Deprioritize meals cooked recently (within last 7 days) for variety
5. Suggest 3-5 meals with ingredient availability status:
   > "• *Pasta bolognese* — have pasta & tomatoes, need ground beef _low_"
   > "• *Stir-fry* — have chicken _low_, need vegetables"
6. Offer to add missing ingredients to the cart
7. When the user confirms a meal, update `meals.md` with the current date as `Last Cooked`
8. If the user mentions a new meal not in `meals.md`, add it with its ingredients

## Event / Guest Mode

When the user mentions guests or a special occasion:
- Scale quantities by expected headcount
- Suggest category additions (drinks, snacks, desserts)
- Ask about dietary restrictions of guests
- Consider disposable plates/napkins if large gathering

## Smart Substitution

When searching for a product and the preferred item is unavailable:
1. Search for alternatives in the same category
2. Prefer the same brand in a different size
3. Then prefer a different brand the user has bought before
4. Present options: "Your usual X isn't available. How about Y (same brand, larger) or Z (different brand, similar price)?"

## Proactive Reorder Reminders

If the agent notices it's been longer than the usual order interval (from `patterns.md`):
> "It's been N days since your last delivery — usually you order every M days. Want me to prepare an order?"

This can be set up as a scheduled task via `mcp__nanoclaw__schedule_task`.
