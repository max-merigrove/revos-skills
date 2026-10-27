# Worked examples

Four scans of clearly illustrative businesses in three countries. None is a real client. Every figure below was produced by the scripts; the full files are in the skill's test runs.

## Example 1: Fernhill Growth (a solo growth marketer who sells personally)

**Where.** United Kingdom (prices in £, a +44 phone number): A4 paper, dates as 20 October 2026, her own British spelling.

**Input.** Website home and about, LinkedIn headline and about, and a recent proposal for paid social management. The proposal carries the client's company, the contact's first name, a monthly fee, an email and a phone number.

**Intake.** None before the scan. The first reply is the full scan on defaults read from the assets (she signs the proposal and LinkedIn says "I", so she sells; everything current; the scan decides the line), ending with two questions that would change it. She answers "all current, let the scan decide", so nothing is rebuilt.

**Cleaning.** "I took out 5 client names, 2 fees, an email address and a phone number before reading."

**The table (extract).**

| Question | Website | LinkedIn | Proposal |
|---|---|---|---|
| Who you serve | "Growth marketing for ambitious brands." (A) | "I'm a fractional CMO for B2B SaaS founders between seed and Series A who are still running marketing themselves." (B) | "Your team is stretched and Meta spend has crept up" (C) |
| What you do | "Growth strategy, channel planning and the hands-on execution to back it up." (A) | "I step in two days a week, own the marketing plan, hire and manage the freelancers" (B) | "We will manage your paid social accounts (Meta and LinkedIn) end to end" (C) |
| Why you | "We're senior people doing the work, not juniors learning on your budget." (A) | "I've been the first marketing hire twice." (B, close to A) | not stated |

**Score.** 24 of 100, Different stories. Who you serve 8 of 25 (worked by hand in `scoring.md`), what you do 3 of 25, result 7 of 20, why 6 of 20, next 0 of 10.

**Headline.** "Your proposal and your website give different answers to what you do."

**Voice drift.** LinkedIn speaks as "I" (10 times); the website as "we" (7 times). She sells personally, so the website's "we" describes a team buyers may never speak to.

**Recommended line** (passes all three tests): "I've been the first marketing hire twice. Now I'm the fractional CMO B2B SaaS founders bring in when they're still running marketing themselves." The website-based line ("Senior growth marketing for ambitious brands...") is shown too, failing "can a buyer picture it" and "could only you say it".

**Edits (two of seven).**
- Website, who you serve. Now: "Growth marketing for ambitious brands." Change to: "Fractional CMO for B2B SaaS founders who are still running marketing themselves."
- Proposal, why you (missing). Add after "Our approach": "I've been the first marketing hire twice, so I'll run your budget the way I ran my own."

**The decision.** "Which business do you want to be known for: the fractional CMO founders bring in, or the paid social service your proposal sells to companies with their own marketing team?"

**Why it passes the rubric.** Every cell verifies word for word; the two quotes behind the headline are named; the score is the script's; the proposal's conflicts cost most; three lines with reasons for each test; seven line edits cover every asset that differs; no client data in either file.

**Two months later (return run).** She rewrites the website from the edits and pastes only that. The scan uses the saved quotes for LinkedIn and the proposal. Score 40 (up from 24), alignment with her line 65 of 100. Who you serve drops from 8 to 6: the vague website used to half-agree with everything, and now sides clearly with LinkedIn, so the proposal stands alone. The report says so; the proposal is the next edit.

## Example 2: Hollow Oak Interiors (a designer who pasted everything in one block)

**Input.** One message: website copy with the founder's own dashes and typos, an Instagram bio typed from a screenshot with emoji, and a proposal from a PDF with the clients' names, home address, postal code, three fees, an email and a phone number.

**Intake.** Scan first, on defaults. Then three questions; answers: she does every sale; keep Instagram (clients find her there); the proposal is closest to the business today ("we only really do kitchens and extensions now"). The second reply rebuilds the line from the proposal.

**Cleaning.** "I took out 3 client names, 3 fees, an email, a phone number, a street address and a postal code before reading." The founder's dashes, typos and emoji stay in the quotes.

**Score.** 42 of 100, Split. The proposal's next step ("please sign below") is not scored against the website's "request a consultation": that is the funnel working.

**Top contradiction.** What you do. Proposal: "Hollow Oak will provide full interior design services ... We do not provide building or installation services." Website: "From a single room refresh to a whole-house renovation, our award-winning studio handles every detail so you don't have to."

**Recommended line** (from the proposal's scope and the bio's voice, keeping her in front): "I'm Morwenna, a mum of two who designs family kitchens and extensions across North Yorkshire around the school run, the dog and the Sunday roast."

**An honest gap.** The website says "award-winning"; nothing names the award. The edit drops it and flags [NEED: the award and the year] rather than keeping or inventing it.

**The decision.** "Are you the designer of family kitchens and extensions who works alongside the builder, or the studio that handles a whole-house renovation end to end, as your website still says?"

## Example 3: Arroyo Brand Studio (a US packaging designer, Letter paper)

**Where.** United States (prices in $, an Austin address): the report prints on Letter, dates read October 20, 2026, and every line is checked for American spelling ("color", never "colour").

**Cleaning.** The proposal names a brewery LLC, its co-founder with a hyphenated Nigerian family name, a referrer at a Corp. and a routing number, account number and EIN. The website testimonial is signed by a Vietnamese founder. "I took out 9 client names, 2 fees, an email address, a phone number, a street address, a postal code and 3 bank or registration numbers before reading." The referrer, named only in running prose, was passed with `--person`.

**Score.** 18 of 100. The website says "Our team has launched more than 40 consumer brands"; LinkedIn says "I'm a one-person studio". The recommended line keeps him visible: "I spent six years designing packaging for a national beverage company. Now I design cans and labels that sell craft beverage brands off a crowded grocery shelf." The website edit that would have kept the team claim asks instead: [NEED: how many brands you have launched yourself, if you want a number here].

## Example 4: Tideline Advisory (a Singapore operations adviser, A4 paper)

**Where.** Singapore (S$ fees, a +65 number, a Raffles Place office): A4, dates as 20 October 2026, Commonwealth spelling ("standardise").

**Cleaning.** A Pte. Ltd. hotel group, a Malay contact with "binti", a Tamil finance lead with "a/l", a Sdn. Bhd. reference in Kuala Lumpur, a testimonial signed in Chinese characters, a UEN and a unit number. Her associate is kept with `--keep`; the testimonial's F&B group, which has no legal form, is passed with `--client`. "Dato'" stays visible in the website testimonial; the name after it does not.

**Score.** 13 of 100. The proposal sells a one-off hotel kitchen audit; the website sells SOPs to multi-outlet groups; LinkedIn sells to hawker-born founders who still cook. She sells with a small team, so "we" and "Tideline" are allowed in the line: "My family ran a hawker stall for 22 years. Tideline writes hawker-born recipes into SOPs, so your second outlet tastes exactly like the first."

**The decision.** "Is Tideline for hawker-born brands opening their second outlet, or for hotels and F&B groups that buy audits and playbooks?"

## What a consistent business looks like

A four-person restaurant bookkeeping firm in Ohio pasted its website, LinkedIn page and welcome email. Every answer fell in the same group: 100 of 100, no contradictions invented, no edits, "we" accepted because a team sells, and the decision moved on to strategy: whether restaurants-only in Ohio is the market to own or to grow beyond.
