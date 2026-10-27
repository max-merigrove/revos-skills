#!/usr/bin/env python3
"""Get Paid: due dates, days late, the chase stage for each client, payment plans, any late fee the
founder's own contract sets, and the plan document.

Usage (paths relative to this skill's folder):
  python3 scripts/chase_plan.py template                         print an empty inputs file
  python3 scripts/chase_plan.py compute <inputs.json> --out <results.json> [--as-of YYYY-MM-DD]
        work out due dates, days late, the stage each client is at, the dated chase plan, payment
        plan instalments and, only where the founder's contract states one, the late fee or
        interest; print a plain table and every NEED and FLAG line
  python3 scripts/chase_plan.py drafts <results.json> --out <chasers.md>
        write a draft of every message (send now and later stages) with the figures filled in,
        for Claude to put into the founder's voice
  python3 scripts/chase_plan.py build <results.json> --chasers <chasers.md> --out <folder>
        [--note <note.md>]
        check the messages against the figures, then write the one main file:
        get-paid-plan-<business>-<date>.docx

Exit codes: 0 done; 1 done, with NEED lines the founder should fill; 2 STOP, nothing usable was
written (read the STOP line, fix the input, run again).

Standard library only. No network calls. No country's rules are built in: currency, date order,
working week, holidays, payment terms and any late fee all come from the founder. The only
arithmetic is plain arithmetic on the founder's own figures.
"""
import argparse
import calendar
import json
import re
import sys
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import locale_numbers as ln  # noqa: E402  (shared Merigrove reader, copied unchanged)

# ---------------------------------------------------------------------------------------------
# WORKING DEFAULTS. Merigrove's chase rhythm, not law. Each is said out loud before computing.
# ---------------------------------------------------------------------------------------------
# Days late at which each stage is due, by how much the client matters.
STAGE_DAYS = {"valued": [1, 14, 30, 60], "normal": [1, 14, 30, 45], "persistent": [1, 1, 14, 30]}
FIRST_CONTACT_MAX = {"valued": 2, "normal": 2, "persistent": 3}  # first message is never the final notice
GAP_DAYS = 7          # at least a week between stages
# However late the invoice, stages are spaced from the first message actually sent, not from lateness.
MIN_GAP = {"valued": 14, "normal": 7, "persistent": 7}          # days between one message and the next
MIN_TO_FINAL = {"valued": 28, "normal": 14, "persistent": 14}   # days from the first message to the final notice
MIN_GAP_BEFORE_FINAL = 14   # a client offered a plan gets two weeks to answer it before any final notice
# The founder's own spacing ("space them 14 days apart", "final notice 28 days after the first") overrides the
# two tables above, globally (top-level gap_days / final_after_days) or for one client.
PLAUSIBLE_MAX_RATE = Decimal(100)   # a contract rate above this a year is checked with the founder before use
PLAUSIBLE_MAX_AGE_DAYS = 3 * 365    # an invoice older than this is checked (often a year typed wrong)
HOLIDAY_WINDOW_DAYS = 56            # dates listed for the founder to check against their own holidays
ZERO_DECIMAL = {"JPY", "KRW", "VND", "CLP", "ISK", "PYG", "UGX", "IDR"}
PAY_WITHIN_DAYS = 7   # pay-by date is a week after sending
DEFAULT_TERMS_DAYS = 30   # used only when no due date or terms were given, and flagged
DEFAULT_PLAN = {"instalments": 3, "every": "month"}
DEFAULT_PREVENTION = {"deposit_pct": "50", "milestones": "40/30/30", "card_on_file": True}
DEFAULT_WEEKEND = ["sat", "sun"]
OLD_DEBT_DAYS = 365
MAX_INSTALMENTS = 12
SKILL = "revos-get-paid"
SKILL_NAME = "Get Paid"
# ---------------------------------------------------------------------------------------------

CENT = Decimal("0.01")
MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
MONTHS.update({m.lower(): i for i, m in enumerate(calendar.month_abbr) if m})
MONTHS["sept"] = 9
WEEKDAYS = {d.lower(): i for i, d in enumerate(calendar.day_name)}
WEEKDAYS.update({d.lower(): i for i, d in enumerate(calendar.day_abbr)})
WEEKDAYS.update({"tues": 1, "thur": 3, "thurs": 3})
# Symbol for a currency, and the locales where the bare symbol reads naturally.
CURRENCIES = {
    "USD": ("$", {"en-us"}, "US$"), "AUD": ("$", {"en-au"}, "A$"), "CAD": ("$", {"en-ca"}, "C$"),
    "NZD": ("$", {"en-nz"}, "NZ$"), "SGD": ("$", {"en-sg"}, "S$"), "HKD": ("$", {"en-hk"}, "HK$"),
    "GBP": ("\u00a3", None, "\u00a3"), "EUR": ("\u20ac", None, "\u20ac"), "INR": ("\u20b9", None, "\u20b9"), "JPY": ("\u00a5", None, "\u00a5"),
    "ZAR": ("R", None, "R"), "AED": ("AED ", None, "AED "), "CHF": ("CHF ", None, "CHF "),
}
MDY_LOCALES = {"en-us", "en-ph"}
US_SPELLING = {"en-us", "en-ph"}
ACTIONS = {
    "advice": "take advice on recovering the full amount",
    "pause": "pause any further work for you until the account is settled",
    "collections": "pass the debt to a collections service",
    "lawyer": "ask a lawyer to recover it",
}
ACTION_LABELS = {"advice": "take advice", "pause": "stop work", "collections": "collections service", "lawyer": "lawyer"}
STAGE_NAMES = {1: "Reminder", 2: "Firm reminder", 3: "Call and payment plan", 4: "Final notice"}
KIND_NAMES = {"reminder": "reminder", "firm": "firm reminder", "plan": "call and payment plan offer",
              "call_plan": "call and payment plan offer", "late_fee": "late fee notice and payment plan offer",
              "final": "final notice", "final_nofee": "final notice"}
TIER_LABELS = {"valued": "keep at all costs", "normal": "normal", "persistent": "always pays late"}


class Stop(Exception):
    pass


class Need(Exception):
    pass


# ----------------------------------------------------------------------------- parsing helpers

def q(x):
    """Round to the currency's smallest unit (cents, or whole units for currencies without them)."""
    return Decimal(x).quantize(_STYLE.get("quantum") or CENT, rounding=ROUND_HALF_UP)


def _safe_arith(expr):
    if not re.fullmatch(r"[\d.\s+\-*/()]+", expr):
        raise Need(f"'{expr}' is not a sum I can work out")
    try:
        val = eval(expr, {"__builtins__": {}}, {})  # digits and operators only, checked above
    except Exception:  # noqa: BLE001
        raise Need(f"'{expr}' is not a sum I can work out")
    return Decimal(str(val))


TAX_WORDS = r"(vat|gst|hst|pst|sales tax|tax|mwst|tva|iva|btw)"
SKIP_WORDS = {"", "?", "skip", "none", "n/a", "na", "unknown", "tbc", "null", "-"}
VAGUE_CURRENCIES = {"DOLLAR", "PESO", "SHILLING"}


def _to_decimal(v):
    return Decimal(repr(float(v))) if isinstance(v, float) else Decimal(str(v))


def _currency_fits(seen, expect):
    """True when the currency written beside a figure is consistent with the invoices' currency."""
    if not seen or not expect:
        return True
    if seen in VAGUE_CURRENCIES:
        return seen != "DOLLAR" or expect.endswith("D")
    return expect in seen.split("_OR_")


def parse_money(x, what="amount", decimal=None, expect_cur=None, allow_approx=False):
    """Founder-typed money to Decimal, read by locale_numbers in the founder's decimal style.

    Skill-specific forms kept here: '=1200*2', 'inc GST' (kept as the invoice total), '+ GST' or
    'ex VAT' (a NEED: the skill never adds tax), and fee words around the figure ('$50 late fee')."""
    if x is None:
        return None
    if isinstance(x, bool):
        raise Need(f"{what}: '{x}' is not an amount")
    if isinstance(x, (int, float, Decimal)):
        v = _to_decimal(x)
    else:
        s = str(x).strip()
        if s.lower() in SKIP_WORDS:
            return None
        if re.search(rf"(\+|\bplus\b|\bex\.?|\bexcl?\.?|\bexcluding\b|\bbefore\b|\bnet of\b|\bzzgl\.?|\bhors\b)\s*{TAX_WORDS}\b", s, re.I):
            raise Need(f"{what} '{x}' is before tax: give the total on the invoice the client was sent")
        s = re.sub(rf"\b(inc|incl|including|inkl|ttc)\.?\s*{TAX_WORDS}\b|\bgross\b|\b{TAX_WORDS}\s+inc\w*\b|\bTTC\b", " ", s, flags=re.I)
        s = re.sub(r"\b(late|payment|admin(istration)?|fee|charge|flat|per invoice|each|total)\b", " ", s, flags=re.I)
        s = re.sub(r"\s+", " ", s).strip()
        if s.startswith("="):
            v = _safe_arith(s[1:])
        else:
            try:
                val, seen, notes = ln.parse_money(s, decimal)
            except ln.Ambiguous as e:
                raise Need(f"{what}: {e}")
            except ln.Unreadable:
                raise Need(f"{what} '{x}' is not an amount I can read; give the figure as it is on the invoice")
            if "approximate" in notes and not allow_approx:
                raise Need(f"{what} '{x}' is approximate; give the exact figure on the invoice the client was sent")
            if not _currency_fits(seen, expect_cur):
                raise Need(f"{what} '{x}' looks like {seen.replace('_OR_', ' or ')}, but these invoices are in {expect_cur}; say which is right")
            v = _to_decimal(val)
    if v < 0:
        raise Need(f"{what} '{x}' is negative")
    return q(v)


def typed_money(raw):
    """Every money figure the founder typed, for reading their decimal style and currency once."""
    out = []

    def add(v):
        if isinstance(v, str) and re.search(r"\d", v):
            out.append(v)
    clients = [c for c in (raw.get("clients") or []) if isinstance(c, dict)]
    invs = [i for c in clients for i in (c.get("invoices") or []) if isinstance(i, dict)]
    invs += [i for i in (raw.get("invoices") or []) if isinstance(i, dict)]
    for inv in invs:
        for k in ("amount", "disputed_amount", "total_shown"):
            add(inv.get(k))
        for p in inv.get("payments") or []:
            if isinstance(p, dict):
                add(p.get("amount"))
    own = raw.get("own_late_terms")
    if isinstance(own, dict):
        add(own.get("fee"))
    add((raw.get("prevention") or {}).get("typical_price"))
    add((raw.get("plan") or {}).get("min_amount"))
    return out


def symbol_after(samples):
    """True when the founder writes the currency after the figure (1.200,50 €)."""
    return any(re.search(r"\d\s*(€|£|\$|zł|kr|Kč|CHF|EUR|GBP|USD)\s*$", s) for s in samples)


def parse_days(x, what, decimal=None):
    """A number of days the founder typed: '10', '10 days', '2 weeks', '48 hours', '14 Tage'."""
    if x is None or (isinstance(x, str) and x.strip().lower() in SKIP_WORDS):
        return 0
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return int(x)
    s = str(x).strip().lower()
    try:
        if re.search(r"\b(hours?|hrs?|h|stunden|horas|heures)\b", s):
            h, _ = ln.parse_hours(s, decimal=decimal)
            return int(round(h / 24))
        n, _ = ln.parse_hours(s, day_hours=1.0, week_days=7, decimal=decimal)
        return int(round(n))
    except (ln.Ambiguous, ln.Unreadable):
        raise Need(f"{what} '{x}' should be a number of days")


def add_months(d, n):
    y, m = divmod(d.month - 1 + n, 12)
    y += d.year
    m += 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def end_of_month(d):
    return date(d.year, d.month, calendar.monthrange(d.year, d.month)[1])


def _infer_year(day, month, as_of, prefer):
    """Year for a date typed without one: invoices are in the past, due dates nearest to today."""
    cands = []
    for y in (as_of.year - 1, as_of.year, as_of.year + 1):
        try:
            cands.append(date(y, month, day))
        except ValueError:
            pass
    if not cands:
        raise Need(f"{day}/{month} is not a real date")
    if prefer == "past":
        past = [c for c in cands if c <= as_of]
        return max(past) if past else min(cands)
    return min(cands, key=lambda c: abs((c - as_of).days))


def _mkdate(y, m, d, raw):
    try:
        return date(y, m, d)
    except ValueError:
        raise Need(f"'{raw}' is not a real date")


def parse_date(x, as_of, order=None, prefer="past", what="date"):
    """Founder-typed date. order is 'DMY', 'MDY' or None (unknown: ambiguous numeric dates ask)."""
    if x is None:
        return None
    s = str(x).strip().lower()
    if s in {"", "?", "skip", "none", "n/a", "unknown", "tbc", "null", "-"}:
        return None
    s = re.sub(r"(?<=\d)(st|nd|rd|th)\b", "", s).replace(",", " ").replace(" of ", " ")
    s = re.sub(r"\s+", " ", s).strip()
    if s == "today":
        return as_of
    if s == "yesterday":
        return as_of - timedelta(days=1)
    m = re.fullmatch(r"(an?|\d+) (day|week|month)s? ago", s)
    if m:
        n = 1 if m.group(1) in {"a", "an"} else int(m.group(1))
        if m.group(2) == "day":
            return as_of - timedelta(days=n)
        if m.group(2) == "week":
            return as_of - timedelta(weeks=n)
        return add_months(as_of, -n)
    m = re.fullmatch(r"(?:the |on the )?(\d{1,2})(?: (?:this|the) month| this month)?", s)
    if m and (len(s) <= 2 or "month" in s or s.startswith("the ") or s.startswith("on the ")):
        day = int(m.group(1))
        try:
            d = date(as_of.year, as_of.month, day)
        except ValueError:
            raise Need(f"{what} '{x}' is not a real date")
        return d if d <= as_of or prefer != "past" else add_months(d, -1)
    m = re.fullmatch(r"(?:the )?(\d{1,2}) (?:of )?last month", s)
    if m:
        lm = add_months(as_of, -1)
        return _mkdate(lm.year, lm.month, int(m.group(1)), x)
    m = re.fullmatch(r"last (\w+)", s)
    if m and m.group(1) in WEEKDAYS:
        back = (as_of.weekday() - WEEKDAYS[m.group(1)]) % 7 or 7
        return as_of - timedelta(days=back)
    m = re.fullmatch(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})(t.*)?", s)
    if m:
        return _mkdate(int(m.group(1)), int(m.group(2)), int(m.group(3)), x)
    m = re.fullmatch(r"(\d{1,2})[/.\-](\d{1,2})(?:[/.\-](\d{2,4}))?", s)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        if order in ("MDY", "YMD"):  # year-first countries write the month before the day too
            month, day = a, b
        elif order == "DMY":
            day, month = a, b
        elif a > 12 and b <= 12:
            day, month = a, b
        elif b > 12 and a <= 12:
            month, day = a, b
        elif a == b:
            day, month = a, b
        else:
            raise Need(f"{what} '{x}' could be read two ways: is it day/month or month/day? Say which, or give the month as a word")
        if m.group(3):
            y = int(m.group(3))
            return _mkdate(y + 2000 if y < 100 else y, month, day, x)
        return _infer_year(day, month, as_of, prefer)
    m = re.fullmatch(r"(\d{1,2})[ \-]([a-z]+)\.?(?:[ \-](\d{2,4}))?", s)
    if m and m.group(2) in MONTHS:
        day, month = int(m.group(1)), MONTHS[m.group(2)]
        if m.group(3):
            y = int(m.group(3))
            return _mkdate(y + 2000 if y < 100 else y, month, day, x)
        return _infer_year(day, month, as_of, prefer)
    m = re.fullmatch(r"([a-z]+)\.? (\d{1,2})(?: (\d{2,4}))?", s)
    if m and m.group(1) in MONTHS:
        day, month = int(m.group(2)), MONTHS[m.group(1)]
        if m.group(3):
            y = int(m.group(3))
            return _mkdate(y + 2000 if y < 100 else y, month, day, x)
        return _infer_year(day, month, as_of, prefer)
    raise Need(f"{what} '{x}' is not a date I can read; give a day, month and year")


def parse_terms(x):
    """Payment terms to a rule: ('days', n), ('months', n), ('eom', n), ('eonm', 0)."""
    if x is None:
        return None
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return ("days", int(x))
    s = str(x).strip().lower()
    if s in {"", "?", "skip", "none", "unknown", "null", "no terms", "not agreed", "nothing agreed", "-"}:
        return None
    if re.search(r"(on|upon) receipt|immediate|\bcod\b|on completion|on delivery|due now|due on invoice", s):
        return ("days", 0)
    if re.search(r"end of (the )?(following|next) month", s):
        return ("eonm", 0)
    m = re.search(r"(\d+)\s*(days?|d|dys)?\s*(from |after )?(the )?(end of (the )?month|eom)", s)
    if m:
        return ("eom", int(m.group(1)))
    if re.search(r"\b(end of (the )?month|eom)\b", s):
        return ("eom", 0)
    m = re.search(r"(\d+)\s*(weeks?|wks?)\b", s)
    if m:
        return ("days", int(m.group(1)) * 7)
    m = re.search(r"\b(a|one|\d+)\s*months?\b", s)
    if m:
        n = 1 if m.group(1) in {"a", "one"} else int(m.group(1))
        return ("months", n)
    bare = re.sub(r"\b(net|terms?|payment|within|in|zahlbar|innerhalb|plazo|de|a)\b", " ", s).strip()
    try:  # durations in other words or languages: '30 Tage', '30 dias', '2 semanas'
        n, notes = ln.parse_hours(bare, day_hours=1.0, week_days=7)
        if not any("no unit" in x for x in notes):
            return ("days", int(round(n)))
    except (ln.Ambiguous, ln.Unreadable):
        pass
    m = re.search(r"net\s*(\d+)", s) or re.search(r"(\d+)\s*(days?|d|dys|day terms)?\b", s)
    if m:
        return ("days", int(m.group(1)))
    raise Need(f"payment terms '{x}' are not terms I can read; say a number of days, such as 30 days")


def apply_terms(rule, start):
    kind, n = rule
    if kind == "days":
        return start + timedelta(days=n)
    if kind == "months":
        return add_months(start, n)
    if kind == "eom":
        return end_of_month(start) + timedelta(days=n)
    if kind == "eonm":
        return end_of_month(add_months(date(start.year, start.month, 1), 1))
    raise Stop(f"unknown terms rule {rule}")


def terms_text(rule):
    kind, n = rule
    if kind == "days":
        return "payment on receipt" if n == 0 else f"{n} days"
    if kind == "months":
        return f"{n} month" + ("s" if n != 1 else "")
    if kind == "eom":
        return "end of the month" if n == 0 else f"{n} days after the end of the month"
    return "end of the following month"


PUBLISHED_RATE = (r"\b(base|prime|cash|reference|official|policy|bank|central bank|sofr|libor|euribor|sonia|repo|"
                  r"discount|lending|fed|federal funds|ocr|mclr|hibor|sibor|sora)\b(\s+rate)?")
PERIOD_MONTH = r"(per|a|each|every|/|pro|al|par|por)?\s*(calendar )?(month|mth|mo|monat|mes|mois)\b|\b(pm|p\.m\.|monthly|mensual|mensuel|monatlich)\b"
PERIOD_DAY = r"(per|a|/|pro|al|par|por)?\s*(day|daily|tag|d[ií]a|jour)\b"
PERIOD_YEAR = (r"(per annum|pa|p\.a\.|a year|per year|annually|yearly|/yr|/year|apr|a yr|pro jahr|j[aä]hrlich|al a[nñ]o|"
               r"anual|par an|annuel)\b")
NUM_PCT = r"(\d[\d.,]*)\s*(?:%|per ?cent|percent|pct)"


def _pct_value(token, decimal):
    try:
        v, _ = ln.parse_percent(token, decimal)
    except (ln.Ambiguous, ln.Unreadable) as e:
        raise Need(f"late rate: {e}")
    return _to_decimal(v)


def parse_rate(x, decimal=None):
    """The founder's own contract late rate, as a simple yearly percentage. Returns (annual %, basis text)."""
    if x is None:
        return None
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        raise Need(f"late rate '{x}': is that once, a month or a year?")
    s = str(x).strip().lower()
    if s in {"", "none", "skip", "null", "?", "no"}:
        return None
    # A rate tied to a published rate is checked first, whatever else the clause says.
    if re.search(PUBLISHED_RATE, s) and re.search(r"\b(over|above|plus|on top of|\+|more than|margin)\b|\+", s):
        raise Need("your clause ties the rate to a published rate; what total yearly rate should I use? Ask your accountant or bank, "
                   "and I will mark it as founder supplied")
    m = re.search(NUM_PCT, s)
    if not m:
        if re.search(PUBLISHED_RATE, s):
            raise Need("your clause ties the rate to a published rate; what total yearly rate should I use? Ask your accountant or bank, "
                       "and I will mark it as founder supplied")
        raise Need(f"contract clause '{x}' names no rate I can use; paste the clause with its rate")
    v = _pct_value(m.group(1), decimal)
    rest = s[m.end():]
    hits = [(mm.start(), kind) for kind, pat in (("month", PERIOD_MONTH), ("day", PERIOD_DAY), ("year", PERIOD_YEAR))
            for mm in [re.search(pat, rest)] if mm]
    kind = min(hits)[1] if hits else None  # the period word nearest the rate decides
    if kind == "month":
        return v * 12, f"{pct_out(v)}% a month, worked out daily as {pct_out(v * 12)}% a year over 365 days"
    if kind == "day":
        return v * 365, f"{pct_out(v)}% a day"
    if kind == "year":
        return v, f"{pct_out(v)}% a year, worked out daily over 365 days"
    raise Need(f"late rate '{x}': is that once, a month or a year?")


def parse_fee(x, what="contract late fee", decimal=None, expect_cur=None):
    """A one-off late fee: a fixed amount, or a percentage of the invoice. Returns ('amount', D) or ('pct', D)."""
    if x is None:
        return None
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return ("amount", q(_to_decimal(x)))
    s = str(x).strip().lower()
    if s in {"", "none", "skip", "null", "?", "no", "-"}:
        return None
    if re.search(r"\b(a|per|each|every)\s*(month|week|day)\b|\bmonthly\b|\bweekly\b|\bdaily\b", s):
        raise Need(f"{what} '{x}' repeats; give it as a rate (for example 1.5% a month) or as a one-off fee")
    m = re.search(NUM_PCT, s)
    if m:
        return ("pct", _pct_value(m.group(1), decimal))
    v = parse_money(re.sub(r"\b(of the invoice|per invoice|once|one[- ]off)\b", " ", s), what, decimal, expect_cur)
    return ("amount", v) if v else None


def parse_bool(x, default=None):
    if isinstance(x, bool):
        return x
    if x is None:
        return default
    s = str(x).strip().lower()
    if s in {"yes", "y", "true", "1", "business", "company", "ltd", "llc", "inc", "pty", "b2b", "on"}:
        return True
    if s in {"no", "n", "false", "0", "consumer", "individual", "person", "private individual", "b2c", "off"}:
        return False
    return default


def norm_tier(x):
    s = str(x or "normal").strip().lower().rstrip(").")
    if re.search(r"persist|repeat|always|serial|chronic|habitual|every (single )?(time|month|invoice)|late every|never on time|bad payer|late payer|nightmare", s) or s in {"c", "3c"}:
        return "persistent"
    if re.search(r"valu|keep|key|vip|important|at all costs|best|favourite|favorite|biggest|main client|can'?t lose|cannot lose|don'?t want to (upset|lose)", s) or s in {"a", "3a"}:
        return "valued"
    return "normal"


def norm_action(x):
    s = str(x or "advice").strip().lower()
    for key, words in [("pause", ("pause", "stop work", "hold work", "stop", "suspend")),
                       ("collections", ("collection", "collect", "agency", "debt recovery")),
                       ("lawyer", ("lawyer", "solicitor", "attorney", "legal"))]:
        if any(w in s for w in words):
            return key
    return "advice"


def norm_every(x):
    s = str(x or "month").strip().lower()
    if "fortnight" in s or "two week" in s or "2 week" in s or "biweek" in s or "bi-week" in s:
        return "fortnight"
    if "week" in s:
        return "week"
    return "month"


def _day_index(word):
    k = str(word).strip().lower().rstrip(".")
    if k in WEEKDAYS:
        return WEEKDAYS[k]
    for name, i in WEEKDAYS.items():
        if len(k) >= 3 and name.startswith(k):
            return i
    raise Need(f"'{word}' is not a day of the week")


def parse_days_set(x, what="days off"):
    """A set of weekdays as founders type it: ['Sat', 'Sun'], 'Fri and Sat', 'Fri-Sat', 'sun to thu'."""
    if isinstance(x, list):
        x = ", ".join(str(i) for i in x)
    s = str(x).strip().lower()
    if s in {"none", "no", "nothing", "never", ""}:
        return []
    if re.search(r"\bweekdays?\b", s):
        return [0, 1, 2, 3, 4]
    if re.search(r"\bweekends?\b", s) and not re.search(r"(mon|tue|wed|thu|fri|sat|sun)", s):
        return [5, 6]
    out = set()

    def expand(m):
        a, b = _day_index(m.group(1)), _day_index(m.group(2))
        span = [(a + k) % 7 for k in range((b - a) % 7 + 1)]
        if len(span) != ln.count_weekdays(m.group(0)):
            raise Need(f"{what} '{x}': I could not read that range of days")
        out.update(span)
        return " "
    rest = re.sub(r"\b([a-z]{3,9})\.?\s*(?:-|to|through|thru|till|until)\s*([a-z]{3,9})\b\.?", expand, s)
    for w in re.findall(r"[a-z]+", rest):
        if w not in {"and", "off", "days", "day", "the", "every", "on"}:
            out.add(_day_index(w))
    return sorted(out)


def parse_weekend(x, work_days=None):
    """The founder's days off. 'work_days' (the days they do work) is turned round into days off."""
    if work_days not in (None, "", []):
        work = parse_days_set(work_days, "working days")
        off = sorted(set(range(7)) - set(work))
        if not work:
            raise Need("no working days given; say which days you work")
        return off
    if x is None:
        return [WEEKDAYS[d] for d in DEFAULT_WEEKEND]
    out = parse_days_set(x)
    if len(set(out)) >= 7:
        raise Need("every day is marked as a day off; say which days you do not work")
    return out


# ----------------------------------------------------------------------------- formatting

_STYLE = {"order": None, "us": False, "locale": "", "currency": None, "country": "", "paper": "A4",
          "dec": "dot", "after": False, "quantum": CENT}
CA_SPELLING = {"en-ca"}  # Canadian English: -ize verbs, 'instalment'


def set_style(locale, currency, country=None, order=None, dec=None, after=False):
    """Founder's English (spelling) from 'locale'; date order and paper from their country, never from spelling."""
    loc = str(locale or "").strip().lower().replace("_", "-")
    _STYLE["locale"] = loc
    _STYLE["us"] = loc in US_SPELLING
    _STYLE["ize"] = loc in US_SPELLING or loc in CA_SPELLING
    _STYLE["country"] = (country or "").upper()
    defaults = ln.locale_defaults(_STYLE["country"])
    _STYLE["paper"] = defaults["paper"]
    _STYLE["order"] = order or (None if defaults["assumed"] else defaults["date_order"])
    _STYLE["currency"] = (currency or "").upper() or None
    _STYLE["dec"] = dec or "dot"
    _STYLE["after"] = bool(after)
    _STYLE["quantum"] = Decimal(1) if _STYLE["currency"] in ZERO_DECIMAL else CENT


def num_out(v, places=2):
    """A number in the founder's own style: 1,200.50 or 1.200,50."""
    s = f"{Decimal(v):,.{places}f}"
    if _STYLE["dec"] == "comma":
        s = s.replace(",", "\u0001").replace(".", ",").replace("\u0001", ".")
    return s


def money(v, cur=None):
    cur = cur or _STYLE["currency"]
    places = 0 if cur in ZERO_DECIMAL else 2
    amt = num_out(q(v), places)
    if not cur:
        return amt
    if cur not in CURRENCIES:
        return f"{amt} {cur}" if _STYLE["after"] else f"{cur} {amt}"
    sym, homes, foreign = CURRENCIES[cur]
    mark = sym if (homes is None or _STYLE["locale"] in homes or _STYLE["country"].lower() in {h[-2:] for h in homes}) else foreign
    if _STYLE["after"]:
        return f"{amt} {mark.strip()}"
    return f"{mark}{amt}"


def long_date(d):
    if not d:
        return ""
    if _STYLE["order"] == "MDY":
        return f"{calendar.month_name[d.month]} {d.day}, {d.year}"
    return f"{d.day} {calendar.month_name[d.month]} {d.year}"


def iso_long(s):
    return long_date(date.fromisoformat(s)) if s else ""


def pct(v):
    return f"{Decimal(v).normalize():f}"


def pct_out(v):
    """A percentage in the founder's decimal style (1.5 or 1,5)."""
    s = pct(v)
    return s.replace(".", ",") if _STYLE["dec"] == "comma" else s


def word_instalment():
    return "installment" if _STYLE["us"] else "instalment"


def word_authorise():
    return "authorize" if _STYLE.get("ize") else "authorise"


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-") or "business"


# ----------------------------------------------------------------------------- calendar

class Cal:
    """The founder's working week and the holidays they gave. No country calendar is built in."""

    def __init__(self, weekend, holidays):
        self.weekend = set(weekend)
        self.holidays = set(holidays)

    def working(self, d):
        return d.weekday() not in self.weekend and d not in self.holidays

    def roll(self, d):
        for _ in range(60):
            if self.working(d):
                return d
            d += timedelta(days=1)
        return d


# ----------------------------------------------------------------------------- compute

def load_json(path):
    p = Path(path)
    if not p.exists():
        raise Stop(f"there is no file at {path}")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise Stop(f"{path} is not valid JSON ({e.msg} at line {e.lineno})")


def normalise(raw):
    """Accept the inputs as Claude is likely to write them; return clients with invoices nested."""
    if not isinstance(raw, dict):
        raise Stop("the inputs file must be one JSON object with a 'clients' list; run 'template' to see the shape")
    clients = raw.get("clients")
    flat = raw.get("invoices")
    if clients is None and flat is None:
        raise Stop("the inputs file has no 'clients' (or 'invoices') list; add the overdue invoices")
    if clients is not None and not isinstance(clients, list):
        raise Stop("'clients' must be a list of clients, each with an 'invoices' list")
    clients = [dict(c) for c in (clients or []) if isinstance(c, dict)]
    if flat:
        if not isinstance(flat, list):
            raise Stop("'invoices' must be a list")
        byname = {c.get("name"): c for c in clients}
        for inv in flat:
            if not isinstance(inv, dict):
                raise Stop("each invoice must be an object with at least a client, number and amount")
            name = inv.get("client") or "Client"
            if name not in byname:
                byname[name] = {"name": name, "invoices": []}
                clients.append(byname[name])
            byname[name].setdefault("invoices", []).append(inv)
    names = set()
    for c in clients:
        if not c.get("name"):
            raise Stop("a client has no name; every client needs one")
        if str(c["name"]).strip().lower() in names:
            raise Stop(f"the client '{c['name']}' appears twice; put all their invoices under one entry")
        names.add(str(c["name"]).strip().lower())
        invs = c.get("invoices") or []
        if not isinstance(invs, list):
            raise Stop(f"'invoices' for {c['name']} must be a list")
        c["invoices"] = [i for i in invs if isinstance(i, dict)]
    if not any(c["invoices"] for c in clients):
        raise Stop("there are no invoices to work on; add at least one with a client, amount and date")
    return clients


def resolve_country(raw, flags, needs):
    """The founder's country (ISO code). It sets date order and page size; spelling never does."""
    c = str(raw.get("country") or "").strip()
    if c:
        if re.fullmatch(r"[A-Za-z]{2}", c):
            return c.upper()
        needs.append(f"country '{c}': give the two-letter country code, such as US, NZ or DE")
        return ""
    loc = str(raw.get("locale") or "").strip().replace("_", "-")
    m = re.fullmatch(r"[A-Za-z]{2}-([A-Za-z]{2})", loc)
    if m:
        flags.append(f"Country taken as {m.group(1).upper()} from the language tag {loc}; it sets the date order and page size. "
                     "Say if you are based somewhere else.")
        return m.group(1).upper()
    return ""


def parse_count(x, what):
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return int(x)
    try:
        v, _ = ln.parse_number(str(x))
    except (ln.Ambiguous, ln.Unreadable):
        raise Stop(f"{what} '{x}' should be a whole number such as 3")
    if v != int(v):
        raise Stop(f"{what} '{x}' should be a whole number such as 3")
    return int(v)


def compute(raw, as_of_override=None):
    clients = normalise(raw)
    needs, flags, checks, defaults_used = [], [], [], []
    cur = (str(raw.get("currency") or "").strip().upper() or None)
    if cur and not re.fullmatch(r"[A-Z]{3}", cur):
        raise Stop(f"currency '{raw.get('currency')}' should be a three-letter code such as USD, AUD or GBP")
    country = resolve_country(raw, flags, needs)
    samples = typed_money(raw)
    dec = (str(raw.get("decimal_style") or "").strip().lower() or None)
    if dec not in (None, "dot", "comma"):
        raise Stop("decimal_style must be 'dot' (1,200.50) or 'comma' (1.200,50)")
    dec = dec or ln.detect_decimal_style(samples)
    after = parse_bool(raw.get("symbol_after"), default=None)
    if after is None:
        after = symbol_after(samples)
    if not cur:
        seen = {ln.find_currency(s) for s in samples} - {None}
        if len(seen) == 1 and re.fullmatch(r"[A-Z]{3}", next(iter(seen))):
            cur = next(iter(seen))
            flags.append(f"Currency read as {cur} from the symbol in your figures; say if that is wrong.")
    order_in = (str(raw.get("date_order") or "").upper() or None)
    if order_in not in {None, "DMY", "MDY", "YMD"}:
        raise Stop("date_order must be DMY, MDY or YMD")
    set_style(raw.get("locale"), cur, country, order_in, dec, after)
    order = _STYLE["order"]
    if not cur:
        needs.append("currency: which currency are these invoices in? Amounts are shown without a symbol until you say")
    if not country and not order_in:
        flags.append("I don't know which country you are in, so the page is A4 and any date that could be read two ways is asked about.")
    try:
        as_of = as_of_override or parse_date(raw.get("date") or date.today().isoformat(), date.today(), order, what="today's date")
    except Need as e:
        raise Stop(str(e))
    try:
        weekend = parse_weekend(raw.get("weekend"), raw.get("work_days"))
    except Need as e:
        raise Stop(str(e))
    if raw.get("weekend") is None and raw.get("work_days") in (None, "", []):
        defaults_used.append("weekend")
    hols = []
    for h in raw.get("holidays") or []:
        try:
            hd = parse_date(h, as_of, order, "near", "holiday")
        except Need as e:
            needs.append(str(e))
            continue
        if hd:
            hols.append(hd)
    cal = Cal(weekend, hols)
    try:
        default_terms = parse_terms(raw.get("default_terms"))
    except Need as e:
        needs.append(str(e))
        default_terms = None
    own = raw.get("own_late_terms") or {}
    if not isinstance(own, dict):
        own = {"has": True, "clause": own}
    own_has = parse_bool(own.get("has"), default=bool(own.get("rate") or own.get("fee") or own.get("clause")))
    own_rate, own_fee, rate_basis = None, None, ""
    grace = 0
    if own_has:
        try:
            pr = parse_rate(own.get("rate"), dec)
            if pr:
                own_rate, rate_basis = pr
        except Need as e:
            needs.append(str(e))
        try:
            own_fee = parse_fee(own.get("fee"), decimal=dec, expect_cur=cur)
        except Need as e:
            needs.append(str(e))
        try:
            grace = parse_days(own.get("grace_days"), "grace period", dec)
        except Need as e:
            needs.append(str(e))
        if own_rate is None and own_fee is None and not any("rate" in n or "fee" in n or "clause" in n for n in needs):
            needs.append("your contract sets a late fee or interest, but I could not find the figure; paste the clause")
        if own_rate is not None and own_rate > PLAUSIBLE_MAX_RATE:
            checks.append(("rate", f"your contract rate comes to {pct_out(own_rate)}% a year ({own.get('rate')}). Is that right, "
                                   "or is it a month or year rate typed as a day rate?"))
    plan_in = {k: v for k, v in (raw.get("plan") or {}).items() if v not in (None, "")}
    if "instalments" not in plan_in and "every" not in plan_in:
        defaults_used.append("plan")
    plan_cfg = dict(DEFAULT_PLAN)
    plan_cfg.update(plan_in)
    n_inst = parse_count(plan_cfg["instalments"], "plan instalments")
    if not 1 <= n_inst <= MAX_INSTALMENTS:
        raise Stop(f"a payment plan of {n_inst} {word_instalment()}s is outside 1 to {MAX_INSTALMENTS}")
    every = norm_every(plan_cfg.get("every"))
    try:
        min_plan = parse_money(plan_cfg.get("min_amount"), "smallest amount to offer a plan on", dec, cur)
    except Need as e:
        needs.append(str(e))
        min_plan = None
    ctx = {"as_of": as_of, "order": order, "default_terms": default_terms, "own_has": own_has, "own_rate": own_rate,
           "own_fee": own_fee, "grace": grace, "rate_basis": rate_basis, "dec": dec, "cur": cur, "checks": checks,
           "cal": cal, "n_inst": n_inst, "every": every, "needs": needs, "min_plan": min_plan,
           "gap_days": {}, "final_after": {}}
    out_invoices, out_clients = [], []

    for c in clients:
        name = str(c["name"]).strip()
        is_business = parse_bool(c.get("is_business"), default=True)
        tier = norm_tier(c.get("tier"))
        charge = parse_bool(c.get("charge_late_fee"), default=True)
        action = norm_action(c.get("final_action"))
        ongoing = parse_bool(c.get("ongoing_work"), default=None)
        for key, store in (("gap_days", "gap_days"), ("final_after_days", "final_after")):
            v = c.get(key) if c.get(key) not in (None, "") else raw.get(key)
            if v not in (None, ""):
                try:
                    n = parse_days(v, key.replace("_", " "), dec)
                except Need as e:
                    needs.append(f"{name}: {e}")
                    continue
                if n and 1 <= n <= 120:
                    ctx[store][name] = n
                else:
                    needs.append(f"{name}: {key.replace('_', ' ')} should be between 1 and 120 days")
        cinvs = []
        for inv in c["invoices"]:
            r = compute_invoice(inv, name, c.get("terms"), ctx)
            cinvs.append(r)
            out_invoices.append(r)
        if action == "pause" and ongoing is False:
            flags.append(f"{name}: you chose to stop work, but there is no work left to stop, so the final notice says you will take advice instead.")
            action = "advice"
        if not is_business and action in {"collections", "lawyer"}:
            flags.append(f"{name}: bought as a private individual. Chasing individuals has its own rules in many places, so the final notice says you will take advice; check the rules where you and they are before passing it on.")
            action = "advice"
        if action in {"collections", "lawyer"}:
            flags.append(f"{name}: the final notice names '{ACTIONS[action]}'. Only send it once you have spoken to one, know what it costs and will use them; they can tell you what fits where you and your client are.")
        cl = stage_for_client(c, name, cinvs, tier, is_business, charge, action, ongoing, ctx)
        final = next((p for p in ([cl["now"]] if cl["now"] else []) + cl["later"] if p["stage"] == 4), None)
        if tier == "valued" and ongoing and action in {"collections", "lawyer"} and final:
            flags.append(f"{name}: you want to keep them and work is still going on, yet the final notice on {iso_long(final['send'])} "
                         f"says you will {ACTIONS[action]}. Confirm that is what you want before it goes; if not, choose take advice or stop work.")
        if cl.get("paid_since"):
            flags.append(f"{name}: {cl['paid_since']} came in after your last message. If they are paying in parts, agree a plan for the rest before sending the next message.")
        if cl.get("paid_late_fee"):
            flags.append(f"{name}: paid late. Your contract terms would add {money(cl['paid_late_fee'])}; whether to ask for it is your call. Many founders let it go with a good client.")
        out_clients.append(cl)

    for r in out_invoices:
        needs.extend(f"{r['client']}, {r['number']}: {n}" for n in r["needs"])
        flags.extend(f"{r['client']}, {r['number']}: {f}" for f in r["flags"])
    if any(r.get("assumed_terms") and r["status"] in {"late", "not_due", "disputed"} for r in out_invoices):
        flags.append(f"Invoices with no due date or terms are counted as due {DEFAULT_TERMS_DAYS} days after the invoice date, a working assumption; give the real terms if you agreed different ones.")

    waived = {cl["name"] for cl in out_clients if not cl["charge_late_fee"]}
    for r in out_invoices:
        r["waived"] = r["client"] in waived and r["fee_applies"]
    late_rows = [r for r in out_invoices if r["status"] == "late"]
    owed = sum((Decimal(r["outstanding"]) for r in late_rows), Decimal(0))
    addon = sum((Decimal(r["interest"]) + Decimal(r["fee"]) for r in late_rows if r["fee_applies"] and not r["waived"]), Decimal(0))
    daily = sum((Decimal(r["daily"]) for r in late_rows if r["fee_applies"] and not r["waived"]), Decimal(0))
    disputed_whole = sum((Decimal(r["outstanding"]) for r in out_invoices if r["status"] == "disputed"), Decimal(0))
    disputed_part = sum((Decimal(r["disputed_part"]) for r in out_invoices if r["status"] == "late"), Decimal(0))
    totals = {
        "owed": str(q(owed)), "addon": str(q(addon)), "with_fees": str(q(owed + addon)), "daily": str(q(daily)),
        "disputed": str(q(disputed_whole + disputed_part)), "all_open": str(q(owed + disputed_whole + disputed_part)),
        "late_invoices": len(late_rows),
        "clients_late": len({r["client"] for r in late_rows}),
        "waived_clients": sorted({r["client"] for r in late_rows if r.get("waived")}),
    }
    if raw.get("report_total") not in (None, ""):
        try:
            rep = parse_money(raw.get("report_total"), "total on your report", dec, cur)
        except Need as e:
            needs.append(str(e))
            rep = None
        if rep is not None:
            open_sum = q(sum((Decimal(r["outstanding"]) + Decimal(r["disputed_part"]) for r in out_invoices
                              if r["status"] in {"late", "not_due", "disputed"}), Decimal(0)))
            totals["report_total"] = str(q(rep))
            totals["report_matches"] = open_sum == q(rep)
            if open_sum != q(rep):
                flags.append(f"Your report's total is {money(rep)}, but the open invoices here add up to {money(open_sum)}. "
                             "Check for a missing, paid or doubled invoice before anything goes out.")
    order_rows = sorted([cl for cl in out_clients if cl["invoices"] or cl["disputed"]],
                        key=lambda cl: (0 if cl["now"] or (cl["disputed"] and not cl["invoices"]) else 1, -Decimal(cl["owed"]), -cl["days_late"]))
    prev_in = raw.get("prevention") or {}
    for k in ("deposit_pct", "milestones", "card_on_file"):
        if prev_in.get(k) in (None, ""):
            defaults_used.append(k)
    if raw.get("bank_line") is None:
        defaults_used.append("bank_line")
    if not raw.get("default_terms"):
        defaults_used.append("default_terms")
    prevention = prevention_figures(raw, out_invoices, dec, cur, checks)
    confirmed = {str(k).strip().lower() for k in (raw.get("confirmed") or [])}
    open_checks = [(k, msg) for k, msg in checks if k.lower() not in confirmed]
    if open_checks:
        lines = "; ".join(f"({i + 1}) {msg} [if it is right, add \"{k}\" to confirmed]" for i, (k, msg) in enumerate(open_checks))
        raise Stop(f"please check {'this figure' if len(open_checks) == 1 else 'these figures'} with the founder before I build: {lines}")
    if not hols:
        upcoming = sorted({d for cl in out_clients for p in ([cl["now"]] if cl["now"] else []) + cl["later"]
                           for d in [p["send"], p["pay_by"]] + [x for x, _ in (p.get("plan") or [])]
                           if d and as_of < date.fromisoformat(d) <= as_of + timedelta(days=HOLIDAY_WINDOW_DAYS)})
        if upcoming:
            flags.append("I have not allowed for public holidays: you gave none. Dates in this plan over the next 8 weeks: "
                         + date_list(upcoming) + ". If any is a holiday or a day off for you, tell me and I'll move it.")
    results = {
        "skill": SKILL, "as_of": as_of.isoformat(), "currency": cur, "locale": raw.get("locale") or "",
        "country": country, "paper": _STYLE["paper"], "decimal_style": dec or "", "symbol_after": bool(after),
        "date_order": order, "business": raw.get("business") or "", "founder_name": raw.get("founder_name") or "",
        "greeting": str(raw.get("greeting") or "").strip().rstrip(","),
        "weekend": [calendar.day_name[d] for d in weekend], "holidays": [h.isoformat() for h in hols],
        "own_terms": {"has": bool(own_has), "annual_rate": own_rate and str(own_rate), "rate_basis": rate_basis,
                      "fee": own_fee and [own_fee[0], str(own_fee[1])], "grace_days": grace,
                      "clause": own.get("clause") or "", "rate_typed": own.get("rate") or "", "fee_typed": own.get("fee") or ""},
        "default_terms": default_terms and terms_text(default_terms),
        "plan": {"instalments": n_inst, "every": every, "min_amount": min_plan and str(min_plan)},
        "bank_line": parse_bool(raw.get("bank_line"), default=True),
        "invoices": out_invoices, "clients": out_clients, "chase_order": [cl["name"] for cl in order_rows],
        "totals": totals, "prevention": prevention, "needs": needs, "flags": flags, "defaults_used": defaults_used,
        "confirmed": sorted(confirmed), "inputs": raw,
    }
    results["headline"] = headline(results)
    return results


def compute_invoice(inv, client, client_terms, ctx):
    as_of, order, dec, cur = ctx["as_of"], ctx["order"], ctx["dec"], ctx["cur"]
    r = {"client": client, "number": str(inv.get("number") or inv.get("invoice") or inv.get("ref") or "").strip(),
         "needs": [], "flags": [], "status": "need", "fee_applies": False, "amount": None, "outstanding": "0",
         "interest": "0", "fee": "0", "daily": "0", "days_late": 0, "annual_rate": None, "rate_basis": ctx["rate_basis"],
         "due_date": None, "due_basis": "", "invoice_date": None, "fee_from": None, "payments": [],
         "total": "0", "assumed_terms": False, "disputed": False, "part_disputed": False, "disputed_part": "0",
         "total_shown": None}
    if not r["number"]:
        r["number"] = "invoice"
        r["needs"].append("no invoice number; add it so the client can match the payment")
    try:
        amount = parse_money(inv.get("amount"), "amount", dec, cur)
    except Need as e:
        r["needs"].append(str(e))
        amount = None
    if amount is None or amount == 0:
        if not any("amount" in n for n in r["needs"]):
            r["needs"].append("no amount; give the total on the invoice")
        return r
    r["amount"] = str(amount)
    if amount < 1:
        ctx["checks"].append((f"amount:{r['number']}", f"{client}, invoice {r['number']}: the amount reads as {money(amount)}, under one unit of currency. "
                                                       "Is that right, or was a decimal point or comma misplaced?"))
    try:
        inv_date = parse_date(inv.get("invoice_date") or inv.get("date"), as_of, order, "past", "invoice date")
        due_given = parse_date(inv.get("due_date") or inv.get("due"), as_of, order, "near", "due date")
        terms = parse_terms(inv.get("terms") or client_terms) or ctx["default_terms"]
    except Need as e:
        r["needs"].append(str(e))
        return r
    if inv_date and inv_date > as_of:
        r["needs"].append(f"the invoice date {long_date(inv_date)} is after today; check it")
        return r
    if inv_date and (as_of - inv_date).days > PLAUSIBLE_MAX_AGE_DAYS:
        ctx["checks"].append((f"date:{r['number']}", f"{client}, invoice {r['number']}: dated {long_date(inv_date)}, over three years ago. Is the year right?"))
    r["invoice_date"] = inv_date and inv_date.isoformat()
    if due_given:
        due = due_given
        r["due_basis"] = "the due date on the invoice"
    elif terms and inv_date:
        due = apply_terms(terms, inv_date)
        r["due_basis"] = f"your terms ({terms_text(terms)}) from the invoice date, {long_date(inv_date)}"
    elif inv_date:
        due = inv_date + timedelta(days=DEFAULT_TERMS_DAYS)
        r["due_basis"] = f"no due date or terms given, so {DEFAULT_TERMS_DAYS} days from the invoice date (a working assumption)"
        r["assumed_terms"] = True
    else:
        r["needs"].append("no invoice date or due date; give either")
        return r
    if inv_date and due < inv_date:
        r["needs"].append(f"the due date {long_date(due)} is before the invoice date; check it")
        return r
    r["due_date"] = due.isoformat()
    try:
        shown = parse_money(inv.get("total_shown"), "total shown on the invoice", dec, cur)
    except Need as e:
        r["needs"].append(str(e))
        shown = None
    if shown is not None and shown != amount:
        r["total_shown"] = str(shown)
        r["flags"].append(f"the invoice the client has shows {money(shown)}; the first message says the right total is {money(amount)} "
                          "and that a corrected invoice is attached. Send the corrected invoice with it")
    items = inv.get("line_items") or []
    if items:
        try:
            vals = [parse_money(x, "line on the invoice", dec, cur) for x in items]
        except Need as e:
            r["needs"].append(str(e))
            vals = []
        if vals and all(v is not None for v in vals):
            lines_sum = q(sum(vals, Decimal(0)))
            r["items_total"] = str(lines_sum)
            if lines_sum != q(amount):
                if shown is not None and lines_sum == q(shown):
                    r["flags"].append(f"the lines on the invoice add up to {money(lines_sum)}, the total the client has, not the {money(amount)} "
                                      "you gave. Check which is right before anything goes out")
                else:
                    r["flags"].append(f"the lines on the invoice add up to {money(lines_sum)}, not {money(amount)}. "
                                      "Check which is right before anything goes out")
            elif shown is not None and shown != amount:
                r["flags"].append(f"the lines on the invoice add up to {money(lines_sum)}, so the {money(shown)} total line looks like the typo")

    payments = []
    for p in inv.get("payments") or []:
        try:
            pd = parse_date(p.get("date"), as_of, order, "past", "payment date")
            pa = parse_money(p.get("amount"), "payment", dec, cur)
        except (Need, AttributeError) as e:
            r["needs"].append(str(e) if isinstance(e, Need) else "a part payment needs a date and an amount")
            return r
        if pd is None or pa is None:
            r["needs"].append("a part payment needs a date and an amount")
            return r
        payments.append((pd, pa))
    try:
        paid_full = parse_date(inv.get("paid_in_full_on") or inv.get("paid_on"), as_of, order, "past", "date paid")
    except Need as e:
        r["needs"].append(str(e))
        return r
    payments.sort()
    paid_sum = sum((a for _, a in payments), Decimal(0))
    if paid_full:
        payments.append((paid_full, amount - paid_sum))
        paid_sum = amount
    if paid_sum > amount:
        r["needs"].append(f"payments of {money(paid_sum)} are above the invoice total of {money(amount)}; check them")
        return r
    r["payments"] = [[d.isoformat(), str(a)] for d, a in payments]
    outstanding = amount - paid_sum
    r["outstanding"] = str(q(outstanding))
    days_late = (as_of - due).days
    r["days_late"] = days_late

    flag_disputed = bool(parse_bool(inv.get("disputed"), default=False))
    try:
        d_amt = parse_money(inv.get("disputed_amount"), "disputed amount", dec, cur)
    except Need as e:
        r["needs"].append(str(e))
        return r
    if d_amt and outstanding > 0:
        if d_amt > outstanding:
            r["needs"].append(f"the disputed part, {money(d_amt)}, is more than the {money(outstanding)} still unpaid; check it")
            return r
        if d_amt < outstanding:
            flag_disputed = False  # only part is disputed: the rest is chased
            r["part_disputed"] = True
            r["disputed_part"] = str(q(d_amt))
            outstanding -= d_amt
            r["outstanding"] = str(q(outstanding))
            r["flags"].append(f"{money(d_amt)} of it is disputed. The other {money(outstanding)} is chased as normal; the first message offers "
                              "to settle the disputed part separately, and nothing is added to that part")
        else:
            flag_disputed = True
    elif flag_disputed and outstanding > 0:
        r["flags"].append("treated as disputed in full. If only part is disputed, give that part and I'll chase the rest")
    if flag_disputed and outstanding > 0:
        r["status"] = "disputed"
        r["disputed"] = True
        r["flags"].append("disputed: nothing escalates and no late fee is added until it is settled; the plan has one message asking to settle it")
        return r
    if outstanding == 0 and not any(d > due for d, _ in payments):
        r["status"] = "paid"
        return r
    if days_late <= 0 and outstanding > 0:
        r["status"] = "not_due"
        return r
    r["status"] = "late" if outstanding > 0 else "paid_late"
    if days_late > OLD_DEBT_DAYS:
        r["flags"].append("over a year late. Talk to a lawyer before chasing a debt this old; older debts can be harder to recover formally")
    own_rate, own_fee, grace = ctx["own_rate"], ctx["own_fee"], ctx["grace"]
    if not ctx["own_has"] or (own_rate is None and own_fee is None):
        return finish(r, outstanding, Decimal(0), Decimal(0), Decimal(0))

    # The founder's own contract terms: plain arithmetic on the figures they gave, never on a disputed part.
    base = amount - Decimal(r["disputed_part"])
    start = due + timedelta(days=grace + 1)
    r["fee_from"] = start.isoformat()
    if as_of < start:
        r["flags"].append(f"inside the {grace} day grace period in your terms; the late fee starts on {long_date(start)}")
        r["fee_applies"] = False
        return finish(r, outstanding, Decimal(0), Decimal(0), Decimal(0))
    interest = Decimal(0)
    daily = Decimal(0)
    if own_rate is not None:
        r["annual_rate"] = str(own_rate)
        for seg_principal, seg_from, seg_to in segments(base, payments, start, as_of):
            days = (seg_to - seg_from).days + 1
            if days > 0:
                interest += seg_principal * own_rate / Decimal(100) / Decimal(365) * days
        daily = outstanding * own_rate / Decimal(100) / Decimal(365)
    fee = Decimal(0)
    if own_fee:
        fee = own_fee[1] if own_fee[0] == "amount" else q(base * own_fee[1] / Decimal(100))
        if fee > base:
            ctx["checks"].append((f"fee:{r['number']}", f"{client}, invoice {r['number']}: your late fee of {money(fee)} is more than the invoice itself "
                                                        f"({money(base)}). Is the fee right?"))
    r["fee_applies"] = True
    return finish(r, outstanding, interest, fee, daily)


def segments(amount, payments, start, end):
    """Principal outstanding over each stretch of days, payments reducing it from the day after."""
    principal = amount
    cur_from = start
    for pd, pa in payments:
        if pd < start:
            principal -= pa
            continue
        if pd > end:
            break
        yield principal, cur_from, pd
        principal -= pa
        cur_from = pd + timedelta(days=1)
    if principal > 0 and cur_from <= end:
        yield principal, cur_from, end


def finish(r, outstanding, interest, fee, daily):
    r["interest"] = str(q(interest))
    r["interest_exact"] = str(interest)
    r["fee"] = str(q(fee))
    r["daily"] = str(q(daily)) if outstanding > 0 else "0.00"
    r["daily_exact"] = str(daily) if outstanding > 0 else "0"
    r["total"] = str(q(outstanding + q(interest) + q(fee))) if r["fee_applies"] else str(q(outstanding))
    return r


def fees_at(r, d):
    """Interest and fee on an invoice as at a later date, same rules. Returns (interest, fee)."""
    if r["status"] != "late" or not r["fee_applies"]:
        return Decimal(0), Decimal(0)
    extra_days = (d - date.fromisoformat(r["_as_of"])).days
    interest = q(Decimal(r.get("interest_exact", r["interest"])) + Decimal(r["daily_exact"]) * extra_days)
    return interest, Decimal(r["fee"])


# ----------------------------------------------------------------------------- payment plan

def plan_schedule(total, n, first, every, cal):
    """Instalments rounded to the cent (or whole unit), the last one taking the difference; dates kept to working days."""
    total = q(total)
    unit = _STYLE.get("quantum") or CENT
    n = max(1, min(n, MAX_INSTALMENTS))
    while n > 1 and total / n < 1:
        n -= 1
    each = q(total / n)
    if each * (n - 1) >= total:  # never leave the last one empty or negative
        each = (total / n).quantize(unit, rounding="ROUND_DOWN")
    amounts = [each] * (n - 1) + [total - each * (n - 1)]
    dates = []
    for i in range(n):
        if every == "week":
            d = first + timedelta(days=7 * i)
        elif every == "fortnight":
            d = first + timedelta(days=14 * i)
        else:
            d = add_months(first, i)
        d = cal.roll(d)
        if dates and d <= dates[-1]:
            d = cal.roll(dates[-1] + timedelta(days=1))
        dates.append(d)
    return [[d.isoformat(), str(a)] for d, a in zip(dates, amounts)]


# ----------------------------------------------------------------------------- stages

def stage_for_client(c, name, cinvs, tier, is_business, charge, action, ongoing, ctx):
    as_of, order, cal, needs = ctx["as_of"], ctx["order"], ctx["cal"], ctx["needs"]
    late = [r for r in cinvs if r["status"] == "late"]
    disputed = [r for r in cinvs if r["status"] == "disputed"]
    sent, dispute_sent = [], []
    for s in c.get("stages_sent") or []:
        try:
            st = int(str(s.get("stage")).strip()[0]) if isinstance(s, dict) else None
            sd = parse_date(s.get("date"), as_of, order, "past", "date a message was sent") if isinstance(s, dict) else None
        except (Need, ValueError, TypeError, IndexError):
            st, sd = None, None
        if st == 0 and sd:
            dispute_sent.append(sd)
        elif st and 1 <= st <= 4 and sd:
            sent.append((st, sd))
        else:
            needs.append(f"{name}: a message already sent needs a stage (1 to 4, or 0 for a dispute message) and a date")
    sent.sort(key=lambda x: (x[1], x[0]))
    last_stage = max((s for s, _ in sent), default=0)
    last_date = max((d for s, d in sent if s == last_stage), default=None)
    first_sent = min((d for _, d in sent), default=None)
    owed = sum((Decimal(r["outstanding"]) for r in late), Decimal(0))
    cl = {"name": name, "tier": tier, "is_business": is_business, "charge_late_fee": charge,
          "final_action": action, "ongoing_work": ongoing, "contact": c.get("contact") or "",
          "to": c.get("to") or c.get("email") or "", "terms": c.get("terms") or "",
          "stages_sent": [[s, d.isoformat()] for s, d in sent], "dispute_sent": [d.isoformat() for d in sorted(dispute_sent)],
          "invoices": [r["number"] for r in late], "part_disputed": [r["number"] for r in late if r["part_disputed"]],
          "disputed": [r["number"] for r in disputed], "now": None, "later": [], "status": "",
          "owed": str(q(owed)), "days_late": max((r["days_late"] for r in late + disputed), default=0),
          "paid_late": [r["number"] for r in cinvs if r["status"] == "paid_late"], "ladder": [],
          "approval": str(c.get("approval") or "").strip().strip('"“”').strip(),
          "approval_date": "", "held_until_paid": str(c.get("held_until_paid") or "").strip().rstrip(".")}
    if c.get("approval_date"):
        try:
            ad = parse_date(c.get("approval_date"), as_of, order, "past", "date the client approved the work")
            cl["approval_date"] = ad.isoformat() if ad else ""
        except Need:
            needs.append(f"{name}: the date they approved the work ('{c.get('approval_date')}') should be a date; leave it out if unsure")
    for r in cinvs:
        r["_as_of"] = as_of.isoformat()
    if last_date and late:
        since = sum((Decimal(a) for r in late for d, a in r["payments"] if date.fromisoformat(d) > last_date), Decimal(0))
        if since > 0:
            cl["paid_since"] = money(since)
    if not late:
        cl["status"] = "settle the dispute" if disputed else ("paid late" if cl["paid_late"] else "nothing late")
        pl = [r for r in cinvs if r["status"] == "paid_late" and r["fee_applies"]]
        if pl and charge:
            cl["paid_late_fee"] = str(q(sum((Decimal(r["interest"]) + Decimal(r["fee"]) for r in pl), Decimal(0))))
        return cl
    oldest = max(late, key=lambda r: r["days_late"])
    days = oldest["days_late"]
    due_oldest = date.fromisoformat(oldest["due_date"])
    thresholds = STAGE_DAYS[tier]
    min_gap = ctx["gap_days"].get(name) or MIN_GAP[tier]
    to_final = ctx["final_after"].get(name) or MIN_TO_FINAL[tier]
    before_final = max(min_gap, MIN_GAP_BEFORE_FINAL)
    if last_stage >= 4:
        cl["status"] = f"final notice already sent; next is the step it named: {ACTIONS[action]}"
        cl["ladder"] = ladder(cl, [], last_date)
        return cl
    if last_stage == 0:
        by_days = max([i + 1 for i, t in enumerate(thresholds) if days >= t] or [1])
        nxt = min(by_days, FIRST_CONTACT_MAX[tier])
        if tier == "persistent":
            nxt = max(nxt, 2)
        if parse_bool(c.get("asked_for_plan"), default=False):
            nxt = max(nxt, 3)  # they asked to pay in parts: the first reply is the plan, not a reminder
        earliest = as_of
    else:
        nxt = last_stage + 1
        earliest = max(last_date + timedelta(days=max(gap_after(last_stage), before_final if nxt == 4 else min_gap)),
                       due_oldest + timedelta(days=thresholds[nxt - 1]))
        if nxt == 4:
            earliest = max(earliest, first_sent + timedelta(days=to_final))
    plan = []
    for st in range(nxt, 5):
        if plan:
            prev = plan[-1]
            after_prev = (prev["pay_by_d"] + timedelta(days=1)) if prev["pay_by_d"] else prev["send"] + timedelta(days=GAP_DAYS)
            after_prev = max(after_prev, prev["send"] + timedelta(days=before_final if st == 4 else min_gap))
            send = max(after_prev, due_oldest + timedelta(days=thresholds[st - 1]))
            if st == 4:
                send = max(send, (first_sent or plan[0]["send"]) + timedelta(days=to_final))
        else:
            send = max(earliest, as_of)
        if send > as_of:
            send = cal.roll(send)
        pay_by_d = cal.roll(send + timedelta(days=PAY_WITHIN_DAYS)) if st >= 2 else None
        plan.append({"stage": st, "send": send, "pay_by_d": pay_by_d})
    sent_dates = [d for _, d in sent]
    for i, p in enumerate(plan):
        p.pop("pay_by_d")
        p.update(stage_figures(cl, late, p["stage"], p["send"], tier, charge, sent_dates + [x["send"] for x in plan[:i]], ctx))
        p["bank_line"] = i == 0 or p["stage"] == 4   # the first message this plan writes, and the final notice
        p["first"] = i == 0
        p["fresh"] = i == 0 and last_stage == 0  # nothing sent before: the wrong total on their copy is corrected here
    cl["now"] = plan[0] if plan[0]["send"] <= as_of else None
    cl["later"] = plan[1:] if cl["now"] else plan
    cl["status"] = f"send the {kind_name(plan[0])} now" if cl["now"] else f"wait: next message on {long_date(plan[0]['send'])}"
    final_pay_by = next((date.fromisoformat(p["pay_by"]) for p in plan if p["stage"] == 4), None)
    for p in plan:
        p["send"] = p["send"].isoformat()
    cl["ladder"] = ladder(cl, plan, final_pay_by)
    return cl


def gap_after(stage):
    """Days to wait after a stage before the next: a week after a reminder, and past the pay-by date after the rest."""
    return GAP_DAYS if stage <= 1 else PAY_WITHIN_DAYS + 1


def kind_name(p):
    if p["kind"] in {"plan", "call_plan"} and not p.get("plan"):
        return "call offer"
    return KIND_NAMES[p["kind"]]


def stage_figures(cl, late, stage, send, tier, charge, sent_dates, ctx):
    cal = ctx["cal"]
    pay_by = cal.roll(send + timedelta(days=PAY_WITHIN_DAYS)) if stage >= 2 else None
    fees = all(r["fee_applies"] for r in late) and charge
    owed = sum((Decimal(r["outstanding"]) for r in late), Decimal(0))
    interest = Decimal(0)
    fee = Decimal(0)
    for r in late:
        i, f = fees_at(r, send)
        interest += i
        fee += f
    daily = sum((Decimal(r["daily"]) for r in late), Decimal(0)) if fees else Decimal(0)
    if not fees:
        interest, fee = Decimal(0), Decimal(0)
    total = owed + interest + fee
    if stage == 1:
        kind = "reminder"
    elif stage == 2:
        kind = "firm"
    elif stage == 3:
        if tier == "valued":
            kind = "call_plan"
        elif fees:
            kind = "late_fee"
        else:
            kind = "plan"
    else:
        kind = "final" if fees else "final_nofee"
    out = {"kind": kind, "pay_by": pay_by and pay_by.isoformat(), "owed": str(q(owed)), "interest": str(q(interest)),
           "fee": str(q(fee)), "total": str(q(total)), "daily": str(q(daily)), "fees": fees,
           "days_late": (send - min(date.fromisoformat(r["due_date"]) for r in late)).days,
           "terms_named": fees and tier != "valued" and kind == "firm",
           "sent_before": [d.isoformat() for d in sorted(sent_dates)], "plan": None}
    if kind in {"plan", "call_plan", "late_fee"}:
        plan_total = total if kind == "late_fee" else owed
        if not (ctx["min_plan"] and plan_total < ctx["min_plan"]):
            out["plan"] = plan_schedule(plan_total, ctx["n_inst"], pay_by, ctx["every"], cal)
        out["plan_total"] = str(q(plan_total))
    return out


def rung_label(st, p=None):
    if not p:
        return STAGE_NAMES[st]
    return {"reminder": "Reminder", "firm": "Firm reminder", "late_fee": "Late fee notice and payment plan",
            "final": "Final notice", "final_nofee": "Final notice"}.get(p["kind"]) or (
        "Call and payment plan" if p.get("plan") else "Call")


def ladder(cl, plan, final_pay_by):
    """The escalation ladder for one client: the dated messages, then the founder's own decisions."""
    rungs = []
    sent = {s: d for s, d in cl["stages_sent"]}
    for st in range(1, 5):
        p = next((x for x in plan if x["stage"] == st), None)
        if p:
            when = "today" if cl["now"] is p else (p["send"] if isinstance(p["send"], str) else p["send"].isoformat())
            rungs.append({"rung": rung_label(st, p), "when": when, "state": "planned", "kind": p["kind"]})
        elif st in sent:
            rungs.append({"rung": STAGE_NAMES[st], "when": sent[st], "state": "sent", "kind": ""})
        else:
            rungs.append({"rung": STAGE_NAMES[st], "when": "", "state": "skipped", "kind": ""})
    after = final_pay_by.isoformat() if final_pay_by else ""
    if cl["ongoing_work"] is not False:
        rungs.append({"rung": "Stop work", "when": after, "state": "chosen" if cl["final_action"] == "pause" else "option",
                      "kind": "decision"})
    if cl["is_business"]:
        rungs.append({"rung": "Hand to a collections service or lawyer", "when": after,
                      "state": "chosen" if cl["final_action"] in {"collections", "lawyer"} else "option", "kind": "decision"})
    else:
        rungs.append({"rung": "Take advice on recovering it", "when": after,
                      "state": "chosen" if cl["final_action"] == "advice" else "option", "kind": "decision"})
    return rungs


def headline(res):
    t = res["totals"]
    need_invs = [r for r in res["invoices"] if r["status"] == "need"]
    need_txt = ""
    if need_invs:
        bits = [f"{r['number']} ({money(r['amount'])})" if r.get("amount") else r["number"] for r in need_invs]
        need_txt = (f"Plus {len(need_invs)} invoice{'s' if len(need_invs) != 1 else ''} I can't place yet: " + ", ".join(bits) + ".")
    disputed_whole = [r for r in res["invoices"] if r["status"] == "disputed"]
    parts_d = [r for r in res["invoices"] if r["status"] == "late" and r["part_disputed"]]
    dbits = [f"{money(r['outstanding'])} on invoice {r['number']}" for r in disputed_whole] + \
            [f"{money(r['disputed_part'])} of invoice {r['number']}" for r in parts_d]
    dline = ""
    if dbits:
        dline = (f"{' and '.join(dbits)} {'is' if len(dbits) == 1 else 'are'} disputed and wait{'s' if len(dbits) == 1 else ''} "
                 f"until settled, so {money(t['all_open'])} is open in all.")
    if t["late_invoices"] == 0:
        return " ".join(x for x in [dline or "Nothing here is overdue yet.", need_txt] if x)
    parts = [f"You are owed {money(t['owed'])} on {t['late_invoices']} late invoice{'s' if t['late_invoices'] != 1 else ''} "
             f"from {t['clients_late']} client{'s' if t['clients_late'] != 1 else ''}."]
    first = next((cl for cl in res["clients"] if cl["name"] == (res["chase_order"] or [None])[0]), None)
    if first and first["invoices"]:
        if t["clients_late"] == 1 and len(res["chase_order"]) == 1:
            parts.append(f"{first['name']}: {money(first['owed'])}, {first['days_late']} days late.")
        else:
            parts.append(f"Chase {first['name']} first: {money(first['owed'])}, {first['days_late']} days late.")
    if Decimal(t["addon"]) > 0:
        parts.append(f"Your own contract terms add {money(t['addon'])} so far, {money(t['with_fees'])} in all"
                     + (f", and {money(t['daily'])} a day while it stays unpaid." if Decimal(t["daily"]) > 0 else "."))
        if t.get("waived_clients"):
            parts.append(f"That leaves out {' and '.join(t['waived_clients'])}, who you chose not to charge.")
    if dline:
        parts.append(dline)
    if need_txt:
        parts.append(need_txt)
    return " ".join(parts)


# ----------------------------------------------------------------------------- prevention terms

def prevention_figures(raw, invoices, dec=None, cur=None, checks=None):
    cfg = dict(DEFAULT_PREVENTION)
    cfg.update({k: v for k, v in (raw.get("prevention") or {}).items() if v not in (None, "")})
    out = {"deposit_pct": None, "milestones": None, "card_on_file": parse_bool(cfg.get("card_on_file"), default=True),
           "late_fee": cfg.get("late_fee") or "", "example_price": None, "example_source": "",
           "deposit_example": None, "milestone_example": None, "needs": []}
    try:
        dp = _to_decimal(ln.parse_percent(str(cfg["deposit_pct"]), dec)[0])
        if not 0 < dp < 100:
            raise ValueError
        out["deposit_pct"] = pct(dp)
    except Exception:  # noqa: BLE001
        out["needs"].append(f"deposit '{cfg['deposit_pct']}' should be a percentage between 0 and 100")
    try:
        sep = r"[/+;\s]+" if dec == "comma" or "/" in str(cfg["milestones"]) else r"[/,+;\s]+"
        parts = [_to_decimal(ln.parse_percent(x.strip(), dec)[0]) for x in re.split(sep, str(cfg["milestones"])) if x.strip().rstrip("%")]
        if len(parts) < 2 or sum(parts) != 100 or any(p <= 0 for p in parts):
            raise ValueError
        out["milestones"] = [pct(p) for p in parts]
    except Exception:  # noqa: BLE001
        out["needs"].append(f"milestones '{cfg['milestones']}' should be shares that add up to 100, such as 40/30/30")
    price = None
    try:
        price = parse_money(cfg.get("typical_price"), "typical price", dec, cur, allow_approx=True)
    except Need as e:
        out["needs"].append(str(e))
    if price is not None and price < 1 and checks is not None:
        checks.append(("typical_price", f"your typical price reads as {money(price)}, under one unit of currency. Is that right?"))
    if price:
        out["example_source"] = "your typical price"
    else:
        amts = sorted(Decimal(r["amount"]) for r in invoices if r.get("amount"))
        if amts:
            price = amts[len(amts) // 2]
            out["example_source"] = "a middle-sized invoice from this list"
    if price:
        out["example_price"] = str(price)
        if out["deposit_pct"]:
            d = q(price * Decimal(out["deposit_pct"]) / 100)
            out["deposit_example"] = [str(d), str(q(price - d))]
        if out["milestones"]:
            amts = [q(price * Decimal(p) / 100) for p in out["milestones"]]
            amts[-1] = q(price - sum(amts[:-1]))
            out["milestone_example"] = [str(a) for a in amts]
    return out


# ----------------------------------------------------------------------------- drafts

def first_name(cl):
    c = (cl.get("contact") or "").strip()
    if not c:
        return ""
    bits = c.split()
    if bits[0].rstrip(".").lower() in {"mr", "mrs", "ms", "miss", "dr", "mx"}:
        return c
    return bits[0]


def inv_list(nums):
    if len(nums) == 1:
        return f"invoice {nums[0]}"
    return "invoices " + ", ".join(nums[:-1]) + f" and {nums[-1]}"


def cap(s):
    return s[:1].upper() + s[1:]


def date_list(isos):
    ds = [date.fromisoformat(x) if isinstance(x, str) else x for x in isos]
    if not ds:
        return ""
    if _STYLE["order"] == "MDY":
        txt = [f"{calendar.month_name[d.month]} {d.day}" + ("" if d.year == ds[-1].year else f", {d.year}") for d in ds]
    else:
        txt = [f"{d.day} {calendar.month_name[d.month]}" + ("" if d.year == ds[-1].year else f" {d.year}") for d in ds]
    txt[-1] = long_date(ds[-1])
    return txt[0] if len(txt) == 1 else ", ".join(txt[:-1]) + " and " + txt[-1]


def plan_lines(sched):
    w = word_instalment()
    return [f"{cap(w)} {i + 1}: {money(a)} by {iso_long(d)}" for i, (d, a) in enumerate(sched)]


def fee_words(res, p):
    own = res["own_terms"]
    bits = []
    if own.get("annual_rate") and Decimal(p["interest"]) > 0:
        bits.append("interest")
    if own.get("fee") and Decimal(p["fee"]) > 0:
        bits.append("a late fee")
    return " and ".join(bits) or "a late fee"


def greeting(cl, res=None):
    """The founder's own greeting word when they gave one ('Hey'), with the contact's first name if known."""
    word = ((res or {}).get("greeting") or "").strip().rstrip(",")
    fn = first_name(cl)
    if fn and fn.split()[0].rstrip(".").lower() in {"mr", "mrs", "ms", "miss", "dr", "mx"}:
        return f"Dear {fn},"
    if fn:
        return f"{word or 'Hi'} {fn},"
    if not cl["is_business"]:
        return f"Dear {cl['name']},"
    return f"{word or 'Hello'},"


def draft_for(res, cl, p):
    invs = [r for r in res["invoices"] if r["client"] == cl["name"] and r["number"] in cl["invoices"]]
    nums = [r["number"] for r in invs]
    ref = inv_list(nums)
    single = len(invs) == 1
    hi = greeting(cl, res)
    sign = res.get("founder_name") or "[NEED: your name]"
    owed = money(p["owed"])
    due_one = iso_long(min(r["due_date"] for r in invs))
    pay_by = iso_long(p["pay_by"]) if p["pay_by"] else ""
    days = p["days_late"]
    sent = date_list(p["sent_before"])
    pay_line = "Payment details are on the invoice."
    if res.get("bank_line", True) and p.get("bank_line", True):
        pay_line += " Our bank details have not changed; if you ever get a message saying they have, please call me before paying."
    part = [r for r in invs if r["part_disputed"]]
    if single and part:
        fact = (f"Invoice {nums[0]} for {money(invs[0]['amount'])} has {owed} that is not in question. It was due on {due_one}")
    elif single and invs[0]["payments"] and Decimal(invs[0]["amount"]) != Decimal(p["owed"]):
        paid = "; ".join(f"{money(a)} paid on {iso_long(d)}" for d, a in invs[0]["payments"])
        fact = f"Invoice {nums[0]} for {money(invs[0]['amount'])} ({paid}, thank you) leaves {owed} to pay. It was due on {due_one}"
    elif single:
        fact = f"Invoice {nums[0]} for {owed} was due on {due_one}"
    else:
        each = "; ".join(f"{r['number']}, {money(r['outstanding'])}" + (f" not in question of {money(r['amount'])}" if r["part_disputed"] else "")
                         + f", due {iso_long(r['due_date'])}" for r in invs)
        fact = f"{cap(ref)} come to {owed} ({each}). The first was due on {due_one}"
    extra = []  # lines that only the first message carries, or that every message must keep
    for r in invs:
        if r.get("total_shown") and p.get("fresh"):
            extra.append(f"The total line on invoice {r['number']} showed {money(r['total_shown'])} by mistake. The items add up to "
                         f"{money(r['amount'])}, and a corrected invoice is attached.")
    for r in part:
        if p.get("first"):
            extra.append(f"On invoice {r['number']}, I'd like to settle the {money(r['disputed_part'])} you raised separately: "
                         "tell me a time this week and I'll call. It is not part of the amount above.")
        else:
            extra.append(f"This leaves aside the {money(r['disputed_part'])} on invoice {r['number']} that we are still settling.")
    k = p["kind"]
    # The founder's own leverage, in their words: the client's written sign-off, and what their agreement holds until payment.
    appr = cl.get("approval") or ""
    if appr and k != "reminder":
        when = f" on {iso_long(cl['approval_date'])}" if cl.get("approval_date") else ""
        if appr.lower() in {"yes", "true", "y"}:
            extra.append(f"You approved the work in writing{when}.")
        else:
            extra.append(f"You approved the work in writing{when} (\"{appr}\").")
    if cl.get("held_until_paid"):
        extra.append(f"{cap(cl['held_until_paid'])} will follow as soon as {'the invoice is' if single else 'the invoices are'} paid in full, "
                     "as our agreement sets out.")
    extra_block = (["", *extra] if extra else [])
    act = ACTIONS[cl["final_action"]]
    the_inv = "the invoice" if single else "the invoices"
    holdup = ("If something is holding it up, tell me this week and I'll sort it." if not cl["is_business"] else
              "If something is holding it up, such as a purchase order number or a question on the invoice, tell me this week and I'll sort it.")
    still = (f"{fact} and is still unpaid {days} days later." if single else f"{fact}, and they are still unpaid.")
    it = "it" if single else "them"
    wrote = f" I wrote about {it} on {sent}." if sent else ""
    w = word_instalment()
    if k == "reminder":
        subj = f"{cap(ref)}: {owed}, due {due_one}"
        lines = [hi, "", f"A quick note: {fact[0].lower() + fact[1:]}, and I can't see the payment yet, so it may have slipped through."] + extra_block + [
            "", "Could you let me know the date it will be paid? If it has already gone, thank you; the payment date would help me match it.", "",
            pay_line, "", "Thanks,", sign]
    elif k == "firm":
        subj = f"{cap(ref)}: {owed}, {days} days overdue"
        lines = [hi, "", f"{fact} and is now {days} days overdue."]
        if p["sent_before"]:
            lines[-1] += f" I last wrote about {it} on {iso_long(p['sent_before'][-1])}."
        lines += extra_block
        lines += ["", f"Please pay {owed} by {pay_by}. {holdup}"]
        if p["terms_named"]:
            lines += ["", f"If it stays unpaid, our agreement adds {fee_words(res, p)}. I would rather not need to."]
        lines += ["", pay_line, "", "Thanks,", sign]
    elif k in {"plan", "call_plan"}:
        subj = f"{cap(ref)}: {owed}, {days} days overdue"
        lines = [hi, "", still + wrote] + extra_block + [""]
        if k == "call_plan" and Decimal(p["interest"]) + Decimal(p["fee"]) > 0:
            lines += [f"Our agreement adds {fee_words(res, p)} to a late invoice, which here comes to "
                      f"{money(Decimal(p['interest']) + Decimal(p['fee']))} so far. I'm happy to leave that off if {owed} is paid by {pay_by}.", ""]
        else:
            lines += [f"Please pay {owed} by {pay_by}.", ""]
        if p["plan"]:
            lines += [f"If one payment is hard right now, I can split it into {len(p['plan'])} {w}s:"] + plan_lines(p["plan"]) + [""]
            ask = ("Could we have a quick call this week to agree which works?" if k == "call_plan" else
                   "Reply to say which works for you, or call me this week.")
        else:
            ask = ("Could we have a quick call this week to agree a date?" if k == "call_plan" else
                   "If that date is hard, reply or call me this week and we'll agree one.")
        lines += [ask, "", pay_line, "", "Thanks,", sign]
    elif k == "late_fee":
        subj = f"{cap(ref)}: late fee now added"
        lines = [hi, "", still + wrote] + extra_block + ["",
                 "Under the late payment terms in our agreement I am now adding " + fee_words(res, p) + ":", "",
                 f"{cap(the_inv)}: {owed}"]
        if Decimal(p["interest"]) > 0:
            lines.append(f"Interest to {iso_long(p['send'])}: {money(p['interest'])}")
        if Decimal(p["fee"]) > 0:
            lines.append(f"Late fee: {money(p['fee'])}")
        lines.append(f"Total due: {money(p['total'])}")
        lines += [""]
        tail = f"If {money(p['total'])} is paid by {pay_by}, I'll add nothing further. An updated invoice is attached."
        if Decimal(p["daily"]) > 0:
            tail = (f"If {money(p['total'])} is paid by {pay_by}, I'll add nothing further; after that, interest adds "
                    f"{money(p['daily'])} a day. An updated invoice is attached.")
        lines += [tail, ""]
        if p["plan"]:
            lines += [f"If one payment is hard right now, I can split it into {len(p['plan'])} {w}s and add nothing further while they are paid on time:"] + plan_lines(p["plan"]) + [""]
        lines += [pay_line, "", "Thanks,", sign]
    else:  # final, final_nofee
        subj = f"Final notice: {ref}, {money(p['total'])} due by {pay_by}"
        opener = (f"This is my final notice about {ref} for {owed}, which was due on {due_one} and is now {days} days overdue."
                  if single else f"This is my final notice about {ref}, {owed} in total, the first due on {due_one} and now {days} days overdue.")
        body = [hi, "", opener + wrote] + extra_block
        if k == "final":
            parts = f"{the_inv} {owed}"
            if Decimal(p["interest"]) > 0:
                parts += f", interest of {money(p['interest'])}"
            if Decimal(p["fee"]) > 0:
                parts += f" and a late fee of {money(p['fee'])}"
            body += ["", f"The total due under our agreement is {money(p['total'])}: {parts}. If it is paid by {pay_by}, I'll add nothing further."]
        body += ["", f"If {money(p['total'])} is not paid by {pay_by}, I will {act}.", "", pay_line, "", sign]
        lines = body
    return subj, "\n".join(lines)


def founder_note(res, cl, p):
    k = p["kind"]
    notes = []
    if k in {"late_fee", "final"}:
        notes.append("These figures are plain arithmetic on the late payment terms you gave me, not advice on what you can charge. "
                     "Check with your lawyer that your clause applies this way before you send it, and send an updated invoice or statement with it.")
    if k in {"plan", "call_plan", "late_fee"} and p.get("plan"):
        notes.append(f"The {word_instalment()} plan is an offer, not a demand. If they agree, confirm the dates by email the same day and stop the chase while they keep to it. "
                     f"If they miss one, the next message on this list picks up from there.")
    if k in {"plan", "call_plan"} and not p.get("plan"):
        notes.append("No payment plan is offered here because the amount is below the smallest you said you would split.")
    if k == "call_plan":
        notes.append("Call script: thank them for the work together; name the invoice, the amount and the due date; ask what is holding it up; "
                     "agree a date or the plan; say you'll confirm it by email today.")
    if p.get("fresh") and any(r.get("total_shown") for r in res["invoices"] if r["client"] == cl["name"] and r["number"] in cl["invoices"]):
        notes.append("Attach the corrected invoice to this message; the one they have shows the wrong total.")
    if k.startswith("final"):
        notes.append(f"Only send this if you will do what the last line says: {ACTIONS[cl['final_action']]}.")
        if cl["final_action"] in {"collections", "lawyer"}:
            notes.append("Talk to the service or lawyer before you send this; they will say what they need from you, what it costs, and what fits where you and your client are.")
    if not cl["is_business"] and k in {"late_fee", "final", "final_nofee"}:
        notes.append("This client bought as a private individual. Chasing individuals has its own rules in many places; check the rules where you and they are before any formal step.")
    return " ".join(notes)


def dispute_body(res, cl):
    nums = cl["disputed"]
    invs = [r for r in res["invoices"] if r["client"] == cl["name"] and r["number"] in nums]
    figs = ", ".join(money(r["outstanding"]) for r in invs)
    if cl.get("dispute_sent"):
        first = f"I wrote on {date_list(cl['dispute_sent'])} about the points you raised on {inv_list(nums)} ({figs}), and I'd still like to settle them."
    else:
        first = f"I'd like to settle the points you raised on {inv_list(nums)} ({figs})."
    subj = f"{cap(inv_list(nums))}: agreeing the points you raised"
    body = "\n".join([greeting(cl, res), "", first, "", "Could we speak this week? Tell me a time that suits and I'll call.", "", "Thanks,",
                      res.get("founder_name") or "[NEED: your name]"])
    return subj, body


def write_drafts(res, out):
    restyle(res)
    blocks = ["# Messages to put in the founder's voice", "",
              "Rewrite the wording between the markers in the founder's voice. Keep every figure, invoice number, date and the one ask exactly as they are; check_copy.py and build will refuse a draft that drops or changes one. Do not edit the marker lines.",
              ""]
    for cl in res["clients"]:
        plan = ([cl["now"]] if cl["now"] else []) + cl["later"]
        to = [f"To: {cl['to']}"] if cl.get("to") else []
        for p in plan:
            cid = f"{slug(cl['name'])}-s{p['stage']}"
            subj, body = draft_for(res, cl, p)
            when = "send now" if cl["now"] is p else f"send on {p['send']} if still unpaid"
            blocks += [f"<!-- chaser id=\"{cid}\" client=\"{cl['name']}\" stage=\"{p['stage']}\" kind=\"{p['kind']}\" when=\"{when}\" -->",
                       *to, f"Subject: {subj}", "", body, "<!-- end -->", ""]
        if cl["disputed"]:
            cid = f"{slug(cl['name'])}-dispute"
            subj, body = dispute_body(res, cl)
            blocks += [f"<!-- chaser id=\"{cid}\" client=\"{cl['name']}\" stage=\"0\" kind=\"dispute\" when=\"send now\" -->",
                       *to, f"Subject: {subj}", "", body, "<!-- end -->", ""]
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text("\n".join(blocks), encoding="utf-8")


# ----------------------------------------------------------------------------- checks used by build

def parse_chasers(text):
    out = []
    for m in re.finditer(r"<!-- chaser (.*?) -->\n(.*?)<!-- end -->", text, re.S):
        attrs = dict(re.findall(r'(\w+)="(.*?)"', m.group(1)))
        body = m.group(2).strip("\n")
        to = re.search(r"^To:\s*(.*)$", body, re.M)
        subj = re.search(r"^Subject:\s*(.*)$", body, re.M)
        text_body = re.sub(r"^(To|Subject):.*\n?", "", body, flags=re.M).strip("\n")
        attrs.update({"to": to.group(1).strip() if to else "", "subject": subj.group(1).strip() if subj else "", "body": text_body})
        out.append(attrs)
    return out


def expected_chasers(res):
    exp = {}
    for cl in res["clients"]:
        for p in ([cl["now"]] if cl["now"] else []) + cl["later"]:
            exp[f"{slug(cl['name'])}-s{p['stage']}"] = (cl, p)
        if cl["disputed"]:
            exp[f"{slug(cl['name'])}-dispute"] = (cl, None)
    return exp


# ----------------------------------------------------------------------------- build

def restyle(res):
    set_style(res.get("locale"), res.get("currency"), res.get("country"), res.get("date_order"), res.get("decimal_style"), res.get("symbol_after"))


def build(res, chasers_path, out_dir, note_path=None):
    restyle(res)
    here = Path(__file__).resolve().parent
    sys.path.insert(0, str(here))
    import check_copy  # noqa: E402
    import docx_lite  # noqa: E402
    if not Path(chasers_path).exists():
        raise Stop(f"there is no messages file at {chasers_path}; run 'drafts' first")
    text = Path(chasers_path).read_text(encoding="utf-8")
    problems, warns = check_copy.check_chasers(text, res)
    note = ""
    if note_path:
        if not Path(note_path).exists():
            raise Stop(f"there is no note file at {note_path}")
        note = Path(note_path).read_text(encoding="utf-8").strip()
        p2, _, _ = check_copy.check(note)
        problems += [f"note: {x}" for x in p2]
        problems += [f"note: {x}" for x in check_copy.check_note_figures(note, res)]
    if problems:
        for x in problems:
            print("PROBLEM:", x)
        raise Stop(f"{len(problems)} problems in the messages or note; fix them and build again")
    for w in warns:
        print("WARN:", w)
    chasers = {c["id"]: c for c in parse_chasers(text)}
    as_of = date.fromisoformat(res["as_of"])
    biz = res.get("business") or "your business"
    fees_any = any(r["fee_applies"] for r in res["invoices"])
    d = docx_lite.Document(locale=res.get("locale"), paper=res.get("paper") or _STYLE["paper"])
    d.title(f"Get paid plan: {biz}")
    d.para(f"Worked out on {long_date(as_of)}. Figures are plain arithmetic on what you gave; nothing here is legal or tax advice.", style="Small")
    d.para(res["headline"], bold=True)
    if note:
        d.para(note)
    # Chase order
    rows = [["Client", "How much they matter", "Owed", "Days late", "Next message", "When"]]
    for name in res["chase_order"]:
        cl = next(c for c in res["clients"] if c["name"] == name)
        nxt = cl["now"] or (cl["later"][0] if cl["later"] else None)
        if nxt:
            step, when = kind_name(nxt), ("today" if cl["now"] else iso_long(nxt["send"]))
        elif cl["disputed"] and not cl["invoices"]:
            step, when = "settle the dispute", "today"
        else:
            step, when = "none: final notice sent", ""
        owed_cell = money(cl["owed"]) if cl["invoices"] else f"{money(sum(Decimal(r['outstanding']) for r in res['invoices'] if r['client'] == name and r['status'] == 'disputed'))} disputed"
        rows.append([name, TIER_LABELS[cl["tier"]], owed_cell, str(cl["days_late"]), step, when])
    if len(rows) > 1:
        d.h1("Who to chase, in order")
        d.table(rows)
    # Send now
    d.h1("Send now")
    sent_any = False
    for name in res["chase_order"] + [c["name"] for c in res["clients"] if c["name"] not in res["chase_order"]]:
        cl = next(c for c in res["clients"] if c["name"] == name)
        if cl["now"]:
            sent_any = True
            add_chaser(d, res, cl, cl["now"], chasers, now=True)
        if cl["disputed"]:
            c = chasers.get(f"{slug(cl['name'])}-dispute")
            if c:
                d.h2(f"{cl['name']}: disputed invoice")
                d.para("No late fee is added and nothing escalates while the dispute is open. This message asks to settle it.", style="Small")
                d.email(c["to"], c["subject"], c["body"])
                sent_any = True
        if cl["status"].startswith("final notice already sent"):
            sent_any = True
            d.h2(f"{cl['name']}: no further message")
            d.para(f"Their final notice has gone. If the money is not in your account by the date it gave, the next step is what it said: {ACTIONS[cl['final_action']]}. "
                   "Another email now would tell them the final notice was not final.")
    if not sent_any:
        d.para("Nothing to send today. The next messages are below with their dates.")
    # Owed
    d.h1("What you're owed")
    late_rows = [r for r in res["invoices"] if r["status"] == "late"]
    show_int = fees_any and any(Decimal(r["interest"]) > 0 for r in late_rows if r["fee_applies"])
    show_fee = fees_any and any(Decimal(r["fee"]) > 0 for r in late_rows if r["fee_applies"])
    head = ["Client", "Invoice", "Owed", "Due", "Days late"] + (["Interest"] if show_int else []) + (["Late fee"] if show_fee else [])
    if fees_any:
        head += ["Total today"]
    rows = [head]
    for r in late_rows:
        row = [r["client"], r["number"], money(r["outstanding"]), iso_long(r["due_date"]), str(r["days_late"])]
        if fees_any:
            if r["fee_applies"] and not r.get("waived"):
                row += ([money(r["interest"])] if show_int else []) + ([money(r["fee"])] if show_fee else []) + [money(r["total"])]
            else:
                label = "not charging" if r.get("waived") else "none"
                row += ([label] if show_int else []) + ([label] if show_fee else []) + [money(r["outstanding"])]
        rows.append(row)
    if len(rows) > 1:
        tot = ["Total", "", money(res["totals"]["owed"]), "", ""]
        if fees_any:
            tot += [""] * (int(show_int) + int(show_fee)) + [money(res["totals"]["with_fees"])]
        rows.append(tot)
        d.table(rows)
    for r in late_rows:
        if r["part_disputed"]:
            d.bullet(f"{r['client']}, {r['number']}: {money(r['disputed_part'])} of {money(r['amount'])} is disputed and waits until it is settled; "
                     f"the other {money(r['outstanding'])} is chased above.")
    if Decimal(res["totals"]["disputed"]) > 0:
        d.para(f"Disputed and waiting: {money(res['totals']['disputed'])}. Open in all, disputed or not: {money(res['totals']['all_open'])}.")
    for r in res["invoices"]:
        if r["status"] in {"not_due", "paid", "paid_late", "disputed", "need"}:
            label = {"not_due": "not due yet", "paid": "paid on time", "paid_late": "paid, late", "disputed": "disputed, waiting to be settled",
                     "need": "needs a figure before it can be worked out"}[r["status"]]
            d.bullet(f"{r['client']}, {r['number']}: {label}.")
    d.para("Only money in your account counts as paid: not a promise, not a remittance email.", style="Small")
    # Later
    if any(cl["later"] for cl in res["clients"]):
        d.h1("If they still haven't paid")
        d.para("Each of these is ready for its date. Check your account first.", style="Small")
        for cl in res["clients"]:
            for p in cl["later"]:
                add_chaser(d, res, cl, p, chasers, now=False)
    # Plans
    plans = [(cl, p) for cl in res["clients"] for p in ([cl["now"]] if cl["now"] else []) + cl["later"] if p.get("plan")]
    if plans:
        d.h1("If they ask to pay in parts")
        d.para(f"The {word_instalment()} plan in each offer, each rounded to the {'cent' if _STYLE['quantum'] == CENT else 'whole unit'}; "
               f"the last {word_instalment()} takes the difference so the plan adds up exactly.", style="Small")
        for cl, p in plans:
            d.h2(f"{cl['name']}: {money(p['plan_total'])} in {len(p['plan'])}")
            for line in plan_lines(p["plan"]):
                d.bullet(line)
    # Ladder
    d.h1("The escalation ladder")
    d.para("Each rung only if the one before it has not worked. The last two rungs are your decisions, not messages this plan writes: "
           "stopping work depends on what your agreement says, and a collections service or lawyer will tell you what fits where you and your client are. Take advice before either.", style="Small")
    for cl in res["clients"]:
        if not cl["ladder"]:
            continue
        d.h2(cl["name"])
        if not cl["is_business"]:
            d.para("Bought as a private individual. Chasing individuals has its own rules in many places; check the rules where you and they are "
                   "before any formal step. Their last step is taking advice or pausing work.", style="Small")
        for rg in cl["ladder"]:
            if rg["state"] == "sent":
                d.bullet(f"{rg['rung']}: sent {iso_long(rg['when'])}.")
            elif rg["state"] == "skipped":
                d.bullet(f"{rg['rung']}: skipped, " + ("because they always pay late." if cl["tier"] == "persistent" and rg["rung"] == STAGE_NAMES[1] else "given how late this is."))
            elif rg["state"] == "planned":
                d.bullet(f"{rg['rung']}: {'today' if rg['when'] == 'today' else iso_long(rg['when'])}.")
            else:
                when = f" from {iso_long(rg['when'])}" if rg["when"] else ""
                state = "your chosen next step" if rg["state"] == "chosen" else "an option to take advice on"
                d.bullet(f"{rg['rung']}{when}: {state}.")
    # Working
    d.h1("The working")
    for r in res["invoices"]:
        if r["status"] not in {"late", "paid_late"}:
            continue
        d.h2(f"{r['client']}, {r['number']}")
        for line in working_lines(r, res):
            d.bullet(line)
    # Terms
    d.h1("Terms for future work (drafts: check with your lawyer before using)")
    for title_, txt in terms_blocks(res):
        d.h2(title_)
        d.para(txt)
    if res["flags"] or res["needs"] or res["prevention"]["needs"]:
        d.h1("Check these")
        for n in res["needs"] + res["prevention"]["needs"]:
            d.bullet(f"[NEED: {n}]")
        for f in res["flags"]:
            d.bullet(f)
    spelling = check_copy.spelling_problems("\n".join(d.text), res.get("locale"))
    if spelling:
        raise Stop("the plan mixes spellings: " + "; ".join(spelling))
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    target = out / f"get-paid-plan-{slug(biz)}-{as_of.isoformat()}.docx"
    d.save(target, title=f"Get paid plan: {biz}", description=f"Made with Merigrove {SKILL_NAME}")
    print(f"WROTE: {target}")
    return target


def add_chaser(d, res, cl, p, chasers, now):
    c = chasers.get(f"{slug(cl['name'])}-s{p['stage']}")
    when = "send today" if now else f"send on {iso_long(p['send'])} if still unpaid"
    d.h2(f"{cl['name']}: {kind_name(p)} ({when})")
    note = founder_note(res, cl, p)
    if note:
        d.para(note, style="Small")
    if c:
        d.email(c["to"], c["subject"], c["body"])


def working_lines(r, res):
    lines = [f"Invoice total {money(r['amount'])}" + (f", {money(r['outstanding'])} still unpaid." if r["status"] == "late" else ", paid late in full.")]
    if r.get("part_disputed"):
        lines[0] = (f"Invoice total {money(r['amount'])}: {money(r['disputed_part'])} disputed and left out of the chase and any late fee; "
                    f"{money(r['outstanding'])} still unpaid and chased.")
    lines.append(f"Due {iso_long(r['due_date'])}: {r['due_basis']}.")
    for pd, pa in r["payments"]:
        lines.append(f"Paid {money(pa)} on {iso_long(pd)}.")
    if r["fee_applies"]:
        own = res["own_terms"]
        src = f"Your terms: \"{own['clause'].rstrip('. ')}\"" if own.get("clause") else "Your terms, as you gave them"
        lines.append(src + (f" (rate: {own['rate_typed']})" if own.get("rate_typed") and own.get("clause") and own["rate_typed"] not in own["clause"] else "") + ".")
        lines.append(f"Counted from {iso_long(r['fee_from'])}" + (f", after your {own['grace_days']} day grace period." if own.get("grace_days") else ", the day after the due date."))
        if r.get("annual_rate"):
            lines.append(f"Interest: {r['rate_basis']}. {money(r['outstanding'])} x {pct_out(r['annual_rate'])}% / 365 = {money(r['daily'])} a day; "
                         f"{money(r['interest'])} to {iso_long(res['as_of'])}" + (" (less on the parts already paid)." if r["payments"] else "."))
        if Decimal(r["fee"]) > 0:
            f = own.get("fee") or ["amount", r["fee"]]
            base = Decimal(r["amount"]) - Decimal(r["disputed_part"])
            lines.append(f"Late fee: {money(r['fee'])}" + (f", {pct_out(f[1])}% of {money(base)}." if f[0] == "pct" else ", once for this invoice."))
        lines.append("Plain arithmetic on your own terms. Check with your lawyer that your clause applies this way.")
    if r.get("waived"):
        lines.append(f"You chose not to charge this client, so none of this is in their messages. Total today: {money(r['outstanding'])}.")
        return lines
    lines.append(f"Total today: {money(r['total'])}.")
    return lines


def terms_blocks(res):
    pv = res["prevention"]
    days = res.get("default_terms") or f"{DEFAULT_TERMS_DAYS} days"
    w = word_instalment()
    blocks = []
    if pv["deposit_pct"]:
        txt = (f"For new projects: {pct_out(pv['deposit_pct'])}% of the fee is due before work starts, and the balance is due on delivery. "
               "Work is booked in once the deposit is paid.")
        if pv["deposit_example"]:
            txt += (f" On {money(pv['example_price'])} ({pv['example_source']}), that is {money(pv['deposit_example'][0])} up front "
                    f"and {money(pv['deposit_example'][1])} on delivery.")
        blocks.append(("Deposit", txt))
    if pv["milestones"]:
        shares = " / ".join(f"{pct_out(m)}%" for m in pv["milestones"])
        txt = (f"For larger projects, bill in stages ({shares}): a deposit before work starts, then on each agreed milestone, each due {days} after its invoice. "
               "Work on the next stage starts once the last stage is paid.")
        if pv["milestone_example"]:
            txt += f" On {money(pv['example_price'])}, that is " + ", ".join(money(a) for a in pv["milestone_example"]) + "."
        blocks.append(("Milestone billing", txt))
    if pv["card_on_file"]:
        blocks.append(("Card or account on file",
                       "For monthly work: payment is taken automatically on the first working day of each month, in advance, from the card or account you " + word_authorise() + " when you sign. "
                       "We will tell you before any change to the amount."))
    own = res["own_terms"]
    if own.get("has") and own.get("clause"):
        late = f"Your current clause stays as it is: \"{own['clause']}\""
    elif pv.get("late_fee"):
        late = f"If payment is late, a late fee of {pv['late_fee']} applies. [NEED: confirm the wording with your lawyer]"
    else:
        late = "[NEED: your late fee or interest, if you want one. Your lawyer can say what you can charge where you and your clients are.]"
    blocks.append(("Late fee or interest", late))
    blocks.append(("Invoice footer",
                   "Payment due by [due date] (" + days + " from the invoice date). Our bank details will never change by email; if you are told they have, call us before paying."))
    blocks.append(("Before you use these",
                   "These are drafts. Check them with your lawyer before you put them in a contract, because what a contract can say differs by country and state. "
                   "Put the due date as a date on every invoice, not only as terms. "
                   "Enter prices before any sales tax (VAT, GST or similar); ask your accountant whether you need to charge it."))
    return blocks


# ----------------------------------------------------------------------------- CLI

TEMPLATE = {
    "business": None, "founder_name": None, "greeting": None, "date": None,
    "country": None, "locale": None, "currency": None, "date_order": None, "decimal_style": None,
    "weekend": None, "work_days": None, "holidays": [], "default_terms": None,
    "own_late_terms": {"has": False, "rate": None, "fee": None, "grace_days": None, "clause": None},
    "plan": {"instalments": None, "every": None, "min_amount": None},
    "prevention": {"deposit_pct": None, "milestones": None, "card_on_file": None, "late_fee": None, "typical_price": None},
    "bank_line": None, "confirmed": [], "gap_days": None, "final_after_days": None, "report_total": None,
    "clients": [{"name": None, "is_business": True, "tier": "normal", "charge_late_fee": True, "contact": None, "to": None,
                 "ongoing_work": None, "asked_for_plan": False, "final_action": "advice", "terms": None, "stages_sent": [],
                 "approval": None, "approval_date": None, "held_until_paid": None, "gap_days": None, "final_after_days": None,
                 "invoices": [{"number": None, "amount": None, "invoice_date": None, "due_date": None, "terms": None,
                               "payments": [], "paid_in_full_on": None, "disputed": False, "disputed_amount": None,
                               "total_shown": None, "line_items": []}]}],
}


def print_table(res):
    print(res["headline"])
    print()
    print(f"{'Client':<22} {'Invoice':<10} {'Owed':>12} {'Due':<19} {'Late':>5} {'Interest':>10} {'Fee':>9} {'Total':>12}  Status")
    for r in res["invoices"]:
        due = iso_long(r["due_date"]) if r["due_date"] else "?"
        print(f"{r['client'][:22]:<22} {r['number'][:10]:<10} {money(r['outstanding']):>12} {due:<19} {r['days_late']:>5} "
              f"{money(r['interest']):>10} {money(r['fee']):>9} {money(r['total']):>12}  {r['status']}")
    print()
    for cl in res["clients"]:
        print(f"{cl['name']}: {cl['tier']}, {cl['status']}")
        for p in ([cl["now"]] if cl["now"] else []) + cl["later"]:
            print(f"   stage {p['stage']} {p['kind']:<12} send {p['send']}  pay by {p['pay_by'] or '-'}  total {money(p['total'])}"
                  + (f"  plan {len(p['plan'])} x from {p['plan'][0][0]}" if p.get("plan") else ""))
    print("Chase order:", ", ".join(res["chase_order"]) or "none")
    for n in res["needs"] + res["prevention"]["needs"]:
        print("NEED:", n)
    for f in res["flags"]:
        print("FLAG:", f)


def check_results(res):
    if not isinstance(res, dict) or res.get("skill") != SKILL:
        raise Stop("that is not a results file from 'compute'; run compute with --out first")


def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = a.add_subparsers(dest="cmd")
    sub.add_parser("template")
    c = sub.add_parser("compute")
    c.add_argument("inputs")
    c.add_argument("--out")
    c.add_argument("--as-of")
    dr = sub.add_parser("drafts")
    dr.add_argument("results")
    dr.add_argument("--out", required=True)
    b = sub.add_parser("build")
    b.add_argument("results")
    b.add_argument("--chasers", required=True)
    b.add_argument("--out", required=True)
    b.add_argument("--note")
    args = a.parse_args(argv)
    if args.cmd == "template":
        print(json.dumps(TEMPLATE, indent=2))
        return 0
    if args.cmd == "compute":
        raw = load_json(args.inputs)
        as_of = None
        if args.as_of:
            try:
                as_of = parse_date(args.as_of, date.today(), "DMY", what="--as-of")
            except Need as e:
                raise Stop(str(e))
        res = compute(raw, as_of)
        if args.out:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")
        print_table(res)
        if args.out:
            print(f"WROTE: {args.out}")
        return 1 if (res["needs"] or res["prevention"]["needs"]) else 0
    if args.cmd == "drafts":
        res = load_json(args.results)
        check_results(res)
        write_drafts(res, args.out)
        print(f"WROTE: {args.out}")
        return 0
    if args.cmd == "build":
        res = load_json(args.results)
        check_results(res)
        build(res, args.chasers, args.out, args.note)
        return 1 if res["needs"] else 0
    a.print_help()
    return 2


if __name__ == "__main__":
    try:  # a closed output pipe (for example '| head') ends quietly; files are written before anything is printed
        import signal
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    except (AttributeError, ValueError):
        pass
    try:
        sys.exit(main())
    except (Stop, Need) as e:
        print(f"STOP: {e}. Nothing usable was written.")
        sys.exit(2)
    except Exception as e:  # noqa: BLE001
        print(f"STOP: something unexpected went wrong ({type(e).__name__}: {e}). Check the inputs file against 'template' and run again. Nothing usable was written.")
        sys.exit(2)
