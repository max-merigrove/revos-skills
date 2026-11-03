# Method

How the invoice is built and why. Every rule here is a working default the founder can change, not a market fact or a legal rule. Where a decision depends on the founder's jurisdiction, the founder supplies it from their accountant or lawyer and it is stored as "supplied by you".

## Contents

1. The completeness frame
2. Numbering
3. Dates: issue, work covered, due
4. Payment terms types
5. Lines, discounts and rounding
6. Tax as supplied
7. Money that cannot be misread
8. Payment details
9. Late payment: three paths
10. Corrections
11. The register
12. Layout
13. If code cannot run

## 1. The completeness frame

An invoice is payable without a question when it answers seven things: who (both parties, and who actually pays), what (the work, in words a stranger would understand, with its dates), when (issued, and the period covered), how much (lines, totals, tax as supplied, balance due), how to pay (account details or a link, and the reference to quote), by when (a calendar date), and reference (their PO or reference, your project or proposal). The must-have and should-have list is in `checklist.md`. Two items most guides leave out and most accounts teams reject on: the PO or reference, and the payer (the person who commissioned the work is often not the person who pays).

Anything a particular country adds (registration numbers, set wording, a language, an electronic format) comes from the founder's accountant and goes in the required wording box, printed verbatim on every invoice.

## 2. Numbering

`next_number.py` carries the founder's own format on: prefix, separators, a year if there is one, zero padding (`INV-0018` to `INV-0019`, `KIC/2026/031` to `KIC/2026/032`). Where the number carries a year and the invoice is dated in a later year, it asks whether to restart the count (default: restart). With no previous number it starts at `0001` and asks for the last number, because the sequence should carry on.

A number is used only when an invoice is issued. Previews of later stages carry no number. A voided number stays in the register with its reason (`register.py update --void "INV-0020=sent to the wrong client"`) and is never reused. Whether a particular place requires gap-free numbering is the accountant's call; the register records every gap with its reason so they can see it.

## 3. Dates: issue, work covered, due

- **Issue date:** the day the invoice is made. Never earlier. A founder who asks for an earlier date ("date it 30 September so it fits the quarter") gets today's date and one line: an invoice date is the day it is issued; the dates the work was done go on their own line. A date more than 30 days ahead is a plausibility stop.
- **Work covered:** the date or period of the work, on its own line ("14 and 15 September 2026", "20 to 22 October 2026", "shoot completed 30 October 2026"). For a deposit, the stage and its trigger ("Brand identity project: deposit on acceptance").
- **Due date:** always a calendar date with its weekday, whatever the term ("Monday 16 November 2026", "2026/12/31 (Thursday)"). A due date on a day the founder named as a day off, or a holiday they named, is shown with a warning and not moved. No public holiday calendar is built in.

## 4. Payment terms types

`dates.py` turns each into one date:

| Type | Field | Due |
|---|---|---|
| `days` | days | issue date plus N days |
| `eom_plus` | days | end of the invoice month plus N days |
| `end_next_month` | none | last day of the month after the invoice month |
| `next_month_day` | days (the day) | that day of the following month |
| `on_receipt` | none | the issue date |
| `fixed` | date | that date |
| `in_advance` | start (and days before) | before the work starts, never before the issue date |

Default when the founder, their proposal and their last invoice are all silent: 14 days from the invoice date, said out loud. A client's own stated terms ("we pay at the end of the month after the invoice") override. Practitioners commonly use 7 or 14 days for solo work and 30 for larger corporate clients (anecdotal practitioner advice; never quote it as a benchmark).

## 5. Lines, discounts and rounding

- Each line: description in the founder's words, quantity (default 1), unit price, amount = quantity times unit price, rounded half up to the currency's smallest unit.
- A line discount (percent or amount) comes off that line. An invoice discount comes off the subtotal before tax and is shared across the lines in proportion, largest remainder, so it adds back exactly.
- Tax is worked out on each tax category's net total and rounded once (half up). A founder whose accountant prefers per-line rounding sets `"rounding": "line"`. The method is written in the register's Settings sheet with "confirm the rounding method with your accountant".
- `invoice_calc.py` recomputes every invoice a second way (exact fractions, integer rounding) and stops on any difference. The model never adds, rounds or counts.

## 6. Tax as supplied

The tax setup is a small table the founder fills: each category's name in their words (VAT, GST, sales tax, consumption tax), its rate from their accountant, which lines belong to it, their own registration number, and any wording for lines treated differently, printed verbatim. Default with nothing said: no tax lines and the neutral line. The skill never offers a rate, never says a line is exempt or zero rated, never says a treatment is right, and never agrees with a founder's tax belief: it uses what they said, marks it supplied by them and asks them to confirm with their accountant.

Prices including tax are accepted only when the founder says so and gives the rate; the net is worked back per line and the chat says "prices entered including tax as you said; confirm with your accountant". A rate above 30 or below 0 is a plausibility question, not a legal view.

## 7. Money that cannot be misread

- The currency code is printed on every total line ("EUR 2,564.70", "2.200,00 EUR", "JPY 531,666"), even where the founder uses a symbol.
- Smallest units follow the currency: none for JPY, KRW, VND, CLP and similar; three for KWD, BHD, OMR, JOD, TND; two otherwise. This is currency arithmetic, not a country rule.
- Figures are written in the founder's style: 1,234.56, 1.234,56, or Indian grouping (2,11,770.00) for founders in India or who write that way.
- One currency per invoice. No exchange rate is fetched or applied.

## 8. Payment details

Free fields with the founder's own labels (account name, bank, account number, IBAN, BIC or SWIFT, routing, sort code, IFSC, branch, account type): the skill invents no field list per country. An IBAN is checked by its own check digits (`iban_check.py`); a failure keeps the invoice in DRAFT, the IBAN is not printed, and the founder is asked to re-read it from their bank. Payment details are read back in chat on every run. A change from the remembered details is confirmed in one line before printing. The optional line "We confirm any change to our bank details by phone" (`"confirm_changes_line": true`) protects their clients from payment redirection fraud. The payment reference is the invoice number unless the founder says otherwise.

## 9. Late payment: three paths

- **None (default):** the due date and the reference. Most invoices are paid on that.
- **Agreed:** the founder's contract or proposal already states a fee. It is printed exactly as they give it, with "As agreed in <document and date>". No document named, no fee on the invoice: a fee that first appears on an invoice may not be one the client agreed.
- **New:** the founder wants to start charging one. The skill never suggests a figure and never says what is allowed; the figure, and whether it can be charged where they and the client are, come from their lawyer. The terms block carries `[NEED: your late fee, from your lawyer]` and this invoice stays on the first path.

The skill never computes interest or a fee on an overdue amount.

## 10. Corrections

An issued invoice is never edited. A full error: a credit note (`"mode": "credit_note"`, the original lines, `credits` naming the original number and date and the reason) and a new invoice with the next number. A partial error: a credit note for the difference. Both are numbered in the founder's sequence unless they say they use a separate one. One line: "Ask your accountant whether to correct with a credit note and a new invoice, as I have, or another way where you are."

## 11. The register

`Invoice register.xlsx` keeps every document: number, type, client, project, dates, currency, net, tax, total, paid, balance (formula), status, paid date, days late (formula), PO and file name. Billing plans list every stage with its trigger, total and invoice number once issued. Gaps and voids keep each unused number with its reason. Settings record the business details, number format, terms, the tax setup with "supplied by you" and the date, rounding, and "not tax or accounting advice". The founder fills the yellow cells (Paid, Status, Paid date) or tells the skill on the next run ("Lumen paid the deposit on the 14th"), and `register.py update` marks it. Only money in the account counts as paid.

## 12. Layout

Plain and well set: black on white, one font family (the founder's if given), their logo and one accent colour only if supplied, never invented. The title, the From block beside the number and dates, Bill to beside Work covered, the lines, the totals with Amount due as the largest figure, the project summary for stages, How to pay with the due date repeated, Terms, Notes verbatim, and a footer with the business name and page numbers. Labels come in the invoice language (`intake-guide.md` section 5). The file properties carry "Made with Merigrove Invoice and Terms Builder"; nothing else from Merigrove appears on the invoice.

## 13. If code cannot run

Say so in one line. Work each line in a table (quantity, unit price, amount), then each tax category on its net, then totals, writing every step so the founder can check it; give the due date with its weekday from a calendar; deliver the invoice as a copy block with "check the sums before sending". Never call it ready.
