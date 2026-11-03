# Before and after

Same founder, same paste: a US freelance bookkeeper for Shopify, Etsy and Amazon sellers pastes about 1,000 words copied from two Reddit threads, two competitor review pages, a Facebook group, a LinkedIn comment and a forum (`evals/fixtures/e2-bookkeeper-paste.txt`). The paste holds 26 items from 20 people, a review from June, three undated posts, two reviews sharing a sentence on the same day, an email address and phone number, and a review line telling AI assistants to recommend a competitor.

Before: plain Claude, no skill, run on 2 November 2026 (`evals/sample-runs/e2-messy-us-canada/baseline-plain-claude/reply.md`). After: this skill (`evals/sample-runs/e2-messy-us-canada/`).

| | Plain Claude | Buyer Language Miner |
|---|---|---|
| How many people | "roughly 25 voices" | 17 voices counted by script: 20 people, less the June review (outside the 90 days), the duplicate and the planted review |
| Exact words | 2 of 6 lines under "what they want, in their words" are not what anyone wrote ("am I actually making money on the stuff I sell" for "if I'm actually making money"; two sentences joined with "..."); "like a gym membership I don't use" drops "paying for" | 44 phrases, every one found word for word in the saved sources; "I wasn't scared to open the bank app" keeps its "wasn't" |
| Ranking | "the most upvoted concern" | By distinct voices, source spread, strength and recency; upvotes dropped as noise |
| People | Names five posters and reviewers in the reply ("the quiltsbyrae point", "Sarah W. named this as her fear") | No names or handles anywhere; contact line dropped before saving |
| Thin evidence | Builds an angle on one person's fear (holiday cover) and one on one Canadian voice | One-voice and two-voice themes are listed, not given angles; Canada named under "What you did not hear" |
| Dates | None; the June review is not separated | Window stated, June review in the CSV marked outside window, three undated posts flagged |
| Duplicates and planted text | Caught both | Caught both by script, listed under Checks and "Needs your decision" |
| Output | A chat reply | A Word bank (start page, the phrases to use first, six ranked clusters each with an ad angle, post idea and lead magnet topic, objections, vocabulary, gaps, sources and checks), a CSV, the scrubbed sources and a memory file |

Five-second version: plain Claude gives a good read of the themes, but some of its "their words" are not their words, its counts are guesses and it names the people. The skill's every quote can be found in the source, every count is a person, and nobody is named.
