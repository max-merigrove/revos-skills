# Client data: what is removed, what is kept, what is saved

Proposals, decks and onboarding emails carry other people's data: client names, contact names, fees, email addresses, phone numbers, addresses. None of it is needed to judge consistency, so none of it is read, shown or saved.

## Before reading

`scripts/redact.py` runs on every asset before anything else and writes clean copies:

| Removed | Where | Becomes |
|---|---|---|
| People passed with `--person` (every client, contact and testimonial person, as written, in any script), and each of their names alone | every asset | `[client]` |
| Companies and brands passed with `--client`, as written | every asset | `[client]` |
| Names it finds itself: after a greeting in many languages (Dear, Hi, Kia ora, Salam, Hola ...) with or without a title (Mr, Dr, Datuk, Dato', Herr, Shri ...); after "Prepared for", "Proposal for", "Attn:", "cc:", "Client:"; on a testimonial dash line; and companies by legal form anywhere: Ltd, Inc, LLC, Corp, Co., PLLC, Pte. Ltd., Pty Ltd, Pvt. Ltd., Sdn Bhd, GmbH, AG, S.A., SARL, S.r.l., B.V., AB, Oy, K.K., Ltda., FZ-LLC, and PT, CV or OOO before the name | every asset | `[client]` |
| Text passed with `--address` (an address or number in a shape the patterns do not know) | every asset | `[address]` |
| Email addresses; phone numbers in any country format, and short ones after Tel, Mobile, HP or WhatsApp | every asset | `[email]`, `[phone]` |
| Street addresses (house number and street, Jalan, Blk, Straße, rue, Calle, unit numbers such as #20-01) and postal codes (UK, US ZIP after a state, Canada, Australia after a state, Singapore, Japan with the postal mark, a labelled PIN, ZIP or postcode) | every asset | `[address]`, `[postal code]` |
| Bank and registration numbers: any IBAN, and anything labelled routing, account, BSB, sort code, SWIFT, IFSC, EIN, ABN, UEN, GSTIN, VAT or GST number, company number | every asset | `[bank details]` |
| Fees and amounts in any currency (symbol or code, before or after the number, with or without a sales tax tail) | client-facing assets only | `[fee]` |

The founder's own name and business are never removed (`--keep` for anyone else on their side). Public prices on the website stay: they are the founder's own published claims.

Names are matched in any script: accented Latin, Vietnamese, Cyrillic, Greek, Arabic, Devanagari, Thai, Chinese, Japanese and Korean. Two-letter family names (Ng, Le, Wu) are removed alone only when written with a capital, and never when they are also English words.

It also removes, by itself: a company's first word on its own when the company was found or given ("Acme's operations team" after "Acme Logistics Inc."), matched as written and only when the founder's copy never uses that word in lower case; and the company on a testimonial line ("- Daniel Okafor, VP Engineering, Brightline Freight": the last field, when it is not a job title).

The founder's own contact and payment details (a line holding their business name, or an email at their own domain) are removed too, but counted as theirs: the founder hears "your own contact and payment details were left out of the reading", never that they were client data. Counts are of distinct client names, with mentions in brackets ("4 client names (7 mentions)"). If client names would take out a large share of an asset (over 40%, or 20% of a long one), redact.py stops: a name has matched ordinary words.

The automatic detection is a backstop, not the method. Read every client-facing asset once yourself and pass every name you see with `--client`. A NOTE appears when a client-facing asset had no names found; read it by eye before going on.

`--delete-raw` deletes the raw pasted copies once the clean ones exist. Work only from the clean copies from then on.

## What redaction.json holds

Counts per asset, and one-way fingerprints (SHA-256) of the removed names. Never the names. The fingerprints let `build_report.py` and `check_memory.py` prove that no removed name reached a report or the memory file, without storing the name anywhere.

## Before writing

- `build_report.py` refuses to write if either output holds an email address, phone number, postal code, street address, bank or registration number, a removed name, or an amount that is not on a public asset.
- `check_memory.py write` refuses to write if the memory would hold any of those, or any amount at all (public prices in saved quotes are stored as `[price]`).

## Testimonials and client results

Using a client's name, words or result in public is covered by rules that differ by country and by platform. The scan gives no view on them. When an edit would add a client's name, result or quote, it becomes `[NEED: a client result you have permission to publish]` and the chat summary carries one line: "Check the rules on using client names and testimonials where you and your clients are."

## What the founder is told

One line before reading ("I took out 3 client names, 2 fees and an email before reading"), and one line in the report footer. If the founder asks to save a client's details, a fee or a deal for next time, decline in one line: the scan keeps only what is needed to compare their own messaging, and a CRM is the right home for client records.
