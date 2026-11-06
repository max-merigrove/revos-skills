# The how-it's-made look

Broken down from two reels by speedy_devv (screen recording, 3 Nov 2026): "Why do new
tyres have little hairs?" (55 s, 150 words) and "What makes a hydrogen bomb stronger?"
(87 s, 240 words). Both share one recipe. Every number below was measured from the
recording; use them as the defaults and change them on purpose.

## 1. What the film is

A vertical (1080 x 1920) narrated explainer in which a dark, product-lit 3D world
shows the thing being made, one step per sentence. The voice is the clock: a new
picture lands on the first word of each sentence, and every label, number and
highlight lands on the word that names it.

## 2. The script

| Part | Length | What it does | From the tyre reel |
| --- | --- | --- | --- |
| Hook | 1 line, under 4 s | The question the viewer already has, or a myth said as fact | "Why do new tires have little hairs all over them?" |
| Snapback | 1 line | Kills the obvious answer, gives the real one in five words | "They're not there for grip, they're rubber that escaped." |
| Process | 5 to 9 lines | The making, in order, one step per line, each with one concrete number | "cooked at 170 degrees Celsius", "10 times the pressure in your tire", "about a millimetre wide" |
| Analogy | 1 line, inside the process | A kitchen object for the hard step | "like toothpaste when you squeeze the tube" |
| Payoff | 1 line | Re-reads the hook with what we now know | "they're the mark of every air bubble that never stayed in your tire" |
| CTA | 1 line | Follow, and send it to the person who believes the myth | "send this to someone who swears they're there for grip" |

- 2.7 to 2.9 spoken words a second; 150 to 240 words for 55 to 90 s.
- Short sentences, second person ("your tire"), no jargon without a picture under it.
- Numbers are said the way people say them ("about a millimetre", "less than 1 kilo").
- The longer reel adds a turn ("But there's a limit") and a human ("Edward Teller,
  who worked with Oppenheimer"); the short one is all process.

## 3. Picture

- **World**: near-black studio (#0b0a09 to #1a1714), warm key from top left, cool faint
  rim, a soft floor that falls off into black, heavy vignette. No horizon, no walls.
- **Materials**: physically lit, slightly rough (roughness 0.35 to 0.6), real colour
  only where the subject has it (orange rubber spew, red/white atoms, yellow paint).
  Everything else is graphite, steel, wood or rubber in low saturation.
- **Lens**: long (28 to 40 degree vertical FOV), shallow depth, objects fill 50 to 80 %
  of the frame width. Macro close-ups for the "magnified" steps.
- **Camera**: always moving, slowly (a 4 % to 10 % push, a 5 to 15 degree orbit, or a
  rise over the shot). One hero object per shot. Dives into the part that matters
  rather than cutting to it when it can.
- **Cuts**: one shot per sentence, 2.5 to 6 s (median about 4 s). Hard cuts on the
  sentence, a 0.4 s dissolve when the step continues the same object. Inside a shot
  the object transforms (mould closes, rubber squeezes, atom splits) so nothing holds still.
- **Cutaways**: the object sliced open (mould cross-section, bomb casing as a glass
  capsule), exploded views, a magnified slice of surface.
- **Heat and energy**: shown as colour (orange glow on the hot part), sparks, a bright
  bloom at the moment of release. Bloom only on the brightest points.
- **Analogy plates**: a single photoreal object (toothpaste tube, finger in clay)
  floating in the same dark studio, 2 to 3 s.
- **History plates**: a black-and-white photo as a print on a wooden desk, its name
  above it; old footage in sepia with a big year over it ("1952").

## 4. Graphics over the picture

All white on the dark world, Inter (SF Pro in the original).

| Device | Spec (at 1080 wide) | When |
| --- | --- | --- |
| Caption | Top centre, baseline about y 300; 60 px semibold; 2 to 5 words a group; the spoken word white, earlier words in the group at 45 % white; at most 2 lines | Every word of the voice |
| Keyword box | The key word of a line wrapped in a 2 px blue (#4C8DF6) rectangle with round handles at top-left and bottom-right, like selected text in an editor | 1 word a sentence, the noun that carries the line |
| Emoji | One emoji right before the keyword (🔥 170, 🪥 toothpaste, ⚡ energy, ☀️ Sun, 🏝️ island) | Under 1 in 4 lines |
| Callout | Uppercase 30 px bold, 0.2 em tracking; a 2 px hairline leader from the label to a 7 px dot on the part | When the voice names a part; it follows the part as the camera moves |
| Stat | Number 72 px bold + unit 34 px regular, a slanted leader to the thing ("64 kilos", "12,719 tons of TNT" counting up, odometer "09 MI") | Every number said aloud |
| Presenter | A 3D cartoon of the creator, bottom-right, chest up, a new gesture per line (points at the label, shrugs, palm out, OK sign) | Optional brand device |

Safe area: nothing readable above y 168 or below y 1330 (Instagram UI); the caption
and callouts live between.

## 5. Sound

The voice, a quiet dark ambient bed, and small sounds on the visible actions (a
press, a hiss, a spark, a pop for each callout). Never louder than the voice.

## 6. Prompting it

Paste section 3 and 4 as the fixed look, then one block per shot:

```
SHOT 4  (line: "It goes into a steel mold with a tread carved in reverse...")
  length   on the voice, ~4.5 s, hard cut in
  world    green tyre (smooth, no tread) lowered into an open two-part steel mould,
           tread carved in reverse on the inner wall
  motion   mould halves close over 2 s; heat glow rises on the steel from 2.5 s
  camera   3/4 from above, 34 deg FOV, push 6 % and orbit 10 deg over the shot
  labels   "170 °C" stat on "170", leader to the mould wall
  caption  keyword "170" with 🔥
```

The skill `revos-how-its-made` writes these blocks for any topic (`PROMPT.md`) and builds
them with the kit in this repo. For Remotion, the same blocks map onto
`@remotion/three` with `useCurrentFrame()` as the clock.
