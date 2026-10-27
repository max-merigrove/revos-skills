# Writing hook options on the spot

The thumbnail's words are written fresh for each video, from two things only: the title and the payoff. Write three to five options, each from a different angle, then recommend one.

## The constraints

- Two to five words. Three is best. Six only if the sixth carries real weight.
- A phrase, not a sentence. No full stop.
- It says the half of the idea the title does not. If the title is "How I close the books in one day", the thumbnail should not say "Close the books in one day".
- It promises nothing the payoff does not deliver. A number on the thumbnail is shown in the video.
- In the founder's language, spelling and register. A precise accountant does not suddenly say "INSANE". If they write "color" it is "color"; if the channel is in Hindi, the words are in Hindi.
- Numbers in the founder's currency and style, as they wrote them ($10k, ₹5 lakh, A$4.20, 10万円). Never convert, never add a sign they did not use. A short form may round down, never up.
- No "more": give the number or the comparison.
- A number stays on the same line as the word it counts ("₹5 lakh", not "₹5 / lakh").
- No emoji: it prints as an empty box in a thumbnail typeface.
- In Chinese, Japanese and Thai, mark where a line may break with a space; it is not drawn.

## The angles

| Angle | Shape | Example (title: "How I close the books in one day") |
|---|---|---|
| Outcome | the result, stated flat | Month end in ONE day |
| Before and after | the change in two halves | Five days to one |
| Mistake or warning | the thing to stop | Stop closing on day five |
| Named object | the tool or asset the video shows | The one-day checklist |
| Curiosity, honest | an incomplete thought the video completes | The step everyone skips |
| Contrarian | the opposite of the common belief | Month end isn't a week |

The curiosity angle must still be paid off: "The step everyone skips" only works if the video names and shows that step. If you cannot say where, drop the option.

## Choosing the highlight

Pick what carries the promise (usually the number, the outcome or the surprising word) and set it as `highlight`. A number with its unit is one highlight of up to three words ("₹5.2 लाख", "10 hours", "$10,400"): it is sized, coloured or boxed as one and never split across lines. Use `focal` (a chip under the words) only when the number is a second idea next to a word-led hook ("40p" under "Coffee costs"); never both.

When the figure is the point, give it its own line (`एक साल में | ₹5.2 लाख | बचे`, `Crews full | $10,400`). The script then sets each line to fill the column, with the figure largest, so the words read as one designed block rather than a small paragraph. Count every word on the thumbnail, the unit included: "एक साल में ₹5.2 लाख बचे" is six words; "एक साल, ₹5.2 लाख बचे" is five.

## Drawing them, not just listing them

Each of the three styles carries a different option (`styles.<name>.hook` in the spec), so the founder sees three word options drawn, not one drawn and three listed in chat. Put the recommended words on the recommended style. The founder can then say "C's words in A's style", and that is one re-render.

## Presenting them

Show the options as a short list: the hook, its angle in a few words, and a mark on the recommended one with one reason. For example:

1. Month end in ONE day (outcome; recommended: it is the payoff in four words)
2. Five days to one (before and after)
3. The one-day checklist (named object; strongest if the checklist is downloadable)

Run `python3 scripts/check_copy.py --hooks <file>` on the options before showing them.

## Testing two hooks

When the founder wants to test, render the second hook in the recommended direction only, so the test is words against words and nothing else changes. YouTube Studio's built-in thumbnail test, where available on the founder's channel, compares them on live impressions; record the result in memory.
