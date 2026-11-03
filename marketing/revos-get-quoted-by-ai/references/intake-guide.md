# Intake guide

At most five questions over at most two turns on a first run; one on a return run. Each only if still unknown, and each asks one thing: a question that bundles six facts is six questions. Defaults are said aloud.

1. **What you sell, to whom, where.** "What do you sell, who buys it, and where are they (a city, region, country, or remote)?" Skipped when the pasted page says it. Sets `sells`, `buyers`, `where`, `locations`, `local`, `country`.
2. **Assistants.** "Which AI assistants do your buyers use? a) ChatGPT and Perplexity (default) b) ChatGPT only (quick panel) c) others: name them." Sets `engines`, `quick`.
3. **Buyer questions.** "Paste three to five questions buyers have really asked you, from emails, calls, DMs or reviews, in their words. Or say none and I'll build them from your offer and mark them derived."
4. **Facts, as a read-back.** "From your page and message the pages would say: from € 4.800; 4 to 6 weeks; you and two developers; Webflow only. Correct, cross out or add; anything you do not confirm stays out." One answer covers it; each fact goes into the register as they wrote it. A figure that reads two ways (12.500) is asked once, inside the same read-back.
5. **Reach and editing.** "Paste your robots.txt (your address plus /robots.txt), and tell me who edits the site and on what (Squarespace, Webflow, Wix, WordPress, a developer)." Default: unknown. Sets `robots_owner`, `platform`, `editor`.

Defaults line: "8 questions, 2 assistants, 3 runs each, about an hour; or the quick panel, 5 questions on one assistant, about 18 minutes. Pages in your buyers' language, prices exactly as you write them, dates written out."

Reading what they type: amounts and dates are copied as written. Decimal style is detected from their writing (`locale_numbers.detect_decimal_style`); a figure that can be read two ways (12.500) is asked once. Paper size and date order come from their country, never from their spelling.

Return run: "Paste your results (the workbook, a CSV or the rows), and tell me which pages went live and on what date." Nothing else is asked; the engines, panel, facts and spelling come from memory.
