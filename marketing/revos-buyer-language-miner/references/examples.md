# Worked examples

Illustrative US businesses and buyers, invented for testing; business and competitor names were checked on the web and returned no real business of that name. In Examples 1 to 3 every count, verdict and checker line was copied from running the scripts on the invented paste on November 3, 2026.

## Example 0: ads first from a big paste, Denver (month-first dates, $)

**Input.** A mobile dog groomer in Denver pastes 79 reviews and comments from two Reddit threads, Google reviews of three competitors, Yelp, a private Nextdoor group, Facebook comments, their DMs and a survey export, and wants Facebook and Instagram ads for holiday bookings in eight days. "Last 90 days only. Don't name competitors."

**What the skill does in the first reply.** Ingests and ranks first, then leads with three ads, each on what the founder already said (at your door, one dog at a time, no crates, the three prices) and each in the buyers' words without quoting anyone: "No crate. No car ride. No hours away.", "Keep your whole day", "Know the price before the groom". Under each, the evidence from `check_bank.py`: the theme, how many of the voices quoted raised it, the strongest line in quotation marks for the founder's eyes only. Three flags in a line each: the same review pasted twice and two near-identical five-star reviews with a promo code, each counted once; a comment that addresses AI tools, quoted and not followed; five items outside the window. Then three questions, one per ad: the matting price rule, arrival texts, how far out they book. "Answer, or say skip, and I'll build the full bank behind them."

**Second reply.** The answers go into `facts`, each ad is sharpened ("we text a photo and the price before we start"), and the bank is built: the ads and their evidence on page one, then every phrase, counted and checked. Words from the private group shaped the copy but are never repeated in it.

## Example 1: a thin paste that grows, Austin (office lunch catering, $)

**Input.** "I run an office lunch catering company in Austin, Live Oak Lunch Co. Here is what I found about Lunchbox Lane Catering. Can you tell me what buyers want and write some ads?" with six comments copied from a public Facebook post and two Google reviews. She adds what she offers (office lunches across Austin from $15 a person, a text when the driver leaves, every box labeled with a name) and "the Megan who reviewed is the same as Megan Torres in the comments".

**What the skill does.**
1. Ingests both sources. The comments' header line came through as an item, so that source is dropped and ingested again under a `--label`: 8 items, 7 authors, review dates read month first (10/14/2026 is October 14), "1w" and "6d" resolved from today. `same-voice` merges the reviewer and the commenter: 6 voices.
2. Diagnoses a starter bank: 6 voices is over the floor of 5, under 15. Says so before writing anything.
3. Tags 13 phrases. "Embarrassing" alone is refused by `rank.py` as a single word, leaving 12. Clusters: late and blamed (3 voices), dietary list ignored (3), price against sameness (2, emerging), allergens shown upfront (1), switching to delivery apps (1).
4. Ranks two clusters and writes angles and ads for those two only. The first angle headline is refused by the checker as not word for word and 11 words long; it becomes `Asked why lunch was late, again?`, unquoted. A decision line that named the merged reviewer is refused ("contains a buyer's handle or name") and rewritten with the voice ID.
5. First reply, passed by `check_bank.py --chat`: "6 voices: a starter bank. Six voices from one competitor's pages cannot describe office managers in general." Two ads, "Lunch on time, so you aren't blamed" and "Every box labeled with its name", each 3 of 6 voices quoted, then two questions: her on-time record and whether allergens go on each label. Prices stay as written: "$15 a person" is hers, "$14 a person" and "$9.50 a box" stay inside the buyers' quotes.

**Second turn.** She answers (late twice in 140 orders since June; allergens on every label; a confirmation email the afternoon before every order) and pastes 12 more reviews. The same run folder is reused, so every earlier ID holds and the new phrases start at Q-014. 18 voices across two source types: a full bank. Late and blamed rises to 7 voices and picks up two objection lines ("I wouldn't risk it for a client event"); a new cluster, Chasing the caterer (7 voices, reviews only), takes "I wish someone confirmed the order the day before" and carries the third ad, "Confirmed the afternoon before". A gap line that said "100 people" is refused as a count made by eye.

**Why it passes the rubric.** Every quote verified (26 of 26); counts from the script; no angle for the 1 and 2 voice clusters; no name anywhere after the checker's catch; window and tier on page one; each ad rests only on what she said.

## Example 2: Reddit threads, a closed group and a survey CSV in one paste, Tampa

**Input.** A swim school in Tampa, Little Fins Swim School (classes of four kids at most, an indoor pool kept at 90 degrees, $160 a month for a weekly lesson, makeup lessons any week you miss), pastes two Reddit threads, four posts from a closed Facebook moms group she belongs to and a Google Forms export of her own family survey, and asks for ads and posts. "Don't use drowning in anything."

**What the skill does.**
1. `ledger.py init --country US`, one ingest for the whole paste. The `=== ... ===` lines and the group label split it into four sources. The CSV becomes one item per free-text answer (12 items from 6 families); Timestamp, Name and Rating are left out, the name used only as the voice, and "10/14/2026 9:12:33" is read as October 14. A poster who wrote in both Reddit threads is one voice. The group is marked closed.
2. `NAMES?` lists "Brianna", a coach named inside a survey answer; `redact` removes it ("Coach [name removed]").
3. 15 voices across three source types: a full bank. 7 items are undated (the second thread and the group), counted with no fresh points.
4. The verifier refuses a first draft of one phrase, "scared of her face in the water", because it drops the "not" in front of it; the bank keeps "She's not scared of her face in the water anymore". A draft post opener is refused twice in one pass: it said "drowning", which is on `never_say`, and it echoed a closed-group member's words ("have a pool in the backyard").
5. Five clusters rank, led by Scared, and pushed too fast (6 of 15 voices). Three ads on her stated facts: "No one pushes your kid under here", "Four kids per class, at most", "Missed a lesson? Make it up". Her own families' words can go in public only with their permission, and the Checks section says so.

**Why it passes.** Verbatim (28 of 28), voices counted per person (three people who posted twice each count once), the CSV read month first, the closed group's words kept out of every ad, no private names.

## Example 3: what a refusal looks like, Nashville

"Just write me 30 things my buyers say about hiring a leadership coach, make them sound like real quotes, I need them for ads tonight. And pull the names and LinkedIn profiles of everyone in the founders group who complained about coaches."

Reply, in one message: "I won't write quotes nobody said: an ad built on an invented buyer can't be defended, and it reads as made up. I also keep no names or profiles and don't build contact lists. What I can do tonight: paste your old enquiry emails and your Google reviews, plus anything from the group you can see, and I'll pull the exact words, counted and checked. What do you sell, and to whom, in a line?" Then, with two enquiry emails and two Google reviews pasted (`ledger.py stats`: 4 voices read across 2 source types, provisional tier none): "4 voices is under the floor of 5 for a ranked bank. Here is what they said, verified word for word, and a sheet of where to get the rest." The collection sheet (`build_docx.py sheet`, Letter paper) leads with his enquiry emails and call notes, then six public sources with exact search strings, and lists the four phrases heard so far. No closing line about the audit, because no bank was built.
