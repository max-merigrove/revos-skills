# Method

How Scope Guard turns an offer and a list of requests into a scope, a creep ledger, priced replies and a change form.

## Contents

1. Diagnose first
2. Sort each request: in, out or unclear
3. The arithmetic
4. Inputs that can flip the result
5. Choosing the recommended reply
6. The goodwill allowance
7. Client dependencies and dates
8. Acceptance: when "done" stops moving
9. Defaults and where they come from
10. What the skill does not do

## 1. Diagnose first

Scope creep has three causes, and only one of them is fixed by better replies. Name the cause in one line with the evidence from the founder's own words, before writing anything.

| Diagnosis | Evidence that points to it | What the kit leads with |
|---|---|---|
| **Creep on a defined scope** | A proposal, agreement or clear list exists; the client asks for things that are not on it | The ledger and the replies; the scope statement tightens the out list |
| **A vague offer** | Nothing written says what is included; the founder cannot say whether a request was in ("it's sort of general support") | The scope statement first. Most requests are marked unclear until the founder decides; the replies come second |
| **Fulfilment drift** | Sold as done-with-you (the client does the work, the founder guides) but the founder now does the client's part, usually after the client fell behind once | The boundary per deliverable (who does it), a pause rule for when the client falls behind, and the founder's part priced as a done-for-you add-on the first time it happens |
| **A new scope, written before the first extra** | No requests yet; the founder wants a scope of work for a new client or offer | Scope statement, change form and allowance; no ledger |
| **One request to price** | A single "how do I answer this" with no wider pattern | The three replies, the form, and a short scope only if the founder has none |

More than one can be true. Lead with the one that explains most of the hours. Drift is the one founders most often miss: "I end up doing it for them" is the tell. When the founder's actual hours run over plan by more than the extras explain, say so: in-scope work is taking longer than it was priced, which is an offer and pricing problem rather than creep.

Source: the done-for-you, done-with-you and do-it-yourself fulfilment models and "hybrid drift" come from Merigrove's product method; the correction (put sold and delivered scope side by side, write the boundary with a pause rule, reprice the first time drift happens rather than absorbing it) is applied here.

## 2. Sort each request: in, out or unclear

For each request the founder lists:

- **In:** the agreed scope covers it, including its quantity (the third post of twelve is in; the thirteenth is out).
- **Out:** the agreed scope does not cover it, or it exceeds a stated quantity or number of change rounds.
- **Unclear:** the scope is silent. Do not decide for the founder. Ask in the readback ("Was the newsletter part of what you agreed?"). Once answered, set `resolved_as` and put the item on the included or not-included list, so it is never unclear again.

Status: `done` (done and not billed), `billed`, `asked` (open, needs a reply), `declined`.

A request that is the client's own job done by the founder (drift) is `out` with `kind: drift`.

## 3. The arithmetic

All of it runs in `scripts/scope_kit.py compute`. Never work a figure out in prose.

**Monthly retainer**

- Priced rate = fee a month ÷ planned hours a month. This is what the founder priced each hour at, whether or not they ever thought of it that way.
- Months counted = days from the start of the count to today ÷ 30.44, to one decimal place (at least half a month). The start is the date the founder gives, or the first of the month of the earliest request, stated as a default. In the workbook the months are live: a start date cell and a "count up to" cell (blank means today), so the hourly figure moves as next month's requests are logged.
- Effective rate = (fee × months) ÷ (planned hours × months + out-of-scope hours done without billing).
- Unbilled work at the priced rate = those hours × priced rate.

**One-off project**

- Priced rate = project fee ÷ planned hours.
- Effective rate = project fee ÷ (planned hours + out-of-scope hours done without billing).

**Basis, said every time.** "Worth £1,330 at your priced rate" (or "$2,760", or "S$1,425": always in the founder's currency) is time given away, valued at the founder's own rate. It is not cash that left their account. The kit says so beside the figure, because a founder who reads it as lost cash will make a worse decision.

**When the founder gives actual hours.** At actual hours a month, the rate is fee ÷ actual hours. Hours over plan × months, less the unbilled extras, is in-scope work taking longer than priced. The kit names it as a separate finding.

**Price of a change** = hours × rate for extras, rounded to the nearest 5 at 100 or more (nearest 1 below). The rate for extras is the priced rate unless the founder names their own (a day rate, a published hourly rate). Rates show to the cent when they are not whole ($162.50, 89,09 €), so a founder checking 10 hours at $162.50 = $1,625 sees it add up.

**Ranges.** Hours given as a range ("30-40 hrs", "3-4 days") are read range first: each end is converted (days at the founder's working day), the middle goes into the totals, and the price reply quotes both ends. A range is honest uncertainty; one figure would hide it.

**Scope it first.** When a request's top end is at least the month's planned hours (a retainer) or half the project's planned hours, `compute` marks it "scope it first" and the replies add that option, recommended by default: a short written plan or spec, then a firm price. A big build quoted as one figure from a founder's guess is where the next overrun starts.

**Plausibility stops.** Before anything is built, `compute` stops with a plain question when a headline figure looks misread: an hourly rate under 10 in any currency, a working day outside 1 to 16 hours, more planned hours a month than a month has, or a single request over 2,000 hours. A founder's "9.800,00 €" read as 9.8 would trip the first. If the founder confirms the figure, it goes into `confirmed` and the build runs.

**Sales tax: none computed.** Every price is worked out and shown before any sales tax. The kit carries one neutral line: "Prices are before any sales tax (VAT, GST or similar); ask your accountant whether you need to charge it." If the founder writes their own fee with tax words ("+ VAT", "+ GST", "plus sales tax"), the script keeps those words as the price wording and the price reply repeats them, so the reply matches the founder's own invoices. No rate, no with-tax figure and no registration question appear anywhere. A fee written including tax becomes a [NEED] for the figure before tax; the skill never nets it down.

**Days into hours.** Where the founder gives hours in days ("half a day", "2 days", "a day and a half"), the script uses the founder's own working day if they gave it, otherwise 8 hours, stated in the kit as an editable assumption.

**Equal-effort swap.** A deliverable whose hours are within 25% of the request's hours (or within one hour) is a candidate. The script lists candidates and the nearest one. When there is none, the swap reply is left out and the kit says why ("No equal-effort swap in the plan"); the build rejects a swap whose deliverable is not equal effort. Part of a deliverable can be swapped when its share is written as a sum (`swap_hours: "=10*6/12"`, six of twelve posts) and comes out equal. A swap needs deliverable hours; ask for them only if the founder wants a swap option.

## 4. Inputs that can flip the result

Each of these is asked, or defaulted out loud, before anything is computed:

| Input | Why it flips the result | If missing |
|---|---|---|
| Fee and planned hours | Set the priced rate, every price and the effective rate | [NEED]; the ledger still shows hours |
| Whether each request was in what was agreed | Decides in or out | Unclear; asked in the readback |
| Hours per request | Sets every price and the creep total | [NEED] for that request; left out of totals |
| Monthly or one-off | Changes the effective-rate formula | Read from how the fee was written, stated |
| Rate for extras | A day rate above the priced rate raises every price | Priced rate, stated |
| Tax words on the founder's own fee | Whether the price reply repeats "plus VAT", "plus GST" or similar | None: prices stated before any sales tax, with the neutral line |
| Working day, where hours came in days | Every price built from days | 8 hours, stated, editable |
| Currency and date order | How every figure and date reads | Read from what the founder wrote; a [NEED] or a readback question, never a country guess |
| The start of the count | Months counted, so the effective rate | First of the month of the earliest request, stated |
| Relationship | Which reply is recommended | Strong, stated |
| Hours in the signed agreement, where they differ from the hours priced on | Which rate is real, and what the scope statement may say | Both rates shown; the client-facing scope quotes the agreement |

## 5. Choosing the recommended reply

Default order (the script's `suggested`):

1. The founder chose **swap only**: recommend the swap if an equal-effort one exists, otherwise next phase.
2. The request is big enough to **scope first**: recommend the scoping step.
3. The founder chose an **allowance** and the request fits inside it: recommend the allowance.
4. The client is **about to renew**: recommend next phase, folded into the renewal.
5. The relationship is **fragile** and an equal-effort swap exists: recommend the swap.
6. Otherwise: **price it**.

An active learning in memory overrides the order (for example "picks the swap for long-standing clients"). The founder can always pick another; the reason line says why the recommended one fits this client.

## 6. The goodwill allowance

An allowance is a deliberate, visible amount of free work that replaces invisible leakage. It is only ever the founder's choice: never a default, never written into a client message they did not choose (the build rejects it). The kit shows:

- what it is worth a year at the priced rate (allowance hours × 12 × priced rate);
- what the retainer pays an hour if the allowance is used in full (fee ÷ (planned hours + allowance hours));
- had it been in place since the start of the count, how much of the unbilled time it would have covered and what the rest was worth.

The client is told about the allowance and told each time a piece of it is used. An allowance the client never hears about is just creep with a name.

## 7. Client dependencies and dates

Every scope lists what the client must provide (content, access, feedback, approvals) with a date or a recurring day ("the 5th of each month"). The script reports each one as due, received or days late. Dates make a client-side delay visible and stop the founder silently absorbing it. The scope says that dates depending on a late item move by the same number of days.

A dependency without a date is a [NEED] and fails the rubric.

## 8. Acceptance: when "done" stops moving

Each deliverable has a "done when" line that either side can check: "approved by email, or five working days after delivery with no change request", "published", "signed off by the named contact". A feeling ("when the client is happy") is not acceptance and the script rejects it. Change rounds are capped per deliverable (default two); a further round is priced as a change.

Source: Merigrove's fulfilment method requires explicit acceptance at close and a final quality check against scope before anything reaches the client.

## 9. Defaults and where they come from

| Default | Value | Source | Who confirms |
|---|---|---|---|
| Goodwill allowance | None unless the founder chooses one (then 2 hours a month if they give no figure) | End-to-end test v1.3: a default allowance put a policy in the founder's mouth | Jack |
| Change rounds per deliverable | 2 | Working default; the brief names revision rounds as the commonest creep | Founder per offer |
| Hours in a working day, where hours came in days | 8, unless the founder gives their own | Working default, stated and editable; the founder's figure always wins | Founder |
| Price rounding | Nearest 5 at 100 or more, else nearest 1 | Working default | Max |
| Swap tolerance | Within 25% of the request's hours, or 1 hour; no swap reply when none fits | Working default | Max |
| Scope it first | A request whose top end is at least the month's planned hours, or half a project's | Blind test v1.1 (D11) | Max |
| Plausibility stop | Hourly rate under 10 units of any currency; working day outside 1 to 16 hours; over 744 planned hours a month; a request over 2,000 hours | Build Standard 13 | Max |
| Paper | From the founder's country; with no country, Letter for month-first dates or US, Canadian or Mexican currency, otherwise A4, stated | Build Standard 13 | Jack |
| Number style | Read once from the figures the founder typed (9.800,00 € means a comma decimal); written back the same way | Build Standard 13 | Jack |
| Sales tax on priced changes | Never computed; prices before any sales tax, one neutral line to the founder's accountant; the founder's own tax words repeated in the reply | Build Standard 0.1 | Jack |

None of these is presented to the founder as a fact about other businesses.

## 10. What the skill does not do

- It does not say whether any wording would hold up in a contract or a court, and it never says what a law requires or allows. Anything the founder may paste into an agreement is labelled a draft for a lawyer.
- It does not bill past work retrospectively or draft demands, threats or legal letters. If the founder wants to recover money for past extras, it stops, says that is a matter for a lawyer, and offers the forward-looking kit instead.
- It does not compute or decide sales tax, employment status or anything to do with an employee's workload.
- It does not assume a country. Currency, date order, working day, spelling and idiom follow the founder.
- It does not invent the founder's offer. If there is no offer to scope, it asks for one.
