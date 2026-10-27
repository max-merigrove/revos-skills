# Method

Contents
1. What the audit decides
2. The three piles and the five functions
3. From calendar to hours
4. The week and what the calendar misses
5. Confidence
6. Ranking: delete first, then hours a month
7. The two flags and the strategy block
8. Value of the hours
9. The proposed week
10. Return runs: did the handovers hold?
11. The commonest failure

## 1. What the audit decides

Where the founder's hours went in one or two real weeks, then what to stop, what to hand over and in what order. The options for every activity are delete, delegate to an existing person, automate, or keep. Hiring is not an option the audit recommends: it shows the hours a role would hold and leaves whether to hire to the founder and their cash.

The founder's hours are the ceiling on a one to five person business. Every question, decision and handover passes through them, so the business grows only as fast as their calendar allows. The audit moves hours out of delivery and administration into selling and direction.

## 2. The three piles and the five functions

Every activity goes in one pile (details and tests in `categories.md`):

1. **Only you**: the founder's judgement is what the client pays for, or the founder legally must do it.
2. **Someone could do it with instruction**: it follows a process, even one that lives in the founder's head.
3. **Nobody should be doing it**: no decision, reader or client depends on it.

And one function, for the flags:

- **Strategy**: direction, planning, pricing, reviewing the numbers to decide something.
- **Selling**: discovery calls, proposals, follow-ups, content and PR that win work.
- **Managing**: one-to-ones, team check-ins, hiring, training.
- **Delivery**: the client work itself, including travel to it.
- **Admin**: email, invoicing, bookkeeping, scheduling, reporting, paperwork.

Doing is delivery plus admin. Selling is kept apart from Doing so a founder who sells is not told to hand over their sales calls.

## 3. From calendar to hours

`parse_calendar.py` does this; never count by eye.

- Times are read in the founder's own time zone (from the calendar, or as the founder says). Repeating events are expanded from their rule in local wall-clock time, so a 9:30 meeting stays at 9:30 when the clocks change, whenever that happens where the founder is (or never, in Singapore). Skipped dates (EXDATE), extra dates (RDATE), and moved or cancelled single instances are applied.
- The working week (days and hours) comes from the founder, Outlook's own setting, or what the events show; public holidays and days off come from the calendar or the founder. No country's calendar is built in.
- Left out: all-day events, meetings the founder declined, cancelled events, events with no length, and anything sorted as personal or not work.
- Overlapping events share the overlapping time equally, so the week is never counted twice. Placeholder holds that sit on top of real meetings are sorted as not work.
- Each activity gets hours each (its hours in the window over its entries) and times a month. Times a month comes from the repeat rule where an activity is one repeating series that runs the next year (a weekly call is 4.33 a month even if one was skipped in the window), otherwise from the count in the window scaled to a month.
- Repeating events with no entry in the window (a quarterly planning day, a monthly accountant call) are listed separately with their rule-based frequency, and count unless the founder says they are not real.
- A month is 52/12 weeks everywhere. "Daily" means each of the founder's working days; "a day" of work is their working day.

## 4. The week and what the calendar misses

Calendars miss email, messages, admin and evening work. The week total comes from the founder ("roughly how many hours did you work?"), and the gap between that and the calendar is filled with rows for what they say it was. Whatever is still unexplained is shown as "not placed", never spread across activities.

With no total from the founder, the week is the calendar plus 20 per cent, flagged as a default (`thresholds.md`). On a return run, the hours the calendar missed last time replace the 20 per cent.

If the rows add to more than the week the founder gave, `rank.py` stops: ask which is right, a longer week or a row counted twice.

## 5. Confidence

- **Good**: a tracked week, or a calendar holding at least 70 per cent of the week.
- **Fair**: a calendar holding 40 to 70 per cent, the rest from what the founder said.
- **Low**: under 40 per cent from the calendar, or recall only.

Recall-based audits flatter the founder and are labelled low confidence at the top of the report. The correction is to track one real week with the log template and run again.

## 6. Ranking: delete first, then hours a month

Deletion comes first because it is free and founders skip it. Delete-test candidates: meetings with no decision in the last four weeks, reports nobody opens, second checks on work that is already right.

Then rank everything delegated or automated by **hours per instance times instances per month**, largest first. Rank by cost, never by ease: handing over small, easy tasks first frees little and teaches the founder that delegation fails. The report shows the top five, with hours a week beside hours a month; the workbook shows them all. If the founder chooses the order, theirs is used (`founder_order`) and the hours-only order is shown beside it.

For each helper, `rank.py` also gives what their handovers cost a week and the share of the hours they free that must go into work at the founder's rate for the help to pay for itself: the helper's hourly cost divided by the founder's hourly value. Ana at $38 against a founder's $185 pays for herself if about a fifth of the freed hours earn that rate. It is arithmetic on the founder's own figures, not a forecast.

Kept-for-now rows (could be handed over, nobody to take them) are shown with their hours a week. Where they add up to a coherent block, the report says it is the shape of a role and a cash question.

## 7. The two flags and the strategy block

From Merigrove's founder time allocation guidance (`thresholds.md`):

- **Doing above 50 per cent** of the week signals a delegation or automation opportunity: hand over the top-ranked task first.
- **Strategy below 15 per cent** means it is being crowded out: fix a protected block of at least four hours a week, paid for by the deletions.

The guidance's full allocation (Managing 40, Strategy 20 to 30, Doing 30 to 40 per cent) assumes a management layer. For a one to five person business it is a direction of travel, not a target, so the report shows only the two flags.

## 8. Value of the hours

Before any value is shown, the headline figures are checked: an hour worth under 1 unit of currency, or less than the dearest helper costs, means a figure was almost certainly misread (450万 read as 450, a day range counted as two days). The run stops with the figure it read and asks; a figure the founder confirms is recorded and used.

Hours back a month are the deletions plus the top five handovers. Value is those hours times the founder's rate:

- the rate they gave, or
- monthly sales divided by their hours a month (the hours they work in a week times 52/12).

The report says which, and that freed hours earn that only if they go into paid or selling work. Where the founder gave a helper's cost an hour, the cost of the delegated hours is shown beside it. Tool costs for automations are not counted unless given. No rate: a `[NEED]`, never an invented figure.

## 9. The proposed week

After the changes, each function's hours are laid into mornings and afternoons, in half hours:

- the strategy block first, kept whole on a morning (the first day of the founder's working week by default);
- delivery in mornings, so making time stays unbroken (Paul Graham's maker's schedule, 2009: fragmented days destroy deep work and selling time alike);
- selling calls together in mid-week afternoons, at most three hours of selling in any one morning or afternoon; team time on one afternoon; admin batched on the last full working day;
- laid out on the founder's own working days and each day's own hours (a Saturday that ends at 12:30 has no afternoon); when those are unknown the week is laid out on plain days and the report carries a `[NEED]`;
- work the founder does at set times outside the day (evening calls with clients in another time zone, nightly email) stays where it is, listed as kept as now, not moved into daytime blocks;
- freed hours go to selling unless the founder chooses strategy, delivery or fewer hours. Freed selling hours that do not fit under the three-hour limit are shown as free for selling or fewer hours, not packed into the days;
- hours not placed in any activity are not laid out at all; the report says how many and points to the one-week log, which places them.

Other work beyond the working day is shown as hours beyond it, with what they are, not hidden. The next handovers are where they come from.

## 10. Return runs: did the handovers hold?

A handover held when the activity's weekly hours fell by at least half; it "came back" when it was handed over before and the hours are back. A returned handover usually means the process was never written down or "done" was never defined: the next attempt starts with the steps written while the founder does it once more. A handover counts as complete when the person has produced the output unaided and the founder has reviewed it, at least twice (operator practice, unverified).

## 11. The commonest failure

Optimising the calendar instead of auditing it: colour-coding, moving blocks around, adding focus time on top of the same work. The correction is to count one real week (or a fortnight of calendar) before changing anything, then delete, then hand over by hours.
