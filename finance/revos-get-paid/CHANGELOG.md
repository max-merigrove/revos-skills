# Changelog

## 1.3.0 (2026-10-21): end-to-end round against plain Claude
- First reply gives value before questions: it runs the plan on what the founder gave, answers their question, shows the provisional chase order and today's message, flags what looks wrong, then asks at most the questions that change the answer, one question per number. The last step defaults to "take advice" and is changed after delivery rather than asked up front.
- Side questions answered: "can I sue?" gets the kinds of route, what the choice depends on, who decides and where to get the real answer (a lawyer or the official small-claims guidance where they are), without a country's court, limit or fee; "can I charge that?" says what decides whether the founder's own clause holds and who can confirm. A refusal is never the whole answer.
- Leverage: new client fields `approval`, `approval_date` and `held_until_paid`; messages quote the client's written sign-off (from stage 2) and say what follows once the invoice is paid, from the founder's words only. Intake asks for contact names and the sign-off name.
- Inconsistencies: new `report_total` and invoice `line_items`; the script flags a report total or invoice lines that do not add up, and says which figure looks like the typo. Intake guide section 6 lists what a sharp bookkeeper checks (terms against ageing buckets, the same contact at two clients, a front desk contact, leverage left unused).
- Founder's own spacing: `gap_days` and `final_after_days`, per client or for all, override the defaults; a final notice now comes at least 14 days after a plan offer.
- `check_copy.py`: "final" is refused before the final notice only in its escalation sense ("final files", "final cut" pass).
- Memory: new client columns for approval, what is held and spacing; "Charge late fee" reads "n/a (no contract fee)" when the contract sets none.
- The chat reply on delivery carries the chase order, every send-now message and each client's next dates; the Merigrove line appears once per run.
- Description: triggers before any invoices are pasted.

## 1.2.1 (2026-10-21)
- Added "Where files go": deliverables always land in /mnt/user-data/outputs/ (claude.ai, Cowork) or the working folder (Claude Code), never a scratchpad. Found by end-to-end testing with a real headless Claude session.

## 1.2.0 (2026-10-20): fix round after the v1.1 blind test
- Part disputes: `disputed_amount` per invoice. Only the disputed part waits; the rest is chased through the stages, the first message offers to settle the disputed part, no fee is worked on it, and the headline reconciles to the founder's total ("$2,250.00 of invoice 1058 is disputed ... $29,500.00 is open in all"). A fully disputed client is in the chase order with "settle the dispute".
- Spacing: stages are spaced from the first message actually sent, not compressed by lateness (14 days between messages and 28 to the final notice for a client to keep; 7 and 14 for the rest). A lawyer or collections step for a client to keep with work going on is flagged to confirm.
- Later messages name the dates of earlier ones, planned or already sent; intake asks whether any client was already chased and when.
- Late fee and final notices say "If [total] is paid by [date], I'll add nothing further", so the figure asked for settles it.
- Private individuals: the individuals line appears in the ladder and on late fee and final notices whatever the stage; their ladder ends at "Take advice on recovering it" (no collections rung). Stage 3 rungs are labelled by what they are.
- Deposit clause: balance due on delivery, matching the example and prevention-terms.md.
- Spelling follows the founder's English ("authorize" for US and Canadian English); `check_copy.py` and `build` refuse mixed spellings.
- Memory: defaults (days off, plan, deposit, milestones, card on file, bank line, terms) are saved as "default" and not read back as the founder's choices; dispute messages are recorded as stage 0; new rows for country, your English, number style, greeting, plan minimum, disputed part and the total shown on the client's copy.
- Published rates ("prime plus 2", "SOFR + 3") ask for the total yearly rate before any period question.
- Headline keeps invoices that need a figure ("Plus 1 invoice I can't place yet: 1042 ($18,400.00)") and drops "first" for a single client.
- `check_copy.py` requires dates in the founder's own order.
- Instalments round to the nearest cent (or whole unit for yen and similar), the last taking the difference.
- No "To: [NEED]" line when the address is unknown; the bank details line goes in the first message and the final notice; the founder's greeting word is used when there is no contact name; a founder-set plan minimum; a corrected-invoice line when the client's copy shows the wrong total.
- Build Standard section 13: `scripts/locale_numbers.py` copied unchanged and used for every money figure, percentage, duration and set of days; decimal style read once; one question on an ambiguous figure; plausibility stops ("please check") on amounts under one unit, rates over 100% a year, invoices over three years old and fees bigger than the invoice, released by `confirmed`; country sets date order and page size, never spelling; figures written back in the founder's style. The old ad hoc money parser was replaced, keeping its skill-specific forms (tax words, "=1200*2", fee words). Rough amounts ("about 3k") are now asked, not accepted.
- Public holidays come only from the founder: the defaults line says none were allowed for and asks for any in the next 8 weeks, and the plan lists its dates in that window to check.
- Evals 6 and 7 are the blind tester's two runs, with fixtures; 98 new regression tests.

## 1.1.0 (2026-10-20): global rework, renamed from merigrove-late-payment-recovery
- Renamed to `revos-get-paid` (folder, skill name, memory file `revos-get-paid-memory.md`, package name). The job is now a global "get paid" plan, not a calculation under one country's late payment law.
- Removed: every statutory element (one country's late payment statute and interest order, the central bank rate table and reference dates, interest worked out under the statute, fixed compensation bands, recovery costs, maximum payment period flags, a national small business complaints body, national court routes, public body rules, old-debt time limits), the "law applied" setting, the business-size questions, the pound and day-first date defaults, and the statute and rates references.
- Added: a chase order (who to chase first); a stage 3 "call and payment plan" with an instalment schedule to the cent; an escalation ladder per client ending in "stop work" and "hand to a collections service or lawyer" as options to take advice on; prevention terms (deposit, milestones, card on file, late fee placeholder) marked as drafts to check with a lawyer; locale from the founder (currency, date order, spelling, days off, holidays) with no country assumed and ambiguous dates asked, not guessed.
- Changed: a late fee or interest is applied only when the founder's own contract states it, from their rate or fee in plain arithmetic (rate tied to a published rate: the founder supplies the total, stored as founder supplied); final notice steps are take advice, stop work, collections service or lawyer; the copy checker now refuses any statement of what a law allows, any court or legal threat, any named country's institution, and any fee wording without a contract clause.
- Main file renamed `get-paid-plan-<business>-<date>.docx`; Letter page size for US and Canadian founders, A4 otherwise.

## 1.0.0 (2026-10-20)
- First build as `merigrove-late-payment-recovery`, built around one country's late payment statute. Build cut off before evals were complete; never released.
