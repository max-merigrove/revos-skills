# Changelog

## 1.3.0 (2026-10-21)
- End-to-end round with real headless founders and a blind comparison against plain Claude. The skill won only slightly and the recall run scored 6 of 10.
- Scores come from a ladder. Each dimension is scored by naming the highest rung the evidence reaches (for example Cost of Inaction: `seller_supplied` is 3, `asked_dropped` is 4). The script turns the rung into the number. It refuses a rung that the objections' six-step record, the next step, the offer or the cost question on file contradicts. Two runs of the same call now give the same score. The Chicago and Dubai evals score 40 and 24 again. Eval 2 now scores 45, eval 4 scores 28 and eval 7 scores 22. Their Discovery, Objection Handling and Close Attempt numbers did not match the other evals on the same evidence. Each rung has a test you can point to, and a behaviour is scored in one dimension only: a term cut after an objection counts under Objection Handling, not Close.
- Value before questions. With a transcript or recall in hand, no question comes before the review. Without one, the founder's own question gets a labelled provisional answer first. A read_founder CHECK no longer holds the review back.
- The chat reply carries the findings and opens on the answer, with no process narration. In order: the answer to what the founder asked, all five scores, the moment, both Say lines in full, the drill, the message to send today on an open deal, the claims and inconsistencies to check, and up to three further findings (a lever left on the table, a promise the timeline cannot meet). It gives no recording advice beyond the consent line in the file.
- The way back in: an open deal left with the prospect now needs a message to send today. It is built only from the call, opens "Hi [name],", stays under 120 words and offers nothing the founder has not stated. It is rendered in the review, and the checker allows names inside it.
- Recall: every scorecard, stage and objection row carries "(recall, unverified)". A moment placed by the clock ("at about 40 minutes", "40 mins in") is refused. A recall already in the first message is reviewed without the recall prompt.
- Say lines holding their own double quotation marks are refused. Stage directions go in square brackets. An amount cut short by the shell (',500' for '$4,500') is refused by the scorer and the checker. Verdicts are written with the file tool or a quoted heredoc.
- Spelling: with no signal in the founder's messages, it comes from their country or the date order they wrote, never a default. Inconsistencies are caught from the founder's material and the call only, never corrected from outside knowledge.
- Rubric: people the prospect named may appear by name in the message to send, as in Say lines.
- Country only from where the founder says they are based, never from the prospect's address or the currency. The founder's "no structure" answer is never cited as evidence of how the call opened. Inconsistencies in the founder's own material are named at intake.
- The transcript is always copied into the scratch folder and the copy is deleted. The founder's attached file is never touched, and the privacy line now says so.
- Description: triggers before the transcript is pasted, and on "we lost it and I can't work out why", "what should I have said when they asked the price" and "she asked for a discount".
- Tests: 273 (30 added). The 7th Level and NEPQ exclusion detector is unchanged.

## 1.2.1 (2026-10-21)
- Added "Where files go": deliverables always land in /mnt/user-data/outputs/ (claude.ai, Cowork) or the working folder (Claude Code), never a scratchpad. Found by end-to-end testing with a real headless Claude session.

## 1.2.0 (2026-10-20)
- Fix round after an independent blind test. The measure script that every review rests on now reads ordinary pain, objections, scarcity and price asks as founders and their buyers say them in American, British, Indian, Australian, South African, Nigerian and Singapore English, tested on a messy real-world Zoom export.
- Pain: plain phrasing ("they don't. Not really", "it's always chaos", "I'm tired", "twenty two days", "underwater", "doing my head in", "facing issues", "doing it tough") and any full answer to a seller's "what happens / how long" question; reassurances ("no problem", "no worries") are set aside first.
- Objections in two tiers: resistance counts wherever it is said ("more than I figured", "not going to make that call by myself", "got burned on a retainer", "last price", "sharpen your pencil", "20% off"); a partner, accountant, budget or past supplier counts only after the price or pitch, and not when it answers the seller's own question. Earlier mentions are listed as context, as likely creation points.
- Scarcity: "one slot left", "we only take on two a month", "lock that in in the next week or two", "valid till Sunday", "intake closes", "filling up fast".
- Price: a seller's estimate of what the problem costs is no longer read as the price; "how much of my team's time" is no longer read as the price asked; "what's the damage", "what are your charges", "the commercials" and "let's talk numbers" now are.
- Folds are read from the pitch or price on, so small talk ("take your time") is not a candidate. An unlabelled caption is set aside or given to the speaker either side of it, never made into a second prospect.
- Names: the measure lists people the prospect names by relation ("my business partner Greg"); the scorer and the checker refuse those names outside quotes and Say lines. A recall review carries the prospect's name in the verdicts (never printed or saved) so it can be checked for.
- Founder-typed figures go through the Build Standard number reader (locale_numbers.py, copied unchanged) in a new read_founder.py: decimal style detected once, one question on an ambiguous figure, plausibility stops on headline figures, the founder's price set against the call's, figures written back in the founder's style, date order and paper from the founder's country. Usual call length is read as written ("45 mins", "an hour").
- The Word file's paper size follows the founder's country and its proofing language their spelling; no fixed default country.
- The working copy of the transcript is deleted at the end of the run (clean_scratch.py), and the review's privacy line says so; a recall review says what it keeps instead.
- Memory: a re-review of the same call replaces its history row (a one-way fingerprint identifies the call), and the pattern check never counts one call twice. Sources are recorded as "read from the call" or "read from your messages" where that is where they came from. Files from 1.1.0 are still read.
- Recall: the intake questions are folded into one five-item recall prompt; the skill declines only when the founder cannot give the problem, the price moment and the ending; a fact the founder adds about the call may change a score, a fact about the deal outside it does not. Recall reviews read "Showed up ... Started ..." and drop the column of repeated labels.
- SKILL.md: when the founder and the transcript disagree, the transcript is used and the readback says so; the closing Merigrove line is the very last line of the run; fresh-eyes subagent on calls of 20 minutes or more.
- Evals: the blind tester's two runs kept as evals 8 and 9 with their fixtures, and 71 regression and cue tests added.

## 1.1.0 (2026-10-20)
- Global rework (Build Standard 0.1). No country is assumed: currency, date order and spelling follow the founder, read from their message, the transcript and memory, and are saved to memory (new profile fields Date style and Spelling; the date style is required in the verdicts and sets the order of the review's date).
- Money said on a call is read in any currency and any spoken form: symbols ($, £, €, ₹, ¥, S$, A$, R$, Rs, RM and others), ISO codes, currency words, k, grand, thousand, lakh, crore, million, European and Indian digit grouping, and words ("ten grand", "fifty thousand dollars", "2 lakh", "two thousand seven fifty"). The measure output lists each figure with the amount it reads, as said; nothing is converted. A seller restating the prospect's own figure is no longer read as the price.
- The solicitor line is replaced by one generic line in every review: "Check the consent rules for recording calls where you and the prospect are."
- The checker now refuses a statement of what a law requires, a named law or regulator, a lawyer by a country's title, and tax worked out on a price; three new banned patterns (stating what a law requires, working out tax, assuming a country).
- No currency is added when none was said (the Otter sample no longer shows pounds the founder never wrote).
- Google Meet transcripts with a timestamp every few minutes are read (turn numbers, length from "Meeting ended after"); US phrasing added to the cues (circle back, run it by, run me, cofounder, end of quarter, slots left).
- Evals: a US founder (Zoom, dollars, month day year) and an Indian founder (Google Meet, rupees and lakh, GST quoted as said) added; the held-out wording detector kept unchanged.

## 1.0.0 (2026-10-20)
- First release.
- Reads plain text, markdown, .vtt, .srt and .docx transcripts from Zoom, Teams, Fathom, Otter and Google Meet, with or without timestamps; refuses a summary, a single speaker or fewer than six turns with a plain STOP.
- Five weighted dimensions with four failure caps, scored by script and rounded down; stage coverage against the founder's own stages or five standard ones.
- Every finding cites a position and a verbatim quote, checked against the transcript; recall reviews carry no times and no verbatim quotes.
- Each objection with its belief and a handling verdict over six steps; next step graded; every failure traced from where it appeared to where it was created.
- Exactly two coaching points, each ending in the line to say, plus Say instead lines and one drill.
- Stated and real loss reasons kept apart.
- Red lines: price before cost, price asked early, deadlines, promises, and lines in the transcript addressed to an AI.
- Memory of setup, learnings and scores only; the pattern check flags a dimension weak in two of a seller's last three reviews and turns it into the drill.
- Word document output, built with the standard library.
