#!/usr/bin/env python3
"""Read durations, frequencies, hours and money the way founders actually type or say them, anywhere.

Imported by parse_calendar.py, rank.py and memory.py. Standard library only. No network calls.
Every number is read by locale_numbers.py (Merigrove's shared reader, copied here unchanged), in
the decimal style detected once from what the founder typed (set DECIMAL before reading). This
file adds the forms a time audit needs on top of it: clock-time ranges ("9-11", "9pm to 10:30-ish"),
parts of the founder's own working day ("the morning"), spoken ranges ("hour, hour and a half",
"3, 4 hours", "an hour or two") and how often ("mon to fri", "every weekday", "fortnightly").

  hours("1h30")              -> (1.5, None)
  hours("9-11")              -> (2.0, "read '9-11' as a time range, 2 hours")
  per_month("mon to fri")    -> (21.67, "read 'mon to fri' as 5 days a week")
  money("about 450万 a month") -> (4500000.0, "month")
  currency_of("A$110/hr")    -> ("AUD", "A$")

Every function raises InputError with a plain sentence when it cannot read a value, and
AmbiguousInput (a kind of InputError) when the value reads two ways, so the calling script can
put one question to the founder instead of a traceback or a silent guess.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import locale_numbers as LN  # noqa: E402

# Working conventions, kept in one place. No country's working day is assumed: the calling script sets
# DAY_HOURS and the working days from the founder's own week (their calendar or their words). The
# values below are used only when neither is known, and every reading that uses them says so.
DAY_HOURS = 8.0                 # a "day" of work when a founder says "2 days"; replaced by their own working day
WEEKS_PER_MONTH = 52 / 12       # one convention everywhere: a month is 52/12 weeks
WORK_DAYS_PER_WEEK = 5          # "daily" means every working day; replaced by their own working days
DECIMAL = None                  # "dot" or "comma": the founder's decimal style, detected once by the caller

# Currency marks a founder may type. A bare "$" or "¥" is kept as typed: each is used in several countries.
CURRENCY_MARKS = [("us$", "USD", "US$"), ("s$", "SGD", "S$"), ("sgd", "SGD", "S$"), ("a$", "AUD", "A$"),
                  ("au$", "AUD", "A$"), ("aud", "AUD", "A$"), ("nz$", "NZD", "NZ$"), ("nzd", "NZD", "NZ$"),
                  ("c$", "CAD", "C$"), ("ca$", "CAD", "C$"), ("cad", "CAD", "C$"), ("hk$", "HKD", "HK$"),
                  ("hkd", "HKD", "HK$"), ("usd", "USD", "$"), ("gbp", "GBP", "£"), ("eur", "EUR", "€"),
                  ("inr", "INR", "₹"), ("rs.", "INR", "₹"), ("myr", "MYR", "RM"), ("rm", "MYR", "RM"),
                  ("aed", "AED", "AED "), ("zar", "ZAR", "R"), ("jpy", "JPY", "¥"), ("chf", "CHF", "CHF "),
                  ("php", "PHP", "₱"), ("cny", "CNY", "¥"), ("krw", "KRW", "₩"), ("thb", "THB", "฿"),
                  ("£", "GBP", "£"), ("€", "EUR", "€"), ("₹", "INR", "₹"), ("₱", "PHP", "₱"), ("₩", "KRW", "₩"),
                  ("฿", "THB", "฿"), ("円", "JPY", "¥"), ("¥", None, "¥"), ("$", None, "$")]
SYMBOL_FOR = {"USD": "$", "SGD": "S$", "AUD": "A$", "NZD": "NZ$", "CAD": "C$", "HKD": "HK$", "GBP": "£", "EUR": "€",
              "INR": "₹", "MYR": "RM", "AED": "AED ", "ZAR": "R", "JPY": "¥", "CHF": "CHF ", "PHP": "₱", "CNY": "¥",
              "KRW": "₩", "THB": "฿", "NGN": "₦", "KES": "KES ", "BRL": "R$", "MXN": "MX$"}
_MARK_RX = re.compile("|".join(
    (r"(?<![a-z])" + re.escape(m) + r"(?![a-z])") if m[0].isalpha() and m.isascii() else re.escape(m)
    for m, _c, _s in sorted(CURRENCY_MARKS, key=lambda x: -len(x[0]))), re.I)


class InputError(Exception):
    """A value the audit cannot use. Shown to the founder as one plain STOP line."""


class AmbiguousInput(InputError):
    """A value that reads two ways (12.500, 1,250 from a founder who writes decimal commas). Ask which."""


NUM_WORDS = {
    "zero": 0, "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "fifteen": 15,
    "twenty": 20, "thirty": 30, "forty": 40, "forty five": 45, "forty-five": 45, "sixty": 60, "ninety": 90,
    "once": 1, "twice": 2, "thrice": 3, "couple": 2, "a couple": 2, "few": 3, "a few": 3,
}
FUZZ = ("about", "around", "roughly", "approx.", "approx", "approximately", "circa", "maybe", "probably",
        "say", "bout", "abt", "or so", "ish", "~", "give or take", "usually", "normally", "typically",
        "at least", "max", "min.", "up to", "nearly", "almost", "just over", "just under", "over", "like",
        "basically", "honestly", "i think", "i guess", "something like", "-ish")
DAYS = {"mon": 0, "monday": 0, "mondays": 0, "tue": 1, "tues": 1, "tuesday": 1, "tuesdays": 1,
        "wed": 2, "weds": 2, "wednesday": 2, "wednesdays": 2, "thu": 3, "thur": 3, "thurs": 3,
        "thursday": 3, "thursdays": 3, "fri": 4, "friday": 4, "fridays": 4, "sat": 5, "saturday": 5,
        "saturdays": 5, "sun": 6, "sunday": 6, "sundays": 6}
ABBR = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
_DAY_RX = "|".join(sorted(DAYS, key=len, reverse=True))
TAIL = r"(?:\s+(?:each|a time|at a time|a go|a session|a pop|per \w+|or so|tops|max|roughly|long|each time|every time))?"


def num(text, label="figure"):
    """One founder-typed number, in their decimal style, through locale_numbers."""
    try:
        v, _n = LN.parse_number(str(text), DECIMAL, allow_words=False)
    except LN.Ambiguous as e:
        raise AmbiguousInput(f"{label}: {e}")
    except LN.Unreadable as e:
        raise InputError(f"{label}: {e}")
    return v


def _canon(s, label):
    """Rewrite every number written with a comma (1,5 or 2,800) as a plain number, in the founder's style.
    A comma followed by a space is a list ("3, 4 hours"), not a decimal, and is left alone."""
    return re.sub(r"\d+(?:,\d+)+", lambda m: f"{num(m.group(0), label):g}", s)


def _f(x):
    return float(x)


def _fmt(x):
    return f"{round(x, 2):g}"


def _hrs(x):
    return f"{_fmt(x)} hour" if _fmt(x) == "1" else f"{_fmt(x)} hours"


def _strip_fuzz(s):
    s = re.sub(r"-?ish\b", " ", s)
    s = " " + s + " "
    for w in sorted(FUZZ, key=len, reverse=True):
        if w == "~":
            s = s.replace("~", " ")
        elif w == "-ish":
            continue
        else:
            s = re.sub(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", " ", s)
    s = re.sub(r"[?!]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _words_to_numbers(s, articles=True):
    s = re.sub(r"\bone and a half\b", "1.5", s)
    s = re.sub(r"\b(\d+(?:\.\d+)?) and a half\b", lambda m: _fmt(_f(m.group(1)) + 0.5), s)
    s = re.sub(r"\b(an?|one) hour and a half\b", "1.5 hours", s)
    s = re.sub(r"\bhour and a half\b", "1.5 hours", s)
    s = re.sub(r"\bhalf an? hour\b|\bhalf hour\b|\bhalf-hour\b", "0.5 hours", s)
    s = re.sub(r"\b(a )?quarter of an hour\b|\bquarter hour\b", "0.25 hours", s)
    s = re.sub(r"\bthree quarters of an hour\b", "0.75 hours", s)
    for w, n in sorted(NUM_WORDS.items(), key=lambda kv: len(kv[0]), reverse=True):
        if not articles and w in ("a", "an"):
            continue
        s = re.sub(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", str(n), s)
    return s


def _clock(tok):
    """'9', '9am', '12:30', '2pm', '10.30' -> hours past midnight, with an am/pm marker or None."""
    m = re.fullmatch(r"(\d{1,2})(?:[:.](\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)?", tok.strip())
    if not m:
        return None
    h, mi, ap = int(m.group(1)), int(m.group(2) or 0), (m.group(3) or "").replace(".", "") or None
    if h > 24 or mi > 59:
        return None
    if ap == "pm" and h < 12:
        h += 12
    if ap == "am" and h == 12:
        h = 0
    return h + mi / 60, ap


def _prep_hours(value, label):
    raw = str(value).replace("\u2013", "-").replace("\u2014", "-")
    s = raw.strip().lower().replace(" ", " ")
    s = _canon(s, label)
    s = _strip_fuzz(s)
    s = re.sub(r"\s+(each|a time|at a time|a go|a session|a pop|per \w+|or so|tops|max|long|each time|every time)$", "", s)
    # a few words of context after the unit ("2-3 hours with the train", "an hour including travel") are dropped
    s = re.sub(r"^(.*?\b(?:hours?|hrs?|mins?|minutes?|days?)\b)\s+(?:with|including|incl\.?|inc\.?|plus|for|in|on|at|of|"
               r"counting|there|door|round|total|altogether|all|travel|the)\b[a-z\s'-]*$", r"\1", s)
    return raw, s


def hours(value, label="hours"):
    """Return (hours, note). Accepts numbers, units, minutes, days, words, ranges, spoken ranges and clock times."""
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return None, None
    if isinstance(value, bool):
        raise InputError(f"{label} should be a number of hours, not yes or no")
    if isinstance(value, (int, float)):
        if value < 0:
            raise InputError(f"{label} cannot be negative ({value})")
        return float(value), None
    raw, s = _prep_hours(value, label)
    # "half an hour each, two of them": one sitting holds several
    m = re.fullmatch(r"(.+?)\s*(?:each|apiece)?,?\s*(?:x\s*)?(\d+|two|three|four|five|six) of (?:them|those)", s)
    if m:
        k = _f(_words_to_numbers(m.group(2)))
        h, _n = hours(m.group(1), label)
        return h * k, f"read '{raw}' as {_fmt(k)} x {_fmt(h)} hours, {_hrs(h * k)}"
    # spoken ranges: "hour, hour and a half", "3, 4 hours", "an hour or two", "2 or 3 hours"
    sp = _spoken_range(s, label)
    if sp is not None:
        lo, hi = sp
        mid = (lo + hi) / 2
        return mid, f"read '{raw}' as {_fmt(lo)} to {_fmt(hi)} hours, the midpoint {_fmt(mid)}"
    note = f"read '{raw}' as 3 hours" if re.search(r"\bfew\b", s) else None
    s = re.sub(r"\bhalf (a |1 )?day", "half day", s)
    s = re.sub(r"^(a|an|one) (whole |full )?(day|morning|afternoon)", r"1 \2\3", s)
    s = re.sub(r"\b(a )?couple of\b", "2", s)
    s = re.sub(r"\b(a )?few\b", "3", s)
    s = _words_to_numbers(s)
    if s in ("hour", "hours", "1 hour"):
        return 1.0, None
    if re.search(r"\d\s*\+\s*$", s):
        s = re.sub(r"\+\s*$", "", s)
        note = f"read '{raw}' as its lowest figure"
    if s.startswith("-"):
        raise InputError(f"{label} cannot be negative ('{raw}')")
    # h:mm or hh:mm:ss durations (an export's Duration column)
    m = re.fullmatch(r"(\d{1,3}):(\d{2})(?::(\d{2}))?", s)
    if m:
        return int(m.group(1)) + int(m.group(2)) / 60 + int(m.group(3) or 0) / 3600, note
    # half a day, a day, mornings
    m = re.fullmatch(r"(?:(\d+(?:\.\d+)?)\s*)?half(?: a)? days?", s)
    if m:
        v = DAY_HOURS / 2 * (_f(m.group(1)) if m.group(1) else 1)
        return v, f"read '{raw}' as {_fmt(v)} hours at {_fmt(DAY_HOURS / 2)} hours a half day"
    m = re.fullmatch(r"(most|much|half|part|some)(?: of)? (the |a |an |1 )?(morning|afternoon|evening|day|working day)", s)
    if m:
        part = {"most": 0.8, "much": 0.8, "half": 0.5, "part": 0.5, "some": 0.5}[m.group(1)]
        base = DAY_HOURS if "day" in m.group(3) else DAY_HOURS / 2
        v = round(base * part * 4) / 4
        return v, f"read '{raw}' as {_fmt(v)} hours; check it"
    if re.fullmatch(r"(the |a |an |1 )?(whole |all )?(evening|night)", s) or s == "all evening":
        return 3.0, f"read '{raw}' as 3 hours; check it"
    if re.fullmatch(r"(all|the whole) (morning|afternoon|evening)", s):
        return DAY_HOURS / 2, f"read '{raw}' as half a day, {_fmt(DAY_HOURS / 2)} hours"
    if re.fullmatch(r"(the |a |an |1 )?(whole |full )?(morning|afternoon)s?", s):
        return DAY_HOURS / 2, f"read '{raw}' as half a day, {_fmt(DAY_HOURS / 2)} hours"
    if re.fullmatch(r"(the |a |1 )?(whole |full |all )?(day|working day)", s):
        return DAY_HOURS, f"read '{raw}' as a working day of {_hrs(DAY_HOURS)}"
    # 1h30, 1h 30m, 1 hr 15 mins
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(?:h|hr|hrs|hour|hours)\s*(?:and\s*)?(\d+)\s*(?:m|min|mins|minutes)?", s)
    if m:
        return _f(m.group(1)) + int(m.group(2)) / 60, note
    # a range with a unit after it: 1-2 hours, 10 to 12 hrs, 30-45 mins, 2-3 days
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(?:h|hrs?|hours?)?\s*(?:-|to|or)\s*(\d+(?:\.\d+)?)\s*(h|hr|hrs|hour|hours|m|min|mins|minutes|d|day|days)\b" + TAIL, s)
    if m:
        a, b, u = _f(m.group(1)), _f(m.group(2)), m.group(3)
        k = 1 / 60 if u.startswith("m") else (DAY_HOURS if u.startswith("d") else 1)
        mid = (a + b) / 2 * k
        return mid, f"read '{raw}' as the midpoint, {_fmt(mid)} hours"
    # clock-time range: 9-11, 9am-12:30, 2-4pm, 10.30 to 12, 11-1, 9pm to 10:30
    m = re.fullmatch(r"(\d{1,2}(?:[:.]\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?)\s*(?:-|to|until|till)\s*(\d{1,2}(?:[:.]\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?)\s*-?", s)
    if m:
        a, b = _clock(m.group(1)), _clock(m.group(2))
        if a and b:
            ta, tb = a[0], b[0]
            if b[1] == "pm" and a[1] is None and ta < 12 and ta + 12 <= tb:
                ta += 12
            if tb <= ta and tb + 12 > ta and tb < 13:
                tb += 12
            if tb > ta and tb - ta <= 16:
                return tb - ta, f"read '{raw}' as a time range, {_hrs(tb - ta)}"
    # single values with a unit
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(m|min|mins|minute|minutes)\b" + TAIL, s)
    if m:
        return _f(m.group(1)) / 60, note
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(d|day|days)\b" + TAIL, s)
    if m:
        v = _f(m.group(1)) * DAY_HOURS
        return v, f"read '{raw}' as {_fmt(v)} hours at {_fmt(DAY_HOURS)} hours a day"
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(h|hr|hrs|hour|hours)?" + TAIL, s)
    if m:
        return _f(m.group(1)), note
    # other languages and forms the shared reader knows ("7,5 Std.", "90 minutos", "3 horas", "2 Tage")
    try:
        v, notes = LN.parse_hours(str(value), day_hours=DAY_HOURS, week_days=WORK_DAYS_PER_WEEK, decimal=DECIMAL)
        return v, (f"read '{raw}' as {_fmt(v)} hours" + (f" ({'; '.join(notes)})" if notes else ""))
    except LN.Ambiguous as e:
        raise AmbiguousInput(f"{label}: {e}")
    except (LN.Unreadable, ValueError):
        pass
    raise InputError(f"could not read '{raw}' as a number of hours for {label}; give it like '1.5', '90 mins' or '9-11'")


def _one_side(t, unit, label):
    t = t.strip()
    if t in ("hour", "an hour", "a hour", "one hour"):
        return 1.0
    if re.fullmatch(r"\d+(?:\.\d+)?", t) and unit:
        t = f"{t} {unit}"
    v, _n = hours(t, label)
    return v


def _spoken_range(s, label):
    """'hour, hour and a half', '3, 4 hours', 'an hour or two', '2 or 3 hours', '20, 30 mins' -> (lo, hi) or None."""
    w = _words_to_numbers(s)
    w = re.sub(r"\b1 (hour|hours)\b", r"1 \1", w)
    m = re.fullmatch(r"(?:an?\s+|1\s+)?(hour|day|week)s?\s+or\s+(2|two)", s) or re.fullmatch(r"1\s+(hour|day|week)s?\s+or\s+2", w)
    if m:
        unit = m.group(1)
        k = 1.0 if unit == "hour" else (DAY_HOURS if unit == "day" else DAY_HOURS * WORK_DAYS_PER_WEEK)
        return k, 2 * k
    parts = re.split(r"\s*,\s+|\s+or\s+", w)
    if len(parts) != 2:
        return None
    left, right = parts
    um = re.search(r"(hours?|hrs?|h|mins?|minutes?|m)\s*$", right)
    unit = um.group(1) if um else ("hours" if re.search(r"\bhour", left) else "")
    if not re.search(r"\d|hour", left) or not re.search(r"\d", right):
        return None
    try:
        lo, hi = _one_side(left, unit, label), _one_side(right, unit, label)
    except InputError:
        return None
    if hi < lo:
        lo, hi = hi, lo
    if lo <= 0 or hi > lo * 4:
        return None
    return lo, hi


def _days_in(s):
    """Weekday names in a phrase, ranges expanded and wrapped round the week, counted by locale_numbers."""
    found = set()
    first_seen = [DAYS[t] for t in re.findall(r"[a-z]+", s) if t in DAYS][:1]
    for m in re.finditer(r"\b(" + _DAY_RX + r")\s*(?:-|to|through|thru|till|until)\s*(" + _DAY_RX + r")\b", s):
        a, b = DAYS[m.group(1)], DAYS[m.group(2)]
        n = LN.count_weekdays(f"{ABBR[a]} to {ABBR[b]}")
        found |= {(a + k) % 7 for k in range(n)}
    rest = re.sub(r"\b(" + _DAY_RX + r")\s*(?:-|to|through|thru|till|until)\s*(" + _DAY_RX + r")\b", " ", s)
    for tok in re.findall(r"[a-z]+", rest):
        if tok in DAYS:
            found.add(DAYS[tok])
    if not found:
        return None, []
    first = min(found, key=lambda d: (d - first_seen[0]) % 7) if first_seen else min(found)
    names = [ABBR[d] for d in sorted(found, key=lambda d: (d - first) % 7)]
    return LN.count_weekdays(", ".join(names)), names


def per_month(value, work_days=WORK_DAYS_PER_WEEK, label="how often"):
    """Return (times a month, note). Bare numbers are times a month."""
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return None, None
    if isinstance(value, bool):
        raise InputError(f"{label} should say how often, not yes or no")
    if isinstance(value, (int, float)):
        if value < 0:
            raise InputError(f"{label} cannot be negative")
        return float(value), None
    raw = str(value).replace("\u2013", "-").replace("\u2014", "-")
    s = _canon(raw.strip().lower(), label)
    s = _words_to_numbers(_strip_fuzz(s), articles=False)
    s = re.sub(r"\bper\b", "a", s).replace("/", " a ").replace(" x ", " ").replace("x ", " ")
    s = re.sub(r"(\d)\s*x\b", r"\1", s)
    s = re.sub(r"\s+", " ", s).strip()
    if s.startswith("-"):
        raise InputError(f"{label} cannot be negative ('{raw}')")
    wpm = WEEKS_PER_MONTH
    wd = work_days or WORK_DAYS_PER_WEEK
    note = None
    num_m = re.search(r"(\d+(?:\.\d+)?)\s*(?:-|to|or|,)\s*(\d+(?:\.\d+)?)", s)
    if num_m:
        n = (_f(num_m.group(1)) + _f(num_m.group(2))) / 2
        note = f"read '{raw}' as the midpoint, {_fmt(n)}"
    else:
        num_m = re.search(r"(\d+(?:\.\d+)?)", s)
        n = _f(num_m.group(1)) if num_m else None
    if "few" in raw.lower() and note is None:
        note = f"read '{raw}' as 3"
    if re.search(r"\b(7 days a week|every single day|including weekends|weekends too)\b", s):
        return 7 * wpm, f"read '{raw}' as 7 days a week"
    if re.search(r"\bmost (days|nights|evenings|mornings|afternoons|weekdays)\b", s):
        return 4 * wpm, f"read '{raw}' as 4 days a week"
    if re.search(r"\b(every|each) weekend\b|\bweekends\b|\bat the weekend\b", s):
        return (n or 1) * wpm, f"read '{raw}' as once a week"
    if re.search(r"\b(some|a few) (days|nights|evenings)\b|\bsometimes\b|\boccasionally\b", s) and not re.search(r"\ba week\b", s):
        return 2 * wpm, f"read '{raw}' as twice a week; check it"
    if re.search(r"\b(fortnight|fortnightly|every other week|alternate weeks|bi-?weekly|every 2 weeks)\b", s):
        k = n if (n and "fortnight" in s and "every" not in s and "fortnightly" not in s) else 1
        nt = f"read '{raw}' as every two weeks" if "biweekly" in s.replace("-", "") else note
        return k * wpm / 2, nt
    m = re.search(r"every (\d+(?:\.\d+)?) (week|weeks|month|months)", s)
    if m:
        k = _f(m.group(1))
        return (wpm / k if m.group(2).startswith("week") else 1 / k), note
    if re.search(r"\b(quarterly|quarter)\b", s):
        return (n or 1) / 3, note
    if re.search(r"\b(yearly|annually|annual|a year|year)\b", s):
        return (n or 1) / 12, note
    if re.search(r"\b(monthly|month|months)\b", s):
        return (n or 1), note
    per_day = re.search(r"(\d+(?:\.\d+)?)\s*(?:times )?(?:a|each|every) ?day\b", s)
    k = _f(per_day.group(1)) if per_day else 1.0
    # weekday names: ranges ("mon to fri", "sun-thu") expanded, lists counted
    nd, names = _days_in(s)
    if nd:
        if n and re.search(r"\d+ (times )?(a )?(week|wk)\b", s) and not per_day:
            return n * wpm, note
        days_txt = f"{nd} day{'s' if nd != 1 else ''} a week ({', '.join(x.capitalize() for x in names)})"
        return k * nd * wpm, (f"read '{raw}' as {days_txt}" if nd > 1 or k != 1 else note)
    if re.search(r"\bweek ?days?\b|\bweeknights?\b|\bevery weeknight\b", s):
        kd = LN.count_weekdays("weekdays")
        return k * kd * wpm, f"read '{raw}' as Monday to Friday, {kd} days a week"
    if re.search(r"\b(every|each) (night|evening)\b|\bnightly\b", s):
        return wd * wpm, f"read '{raw}' as each of your {_fmt(wd)} working days"
    if re.fullmatch(r"(1 )?(daily|every ?day|each day|every morning|every afternoon|every evening|every working day|"
                    r"each working day|a day|day|every work day)", s):
        return wd * wpm, f"read '{raw}' as each of your {_fmt(wd)} working days"
    if re.search(r"\b(a|each|every|per) ?(working )?day\b|\bdaily\b|\bpd\b", s):
        return (n or 1) * wd * wpm, f"read '{raw}' as {_fmt(n or 1)} on each of your {_fmt(wd)} working days"
    if re.search(r"\b(weekly|week|weeks|wk|wks|pw)\b", s):
        return (n or 1) * wpm, note
    if n is not None and re.fullmatch(r"\d+(?:\.\d+)?( times)?", s):
        return n, note
    raise InputError(f"could not read '{raw}' as how often for {label}; give it like 'twice a week', '3 a month' or 'daily'")


def week_hours(value, label="hours a week", work_days=None):
    """Hours worked in a week: '55', '55hrs', 'bout 50-55', '60+', '5, 6 hours'."""
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return None, None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        v = float(value)
        note = None
    else:
        raw = str(value).replace("\u2013", "-").replace("\u2014", "-")
        s = _canon(raw.lower(), label)
        s = _words_to_numbers(_strip_fuzz(s), articles=False)
        m = re.search(r"(\d+(?:\.\d+)?)\s*(?:h|hrs?|hours?)?\s*(?:-|to|or|,)\s*(\d+(?:\.\d+)?)", s)
        if m and _f(m.group(2)) > _f(m.group(1)):
            v = (_f(m.group(1)) + _f(m.group(2))) / 2
            note = f"read '{raw}' as the midpoint, {_fmt(v)} hours"
        else:
            m = re.search(r"(\d+(?:\.\d+)?)", s)
            if not m:
                raise InputError(f"could not read '{raw}' as {label}")
            v = _f(m.group(1))
            note = f"read '{raw}' as {_fmt(v)} hours" if ("+" in s or re.search(r"\d.*\D\d", s)) else None
            if re.search(r"\b(a|per|each) ?day\b|\bdaily\b", s):
                wd = work_days or WORK_DAYS_PER_WEEK
                v = v * wd
                note = f"read '{raw}' as {_fmt(v)} hours a week over {_fmt(wd)} working days"
    if v < 0 or v > 112:
        raise InputError(f"{label} of {_fmt(v)} is not possible in a week; check the figure")
    return v, note


def currency_of(value):
    """The currency a founder's figure is written in: (ISO code or None, symbol as they would write it)."""
    if value is None or isinstance(value, (int, float)):
        return None, None
    s = str(value).strip().lower()
    for mark, code, sym in sorted(CURRENCY_MARKS, key=lambda x: -len(x[0])):
        rx = (r"(?<![a-z])" + re.escape(mark) + r"(?![a-z])") if mark[0].isalpha() and mark.isascii() else re.escape(mark)
        if re.search(rx, s):
            if code is None:  # a bare $ or ¥: a currency word or code elsewhere may settle it
                c2 = LN.find_currency(re.sub(re.escape(mark), " ", s))
                if c2 and re.fullmatch(r"[A-Z]{3}", c2):
                    return c2, SYMBOL_FOR.get(c2, c2 + " ")
            return code, sym
    c = LN.find_currency(str(value))
    if c and re.fullmatch(r"[A-Z]{3}", c):
        return c, SYMBOL_FOR.get(c, c + " ")
    return None, None


_PERIODS = [
    ("hour", r"(?:/|\b(?:a|per|an|each)\s*)(?:hr|hour|h)\b|(?<=\d)\s*ph\b|\bph\b|p/h|\bhourly\b|\ban hour\b"),
    ("day", r"(?:/|\b(?:a|per|each)\s*)day\b|\bday rate\b|\bpd\b|\bdaily\b"),
    ("week", r"(?:/|\b(?:a|per|each)\s*)(?:wk|week)\b|\bpw\b|\bweekly\b"),
    ("month", r"(?:/|\b(?:a|per|each)\s*)(?:mo|month|mth)\b|\bpcm\b|\bpm\b|p/m|\bmonthly\b"),
    ("year", r"(?:/|\b(?:a|per|each)\s*)(?:yr|year|annum)\b|\bpa\b|p/a|\byearly\b|\bannually\b|\bannual\b"),
]


def money(value, label="figure"):
    """Return (amount, period) where period is 'hour', 'day', 'week', 'month', 'year' or None.
    The number is read by locale_numbers: 1.200,50, 18,00,000, 450万, 4.5 million, 2.4 lakh, 22k."""
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return None, None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if value < 0:
            raise InputError(f"{label} cannot be negative")
        return float(value), None
    raw = str(value).replace("\u2013", "-").replace("\u2014", "-")
    low = raw.strip().lower()
    period = None
    t = low
    for p, rx in _PERIODS:
        if re.search(rx, t):
            period = period or p
            t = re.sub(rx, " ", t)
    t = re.sub(r"^\s*(?:(?:i|we|they)\s+(?:bill|charge|invoice|make|earn|take|turn over|do|get|pay(?: them| him| her)?)|"
               r"(?:it|that|he|she|they)(?:'s| is| are| costs?| charges?)|(?:she|he) costs?|costs?|charges?|bills?|"
               r"revenue is|sales are|turnover is)\b", " ", t)
    t = re.sub(r"\b(all in|all-in|incl\.?|including|excl\.?|excluding|before tax|after tax|net|gross|revenue|sales|"
               r"turnover|billings?|a head|each|roughly|roughly about|in sales)\b", " ", t)
    t = _MARK_RX.sub(" ", t.replace("元", " "))
    t = _strip_fuzz(t)
    t = re.sub(r"\s+", " ", t).strip()
    if re.search(r"[぀-ヿ一-鿿]", re.sub(r"[万萬億亿千百]", "", t)):
        raise InputError(f"could not read '{raw}' as an amount for {label}; give the figure in digits, like ¥4,500,000")
    rng = re.fullmatch(r"(.*?\d.*?)\s*(?:-|to)\s*(.*\d.*)", t)
    if rng and not t.startswith("-"):
        left, right = rng.group(1).strip(), rng.group(2).strip()
        mult = re.search(r"(k|m|mn|bn|million|billion|thousand|grand|lakhs?|lacs?|crores?|cr|万|萬|億|亿)\s*$", right)
        if mult and not re.search(r"(k|m|mn|bn|million|billion|thousand|grand|lakhs?|lacs?|crores?|cr|万|萬|億|亿)\s*$", left):
            left = left + (" " if mult.group(1).isalpha() and len(mult.group(1)) > 1 else "") + mult.group(1)
        a, b = num(left, label), num(right, label)
        v = (a + b) / 2
    else:
        v = num(t, label)
    if v < 0:
        raise InputError(f"{label} cannot be negative ('{raw}')")
    return v, period


def monthly_amount(value, label="monthly figure"):
    """Money as a monthly figure: '18k', '£4.5k a week', '£216k a year', '450万'. Returns (amount, note)."""
    v, period = money(value, label)
    if v is None:
        return None, None
    note = None
    if isinstance(value, str) and re.search(r"[万萬億亿]|\b(million|mn|bn|billion|lakhs?|lacs?|crores?|cr)\b", value.lower()):
        note = f"read '{value}' as {fmt_number(v, 2, DECIMAL)}"
    if period == "week":
        return v * WEEKS_PER_MONTH, f"read '{value}' as a weekly figure, {_fmt(v * WEEKS_PER_MONTH)} a month"
    if period == "year":
        return v / 12, f"read '{value}' as a yearly figure, {_fmt(v / 12)} a month"
    if period in ("hour", "day"):
        raise InputError(f"'{value}' reads as a{'n' if period == 'hour' else ''} {period}ly figure; {label} needs a monthly figure")
    return v, note


def hourly_amount(value, label="hourly rate"):
    """Money as an hourly rate. A day rate is divided by DAY_HOURS. Returns (amount, note)."""
    v, period = money(value, label)
    if v is None:
        return None, None
    if period == "day":
        return v / DAY_HOURS, f"read '{value}' as a day rate over {_fmt(DAY_HOURS)} hours"
    if period in ("week", "month", "year"):
        raise InputError(f"'{value}' reads as a {period}ly figure; {label} needs an hourly figure")
    return v, None


# ------------------------------------------------------------------ writing numbers back in the founder's style
def detect_style(samples):
    """The founder's decimal style ('dot', 'comma' or None) from every string they typed, via locale_numbers."""
    return LN.detect_decimal_style([str(x) for x in samples if isinstance(x, str)])


def fmt_number(x, dp=0, decimal=None):
    """1234.5 -> '1,234.5' for a dot founder, '1.234,5' for a comma founder. Trailing zeros dropped when dp > 0."""
    x = float(x)
    s = f"{x:,.{dp}f}"
    if dp:
        s = s.rstrip("0").rstrip(".") if "." in s else s
    if decimal == "comma":
        s = s.replace(",", "\u0001").replace(".", ",").replace("\u0001", ".")
    return s


def fmt_money(x, sym, decimal=None, after=False):
    """Money as the founder writes it: '$1,234', 'S$1,234', '1.234 €' for a founder who puts the symbol after."""
    n = fmt_number(round(float(x)), 0, decimal)
    sym = sym or ""
    if after and sym:
        return f"{n} {sym.strip()}"
    return f"{sym}{n}"


def symbol_after(samples):
    """True when the founder writes the currency mark after the figure (9.800,00 €, 450 zł)."""
    before = after = 0
    for s in samples:
        if not isinstance(s, str):
            continue
        if re.search(r"\d\s*(€|£|\$|zł|kr\b|Kč|CHF|EUR|GBP|USD)", s):
            after += 1
        if re.search(r"(€|£|\$|zł|kr|Kč|CHF|EUR|GBP|USD)\s*\d", s):
            before += 1
    return after > before
