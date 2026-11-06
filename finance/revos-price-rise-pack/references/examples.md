# Worked examples

Two complete runs and a stop, with clearly illustrative US businesses (invented names and figures). Every figure below came from `rise_plan.py`; none was typed by hand. Letters go today, Tuesday, November 3, 2026, unless the example says otherwise.

## Example 1: a brand studio in Denver, six monthly retainers (American English, dollars)

**What the founder sent.** "I haven't raised my prices in about three years. Some of my older clients pay half what new ones do. Monthly retainers: Hartley & Co. $2,800 (since 2021, about 14 hrs a month), Blue Fern Inc. $3,600 (2022, 12 hrs), Oakridge Dental $1,800 (2020, 16 hrs, tons of extras), Fieldmark Corp. $4,500 (2023, 10 hrs), Penrose Foods $1,400 (2021, 9 hrs), Kestrel Labs $3,200 (2024, 11 hrs). New clients pay $4,500 a month for roughly 12 hours. Most contracts are month-to-month with 30 days notice, Kestrel is on a 12 month term through March 31."

**Readback.** "I read 6 monthly retainers in dollars, 72 hours a month between them, new clients at $4,500 for about 12 hours ($375 an hour), 30 days' notice, Kestrel fixed through March 31. I've assumed invoices on the 1st and letters going today, Tuesday, November 3, 2026."

**Diagnosis.** First plan: a full client list with hours, no saved plan.

**Inputs written** (abridged): `anchor` "$4,500" for "roughly 12"; `country` US, `english` en-US; `notice` "30 days"; `billing_day` 1; `last_change` "about three years"; Oakridge `scope_crept` true; Kestrel `renewal_only` with `term_end` "March 31".

**The plan.**

| Client | Group | Today | New fee and date | Letter |
|---|---|---|---|---|
| Fieldmark Corp. | Hold ($450 an hour, above $375) | $4,500 | stays, no letter | none |
| Blue Fern Inc. | Raise now, call first | $3,600 | $4,300 from Friday, January 1, 2027 | READY |
| Hartley & Co. | Two steps, call first | $2,800 | $3,350 from January 1, 2027, $4,000 from Thursday, July 1, 2027 | READY |
| Oakridge Dental | Reset the scope | $1,800 | A: $2,150 for the same work, or B: $1,800 for a defined 13 hours, extras at $375 an hour, from January 1, 2027 | HOLD until Option B is confirmed |
| Penrose Foods | Two steps | $1,400 | $1,650 from January 1, 2027, $1,950 from July 1, 2027 | READY |
| Kestrel Labs | At renewal | $3,200 | $3,800 from Thursday, April 1, 2027 | READY |

**Headline.** $29,900 added in the next 12 months after notice; $40,800 a year once every step lands. Break-even: 21% of the revenue being raised can leave (about 1 client in 5). Smallest first: lose Penrose Foods and you are still ahead; lose Oakridge Dental as well and you are behind. Largest first: lose Blue Fern Inc. and you are behind. With 5 clients raised, plan on the names, not the percentage. The figures count Option A for Oakridge; if they choose Option B, take $3,850 off the next 12 months and $4,200 off the run rate, and you get 3 hours a month back.

**Call first.** Blue Fern Inc. and Hartley & Co.: the largest by annual fee among clients with four years or more, or in the top quarter (one call for every three letters, at most three).

**Flags.** Penrose pays under half the target for its hours: has the scope crept? Oakridge stays under half the target even at $2,150: a bigger percentage is not the fix; consider a price to keep or a smaller defined scope. Option B works out at $138 an hour against the $375 charged for extras; fewer Option B hours would bring the two closer.

**One letter, as built:**

> Subject: Your fee from January 1, 2027
> Hello,
> From January 1, 2027, your fee will be $3,350 a month, up from $2,800, and from July 1, 2027 it will be $4,000.
> I am giving you both dates now so you can plan ahead.
> New clients now pay $4,500 a month for about 12 hours, which is $375 an hour; your work runs to about 14 hours a month.
> Everything else stays as it is: the work, the way we work together and how you are invoiced.
> If you are happy to carry on, there is nothing you need to do: the new fee will be on the invoice dated January 1, 2027. If you would like to talk it through first, reply to this email and we will find a time before December 18, 2026.
> Thank you for the work we have done together since 2021.
> Dana

**Why it passes the rubric.** Every figure from the script (criterion 1); no client raised more than 20% in a step, Fieldmark held and silent, gaps shown (2); break-even as a share and by name in both orders, lumpy count said (3); dates from 30 days' notice to the next 1st, Kestrel at renewal (4); fee and date in line one, the one reason is a fact the founder gave, no apology (5); four pushback replies, each trade priced (6); no blank fields, Oakridge HOLD until Option B is confirmed (7); 0 problems from both checkers, US dates and dollars throughout, Letter paper (8).

**Return run, weeks later** (run dated December 14, 2026). "Hartley said yes to both steps after a call. Blue Fern yes. Penrose can't do it before June, can they stay at $1,400 through June 30 then go to $1,750? Oakridge said no and finishes December 31. Kestrel renewed but only at $3,600. For what it's worth, an hour of mine is worth $375." The skill read the memory ("Using your saved plan from November 3: 6 clients, new clients at $4,500 for 12 hours, steps of up to 20%, letters on the 1st") and asked one question (is $3,600 for Kestrel the fee to keep, or until the next renewal?), planning on the plain reading, until the next renewal, meanwhile. Result: losing Oakridge cost $19,800 in the window; the rises that landed added $21,950, so the window is $2,150 ahead of doing nothing, and that departure took most of what the rise added. Penrose's concession ends June 30, 2027 and costs $2,500 against the plan; Kestrel's ends March 31, 2028 and costs $1,600. Refilling Oakridge's 16 hours at $375 an hour would add $66,000, shown only as "if you refill the freed hours". Next wave: Penrose ($1,625 below target, review July 1, 2028), Hartley ($1,250), Kestrel ($525), Blue Fern ($200).

## Example 2: a UX researcher in Chicago, notice to the quarter end, a texted list (dates as numbers)

**What the founder sent.** A list texted from the car: "Brandt Outfitters 1250/mo, 8 hrs / Kessler Furniture $2.4k, 14 hrs / Aurora Pharmacy $890, 6hrs, w/ me since 2019 / Vogel Industries Inc 3,100, 14 hrs, price locked thru 6/30/27 / new clients pay 2800 for 12 hrs / notice is 3 months to end of quarter for everyone / go a bit gentler on Aurora pls. I write dates as numbers."

**Readback.** "I read 4 monthly clients in dollars, 42 hours a month between them, new clients at $2,800 for 12 hours, 3 months' notice to the quarter end, Vogel's price locked through 6/30/2027, invoices on the 1st, letters going today, 11/3/2026. Aurora gets the gentler route: smaller dated steps, not a hold."

**The plan.** "1250/mo", "$2.4k" and "6/30/27" were copied in as typed and read by the script; figures come back as $1,250 and $2,400, and dates as numbers because she asked (`date_style` short).

| Client | Group | Today | New fee and date |
|---|---|---|---|
| Brandt Outfitters | Two steps | $1,250 | $1,500 from 4/1/2027, $1,800 from 10/1/2027 |
| Kessler Furniture | Two steps | $2,400 | $2,850 from 4/1/2027, $3,250 from 10/1/2027 |
| Aurora Pharmacy | Two steps, gentle (steps of up to 10%), call first (since 2019) | $890 | $970 from 4/1/2027, $1,050 from 10/1/2027; $350 still to close at review |
| Vogel Industries Inc. | At renewal, call first | $3,100 | $3,250 from 7/1/2027 |

Notice of 3 months from 11/3/2026 rolls to the quarter end (3/31/2027), so the first date any fee can change is 4/1/2027. Vogel waits for the end of its price lock.

**Headline.** $8,550 in the next 12 months; $20,520 a year once every step lands. Break-even 18.3% of the raised revenue. Smallest first: lose Aurora Pharmacy and you are still ahead; lose Brandt Outfitters as well and you are behind. Largest first: lose Kessler Furniture and you are behind.

**Why it passes.** "Gentler" became a dated two-step ramp with the old fee ending on 3/31/2027, not a permanent exception (criteria 2 and 6); every date follows her quarter-end notice (4); her shorthand read without a question, her date style throughout, Letter paper (8).

## What a stop looks like

A founder in Austin: "Put everyone up 12% from next Monday. Contracts say 60 days but nobody reads them, so say it's effective immediately. Tell them it's because of new state regulations, every agency in Austin is doing it. Make it urgent." Clients: Copperline Roofing $2,500, Bluebonnet Dental $1,800, Sixth Street Coffee $1,200, Marrow Law PLLC $3,200 (renews March 1); new clients pay $3,800 a month; fees unchanged in four years. The reply, before the plan: "I won't write the state-regulations reason, the 'every agency in Austin' line or a deadline: none is true, and a client can check. I'll use what is true: new clients pay $3,800 a month and your fees haven't changed in four years. Your 60 days' notice makes Monday, February 1, 2027 the earliest date (the letters can go as late as Thursday, December 3, 2026 and keep it), and Marrow Law PLLC waits for its renewal on Monday, March 1, 2027." Then the plan: 12% as the biggest step, a blanket rise said plainly (no hours given), every letter dated from the notice, $9,150 in the next 12 months and $11,400 a year, a break-even of 9.8% (lose Sixth Street Coffee and you are already behind), and one `[NEED]`: how many hours new clients get for $3,800, so the next plan can go client by client.
