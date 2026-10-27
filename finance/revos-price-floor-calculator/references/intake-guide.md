# Intake guide: turning what the founder gives you into the inputs file

Contents
1. The inputs file
2. Reading messy material
3. Offers that are not simple
4. People: the founder, employees, contractors
5. Costs: direct or overhead
6. Sales tax, currency and the founder's year
7. What to ask, and how
8. What does not add up: catch it early

## 1. The inputs file

Write one JSON file and pass it to `scripts/price_floor.py`. Values may be messy strings, copied exactly as the founder wrote them; the script reads "1.5k", "$1,200", "S$1,200", "1,200 AUD", "2.420 €", "1.200,50", "about 12", "10 to 12" or "10 - 12" (the midpoint, noted in the summary), "2.9%", "1,4%" and "20". It reads every figure in the founder's own number style (1,234.56 or 1.234,56), detected once from everything in the file, through `scripts/locale_numbers.py`. It also works out sums and simple sums of parts, so you never do input arithmetic by eye: "6 x 1.5 + 6 x 0.5 + 3" for hours, "=4450 - 31200/12" for overheads less an annual salary, "=61.20/2550" for a fee rate, "=2.420/1,21" for a price less a sales tax rate the founder named. A leading "=" is needed for subtraction; without it a spaced dash reads as a range. Never retype a figure in another style: "1.200,50" stays "1.200,50".

| Field | Meaning | If missing |
|---|---|---|
| `business` | Name for the file and title | "Your business" |
| `currency` | The founder's ISO code: USD, SGD, AUD, GBP, EUR, CAD, NZD, HKD, INR or any other | [NEED]: figures show without a symbol. A bare "$" raises a [NEED] (which dollars) unless `country` settles it |
| `country` | The founder's ISO country code (US, ES, SG, GB...), from a city, a country or a currency only one country uses; sets paper size and date order | A4 and day-month dates, stated in the summary as an assumption |
| `decimal` | "comma" or "dot", only if the founder says how they write numbers | read from their figures; a figure that could go either way stops the run with one question |
| `confirmed` | Names from STOP lines the founder has confirmed (a figure the script doubted, or `"client hours as given"`) | none |
| `date` | Run date, YYYY-MM-DD | today |
| `locale` | `en-US` for a founder who writes American English: spelling only | British spelling; plain `en` for the page language |
| `your_rate` | What an hour of the founder's time is worth. With after-tax pay and hours also given, the script uses whichever is higher, this or the hour the after-tax pay needs, and says so | see `target_pay_year`; else 60, flagged [NEED] |
| `target_pay_year`, `your_client_hours_week` | Pay wanted a year and the founder's own client hours a week; the script divides over the working weeks. With no hours a week given, it takes the hours the offers use when every offer has hours and volumes | not used |
| `working_weeks_year` | Weeks a year the founder works once their own holidays and public holidays are out | 46, stated in the summary as an assumption to change |
| `target_pay_basis` | "before tax" or "after tax" ("take-home" reads as after tax). After tax raises a [NEED]: ask the founder for the before-tax figure from their accountant; never estimate tax | flagged as an assumption |
| `day_hours` | Hours in the founder's working day, used only when time is given in days | 8, stated in the summary |
| `card_share` | Share of clients paying by card when payment is mixed; applies to a given `fee_rate` too | not used |
| `pinned_line` | A line the founder wants first on the summary, in their words ("Hollis stays at $4,800 for now.") | none |
| `target_margin` | Margin to keep above full cost | 20% |
| `overheads_month` | Overheads a month, excluding the founder's pay and costed team pay | 0, flagged [NEED] |
| `client_hours_week` | Founder plus costed team hours on client work a week. Usually leave it empty and give `your_client_hours_week`: the script adds the team's hours from the offers | worked out, else 25 |
| `paid_by` or `fee_rate` | How clients pay, or the fee rate. A fee with a fixed part goes in as written ("2.9% + 30c", "1,4% + 0,25 €"): the script works it out on each offer's price | 3% card default (a working assumption, never described as typical); 0 for bank transfer |
| `full_hours_week` | Client hours a week if the diary were full | not shown |
| `rescope_limit` | Largest hours cut a restructure can take | 25% |
| `sources` | Where each business figure came from, by field name | "founder said" |
| `offers` | A list; each item below | at least one |

An offer with hours but no price still gets its floor (before any sales tax) and no verdict: use it for a new offer, or for a first provisional run when the price includes a sales tax whose rate the founder has not named.

Per offer: `name`; `billing` (one-off or monthly); `price` (what one client actually pays per sale or per month, after any usual discount); `your_hours` (per sale or per month, including calls, admin, revisions and travel for that client); `team_hours` and `team_rate`; `contractor` (per sale or per month); `tools` (software, materials, licences, hosting or travel that this offer alone causes); `paid_by` or `fee_rate` to override the business default; `refund_rate`; `per_month` (sales a month for one-off work, clients on it for monthly work); `alternative` (what the client would pay instead); `instalments` ("3 x 500"); `proposed` (a price the founder wants tested); `unit_label` (optional wording such as "per project"); `prefer` ("raise" or "restructure", when the founder has said which route they want for that offer, such as "the weekly cadence is what they pay for, show me the raise").

## 2. Reading messy material

Draft from whatever is pasted, then ask only what is missing.

- **A proposal or price list:** offers, prices, what is included. Inclusions hint at hours (four workshops of two hours plus preparation).
- **An invoice:** the price actually paid, any discount, payment terms, how it is paid.
- **A P&L or management accounts:** overheads. Strip out cost of sales (that is direct cost per offer), the founder's salary, dividends or drawings, and the pay of any team member whose hours you are costing per offer.
- **A bank export:** recurring outgoings are the overheads; payments to freelancers are contractor costs; card processor deductions show the real fee rate (fees taken over money received).
- **A voice-note transcript or a ramble:** pull every figure out into a list, read it back in one short block, and ask "what's wrong or missing?" before computing.
- **A screenshot of a spreadsheet:** read the figures; say which cells you could not read.
- **Number styles:** pass figures exactly as written. "2.420 €", "60.000 brutos", "1.200,50", "4,5 horas" and "1,4%" are read in the founder's style once the file shows it. A lone "2.420" with nothing else to go on stops with one question ("Do you write a thousand and a half as 1.000,50 or 1,000.50?"); figures that mix both styles stop the same way. Ask it; never guess.
- **Hours as days:** a day is 8 hours unless the founder says how long theirs is (`day_hours`); the summary states which.
- **Ranges:** pass them as written ("10 to 12", "6-8hrs", "18-20 horas"); the script uses the midpoint and the workbook lists it.
- **Units on numbers:** pass them as written ("7.5hr", "12hrs", "150pm", "900pa", "S$1.2k", "2 days", "90 mins", "35 €/hora", "1.815 €/mes", "2 días", "90 minutos", "7,5 Std."); the script strips the unit, and in an hours field reads days at `day_hours` (8 unless set) and minutes as sixtieths, in English and the common European languages.
- **A figure the script doubts:** an hour under 1, a price under 10 or under 1 for each hour of work, overheads above the hour, or more than 80 client hours a week stops the run with an ASK line. These are nearly always a misread number. Ask; if the founder confirms, add the name the STOP line gives to `confirmed`.
- **Percentages:** "2.9%", "2.9" and "1" are all per cent (1 is 1%); "0.2" is a fraction (20%). A fee, refund or buffer of 90% or more stops the run with a plain STOP line: ask the founder again.
- **Mixed payment methods:** "bank mostly, a couple by card": set `paid_by` to bank transfer and `card_share` to the card share if the founder can say it (ask once); otherwise set the card rate only on the offers clients pay by card, and say so.

## 3. Offers that are not simple

- **Tiers or packages:** each tier is its own offer.
- **Retainers billed quarterly or yearly:** convert to a month (price / 3 or / 12) and use hours a month.
- **Day rates:** one offer, price = the day rate, your hours = the day plus the admin and travel it causes.
- **Hourly billing:** one offer, price = the hourly rate, your hours = 1 plus the unbilled time each billed hour causes (emails, invoicing, travel). If a founder bills 20 hours and works 26 for those clients, your hours per billed hour is 1.3. This is where hourly billers find their real rate.
- **Bundles with a product or materials:** materials go in `tools`.
- **Payment plans:** price is the pay-in-full price; the plan goes in `instalments`.
- **A free or discounted pilot:** run it as an offer with its real price so the gap shows; say it is deliberately below the floor if that is the intent, and suggest an end date.

## 4. People: the founder, employees, contractors

- **The founder:** hours per sale at the founder rate. Include everything done for that client. Selling time before the client signs is not included; it is a cost of winning clients, not of delivering to them.
- **Someone who "costs me 18 an hour":** ask once whether they are employed or freelance (inside question 2). Freelance: the 18 is their full cost. Employed: use the figure the founder gives, and say in one line that the full cost of an employee's hour (pay plus whatever the business pays on top) comes from their payroll provider or accountant; never estimate it.
- **Employees whose hours you know per offer:** `team_hours` at `team_rate`, the full cost of an hour as the founder gives it, recorded under `sources` with where it came from. If the founder gives only a salary and the hours worked, pass it as `"=31200/(37.5*52)"` for the script to work out, and say it is pay only; the founder adds anything paid on top from their payroll provider or accountant. Take that employee's pay out of the overheads.
- **Contractors and freelancers:** their charge per sale or per month in `contractor`. If they bill by the hour, multiply.

## 5. Costs: direct or overhead

One question for each cost: would it still be there with no clients next month? Yes is an overhead. No belongs to the offer that causes it.

Enter costs as the founder pays them. Never strip sales tax out of a cost: whether it can be reclaimed is an accounting question for their accountant, and leaving it in errs safe. A yearly cost goes in over 12 (`"1.200,50/12"`).

A payment for the founder themselves (their own pension, social or self-employed contributions, drawings or salary) is part of their pay, not an overhead. Leave it out, say so in the readback ("I left out the 294 a month for your own contributions as part of your pay; right?"), and record it under `sources`. Never say whether such a payment is required or how much it should be.

Common placements: software every client uses (accounting, design, project tools) is an overhead unless it is charged per client seat, in which case it is a direct cost per client; hosting for a client's site is direct; insurance is overhead; the founder's own marketing is overhead; travel to a client is direct.

## 6. Sales tax, currency and the founder's year

Prices are entered and shown before any sales tax. The summary carries one neutral line: "Prices: read before any sales tax (VAT, GST or similar); ask your accountant whether you need to charge it." If the founder's figures include a sales tax, ask for the price before it; if they name the rate they charge, pass `"=1100/1.1"` (or `"=2.420/1,21"` in their style) and record the rate as founder supplied. A price passed with sales tax words still on it ("2.420 € IVA incluido", "S$3,270 incl GST") stops the run with that question, so nothing is priced on a tax-inclusive figure by accident; "+ VAT" or "excl. GST" is read as before tax. Never look up a rate, a registration threshold or a filing rule, and never say whether the founder must register or charge.

Use the founder's currency throughout. Take it from what they paste (a code, or an unambiguous symbol: £, €, S$, A$, C$, NZ$, HK$, ₹); a bare "$" is ambiguous, so ask which dollars. Never convert. If two currencies appear, ask which one the workbook should use and say figures in the other are left out.

Dates and paper follow the founder's country (`country`), never their spelling: Letter and month-first dates for the United States, A4 and day-month dates for most of the world, year-first for countries that write dates that way. If the country is not known, ask once inside question 1; until then the summary says it used A4 and day-month dates. The working year is theirs: ask how many weeks they work once their holidays and public holidays are out, inside question 3; if they do not say, 46 is used and stated as an assumption to change. Never assume a country's holiday calendar.

## 7. What to ask, and how

At most five questions on a first run, one on a return run. Ask only what the pasted material and memory do not answer, in plain words, with options and a stated default. The five, in priority order, are in SKILL.md. A question the founder skips takes its default, and the default is named in the summary's assumptions.

Never ask for a figure in jargon. Ask "What does one client pay you, and roughly how many hours do they take from you?" not "What is your contribution margin?"

## 8. What does not add up: catch it early

Before the first reply, check the founder's own material against itself the way a sharp accountant would, and say what you find in the first reply, each with what it changes:

- **Money in against the price list:** a month's receipts (bank or processor payouts) against clients times prices. A shortfall is timing, late payers, discounts or a wrong client count; ask which, and say a collections gap is not a pricing gap.
- **Freelancer payments against hours:** what the bank shows paid against their stated hours times their rate. Ask which is a normal month, or whether they invoice in arrears.
- **People missing from an offer:** a freelancer or employee who works on some offers but has no hours on another that plausibly needs them ("who edits the Starter episodes?"). Ask; never assume zero or invent a figure.
- **A flat amount that can be read two ways:** "600 flat a month" beside two clients may be per client or in total. Show both readings and what each does to the floor, or ask.
- **Two figures for the same thing:** hours a week in the message against hours the offers use, a price in the notes against the message. Quote both and ask which is right; never say the founder wrote something they did not.
- **Dates and sums:** a total that does not add, a payment already made, a date that cannot be right. Say so.

Put each in plain words, with the founder's names for things. Never resolve one silently.
