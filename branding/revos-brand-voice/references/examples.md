# Worked examples

Six runs. All businesses are illustrative, written for testing: Clearwater Kitchens (Ruth Achebe, UK), Brightpath IT (Sam Hartley, UK), Pryce Physio (Gareth "Gaz" Pryce, UK), Bright Steps (Kayla Brooks, US), Tiffin Lane (Wei Ling Tan, Singapore), Wójcik Oak (Tomasz Wójcik, Poland) and every client, patient and helper named are not real. Every figure below was produced by `scripts/voice_stats.py` on the sample text.

Contents: 1 a clean first build; 2 a messy paste; 3 the traps; 4 a founder writing English as a second language; 5 a founder who mixes spellings and registers; 6 a US founder and an agency with other spellings; what a correction looks like; what `compare` is and is not.

## Example 1: a clean first build (Ruth, kitchen studio)

**Input.** "My VA uses ChatGPT for our Instagram and LinkedIn and it comes out sounding like an estate agent. Can you work out how I write?" Attached: 7 LinkedIn posts and 4 client emails.

**Before any question.** `pieces`: READY, 11 pieces, 857 words, nothing flagged, no helper named.

**Questions before calibration: one.** "Any words or phrases you can't stand?" Where it will be used (ChatGPT, for the VA) and the registers (posts, emails) were taken from the request and stated in the defaults line. Ruth: "stunning, dream kitchen, bespoke".

**Measured, in part.**
```
Sentence length: median 10 words; middle 80% 4 to 19; longest 24 (83 sentences) (measured)
Questions: 0% of sentences; exclamations: 0% of sentences (measured)
Contractions: 5.0 per 100 words; 96% of contractible forms contracted (45 found) (measured)
Stock phrases found in your pieces: "announced honesty" (linkedin-posts.md piece 6) (measured)
```

**Calibration, round 1.** Two samples (a post and an email) that passed `compare` first (the first post failed with sentence median 11 against her 8 and was shortened), plus a tick list: T1 no exclamation marks, T2 no emoji or lists, T3 no questions, T4 "you opened one post with 'Honestly,': keep or ban?" Ruth marked three lines and two ticks in one reply. Each changed a rule.

**Delivered.** `ruth-PASTE-THIS-INTO-YOUR-AI.txt` (full prompt 4,379 characters, short 778), `ruth-voice-guide.docx` (page one 276 words), memory with 4 learnings and her 11 pieces in its machine section.

**From the PASTE file.**
```
- Posts: open on the point. Open on a real moment (a time, a place, something a client said) only when my brief gives you one; otherwise write [NEED: a real case] where a story would go.
KEEP IT NATURAL
- Do not use "Draw it before you buy it", "faff" or "the boring bit" unless I ask for them.
```
In the guide the same habits keep their rates ("each in about one piece in ten"); in the prompt they are off unless asked, because a model writing one post cannot keep a rate.

## Example 2: a messy paste (Sam, IT support for dental practices)

**Input.** One paste: a covering note, posts with his own labels ("linkedin post, june:"), an agency newsletter, a VA's email, a one-line reply, and a phone voice-note transcript.

**Before any question.** The covering note went to `samples/_note.txt`. `pieces` printed ASK for two pieces: the January newsletter (his label says the agency did it; nine stock phrases) and an invoice email signed "Priya". The one-line reply was marked short.

**Questions before calibration: two**, in one message: the two flagged pieces, and his nevers. Sam: "bin both"; nevers "solutions, peace of mind, 'digital transformation' unless I'm taking the mick". The last became an edge case, because his own March post mocks the phrase in quotation marks.

**Calibration.** The first post sample passed on problems but drew two performative warnings (one-sentence paragraphs 67% against his 22%, questions 22% against 0%) and was rewritten before he saw it. He then cut a drama line and "Apologies for any disruption", and ticked hashtags as something to drop.

**Feedback.** "Close: page one says no questions but on the phone I ask loads." The rule was scoped to writing and saved as a learning.

## Example 3: the traps (Gaz, physio clinic)

**Input.** "Can you work out my writing style so ChatGPT stops sounding like a robot?" The covering note says the voice note was "for Bethan (she does our socials)". The voice note has no speaker labels. One LinkedIn post was written with ChatGPT and has no dashes, no emoji and no contractions.

**What `pieces` caught.** (Pasted inline, the voice note counts under its label. Sent as its own file with no speaker labels, as the blind tester did, `pieces` prints "NOTE: voice-note.txt has no speaker labels; read as a solo voice note by Gareth Pryce" and counts it.)
```
NOTE: you named Bethan as writing for you ("Bethan (she does our socials)")
piece 5 | 218 words | spoken | counted   (the voice note, read under its label as his speech)
piece 6 | ask: possible AI or ghostwritten draft (stock phrases: built around you, root cause, we would love to, whether it is; contractions 0% against 100% in your other pieces; sentence median 20 against 9; sentence lengths unusually even)
```
With its stock phrases removed, the same post is still flagged on style alone.

**One question covered both.** "You mentioned Bethan does your socials. Did she write or edit any of these posts? And the June post reads unlike the rest: no contractions where you use them every time, and sentences twice as long. Yours, or written with AI?" Gaz: "the june one was chatgpt, I tidied it, bin it. Bethan just posts them, I write them."

**What the PASTE file does differently.** Gaz's own posts open on real patients ("Had a lad in yesterday..."). The prompt keeps that only when the brief supplies a real case, otherwise it opens on the point and writes `[NEED: a real case]`, so ChatGPT does not invent "three runners in this week". "Anyway." closes two of his five pieces; in the prompt it is off unless asked.

## Example 4: English as a second language (Tomasz, oak furniture, Kraków)

**Input.** "My English is not perfect, I know. When I ask ChatGPT to improve my posts, it makes them sound like American marketing, not like me." Five posts, four customer emails and the website About page.

**What `pieces` caught.** The About page, on style alone: every contractible form contracted where his other pieces contract none, and three English idioms ("built to last", "heart and soul", "labour of love") his pieces never use. The reverse of the usual case: here the polished piece is the outlier. His own pieces, with 0% contractions, were never flagged.

**Phrasing kept, polish offered once.** On reading, eight constructions a copy editor would change were passed with `--phrasing` ("since 9 years", "is including", "write me", "until Friday", "I recommend to"...). The defaults line said: "I'll keep your phrasing exactly as you write it; say polish if you would rather have the grammar tidied." No extra question. Tomasz: "no polish, keep my way. Typos you can fix, like recieve, but not my grammar." "recieve" is not a spelling variant, so it is a typo; "colour" and "color" are both his.

**Calibration.** A sample line with "since" twice was "too much"; the ceiling became one "since" in a piece. The guide never calls his English wrong; `check-guide` rejects that wording and any "<country> English" label.

**Before and after.** `assets/before-after.md`: the usual "improve my English" post fails `compare` on contractions, an exclamation mark, two stock phrases and three idioms; the post from his PASTE file passes.

## Example 5: mixed spelling and three registers (Wei Ling, catering, Singapore)

`measure` found colour (1), colours (1), color (1), favourite (1), favorite (1): both forms of two words. The tick list asked once ("a choice, or a slip?"); she said "both ok", so the prompt says "either is mine; keep whichever the brief uses", and `compare` accepts either. Contractions are 100% in her LinkedIn posts and 18% in her emails and WhatsApp; "can lah", "Ok noted" and "If got any" are kept, on WhatsApp only. Prices stay "S$2,880" and "$16 per pax"; dates stay day first ("19/12").

## Example 6: a US founder and a London agency (Kayla, pediatric therapy, Austin)

Her agency's post (excluded on her label) wrote colourful, centre, paediatric and personalised; her own pieces write color, behavior, favorite, pediatric and mom. Only hers are measured. The defaults line stated her spelling, "$" and month-first dates ("Oct 14", "10/21") and asked nothing about where she is. A test draft with "colours", "behaviour", "£120" and "14 October" fails `compare` on spelling, money and dates.

## What a correction looks like

Ruth returns with her VA's Instagram caption and her own edit, and attaches only her memory file. `unpack` recovers her profile, her 11 pieces and the guide, and notes that the memory predates spelling; `measure --profile-in` re-measures the 11 stored pieces once and adds her spelling and money lines without her pasting anything. `diff` lists the sentences she cut ("Draw it before you buy it.", "Can't wait to show you the finished room."), reworded and added. `compare`, with the memory as the profile, flags "honestly", "can't wait" and "the boring bit" used twice. Four learnings are proposed in one question; the guide goes to v1.1 and the PASTE file is regenerated.

## What `compare` is and is not

`compare` is a drift check: it catches a draft that breaks the founder's measured habits (filler, stock phrases, questions they never ask, exclamation marks, rhythm far off theirs, a phrase used twice). On the blind tester's files it reported 3 problems for a generic post with the emoji stripped and none for the founder's own rewrite. It cannot tell whether a draft sounds like the founder; only the founder can, which is why calibration exists. Never present a `compare` score to a founder as proof of voice.
