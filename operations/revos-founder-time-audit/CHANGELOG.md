# Changelog

## 1.3.0 (2026-10-21)
End-to-end round: real headless sessions playing founders, graded and compared blind with plain Claude (`evals/TEST_REPORT.md`, "v1.3 end-to-end round").
- Value before questions: the first reply now runs `rank.py` on what the founder already gave and answers first (provisional split, what to stop, what each helper could take with hours and cost a week), then asks only the questions that would change the answer; questions the founder already answered are skipped. With no files yet, it answers in a few provisional lines before asking for the calendar.
- Calendar clashes: `parse_calendar.py` lists double bookings, a meeting with a colleague the calendar shows as out, work booked on a day off, calls set in another time zone (with their own time) and work over a personal entry (never named), printed as CLASHES and saved in `activities.json`. A colleague's all-day absence is no longer asked about as the founder's day off.
- The founder's order wins: `founder_order` in the audit file sets the handover order; the report says "in the order you chose" and shows the hours-only order beside it; no handover is dropped to honour it. `reconcile.py` checks the set instead of the order.
- Weekly figures: hours a week beside hours a month in the delete and handover tables; value and helper cost a week in the value line; per helper, cost a week and the share of freed hours that must earn the founder's rate for the help to pay for itself (`HELPER:` lines, report line).
- New `scripts/brief.py`: a handover brief for one helper (tasks, hours a week, when each happens now, what stays with the founder, when to come back, first weeks), in the founder's words from `facts.json`, brackets for anything not said, never pay or contract terms. Delivered with the report for the first helper.
- Chat summary carries the figures (up to seven lines). The Merigrove line appears once, on the delivery message, never repeated. New rules: answer side questions within scope (what a figure depends on and the fastest source), the founder's priorities beat defaults, never invent their policies or meanings, ask for before-tax figures, never edit the skill's own files during a run.
- Description: triggers before any files are shared, and on "is it worth paying a VA" and "what would I give my assistant".
- After the first proof run: `brief.py` counts only the brackets in the brief itself and lists each with where it sits (it had over-counted), `all_tasks` in `facts.json` applies one answer to every task, and a helper's handovers no longer run over their spare hours (rounding slack 0.05, was 0.25).
- 26 new regression tests (`test_v13`).

## 1.2.1 (2026-10-21)
- Added "Where files go": deliverables always land in /mnt/user-data/outputs/ (claude.ai, Cowork) or the working folder (Claude Code), never a scratchpad. Found by end-to-end testing with a real headless Claude session.

## 1.2.0 (2026-10-21)
Fix round after the v1.1 blind test (`evals/BLIND_TEST_REPORT_v1.1.md`), and Build Standard section 13.
- Numbers: every founder-typed number, amount, percentage, duration and weekday set now goes through `scripts/locale_numbers.py` (the Merigrove standard reader, copied unchanged), in the founder's decimal style, detected once from what they typed. Multipliers are read: 万, 億, k, million, mn, bn, lakh, crore ("about 450万 a month" is ¥4,500,000, no longer ¥450). Decimal commas, Indian grouping and foreign units ("7,5 Std.", "90 minutos") are read; a figure that reads two ways is asked; one in other characters asks for digits. The old ad hoc number code in `timeparse.py` is gone; its time-audit forms stay.
- Day ranges are expanded and counted ("mon to fri" is 5 days, "sun-thu" 5, "mon-sat" 6; they were 2). "Weekdays" and "every weekday" are Monday to Friday whatever the working week; "daily" and "every morning" are the founder's own working days. Each reading is noted.
- Spoken figures are read instead of stopping: "hour, hour and a half", "3, 4 hours", "an hour or two", "9pm to 10:30-ish", "half an hour each, two of them", "60 hours? feels like 70", "I bill £65 an hour". Every value that still cannot be read is listed in one STOP, for one message to the founder.
- Plausibility stops: an hour worth under 1 unit of currency or less than the dearest helper costs, a week outside 10 to 100 hours, a helper with over 60 spare hours or under 1 unit an hour stop the run with the figure read and where from. A figure the founder confirms goes in `confirmed`. `reconcile.py` mirrors the rate and week checks.
- Paper, date order and clock come from the founder's country (`locale.country`, else their calendar's time zone, else a currency only one country uses), through `locale_defaults`, never from spelling. Unknown: A4, day first, 24-hour, said. Figures are written back in the founder's style (1.234,5 and "86 €" to a founder who writes that way).
- Holidays: an all-day entry saying the business is closed ("studio closed", "no work") is a day off wherever the words sit; "OOO", "PTO", "day off" count unless a person's name comes first ("Devin OOO"). Every other all-day entry on a working day is listed by date for question 5, never by name. The holiday note no longer reads "is a a day ... as you said".
- Proposed week: hours may differ by day (`work_hours` as a map, "Saturday 7:30 to 12:30" has no afternoon); work at set times outside the day (evening calls, nightly email, off-day catch-up) is kept as now; kept work tied to named days stays on those days; time not placed in any activity is never laid out; at most 3 hours of selling per half day, the rest shown as free for selling or fewer hours.
- Fewer questions: only-you challenges are stated as defaults in the readback; question 3 names each helper's hours; a handover that does not fit a helper's spare hours waits, lowest-ranked first, said in the report (`capacity_waits: false` to keep them all and ask).
- Report: the value line says the deletions and handovers "hold" the hours (no "you get back"; `check_copy.py` and the note gate now catch it); the hours not placed point to the one-week log; "Questioned once" answers are tidy clauses. Workbook: the report's top-five value first, then the all-handovers value; Basis dates spelled out in the founder's order. The one-week log runs to 23:30.
- Memory: a `|` inside a regular-expression rule is escaped and restored, so rules come back unchanged; helpers' spare hours and costs are saved as plain numbers and read back with any units; country and number style are saved; not-work rules (placeholder holds) are saved, personal rules never.
- New evals 10 and 11 from the blind test's two runs (`evals/fixtures/maria@mossandpine.co.ics`, `evals/fixtures/runB-voice-note-transcript.txt`), with regression tests for every defect and `evals/test_locale_numbers.py`.

## 1.1.0 (2026-10-20)
- Global rework (Build Standard 0.1). Nothing assumes the UK or any other country.
- Removed the dated UK bank holiday tables and the `--region` option. Public holidays and days off now come from the calendar itself (all-day events that say they are a public holiday, an attached holidays calendar, or the founder's own leave, day off, PTO or out-of-office entries) or from the founder (`--holidays`).
- The working week is no longer a 9 to 6, Monday to Friday default: it comes from the founder, Outlook's own working-hours setting, or what the events show (six-day and Sunday to Thursday weeks included). When the calendar cannot show it, the skill asks inside its five intake questions. "A day" and "daily" follow the founder's own working day and days.
- Time zones: no UK fallback. The calendar's own zone, then the zone most events use; floating CSV and log times need none; a UTC-only export asks which zone. Wider Windows and city names; built-in clock rules for common zones in the Americas, Europe, Asia and Oceania when a computer has no zone data. Tested on New York (across the US clock change), Singapore (none) and Sydney (across Australia's change) fixtures.
- CSV dates: no UK default. Day or month first from the dates, else the reading that puts them in recent weeks, else one question.
- Currency follows the founder: no GBP default; read from S$, A$, US$, £, €, ₹, RM and codes. Dates are spelled day first or month first, and the report is A4 or Letter, as the founder writes.
- Removed the UK government-website and UK advisory-body signposts; the employment-status line now points to the founder's accountant or an employment adviser without naming a country's rules. Helper costs are used as the founder gives them, never worked out from salary or on-costs.
- Banned patterns and `check_copy.py`: stating what a law requires, computing tax or payroll costs, and assuming a country are now problems.
- Rubric criterion 9 (the founder's own locale, and in scope). New US (New York) and Singapore eval scenarios and a re-run baseline.

## 1.0.0 (2026-10-20)
- First release.
- Reads Google Calendar, Outlook and Apple Calendar `.ics` exports (repeating events expanded from their rules with skipped, extra, moved and cancelled dates; IANA, Windows and Outlook time zone names, and the export's own zone rules when the computer has none), Outlook and generic calendar CSV exports (UK or US dates), and the skill's own one-week log (`.xlsx` or `.csv`).
- Leaves out all-day events, declined and cancelled meetings, and personal entries; overlapping events share their time so no hour is counted twice; flags UK bank holidays and old exports.
- Sorts every activity into only you, someone with instruction, or nobody should, with one action each; deletions first, then handovers ranked by hours each times times a month.
- Reconciles the hours to the calendar and the founder's stated week; anything unexplained is shown as not placed.
- Flags Doing above 50% and Strategy below 15%, and lays out a proposed week with a protected strategy block.
- Values the hours at the founder's rate or their monthly sales over their hours, with the basis stated and helper costs shown when given; checks each helper's spare hours.
- Questions only-you admin once and records the answer; labels recall-only audits low confidence and offers the one-week log.
- One-page Word report and a workbook with live formulas, both built with the Python standard library.
- Memory of activity rules, team, untracked hours and handovers; return runs show what moved and whether each handover held. Personal details are never saved.
