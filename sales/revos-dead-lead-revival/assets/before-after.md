# Before and after

Same founder, same paste: a UK brand consultant with 63 lines of messy notes and three packages (eval 1). "Before" is plain Claude with no skill, run headless on 2 November 2026 (`evals/sample-runs/eval1-messy-paste-uk/baseline-plain-claude.md`). "After" is this skill (`evals/sample-runs/eval1-messy-paste-uk/`).

| | Plain Claude | Dead Lead Revival |
|---|---|---|
| A file | Says "I've sorted all of them into a CSV, attached above". No file was made. | A six-sheet tracker and a messages document, both checked by script before delivery. |
| Everyone accounted for | "61 unique contacts", no list of who is where. | 63 rows in: 55 on Contacts, 8 on Held back, each with a reason and what would release them. |
| Grouping | Waves by its own judgement; puts Tom Webb ("think about it"), Kate Moore ("then nothing"), Marcus Dell ("too much for us") and Hannah B (lapsed client) in "they gave a return date". | Nine groups by where each conversation stopped. Only people who named a time are parked, and their dates are read: Sarah's "till Q3" is Q3 2024, Ravi's "Q2 numbers first" is Q2 2025. |
| Dates and pace | None. | 184 messages dated from 2 to 23 November on weekdays, never more than 15 a day, touches at least two days apart. |
| First messages | Five templates with brackets ("Hi [Name]... [January / after the summer]"). | Ten written for each person from their notes ("When I sent the sprint proposal in March last year, you said "the board wants to see Q2 numbers first". Those numbers are long in."); the other 45 carry a line from their own notes where there is one. |
| Price in a first message | The "owed something" template puts "[package] ... and the price" in the first message. | No price, package or case study in touch 1 or 2; the case study first appears in touch 3. A script refuses the build otherwise. |
| Stock lines | "a quick note, as I never heard back", "No pressure either way", "I wanted to check in", "I'm sorry it took this long" (an apology the founder never made). | Banned by check_copy.py: no "checking in", no guilt opener, no apology the founder did not make. |
| Sequence and stops | One message per group, "then stop". | Three or four touches per group, the last closes the file, any reply stops it, six months' rest after. |
| Law | "Sole traders count as individuals under UK and EU rules... Irish law... check your lawful basis." | One line: check the rules where you and your contacts are; planning, not legal advice. |
| Next time | Nothing to bring back. | Bring the tracker back with Status updated: replies, stops and bounces come off, the rest are dated. |

What plain Claude did well, and the skill now does too: it merged the duplicates, held back James, Peter, Martin, Nathan and Josh, spotted the future date on Fiona, and noticed that Mike T works at Tomlin & Co, the agency Olivia chose. The skill flags that last one too ("are they a competitor?").
