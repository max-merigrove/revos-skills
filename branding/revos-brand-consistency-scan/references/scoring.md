# How the score works

Everything here is done by `scripts/score_consistency.py`. The constants live in one place, `scripts/scan_common.py`, so they can be changed without touching the logic. They are working defaults set on 20 October 2026, for Merigrove to confirm.

## Asset weights

| Asset kind | Weight | Why |
|---|---|---|
| Proposal, sales deck, onboarding email, invoice, client email | 3 | Read by a buyer who is about to pay, or has just paid. A contradiction here is where a good call turns into a stalled proposal. |
| Website | 2 | Where most buyers check you before a call. |
| LinkedIn | 1.5 | Read often, but as social proof. |
| Instagram, other social, bio, email signature, other | 1 | Glanced at. |

## Question weights

Who you serve 25, what you do 25, the result you promise 20, why you 20, what to do next 10. Total 100.

## The arithmetic, per question

Every pair of assets that answer the question is compared. Each pair is weighted by multiplying the two assets' weights. The pair scores:

| The two answers are | Value |
|---|---|
| The same (same group letter) | 1 |
| Compatible (one is a narrower or broader form of the other) | 0.5 |
| One or both assets silent | 0.25 |
| Different | 0 |

The question's points = its weight x (sum of pair weight x value) / (sum of pair weights), rounded to a whole number. The total is the sum of the five rounded points, so the strip on the report always adds up.

A question nobody answers scores 0.

### Worked example (Fernhill Growth, illustrative)

Who you serve: website "ambitious brands" (A, weight 2), LinkedIn "B2B SaaS founders" (B, 1.5), proposal "your team is stretched" (C, 3). A and B compatible, A and C compatible, B and C different.

| Pair | Pair weight | Value | Weighted |
|---|---|---|---|
| Website, LinkedIn | 3 | 0.5 | 1.5 |
| Website, proposal | 6 | 0.5 | 3 |
| LinkedIn, proposal | 4.5 | 0 | 0 |
| Total | 13.5 | | 4.5 |

25 x 4.5 / 13.5 = 8.3, shown as 8 of 25.

Because pairs multiply weights, a proposal that disagrees with everything costs far more than a LinkedIn headline that does.

## Bands

| Score | Band | Reading |
|---|---|---|
| 85 to 100 | Consistent | A buyer who reads everything hears one story. |
| 65 to 84 | Drifting | One story, with cracks a careful buyer will notice. |
| 40 to 64 | Split | A buyer who reads two of these could describe two different businesses. |
| 0 to 39 | Different stories | Each asset tells its own version of the business, so a referral has no one sentence to repeat. |

The bottom band says "different stories", not "contradicting itself": three assets that each pitch a slightly different buyer score the same as flat contradictions, and a founder who hears "contradicting" for drift is likelier to dismiss the score than act on it. The arithmetic is unchanged.

## Ranking the contradictions

**Facts first.** Where two assets state different facts (a team of four against a team of six), the report and the Word file lead with them, whatever they cost in points: a buyer who checks both will ask which is true, and that question can stall a proposal on its own. Claude lists them in the extraction's `facts`; `score_consistency.py` suggests team-size conflicts it finds (CHECK FACT). Every fact needs an edit or `[NEED: which is true]`.

A question is a contradiction when at least one pair of answers is different. Contradictions are ranked by the points they cost (weight minus points), then by whether a client-facing asset is involved, then by question weight. The report shows the top three side by side; the Word file shows them all.

The two quotes named in the headline are the heaviest asset holding the answer with the most weight behind it, and the heaviest asset that contradicts it.

## Return runs

- **Consistency** is worked out the same way every time, so the movement since the last scan is real. Assets the founder did not paste again keep their saved quotes.
- **Alignment** is new on a return run: each asset's answer against the agreed answer the founder chose last time, weighted by the asset's weight, same values as above. It answers "have my edits landed?" while the consistency score answers "do my assets agree with each other?"
