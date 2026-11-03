# Signal catalogue

Every signal the verdict reads. Severities: **stop** (verified alone decides Stop), **major** (decides Caution), **minor** (two or more decide Caution), **context** (shown, never decides). Thresholds are working defaults, set in `scripts/signals.py`, shown in every brief and never presented as benchmarks.

Confidence: **verified** (a register, notices or website page read, or register text the founder pasted, with title and date); **public report** (reviews and forums); **founder reported** (the founder's own observation); **unverified** (said but not seen anywhere). Only verified signals can decide Stop; a stop signal from a public report counts as major. Unverified claims become questions, never findings: the brief shows them as "You were told, not seen" under their own label, never under a signal's name. A claim that a register in hand contradicts is not unverified: it is R14, verified.

## Register and public signals

| Id | Signal | Where to see it | Severity | Why it matters | How to word it |
|---|---|---|---|---|---|
| R1 | No register entry for the contracting entity, or the contract names a different business from the register entry | Official register (its own search, not a web search that found nothing) | stop (when the client says it is incorporated and the register was reachable) | You could be contracting with nobody | "The register shows no entry for '<name>' as at <date>" |
| R2 | Status not active (dissolved, struck off, forfeited, in liquidation or administration, or the local equivalent) | Register entry | stop | An entity in that state may not be able to pay or contract | "The register shows the status as '<words>' as at <date>" |
| R3 | Insolvency, winding-up or administration notice for this entity | Official notices source | stop | Payment may be frozen or never come | "<source> lists '<notice type>' dated <date>" |
| R4 | Public judgment or recorded unpaid debt | Judgment register, where published | major | Someone else already had to go to court to be paid | "<source> shows: '<words>'" |
| R5 | Filings overdue | Register due dates | major if more than one period overdue, else minor | Late filing often travels with late paying | Quote the due line |
| R6 | Registered in the last 12 months | Register date | minor | No filing history to read: no history, not bad history | "Registered <date>, <n> months ago: no filing history to read yet" |
| R7 | More than two officer changes in 12 months | Officers list | minor | Churn at the top makes promises harder to hold | "The register shows <n> officer changes in the last 12 months" |
| R8 | Registered address changed in 12 months, or a filing agent's or virtual address only | Register and filing history | minor | Harder to find the business if it goes quiet | Quote the page |
| R9 | Outstanding secured charges or liens | Charges section, where published | context | Common with any bank loan; someone else ranks first | "<n> outstanding charge(s); context, not a finding" |
| R10 | Public reports of non-payment naming this entity | Review sites and forums | major at 3 or more independent sources, minor at 1 or 2 | A pattern is information; one angry review is not | "<n> independent reports of non-payment (<sources>)" |
| R11 | Officers linked to entities dissolved or insolvent in 24 months | Register's own appointment pages only | major at 2 or more, context at 1 | Repeated failures behind the same people | Quote the register |
| R12 | Small or micro accounts only | Filing history | context | They reveal little | "Only small or micro accounts are filed" |
| R13 | Website, domain or contact details do not match the entity | Client's website | minor | The business you met may not be the one signing | Say exactly what differs |
| R14 | A claim the register contradicts ("8 years in business" against a company formed last year) | The register in hand, against what the client or contract says | minor | A new entity may carry none of the old business's record, and the claim was wrong | "Told: '<claim>'. The register shows: <fact>" |
| R15 | The contract names the right business with a different legal form or a near spelling ("UG" for "GmbH", "Studio" for "Studios") | The register entry, against the contract | major, with a fix-before-signing line | The contract must name the entity that will pay, or there may be nobody to hold to it | "The contract names '<x>'; the register shows '<y>'". The brief and the first reply say: the contract must name <register name>, <number> |

## Founder-observed signals (confidence: founder reported)

| Id | Key in case.json | Signal | Severity | How to word it |
|---|---|---|---|---|
| F1 | `long_terms` | Asks for 60 days or more as a new client (added by the script from their terms) | minor | "<n> days to pay as a new client" |
| F2 | `refused_deposit` | Refuses or strongly resists a deposit that was asked for (a draft that simply offers none is not this) | major | In the founder's words |
| F3 | `start_before_contract` | Presses to start before a contract is signed | major | In the founder's words |
| F4 | `slow_to_sign` | Slow to sign the contract | minor | In the founder's words ("took 9 days to reply on the contract") |
| F5 | `free_work` | Asks for free samples, or offers exposure instead of pay | minor | In the founder's words |
| F6 | `budget_mismatch` | Budget does not fit the scope | minor | In the founder's words |
| F7 | `blames_previous` | Blames the previous supplier for the mess | context | In the founder's words |
| F8 | `client_defines_completion` | Pays only on a "completion" the client defines | minor | In the founder's words |
| F9 | `contact_mismatch` | Contact details informal or not agreeing (free-mail address, a different domain, a dead website) | minor | In the founder's words |

Founder signals are written in the founder's own plain words, summarised: never a client's message pasted whole, an email address or a phone number, because the brief may be shared. The brief's headline uses the signal names above, never the founder's text.

## The verdict rule

- **Stop:** a verified stop signal, or (return run only) the client has refused every rung of the terms.
- **Caution:** any major signal, or two or more minor signals (verified, public report and founder reported together), or the entity could not be verified and the peak unpaid work under the client's terms is above the founder's limit.
- **Go:** otherwise. It means only that no stop or major signal was found in what could be checked.

`brief.py` decides between R1 and R15 itself: it strips the legal form from both names (Ltd and Limited, Pvt Ltd and Private Limited count as the same), and a matching core or a near spelling is R15; anything else is R1. Version 1.0 made every mismatch R1, which gave a Stop for a typo in a lawyer's draft; a typo is fixed by correcting the contract, not by refusing the client.

Departure from the build brief: the brief listed "three or more verified R10 reports" under Stop, but reviews are public reports, and only verified signals may decide Stop. Three or more independent reports are therefore major (Caution), and the founder sees them in the evidence.
