# Method: is the business ready for this hire?

Contents
1. The question before the job ad
2. The six conditions
3. The cash scenario
4. The verdict: Ready, Not yet or No
5. Not yet is conditions, never a date
6. The contractor alternative
7. The role from the hours it frees, and the first-hire order
8. Working defaults and where each comes from
9. The hire's cost: fully loaded, or pay alone
10. What this method does not do

All arithmetic runs in `scripts/conditions.py` and `scripts/cash_scenario.py`. The workbook carries the same formulas, so the report and the spreadsheet cannot disagree. Never compute a figure in prose; copy it from the script output.

## 1. The question before the job ad

The commonest hiring mistake in a business of one to five people is the exhaustion hire: the founder is drowning, a good month arrives, and a fixed cost is added on the strength of it. Payroll rises, cash cover drops within a quarter, and the founder's hours do not fall because nothing was written down to hand over. The check answers whether this person should exist yet, before anyone writes an advert.

A hire is close to a one-way door. Notice periods, morale, recruiting time and the months it takes someone to become useful make it slow and costly to reverse. A contractor is a two-way door. The check treats them differently for that reason.

## 2. The six conditions

Ready needs all six. A condition with a missing figure is Unknown, and Unknown cannot pass.

| # | Condition | Passes when | Source |
|---|---|---|---|
| 1 | Cash holds in a bad quarter | With the full cost of the hire loaded from the start date, the bad-quarter balance stays at or above the cash floor in every week from today to the hire's 13th week | Merigrove finance guidance (13-week forecast, stress case, one-month floor) |
| 2 | Margin above your floor for two months | Gross margin at or above the founder's floor in each of the last two months | Merigrove finance guidance (hiring conditions) |
| 3 | Six months of the role covered | Recurring or contracted revenue for the next six months, plus repeat revenue from regulars, memberships, plans or packs (for an appointment or retail business), plus weighted pipeline, is at least six months of the role's full cost | Merigrove finance guidance (hiring conditions); repeat revenue as cover is a working default for review |
| 4 | Your worst month is rising | With 18 months or more: the worst month of the last six is above the worst of the same six months a year earlier. With 12 to 17: above the worst of the six before passes; anything else is Unknown, because the two halves are different seasons | Merigrove data guidance (the floor month); the season rule is a working default for review |
| 5 | A real role, and a use for your freed hours | Named tasks fill at least 80 per cent of the role's hours, they form one job one person could own, the biggest task is at least partly written down (not known is Unknown, with the question asked), and the freed hours go to work with a route to revenue (usually selling) | Merigrove management guidance |
| 6 | You are near full, and a price rise came first | The founder is at 90 per cent or more of the client hours (or clients) they can take on, and a price rise for new clients has been tested | Merigrove operations and product guidance |

Why each matters, in a line:
1. Cash is what makes a hire survivable. Profit on paper does not pay a salary in the week clients pay late.
2. A hire adds fixed cost. Thin margin means each extra sale barely funds it.
3. A salary is paid every month whether or not the next sale lands; secured revenue is what stands behind it.
4. A rising worst month is growth. A high best month is a good month. Fixed cost should follow growth.
5. A person with no defined work and a founder with no plan for the freed hours produces a payroll cost and no change in the founder's week.
6. If there is room in the diary, the answer is selling. If demand outstrips the diary at today's price, a price rise is the cheapest capacity there is and comes before a hire.

Judgement in condition 5. The script checks the hours and the written-down flag. Whether the tasks form one job is Claude's judgement, recorded in `role_coherent` with a one-line reason the founder can read: tasks in one area of the business that one person could own (all client admin; all fulfilment of one offer) form a job; a scatter of unrelated chores across sales, design and bookkeeping does not.

## 3. The cash scenario

From today to the 13th week of the hire (at least 13 weeks; longer when the start is more than a week away), week 1 starting on the run date, in two cases. A window that ended at week 13 from today would miss most of a hire that starts in week 5, and all of one that starts in week 15.

- **Opening balance:** cash in the business account today.
- **Money in:** the average monthly revenue of the last three months, spread evenly across weeks (x 12 / 52). How fast clients usually pay is already reflected in today's balance and in that average, so the usual quarter brings in the usual weekly rate from week 1.
- **Money out:** the average monthly costs of the last three months, the founder's own pay included, spread evenly; known bills (a tax payment, an insurance renewal, annual software, each with the founder's amount and date) on their dates; the hire's monthly cost from the start week (section 9), plus any one-off costs (recruitment, laptop) in the start week.
- **The bad quarter (stress case):** 20 per cent less money in, and every payment arriving 15 days later than usual. The cut applies to everything that arrives in the window except revenue under contract for the next six months (`contracted_next_6_months`), as if the slowdown had already begun; contracted revenue is not cut but arrives just as late. Month-to-month recurring revenue is cut like the rest, because it can stop. The delay means the first two weeks bring in nothing and the third a part week. With no delay (patients who pay on the day), the report says "paid on time as usual". This is the conservative reading: a slowdown that starts today would reach the bank only after clients' usual payment time, and a 13-week window would then hide most of it.
- **Known low periods.** A closure or quiet season the founder names (dates and their own figure for the drop, and for costs if they fall too) is loaded in both the usual and the bad quarter. The window runs on to the end of any such period that starts within a year (at most 60 weeks), so the winter the founder warned about is tested; the month-three line stays at the hire's 13th week.
- **Seasons not named.** Months in the revenue history more than 10 per cent below the monthly average this check uses are listed, each saying whether its next turn falls inside the window (which assumes the average) or after it (not tested), so the founder can name the period.
- **The floor:** one month of costs. Before the start date that is today's monthly costs; from the start date it includes the hire. The founder can set it higher (three months is common for founders who sleep badly), and a saved learning will hold it.
- **Pass:** the bad-quarter balance never drops below the floor in the window.

**The month-three line** is the balance in the hire's 13th week, in both cases. It leads the report because it is the number a founder can picture.

**The later start rule.** When the bad quarter breaks the floor only late in the window (week 9 or later), or a start up to eight weeks later would hold, the script tests later start weeks with today's figures held and reports the earliest start that holds the floor to its 13th week. This is a condition on the start date with today's figures, not a forecast of when the business will be ready.

**The cash gap, with and without the hire.** The largest amount by which the bad-quarter balance falls short of the floor. "An extra (amount) in the bank before the start" is the cash condition in its plainest form. The same bad quarter is run with no hire, against one month of today's costs: when the business is short even without the hire, the report says so first ("Without the hire, the same bad quarter already leaves you $9,291 short; the hire adds $18,333"), because a founder reads the whole gap as the price of the hire otherwise.

**What the business can carry (the ceiling).** The largest monthly cost for the hire, all in, at which the cash still holds the floor in every week to the hire's 13th week (and through any named low period), found by trying costs in the same scenario: one figure for a usual quarter, one for a bad one, rounded down to a whole 10. The floor rises with the cost, as it does for the real hire. It answers "can I afford it?" without knowing what goes on top of pay: when the cost is pay alone, the gap between pay and the ceiling is the room for everything else, and the founder can compare the loaded figure with it the moment it arrives. Zero means the floor breaks even without the hire. It is arithmetic on the founder's own figures, never an estimate of an on-cost.

**What it has to bring in.** The hire's monthly cost divided by today's gross margin (the latest month, or the low end of a rough range): the revenue a month the hire has to bring in or protect to cover itself. With a typical new client's monthly fee from the founder, the script also gives the number of new clients, rounded up. On pay alone it is marked as understating the real figure.

The money-in model in one formula: bad-quarter money in for week w = (contracted weekly revenue + the rest x (1 less the cut)) x (the part of week w that falls after the delay, less each low period's cut times the part of week w it covers, shifted by the delay). `cash_scenario.py simulate()` and the workbook columns use the same formula.

## 4. The verdict: Ready, Not yet or No

- **Ready:** all six conditions pass, and the hire's cost is the fully loaded figure from the founder's accountant or payroll provider (section 9), not pay alone.
- **No:** the hire as described is the wrong answer, not merely early. Three cases: (a) an employee for under the contractor line (15 hours a week by default): a contractor arrangement you can stop does this, a commercial judgement about commitment and never a ruling on anyone's legal status; (b) the business already spends more each month than it brings in and even the usual quarter breaks the floor: a hire adds to the gap; (c) there are no named tasks and no named use for the freed hours: there is no job yet.
- **Not yet:** anything else. One or more conditions fail or are Unknown.

The verdict is the first line of the report, in those words, followed by one sentence naming what decides it.

## 5. Not yet is conditions, never a date

Every failed or Unknown condition carries what must be true, in the founder's figures: "An extra $545 in the bank before the start", "Two months in a row with gross margin at or above 55%", "Scheduling and inbox written down well enough that someone else could do it from the notes". Never "you'll be ready in March". A date is a forecast the check cannot make; a condition is something the founder can work towards and test.

## 6. The contractor alternative

Run beside every check where the founder gives a contractor's hourly rate: the same bad quarter with the contractor's cost (rate x hours a week x 52 / 12 a month) in place of the hire, at the role's full hours and, where the role is bigger than the contractor line, at the line. A contractor is a variable cost and a two-way door: the usual route while the work is under about 15 hours a week or can be defined piece by piece. An employee suits continuous work that needs the founder's judgement passed on over months, once all six conditions hold.

Whether a person would be an employee or a contractor is never judged by this skill, in any country. The report says so in one line and names the founder's accountant, payroll provider or an employment lawyer where they hire. The comparison here is commercial only: cash in a bad quarter and how easily the cost can be stopped.

## 7. The role from the hours it frees, and the first-hire order

The role is defined from the founder's own week: the tasks it takes off them, with rough hours, and what the founder will do with the hours back. Hours come from a week of the founder's calendar or a rough list; recall flatters, so a calendar is better.

Rank what to hand over by hours a week, largest first. Small easy tasks first frees little and teaches the founder that delegation fails.

The usual order of first hires, applied to the role type:
1. Admin and operations support: the cheapest, frees the most founder hours, lowest risk.
2. Delivery: once the delivery steps are written down well enough that someone can produce the work unaided. Raises how many clients the business can serve.
3. A setter: once leads exceed the founder's selling hours and the sales call is written down.
4. A closer: last. Until the sales call is written and proven, the founder's own close rate is the business's best asset.

A handover counts as complete when the person has produced the output unaided and the founder has reviewed it, at least twice.

## 8. Working defaults and where each comes from

Every default is stated to the founder before the figures and listed in the report's assumptions. None is a statistic about other businesses, and none may be presented as one.

| Default | Value | Source |
|---|---|---|
| Bad quarter: money in | 20 per cent lower, applied to everything received in the window except contracted revenue | Merigrove finance guidance sets the 20 per cent for sales; applying it to all non-contracted receipts from week 1 is a working default for review |
| Bad quarter: payment | every payment 15 days later | Merigrove finance guidance (stress case) |
| Forecast window | from today to the hire's 13th week, at least 13 weeks | Merigrove finance guidance sets 13 weeks; running it to the hire's 13th week is a working default for review |
| Cash floor | one month of costs, hire included from the start | Merigrove finance guidance; the "hire included" reading is a working default for review |
| Start date | four weeks from today, when not given | Working default |
| Gross margin floor | 50 per cent, when the founder has none | Working default for a service business; Merigrove's own sources give ranges that differ, so it is flagged for review. Always replaced by the founder's figure |
| Role cover window | six months | Merigrove finance guidance |
| Contractor line | 15 hours a week | Working rule, unverified; for review |
| Near full | 90 per cent of the most the founder can take on | Working default; for review |
| Role filled by named tasks | 80 per cent of its hours | Working default |
| Later start search | up to week 26 | Working default |
| Season flag | a month more than 10 per cent below the average this check uses | Working default; for review |
| Window with a known low period | to the end of any period starting within a year, at most 60 weeks | Working default; for review |
| Plausibility stops | a monthly hire cost above a month's revenue; under one unit of money an hour; cash under a thousandth of monthly costs; money in and out more than 20 times apart; capacity now over one and a half times the most; a bill above a year's revenue | Working default: a question, never a correction |

## 9. The hire's cost: fully loaded, or pay alone

The scenario carries one monthly figure for the hire, and it is always the founder's:

- **Fully loaded (`cost_basis: loaded`).** Pay plus whatever the founder's accountant or payroll provider says goes on top of it where they hire: employer taxes or charges, benefits, retirement contributions, insurance, whatever applies there. The skill does not know or need the parts. It stores the total as founder supplied, names who gave it (`cost_from`), and uses it in plain arithmetic. A payroll calculator the founder ran counts as their figure. A contractor's invoice is a full cost.
- **Pay alone (`cost_basis: salary_only`).** When the founder knows only the salary or hourly rate, the skill asks them to get the fully loaded figure and, meanwhile, runs on pay alone (a salary divided by 12, or rate x hours x 52 / 12). The month-three line, the cash condition and the full-cost section all say these figures understate the cost of the hire. The verdict cannot be Ready on this basis: if every condition passes, it is Not yet, with the loaded figure as the one thing to get.
- **Not said.** A monthly figure the founder has not confirmed as loaded is treated like pay alone for the verdict, and the report asks them to confirm it.

The report lists what the loaded figure should cover, as a prompt for the founder's conversation with their accountant, with no rates and no country: pay; whatever goes on top of pay where they hire; benefits promised; equipment and software; cover during paid leave if they would pay for it; training and the founder's own onboarding time. One-off costs go in the start week.

Before and after:
- Before: "Employer taxes on $36,000 come to about $2,750, so budget $3,230 a month."
- After: "The scenario uses $3,000 a month, which is pay alone. It understates the cost of the hire. Ask your accountant or payroll provider for the fully loaded monthly cost and run the check again."

## 10. What this method does not do

- It does not compute or estimate tax, employer charges, benefits, wage floors, holiday entitlement or any on-cost, for any country, and it does not say what a law requires.
- It does not decide whether someone would be an employee or a contractor, write contracts, check anyone's eligibility to work, set up payroll or give tax advice. One line, then the founder's accountant, payroll provider or an employment lawyer where they hire.
- It does not forecast revenue. The usual quarter is the last three months repeated, less any low period the founder names with their own figure; the bad quarter is that less 20 per cent on non-contracted revenue, paid later.
- It does not model sales tax on each invoice. Any tax payment enters as a known bill with the founder's amount and date.
- It is a planning tool, not financial, tax, legal or employment advice.
