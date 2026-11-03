# Payment terms wording

`terms_block.py` prints the wording for chat from the founder's own schedule, in up to three lengths so it fits any proposal or contract. It writes a one-page `Payment terms <Business>.docx` only when the founder asks for a page (`--out`):

1. **Two lines:** the schedule and when each invoice is due. "Payment: 30% to start, 40% at design sign-off and 30% when the site goes live. Each invoice is due within 14 days of its date."
2. **A paragraph:** the schedule, when each invoice is due, how to pay, and tax as supplied ("Prices are before GST, which is added to each invoice as shown"), only where the founder charges it.
3. **A paragraph with the late fee:** where the founder has a clause in their own terms (`agreed`, printed verbatim), or has decided on their own fee for future contracts and said it ("2.5% per month and we hand over to our attorneys": `new` with `clause` in their words, adding nothing). The chat then says it applies from the next contract, stays off invoices for work agreed before it existed, and should be checked with their lawyer for where they and their clients are. A founder who wants a fee but has no figure gets a `NEED:` line and a chat note.

Tax is named only for categories with a rate above 0, so a line with no tax never produces "Prices are before No sales tax".

The page is the founder's, ready to paste: it carries no notes to them and no gaps. What to agree, what is still missing and who to check with come out as `CHAT:` lines for the chat reply: agree the terms before the work starts and attach them to the proposal or contract; the late fee comes from their lawyer; deposit wording (refunds, cancellation, what it is called) is theirs to add; the wording is commercial and worth checking with their lawyer.

## Rules

- Only what the founder gave: shares, triggers, days, how they are paid, tax as supplied, their late fee clause. No invented due days, start dates, pause-work clauses, suspension rights or take-down threats.
- The triggers are the founder's words, written so they follow the share ("30% to start", "40% at design sign-off").
- A late fee figure is never suggested, and none is called standard. A founder who says "maybe 2%" or "is 1.5% standard?" has not decided; there is no late fee version yet and the chat says the figure and whether it can be charged come from their lawyer. A founder who says "put 2.5% a month on" has decided: their words go into the `new` version for future contracts.
- Deposit wording (refundable or not, cancellation) is the founder's: the chat names it as theirs to add; the page never carries a gap for it.

## Why terms come first

A late fee or a payment schedule that first appears on an invoice is one the client never agreed. Terms agreed before the work, then repeated on each invoice, are the ones that hold up in a conversation about payment.
