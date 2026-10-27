# Banned patterns

Each pattern: what to watch for, why it hurts, a before and an after. The Merigrove base list comes first, then this skill's scope list, then the global rules (no law, no tax, no assumed country).

## Contents

Base list: dashes, contrast reveal, filler words, "more", announced honesty, stock openers. Scope list: regret, apology, refusal opener, legal words, blame, hedges, policy voice, legal claims, open-ended scope words, feelings as acceptance, retrospective billing, claims about other businesses, prose arithmetic. Global rules: stating what a law requires, computing tax, assuming a country, regional phrasing without a voice sample. `scripts/check_copy.py` catches the ones a script can catch (`--client` adds the client-message rules); read the rest yourself before showing anything.

## Base list

### Em and en dashes
- Watch for: the long dashes used as clause breaks.
- Why: the clearest tell of machine-written copy.
- Before: Happy to help (dash) it's a new piece though.
- After: Happy to help. It's a new piece rather than part of the plan.

### Contrast reveal
- Watch for: "It's not X, it's Y."
- Why: a formula readers now recognise and discount.
- Before: It's not a scope problem, it's a boundaries problem.
- After: Six of the last eight requests were new pieces of work.

### Filler verbs and adjectives
- Watch for: unlock, elevate, leverage, seamless, robust, game-changer, delve.
- Why: they say nothing a competitor could not say.
- Before: A seamless change process that elevates the partnership.
- After: A short note with the hours and price before any extra starts.

### "More" as an intensifier
- Watch for: "more work", "more value" with no figure.
- Why: lazy and unprovable.
- Before: They keep wanting more.
- After: Six extras since August, 14 hours.

### Announced honesty
- Watch for: "to be honest", "honestly", "I mean", "let's be real".
- Why: implies the rest was not honest.

### Stock openers and exclamation marks
- Watch for: "In today's busy world", "Great question!"
- Why: noise before the point.

## This skill's list

### Regret before a price
- Watch for: "unfortunately", "I'm afraid", "sadly".
- Why: it frames the price as bad news, which invites a haggle.
- Before: Unfortunately this falls outside our scope, so I'm afraid there will be a charge.
- After: It's a new piece rather than part of the plan: about six hours, £570.

### Apology
- Watch for: "sorry", "apologies", "I apologise" in any priced reply.
- Why: nobody apologises for having a price. An apology says the founder feels at fault.
- Before: Sorry to be a pain, but I'll need to charge for this one.
- After: Happy to. It's about four hours, so $480. Want me to go ahead?

### Refusal as the opening line
- Watch for: a first sentence that starts "This is outside", "That's not included", "We can't", "Out of scope".
- Why: the client reads the first line and stops. Start with yes to their goal.
- Before: This is outside our contract. If you want it, it costs £570.
- After: A spring landing page is a good idea. It's outside the monthly plan, so it's six hours, £570.
- After (US client): A holiday label is a great idea for the season. It's a fourth label on top of the three we planned, so it's about 10 hours, $1,200.

### Legal words in a client message
- Watch for: contract, clause, breach, terms and conditions, "per our agreement", "as per my last email".
- Why: they turn a conversation into a dispute. Say "what we agreed" or leave it out.

### Blame and telling-off
- Watch for: "scope creep", "you keep", "yet another", "once again", "every time you".
- Why: the ledger is the founder's, not a charge sheet for the client.

### Hedges that invite a no
- Watch for: "I hope that's OK", "if that's alright", "is that okay for you?", "would that be OK?", "does that make sense", "I'm just asking".
- Why: it asks permission for the price. End with a one-word next step instead.
- Before: Would that be OK? Totally understand if not.
- After: Want me to go ahead?

### Policy voice
- Watch for: "our policy", "company policy", "procedure requires".
- Why: the founder is a person; the client bought them.
- After: "The way I work is..."

### Legal claims about the scope
- Watch for: "legally binding", "enforceable", "watertight", "ironclad", "protects you legally", "you can sue".
- Why: the skill is not a lawyer and never says how wording would be read in law.
- After: "Draft for your own use. Have a lawyer read it before it goes into a contract."

### Open-ended scope words
- Watch for: "ongoing support", "as needed", "as required", "ad hoc", "unlimited", "general".
- Why: a deliverable without a number is where creep starts.
- Before: Ongoing social media support.
- After: 12 feed posts and 8 stories a month.

### Feelings as acceptance
- Watch for: "when the client is happy", "to the client's satisfaction", "until it's perfect".
- Why: "done" keeps moving. `scope_kit.py build` rejects these.
- After: "Approved by email, or five working days after delivery with no change request."

### Retrospective billing and threats
- Watch for: an invoice for past extras, "you owe", "we will have to take further action".
- Why: it costs the relationship more than the money and strays into legal territory. Reset forward instead.

### Claims about other businesses
- Watch for: "most clients accept", "most agencies charge", any percentage about other businesses.
- Why: unsourced, and the founder cannot check it.

### Prose arithmetic
- Watch for: a figure in a reply, the note or the chat that `compute` did not print.
- Why: the model never counts by eye. `scope_kit.py build` rejects any money, hours or percentage it did not work out.

### Stating what a law requires
- Watch for: "the law requires", "by law you must", "you are legally entitled", "under the [name] Act", "statutory" anything.
- Why: rules differ by country and change; the founder's clients are in many of them. The skill is planning, not legal advice. `check_copy.py` rejects these.
- Before: By law the client has to approve changes in writing.
- After: Work on a change starts once you approve it in writing; an email reply is enough. (The founder's own process, not a legal rule.)

### Computing tax
- Watch for: a with-tax figure ("£684 with VAT", "2.495 € brutto"), a tax rate ("plus 20% VAT", "GST at 9%", "zzgl. 19% MwSt."), "tax would be".
- Why: whether and how much sales tax applies is for the founder's accountant. `check_copy.py` rejects these.
- Before: It's £570 plus VAT, so £684 in all.
- After: It's £570 plus VAT, or 1.070 € netto. (Only when the founder writes their own fee that way, in their own words; otherwise just £570.) The kit carries: "Prices are before any sales tax (VAT, GST or similar); ask your accountant whether you need to charge it."

### Assuming a country
- Watch for: a currency, date style, working day or spelling the founder did not use; a named national tax authority or company registry; "in the UK you", "under US law"; a public holiday calendar.
- Why: Merigrove's founders are in the US, the UK, Asia, Australia and Europe. `check_copy.py` rejects "UK law", "under US rules" and similar; the script never defaults a currency or a date order.
- Before (a founder in Austin who bills in dollars and writes dates month first): It's 1,200 pounds, ready by 9 November.
- After: It's $1,200, and I can have it to you by 11/9.

### Regional phrasing without a voice sample
- Watch for: closes and idioms that read as one country's ("Shall I book it in?", "Cheers", "Good shout", "Awesome", "Y'all") when the founder gave no message to copy.
- Why: a reply that sounds foreign to the client reads as a template.
- After: "Want me to go ahead?", "Which works better for you?", "Thanks".
