# Changelog

## 1.2.0 (2026-11-02)
End-to-end round 1 fixes (real headless runs against plain Claude).
- Working files go in a folder made per conversation with `mktemp -d`; a fixed shared path let two chats overwrite each other's case files.
- Founder signals are given by meaning (`start_before_contract`, `slow_to_sign`, `refused_deposit` ...); compute prints a CHECK SIGNAL line when the founder's words do not fit the signal, and long payment terms are never added twice. A draft that simply offers no deposit is not "refuses a deposit".
- Chat follows the language of the founder's own words, not loan words or pasted documents; the client wording can be written in the client's language, and the copy check now catches check, risk and apology words and day counts in German, Dutch, French, Spanish and Italian.
- The build keeps one page by shrinking the type and then the cleared evidence rows, never the client replies; `--proposal-first` puts the paste-ready paragraph above the verdict; `--replace` keeps one current brief on revisions.
- The short first reply is required for a founder in a hurry; the closing line appears once per conversation.
- After round 2: the evidence table keeps the insolvency and judgments rows ahead of filings and age when it trims to fit; rows from the founder carry the check date ("you told me, 02.11.2026"); the headline lists up to six signals.


## 1.1.0 (2026-11-02)
Blind-test fix round.
- A contract that names the right business with a different legal form or a near spelling is now R15 (major) with a "fix before signing" line in the first reply, the brief and the client wording; Stop stays for no register entry or a different business. Ltd and Limited, Pvt Ltd and Private Limited count as the same.
- Each pasted source is cited by its own title: the founder's own notices search no longer shows as "Your pasted extract".
- A claim the register contradicts ("8 years in business" against a company formed last year) is R14, a verified minor signal; claims not seen anywhere show as "You were told, not seen" instead of borrowing a signal's name.
- A pasted register extract with a block missing (filings, officers, a cut-off number) lists each under "could not check" and prints one NEED line to ask for it.
- The brief's headline uses signal names only (never the client's messages or contact details), lists every gap, and marks majors "Raised (major)"; R6 reads "registered 9 months ago".
- Wording: a reply to long days on ongoing work, the founder's own stage names (`deal.stage_names`), and a request to correct the contract name.
- Numbers: "€18.500,-" and "CHF 18'500.-" are read; a fee under 20 a week and a limit above the whole fee are put to the founder as "please check".
- SKILL.md: the scratch folder and where to run scripts are defined; a short first reply for a founder in a hurry; a search that finds nothing is never "no register entry"; a worked `--history` example (a date typed as the first part is now dropped).
- The PDF carries the credit in its Subject property.
- Description: triggers on customers on credit, due diligence on a prospect and net 90; steers away from scam and investor checks.


## 1.0.0 (2026-11-02)
- First release.
- Verdict rule in `scripts/verdict.py` (Go, Caution, Stop with a trace), tested over 30 signal combinations.
- Signal catalogue of 13 register and public signals and 9 founder-observed signals (`references/signals.md`), with confidence levels; only verified signals can decide Stop.
- Unpaid-work model in `scripts/exposure.py` (peak, time carried, cash by the end of the work, per rung), checked against a brute-force simulation of 200 random schedules; calendar months for ongoing work; invoice-day-of-month support.
- Terms ladder for projects and ongoing work; concessions for the wording are tested against the founder's limit before they are offered.
- Lookup protocol tested on registers in four countries; a matching rule sets aside notices about other entities; the lookup card is an equal path when web tools are missing.
- One-page Word brief (PDF twin when LibreOffice is present) built by `scripts/brief.py`, with gates: verdict in the first lines, "could not check" present, every finding sourced, one page, wording and brief copy checks.
- Memory: profile, client log with outcomes, learnings and history; own counts by verdict, never rates under ten outcomes.

Working defaults recorded for review (never shown to founders as benchmarks):
1. Entity first; a name or number that does not match the register is R1 (stop when the register was reachable).
2. Registered 12 months ago or less: minor (R6). More than two officer changes in 12 months: minor (R7).
3. Filings overdue: minor for one period, major for more (R5).
4. Reviews naming non-payment: minor at one or two independent sources, major at three or more (R10); not a Stop, because reviews are public reports, not verified sources.
5. Officers linked to two or more entities dissolved or insolvent in 24 months: major (R11), from the register's own pages only.
6. New client asking 60 days or more: minor (F1). Refused deposit (F2) and pressure to start before a contract (F3): major.
7. Verdict: Stop on a verified stop signal or every rung refused; Caution on any major, two or more minors, or an unverified entity above the limit; Go otherwise.
8. Ladder: rung 0 the founder's usual terms; 1: 30% deposit, balance on delivery, 14 days; 2: 50% deposit, two stages of 25%, 14 days; 3: 50% deposit, stages of 25%, 15% and 10%, 7 days, files held until paid; 4: a first phase of about a quarter of the work paid in full before it starts, or decline. Floors: Go 0, Caution 2, Stop 4; sole traders above the limit 2.
9. Ongoing work: in advance, 14 days and a pause right, then 7 days with card or direct debit on file, then each month paid before it starts.
10. Founder's limit when not given: a quarter of the fee. Project length when not given: 8 weeks. Re-check window: 90 days. Large-exposure line when the recommended peak still exceeds the limit, or the fee reaches the founder's own "large" figure.
