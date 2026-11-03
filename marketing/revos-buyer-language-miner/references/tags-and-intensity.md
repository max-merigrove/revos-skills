# Tags and intensity

## The five tags

The tags follow the four forces that move someone to switch (Moesta and Spiek): pain and trigger push them away from today, outcome pulls them towards something better, objection is the anxiety that holds them back, alternative is the habit of what they already use. One phrase gets one tag: the one that says what the phrase does for a buyer deciding.

| Tag | What it is | Test | Example (illustrative) |
|---|---|---|---|
| pain | What is wrong now, in their words | Would they say it while still stuck? | "just a PDF of numbers" |
| trigger | The moment or event that made them look | Can you put a date or a scene on it? | "Got a letter from the tax people and panicked" |
| objection | What makes them hesitate to buy, or what went wrong with someone like you | Would it stop them signing? | "Nobody told me upfront" |
| outcome | What they want, or what good looked like when they got it | Is it the after, not the before? | "a one-page summary every month instead of 40 tabs" |
| alternative | What they use, tried or compared instead: a spreadsheet, a competitor, a big firm, doing nothing | Does it name another way of getting the job done? | "I did my own books in a spreadsheet for 2 yrs" |

Edge cases:
- A complaint about a competitor is an objection when it would make someone hesitate about anyone like the founder ("fees went up 30% after the first year with no warning"), and a pain when it is simply what is wrong.
- Praise for a competitor is an outcome: it says what good looks like ("Flat fee, no surprises").
- "I just want..." is an outcome even when it is said angrily.
- A question asked in a thread ("how do you even find a bookkeeper who knows inventory") is usually a pain.
- If a phrase genuinely does two jobs, take the one it does in the sentence it came from; never duplicate a phrase across tags.

To fold `alternative` into `pain`, set `FOLD_ALTERNATIVE = True` in `scripts/rank.py`.

## Intensity, 1 to 3

| Score | Meaning |
|---|---|
| 1 | Mentioned in passing, no feeling attached ("We switched from a big firm to a freelancer") |
| 2 | Clearly felt or clearly wanted ("never once got a report I could understand") |
| 3 | Strong, with a stake marker in the same item |

A 3 needs a stake marker, written in `bank.json` as `kind: words`, where the words are copied from the item:

- `money`: an amount, a price, paying ("money: quote me double")
- `time`: a duration or a wait ("time: 6 weeks")
- `event`: a named moment ("event: the week before filing")
- `feeling`: a feeling word ("feeling: scared", "feeling: resent")
- `repetition`: it keeps happening ("repetition: Fourth one in three years")

`rank.py` refuses a 3 without a marker, or with marker words that are not in what the person said. The fresh-eyes reviewer samples five intensity scores.

## Phrases

- A whole, unbroken run of the buyer's words, two words or more. Capitalising the first letter is fine; nothing else changes.
- Never join two statements, never cut out the middle, never add a bracket or an ellipsis.
- Keep the "not": "I wasn't scared to open the bank app", never "scared to open the bank app". The verifier fails a phrase whose sentence has a negation directly before it.
- Keep their spelling, capitals, typos and numbers exactly ("2 yrs", "DO", "S$9.50 a box", "3,5 Monate").
- In another language, the phrase stays in that language. If the founder wants an English reading, add `"reading"` beside it; it is shown as a reading, never inside the quote.

## Clusters

- Group by what the buyer means, not by the words they share. "Am I actually making money" and "where the money went each month" belong together.
- One cluster per phrase. A cluster of one is fine (it is listed under "Heard once").
- Name each cluster plainly, in the founder's language, as a buyer would recognise it ("Price and scope surprises", not "Pricing transparency concerns").
- Do not split a cluster to make more of them rank, or merge two to push one over three voices. The fresh-eyes reviewer asks whether any cluster mixes two meanings.
