# Intake guide

Turning what the founder typed into `case.json`, without losing or inventing anything.

## 1. Read first, ask second

Read the whole message and everything pasted (emails, a contract, register text, notes, screenshots) before asking. Take every figure, date, name and term from it. Confirm in one line. Ask only for what is still missing and would change the verdict or a figure.

## 2. The founder block

- `country`: where the founder is (from what they say, their currency or address). It sets date order and page size. Never infer it from spelling. Unknown: the script asks once.
- `english`: from how they write (en-US, en-GB, en-AU, en-IN, en-CA ...). A founder writing in another language who asks for English: en-GB unless they say otherwise; mirror their language in chat if they keep writing in it.
- `currency` and `decimal`: from their figures. Set `decimal` to `comma` for `14.000 €`, `1.200,50` or `3.000 €` written by a founder in a decimal-comma language; leave it null when unsure and the script asks.
- `limit`: as typed ("3.000 €", "1 lakh", "10k", "a quarter"). Not given: leave null; the script uses a quarter of the fee and flags it.
- `usual_deposit`, `usual_days`, `usual_billing`: their usual terms, as typed.
- `voice`: plain, warm or brisk, from their own emails or memory.
- `date_samples`: any date they typed, so the brief writes dates their way (numeric with their separator, or words).

## 3. The client and the deal

- `client.contract_name`: the name exactly as the contract or proposal shows it, when the founder pasted one. `brief.py` compares it with `register.name_on_register`.
- `client.name`: the legal name if known; `entity_type`: company, sole_trader, person or unknown. "A guy called Dave who runs Mullins Landscaping" is a sole trader, and the brief names the business, never the person.
- `deal.kind`: project or retainer. Monthly billing over six months is a retainer: `fee` (the total) and `months`, or `monthly_fee`.
- `deal.weeks`: as typed ("rund 10 Wochen", "3 to 4 weeks", "six months"); null when unknown (8 assumed and flagged).
- `their_terms`: deposit, stages (`when`: "delivery", "halfway", "week 4"), days ("net 45", "60 Tage", "90 days after final delivery").
- `invoice_day`: when the founder invoices on a set day of the month ("invoice on the 5th").
- `start`: when work starts, if said; otherwise today, flagged.
- `stage_names`: the founder's own names for the milestones, in order, worded to read after "at" (["the concept", "the prototype", "acceptance"]), or with weeks ([{"name": "launch", "week": 10}]). The drafts and the terms table use them where they place cleanly; otherwise they fall back to week numbers.

## 4. Signals and the paste

- Register facts go in `register` exactly as the page shows them; `status` keeps the page's words ("aktiv", "Forfeited", "Active").
- A paste that is cut off or missing a block: leave that field null (filings, officers, date) and list anything else in `register.missing` ("Registration number (cut off)"). The script puts each under "could not check" with "not in the extract you pasted" and prints one NEED line: ask for the block once.
- The founder's observations go in `founder_signals` by meaning (`start_before_contract`, `slow_to_sign`, `refused_deposit` and the rest in `signals.md`), summarised in a few plain words. Long payment terms come from `their_terms`; never add them as a signal. A CHECK SIGNAL line after compute means an id does not fit its words: fix it. Never paste a client's message, email address or phone number into the case file: the brief may be shared.
- A claim the client made ("we are 8 years in business", "we rebranded in March") goes in `unverified` as `{"claim": "..."}`. When the register in hand contradicts it, add `"register_shows": "formed on 09/22/2025"`: it becomes R14, a verified minor signal, instead of a question.
- Every pasted note goes in `pasted_notes` so the script can report any line addressed to an AI.

## 5. What does not add up (say it early)

- A name on the contract that differs from the register entry, or a brand name with no legal suffix.
- A rebrand date that does not match the register's formation date (a new entity, not a renamed one, may carry none of the old name's record).
- Payment terms quoted two ways ("net 45" and "on completion").
- A start date before the contract is signed.
- A fee and a scope that do not fit, or a total that does not match its parts.
- A date that reads two ways (03/04/2025) with no country to settle it: show both readings.

## 6. Questions, when needed (at most five, two turns)

1. Who signs: "What's the exact name on the contract, and is it a company, a sole trader or a person? Default: the name you gave, as a company."
2. The deal: "Roughly how many weeks does the work run? Default: 8."
3. The limit: "What's the most unpaid work you could carry for this client without it hurting? Default: a quarter of the fee."
4. Usual terms: "What do you normally ask of new clients, deposit and days to pay? Default: 30% up front, 14 days."
5. Anything noticed: "Anything that made you pause: slow replies, pressure to start, odd contact details? Default: nothing."
