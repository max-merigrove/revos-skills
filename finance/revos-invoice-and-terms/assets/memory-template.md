# Invoice and Terms Builder memory

Skill: revos-invoice-and-terms | Memory version: 1 | Updated: YYYY-MM-DD

Keep this file private: it holds your payment details. Attach it next time (or leave it in your merigrove-memory folder, or your Claude Project) and the next invoice carries on from the last. You can edit it by hand.

`scripts/memory.py write` fills this in; `scripts/memory.py read` reads it back. Lists are separated by " / ".

## Profile

| Field | Value | Source | Updated |
|---|---|---|---|
| Business name | | you said | |
| Address | line / line | you said | |
| Email | | you said | |
| Tax number label | the founder's words, e.g. VAT number, GSTIN | you said | |
| Tax number | | you said | |
| Country | ISO code | you said | |
| Invoice language | en | you said | |
| Your English | e.g. en-GB, en-US | you said | |
| Currency | ISO code | you said | |
| How you write numbers | dot or comma | you said | |
| Date style | e.g. d MMMM yyyy | you said | |
| Last invoice number | | this run | |
| Usual terms | days, eom_plus, end_next_month, on_receipt | you said | |
| Usual terms, days | | you said | |
| Tax charged | yes or no | you said | |
| Late fee | none, agreed or new | you said | |
| Late fee clause (verbatim) | only from your own agreed terms | you said | |
| Late fee agreed in | document and date | you said | |

## Payment details

Read back to you on every run before they are printed.

| Field | Value | Updated |
|---|---|---|

## Tax setup (supplied by you)

From you and your accountant; this skill never sets a rate.

| Id | Label | Rate | Default | Supplied on |
|---|---|---|---|---|

## Clients

| Client | Address | Contact | Email | Tax number label | Tax number | PO needed | PO or reference | Their usual payment days | Notes |
|---|---|---|---|---|---|---|---|---|---|

## Billing plans

| Plan | Client | Name | Currency | Project total | Stage | Label | Share | Trigger | Stage total | Number | Issue date | Status | Paid date | Tax on this stage |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

## Project lines

| Plan | Description | Qty | Unit | Unit price | Tax | Stage |
|---|---|---|---|---|---|---|

## Documents

| Number | Type | Client | Project | Issue date | Due date | Currency | Net | Tax | Total | Paid | Status | Paid date | PO | File |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

## Gaps and voids

| Number | Reason | Date |
|---|---|---|

## Learnings

| # | Learning | Evidence | Applies to step | Status | Added |
|---|---|---|---|---|---|

Status: watch (seen once), active (approved or repeated), retired (kept for the record, no longer applied).

## History

| Date | Made | Option chosen | Verdict |
|---|---|---|---|
