# The audit file, recall rows and messy answers

Contents
1. Getting the export
2. The audit file
3. Rows
4. Recall rows (no calendar, or what the calendar missed)
5. Messy answers the scripts read
6. Time zones, several calendars, odd exports

## 1. Getting the export

Tell the founder the one route that matches what they use:

- **Google Calendar (web):** Settings (the cog), Import and export, Export. It downloads a zip with one `.ics` per calendar; attach the one for the main calendar (usually named after their email).
- **Outlook desktop (Windows):** File, Save Calendar, choose a date range covering the last two weeks, Save. Or File, Open and Export, Import/Export, Export to a file, Comma Separated Values, Calendar, and the date range: a `.csv`.
- **Outlook on the web or new Outlook:** Settings, Calendar, Shared calendars, Publish a calendar, then download the ICS link in a browser and attach the file.
- **Apple Calendar (Mac):** File, Export, Export, and attach the `.ics`.
- **A time tracker or a spreadsheet:** a CSV with a title, a start and an end or duration column works.
- **No calendar:** the one-week log (`assets/one-week-log.xlsx` or `.csv`), filled in as they go, then attached.

## 2. The audit file

`parse_calendar.py` writes `activities.json`. Copy it to `audit.json` and add the founder's answers. Values may be messy strings as the founder said them.

| Field | Meaning | If missing |
|---|---|---|
| `business` | Name for the title and file names | "Your business" |
| `currency` | The founder's currency code (USD, SGD, AUD, GBP, EUR, INR...), from the marks on their figures or their words | read from the marks on `rate`, `monthly_revenue` or `cost_hour` ("S$85" is SGD, "A$" AUD, "£" GBP); a bare "$" shows as "$"; none, no symbol |
| `locale` | `country` (ISO code, "JP", "US", "DE") when the founder names where they work; `spelling` (`british` or `american`, from how they write; it sets nothing else); optionally `paper` (`a4` or `letter`) or `clock` (`12` or `24`) only if the founder asks for one; `decimal` (`dot` or `comma`) and `symbol_after` only to override what `rank.py` detects; `lang` ("en-AU") | country from the calendar's time zone, else a currency only one country uses (¥ with "yen", S$, ₹); paper, date order and clock from that country via `locale_numbers.locale_defaults`; none known: A4, day first, 24-hour, said in a note. `date_style` is used only when the country is unknown |
| `confirmed` | Names of figures the founder confirmed after a plausibility stop: `"rate"`, `"week"` or a helper's name | every plausibility check runs |
| `capacity_waits` | `false` when the founder wants every handover to a helper kept even past their spare hours | `true`: the lowest-ranked handovers to that person wait until they have room, said in the report |
| `source` | `calendar`, `tracked`, `calendar+recall`, `tracked+recall` or `recall` | from the parser |
| `stated_week_hours` | Hours worked in a typical one of the audited weeks ("50-55", "bout 55hrs", "60+") | the calendar plus 20%, flagged |
| `untracked_week_hours` | Hours a week the calendar missed last time (from memory) | not used |
| `monthly_revenue` | What the business bills a month ("$38k/month", "S$65k a month", "£4,500 a week", "A$216k a year"), before any sales tax | not used |
| `rate` | What an hour of the founder's time is worth ("$175", "110/hr", "€600 a day") | worked out from `monthly_revenue`, else `[NEED]` |
| `team` | List of people: `name`, `role`, `cost_hour` (what the founder says that person costs them an hour, used as given; never worked out from a salary), `spare_week` | nobody |
| `protected` | Work the founder said stays with them (words that appear in the activity labels) | none |
| `freed_to` | `selling`, `strategy`, `delivery` or `fewer hours` | selling |
| `work_days`, `work_hours` | The founder's working days ("mon-fri", "sun-thu", "mon-sat") and working day ("8-17:30", "8am-6pm", "9 to 6ish"), when they said them; a recall audit needs them from the founder. Hours that differ by day go in as a map: `{"mon-fri": "7:30-19:00", "sat": "7:30-12:30"}` | from the calendar (`period`); unknown is a `NEED`, never a default |
| `activities` | The rows | from the parser |
| `repeats_outside_window` | Repeating events with no entry in the audited weeks; set `"include": false` on any that are not real | included |

## 3. Rows

Calendar rows come from the parser with `hours_each`, `per_month`, `window_hours` and `entries`. Do not edit those numbers: if the grouping is wrong, change the map and parse again. The one exception is how often: an activity seen once in the window is scaled to a month as if it repeats, so the parser hints "once in the window". When the founder says how often it really happens ("the MOT is once a year"), put their words in `per_month` and set `per_month_basis` to "founder said". Never change `window_hours`. Add to each row:

- `category`: 1, 2 or 3 (or "only you", "with instruction", "nobody should"); `personal` or `not work` to leave it out.
- `function`: strategy, selling, managing, delivery or admin.
- `action`: keep, delete, delegate or automate.
- `who`: a named person, a tool, or "a contractor (to find)".
- `reason`: one line, in the founder's terms where possible.
- `protected`: true when the founder said it stays with them.
- `challenge_answer`: the founder's answer to the one challenge, as a short clause in their terms ("clients write to you directly, so it stays with you"), not a verbatim quote. A challenge stated as a default at the read-back that the founder did not change is answered by that default.
- `fixed`: `true` for work done at set times outside the working day that cannot move (evening calls with clients in another time zone, nightly email). It is kept as now in the proposed week instead of being moved into the day. Set automatically when the label says evening, night or weekend, when the founder's hours are a clock time outside their day ("9pm to 10:30"), or when the row happens only on days they do not work; set `false` to override.

## 4. Recall rows (no calendar, or what the calendar missed)

```json
{"activity": "Evening email and WhatsApp", "source": "recall", "hours_each": "an hour", "per_month": "every day",
 "category": 1, "function": "admin", "action": "keep"}
```

- `hours_each` is one sitting; `per_month` is how often, in the founder's words ("twice a week", "most days", "every Friday", "monthly"). Or give `times` and `per` ("3", "week").
- From a ramble or a voice note: pull every activity out into a list with hours each and how often, read it back in one block, and ask "what's wrong or missing?" before ranking.
- Day by day ("Monday: 9 to 11 calls, then a job in Leeds till 4"): one row per kind of activity, with how often it happened in the week.
- When the calendar exists, recall rows are only for time it misses (email, messages, evenings, admin between meetings). Never a recall row for something already in the calendar.
- In a recall-only audit, set `"source": "recall"` at the top. There is no calendar total; the week is the founder's stated hours, or the rows if they give none.

## 5. Messy answers the scripts read

Pass them as written; `timeparse.py` reads them and the notes say how.

Every number goes through `scripts/locale_numbers.py` in the founder's decimal style, detected once from everything they typed (1,234.56 or 1.234,56; 1 234,56; 18,00,000). A figure that reads two ways ("12.500" with no other clue) is asked, not guessed.

| Kind | Examples | Read as |
|---|---|---|
| Hours | "2h", "2hrs", "1.5h", "1,5 h", "90 mins", "1h30", "1:30", "an hour", "half an hour", "hour and a half", "couple of hours", "7,5 Std.", "3 horas", "90 minutos" | hours |
| Rough | "about 2", "2ish", "~3", "a few hours" (3, noted), "3+" (3, noted) | the figure |
| Ranges | "1-2 hours", "30-45 mins", "50-55" | the midpoint, noted |
| Spoken ranges | "hour, hour and a half", "3, 4 hours", "an hour or two", "2 or 3 hours", "an hour, maybe two" | the midpoint, noted |
| Several in one sitting | "half an hour each, two of them" | the total, noted |
| Clock times | "9-11", "9am-12:30", "2-4pm", "10.30 to 12", "11-1", "9pm to 10:30-ish" | the length, noted |
| Days | "half a day", "the morning", "a day", "a full day", "2 days" | half or all of the founder's own working day, less an hour's break when it runs through 13:00 (8 hours when the working day is unknown), noted |
| How often | "daily", "every morning", "twice a week", "2x a week", "Mon/Wed/Fri", "tues and thurs", "mon to fri", "mon-sat", "sun-thu", "monday through friday", "fortnightly", "every other week", "monthly", "3 a month", "quarterly", "most days" (4 a week, noted) | times a month. Day ranges are expanded round the week and counted, noted. "Daily", "every day" and "every morning" are each of the founder's own working days; "weekdays" and "every weekday" are Monday to Friday, 5 days, whatever their week |
| Week | "55", "bout 55hrs", "50-55", "60+", "10 a day", "5, 6 hours", "60 hours? feels like 70" (the first figure, noted) | hours a week |
| Money | "$110", "S$85/hr", "110/hr", "€600 a day", "A$1.2k", "22k a month", "£4,500 a week", "₹2,000 an hour", "₹2.4 lakh a month", "RM 50", "about 450万 a month", "4.5 million yen a month", "2,800 yen an hour", "9.800 €", "I bill £65 an hour" | hourly or monthly as the field needs; multipliers (k, million, mn, bn, lakh, crore, 万, 億) applied; the mark or word sets the currency. A figure written in other characters ("四百五十万") stops with a request for digits |

A value the scripts cannot read, or that reads two ways, stops the run with every such value listed together. Ask the founder about all of them in one message.

After reading, `rank.py` checks the headline figures: an hour of the founder's time worth under 1 unit of currency or less than a helper costs, a week outside 10 to 100 hours, a helper with more than 60 spare hours or costing under 1 unit an hour. Any of these stops the run with the figure it read and where from ("I read your monthly sales as ¥450 from 'about 450'; is that right?"). Put the questions to the founder in one message.

## 6. Time zones, working weeks, holidays, several calendars, odd exports

- **Time zone.** The parser uses `--tz` if the founder gave one, else the calendar's own zone (Google's X-WR-TIMEZONE), else the zone most events are written in (Outlook's "Eastern Standard Time" is read as America/New_York, "Singapore Standard Time" as Asia/Singapore), and says which. CSV exports and the one-week log carry no zone and need none: times are read as written. An export written only in UTC with no zone named stops with one question: which city or time zone they work in (`--tz Asia/Singapore`, `--tz Sydney` both work).
- Events in other zones (a London client on a New York calendar, a Sydney supplier on a Singapore one) are converted, including across clock changes, which fall on different dates in the US, Europe, Australia and New Zealand and not at all in most of Asia. If the computer has no time zone data, the parser uses the zone rules inside the export, then built-in rules for common zones.
- **Working week.** From what the founder said, else Outlook's own working-hours setting in the export, else what the events show (weekdays booked in at least half the weeks; the typical first start to the typical last finish, to the half hour). A six-day week, a Sunday to Thursday week or a 7:00 start all come through. Too thin a calendar prints `ASK:`; the question goes into question 1, never a guessed default.
- **Public holidays and days off** are never looked up. They come from the calendar (an all-day event that says it is a public holiday, an event from an attached holidays calendar such as Google's "Holidays in Australia", or the founder's own "Annual leave", "Day off", "PTO", "Out of office", or Outlook's out-of-office status) or from the founder (`--holidays 2026-11-26,2026-11-27`). A colleague's absence ("Tom on holiday") is not the founder's day off. Holidays are left out of the working days, listed in the readback, and named in the report's basis as a reason the week may be lighter.
- Two calendars (work and personal, or a holidays calendar): attach both. The same meeting in both counts once. Personal entries are sorted out in the map.
- **CSV dates:** day or month first is worked out from the dates (a day above 12), else from which reading puts the entries in recent weeks, and said. If both readings fit, the parser stops with one question; pass `--date-order dmy` or `--date-order mdy` with the answer.
- An old export (nothing one-off in the audited weeks) is flagged: ask for a fresh one.
