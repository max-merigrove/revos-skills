# Rubric: what an exceptional voice guide looks like

Score the guide (page one included) and the PASTE file before delivery. Every criterion must pass. If one fails, rework the output; do not caveat it.

| # | Criterion | Pass when |
|---|---|---|
| 1 | Measured, not described | Every figure in the guide matches the measured block exactly; every rule rests on a figure, a quoted passage or the founder's own words; no rule is an adjective. `check-guide` reports no altered measured line. |
| 2 | Only the founder's writing | No AI-drafted, agency, VA, customer or admired piece is counted or quoted as theirs; every piece flagged by phrase or by style, and every writer named in the covering note, had an answer before measuring; excluded pieces appear only as Befores, tagged "not yours". |
| 3 | Banned first and specific | Never write is the first section and the first block of the prompt; stated, provisional and house nevers are labelled; every provisional line carries its count; each stated never says what to write instead. |
| 4 | Calibrated | Two samples in the founder's two main registers that their pieces show (a register with no pieces stays `[NEED]` and is not sampled) passed `compare` before the founder saw them; every "not me" line changed a rule, not only the line; the rounds are logged. (Or calibration was skipped at the founder's request and the guide says so.) |
| 5 | Natural, not theatrical | At least four Ceiling lines in the guide, each with its measured rate; every rate-based habit is default-off in the PASTE file; calibration samples and rewrites show no PROBLEM from the performative checks. |
| 6 | Portable and plain | One PASTE file whose first lines say where to paste it, ChatGPT Project first; full prompt under 8,000 characters and short version under 1,500 starting "When I ask you to write"; page one of the guide is at most 350 words and a VA could write a client email from it alone; no raw separators in the .docx; three files in all. |
| 7 | Specific to this founder | The Sounds like line is verbatim; the Do lines are the founder's sentences; nothing in the guide could be pasted into another founder's guide unchanged. |
| 8 | Honest and clean | No invented quote, figure, client or result; the prompt opens on a story only when the brief supplies a real case, otherwise on the point with `[NEED: a real case]`; every Do line is verbatim or labelled; `check-guide` and `check_copy.py` report 0 problems. |
| 9 | The founder's English, not a country's | The Spelling and phrasing section and the prompt's `- Spell` line carry the founder's own forms, both forms kept where they write a word both ways; their phrasing is kept as written (or tidied only because they asked for polish, which the guide and prompt both say); no line calls their English wrong or names a country for it; prices, numbers (thousands separator, decimal mark, lakh or k) and dates in samples and the prompt are written as they write them, never converted and never with tax added; `compare` shows no spelling, money, number, date or idiom problem on any sample; clients and patients appear by initials in the guide, the PASTE file and the memory. |

Fresh-eyes questions (subagent or a separate pass, reading only the outputs and this rubric):
1. Could a VA who has never met the founder write a client email from page one of the guide alone?
2. Pick three Do lines at random: would the founder recognise them as theirs?
3. Is there any line a different founder in the same trade could have in their guide unchanged?
4. Paste the full prompt into a fresh chat and ask for a post with no case in the brief: does it invent a client or patient? Does it break any never?
5. Read three Do lines and the calibration samples as the founder's buyer would: is any spelling, price, date or phrase "corrected" into somebody else's English?
