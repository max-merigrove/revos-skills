---
name: revos-brand-consistency-scan
description: "Finds where a founder's website, LinkedIn and proposals contradict each other, quoted side by side, and gives one core line to align them on. Use when someone says my website and LinkedIn say different things, is my messaging consistent, audit my brand, nobody understands what I do, my proposal doesn't sound like my website, check my about page against my profile, I want one line that describes my business everywhere, should I rebrand or just tidy up. Gives a score out of 100, contradictions ranked and line edits. Use this as soon as the founder asks, even before they have pasted anything; the skill asks for what it needs. Use this even if the founder does not name it. Do not use for reviewing one draft against brand guidelines, writing brand guidelines or a voice guide from scratch, analysing a competitor's messaging, or designing a logo or visual identity."
license: Proprietary, free to use in your own business. See LICENSE.md
metadata:
  version: 1.3.0
  author: Merigrove
  category: Branding
  updated: 2026-10-21
compatibility: "claude.ai with code execution on, Cowork, Claude Code. Python 3.8 or later, standard library only. No network."
---

# Brand Consistency Scan

The founder walks away with a one-page report showing where their own assets contradict each other, quoted word for word and side by side, a score out of 100 counted from those quotes, the one core line to align everything on, and a Word file of line-by-line edits for each asset. Client names and fees never appear in anything it writes or saves.

`S` below means `python3 scripts/`. Run every script from this skill's folder. The scripts run on Python 3.8 or later; if `python3` is older, say so in one line and do the steps by hand. `<work>` is a private scratch folder (on claude.ai `/tmp/brand-scan`; in Cowork and Claude Code a temporary folder, never the founder's outputs). `<out>` is `/mnt/user-data/outputs` when that folder exists, otherwise `brand-scan/` in the working folder.

## Where files go

Every file the founder is meant to open goes where they can open it: `/mnt/user-data/outputs/` when that folder exists (claude.ai and Cowork), otherwise the current working folder (Claude Code). Never leave a deliverable in a scratchpad, temp or session folder; those are for working files only. Wherever this file says `<out>`, `<output folder>` or "the output folder", it means this location. After saving, name each file in the chat.

## Start

Your next message does useful work. Do not describe the skill or ask permission. Run the memory check, then, if the founder has not pasted anything yet, open with:

"Paste the text of your website home and about pages, your LinkedIn headline and about section, and one recent proposal or sales deck. Screenshots and PDFs are fine. I'll take client names, fees and contact details out before I read anything, and weight the proposal highest because that's where buyers decide. Say skip and I'll score what you've given me."

Mirror the founder's English in everything you write to them.

If the first message already holds assets, skip the invitation and go to Intake.

**Value before questions.** When the founder has given two or more assets, the first reply is the finished scan, built on stated defaults: the score, the contradictions quoted, what else a careful buyer would notice, the line to align on and the first rewrite, with both files. Questions come after it, and only the ones whose answer would change what you delivered. Never send a message that is only questions.

## Memory check

Look for `revos-brand-consistency-scan-memory.md` in this order: `merigrove-memory/` in the working folder, files attached to this chat, the Project's files. On claude.ai, Project files reach you as text, not as files on disk: write the contents unchanged to `<work>/memory.md` and use that path. If found:

1. Run `S check_memory.py read <memory file> --json-out <work>/previous.json`.
2. Say in one line what you are using: "Using your saved line from <date>: '<core line>'. Last score <n>."
3. This is a return run. Ask only: "Paste the assets you've changed since <date>." (skip it if they already pasted). Apply every `active` learning at the step it names; never apply `watch` or `retired` rows silently.

If not found, this is a first run.

## Intake

First pull everything you can from what was pasted: each asset, its kind, the business name, the founder's name, who seems to sell, and where they are. Where they are comes from the paste: the currency of their prices, a phone country code, an address, a city they name. Never assume a country. Then run the whole scan on the defaults below and deliver it (Make, Check, Deliver). The questions go at the end of that same first reply, and only those whose answer would change the score, the line or an edit; say beside each what it would change ("if the proposal is a one-off, the score goes up and the team edit stays"). First run: at most five questions in all, across at most two founder turns, the first of them after the scan. Return run: at most one.

The only things that stop the scan before it is built: one asset and no memory (read that asset for the five questions, say what it answers and what it never says, then ask for a second); a figure that reads two ways when it sits in a fact or an edit (question 5; scan everything else meanwhile and show both readings); a STOP from a script.

Ask them in the text of the reply, after the scan, numbered with options, and say: "Answer like 1a, 2b, or say skip and I'll keep these defaults." (A multiple-choice tool is fine on a later turn, never in place of the scan.)

1. **Who sells.** "Who does the selling: (a) me (b) me and others (c) a team. If different people sell different offers, say who sells which." Ask only when the assets disagree on it or say "we". Default: read from the assets (below). It decides whether the core line may say "we"; an asset someone else sells goes in `sold_by` (`{"prop": "others"}`) and its edits never add the founder's "I" or name.
2. **Anything not current or aimed elsewhere.** "Is any of these out of date, a one-off, or aimed at a different buyer on purpose? (a) No, all current (b) Yes: tell me which." Default: (a). An out-of-date asset is left out (`excluded`), unless that would leave fewer than two assets: then keep it and say so in one line ("I've kept your Instagram in; it's older, but without it there's nothing to compare"). A deliberately different audience is left out of the questions the founder names, any of the five (`skip`, with their reason).
3. **Closest to the truth.** Ask only when the assets name different buyers. "If you had to pick, which of these is closest to the business you want today? (a) website (b) LinkedIn (c) proposal (d) none, let the scan decide." Default: (d).
4. **Where you are** (only when the paste does not show it). "Which country are you in? It sets whether the report prints on Letter or A4 and how dates read." Default: no country; the page prints on whatever paper their browser uses and dates read 2026-10-20.
5. **A number that reads two ways** (only when redact.py prints an ASK line). "You write 12.500: is that twelve thousand five hundred, or twelve and a half?" Set `locale.decimal` to `dot` or `comma`. Default: numbers are compared exactly as written.

Missing assets: score what is there if at least two remain. With one asset, score nothing (score_consistency.py stops on it), but still give the founder that asset's five answers and its gaps before asking for a second. State the defaults you used in one line inside the first reply: "I've treated everything as current and you as the seller, and set it for A4 with dates as 20 October 2026 since your prices are in S$; tell me if any of that is wrong."

Defaults are read from the assets, never invented. Who sells: the founder when they sign the proposal or the copy says "I"; "me and others" when the assets say "we" or name a team; never a team size, a role or a split of work the assets do not state. When the assets disagree on who sells, that disagreement is a finding, not a default.

Screenshots and PDFs: type the text out word for word, typos included, into `<work>/raw/<id>.txt`. Never tidy it; the quotes come from it. Keep a PDF's line breaks and split words as pasted; the scripts read through them. For a bio, leave out the profile name line above it: it is not part of the bio, and the bio's length is counted.

## Diagnose

In one line, name the job and the evidence; it sets how much you may change:

- **First scan:** no memory. Full scan, three core lines.
- **Re-scan after edits:** memory holds an agreed line. Score the changed assets against it; keep the line unless the founder asks to revisit it.
- **One asset to check against the rest:** memory plus one new asset (a new proposal template, a new about page). Re-scan with the saved quotes for the others.
- **Not enough to compare:** one asset, no memory. Give that asset's five answers and what it never says, then ask for a second.

## Make

Load only what the task needs:

| If the task is | Read |
|---|---|
| Reading assets for the five questions, grouping answers | `references/five-questions.md` |
| How the score, weights and ranking work | `references/scoring.md` |
| Writing the three core lines and the gate | `references/core-line-gate.md` |
| Who sells, "I" or "we", founder-fronted | `references/brand-ladder.md` |
| Removing client data, what is and is not saved | `references/privacy.md` |
| A finished scan to calibrate against | `references/examples.md` |
| Always, before writing any line for the founder | `references/banned-patterns.md` |

1. **Save and clean.** Write each asset to `<work>/raw/<id>.txt` exactly as pasted and list them in `<work>/assets.json` (`business`, `founder`, `founder_sells`, `assets`: id, kind, label, file). Run `S redact.py <work>/assets.json --out <work>/clean --delete-raw` with `--person "<full name>"` for every client, contact or testimonial person you can see (as written, in any script: "Nurul Aisyah binti Rahman", "陈伟明", "Nguyễn Thị Lan"), `--client "<name>"` for every client company or brand without a legal form after it ("Golden Lotus F&B Group"), `--address "<text>"` for any address or registration number in a shape the script may not know, and `--keep "<name>"` for anyone on the founder's side. Read back the counts in one line ("I took out 3 client names, 2 fees and an email"; the founder's own contact and payment details are named as theirs, never as client data). Act on every NOTE; an ASK line is intake question 5. A STOP here means a name matched ordinary words: fix the names and run again. From here on read only `<work>/clean/`.
2. **Measure the voice.** `S voice_drift.py <work>/clean/assets.json --out <work>/voice.json` (add `--previous <work>/previous.json` on a return run). Its ENGLISH line says which English the founder spells; write in it.
3. **Fill the table.** Copy `assets/extraction-template.json` to `<work>/extraction.json` and set `locale` (`country` as a two-letter code, or leave it empty when unknown; `paper` or `dates` only if the founder said). For each question and asset, quote the shortest line that answers it, word for word from the clean copy, or `null` if it never does. Give answers that mean the same thing the same group letter; list compatible groups (one a narrower or broader form of the other) with a reason. On a return run add the saved assets you did not get again (file: the memory file, `from_memory`: their date, quotes copied from its Assets table) and the agreed answers as asset `agreed`, kind `agreed`, and copy back the saved `skip`, `declined` and `sold_by`. Where two assets state different facts (a team of four against a team of six, nine years against twelve, a suburb or city against another, two prices for one offer), list them in `facts` with a quote from each: the report leads with them whatever they cost in points. Give a bio its `platform` (instagram, tiktok, x, threads) so its length is counted.
3b. **Read it as a sharp buyer would.** Read every clean asset once more, outside the five questions, against today's date (run `date`). List up to six things a careful buyer or a co-founder would catch, each in `also` with the asset, the quote (the exact words that carry the problem, never a neighbouring line) and one line on what to do: a claim of experience, scale or proof that no other asset backs (`[NEED: what would prove it]` in any edit that keeps it); a date that has passed (a sign-by or start date before today) or falls on a weekend; figures that do not reconcile (a capacity cap against the size of the engagement sold, totals that do not add up, a price that differs between assets); a broken next step; a typo. These go early in the chat reply, before the line. Never guess at a meaning: where a line reads two ways, show both readings.
4. **Check the table.** `S verify_quotes.py <work>/extraction.json`, fix every PROBLEM, then `S score_consistency.py <work>/extraction.json --out <work>/score.json` (add `--previous`). Read the ranking. Act on each CHECK line: CHECK FACT is a fact two assets may state differently (add it to `facts` if both describe the same thing); CHECK OVERLAP is one asset naming another's answer (list the pair as compatible if a buyer would hear one inside the other; otherwise leave it). ASK means a figure does not look right; ask before quoting it.
5. **Write the lines.** Three core lines, each from a different asset or angle, each tested on the three gate questions with a reason, each with `aligns_with`; recommend the one that passes all three and best fits who sells and question 3. With no answer to question 3, recommend the line that keeps what most of the weight already shares (the proposal and website outweigh LinkedIn), including a shared moment or problem underneath different buyer labels ("newly promoted, untrained for the people side"); the asset most out of step with that is the one to change first. Never recommend the outlier because it is the sharpest. The line and its `if_you_choose` use only the assets' words for scope: no "in any sector", "anywhere" or market the assets do not say. When the decision (step 7) is which buyer, the recommendation depends on it: set `if_you_choose` on the recommended line ("women in finance and fintech") so the report says so. On a return run with a saved line, set `chosen` (`by`: `memory`, `aligns_with` the agreed groups) and write no new lines unless asked.
6. **Write the edits.** For every asset that answers differently from the recommended line, one edit per question: the current line word for word, the proposed line, a short why. A missing answer gets an added line with `after`. One line that answers two questions gets one edit, which covers both; never a second edit inside it. Every fact in `facts` gets an edit on one of its lines, or `[NEED: which is true]`. Use only facts and credentials the assets state, and write numbers the founder's way. Never add who leads or delivers the work, a headcount, a role or a policy the assets do not state; when the founder supplies a fact in chat that does not square with something else they said ("me plus a few contractors", then "it's six"), say so and give both wordings (for example "a team of six" and "six coaches, employed and contracted") until they pick. A fact the founder gives you in chat ("Target year, use 2030") goes in `founder_said` word for word, so the edit can use it; never leave the founder to type in something they already told you. When an asset's who or what is held for the decision, hold its result and why edits too where they would carry the other buyer's words (digits for their "nine" are fine; "4.500" stays "4.500"); a missing proof becomes `[NEED: what would prove it]`. A proposal or deck is a record once sent: write its edits for the template the founder reuses, and label the asset that way ("Proposal template"). Where the recommended line targets a different buyer from a client-facing asset, do not rewrite that asset's who or what: list them in `declined` with `"by": "decision"` and name the asset in the decision. An edit the founder turns down goes in `declined` with `"by": "founder"` and their reason; the Word file prints "Left as is at your request". A bio's edits must leave the whole bio within its platform's limit (Instagram 150 characters; build_report counts it). An edit that would add a client's name, result or quote becomes `[NEED: a client result you have permission to publish]`, and the chat summary carries one line: "Check the rules on using client names and testimonials where you and your clients are."
7. **Write the decision.** The one choice only the founder can make, as a question.
8. **Build.** `S build_report.py <work>/extraction.json --voice <work>/voice.json --redaction <work>/clean/redaction.json --out <out>` (add `--previous`). Exit 0 with WROTE lines means the files exist. Exit 1 lists PROBLEM lines and wrote nothing: fix the extraction, run again. Exit 2 or a STOP line or a traceback: nothing usable exists; never show a score from that run. A STOP is also a plausibility stop (for example, no asset answers any question): fix what it names, or ask the founder for the one thing it needs. A SyntaxError means the Python is older than 3.8: say so and do the steps by hand.

If code cannot run here, say so in one line, do every step by hand with the same rules: quote word for word, take client names and fees out before quoting, show the five-question table and the arithmetic from `references/scoring.md` so the founder can check it.

## Check

Before showing anything:

1. `S check_copy.py --extraction <work>/extraction.json` reports 0 problems (build_report runs it too).
2. Open the report yourself. Is the headline the first thing a reader sees? Could the founder show it to a co-founder and have them agree what the conflict is in five seconds?
3. Score it against `references/rubric.md`. Rework anything below the bar; do not caveat it.
4. Fresh eyes: if subagents are available, give one the HTML report, the clean assets and the rubric only, and apply what it finds. Otherwise read the report cold as the founder's co-founder would.
5. Nothing added that the assets do not claim. No client name, fee, email or phone number anywhere (build_report refuses them).

## Deliver

The chat reply carries the findings; a founder who never opens a file must still see the value. In this order:

1. The score and band in one line, and the headline conflict in one sentence.
2. A short table: the five questions down the side, one column per asset, each cell a quote of at most eight words or "not stated".
3. Facts that disagree, each as two quotes.
4. Also worth fixing (step 3b), one line each.
5. The line to align on, with which choice it assumes, and why in one sentence.
6. Ready to paste: the full rewritten text of the asset most out of step (a bio, a LinkedIn headline and About, a homepage intro, up to about 180 words), built only from facts the assets state, plus the first proposal-template edit. Once a buyer is chosen (or assumed), carry it through every line of the rewrite: drop the other buyer's cues (their titles, their sector, the scene they recognise) and keep the founder's credentials as plain history. Say which facts you kept and anything you left out. Run `S check_copy.py --text "<the rewrite>"` and fix every PROBLEM before showing it.
7. Any `[NEED]`, then the defaults you used in one line and the at most three questions whose answers would change this, each with what it would change.
8. The two files, named.

Everything the chat says is in the files must be in them: put every finding and fix you mention in the extraction (an edit, a fact or `also`) and rebuild before saying so. In chat, call a client by what the asset is ("the proposal", "your testimonial"), never by name; the cleaned copy is all you read.

Give the founder two files from `<out>`:

- `brand-scan-<business>-<date>.html`: **open this first.** One page: score, headline, the line to align on, the contradictions quoted side by side, all five questions, the decision. Prints to one page on the founder's paper (Letter or A4) or saves as PDF.
- `brand-scan-<business>-<date>-line-edits.docx`: every line edit by asset, the full table, voice drift and how the score works. Hand it to whoever updates the site.

Answer any other question the founder asks in the same turn directly (a headline length, whether a credential should move, whether to resend a proposal): give the answer, then carry on with the scan. Count characters with a script, never by eye.

## Learn

Ask one question, folded into the end of the reply with the intake questions: Spot on / Close, small changes / Wrong line / I disagree with a contradiction. Anything but spot on: ask "What would you change?", then follow the founder's priorities over the skill's order and change the extraction (regroup an answer, pick or rewrite the line as `chosen` with `by`: `founder`, change an edit, `skip` an asset on the questions they name, `declined` for an edit they turn down) and rebuild. Never keep an edit the founder rejected to get past a gate. At most three rounds; leave untouched what they did not mention.

Turn each correction into a proposed learning: a rule, its evidence, the step it applies to ("Say clients, never customers | changed on 20 Oct | Make | watch"). Exclusions become learnings for Intake ("Instagram is personal; leave it out"). Show what will be saved in a few lines and save only on approval:

- Working folder: `S check_memory.py write <work>/results.json --out merigrove-memory/revos-brand-consistency-scan-memory.md --existing <old file if any> --redaction <work>/clean/redaction.json --history "<made> | <line chosen> | <verdict>" --learning "<rule> | <evidence> | <step> | <status>"`.
- Otherwise write it to `<out>` and say: "Attach this next time, or add it to your Project's files, and I'll score your changes against this line."

The memory holds the business, who sells (and who sells which asset), the agreed line and answers, what was left out and which edits were declined, with the founder's reasons, the quotes and voice markers per asset, the scores, learnings and history. Never client names, fees, contact details or anything the founder did not give or approve; check_memory.py refuses to write them. Never save a learning that lowers honesty (for example, "stop flagging the proposal").

## Next step

Close the first delivery with one line, once in the conversation, and nothing else promotional anywhere: "You can see where your story splits; which version of it your best buyers will pay for is a positioning question, and the Merigrove Business Audit scores it: [BUSINESS_AUDIT_URL]."

## Rules

- Quote, never paraphrase, in any cell or "current" line. A contradiction is always two quotes from two named assets.
- The score comes from score_consistency.py. Never judge, adjust or round a figure by eye.
- Client-facing assets (proposal, deck, onboarding, invoice, client email) weigh most; a conflict there costs most.
- When the founder sells personally, the recommended line keeps them visible ("I", their name, or no pronoun), never a corporate "we".
- Client personal data is removed before reading and never written to a report, the memory or the chat (in chat a client is "the proposal" or "that client", even though the paste named them). The raw pastes are deleted once cleaned.
- Write in the founder's English, spelt their way (build_report.py refuses the other spelling once it is known). Numbers go back in the founder's own style; paper, dates and clock follow their country, never their spelling. Never name a country, currency or market the founder's assets do not. No em or en dashes in anything you write; the founder's quotes stay as they wrote them.
- No legal or tax statements. Never say what a law requires, what a tax rate is, or that anything is compliant; check_copy.py refuses those lines.
- No network calls. Nothing is published or sent anywhere.

## Gotchas

- **Saved assets can only be quoted from their saved quotes.** On a return run, an edit to an asset the founder did not paste again must anchor on a quote in the memory file; verify_quotes.py refuses anything else.
- **A vague answer half-agrees with everything.** "Ambitious brands" is compatible with almost any buyer, so sharpening one asset can lower a question's points until the others follow. Say so in one line when it happens; the alignment score shows the progress.
- **Redaction removes a name everywhere.** If a client shares a word with the founder's copy (a client called "Bloom" and a line about blooming), check the clean copy reads sensibly; pass `--keep` for anything removed in error and run redact.py again from the founder's paste.
- **Testimonials are client data.** Pass every testimonial name with `--person` and their company with `--client`; the quote itself can stay. A title stays visible (Dato', Dr); the name does not.
- **Names in every form.** The script finds names after a greeting in many languages, with particles (van der, bin, binti, a/l) and titles, and companies by any common legal form (Inc, LLC, Corp, Pte. Ltd., Pty Ltd, Sdn Bhd, GmbH, S.A., K.K., PT). A brand with no legal form, or a name only mentioned in running prose, needs `--client` or `--person`. Two-letter family names (Ng, Le, Wu) are removed with the full name, and alone only in capitals, so give the full name.
- **Locale is formatting, not law.** Country sets paper and date style only; the founder's own answer wins. If the paste mixes signals (S$ prices and a phone code from another country), ask question 4 rather than guess.
- **Short assets.** A LinkedIn headline or a bio is still read for the five questions; it is only too short for sentence and reading measures.
- **Staff are not clients.** Keep a team member's name with `--keep`; their email and phone are still removed.
- **Corrections that do not square.** If the founder's answer contradicts the assets or an earlier answer, say so in one line and show both readings; never write the newer figure into live copy without saying what it replaced.
- **The proposal is always the heaviest asset.** If the founder says it was a one-off for an unusual client, leave it out (`excluded`) and ask for a typical one rather than letting it lead the ranking.
