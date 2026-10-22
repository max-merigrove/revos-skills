# Changelog

## 1.3.0 (2026-10-21)
Fix round after the end-to-end test (real headless founder sessions, an independent grader and a blind comparison with plain Claude, which the skill won clearly).
- First reply leads with value: a provisional read of the founder's voice (four to six measured habits, each with a verbatim quote), why their AI output sounds wrong, a starter block to paste today, and any mismatch between what the founder says and what the pieces show; then at most five questions. New `measure --provisional` measures the unquestioned pieces while authorship answers are pending; `pack` and `check-guide` refuse a provisional profile.
- A request beside the guide (rewrite this post, fix my VA's draft) is answered in the same reply, in the measured voice, with `[NEED]` for missing facts and `[CHECK]` for any claim carried from a piece the founder did not write.
- No invented attribution: only phrasing quoted from the founder's counted pieces is named back to them; `check-guide` fails a guide that keeps phrasing found in none of them. A greeting, sign-off or price that a register's pieces do not show is `[NEED]` in calibration samples, never a guess. A skill-written After adds no claim the Before did not hold.
- One phrase, one ruling: when calibration removes a word the guide keeps as phrasing, the guide says which wins.
- Exactly three founder files: the PASTE file and the .docx in `brand-voice/`, the memory once in `merigrove-memory/`; every working file (samples, profile, measured block, guide source) stays in a working folder outside the output folder.
- `pack` replaces phone numbers and email addresses in the stored pieces and guide source.
- Missing client emails become question 4 when emails are a stated or inferred use, not an aside.
- The chat summary carries the key rules with figures, the top nevers and what changed from calibration, so a founder who never opens a file still sees the result; calibration messages say the samples passed the check.
- Page one of the guide aims for 300 words (limit still 350).
- Description: "what's my writing style" and "work out how I write from these newsletters or emails" added, plus a directive to trigger before anything is pasted (real-install recall was 8 of 10).
- Round two of the same fix: one output location chosen at the first save and every version written over the same three paths, so no stale copy is left; calibration samples only in registers the founder's pieces show; the tick list holds only uncertain items, with absent habits stated in one line; every rule change shown as a short fresh sample that passed `compare`; a correction that drops the pieces below the floor mid-run still gets applied, with the measured figures marked provisional; the starter block follows the full prompt's rules; clients by initials in the chat too.
- Round three: `check-guide` fails an untagged Don't line (every skill-written Don't ends "(generic example, not yours)"), a line repeated in the full prompt, and a guide with fewer than four Ceiling lines; `check_copy.py` gains `--client` (a client named in full fails) and fails a country named for the founder's English ("Indian phrasing"), and runs on every reply that describes the voice; pieces are referred to by first words, not guessed dates; a fact is used only in the situation it came from.
- 9 new script tests; sample-run guides' Don't lines tagged.

## 1.2.1 (2026-10-21)
- Added "Where files go": deliverables always land in /mnt/user-data/outputs/ (claude.ai, Cowork) or the working folder (Claude Code), never a scratchpad. Found by end-to-end testing with a real headless Claude session.

## 1.2.0 (2026-10-20)
Fix round after the v1.1 blind test, and Build Standard section 13 (reading what founders type, anywhere).
- Voice notes follow the authors map like any other file: file-level `author` and `exclude`, `split` (new: `paragraph`) and `pieces.<n>`. A paragraph that reads as someone replying to the founder ("ya ma'am noted ... should I mention") is split off as its own piece and asked about, instead of being counted as the founder's speech.
- Money in lakh, lac and crore (and "2.4L") is read as money as written; a draft that writes rupee digits or dollars to a founder who writes lakh fails `compare`, and `compare` warns on any currency the founder never uses.
- Numbers are read with `locale_numbers.py` (copied unchanged): decimal style detected once; thousands separator, decimal mark and units (k, lakh) measured and written back; a figure that reads two ways (12.500 €) gets one question inside the defaults line. A currency sign after the amount (1.200,50 €) is now seen.
- Phrasing is counted in every counted piece, speech included, and reported by register ("do the needful" in 1 of 5 pieces, spoken only).
- Emoji runs before a capital end a sentence; variation selectors, joiners, keycaps and skin tones are emoji; hashtags at the end of a line are not words. Exclamations before hashtags and in a stripped greeting ("Hey Katie!") are counted.
- A `---` separator never ends up in an email sign-off.
- The measured block prints "Ceilings for a draft" (the founder's rate plus 15 points), so the guide copies figures instead of computing them; `compare` uses the same ceilings for fragments, one-sentence paragraphs, questions and exclamations.
- `compare`: the sentence median only warns on drafts under six sentences, so a founder's own short edit never fails; exclamations and questions above the ceiling fail; kept phrasing used more than once a piece fails.
- Writers named in the covering note: "intern", "content writer", "social media intern", "team member", and "<Name> posts on / writes for / handles our ..." are recognised.
- Paper size comes from the founder's country (`build_docx.py --country`, or `--paper`), never from spelling; date order and clock fall back to the country only where the writing shows none, labelled as such.
- The memory keeps clients and patients by initials: `pack --map` reduces every name in `clients` in the stored pieces, the guide source and the top part, and refuses while any capitalised name is unsorted. `check-guide` accepts a quote with names reduced to initials.
- `measure` stops (exit 5) on headline figures that are almost always a misread paste: a written sentence over 60 words, one piece over 2,500 words, a typical sentence under 3 words, a transcript with no full stops.
- A short chatty piece is asked about only on three phrase tells, or one tell with a style outlier, or two style outliers.
- Intake skips any question the covering note already answers and states the answer instead; the defaults line can invite two client emails when none were pasted.
- The date line quotes the founder's own first date ("month first (e.g. 10/17)").
- README: the zip is named without a version that can drift; the memory description is exact.
- New evals 9 and 10 (the blind test's two runs, as fixtures and sample runs), 37 new script tests, memory version 3.

## 1.1.0 (2026-10-20)
Global rework (Build Standard 0.1) and the founder's own English.
- Removed: British English as the default for guides and prompts ("in British English (your samples are British)" in the defaults line); eight UK tax, health, vehicle and broadcasting acronyms from the list of acronyms never read as emphasis; the pound and euro as the only currency signs the sentence splitter knew; a sales-tax question used as an example in the banned patterns.
- Spelling is measured, never assumed: about 1,350 forms with two common spellings (colour and color, organise and organize, centre and center, travelled and traveled, paediatric and pediatric, mum and mom), from written pieces only. The guide and the PASTE file copy the founder's own forms; a founder who writes a word both ways keeps both. No country is named from spelling. A pattern the founder asks for is stored as or-ize, our-ise or our-ize.
- Phrasing kept as written: `measure --phrasing` counts constructions a copy editor would change ("since 9 years", "Kindly revert", "can lah"); the guide and the prompt keep them; polish is offered once, in the defaults line, and only changes grammar when the founder asks. Typos are fixed only at the founder's request.
- Money and dates as written: currency signs and codes ($, S$, €, zł, ₹, SGD and 30 more) and date order (day first, month first, year first) are measured and copied into samples and the prompt; nothing is converted and no tax is added.
- English idioms: 65 checked; a draft that adds idioms the founder never uses fails `compare`.
- `compare` now checks spelling, money, dates and idioms; `diff` reports spelling changes and idioms cut; authorship checks also flag a polished piece full of contractions and idioms from a founder who writes neither.
- `check-guide` requires a Spelling and phrasing section, a "- Spell" line with the founder's forms and their phrasing in the prompt, and a "- Money and dates:" line; it rejects prose that calls the founder's English wrong or names a variety of English.
- `check_copy.py` gains three gates every Merigrove skill carries: stating what a law requires, tax arithmetic, assuming a country. Founder quotes (lines starting ">") are skipped.
- New rubric criterion 9, "The founder's English, not a country's"; new banned patterns for correcting the founder's English, naming a country from spelling, idioms the founder never uses, converted money and dates, law, tax and assumed countries.
- Recordings: one generic line pointing to the rules where the founder and the other people on the call are.
- Memory version 2 adds Spelling, Phrasing kept, Polish, and Money and dates. An older memory is upgraded by re-measuring its stored pieces once (`unpack` says so).
- New evals: a US founder (Austin, "$", month-first dates, a London agency's spellings excluded), a Singapore founder (mixed spelling, S$, day-first dates, WhatsApp phrasing) and a founder writing English as a second language (Kraków, "€", no contractions, phrasing kept). Trigger queries gain US, Singapore and second-language phrasings.

## 1.0.1 (2026-10-20)
Fix round after an independent blind test.
- A phone voice note with no speaker labels now counts as the founder's speech (one turn), with a note saying so.
- Polished AI copy is caught by style as well as phrases: contractions, sentence length and its spread, and punctuation far off the founder's other pieces, measured leave-one-out. The phrase list grows from 34 to 55. Flagged pieces are always put to the founder.
- The founder's covering note is kept as `_note.txt` and read for anyone named as writing for them ("Bethan (she does our socials)"); authorship is asked.
- `compare` now checks filler words and questions (two questions against a founder who asks none is a problem), warns when none of the founder's own words appear, and falls back to all the founder's writing for a register with fewer than four pieces. It is described as a drift check; the "9 of 9" proof claim is gone.
- The PASTE file never invites invention: story openers only when the brief supplies a real case, otherwise `[NEED: a real case]`. Rate-based habits are default-off in the prompt and stay as rates in the guide. `check-guide` enforces both.
- ChatGPT placement: a ChatGPT Project first, then a custom GPT; the short version for custom instructions starts "When I ask you to write something for my business".
- Two founder turns and at most five questions before calibration; where it is used and who writes with it are inferred and stated; house-rule conflicts and provisional nevers move into calibration as a tick list; feedback and saving are one question.
- Three deliverables: `<name>-PASTE-THIS-INTO-YOUR-AI.txt`, the voice guide `.docx` whose first page is the one-page version (no raw separators), and the memory file. The separate cheat sheet and `.md` prompt are gone.
- The memory file's machine section (`voice_stats.py pack` and `unpack`) holds the profile, the founder's own measured pieces and the guide source, so corrections and refreshes (`measure --profile-in`) work on claude.ai with nothing else kept.
- Smaller: "Hiya" and similar greetings; Do lines verified verbatim or labelled; check_copy and check-guide agree on never-lists and skip quoted words; staff names and short common words filtered from distinctive words; "honestly" caught mid-sentence; `diff` reports whole sentences; `.docx` samples read directly.

## 1.0.0 (2026-10-20)
- First standalone release, rebuilt from Merigrove's voice builder method for anyone to run without other files.
- Paste-first intake, at most five first-run questions; authorship flags for AI, agency and VA pieces before anything is measured.
- `voice_stats.py`: pieces, measure, compare, diff and check-guide; `build_docx.py` for Word output without extra libraries.
- Never-write first; stated, provisional and house nevers; ceilings on every habit; two-round calibration.
- Voice prompt (full and short, character-checked) and one-page cheat sheet.
- Memory file with a figures-only measured profile, so corrections can be checked on any surface.
