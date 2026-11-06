# The JSON files the scripts read

All live in `<scratch>`. Keys not listed are ignored. Every script stops with a plain "STOP:" line if a file is missing or unreadable.

## settings.json

```json
{"business": "Peakline IT", "aliases": ["Peakline"], "domain": "peaklineit.example",
 "sells": "managed IT support", "buyers": "dental practices", "where": "Denver",
 "country": "US", "language": "en-US", "kit_language": "en-US", "english": "American",
 "decimal": "dot", "currency": "USD", "date_order": "MDY", "paper": "Letter",
 "engines": ["ChatGPT", "Perplexity"], "runs": 3, "quick": false, "cadence_weeks": 4,
 "platform": "Squarespace", "editor": "founder", "robots_owner": "you, in Squarespace settings",
 "competitors": [{"name": "Rival IT", "domain": "rivalit.example"}],
 "locations": ["Denver", "Cherry Creek"], "offer_words": ["managed IT", "dental practices"],
 "local": true, "today": "2026-11-03", "must": ["Denver", "dental"],
 "faq_markup": false, "reviews_shown": false, "no_entities": false}
```

- `country` sets paper and date order (from `locale_numbers.locale_defaults`) unless `paper` or `date_order` is given. `decimal` is `dot` or `comma`, from how the founder writes numbers.
- `must`: words every answer block holds (the place and the category).
- `no_entities`: true for languages that capitalise every noun (German), which turns off the capitalised-name check; numbers, prices and links are still checked.
- `kit_language`: the language tag stored in the kit (defaults to `language`).
- `reach_finding`: on a return run, the last reach finding, kept in memory.
- `english`: the founder's English ("American", "British", "Indian", "Australian"). American English gets American spelling in the kit's and workbook's fixed text (favorable, color); every other English keeps the spelling it has.

## facts.json (the fact register)

```json
{"business": "Peakline IT", "decimal": "dot", "currency": "USD", "allow": [],
 "facts": [
  {"kind": "price", "label": "Managed plan price", "value": "from $1,850 a month for up to 10 users",
   "status": "confirmed", "source": "founder said", "confirmed_on": "2026-11-03"},
  {"kind": "credential", "label": "A credential", "value": "", "status": "NEED", "source": "founder said leave out",
   "need": "one credential or client result you can stand behind"},
  {"kind": "other", "label": "Old contract line", "value": "Flexible 12-month agreements", "status": "declined", "source": "founder said it is out of date"}]}
```

`allow` also feeds the number check: a year or figure listed there may appear in a page. Dates in any style (2. November 2026, 02.11.2026, 02/11/2026, November 2, 2026) are read as dates, never as figures.

Kinds: name, location, area, service, audience, price, duration, team, person, credential, years, count, result, url, booking, phone, email, address, hours, language, other. `value` is exactly as the founder wrote it. Only `confirmed` facts may appear in pages and files; `declined` values must not appear anywhere. `allow` lists extra words the founder approved (rarely needed).

## panel.json

```json
{"business": "Peakline IT", "aliases": ["Peakline"], "locations": ["Denver"], "local": true,
 "offer_words": ["managed IT", "dental practices"],
 "questions": [
  {"text": "how much does managed IT cost for a small dental office", "family": "cost", "tag": "heard",
   "quote": "how much does managed IT cost for a small dental office", "source": "asked by a buyer", "page": "managed-it-cost-dental-denver"},
  {"text": "What does a managed IT provider do for a dental practice?", "family": "category", "tag": "derived",
   "source": "offer words: managed IT, dental practices", "page": "no page yet"},
  {"text": "...", "cut": true, "cut_reason": "buyers never compare these two"}],
 "branded": [{"text": "What does Peakline IT do and who does it work with?"}, {"text": "..."}, {"text": "..."}],
 "run_first": ["Q1", "Q4"]}
```

A heard message written to the founder rather than to an assistant keeps the buyer's words in `quote` and gets a reworded `text` with the offer words and the place, plus `"reworded": true`:

```json
  {"text": "Do food photographers in Austin shoot at the restaurant or in their own studio?", "family": "choosing", "tag": "heard",
   "reworded": true, "quote": "do you shoot at our restaurant or in the studio?", "source": "text message, a cafe owner"}
```

The kit prints both ("heard as: ..."). A heard question that is the buyer's exact words is kept as typed, with or without a question mark. Offer words and places are matched word by word across spellings (food photography is in "food and hospitality photography"; Wärmepumpe is in waermepumpe).

`run_first` (optional) overrides which questions run first, when the founder says so. `queries.py validate --out` adds `id`, `priority` and `quick`; for a local business it moves place-bearing questions up so three of the quick five carry the place.

## kit.json

```json
{"date": "2026-11-03",
 "read_first": {"read": "One sentence.", "actions": [{"kind": "baseline", "text": "..."}, {"kind": "reach", "text": "..."}, {"kind": "publish", "text": "..."}]},
 "reach_notes": ["..."], "reach_from_memory": "only on a return run that did not re-check reach",
 "pages": [{"slug": "managed-it-cost-dental-denver", "title": "...", "question_ids": ["Q2"], "where": "...",
            "facts_used": ["Managed plan price"], "needs": ["..."], "must": ["Denver"], "price": true}],
 "no_pages_reason": "only when no page can be written yet (for example an empty fetch and no paste)",
 "beyond": {"notes": ["..."], "actions": ["at most three"]},
 "next": {"fixes": [{"q": "Q4", "cause": "no page", "fix": "..."}],
          "accuracy": ["B1 on ChatGPT, run 1: says the studio has a team of ten; your register says Dana and one assistant."],
          "accuracy_ignore": [{"q": "B3", "engine": "Perplexity", "run": 2, "reason": "names the street, which is in Austin"}]},
 "retest_date": "2026-12-01", "not_checked": ["..."],
 "closing": "... [BUSINESS_AUDIT_URL]."}
```

`next.accuracy` holds wrong descriptions you found by reading the branded answers that the script did not flag; `next.accuracy_ignore` drops a flagged line that is not a real mismatch, with its reason. `closing` is the first-visit line until runs are scored (SKILL.md, Next step); build_kit refuses the return-visit line on a first visit.

## Page audits

`page_check.py audit <page> --label "Your home page" --json-out audit-home.json`: the label is how the kit names the page (in the founder's language), never the scratch file name. Lines that are the founder's own notes, a whole line in square brackets or an arrow note at the end of a line ("<- this is from Google"), are left out and listed as `founder_notes`.

Action kinds: baseline, reach, accuracy, publish, fix, presence, retest. Causes: unreachable, no page, not quotable, quoted not recommended, described wrongly.

## proxy.json (only with Claude's own web search)

```json
{"date": "2026-11-03", "rows": [{"q": "Q1", "text": "...", "domains": ["dentalitdirectory.example"], "named": ["Rival IT"]}]}
```

## pages.json (for memory)

```json
[{"slug": "managed-it-cost-dental-denver", "question": "Q2, Q6", "went_live": "2026-11-10", "address": "https://..."}]
```
