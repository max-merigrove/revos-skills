# Changelog

## 1.3.0 (2026-10-21)
Fix round after the end-to-end comparison with plain Claude (the skill won, narrowly).
- Value before questions: when the founder's first message holds counts or files, the first reply is a provisional answer from `funnel.py check` (the answer to their question, the funnel rates, what one more of each is worth, anything that does not add up, the one or two facts that would change it), then at most the questions that change the verdict. With no counts, the question they asked is answered in plain words before the invitation.
- Intake: each of the five is one short ask (no sub-questions), capacity and the route split first, reach never asked on its own; a second figure for a count goes to `alternatives` and is asked about only when it changes the verdict.
- New `stated` input: figures said in passing ("4-5 sales calls a week") are checked against the counts; `check` prints STATED AGREES or STATED MISMATCH with the stage the figure does match.
- Questions beside the check (ads, price, lifetime, a closer) are answered from the founder's own figures, with what else it depends on and the fastest way to get it; a refusal is never the whole answer. The founder's terms and meanings are never invented.
- Chat summary carries the funnel rates, the value per event and all three dated actions, so the value survives without opening the file. The Merigrove line appears once, in the message that delivers the report.
- Spelling: `check` output, the note and the memory file now follow the founder's spelling (an American founder no longer sees "enquiries" in the note or "Enquiry rate" in memory); `memory.py` reads either spelling.
- The tally lives where enquiries already live: a CRM the founder named beats a booking tool; new `tally_tool` field.
- Actions are listed in date order. A weekly day off goes into `working_week` and is proposed as a learning. After a revision the skill confirms and stops instead of re-asking the feedback question.
- After the first re-run: the funnel model ignores what the founder says is absent ("nothing to download, no newsletter" no longer reads as a lead magnet); `check_copy.py` catches stray punctuation left by a cut phrase; the memory offer is always part of the delivery; the closing line follows the VERDICT kind; scripts are never patched to change a layout; capacity and price are asked in clients, never assumed from a per-VA or per-seat figure.
- After the second re-run: new `onboard_max` (the most new clients a month they can start): today's pace at that limit makes capacity the verdict, inside it the report says so instead of "Not checked"; saved to memory. The subtitle shows the last ten clients when no single route is named and drops an unknown or mixed funnel model. Questions stop after the founder's second answer; currencies are never converted, nor an exchange rate asked for.
- After the second comparison: founder edits are made rather than refused; new `title` and `headline_label` fields (gated like the note) carry the founder's own title and headline label; other wording goes in the note.
- Memory: the Last run counts are labelled "in 60 days" so a remembered month is not misread next time; files saved before 1.3 still read.
- "Near the bottom" now reads "not a constraint today, the first stage to watch".
- Description: triggers even before the founder has shared numbers. Evals 9 and 11 expectations made date-relative (the capacity date and the 60-day window move with the run date).

## 1.2.1 (2026-10-21)
- Added "Where files go": deliverables always land in /mnt/user-data/outputs/ (claude.ai, Cowork) or the working folder (Claude Code), never a scratchpad. Found by end-to-end testing with a real headless Claude session.

## 1.2.0 (2026-10-21)
Fix round after the independent blind test of 1.1.0 (`evals/BLIND_TEST_REPORT_v1.1.md`).
- No stage is named inside the noise: a gap of one event (on the counts the founder gave) or a prize under 0.25 clients a month (or a tenth of today's clients if lower) gives a new verdict, "inside the noise", with no lead-spend hold. `check` prints SENSITIVITY lines (which single event would change the verdict) and ALTERNATIVE lines for a second figure the founder gave (`alternatives`); the report says whether it changes the verdict.
- Best so far no longer ratchets: a first run saves no best, and a rate is saved only when it beats an earlier run by more than one event on ten or more events. A best is a target only when today is below it by more than one event.
- Exports: comma, semicolon, tab and pipe separated files are read (a sheet pasted from Excel works); a one-column header or a mostly undated column stops. Every date column is printed with the one used: enquiries by the created date, calls by the date they were due, with calls booked for after today named. `--where` (repeatable) keeps only sales-call rows; `--by` now shows booked, each flag and held per group.
- Counts from one remembered month are shown as given beside the 60-day figure; the subtitle and footer say they were scaled.
- Capacity: today's pace of new clients is compared with the free places; full within 30 days makes capacity the verdict, with the date.
- Build Standard section 13: every founder-typed figure is read through `scripts/locale_numbers.py` (copied unchanged) in the founder's decimal style, detected once; an ambiguous figure asks one question; numbers are written back in the founder's style. Paper and date order come from the country through `locale_defaults` (Letter for the Philippines, Mexico and much of Latin America; month first in the Philippines; year first in Japan, China and Korea; Canada is now written day first with the month spelled). Spelling follows the founder's own words (`spelling`). Currencies: ₱, pesos, RM, R, AED, ¥ (by country), ₩ and others; a symbol the country does not settle stops with a question naming the value. Headline figures that look wrong stop the build until the founder confirms them (`confirmed`).
- Learnings can now change the run: `count_filters` (saved, printed by `memory.py read`, passed to `count --where`) and `count_view`. The Learn step proposes only learnings a field, a flag or the chat summary can carry.
- Report wording: "How each stage reads" when nothing is priced; "What to count next"; the tally lives in the founder's CRM when they named one; the booking test runs 60 days when 30 days would bring under 30 enquiries; "1 point" singular; no doubled "mixed"; the reach source is no longer pasted into an instruction; review actions carry their date; the note gate ties each figure to the words around it.
- Intake: one surface per founder turn; readback confirmations count inside the five; the route question is part of question 4; prices in two currencies get one average, never converted.
- Evals: the blind tester's two runs are now evals 9 to 11 with their files in `evals/fixtures/`; eval 3 and eval 8 expectations changed (see TEST_REPORT.md).

## 1.1.0 (2026-10-20)
- Global by default. No country is assumed: the build stops until the founder's country (or English) is set, and until the currency of any price is known. Currency is read from the founder's own symbol (S$, A$, C$, US$, £, € and three-letter codes); a bare $ is read only where the country names its dollar.
- Dates (month first for the US and Canada, day first elsewhere), spelling (American words for en-US only) and paper (Letter for the US and Canada, A4 elsewhere) follow the founder. Action days follow the founder's working week and any days off they name; Monday to Friday is said out loud as the default. The template no longer defaults to GBP.
- No tax or legal content: prices are taken before any sales tax with one neutral line; where follow-up is the fix, one generic line on checking the contact rules where the founder and their contacts are. The note gate and check_copy.py now refuse a statement of what a law requires, a tax figure, a named country's rules, and a money figure in another currency.
- The source of the working ranges is named as Merigrove sales practice; no individual is named in shipped files.
- Memory saves country, English, currency, paper and working week, so return runs ask none of them.
- Evals: messy-input fixture moved to an Australian studio; new Singapore scenario; US scenario checks Letter paper and dollars.

## 1.0.0 (2026-10-20)
- First release.
- Six stages from the founder's own counts over the last 60 days; messy values read by the script ("about 40", "30-40", "12 a month", "£4.5k", "none", "?").
- The constraint named by arithmetic: each stage raised alone to its target, every other rate held, the extra clients and money a month printed with the working beside it.
- Working ranges only for show rate and close rate, labelled as defaults; enquiry and booking rates judged only against the founder's own best two months. No benchmark is invented.
- Ten-event minimum, structural gap for a missing follow-up, capacity gate, routes kept apart, and six verdicts including "not named yet" with what to count and until when.
- What one extra enquiry, booked call and held call is worth at the founder's own rates.
- Three actions, each with a first step on a named day and an hour count.
- One-page PDF (standard library, no installs) and a markdown copy; memory file with the founder's best rate per stage so far, used as their own target next time.
