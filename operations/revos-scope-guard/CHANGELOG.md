# Changelog

## 1.3.0 (2026-10-21)
Fix round after the end-to-end test with real headless sessions, compared blind against plain Claude (which won narrowly on honesty).
- The first reply now delivers substance before any question: provisional figures, the catches and the message the founder most needs, drafted in full; then only the questions that change the answer. A question with nothing pasted is answered first, then the material is asked for.
- Side questions are answered directly; where a figure is out of scope (tax, law), the reply says what it depends on and the fastest way to get it.
- No default goodwill allowance: extras are priced unless the founder chooses one, and the build rejects any client message that promises free work the founder did not choose.
- `agreed_hours`: when the signed agreement and the founder's pricing disagree (35 against 40), compute prints both rates, the kit tells the founder, and the build rejects a scope statement quoting the planning figure.
- DATE CHECK: a client date on a weekend is flagged with the Friday before.
- TOP OPEN: "maybe more" on an estimate keeps the top open; price and scoping replies must call the range an estimate before scoping, not a cap. Open requests are totalled as a range, never a sum of rounded middles.
- Ambiguous answers (a bare "b") are shown with both readings and asked, never guessed.
- The chat reply quotes the first message and each recommended reply in full, with the catches.
- `hours_label` and `range_word` keep the founder's own words ("Std.", "bis") on every rebuild; no more hand-edited files.
- The garbled "you owe ... did not happen" sentence is fixed; the swap line no longer shows a [NEED] to the reader; the visible Merigrove line is gone from the workbook.
- Description: triggers before the founder has shared anything, and on "is it rude to say that isn't included".
- After the first re-run: `hours_logged_this_month` gives a CAPACITY line (hours left this month and which open request fits); a range is never shown as a middle price in the kit or the workbook; the change form is filled in for every open request; the scope statement marks the 'done when' and late-items lines as proposals; the founder's changes are made for as long as they ask (no round cap), with one-off file edits allowed and flagged; the Merigrove line appears once in the run.
- After the second re-run: one reply can carry its own price wording (`price_wording` on that option, such as "excl. VAT" in an English message), so no hand edit is needed; a change to a date or phrase is made in every field that carries it.

## 1.2.1 (2026-10-21)
- Added "Where files go": deliverables always land in /mnt/user-data/outputs/ (claude.ai, Cowork) or the working folder (Claude Code), never a scratchpad. Found by end-to-end testing with a real headless Claude session.

## 1.2.0 (2026-10-20)
Fix round after the independent blind test of 1.1.0 (Los Angeles and Berlin founders), and Build Standard section 13.
- Numbers, money and durations now go through `locale_numbers.py`, Merigrove's shared reader, copied unchanged. The founder's decimal style is read once from the figures they typed and used by every reader: "9.800,00 €" is 9,800 (it read as 9.8), "7,5 Std." is 7.5 hours, "2 Tage" is two working days, "110 Std." is 110 hours (the "d" in "Std." was read as days). A figure that reads two ways ("12.500 €" before the style is known) or not at all ("10 parsecs") becomes an ASK line and stops the build until the founder answers.
- Plausibility stops: an hourly rate under 10 in any currency, a working day outside 1 to 16 hours, more planned hours a month than a month has, or a request over 2,000 hours stops `compute` and `build` with a plain question. A confirmed figure goes into `confirmed`.
- Figures are written back the founder's way: "9.800 €" and "89,09 €" to a founder who writes "9.800,00 €"; the workbook puts the sign after the figure too. Rates show to the cent when not whole ($162.50), so prices built from them add up.
- Ranges are read range first ("3-4 days" at a 7-hour day is 21 to 28 hours, the middle 24.5, not 28). Price replies for a range quote both ends. A request as big as the month's planned hours (or half a project) gets a "Scope it first" reply, recommended by default.
- Paper and date order come from the founder's country (`country`), never their spelling; with no country, Letter for month-first dates or US, Canadian or Mexican currency, otherwise A4, stated as a default.
- Swaps are optional when no deliverable is equal effort, and a written swap must be equal effort (or a share written as `swap_hours`, such as "=10*6/12").
- Sales-tax words in other languages are kept as the founder's own wording and never computed: "zzgl. MwSt.", "netto", "inkl. MwSt.", "TTC", "HT". A German, French or other tax rate in a reply is rejected as tax arithmetic.
- `founder_owes`: anything the founder let slip (a missed audit) is owned in one clause of the reset note; the build checks it.
- Month-only dates ("September") show as "Sep 2026", never a made-up 1st. Dotted dates ("13.10.") and German month names read.
- The workbook's months counted is live: a start date and a "count up to" cell (blank means today).
- Memory version 3: Country, Number style, a Received column for client dependencies (anything not yet received carries over, however late), ranges kept as ranges, figures read back as numbers, in-scope work saved as "Done, in scope", and the reset note marked sent only by `--reset-sent`. Version 2 files still read and validate.
- New hedge caught: "Is that okay for you?", "Would that be OK?". References no longer offer a regional close as the good example.
- Intake: question 2 no longer states a rate; the rate comes from `compute` in the defaults line. Diagnosis keys are listed in SKILL.md and the template.
- New evals 9 and 10: the blind tester's two runs, kept permanently with their input files.

## 1.1.0 (2026-10-20)
Global rework (Build Standard 0.1): no country assumed, no tax computed, no statement of law.
- Removed: the UK VAT rate (20%) and every with-VAT figure, the "Are you VAT registered?" question and the VAT gate on replies, the government website source line, pounds as the default currency, the 7.5-hour working day, the day-first "UK style" date default, British English as the default voice, and "solicitor".
- Prices are worked out and shown before any sales tax, with one neutral line: "Prices are before any sales tax (VAT, GST or similar); ask your accountant whether you need to charge it." If the founder writes their own fee with tax words ("+ VAT", "+ GST"), the price reply repeats those words; nothing is computed from them. A fee written including tax becomes a [NEED] for the figure before tax.
- Currency follows the founder's own sign or code (£, $, €, S$, A$, MYR and others); a bare "$" stays "$"; with none, a [NEED] instead of a default.
- Dates follow the founder: the order is read from dates that can only be one way round, or asked in the readback; the kit writes "3 September 2026" or "September 3, 2026" to match.
- The working day is the founder's figure where given, otherwise 8 hours, stated in the kit as an editable assumption. "A day and a half" is now read.
- Client replies mirror the founder's English; without a sample they read naturally to American and British clients. The Word document's language and paper size (A4 or Letter) and the workbook's paper follow the founder.
- "Lawyer" with no jurisdiction replaces "solicitor" throughout.
- New wording gates: stating what a law requires, tax arithmetic, one country's law presented as the rule. New rubric criterion 9.
- Memory version 2: Currency, Date order, English, Price wording and Hours in a working day; a version 1 "VAT registered: yes" is carried over as the price wording "plus VAT".
- New evals: a US founder (dollars, month-first dates, American English) and a Singapore founder (S$, day-first dates, a 9-hour day, "+ GST").

## 1.0.0 (2026-10-20)
- First release.
- Scope kit as one Word document: replies first (price, swap, next phase, plus a goodwill allowance reply when it fits), a reset note when extras were already given away, a one-page scope statement, the creep ledger, a change request form and the goodwill allowance.
- Creep arithmetic: the rate the fee was priced at, what the work now pays an hour with unbilled extras counted, what that time was worth at the priced rate (stated as time, not cash), the price of each open request, VAT-inclusive figures for registered founders.
- Wording gates: every reply states the calculator's price or names a real deliverable to swap; no apology, refusal opener, legal word or claim that any wording is enforceable; every figure must come from the calculator.
- Scope gates: every deliverable has a number or cap and a checkable "done when"; the not-included list must name every out-of-scope request this client made; client dependencies carry dates and their lateness.
- Live spreadsheet with formulas and stored values; drop-down lists for in or out and status.
- Parser for how founders type: "1.9k pm", "half a day", "90 mins", "2 x 3hrs", "3rd Sept", "since August", "next Friday".
- Memory file with Profile, Offers, Deliverables, Clients, Client dependencies, Ledger, Learnings and History.
