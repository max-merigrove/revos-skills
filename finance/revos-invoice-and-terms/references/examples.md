# Worked examples

Illustrative businesses only. Every figure below was produced by the scripts.

## Contents

1. Dublin brand designer: a deposit invoice in a 50/50 plan (first run)
2. Tokyo strategy consultant: whole-yen invoice, end of the following month, a wrong estimate caught (first run)
3. Portland photographer: stage 2 from memory (return run)

## 1. Dublin brand designer, deposit invoice

**Input.** "Aoife Brennan Design, 14 Ranelagh Road, Dublin 6, VAT number IE1234567X, IBAN IE29 AIBK 9311 5212 3456 78. Client: Harbourline Coffee Ltd, 22 Quay Street, Cork. Brand identity project 3,200 euro fixed fee; two rounds of packaging artwork at 450 each; stock photography licences 86.40 (passed on at cost). 50 percent upfront, balance on delivery. VAT 23 percent on the design work but I don't think on the licences. Payment 14 days. Can you do the deposit invoice and the final invoice, and tell me what late payment wording to put on?"

**Diagnosis.** Deposit or stages: a 50/50 split was named. Build stage 1; stage 2 is a preview.

**First reply.** Answers the late payment question (due date only; a fee belongs in agreed terms; the figure comes from her lawyer) and the one-or-two question, reads back the IBAN as passing, shows the draft deposit (EUR 2,564.70) with draft files, uses "no VAT on the licences" as hers and asks her to confirm with her accountant, then asks five questions: last number, VAT on the deposit, when the proposal was accepted and the work runs (the Work covered line needs a date), PO, existing late fee.

**After her answers** (last INV-0018; accountant: same-share VAT on the deposit, no VAT on licences; accepted 30 October, work runs 9 November to 18 December; no PO; no late fee, wants wording):

| Deposit invoice INV-0019 | EUR |
|---|---|
| Brand identity project, fixed fee: 50% of 3,200.00 | 1,600.00 |
| Packaging artwork, two rounds: 50% of 900.00 | 450.00 |
| Stock photography licences, passed on at cost: 50% of 86.40 | 43.20 |
| Subtotal | 2,093.20 |
| VAT 23% on 2,050.00 | 471.50 |
| VAT 0% on 43.20 | 0.00 |
| Amount due | EUR 2,564.70 |

Issued 2 November 2026, due Monday 16 November 2026. Work covered: "Deposit on acceptance of the proposal, 30 October 2026; work runs 9 November to 18 December 2026". Project summary: project total, including VAT, EUR 5,129.40, nothing billed before, this invoice EUR 2,564.70, remaining EUR 2,564.70. Under it, "Still to come: Stage 2: Balance, on delivery, EUR 2,564.70". Terms wording in chat: "Payment: 50% on acceptance and 50% on delivery. Each invoice is due within 14 days of its date." and the paragraph version; the late fee is a chat note (her lawyer gives her the clause), never a gap on the page.

**Why it passes the rubric.** Every figure from the script and read back (1, 2); no open must-have (3); VAT as supplied, never endorsed (4); due date with weekday, work line separate, dated today (5); EUR on every total, IBAN checked (6); the chain adds to the project total exactly (7); no law stated, no fee figure, one Merigrove line (8).

## 2. Tokyo strategy consultant, whole yen

**Input.** "Mori Strategy KK, 2-4-6 Kojimachi, Chiyoda-ku, Tokyo. Client Hoshino Foods KK, 1-8 Nihonbashi, Chuo-ku. Strategy workshop 3 days at 150,000 yen a day, plus workshop materials 33,333 yen. Consumption tax 10 percent on everything, my accountant said. They pay at the end of the month after the invoice date. Bank: Mizuho Bank, Kojimachi Branch, ordinary account 1234567, account name Mori Strategy KK. Last invoice was 2026-0044. Dates like 2026/11/02. Total should come to about 528,000 yen with tax I think."

**Diagnosis.** New invoice. `"date_format": "yyyy/MM/dd"`, terms `end_next_month`, JPY has no smaller unit.

**First reply.** Flags the estimate: the lines give JPY 531,666, not about 528,000, and shows the working so he can see which figure is off. "Workshop materials" alone is too vague, so the description uses his own words: "Workshop materials for the strategy workshop".

| Invoice 2026-0045 | JPY |
|---|---|
| Strategy workshop, three days, 20 to 22 October 2026 (3 x 150,000) | 450,000 |
| Workshop materials for the strategy workshop, bought 19 October 2026 | 33,333 |
| Subtotal | 483,333 |
| Consumption tax 10% (48,333.3 rounded half up to the yen) | 48,333 |
| Amount due | JPY 531,666 |

Issued 2026/11/02, due 2026/12/31 (Thursday). No registration number is printed or invented: a warning says his accountant can say whether one must appear. Bank details print exactly as given; no IBAN check, no invented field.

**Why it passes.** Whole yen everywhere (6); the estimate caught early and resolved by the founder (1, rule 6 of the intake guide); 10% as supplied (4); the term resolved to a date with its weekday (5).

## 3. Portland photographer, return run

**Input.** "shoot's done, send Lumen stage 2", with the memory file attached.

**Memory read.** `memory.py read --plan Lumen` finds the plan LUMEN-2026 (USD 9,000.00 in three stages, 40/40/20), stage 1 issued as INV-2026-013 and paid 10/14/2026, the client's PO LH-4471, the last number INV-2026-014, and one active learning: put the shoot date in the Work covered line.

**Reply, no questions.** "Using your saved details: Cedar and Pine Photography, USD, last invoice INV-2026-014, payment details ending 4821." Invoice INV-2026-015, USD 3,600.00, dated 11/2/2026, due 11/16/2026 (Monday), PO LH-4471, Work covered "Shoot completed 10/30/2026". Project summary: project total USD 9,000.00, billed before INV-2026-013 (9/30/2026, paid 10/14/2026) USD 3,600.00, this invoice USD 3,600.00, remaining USD 1,800.00 for the final images. The register also shows INV-2026-014 to Fernhill Bakery, USD 850.00, due 10/28/2026 and not marked paid, so the reply asks about it in one line rather than staying silent.

**Why it passes.** Zero intake questions on a return run; the saved learning applied at Make; payment details read back, not asked; the chain reads the earlier stage from memory and stops if the project lines no longer give the total that was invoiced (7).
