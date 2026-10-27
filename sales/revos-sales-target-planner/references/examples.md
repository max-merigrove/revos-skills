# Worked examples

Three complete runs on clearly illustrative businesses in three countries. Every figure was printed by `scripts/target_plan.py`; none was worked out by hand. Use them to see the shape of a finished run, not as benchmarks.

Contents
1. Harbour Lane Consulting, UK (illustrative): the calendar binds and the price leads
2. Brightwater Digital, Singapore (illustrative): a price including sales tax, revenue-first, lead volume binds
3. Kestrel Learning, India (illustrative): a six-day week, days off, delivery binds
4. Northlight Marketing, US (illustrative): a monthly retainer, a year nearly over
5. Lexis Traduction, France (illustrative): European numbers, a French CRM export
6. What plain Claude gives

## 1. Harbour Lane Consulting, UK (illustrative): the calendar binds and the price leads

**What the founder said.** "I keep having 15 to 18k months and there's never enough left. I want the business to clear 12k a month profit before tax, I pay myself out of the profit. Main package is a 6 week ops review at £3,600, the analyst costs me about £1,200 per client. Running costs roughly 2.4k a month. Of 10 calls booked maybe 6 or 7 turn up and I close about 1 in 4. I can give sales calls about 8 hours a week. Clients pay half up front." Every intake question was answered; currency read from the £.

**Diagnosis.** First plan from profit: target and costs known, no saved plan.

**Inputs (as written; the script reads the wording).**

```json
{"business": "Harbour Lane Consulting", "target_profit_month": "12k", "target_basis": "before tax",
 "sales_month_now": "15 to 18k", "price": "£3,600", "delivery_cost": "about £1,200",
 "running_costs_month": "roughly 2.4k", "show_rate": "6 to 7", "close_rate": "about 1 in 4",
 "selling_hours_week": "8", "cash_share": "half"}
```

**First plan (1.5-hour calls, the default said out loud).** The business must leave £14,400 a month; each sale leaves £2,400, so 6 sales, 24 held calls and 37 bookings. At 1.5 hours a call that is 8.3 hours a week against 8: the calendar breaks. Headline: "At £4,100 the same target needs 5 sales, 20 held calls and 6.9 hours a week, which fits, tightly."

**The correction.** "My calls are nearer 2 hours with the write-up." Re-run:

> At today's price of £3,600, your calendar cannot carry £12,000 of profit a month: it needs 6 sales, 24 held calls and 37 bookings a month, 11.1 hours a week of calls against your 8.
> At £4,800 the same target needs 4 sales, 16 held calls and 7.4 hours a week, which fits, tightly. The price is the first thing to move.

| Scenario | Sales | Held | Booked | Hours a week | Fits |
|---|---|---|---|---|---|
| Today's rates | 6 | 24 | 37 | 11.1 | breaks |
| Show rate to 70% (planning default) | 6 | 24 | 35 | 11.1 | breaks |
| Price up 10% (to £3,960) | 6 | 24 | 37 | 11.1 | breaks |
| Close rate on held calls to 30% (planning default) | 6 | 20 | 31 | 9.2 | breaks |
| All three together | 6 | 20 | 29 | 9.2 | breaks |
| The price your calendar needs (£4,800) | 4 | 16 | 25 | 7.4 | fits, tightly |

Hire: triggered only if the price stays at £3,600. Weekly pace, set at the calendar: 6.1 bookings, 4 held calls, 1 sale. First week: Wednesday, decide the price for new clients (£4,800) and hold bookings to 6.1 a week; Thursday, start a tally by source; Tuesday, check the week. Re-plan by 19 November (both rates are estimates).

**What was learned.** "Calls take 2 hours with preparation and write-up", step Make, active.

## 2. Brightwater Digital, Singapore (illustrative): a price including sales tax, revenue-first, lead volume binds

**What the founder said.** "how many calls do i need for 40k a month? ... standard website build is S$7,200 incl GST. leads last 90 days: referrals 14 leads 9 booked 8 showed, linkedin 31 leads 6 booked 4 showed, google ads 6 leads 2 booked 1 showed. we close about 3 in 10 calls. between us we can do 10 hours of calls a week."

**What the skill did with the tax.** Nothing it could compute. It asked for the price before GST; the founder gave S$6,600 from their own invoice. Had they skipped, the plan would have run on S$7,200 as given with a [NEED] saying so. The plan carries the one neutral line, once: "Enter prices before any sales tax (VAT, GST or similar); ask your accountant whether you need to charge it."

**The plan.**

> To make S$40,000 of sales a month you need 7 sales, 24 held calls and 32 bookings a month, from 96 leads: 7.4 bookings a week.
> What breaks first is your lead volume: the plan needs 96 leads a month, 5.6 times the 17 you get now. Change a rate or the target before spending on leads.

Show 76.5% (measured, 13 of 17) and close 30% (your estimate) already meet the lever lines, so those rows are listed as met. Referrals book 64.3% of their leads (measured) and are loaded first; Google Ads (6 leads in 90 days) is a capped experiment. [NEED] for the profit: revenue can be hit with nothing left over.

## 3. Kestrel Learning, India (illustrative): a six-day week, days off, delivery binds

**What the founder said.** "₹6 lakh profit a month before tax, and my salary of ₹2,00,000 is on top of that. A two-day workshop sells at ₹3,50,000; trainer fees and venue come to about ₹1,20,000 ... Fixed costs are ₹1,50,000 a month ... I take calls Monday to Saturday, about 10 hours a week, 1 hour each ... at most 4 workshops a month ... I'm off on 21 and 22 October."

**What the scripts did.** Read "₹6 lakh" as 6,00,000 and printed every figure in Indian grouping; scaled the selling days to 24 for six call days; built the first week on her call days, skipping 21 and 22 October (Friday 23, Saturday 24, Wednesday 28 October).

> At today's price of ₹3,50,000, ₹6,00,000 of profit a month needs 5 new clients a month, and you can deliver for 4.
> At ₹3,57,500 the same target needs 4 sales, 14 held calls and 3.2 hours a week, which fits. The price is the first thing to move.

Calls take 3.9 of her 10 hours: delivery, not the calendar, binds, so the hiring line reads "Not a sales hire: delivery is the limit". The weekly pace is held to the delivery limit: 3.8 bookings, 3 held calls, 0.9 sales.

## 4. Northlight Marketing, US (illustrative): a monthly retainer, a year nearly over

**What the founder said.** "fractional marketing team, $3,500/mo retainers, clients stick around ~7 months on avg. want to make 250k this year ... contractors ~$1,400 a client a month, tools+software ~1.8k/mo ... maybe 8 of 10 show, close 1 in 3ish ... 6-8 hrs a week tues to thurs ... can't take more than 4 new clients a month ... i already have 5 clients."

**What the skill asked.** Run rate or by the year end ("Is 250k the yearly rate you want to be running at, or profit to make between now and December 31?"), and how long one call takes: "45 min plus prep so call it an hour" holds two figures, so the script stopped and asked rather than picking 0.75.

**Inputs.** `billing: monthly`, `price: "$3,500/mo"`, `delivery_cost: "~$1,400 a client a month"`, `months_retained: "~7 months"`, `active_clients_now: "5"`, `target_profit_year: "250k"`, `country: "US"`.

**As a run rate by December 31 (2 whole months of selling).**

> You need 11 paying clients at once and have 5. To make $20,833 of profit a month by December 31, 2026 you need 4 new clients, 12 held calls and 15 bookings a month: 3.5 bookings a week.
> At this pace the target is first reached in December 2026.

Holding 11 clients takes 2 new clients a month once there (11 over 7 months, rounded up). Clients staying 2 months longer is a scenario row.

**As profit to make by December 31.**

> At today's fee of $3,500, $250,000 of profit between today and December 31, 2026 needs 40 new clients a month, and you can deliver for 4.
> At the most you can carry (4 new clients a month), profit from today to December 31, 2026 is about $37,114.

Folding the retainer into one price ($24,500) had said "2 sales a month, nothing breaks"; reading the fee as one-off had said 11 new clients a month. Neither counted the 5 clients already paying.

## 5. Lexis Traduction, France (illustrative): European numbers, a French CRM export

**What the founder said.** "Objective is 15.000 € profit per month before taxes ... Average contract is 4.850,00 € HT, freelance translators cost me around 2.100,00 € per contract, fixed costs 3.200 € / month ... around 10h per week ... 1h per call", with a Pipedrive export saved by Excel in Windows-1252, semicolons, French headings and statuses (Nouveau, RDV pris, RDV effectué, Proposition envoyée, Gagné, Perdu).

**What the scripts did.** `count_export.py` read the file as Windows-1252, found "Date de création" and "Statut", and mapped every French status; the one question was whether "Perdu" means lost after a call. `target_plan.py` detected the decimal comma from "4.850,00" and read "15.000 €" as fifteen thousand, "HT" as before sales tax, and later "1,5h" as an hour and a half.

> To make 15.000 € of profit a month you need 7 sales, 17 held calls and 25 bookings a month, from 38 leads: 5,8 bookings a week.
> Nothing breaks at these rates: the calls take 5,9 of your 10 selling hours a week, which fits.

Every figure is written back her way (15.000 €, 68,3%). Before the fix, the same words produced "€15 of profit a month" and, after her correction, a 15-hour call.

## 6. What plain Claude gives

For a US studio owner with no tracked rates and 6 hours a week, plain Claude worked the film count correctly (8), then used "typical cold outreach benchmarks" of 25% close and 80% show as facts, assumed 30 to 45 minute calls, called the plan possible in 6 hours and closed with "you're definitely in range ... if you stay consistent". The skill's run needed 27.7 hours a week on labelled defaults and triggered a hire with a start-by date. The full comparison is in `assets/before-after.md`.
