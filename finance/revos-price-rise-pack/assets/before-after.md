# Before and after

Same founder, same message (eval 1: a London brand consultancy with six monthly retainers, new clients at 3,000 for roughly 12 hours, 30 days' notice, one client on a term to 31 March). "Before" is plain Claude with no skill, run on 2 November 2026 (`evals/sample-runs/uk-six-retainers-first-run/baseline-plain-claude.md`). "After" is this skill (`evals/sample-runs/uk-six-retainers-first-run/`). Illustrative business.

| | Plain Claude | The Price Rise Pack |
|---|---|---|
| What you get | About 1,200 words in chat. No file. | A workbook with live formulas and a letters document, plus a five-line answer in chat. |
| Size of each rise | Single steps of 25% to 58%: Penrose 950 to 1,500 (58%), Oakridge 1,200 to 1,800 (50%), Kestrel 2,100 to 3,000 (43%), with second steps on top. | No step above 20%. Big gaps close in two dated steps (Penrose 1,100 then 1,300), with the gap left shown for the annual review. |
| Cash | "About £58k a year more" from July, the run rate only; the notice delay is hidden. | 18,850 in the next 12 months after notice, beside 25,800 a year once every step lands. |
| How many clients you can lose | Not answered. One line: "Oakridge may leave". | 20.3% of the raised revenue; lose Penrose and you are still ahead, lose Oakridge as well and you are behind; lose Blue Fern alone and you are behind. Checked against every combination. |
| Dates | 1 January for everyone, Kestrel's letter "around mid-January". The founder is told to check each contract. | Each date from 30 days' notice to the next billing day (Friday 1 January 2027), Kestrel at its renewal (Thursday 1 April 2027), weekdays printed, the last day to send (Wednesday 2 December 2026). |
| Reasons in the letters | "I have not reviewed my fees since 2023", "the rate you pay is now well below what the work costs me to deliver" (no figure behind it), "my current standard rate". | One reason per letter from what the founder said: "New clients now pay 3,000 a month for about 12 hours, which is 250 an hour; your work runs to about 14 hours a month", or for Oakridge the scope line in the founder's words, written to the client. |
| Ready to send | Every letter opens "Dear [Name]" with fields to fill; the currency is guessed as pounds. | Every letter is filled in, marked READY or HOLD, and passes a merge check and a banned-words check. |
| Pushback | None. | Four replies, each in a hold version and a trade version, with the cost of each concession per client. |
| Next time | Starts from nothing. | Remembers the plan as sent; next time one question ("who said yes?") gives the realised figure, the concessions with end dates and the next wave. |

Where plain Claude was already good: the hourly-rate table, holding Fieldmark, waiting for Kestrel's renewal and capping Oakridge's scope. The skill matches those and wins on the arithmetic, the dates, the files, the pushback and the honesty of the reasons.
