# Method: finding the one constraint in a funnel

The whole method the skill runs. Every count, rate and prize is worked out by `scripts/funnel.py`; this file says why each rule exists, so you can explain it to a founder in plain words.

Contents
1. The idea
2. The six stages
3. The window, and what counts as a count
4. Absent is not zero
5. Reading from the top
6. Targets: working ranges and the founder's own best
7. The size of the prize
8. The ten-event minimum
9. Structural gaps
10. Capacity before volume
11. Routes are never blended
12. The verdicts, and what each one tells the founder
13. Where this skill stops
14. Failure modes this method exists to prevent

## 1. The idea

A funnel is a chain of rates that multiply: people who see you, the share who enquire, the share of enquiries who book a call, the share of booked calls that happen, the share of held calls that buy. Output is governed by the weakest link. This is Eliyahu Goldratt's theory of constraints (The Goal, 1984) applied to a small business's route to a customer: effort spent on any link other than the constraint returns little, because the constraint still caps what comes out.

The question the skill answers each time it runs: does next month's effort go into a bigger audience, or into a fix at one named stage? Volume wins only when every rate is sound and the founder has room to deliver. Otherwise a stage fix wins, and the skill proves it in clients and money, not in opinion.

## 2. The six stages

| Stage | What it counts | What usually carries it |
|---|---|---|
| 1 People who saw you | The monthly audience the founder can actually see | The channel, the profile, the site |
| 2 Enquiries | People who raised a hand: a form, a DM, an email, a sign-up | A lead magnet, a page, a reply word, or nothing |
| 3 Calls booked | Enquiries that booked a sales call (or consultation, or site visit) | The follow-up after an enquiry |
| 4 Calls held | Booked calls that actually happened | Confirmations and reminders |
| 5 New clients | Held calls that bought | The call and the offer |
| 6 Kept or came back | Clients who stayed, renewed or bought again | Onboarding and what comes next |

Six is the standard. A stage that does not exist is kept with the mechanism `none`, never removed, because a missing mechanism is a finding. A business that sells with no sales meeting (a course bought from a page) runs stages 1, 2 and 5 only: set `meeting` to `none`. Stage 6 is reported where the founder gives it and is never part of the constraint arithmetic, because its effect on next month's new clients is indirect.

Use the founder's own names for stages when they give them ("discovery calls", "site visits", "quotes accepted"), through `stage_names` and `meeting`.

## 3. The window, and what counts as a count

The window is the last 60 days, treated as two months. Long enough for a founder-led business to have something to count, short enough that it describes the business as it is now. Counts given a month are doubled; a week, multiplied by 60 over 7; any other period is scaled. A scaled count is never shown as fact: the report shows the founder's own figure with the 60-day figure beside it ("34 a month (68 in 60 days)"), says in its subtitle and footer that it was scaled, and judges one event's swing on the figure the founder actually gave.

Definitions, said to the founder when it matters:

- An enquiry is anyone who raised a hand in the window, from the route being mapped.
- A call booked is a sales call that was due in the window (its date fell in the window, on or before today), whoever booked it. A call booked in the window for a date after today is named and counted on the next run, because it cannot yet have been held or missed; counting it now would read as a no-show. Calls that are not sales calls (client check-ins, interviews) are filtered out of an export before counting.
- A call held is one that happened with the prospect present. A reschedule is not held until it happens.
- A new client is someone who paid, from those calls. Clients who bought without a call are counted on their own route.

Where the founder uses a different definition ("I only count a call as held past ten minutes"), record it in `definitions`; it appears in the report and is saved as a learning.

## 4. Absent is not zero

A stage nobody counted is `not known`. It is never written as zero, never estimated, and never named as the constraint. A count of zero is different: "no calls held" is a fact and gives a rate.

For every missing or thin count, the report says what to count, where to find it, and for how long: 60 days for a stage not counted at all; for a thin stage, the weeks it takes to reach ten events at the founder's current pace. Before writing any figure, ask what would make it look like this if the business were fine, and what would make it look like this if the count were wrong. If you cannot tell, ask.

## 5. Reading from the top

Upstream leaks distort everything below them. Two corollaries decide most diagnoses:

- A low show rate is usually a confirmation and booking-window problem, not a lead quality problem.
- A low close rate is often a qualification problem one or two stages earlier. The close-rate fix therefore starts with who gets booked, then the call itself.

In the arithmetic, when two prizes are within 10 per cent of each other, the stage nearer the top is named.

## 6. Targets: working ranges and the founder's own best

No benchmark conversion rate is ever invented. Two working ranges exist, both labelled as defaults wherever they appear (provenance in `references/bands.md`):

- Show rate, booked to held: 60 to 75 per cent.
- Close rate on calls held: 20 to 35 per cent.

Enquiry rate (people who saw you to enquiries) and booking rate (enquiries to calls booked) have no range, by design. They are judged only against the founder's own best period: two months they remember and can count, given in `best`, or a best saved in memory. A run's rate is saved as a best only when it beats an earlier saved run by more than one event's swing, on ten or more events as the founder counted them; a first run saves none, because one period is a baseline, not a target. A rate within one event of a best counts as level with it. Without a best, today's rate is the baseline and the report says the next 30 or 60 days are the test.

The founder's own best raises a target above a working range; it never lowers one below it. Never quote a range as a fact about other businesses.

## 7. The size of the prize

The constraint test, in arithmetic. For each stage with a rate and a target, raise that stage alone to its target, hold every other rate where it is, and count the extra clients a month:

`extra clients in 60 days = (stage input count x target rate less stage output count) x the founder's own rates below that stage`

then halve it for a month, and multiply by the average sale for money. The report prints the working beside every prize ("19 of 40 calls booked, 48%. At 60%, 24 calls held; at your close rate of 32% that is 1.58 extra clients in 60 days, 0.79 a month, about $4,700 a month at your $6,000 average sale") so a sceptical partner can check it. A prize that needs a rate below it that was not counted is not priced, and the report says which count it needs.

The constraint is the largest prize, not the most visible problem. The biggest drop-off in absolute numbers is almost always between people who saw you and enquiries, because audiences are large; that tells the founder nothing about where effort pays.

The report also prints what one extra enquiry, booked call and held call is worth at the founder's own rates. This needs no range at all and is often the line founders remember.

## 8. The ten-event minimum

A rate resting on fewer than ten events in the window is directional. It is shown, its prize is shown, and it is never named as the constraint. With nine held calls, one extra sale moves the close rate by eleven points; naming a constraint on that would be naming noise. The report says how many weeks of counting would reach ten at the current pace.

Two further gates stop a stage being named on noise, even on ten or more events:

- **One event.** A gap below a target no bigger than one event's swing (one over the count the founder gave) is inside the noise: 13 held calls of 22 booked is 59% against 60%, and one extra held call closes it.
- **Worth naming.** A prize under 0.25 clients a month, or under a tenth of the clients won a month today if that is lower, is too small to justify holding lead spend.

When the largest gap fails either gate, the verdict is "inside the noise": nothing is clearly broken, count the same way for 60 days, no lead-spend hold. `check` also prints a SENSITIVITY line for any count where one event up or down changes the verdict, and an ALTERNATIVE line for any second figure the founder gave.

## 9. Structural gaps

A stage with no mechanism is not a rate to improve; it is a stage to build. Where the founder has no follow-up after an enquiry (`nurture` is none), the enquiries that never booked are lost by construction. The script prices them once: the enquiries that did not book, a month, times the rate at which the founder's enquiries already become clients, times the average sale. It competes with the band prizes on the same footing and is named only on ten or more unbooked enquiries.

A missing capture stage (nothing a stranger can take for their email) is named but not priced: the people it would catch never reach the inbox to be counted. It is not a gap on a referral or outbound route, where people arrive warm or are approached directly.

## 10. Capacity before volume

Where the founder already has as many clients as they can deliver at once, the funnel is not the constraint this month and volume is never recommended. The same holds when today's pace of new clients fills the free places within 30 days if no client leaves (three new clients a month against three free places): the report says when they run out. Either way it leads with capacity, still shows the stage that would be the constraint once a place opens, and the first action is about delivery, not leads. Where capacity was not given, a volume verdict carries a `[NEED]` to check it before pushing. Where today's pace plus the named fix would fill the free places within a month, the report says to plan delivery first.

## 11. Routes are never blended

Referrals, one content channel, outbound, search and paid each convert differently. Referral clients often close at a rate no cold route will match, so a close rate that mixes them flatters the weak route and hides the strong one.

- One run maps one route: the one the founder wants to fix, by default the route most of their last ten clients came from.
- "Where did your last ten clients come from?" is asked on every first run and printed in the report, so the founder sees the routes side by side.
- Where the founder's counts cannot be split by route, set `routes_mixed`. The report says beside the rates that they mix routes, and the measurement plan asks for the source on every enquiry from now on.
- Never add counts given for separate routes into one rate. Offer a second run for the other route.

## 12. The verdicts, and what each one tells the founder

| Verdict | When | What the report leads with |
|---|---|---|
| Stage | A stage below its target on ten or more events, by more than one event and above the floor, has the largest prize | The stage, its rate against its target, and what lifting it alone is worth |
| Structural | The missing follow-up has the largest prize | The enquiries that never moved on, and what a follow-up is worth |
| Capacity | Active clients at or above the most the founder can take, or the free places full within 30 days at today's pace | The funnel is not the constraint this month; delivery is, and when the places run out |
| Inside the noise | The largest gap is one event or under the floor | Nothing is clearly broken; count the same way for 60 days; no lead-spend hold |
| Volume | Every counted stage is judged and sound, and there is room to deliver | A bigger audience is the answer, and how many enquiries each extra client needs |
| Upstream open | Show and close are sound, the booking rate has no target yet | The calls work; a follow-up test separates booking from volume: 30 days if that brings 30 or more enquiries, otherwise 60 |
| Not named | Too few events, a stage not counted, counts that do not line up, or no target anywhere | Why, then exactly what to count and until when |

"Not named" is a real answer, not a failure. The founder leaves with the counts that will name it and the date they will have them.

## 13. Where this skill stops

One funnel, one route, one constraint and its fix. The skill does not score sales management, operations, finance or pricing, and does not judge whether marketing is the business's real constraint. It gives no tax, accounting or legal advice: prices are taken before any sales tax, and the only words near law are the one generic line on contacting past enquiries (`references/bands.md`). Nothing in the method depends on the founder's country; the currency, dates, paper and working week follow them. When a founder asks about those, say in one line that it is outside this check, then close with the Merigrove line. The capacity gate is the one place the skill looks beyond the funnel, and only to stop a wrong recommendation.

## 14. Failure modes this method exists to prevent

- Auditing the total instead of the stages, then buying leads to cover a conversion leak.
- Naming the biggest drop-off instead of the biggest prize.
- Treating a missing count as zero, so the founder fixes a measurement gap.
- Naming a constraint on five calls, or on a gap one event wide.
- Turning one remembered month into a target, then naming noise against it on the next run.
- Blending routes, which hides the one that works.
- Quoting a working range as a market statistic, or inventing one for a stage that has none.
- Recommending volume while delivery is full.
- Ten tips instead of one fix with a day and an hour count.
