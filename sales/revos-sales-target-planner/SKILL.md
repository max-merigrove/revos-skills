---
name: revos-sales-target-planner
description: "Works back from the profit a founder needs to the sales, calls and leads each month takes, checks it against their calendar and names what breaks first, in a live spreadsheet. Use when a founder asks how many sales or discovery calls do I need a week or a month, how many leads for 40k, work back from my target, reverse pipeline, is my target realistic, I keep missing my number, I hit revenue but there's no profit, I'm busy but the month never lands, how many retainer clients do I need, or do I need a setter or can I hit my target myself. For founder-led service businesses that sell on calls. Use this as soon as the founder asks, even before they have shared numbers or files; the skill asks for what it needs. Use this even if the founder does not name it. Do not use for forecasting named deals in a CRM, reviewing a sales call, writing outreach or call scripts, a cash flow forecast, or pricing an offer from its costs."
license: Proprietary, free to use in your own business. See LICENSE.md
metadata:
  version: 1.3.0
  author: Merigrove
  category: Sales
  updated: 2026-10-21
---

# Sales Target Planner

The founder walks away knowing the sales, held calls, bookings and leads their profit target needs each month and each week, every rate labelled measured or assumed, whether their calendar can carry it, the one thing that breaks first with its number, what each lever buys, a dated first week, and a workbook where they can move any lever and watch the plan move.

## Where files go

Every file the founder is meant to open goes where they can open it: `/mnt/user-data/outputs/` when that folder exists (claude.ai and Cowork), otherwise the current working folder (Claude Code). Never leave a deliverable in a scratchpad, temp or session folder; those are for working files only. Wherever this file says `<out>`, `<output folder>` or "the output folder", it means this location. After saving, name each file in the chat.

## Start

Your next message does useful work. Do not describe the skill or ask permission to begin. Run the memory check first.

**Value before questions, always.** Whatever the founder gave, the first reply answers their actual question with substance before it asks anything:

- **Figures given** (a price, a target, hours, rates, an export): build the plan now on what they gave plus labelled defaults, and lead with the answer to what they asked ("You need 25 bookings a month, about 5.8 a week"). Then ask at most the questions whose answer would change that figure, each with what it would change ("If calls take 1.5 hours, not 1, the calendar use goes from 3.9 to 5.9 of your 10 hours, so the plan still fits").
- **No figures yet** ("I keep missing my number"): give the chain in four plain lines, with their words where they gave any (profit plus running costs, divided by what one sale leaves, is the sales a month; sales divided by the close rate is held calls; held calls divided by the show rate is bookings; bookings divided by the booking rate is leads), and the four places a month usually breaks, in the order the plan checks them (calendar or delivery, show rate, lead volume, close rate), naming the one their words point to if they do. Then ask questions 1 and 2 in the same message, with: "Or paste your numbers (a CRM export, last quarter's calls, a voice note) and I'll pull them out. Say skip on anything and I'll use a labelled default."

**Answer the question beside the plan.** If the founder also asks something next to it ("do I need a setter?", "what would a hire cost me?", "is 6 hours enough?"), answer it in the first reply from the plan's own figures: the Hiring line answers the setter question, the calendar line answers the hours question. Where the rules forbid a figure (tax, payroll charges, what a law allows), say what it depends on, list what goes into it in plain words without amounts or rates, name the fastest way to get the real figure (their accountant or payroll provider, by name where their material shows one), then carry on. A refusal is never the whole answer.

**Two readings, show both.** Where something the founder wrote reads two ways and the reading changes the answer (a yearly figure that could be a run rate or money by a date, two different call lengths, a figure the script stops on), never pick one silently and never present a guess as their meaning. Run the plan both ways (two inputs files), put both headline figures side by side in two lines, build the workbook on the reading their words support best and say which and why, and ask which is right. Once the founder picks a reading, the plan follows it. If they later ask for the workbook on the other reading, build it, keep their stated target in view in one line (its headline, and what the ceiling reaches by the date), and save both to memory: `--history "target stated as <their reading>; workbook on <the other> at your request | ..."`. Where both readings give the same verdict, say so in one line ("at 1 hour or 1.5 hours the calls still fit") and ask once.

**Catch what does not add up.** Before building, read the founder's material as a sharp adviser would and say early, in one line each, anything that conflicts: two figures for the same thing in different places, counts that cannot both be true (more sales in 90 days than clients paying now on a monthly fee, leads per channel that do not sum to the total), a target date already past or months left that do not match the date, a "nothing left" with costs that leave plenty. Never resolve it yourself; show it and ask.

**Their language.** Reply in the language the founder writes in, never the language of their country: an English message from Paris gets English, with their figures in their number style. The workbook is in English; say so once only if they write in another language.

**Their material, in their terms.** Refer to what the founder gave as they would: "your notes", "your second message", "your Pipedrive export". Never quote a label from inside a file ("Founder 3", "User 2", "Speaker 1"); a pasted transcript or notes file is the founder's own words. `check_copy.py` refuses such labels.

## Memory check

Look for `revos-sales-target-planner-memory.md` in this order: the working folder's `merigrove-memory/` subfolder, files attached to this chat, the Project's files. On claude.ai, Project files reach you as text in the conversation: write the contents unchanged to `<scratch>/memory.md` and use that path. If found:

1. Run `python3 scripts/memory.py read <memory file> --json-out <scratch>/previous.json`.
2. Say in one line what you are using: "Using your plan from <date>: <sales> sales a month at <price>, <hours> selling hours a week, <n> months of actual figures." If `read` printed IGNORED for tax rows from an earlier version, add: "Your saved file has tax rows from an earlier version; this planner no longer uses them."
3. Skip every intake question it answers. Apply each ACTIVE LEARNING line at the step it names. Do not apply `watch` or `retired` rows.
4. If the founder's message gives last month's figures, re-plan at once. If not, re-run the saved plan as it stands (it is still the answer to "what should this month look like"), show its headline, and ask the one return-run question: "What actually happened last month: how many enquiries, calls booked, calls held and sales?" For a monthly fee, add "and how many clients are paying you now?"

If no memory file is found, this is a first run.

## Intake

Draft from whatever the founder gave first, following `references/intake-guide.md`. If they attached a CRM or spreadsheet export of leads, run `python3 scripts/count_export.py <file> --today <today> --json-out <scratch>/counts.json`: it reads UTF-8 or Windows-1252 exports, headings and statuses in English, French, Spanish, German, Portuguese, Dutch or Italian, and counts leads, bookings, held calls and sales for the last three whole months and by source. Read back how it read each status. While any status is UNMAPPED it writes no counts file: plan on the founder's estimates or defaults meanwhile, put the UNMAPPED status into your questions, then re-run with `--map "Status=stage"`. Never convert the file yourself. Take the currency, number style (1,250.00 or 1.250,00), spelling and working week from what they wrote, and the country for date order and paper size (`references/intake-guide.md` section 2); never assume a country, and if nothing shows it, add "Which country are you in?" to the questions. If the export's dates could be read either way, `count_export.py` stops: put "Do you write dates day first or month first?" into your questions.

The questions come after the plan, in the same message, and only those whose answer would move a figure in it: at most three in that message, and any two that touch the same figure (hours a week and hours a call, for example) merged into one. First run: at most five questions in at most two founder turns. Return run: at most one. Follow the founder's stated priorities and corrections over the order below. If a multiple-choice question tool is available (AskUserQuestion), use it for questions 3 to 5, at most four questions per call, with the free-text escape. Otherwise ask in one numbered message and say: "Answer like 1, 2, 3b, 4a, 5a, or say skip."

The five, in priority order, each asked only if still unknown:

Never ask what the founder has already said (before tax, pay inside the figure, the call length); confirm it in the read-back instead.

1. **The target.** "What profit does the business need to make each month once every cost is paid? Is that before tax, or what you want to take home? And is your own pay inside that figure or on top of it?" No default for the profit. If the founder gives a yearly figure or a date ("250k this year", "by June"), ask: "Is that the yearly rate you want to be running at, or money you want made between now and then?" and show both readings meanwhile (Start). Never divide a yearly figure by 12 until they say it is a run rate. If the founder only has a revenue figure, plan from it and flag it. If they did not say before tax or take-home, plan it as before tax and say in one line that if it is take-home, every figure in the plan understates what they need, and their accountant can give the before-tax figure; never work out tax.
2. **Price and costs.** "What does one client pay for your main offer, before any sales tax: once, or a fee every month? Roughly what does one cost you to deliver (freelancers, tools, materials, not your own time; a month, for a monthly fee), and roughly what does the business spend a month with no clients?" For a monthly fee (retainer, subscription, membership) add: "How many clients pay you now, how many months does a client usually stay, and how many can your team serve at once?" Add "in which currency?" only if no figure shows it. No default for the price. Without delivery cost the plan runs from revenue, flagged. If the price includes sales tax ("incl GST", "TTC", "inkl. MwSt"), ask for the figure before it; never take tax off yourself.
3. **Your rates.** "Of 10 calls booked, how many turn up? Of 10 held, how many buy? If you've counted (enquiries, booked, held, sold for the last three months), paste the counts instead." Options: (a) I've counted, here they are; (b) rough figures; (c) no idea. Default (c): the planning defaults, labelled.
4. **Your time.** "How many hours a week can you give to sales calls, and on which days? Roughly how long does one take with prep and follow-up? Is there a cap on new clients a month you can deliver for? Any days off coming up?" Options for hours: 4, 8, 12, or type your own. Default: 8 hours, Monday to Friday, 1.5 hours a call, no delivery cap.
5. **Cash.** One-off prices only: "When a client signs, how much of the price lands that month?" Options: all of it; half; a third; type a percentage. Default: all of it. A monthly fee lands each month, so skip it.

State the defaults in use in one line beside the plan: "I've used 1.5 hours a call, calls Monday to Friday, 20 selling days a month and the planning rates of 60 per cent show and 20 per cent close, all labelled; tell me if any is wrong." Name only the defaults actually in use. Never ask in jargon. Never accept a hoped-for rate as a rate: plan on what has happened (`references/intake-guide.md` section 4).

## Diagnose

In one line, name the job and the evidence:

- **First plan from profit:** a profit target and costs, no saved plan. Build everything.
- **Revenue-first:** only a revenue figure, or the founder asked "how many calls for 40k". Build it, flag the profit gap, offer to re-run from profit.
- **Re-plan with actuals:** a saved plan plus last month's counts. Counts replace estimates; change nothing else the founder did not mention.
- **Test a lever:** the founder wants one change tried ("what if I charged 4,500", "what if I had 12 hours"). Change that one input and rebuild beside the saved plan.
- **Not enough to plan:** no price, or no target of any kind. Ask questions 1 and 2 first.

## Make

Load only what the task needs:

| If the task is | Read |
|---|---|
| Turning what was pasted into the inputs file | `references/intake-guide.md` |
| Any run: the arithmetic, the tags, the order of constraints, the defaults | `references/method.md` |
| You want to see a finished run | `references/examples.md` |
| Always, before writing the note or the chat summary | `references/banned-patterns.md` |

1. Write the inputs file to your scratch folder (fields in `references/intake-guide.md` section 1), passing the founder's own wording for figures exactly as they wrote them ("15.000 €", "1,5h", "68,3%", "₹6 lakh") and recording where each came from under `sources`. The script reads every figure in the founder's number style; never rewrite one. Set `country`, `currency`, `spelling`, `call_days` and, for a monthly fee, `billing`, `months_retained` and `active_clients_now` from what the founder said; a yearly figure goes in `target_profit_year` with `target_kind` ("run rate" or "by date") and `target_date`; profit already made towards a dated target goes in `made_so_far` (the script takes it off and adds it back in what the ceiling reaches); for a monthly fee, the most clients the team can serve at once goes in `active_clients_max` (it caps paying clients, and where the target needs more it is what breaks, with the fee that fits); counts for the month in progress (from `count_export.py`'s `month_to_date`, or the founder's own) go in `month_to_date` with the date they run to, and the plan shows that month against the pace without touching the rates. Leave a field blank only when nothing shows it, and the plan says its default out loud. Never add, divide or convert a figure yourself, in the inputs or in the chat (a year-end total, a figure a day, a target less what is made); write the parts ("=4450 - 1200") or the field and let the script work them out. If the script does not print a figure the founder asks for, say what it is made of in words and which printed figures to read it from, never a number of your own. On a return run, copy `previous.json`, set `date` to today, add last month's counts to `actuals`, and edit only what changed. Script paths are relative to this skill's folder.
2. Run `python3 scripts/target_plan.py compute <inputs.json>`. Read the headline, the binding constraint, the `CHAT-` lines and every `NEED:` line. If a NEED can still be answered inside your question limit, ask; otherwise it stays in the plan. A `STOP:` that says "Ask the founder" is a figure the script would not guess (it reads two ways, holds two figures, or is implausible, such as a 15-hour call): put that one question to the founder in their words, never pick an answer yourself; where you can, run the plan once on each reading and show both headlines beside the question (Start). If they confirm an unusual figure, add its field to `confirmed` and run again.
3. Write a note of at most 120 words to `<scratch>/note.md`: what the plan means for this founder, in their words where they gave them, and the one move it calls for. It sits under the headline on the Plan sheet, so never restate the headline ("Nothing breaks at these rates..."); the build refuses a note that does. Copy every figure exactly from the compute output; the build refuses any figure it did not compute.
4. Run `python3 scripts/target_plan.py build <inputs.json> --out <output folder> --note <scratch>/note.md --json-out <scratch>/results.json`, adding `--previous <scratch>/previous.json` on a return run. Exit 0, or exit 1 with a `WROTE:` line, means the workbook was written (exit 1: with [NEED] lines, expected when something was skipped). Exit 2, a `STOP:` line or a traceback means nothing usable was written: never show figures from that run. Read the STOP reason, fix the inputs file or ask the founder for the one figure it names, and run again. If the STOP says each sale loses money, that is the answer: tell the founder plainly that the price comes before any sales plan, and offer to plan again once the price or delivery cost changes.

The output folder is `/mnt/user-data/outputs/` when that folder exists (claude.ai), otherwise the working folder.

If code cannot run here, say so in one line, work through `references/method.md` sections 1 to 12 by hand, show each step's figure in a table so the founder can check it, and give the formulas from method.md to paste into a spreadsheet.

## Check

Before showing anything:

1. Run `python3 scripts/check_copy.py <scratch>/note.md`, and on every chat reply before you send it with `--chat --text "..."` (the chat mode also refuses any sales-tax mention that is not a question for the before-tax price). Fix every PROBLEM, including any untagged rate, and rebuild until it prints 0 problems.
2. Score the plan against `references/rubric.md`. Rework anything below the bar by changing the inputs or the note, never by editing figures.
3. Fresh eyes: if subagents are available, give a fresh subagent the plan text, the inputs file and the rubric only, and apply its findings. Otherwise read the plan cold as the founder: could they act on the first action without asking anything, and does every figure in the chat match the workbook?
4. No invented figures, clients or benchmarks. A gap stays `[NEED: ...]` and the plan says what would fill it.

## Deliver

Give the founder one file: `sales-target-plan_<date>.xlsx`. Its Plan sheet is the plan in plain words and prints to one page width, with the headline, the first action and the weekly pace together at the top; Week by week is a table of the coming weeks (six unless `weeks_ahead` says otherwise, up to 26), each scaled to its selling days and days off, with a total row; Try a lever holds yellow input cells and live formulas; Scenarios shows what each lever buys; Assumptions lists every default and source. In `sources`, record only where a figure came from ("founder said", "Pipedrive export"), never a reading of it.

Never edit the workbook by hand: a hand edit drops the calculated values a viewer shows and vanishes at the next rebuild. Meet a layout request through the script: point to where it already sits (pace beside the first action, the Week by week table and its total), or change an input and rebuild (`weeks_ahead` for more or fewer weeks). A request beyond that goes into the chat as a table they can paste and, where it fits, into the note at the top of the Plan sheet. To put anything at the top of the Plan sheet, write it into the note (it sits directly under the headline) and rebuild. The plan already prints the pace a selling day as well as a week, and this month against the pace when `month_to_date` is given. Whole calls instead of decimals: set `pace_whole` to yes and rebuild (rounded up so the month is still met, or down where a ceiling caps the pace). Never tell the founder you cannot change the workbook; say where the thing now sits. If a message is unclear, ask what they meant in one line; never say the founder misled you.

The chat carries the answer on its own: a founder who never opens the file must still see every key figure. Lead with the answer to the question they asked, then at most five short lines:

1. The headline, copied from the plan, then `CHAT-BREAKS` word for word, so what breaks first is never buried. Whenever the plan prints `CHAT-DATE` (months left and whole months of selling) or `CHAT-REACH` (what the ceiling reaches instead and, for a monthly fee, the profit the next 12 months make), copy them into the first reply, for each reading shown. For a yearly target on a monthly fee, that 12-month profit is the plain answer to "will I make it this year": say it.
2. The monthly numbers and the weekly pace (`CHAT-PACE`, word for word): sales, held calls, bookings (and leads where known), and each rate named as the plan names it (booking rate, show rate, offer rate, close rate; the share of held calls that get a proposal is the offer rate, never a close rate), with its tag in brackets.
3. The lever that buys the most: copy `CHAT-BIGGEST-LEVER` word for word, so the chat never disagrees with the workbook. Never call a gap the thing that breaks when the plan says nothing breaks.
4. Any [NEED] and what it would change, or "No gaps".
5. The first action with its own date, copied from `CHAT-FIRST-ACTION` (never "Monday" unless that date is a Monday), and the re-plan date from `CHAT-REPLAN`. On every rebuild, copy the `CHAT-` lines from the new run, never from an earlier one.

Then any conflicts you caught and the questions that would change the plan (Start, Intake), then the feedback question (Learn).

Say nothing about sales tax in the chat beyond the before-tax or take-home question and a [NEED] for a price that includes it. Never explain what HT, TTC, VAT or GST means or how a price was read: the plan's one neutral line covers it.

## Learn

Ask one question with options, once, at the first delivery: Spot on / Close, small changes / Wrong figures or assumptions / Wrong for my business. Never ask it again in the run, not even after a rebuild. Anything but "spot on": ask "What would you change?", change the inputs and rebuild (at most three rounds; the founder may move a lever by name, such as "try 12 hours" or "what if 7 in 10 show"), then propose the lesson as a rule with its evidence and the step it applies to ("Calls take 2 hours with prep; corrected on 20 October", step Make).

After the first change, say in one line what changed and which figures moved (or that none did), and offer once: "Say save when you are happy and I'll save the plan for next month." That offer appears in one message only. After later changes, end on the change itself, with no question, unless the founder asks whether the plan is good: then answer yes or no with the reason. Once the plan is saved, the run is done; do not invite another round.

Choices become preferences: if the founder picks the same lever twice for the same reason, propose it as a learning.

Save only what the founder approves:

- Working folder available (Cowork, Claude Code): `python3 scripts/memory.py write <inputs.json> --results <scratch>/results.json --out merigrove-memory/revos-sales-target-planner-memory.md --existing <old memory file, if any> --history "<what was made> | <lever chosen> | <verdict>" --learning "<rule> | <evidence> | <step> | active"`.
- No working folder (claude.ai): write it to `/mnt/user-data/outputs/revos-sales-target-planner-memory.md`, offer it as a download and say: "Attach this next time, or add it to your Project's files, and I'll pick up where we left off. Next month, tell me what actually happened and the re-plan takes two minutes."

Run `python3 scripts/memory.py validate <memory file>` after writing. Never save anything the founder did not give or approve, and never a learning that lowers honesty (such as dropping a rate's tag or planning on hoped-for rates).

## Next step

Close with one line, and nothing else promotional anywhere in the run: the `CHAT-CLOSING` line of the plan you are handing over, copied word for word, as the very last line of every message that hands over a new or changed workbook or saves the plan (after any question or offer). Never put it mid-message, and never on a message that only answers a question.

## Rules

- Start at profit. Revenue-first only when that is all the founder has, and say so.
- Every figure in the chat, the note and the file comes from `target_plan.py`. Never add, divide or round a figure in prose.
- Every rate carries its tag wherever it appears. Never plan on a hoped-for rate.
- Value before questions: every first reply answers the founder's question with figures before it asks anything.
- Never present a guess as the founder's meaning, policy or figure. Two readings are shown, not chosen.
- The calendar is checked before any plan is called possible. The weekly pace never exceeds what the calendar or delivery carries.
- Cash is reported beside sales and never multiplies them.
- A monthly fee is recurring revenue: plan the paying clients the target needs, the clients already paying, the clients who leave, and the new clients a month to get there by the date. Never fold months into one price.
- A target with a date is planned to that date, with the months left said out loud.
- A planning tool, not financial, tax or legal advice. Prices are planned before any sales tax, said once in the plan; nothing is added to or taken off a price. Before tax or take-home is always asked; tax is never worked out or estimated, and no rule of any country is stated. Any such figure comes from the founder's accountant and is used as given.
- Never present a default as a fact about other businesses.
- Global by default: the founder's currency (never converted), date order, spelling and working week. Never assume a country, its holidays or its institutions. No em or en dashes in anything written for the founder.
- No network calls. Nothing leaves the founder's machine or chat.
