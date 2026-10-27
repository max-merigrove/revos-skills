# Changelog

## 1.3.0 (2026-10-21)
- Value before questions: with two or more assets the first reply is the finished scan on defaults read from the assets; at most three questions follow it, each saying what its answer would change. One asset gets its five answers and gaps before the request for a second.
- The chat reply carries the findings: score, a five-question table of short quotes, facts that disagree, what else a careful buyer would catch, the line, and a ready-to-paste rewrite of the asset most out of step (checked by check_copy.py).
- New "Also worth fixing" (`also` in the extraction): claims nothing else backs, dates that have passed or fall on a weekend, figures that do not reconcile, typos. Quotes verified word for word, notes copy-checked, shown in the report and the Word file.
- The recommended line keeps what most of the weight shares (including a shared moment beneath different buyer labels) unless the founder chooses; the sharpest outlier is the alternative, not the default.
- No invented roles, headcounts or "who leads the work" in edits; a figure the founder gives in chat that does not square with what they said earlier is shown both ways. An asset held for the decision gets no edit in the other buyer's words.
- Adjacent questions answered directly in the same turn; corrections follow the founder's priorities.
- Memory: the date style is labelled as a format ("month day, year, as in October 20, 2026"), and a line the founder has not chosen is saved as "recommended, not yet agreed by you". Memory files from 1.2 still read.
- Claude's own copy is refused when it writes a date in the other order from the founder's, or "sceptic" to an American-English founder. The report names how many further "also" items are in the Word file.
- The chat never names a client, never claims a fix the files do not hold, and a location or price that differs between assets is a fact that leads the report.
- A fact the founder gives in chat (a target year, a headcount) goes in `founder_said` word for word and may be used in edits; the founder is never asked to type in what they already said. Ready-to-paste rewrites carry the chosen buyer through every line.
- Description: triggers on "is my messaging consistent" and "one line for my business everywhere", and before anything is pasted.

## 1.2.1 (2026-10-21)
- Added "Where files go": deliverables always land in /mnt/user-data/outputs/ (claude.ai, Cowork) or the working folder (Claude Code), never a scratchpad. Found by end-to-end testing with a real headless Claude session.

## 1.2.0 (2026-10-20)
- Runs on Python 3.8 or later. `build_report.py` no longer uses an f-string only Python 3.12 accepts (it stopped the skill dead on macOS's Python 3.9). A compile check (`evals/check_py_compat.py`) compiles every script with the oldest Python on the machine and reads them for 3.9 to 3.12-only constructs.
- Facts that disagree come first: two assets that state different facts (a team of four against six) lead the report and the Word file whatever they cost in points, and need an edit or a [NEED]. The score step suggests team-size conflicts it finds.
- The founder's corrections hold: an edit they decline is printed "Left as is at your request" and no gate forces it back; an asset aimed at another buyer on purpose can be left out on any question they name; a client-facing asset aimed at another buyer is held for the decision; an asset someone else sells never gets the founder's "I" or name. A sent proposal is edited as the template the founder reuses.
- Credentials the founder states ("ICF certified", "FSC certified") are no longer refused as compliance claims; a credential no asset names is refused instead. "GDPR compliant" and the like are still refused unless the founder's own copy says it.
- Digits for the founder's number words ("9 yrs" for "nine years"). Every figure is read through `locale_numbers.py` (Build Standard 13) with the founder's decimal style, read once; a number that reads two ways is one question; figures go back in the founder's style.
- Bio length counted after every edit (Instagram 150, X 160, TikTok 80, Threads 150, LinkedIn headline 220). One edit to a line that answers two questions covers both; a second edit inside it is refused.
- Voice drift reads through a PDF's line wraps and hyphen splits, ignores headings and labels as sentences, and no longer counts "US" as "us".
- Redaction: a company's first word alone ("Acme's team"), the company on a testimonial line, "228 Park Ave S", and "Level 2" before an address. Counts are distinct client names ("4 client names (7 mentions)"). The founder's own contact and payment details are counted as theirs. A stop when names would take out a large share of an asset.
- Memory keeps what was left out and why, declined edits, who sells which asset, "me and others" in words, and names Australian or other Commonwealth spelling honestly ("Commonwealth spelling (en-AU)", sourced to the country when the copy had too few markers).
- The bottom band is "Different stories", not "Contradicting itself". The report heading says which choice the recommended line assumes. The footer mentions proposals only when there is one.
- Plausibility stops: no asset answering any question; names matching ordinary words.
- New evals 10 and 11 from the v1.1 blind test (New York coaching firm, Sydney packaging consultant).

## 1.1.0 (2026-10-20)
- Global, not UK. The report prints on one page of the founder's paper (Letter in the US, Canada and Mexico, A4 elsewhere, the browser's own paper when the country is unknown); dates read the founder's way; the HTML and Word language follow the founder.
- Locale read from the paste (currency, phone code, address) or asked once as an optional fourth question; never assumed. Saved in the memory file.
- The founder's English is counted from their own spelling (`voice_drift.py`), and `build_report.py` refuses Claude's copy in the other spelling or naming a country or currency the assets never mention.
- Redaction for any country: names in any script, with particles (van der, bin, binti, a/l) and titles (Dato', Shri, Herr); greetings in many languages; companies by every common legal form (Inc, LLC, Corp, PLLC, Pte. Ltd., Pty Ltd, Pvt. Ltd., Sdn Bhd, GmbH, S.A., B.V., K.K., Ltda., PT ...); fees in any currency; phone numbers in any format; US, Canadian, Australian, Singapore, Japanese and other postal codes and street forms; IBAN and labelled bank and registration numbers (routing, BSB, EIN, ABN, UEN, GSTIN). New `--person` (a person, each name removed too) and `--address`; `--client` now never splits a company into words.
- No legal or tax statements: `check_copy.py` refuses lines that state what a law requires, give a tax rate or claim compliance; testimonial edits carry one generic line on checking the rules where the founder and clients are.
- Print layout: the denser layout now switches on from an estimate of printed height, so long quotes stay on one page of Letter as well as A4.
- Removed: the UK-only postcode and bare sort-code assumptions, the en-GB default, the A4-only page.
- New evals: a US founder (Letter) and a Singapore founder (A4).

## 1.0.0 (2026-10-20)
- First release.
- Reads a website, LinkedIn, proposal and any other asset for five questions (who you serve, what you do, the result you promise, why you, what to do next), every answer quoted word for word and checked by script.
- Consistency score out of 100 counted in code from the table, with client-facing assets weighted highest; contradictions ranked by the points they cost.
- Voice drift measured per asset: "I" against "we", sentence length, reading level, contractions.
- Three core lines through a three-test gate, a recommendation that keeps a personally selling founder visible, line edits per asset, and the one decision only the founder can make.
- Client names, fees, emails, phone numbers, addresses and bank details removed before reading; reports and memory refuse to hold them.
- One-page report (HTML, prints to one A4 page) and a Word file of line edits.
- Memory file with the agreed line and answers, per-asset quotes, scores, learnings and history; return runs show the movement and alignment with the agreed line.
