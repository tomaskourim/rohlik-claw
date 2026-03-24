---
name: fridge-tracker
description: Estimate current fridge and pantry contents based on delivery history and consumption rates. Use when planning a grocery order, when the user asks what they have at home, or to check if something needs restocking.
---

# Fridge Tracker — Pantry State Estimation

Maintain an estimated view of what the household currently has at home, based on delivery history and category-based consumption rates. The state is stored in `/workspace/group/grocery/fridge-state.md`.

## Consumption Rate Model

Default consumption rates by category (days until fully consumed, assuming typical household usage):

| Category | Days | Examples |
|----------|------|----------|
| Fresh meat/fish | 2-3 | Chicken breast, salmon fillet |
| Deli/ham | 4-5 | Sliced ham, salami |
| Fresh dairy (liquid) | 5-7 | Milk, kefir, fresh cream |
| Yogurt | 7-10 | Individual yogurts, skyr |
| Fresh vegetables | 5-7 | Lettuce, tomatoes, peppers |
| Root vegetables | 14-21 | Potatoes, carrots, onions |
| Fresh fruit | 3-5 | Bananas, berries, grapes |
| Citrus/apples | 10-14 | Oranges, lemons, apples |
| Bread | 3-4 | Fresh bread, rolls |
| Eggs | 14 | Carton of eggs |
| Hard cheese | 14-21 | Parmesan, cheddar blocks |
| Soft cheese | 7-10 | Mozzarella, brie |
| Butter | 21-30 | Butter, margarine |
| Pantry staples | 60-90 | Rice, pasta, flour, canned goods |
| Cooking oils | 60-90 | Olive oil, sunflower oil |
| Spices/condiments | 180+ | Salt, pepper, ketchup, mustard |
| Frozen items | 60 | Frozen vegetables, ice cream |
| Cleaning/household | 60-90 | Detergent, paper towels |
| Drinks (juice) | 5-7 | Fresh juice, smoothies |
| Drinks (shelf-stable) | 30 | UHT juice, sparkling water |

### Rate Priority

When determining the consumption rate for a specific item, use this priority:

1. **Calibrated rate** — Check `## Calibrated Rates` section in `fridge-state.md`. If the specific product has a calibrated rate based on actual reorder intervals, use it. These are the most accurate.
2. **Custom rate** — Check `## Custom Rates` section in `fridge-state.md`. If the user manually corrected an item's consumption, use their override.
3. **Category default** — Fall back to the table above.

### Adjustments

After selecting the rate, apply these adjustments:
- **Household size**: multiply consumption speed by `(people / 2)` (model assumes 2 adults)
- **Known preferences**: if `preferences.md` indicates heavy consumption of a category, reduce the days by 30%
- Read `grocery/household.md` for household size
- Do NOT apply household scaling to calibrated rates — they already reflect actual household consumption

## How to Estimate Fridge State

### 1. Read current state

Read `/workspace/group/grocery/fridge-state.md`. If it doesn't exist, build it from the most recent delivery.

### 2. Calculate remaining percentage

For each item:
```
days_since_delivery = today - delivery_date
consumption_rate = default_days for category (adjusted for household size)
remaining_pct = max(0, (1 - days_since_delivery / consumption_rate) * 100)
```

### 3. Status classification

| Remaining | Status | Action |
|-----------|--------|--------|
| 0-10% | DEPLETED | Definitely needs restocking |
| 10-30% | LOW | Should restock soon |
| 30-70% | OK | No action needed |
| 70-100% | FULL | Recently delivered |

### 4. Update the file

```markdown
# Fridge & Pantry State
Last delivery: YYYY-MM-DD
Last updated: YYYY-MM-DD
Household: N adults, M children

## Fresh (check first)
| Item | Qty | Delivered | Est. Remaining | Status |
|------|-----|-----------|---------------|--------|
| Item | N | Mon DD | ~XX% | STATUS |

## Pantry
| Item | Qty | Delivered | Est. Remaining | Status |
|------|-----|-----------|---------------|--------|

## Frozen
| Item | Qty | Delivered | Est. Remaining | Status |

## Likely Depleted
- Item (delivered Mon DD, ~0%)
```

## When to Ask Questions

Ask the user for clarification when:
- An item's status is uncertain (e.g., you had guests who might have eaten things faster)
- A perishable item is near the boundary between OK and LOW
- The user hasn't ordered in longer than usual (consumption estimates become less reliable after 2x the normal order interval)
- The user mentions cooking a specific meal (update quantities accordingly)

Frame questions concisely for WhatsApp:
> "Before I plan your order — do you still have eggs and milk from last Thursday, or are they gone?"

Do NOT ask about items with clear status (FULL or DEPLETED). Only ask about borderline items (2-3 max per interaction).

## Manual Corrections

When the user says things like "we already ate the chicken" or "we still have plenty of rice":
- Update the specific item in `fridge-state.md`
- Adjust the consumption rate for that item category in future estimates (note in a `## Custom Rates` section at the bottom of the file)

## Restock Alerts

When checking fridge state, if DEPLETED or LOW items are also in `grocery/staples.md`, proactively mention them:
> "You're likely running low on milk and eggs based on your last delivery 5 days ago."

Only alert for staple items — don't alert for one-time purchases.
