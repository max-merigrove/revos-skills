# Worked examples

Three complete runs, taken from the skill's own test runs (v1.1.0): a US founder, a UK founder and an Indian founder writing in Hindi. Every business is illustrative, not a client. The portraits are synthetic stand-ins.

## Example 1: a US bookkeeper with brand colors and a logo

**Input, as the founder gave it.** "I run a small bookkeeping firm in Hoboken, NJ and I've just started a YouTube channel. Next video is 'How I close the books in one day'. In it I walk through my one-day month-end checklist, that's at about 3:40. Photo of me attached, my colors are navy #0E2A47 and gold #F2B33D, logo attached too. Can you do me a thumbnail, and a square one for LinkedIn?"

**Intake.** Their message answered everything, so the reply opened by confirming it in one line and asked nothing. The founder writes American English, so every message back did too ("your colors"); nothing asked them which.

**Promise and payoff.** Promise: a way for a small firm to close month-end in one working day. Payoff: the one-day checklist on screen at 3:40.

**Word options** (all pass `check_copy.py --hooks`): Month-end in ONE day (recommended); Five days to one; The one-day checklist; Stop closing on day five.

**Colours as the script sorted them.** Dark: navy. Light: none given, so white carries the words. Bright: gold, which colours ONE, edges the slanted panel and, because there is no quiet light colour, becomes the poster's background with navy words.

**Spec, abbreviated.**

```json
{"slug": "month-end-in-one-day", "title": "How I close the books in one day",
 "hook": "Month-end in ONE day", "highlight": "ONE",
 "photo": "founder-portrait.jpg", "face_box": [0.33, 0.13, 0.67, 0.59], "subject_side": "right",
 "brand": {"mode": "brand", "colours": ["#0E2A47", "#F2B33D"], "logo": "harbour-ledger-logo.png"},
 "directions": ["panel", "poster", "cinema"], "sizes": ["youtube", "square"],
 "promise": "A way for a small firm to close month-end in one working day",
 "payoff": "The one-day month-end checklist, walked through step by step on screen", "payoff_time": "3:40"}
```

**Render output, bold panel at 1280x720.**

```
Hook set at 100 px in 2 line(s): Month-end / in ONE day
PASS  Hook size at 168 px wide: capitals 9.6 px tall (pass at 8)
PASS  Contrast behind the words: 14.6:1 typical, 14.6:1 at the busiest tenth
PASS  Squint test: words still separate from their ground at 9.1:1 when blurred at 168 px
PASS  Highlight stands out: highlighted word 1.9:1 against the other words, 7.8:1 against the background
PASS  Clear of the duration badge: nothing essential sits there
PASS  Words clear of the face: 0 per cent of the face is under the words
PASS  Face size: face is 58 per cent of the frame height, 100 per cent of it in frame
PASS  Photo sharpness: photograph enlarged 0.45 times
```

"in" is set smaller and ONE a third larger, so the eye goes to ONE first. On the gold poster the gold logo would vanish; the script left it off that style and said so.

**What was delivered.** Three styles at both sizes, the comparison sheet and notes. The recommendation was the bold panel. The founder answered "Close. Lose the logo", it was redrawn without it, and "no logo on thumbnails" was proposed as a learning to check next time.

## Example 2: a UK design agency that gave a colour by name

**Input.** "brand colours are a dark green #1F3D2B and cream. no idea what font", with the title, but no payoff and no photo yet.

**Intake.** Confirmed the title and green in one line; asked three things: what the video delivers and when, the photo, and a screenshot for the cream. With no screenshot, `S swatches cream` offered A #F3EBD8, B #EFE4C8, C #F7F1E3; the founder picked A. Until then the spec carried `"named": ["cream"]` and `check` refused to draw.

**Word options.** 10 hours to 5 (recommended), Admin, halved, The invoicing fix, No hire, half the admin.

**Line breaks.** The setter keeps a number with its unit: "10 hours / to 5", never "10 / hours / to 5". In the panel and words-only styles "to" is set smaller and the 5 is set 60 per cent larger.

**Render output, poster at 1280x720.**

```
Hook set at 126 px in 2 line(s): 10 hours / to 5
PASS  Highlight stands out: highlight box 10.0:1 against the background, its word 10.0:1 inside it
PASS  Hook size at 168 px wide: capitals 12.1 px tall (pass at 8)
```

The cream carries the words on green in the panel and is the whole background of the poster; the 5 is reversed out of a green box. In v1.0.0 the same brief put cream on one character next to white words, at 1.19:1, and every check still passed.

**Why both pass the rubric.** Every check passes at 168 px; three styles that differ in layout, type and colour logic with one on a light background; only the founder's colours plus black and white; promise and payoff written with a time; a memory file proposed.

## Example 3: an Indian founder who wants the words in Hindi

**Input.** "Title: 'No-show students se ₹5.2 lakh kaise bachaye'. Channel is in Hindi so the words on the thumbnail in Hindi please. At 3:05 I show the WhatsApp reminder system and the ₹5.2 lakh we saved in a year. Video live on 14/11/2026. Brand colours maroon #8C1C13 and cream #F6E7C1, our font is Liberation Sans. Photo attached."

**Intake.** Nothing asked. The words are in Hindi because the founder asked; the rupee and "lakh" stay exactly as written; the date is not restated in another style.

**The font.** `check` read every character against Liberation Sans's character map: no Devanagari and no ₹. It set the words in Poppins (open licence, installed, has both) and warned; the founder was told in one line and asked for a Hindi version of their own font if they have one. Had no installed font covered Devanagari, `check` would have refused rather than print empty boxes.

**Word options.** ₹5 लाख बचाए (recommended), WhatsApp से ₹5 लाख, नो-शो का इलाज. "₹5 लाख" passes the number check because it rounds the ₹5.2 lakh in the payoff down; "₹6 लाख" would be refused.

**Render output, bold panel at 1280x720.**

```
Typeface: Poppins (OFL, installed here); your font Liberation Sans has no glyphs for some of these letters
Script: Devanagari, shaped with raqm
Hook set at 158 px in 2 line(s): ₹5 लाख / बचाए
PASS  Hook size at 168 px wide: letters (क height) 15.4 px tall (pass at 8)
PASS  Contrast behind the words: 7.5:1 typical, 7.5:1 at the busiest tenth
```

The leading opens up for the vowel signs above and below the line, and "₹5 लाख" stays on one line. Plain Claude's usual script draws the same words as boxes (`assets/before-after.md`).
