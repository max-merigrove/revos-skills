# Banned patterns

Each pattern: what to watch for, why it hurts, a before and an after. The Merigrove base list comes first, then this skill's pricing list. `scripts/check_copy.py` catches the ones a script can catch; read the rest yourself before showing anything.

## Base list

### Em and en dashes
- Watch for: the long dashes used as clause breaks.
- Why: the clearest tell of machine-written copy.
- Before: The project looks fine on paper (dash) until you count your hours.
- After: The project looks fine on paper. Count your hours and it pays you 36 an hour.

### Contrast reveal
- Watch for: "It's not X, it's Y."
- Why: a formula readers now recognise and discount.
- Before: It's not a pricing problem, it's a scope problem.
- After: The price holds if the hours come down from 20 to 17 a month.

### Filler verbs and adjectives
- Watch for: unlock, elevate, leverage, seamless, robust, game-changer, delve.
- Why: they say nothing a competitor could not say.
- Before: Unlock healthier margins.
- After: At 4,100 the project keeps the 20 per cent you set.

### "More" as an intensifier
- Watch for: "more profit", "charge more" with no number.
- Why: lazy and unprovable.
- Before: You should charge more for retainers.
- After: The retainer needs 550 a month to reach its floor.

### Announced honesty
- Watch for: "to be honest", "I mean", "let's be real".
- Why: implies the rest was not honest.

### Stock openers and exclamation marks
- Watch for: "In today's economy", "Great news!"
- Why: noise before the number the founder came for.

## This skill's list

### Pricing platitudes
- Watch for: "charge what you're worth", "know your value", "no-brainer".
- Why: the founder came for a number, not a slogan.
- Before: Remember to charge what you're worth.
- After: Your hour is worth 55. This price pays you 36.

### Advice with no figure
- Watch for: "just raise your prices", "consider increasing", "you might want to look at".
- Why: a verdict without a number is not a verdict.
- Before: You might want to consider a modest increase.
- After: Raise to 1,250 for new clients. In plain cash the line is the stated share: lose a larger share of them and you take in less than today.

### Client loss without the cash line
- Watch for: "you could lose X% and still make the same", "losing some does not cost you", with no cash figure beside it.
- Why: it is only true if the freed hours are refilled. For a sole trader it misleads about next month's cash.
- Before: You could lose up to 51% of the clients on it and still make the same.
- After: In plain cash the line is 12%: lose a larger share and you take in less than today. Counting each freed hour at your 43, the line is 51%, but only if you refill those hours at your rate.

### Unsourced benchmarks
- Watch for: "industry standard", "most agencies charge", "the going rate", "healthy margins are 50 per cent", any percentage about other businesses.
- Why: invented or unsourced figures are the fastest way to lose a founder's trust, and they cannot be checked.
- Before: Most consultants aim for a 50 per cent margin.
- After: Your target margin is 20 per cent, the default; change it in the yellow cell if you aim higher.

### Competitor anchoring as the method
- Watch for: "a competitor charges X, so you should".
- Why: matching a competitor copies their pricing without their costs. A competitor's price is a data point beside the floor, never the floor.
- Before: Agency X charges 3,000, so price at 3,000.
- After: Your floor is 4,068. Agency X's 3,000 sits below it, so you win on what only you deliver, not on price.

### Framework name-dropping
- Watch for: "value-based pricing", "premium positioning", "Van Westendorp" with no figure attached.
- Why: a label in place of a number.

### Jargon in founder copy
- Watch for: "unit economics", "contribution margin", "CAC", "LTV", "overhead absorption" in the summary text.
- Why: the founder asked in plain words. Say "what one sale leaves after every direct cost" and "a share of your running costs".
- Note: the workbook may use the terms in its row labels, with plain words beside them.

### Promises of a result
- Watch for: "guaranteed", "you will make", "this will double".
- Why: the floor says what a price covers; it cannot promise demand.

### Soft verdicts
- Watch for: "it depends", "you could possibly", a verdict buried at the end.
- Why: the job is a verdict. Lead with Hold, Restructure or Raise, then the reason.

### Stating what a law requires
- Watch for: "you must register", "you need to charge", "the law requires", "you are legally required", a registration or sales tax threshold, a filing deadline, a named tax authority or a government website given as the source of a rule.
- Why: rules differ by country and change; the skill holds none of them. One neutral line, then the founder's accountant or lawyer.
- Before: Your sales pass the registration threshold, so you must register.
- After: Prices: read before any sales tax (VAT, GST or similar); ask your accountant whether you need to charge it.

### Computing tax or on-costs
- Watch for: an income tax, sales tax, social charge or employer cost worked out or estimated; "after tax you would take home"; a gross-up from take-home pay.
- Why: a regulated calculation outside this skill, and wrong for most founders somewhere. The founder supplies the before-tax figure or the full cost of an employee's hour from their accountant or payroll provider; the skill stores it as founder supplied and names who to confirm it with.
- Before: To take home 50,000 you need about 64,000 before tax.
- After: The floors need the pay before tax. Until you have it, the Raise verdicts stand and the rest are provisional; what you would pay someone capable to do your part settles them with no tax involved.

### Assuming a country
- Watch for: a currency the founder did not use, a holiday calendar ("bank holidays"), month-first dates or Letter paper for a founder outside the countries that use them, American spelling for a founder who does not write it, a figure retyped in another number style (1,200.50 for a founder who writes 1.200,50), a country named that the founder did not name, a country-specific payment method offered as the norm.
- Why: Merigrove's founders are in the US, Asia, Europe and the UK. A default that fits one country reads as careless to everyone else.
- Before: 46 working weeks (52 less holiday and bank holidays).
- After: Working weeks a year: 46 (assumption: 52 less 6 weeks off for your holidays and public holidays; set your own figure).

### Prose arithmetic
- Watch for: a figure in the chat or note that the script did not print (a sum, a difference, a rounded "about").
- Why: the model never counts by eye. `price_floor.py build --note` rejects any figure it did not compute.

### Verdicts presented as settled when they are not
- Watch for: "keep it", "hold", "no change needed" or a recommended restructure while the founder's pay figure is after tax; a chat "first move" that keeps a price the summary marks provisional.
- Why: a before-tax figure can only lift a floor, so a Hold or a Restructure on after-tax pay may be wrong; only a Raise is safe to act on.
- Before: Starter holds and Premium needs a 13% trim; keep 4,800 for now.
- After: Premium: at least 6,000 for new clients. Starter and Pro are provisional until your hour has a before-tax footing; what you would pay someone to do your part settles them.
