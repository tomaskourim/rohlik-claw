# Scheduled task prompt

Paste this to the assistant to create the recurring ingest task. Cadence:
every Monday at 03:00 (`0 3 * * 1`). A weekly run picks up whatever was
delivered during the week in one batch, and is a no-op when nothing new has
arrived.

---

Založ opakovanou úlohu, která každé pondělí ve 3:00 ráno doplní databázi nákupů.

Postup úlohy:

1. Zjisti, které objednávky už jsou v databázi:
   `python3 ~/.claude/skills/purchase-db/query.py "SELECT order_id FROM orders"`
2. Načti `mcp__rohlik__get_order_history` a vyber jen doručené objednávky,
   které v databázi chybí.
3. Pro každou chybějící zavolej `mcp__rohlik__get_order_detail` a sestav JSON
   podle skillu `purchase-db` — jedna objednávka celá, se všemi položkami,
   `product_id`, `name`, `category`, `unit`, `quantity`, `unit_price`,
   `line_total`.
4. Nahraj ji: `python3 ~/.claude/skills/purchase-db/ingest.py <<'JSON' … JSON`
5. Sleduj stderr. Když ingest hlásí varování o nesedícím `line_total`, oprav
   parsování a objednávku nahraj znovu — přepsání je bezpečné.
6. Když nepřibyla žádná objednávka, nepiš do skupiny nic.
7. Když nějaká přibyla, napiš krátké shrnutí: kolik objednávek, kolik položek,
   celková částka, a jestli se u některé pravidelně kupované položky výrazně
   změnila jednotková cena oproti minulému nákupu.

Databázi needituj ručně ani přes Write — vždy jen přes `ingest.py`.
