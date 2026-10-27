# The role pack: scorecard, job ad, interview guide, first 90 days

Read this when the verdict is Ready, when the founder chooses the contractor route, or when the founder asks for the ad and says skip to the check. Write the pack as JSON (blank: `python3 scripts/role_pack.py template`), check it with `python3 scripts/role_pack.py check <rolepack.json> --inputs <inputs.json>`, and pass it to `build.py --role-pack`.

Contents
1. Outcomes first
2. The job ad
3. Ad wording: describe the work, not the person
4. The interview guide
5. The first 90 days
6. The one-to-one
7. The contractor brief
8. Jurisdiction-neutral, always

## 1. Outcomes first

The role is defined by what the person must deliver, built from the hours it takes off the founder, not from a title and a list of traits.

- Three to five outcomes. Fewer leaves the job vague; more and none gets finished.
- Each outcome comes from a task the founder named (`from_task`, with its hours a week), so the scorecard traces back to the founder's week.
- Each has a number and a date: "Every new client welcomed within 24 hours and their kickoff booked by day 7, by day 60". A number the founder can check without asking.
- Each is something the person owns, not something they help with.
- Competencies are tied to an outcome ("clear written updates, for outcome 2"), never free-floating ("great communicator").
- The mission is one line in terms of the work: "Run client admin end to end so the founder's week goes to selling and delivery."

Before: "Proactive, passionate operations assistant to support the founder."
After: "Own client onboarding (8 hours a week of the founder's time today): every new client welcomed within 24 hours and their kickoff booked by day 7."

## 2. The job ad

Sections: headline (the job, not the company's ambitions); about (two sentences on the business, in the founder's words); what you will do; what you will own (the outcomes, in plain words); what good looks like at day 90; pay range; hours; location (remote, hybrid or on site, and where); how to apply (include the work sample if there is one).

- Pay: a range. If the founder leaves it out, set `pay_note` to say so ("the founder prefers to discuss pay at interview"); the report shows that it is their choice.
- Hours and location: real ones. "Available any time" is both a cliche and a discrimination risk.
- Requirements: only what the outcomes need. A degree, a driving licence or a number of years' experience is included only if the work needs it.
- Wording: run the check (section 3). It prompts a review; it is not a compliance verdict.
- Length: as short as the content allows; a learning can set a cap ("ads under 300 words").
- The report prints one line under every ad: "Before you post it, check the employment and anti-discrimination rules where you hire; an employment lawyer or adviser there can confirm the wording." Do not add anything country-specific to the ad itself.

## 3. Ad wording: describe the work, not the person

`scripts/role_pack.py check` flags the terms below. Wording that describes the person the founder wants (by age, sex, race or nationality, disability, appearance or family status) instead of the work puts good applicants off, and in many places it is restricted. A flag is a prompt to rewrite, never a ruling on whether an ad is lawful anywhere; that is for an employment lawyer or adviser where the founder hires.

| Watch for | Why it is flagged | Write instead |
|---|---|---|
| young, youthful, young and vibrant team | Age: describes the people you want by age | Describe the work and how the team works |
| recent graduate, graduates only | Age: tends to exclude older applicants | The skill: "can build a monthly report in a spreadsheet" |
| digital native | Age: a coded word for younger applicants | Name the tools: "confident in Xero and Google Workspace" |
| energetic, high energy, fresh | Age: often read as wanting younger applicants | What the pace actually is: "eight to ten client calls a week" |
| mature, early career, junior person | Age: describes the person, not the work | The level of the work |
| up to / no more than N years' experience | Age: a ceiling excludes older applicants | What they must be able to do |
| N years' experience (a warning, not a problem) | Age, indirectly: a set number of years can exclude | What they must be able to do on day one |
| he, him, his, she, her | Sex | "you" or "they" |
| salesman, chairman, manpower, handyman, waitress, girl Friday | Sex: gendered job words | salesperson, chair, staff, maintenance, server, assistant |
| aggressive, dominant, competitive spirit | Sex, coded: tends to put women off applying | The result: "books 20 calls a month from warm leads" |
| native English speaker, mother tongue | Race or nationality | "written English good enough to email clients without edits" |
| (any nationality) citizens only, must be a (nationality) national, locals only | Race or nationality | Where the work is done and when |
| able-bodied, physically fit, excellent health | Disability | Only if the work needs it, and then what: "lifting boxes up to 15kg" |
| clean driving licence, own car | Disability, indirectly | Only if driving is part of the job |
| attractive, good-looking, presentable | Appearance | The standard of client contact you need |
| no family commitments, no kids, available any time, 24/7 | Family status and sex, indirectly | The real hours |
| culture fit | Vague; can hide bias | The behaviour you need |

Recruitment cliches (also flagged): rockstar, ninja, guru, wizard, unicorn, fast-paced, work hard play hard, passionate, self-starter, proactive, go-getter, hit the ground running, like a family, wear many hats, team player, detail-oriented, excellent communication skills, competitive salary.

Before: "We're a young, fast-paced team looking for a passionate digital native to hit the ground running."
After: "You'll run client admin for a four-person design studio: onboarding, invoicing and the inbox, about 30 hours a week."

## 4. The interview guide

- One question per outcome, at least. Questions ask for evidence of having done the work: "Walk me through the last onboarding sequence you ran. What broke, and what did you change?"
- Beside each question: what a strong answer includes (specific numbers, what they did themselves, what they learned).
- A short work sample that tests the biggest outcome, 60 to 90 minutes at most. Whether it is paid is the founder's decision; record it (`paid`, `unpaid` or `founder to decide`).
- The same questions for every candidate, scored against the strong-answer notes, so the decision rests on the outcomes and not on rapport.

## 5. The first 90 days

Three stages, with decision rights growing at each:

| Weeks | Focus | They decide |
|---|---|---|
| 1 to 4 | Shadow, then do with the founder checking; learn the written process and improve it | Nothing alone; decisions made jointly |
| 5 to 8 | Run the work; the founder reviews outputs, not steps | Operational decisions; the founder is consulted on anything commercial (pricing, scope, client complaints) |
| 9 to 12 | Own the remit | The whole remit; the founder is informed |

The handover test: a task counts as handed over when they have produced it unaided and the founder has reviewed it, at least twice. Write the specific decisions for this role into each stage ("weeks 5 to 8: books kickoff calls and chases invoices without checking").

## 6. The one-to-one

Fortnightly, 30 minutes, the team member's agenda: what is working; what is blocked; what help they need; one development question. Status lives on the task list, not in the one-to-one. A written review every six months against the outcomes, their self-assessment first.

## 7. The contractor brief

For the contractor route, the same outcomes become deliverables, each with a definition of done: "Weekly invoicing run: every invoice for work completed by Friday sent by Monday 10am, and a list of anything over 30 days sent to the founder." The contractor is managed by output, not hours. No 90-day decision-rights table; a review after the first four weeks of deliverables instead. The report adds one line: whether the person would be an employee or a contractor is not something the check decides, and the agreement goes to the founder's accountant or an employment lawyer where they hire.

## 8. Jurisdiction-neutral, always

The pack must travel: a founder in Austin, Singapore, Sydney or Leeds can use it unchanged. The check refuses country-specific employment, tax and benefit terms anywhere in the pack (eligibility to work, work permits, social security or retirement schemes by name, payroll tax forms, statutory minimums, leave entitlements, equal-opportunity boilerplate). The founder's adviser adds what applies where they hire. The work itself may name the founder's own tools and tasks (Xero, the returns a bookkeeping practice prepares for its clients) when the founder named them as the job: that is the work, not a rule about employing someone.
