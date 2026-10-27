# The five questions

Every asset is read for the same five questions. They are the questions a buyer silently answers before they will pay: if two of your assets answer them differently, the buyer cannot repeat what you do, and a referral cannot carry you.

| Key | Question | What counts as an answer | Weight |
|---|---|---|---|
| who | Who you serve | A named buyer, situation or trigger ("B2B SaaS founders still running marketing themselves", "your team is stretched") | 25 |
| what | What you do | The service or offer as the asset describes it ("we will manage your paid social accounts") | 25 |
| result | The result you promise | What the buyer ends up with or stops having to do ("so you can stop doing it yourself") | 20 |
| why | Why you over the alternatives | The reason to choose this business: proof, history, method, who does the work | 20 |
| next | What to do next | The call to action ("Book a free growth call", "DM me CMO") | 10 |

## Where to look in each asset

- **Website:** the hero line and the line under it answer who and what; the about section answers why; the last button answers next.
- **LinkedIn:** the headline usually answers who and what; the first two lines of the about section answer result; the last line answers next.
- **Proposal or deck:** the opening paragraph and "the challenge" answer who (the buyer as this proposal sees them); "our approach" or "what you get" answers what; the promise paragraph answers result. Proposals often never say why: that is a finding, not a gap to fill by guessing.
- **Onboarding email, invoice:** usually what and next. Silence on the rest is normal; it only costs a quarter of a pair.

## How to quote

- Quote the shortest line that answers the question, word for word from the clean copy, including the founder's typos and their own dashes. Two to 45 words.
- To skip words inside a line, use "..." and keep each piece exact.
- Never merge two lines into one quote and never tidy grammar. `verify_quotes.py` refuses anything not found.
- If the asset never answers, the cell is `null` ("not stated"). Do not infer an answer from tone.
- Placeholders such as `[client]` and `[fee]` stay in the quote; they show where data was removed.

## Grouping answers: the one judgement you make

Give answers that mean the same thing the same group letter. Test: if a buyer read both, would they describe the same business? Same meaning in different words is the same group ("founder-led SaaS companies" and "SaaS founders").

Then list compatible pairs, with a reason, where one answer is a narrower or broader form of the other ("B2B SaaS founders" sits inside "ambitious brands"). Compatible counts half. Everything else is a different answer and counts nothing.

**The overlap test.** If one asset's answer is named inside another asset's text (not just its quote), the pair is compatible: LinkedIn's "senior women in finance" sits beside the website's "first-time executives" when the same LinkedIn lists "first-time CEOs" among the clients. `score_consistency.py` prints CHECK OVERLAP where a quote's distinctive words ("first-time", "interior design") appear in the other asset; decide each one, it is a pointer, not a verdict. A shared word is not enough on its own: Hollow Oak's proposal says "interior design" and rules out building, the website says "interior design" and promises the whole renovation, so they stay different.

Be strict in both directions:

- Do not call two answers compatible to soften the score. "Paid social management" is not a narrower form of "growth strategy across paid, organic and email" when the website promises that nothing sits in a silo.
- Do not call two answers different because the words differ. "Book a call" and "Book a free 20-minute call" are the same answer.

Write the reason for every compatible pair; it is printed in the Word file so the founder can disagree with it.

## What is not scored

- **A proposal's next step.** A proposal asks the buyer to sign; a website asks them to book a call. That is the funnel working, not a contradiction, so client-facing assets are left out of "what to do next" automatically.
- **A deliberate difference.** If the founder says an asset is aimed at a different buyer on purpose (a recruitment page, a personal Instagram, a team offer someone else sells), leave it out of the questions they name, any of the five, with `skip` and their reason (`{"prop": {"questions": ["who", "what"], "reason": "the team offer Jordan sells"}}`), and say so in one line.
- **An edit the founder declines.** The question is still scored, but no edit is forced: `declined` with their reason, printed as "Left as is at your request".
- **A sent proposal.** It is a record. Its answers are scored as they stand; edits are written for the template the founder reuses. Where the recommended line targets a different buyer, its who and what are held for the decision (`declined`, `"by": "decision"`), and the decision names it.
- **Out of date or one-off assets.** Leave them out entirely and list them under `excluded` with the founder's reason.
