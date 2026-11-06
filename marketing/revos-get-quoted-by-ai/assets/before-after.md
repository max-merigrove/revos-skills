# Before and after

What a founder gets from a general AI chat when they ask "why does ChatGPT never mention us?", and what they get from this skill, for the same message. Both businesses are fictional. The general chat replies were captured on November 3, 2026 with no skill, no tools.

A general chat is good at half of this job. It writes an answer-first page, a JSON-LD block and plain advice on listings and reviews, says changes take time, and often spots a robots.txt that blocks a search crawler. The skill adds the half that decides whether anything changed: a test built from real buyer questions, counts over several runs, facts checked by script, and a memory for the retest.

## A financial modeler selling to SaaS founders in the US

| | A general chat | With this skill |
|---|---|---|
| Offer on the page | Uses her price, timing and tool, then adds a market range she never gave ("$3,000 to $15,000", flagged as a placeholder to check) and suggests describing method details she never gave. | Uses only what she confirmed ("from $4,500", usually two to three weeks, Google Sheets only, Austin). Nothing else can reach a page: the claims gate refuses it. Proof stays `[NEED: one client result or quote you have permission to use]` and the page is marked not finished. |
| A test | "Re-test with the same prompts monthly", plus a few variants, with no run count or sheet. | 8 buyer questions (3 in her buyers' own words), a run protocol, and a workbook of 54 rows that scores named, cited and recommended as "x of y, n equals y" with ranges, UNKNOWN below three runs. Retest on or after December 1, 2026. |
| Buyer questions | Turns her three questions into three pages, which is sound. | The same three questions, word for word and tagged heard; the one written to her ("can you build a model...") is reworded as a founder would ask an assistant, with her buyer's words kept beside it; the rest are tagged derived from her own offer words. |
| Structured data | Adds FAQPage markup on every question page without saying Google retired the FAQ rich result on May 7, 2026; nothing checked. | Business, person and service markup only, parsed and checked; FAQ markup only if she asks. |
| Reach | One line: make sure robots.txt does not block OAI-SearchBot or GPTBot, treating a search crawler and a training crawler alike. | Robots.txt not seen, so every crawler reads UNKNOWN, not FAIL, with the one step that settles it; a training block would be left as her choice. |
| Files | One chat reply, offering to write the pages next. | The Quote Kit, the workbook, page text, JSON-LD and llms.txt, plus a memory file for the retest. |

## A web studio in Asheville, North Carolina (messy paste)

| | A general chat | With this skill |
|---|---|---|
| Reach | Catches the OAI-SearchBot block and explains search versus training well, but its corrected file drops the GPTBot block by default, drops her /wp-admin/ rules, and sends her to Webflow's settings rather than the plugin that wrote the lines. | The same finding, with the corrected file re-checked so no other crawler changes (the GPTBot block stays as her choice), a note to change it in the plugin's settings, and a request that Marcus check the plugin's firewall too. |
| Broken markup | Spots the trailing comma and the rating for reviews that live on Google Maps, and removes the rating. | The same, by script (does not parse, line 10, column 1; rating refused until the site shows those reviews). |
| Contradictions | Uses her 4 to 6 weeks rather than the review's "3 weeks", and says why. | Asks; she confirms 4 to 6 weeks, so "3 weeks flat" is declined and kept out of every file by the gate. |
| Facts | Suggests case studies with client names, describes her clients as "breweries, restaurants, and outdoor brands", and fills the markup with placeholders such as "+1-828-XXX-XXXX" and "YOUR STREET". | No client named without permission; no placeholder in any markup; the phone and street are left out until confirmed. |
| Prices | "$4,800" as she wrote it. | The same, enforced by script in every file. |
| A test | "Expect weeks for recrawling", with no questions or runs. | 8 questions, a 54-row run sheet, a baseline before any change, and a retest on or after December 1, 2026. |

What a general chat also does well, and the skill keeps: refusing to promise a citation, separating search crawlers from training crawlers, recommending accurate business profiles and real reviews, and saying that changes take time to be picked up.
