# Changelog

## 1.3.0 (2026-11-02)

End-to-end round 2 fixes (Johannesburg 8, Austin 9; the comparator preferred plain Claude, which put the founder's late fee wording on the invoice).

- The founder's own late fee: when they have decided on their own fee and said it, it stays off any invoice for work the client agreed before it existed, and goes, in their words with nothing added, into a "with your late fee" version of their payment terms for contracts from now on, shown in the first reply with one line to check with their lawyer. Still never suggested, never called standard.
- A total the founder quoted that the lines do not give is an open question: the invoice stays DRAFT until they confirm (`confirmed: ["quoted_total"]` or the figure removed).
- A tax view the founder attributes ("my bookkeeper said") is said back that way. Line descriptions stay in the founder's words; no added dates or detail.
- Tighter page: top and bottom margins reduced, notes sit in the How to pay block, so an invoice with notes and the bank-change line still fits one page on Letter and A4.

## 1.2.0 (2026-11-02)

End-to-end round 1 fixes (Johannesburg graded 6.5; Austin 8.5; the comparator preferred the skill).

- Number style follows how the founder typed: "R 14 500,00" prints as 14 500,00 (space grouping, non-breaking), not 14.500,00; mixed figures take the first figure with decimals and a DEFAULT line says so. `grouping` and `print_decimal` let a founder ask for another style. Every reader (verify, register, memory) uses the plan's own format, so chat and file match.
- Draft state is honest: questions still open in the first reply go in `"open_questions"`, which keeps the files DRAFT with the draft line; with none, the first reply is READY.
- Fewer questions: a self-correction in the message ("no wait 21 days") is the answer; "I think" facts are printed with a check note; register findings are stated defaults; at most two questions when the founder says they are busy.
- The closing line appears once, in the first reply that delivers READY files; copy blocks are proofread and shown once.
- `memory.py write --no-payment` leaves payment details out and says so in the file.

## 1.1.0 (2026-11-02)

Blind-test fix round (report `evals/BLIND_TEST_REPORT_v1.0.md`).

- A line with no tax: `"tax": "none"` on a line (or `"default": "none"`) leaves it untaxed and prints a dash in the Tax column; a null tax beside untaxed lines is said out loud as a DEFAULT. The project total label and the terms wording name only taxes with a rate above 0, so "No sales tax 0%" and "Prices are before No sales tax" can no longer appear. Intake guide maps "tax on some lines only".
- One-page stage invoices: lines that are all shares of the project drop the Qty and Unit price columns; "Remaining after this invoice" carries no stage names; the later stages sit in a small "Still to come" list (checked to add to the remainder); How to pay, the reference, the due date and the terms sit in one block. The plain PDF writer wraps every column. A regression test holds the standard three-stage example to one page.
- The founder's own register: `register.py read` maps common headings (Number, Client, Date, Amount, Paid?, Status, Due), reads amounts in the founder's style ("R 21 275.00"), reads "paid 14/10" and "15 Aug", lists blank numbered rows as gaps, raises duplicate-looking unpaid invoices, and says what it did and did not understand. `register.py build` no longer crashes on a row with no due date and adds the overdue invoice being chased.
- `register.py update --paid` reads the date in the founder's order (from `--country` or the saved country), echoes it with the month written out, and stops on an ambiguous date when the country is unknown.
- The Check step works as written: `verify_invoice.py --preview` checks previews; `register.py build` stores the OUTSTANDING and OVERDUE figures in `history.json` for `check_copy.py --also`; preview plans are passed with `--also`; the founder's own quoted words are not checked as our copy.
- Estimate flag compares the founder's figure with the subtotal and the total and prints both. `ingest.py` reads "R9 800" and "R 38 500.00", keeps tax, company, account, branch, phone and postcode numbers out of the amounts, lists percentages separately, keeps invoice prefixes ("INV-0187 (or 0188?)"), and ignores only the injected sentence, not the whole line.
- Standalone: the register's Settings sheet no longer carries a "Made with" row (the credit stays in file properties); the terms wording carries no notes to the founder and no gaps (those come out as `CHAT:` lines); the closing line no longer uses an internal term.
- Lighter first run: previews only on request and as PDF only (the Word copy stays in the scratch folder for the check); terms wording in chat, the Word page only on request. Memory read-back takes the last four of the account number or IBAN, never the SWIFT.
- Description: adds "bill a client", "invoice my monthly retainer" and "credit note".
- Evals: Johannesburg (WhatsApp, own CSV register, overdue) and Austin (30/40/30, tax on one line, US dates) added as permanent evals with fixtures and sample runs; 57 new regression tests.

## 1.0.0 (2026-11-02)

First build, Wave 2.

- Invoice engine (`invoice_calc.py`): lines, line and invoice discounts, tax per category exactly as the founder supplies it, rounding half up to the currency's smallest unit, totals, amounts paid, balance due, deposit and stage plans with a project summary, credit notes, overdue reminder facts, and a second, independent recomputation in exact fractions that stops on any difference.
- Read-back (`verify_invoice.py`): reads the finished Word file's tables and the PDF text and re-checks every tie-out; a tampered figure or a `[NEED]` on a READY invoice fails it.
- Word and PDF (`build_invoice.py`, `make_pdf.py`, `docx_lite.py`): LibreOffice when present, otherwise a plain standard-library PDF; labels in any language from a checked label set.
- Numbering (`next_number.py`), dates and terms (`dates.py`), IBAN check digits (`iban_check.py`), the register workbook with live formulas or a CSV (`register.py`), payment terms page (`terms_block.py`), memory (`memory.py`), copy checks (`check_copy.py`), paste reader with planted-instruction detection (`ingest.py`).
- Working defaults for review (Max), recorded in `references/` and never presented as market facts or law: 14 days from the invoice date when nothing is said; a stage share applies to every line in proportion, the last stage takes the remainder; tax rounded once per category, half up; the vague description list; the must-have and should-have split in `references/checklist.md`; a late fee only from the founder's own agreed terms; a reminder's pay-by date a week out when the founder gives none; credit notes in the founder's own number sequence.
- `locale_numbers.py` copied unchanged from the standard library; its tests in `evals/test_locale_numbers.py`.
