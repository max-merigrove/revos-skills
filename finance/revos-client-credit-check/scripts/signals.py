#!/usr/bin/env python3
"""Signal catalogue and date helpers for Client Credit Check.

Usage (paths relative to this skill's folder):
  python3 scripts/signals.py catalogue            print every signal: id, severity, what it is
  python3 scripts/signals.py date "12.09.2025" [--order DMY]   read one founder-typed date
  python3 scripts/signals.py age "12.09.2025" --asof 2026-11-02 [--order DMY]   months since a date
  python3 scripts/signals.py --self-test

Severities: stop (verified alone decides Stop), major (decides Caution), minor (two or more decide Caution),
context (shown, never decides). Every threshold here is a working default, never a benchmark.
Standard library only. No network calls. Exit 2 with a STOP line on bad input.
"""
import re
import sys
from datetime import date, timedelta

# Working defaults. Shown in the brief's assumptions; the founder can change any of them.
AGE_LINE_MONTHS = 12          # R6: registered this many months ago or less
OFFICER_CHANGES_LINE = 2      # R7: more than this many officer changes in 12 months
REVIEWS_MAJOR = 3             # R10: this many independent reports of non-payment is major
FAILED_LINKS_MAJOR = 2        # R11: this many linked entities dissolved or insolvent in 24 months is major
LONG_TERMS_DAYS = 60          # F1: a new client asking for this many days or more
RECHECK_DAYS = 90             # findings older than this are stale on a return run

# id: (severity, short name, where to see it, how to word it)
CATALOGUE = {
    "R1": ("stop", "Register entry missing or not matching",
           "the official company register for the client's country",
           "The register shows no entry for '{name}' as at {date}"),
    "R2": ("stop", "Status not active", "the register entry",
           "The register shows the status as '{text}' as at {date}"),
    "R3": ("stop", "Insolvency, winding-up or administration notice", "the official notices source for the country",
           "{source} lists a notice: '{text}' ({date})"),
    "R4": ("major", "Public judgment or recorded unpaid debt", "a public judgments register, where the country has one",
           "{source} shows: '{text}'"),
    "R5": ("minor", "Filings overdue", "the register entry (accounts or annual return due dates)",
           "The register shows: '{text}'"),
    "R6": ("minor", "Registered in the last 12 months", "the register entry (date registered)",
           "Registered {text}: no filing history to read yet, which is no history, not bad history"),
    "R7": ("minor", "More than two officer changes in 12 months", "the register's officers list",
           "The register shows {text}"),
    "R8": ("minor", "Registered address changed in 12 months, or an agent or virtual address only",
           "the register entry and its filing history", "The register shows: '{text}'"),
    "R9": ("context", "Outstanding secured charges or liens", "the register's charges section, where published",
           "The register shows: '{text}'. Common for businesses with a bank loan; context, not a finding"),
    "R10": ("minor", "Public reports of non-payment by this entity", "review sites and forums naming the entity",
            "{text}"),
    "R11": ("context", "Officers linked to entities dissolved or insolvent in 24 months",
            "the register's own appointments pages only", "The register shows: '{text}'"),
    "R12": ("context", "Small or micro accounts only", "the register's filing history",
            "Only small or micro accounts are filed, which show little"),
    "R13": ("minor", "Website, domain or contact details do not match the entity", "the client's own website",
            "{text}"),
    "R14": ("minor", "A claim that the register contradicts", "the register entry, against what the client or contract says",
            "Told: '{claim}'. The register shows: {shows}"),
    "R15": ("major", "Contract name differs from the register", "the register entry, against the name on the contract",
            "The contract names '{contract}'; the register shows '{register}'. Fix before signing"),
    "F1": ("minor", "Asks for 60 days or more as a new client", "you told me", "They asked for {text}"),
    "F2": ("major", "Refuses or strongly resists any deposit", "you told me", "{text}"),
    "F3": ("major", "Presses to start before a contract is signed", "you told me", "{text}"),
    "F4": ("minor", "Slow to sign the contract", "you told me", "{text}"),
    "F5": ("minor", "Asks for free samples or offers exposure instead of pay", "you told me", "{text}"),
    "F6": ("minor", "Budget does not fit the scope", "you told me", "{text}"),
    "F7": ("context", "Blames the previous supplier for the mess", "you told me", "{text}"),
    "F8": ("minor", "Pays only on a 'completion' the client defines", "you told me", "{text}"),
    "F9": ("minor", "Contact details informal or not agreeing", "you told me", "{text}"),
}
REGISTER_IDS = [k for k in CATALOGUE if k.startswith("R")]
FOUNDER_IDS = [k for k in CATALOGUE if k.startswith("F")]
CONFIDENCE = ("verified", "public report", "founder reported", "unverified")


class DateError(ValueError):
    pass


MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
MONTHS.update({"mär": 3, "mrz": 3, "mai": 5, "okt": 10, "dez": 12, "janv": 1, "févr": 2, "avr": 4, "juin": 6,
               "juil": 7, "août": 8, "déc": 12, "ene": 1, "abr": 4, "ago": 8, "dic": 12, "giu": 6, "lug": 7,
               "set": 9, "ott": 10, "maart": 3, "mei": 5, "januar": 1, "februar": 2, "märz": 3, "juni": 6,
               "juli": 7, "oktober": 10, "dezember": 12})


def read_date(text, order=None):
    """Read a founder-typed or register date. order: DMY, MDY or YMD (from the founder's country or what they
    said). Returns a date. Raises DateError with a plain question when it cannot be read or reads two ways."""
    if isinstance(text, date):
        return text
    t = str(text or "").strip().lower().replace(",", " ")
    if not t:
        raise DateError("no date given")
    if re.fullmatch(r"(19|20)\d{2}", t):  # a year only: the latest day in it, so age is never overstated
        return date(int(t), 12, 31)
    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})(?:t.*)?", t)
    if m:
        return _mk(int(m.group(1)), int(m.group(2)), int(m.group(3)), text)
    m = re.fullmatch(r"(\d{1,2})(?:st|nd|rd|th)?\.?\s+([a-zäéû]+)\.?\s+(\d{4})", t)
    if m and _month(m.group(2)):
        return _mk(int(m.group(3)), _month(m.group(2)), int(m.group(1)), text)
    m = re.fullmatch(r"([a-zäéû]+)\.?\s+(\d{1,2})(?:st|nd|rd|th)?\s+(\d{4})", t)
    if m and _month(m.group(1)):
        return _mk(int(m.group(3)), _month(m.group(1)), int(m.group(2)), text)
    m = re.fullmatch(r"([a-zäéû]+)\.?\s+(\d{4})", t)
    if m and _month(m.group(1)):
        return _mk(int(m.group(2)), _month(m.group(1)), 1, text)
    m = re.fullmatch(r"(\d{1,4})[./\- ](\d{1,2})[./\- ](\d{2,4})", t)
    if not m:
        raise DateError(f"'{text}' could not be read as a date; give it as day, month and year")
    a, b, c = m.group(1), m.group(2), m.group(3)
    if len(a) == 4:
        return _mk(int(a), int(b), int(c), text)
    y = int(c) + (2000 if len(c) == 2 else 0)
    a, b = int(a), int(b)
    if a > 12 and b <= 12:
        return _mk(y, b, a, text)
    if b > 12 and a <= 12:
        return _mk(y, a, b, text)
    if a == b:
        return _mk(y, a, b, text)
    o = (order or "").upper()
    if o == "DMY":
        return _mk(y, b, a, text)
    if o == "MDY":
        return _mk(y, a, b, text)
    raise DateError(f"'{text}' reads two ways: is it {a} {_mname(b)} or {_mname(a)} {b}?")


def _month(word):
    w = word.strip(".")
    for k, v in MONTHS.items():
        if w == k or (len(w) >= 3 and w.startswith(k)) or (len(k) > 3 and k.startswith(w) and len(w) >= 3):
            return v
    return None


def _mname(n):
    return ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
            "November", "December"][n - 1] if 1 <= n <= 12 else str(n)


def _mk(y, m, d, raw):
    try:
        return date(y, m, d)
    except ValueError:
        raise DateError(f"'{raw}' is not a real date")


def months_between(earlier, later):
    """Whole and part months from earlier to later (30.44 days a month)."""
    return (later - earlier).days / 30.4375


def age_text(registered, asof):
    """'14 months ago (12 September 2025)' style, in months under two years, else years."""
    m = months_between(registered, asof)
    if m < 24:
        return f"{int(m)} months ago"
    return f"{int(m // 12)} years ago"


def check_not_future(d, asof, what):
    if d > asof:
        raise DateError(f"the {what} date {d.isoformat()} is after the check date {asof.isoformat()}; please check it")


def count_in_window(dates, asof, months=12):
    start = asof - timedelta(days=round(months * 30.4375))
    return sum(1 for d in dates if start <= d <= asof)


def stale(checked, asof, window_days=RECHECK_DAYS):
    return (asof - checked).days > window_days


def fmt_date(d, order="DMY", style="long", sep="/", english="en-GB"):
    """Write a date the founder's way: long words in their order, or numeric with their separator."""
    if style == "numeric":
        if order == "MDY":
            return f"{d.month:02d}{sep}{d.day:02d}{sep}{d.year}"
        if order == "YMD":
            return f"{d.year}{sep}{d.month:02d}{sep}{d.day:02d}"
        return f"{d.day:02d}{sep}{d.month:02d}{sep}{d.year}"
    if order == "MDY":
        return f"{_mname(d.month)} {d.day}, {d.year}"
    if order == "YMD":
        return d.isoformat()
    return f"{d.day} {_mname(d.month)} {d.year}"


def date_style_from(samples):
    """('numeric', sep) if the founder typed numeric dates, else ('long', '')."""
    for s in samples or []:
        m = re.search(r"\b\d{1,2}([./\-])\d{1,2}\1\d{2,4}\b", str(s))
        if m:
            return "numeric", m.group(1)
    return "long", ""


def _self_test():
    ok = fail = 0

    def eq(got, exp, label):
        nonlocal ok, fail
        if got == exp:
            ok += 1
        else:
            fail += 1
            print("FAIL", label, "got", got, "expected", exp)

    def raises(fn, label):
        nonlocal ok, fail
        try:
            fn()
            fail += 1
            print("FAIL (no error)", label)
        except DateError:
            ok += 1

    eq(read_date("12.09.2025", "DMY"), date(2025, 9, 12), "de dots")
    raises(lambda: read_date("12.09.2025"), "dmy ambiguous needs order")
    raises(lambda: read_date("03/04/2025"), "ambiguous without order")
    eq(read_date("03/04/2025", "MDY"), date(2025, 3, 4), "mdy")
    eq(read_date("03/14/2025"), date(2025, 3, 14), "mdy obvious")
    eq(read_date("11/07/2023", "DMY"), date(2023, 7, 11), "in dmy")
    eq(read_date("2026-02-03"), date(2026, 2, 3), "iso")
    eq(read_date("2016"), date(2016, 12, 31), "year only")
    eq(read_date("10 October 1984"), date(1984, 10, 10), "long")
    eq(read_date("Oct 10, 1984"), date(1984, 10, 10), "us long")
    eq(read_date("12 Jun 2012"), date(2012, 6, 12), "short month")
    eq(read_date("3. Februar 2026"), date(2026, 2, 3), "german month")
    eq(read_date("1/1/26", "DMY"), date(2026, 1, 1), "two digit year")
    raises(lambda: read_date("31.02.2025", "DMY"), "not real")
    raises(lambda: read_date("next friday"), "words")
    raises(lambda: check_not_future(date(2027, 1, 1), date(2026, 11, 2), "registration"), "future")
    eq(int(months_between(date(2025, 9, 12), date(2026, 11, 2))), 13, "13.7 months")
    eq(count_in_window([date(2026, 2, 3), date(2025, 1, 1)], date(2026, 11, 2)), 1, "window")
    eq(stale(date(2026, 7, 1), date(2026, 11, 2)), True, "stale")
    eq(fmt_date(date(2026, 11, 2), "DMY", "numeric", "."), "02.11.2026", "fmt de")
    eq(fmt_date(date(2026, 11, 2), "MDY"), "November 2, 2026", "fmt us")
    eq(date_style_from(["eingetragen 12.09.2025"]), ("numeric", "."), "style")
    eq(len(CATALOGUE), 24, "catalogue size")
    print(f"{ok} passed, {fail} failed")
    return fail == 0


def main(argv):
    if not argv or argv[0] in {"-h", "--help"}:
        print(__doc__)
        return 0
    if argv[0] == "--self-test":
        return 0 if _self_test() else 1
    if argv[0] == "catalogue":
        for k, (sev, name, where, _) in CATALOGUE.items():
            print(f"{k:4} {sev:8} {name} (where: {where})")
        return 0
    try:
        order = argv[argv.index("--order") + 1] if "--order" in argv else None
        if argv[0] == "date" and len(argv) > 1:
            print(read_date(argv[1], order).isoformat())
            return 0
        if argv[0] == "age" and len(argv) > 1 and "--asof" in argv:
            asof = read_date(argv[argv.index("--asof") + 1])
            d = read_date(argv[1], order)
            check_not_future(d, asof, "given")
            print(f"{months_between(d, asof):.1f} months")
            return 0
    except DateError as e:
        print(f"STOP: {e}.")
        return 2
    print("STOP: unknown command; run with --help.")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
