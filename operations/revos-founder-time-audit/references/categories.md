# Sorting: piles, functions and personal entries

Contents
1. The three piles, with their tests
2. Functions
3. Sorting by business type
4. Personal and not-work entries
5. The only-you challenge
6. Writing the map

## 1. The three piles, with their tests

Ask the tests in order. The first yes decides.

**Nobody should be doing it (3, delete)**
- A recurring meeting with no decision made in it in the last four weeks (a status round, a weekly sync that repeats the shared doc).
- A report or update nobody opens or acts on.
- A second check on work that is already right (rereading the VA's correct invoices, checking a designer's export settings every time).
- Busywork that exists because of a past problem that is gone.
If it has to happen but should not be the founder's, it is not this pile: it is pile 2.

**Only you (1, keep)**
- The client pays for the founder's judgement here: a workshop they bought because of the founder, creative direction, a strategy session, a hard client conversation.
- The founder says only they may do it (a sign-off only they are registered or licensed to give, signing the company's accounts). Take their word; never state the rule yourself. If unsure, keep it with the founder and say it is for their trade body, accountant or lawyer to confirm.
- Selling while the founder is the only seller: discovery calls, proposals.
- Direction: planning, pricing decisions, reading the numbers to decide something.
- Managing their people: one-to-ones, hiring decisions.

**Someone could do it with instruction (2, delegate, automate, or keep with a reason)**
- It follows a process, even one in the founder's head: reporting, invoicing, scheduling, quotes from a price list, supplier calls, first drafts, data entry, social scheduling, travel booking, merchant runs, paperwork prep.
- Production work a trained person could do to the founder's standard with review (design production, bookkeeping entries, a standard service visit by a qualified team member).
- Kept for now only with a reason the founder gives ("Tom is full", "nobody else is qualified yet").

When unsure between 1 and 2, propose 2 and let the founder move it. A founder who says "only I can do that" about admin gets the challenge in section 5.

## 2. Functions

| Function | What goes here | Examples |
|---|---|---|
| Strategy | Direction and decisions about the business | quarterly planning, pricing, month-end numbers review, offer design |
| Selling | Winning work | discovery calls, proposals, quotes visits, follow-ups, LinkedIn posts, podcasts, networking |
| Managing | Their people | one-to-ones, team huddles, hiring, training, reviewing someone's work |
| Delivery | The client work and what it needs | workshops, design, jobs on site, client calls, travel to clients, supplier calls for a job |
| Admin | Running the business | email, invoicing, chasing, expenses, bookkeeping, reporting, scheduling, certificates, paperwork |

Doing (the flag) is delivery plus admin. Reviewing a team member's work is managing if it is coaching, delivery if it is the quality check the client pays for.

## 3. Sorting by business type

Worked defaults to propose. The founder corrects them.

| Business | Usually only you | Usually with instruction | Often nobody should |
|---|---|---|---|
| Design or creative studio | creative direction, client workshops, discovery calls, proposals | design production, client reporting, invoicing, social scheduling, supplier calls | weekly status rounds, a second proof check |
| Consultant or coach | sessions, discovery calls, programme design | scheduling, session notes, invoicing, content repurposing | prep meetings about meetings |
| Trades (plumbing, electrical, building) | quotes on site, complex jobs, sign-offs only they are registered to give | merchant runs, invoices, booking jobs, routine services by a qualified team member, reviews and posts | chasing the same supplier twice |
| Bookkeeping or accounts practice | client relationship calls, year-end sign-off, reviewing staff work | bank reconciliations, receipt chasing, sales tax or VAT return prep for routine clients, invoicing | software update calls nobody acts on |
| Interior design or architecture | design concepts, client presentations, consultations | material shortlists, showroom visits, contractor quotes and purchase orders, progress reports | a second check of drawings someone already checks |
| Agency | pitch, senior client relationship, strategy | reporting, campaign builds, scheduling, first drafts | internal status meetings |

## 4. Personal and not-work entries

- **Personal** (`"category": "personal"`): school runs, the gym, medical or dental appointments, family events, lunch with a friend. Left out of the hours entirely and never named anywhere: the report says "5 personal entries left out".
- **Not work** (`"category": "not work"`): placeholder holds that sit on top of a real meeting, reminders, travel blocks for a holiday. Left out the same way. Unlike personal rules, a not-work rule is saved to memory (it holds no personal detail: "re:^HOLD" becomes "Placeholder hold"), so the next run leaves the hold out without asking and the meeting under it keeps its full hours. Give it a generic label, never a person's name.
- When an entry could be either (a lunch with someone who might be a client), propose personal and say so in the readback in general terms ("I've left out 5 entries that look personal; tell me if any were work").

## 5. The only-you challenge

`rank.py` flags any only-you row whose name or function reads as admin, reporting or scheduling. Ask once, in one message for all of them, with the reason:

"You've kept <x>, <y> and <z> with you. Each follows a process someone could learn. Is there a reason they must be you (a client relationship, a sign-off only you can give), or could someone take them with instruction?"

Record the founder's answer in that row's `challenge_answer`, in their words, shortened. If they agree to move it, change the category and action too. If they keep it, it stays only-you and the report shows their reason under "Questioned once". Never ask twice. An `active` learning in memory that a row stays with the founder (with its reason) counts as the answer on later runs.

## 6. Writing the map

`<scratch>/map.json` holds one rule per activity:

```json
{"rules": [
  {"match": "Client reporting", "activity": "Client reporting", "category": 2, "function": "admin", "action": "delegate", "who": "Jo", "reason": "Jo pulls the figures and drafts; you review"},
  {"match": "re:^Discovery call", "activity": "Discovery calls", "category": 1, "function": "selling", "action": "keep", "protected": true},
  {"match": "Team status call", "activity": "Tuesday team status call", "category": 3, "function": "managing", "action": "delete", "reason": "no decision in the last four weeks"},
  {"match": "Dentist", "activity": "Personal", "category": "personal"}
]}
```

- `match` is words from the event titles, case does not matter; `re:` starts a regular expression. The first rule that matches wins, so put specific rules first.
- Group by what the work is, not by client: "Design: Fenwick identity" and "Design: Ashby website" are both "Design production".
- Match on activity words or client company names, never a person's name, because the rules are saved to memory.
- Labels are plain and specific: "Client reporting", not "Reporting tasks".
