# Wording

The client-facing words: a proposal paragraph, a reply to what the client actually asked for (long days, payment at the end, billing in arrears), a reply to a refused deposit, and a line asking for the contract name to be corrected when it differs from the register. `brief.py drafts` writes them with every figure filled in; Claude then puts them in the founder's voice.

## Rules

1. Terms are how the founder works with every new client of this size, never a reaction to this client.
2. Never mention the check, the register, credit, risk, trust or reviews. If the client asks "have you checked us out?", answer honestly (below).
3. No apology ("sorry", "I'm afraid", "unfortunately") and no accusation.
4. Every concession trades something visible: shorter days for a smaller deposit, a fixed start date for the first payment.
5. Keep every figure, percentage and day count exactly as the draft has it. `check_copy.py --wording` refuses any figure the scripts did not produce.
6. Use the founder's words: their name for the stages ("design sign-off", "launch"), their greeting and sign-off, their English.
7. No interest, late fees, legal steps or "the law says".

## Voices

- **Plain:** short sentences, the facts in order. "For projects of this size I work in stages: 50% (7.000 €) when we sign, which books your start date, then ..."
- **Warm:** the same terms framed as looking after both sides. "For projects of this size I like to work in stages, so neither of us is ever carrying too much: ..."
- **Brisk:** a terms line. "Terms: 50% (7.000 €) on signing to book the start date, then ..."

Pick the voice from the founder's own emails (or memory). Warm for a first contact unless they write briskly.

## The replies

- **Long terms with payment at the end**, with a concession the script found within the limit: "60 days with everything at the end doesn't work for me on work this size. I can do 30 days on each invoice, as long as the 7.000 € deposit is paid when we sign."
- **Without a concession:** "... What I can do is fix your start date the day the first payment lands, and keep each invoice small by splitting the work into stages."
- **Refused deposit**, with a concession: "I start every new project once the first payment is in; it's what holds your slot. If 7.000 € up front is a stretch, I can take 4.200 € now and add the difference to the first stage payment."
- **Ongoing work, asked for long days** ("net 90"), with a concession the script found within the limit: "90 days to pay doesn't work for me on an engagement this size. I can do 30 days on each invoice, as long as each month is invoiced at its start."
- **Contract names a different legal form:** "One small thing before we sign: the draft names Brauwerk Digital UG (haftungsbeschränkt). Could you have it changed to Brauwerk Digital GmbH, HRB 48213, so it matches your company's registered details?"
- **Ongoing work, asked to bill in arrears:** "Invoicing at the end of the month doesn't work for me on an engagement this size. What I can do is keep the 30-day window to pay, so the timing on your side barely changes."
- **Stop, prepaid first phase:** "For a first project together I start with a short first phase, about a quarter of the work, paid in full before it starts (5.500 €). Once that is done we can plan the rest together."
- **Stop, declining:** "Thank you for thinking of me for this. I'm not able to take it on at the moment, and I wish you well with it."

## "Have you checked us out?" (chat only, when the founder asks what to say)

"Yes, I look up every new business I work with on the public register, the same way I'd expect a client to look me up. It doesn't change how much I'm looking forward to the work." Honest, short, and never used unless the client asks.
