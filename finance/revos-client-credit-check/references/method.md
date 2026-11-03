# Method

## Contents
1. The order of work
2. Background: what a lender looks at, and what a service founder can see
3. Reading "no information"
4. The unpaid-work model
5. How verdict and terms relate
6. Working defaults

## 1. The order of work

1. **Entity first.** Who is signing: the legal name, the registration number if known, the country, and whether it is a company, a sole trader or a person. A name on the contract for a different business from the register entry is signal R1 (Stop); the same business with a different legal form or a near spelling is R15 (major, and the contract must be corrected before signing). A brand or trading name is not a legal entity; ask which one signs.
2. **The public register.** Status, age, filings, officers, address, charges (lookup protocol).
3. **Notices and judgments.** The official insolvency or notices source, and judgments where published, matched to the entity by name and number.
4. **Public reports.** Reviews and forums naming the business for non-payment. One or two angry posts weigh lightly; a consistent pattern from independent sources weighs heavily.
5. **The founder's own signals.** What they have seen: the payment terms asked for, how the contract has gone, pressure to start, contact details.
6. **Terms.** The unpaid work under the client's terms, then the lightest rung of the ladder that the verdict allows and the founder's limit needs.

## 2. Background

Lenders have long judged a borrower on five things: character (their record of paying), capacity (the cash to pay), capital (what they are worth), collateral (security) and conditions (the world around them). A service founder can see some of character and capacity from public records and their own dealings, and almost nothing of the rest. That is why every brief lists what could not be checked, and why terms do the heavy lifting: a deposit and stage payments protect the founder whatever the record would have shown.

## 3. Reading "no information"

- **No register entry** for a business that says it is incorporated, when the register was reachable: R1, a Stop. Check spelling and the legal name first; ask the founder for the name on the contract.
- **Register not reachable** (no web tools, a form, a login): not a finding. It goes under "could not check", and the entity counts as unverified.
- **A young company** has no filings to read. That is no history, not bad history (R6, minor, and not counted after 12 months).
- **Small or micro accounts** show little (R12, context).
- **A sole trader or individual** has no company register entry, and their personal records are never checked. The brief rests on the founder's signals and on terms; above the founder's limit the floor is rung 2.

## 4. The unpaid-work model

`scripts/exposure.py` answers: at the worst moment, how much finished work has the founder delivered that the client has not yet paid for, for how long, and how much cash is in by the end of the work?

- Work is delivered evenly across the project, or across each stage when the founder gives stage values.
- A deposit lands at signing, before work starts.
- A stage is invoiced when it completes (or on the founder's invoice day of the month after it completes) and paid the stated number of days later.
- Ongoing work: each month's work is delivered across that month, invoiced at its start (in advance) or end (in arrears), and paid the stated days later. Calendar months are used, so a short February shows up.
- Peak unpaid work is the largest gap between work delivered and cash received. "Time with unpaid work outstanding" runs from the first day of work until the client is fully paid; for ongoing work the brief shows the weeks above the founder's limit instead.

The closed form is checked in the self-test against a brute-force simulation of 200 random schedules.

## 5. How verdict and terms relate

The verdict sets the floor of the terms ladder; the founder's limit decides how far above the floor to go:

| Verdict | Floor | Then |
|---|---|---|
| Go | rung 0, the founder's usual terms | the lightest rung that keeps the peak within the limit; the brief says any tightening is about the limit, not the client |
| Caution | rung 2, a visible deposit and stages | the lightest rung from 2 up that fits |
| Stop | rung 4, a prepaid first phase, or decline | no credit at all |

If no rung up to 3 keeps the peak within the limit, the brief says so plainly, shows rung 3, and adds the large-exposure line. A founder's cap on deposits ("never more than 30% up front") skips rungs above it and says so. Sole traders and individuals above the limit start at rung 2.

## 6. Working defaults

All of these are working defaults, not market facts; the founder can change any of them, and none is shown as a benchmark: the 12-month age line; more than two officer changes in 12 months; three independent review reports for major; two failed linked entities for major; 60 days as "long terms"; deposit rungs of 30, 50 and 50 per cent; the stage splits; 14 and 7 days; the first phase at a quarter of the work; the founder's limit at a quarter of the fee when not given; the 8-week project length when not given; the 90-day re-check window; one page.
