---
name: revos-founder-time-audit
description: "Audits where a founder's week goes, from a calendar export or a description, ranks what to stop and hand over by the hours it gives back, shows what each handover costs against the founder's own rate, and writes the handover brief. Use when a founder says where does my week go, I'm working 60 hours and not growing, what should I delegate or hand off, what would I give my VA or assistant, is it worth paying a VA to take my admin, time audit, I'm the bottleneck, I never have time to sell, I'm drowning in admin, I'm stuck in the weeds, everything goes through me, or I can't step back. For founders of one to five person businesses anywhere, with a calendar export or none. Use this as soon as the founder asks, even before they have shared a calendar or any files; the skill asks for what it needs. Do not use for scheduling one meeting, booking or tidying a calendar, a team member's timesheet, monitoring staff, a to-do list for today, payroll or employment law questions on their own, or pricing an offer."
license: Proprietary, free to use in your own business. See LICENSE.md
metadata:
  version: 1.3.0
  author: Merigrove
  category: Operations
  updated: 2026-10-21
---

# Founder Time Audit

The founder walks away with last week's hours in three piles (only you, someone with instruction, nobody should), what to stop first, a handover list ranked by the hours it gives back, what those hours are worth at their own rate against what the help costs, the clashes in their calendar, a proposed week with a protected strategy block, and a handover brief for the first person taking work: a one-page report, a workbook they can change and a brief they can send.

**Value before questions.** The founder's first reply from you answers their question from what they gave: a provisional split of the week, what to stop, what each helper could take with hours and cost a week, and anything in their calendar or figures that does not add up. Questions come after that, only the ones whose answer would change the result. Never send a message that is only questions.

## Where files go

Every file the founder is meant to open goes where they can open it: `/mnt/user-data/outputs/` when that folder exists (claude.ai and Cowork), otherwise the current working folder (Claude Code). Never leave a deliverable in a scratchpad, temp or session folder; those are for working files only. Wherever this file says `<out>`, `<output folder>` or "the output folder", it means this location. After saving, name each file in the chat.

## Start

Your next message does useful work. Do not describe the skill or ask permission. Run the memory check. If the founder already attached a calendar or described their week, go to Intake. If not, first answer what they asked in a few plain lines from what they did say, labelled provisional (for "I'm working 60 hours and not growing": the usual pattern is delivery and admin crowding out selling, the first things to test for deletion are recurring meetings that make no decision, and the first handovers are the biggest repeating admin blocks; name what they mentioned), then say one line:

"Attach a calendar export for the last one or two weeks (Google Calendar: Settings, Import and export, Export; Outlook: File, Save Calendar, or export to CSV), or tell me what last week looked like day by day. Rough is fine; I'll ask about the email and admin a calendar misses. Say skip and I'll ask."

## Memory check

Look for `revos-founder-time-audit-memory.md` in this order: the working folder's `merigrove-memory/` subfolder, files attached to this chat, the Project's files. On claude.ai, Project files reach you as text, not files on disk: if you can see the memory file's contents, write them unchanged to `<scratch>/memory.md` and use that path. If found:

1. Run `python3 scripts/memory.py read <memory file> --out <scratch>`. It writes `map.json` (saved activity rules), `previous.json` (last audit and handovers) and `defaults.json` (profile, remembered rows, learnings).
2. Say in one line what you are using: "Using your audit from <date>: <n> sorted activities, <team>, and the <x> hours a week your calendar missed last time."
3. Skip every question it answers. Apply each `active` learning at the step it names. Ignore `watch` and `retired` rows.
4. Return run: no questions if the new export parses and every activity matches a saved rule. Personal entries are never saved, so sort them as personal again yourself, without asking. Otherwise ask at most one question, the one the result hinges on (usually "Roughly how many hours did you work last week?" or how a new activity should be sorted).

No memory file: first run.

## Intake

Draft from what the founder gave you first, then ask only what is missing. First run: at most five questions, in at most two founder turns. Return run: at most one.

**1. Read the calendar.** `python3 scripts/parse_calendar.py <files> --out <scratch>` (add `--map <scratch>/map.json` on a return run, `--weeks 1` if they said "last week", `--from`/`--to` for named weeks). The parser takes the time zone, the working week and any public holidays or days off from the calendar itself; pass `--tz`, `--work-days`, `--work-hours`, `--holidays` or `--date-order` only for what the founder has told you (or memory holds). Exit 2 or a `STOP:` line means nothing usable was read: ask the founder the one thing it names (which time zone they work in, whether their dates are day or month first). An `ASK:` line about the working week goes into question 1; an `ASK:` line listing all-day entries goes into question 5, asked by date and never by the entry's name. Never estimate hours from a calendar by reading it yourself.

**2. Sort it.** Read the activity list and `references/categories.md`. Write `<scratch>/map.json`: one rule per activity (`match` is words from the event titles, or `re:` and a pattern), with `activity` (a plain label), `category` (1, 2, 3, or `personal` or `not work`), `function` (strategy, selling, managing, delivery, admin), `action` (keep, delete, delegate, automate), `who`, `reason`, and `protected: true` for work the founder said stays with them. `personal` is the founder's private life (never saved); `not work` is placeholders, holds and buffers ("HOLD", "travel buffer"), saved so they stay out next time. Match on activity words or client company names, never on a person's name. Then run step 1 again with `--map`. Repeat until no work entry is left unsorted.

**3. Answer first, then ask, in one message.** Before you reply, copy `<scratch>/activities.json` to `<scratch>/audit.json`, add everything the founder has already said (Make step 1: business, team with cost and spare hours, sales or rate, week hours, what stays with them) and run `rank.py` into `<scratch>/results.json`. Exit 1 (`NEED:`) is fine at this point; with no week given it uses the calendar plus 20 per cent, flagged. A `STOP:` that only the founder can settle goes into the questions; give everything else. Then reply in this order:

- **The provisional answer.** One line saying it is from the calendar alone (or their description) and which answers would change it. Then where the time goes: the top activities with hours a week and hours a month from the scripts and your proposed pile and action, in a short table (at most twelve rows, then "and <n> smaller ones"). Then what to stop first and what each named helper could take: the `HELPER:` lines (hours a week against their spare hours, cost a week, and, when a rate or monthly sales is known, the share of freed hours that must earn the founder's rate for the help to pay for itself). If no rate is known, say the value comes once they give one.
- **What does not add up.** Every `CLASHES` line from the parser, in plain words, with the dates: double bookings, a meeting with a colleague the calendar shows as out, work booked on a day off, a call set in another time zone that lands inside a block, work over a personal entry (say "a personal entry", never what it is). Add anything in the founder's own figures that cannot all be true (handovers that exceed a helper's spare hours, a week total below the calendar). These are what a sharp assistant points out first; never leave them for the report.
- **The defaults you are assuming**, out loud: "Your calendar shows Monday to Friday, 8:30 to 17:00, New York time, so I'll lay the report out on Letter paper with a 12-hour clock. I've treated Friday 6 November (PTO) as a day off. I've left out <n> personal entries, declined meetings and all-day events. I've marked the Tuesday status call delete unless it produced a decision in the last four weeks. Freed hours go to selling unless you say otherwise." Every only-you row that reads as admin, email, reporting or scheduling gets its challenge here as a stated default with your best reason, so it costs no extra question: "I've left the evening email with you because clients write to you directly; say if someone else could take the first pass." Then ask only what is still unknown and would change the answer. Skip any question the founder has already answered (a founder who named each helper's cost and spare hours is not asked question 3); state the default instead. Usually that leaves questions 1 and 2.

1. "Roughly how many hours did you work in a typical one of those weeks, and how much of that was email, messages or admin that is not in the calendar?" When the parser printed a working-week `ASK:` (or there is no calendar), add: "and which days and hours do you usually work?" When neither the calendar's time zone nor their currency shows the country they work in, add: "and which country are you in?" Default: the calendar plus 20 per cent, flagged.
2. "What is an hour of your time worth?" (a) work it out from what the business bills a month: tell me the figure, in your currency; (b) I'll give a rate; (c) skip. Default (a) if they mention sales, else the value stays `[NEED]`.
3. "Who could take work today?" (a) nobody yet; (b) a VA or contractor: their name, what they cost an hour, and roughly how many spare hours a week; (c) someone on the team: who, and how much room they have. Name the hours a helper would take ("the inbox, client syncs and social scheduling come to about 7 hours a week"), so the answer settles capacity too. Default (a). If the handovers to one person exceed their spare hours, the lowest-ranked ones wait until they have room; say so in the summary rather than asking.
4. "Anything that must stay with you?" Default: sales calls and the client work people buy you for.
5. "Anything in the list in the wrong pile, or a public holiday or day off in those weeks I haven't marked?" Name the dates from an all-day `ASK:` line here.

If a multiple-choice question tool is available, use it for questions 2 and 3 with the free-text escape. Otherwise ask in one message and say: "Answer like 1: about 55, 2a: 22k, 3b, or say skip."

**The founder's locale.** Currency, numbers, dates, paper, clock and working week follow the founder; never assume a country. Take the currency from the marks on their figures (S$, A$, £, €, ¥, "USD", "yen"); a bare "$" with nothing else to go on is shown as "$". Paper size, date order and clock come from the country they work in, never from their spelling: `rank.py` reads it from `locale.country` (set it when they name a city or country: Tokyo is JP), else their calendar's time zone, else a currency only one country uses; with none of those it uses A4, day first and a 24-hour clock and says so. Their decimal style (1,234.56 or 1.234,56) is detected once from what they typed, and every figure is written back the same way. Spelling only sets `locale.spelling`. Record them in the audit file (`references/audit-file.md` section 2). If something the result depends on is still unknown, it belongs in the five questions, not a sixth.

**No calendar (recall).** Pull every activity out of the founder's description into rows with `"source": "recall"` (see `references/audit-file.md`), read them back in one block with hours each and how often, and ask the same questions. A recall audit is always labelled low confidence, and you offer the one-week log (`assets/one-week-log.xlsx`, or `assets/one-week-log.csv`) for a proper run next week. When they work different hours on some days ("Saturdays only mornings"), record `work_hours` per day; work they do at set times outside the day (evening calls with US clients) is marked `fixed` and stays where it is in the proposed week.

**No calendar (recall) first reply.** Same order: the rows read back with hours each and how often, then the provisional split, deletions and handovers from `rank.py` on the recall rows, then the questions.

**Turn two, only if needed.** After their answers, run Make step 1. `rank.py` collects everything it needs in one pass: values it could not read, figures that cannot be right (an hour worth less than a helper costs, a week outside 10 to 100 hours), a challenge the founder objected to, a capacity `NEED`. Ask them all together in one short message, then build. This is the founder's second and last turn before the report.

## Diagnose

In one line, name the job and the evidence:

- **Calendar audit:** a calendar export covers the weeks; the week total comes from the founder. Confidence comes from how much of the week the calendar holds.
- **Tracked week:** the one-week log was filled in. Highest confidence.
- **Recall audit:** no calendar or log. Low confidence, said at the top of the report.
- **Return run:** saved memory plus a new export. Change only what the new weeks show; report what moved and whether each handover held.
- **Stop:** the request is to audit or monitor someone else's time, or the files are not a calendar. See Rules.

## Make

| If the task is | Read |
|---|---|
| Sorting entries into piles, functions and actions | `references/categories.md` |
| Choosing delete, delegate, automate or keep, and who | `references/handover-order.md` |
| The arithmetic, flags, value of time, the proposed week | `references/method.md` and `references/thresholds.md` |
| Building the audit file, recall rows, messy answers | `references/audit-file.md` |
| Seeing a finished run | `references/examples.md` |
| Always, before writing the note or the chat summary | `references/banned-patterns.md` |

1. If the founder corrected their working week or named a holiday, run step 1 again with `--work-days`, `--work-hours` or `--holidays`. Copy `<scratch>/activities.json` to `<scratch>/audit.json` and add what the founder said: `business`, `currency` and `locale` (with `country` when known), `stated_week_hours`, `monthly_revenue` or `rate`, `team` (name, role, `cost_hour` as the founder states what that person costs them, `spare_week`), `protected`, `freed_to`, `work_days` and `work_hours` for a recall audit, and the recall rows for time the calendar missed. Pass the founder's words as written ("50-55", "about 450万 a month", "4.5 million yen", "2,4 lakh", "mon to fri", "hour, hour and a half", "9pm to 10:30-ish"); the scripts read them, multipliers and day ranges included. Never add, divide or convert figures yourself, and never resolve a multiplier (万, k, million, lakh) or a unit: leave those exactly as typed. The one restatement allowed is turning a spoken figure into digits when it reads only one way ("three and a half" to "3.5"); that still counts as passing it as written. Leave rows from `repeats_outside_window` in unless they are not real work (set `"include": false`). On a return run, copy the `defaults.json` values in, and add its `remembered_rows` only for time the new calendar still misses. When the founder says what to hand over first ("Ana's work before Jules's", "social scheduling first"), set `founder_order` to those activity labels in their order: their order wins, the report says "in the order you chose" and shows what the hours alone would say. Never drop or move a handover out of the list to honour an order.
2. Run `python3 scripts/rank.py <scratch>/audit.json --out <scratch>/results.json` (add `--previous <scratch>/previous.json` on a return run). Exit 2 or `STOP:` means fix the audit file, or put every question it lists to the founder in one message: an unreadable value is restated by them; a figure that cannot be right is corrected, or, if they say it is right, its name goes in `"confirmed"`. Exit 1 lists `NEED:` and `CHALLENGE:` lines: a `CHALLENGE` the founder did not answer at the read-back is asked once, and its answer goes in that row's `challenge_answer` as a short clause in their terms, not a verbatim quote ("clients write to you directly, so it stays with you"); the row moves pile only if the founder agrees. A `NEED` about capacity appears only when the founder asked to keep every handover (`"capacity_waits": false`); a `NEED` about the week or the rate may stay as a flag.
3. Write `<scratch>/note.md`: at most 90 words on what this week says about this founder, in their words where they gave them. Name the pattern (delivery crowding out selling, admin leaking into evenings) and the one judgement the numbers leave open. Copy every figure exactly from `results.json`.
4. Run `python3 scripts/report.py <scratch>/results.json --out <output folder> --note <scratch>/note.md --md <scratch>/summary.md`. It refuses to build while a challenge is unanswered or the note holds a figure it did not compute. Exit 2 or `STOP:` means nothing was written: fix and run again.

If code cannot run here, say so in one line, total the hours by hand in a table the founder can check (hours each, times a month, hours a month), apply the same rules from `references/method.md`, and deliver the report as text.

## Check

1. `python3 scripts/reconcile.py <scratch>/results.json --events <scratch>/events.json --summary <scratch>/summary.md` (leave out `--events` for a recall audit). Fix every PROBLEM at its source and rebuild until it prints 0 problems.
2. `python3 scripts/check_copy.py <scratch>/summary.md` and on the note. Fix every PROBLEM.
3. Score against `references/rubric.md`. All nine must pass; rework rather than caveat.
4. Fresh eyes: if subagents are available, give one the summary, `results.json` and the rubric only. Otherwise reread the summary cold as the founder. Ask: could a real person take the top handover next week? Does any figure read as cash when it is time? Is anything personal visible?

## Deliver

Give the founder the files from the output folder (on claude.ai, `/mnt/user-data/outputs/`): `founder-time-audit-<business>-<date>.docx`, the one-page report to read first, and `...-workings.xlsx`, the full log with live formulas where yellow cells are theirs to change. For a recall audit, or whenever the report shows hours not placed in any activity, also give `assets/one-week-log.xlsx` (the report points to it).

**The handover brief.** For the helper with the top handover (or the one the founder chose to start with), run `python3 scripts/brief.py <scratch>/results.json --who <name> --out <output folder> --events <scratch>/events.json` (leave out `--events` for a recall audit). Put anything the founder has said about how the work is done, what stays with them, when to come back to them and when to start into `<scratch>/facts.json` in their words (see the script's header) and pass `--facts`. Run `check_copy.py` on the brief's `.md`. It never holds pay or contract terms; what the founder has not said stays in brackets, never invented. Give the `.docx` and name the two or three brackets that matter most, so they can answer in one line and you rebuild it. Offer the next helper's brief in one line.

Then a chat summary that carries the findings, so a founder who never opens a file still has them (at most seven short lines):

1. The headline split of the week, with the confidence.
2. The first deletion and the top handover, with hours a week and a month.
3. The value of the hours and what the help costs, a week and a month, and each helper's pay-for-itself share, or the `[NEED]` that blocks it.
4. Clashes or figures still unresolved, or "No gaps".
5. The handover brief and the brackets to fill.
6. What will be remembered if they approve (Learn).
7. Their first move this week, such as cancelling the next status call or walking Ana through the brief on Thursday.

## Learn

Ask one question with options: Spot on / Close, small changes / Wrong piles for my business / Wrong hours. Anything but "spot on": if they have not already said what to change, ask "What would you change?"; do what they asked, in their order, by editing the rows in `audit.json` (category, action, who, hours), rerun rank, report and the checks (at most three rounds), then propose the lesson as a rule with its evidence and the step it applies to ("Proposals stay only-you; moved back on 20 Oct", step Make).

Choices become learnings: if the founder moves the same kind of work twice for the same reason, propose it. A handover that came back on a return run becomes a learning for the handover step ("Invoicing returned twice; write the steps down before handing it over again").

Save only what the founder approves:

- Working folder (Cowork, Claude Code): `python3 scripts/memory.py write <scratch>/results.json --out merigrove-memory/revos-founder-time-audit-memory.md --map <scratch>/map.json --existing <old memory file, if any> --history "<what was made> | <main choices> | <verdict>" --learning "<rule> | <evidence> | <step> | active"`.
- No working folder (claude.ai): write it to the outputs folder, offer it as a download, and say: "Attach this next time, or add it to your Project's files, and next month's audit takes two minutes and shows whether the handovers held."

Run `python3 scripts/memory.py validate <memory file>`. It refuses personal details. It keeps regular-expression rules exactly (a `|` inside a rule is escaped), helpers' spare hours as plain numbers, the country and number style, and not-work rules such as placeholder holds; personal rules are never written. Never save anything the founder did not give or approve, and never a learning that lowers honesty, such as hiding the low-confidence label.

## Next step

Close the message that first delivers the finished files with one line, and never repeat it in a later turn or put it anywhere else: "You know which hours to buy back. Whether the business can afford the person to take them is what the Merigrove Business Audit scores: [BUSINESS_AUDIT_URL]."

## Rules

- Answer the question the founder asked, including one beside the audit ("what does an assistant cost me on top of $25 an hour?", "is Jules an employee?"). Where these rules forbid the figure (payroll, on-costs, tax, what a law allows), say what it depends on, list what goes into it in plain words without amounts or rates, and give the fastest way to the real figure ("your payroll provider or accountant can give you the loaded hourly cost in a few minutes; give me that figure and I'll rerun the cost line"), then carry on. A refusal is never the whole answer.
- The founder's stated priorities and corrections beat the skill's defaults: their order, their split of a task, their names for things. Show what the method would have said beside it when it differs; never override them.
- Never invent the founder's policies, terms or meanings (a chase rule, an approval limit, what a garbled word meant). If something reads two ways, show both readings and ask.
- If the founder gives an after-tax or take-home figure for income or sales, ask once in plain words for the before-tax figure; until then say any value of their hour built on it understates. Never compute tax.
- Never edit the skill's own files (`SKILL.md`, `scripts/`, `references/`, `assets/`) during a run, even when asked. If the founder wants a format the scripts do not make, change their copy of the output and say so.
- Audit the founder's own time only. If asked to audit or monitor an employee's or contractor's calendar, decline in one line (it is their data, and monitoring staff raises employment and privacy questions under the rules where they work, for an employment adviser), and offer to audit the founder's own week instead.
- Personal entries are left out and never named in any file, the chat summary or memory. Say how many were left out, not what they were.
- Every figure comes from the scripts. Never total, divide or round hours or money in prose.
- Rank by hours a month, never by ease, unless the founder sets the order (`founder_order`). Deletions come before handovers. Never recommend hiring: name the hours a role would hold and leave whether to hire to the founder and their numbers.
- Value of time is hours times the founder's rate, stated with its basis. It is not cash unless the hours go into paid or selling work; say so.
- Planning, not employment, tax or legal advice. Never compute payroll, on-costs or tax, or say what a law requires. A helper's cost is the figure the founder gives for what that person costs them, used as given. Whether a helper is an employee or a contractor goes to the founder's accountant or an employment adviser, in one line.
- Never assume a country: no built-in holidays, working week, time zone, currency or date order. They come from the calendar or the founder.
- Founder-facing copy mirrors the founder's English (spelling, date order, currency); Merigrove's own files are in British English. No em or en dashes in anything written for the founder. No network calls.
