# Banned patterns

Each pattern: what to watch for, why it hurts, a before and an after. The Merigrove base list comes first, then this skill's cash list. `scripts/check_copy.py` catches what a script can catch; read the rest yourself before showing anything.

## Base list

### Em and en dashes
- Watch for: the long dashes used as clause breaks.
- Why: the clearest tell of machine-written copy.
- Before: Cash looks fine (dash) until the tax payment lands.
- After: Cash holds until 6 November. The 5,200 tax payment takes it under the line.

### Contrast reveal
- Watch for: "It's not X, it's Y."
- Why: a formula readers now recognise and discount.
- Before: It's not a sales problem, it's a timing problem.
- After: Alder's 4,200 lands three weeks after the tax payment leaves.

### Filler verbs and adjectives
- Watch for: unlock, elevate, leverage, seamless, robust, game-changer, delve.
- Why: they say nothing a competitor could not say.
- Before: Unlock a robust cash position.
- After: Keep $25,000 in the account through January 15.

### "More" as an intensifier
- Watch for: "more cash", "more headroom" with no number.
- Why: lazy and unprovable.
- Before: You need more headroom in November.
- After: In week 3 the balance is S$3,942 under the line.

### Announced honesty
- Watch for: "to be honest", "I mean", "let's be real".
- Why: implies the rest was not honest.

### Stock openers and exclamation marks
- Watch for: "In today's economy", "Good news!"
- Why: noise before the week the founder came for.

## This skill's list

### Comfort with no number
- Watch for: "healthy", "in good shape", "should be fine" or "should be ok", "nothing to worry about", "plenty", "safe", "no problem".
- Why: the founder came to stop guessing. A comfort word without the lowest balance and its week is a guess with better manners.
- Before: Your cash position looks healthy.
- After: The lowest point in a bad quarter is $10,910 in week 6, $7,477 above your line.

### Runway from the good case
- Watch for: "runway" quoted from the normal quarter, or with no case named.
- Why: runway is the question "how long if it goes wrong". The normal quarter cannot answer it.
- Before: You have 13 weeks of runway.
- After: Bad-quarter runway: 1 week before the balance crosses the line, against an 8-week minimum.

### A sale counted as cash
- Watch for: "you've got 6,000 coming from the Alder project" with no date, or receipts placed on the day the work was agreed.
- Why: the commonest cash forecasting failure. Cash is dated by when the client pays.
- Before: The Alder project brings in 4,200 this month.
- After: Alder's 4,200 is due on 30 October; they usually pay 21 days late, so it lands in week 5.

### Tax worked out by the skill
- Watch for: "you'll owe about 5,000 in tax", "set aside 20 per cent for tax", a sales tax or payroll tax figure, an employer cost, interest or a penalty that the founder or their accountant did not give.
- Why: the skill does no tax arithmetic. Tax figures are the founder's or their accountant's; a wrong tax figure is worse than a `[NEED]`.
- Before: You'll owe roughly 5,000 in sales tax in November.
- After: Sales tax due 30 November: [NEED: the figure from your accountant]. Your last payment in the export was 4,860.

### Stating what a law requires
- Watch for: "by law", "you are required to", "the deadline is", "the statutory rate", "penalties apply if", any claim about when a tax is due or what an authority will allow.
- Why: the skill is not a lawyer or an accountant, and the rules differ in every country the founder might be in. The founder lists the dates; the output names who to confirm them with.
- Before: Payroll taxes must legally be paid by the 15th.
- After: Payroll taxes: $1,870.40 on the 15th and the last day of each month, founder supplied (your payroll provider).

### Assuming a country
- Watch for: a currency sign, a date order, a tax name, a bank holiday, a tax year or an institution that the founder did not give; "UK banks write dates day first"; a bare "$" read as US dollars.
- Why: Merigrove's founders are in the US, Asia, Europe and the UK. A forecast in the wrong currency or date order is wrong in every row. `check_copy.py --currency` flags a foreign currency sign.
- Before: (to a Singapore founder) Your $26,000 from Marina Bay lands on 12/15.
- After: Your S$26,000 from Marina Bay Hotel lands on 15 December.

### Borrowing advice
- Watch for: "take an overdraft", "consider invoice finance", "a loan would cover it".
- Why: borrowing is a decision with costs the skill cannot see. It goes to the accountant, named once.
- Before: Consider an overdraft to bridge November.
- After: Talk to your accountant by 24 October about the 5,200 tax payment due 7 November.

### A hire answered with a feeling
- Watch for: "you can afford to hire", "it's safe to hire", "go for it".
- Why: the answer is yes, a later start date, or not yet, with the stress-case figure behind it.
- Before: You can afford the junior designer.
- After: Junior designer from 7 December: not yet. Starting on 4 January keeps a bad quarter above the line, with 8 weeks of the cost in hand.

### Vague timing
- Watch for: "soon", "next month", "around the end of the quarter", "early December".
- Why: the forecast's whole job is the week.
- Before: Cash gets tight around the end of the quarter.
- After: Week 3 (from 31 Oct) closes at 5,374.

### Prose arithmetic
- Watch for: a figure in the chat or note that the script did not print (a sum, a difference, an "about").
- Why: the model never counts by eye. `forecast.py build --note` rejects a figure or date it did not compute.

### Unsourced benchmarks
- Watch for: "most small businesses keep three months of cash", "the industry standard is", any percentage about other businesses.
- Why: invented or unsourced figures are the fastest way to lose a founder's trust. The defaults are working defaults, named as such.

### Jargon in founder copy
- Watch for: "DSO", "working capital", "liquidity", "burn", "AR", "AP" in the reading.
- Why: the founder asked in plain words. Say "how late clients pay", "cash in the bank", "money you are owed".
- Note: the workbook may use a plain label with no jargon at all; it does.

### Promotion in the founder's files
- Watch for: "Merigrove" or "Business Audit" in the workbook or the one-page reading.
- Why: the quality is the pitch. The one bridge line goes at the end of the chat.

### What a law or an authority requires
- Watch for: "must legally be paid", "the tax office requires", "required", "deadline", "mandatory", "by law".
- Why: the skill holds no country's rules. A due date or an obligation stated by the skill is legal advice it cannot stand behind.
- Before: The tax office requires the estimate by January 15.
- After: The $14,000 estimated tax you listed leaves on January 15 (founder supplied: your CPA).

### Claims about other businesses
- Watch for: "the norm", "industry average", "most small businesses", "typical for consultancies", "benchmark", "rule of thumb".
- Why: the forecast knows this business's own figures and nothing else. A benchmark it did not measure is an invented statistic.
- Before: Payroll at half of revenue is double the norm for consultancies.
- After: Payroll of $34,820 a month is the largest line; it leaves in weeks 2, 4, 6 and 8.
