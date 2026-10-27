# Changelog

## 1.3.0 (2026-10-21)
From the end-to-end round against plain Claude (India scenario graded 6/10; US won only narrowly).
- First reply delivers: renders straight away when the title and payoff are given, opening with one line confirming title, payoff, colours and photo; with less, gives provisional word options before any question. Side questions are answered directly. Questions never come before value.
- Three options now carry three word options: `styles.<name>.hook` (and highlight, focal, size and photo adjustments) per style, checked per style; `check` warns when every style carries the same words. The comparison sheet and notes name the words on each.
- A number and its unit highlight as one phrase ("₹5.2 lakh", "$10,400"), sized, coloured or boxed together and never split. Cinema now sizes its highlight too (with no accent colour it previously showed no highlight at all).
- Stacked type: each line of a two or three line hook is set to fill the column, so the block no longer floats small in empty space; lines without the highlight stay below three quarters of its size.
- Founder requests are carried out, not refused: `text_width` (0.40 to 0.70, the words' side in panel, poster and cinema), `highlight_scale` (0.8 to 2.2), `focal_scale` widened to 2.6, `face_scale` (0.6 to 1.4), `photo_offset`, `text_position` and `weight_boost`. A photo moved past its edge is extended with a soft, blurred copy of itself instead of being clamped.
- Words never touch the face: the words' column is pulled back from the face box before fitting, and the check now measures the ink of every letter, dot and mark (a Devanagari anusvara touching the cheek passed before).
- Lines are spaced by their ink, evenly in every script (Devanagari lines no longer float apart). `weight_boost` thickens the letters when "bolder" is asked and no heavier weight is installed.
- A quiet black edge shade on flat dark backgrounds for depth; the poster circle is slightly smaller to give the words room.
- Clean folder: each round keeps one slug and `render` moves the previous round to `earlier/round-N/` (no more v2 to v8 files beside the final).
- Notes and sheet follow the founder's spelling (`"spelling": "us"`); memory dates are filled, never left as YYYY-MM-DD; founder dates are quoted exactly as written.
- `check` refuses a `ground` or `accent` that is not the founder's colour, black or white (a mixed shade slipped through to answer "brighter"); warns when a hook repeats a title word or two styles carry nearly the same words.
- Closing line shortened to one line: the last line of the first delivery and of the final message only. Chat replies follow the language and script the founder writes in. Four or five word options in all: three drawn, one or two listed. Description triggers before files are shared and on "what should my thumbnail say".
- Founder-facing replies never show spec field names, step names or memory statuses.
- Pruned superseded sample images from evals (18 MB to under 3 MB).

## 1.1.1 (2026-10-21)
- Added "Where files go": deliverables always land in /mnt/user-data/outputs/ (claude.ai, Cowork) or the working folder (Claude Code), never a scratchpad. Found by end-to-end testing with a real headless Claude session.

## 1.1.0 (2026-10-20)
- Global by default: the words follow the founder's language, spelling and currency as they write them; no spelling, currency or country is assumed (the "British English" default and the UK-only examples are gone). Example founders now include the US and India as well as the UK.
- Any script: every character is checked against the font's own character map before drawing. A founder font that lacks a letter is swapped for an open-licence face that has it (and the founder is told); with no covering font installed, `check` refuses instead of drawing empty boxes. Emoji are refused.
- Shaped scripts (Arabic, Hebrew, the Indic scripts, Thai and others) are drawn with Pillow's raqm layout, and `check` refuses them where raqm is missing. Right-to-left words are set right to left and flush right. In Chinese, Japanese and Thai a space marks a line break and is not drawn. Leading and the size check follow the script. Optional `lang` picks Chinese, Japanese or Korean letterforms and Turkish casing.
- Currency: number recognition covers the world's common currency signs and short forms ($10k, 2.5m, ₹5 lakh, 2 crore, 10万). A short form may round a figure down, never up, and is checked against the payoff.
- Word counts work in every language (about two characters a word in Chinese and Japanese, three in Thai and similar), in `check`, `check_copy.py --hooks` and the memory history.
- Rules added: no tax, legal or accounting view; one line on permission when someone else appears. Banned patterns added: stating what a law requires, computing tax, assuming a country, empty boxes, unjoined letters, rounding a number up.

## 1.0.1 (2026-10-20)
- Three genuinely different styles replace one layout with three photo frames: `panel` (dark, slanted photo panel with a bright edge), `poster` (light background in the founder's light colour, dark words, photo in a circle) and `cinema` (photo fills the frame, words low in the shade). Old names still work.
- Typography: tight leading, linking words set smaller, the key word set a third larger (a number 60 per cent larger), boxed highlights that no longer shrink the whole hook.
- Colour roles: a quiet light brand colour carries the words; a bright one is the highlight; a highlight that would not stand out becomes a box. New "Highlight stands out" check. No invented greys.
- Colours given by name: `colours` reads them from a screenshot, `swatches` offers candidates; `check` refuses to draw until they are settled.
- Outlines only on busy photo areas; no drop shadows. A tall photo in `cinema` fills the face side and fades instead of blowing the face up.
- Line breaks never split a number from its unit.
- Intake confirms what the founder already said and asks only for what is missing; plainer words in founder-facing messages.
- `out_dir` defaults to the claude.ai outputs folder when it exists; titles on the comparison sheet cut at a word with an ellipsis.
- `check_copy.py --hooks` refuses "more" and exclamation marks; `|` no longer counts as a word there or in memory.
- `test` estimates type size from a block of words read off the grid (`--text-box`, `--lines`) instead of a capital's height; `inspect` draws lines every 0.05.
- JPEG twins carry the credit line in their comment.

## 1.0.0 (2026-10-20)
- First release as a standalone skill.
- Renders finished PNGs with Pillow in five art directions (split, full bleed, framed card, cut-out, type only) at five sizes, with an SVG fallback when Pillow is missing.
- Readability test at feed sizes: hook size, contrast against the real pixels, squint test, platform keep-clear zones, face size and overlap, photo sharpness; comparison sheet in dark and light feeds.
- Hook options written on the spot from the title and the payoff, checked by script; promise to payoff check, including numbers.
- Test mode for an existing thumbnail.
- Memory with a winning style and click-through history.
