# Worked examples

Three complete runs on clearly illustrative businesses, two in the UK and one in the US. Every figure was printed by `scripts/capacity.py`; none was worked out by hand. Use them to see the shape of a finished run, not as benchmarks.

Contents
1. Tidewater Marketing: one offer, four over the ceiling
2. Northlight Bookkeeping: three offers and a VA with no room
3. Copperline Web (US): a founder's own day and time off, and a payroll tax question answered without a figure
4. What plain Claude gives for the same question

## 1. Tidewater Marketing (illustrative): one offer, four over the ceiling

**What the founder said.** A solo marketing consultant with 11 clients on a Growth Retainer, "completely maxed out, working most evenings", turning enquiries away. Per client a month: a 90-minute strategy call, a 30-minute weekly check-in, about 2 hours of campaign planning, 3 hours on the content calendar and posts, ad account tweaks every week ("1-2 hrs each time, honestly it's a lot"), a 2-hour report, about an hour going over everything before it goes out, 4 hours of onboarding per client (clients stay about 9 months), half an hour of invoicing and booking. "I'm doing 50+ hours a week on delivery and I'd like it to be more like 35. Should I hire someone or put my prices up?"

**Questions asked.** One turn: the flag list, and whether they would check moved work. Answer: "flags look right, strategy call definitely stays mine, I'd check the posts, maybe 30 mins a client, not the ads or the report."

**Diagnosis.** First check, one offer, every figure given.

**The flags.** F: strategy call, check-ins, campaign planning, and the review before anything goes out (a quality check, so F whatever the founder might have said). W: posts, ad tweaks, report, onboarding. T: invoicing and booking (software can do it now).

**What the script found.**

| Figure | Value |
|---|---|
| Delivery hours a month | 134.2 (35 a week over 46 working weeks, divided by 12; six weeks off, stated as a default he could change) |
| Your hours per client a month, F + W | 18.6 |
| Load | 204.7 hours a month |
| Ceiling | 7 clients, against 11 |
| Handover order | ad tweaks 71.5, posts 33, report 22 hours a month across clients |
| Ceiling after those three move, with 30 minutes of checking on posts kept | 17 |

**The order of moves on the page.** Stop adding clients for now (70.6 hours a month over). Check price and fit first. Then hand over the three W steps, writing each down. Then, only if still short, test a hire: the founder's own hours fit after the handover, but 126.5 hours a month of moved work has nobody named to take it.

**The note (96 words).** "The ad account tweaks are the surprise: 71.5 hours a month across your 11 clients, about half of the 134.2 you can give. Write down the thresholds you use to change a bid or pause an ad, and someone else can run them while you check the results in your monthly review. The posts and the report come next, with your 30 minutes of checking on the posts kept as yours. With those three moved, your clients need 83.7 of your 134.2 hours, so the evenings can go before any hire does."

**Why it passes the rubric.** Every step has one flag and a reason; the review is F (criteria 1, 6). Load and ceiling come from the script, with the working on the page (2, 3). 35 is the founder's figure, 46 weeks is stated, the hours check ran (4). The ranking is hours x frequency x clients, and the check time is kept (5). The order of moves leads with stopping new clients and price, and says plainly the moved work needs a person, without a hire verdict (7). The note uses his phrase about the ads; check_copy reports 0 problems; one page (8).

## 2. Northlight Bookkeeping (illustrative): three offers and a VA with no room

**What the founder said.** Monthly bookkeeping (22 clients), a payroll bureau (8) and year-end accounts (3 running, each about 6 weeks). Priya, a VA, 10 paid hours a week, does data entry, payslips and filing. The founder works about 45 hours a week, 12 of them on selling, admin and marketing; delivery takes about 35 now. She suggests Priya could do the year-end sign-off. "Can I take on the 4 bookkeeping clients in my pipeline?"

**Questions asked.** One turn: the flags, with the sign-off held at F ("it is your quality check, so it stays yours until someone else is named as the reviewer"). She agreed.

**What the script found.**

| Offer | Clients | Your hours per client a month | Your hours a month | Ceiling on its own | Room at today's mix |
|---|---|---|---|---|---|
| Monthly bookkeeping | 22 | 4.7 | 103.3 | 26 | 2 over |
| Payroll bureau | 8 | 0.75 | 6 | 168 | 9 over |
| Year-end accounts | 3 | 7.9 | 23.8 | 15 | 1 over |
| All offers | | | 133.1 of 126.5 | | |

Available: 33 hours a week (45 less 12, by the script), 126.5 a month. Binding offer: monthly bookkeeping. Hours check: the steps (133.1 a month) match what she said delivery takes (134.2).

**Handover order.** Bank reconciliation 33, chasing receipts 31.8, year-end prep 17.3 hours a month. After they move, her clients need 51 of her 126.5 hours. Priya is at 61% of her paid hours today; the moves would take her to 275%, past the 80% planning line, so 74.8 hours a month of moved work has nobody with room.

**Why it is useful.** The founder's question had a one-line answer (no: 6.6 hours a month over, so the four pipeline clients do not fit today), and the reading shows why a handover alone will not do it: the VA has no room. That is the point where price, fit and paid help come in, in that order.

## 3. Copperline Web (illustrative, Austin, Texas): his own day and time off, and a payroll tax question answered without a figure

**What the founder said.** Website builds (5 running, about 6 weeks each) and care plans (14). Jordan, a contractor, 20 hours a week, does most of the development. 50 hours a week, 15 on sales and admin; "my days run about 10 hours"; "2 weeks PTO plus the federal holidays, call it 4 weeks". "Should I hire a full-time developer? What would that cost me with payroll taxes on $85k?"

**What the skill did first.** Provisional figures from his message, and a short answer to "should I hire?": hand over and check price first, because most of the development already sits with Jordan and the steps still his are W. On payroll taxes: yes, employing someone adds costs on top of the $85k (the employer's share of payroll taxes, unemployment insurance, injury-at-work insurance, any benefits, payroll software), and his payroll provider or accountant can price the full cost in minutes. No figure, no rate. Then the draft flags and three questions. `country` US from "Austin" and "federal holidays", `english` American from his spelling; `day_hours` "10"; `weeks_off_year` "4 weeks".

**What the script found.** 35 a week over 48 working weeks: 140 hours a month. "2 days" of design is 20 hours at his day. Load 211.6, 71.6 over; ceiling on Website builds 4 against 5. Handover: his share of development 36.1, support tickets 21, content loading 14.4; ceiling after 6; after the handover his clients need 140.1 of his 140 hours, which the reading calls "no room at all". Jordan is at 90% of his paid hours today, so the moved work has nobody with room. Hours check: his steps (211.6 a month) run above the 160 he said delivery takes.

**Why it passes the rubric.** His figures, not defaults, for the day and the weeks (4). No tax or pay figure, the question answered in plain words with the fastest route to the real figure, and the reading in his English on US Letter (8). The order of moves stops at "test a hire" without a verdict (7).

## 4. What plain Claude gives for the same question

The Tidewater prompt was put to Claude with no skill (`evals/sample-runs/first-run-typical/baseline-plain-claude.txt`). It did well: it tabled the hours per client, totalled them to about 209 a month (about 48 a week), said "about 8 clients" at 35 hours a week, named the ad tweaks as the biggest block, and advised raising prices before hiring. What it could not do: no flags or reasons, so the review and invoicing sat in the same pile as the strategy call; it used 52 working weeks, so its 8 is one client too generous; it ranked by eye; it went from price straight to "hire for ad management" with nothing written down first; it offered to work out "the most you could pay a hire" (a hire verdict this skill leaves to an accountant); no file, no workbook, no memory. Its "the usual sign you are underpriced" is a general claim with no source. See `assets/before-after.md`.
