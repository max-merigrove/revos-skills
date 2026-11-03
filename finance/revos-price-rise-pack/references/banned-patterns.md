# Banned patterns

Each pattern: what to watch for, why it hurts, a before and an after. The base list comes first, then this skill's price rise list. `scripts/check_copy.py` checks every one it can (`--letters` adds the price rise list).

## Base list

### Em and en dashes
- Watch for: long dashes used as clause breaks.
- Why: the clearest tell of machine-written copy.
- Before: The new fee starts in January and it covers the same work.
- After: The new fee starts in January. It covers the same work.

### Contrast reveal
- Watch for: "It's not X, it's Y."
- Why: a formula readers recognise and discount.
- Before: It's not a price rise, it's an investment in quality.
- After: From 1 January 2027 your fee is 2,150 a month.

### Filler words
- Watch for: unlock, elevate, leverage, seamless, robust, game-changer, delve.
- Why: they say nothing a competitor could not say.
- Before: This lets us deliver seamless, elevated service.
- After: Everything else stays as it is.

### "More" as an intensifier
- Watch for: "more value", "more support" with no number.
- Why: lazy and unprovable.
- Before: You'll get more from the retainer.
- After: The retainer covers 12 hours a month, as now.

### Announced honesty
- Watch for: "to be honest", "I mean", "let's be real".
- Why: it implies the rest was not honest.

### Stock openers, exclamation marks, vague superlatives, unsourced statistics
- Why: generic, and a claim with no source cannot be checked.

## This skill's list

### Minimising the rise
- Watch for: "small adjustment", "slight increase", "pricing adjustment".
- Why: the client sees the figure; calling it small reads as a trick and invites a haggle.
- Before: We're making a small pricing adjustment.
- After: From 1 January 2027, your fee will be 2,150 a month, up from 1,800.

### Apology
- Watch for: "unfortunately", "regrettably", "we hate to", "I'm sorry", "I hope you understand".
- Why: an apology tells the client the fee is negotiable and that the founder doubts it.
- Before: Unfortunately, I've had to raise my prices. I hope you understand.
- After: New clients now pay 3,000 a month for about 12 hours, which is 250 an hour; your work runs to about 14 hours a month.

### Stock phrases
- Watch for: "valued client", "reaching out", "going forward".
- Why: form-letter words on a letter that should sound like one person to another.
- Before: As a valued client, I'm reaching out to let you know that going forward...
- After: Hi Sarah, from 1 January 2027 your fee will be...

### A cost reason with no figure
- Watch for: "due to rising costs", "costs have gone up", "inflation", "the cost of living", without the founder's own number.
- Why: the weakest reason, because the client cannot check it, and an invented one is untrue.
- Before: Due to rising costs, fees are increasing.
- After: (founder gave a figure) My design software went from 400 to 520 a month this year. (no figure) Use another true reason, or state the change with none.

### Borrowed authority
- Watch for: "industry standard", "market rate", "the going rate", "everyone is raising", "every agency is doing it".
- Why: unsourced, and a client can ask for the source.
- Before: Every agency in Sydney is raising prices this year.
- After: New clients now pay 1,900 a month.

### Blaming a third party
- Watch for: "the government", "the new wage rise", "new regulations", a supplier.
- Why: untrue unless the founder gave the figure, and it hands the client a reason to argue.
- Before: Because of the new government wage rise...
- After: My fees have not changed in four years.

### No notice and false urgency
- Watch for: "effective immediately", "with immediate effect", "limited time", "last chance", "act now", a deadline to accept, a backdated date.
- Why: it breaks the founder's own notice terms and turns a fair change into pressure.
- Before: Effective immediately, and please confirm by Friday.
- After: From 1 January 2027... If you would like to talk it through, reply before 18 December 2026.

### A discount for nothing
- Watch for: "loyalty discount", "as a thank-you we'll knock off", any concession with no end date.
- Why: an exception given for nothing becomes the new price.
- Before: As a loyal client you'll get 10% off the new rate.
- After: If you confirm the next twelve months by 18 December, today's fee holds until 31 March 2027.

### A reason that is false for this client
- Watch for: the new-client price given as the reason for a fee above it; a scope line about the client ("they always send extra requests") pasted into a letter to them.
- Why: the client sees a rise justified by a lower price, or reads a note about themselves. `letters.py check` fails both.
- Before: New clients now pay 2,800 a month. (to a client raised to 3,550 for 22 hours) / The work has grown: they always send extra requests.
- After: New clients now pay 2,800 a month for about 14 hours, which is 200 an hour; your work runs to about 22 hours a month. / The work has grown since we set your fee: you often send extra requests.

### "Investment" for a fee
- Watch for: "your investment" meaning the fee, unless the founder uses the word themselves.
- Why: a euphemism clients notice.
