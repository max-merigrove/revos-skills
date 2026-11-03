# bank.json and sheet.json

## bank.json

Written by Claude in the run folder. The scripts fill in every count; never write a count into a field the scripts compute.

```json
{
 "business": "Tally and Twine Bookkeeping",
 "lang": "en",
 "english": "en-US",
 "offer": "Monthly bookkeeping for Shopify, Etsy and Amazon sellers",
 "buyer": "Small ecommerce sellers in the US and Canada",
 "uses_first": "Meta ads first, then posts, then a lead magnet",
 "avoid_angle_types": [],
 "never_say": ["load shedding"],
 "with_ads": [{"line": "The van brings its own water and power; we just need a spot on the street or driveway.", "where": "pinned comment and booking page",
               "facts": ["own water tank and generator, no hookups", "needs a street spot or driveway"]}],
 "phrases": [
  {"id": "Q-001", "item": "I-003", "text": "am I actually making money", "tag": "pain", "intensity": 3,
   "stake": "repetition: is the only question I care about"}
 ],
 "clusters": [
  {"id": "C1", "name": "Numbers with no answer", "means": "One line on what this tells the founder.",
   "phrases": ["Q-001", "Q-002"],
   "ad_angle": {"buying_reason": "...", "type": "the-after", "headline": "...", "need": ["[NEED: ...]"]},
   "post_idea": {"opener": "...\"three or more of their words\"...", "show": "...", "proof": "... or [NEED: ...]"},
   "lead_magnet": {"title": "...", "format": "...", "next_question": "..."},
   "stops": {"answer": "...", "where": "page"},
   "ad_draft": {"headline": "...", "primary_text": "...", "cta": "...", "facts": ["what the founder stated, in their words"],
                "sharpen": "the one question that would make this ad stronger", "visual": "what the image or video shows"}}
 ],
 "vocabulary": [{"term": "bookkeeper", "founder_term": "accountant", "kind": "category"}],
 "first_three": ["...", "...", "..."],
 "decisions": ["..."],
 "not_heard": ["..."],
 "next_collect": {"source": "...", "search": "..."},
 "checks_notes": ["..."],
 "labels": {}
}
```

Field rules:
- `lang`: `en` or `de` have built-in headings; for any other language add `labels` with the same keys as the `en` block in `scripts/build_docx.py` (the document is then in that language; the English writing checks do not run and the Checks section says so).
- `phrases[].id`: `Q-001` onwards. On a return run, earlier IDs are loaded from memory; do not reuse them for new phrases. Earlier phrases need not be restated unless they move cluster or change tag.
- `phrases[].item`: the item ID from `ledger.py list`. The phrase must be inside that item, word for word.
- `phrases[].reading`: optional English reading of a phrase in another language; never inside the quote.
- `clusters[].ad_angle`, `post_idea`, `lead_magnet`: only for clusters `rank.py` ranks. `ad_draft`: two or three per bank (one is a warning, none is refused), ranked clusters only, written on what the founder stated (`facts`), no `[NEED]` inside; the angle's own `need` may stay open beside it. `sharpen`: the question that would unlock a stronger version. `quote_ok`: only when the founder's own customer gave permission to be quoted. `stops`: required for ranked clusters that are mostly objection or alternative.
- `with_ads`: lines for the pinned comment or the page the ads link to, answering the questions buyers ask before they book, each resting on `facts` the founder gave. `visual` on each ad: what the image or video shows, from the founder's own material.
- `never_say`: words or topics the founder will not use; any public copy containing one is refused. `name_competitors: true` only when the founder asks for competitors to be named in ads.
- Quotation marks anywhere mean the buyers' words: anything in quotes must be found word for word in what that cluster's buyers said (or, outside a cluster, in any counted item). Cluster names and the founder's own words are never put in quotes.
- `avoid_angle_types`: from active learnings, for example `["cost-of-waiting"]`.
- `vocabulary[].term`: a word buyers used; `founder_term`: the founder's word for the same thing when it differs. The script counts voices.
- `first_three`: exactly three things to do this week: the first angle to use, the objection to answer where buyers land, the one source to collect next.
- `decisions`: anything the founder must settle (suspected duplicates, dates with no year, a source that may be a different segment).
- `not_heard`: who and what is missing: segments, countries, stages before and after the sale, source types, the founder's own buyers.
- `next_collect`: the one source to collect next and its exact search string.
- `checks_notes`: extra lines for the Checks section (a language note, anything the founder told you about a source). A closed group's note is added automatically from the ledger.
- Headlines, ready-to-run ads, post openers and lead magnet titles never put a buyer's words in quotation marks (unless `quote_ok`), never repeat eight words in a row from one item, and never five from a closed group.

## sheet.json

```json
{
 "business": "Hartwell and Pike Lofts",
 "lang": "en",
 "paper": "A4",
 "today": "2026-11-02",
 "intro": "optional; a default line is used",
 "heard": [{"item": "I-002", "text": "a phrase heard so far"}],
 "own_material": [
  {"name": "Your old enquiry emails", "search": "in your inbox: loft OR conversion OR quote", "copy": "the customer's own words, the date", "how_many": "all of them, about 30", "note": "..."}
 ],
 "sources": [
  {"name": "Google reviews of Gablecrest Lofts", "search": "Gablecrest Lofts reviews, sorted by newest", "copy": "the review text, star rating, date and link", "how_many": "20", "note": "read three-star first"}
 ],
 "paste_format": "optional; a default line is used. Paste it as it comes, one source at a time with a line saying where it came from. Names are fine; I remove them.",
 "listen_for": ["hypothesis in plain words, never in quotation marks"]
}
```

At least one `own_material` entry, at least six sources in all, each with `name`, `search`, `copy` and `how_many`. `heard` phrases cite ledger items and are verified word for word; pass `--run` so they can be checked.
