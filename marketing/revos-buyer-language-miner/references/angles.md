# Angles, post ideas and lead magnet topics

Written for ranked clusters only (three voices or more, inside the tier's cap). A cluster with one or two voices gets no angle: it is not yet evidence of a pattern.

Every block is built from the cluster's own quotes. Public copy (ad headlines, ready-to-run ads, post openers, lead magnet titles) carries the buyers' words without quotation marks, written as the reader's own situation; it never repeats one buyer's sentence word for word (eight words in a row from one item, or five from a closed group, is refused). The verbatim quote stays in the bank and in the evidence line the founder reads, so no stranger is ever quoted in public. Write the hook last, after the buying reason is clear (Vibe9's "hook last"), and keep it the way a person texts a friend: plain, specific, no sales voice. A seller who found his first customers in public threads put it bluntly: "the moment you sound like a salesperson, you're dead" (Indie Hackers, 27 Dec 2025).

## Ad angle

An angle is the buying reason, not the headline and not the format (Segwise's distinction). Fields:

- **Buying reason**: one sentence, the reason a buyer in this cluster would pay, in plain words.
- **Type**, chosen from the cluster's tags:

| Type | Fits tags | Shape |
|---|---|---|
| `name-the-pain` | pain, trigger | Says the pain back in their words so they feel seen |
| `cost-of-waiting` | pain | What staying stuck costs. Leans on fear; drop it if the founder rules out fear angles |
| `the-moment` | trigger, pain | Opens on the moment it went wrong |
| `answer-the-doubt` | objection, alternative | Meets the hesitation head on with what the founder actually does |
| `the-after` | outcome, pain, trigger, alternative | Shows the after they asked for |
| `switch-story` | alternative, objection, pain, outcome | From what they used before to what they have now |

A type fits if it suits the cluster's main tag or a tag that makes up a third or more of its phrases (`check_bank.py` enforces this and any type the founder ruled out).

- **Headline**: eight words or fewer, mostly the buyers' own words, unquoted ("Whole day lost for a haircut?" from "I'm tired of losing a whole day for a haircut").
- **Need**: every claim the founder would have to prove before running it, as `[NEED: what would prove this]`. Any figure, speed, price or promise ("within a day", "flat fee", "never", "save") must carry one.

## Post idea

- **Opening line**: carries a run of three or more of the buyers' words, unquoted, as the reader's situation or as something the founder keeps hearing ("You drop her off at 8 and the call comes at 4:45."). Never a named person's testimonial, never "buyers want" or "customers love": that is a claim about everyone. A cluster heard only in a closed group gets an opener in the founder's own words.
- **What to show or tell**: the one thing the post demonstrates, ideally something only this founder can show.
- **Proof**: what the founder holds, or `[NEED: ...]`.

## Lead magnet topic

- **Working title**: in the buyers' words, unquoted (a run of their words). A title that names the outcome they asked for beats a clever one.
- **Format**: checklist, scorecard, one-page sheet, template, short guide. Choose the lightest format that answers the cluster.
- **The question it leaves**: the one thing the lead magnet deliberately does not answer, which the founder's paid offer does. Valuable enough to have paid for, not so complete it replaces the offer.

## What stops them

For clusters that are mostly objection or alternative, `stops` says what answer or proof the hesitation needs and where it belongs:
- **ad**: when the doubt stops the click;
- **page**: when buyers check before they enquire (pricing, scope, process);
- **call**: when it needs a conversation (switching, handover, fit).

## Never

- A detail about a buyer that nobody stated: gender, age, job title, family. Write "one seller", "someone", "they". (`check_bank.py` refuses gendered pronouns in English openers.)
- An angle that says something no buyer in the cluster said.
- A percentage of buyers or "customers love". Counts of voices only.
- A competitor named in an angle on the strength of one review. Two voices or more, and even then shape the founder's own promise rather than attacking the competitor.
- A quote presented as a testimonial or a review of the founder.
- A generic question hook ("Tired of...?", "Struggling with...?", "Ready to...?").
- A finished post or lead magnet. This skill gives the opener and the topic.

## Ready to run (`ad_draft`): the first thing the founder sees

Two or three per bank, on the top ranked themes the founder can already answer, written before any question is asked. They lead the first reply and the document.

- **Pick the themes.** Highest ranked first, skipping a theme whose only honest answer is a fact the founder has not given (that theme's question goes in `sharpen` on the nearest ad, or waits for the second reply). Three ads, three different angle types where the tags allow, so they test against each other.
- **Headline**: about 40 characters or fewer (feed placements commonly cut longer ones), in the buyers' vocabulary, unquoted. The founder's own wording wins.
- **Primary text**: two to four short sentences, the hook inside the first 125 characters: the reader's situation in the buyers' words ("Shakes the whole car ride, then hours in a crate?"), then what the founder does about it, as they told you, then the price or offer exactly as they wrote it.
- **Call to action**: one plain action ("Book now", "Get a quote"), nothing invented; the platform's own button list may decide the exact words.
- **visual**: one line on what the image or video shows, from the founder's own photos or footage (the van at a client's door, the price list, a groomed dog on its own sofa). Never a stock scene, never a person or result the founder has not got.
- **Headline craft.** Plain and concrete, a line a person would say out loud. Either the founder's answer ("Know the price before the groom") or the buyer's situation in their words ("A whole day lost for a haircut?"). Read it aloud: if it sounds odd ("A groom without the whole day gone"), rewrite it. No wordplay, no stacked negations.
- **facts**: each thing the ad rests on, in the founder's words, from their message or answers. Nothing else may be claimed.
- **sharpen**: the one question whose answer would make this ad stronger or let it say something it cannot yet ("Do you text the price before starting on a matted coat?"). These are the first reply's questions, at most three in all. Cleared once answered.
- **Unquoted, always.** No quotation marks around a buyer's words and no buyer's sentence echoed: keep their two or three most telling words and say the rest plainly. `check_bank.py` refuses five words in a row from one buyer with four real words among them (pronouns aside, so "show me a plan" and "show you a plan" count as the same), six in a post opener or title, four from a closed group, and any number from a closed-group member's own story ("three quotes", "9 Hunden"). A competitor review turned into ad copy reads as your claim or as a stranger's words used without asking; both are avoided this way. Only the founder's own customer, quoted with permission, may be quoted, and then `quote_ok` says so.
- **No competitor named**, unless the founder asks (`name_competitors`).
- **Test the fact against the buyer.** Read each quote in the theme against the founder's rule. Where it covers only part of what a buyer described, say so and word the ad to the part it covers. A promise the rule does not keep is the fastest way to angry comments.

## Put with the ads (`with_ads`)

Buyers ask some questions before they book that no ad should carry: does the van need my power, where does it park, is the tip included, what happens if I cancel. When the founder answers one, write it as a plain line in their words for the pinned first comment or the page the ads link to, with the facts it rests on. One line per question, no quotation marks, no promise beyond what they said.

Example, from a mobile groomer's bank (illustrative): theme "Hours in a crate at the salon", 9 of 41 voices quoted.
- Headline: No crate. No car ride. No hours away.
- Text: Does your dog shake the whole car ride, then sit in a crate for hours? We groom at your door, one dog at a time. Small $95, medium $120, large $145.
- Button: Book a groom at your door
- Rests on: full groom at your door; one dog at a time, no crates; $95 / $120 / $145
- Sharpen: Do senior dogs get breaks, and is there a time limit?
- Evidence (for the founder only): "sits in a crate at the salon for like 6 hours", forum.
