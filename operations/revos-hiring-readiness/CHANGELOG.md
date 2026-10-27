# Changelog

## 1.3.0 (2026-10-21)
Fix round after the end-to-end test, where a blind comparator slightly preferred plain Claude for the US agency founder.
- The first reply now carries a provisional answer before any question: the verdict, the month-three line, what the business can carry and what the hire has to bring in, plus a direct answer to whatever the founder asked. Then at most three questions, each asking one thing, chosen because they could change the verdict; five in all across two founder turns. A founder with no figures gets the short answer first, then the ask.
- New `CEILING` line and report line: the most the hire can cost a month, all in, with the cash holding the floor in a usual and a bad quarter. On pay alone it shows the room left for whatever goes on top of pay, so "what does payroll add?" gets a usable answer without any on-cost being estimated.
- New `PAYS ITS WAY` line and report line: revenue a month the hire has to bring in or protect at today's margin, and the number of new clients when the founder gives a typical client's fee (`typical_client_month`).
- "What does payroll add?" is answered in plain words (employer payroll taxes or social charges, staff insurance, retirement contributions, benefits, equipment, leave cover, recruiting), with no amounts or rates, and the fastest route to the real figure. The report's full-cost list uses the same plain words.
- Capacity given as headroom ("could take maybe 2 more clients") is read (`capacity.room_for`, `said`), quoted, and turned into a share once the founder says how many they have now; it is no longer dropped.
- When the founder wants to move anyway, the skill gives the safest version in their own figures (recruit, offer conditional on the named conditions, checkpoint as a test of them) instead of arguing the verdict again.
- After-tax figures prompt a plain request for the before-tax figure; pass-through money (ad spend billed back) is asked about, never assumed.
- The Merigrove Business Audit line appears once per conversation; the "Made with" credit moved off the docx footer and the workbook Read me into the document properties.
- Description: triggers before the founder has shared anything.
- Costs that move with revenue (`variable_costs_share`, "contractor fees fall about 40% of whatever income drops"): the bad quarter saves that share of the revenue lost, in the scripts and the workbook alike, so no figure is ever built by hand outside them. Saved in memory.
- The first reply's run is marked `provisional`, so a task list not yet asked for cannot make the verdict No.
- The verdict reason separates conditions that fail from those that need a figure ("one fails on today's figures: cash in a bad quarter; one needs a figure...").
- Not yet always comes with a way through in the founder's figures: what to do this week, the offer gate (the loaded figure inside the ceiling, the cash or signed work named), and the re-check; a founder's correction that worsens the figures is shown side by side, never labelled a recommendation.
- A descriptive placeholder ("Your HVAC agency") is never kept as the business name, and an unnamed business is left out of the report header and Read me rather than shown as "Your business". "The skill never works this out" became "This check never works it out".
- Layout requests ("put the no-hire gap line at the top") go through the build with `--lead` (under the verdict, or `--lead-above` when asked), gated like the note; never refused because of the template and never hand-edited into a finished file.
- Tests: 21 new (283 in all).

## 1.2.1 (2026-10-21)
- Added "Where files go": deliverables always land in /mnt/user-data/outputs/ (claude.ai, Cowork) or the working folder (Claude Code), never a scratchpad. Found by end-to-end testing with a real headless Claude session.

## 1.2.0 (2026-10-21)
Fix round after the independent blind test of 1.1.0 (15 defects) and Build Standard section 13.
- Numbers are read with `scripts/locale_numbers.py` (copied unchanged from the standard): decimal comma or point worked out once from the founder's figures, Indian grouping, lakh, crore, 万, k, ranges, hours in any common unit and weekday sets. A figure that reads two ways or cannot be read, or a headline figure that fails a plausibility check (a monthly cost above a month's revenue, cash a thousand times smaller than costs, under one unit an hour), stops with an `ASK:` question; `confirmed_figures` lets a confirmed figure through. Numbers and money are written back in the founder's style (9.800 €); an Australian who writes $ sees $. Date order and paper size come from the founder's country (`country`), never their spelling: US Letter for the US, year-first dates for Japan.
- Bank exports: columns found by name in order of preference (Chase's `Details` column is no longer read as the description); `--exclude` matches any text in a row and warns when it matches nothing; transfers, pending rows, one-off big payments inside the average and regular payees are listed for Claude to ask about; the latest balance is the chronologically last row in a newest-first file; every month inside the export's range counts as full; semicolon and decimal-comma exports read; a P&L with months as columns stops with a pointer.
- The cash test runs the same bad quarter without the hire and says how much of the gap is there anyway. Contracted revenue is not cut in the bad quarter (still paid late); month-to-month recurring revenue still is. "Contracted work" is not suggested to a founder who already has it.
- Known low periods (a closure, a season, with the founder's own figure) are loaded in both cases and the window runs on through them; months well below the average are flagged as seasons, inside or after the window. Condition 4 compares the same months a year apart with 18 months of history; with 12, a lower worst month in a different season is Unknown, not a fail.
- Condition 3 accepts repeat revenue (regulars, memberships, plans, packs, or the share from returning clients) for appointment and retail businesses; question 3 asks it in their terms.
- A role pack written inside a Not yet or No report opens with a line to hold the ad.
- A price rise in the founder's own words ("raised prices in May", "fees up $5") is read; a biggest task whose written status is unknown makes condition 5 Unknown with the question asked; "paid on time as usual" replaces "0 days late"; a rough margin range is shown as a range; 20 hours against named days is flagged as a question about the cost.
- The payroll provider the founder's own export shows is named as where to get the loaded figure; on-costs are still never estimated.
- Memory keeps the founder's overrides (a 0-day delay included), closures in their own dates, the currency mark and number style; never saves a placeholder business name; rounds money; keeps the last margin aside for confirmation instead of reusing it.
- The workbook shows the source of every figure, labels a pay-alone cost on the Inputs and Read me sheets, carries the closure and contracted revenue in its formulas, and takes up to 24 months of history.
- Evals: the blind tester's two runs are permanent evals with their input files as fixtures; 96 new regression tests.

## 1.1.0 (2026-10-20)
- Global rework (Build Standard 0.1). The skill now works the same for a founder in any country and currency.
- Removed: every jurisdiction's on-cost constants (employer charges, retirement contributions, wage floors, small-employer allowances, holiday entitlement), the on-cost illustration path and its two flags, the two country-specific reference files, the sales tax registration field, the default currency and the day-first-only date reading.
- The hire's cost is now the founder's fully loaded monthly figure (pay plus whatever their accountant or payroll provider says goes on top). With a salary only, the scenario runs on pay alone, marked everywhere as understating the hire, and the verdict cannot be Ready.
- Employee or contractor status is never judged; one line names the accountant, payroll provider or an employment lawyer where the founder hires.
- Scorecard and job ad are jurisdiction-neutral, with one line to check the employment and anti-discrimination rules where the founder hires; the pack check refuses country-specific employment, tax and benefit terms; the ad wording table is now in `role-pack.md`.
- Currency, date style (day or month first, in reading and in the report and workbook) and English follow the founder. Bank exports work out their own date order.
- New banned patterns, checked in code: computing tax or employer charges, stating what a law requires, judging status, assuming a country.
- Evals: a US founder and a Singapore founder added; an Australian pack-only run; the refusal eval now tests the salary-only path.
- Fixed: pipeline odds written "50/50" were read as a 1% chance; memory now keeps the last two months' gross margin, the locale and the cost basis; cost NEED lines show the currency.

## 1.0.0 (2026-10-20)
- First release.
- Six conditions as a gate (cash in a bad quarter, margin for two months, six months of role cover, a rising worst month, a real role with a use for the freed hours, near full after a price rise), each Pass, Fail or Unknown with evidence.
- Ready, Not yet or No verdict; Not yet stated as conditions in the founder's figures, never a date.
- Cash scenario from today to the hire's 13th week (at least 13 weeks): a usual quarter and a bad one (20% less money in, every payment 15 days late), a one-month floor with the hire included from the start, known bills, one-off hire costs, the cash gap and the later start rule.
- Contractor alternative at the role's hours and at the 15-hour line.
- A single-country on-costs checklist and dated rate illustrations (removed in 1.1.0).
- Role pack as the Ready output (the role scorecard folded in): outcomes from freed hours, job ad with a single-country wording check (made neutral in 1.1.0), interview guide mapped to outcomes, first 90 days with decision rights, one-to-one agenda, contractor brief.
- Report (.docx) as the one main file; cash workings (.xlsx) with live formulas and a CSV fallback; bank export reader; memory with return-run comparison.
