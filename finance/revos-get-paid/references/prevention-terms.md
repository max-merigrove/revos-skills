# Prevention terms: so the next invoice is easier to collect

The plan ends with drafts for future work. `chase_plan.py build` writes them with the founder's figures filled in. Every one is a draft to check with their lawyer before it goes into a contract, because what a contract can say differs by country and state. The skill does not say whether any term is enforceable.

## What the plan drafts

| Term | Default | Why it works | Founder can change |
|---|---|---|---|
| Deposit | 50% before work starts, balance on delivery | Work never starts on credit; the client is committed before the founder spends time | `prevention.deposit_pct` |
| Milestone billing | 40/30/30 for larger projects, each stage invoiced on its milestone, next stage starts once the last is paid | Caps how much is ever owed at once | `prevention.milestones` |
| Card or account on file | Monthly work taken automatically on the first working day of the month, in advance | The client has to act to stop paying, not to pay | `prevention.card_on_file` |
| Late fee or interest | Their existing clause kept; otherwise `[NEED]` | A fee the contract states is one they can apply next time | `prevention.late_fee` (their own wording) |
| Invoice footer | Due date as a date, terms in brackets, bank details line | A date is a fact; terms are an argument | |

Worked examples use the founder's typical price if they gave one, otherwise a middle-sized invoice from the list, and are plain arithmetic (for example 50% of $4,200.00 is $2,100.00 up front and $2,100.00 on delivery).

## Rules

- Never suggest a late fee or interest rate. If the founder wants one, the placeholder sends them to their lawyer, who can say what they may charge where they and their clients are.
- If their contract already sets one, keep it word for word and say it stays as it is.
- Prices for future work are shown before any sales tax, with the one neutral line: "Enter prices before any sales tax (VAT, GST or similar); ask your accountant whether you need to charge it."
- Diagnose first: if the founder already takes deposits or bills in stages, say so and offer only what they lack.
- A learning can change a default ("I take 30% deposits, never 50%"); the memory stores it and the next run uses it.
