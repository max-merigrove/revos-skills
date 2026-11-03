# The nine groups and their messages

Read this before writing the messages file. Each group has a definition, how the script places someone in it when no reason is recorded, the angle, the touch plan with each touch's purpose, and two illustrative lines. The illustrative lines are written for made-up businesses to show the shape; never paste them into a founder's messages. Every message is written fresh in the founder's voice from their own facts.

## Contents

1. How to write any touch
2. The messages file
3. The nine groups
4. Hand-written first messages (the top ten)
5. Texts and DMs
6. Messages in another language

## 1. How to write any touch

- One ask. One question mark in the body, exactly one in touch 1. The close-the-file touch may have none.
- A reason to write. Touch 1 names when you last spoke, the date they gave, or something they said. In a template that means `{context}`, `{when}` or `{their_date}`; in a hand-written message it means their own words or date.
- No pitch in touch 1: no price, no offer, no result, no deadline, no booking link, no "book a call". Touch 2 can offer something small (a one-word reply, an outline in writing). What the founder says has changed (a new case study, a new package, a new price) waits until touch 3. Prices appear only from the touch the founder allows, and never by default.
- No invented changes. If the founder said nothing has changed, touch 3 is an honest question, not news. `{changed}` is only used when the founder gave something.
- Plain and short. Email under 90 words, text under 300 characters, DM under 60 words. Write as the founder would to one person: no "I hope this finds you well", no "just checking in", no apology they did not make.
- Opt-out line on touch 1 and the last touch. `{opt_out}` fills the founder's line (default: "If you'd rather I didn't get in touch again, just say and I won't."). The close-the-file message says plainly that you will not write again, which is its own opt-out.
- Quotation marks only around words that are in that person's notes. The script checks.
- Subjects: specific and calm ("The October proposal", "You said January"). Never "Quick question", "Checking in", "Re:". Put a field in template subjects ("Your enquiry in {when}", "{company} and the audit") so thirteen people in one group do not get thirteen identical subject lines.
- Say the year whenever the month was not in the last few months ("October last year", "October 2025"); a bare "October" in November reads as last month.

## 2. The messages file

```json
{
 "templates": {
  "quiet_after_proposal": {
   "1": {"purpose": "Acknowledge the gap, one easy question",
         "email": {"subject": "...", "body": "Hi {first_name},\n\n...{context}...?\n\n{opt_out}\n\n{sender}"},
         "text": "Hi {first_name}, it's {sender}. ...?"}
  }
 },
 "tier_a": {"C012": {"subject": "...", "body": "..."}},
 "overrides": {"C030": {"2": {"subject": "...", "body": "..."}}}
}
```

`{detail}` is optional: one sentence about that person, written in annotations from their notes ("You'd said the board wants to see Q2 numbers first."). It renders as nothing when absent, so put it at the start of touch 1 (`"Hi {first_name},\n\n{detail}It's been a while since..."`) and write the rest so it reads with or without it. The preview lists everyone whose notes hold a fact their group message would otherwise miss.

Fields: `{first_name}` `{full_name}` (for a formal greeting: "Dear Markus Weber") `{last_name}` `{greeting}` (the per-person salutation, section 6) `{company}` `{context}` (the personal field: "my proposal from May 2025") `{when}` ("May 2025") `{their_date}` ("Q3 2024", "the new year") `{sender}` `{business}` `{next_step}` `{changed}` `{opt_out}`. Write templates only for the groups, touches and channels the preview lists under TEMPLATES NEEDED. Write `{context}` into a sentence that reads naturally with any of the script's phrases, all noun phrases: "my proposal from May 2025", "the price we talked about in May 2025", "your enquiry in October 2025", "the time we met in June 2025", "the conversation we had in March 2025", "our last exchange in March 2024", "the call we had lined up around February 2025", "the work we did together in 2023". The build fills every template with each of them, with and without a detail, and refuses one that reads wrongly ("after when", two articles, a doubled word). "Your enquiry" is used only when the notes say they asked; where the notes do not say who wrote first, the phrase is "our last exchange" and the preview flags it. Where a contact's default phrase is weak or missing, set a better one in the annotations file (`"context": "the audit for the bakery in May"`), built only from their notes.

## 3. The nine groups

Day offsets are working defaults for a 14 to 21 day sequence (practitioner ranges of three to five touches spaced three to five days apart), not a measured best. The script moves each date to the founder's next working day and keeps two days between touches.

### Parked with a date (3 touches: days 0, 5, 14)

- Who: they named a time to come back ("budget frozen till Q3", "after the summer break", "ring me after the 20th", "ask in January").
- Placed by: a come-back phrase in the notes, read into a date after the last contact. If the date cannot be read, they go to Said not now with a flag.
- Angle: they told you when. Write on that date (or now, if it has passed) and use their words for it.
- Touch 1: name the time they gave; ask if it still stands. Touch 2: make answering take one word (1 yes, 2 later, 3 no). Touch 3: close the file.
- Illustrative (a joinery firm): "You said to try again once the workshop move was done. Is it done?"
- Illustrative (a dental clinic): "In March you asked me to come back after the new financial year. Is that still the plan?"

### Past client (4 touches: days 0, 4, 11, 18)

- Who: worked with the founder and stopped. Placed by "client 2023", "lapsed", "former client", invoice history.
- Angle: good work already happened. Ask how things went since; no pitch until they answer.
- Touch 1: how have things gone since the work. Touch 2: one honest question about what may have outgrown the work. Touch 3: what has changed on the founder's side, offered, not pushed (or an honest question if nothing changed). Touch 4: close the file.
- Over three years since: three touches (1, 2 and the close).
- A dispute, complaint or unpaid invoice on file means held back: a phone call, not a message.
- Illustrative (a bookkeeper): "It's been a while since we wrapped up your year-end. How has the new system held up?"
- Illustrative (a web studio): "The site we built is two years old now. Is it still doing its job?"

### Went quiet after a proposal (4 touches: days 0, 4, 11, 18)

- Who: a proposal, quote or price went out and nothing came back. Placed by "proposal", "quote", "sent pricing", "contract sent", or a proposal-stage column.
- Angle: the proposal is still open in their head. One easy question about where it landed.
- Touch 1: acknowledge the gap; ask where it landed. Touch 2: the one-number reply (the labelled options may sit in quotation marks: they are the founder's words, not a quotation) ("1, 2 or 3?": still interested, went another way, project died), a known approach for getting silent prospects to answer. Touch 3: the no-oriented question ("Have you decided to leave this for now?"), which is allowed only here and only from touch 3, or what has changed. Touch 4: close the file.
- Illustrative (an HR consultancy): "I sent the onboarding proposal in May and never found out where it landed. Did it get shelved?"
- Illustrative (a printer): "Which is closest: 1 still on, 2 went elsewhere, 3 the event was cancelled?"

### Said not now (4 touches: days 0, 4, 11, 18)

- Who: timing or budget with no date, a partner or board to consult, "on hold", "too busy". Placed by those words, or a budget reason before any offer.
- Angle: timing was the reason. Ask whether timing has changed, nothing else.
- Touch 1: has the timing moved. Touch 2: ask for a better month to write. Touch 3: what has changed, or an honest question. Touch 4: close the file.
- Illustrative (a coach): "When we spoke in spring the timing was wrong. Has that changed?"

### Talked, no proposal followed (4 touches: days 0, 4, 11, 18)

- Who: there was a call or meeting and the conversation never reached a proposal. Also: "price too high" with no price ever sent, and "think about it" with no offer made. Those are unfinished conversations, not objections, because the earliest true cause is that no offer was made.
- Angle: pick it up where it stopped. If the founder dropped the ball, a plain "that was on my list" is fine; never a grovelling apology.
- Touch 1: is the problem they raised still live. Touch 2: offer a short outline in writing. Touch 3: what has changed, or an honest question. Touch 4: close the file.
- Illustrative (an IT support firm): "We talked about the backups in March and never got to next steps. Is that still a worry?"

### Stopped at the price (3 touches: days 0, 5, 14)

- Who: a price was given and price was the stated reason. Only with a proposal, quote or price on record.
- Angle: ask what would have had to be different. Never cut the price or offer a discount in writing.
- Touch 1: what would have made it work (size, timing, scope). Touch 2: the one-number reply. Touch 3: close the file, mentioning a smaller first step only if the founder has one and said so.

### Booked a call that didn't happen (3 touches: days 0, 5, 14)

- Who: no-show, cancelled, rescheduled and gone.
- Angle: an easy way back, then an honest fork.
- Touch 1: no blame; would they like another time. Touch 2: the honest fork: was it timing, or did something change? Either answer is fine. Touch 3: close the file.
- Illustrative (a physio): "We had a call booked in February that didn't happen. Want to find another time?"

### Enquired or met, never got to a call (3 touches: days 0, 5, 14)

- Who: enquired and never booked; met at an event or by introduction; signed up and asked a question. Placed by "enquired", "form", "met at", "event", "intro", "newsletter".
- Angle: remind them of the moment and ask if it is still live.
- Touch 1: the moment ("your enquiry in October", "meeting you at the expo"), is it still on their list. Touch 2: the one-number reply. Touch 3: close the file.

### Chose someone else (3 touches: days 0, 5, 14)

- Who: went with a competitor, did it themselves, hired in-house.
- Angle: ask, without edge, how it went. The door stays open. Never criticise the other provider.
- Touch 1: how did it turn out. Touch 2: a second opinion, offered lightly. Touch 3: close the file.

## 4. Hand-written first messages (the top ten)

The preview names the top contacts (Tier A, ten by default, up to fifteen). For each, write touch 1 by hand in `tier_a`, from their row only:

- Use their name, and something only they said or did: their date, their words, the detail of what was discussed. A competitor could not have written this sentence.
- Quote only words that are in their notes, in quotation marks. Paraphrase anything else.
- Use relative time correctly against today's date ("last year", "in March 2024"). Check the year.
- Never infer a company name from an email domain; use a company only if the founder's data names it.
- Never promise to ask only once, or that you are not chasing: the sequence follows. Never say "when we spoke" if the notes only show an email; "when we were last in touch" is always true, and "your enquiry" only where the notes say they asked.
- Vary the openers across the ten: not seven that start "When". No pointed lines: nothing about how long they have taken ("two summers have gone by"), no "only ever", no "I'm asking properly", no sarcasm.
- Owning a miss ("I never followed up") only where the founder said they dropped it, in their message or their notes.
- Do not assume what the notes do not say: that timing was the reason, that the business grew, that a call happened, or what the work was about beyond the founder's own offer.
- Same rules as any touch 1: one question, no pitch, opt-out line, under 90 words.

## 5. Texts and DMs

- Texts only to people the notes say texted before, unless the founder allows texts to everyone with a mobile.
- The first text says who it is from ("Hi Dan, it's Jo from Hollis Brand Studio").
- Under 300 characters; one question; the short opt-out ("Just say if you'd rather I didn't message again.").
- DMs: under 60 words, same shape. A handle in the notes ("@name", "insta", "IG", LinkedIn) makes a DM possible, and it shows on the Send queue.
- Nobody is planned on a channel they cannot be reached on. Someone with only an email when the founder chose texts, or a number but no texting history, is held as "no usable channel", with the true reason, and the founder is asked once whether to allow another channel. In a pasted list, someone with no address at all is planned on the founder's first allowed channel and flagged "add their number", and is never in today's ten.

## 6. Messages in another language

Messages go out in the language the founder's clients get (`message_language`), which may differ from the language the founder writes to you in. Ask once if the notes and the founder's message point different ways; otherwise state it.

- Opt-out: write `opt_out_email` and `opt_out_short` in that language, in the founder's register (formal or informal). Every first and last message must carry one of them word for word; `{opt_out}` fills it. The build refuses German or French messages that still carry the English default.
- Personal field: write `context_phrases` in that language for every key the preview lists, each with `{when}` (filled with the month in that language: "März 2026"). Keys and their English: proposal ("my proposal from {when}"), proposal_deal, price_talk ("the price we talked about in {when}"), met, enquiry ("your enquiry in {when}"), exchange ("our last exchange in {when}"), conversation, booked_call, work ("the work we did together in {when}", where {when} is the year), work_deal.
- Grammatical case: where the language inflects (German, Polish, Finnish...), write every phrase in one case and put `{context}` only where that case fits. German example: all phrases in the accusative ("mein Angebot vom {when}", "unser Gespräch im {when}", "Ihre Anfrage im {when}", "unseren letzten Kontakt im {when}") and `{context}` only after "an", "um" or "auf" ("Ich denke an {context}", "wie es um {context} steht", "Ich komme auf {context} zurück").
- The script checks every message for length, one question, money and the founder's prices, the opt-out line, quotations, fields, dashes, exclamation marks and emoji in any language. Its English phrase lists (stock openers, chasers, pitch words in touch 1, claimed results) do not run: apply `references/banned-patterns.md` to the meaning yourself, in that language, and say in the chat that you did.
- Greetings and register follow the founder. In a formal language a greeting with the full name ("Guten Tag Petra Lindqvist") reads as mail-merge: start each template with `{greeting}`, write a `greeting` per person in annotations in the founder's style ("Sehr geehrte Frau Dr. Lindqvist", "Madame Durand", "Estimado Sr. García") where the name in the data makes Frau or Herr plain, and set `greeting_default` (for example "Guten Tag {full_name}") for the rest. List in the chat the people who got the neutral greeting, so the founder can fix any. The hand-written first messages use the same salutations.
- Natural sentences: "Ich komme noch einmal auf {context} zurück" and "wie es um {context} steht" read like a person; "Ich denke an {context}" reads stilted. Read every template aloud with two of the phrases before building.

