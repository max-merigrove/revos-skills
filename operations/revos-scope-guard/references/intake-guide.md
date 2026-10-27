# Intake guide

How to turn what the founder pastes into `kit.json` with the fewest questions.

## 1. Extract first

Read everything the founder gave (the opening message, pasted emails, WhatsApp or Slack threads, texts, a proposal, an invoice) before asking anything. Pull out:

| Look for | Goes to | Notes |
|---|---|---|
| Who the client is, what the offer is called | `client`, `offer` | Use the founder's own name for the offer |
| Where the founder is based | `country` | A two-letter code or the country's name, from what they say ("we're in LA" is US, "in Berlin" is DE). It sets the paper and, when no date shows it, the date order. Never read it from spelling: a Berliner who writes "colors" still prints on A4 |
| What the client pays | `fee` | Keep the founder's text exactly, in any language or number format ("1.9k pm", "$8,400", "S$3,600 a month + GST", "9.800,00 € netto"); the script reads the figure, the period, the currency sign and the founder's decimal style. Never rewrite "9.800,00" as "9800" yourself: the founder's own figures are how the script learns their style |
| The currency | `currency` | Only if the founder names it and the fee text does not show it ("we bill in AUD"). A bare "$" stays "$": never decide which country's dollar it is |
| Tax words beside their own fee | `price_wording` | Read by the script from the fee ("+ VAT" becomes "plus VAT"). The replies repeat the founder's words and nothing more. If the fee is written including tax ("£2,280 inc VAT"), the script asks for the figure before tax; never work it out |
| Monthly or one-off | `billing` | "pm", "/mo", "a month", "retainer" mean monthly |
| Hours planned when it was priced | `planned_hours` | "20 hrs a month", "about 5 days" (the script converts days at the founder's working day) |
| How long their working day is | `hours_per_day` | Only if they said ("our working day is 9 hours"). Otherwise the script counts 8 and states it, editable |
| Hours the signed agreement states, when they differ from the hours priced on | `agreed_hours` | "SOW says up to 35 dev hrs/mo" while the founder planned 40. Never pick one: the founder chooses the pricing figure, and the scope statement keeps quoting what the client signed until the client agrees a change. `compute` prints both rates |
| The founder's own words for hours and ranges in client messages | `hours_label`, `range_word` | "21 bis 28 Std." gives `"Std."` and `"bis"`; every rebuild keeps them. Set only when the founder asks |
| Hours actually worked, if said | `actual_hours` | "I'm doing more like 30" |
| What was agreed: deliverables, quantities, rounds of changes | `scope.deliverables`, `revision_rounds` | From the proposal or the founder's description |
| Each request: what, when, rough hours, done or open | `requests` | One row each. Keep the founder's words for hours ("half a day", "90 mins", "a day and a half", "7,5 Std.", "2 Tage", "30-40 hrs") and dates ("3rd Sept", "9/26", "13.10.", "September"). A range stays a range. Status: `done` (done, not billed), `billed`, `swapped`, `asked` (open), `declined` |
| Anything the founder owes the client that slipped | `founder_owes` | "the Sept speed audit didn't happen, that's on us". The reset note owns it in one clause. Also look for the client asking "did X happen?" |
| Which way round they write dates | `date_order` | Leave empty: the script reads it from any date that can only be one way (9/26 is month first, 26/9 day first). Set it only if the founder says, or answers the readback question |
| What the client must provide, and when | `scope.dependencies` | Photos by the 5th, feedback within five working days, access to the site |
| A message the founder wrote to this client | voice, `english` | Greeting, sign-off, sentence length, "I" or "we", contractions. Set `english` to american or british only when their message shows it ("color", "colour", "Talk soon", "Cheers"); otherwise leave it empty |
| Their rate for extra work, if they have one | `rate_for_changes` | A day rate divided by their own working day is fine as `"=650/8"` |

Never fill a figure the founder did not give. Hours they did not give stay empty and become [NEED]. If the founder gave a range, keep the range; the script uses the middle and says so.

Contradictions: when two figures disagree ("we said 20 hours" then "the proposal says 16"), do not pick one. Put both in the readback and ask which is right.

## 2. Read back in one block

The first reply leads with substance (SKILL.md, Start): the provisional figures, the catches and the message most needed, drafted. The readback follows it. In the same message as any questions, read back what you extracted, in plain words, in the founder's own currency and date style, so the founder corrects it once:

> I read: Harbour Bakery pays £1,900 a month plus VAT for social media, planned at 20 hours. Since August they've asked for six things outside that: a landing page (about 6 hours, still open), two extra reels (3 hours each, done), a menu redesign (4 hours, done), weekend posting (2 hours, done) and a newsletter (I couldn't tell if that was in what you agreed). What's wrong or missing?

> I read: Copper Kettle pays a flat $8,400 for the brand refresh, estimated at 70 hours, with 2 rounds of revisions. Since kickoff on 8/4 they've had a fourth logo round (5 hours), merch mockups (a day and a half) and a template pack (6 hours), all done. Open now: a pitch deck (2 days) and a holiday label (10 hours). What's wrong or missing?

## 3. The questions

Ask only what is still missing. First run: at most five questions, in at most two messages. Return run: at most one. If a multiple-choice tool is available, use it (four questions per call at most, real options, a free-text escape). Otherwise number them and say "Answer like 1, 2b, 3a, or say skip."

1. **The money and the hours.** "What does this client pay, before any sales tax, and how many hours did you plan for it a month (or for the whole project)?" Fold in only what you could not read: the currency ("in which currency?"), the country if nothing says it ("and which country do you work from?"), and, when hours came in days, "How many hours is your working day? I'll count 8 unless you say." No default for the fee or hours: without them there is no rate, so the kit shows hours only and flags [NEED].
2. **How you want to handle extras.** "From now on, do you want to (a) price every extra, (b) give a small goodwill allowance each month (how many hours?), then price anything beyond it, or (c) only swap extras for something already in the plan? I'll price extras at the rate your fee works out at, unless you give me another rate." Default (a). An allowance is a promise to the client and only ever the founder's choice. Do not state the rate here: the hours may not be settled yet, and the figure comes from `compute`, in the defaults line.
3. **The relationship.** "How is the relationship right now: (a) strong, (b) a bit fragile, (c) about to renew?" Default (a).
4. **Your voice.** "Paste one message you've sent this client, so the replies sound like you. Or skip." Default: plain, warm English that reads naturally to an American or a British client.
5. **What was agreed.** Ask only if no proposal or list was pasted (a quote exported as CSV, in any language, counts as pasted): "What did you agree to deliver, with quantities (for example 12 posts a month, two rounds of changes)? Paste the proposal if you have it." For an unclear request, fold it in: "Was the newsletter part of that?"

A date that could be either way round (10/3) when nothing else shows the founder's order goes into the readback as a question ("Is 10/3 the 10th of March or October 3?"), not a sixth question.

If the founder answers only some, use the defaults and say which ones in one line.

If an answer reads two ways, or refers to options the founder never saw (a bare "b"), do not choose. Show both readings, say which one the provisional draft uses and what would change under the other, and ask.

## 4. Defaults said out loud

After the first `compute`, one line: "I'll price extras at £95 an hour, the rate your fee works out at, and assume two rounds of changes per deliverable, unless you say otherwise." Mention an allowance only when the founder chose one. The rate is the one `compute` printed, never one worked out in prose. Add "and count a working day as 8 hours" only when hours came in days and the founder did not give their day.

## 4a. When compute asks or checks

- **ASK** lines: a figure that can be read two ways ("12.500 €" from a founder whose style is not yet known: twelve thousand five hundred, or twelve and a half?) or not at all ("10 parsecs"). Put each to the founder as one plain question, in the readback if it is the first turn. Write the answer into kit.json in their words. Never pick a reading.
- **CHECK** lines: a headline figure that looks misread (an hourly rate under 10, a 30-hour working day). Nothing is built. Ask the plain question the line gives. If the founder confirms, add the key to `confirmed`.

Neither counts against the five questions when it replaces one already asked; if a sixth question would be needed, use the defaults for the least important open question instead.

## 5. Return runs

The memory file holds the offers, fees, planned hours, rates, the out list per offer, the founder's policy, currency, date order, working day, price wording, voice notes and the clients seen before. The one question is: "Which client, and what did they ask for?" Skip it if the opening message says. A new fee or new hours change only those fields. Apply every active learning at the step it names.

## 6. Stop cases

Stop and say why in one line, then offer what the skill can do:

- The founder wants to bill a client for past extras, or wants a demand or legal letter: that is a matter for a lawyer. Offer the forward-looking kit and the reset note.
- The founder wants a contract written or checked, or asks what a law lets them charge, claim or refuse: the skill writes a draft scope for a lawyer to work from, nothing more, and never says what a law requires.
- The "client" is an employer or the founder is an employee being given more work: outside this skill (employment, not service scope).
- There is no offer to scope (the founder has not sold anything yet): the skill needs an offer; ask what they plan to sell and at what price.
