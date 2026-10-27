# Styles

Five styles the renderer knows. Draw three by default so the founder compares real ideas, not three frames for one idea. Each differs in composition, type treatment, hierarchy and colour logic. Write one line of reasoning per style about this video, and recommend one.

| Style | Composition | Type and highlight | Colour logic | Best for |
|---|---|---|---|---|
| `panel` Bold panel | Words on a flat panel; the photo on a slanted panel beside it, edged with a stripe of the bright brand colour (or the words' colour) | Black weight, tight leading, little linking words set smaller; the key word set a third larger, a number 60 per cent larger | Dark: the dark brand colour behind, the light brand colour (or white) for words, the bright colour for the key word | A method, a claim, a before and after |
| `poster` Poster | Light background, words left; the founder in a large circle with a ring in the words' colour and, if there is a bright brand colour, an offset disc behind | Same hierarchy; the key word reversed out of a solid box | Light: the quiet light brand colour behind (cream, sand), else a bright brand colour the dark one reads on, else white; words in the dark brand colour | An explainer or a series; stands apart in a dark feed |
| `cinema` Cinematic | The photo fills the frame (or the face side, fading into the dark colour if the photo is tall); words sit low in a shaded corner | Large, left-aligned at the bottom; key word or figure set larger, in the bright colour when there is one | Dark shade in the dark brand colour; words light | A story, behind the scenes, a personal turn |
| `cutout` Cut-out | The founder, background already removed, stands in front of the words on flat colour, edged in the words' colour | Key word larger | Dark | A reaction, a warning, a surprising result |
| `type` Words only | Words centred and large; one number in a chip below | Strong hierarchy: key word larger, linking words smaller | Dark | A list or a number-led video; founders who do not show their face |

## How to choose the recommendation

1. Start from the tone: a method or claim to `panel`; an explainer or a series to `poster`; a story or opinion to `cinema`; a warning or result to `cutout` if there is a cut-out, otherwise `panel`; a list or number to `type`.
2. Then the photo decides. A busy background behind the face counts against `cinema`. A small face in a wide photo favours `cinema` (it crops tightest). A product photo usually suits `panel` or `poster`.
3. Arabic or Hebrew words: put the face on the left so the words, set flush right, are read first.
4. Then the feed decides. Most YouTube home feeds are dark at night and light by day; a channel whose competitors all use dark thumbnails stands out with `poster`.
5. Then memory decides. If a winning style is saved, draw it first and make the recommendation either the saved look or the challenger with a stated reason.

## Writing the reason line

One sentence, about this video, in plain words. Name the thing in the video or the photo that makes the style fit.

- Weak: "Clean and professional."
- Strong: "Your before and after is the whole video, so the bold panel lets the 5 dominate and puts you beside it as the person who did it."

## What every style does on its own

- **Even line spacing.** Lines are spaced by their ink, so the gap between lines is the same in every script and at every size.
- **Stacked lines.** With two or three lines, a line narrower than the column is set larger until it fills the width, so the words read as one block. A line without the highlight never grows past three quarters of the highlight's size.
- **Words never touch the face.** The words' column is pulled back from the face box before the words are fitted, and the check flags any letter, dot or mark within about 15 px of it.
- **Depth on flat dark backgrounds.** A quiet black shade at the edges, so a flat panel does not read as a fill. Nothing is added to light backgrounds.

## Adjustments the founder may ask for

| They say | Set | Range |
|---|---|---|
| "Make the number bigger" | first `text_width` (more room for the words), then `highlight_scale` (in `styles.<name>` for one style) | 0.40 to 0.70; 0.8 to 2.2 |
| "Make the chip bigger" | `focal_scale` | 0.6 to 2.6 |
| "Move my photo right / down" | `photo_offset` [x, y] as fractions of the frame (0.05 is 64 px at 1280) | about -0.2 to 0.2 |
| "Make me smaller / bigger" | `face_scale` | 0.6 to 1.4 |
| "Move the words up / down" | `text_position` | top, center, bottom |
| "Bolder" | a heavier installed weight first (`S fonts`), else `weight_boost` | 0 to 1 |
| "Brighter" | a larger figure; white for the other words so the bright colour stands alone; or the figure reversed out of a box in the bright colour | never a mixed shade or tint of a founder's colour; `check` refuses one |

When the photo moves or shrinks past its own edge, the strip it no longer covers is filled with a soft, blurred extension of the same photo. Say so in one line. Nothing is generated or retouched.

## What every style keeps

- The words on the side the eyes face, or away from the face if they look at camera.
- Nothing in the bottom right, where the video length badge sits.
- One key word or one number, not both.
- Only the founder's colours, plus black and white.
- No drop shadows. An outline only where the words sit on a busy part of the photo.
