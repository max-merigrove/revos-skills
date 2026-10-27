# Banned patterns

Each pattern: what to watch for, why it hurts, a before and an after. `scripts/check_review.py` checks every one it can. The Merigrove base list comes first, then this skill's own list.

## Base list

### Em and en dashes
- Watch for: the long dashes used as clause breaks.
- Why: the clearest tell of machine-written copy.
- Before: You priced early and it cost you.
- After: You priced early. It cost you the close.

### Contrast reveal
- Watch for: "It's not X, it's Y."
- Why: a formula readers now recognise and discount.
- Before: It's not a price problem, it's an order problem.
- After: The price was fine. It arrived before she had said what the problem costs.

### Filler verbs and adjectives
- Watch for: unlock, elevate, leverage, seamless, robust, game-changer, delve.
- Why: they say nothing a competitor could not say.
- Before: Leverage the discovery to unlock urgency.
- After: Ask what fifteen fewer bookings a week has cost her since spring.

### "More" as an intensifier
- Watch for: "ask more questions", "more rapport".
- Why: lazy and unprovable.
- Before: Ask more questions in discovery.
- After: After "bookings have dropped", ask "what has that cost you?" and wait.

### Announced honesty
- Watch for: "to be honest", "I mean", "let's be real".
- Why: implies the rest was not honest.

## This skill's list

### The compliment sandwich
- Watch for: "great job building rapport", "overall a solid call", "well done", "keep up the good work".
- Why: plain AI rounds every review up to be kind. A founder who hears "solid call" repeats it.
- Before: Overall a solid call with great rapport. A few areas for improvement.
- After: 36 out of 100. The price came before the cost, so she had nothing to set it against.

### Areas for improvement
- Watch for: "areas for improvement", "strengths and weaknesses", a list of eight tips.
- Why: a list nobody acts on. Two points with the words to say beat ten observations.
- Before: Areas for improvement: discovery, objection handling, closing, follow-up, confidence.
- After: Two things to change, each ending in the line to say.

### Behaviour-free coaching
- Watch for: "build rapport", "ask open-ended questions", "be more confident", "handle objections better".
- Why: it names a wish, not a behaviour. Nobody can rehearse "be more confident".
- Before: Be more confident when you give the price.
- After: Say the price once, stop, and count to five before you speak.

### Framework names at the seller
- Watch for: "your cost of inaction was weak", "work on your gap build", "use the loop", named sales methods.
- Why: labels are for the reviewer. The seller needs the behaviour and the words.
- Before: Your cost of inaction section needs work.
- After: You told her the number. Next time give her the parts and ask her to add them up.

### Blaming the prospect
- Watch for: "time waster", "tyre kicker", "she was never going to buy", "difficult prospect", "not serious".
- Why: it lets the call off the hook. A bad-fit prospect is a booking problem the founder can fix.
- Before: She was a tyre kicker who just wanted a price.
- After: She asked the price at minute 16 because nothing earlier had made the cost of the problem hers.

### Softened coaching
- Watch for: "perhaps", "it might be worth", "you might want to consider".
- Why: a coach who hedges is not heard.
- Before: You might want to consider asking about budget earlier.
- After: Ask who else decides in the first five minutes.

### A promise of a result
- Watch for: "you'll close the next one", "this will double your close rate".
- Why: unprovable, and it sets up the next review to fail.

### Quotes that are not quotes
- Watch for: a quotation in the review that is a paraphrase, or a time that is not on the transcript.
- Why: one invented quote and the founder stops trusting every finding.
- Fix: copy the words exactly from the turn the measure output names, or mark the review recall.

### Stating what a law requires
- Watch for: "it's illegal to record without consent", "under GDPR you must", "two-party consent", a named regulator, "ask a solicitor".
- Why: the founder and their prospect may be anywhere, and the skill gives no legal advice. A rule from one country is wrong in the next.
- Before: You can record as long as one party consents; ask a solicitor if unsure.
- After: Check the consent rules for recording calls where you and the prospect are.

### Working out tax
- Watch for: "plus 18% GST that's", "inc VAT it comes to", "after tax", "tax deductible".
- Why: tax depends on where the founder and the buyer are and on advice the skill does not have. The review shows the price exactly as it was said.
- Before: One and a half lakh plus 18% GST is 1,77,000 a month, so say that number.
- After: "It's one and a half lakh a month plus GST, three month minimum."

### Assuming a country
- Watch for: a currency symbol nobody said, dates in an order the founder does not use, British or American spelling the founder does not write, one country's rules or public holidays.
- Why: Merigrove's founders sell in many countries. A review in the wrong currency or date order reads as written for someone else.
- Before: (the founder wrote "3k or maybe 2.5k" and the call said "two thousand seven fifty") Price: 2,750 with a pound sign added because the call sounded British.
- After: Price: 2,750. No currency was said on the call or in your message, so none is shown.

## Held-out wording

Some phrasing and method from other sales training is never taught by this skill, in coaching, Say instead lines, drills or anywhere else. The register lives as data in `scripts/check_review.py`; a hit is always a problem, and the fix is to coach a different behaviour. A seller's own words quoted verbatim from the transcript are exempt, because the review may need to show what was said.
