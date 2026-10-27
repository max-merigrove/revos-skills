# 13-Week Cash Forecast memory

Skill: revos-cash-forecast | Memory version: 1 | Updated: YYYY-MM-DD

Keep this file. Attach it next time (or leave it in your merigrove-memory folder, or your Claude Project) and the forecast picks up where you left off: your bank's layout, your regular bills, the payments you listed and how your clients pay. You can edit it by hand.

## Profile

| Field | Value | Source | Updated |
|---|---|---|---|
| Business | <name> | your answers and export | YYYY-MM-DD |
| Currency | <USD / SGD / AUD / GBP / EUR ...> | your answers and export | YYYY-MM-DD |
| Dates written | <day first / month first> | your answers and export | YYYY-MM-DD |
| Bank | <bank> | your answers and export | YYYY-MM-DD |
| Bank column map | <the MAP line the parser printed> | your answers and export | YYYY-MM-DD |
| Safety line | <one month of outgoings / N weeks of outgoings / a figure> | your answers and export | YYYY-MM-DD |
| Bad quarter: money in lower by | 20% | default | YYYY-MM-DD |
| Bad quarter: money in later by (days) | 15 | default | YYYY-MM-DD |
| Bad quarter: payment plan failures | 10% | default | YYYY-MM-DD |
| Country | <US / ZA / SG / GB ...: sets Letter or A4> | your answers and export | YYYY-MM-DD |
| Decimals written with | <a dot (1,234.50) / a comma (1.234,50)> | your answers and export | YYYY-MM-DD |
| Last forecast opened on | <YYYY-MM-DD> | your answers and export | YYYY-MM-DD |

## Regular items

| Label | Match | Category | Cadence | Amount | Day | Next date | Status | Source |
|---|---|---|---|---|---|---|---|---|
| <Rent> | <office space> | <rent> | <monthly> | <1250> | <1> | <YYYY-MM-DD> | keep | confirmed in the forecast |
| <Pay (mid-month)> | <gusto net early> | payroll | monthly | <17410.06> | <12> | <YYYY-MM-DD> | keep | confirmed in the forecast |
| <a line you listed as tax> | <match> | known | <monthly> | <amount> | | | ignore | founder said |

Status: keep (forecast it), ignore (not a regular bill), one-off, stopped. Items marked keep are carried into the next forecast even when the next export is too short to show them; change the status to stopped when one ends.

## Client payment habits

| Client | Days late | Evidence | Updated |
|---|---|---|---|
| <client> | <21> | <what happened> | YYYY-MM-DD |

Every client whose invoices you listed is kept here, so the next forecast leaves them out of the usual pattern and asks for their open invoices.

## Known payments you listed

Tax, payroll and other payments you gave, with the figure's source. Founder supplied: confirm them with your accountant or payroll provider when they change.

| Label | Kind | Amount | Rhythm | Next or only date | Supplied by | Updated |
|---|---|---|---|---|---|---|
| <Payroll taxes> | <payroll tax> | <1870.40> | <monthly / once> | <YYYY-MM-DD> | <your payroll provider> | YYYY-MM-DD |

## Last forecast

Opened on <YYYY-MM-DD> with <balance> in the bank.

| Week ends | Money in forecast | Balance forecast |
|---|---|---|
| <YYYY-MM-DD> | <figure> | <figure> |

## Forecast checks

| Checked on | From | To | Money in forecast | Money in actual | Difference |
|---|---|---|---|---|---|

## Learnings

| # | Learning | Evidence | Applies to step | Status | Added |
|---|---|---|---|---|---|
| 1 | <rule> | <what happened> | <Intake / Make / Deliver> | watch | YYYY-MM-DD |

Status: watch (seen once), active (approved or repeated), retired (kept for the record, no longer applied).

## History

| Date | Made | Option chosen | Verdict |
|---|---|---|---|
| YYYY-MM-DD | <13-week forecast> | <the answer given> | <spot on / close / off> |
