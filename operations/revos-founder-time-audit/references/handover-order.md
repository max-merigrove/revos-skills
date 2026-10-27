# Handover order: delete, delegate, automate, keep

Contents
1. The order
2. Delete
3. Delegate: to whom, and whether they have room
4. Automate
5. Keep, and the shape of a role
6. When a handover comes back

## 1. The order

1. Delete everything in the nobody-should pile. Free, immediate, and the step founders skip.
2. Hand over the someone-with-instruction pile, ranked by hours a month (hours each times times a month), largest first.
3. Keep the only-you pile, after one challenge on anything that reads as admin.

Never reorder by ease. The top of the list frees real time; the bottom frees minutes. The one exception is the founder: when they say what goes first ("Ana's work before Jules's"), set `founder_order`; the report follows their order and shows the hours-only order beside it. Never remove a handover from the list to honour an order.

## 2. Delete

The tests: no decision made in it in the last four weeks; nobody reads it; it double-checks work that is already right. Propose the deletion as a default out loud in the readback ("I've marked the Tuesday status call delete unless it produced a decision in the last four weeks") so the founder can object in one word. The reason goes in the row and appears in the report.

A meeting that carries a little real value often becomes something smaller rather than nothing: a written update in a shared document, or ten minutes on one day. Say so in the reason; the hours still count as deleted because the founder's time in it goes.

## 3. Delegate: to whom, and whether they have room

- Delegation to an existing person wins when the work follows a process, even one in the founder's head.
- `who` is a named person the founder gave (Jo, Marcus, Mei Ling), or "a contractor (to find)" when nobody is free. Never name a person the founder did not mention.
- Give each person in `team` their `spare_week` when the founder says it. `rank.py` adds up the hours handed to each person and raises a `NEED` when they exceed it: the founder chooses which handover waits, or whether the person's hours grow. Never quietly overload someone.
- Give `cost_hour` when the founder says what the person costs them an hour; the report shows the cost of the delegated hours beside their value. Use their figure as given: never add payroll taxes, pension or other on-costs, which depend on the country and are for their accountant or payroll provider.
- The reason names how: "Jo pulls the figures and drafts; you review for 15 minutes". A handover with no written steps tends to come back (section 6).
- Whether someone is an employee or a contractor depends on the rules where they work: one line in the report pointing to the founder's accountant or an employment adviser, no advice.

## 4. Automate

Automation wins when the step is rule-based and recurs weekly or more: payment reminders, receipt capture, booking links instead of email back-and-forth, recurring invoices. `who` names the tool type plainly ("accounting software reminders", "a booking link"), not a brand unless the founder already uses it. The report says tool costs are not counted unless given. Automation rarely removes every minute: where a check remains, say so in the reason.

## 5. Keep, and the shape of a role

A someone-with-instruction row stays with the founder only with a reason (nobody free, nobody qualified yet). These rows are listed under "Could be handed over but kept for now" with their hours a week.

When they add up to a coherent block (design production, routine services, bookkeeping entries), the note may say it is the shape of a role. It never says to hire: whether the business can afford a person is a cash question, and that is where the closing line points.

## 6. When a handover comes back

On a return run, `rank.py --previous` marks each saved handover as held (hours fell by half or more), partly held, not moved yet, or came back. A handover that came back usually means:
- the steps were never written down, so the founder took it back the first time something went wrong; or
- "done" was never defined, so the founder kept checking.

Propose a learning for the next audit ("Invoicing came back twice; write the steps while doing it once more before handing it over again") and keep the row as delegate with that reason. A handover counts as complete when the person has produced the output unaided and the founder has reviewed it, at least twice (operator practice, unverified).
