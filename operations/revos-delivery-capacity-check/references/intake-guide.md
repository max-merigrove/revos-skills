# Intake guide: from what the founder says to the inputs file

Contents
1. The inputs file
2. Drafting the steps from a description
3. Reading messy figures
4. Offers that are not simple
5. People: helpers, contractors, tools
6. The questions, and how to ask them

## 1. The inputs file

Write one JSON file in your scratch folder and pass it to `scripts/capacity.py`. Pass values as the founder gave them ("1-2 hrs", "30 mins", "every other week", "about a dozen"): the script reads them and says how. `python3 scripts/capacity.py template` prints an empty file.

| Field | Meaning | If missing |
|---|---|---|
| `business` | Name for the file and title | "Your business" |
| `date` | Run date, YYYY-MM-DD | today |
| `country` | Where the founder is based, from what they mention: a code (`US`, `MY`), a name, a demonym ("Malaysian", "Kiwi") or a city ("KL", "Denver"). Sets paper size and date order (`locale_numbers.locale_defaults`) | left out: A4 and day-first dates, said out loud; an unknown place is dropped with the same line, never a STOP |
| `english` | The founder's spelling, from how they write: `American`, or leave it out for their own English | follows the country only when not given; never sets paper or dates |
| `locale` | Older inputs and memory files: `en-US` and similar. Read as `english`, and its region as `country` when `country` is missing | |
| `number_style` | `dot` (1,234.5) or `comma` (1.234,5), only if the founder says so | detected once from their figures; mixed styles ask one question |
| `paper` | `A4` or `Letter`, only if the founder asks for the other one | follows `country` |
| `delivery_hours_week` | Hours a week the founder can give to delivery, after selling, admin and their own marketing | 25, flagged [NEED] |
| `delivery_hours_month` | Use instead when the founder gives a month's figure; the script turns it into a week over the working weeks | |
| `working_hours_week`, `selling_admin_hours_week` | Use instead when the founder gives the total and the split; the script subtracts. "12 hr x 6 days", "12 hours a day, 6 days a week" and "9 hours mon-sat" are read as day x days | asks for the split |
| `target_working_hours_week` or `target_delivery_hours_week` | The week the founder wants to be working, asked inside the hours question when they work over about 50 hours or mention evenings or 12-hour days. The ceiling uses it; today's week is shown beside it | a NEED: the reading says it takes today's long week as the plan |
| `delivery_hours_now_week` | Roughly how many hours a week delivery takes now | the hours check is skipped |
| `weeks_off_year` | Time off a year, holidays and public holidays included, as the founder says it ("3 weeks", "25 days"); the script takes it from 52 | 6 weeks off (46 working weeks), said out loud |
| `working_weeks_year` | Use instead when the founder gives weeks worked | |
| `day_hours` | Length of the founder's working day, when they give figures in days | 8, said when used |
| `working_days_week` | Days a week the founder works ("6", "Mon-Sat"), to turn days off into weeks and to count "daily" steps | 5, said when used |
| `helper_planning_line`, `helper_low_line` | The founder's own lines, if they set them | 80% and 50%, planning assumptions |
| `handover_count` | Steps in the handover round | 3 |
| `helpers` | List: `name`, `kind` (contractor, VA, employee), `hours_week` (paid hours a week) | none |
| `offers` | List: `name`, `billing` (monthly or one-off), `active_clients`, `months_per_client` (how long a client stays, or a project runs: "about a month", "half a year", "8 weeks"), `price` (optional, as the founder said it, before any sales tax: a month for monthly offers, a project for one-off; "RM 18k-35k" reads as the middle) | at least one |
| `steps` | List, below | at least one |
| `confirmed` | `["hours_gap"]` or `["price"]` once the founder confirms a figure the plausibility check questioned | |
| `sources` | Where a figure came from, by field name ("country": "KL, from your first message") | "founder said"; country "from what you mentioned"; English "read from how you write" |

Per step: `offer` (an offer's exact name, `all` for a step every offer has per client, or `business` for work that does not grow with clients: team standups, reviewing the team's work across all projects, one dashboard for every site); `step`; `hours` (each time); `how_often` (per client); `owner` (`me`, a helper's name, or a tool); `flag` (F, W or T); `reason` (one line); `gate` (`yes` on every check of the work before the client sees it, `no` on a step that only sounds like one, such as "design review with client"; unset, the script counts unambiguous checks ("QA", "final check", "sign-off", "proofread", "review ... before delivery") as F whatever the flag, and on a step flagged W or T whose name only says "review" or "approve" it prints a NOTE asking you to settle it); `check_hours_after` (the founder's checking time each time, once the step moves); `handover_to` (who or what takes it); `handover` (yes on steps the founder picks for this round, overriding the ranking).

## 2. Drafting the steps from a description

The founder describes a typical client month in their own words. Turn it into steps:

1. One step per distinct activity with its own hours and frequency. "Two calls a month with an hour of prep each" is two steps: the calls (F) and the prep (W or F).
2. Walk the line from contract signed to close, and draft the steps founders forget, marked as your guess for them to confirm: onboarding and setup, prep before calls, follow-up emails after calls, client messages (WhatsApp, Slack, email), chasing the client for inputs, revisions and rework, internal checks, reviewing the team's work, team standups and chasing the team, reporting, invoicing, offboarding. Do not invent hours for them; ask in the same readback ("about how long is the follow-up after each call?"). Team standups and reviewing the team's work across all projects are `business` steps.
3. Split mixed steps (`references/flag-rules.md` section 3).
4. Leave out selling (discovery calls, proposals) and general admin; they come off the available hours.
5. Read the draft back as one short list and ask "What's wrong or missing?"

## 3. Reading messy figures

- **Hours:** "7.5hr", "7,5 Std.", "90 mins", "1h30", "1:30", "half a day", "2 days" (at the founder's `day_hours`, 8 until they say), "1-2 hrs" (the middle), "4 hrs, sometimes 5" (the middle), "6 x 1.5". Pass as written; every figure is read by `scripts/locale_numbers.py` in the founder's decimal style.
- **A task export:** `python3 scripts/capacity.py import-csv <file>` groups the rows by offer and task name, writes each step's hours as an `=` sum of the rows' own figures, and lists blanks and shared assignees. Read its list back; map the founder's own name to `me`.
- **How often, per client:** "weekly", "every other week", "twice a month", "3x a week", "quarterly", "every 6 weeks", "once at the start", "daily", "every day" and "per day" (the founder's working days a week), "every weekday" (Monday to Friday), "6 days a week", "Mon-Sat". "As needed" or "ad hoc" stops for a rough figure: ask "about how many times a month?"
- **Once-per-client steps** are spread over the months a client stays (monthly offers) or the months a project runs (one-off offers). Ask once when it matters; otherwise the defaults are 12 and 1, said out loud.
- **Clients:** "11", "about a dozen", "10 to 12" (the middle, rounded down).
- **Hours a week:** "35", "30ish", "4 days a week" (at the founder's day length).
- **Time off:** "3 weeks PTO plus public holidays, so about 4 weeks" is `weeks_off_year: "4 weeks"`; "25 days of leave" is `"25 days"` (the script turns days into weeks at the founder's working week). Never add a country's public holidays yourself; use what the founder says.
- **A founder who gives a month's hours as a week's** (150 "a week"): the script stops above 100; ask again, and if it was a month, pass it as `delivery_hours_month`.
- **Two figures that disagree** ("about 6 hours, well maybe 9 with emails"): use the larger and say so; under-reporting is the commoner error.

## 4. Offers that are not simple

- **Tiers or packages:** each tier is its own offer.
- **Projects of different sizes:** one offer per size, or the typical size with the range said.
- **Group programmes:** steps that serve the whole group (the group call) are per client = hours / members; pass `"=1.5/12"` as the hours or set the step on the group with its own frequency, and say so.
- **Business-wide work:** a step that serves the whole business, not each client (team standups, reviewing all the team's code, one security dashboard for every site, a weekly team meeting) gets `"offer": "business"` with its hours and how often a month. It sits in the load once and comes off the available hours before every ceiling, so it does not grow with clients. Never divide it by today's client count.
- **Pipelines of one-off projects:** active clients = projects running at once.
- **Retainers billed quarterly:** still per month.

## 5. People: helpers, contractors, tools

- A helper's `hours_week` is the hours they are paid for, not the hours they work for this business if those differ; ask once if unclear.
- A helper paid by the task ("she does the scheduling, about 3 hours a week"): add them with the hours they work for the business.
- Steps owned by a helper are T unless the founder says otherwise.
- `handover_to` can be a helper's name, a tool ("Xero", "booking link"), or "a contractor". With one helper and no name given, moved steps are assumed to go to that helper, and the reading says so.
- Employment status, pay, payroll taxes and on-costs: the skill never computes them or says what a law requires, but it answers the question by `references/side-questions.md` (what it depends on, what goes into it in plain words, the fastest route to the real figure), then carries on.

## 6. The questions, and how to ask them

Value comes first: the first reply gives provisional figures from what the founder said (SKILL.md, First reply), then asks at most four questions; five in the whole run before the files. Count every separate thing asked, including each part joined by "and". Ask only what the pasted material and memory do not answer, in plain words, each with what it would change, a stated default and a skip. The ranked list is in SKILL.md (First reply): delivery hours (and the week they want, when they work long weeks), prices, helpers' hours on this work, hours missing from the list, checking moved work, country.

The steps and the draft flags are not questions: they are shown in the first reply, grouped F, W, T (`references/flag-rules.md` section 5), with "change any that are wrong". A founder who corrects nothing has accepted them.

The answers that can flip the verdict, so each must be asked or defaulted out loud: delivery hours net of selling and admin, weeks worked (the founder's time off, which differs widely between founders and countries), step hours (and the hours check), active clients, the flags, and whether the founder checks moved work. "Defaulted out loud" counts: a default stated in the reading's "What this rests on" is honest; a sixth question is not needed.
