#!/usr/bin/env python3
"""Delivery Capacity Check: founder load, client ceiling per offer, handover order.

Usage:
  python3 scripts/capacity.py template                 print an empty inputs file to fill in
  python3 scripts/capacity.py compute <inputs.json>    check the inputs and print every figure
  python3 scripts/capacity.py import-csv <export.csv> [--out <scratch>/steps.json]
        collapse a task export into draft steps (hours as '=' sums of the rows), to read back to the founder
  python3 scripts/capacity.py build <inputs.json> --out <folder> --results <scratch>/results.json
        [--note <scratch>/note.md] [--previous <scratch>/previous.json]
        write the one-page reading (.docx) and the workings (.xlsx)

Exit codes: 0 clean; 1 written, with [NEED] lines to resolve or mention; 2 STOP, nothing usable
was written: read the STOP line, fix the inputs or ask the founder, run again.

The arithmetic, exactly as the method defines it (references/method.md section 2):
  founder load a month  = (F + W hours per client a month) x active clients, per offer, summed
  capacity ceiling      = available delivery hours a month / (F + W hours per client a month), per offer
Standard library only. No network calls.
"""
import argparse
import ast
import json
import math
import operator
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import locale_numbers as LN  # noqa: E402
import office  # noqa: E402

SKILL_NAME = "Delivery Capacity Check"

# ------------------------------------------------------------------ working defaults
# Every default is said to the founder before the figures and listed in the reading. None is drawn
# from any country's rules: time off, the length of a working day and the working week are the
# founder's own, and these stand in only until the founder gives theirs.
WORKING_WEEKS_DEFAULT = 46            # 52 less six weeks off (holidays, public holidays, sick days)
DELIVERY_HOURS_WEEK_DEFAULT = 25      # Merigrove planning default when the founder skips; flagged
DAY_HOURS_DEFAULT = 8.0               # "a day" in an hours field, until the founder gives their own
WORKING_DAYS_WEEK_DEFAULT = 5         # to turn "15 days off" into weeks, until the founder gives their own
DAY_HOURS = DAY_HOURS_DEFAULT         # set per run from the founder's day_hours
_DAY_USED = [False]                   # set when any figure was read in days
# Helper planning lines: Merigrove planning assumptions, NOT benchmarks. Unverified; the founder
# can change both. Shown as "planning assumption" in every founder file.
HELPER_PLAN_LINE_DEFAULT = 0.80
HELPER_LOW_LINE_DEFAULT = 0.50
HANDOVER_COUNT_DEFAULT = 3
MONTHS_ON_MONTHLY_DEFAULT = 12        # months a client stays, for once-per-client steps on monthly offers
MONTHS_ON_ONE_OFF_DEFAULT = 1         # months a one-off project runs, when not given
HOURS_CHECK_GAP = 0.15                # steps vs "delivery takes me now": gap that raises the hours check
WEEKS_PER_MONTH = 52 / 12


class Stop(Exception):
    pass


# ------------------------------------------------------------------ reading what the founder typed
# Every number, amount, percentage, duration and weekday set goes through locale_numbers.py (Merigrove's
# shared reader, copied here unchanged). This module adds only the forms specific to this skill: "=" sums
# Claude writes from the founder's parts, hedges ("more like 40", "40+"), how often a step happens, how
# long a client stays, and hours a week given as a day and a week ("12 hr x 6 days").
STYLE = {"decimal": None}             # 'dot' or 'comma', detected once per run from what the founder typed
WORKING_DAYS = [WORKING_DAYS_WEEK_DEFAULT]  # the founder's working days a week, set per run
WORDNUM = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
           "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20,
           "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60}
HEDGES = r"\b(more like|closer to|nearer to|nearer|like|about|around|roughly|approx(imately)?|circa|c\.|maybe|say|or so|give or take|at least|at most|up to|nearly|almost|over|under|just|more than|less than|probably|easily|prob|lah|lol|call it|usually|typically|avg|average|on average)\b"
UNKNOWN = ("", "?", "na", "n/a", "unknown", "not sure", "dunno", "tbc", "skip", "no idea")
DAY_TOKEN = r"\b(mon|monday|tue|tues|tuesday|wed|weds|wednesday|thu|thur|thurs|thursday|fri|friday|sat|saturday|sun|sunday)s?\b"
_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.USub: operator.neg, ast.UAdd: operator.pos}


class Ask(Exception):
    """A value that reads two ways (locale_numbers.Ambiguous): collected, then asked as one question."""


def _safe_eval(expr):
    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return float(n.value)
        if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](ev(n.operand))
        raise ValueError("unsupported")
    return ev(ast.parse(expr, mode="eval"))


def num(tok, decimal=None):
    """One number through locale_numbers, in the founder's decimal style. Ambiguous becomes Ask."""
    try:
        return LN.parse_number(tok, decimal or STYLE["decimal"], allow_words=False)[0]
    except LN.Ambiguous as e:
        raise Ask(str(e))


def _clean(v):
    s = unicodedata.normalize("NFKC", str(v)).strip().lower()
    return s.replace("\u2013", "-").replace("\u2014", "-").replace("\u2212", "-").replace("\u00d7", "x")


def _words(s):
    """Number words to digits ('two hours', 'four and a half'); 'a', 'an', 'half' are left to locale_numbers."""
    for w in sorted(WORDNUM, key=len, reverse=True):
        s = re.sub(rf"\b{w}\b", str(WORDNUM[w]), s)
    s = re.sub(r"\b(\d+(?:[.,]\d+)?) and a half\b", lambda m: str(num(m.group(1)) + 0.5), s)
    return s


def _formula(expr, written_by_claude):
    """A sum: '=(2+2+1.5)/3' written by Claude from the founder's parts (dot decimals, no commas), or
    '2 + 0.5' typed by the founder (their own decimal style)."""
    if written_by_claude and "," in expr:
        raise ValueError("write '=' sums with a dot for decimals and no commas")
    style = "dot" if written_by_claude else None
    e = re.sub(r"\d[\d.,]*", lambda m: repr(num(m.group(0), style)), expr.replace("x", "*"))
    return _safe_eval(e)


def parse_hours(v):
    """Hours from what a founder types: 7.5hr, 90 mins, 1h30, half a day, 2 days, 1-2 hrs, 6 x 1.5, 7,5 Std.
    Returns (value or None, note or None). Unreadable or negative gives None with a note; a figure that
    reads two ways raises Ask."""
    if v is None:
        return None, None
    if isinstance(v, bool):
        return None, "not a number"
    if isinstance(v, (int, float)):
        return (float(v), None) if v >= 0 else (None, "negative hours")
    s = _clean(v)
    if s in UNKNOWN:
        return None, None
    if s in ("none", "nil", "nothing", "0", "zero", "no time"):
        return 0.0, None
    lead_eq = s.startswith("=")
    s = s.lstrip("=").strip()
    if lead_eq or (re.fullmatch(r"[\d.,\s+\-*/()x]+", s) and re.search(r"\d\s*[+*/]\s*[\d(]|\)\s*[*/]", s)):
        try:
            val = _formula(s, lead_eq)
        except Ask:
            raise
        except Exception as e:  # noqa: BLE001
            return None, f"could not work out '{v}' ({e})" if "dot" in str(e) else f"could not work out '{v}'"
        if val < 0:
            return None, f"'{v}' works out negative"
        return float(val), (f"worked out '{v}' as {fmt_h(val)}" if re.search(r"[+*/x]", s) else None)
    s = _words(s)
    plus = bool(re.search(r"\d\s*\+\s*(h|hr|hrs|hours?)?\s*$|\b(over|at least|more than)\s+\d", s))
    s = re.sub(r"(\d)\s*\+(?=\s*(h|hr|hrs|hours?)?\s*$)", r"\1", s)
    s = re.sub(r"(\d)\s*-?ish\b", r"\1", s)
    s = re.sub(HEDGES, " ", s)
    s = re.sub(r"[~≈?!]", " ", s)
    s = re.sub(r"\bbetween\s+([\d.,]+)\s+and\s+([\d.,]+)", r"\1 to \2", s)
    s = re.sub(r"\b(full|whole|entire|working|work|long|short)\s+(?=(day|days|week|weeks)\b)", "", s)
    s = re.sub(r"\bhalf-(day|hour)\b", r"half \1", s)
    s = re.sub(r"^\s*(day|week)\s*$", r"a \1", s)
    s = re.sub(r"(\d+)\s*(?:hrs?|hours?)\s*(\d{1,2})\s*(?:m|mins?|minutes?)?\b", r"\1h\2", s)
    s = re.sub(r"\b(per|a|each|every)\s+(client|month|week|time|session|project|call|go|one|build|job)\b", " ", s)
    s = re.sub(r"\b(pcm|pm|pw|p/w|/mo|/month|/wk|/week|all in|total|tops|max|each|incl\.?\s+\w+)\b", " ", s)
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.sub(r"[£$€¥₹₩₱฿,]\s*(?=\D|$)", " ", s) if not re.search(r"\d,\d", s) else s
    s = re.sub(r"\s+", " ", s).strip(" .")
    if not s:
        return None, f"could not read '{v}' as hours"
    two = re.fullmatch(r"(.+?)\s*[,;]?\s*\b(sometimes|occasionally|or even|other times|some weeks|some months|rarely)\b\s*(.+)", s)
    if two:  # '4 hrs, sometimes 5': between the usual figure and the one it sometimes takes
        lo, _a = parse_hours(two.group(1))
        unit = re.sub(r"^[\d.,\s]+", "", two.group(1)).strip()
        hi, _b = parse_hours(two.group(3) if re.search(r"[a-z]", two.group(3)) else f"{two.group(3)} {unit}".strip())
        if lo is not None and hi is not None:
            val = (lo + hi) / 2
            return val, f"read '{v}' as {fmt_h(val)}, between the usual {fmt_h(lo)} and the {fmt_h(hi)} it {two.group(2)} takes"
    try:
        val, lnotes = LN.parse_hours(s, day_hours=DAY_HOURS, week_days=WORKING_DAYS[0], decimal=STYLE["decimal"])
    except LN.Ambiguous as e:
        raise Ask(f"'{v}': {e}")
    except (LN.Unreadable, ValueError):
        figs = re.findall(r"\d+(?:[.,]\d+)?", s)
        mh = re.search(r"(\d+(?:[.,]\d+)?)\s*(h|hrs?|hours?|mins?|minutes?)\b", s)
        if len(figs) == 1 and mh:  # one figure with its unit inside a sentence: '6 hrs total across the builds'
            val = num(mh.group(1)) / (60 if mh.group(2).startswith("m") else 1)
            return val, f"read {fmt_h(val)} hours from '{v}'"
        return None, f"could not read '{v}' as hours"
    if val < 0:
        return None, f"'{v}' works out negative"
    if any(n.startswith("day =") or n.startswith("week =") for n in lnotes):
        _DAY_USED[0] = True
    note = None
    if any("midpoint" in n for n in lnotes):
        note = f"read '{v}' as {fmt_h(val)}, the middle of the range"
    elif any(n.endswith(" x") or " x " in n for n in lnotes):
        note = f"worked out '{v}' as {fmt_h(val)}"
    if plus:
        note = f"read '{v}' as {fmt_h(val)}, the least it could be"
    return float(val), note


def parse_count(v):
    """A count of clients or people: '11', 'about a dozen', '10-12' (middle, rounded down), '20+'."""
    if v is None:
        return None, None
    if isinstance(v, bool):
        return None, "not a number"
    if isinstance(v, (int, float)):
        return (float(v), None) if v >= 0 else (None, "negative count")
    s = _clean(v)
    if s in UNKNOWN:
        return None, None
    if s in ("none", "nil", "0", "zero", "no one", "nobody"):
        return 0.0, None
    s = re.sub(r"(\d)\s*-?ish\b", r"\1", s)
    s = re.sub(r"\b(half a dozen)\b", "6", s)
    s = re.sub(r"\b(a couple of|couple of|a couple|a few)\b", lambda m: "3" if "few" in m.group(0) else "2", s)
    s = _words(s)
    s = re.sub(HEDGES, " ", s)
    s = re.sub(r"\b(clients?|customers?|people|members?|accounts?|active|on it|on this|right now|now|currently|at the moment|"
               r"ongoing|live|running|in progress|projects?|builds?|a month|per month|pcm|total|in total)\b", " ", s)
    s = re.sub(r"[~+]", " ", s).strip(" .")
    m = re.fullmatch(r"(?:between\s+)?([\d.,]+)\s*(?:-|to|and|or)\s*([\d.,]+)", s)
    try:
        if m:
            val = math.floor((num(m.group(1)) + num(m.group(2))) / 2)
            return float(val), f"read '{v}' as {val}, the middle of the range rounded down"
        if re.fullmatch(r"[\d.,' ]+", s or "x"):
            return num(s), None
        val, _n = LN.parse_number(s, STYLE["decimal"])  # 'a dozen'
        return float(val), None
    except Ask:
        raise
    except (LN.Unreadable, LN.Ambiguous, ValueError):
        return None, f"could not read '{v}' as a number"


def parse_hours_week(v):
    """Hours a week: '25', '25hrs/wk', '4 days a week' (days at the founder's day), '12 hr x 6 days',
    '12 hours a day, 6 days a week', '6 days of 12 hours', '9 hours mon-sat', '30ish'."""
    if not isinstance(v, str):
        return parse_hours(v)
    s = _clean(v)
    if s.startswith("="):
        return parse_hours(s)
    s = _words(s)
    s = re.sub(r"(\d)\s*-?ish\b", r"\1", s)
    s2 = re.sub(HEDGES, " ", s)
    numre = r"(\d+(?:[.,]\d+)?)"
    hour = r"(?:h|hrs?|hours?)"
    # N hours a day, M days a week / N hr days, M days / N hr x M days
    m = re.search(numre + r"\s*" + hour + r"\s*(?:a|per|each|/)?\s*(?:-|\s)?days?\b.*?" + numre + r"\s*(?:working\s+)?days?\b", s2) \
        or re.search(numre + r"\s*" + hour + r"\s*(?:x|\*|,)\s*" + numre + r"\s*(?:working\s+)?days?\b", s2)
    if m:
        a, b = num(m.group(1)), num(m.group(2))
        return a * b, f"read '{v}' as {fmt_h(a)} hours a day x {fmt_h(b)} days = {fmt_h(a * b)} a week"
    # M days (a week) of / at / x N hours
    m = re.search(numre + r"\s*(?:working\s+)?days?\b(?:\s*(?:a|per)\s*week)?\s*(?:of|at|x|\*|,)?\s*" + numre + r"\s*" + hour + r"\b", s2)
    if m:
        a, b = num(m.group(1)), num(m.group(2))
        return a * b, f"read '{v}' as {fmt_h(a)} days x {fmt_h(b)} hours = {fmt_h(a * b)} a week"
    # N hours on a set of weekdays: '9 hours mon-sat'
    if re.search(DAY_TOKEN, s2) or re.search(r"\bweekdays?\b", s2):
        mh = re.search(numre + r"\s*" + hour + r"?\b", s2)
        try:
            days = LN.count_weekdays(s2)
        except LN.Unreadable:
            days = None
        if mh and days:
            a = num(mh.group(1))
            return a * days, f"read '{v}' as {fmt_h(a)} hours x {days} days = {fmt_h(a * days)} a week"
    s = re.sub(r"\b(a|per|each|every)\s+week\b|/\s*wk\b|/\s*week\b|\bpw\b|\bweekly\b|\bhours? of delivery\b|\bon delivery\b", " ", s)
    val, note = parse_hours(s)
    if val is None:  # one figure with its hours unit inside a sentence: 'sales, admin, invoices maybe 15 hrs'
        figs = re.findall(r"\d+(?:[.,]\d+)?", s)
        mh = re.search(numre + r"\s*" + hour + r"\b", s)
        if len(figs) == 1 and mh:
            val = num(mh.group(1))
            note = f"read {fmt_h(val)} hours a week from '{v}'"
    return val, note


SPAN_UNITS = [  # unit pattern, weeks per unit ('DAY' uses the days a week given)
    (r"weeks?|wks?", 1.0), (r"fortnights?", 2.0), (r"months?|mths?|mos?", WEEKS_PER_MONTH),
    (r"quarters?|qtrs?", 3 * WEEKS_PER_MONTH), (r"years?|yrs?", 52.0), (r"days?", "DAY"),
]


def _span_weeks(v, days_per_week, default_unit):
    """A length of time in weeks: '8 weeks', 'about a month', 'half a year', 'two quarters', 'a fortnight',
    '2-4 months', '25 days' (days at days_per_week). Returns (weeks or None, note, unit_seen)."""
    s = _clean(v)
    s = re.sub(r"\bhalf an? (year|month|week|quarter)\b", lambda m: f"0.5 {m.group(1)}", s)
    s = re.sub(r"\b(a|an|one)\s+(year|month|week|fortnight|quarter|day)\b", r"1 \2", s)
    s = re.sub(r"\b(a|one)\s+(couple)\s+of\b", "2", s)
    s = re.sub(r"\ba few\b", "3", s)
    s = _words(s)
    s = re.sub(r"(\d)\s*-?ish\b", r"\1", s)
    s = re.sub(HEDGES, " ", s)
    unit_pat = "|".join(p for p, _w in SPAN_UNITS)
    m = re.search(r"([\d.,]+)\s*(?:-|to)\s*([\d.,]+)\s*(" + unit_pat + r")?\b", s)
    if m:
        n = (num(m.group(1)) + num(m.group(2))) / 2
        unit = m.group(3) or ""
        rest = s[:m.start()] + s[m.end():]
        note = f"read '{v}' as {fmt_h(n)} {unit or default_unit}, the middle of the range"
    else:
        m = re.search(r"([\d.,]+)\s*(" + unit_pat + r")?\b", s)
        if not m:
            left = " ".join(w for w in re.findall(r"[a-z]+", s))
            return None, f"could not read '{v}' as a length of time" + (f" (the words '{left}')" if left else ""), ""
        n, unit = num(m.group(1)), m.group(2) or ""
        rest = s[:m.start()] + s[m.end():]
        note = None
    left = [w for w in re.findall(r"[a-z]+", rest) if w not in ("of", "and", "total", "in", "the", "so", "for", "s", "stay", "stays",
                                                                 "long", "on", "average", "each", "per", "client", "clients",
                                                                 "project", "projects", "booking", "delivery", "run", "runs", "to", "from",
                                                                 "until", "till", "start", "finish", "end", "about")]
    unit = unit or default_unit
    for pat, per in SPAN_UNITS:
        if re.fullmatch(pat, unit):
            weeks = n / days_per_week if per == "DAY" else n * per
            if left:
                note = (note + "; " if note else "") + f"ignored the words '{' '.join(left)}' in '{v}'"
            return weeks, note, unit
    return None, f"could not read '{v}' as a length of time", ""


def parse_months(v):
    """How long a client stays or a project runs, in months: '6 weeks', '3 months', 'a year', 'about a month',
    'half a year', 'two quarters', 'a fortnight'. Bare numbers are months."""
    if v is None or v == "":
        return None, None
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return (float(v), None) if v > 0 else (None, "must be above zero")
    try:
        weeks, note, _u = _span_weeks(v, 7.0, "months")
    except (LN.Unreadable, ValueError):
        return None, f"could not read '{v}' as a length of time"
    if weeks is None:
        return None, note
    val = weeks / WEEKS_PER_MONTH
    return (val, note) if val > 0 else (None, "must be above zero")


def parse_weeks_off(v, days_per_week):
    """Time off a year in weeks: '3 weeks', '25 days' (at the founder's working days a week), 'a month'."""
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v), None, "weeks"
    try:
        return _span_weeks(v, days_per_week, "weeks")
    except (LN.Unreadable, ValueError):
        return None, f"could not read '{v}' as time off", ""


def parse_pct(v):
    """'80%', '80', '0.8', '75 percent', '80,5 %' read as a share. Bare 1 asks (1 or 100 per cent?)."""
    if v is None or v == "":
        return None, None
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        x = float(v)
        sign = False
    else:
        sign = bool(re.search(r"%|per ?cent|pct", str(v), re.I))
        try:
            x, _n = LN.parse_percent(str(v), STYLE["decimal"])
        except LN.Ambiguous as e:
            raise Ask(str(e))
        except (LN.Unreadable, ValueError):
            return None, f"could not read '{v}' as a percentage"
    if not sign and x == 1:
        raise Ask(f"'{v}': 1 per cent or 100 per cent?")
    if sign or x > 1:
        x = x / 100
    if x <= 0 or x > 1:
        return None, f"'{v}' must be between 1 and 100 per cent"
    return x, None


PER_PERIOD = r"(?:/|\bper\b|\ba\b|\beach\b|\bevery\b)\s*(?:mth|mnth|month|mo|pcm|year|yr|annum|project|build|job|client|day|session|week|wk)\b|\bp/?m\b|\bpcm\b|\bmonthly\b"


PRICE_RANGES = {}  # raw price text -> (low, high), for a price the founder gave as a range


def parse_price(v):
    """A price before any sales tax: '$2,400', 'RM 18k-35k' (the middle, both ends kept), '1.200,50 €', '₹2.4 lakh', 'RM 800/mth'.
    Returns (amount or None, currency or None, affix (prefix, suffix), note)."""
    if v is None or v == "":
        return None, None, ("", ""), None
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v), None, ("", ""), None
    raw = unicodedata.normalize("NFKC", str(v)).strip()
    cur = LN.find_currency(raw)
    t = re.sub(PER_PERIOD, " ", raw, flags=re.I)
    t = re.sub(r"\b(before|excl\.?|excluding|plus|\+)\s*(any\s+)?(sales tax|vat|gst|tax)\b", " ", t, flags=re.I)
    t = re.sub(r"\(.*?\)", " ", t).strip()
    pre = re.match(r"^\s*([^\d\s~(-]{1,4})\s*\d", t)
    suf = re.search(r"\d[\d.,]*\s*(?:k|m|mn|lakh|crore)?\s*([€£¥₹₩₱฿]|zł|kr|Kč|[A-Z]{3})\s*$", t)
    affix = ((pre.group(1).strip() if pre and not re.fullmatch(r"(?i)about|around|c\.|ca", pre.group(1)) else ""),
             (suf.group(1) if suf else ""))
    note = None
    rng = re.match(r"^\s*(.*?\d[\d.,]*\s*(?:k|m|mn|lakh|lakhs|crore|万)?)\s*(?:-|to|\u2013)\s*(\D{0,4}\d.*)$", t, re.I)
    try:
        if rng:
            lo_s, hi_s = rng.group(1), rng.group(2)
            mult = re.search(r"(k|m|mn|lakh|lakhs|crore|万)\s*\D*$", hi_s, re.I)
            if mult and not re.search(r"(k|m|mn|lakh|lakhs|crore|万)\s*$", lo_s, re.I):
                lo_s = lo_s + mult.group(1)
            lo = LN.parse_number(lo_s, STYLE["decimal"])[0]
            hi = LN.parse_number(hi_s, STYLE["decimal"])[0]
            val = (lo + hi) / 2
            PRICE_RANGES[str(v)] = (float(min(lo, hi)), float(max(lo, hi)))
            note = (f"the price '{v}' is a range: what it pays for each hour of yours is shown at both ends; "
                    f"the workbook uses the middle, {fmt_num(val)}, until you give a typical price")
        else:
            val, lnotes = LN.parse_number(t, STYLE["decimal"])
            if any(n.startswith("x") for n in lnotes):
                note = f"read the price '{v}' as {fmt_num(val)}"
    except LN.Ambiguous as e:
        raise Ask(f"price '{v}': {e}")
    except (LN.Unreadable, ValueError):
        return None, cur, affix, f"could not read the price '{v}'"
    if val < 0:
        return None, cur, affix, f"the price '{v}' is negative"
    return float(val), cur, affix, note


FREQ_WORDS = [
    (r"\b(fortnightly|every two weeks|every 2 weeks|every other week|biweekly|bi-weekly|every fortnight|once a fortnight|each fortnight|a fortnight|per fortnight)\b", 26 / 12, "fortnightly"),
    (r"\b(weekly|every week|each week|once a week|a week|per week|1x a week|1 x a week)\b", WEEKS_PER_MONTH, "weekly"),
    (r"\b(quarterly|every quarter|every three months|every 3 months|once a quarter|a quarter|per quarter)\b", 1 / 3, "quarterly"),
    (r"\b(twice a year|every six months|every 6 months|half[- ]yearly|biannually)\b", 2 / 12, "twice a year"),
    (r"\b(yearly|annually|once a year|every year|a year|per year|annual)\b", 1 / 12, "yearly"),
    (r"\b(monthly|every month|each month|once a month|a month|per month|pcm|1x a month|1 x a month)\b", 1.0, "monthly"),
]
DAILY = r"\b(daily|every day|each day|every working day|each working day|every workday|a day|per day|each morning|every morning|every evening)\b"
ONCE_WORDS = r"\b(once|one[- ]off|one time|at the start|at the beginning|at the end|on signing|kick[- ]?off|per project|per client|each project|each client|per workshop|per event|per build|per job|start of|end of|onboarding|offboarding|setup|set up|handover)\b"


def parse_freq(v, months_on_offer, days_week=None):
    """Times per client per month. Returns (value or None, label, note, once_flag).
    'daily' and 'per day' use the founder's working days a week; 'every weekday' is Monday to Friday;
    'N days a week' and day ranges ('mon-sat') count those days."""
    wd = float(days_week or WORKING_DAYS[0])
    if v is None or v == "":
        return None, "", None, False
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return (float(v), f"{fmt_h(float(v))} a month", None, False) if v >= 0 else (None, "", "negative", False)
    raw = str(v).strip()
    s = _words(_clean(raw))
    s = re.sub(r"\btwice\b", "2 times", s)
    s = re.sub(r"\bthrice\b", "3 times", s)
    s = re.sub(r"\bonce\s+(a|per|every|each)\s+(?=(week|wk|month|mo|quarter|year|day|working day|fortnight)\b)", r"1 times \1 ", s)
    s = re.sub(HEDGES, " ", s).strip()
    numre = r"(\d+(?:[.,]\d+)?)"
    if re.search(r"\b(ad hoc|as needed|when needed|now and then|occasionally|sometimes|varies|on demand|whenever)\b", s):
        return None, raw, f"'{raw}' needs a rough figure: about how many times a month?", False
    if re.search(r"\d\s*(hours?|hrs?|h|mins?|minutes?)\b", s):
        return None, raw, f"'{raw}' gives time, not how often; put the time in hours and say how often it happens", False
    if re.search(r"\bevery\s+weekday\b|\bweekdays\b|\beach\s+weekday\b", s):
        return 5 * WEEKS_PER_MONTH, raw, f"read '{raw}' as Monday to Friday, 5 days a week", False
    if re.search(DAY_TOKEN, s):
        try:
            days = LN.count_weekdays(re.sub(r"\b(\w{3})(day)s?\b", r"\1", s))
        except LN.Unreadable:
            days = None
        if days:
            mt = re.search(numre + r"\s*(?:x|times)\b", s)
            k = num(mt.group(1)) if mt else 1.0
            return k * days * WEEKS_PER_MONTH, raw, f"read '{raw}' as {days} days a week", False
    m = re.search(numre + r"\s*(?:working\s+)?days?\s*(?:a|per|each|every|/|in a|of the)\s*(?:working\s+)?week\b", s)
    if m:
        n = num(m.group(1))
        return n * WEEKS_PER_MONTH, raw, None, False
    m = re.search(r"every\s+(other|\d+(?:[.,]\d+)?)\s*(working\s+)?(days?|weeks?|months?)", s)
    if m:
        n = 2.0 if m.group(1) == "other" else num(m.group(1))
        unit = m.group(3)
        if unit.startswith("d"):
            return wd * WEEKS_PER_MONTH / n, raw, f"read '{raw}' over your {fmt_h(wd)} working days a week", False
        val = (WEEKS_PER_MONTH / n) if unit.startswith("w") else 1 / n
        return val, raw, None, False
    m = re.search(numre + r"\s*(?:x|times|[a-z]+)?\s*(?:a|per|each|every|/)\s*(week|wk|month|mo|quarter|year|working day|day|fortnight)\b", s)
    if m:
        n, unit = num(m.group(1)), m.group(2)
        per = {"week": WEEKS_PER_MONTH, "wk": WEEKS_PER_MONTH, "month": 1, "mo": 1, "quarter": 1 / 3,
               "year": 1 / 12, "day": wd * WEEKS_PER_MONTH, "working day": wd * WEEKS_PER_MONTH,
               "fortnight": 26 / 12}[unit]
        note = f"read '{raw}' over your {fmt_h(wd)} working days a week" if "day" in unit else None
        return n * per, raw, note, False
    m = re.search(numre + r"\s*(?:x|times|[a-z]+)?\s*(?:per|a|each|over the|in the)?\s*(project|client|engagement|programme|program|build|job|workshop|event|course|cohort)", s)
    if m:
        return num(m.group(1)) / months_on_offer, raw, None, True
    if re.search(DAILY, s):
        return wd * WEEKS_PER_MONTH, raw, f"read '{raw}' as each of your {fmt_h(wd)} working days a week", False
    for pat, val, _lab in FREQ_WORDS:
        if re.search(pat, s):
            return val, raw, None, False
    if re.search(ONCE_WORDS, s):
        return 1 / months_on_offer, raw, None, True
    m = re.fullmatch(numre + r"\s*(x|times)?", s.strip())
    if m:
        return num(m.group(1)), raw, f"read '{raw}' as {m.group(1)} times a month", False
    return None, raw, f"could not read how often '{raw}' happens", False


def detect_style(data):
    """The founder's decimal style, once, from every figure they typed (never the '=' sums Claude writes).
    Returns (style or None, source). Raises Ask when their figures disagree."""
    given = str(data.get("number_style") or "").strip().lower()
    if given:
        if given in ("dot", "point", "period", "1,234.56", "."):
            return "dot", "founder said"
        if given in ("comma", "1.234,56", ","):
            return "comma", "founder said"
        raise Stop(f"number_style '{data.get('number_style')}' should be dot or comma")
    samples = []
    keys = ("hours", "how_often", "active_clients", "months_per_client", "hours_week", "delivery_hours_week",
            "delivery_hours_month", "working_hours_week", "selling_admin_hours_week", "delivery_hours_now_week",
            "weeks_off_year", "working_weeks_year", "day_hours", "check_hours_after", "price",
            "target_working_hours_week", "target_delivery_hours_week")

    def walk(o):
        if isinstance(o, dict):
            for k, x in o.items():
                if k in keys and isinstance(x, str) and not x.strip().startswith("="):
                    samples.append(x)
                elif isinstance(x, (dict, list)):
                    walk(x)
        elif isinstance(o, list):
            for x in o:
                walk(x)
    walk({k: v for k, v in data.items() if k not in ("sources",)})
    votes = {LN.detect_decimal_style([x]) for x in samples} - {None}
    if len(votes) == 2:
        dots = [x for x in samples if LN.detect_decimal_style([x]) == "dot"][:2]
        commas = [x for x in samples if LN.detect_decimal_style([x]) == "comma"][:2]
        raise Ask(f"some figures use a dot for decimals ({', '.join(dots)}) and some a comma ({', '.join(commas)}); "
                  "which do you use?")
    return (votes.pop() if votes else None), "read from how you write numbers"


FOUNDER_WORDS = {"me", "i", "myself", "founder", "you", "the founder", "owner", "me (founder)", "self", "mine", "me myself"}
TOOL_WORDS = r"\b(tool|automation|automated|zapier|make\.com|software|system|auto|template|app|crm|calendly|scheduler)\b"


def owner_of(v):
    if v is None or str(v).strip() == "":
        return "you", True, "not given; read as you"
    s = str(v).strip()
    low = s.lower()
    if low in FOUNDER_WORDS or re.fullmatch(r"(me|i|myself|founder|you)( mostly| usually| for now| at the moment)?", low):
        return "you", True, None
    if re.search(r"\b(me|myself|founder)\b", low) and re.search(r"\b(and|with|\+|&)\b", low):
        return "you", True, f"'{s}' is shared; counted as you until someone else does all of it"
    return s, False, None


def flag_of(v):
    if v is None:
        return None
    s = str(v).strip().lower()
    if s in ("f", "founder", "founder only", "founder-only", "only me", "me only"):
        return "F"
    if s in ("w", "founder until written", "until written", "written", "write it down", "needs writing"):
        return "W"
    if s in ("t", "team", "tool", "team or tool", "hand over now", "handover now", "ready"):
        return "T"
    return None


# Quality checks: an unambiguous check of the work is counted F whatever flag it was given (flag-rules section 3).
# A weaker word ("review", "approve", "feedback") is only a quality check when the step has no flag yet;
# on a step the founder flagged W or T it raises a question instead of overriding them.
GATE_STRONG = re.compile(r"\b(qa|quality (check|gate|control|review)|final check|check(ing)? (the |over |before |of the )?(work|draft|drafts|output|deliverable)|"
                         r"check before|checks? before|sign[- ]?off|signing off|proof ?read(ing)?|proofing|edit pass|pre-?flight|"
                         r"review(ing|s)? (the |of the |all |every |their )?(work|drafts?|output|deliverables?|edits|files|copy|designs?|posts?|content)|"
                         r"review\w*\b[^.]{0,40}\bbefore (it goes|delivery|sending|the client|they|launch|go-live|publishing))\b", re.I)
GATE_WEAK = re.compile(r"\b(review|reviews|reviewing|approv(e|al|ing)|check(ing)? over)\b", re.I)
NOT_GATE = re.compile(r"\bcheck[- ]?ins?\b|\bwith (the )?clients?\b|\bclient feedback\b|\bbusiness review\b|\breviews? (call|meeting)s?\b|"
                      r"\btimesheets?\b|\breview (their |the client'?s? )?feedback\b|\bperformance review\b|\bannual review\b|\b(google|online|customer) reviews?\b", re.I)


def gate_kind(step, flag):
    """'yes' (counted F), 'ask' (a NOTE asks the founder), or '' (not a quality check)."""
    g = step.get("gate")
    if isinstance(g, bool):
        return "yes" if g else ""
    if isinstance(g, str) and g.strip():
        return "yes" if g.strip().lower() in ("yes", "y", "true", "1") else ""
    name = str(step.get("step", ""))
    if NOT_GATE.search(name):
        return ""
    if GATE_STRONG.search(name):
        return "yes"
    if GATE_WEAK.search(name):
        return "yes" if flag in (None, "F") else "ask"
    return ""


def is_gate(step):
    return gate_kind(step, flag_of(step.get("flag"))) == "yes"


# ------------------------------------------------------------------ formatting
def _styled(s):
    """Write a dot-style figure back in the founder's own style (1,234.5 or 1.234,5)."""
    if STYLE["decimal"] == "comma":
        return s.replace(",", "\x00").replace(".", ",").replace("\x00", ".")
    return s


def fmt_h(x):
    if x is None:
        return "?"
    if abs(x - round(x)) < 0.005 or (abs(x) >= 1 and abs(x - round(x)) < 0.05):
        return _styled(f"{int(round(x)):,}")
    if abs(x) < 1:
        return _styled(f"{x:.2f}")
    return _styled(f"{x:,.1f}")


fmt_num = fmt_h


def fmt_pct(x, line=None):
    """A share as a whole per cent; one decimal when rounding would put it on the wrong side of a line."""
    p = x * 100
    if line is not None and round(p) == round(line * 100) and abs(p - line * 100) > 1e-9:
        q = math.floor(p * 10) / 10 if p < line * 100 else math.ceil(p * 10) / 10
        return _styled(f"{q:.1f}%")
    return f"{round(p):.0f}%"


def fmt_money(x, affix=("", "")):
    if x is None:
        return "?"
    pre, suf = affix
    body = _styled(f"{x:,.0f}") if abs(x) >= 100 else _styled(f"{x:,.2f}")
    if pre:
        return f"{pre}{'' if len(pre) <= 2 and not pre.isalpha() else ' '}{body}"
    return f"{body} {suf}" if suf else body


BRANDS = {"google", "xero", "quickbooks", "shopify", "wordpress", "instagram", "linkedin", "facebook", "meta", "tiktok",
          "youtube", "canva", "notion", "slack", "zoom", "figma", "wordfence", "bukku", "stripe", "calendly", "mailchimp",
          "hubspot", "asana", "trello", "dropbox", "gmail", "outlook", "excel", "elementor", "webflow", "squarespace",
          "wix", "klaviyo", "pinterest", "lightroom", "photoshop", "capcut", "skool", "kajabi", "teachable", "circle",
          "voxer", "loom", "airtable", "zapier", "sage", "freeagent", "myob", "ga4", "seo"}
PROPER = set()   # helper, offer, tool and business names for this run, set in normalise


def lc(name):
    """A step name mid-sentence: lower-case its first letter unless the first word is all capitals, has a
    capital inside it, or is a name (a helper, an offer, a tool or a known product)."""
    s = str(name)
    words = s.split()
    if not words:
        return s
    first = words[0]
    core = re.sub(r"[^\w'-]", "", first)
    if len(core) < 2 or not core[0].isupper():
        return s
    if core.isupper() or any(ch.isupper() for ch in core[1:]):
        return s
    low = re.sub(r"'s?$", "", core.lower())
    if low in BRANDS or low in PROPER:
        return s
    return s[0].lower() + s[1:]


def plural(n, one, many=None):
    return one if n == 1 else (many or one + "s")


def long_date(iso, order="DMY"):
    """The month in words, in the founder's country's date order (locale_numbers.locale_defaults):
    'October 20, 2026' month first, '20 October 2026' day first, '2026-10-20' year first."""
    try:
        d = date.fromisoformat(str(iso)[:10])
    except ValueError:
        return str(iso)
    month = d.strftime("%B")
    if order not in ("MDY", "DMY", "YMD"):  # a locale code such as en-US: the date order of its country
        order = LN.locale_defaults(str(order).split("-")[-1] if order else "")["date_order"]
    if order == "MDY":
        return f"{month} {d.day}, {d.year}"
    if order == "YMD":
        return d.isoformat()
    return f"{d.day} {month} {d.year}"


# The founder's country, from a code, a name, a demonym or a city they mention. Paper size and date order
# follow the country (locale_numbers.locale_defaults), never their spelling. Not a lookup of any rule.
COUNTRY_WORDS = {
    "united states": "US", "usa": "US", "u.s.": "US", "america": "US", "american": "US",
    "united kingdom": "GB", "uk": "GB", "britain": "GB", "british": "GB", "england": "GB", "english": "GB",
    "scotland": "GB", "scottish": "GB", "wales": "GB", "welsh": "GB", "northern ireland": "GB",
    "ireland": "IE", "irish": "IE", "australia": "AU", "australian": "AU", "aussie": "AU",
    "new zealand": "NZ", "kiwi": "NZ", "canada": "CA", "canadian": "CA", "singapore": "SG", "singaporean": "SG",
    "malaysia": "MY", "malaysian": "MY", "philippines": "PH", "filipino": "PH", "filipina": "PH", "pinoy": "PH",
    "india": "IN", "indian": "IN", "pakistan": "PK", "pakistani": "PK", "bangladesh": "BD", "sri lanka": "LK",
    "hong kong": "HK", "china": "CN", "chinese": "CN", "japan": "JP", "japanese": "JP", "korea": "KR",
    "south korea": "KR", "korean": "KR", "taiwan": "TW", "thailand": "TH", "thai": "TH", "vietnam": "VN",
    "indonesia": "ID", "indonesian": "ID", "south africa": "ZA", "south african": "ZA", "nigeria": "NG",
    "nigerian": "NG", "kenya": "KE", "kenyan": "KE", "ghana": "GH", "egypt": "EG", "uae": "AE",
    "united arab emirates": "AE", "emirati": "AE", "saudi arabia": "SA", "saudi": "SA", "israel": "IL",
    "germany": "DE", "german": "DE", "france": "FR", "french": "FR", "spain": "ES", "spanish": "ES",
    "italy": "IT", "italian": "IT", "netherlands": "NL", "dutch": "NL", "belgium": "BE", "switzerland": "CH",
    "swiss": "CH", "austria": "AT", "sweden": "SE", "swedish": "SE", "norway": "NO", "denmark": "DK",
    "danish": "DK", "finland": "FI", "poland": "PL", "polish": "PL", "portugal": "PT", "portuguese": "PT",
    "greece": "GR", "czechia": "CZ", "czech republic": "CZ", "romania": "RO", "hungary": "HU", "turkey": "TR",
    "mexico": "MX", "mexican": "MX", "brazil": "BR", "brazilian": "BR", "argentina": "AR", "chile": "CL",
    "colombia": "CO", "peru": "PE", "puerto rico": "PR",
    # cities founders name
    "kl": "MY", "kuala lumpur": "MY", "penang": "MY", "johor bahru": "MY", "manila": "PH", "cebu": "PH",
    "nyc": "US", "new york": "US", "la": "US", "los angeles": "US", "sf": "US", "san francisco": "US",
    "chicago": "US", "austin": "US", "denver": "US", "seattle": "US", "boston": "US", "miami": "US",
    "toronto": "CA", "vancouver": "CA", "montreal": "CA", "london": "GB", "manchester": "GB", "edinburgh": "GB",
    "dublin": "IE", "sydney": "AU", "melbourne": "AU", "brisbane": "AU", "perth": "AU", "auckland": "NZ",
    "wellington": "NZ", "mumbai": "IN", "bangalore": "IN", "bengaluru": "IN", "delhi": "IN", "tokyo": "JP",
    "osaka": "JP", "seoul": "KR", "shanghai": "CN", "beijing": "CN", "jakarta": "ID", "bangkok": "TH",
    "dubai": "AE", "abu dhabi": "AE", "johannesburg": "ZA", "cape town": "ZA", "lagos": "NG", "nairobi": "KE",
    "berlin": "DE", "munich": "DE", "paris": "FR", "madrid": "ES", "barcelona": "ES", "amsterdam": "NL",
    "lisbon": "PT", "stockholm": "SE", "warsaw": "PL", "zurich": "CH", "milan": "IT", "rome": "IT",
    "mexico city": "MX", "sao paulo": "BR", "são paulo": "BR",
}
AMERICAN_ENGLISH = {"en-us", "us", "american", "american english", "usa"}


def read_country(v):
    """Returns (ISO code or '', what was given). '' with a value given means not recognised (never a STOP)."""
    s = str(v or "").strip()
    low = re.sub(r"\s+", " ", s.lower().replace("_", "-")).strip(" .")
    if not low:
        return "", ""
    if low in COUNTRY_WORDS:
        return COUNTRY_WORDS[low], s
    m = re.fullmatch(r"(?:[a-z]{2}-)?([a-z]{2})", low)
    if m and m.group(1) not in ("kl", "la", "sf"):
        return m.group(1).upper(), s
    for part in re.split(r"[,/]| in ", low):
        part = part.strip()
        if part in COUNTRY_WORDS:
            return COUNTRY_WORDS[part], s
    return "", s


def slug(s):
    s = re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")
    return s[:40] or "your-business"


# ------------------------------------------------------------------ normalise
BUSINESS = "Business-wide"
BUSINESS_WORDS = ("business", "business-wide", "business wide", "whole business", "the business", "overhead",
                  "overheads", "all clients at once", "team")
SUSTAIN_WORKING = 50     # working hours a week above which the skill asks what week the founder wants
SUSTAIN_DELIVERY = 45    # delivery hours a week above which the reading says the ceiling assumes it is kept up
HOURS_GAP_STOP = 0.30    # steps short of what delivery takes by more than this: stop and ask before building


def normalise(data):
    if not isinstance(data, dict):
        raise Stop("the inputs file must be one JSON object with offers and steps")
    offers_in = data.get("offers")
    steps_in = data.get("steps")
    if not isinstance(offers_in, list) or not offers_in:
        raise Stop("the inputs file has no offers list. Add at least one offer with its name and active clients")
    if not isinstance(steps_in, list) or not steps_in:
        raise Stop("the inputs file has no steps list. Add the delivery steps, each with its offer, hours and how often")
    needs, notes, assumptions, asks = [], [], [], []
    src = data.get("sources") or {}
    if not isinstance(src, dict):
        src = {}
    confirmed = {str(x).strip().lower() for x in (data.get("confirmed") or [])} if isinstance(data.get("confirmed"), list) else set()

    def read(fn, *args, field=""):
        """Run one reader; a value that reads two ways is collected for one question, never guessed."""
        try:
            return fn(*args)
        except Ask as e:
            asks.append(f"{field}: {e}" if field else str(e))
            if fn is parse_freq:
                return None, "", "ASK", False
            if fn is parse_price:
                return None, None, ("", ""), "ASK"
            if fn is parse_weeks_off:
                return None, "ASK", ""
            return None, "ASK"

    biz = {"business": str(data.get("business") or "Your business").strip(),
           "date": str(data.get("date") or date.today().isoformat())[:10], "confirmed": sorted(confirmed)}
    try:
        date.fromisoformat(biz["date"])
    except ValueError:
        raise Stop(f"the date '{biz['date']}' is not YYYY-MM-DD")

    # number style, once, from what the founder typed
    try:
        STYLE["decimal"], biz["style_src"] = detect_style(data)
    except Ask as e:
        STYLE["decimal"], biz["style_src"] = None, "not known"
        asks.append(str(e))
    biz["number_style"] = STYLE["decimal"]

    # the founder's country (paper, date order) and English (spelling): never one from the other's spelling
    country, c_raw = read_country(data.get("country"))
    c_src = src.get("country", "from what you mentioned") if country else ""
    loc_raw = str(data.get("locale") or "").strip()
    english = str(data.get("english") or "").strip()
    if not country and loc_raw:
        lc_country, _r = read_country(loc_raw.split("-")[-1] if "-" in loc_raw else loc_raw)
        if lc_country:
            country, c_src = lc_country, src.get("locale", "from what you mentioned")
    if c_raw and not read_country(c_raw)[0]:
        assumptions.append(f"could not tell a country from '{c_raw}', so the page is A4 with the day before the month; "
                           "say your country to change it")
    if not english and loc_raw:
        english = loc_raw
    american = english.strip().lower() in AMERICAN_ENGLISH or (not english and country == "US")
    biz["country"], biz["country_src"] = country, c_src
    biz["english"] = "American" if american else ("British" if not english else english)
    biz["locale"] = "en-US" if american else (f"en-{country}" if country else "")
    d = LN.locale_defaults(country)
    biz["paper"] = d["paper"].lower()
    biz["date_order"] = d["date_order"]
    paper = str(data.get("paper") or "").strip().lower()
    if paper:
        if paper not in ("a4", "letter", "us letter"):
            raise Stop(f"paper '{data.get('paper')}' should be A4 or Letter")
        biz["paper"] = "letter" if "letter" in paper else "a4"
    if not country:
        assumptions.append("your country is not known, so the page is A4 with the day before the month; "
                           "say where you are based and it will follow your country")
    if not english and not country:
        assumptions.append("English style not given, so British spelling; say if you write American English and it will switch")

    # the founder's working day and week: set before any hours are read
    global DAY_HOURS
    dhrs, n = read(parse_hours, re.sub(r"\b(a|per|each)\s+day\b|/\s*day\b", " ", str(data.get("day_hours")).lower())
                   if data.get("day_hours") not in (None, "") else None, field="day_hours")
    if n and n != "ASK" and dhrs is None:
        raise Stop(f"day_hours: {n}. Ask the founder how many hours a normal working day is")
    if dhrs is not None and not 2 <= dhrs <= 16:
        raise Stop(f"a {fmt_h(dhrs)}-hour working day is outside 2 to 16; check the figure")
    DAY_HOURS = float(dhrs) if dhrs is not None else DAY_HOURS_DEFAULT
    biz["day_hours"], biz["day_hours_src"] = DAY_HOURS, ("founder said" if dhrs is not None else "default")
    _DAY_USED[0] = False
    wdw_raw = data.get("working_days_week")
    wdw, n = None, None
    if wdw_raw not in (None, ""):
        wtext = str(wdw_raw).lower()
        if re.search(DAY_TOKEN, wtext) or re.search(r"\bweekdays?\b", wtext):
            try:
                wdw = float(LN.count_weekdays(re.sub(r"\b(\w{3})(day)s?\b", r"\1", wtext)))
                notes.append(f"read working days '{wdw_raw}' as {fmt_h(wdw)} days a week")
            except LN.Unreadable as e:
                raise Stop(f"working_days_week: {e}")
        else:
            wdw, n = read(parse_count, re.sub(r"\b(working )?days?\b|\b(a|per|each) week\b", " ", wtext), field="working_days_week")
            if n and n != "ASK" and wdw is None:
                raise Stop(f"working_days_week: {n}")
    if wdw is not None and not 1 <= wdw <= 7:
        raise Stop(f"{fmt_h(wdw)} working days a week is outside 1 to 7; check the figure")
    WORKING_DAYS[0] = float(wdw) if wdw is not None else float(WORKING_DAYS_WEEK_DEFAULT)
    biz["working_days_week"] = WORKING_DAYS[0]
    biz["working_days_src"] = "founder said" if wdw is not None else "default"

    ww, n = read(parse_count, data.get("working_weeks_year"), field="working_weeks_year")
    off_raw = data.get("weeks_off_year")
    if ww is None and off_raw not in (None, ""):
        n_off, n_note, unit = read(parse_weeks_off, off_raw, WORKING_DAYS[0], field="weeks_off_year")
        if n_off is None and n_note != "ASK":
            raise Stop(f"weeks_off_year: {n_note or 'could not read ' + repr(off_raw)}. Ask how many weeks a year the founder takes off, holidays included")
        if n_off is not None:
            if unit.startswith("d") and wdw is None:
                assumptions.append(f"days off turned into weeks at {WORKING_DAYS_WEEK_DEFAULT} working days a week; "
                                   "give your own working week to change it")
            if n_note and n_note != "ASK":
                notes.append(f"time off: {n_note}")
            if not 0 <= n_off <= 32:
                raise Stop(f"{fmt_h(n_off)} weeks off a year is outside 0 to 32; check the figure (read from '{off_raw}')")
            ww = 52 - n_off
            biz["weeks_src"] = f"52 less {fmt_h(n_off)} weeks off, {src.get('weeks_off_year', 'founder said')}"
    if ww is None:
        ww = float(WORKING_WEEKS_DEFAULT)
        biz["weeks_src"] = "default"
        assumptions.append(f"{WORKING_WEEKS_DEFAULT} working weeks a year: 52 less six weeks off for holidays, public holidays "
                           "and sick days, a planning default; give your own time off to change it")
    elif "weeks_src" not in biz:
        biz["weeks_src"] = src.get("working_weeks_year", "founder said")
    if not 20 <= ww <= 52:
        raise Stop(f"{fmt_h(ww)} working weeks a year is outside 20 to 52; check the figure")
    biz["working_weeks_year"] = ww

    # available delivery hours: today's week, and the week the founder wants when they give one
    def week_field(key, label):
        raw = data.get(key)
        v, nn = read(parse_hours_week, raw, field=key)
        if nn and nn != "ASK" and v is None:
            raise Stop(f"{key}: {nn}. Ask the founder {label}")
        if v is not None and v > 100:
            raise Stop(f"{key}: I read '{raw}' as {fmt_h(v)} hours a week ({nn or 'as written'}), more than anyone works. "
                       f"Check the figure with the founder: {label}")
        if nn and nn != "ASK" and v is not None:
            notes.append(f"{key}: {nn}")
        return v

    dm, nm = read(parse_hours, data.get("delivery_hours_month"), field="delivery_hours_month")
    if nm and nm != "ASK" and dm is None:
        raise Stop(f"delivery_hours_month: {nm}. Ask the founder how many hours a month they can give to delivery")
    dh = week_field("delivery_hours_week", "how many hours a week they can give to delivery")
    wh = week_field("working_hours_week", "how many hours a week they work in total")
    sa = week_field("selling_admin_hours_week", "how many hours a week go on selling, admin and marketing")
    biz["working_hours_week"], biz["selling_admin_hours_week"] = wh, sa
    if dm is not None and dh is None:
        if dm <= 0:
            raise Stop("delivery hours a month must be above zero")
        dh = dm * 12 / ww
        biz["delivery_hours_src"] = f"worked out from {fmt_h(dm)} a month over {fmt_h(ww)} working weeks"
    if dh is None and wh is not None:
        if sa is not None:
            dh = wh - sa
            if dh <= 0:
                raise Stop("selling and admin take all the working hours given, which leaves nothing for delivery. Ask the founder again")
            biz["delivery_hours_src"] = f"worked out: {fmt_h(wh)} working hours less {fmt_h(sa)} on selling and admin"
        else:
            needs.append(f"delivery hours: the founder gave {fmt_h(wh)} working hours a week but not how many go on selling and admin. "
                         f"Ask: how many of those are selling, admin and marketing? Until then the default of {DELIVERY_HOURS_WEEK_DEFAULT} is used")
    if dh is None:
        dh = float(DELIVERY_HOURS_WEEK_DEFAULT)
        biz["delivery_hours_src"] = "default"
        if not any(x.startswith("delivery hours") for x in needs):
            needs.append(f"delivery hours: not given, so the planning default of {DELIVERY_HOURS_WEEK_DEFAULT} a week is used. "
                         "The ceiling moves in step with this figure; ask the founder for theirs")
    else:
        biz.setdefault("delivery_hours_src", src.get("delivery_hours_week", "founder said"))
    if dh <= 0:
        raise Stop("delivery hours a week must be above zero")
    if dh > 100:
        raise Stop(f"{fmt_h(dh)} delivery hours a week is more than anyone can sustain; check the figure with the founder (did they give a month?)")
    today_dh = dh
    tw = week_field("target_working_hours_week", "what week they want to be working, in hours")
    td = week_field("target_delivery_hours_week", "how many delivery hours a week they want to be working")
    target = None
    if td is not None:
        target, biz["target_src"] = td, src.get("target_delivery_hours_week", "the delivery week you want")
    elif tw is not None:
        if sa is None:
            needs.append("the week you want: the founder gave the hours they want to work but not how many go on selling and admin; "
                         "until they do, the ceiling uses today's week")
        else:
            target = tw - sa
            if target <= 0:
                raise Stop("selling and admin take all of the week the founder wants to work. Ask the founder again")
            biz["target_src"] = f"the {fmt_h(tw)}-hour week you want, less {fmt_h(sa)} on selling and admin"
    biz["target_working_week"] = tw
    biz["today_delivery_hours_week"] = today_dh
    if target is not None:
        dh = target
        biz["delivery_hours_src"] = biz["target_src"]
    biz["target"] = target is not None
    over_week = (wh is not None and wh > SUSTAIN_WORKING) or (wh is None and today_dh > SUSTAIN_DELIVERY)
    biz["long_week"] = bool(over_week and target is None)
    if biz["long_week"]:
        what = f"{fmt_h(wh)}-hour weeks" if wh is not None else f"{fmt_h(today_dh)} delivery hours a week"
        needs.append(f"the week you want: the ceiling takes your {what} as the plan. Ask once: what week do you want to be working? "
                     "Pass it as target_working_hours_week and the ceiling moves to it, with today's week shown beside it")
    elif target is None and today_dh > SUSTAIN_DELIVERY:
        notes.append(f"{fmt_h(today_dh)} delivery hours a week is a lot to sustain on top of selling and admin; the ceiling assumes the founder keeps it up")
    biz["delivery_hours_week"] = dh

    now, n = read(parse_hours_week, data.get("delivery_hours_now_week"), field="delivery_hours_now_week")
    if n and n != "ASK" and now is None:
        needs.append(f"delivery hours now: {n}; the hours check is skipped")
    elif n and n != "ASK":
        notes.append(f"delivery hours now: {n}")
    biz["delivery_hours_now_week"] = now
    if now is not None and now > 120:
        raise Stop(f"{fmt_h(now)} hours a week on delivery now is more than a week holds; check the figure")

    pl, n = read(parse_pct, data.get("helper_planning_line"), field="helper_planning_line")
    if n and n != "ASK":
        raise Stop(f"helper_planning_line: {n}")
    biz["plan_line"] = pl if pl is not None else HELPER_PLAN_LINE_DEFAULT
    biz["plan_line_src"] = "founder said" if pl is not None else "planning assumption"
    ll, n = read(parse_pct, data.get("helper_low_line"), field="helper_low_line")
    if n and n != "ASK":
        raise Stop(f"helper_low_line: {n}")
    biz["low_line"] = ll if ll is not None else HELPER_LOW_LINE_DEFAULT
    if biz["low_line"] >= biz["plan_line"]:
        raise Stop("the helper low line must sit below the planning line")
    hc, _n = read(parse_count, data.get("handover_count"), field="handover_count")
    biz["handover_count"] = int(hc) if hc else HANDOVER_COUNT_DEFAULT
    lead = str(data.get("lead") or "").strip().lower()
    if lead and lead not in LEAD_BLOCKS:
        notes.append(f"lead '{data.get('lead')}' not read; use one of {', '.join(LEAD_BLOCKS)}. The page keeps its usual order")
        lead = ""
    biz["lead"] = lead

    # offers
    offers, names, currencies = [], {}, {}
    for i, o in enumerate(offers_in):
        if not isinstance(o, dict):
            raise Stop(f"offer {i + 1} is not an object with a name")
        name = str(o.get("name") or "").strip()
        if not name:
            raise Stop(f"offer {i + 1} has no name")
        if name.lower() in names:
            raise Stop(f"two offers are called '{name}'. Give each a different name")
        if name.lower() in BUSINESS_WORDS or name == BUSINESS:
            raise Stop(f"'{name}' is the name used for business-wide steps; give the offer another name")
        billing = str(o.get("billing") or "monthly").strip().lower()
        billing = "one-off" if re.search(r"one|project|off|single|fixed|package", billing) else "monthly"
        ac, n = read(parse_count, o.get("active_clients"), field=f"{name} active clients")
        if n and n != "ASK" and ac is None:
            needs.append(f"{name}: {n}")
        if ac is None and n != "ASK":
            needs.append(f"{name}: active clients not given, so its load and room are not worked out. Ask how many clients are on it now")
        elif n and n != "ASK":
            notes.append(f"{name}: {n}")
        if ac is not None and ac != int(ac):
            notes.append(f"{name}: {fmt_h(ac)} active clients read as {int(ac)}")
            ac = float(int(ac))
        if ac is not None and ac > 1000:
            raise Stop(f"{name}: I read {fmt_h(ac)} active clients from '{o.get('active_clients')}'; check the figure with the founder")
        mo, n = read(parse_months, o.get("months_per_client"), field=f"{name} months a client stays")
        mo_src = "founder said"
        if mo is None:
            mo = float(MONTHS_ON_ONE_OFF_DEFAULT if billing == "one-off" else MONTHS_ON_MONTHLY_DEFAULT)
            if n and n != "ASK":
                mo_src = "unread"
                needs.append(f"{name}: {n}. Until the founder says how long a client stays, once-per-client steps are spread over "
                             f"{fmt_h(mo)} {plural(mo, 'month')}")
            else:
                mo_src = "default"
        elif n:
            notes.append(f"{name}: {n}")
        price, cur, affix, pn = read(parse_price, o.get("price"), field=f"{name} price")
        if pn and pn != "ASK" and price is None:
            needs.append(f"{name}: {pn}")
        elif pn and pn != "ASK":
            notes.append(f"{name}: {pn}")
        rng = PRICE_RANGES.get(str(o.get("price"))) if price is not None else None
        if rng and rng[0] != rng[1]:
            needs.append(f"{name} price: you gave a range ({o.get('price')}), so what it pays for each hour of yours is shown at "
                         "both ends; give a typical price to narrow it")
        else:
            rng = None
        if price is not None:
            currencies[name] = (cur, affix)
        off = {"name": name, "billing": billing, "active": ac, "months": mo, "months_src": mo_src,
               "active_raw": o.get("active_clients"), "months_raw": o.get("months_per_client"),
               "price": price, "price_raw": o.get("price"), "affix": affix, "price_range": rng,
               "price_month": (price if billing == "monthly" else price / mo) if price is not None else None}
        offers.append(off)
        names[name.lower()] = off
    curs = {c for c, _a in currencies.values() if c}
    if len(curs) > 1:
        raise Stop("the prices are in different currencies (" + ", ".join(f"{k}: {v[0]}" for k, v in currencies.items()) +
                   "). Ask the founder for every price in one currency")
    biz["affix"] = next((a for _c, a in currencies.values() if a != ("", "")), ("", ""))
    for off in offers:
        if off["price"] is not None and off["affix"] == ("", ""):
            off["affix"] = biz["affix"]
    biz["priced"] = bool(currencies)

    # helpers
    helpers = []
    for h in data.get("helpers") or []:
        if not isinstance(h, dict) or not str(h.get("name") or "").strip():
            raise Stop("each helper needs a name (for example 'Priya, VA')")
        hw, n = read(parse_hours_week, h.get("hours_week"), field=f"helper {h.get('name')} hours a week")
        if n and n != "ASK" and hw is None:
            raise Stop(f"helper {h.get('name')}: {n}")
        if hw is not None and hw > 80:
            raise Stop(f"helper {h.get('name')}: {fmt_h(hw)} hours a week; check the figure")
        if hw is None and n != "ASK":
            needs.append(f"helper {h.get('name')}: paid hours a week not given, so their room is not worked out")
        helpers.append({"name": str(h["name"]).strip(), "kind": str(h.get("kind") or "").strip(), "hours_week": hw})

    PROPER.clear()
    for nm_ in [h["name"] for h in helpers] + [o["name"] for o in offers] + [biz["business"]] + \
               [str(st.get("handover_to") or "") for st in steps_in if isinstance(st, dict)] + \
               [str(st.get("owner") or "") for st in steps_in if isinstance(st, dict)]:
        for w in re.findall(r"[A-Za-z][\w'-]*", nm_):
            if w[0].isupper():
                PROPER.add(re.sub(r"'s?$", "", w.lower()))

    def helper_match(owner):
        low = owner.lower()
        for h in helpers:
            hl = h["name"].lower()
            first = re.split(r"[\s,(]", hl)[0]
            if low == hl or low == first or low.startswith(first + " ") or hl.startswith(low):
                return h["name"]
        return None

    # steps
    business_off = {"name": BUSINESS, "billing": "monthly", "active": 1.0, "months": 1.0, "months_src": "n/a"}
    steps = []
    used_used_all = False
    for i, st in enumerate(steps_in):
        if not isinstance(st, dict):
            raise Stop(f"step {i + 1} is not an object")
        sname = str(st.get("step") or "").strip()
        if not sname:
            raise Stop(f"step {i + 1} has no name")
        oname = str(st.get("offer") or "").strip()
        per = str(st.get("per") or "").strip().lower()
        business = per in ("business", "business-wide", "month") or oname.lower() in BUSINESS_WORDS or oname == BUSINESS
        if business:
            targets = [business_off]
        elif oname.lower() in ("all", "every offer", "all offers", "everyone", "*"):
            targets = offers
            used_used_all = True
        elif oname.lower() in names:
            targets = [names[oname.lower()]]
        elif not oname and len(offers) == 1:
            targets = offers
        else:
            raise Stop(f"step '{sname}' names offer '{oname}', which is not in the offers list. Fix the name, use 'all', "
                       "or 'business' for work that does not grow with clients")
        hours, hn = read(parse_hours, st.get("hours"), field=f"{sname} hours")
        if hn == "ASK":
            pass
        elif hn and hours is None:
            needs.append(f"{sname}: {hn}; counted as 0 hours until fixed")
        elif hours is None:
            needs.append(f"{sname}: hours each time not given; counted as 0 until the founder gives a rough figure")
        elif hn:
            notes.append(f"{sname}: {hn}")
        if hours is not None and hours > 200:
            raise Stop(f"step '{sname}': I read '{st.get('hours')}' as {fmt_h(hours)} hours each time; check whether that is a year's total")
        owner, is_you, on = owner_of(st.get("owner"))
        if on and "shared" in on:
            notes.append(f"{sname}: {on}")
        hm = None if is_you else helper_match(owner)
        if hm:
            owner = hm
        flag_raw = st.get("flag")
        flag = flag_of(flag_raw)
        if flag_raw not in (None, "") and flag is None:
            needs.append(f"{sname}: flag '{flag_raw}' is not F, W or T; counted as F until confirmed")
        elif flag is None:
            needs.append(f"{sname}: no flag yet; counted as F (yours) until confirmed")
        reason = str(st.get("reason") or "").strip()
        if not reason and flag:
            needs.append(f"{sname}: flag {flag} has no reason; give one line on why")
        gk = gate_kind(st, flag)
        gate = gk == "yes"
        counted = flag or "F"
        if gate and is_you and counted != "F":
            notes.append(f"{sname}: a quality check you do yourself, so counted as F until someone else can review")
            counted = "F"
        if gk == "ask" and is_you:
            notes.append(f"{sname}: flagged {flag}, and its name sounds like a review. Ask once: is this a check of the work before "
                         "the client sees it? If yes, set gate: yes and it counts F; if not, set gate: no")
        if flag == "W" and not is_you:
            notes.append(f"{sname}: flagged W but {owner} already does it. If they do all of it from a write-up, it is T")
        if flag == "T" and is_you and not str(st.get("handover_to") or "").strip() and not reason:
            needs.append(f"{sname}: flagged T while you do it; say who or what would do it now")
        check_h, cn = read(parse_hours, st.get("check_hours_after"), field=f"{sname} check time")
        if cn and cn != "ASK" and check_h is None:
            needs.append(f"{sname}: {cn}")
        move_in = st.get("handover")
        moved = str(move_in).strip().lower() in ("yes", "y", "move", "true", "1") if move_in not in (None, "") else None
        for off in targets:
            times, label, fnote, once = read(parse_freq, st.get("how_often"), off["months"], WORKING_DAYS[0],
                                             field=f"{sname} how often")
            if business and once:
                needs.append(f"{sname} (business-wide): '{st.get('how_often')}' is once per client; a business-wide step needs "
                             "how often a month it happens. Counted as once a month until fixed")
                times, once = 1.0, False
            if times is None:
                if fnote != "ASK":
                    needs.append(f"{sname} ({off['name']}): {fnote or 'how often not given'}; counted as once a month until fixed")
                times, label = 1.0, label or "not given"
                times_src = "default"
            else:
                times_src = "founder said"
                if fnote:
                    notes.append(f"{sname}: {fnote}")
            if times > 100:
                raise Stop(f"step '{sname}': I read '{st.get('how_often')}' as {fmt_h(times)} times a month per client; "
                           "check the frequency with the founder")
            if once and off["months_src"] == "default":
                assumptions.append(
                    f"{off['name']}: a once-per-client step is spread over {fmt_h(off['months'])} "
                    f"{plural(off['months'], 'month')}, the default for a {off['billing']} offer; say how long a client stays to change it")
            steps.append({
                "key": f"S{i + 1}", "offer": off["name"], "step": sname, "hours": hours if hours is not None else 0.0,
                "hours_raw": st.get("hours"), "hours_known": hours is not None, "business": business,
                "times": times, "how_often": st.get("how_often"), "freq_label": label, "times_src": times_src,
                "once": once, "owner": owner, "you": is_you, "flag": flag, "counted": counted,
                "flag_raw": flag_raw, "reason": reason, "gate": gate,
                "check_hours": check_h or 0.0, "check_given": check_h is not None,
                "handover_to": str(st.get("handover_to") or "").strip(), "pick": moved,
            })
    if asks:
        raise Stop("some figures read two ways. Ask the founder in one message, then run again:\n" +
                   "\n".join(f"ASK: {a}" for a in dict.fromkeys(asks)))
    biz["used_all"] = used_used_all
    biz["has_business"] = any(s["business"] for s in steps)
    if _DAY_USED[0] and biz["day_hours_src"] == "default":
        assumptions.append(f"a day in your figures counted as {fmt_h(DAY_HOURS_DEFAULT)} hours; give the length of your "
                           "working day to change it")
    if biz["priced"]:
        unpriced = [o["name"] for o in offers if o["price"] is None]
        if unpriced:
            notes.append("no price for " + ", ".join(unpriced) + "; what it pays for your hours is not worked out")
    return biz, offers, steps, helpers, needs, notes, list(dict.fromkeys(assumptions))


# ------------------------------------------------------------------ compute
def compute(biz, offers, steps, helpers, _with_today=True):
    avail = biz["delivery_hours_week"] * biz["working_weeks_year"] / 12
    for s in steps:
        s["per_client"] = s["hours"] * s["times"]
    by_offer = {o["name"]: o for o in offers}
    for s in steps:
        ac = 1.0 if s["business"] else by_offer[s["offer"]]["active"]
        s["clients"] = ac or 0.0
        s["across"] = s["per_client"] * s["clients"]

    # handover ranking: W steps, by your hours a month across clients (hours x frequency x clients). One entry per
    # step as the founder listed it: a step set on 'all' offers is summed once; two offers' steps that share a name are not.
    agg = {}
    for s in steps:
        if s["counted"] != "W":
            continue
        a = agg.setdefault(s["key"], {"key": s["key"], "step": s["step"], "offers": [], "freed": 0.0, "per_client": 0.0,
                                      "times": 0.0, "hours": s["hours"], "reason": s["reason"], "clients": 0.0,
                                      "pick": None, "check_hours": 0.0, "check_given": False, "handover_to": ""})
        a["offers"].append(s["offer"])
        a["freed"] += s["across"]
        a["per_client"] = max(a["per_client"], s["per_client"])
        a["times"] = max(a["times"], s["times"])
        a["clients"] += s["clients"]
        if s["pick"] is not None:
            a["pick"] = s["pick"] if a["pick"] is None else (a["pick"] or s["pick"])
        a["check_hours"] = max(a["check_hours"], s["check_hours"])
        a["check_given"] = a["check_given"] or s["check_given"]
        a["handover_to"] = a["handover_to"] or s["handover_to"]
        if not a["reason"]:
            a["reason"] = s["reason"]
    ranked = sorted(agg.values(), key=lambda a: (-round(a["freed"], 6), -round(a["per_client"], 6), -a["times"], a["step"].lower()))
    for i, a in enumerate(ranked, 1):
        a["rank"] = i
    founder_picked = any(a["pick"] for a in ranked)
    picks = [a for a in ranked if a["pick"]] if founder_picked else ranked[: biz["handover_count"]]
    pick_keys = {a["key"] for a in picks}
    for a in ranked:
        a["picked"] = a["key"] in pick_keys

    single_helper = helpers[0]["name"] if len(helpers) == 1 else ""
    auto_assigned = []
    for s in steps:
        s["move"] = s["counted"] == "W" and s["key"] in pick_keys
        s["after"] = "T" if s["move"] else s["counted"]
        s["check_pc"] = s["check_hours"] * s["times"] if s["move"] else 0.0
        s["moves_to"] = (s["handover_to"] or single_helper or "not yet named") if s["move"] else ""
        if s["move"] and not s["handover_to"] and single_helper:
            auto_assigned.append(single_helper)
        s["moving_hours"] = s["across"] if s["move"] else 0.0

    # business-wide work: fixed hours a month, in the load once, off the available hours before any ceiling
    bsteps = [s for s in steps if s["business"]]
    ov = {"F": sum(s["per_client"] for s in bsteps if s["counted"] == "F"),
          "W": sum(s["per_client"] for s in bsteps if s["counted"] == "W"),
          "T_you": sum(s["per_client"] for s in bsteps if s["counted"] == "T" and s["you"]),
          "T_other": sum(s["per_client"] for s in bsteps if s["counted"] == "T" and not s["you"])}
    ov["FW"] = ov["F"] + ov["W"]
    ov["FW_after"] = sum(s["per_client"] for s in bsteps if s["after"] in ("F", "W")) + sum(s["check_pc"] for s in bsteps)
    ov["steps"] = [s["step"] for s in bsteps if s["counted"] in ("F", "W")]
    for_clients = max(avail - ov["FW"], 0.0)
    for_clients_after = max(avail - ov["FW_after"], 0.0)
    for_clients_T = max(avail - ov["FW"] - ov["T_you"], 0.0)

    res_offers = []
    for o in offers:
        mine = [s for s in steps if s["offer"] == o["name"]]
        F = sum(s["per_client"] for s in mine if s["counted"] == "F")
        W = sum(s["per_client"] for s in mine if s["counted"] == "W")
        T_you = sum(s["per_client"] for s in mine if s["counted"] == "T" and s["you"])
        T_other = sum(s["per_client"] for s in mine if s["counted"] == "T" and not s["you"])
        FW = F + W
        ac = o["active"]
        load = FW * ac if ac is not None else None
        FW_after = (sum(s["per_client"] for s in mine if s["after"] in ("F", "W")) + sum(s["check_pc"] for s in mine))
        r = {
            "name": o["name"], "billing": o["billing"], "active": ac, "months": o["months"],
            "F": F, "W": W, "FW": FW, "T_you": T_you, "T_other": T_other,
            "load": load, "ceiling": (for_clients / FW) if FW > 0 else None,
            "ceiling_whole": math.floor(for_clients / FW + 1e-9) if FW > 0 else None,
            "ceiling_with_T": (for_clients_T / (FW + T_you)) if FW + T_you > 0 else None,
            "FW_after": FW_after, "load_after": FW_after * ac if ac is not None else None,
            "ceiling_after": (for_clients_after / FW_after) if FW_after > 0 else None,
            "ceiling_after_whole": math.floor(for_clients_after / FW_after + 1e-9) if FW_after > 0 else None,
            "steps": len(mine), "price": o.get("price"), "price_month": o.get("price_month"), "affix": o.get("affix", ("", "")),
            "price_months": 1.0 if o["billing"] == "monthly" else o["months"], "price_range": o.get("price_range"),
        }
        r["per_hour"] = (r["price_month"] / FW) if (r["price_month"] is not None and FW > 0) else None
        r["per_hour_range"] = None
        if r["per_hour"] is not None and r["price_range"]:
            k = r["per_hour"] / r["price"] if r["price"] else 0.0
            r["per_hour_range"] = (r["price_range"][0] * k, r["price_range"][1] * k)
        r["ceiling_with_T_whole"] = math.floor(r["ceiling_with_T"] + 1e-9) if r["ceiling_with_T"] is not None else None
        res_offers.append(r)
    known = [r for r in res_offers if r["load"] is not None]
    total_load = sum(r["load"] for r in known) + ov["FW"]
    total_after = sum(r["load_after"] for r in known) + ov["FW_after"]
    spare = avail - total_load
    spare_after = avail - total_after

    def room(sp, fw):
        if not fw:
            return None
        if sp >= 0:
            return math.floor(sp / fw + 1e-9)
        return -math.ceil(-sp / fw - 1e-9)

    for r in res_offers:
        r["room"] = room(spare, r["FW"])
        r["room_after"] = room(spare_after, r["FW_after"])
    binding = max(known, key=lambda r: (r["load"], r["FW"]), default=None) if known else None
    if binding is None and res_offers:
        binding = max(res_offers, key=lambda r: r["FW"])

    def status_of(total, sp, fw):
        if total > avail + 1e-9:
            return "over"
        if binding and fw > 0 and sp < fw - 1e-9:
            return "full"
        return "room"
    status = status_of(total_load, spare, binding["FW"] if binding else 0)
    status_after = status_of(total_after, spare_after, binding["FW_after"] if binding else 0)

    ready_now = {}
    for s in steps:
        if s["counted"] == "T" and s["you"]:
            r = ready_now.setdefault(s["key"], {"key": s["key"], "step": s["step"], "offers": [], "hours_month": 0.0,
                                                "reason": s["reason"], "handover_to": s["handover_to"]})
            r["offers"].append(s["offer"])
            r["hours_month"] += s["across"]
    ready = sorted(ready_now.values(), key=lambda r: -r["hours_month"])
    T_you_total = sum(r["hours_month"] for r in ready)

    # helpers
    res_helpers = []
    for h in helpers:
        cap = h["hours_week"] * biz["working_weeks_year"] / 12 if h["hours_week"] is not None else None
        load_today = sum(s["across"] for s in steps if not s["you"] and s["owner"] == h["name"])
        incoming = sum(s["moving_hours"] for s in steps if s["moves_to"] == h["name"])
        rh = {"name": h["name"], "kind": h["kind"], "hours_week": h["hours_week"], "cap": cap,
              "load": load_today, "incoming": incoming, "load_after": load_today + incoming,
              "by_job": bool(re.search(r"per (project|job|task|piece)|by the (job|project|task)|freelanc|paid per", h["kind"], re.I))}
        if cap:
            rh["share"] = load_today / cap
            rh["share_after"] = rh["load_after"] / cap
            rh["spare_at_line"] = cap * biz["plan_line"] - load_today
        res_helpers.append(rh)
    unassigned = sum(s["moving_hours"] for s in steps if s["moves_to"] == "not yet named")
    hnames = {h["name"] for h in helpers}
    to_tool = sum(s["moving_hours"] for s in steps if s["moves_to"] and s["moves_to"] not in hnames
                  and re.search(TOOL_WORDS, s["moves_to"], re.I))
    to_other = sum(s["moving_hours"] for s in steps if s["moves_to"] and s["moves_to"] not in hnames
                   and s["moves_to"] != "not yet named" and not re.search(TOOL_WORDS, s["moves_to"], re.I))
    over_line = sum(max(h["incoming"] - max(h.get("spare_at_line", 0.0), 0.0), 0.0) for h in res_helpers if h["cap"])
    no_cap = sum(h["incoming"] for h in res_helpers if not h["cap"])
    needed = unassigned + over_line
    moving_total = sum(s["moving_hours"] for s in steps)
    # until someone has room, hours with nobody to take them stay yours
    total_after_held = total_after + needed
    spare_after_held = avail - total_after_held

    # hours check against what delivery takes now
    you_steps = sum(s["across"] for s in steps if s["you"])
    hours_check = None
    if biz.get("delivery_hours_now_week") is not None:
        now_m = biz["delivery_hours_now_week"] * biz["working_weeks_year"] / 12
        gap = now_m - you_steps
        hours_check = {"now_month": now_m, "steps_month": you_steps, "gap": gap, "share_missing": (gap / now_m) if now_m else 0.0,
                       "flag": ("missing" if gap > HOURS_CHECK_GAP * now_m else
                                "over" if -gap > HOURS_CHECK_GAP * now_m else "ok")}
    all_F = bool(steps) and all(s["counted"] == "F" for s in steps)
    priced = [r for r in res_offers if r["per_hour"] is not None]
    lowest = min(priced, key=lambda r: r["per_hour"]) if priced else None
    res = {
        "available_month": avail, "total_load": total_load, "spare": spare, "share_used": (total_load / avail) if avail else 0,
        "total_load_after": total_after, "spare_after": spare_after, "status": status, "status_after": status_after,
        "total_load_after_held": total_after_held, "spare_after_held": spare_after_held,
        "binding": binding["name"] if binding else None, "offers": res_offers, "ranked": ranked, "picks": picks,
        "founder_picked": founder_picked, "ready_now": ready, "T_you_total": T_you_total, "helpers": res_helpers,
        "you_steps_week": you_steps * 12 / biz["working_weeks_year"],
        "unassigned_moving": unassigned, "moving_to_tools": to_tool, "moving_to_others": to_other,
        "moving_no_room": needed, "moving_to_helper_no_hours": no_cap, "you_steps_month": you_steps, "hours_check": hours_check, "all_F": all_F,
        "moving_total": moving_total, "auto_assigned": auto_assigned, "overhead": ov,
        "lowest_per_hour": lowest["name"] if lowest and len(priced) > 1 else None, "priced": len(priced),
    }
    if _with_today and biz.get("target"):
        b2 = dict(biz)
        b2["delivery_hours_week"] = biz["today_delivery_hours_week"]
        t = compute(b2, offers, steps, helpers, _with_today=False)
        res["today"] = {"available_month": t["available_month"], "spare": t["spare"], "status": t["status"],
                        "offers": {r["name"]: {"ceiling_whole": r["ceiling_whole"], "room": r["room"]} for r in t["offers"]}}
        compute(biz, offers, steps, helpers, _with_today=False)  # leave the steps as the target run set them
    return res


# ------------------------------------------------------------------ words
def _join(names):
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def need_word(res):
    return "Your work needs" if res["overhead"]["FW"] >= 0.05 else "Your clients need"


def _ov_clause(res):
    ov = res["overhead"]
    if ov["FW"] < 0.05:
        return ""
    return f", {fmt_h(ov['FW'])} of them on business-wide work that does not grow with clients"


def headline(biz, res):
    b = next((r for r in res["offers"] if r["name"] == res["binding"]), None)
    avail = res["available_month"]
    if b is None:
        return "Add the delivery steps to see your ceiling."
    single = len(res["offers"]) == 1
    if b["ceiling"] is None:
        return (f"On {b['name']} you do none of the delivery steps yourself, so your hours do not limit it. "
                "The limit sits with whoever does the work.")
    ov = res["overhead"]
    after_ov = (f" after the {fmt_h(ov['FW'])} hours a month your business-wide work takes" if ov["FW"] >= 0.05 else "")
    if single:
        if b["active"] is None:
            return (f"You can hold {b['ceiling_whole']} {plural(b['ceiling_whole'], 'client')} on {b['name']} with the "
                    f"{fmt_h(avail)} delivery hours a month you have{after_ov}. [NEED: how many clients are on it now]")
        line = (f"You can hold {b['ceiling_whole']} {plural(b['ceiling_whole'], 'client')} on {b['name']} with the "
                f"{fmt_h(avail)} delivery hours a month you have{after_ov}; you have {int(b['active'])}.")
        if b["active"] > b["ceiling_whole"]:
            line += f" That is {int(b['active']) - b['ceiling_whole']} over your ceiling."
        elif b["active"] == b["ceiling_whole"]:
            line += " You are at your ceiling."
        else:
            line += f" There is room for {b['ceiling_whole'] - int(b['active'])} extra."
        return line
    line = f"{need_word(res)} {fmt_h(res['total_load'])} of your hours a month{_ov_clause(res)}; you have {fmt_h(avail)}."
    if res["status"] == "over":
        line += (f" You are {fmt_h(-res['spare'])} hours a month over, about {-b['room']} "
                 f"{b['name']} {plural(-b['room'], 'client', 'clients')}{chr(39) + 's' if -b['room'] == 1 else chr(39)} worth.")
    elif res["status"] == "full":
        line += f" You are at your ceiling: there is no room for another {b['name']} client."
    else:
        line += f" There is room for {b['room']} extra {b['name']} {plural(b['room'], 'client')} at today's mix."
    return line


def week_line(biz, res):
    """The week the ceiling assumes: the one the founder wants (today's beside it), or today's long week flagged."""
    if biz.get("target") and res.get("today"):
        t = res["today"]
        b = res["binding"]
        tb = t["offers"].get(b, {})
        want = (f"the {fmt_h(biz['target_working_week'])}-hour week you want" if biz.get("target_working_week") is not None
                else f"the {fmt_h(biz['delivery_hours_week'])} delivery hours a week you want")
        now = (f"{fmt_h(biz['working_hours_week'])}-hour weeks" if biz.get("working_hours_week") is not None
               else f"{fmt_h(biz['today_delivery_hours_week'])} delivery hours a week")
        if tb.get("room") is None:
            tail = ""
        elif len(res["offers"]) == 1:
            tail = f", a ceiling of {tb['ceiling_whole']} on {b}"
        elif tb["room"] == 0:
            tail = f", no room for another {b} client"
        elif tb["room"] > 0:
            tail = f", room for {tb['room']} extra {b} {plural(tb['room'], 'client')}"
        else:
            tail = f", {-tb['room']} {b} {plural(-tb['room'], 'client')} over"
        return (f"That is at {want}. At the {now} you work now you have {fmt_h(t['available_month'])} delivery hours "
                f"a month{tail}.")
    if biz.get("long_week"):
        now = (f"{fmt_h(biz['working_hours_week'])}-hour weeks" if biz.get("working_hours_week") is not None
               else f"{fmt_h(biz['delivery_hours_week'])} delivery hours a week")
        return (f"This takes your {now} as the plan. **[NEED: the week you want to be working.]** Give it and the ceiling "
                "moves to it, with today's week beside it.")
    return ""


def after_line(res):
    b = next((r for r in res["offers"] if r["name"] == res["binding"]), None)
    picks = res["picks"]
    if not picks or b is None or b["ceiling"] is None:
        return ""
    joined = _join([lc(p["step"]) for p in picks])
    if b["ceiling_after"] is None:
        tail = f"{b['name']} no longer needs your hours on its F and W steps"
    else:
        tail = f"your ceiling on {b['name']} goes from {b['ceiling_whole']} to {b['ceiling_after_whole']} clients"
    line = f"Hand over {joined} and {tail}"
    held = res["moving_no_room"]
    if held > 0.05:
        line += (f", once someone has room for the work: {fmt_h(held)} of the {fmt_h(res['moving_total'])} hours a month "
                 "that move have nobody with room today")
        if len(res["offers"]) > 1 or res["overhead"]["FW"] >= 0.05:
            line += (f", so until then {need_word(res).lower()} {fmt_h(res['total_load_after_held'])} of your "
                     f"{fmt_h(res['available_month'])} hours a month")
    elif len(res["offers"]) > 1 or res["overhead"]["FW"] >= 0.05:
        line += f", and {need_word(res).lower()} {fmt_h(res['total_load_after'])} of your {fmt_h(res['available_month'])} hours a month"
    return line + "."


def price_text(r):
    """The offer's price as the founder gave it: one figure, or both ends of a range."""
    per = "a month" if r["billing"] == "monthly" else "a project"
    if r.get("price_range"):
        lo, hi = r["price_range"]
        return f"{fmt_money(lo, r['affix'])} to {fmt_money(hi, r['affix'])} {per}"
    return f"{fmt_money(r['price'], r['affix'])} {per}"


def pay_text(r):
    """What the offer pays for each hour of the founder's: one figure, or both ends when the price is a range."""
    if r.get("per_hour_range"):
        lo, hi = r["per_hour_range"]
        return f"{fmt_money(lo, r['affix'])} to {fmt_money(hi, r['affix'])}"
    return fmt_money(r["per_hour"], r["affix"])


def price_move(res):
    """Move 2, from the founder's own prices where given: what each offer pays for an hour of the founder's work."""
    priced = [r for r in res["offers"] if r["per_hour"] is not None]
    base = ("A higher price for new clients means fewer clients for the same income, and clients outside your best fit "
            "usually take the most hours. Both raise your ceiling without anyone new.")
    if not priced:
        return (f"**Check price and fit first.** {base} Give what each offer pays (before any sales tax) and the check "
                "shows which pays least for your hours.")
    if len(priced) == 1:
        r = priced[0]
        return (f"**Check price and fit first.** {r['name']} pays {pay_text(r)} for each hour of yours "
                f"({price_text(r)} over your {fmt_h(r['FW'] * r['price_months'])} hours on "
                f"each client). {base}")
    lo = min(priced, key=lambda r: r["per_hour"])
    clear = all((lo["per_hour_range"] or (lo["per_hour"],) * 2)[1] <= (r["per_hour_range"] or (r["per_hour"],) * 2)[0]
                for r in priced if r is not lo)
    others = "; ".join(f"{r['name']}, {price_text(r)}, {pay_text(r)}" for r in priced if r is not lo)
    least = "the least of your offers" if clear else "the least of your offers at the middle of your price range, so give a typical price to settle it"
    return (f"**Check price and fit first.** {lo['name']} ({price_text(lo)}) pays {pay_text(lo)} for each hour of yours, "
            f"{least} ({others}). Start the price and fit check there: {base[0].lower() + base[1:]}")


def order_of_moves(res):
    b = next((r for r in res["offers"] if r["name"] == res["binding"]), None)
    bn = b["name"] if b else "your main offer"
    out = []
    if res["status"] in ("over", "full"):
        why = (f"you are {fmt_h(-res['spare'])} hours a month over the hours you can give, so a new client takes hours from the ones you have"
               if res["status"] == "over" else "there is no room for another client without taking hours from the ones you have")
        out.append(f"**Stop adding clients for now.** Pause new lead generation until there is room: {why}.")
    else:
        stop_at = int(b["active"] or 0) + (b["room"] or 0) if b else 0
        out.append(f"**Keep selling, with a stop line.** There is room for {b['room'] if b else 0} extra {bn} "
                   f"{plural(b['room'] if b else 0, 'client')} at today's mix; plan to stop taking {bn} clients at {stop_at}.")
    out.append(price_move(res))
    held = res["moving_no_room"] > 0.05
    if res["picks"]:
        n = len(res["picks"])
        if b and b["ceiling_after"] is not None and b["ceiling"] is not None:
            gain = f"That takes your ceiling on {bn} from {b['ceiling_whole']} to {b['ceiling_after_whole']}"
            gain += (", once someone has room for the work." if held else ".")
        else:
            gain = ""
        out.append(f"**Then hand over the {n} {plural(n, 'step')} above, in that order.** Write each one down, have someone run it "
                   f"from the write-up while you check, then mark it T. {gain}".strip())
    else:
        out.append("**There is nothing flagged W to hand over.** Your ceiling moves only through price, fit, or changing what the F work involves.")
    if res["status_after"] == "over" and -res["spare_after"] < 1:
        tail = (f"After the handover {need_word(res).lower()} {fmt_h(res['total_load_after'])} of your {fmt_h(res['available_month'])} "
                "hours a month, which leaves no room at all, so this is the step that would make any.")
    elif res["status_after"] == "over":
        tail = (f"After the handover you are still {fmt_h(-res['spare_after'])} hours a month over, "
                "so this is the step that closes the gap.")
    elif held and res["picks"]:
        tail = (f"After the handover your own hours fit, but {fmt_h(res['moving_no_room'])} hours a month of the work that moves "
                "has nobody with room to take it. Extra paid hours for a helper, a contractor or a hire are the options.")
    else:
        tail = ("After the handover your work fits inside your hours, so a hire is not needed to fix this." if res["overhead"]["FW"] >= 0.05
                else "After the handover your clients fit inside your hours, so a hire is not needed to fix this.")
    out.append(f"**Then, only if you are still short, test a hire.** {tail} Get the full cost of any hire from your accountant "
               "or payroll provider, and the terms from an employment lawyer where you hire, before you decide.")
    return out


WHY_ORDER = ("Why this order: your hours are the limit, so they go on F work; W work gets written down and handed over; "
             "a hire comes last, because it costs money before it frees any of your time.")


def americanise(text, locale):
    if locale != "en-US":
        return text
    for a, b in (("utilisation", "utilization"), ("programme", "program"), ("organis", "organiz"),
                 ("prioritis", "prioritiz"), ("recognis", "recogniz")):
        text = text.replace(a, b)
    return text


# ------------------------------------------------------------------ report (compute)
def report(biz, offers, steps, helpers, needs, notes, assumptions, res):
    L = [f"Business: {biz['business']} | date {biz['date']}",
         f"Available delivery hours: {fmt_h(biz['delivery_hours_week'])} a week ({biz['delivery_hours_src']}) x "
         f"{fmt_h(biz['working_weeks_year'])} weeks / 12 = {fmt_h(res['available_month'])} a month",
         "", "STEPS (hours per client a month = hours each time x times a month)"]
    for s in steps:
        tag = s["counted"] + ("" if s["flag"] == s["counted"] else f" (given {s['flag'] or 'none'})")
        L.append(f"  {s['offer']} | {s['step']} | {fmt_h(s['hours'])} x {s['times']:.3f} = {s['per_client']:.2f} | "
                 f"owner {s['owner']} | counted {tag}{' | quality gate' if s['gate'] else ''}")
    L += ["", "PER OFFER"]
    for r in res["offers"]:
        ceil_txt = "no limit" if r["ceiling"] is None else "%.2f -> %s" % (r["ceiling"], r["ceiling_whole"])
        L.append(f"  {r['name']}: active {fmt_h(r['active']) if r['active'] is not None else '[NEED]'} | F {r['F']:.2f} + W {r['W']:.2f} = "
                 f"{r['FW']:.2f} a client | load {fmt_h(r['load']) if r['load'] is not None else '?'} | ceiling "
                 f"{ceil_txt} | room at mix "
                 f"{r['room']} | T you still do {r['T_you']:.2f} a client | after handover F+W {r['FW_after']:.2f}, ceiling "
                 f"{'no limit' if r['ceiling_after'] is None else r['ceiling_after_whole']}, room at mix after {r['room_after']}")
        if r["per_hour"] is not None:
            L.append(f"    price {price_text(r)} | "
                     f"pays {pay_text(r)} for each hour of yours (price a month / F + W hours a client)"
                     + (" | a range: never quote one figure inside it as the founder's price" if r.get("price_range") else ""))
    ov = res["overhead"]
    if biz.get("has_business"):
        L.append(f"  BUSINESS-WIDE (not per client): F {ov['F']:.2f} + W {ov['W']:.2f} = {ov['FW']:.2f} hours a month, in the load once "
                 f"and off the available hours before each ceiling; after handover {ov['FW_after']:.2f}; T you still do {ov['T_you']:.2f}")
    if res["lowest_per_hour"]:
        L.append(f"LOWEST PAY FOR YOUR HOURS: {res['lowest_per_hour']}")
    L.append(f"TOTAL: load {fmt_h(res['total_load'])} of {fmt_h(res['available_month'])} ({fmt_pct(res['share_used'])}); "
             f"spare {fmt_h(res['spare'])}; status {res['status']}; binding offer {res['binding']}")
    L.append(f"AFTER HANDOVER: load {fmt_h(res['total_load_after'])}; spare {fmt_h(res['spare_after'])}; status {res['status_after']}")
    if res["moving_no_room"] > 0.05:
        L.append(f"AFTER, HOLDING WORK NOBODY HAS ROOM FOR: {fmt_h(res['moving_no_room'])} of {fmt_h(res['moving_total'])} moved hours "
                 f"stay yours until someone has room; load {fmt_h(res['total_load_after_held'])}, spare {fmt_h(res['spare_after_held'])}")
    if res.get("today"):
        t = res["today"]
        L.append(f"TODAY'S WEEK: {fmt_h(biz['today_delivery_hours_week'])} delivery hours a week = {fmt_h(t['available_month'])} a month; "
                 f"status {t['status']}; " + "; ".join(f"{k} ceiling {v['ceiling_whole']}, room {v['room']}" for k, v in t["offers"].items()))
    L += ["", "HANDOVER ORDER (W steps by your hours a month across clients)"]
    for a in res["ranked"]:
        L.append(f"  {a['rank']}. {a['step']} ({', '.join(a['offers'])}): frees {fmt_h(a['freed'])} hours a month"
                 f"{' | PICKED' if a['picked'] else ''}")
    if not res["ranked"]:
        L.append("  none: no steps counted W")
    if res["ready_now"]:
        L.append(f"T STEPS YOU STILL DO: {fmt_h(res['T_you_total'])} hours a month")
        for r in res["ready_now"]:
            L.append(f"  {r['step']}: {fmt_h(r['hours_month'])} hours a month")
    for h in res["helpers"]:
        if h["cap"]:
            L.append(f"HELPER {h['name']}: {fmt_h(h['cap'])} hours a month; today {fmt_h(h['load'])} ({fmt_pct(h['share'])}); "
                     f"after moves {fmt_h(h['load_after'])} ({fmt_pct(h['share_after'])}); planning line {fmt_pct(biz['plan_line'])}")
        else:
            L.append(f"HELPER {h['name']}: hours not given")
    if res["unassigned_moving"]:
        L.append(f"MOVES WITH NO NAMED PERSON: {fmt_h(res['unassigned_moving'])} hours a month")
    L.append(f"YOUR STEPS: {fmt_h(res['you_steps_month'])} hours a month of your time, {fmt_h(res['you_steps_week'])} a week "
             "(every step you do today, T steps included)")
    hc = res["hours_check"]
    if hc:
        L.append(f"HOURS CHECK: steps you do come to {fmt_h(hc['steps_month'])} a month; you said delivery takes "
                 f"{fmt_h(hc['now_month'])} ({hc['flag']})")
    if hc and hc["flag"] == "missing":
        L.append(f"ASK (in your next reply, beside the provisional figures): Your steps come to {fmt_h(hc['steps_month'])} hours a month but you "
                 f"said delivery takes {fmt_h(hc['now_month'])}. What's missing: client messages, chasing, rework, travel, team time?")
    L += ["", "HEADLINE: " + headline(biz, res)]
    wl = week_line(biz, res)
    if wl:
        L.append("WEEK: " + wl.replace("**", ""))
    L.append("AFTER: " + after_line(res))
    for a in assumptions:
        L.append("ASSUMED: " + a)
    for n in notes:
        L.append("NOTE: " + n)
    if res["all_F"]:
        L.append("NOTE: every step is counted F. Challenge it once: is the client paying for your judgement in each, "
                 "or do you do some only because nobody else knows how?")
    for n in needs:
        L.append("NEED: " + n)
    return "\n".join(L)


# ------------------------------------------------------------------ workbook
def build_xlsx(path, biz, offers, steps, helpers, res, assumptions, needs):
    S = office
    st = S.Sheet("Steps")
    ld = S.Sheet("Load")
    ce = S.Sheet("Ceiling")
    ho = S.Sheet("Handover order")
    ov = res["overhead"]
    # ---- Load layout first (Steps refer to it)
    ld.set(1, 1, "Founder load per offer", S.S_TITLE)
    ld.set(2, 1, "Yellow cells are yours to change. Load counts only F and W steps: the ones that need you. "
                 "Business-wide work sits on its own row, counted once, whatever your client count.", S.S_SIDE)
    heads = ["Offer", "Active clients", "F hours per client a month", "W hours per client a month",
             "F + W hours per client a month", "Your load a month (F + W x clients)", "T steps you still do, hours per client a month",
             "Done by others, hours per client a month", "F + W per client after handover", "Your load after handover"]
    for j, h in enumerate(heads, 1):
        ld.set(4, j, h, S.S_HEAD)
    o_row = {}
    for i, r in enumerate(res["offers"]):
        o_row[r["name"]] = 5 + i
    brow = None
    if biz.get("has_business"):
        brow = 5 + len(res["offers"])
        o_row[BUSINESS] = brow
    nst = len(steps)
    last = 4 + nst
    rngA, rngE, rngJ, rngG = f"Steps!$A$5:$A${last}", f"Steps!$E$5:$E${last}", f"Steps!$J$5:$J${last}", f"Steps!$G$5:$G${last}"
    rngP, rngQ = f"Steps!$P$5:$P${last}", f"Steps!$Q$5:$Q${last}"
    rows_out = [(r["name"], r["active"], r) for r in res["offers"]]
    if brow:
        rows_out.append((BUSINESS, 1.0, None))
    for name, active, r in rows_out:
        rr = o_row[name]
        bus = r is None
        ld.set(rr, 1, "Business-wide (not per client)" if bus else name, S.S_TEXT)
        if bus:
            ld.set(rr, 2, 1, S.S_INT)
            F, W, FW, T_you, T_other, FW_after = ov["F"], ov["W"], ov["FW"], ov["T_you"], ov["T_other"], ov["FW_after"]
            load, load_after = ov["FW"], ov["FW_after"]
        else:
            ld.set(rr, 2, int(active) if active is not None else None, S.S_IN_NUM)
            F, W, FW, T_you, T_other, FW_after = r["F"], r["W"], r["FW"], r["T_you"], r["T_other"], r["FW_after"]
            load, load_after = r["load"] or 0.0, r["load_after"] or 0.0
        key = f'"{BUSINESS}"' if bus else f"$A{rr}"
        ld.set(rr, 3, F, S.S_NUM1, f'SUMIFS({rngE},{rngA},{key},{rngJ},"F")')
        ld.set(rr, 4, W, S.S_NUM1, f'SUMIFS({rngE},{rngA},{key},{rngJ},"W")')
        ld.set(rr, 5, FW, S.S_BOLD_NUM1, f"C{rr}+D{rr}")
        ld.set(rr, 6, load, S.S_BOLD_NUM1, f"E{rr}*B{rr}")
        ld.set(rr, 7, T_you, S.S_NUM1, f'SUMIFS({rngE},{rngA},{key},{rngJ},"T",{rngG},"yes")')
        ld.set(rr, 8, T_other, S.S_NUM1, f'SUMIFS({rngE},{rngA},{key},{rngJ},"T",{rngG},"no")')
        ld.set(rr, 9, FW_after, S.S_NUM1,
               f'SUMIFS({rngE},{rngA},{key},{rngP},"F")+SUMIFS({rngE},{rngA},{key},{rngP},"W")+SUMIFS({rngQ},{rngA},{key})')
        ld.set(rr, 10, load_after, S.S_NUM1, f"I{rr}*B{rr}")
    tr = 5 + len(rows_out)
    ld.set(tr, 1, "Total", S.S_BOLD)
    ld.set(tr, 6, res["total_load"], S.S_BOLD_NUM1, f"SUM(F5:F{tr - 1})")
    ld.set(tr, 10, res["total_load_after"], S.S_BOLD_NUM1, f"SUM(J5:J{tr - 1})")
    ld.widths = {1: 30, 2: 10, 3: 12, 4: 12, 5: 13, 6: 14, 7: 15, 8: 14, 9: 14, 10: 13}
    ld.freeze = 5
    match_rng = f"Load!$A$5:$A${tr - 1}"

    # ---- Steps
    st.set(1, 1, f"Delivery steps: {biz['business']}", S.S_TITLE)
    st.set(2, 1, "F: your judgement is what the client pays for. W: you do it only because nobody else knows how yet. "
                 "T: someone or something else can do it now. Change a yellow cell and every sheet updates.", S.S_NOTE)
    sh = ["Offer", "Step", "Hours each time", "Times per client a month", "Hours per client a month", "Who does it today",
          "You do it today", "Flag (F, W, T)", "Quality check you do", "Counted as", "Why this flag", "Clients on this offer",
          "Hours a month across clients", "Hand over in this round", "Your check hours each time, after it moves",
          "Counted after handover", "Your check time per client a month, after", "Moves to", "Hours a month that move", "Step key"]
    for j, h in enumerate(sh, 1):
        st.set(4, j, h, S.S_HEAD)
    for i, s in enumerate(steps):
        r = 5 + i
        st.set(r, 1, s["offer"], S.S_TEXT)
        st.set(r, 2, s["step"], S.S_WRAP)
        st.set(r, 3, s["hours"], S.S_IN_NUM)
        st.set(r, 4, s["times"], S.S_IN_NUM)
        st.set(r, 5, s["per_client"], S.S_NUM1, f"C{r}*D{r}")
        st.set(r, 6, s["owner"], S.S_TEXT)
        st.set(r, 7, "yes" if s["you"] else "no", S.S_IN_TEXT)
        st.set(r, 8, s["flag"] or "", S.S_IN_TEXT)
        st.set(r, 9, "yes" if (s["gate"] and s["you"]) else "no", S.S_IN_TEXT)
        st.set(r, 10, s["counted"], S.S_BOLD, f'IF(I{r}="yes","F",IF(H{r}="","F",H{r}))')
        st.set(r, 11, s["reason"] or "[NEED: one line on why]", S.S_WRAP)
        st.set(r, 12, int(s["clients"]), S.S_INT, f"INDEX(Load!$B$5:$B${tr - 1},MATCH(A{r},{match_rng},0))"
               if not s["business"] else None)
        if s["business"]:
            st.set(r, 12, 1, S.S_INT)
        st.set(r, 13, s["across"], S.S_NUM1, f"E{r}*L{r}")
        st.set(r, 14, "move" if s["move"] else "", S.S_IN_TEXT)
        st.set(r, 15, s["check_hours"], S.S_IN_NUM)
        st.set(r, 16, s["after"], S.S_TEXT, f'IF(AND(N{r}="move",J{r}="W"),"T",J{r})')
        st.set(r, 17, s["check_pc"], S.S_NUM1, f'IF(AND(N{r}="move",J{r}="W"),O{r}*D{r},0)')
        st.set(r, 18, s["moves_to"], S.S_IN_TEXT)
        st.set(r, 19, s["moving_hours"], S.S_NUM1, f'IF(AND(N{r}="move",J{r}="W"),M{r},0)')
        st.set(r, 20, s["key"], S.S_TEXT)
    st.widths = {1: 22, 2: 34, 3: 9, 4: 10, 5: 10, 6: 14, 7: 8, 8: 8, 9: 9, 10: 9, 11: 40, 12: 9, 13: 11, 14: 10,
                 15: 11, 16: 10, 17: 11, 18: 14, 19: 11, 20: 7}
    st.freeze = 5

    # ---- Ceiling
    ce.set(1, 1, "Your client ceiling", S.S_TITLE)
    ce.set(2, 1, "Ceiling = the delivery hours you can give a month, less business-wide work, divided by the F + W hours "
                 "each client takes from you.", S.S_NOTE)
    ce.set(4, 1, "Delivery hours you can give a week, after selling and admin" +
           (" (the week you want)" if biz.get("target") else ""), S.S_WRAP)
    ce.set(4, 2, biz["delivery_hours_week"], S.S_IN_NUM)
    ce.set(4, 3, biz["delivery_hours_src"], S.S_SIDE)
    ce.set(5, 1, "Working weeks a year", S.S_WRAP)
    ce.set(5, 2, biz["working_weeks_year"], S.S_IN_NUM)
    ce.set(5, 3, biz["weeks_src"], S.S_SIDE)
    ce.set(6, 1, "Delivery hours you can give a month", S.S_BOLD)
    ce.set(6, 2, res["available_month"], S.S_BOLD_NUM1, "B4*B5/12")
    ce.set(7, 1, "Your work needs, a month (F + W)", S.S_TEXT)
    ce.set(7, 2, res["total_load"], S.S_NUM1, f"Load!F{tr}")
    ce.set(8, 1, "Spare (minus means over)", S.S_TEXT)
    ce.set(8, 2, res["spare"], S.S_NUM1, "B6-B7")
    ce.set(9, 1, "Share of your delivery hours used", S.S_TEXT)
    ce.set(9, 2, res["share_used"], S.S_PCT, "IF(B6>0,B7/B6,0)")
    ce.set(10, 1, "Business-wide work, F + W hours a month (comes off before each ceiling)", S.S_WRAP)
    ce.set(10, 2, ov["FW"], S.S_NUM1, f"Load!E{brow}" if brow else None)
    ce.set(11, 1, "Business-wide work after handover", S.S_WRAP)
    ce.set(11, 2, ov["FW_after"], S.S_NUM1, f"Load!I{brow}" if brow else None)
    ce.set(12, 1, "Business-wide T steps you still do, hours a month", S.S_WRAP)
    ce.set(12, 2, ov["T_you"], S.S_NUM1, f"Load!G{brow}" if brow else None)
    today_row = None
    if biz.get("target"):
        ce.set(4, 4, "Today's week", S.S_BOLD)
        ce.set(4, 5, biz["today_delivery_hours_week"], S.S_IN_NUM)
        ce.set(4, 6, "delivery hours a week you work now", S.S_SIDE)
        ce.set(6, 4, "Today, a month", S.S_BOLD)
        ce.set(6, 5, res["today"]["available_month"], S.S_BOLD_NUM1, "E4*B5/12")
        today_row = "$E$6"
    hh = ["Offer", "Active clients", "F + W hours per client a month", "Ceiling if all your hours went to this offer",
          "Ceiling, whole clients", "Room at today's mix (minus means over)", "F + W per client after handover",
          "Ceiling after handover", "Ceiling after, whole clients", "Ceiling today while you still do your T steps",
          "Price, before any sales tax", "Months the price covers", "Paid for each hour of yours"]
    if today_row:
        hh.append("Ceiling at today's week")
    H0 = 14
    for j, h in enumerate(hh, 1):
        ce.set(H0, j, h, S.S_HEAD)
    for i, r in enumerate(res["offers"]):
        rr = H0 + 1 + i
        lr = o_row[r["name"]]
        ce.set(rr, 1, r["name"], S.S_TEXT)
        ce.set(rr, 2, int(r["active"]) if r["active"] is not None else None, S.S_INT, f"Load!B{lr}")
        ce.set(rr, 3, r["FW"], S.S_NUM1, f"Load!E{lr}")
        ce.set(rr, 4, r["ceiling"] if r["ceiling"] is not None else "no limit", S.S_NUM1, f'IF(C{rr}>0,MAX($B$6-$B$10,0)/C{rr},"no limit")')
        ce.set(rr, 5, r["ceiling_whole"] if r["ceiling_whole"] is not None else "no limit", S.S_INT,
               f'IF(C{rr}>0,ROUNDDOWN(D{rr},0),"no limit")')
        ce.set(rr, 6, r["room"] if r["room"] is not None else "no limit", S.S_INT,
               f'IF(C{rr}>0,IF($B$8>=0,ROUNDDOWN($B$8/C{rr},0),-ROUNDUP(-$B$8/C{rr},0)),"no limit")')
        ce.set(rr, 7, r["FW_after"], S.S_NUM1, f"Load!I{lr}")
        ce.set(rr, 8, r["ceiling_after"] if r["ceiling_after"] is not None else "no limit", S.S_NUM1,
               f'IF(G{rr}>0,MAX($B$6-$B$11,0)/G{rr},"no limit")')
        ce.set(rr, 9, r["ceiling_after_whole"] if r["ceiling_after_whole"] is not None else "no limit", S.S_INT,
               f'IF(G{rr}>0,ROUNDDOWN(H{rr},0),"no limit")')
        ce.set(rr, 10, r["ceiling_with_T_whole"] if r["ceiling_with_T_whole"] is not None else "no limit", S.S_INT,
               f'IF(C{rr}+Load!G{lr}>0,ROUNDDOWN(MAX($B$6-$B$10-$B$12,0)/(C{rr}+Load!G{lr}),0),"no limit")')
        ce.set(rr, 11, r["price"], S.S_IN_NUM)
        ce.set(rr, 12, r["price_months"], S.S_IN_NUM)
        ce.set(rr, 13, r["per_hour"] if r["per_hour"] is not None else "no price", S.S_NUM1,
               f'IF(AND(ISNUMBER(K{rr}),C{rr}>0,L{rr}>0),K{rr}/L{rr}/C{rr},"no price")')
        if today_row:
            tw = res["today"]["offers"][r["name"]]["ceiling_whole"]
            ce.set(rr, 14, tw if tw is not None else "no limit", S.S_INT,
                   f'IF(C{rr}>0,ROUNDDOWN(MAX({today_row}-$B$10,0)/C{rr},0),"no limit")')
    ar = H0 + 1 + len(res["offers"]) + 1
    ce.set(ar, 1, "After handover: your work needs, a month", S.S_TEXT)
    ce.set(ar, 2, res["total_load_after"], S.S_NUM1, f"Load!J{tr}")
    ce.set(ar + 1, 1, "After handover: spare (minus means over)", S.S_TEXT)
    ce.set(ar + 1, 2, res["spare_after"], S.S_NUM1, f"B6-B{ar}")
    hr0 = ar + 3
    ce.set(hr0, 1, "Helpers", S.S_BOLD)
    ce.set(hr0, 3, "Planning line (a planning assumption, not a benchmark): fill at most this share of a helper's paid hours. "
                   "Helpers' months use your working weeks.", S.S_SIDE)
    ce.set(hr0 + 1, 1, "Planning line", S.S_TEXT)
    ce.set(hr0 + 1, 2, biz["plan_line"], S.S_IN_PCT)
    ce.set(hr0 + 2, 1, "Low line", S.S_TEXT)
    ce.set(hr0 + 2, 2, biz["low_line"], S.S_IN_PCT)
    ce.set(hr0 + 2, 3, "Below this for two months: sell or cut their hours before adding help", S.S_SIDE)
    hh2 = ["Helper", "Paid hours a week", "Hours a month", "Their delivery hours a month today", "Share used today",
           "Spare at your planning line", "Hours moving to them", "Share used after the moves"]
    for j, h in enumerate(hh2, 1):
        ce.set(hr0 + 4, j, h, S.S_HEAD)
    rngF, rngM, rngR, rngS = (f"Steps!$F$5:$F${last}", f"Steps!$M$5:$M${last}", f"Steps!$R$5:$R${last}", f"Steps!$S$5:$S${last}")
    for i, h in enumerate(res["helpers"]):
        rr = hr0 + 5 + i
        ce.set(rr, 1, h["name"], S.S_TEXT)
        ce.set(rr, 2, h["hours_week"], S.S_IN_NUM)
        ce.set(rr, 3, h["cap"] or 0.0, S.S_NUM1, f"B{rr}*$B$5/12")
        ce.set(rr, 4, h["load"], S.S_NUM1, f'SUMIFS({rngM},{rngF},A{rr},{rngG},"no")')
        ce.set(rr, 5, h.get("share", 0.0), S.S_PCT, f"IF(C{rr}>0,D{rr}/C{rr},0)")
        ce.set(rr, 6, h.get("spare_at_line", 0.0), S.S_NUM1, f"C{rr}*$B${hr0 + 1}-D{rr}")
        ce.set(rr, 7, h["incoming"], S.S_NUM1, f"SUMIFS({rngS},{rngR},A{rr})")
        ce.set(rr, 8, h.get("share_after", 0.0), S.S_PCT, f"IF(C{rr}>0,(D{rr}+G{rr})/C{rr},0)")
    if not res["helpers"]:
        ce.set(hr0 + 5, 1, "No helpers today", S.S_NOTE)
    nr = hr0 + 6 + max(1, len(res["helpers"]))
    ce.set(nr, 1, "What this rests on", S.S_BOLD)
    k = nr + 1
    for a in assumption_lines(biz, res, assumptions) + [f"[NEED] {n}" for n in needs if not n.startswith("the week you want: the ceiling takes")] + \
            ([f"[NEED] {week_line(biz, res).replace('**', '')}"] if biz.get("long_week") else []):
        ce.set(k, 1, a, S.S_SIDE)
        k += 1
    ce.set(k + 1, 1, f"Made with Merigrove {SKILL_NAME}. A planning tool, not tax, legal, employment or financial advice.", S.S_NOTE)
    ce.widths = {1: 44, 2: 12, 3: 14, 4: 16, 5: 12, 6: 14, 7: 14, 8: 13, 9: 12, 10: 16, 11: 12, 12: 10, 13: 12, 14: 12}

    # ---- Handover order: the W steps when this was built, re-ranked live from their hours
    ho.set(1, 1, "Handover order", S.S_TITLE)
    ho.set(2, 1, "W steps ranked by the hours a month they take from you across your clients (hours each time x how often x clients). "
                 "Hours and ranks follow the Steps sheet; a step you newly flag W there is not added here, so run the check again.", S.S_NOTE)
    ho.set(3, 1, "Steps in this round", S.S_TEXT)
    ho.set(3, 3, biz["handover_count"], S.S_IN_NUM)
    if res["founder_picked"]:
        ho.set(3, 4, "You picked this round's steps, so 'In this round' is your pick, not the ranking.", S.S_SIDE)
    h3 = ["Rank", "Step", "Offer", "Hours each time", "Times per client a month", "Clients", "Your hours a month it frees",
          "Why it can move once written", "In this round", "Step key"]
    for j, h in enumerate(h3, 1):
        ho.set(4, j, h, S.S_HEAD)
    rngT = f"Steps!$T$5:$T${last}"
    first, lastr = 5, 4 + len(res["ranked"])
    r = 5
    for a in res["ranked"]:
        ho.set(r, 1, a["rank"], S.S_INT, f"RANK(G{r},$G${first}:$G${lastr})+COUNTIF($G${first}:G{r},G{r})-1")
        ho.set(r, 2, a["step"], S.S_WRAP)
        ho.set(r, 3, ", ".join(a["offers"]), S.S_WRAP)
        ho.set(r, 4, a["hours"], S.S_NUM1)
        ho.set(r, 5, round(a["times"], 2), S.S_NUM1)
        ho.set(r, 6, int(a["clients"]), S.S_INT)
        ho.set(r, 7, a["freed"], S.S_BOLD_NUM1, f'SUMIFS({rngM},{rngT},J{r},{rngJ},"W")')
        ho.set(r, 8, a["reason"] or "[NEED: one line on why]", S.S_WRAP)
        if res["founder_picked"]:
            ho.set(r, 9, "yes" if a["picked"] else "", S.S_TEXT)
        else:
            ho.set(r, 9, "yes" if a["picked"] else "no", S.S_TEXT, f'IF(AND(A{r}<=$C$3,G{r}>0),"yes","no")')
        ho.set(r, 10, a["key"], S.S_TEXT)
        r += 1
    if not res["ranked"]:
        ho.set(r, 2, "No steps are counted W.", S.S_NOTE)
        r += 1
    if res["ready_now"]:
        r += 1
        ho.set(r, 1, "Ready to hand over now: T steps you still do yourself", S.S_BOLD)
        r += 1
        for j, h in enumerate(["", "Step", "Offer", "", "", "", "Your hours a month", "Why it can move now", "", "Step key"], 1):
            if h:
                ho.set(r, j, h, S.S_HEAD)
        r += 1
        for x in res["ready_now"]:
            ho.set(r, 2, x["step"], S.S_WRAP)
            ho.set(r, 3, ", ".join(x["offers"]), S.S_WRAP)
            ho.set(r, 7, x["hours_month"], S.S_NUM1, f'SUMIFS({rngM},{rngT},J{r},{rngJ},"T",{rngG},"yes")')
            ho.set(r, 8, x["reason"], S.S_WRAP)
            ho.set(r, 10, x["key"], S.S_TEXT)
            r += 1
    ho.widths = {1: 6, 2: 34, 3: 22, 4: 10, 5: 11, 6: 8, 7: 13, 8: 44, 9: 9, 10: 7}
    office.write_xlsx(path, [ce, st, ld, ho], title=f"Capacity check: {biz['business']}")


def assumption_lines(biz, res, assumptions):
    out = []
    src = str(biz["delivery_hours_src"])
    m = re.match(r"^saved memory: (.*), (\d{4}-\d{2}-\d{2})$", src)
    if m:
        src = f"{m.group(1)}, saved {long_date(m.group(2), biz['date_order'])}"
    out.append(f"{fmt_h(biz['delivery_hours_week'])} delivery hours a week, after selling and admin ({src}).")
    if biz.get("target"):
        out.append(f"Today you give {fmt_h(biz['today_delivery_hours_week'])} delivery hours a week; the ceiling uses the week you want, "
                   "and today's week is shown beside it.")
    ov = res["overhead"]
    if ov["FW"] >= 0.05:
        out.append(f"Business-wide work ({_join([lc(x) for x in ov['steps']])}) takes {fmt_h(ov['FW'])} of your hours a month "
                   "whatever your client count, so it comes off your hours before each ceiling.")
    if biz["weeks_src"] == "default":
        out.append(f"{WORKING_WEEKS_DEFAULT} working weeks a year, a planning default (six weeks off for holidays, public holidays "
                   "and sick days; give yours to change it); a month's hours are the week's hours x weeks / 12.")
    else:
        why = "" if biz["weeks_src"] in ("founder said",) else f" ({biz['weeks_src']})"
        out.append(f"{fmt_h(biz['working_weeks_year'])} working weeks a year{why}; a month's hours are the week's hours x weeks / 12.")
    if biz.get("day_hours_src") == "founder said":
        out.append(f"A working day is {fmt_h(biz['day_hours'])} hours, your figure.")
    for a in assumptions:
        if not a.startswith(f"{WORKING_WEEKS_DEFAULT} working weeks"):
            out.append(a[0].upper() + a[1:] + ".")
    out.append("Quality checks you do yourself count as F until someone else can review.")
    zero = [lc(a["step"]) for a in res["picks"] if not a["check_hours"] and not a["check_given"]]
    if zero:
        joined = zero[0] if len(zero) == 1 else ", ".join(zero[:-1]) + " and " + zero[-1]
        out.append(f"Once {joined} {'moves' if len(zero) == 1 else 'move'}, your time checking {'it' if len(zero) == 1 else 'them'} "
                   "counts as zero. If you will check before the client sees the work, that check stays yours: "
                   "give the minutes and the figures move.")
    auto = sorted({s for s in res.get("auto_assigned", [])})
    if res["helpers"]:
        lead = (f"Moved steps are assumed to go to {auto[0]}, your only helper (say if not). " if auto else "")
        out.append(f"{lead}Helpers: fill at most {fmt_pct(biz['plan_line'])} of their paid hours; under {fmt_pct(biz['low_line'])} "
                   "for two months means sell or cut their hours. Both are planning assumptions you can change, not benchmarks. "
                   "Helpers' months use your working weeks; give theirs if different.")
    if res["priced"]:
        out.append("Prices are before any sales tax (VAT, GST or similar); ask your accountant whether you need to charge it. "
                   "Pay for each hour of yours is the price a month divided by your F and W hours on each client.")
    return out


# ------------------------------------------------------------------ the one-page reading
PAGE_BUDGET_PT = {"a4": 735, "letter": 685}  # usable height of one page at the margins office.Doc uses


LEAD_BLOCKS = ("helpers", "note", "handover")  # what the founder asked to see first on the page


def helper_lines(biz, res):
    out = []
    for h in res["helpers"]:
        if h["cap"]:
            line = (f"**{h['name']}:** {fmt_h(h['cap'])} paid hours a month, {fmt_h(h['load'])} on your delivery today "
                    f"({fmt_pct(h['share'], biz['low_line'] if h['share'] < biz['plan_line'] - 0.05 else biz['plan_line'])}).")
            if h["incoming"]:
                line += f" The moves add {fmt_h(h['incoming'])}, taking them to {fmt_pct(h['share_after'], biz['plan_line'])}"
                if h["share_after"] > biz["plan_line"] + 1e-9:
                    room_line = max(h["spare_at_line"], 0.0)
                    if room_line > 0.05:
                        line += (f", over your {fmt_pct(biz['plan_line'])} planning line: they have room for {fmt_h(room_line)} "
                                 f"of the {fmt_h(h['incoming'])} hours, so the rest needs extra paid hours or someone else.")
                    else:
                        line += (f", over your {fmt_pct(biz['plan_line'])} planning line: they have no room at that line, "
                                 f"so the {fmt_h(h['incoming'])} hours need extra paid hours or someone else.")
                else:
                    line += f", inside your {fmt_pct(biz['plan_line'])} planning line."
            elif h["share"] > biz["plan_line"] + 1e-9:
                line += f" That is over your {fmt_pct(biz['plan_line'])} planning line already."
            elif h["share"] < biz["low_line"] and not h["by_job"]:
                line += (f" That is under your {fmt_pct(biz['low_line'])} low line: if it holds for two months, "
                         "fill their hours or cut them before adding help.")
            out.append(line)
    return out


def build_docx(path, biz, res, note_text, assumptions, needs, changes):
    """Lay the reading out at full size; if the estimate overflows one page, step the type down."""
    budget = PAGE_BUDGET_PT[biz.get("paper", "a4")]
    for scale in (1.0, 0.95, 0.9, 0.85, 0.8, 0.75):
        d = _reading(biz, res, note_text, assumptions, needs, changes, scale)
        if d.height <= budget:
            break
    d.save(path, footer=f"Made with Merigrove {SKILL_NAME}. A planning tool, not tax, legal, employment or financial advice.",
           title=f"Your client ceiling: {biz['business']}", paper=biz.get("paper", "a4"), lang=biz.get("locale") or "en-GB")
    return d.height


def _reading(biz, res, note_text, assumptions, needs, changes, scale):
    d = office.Doc(scale, paper=biz.get("paper", "a4"))
    loc = biz["locale"]
    A = lambda t: americanise(t, loc)  # noqa: E731
    order = biz["date_order"]
    d.para("Your client ceiling", size=17, bold=True, after=20)
    d.para(f"{biz['business']}, {long_date(biz['date'], order)}", size=9.5, color="555555", after=100)
    lead = biz.get("lead")
    if lead == "helpers":
        for line in helper_lines(biz, res):
            d.para(A(line), size=11, after=50)
    elif lead == "note" and note_text:
        d.para(note_text.strip(), size=11, after=60)
    elif lead == "handover" and after_line(res):
        d.para(A(after_line(res)), size=11.5, bold=True, after=60)
    d.para(A(headline(biz, res)), size=11.5, bold=True, after=50)
    wl = week_line(biz, res)
    if wl:
        d.para(A(wl), size=10, after=50)
    al = after_line(res)
    if al and lead != "handover":
        d.para(A(al), size=10.5, after=60)
    ovw = (f", less the {fmt_h(res['overhead']['FW'])} hours of business-wide work" if res["overhead"]["FW"] >= 0.05 else "")
    d.para(f"How it is worked out: the {fmt_h(res['available_month'])} delivery hours you can give a month "
           f"({fmt_h(biz['delivery_hours_week'])} a week over {fmt_h(biz['working_weeks_year'])} working weeks, divided by 12){ovw}, "
           "divided by the hours each client takes from you on F and W steps (your hours per client).", size=8.5, color="555555", after=60)
    if biz["delivery_hours_src"] == "default":
        d.para(f"**[NEED: your delivery hours a week.]** {DELIVERY_HOURS_WEEK_DEFAULT} is a planning default, not your figure. "
               "Every ceiling on this page moves in step with it.", size=9, after=50)
    if changes:
        lead = changes[0].replace("Compared with ", "Since ").rstrip(":")
        d.para(f"**{lead}:** " + " ".join(changes[1:]), size=9, after=50)
    d.heading("Where your hours go", before=90)
    multi = len(res["offers"]) > 1
    ov = res["overhead"]
    if multi:
        rows = [["Offer", "Clients now", "Your hours per client a month", "Your hours a month", "Room at today's mix", "Ceiling on its own"]]
    else:
        rows = [["Offer", "Clients now", "Your hours per client a month", "Your hours a month", "Ceiling", "Room"]]
    for r in res["offers"]:
        room_txt = "no limit" if r["room"] is None else (f"room for {r['room']}" if r["room"] >= 0 else f"{-r['room']} over")
        rows.append([r["name"], fmt_h(r["active"]) if r["active"] is not None else "[NEED]", fmt_h(r["FW"]),
                     fmt_h(r["load"]) if r["load"] is not None else "?",
                     room_txt if multi else ("no limit" if r["ceiling_whole"] is None else str(r["ceiling_whole"])),
                     ("no limit" if r["ceiling_whole"] is None else str(r["ceiling_whole"])) if multi else room_txt])
    if ov["FW"] >= 0.05:
        rows.append(["Business-wide work", "", "", fmt_h(ov["FW"]), "", ""])
    if multi or ov["FW"] >= 0.05:
        rows.append(["**All your work**", "", "", f"**{fmt_h(res['total_load'])} of {fmt_h(res['available_month'])}**", "", ""])
    d.table(rows, [3000, 1100, 1500, 1500, 1500, 1300])
    if multi:
        d.para("Room at today's mix: extra clients on that offer that fit beside the ones you have. "
               "Ceiling on its own: clients you could hold if all your client hours went to that offer.",
               size=8, color="555555", after=40)
    if res["ready_now"] and res["T_you_total"] >= 1:
        n = len(res["ready_now"])
        b = next((r for r in res["offers"] if r["name"] == res["binding"]), None)
        extra = ""
        if b and b["ceiling_with_T_whole"] is not None and b["T_you"] > 0 and b["ceiling_with_T_whole"] != b["ceiling_whole"]:
            extra = f" Until they move, your ceiling on {b['name']} is {b['ceiling_with_T_whole']}, not {b['ceiling_whole']}."
        names = ", ".join(x["step"] for x in res["ready_now"][:4])
        d.para(f"**Ready to go now:** {fmt_h(res['T_you_total'])} hours a month on {n} T {plural(n, 'step')} you still do "
               f"yourself ({names}). They need no write-up, so they are not in the ceiling.{extra}", size=9, after=50)
    d.heading("Hand these over first", before=90, after=20)
    if res["picks"]:
        basis = ("Picked by you." if res["founder_picked"] else
                 "Ranked by your hours a month across clients: hours each time x how often x clients.")
        d.para(basis, size=8, color="555555", after=40)
    if res["picks"]:
        rows = [["", "Step", "Offer", "Your hours a month it frees", "Why it can move once written"]]
        for i, a in enumerate(res["picks"], 1):
            rows.append([str(a["rank"]), a["step"], ", ".join(a["offers"]), fmt_h(a["freed"]), a["reason"] or "[NEED: why]"])
        d.table(rows, [350, 2500, 1700, 1250, 4100])
        if res["unassigned_moving"] > 0:
            d.para(f"{fmt_h(res['unassigned_moving'])} hours a month of this work has no named person yet.", size=9, after=30)
    else:
        d.para("Nothing is flagged W. Everything you do is either judgement clients pay for (F) or ready to go now (T).", size=10)
    if biz.get("lead") != "helpers":
        for line in helper_lines(biz, res):
            d.para(A(line), size=9, after=30)
    hc = res["hours_check"]
    if hc is None:
        d.para(f"**Hours check:** your steps come to {fmt_h(res['you_steps_week'])} hours a week of your time. If your week "
               "feels fuller than that, hours are missing from the list (often messages, chasing and rework), and the ceiling "
               "reads high. Logging one normal week settles it.", size=9, after=30)
    if hc and hc["flag"] == "missing":
        d.para(f"**Hours check:** the steps you do come to {fmt_h(hc['steps_month'])} hours a month, but you said delivery takes "
               f"{fmt_h(hc['now_month'])}. About {fmt_h(hc['gap'])} hours a month are missing from the list (often email, chasing "
               "and rework). Until they are added, the ceiling reads high.", size=9, after=30)
    elif hc and hc["flag"] == "over":
        d.para(f"**Hours check:** the steps you do come to {fmt_h(hc['steps_month'])} hours a month, above the "
               f"{fmt_h(hc['now_month'])} you said delivery takes now. Check the step hours; if they are right, delivery is "
               "already spilling into your selling and admin time.", size=9, after=30)
    d.heading("Your order of moves", before=90)
    for i, m in enumerate(order_of_moves(res), 1):
        d.para(A(f"{i}. {m}"), size=9, after=30, indent=260)
    d.para(A(WHY_ORDER), size=8.5, color="555555", after=60)
    if note_text and lead != "note":
        d.heading("For you", before=90)
        d.para(note_text.strip(), size=9.5, after=50)
    d.heading("What this rests on", size=10, before=80)
    for a in assumption_lines(biz, res, assumptions):
        d.para(A(a), size=7.5, color="444444", after=0)
    for n in needs:
        if biz["delivery_hours_src"] == "default" and n.startswith("delivery hours: not given"):
            continue  # already said at the top of the page
        if n.startswith("the week you want: the ceiling takes"):
            continue  # said under the headline
        d.para(f"[NEED: {n}]", size=7.5, color="444444", after=0)
    return d


# ------------------------------------------------------------------ note gate
UNIT_AFTER = r"\s*(clients?|steps?|hours?|hrs?|weeks?|months?|moves?|offers?|days?|calls?|minutes?|mins?|people|times|sessions?|rounds?|projects?|members?|x)\b"
COMPARE = (r"\b(double[sd]?|doubling|triple[sd]?|tripling|quadruple[sd]?|twice (as|the|that|what)|half (as|the|of|what)|"
           r"(\d+(\.\d+)?|two|three|four|five|six|seven|eight|nine|ten) times (as|the|more|less|over|what|that|your)|"
           r"(\d+(\.\d+)?|two|three|four|five|six|seven|eight|nine|ten)-fold|(\d+(\.\d+)?|two|three|four|five|six|seven|eight|nine|ten)x (more|the|your))\b")
PROMISES = r"\b(guarantee[sd]?|you will (make|earn|double|free)|will double|will triple|double your|triple your|definitely|certainly will)\b"


def note_problems(note, biz, offers, steps, helpers, res, data=None, prev=None):
    probs = []
    words = len(re.findall(r"\b\w[\w'-]*\b", note))
    if words > 120:
        probs.append(f"note is {words} words; keep it to 120")
    for m in re.finditer(COMPARE, note, re.I):
        probs.append(f"'{m.group(0)}' is a comparison worked out in prose; give the two figures the calculator printed instead")
    if re.search(PROMISES, note, re.I):
        probs.append("the note promises a result; say what the figures show instead")
    allowed = set()

    def add(x):
        if x is None or isinstance(x, (str, bool)):
            return
        for v in (x, round(x, 1), round(x), math.floor(x), math.ceil(x)):
            v = float(v)
            allowed.add(str(int(round(v))) if abs(v - round(v)) < 0.05 else f"{v:.1f}")
            allowed.add(f"{v:.1f}")
        allowed.add(f"{x:.2f}")

    def walk(o):
        if isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
        elif isinstance(o, (int, float)) and not isinstance(o, bool):
            add(abs(float(o)))
            if 0 < abs(o) <= 10:
                allowed.add(f"{round(abs(o) * 100):.0f}%")
                allowed.add(f"{abs(o) * 100:.1f}%")
    walk(res)
    walk(prev or {})
    walk({"b": {k: v for k, v in biz.items()}, "o": offers, "s": steps, "h": helpers})
    named = " ".join([biz["business"]] + [o["name"] for o in offers] + [s["step"] for s in steps] + [h["name"] for h in helpers])
    for m in re.finditer(r"\d+", named):
        allowed.add(m.group(0))
    given = {k: v for k, v in (data or {}).items() if k not in ("sources", "date")}
    for m in re.finditer(r"\d+(?:[.,]\d+)?", json.dumps(given, ensure_ascii=False)):
        g = m.group(0)
        allowed.add(g.replace(",", ".") if STYLE["decimal"] == "comma" else g)  # the founder's own figures, as they gave them
        allowed.update(re.findall(r"\d+", g))
    for m in re.finditer(r"(?<![\w.,])(\d[\d,.]*\d|\d)(\s?%?)", note):
        raw_tok = m.group(1)
        tok = (raw_tok.replace(".", "").replace(",", ".") if STYLE["decimal"] == "comma" else raw_tok.replace(",", ""))
        tok = tok.rstrip(".")
        m_pct = m.group(2).strip()
        if m_pct:
            if tok + "%" not in allowed and f"{float(tok):.0f}%" not in allowed:
                probs.append(f"'{tok}%' is not a share the calculator worked out")
            continue
        if re.fullmatch(r"(19|20)\d\d", tok):
            continue
        if tok in allowed:
            continue
        try:
            v = float(tok)
        except ValueError:
            continue
        after = note[m.end():m.end() + 20]
        if v <= 12 and v == int(v) and re.match(UNIT_AFTER, after, re.I):
            continue
        probs.append(f"'{tok}' is not a figure the calculator printed or the founder gave")
    return probs


# ------------------------------------------------------------------ return-run changes
def compare_previous(prev, biz, res, steps):
    out = []
    when = prev.get("date") or "your last check"
    pb = prev.get("result_offers") or {}
    for r in res["offers"]:
        p = pb.get(r["name"])
        if not p:
            out.append(f"New offer: {r['name']}.")
            continue
        bits = []
        if p.get("active") is not None and r["active"] is not None and p["active"] != r["active"]:
            bits.append(f"clients {fmt_h(p['active'])} to {fmt_h(r['active'])}")
        if p.get("FW") is not None and abs(p["FW"] - r["FW"]) > 0.05:
            bits.append(f"your hours per client {fmt_h(p['FW'])} to {fmt_h(r['FW'])}")
        if p.get("ceiling_whole") != r["ceiling_whole"]:
            bits.append(f"ceiling {p.get('ceiling_whole', '?')} to {r['ceiling_whole'] if r['ceiling_whole'] is not None else 'no limit'}")
        out.append(f"{r['name']}: " + (", ".join(bits) if bits else "no change") + ".")
    for name in pb:
        if name not in {r["name"] for r in res["offers"]}:
            out.append(f"Dropped offer: {name}.")
    pf = prev.get("step_flags") or {}
    for s in steps:
        key = f"{s['offer']}|{s['step']}"
        if key in pf and pf[key] != s["counted"]:
            out.append(f"{s['step']} ({s['offer']}): {pf[key]} to {s['counted']}.")
    pa = prev.get("available_month")
    if pa is not None and abs(pa - res["available_month"]) > 0.05:
        out.append(f"Delivery hours a month: {fmt_h(pa)} to {fmt_h(res['available_month'])}.")
    if out:
        out.insert(0, f"Compared with {long_date(when, biz['date_order'])}:")
    return out


# ------------------------------------------------------------------ results file
def results_json(biz, offers, steps, helpers, needs, notes, assumptions, res, data):
    return {
        "skill": "revos-delivery-capacity-check", "date": biz["date"], "business": biz,
        "inputs": data, "offers": res["offers"], "available_month": res["available_month"],
        "total_load": res["total_load"], "status": res["status"], "binding": res["binding"],
        "handover": [{k: a[k] for k in ("rank", "step", "offers", "freed", "picked", "reason")} for a in res["ranked"]],
        "result_offers": {r["name"]: {"active": r["active"], "FW": r["FW"], "ceiling_whole": r["ceiling_whole"],
                                      "ceiling_after_whole": r["ceiling_after_whole"]} for r in res["offers"]},
        "step_flags": {f"{s['offer']}|{s['step']}": s["counted"] for s in steps},
        "headline": headline(biz, res), "week": week_line(biz, res).replace("**", ""), "after": after_line(res),
        "overhead": res["overhead"], "needs": needs, "notes": notes,
    }


def plausibility(biz, res):
    """Headline figures that are probably a misreading: asked before anything is built (Build Standard 13)."""
    asks = []
    conf = set(biz.get("confirmed") or [])
    hc = res["hours_check"]
    if hc and hc["flag"] == "missing" and hc["share_missing"] > HOURS_GAP_STOP and "hours_gap" not in conf:
        asks.append(f"Your steps come to {fmt_h(hc['steps_month'])} hours a month but you said delivery takes {fmt_h(hc['now_month'])}, "
                    f"so {fmt_h(hc['gap'])} hours a month are not in the list and the ceiling would read high. What's missing: "
                    "client messages, chasing, rework, travel, team time? (Add the steps; if the founder cannot place them, "
                    "add \"hours_gap\" to confirmed and the reading says the ceiling reads high.)")
    for r in res["offers"]:
        if r["per_hour"] is not None and r["per_hour"] < 1 and "price" not in conf:
            asks.append(f"I read the {r['name']} price as {fmt_money(r['price'], r['affix'])}, which pays "
                        f"{fmt_money(r['per_hour'], r['affix'])} for each hour of yours. Is that the right price? "
                        "(If it is, add \"price\" to confirmed.)")
    return asks


# ------------------------------------------------------------------ CSV exports (Notion, Asana, ClickUp, Trello, a spreadsheet)
CSV_COLS = {
    "step": r"^(name|task|task name|step|title|activity|item)$",
    "client": r"^(client|customer|account|company|project)$",
    "offer": r"^(type|offer|service|package|category|project type|product)$",
    "owner": r"^(assignee|assignees|owner|who|assigned to|person|done by)$",
    "hours": r"(est|estimate|hours|hrs|time|duration|effort)",
    "how_often": r"^(recurring|recurrence|frequency|how often|repeat|repeats|cadence)$",
    "notes": r"^(notes?|comments?|description)$",
}


def import_csv(path, out=None):
    """Collapse a task export into draft steps: one row per offer and task name, hours as an '=' sum of the
    rows' own figures (read through locale_numbers), so the founder can see exactly how it was collapsed."""
    import csv
    p = Path(path)
    if not p.exists():
        raise Stop(f"there is no file at {path}")
    text = p.read_text(encoding="utf-8-sig", errors="replace")
    rows = list(csv.DictReader(text.splitlines()))
    if not rows:
        raise Stop("the CSV has no rows under its header")
    heads = list(rows[0].keys())
    col = {}
    for k, pat in CSV_COLS.items():
        col[k] = next((h for h in heads if h and re.search(pat, h.strip().lower())), None)
    if not col["step"]:
        raise Stop(f"could not find the task name column in {heads}")
    STYLE["decimal"] = LN.detect_decimal_style([r.get(col["hours"]) or "" for r in rows]) if col["hours"] else None
    groups = {}
    for r in rows:
        name = (r.get(col["step"]) or "").strip()
        if not name:
            continue
        offer = (r.get(col["offer"]) or "").strip() if col["offer"] else ""
        g = groups.setdefault((offer, name), {"offer": offer, "step": name, "values": [], "raw": [], "blank": 0,
                                               "owners": [], "often": [], "clients": [], "notes": []})
        hv = (r.get(col["hours"]) or "").strip() if col["hours"] else ""
        if hv:
            try:
                v, _n = parse_hours(hv)
            except Ask as e:
                raise Stop(f"the hours '{hv}' for {name} read two ways ({e}). Ask the founder which")
            if v is None:
                g["raw"].append(f"{hv} (unread)")
            else:
                g["values"].append(v)
                g["raw"].append(hv)
        else:
            g["blank"] += 1
        for k in ("owners", "often", "clients", "notes"):
            c = {"owners": "owner", "often": "how_often", "clients": "client", "notes": "notes"}[k]
            if col[c] and (r.get(col[c]) or "").strip():
                g[k].append(r[col[c]].strip())
    steps, lines = [], []
    for g in groups.values():
        vals = g["values"]
        if len(vals) > 1:
            hours = "=(" + "+".join(f"{v:g}" for v in vals) + f")/{len(vals)}"
        elif vals:
            hours = f"{vals[0]:g}"
        else:
            hours = None
        owners = sorted(set(g["owners"]))
        often = max(set(g["often"]), key=g["often"].count) if g["often"] else None
        steps.append({"offer": g["offer"], "step": g["step"], "hours": hours, "how_often": often,
                      "owner": owners[0] if len(owners) == 1 else (", ".join(owners) if owners else None),
                      "flag": None, "reason": None})
        avg = (sum(vals) / len(vals)) if vals else None
        blank = f" and {g['blank']} blank" if g["blank"] else ""
        lines.append(f"  {g['step']} ({g['offer'] or 'no type'}): {len(g['raw']) + g['blank']} {plural(len(g['raw']) + g['blank'], 'row')}, "
                     f"{len(set(g['clients']))} {plural(len(set(g['clients'])), 'client')}; hours {', '.join(g['raw']) or 'none'}{blank}"
                     f" -> {hours or '[NEED: hours]'}{f' = {fmt_h(avg)} each time' if avg is not None else ''}; "
                     f"who: {', '.join(owners) or '?'}; how often: {often or '?'}"
                     + (f"; notes: {'; '.join(sorted(set(g['notes'])))[:120]}" if g["notes"] else ""))
    print(f"READ {len(rows)} rows into {len(steps)} draft steps (columns used: " +
          ", ".join(f"{k}={v}" for k, v in col.items() if v) + ")")
    print("\n".join(lines))
    print("Draft only: map the founder's own name to 'me', check each 'how often' (a recurring row may already be per client "
          "or for all clients at once), add the steps exports miss (client messages, chasing, standups, reviewing the team's "
          "work), and read the list back to the founder before computing.")
    if out:
        Path(out).write_text(json.dumps({"steps": steps}, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"WROTE: {out}")
    return 0


# ------------------------------------------------------------------ CLI
TEMPLATE = {
    "business": None, "date": None, "country": None, "english": None, "number_style": None, "paper": None,
    "delivery_hours_week": None, "working_hours_week": None, "selling_admin_hours_week": None,
    "target_working_hours_week": None, "target_delivery_hours_week": None,
    "delivery_hours_now_week": None, "working_weeks_year": None, "weeks_off_year": None,
    "day_hours": None, "working_days_week": None,
    "helper_planning_line": None, "helper_low_line": None, "handover_count": None, "lead": None,
    "helpers": [{"name": None, "kind": None, "hours_week": None}],
    "offers": [{"name": None, "billing": None, "active_clients": None, "months_per_client": None, "price": None}],
    "steps": [{"offer": None, "step": None, "hours": None, "how_often": None, "owner": None, "flag": None,
               "reason": None, "gate": None, "handover": None, "check_hours_after": None, "handover_to": None}],
    "confirmed": [], "sources": {},
}


def load_inputs(p):
    path = Path(p)
    if not path.exists():
        raise Stop(f"there is no inputs file at {p}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise Stop(f"the inputs file is not valid JSON (line {e.lineno}: {e.msg}). Fix it and run again")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("template")
    c = sub.add_parser("compute")
    c.add_argument("inputs")
    b = sub.add_parser("build")
    b.add_argument("inputs")
    b.add_argument("--out", required=True)
    b.add_argument("--results", required=True)
    b.add_argument("--note")
    b.add_argument("--previous")
    ic = sub.add_parser("import-csv")
    ic.add_argument("csv")
    ic.add_argument("--out")
    a = ap.parse_args()
    if a.cmd == "template":
        print(json.dumps(TEMPLATE, indent=2))
        return 0
    if a.cmd == "import-csv":
        return import_csv(a.csv, a.out)
    if a.cmd not in ("compute", "build"):
        ap.print_help()
        return 2
    data = load_inputs(a.inputs)
    biz, offers, steps, helpers, needs, notes, assumptions = normalise(data)
    res = compute(biz, offers, steps, helpers)
    asks = plausibility(biz, res)
    if a.cmd == "compute":
        print(report(biz, offers, steps, helpers, needs, notes, assumptions, res))
        for x in asks:
            print("CHECK BEFORE BUILDING:", x)
        return 1 if needs or asks else 0
    if asks:
        raise Stop("a headline figure looks wrong. Ask the founder in one message, then run again:\n" +
                   "\n".join(f"ASK: {x}" for x in asks))
    changes, prev = [], None
    if a.previous:
        if not Path(a.previous).exists():
            raise Stop(f"there is no previous results file at {a.previous}")
        prev = json.loads(Path(a.previous).read_text(encoding="utf-8"))
        changes = compare_previous(prev, biz, res, steps)
    note_text = ""
    if a.note:
        if not Path(a.note).exists():
            raise Stop(f"there is no note file at {a.note}")
        note_text = Path(a.note).read_text(encoding="utf-8").strip()
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import check_copy
        cp, _w, _n = check_copy.check(note_text)
        probs = note_problems(note_text, biz, offers, steps, helpers, res, data, prev) + [f"banned pattern: {x}" for x in cp]
        if probs:
            for p in probs:
                print("PROBLEM:", p)
            raise Stop("the note failed its checks. Rewrite it using only figures printed by compute, then build again")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    base = f"capacity-check-{slug(biz['business'])}-{biz['date']}"
    docx_p, xlsx_p = out / f"{base}.docx", out / f"{base}-workings.xlsx"
    written = []
    try:
        build_docx(docx_p, biz, res, note_text, assumptions, needs, changes)
        written.append(docx_p)
        build_xlsx(xlsx_p, biz, offers, steps, helpers, res, assumptions, needs)
        written.append(xlsx_p)
        rp = Path(a.results)
        rp.parent.mkdir(parents=True, exist_ok=True)
        rp.write_text(json.dumps(results_json(biz, offers, steps, helpers, needs, notes, assumptions, res, data),
                                 indent=2, default=str), encoding="utf-8")
    except Exception:
        for p in written:
            try:
                p.unlink()
            except OSError:
                pass
        raise
    print(report(biz, offers, steps, helpers, needs, notes, assumptions, res))
    for c in changes:
        print("CHANGED:", c)
    print(f"WROTE: {docx_p}")
    print(f"WROTE: {xlsx_p}")
    print(f"WROTE: {a.results} (for the memory file; not for the founder)")
    return 1 if needs else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Stop as e:
        print(f"STOP: {e}. Nothing was written.")
        sys.exit(2)
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print(f"STOP: the calculation could not finish ({type(e).__name__}: {e}). Nothing was written. "
              "Check the inputs file against references/intake-guide.md and run again.")
        sys.exit(2)
