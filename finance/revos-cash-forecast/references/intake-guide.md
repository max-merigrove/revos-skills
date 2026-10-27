# Intake guide: from the export and the founder's answers to the inputs file

Contents
1. The order of work
2. The readback
3. The five questions, and what each answer changes
4. The inputs file, field by field
5. Messy answers
6. Inputs that can flip the result

## 1. The order of work

1. `parse_bank_csv.py` on every attached export (one account). Add `--map` from memory when there is one.
2. `find_recurring.py` on what it wrote, with `--memory-json` on a return run. It writes the draft inputs file.
3. Put what the founder's message already settles into the draft (section 4) and run `forecast.py compute` on it: the provisional run.
4. One message to the founder: the answer so far from the provisional run (labelled "First read, before your answers", with the one or two facts that would change it), the checks against what they said, a direct answer to anything else they asked, the readback (section 2), then only the questions still open (section 3), with the defaults stated. Value first, questions last.
5. Edit the draft with the answers (section 4) and build. Never compute a figure yourself: write what the founder said ("4.2k", "30/10", "$1,870 with every payroll") and let the script read it.

No export at all (the founder will not or cannot share one): build the inputs by hand from what they say. Opening balance and date, each regular bill with amount, cadence and next date, everyday spending a week, regular clients, invoices, and the tax and payroll payments they list. Say in one line that a bank export would find the bills they forget.

## 2. The readback

Short, in the founder's words and currency, in the same message as the questions. A US example:

> I read your Chase export, July 1 to October 16: $33,163.74 in the account on October 16, and every row adds up to the bank's running balance. I've taken the account as US dollars and the dates as month first, as the file writes them.
> Regular out: Gusto net pay $9,850 on the 15th and again at month end, rent $3,200 on the 1st, health insurance $1,140, the SBA loan $610, a $3,000 owner draw on the 10th, $1,500 to savings on the 20th, and 4 software and phone bills.
> Regular in: Lumen Health $12,500 around the 6th, Northwind Capital $9,000 around the 18th. Everything else averages $3,161 a week.
> Looks like tax, so not in the forecast until you tell me: Gusto Tax $1,870.40, twice a month; $7,500 on September 15 marked "EST TAX Q3".
> Left out as a one-off: $2,350 at B&H Photo on August 19.
> What's wrong or missing?

Keep it to the lines that matter: balance, pay, the three or four largest bills, money in, tax-like payments seen, one-offs. Figures in the readback are copied from the script's printout. Round nothing. Never say what a tax-like payment is for or when the next one is due: show what the export holds and ask.

Rules for the readback:

- **A payee seen three or more times is never a one-off.** The finder groups by payee first, so pay runs with a different batch code each time, a card bill and a cloud bill whose amount moves are regular lines ("amount varies from $3,532 to $5,014, the middle figure is used"). Anything left under `REPEATING, NOT REGULAR ENOUGH TO PLACE` is named as repeating and asked about.
- **Name lines in plain words.** The finder strips bank codes (batch and trace numbers, `DES:`, `INDN:`, `ORIG:`, card prefixes); rename what is still unclear in the founder's words before showing it.
- **Tax-like payments: at most five lines**, one per payee ("Gusto tax: 12 payments, $6,641 to $7,828, twice a month").
- **The largest payer in the pattern.** When one client is 40 per cent or more of the usual pattern, say so and ask for that client's open invoices: once listed, the client comes out of the pattern.
- **Check the founder's claims against the bank.** The `last receipts` line prints the latest payments from the largest payers with their references (INV-1063, DEP, BAL). If the founder says a client still owes an invoice and a recent receipt may be that invoice, say so in the first reply and ask which invoice is open; never list money already in the bank as owed. `DEPOSITS SEEN` means work is booked and paid in part: ask whether a balance is still to come and what that work costs to deliver.
- **Currency.** When the layout suggests a currency and the founder's own writing fits it (a "$" and a US city on a Bank of America export), state it as a default ("in US dollars unless you say otherwise"); do not spend a question on it.

## 3. The five questions, and what each answer changes

At most five in the whole run (both founder turns together), counting every question mark, including the parser's ASK and the balance question. Each is one question, never a list of sub-questions. Ask only those still open after the export, memory and the founder's message, highest effect first. Use the multiple-choice tool when there is one (at most four per call, a free-text escape); otherwise one message with numbered options and "Answer like 1a, 3: ..., or say skip."

| # | Question (plain words) | Default when skipped | Changes |
|---|---|---|---|
| 1 | "Which tax, payroll tax or government payments fall due in the next 13 weeks, with the amount and date of each? Your accountant or payroll provider has the figures." | Nothing placed; the reading carries a `[NEED]` naming the tax-like payments seen, so the founder knows the forecast leaves them out | `known_outgoings`; remove any regular line it replaces |
| 2 | "Who owes you money and when is it due (open invoices, balances on booked work), and who usually pays late?" Quiet months only when `SEASONAL CHECK` printed and the founder has not already named them | The usual pattern carries money in, flat across the months | `invoices`, `client_late_days`, `payment_terms_days`, `receipts_pattern_week.months_off` |
| 3 | For booked work: "What does each booked job cost to deliver (suppliers, temps), and when do you pay it?" | Delivery costs stay out; a `[NEED]` says the forecast carries the income without its cost | `one_offs` or `recurring_out` with `linked_to`; `commitment` with `revenue_linked` |
| 4 | "Is one month of outgoings (X, worked out) the least you'd want in the account, or do you keep a different figure?" Ask only when budget remains; otherwise state the default | One month of outgoings | `floor` |
| 5 | "Are you weighing a hire or a big spend? If so, its full monthly cost and start date." | None | `commitment` (with `end` and `revenue_linked: true` when it delivers booked work) |

Currency, country and date order are asked only when neither the export nor the founder's writing settles them, and then count toward the five. A city settles the country; a city or country with one currency settles the currency, said as a default. The date order cannot be skipped when the parser asked; it decides every date. With no currency, figures print plain with a `[NEED]`; with no country, A4 paper.

When budget is tight, keep 1 and 2, then 3, and state the default for 4 and 5 instead of asking.

Say the defaults out loud in one line: "Until you say otherwise I'll treat a bad quarter as money in 20% lower and 15 days later, keep your $1,500 monthly transfer to savings in, and leave the B&H Photo payment out unless it will happen again. Tax and payroll payments go in only as you list them."

## 4. The inputs file, field by field

| Field | Fill with |
|---|---|
| `business` | The founder's business name (or a short description) |
| `currency` | A three-letter code (USD, SGD, AUD, GBP, EUR...) from the export, the founder's writing or their answer |
| `date_order` | `day-first` or `month-first`, from the export, a typed date that reads only one way, memory or the founder's answer. Left empty, the founder's `country` decides it (month first where that country writes it so) |
| `country` | Two-letter code (US, ZA, SG, GB, DE, IN...) from the founder's own words (a city, "we're in Joburg") or their answer. Sets the paper size (Letter or A4) and, when nothing else has, the date order. Never taken from their spelling |
| `decimal_style` | `dot` (1,234.50) or `comma` (1.234,50), only when the founder answered the one question a `STOP: ... reads two ways` asked. Otherwise it is read from what they typed, then from the export |
| `number_style` | From the export (`group`, `decimal`). The founder's own typing overrides it, so figures are written back the way they write them (R729 891, 1.200,50 €) |
| `asked_about` | Any month the founder asked about ("December", "through Jan"). The reading says plainly when that month runs past the 13 weeks |
| `week_labels` | `"date first"` when the founder wants "the week from 21 Nov 2026 (week 6)" rather than "week 6 (from 21 Nov 2026)"; saved as a learning |
| `provisional_tax`, `without_payer` | First read only (the build refuses both): repeat a tax-like payee at the bank's last amount until the founder gives the figure; show the pattern without the largest payer |
| `moves_first` | Lines the founder wants as moves first, in their words (`["WA excise"]`); those moves are kept and listed first |
| `moves_on_top` | `true` when the founder wants the moves above the summary on the one-page reading |
| `confirmed` | Labels of figures the founder confirmed after a plausibility stop ("the invoice from Khumalo Holdings") |
| `opening` | From the parser: `balance`, `date`, `source`. With no balance in the export: the founder's figure, its date, and `source: "you said, <date>"` |
| `floor` | `{"mode": "one_month"}` (default), `{"mode": "figure", "value": "25k"}`, or `{"mode": "weeks", "value": 6}` |
| `known_outgoings` | Each payment the founder listed: `label` in their words ("GST", "Payroll taxes", "Q4 estimated tax", "CPF"), `kind` (tax, payroll tax, government or other), `amount` as given, then either `date`, `dates` (a list), or `cadence` plus `next_date` (and optional `until`); `source` names who gave the figure ("your accountant", "your payroll provider", "you"). Twice-monthly payments are two monthly entries with the same label |
| `recurring_out` | The draft's list, corrected (a steady cost of booked work gets `linked_to`, `next_date` and `until`, and is then never held and left out of the safety line): rename `label` to the founder's words ("Rent", "Payroll: Jas"), fix `category`, set `keep: false` for anything that has stopped, remove any line the founder says is a tax or payroll payment (it lives in `known_outgoings` now), add bills the export missed (amount, cadence, `next_date`) |
| `everyday_spending_week`, `owner_pay_irregular_week` | From the draft; change only when the founder says their spending has changed |
| `recurring_in` | The draft's regular clients, corrected; `until` for a client who is leaving |
| `receipts_pattern_week` | From the draft. `use: false` when the founder says the listed invoices are everything coming in. `months_off`: the months the founder calls quiet (`["Jan", "Feb"]`), no pattern then; `month_factor`: a share the founder gives for a month (`{"Dec": "50%"}`). `payers` and `exclude` come from the finder: any payer matching a client whose invoices are listed (or saved as invoiced) is taken out of the pattern by the script, never by hand |
| `invoices` | Each: `client`, `amount` (what will land in the bank), `due` (or `issued` plus `terms_days`), optional `late_days`. Only invoices the founder gave, with their amounts; never one inferred from past payments |
| `client_late_days` | `{"Brightline Foods": 14}` from what the founder says or memory |
| `payment_terms_days` | The founder's usual terms when they list invoices; else the 30-day default |
| `instalments` | Each plan: `client`, `amount` per instalment, `dates` (or `first` and `count`, monthly) |
| `one_offs` | Each: `label`, `amount`, `date`, `direction` in or out, `certain: true` only for money already agreed (a loan drawdown), `linked_to` the booked job or invoice it serves (a supplier payment for an event). A one-off whose label names an invoiced client is linked automatically. Linked payments are never offered as a move to hold |
| `commitment` | `kind` hire or spend, `label`, `monthly_cost` (the full monthly cost, the founder's or accountant's figure), `one_off`, `start`, optional `end`, optional `payday`, `source`. `revenue_linked: true` when it is needed to deliver work already booked (temps for booked events): it goes in as a cost, not a choice to test |
| `stress` | Leave as the defaults unless the founder has approved different figures (a saved learning) |

## 5. Messy answers

Write them as given; the scripts read them through `scripts/locale_numbers.py`: "4.2k", "$4,200", "S$1,250.50", "4,200 AUD", "R412 000", "about R41k", "1.200,50 €", "₹2.4 lakh", "450万", "about 4200", "~62k", "(450)", "450 DR", "30/10" or "10/30" (in the founder's date order), "30 Oct", "Oct 30", "next Friday", "in 2 weeks", "end of November", "the 15th", "a month". A date with no year is the next one on or after today. A range ("4 to 5k") is not an amount: ask, or use the founder's own lower figure and say so. A figure that reads two ways ("12.500" from a founder who has not shown which mark they use for decimals) stops with one question; set `decimal_style` from the answer. A figure in another currency than the account's stops: this forecast never converts.

A figure given per person or per item ("$1,500 each for 4 staff") goes in as that many entries of the figure given, with the same label, never multiplied by you. A lump the founder gives for several booked jobs ("suppliers about R640k, paid 7 days before each event") is not split by you. Ask for the cost per job inside question 3, or place the lump on the one date the founder gives. Payday versus debit day: when the export shows pay leaving a day or two before the payday the founder names, the export's day is the cash day; use it and say so. "Monthly-ish" is monthly. "With every payroll" means the payroll's own dates. A payday "last working day" is the founder's choice to make: ask, or use the last calendar day and say so.

## 6. Inputs that can flip the result

Make sure each is asked or defaulted out loud:

- **The opening balance and its date.** Stale or missing, every week is wrong.
- **The tax and payroll payments the founder lists.** Usually the largest single payments; a skipped one is a `[NEED]` in the reading, never a guess.
- **Who pays late.** One large invoice 21 days late moves a breach week.
- **Owner pay and transfers to savings.** Founders forget they are cash out; the readback names them.
- **One-offs that will recur** (annual insurance, a software renewal, a van service).
- **Whether listed invoices are everything coming in**, or the usual pattern continues alongside them.
- **The commitment's real monthly cost**, all in, from the founder or accountant.
- **The date order**, when the export cannot show it: one wrong reading moves every date the founder typed.
