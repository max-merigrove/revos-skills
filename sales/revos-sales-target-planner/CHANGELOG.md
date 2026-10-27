# Changelog

## 1.3.0 (2026-10-21)
Fix round after the end-to-end test with headless founder sessions (1.2.1 won clearly against plain Claude; grades 7 and 8 out of 10).
- Value before questions: the first reply always answers the founder's question with figures (the plan on what they gave plus labelled defaults, or the four-line chain and the four places a month breaks when no figures are given), then asks only the questions that would move a figure, each with what it would change.
- Two readings shown, never guessed: a yearly figure that may be a run rate or money by a date, or two call lengths, is planned both ways with both headlines side by side; the workbook follows the reading the founder's words support best, said out loud.
- The question beside the plan (a setter, a hire, hours) is answered from the plan; where a figure is out of scope, what it depends on and the fastest route to the real figure are given, never a bare refusal.
- Conflicts in the founder's own material are named early (figures that disagree, counts that cannot both be true, dates that do not match).
- The fix order is ranked from this plan's Scenarios rows (fewest held calls, then bookings) instead of a fixed list, so it never contradicts the table or the chat.
- Where nothing breaks but the plan needs more leads than today, section 4 names lead volume as the gap to watch, not the thing that breaks.
- `target_plan.py` prints `CHAT-BREAKS`, `CHAT-BIGGEST-LEVER`, `CHAT-FIRST-ACTION` and `CHAT-CLOSING` lines that the chat copies word for word: the chat can no longer say a gap breaks when the workbook says nothing does, or say "Monday" for a Thursday.
- The Merigrove line appears once, as the last line of the first delivery message, and again only if what breaks first changes.
- Rates are named in chat as the plan names them; the share of held calls that get a proposal is the offer rate, never a close rate.
- Description: discovery calls a week, "do I need a setter or can I hit my target myself", and a line to trigger before any numbers or files are shared.
- Rubric criterion 9 (value first, chat agrees with the file); 10 new script tests.

Second pass inside 1.3.0, after the first 1.3.0 end-to-end rerun (still won clearly; grades 6 and 8 out of 10):
- The Plan sheet opens with the headline, the first action and the weekly pace together, and section 9 gives six weeks of pace scaled to the days the founder takes calls and their dated days off, so layout requests no longer lead to hand edits that drop the calculated values.
- New chat lines: `CHAT-DATE` (months left and whole months of selling for a dated target), `CHAT-REACH` (what the calendar or delivery ceiling reaches instead) and `CHAT-PACE`; the chat leads with the headline and what breaks first.
- The six-month horizon for a monthly fee with no date is labelled a planning default in the headline.
- The note gate refuses a note that restates the headline (the duplicated "Nothing breaks" line).
- `check_copy.py` refuses labels quoted from inside a file ("Founder 3").
- Rules: never edit the workbook by hand; no sales-tax commentary in the chat; at most three questions after the plan, overlapping ones merged; the feedback question asked once, then "Anything else, or shall I save the plan?"; when the founder asks for the workbook on another reading than their stated target, the stated target stays in view and both are saved; the Merigrove line ends every message that hands over a workbook.
- `sources` record where a figure came from, never a reading of it.
- A Week by week sheet: the coming weeks (`weeks_ahead`, 6 by default, up to 26) scaled to their selling days and days off, with hours of calls and a SUM total row. Layout requests are met through the script and never refused; the save offer is made once, then each change ends on the change itself. 17 new script tests; workbook tests find sheets by name.
- The pace a selling day for bookings, held calls and sales, beside the pace a week; the weekly pace gets its own line at the top of the Plan sheet, with the first action under it.
- `made_so_far`: profit already made comes off a dated target, and what the ceiling reaches is given with it added back, so no year-end total is ever summed in prose. A target already met stops.
- `month_to_date`: this month's counts against the pace for the selling days gone, in the plan and the `CHAT-MONTH-SO-FAR` lines, never folded into the rates. `count_export.py` prints and saves them from the export.
- A dated day off that falls outside the call days is named (`CHAT-DAYS-OFF`).
- Rules: anything the founder wants at the top of the Plan sheet goes in the note; no figure of the model's own in the chat; never re-ask what the founder already said; the feedback question never returns after a rebuild; the Merigrove line also ends the save message. 8 new script tests.
- `pace_whole`: the weekly pace in whole calls when the founder asks (up when uncapped, down under a ceiling). The second line about an HT price is gone from Assumptions; `check_copy.py` refuses sales-tax readings in the chat. Rules: reply in the founder's language, not their country's; never say the founder misled you; the save offer appears in one message only. 4 new script tests.
- `active_clients_max` for a monthly fee: the most clients the team can serve at once caps paying clients month by month, and where the target needs more it is what breaks, with the fee that fits (profit plus costs over the cap, plus delivery). Question 2 asks it.
- For a monthly fee, the profit the next 12 months make at the plan's pace (or at the ceiling) is printed with `CHAT-REACH`.
- A lever that cuts nothing at whole-client level is no longer called the biggest lever without saying so. `CHAT-REPLAN` carries the re-plan date. 6 new script tests.
- When nothing breaks but delivery is met exactly or the calendar is tight, `CHAT-BREAKS` says so with the figure (added after the last end-to-end pass; unit tested).
- `check_copy.py --chat`: every chat reply is checked, and any sales-tax mention that is not a question for the before-tax price is refused. 3 new script tests.

## 1.2.1 (2026-10-21)
- Added "Where files go": deliverables always land in /mnt/user-data/outputs/ (claude.ai, Cowork) or the working folder (Claude Code), never a scratchpad. Found by end-to-end testing with a real headless Claude session.

## 1.2.0 (2026-10-21)
Fix round after the blind test of 1.1.0 (verdict: not ready).
- Monthly fees (retainers, subscriptions, memberships) are planned as recurring revenue: paying clients needed at once, clients paying now, clients leaving at 1 in (months a client stays) a month, and the fewest new clients a month that reach the target by the date, then the new clients a month that hold it. Month-by-month paying clients and profit, the month the target is first reached, and what the delivery or calendar ceiling reaches instead. A "clients stay 2 months longer" scenario. New inputs: `billing`, `months_retained`, `active_clients_now`. Question 2 asks for them; question 5 is skipped for a monthly fee.
- Targets with a date: `target_profit_year` never becomes a monthly figure until the founder says run rate or by date (`target_kind`); `target_profit_by_date`; the plan says the months left and the whole months of selling, and plans to the date.
- Every founder-typed number, amount, percentage and duration goes through `scripts/locale_numbers.py` (Build Standard section 13): 15.000 €, 4.850,00, 4 850,00 €, 1'250.50, 68,3%, 1,5h, 90 minutos, 7,5 Std. The decimal style is detected once; a figure that reads two ways, or a value holding two figures ("45 min plus prep so call it an hour"), stops with one question. The old comma-stripping parser is gone; arithmetic in parts, ranges as midpoints and voice-note words are kept.
- Plausibility stops before anything is built: a call over 4 hours or under a quarter of an hour, a price under 50, a target under 100, over 60 selling hours a week, a stay over 120 months. The founder can confirm (`confirmed`).
- Figures are written back in the founder's style (15.000 €, 68,3%), in the plan, the note gate and the workbook's money format.
- Date order and paper size come from the founder's `country` (`locale_defaults`), never from spelling.
- `count_export.py` reads UTF-8, Windows-1252 and Latin-1, says which; matches headings and statuses without case or accents; knows French, Spanish, German, Portuguese, Dutch and Italian CRM words; keeps the founder's spelling of source names; writes no counts file while a status is unmapped.
- Sales-tax markers in other languages: TTC, inkl. MwSt, IVA incluido, BTW inbegrepen raise the [NEED]; HT, zzgl. MwSt, + IVA, excl. BTW are read as before tax and noted.
- Weekly pace on an uncapped plan is shown to one decimal (1.4 held calls a week for 6 a month), with a fortnight figure under two a week; "Set at your calendar" appears only when a ceiling caps the pace.
- The note gate checks each figure against the plan's figure for the same thing (held calls, bookings, leads, sales, hours a week, hours a call), so a stale figure that happens to appear elsewhere is refused.
- Polish: "1 hour", not "1 hours"; no "your estimate: your estimate"; "Lowest price at which your calendar carries this target"; no "Your business" placeholder title; memory stores the value of a sum with the sum in Source, the number style, the country and future dated days off.
- Evals: the blind tester's two runs are permanent samples (`blind-runA-retainer-us`, `blind-runB-europe-crm`) with their fixtures; 76 new script tests including 600 random retainers.

## 1.1.0 (2026-10-20)
- Global rework (Build Standard 0.1). Removed every UK-specific element: the VAT registration threshold and standard rate with their government sources, the VAT question and VAT arithmetic on prices, the GBP default currency, the day-first-only export reading, the Monday to Friday-only working week and the A4 paper setting.
- Prices are planned as entered, before any sales tax, with one neutral line in the plan. A price that reads as including sales tax ("incl GST", "inc VAT") is a [NEED] for the before-tax figure; nothing is ever taken off a price. The before-tax or take-home question stays; tax is never computed or estimated.
- Currency read from the founder's figures (£, $, €, S$, A$, HK$, ₹, RM, ISO codes) or left without a symbol and said out loud; a bare $ is "dollars", not a country. Never converted.
- Date order (`date_style`), spelling (`spelling`), working week (`call_days`, for example Sunday to Thursday or Monday to Saturday) and dated days off (`days_off`) follow the founder. Selling days scale with the call days.
- `count_export.py` reads the date order from the export and stops to ask when every date is ambiguous (`--dates day-first|month-first`).
- `check_copy.py` now refuses tax arithmetic, statements of what a law requires and country assumptions (tax offices, "bank holiday", "UK founders").
- Memory: version 1.0 files still read; their tax rows are ignored and said. New rows for date order, spelling and call days.
- Evals: US (USD, month first, American English), Singapore (SGD, GST-inclusive price) and India (INR, Monday to Saturday, days off) founders added beside the UK ones.

## 1.0.0 (2026-10-20)
- First release.
- Works back from the profit a founder needs (or from revenue, flagged) through delivery cost and running costs to whole sales, then up the chain to offers (where counted), held calls, bookings and leads.
- Every rate tagged: measured (with its count), measured on under 10 (directional, with the planning default beside it), your estimate, planning default, or not known. Re-plan date set by the tags.
- Calendar and delivery checked before the plan is called possible; one binding constraint in the order capacity, show rate, lead volume, close rate; where capacity binds, the price the ceiling needs leads the headline.
- Scenarios one lever at a time and all three together, "three bets, not a plan", per-channel loads at each channel's own rates, the hiring trigger, a weekly pace that never exceeds a ceiling, and a dated, owned first week.
- Cash in the month kept apart from sales. Before tax or take-home always asked; tax never worked out. One country's sales tax rules were built in (removed in 1.1.0).
- One file: a standard-library workbook with live formulas and cached values (Plan, Try a lever, Scenarios, Assumptions). No libraries needed.
- `count_export.py` counts a CRM or spreadsheet export (title lines, mixed date formats, messy statuses) into monthly actuals and channel counts, and lists every status it read; unknown statuses are asked, never guessed.
- Reads founder wording, including voice-note numbers ("five grand", "six fifty", "an hour and a half") and "1 in 4" style estimates; a "Today" line sets current sales against the target.
- Memory file with profile, monthly actuals, the last plan, learnings and history; return runs compare the month with the plan.
