# Intake guide: from what the founder says to the inputs file

Contents
1. The inputs file
2. Reading messy material
3. The inputs that can flip the plan
4. Counts, estimates and hopes
5. Return runs

## 1. The inputs file

Write one JSON file in your scratch folder and pass it to `scripts/target_plan.py`. Write values exactly as the founder wrote them. The script reads them in the founder's own number style through `scripts/locale_numbers.py`: "12k", "£3,600", "$5k", "S$4,500", "₹1,50,000", "₹6 lakh", "15.000 €", "4.850,00 € HT", "4 850,00 €", "15 000 €", "1'250.50", "68,3%", "1,5h", "90 mins", "1h30", "7,5 Std.", "450万", "about 8", "10 to 12" (the midpoint, noted), "a day a week" (7.5 hours, noted), "half", "6 of 10", "8 sur 10", and sums of parts ("=4450 - 1200"). It detects once whether the founder writes a decimal point or a decimal comma; where a figure such as "15.000" could still be read two ways, or one value holds two figures ("45 min plus prep so call it an hour"), it stops with the one question to ask. Never do the arithmetic yourself and never rewrite a figure into another style. `python3 scripts/target_plan.py template` prints a blank file.

| Field | Meaning | If missing |
|---|---|---|
| `business` | Name for the plan | "Your business" |
| `currency` | The founder's currency code: USD, GBP, EUR, SGD, AUD, INR and so on | read from a symbol in their figures; otherwise plain figures, said out loud. Never assumed |
| `date_style` | "day first" or "month first", from how the founder writes dates | day first, month in words, said out loud |
| `spelling` | "American" or "British", from the founder's own writing | British |
| `date` | Run date, YYYY-MM-DD | today |
| `owner`, `books_calls` | Names for the first week | "You" |
| `target_profit_month` | Profit the business must make a month once every cost is paid | ask question 1 |
| `target_basis` | "before tax" or "take-home" | read as before tax, flagged |
| `founder_pay_month` | The founder's pay, only where it sits on top of the profit figure and is not in running costs | none |
| `target_revenue_month` | A revenue target, only where no profit is given or the founder asked in revenue | not used |
| `sales_month_now` | Roughly what the business sells a month today | no "today" line |
| `target_profit_year` | A yearly profit figure, only with `target_kind` | the script stops and asks run rate or by date |
| `target_kind` | "run rate" (the yearly rate to be running at; divided by 12) or "by date" (profit to make between today and `target_date`) | none; never assumed |
| `target_profit_by_date` | Profit to make between today and `target_date` | not used |
| `target_date` | The date the target is due by, YYYY-MM-DD; the plan counts the whole months left | none (monthly fee: reach it in 6 months, said out loud) |
| `margin` | Profit as a share of sales, if the founder knows it and has no costs | not used |
| `billing` | "one-off" (one price per sale) or "monthly" (a fee each month while the client stays: retainer, subscription, membership) | one-off |
| `price` | What one client pays for the main offer; for a monthly fee, the fee a month | ask question 2; the plan cannot run without it |
| `delivery_cost` | What one sale costs to deliver (a month, for a monthly fee): freelancers, materials, tools for that client; not the founder's own time | revenue route, flagged |
| `months_retained` | Monthly fee only: how many months a client pays for, on average | none leave, raised as a [NEED] |
| `active_clients_now` | Monthly fee only: clients paying today | none, raised as a [NEED] |
| `running_costs_month` | Costs that stay with no clients: software, insurance, accountant, premises; not the founder's pay | nil, flagged |
| `price_includes_sales_tax` | yes only where the founder's price includes sales tax | read from "incl GST", "inc VAT" in the price; a yes raises a [NEED], never a sum |
| `show_rate`, `close_rate`, `booking_rate` | The founder's estimates ("6 of 10", "65%") | planning default (booking: not known) |
| `channel_type` | inbound or outbound; picks the defaults | inbound |
| `actuals` | Counts by month: `month`, `leads`, `booked`, `showed`, `offers`, `closed` | estimates or defaults |
| `leads_month_now` | Leads a month today, if not in actuals | volume not checked |
| `selling_hours_week` | Hours a week the founder can give to sales calls | 8, said out loud |
| `call_hours` | Hours one held call takes with preparation and follow-up | 1.5, said out loud |
| `working_days_month` | Selling days a month | 20, less no-call days |
| `call_days` | Days the founder takes calls ("Monday to Friday", "Sunday to Thursday") | Monday to Friday, said out loud |
| `no_call_days` | Days inside that week they take no calls ("Fridays") | none |
| `days_off` | Dated days off: public holidays, leave, YYYY-MM-DD | none |
| `made_so_far` | Profit already made towards a dated target | none |
| `month_to_date` | Counts for the month in progress: `to` (YYYY-MM-DD), `leads`, `booked`, `showed`, `closed`; shown against the pace, never folded into the rates | not shown |
| `pace_whole` | yes to show the weekly pace in whole calls | one decimal |
| `active_clients_max` | Monthly fee only: the most clients the team can serve at once | not limited |
| `weeks_ahead` | How many weeks the Week by week table shows, 1 to 26 | 6 |
| `new_clients_month_max` | Most new clients a month they can deliver for | not limited, said out loud |
| `cash_share` | Percentage of the price paid in the month they sign, 0 to 100 | 100, said out loud |
| `channels` | By source over 90 days: `name`, `leads`, `booked`, optional `showed` | not split |
| `country` | Two-letter country code (US, FR, IN, SG); sets date order and paper size | day first, month in words, said out loud; paper left to the printer |
| `number_style` | "1,250.00" or "1.250,00", only where the founder said which, or answered the script's question | detected from their figures |
| `confirmed` | Fields the founder confirmed after a plausibility stop, for example `["call_hours"]` | none |
| `sources` | Where each figure came from, by field name | "founder said" |

## 2. Reading messy material

Draft from whatever is pasted, then ask only what is missing.

- **A ramble or voice note:** pull every figure into a list, read it back in one short block ("I read: main package £3,600, a freelancer at about £1,200 a client, about 8 hours a week for calls..."), and ask "What's wrong or missing?" in the same message as any questions.
- **Their locale:** set `currency` and `spelling` from what they wrote, and `country` from what they said ("translation agency in Paris" is FR; "I'm in Austin" is US). Date order and paper size come from the country, never from spelling: a British-spelling founder in the US still writes the month first. Set `date_style` only where they wrote a date that settles it. If nothing shows the country, ask once in the read-back. Never infer a country from a name.
- **Their number style:** pass figures as written. "15.000 €" with "4.850,00" elsewhere reads as fifteen thousand; "15.000 €" alone stops with a question, and you set `number_style` from the founder's answer. Plan figures are written back the founder's way (15.000 €, 68,3%).
- **A yearly figure or a date** ("250k this year", "100k by June"): ask whether it is the yearly rate they want to be running at or money to make by then, and which date. Write `target_profit_year` with `target_kind`, or `target_profit_by_date` with `target_date`. The plan says how many whole months are left; ten weeks is not a year.
- **A monthly fee** ("$3,500/mo retainer", "membership at 300 a month", "clients stay about 7 months"): set `billing` to "monthly", `price` to the fee a month, `delivery_cost` to what one client costs a month, and ask how many clients pay now and how long one stays. Never multiply the fee by the months into one price: retainers stack, and the plan counts the clients already paying and the clients who leave.
- **A CRM or spreadsheet export:** `count_export.py` reads the date order from the export; if every date could be either way it stops, and you ask the founder whether they write the day or the month first. Count by month: enquiries (leads), calls booked, calls held, offers made if recorded, sales. Put the counts in `actuals`, one row per month, last three months only. A call marked rescheduled counts once, when it happens. Count sources into `channels` if a source column exists.
- **A calendar screenshot:** count held sales calls a week; say which you could not read.
- **Two figures for one thing** (two prices, two hours figures): ask which the plan should use, in the question block. If the founder has several offers, plan on the one most sales come from, and say so; offer to run another afterwards.
- **"Revenue" that is really profit, or the reverse:** read it back in plain words ("so 12k is what you want left after every cost?").
- **Today against the plan:** where the founder says what they sell now, pass it as `sales_month_now`. The plan prints what that leaves at the costs given. If the founder says nothing is left but that line shows a healthy figure, a cost is missing (their pay, a second freelancer, something their accountant sets aside): ask which, inside your question limit. Never estimate it.
- **Hours as days:** a day is read as 7.5 hours and the plan says so; use the founder's own day length if they give it.
- **Sales tax in a price:** "7,200 incl GST", "4.850 € TTC", "inkl. MwSt", "IVA incluido" are planned as given with a [NEED] for the price before sales tax. "HT", "excl. VAT", "zzgl. MwSt", "+ IVA" are read as before sales tax and noted. Never take tax off yourself.

## 3. The inputs that can flip the plan

Each of these must be asked or defaulted out loud. Never leave one silent.

| Input | Why it flips the plan |
|---|---|
| Profit before tax or take-home | Take-home understates every figure |
| Founder's pay inside or on top of the profit | On top adds it to what each month must make |
| Delivery cost and running costs | Without them the plan cannot start from profit |
| Whether the price includes sales tax | A tax-inclusive price overstates what each sale leaves; the founder gives the figure before tax |
| One price or a monthly fee | A monthly fee recurs: clients already paying count, and clients who leave must be replaced |
| A yearly figure: run rate or by a date | Ten weeks before a year end, "250k this year" needs a different plan from 250k a year |
| How the founder writes numbers | 4.850,00 read as 4.85 shrinks every figure a thousand times |
| The days they take calls | Sets the first week's dates and the selling days a month |
| Hours per call held | 1.5 against 2 moves the calendar ceiling by a quarter |
| Hours a week for sales calls | Sets the ceiling |
| Show and close rates | Every call figure rests on them |
| Delivery limit | Can bind before the calendar |

## 4. Counts, estimates and hopes

- Counts beat estimates. If the founder has counts, use `actuals` and leave the estimates empty.
- "Of 10 booked, about 6 turn up" is an estimate: `"show_rate": "6 of 10"`.
- "15 of the 22 I booked last quarter showed" is a count: `"show_rate": "15 of 22"`, or better, `actuals`.
- A hope is not a rate. "I want to close half" is a target; use what has happened, or the default, and say so in one line.
- "No idea" is fine: the planning default is used, tagged, and the re-plan is set for 30 days.

## 5. Return runs

`scripts/memory.py read` gives `previous.json`: the saved profile, the actuals, the last plan's figures and the active learnings. Copy it to the new inputs file, set `date` to today, add last month's counts as a new row in `actuals`, and change only what the founder says changed. Counts replace estimates automatically: the script prefers `actuals` over `show_rate` and `close_rate`. Pass `--previous previous.json` to `build` so the plan opens with last month's results against the last plan.

Apply each active learning at its step: "calls take 2 hours with prep" sets `call_hours` to 2; "no calls on Fridays" sets `no_call_days`; "referral bookings show at 90 per cent" means the channel rows carry `showed` counts.

A memory file from version 1.0 may carry "VAT registered" and "Price includes VAT" rows. `memory.py read` ignores them and says so; the plan runs on the saved price as before any sales tax.
