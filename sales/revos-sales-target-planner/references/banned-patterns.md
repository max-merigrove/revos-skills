# Banned patterns

Each pattern: what to watch for, why it hurts, a before and an after. The Merigrove base list comes first, then this skill's sales planning list. `scripts/check_copy.py` catches the ones a script can catch; read the rest yourself before showing anything.

## Base list

### Em and en dashes
- Watch for: the long dashes used as clause breaks.
- Why: the clearest tell of machine-written copy.
- Before: The plan looks fine (dash) until you count your hours.
- After: The plan looks fine. Count your hours and it needs 8.3 a week against your 8.

### Contrast reveal
- Watch for: "It's not X, it's Y."
- Why: a formula readers now recognise and discount.
- Before: It's not a leads problem, it's a price problem.
- After: At £3,600 the calendar runs out at 23 held calls. At £4,100 the target needs 20.

### Filler verbs and adjectives
- Watch for: unlock, elevate, leverage, seamless, robust, game-changer, delve.
- Why: they say nothing a competitor could not say.
- Before: Unlock predictable growth.
- After: Book 9 calls a week and the month lands.

### "More" as an intensifier
- Watch for: "more calls", "more leads" with no number.
- Why: lazy and unprovable.
- Before: You need more calls.
- After: You need 37 bookings a month, 9 a week.

### Announced honesty
- Watch for: "to be honest", "I mean", "let's be real".
- Why: implies the rest was not honest.

### Stock openers and exclamation marks
- Watch for: "In today's competitive market", "Great news!"
- Why: noise before the number the founder came for.

## This skill's list

### Activity advice with no figure
- Watch for: "just increase your outreach", "ramp up your activity", "double your leads", "book more calls".
- Why: this is what plain Claude says. The plan exists to replace it with a number and the constraint that stops it.
- Before: Increase your outreach to hit your number.
- After: The plan needs 56 bookings a month. Your calendar carries 23 held calls, so outreach is not the limit.

### Platitudes
- Watch for: "stay consistent", "it's a numbers game", "hustle harder", "trust the process".
- Why: a slogan where a figure should be.

### Untagged rates
- Watch for: a show, close or booking rate quoted with no tag.
- Why: the founder cannot tell what they measured from what was assumed, and will plan on a default as if it were theirs.
- Before: With a 60% show rate you need 40 bookings.
- After: With a show rate of 60% (planning default; you have not counted yet) you need 40 bookings.

### Aspirational rates
- Watch for: planning on a rate the founder hopes for ("assuming you close 50%").
- Why: a plan built on a hope fails in week two and the founder blames themselves.
- Before: If you close half your calls you only need 12.
- After: You have closed 1 in 4 (your estimate). At that rate you need 24 held calls.

### Revenue as the goal
- Watch for: "hit 40k", "your 40k target" treated as success with no word on what it leaves.
- Why: revenue can be hit with nothing left over.
- Before: You need 11 sales to hit 40k.
- After: 11 sales makes $40,000 of sales; at your costs that leaves $9,100 [NEED: confirm delivery cost].

### Cash and sales blurred
- Watch for: "you'll have 21k in the bank" from sales booked on payment plans; dividing the target by the upfront share.
- Why: a sale on instalments is not cash this month, and multiplying the plan by the share inflates it.
- Before: Half upfront, so you need twice the sales.
- After: You need 6 sales either way; with half paid on signing, S$10,800 lands in the month.

### Hiring as the first lever
- Watch for: "hire a closer", "get an SDR" before the rates are fixed.
- Why: a hire under a leaky process pays for the leak.

### Benchmarks with no source
- Watch for: "the average close rate is", "most founders book", "industry standard show rate", any percentage about other businesses.
- Why: invented or unsourced figures lose the founder's trust and cannot be checked. Planning defaults are labelled as defaults, never as facts about the market.

### Promises
- Watch for: "you will hit", "guaranteed", "this will get you to".
- Why: the plan says what the target needs; it cannot promise the market.

### Jargon in founder copy
- Watch for: pipeline velocity, CAC, LTV, MQL, SQL, funnel optimisation.
- Why: the founder asked how many calls they need. Say "calls booked", "calls held", "sales".

### Computing tax
- Watch for: grossing up take-home pay, a tax or sales tax rate, taking tax off a price, "you'll pay X in tax", a registration threshold.
- Why: tax is outside this skill in every country. The founder's accountant gives any such figure; the plan uses it as given.
- Before: At 20% you'd need about 7,400 before tax to take home 5,000.
- After: Your 5,000 is take-home, so every figure here is too low until your accountant gives the before-tax figure.

### Stating what a law requires
- Watch for: "you must register for", "the law requires", "you're legally obliged", "by law you".
- Why: the skill does not know the founder's jurisdiction and gives no legal advice. Where a rule might matter, one line sends the founder to the rules where they and their clients are.
- Before: You must register for GST once sales pass the threshold.
- After: Enter prices before any sales tax (VAT, GST or similar); ask your accountant whether you need to charge it.

### Assuming a country
- Watch for: a currency the founder did not use, a date order they did not write, a tax office or public body by name, "bank holiday", a holiday calendar, a working week they did not give.
- Why: Merigrove's founders are in the US, Asia, Europe and the UK. A plan in the wrong currency or with Friday calls in a Sunday to Thursday week reads as written for someone else.
- Before: Your first week runs Monday 26 October to Friday 30 October, skipping the bank holiday.
- After: Your first week runs on your call days, Sunday to Thursday, skipping the 27th you said you are away.

### Prose arithmetic
- Watch for: a figure in the chat or the note that the script did not print.
- Why: the model never counts by eye. `target_plan.py build --note` refuses any figure it did not compute.

### A retainer folded into one price
- Watch for: "$3,500 x 7 months is one sale", "each client is worth 24,500", or a monthly fee planned as a one-off price.
- Why: retainers stack. The clients already paying count, the first month of a new client adds one month's fee, and the clients who leave must be replaced. Either folding reads the business wrong.
- Before: Each client is worth $24,500, so 2 new clients a month and nothing breaks.
- After: You need 11 paying clients at once and have 5. That takes 4 new clients a month to reach by December 31, then 2 a month to hold it.

### A year that is nearly over
- Watch for: a yearly target divided by 12 without asking, or a dated target with no months left stated.
- Why: on 20 October, "250k this year" is ten weeks of selling, not twelve months.
- Before: 250k a year is 20,833 a month, so you need 2 sales a month.
- After: From today to December 31 is 2.4 months. Is 250k the yearly rate you want to be running at, or profit to make by then?

### Figures in someone else's number style
- Watch for: 15,000 € to a founder who writes 15.000 €, or a figure rewritten by hand into another style before the script reads it.
- Why: to a reader who uses a decimal comma, "€15,000" can read as fifteen euros; a rewritten figure is a figure the founder did not give.
- Before: Your target of €15,000 needs 7 contracts at €4,850.
- After: Your target of 15.000 € needs 7 contracts at 4.850 €.

### A label from inside a file
- Watch for: "Founder 3 says", "User 2 confirms", "per Speaker 1" in the chat.
- Why: a notes file or pasted thread is the founder's own words. Quoting its labels back reads as a machine talking about a file, not an adviser talking to them.
- Before: Founder 3's point that there are about 10 weeks left makes this the reading.
- After: Your note that there are about 10 weeks left makes this the reading.

### Tax commentary in the chat
- Watch for: "the price is before VAT, as HT means", "I've read TTC as including tax", any line explaining a tax word.
- Why: the plan carries one neutral line on sales tax in the file. A second one in the chat reads as tax advice and adds nothing the founder needs.
- Before: Prices: the price is before VAT, as HT means.
- After: (nothing; the file's one line covers it)

### The headline said twice
- Watch for: a note that opens with the headline's own words ("Nothing breaks at these rates...").
- Why: the note sits under the headline on the Plan sheet; a repeat wastes the one place for what the plan means.
- Before: Nothing breaks at these rates: the calls take 3,9 of your 10 hours.
- After: Your calendar has room, so the month turns on leads: 38 needed against the 20,3 you get now.

### Asking for feedback on every turn
- Watch for: "Is this spot on now?" after each small change.
- Why: it invites another round of small edits instead of a finished plan. Ask once; after the first change offer to save once; after that, end on the change.
- Before: Is this spot on now, or does anything else need changing?
- After: Say save when you are happy and I'll save the plan for next month.

### "I can't change the workbook"
- Watch for: a layout request answered with a refusal, or with a table that lives only in the chat while the file differs.
- Why: the workbook already holds the first action beside the pace and a Week by week table with totals, and `weeks_ahead` sets its length. Say where the thing sits, or rebuild.
- Before: I can't change the workbook's layout, so the table lives here in the chat.
- After: The weeks are now a table with a total row on the Week by week sheet; here it is to paste into your Monday notes.
