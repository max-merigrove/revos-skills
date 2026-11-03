# Get Quoted by AI

Find out which questions your buyers ask ChatGPT and other AI assistants name you, and which name your competitors, then get the fixed pages, structured data and llms.txt that answer the ones you are missing from. Built by Merigrove.

## Card copy

When buyers ask ChatGPT who to hire, are you in the answer? Get Quoted by AI turns the questions your buyers really ask into a test you run in under an hour, scores how often you are named with the sample size beside every figure, and writes the pages, structured data and llms.txt for the questions you miss. No ranking promised.

## Install

**Claude (web or desktop app)**
1. Download `revos-get-quoted-by-ai.zip` (do not unzip it).
2. In Claude, open Customize, then Skills, then Upload a skill, and choose the zip. Code execution needs to be on (Settings, Capabilities).
3. Start a new chat and paste the first prompt below.

**Cowork:** Customize, Skills, Install, choose the zip.
**Claude Code:** unzip into `~/.claude/skills/`.

## Your first prompt

> Use revos-get-quoted-by-ai. When buyers ask ChatGPT who does what I do, we never come up. My site is (your address), we sell (what) to (whom) in (where). Here are a few questions buyers have asked me: (paste them)

No address? Paste the text of your main services page instead. Have your robots.txt to hand (your address followed by /robots.txt)? Paste that too. Messy is fine, in any language.

## What you get

**The Quote Kit**, `get-quoted-by-ai_<your-business>_<date>.docx`:

1. **Read first:** where you stand in one sentence, the three things to do this week in order, and the retest date.
2. **Can assistants reach you?** Your robots.txt read crawler by crawler (search, user-triggered, training), whether your page has text before scripts run, and the exact line to change if a search crawler is blocked.
3. **Your buyer questions:** 5 to 12 questions in your buyers' words, each tagged heard or derived, with the page that should answer it.
4. **How to run the test:** one page. Clean sessions, three runs per question, a 72 hour window, what to record.
5. **What to publish:** up to five pages, each opening with a 40 to 60 word answer and ending in its own short FAQ block, using only facts you confirmed. No promise you did not make gets through.
6. **Fact register:** every fact the pages use, as you wrote it, with its source; what you left out; what is still needed.
7. **Machine-readable files:** the JSON-LD and llms.txt, checked, with a plain line on what each does and does not do.
8. **Beyond your own pages:** which sites the assistants lean on, and up to three honest actions.
9. **Results and what to do next:** "no runs yet" on your first visit; on a return visit, how often you were named with the sample size and range, whether it moved against your baseline, and the fix for each question that failed.
10. **What this did not check:** the honest limits.

The kit is a plain working document for you and whoever edits your site, not a branded one; the page text carries no styling, so it takes your own site's design.

**Short of time?** Say so, and it leads with the quick panel: five questions on one assistant, about 18 minutes.

**The test workbook**, `ai-query-test_<your-business>_<date>.xlsx`: every run laid out to fill in, with results, ranges, verdicts (PASS, FAIL or UNKNOWN), your panel headline, the sources assistants list and an accuracy check, all in live formulas.

**site-files/**: the page text (`page-*.html`), `entity.jsonld.json`, one `service-*.jsonld.json` per service, `llms.txt`, and `robots-lines.txt` only when a search crawler is blocked.

## How it thinks

- **The test comes first.** One answer is one sample; the skill counts over at least three runs per question and says UNKNOWN below that.
- **Nothing invented.** Every price, figure and name on a page comes from your fact register. A gap is marked `[NEED: ...]`, never filled.
- **Reach before content.** A security plugin blocking the crawler behind ChatGPT search outweighs any page rewrite. Training crawlers you block stay blocked.
- **Hygiene, not levers.** Google says no special markup or files are needed for its AI answers and ignores llms.txt; the skill still writes them, correctly, and says so.
- **No promises.** Nobody can make an assistant recommend a business. The skill never claims a ranking, and never says a page change caused a change in your numbers.

## It remembers you

After each run it offers to save your facts, your questions, your assistants and your baseline. In Cowork or Claude Code it saves a file in a `merigrove-memory` folder; on claude.ai it hands you the file to download. Next time, bring the workbook back with your runs filled in: it scores them against your baseline, fixes only what failed and sets the next retest. It asks one question at most.

## Safety

Read SKILL.md before installing; it is plain text. The scripts make no network calls. With Claude's own web tools, when your session has them, the skill may read your own website and robots.txt, and run one web search per buyer question without your business name to see which sites come up; nothing else is looked up, and nothing you paste is sent anywhere else. It publishes nothing and changes nothing on your site.

## Want the full system?

Once your baseline is in you will know which questions name you. Whether your positioning gives an assistant a reason to recommend you over the firms it names is the next question; the Merigrove Business Audit scores it: [BUSINESS_AUDIT_URL]
