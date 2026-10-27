# Before and after: the same founder, plain Claude and the Price Floor Calculator

Landing page material. One illustrative founder: a US web developer in Denver, writing in dollars. Website builds $6,500 (about 6 days of her time, plus a $1,200 freelance designer), maintenance plans $250 a month (about 3 hours, 12 clients), strategy days $1,800 (a day plus 2 hours of prep). Stripe at 2.9%, $900 a month of running costs, 28 billed hours a week, 4 weeks off a year. She wants "$90k take-home"; her CPA puts that at about $118,000 before tax.

## The question

"Am I charging enough?"

## Plain Claude (no skill)

> Short answer: your builds and strategy days look healthy; the maintenance plans are the weak spot. To take home $90k as a self-employed person in Colorado you'd need roughly $120k to $125k before tax ... a target of roughly $98 an hour. Website build: roughly $106 an hour, fine. Maintenance: about $81 an hour; consider raising to $300 to $350 a month or capping the hours. Strategy day: about $175 an hour, strong.

Sensible on the weak offer. But it works out her tax itself from one state's rules, every figure is by eye, the price is a range with no working (and both ends sit below the plan's real floor), the build's thin buffer is missed, there is no way to see what a rise costs in lost clients, nothing to keep, and next month it starts from scratch.

## With the Price Floor Calculator

On her $90k take-home it still finishes the run, but marks every Hold and Restructure provisional and recommends nothing for them, because a before-tax figure can only lift a floor; it never estimates tax. It offers three ways to settle them, one of which (what she would pay someone to do her part) needs no tax at all. Two of those provisional verdicts moved once her CPA gave $118,000:

> **At these volumes the business leaves you $158,110 a year before tax, against the $118,000 you want. Maintenance plan is the furthest below its floor: at $250 it pays you $73 an hour once costs and overheads are paid, against the $88 your time is worth.**
>
> | Offer | Price | Price floor | Pays you an hour | Verdict |
> |---|---|---|---|---|
> | Website build | $6,500 per build | $7,523 | $98 | Restructure |
> | Maintenance plan | $250 a month | $373 | $73 | Raise |
> | Strategy day | $1,800 per day | $1,243 | $167 | Hold |
>
> **Maintenance plan: raise to $380 a month for new clients**, or $320 with 14% fewer hours as a softer step for the 12 already on it. In plain cash the line is 34%: lose a larger share of plan clients at $380 and you take in less than today; keeping all 12, cash in rises by $1,515 a month.
>
> **Website build: keep $6,500 and bring your hours from 48 to 39.8.** It pays you $98 an hour but keeps a 7.9% buffer rather than your 20%.

Plus a workbook with live formulas (change the pay you want, your weeks or a price and every floor moves), a summary that prints on one page, and a memory file: next time "costs went up" is a one-line re-run.

## The difference in five seconds

| | Plain Claude | Price Floor Calculator |
|---|---|---|
| Pay before or after tax | Estimates her tax itself | Marks what the after-tax figure cannot settle as provisional; never estimates tax |
| Exact price floor per offer | No | Yes, with her hours, designer, fees and overheads priced in |
| A verdict per offer | A suggestion | Hold, restructure or raise, with the reason |
| The build's thin buffer | Missed ("fine") | Restructure: 48 to 39.8 hours at the same price |
| What a rise can survive | No | Clients she could lose, in cash and in freed hours |
| Her own working year and day | Assumed | Her 48 weeks; days at 8 hours, stated; Letter paper and US dates from her country |
| Arithmetic you can check | By eye | Script and spreadsheet, the same formulas |
| Next month | Start again | One-minute re-run from memory |

Figures from the calculator's own test run of this founder (`evals/sample-runs/us-after-tax-days/`); the plain-Claude answer is in `evals/sample-runs/us-after-tax-days/baseline-plain-claude.md`. Illustrative business; planning, not financial, tax or legal advice.
