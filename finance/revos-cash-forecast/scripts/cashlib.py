#!/usr/bin/env python3
"""Shared helpers for this skill's scripts: reading money and dates the way founders and banks write
them, and printing figures in the founder's currency and date order. Standard library only. Not run directly.

No country is assumed. The currency comes from the export or the founder; the date order (day first or
month first) comes from the export, the founder's saved answer, or one question. A day and month typed with
no known order and two possible readings stops with a question rather than a guess.
"""
import re
from datetime import date, datetime, timedelta

import locale_numbers as ln

MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}
MONTHS.update({"sept": 9, "january": 1, "february": 2, "march": 3, "april": 4, "june": 6, "july": 7,
               "august": 8, "september": 9, "october": 10, "november": 11, "december": 12})
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


# How dates are printed for this founder: set once per run by the caller (set_style).
STYLE = {"month_first": False}


def set_style(month_first=False):
    STYLE["month_first"] = bool(month_first)


class InputError(Exception):
    """A problem the founder or Claude can fix. Printed as one STOP line."""


# ------------------------------------------------------------------ money
CODES = ("gbp", "usd", "eur", "aud", "cad", "nzd", "sgd", "hkd", "inr", "jpy", "chf", "aed", "zar", "myr", "sek",
         "nok", "dkk", "php", "idr", "thb", "mxn", "brl")
_CUR = re.compile(r"((?:us|s|sg|a|au|nz|c|ca|hk)\$|\b(?:" + "|".join(CODES) + r")\b|£|\$|€|₹|¥|r\$)", re.I)
# How a figure is printed for each currency: (symbol, after the number). Anything else prints "1,234 CODE".
SYMBOLS = {"GBP": "£", "USD": "$", "EUR": "€", "AUD": "A$", "CAD": "C$", "NZD": "NZ$", "SGD": "S$", "HKD": "HK$",
           "INR": "₹", "JPY": "¥", "ZAR": "R", "MYR": "RM", "PHP": "₱", "NGN": "₦", "BRL": "R$", "PLN": "zł",
           "SEK": "kr", "NOK": "kr", "DKK": "kr", "CHF": "CHF", "AED": "AED", "KES": "KSh", "IDR": "Rp", "THB": "฿"}
SYMBOL_AFTER = {"PLN", "SEK", "NOK", "DKK"}
SYMBOL_TO_CODE = {"£": "GBP", "€": "EUR", "₹": "INR", "S$": "SGD", "SG$": "SGD", "A$": "AUD", "AU$": "AUD",
                  "NZ$": "NZD", "C$": "CAD", "CA$": "CAD", "HK$": "HKD", "US$": "USD"}


def currency_in(text):
    """A currency code or unambiguous symbol written in a cell or header, else None. A bare $ is not
    unambiguous (several countries use it), so it is never read as one currency."""
    s = str(text or "")
    m = re.search(r"\b(" + "|".join(CODES) + r")\b", s, re.I)
    if m:
        return m.group(1).upper()
    for sym, code in sorted(SYMBOL_TO_CODE.items(), key=lambda kv: -len(kv[0])):
        if sym.lower() in s.lower():
            if sym in ("£", "€", "₹") or re.search(r"(?<![a-z])" + re.escape(sym.lower()), s.lower()):
                return code
    return None


def parse_bank_amount(v):
    """Read an amount from a bank export cell. Returns a float, or None for blank.

    Bank cells only (founder-typed figures go through parse_money). Handles '£1,234.56', '-£12', '(123.45)',
    '123.45-', '123.45 CR', '50 DR', 'GBP 850.00', '1.234,56' and '-38 500,00' (comma decimals), '0.00-'.
    Raises InputError on text.
    """
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace("\u00a0", " ").replace("\u202f", " ").replace("\u2212", "-")
    if s == "" or s.lower() in ("-", "n/a", "na", "none", "nil", "null", "0.00-"):
        return None if s.lower() != "0.00-" else 0.0
    neg = False
    m = re.search(r"\s*\b(cr|dr)\.?$", s, re.I)
    if m:
        neg = m.group(1).lower() == "dr"
        s = s[:m.start()]
    if s.startswith("(") and s.endswith(")"):
        neg, s = True, s[1:-1]
    s = _CUR.sub("", s).strip()
    if s.endswith("-") and not s.startswith("-"):
        neg, s = True, s[:-1].strip()
    if s.startswith("+"):
        s = s[1:]
    if s.startswith("-"):
        neg, s = (not neg), s[1:].strip()
    s = _CUR.sub("", s).strip()
    s = s.replace(" ", "").replace("'", "")
    if re.fullmatch(r"\d{1,3}(\.\d{3})+,\d{1,2}", s) or re.fullmatch(r"\d+,\d{1,2}", s):
        s = s.replace(".", "").replace(",", ".")  # 1.234,56 or 12,50
    else:
        s = s.replace(",", "")
    if not re.fullmatch(r"\d+(\.\d+)?|\.\d+", s):
        raise InputError(f"'{v}' is not an amount")
    x = float(s)
    return -x if neg else x


def money_or_none(v):
    try:
        return parse_bank_amount(v)
    except InputError:
        return None


# ------------------------------------------------------------------ figures the founder typed
# Every number, amount, percentage or count of days the founder typed goes through locale_numbers.py (Build
# Standard section 13). The decimal style is detected once per run (set_decimal) and passed to every reader.
TYPED = {"decimal": None, "currency": None}
_FAMILY = {"DOLLAR": {"USD", "AUD", "CAD", "NZD", "SGD", "HKD", "TWD"}, "JPY_OR_CNY": {"JPY", "CNY"},
           "INR_OR_PKR_OR_LKR": {"INR", "PKR", "LKR"}, "SEK_OR_NOK_OR_DKK": {"SEK", "NOK", "DKK"},
           "NOK_OR_DKK": {"NOK", "DKK"}, "PESO": {"MXN", "PHP", "COP", "CLP", "ARS"},
           "SHILLING": {"KES", "UGX", "TZS"}, "CHF_OR_OTHER": {"CHF"}}


def set_decimal(style):
    """'dot', 'comma' or None: how this founder writes decimals, detected once per run."""
    TYPED["decimal"] = style if style in ("dot", "comma") else None


def set_account_currency(code):
    TYPED["currency"] = (str(code).upper() if code else None)


def _same_currency(seen, account):
    if not seen or not account:
        return True
    return seen == account or account in _FAMILY.get(seen, set())


def parse_money(v, label=None):
    """Read an amount the founder typed: '4.2k', 'R412 000', 'about R41k', '1.200,50 €', '₹2.4 lakh', '(450)',
    '450 DR', '123.45-', '~62k'. Returns a float, or None for blank. Raises InputError with one plain question
    when the figure reads two ways (Ambiguous), cannot be read (Unreadable), or carries another currency."""
    if v is None:
        return None
    if isinstance(v, bool):
        raise InputError(f"'{v}' is not an amount")
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace("\u00a0", " ").replace("\u202f", " ").replace("\u2212", "-")
    if s == "" or s.lower() in ("-", "n/a", "na", "none", "nil", "null"):
        return None
    neg = False
    m = re.search(r"\s*\b(cr|dr)\.?$", s, re.I)
    if m:  # a bank's own marker, copied by the founder
        neg, s = m.group(1).lower() == "dr", s[:m.start()].strip()
    if re.search(r"\d\s*-$", s) and not s.startswith("-"):
        neg, s = True, s[:-1].strip()
    what = f"{label}: '{v}'" if label else f"'{v}'"
    try:
        x, cur, _notes = ln.parse_money(s, TYPED["decimal"])
    except ln.Ambiguous as e:
        raise InputError(f"{what} reads two ways ({e}). Ask the founder once which they meant, and set "
                         "decimal_style in the inputs ('dot' for 1,234.50 or 'comma' for 1.234,50)")
    except ValueError as e:
        raise InputError(f"{what} is not an amount I can read ({e}). Ask the founder to restate that figure")
    if not _same_currency(cur, TYPED["currency"]):
        raise InputError(f"{what} is written in {cur}, but this account is in {TYPED['currency']}. Ask the founder "
                         "for the figure in the account's currency; this forecast never converts")
    return -x if neg else x


def parse_count(v, label=None):
    """A whole number of days or payments the founder typed ('14', '2 weeks' is not accepted here, 'about 30')."""
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return int(round(v))
    try:
        x, _n = ln.parse_number(str(v), TYPED["decimal"])
    except ln.Ambiguous as e:
        raise InputError(f"{label or 'a number'}: '{v}' reads two ways ({e}); ask the founder once")
    except ValueError:
        raise InputError(f"{label or 'a number'}: '{v}' is not a number I can read; ask the founder to restate it")
    return int(round(x))


def parse_pct(v, label=None):
    """A percentage the founder typed ('20%', '1,4 %', '12.5 percent') as a fraction. A number already below 1
    in the inputs file (0.2) is a fraction written by the script."""
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v) if float(v) < 1 else float(v) / 100
    try:
        x, _n = ln.parse_percent(str(v), TYPED["decimal"])
    except ln.Ambiguous as e:
        raise InputError(f"{label or 'a percentage'}: '{v}' reads two ways ({e}); ask the founder once")
    except ValueError:
        raise InputError(f"{label} '{v}' is not a percentage")
    return x / 100


def typed_samples(raw):
    """Every figure the founder typed into the inputs (strings only; the export's own numbers are floats)."""
    out = []

    def walk(o, key=""):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("seen", "history_daily", "export", "sources", "receipts_pattern_week", "everyday_spending_week",
                         "owner_pay_irregular_week", "source", "label", "client", "ref", "match", "_how"):
                    continue
                walk(v, k)
        elif isinstance(o, list):
            for v in o:
                walk(v, key)
        elif isinstance(o, str) and key in ("amount", "balance", "value", "monthly_cost", "one_off", "amount_each"):
            out.append(o)
    walk(raw)
    return out


# ------------------------------------------------------------------ the founder's way of writing figures
NUM = {"group": ",", "decimal": "."}


def set_number_style(group=None, decimal=None):
    """How figures are written back: group ',' '.' ' ' or "'", decimal '.' or ','. From the founder's own typing,
    else the export's, else 1,234.56."""
    NUM["group"] = group if group in (",", ".", " ", "'") else ","
    NUM["decimal"] = decimal if decimal in (".", ",") else "."
    if NUM["group"] == NUM["decimal"]:
        NUM["group"] = " " if NUM["decimal"] == "," else ","


def style_from_samples(samples):
    """(group, decimal) the founder used in what they typed, or (None, None)."""
    dec = ln.detect_decimal_style(samples)
    group = None
    for s in samples or []:
        s = str(s)
        if re.search(r"\d{1,3}(?:[ \u00a0\u202f]\d{3})+(?!\d)", s):
            group = " "
        elif re.search(r"\d'\d{3}", s):
            group = "'"
        elif re.search(r"\d\.\d{3}(?:[.,]|\b)", s) and dec == "comma":
            group = "."
        elif re.search(r"\d,\d{3}(?!\d)", s) and dec != "comma":
            group = group or ","
        if group == " ":
            break
    return group, ({"dot": ".", "comma": ","}.get(dec))


def _digits(x, places):
    body = f"{x:,.{places}f}"
    whole, _, frac = body.partition(".")
    whole = whole.replace(",", NUM["group"])
    return whole + (NUM["decimal"] + frac if frac else "")


# ------------------------------------------------------------------ dates written by banks
_YMD = re.compile(r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})(?:[ T].*)?$")
_NUM = re.compile(r"^(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})(?:[ T].*)?$")
_DMONY = re.compile(r"^(\d{1,2})(?:st|nd|rd|th)?[ \-]?([A-Za-z]{3,9})\.?[ \-,]*(\d{2,4})(?:[ T].*)?$")
_MONDY = re.compile(r"^([A-Za-z]{3,9})\.? (\d{1,2})(?:st|nd|rd|th)?,? (\d{4})(?:[ T].*)?$")


def _year(y):
    y = int(y)
    return y + 2000 if y < 100 else y


def date_shape(s):
    """Classify a bank date string: ('ymd', parts), ('num', (a, b, y)), ('dmony', d), ('serial', d) or None."""
    s = str(s or "").strip().strip('"')
    if not s:
        return None
    m = _YMD.match(s)
    if m:
        try:
            return ("fixed", date(int(m.group(1)), int(m.group(2)), int(m.group(3))))
        except ValueError:
            return None
    m = _NUM.match(s)
    if m:
        return ("num", (int(m.group(1)), int(m.group(2)), _year(m.group(3))))
    m = _DMONY.match(s)
    if m and m.group(2)[:3].lower() in MONTHS:
        try:
            return ("fixed", date(_year(m.group(3)), MONTHS[m.group(2)[:3].lower()], int(m.group(1))))
        except ValueError:
            return None
    m = _MONDY.match(s)
    if m and m.group(1)[:3].lower() in MONTHS:
        try:
            return ("fixed", date(int(m.group(3)), MONTHS[m.group(1)[:3].lower()], int(m.group(2))))
        except ValueError:
            return None
    if re.fullmatch(r"\d{5}(\.\d+)?", s) and 30000 <= float(s) <= 70000:  # a spreadsheet serial number
        return ("fixed", date(1899, 12, 30) + timedelta(days=int(float(s))))
    return None


def resolve_num(parts, day_first):
    a, b, y = parts
    d, m = (a, b) if day_first else (b, a)
    return date(y, m, d)


# ------------------------------------------------------------------ dates written by founders
def parse_when(v, today, day_first=None):
    """Read a date a founder typed, relative to today. Returns a date or raises InputError.

    Accepts ISO dates, 31/10 or 10/31 (in the founder's date order), 31 Oct, Oct 31, 31st October 2026,
    'today', 'tomorrow', 'next friday', 'friday', 'in 2 weeks', '2 weeks', '10 days', 'end of month',
    'end of november', 'the 15th', '15th'. A day and month without a year is the next such date on or after
    today. day_first is True, False, or None when the founder's order is not known yet: then a numeric date
    that reads two ways stops with a question instead of a guess.
    """
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    s = str(v or "").strip().lower().rstrip(".")
    if not s:
        raise InputError("a date is missing")
    if s in ("today", "now"):
        return today
    if s == "tomorrow":
        return today + timedelta(days=1)
    m = re.fullmatch(r"(?:in\s+)?(\d+|a|one|two|three|four|six)\s+(day|days|week|weeks|wk|wks|month|months)(?:\s+time)?", s)
    if m:
        n = {"a": 1, "one": 1, "two": 2, "three": 3, "four": 4, "six": 6}.get(m.group(1)) or int(m.group(1))
        unit = m.group(2)
        if unit.startswith("day"):
            return today + timedelta(days=n)
        if unit.startswith("w"):
            return today + timedelta(weeks=n)
        return add_months(today, n)
    m = re.fullmatch(r"(next|this)?\s*(mon|tue|tues|wed|thu|thur|thurs|fri|sat|sun)[a-z]*", s)
    if m:
        target = [w[:3] for w in WEEKDAYS].index(m.group(2)[:3])
        ahead = (target - today.weekday()) % 7
        if ahead == 0:  # "friday" said on a Friday means a week today
            ahead = 7
        return today + timedelta(days=ahead)
    m = re.fullmatch(r"end of (?:the )?(month|this month|next month|[a-z]+)", s)
    if m:
        word = m.group(1)
        if word in ("month", "this month"):
            return month_end(today.year, today.month)
        if word == "next month":
            y, mo = (today.year + 1, 1) if today.month == 12 else (today.year, today.month + 1)
            return month_end(y, mo)
        if word[:3] in MONTHS:
            mo = MONTHS[word[:3]]
            y = today.year if mo >= today.month else today.year + 1
            return month_end(y, mo)
    m = re.fullmatch(r"(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)", s)
    if m:
        d = int(m.group(1))
        cand = _safe(today.year, today.month, d)
        if cand is None or cand < today:
            y, mo = (today.year + 1, 1) if today.month == 12 else (today.year, today.month + 1)
            cand = _safe(y, mo, d)
        if cand:
            return cand
    shape = date_shape(s)
    if shape and shape[0] == "fixed":
        return shape[1]
    if shape and shape[0] == "num":
        a, b, y = shape[1]
        return resolve_num(shape[1], _order(v, a, b, day_first))
    m = re.fullmatch(r"(\d{1,2})[/.-](\d{1,2})", s)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        df = _order(v, a, b, day_first)
        return _forward(today, b, a) if df else _forward(today, a, b)
    m = re.fullmatch(r"(\d{1,2})(?:st|nd|rd|th)?\s+([a-z]{3,9})", s)
    if m and m.group(2)[:3] in MONTHS:
        return _forward(today, MONTHS[m.group(2)[:3]], int(m.group(1)))
    m = re.fullmatch(r"([a-z]{3,9})\s+(\d{1,2})(?:st|nd|rd|th)?", s)
    if m and m.group(1)[:3] in MONTHS:
        return _forward(today, MONTHS[m.group(1)[:3]], int(m.group(2)))
    raise InputError(f"'{v}' is not a date I can read; give it as 31/10/2026")


def _order(raw, a, b, day_first):
    """Day first or month first for a numeric date the founder typed."""
    if a > 12 and b <= 12:
        return True
    if b > 12 and a <= 12:
        return False
    if a == b or day_first is not None:
        return True if day_first is None else day_first
    raise InputError(f"'{raw}' could be read as day {a} month {b} or as month {a} day {b}. Ask the founder once "
                     "whether they write dates day first or month first, and set date_order in the inputs")


def add_months(d, n):
    """Same day n calendar months later, clamped to the month's last day."""
    y, m = divmod(d.month - 1 + n, 12)
    y, m = d.year + y, m + 1
    return date(y, m, min(d.day, month_end(y, m).day))


def month_end(y, m):
    return date(y + (m // 12), m % 12 + 1, 1) - timedelta(days=1)


def _safe(y, m, d):
    try:
        return date(y, m, d)
    except ValueError:
        return None


def _forward(today, month, day):
    cand = _safe(today.year, month, day)
    if cand is None:
        raise InputError(f"{day}/{month} is not a real date")
    if cand < today - timedelta(days=60):
        cand = _safe(today.year + 1, month, day) or cand
    return cand


def iso(d):
    return d.isoformat() if d else None


def from_iso(s):
    return date.fromisoformat(str(s)[:10])


# ------------------------------------------------------------------ printing
def money(v, cur=None, pence=False):
    """A figure in the founder's currency and their way of writing numbers. With no currency known, a plain number."""
    code = str(cur or "").upper()
    sym = SYMBOLS.get(code, "")
    if v is None:
        return "[NEED]"
    x = round(v, 2) if pence else round(v)
    sign = "-" if x < 0 else ""
    body = _digits(abs(x), 2 if pence else 0)
    if sym and code in SYMBOL_AFTER:
        return f"{sign}{body} {sym}"
    if sym:
        return f"{sign}{sym}{' ' if len(sym) > 1 and sym.isalpha() and sym not in ('R', 'RM', 'Rp', 'KSh') else ''}{body}"
    return f"{sign}{body} {cur}" if cur else f"{sign}{body}"


def long_date(d):
    """16 October 2026, or October 16, 2026 for a founder who writes month first."""
    if isinstance(d, str):
        d = from_iso(d)
    if STYLE["month_first"]:
        return f"{d.strftime('%B')} {d.day}, {d.year}"
    return f"{d.day} {d.strftime('%B')} {d.year}"


def short_date(d):
    if isinstance(d, str):
        d = from_iso(d)
    if STYLE["month_first"]:
        return f"{d.strftime('%b')} {d.day}"
    return f"{d.day} {d.strftime('%b')}"
