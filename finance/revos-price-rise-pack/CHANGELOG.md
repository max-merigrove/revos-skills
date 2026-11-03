# Changelog

## 1.2.0 (2026-11-02)

End-to-end round 1 fixes (general behaviour, not the scenarios).

- Founder wording without touching the skill: `reason` (a client's own one-line reason, used first), `new_client_line` (the founder's wording for the new-client sentence, `{hours}` filled per client) and `money_decimals` (2.750,00 € or 2.750 €). SKILL.md forbids editing the skill's own files; every change is an input and a rebuild. `memory.py write --retire "words"` and `--activate "words"` change a saved learning's status, so memory is never hand-edited.
- A founder in a hurry still gets every question that moves a figure (who to go gently with, a cost per client, notice for a client with no contract), in one message. "Go easy on", "spare" and "schonen" map to `gentle`, never `hold`.
- The headline says that the figures count Option A for a scope-reset client and what Option B would take off the 12 months and the run rate. The letters document opens with a one-line contents list naming the pushback replies. The rubric says the `[BUSINESS_AUDIT_URL]` placeholder stays until release.
- A founder's own reason in the third person HOLDs the letter, like a scope line.

## 1.1.0 (2026-11-02)

Blind-test fix round.

- Reasons are true for the client reading them: the new-client price is set beside the client's own hours ("2,800 for about 14 hours, which is 200 an hour; your work runs to about 22 hours"), and is never the reason for a fee above it; the "I've been with you for years" reply only says "below what new clients pay" when that is true for every raised client. `letters.py check` fails a letter that breaks this.
- Notice text is read whole: "3 Monate zum Quartalsende", "3 months to quarter end" and "to the end of the month" set the alignment; words after a notice that are not understood stop the run with a question; a notice and a `notice_align` that disagree stop.
- `ingest.py` keeps every column it does not read, and every notes column, under the client's `unread`, prints a NOTE for each, and splits the alignment out of the notice; a client with an `unread` note has its letter on HOLD.
- Scope lines go into letters in the second person: a third-person `scope_line` HOLDs the letter and `letters.py check` fails "they", "their", "them" or the client's own name in a READY letter body.
- Nothing of Merigrove in what the founder sees: the Assumptions notes say "default"; the Summary and letters footers carry the founder's business name; the credit stays in the file properties. Merigrove method and people removed from LICENSE and CHANGELOG wording.
- A client listed twice with different fees no longer blocks the first reply: `--provisional` (or `provisional: true`) plans on the higher fee and HOLDs that letter; `fee_unsure` records the figure the founder did not lean to. `check_copy.py --letters` lets a sentence that declines "effective immediately" or backdating pass. Bare weekdays ("thursday", "on Monday") are read as send dates. `decimal` accepts "dot", "comma", "." and ","; anything else stops with the accepted values. "ungefähr 14", "about 22 hrs" and "~1.2 lakh" are read.
- Call first is a ranked short list: the largest by annual fee among the clients who qualify, one per three letters, at most three (`call_first_max`). The Summary no longer repeats the planning-default notice flag; headers sit over their figures; the headline figures are larger; flag rows grow to fit.
- Return runs: confirmations state the agreed terms only ("stays at 55,000 until 4 April 2027, and from 5 April 2027 it is 66,000"); the follow-up says a leaver is counted at the old fee to their end date and what it would add if they paid the new fee. Rebuilds replace files under the same name and move the earlier copy into `superseded/`; files are named with today's date. Numbered lines no longer carry a bullet. `memory.py read` prints WATCH learnings; SKILL.md applies those that only change wording or format.
- Also: "Dear Frau Dr. Weiß," when the founder gives a title; reminders moved off non-working days; Option B's hourly figure compared with the extras rate in the plan; possessives such as "Orchid Interiors'".
- Description: adds day rate and hourly rate, annual fee review and uplift letters, repricing retainers and pushback on an increase; excludes a prospect who says a quote is too high and choosing clients to drop.
- Evals: the blind tester's two runs are now evals 9 and 10 with fixtures and sample runs; 44 new regression tests.

## 1.0.0 (2026-11-02)

First release (Wave 2a build).

- Plan per client: Hold, Price to keep, Reset the scope, At renewal, Two steps or Raise now, first match wins, with a call-first flag. Target from the founder's per-client target, else their new-client price scaled by hours, else an hourly target, else their own median rate (said aloud); no hours means a flat step marked "hours not given", and no hours anywhere is called a blanket rise.
- Dates from the founder's notice (days, weeks or months; month or quarter end alignment), billing day and billing months, renewals, terms and price locks; a renewal inside the notice period moves a year; a requested start can only move dates later; the last working day to send for a requested start; no backdating; weekdays printed.
- Cash over the 12 months from the send date beside the full-year run rate; annual prepay, quarterly and per-project clients handled.
- Break-even on contribution per client and for the list, by name in both orders, with the departure that breaks it, a loss table, a lumpy-count line, and an optional freed-hours line "only if you refill them"; checked against a brute-force pass over every subset of up to 12 raised clients.
- Workbook with live formulas (Summary, Plan, Break-even, Scenarios, Exceptions, Outcomes, Assumptions), verified against the script by recalculating in LibreOffice; CSV fallback without openpyxl. Letters document written with the standard library (how to send, call outline, letters by group, client by client, pushback, before you send); single-client mode without a workbook; return-run follow-up with confirmations and the next wave.
- Return run: outcomes (accepted, countered, left, held), realised against plan with a plain verdict line, every concession logged with an end date and its cost, next wave by gap and review date.
- Reads founder-typed figures in any style through `locale_numbers.py` (copied unchanged); STOP with one question on an ambiguous figure, two fees for one client, a fee under one unit, over 200 hours a month, a step over 50%, targets all below current fees, or a past send date. Lines written to an AI are ignored and reported.
- `check_copy.py` with the price rise list; `letters.py check` (fee and date in the first three lines, reason matches the plan, no empty field, HOLD on any [NEED]); `memory.py` read, write and validate; `ingest.py` for CSV, TSV, XLSX and JSON with no library, plus a scan for pasted notes.

Planning defaults (never presented as market facts): step cap 20%; one step when it reaches 95% of target; second step six months after the first; rounding down to 10 below 1,000 and 50 from 1,000; 60-day planning default for unknown notice; 12-month cash window from the send date; call first at four years' tenure or the largest quarter by annual fee; gentle halves the cap; break-even on direct costs only; freed hours only when the founder gives an hour's value; reply-by date two weeks before the effective date.
