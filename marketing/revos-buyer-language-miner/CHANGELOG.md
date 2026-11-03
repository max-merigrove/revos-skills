# Changelog

## 1.5.0 (2026-11-02)
Improvement round, second pass (i2). In i1 plain Claude was slightly preferred on the big paste because its final ads carried every fact the founder gave (a second-dog discount, a pinned answer on parking and hookups, what to show), and a grader marked the Cape Town run down for ads and openers that echoed reviews and a closed-group post too closely.
- Every fact the founder gives now lands somewhere usable: the ad it sharpens, an offer in the ad it suits, or `with_ads`, the lines for the pinned comment or booking page answering what buyers ask before they book. Each ad also says what to show (`visual`), from the founder's own material.
- Echo check: five words in a row from one buyer (four of them real words, pronouns folded, so "show me" and "show you" match) in an ad or headline, six in an opener or title, four from a closed group, and any number from a closed-group member's own story are refused. Runs the founder wrote themselves are exempt.
- Headline craft: plain and concrete, read aloud, the founder's answer or the buyer's situation.
- `ledger.py stats` prints a DUPLICATE line per duplicate with its reason, so the chat describes each one correctly.
- The ledger no longer reads "my" inside a quoted thread title as the founder's own source.

## 1.4.0 (2026-11-02)
Improvement round (approved by Jack): reshaped ads first.
- The first reply leads with two or three ready-to-run ads in the buyers' words, each resting only on what the founder stated, each with its evidence (voices out of voices quoted, source types, the strongest line) printed by `check_bank.py`; at most three questions follow, each the fact that sharpens one ad (`ad_draft.sharpen`), asked before the bank is built. The bank (document, CSV, sources) follows in the second reply, with the ads on page one.
- Public copy is unquoted by default: no buyer's words in quotation marks in an ad, headline, post opener or title, no run of eight words from one item (five from a closed group); the verbatim quote stays in the bank. `quote_ok` only for the founder's own customer with permission. No competitor named in a ready-to-run ad unless asked; `never_say` list enforced.
- `check_bank.py` reads counts written in words or digits: "N of M voices", "N voices have no date" (against voices, not items), "N items are undated", "N outside the window"; `--chat` checks a drafted reply before it is sent.
- What stops them: each heading says how many of the theme's voices raised an objection or named an alternative.
- Ledger: headers ruled with dashes start a source; "Name · City, ST · 1 star · date" and "Name from Place · 2 weeks ago" read as review headers; the same review pasted twice is one suspected duplicate; a long survey question that mentions "mobile" or "name" is no longer skipped as a contact column; Nextdoor reads as social.

## 1.3.0 (2026-11-02)
End-to-end round 2: the skill won, but only slightly; plain Claude asked the founder three direct questions and wrote two well-judged ads from the answers.
- The first delivery now ends with up to three plain questions, one per top theme, each the fact that would let that ad be written ready to run; the next reply writes those ads and says where the founder's rule covers only part of what a buyer described.
- Chat in plain words: themes, "to confirm", no IDs, kept short.
- The CSV lists items read but not quoted that sit outside the window, are suspected duplicates or address a model, marked so, as the Checks line says.
- Quote marks in headlines: dropped only when the words read as the reader's own situation, never as a claim.
- The document no longer quotes an outside figure for how many reviews practitioners collect; single-voice vocabulary goes on one line.

## 1.2.0 (2026-11-02)
End-to-end round 1 found plain Claude slightly preferred by a founder with a Friday launch, because it handed over finished ad copy while the skill stopped at angles.
- Ready to run: for a ranked cluster whose facts the founder has confirmed, the skill now writes the ad (headline, primary text, call to action) from the buyers' words and those facts only, checked like everything else, shown in chat and in the document. It tests each buyer's situation against the founder's rule and says where it falls short.
- The founder's own headline wording wins: over eight words is a warning, over fourteen a stop.
- No round limits announced; counts in chat come from script lines; columns and notes go through the bank, never by editing a built file.
- The Checks window line no longer says items without phrases are in the CSV.
- Memory: saving twice in one run replaces that run's source rows and history line instead of repeating them; a repeated learning becomes active instead of a second row.

## 1.1.0 (2026-11-02)
Blind-test fix round.
- Privacy: author names with particles ("Mark van der Merwe") are read as authors; bare 9 to 13 digit mobile numbers are removed; the build refuses while any possible name (`NAMES?`) is unsettled or a long digit run is left in the saved text; `ledger.py keep` marks brands, places and ordinary words; excluded items have their text blanked.
- Parsing: label lines ("Google reviews - X", "Facebook group: Y", "Own emails") start a new source; a pasted CSV or spreadsheet becomes one item per free-text answer with names used only as voices; "Name ★★ date" and "Name, date, stars" lines are read as author, rating and date; reviews stacked with no blank lines are split; lines each in quotation marks are separate items; "Anonymous" is read as no author; a CHECK THE SPLIT warning names items that may hold two posts.
- Duplicates: a shared phone number, email or link across voices, or a shared sentence or 40 per cent overlap within three days, now marks a suspected duplicate; shared sentences further apart are listed under Checks; "none found" appears only when nothing was flagged; excluded items no longer swallow corrected re-ingests; `set I-nnn dup=no` clears a flag the founder knows is wrong.
- Tier: decided on voices quoted (people with a verified phrase in the bank), shown beside voices read.
- `ledger.py drop` removes a bad split for a clean re-ingest; IDs are never reused.
- `init` with a 30 day window no longer stops: the fresh band defaults to 30 days or half the window.
- A planted instruction is split from the buyer's real words before it, which are kept.
- Closed groups are marked from their label or `--closed`; Checks says so automatically and public copy (headline, opener, title) may not quote them.
- Document: "The phrases to use first" heading, singular counts ("1 voice", "1 phone number"), a default paste line on the collection sheet, and a "quickest to run" summary line for the chat.
- Writing check allows "what buyers said"; still refuses "buyers want".
- Description: adds survey and NPS comments, complaints about a competitor and hooks from customer emails; steers away from replying to reviews and choosing testimonials.
- Evals: the blind test's two runs added as e7 (India, messy paste and survey CSV) and e8 (South Africa, closed group, particle names).

## 1.0.0 (2026-11-02)
- First release.
- Paste route that carries the whole job: any mix of threads, review pages, comments, emails and call notes split into sources and items by script, authors turned into voice IDs, emails, phones, links and handles removed, the original paste never saved.
- Word-for-word verification of every phrase against the item it cites, failing any phrase that drops a "not" in front of it, any join, bracket or ellipsis.
- Distinct-voice counting, suspected-duplicate and burst checks, a 90 day window with a 30 day fresh band, date reading in the founder's date order (mixed formats handled), dates with no year flagged.
- Five tags (pain, trigger, objection, outcome, alternative), intensity 1 to 3 with stake markers, cluster scores out of 100, starter and full bank floors.
- Ad angle, post idea and lead magnet topic for ranked clusters only, typed by tag, with `[NEED: ...]` on any promise; competitor claims need two voices.
- Web route with a hard cap and a "Could not read" log; collection sheet when there is too little to rank.
- Return runs keep phrase IDs and show new, rising, steady and faded clusters; learnings apply at named steps.
- English and German document labels built in; any other language through a labels block.
