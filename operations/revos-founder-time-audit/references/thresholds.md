# Thresholds, defaults and dated constants

Every figure the scripts use, where it is set, and its source. Change a figure in the script named, nowhere else.

## Method thresholds (`scripts/rank.py`)

| Constant | Value | Meaning | Source |
|---|---|---|---|
| `DOING_FLAG` | 50% | Doing (delivery plus admin) above this share of the week flags a delegation or automation opportunity | Merigrove founder time allocation guidance (internal source MRG-187) |
| `STRATEGY_FLAG` | 15% | Strategy below this share means it is being crowded out | Same |
| `STRATEGY_BLOCK_HOURS` | 4 hours a week | The protected strategy block, at least | Same |
| `UNTRACKED_DEFAULT` | 20% | With no week total from the founder, the week is the calendar plus this, flagged | Operator practice, unverified. For Max to confirm |
| `GOOD_COVERAGE`, `FAIR_COVERAGE` | 70%, 40% | Share of the week the calendar holds for good and fair confidence | Working default, this skill. For Max to confirm |
| `OVER_TOLERANCE_HOURS` | 1 hour | Rows may exceed the stated week by this before the run stops | Working default (rounding in what founders say) |
| `HELD_SHARE` | 50% | A handover held when the activity's weekly hours fell by at least this | Working default, this skill |
| `SELLING_SLOT_CAP` | 3 hours | Most selling laid into one morning or afternoon of the proposed week; the rest is shown as free | Working default, this skill |
| `CAPACITY_SLACK` | 0.25 hours a week | A helper's handovers may run this far past their spare hours before the lowest-ranked one waits | Working default (rounding) |
| `WEEK_MIN`, `WEEK_MAX` | 10 and 100 hours | Plausibility: a week outside this stops the run with a question | Working default, this skill |
| `SPARE_MAX` | 60 hours a week | Plausibility: a helper's spare hours above this stops the run with a question | Working default, this skill |
| Rate floor | 1 unit of currency, and the dearest helper's cost an hour | Plausibility: an hour of the founder's time valued below either stops the run with a question | Build Standard section 13 |

## Units (`scripts/timeparse.py`)

| Constant | Value | Meaning |
|---|---|---|
| `WEEKS_PER_MONTH` | 52/12 | One convention everywhere, so weekly and monthly figures reconcile exactly |
| `WORK_DAYS_PER_WEEK` | 5, only when the working days are unknown | "Daily" means each of the founder's working days: `rank.py` replaces it with their own count (six for a Monday to Saturday week) |
| `DAY_HOURS` | the founder's working day, less an hour's break when it runs through 13:00; 8 only when unknown | "A day" or "2 days" of work; "half a day" or "the morning" is half of it. When the working day is unknown, every reading that uses 8 says so |

## The founder's locale (no constants)

Nothing below is built in. Each value comes from the calendar or the founder, and the readback says which.

| What | Where it comes from | If unknown |
|---|---|---|
| Time zone | `--tz`, the calendar's own zone, the zone most events use | CSV and the log need none; a UTC-only export stops with one question |
| Working days and hours | the founder, Outlook's working-hours setting, what the events show | `ASK:` at intake; `NEED` in the report, laid out on plain days |
| Public holidays and days off | all-day events in the calendar, an attached holidays calendar, the founder's `--holidays` | none flagged |
| Currency | the founder's code or the mark on their figures | figures shown without a symbol |
| Date order (CSV) | the founder, the dates themselves, the reading in recent weeks | one question |
| Country | `locale.country` from the founder's words, else the calendar's time zone, else a currency one country uses | A4, day first, 24-hour, said in a note |
| Paper, date order, clock | the country, through `locale_numbers.locale_defaults` (never from spelling) | A4, day first, 24-hour |
| Decimal style | detected once from everything the founder typed (`locale_numbers.detect_decimal_style`); figures written back the same way | figures read as written; a figure that reads two ways is asked |
| Spelling | how the founder writes; sets spelling only | British |

## Clock rules for computers with no zone data (`scripts/parse_calendar.py`, `ZONE_RULES`)

Used only when the computer has no time zone database and the export carries no VTIMEZONE block for the zone. Common zones in the Americas, Europe, Africa, Asia and Oceania, with the daylight-saving rules in force in 2026 (US: second Sunday of March to first Sunday of November; Europe: last Sunday of March to last Sunday of October at 01:00 UTC; south-east Australia: first Sunday of October to first Sunday of April; New Zealand: last Sunday of September to first Sunday of April; none in Singapore, Hong Kong, Japan, India, the Gulf, Queensland, Western Australia). They mirror the IANA time zone database; re-check against it at each release. They are clock rules, not law or holidays.

## Signposting (no figures)

| Where | Line |
|---|---|
| Report basis line, SKILL.md Rules | Whether someone who works for the founder is an employee or a contractor depends on the rules where they both work: their accountant or an employment adviser |
| SKILL.md Rules | Monitoring staff raises employment and privacy questions under the rules where they work: an employment adviser |

This skill states no tax, employment or legal rule, computes no tax, payroll or on-cost, and looks nothing up for any country. It is a planning tool.
