# Rubric: what exceptional looks like

Score the output before delivery. All seven must pass. If one fails, rework the output; do not caveat it.

| # | Criterion | Pass when |
|---|---|---|
| 1 | Nobody lost or doubled | Every input row is on Contacts or Held back exactly once; the counts in the chat equal the counts in the workbook; check_plan.py prints 0 problems. |
| 2 | Sorted by why, ordered by how long ago | Each person's group comes from where the conversation stopped (or the furthest stage, marked "reason inferred"); price with no offer on record is an unfinished conversation; recency only changes order and pace. A sales lead reading the Contacts sheet would agree with the group for at least nine in ten rows. |
| 3 | The first touch never pitches | No price, discount, result, deadline, booking link or new offer in touch 1; nothing the founder said has changed before touch 3; no price at all unless the founder allowed it, and then not before touch 3. |
| 4 | One ask, built on their own facts | One question per message (exactly one in touch 1); under 90 words for email, 300 characters for a text, 60 words for a DM; touch 1 rests on their date, their words or when they last spoke; every quotation is in their notes; each of the top ten could only have been sent to that person. |
| 5 | Stops are built in | The founder's opt-out line on touch 1; the last touch closes the file in plain words ("I won't write again about this"), which is its opt-out (it may also carry the opt-out line); nobody who asked to stop, unsubscribed, replied, is a current client, is in a dispute or is inside the cooldown is in the Send queue. |
| 6 | Paced like a person, on channels that work | Every send is on a founder working day, no day over the cap, touches at least two days apart, three to five touches over 14 to 21 days; everyone in the first ten can be messaged on the first sending day with an address on file; nobody is planned on a channel they cannot be reached on unless flagged to add the address; texts go only where the founder allowed them. |
| 7 | Read as a person, in their language | Passes check_copy.py; no banned pattern (in any language: read non-English messages against the list yourself); messages are in the language the founder's clients get, with the founder's own opt-out line; on a read-aloud the recipient would feel remembered, not processed; the chat reply carries the counts, the first ten and the flags in five lines; the compliance line is present and no law is stated. |

## The per-line gate (criterion 7)

For every hand-written first message and every template, read each sentence and ask:

1. Can the reader picture it? ("the proposal I sent in May", yes; "our solutions", no)
2. Is it true from the founder's data? (a date, a quote, a thing they said)
3. Could a competitor have sent this exact sentence to this person? If yes on two of three counts, rewrite it.

## Fresh-eyes questions

Give a reviewer the workbook's Send queue (first 30 rows), the document's Today's ten, and this rubric. Ask:

- Would the recipient feel remembered or processed?
- Does any of the top ten read as mail-merge?
- Is each reason to write real, from the notes?
- Is anything promised, offered or claimed that the founder did not say?
