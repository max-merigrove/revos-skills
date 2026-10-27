# Ranges and constants, with where each comes from

Every threshold the skill uses lives as a dated constant at the top of `scripts/funnel.py`. This file records where each one comes from. Checked on 21 October 2026. None of them is a market statistic, and none may be presented to a founder as one.

| Constant | Value | Where it comes from | Status |
|---|---|---|---|
| Show rate range, booked to held | 60 to 75% | Merigrove sales practice: the warm inbound show-rate target used across the sales teams it has run (recorded 24 September 2026). Merigrove's funnel audit method gives 65 to 80% as market orientation; the lower practice range is used because it was set for warm inbound calls | Working default, to be confirmed by Merigrove sales practice for founder-sold calls |
| Close rate range, calls held | 20 to 35% | Merigrove sales practice (the same source) for warm inbound, qualified held calls; Merigrove's funnel audit method gives the same range as market orientation for high-ticket sales with a team | Working default, not yet validated for a founder selling personally; to be confirmed by Merigrove sales practice |
| Enquiry rate and booking rate | none | By design. No range is held for these stages, so none is used. The founder's own best period is the only target | Fixed |
| Counting window | 60 days, two months | Merigrove convention for measuring a funnel at founder scale | Working default |
| Ten-event minimum | 10 | House rule: under ten events one outcome moves a rate by more than ten points | Working default |
| Near the bottom | 5 points | House rule: a rate within five points of the bottom of its range is flagged as the first stage to watch (not a constraint) | Working default |
| Tie rule | 10% | House rule: two prizes within a tenth of each other, the stage nearer the top is named | Working default |
| One-event gate | gap no bigger than 1 over the count given | House rule (v1.2, after the blind test): a gap one event wide is noise, never named | Working default |
| Floor to name a prize | 0.25 clients a month, or a tenth of today's new clients a month if lower | House rule (v1.2): smaller prizes do not justify holding lead spend | Working default |
| Best so far | a rise of more than one event, on 10 or more events | House rule (v1.2): one period is a baseline, not a target | Working default |
| Free places filling | within 30 days at today's pace, if no client leaves | House rule (v1.2): delivery becomes the constraint before the funnel | Working default |
| Booking test length | 30 days if that brings 30 or more enquiries, otherwise 60 | House rule (v1.2): too few enquiries cannot separate booking from volume | Working default |
| Money rounding | nearest 10 under 1,000, nearest 100 above; clients to two places | Readability; stated on every report | Fixed |
| Booking window in the show-rate fix | 0 to 2 working days out | Merigrove sales practice (its show-rate work) | Working default |
| Paper size and date order | From the founder's country through `scripts/locale_numbers.py` (`locale_defaults`): Letter in the US, Canada, Mexico, the Philippines and much of Latin America; month first in the US and the Philippines, year first in Japan, China and Korea | Print and writing convention, shared Merigrove library | Fixed |
| Working week | Monday to Friday unless the founder gives theirs | Said out loud at intake; the founder's own week and days off replace it | Working default |

How to describe a range to a founder: "a working range of 60 to 75%, a default for warm booked sales calls, not a market statistic; your own best two months is the fairer test." Never "the industry average", "most businesses", "a healthy rate is".

The founder's own best two months, given in the run or saved in memory from an earlier run on ten or more events, raises a target above these ranges and never lowers it below them.

No country's law, tax rate, threshold, holiday calendar or institution is relied on by this skill, and the ranges above apply the same way in every country. Currency, dates, spelling, paper and working week follow the founder.

Two neutral lines are the only words the skill says near tax or law, and the script prints both:

- Prices: "Prices are before any sales tax (VAT, GST or similar); ask your accountant whether you need to charge it."
- Following up past enquiries: "Before you message past enquiries, check the rules on contacting people where you and they are." A founder who asks what those rules are is told in one line that it is a question for a lawyer or data protection adviser where they and their contacts are; the skill never says what any law requires.
