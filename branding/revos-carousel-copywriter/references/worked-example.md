# Worked example: from a voice note to the three outputs

Illustrative. The business, the figures and the note are synthetic.

## The input (a voice note transcript, as pasted)

"Right so I keep seeing this with the trades firms we work with, they're flat out, diary's full for six weeks, and the owner cannot tell me if last month made money. And when you dig in the quotes are basically last year's price plus a bit. Nobody has ever sat down and costed the job they do most, like the standard bathroom or whatever, because it's so familiar nobody thinks to. So the first thing we do, before touching any prices, is take the three most common jobs and write down hours, materials, travel, van, the lot, and put the total next to what they charge. Takes a morning. Then you've actually got a price list that means something. Cost the job then quote it, basically."

## Stage 1: the argument

A full diary says nothing about margin, and the first fix is costing the three most common jobs before any price moves.

Voice read from the input: short declaratives, "flat out", "the lot", "basically"; first person plural ("we work with"); direct, practical, no jargon. The carousel keeps the plainness and drops the filler.

## Output 1: the spec

```
CAROUSEL: Busy is not profitable
Argument: A full diary says nothing about margin, and the first fix is costing the three most common jobs before any price moves.
Platform: Instagram, 4:5 · 6 slides · Swipe arc: hook → frame → stakes → mechanism → payoff → close

Slide 1/6 · Hook
Headline: A full diary is not a *margin*.
  → emphasis: margin
Body: Every owner-run firm knows how busy it is. Few can say what their most common job makes.

Slide 2/6 · Frame
Headline: Every quote is a guess with a *number* on it
  → emphasis: number
Contrast:
  Left: A costed quote starts from what the job takes: hours, materials, travel, the van.
  Right: A guessed quote starts from last year's price and what the customer might accept.
Punch line: One protects the margin. The other hopes for it.

Slide 3/6 · Stakes
Headline: The job you do most is the one *never costed*.
  → emphasis: never costed
Body: It feels familiar, so nobody checks it. Familiar work is where a small loss repeats every week, unnoticed, for a year.

Slide 4/6 · Mechanism
Label: THREE JOB TYPES. ONE MORNING.
Body: Take your three most common jobs. Write down the hours, materials and travel each one carries. Set each total beside the price you charge for it.
Punch line: That is the whole exercise. It costs nothing but a morning.

Slide 5/6 · Payoff
Body: The price list starts to mean something. Quotes go out from the list, not from memory. And a quote a customer questions has a costing behind it.

Slide 6/6 · Close
Headline: Cost the job, *then* quote it.
  → emphasis: then
Body: A price you cannot cost is a price you cannot defend. The costing comes before the rise, every time.
Sign-off: NORTHGATE
```

Note: Full arc because the fix is clear and usable; no figures on the slides because the note gave none.

Word counts on the cards: 25, 47, 31, 42, 27, 25; set 197. All inside the Instagram budget (slide two is the heaviest at 47, under the 55 cap).

## Output 2: the caption

Busy every week, and still unable to say whether May made any money. That is where most of the owners we work with start.

Busy is a count of jobs. Margin is what each job leaves behind once the hours, the materials, the travel and the van are paid for. The two can move in opposite directions for a year before anyone notices, because the job you do most is the one you stopped checking.

The fix on slide four needs no software and no consultant: three job types, one morning, every cost written down. Do it before you change a single price.

If a price review is coming up, keep this for the morning you sit down to do it.

## Output 3: the Claude Design prompt

```
Build an Instagram carousel in my design system: 6 slides, portrait 4:5 (1080 x 1350), one canvas size for the whole set.

Use my design system's tokens, typefaces, colours, logo and components throughout. Do not introduce a colour, typeface or decorative element that is not in the system. Keep the layout quiet: generous space, one idea per slide, the type carrying the hierarchy. No hairline rules, no boxes or panels around the copy, no icons unless the system has them, no stock imagery.

Type roles, applied consistently on every slide:
- Headline: the largest line, the system's display or heading face; the word marked *like this* is the emphasis word, set in italic or in the system's accent, never in a different size.
- Label: a short tag set apart from the headline, small, in capitals with letter spacing if the system uses that style.
- Body: the system's body face, at a size that reads at phone scale; never more than four lines on a slide.
- Contrast: Left and Right as two columns or two stacked blocks with the same type role.
- Punch line: one standalone line at the foot of the slide, a step above body size.
- Sign-off: the wordmark or monogram, on the final slide only.

Progress: a small "n/6" marker in the same position on every slide. Nothing else repeats across slides apart from the system's standard framing.

Copy, word for word, in stacking order, one slide per block:

Slide 1/6 · Hook
Headline: A full diary is not a *margin*.
Body: Every owner-run firm knows how busy it is. Few can say what their most common job makes.

Slide 2/6 · Frame
Headline: Every quote is a guess with a *number* on it
Contrast:
  Left: A costed quote starts from what the job takes: hours, materials, travel, the van.
  Right: A guessed quote starts from last year's price and what the customer might accept.
Punch line: One protects the margin. The other hopes for it.

Slide 3/6 · Stakes
Headline: The job you do most is the one *never costed*.
Body: It feels familiar, so nobody checks it. Familiar work is where a small loss repeats every week, unnoticed, for a year.

Slide 4/6 · Mechanism
Label: THREE JOB TYPES. ONE MORNING.
Body: Take your three most common jobs. Write down the hours, materials and travel each one carries. Set each total beside the price you charge for it.
Punch line: That is the whole exercise. It costs nothing but a morning.

Slide 5/6 · Payoff
Body: The price list starts to mean something. Quotes go out from the list, not from memory. And a quote a customer questions has a costing behind it.

Slide 6/6 · Close
Headline: Cost the job, *then* quote it.
Body: A price you cannot cost is a price you cannot defend. The costing comes before the rise, every time.
Sign-off: NORTHGATE

Export the set as 6 separate 1080 x 1350 PNG files named slide-01 to slide-06, plus one PDF of the set.
```
