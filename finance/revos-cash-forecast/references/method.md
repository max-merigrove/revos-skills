# Method: the 13-week cash forecast

Contents
1. What the forecast answers
2. The opening balance
3. Money in: when cash actually arrives
4. Money out: bills, pay, the payments the founder lists, and everyday spending
5. The safety line
6. The bad quarter (stress case)
7. Reading the result: breach week, lowest point, runway
8. The commitment test
9. The three moves
10. How often to re-run
11. How the forecast learns
12. Working defaults
13. The founder's currency, dates and English
14. What this method does not do

All arithmetic runs in `scripts/forecast.py`. Never add, subtract or round a figure in prose; copy it from the script. The workbook carries the same calculations as live formulas, and `evals/verify_workbook.py` proves they agree.

## 1. What the forecast answers

One question, in cash: in which week, if any, does the balance in this account fall below the line the founder needs to keep, in a normal quarter and in a bad one? It forecasts week by week for 13 weeks, because monthly blocks hide the week a large tax payment and the payroll land together. Week 1 starts the day after the opening balance date; every week is seven days.

The commonest failure it fixes: counting a sale as cash in the week it closes. Cash arrives when the client pays, which is the due date plus however late that client usually is.

## 2. The opening balance

The forecast opens on the last balance in the bank export, with its date, and says so ("last balance in the export, 16 October 2026"). It never opens on an estimate when the export carries a balance.

- No running balance, but a ledger or closing balance printed above the header (DBS, OCBC and others): that figure, dated at the export's last transaction, with a note that rows cannot be checked against it. An available balance is never used: it nets off holds.
- No balance anywhere (Barclays, Wells Fargo, Mercury, many others): ask the founder for the balance on the export's last date, or today's balance with today's date. Never derive it from a sum of transactions.
- Pending rows are not in the bank's balance and are left out. If a pending payment will clear, it clears inside week 1 in reality; the founder can add it as a known date.
- An export more than 10 days old is flagged: anything paid since is not in the opening balance.

Every week then asserts closing = opening + money in less money out, checked against the individual receipts and payments, and the next week opens on that closing balance.

## 3. Money in: when cash actually arrives

Four sources, each on its own line:

| Source | Normal quarter | From |
|---|---|---|
| Regular clients (retainers, subscriptions) | On their usual day each month, plus their usual lateness | Payments that repeat in the export at a steady amount |
| Invoices the founder lists | Due date plus that client's usual lateness (0 days unless the founder or memory says otherwise). An overdue invoice lands in week 1 | The founder: client, amount, due date. The amount is what will land in the bank |
| Payment plans | Each instalment on its date | The founder |
| The usual pattern of other receipts | The weekly average of everything else that came in over the export, from week 1 when no invoices are listed; when invoices are listed, from the end of the usual payment terms (30 days unless the founder says), because the listed invoices already cover the weeks before new work is paid | The export |

The pattern leaves out transfers from the founder's own accounts, loans and tax refunds. When one payer makes up 40 per cent or more of the pattern, the readback says so: one late payment moves the whole line.

**No client is counted twice.** A client whose invoices the founder lists is taken out of the usual pattern (its share of the export's receipts, divided by the export's weeks) and out of the regular clients; the reading says "without Northwind Health, whose money in comes from the invoices listed". Clients whose invoices were listed before are remembered and kept out on the next run, with a `[NEED]` until their open invoices are listed.

**Seasons.** The pattern is one weekly average of the months the export covers, and the reading names them ("the average of April to October 2026"). When money in moves by more than half from one month to the next, the founder is asked whether income is seasonal and which months are quiet: the pattern is left out in those months (`months_off`), or set to the share the founder gives (`month_factor`). The skill never invents a seasonal shape.

## 4. Money out: bills, pay, the payments the founder lists, and everyday spending

- **Regular payments** found in the export (rent, software, insurance, loans and leases, net pay, pension contributions, the accountant, transfers to savings) on their next date and cadence. The founder corrects the list rather than recalling it. A payment that has not appeared for longer than its cycle is listed as possibly stopped and left out unless the founder says it continues.
  - Payments are grouped by payee first, with bank codes removed (batch and trace numbers, anything after `ID:` or `INDN:`, a wire's sender from `ORIG:`, card prefixes), so one payee is one group however the bank numbers each payment.
  - A payee paid twice a month around two days (pay on the 15th and the last day, debited a day or two earlier) becomes two monthly lines on the days the money actually left.
  - A payee on one rhythm whose amount moves (a card bill, a cloud bill) is one regular line: the latest amount when the spread is 15 per cent or less, the middle figure when it is wider, said in the line's source.
  - A payee seen three or more times is never a one-off: if it is not regular enough to place, it is shown as repeating and asked about.
- **Pay**: net pay on payday, as its own line per person or one payroll line, at the amounts the export shows.
- **Tax, payroll taxes and other government payments: founder supplied, never derived.** The skill holds no country's tax calendar, rates or rules and never works out a figure or a date. The founder lists each one due in the next 13 weeks: what it is, the amount, and either its date or its rhythm (monthly on the 22nd, with every payroll, quarterly from 31 October). The figure comes from their accountant, bookkeeper or payroll provider, and the line carries "founder supplied" with who gave it. A listed payment with no amount is placed at zero and marked `[NEED]`; one with no date or rhythm is not placed and is marked `[NEED]`. Payments in the export that look like tax (`TAX-LIKE SEEN`) are shown to the founder to prompt the list; they are never projected on their own. If a tax payment was also found as an ordinary regular line (a payment with no telling words, such as a payroll provider's tax debit), the founder's listed version replaces it, so it is never counted twice.
- **Everyday spending**: the weekly average of every other payment out over the export, leaving out regular payments, tax-like payments, transfers to the founder's own accounts and one-offs (a single payment above 500 in the account's currency, or five times the typical payment).
- **Owner pay that is not regular** (irregular drawings, draws or dividends): its own weekly average line, so the founder can see it and change it.
- **Transfers to the founder's own savings or tax pot**: kept in the forecast as a line (the money does leave this account) and left out of the safety line. The readback says so; the founder may pause them.
- **One-offs**: listed for the founder, left out unless they say one will happen again inside the 13 weeks; then it goes in as a known date.

Dates are placed exactly as the founder gives them. The skill does not move a payment for weekends or public holidays, because it does not know the founder's calendar; if a date falls on a non-working day and the bank will take the money earlier, the founder gives the earlier date.

## 5. The safety line

The floor is the least the account should ever hold. Default: one month of outgoings (MRG-211: at least one month of total operating costs), worked out by the script from the forecast's own lines:

monthly outgoings = regular payments at their monthly equivalent + listed payments that come monthly or more often + everyday spending and irregular owner pay at 52/12 of a week

It leaves out costs tied to booked work (they are paid from that work's money in and swing with the season), listed payments that come quarterly, yearly or once (they are lumpy and placed on their dates), transfers to the founder's own accounts, one-offs and the commitment being tested. The founder can set a figure instead, or a number of weeks of outgoings. The reading states the line and its basis.

## 6. The bad quarter (stress case)

Same opening balance, same outgoings. Money in changes:

- Regular clients, invoices, the usual pattern and one-off receipts: 20 per cent lower and 15 days later (MRG-211: revenue less 20 per cent and debtor days extended by 15). A receipt pushed past week 13 drops out.
- Payment plan instalments: on their dates, with 10 per cent failing until the founder has six months of their own plan history (working default, marked for review).
- A receipt the founder marks as certain (a loan already agreed, a grant already paid): unchanged.

Outgoings do not move in the bad quarter. That is deliberate: suppliers, tax payments and payroll do not wait because a client did.

## 7. Reading the result: breach week, lowest point, runway

- **First breach week**: the first week whose closing balance is below the safety line, in each case. "No breach in 13 weeks" when none.
- **Lowest point**: the lowest closing balance and its week, in each case.
- **Bad-quarter runway**: the number of weeks before the bad quarter first crosses the line (a breach in week 4 is 3 weeks of runway; no breach is 13). The method asks for at least 8 (MRG-211). Runway is never quoted from the normal quarter.
- **Already below**: if the opening balance is under the line, the reading says so first.
- The headline names the week by number and start date and the largest payment leaving that week ("when payroll of 19,700 leaves").

## 8. The commitment test

A hire or a large spend is loaded from its start date with no extra money in while it beds in. A hire's cost is the founder's figure for its full monthly cost, including whatever employment costs apply where they are (from them, their accountant or payroll provider; never estimated), paid monthly on the business's payday (or the 28th), plus any one-off cost on the start date.

| Answer | When |
|---|---|
| Yes | With it loaded, the bad quarter stays above the safety line for all 13 weeks, and ends week 13 at least 8 weeks of the commitment's cost above the line (so it is still affordable for two months past what the forecast can see) |
| Not yet, and a later start date | The answer is no at the asked date, and a start date up to week 13 passes both tests. The earliest one is given (MRG-211: if the stress case fails only in later weeks, the answer is a later start date). The reading says to test again before committing, because the forecast cannot see past week 13 |
| Not yet | No start date inside the 13 weeks passes, or the bad quarter breaches the line even without it (then: fix the breach first) |

## 9. The three moves

Three dated moves, each tied to a named line in the workbook, chosen by rule:

When a case breaches (or the balance is already below the line):
1. Chase the largest overdue receipt, or ask a usually-late client to pay on time, for money due up to three weeks after the breach week (by a week before its due date, or today if overdue), naming the client and figure. A client who pays on time is not chased.
2. Hold the largest payment in the breach weeks that can wait, in this order: a transfer to the founder's own savings, then owner pay, then spending not tied to booked work (a one-off, software, another non-essential regular payment). Only when none of the first two is there and a tax or government payment the founder listed is larger than any spending: talk to whoever gave the figure at least 14 days before it is due. Never offered: pay, payroll taxes, a payment the founder tied to a booked job or invoice (`linked_to`), or a cost needed to deliver booked work (`revenue_linked`).
3. If a commitment was tested and is not a yes: move it to the later start date, or hold it. Otherwise the next of: asking a usually-late client to pay on time when their lateness pushes the money past the low week, another payment that can wait (a transfer to the founder's own account, owner pay, a one-off; never rent, pay or a bill that keeps the business running), money set aside for the nearest payment the founder listed, the largest single receipt to confirm, and only then the gap itself (how far the low sits under the line).

When nothing breaches:
1. Set aside the nearest listed payment a week before it leaves (or get its figure three weeks before, when the amount is a `[NEED]`).
2. Confirm the largest single receipt in the 13 weeks, or act on the commitment answer.
3. Re-run on the next date.

When the business is paid before or during the work (deposits, upfront payment), the collection move reads "collect the money for work in weeks N to M on time (invoices out, deposits and balances in)", never "send every invoice".

Each move carries a figure from the forecast and a named line. The three moves are listed in date order. The re-run date is printed on its own line and is never counted as one of the three, unless nothing else exists to do.

**The receipt that decides it.** The script also prints `DECIDES:`, only when it changes the answer: first, a late payer whose lateness moves the week (what a normal quarter looks like if it paid on its due date); otherwise the last date a large receipt can land before a normal quarter falls below the line (or, when the balance is already below, before the account is overdrawn). It is plain arithmetic on the forecast's own weeks, and it goes in the first reply, the reading and the chat. No move ever recommends borrowing, or says what an authority will or will not allow.

## 10. How often to re-run

Weekly while the bad quarter crosses the line inside 8 weeks, the normal quarter crosses it inside 4, the balance is already below the line, or the business runs payroll. Monthly otherwise, and before any new commitment. (MRG-211 sets weekly updates near the floor; the payroll and size thresholds are Merigrove working defaults.)

## 11. How the forecast learns

- **Client lateness**: "Alder pays 21 days late" becomes a saved habit; every future receipt from that client is placed 21 days after its due date.
- **The regular list**: corrections (rename, recategorise, ignore, one-off) are saved by the payment's match key and day (two lines with one payee, such as pay on the 15th and at month end, stay two rows), with the amount, rhythm and next date, so the next run applies them before showing the list.
- **Carrying the list forward**: a saved bill or client the new export does not show as regular (a one-month export sees most monthly bills once, or not at all) is carried forward with its saved rhythm and next date, at the amount this export shows when it appears once (the saved figure is kept when the two differ by more than 15 per cent, and the founder is asked). Its payments in the export are not counted again as everyday spending, one-offs or the pattern. It is dropped only when the founder says it stopped, or marked "may have stopped" when the export is longer than its cycle and never shows it.
- **The payments the founder listed**: saved with their amount, rhythm or date and who supplied them. The next run carries the rhythmic ones and the future-dated ones forward and asks only whether they changed.
- **The bank's layout, currency and date order**: the confirmed `--map` line, the currency and the date order are saved, so each is asked about once.
- **Forecast against actual**: each run saves its weekly forecast of money in and closing balance. The next run compares the money that actually arrived (from the new export) with what was forecast for the same weeks, and records the difference. After three such checks, if the middle shortfall is larger than 20 per cent, the script proposes a deeper bad-quarter cut as a learning for the founder to approve. It never changes the stress settings on its own.
- **Safety line**: a founder who wants six weeks rather than one month saves it once.

## 12. Working defaults

Every default is stated to the founder before the figures and listed on the Assumptions tab as a yellow cell.

| Default | Value | Source |
|---|---|---|
| Safety line | One month of outgoings | MRG-211 (cash floor: at least one month of total operating costs). Max to confirm for founders who are strangers to Merigrove |
| Bad quarter, receipts | 20 per cent lower | MRG-211 |
| Bad quarter, timing | 15 days later | MRG-211 (debtor days plus 15) |
| Payment plan failures in a bad quarter | 10 per cent | Merigrove working default, until six months of the founder's own history; Max to review |
| Bad-quarter runway asked for | 8 weeks | MRG-211. Max to confirm |
| Weekly re-run when near the line | inside 4 weeks (normal) or 8 weeks (bad quarter) | MRG-211 (proximity alert at 4 weeks); 8 weeks matches the runway minimum |
| Client lateness | 0 days unless known | Working default; the founder's own history replaces it |
| Payment terms on new work, when invoices are listed | 30 days | Working default |
| Commitment cushion | 8 weeks of its cost above the line at week 13 | Merigrove working default, matching the runway minimum; Max to review |
| One-off threshold | above 500 in the account's currency, or five times the typical payment | Working default for the readback only |
| New hire payday | the business's payroll day, else the 28th | Working default |
| Amount varies | Latest amount when the spread is 15 per cent or less; the middle figure when wider | Working default |
| Seasonal question | Money in moves by more than half from one month to the next | Working default; the founder decides the quiet months |
| A saved item missing from a new export | Carried forward unless the export is longer than its cycle plus 10 days | Working default |
| Plausibility stop | A typed figure below 1 unit; an invoice under a hundredth of a typical day's receipts, or over 50 times the largest day and 10 times the balance; a listed payment over a year of outgoings; a commitment over 10 times monthly outgoings; a safety line over two years of outgoings | Working default: each asks the founder one question, never changes the figure |

None of these is a statistic about other businesses, and none may be presented as one. None depends on a country.

## 13. The founder's currency, dates and English

- **Currency**: from the export (a currency column, a code in a header such as "Withdrawals (SGD)", codes or symbols in the cells, a balance line), from the founder's own writing ("4.2k AUD", "S$"), or from memory. A layout's usual currency (Chase in US dollars) is a labelled guess the readback confirms. Otherwise ask once. A bare "$" is never read as one country's dollar. With no currency confirmed, figures print without a sign and the gap is a `[NEED]`.
- **Date order**: read from the export (any day over 12 settles it; else the order that keeps the rows in sequence; else a layout's documented order). If none of those settles it, the parser asks once (`--dates`). Dates the founder types follow the same order; a typed date that reads only one way ("15/11") settles it. Output dates print as "16 October 2026" for a day-first founder and "October 16, 2026" for a month-first founder; week labels read "week 2 (from 24 Oct)" or "week 2 (from Oct 24)".
- **Working week and holidays**: the skill keeps none. Payments go on the dates the founder or the export shows.
- **Numbers**: every figure the founder types is read by `scripts/locale_numbers.py` (1,234.56, 1.234,56, 1 234,56, R412 000, ₹2.4 lakh, 450万), with the decimal style read once from what they typed (or the export) and one question when a figure reads two ways. Figures are written back the way the founder writes them: R729 891 to a founder who writes that way, 1.200,50 € to another. In the workbook, the spreadsheet app shows thousands and decimal marks in the viewer's own setting.
- **Paper and dates from the country**: the business's country (from what the founder says, or one question) sets Letter or A4 for the one-page reading and the workbook, and the date order when neither the export nor a typed date has. Never from the founder's spelling.
- **English**: the note and chat mirror the founder's own spelling and words; the script's fixed phrases avoid words that differ between British and American English.

## 14. What this method does not do

- It does not say why profit fails to become cash (pricing, terms, delivery). It names the week.
- It does not work out tax, sales tax or its reclaim, payroll taxes, employer or social charges, pension costs, interest, penalties or borrowing costs, and it does not say when any tax is due or what any law requires. Those come from the founder's accountant, payroll provider or lawyer.
- It does not recommend borrowing, an overdraft or invoice finance.
- It forecasts one bank account in one currency. Money in a second account or a savings pot is not counted unless the founder adds a transfer in as a known date.
- It is a planning tool, not financial, tax or legal advice.
