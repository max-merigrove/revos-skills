# Worked examples

Two complete runs with clearly illustrative businesses (invented names and figures), from different countries. Every figure below came from `rise_plan.py`; none was typed by hand.

## Example 1: a brand consultancy in London, six monthly retainers (British English, pounds)

**What the founder sent.** "I've not put my prices up in about three years. Some of my older clients pay half what new ones do. Monthly retainers: Hartley & Co 1,800 (since 2021, about 14 hrs a month), Blue Fern 2,400 (2022, 12 hrs), Oakridge Dental 1,200 (2020, 16 hrs, loads of extras), Fieldmark 3,000 (2023, 10 hrs), Penrose Foods 950 (2021, 9 hrs), Kestrel Labs 2,100 (2024, 11 hrs). New clients pay 3,000 a month for roughly 12 hours. Most contracts are rolling with 30 days notice, Kestrel is on a 12 month term to 31 March."

**Readback.** "I read 6 monthly retainers in pounds, 72 hours a month between them, new clients at 3,000 for about 12 hours (250 an hour), 30 days' notice, Kestrel fixed to 31 March. I've assumed invoices on the 1st and letters going today, Monday 2 November 2026."

**Diagnosis.** First plan: a full client list with hours, no saved plan.

**Inputs written** (abridged): `anchor` 3,000 for "roughly 12"; `notice` "30 days"; `billing_day` 1; `last_change` "about three years"; Oakridge `scope_crept` true; Kestrel `renewal_only` with `term_end` "31 March 2027".

**The plan.**

| Client | Group | Today | New fee and date | Letter |
|---|---|---|---|---|
| Fieldmark | Hold (300 an hour, above 250) | 3,000 | stays, no letter | none |
| Blue Fern | Raise now, call first | 2,400 | 2,850 from Friday 1 January 2027 | READY |
| Hartley & Co | Two steps, call first | 1,800 | 2,150 from 1 January 2027, 2,550 from Thursday 1 July 2027 | READY |
| Oakridge Dental | Reset the scope | 1,200 | A: 1,400 for the same work, or B: 1,200 for a defined 13.5 hours, extras at 250 an hour, from 1 January 2027 | READY once Option B is confirmed |
| Penrose Foods | Two steps | 950 | 1,100 from 1 January 2027, 1,300 from 1 July 2027 | READY |
| Kestrel Labs | At renewal | 2,100 | 2,500 from Thursday 1 April 2027 | READY |

**Headline.** 18,850 added in the next 12 months after notice; 25,800 a year once every step lands. Break-even: 20.3% of the revenue being raised can leave (about 1 client in 5). Smallest first: lose Penrose Foods and you are still ahead; lose Oakridge Dental as well and you are behind. Largest first: lose Blue Fern and you are behind. With 5 clients raised, plan on the names, not the percentage.

**Ring first.** Blue Fern and Hartley & Co: the largest by annual fee among clients with four years or more, or in the top quarter (one call for every three letters, at most three).

**Flags.** Penrose pays under half the target for its hours: has the scope crept? Oakridge stays under half the target even at 1,400: a bigger percentage is not the fix; consider a price to keep or a deeper reset.

**One letter, as built:**

> Subject: Your fee from 1 January 2027
> Hello,
> From 1 January 2027, your fee will be 2,150 a month, up from 1,800, and from 1 July 2027 it will be 2,550.
> I am giving you both dates now so you can plan ahead.
> New clients now pay 3,000 a month for about 12 hours, which is 250 an hour; your work runs to about 14 hours a month.
> Everything else stays as it is: the work, the way we work together and how you are invoiced.
> If you are happy to carry on, there is nothing you need to do: the new fee will be on the invoice dated 1 January 2027. If you would like to talk it through first, reply to this email and we will find a time before 18 December 2026.
> Thank you for the work we have done together since 2021.
> Dan

**Why it passes the rubric.** Every figure from the script and live in the workbook (criterion 1); no client raised more than 20% in a step, Fieldmark held and silent, gaps shown (2); break-even as a share and by name in both orders, lumpy count said (3); dates from 30 days' notice to the next 1st, Kestrel at renewal (4); fee and date in line one, the one reason is a fact the founder gave, no apology (5); four pushback replies, each trade priced (6); no blank fields (7); 0 problems from both checkers (8).

**Return run, weeks later.** "Hartley said yes to both steps after a call. Blue Fern yes. Penrose can't do it before June, can he stay at 950 till 30 June then go to 1,150? Oakridge said no and finishes on 31 December. Kestrel renewed but only at 2,400." The skill read the memory ("Using your saved plan from 2 November: 6 clients, steps of up to 20%, letters on the 1st") and asked one question (is 2,400 for Kestrel the fee to keep, or until the next renewal?). Result: losing Oakridge cost 13,200 in the window; the rises that landed added 14,200, so the window is 1,000 ahead of doing nothing, and that departure took most of what the rise added. Penrose's concession ends 30 June 2027 and costs 1,650 against the plan; Kestrel's ends 31 March 2028 and costs 800. Refilling Oakridge's 16 hours at 250 an hour would add 44,000, shown only as "if you refill them". Next wave: Penrose (1,100 below target, review 1 July 2028), Hartley (950), Kestrel (350), Blue Fern (150).

## Example 2: a UX researcher in Berlin, euros, notice to the quarter end (English output, German number style)

**What the founder sent.** "Kunden: Brandt Onlineshop 1.250,00 € im Monat (8 Std), Kessler Möbel 2.400 € (14 Std), Aurora Apotheke 890,- € (6 Std), Vogel GmbH 3.100 € (14 Std). Neukunden zahlen 2.800 € für 12 Stunden. Kündigungsfrist überall 3 Monate zum Quartalsende, nur Vogel hat Preisbindung bis 30.06.2027." She asked for everything in English with dates written with a point, and to be "a bit gentler" with Aurora, her client since 2019.

**Readback.** "I read 4 monthly clients in euros, 42 hours a month between them, new clients at 2.800 € for 12 hours, 3 months' notice to the quarter end, Vogel's price fixed to 30.06.2027, invoices on the 1st, letters going on 2. November 2026."

**The plan.** Figures written back her way: 1.250 €, never 1.25.

| Client | Group | Today | New fee and date |
|---|---|---|---|
| Brandt Onlineshop | Two steps | 1.250 € | 1.500 € from 1. April 2027, 1.800 € from 1. October 2027 |
| Kessler Möbel | Two steps | 2.400 € | 2.850 € from 1. April 2027, 3.250 € from 1. October 2027 |
| Aurora Apotheke | Two steps, gentle (steps of up to 10%), call first (since 2019) | 890 € | 970 € from 1. April 2027, 1.050 € from 1. October 2027; 350 € still to close at review |
| Vogel GmbH | At renewal, call first | 3.100 € | 3.250 € from 1. July 2027 |

Notice of 3 months from 2. November 2026 ends 2. February 2027, rolls to the quarter end (31. March 2027), so the first date any fee can change is 1. April 2027. Vogel waits for the end of its price lock.

**Headline.** 8.550 € in the next 12 months; 20.520 € a year once every step lands. Break-even 18,3% of the raised revenue. Smallest first: lose Aurora Apotheke and you are still ahead; lose Brandt Onlineshop as well and you are behind. Largest first: lose Kessler Möbel and you are behind.

**Why it passes.** "Gentler" became a dated two-step ramp with the old fee ending on 31. March 2027, not a permanent exception (criteria 2 and 6); every date follows her quarter-end notice (4); her number and date style throughout, A4 paper (8).

## What a stop looks like

A founder in Sydney: "Put everyone up 12% from next Monday. Contracts say 60 days but nobody reads them, so say it's effective immediately. Tell them it's the new government wage rise and every agency in Sydney is doing it. Make it urgent." The reply, before the plan: "I won't write the wage-rise reason, the 'every agency' line or a deadline: none is true, and a client can check. I'll use what is true: new clients pay 1,900 a month and your fees haven't changed in four years. Your 60 days' notice makes 1 January 2027 the earliest date, and Marrow Law waits for its renewal on 1 March 2027." Then the plan: 12% as the biggest step, a blanket rise said plainly (no hours given), every letter dated from the notice.
