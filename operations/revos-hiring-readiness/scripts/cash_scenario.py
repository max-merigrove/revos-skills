#!/usr/bin/env python3
"""Hiring Readiness Check: reading the founder's figures and the 13-week cash scenario.

Usage:
  python3 scripts/cash_scenario.py template                 print a blank inputs file
  python3 scripts/cash_scenario.py compute <inputs.json>    print the week-by-week base and stress balances

The six conditions, the verdict and the files are built by conditions.py and build.py, which
import this file. Values may be messy strings ("18.4k", "about 12", "10 to 12", "2.5k pcm",
"in 4 weeks", "1st Dec", "next Friday"); the script reads them and records what it did.
Missing values get a stated default or a [NEED] flag, never an invented figure.

The hire's cost is always the founder's figure: the fully loaded monthly cost from their accountant or
payroll provider, or pay alone, marked as understating the hire. This file holds no tax rates, employer
charges, wage floors or other jurisdiction rules, and never works one out.

Exit codes: 0 clean, 1 ran with [NEED] flags, 2 STOP (input the script cannot use).
Standard library only. No network calls.
"""
import ast
import calendar
import json
import math
import operator as op
import re
import sys
import unicodedata
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from locale_numbers import (Ambiguous, Unreadable, count_weekdays, detect_decimal_style,  # noqa: E402
                            find_currency, locale_defaults, parse_hours, parse_number)

# ------------------------------------------------------------------ working defaults (Merigrove, stated to the founder)
DEFAULTS = {
    "stress_revenue_cut": (0.20, "in a bad quarter 20% less money comes in than in the last three months"),
    "stress_extra_days": (15.0, "in a bad quarter every payment arrives 15 days later than usual"),
    "cover_target_months": (1.0, "the cash floor is one month of costs, the hire included"),
    "start_weeks": (4.0, "the hire starts four weeks from today"),
    "margin_floor": (0.50, "margin floor: 50% gross margin, a working default for a service business; change it"),
    "contractor_line_hours": (15.0, "under 15 hours a week of work, a contractor is the first route"),
    "near_ceiling": (0.90, "near the ceiling: working at 90% or more of the hours you can give clients"),
    "role_filled_share": (0.80, "a role is coherent when named tasks fill at least 80% of its hours"),
    "season_dip": (0.10, "a month over 10% below the monthly average this check uses is flagged as a possible season"),
}
WEEKS = 13
MAX_WEEKS = 60
WEEKS_PER_MONTH = 52 / 12
SYMBOLS = {"GBP": "£", "USD": "$", "EUR": "€", "AUD": "A$", "CAD": "C$", "NZD": "NZ$", "SGD": "S$",
           "HKD": "HK$", "INR": "₹", "JPY": "¥", "PHP": "₱", "MXN": "MX$"}
HOME = {"USD": "US", "AUD": "AU", "CAD": "CA", "NZD": "NZ", "SGD": "SG", "HKD": "HK", "MXN": "MX"}  # bare "$" at home
AFTER = {"EUR", "CHF", "SEK", "NOK", "DKK", "PLN", "CZK", "HUF"}  # symbol after the figure for a decimal-comma founder
DOLLARS = {"USD", "AUD", "CAD", "NZD", "SGD", "HKD", "MXN"}
DAY_HOURS = 8.0  # "2 days" of work read as 16 hours unless the founder gives day_hours
# Set once per run from the founder's country, locale and figures (set_style, normalise). Never from spelling.
STYLE = {"dates": "dmy", "decimal": None, "country": None, "currency": None, "paper": "A4", "day_hours": DAY_HOURS}


def country_of(country, locale):
    """The founder's ISO country: the country field, else the region part of the locale (en-AU -> AU), else None."""
    c = str(country or "").strip().upper()
    if re.fullmatch(r"[A-Z]{2}", c):
        return c
    loc = str(locale or "").replace("_", "-")
    m = re.search(r"-([A-Za-z]{2})$", loc)
    return m.group(1).upper() if m else None


def set_style(locale, country=None, decimal=None, currency=None, mark=None, bare_dollar=True):
    """Date order and paper size from the founder's country (locale_defaults), never from their spelling."""
    c = country_of(country, locale)
    d = locale_defaults(c)
    STYLE.update({"dates": d["date_order"].lower(), "paper": d["paper"], "country": c,
                  "decimal": decimal if decimal in ("dot", "comma") else None, "currency": currency,
                  "symbol": str(mark).strip() if mark else None, "bare_dollar": bare_dollar is not False})
    return STYLE["dates"]


class InputError(Exception):
    """An input the script cannot use. Shown as one plain STOP line."""


class AskFounder(InputError):
    """A figure that reads two ways, reads not at all, or fails a plausibility check: one plain question each."""

    def __init__(self, questions):
        self.questions = [questions] if isinstance(questions, str) else list(questions)
        super().__init__("; ".join(self.questions))


# ------------------------------------------------------------------ messy numbers (locale_numbers does the reading)
FILLER = (r"\b(?:about|roughly|around|approx\.?|circa|maybe|say|probably|prob|between|like|just under|just over|"
          r"give or take|est\.?|estimated|or so)\b|~|\?")
TAILS = (r"\b(?:pcm|p\.c\.m\.?|monthly|yearly|annually|weekly|each|all[ -]in|all up|fully loaded|in total|total|"
         r"incl(?:uding|\.)?(?:\s+[a-z]+)?|a mo|per annum|/m|/mth|/wk|/week|/w)\b")
WEEK_TAIL = r"\s*(?:a|per|/|each|every)\s*(?:week|wk)\b|\s*(?:pw|p/w|weekly)\b"
NUM_TOKEN = re.compile(r"\d[\d.,']*\d|\d")


def _safe_eval(expr):
    ops = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv, ast.USub: op.neg, ast.UAdd: op.pos}

    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool):
            return float(n.value)
        if isinstance(n, ast.BinOp) and type(n.op) in ops:
            return ops[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in ops:
            return ops[type(n.op)](ev(n.operand))
        raise ValueError("not plain arithmetic")
    return ev(ast.parse(expr, mode="eval"))


def fmt_plain(v, dp=None):
    """A number in the founder's own style: 1,234.5 or 1.234,5."""
    if v is None:
        return "[NEED]"
    if dp is None:
        dp = 0 if abs(v) >= 10 else 2
    s = f"{v:,.{dp}f}"
    if dp and "." in s:
        s = s.rstrip("0").rstrip(".")
    if STYLE.get("decimal") == "comma":
        s = s.replace(",", "\u0000").replace(".", ",").replace("\u0000", ".")
    return s


def _pre(s):
    s = unicodedata.normalize("NFKC", str(s)).strip()
    s = re.sub(FILLER, " ", s, flags=re.I)
    return re.sub(r"\s+", " ", s).strip()


def _one(text, label, decimal):
    """One figure through locale_numbers, with the skill's own unit words stripped first."""
    t = re.sub(TAILS, " ", text, flags=re.I).strip()
    try:
        return parse_number(t, decimal)[0]
    except Ambiguous as e:
        raise AskFounder(f"{label}: {e}")
    except Unreadable:
        toks = re.findall(r"-?\d[\d.,']*(?:\s*(?:k|m|mn|bn|million|thousand|grand|lakh|crore|cr)\b)?", t, re.I)
        if len(toks) == 1 and len(NUM_TOKEN.findall(t)) == 1:
            pre = t[:t.find(toks[0].lstrip("-")[0])]
            sym = re.findall(r"[^\w\s]{1,3}\$?|[A-Z]{3}", pre)
            try:
                return parse_number((sym[-1] if sym else "") + toks[0], decimal)[0]
            except (Ambiguous, Unreadable):
                pass
        raise AskFounder(f"{label}: '{text}' could not be read as one figure; ask the founder to give it as one number")


def _expr(s, label, decimal, notes, raw):
    ex = s[1:] if s.startswith("=") else s
    ex = re.sub(r"(?<=\d)\s*[x\u00d7]\s*(?=[\d(])", " * ", ex, flags=re.I)
    out = []
    pos = 0
    for mm in re.finditer(r"(\d[\d.,']*)\s*(k|m)?\b", ex, re.I):
        out.append(ex[pos:mm.start()])
        val = parse_number(mm.group(1) + (mm.group(2) or ""), decimal)[0]
        out.append(repr(val))
        pos = mm.end()
    out.append(ex[pos:])
    body = re.sub(r"[^\d.eE+\-*/() ]", " ", "".join(out))
    val = _safe_eval(body)
    if notes is not None:
        notes.append(f"{label}: {fmt_plain(val, 2)}, worked out from {re.sub(r'\s*\*\s*', ' x ', str(raw).lstrip('=').strip())}")
    return val


def to_num(v, notes=None, label="", decimal=None):
    """Read one founder-typed figure in their own number style (decimal point or comma, Indian grouping, k, lakh,
    million). Ranges become their midpoint (noted); sums of parts ("8 + 3 + 2", "=4450 - 1200") are worked out here,
    never by eye. Hours fields read days, minutes and weekday sets. A figure that reads two ways or not at all raises
    AskFounder with one plain question."""
    decimal = decimal or STYLE.get("decimal")
    label = label or "a figure"
    hours_field = "hour" in label.lower()
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, (list, dict)):
        raise InputError(f"{label} should be one figure, not a list")
    raw = str(v)
    s = _pre(raw)
    low = s.lower()
    if low in ("", "none", "nil", "zero", "n/a", "na", "unknown", "not known", "dont know", "don't know", "idk", "skip", "-", "nothing"):
        return 0.0 if low in ("none", "nil", "zero", "nothing") else None
    cur = find_currency(raw)
    want = STYLE.get("currency")
    if want and cur and "_OR_" not in cur and cur not in ("DOLLAR", "PESO", "SHILLING", want) and not (cur == "JPY" and want == "CNY"):
        raise AskFounder(f"{label}: '{raw}' is written in {cur}, but the check runs in {want}; which currency is it?")
    if hours_field:
        s = re.sub(WEEK_TAIL, "", s, flags=re.I).strip()
    if s.startswith("=") or re.search(r"\d\s*(?:k\b)?\s*[+*/x\u00d7]\s*[\d(]", s, re.I):
        try:
            return _expr(s, label, decimal, notes, raw)
        except (ValueError, SyntaxError, ZeroDivisionError):
            raise AskFounder(f"{label}: '{raw}' could not be worked out as a sum; give the parts or one figure")
        except Ambiguous as e:
            raise AskFounder(f"{label}: {e}")
    if hours_field:
        if re.search(r"\b(mon|tue|wed|thu|fri|sat|sun)[a-z]*\b|\bweekdays?\b", low) and not re.search(r"\d\s*(h|hr|hour)", low):
            try:
                n = count_weekdays(low)
            except Unreadable as e:
                raise AskFounder(f"{label}: {e}")
            m = re.search(r"(\d+(?:[.,]\d+)?)\s*days?", low)
            if m and abs(float(m.group(1).replace(",", ".")) - n) > 1e-9:
                raise AskFounder(f"{label}: '{raw}' says {m.group(1)} days but names {n}; which is it?")
            h = n * STYLE.get("day_hours", DAY_HOURS)
            if notes is not None:
                notes.append(f"{label}: '{raw}' read as {n} days of {fmt_plain(STYLE.get('day_hours', DAY_HOURS), 1)} hours, {fmt_plain(h, 1)} hours")
            return h
        if re.match(r"\s*-\s*\d", s):
            return -to_num(s.strip()[1:], notes, label, decimal)
        try:
            h, hn = parse_hours(s, day_hours=STYLE.get("day_hours", DAY_HOURS), decimal=decimal)
        except Ambiguous as e:
            raise AskFounder(f"{label}: {e}")
        except Unreadable:
            tail = re.search(r"\d.*$", s)
            if tail and tail.group(0) != s:
                try:
                    return parse_hours(tail.group(0), day_hours=STYLE.get("day_hours", DAY_HOURS), decimal=decimal)[0]
                except (Ambiguous, Unreadable):
                    pass
            return _one(s, label, decimal)
        if notes is not None and any("midpoint" in x for x in hn):
            notes.append(f"{label}: read '{raw}' as the midpoint, {fmt_plain(h, 2)}")
        return h
    rng = re.fullmatch(r"(.*?\d)\s*(k|m)?\s*(?:-|\u2013|\bto\b|\bor\b|\band\b)\s*([^\d\s]{0,3}\s?\d.*?)", s, re.I)
    if rng:
        try:
            left = rng.group(1) + (rng.group(2) or "")
            right = rng.group(3)
            if not rng.group(2) and re.search(r"\d\s*(k|m)\b", right, re.I) and not re.search(r"[kKmM]\b", left):
                left += re.search(r"(k|m)\b", right, re.I).group(1)
            a, b = _one(left, label, decimal), _one(right, label, decimal)
            mid = (a + b) / 2
            if notes is not None:
                notes.append(f"{label}: read '{raw}' as the midpoint, {fmt_plain(mid, 2)}")
            return mid
        except AskFounder:
            pass
    return _one(s, label, decimal)


def to_pct(v, notes=None, label="", limit=None):
    """'20%', '20', '1' and '0.2' are percentages: a bare number of 1 or more is per cent, below 1 a fraction.
    '1,4%' reads in the founder's decimal style. Ranges ('55-60%') give the midpoint, noted."""
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        x = float(v)
        x = x / 100 if x >= 1 else x
    else:
        s = str(v).strip().lower()
        odds = re.fullmatch(r"(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)", s)
        if s in ("fifty-fifty", "fifty fifty", "coin flip", "evens") or (odds and abs(float(odds.group(1)) + float(odds.group(2)) - 100) < 1e-9):
            return 0.5 if not odds else float(odds.group(1)) / 100  # "50/50", "60/40": odds out of 100, never a division
        if s in ("closed", "shut", "all", "everything"):
            return 1.0
        has = bool(re.search(r"%|per ?cent|pct", s))
        x = to_num(re.sub(r"%|per ?cent|pct", " ", s), notes, label)
        if x is None:
            return None
        if has or x >= 1:
            x = x / 100
    if x < 0:
        raise InputError(f"{label} cannot be negative (read '{v}')")
    if limit is not None and x >= limit:
        raise InputError(f"{label} of {x * 100:.0f}% cannot be right. Check the figure and run again")
    return x


def yes_no(v):
    s = str(v or "").strip().lower()
    if not s or s in ("unknown", "not sure", "dont know", "don't know", "?", "skip", "n/a", "idk"):
        return None
    if re.match(r"(y|yes|yep|yeah|yup|true|included|incl|inc|it does|they do|partly written|written|of course|sure)\b", s):
        return True
    if re.match(r"(n|no|nope|false|not|excluded|excl|none)\b", s):
        return False
    return None


PRICE_UP = re.compile(r"\b(raised|raise|put (?:them |prices |rates |fees )?up|increased|increase|bumped|went up|gone up|"
                      r"hiked|lifted|up\s+(?:by\s+)?[^\s]*\d|(?:prices?|rates?|fees?|retainers?|bouquets?)\s+(?:are\s+|were\s+)?up|"
                      r"new (?:price|rate)s?|higher (?:price|rate)s?)\b", re.I)
PRICE_NOT = re.compile(r"^\s*(?:no|nope|not|never|haven'?t|have not|didn'?t|did not|nah)\b|\bnot yet\b|\bno price rise\b", re.I)


def price_rise(v):
    """{'value': True/False/None, 'said': founder's words}. Accepts {'value', 'said'} or the founder's own words
    ("raised prices in May", "fees up $5 in July", "bumped rates 10%")."""
    if isinstance(v, dict):
        said = str(v.get("said") or v.get("value") or "")
        val = yes_no(v.get("value")) if v.get("value") not in (None, "") else None
        return {"value": val if val is not None else price_rise(said)["value"], "said": said}
    s = str(v or "").strip()
    if PRICE_NOT.search(s):
        return {"value": False, "said": s}
    if PRICE_UP.search(s):
        return {"value": True, "said": s}
    return {"value": yes_no(s), "said": s}


def written(v):
    """yes, partly, no or unknown, from the founder's words about whether a task is written down."""
    s = str(v or "").strip().lower()
    if not s or s in ("unknown", "not sure", "dont know", "don't know", "?", "skip", "n/a", "idk"):
        return "unknown"
    if re.match(r"(no|not|nothing|none|nope|never|in my head|only in my head)\b", s):
        return "no"
    if re.search(r"\b(partly|partial|partially|sort of|kind of|kinda|some of it|somewhat|half|rough(ly)?|bits?|sorta)\b", s):
        return "partly"
    if re.match(r"(y|yes|yep|yeah|written|documented|fully|all of it)\b", s) or re.search(
            r"\b(sop|doc|docs|document|checklist|notion|manual|guide|playbook|template|process written)\b", s):
        return "yes"
    return "unknown"


# ------------------------------------------------------------------ messy dates
MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
MONTHS.update({m.lower(): i for i, m in enumerate(calendar.month_abbr) if m})
MONTHS["sept"] = 9
DAYS = {d.lower(): i for i, d in enumerate(calendar.day_name)}
DAYS.update({d.lower(): i for i, d in enumerate(calendar.day_abbr)})


def to_date(v, today, label=""):
    """'in 4 weeks', '4 weeks', '6 wks', 'next month', 'next Friday', '1st Dec', 'Dec 1', 'December',
    '01/12/2026' (in the date order of the founder's country), '2026-12-01', '2026/12/01', 'now',
    'asap'. Returns a date or None. Past dates move to next year only when no year was written."""
    if v in (None, ""):
        return None
    if isinstance(v, (int, float)):
        return today + timedelta(weeks=float(v))
    s = str(v).strip().lower().replace(",", " ")
    s = re.sub(r"\s+", " ", s)
    if s in ("now", "asap", "today", "immediately", "straight away", "right away"):
        return today
    m = re.fullmatch(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", s)
    if m:
        return _mk(int(m.group(1)), int(m.group(2)), int(m.group(3)), label)
    m = re.fullmatch(r"(\d{1,2})[/.](\d{1,2})(?:[/.](\d{2,4}))?", s)
    if m:
        y = int(m.group(3)) if m.group(3) else today.year
        y = y + 2000 if y < 100 else y
        dd, mo = (int(m.group(2)), int(m.group(1))) if STYLE["dates"] in ("mdy", "ymd") else (int(m.group(1)), int(m.group(2)))
        d = _mk(y, mo, dd, label)
        return d if m.group(3) or d >= today else _mk(y + 1, mo, dd, label)
    m = re.search(r"(?:in |within )?(\d+(?:\.\d+)?|a|one|two|three|four|five|six|eight|ten|twelve)\s*"
                  r"(day|days|wk|wks|week|weeks|month|months|mth|mths)\b", s)
    if m:
        words = {"a": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "eight": 8, "ten": 10, "twelve": 12}
        n = float(words.get(m.group(1), m.group(1)))
        unit = m.group(2)
        if unit.startswith("d"):
            return today + timedelta(days=round(n))
        if unit.startswith("w"):
            return today + timedelta(days=round(n * 7))
        return today + timedelta(days=round(n * 365 / 12))
    if re.search(r"\bnext month\b", s):
        y, mo = (today.year + 1, 1) if today.month == 12 else (today.year, today.month + 1)
        return date(y, mo, 1)
    if re.search(r"\bnext week\b", s):
        return today + timedelta(days=7 - today.weekday())
    m = re.search(r"\b(?:next |this )?(" + "|".join(sorted(DAYS, key=len, reverse=True)) + r")\b", s)
    if m and not re.search(r"\d", s):
        ahead = (DAYS[m.group(1)] - today.weekday()) % 7
        ahead = ahead or 7
        if s.startswith("next") and ahead < 7 and today.weekday() < DAYS[m.group(1)]:
            ahead += 0
        return today + timedelta(days=ahead)
    m = re.search(r"(\d{1,2})(?:st|nd|rd|th)?\s*(?:of\s*)?([a-z]+)\.?\s*(\d{4})?", s)
    if m and m.group(2) in MONTHS:
        y = int(m.group(3)) if m.group(3) else today.year
        d = _mk(y, MONTHS[m.group(2)], int(m.group(1)), label)
        return d if m.group(3) or d >= today else _mk(y + 1, MONTHS[m.group(2)], int(m.group(1)), label)
    m = re.search(r"([a-z]+)\.?\s*(\d{1,2})(?:st|nd|rd|th)?(?:\s*(\d{4}))?\b", s)
    if m and m.group(1) in MONTHS:
        y = int(m.group(3)) if m.group(3) else today.year
        d = _mk(y, MONTHS[m.group(1)], int(m.group(2)), label)
        return d if m.group(3) or d >= today else _mk(y + 1, MONTHS[m.group(1)], int(m.group(2)), label)
    m = re.search(r"(start of |early |beginning of |begin |from |mid |mid-|middle of |end of |late )?([a-z]+)\s*(\d{4})?$", s)
    if m and m.group(2) in MONTHS:
        y = int(m.group(3)) if m.group(3) else today.year
        mo = MONTHS[m.group(2)]
        if not m.group(3) and date(y, mo, 1) < today.replace(day=1):
            y += 1
        pre = (m.group(1) or "").strip()
        day = 15 if pre in ("mid", "mid-", "middle of") else (calendar.monthrange(y, mo)[1] if pre in ("end of", "late") else 1)
        return date(y, mo, day)
    return None


def _mk(y, mo, d, label):
    try:
        return date(y, mo, d)
    except ValueError:
        raise InputError(f"{label or 'a date'} is not a real date ({d}/{mo}/{y})")


def week_of(d, today):
    """Week 1 is the seven days starting today."""
    return max(1, (d - today).days // 7 + 1)


def long_date(d):
    if STYLE["dates"] == "mdy":
        return f"{calendar.month_name[d.month]} {d.day}, {d.year}"
    if STYLE["dates"] == "ymd":
        return d.isoformat()
    return f"{d.day} {calendar.month_name[d.month]} {d.year}"


def symbol(cur):
    """The founder's own currency mark: the mark they write (currency_symbol), else a bare $ at home when they never
    wrote a prefixed one (an Australian founder who writes $3,100 sees $, not A$), else the international mark."""
    if STYLE.get("symbol"):
        return STYLE["symbol"]
    if cur in HOME and STYLE.get("country") == HOME[cur] and STYLE.get("bare_dollar", True):
        return "$"
    return SYMBOLS.get(cur or "", "")


def money(v, cur=None):
    """Money in the founder's style: $1,200 or 1.200 \u20ac to a founder who writes a decimal comma."""
    if v is None:
        return "[NEED]"
    sym = symbol(cur)
    sign = "-" if v < 0 else ""
    small_cents = abs(v) < 100 and abs(round(v, 2) - round(v)) >= 0.005
    if small_cents:
        body = f"{abs(v):,.2f}"
        if STYLE.get("decimal") == "comma":
            body = body.replace(",", "\u0000").replace(".", ",").replace("\u0000", ".")
    else:
        body = fmt_plain(abs(v), 0)
    if sym and cur in AFTER and STYLE.get("decimal") == "comma":
        return f"{sign}{body} {sym}"
    if sym:
        return f"{sign}{sym}{body}"
    return f"{sign}{body} {cur}" if cur else f"{sign}{body}"


def pct(v):
    if v is None:
        return "[NEED]"
    x = v * 100
    dp = 0 if abs(x - round(x)) < 0.05 else 1
    s = f"{x:.{dp}f}"
    if STYLE.get("decimal") == "comma":
        s = s.replace(".", ",")
    return s + "%"


# ------------------------------------------------------------------ normalise
TOP_KEYS = {"business", "currency", "date", "cash_today", "monthly_revenue", "monthly_costs", "costs_include_founder_pay",
            "founder_pay_month", "debtor_days", "known_payments", "revenue_history", "margin_floor",
            "gross_margin_months", "gross_margin_rough", "margin_detail", "recurring_revenue_month",
            "contracted_next_6_months", "repeat_revenue_month", "repeat_share", "pipeline",
            "pipeline_weighted", "role", "tasks", "freed_hours_use", "freed_use_has_revenue_path", "role_coherent",
            "capacity", "price_rise_tested", "contractor_rate_hour", "typical_client_month", "cover_target_months", "stress_revenue_cut", "variable_costs_share",
            "stress_extra_days", "stress_cut_all_revenue", "known_low_periods", "contractor_line_hours", "sources", "notes",
            "locale", "country", "decimal_style", "provisional", "currency_symbol", "day_hours", "payroll_provider_seen", "confirmed_figures"}
NUMERIC_KEYS = ("cash_today", "monthly_revenue", "monthly_costs", "founder_pay_month", "recurring_revenue_month",
                "contracted_next_6_months", "repeat_revenue_month", "pipeline_weighted", "contractor_rate_hour",
                "gross_margin_rough", "repeat_share", "margin_floor", "typical_client_month")


def numeric_strings(raw):
    """Every figure the founder typed, for working out their decimal style once."""
    out = [raw.get(k) for k in NUMERIC_KEYS]
    rh = raw.get("revenue_history")
    out += list(rh.values()) if isinstance(rh, dict) else list(rh or [])
    out += list(raw.get("gross_margin_months") or [])
    for x in raw.get("margin_detail") or []:
        out += [x.get("revenue"), x.get("direct_costs")] if isinstance(x, dict) else []
    out += [p.get("amount") for p in raw.get("known_payments") or [] if isinstance(p, dict)]
    out += [p.get("value") for p in raw.get("pipeline") or [] if isinstance(p, dict)]
    out += [t.get("hours_week") for t in raw.get("tasks") or [] if isinstance(t, dict)]
    r = raw.get("role") if isinstance(raw.get("role"), dict) else {}
    out += [r.get(k) for k in ("monthly_cost", "salary_year", "one_off_costs", "hours_week")]
    cap = raw.get("capacity") if isinstance(raw.get("capacity"), dict) else {}
    out += [cap.get("now"), cap.get("max")]
    return [str(x) for x in out if isinstance(x, str) and x.strip()]


def validate_shape(raw):
    if not isinstance(raw, dict):
        raise InputError("the inputs file must be one JSON object (named fields), not a list or a single value")
    for k in ("role", "capacity", "sources", "role_coherent"):
        if raw.get(k) is not None and not isinstance(raw[k], dict):
            raise InputError(f"'{k}' must be a set of named fields")
    for k in ("known_payments", "tasks", "pipeline", "known_low_periods"):
        if raw.get(k) is not None and not isinstance(raw[k], list):
            raise InputError(f"'{k}' must be a list")
        for i, x in enumerate(raw.get(k) or []):
            if not isinstance(x, dict):
                raise InputError(f"item {i + 1} in '{k}' must be a set of named fields, not '{x}'")
    if raw.get("confirmed_figures") is not None and not isinstance(raw["confirmed_figures"], list):
        raise InputError("'confirmed_figures' must be a list of field names the founder has confirmed")
    rh = raw.get("revenue_history")
    if rh is not None and not isinstance(rh, (list, dict)):
        raise InputError("'revenue_history' must be a list of monthly figures, oldest first, or month: figure pairs")
    gm = raw.get("gross_margin_months")
    if gm is not None and not isinstance(gm, list):
        raise InputError("'gross_margin_months' must be a list, oldest first, e.g. [\"48%\", \"55%\"]")
    if raw.get("decimal_style") not in (None, "", "dot", "comma"):
        raise InputError("'decimal_style' must be dot or comma")
    unknown = sorted(set(raw) - TOP_KEYS)
    if unknown:
        raise InputError(f"unknown field(s) {', '.join(unknown)}; check the spelling against the template")


def _end_date(v, today, label):
    """A 'to' date: a bare month ('Aug', 'August 2027') means the end of that month."""
    s = str(v or "").strip().lower()
    m = re.fullmatch(r"([a-z]+)\.?\s*(\d{4})?", s)
    if m and m.group(1) in MONTHS:
        return to_date(f"end of {s}", today, label)
    return to_date(v, today, label)


def normalise(raw):
    """Turn the founder's figures into clean values. Returns the business dict with needs, notes and assumptions.
    Raises AskFounder when a figure reads two ways or fails a plausibility check."""
    validate_shape(raw)
    needs, notes, assumptions, asks = [], [], [], []
    today = date.fromisoformat(raw["date"]) if raw.get("date") else date.today()
    cur = str(raw.get("currency") or "").strip().upper() or None
    src = raw.get("sources") or {}
    country = country_of(raw.get("country"), raw.get("locale"))
    dec = raw.get("decimal_style") or detect_decimal_style(numeric_strings(raw))
    bare = not any(re.search(r"(?<![A-Za-z])[A-Z]{1,3}\$", s) for s in numeric_strings(raw))
    set_style(raw.get("locale"), country, dec, cur, raw.get("currency_symbol"), bare)
    b = {"business": raw.get("business") or "Your business", "currency": cur, "date": today.isoformat(),
         "locale": raw.get("locale") or None, "country": country, "decimal_style": dec, "paper": STYLE["paper"],
         "date_style": STYLE["dates"], "sources": src, "currency_symbol": raw.get("currency_symbol"), "bare_dollar": bare, "payroll_provider_seen": str(raw.get("payroll_provider_seen") or "").strip()}
    _bn = str(raw.get("business") or "").strip().lower()
    if not _bn or _bn in ("[need]", "business") or _bn.startswith("your ") or _bn.startswith("my "):
        b["business"] = "Your business"
        b.setdefault("defaults_used", []).append("business")
    if not country:
        assumptions.append("No country was given, so dates are read and shown day first and the report is A4 paper (say which country you are in)")
    if cur is None:
        assumptions.append("No currency was given, so figures are shown without a symbol")
    if dec == "comma":
        notes.append("Figures read with a decimal comma, the way you write them")
    dh = to_num(raw.get("day_hours"), None, "Hours in a working day")
    STYLE["day_hours"] = dh if dh and 0 < dh <= 16 else DAY_HOURS
    confirmed = {str(x) for x in raw.get("confirmed_figures") or []}

    def num(key, label, nonneg=True, required=True, need=None):
        v = to_num(raw.get(key), notes, label)
        if v is not None and nonneg and v < 0:
            raise InputError(f"{label} cannot be negative (read '{raw.get(key)}')")
        if v is None and required:
            needs.append(need or f"{label}")
        return v

    b["cash_today"] = to_num(raw.get("cash_today"), notes, "Cash in the bank today")
    if b["cash_today"] is None:
        needs.append("Cash in the bank today (the business account balance)")
    b["monthly_revenue"] = num("monthly_revenue", "Average monthly revenue, last three months",
                               need="Average monthly revenue over the last three months (bank deposits or invoiced sales)")
    b["monthly_costs"] = num("monthly_costs", "Average monthly costs, last three months",
                             need="Average monthly costs over the last three months, everything that leaves the account")
    inc = yes_no(raw.get("costs_include_founder_pay"))
    b["founder_pay_month"] = num("founder_pay_month", "What you pay yourself a month", required=False)
    if inc is False:
        if b["founder_pay_month"] is None:
            needs.append("What you pay yourself a month: your costs leave it out, and the cash scenario needs it")
        else:
            notes.append("Your own pay added to the monthly costs, because the costs you gave leave it out")
    elif inc is None:
        assumptions.append("The monthly costs include what you pay yourself (say if they do not)")
    b["costs_include_founder_pay"] = inc
    b["costs_month_total"] = None
    if b["monthly_costs"] is not None:
        extra = b["founder_pay_month"] if (inc is False and b["founder_pay_month"]) else 0.0
        b["costs_month_total"] = b["monthly_costs"] + extra

    def dflt(key, conv, label):
        v = conv(raw.get(key), notes, label)
        if v is None:
            v, why = DEFAULTS[key]
            assumptions.append(why)
            b.setdefault("defaults_used", []).append(key)
        return v

    b["stress_revenue_cut"] = dflt("stress_revenue_cut", lambda v, n, l: to_pct(v, n, l, limit=1.0), "Stress revenue cut")
    b["stress_extra_days"] = dflt("stress_extra_days", to_num, "Stress extra days")
    vc = to_pct(raw.get("variable_costs_share"), notes, "Costs that move with revenue", limit=1.0) \
        if raw.get("variable_costs_share") not in (None, "") else None
    b["variable_costs_share"] = vc or 0.0
    if vc:
        assumptions.append(f"in a bad quarter costs fall by {pct(vc)} of the revenue lost (your figure for the costs that move with "
                           "revenue); costs are otherwise held at the last three months")
    if raw.get("debtor_days") not in (None, ""):
        notes.append("How fast clients usually pay is already in today's balance; the bad quarter adds the delay to every payment")
    if b["stress_extra_days"] < 0 or b["stress_extra_days"] > 91:
        raise InputError(f"the bad-quarter payment delay must be between 0 and 91 days (read '{raw.get('stress_extra_days')}')")
    b["cover_target_months"] = dflt("cover_target_months", to_num, "Cash floor in months of costs")
    if b["cover_target_months"] <= 0 or b["cover_target_months"] > 24:
        raise InputError("the cash floor must be between a few days and 24 months of costs")
    b["contractor_line_hours"] = dflt("contractor_line_hours", to_num, "Contractor line, hours a week")

    # known payments
    kp = []
    for i, p in enumerate(raw.get("known_payments") or []):
        amt = to_num(p.get("amount"), notes, f"Payment '{p.get('what', i + 1)}'")
        when = to_date(p.get("when"), today, f"date of '{p.get('what', i + 1)}'")
        what = str(p.get("what") or f"Payment {i + 1}")
        if amt is None or when is None:
            needs.append(f"{what}: {'amount' if amt is None else 'date'} (read '{p.get('amount') if amt is None else p.get('when')}')")
            continue
        if amt < 0:
            raise InputError(f"{what} cannot be negative; enter what leaves the account as a positive figure")
        kp.append({"what": what, "amount": amt, "date": when.isoformat(), "week": week_of(when, today)})
    b["known_payments"] = kp

    # known low periods: a closure or a quiet season the founder names, with their own figure for the drop
    lows = []
    for i, x in enumerate(raw.get("known_low_periods") or []):
        what = str(x.get("what") or f"Low period {i + 1}")
        f = to_date(x.get("from"), today, f"start of '{what}'")
        e = _end_date(x.get("to"), today, f"end of '{what}'")
        if f is None or e is None:
            needs.append(f"{what}: the dates it runs from and to")
            continue
        if e < f:
            e = _mk(e.year + 1, e.month, min(e.day, 28) if e.month == 2 else e.day, f"end of '{what}'")
        rc = to_pct(x.get("revenue_cut"), notes, f"{what}: money in lower by", limit=1.0001)
        if rc is None:
            needs.append(f"{what}: how much less comes in over it (for a closure, 100%)")
            continue
        cc = to_pct(x.get("costs_cut"), notes, f"{what}: costs lower by", limit=1.0001) or 0.0
        if e < today:
            notes.append(f"{what} ({long_date(f)} to {long_date(e)}) is already past, so it is not in the scenario")
            continue
        lows.append({"what": what, "from": f.isoformat(), "to": e.isoformat(), "revenue_cut": rc, "costs_cut": cc,
                     "from_said": str(x.get("from")), "to_said": str(x.get("to")),
                     "from_week": max(0.0, (f - today).days / 7), "to_week": ((e - today).days + 1) / 7})
    if len(lows) > 3:
        raise InputError("at most three known low periods; join the ones that touch and leave out the rest")
    b["low_periods"] = lows

    # revenue history (oldest first), with month labels when given as YYYY-MM keys
    rh = raw.get("revenue_history")
    vals, labels = [], []
    if isinstance(rh, dict):
        keys = sorted(rh)
        labels = keys if all(re.fullmatch(r"\d{4}-\d{2}", k) for k in keys) else []
        rh = [rh[k] for k in keys]
    for i, x in enumerate(rh or []):
        v = to_num(x, None, f"Revenue month {i + 1}")
        if v is None:
            raise InputError(f"revenue month {i + 1} ('{x}') is not a figure")
        vals.append(v)
    b["revenue_history"] = vals[-24:]
    b["revenue_months"] = labels[-24:] if labels else []

    # margin
    b["margin_floor"] = dflt("margin_floor", lambda v, n, l: to_pct(v, n, l, limit=1.0), "Margin floor")
    gm = []
    for i, x in enumerate(raw.get("gross_margin_months") or []):
        v = to_pct(x, None, f"Gross margin month {i + 1}", limit=1.0001)
        if v is None:
            raise InputError(f"gross margin month {i + 1} ('{x}') is not a percentage")
        if isinstance(x, str) and re.search(r"\d\s*(?:-|\u2013|to)\s*\d", x):
            raise InputError(f"gross margin month {i + 1} is a range ('{x}'); pass a rough range once as gross_margin_rough")
        gm.append(v)
    for i, x in enumerate(raw.get("margin_detail") or []):
        r = to_num(x.get("revenue"), None, "Revenue")
        c = to_num(x.get("direct_costs"), None, "Direct costs")
        if r is None or c is None or r <= 0:
            raise InputError(f"margin month {i + 1} needs revenue above 0 and direct costs")
        gm.append((r - c) / r)
        notes.append(f"Gross margin month {i + 1}: {pct((r - c) / r)}, worked out from revenue {fmt_plain(r)} and direct costs {fmt_plain(c)}")
    b["gross_margin_months"] = gm[-2:] if gm else []
    b["gross_margin_rough"] = None
    gr = raw.get("gross_margin_rough")
    if gr not in (None, "") and not gm:
        parts = re.split(r"\s*(?:-|\u2013|\bto\b)\s*", re.sub(r"%|per ?cent|about|roughly|around|maybe|~", " ", str(gr), flags=re.I).strip())
        lo_hi = [to_pct(p_ + "%", None, "Rough gross margin", limit=1.0001) for p_ in parts if p_.strip()]
        lo_hi = [x for x in lo_hi if x is not None]
        if lo_hi:
            b["gross_margin_rough"] = {"low": min(lo_hi), "high": max(lo_hi), "said": str(gr)}

    # cover: recurring or contracted revenue, repeat revenue, pipeline
    b["recurring_revenue_month"] = num("recurring_revenue_month", "Recurring or contracted revenue a month", required=False)
    b["contracted_next_6_months"] = num("contracted_next_6_months", "Contracted revenue, next six months", required=False)
    b["repeat_revenue_month"] = num("repeat_revenue_month", "Repeat revenue a month (regulars, memberships, plans)", required=False)
    rs = to_pct(raw.get("repeat_share"), notes, "Share of revenue from returning clients", limit=1.0001)
    b["repeat_from_share"] = False
    if b["repeat_revenue_month"] is None and rs is not None and b["monthly_revenue"] is not None:
        b["repeat_revenue_month"] = rs * b["monthly_revenue"]
        b["repeat_from_share"] = True
        notes.append(f"Repeat revenue a month: {money(b['repeat_revenue_month'], cur)}, worked out as {pct(rs)} of {money(b['monthly_revenue'], cur)}")
    b["repeat_share"] = rs
    # Only revenue under contract for the window escapes the bad-quarter cut; month-to-month recurring revenue can stop.
    sec = b["contracted_next_6_months"] / 6 if b["contracted_next_6_months"] is not None else None
    b["stress_cut_all_revenue"] = yes_no(raw.get("stress_cut_all_revenue")) is True
    b["secured_month"] = 0.0
    if sec and b["monthly_revenue"] and not b["stress_cut_all_revenue"]:
        b["secured_month"] = min(sec, b["monthly_revenue"])
        if sec > b["monthly_revenue"] + 0.5:
            notes.append("Contracted revenue is above the three-month average, so only the average is treated as contracted")
    if b["secured_month"]:
        assumptions.append(f"In the bad quarter your contracted revenue ({money(b['secured_month'], cur)} a month) keeps "
                           "coming in, still late; the cut applies to the rest (say if it should apply to everything)")
    pw = to_num(raw.get("pipeline_weighted"), notes, "Weighted pipeline")
    pl = []
    for i, d in enumerate(raw.get("pipeline") or []):
        val = to_num(d.get("value"), None, "Deal value")
        ch = to_pct(d.get("chance"), None, "Deal chance", limit=1.0001)
        if val is None or ch is None:
            needs.append(f"Pipeline deal '{d.get('name', i + 1)}': value and chance of closing")
            continue
        pl.append({"name": d.get("name") or f"Deal {i + 1}", "value": val, "chance": ch, "weighted": val * ch})
    if pl:
        pw = sum(x["weighted"] for x in pl)
        notes.append("Weighted pipeline: each deal's value times your chance of closing it, added up")
    b["pipeline"] = pl
    b["pipeline_weighted"] = pw

    # the role
    r = raw.get("role") or {}
    role = {"title": r.get("title") or "[NEED: role title]", "type": (r.get("type") or "other").lower(),
            "employment": (r.get("employment") or "undecided").lower()}
    role["hours_week"] = to_num(r.get("hours_week"), notes, "Role hours a week")
    if role["hours_week"] is None:
        needs.append("The role's hours a week")
    elif role["hours_week"] <= 0 or role["hours_week"] > 60:
        raise InputError(f"the role's hours a week must be above 0 and at most 60 (read '{r.get('hours_week')}')")
    role["days"] = str(r.get("days") or "").strip()
    if role["days"] and role["hours_week"]:
        dh_ = to_num(role["days"], None, "Role days, in hours a week")
        if dh_ and abs(dh_ - role["hours_week"]) > 0.1 * role["hours_week"]:
            needs.append(f"The role's hours: {fmt_plain(role['hours_week'], 1)} hours a week, but '{role['days']}' at "
                         f"{fmt_plain(STYLE['day_hours'], 1)} hours a day is {fmt_plain(dh_, 1)}. Which is it? The cost "
                         "you have is for one of them, and the hours change the cost")
            role["hours_conflict"] = dh_
    total = to_num(r.get("monthly_cost"), notes, "Role cost a month")
    role["salary_year"] = to_num(r.get("salary_year"), notes, "Salary a year")
    if (total is not None and total < 0) or (role["salary_year"] is not None and role["salary_year"] < 0):
        raise InputError("the role's costs cannot be negative")
    emp = role["employment"]
    basis = cost_basis(r.get("cost_basis"))
    role["cost_from_salary"] = False
    if total is None and role["salary_year"] is not None:
        total = role["salary_year"] / 12
        basis = "salary_only"
        role["cost_from_salary"] = True
        notes.append(f"Role cost a month: {money(total, cur)}, worked out from the salary of {money(role['salary_year'], cur)} a year / 12 (pay alone)")
    if basis is None and emp == "contractor" and total is not None:
        basis = "loaded"
        assumptions.append("A contractor's monthly cost is what they invoice you, so it is used as the full cost")
    role["monthly_cost"] = total
    role["cost_basis"] = basis  # loaded | salary_only | None (not confirmed)
    role["cost_from"] = str(r.get("cost_from") or "").strip()
    who = cost_who(b)
    if total is None:
        needs.append(f"The role's fully loaded monthly cost: pay plus whatever {who} says goes on "
                     "top of it where you hire (the skill never works this out)")
    elif basis == "salary_only":
        needs.append(f"The fully loaded monthly cost from {who}: the {money(total, cur)} a month used "
                     "is pay alone, so the scenario understates the hire")
    elif basis is None:
        needs.append(f"Whether the {money(total, cur)} a month is pay alone or the fully loaded cost from {who}")
    role["one_off"] = to_num(r.get("one_off_costs"), notes, "One-off costs (recruitment, laptop)") or 0.0
    start = to_date(r.get("start"), today, "start date")
    if start is None:
        start = today + timedelta(weeks=DEFAULTS["start_weeks"][0])
        assumptions.append(DEFAULTS["start_weeks"][1])
        b.setdefault("defaults_used", []).append("start")
    if start < today:
        raise InputError("the start date is in the past; give a start date from today on")
    if (start - today).days > 365:
        raise InputError("the start date is more than a year away; check it, or run the check nearer the time")
    role["start"] = start.isoformat()
    role["start_week"] = week_of(start, today)
    b["season_end_week"] = 0
    for p in lows:
        if p["from_week"] <= 52:
            b["season_end_week"] = max(b["season_end_week"], math.ceil(p["to_week"] - 1e-9))
    b["m3_week"] = m3_week(role["start_week"])
    b["horizon"] = horizon(role["start_week"], b)
    if b["season_end_week"] > MAX_WEEKS:
        notes.append(f"Only the first {MAX_WEEKS} weeks are tested; a low period you named runs past them")
    for p in kp:
        p["in_window"] = p["week"] <= b["horizon"]
    b["role"] = role

    # tasks the role takes off the founder
    tasks = []
    for i, t in enumerate(raw.get("tasks") or []):
        h = to_num(t.get("hours_week"), None, "Task hours a week")
        if h is not None and h < 0:
            raise InputError(f"task '{t.get('task')}' has negative hours")
        tasks.append({"task": str(t.get("task") or f"Task {i + 1}"), "hours_week": h,
                      "written_down": written(t.get("written_down")), "written_said": str(t.get("written_down") or "")})
    b["tasks"] = tasks
    b["freed_hours_use"] = (raw.get("freed_hours_use") or "").strip()
    b["freed_use_has_revenue_path"] = yes_no(raw.get("freed_use_has_revenue_path"))
    rc_ = raw.get("role_coherent") or {}
    b["role_coherent"] = {"value": yes_no(rc_.get("value")), "reason": rc_.get("reason") or ""}

    cap = raw.get("capacity") or {}
    b["capacity"] = {"now": to_num(cap.get("now"), None, "Client hours now"),
                     "max": to_num(cap.get("max"), None, "Client hours at most"),
                     "room_for": to_num(cap.get("room_for"), None, "Room for"),
                     "said": str(cap.get("said") or ""),
                     "unit": cap.get("unit") or "client hours a week"}
    if b["capacity"]["max"] is None and b["capacity"]["now"] is not None and b["capacity"]["room_for"] is not None:
        b["capacity"]["max"] = b["capacity"]["now"] + b["capacity"]["room_for"]
        notes.append(f"The most you can take on is worked out as {fmt_plain(b['capacity']['now'], 1)} now plus room for "
                     f"{fmt_plain(b['capacity']['room_for'], 1)} more {b['capacity']['unit']}.")
    b["provisional"] = bool(raw.get("provisional"))
    b["typical_client_month"] = to_num(raw.get("typical_client_month"), notes, "A typical new client a month")
    if b["capacity"]["max"] is not None and b["capacity"]["max"] <= 0:
        raise InputError("the most you can take on must be above 0")
    b["price_rise_tested"] = price_rise(raw.get("price_rise_tested"))
    b["contractor_rate_hour"] = to_num(raw.get("contractor_rate_hour"), notes, "Contractor rate an hour")
    b["season"] = seasons(b, today)
    b["needs"], b["notes"], b["assumptions"] = needs, notes, assumptions
    asks = [q for k, q in plausibility(b) if k not in confirmed]
    if asks:
        raise AskFounder(asks)
    return b


def cost_who(b):
    """Who gives the loaded figure: the accountant or payroll provider, naming the provider the founder's own data shows."""
    seen = (b or {}).get("payroll_provider_seen")
    return f"your accountant or payroll provider (it looks like you use {seen})" if seen else "your accountant or payroll provider"


def plausibility(b):
    """Headline figures that are almost certainly misread or mistyped: (field, one plain question). The founder's
    confirmation (confirmed_figures) lets a figure through."""
    cur = b["currency"]
    m = lambda v: money(v, cur)  # noqa: E731
    out = []
    cash, rev, cost = b["cash_today"], b["monthly_revenue"], b["costs_month_total"]
    for k, v, lab in (("cash_today", cash, "Cash in the bank today"), ("monthly_revenue", rev, "Monthly revenue"),
                      ("monthly_costs", cost, "Monthly costs")):
        if v is not None and 0 < abs(v) < 1:
            out.append((k, f"{lab} reads as {m(v)}, less than one unit of money. Is that right?"))
    if cash and cost and abs(cash) < cost / 1000:
        out.append(("cash_today", f"Cash in the bank today reads as {m(cash)} against monthly costs of {m(cost)}. Is that the right figure?"))
    if rev and cost and (rev > 20 * cost or cost > 20 * rev):
        out.append(("monthly_revenue", f"Money in reads as {m(rev)} a month and money out as {m(cost)}. One of them looks a thousand times off; which is right?"))
    role = b["role"]
    mc, hrs = role["monthly_cost"], role["hours_week"]
    if mc is not None and hrs:
        hourly = mc / (hrs * WEEKS_PER_MONTH)
        if hourly < 1:
            out.append(("role.monthly_cost", f"The hire's cost reads as {m(mc)} a month for {fmt_plain(hrs, 1)} hours a week, under {m(1)} an hour. Is that the monthly figure?"))
    if mc is not None and rev and mc > rev:
        out.append(("role.monthly_cost", f"The hire's cost reads as {m(mc)} a month, above everything that comes in a month ({m(rev)}). Is that a month or a year?"))
    rate = b["contractor_rate_hour"]
    if rate is not None and 0 < rate < 1:
        out.append(("contractor_rate_hour", f"The contractor's rate reads as {m(rate)} an hour. Is that right?"))
    for p in b["known_payments"]:
        if rev and p["amount"] > 12 * rev:
            out.append(("known_payments", f"{p['what']} reads as {m(p['amount'])}, above a year of revenue. Is that the figure?"))
    cap = b["capacity"]
    if cap["now"] is not None and cap["max"] and cap["now"] > 1.5 * cap["max"]:
        out.append(("capacity", f"You are at {fmt_plain(cap['now'], 1)} {cap['unit']} against a most of {fmt_plain(cap['max'], 1)}. Are those the wrong way round?"))
    return out


def seasons(b, today):
    """Months in the history well below the monthly average this check uses: possible seasons the scenario's flat
    average does not show. Each says whether its next occurrence falls inside the window."""
    rev, vals, labs = b["monthly_revenue"], b["revenue_history"], b["revenue_months"]
    if not rev or not vals:
        return []
    dip = DEFAULTS["season_dip"][0]
    out = []
    covered = [(date.fromisoformat(p["from"]), date.fromisoformat(p["to"])) for p in b["low_periods"]]
    if not labs:
        k = sum(1 for v in vals[-12:] if v < rev * (1 - dip))
        if k:
            out.append({"month": None, "text": f"{k} of your last {min(12, len(vals))} months fell over "
                        f"{pct(dip)} below the {money(rev, b['currency'])} a month this check uses. Give the months "
                        "by name to see whether the next one falls inside the window"})
        return out
    end = today + timedelta(days=7 * b["horizon"] - 1)
    inside, after = [], []
    for lab, v in list(zip(labs, vals))[-12:]:
        if v >= rev * (1 - dip):
            continue
        y, mo = int(lab[:4]), int(lab[5:])
        nxt = date(today.year, mo, 1)
        if nxt < today.replace(day=1):
            nxt = date(today.year + 1, mo, 1)
        nxt_end = date(nxt.year, mo, calendar.monthrange(nxt.year, mo)[1])
        if any(f <= nxt_end and e >= nxt for f, e in covered):
            continue
        item = {"month": lab, "value": v, "inside": nxt <= end, "next": nxt.isoformat(),
                "words": f"{calendar.month_name[mo]} {y} ({money(v, b['currency'])})"}
        (inside if item["inside"] else after).append(item)
    if inside or after:
        txt = f"Months that fell over {pct(dip)} below the {money(rev, b['currency'])} a month this check uses: "
        parts = []
        if inside:
            parts.append(", ".join(x["words"] for x in inside) + ". " + ("Its" if len(inside) == 1 else "Their")
                         + " next turn falls inside the window, which assumes the average")
        if after:
            parts.append(", ".join(x["words"] for x in after) + ". " + ("Its" if len(after) == 1 else "Their")
                         + " next turn falls after the window, so it is not tested")
        out.append({"months": inside + after, "text": txt + "; ".join(parts)})
    return out


# ------------------------------------------------------------------ the scenario
def overlap(a, e, s, f):
    """Length of [a, e) inside [s, f)."""
    return max(0.0, min(e, f) - max(a, s))


def inflow(week, weekly_rev, delay_wk, cut):
    """Cash received in week w (covering [w-1, w) in weeks from today). In a usual quarter money arrives at the
    usual weekly rate. In a bad quarter what arrives is cut by `cut` and arrives delay_wk weeks later, so nothing
    lands until the delay has passed. (The plain case; simulate() adds secured revenue and low periods.)"""
    return weekly_rev * (1 - cut) * overlap(week - 1.0, float(week), delay_wk, 1e9)


def m3_week(start_week):
    """The hire's 13th week: at least week 13."""
    return max(WEEKS, start_week + WEEKS - 1)


def horizon(start_week, biz=None):
    """The scenario runs from today to the 13th week of the hire (at least 13 weeks), and on to the end of any known
    low period the founder named that starts within a year, at most MAX_WEEKS."""
    h = m3_week(start_week)
    if biz and biz.get("season_end_week"):
        h = max(h, min(MAX_WEEKS, biz["season_end_week"]))
    return h


def simulate(biz, hire_month, start_week, one_off=0.0, stress=False, weeks=None):
    """Week-by-week balances. Returns a list of dicts (week, in, out, hire, payments, balance).
    Money in for week w = rate x (the part of week w after the delay, less each low period's cut times the part of
    week w it covers, shifted by the delay). In a bad quarter the rate is contracted revenue plus the rest cut by the
    stress cut (contracted revenue is not cut, but still arrives late)."""
    cur_cash = biz["cash_today"]
    W = biz["monthly_revenue"] / WEEKS_PER_MONTH
    S = min(biz.get("secured_month") or 0.0, biz["monthly_revenue"]) / WEEKS_PER_MONTH
    C = biz["costs_month_total"] / WEEKS_PER_MONTH
    d = biz["stress_extra_days"] / 7 if stress else 0.0
    rate = (S + (W - S) * (1 - biz["stress_revenue_cut"])) if stress else W
    # Costs that move with revenue (contractor fees, materials): in a bad quarter they fall by the founder's share of the
    # revenue lost, from week 1 (the work falls when the work falls, not when the cash arrives).
    relief = (biz.get("variable_costs_share") or 0.0) * (W - S) * biz["stress_revenue_cut"] if stress else 0.0
    lows = biz.get("low_periods") or []
    hire_week = (hire_month or 0.0) / WEEKS_PER_MONTH
    weeks = weeks or horizon(start_week, biz)
    rows = []
    for w in range(1, weeks + 1):
        a = w - 1.0
        cin = rate * (overlap(a, w, d, 1e9) - sum(p["revenue_cut"] * overlap(a, w, d + p["from_week"], d + p["to_week"]) for p in lows))
        out = C * (1 - sum(p["costs_cut"] * overlap(a, w, p["from_week"], p["to_week"]) for p in lows)) - relief
        hire = (hire_week if w >= start_week else 0.0) + (one_off if w == start_week else 0.0)
        pay = sum(p["amount"] for p in biz["known_payments"] if p["week"] == w)
        cur_cash = cur_cash + cin - out - hire - pay
        rows.append({"week": w, "in": cin, "out": out, "hire": hire, "payments": pay, "balance": cur_cash})
    return rows


def floor_amount(biz, hire_month):
    return biz["cover_target_months"] * (biz["costs_month_total"] + (hire_month or 0.0))


def floor_for_week(biz, hire_month, start_week, week):
    """Before the start the floor is the cover target in today's monthly costs; from the start, the hire is in them."""
    return floor_amount(biz, hire_month if week >= start_week else 0.0)


def first_breach(rows, biz, hire_month, start_week):
    for r in rows:
        if r["balance"] < floor_for_week(biz, hire_month, start_week, r["week"]) - 1e-9:
            return r["week"]
    return None


def scenario(biz, hire_month, start_week, one_off=0.0):
    """Usual and bad quarter with the hire loaded; the floor; the first breach; the gap to the floor; and the same bad
    quarter with no hire, so the report can say how much of the gap is there without the hire."""
    base = simulate(biz, hire_month, start_week, one_off, stress=False)
    stress = simulate(biz, hire_month, start_week, one_off, stress=True)
    fl = floor_amount(biz, hire_month)
    gaps = [floor_for_week(biz, hire_month, start_week, r["week"]) - r["balance"] for r in stress]
    worst = max(range(len(gaps)), key=lambda i: gaps[i])
    lo = min(stress, key=lambda r: r["balance"])
    nh = simulate(biz, 0.0, start_week, 0.0, stress=True)
    nh_gaps = [floor_amount(biz, 0.0) - r["balance"] for r in nh]
    nw = max(range(len(nh_gaps)), key=lambda i: nh_gaps[i])
    m3 = min(m3_week(start_week), len(base))
    short = max(0.0, gaps[worst])
    nh_short = max(0.0, nh_gaps[nw])
    return {"base": base, "stress": stress, "floor": fl, "floor_before_start": floor_amount(biz, 0.0),
            "base_breach": first_breach(base, biz, hire_month, start_week),
            "stress_breach": first_breach(stress, biz, hire_month, start_week),
            "stress_low": lo["balance"], "stress_low_week": lo["week"],
            "shortfall": short, "shortfall_week": stress[worst]["week"],
            "nohire_shortfall": nh_short, "nohire_shortfall_week": nh[nw]["week"],
            "nohire_breach": first_breach(nh, biz, 0.0, start_week), "hire_adds": max(0.0, short - nh_short),
            "m3_week": m3, "window_weeks": len(base),
            "base_end": base[m3 - 1]["balance"], "stress_end": stress[m3 - 1]["balance"],
            "base_window_end": base[-1]["balance"], "stress_window_end": stress[-1]["balance"]}


def later_start(biz, hire_month, one_off, from_week, max_week=26):
    """The earliest start week after from_week for which the stress case holds the floor in every week up to 13
    weeks after the start (and through any named low period), today's figures held. None if no start up to max_week holds."""
    for s in range(from_week + 1, max_week + 1):
        rows = simulate(biz, hire_month, s, one_off, stress=True)
        if first_breach(rows, biz, hire_month, s) is None:
            return s
    return None


# ------------------------------------------------------------------ the hire's cost basis (the founder's word, never worked out)
def cost_basis(v):
    """'loaded' when the founder says the figure is the full cost (all in, from the accountant, the payroll provider
    or a payroll calculator); 'salary_only' for pay alone; None when not said."""
    s = str(v or "").strip().lower()
    if not s or s in ("unknown", "not sure", "illustration"):
        return None
    if re.match(r"(loaded|fully loaded|full|all in|all-in|accountant|payroll|founder|confirmed|total)", s):
        return "loaded"
    if re.match(r"(salary|pay|wage|gross pay|base)", s):
        return "salary_only"
    return None


# ------------------------------------------------------------------ CLI
def load(path):
    p = Path(path)
    if not p.exists():
        raise InputError(f"there is no inputs file at {path}")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise InputError(f"the inputs file is not valid JSON ({e.msg} at line {e.lineno})")


TEMPLATE = {
    "business": None, "currency": None, "country": None, "locale": None, "decimal_style": None, "date": None,
    "cash_today": None, "monthly_revenue": None, "monthly_costs": None, "costs_include_founder_pay": None,
    "founder_pay_month": None,
    "known_payments": [{"what": None, "amount": None, "when": None}],
    "revenue_history": [], "gross_margin_months": [], "margin_floor": None,
    "recurring_revenue_month": None, "contracted_next_6_months": None, "repeat_revenue_month": None, "repeat_share": None,
    "known_low_periods": [{"what": None, "from": None, "to": None, "revenue_cut": None, "costs_cut": None}],
    "gross_margin_rough": None, "payroll_provider_seen": None, "confirmed_figures": [],
    "pipeline": [{"name": None, "value": None, "chance": None}],
    "role": {"title": None, "type": None, "employment": None, "hours_week": None, "salary_year": None,
             "monthly_cost": None, "cost_basis": "loaded or salary_only", "cost_from": None,
             "one_off_costs": None, "start": None, "days": None},
    "tasks": [{"task": None, "hours_week": None, "written_down": None}],
    "freed_hours_use": None, "freed_use_has_revenue_path": None,
    "role_coherent": {"value": None, "reason": None},
    "capacity": {"now": None, "max": None, "room_for": None, "said": None, "unit": "client hours a week"},
    "typical_client_month": None,
    "variable_costs_share": None,
    "price_rise_tested": {"value": None, "said": None}, "contractor_rate_hour": None, "sources": {},
}


def ready_for_cash(biz):
    return all(biz.get(k) is not None for k in ("cash_today", "monthly_revenue", "costs_month_total"))


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("template", "compute"):
        print(__doc__)
        sys.exit(2)
    if sys.argv[1] == "template":
        print(json.dumps(TEMPLATE, indent=2))
        return 0
    if len(sys.argv) < 3:
        raise InputError("give the inputs file: python3 scripts/cash_scenario.py compute <inputs.json>")
    biz = normalise(load(sys.argv[2]))
    if not ready_for_cash(biz):
        for n in biz["needs"]:
            print("NEED:", n)
        print("STOP: the cash scenario needs cash today, monthly revenue and monthly costs. Nothing was computed.")
        return 2
    hm = biz["role"]["monthly_cost"] or 0.0
    sc = scenario(biz, hm, biz["role"]["start_week"], biz["role"]["one_off"])
    cur = biz["currency"]
    print(f"Floor: {money(sc['floor'], cur)} | hire {money(hm, cur)} a month from week {biz['role']['start_week']}")
    print("Week | Base | Stress")
    for b_, s_ in zip(sc["base"], sc["stress"]):
        print(f"{b_['week']:>4} | {money(b_['balance'], cur):>10} | {money(s_['balance'], cur):>10}")
    print(f"Stress first below the floor: {'week ' + str(sc['stress_breach']) if sc['stress_breach'] else 'never'}")
    print(f"No hire, stress: short of the floor by {money(sc['nohire_shortfall'], cur)} at most")
    for n in biz["needs"]:
        print("NEED:", n)
    return 1 if biz["needs"] else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AskFounder as e:
        for q in e.questions:
            print("ASK:", q)
        print("STOP: one or more figures need the founder's answer first (ASK lines). Nothing was written.")
        sys.exit(2)
    except InputError as e:
        print(f"STOP: {e}. Nothing was written.")
        sys.exit(2)
    except Exception as e:  # noqa: BLE001
        print(f"STOP: the script could not read these inputs ({type(e).__name__}: {e}). Check the inputs file. Nothing was written.")
        sys.exit(2)
