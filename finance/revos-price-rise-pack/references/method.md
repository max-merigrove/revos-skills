# Method: how a price rise is planned

Every rule here is computed by `scripts/rise_plan.py`. This page explains the rules so you can say why, answer the founder's questions, and do the work by hand if code cannot run. Every number marked "working default" is a planning default the founder can change. None is a market fact; never present one as what other businesses do.

Contents
1. The rollout: who moves first
2. The target for each client
3. The step: cap, closure, rounding
4. The groups
5. Dates: notice, alignment, billing, renewal
6. Cash: the next twelve months and the run rate
7. Break-even: how many clients can leave
8. Reasons, concessions, outcomes and the next wave
9. Doing it by hand
10. Credits

## 1. The rollout: who moves first

A price rise is a rollout, not a switch.

1. **New clients first.** Change what new clients pay before you move existing ones. New clients have no old price in their heads, so they show whether the number is accepted, and the new-client price then becomes the plainest reason an existing client can check. Where the diary is full or a waitlist exists, say so in one line of the plan as a reason to move now; there is no threshold.
2. **Existing clients in a wave, not all at once.** The plan groups clients and the letters go in a set order: the clients you ring first, then the letters. Watch replies for one billing cycle before the next wave.
3. **Grandfathering is a transition with an end date, never an exemption.** A client left at the old fee with no end date is a subsidy that grows every year. The plan's "Two steps" and "gentle" routes are the dated version of grandfathering; every concession goes on the Exceptions sheet with its end date.
4. **Say why, in advance, once.** One true reason, notice from the founder's own terms, and a stated choice. A softening route (a later start for a longer commitment) is a trade with an end date, never a discount for nothing.

Expect to lose some clients. The ones most likely to leave over a fair, explained rise are often the least profitable, which is why break-even counts contribution (section 7), not revenue.

## 2. The target for each client

The target is the fee that client would pay at the founder's own anchor. The first rule that applies:

1. **The founder's target for that client** (`target_fee`), used as given.
2. **The new-client price scaled by hours:** new-client price divided by the hours it buys, times this client's hours. "New clients pay 3,000 a month for about 12 hours" is 250 an hour; a client on 14 hours has a target of 3,500.
3. **An hourly target** the founder gives, times this client's hours.
4. **The founder's own median:** the middle hourly rate across their own clients, times this client's hours. Said aloud as "your own median", with a note that the founder's new-client price would make it specific.

Any direct cost the founder gives for a client (a contractor, software, ad spend) is added to its target, so the founder's hour stays whole.

No hours for a client: no target. The client gets a flat step of the cap, marked "hours not given", and the plan asks for the hours. No hours anywhere and no target: the whole plan is a blanket rise, and the output says so and names the one thing that would make it client by client (hours a month per client).

## 3. The step: cap, closure, rounding

- **Step cap** (working default 20% of the current fee, founder changeable, per client too). No single step is bigger. A large catch-up in one go reads as an ambush; two dated steps read as a plan.
- **Closure** (working default 95%). If one capped step reaches at least 95% of the target, one step. Otherwise two steps, the second six months after the first (working default), each capped. Whatever gap remains is shown, with the number of further capped steps it would take, for the annual review.
- **Renewal-bound clients** get one step, at renewal.
- **Rounding** (working default): new fees are rounded down to the nearest 10 below 1,000 and to the nearest 50 from 1,000, in the founder's currency units. Rounding down keeps every fee at or under both the cap and the target. If rounding would leave the fee unchanged, the fee is rounded down to a whole unit instead. A founder's own rounding overrides this.
- **Gentle** (the founder asks to go easy on a client): that client's cap is halved and the rise always comes in two dated steps, so the old fee still has an end date.

## 4. The groups

First match wins (detail and letters in `segments.md`):

1. **Hold:** at or above target, or the founder says hold. No letter.
2. **Price to keep:** the client costs money at today's fee (direct costs at or above the fee), or the founder would be relieved to lose them. The fee is the target, uncapped, or the founder's own figure.
3. **Reset the scope:** the founder says the scope has crept. Two options: the same work at the new fee, or today's fee for a smaller defined allowance (by default, the hours today's fee buys at the new fee's hourly rate) with extra work at the anchor hourly fee. If the client picks the allowance, the cash for them is nothing and the founder gets hours back; the plan says so.
4. **At renewal:** the price can change only at renewal, or a fixed term or price lock is running.
5. **Two steps:** one capped step cannot reach 95% of target.
6. **Raise now:** one step closes the gap.

**Call first** is a flag, not a group, and a short list so it ranks someone: clients with tenure of at least four years or among the largest quarter by annual fee qualify (both working defaults, founder changeable; ties at the boundary count only when they sit clearly above the middle fee), and of those only the largest by annual fee are kept: one for every three letters, at most three (`call_first_max` changes it). Everyone else gets the letter.

A client paying under half the target whose scope the founder has not mentioned gets a question: "Has the scope crept?" If yes, they become Reset the scope. If a reset still leaves the fee under half the target, the plan says so and recommends a price to keep or a deeper reset, never a bigger percentage.

## 5. Dates: notice, alignment, billing, renewal

From the send date:

1. Notice end = send date plus the notice the founder gave (days, weeks or months). Unknown notice uses the 60-day planning default and HOLDs that letter until the founder confirms.
2. Alignment: where the notice runs to a month end or quarter end ("3 months to the quarter end", "3 Monate zum Quartalsende"), the notice end rolls forward to that period end and the change starts the day after. The script reads the period end from the notice text itself; words after the notice that it does not understand ("30 days or at renewal") stop the run with a question, so a notice is never half read.
3. The effective date is the first billing date on or after that point, on the founder's billing day (and billing months for quarterly or yearly billing).
4. Renewal-only or a running term or price lock: the effective date is the renewal (the day after the term ends) or the first billing date after it. A renewal that falls inside the notice period moves to the next renewal, and the plan says so.
5. A start date the founder asks for ("from April") moves dates later, never earlier than notice allows. A requested date earlier than notice allows is flagged and not used.
6. The second step is the first billing date on or after six months from the first.
7. Every date prints with its weekday. A send date that is not one of the founder's working days is flagged. Where the founder asked for a later start, the plan gives the last working day the letters can go and still keep that date.
8. The send date cannot be in the past: letters are dated the day they go and are never backdated.

The skill never says a date meets a contract or a law. The founder confirms with their contracts.

## 6. Cash: the next twelve months and the run rate

- **Next twelve months** (working default window, from the send date): for each billing date in the window on or after the effective date, the new fee less the old, times the fee units billed (12 for an annual bill of a monthly fee, 1 for a quarterly fee billed quarterly). Project clients: the rise times the projects the founder expects a year, in proportion to the part of the window after the effective date.
- **Run rate:** the full year once every dated step has landed: (last step fee less today's fee) times fee units a year.

Both are shown so the notice delay is never hidden: "18,850 in the next 12 months; 25,800 a year once every step lands".

## 7. Break-even: how many clients can leave

Contribution per client = fee less the direct costs the founder gave. Overheads stay when a client goes, so they are left out.

- **Per client:** the largest share of that client's volume that could go and leave the founder level = change in contribution / new contribution.
- **Portfolio:** share of the raised revenue that can leave = total change / total new contribution across the raised clients. The same as d / (CM + d), where d is the rise as a share of old revenue and CM the old contribution margin.
- **By name, two orders:** departures in order of new contribution, smallest first and largest first, with the running net after each. A departure costs the client's old contribution plus the rise you would have had. The plan names the departure that turns it negative: "lose Penrose and you are still ahead; lose Oakridge as well and you are behind" and "lose Blue Fern and you are behind".
- **Lumpy counts:** with ten or fewer clients raised, each departure is a big step; plan on the named clients, not the percentage.
- **Loss table:** the net at 0, 5, 10, 15, 20 and 25% of the raised revenue leaving.
- **Freed hours:** only when the founder gives a value for an hour, a separate line counts the hours a departure frees at that value, labelled "only if you refill them". It never enters the break-even.

The script checks the break-even against a brute-force pass over every subset of up to 12 raised clients and refuses to build on any mismatch.

## 8. Reasons, concessions, outcomes and the next wave

**Reason ranking** (first that applies; a learning can reorder it): for a client the founder says was priced too low from the start, that fact ("I set your fee too low when we started, and I am putting that right"); then the founder's price for new clients, stated as a fact the client can check and set beside that client's own hours ("New clients now pay 2,800 a month for about 14 hours, which is 200 an hour; your work runs to about 22 hours a month"), so it is true for a client whose new fee is above the new-client price; with no hours for the client, the new-client price is used only when the new fee sits at or below it; how the scope has grown, in the founder's words; the date of the last change, if the founder states one (only for clients who were with them then); a cost the founder puts a figure on. None: the letter states the change plainly and the plan marks `[NEED: one true reason]`. People accept a rise that follows a real, explained reason and resent one that looks like it exploits them, so a checkable reason beats a vague one.

**Concessions** are trades with end dates: a later start for a twelve-month commitment, half the step now and half three months later, a smaller scope at today's fee. Each goes on the Exceptions sheet with its end date and its cost against the plan in the window. A concession given for nothing, with no end date, becomes the new price.

**Outcomes** (return run): accepted (the plan as sent), countered (the agreed fees and dates, logged as a concession with an end date: the day before the first agreed fee starts, or the next review), left (old fee until the end date, nothing after; the follow-up says what it would add if they paid the new fee on invoices before they went), held. Confirmations state only the agreed terms: a client staying at today's fee is told their fee "stays at" it until a date, never "from" the plan's step date. The realised twelve-month figure is set against the plan, with one plain verdict line ("Losing Oakridge cost 13,200 in the window; the rises that landed added 14,200").

**Next wave:** clients still below target after the agreed fee, with their review date twelve months after their last step. Leavers drop out; nobody already moved is raised again before their review.

## 9. Doing it by hand

If code cannot run: for each client, (1) target = anchor per hour times hours (plus direct cost); (2) step 1 = the lower of target and fee x (1 + cap), rounded down to 10 or 50; (3) if step 1 is under 95% of target, step 2 = the lower of target and step 1 x (1 + cap), rounded down; (4) dates as in section 5; (5) twelve-month cash = (step 1 less fee) x billings at step 1 + (step 2 less fee) x billings at step 2; (6) run rate = (last step less fee) x fee units a year; (7) break-even = total run-rate change / total new contribution. Show every step in a table. Formulas to paste: run-rate change `=(LAST-FEE)*UNITS`; cash `=(S1-FEE)*N1+(S2-FEE)*N2`; break-even `=SUM(CHANGE)/SUM((LAST-COST)*UNITS)`.

## 10. Credits

The rollout in section 1 adapts the price-change rollout in marketingskills (`pricing`, Corey Haines, MIT licence; see LICENSE.md), rewritten for service clients with notice and end-dated concessions. The break-even presentation follows the standard break-even volume formula for a price change, as Impact Pricing presents it. The point about fair reasons draws on Kahneman, Knetsch and Thaler, "Fairness as a Constraint on Profit Seeking" (1986), and Heyman and Mellers, "Perceptions of Fair Pricing". No wording is quoted from any of them.
