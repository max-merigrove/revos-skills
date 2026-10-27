# Method

How the skill turns a list of overdue invoices into a chase plan per client: who to chase first, which message to send today, the dated messages after it, a payment plan offer, the escalation ladder, and terms that make the next invoice easier to collect.

Contents: 1 What this skill does and does not do. 2 The inputs that can flip the plan. 3 Due dates. 4 Stages and tiers. 5 Payment plans. 6 Late fees and interest (only from the founder's contract). 7 The escalation ladder. 8 Prevention terms. 9 Only collected cash counts. 10 Defaults said out loud. 11 Reading figures and stopping on odd ones.

## 1. What this skill does and does not do

It does: commercial chasing. Dates, amounts, order of work, the words, a plan the client can say yes to, and terms for next time. All arithmetic is plain arithmetic on figures the founder gives.

It does not: say what any law allows, requires or entitles; work out interest, fees or compensation from any statute or published rate; write a letter before action, a demand letter, a court threat or any court step; name a country's courts, regulators or tax bodies; compute or advise on tax. Where the founder needs those, the output names who to ask: their lawyer for contracts and recovery, their accountant for tax.

## 2. The inputs that can flip the plan

Each is asked, read from what the founder pasted, or defaulted out loud before computing.

| Input | Why it changes the plan | Default if skipped |
|---|---|---|
| Country, currency and number style | Every figure and date in every message, and the page size | Country from where they are (never from spelling); currency from a symbol that names one or from what they say; number style read once from their figures. Otherwise asked once. Never assumed |
| Already chased? | Where the sequence starts, and the dates later messages cite | Nothing sent yet, said out loud |
| Due date or terms per invoice | Sets days late, and so the stage | The founder's usual terms; if none, 30 days from the invoice date, flagged as a working assumption |
| How much each client matters | Sets the opening stage, the gap to the final notice, and whether any contract late fee is waived as goodwill | Normal |
| Does their contract set a late fee or interest? | The only route to any late fee or interest in a message | No: no fee, no interest, never mentioned |
| Disputed (all or part) or part paid | A fully disputed invoice gets one message to settle it and nothing escalates. A part dispute holds only that part: the rest is chased as normal and the first message offers to settle the disputed part. Part payments reduce what is owed | Neither |
| What they will do after the final notice | The one step the final notice names | Take advice on recovering the full amount |
| Still doing work for the client | Whether "stop work" is a real option | Unknown: offered as an option |
| Private individual or business | Tone ("Dear Mrs Okafor") and a narrower final step | Business, unless the paste says otherwise |

## 3. Due dates

In this order, per invoice:

1. A due date written on the invoice: use it.
2. Terms (on the invoice, for that client, or the founder's usual terms) from the invoice date: "30 days", "net 30", "14d", "2 weeks", "a month", "end of month", "30 days EOM", "end of the following month", "on receipt".
3. Nothing given: 30 days from the invoice date, said out loud and flagged in the plan's "Check these" list.

Dates typed as numbers follow the founder's date order. US founders write 3/8 for March 8; most others mean 3 August. If the order is unknown and the date could be either, the script asks rather than guessing.

## 4. Stages and tiers

Four messages. Every message names the invoice, the amount, the due date and one next step. Wording by stage: `references/chaser-stages.md`.

| Stage | Purpose | Keep at all costs | Normal | Always pays late |
|---|---|---|---|---|
| 1 Reminder | Assume it slipped; ask for a payment date | From day 1 late | From day 1 | Skipped |
| 2 Firm reminder | A date to pay by; ask what is holding it up | From day 14 | From day 14 | From day 1 |
| 3 Call and payment plan | Offer a call and a plan; add a contract late fee where the founder has one | From day 30: a call, with any contract fee waived if paid by the date | From day 30 | From day 14 |
| 4 Final notice | The total, a date, and the one step the founder will take | From day 60 | From day 45 | From day 30 |

Rules:

- One message per client, covering all their late invoices; the stage follows the oldest.
- The first message is never the final notice: at most stage 2 (stage 3 for a client who always pays late), however late the invoice. A client who has asked to pay in parts gets the stage 3 plan offer first.
- A week after a reminder, and never before the last pay-by date has passed, before the next stage.
- However late the invoice, stages are spaced from the first message actually sent, not from lateness: at least 14 days between messages for a client they want to keep (7 for the others), and the final notice at least 28 days after the first message for a client they want to keep (14 for the others). A final notice that names a lawyer or a collections service for a client they want to keep, with work still going on, is flagged for the founder to confirm.
- Every later message names the dates of the earlier ones, whether the founder sent them before this run or they are earlier messages in this plan.
- The bank details line goes in the first message and the final notice, not every message.
- Pay-by date: 7 days after sending. Send and pay-by dates move off the founder's days off (Saturday and Sunday unless they say otherwise) and any holidays they list. No country's holiday calendar is built in: when the founder gives none, the plan says so and lists its dates in the next 8 weeks for them to check.
- Chase order: clients with a message due today (including a dispute to settle) first, then by the amount owed, then by days late. With one client, there is no "first".

## 5. Payment plans

Every stage 3 message offers a plan, because a client who cannot pay in one go is the commonest reason a chase stalls.

- Default: 3 instalments, monthly, the first on the pay-by date. The founder can change the number (1 to 12) and the rhythm (weekly, fortnightly, monthly).
- Instalments rounded to the cent (whole units for currencies without cents, such as yen); the last takes the difference so the plan adds up exactly ($3,200.00 in 3 is $1,066.67, $1,066.67, $1,066.66). Dates move off days off.
- The founder can set a smallest amount for a plan (`plan.min_amount`); below it, stage 3 offers a call and a date, no plan.
- What the plan covers: the amount owed; or, where a contract late fee is being added, the total in that message. While the client keeps to the plan, nothing further is added. That is the founder's concession, said in the message.
- A late fee notice and a final notice say "if [total] is paid by [date], I'll add nothing further", so the figure asked for is the figure that settles it.
- Founder note: confirm the dates by email the same day and stop the chase while they keep to it.

## 6. Late fees and interest (only from the founder's contract)

The skill never decides whether a late fee or interest can be charged and never says what any law allows. It only applies what the founder's own contract states, as plain arithmetic:

- A rate: "1.5% a month" is 18% a year; "10% a year" is 10%; "0.05% a day" is 18.25% a year. Simple interest on the unpaid amount, worked out daily over 365 days, from the day after the due date (or after the grace days the clause gives). Part payments reduce the amount from the day after they land.
- A one-off fee: a fixed amount, or a percentage of the invoice, once per invoice.
- A rate tied to a published rate ("4% over base", "prime plus 2", "SOFR + 3"): the skill does not look up any published rate. It asks "what total yearly rate should I use? Ask your accountant or bank", and stores the answer as founder supplied.
- A rate over 100% a year (often a month rate typed as a day rate) stops the run with a question until the founder confirms it.
- Interest and fees are worked only on the undisputed part of an invoice.
- A bare "5%" with no period: ask once whether it is a one-off fee, a month or a year.
- No clause: no fee, no interest, and the words do not appear in any message. The prevention terms offer a placeholder for next time.
- Every figure carries its working in the plan and one line: check with your lawyer that your clause applies this way.

## 7. The escalation ladder

Per client, dated: reminder, firm reminder, call and payment plan, final notice. Then two rungs that are the founder's decisions, never messages this skill writes:

- **Stop work.** Only if work is still going on, and only if their agreement allows it. Shown from the final notice's pay-by date.
- **Hand to a collections service or lawyer.** Named as an option to take advice on. The service or lawyer says what fits where the founder and client are, what it costs and what they need.

The final notice names one of these only when the founder has chosen it and will carry it out. Default: "take advice on recovering the full amount". For a private individual the ladder ends at "take advice on recovering it" (no collections rung), the final step is taking advice or pausing work, and the plan carries one line, whatever the stage, that chasing individuals has its own rules in many places.

## 8. Prevention terms

The plan ends with drafts for future work, each marked "check with your lawyer before using":

- Deposit: default 50% before work starts, balance on delivery, with the example worked on the founder's typical price (or a middle-sized invoice from the list).
- Milestone billing: default 40/30/30 for larger projects, with the same example.
- Card or account on file: monthly work taken automatically on the first working day of the month, in advance.
- Late fee or interest: the founder's existing clause kept as it is; otherwise a `[NEED]` placeholder. The skill never suggests a rate.
- Invoice footer with the due date as a date and a bank details line.
- One neutral line: enter prices before any sales tax (VAT, GST or similar); ask your accountant whether you need to charge it.

## 9. Only collected cash counts

An invoice is open until the money is in the founder's account. A promise, a remittance email or "it's in the next payment run" does not close it. On a return run, ask what has landed, not what was promised. Bank details are confirmed by voice: every message says the founder's bank details have not changed and to call before paying if told otherwise (the founder can switch this line off).

## 10. Defaults said out loud

Say these in one line before computing, and put any that were used in the plan's "Check these" list:

"I'll use your invoice due dates (or 30 days where there are none), treat every client as normal and nothing as chased yet unless you say otherwise, keep dates off Saturdays and Sundays, offer a 3-part monthly plan at the call stage, and add no late fee unless your contract sets one. I have not allowed for public holidays; tell me any in the next 8 weeks."

## 11. Reading figures and stopping on odd ones

Every figure, percentage, duration and set of days the founder types is read by `scripts/locale_numbers.py` in their own number style, detected once from what they pasted. A figure that reads two ways (12.500) is one question; one that cannot be read is asked again. Figures go back to the founder in their style (12.500,00 € to a founder who writes that way).

Before building, headline figures that look wrong stop the run with a plain question rather than a plan: an amount under one unit of currency, a contract rate over 100% a year, an invoice dated over three years ago, a late fee larger than the invoice. If the founder says the figure is right, it goes in `confirmed` and the run goes on.
