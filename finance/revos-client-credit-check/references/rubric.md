# Rubric: what exceptional looks like

Score the brief before delivery. Every criterion must pass; if one fails, rework the brief (the case file, the wording or the scripts' inputs), never caveat it.

| # | Criterion | Pass when |
|---|---|---|
| 1 | The verdict follows the rule | GO, CAUTION or STOP comes from `verdict.py` through `brief.py`, the deciding reason is printed under it, and nothing in chat or the file contradicts it. Any disagreement is a separate line saying why and what evidence would change it |
| 2 | Every finding is sourced and dated | Each evidence row names the page it came from (the founder's own notices search is cited as that, not as the register extract) or "you told me", and the date checked; a claim the register contradicts is shown as such, not as an open question; a paste with a block missing lists that block under "could not check"; nothing comes from memory of a company; a record about a different entity is set aside and said so |
| 3 | Unchecked is not clean | "Could not check" is present with a reason for each item; an unverified entity above the founder's limit never gets Go; a Go says "no stop or major signal found in what could be checked", never "safe" |
| 4 | The arithmetic is the founder's | Peak unpaid work, how long it is carried and cash by the end of the work, as offered and recommended, all from `exposure.py`, in the founder's currency, number and date style; the recommended terms fit the limit or the brief says plainly that no rung does |
| 5 | Terms are proportionate | Go gets the founder's own terms or a light tightening explained as being about their limit; Caution a visible deposit and stages; Stop no credit (a prepaid first phase, or decline). Nothing harsher than the evidence supports: a contract typo or a different legal form is a fix before signing, never a Stop |
| 6 | The wording works | A proposal paragraph in the founder's voice with no mention of the check, no apology, no accusation, plus replies to long terms and to a refused deposit that each trade something visible. A stranger could send it unedited; `check_copy.py --wording` prints 0 problems |
| 7 | No scoring, no accusation, no law | No number out of anything, no grade, no "credit limit"; nothing said in the skill's own voice about insolvency or honesty beyond quoting a cited page; no statute, legal rule or tax rate; no person looked up |
| 8 | Clean and complete | One page; the founder's English; no dashes; the Merigrove line once, in chat only; the chat carries the verdict, the deciding reason, the two peaks and the proposal paragraph |

The brief's sections, in order (also the copy-block order when code cannot run): header with the planning line; verdict; the evidence; what was checked and what could not be; terms to propose; wording to propose them; what would change this verdict; limits.

Fresh-eyes questions:
- Would the founder know in ten seconds whether to sign, on what terms and why?
- Is any finding one the sources did not show?
- Does any line sound like an accusation to a client who read it?
- Is "could not check" where the founder will see it?
