# Banned patterns

Each pattern: what to watch for, why it hurts, a before and an after. `scripts/check_copy.py` enforces every one it can detect; the rest are for the read-aloud pass. Before and after lines are illustrative.

## Base list

### Em and en dashes
- Watch for: long dashes as clause breaks.
- Why: the clearest tell of machine-written copy.
- Before: I sent the proposal in May and then nothing came back.
- After: I sent the proposal in May. Nothing came back.

### Contrast reveal
- Watch for: "It's not X, it's Y."
- Why: a formula readers discount.
- Before: It's not a sales email, it's a genuine question.
- After: One question, and either answer helps me.

### Filler verbs and adjectives
- Watch for: unlock, elevate, leverage, seamless, robust, game-changer, delve, synergy.
- Why: they say nothing a competitor could not say.
- Before: Let's unlock the potential of your brand.
- After: Is the rebrand still on your list?

### "More" as an intensifier
- Watch for: "more clients", "more growth" with nothing to compare.
- Why: lazy and unprovable. ("Any more" and "no more" in their plain sense are fine.)

### Announced honesty
- Watch for: "to be honest", "honestly", "I mean", "let's be real".
- Why: implies the rest was not honest.
- Before: To be honest, I dropped the ball.
- After: That one was on my list to follow up.

### Exclamation marks and emoji
- Why: they read as a campaign, not a person, in a message to someone who went quiet.

## This skill's list

### "Just checking in" and friends
- Watch for: just checking in, circling back, touching base, bumping this, following up on my last email, any update, per my last, friendly reminder, gentle nudge.
- Why: the most deleted lines in sales email; they ask the reader to do the work of remembering.
- Before: Just checking in to see if there's any update on the proposal.
- After: I never found out where the May proposal landed. Did it get shelved?

### "I hope this finds you well"
- Watch for: any hope-you're-well opener.
- Why: filler before the point; marks the message as a template.
- Before: I hope this email finds you well.
- After: (Delete it. Start with the reason to write.)

### Guilt openers
- Watch for: I never heard back, you never replied, haven't heard from you, I noticed you haven't.
- Why: blames the reader; nobody replies to an accusation.
- Before: I never heard back after my last three emails.
- After: It's been a while since we spoke in March.

### "We miss you"
- Why: a mass-mail line; nobody believes a business misses them.

### Fake personalisation
- Watch for: I came across your profile, saw your post, was looking at your website.
- Why: the skill looks nothing up, so any such line is invented.

### "Reaching out"
- Watch for: I'm reaching out, reaching out to, reaching out because.
- Why: a verb of first resort that signals a sequence.
- Before: I'm reaching out to reconnect.
- After: You'd said to try again after the summer.

### Urgency and scarcity the founder did not give
- Watch for: last chance, limited time, final reminder, before it's too late, don't miss out, only N left, expires, ends Friday, today only, act now, hurry.
- Why: false urgency to someone who went quiet ends the relationship. The close-the-file message never threatens or stages scarcity.
- Before: Final reminder: this offer expires Friday.
- After: I won't write again. If it comes back round, reply and we'll pick it up.

### Discounts, bonuses, deadlines the founder did not give
- Watch for: discount, % off, special offer, free bonus.
- Why: never invent an offer; never cut a price in writing.

### An apology the founder did not make
- Watch for: sorry to bother you, apologies for the silence, that's on me, my bad.
- Why: the skill must not put words in the founder's mouth. "That was on my list" is fine where the notes say the founder dropped it.

### "Quick question" subjects and fake replies
- Watch for: subject "Quick question" with nothing behind it; "Re:" or "Fwd:" on a new message; "Checking in" as a subject.
- Why: tricks are noticed, and a trick in message one poisons the rest.

### The no-oriented question too early
- Watch for: "Have you given up on...?", "Have you decided not to...?" in touch 1 or 2, or outside the went-quiet-after-a-proposal group.
- Why: it works as a late nudge for someone who saw a proposal; as an opener it reads as a guilt trip.

### Statements about law
- Watch for: GDPR, CAN-SPAM, "compliant", "legally", "the law says".
- Why: the skill states no rule. One generic line points the founder to the rules where they and their contacts are.

### Tax or accounting advice in a message
- Watch for: tax deductible, save tax, you can claim, a tax rate.
- Why: outside scope, and wrong for most readers somewhere.

### Pointed lines
- Watch for: remarks on how long they took ("two summers have gone by", "a year has passed"), "only ever", "I'm asking properly", "those numbers are long in", "as I was told".
- Why: to someone who went quiet, a dig reads as resentment and ends the conversation.
- Before: Two summers have gone by since.
- After: You'd wanted to wait until after the summer. Is now a better time?

## Messages in another language

`check_copy.py` runs only the checks that do not depend on English when `message_language` is not English (length, one question, money and prices, the opt-out line, quotations, fields, dashes, exclamation marks, emoji). Every pattern above still applies to the meaning: no "just checking in" ("ich wollte nur mal nachhaken", "je me permets de revenir vers vous"), no guilt opener, no urgency, no apology the founder did not make, no pitch in touch 1. Read each message against this list yourself before building, and say in the chat that you did.

