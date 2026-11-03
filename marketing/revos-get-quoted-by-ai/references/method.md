# Method

How this skill tests whether AI assistants name a business, and how it decides what to fix. Written for founders using this skill and for Claude running it.

## Contents

1. What this is, and what it is not
2. The ladder: retrieved, cited, named, recommended
3. Building the panel
4. Running the test without fooling yourself
5. Scoring: rates, ranges, verdicts and movement
6. Diagnosis and the fix for each failing question
7. Priority order
8. Beyond the founder's own pages
9. Measuring beyond the test
10. Sources and dates

## 1. What this is, and what it is not

An assistant with search either draws on a page or it does not. A well-organised page can be used while ranking below the first screen in search, because the assistant is choosing a passage it can lift and stand behind. Two things follow, and the kit states both:

- **Being used is not being recommended.** A page used as a source means it was useful to consult. Being recommended means the business was put on the buyer's shortlist, and that follows what the rest of the web says (reviews, directories, forums, press), largely independent of the founder's own pages.
- **Answers are not fixed.** One run is one sample of an answer that changes every time. Every figure is a count over several runs, with its sample size, on a date, compared only with the founder's own earlier runs.

Nobody can make an assistant recommend a business. The skill measures what assistants say and fixes what the founder owns: their pages, their files and the facts on them. It runs no assistant itself: the founder runs the questions in their own browser and records what they saw. Claude cannot stand in for that, because a Claude session that knows the business is contaminated (section 4).

The structural fixes are ordinary good page organisation. Google's AI optimization guide (last updated 10 July 2026) says optimising for generative AI search is still search optimisation, that no special files, markup or AI-only pages are needed, and lists as unnecessary: rewriting content only for AI, chopping content into tiny pieces, making variants to catch related queries, and seeking inauthentic mentions. The skill writes for people first and keeps to that list.

## 2. The ladder

| Rung | What it means | What moves it | How it is seen |
|---|---|---|---|
| Retrieved | The assistant read a page while building its answer, without showing it | Reach and readable text | Inferred from the reach and page checks |
| Cited | One of the founder's pages is listed as a source | A direct answer, structure, checkable facts, freshness | The founder's runs (Cited column) |
| Named | The business is named in the answer text | How clearly the web describes who the business is | The founder's runs (Named column) |
| Recommended | The business is put forward as an option to choose | What the wider web says: reviews, directories, forums, press | The founder's runs (Recommended column and framing) |

A fifth state is worth recording: **recommended against**, where an assistant warns a buyer off. So the framing of every mention is recorded: favourable, neutral, hedged or against.

**The diagnosis that matters.** Cited rising while recommended stays flat means the founder's pages work and the wider web does not yet back them up. Another page will not close that. The test before writing another page: if the assistant ignored the founder's own site, would the rest of the web still put them on the shortlist?

## 3. Building the panel

A panel is a small sample of the questions buyers really ask, built from evidence, each traced to where it came from.

| Family | Built from | Shape |
|---|---|---|
| Category | The founder's offer words | "What does a [category] do for [buyer]?" |
| Choosing | Offer words, place, alternatives the founder names | "Who does [category] for [buyer] in [place]?", "How do I choose a [category]?" |
| Problem | Buyers' own questions | The buyer's sentence, unchanged |
| Objection | Buyers' doubts the founder reports | "Is it worth paying for [category] or should we do it ourselves?" |
| Cost | Buyers' own questions, offer words | "How much does [category] cost for [buyer] in [place]?" |

Rules, enforced by `queries.py validate`:

- 5 to 12 questions kept; 8 run first (heard questions first, then one per family). The quick panel is the first 5.
- Every question is tagged `heard` (the buyer's words, with the quote found in what the founder pasted) or `derived` (built from offer words that appear in what the founder pasted). None is invented.
- A heard message written to the founder ("do you shoot at our restaurant or in the studio?", "we have 40 dishes, how long?") names no service and no place, so pasted into an assistant it tests nothing about the business. It is reworded as a buyer asks an assistant ("Do food photographers in Bengaluru shoot at the restaurant or in a studio?"), the buyer's words kept beside it, and marked reworded.
- A question reads as a question a person would type, never a keyword string.
- No unbranded question contains the business name: buyers who do not know you would not type it.
- A local business keeps its place (city or suburb) in at least three of the questions run first, and in three of the five quick ones, because the quick panel is often the only test a busy founder runs.
- Three branded questions check what assistants say about the business (what you do, what you charge or how you compare, where you are). They are run once per assistant and checked against the fact register. They never count in the headline.
- One panel per market and language. A founder whose buyers ask in two languages runs two separate panels; the kit says so rather than mixing them.
- The founder cuts any question no buyer would ask; cuts are kept with the reason.

Why 8 to 12: practitioners who build prompt libraries for brands suggest 30 to 50 prompts for a full library and around 10 for a pilot; a founder with one site and one market needs a pilot, not a library.

## 4. Running the test without fooling yourself

- **Engines.** The ones the founder's buyers use. Default ChatGPT with search on, plus Perplexity. The skill never ranks assistants for a country.
- **Runs.** Three per question per assistant at minimum. A full panel is 8 x 2 x 3 = 48 runs plus 6 branded runs, about an hour. The quick panel is 5 x 1 x 3 = 15 runs plus 3 branded, about 18 minutes.
- **Clean sessions.** A private or logged-out window, chat history and memory off where the assistant allows, a new chat per run, the question pasted exactly. Record date and location, because answers vary by place and over time.
- **A window.** All runs within 72 hours, so a platform change does not land in the middle of a test.
- **Before publishing.** The baseline is taken before any page from the kit goes live, so the retest has something to compare with.
- **What to record.** Named, cited, recommended (or against), framing, the sources listed, and anything the answer says about the business.

## 5. Scoring

`runlog.py` does every count and every range; the model never counts by eye.

- **A rate is always "x of y, n equals y".** No percentage without its n.
- **UNKNOWN below three runs** for a question on an assistant, with the runs shown. Never a pass or a fail.
- **PASS** when named in at least half the runs; **FAIL** below half with at least three runs; "seen in some runs" beside a FAIL with some hits.
- **The range** beside each rate is the 95% Wilson score interval: with 3 runs it is wide, which is the point.
- **The headline** is the panel total (named in X of N runs), steadier than any single question. Verdicts per question are directional.
- **Movement** against the baseline is "moved up" or "moved down" only when the two ranges do not overlap; anything else is "no clear change". Example: 3 of 48 (range 2% to 17%) against 15 of 48 (range 20% to 45%) moved up.
- **Never cause.** A page going live and a change in rates can coincide by chance. The kit says the test cannot show why.

## 6. Diagnosis and fix

Each failing question gets one cause and one fix:

| Cause | Evidence | Fix |
|---|---|---|
| Unreachable | A search crawler blocked; the page is empty without scripts; noindex | The exact robots.txt change, or a brief for whoever builds the site |
| No page | No page answers the question | A new page (counts toward the five) |
| Not quotable | A page exists but opens with a greeting, buries the answer, or keeps the price in a PDF | A new opening answer block and question headings on that page |
| Quoted not recommended | The page is cited but others are named, or the answers lean on directories, forums and listing sites that name others | Presence work (section 8), not another page |
| Described wrongly | A branded or unbranded answer states a wrong place, price or service | Correct the source it cited where possible; state the fact plainly on the page and in JSON-LD |

## 7. Priority order

Reach first, then the pages that already exist, then missing pages, then presence beyond the site. Nothing lower is worth doing while something higher is open. One exception sets the order of the three actions: the baseline runs before anything changes, including a robots.txt fix, so the retest compares like with like. Unblocking is the same day, straight after. A founder who would rather unblock first is told, in plain words, what it costs ("your baseline will then start from the fixed state, so the retest cannot show what the unblock did") and chooses; the kit records the choice. For a founder short of time the quick panel (about 18 minutes) is the baseline; the full panel can follow.

## 8. Beyond the founder's own pages

- Assistants quote where a business appears, not only its site. The sources tally (from the founder's runs, or the search proxy) shows which sites come up: own, competitor, directory or review site, media, forum, video, other.
- It is a portfolio, not a menu. A single third-party site that matters today can matter nothing after one change.
- Up to three honest actions: claim or correct a listing, keep a business profile consistent with the fact register, ask real customers for real reviews. Never manufacture mentions, plant reviews or publish a list that ranks yourself first: for a business that is not already the obvious choice, such a list tends to get used to describe the competition.

## 9. Measuring beyond the test

Most visits that follow an assistant's recommendation arrive as a branded search or a direct visit, not tagged as AI. So the kit points the founder to: an "AI assistant" option in their enquiry form's how-did-you-hear field, their own branded search figures, and the free reports that exist (Google Search Console; Bing Webmaster Tools' AI performance report, in beta in 2026). No benchmark from anyone else's data is used.

## 10. Sources and dates

All opened on 2 November 2026 unless stated.

- Google, AI optimization guide (last updated 10 July 2026): no special files or markup needed; Google Search ignores llms.txt.
- Google, structured data changes: the FAQ rich result stopped appearing from 7 May 2026.
- Google, common crawlers (last updated 30 October 2026): Google-Extended does not affect inclusion or ranking in Google Search.
- OpenAI, bots page: OAI-SearchBot feeds ChatGPT search; GPTBot is training; ChatGPT-User is user-initiated and robots.txt may not apply.
- Anthropic, crawler article (dated 7 April 2026): ClaudeBot training, Claude-User user fetches, Claude-SearchBot search.
- Perplexity, crawlers page: PerplexityBot surfaces sites in search; Perplexity-User generally ignores robots.txt.
- llmstxt.org (Jeremy Howard; modified 10 August 2026): the llms.txt format.
- SE Ranking via Search Engine Journal (20 November 2025): about 300,000 domains, no measurable link between llms.txt and citations.
- SparkToro and Gumshoe via Search Engine Journal (30 January 2026): the same brand list in under 1% of repeated runs; visibility across many runs steadier than position. Not peer reviewed.
- Vercel and MERJ (17 December 2024): major AI crawlers measured did not run scripts, Gemini via Googlebot and Apple's crawler the exceptions. Dated; treat as a reason to check.
- Practitioner guidance on prompt panels (Aleyda Solis; Entrepreneur, 14 September 2026): build from real buyer language, run each prompt several times, report rates not positions.
