# Worked examples

Two complete runs with fictional businesses (the `.example` addresses do not exist), and a briefer third. Every figure in them came from the fictional founder; none is a benchmark. Counts, verdicts, ranges and dates are copied from the scripts' own output on those inputs.

## Example 1: first visit. An IT support firm for dental practices, Denver, Colorado

**What the founder sent.** "I run a small IT support firm for dental practices in Denver, Colorado. Our site is peaklineit.example. When a practice manager asks ChatGPT 'who does managed IT for dental practices in Denver' we never come up. Can you check whether we show up and fix whatever is stopping us?" Plus the saved home page.

**First reply (value before questions).** Read the home page: it opens "Welcome to Peakline, your trusted technology partner", has no question headings and no date, and the price sits only in a PDF brochure (page_check: 3 fail, 4 unknown). The site also says "Flexible 12-month agreements". A draft panel of eight questions (one heard: the question he quoted), a draft answer block with `[NEED: your monthly price]`, `[NEED: your response time]`, and four questions: assistants, buyer questions, facts, robots.txt and who edits the site.

**His answers.** ChatGPT and Perplexity. Two buyer questions: "how much does managed IT cost for a small dental office" and "what happens if our imaging server goes down". From $1,850 a month for up to 10 users; 2 hour response on weekdays; no long-term contract, month to month ("the 12 month thing on the site is old"); six on the team; Cherry Creek, Highlands, Lakewood and Aurora; credential: leave out. Squarespace, he edits it himself; no idea about robots.txt.

**Diagnosis.** First visit; reach unknown (no robots.txt); not quotable (greeting opener, price in a PDF); one contradiction (12-month line versus month to month).

**Register.** Ten confirmed facts, one NEED (a credential), one declined ("Flexible 12-month agreements", so the gate keeps it out of every file).

**Panel.** Ten questions, three heard and seven derived from his offer words; eight run first, five of them naming Denver; three branded questions. "what happens if our imaging server goes down" is written to the firm and names no service or place, so it runs reworded as "What happens if a dental practice's imaging server goes down, and how fast can a managed IT provider in Denver restore it?", with his buyer's words kept beside it. queries.py validate: 0 problems.

**Answer block (pricing page, 48 words).** "Managed IT support from Peakline IT starts from $1,850 a month for up to 10 users. That covers dental practices in Denver, Colorado, including Cherry Creek, Highlands, Lakewood and Aurora, with a 2 hour response on weekdays. There is no long-term contract: the plan runs month to month."

**Files.** Two pages (the pricing page finished; the service page not finished because "what happens if our imaging server goes down" needs his restore process: `[NEED: what you do when an imaging server fails, and how long a restore usually takes]`), `entity.jsonld.json` (ProfessionalService, Denver, CO, areaServed Denver and the four areas, no phone, no rating), one Service block on the service page with `"price": "1850", "priceCurrency": "USD"` (the pricing page for the same service gets none), an llms.txt, and a workbook with 54 rows laid out and no rates.

**Chat summary.**
1. This week: run the quick panel today (about 18 minutes), paste your robots.txt, then publish the pricing page.
2. Robots.txt not seen, so reach is unknown; no runs yet: run the baseline before you publish.
3. Peakline IT: 10 buyer questions (3 heard), 2 pages (1 finished), 2 JSON-LD files and llms.txt, saved with the workbook. One [NEED] on the service page (your imaging server answer) and one credential; the old 12-month line is kept out. Check the rules on testimonials, reviews and endorsements where you and your customers are.
4. If you approve, I'll remember your facts, questions and assistants so the retest asks one question.
5. Retest on or after December 1, 2026.

**Why it passes.** Every question is traced and the buyer message is reworded with its quote kept (1); no rate exists (2); claims_check finds nothing outside the register and the declined line never appears (3); both answer blocks are 48 words with Denver and dental (4); files pass and are labelled as hygiene (5); reach is UNKNOWN, not FAIL, with the step that settles it (6); limits are in section 10 (7); three dated actions with the baseline first (8).

## Example 2: return visit. A bookkeeper, Columbus, Ohio

**What the founder sent.** "Here are my results from the weekend. The two pages went live on October 14." A CSV of 54 rows in her own column order (Date, Assistant, Q, Run, Named, Sources, What it said; "chat gpt", "Y", "n", dates as "Oct 31" and "11/01/2026"), and the memory file from October 6.

**Memory read.** "Using your saved setup: Maple Lane Bookkeeping, 8 questions, ChatGPT and Perplexity, 3 runs each; baseline named in 3 of 48 runs, n equals 48 (October 6, 2026)." No question asked: the one return question was answered in her message.

**Scores (runlog.py).** Named in 15 of 48 runs, n equals 48 (range 20% to 45%), against 3 of 48 at baseline (range 2% to 17%): the ranges do not overlap, so this moved up. The test cannot say the pages caused it. Q6 on Perplexity has 2 runs: UNKNOWN (she ran Q5 there four times instead). Four ChatGPT answers (and one branded answer) say she is "based in Cleveland"; the register says Columbus. A directory, bookkeepersdirectory.example, was listed four times, once beside a Cleveland answer.

**Diagnosis per failing question.** Q2 QuickBooks Online on Perplexity: not quotable (the QuickBooks answer had no heading of its own). Q3 and Q7 "best" and "reliable" bookkeeper in Columbus: quoted not recommended (the answers lean on columbuslistings.example and columbusforum.example, each listed 12 times; a presence gap, not a page gap). Q4 and Q6: no page. Q8 monthly cost: not quotable (the prices page did not open with Columbus and a monthly figure). B3: described wrongly (Cleveland).

**Fixes.** A new sole proprietors page for Q4 and Q6; new openings for the prices and Columbus pages (one `[NEED: what moves a client above $350 a month]`); `entity.jsonld.json` stating Columbus, OH as her city; correct the directory listing; presence actions for Q3 and Q7 instead of another page. Retest on or after December 1, 2026 (four weeks from the return, her cadence).

**Chat summary.**
1. This week: correct the bookkeepersdirectory.example listing, publish the sole proprietors page, then the two new openings.
2. Named in 15 of 48 runs, n equals 48, up from 3 of 48; the ranges do not overlap, so this moved, though the test cannot show why.
3. Rescored your 48 panel runs and 6 branded runs; 3 page fixes (2 finished), JSON-LD and llms.txt, workbook updated. ChatGPT says Cleveland in 5 answers. Q6 on Perplexity is unknown (2 runs). One [NEED] on the prices page.
4. I'll add today's result and the live dates to your memory if you approve.
5. Retest on or after December 1, 2026.

**Why it passes.** Every rate has its n and range, the unknown stays unknown, movement is called by the overlap rule with the no-cause line (2); fixes go only to failing questions, each with one cause (6); the Cleveland error is caught from her own runs, not guessed (7); one question at most on a return visit (8).

## A third, briefer case: a web studio in Asheville, North Carolina, with a messy paste

The paste, typed in lower case in one message, held a robots.txt with `User-agent: OAI-SearchBot / Disallow: /` and `User-agent: GPTBot / Disallow: /` from a security plugin her cousin Marcus set up, a JSON-LD block with a trailing comma (jsonld_check: does not parse, line 10, column 1) and a 4.9 rating from 212 reviews that live on Google Maps, not the site, and a Google review saying the studio built a site in "3 weeks flat". The kit names the OAI-SearchBot block as what keeps the studio out of ChatGPT search, leaves the GPTBot block as her choice (robots_check: training only), writes the corrected file for Marcus with the note to change it in the plugin's settings (re-checked: no other crawler changed), removes the rating markup and asks whether she will show the reviews on the site, declines "3 weeks flat" after she confirms 4 to 6 weeks, keeps "$4,800" as she writes it, and builds the panel (8 questions, 1 heard), one finished page (52-word answer block) and the kit in American English.
