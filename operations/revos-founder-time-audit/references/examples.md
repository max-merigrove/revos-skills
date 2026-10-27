# Worked examples

Contents
1. A studio founder in the UK with a Google Calendar (calendar plus what she told me)
2. A coach with no calendar (recall, low confidence)
3. An agency founder in New York, across the US clock change
4. An interior designer in Singapore with a six-day week
5. A localisation agency in Tokyo from a voice note (recall, Saturday mornings, yen in 万)

All five businesses are illustrative. Every figure below came from the scripts on the test fixtures.

## 1. A studio founder with a Google Calendar

**Input.** Priya runs a brand and web design studio with Tom (designer, full time, at capacity) and Jo (VA, 15 hours a week). "I'm working every hour and we're not growing. Attached is my Google Calendar export. Where is my time going and what should I hand over?"

**Diagnosis.** Calendar audit: a Google export covering the last two complete weeks; the week total will come from her.

**Step 1, parse.** 5 to 18 October, London time, Monday to Friday 08:30 to 17:00 as her calendar shows it: 51 work events, 31.4 hours a week once the declined breakfast, two all-day events and five personal or placeholder entries were left out and one overlap shared. A weekly status call with one week skipped still counts 4.33 times a month, from its rule. A quarterly planning day and a monthly accountant call fall outside the fortnight and are listed separately.

**Step 2, sort.** The map groups "Design: Fenwick identity" and "Design: Ashby website" as Design production, both client reporting series as Client reporting, every "Discovery call - ..." as Discovery calls. The status call is proposed for deletion (no decision in four weeks), said out loud in the readback.

**Step 3, readback and questions (turn one).** She answers: "about 50-55 both weeks; evening emails and WhatsApp prob an hour a day; quotes and admin maybe 3hrs a week; I finish design stuff most evenings, 1.5-2 hrs; we bill around 22k a month; Jo has about 5 spare hrs a week at £24/hr, Tom's flat out; workshops and sales calls stay with me, and client reporting, clients expect me on it."

**Challenges and capacity, without extra questions.** The readback states the four challenges as defaults with a reason each (inbox, evening email, client reporting, accountant call), and question 3 names the hours Jo would take (6.8 a week). Her answers settle both: she keeps the inbox, the evening WhatsApp and the accountant call, agrees Jo can draft the reports for her to check, and says Jo goes to 22 hours in November with 7 spare. Had she not, the lowest-ranked handover to Jo would have waited until Jo has room, said in the report.

**Output.** "You work about 52.5 hours a week: 20.6 hours only you can do, 25.1 hours someone could do with instruction, and 1 hour nobody should be doing. Another 5.7 hours are not placed in any activity." Delete the status call (4.3 hours a month). Hand over quotes and admin (3 x 4.33 = 13), client reporting (1.25 x 8.67 = 10.8), invoicing (automate, 6.5), social scheduling (4.3) and expenses (automate, 2.2): 41.2 hours a month, worth £3,981 at £97 an hour if it goes into selling, with Jo's time costing £676. Doing 72%, Strategy 1%: a four-hour Monday morning block. Design production and evening design, 16.4 hours a week, kept because Tom is full: the shape of a role, left as a cash question.

**Why it passes the rubric.** Hours reconcile (reconcile.py 0 problems). Every row has one pile and one action. The list runs by hours a month and shows both factors. The deletion comes first with its reason. The value names its basis and its condition. Four only-you admin rows were questioned once and the answers are in the report. Confidence is fair (the calendar holds 60% of the week) and rows from memory are marked. Jo's handovers fit her spare hours. No personal entry is named.

## 2. A coach with no calendar

**Input.** A voice-note transcript: three sessions Monday, two Wednesday, three Thursday, half an hour of notes after each, "emails all day, two hours minimum", LinkedIn posts "most of the morning", invoicing and chasing an hour and a half, booking and rescheduling by hand "probably 3 hours across the week" because the booking link broke, a monthly corporate workshop (4 hours prep, 3 delivering), monthly supervision, "about 45 hours but it feels like 60", no team, a paper diary.

**Diagnosis.** Recall audit: no calendar or log. Low confidence, said at the top.

**Rows.** Each activity becomes a recall row in her words ("an hour" x "8 a week", "most of the morning" x "weekly"). With no calendar there is no working week to read, so question 1 asks her usual hours ("9 to 6ish", Monday to Friday from the voice note); "most of the morning" is then read against her own 9 to 1 morning as 3.25 hours, and noted. The readback lists the rows in one block and asks what is wrong or missing, plus what the business bills a month in her currency ("about £7k").

**Output.** "Low confidence: from what you remembered..." then "You work about 45 hours a week: 28.2 hours only you can do, 4.5 hours someone could do with instruction, and nothing that nobody should be doing. Another 12.3 hours are not placed in any activity." Two handovers, both automations because there is nobody to delegate to: a working booking link (3 x 4.33 = 13 hours a month) and card payment at booking (6.5). The two automations hold 4.5 hours a week, worth £700 a month at £36 an hour. Email (10 hours a week) was questioned once and kept. The note says the 12.3 hours not placed are likely why the week feels longer than 45, and to track one week before changing anything bigger. The one-week log is delivered with the report.

**Why it passes the rubric.** The low-confidence label leads the report, the log is offered, no handover goes to a person who does not exist, no hire is suggested, and the unplaced hours are shown rather than spread.

## 3. An agency founder in New York

**Input.** Dana runs a four-person marketing agency in Brooklyn with Marcus (account manager) and Lena (freelance designer). "I'm constantly in the weeds and can't get to new business. Attached my Google Calendar export for Oct 26 - Nov 8."

**Step 1, parse.** New York time from the export. The US clocks went back on Sunday 1 November: the weekly client sync stays at 10:00 (EDT, then EST), a webinar sent in UTC lands at 13:00 on both sides of the change, and a London call is shown at 10:00 New York time because London had already changed a week earlier. Friday 6 November is an all-day "PTO": left out of her working days and said in the readback. Her calendar shows 08:00 to 16:00; she corrects it to 8 to 6 and the parser runs again with `--work-hours 8-18`.

**Answers.** "~50 hrs, 6-8 hrs of email/slack after hours + client texts; we bill about $38k/month; Marcus has maybe 5 hrs/wk spare, costs us $45/hr all in; Lena $65/hr; strategy sessions, discovery calls and proposals stay with me; the London call is a one-off; the webinars I don't need." Her dollar sign sets USD; her calendar's New York time zone sets the country, so dates are month first on Letter paper with a 12-hour clock (her American spelling sets only the spelling). Marcus's $45 is used as she gave it: no payroll or on-cost is added.

**Turn two.** She changes the readback's default for the morning inbox, so that one challenge is asked once; the after-hours texts stay with her as stated. The handovers to Marcus need 6.1 hours a week against his 5, so the lowest-ranked one, the content calendars, waits until he has room: a stated default she accepts.

**Output.** "You work about 50 hours a week: 16.2 hours only you can do, 12.6 hours someone could do with instruction, and 0.7 hours nobody should be doing." Delete the webinars (3.2 hours a month), then design reviews (8.7) and ad reporting (8.7) to Marcus, client syncs (3.2), and invoicing automated (2.2): 26 hours a month, worth $4,560 at $175 an hour if it goes into selling, Marcus's time costing $926. Client copywriting, 26 hours a month, is kept: the shape of a role, left as a cash question. Dates read "October 26 to November 8, 2026".

## 4. An interior designer in Singapore

**Input.** Jasmine runs Ong & Co Interiors with Darren (project manager, full), Aisha (junior designer, part time) and Mei Ling (admin, three days a week). "Every project still runs through me and I'm working most Saturdays."

**Step 1, parse.** Singapore time, no clock change; a Sydney supplier call (Sydney already on daylight time) shows at 07:00 and a London client call at 16:00. Saturday site visits every week make her calendar's working week Monday to Saturday, 09:00 to 17:30; nothing assumes Monday to Friday.

**Answers.** "55-60 hrs incl Saturday, plus an hour a night on WhatsApp; revenue about S$65k a month; Darren has no spare; Aisha about 6 spare hrs at S$28/hr; Mei Ling 4 spare at S$22/hr." S$ sets SGD; the Singapore time zone sets day-first dates, A4 and a 24-hour clock.

**Output.** "You work about 57.5 hours a week: 23.1 hours only you can do, 15.9 hours someone could do with instruction, and 2.8 hours nobody should be doing." Delete the second check of Aisha's drawings (11.9 hours a month; Darren already checks them), then contractor quotes to Mei Ling (16.8), showroom visits and material selection to Aisha (8.7 each), progress claims automated (8.7) and client progress reports to Aisha (6.5): 61.2 hours a month, worth S$15,967 at S$261 an hour if it goes into selling, the help costing S$1,037. Every handover fits inside the spare hours she gave. The proposed week runs Monday to Saturday.

## 5. A recall audit from a voice note, Tokyo

**Input.** A four-minute voice-note transcript: a localisation agency, Monday to Saturday with Saturday mornings only, US client calls at 9pm, "revenue is about 450万 a month", QA "3 hours a day mon to fri", email "an hour, hour and a half every morning".

**What the scripts do.** Every phrase goes in as she said it. "450万" is read as ¥4,500,000 and the note says so; "mon to fri" is five days, not two; "hour, hour and a half" is the midpoint, 1.25; "9pm to 10:30-ish" is 1.5 hours. Her yen sets the country (Japan), so the report is A4 with a 24-hour clock despite her American spelling. Saturday has hours to 12:30 and no afternoon; the 9pm calls are kept as now rather than moved into the day. Had the 万 been lost ("about 450 a month"), the run would have stopped: "an hour of your time comes out at ¥2, below the ¥4,000 an hour Freelance reviewer costs. I read your monthly sales as ¥450 (from 'about 450 a month'); is that right?"

**Why it passes the rubric.** Every figure is the one she meant, the plausibility checks ran before anything was built, the low-confidence label leads, the morning email waits for Ren's spare hours as a stated default rather than a question, and the log is delivered for the 20 hours not placed.
