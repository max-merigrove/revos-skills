# Method: the reverse sales plan

Contents
1. Start at profit, not revenue
2. Cash is kept apart from sales
3. The chain, climbed from whole sales
4. Every rate tagged
5. The calendar before feasibility
6. What breaks first, in a fixed order
7. The price the ceiling needs
8. Fix order
9. Scenarios, and "three bets, not a plan"
10. Channels, never blended
11. The hiring trigger
12. The weekly pace and the first week
13. Prices, sales tax and the before-tax question
14. Planning defaults and where each comes from
15. The founder's currency, dates, spelling and week
16. What this method does not do
17. Monthly fees: retainers stack
18. Targets with a date
19. Reading the founder's numbers

All arithmetic runs in `scripts/target_plan.py`. Never compute a figure in prose: copy it from the script. The workbook carries the same formulas, so the plan and the spreadsheet cannot disagree.

## 1. Start at profit, not revenue

Founders set a revenue target because it is the number everyone uses. They hit it and still cannot pay themselves, because a revenue target says nothing about what each sale costs to deliver or what the business spends before anyone buys. The plan starts from the profit the business must make each month and works back.

Three entry routes, in order of preference. The script picks the first the inputs allow and says which it used.

| Route | Needs | Arithmetic |
|---|---|---|
| Costs (preferred) | profit, price, delivery cost per sale, running costs a month | what the business must leave = profit + the founder's pay where it sits on top + running costs; each sale leaves price less delivery cost; sales = what it must leave / what each sale leaves |
| Margin | profit, margin, price | sales value = profit / margin; sales = sales value / price |
| Revenue (flagged) | revenue target, price | sales = revenue / price, with a [NEED] for the profit, because revenue can be hit with nothing left over |

Where the founder gives both a margin and costs, the plan runs on the costs (they are what one sale actually leaves) and prints the margin route beside it. Where the two are more than a tenth apart, a [NEED] asks which margin the founder meant.

Where delivery cost is known and running costs are not, running costs are counted as nil and a [NEED] says the plan is short by whatever they are.

Where one sale costs as much as or more to deliver than it brings in, no number of sales reaches a profit. The script stops and says so: the price is the first problem, before any sales plan.

**The founder's pay.** Ask whether the founder's own pay is inside the profit figure or on top of it. On top: give it as `founder_pay_month` and leave it out of running costs. Inside: leave `founder_pay_month` empty. Never count it twice.

## 2. Cash is kept apart from sales

Cash collected, not sales booked, pays the bills. The plan keeps the two apart. Sales are worked out from the target at the price; the share of the price paid in the month a client signs (a percentage from 0 to 100) is reported beside them: the cash that lands in the month from that month's sales, and how far cash runs behind sales in the first month of a new plan, until earlier instalments land.

The share never multiplies the sales needed. Once a plan is running, later instalments of earlier sales land too, so at steady state cash equals sales. Multiplying would inflate the plan and push the founder to book calls they do not need.

A share written as a fraction (0.34) is refused with a STOP: ask for the percentage (34). A share above 100 is refused.

## 3. The chain, climbed from whole sales

Sales are whole: the exact figure is rounded up and every later step is worked from the whole number, each rounded up to whole calls.

- Sales a month (rounded up)
- Offers made = sales / share of offers that buy (only where offers are counted, see section 4)
- Calls held = offers / share of held calls that get an offer; or, where offers are not counted, sales / close rate on held calls
- Calls booked = held / show rate
- Leads = booked / booking rate (leads that book a call); "not known" until leads are counted

A booked call is on the calendar with a date. A held call happened with the prospect present (a rescheduled call counts once, when it happens). A sale is a yes recorded as won. A lead is a person who raised a hand: an enquiry, an opt-in, a referral introduction, a reply.

## 4. Every rate tagged

Every rate the chain climbs carries one tag, in the plan, the workbook and any chat line that quotes it.

| Tag | When | Effect |
|---|---|---|
| measured | worked out from the founder's counts on 10 or more events (last three months at most) | planned on; re-plan in 90 days once every rate is measured on three months of counts, otherwise 30 |
| measured on under 10, directional | counts on fewer than 10 events | planned on, with the planning default printed beside it as the pessimistic case |
| your estimate | the founder's "of 10 booked, about 6 turn up" | planned on; re-plan in 30 days |
| planning default | nothing given (section 14) | planned on; re-plan in 30 days |
| not known | the booking rate where leads are not counted | that stage reads "not known"; nothing is estimated |

Offers are a separate step only where the founder counted offers made on 10 or more held calls. Otherwise the offer step is folded into the close rate on held calls and the plan says so.

**No aspirational rates.** Plan on what has happened. If the founder gives a rate they hope for ("I want to close half"), say in one line that the plan uses what has happened, and use their past figure or the planning default. The script notes any estimate above 90 per cent show or 50 per cent close so you can check it is not a hope.

Questions are asked as "out of 10", so a bare 1 to 10 reads as that many out of 10 ("6" is 60 per cent; "1" is 10 per cent). A figure with a % sign is a percentage ("7%" is 7 per cent). "0.6" is a fraction. "15 of 22" is a count with 22 events.

## 5. The calendar before feasibility

Held calls times the hours one call takes (the call plus preparation and follow-up) is set against the hours a week the founder can give to sales calls, before the plan is called possible.

- Under three quarters of the hours: fits.
- From three quarters to all of them: fits, tightly.
- Above them: breaks.

The calendar's ceiling is stated with its number: the most held calls a month the hours carry, and the sales that makes at the founder's rates.

Where the founder gives the most new clients a month they can deliver for, delivery is checked beside the calendar. A plan that needs more new clients than delivery can take breaks there, whatever the calendar says.

## 6. What breaks first, in a fixed order

Checked in this order; the first that breaks is the one binding constraint, stated with the number that shows it.

1. **Capacity:** the calendar or delivery. Where both break, the lower ceiling breaks first.
2. **Show rate:** under 65 per cent of booked calls held, with what 70 per cent would save in bookings.
3. **Lead volume:** leads needed at three times today's or more. Change a rate or the target before spending on leads.
4. **Close rate:** under 20 per cent of held calls buying (only where offers are not counted separately).

A plan without a named binding constraint is a wish with arithmetic. Where none breaks, the plan says so and shows how much of the calendar it uses.

## 7. The price the ceiling needs

Where capacity binds, more activity cannot reach the target: the founder runs out of hours or delivery first. The headline then leads with the price. The script finds the lowest price, rounded up to a figure the founder would quote (to 10 below 500, 50 below 2,000, 100 below 10,000, else 500), at which the whole sales needed fit both the calendar and delivery, and shows the calls and hours at that price. Where no price fits, the headline says the target, the hours or a hire has to move.

The price is a planning figure. Whether the market will pay it is a separate question; the plan names it, it does not decide it.

## 8. Fix order

Ranked for this plan, not from a fixed list: each lever moved alone (the Scenarios rows), ordered by the held calls the target then needs, then by bookings. Ties keep the usual order: show rate (a process fix and the fastest), then price (a framing and structure fix), then close rate (the slowest, and it compounds). A lever the founder's rates already meet is listed as buying nothing here. Because the order is worked from the same rows as the Scenarios table, the chat, the fix order and the table always name the same biggest lever.

Improve the rates until the target needs less activity, rather than working harder at today's rates. Hiring comes after these: a hire under a leaky process pays for the leak.

## 9. Scenarios, and "three bets, not a plan"

Today's rates, then each lever moved alone, then all three together, each worked from whole sales:

- show rate to 70 per cent;
- price up 10 per cent;
- close rate on held calls to 30 per cent (or an offer on every held call, where offers are counted);
- all three together;
- where capacity binds, the price the ceiling needs (section 7).

A lever the founder's rates already meet gets no row and is listed as already met. Each row shows sales, held, booked and leads a month, bookings a selling day, hours a week and whether the calendar fits. If the plan only fits when all three improve at once, it is three bets, not a plan, and the plan says so.

## 10. Channels, never blended

Where the founder gives leads and bookings by source over the last 90 days, the bookings needed are shared across channels by each channel's share of today's bookings, and each channel's leads are worked at its own booking rate (and its own show rate where it has 10 or more bookings). A channel with under 10 leads in 90 days enters as a capped experiment, not a channel the plan rests on. Without counts by source the plan is not split, because an even split would be an invented figure.

## 11. The hiring trigger

Where all three levers together still break the calendar, a hire is triggered. Planning default: a setter first, to take booking and qualifying off the founder's hours; productive in weeks 3 to 4 and at full pace from week 8; so with a target date, they start by that date less eight weeks. This skill stops at "a hire is triggered": who to hire and how is a separate job.

Where delivery binds, it is not a sales hire: a sales hire adds no delivery capacity. Price and fit first.

## 12. The weekly pace and the first week

The pace is the monthly plan over 52/12 weeks: bookings, held calls, offers (where counted) and sales a week, and bookings a selling day. Uncapped, each is shown to one decimal ("1.4 held calls a week"), not rounded up to whole calls, because rounding a 6-a-month plan up to 2 a week asks for 44 per cent more than the target needs; under two held calls a week the plan also gives the figure a fortnight. Where capacity binds, the pace is set at the ceiling, not at the target, in one decimal rounded down, so a week never asks for more than the calendar or delivery carries, and only then does the plan say "Set at your calendar".

The first week is two to four actions, each dated (the founder's next call days, skipping any dated days off they gave) and owned (the founder, or the person who books calls), chosen by what breaks first, plus a tally so next month's rates are measured, and a check of the week against the pace.

The re-plan date closes the plan: 30 days where any rate is an estimate, a default or directional; 90 days where every rate is measured.

## 13. Prices, sales tax and the before-tax question

This skill never works out tax of any kind and never says what a tax rule requires.

- **Prices are planned as entered, before any sales tax.** The plan carries one neutral line, once: "Enter prices before any sales tax (VAT, GST or similar); ask your accountant whether you need to charge it." Nothing is added to or taken off a price.
- **A price that reads as including sales tax** ("7,200 incl GST", "inc VAT", or `price_includes_sales_tax` set to yes) is planned on as given and raised as a [NEED]: the founder gives the price before any sales tax, from their own invoice or their accountant. The script never divides by a rate.
- **Profit before tax or take-home.** Always ask. Take-home: the plan runs on the figure but raises a [NEED] that every figure is too low until the founder's accountant gives the before-tax figure. Never estimate, gross up or name a tax.
- No thresholds, rates, registrations, filing dates or institutions of any country appear anywhere in the plan.

## 14. Planning defaults and where each comes from

Every default is said out loud before the plan is shown and is a yellow cell in the workbook. None is a statistic about other businesses, and none may be presented as one.

| Default | Value | Basis |
|---|---|---|
| Show rate, inbound | 60 per cent | Merigrove sales planning default where there is no history: the conservative end of a working band |
| Close rate on held calls, inbound | 20 per cent | as above |
| Show and close, outbound | 70 and 10 per cent | as above |
| Hours per call held | 1.5 | a 45 to 60 minute call plus preparation and follow-up; the founder's figure wins |
| Hours a week for sales calls | 8 | assumption when skipped |
| Selling days a month | 20 for a five-day week, scaled to the founder's call days | working default |
| Days the founder takes calls | Monday to Friday when not given, said out loud | working default; the founder's week wins |
| Share paid in the month they sign | 100 per cent | assumption when skipped |
| Thresholds | show under 65 per cent, close under 20 per cent, leads at 3 times today's | working lines for what binds |
| Lever lines | show 70, price up 10, close 30 per cent | working lines for the scenarios |
| First setter | productive in weeks 3 to 4, full pace from week 8 | working default |
| Fits, tightly | from three quarters of the selling hours | working default |
| Months to reach a monthly-fee target with no date | 6 whole months, said out loud | working default; the founder's date wins |
| Retention lever | clients staying 2 months longer | working line for the scenarios |
| Plausibility stops | a call over 4 hours or under a quarter of an hour, a price under 50, a target under 100, over 60 selling hours a week, a stay over 120 months | a question to the founder, never a silent fix; the founder can confirm |

## 15. The founder's currency, dates, spelling and week

No country is assumed. Each of these follows the founder, read from what they write or asked once in the read-back.

| Item | Read from | When nothing settles it |
|---|---|---|
| Currency | `currency`, or a symbol or code in their figures (£, €, S$, A$, ₹, RM, USD, SGD) | a bare $ shows as $ and is said out loud as "dollars"; no symbol at all shows plain figures. Never converted |
| Date order | `date_style` ("day first" or "month first"), from how they write dates | day first with the month in words (21 October), which no reader can misread, said out loud |
| Spelling | `spelling` ("British" or "American"), from their own writing | British, the skill's house spelling; set American when the founder writes it |
| Working week | `call_days` ("Monday to Friday", "Sunday to Thursday", "Mon to Sat") and `no_call_days` | Monday to Friday, said out loud |
| Holidays and leave | `days_off`, dated, as the founder gives them | none; the skill holds no holiday calendar |
| Number style | detected once from their figures (decimal point or decimal comma, grouping by comma, dot, space or apostrophe, symbol before or after) | asked when a figure reads two ways |
| Date order and paper | `country`, through `locale_defaults` (month first only where the country writes it so; Letter or A4) | day first with the month in words; paper left to the printer |

## 16. What this method does not do

- It does not say what the market will pay. The price the ceiling needs is a planning figure.
- It does not work out tax, sales tax, social charges or any figure set by law, and does not say what a law requires. The founder's accountant gives those figures.
- It does not forecast cash flow or a pipeline of named deals.
- It does not write call scripts or outreach.
- It does not choose a hire; it says when one is triggered.
- It is a planning tool, not financial, tax or legal advice.

## 17. Monthly fees: retainers stack

A monthly fee (retainer, subscription, membership) is not one sale at one price. Each client pays every month they stay, so the clients already paying count towards the target, and the clients who leave have to be replaced. Folding the months into one price ("3,500 x 7 months") says "2 sales a month, nothing breaks" when the first month of a new client adds one month's fee, not seven; reading the fee as a one-off price asks for 11 new clients a month when 4 will do. Both are wrong.

| Step | Arithmetic |
|---|---|
| What one client leaves a month | fee less what one client costs to deliver a month (or fee x margin, or the fee on the revenue route) |
| Paying clients needed at once | what the business must leave a month / what one client leaves, rounded up |
| Clients leaving | with clients staying L months on average, about 1 in L leave each month: paying clients move as A(next month) = A x (1 - 1/L) + new clients |
| To hold the target | paying clients needed / L new clients a month, rounded up |
| To get there by the date | the fewest whole new clients a month that take today's paying clients to the number needed in T whole months: (needed - today x (1 - 1/L)^T) / (L x (1 - (1 - 1/L)^T)), rounded up |
| New clients a month in the plan | the higher of the two |

The plan prints the paying clients month by month at that pace and the month the target is first reached. Where calendar or delivery caps new clients, it says when the target is reached at the cap, or that it never is (at the cap, the most paying clients the business can hold is the cap times L). Clients staying 2 months longer is a scenario row: for a retainer, retention is often a bigger lever than price. Cash follows paying clients; the share paid on signing is not used. Without a figure for how long clients stay, none are counted as leaving, raised as a [NEED].

## 18. Targets with a date

A yearly figure is never divided by 12 until the founder says it is the rate they want to be running at. "250k this year" on 20 October is either a run rate of 20,833 a month or 250,000 to make in the ten weeks left, and the two plans differ by a factor of ten. The script stops and asks when `target_kind` is missing.

- **Months left.** From today to the date, in months to one decimal, and the whole calendar months of selling between them (the months after this one that end on or before the date). The plan counts whole months, said out loud.
- **Run rate by a date.** One-off prices: the monthly plan, with the months left stated. Monthly fees: the new clients a month to reach the paying clients needed by the date (section 17).
- **Profit by a date.** One-off prices: the total over the whole months left is planned as a monthly figure. Monthly fees: the paying client-months between now and the date must cover the profit, the running costs and the founder's pay; today's clients carry their share as they leave, and new clients carry the rest.
- **What the ceiling reaches.** Where capacity binds, the plan says what the most the founder can carry reaches instead: the month the target is first reached, or the profit made by the date.

## 19. Reading the founder's numbers

Every figure the founder types goes through `scripts/locale_numbers.py`. The decimal style is detected once from everything they wrote (4.850,00 sets a decimal comma, so 15.000 is fifteen thousand); a figure that still reads two ways stops with one question. Durations read in the founder's words and language (1,5h, 90 minutos, 7,5 Std., 1h30). A value that holds two figures that are not a range ("45 min plus prep so call it an hour") stops and asks which; a range is read as its midpoint and noted. Every hours figure read is listed in the Assumptions. Headline figures are checked for plausibility before anything is built (section 14). Figures are written back in the founder's own style, and the note gate reads the note the same way and checks each figure against the plan's figure for the same thing (a "held calls" figure must be a held-call figure from this plan).
