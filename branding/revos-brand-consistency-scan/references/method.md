# Method

## Contents
1. Why this scan exists
2. The steps and the files they write
3. Where the method comes from
4. Judgement calls and how to make them

## 1. Why this scan exists

A founder's website, LinkedIn and proposals are written at different times, often by different versions of the founder, for different moods of the market. Each one is fine on its own. Read together, they describe two or three different businesses. Buyers notice at the worst moment: a call goes well, the proposal arrives, and it sells something the website never mentioned. The proposal stalls. Nobody says why.

Free brand reviews check one draft against guidelines the founder already has. This scan needs no guidelines: it compares the assets with each other, quotes the conflicts, and proposes the one line to align on.

## 2. The steps and the files they write

| Step | Script | Writes (in the private work folder) |
|---|---|---|
| Save and clean | `redact.py` | `clean/<id>.txt`, `clean/assets.json`, `clean/redaction.json` (counts and fingerprints only) |
| Measure the voice | `voice_drift.py` | `voice.json` |
| Fill the table | Claude | `extraction.json` from `assets/extraction-template.json` |
| Check the quotes | `verify_quotes.py` | nothing; PROBLEM lines |
| Score | `score_consistency.py` | `score.json`; CHECK FACT, CHECK OVERLAP and ASK lines for Claude to act on |
| Check the copy | `check_copy.py` | nothing; PROBLEM lines |
| Build | `build_report.py` | the two founder files in the outputs folder, and `results.json` in the work folder |
| Remember | `check_memory.py` | the memory file, after approval |

## 3. Where the method comes from

- **Merigrove's founder-led brand method.** The brand at this stage is the founder; brand work writes down what they stand for so work they did not make still carries the trust. Its diagnostic "show me the last proposal, the last invoice and your last three posts" (do they look like different businesses?) is this scan's starting question. Its 30-day audit insists client-facing surfaces are checked, because that is where a paying buyer forms a view; hence the weights.
- **The core promise.** One short promise, argued by everything else, short enough for a happy client to repeat. The core line is that promise.
- **The founder-led brand ladder.** Founder-fronted, founder-endorsed, firm-fronted; the move up is earned by proof the business owns. See `brand-ladder.md`.
- **The per-line gate.** Can the reader picture it, can it be shown true or false, could a competitor write this exact sentence. See `core-line-gate.md`.

## 4. Judgement calls and how to make them

- **Grouping** is the only judgement in the score. When unsure whether two answers are the same, ask: would a buyer who read both describe the same business? Write the reason for every compatible pair.
- **Which asset is "right".** None, by default. The scan shows the split; the founder decides. Until they do, the line follows what most of the weight already shares; question 3, asked after the first scan, and the decision at the end exist for this.
- **A proposal for an unusual client.** If the founder says it is a one-off, leave it out and ask for a typical one. A proposal that is typical but contradicts the website is the most valuable finding the scan makes.
- **Few words.** A LinkedIn headline or a bio is too short for sentence measures; it is still read for the five questions.
