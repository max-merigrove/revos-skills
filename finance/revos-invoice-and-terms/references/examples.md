# Worked examples

Illustrative businesses only. Every figure below was produced by the scripts.

## Contents

1. Austin brand designer: a deposit invoice in a 50/50 plan (first run)
2. Chicago strategy consultant: end of the following month, a wrong estimate caught (first run)
3. Portland photographer: stage 2 from memory (return run)

## 1. Austin brand designer, deposit invoice

**Input.** "Rosa Delgado Design LLC, 418 Congress Ave, Suite 210, Austin, TX 78701, EIN 12-3456789. Bank for ACH: Lone Star Example Bank, routing 123456789, checking account 000123456789, account name Rosa Delgado Design LLC. Client: Bluebonnet Coffee Roasters Inc., 2200 S Lamar Blvd, Austin, TX 78704. Brand identity project $3,200 fixed fee; two rounds of packaging artwork at $450 each; printed packaging samples $186.40 (passed on at cost). 50 percent upfront, balance on delivery. My accountant said sales tax 8.25 percent on the printed samples, and I don't think the design work is taxed. Payment 15 days. Can you do the deposit invoice and the final invoice, and tell me what late payment wording to put on?"

**Diagnosis.** Deposit or stages: a 50/50 split was named. Build stage 1; stage 2 is a preview.

**First reply.** Answers the late payment question (due date only; a fee belongs in agreed terms; the figure comes from her lawyer) and the one-or-two question, reads back the ACH details as she gave them, shows the draft deposit (USD 2,150.89) with draft files, uses "sales tax only on the printed samples" as hers and asks her to confirm with her accountant, then asks five questions: last number, sales tax on the deposit, when the proposal was accepted and the work runs (the Work covered line needs a date), PO, existing late fee.

**After her answers** (last INV-0018; accountant: the same share of the sales tax on the deposit, design work untaxed; accepted 10/30/2026, work runs 11/9/2026 to 12/18/2026; no PO; no late fee, wants wording):

| Deposit invoice INV-0019 | USD |
|---|---|
| Brand identity project, fixed fee: 50% of 3,200.00 | 1,600.00 |
| Packaging artwork, two rounds: 50% of 900.00 | 450.00 |
| Printed packaging samples, passed on at cost: 50% of 186.40 | 93.20 |
| Subtotal | 2,143.20 |
| Sales tax 8.25% on 93.20 | 7.69 |
| Amount due | USD 2,150.89 |

The two design lines show a dash in the Tax column; the samples line shows "Sales tax 8.25%", marked "supplied by you" in the register. Issued November 3, 2026, due Wednesday, November 18, 2026. Work covered: "Deposit on acceptance of the proposal, 10/30/2026; work runs 11/9/2026 to 12/18/2026". Project summary: project total, including sales tax, USD 4,301.78, nothing billed before, this invoice USD 2,150.89, remaining USD 2,150.89. Under it, "Still to come: Stage 2: Balance, on delivery, USD 2,150.89". Letter paper, her EIN under her address, and How to pay with the bank, routing number and checking account exactly as given. Terms wording in chat: "Payment: 50% on acceptance and 50% on delivery. Each invoice is due within 15 days of its date." and the paragraph version; the late fee is a chat note (her lawyer gives her the clause), never a gap on the page.

**Why it passes the rubric.** Every figure from the script and read back (1, 2); no open must-have (3); sales tax as supplied, on the samples only, never endorsed (4); due date with weekday, work line separate, dated today (5); USD on every total, ACH details read back (6); the chain adds to the project total exactly (7); no law stated, no fee figure, one Merigrove line (8).

## 2. Chicago strategy consultant, end of the following month

**Input.** "Whitfield Strategy Group LLC, 233 S Wacker Dr, Suite 4400, Chicago, IL 60606. Client Lakeshore Foods Inc., 1801 N Water St, Milwaukee, WI 53202. Strategy workshop 3 days at $4,500 a day, October 20 to 22, plus workshop materials $833.33 I bought October 19. No sales tax on this, my accountant said. They pay at the end of the month after the invoice date. ACH: Example Prairie Bank, routing 111222333, account 5566778899, account name Whitfield Strategy Group LLC. Last invoice was 2026-044. Total should come to about $14,000 I think."

**Diagnosis.** New invoice. Terms `end_next_month`; no tax lines, as his accountant said; his figure goes in `quoted_total` so the script checks it.

**First reply.** Flags the estimate: the lines give USD 14,333.33, not about 14,000, a gap of USD 333.33, and shows the working so he can see which figure is off. The invoice stays DRAFT on that question (default: the lines) and on whether Lakeshore needs a PO. "Workshop materials" alone is too vague, so the description uses his own words: "Workshop materials for the strategy workshop".

**After his answers** (the lines are right, he had guessed the materials low; no PO):

| Invoice 2026-045 | USD |
|---|---|
| Strategy workshop, three days (3 days x 4,500.00) | 13,500.00 |
| Workshop materials for the strategy workshop | 833.33 |
| Subtotal | 14,333.33 |
| Amount due | USD 14,333.33 |

Issued November 3, 2026, due Thursday, December 31, 2026. Work covered: "Strategy workshop 10/20/2026 to 10/22/2026; materials bought 10/19/2026". No tax line and no tax number is printed or invented; the default line says to ask his accountant whether he needs to charge sales tax. Bank details print exactly as given; no invented field.

**Why it passes.** The estimate caught early and resolved by the founder, never quietly matched (1, rule 6 of the intake guide); no tax lines, as supplied (4); the term resolved to a date with its weekday (5); USD on every total (6).

## 3. Portland photographer, return run

**Input.** "shoot's done, send Lumen stage 2", with the memory file attached.

**Memory read.** `memory.py read --plan Lumen` finds the plan LUMEN-2026 (USD 9,000.00 in three stages, 40/40/20), stage 1 issued as INV-2026-013 and paid 10/14/2026, the client's PO LH-4471, the last number INV-2026-014, and one active learning: put the shoot date in the Work covered line.

**Reply, no questions.** "Using your saved details: Cedar and Pine Photography, USD, last invoice INV-2026-014, payment details ending 4821." Invoice INV-2026-015, USD 3,600.00, dated 11/3/2026, due 11/17/2026 (Tuesday), PO LH-4471, Work covered "Shoot completed 10/30/2026". Project summary: project total USD 9,000.00, billed before INV-2026-013 (9/30/2026, paid 10/14/2026) USD 3,600.00, this invoice USD 3,600.00, remaining USD 1,800.00 for the final images. The register also shows INV-2026-014 to Fernhill Bakery, USD 850.00, due 10/28/2026 and not marked paid, so the reply asks about it in one line rather than staying silent.

**Why it passes.** Zero intake questions on a return run; the saved learning applied at Make; payment details read back, not asked; the chain reads the earlier stage from memory and stops if the project lines no longer give the total that was invoiced (7).
