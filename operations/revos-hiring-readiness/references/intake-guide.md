# Intake guide: turning what the founder gives you into the inputs file

Contents
1. The inputs file
2. The inputs that can flip the verdict
3. Reading messy material
4. The questions: at most five, after the first answer
5. Return runs

## 1. The inputs file

One JSON file for `scripts/conditions.py`. Print a blank one with `python3 scripts/cash_scenario.py template`. Values may be messy strings in the founder's own number style; the script reads them with `scripts/locale_numbers.py`: "$24.5k", "S$5.2k", "1.234,56 €", "₹18 lakh", "18,00,000", "450万", "about 12", "10 to 12" (the midpoint, noted), "2.5k pcm", "38hrs", "7,5 Std.", "mon wed fri" (days of the working day's hours), "8 + 5 + 9" (worked out, noted) and dates such as "in 4 weeks", "next month", "1st Dec", "Dec 1", "7 Jan", "01/12/2026" (in the date order of the founder's country), "2026/12/01", "asap". Never add, divide or convert a figure yourself: pass the parts and let the script work them out. A figure that reads two ways ("12.500" with no other decimals to go on) or fails a plausibility check comes back as an `ASK:` line; put it to the founder, then fix it or list the field in `confirmed_figures`.

| Field | Meaning | If missing |
|---|---|---|
| `business`, `date` | Name, run date (YYYY-MM-DD) | "Your business", today |
| `currency` | The founder's currency code (USD, GBP, SGD, AUD, EUR...), from what they wrote | figures shown without a symbol, said out loud |
| `currency_symbol` | Only if the founder writes a mark the script would not use ("S$" at home in Singapore); a founder at home who writes a bare "$" gets "$" | the founder's own mark |
| `country` | ISO code of where the founder runs the business (US, AU, DE...), from what they say, never from spelling. Sets date order and paper size | the region in `locale`; else day first and A4, said out loud |
| `locale` | The founder's English, such as `en-US`, `en-GB`, `en-AU`, `de-DE` | as written |
| `decimal_style` | `dot` or `comma`, only when the `NUMBERS:` line has it wrong | worked out once from the founder's figures |
| `confirmed_figures` | Field names the founder confirmed after an `ASK:` plausibility question (`"role.monthly_cost"`, `"cash_today"`) | none |
| `cash_today` | Business bank balance today (negative for an overdraft) | `[NEED]`; no cash test |
| `monthly_revenue` | Average monthly revenue, last three months | `[NEED]` |
| `monthly_costs` | Average monthly costs, last three months: everything that leaves the account | `[NEED]` |
| `costs_include_founder_pay`, `founder_pay_month` | Whether the founder's own pay is in the costs; if not, what they take a month | assumed included, said out loud |
| `known_payments` | List of `{what, amount, when}`: big bills the founder already knows about (a tax payment, an insurance renewal, annual software), with the founder's amount and date | none |
| `known_low_periods` | Up to three `{what, from, to, revenue_cut, costs_cut}`: a closure ("23 Dec" to "5 Jan", "closed") or a quiet season ("1 Jun" to "Aug", "15%"), with the founder's own figure for the drop; `costs_cut` only if the founder says costs fall too. Loaded in both cases; the window runs on to the end of any that starts within a year | none; a `SEASON:` line flags low months in the history |
| `revenue_history` | Monthly revenue, oldest first: 12 months, or 18 to 24 to compare the same months a year apart. Pass month labels (`{"2025-10": "61,200", ...}`) so seasons can be named | condition 4 Unknown |
| `gross_margin_months`, or `margin_detail` | Last two months' gross margin (or revenue and direct costs for each) | condition 2 Unknown |
| `gross_margin_rough` | The founder's one rough range when they have no monthly figures ("55-60%"). Passes only if the low end clears the floor; Unknown if the floor sits inside it | not used |
| `margin_floor` | The least gross margin the founder accepts | 50%, said out loud |
| `recurring_revenue_month`, `contracted_next_6_months` | Recurring revenue a month; contracted revenue for the next six months (signed, not "mostly"). Only contracted revenue escapes the bad-quarter cut | condition 3 Unknown |
| `repeat_revenue_month` or `repeat_share` | For an appointment, class or retail business: revenue a month from regulars, memberships, care plans and packs, or the share of revenue from returning clients (founder supplied), not already counted as recurring | condition 3 Unknown |
| `variable_costs_share` | Costs that move with revenue (contractor fees, materials, commissions): the share of each unit of revenue lost that the founder says they would save in costs ("contractor fees run at about 45% of revenue" gives "45%"; "fees drop about 40% of whatever income drops" gives "40%"). Used only in the bad quarter, from week 1, in the script and the workbook alike. If the founder's words read two ways, ask which | costs held flat in the bad quarter, said in the report |
| `provisional` | `true` for the first reply's run, before the questions are answered: a missing task list cannot make the verdict No yet | false |
| `stress_cut_all_revenue` | "yes" if the founder wants the bad-quarter cut on contracted revenue too | no |
| `pipeline` or `pipeline_weighted` | Deals with value and chance, or one weighted figure | none counted, said in the report |
| `role` | `title`, `type` (admin, delivery, setter, closer, other), `employment` (employee, contractor, undecided), `hours_week`, `days` (the days the founder named: "3 days, mon wed fri"), `monthly_cost`, `cost_basis` (`loaded` or `salary_only`), `cost_from` (who supplied it: "your accountant", "your payroll provider"), `salary_year` (only when no monthly cost is known), `one_off_costs`, `start` | hours and cost are `[NEED]`; start four weeks out |
| `payroll_provider_seen` | The payroll provider the founder's own bank export shows (a `REGULAR OUT` payee), so the report can name it for the loaded figure | not named |
| `tasks` | List of `{task, hours_week, written_down}` in the founder's words ("sort of", "in my head", "Google Doc SOP"); read as yes, partly, no or unknown | condition 5 fails; an unknown biggest task is Unknown with a question |
| `freed_hours_use`, `freed_use_has_revenue_path` | What the founder does with the hours back, and whether it leads to revenue | condition 5 fails |
| `role_coherent` | `{value, reason}`: your judgement on whether the tasks form one job | condition 5 Unknown |
| `capacity` | `{now, max, unit}`: client hours (or clients) now and the most the founder can take. A founder who answers in headroom ("pretty full, could take maybe 2 more clients") gives `room_for` (2) and `said` (their words); with `now` as well, the most is worked out as now plus room. Never invent `now` | condition 6 Unknown, quoting their words and asking how many they have now |
| `price_rise_tested` | The founder's own words ("raised prices in May for new clients", "fees up $5 in July"), or `{value, said}` | condition 6 fails |
| `contractor_rate_hour` | A contractor's hourly rate, from a quote | contractor alternative not run |
| `typical_client_month` | What a typical new client pays a month (fees only, not money passed through), when the founder says it | the `PAYS ITS WAY` line gives revenue only, not a number of clients |
| `cover_target_months`, `stress_revenue_cut`, `stress_extra_days`, `contractor_line_hours`, `day_hours` | Overrides, from the founder or an active learning | the defaults in `method.md`; a working day of 8 hours |
| `sources` | Where each figure came from, by field name ("bank export Jul to Sep", "founder said", "your payroll provider") | "founder said" |

## 2. The inputs that can flip the verdict

Ask for each, or say its default out loud before computing:

1. **The hire's fully loaded monthly cost.** Pay plus whatever the founder's accountant or payroll provider says goes on top of it where they hire. Pay alone understates the hire. Never work out or estimate what goes on top.
2. **Whether the monthly costs include the founder's own pay.** Leaving it out overstates the cash every week.
3. **Big bills in the next three months** (a tax payment, an insurance renewal, annual software), each with the founder's amount and date. One such bill can be the week the floor breaks.
4. **The start date.** A later start can turn Fail into Pass.
5. **The cash floor.** One month is the default; a founder who wants three months changes condition 1.
6. **Employee or contractor, and the role's hours.** Under 15 hours a week as an employee is a No (a commercial rule about a commitment you cannot easily stop, not a ruling on status).

## 3. Reading messy material

Draft from whatever is pasted, read it back in one short block, then ask only what is missing.

- **The founder's locale:** take the currency from symbols or codes ("$", "S$", "A$", "£", "EUR"), the date style from how they write dates and from the bank export, and the English from their spelling. A bare "$" is ambiguous (US, Australian, Singapore, Canadian dollars): use the country they mention or state your reading in the readback. Set `currency` and `locale`.
- **A bank export (CSV):** run `python3 scripts/bank_summary.py <file>`. It finds columns by name (a "Details: CREDIT/DEBIT" column is never taken for the description), reads commas, semicolons or tabs, the export's own number style and its date order; when every date could be read both ways it stops and asks, and you rerun with `--day-first` or `--month-first`. It prints money in and out by month (every month inside the export's range counts as full, however quiet), the three-month averages, money in by month with labels (pass them as `revenue_history`), and the latest balance from the chronologically last row with the row it came from. Then what you ask about, once, in the readback:
  - `TRANSFERS?` groups: savings, owner loans, money between accounts. Card processor payouts (Stripe, Square, PayPal) are usually sales. Leave out what is not trading with `--exclude "SAV,loan"` (it matches any text in the row); a `WARN: nothing matched` line means the term missed.
  - `AFTER IT, NO BALANCE`: pending rows after the last balance, with the balance they would leave. Ask which is today's.
  - `BIG ONE-OFF OUT` inside the averaged months: **a bill that is also entered as a known bill is left out of the average** (`--exclude`), so a quarterly tax payment is never carried one and a half times.
  - `REGULAR OUT`: the payees that recur. A payroll provider here can be named to the founder for the loaded figure.
  - Money passed through: ad spend, materials or fees the founder pays on a client's behalf and bills back. It sits in both money in and money out, so the cash test is unchanged, but it is not the business's own revenue or margin. Ask once whether a large recurring cost of this kind is passed through; never assume either way.
  - If money in includes sales tax the founder collects and pays on (VAT, GST or similar), ask for their accountant's figure for the next payment and enter that as a known bill; never work it out.
- **A P&L or management accounts:** revenue and gross margin for the last two months (gross profit over revenue), costs. Add back nothing; ask whether the founder's own pay is in it. A P&L with months as columns (Xero, QuickBooks) is read by hand: pass the parts as sums (`"=(47,900 + 51,600 + 63,100) / 3"`) and the monthly revenue with month labels; the bank reader stops on it with a pointer here.
- **A season or a closure** ("cash is always tight over winter", "we close 23 Dec to 5 Jan"): ask for the dates and roughly how much less comes in, inside question 1, and enter it in `known_low_periods`. Never invent the drop.
- **Contradictions** ("20 hours" and "3 days, Mon Wed Fri"): pass both (`hours_week` and `role.days`); the script flags the difference and the report says the hours may change the cost.
- **A voice note or a ramble:** pull every figure into a list, read it back, ask "what's wrong or missing?".
- **A calendar export or a list of tasks:** group the tasks the role would take, with hours a week each. Hours as days: 8 hours a day unless the founder says otherwise (`day_hours`).
- **A fully loaded figure ("2,500 a month all in, from my accountant", "my payroll provider says $3,100 a month"):** `monthly_cost` as given, `cost_basis: loaded`, `cost_from` naming who.
- **A salary only ("I'd pay them 26k"):** ask for the fully loaded monthly cost from their accountant or payroll provider. Meanwhile pass `salary_year` and leave `monthly_cost` empty: the script uses the salary divided by 12, marks it pay alone (`salary_only`), and blocks Ready.
- **An hourly rate for an employee ("$22 an hour, 20 hours"):** `monthly_cost` as `"=22 * 20 * 52 / 12"`, `cost_basis: salary_only`, and ask for the fully loaded figure.
- **A VA or freelancer at an hourly rate:** that is `employment: contractor`, `monthly_cost` as `"=rate * hours * 52 / 12"`; set `contractor_rate_hour` too. A contractor's invoice is the full cost, so the basis defaults to loaded. Whether the arrangement is legally a contractor one is never judged.
- **A balance flattered by a one-off:** an invoice paid early, a grant, a refund or a loan sits in today's balance but will not repeat. Ask how much and when it would otherwise have landed, and enter it as a known payment in that week ("Invoice already received early", the amount, the date), so the scenario does not count it twice.
- **Ranges:** pass as written ("6-8hrs").

## 4. The questions: at most five, after the first answer

The first reply gives a provisional answer from what the founder gave (SKILL.md, The first reply). Questions come after it: at most three in that reply, at most two in the next, five in all across at most two founder turns. Ask only what the founder's message, files and memory do not already answer, and only what could change the verdict or move the month-three figures. Each question is one question with one thing to answer; never bundle sub-questions under a number. Use the founder's currency and date style in every option and example.

Pick from this list, most decisive first for this founder:

1. **A figure the scripts could not read** (`ASK:`), or a contradiction in their own material.
2. **The tasks the role takes, with rough hours a week.** "Which of your tasks would they take, and roughly how many hours a week each?" Condition 5 fails without it.
3. **Big bills in the next three months.** "Any big bills due before the end of [month], such as a tax payment or a renewal, and roughly when?" One can be the week the floor breaks.
4. **What's secured.** For a retainer or project business: "How much of your monthly revenue is signed for the next six months?" For an appointment, class or retail business: "Roughly how much of a typical month comes from regulars, memberships or packs?"
5. **The use for the freed hours.** "What would you do with the hours you get back?"
6. **Whether anything is written down.** "Is [biggest task] written down anywhere someone else could follow?"
7. **Capacity.** "How many [clients or client hours] do you have now, and the most you could take?"
8. **A price rise.** "Have you put prices up for new [clients] in the last year?"
9. **Margin.** "Roughly what gross margin did you make last month?" A single rough range goes in `gross_margin_rough`.
10. **A season or closure**, when the history or the founder hints at one: "When is your quiet spell, and roughly how much less comes in?"
11. **Pass-through money**, when a large recurring cost may be billed back.
12. **Costs that move with revenue**, when a large cost line clearly tracks revenue (contractor fees, materials): "When revenue drops, roughly what share of the drop do you save in [that cost]?" Goes in `variable_costs_share`.
13. **A typical new client's monthly fee**, when the freed hours go to selling: it turns `PAYS ITS WAY` into a number of clients.

Not a question: the hire's fully loaded cost when the founder has only the salary. That is an action for them (their payroll provider or accountant gives it); say so with the fastest route and run on pay alone with the ceiling. Not a question either: currency, country and date style (state your reading), the start date and the cash floor (state the defaults in one line).

If a multiple-choice tool is available, use it for the questions with natural options (employee or contractor; start date: in 4 weeks, next month, in 3 months, a date; cash floor: one month of costs, two, three; prices raised: yes in the last six months, yes earlier, no). Otherwise numbered questions the founder can answer in one line each.

Twelve months of revenue (condition 4) is never a question of its own: a bank export gives it, or ask for it inside the money question as "if you have it, monthly revenue for the last year".

## 5. Return runs

Memory holds the country, locale, currency mark and number style, the role and its cost basis, tasks, floors, the bad-quarter settings the founder set (a 0-day delay included), recurring and repeat revenue, known low periods in the founder's own dates, contractor rate, revenue history and the last check. The last margin is kept aside (`SAVED MARGIN`), not put in the inputs: a margin is reused only as the month before the one the founder gives now. One question: "Paste this month's figures: bank balance, what came in and went out, last month's gross margin, and anything that changed (the role, its cost, a start date, a big bill, prices)." If the saved cost was pay alone, add in the same sentence: "and the fully loaded cost, if your accountant or payroll provider has given it." Then rerun with `--previous` so the report shows which conditions moved.
