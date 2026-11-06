# The six groups

`rise_plan.py` puts every client in exactly one group, first match wins. This page says what each group means, what its letter does, and what must be true before that letter goes.

| # | Group | Rule | Fee | Letter |
|---|---|---|---|---|
| 1 | Hold | At or above target, or the founder says hold | Unchanged | None. The client is told nothing |
| 2 | Price to keep | Costs money at today's fee, or the founder would be relieved to lose them | Target, uncapped, or the founder's figure | New fee from the date; the fee at which the work continues; tell me by the reply-by date if it does not fit |
| 3 | Reset the scope | The founder says the scope has crept | Option A: capped step for the same work. Option B: today's fee for a smaller defined allowance, extra work at the anchor hourly fee | Two options, reply A or B; A applies if no reply |
| 4 | At renewal | Price changes only at renewal, or a term or price lock is running | One capped step at renewal | New fee from the renewal date; reply to confirm |
| 5 | Two steps | One capped step falls short of 95% of target (or the founder asked to go gently) | Two capped steps six months apart | Both fees and both dates in the first line |
| 6 | Raise now | One capped step reaches 95% of target | One step | New fee and date in the first line |

## Call first

A flag on any group except Hold, kept to a short list so it ranks someone: of the clients with tenure of at least four years or in the largest quarter by annual fee, only the largest by annual fee, one for every three letters and at most three. The founder rings these before the letter goes, using the call outline, and sends the letter the same day as the written record. Both thresholds are working defaults; a founder who says "calls for anything over $2,000 a month" is giving a learning to propose.

## What must be true before each letter goes

- **Raise now:** notice confirmed (not a planning default); the reason is one the founder gave; the client is not mid-way through a deadline the founder knows of.
- **Two steps:** as Raise now, and the founder is content to commit to both dates now.
- **At renewal:** the renewal date is right and is not inside the notice period.
- **Reset the scope:** the founder has confirmed Option B (`scope_confirmed`): the hours it includes (their own figure; else their hours less the extra hours they named; else the hours today's fee buys at Option A's hourly rate, rounded down to the half hour, so B is a smaller scope and never a free hold) and the hourly fee for extra work (default: the anchor). Until then the letter is HOLD.
- **Price to keep:** the founder would genuinely be content if the client chose to finish. No exit or termination wording: that depends on the founder's contract and is theirs to take advice on.

## Groups the founder can force

The founder's word overrides the rule: "hold Fieldmark" (`hold`), "go gently with Aurora" (`gentle`), "I'd be glad to see the back of them" (`relieved`), "Oakridge gets loads of extras" (`scope_crept`, with `scope_line` keeping the founder's point, written to the client: "you often ask for extras on top of the retainer"). Record what they said; never infer it.
