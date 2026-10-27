# Changelog

## 1.3.0 (2026-10-21)
Fix round after the end-to-end test with real headless sessions (won narrowly against plain Claude on the US founder; South Africa run graded 5/10).
- The first reply answers before it asks: a provisional run on the export plus whatever the founder's message settles, labelled "First read", with the one or two facts that would change it, then checks against what the founder said, then the questions. At most five questions in the whole run, counting every question mark, with no sub-question lists.
- The first read is never kinder than the bank: `provisional_tax` repeats a tax-like payee at the amount the bank last showed (labelled, first read only; the build refuses it), and `without_payer` shows the overdraft week if the largest payer pays nothing more. `OVERDRAWN:` is printed by the compute.
- Checks the founder's claims against the bank: the finder prints the largest payers' last receipts with their references (INV-1063, DEP, BAL) and the days between them, and a `DEPOSITS SEEN` block, so an invoice already paid or a balance still to come is raised in the first reply. Descriptions are kept to 240 characters so wire references survive.
- `DECIDES:` line: the last date the decisive receipt can land before a normal quarter falls below the line (or, already below, before the account is overdrawn). In the first reply, the reading and the chat.
- Three real moves: the re-run date is printed on its own line and is never one of the three unless nothing else exists. New fill moves, each with a figure: the gap to close before the low week, a second payment that can wait, money set aside for a listed payment, the largest receipt to confirm. "Send every invoice" became "collect the money for work in weeks N to M on time", which fits businesses paid upfront.
- Costs of booked work: a regular payment can carry `linked_to` (never held, left out of the safety line), and the safety line names that it leaves them out. Guidance to place such costs only in the weeks the work happens, suppliers and temps on separate lines.
- The safety line is always the compute's figure and basis; a typed figure is "the figure you set", never relabelled.
- Week labels carry the year when the 13 weeks cross into a new year; `"week_labels": "date first"` prints "the week from 21 Nov 2026 (week 6)" in every file.
- The headline names a single payment as the cause only when it alone takes the balance through the line; otherwise it gives the week's money out against money in, with the largest payment named. A client who is neither overdue nor usually late is not chased; a usually-late client is asked to pay on time. Fill moves are concrete (a late payer whose lateness pushes money past the low, a transfer or owner pay to hold, money set aside for a listed payment) before the bare gap; never rent or a bill that keeps the business running. `DECIDES:` is printed only when it changes the answer, a late payer first ("paid on its due date, a normal quarter would ..."). A week-1 breach is explained by how little the balance starts above the line, not by naming one bill. The closing message restates the headline, bad quarter and moves.
- `moves_first` keeps and leads with the moves the founder names; `moves_on_top` prints the moves above the summary in every file. Two moves on one invoice are merged.
- Never an invoice amount or rhythm the founder did not give; quiet months they name are applied; the chat is copied from the final build.
- Side questions (a tax, payroll or legal figure) are answered within scope: what it depends on, what goes into it, and the fastest route to the real figure. Never a bare refusal.
- The chat carries the findings (headline, bad quarter, deciding receipt, three moves with figures, gaps). The Merigrove line appears once, in the closing message only. Never edit the skill's own scripts during a run; contradictions are built on the reading the bank supports, with the other offered.
- Description: triggers before any file is shared, plus "what if two clients pay late" and "cover the quarterly tax and still pay myself".
- Evals: the South Africa scenario now carries `founder_facts`, so the simulated founder answers from the facts its assertions assume.

## 1.2.1 (2026-10-21)
- Added "Where files go": deliverables always land in /mnt/user-data/outputs/ (claude.ai, Cowork) or the working folder (Claude Code), never a scratchpad. Found by end-to-end testing with a real headless Claude session.

## 1.2.0 (2026-10-20)
Fix round after the independent blind test of 1.1.0 (verdict "not ready": output 4/10, experience 5/10).
- Regular payments are grouped by payee first. Bank codes are stripped before grouping (batch and trace numbers, anything after `ID:` or `INDN:`, a wire's sender from `ORIG:`, `CHECKCARD mmdd` and other card prefixes), so a payroll provider's debits with a new batch code every run are one payee. Payroll paid twice a month around two days (debited a day or two before payday) becomes two monthly lines. A payee on one rhythm whose amount moves (a card bill, a cloud bill) is one regular line at its middle figure, said so. A payee seen three or more times is never a one-off.
- A client whose invoices are listed comes out of the usual receipts pattern and the regular clients, so it is never counted twice; the reading names it and the new weekly figure. Invoiced clients are remembered and kept out on the next run, with a `[NEED]` until their open invoices are listed.
- Return runs carry every saved bill and client forward with its rhythm and next date when the new export is too short to show it, and do not count its payments again. Memory rows are keyed by payee and day, so two pay runs to one payee stay two rows. The return-run question asks for the export since last time (or three months) and the open invoices.
- Seasonal income: the finder flags months where money in moves by more than half; question 3 asks which months are quiet; `months_off` and `month_factor` shape the pattern; the reading names the months the pattern averages and says plainly when the month the founder asked about runs past the 13 weeks.
- The three moves: hold, in order, a transfer to savings, owner pay, then spending not tied to booked work. Pay, payroll taxes, payments tied to a booked job (`linked_to`) and costs needed to deliver booked work (`revenue_linked`, with an `end`) are never offered. Moves print in date order. The "largest single receipt" move no longer picks the usual pattern.
- Founder-typed figures read through `scripts/locale_numbers.py` (Build Standard section 13): "R412 000", "about R41k", "1.200,50 €", "₹2.4 lakh"; the decimal style is detected once; a figure that reads two ways asks one question; another currency stops; plausibility stops ask before a misread figure is used. Figures are written back the way the founder writes them (R729 891). Paper size (Letter or A4) and, where nothing else settles it, the date order come from the founder's country.
- Generic payroll-tax and social-charge acronyms route a line to the tax-like list for the founder to supply; nothing is computed from them. A municipal or short-coded line is flagged to ask.
- The note gate and `check_copy.py` refuse comfort words ("healthy", "safe", "plenty"), statements of what a law or an authority requires, and claims about other businesses. The note gate reads figures in the founder's own style.
- Readable labels in the readback and reading; tax-like payments collapsed by payee, at most five lines; no nested brackets.
- Evals: the blind tester's two runs and the return run are permanent evals 10 to 12 with their own fixtures; 69 new script tests.

## 1.1.0 (2026-10-20)
Global rework (Build Standard section 0.1).
- Removed: the UK tax calendar and its date checker (`scripts/uk_calendar.py`, `scripts/check_dates.py`, `references/uk-tax-dates.md`), every tax rule, deadline, weekend and bank holiday adjustment, the tax-type and business-type inference from tax authority references, the payment plan line naming a tax authority, the pound and day-first defaults, and UK-only payee lists.
- Tax, payroll taxes and other government payments are now founder-listed known payments (what, amount, date or rhythm), labelled founder supplied with who gave the figure, never derived. Payments in the export that look like tax are shown as seen and not projected; a regular line the founder names as tax is replaced, not doubled, and saved as ignored.
- Bank reader: the generic column mapper and running-balance check stay the backbone. Added Chase, Bank of America, Wells Fargo (no header), American Express (charges shown as a plus; asks because a card is not a bank account), Mercury, DBS and OCBC (ledger balance in the preamble; descriptions on a second row), Commonwealth Bank and ANZ (no header) and Wise (several currencies). Layouts no published source confirms are marked not verified.
- Dates: day first or month first read from the data; asked once (`--dates`) when the data cannot tell, and saved. Founder-typed dates follow the same order; an ambiguous one stops with a question. Output dates print in the founder's order.
- Currency: from the file, a labelled guess from the layout, or one question; never a default. Figures, workbook formats and the copy check follow it.
- Twice-monthly payments (the 15th and month end) found as two monthly lines.
- Intake still five questions in at most two turns: the two UK tax questions became one known-payments question and one locale question, asked only when the file does not settle it.
- Banned patterns: stating what a law requires, computing tax, assuming a country. `check_copy.py --currency` flags a foreign currency sign.
- Evals: added a US founder (Chase, dollars, month first) and a Singapore founder (DBS, Singapore dollars); all nine runs redone; baseline re-run on the US founder.

## 1.0.0 (2026-10-20)
- First release.
- Bank export reader for Barclays, HSBC (with and without a header row), Lloyds, Lloyds Commercial Banking, NatWest, Monzo Business, Starling, Tide and Revolut Business, plus any export with recognisable column names. Split and signed amounts, CR and DR markers, pending and declined rows, repeated header rows, overlapping exports, preambles, comma decimals and every common date form. Every row checked against the running balance where there is one; one question, saved to memory, where a layout cannot be proved.
- Regular bills, regular clients, tax payments, everyday spending, one-offs and transfers to savings found in the export, so the founder corrects a list rather than recalls one. Tax periods and business type inferred from tax payments (removed in 1.1.0).
- 13 weeks rolled week by week in a normal and a bad quarter (money in 20 per cent lower and 15 days later; payment plan failures), with the arithmetic asserted every week.
- A single-country tax calendar with an independent date checker (removed in 1.1.0).
- Safety line, first breach week, lowest point and bad-quarter runway against an 8-week minimum; three dated moves tied to named lines.
- Commitment test for a hire or big spend: yes, a later start date, or not yet.
- Workbook with live formulas (openpyxl) and a CSV fallback; one-page reading as .docx with no extra libraries.
- Memory: bank layout, regular items, client payment habits, tax setup (replaced in 1.1.0), last forecast; forecast against actual after each run, and a proposed bad-quarter change after three.
