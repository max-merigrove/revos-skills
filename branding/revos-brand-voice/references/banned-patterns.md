# Banned patterns

Two jobs here. The base list keeps the skill's own writing (the guide's prose, the PASTE file, the calibration samples, the chat summary) out of the generic AI house style. The second list names the ways voice guides and voice prompts fail, so this skill's output does not. `scripts/check_copy.py` checks the base list on any text; `scripts/voice_stats.py compare` and `check-guide` check the measurable ones.

Contents: Base list (dashes, contrast reveal, filler, "more", announced honesty, stock openers, exclamations and emoji, vague superlatives); This skill's list (adjectives as rules, counting by eye, a borrowed voice, invented Do lines, performative tics, generic prompt language, flattening quirks, absence turned into law, dead registers, prompts that invite invention, rates in a prompt, custom instructions that take over, correcting the founder's English, naming a country from spelling, idioms the founder never uses, converted money and dates); Every Merigrove skill (stating what a law requires, computing tax, assuming a country).

## Base list

### Em and en dashes
- Watch for: the long dashes used as clause breaks.
- Why: the clearest tell of machine-written copy. The skill never writes one, even where the founder does (method section 18).
- Before: Our quotes take ten days, and that is the point.
- After: Our quotes take ten days. That is the point.

### Contrast reveal
- Watch for: "It's not X, it's Y", "This isn't X. It's Y."
- Why: a formula readers now recognise and discount.
- Before: It's not a kitchen, it's the heart of your home.
- After: It's where the post lands, the dog sleeps and the homework gets done.

### Filler verbs and adjectives
- Watch for: unlock, elevate, leverage, seamless, robust, game-changer, delve, empower, harness, journey, transformative.
- Why: they say nothing a competitor could not say.
- Before: We unlock seamless IT for your practice.
- After: The X-ray PC boots before the first patient at 8.15.

### "More" as an intensifier
- Watch for: "more clients", "more growth" with no number or comparison.
- Why: lazy and unprovable.
- Before: Get more done with fewer headaches.
- After: Two failing hard drives replaced before they failed.

### Announced honesty
- Watch for: "to be honest", "if I'm being honest", "honestly,", "I mean", "let's be real".
- Why: implies the rest was not honest. If the founder uses one, it is an edge case they decide (method section 18).

### Stock openers and closers
- Watch for: "In today's fast-paced world", "In a world where", "Here's the thing", "Let that sink in", "I hope this finds you well", "Just following up", "Don't hesitate to reach out", "In conclusion".
- Why: each one tells the reader nobody in particular wrote this.
- Before: I hope this email finds you well. Just following up on the invoice.
- After: The invoice from the 3rd is still open. Can you pay it this week?

### Exclamation marks and emoji in business copy
- Watch for: "!" and emoji anywhere the founder's measured rate is zero.
- Why: borrowed energy. Allowed only at the founder's own measured rate.

### Vague superlatives
- Watch for: world-class, cutting-edge, best-in-class, innovative, exceptional.
- Why: claims with no proof behind them.

## This skill's list: how voice guides and voice prompts fail

### Adjectives as rules
- Watch for: "friendly yet professional", "warm, approachable, expert", "conversational".
- Why: describes every business and instructs nobody. The most common failure in voice work.
- Before: Ruth's tone is warm and down to earth.
- After: Rule 2: say the bad news in the first line of an email, then the fix. | why: 3 of 4 client emails do this.

### Counting by eye
- Watch for: "Ruth uses short sentences" or "about 10 words" with no measured line behind it.
- Why: models estimate rhythm badly, and a wrong figure becomes a wrong rule in every draft.
- After: copy the figure from the measured block exactly, or describe the habit with a quoted example.

### A borrowed voice
- Watch for: samples the founder admires but did not write; AI-drafted or agency pieces counted as theirs; a "starter" voice.
- Why: it measures somebody else's habits and produces a voice the founder cannot hold on a call.
- After: exclude before measuring; use excluded pieces only as a Before.

### Invented Do lines
- Watch for: a "Do" example, a "Sounds like" line or an evidence quote that the founder never wrote, presented as theirs.
- Why: the guide then teaches the skill's voice, not the founder's, and it breaks the no-fabrication rule.
- After: verbatim from a counted piece, or labelled "written in your voice, not yet approved" until calibration approves it.

### Performative tics
- Watch for: the founder's catchphrase in every piece; every paragraph one line; a regional word in every sentence; three signature moves in a 90-word post; their favourite word stacked twice in a sentence.
- Why: natural habits become theatrical when a writer is told about them. Readers who know the founder notice at once.
- Before: Draw it before you buy it. Honestly? The boring bit matters. Proper faff. Draw it before you buy it.
- After: one signature move, at the founder's measured rate, and the rest of the piece plain.

### Generic prompt language
- Watch for: prompts that say "be authentic", "be engaging", "match my tone", "write in a conversational style".
- Why: the model already thinks it is doing all of these. Only numbers, nevers and examples change its output.
- Before: Write in an authentic, engaging voice that resonates with my audience.
- After: Sentences mostly 4 to 19 words, median 10. No exclamation marks (0 in 11 pieces). Sign emails "Ruth".

### Flattening the founder's quirks
- Watch for: tidying a founder's local word ("faff", "proper"), their brackets, their fragments or their odd capitalisation into house style.
- Why: the quirks are the voice. House rules apply to the skill's own prose, not to the founder's habits (dashes and the stated base list excepted, and only after asking).

### Absence turned into law
- Watch for: "Never uses numbers" because five posts had none.
- Why: absence in a small sample is a pattern, not a rule.
- After: label it provisional with its count and put it to the founder in calibration.

### Dead registers
- Watch for: rules for a proposal or a press release when the founder supplied none.
- Why: invented registers read as guesses and get followed as rules.
- After: "Formal document: not measured; supply one proposal you wrote to measure it."

### Prompts that invite invention
- Watch for: "open on a story", "open on a person or a moment ('Had a lad in yesterday...')" with no condition.
- Why: a model given no real case invents one ("Had three runners in this week"), and the founder publishes a patient who never existed.
- After: "Open on a real person or moment only when my brief gives you one; otherwise open on the point, and write [NEED: a real case] where a story would go."

### Rates in a prompt
- Watch for: "closes at most one post in three", "every other post", "in about one piece in ten" inside the PASTE file.
- Why: a model writing one piece never sees the other two, so it uses the habit every time.
- After: in the prompt, "Do not close with 'Anyway.' unless I ask for it"; the rate stays in the guide for people.

### Custom instructions that take over every chat
- Watch for: a short version pasted into ChatGPT's custom instructions that says "Write as Gareth" with no scope.
- Why: every answer, including "what should I cook tonight", comes back in the founder's voice.
- After: recommend a ChatGPT Project first; the short version starts "When I ask you to write something for my business".

### Correcting the founder's English
- Watch for: naming a phrase as the founder's that is not in their pieces (a sample phrase from this skill, or what founders in their market often write); guessing a greeting, sign-off, price or policy for a register their pieces do not show; an After that adds a line the Before never had.
- Watch for: a guide, prompt or sample that "fixes" the founder's spelling or phrasing ("since 9 years" becomes "for nine years", "Kindly revert" becomes "Let me know", "color" becomes "colour"); prose that calls their English a mistake, an error, broken, poor, awkward or non-native.
- Why: their spelling and phrasing are the voice. A founder writing English as a second language is often trusted because the writing reads as a real person; a polished draft reads as an agency. `check-guide` and `check_copy.py` reject the wording; `compare` rejects a changed spelling.
- Before: Note: Tomasz's grammar errors are kept for authenticity.
- After: Kept as written: "since 9 years" (1 of 9 pieces), "write me" (2 of 9). Polish: off.

### Naming a country from spelling
- Watch for: "British English (your samples are British)", "write in American English", "Singlish", "Indian English" as a label for the founder.
- Why: spelling does not tell you where someone lives or who they sell to. Australians, Indians and Singaporeans mostly share one set of forms; plenty of founders mix two. A country label then drags in idioms and conventions the founder never uses.
- Before: Write in British English.
- After: Spell as I do: colour, organise, centre, favourite and favorite. Do not change my spelling or phrasing to match a dictionary or a country.

### Idioms the founder never uses
- Watch for: "hit the ground running", "a labour of love", "move the needle", "on the same page" in a draft for a founder whose pieces hold none.
- Why: idioms are where a model's English shows through most, and they are the first thing a founder writing in a second language notices is not theirs.
- After: plain statements in the founder's words; `compare` flags any idiom the founder's pieces do not hold.

### Converted money and dates
- Watch for: "£120" or "14 October" in a sample for a founder who writes "$120" and "Oct 14"; "$" written as "USD" when they write "$"; "S$" dropped.
- Why: the currency and the date order are part of how the founder writes, and a converted one is wrong in front of their buyer.
- After: copy the measured forms; with none measured, write `[NEED: price]` or `[NEED: date]`.

## Every Merigrove skill: no law, no tax, no assumed country

### Stating what a law requires
- Watch for: "by law you must", "the law requires", "statutory", "legally required", in the guide, the prompt, a sample or the chat (for example about recording calls, keeping emails or using testimonials).
- Why: what a law requires depends on where the founder and their contacts are. The skill points to those rules in one line and stops there. `check_copy.py` rejects the wording.
- After: "The rules on recording calls depend on where you and the other people on the call are; check them before you record."

### Computing tax
- Watch for: a price with a tax added or removed ("$165 plus 8% sales tax, so $178.20", "€3,450 including 23% VAT") in a sample, a Do line written in the voice, or the prompt.
- Why: the skill gives no tax or accounting advice. Prices are copied as the founder writes them.
- After: the price exactly as the founder wrote it, or `[NEED: price]`.

### Assuming a country
- Watch for: a default spelling, currency, date order, holiday or working week that the founder's own pieces do not show; "your clients are in the UK".
- Why: Merigrove's founders are in the US, Asia, Europe, Australia and the UK. A default is a guess about which.
- After: what the founder's pieces show, stated once in the defaults line; with nothing to go on, keep what the brief uses.
