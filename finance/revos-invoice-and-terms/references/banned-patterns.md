# Banned patterns

Each pattern: what to watch for, why it hurts, a before and an after. `scripts/check_copy.py` enforces them on the chat reply, the reminder and the terms wording; `verify_invoice.py` checks the invoice itself. The base list comes first.

## Base list

### Em and en dashes
- Watch for: long dashes as clause breaks.
- Why: the clearest tell of machine-written copy.
- Before: Payment is due in 14 days (by the 16th).
- After: Payment is due in 14 days, by Monday 16 November 2026.

### Contrast reveal
- Watch for: "It's not X, it's Y."
- Why: a formula readers discount.
- Before: It's not just an invoice, it's your cash flow.
- After: Invoice INV-0019 for EUR 2,564.70 is due Monday 16 November 2026.

### Filler words
- Watch for: unlock, elevate, leverage, seamless, robust, game-changer, delve.
- Why: they say nothing a competitor could not say.
- Before: A seamless way to get paid.
- After: Pay by bank transfer to IE29 AIBK 9311 5212 3456 78, quoting INV-0019.

### "More" as an intensifier
- Watch for: "more professional", "get paid more quickly" with no comparison.
- Why: unprovable.
- Before: Look more professional.
- After: Every total carries its currency code and the due date is a date.

### Announced honesty
- Watch for: "to be honest", "I mean", "let's be real".
- Why: implies the rest was not honest.

### Stock openers, exclamation marks, unproven superlatives
- Watch for: "In today's fast-paced world", "!", "world-class".
- Why: the reader stops trusting the next line.

## This skill's list

### Claims about the law
- Watch for: statutory, by law, under the law, required by law, legally entitled, legal backing, enforceable, mandatory, legislation, regulations.
- Why: the skill does not know the founder's law, and a wrong legal claim on an invoice is worse than none.
- Before: Late payment is subject to interest at the statutory rate under the 2012 Regulations, which makes it enforceable.
- After: (invoice) Payment due within 14 days of the invoice date, by Monday 16 November 2026. (chat) A late fee belongs in terms your client agrees before the work; the figure and whether you can charge it come from your lawyer.

### A late fee or interest the founder did not supply
- Watch for: "2% per month", "interest at", "per annum", "penalty", any fee figure not in their own terms.
- Why: an invented term, presented as theirs.
- Before: Late payments incur 2% per month (24% per annum).
- After: Late payment: [NEED: your late fee, from your lawyer].

### Threats and take-downs
- Watch for: legal action, take legal, court, debt collection, we reserve the right to suspend, take the site offline, suspend hosting.
- Why: they harden a client who may simply be stuck in a payment run, and the founder never chose them.
- Before: We reserve the right to suspend hosting or take the site offline.
- After: (nothing; the due date and how to pay do the work)

### Pressure words
- Watch for: pay immediately, ASAP, urgent, within 24 hours, final notice.
- Why: they read as panic and invite delay.
- Before: Please pay ASAP.
- After: Could you pay it by Monday 9 November 2026?

### Stock collection phrases
- Watch for: kindly, per my last email, friendly reminder, as discussed (with no reference), valued client, thank you for your continued support.
- Why: recognised as templates; some read as passive aggressive.
- Before: Just a friendly reminder, kindly settle at your earliest convenience.
- After: Invoice 118 for AUD 4,400.00 was due on 12 October 2026, 21 days ago.

### "Net 30" with no date
- Watch for: net 7, net 14, net 30 on its own.
- Why: "30 days" can run from the invoice date or the month end; a date cannot be misread.
- Before: Terms: net 30.
- After: Payment due within 30 days of the invoice date, by Wednesday, December 2, 2026.

### Agreeing with a tax belief
- Watch for: "You're correct about the VAT", "no GST applies to that".
- Why: the skill is not the founder's accountant.
- Before: You're correct: design services aren't taxable, so no sales tax applies.
- After: I've put no sales tax on the design work, as you said, marked as supplied by you. Confirm that with your accountant before you send it.

### Claiming a deliverable that does not exist
- Watch for: "Your invoice is ready" before the file is built and verified.
- Why: plain AI does this; the founder finds out when they look.
- After: "Invoice INV-0019 is built and its totals tie out: PDF and Word in your outputs folder."

### Placeholders that look like fields
- Watch for: [INSERT NUMBER], [INSERT DATE], [Client Name].
- Why: they get sent.
- After: the script fills every field it can; anything missing is `[NEED: what, and why]` and the invoice is DRAFT.
