# Rubric: what exceptional looks like

Score the plan before delivery. Every criterion must pass. If one fails, rework the output; do not caveat it.

| # | Criterion | Pass when |
|---|---|---|
| 1 | Right locale, nothing assumed | Currency, number style and spelling come from the founder, and date order and page size from their country (never their spelling), read from the paste or asked once; every date and figure in every message is in their style; no country's law, institution, rate or holiday calendar appears anywhere |
| 2 | Due dates and days late right | Each due date is the invoice's date, the founder's terms applied, or 30 days flagged as a working assumption; days late and pay-by dates come from `chase_plan.py`; dates avoid the founder's days off |
| 3 | Staged by importance and lateness | The send-now stage fits the tier and days late (first message never the final notice; a client who always pays late skips the reminder); later stages wait past the previous pay-by date and are spaced from the first message, not compressed by lateness; later messages name the earlier dates; a chase order names who to chase first; only the disputed part of an invoice waits |
| 4 | Messages that get paid without burning the client | Each names the invoice, amount, due date and one next step; firm and warm; no threat, legal step, credit report or "final" before the final notice; `check_copy.py --chasers` prints 0 problems |
| 5 | A payment plan they can say yes to | Stage 3 offers a plan with every instalment and date, summing exactly to the amount offered (or a call only, below the founder's plan minimum); a figure asked for is the figure that settles it |
| 6 | Late fee only from the founder's contract | A late fee or interest appears only where the founder's own contract states it, from their stated rate or fee in plain arithmetic, with the working and "check with your lawyer"; with no clause, the words never appear in a message; nothing says what any law allows |
| 7 | Escalation ladder with the founder in charge | Each client's ladder shows the dated messages, then "stop work" and "hand to a collections service or lawyer" as options to take advice on; the final notice names only the one step the founder chose |
| 8 | Prevention terms marked as drafts | Deposit, milestones, card on file and late fee drafts carry "check with your lawyer before using", worked examples are plain arithmetic, no late fee rate is suggested, and the sales tax line is neutral |
| 9 | Sounds like the founder, usable today | The send-now messages read as the founder wrote them (their greeting, sign-off, length, English) and can be sent after filling any `[NEED]` |

Bar for every run: the first reply gives value (an answer to their question, the provisional chase order, today's message) before any question; the founder's side questions are answered usefully within scope; nothing is stated as the founder's that they did not give; and the chat reply carries the key figures without the file.

Fresh-eyes questions for the review pass:
- Would a good client be offended by the send-now message? If yes, the tier or the wording is wrong.
- Is the amount impossible to miss? It should be in the subject line or the first two sentences.
- Does anything sound like a lawyer wrote it, or claim to know what a law allows? Cut it.
- Could the client argue with a figure? Every figure has its working in the plan.
