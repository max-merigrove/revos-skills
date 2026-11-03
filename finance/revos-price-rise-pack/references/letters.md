# The letters

`letters.py` writes every letter from the plan. This page is the standard they are held to, for when the founder asks for a change, or code cannot run and you write them by hand from `assets/letter-templates.md`.

## What every letter carries, in this order

1. **Subject:** "Your fee from 1 January 2027" (the founder's word for fee, and the date).
2. **Greeting:** "Hi Sarah," when the founder gave a contact name, otherwise "Hello,". Never "Dear valued client".
3. **The new fee and the date in the first three lines,** with today's fee beside it: "From 1 January 2027, your fee will be 2,150 a month, up from 1,800." Two steps: both fees and both dates in the same line.
4. **One reason, true and checkable,** from what the founder said (ranking in `method.md` section 8), and true for this client: the new-client price is set beside the client's own hours, and is never the reason for a fee above it. Never stacked: one reason is stronger than three. Written to the client ("you often send extra requests"), never about them ("they always send...").
5. **What stays the same:** the founder's own line if they gave one, otherwise "the work, the way we work together and how you are invoiced".
6. **The choice:** carry on with nothing to do (the new fee appears on the invoice dated the effective date), or reply to talk it through before the reply-by date (two weeks before the effective date, never sooner than a week after sending).
7. **One thank-you,** tied to a fact ("since 2021") and only when the founder gave it.
8. **The founder's sign-off.**

## What a letter never carries

An apology, "unfortunately", "small adjustment", "I hope you understand", "valued client", "reaching out", "going forward"; a cost or inflation reason without the founder's figure; "industry standard", "market rate" or "everyone is raising"; "effective immediately", a deadline to accept, "limited time" or "last chance"; a discount for nothing or a "loyalty discount" the founder did not choose and price; a third party to blame (a government, a regulator, a supplier) unless the founder gave the figure; legal wording on variation or termination; a backdated date. `check_copy.py --letters` enforces the list.

## Status

Each client page is marked **READY** or **HOLD** with the reason. HOLD when: the notice is a planning default; the send date is not confirmed; the tax status of the fees is unconfirmed; the fee to keep a client is unknown; the defined scope has no hours; a project client has no expected project count. A letter with a `[NEED]` in it is always HOLD.

## The reminder

About two weeks before each effective date, one line: "A reminder that from 1 January 2027 your fee is 2,150." The dates are in the How to send page.

## The silence follow-up

After five working days with no reply: "Hi Sarah, a quick check that my note of 2 November 2026 reached you: from 1 January 2027 your fee is 2,150. Reply if you would like to talk it through before then." No reply after that is a yes: the new fee goes on the invoice as the letter said.

## When the founder edits the wording

Keep the order above. A changed word that lands in a banned pattern is put back with one line on why. A learning such as "writes 'fee', not 'rate'" goes in `fee_word`; "leads with the scope, not the list price" goes in `reason_order`; "say 'our current rate', not the figure" goes in `new_client_line`; "write 2.750,00 €" is `money_decimals` 2; a sentence of their own for one client is that client's `reason`; "never offers the lock option" is honoured in the pushback replies. Rebuild; never hand-edit the built file and never edit the scripts.
