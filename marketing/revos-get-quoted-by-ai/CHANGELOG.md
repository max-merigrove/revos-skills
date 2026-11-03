# Changelog

## 1.1.0 (2026-11-02)
Fix round after the independent blind test (Bengaluru photographer, Hamburg heat pump installer).
- Prices with the currency after the number ("14.500 €", "12,50 €", "1 200 Kč", "500 zł", "299 kr") and "Rs. 25,000" are read as prices by every script; the page audit and the claims gate no longer deadlock on a founder's own form.
- Dates in any style ("2. November 2026", "02.11.2026", "02/11/2026", "2 de noviembre de 2026") are dates, never unsourced figures; no number token can raise a traceback; `allow` in the fact register feeds the number check.
- Every script creates the folder it writes into, so the first robots.txt fix is never lost.
- The sample-size rule for percentages applies only to sentences about being named, cited, recommended or seen in answers; the founder's own quoted figures are left as written.
- The accuracy check reads any place after in, at, from or near and compares it with the register, flags "no place stated" on the where-you-are question, and SKILL.md has Claude read every branded answer itself (`kit.next.accuracy`, `accuracy_ignore`).
- Heard questions: kept exactly as typed with or without a question mark; a message written to the business is refused as it stands and reworded for an assistant with the buyer's words kept (`reworded`); offer words and places match word by word across spellings; verb-first questions in German, Dutch, French and Spanish; the quick five carry the place three times for a local business.
- Promise and comparison language on pages (always, any time, refunds, in writing, the most affordable, higher orders after every shoot, and German, Dutch, French and Spanish equivalents) is refused unless a confirmed fact says it.
- The first-visit closing line no longer claims the founder already knows which questions name them; build_kit refuses it before runs exist.
- American founders get American spelling in the kit and workbook (favorable, color), including the drop-down.
- The page audit names pages ("Your home page") and leaves out the founder's own notes; one slug for kit and workbook (`runlog.py --out-dir`); source1, source2 and "listed my site?" columns read; regional directories classified.
- Chat leads with the three actions; quick panel first for a founder short of time; the founder may choose to unblock before the baseline, told plainly what it costs; every heard question gets a page or a draft page; the kit says it is a plain, unbranded working document.
- Description: Gemini, Google AI Overviews and Copilot named; "in any language"; near misses for blocking AI crawlers, rich results audits and developer-docs llms.txt.
- `assets/before-after.md` rewritten to stand alone. Two new evals and fixtures from the blind test; 55 new regression tests.

## 1.0.0 (2026-11-02)
- First release.
- Buyer-question panel: 5 to 12 questions in five families, each heard (the buyer's exact words, traced to the paste) or derived (from the founder's offer words), three branded accuracy questions, a place rule for local businesses; `queries.py`.
- Test workbook with live formulas and stored values: runs laid out to fill in, rates written "x of y, n equals y", 95% Wilson ranges, PASS, FAIL or UNKNOWN below three runs, panel headline, movement against the baseline only when ranges do not overlap, sources tally, accuracy check against the fact register; reads results back from the workbook, a CSV or pasted rows in any column order and many spellings of yes and no; `runlog.py`.
- Reach check: robots.txt read with standard group rules, crawlers grouped by purpose with a dated source per row, the exact corrected file for a blocked search crawler (re-checked so no other crawler changes); a page audit for empty script shells, greeting openers, prices only in PDFs, hidden text and text addressed to AI; `robots_check.py`, `page_check.py`, `references/agents.json`.
- Fact register and claims gate: every price, figure, link, contact detail, name and invention-prone term in a page or file must be a confirmed fact, written as the founder writes it; declined facts never appear; `claims_check.py`.
- JSON-LD and llms.txt checkers (`jsonld_check.py`, `llms_check.py`); banned patterns (`check_copy.py`).
- The Quote Kit (.docx, ten fixed sections) built only when every gate passes; the kit's fixed text in the founder's language through a labels file (Dutch ships; any other language is translated at run time from `assets/labels/labels-en.json`); `build_kit.py`.
- Memory: profile, fact register, panel, scored totals with dates and n, pages with live dates, learnings and history; never run-by-run answers; `memory_tool.py`.
