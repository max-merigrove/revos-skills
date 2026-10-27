# Changelog

## 1.3.0 (2026-10-21)
Fix round after the end-to-end test against plain Claude (`evals/TEST_REPORT.md`, "v1.3 end-to-end round").
- Value before questions: the first reply runs `compute` on what the founder gave (draft flags, stated defaults) and opens with a short, labelled provisional answer to the question they asked, where their hours go, the top handover candidates, and anything in their own figures that does not add up. Draft flags are shown in the same reply for correction, so the flag turn is gone.
- Question cap made countable: at most four in the first reply and five before the files, every part joined by "and" counted; questions ranked by how much they move the answer, each saying what it changes; anything else becomes a stated default. Files are built on the second reply unless an answer opened a headline gap.
- Side questions answered, never only referred: new `references/side-questions.md` (hire or raise prices, the cost of a hire and payroll tax in plain words with no figures or rates, contractor or employee, sales tax, pricing, a helper's extra hours, writing the handover). Rubric criterion 8 and the intake guide updated; new criterion 9, value first.
- No invented figures: a price given as a range is no longer quoted as its middle. `capacity.py` keeps both ends, prints what the offer pays per hour at both ends, raises a NEED for a typical price, and says when the lowest-paying offer is unsettled by the range.
- Each offer's own price now shows beside what it pays for each hour of the founder's.
- The founder's priority leads: new `lead` input (`helpers`, `note`, `handover`) puts that block straight under the title, so nobody hand-edits the reading or the script. Rule added: never edit the skill's own files during a run.
- After delivery the skill offers to draft the write-up for the first handover step from the founder's own tools and rules.
- Description: triggers before the founder has shared any material.
- The Merigrove line appears once, with the first delivery, never on rebuilds; no skill-internal paths in founder copy (assets are copied to the output folder first).
- Tests: `evals/test_e2e_v13.py` (run by `test_scripts.py`) covers range prices, price beside per-hour and `lead`.

## 1.2.1 (2026-10-21)
- Added "Where files go": deliverables always land in /mnt/user-data/outputs/ (claude.ai, Cowork) or the working folder (Claude Code), never a scratchpad. Found by end-to-end testing with a real headless Claude session.

## 1.2.0 (2026-10-21)
Fix round after the independent blind test of 1.1.0 (`evals/BLIND_TEST_REPORT_v1.1.md`), and Build Standard section 13.
- Every founder-typed number, amount, percentage, duration and weekday set is read by `scripts/locale_numbers.py` (copied unchanged from the Merigrove standard), in the founder's decimal style, detected once; figures are written back in that style. A figure that reads two ways stops with every such question in one message. The old ad hoc parsers are gone; this skill's own forms ("=" sums, "40+", "4 hrs, sometimes 5", how often, how long a client stays) stay on top of it.
- How often: "6 days a week", "Mon-Sat" and other day ranges, "every weekday" (Monday to Friday); "daily", "every day" and "per day" use the founder's working days; "2 rounds per project", "4 posts a week"; hours in the how-often field are refused, not counted.
- How long: "a month", "about a month", "half a year", "two quarters", "a fortnight"; an unread length names the words and is never labelled "the default".
- Hours a week given as a day and a week ("12 hr x 6 days", "12 hours a day, 6 days a week", "9 hours mon-sat") are day x days; the 100-hour stop names what it read.
- The week the founder wants: above about 50 working hours (or 45 delivery hours), or with evenings and 12-hour days, question 3 asks what week they want to be working (`target_working_hours_week`). The ceiling uses it and shows today's week beside it; unanswered, a week line and a NEED say the plan takes today's long week.
- The after-handover ceiling is said with "once someone has room for the work" whenever moved hours exceed what helpers have room for, with the load counting those hours as still the founder's.
- Business-wide work (`"offer": "business"`): fixed hours a month, in the load once and off the available hours before every ceiling, never divided by client count; shown on its own row in the reading and the workbook.
- Quality checks: unambiguous checks (QA, final check, sign-off, proofread, review before delivery) still count F whatever the flag; a step the founder flagged W or T whose name only says "review" or "approve" gets a NOTE asking instead of an override; client calls, client feedback, business reviews and timesheets are not checks; `gate: no` documented.
- Optional price per offer, before any sales tax: the reading prints what each offer pays for an hour of the founder's work and move 2 names the lowest. Mixed currencies stop; a price paying under 1 an hour stops until confirmed.
- Intake: compute runs after turn one, so the hours-check question goes in the turn-two flag message; steps short of what delivery takes by over 30 per cent stop the build until added or confirmed. Flags are read back grouped F, W, T. Client messages, team standups and reviewing the team's work added to the forgotten steps. New `capacity.py import-csv` collapses a task export into draft steps with the working shown.
- Country and English are separate: `country` (a code, name, demonym or city such as "KL", "Malaysian", "Denver") sets paper and date order through `locale_defaults`; `english` sets spelling; an unknown place is a stated default, never a STOP. Legacy `locale` still reads.
- Memory (version 2): working and selling hours saved as the founder gave them; derived delivery hours labelled "worked out" and not read back as an input; country "from what you mentioned", English "read from how you write"; prices kept; the return question also checks whether delivery still takes what it did.
- Shares near a line show a decimal (49.9%, never 50%); no low-line advice for a helper paid by the project; helpers' months said to use the founder's working weeks.
- Note gate: 120 words, and comparisons worked out in prose ("nearly double", "six times the", "half the") are refused; check_copy carries the same pattern.
- Workbook: the handover order keys on each step as listed (two offers' "Culling" no longer merge), re-ranks live with RANK, and works out "in this round" from the round size.
- Step names mid-sentence keep capitals only on names (helpers, offers, tools, known products) and all-caps words.

## 1.1.0 (2026-10-20)
Global rework (Build Standard 0.1).
- Removed the one-country statutory holiday constant, its government web source and the holiday wording tied to it. Working weeks now come from the founder's own time off (`weeks_off_year`, in weeks or days); the 46-week default is a stated planning default (six weeks off, public holidays included) drawn from no country's rules.
- A day in an hours field follows the founder's `day_hours` (default 8, said when used); days off follow their `working_days_week` (default 5, said when used).
- English, date order and paper follow the founder (`locale`): US style gets American spelling, month-first dates and US Letter; others their own English on A4. No locale means a default said out loud, never an assumed country. The .docx language tag follows too.
- Hire lines no longer name an "employment adviser" for costs: the full cost of a hire goes to the founder's accountant or payroll provider, the terms to an employment lawyer where they hire. The skill never computes tax, payroll costs or on-costs, or says what a law requires; a question about them gets one line and the check carries on.
- check_copy: new PROBLEM patterns for stating what a law requires, tax or payroll arithmetic, and country-specific institutions; a WARN for money rule words.
- Fixes found in the new test runs: "more like 40" and "closer to" read as hedges; "1 ... client's worth" plural; a handover that leaves the founder a fraction of an hour over now reads as "no room at all"; step-name casing for development, support, workshops and similar; "room at mix after" printed by compute.
- New evals: a US founder asking for payroll taxes, a Singapore founder asking about sales tax registration. Trigger queries now include US, Australian, Canadian and Singapore phrasing.

## 1.0.0 (2026-10-20)
- First release.
- Every delivery step flagged F, W or T with a reason; quality checks the founder does are counted F whatever flag they were given.
- Founder load and client ceiling per offer, by script, with room at today's mix and the binding offer when there is more than one offer.
- Handover order: W steps ranked by the founder's hours a month across clients, shared steps summed once; ceiling after the top three move, including the founder's checking time.
- Helper load against a planning line and a low line, both labelled planning assumptions the founder can change.
- Hours check: the steps against what the founder says delivery takes now, with an optional one-week time log.
- One-page reading (.docx) and a workings workbook (.xlsx) with live formulas and stored values, both written with the Python standard library.
- Memory file with Profile, Offers, Steps, Helpers, Ceiling history, Learnings and History; return runs show what changed since the last check.
