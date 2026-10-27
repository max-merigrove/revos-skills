# Worked examples

Five runs on clearly illustrative businesses, in euros, pounds, US dollars and Singapore dollars. Every figure was printed by `scripts/price_floor.py`; none was worked out by hand. Use them to see the shape of a finished run, not as benchmarks.

Contents
1. Consultoría de marketing (euros, Madrid): decimal commas, prices quoted with sales tax, one offer at its floor
2. Fern Studio (pounds): a solo designer, two offers below the floor
3. Ledgerline Bookkeeping (pounds): a two-person practice, restructure before raise
4. Ridgeway Web Co. (US dollars): pay given after tax, time given in days
5. Kaya People Advisory (Singapore dollars): prices quoted including GST
6. What plain Claude gives for the same question

## 1. Consultoría de marketing (illustrative): decimal commas, sales tax in the prices

**What the founder said.** A marketing consultant in Madrid, writing English with Spanish figures: a strategy sprint at "2.420 € IVA incluido", about 30 hours of hers and 8 of a freelance designer's at "35 €/hora"; a retainer at "1.815 €/mes con IVA", "18 horas/mes, maybe 20"; "60.000 brutos al año"; one sprint a month and four retainer clients; one retainer client pays by Stripe at "1,4% + 0,25 €", the rest by transfer. Her costs came as a semicolon CSV with decimal commas: "250,00", "54,45", a yearly "1.200,50", some lines with IVA included, and her own cuota de autónomo.

**What the skill did with the hard parts.** Every figure went into the inputs file exactly as she wrote it. The script read her style once (a comma before decimals, a dot between thousands) and wrote every figure back the same way: 2.800 €, 3,79 €. She named the 21% IVA she charges, so the prices went in as `"=2.420/1,21"` and `"=1.815/1,21"` and the script worked out 2.000 € and 1.500 €. Her costs went in as she pays them, IVA and all, because stripping tax from a cost is her accountant's question. The cuota is a payment for herself, so it was left out of the overheads as part of her pay, and the readback said so. Madrid sets A4 paper and day-month dates.

**What the script found.** Her hour is 55 €: 60.000 € over 44 working weeks and 25 client hours a week.

| Offer | Price | Price floor | Pays you an hour | Verdict |
|---|---|---|---|---|
| Sprint de estrategia | 2.000 € per sprint | 2.799 € | 47 € | Raise to 2.800 € (below cost floor) |
| Retainer mensual | 1.500 € a month | 1.504 € | 70 € | Hold, at the floor |

The retainer sits 3,79 € under its floor, within 5%, so it holds: a restructure that small is noise. At these volumes the business leaves her 82.229 € a year before tax against the 60.000 € she wants. A [NEED] asks which hours are right: her offers need 28,9 hours a week against the 25 she gave.

**What v1.1 did with the same figures.** It read "2.420" as 2.42 and "60.000" as 60, reported an hour worth 0,05 € and exited clean. The plausibility stops (an hour under 1, a price under 10) would now catch that even if the number style were missed.

## 2. Fern Studio (illustrative): a solo designer, two offers below the floor

**What the founder said.** "Brand identity projects are £2,400, they take me 40 to 50 hours if I'm honest, I pay my copywriter £300 a project and fonts and stock are about £40. Website care retainer at £350 a month, about 6 hours a month each, Stripe at 2%, hosting £25 a site. Brand workshops at £750, roughly 7 hours, can be split into 2 payments. Business costs roughly 1,100 a month." After two questions: her hour is £55 ("what I'd pay a decent senior freelancer"), 26 client hours a week, 2 projects a month, 8 retainer clients, 1 workshop.

**Diagnosis.** First price check: offers and most costs known, no saved run.

**Inputs file (as written, messy values left for the script).**

```json
{"business": "Fern Studio", "currency": "GBP", "country": "GB", "your_rate": "55", "overheads_month": "1,100",
 "client_hours_week": "26", "paid_by": "bank transfer",
 "offers": [
  {"name": "Brand identity project", "billing": "one-off", "price": "£2,400", "your_hours": "40 to 50",
   "contractor": "300", "tools": "40", "per_month": "2", "unit_label": "per project"},
  {"name": "Website care retainer", "billing": "monthly", "price": "350 a month", "your_hours": "6",
   "tools": "25", "paid_by": "Stripe", "fee_rate": "2%", "per_month": "8"},
  {"name": "Brand workshop", "billing": "one-off", "price": "750", "your_hours": "7", "per_month": "1",
   "instalments": "2 x 375", "unit_label": "per project"}]}
```

**What the script found.** Overheads come to £11 for every client hour, spread over her client hours in 46 working weeks.

| Offer | Price | Cost floor | Price floor | Pays you an hour | Verdict |
|---|---|---|---|---|---|
| Brand identity project | £2,400 per project | £3,312 | £4,140 | £35 | Raise (below cost floor) |
| Website care retainer | £350 a month | £430 | £540 | £42 | Raise (below cost floor) |
| Brand workshop | £750 per project | £462 | £578 | £96 | Hold |

**The headline.** "At these volumes the business leaves you £75,768 a year before tax, against £95,700 for your client hours at your rate. Brand identity project is the furthest below its floor: at £2,400 it pays you £35 an hour once costs and overheads are paid, against the £55 your time is worth." The whole-business block adds a check she did not ask for: at these volumes her offers need 37.8 of her hours a working week against the 26 she gave.

**The options for the brand project.** A, raise to £4,200 (recommended): a 75% rise; what one project leaves after every direct cost goes from -£415 to £1,385. Client loss, cash first: in plain cash the line is 47%, past which she takes in less until she refills the hours; each project at today's price pays her less than her £55 an hour, so a freed hour is worth her full rate, but only if she refills it. B, keep £2,400 and cut the hours by 47%, from 45 to 23.9: beyond the 25% a restructure can take, so it would change what the client buys. C, £3,300 and 23% fewer hours: a softer step for existing clients.

**The note Claude wrote (90 words).** "The two offers you sell most often are the two below their floor, and in both it is the hours that sink the price. At £2,400 the brand project pays you £35 an hour for its 45 hours. For new project clients, quote £4,200. For the eight clients already on the £350 retainer, the middle step is the gentler move: £450, with 18% fewer hours, for example a set monthly allowance of edits in place of open-ended requests. The workshop is your healthiest offer at £96 an hour; hold it."

**Also flagged.** The 2 x £375 workshop plan totals £750 against £750 paid in full, so the plan carries the risk of a missed payment for nothing.

## 3. Ledgerline Bookkeeping (illustrative): a two-person practice, restructure before raise

**What the founder said.** Bookkeeping Essentials at £180 a month (Sam, the employee, 4 hours; the founder half an hour), Bookkeeping and Payroll at £320 a month (Sam 6.5 hours, founder 1.5), year-end accounts at £950 (founder 9 hours, Sam 6, £120 for a tax specialist). Software per client £12 and £20. Direct debit at 1.2%. Sam on £31,200 for 37.5 hours; her payroll provider puts his full cost at "about £19 an hour". Overheads "about £4,450 a month but that includes Sam's salary". Target pay £70,000 before tax; 22 client hours a week, Sam 30. 18, 9 and 1.5 a month.

**The decisions the intake guide makes.** Sam's salary comes out of the overheads because his hours are costed per offer (`"=4450 - 31200/12"`, £1,850). Sam's £19 is her payroll provider's figure, used as given. Her offers use only 9.4 of her 22 client hours a week, so the script first priced her hour on 9.4 and asked which is right; she confirmed 22 ("the rest is reviewing Sam's work and answering clients across all of them"), so `"client hours as given"` went into `confirmed` and her hour is £69 over 46 working weeks.

| Offer | Price | Price floor | Pays you an hour | Verdict |
|---|---|---|---|---|
| Bookkeeping Essentials | £180 a month | £209 | £96 | Restructure: 15% fewer hours |
| Bookkeeping and Payroll | £320 a month | £408 | £66 | Restructure: 23% fewer hours |
| Year-end accounts | £950 each | £1,264 | £63 | Raise to £1,300 |

**What the whole business adds.** The practice leaves her £28,536 a year before tax against the £70,000 she wants, and 12.6 of her client hours a week sit in no offer. No single offer fix closes that; the note leads with it rather than reading the restructures as good news.

## 4. Ridgeway Web Co. (illustrative): pay given after tax, time given in days

**What the founder said.** A Denver web developer writing American English: website builds $6,500 at "about 6 days" plus a $1,200 freelance designer; maintenance plans $250/month at 3 hours, 12 clients; strategy days $1,800 at "one day plus 2 hrs prep"; Stripe at 2.9%; $900 a month of running costs; "I want to take home $90k a year"; 28 billed hours a week; "4 weeks off a year".

**The first run, on after-tax pay.** Her hour came to $67. The summary marked every Hold and Restructure provisional and recommended nothing for them: website build Hold (provisional), maintenance plan Restructure (provisional), strategy day Hold (provisional). It offered three ways to settle them that need no tax: what she would pay someone to do her part, her CPA's before-tax figure, or what she paid herself last year before tax. Letter paper and month-first dates, because she is in the United States.

**With her CPA's $118,000 before tax.** Her hour is $88, and two of the provisional verdicts moved, which is why they were provisional.

| Offer | Price | Price floor | Pays you an hour | Verdict |
|---|---|---|---|---|
| Website build | $6,500 per build | $7,523 | $98 | Restructure: hours 48 to 39.8 |
| Maintenance plan | $250 a month | $373 | $73 | Raise to $380 (below cost floor) |
| Strategy day | $1,800 per day | $1,243 | $167 | Hold |

## 5. Kaya People Advisory (illustrative): prices quoted including GST

**What the founder said.** A Singapore HR consultant: HR audit S$3,270 "including 9% GST", about 30 hours; fractional HR retainer S$2,180 a month including GST, 16 of her hours and 6 of a freelance associate's at S$65; workshops S$1,500 before GST, "a full day plus 3 hours prep"; PayNow or bank transfer; S$1,400 a month of overheads; S$150,000 before tax over 24 client hours a week.

**What the skill did with the hard parts.** She named the 9% she charges, so the two prices went in as `"=3270/1.09"` and `"=2180/1.09"`. No rate was looked up and nothing was said about whether she must charge it. Her day is 8.5 hours. She did not know her working weeks, so 46 was used and stated.

**What the script found.** Her hour is S$136. All three offers sit below their cost floor: audit S$5,600 recommended, retainer S$3,600 (or S$2,800 with 21% fewer hours for her three current clients), workshop S$2,200. At these volumes the business leaves her S$113,160 a year before tax against S$150,000, so the headline is about the business, not one offer.

## 6. What plain Claude gives for the same question

The Ridgeway founder was put to plain Claude with no skill (see `assets/before-after.md`). It did well on judgement: it noticed that take-home pay needs a before-tax figure and gave a rough hourly figure per offer. What it could not do: it estimated the tax itself to reach a before-tax figure, gave no exact floor or buffer, no option maths (how many clients a rise can lose, in cash), no file and no memory, and its price suggestions were ranges with no working. The skill asks the same judgement questions, leaves the tax to her accountant, and adds everything plain Claude cannot audit.
