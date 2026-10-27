# Intake guide: from what the founder pastes to the inputs file

Contents: 1 The inputs file. 2 Locale. 3 Reading messy input. 4 Mapping what founders say. 5 The readback. 6 Catching what looks wrong.

## 1. The inputs file

Start from `python3 scripts/chase_plan.py template`. Every field the founder did not give stays `null`; never fill a plausible value.

| Field | What goes in | Notes |
|---|---|---|
| `business` | The founder's business name | Used in the file name |
| `founder_name` | How they sign emails | From a pasted email if possible; otherwise the messages carry `[NEED: your name]` |
| `greeting` | Their greeting word, such as "Hey" or "Hi" | From a pasted email. Used with the contact's first name, or alone when there is none ("Hey,") |
| `date` | Today, `YYYY-MM-DD` | |
| `country` | Two-letter code where the founder is based: US, NZ, DE, IN, JP | Sets date order and page size. From their address, currency or what they say; never from spelling |
| `locale` | Their English: `en-US`, `en-GB`, `en-AU`, `en-NZ`, `en-CA`, `en-IN` | From how they write. Sets spelling only ("installment", "authorize") |
| `currency` | Three-letter code: USD, AUD, GBP, EUR, INR, JPY | Section 2. Unknown stays `null`; a symbol that names one currency (£, €, ₹) is read, a bare $ is asked |
| `decimal_style` | `dot` (1,200.50) or `comma` (1.200,50) | Leave `null`: the script reads it once from the figures pasted. Set it only after asking about a figure that reads two ways |
| `date_order` | `MDY`, `DMY` or `YMD`, only if the country is unknown and the founder said | Normally from `country` |
| `weekend` or `work_days` | Days off ("Fri and Sat"), or the days they work ("Sun to Thu") | Leave `null` unless they said; default Saturday and Sunday, said out loud |
| `holidays` | Dates the founder gives | Never filled from any country's calendar. With none, the plan lists its dates in the next 8 weeks for the founder to check |
| `confirmed` | Keys from a "please check" STOP the founder confirmed, such as `"amount:1042"` | Only after the founder says the figure is right |
| `default_terms` | Their usual terms, as typed | |
| `own_late_terms` | `{"has": true, "rate": "1.5% a month", "fee": "$50", "grace_days": 10, "clause": "..."}` | Only when their contract sets a late fee or interest |
| `plan` | `{"instalments": 3, "every": "month", "min_amount": null}` | Leave `null` unless they said. `min_amount`: below it, stage 3 offers a call and no plan |
| `prevention` | `{"deposit_pct": 50, "milestones": "40/30/30", "card_on_file": true, "late_fee": null, "typical_price": null}` | Leave `null` unless they said; defaults said out loud |
| `bank_line` | false only if the founder asks to drop the bank details line | It appears in the first message and the final notice |
| `clients[]` | One per client | |
| `.name`, `.contact`, `.to` | Client name, contact's name, the address to send to | A learning such as "only answers via accounts@" sets `.to` |
| `.is_business` | false for a private individual | Default true |
| `.tier` | `valued`, `normal`, `persistent` | Section 4 |
| `.charge_late_fee` | false if the founder will not charge this client their contract fee | |
| `.ongoing_work` | true if the founder is still doing work for them | Makes "stop work" a real option |
| `.asked_for_plan` | true if the client has asked to pay in parts | The first message is then the stage 3 plan offer |
| `.final_action` | `advice`, `pause`, `collections`, `lawyer` | Only what the founder will do |
| `.stages_sent` | `[{"stage": 1, "date": "2026-09-20"}]` | A polite nudge is 1, a chase with a pay-by date is 2, an offer of a call or plan (or a late fee notice) is 3, a final notice is 4, a message about a dispute is 0. Rough dates work ("3 weeks ago") |
| `.invoices[]` | `number`, `amount`, `invoice_date`, `due_date`, `terms`, `payments` (`[{"date","amount"}]`), `paid_in_full_on`, `disputed`, `disputed_amount`, `total_shown` | Type figures and dates as the founder gave them; the script reads them |
| `.disputed_amount` | The part of the invoice the client disputes | The rest is chased; the first message offers to settle this part. `disputed: true` with no amount holds the whole invoice and flags it |
| `.total_shown` | The total printed on the copy the client has, when it is wrong | The first message corrects it and says a corrected invoice is attached |
| `.line_items` | The line amounts on a pasted or photographed invoice, as typed (`["4,217.39", "632.61"]`) | The script adds them and flags a total that does not match, or says which figure looks like the typo |
| `report_total` (top level) | The grand total on a pasted aged receivables report | The script flags it when the open invoices do not add up to it |
| `.approval`, `.approval_date` | What the client said when they signed off the work, in the founder's words ("approved, looks great"), and when | Messages from stage 2 quote it. Never paraphrase it into something stronger; leave it out if the founder did not say it |
| `.held_until_paid` | What the founder's agreement holds until payment, as a noun phrase ("the final files", "the licence to use the footage") | Every message says it will follow once the invoice is paid in full, as their agreement sets out. Only what the founder said their agreement says |
| `.gap_days`, `.final_after_days` (client or top level) | The founder's own spacing: days between messages, and days from the first message to the final notice | Overrides the defaults. Without it: 14 and 28 for a client to keep, 7 and 14 for the rest, and always at least 14 days from a plan offer to a final notice |

A flat `invoices` list with a `client` field on each also works; the script groups it.

## 2. Locale

Never assume a country. Keep three things apart:

- **Country** (`country`): where the founder is based. It sets date order and page size. Read it from what they say ("we're in Auckland"), an address, a company suffix (Pty Ltd, GmbH) or the currency. Never from spelling: a Briton in New York uses US dates and Letter paper.
- **Their English** (`locale`): from how they write ("color", "organise"). It sets spelling only.
- **Number style** (`decimal_style`): read once by the script from the figures they pasted (1,200.50 or 1.200,50). If a figure reads two ways (12.500), the script asks; put that one question to the founder.

Currency: a symbol that names one currency (£, €, ₹, A$, S$) is enough; a bare $ is not. Dates: a day over 12 in the first position (25/08) means day first. If two signs agree, use them and say so in the readback ("I'll use Australian dollars and day-first dates"). If not, ask once inside question 2. Founder-facing text mirrors the founder's English and writes figures in their style.

## 3. Reading messy input

The script reads these as written. Do not convert them yourself.

- Money (read by `scripts/locale_numbers.py` in the founder's number style): "$2,400", "2400.00", "$2.4k", "1.2K", "A$12.5k", "US$900", "£850", "2.400,00 €", "15 000 €", "1'234.50", "₹2.4 lakh", "18,00,000", "450万", "2,400 inc GST", "=1200*2". "$2,000 + GST" or "ex VAT" stops that invoice with a `[NEED]`: ask for the total on the invoice the client was sent. A rough figure ("about 3k", "like 2k") is a `[NEED]`: messages carry exact amounts.
- Dates: "3 Aug", "Aug 3", "3rd August 2026", "08/03/2026", "3/8/26", "3.8.26", "2026-08-03", "today", "yesterday", "6 weeks ago", "a month ago", "last Friday", "the 2nd of this month". A date with no year takes the most recent one (invoice dates) or the nearest one (due dates). "Early September" is not a date: ask, or use the first of the month and say so.
- Terms: "30", "30 days", "net 30", "14d", "2 weeks", "a month", "end of month", "EOM", "30 days EOM", "end of the following month", "on receipt", "due on completion", "30 Tage", "30 días".
- Contract late terms: "1.5% a month", "2% pm", "1,5 % pro Monat", "10% a year", "18% APR", "$50 late fee", "5% of the invoice". Grace periods: "10 days", "2 weeks". "Prime plus 2" or "4% over base" asks: what total yearly rate should I use? Ask your accountant or bank. A bare "5%" asks: once, a month or a year?
- Days off: "Sat and Sun", "Fri-Sat", or working days "Sun to Thu" in `work_days`.
- Headline figures that look wrong stop the run with a plain question ("please check"): an amount under one unit of currency, a rate over 100% a year, an invoice over three years old, a late fee bigger than the invoice. Ask; if the founder confirms, add the key to `confirmed`.
- From a screenshot or an accounting export: one row per invoice; use the invoice total, not a "due" column that shows only part.

## 4. Mapping what founders say

| Founder says | Input |
|---|---|
| "great client", "don't want to lose them", "keep at all costs", "biggest client" | `tier: valued` |
| "always late", "every single month", "this is the third time" | `tier: persistent` |
| "a homeowner", "a private client", "a lady whose kitchen I did" | `is_business: false` |
| "a sole trader", "a one-man band", "a freelancer", "an LLC", "a Pty Ltd" | `is_business: true` |
| "they say the work wasn't right", "they're disputing it", "they're holding it" | `disputed: true`; ask whether it is all of it or how much |
| "they won't pay that part", "they're disputing $2,250 of it", "the second cut, about 2k" | `disputed_amount` (the exact figure; a rough one is asked) |
| "the invoice says $4,580 but it should be $4,850", "the total line was a typo" | `amount` is the right total, `total_shown` the wrong one they have |
| "ghosted, nothing in 3 weeks", "I've chased once" | ask once: "When did you last write to them?" and map to `stages_sent` |
| "they paid half", "$500 came in on the 2nd" | `payments`; with several open invoices and no say which, set it against the oldest and say so out loud |
| "they paid last week" | `paid_in_full_on` |
| "I've emailed twice" | two `stages_sent` rows, stages 1 and 2, with dates if known ("3 weeks ago" works); otherwise ask once for the last date |
| "we work Sunday to Thursday", "we're off Fridays" | `work_days` or `weekend` |
| "the 25th is a holiday here", "I'm away 1 to 5 December" | `holidays` |
| "don't offer a plan on anything under $2k" | `plan.min_amount` |
| "I'll stop work", "I'd pause the retainer" | `final_action: pause`, `ongoing_work: true` |
| "I'd send it to a collections agency" | `final_action: collections` |
| "my lawyer would handle it" | `final_action: lawyer` |
| "they asked if they can split it", "can they pay monthly" | `asked_for_plan: true` |
| "I don't want to charge them the late fee" | `charge_late_fee: false` |
| "my contract says 1.5% a month" | `own_late_terms.has: true, rate: "1.5% a month"` |
| "what interest does the law let me charge?" | Not an input. Say the skill does not give legal advice; it applies only a rate their own contract sets, and their lawyer can say what they may charge |

## 5. The readback

When you pulled figures out of a paste, read them back in one short block in the same message as any questions, and ask "What's wrong or missing?":

"I read: Harbour Dental, FS-104, £2,400, invoiced 3 August, no terms so 30 days; Kettle & Co, FS-110, £850, 14 day terms from 1 September; Greyline, two invoices (£12,500 and £1,200) and you've chased twice. Pounds, UK, day-first dates."

If the paste carries a total (an aged receivables export), put it in `report_total` and say whether the invoices add up to it, and name any gap ("$29,500.00 in all, $2,250.00 of it disputed").

## 6. Catching what looks wrong

A sharp bookkeeper reads the founder's material for what does not fit and says so in the first reply, before anything goes to a client. Check every run for:

- **Totals that do not reconcile:** a report total against its invoices (`report_total`), invoice lines against the invoice total (`line_items`), a figure in the message against the figure on the invoice ("4850" said, "$4,580.00" printed). Say which figure the evidence backs ("the lines add up to $4,850.00, so the total line looks like the typo") and what you used; never choose silently.
- **Terms against the evidence:** "net 15 i think" against the report's own ageing bucket; terms in the message against terms printed on the invoice.
- **Dates:** a due date or invoice date in the future, a date on the founder's day off, a date typed in the other order.
- **Status:** an invoice the founder says was paid but is in the list; a part payment with no invoice named; a client marked "still working for them" with a final notice planned.
- **People:** the same contact name at two clients (a mix-up, or two different people: ask before anything goes out); a contact who is a receptionist or front desk rather than the person who pays (the first message then asks who handles payments).
- **Leverage left unused:** the founder mentions files not delivered, a signed approval or a booked job, and none of it is in the messages.

Each finding is one line in the "I read" block. Where a script figure is needed (a sum, a difference), get it from the script, never from your head.
