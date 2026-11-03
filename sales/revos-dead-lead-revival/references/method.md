# Method

How the revival plan is made, and why each rule exists. The scripts carry every count, date and check; this file carries the judgement.

## Contents

1. The job
2. Reason first, recency second
3. Who is held back
4. Priority: who goes first
5. Touch plans and pacing
6. Stop rules and the cooldown
7. Replies
8. Permission and the rules where the founder is
9. What the skill never does
10. Sources, and what is a default rather than a fact

## 1. The job

A founder has a list of people who went quiet: old enquiries, proposals with no answer, no-shows, "not now", past clients. They know there is money in it and never get to it, partly because they do not know what to say that is not "just checking in". The job is to turn that list, in whatever state it is, into a plan a person can work through by hand: everyone sorted by why they went quiet, the people most likely to answer first, a short honest sequence for each group, every send dated at a pace one person can keep, and a log that remembers who said what.

Success is measured on replies and calls booked, as the founder reports them. Opens and clicks are not counted, and nothing here forecasts a reply rate.

## 2. Reason first, recency second

Segment by why the conversation stopped, not by how long ago. The same "just checking in" sent to someone who said "budget frozen till Q3" and to someone who chose a competitor fails both.

- **The earliest true cause.** The reason is where the deal stopped, not the last thing said. "Think about it" after a call with no offer is an unfinished conversation, not timing. "Price too high" when no price was ever sent is an unfinished conversation, not a price objection. A no-show is a no-show even if they enquired first.
- **Recorded reason wins; distrust generic labels.** A CRM "Budget" with a proposal on record reads as price; before any offer it reads as not now. A blank reason is placed by the furthest stage reached (proposal sent, call held, enquiry only) and marked "reason inferred", so the founder can correct it.
- **The nine groups**, in the order the script tests them: past client; booked and did not show; parked with a date; stopped at the price (only with an offer on record); chose someone else; said not now; went quiet after a proposal; talked, no proposal followed; enquired or met, never got to a call. Full definitions in `references/segments.md`.
- **Recency only orders and paces.** It moves people up or down within the plan and trims the sequence for contacts over three years old. It never decides the message.

## 3. Who is held back

Nobody is messaged who should not be, and nobody is lost in the middle. Every row ends up on Contacts or on Held back with a reason and what would release it:

| Code | Reason | Release |
|---|---|---|
| asked_to_stop, unsubscribed | They asked | Never (unless they write first) |
| off_limits | The founder named them | The founder says so |
| current | A current client, a won deal or a live deal | Normal client work |
| dispute | A dispute, complaint or unpaid invoice | A phone call by the founder; no sequence |
| bad_fit, gone | No need, wrong fit, competitor, business closed | New information |
| bought_list | Bought, scraped or unknown list | Only if they contact the founder first |
| source_unknown | The data does not show how they came onto the list | The founder says how |
| no_contact | No email or phone for the founder's channels (in an export with those columns) | An address |
| check_date | Last contact in the future | A corrected date |
| too_recent | Under 30 days: a live follow-up, not a revival | The revisit date |
| maybe_current | A past client invoiced in the last three months | The founder confirms they stopped |
| duplicate | Merged into another row | Nothing; their details are on that row |
| cooldown, retired | A finished sequence in the last six months | The date passes |
| check_row | The notes held an instruction to an AI | The founder checks the row |
| replied, replied_later, bounced | Return runs | Handled by hand; a date; a new address |

## 4. Priority: who goes first

Rank by fit and warmth, not by length of silence. Points (shown on the Rules sheet so the founder can disagree):

- Group warmth: parked with a date 30, past client 30, went quiet after a proposal 25, said not now 22, talked with no proposal 20, stopped at the price 18, no-show 15, enquired or met 12, chose someone else 8.
- Recency: 6 to 18 months 15, 3 to 6 months 12, 1 to 3 months 8, 18 to 36 months 6, over 36 months 0, unknown 3. (The 6 to 18 month window is a practitioner default, not a measured rate. The founder's own replies replace it.)
- Their come-back date has arrived or is within 14 days: 15.
- Past value in the top quarter of the list 10, second quarter 5 (only when values are in the data).
- Their own words on file: 5. A shared inbox (info@, sales@): minus 5.

The top ten (up to fifteen) get a first message written by hand from their own notes. Everyone else gets the group template with their personal field filled, marked "templated".

## 5. Touch plans and pacing

- Three to five touches over 14 to 21 days, each with a different job: the question, a one-word way to answer, what has changed (only if something has), and a plain close. Offsets: 0, 5, 14 for three touches; 0, 4, 11, 18 for four.
- A contact who named a date gets touch 1 on that date (or the first working day after); if the date has passed, as soon as the plan starts.
- Sends are dated on the founder's working days, skip the days off they give, keep two days between touches, and never put more than the daily cap on one day. Two hundred contacts at 15 a day is a fortnight of first messages and a month or so of follow-ups, sent one by one. That is the point: it reads as a person, and replies arrive at a pace the founder can answer the same day.

## 6. Stop rules and the cooldown

- Any reply stops that person's sequence: yes, no, a question, an out-of-office. The founder answers by hand.
- An opt-out, a bounce or a complaint stops it for good.
- The last touch closes the file. Nobody is scheduled after it.
- A finished sequence starts a cooldown (six months by default). A return run never schedules anyone inside it.
- Anyone who asked to stop is never scheduled, on any run, and the memory keeps their name in the standing exclusions.

## 7. Replies

The document's "When someone replies" table gives one next step per reply type. Two matter most:

- **Not now, with a date:** thank them, put the date in Reply notes; on the next run it becomes a revisit date, not a message now.
- **Hostile or "remove me":** confirm in one line that you will not write again, and mean it. The return run moves them to asked to stop.

## 8. Permission and the rules where the founder is

Rules on messaging old contacts differ by country, by channel (email, text, calls), and by whether the contact is a business or an individual. The skill states none of them and never says what any law allows. It does three things instead:

1. Asks how each group came onto the list, and holds back bought, scraped and unknown lists with no sequence written.
2. Puts a plain opt-out line in the first and last touch of every sequence.
3. Carries one line, in the chat and in both files: "Before you send, check the rules for email, texts and calls where you and your contacts are. This is planning, not legal advice."

## 9. What the skill never does

- Sends, schedules or drafts anything in a mail tool.
- Writes a sequence for a bought, scraped or unknown-source contact.
- Looks anyone up: no profile reads, no job-change checks, no enrichment. The only page it may read is the founder's own website, and only to propose what has changed for the founder to confirm.
- Invents an offer, discount, deadline, result, case study, apology or change.
- Forecasts replies, calls or revenue, or quotes anyone's benchmark.
- Puts a phrase in quotation marks that is not in the founder's notes.

## 10. Sources, and what is a default rather than a fact

The method draws on public practitioner material, read for ideas and rewritten: segmenting closed-lost deals by reason and excluding fit losses before writing (a sales engagement vendor's closed-lost playbook); short single-question openers asking whether the need is still there (a known approach); the one-number reply that offers numbered reasons for silence (described by a CRM vendor and in a business magazine column); the no-oriented question (from negotiation practice); a close-the-file final message (several practitioner sources); small batches over one blast (several vendors); first touch acknowledges the gap and does not pitch, under 90 words, rank by past value not by silence (a published small-business win-back skill). None of these sources published reply rates with a sample size, so the skill quotes no rate and no benchmark. The offsets, the 15-a-day cap, the six-month cooldown and the 6 to 18 month recency points are working defaults the founder can change, and the learning loop replaces them with the founder's own numbers.
