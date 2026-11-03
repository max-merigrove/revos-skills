# Changelog

## 1.1.0 (2026-11-02)
Blind-test fix round.
- Fixed: the build crashed on any money or volume range question without a "Not sure" option (or with an overlap or a wrong thousands style). Range checks now record PROBLEM and WARN lines as intended; regression tests added.
- An unexpected script error now names the file, line and function in its STOP line; `LMF_DEBUG=1` prints the full trace.
- The launch pack lists every merge tag in double braces (`{{booking_link}}` was printed with single braces); the build now refuses a pack with a broken or unknown tag.
- The build prints every WARN line from every check, and SKILL.md says to fix or explain each one. "More" with no comparison and promises of the offer's outcome ("Fix your", "Grow your", "Get more") are PROBLEMs in titles, headlines, subheads, buttons and subject lines.
- "On average" is a claim only beside a figure or a research word; answer options in the reader's own voice ("I know it on average") are not scanned as claims.
- Result page: `cta.line_top_tier` (required) gives a top-tier reader an honest line and a quiet text link instead of "these gaps look familiar"; `strength_mid` (required) words What is working to match an upper answer that is not the top one. Mirrored in the printable copy and the browser check.
- Launch pack page flow: an email's last two paragraphs, sign-off and P.S. stay together; label and value pairs, the opt-in block and the thank-you block do not split.
- `cta.link` must be https or mailto. The pack no longer speaks in the tool's voice, says it is not for readers, and SKILL.md names sources by kind, never by a client's name. Opt-in copy that says the result arrives by email is refused.
- New `magnet.py init` writes a full spec scaffold with `FILL:` values; a spec with any left never builds.
- A founder who says "just build it" gets the build first, with the read-back and defaults in the delivery reply.
- Description: adds "lead magnet", "grow my email list", "get people onto my email list" and "turn my slides into a download"; excludes welcome sequences and personality or product-finder quizzes.
- Evals: the blind test's two runs (India scorecard, Germany checklist) are now evals 7 and 8 with fixtures and sample runs; 23 regression tests added (74 in all).

## 1.0.0 (2026-11-02)
- First release (Wave 2b build).
- One spec file builds everything: a self-contained scorecard page (five scored questions, up to two fit questions, a result with what is working, three fixes, the door and the call to action or a kind not-a-fit line) with a printable Word copy; or a checklist (Word, and PDF where LibreOffice is present); or a one-page guide; plus the launch pack (read first, topic and why, opt-in page copy, thank-you page, five emails with their rules, result map, what to measure, go-live checklist). The opt-in page is built as HTML only when the founder gives a form address or embed code.
- Checks by script: structure and sources (every question and item traced to the founder's material); tier simulation over every possible answer set (no gap or overlap, no tier under 10 or over 60 per cent, a middle pattern in a middle tier); answer ranges in order and in the founder's number style; time to finish; contrast; a claim scan that fails any figure or general claim without a named source; currency, spelling, legal, tax and never-word checks; five-email rules; a page audit (no network call, form, storage, placeholder, box or rule; labelled inputs; one h1; no sideways scroll at 375 pixels; no promise of an email the page cannot send).
- Memory: offer, fit rules, link, sign-off, locale, look, hosting, past magnets and their subject lines, learnings; dates in the founder's own order.
