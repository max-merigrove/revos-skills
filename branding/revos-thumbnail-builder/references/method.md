# Method

How the Thumbnail Builder decides what to draw and how it knows the result works. Contents:

1. Why the thumbnail matters and what it is for
2. The composition rules
3. Reading the face box
4. The crop arithmetic
5. The readability test
6. Fonts, colours and logos
7. The promise to payoff check (including currency and short forms)
8. Holding a look across a series
9. Where it goes wrong
10. Languages and scripts

## 1. Why the thumbnail matters and what it is for

The thumbnail and the title are the whole advert for the video. Nobody hears a word until they have clicked, and most decide in the time it takes to scroll past. A thumbnail has one job: make the video's one promise readable at a glance, at the size it is really seen, by the person the video is for.

Writing the thumbnail first is also a cheap test of the video. If its promise cannot be said in three to five words, the video does not yet have one idea.

## 2. The composition rules

These rules are carried from Charlie Hills' youtube-thumbnail skill (MIT, see LICENSE.md) and turned into checks the script runs. Every one is about the small size, not the full size.

| Rule | Why | Checked by |
|---|---|---|
| Three to five words. Three reads fastest; six is the hard limit | At 168 px wide a sixth word drops the type below readable | `check` (word count; in Chinese and Japanese about two characters count as a word, in Thai, Lao, Khmer and Burmese about three, a house working rule), `render` (cap height) |
| A phrase, not a sentence. No full stop | A sentence asks to be read; a phrase is taken in | `check` |
| One focal point besides the face: one highlighted word or one number with its unit | Two focal points read as none | `check` (warns when both are set) |
| Two dominant colours plus the photo | A third colour turns to noise when small | the colour roles in `render` |
| The face large and clear | A face is the fastest thing a person recognises in a feed | `render` (face size, words clear of the face) |
| High contrast between words and what is behind them | Contrast is what survives shrinking and blurring | `render` (contrast, squint test) |
| Nothing essential in the bottom right | The platform draws the duration badge there | `render` (keep-clear check) |
| The thumbnail and the title do not repeat each other | They are read together; repetition wastes the second line | `check` |

The face size rule in the source reads "the face fills 30 to 50 per cent of the frame". This skill measures it as the face's height as a share of the frame height, aiming for 45 to 60 per cent on a 16:9 thumbnail and passing anything from 35 to 75. That is a house working rule chosen because it can be measured from a face box; it is not taken from a published study.

## 3. Reading the face box

Nothing is detected automatically and no face is ever generated. `S inspect <photo>` writes a copy of the photo with lines every tenth of the width and height. Open it, and read the box that runs from the top of the hair to the chin, and from ear to ear, as `[left, top, right, bottom]`. Round to two decimals. For a photo of a product or the work, the box is the object itself.

Also note:

- Which way the eyes look. Words sit where the eyes point, or on the side away from the face if they look at camera.
- Whether the photo is soft, dark or busy behind the head. A busy background favours `panel` or `poster` over `cinema`.
- Whether it is a transparent PNG (inspect says so). Only then is `cutout` offered.

If the founder can see the result and says the crop is off, move the box by a tenth in the direction they name and render again.

## 4. The crop arithmetic

For each direction the script knows where the face should sit and how tall it should be. It scales the photo so the face box reaches that height, never smaller than the scale that fills the photo's region (so no gap shows), then places the face centre where the direction wants it and clamps so no edge of the photo shows through. It reports:

- the face's height as a share of the frame, and how much of the face is in frame
- how much the photo was enlarged; over 1.6 times it warns that the result may look soft
- whether any of the words sit over the face

A photo under 600 px on its short side is warned at `check`. Ask for a larger original if one exists; phone photos straight from the camera roll are usually large enough.

## 5. The readability test

`S render` measures every thumbnail the way a viewer meets it. Thresholds:

| Check | Pass | Warn | Fail | What it measures |
|---|---|---|---|---|
| Hook size | capitals 8 px or taller at the smallest test width | 6 to 8 px | under 6 px | the height of a capital letter once the thumbnail is shrunk to 168 px wide (16:9), 110 px (square) or 120 px (vertical) |
| Contrast behind the words | 4.5:1 typical and 3:1 at the busiest tenth | 3:1 typical | under 3:1 | the words' colour against the actual pixels behind them, measured before the words are drawn |
| Squint test | 3:1 | 2:1 | under 2:1 | shrink to the smallest size, blur, and measure how far apart the lightest and darkest parts of the hook box still are |
| Clear of platform furniture | nothing there | | anything there | the duration badge corner on 16:9; the caption strip and the action buttons on vertical |
| Inside the profile-grid crop | words inside the centre 3:4 | words outside | | vertical covers only |
| Face size | in range and 85 per cent in frame | outside | | section 2 |
| Words clear of the face | no overlap, nearest letter at least 1.2 per cent of the width away (15 px at 1280) | touching, or under 10 per cent covered | 10 per cent or more | the ink of every letter, dot and mark of the words and the chip against the visible face box |
| Highlight stands out | a coloured key word 1.5:1 against the other words and 3:1 against the background; a box 3:1 against the background with its word 4.5:1 inside | 1.2:1 and 2:1 | below | so a cream highlight next to white words can never pass unnoticed |
| Photo sharpness | enlarged 1.6 times or less | more | | section 4 |
| Focal element | 4.5:1 inside its chip | 3:1 | under 3:1 | the chip's words against the chip |

The test widths are approximate sizes people see: about 360 px for a phone feed, about 246 px for a desktop grid and about 168 px for the "up next" sidebar. They are working figures from looking at the platforms, not published specifications, and the platforms change them. The 4.5:1 and 3:1 contrast figures come from WCAG 2.2.

What the eye still does: open the comparison sheet and look at the smallest copy. The numbers say the words can be read; only looking says whether the face still reads as a person and whether the thing feels like the video.

`S test <image>` runs the parts of this that do not need to know where the words are (the light to dark spread at the smallest size, and how much detail sits in the badge corner) on a thumbnail the founder already has, and writes a small-size sheet with the badge drawn in. Add `--words` with the words typed out to count them, and `--text-box l t r b --lines n` (the block of words read off the `inspect` grid, which has lines every 0.05) to estimate the type size at 168 px.

## 6. Fonts, colours and logos

**Fonts.** In order: the founder's own font file; an installed family they name; the best open-licence bold font `S fonts` finds (Anton, Bebas Neue, Archivo Black, Montserrat, Inter, Poppins, Oswald and others under the SIL Open Font Licence or Apache 2.0, then the Noto families for other scripts and a few free fonts with a font exception); and only if none is installed, Pillow's own bundled sans, thickened with a stroke. Whichever comes first, it must have every character in the words (section 10). The skill bundles no font and downloads none. Rendering words into an image does not distribute the font, but the allow-list exists so the skill never reaches for a font whose licence limits its use, such as a platform's own interface typeface. If the founder names a commercial font they own, they supply the file and the licence is theirs.

**Colours.** Only the founder's colours are used, plus black and white. The script sorts them:

- **Dark**: the darkest colour, the background of `panel`, `cinema`, `cutout` and `type`.
- **Light**: a quiet light colour (cream, sand, pale grey). It carries the words on dark and is the background of `poster`. Without one, white does the job.
- **Bright**: a saturated colour (gold, orange, coral). It colours the key word, edges the slanted panel and sits behind the circle in `poster`. If there is no light colour, a bright colour that the dark one reads on becomes the `poster` background.

A coloured key word must stand 3:1 off the background and 1.5:1 off the other words; otherwise it becomes a solid box in the words' colour with the word reversed out, which always stands out. The founder can force `ground` and `accent`. Without brand colours the look is deliberately plain: black and white and the photo. No colour is invented.

**Colours given by name.** Founders usually say "cream" or "our orange", not a code. Never drop the colour and never guess a code. Ask once for a screenshot of the logo, website or brand sheet and run `S colours <image>` to read the main colours from it; confirm which is which. Without a screenshot, run `S swatches <name>` and let the founder pick one of two or three candidates; record the pick as their choice. Until it is settled, the spec carries `"named": [...]` and `check` will not draw.

**Type.** The heaviest weight installed, tight leading (0.9 of the size, 0.86 in upper case), and a hierarchy: in hooks of three words or more, little linking words (to, in, of, the, my) are set at about two thirds of the size so the words that carry the idea dominate. The key word is set a third larger, a number 60 per cent larger.

**Logo.** Optional and small: top corner on the words' side, about 8 per cent of the height. Never bottom right. Most founder channels do better without one; the face is the logo.

## 7. The promise to payoff check

Before anything is drawn, write two lines:

- **Promise:** what the title and thumbnail together tell the viewer they will get.
- **Payoff:** the moment in the video that delivers it, with a time.

Then test:

1. Is the payoff at least as big as the promise? If the thumbnail says "Month end in ONE day" and the video shows a checklist that gets it to two days, change the hook ("Month end in two days"), not the video's description.
2. Does every number on the thumbnail appear in the video? The script refuses a number that is not in the payoff or the promise. It reads short forms in any of the usual styles ($10k, 2.5m, 3bn, ₹5 lakh, 2 crore, 10万) as their full value, so "$10k" is backed by "$10,000" in the payoff. A short form may round a figure down, never up: "$10k" for $10,400 passes, "$10k" for $9,600 is refused.
3. Is the number in the founder's own currency and style, exactly as they wrote it? Never convert it, never add a currency sign they did not use, never swap their number style (5,00,000 stays as written).
4. Do absolutes (never, always, only, guaranteed, secret) survive the payoff? The script warns on each one.
5. Will the person who clicks feel they got what they were shown within the first minute? If the payoff is at 9:30 of a ten-minute video, say so to the founder; the opening should point to it.

A thumbnail the video does not pay off buys one click and costs the next ten, because viewers who feel tricked leave early and the platform learns from that.

## 8. Holding a look across a series

One look held across a run of videos is worth more than a better look each time, because the return is recognition. Once the founder picks a direction twice, it becomes the saved winning style and later runs draw it first, with one challenger. Change the look when click-through says to, not because a new video arrived.

Click-through rate depends on far more than the thumbnail: the topic, the title, where the impressions came from and how many there were. The memory keeps each reported rate beside the thumbnail it belongs to, and `memory_tool.py summary` shows the pattern with its sample size. Under five videos, a pattern is a hint to test, not a finding.

## 9. Where it goes wrong

- A sentence on the thumbnail. Cut to a phrase.
- The hook repeats the title. Use the thumbnail for the half of the idea the title does not say.
- A promise the video does not keep.
- Words over the face, or a face cut through the eyes by the frame edge.
- A logo or a word in the bottom right, under the duration badge.
- A new look every video.
- A soft, enlarged photo. Ask for the original.
- Three colours fighting. Two dominate; the photo brings the rest.
- An empty box where a letter should be. The script will not draw one (section 10).

## 10. Languages and scripts

The words go on the thumbnail in the founder's language and spelling, and the renderer has to draw every letter of it properly. Three things can go wrong, and the script checks each before drawing:

1. **A missing letter.** Fonts only contain the characters they were designed for. A Latin display face may lack ₹, and has no Devanagari, Arabic or Chinese at all; a missing character prints as an empty box. `check` and `render` read every character in the words against the font's own character map. If the founder's font lacks one, the words are set in the first open-licence bold face installed that has them all (for example Poppins for Devanagari, Noto Sans CJK for Chinese, Japanese and Korean), and `check` warns so you can tell the founder. If no installed font has them, `check` refuses and says which script is missing: ask the founder for a font file that covers it (the free Noto Sans family has one for almost every script), or write the words in a script that is covered. An emoji is always refused: no thumbnail typeface draws it.
2. **Letters that join, reorder or stack.** Arabic and Hebrew run right to left and Arabic letters join; Devanagari, Bengali, Tamil and the other Indic scripts reorder and stack vowel signs; Thai, Lao, Khmer and Burmese stack tone marks. These need a text shaping library (Pillow's raqm layout). The script uses it when present; without it `check` refuses, because the result would look broken to every reader of that language. Offer the words and a layout brief instead.
3. **Line breaks and spacing.** Chinese and Japanese, and Thai, have no spaces between words. Put a space in the hook where a line may break; between two such characters the space is not drawn. Right-to-left lines are set flush right with the words in right-to-left order; put the face on the left so the eye starts on the words.

Leading and the size check follow the script: scripts with marks above and below the letters get looser leading, and the "capital height" in the size check is the height of a typical letter of that script (for example क in Devanagari, 国 in Chinese). Upper case applies only to scripts that have it; with `"lang": "tr"` a Turkish i becomes İ. Chinese characters are drawn in Simplified letterforms unless `lang` says `zh-Hant` or `zh-HK`; Japanese and Korean are recognised from kana and hangul.

Without Pillow the SVG fallback leaves the drawing to the viewer's own fonts; `check` warns to open each file and look for boxes.