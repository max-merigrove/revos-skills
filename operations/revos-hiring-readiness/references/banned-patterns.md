# Banned patterns

Each pattern: what to watch for, why it hurts, a before and an after. The Merigrove base list comes first, then this skill's hiring list. `scripts/check_copy.py` catches the ones a script can catch; `scripts/role_pack.py check` catches the job ad wording. Read the rest yourself before showing anything.

## Base list

### Em and en dashes
- Watch for: the long dashes used as clause breaks.
- Why: the clearest tell of machine-written copy.
- Before: The cash holds (dash) until the tax payment lands.
- After: The cash holds until the tax payment lands in week 12.

### Contrast reveal
- Watch for: "It's not X, it's Y."
- Why: a formula readers now recognise and discount.
- Before: It's not a hiring problem, it's a cash problem.
- After: The role is real. The bad quarter drops below your floor in week 12.

### Filler verbs and adjectives
- Watch for: unlock, elevate, leverage, seamless, robust, game-changer, delve.
- Why: they say nothing a competitor could not say.
- Before: Unlock your capacity with a seamless first hire.
- After: The hire takes 26 of your hours a week; two discovery calls a week go in their place.

### "More" as an intensifier
- Watch for: "more time", "more growth" with no number.
- Why: lazy and unprovable.
- Before: A hire gives you more time to sell.
- After: The role frees 26 of your hours a week.

### Announced honesty
- Watch for: "to be honest", "I mean", "let's be real".
- Why: implies the rest was not honest.

### Stock openers and exclamation marks
- Watch for: "In today's fast-paced world", "Great news!"
- Why: noise before the verdict the founder came for.

## This skill's list

### Affordability promises
- Watch for: "you can definitely afford it", "you can comfortably afford", "you can afford to hire".
- Why: affordability is a scenario with a bad quarter in it, not a feeling. A founder hears permission.
- Before: You can definitely afford a part-time hire.
- After: Ready. The bad quarter holds above your $14,400 floor in every week to the hire's 13th, with the hire loaded.

### Hiring cheerleading
- Watch for: "invest in yourself", "take the leap", "go for it", "just hire".
- Why: the founder came tired and wanting a yes. The skill's value is a straight answer.

### Readiness dates
- Watch for: "you'll be ready by March", "in three months you can hire", "ready by spring".
- Why: a date is a forecast the check cannot make. A condition the founder can test is honest and useful.
- Before: You should be ready to hire by February.
- After: Not yet. An extra $3,855 in the bank before the start, or a start on or after February 2, 2027 if revenue and costs hold at today's figures.

### Computing tax or employer charges
- Watch for: any rate applied to pay ("payroll taxes at 7.65%", "employer contributions of 17%"), "your hire will cost about", any on-cost the skill worked out. `check_copy.py` refuses a line that puts a rate on an employer charge or tax.
- Why: the rules differ by country, state and person, and change. An estimate the founder acts on becomes a payroll surprise. The cost is the founder's fully loaded figure from their accountant or payroll provider.
- Before: Employer taxes on $36,000 come to about $2,750, so budget $3,230 a month.
- After: The scenario uses $3,000 a month, which is pay alone and understates the hire. Ask your accountant or payroll provider for the fully loaded monthly cost.

### Pay alone passed off as the full cost
- Watch for: a salary-only run with no "understates" line, or a Ready on it.
- Why: the founder reads the month-three figure as safe when it is not.
- After: "These figures carry pay alone, so they understate the cost of the hire."

### Stating what a law requires
- Watch for: "the law requires", "you are legally required to", "it is illegal to", "you must by law", any minimum wage, leave entitlement or registration rule.
- Why: the skill cannot see where or how the founder hires, and it is not a lawyer. `check_copy.py` refuses these.
- After: "Check the employment and anti-discrimination rules where you hire with an employment lawyer or adviser there."

### Judging employee or contractor status
- Watch for: "she would be a contractor", "they count as self-employed", "so you don't need payroll".
- Why: status turns on facts and law the skill cannot see. `check_copy.py` refuses these.
- After: "Whether this person would be an employee or a contractor is not something this check decides. Ask your accountant, payroll provider or an employment lawyer where you hire."

### Assuming a country
- Watch for: a currency symbol, date order, spelling, tax body, scheme, form or rate the founder did not use; a UK payroll scheme named to a founder in Texas. `check_copy.py` warns on country-specific terms; treat each warning as a problem unless the founder used the word.
- Why: Merigrove's founders are in the US, Asia, Europe and the UK. A country assumed is a sign the output was not written for them.
- Before: "£2,500 a month from 17 November" to a founder who wrote "$2,500, start Dec 1".
- After: "$2,500 a month from December 1, 2026."

### Advice with no figure
- Watch for: "consider hiring", "you might want to", "it depends".
- Why: a verdict without a number is not a verdict.

### Unsourced benchmarks
- Watch for: "most founders hire too early", "a healthy margin is", any percentage about other businesses.
- Why: invented or unsourced figures cannot be checked. Every default is named as a default, never as a fact about others.

### Recruitment cliches and coded words
- Watch for: rockstar, ninja, fast-paced, work hard play hard, passionate, self-starter, digital native, young team, native English speaker, citizens only. Full list in `role-pack.md` section 3.
- Why: they describe a person, not the work, put good applicants off, and in many places are restricted.
- Before: Passionate self-starter to join our young, fast-paced team.
- After: Own client onboarding: every new client welcomed within 24 hours.

### Diagnosing the founder
- Watch for: "you're burnt out", "you're overwhelmed".
- Why: use the founder's own words if they gave them; never a diagnosis.

### Prose arithmetic
- Watch for: a figure in the chat or note that the scripts did not print.
- Why: the model never counts by eye. `build.py --note` refuses a note with a figure the results do not hold.
