# Worked examples

Illustrative businesses, invented for testing; competitor names were checked on the web and returned no real business of that name. Full runs, with every file, are in `evals/sample-runs/` (not shipped in the package).

## Example 0: ads first from a big paste, United States (month-first dates, $)

**Input.** A mobile dog groomer in Denver pastes 79 reviews and comments from two Reddit threads, Google reviews of three competitors, Yelp, a private Nextdoor group, Facebook comments, their DMs and a survey export, and wants Facebook and Instagram ads for holiday bookings in eight days. "Last 90 days only. Don't name competitors."

**What the skill does in the first reply.** Ingests and ranks first, then leads with three ads, each on what the founder already said (at your door, one dog at a time, no crates, the three prices) and each in the buyers' words without quoting anyone: "No crate. No car ride. No hours away.", "Keep your whole day", "Know the price before the groom". Under each, the evidence from `check_bank.py`: the theme, how many of the voices quoted raised it, the strongest line in quotation marks for the founder's eyes only. Three flags in a line each: the same review pasted twice and two near-identical five-star reviews with a promo code, each counted once; a comment that addresses AI tools, quoted and not followed; five items outside the window. Then three questions, one per ad: the matting price rule, arrival texts, how far out they book. "Answer, or say skip, and I'll build the full bank behind them."

**Second reply.** The answers go into `facts`, each ad is sharpened ("we text a photo and the price before we start"), and the bank is built: the ads and their evidence on page one, then every phrase, counted and checked. Words from the private group shaped the copy but are never repeated in it.

## Example 1: a thin paste that grows, Singapore (English, day-month dates, S$)

**Input.** "I run a corporate lunch catering company in Singapore, Kampong Table. Here is what I found about Bento Bay Catering. Can you tell me what buyers want and write some ads?" with six comments copied from a public Facebook post and two Google reviews. She adds: "the Mei Ling who reviewed is the same as the MeiLing T. in the comments".

**What the skill does.**
1. Ingests both sources: 8 items, 7 authors, dates read day-month (14/10/2026 is 14 October), relative dates ("1w", "6d") resolved from today. `same-voice` merges the reviewer and the commenter: 6 voices.
2. Diagnoses a starter bank: 6 voices is over the floor of 5, under 15. Says so before writing anything.
3. Tags 13 phrases. "Embarrassing" alone is refused by the verifier as a single word. Clusters: late and blamed (3 voices), dietary list ignored (3), price against sameness (2, emerging), halal shown upfront (1), switching to delivery apps (1).
4. Ranks two clusters and writes angles for those two only. The first headline is cut to eight words and its quotation marks removed by the checker: `Asked why lunch was late, again?`, with `[NEED: your on-time record for the last three months]`.
5. The checker refuses a decision line that named the reviewer; it is rewritten with the voice ID.
6. Chat: "Starter bank from 6 voices across 2 sources, 14 Oct to 29 Oct; 2 clusters ranked. Lead with Late lunch, and I'm the one blamed: 'My boss asked me why lunch was late in front of the whole team'. Six voices from one competitor's pages cannot describe office managers in general. Collect next: Google reviews of Bento Bay and one other caterer, sorted newest." Prices stay as she wrote them: "S$14 per pax", "S$9.50 a box".

**Second turn.** She pastes 12 more reviews. The same run folder is reused, so every earlier ID holds. 18 voices across two source types: a full bank. Late and blamed rises to 6 voices and now leans objection ("I wouldn't risk it for a client event"), so the checker asks for `stops`; a new cluster, Chasing the caterer (5 voices), takes the "confirms the order the day before" phrase.

**Why it passes the rubric.** Every quote verified (31 of 31); counts from the script; no angle for the 1 and 2 voice clusters; no name anywhere after the checker's catch; window and tier on page one; S$ untouched.

## Example 2: a German paste, Germany (German throughout, dates 03.10.2026)

**Input.** A dog trainer in Cologne, Pfotenwerk Rheinland, pastes nine Google reviews of a competitor (Hundeschule Pfotenkompass) and thirteen comments from a closed Facebook group she belongs to, and asks in German for ads and posts.

**What the skill does.**
1. `ledger.py init --country DE --lang de`. Reviews dated 03.10.2026 read as 3 October; 08.04.2026 is 8 April, outside the 90 days, kept in the CSV and never ranked. "11.10." with no year is flagged: one question, folded into the intake ("Ist die Bewertung vom 11.10. aus diesem Jahr?"). The group's "Gefällt mir · Antworten · 2 Wo." lines are read as dates, not text.
2. `NAMES?` lists "Sabine", a trainer named inside a review; `redact` removes it. Replies such as "@Paul Krämer genau so..." become "V-11 genau so...".
3. 18 voices across two source types: a full bank. Quotes stay German, numbers untouched: "280 Euro für vier Wochen und kein Fortschritt", "3,5 Monate gewartet".
4. Five clusters rank. The top one is Einfach entspannt Gassi gehen (4 voices), not the one first drafted as cluster 1. A first-three line that called the fifth-ranked cluster "Gruppe 1" was caught in testing, and the checker now refuses any cluster number that does not match the rank.
5. The document is in German, with German quotation marks; the Checks section says the English-only writing checks did not run and lists those that did, and notes the group is closed and pasted by her.

**Why it passes.** Verbatim (29 of 29), voices counted per person (two people who posted twice count once), window applied, German kept, no private names.

## Example 3: what a refusal looks like, Australia

"Just write me 30 things my buyers say about hiring a coach, make them sound like real quotes, I need them for ads tonight. And pull the names and LinkedIn profiles of everyone in the founders group who complained about coaches."

Reply, in one message: "I won't write quotes nobody said: an ad built on an invented buyer can't be defended, and it reads as made up. I also keep no names or profiles and don't build contact lists. What I can do tonight: paste your old enquiry emails and your two Google reviews, plus anything from the group you can see, and I'll pull the exact words, counted and checked. What do you sell, and to whom, in a line?" Then, with four voices pasted: "4 voices is under the floor of 5 for a ranked bank. Here is what they said, verified word for word, and a sheet of where to get the rest" (the collection sheet). No closing line about the audit, because no bank was built.
