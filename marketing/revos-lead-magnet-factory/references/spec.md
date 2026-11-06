# The spec file

`magnet.json` is the single source. `magnet.py build` makes every file from it, so the page, the printable copy and the launch pack cannot disagree.

Start it with `python3 scripts/magnet.py init --format scorecard|checklist|guide --out <scratch>/magnet.json`: every field is in place with `FILL: what goes here` as its value, and `validate` refuses any `FILL:` left, so a half-written spec never builds. A complete, valid scorecard spec to compare against is in `assets/spec-template.json` (the Denver studio from `references/examples.md`).

Contents: 1 Top level. 2 The scorecard. 3 Checklist and guide. 4 The launch pack. 5 When code cannot run.

## 1. Top level

| Field | What goes in it |
|---|---|
| `format` | `scorecard`, `checklist` or `guide` |
| `date` | Build date, YYYY-MM-DD (file names use it; documents show it in the founder's date order) |
| `hosting` | Where the page will live, in the founder's words ("her own website", "cannot host a page") |
| `founder` | `name`, `first_name`, `business`, `country` (two letters), `spelling` (british, american, australian, canadian, indian), `decimal` (dot or comma), `currency` (three letters), `signoff`, `never_words` (list), `we` (true when the founders write as "we") |
| `offer` | `name`, `price_as_typed` (exactly as they wrote it: "$4.8K"), optional `price_value`, `link` (booking or reply route), `route` (book, reply, buy) |
| `sources` | Files holding what the founder pasted, exactly as given, relative to the spec |
| `founder_replies` | Their answers to your questions, as they wrote them |
| `topic` | `slug`, `problem`, `source_line` (copied exactly), `source` (the kind of source, such as "a client email" or "your call notes"; never a client's name), `inferred` (true when not quoted), `runners_up` (two: `topic`, `why_not`), `format_reason`, `not_given_away`, `drafted` (what you drafted for them to read as the expert), `previous` (rebuild only: what changed) |
| `facts` | Every figure or general claim used anywhere: `claim` (as written in the copy) and `source` (where the founder got it). "Heard it somewhere" is not a source |
| `look` | Optional hex colours: `text`, `background`, `accent`, `accent_text`, `muted`; `font_stack` for the page; `docx_font` for Word. Leave empty for plain black on white |
| `previous_subjects`, `previous_spec` | Return runs: earlier subject lines (from memory) or the earlier spec file, so nothing repeats |

## 2. The scorecard (`magnet`)

| Field | Rule |
|---|---|
| `title` | The headline on the page: one specific question or outcome |
| `promise` | One line: what the reader will know when they finish |
| `minutes` | An honest time, three or under (checked against an estimate) |
| `who_for`, `who_not_for` | One line each; the second counts as a fit signal |
| `questions` | Exactly five. Each: `id`, optional `label` (a short heading, such as the founder's slide title), `text`, `source`, `source_quote` (exact words from the paste, where it came from there), `options` (three or four, each `label` and whole-number `points`, all different), `strength` (for the top answer), `strength_mid` (for an upper answer that is not the top one: "You know a typical order", where `strength` says "You know each order"), `fix_low`, `fix_high` (one sentence each, all different) |
| `fit_questions` | Up to two, unscored. Each: `id`, `text`, `source`, `options` (two to four, each `label` and `fit`: true or false) |
| `strength_fallback` | The honest What is working line when every answer is low |
| `tiers` | Three to five, lowest first: `name`, `min`, `max`, `description` (40 to 70 words). Bands cover every total with no gap or overlap |
| `door` | `question` (the next question the scorecard cannot answer) and `sentence` (where that question gets answered) |
| `cta` | `label`, `link` (a full `https://` or `mailto:` address; `http://` is refused) and `line`; with no link, a `line` asking them to reply to the email that brought them. Always `line_top_tier`: what a reader in the top tier sees instead of `line`. They have few gaps, so say honestly whether a call is worth their time yet; the link shows as a quiet text link for them, not a button |
| `not_a_fit` | Shown in place of the call to action when a fit answer says the offer is not for them |
| `footer` | The founder's name and business |

Example question:

```json
{"id": "q2", "label": "Pushing back on your own boss", "source": "slide 2",
 "source_quote": "Pushing back on your own boss",
 "text": "When your boss asks for something you think is a mistake, what do you usually do?",
 "options": [{"label": "Go along with it and say nothing", "points": 0},
             {"label": "Complain to peers rather than to my boss", "points": 1},
             {"label": "Raise it, then drop it at the first push back", "points": 2},
             {"label": "Say what I see and what I would do instead", "points": 3}],
 "strength": "You tell your boss when you think a call is wrong, and you say what you would do instead.",
 "strength_mid": "You raise it with your boss when you think a call is wrong, even if you let it drop.",
 "fix_low": "Before the next request you disagree with, write the risk and your alternative in two lines.",
 "fix_high": "Ask your boss how they prefer to hear disagreement, so the next one gets a hearing sooner."}
```

## 3. Checklist (`checklist`) and guide (`guide`)

Checklist: `title` ("12-point ... checklist"; the number must match), `who_for`, `minutes`, `sections` (each `heading` and `items`; each item `text`, `detail` of one or two sentences, `source`, optional `source_quote`, and `need` when it cannot be sourced: it is then held off the page and listed in the pack; write it to the founder, "confirm ...", with no figure in it), `not_covered` (the door), `next_step`.

Guide: `title`, `who_for`, `idea`, `steps` (three to five, each `text` and `source`), `example_label` (says it is an example), `example`, `not_covered`, `next_step`.

## 4. The launch pack (`launch`)

| Field | Rule |
|---|---|
| `optin` | `headline`, `subhead`, `bullets` (exactly three), `fields` (default First name, Email), `expectation` (must mention unsubscribing), `button` (names what they get), `signoff_line`; `form_action` (https address) or `embed` (the code their email tool gave them) only when the founder supplied one: then the opt-in page is built |
| `thankyou` | `headline`, `body`, `link_label`, `next_step` |
| `rules` | `starts`, `stops` (list), `remove_before` (list), `timing_days` (default 0, 1, 3, 5, 7), `no_ps_email_one` (true only if the founder asked) |
| `emails` | Five, each `day`, `job`, `subjects` (two), `preview`, `body` (paragraphs separated by a blank line), `signoff`, `ps`. Rules in `references/email-arc.md` |
| `result_map` | Scorecard: one entry per tier, in order, `when` set to the tier name. Checklist or guide: two or more entries keyed by what a reader's reply says. Each: `dealing_with`, `ask`, `next_step` |
| `golive` | Optional extra go-live items |

Merge tags allowed: `{{first_name}}`, `{{magnet_link}}`, `{{booking_link}}`, `{{reply_address}}`, `{{unsubscribe_link}}`.

## 5. When code cannot run

Say so in one line. Give the founder the same sections as copy blocks: the questions with points, the tier table, the result lines per question, the opt-in and thank-you blocks, the five emails and the result map. Add up the lowest and highest possible totals yourself and make the bands cover them with no gap; claim no simulation, no audit and no file. Every rule above still applies.
