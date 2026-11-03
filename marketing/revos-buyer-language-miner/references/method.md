# Method

How a run works, start to finish. Contents:

1. What the bank is for
2. The paste route
3. Counting: voices, windows, floors and the score
4. The web route
5. Return runs
6. Revisions
7. Where the method comes from

## 1. What the bank is for

Founders write ads and posts in their own words, which are rarely their buyers' words. The skill's first job is the ads: two or three the founder can run, written in the words buyers used, about the reader's own situation, with no stranger quoted. The bank is the evidence behind them: it collects what buyers actually said, keeps it exact, counts how many different people said each thing, and turns the strongest clusters into three working outputs: an ad angle, a post idea and a lead magnet topic.

It is good evidence for the words buyers use and whether a pain keeps recurring. It is not evidence of market size, of what people would pay, or of whether what they say is true. The document says this on page one.

## 2. The paste route

The paste route must carry the whole job on its own: web reach is patchy, and a founder's own enquiries, reviews and call notes are often the best source anyway.

1. **Init the ledger** with the business name, country (two letters), today's date, the window and the competitors named. The fresh band is the last 30 days, or half the window when the window is shorter. The country sets the date order: `03.10.2026` is 3 October in Germany; `10/03/2026` is October 3 in the US. A date that cannot be a month in the country's order (29/09/2026 in a US paste) is read the other way, which handles mixed pastes.
2. **Ingest each paste exactly as given**, piped through stdin so the original is never written to disk. The script:
   - splits the paste into sources at header lines (`[...]`, `## ...`, `=== ... ===`, `Source: ...`) and at label lines a founder types ("Google reviews - Greenleaf Garden Services", "Facebook group: Constantia Neighbours (closed group)", "Own emails", "my enquiry emails (last few weeks):");
   - splits each source into items: `Name: text` lines (names with particles such as "Mark van der Merwe" included), author lines with stars and date on one line ("Anand R.  ★★☆☆☆  2 months ago", "Name, 2 weeks ago, 2 stars", `user · 3 weeks ago`), review headers stacked with no blank line between reviews (name, stars and date, text, repeated), lines that are each wrapped in quotation marks, or blank-line blocks; a pasted spreadsheet or survey (comma, tab or semicolon) becomes one item per free-text answer, the name column used only as the voice and columns of one-word answers left out; "Anonymous" and similar are read as no author;
   - drops interface noise (points, Like, Reply, Share, Helpful, Local Guide, review counts);
   - reads ratings (stars, "Rated 2 out of 5", "4/5", "3 Sterne") and dates (absolute, relative such as "3 weeks ago", "vor 2 Wochen", "3w"); a header date applies to a one-item source as exact and to a thread as approximate; a date with no year is flagged for one question, never guessed;
   - turns every author into a voice ID (V-01) and stores only a one-way code of the handle; removes emails, phone numbers (spaced, dashed or a bare run of 9 to 13 digits), links and @handles; drops lines that held nothing but contact details; keeps a one-way code of each removed contact so a shared phone number can still be spotted;
   - flags text addressed to a model and leaves it out of every count; where the instruction follows a buyer's own words in the same item, the item is split at that sentence and the words before it are kept;
   - flags a suspected duplicate, counted once, when two different voices share a phone number, email or link, share more than 60 per cent of their five-word runs, or share 40 per cent or an identical sentence of eight or more words within three days; a shared sentence further apart is listed under Checks and both are counted; and flags any source where more than 40 per cent of dated items fall on one day as a burst. Excluded items and text addressed to a model are left out of these checks;
   - marks a source closed when its label says closed or private, or `--closed` is passed;
   - lists `NAMES?`: capitalised words that may be private people. Each is settled with `redact` (a private person) or `keep` (a brand, place or ordinary word) before the build will run.
3. **Check the split.** Every SOURCE line shows how it was split, and `CHECK THE SPLIT` lines name an item that may hold two posts. If an author was read as text or two reviews ran together, `drop` that source and ingest it again with separator lines added. `drop` removes the items and their saved file completely and never reuses an ID; `exclude` is for a source the founder rules out, and blanks its text. Never change a buyer's word to make a split work.
4. **Tag and cluster** (`references/tags-and-intensity.md`). Claude judges meaning; the scripts count. A phrase is a whole, unbroken run of the buyer's words. One item can give several phrases with different tags in different clusters.
5. **Rank** with `rank.py`. Read the tier and the table before writing anything.
6. **Write two or three ready-to-run ads first**, on the top ranked themes and only on what the founder stated, in the buyers' words without quoting anyone, then the angles, post ideas and lead magnet topics for the ranked clusters only (`references/angles.md`).
7. **First reply: the ads, their evidence, the questions.** The evidence lines come from `check_bank.py`; the questions are the facts that sharpen each ad, asked before the bank is built.
8. **Second reply: sharpen, check, build, learn.**

## 3. Counting: voices, windows, floors and the score

- **A voice is a person.** One person posting three times across two threads is one voice. Items with no author shown each count as their own voice, and the Checks section says that two of them could be one person. When the founder knows two posters are one person, `same-voice` merges them.
- **Window.** Default 90 days to today, with the last 30 marked fresh. Items outside the window stay in the CSV marked `outside window` and are never ranked. Undated items are counted but earn no fresh points. The founder can choose 30 days or 12 months.
- **Voices read and voices quoted.** The ledger counts every person read; the bank's tier counts only the people with at least one verified phrase in the bank. A vendor ping, a suspect review or a one-line question can be read without being quoted, and then it does not lift the tier. The document shows both numbers.
- **Floors** (working defaults, stated as such, on voices quoted): under 5 voices in all, no ranked bank; 5 to 14, a starter bank with at most five clusters ranked; 15 or more across at least two source types, a full bank with at most ten. A cluster needs 3 voices to rank; 2 is emerging (shown, not ranked); 1 is held back. The 3-voice line follows Corey Haines' confidence levels (high at three or more independent sources) and the floor of 5 his minimum of five independent data points before drawing messaging conclusions. Practitioners aim far higher (30 to 50 reviews; Copyhackers works with 85 or more), so the document calls these floors, not targets.
- **Score out of 100** (working defaults): distinct voices up to 10 at 4 points each (40), distinct source types up to 4 at 5 each (20), mean intensity scaled to 25, share of voices in the fresh band times 15. Spread across source types matters because language that shows up in two or more kinds of source is more likely to be a real pattern than one thread's in-joke.
- **Never by engagement.** Upvotes and likes measure a post's popularity, not how many buyers feel something. A viral thread must not outrank ten quiet buyers who said the same thing. Engagement figures the founder pasted are dropped as noise.

## 4. The web route

Only when the session has web search or fetch tools, and only for public pages. Every step has the paste route as its fallback, and the deliverable is the same.

1. Build 8 to 12 searches from the niche's own words crossed with intent frames: "frustrated with", "alternative to [competitor]", "[competitor] review", "looking for a [role] for [niche]", "how do you handle [job]", "worth it", "switched from", "regret", "not worth it", "overpriced".
2. Search results decide where to look. They are never quotes: a search summary is a paraphrase.
3. Open a page, then log it: `ledger.py opened --run <run> --url <url> --result ok|refused|login|empty|snippet-only [--reason ...]`. Only text read on an opened, logged page can be ingested, with `--arrived web --url <url>`.
4. **Summarising fetch tools.** Some fetch tools answer over the page and quote only short fragments, paraphrasing the rest (seen in testing on 2 November 2026: a forum page and a review page came back as summaries with quoted excerpts capped at about 125 characters). From such a tool, ingest only the text it presents as quoted word for word, each fragment as its own item, and never the paraphrase around it. Where a tool that returns the page's text is available (a browser page-text tool), prefer it.
5. Never log in, never pass a CAPTCHA or a login wall, never touch a private group, never open a person's profile. A refusing source is logged and appears under "Could not read" with the paste instruction for it.
6. The cap: 25 page opens or 20 voices from the web, whichever comes first, and stop after three pages in a row add no new voice. The ledger prints `STOP THE WEB ROUTE` when a limit is reached. Then build from what you have and hand over the collection sheet for the rest.
7. Things seen in testing: review sites often show newest or best first, so the first page can be all five-star and years old (outside any 90 day window); "Invited" or "Verified" labels on reviews mean the business asked for them; general searches for a niche return vendor blogs and guides, which are what sellers are told, not what buyers say, and are never ingested as buyer language.

## 5. Return runs

1. `memory_tool.py read` writes `previous.json`; `ledger.py init --previous` loads the earlier phrases with their IDs, voice codes, dates, tags and clusters. They were verified on their own run and are not re-checked against sources that may no longer exist.
2. A voice code from last time that appears again (the same handle) is the same voice.
3. New phrases continue the numbering. Reuse an earlier cluster ID when the meaning is the same; give a new ID otherwise. Earlier phrases join their old cluster unless placed elsewhere.
4. `rank.py` prints CHANGE lines: new, rising (more voices and new phrases), steady, faded (no new phrase this run), and phrases now outside the window. The document's "What changed since last time" section is built from these.
5. Active learnings apply at their step: an exclusion at Ingest (`ledger.py exclude S-03 --reason "learning 1: different segment"`), an angle-type ban at Angles (`avoid_angle_types` in `bank.json`), a window at Init, a vocabulary merge at Cluster.

## 6. Revisions

By cluster or phrase: drop, merge, split, retag, rename, angles for one tag only, treat a source as another segment (exclude it, or rerun with only that source). Edit `bank.json`, rerun `rank.py` and `check_bank.py`, rebuild. At most three rounds. A change that is not measurably better is reverted.

## 7. Where the method comes from

Re-expressed, not copied: Joanna Wiebe's review mining at Copyhackers (search for customer language, sort it by what it does, count how often); Corey Haines' `customer-research` skill (confidence by number of independent sources, a minimum of five data points, review reading order, sample-bias notes; MIT); Big Flare's review mining playbook (only quote what was read on a page; access quirks; MIT); Sherif Butt's `voice-of-customer` (what this kind of evidence is and is not good for; objection-shaped searches; MIT); Aatir Abdul Rauf's `voc-claude-skills` (count distinct events, not mentions; the model clusters, code counts; MIT); Bob Moesta and Chris Spiek's four forces of progress (the tag logic). Notices are in `LICENSE.md`.
