# Banned patterns

Each pattern: what to watch for, why it hurts, a before and an after. The Merigrove base list comes first, then this skill's list. `scripts/check_copy.py` catches what a script can catch, on everything Claude writes (core lines, reasons, edits, the decision). The founder's quotes are theirs and are never checked or changed.

## Base list

### Em and en dashes
- Watch for: the long dashes used as clause breaks, in anything you write.
- Why: the clearest tell of machine-written copy.
- Before: Your website says one thing (dash) your proposal another.
- After: Your website says one thing. Your proposal says another.

### Contrast reveal
- Watch for: "It's not X, it's Y."
- Why: a formula readers recognise and discount.
- Before: It's not a design problem, it's a positioning problem.
- After: Your proposal sells paid social; your LinkedIn sells a fractional CMO.

### Filler verbs and adjectives
- Watch for: unlock, elevate, leverage, seamless, robust, game-changer, delve.
- Why: they say nothing a competitor could not say.
- Before: Elevate your brand story.
- After: Change the website hero to "Fractional CMO for B2B SaaS founders".

### "More" as an intensifier
- Watch for: "more consistent", "more clients" with no comparison.
- Why: lazy and unprovable.
- Before: Make your messaging more consistent.
- After: Two of your three assets now name the same buyer.

### Announced honesty
- Watch for: "to be honest", "I mean", "let's be real", "honestly".
- Why: implies the rest was not honest.

### Stock openers and exclamation marks
- Watch for: "In today's competitive market", "Great news!"
- Why: noise before the finding.

## This skill's list

### The upbeat summary
- Watch for: "Overall your messaging is consistent, but you could strengthen..."
- Why: it is what plain AI writes, and it tells the founder nothing they can act on.
- Before: Overall your messaging is consistent, with some room to tighten.
- After: Your proposal and your website give different answers to what you do.

### Verdicts with no quote
- Watch for: "your messaging could be stronger", "strengthen your positioning", "cohesive" with nothing behind it.
- Why: a finding without the two quotes is an opinion.
- Before: Your brand feels a little disjointed.
- After: Website: "ambitious brands". LinkedIn: "B2B SaaS founders". Proposal: "your team is stretched".

### Edits that are not lines
- Watch for: "consider clarifying", "make it clearer", "tighten the hero", "you might want to".
- Why: the founder still has to write the line. The scan's job is to write it.
- Before: Consider clarifying who you serve on the website.
- After: Now "Growth marketing for ambitious brands." Change to "Fractional CMO for B2B SaaS founders who are still running marketing themselves."

### Added claims
- Watch for: a result, a figure, a client count or a credential in a core line or edit that no asset states.
- Why: the scan aligns what the founder already says; it never invents proof. `build_report.py` refuses figures the assets do not hold.
- Before: Founders see pipeline double in 90 days.
- After: I report to you on pipeline, not likes. [NEED: a client result you may publish]

### Stock lines a competitor could sign
- Watch for: "tailored solutions", "trusted partner", "results-driven", "passionate about", "help businesses grow", "one-stop shop".
- Why: a core line that fails "could only you say it" will not survive a buyer comparing three suppliers.

### Jargon in founder copy
- Watch for: "value proposition", "USP", "brand architecture", "brand equity", "on-brand".
- Why: the founder asked in plain words. Say "why buyers choose you", "what you do".

### Promises of a result
- Watch for: "guaranteed", "will double", "10x".
- Why: the scan reads messaging; it cannot promise what aligning it will earn.

### Unprovable reader claims
- Watch for: "resonates with your audience", "compelling".
- Why: nobody can check them.

### Stating what a law requires
- Watch for: "you are legally required to", "the law says", "it is illegal to", "you must register for", "GDPR compliant", "FDA approved". A credential the founder holds and states ("ICF certified", "FSC certified", "ISO 9001 certified") is a fact, not a compliance claim: keep it where the assets state it, and never add one they do not (`build_report.py` refuses a credential no asset names). A compliance phrase the founder's own assets already use is theirs and may stay in an edit of that line.
- Why: the scan reads messaging. Rules differ by country, and a wrong one costs the founder money. `check_copy.py` refuses these lines.
- Before: You are legally required to show prices including sales tax on your website.
- After: Your website shows a price; your proposal does not. [NEED: whether you show prices publicly at all]

### Computing or stating tax
- Watch for: a tax rate of any kind, "plus 20% tax", "sales tax at 8%", a price with tax worked out.
- Why: tax depends on where the founder and the buyer are, and is a question for their accountant. Prices in an edit are quoted from the founder's assets as they wrote them, or not at all.
- Before: 2,500 a month plus 20% tax, so 3,000.
- After: (no price in the edit; the website already states its own)

### Assuming a country
- Watch for: a country, region or currency ("nationwide", "across the US", "in pounds", "dollars") that the founder's assets never mention.
- Why: Merigrove's founders are in the US, Asia, Europe and the UK. A line that names a market the founder never named is invented, and it reads as if written for someone else. `build_report.py` refuses a country, currency word or symbol in Claude's copy that no asset contains.
- Before: Fractional CMO for B2B SaaS founders across Europe.
- After: Fractional CMO for B2B SaaS founders between seed and Series A.

### The other English
- Watch for: "colour" for a founder who writes "color", "optimize" for one who writes "optimise".
- Why: an edit spelt differently from the asset it lands in is the first thing a careful buyer notices. `voice_drift.py` counts the founder's spelling; `build_report.py` refuses the other form.
