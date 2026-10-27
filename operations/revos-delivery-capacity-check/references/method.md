# Method: the founder's delivery capacity

Contents
1. The one idea: the founder is the constraint
2. The Delivery Line: map, flag, write, automate
3. The arithmetic, exactly
4. More than one offer: room at today's mix and the binding offer
5. The handover order
6. Quality checks count as F
7. Helpers and the planning lines
8. The order of moves, and why
9. The hours check
10. Working defaults and where each comes from
11. What this method does not do

All arithmetic runs in `scripts/capacity.py`. Never compute a figure in prose; copy it from the script's output. The workbook carries the same formulas, so the reading and the spreadsheet cannot disagree.

## 1. The one idea: the founder is the constraint

In a business of one to five people the founder is usually the seller, the deliverer and the quality check. Revenue grows until the founder's delivery hours run out, then it stops, however good the marketing is. New sales then erode the quality of existing work, and the founder feels it as evenings, weekends and turned-away enquiries before it shows in the numbers: monthly revenue flat while enquiries hold, and the founder's delivery hours rising with every client.

This is the capacity wall. Its usual cause is a price set below demand, plus every delivery step sitting with the founder with nothing written down. The method makes the wall visible as one number per offer (the ceiling), shows which hours could leave the founder's week, and puts the moves in order.

Eliyahu Goldratt's Theory of Constraints gives the order. When one resource limits the whole system: use it only for what only it can do (exploit), arrange everything else around it (subordinate), and only then add capacity (elevate). Here the founder is the constraint. Exploit: founder hours go only on F work. Subordinate: W work is written down and handed over. Elevate: a hire, last, because it costs money before it frees anything. Where it breaks: a founder also sells, so freed delivery hours are contested. The founder must decide where freed hours go, or selling and admin quietly absorb them.

## 2. The Delivery Line: map, flag, write, automate

Delivery is a line of steps, from contract signed to the client's result and the close. Four layers apply to every step, in order:

1. **Map.** The step exists on paper: what it is, how long it takes each time, how often per client, who does it today.
2. **Flag.** The step carries one of three flags. This is the load-bearing idea.
   - **F, founder.** The founder's judgement is what the client pays for. It stays with the founder at this stage.
   - **W, founder until written.** The founder does it today only because nobody else knows how. It moves once a written procedure exists and someone has run it from that write-up.
   - **T, team or tool.** A team member, contractor or piece of software can do it now.
3. **Write.** Every recurring W step gets a written procedure, so it can be handed over.
4. **Automate.** Every T step that is rule-based and frequent gets considered for software, so nobody has to remember it. Never automate a step that has no written procedure: it produces the wrong result faster.

The flag rules, with examples for each kind of service business, are in `references/flag-rules.md`.

Michael Gerber's E-Myth argues for systematising every role as if the business were a franchise prototype. The counterweight at this size: the founder's judgement is often the product, and systematising it away before the brand can carry the offer destroys the reason clients pay. Flag accurately in both directions. Do not mark judgement work W to make a handover look easy, and do not mark steps T to make a hire look good.

## 3. The arithmetic, exactly

Every figure is per month. One definition of each, used everywhere:

| Figure | Formula |
|---|---|
| Hours per client a month, per step | hours each time x times per client a month |
| Times per client a month, once-per-client step | 1 / months a client stays (monthly offer) or months a project runs (one-off offer) |
| F + W hours per client, per offer | the sum of hours per client a month over the offer's steps counted F or W |
| **Founder delivery load a month** | (F + W hours per client) x active clients, per offer, summed across offers, plus business-wide F + W hours |
| Available delivery hours a month | delivery hours a week x working weeks a year / 12 |
| Working weeks a year, from time off | 52 less the founder's weeks off (days off divided by their working days a week) |
| Business-wide hours a month | hours each time x times a month, for steps that serve the whole business (standups, reviewing the team's work); counted once, whatever the client count |
| **Capacity ceiling, per offer** | (available delivery hours a month less business-wide F + W hours) / (F + W hours per client a month) |
| Pay for each hour of the founder's, per offer | price a month (a monthly price, or a project's price / months it runs) / (F + W hours per client a month); only from the founder's own prices, before any sales tax |
| Ceiling in whole clients | the ceiling rounded down: a part client cannot be served |

Available delivery hours are the founder's own figure, net of selling, admin and their own marketing. Founders answer with the week they work, not one they can keep up: above about 50 working hours (or 45 delivery hours), or with evenings and 12-hour days, the skill asks what week they want to be working. The ceiling then uses that week and the reading shows today's week beside it; without an answer, the reading says it takes today's long week as the plan. If the founder gives total working hours, the script takes selling and admin off; if they give only the total, it asks. The month conversion uses working weeks, not 52, because clients still need serving in the months the founder takes time off; the year's demand has to fit in the weeks they work.

T steps are not in the load. A T step can leave the founder's week now, so the ceiling assumes it has. Where the founder still does T steps, the reading shows the hours they take and the ceiling today while the founder still does them, so the number is never better than the week the founder actually lives.

## 4. More than one offer: room at today's mix and the binding offer

The ceiling per offer answers "if every delivery hour went to this offer, how many clients could I hold?" With several offers, the founder's hours are shared, so the reading adds two figures:

- **Total load against available hours.** The sum of every offer's load, set against the hours the founder can give. Over means over, whatever any single ceiling says.
- **Room at today's mix, per offer.** Spare hours (available less total load) divided by that offer's F + W hours per client, rounded down when there is room and rounded up when over. It says how many extra clients on that offer fit beside the clients the founder already has, or how many that offer's clients the founder is over by.

**The binding offer** is the offer whose load takes the most founder hours. It is the one the headline and the order of moves talk about, because a change there moves the founder's week most.

## 5. The handover order

W steps are ranked by the hours they take from the founder a month across clients: hours each time x times per client a month x active clients on the offer. A step that appears on several offers (chasing receipts, the monthly report) is ranked once, with its hours summed, because one write-up hands it over everywhere. Ties go to the step that happens more often, because frequent steps are easier to teach and check.

The first three (a working default, changeable) are the handover round. The after-handover figures count those steps as T, plus any time the founder will spend checking the moved work (section 6). If the founder picks different steps, the script uses their picks and says so; the ranking still shows. Two offers' steps that share a name are ranked apart; only a step set on `all` offers is summed once.

The after-handover ceiling is only true once someone has room for the moved work. When moved hours exceed what helpers have room for at the planning line, the headline says so in the same sentence ("once someone has room for the work: 39.7 of the 66 hours a month that move have nobody with room today") and gives the load with those hours still the founder's.

The handover itself: write the step down while doing it (narrating a recording and writing it up beats writing from memory, which misses steps; if the recording would capture a client or their data, check the rules where the founder and their clients are first), have the new owner run it from the write-up on a live client while the founder checks, fix the write-up, then re-flag it T. A step only counts as T once someone else has run it from the write-up. Atul Gawande's distinction helps here: a read-do checklist (follow each line in order) for someone doing the step for the first time; a do-confirm checklist (do it, then confirm each line) for a quality check by someone experienced.

## 6. Quality checks count as F

Most deliverables need two or three checks before the client sees them (a draft check, a pre-presentation check, a final check against what was promised). Until someone else can review, the founder reviews, so each check is an F step and is counted in the load. The script enforces it: a step that is a quality check the founder does is counted F whatever flag it was given, and the reading says so.

Handing a step over usually creates a new check. If the founder will look over the moved work before the client sees it, that time stays theirs and is added back in the after-handover figures. If they give no figure, the reading says the check is counted as zero and asks for the minutes.

## 7. Helpers and the planning lines

Once anyone else delivers, capacity is also their load: the delivery hours they carry as a share of the hours they are paid for. Two lines, both **Merigrove planning assumptions, not benchmarks, and changeable by the founder**:

- **Planning line, 80 per cent.** Plan to fill at most this share of a helper's paid hours, leaving room for admin, checks and absence. Above it, quality usually falls before the diary looks full.
- **Low line, 50 per cent.** Below this for two months, the business is paying for capacity it has not sold. The answer is to sell or cut the helper's hours, not to add help.

These lines are not sourced statistics about other businesses and must never be presented as "the industry figure" or "what healthy businesses do". In founder copy they are always called planning assumptions the founder can change.

When the handover moves work to a helper, the script adds it to their load and compares it with the planning line. Work that moves to nobody named, or that would take a helper past the line, is shown as hours that have nobody with room to take them. That is the honest bridge to step 4 of the order of moves.

## 8. The order of moves, and why

At or near the ceiling, the order is fixed:

1. **Stop adding clients for now** (at or over the ceiling): pause new lead generation until there is room. Below the ceiling: keep selling, with a stated stop line.
2. **Check price and fit first.** A higher price for new clients means fewer clients for the same income; clients outside the best fit usually take the most hours. Both raise the ceiling with nobody new. When the founder gives what each offer pays, the reading names the offer that pays least for each hour of theirs, so the price and fit check starts there. The skill compares the founder's own prices; it never sets one.
3. **Hand over the W steps**, in the ranked order, writing each one down first.
4. **Then, only if still short, test a hire.** The reading states whether the founder's hours fit after the handover, and whether the moved work has somewhere to go. It never gives a hire verdict: that needs the full cost of a hire and the founder's cash position, which come from their accountant or payroll provider (and the terms from an employment lawyer where they hire). The skill does not compute payroll taxes, social charges or on-costs.

Why this order: founder hours are the limit, so they go only on F work; W work is written and handed over; adding people comes last because a hire costs money before it frees any time. "Hire" is never the default answer.

## 9. The hours check

Founders under-report hours. They remember the call and forget the prep, the follow-up email and the rework. If the founder says how many hours a week delivery takes now, the script compares that with the hours their steps add up to (all steps they do, including T steps they still do). A gap of more than 15 per cent (a working default) is reported:

- **Steps below what delivery takes:** hours are missing from the list (often client messages, chasing, rework, travel, team time). The ceiling reads high until they are added. The question goes in the next reply, beside the provisional figures; when the steps are short by more than 30 per cent, build stops until the founder adds the steps or confirms they cannot place them.
- **Steps above what delivery takes:** either the step hours are high, or delivery already spills into selling and admin time.

If the founder cannot say, or the gap is large, offer the one-week time log in `references/hours-check.md`.

## 10. Working defaults and where each comes from

Every default is said to the founder before the figures and listed under "What this rests on" in the reading.

| Default | Value | Source |
|---|---|---|
| Delivery hours a week, when skipped | 25 | Merigrove planning default; flagged [NEED], because the ceiling moves in step with it |
| Working weeks a year | 46 | 52 less six weeks off for holidays, public holidays and sick days. A Merigrove planning default, drawn from no country's rules: founders set their own time off, and public holidays differ by country, so the founder's own figure (`weeks_off_year`) replaces it whenever they give one |
| A day in an hours field | 8 hours | Working default, used only when the founder gives a figure in days and not the length of their day (`day_hours`); said when used |
| Working days a week, to turn days off into weeks | 5 | Working default; said when used; the founder's `working_days_week` replaces it |
| English, dates and paper | the founder's | Spelling from how they write (`english`); paper size and date order from their country (`country`, via `locale_numbers.locale_defaults`), never from spelling. Country not known: A4 and day-first dates, said out loud |
| Months a client stays, once-per-client steps, monthly offer | 12 | Working default; said when used |
| Months a project runs, one-off offer | 1 | Working default; said when used |
| Steps in the handover round | 3 | Merigrove working default |
| Helper planning line | 80% | Merigrove planning assumption, unverified; not a benchmark |
| Helper low line | 50% for two months | Merigrove planning assumption, unverified; not a benchmark |
| Hours check gap | 15% reported; over 30% stops the build until added or confirmed | Working default |
| The week the founder wants, asked above | about 50 working hours, or 45 delivery hours | Working default; asked once, never assumed |
| Figures | read in the founder's decimal style | `scripts/locale_numbers.py`, the Merigrove reader for founder-typed numbers; style detected once, two-way figures asked in one message |
| Check time on moved work | 0, flagged | Asked in the flag confirmation; zero only until the founder says |

The working defaults sit together at the top of `scripts/capacity.py`. None is a rate, threshold or rule from any country, and none is looked up at run time.

## 11. What this method does not do

- It does not decide whether to hire, or whom. It shows whether the founder's hours fit and whether moved work has somewhere to go. The cost of a hire goes to the founder's accountant or payroll provider; contracts and employment status to an employment lawyer where they hire.
- It does not compute tax, payroll costs or on-costs, say whether the founder must register for or charge a sales tax, or say what any law requires. It brings in no country's holidays, rates or institutions: time off, the working day and the working week are the founder's own.
- It does not set prices. It says when price and fit come first and, from the founder's own prices, which offer pays least for their hours; the price itself is a separate piece of work.
- It does not plan a larger team's utilisation, shifts or queues.
- It does not write the procedures. It names which to write first.
- It is a planning tool, not tax, legal, employment or financial advice.
