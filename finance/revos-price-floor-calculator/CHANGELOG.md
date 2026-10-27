# Changelog

## 1.3.0 (2026-10-21)
Fix round after the end-to-end test against plain Claude (the Boston podcast studio lost slightly to plain Claude; Madrid graded 7/10).
- The first reply answers before it asks: a provisional verdict table from the script on whatever the founder gave, the hour and the whole-business line, and the inconsistencies in their material, then at most the questions that change a floor or a verdict. No question asks what the founder already said ("brutos" settles the pay basis).
- After-tax pay with a stated rate: the script uses the higher of that rate and the hour the after-tax pay needs, and prints an HOUR CHECK line when the founder's rate is lower. A BEFORE-TAX SENSITIVITY line shows what each round step of before-tax pay adds to each floor, so the founder can read off the floor once their accountant gives the figure. No tax is estimated.
- With no hours a week given, the hour from pay uses the hours the offers take at their volumes.
- An offer with hours but no price gets its floor before any sales tax, so a tax-inclusive price with no rate still gets a useful first answer.
- Fees with a fixed part ("2.9% + 30c", "1,4% + 0,25 €") are worked out on each offer's price, and a card share applies to a given fee rate. The summary lists an offer's own fee beside a bank-transfer default instead of saying there is no fee.
- No more card-range benchmark in any assumption or STOP line.
- `pinned_line`: a line the founder wants first on the summary, saved in memory; no hand-edits to built files.
- Clearer client-loss wording ("Break-even client loss in plain cash: 30%").
- SKILL.md: answer side questions directly within scope, follow the founder's chosen price, never invent meanings, use their names, the chat carries the verdict table, and the chat follows the founder's main language. Intake guide section 8 lists the inconsistencies to catch. Rubric criterion 10. Description triggers before files are shared.

## 1.2.1 (2026-10-21)
- Added "Where files go": deliverables always land in /mnt/user-data/outputs/ (claude.ai, Cowork) or the working folder (Claude Code), never a scratchpad. Found by end-to-end testing with a real headless Claude session.

## 1.2.0 (2026-10-20)
Fix round after the independent v1.1 blind test (a Boston podcast studio and a Madrid consultant) and Build Standard section 13.
- Numbers are read in the founder's own style through the shared `locale_numbers.py` (copied unchanged into `scripts/`): "2.420 €", "60.000 brutos", "1.200,50", "4,5 horas", "1,4%", "=2.420/1,21", "90 minutos", "2 días". The style is detected once per run; a figure that can be read two ways, or two styles in one run, stops with one ASK line. Figures are written back the founder's way (2.800 €, 3,79 €), in the summary, the workbook and the memory file.
- Plausibility stops before anything is built: an hour under 1 or over 20 times what any offer charges an hour, a price under 10 or under 1 for each hour of work, overheads above the hour, more than 80 client hours a week. A figure the founder confirms goes into `confirmed`.
- Pay given after tax: Raise verdicts stand ("at least"), Hold and Restructure are marked provisional with no option recommended, three routes that need no tax estimate are offered, and the floors with the hour a quarter higher are shown as a sensitivity.
- When the hour comes from pay and the hours the offers use differ from the founder's figure by more than 10%, the hour is priced on the lower figure and a [NEED] asks which is right (`"client hours as given"` confirms the founder's).
- Overheads are spread over client hours in the founder's working weeks, not 52, in the script, the workbook and the rebuild formulas; the hours comparison is per working week. Every floor rises by up to 52 over the working weeks.
- Paper size and date order come from the founder's country (`country`), never their spelling: HTML `@page` size, page language, workbook paper size. A bare "$" with a known country follows it.
- American English no longer rewrites "rise" or touches the founder's note.
- Workbook: client hours a week is a live formula of the founder's hours and the team's; the pay row says when the figure is after tax, in red; a stated rate is used first, matching the script; per-offer preferred route; provisional verdicts on the Summary tab.
- Note gate: allows every figure the founder gave; refuses figures from an option the calculator did not recommend unless the note names it; warns when a verdict word contradicts the verdict; new `checknote` command so a rewrite costs one fast run.
- Client loss leads with the cash line; the freed-hours view carries "only if you refill those hours" and is dropped for an offer sold once a month or less.
- Per-offer `prefer: raise | restructure` replaces lowering the global restructure limit.
- A price within 5% under its floor and above its cost floor holds: "Hold, at the floor".
- Intake: costs entered as paid, sales tax and all; a payment for the founder themselves is part of their pay. A price with sales tax words on it stops with a question.
- File names fold accents; plurals for one and two; fee sources without nested brackets; the results file goes to scratch, so the founder gets three files.
- Fixed: two f-strings with backslashes that would not run on Python before 3.12.
- New evals 10 and 11 from the blind tester's two runs, with their files in `evals/fixtures/`; 69 new regression tests; a euro example first in `references/examples.md`.

## 1.1.0 (2026-10-20)
Global rework to Build Standard 0.1: no country assumed, no tax worked out or stated.
- Removed: the VAT registration question, the VAT threshold constant and its source, the yearly-sales-against-threshold line in the summary and the workbook, and the take-home question's reference to one country's income tax and social charges.
- Prices are entered and shown before any sales tax, with one neutral line telling the founder to ask their accountant whether they need to charge it. A founder who quotes tax-inclusive prices and names the rate they charge has them divided by the script, recorded as founder supplied.
- Pay is still asked before or after tax. After tax raises a [NEED] and the founder is asked for the before-tax figure from their accountant; the skill never estimates tax.
- Working weeks: the founder's own figure (weeks worked once their holidays and public holidays are out), asked inside question 3; 46 when unknown, stated in the summary and a yellow cell as an assumption to change. No holiday calendar assumed. Impossible values are flagged.
- Days in hours fields: 8 hours unless the founder sets `day_hours`; stated in the summary when used.
- Currency follows the founder: no GBP default; a missing currency or a bare "$" raises a [NEED]. S$ and HK$ added, more codes parsed, PayNow, PayID, Zelle, Interac, SEPA, UPI and similar read as bank payments.
- Employee cost: the founder's figure from their payroll provider or accountant, used as given; the skill never adds on-costs.
- Memory saves the founder's English (locale), working weeks and day length when the founder gave them; 1.0 memory files with VAT rows still read and the rows are dropped on the next save.
- check_copy refuses tax thresholds, statements of what a law requires, tax or on-cost estimates, named tax authorities and holiday calendars, and warns on a named country. Banned patterns and a ninth rubric criterion (global, no tax or law) added.
- New evals: a US founder (after-tax pay, days, own working weeks) and a Singapore founder (GST-inclusive prices at her own rate, her own day length). Every sample run replaced; before-after now uses the US founder.

## 1.0.1 (2026-10-20)
Fixes from an independent blind test.
- Client loss is shown in two named views: counting freed hours at your rate, and in plain cash. "Still make the same" and "does not cost you" are gone.
- Intake asks whether target pay is before tax or take-home (take-home is flagged and sent to the accountant; tax is never worked out) and whether the founder is VAT registered. Still at most five questions on a first run; the founder gives their own client hours and the script adds the team's.
- New whole-business view: sales a year and what the business leaves the founder before tax against the pay they want, plus a check of the hours the offers use against the hours given.
- UK VAT line for founders not registered: yearly sales now and at the recommended prices against the £90,000 threshold (government source, checked 20 October 2026), then the accountant. Removed in 1.1.0.
- Parser reads units on numbers ("7.5hr", "12hrs", "150pm", "£1.2k"), days and minutes in hours fields, bare percentages ("1" is 1%), and rejects negative hours and costs and fees, refunds or buffers of 90% or more with a plain STOP.
- Any error ends in one STOP line and exit 2 with nothing left half-written; input shape is checked first. SKILL.md says what to do on exit 2.
- Memory saves the pay, its basis and hours instead of the worked-out rate, saves an offer's fee only when it differs from the business rate, and the return-run list names every change.
- Workbook: the hourly rate is a formula from pay, hours and weeks; client loss in both views; restructure rows read "not needed" on Hold offers; the middle option shows whether it appears in the summary; calculated values are stored via LibreOffice when available.
- Summary: British dates, one A4 page, "buffer" in place of "margin" with a line on what it is for, worked-out inputs moved to the workbook, no internal authority in founder files, pipes in offer names escaped.
- Note gate: money and percentages must match the same kind of figure, a named price must be one the calculator worked out, small numbers pass only with a unit, promises are refused. Copy checker widened.
- Template values are empty, so nothing plausible can pass as founder-given.
- New assets/before-after.md.

## 1.0.0 (2026-10-20)
- First release.
- Price floor and cost floor per offer with the founder's hours priced in, overheads shared by client hours, payment fees and refunds solved into the floor exactly.
- What today's price pays the founder an hour, beside their rate.
- Hold, restructure or raise verdict with three costed options and the break-even client loss.
- Workbook with live formulas (openpyxl), with a CSV and formulas fallback; one-page HTML and markdown summary.
- Memory file with Profile, Offers, Learnings and History; return runs show what changed and which floors moved.
