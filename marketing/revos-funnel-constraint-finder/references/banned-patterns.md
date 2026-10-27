# Banned patterns

Each pattern: what to watch for, why it hurts, a before and an after. The Merigrove base list comes first, then this skill's funnel list. `scripts/check_copy.py` catches the ones a script can catch; read the rest yourself before showing anything.

## Base list

### Em and en dashes
- Watch for: the long dashes used as clause breaks.
- Why: the clearest tell of machine-written copy.
- Before: Your show rate is the problem (dash) not your leads.
- After: Your show rate is the constraint. Your leads are not.

### Contrast reveal
- Watch for: "It's not X, it's Y."
- Why: a formula readers now recognise and discount.
- Before: It's not a lead problem, it's a show-up problem.
- After: 19 of 40 booked calls happened. That is where the clients go.

### Filler verbs and adjectives
- Watch for: unlock, elevate, leverage, seamless, robust, game-changer, delve, supercharge, skyrocket.
- Why: they say nothing a competitor could not say.
- Before: Unlock your funnel's potential.
- After: Lifting the show rate to 60% adds 0.79 clients a month.

### "More" as an intensifier
- Watch for: "more leads", "more sales", "more growth" with no number.
- Why: lazy, and in this skill it is usually the wrong answer.
- Before: You need more leads.
- After: Each extra client needs about 11 enquiries at your own rates.

### Announced honesty
- Watch for: "to be honest", "I mean", "let's be real", "honestly".
- Why: implies the rest was not honest.

### Stock openers and exclamation marks
- Watch for: "In today's competitive market", "Great news!"
- Why: noise before the number the founder came for.

## This skill's list

### Funnel cliches
- Watch for: "leaky bucket", "leaky funnel", "plug the leaks".
- Why: a picture with no stage and no number in it.
- Before: Your funnel is a leaky bucket.
- After: 21 of 40 booked calls never happened.

### Optimise everything
- Watch for: "optimise every stage", "optimise your funnel".
- Why: the method is that only one stage matters this month.
- Before: Optimise each stage of your funnel.
- After: Fix the show rate this month. Leave the rest alone.

### Invented benchmarks
- Watch for: "industry average", "typical conversion rate", "most coaches convert", "a healthy close rate is", "80% of leads never buy".
- Why: no such figure is held for most stages, and an unsourced number is the fastest way to lose a founder's trust.
- Before: The average conversion rate for coaches is 3%.
- After: Your enquiry to booked call rate is 25%. That is your baseline; your own best two months is the test.

### Volume as the reflex
- Watch for: "just get more leads", "more leads", "scale your ads".
- Why: buying leads into a stage that loses them pays for the loss.
- Before: Get more leads to grow.
- After: Hold lead spend until the show-rate fix has run for 30 days.

### Blended rates
- Watch for: "overall conversion rate", "blended close rate", a rate that mixes referral and cold enquiries without saying so.
- Why: it hides the route that works.
- Before: Your overall conversion is 9%.
- After: These counts mix referrals and website enquiries; tag the source on every enquiry so the next run can split them.

### The biggest drop-off as the answer
- Watch for: "the biggest drop is at the top, so focus on awareness".
- Why: the largest drop is nearly always audience to enquiry; it says nothing about where effort pays.
- After: name the stage with the largest prize, with its working.

### Ten tips
- Watch for: a list of tactics, "here are some ideas", more than three actions.
- Why: the founder came for one constraint and one fix.

### Jargon
- Watch for: TOFU, MOFU, BOFU, AARRR, CAC, LTV, CRO, MQL, SQL in the report.
- Why: the founder asked in plain words.

### Promises
- Watch for: "guaranteed", "you will double", "this will get you".
- Why: the prize is arithmetic on today's rates, not a forecast.
- After: "Lifting that stage alone to 60% adds 0.79 clients a month at your own close rate."

### Soft verdicts
- Watch for: "it depends", "you might want to", "consider looking at".
- Why: the job is a verdict. Lead with the constraint, then the reason.

### Prose arithmetic
- Watch for: a figure in the chat or note the script did not print ("about a third", a sum, a rounded total).
- Why: the model never counts by eye. `funnel.py build --note` refuses any figure it did not work out.

### Stating what a law requires
- Watch for: "the law requires", "you are legally obliged", "under GDPR you must", any named regulator or statute.
- Why: rules differ by country and by who the contact is; this skill gives no legal advice (Build Standard 0.1).
- Before: Under the regulations you must get consent before emailing past enquiries.
- After: Before you message past enquiries, check the rules on contacting people where you and they are.

### Computing tax
- Watch for: a sales tax, VAT, GST or income tax figure; "add 20% VAT"; prices shown including tax.
- Why: tax depends on the founder's country and registration; their accountant supplies it.
- Before: At your £1,450 package plus VAT, that is £1,740 a client.
- After: Prices are before any sales tax (VAT, GST or similar); ask your accountant whether you need to charge it.

### Assuming a country
- Watch for: a currency symbol the founder did not use, "bank holiday", day-first dates for an American founder, A4 for a Canadian, a Monday to Friday week stated as fact.
- Why: Merigrove's founders are in the US, Asia, Europe and the UK; a wrong symbol or date says the report was not made for them.
- Before: (to a founder in Austin) about £2,800 a month, by 19 December 2026.
- After: about $2,800 a month, by December 19, 2026.
- `funnel.py build` stops until the country and currency are known, and refuses a note in another currency.

### Merigrove inside the file
- Watch for: Merigrove, the Business Audit, or an internal source name in the report.
- Why: the report is the founder's to share. The one Merigrove line belongs at the end of the chat.
