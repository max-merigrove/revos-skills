# Method: building a measured voice guide

The voice is extracted, never designed. It already exists in what the founder writes and says, and it has to survive the moment a buyer meets the founder. A designed voice breaks there. This file is the whole method; SKILL.md says when to read each section.

## Contents

1. What counts as the founder's writing
2. Tidying a paste and running the script
3. The floor, the voice-note route and confidence
4. From figures to rules
5. Never write: stated, provisional and house
6. The rules that never bend
7. Traits and tone axes
8. Do and don't pairs
9. Registers
10. Signature moves
11. Keep it natural: ceilings on every habit
12. Before and after rewrites
13. Calibration
14. The voice prompt
15. Page one of the guide
16. Two voices
17. Corrections, refreshes and the learning loop
18. When the founder's habit and the house rules disagree
19. The founder's English: spelling, phrasing, money and dates

## 1. What counts as the founder's writing

A piece is one self-contained item: one post, one email, one DM, one newsletter issue, one article, one proposal, one voice note or one call. A file of ten posts is ten pieces. Pieces under 30 words do not count (a one-line reply shows almost nothing about how someone writes).

Counted: writing the founder wrote themselves, and their own turns in a recording. A draft someone else wrote and the founder rewrote heavily counts; one the founder approved with light edits does not.

Excluded before anything is measured, because each one poisons the extraction:

| Source | Why it is excluded |
|---|---|
| Anything drafted by an AI tool, even if tidied | It measures the model's habits, then feeds them back to the next model as the founder's. This is the single biggest cause of a voice guide that sounds like everyone else. |
| Agency, freelance or ghostwritten copy in the founder's name | Someone else's voice. It is still useful as a Before in the rewrites. |
| A VA's or team member's emails | Kept for reference only (they show what the rules must fix); never counted or quoted as the founder's. |
| Customers' and prospects' words (quoted replies, testimonials, the other side of a call) | Not the founder. Never quoted beyond initials. |
| Writing the founder admires but did not write | A borrowed voice; it describes somebody else's habits and produces a voice the founder cannot hold. |

Asking about authorship. `voice_stats.py pieces` flags five kinds of doubt:

- a sign-off with another name ("Priya");
- the founder's own label saying someone else wrote it ("the agency did this one");
- a person the founder names as writing for them, in the covering note or in a piece ("Bethan (she does our socials)", "our VA, Priya"), printed as a NOTE;
- machine-writing tells: long dashes, stock phrases such as "in today's fast-paced" or "we would love to help", the "not X, it's Y" contrast, triplet lists, emoji bullets;
- style far from the founder's other pieces, measured leave-one-out once there are four or more written pieces: contractions under 50% where the rest are 85% or more, a sentence median more than double the rest, unusually even sentence lengths, or punctuation the founder never uses. Polished AI copy with no dashes or emoji is usually caught here, because a model writing "on brand" drops the founder's contractions and evens out their rhythm.

The founder is always asked about a flagged piece. It is never silently counted and never silently dropped. Ask one plain question covering every flagged piece at once, quoting each piece's first words and the reason, for example: "Three pieces look like someone else's: the January newsletter (you said the agency wrote it, and it has 8 stock phrases), the invoice email signed Priya, and the post starting 'In a world'. Exclude all three? Say which to keep." Never guess, and never count a flagged piece without an answer. Record answers in the authors map (`files.<name>.pieces.<n>.author` or `exclude`, or `confirmed: true` to keep a flagged piece).

Recordings. Before measuring a call or meeting transcript, ask once: "Was everyone on this call aware it was recorded?" The rules on recording and keeping calls depend on where the founder and the other people on the call are; the skill points the founder to those rules in one line and never says what they require. Only the founder's turns are measured. The other party is never quoted, and clients appear by initials. A voice note the founder recorded alone needs no consent question.

Voice notes with no speaker labels are the founder's speech, with one exception the script catches: a paragraph that reads as someone answering the founder (it opens "ya", "ok" or "noted", calls them "ma'am" or "sir", or asks a question back such as "One doubt, should I mention..."). Founders forward these by mistake. `pieces` splits that paragraph off as its own piece, prints a NOTE, and asks; record the answer as `files.<name>.pieces.<n>.author` (or `exclude`). The map applies to spoken files exactly as to written ones: a file-level `author` or `exclude`, `split` (rule, paragraph, blank2) and `pieces.<n>`.

## 2. Tidying a paste and running the script

Founders paste mess. That is the skill's job to sort, not theirs.

1. Attached `.docx`, `.txt`, `.md`, `.csv` and `.eml` files are read as they are. For a PDF or an image, ask the founder to paste the text (or read it yourself and save it as text, word for word). Save each paste exactly as given to a text file in a `samples/` folder in the working folder (or the scratch folder on a chat surface). Name files by what they hold where you can tell: `posts.md`, `emails.txt`, `voice-note.txt`.
2. Move the founder's covering note to you ("ok here's everything, sorry it's a mess, and a voice note I did for Bethan (she does our socials)") into `samples/_note.txt`. Read it first: anyone it names as writing for them goes into the map's `people` with their role and into intake question 1 ("You mentioned Bethan does your socials. Did she write or edit any of these posts?"). The script reads `_note.txt` for named writers and never measures it. Never edit a word of the founder's writing, including typos: typos are evidence.
3. Leave label lines such as "linkedin post, june:" in place; the script reads them as register hints and removes them from the piece.
4. Separate pieces with a line of `---` if the paste has no clear breaks.
5. Write the authors map (format at the top of `scripts/voice_stats.py`): `voice_owner`, `aliases`, any people the founder named with their role, and `country` (a two-letter code from what the founder says about where they are: the note, a signature, an address; never from spelling). After reading the pieces, add `clients` (clients and patients named in them, stored by `pack` as initials) and `keep_names` (places, products and staff the memory may keep). Only after asking: `decimal` ("dot" or "comma") when `pieces` printed ASK NUMBER, and `plausible` when `measure` stopped on a figure the founder confirms.

Commands, in order:

```
python3 scripts/voice_stats.py pieces samples/ --map map.json
python3 scripts/voice_stats.py measure samples/ --map map.json --never "<each stated never>" --signature "<each candidate signature phrase>" --profile-out profile.json --md-out measured.md
```

`pieces` ends READY, ASK (exit 4: authorship to confirm) or DECLINE (exit 3: below the floor), and prints COUNTRY and ASK NUMBER lines when the map needs a country or a figure reads two ways (12.500 €). Both go into the defaults line, never as extra questions. `measure` refuses to run until READY, and stops (exit 5, STOP) when a headline figure is almost certainly a misread paste: a written sentence over 60 words, one piece over 2,500 words, a typical sentence under 3 words, or a transcript with no full stops. Fix the paste, or ask the founder the plain question it prints. Signature phrases are candidates you spotted on reading (a phrase that sounds like them); `measure` counts how often each really appears, and a phrase that appears in one piece only is a habit, not a signature. A trade word the founder uses in most pieces ("pax", "worktop") is vocabulary, not a signature: leave it out of `--signature`, because `compare` allows a signature once a piece.

## 3. The floor, the voice-note route and confidence

The floor: five counted pieces and 400 founder words. These are working defaults, not benchmarks: below them a measured habit is one piece's quirk. Below the floor the skill declines to build a guide and gives the fastest route to five, in this order:

1. The sent folder: five emails to clients or suppliers written in the last six months, pasted as they are.
2. LinkedIn, Instagram or a newsletter: the last five things they wrote themselves.
3. The voice-note route, for founders who barely write: record three voice notes on a phone, one to two minutes each, answering (a) "What do you tell a new client on the first call?", (b) "What does your industry get wrong?", (c) "Tell me about a job that went sideways and what you did." Paste the phone's transcript. Each note is one spoken piece; a phone transcript with no speaker labels is read as the founder's own speech, one turn, and `pieces` prints a NOTE saying so. A guide built mostly from speech marks every written rule as provisional and says so in the header.

Confidence (printed by `measure` as `Samples support`):

- High: 8 or more pieces, 1,000 or more founder words, at least two pieces each of public and one-to-one writing, every authorship question answered.
- Medium: above the floor but short of high. The header says what would raise it ("two client emails would make this high").
- Low is never written. Below the floor there is no guide.

## 4. From figures to rules

Every figure in the guide comes from the measured block, copied exactly. If a rule needs a count the block does not give, describe the habit with a quoted example instead of counting in prose.

| Measured line | Becomes |
|---|---|
| Sentence length, short, fragments, long | Rhythm rules: the typical build, the longest acceptable sentence (the measured longest), whether fragments are used and how often |
| Paragraphs | Paragraph rule; the one-sentence paragraph rate is also a ceiling (section 11) |
| Questions, Openings, Closings | How pieces open and close; whether the reader is asked questions |
| Exclamations, Formatting, Capitals | Formatting rules (emphasis, emoji, hashtags, lists, bold) |
| Person (I, we, you) | Whether the founder speaks as I or we, and how directly the reader is addressed |
| Contractions | Formal to casual axis; the contraction rule ("writes it's and don't, 96% of the time") |
| Punctuation per 1,000 words | Rules on brackets, colons, semicolons; dashes are covered by section 18 |
| Greetings, Sign-offs | Email and DM rules, exact form |
| Distinctive words, Repeated phrases, Signature phrases | Words to use, with where they belong |
| Absent from all, Rare | Provisional nevers (section 5) |
| Stock phrases found, Filler words found | Edge cases put to the founder (section 18) |
| Register lines | The By register section |
| Speaking rate | The spoken register, and the pace for any script written in the voice |
| Spelling, your forms as written | The Spelling and phrasing section and the prompt's "- Spell" line, word for word (section 19) |
| Money and dates as you write them | How calibration samples, Do lines in the voice and the prompt write prices, dates and times (section 19) |
| Numbers as you write them | The thousands separator, decimal mark and units (k, lakh) every number in a sample, Do line and the prompt uses (section 19) |
| Ceilings for a draft | The Ceiling lines for fragments, one-sentence paragraphs, questions and exclamations, copied as figures; `compare` uses the same figures |
| English idioms | Whether a draft may use any; none measured means none written |
| Your phrasing, kept as written | Constructions kept as the founder writes them unless they asked for polish (section 19) |

Distinctive words are frequency lists, not meaning. Choose the ones that carry the founder's world (worktop, chair, joists, backup) and ignore the ones that are only common ("rest", "ones").

## 5. Never write: stated, provisional and house

The never-list comes first in the guide and first in the prompt, because a model writing in someone's voice fails mostly by adding things the person would never write. Three kinds, kept apart and labelled:

- **Stated.** The founder said it: in intake, in calibration or in a correction. Holds whatever the samples show. Format: `- Never: "phrase" | instead: <their word> | stated <date>, "<their reason, quoted>"`.
- **Provisional.** Absent from every counted piece and not yet confirmed. Always carries its count. Format: `- Never: exclamation marks | provisional: 0 of 11 pieces`. Absence alone never creates a permanent ban: a founder who has not yet had reason to write a number does not have a rule against numbers. Put the provisional list to the founder during calibration ("I've marked these as things you never do; anything here you actually do?").
- **House.** Machine-writing tells every guide carries (the base list in `references/banned-patterns.md`): long dashes, stock openers, the contrast reveal, filler verbs, announced honesty. Labelled `house`.

Eight lines at least, thirty at most. If the founder uses one of the house items, section 18 applies.

## 6. The rules that never bend

Five to seven rules, each checkable on a draft by someone who has never met the founder, each with its reason. These are what the founder would correct every time. Draw them from the strongest measured habits, the stated nevers, and anything the founder said about how they will and will not talk to clients. Format: `Rule 1: <rule> | why: <figure, quoted passage or the founder's words>`. "Be warm" is not a rule. "Say the bad news in the first line of an email" is.

## 7. Traits and tone axes

Three traits, exactly. Each has a `means` a reviewer can see in a draft and a `does not mean` that blocks the obvious misreading (usually what the trait turns into when overdone). Format: `Trait 1: <name> | means: <behaviour> | does not mean: <misreading>`. Choose the three the samples show most clearly; a trait the founder claims but the samples never show is not a trait.

Four tone axes, always in this order and orientation (Nielsen Norman Group's tone dimensions, Kate Moran, 2016): serious (1) to funny (5); formal (1) to casual (5); respectful (1) to irreverent (5); matter-of-fact (1) to enthusiastic (5). Format: `Tone axis 1: serious (1) to funny (5) | 2 | reason: <a measured figure or a quoted habit>`. The axes place tone; they never replace the traits. Where a register sits differently, say so in the By register section.

## 8. Do and don't pairs

Six to twelve pairs. Each pair makes the same point twice: once as the category or an AI model would write it, once as the founder does.

- The `Don't:` line is generic phrasing for the situation, written by the skill in the category's voice and ending `(generic example, not yours)`, or a real line from an excluded piece ending `(from <the piece>, not yours)`. `check-guide` fails an untagged Don't line in the guide or the prompt.
- The `Do:` line is the founder's own sentence, verbatim, wherever a counted piece makes the same point. Where none does, the Do line is the skill's sentence in the voice, marked `(written in your voice, not yet approved)`, and calibration is where it gets approved or fixed.
- Format: `Don't: <line>` then `Do: <line> (<source>)` on the next line. Cover openings, closings, bad news, price, a claim, a refusal or boundary, and email sign-offs where those situations exist in the samples.

## 9. Registers

A register measured from fewer than four pieces gives a description, not a hard limit: write what the pieces show and say how many there were. `compare` falls back to all the founder's writing for such a register.

Registers are where the writing happens: written public (posts, newsletters, website), written one-to-one (email, DMs), spoken (calls, video, voice notes) and formal document (proposals, reports). Write a short block for each register the samples hold, naming what shifts against the others, with the measured register line it rests on. For a register with no samples, write `not measured` with what would measure it, and say that writing in that register is lower confidence. Never invent a register the founder does not use.

## 10. Signature moves

Two to four structural patterns that make a piece sound like this founder, each with a verbatim example and how often it appears in the samples. A move is structural (how a piece opens, turns or closes), not a word. Examples: opening on a time and a place; refusing the obvious move before giving the real one; closing on a short instruction with its reason attached.

## 11. Keep it natural: ceilings on every habit

Natural habits become theatrical signature moves when a writer, or a model, is told about them. A founder who opens one post in four with a scene does not open every post with a scene; a phrase they used twice in a year should not appear in every caption. This section stops the voice turning into a parody of itself.

Write at least four `Ceiling:` lines, one for each signature move, signature phrase and strong rhythm habit, each with the measured rate it rests on:

- Signature phrase and kept phrasing: at most once a piece (`compare` fails "Kindly revert" used three times), and in no more pieces than the samples show (`"draw it before you buy it": 1 of 11 pieces, so about one piece in ten`).
- Signature move: at most the measured share of pieces.
- Fragments, one-sentence paragraphs, questions and exclamations: no more than the figure in the measured "Ceilings for a draft" line (the measured rate plus 15 points, computed by the script). Copy that figure ("at most 27% of paragraphs"); never compute it yourself, because `check-guide` rejects any percentage that is not in the measured block. `compare` fails a draft above it.
- Questions, brackets, local words and humour: at the measured rate, never stacked two in a sentence.
- Never more than one signature move in a piece under 150 words.

Add a short list of performative tells to avoid: stacking the founder's favourite words, turning every paragraph into one line, ending every piece with the catchphrase, exaggerating a regional word into a costume. `voice_stats.py compare` checks the measurable ones.

Rates belong in the guide, for people who write many pieces. A model writing one piece cannot hold "one post in three", because it never sees the other two. So in the PASTE file every rate-based habit becomes default-off: "Do not close with 'Anyway.' unless I ask for it", "Leave out the bracketed aside unless the piece is over 150 words". `check-guide` rejects rate wording in the prompt.

## 12. Before and after rewrites

Three rewrites so a writer sees the difference in a real situation. Before, in order of preference: a real excluded piece (agency, VA, AI) from the samples; otherwise a passage the skill writes in the category's generic voice making the same point as a counted piece, labelled `written by this skill in the category's voice; from no source`. After: the founder's own passage making the same point, verbatim, where one exists; otherwise the skill's rewrite, labelled `rewritten in your voice; approved <date>` only once the founder has approved it in calibration, and `not yet approved` until then. A skill rewrite makes the Before's point with the founder's facts only: it may cut and reorder, never add a claim, a line of reflection or a detail the Before and the founder's pieces do not hold. Where the point needs one, write `[NEED: ...]`. Each rewrite ends with `What changed:` naming the rules and the never-list lines it applied. Before and After lines are single lines, paragraphs separated by ` / `.

## 13. Calibration

Calibration is where the founder's ear corrects the measurements. Measured rules are right on average and wrong at the edges; the founder knows the edges.

1. Write two short samples, 80 to 150 words each, in the two registers the founder said they use most (by default a post and a client email), as long as their pieces show that register. With no pieces in a register, write the second sample in another register their pieces show (a team message from a voice note, a DM; a second post only when nothing else exists) and leave the missing register's form as `[NEED]` in the guide. Topics come from the founder's own material (a situation in their samples, told fresh); never invent a client result, figure or quote. Use `[NEED: ...]` where a fact is missing, and also for any part of the form their pieces do not show in that register: with no client email in the samples, the greeting and sign-off are `[NEED: how you open]` and `[NEED: how you sign off]`, asked in the tick list, never "Hello" and "Regards" by guess. Spell, price and date exactly as the founder does (section 19), and use their phrasing only where it fits what is being said, never more often than their pieces show.
2. Before showing them (and say in the message that they passed), run `python3 scripts/voice_stats.py compare draft.txt --profile profile.json --register "<register>"` on each, and fix every PROBLEM. A sample that fails its own measured voice cannot calibrate anything.
3. Number every line (L1, L2...). Under the samples, add a short numbered tick list (T1, T2...) of the provisional nevers, any house-rule conflict (method section 18) and, where both spellings of a word appear, one line asking whether that is a choice or a slip (default: both kept), each one line: "T1 You never use exclamation marks. T2 You opened one post with 'Honestly,': keep it or ban it?" Ask once: "Mark any line that isn't you (a word on why if it's quick), and tick anything on the list you actually do. For example: L3 too chirpy, L6, T2 ban it." This is the only step that may go past the five-question budget, so keep it to one message the founder can answer in a line.
4. For each "not me" line, name the rule that produced it and change the rule, not just the line: tighten a ceiling, add a stated never, move a tone axis, rewrite a Do line. Read back the changes in one line each.
5. Rewrite the missed lines and show them again as round two. Two rounds by default; offer a third if more than a quarter of lines still miss. Stop when the founder says it sounds like them.
6. Record each round in the guide's Calibration section: the sample, the verdicts, the rules changed. The "me" lines may be quoted later as approved examples, labelled `calibration, approved <date>`; they are never presented as the founder's original writing.

If the founder says skip, deliver without calibration, write `Calibration: skipped <date>` in the guide, and offer it next time.

## 14. The voice prompt

The voice prompt is the guide compressed into instructions a model follows. It is delivered as one plain text file, `<name>-PASTE-THIS-INTO-YOUR-AI.txt` (template: `assets/paste-file-template.txt`): where to paste it at the top, then the full prompt and the short version, each between START and END marker lines so a founder can see exactly what to copy.

The full prompt (under 8,000 characters, which fits a custom GPT's instructions field and a Claude Project's instructions with room to spare), in this order:

1. One line: whose voice this is and what it is for ("You are writing as Ruth Achebe, who runs a three-person kitchen design and fit studio in Bristol.").
2. Never write: stated nevers, then the house list, then provisional nevers in a short line.
3. The rules that never bend.
4. Measured targets as instructions with numbers: sentence median and range, longest sentence, fragment rate, contractions, questions, exclamations, paragraph size, person.
4a. Spelling and phrasing (section 19): a `- Spell` line with the founder's forms; their phrasing kept; "Do not change my spelling or phrasing to match a dictionary or a country", or, when the founder asked for polish, what to tidy and what to keep; no idioms when they use none; a `- Money and dates:` line copying their currency and date order.
5. How pieces open and close, per register. Any opener that needs a real event (a client, a patient, "had a lad in yesterday") carries its condition: "Open on a real person or moment only when my brief gives you one; otherwise open on the point, and write [NEED: a real case] where a story would go." A prompt that says "open on a story" without that condition makes the model invent one.
6. Words to use, and words to avoid with what to say instead.
7. Three do and don't pairs, the clearest ones.
8. Keep it natural: each rate-based habit as a default-off instruction (section 11), never as a rate.
9. One short verbatim passage of the founder's, labelled as an example of the rhythm, not text to reuse.
10. Self-check before replying: re-read the draft against the never list and the targets, and cut anything the founder would not say.

The short prompt (under 1,500 characters) is for small boxes such as ChatGPT's custom instructions. Custom instructions apply to every chat, so the short version must begin "When I ask you to write something for my business, write as <Name>..." and nothing else in the founder's chats changes. Then: the six most important nevers, three rules, the three targets that matter most, one spelling line with their forms, the no-invention line.

Write instructions, not descriptions: "Keep most sentences between 4 and 19 words" beats "Ruth writes concisely". No adjectives without a behaviour. The example Do lines in the prompt are copied from the guide's Do lines; `check-guide` rejects any that are not.

Where to paste, in this order of preference: for ChatGPT, a ChatGPT Project (paste the full prompt into the Project's instructions and ask for writing inside it), then a custom GPT, and the scoped short version in custom instructions only if neither is available; for Claude, a Claude Project; for Gemini, a Gem. A person (VA, agency) gets the guide, not the prompt. The file states the date the limits were checked.

## 15. Page one of the guide

The guide's first section, "On one page", is the cheat sheet, followed by a page break: at most 350 words, for the wall or the top of a VA's brief. It opens with the never-list (top eight), then: whose voice in a line; the sound in two lines with the median sentence; the rules that never bend; how to open and close; one Spelling line (their forms, their phrasing kept, money and dates as they write them); three Do lines; the ceilings in one line; the sign-off. No figure that is not in the measured block.

## 16. Two voices

Where two founders both write, ask once whether they want two voices or one shared voice. Measure each separately first (one authors map each, `voice_owner` set to each in turn). Recommend two voices where the measured block differs on two or more of: contraction share (30 points), sentence median (3 words), question share (10 points), first person (2 per 100 words). Two voices means two guides and two PASTE files, each needing its own five pieces. A shared voice is measured with both as `principal` and every measured difference written into the guide as a choice the founders made.

## 17. Corrections, refreshes and the learning loop

A correction the founder makes to a draft is the strongest signal the skill ever gets, because it is the voice being enforced rather than described. A correction made once should never need making twice.

When the founder pastes a draft and their edited version (or says "this doesn't sound like me" about a draft):

1. Run `python3 scripts/voice_stats.py diff before.txt after.txt`. It lists the sentences cut, reworded and added, and how rhythm, contractions, punctuation, the opening and the closing moved.
2. Turn each meaningful change into a proposed learning: a rule, the evidence (the before and after phrasing), the guide section it changes. Example: `Cut "Just checking in" from follow-ups | before: "Just checking in on the quote" after: "Did the quote make sense?" | Never write`.
3. A learning enters as `watch` after one correction and becomes `active` when the founder approves it or makes the same correction again.
4. Check the founder's version passes `python3 scripts/voice_stats.py compare after.txt --profile <profile.json or the memory file> --register "<register>" --never "<each new stated never>"`. If their own edit fails a measured target, the target is wrong for this kind of piece: say so and propose the change.
5. Each approved learning is appended to the guide's Corrections log (date, change, the founder's reason quoted, the rule it creates or changes), and the guide and the PASTE file are regenerated with it, then packed into the memory file again. The guide's version goes up by 0.1. Nothing in the log is ever deleted; a retired rule is struck through with the date.
6. A correction that contradicts a measured habit is recorded as such and the founder decides which wins.

Refresh (new samples): run `python3 scripts/voice_stats.py measure new-samples/ --map map.json --profile-in merigrove-brand-voice-memory.md --profile-out profile.json`. The memory file's machine section holds the pieces measured last time, so old and new are measured together on any surface, claude.ai included, without the founder pasting the old pieces again. Keep every stated never and approved learning, say in one line which figures moved, and pack the memory again.

## 18. When the founder's habit and the house rules disagree

Some founders use a long dash, "honestly", "leverage" or the "not X, it's Y" contrast in their own writing. Never resolve this silently:

- Long dashes: the skill never writes them, in the guide, the prompt or any sample, because readers now read them as machine-written. Tell the founder in one line that the guide uses a comma, full stop or brackets where they would use a dash, and why.
- A filler word or stock phrase the founder uses: ask once, quoting where they used it: "You wrote 'honestly' to open the post about your best kitchens. Keep it as yours, or ban it?" Keep means an `Edge case:` line (allowed only where they used it, at their rate); ban means a stated never.
- The contrast reveal used once or twice: record as rare with its count, and put it in the Keep it natural ceilings rather than banning it, unless the founder bans it.

## 19. The founder's English: spelling, phrasing, money and dates

The founder's English is part of the voice. Founders write American, British, Australian, Indian, Singaporean, Canadian, Irish or Oxford English, often a mix of two, and many write English as a second or third language. The skill measures what the founder writes and copies it. It never corrects it, never names a country from it, and never upgrades it to somebody else's English.

**Spelling.** `measure` lists every word in the founder's written pieces that has two common spellings (colour and color, organise and organize, centre and center, travelled and traveled, paediatric and pediatric, grey and gray, mum and mom; about 1,350 forms in all), with the counts for each pattern. Transcripts are left out, because a phone spells what it hears its own way. Words where both forms are standard in one variety (program and programme, license and licence, judgment and judgement, check and cheque) are left out on purpose.

- The guide lists the founder's forms as written, and the prompt carries a `- Spell` line with them, for example: "Spell as I do: favorite, mom, behavior, color, pediatric. For other words follow the same patterns. Do not change my spelling or phrasing to match a dictionary or a country."
- A founder who writes the same word both ways keeps both. Never pick one for them. The prompt says so ("I write both colour and color; either is mine; keep whichever the brief uses") and the calibration tick list asks once whether it is a choice or a slip; the default is both kept.
- No word spelled two ways in the pieces: the guide says "not measured: none of your pieces has a word spelled two ways", and the prompt says "Keep the spelling my brief uses." Never fall back to a variety.
- The founder may ask for a pattern ("use American spelling for my US clients", "I want it all -ise"). Record it as stated, set `"spelling"` in the authors map (`or-ize`: color, organize; `our-ise`: colour, organise; `our-ize`: colour, organize), re-run `measure`, and describe it by its forms, not by a country. `compare` then checks drafts against the stated pattern.
- A typo is not a spelling. A misspelled word that is not a variant ("recieve", "isnt") is a typo: keep it in quotes of their writing, never copy it into a prompt or sample, and fix typos in drafts only when the founder says so.

**Phrasing.** Some founders write constructions a copy editor would change: "since 9 years", "Price is including delivery", "please write me", "I suggest to leave it", "Kindly revert", "can lah", "do the needful", "prepone the call". These are voice. Buyers often trust them because they read as a real person, and a draft that smooths them out reads as somebody else.

- While reading the samples, note any construction a polish would change, in speech as well as writing ("do the needful" on a voice note is the founder's). Quote it exactly and pass each with `--phrasing "<exact words>"` so `measure` counts it in every counted piece and says which were spoken. Phrasing heard only in speech belongs to the register it was said in: say so in the guide and the prompt ("in messages to my team"). Never describe it, in the guide or in chat, as a mistake, an error, broken, poor, non-native, unidiomatic or awkward English, and never label anyone's English by country; `check-guide` and `check_copy.py` reject both.
- Only phrasing quoted from their counted pieces is named back to them, in chat or in any file; `measure` prints "not found" for anything else, and `check-guide` fails a guide that keeps it. The examples in this section are other founders', never a default list.
- The guide's Spelling and phrasing section lists each phrasing as kept as written, with its count and the register it belongs to. The prompt keeps each one and adds the ceiling: "Use these where they fit what you are saying. Do not add constructions I do not use." Their phrasing is a habit with a rate like any other (section 11); a draft stuffed with it is a parody.
- Polish is the founder's choice, never the skill's. Offer it once, inside the defaults line, and only when phrasing was noted: "I'll keep your spelling and phrasing exactly as you write them (since 9 years, write me); say polish if you would rather have the grammar tidied." This replaces no question and adds none. If the founder says polish, set `"polish": true` in the map and re-run `measure`. The guide and the prompt then say what polish changes (articles, tenses, prepositions, word order) and what it keeps (their words, their rhythm, their spelling, their contractions or the lack of them).
- Idioms. `measure` counts 65 common English idioms. A founder who uses none reads wrong when a draft adds "hit the ground running" or "a labour of love"; `compare` makes that a problem. A founder who uses some keeps those and gets a warning for new ones.
- Contractions are measured like any habit. A founder who writes "it is" and "we do not" every time keeps 0%, and a draft that contracts fails `compare`. A piece of theirs full of contractions and idioms is asked about before it is counted, because an agency or an AI tool usually wrote it.

**Money, numbers and dates.** `measure` reports currency as written ("$", "S$", "€" before or after the amount, "zł", "SGD", "₹", and magnitude words such as lakh and crore, which are money as the founder says it), the order of any date whose order can be read, with the founder's own first example ("month first (e.g. 10/17)"), and times where the clock can be read (10am is 12-hour; 14:30 is 24-hour; 4:45 alone is neither). A separate line reads their numbers with `locale_numbers.py`: the thousands separator (14,500, 14.500, 14 500, 18,00,000), the decimal mark and units (k, lakh). Calibration samples, Do lines written in the voice and the prompt's `- Money and dates:` line use the same forms; `check-guide` requires lakh or crore, and any number style a model would not write by default, to be in that line, and `compare` fails a draft that writes ₹18,00,000 to a founder who writes 18 lakh, or 1,200.50 to one who writes 1.200,50. Where the writing shows no date order or clock, the line gives the founder's country's ("from your country (IN), not your writing"), and samples use it only where a date is needed. Nothing is converted. A price is written as the founder writes it; the skill never adds, removes or computes a sales tax. Where the pieces hold no currency or no readable date, samples use none and write `[NEED: price]` or `[NEED: date]` where one is needed.

**Registers.** A founder's English often shifts by register: Wei Ling writes plain sentences with contractions on LinkedIn, writes them out in emails, and uses "can lah" and "Ok noted" on WhatsApp. Each register keeps its own, and the By register section says which phrasing belongs where.
