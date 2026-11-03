# Worked examples

Two complete runs with fictional businesses (the `.example` addresses do not exist). Every figure in them came from the fictional founder; none is a benchmark.

## Example 1: first visit. An IT support firm for dental practices, Melbourne, Australia

**What the founder sent.** "I run a small IT support firm for dental practices in Melbourne, Australia. Our site is brightpathit.example. When a practice manager asks ChatGPT 'who does managed IT for dental practices in Melbourne' we never come up. Can you check whether we show up and fix whatever is stopping us?" Plus the saved home page.

**First reply (value before questions).** Read the home page: it opens "Welcome to BrightPath, your trusted technology partner", has no question headings and no date, and the price sits only in a PDF brochure. The site also says "Flexible 12-month agreements". A draft panel of eight questions (one heard: the question she quoted), a draft answer block with `[NEED: your monthly price]`, `[NEED: your response time]`, and four questions: assistants, buyer questions, facts, robots.txt and who edits the site.

**Her answers.** ChatGPT and Perplexity. Two buyer questions: "how much does managed IT cost for a small clinic" and "what happens if our imaging server goes down". From AUD 1,850 a month for up to 10 users, before tax; 2 hour response on weekdays; no lock-in contract ("the 12 month thing on the site is old"); six staff; Richmond, Hawthorn, Camberwell and Box Hill; credential: leave out. Squarespace; no idea about robots.txt.

**Diagnosis.** First visit; reach unknown (no robots.txt); not quotable (greeting opener, price in a PDF); one contradiction (12-month line versus no lock-in).

**Register.** Ten confirmed facts, one NEED (a credential), one declined ("12-month agreements", so the gate keeps it out of every file).

**Panel.** Ten questions, three heard (her quoted question and the two buyer questions, word for word), seven derived from her offer words; eight run first, five of them naming Melbourne or a suburb; three branded questions.

**Answer block (pricing page, 55 words).** "Managed IT support from BrightPath IT starts from AUD 1,850 a month for up to 10 users, before tax. That covers dental practices across Melbourne's Richmond, Hawthorn, Camberwell and Box Hill, with a 2 hour response on weekdays. There is no lock-in contract, so a clinic can leave if the service does not suit it."

**Files.** Two pages (the pricing page finished; the service page not finished because "what happens if our imaging server goes down" needs her restore process: `[NEED: what you do when an imaging server fails, and how long a restore usually takes]`), `entity.jsonld.json` (ProfessionalService, areaServed Melbourne and the suburbs, no phone, no rating), two Service blocks with `"price": "1850", "priceCurrency": "AUD"`, an llms.txt, a workbook with 54 rows laid out and no rates.

**Chat summary.**
1. This week: run the quick panel today (about 18 minutes), paste your robots.txt, then publish the pricing page.
2. Robots.txt not seen, so reach is unknown; no runs yet: run the baseline before you publish.
3. BrightPath IT: 10 buyer questions (3 heard), 2 pages (1 finished), JSON-LD and llms.txt, saved with the workbook. One [NEED] on the service page (your imaging server answer) and a credential; the old 12-month line is kept out. Check the rules on testimonials, reviews and endorsements where you and your customers are.
4. If you approve, I'll remember your facts, questions and engines so the retest asks one question.
5. Retest on or after 30 November 2026.

**Why it passes.** Every question is traced (1); no rate exists (2); claims_check finds nothing outside the register and the declined line never appears (3); both answer blocks are 40 to 60 words with Melbourne and dental (4); files pass and are labelled as hygiene (5); reach is UNKNOWN, not FAIL, with the step that settles it (6); limits are in section 10 (7); three dated actions with the baseline first (8).

## Example 2: return visit. A bookkeeper, Manchester, United Kingdom

**What the founder sent.** "Here are my results from the weekend. The two pages went live on 14 October." A CSV of 54 rows in her own column order ("chat gpt", "Y", "n", dates as "31 Oct" and "01/11/2026"), and the memory file from 6 October.

**Memory read.** "Using your saved setup: Oakridge Bookkeeping, 8 questions, ChatGPT and Perplexity, 3 runs each; baseline named in 3 of 48 runs, n equals 48 (6 October 2026)." No question asked: the one return question was answered in her message.

**Scores (runlog.py).** Named in 15 of 48 runs, n equals 48 (range 20% to 45%), against 3 of 48 at baseline (range 2% to 17%): the ranges do not overlap, so this moved up. The test cannot say the pages caused it. Q6 on Perplexity has 2 runs: UNKNOWN. Four ChatGPT answers (and one branded answer) say she is "based in Leeds"; the register says Manchester. A directory, accountantsdirectory.example, was listed four times, once beside a Leeds answer.

**Diagnosis per failing question.** Q2 Xero on Perplexity: not quotable (the Xero answer had no heading of its own). Q3 and Q7 "best" and "reliable" bookkeeper in Manchester: quoted not recommended (answers lean on a local listing site and Reddit; a presence gap, not a page gap). Q4 and Q6: no page. Q8 monthly cost: not quotable (the prices page did not open with Manchester and a monthly figure). B1: described wrongly (Leeds).

**Fixes.** A new sole traders page for Q4 and Q6; new openings for the prices and Manchester pages (one `[NEED: what moves a client above £180 a month]`); `entity.jsonld.json` stating Manchester as her town; correct the directory listing; presence actions for Q3 and Q7 instead of another page. Retest on or after 30 November 2026 (four weeks from the return, her cadence).

**Chat summary.**
1. This week: correct the accountantsdirectory.example listing, publish the sole traders page, then the two new openings.
2. Named in 15 of 48 runs, n equals 48, up from 3 of 48; the ranges do not overlap, so this moved, though the test cannot show why.
3. Rescored your 48 panel runs and 6 branded runs; 3 page fixes (2 finished), JSON-LD and llms.txt, workbook updated. ChatGPT says Leeds in 5 answers. Q6 on Perplexity is unknown (2 runs). One [NEED] on the prices page.
4. I'll add today's result and the live dates to your memory if you approve.
5. Retest on or after 30 November 2026.

**Why it passes.** Every rate has its n and range, the unknown stays unknown, movement is called by the overlap rule with the no-cause line (2); fixes go only to failing questions, each with one cause (6); the Leeds error is caught from her own runs, not guessed (7); one question at most on a return visit (8).

## A third, briefer case: a web studio in Rotterdam writing in Dutch

The paste held a robots.txt with `User-agent: OAI-SearchBot / Disallow: /` and `User-agent: GPTBot / Disallow: /` from a security plugin, and a JSON-LD block with a trailing comma and a 4.9 rating from 212 reviews that live on Google Maps, not the site. The kit names the OAI-SearchBot block as what keeps the studio out of ChatGPT search, leaves the GPTBot block as her choice, writes the corrected file for her cousin (who manages the plugin) with the note to change it in the plugin's settings, removes the rating markup and asks whether she will show the reviews on the site, keeps "€ 4.800" as she writes it, writes the page and the panel in Dutch, and builds the kit in Dutch from `assets/labels/labels-nl.json`.
