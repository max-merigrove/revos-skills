#!/usr/bin/env python3
"""Date maths for The Price Rise Pack: notice, alignment, billing dates, renewals, weekdays.

Standard library only. No network calls. Used by rise_plan.py; can be run on its own:
  python3 scripts/dates.py effective --send 2026-11-02 --notice "30 days" --billing-day 1
  python3 scripts/dates.py effective --send 2026-11-02 --notice "3 months" --align quarter_end --billing-day 1
  python3 scripts/dates.py format 2027-04-01 --country DE --sep .

Every date the skill prints comes from here, with its weekday. Nothing here says whether a
date meets a contract or a law; the founder supplies the notice terms and confirms them.
"""
import argparse
import calendar
import re
import sys
from datetime import date, timedelta

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAY_ABBR = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
ALIGNMENTS = {"none", "month_end", "quarter_end", "year_end"}


class DateStop(ValueError):
    """A date the founder gave cannot be read or cannot be right."""


# ------------------------------------------------------------------ reading
_MONTH_WORDS = {m.lower(): i + 1 for i, m in enumerate(MONTHS)}
_MONTH_WORDS.update({m[:3].lower(): i + 1 for i, m in enumerate(MONTHS)})
_MONTH_WORDS.update({"sept": 9, "januar": 1, "februar": 2, "märz": 3, "maerz": 3, "mai": 5, "juni": 6, "juli": 7,
                     "oktober": 10, "dezember": 12, "janvier": 1, "février": 2, "mars": 3, "avril": 4, "juin": 6,
                     "juillet": 7, "août": 8, "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12,
                     "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
                     "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12})


def parse_date(text, date_order="DMY", today=None):
    """Read a date the founder typed. ISO always works; otherwise the founder's date order decides.

    Accepts 2026-11-02, 02/11/2026, 11/2/2026 (MDY), 02.11.2026, 2 November 2026, November 2, 2026,
    "1st of April 2027", "31 March" (next occurrence after today). Raises DateStop if it cannot.
    """
    if text is None or str(text).strip() == "":
        raise DateStop("no date given")
    if isinstance(text, date):
        return text
    t = str(text).strip().lower().replace(",", " ")
    today_ = today or date.today()
    t = re.sub(r"^(on|this coming|coming)\s+", lambda m: "this " if "coming" in m.group(1) else "", t.strip())
    bare = re.fullmatch(r"(mon(day)?|tue(s|sday)?|wed(s|nesday)?|thu(r|rs|rsday)?|fri(day)?|sat(urday)?|sun(day)?)\.?", t)
    if bare:  # "thursday" on its own: the next one (a week today if today is that day)
        t = "this " + t
    rel = re.fullmatch(r"(today|tomorrow|next (mon|tue|wed|thu|fri|sat|sun)\w*|this (mon|tue|wed|thu|fri|sat|sun)\w*|"
                       r"in (\d+) (days?|weeks?))", t.strip())
    if rel:
        if t == "today":
            return today_
        if t == "tomorrow":
            return today_ + timedelta(days=1)
        if rel.group(4):
            n = int(rel.group(4))
            return today_ + timedelta(days=n * (7 if rel.group(5).startswith("week") else 1))
        wd = DAY_ABBR.index((rel.group(2) or rel.group(3))[:3])
        ahead = (wd - today_.weekday()) % 7
        if t.startswith("next") or ahead == 0:
            ahead = ahead or 7
        return today_ + timedelta(days=ahead)
    t = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", t)
    t = re.sub(r"\bof\b", " ", t)
    t = re.sub(r"\b(mon|tues?|wed(nes)?|thu(rs)?|fri|sat(ur)?|sun)(day)?\b\.?", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", t)
    if m:
        return _mk(int(m.group(1)), int(m.group(2)), int(m.group(3)), text)
    m = re.fullmatch(r"(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2,4})", t)
    if m:
        a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        y = y + 2000 if y < 100 else y
        if date_order == "MDY":
            return _mk(y, a, b, text)
        if date_order == "YMD":
            raise DateStop(f"'{text}': write it as year-month-day, for example 2027-04-01")
        return _mk(y, b, a, text)
    m = re.fullmatch(r"(\d{4})[/.](\d{1,2})[/.](\d{1,2})", t)
    if m:
        return _mk(int(m.group(1)), int(m.group(2)), int(m.group(3)), text)
    m = re.fullmatch(r"(\d{1,2})\.? ([a-zäéû]+)\.? ?(\d{4})?", t)
    if m and m.group(2) in _MONTH_WORDS:
        return _year_or_next(int(m.group(1)), _MONTH_WORDS[m.group(2)], m.group(3), today, text)
    m = re.fullmatch(r"([a-zäéû]+)\.? (\d{1,2}) ?(\d{4})?", t)
    if m and m.group(1) in _MONTH_WORDS:
        return _year_or_next(int(m.group(2)), _MONTH_WORDS[m.group(1)], m.group(3), today, text)
    m = re.fullmatch(r"([a-zäéû]+)\.? (\d{4})", t)
    if m and m.group(1) in _MONTH_WORDS:
        return _mk(int(m.group(2)), _MONTH_WORDS[m.group(1)], 1, text)
    if t in _MONTH_WORDS:  # "from April": the first of the next April
        return _year_or_next(1, _MONTH_WORDS[t], None, today, text)
    raise DateStop(f"'{text}' could not be read as a date; give it as day, month and year")


def _mk(y, mo, d, raw):
    try:
        return date(y, mo, d)
    except ValueError:
        raise DateStop(f"'{raw}' is not a real date") from None


def _year_or_next(d, mo, y, today, raw):
    if y:
        return _mk(int(y), mo, d, raw)
    today = today or date.today()
    cand = _mk(today.year, mo, d, raw)
    return cand if cand >= today else _mk(today.year + 1, mo, d, raw)


def parse_year(text):
    """'2021', 'since Mar 2022', 'Jan 2020' -> (year, month or None)."""
    t = str(text or "").lower()
    m = re.search(r"(19|20)\d{2}", t)
    if not m:
        return None, None
    month = None
    for w, n in _MONTH_WORDS.items():
        if re.search(r"\b" + re.escape(w) + r"\b", t):
            month = n
            break
    return int(m.group(0)), month


_ALIGN_PHRASES = [
    ("quarter_end", r"(?:zum|bis zum|to(?: the)?|at(?: the)?|until(?: the)?|by(?: the)?|running to(?: the)?|"
                    r"à la|a la|al|hasta el|au)?\s*(?:end of (?:the |a |each )?(?:calendar )?quarter|"
                    r"(?:calendar )?quarter[- ]?end|quartalsende|ende (?:des|eines) (?:kalender)?quartals|"
                    r"fin (?:du|de|del) trimestre|final del trimestre)"),
    ("month_end", r"(?:zum|bis zum|to(?: the)?|at(?: the)?|until(?: the)?|by(?: the)?|running to(?: the)?|"
                  r"à la|a la|al|hasta el|au)?\s*(?:end of (?:the |a |each )?(?:calendar )?month|(?:calendar )?month[- ]?end|"
                  r"monatsende|ende (?:des|eines) (?:kalender)?monats|fin (?:du|de|del) mois|fin de mois|final del mes|"
                  r"fin del mes|eom)"),
    ("year_end", r"(?:zum|bis zum|to(?: the)?|at(?: the)?|until(?: the)?|by(?: the)?|running to(?: the)?)?\s*"
                 r"(?:end of (?:the |a )?(?:calendar )?year|(?:calendar )?year[- ]?end|jahresende|ende des (?:kalender)?jahres|"
                 r"fin d'?ann[ée]e|fin de a[ñn]o)"),
]
# Words that may follow a notice without changing it ("60 days written notice", "3 Monate schriftlich").
_NOTICE_FILLER = {
    "notice", "notices", "written", "in", "writing", "prior", "advance", "beforehand", "before", "of", "the", "a",
    "period", "minimum", "min", "at", "least", "required", "rolling", "by", "email", "e-mail", "mail", "either",
    "side", "party", "parties", "both", "sides", "mutual", "each", "way", "on", "change", "changes", "price",
    "pricing", "fee", "fees", "and", "month-to-month", "contract", "contracts", "agreement", "notification",
    "schriftlich", "schriftliche", "kündigungsfrist", "frist", "vorher", "im", "voraus", "vorab", "préavis", "preavis",
    "de", "preaviso", "aviso", "por", "escrito", "par", "écrit", "ecrit", "approx", "about", "roughly", "around",
    "calendar", "clear", "full", "s", "standard", "usual", "normal", "only",
}


def parse_notice_full(text):
    """Read a notice and any period-end alignment written into it.

    Returns (notice, alignment or None), where notice is ('days', n) or ('months', n).
    '3 Monate zum Quartalsende' -> (('months', 3), 'quarter_end'); '30 days to month end' -> (('days', 30), 'month_end').
    Raises DateStop when words after the number and unit are not understood ('30 days or at renewal'),
    so a notice is never half read.
    """
    if text is None or str(text).strip() == "":
        return None, None
    if isinstance(text, (int, float)):
        return ("days", int(text)), None
    t = str(text).strip().lower()
    t = t.replace("month to month", "month-to-month").replace("’", "'")
    align = None
    for name, pat in _ALIGN_PHRASES:
        m = re.search(pat, t)
        if m:
            if align and align != name:
                raise DateStop(f"'{text}' names two period ends; which one does the notice run to?")
            align = name
            t = (t[:m.start()] + " " + t[m.end():]).strip()
    words = {"one": 1, "two": 2, "three": 3, "four": 4, "six": 6, "a": 1, "thirty": 30, "sixty": 60, "ninety": 90}
    if re.fullmatch(r"\d+", t):
        return ("days", int(t)), align
    m = re.search(r"(?<![\w.,])(\d+|one|two|three|four|six|thirty|sixty|ninety|a)\s*(days?|tage?n?|d[ií]as?|jours?|weeks?|"
                  r"wochen?|semanas?|semaines?|months?|monate?n?|mois|meses?|m|d|w)\b", t)
    if not m:
        raise DateStop(f"'{text}': give the notice as a number of days, weeks or months")
    rest = re.findall(r"[\w'\-éèàçñäöüß]+", t[m.end():])
    unknown = [w for w in rest if w.strip("'") not in _NOTICE_FILLER]
    if unknown:
        raise DateStop(f"'{text}': I read {m.group(0)} but not '{' '.join(unknown)}' after it; say what the notice "
                       f"runs to (a month end, a quarter end, a renewal) or give the notice alone")
    n = int(m.group(1)) if m.group(1).isdigit() else words[m.group(1)]
    unit = m.group(2)
    if unit.startswith(("w", "semana", "semaine")):
        return ("days", n * 7), align
    if unit.startswith(("mon", "mois", "mes")) or unit == "m":
        return ("months", n), align
    return ("days", n), align


def parse_notice(text):
    """'30 days', '60', '3 months', '8 weeks', '90 Tage', '3 Monate', '60 days written notice' -> ('days', n) or ('months', n).

    Any period end written into the text is read by parse_notice_full; use that when the alignment matters.
    """
    return parse_notice_full(text)[0]


def notice_text(notice):
    kind, n = notice
    if kind == "months":
        return f"{n} month{'s' if n != 1 else ''}"
    return f"{n} day{'s' if n != 1 else ''}"


# ------------------------------------------------------------------ arithmetic
def add_months(d, n, day=None):
    y, m = divmod(d.month - 1 + n, 12)
    y += d.year
    m += 1
    want = day if day is not None else d.day
    return date(y, m, min(want, calendar.monthrange(y, m)[1]))


def notice_end(send, notice):
    kind, n = notice
    return add_months(send, n) if kind == "months" else send + timedelta(days=n)


def align(d, alignment):
    """Roll a date forward to the end of its month, quarter or year."""
    if alignment in (None, "", "none"):
        return d
    if alignment == "month_end":
        return date(d.year, d.month, calendar.monthrange(d.year, d.month)[1])
    if alignment == "quarter_end":
        qm = ((d.month - 1) // 3 + 1) * 3
        return date(d.year, qm, calendar.monthrange(d.year, qm)[1])
    if alignment == "year_end":
        return date(d.year, 12, 31)
    raise DateStop(f"alignment '{alignment}' not known; use none, month_end, quarter_end or year_end")


def billing_dates(start, end, every_months=1, day=1, months=None):
    """Billing dates d with start <= d < end. months: the calendar months billed in (quarterly, annual)."""
    out = []
    if months:
        months = sorted(set(int(x) for x in months))
    cur = date(start.year, start.month, 1)
    cur = add_months(cur, -12)
    while cur < end:
        if (months and cur.month in months) or (not months and every_months == 1):
            d = date(cur.year, cur.month, min(day, calendar.monthrange(cur.year, cur.month)[1]))
            if start <= d < end:
                out.append(d)
        cur = add_months(cur, 1, 1)
    if not months and every_months != 1:
        raise DateStop("billing every few months needs the months it falls in")
    return out


def first_billing_on_or_after(d, every_months=1, day=1, months=None):
    found = billing_dates(d, add_months(d, 25), every_months, day, months)
    if not found:
        raise DateStop("no billing date found in the two years after the notice ends; check the billing months")
    return found[0]


def default_months(every_months, anchor_month):
    """Calendar months for a cadence, anchored on a month the founder gave (or January)."""
    a = anchor_month or 1
    if every_months == 1:
        return None
    return sorted({((a - 1 + k * every_months) % 12) + 1 for k in range(12 // every_months)})


def is_working_day(d, working="mon-fri"):
    return d.weekday() in working_days(working)


def working_days(text):
    t = str(text or "mon-fri").lower()
    m = re.search(r"(mon|tue|wed|thu|fri|sat|sun)\w*\s*(?:-|to|through|thru)\s*(mon|tue|wed|thu|fri|sat|sun)", t)
    if m:
        a, b = DAY_ABBR.index(m.group(1)), DAY_ABBR.index(m.group(2))
        return {(a + i) % 7 for i in range((b - a) % 7 + 1)}
    found = {i for i, d in enumerate(DAY_ABBR) if re.search(r"\b" + d, t)}
    return found or {0, 1, 2, 3, 4}


# ------------------------------------------------------------------ writing
def fmt(d, order="DMY", sep="/", long=False, weekday=False, american=False):
    """Write a date the founder's way. long: 1 April 2027 / April 1, 2027 / 1. April 2027 (dot style)."""
    if d is None:
        return ""
    wd = WEEKDAYS[d.weekday()] + " " if weekday else ""
    if long:
        if order == "MDY" or american:
            return f"{wd.strip() + ', ' if wd else ''}{MONTHS[d.month - 1]} {d.day}, {d.year}"
        if order == "YMD":
            return f"{wd}{d.isoformat()}"
        dot = "." if sep == "." else ""
        return f"{wd}{d.day}{dot} {MONTHS[d.month - 1]} {d.year}"
    if order == "MDY":
        s = f"{d.month}{sep}{d.day}{sep}{d.year}"
    elif order == "YMD":
        s = d.isoformat()
    else:
        s = f"{d.day:02d}{sep}{d.month:02d}{sep}{d.year}" if sep in "./" else f"{d.day}{sep}{d.month}{sep}{d.year}"
    return wd + s


def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = a.add_subparsers(dest="cmd")
    e = sub.add_parser("effective")
    e.add_argument("--send", required=True)
    e.add_argument("--notice", default="60 days")
    e.add_argument("--align", default="none")
    e.add_argument("--billing-day", type=int, default=1)
    e.add_argument("--order", default="DMY")
    f = sub.add_parser("format")
    f.add_argument("date")
    f.add_argument("--order", default="DMY")
    f.add_argument("--sep", default="/")
    args = a.parse_args()
    try:
        if args.cmd == "effective":
            s = parse_date(args.send, args.order)
            n = parse_notice(args.notice)
            end = align(notice_end(s, n), args.align)
            start = end + timedelta(days=1) if args.align not in ("none", "") else end
            eff = first_billing_on_or_after(start, 1, args.billing_day)
            print(f"send {fmt(s, args.order, weekday=True, long=True)}; notice {notice_text(n)} ends "
                  f"{fmt(end, args.order, long=True)}; effective {fmt(eff, args.order, weekday=True, long=True)}")
        elif args.cmd == "format":
            print(fmt(parse_date(args.date, args.order), args.order, args.sep, long=True, weekday=True))
        else:
            a.print_help()
            sys.exit(2)
    except DateStop as x:
        print(f"STOP: {x}")
        sys.exit(2)


if __name__ == "__main__":
    main()
