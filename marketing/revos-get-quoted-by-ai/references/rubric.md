# Rubric: what exceptional looks like

Score the kit, the workbook and the site files before delivery. Every criterion must pass. If one fails, rework the output; do not caveat it.

| # | Criterion | Pass when |
|---|---|---|
| 1 | Questions are the buyers', traced | Every panel question is tagged heard (the buyer's exact words, quote found in what the founder pasted) or derived (from offer words the founder used). None is invented, none holds the business name, a local business keeps its place in at least three run-first questions. `queries.py validate` prints 0 problems. |
| 2 | No rate without its sample | Every rate reads "x of y, n equals y" with its range; fewer than three runs is UNKNOWN; no score for an assistant the founder did not run; on a first visit there is no rate at all. Movement is called only when ranges do not overlap, and the kit says the test cannot show cause. |
| 3 | Every fact traces to the register | Every price, figure, place, name, link and credential in pages, JSON-LD and llms.txt is a confirmed register fact (prices and figures in the founder's own form), and no sentence adds a consequence or promise they did not state; declined facts appear nowhere; gaps are `[NEED: ...]` and the page is marked not finished. `claims_check.py` prints 0 problems. |
| 4 | Answer first, quotable | Each page opens with a 40 to 60 word answer block (by script) that stands alone and holds the place and the category; headings are the questions buyers ask; prices are in the text; the page is dated. |
| 5 | Files that pass, labelled honestly | JSON-LD parses, uses listed schema.org types, holds no placeholder, no rating or review the page does not show, and no FAQ markup unless asked; llms.txt matches the llmstxt.org shape; both are introduced as hygiene with no promised effect. |
| 6 | Each failure has a cause and a fix | Reach first (a blocked search crawler or an empty served page is the first finding, a training block is left as the founder's choice); on a return visit every failing question names one cause (unreachable, no page, not quotable, quoted not recommended, described wrongly) and its fix, and passing ones get none. |
| 7 | Honest limits stated | The kit says nobody can make an assistant recommend a business, that Google needs no special markup or files and ignores llms.txt, that rates are snapshots, and that nothing here guarantees a citation; dated sources carry their dates; no ranking, guarantee or manipulation appears anywhere. |
| 8 | A stranger can act today | The three actions are on the first page in a safe order (the baseline before publishing), the run protocol fits on one page, the retest date is set, the chat carries the headline in five lines, and everything is in the founder's language and number style. |
