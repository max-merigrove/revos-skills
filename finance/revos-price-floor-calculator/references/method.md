# Method: the price floor for a service business

Contents
1. The two floors and the one rule underneath them
2. The arithmetic, per offer
3. Overheads, and how they are shared
4. Your hour: setting the founder rate
5. The verdict: hold, restructure or raise
6. The price change options
7. Checks the script runs and flags it raises
8. Working defaults and where each comes from
9. What this method does not do

All arithmetic runs in `scripts/price_floor.py`. Never compute a figure in prose; copy it from the script's output. The workbook carries the same formulas, so the summary and the spreadsheet cannot disagree.

## 1. The two floors and the one rule underneath them

**The cost floor** is the price at which one sale covers every cost it causes, including the founder's own hours and a fair share of the overheads, with nothing left over. Below it, every sale makes the business poorer.

**The price floor** adds the founder's target margin on top. It is the least the offer can charge and still keep the margin the business needs to save, invest or survive a bad month.

**The rule underneath both: founder hours are never free.** The commonest pricing failure in a founder-led service business is costing the founder's delivery time at zero. The offer looks profitable until someone else has to deliver it, or until the founder works out what they earn an hour. Every hour the founder spends on a client (delivery, calls, admin, revisions, travel) enters the cost at the founder's rate.

**Costed once.** Because the founder's time is priced into each offer, the founder's own salary or drawings are never also counted in the overheads. Counting both inflates the floor and pushes prices up for the wrong reason. The same applies to any employee whose hours are costed per offer: their pay comes out of the overheads.

The floor is the least an offer can charge. It is not what the offer is worth. Price is set between what the client would otherwise do (hire a freelancer, an agency, do it in house, do nothing) and what the result is worth to them. The floor only says where the bottom is.

## 2. The arithmetic, per offer

Everything is per sale for one-off work (a project, a workshop, a set of accounts) and per month for monthly work (a retainer, a subscription). Prices are before any sales tax (VAT, GST or similar).

| Figure | Formula |
|---|---|
| Net revenue | price x (1 less refund and write-off rate) |
| Payment fees | price x fee rate |
| Team time | team hours x team cost an hour |
| Cash costs | payment fees + contractor + tools and other direct costs + team time |
| Your time | your hours x your rate |
| Direct cost | cash costs + your time |
| Contribution | net revenue less direct cost: what one sale leaves after every cost that moves with it |
| Overhead share | (your hours + team hours) x overhead per client hour |
| Full cost | direct cost + overhead share |
| Cost floor | (full cost less fees) / ((1 less refund rate) less fee rate) |
| Price floor | (full cost less fees) / ((1 less refund rate) x (1 less target margin) less fee rate) |
| Margin at today's price | (net revenue less full cost) / net revenue |
| What today's price pays you an hour | (net revenue less cash costs less overhead share) / your hours |

Why the floor formula divides: payment fees rise with the price, so a floor that simply added the margin to today's costs would be short by the fees on the extra. Solving for the price where margin equals the target, with fees and refunds charged on that price, gives the formula above. It is exact.

**What today's price pays you an hour** is the figure founders remember. It is what is left for the founder, per hour of their own time, after every other cost and the overhead share are paid, and before any margin. Set beside the founder's rate it answers "am I charging enough" in one line. Where most of the delivery is done by a team member, this figure can be high on very few founder hours; read it beside the verdict, which carries the margin.

## 3. Overheads, and how they are shared

**Overheads** are business costs that would still be there with no clients next month: software subscriptions, insurance, the accountant, phone and broadband, premises or co-working, the founder's own marketing spend, professional memberships. They exclude the founder's pay and any employee pay already costed per offer, and they exclude anything that moves with one client (that is a direct cost).

The test, one cost at a time: would this cost exist with zero clients next month? Yes is an overhead. No is a direct cost of the offer that causes it.

**Shared by client hours.** Overhead per client hour = monthly overheads / (client hours a week x working weeks a year / 12). Overheads are paid every month, but client hours only happen in the weeks the founder works, so the hours are counted over working weeks, not 52; counting 52 would understate each hour's share by 52 over the working weeks (13 per cent at 46 weeks). Each offer carries its hours times that rate. In a service business time is the capacity the overheads pay for, so sharing by hours charges a long project more than a short workshop, which an equal share per client would not. Client hours a week means the hours the founder and any costed team member spend on client work across all offers, including calls and admin for clients, not selling or the founder's own admin.

If the founder does not know their weekly client hours but gave hours per sale and sales a month for every offer, the script works it out (hours a month x 12 / working weeks), and the workbook carries it as a formula, so a change to any offer's hours or volume moves it. If neither is known, it uses the default of 25 hours a week and says so.

**Empty diary.** Overheads shared over fewer client hours make each hour dearer. Where the founder gives the hours a week they would work if full, the script shows the floor at full load beside today's. The gap between them is the cost of spare capacity; it is a reason to fill the diary as well as a reason to price.

**An offer delivered entirely by contractors** carries no overhead share under this method, because it uses none of the business's client hours. Count the founder's hours spent managing it (briefing, checking, client calls): there are always some, and they carry the share.

## 4. Your hour: setting the founder rate

The founder rate is the one judgement the floor rests on. Three ways to set it, in order of preference:

1. **Replacement cost.** What the business would pay a capable person to do the founder's part of the work. This is the shadow rate: the price of the founder's time if they were not free.
2. **Target pay.** The pay the founder wants a year before tax, divided by their client hours a week and the weeks they work a year. Where the founder gave volumes for every offer and the hours those offers use (hours per sale x sales a month x 12 / working weeks) differ from the founder's own figure by more than 10 per cent, the script prices the hour on the lower of the two and raises a [NEED] asking which is right. On the hours the offers use, the offers fund the pay the founder wants; on a higher figure, they fund only part of it. If the founder confirms their own figure (`"client hours as given"`), it is used and the whole-business line shows the gap. The weeks are the founder's own (52 less their holidays and their public holidays, which differ by country); if they do not say, the script uses 46 and the summary states it as an assumption to change. This prices each client hour so the year's client work funds the pay they want. The script does the division when given `target_pay_year`, `your_client_hours_week` and, if known, `working_weeks_year`.
3. **A stated figure.** The founder names a rate.

If the founder skips, the script uses a placeholder of 60 an hour in their currency and flags it as `[NEED]`. The summary must say so in its assumptions, and the founder should change the yellow cell in the workbook.

## 5. The verdict: hold, restructure or raise

Per offer, in this order:

1. **Hold** when today's price is at or above the price floor. The summary says by how much, and that the floor is not the ceiling. **Hold, at the floor** when the price sits less than 5 per cent below the floor and above the cost floor: the buffer is a little under target, and a restructure that small is noise.
2. **Restructure** when the price is below the floor, and cutting the delivery hours (founder and team, by the same share) by at most the restructure limit would bring the offer to its target margin at today's price. The share of today's hours the price can pay for is k = (net revenue x (1 less target margin) less fees less contractor less tools) / (your hours x your rate + team hours x team rate + all hours x overhead per hour). The cut is 1 less k. The limit is 25 per cent by default: a deeper cut usually changes what the client is buying, which is a new offer rather than a restructure.
3. **Raise** otherwise. The recommended price is the price floor rounded up (to 10 below 500, 50 below 2,000, 100 below 10,000, else 500), for new clients first.

A founder's stated route for an offer (`prefer`) overrides steps 2 and 3: "raise" recommends the rise even when a restructure would fit; "restructure" recommends the cut even beyond the limit, and the summary says the cut is beyond what a restructure usually takes.

**Pay given after tax.** A before-tax figure is always higher, so it can only lift every floor. A Raise verdict therefore stands, and its price is a minimum ("at least"). Hold and Restructure are marked provisional, no option is recommended for them, and the summary shows the floors with the hour a quarter higher as a sensitivity (never as a tax estimate). Three routes settle them without the skill touching tax: what the founder would pay someone capable to do their part an hour, the before-tax figure from their accountant, or what they paid themselves last year before any tax.

The verdict also says when an offer is **below its cost floor**: it falls short of its full cost on every sale once the founder's time is counted. That is the most urgent case, because each extra client makes the founder poorer at their own rate.

Restructuring levers, to name the one that fits what the founder described: a tighter scope with extras charged separately; a templated or pre-filled start; fewer or shorter calls; group delivery in place of one-to-one; moving a block of the founder's hours to a team member or contractor whose hour costs less; charging for revisions beyond a set number; changing monthly work from unlimited to a stated allowance.

## 6. The price change options

For every offer below its floor the script works out:

- **A. Raise** to the recommended price. With the rise: what one sale leaves before and after, and the **break-even client loss in two views, always shown together and named**:
  - *In plain cash*, shown first: (new cash per sale less old cash per sale) / new cash per sale, where cash per sale is what one sale leaves before the founder's time and overheads. Lose a larger share of clients than this and the business takes in less cash until the freed hours are refilled.
  - *Counting freed hours at your rate*, shown second and only with its condition: (new contribution less old contribution) / new contribution, contribution including the founder's time. Lose fewer clients than this and the founder is no worse off, but only if they refill each freed hour at their rate. Not shown for an offer sold or held once a month or less, where a share of clients lost is not a useful line.
  The cash line is always the lower one. For a sole trader it is the one that pays the bills next month, so never write "you could lose X and make the same" without the cash line beside it. Contribution is used, not profit after overheads, because the overheads stay when a client leaves. Where today's contribution is negative, each client pays the founder less than their rate, so a freed hour is worth the founder's full rate, above what the client paid for it, if it is refilled; the cash line still applies.
- **B. Restructure**: same price, hours cut by the share above, with the hours before and after.
- **C. Meet in the middle**: half the rise (rounded up), with the hours cut that closes the rest. Shown when that cut is at least 5 per cent; a softer step for existing clients.

The recommended option follows the verdict: B for restructure, A for raise. Where the rise is large, C is often the right route for existing clients while new clients get A. That is a judgement for the founder; name it, do not decide it.

How to roll out a rise is in `references/price-change-rollout.md`.

## 7. Checks the script runs and flags it raises

- **Instalment plans.** Where an offer can be paid in instalments, the plan total should sit above the pay-in-full price, so spreading the cost pays for the risk of a missed payment, and the last instalment should fall before delivery ends. The script checks the first; ask about the second when a plan exists. If the buyers are consumers, one line: rules on consumer payment plans differ by country, so check them with a qualified adviser where the founder and their clients are.
- **The alternative.** Where the founder says what the client would pay instead, the script shows it beside the floor. Alternative below the floor: the offer cannot win on price and must win on what only this business delivers. Alternative above: there is room to price on value.
- **Test price.** Where the founder names a price they want to test, the script works out its contribution and both break-even views.
- **The whole business.** With volumes for every offer, the script adds sales a month and a year, and what the business leaves the founder a year before tax (cash per sale times volume, less overheads, times 12), set against the pay they want (or their client hours at their rate). This answers "am I charging enough?" for the business as well as per offer, so a single thin offer never reads as "you are short" while the business clears the target.
- **Sales tax.** Prices are entered and shown before any sales tax, with one neutral line: "Prices: read before any sales tax (VAT, GST or similar); ask your accountant whether you need to charge it." The skill holds no rates, thresholds or registration rules for any country and never says whether a founder must register or charge.
- **Pay before tax.** The founder rate from target pay needs the pay before tax. If the founder gives an after-tax figure, the run still finishes: Raise verdicts stand, Hold and Restructure are provisional (section 5), and the founder is offered three ways to settle them, none of which needs the skill to touch tax. It never estimates income tax or any other deduction, in any country.
- **Employee cost.** The cost of an employee's hour is the founder's figure (from their payroll provider or accountant), stored with its source. The skill never adds employer on-costs itself.
- **Sensitivity.** The workbook shows the floor with the founder's hour worth 25 per cent less and 25 per cent more, so the founder sees how much the floor rests on that one figure.
- **Missing inputs** become `[NEED: ...]` lines and the script exits 1. An offer without a price or the founder's hours is listed and not judged.
- **Figures that cannot be right.** Before anything is built, the script stops with one question when the founder's hour is under 1 unit of their currency or over 20 times what any offer charges for an hour of their time, a price is under 10 or under 1 for each hour of work, overheads per client hour exceed the founder's hour, or client hours pass 80 a week. These are almost always a misread number. A figure the founder confirms is added to `confirmed` and passes.
- **Number style.** Every founder-typed figure is read in their own style, detected once per run; a figure that could be read two ways stops with one question. Figures are written back in the same style, with the currency sign where the founder puts it.

## 8. Working defaults and where each comes from

Every default is stated to the founder before the figures are shown, and every one is a yellow input cell in the workbook.

| Default | Value | Source |
|---|---|---|
| Buffer (target margin) | 20 per cent | Working default: what an offer keeps after every cost and the founder's pay, for quiet months, tax bills and holidays. Shown to founders as "a 20% buffer; change it if you aim higher" |
| Payment fees, card or online | 3 per cent | The top of the 1.5 to 3 per cent range Merigrove practitioner guidance uses for card and online payments, so the floor errs safe. Replace with the founder's own rate |
| Payment fees, bank transfer | 0 | No fee |
| Client hours a week | 25 | Assumption when unknown; change it |
| Founder rate when skipped | 60 an hour in the founder's currency | Placeholder only, flagged `[NEED]` |
| Working weeks a year | 46 | Assumption when the founder does not say: 52 less 6 weeks for their own holidays and public holidays. Used for the hour from pay and for spreading overheads. Stated in the summary and a yellow cell; the founder's own figure replaces it |
| Hours check | 10 per cent | Merigrove working default: how far the hours the offers use may differ from the founder's figure before the hour is priced on the lower one and a [NEED] asks which is right |
| At the floor | within 5 per cent below | Merigrove working default: a price this close to its floor (and above its cost floor) holds |
| Hours in a working day | 8 | Used only when the founder gives time in days and does not say how long their day is; stated in the summary |
| Restructure limit | 25 per cent cut in hours | Merigrove working default |
| Rounding steps | 10, 50, 100, 500 | Merigrove working default |
| Pricing review | at least once a year, and whenever a cost moves | Merigrove practitioner guidance |

None of these is a statistic about other businesses, and none may be presented as one.

## 9. What this method does not do

- It does not say what the market will pay. That is positioning and value, and it sits above the floor.
- It does not forecast cash, profit for the year or tax. A price can clear its floor and the business still run short of cash in a month when clients pay late.
- It does not handle sales tax, income tax, company tax, employer costs or consumer credit, and holds no country's rules. Prices are read before any sales tax; anything tax, payroll or legal goes to the founder's accountant, payroll provider or lawyer.
- It is a planning tool, not financial, tax or legal advice.
