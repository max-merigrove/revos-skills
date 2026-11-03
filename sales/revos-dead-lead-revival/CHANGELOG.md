# Changelog

## 1.2.0 (2026-11-02)
Second round after the first end-to-end runs against plain Claude (a German founder graded 7 of 10).
- `{greeting}`: a salutation per person in annotations ("Sehr geehrte Frau Dr. Lindqvist") with a `greeting_default`, so formal languages no longer read as mail-merge; guidance on natural sentences around the personal field.
- `priority_points` in annotations: any order the founder asks for ("Bartels before Köhler") is applied, never refused.
- The chat follows the language the founder writes in, even when the messages are in another language; the sign-off name is taken from a heading or signature in the notes.
- Send queue rows for people with no address on file say "add their number first" instead of "ready".
- Rubric: the close-the-file line is the last touch's opt-out.
- `memory.py write` names every standing exclusion it saved.

## 1.1.0 (2026-11-02)
Fix round after the v1.0 blind test (German CRM export, Australian notes app paste, return run).
- Messages in any language: new `message_language`, the founder's own opt-out lines (required word for word in every first and last message), personal-field phrases in that language (`context_phrases`, months in German, French, Spanish, Italian, Dutch, Portuguese, Swedish and Danish built in, `month_names` for others). Non-English messages get every check that does not depend on English; the build says which English-only checks were skipped. Quoted reply options are no longer treated as quotations.
- Classifier: German, French and Spanish cues widened (Kunde as a stage, Kunde aktuell, Konkurrent, ging zu, Eigenleistung, gekauft Adressliste, Angebot nie geschickt, offene Rechnung, Empfehlung, Visitenkarte); "owes me" and other unpaid-money words hold the person back; a competitor named as the recorded reason is chose someone else whatever the stage; "asked for pricing" is no longer a price objection; an amount beside an objection counts as a price seen; "maybe current" is held back.
- Source inference: any real exchange in the notes counts as enquired; only rows with no history, or "don't remember", are held as source unknown.
- Dates: "Aug last year", "last winter" and "June last winter" by hemisphere, "14/5" with no year, "after Christmas (last year)", "nach der Heizperiode"; every no-year or relative date is flagged; `last_contact` is now an annotation key, with `email`, `phone` and `handle`. Unknown annotation keys stop.
- Channels: texts-only-to-people-who-texted is applied before any fallback; nobody is planned on a channel they cannot be reached on (held as "no usable channel" with the true reason, and the founder is asked once); "insta @handle", "IG" and @handles are DMs, and the handle shows on the tracker.
- The first ten are the people who can be messaged on the first sending day with an address on file; parked people and people who need an address are listed apart in the preview, the chat and the Today sheet.
- Personal-field phrases are all noun phrases ("our last exchange in March 2024"), and every template is rendered with each of them, with and without a detail, and refused if a junction reads wrongly ("after when"). "Your enquiry" only where the notes say they asked.
- Memory keeps everyone held back as asked to stop, unsubscribed, a dispute or off limits by name, and the message language and phrases; a return run keeps every hold and personal field from the tracker.
- The messages document shows templates with plain [first name] labels, never raw fields, and the repeated close-the-file section is gone; annotation reasons go to a "Changes made from what you told me" table on the Rules sheet, not the Why column. Same-name rows with different emails are flagged.
- Description: lapsed customers, unanswered quote requests and trade show contacts added; recent proposals and bulk newsletter re-engagement added to "Do not use for".

## 1.0.0 (2026-11-02)
- First release.
- Reads a pasted list (one contact per line, any shape), a CSV or TSV export (any delimiter, UTF-8 or Windows-1252), an XLSX file (no library needed) or a returned tracker. Headers matched by synonym in English, German, French, Spanish and others; date order read from the data; month-only, quarter, season and year-only dates marked approximate; money read in the founder's own number style through the shared locale reader; duplicates merged on email, phone or name plus company.
- Nine groups by the earliest true cause, with a reason-inferred flag where only the stage is known; price with no offer on record is an unfinished conversation.
- Held-back list with a reason and a release for every person not messaged: asked to stop, unsubscribed, off limits, current client, dispute, bad fit, business gone, bought or unknown list, no contact detail, future date, too recent, possibly still a client, duplicate, cooldown, a row whose notes hold an instruction, return-run replies and bounces.
- Priority score by group warmth, recency band, a come-back date that has arrived, past value and their own words; shown on the Rules sheet.
- Three to five touches per group over 14 to 21 days, dated on the founder's working days and days off, capped per day, at least two days apart; come-back dates honoured.
- Every message checked by script: one question, length by channel, no money or the founder's prices before the touch they allow, no pitch or what-has-changed before touch 3, opt-out on the first and last touch, quotations traced to the notes, a reason to write in touch 1, the banned list.
- Tracker (Today, Segments, Contacts, Send queue, Held back, Rules) with a Status drop-down and live status totals; messages document; both checked by check_plan.py before delivery.
- Return runs from the updated tracker; `--previous` keeps stops and cooldowns when a new list is planned beside an old one.
- Memory: profile, standing exclusions, learnings and history; never a contact list or an address.
