# Lookup protocol

How to find and read the client's public record, with web tools or from a paste. Both paths produce the same brief. Scripts never go online; only Claude's own search and fetch tools do, and only when the session has them.

## Contents
1. What may and may not be looked up
2. With web tools
3. Matching: is this record about the client?
4. Without web tools, or when a register needs a form: the lookup card
5. Logging a source
6. What was found in testing

## 1. What may and may not be looked up

May: the client business's entry on its country's official company or business register; the official notices source for insolvency, winding-up or administration in that country; public judgment registers where the country publishes them; review sites and forums naming the business for non-payment; the client's own website.

Never: a named person (the owner, a director, a contact), their home address, personal finances, personal credit files or social media. Officer names appear only as the register page shows them, as appointment facts, and are never searched further. For a sole trader or individual: only what they publish as a business (their website, a business listing), and a business registration or tax number only if it appears on their own paperwork, checked for active or not on the public business register.

## 2. With web tools

1. Search `"<legal name>" company register <country> status`. Prefer the official register (a government domain or the register's own site) to an aggregator. If only an aggregator is readable, use it and name it.
2. Open the register page. Read and copy, in the page's words: legal name, registration number, status, date registered, filings due and overdue (accounts, annual returns), officers and any appointments or resignations in the last 12 months, registered address and when it changed, charges or liens if shown, and any insolvency marker.
3. Search `"<legal name>" <registration number> insolvency OR winding up OR administration notice <country>` and open the official notices source if one appears.
4. Where the country publishes judgments, search the same way.
5. Search `"<legal name>" late payment OR not paid OR unpaid invoice` for reviews and forum posts; count only independent sources that name this entity.
6. Open the client's website if the founder gave one: does the business name, address or domain match the register?

A search that does not surface the business is not "no register entry": R1 needs the register's own search showing no result for the exact legal name. If the founder pasted an extract, it stands; never replace it with a search that found nothing. A general web search that returns nothing is not a check of the notices source: only an official notices page you opened, or the founder's pasted result, clears it; otherwise it goes under "could not check".

Stop at a status that decides the verdict (for example "dissolved", "struck off", "forfeited", "in liquidation"): further checks will not change a Stop, and the reason not checked says so.

## 3. Matching: is this record about the client?

A record counts only when it is about the contracting entity:

- The name matches the register entry exactly (punctuation and "Ltd"/"Limited" aside), and the registration number or registered address matches where the record shows one.
- Search results for big brands return many related entities (group companies, old names, overseas branches). Use the one named on the contract.
- A notice found by search that names a different entity is set aside, and the chat says so in one line. In testing, a search for a well-known UK company returned a winding-up petition notice for an unrelated company with a similar word in its name; reading it as the client's would have been a false and damaging finding.
- A petition, application or proposal is not an outcome: quote the notice type and date exactly as published.

## 4. The lookup card (paste fallback)

When there are no web tools, or the register needs a form, a login or a paid account, give the founder this card, filled with the client's name and country:

> 1. Search for "<legal name> company register <country>" and open the official register (usually a government site).
> 2. Find <legal name>. Copy and paste back: the status, the date it was registered, whether any filings or accounts are overdue, any officer changes in the last year, the registered address, and any charges, liens or insolvency notes on the page.
> 3. Search the official insolvency or notices source for <country> for the name. Paste anything found, or say "nothing found".
> 4. Search "<legal name> not paid" and paste anything that names them.
> About ten minutes. Paste the text as it appears, in any language; I'll read it.

Pasted register text counts as a verified source dated the day it was pasted ("Register extract you pasted, 2 November 2026"). Read it in its own language, quote it in its own words and translate in brackets.

## 5. Logging a source

Each source in `case.json` has an id, the page title (or "Register extract you pasted"), its kind (register, aggregator, notices, judgments, reviews, website), how it was read (fetched or pasted) and the date. Each block not checked carries a plain reason: no web tools in this session; the register needs a form or login; not published in this country; a sole trader has no company register entry; not needed once the status decided the verdict.

## 6. What was found in testing (2 November 2026)

| Country | Source | Readable by a fetch tool? |
|---|---|---|
| United Kingdom | Official company register, company overview page | Yes: status, date registered, accounts and confirmation statement due dates |
| Australia | Official business number register, current details page | Yes: entity name, status and date, entity type |
| United States (North Carolina) | Secretary of State business registration page | Yes: legal name, status, date formed, registered agent |
| Germany | A commercial register aggregator | No: the site returned an error |
| Global | An open company data aggregator, search page | No: the request was refused in that session |
| United Kingdom | Official notices source, notice page | Yes, but the search hit was about a different company (see section 3) |

Registers that need a form or login are common, and US records are kept state by state. Treat the lookup card as an equal path, not a fallback of last resort.
