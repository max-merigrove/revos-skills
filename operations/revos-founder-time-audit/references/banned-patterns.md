# Banned patterns

Each pattern: what to watch for, why it hurts, a before and an after. The Merigrove base list comes first, then this skill's list. `scripts/check_copy.py` catches the ones a script can catch; read the rest yourself before showing anything.

## Base list

### Em and en dashes
- Watch for: the long dashes used as clause breaks.
- Why: the clearest tell of machine-written copy.
- Before: Your week is full (dash) mostly of admin.
- After: Your week is full. Admin is 31% of it.

### Contrast reveal
- Watch for: "It's not X, it's Y."
- Why: a formula readers now recognise and discount.
- Before: It's not a time problem, it's a delegation problem.
- After: Jo could take 6.8 hours a week of it, inside her spare hours.

### Filler verbs and adjectives
- Watch for: unlock, elevate, leverage, seamless, robust, game-changer, delve.
- Why: they say nothing a competitor could not say.
- Before: Unlock seamless productivity.
- After: Cancel the Tuesday status call and get 4.3 hours a month back.

### "More" as an intensifier
- Watch for: "more time", "more focus" with no number.
- Why: lazy and unprovable.
- Before: Get more time for sales.
- After: The changes free 9.5 hours a week; the week below puts them into selling.

### Announced honesty
- Watch for: "to be honest", "I mean", "let's be real", "honestly".
- Why: implies the rest was not honest.

### Stock openers and exclamation marks
- Watch for: "In today's busy world", "Great news!"
- Why: noise before the number the founder came for.

## This skill's list

### Productivity platitudes
- Watch for: "work smarter, not harder", "hustle", "grind", "time is money", "eat the frog", "level up", "10x".
- Why: the founder came for their own hours, not a slogan.
- Before: Work smarter, not harder, and protect your time.
- After: Mondays from 9 to 1 are your strategy block. Nothing else goes in it.

### Framework name-dropping
- Watch for: "Eisenhower matrix", "Pareto", "80/20", "Pomodoro", "time-blocking" with no figure attached.
- Why: a label in place of the founder's own numbers. Plain Claude already gives this.
- Before: Use the Eisenhower matrix to sort your tasks.
- After: Client reporting is 10.8 hours a month someone could do with instruction. Jo takes it first.

### Easy tasks first
- Watch for: "quick wins", "low-hanging fruit", "start small", "start with the easy ones".
- Why: handing over small tasks frees little and teaches the founder that delegation fails. The method ranks by hours a month.
- Before: Start with a quick win like booking travel.
- After: Start with quotes and admin: 13 hours a month, the largest block someone else could take.

### Recommending a hire
- Watch for: "you should hire a VA", "time to recruit", "hire an ops manager".
- Why: whether the business can afford a person is a cash question this audit does not answer. Name the hours; leave the decision with the founder and their numbers.
- Before: You should hire a part-time designer.
- After: Design production is 16.4 hours a week someone could do with instruction. That is the shape of a role, and a cash question before it is a hiring one.

### Advice with no ranking
- Watch for: "delegate everything", "just delegate", "outsource your admin", "automate what you can".
- Why: a list with no order and no hours is the generic answer.
- Before: Outsource your admin and automate what you can.
- After: Invoicing and chasing is 6.5 hours a month and rule-based: let your accounting software send reminders, and Jo sends the invoices.

### Time shown as cash
- Watch for: "saves you $4,560", "worth S$2,261 to you" with no basis or condition.
- Why: freed hours earn nothing unless they go into paid or selling work. Reading time as cash misleads a founder about next month's bank balance.
- Before: This saves you $4,560 a month.
- After: At $175 an hour (your monthly sales over your hours) that time is worth $4,560 a month, if it goes into selling and earns at that rate.

### Promises of a result
- Watch for: "you get back", "you will get back", "you'll save", "guaranteed", "this will free up".
- Why: the audit says where the hours are; whether they come back depends on the handover holding.
- Before: Stop the one deletion and hand over the top five and you get back 66.4 hours a month.
- After: The one deletion and the top five handovers hold 66.4 hours a month of your time.

### Unsourced claims about other founders
- Watch for: "most founders spend", "studies show", "the average founder".
- Why: invented or unsourced figures lose trust and cannot be checked. Use this founder's own hours.

### Wellbeing cliches in place of figures
- Watch for: "work-life balance", "self-care", "avoid burnout".
- Why: the founder knows they are tired. Show them the 12.5 hours beyond their working day and where it comes from.

### Internal jargon
- Watch for: "category one", "category two", "T flag", "Doing share" without explanation.
- Why: say "only you can do", "someone could do with instruction", "nobody should be doing", "delivery and admin".
- Note: the workbook may use short labels in its columns.

### Naming personal entries
- Watch for: a dentist, a school run, a medical appointment or a family event named in any file or in chat.
- Why: the founder's calendar is private. Say "5 personal entries left out", never what they were.

### Stating what a law requires
- Watch for: "the law requires", "you must register", "you are legally required to", the name of one country's employment or tax test, any rule from one country.
- Why: the audit is a planning tool for founders in many countries. A rule stated for one country is wrong for the others and is advice the skill is not qualified to give.
- Before: Jo is self-employed, so you don't need to run payroll for her.
- After: Whether Jo is an employee or a contractor depends on the rules where you both work; ask your accountant or an employment adviser.

### Computing tax, payroll or on-costs
- Watch for: a helper's cost worked out from a salary plus employer taxes, pension or super, a rate "including VAT", or a sales tax figure.
- Why: those figures depend on the country and the person. The founder gives what a person costs them an hour; the audit uses it as given.
- Before: Marcus costs about $52 an hour once payroll taxes are added.
- After: Marcus's time on three of them costs $926 a month at $45 an hour (the figure you gave).

### Assuming a country
- Watch for: one country's holiday name, tax authority, government website or advisory body; a single country's word used as if every founder says it; pounds or day-first dates for a founder who writes in dollars and month first; a Monday to Friday week for a founder who works Sunday to Thursday; Letter paper or a 12-hour clock inferred from American spelling (paper and clock follow the country, not the spelling); figures written 1,234.5 to a founder who writes 1.234,5.
- Why: Merigrove's founders are in the US, Asia, Australia, Europe and the UK. Currency, dates, spelling, working week and holidays follow the founder.
- Before: Monday 5 October was a bank holiday, so the week is short.
- After: Monday 5 October is marked in your calendar as a public holiday (Labour Day), so the week may be lighter than usual.

### Prose arithmetic
- Watch for: a figure in the note or chat that the scripts did not print (a sum, a difference, an "about").
- Why: the model never counts by eye. `report.py --note` and `reconcile.py --summary` reject figures they did not compute.
