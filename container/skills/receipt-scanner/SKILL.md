---
name: receipt-scanner
description: Process store receipt images sent via WhatsApp. When a photo of a grocery receipt from any shop (Albert, Lidl, Tesco, Billa, Kaufland, Penny, etc.) is received, extract purchased items and update fridge-state.md so the fridge tracker reflects what was bought outside of Rohlik. Use whenever an image message contains a receipt or the user says they bought groceries elsewhere.
---

# Receipt Scanner — Non-Rohlik Purchase Tracker

When the user sends a photo of a grocery store receipt from a shop other than Rohlik, extract the purchased items and update the fridge state so the household inventory stays accurate regardless of where groceries were bought.

## When to Activate

Trigger this workflow when:
- An image message contains a store receipt (look for store name, item list with prices, total)
- The user says something like "bought these at Albert" or "picked up groceries at Lidl" alongside an image
- The user asks to manually log a non-Rohlik purchase

If the image is unclear or you're not sure it's a receipt, ask:
> "Is this a store receipt? I can extract the items and update your fridge inventory."

## Receipt Processing

### 1. Read the receipt image

Examine the image carefully. Czech grocery receipts typically contain:
- **Store name** at the top (Albert, Lidl, Tesco, Billa, Kaufland, Penny, Globus, Makro, etc.)
- **Item lines** — product name, quantity, unit price, total price
- **Date and time** of purchase
- Discounts, loyalty card savings
- VAT breakdown and total

Extract:
- **Store name**
- **Purchase date** (from the receipt, not today's date)
- **Each item**: name, quantity (default 1 if not listed), price in CZK

### 2. Normalize items to fridge-tracker categories

Map each receipt item to one of the fridge-tracker consumption categories:

| Category | Days | Receipt clues |
|----------|------|---------------|
| Fresh meat/fish | 2-3 | kuře, kureci, vepřové, hovězí, ryba, losos, filé |
| Deli/ham | 4-5 | šunka, salám, párek, klobása |
| Fresh dairy (liquid) | 5-7 | mléko, kefír, smetana |
| Yogurt | 7-10 | jogurt, skyr, tvaroh |
| Fresh vegetables | 5-7 | salát, rajče, paprika, okurka, cuketa |
| Root vegetables | 14-21 | brambory, mrkev, cibule, česnek |
| Fresh fruit | 3-5 | banán, jahody, hroznové, maliny |
| Citrus/apples | 10-14 | pomeranč, citrón, jablko, grep |
| Bread | 3-4 | chléb, rohlík, pečivo, bageta |
| Eggs | 14 | vejce |
| Hard cheese | 14-21 | eidam, parmazán, gouda, čedar |
| Soft cheese | 7-10 | mozzarella, brie, hermelín, žervé |
| Butter | 21-30 | máslo, margarín |
| Pantry staples | 60-90 | rýže, těstoviny, mouka, konzerv, luštěniny |
| Cooking oils | 60-90 | olej, olivový |
| Spices/condiments | 180+ | sůl, pepř, kečup, hořčice, koření |
| Frozen items | 60 | mražen, zmrzlina |
| Cleaning/household | 60-90 | prací, ubrousky, toaletní papír |
| Drinks (juice) | 5-7 | džus, šťáva, smoothie |
| Drinks (shelf-stable) | 30 | perlivá voda, minerálka, limonáda |

Skip non-food items that don't fit any category (bags, batteries, magazines, etc.) unless they fall under cleaning/household.

### 3. Confirm with the user

Before updating the fridge state, present a summary for confirmation:

> "I see a receipt from **Albert** (March 23, 2026):
> - Milk 1.5% x2 — dairy
> - Chicken breast 500g — fresh meat
> - Bananas 1kg — fresh fruit
> - Pasta 500g — pantry
> - Toilet paper x4 — household
>
> Should I add these to your fridge tracker?"

Keep the confirmation concise — group items by category, skip prices (the user already knows what they paid). If many items (10+), summarize by category counts instead of listing each item.

If the user says "just add it" or has previously indicated they don't need confirmation, skip this step in future interactions.

### 4. Update fridge-state.md

Read `/workspace/group/grocery/fridge-state.md` and add the extracted items.

For each item:
- **Delivered date** = the receipt date (not today's date, unless the receipt date is unreadable)
- **Quantity** = as shown on receipt
- **Est. Remaining** = 100% (freshly bought)
- **Status** = FULL

Place items in the correct section (Fresh, Pantry, Frozen) following the existing file format:

```markdown
| Item | Qty | Delivered | Est. Remaining | Status |
|------|-----|-----------|---------------|--------|
| Chicken breast (Albert) | 1 | Mar 23 | ~100% | FULL |
```

Add the store name in parentheses after the item name so the user can distinguish Rohlik deliveries from other shops.

If an item already exists from a recent Rohlik delivery with OK/FULL status, don't duplicate it — the user likely bought extra. Instead, increase the estimated remaining percentage or note the additional quantity.

### 5. Update delivery-log.md

Append a compact entry to `/workspace/group/grocery/delivery-log.md`:

```markdown
### Mar 23 — Albert (receipt scan)
Items: 5 | Total: ~320 CZK
Categories: dairy (2), meat (1), fruit (1), pantry (1), household (1)
```

Mark it as "receipt scan" to distinguish from Rohlik deliveries.

## Edge Cases

- **Blurry or partial receipt**: Extract what you can, ask about items you're unsure of. "I couldn't read 2 items on the receipt — can you tell me what they were?"
- **Non-Czech receipt**: The category mapping still applies, just the product names will be in a different language. Adapt accordingly.
- **Receipt without date**: Use today's date and note the assumption.
- **Multiple receipts in one image**: Process each separately, ask which store if unclear.
- **User sends a photo that isn't a receipt**: Don't force receipt processing. If it's clearly not a receipt (a meal photo, a product photo), respond normally.

## What NOT to Do

- Do NOT update `staples.md` or `preferences.md` from receipt data — those files track Rohlik ordering patterns specifically. Non-Rohlik purchases inform fridge state only.
- Do NOT try to find matching Rohlik product IDs for receipt items.
- Do NOT suggest reordering receipt items on Rohlik unless the user asks.
- Do NOT update `spending.md` with non-Rohlik purchases — that file tracks Rohlik spending only.
