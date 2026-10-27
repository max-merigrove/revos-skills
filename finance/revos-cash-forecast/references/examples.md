# Worked examples

Five complete runs on clearly illustrative businesses in four countries. Every figure was printed by the scripts; none was worked out by hand. Use them to see the shape of a finished run, not as benchmarks.

Contents
1. Harbor and Pine Studio (US): a bad quarter breaches before a new contractor
2. Tanjong Interiors (Singapore): the GST the founder listed causes the breach
3. Hollis Joinery (UK): no breach, and still "not yet" on a hire
4. What plain Claude gives for the same question
5. Fernhill Software (US): payroll with a new batch code every run, and one client counted once
6. Jozi Gatherings (South Africa): a seasonal business, rand amounts as typed

## 1. Harbor and Pine Studio (illustrative, US): a bad quarter breaches before a new contractor

**What the founder said.** "We're a 5-person brand studio. Here's our Chase export. Payroll runs through Gusto on the 15th and the last day of the month. I'm thinking about bringing on a contract developer at $7,500/month starting 12/1. Can we swing it without sweating payroll?"

**What the scripts read.** Chase layout; dates month first, read from the data, so "12/1" is December 1; US dollars as a labelled guess the readback confirms; 120 of 120 rows reconcile; $33,163.74 on October 16. Net pay of $9,850 found on the 15th and at month end (not as fortnightly). Gusto's tax debits and a September estimated tax payment listed as tax-like and not projected.

**What the founder listed.** Payroll taxes of $1,870.40 with each payroll (from Gusto) and a Q4 estimated tax of $7,500 on January 15 (from their CPA). A $25,000 line. Brightline owes $9,500 due November 15 and pays two weeks late.

**What the forecast found.** "Your cash falls below its $25,000 safety line in week 13 (from Jan 9) in a normal quarter, when payroll of $9,850 leaves, and in week 3 (from Oct 31) in a bad one." Brightline Foods and Cedar & Oak came out of the usual pattern ($3,161 a week down to $2,066) because their invoices are listed. The contractor: not yet, because a bad quarter crosses the line even without it. Moves, in date order: hold the contractor; chase Lumen Health for its $12,500 by October 30; hold the $1,500 transfer to savings due November 20.

**Why it passes the rubric.** Every tax line is one the founder listed, labelled founder supplied; nothing was placed by a US rule (3). Dates print month first and figures in dollars throughout; the founder's own "12/1" and "1/15" read the way they write them (8).

## 2. Tanjong Interiors (illustrative, Singapore): the GST the founder listed causes the breach

**What the founder said.** "Small interior design firm in Singapore. DBS export attached. We have GST going out end of the month and I want to hire a project coordinator. Is our cash ok through to Chinese New Year?"

**What the scripts read.** A DBS layout no published source confirms, with no running balance: the parser asked once, with three sample rows, and the founder confirmed. The ledger balance printed above the header, S$56,102.39, opens the forecast; the currency comes from that line. DBS writes months as names, so the date order came from the founder's own "15/11", which reads only one way; their "1/12" is then 1 December, with no extra question.

**What the founder listed.** CPF of S$4,212 by the 14th each month and GST of S$7,800 due 31 October, both from their accountant. The CPF Board line found in the export was removed so it is not counted twice.

**What the forecast found.** "Your cash falls below its S$29,598 safety line in week 3 (from 31 Oct), in a normal quarter and a bad one, when GST (S$7,800) leaves." Bad-quarter lowest -S$9,271 in week 10, once Marina Bay Hotel is counted from its invoice only and not also in the usual pattern. The coordinator: not yet. Moves: collect the money for work in the first weeks on time; talk to the accountant about the GST today; hold the hire.

## 3. Hollis Joinery (illustrative, UK): no breach, and still "not yet" on a hire

**What the founder said.** A joiner on Starling: "Thinking of taking on a qualified joiner from 7 December, about 3,400 a month all in plus 1,200 for tools and the van deposit. Can I afford it?" Listed: a tax payment of £3,100 on 31 January, from their accountant.

**What the forecast found.** "Your cash stays above its £3,415 safety line for all 13 weeks, in a normal quarter and a bad one. The lowest point in a bad quarter is £9,442 in week 13 (from 9 Feb)." The decision: "not yet. A bad quarter crosses the safety line in week 11. No start inside these 13 weeks clears it." (Davies Homes and Claremont Lettings come in from their invoices only; the weekly fuel card is a regular line at its middle figure.) The £3,100 sits on 31 January exactly as given; the skill does not move it for a weekend, because it keeps no country's calendar.

**Why it is the interesting case.** No breach at all, yet the answer to the hire is still "not yet", because with the joiner loaded a bad quarter crosses the line in week 11. A yes needs the business still to hold eight weeks of the new cost above the line when the forecast runs out.

## 4. What plain Claude gives for the same question

Run on Harbor and Pine's export with no skill (`evals/sample-runs/us-founder-chase/baseline-plain-claude.md`), a capable assistant totalled the months, took out the one-offs, called the business "roughly break-even" and said the founder could "probably swing December" with the contractor. It also named a January tax payment from general knowledge of US rules. Week by week, a quarter where clients pay 20% less and two weeks later puts the account under the founder's own $25,000 line in week 3, before the contractor starts.

## 5. Fernhill Software (illustrative, US): payroll with a new batch code every run, and one client counted once

**What the founder said.** "need a cash forecast. bofa business checking export attached, 6 months. 5 person software consultancy in seattle. worried about december, northwind (biggest client) keeps paying later and later and still owes the aug invoice. payroll's gusto on the 15th and last day."

**What the scripts read.** Bank of America layout with its summary block; 176 of 176 rows reconcile. Every Gusto net-pay debit carries a different batch code (`GUSTO DES:NET B0BC77 ID:7KX3Q9M18 ...`); grouped by payee, they are two monthly lines, debited around the 12th and the 28th, a day or two before payday. The card bill and the cloud bill vary by month and are regular lines at their middle figure. Gusto's tax debits are one tax-like payee (12 payments), not projected. Northwind is 87% of the usual pattern; once the founder lists its three invoices, the pattern drops from $13,813 to $1,794 a week. US dollars stated as a default; Letter paper from the founder's city.

**What the forecast found.** "Your cash falls below its $69,891 safety line in week 1 (from Oct 19), in a normal quarter and a bad one." In a bad quarter the account is $8,169 overdrawn in week 8 (from Dec 7), the week the holiday bonuses and mid-month payroll leave. Moves: chase Northwind's $61,200 today; hold the $2,000 transfer to savings; find the gap between the December low and the line a week before it. The re-run date sits on its own line.

**What the first reply caught.** The founder said Northwind "still owes the aug invoice". The finder's `last receipts` line shows a $64,800 wire on October 2 referencing INV-1063. The first reply, before any question, gives the provisional week and says: if INV-1063 was the August invoice, it is already in the opening balance and the open one is September's; which is it? Counting it as owed would put money in December that arrived in October.

**The return run.** A month later, a one-month export finds almost nothing regular on its own. Every saved bill, both payrolls and Lakeview's retainer are carried from memory; Northwind stays out of the pattern and the founder lists its open invoices. A bad quarter crosses the line in week 3.

## 6. Jozi Gatherings (illustrative, South Africa): a seasonal business, rand amounts as typed

**What the founder said.** "Hi, need to see if cash holds through Jan. Events co in Joburg, bank CSV attached (semicolons). Nov/Dec is our peak, Jan-Feb is dead and that's when we get caught every year." Answers typed as "R412 000", "about R41k", "R96 400", "keep R250k min".

**What the scripts read.** An unknown layout read by its column names, newest first, space thousands and comma decimals, 161 of 161 rows reconciled. The monthly payroll-tax payments, the VAT and a provisional tax payment in the export are tax-like and not projected; the founder lists the payroll tax and the VAT from the bookkeeper. Money in moved by more than half between months, so question 3 asked which months are quiet.

**What the forecast found.** "Your cash falls below its R250 000 safety line in week 10 (from 19 Dec) in a normal quarter, when payroll of R132 400 leaves, and in week 6 (from 21 Nov) in a bad one." The usual pattern leaves out the three clients with listed invoices and is off in January and February. The supplier payments for each booked event and the temps for November and December are costs of booked work, never offered as moves. The reading says plainly that the forecast ends on 15 January, so the rest of January is past what it can see.

