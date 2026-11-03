#!/usr/bin/env python3
"""Dates for invoices: read what the founder typed, write dates in their style, and turn payment terms into a due date.

Usage (standalone checks):
  python3 scripts/dates.py due --issue 2026-11-02 --terms "days:14" [--country IE]
  python3 scripts/dates.py read "12 October 2026" [--country US] [--today 2026-11-02]
Term types: days:N, eom_plus:N, end_next_month, next_month_day:N, on_receipt, fixed:<date>, in_advance:<start date>[:N]
Exit 0 done, 2 STOP. Standard library only. No network calls. No public holiday calendar is built in:
holidays and days off come only from the founder.
"""
import argparse
import calendar
import os
import re
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402
import locale_numbers as LN  # noqa: E402

EN_MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
             "November", "December"]
EN_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
# Month names for READING founder dates in common languages (writing uses the label set).
READ_MONTHS = {
    1: ["jan", "january", "januar", "janvier", "enero", "gennaio", "januari", "janeiro", "jänner", "jaenner"],
    2: ["feb", "february", "februar", "fevrier", "février", "febrero", "febbraio", "februari", "fevereiro"],
    3: ["mar", "march", "maerz", "märz", "marz", "mars", "marzo", "maart", "março", "marco"],
    4: ["apr", "april", "avril", "abril", "aprile"],
    5: ["may", "mai", "mayo", "maggio", "mei", "maio"],
    6: ["jun", "june", "juni", "juin", "junio", "giugno", "junho"],
    7: ["jul", "july", "juli", "juillet", "julio", "luglio", "julho"],
    8: ["aug", "august", "aout", "août", "agosto", "augustus"],
    9: ["sep", "sept", "september", "septembre", "septiembre", "settembre", "setembro"],
    10: ["oct", "october", "oktober", "octobre", "octubre", "ottobre", "okt", "outubro"],
    11: ["nov", "november", "novembre", "noviembre", "novembro"],
    12: ["dec", "december", "dezember", "décembre", "decembre", "diciembre", "dicembre", "dez", "dezembro"],
}
MONTH_LOOKUP = {name: n for n, names in READ_MONTHS.items() for name in names}
WEEKDAY_LOOKUP = {"mon": 0, "monday": 0, "tue": 1, "tues": 1, "tuesday": 1, "wed": 2, "wednesday": 2, "thu": 3,
                  "thur": 3, "thurs": 3, "thursday": 3, "fri": 4, "friday": 4, "sat": 5, "saturday": 5, "sun": 6,
                  "sunday": 6, "montag": 0, "dienstag": 1, "mittwoch": 2, "donnerstag": 3, "freitag": 4,
                  "samstag": 5, "sonntag": 6}


def parse_iso(s):
    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", str(s).strip())
    if not m:
        return None
    return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))


def _month_for(word, extra=None):
    w = word.lower().strip(".")
    if extra:
        for i, name in enumerate(extra):
            if w == str(name).lower() or w == str(name).lower()[:3]:
                return i + 1
    return MONTH_LOOKUP.get(w)


def read_date(text, order="DMY", today=None, prefer="any", months=None):
    """Read one founder-typed date. order is DMY, MDY or YMD (from their country). Raises C.Stop with a question."""
    if text is None:
        raise C.Stop("a date is missing")
    if isinstance(text, date):
        return text
    raw = str(text).strip()
    t = raw.lower().replace(",", " ").strip()
    t = re.sub(r"\s+", " ", t)
    today = today or date.today()
    d = parse_iso(t)
    if d:
        return d
    if t in ("today", "heute", "now"):
        return today
    if t == "tomorrow":
        return today + timedelta(days=1)
    if t == "yesterday":
        return today - timedelta(days=1)
    m = re.fullmatch(r"(next|this|coming|last) (\w+)", t)
    if m and m.group(2) in WEEKDAY_LOOKUP:
        wd = WEEKDAY_LOOKUP[m.group(2)]
        delta = (wd - today.weekday()) % 7
        if m.group(1) == "last":
            delta = -((today.weekday() - wd) % 7 or 7)
        elif m.group(1) == "next" and delta == 0:
            delta = 7
        elif m.group(1) in ("this", "coming") and delta == 0:
            delta = 0
        return today + timedelta(days=delta)
    m = re.fullmatch(r"in (\d+|a|one|two|three|four) (day|days|week|weeks)", t)
    if m:
        n = {"a": 1, "one": 1, "two": 2, "three": 3, "four": 4}.get(m.group(1)) or int(m.group(1))
        return today + timedelta(days=n * (7 if m.group(2).startswith("week") else 1))
    m = re.fullmatch(r"(\d+|a|one|two|three|four|five|six) (day|days|week|weeks) ago", t)
    if m:
        n = {"a": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}.get(m.group(1)) or int(m.group(1))
        return today - timedelta(days=n * (7 if m.group(2).startswith("week") else 1))
    if t in ("end of month", "end of the month", "month end"):
        return date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])
    # numeric
    m = re.fullmatch(r"(\d{1,4})[./-](\d{1,2})[./-](\d{1,4})\.?", t)
    if m:
        a, b, c = m.group(1), m.group(2), m.group(3)
        if len(a) == 4:
            y, mo, dd = int(a), int(b), int(c)
        else:
            y = int(c) + (2000 if len(c) == 2 else 0)
            x, z = int(a), int(b)
            if order == "MDY":
                mo, dd = x, z
            else:
                dd, mo = x, z
            if order not in ("MDY",) and mo > 12 and dd <= 12:
                raise C.Stop(f"please check the date '{raw}': it reads as month {mo}. Is it {z}/{x} the other way round?")
            if order == "MDY" and mo > 12 and dd <= 12:
                raise C.Stop(f"please check the date '{raw}': it reads as month {mo}. Ask the founder which day it is")
        try:
            return date(y, mo, dd)
        except ValueError:
            raise C.Stop(f"'{raw}' is not a real date. Ask the founder for it again")
    # words: 12 October 2026, 12th Oct 2026, 12. Oktober 2026, October 12 2026, Oct 2026 (no day: refuse)
    t2 = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", t).replace(". ", " ").rstrip(".")
    t2 = re.sub(r"^(\w+day|montag|dienstag|mittwoch|donnerstag|freitag|samstag|sonntag) ", "", t2)
    parts = t2.split()
    y = None
    if parts and re.fullmatch(r"\d{4}", parts[-1]):
        y = int(parts.pop())
    day = mon = None
    if len(parts) == 2:
        if parts[0].isdigit() and _month_for(parts[1], months):
            day, mon = int(parts[0]), _month_for(parts[1], months)
        elif parts[1].isdigit() and _month_for(parts[0], months):
            day, mon = int(parts[1]), _month_for(parts[0], months)
    if day and mon:
        if y is None:
            y = today.year
            cand = date(y, mon, day)
            if prefer == "past" and cand > today:
                y -= 1
            elif prefer == "future" and cand < today:
                y += 1
        try:
            return date(y, mon, day)
        except ValueError:
            raise C.Stop(f"'{raw}' is not a real date. Ask the founder for it again")
    raise C.Stop(f"the date '{raw}' could not be read. Ask the founder to write it as day, month name and year")


def end_of_month(d):
    return date(d.year, d.month, calendar.monthrange(d.year, d.month)[1])


def add_months(d, n):
    y, m = divmod(d.month - 1 + n, 12)
    y += d.year
    m += 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


# ---------------------------------------------------------------- writing dates
def default_format(country, language):
    loc = LN.locale_defaults(country)
    lang = (language or "en").lower()[:2]
    if lang == "de":
        return "d. MMMM yyyy"
    if lang in ("ja", "zh", "ko"):
        return "yyyy/MM/dd"
    if loc["date_order"] == "MDY":
        return "MMMM d, yyyy"
    if loc["date_order"] == "YMD":
        return "yyyy-MM-dd"
    return "d MMMM yyyy"


def fmt(d, pattern, months=None):
    if d is None:
        return ""
    months = months or EN_MONTHS
    tokens = re.findall(r"yyyy|MMMM|MMM|MM|M|dd|d|[^yMd]+", pattern)
    out = []
    for tok in tokens:
        if tok == "yyyy":
            out.append(str(d.year))
        elif tok == "MMMM":
            out.append(months[d.month - 1])
        elif tok == "MMM":
            out.append(months[d.month - 1][:3])
        elif tok == "MM":
            out.append(f"{d.month:02d}")
        elif tok == "M":
            out.append(str(d.month))
        elif tok == "dd":
            out.append(f"{d.day:02d}")
        elif tok == "d":
            out.append(str(d.day))
        else:
            out.append(tok)
    return "".join(out)


def is_numeric_format(pattern):
    return "MMM" not in pattern


def fmt_weekday(d, pattern, months=None, weekdays=None, us_style=False, language="en"):
    """A date with its weekday, the way the founder would write it."""
    weekdays = weekdays or EN_DAYS
    wd = weekdays[d.weekday()]
    body = fmt(d, pattern, months)
    if is_numeric_format(pattern):
        return f"{body} ({wd})"
    if us_style or (language or "en")[:2] != "en":
        return f"{wd}, {body}"
    return f"{wd} {body}"


def fmt_range(a, b, pattern, months=None, joiner="to"):
    if not a:
        return ""
    if not b or a == b:
        return fmt(a, pattern, months)
    return f"{fmt(a, pattern, months)} {joiner} {fmt(b, pattern, months)}"


# ---------------------------------------------------------------- payment terms
TERM_TYPES = ("days", "eom_plus", "end_next_month", "next_month_day", "on_receipt", "fixed", "in_advance")


def parse_terms_spec(spec):
    """'days:14' or a dict {type, days, date, start} to a dict."""
    if isinstance(spec, dict):
        return dict(spec)
    s = str(spec or "").strip()
    if not s:
        return {}
    kind, _, rest = s.partition(":")
    out = {"type": kind.strip()}
    if kind in ("days", "eom_plus", "next_month_day"):
        out["days"] = rest
    elif kind == "fixed":
        out["date"] = rest
    elif kind == "in_advance":
        start, _, n = rest.partition(":")
        out["start"] = start
        out["days"] = n or 0
    return out


def resolve_due(issue, terms, order="DMY", today=None, months=None):
    """Return (due date, notes). terms is a dict with type and its fields, founder-typed values allowed."""
    t = dict(terms or {})
    kind = t.get("type") or "days"
    notes = []
    if kind not in TERM_TYPES:
        raise C.Stop(f"payment terms type '{kind}' is not one of {', '.join(TERM_TYPES)}")

    def n_days(default=None):
        v = t.get("days", default)
        if v in (None, ""):
            if default is None:
                raise C.Stop(f"payment terms '{kind}' need a number of days")
            v = default
        try:
            val, _ = LN.parse_number(str(v))
        except (LN.Ambiguous, LN.Unreadable):
            raise C.Stop(f"the number of days in the payment terms ('{v}') could not be read")
        if val < 0 or val != int(val) or val > 365:
            raise C.Stop(f"please check the payment terms: {v} days")
        return int(val)

    if kind == "days":
        due = issue + timedelta(days=n_days())
    elif kind == "eom_plus":
        due = end_of_month(issue) + timedelta(days=n_days(0))
    elif kind == "end_next_month":
        due = end_of_month(add_months(date(issue.year, issue.month, 1), 1))
    elif kind == "next_month_day":
        day = n_days()
        nm = add_months(date(issue.year, issue.month, 1), 1)
        due = date(nm.year, nm.month, min(max(day, 1), calendar.monthrange(nm.year, nm.month)[1]))
    elif kind == "on_receipt":
        due = issue
    elif kind == "fixed":
        due = read_date(t.get("date"), order, today, prefer="future", months=months)
    else:  # in_advance
        start = read_date(t.get("start"), order, today, prefer="future", months=months)
        due = start - timedelta(days=n_days(0))
        if due < issue:
            notes.append(f"FLAG: the work starts {start.isoformat()}, so payment in advance falls due on the invoice date")
            due = issue
    if due < issue:
        raise C.Stop(f"the due date {due.isoformat()} is before the invoice date {issue.isoformat()}. Check the payment terms")
    return due, notes


def day_off_warning(d, days_off=(5, 6), holidays=()):
    """A warning if the date is a day the founder named as off, or a holiday they gave. The date is never moved."""
    if d.weekday() in set(days_off):
        return "falls on a day off"
    for h in holidays or ():
        if h == d:
            return "falls on a holiday you named"
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    a = sub.add_parser("due")
    a.add_argument("--issue", required=True)
    a.add_argument("--terms", required=True)
    a.add_argument("--country", default="")
    b = sub.add_parser("read")
    b.add_argument("text")
    b.add_argument("--country", default="")
    b.add_argument("--today")
    args = ap.parse_args()
    if args.cmd == "due":
        order = LN.locale_defaults(args.country)["date_order"]
        issue = read_date(args.issue, order)
        due, notes = resolve_due(issue, parse_terms_spec(args.terms), order)
        print(f"DUE: {due.isoformat()} ({EN_DAYS[due.weekday()]})")
        for n in notes:
            print(n)
        return 0
    if args.cmd == "read":
        order = LN.locale_defaults(args.country)["date_order"]
        today = parse_iso(args.today) if args.today else None
        d = read_date(args.text, order, today)
        print(f"DATE: {d.isoformat()} ({EN_DAYS[d.weekday()]})")
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    C.run_main(main)
