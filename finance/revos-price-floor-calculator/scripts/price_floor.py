#!/usr/bin/env python3
"""Price Floor Calculator: the arithmetic, the workbook and the one-page summary.

Usage:
  python3 scripts/price_floor.py template                      print a blank inputs file
  python3 scripts/price_floor.py compute <inputs.json>          print every figure and the verdicts
        [--json-out results.json]
  python3 scripts/price_floor.py build <inputs.json> --out <folder>
        [--note note.md] [--previous old-inputs.json]
        [--format auto|xlsx|csv]                                 write the workbook (or CSV) and the summary

Inputs are JSON. Values may be messy strings ("1.5k", "about 12", "10 to 12", "2.9%", "1.200,50 €",
"4,5 horas", "3 x 500"); the script normalises them and records what it did. Missing values get a stated
default or a [NEED] flag, never an invented figure.

Every figure is defined once below and mirrored by a spreadsheet formula in the workbook, so
the summary and the workbook cannot disagree. openpyxl is optional: without it the script
writes CSV files and the summary still carries every figure. Standard library otherwise.
No network calls.

  python3 scripts/price_floor.py checknote <inputs.json> <note.md> [--previous old-inputs.json]
                                                               check the note's figures without building

Figures are read in the founder's own number style (1,234.56 or 1.234,56), detected once from everything they
gave, through locale_numbers.py. A figure that can be read two ways, cannot be read, or cannot be right (an hour
under 1, a price under 10, overheads above the hour) stops the run with a STOP line and one ASK line to put to
the founder.

Exit codes: 0 clean, 1 written with [NEED] flags, 2 stopped (unreadable input, a question for the founder, or no offer).
"""
import argparse
import csv
import html
import json
import math
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import locale_numbers as ln  # noqa: E402  the shared reader for founder-typed numbers, copied unchanged

STYLE = {"decimal": None, "dec": ".", "group": ",", "after": False, "indian": False}  # the founder's number style, set once per run
PLACE = {"paper": "A4", "date_order": "DMY", "assumed": True}  # from the founder's country, set once per run
SKILL_NAME = "Price Floor Calculator"
WEEKS_PER_MONTH = 52 / 12

WORKING_WEEKS = 46.0
WEEKS_SRC = ("assumption: 52 less 6 weeks off for your holidays and public holidays; "
             "set your own figure")
DAY_HOURS = 8.0  # hours in a working day when the founder gives time in days; set per run from day_hours
SALES_TAX_LINE = ("Enter prices before any sales tax (VAT, GST or similar); ask your accountant whether you need to "
                  "charge it.")
DISCLAIMER = ("A planning tool, not financial, tax or legal advice. Sales tax, income tax and the cost of employing "
              "anyone belong with your accountant or payroll provider.")


class InputError(Exception):
    """An input the calculator cannot use. Shown to the founder as one plain STOP line."""


class AskError(InputError):
    """A figure that can be read two ways, cannot be read, or is implausible: one question for the founder."""

    def __init__(self, msg, question):
        super().__init__(msg)
        self.question = question


DEFAULTS = {
    "target_margin": (0.20, "default: a 20% buffer; change it if you aim higher"),
    "client_hours_week": (25.0, "default: 25 client hours a week (assumption; change it)"),
    "rescope_limit": (0.25, "default: a restructure can take at most a 25% cut in hours; a working default"),
    "your_rate": (60.0, "a placeholder of 60 an hour because none was given; change it"),
    "fee_card": (0.03, "card default"),
    "fee_bank": (0.0, "no payment fee on bank transfers"),
}
AT_FLOOR = 0.95  # a price within 5% of its floor (and above its cost floor) holds: "Hold, at the floor"
HOURS_GAP = 0.10
HOURS_OK = "client hours as given"  # the founder confirmed their hours though the offers use a different figure  # the hours the offers use and the hours the founder gave may differ by this share before it is flagged
DOLLAR_COUNTRIES = {"US": "USD", "AU": "AUD", "CA": "CAD", "NZ": "NZD", "SG": "SGD", "HK": "HKD"}


def card_default_src():
    return (f"default: {pct(0.03)} on card payments, a working assumption; give your processor's rate and the floors use it")
SYMBOLS = {"GBP": "£", "USD": "$", "EUR": "€", "AUD": "A$", "CAD": "C$", "NZD": "NZ$", "SGD": "S$", "HKD": "HK$",
           "INR": "₹", "JPY": "¥", "BRL": "R$", "PHP": "₱"}
CODES = r"gbp|usd|eur|aud|cad|nzd|sgd|hkd|inr|jpy|chf|zar|aed|myr|sek|nok|dkk|php|idr|thb|mxn|brl"


# ------------------------------------------------------------------ parsing messy values
# Every founder-typed number goes through locale_numbers (the shared reader, copied unchanged), in the founder's
# own number style, detected once per run. This layer adds only what is specific to this calculator: unit words
# after prices and hours, sums of parts, ranges read as their midpoint, and sales-tax words on prices.
NUM = r"\d(?:[\d.,'\u00a0\u202f]*\d)?"
_HOUR_UNITS = (r"(?:hours?|hrs?|h|horas?|heures?|stunden?|std\.?|ore|uur|timer|jam|days?|d[ií]as?|tage?n?|jours?|"
               r"giorni|dagen?|hari|mins?|minutes?|minutos?|minuten?|min\.?)")
_PER_UNITS = (r"(?:months?|mo|mes(?:es)?|mois|monat(?:s)?|years?|yrs?|yr|annum|a[ñn]os?|ans?|jahre?s?|weeks?|wks?|"
              r"semanas?|semaines?|wochen?|sales?|ventas?|clients?|clientes?|projects?|proyectos?|sprints?|"
              r"sessions?|sesi[oó]n(?:es)?|seats?|members?|miembros?|episodes?|eps?|units?)")
_MONEY_PER = re.compile(r"(?:/\s*|\b(?:per|a|an|al|por|pro|par|each|every|cada)\s+)(?:" + _PER_UNITS[3:-1] +
                        r"|hours?|hrs?|hr|h|horas?|hora|heures?|heure|stunden?|stunde|std|days?|d[ií]as?|d[ií]a)\b\.?", re.I)
_HOURS_PER = re.compile(r"(?:/\s*|\b(?:per|a|an|al|por|pro|par|each|every|cada)\s+)" + _PER_UNITS + r"\b\.?", re.I)
_FILLER = re.compile(r"\b(?:monthly|yearly|annually|weekly|mensual(?:es)?|anual(?:es)?|each|flat|fijo|pm|pa|p/m|p/a|"
                     r"brutos?|brutas?|netos?|gross|net|before tax(?:es)?|after tax(?:es)?|pre-?tax|post-?tax|"
                     r"take[- ]home|all in|in total|total|approx\.?|approximately|roughly|about|around|circa|maybe|probably|prob\.?|"
                     r"like|or so|give or take|more or less|one[- ]?off|one[- ]?time|once|fixed|fee|"
                     r"say|unos|unas|aprox\.?|ca\.|of my time|from me|mine|me)\b", re.I)
_TAX_EXCL = re.compile(r"(?:\+|\bplus\b|\bexcl\.?(?:uding)?\b|\bex\.?\b|\bsin\b|\bbefore\b|\bantes del?\b|\bhors\b|"
                       r"\bzzgl\.?|\bsans\b|\bsem\b)\s*(?:de\s+)?(?:iva|vat|gst|tva|mwst|ust|hst|sst|ppn|sales tax)\b\.?",
                       re.I)
_TAX_WORD = re.compile(r"\b(?:iva|vat|gst|tva|mwst|ust|hst|sst|ppn|sales tax|ttc)\b", re.I)
_TAX_INCL = re.compile(r"\b(?:incl\.?|inc\.?|including|included|incluid[oa]s?|inclusive|con|inkl\.?|avec|com)\b", re.I)
NONE_ZERO = {"none", "nothing", "nil", "nada", "ninguno", "ninguna", "zero", "no", "0"}
NONE_SKIP = {"", "n/a", "na", "unknown", "not known", "[not known]", "?", "skip", "idk", "no idea", "not sure", "tbc",
             "-", "no sé", "ns"}
_WORDNUMS = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7", "eight": "8",
             "nine": "9", "ten": "10", "half": "0.5", "a": "1", "an": "1"}


def _ask(label, v, why, question):
    q = question or f"Can you give {label.lower()} again as one figure? I read '{v}' and could not be sure of it."
    return AskError(f"{label}: '{v}' {why}", q)


def _num(tok, label, v):
    try:
        return ln.parse_number(tok, STYLE["decimal"], allow_words=False)[0]
    except ln.Ambiguous as e:
        raise _ask(label, v, f"can be read two ways ({e})",
                   f"In '{v}', is {tok} a whole number with a thousands mark or a decimal? "
                   "Do you write a thousand and a half as 1.000,50 or 1,000.50?")
    except ln.Unreadable:
        raise _ask(label, v, "could not be read as a number", None)


def _expr(e, label, v, hours_field):
    """Sums of parts, in the founder's number style: '7.5 + 3 + 3.75', '=2.420/1,21', '1 day + 2', '6 x 1.5'."""
    e = ln._strip_currency(e)
    e = re.sub(r"\b(plus|and|y|und|et|mais)\b", "+", e, flags=re.I)
    if hours_field:
        e = re.sub(r"\b(" + "|".join(k for k in _WORDNUMS if len(k) > 2) + r")\b",
                   lambda m: _WORDNUMS[m.group(1).lower()], e, flags=re.I)
    unit = _HOUR_UNITS if hours_field else r"(?!)"
    tok = re.compile(r"(" + NUM + r")\s*(k\b|" + unit + r"(?![a-z]))?", re.I)

    def repl(m):
        n, u = m.group(1), (m.group(2) or "")
        if u.lower() == "k":
            val = _num(n, label, v) * 1000
        elif u:
            try:
                val = ln.parse_hours(f"{n} {u}", DAY_HOURS, 5, STYLE["decimal"])[0]
            except (ln.Ambiguous, ln.Unreadable):
                raise _ask(label, v, "could not be read as a length of time", None)
        else:
            val = _num(n, label, v)
        return f"({val!r})"
    out = tok.sub(repl, e)
    out = re.sub(r"(?<=\))\s*[x×X]\s*(?=\()", "*", out).replace("×", "*")
    if re.search(r"[A-Za-z]", out):
        raise _ask(label, v, "mixes words and figures in a way the calculator cannot read", None)
    try:
        return _safe_eval(out)
    except (ValueError, SyntaxError, ZeroDivisionError):
        raise _ask(label, v, "is not a sum the calculator can work out", None)


def _safe_eval(expr):
    """Evaluate plain arithmetic (numbers, + - * / and brackets) without eval()."""
    import ast
    import operator as op
    ops = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv, ast.USub: op.neg, ast.UAdd: op.pos}

    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return float(n.value)
        if isinstance(n, ast.BinOp) and type(n.op) in ops:
            return ops[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in ops:
            return ops[type(n.op)](ev(n.operand))
        raise ValueError("not plain arithmetic")
    return ev(ast.parse(expr, mode="eval"))


def to_num(v, note=None, label="", hours_field=False, price_field=False):
    """Read one founder-typed figure in the founder's number style (STYLE, set once per run).

    Prices, costs and pay: currency marks, codes and unit words ('/mo', 'a month', 'al mes', 'brutos', 'pm') are
    stripped; '1.5k' is 1,500. Hours: days count as DAY_HOURS (8 unless the founder sets day_hours), minutes as
    sixtieths, in English and other languages. Ranges become their midpoint (noted); sums of parts ('7.5 + 3',
    '=4450 - 31200/12', '=2.420/1,21', '1 day + 2') are worked out here, never by eye. A figure that can be read two
    ways, or not at all, stops the run with one question for the founder (AskError)."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, (list, dict)):
        raise InputError(f"{label or 'a value'} should be one figure, not a list")
    raw = unicodedata.normalize("NFKC", str(v)).strip()
    low = raw.lower().strip().strip(".")
    if low in NONE_ZERO and low != "0":
        return 0.0
    if low in NONE_SKIP:
        return None
    s = _TAX_EXCL.sub(" ", raw)
    if _TAX_WORD.search(s):
        if price_field:
            raise _ask(label, v, "looks like it includes sales tax",
                       f"Is {raw} before or after sales tax? If it includes it, what is the price before it, or what "
                       "rate do you charge?")
        s = _TAX_INCL.sub(" ", _TAX_WORD.sub(" ", s))  # a cost is entered as paid, sales tax and all
    s = re.sub(r"(?<=\d)\s*-?ish\b", "", s, flags=re.I)
    s = (_HOURS_PER if hours_field else _MONEY_PER).sub(" ", s)
    s = _FILLER.sub(" ", s)
    s = re.sub(r"[~≈]", " ", s)
    s = re.sub(r"[?!]", " ", s)
    s = re.sub(r"(?:(?<=\s)|^)[.,;:]+(?=\s|$)", " ", s)  # punctuation left behind by the words taken out
    s = re.sub(r"\s+", " ", s).strip().strip(".,;:").strip()
    if not re.search(r"\d", s) and not (hours_field and re.search(r"\b(an?|one|two|three|half|couple|few)\b", s, re.I)):
        return None
    expr = s.startswith("=") or re.search(NUM + r"\s*k?\s*[+*/×]\s*[\d(=]", s) or \
        re.search(r"\d\s*[xX]\s*\d", s) or (hours_field and re.search(r"\+|\bplus\b", s, re.I))
    if expr:
        val = _expr(s.lstrip("=").strip(), label, v, hours_field)
        if note is not None:
            shown = re.sub(r"\s+", " ", str(v).lstrip("=").replace("*", " x ")).strip()
            note.append(f"{label}: {fmt_plain(val, 2)}, worked out from {shown}")
        if hours_field and note is not None and re.search(r"\d\s*(days?|d[ií]as?|tage?|jours?)\b", raw, re.I):
            note.append(f"{label}: days read as {fmt_plain(DAY_HOURS, 2)} hours each")
        return val
    if hours_field:
        t = re.sub(r"\b(?:between|entre|zwischen)\s+(.+?)\s+(?:and|y|und|et)\s+", r"\1 to ", s, flags=re.I)
        try:
            val, nts = ln.parse_hours(t, DAY_HOURS, 5, STYLE["decimal"])
        except ln.Ambiguous as e:
            raise _ask(label, v, f"can be read two ways ({e})", None)
        except ln.Unreadable:
            raise _ask(label, v, "could not be read as a number of hours",
                       f"How many hours is '{raw}'? One figure is fine.")
        if note is not None:
            if any("midpoint" in n for n in nts):
                note.append(f"{label}: read '{v}' as the midpoint, {fmt_plain(val, 2)}")
            if any(n.startswith("day =") for n in nts):
                note.append(f"{label}: days read as {fmt_plain(DAY_HOURS, 2)} hours each")
        return val
    t = ln._strip_currency(s).strip()
    m = re.fullmatch(r"(?:between\s+|entre\s+)?(" + NUM + r")\s*(k|m)?\s*(?:-|to|or|and|a|y|bis|à|\u2013)\s*(" + NUM +
                     r")\s*(k|m)?", t, re.I)
    if m:
        mult = {"k": 1000.0, "m": 1e6}
        a = _num(m.group(1), label, v) * mult.get((m.group(2) or m.group(4) or "").lower(), 1.0)
        b = _num(m.group(3), label, v) * mult.get((m.group(4) or "").lower(), 1.0)
        mid = (a + b) / 2
        if note is not None:
            note.append(f"{label}: read '{v}' as the midpoint, {fmt_plain(mid, 2)}")
        return mid
    try:
        return ln.parse_number(s, STYLE["decimal"])[0]
    except ln.Ambiguous as e:
        kind = "a whole number" if re.search(r"[.,]\d{3}\b", raw) else "a decimal"
        raise _ask(label, v, f"can be read two ways ({e})",
                   f"Is {raw} {kind}? Do you write a thousand and a half as 1.000,50 or 1,000.50?")
    except ln.Unreadable:
        raise _ask(label, v, "could not be read as one figure", None)


def to_pct(v, note=None, label="", limit=None):
    """'20%', '20', '1', '0.2', '1,4%' and '20 per cent' read as percentages, in the founder's number style: a bare
    number of 1 or more is per cent ('1' is 1%), a number below 1 is a fraction ('0.2' is 20%). With a limit, a
    value at or above it stops the run."""
    if v is None:
        return None
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        x = float(v)
        x = x / 100 if x >= 1 else x
    else:
        s = str(v).strip()
        pct_word = re.compile(r"%|\bper ?cent\b|\bpercent\b|\bpor ?ciento\b|\bpour ?cent\b|\bprozent\b", re.I)
        has = bool(pct_word.search(s))
        tmp = []
        x = to_num(pct_word.sub(" ", s), tmp, label)
        if x is None:
            return None
        if has or x >= 1:
            x = x / 100
        if tmp and note is not None:
            shown = re.sub(r"\s+", " ", str(v).lstrip("=").replace("*", " x ")).strip()
            note.append(f"{label}: {pct(x)}, worked out from {shown}")
    if x < 0:
        raise InputError(f"{label} cannot be negative (read '{v}')")
    if limit is not None and x >= limit:
        raise InputError(f"{label} of {pct(x)} cannot be right: at {pct(limit)} or more nothing is left to cover costs. "
                         "Check the figure and run again")
    return x


def parse_plan(v, label="Instalments"):
    """'3 x 500', '3x500 monthly', '2 payments of 1,750', '3 cuotas de 1.200' -> (n, amount)."""
    if v in (None, ""):
        return None
    s = unicodedata.normalize("NFKC", str(v))
    m = re.search(r"(\d+)\s*(?:x|×|\*|payments? of|instalments? of|installments? of|cuotas? de|pagos? de|plazos? de)\s*(.+)",
                  s, re.I)
    if not m:
        return None
    amt = to_num(m.group(2), None, label)
    return (int(m.group(1)), amt) if amt else None


# ------------------------------------------------------------------ the founder's number style, country and checks
STYLE_KEYS = ["target_pay_year", "your_client_hours_week", "working_weeks_year", "your_rate", "target_margin",
              "overheads_month", "client_hours_week", "full_hours_week", "fee_rate", "card_share", "day_hours"]
OFFER_STYLE_KEYS = ["price", "your_hours", "team_hours", "team_rate", "contractor", "tools", "fee_rate", "refund_rate",
                    "per_month", "alternative", "proposed", "instalments", "card_share"]


def founder_strings(raw):
    out = [raw.get(k) for k in STYLE_KEYS]
    for o in raw.get("offers") or []:
        if isinstance(o, dict):
            out += [o.get(k) for k in OFFER_STYLE_KEYS]
    return [str(x) for x in out if isinstance(x, str) and re.search(r"\d", x)]


def set_style(raw, cur):
    """Detect the founder's decimal mark once, from every figure they gave; ask if the figures disagree."""
    given = str(raw.get("decimal") or "").strip().lower()
    samples = founder_strings(raw)
    src = "founder said"
    if given in ("comma", ",", "1.234,56", "1 234,56", "decimal comma"):
        dec = "comma"
    elif given in ("dot", "point", ".", "1,234.56", "decimal point"):
        dec = "dot"
    else:
        seen = {}
        for s in samples:
            d = ln.detect_decimal_style([s])
            if d:
                seen.setdefault(d, s)
        if len(seen) > 1:
            raise AskError(f"the figures mix two number styles ('{seen['dot']}' and '{seen['comma']}')",
                           "Do you write a thousand and a half as 1.000,50 or as 1,000.50?")
        dec = next(iter(seen), None)
        src = "read from how you write your figures" if dec else "not needed: no figure could be read two ways"
    STYLE["decimal"] = dec
    STYLE["dec"] = "," if dec == "comma" else "."
    STYLE["group"] = "," if dec != "comma" else ("\u202f" if any(re.search(r"\d[ \u00a0\u202f]\d{3}\b", s) for s in samples)
                                                  else ".")
    sym = SYMBOLS.get(cur, "")
    after = before = False
    if sym:
        for s in samples:
            after |= bool(re.search(r"\d\s*" + re.escape(sym), s))
            before |= bool(re.search(re.escape(sym) + r"\s*\d", s))
    STYLE["after"] = after and not before or (dec == "comma" and not before and cur == "EUR")
    STYLE["indian"] = dec != "comma" and any(re.search(r"\d,\d{2},\d{3}\b|\b(lakhs?|lacs?|crores?)\b", x, re.I)
                                             for x in samples)
    return dec, src



def billing_of(v):
    s = str(v or "").lower()
    if re.search(r"month|retainer|recurring|subscription|rolling|/mo|per mo", s):
        return "monthly"
    return "one-off"


_FIXED_FEE = re.compile(r"^\s*=?\s*([^+]*%[^+]*?)\s*\+\s*([^+%]+?)\s*(?:a payment|per payment|per transaction|each)?\s*$", re.I)


def split_fixed_fee(v):
    """'2.9% + 30c', '1,4% + 0,25 €', '2.9% + $0.30': a percentage plus a fixed amount a payment."""
    if not isinstance(v, str):
        return None
    m = _FIXED_FEE.match(v)
    return (m.group(1), m.group(2)) if m else None


def fixed_part(v, label):
    s = str(v).strip()
    m = re.fullmatch(r"(\d+(?:[.,]\d+)?)\s*(?:c|¢|cents?|c[ée]ntimos?|p|pence)\.?", s, re.I)
    if m:
        return to_num(m.group(1), None, label) / 100
    x = to_num(s, None, label)
    if x is None:
        raise AskError(f"{label}: could not read the fixed part '{v}' of the fee",
                       f"What is the fixed part of your card fee per payment? I read '{v}'.")
    return x


def fee_from_paid_by(v):
    s = str(v or "").lower()
    if not s:
        return None, None
    if re.search(r"bank|transfer|bacs|faster payment|cheque|check|ach|wire|standing order|direct debit|gocardless"
                 r"|paynow|payid|bpay|zelle|interac|sepa|upi|giro|e-?transfer", s):
        if re.search(r"direct debit|gocardless", s):
            return None, None  # fees exist but vary; fall through to the card default unless a rate is given
        return 0.0, "no payment fee"
    if re.search(r"card|stripe|paypal|square|online|sumup|apple pay|link|tarjeta", s):
        return DEFAULTS["fee_card"][0], (f"the {pct(0.03)} card default applies, a working assumption; give your "
                                         "processor's rate and the floors use it")
    return None, None


# ------------------------------------------------------------------ formatting
def _indian(s):
    """1,234,567.5 grouped the Indian way: 12,34,567.5."""
    sign, s = ("-", s[1:]) if s.startswith("-") else ("", s)
    whole, _, frac = s.partition(".")
    whole = whole.replace(",", "")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        head = ",".join(re.findall(r"\d{1,2}(?=(?:\d{2})*$)", head))
        whole = head + "," + tail
    return sign + whole + ("." + frac if frac else "")


def _style(s):
    """Python's 1,234.5 written in the founder's own style (1.234,5 or 1 234,5 for a decimal-comma founder,
    12,34,567 for a founder who groups in lakhs)."""
    if STYLE.get("indian") and STYLE["dec"] == ".":
        return _indian(s)
    if STYLE["dec"] == ",":
        s = s.replace(",", "\0").replace(".", ",").replace("\0", STYLE["group"])
    return s


def fmt_plain(v, dp=None):
    if v is None:
        return "[NEED]"
    if dp is None:
        dp = 0 if abs(v) >= 10 else 2
    s = f"{v:,.{dp}f}"
    if dp and "." in s:
        s = s.rstrip("0").rstrip(".")
    return _style(s)


def money(v, cur):
    if v is None:
        return "[NEED]"
    sym = SYMBOLS.get(cur, "")
    sign = "-" if v < 0 else ""
    body = fmt_plain(abs(v))
    if sym:
        return f"{sign}{body} {sym}" if STYLE["after"] else f"{sign}{sym}{body}"
    return f"{sign}{body} {cur}" if cur else f"{sign}{body}"


def pct(v):
    if v is None:
        return "[NEED]"
    x = v * 100
    dp = 0 if abs(x) >= 10 or abs(x - round(x)) < 0.05 else 1
    return _style(f"{x:.{dp}f}") + "%"


def pct1(v):
    """A percentage to one decimal place, for a figure that sits close to its target."""
    return _style(f"{v * 100:.1f}") + "%"


def pct2(v):
    """A fee rate to two decimal places, trailing zeros dropped, so it matches the workbook and the memory file."""
    s = f"{v * 100:.2f}".rstrip("0").rstrip(".")
    return _style(s) + "%"


def pct_vs(x, ref):
    """A percentage shown to one decimal place when whole-number rounding would make it look equal to ref."""
    return pct1(x) if pct(x) == pct(ref) and abs(x - ref) > 1e-9 else pct(x)


def a_an(pct_text):
    """'An 11% rise', 'An 80% rise', 'A 17% rise'."""
    return "An" if re.match(r"8", pct_text) or re.match(r"1[18](\D|$)", pct_text) else "A"


def hours(v):
    if v is None:
        return "[NEED]"
    v = math.floor(v * 10 + 0.5 + 1e-9) / 10
    return fmt_plain(v, 0 if abs(v - round(v)) < 0.05 else 1)


# ------------------------------------------------------------------ normalise inputs
def _nonneg(v, label, needs):
    if v is not None and v < 0:
        needs.append(f"{label}: cannot be negative (check how it was written)")
        return None
    return v


def validate_shape(raw):
    """Stop early, in plain words, on an inputs file the calculator cannot read."""
    if not isinstance(raw, dict):
        raise InputError("the inputs file must be one JSON object with an 'offers' list, not a list or a single value")
    offers = raw.get("offers")
    if not isinstance(offers, list) or not offers:
        raise InputError("the inputs need an 'offers' list with at least one offer (a name and what one client pays)")
    for i, o in enumerate(offers):
        if not isinstance(o, dict):
            raise InputError(f"offer {i + 1} must be a set of named fields (name, price, your_hours), not '{o}'")
    if raw.get("sources") is not None and not isinstance(raw["sources"], dict):
        raise InputError("'sources' must be a set of named fields")


def pay_basis(v):
    s = str(v or "").lower()
    if not s:
        return None
    if re.search(r"take[- ]?home|after[- ]tax|net|in my pocket|in hand", s):
        return "after tax"
    if re.search(r"before tax|pre[- ]?tax|gross", s):
        return "before tax"
    return None


def normalise(raw):
    validate_shape(raw)
    notes, needs = [], []
    src = raw.get("sources") or {}
    biz = {}

    def put(key, value, source):
        biz[key] = value
        biz[key + "_src"] = source

    src = {k: (DEFAULTS["target_margin"][1] if "Merigrove practice" in str(v) else v) for k, v in src.items()}
    put("business", str(raw.get("business") or "Your business"), src.get("business", "founder said"))
    global DAY_HOURS
    cur = str(raw.get("currency") or "").upper().strip()
    cur = {"£": "GBP", "€": "EUR", "A$": "AUD", "S$": "SGD", "C$": "CAD", "NZ$": "NZD", "HK$": "HKD", "US$": "USD",
           "₹": "INR", "R$": "BRL", "₱": "PHP"}.get(cur, cur)
    country = re.sub(r"[^A-Z]", "", str(raw.get("country") or "").upper())[:2]
    if cur == "$" and country in DOLLAR_COUNTRIES:
        cur = DOLLAR_COUNTRIES[country]
        src.setdefault("currency", f"a bare $ read as {cur} because you are in {country}; say if not")
    if cur in ("", "$"):
        needs.append("Currency: which currency your prices are in" + (" (which dollars: US, Australian, Singapore or "
                     "another)" if cur == "$" else "") + "; figures show without a symbol until you say")
        cur = ""
    put("currency", cur, src.get("currency", "founder said") if cur else "[NEED] not given")
    put("country", country, src.get("country", "founder said") if country else "not given")
    place = ln.locale_defaults(country)
    PLACE.update(paper=place["paper"], date_order=place["date_order"], assumed=place["assumed"])
    put("paper", place["paper"], f"from your country ({country})" if country else
        "your country was not given, so A4 paper and day-month dates; say where you are and they follow it")
    put("date_order", place["date_order"], biz["paper_src"])
    dec, dec_src = set_style(raw, cur)
    put("decimal", dec, src.get("decimal", dec_src))
    d = str(raw.get("date") or "")
    put("date", d if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d) else date.today().isoformat(), "run date")
    loc = str(raw.get("locale") or ("en-US" if country == "US" else "en-GB"))
    put("locale", loc, "founder's own English" if raw.get("locale") else "default")
    dh = to_num(raw.get("day_hours"), None, "Hours in your working day")
    DAY_HOURS = dh if dh and 0 < dh <= 24 else 8.0
    put("day_hours", DAY_HOURS, src.get("day_hours", "founder said") if (dh and 0 < dh <= 24)
        else "assumption: a working day of 8 hours when time is given in days; set your own")
    pin = re.sub(r"\s+", " ", str(raw.get("pinned_line") or "")).strip()
    put("pinned_line", pin, "founder asked for it at the top of the summary" if pin else "not given")
    conf = raw.get("confirmed") or []
    conf = [c.strip() for c in (conf.split(";") if isinstance(conf, str) else conf) if str(c).strip()]
    put("confirmed", conf, "founder confirmed" if conf else "none")

    # the founder's hour: a stated rate, or worked out from the pay they want
    pay = _nonneg(to_num(raw.get("target_pay_year"), notes, "Pay you want a year"), "Pay you want a year", needs)
    ych = _nonneg(to_num(raw.get("your_client_hours_week"), notes, "Your client hours a week", True),
                  "Your client hours a week", needs)
    wk_given = to_num(raw.get("working_weeks_year"), notes, "Working weeks a year")
    wks = wk_given if (wk_given is not None and 0 < wk_given <= 52) else WORKING_WEEKS
    basis = pay_basis(raw.get("target_pay_basis"))
    put("target_pay_year", pay, src.get("target_pay_year", "founder said") if pay else "not given")
    put("your_client_hours_week", ych, src.get("your_client_hours_week", "founder said") if ych else "not given")
    put("stated_client_hours_week", ych, "founder said" if ych else "not given")
    if wk_given is not None and wks != wk_given:
        needs.append(f"Working weeks a year: {fmt_plain(wk_given, 2)} cannot be right (it must be between 1 and 52); "
                     "the floors use 46 until you set it")
    put("working_weeks", wks, src.get("working_weeks_year", "founder said") if wks == wk_given else WEEKS_SRC)
    put("target_pay_basis", basis, src.get("target_pay_basis", "founder said") if basis else "not asked")
    r = _nonneg(to_num(raw.get("your_rate"), notes, "Your hourly rate"), "Your hourly rate", needs)
    rate_from_pay = False
    stated_check = None  # a stated rate beside after-tax pay: checked against the hour that pay needs, below
    if r is not None and r > 0 and pay and ych and basis == "after tax":
        stated_check = r
        rate_from_pay = True
        put("your_rate", pay / (ych * wks), "")
    elif r is not None and r > 0:
        put("your_rate", r, src.get("your_rate", "founder said"))
    elif pay and ych:
        rate_from_pay = True
        put("your_rate", pay / (ych * wks), "")  # source written once the hours are settled, below
    elif pay and not r:
        rate_from_pay = True  # hours a week not given: taken from the offers below when every offer has volumes
        put("your_rate", DEFAULTS["your_rate"][0], "")
    else:
        put("your_rate", DEFAULTS["your_rate"][0], DEFAULTS["your_rate"][1])
        needs.append("Your hourly rate: what an hour of your time is worth (the floor uses a placeholder of 60 until you set it)")

    tm = to_pct(raw.get("target_margin"), notes, "Target buffer", limit=0.9)
    if tm is None:
        put("target_margin", DEFAULTS["target_margin"][0], DEFAULTS["target_margin"][1])
    else:
        put("target_margin", tm, src.get("target_margin", "founder said"))

    oh = _nonneg(to_num(raw.get("overheads_month"), notes, "Monthly overheads"), "Monthly overheads", needs)
    if oh is None:
        needs.append("Monthly overheads: business costs not tied to one client (software, insurance, accountant, phone, premises), excluding your own pay. Floors below carry no overhead share until you add them")
        put("overheads_month", 0.0, "[NEED] not given; set to 0, so floors are understated")
    else:
        put("overheads_month", oh, src.get("overheads_month", "founder said"))

    def fee_for(fee_v, paid_v, share_v, label, fallback, price=None):
        fixed = split_fixed_fee(fee_v)
        if fixed:
            pr = to_pct(fixed[0], notes, label, limit=0.9)
            fx = fixed_part(fixed[1], label)
            fr = pr + (fx / price if (price and fx) else 0.0)
            how = (f"{fixed[0].strip()} plus {fixed[1].strip()} a payment, worked out on this price" if price
                   else f"{fixed[0].strip()} plus {fixed[1].strip()} a payment, worked out per offer")
        else:
            fr = to_pct(fee_v, notes, label, limit=0.9)
            how = None
        if fr is not None:
            share = to_pct(share_v, notes, f"{label} card share", limit=1.01)
            base_src = src.get("fee_rate", "founder said") if fallback is None else "founder said"
            if how:
                base_src = f"{how}, {base_src}"
            if share is not None and 0 < share < 1:
                return fr * share, f"{base_src}, on the {pct(share)} of payments made by card"
            return fr, base_src
        share = to_pct(share_v, notes, f"{label} card share", limit=1.01)
        if share is not None and share > 0:
            return DEFAULTS["fee_card"][0] * share, f"{pct(share)} paid by card at the {pct(DEFAULTS['fee_card'][0])} card default"
        fv, fs = fee_from_paid_by(paid_v)
        if fv is not None:
            return fv, f"clients pay by {paid_v}, so {fs}"
        if fallback is not None:
            return fallback
        return DEFAULTS["fee_card"][0], card_default_src()

    fee_global, fee_g_src = fee_for(raw.get("fee_rate"), raw.get("paid_by"), raw.get("card_share"), "Payment fee rate", None)
    put("fee_rate", fee_global, fee_g_src)
    put("paid_by", raw.get("paid_by"), "founder said" if raw.get("paid_by") else "not given")
    if fee_global > 0.10:
        notes.append(f"Payment fee rate: {pct(fee_global)} is high for card fees; check it")

    rl = to_pct(raw.get("rescope_limit"), limit=0.9)
    put("rescope_limit", rl if rl is not None else DEFAULTS["rescope_limit"][0],
        src.get("rescope_limit", "founder said") if rl is not None else DEFAULTS["rescope_limit"][1])
    fh = _nonneg(to_num(raw.get("full_hours_week"), notes, "Client hours a week if you were full", True),
                 "Client hours a week if you were full", needs)
    put("full_hours_week", fh, src.get("full_hours_week", "founder said") if fh else "not given")

    offers = []
    for i, o in enumerate(raw["offers"]):
        name = re.sub(r"\s+", " ", str(o.get("name") or f"Offer {i + 1}")).strip()
        lab = name
        off = {"name": name, "billing": billing_of(o.get("billing") or o.get("price"))}
        off["unit"] = "a month" if off["billing"] == "monthly" else "each"
        off["each"] = "each month" if off["billing"] == "monthly" else "each time it sells"
        if o.get("unit_label"):
            off["unit"] = str(o["unit_label"])
        price = _nonneg(to_num(o.get("price"), notes, f"{lab} price", price_field=True), f"{lab} price", needs)
        off["price"] = price
        if price is None or price <= 0:
            needs.append(f"{lab}: what one client pays")
        yh = _nonneg(to_num(o.get("your_hours"), notes, f"{lab} your hours", True), f"{lab} your hours", needs)
        if yh is None and not any(n.startswith(f"{lab} your hours") for n in needs):
            needs.append(f"{lab}: roughly how many hours it takes you, including calls, admin and revisions")
        off["your_hours"] = yh
        off["team_hours"] = _nonneg(to_num(o.get("team_hours"), notes, f"{lab} team hours", True), f"{lab} team hours", needs) or 0.0
        tr = _nonneg(to_num(o.get("team_rate"), notes, f"{lab} team cost an hour"), f"{lab} team cost an hour", needs)
        if off["team_hours"] > 0 and tr is None:
            needs.append(f"{lab}: what an hour of your team member's time costs you")
        off["team_rate"] = tr or 0.0
        off["contractor"] = _nonneg(to_num(o.get("contractor"), notes, f"{lab} contractor cost"), f"{lab} contractor cost", needs) or 0.0
        off["tools"] = _nonneg(to_num(o.get("tools"), notes, f"{lab} tools and other costs"), f"{lab} tools", needs) or 0.0
        g_fixed = split_fixed_fee(raw.get("fee_rate")) and not (o.get("fee_rate") or o.get("paid_by"))
        if g_fixed:  # a fee with a fixed part per payment depends on each offer's price
            fr, fsrc = fee_for(raw.get("fee_rate"), None, o.get("card_share", raw.get("card_share")),
                               f"{lab} payment fee", None, price)
        else:
            fr, fsrc = fee_for(o.get("fee_rate"), o.get("paid_by"), o.get("card_share"), f"{lab} payment fee",
                               (fee_global, "business default"), price)
        off["fee_rate"], off["fee_src"] = fr, fsrc
        off["refund_rate"] = to_pct(o.get("refund_rate"), notes, f"{lab} refunds", limit=0.9) or 0.0
        off["per_month"] = _nonneg(to_num(o.get("per_month"), notes, f"{lab} sales a month"), f"{lab} sales a month", needs)
        off["alternative"] = to_num(o.get("alternative"), notes, f"{lab} alternative", price_field=True)
        off["proposed"] = to_num(o.get("proposed"), notes, f"{lab} test price", price_field=True)
        plan = parse_plan(o.get("instalments"), f"{lab} instalments")
        off["plan_total"] = plan[0] * plan[1] if plan else to_num(o.get("plan_total"), None, f"{lab} plan total")
        off["plan_text"] = str(o.get("instalments") or "")
        off["notes"] = str(o.get("notes") or "")
        pref = str(o.get("prefer") or "").strip().lower()
        off["prefer"] = "raise" if pref.startswith(("raise", "price", "subir")) else (
            "restructure" if pref.startswith(("restruct", "hours", "cut", "trim")) else "")
        offers.append(off)
    for off in offers:
        if (1 - off["refund_rate"]) * (1 - biz["target_margin"]) - off["fee_rate"] <= 0:
            raise InputError(f"{off['name']}: the payment fee, refunds and buffer together leave nothing to cover costs. "
                             "Check those three figures and run again")

    # the hours the offers use, per working week, against the hours the founder gave (when the hour comes from pay)
    vols = all(o.get("per_month") is not None and o["your_hours"] is not None for o in offers)
    offer_hours = sum(o["your_hours"] * o["per_month"] for o in offers) * 12 / wks if vols else None
    put("offer_hours_week", offer_hours, "your hours per sale times sales a month, over your working weeks")
    if rate_from_pay and not ych:
        if offer_hours:
            ych = offer_hours
            biz["stated_client_hours_week"] = None
            put("your_client_hours_week", ych, "worked out from your offers: your hours per sale times sales a month, "
                "over your working weeks")
        else:
            rate_from_pay = False
            put("your_rate", DEFAULTS["your_rate"][0], DEFAULTS["your_rate"][1])
            needs.append("Your client hours a week: needed to turn the pay you want into an hour (the floor uses a "
                         "placeholder of 60 until you give it, or give how many of each offer you sell a month)")
    if rate_from_pay:
        used, why = ych, (f"your {hours(ych)} client hours a week" if biz.get("stated_client_hours_week")
                          else f"the {hours(ych)} client hours a week your offers use at these volumes")
        if offer_hours and abs(offer_hours - ych) > HOURS_GAP * ych and HOURS_OK in biz["confirmed"]:
            why += f", which you confirmed though your offers use {hours(offer_hours)} at these volumes"
        elif offer_hours and abs(offer_hours - ych) > HOURS_GAP * ych:
            if offer_hours < ych:
                used = offer_hours
                why = (f"{hours(offer_hours)} client hours a week, the hours your offers use at these volumes, lower than "
                       f"the {hours(ych)} you gave, so the floors err safe")
                needs.append(f"Your client hours: you gave {hours(ych)} a week, but at these volumes your offers use "
                             f"{hours(offer_hours)}. Your hour is priced on {hours(offer_hours)}, so the offers fund the "
                             f"pay you want. Which is right? If the other {hours(ych - offer_hours)} are client work no "
                             f"offer pays for (add \"{HOURS_OK}\" to confirmed), the hour is priced on all {hours(ych)} "
                             "and the whole-business line shows the gap")
            else:
                needs.append(f"Your client hours: you gave {hours(ych)} a week, but at these volumes your offers need "
                             f"{hours(offer_hours)}. Your hour is priced on the {hours(ych)} you gave. Which is right? "
                             "Either the hours per offer are high, or you work longer than you think (if so, give the "
                             f"longer week; if {hours(ych)} is right, add \"{HOURS_OK}\" to confirmed)")
        biz["your_client_hours_week"] = used
        if used != ych:
            biz["your_client_hours_week_src"] = "worked out from your offers: " + why
        biz["your_rate"] = pay / (used * wks)
        biz["your_rate_src"] = f"worked out from {money(pay, cur)} a year over {fmt_plain(wks)} working weeks and {why}"
        biz["pay_hour"] = biz["your_rate"]
        if stated_check is not None and stated_check >= biz["your_rate"] - 1e-9:
            rate_from_pay = False  # the founder's own rate already funds the after-tax pay before any tax
            needs[:] = [n for n in needs if not n.startswith("Your client hours:")]
            biz["your_client_hours_week"] = ych
            biz["your_client_hours_week_src"] = src.get("your_client_hours_week", "founder said")
            biz["your_rate"] = stated_check
            biz["your_rate_src"] = (src.get("your_rate", "founder said") + f"; at or above the {money(biz['pay_hour'], cur)} "
                                    f"an hour that {money(pay, cur)} after tax needs before any tax")
        elif stated_check is not None:
            biz["stated_rate_below"] = stated_check
            biz["your_rate_src"] += (f". The {money(stated_check, cur)} you gave ({src.get('your_rate', 'founder said')}) "
                                     f"is below this, so it could not fund {money(pay, cur)} after tax even before any "
                                     "tax; the floors use the higher figure")
        if basis == "after tax" and rate_from_pay:
            routes = ("the before-tax figure from your accountant, or what you paid yourself last year before any tax, "
                      "from your accounts" if stated_check is not None else
                      "what you would pay someone capable to do your part an hour; the before-tax figure from your "
                      "accountant; or what you paid yourself last year before any tax, from your accounts")
            needs.append(f"Pay before tax: the {money(pay, cur)} you gave is after tax. The Raise verdicts stand (a "
                         "before-tax figure can only lift a floor); Hold and Restructure are provisional. To settle them, "
                         f"give one of: {routes}. This calculator never estimates tax")
        elif basis is None:
            needs.append(f"Pay before or after tax: the floors read {money(pay, cur)} as before tax. If it is what you want "
                         "after tax, ask your accountant for the before-tax figure and run again")
    ych = biz["your_client_hours_week"]

    chw = to_num(raw.get("client_hours_week"), notes, "Client hours a week", True)
    team_month = [o["team_hours"] * o["per_month"] for o in offers if o["team_hours"] and o.get("per_month") is not None]
    team_known = all(o.get("per_month") is not None for o in offers if o["team_hours"])
    biz["client_hours_formula"] = None
    if chw is not None and chw > 0:
        put("client_hours_week", chw, src.get("client_hours_week", "founder said"))
    elif ych and team_known:
        team_week = sum(team_month) * 12 / wks
        put("client_hours_week", ych + team_week,
            (f"the {hours(ych)} client hours a week your offers use" if biz.get("your_client_hours_week_src", "").startswith(
                "worked out") else f"your {hours(ych)} client hours a week")
            + (f" plus {hours(team_week)} team hours worked out from the offers"
                                                            if team_week else ""))
        biz["client_hours_formula"] = "yours plus team"
    elif offers and all(o.get("per_month") is not None for o in offers) and \
            sum(((o["your_hours"] or 0) + o["team_hours"]) * o["per_month"] for o in offers) > 0:
        per_month = sum(((o["your_hours"] or 0) + o["team_hours"]) * o["per_month"] for o in offers)
        put("client_hours_week", per_month * 12 / wks, "worked out from your hours per sale and sales a month")
        biz["client_hours_formula"] = "all from offers"
    else:
        v, s_ = DEFAULTS["client_hours_week"]
        put("client_hours_week", v, s_)
    biz["rate_from_pay"] = rate_from_pay
    biz["hours_from_offers"] = rate_from_pay and biz["your_client_hours_week"] != biz["stated_client_hours_week"]
    return biz, offers, notes, needs


# ------------------------------------------------------------------ the arithmetic (mirrors the workbook)
def step_for(x):
    return 10 if x < 500 else (50 if x < 2000 else (100 if x < 10000 else 500))


def roundup(x, step):
    return math.ceil(round(x / step, 9)) * step


def contribution_at(o, price, rate, scale=1.0):
    """Contribution per sale at a price: net revenue less every direct cost (your time included)."""
    return (price * (1 - o["refund_rate"]) - price * o["fee_rate"] - o["contractor"] - o["tools"]
            - scale * o["team_hours"] * o["team_rate"] - scale * (o["your_hours"] or 0) * rate)


def cash_left_at(o, price):
    """Cash one sale leaves at a price, before your time and overheads."""
    return price * (1 - o["refund_rate"]) - price * o["fee_rate"] - o["contractor"] - o["tools"] - o["team_hours"] * o["team_rate"]


def business_view(biz, offers, rows):
    """The whole business at the volumes given: sales, and what is left for the founder before tax."""
    done = [(o, r) for o, r in zip(offers, rows) if r["complete"]]
    if not done or any(o.get("per_month") is None for o, _r in done) or len(done) < len(offers):
        return None
    sales_m = sum(o["price"] * o["per_month"] for o, _r in done)
    left_m = sum(r["cash_left"] * o["per_month"] for o, r in done) - biz["overheads_month"]
    rec_m = sum(r["rec_price"] * o["per_month"] for o, r in done)
    raise_m = sum(r["raise_price"] * o["per_month"] for o, r in done)
    hours_m = sum((o["your_hours"] or 0) * o["per_month"] for o, _r in done)
    target = biz.get("target_pay_year")
    target_src = "the pay you want" if target else None
    if not target:
        target = hours_m * 12 * biz["your_rate"]
        target_src = "your client hours at your rate"
    return {"sales_month": sales_m, "sales_year": sales_m * 12, "left_month": left_m, "left_year": left_m * 12,
            "sales_year_rec": rec_m * 12, "sales_year_raise": raise_m * 12,
            "your_hours_week": hours_m * 12 / biz["working_weeks"],
            "target_year": target, "target_src": target_src, "versus_target": left_m * 12 - target}


def compute(biz, offers):
    rate, m = biz["your_rate"], biz["target_margin"]
    wpm = biz["working_weeks"] / 12  # working weeks a month: overheads are paid every month, client hours only happen
    chm = biz["client_hours_week"] * wpm  # in the weeks the founder works
    oh_hr = biz["overheads_month"] / chm if chm > 0 else 0.0
    oh_full = None
    if biz.get("full_hours_week"):
        oh_full = biz["overheads_month"] / (biz["full_hours_week"] * wpm)
    out = {"oh_per_hour": oh_hr, "client_hours_month": chm, "oh_per_hour_full": oh_full, "offers": []}
    for o in offers:
        r = {"name": o["name"], "complete": o["price"] not in (None, 0) and o["your_hours"] is not None}
        out["offers"].append(r)
        if not r["complete"]:
            r["verdict"] = "Need inputs"
            if o["your_hours"] is not None:
                # no price yet: the floor does not depend on the price, so it is still worked out (a fixed fee part,
                # which does, is left out until the price is known)
                d1 = (1 - o["refund_rate"]) * (1 - m) - o["fee_rate"]
                d0 = (1 - o["refund_rate"]) - o["fee_rate"]
                t = o["your_hours"] + o["team_hours"]
                base = (o["contractor"] + o["tools"] + o["team_hours"] * o["team_rate"] + o["your_hours"] * rate
                        + t * oh_hr)
                r["floor_only"] = base / d1 if d1 > 0 else None
                r["cost_floor_only"] = base / d0 if d0 > 0 else None
            continue
        P, yh, th = o["price"], o["your_hours"], o["team_hours"]
        rr, f = o["refund_rate"], o["fee_rate"]
        r["net"] = P * (1 - rr)
        r["fees"] = P * f
        r["team_cost"] = th * o["team_rate"]
        r["cash_costs"] = r["fees"] + o["contractor"] + o["tools"] + r["team_cost"]
        r["your_time"] = yh * rate
        r["direct"] = r["cash_costs"] + r["your_time"]
        r["contribution"] = r["net"] - r["direct"]
        r["cmargin"] = r["contribution"] / r["net"] if r["net"] else None
        r["overhead_share"] = (yh + th) * oh_hr
        r["full_cost"] = r["direct"] + r["overhead_share"]
        base = r["full_cost"] - r["fees"]  # every cost that does not move with the price
        d0 = (1 - rr) - f
        d1 = (1 - rr) * (1 - m) - f
        r["cost_floor"] = base / d0 if d0 > 0 else None
        r["price_floor"] = base / d1 if d1 > 0 else None
        r["gap"] = r["price_floor"] - P if r["price_floor"] is not None else None
        r["real_margin"] = (r["net"] - r["full_cost"]) / r["net"] if r["net"] else None
        r["loss_per_sale"] = r["net"] - r["full_cost"]
        r["eff_rate"] = (r["net"] - r["cash_costs"] - r["overhead_share"]) / yh if yh > 0 else None
        r["eff_rate_before_oh"] = (r["net"] - r["cash_costs"]) / yh if yh > 0 else None
        time_unit = yh * rate + th * o["team_rate"] + (yh + th) * oh_hr
        r["k"] = ((r["net"] * (1 - m) - r["fees"] - o["contractor"] - o["tools"]) / time_unit) if time_unit > 0 else None
        r["cut"] = (1 - r["k"]) if r["k"] is not None else None
        pfl, cfl = r["price_floor"], r["cost_floor"]
        r["at_floor"] = False
        if pfl is not None and P >= pfl - 1e-9:
            v = "Hold"
        elif pfl is not None and P >= AT_FLOOR * pfl and (cfl is None or P >= cfl - 1e-9):
            v, r["at_floor"] = "Hold", True  # within 5% of the floor: a restructure this small is noise
        elif o.get("prefer") == "raise":
            v = "Raise"
        elif r["k"] is not None and r["k"] > 0 and (o.get("prefer") == "restructure"
                                                     or r["cut"] <= biz["rescope_limit"] + 1e-9):
            v = "Restructure"
        else:
            v = "Raise"
        r["verdict"] = v
        # pay given after tax: a before-tax figure can only lift the floor, so Raise stands and the rest wait
        r["provisional"] = bool(biz.get("rate_from_pay") and biz.get("target_pay_basis") == "after tax" and v != "Raise")
        r["below_cost"] = r["cost_floor"] is not None and P < r["cost_floor"] - 1e-9
        pf = r["price_floor"]
        r["step"] = step_for(pf) if pf else None
        # option A, the rise to the floor, is worked out for every offer below its floor
        r["raise_price"] = roundup(pf, r["step"]) if (pf and P < pf) else P
        r["rec_price"] = r["raise_price"] if v == "Raise" else P
        r["rise"] = r["raise_price"] / P - 1
        r["c_now"] = r["contribution"]
        r["c_rec"] = contribution_at(o, r["raise_price"], rate)
        r["be_loss"] = None if r["c_rec"] <= 0 else (None if r["c_now"] <= 0 else (r["c_rec"] - r["c_now"]) / r["c_rec"])
        r["be_any"] = r["c_now"] <= 0 < r["c_rec"]
        # the plain cash view: what one sale leaves before your time and overheads
        r["cash_left"] = r["net"] - r["cash_costs"]
        r["cash_rec"] = cash_left_at(o, r["raise_price"])
        r["be_cash"] = (r["cash_rec"] - r["cash_left"]) / r["cash_rec"] if r["cash_rec"] > 0 else None
        # middle path: half the rise in price, the rest from hours
        if pf and P < pf:
            raise_to = roundup(pf, step_for(pf))
            mid = roundup(P + (raise_to - P) / 2, step_for(P + (raise_to - P) / 2))
            if mid >= raise_to:
                mid = None
        else:
            mid = None
        r["mid_price"] = mid
        if mid and time_unit > 0:
            km = (mid * (1 - rr) * (1 - m) - mid * f - o["contractor"] - o["tools"]) / time_unit
            r["mid_k"], r["mid_cut"] = km, 1 - km
        else:
            r["mid_k"] = r["mid_cut"] = None
        r["rate_down"] = (base - r["your_time"] * 0.25) / d1 if d1 > 0 else None
        if after_tax(biz) and d1 > 0 and biz.get("your_client_hours_week"):
            # what each extra step of before-tax pay adds to this floor: the founder plugs in their accountant's figure
            r["floor_per_step"] = yh * pay_step(biz) / (biz["your_client_hours_week"] * biz["working_weeks"]) / d1
        r["rate_up"] = (base + r["your_time"] * 0.25) / d1 if d1 > 0 else None
        if oh_full is not None and d1 > 0:
            r["floor_full"] = (base - r["overhead_share"] + (yh + th) * oh_full) / d1
        else:
            r["floor_full"] = None
        vol = o.get("per_month")
        r["monthly_gain_rec"] = (r["c_rec"] - r["c_now"]) * vol if vol else None
        r["monthly_shortfall"] = (pf - P) * (1 - rr) * vol if (vol and pf and P < pf) else None
        if o.get("proposed"):
            cp = contribution_at(o, o["proposed"], rate)
            r["c_prop"] = cp
            r["be_prop"] = None if (cp <= 0 or r["c_now"] <= 0) else (cp - r["c_now"]) / cp
            cc = cash_left_at(o, o["proposed"])
            r["be_prop_cash"] = (cc - r["cash_left"]) / cc if cc > 0 else None
        if o.get("plan_total"):
            r["plan_ok"] = o["plan_total"] > P
        r["alt_gap"] = (o["alternative"] - pf) if (o.get("alternative") and pf) else None
    out["business"] = business_view(biz, offers, out["offers"])
    return out


# ------------------------------------------------------------------ plain-English reasoning
BUFFER_LINE = ("The buffer is what an offer keeps after every cost and your pay: it carries you through quiet months, "
               "tax bills and holidays.")


def after_tax(biz):
    return bool(biz.get("rate_from_pay") and biz.get("target_pay_basis") == "after tax")


def pay_step(biz):
    """A round step of pay, about a tenth of the pay given, for the before-tax sensitivity line."""
    pay = biz.get("target_pay_year") or 0
    if pay <= 0:
        return 0
    x = pay * 0.1
    mag = 10 ** math.floor(math.log10(x))
    return round(x / mag) * mag


def sensitivity_line(biz, offers, res):
    """Each step of before-tax pay above the after-tax figure, and what it adds to each floor. Not a tax estimate."""
    cur, stp = biz["currency"], pay_step(biz)
    parts = [f"{o['name']} {money(r['floor_per_step'], cur)}" for o, r in zip(offers, res["offers"])
             if r.get("complete") and r.get("floor_per_step") is not None]
    if not parts or not stp:
        return ""
    return (f"Every {money(stp, cur)} a year that your before-tax figure sits above {money(biz['target_pay_year'], cur)} "
            "adds to each floor: " + "; ".join(parts) + ". Your accountant can give you the before-tax figure; this is "
            "not a tax estimate.")


def verdict_label(r):
    if not r.get("complete"):
        return "Need inputs"
    v = r["verdict"] + (", at the floor" if r.get("at_floor") else "")
    return v + (" (provisional)" if r.get("provisional") else "")


def plausibility(biz, offers, res):
    """Stop with one plain question on a headline figure that cannot be right, usually a misread number."""
    cur, conf, rate = biz["currency"], set(biz.get("confirmed") or []), biz["your_rate"]
    checks = []
    src = biz.get("your_rate_src", "")
    per_hour = [o["price"] / o["your_hours"] for o in offers if o.get("price") and o.get("your_hours")]
    if rate < 1:
        checks.append(("hour", f"your hour works out at {money(rate, cur)} ({src})",
                       f"Your hour works out at {money(rate, cur)}. Is the pay figure, or the hours, written the way you "
                       "meant?"))
    elif per_hour and rate > 20 * max(per_hour):
        checks.append(("hour", f"your hour of {money(rate, cur)} is over 20 times what any offer charges for an hour of "
                               "your time", f"Is {money(rate, cur)} an hour right for your time?"))
    for o in offers:
        P, hrs = o.get("price"), (o.get("your_hours") or 0) + (o.get("team_hours") or 0)
        if P and (P < 10 or (hrs and P / hrs < 1)):
            checks.append((f"price: {o['name']}", f"{o['name']} reads as {money(P, cur)}"
                           + (f" for {hours(hrs)} hours of work" if hrs else ""),
                           f"Does one client really pay {money(P, cur)} for {o['name']}?"))
    if biz["overheads_month"] > 0 and res["oh_per_hour"] > rate:
        checks.append(("overheads", f"overheads of {money(biz['overheads_month'], cur)} a month come to "
                                    f"{money(res['oh_per_hour'], cur)} for every client hour, above your hour of "
                                    f"{money(rate, cur)}",
                       f"Are your running costs really {money(biz['overheads_month'], cur)} a month, leaving out your "
                       "own pay?"))
    if biz["client_hours_week"] > 80:
        checks.append(("client hours over 80", f"client hours of {hours(biz['client_hours_week'])} a week",
                       f"Is {hours(biz['client_hours_week'])} client hours a week right, counting anyone whose hours "
                       "are costed?"))
    for key, what, q in checks:
        if key not in conf:
            raise AskError(f"{what}, which looks like a misread figure. If the founder confirms it, add \"{key}\" to "
                           "\"confirmed\" in the inputs file and run again", q)


def pays_phrase(r, biz):
    cur, rate, eff = biz["currency"], biz["your_rate"], r["eff_rate"]
    if eff is None:
        return "none of your own hours go into it"
    if eff >= rate:
        return (f"it pays you {money(eff, cur)} an hour once costs and its share of overheads are paid, "
                f"above the {money(rate, cur)} your time is worth")
    return (f"it pays you {money(eff, cur)} an hour once costs and its share of overheads are paid, "
            f"against the {money(rate, cur)} your time is worth")


FLOOR_TAIL = " The floor is the least it can charge, not what it is worth."
PROVISIONAL_LINE = " Provisional: your pay figure is after tax, and a before-tax figure lifts this floor."


def reasoning(o, r, biz):
    cur, rate = biz["currency"], biz["your_rate"]
    if not r["complete"]:
        return f"Not worked out yet: {o['name']} needs a price and your hours."
    P, pf = o["price"], r["price_floor"]
    unit = o["unit"]
    pays = pays_phrase(r, biz)
    prov = PROVISIONAL_LINE if r.get("provisional") else ""
    if r["verdict"] == "Hold" and r.get("at_floor"):
        return (f"Hold, at the floor{' (provisional)' if prov else ''}. At {money(P, cur)} {unit}, it sits {money(pf - P, cur)} below its floor of "
                f"{money(pf, cur)}, within 5%, so it keeps {a_an(pct1(r['real_margin'])).lower()} {pct1(r['real_margin'])} "
                f"buffer rather than your {pct(biz['target_margin'])}, and {pays}. A change this small is not worth "
                "reshaping the offer for; look at it again at your next price change." + prov)
    if r["verdict"] == "Hold":
        head = (f"Hold{' (provisional)' if prov else ''}. At {money(P, cur)} {unit}, it clears its floor of {money(pf, cur)} by "
                f"{money(P - pf, cur)}, and {pays}.")
        return head + prov + FLOOR_TAIL
    lead = f"{r['verdict']}{' (provisional)' if prov else ''}. At {money(P, cur)} {unit}, {pays}."
    if r["below_cost"]:
        lead += (f" It falls {money(-r['loss_per_sale'], cur)} short of its full cost {o['each']}, with your time "
                 f"counted at {money(rate, cur)} an hour.")
    else:
        lead += (f" It covers every cost, your time included, but keeps {a_an(pct(r['real_margin'])).lower()} {pct(r['real_margin'])} buffer rather than your "
                 f"{pct(biz['target_margin'])}, so it sits {money(r['gap'], cur)} below the floor of {money(pf, cur)}.")
    if r["verdict"] == "Restructure":
        who = f"yours from {hours(o['your_hours'])} to {hours(o['your_hours'] * r['k'])}"
        if o["team_hours"]:
            who += f", your team's from {hours(o['team_hours'])} to {hours(o['team_hours'] * r['k'])}"
        lead += f" Cutting the hours by {pct(r['cut'])} ({who}) closes the gap without touching the price."
        if r["cut"] > biz["rescope_limit"] + 1e-9:
            lead += (f" That is beyond the {pct(biz['rescope_limit'])} a restructure usually takes, which you chose over "
                     "a raise.")
        return lead + prov
    if o.get("prefer") == "raise" and r["k"] is not None and r["k"] > 0 and r["cut"] <= biz["rescope_limit"] + 1e-9:
        why = f"You chose a raise over cutting the hours (a {pct(r['cut'])} cut would also close it)"
    elif r["cut"] is not None and r["k"] is not None and r["k"] > 0:
        why = (f"Trimming hours would need a {pct_vs(r['cut'], biz['rescope_limit'])} cut, beyond the "
               f"{pct(biz['rescope_limit'])} a restructure can take without changing the offer")
    else:
        why = "No cut in hours can close a gap this size"
    if after_tax(biz):
        return lead + (f" {why}, so the price moves to at least {money(r['rec_price'], cur)} {unit} for new clients, "
                       "because a before-tax pay figure can only lift the floor.")
    return lead + f" {why}, so the price moves: {money(r['rec_price'], cur)} {unit} for new clients."


def loss_lines(r, biz, be, be_any, be_cash, vol=None):
    """The client-loss test: plain cash first, then freed hours, which count only if they are refilled."""
    cur, rate = biz["currency"], money(biz["your_rate"], biz["currency"])
    a = ""
    if be_cash is not None and be_cash > 0:
        a = (f"Break-even client loss in plain cash: {pct(be_cash)}. Lose a larger share of the clients on it and you "
             "take in less cash than today, until you refill the freed hours.")
    if vol is not None and vol < 2:
        return a  # with one sale or one client a month, a share of clients lost is not a useful line
    b = ""
    if be_any:
        b = (f"At today's price each client pays you less than your {rate} an hour, so a freed hour is worth your full "
             "rate, above what the client paid for it, but only if you refill it.")
    elif be is not None:
        b = (f"Counting each freed hour at your {rate}, the break-even loss is {pct(be)}, but only if you refill those "
             "hours at your rate.")
    return (a + " " + b).strip()


def volume_phrase(o):
    n = o["per_month"]
    if o["billing"] == "monthly":
        if abs(n - 1) < 1e-9:
            return "Keeping the one client on it"
        if abs(n - 2) < 1e-9:
            return "Keeping both clients on it"
        return f"Keeping all {fmt_plain(n)} clients on it" if float(n).is_integer() else f"Keeping the {fmt_plain(n)} clients a month on it"
    if abs(n - 1) < 1e-9:
        return "Selling one a month, as now"
    return f"Selling the same {fmt_plain(n)} a month"


def options(o, r, biz):
    """The price change options for an offer below its floor, recommended one first."""
    cur = biz["currency"]
    if not r["complete"] or r["verdict"] == "Hold":
        return []
    opts = []
    a = {"key": "A", "title": f"Raise to {money(r['raise_price'], cur)} {o['unit']}",
         "detail": (f"{a_an(pct(r['rise']))} {pct(r['rise'])} rise. What one sale leaves after every direct cost, your "
                    f"time included, goes from {money(r['c_now'], cur)} to {money(r['c_rec'], cur)} {o['each']}. "
                    + loss_lines(r, biz, r["be_loss"], r["be_any"], r["be_cash"], o.get("per_month"))).strip()}
    if r.get("monthly_gain_rec"):
        a["detail"] += f" {volume_phrase(o)}, cash in rises by {money(r['monthly_gain_rec'], cur)} a month."
    opts.append(a)
    if r["k"] is not None and r["k"] > 0:
        b = {"key": "B", "title": f"Keep {money(o['price'], cur)}, cut the hours by {pct_vs(r['cut'], biz['rescope_limit'])}",
             "detail": (f"Your hours go from {hours(o['your_hours'])} to {hours(o['your_hours'] * r['k'])}"
                        + (f" and your team's from {hours(o['team_hours'])} to {hours(o['team_hours'] * r['k'])}"
                           if o["team_hours"] else "") + ". Same price, fewer hours in each one.")}
        if r["cut"] > biz["rescope_limit"]:
            b["detail"] += f" A cut beyond {pct(biz['rescope_limit'])} usually changes what the client is buying."
        opts.append(b)
    if r.get("mid_price") and r.get("mid_cut") is not None and r["mid_cut"] >= 0.05:
        rise_c = pct(r["mid_price"] / o["price"] - 1)
        who = f"your hours from {hours(o['your_hours'])} to {hours(o['your_hours'] * r['mid_k'])}"
        if o["team_hours"]:
            who += f" and your team's from {hours(o['team_hours'])} to {hours(o['team_hours'] * r['mid_k'])}"
        opts.append({"key": "C", "title": f"Meet in the middle: {money(r['mid_price'], cur)} and {pct(r['mid_cut'])} fewer hours",
                     "detail": f"{a_an(rise_c)} {rise_c} rise, with {who}. A softer step for existing clients."})
    rec = None if r.get("provisional") else ("B" if r["verdict"] == "Restructure" else "A")
    opts.sort(key=lambda x: 0 if x["key"] == (rec or "B") else 1)
    for x in opts:
        x["recommended"] = x["key"] == rec
    return opts


def business_sentence(biz, res):
    bv, cur = res.get("business"), biz["currency"]
    if not bv:
        return ""
    if biz.get("target_pay_year") and biz.get("target_pay_basis") == "after tax":
        return (f"At these volumes the business leaves you {money(bv['left_year'], cur)} a year before tax. You gave "
                f"{money(bv['target_year'], cur)} after tax, so compare it with the before-tax figure your accountant gives you.")
    if biz.get("target_pay_year"):
        return (f"At these volumes the business leaves you {money(bv['left_year'], cur)} a year before tax, against the "
                f"{money(bv['target_year'], cur)} you want.")
    return (f"At these volumes the business leaves you {money(bv['left_year'], cur)} a year before tax, against "
            f"{money(bv['target_year'], cur)} for your client hours at your rate.")


def headline(biz, offers, res):
    s = " ".join(x for x in (business_sentence(biz, res), _headline(biz, offers, res)) if x)
    if biz["your_rate_src"].startswith("a placeholder"):
        s += (f" These floors use a placeholder of {money(biz['your_rate'], biz['currency'])} for your hour; "
              "set your own and they move.")
    if after_tax(biz):
        s += (" Your pay figure is after tax, so Hold and Restructure verdicts here are provisional; Raise verdicts "
              "stand, because a before-tax figure can only lift a floor.")
    return s


def _headline(biz, offers, res):
    cur = biz["currency"]
    done = [(o, r) for o, r in zip(offers, res["offers"]) if r["complete"]]
    if not done:
        return "Nothing worked out yet: each offer needs a price and your hours."
    below = [(o, r) for o, r in done if r["verdict"] != "Hold"]
    if not below:
        o, r = min(done, key=lambda x: x[0]["price"] - x[1]["price_floor"])
        if r.get("at_floor"):
            return (f"Every offer holds. Tightest: {o['name']}, {money(r['price_floor'] - o['price'], cur)} below its "
                    "floor, within 5%.")
        return (f"Every offer clears its floor. Tightest: {o['name']}, {money(o['price'] - r['price_floor'], cur)} above it.")
    o, r = max(below, key=lambda x: (x[1]["below_cost"], x[1]["gap"] / x[0]["price"]))
    n = len(below)
    lead = (f"{o['name']} is the one offer below its floor" if n == 1 else f"{o['name']} is the furthest below its floor")
    if r["eff_rate"] is not None and r["eff_rate"] < biz["your_rate"]:
        s = (f"{lead}: at {money(o['price'], cur)} it pays you {money(r['eff_rate'], cur)} an hour once costs and "
             f"overheads are paid, against the {money(biz['your_rate'], cur)} your time is worth.")
    elif r["eff_rate"] is not None:
        s = (f"{lead}: at {money(o['price'], cur)} it pays you {money(r['eff_rate'], cur)} an hour, above your "
             f"{money(biz['your_rate'], cur)}, but keeps {a_an(pct(r['real_margin'])).lower()} {pct(r['real_margin'])} buffer rather than your {pct(biz['target_margin'])}.")
    else:
        s = f"{lead}: at {money(o['price'], cur)} it sits {money(r['gap'], cur)} below its floor."
    if n > 1:
        s += ((" Both offers sit below their floor." if n == 2 else f" All {n} offers sit below their floor.") if n == len(done)
              else f" {n} of {len(done)} offers sit below their floor.")
    short = [r_["monthly_shortfall"] for _o, r_ in below if r_.get("monthly_shortfall")]
    if short and len(short) == n and not (n == 1 and abs(short[0] - r["gap"]) < 0.5):
        s += (f" At your current volume, lifting {'them to their floors' if n > 1 else 'it to its floor'} would add "
              f"{money(sum(short), cur)} a month.")
    return s


# ------------------------------------------------------------------ summary (markdown and html)
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]


def long_date(iso, order=None):
    """The date in the order the founder's country uses (from locale_defaults), never from their spelling."""
    order = order or PLACE["date_order"]
    try:
        y, m, d = (int(x) for x in iso.split("-"))
        if order == "MDY":
            return f"{MONTHS[m - 1]} {d}, {y}"
        if order == "YMD":
            return f"{y}-{m:02d}-{d:02d}"
        return f"{d} {MONTHS[m - 1]} {y}"
    except Exception:  # noqa: BLE001
        return iso


def cell_text(x):
    return str(x).replace("|", "/")


BIZ_DIFF = [("your_rate", "your hour", "m"), ("target_pay_year", "pay you want a year", "m"),
            ("your_client_hours_week", "your client hours a week", "h"), ("working_weeks", "working weeks", "h"),
            ("target_margin", "buffer", "p"), ("overheads_month", "overheads a month", "m"),
            ("client_hours_week", "client hours a week", "h"), ("fee_rate", "payment fees", "p"),
            ("rescope_limit", "restructure limit", "p"), ("full_hours_week", "client hours if full", "h")]
BIZ_TEXT = [("target_pay_basis", "pay basis"), ("currency", "currency")]
OFFER_DIFF = [("price", "price", "m"), ("your_hours", "your hours", "h"), ("team_hours", "team hours", "h"),
              ("team_rate", "team cost an hour", "m"), ("contractor", "contractor", "m"), ("tools", "tools and other costs", "m"),
              ("fee_rate", "payment fees", "p"), ("refund_rate", "refunds", "p"), ("per_month", "volume", "h"),
              ("alternative", "alternative", "m"), ("plan_total", "instalment plan total", "m")]


def norm_changes(pbiz, poffers, biz, offers):
    """Every change between two runs, on the normalised figures, in plain words."""
    cur = biz["currency"]
    f = {"m": lambda v: money(v, cur) if v is not None else "not set", "p": lambda v: pct(v) if v is not None else "not set",
         "h": lambda v: hours(v) if v is not None else "not set"}
    out = []
    for k, lab, kind in BIZ_DIFF:
        a, b = pbiz.get(k), biz.get(k)
        if (a is None) != (b is None) or (a is not None and abs(a - b) > 1e-9):
            out.append(f"{lab} {f[kind](a)} to {f[kind](b)}")
    for k, lab in BIZ_TEXT:
        if (pbiz.get(k) or "") != (biz.get(k) or ""):
            out.append(f"{lab} {pbiz.get(k) or 'not set'} to {biz.get(k) or 'not set'}")
    old = {o["name"]: o for o in poffers}
    for o in offers:
        po = old.get(o["name"])
        if not po:
            out.append(f"new offer {o['name']}")
            continue
        if po["billing"] != o["billing"]:
            out.append(f"{o['name']} billing {po['billing']} to {o['billing']}")
        for k, lab, kind in OFFER_DIFF:
            if k == "fee_rate" and po.get("fee_src") == "business default" and o.get("fee_src") == "business default":
                continue  # already listed once as the business's payment fees
            a, b = po.get(k), o.get(k)
            if (a is None) != (b is None) or (a is not None and abs(a - b) > 1e-9):
                out.append(f"{o['name']} {lab} {f[kind](a)} to {f[kind](b)}")
    names = {o["name"] for o in offers}
    out += [f"dropped offer {n}" for n in old if n not in names]
    return out


def restore_globals(keep):
    global DAY_HOURS
    STYLE.update(keep[0])
    PLACE.update(keep[1])
    DAY_HOURS = keep[2]


def since_last(prev, biz, offers, res, raw=None):
    """What changed since the saved run, then the floors and verdicts that moved."""
    keep = (dict(STYLE), dict(PLACE), DAY_HOURS)
    try:
        pbiz, poffers, _n, _d = normalise(prev)
        pres = compute(pbiz, poffers)
    finally:
        restore_globals(keep)
    changed = norm_changes(pbiz, poffers, biz, offers)
    cur = biz["currency"]
    when = long_date(pbiz["date"])
    old = {o["name"]: (o, r) for o, r in zip(poffers, pres["offers"])}
    lines = []
    for o, r in zip(offers, res["offers"]):
        if o["name"] not in old:
            lines.append(f"- {o['name']} is new since {when}.")
            continue
        po, pr = old[o["name"]]
        if not (r["complete"] and pr["complete"]):
            continue
        d = r["price_floor"] - pr["price_floor"]
        if abs(d) >= 0.5:
            pv, nv = verdict_label(pr), verdict_label(r)
            lines.append(f"- {o['name']}: the floor moved from {money(pr['price_floor'], cur)} to {money(r['price_floor'], cur)}"
                         + (f"; the verdict changed from {pv} to {nv}." if pv != nv else f"; the verdict stays {nv}."))
        elif verdict_label(pr) != verdict_label(r):
            lines.append(f"- {o['name']}: the verdict changed from {verdict_label(pr)} to {verdict_label(r)}.")
        else:
            lines.append(f"- {o['name']}: no change to the floor ({money(r['price_floor'], cur)}).")
    lines += [f"- {n} has been dropped since {when}." for n in old if n not in {o["name"] for o in offers}]
    pb, nb = pres.get("business"), res.get("business")
    if pb and nb and abs(pb["left_year"] - nb["left_year"]) >= 0.5:
        lines.append(f"- The whole business: what it leaves you went from {money(pb['left_year'], cur)} to "
                     f"{money(nb['left_year'], cur)} a year before tax.")
    head = [f"## Since {when}", ""]
    head += ["What changed: " + ("; ".join(changed) if changed else "nothing in the figures") + ".", ""]
    return head + lines + [""]


def business_md(biz, offers, res):
    bv, cur = res.get("business"), biz["currency"]
    L = ["## The whole business", ""]
    if not bv:
        L += ["Add how many of each offer you sell a month (or how many clients are on it) to see what the whole "
              "business leaves you.", ""]
        return L
    L.append(f"- Sales: {money(bv['sales_month'], cur)} a month, {money(bv['sales_year'], cur)} a year at these volumes.")
    tgt = "the pay you want" if biz.get("target_pay_year") else "your client hours at your rate"
    vs = bv["versus_target"]
    if biz.get("target_pay_basis") == "after tax":
        L.append(f"- Left for you after every cost and overhead, before tax: {money(bv['left_year'], cur)} a year. The "
                 f"{money(bv['target_year'], cur)} you want is after tax, so it cannot be set against this until you have "
                 "the before-tax figure.")
    else:
        L.append(f"- Left for you after every cost and overhead, before tax: {money(bv['left_year'], cur)} a year, "
                 f"{money(abs(vs), cur)} {'above' if vs >= 0 else 'below'} {money(bv['target_year'], cur)}, {tgt}.")
    stated = biz.get("stated_client_hours_week")
    if not stated and not any(o["team_hours"] for o in offers) and biz["client_hours_week_src"] != DEFAULTS["client_hours_week"][1] \
            and not biz["client_hours_week_src"].startswith("worked out"):
        stated = biz["client_hours_week"]
    if biz.get("rate_from_pay") and HOURS_OK not in biz.get("confirmed", []):
        stated = None  # the hours check is a [NEED] in the assumptions, because it moves the hour itself
    if stated and abs(bv["your_hours_week"] - stated) > HOURS_GAP * stated:
        if bv["your_hours_week"] < stated:
            L.append(f"- Hours: at these volumes your offers use {hours(bv['your_hours_week'])} of your hours a working "
                     f"week, against the {hours(stated)} client hours you gave. The difference is client time no offer "
                     "pays for as described: either the hours per offer are low, or it goes on unpaid work.")
        else:
            L.append(f"- Hours: at these volumes your offers need {hours(bv['your_hours_week'])} of your hours a working "
                     f"week, against the {hours(stated)} client hours you gave. Either the hours per offer are high, or "
                     "you are working longer than you think.")
    L.append("")
    return L


def summary_md(biz, offers, res, needs, notes, note_text=None, prev=None, raw=None):
    cur = biz["currency"]
    L = [f"# Price floor: {biz['business']}", "",
         f"{long_date(biz['date'])}. Every figure comes from the workbook beside this page.", ""]
    if biz.get("pinned_line"):
        L += [f"**{biz['pinned_line']}**", ""]
    L += [headline(biz, offers, res), ""]
    if note_text:
        L += [NOTE_MARK, ""]  # the founder's note goes in after localising, so it is never rewritten
    if prev:
        L += since_last(prev, biz, offers, res, raw)
    L += business_md(biz, offers, res)
    L += ["## The verdicts", "", "| Offer | Price | Price floor | Pays you an hour | Verdict |", "|---|---|---|---|---|"]
    for o, r in zip(offers, res["offers"]):
        if not r["complete"]:
            fl = money(r["floor_only"], cur) if r.get("floor_only") is not None else "[NEED]"
            L.append(f"| {cell_text(o['name'])} | {money(o['price'], cur) if o.get('price') else '[NEED]'} | {fl} | "
                     "[NEED] | Need inputs |")
            continue
        L.append(f"| {cell_text(o['name'])} | {money(o['price'], cur)} {cell_text(o['unit'])} | {money(r['price_floor'], cur)} | "
                 f"{money(r['eff_rate'], cur) if r['eff_rate'] is not None else 'no hours of yours'} | {verdict_label(r)} |")
    L += ["", BUFFER_LINE, ""]
    said_floor = False
    for o, r in zip(offers, res["offers"]):
        why = reasoning(o, r, biz)
        if why.endswith(FLOOR_TAIL):
            if said_floor:
                why = why[: -len(FLOOR_TAIL)]
            said_floor = True
        L += [f"### {o['name']}", "", re.sub(r"^((?:Hold|Raise|Restructure)[^.]{0,45})\.", r"**\1.**", why), ""]
        if r["complete"]:
            P = o["price"]
            extra = []
            if r.get("alt_gap") is not None:
                if r["alt_gap"] < 0:
                    extra.append(f"What your client would pay instead ({money(o['alternative'], cur)}) sits below your floor: "
                                 "the price has to be won on what only you deliver, not on cost.")
                else:
                    extra.append(f"What your client would pay instead ({money(o['alternative'], cur)}) sits "
                                 f"{money(r['alt_gap'], cur)} above your floor, so there is room to price on value.")
            if r.get("plan_ok") is False:
                extra.append(f"The instalment plan ({o['plan_text']}) totals {money(o['plan_total'], cur)} against "
                             f"{money(P, cur)} paid in full. Set the plan total above the full price so spreading "
                             "the cost pays for the risk of a missed payment.")
            if r.get("floor_full") is not None and r["floor_full"] < r["price_floor"] - 0.5:
                extra.append(f"If your diary were full the floor would be {money(r['floor_full'], cur)}: "
                             f"{money(r['price_floor'] - r['floor_full'], cur)} of today's floor is empty diary.")
            if o.get("proposed") and "c_prop" in r:
                extra.append(f"Your test price of {money(o['proposed'], cur)} leaves {money(r['c_prop'], cur)} a sale after "
                             "every direct cost, your time included. "
                             + loss_lines(r, biz, r.get("be_prop"), r["c_now"] <= 0 < r["c_prop"], r.get("be_prop_cash"),
                                          o.get("per_month")))
            L += extra + ([""] if extra else [])
            for x in options(o, r, biz):
                tag = " (recommended)" if x["recommended"] else ""
                L.append(f"- **{x['key']}. {x['title']}{tag}.** {x['detail']}")
            if options(o, r, biz):
                L.append("")
    if any(r["complete"] and r["verdict"] == "Raise" for r in res["offers"]):
        L += ["## Rolling out a rise", "",
              "1. New clients first: they have no old price to compare against, so they tell you whether the number holds.",
              "2. Existing clients next, a few at a time, with notice and the reason. Offer to hold the old price for anyone who commits to a longer term now.",
              "3. If you keep anyone on the old price, put an end date on it.", ""]
    L += ["## What the figures assume", ""]
    L.append(f"- Your hour: {money(biz['your_rate'], cur)} ({biz['your_rate_src']}"
             + (f"; pay given as {biz['target_pay_basis']}" if biz.get("target_pay_basis") else "") + ").")
    if biz["your_rate_src"].startswith("a placeholder"):
        lo, hi = money(biz["your_rate"] * 0.75, cur), money(biz["your_rate"] * 1.25, cur)
        parts = [f"{o['name']} {money(r['rate_down'], cur)} to {money(r['rate_up'], cur)}"
                 for o, r in zip(offers, res["offers"]) if r["complete"]]
        L.append(f"- With your hour at {lo} or {hi}, the floors would run: " + "; ".join(parts) + ".")
    elif after_tax(biz) and sensitivity_line(biz, offers, res):
        L.append("- " + sensitivity_line(biz, offers, res))
    L.append(f"- Buffer above your pay: {pct(biz['target_margin'])} ({biz['target_margin_src']}).")
    L.append(f"- Overheads: {money(biz['overheads_month'], cur)} a month excluding your own pay ({biz['overheads_month_src']}), "
             f"spread over {hours(biz['client_hours_week'])} client hours a week ({biz['client_hours_week_src']}) in "
             f"{fmt_plain(biz['working_weeks'], 2)} working weeks a year: {money(res['oh_per_hour'], cur)} for every "
             "client hour.")
    L.append(f"- Working weeks a year: {fmt_plain(biz['working_weeks'], 2)} ({biz['working_weeks_src']}).")
    fsrc = biz["fee_rate_src"]
    own = [(o["name"], o["fee_rate"], o["fee_src"]) for o in offers if o.get("fee_src") != "business default"]
    if own and len(own) == len(offers):
        L.append("- Payment fees, per offer: " + "; ".join(f"{n} {pct2(f)} ({fs})" for n, f, fs in own) + ".")
    else:
        L.append(f"- Payment fees: {pct(biz['fee_rate'])} unless set per offer. {fsrc[:1].upper() + fsrc[1:]}."
                 + ("".join(f" {n}: {pct2(f)} ({fs})." for n, f, fs in own)))
    if any(" days read as " in n for n in notes):
        L.append(f"- Time given in days: {fmt_plain(biz['day_hours'], 2)} hours a day ({biz['day_hours_src']}).")
    L.append("- Prices: read before any sales tax (VAT, GST or similar); ask your accountant whether you need to charge it.")
    if biz.get("decimal") == "comma":
        L.append("- Figures are read and written your way: " + ("a space" if STYLE["group"] != "." else "a dot")
                 + " between thousands and a comma before decimals.")
    if not biz.get("country"):
        L.append(f"- Paper and dates: {biz['paper_src']}.")
    if notes:
        L.append("- Ranges and sums you gave were worked out by the calculator; the workbook's Assumptions tab lists each one.")
    for n in needs:
        L.append(f"- [NEED: {n}]")
    L += ["", DISCLAIMER, ""]
    return "\n".join(L)


NOTE_MARK = "@@FOUNDER_NOTE@@"
US_WORDS = [(r"\bper cent\b", "percent")]  # "rise" is American English too, so it stays


def localise_us(md):
    """American English for a founder who writes it, on the calculator's own words only: never on the note."""
    for a, b in US_WORDS:
        md = re.sub(a, b, md)
    return md


def finish_md(md, biz, note_text):
    """Localise the generated text, then put the founder's note in unchanged."""
    if biz.get("locale") == "en-US":
        md = localise_us(md)
    return md.replace(NOTE_MARK, (note_text or "").strip())


def md_to_html(md, title, biz=None):
    tpl_path = HERE.parent / "assets" / "summary-template.html"
    tpl = tpl_path.read_text(encoding="utf-8") if tpl_path.exists() else "<html><body>$body</body></html>"
    out, in_list, in_table = [], None, False
    rows = []

    def inline(s):
        s = html.escape(s)
        return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)

    def close():
        nonlocal in_list, in_table, rows
        if in_list:
            out.append(f"</{in_list}>")
            in_list = None
        if in_table:
            head, body = rows[0], rows[1:]
            t = ["<table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead><tbody>"]
            for rw in body:
                t.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in rw) + "</tr>")
            t.append("</tbody></table>")
            out.append("".join(t))
            in_table, rows = False, []

    for line in md.splitlines():
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if all(re.fullmatch(r"-+", c) for c in cells):
                continue
            if not in_table:
                close()
                in_table = True
            rows.append(cells)
            continue
        if re.match(r"^- ", line):
            if in_list != "ul":
                close()
                out.append("<ul>")
                in_list = "ul"
            out.append(f"<li>{inline(line[2:])}</li>")
            continue
        if re.match(r"^\d+\. ", line):
            if in_list != "ol":
                close()
                out.append("<ol>")
                in_list = "ol"
            item = re.sub(r"^\d+\. ", "", line)
            out.append(f"<li>{inline(item)}</li>")
            continue
        close()
        if line.startswith("### "):
            out.append(f"<h3>{inline(line[4:])}</h3>")
        elif line.startswith("## "):
            out.append(f"<h2>{inline(line[3:])}</h2>")
        elif line.startswith("# "):
            out.append(f"<h1>{inline(line[2:])}</h1>")
        elif line.strip():
            out.append(f"<p>{inline(line)}</p>")
    close()
    from string import Template
    lang = (biz or {}).get("locale") if (biz or {}).get("locale_src") == "founder's own English" else "en"
    return Template(tpl).safe_substitute(title=html.escape(title), body="\n".join(out), lang=html.escape(lang or "en"),
                                         paper=PLACE["paper"], generator=f"Made with Merigrove {SKILL_NAME}")


# ------------------------------------------------------------------ note check (figures in prose must come from the script)
SYM_RE = r"A\$|C\$|NZ\$|S\$|HK\$|US\$|R\$|[£$€₹¥₱]"
SMALL_UNITS = r"\s*(?:hours?|hrs?|clients?|rounds?|weeks?|months?|days?|offers?|calls?|sessions?|projects?|members?|people|times?)\b"
PRICE_WORDS_T = (r"(?:raise|raising|quote|quoting|charge|charging|price|move|moving|set)\s+(?:it\s+|them\s+|the price\s+)?"
                 r"(?:(?:to|at)\s+)?(?:(?:{sym})\s?({num})|({num})\s?(?:{sym}))")
PROMISES = re.compile(r"\b(you will make|you'll make|double|triple|guarantee[sd]?|guaranteed|risk[- ]free)\b", re.I)


def _num_re():
    """A figure as the founder writes it: 1,234.5 for a decimal-point founder, 1.234,5 or 1 234,5 for a comma one."""
    if STYLE["dec"] == ",":
        g = re.escape(STYLE["group"]) + ("| " if STYLE["group"] != "." else "")
        return r"\d{1,3}(?:(?:" + g + r")\d{3})+(?:,\d+)?|\d+(?:,\d+)?"
    return r"\d{1,2}(?:,\d{2})*,\d{3}(?:\.\d+)?|\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?"


def _tok_value(n):
    if STYLE["dec"] == ",":
        return float(re.sub(r"[.\s\u202f]", "", n).replace(",", "."))
    return float(n.replace(",", ""))


def tokens(text):
    """Each figure with its kind: money (a currency sign before or after), pct (a % or per cent), or plain."""
    rx = re.compile(r"(?<![\w.,$])(-?)((?:" + SYM_RE + r")\s?)?(" + _num_re() + r")(?![\d])(\s?(?:" + SYM_RE + r")(?!\w))?"
                    r"(\s*(?:%|per ?cent\b|percent\b))?")
    out = []
    for m in rx.finditer(text):
        try:
            v = round(float(m.group(1) + "1") * _tok_value(m.group(3)), 2)
        except ValueError:
            continue
        kind = "money" if (m.group(2) or m.group(4)) else ("pct" if m.group(5) else "plain")
        out.append((v, kind, m.end()))
    return out


def numbers_in(text):
    return {v for v, _k, _e in tokens(text)}


def input_figures(raw, biz, offers):
    """Every figure the founder gave, as given and as read, so a note may quote any of them."""
    vals = set()
    for k in ("target_pay_year", "your_client_hours_week", "stated_client_hours_week", "working_weeks", "your_rate",
              "overheads_month", "client_hours_week", "day_hours", "full_hours_week"):
        if isinstance(biz.get(k), (int, float)):
            vals.add(round(biz[k], 2))
    for o in offers:
        for k in ("price", "your_hours", "team_hours", "team_rate", "contractor", "tools", "per_month", "alternative",
                  "proposed", "plan_total"):
            if isinstance(o.get(k), (int, float)):
                vals.add(round(o[k], 2))
    texts = []

    def walk(x):
        if isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
        elif isinstance(x, str):
            texts.append(x)
        elif isinstance(x, (int, float)) and not isinstance(x, bool):
            vals.add(round(float(x), 2))
    walk(raw or {})
    for t in texts:
        vals |= numbers_in(t)
    return vals


def option_figures(o, r, opts):
    """Figures that belong only to options the calculator did not recommend: (option key, its figures)."""
    out = []
    rec = next((x["key"] for x in opts if x["recommended"]), None)
    for x in opts:
        if x["key"] == rec:
            continue
        if x["key"] == "B":
            figs = f"{hours(o['your_hours'] * r['k'])}" + (f" {hours(o['team_hours'] * r['k'])}" if o["team_hours"] else "")
        elif x["key"] == "C":
            figs = f"{money(r['mid_price'], '')} {pct(r['mid_cut'])} {hours(o['your_hours'] * r['mid_k'])}"
        else:
            figs = f"{money(r['raise_price'], '')} {pct(r['rise'])}"
        out.append((x["key"], numbers_in(figs)))
    return out


OPTION_NAMES = {"A": r"\boption A\b|\(A\)|\braise to\b|\braising (it )?to\b",
                "B": r"\boption B\b|\(B\)",
                "C": r"\boption C\b|\(C\)|\bmiddle\b"}
VERDICT_WORDS = {"Raise": r"\braise\b|\braising\b|\bput (it|the price) up\b",
                 "Restructure": r"\brestructur\w*|\bcut the hours\b|\btrim\w*",
                 "Hold": r"\bhold\b|\bkeep (it|the price)\b"}


def check_note(note, allowed_text, price_figures=(), offers=None, res=None, biz=None, extra=()):
    """Problems (blocking) and warnings for the founder's note. Every figure must come from the computed results or
    from what the founder gave; a figure that belongs only to an option the calculator did not recommend must name
    that option; a promise of a result is refused."""
    allowed = {}
    for v, k, _e in tokens(allowed_text):
        allowed.setdefault(k, set()).add(v)
    extra = set(extra)
    any_allowed = set().union(*allowed.values()) if allowed else set()
    problems, warns = [], []
    found = tokens(note)
    for v, k, end in found:
        small = 0 <= v <= 12 and float(v).is_integer() and k == "plain" and re.match(SMALL_UNITS, note[end:])
        if small or v in extra:
            continue
        ok = v in allowed.get(k, set()) if k in ("money", "pct") else v in any_allowed
        if not ok:
            problems.append(f"figure {fmt_plain(v)}{'%' if k == 'pct' else ''} is not in the computed results or in what "
                            "the founder gave" + (" as a money figure" if k == "money" else "")
                            + ("; write figures the way the summary does" if STYLE["dec"] == "," else ""))
    prices = {round(x, 2) for x in price_figures if x is not None} | extra
    rx = re.compile(PRICE_WORDS_T.format(sym=SYM_RE, num=_num_re()), re.I)
    for m in rx.finditer(note):
        v = round(_tok_value(m.group(1) or m.group(2)), 2)
        if prices and v not in prices:
            problems.append(f"'{m.group(0)}' names a price the calculator did not recommend or test")
    for m in PROMISES.finditer(note):
        problems.append(f"promise of a result: '{m.group(0)}'")
    if offers and res and biz:
        note_vals = {v for v, _k, _e in found}
        plain = "\n".join(ln_ for ln_ in allowed_text.splitlines()
                          if not (re.match(r"^- \*\*[ABC]\. ", ln_) and "(recommended)" not in ln_))
        safe = numbers_in(plain) | extra
        done = [(o, r) for o, r in zip(offers, res["offers"]) if r.get("complete")]
        sentences = re.split(r"(?<=[.!?])\s+", note)
        for o, r in done:
            about = [x for x in sentences if len(done) == 1 or re.search(re.escape(o["name"]), x, re.I)]
            if not about:
                continue
            opts = options(o, r, biz)
            for key, figs in option_figures(o, r, opts):
                hit = sorted((figs & note_vals) - safe)
                if hit and not re.search(OPTION_NAMES[key], note, re.I):
                    problems.append(f"the note uses {fmt_plain(hit[0], 2)} from option {key} for {o['name']}, but the "
                                    "calculator recommends "
                                    + ("no option yet (provisional)" if r.get("provisional") else
                                       next((f"option {x['key']}" for x in opts if x["recommended"]), verdict_label(r)))
                                    + f"; name option {key} or use the recommended figures")
            own = VERDICT_WORDS.get(r["verdict"], "(?!)")
            for x in about:
                for verdict, pat in VERDICT_WORDS.items():
                    m = re.search(pat, x, re.I)
                    if verdict != r["verdict"] and m and not re.search(own, x, re.I):
                        warns.append(f"the note says '{m.group(0)}' about {o['name']}, whose verdict is "
                                     f"{verdict_label(r)}; check the note still matches")
    words = len(re.findall(r"\b\w[\w'-]*\b", note))
    if words > 120:
        problems.append(f"note is {words} words, limit 120")
    if re.search("[\u2014\u2013]", note):
        problems.append("note contains an em or en dash")
    return problems, warns


def price_figures(offers, res):
    out = []
    for o, r in zip(offers, res["offers"]):
        out += [o.get("price"), o.get("proposed"), o.get("alternative")]
        if r.get("complete"):
            out += [r.get("price_floor"), r.get("cost_floor"), r.get("raise_price"), r.get("rec_price"), r.get("mid_price"),
                    round(r["price_floor"]) if r.get("price_floor") else None]
    return out


# ------------------------------------------------------------------ workbook (openpyxl, live formulas)
IN_ROWS = [  # key, label, format
    ("name", "Offer name", "text"), ("billing", "Billing: one-off or monthly (for reference)", "text"),
    ("price", "Price one client pays, per sale or per month, before any sales tax", "money"),
    ("your_hours", "Your hours per sale or month (include calls, admin and revisions)", "num"),
    ("team_hours", "Team hours per sale or month", "num"), ("team_rate", "Team cost per hour", "money"),
    ("contractor", "Contractor or freelancer cost per sale or month", "money"),
    ("tools", "Tools, materials and other direct costs per sale or month", "money"),
    ("fee_rate", "Payment fee rate", "pct"), ("refund_rate", "Refunds and write-offs (share of price)", "pct"),
    ("per_month", "Sales a month, or clients on it (optional)", "num"),
    ("alternative", "What the client would pay instead (optional)", "money"),
    ("plan_total", "Instalment plan total (optional)", "money"),
    ("proposed", "A price you want to test (optional)", "money"),
    ("prefer", "Preferred route if below the floor: raise or restructure (optional)", "text"),
]


NOTES_FOR_BOOK = []


def recalc_with_libreoffice(path):
    """Store calculated values beside the formulas so previews show figures. Optional: needs LibreOffice."""
    import shutil
    import subprocess
    import tempfile
    exe = shutil.which("soffice") or shutil.which("libreoffice")
    if not exe:
        return False
    tmp = Path(tempfile.mkdtemp())
    try:
        subprocess.run([exe, f"-env:UserInstallation=file://{tmp / 'profile'}", "--headless", "--calc",
                        "--convert-to", "xlsx:Calc MS Excel 2007 XML", "--outdir", str(tmp / "out"), str(path)],
                       check=True, capture_output=True, timeout=120)
        made = tmp / "out" / Path(path).name
        if made.exists() and made.stat().st_size > 0:
            shutil.copyfile(made, path)
            return True
    except Exception:  # noqa: BLE001
        return False
    return False


def write_xlsx(path, biz, offers, res):
    import openpyxl as ox  # optional: without it the build step writes CSV files instead
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter as L
    Workbook = ox.Workbook

    cur = biz["currency"]
    sym = SYMBOLS.get(cur, "")
    if sym and STYLE["after"]:  # the symbol where the founder puts it; the app shows the marks in its own locale
        MON, MON2 = f'#,##0 "{sym}";-#,##0 "{sym}"', f'#,##0.00 "{sym}";-#,##0.00 "{sym}"'
    else:
        MON = f'"{sym}"#,##0;-"{sym}"#,##0' if sym else '#,##0'
        MON2 = f'"{sym}"#,##0.00;-"{sym}"#,##0.00' if sym else '#,##0.00'
    PCT, NUM = "0.0%", "#,##0.0"
    YEL = PatternFill("solid", fgColor="FFF4C2")
    B, T, G = Font(bold=True), Font(bold=True, size=14), Font(color="666666", italic=True)
    RED = Font(color="B00020", bold=True)
    WR = Alignment(wrap_text=True, vertical="top")
    wb = Workbook()
    wb.properties.creator = "Merigrove"
    wb.properties.title = f"Price floor: {biz['business']}"
    wb.properties.description = f"Made with Merigrove {SKILL_NAME}"
    n = len(offers)
    cols = [L(2 + i) for i in range(n)]
    fmts = {"money": MON, "pct": PCT, "num": NUM, "text": "@"}

    # ---- Inputs
    si = wb.active
    si.title = "Inputs"
    si["A1"], si["A1"].font = f"Price floor inputs: {biz['business']}", T
    si["A2"] = "Yellow cells are your inputs. Change any of them and every figure in this workbook updates. " + SALES_TAX_LINE
    si["A2"].font = G
    stated = None if biz.get("rate_from_pay") else biz["your_rate"]
    basis = biz.get("target_pay_basis")
    pay_lab = {"before tax": "Pay you want a year, before tax (leave empty to use the rate below)",
               "after tax": "Pay you want a year: AFTER TAX as given, so every floor is too low until you enter the "
                            "before-tax figure (from your accountant)"}.get(
        basis, "Pay you want a year, before tax (leave empty to use the rate below)")
    biz_rows = [("currency", "Currency (for reference)", biz["currency"], "@"),
                ("target_pay_year", pay_lab, biz.get("target_pay_year"), MON),
                ("target_pay_basis", "Pay given before or after tax (type: before tax, or after tax)", basis or "", "@"),
                ("your_client_hours_week", "Your own client hours a week" + (
                    " (worked out from your offers: the hours they use at these volumes)" if biz.get("hours_from_offers")
                    else ""), biz.get("your_client_hours_week"), NUM),
                ("working_weeks", "Working weeks a year once your holidays and public holidays are out (46 is an assumption; set your own)",
                 biz.get("working_weeks", WORKING_WEEKS), NUM),
                ("stated_rate", "Or: an hourly rate you set yourself (used first when filled)", stated, MON2),
                ("your_rate", "What an hour of your time is worth (worked out)", None, MON2),
                ("target_margin", "Buffer above your pay (target margin)", biz["target_margin"], PCT),
                ("overheads_month", "Monthly overheads, excluding your own pay", biz["overheads_month"], MON),
                ("client_hours_week", "Client hours a week (you and anyone whose hours are costed below)" + (
                    "; worked out from the rows above and below" if biz.get("client_hours_formula") else ""),
                 biz["client_hours_week"], NUM),
                ("rescope_limit", "Largest hours cut a restructure can take", biz["rescope_limit"], PCT),
                ("full_hours_week", "Client hours a week if you were full (optional)", biz.get("full_hours_week"), NUM)]
    ref = {}
    for i, (k, lab, v, f) in enumerate(biz_rows):
        ref[k] = f"Inputs!$B${4 + i}"
    top = 4 + len(biz_rows) + 1
    irow = {k: top + 1 + i for i, (k, _lab, _f) in enumerate(IN_ROWS)}
    first, last = cols[0], cols[-1]

    def rng(k):
        return f"Inputs!${first}${irow[k]}:${last}${irow[k]}"
    formula_cells = set()
    for i, (k, lab, v, f) in enumerate(biz_rows):
        row = 4 + i
        si.cell(row, 1, lab)
        if k == "your_rate":
            v = (f"=IF(N({ref['stated_rate']})>0,{ref['stated_rate']},IF(AND(N({ref['target_pay_year']})>0,"
                 f"N({ref['your_client_hours_week']})>0),{ref['target_pay_year']}/({ref['your_client_hours_week']}*"
                 f"{ref['working_weeks']}),0))")
            si.cell(row, 1).font = B
        elif k == "your_client_hours_week" and biz.get("hours_from_offers"):
            v = f"=SUMPRODUCT({rng('your_hours')},{rng('per_month')})*12/{ref['working_weeks']}"
            formula_cells.add(k)
        elif k == "client_hours_week" and biz.get("client_hours_formula") == "yours plus team":
            v = f"={ref['your_client_hours_week']}+SUMPRODUCT({rng('team_hours')},{rng('per_month')})*12/{ref['working_weeks']}"
            formula_cells.add(k)
        elif k == "client_hours_week" and biz.get("client_hours_formula") == "all from offers":
            v = (f"=(SUMPRODUCT({rng('your_hours')},{rng('per_month')})+SUMPRODUCT({rng('team_hours')},{rng('per_month')}))"
                 f"*12/{ref['working_weeks']}")
            formula_cells.add(k)
        c = si.cell(row, 2, v)
        c.number_format = f
        if k not in ("your_rate", "currency") and k not in formula_cells:
            c.fill = YEL
        if k in ("target_pay_year", "target_pay_basis") and basis == "after tax":
            si.cell(row, 1).font = RED
            c.font = RED
    si.cell(top, 1, "Per offer").font = B
    for j in range(n):
        si.cell(top, 2 + j, offers[j]["name"]).font = B
    for i, (k, lab, f) in enumerate(IN_ROWS):
        row = top + 1 + i
        si.cell(row, 1, lab)
        for j, o in enumerate(offers):
            v = o.get(k)
            if k == "billing":
                v = o["billing"]
            c = si.cell(row, 2 + j, v)
            c.number_format = fmts[f]
            if k != "billing":
                c.fill = YEL
            c.alignment = Alignment(horizontal="right", wrap_text=(k == "name"))
    si.column_dimensions["A"].width = 66
    for c in cols:
        si.column_dimensions[c].width = 24
    si.freeze_panes = "B4"

    def I(k, c):
        return f"Inputs!{c}${irow[k]}"

    # ---- Floors
    sf = wb.create_sheet("Floors")
    sf["A1"], sf["A1"].font = "Price floors, per offer", T
    sf["A2"] = "Per sale for one-off work, per month for monthly work. Formulas only: change the Inputs tab."
    sf["A2"].font = G
    sf["A3"] = "Overhead per client hour"
    sf["B3"] = f"=IFERROR({ref['overheads_month']}/({ref['client_hours_week']}*{ref['working_weeks']}/12),0)"
    sf["B3"].number_format = MON2
    OH = "Floors!$B$3"
    sf["A4"] = "Overhead per client hour if you were full"
    sf["B4"] = (f"=IF(N({ref['full_hours_week']})>0,{ref['overheads_month']}/({ref['full_hours_week']}*{ref['working_weeks']}/12),"
                "\"not set\")")
    sf["B4"].number_format = MON2
    OHF = "Floors!$B$4"
    R, M, LIM = ref["your_rate"], ref["target_margin"], ref["rescope_limit"]
    rows = [
        ("name", "Offer", "={c}", "@"),
        ("net", "Net revenue (after refunds)", "={P}*(1-{rr})", MON),
        ("fees", "Payment fees", "={P}*{f}", MON),
        ("contractor", "Contractor or freelancer", "={con}", MON),
        ("tools", "Tools and other direct costs", "={tools}", MON),
        ("team_cost", "Team time", "={th}*{tr}", MON),
        ("cash_costs", "Cash costs", "={fees}+{contractor}+{tools}+{team_cost}", MON),
        ("your_time", "Your time at your rate", "={yh}*" + R, MON),
        ("direct", "Direct cost, your time included", "={cash_costs}+{your_time}", MON),
        ("contribution", "Contribution (what one sale leaves after every direct cost)", "={net}-{direct}", MON),
        ("cash_left", "Cash one sale leaves before your time and overheads", "={net}-{cash_costs}", MON),
        ("cmargin", "Contribution margin", "=IFERROR({contribution}/{net},\"\")", PCT),
        ("overhead_share", "Share of overheads (by client hours)", "=({yh}+{th})*" + OH, MON),
        ("full_cost", "Full cost", "={direct}+{overhead_share}", MON),
        ("cost_floor", "Cost floor: the price that covers every cost, nothing left over", "=IFERROR(({full_cost}-{fees})/((1-{rr})-{f}),\"\")", MON),
        ("price_floor", "Price floor: every cost covered and your buffer kept", "=IFERROR(({full_cost}-{fees})/((1-{rr})*(1-" + M + ")-{f}),\"\")", MON),
        ("gap", "Price floor less today's price", "=IFERROR({price_floor}-{P},\"\")", MON),
        ("real_margin", "Buffer at today's price, after full cost", "=IFERROR(({net}-{full_cost})/{net},\"\")", PCT),
        ("eff_rate", "What today's price pays you an hour", "=IFERROR(({net}-{cash_costs}-{overhead_share})/{yh},\"no hours of yours\")", MON2),
        ("eff_vs", "Against your rate", "=IFERROR({eff_rate}-" + R + ",\"\")", MON2),
        ("k", "Share of today's hours the price can pay for", "=IFERROR(({net}*(1-" + M + ")-{fees}-{contractor}-{tools})/({yh}*" + R + "+{th}*{tr}+({yh}+{th})*" + OH + "),\"\")", PCT),
        ("cut", "Hours cut a restructure needs", "=IF({P}>={price_floor}-0.000001,\"not needed\",IFERROR(1-{k},\"\"))", PCT),
        ("verdict", "Verdict", "=IF(OR({P}>={price_floor}-0.000001,AND({P}>=" + str(AT_FLOOR) + "*{price_floor},{P}>={cost_floor}-0.000001)),"
         "\"Hold\",IF(LOWER({pref})=\"raise\",\"Raise\",IF(AND(ISNUMBER({k}),N({k})>0,OR(LOWER({pref})=\"restructure\",N({cut})<="
         + LIM + "+0.000001)),\"Restructure\",\"Raise\")))", "@"),
        ("below_cost", "Loses money once your time is counted", "=IF({P}<{cost_floor}-0.000001,\"Yes\",\"No\")", "@"),
        ("step", "Rounding step for a new price (10 below 500, 50 below 2,000, 100 below 10,000, else 500)", "=IF({price_floor}<500,10,IF({price_floor}<2000,50,IF({price_floor}<10000,100,500)))", "#,##0"),
        ("rec_price", "Recommended price (new clients first)", "=IF({verdict}=\"Raise\",ROUNDUP({price_floor}/{step},0)*{step},{P})", MON),
        ("rate_down", "Price floor if your hour were worth 25% less", "=IFERROR(({full_cost}-{fees}-{your_time}*0.25)/((1-{rr})*(1-" + M + ")-{f}),\"\")", MON),
        ("rate_up", "Price floor if your hour were worth 25% more", "=IFERROR(({full_cost}-{fees}+{your_time}*0.25)/((1-{rr})*(1-" + M + ")-{f}),\"\")", MON),
        ("floor_full", "Price floor if you were full", "=IF(ISNUMBER(" + OHF + "),({full_cost}-{fees}-{overhead_share}+({yh}+{th})*" + OHF + ")/((1-{rr})*(1-" + M + ")-{f}),\"not set\")", MON),
        ("alt_gap", "What the client would pay instead, less your floor", "=IF(N({alt})>0,{alt}-{price_floor},\"not given\")", MON),
        ("plan_ok", "Instalment plan total above the full price", "=IF(N({plan})>0,IF({plan}>{P},\"Yes\",\"No\"),\"no plan\")", "@"),
    ]
    frow = {}
    for i, (k, *_r) in enumerate(rows):
        frow[k] = 6 + i
    for i, (k, lab, tmpl, f) in enumerate(rows):
        row = 6 + i
        sf.cell(row, 1, lab)
        if k in ("price_floor", "verdict", "eff_rate", "rec_price"):
            sf.cell(row, 1).font = B
        for j in range(n):
            c = cols[j]
            sub = {kk: f"{c}{frow[kk]}" for kk in frow}
            sub.update(c=f"Inputs!{c}${irow['name']}", P=I("price", c), rr=I("refund_rate", c), f=I("fee_rate", c),
                       con=I("contractor", c), yh=I("your_hours", c), th=I("team_hours", c), tr=I("team_rate", c),
                       alt=I("alternative", c), plan=I("plan_total", c), pref=I("prefer", c))
            sub["tools_in"] = I("tools", c)
            t = tmpl.replace("={tools}", "={tools_in}")
            cell = sf.cell(row, 2 + j, t.format(**sub))
            cell.number_format = f
            cell.alignment = Alignment(horizontal="right", wrap_text=(k == "name"))
            if k in ("price_floor", "verdict", "eff_rate", "rec_price"):
                cell.font = B
    sf.column_dimensions["A"].width = 62
    for c in cols:
        sf.column_dimensions[c].width = 24
    sf.row_dimensions[frow["name"]].height = 30
    sf.freeze_panes = "B6"

    def FL(k, c):
        return f"Floors!{c}${frow[k]}"

    # ---- Options
    so = wb.create_sheet("Options")
    so["A1"], so["A1"].font = "Price change options", T
    so["A2"] = ("Break-even client loss: two views. Counting freed hours at your rate, or in plain cash "
                "(lose more than the cash figure and you take in less until you refill the hours).")
    so["A2"].font = G
    orows = [
        ("name", "Offer", "={nm}", "@"),
        ("verdict", "Verdict", "={vd}", "@"),
        ("h_a", "A. Raise", "", "@"),
        ("a_price", "New price", "=IF({P}<{pf},ROUNDUP({pf}/{st},0)*{st},{P})", MON),
        ("a_rise", "Rise", "=IFERROR({a_price}/{P}-1,\"\")", PCT),
        ("c_now", "Contribution per sale today", "={cn}", MON),
        ("a_contr", "Contribution per sale at the new price", "={a_price}*(1-{rr})-{a_price}*{f}-{con}-{tools}-{th}*{tr}-{yh}*" + R, MON),
        ("a_be", "Break-even client loss, counting freed hours at your rate", "=IF({verdict}=\"Hold\",\"not needed\",IF({c_now}<=0,\"any: each client today costs you money\",IFERROR(({a_contr}-{c_now})/{a_contr},\"\")))", PCT),
        ("a_cash", "Break-even client loss in plain cash", "=IF({verdict}=\"Hold\",\"not needed\",IFERROR(({a_price}*(1-{rr})-{a_price}*{f}-{con}-{tools}-{th}*{tr}-{cl})/({a_price}*(1-{rr})-{a_price}*{f}-{con}-{tools}-{th}*{tr}),\"\"))", PCT),
        ("a_month", "Extra cash a month at your volume, keeping every client", "=IF(N({vol})>0,({a_contr}-{c_now})*{vol},\"volume not given\")", MON),
        ("h_b", "B. Restructure: same price, fewer hours", "", "@"),
        ("b_cut", "Hours cut needed", "=IF({verdict}=\"Hold\",\"not needed\",{cut})", PCT),
        ("b_yh", "Your hours after the cut", "=IF({verdict}=\"Hold\",\"not needed\",IFERROR({yh}*{k},\"\"))", NUM),
        ("b_th", "Team hours after the cut", "=IF({verdict}=\"Hold\",\"not needed\",IFERROR({th}*{k},\"\"))", NUM),
        ("h_c", "C. Meet in the middle", "", "@"),
        ("c_price", "Price (half the rise)", "=IF({P}<{pf},ROUNDUP(({P}+({a_price}-{P})/2)/IF(({P}+({a_price}-{P})/2)<500,10,IF(({P}+({a_price}-{P})/2)<2000,50,IF(({P}+({a_price}-{P})/2)<10000,100,500))),0)*IF(({P}+({a_price}-{P})/2)<500,10,IF(({P}+({a_price}-{P})/2)<2000,50,IF(({P}+({a_price}-{P})/2)<10000,100,500))),\"n/a\")", MON),
        ("c_k", "Share of hours that price pays for", "=IFERROR(({c_price}*(1-{rr})*(1-" + M + ")-{c_price}*{f}-{con}-{tools})/({yh}*" + R + "+{th}*{tr}+({yh}+{th})*" + OH + "),\"n/a\")", PCT),
        ("c_cut", "Hours cut needed at that price", "=IFERROR(1-{c_k},\"n/a\")", PCT),
        ("c_shown", "Shown in the summary", "=IF(AND(ISNUMBER({c_cut}),N({c_cut})>=0.05),\"yes\",\"no: under a 5% hours cut, or no rise needed\")", "@"),
        ("h_t", "Your test price", "", "@"),
        ("t_contr", "Contribution per sale at your test price", "=IF(N({prop})>0,{prop}*(1-{rr})-{prop}*{f}-{con}-{tools}-{th}*{tr}-{yh}*" + R + ",\"not run\")", MON),
        ("t_be", "Break-even client loss at your test price, counting freed hours at your rate", "=IF(N({prop})>0,IF({c_now}<=0,\"any\",IFERROR(({t_contr}-{c_now})/{t_contr},\"\")),\"not run\")", PCT),
    ]
    orow = {k: 4 + i for i, (k, *_r) in enumerate(orows)}
    for i, (k, lab, tmpl, f) in enumerate(orows):
        row = 4 + i
        so.cell(row, 1, lab)
        if k.startswith("h_"):
            so.cell(row, 1).font = B
            continue
        for j in range(n):
            c = cols[j]
            sub = {kk: f"{c}{orow[kk]}" for kk in orow}
            sub.update(nm=FL("name", c), vd=FL("verdict", c), pf=FL("price_floor", c), st=FL("step", c),
                       P=I("price", c), rr=I("refund_rate", c), f=I("fee_rate", c), con=I("contractor", c),
                       tools=I("tools", c), th=I("team_hours", c), tr=I("team_rate", c), yh=I("your_hours", c),
                       cn=FL("contribution", c), vol=I("per_month", c), cut=FL("cut", c), k=FL("k", c),
                       prop=I("proposed", c), cl=FL("cash_left", c))
            cell = so.cell(row, 2 + j, tmpl.format(**sub))
            cell.number_format = f
            cell.alignment = Alignment(horizontal="right", wrap_text=(k == "name"))
    so.column_dimensions["A"].width = 52
    for c in cols:
        so.column_dimensions[c].width = 22

    # ---- Summary (first tab)
    ss = wb.create_sheet("Summary", 0)
    ss["A1"], ss["A1"].font = f"Price floor: {biz['business']}", T
    ss["A2"] = f"{long_date(biz['date'])}. {headline(biz, offers, res)}"
    if biz.get("locale") == "en-US":
        ss["A2"] = localise_us(ss["A2"].value)
    ss["A2"].alignment = WR
    ss.merge_cells("A2:H2")
    ss.row_dimensions[2].height = 48
    heads = ["Offer", "Price today", "Cost floor", "Price floor", "Pays you an hour", "Your rate", "Verdict", "Recommended price"]
    for j, h in enumerate(heads):
        ss.cell(4, 1 + j, h).font = B
        ss.cell(4, 1 + j).alignment = Alignment(horizontal="right" if j else "left", wrap_text=True)
    ss.row_dimensions[4].height = 30
    for i in range(n):
        c, row = cols[i], 5 + i
        vals = [f"={FL('name', c)}", f"={I('price', c)}", f"={FL('cost_floor', c)}", f"={FL('price_floor', c)}",
                f"={FL('eff_rate', c)}", f"={R}",
                (f"={FL('verdict', c)}&IF(AND(LOWER({ref['target_pay_basis']})=\"after tax\",N({ref['stated_rate']})=0,"
                 f"N({ref['target_pay_year']})>0,{FL('verdict', c)}<>\"Raise\"),\" (provisional)\",\"\")"),
                f"={FL('rec_price', c)}"]
        for j, v in enumerate(vals):
            cell = ss.cell(row, 1 + j, v)
            cell.number_format = [None, MON, MON, MON, MON, MON, "@", MON][j] or "General"
            if j:
                cell.alignment = Alignment(horizontal="right")
    # the whole business, live: changes with the yellow cells
    first, last = cols[0], cols[-1]
    pm = f"Inputs!{first}${irow['per_month']}:{last}${irow['per_month']}"
    yhr = f"Inputs!{first}${irow['your_hours']}:{last}${irow['your_hours']}"
    prr = f"Inputs!{first}${irow['price']}:{last}${irow['price']}"
    clr = f"Floors!{first}${frow['cash_left']}:{last}${frow['cash_left']}"
    have = f"AND(COUNT({pm})={n},COUNT({yhr})={n},COUNT({prr})={n})"
    rb = 6 + n
    ss.cell(rb, 1, "The whole business, at the volumes on the Inputs tab").font = B
    brows = [
        ("Sales a year", f"=IF({have},SUMPRODUCT({prr},{pm})*12,\"add volumes\")", MON),
        ("Left for you a year, before tax, after every cost and overhead",
         f"=IF({have},(SUMPRODUCT({clr},{pm})-{ref['overheads_month']})*12,\"add volumes\")", MON),
        ("Against: the pay you want (or your client hours at your rate)",
         f"=IF({have},IF(N({ref['target_pay_year']})>0,{ref['target_pay_year']},SUMPRODUCT({yhr},{pm})*12*{R}),\"add volumes\")", MON),
        ("Difference", f"=IFERROR(B{rb + 2}-B{rb + 3},\"add volumes\")", MON),
    ]
    for i, (lab, f_, fm) in enumerate(brows):
        ss.cell(rb + 1 + i, 1, lab)
        c = ss.cell(rb + 1 + i, 2, f_)
        c.number_format = fm
        c.alignment = Alignment(horizontal="right")
    ss.column_dimensions["A"].width = 58
    r0 = rb + 2 + len(brows)
    ss.cell(r0, 1, "Why").font = B
    for i, (o, r) in enumerate(zip(offers, res["offers"])):
        why = reasoning(o, r, biz)
        cell = ss.cell(r0 + 1 + i, 1, localise_us(why) if biz.get("locale") == "en-US" else why)
        cell.alignment = WR
        ss.merge_cells(start_row=r0 + 1 + i, start_column=1, end_row=r0 + 1 + i, end_column=8)
        ss.row_dimensions[r0 + 1 + i].height = 52
    rz = r0 + 2 + n
    ss.cell(rz, 1, "The Why lines were written when the workbook was made. If you change an input, the table above updates; run the calculator again to refresh the words.").font = G
    ss.cell(rz + 1, 1, DISCLAIMER).font = G
    for c in "BCDEFGH":
        ss.column_dimensions[c].width = 17

    # ---- Assumptions
    sa = wb.create_sheet("Assumptions")
    sa["A1"], sa["A1"].font = "Where each input came from", T
    for j, h in enumerate(["Input", "Value", "Source"]):
        sa.cell(3, 1 + j, h).font = B
    rr_ = 4
    for k, lab, v, f in biz_rows:
        sa.cell(rr_, 1, lab)
        c = sa.cell(rr_, 2, f"={ref[k]}")
        c.number_format = f
        sa.cell(rr_, 3, biz.get(k + "_src", ""))
        rr_ += 1
    for lab, v, src_ in (("Your country (sets paper size and date order)", biz.get("country") or "not given", biz["paper_src"]),
                         ("Your number style", {"comma": "1.234,56", "dot": "1,234.56"}.get(biz.get("decimal"), "not needed"),
                          biz["decimal_src"])):
        sa.cell(rr_, 1, lab)
        sa.cell(rr_, 2, v)
        sa.cell(rr_, 3, src_)
        rr_ += 1
    for o in offers:
        sa.cell(rr_, 1, f"{o['name']}: payment fee")
        sa.cell(rr_, 2, o["fee_rate"]).number_format = PCT
        sa.cell(rr_, 3, o["fee_src"])
        rr_ += 1
    sa.cell(rr_ + 1, 1, SALES_TAX_LINE)
    rr_ += 3
    if NOTES_FOR_BOOK:
        sa.cell(rr_, 1, "Figures the calculator worked out from what you gave").font = B
        for x in NOTES_FOR_BOOK:
            rr_ += 1
            sa.cell(rr_, 1, x)
    sa.column_dimensions["A"].width = 62
    sa.column_dimensions["B"].width = 16
    sa.column_dimensions["C"].width = 80
    try:
        from openpyxl.workbook.properties import CalcProperties
        wb.calculation = CalcProperties(fullCalcOnLoad=True)
    except Exception:  # noqa: BLE001
        pass
    for ws in wb.worksheets:
        ws.page_setup.paperSize = ws.PAPERSIZE_LETTER if PLACE["paper"] == "Letter" else ws.PAPERSIZE_A4
        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToWidth = 1
        ws.sheet_properties.pageSetUpPr.fitToPage = True
    wb.save(path)


def write_csv(folder, stem, biz, offers, res):
    p1 = folder / f"{stem}-inputs.csv"
    with p1.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Input"] + [o["name"] for o in offers])
        for k, lab, _f in IN_ROWS:
            w.writerow([lab] + [o.get(k) if o.get(k) is not None else "" for o in offers])
        for k, lab in (("your_rate", "What an hour of your time is worth"), ("target_margin", "Target margin"),
                       ("overheads_month", "Monthly overheads, excluding your own pay"),
                       ("client_hours_week", "Client hours a week"), ("rescope_limit", "Largest hours cut a restructure can take")):
            w.writerow([lab, round(biz[k], 4)])
    p2 = folder / f"{stem}-results.csv"
    keys = [("net", "Net revenue (after refunds)"), ("fees", "Payment fees"), ("cash_costs", "Cash costs"),
            ("your_time", "Your time at your rate"), ("direct", "Direct cost, your time included"),
            ("contribution", "Contribution (what one sale leaves after every direct cost)"), ("cmargin", "Contribution margin"),
            ("overhead_share", "Share of overheads"), ("full_cost", "Full cost"), ("cost_floor", "Cost floor"),
            ("price_floor", "Price floor"), ("gap", "Price floor less today's price"),
            ("real_margin", "Margin at today's price, after full cost"), ("eff_rate", "What today's price pays you an hour"),
            ("cut", "Hours cut a restructure needs"), ("verdict", "Verdict"), ("rec_price", "Recommended price"),
            ("raise_price", "Option A: raised price"), ("rise", "Option A: rise"), ("c_rec", "Option A: contribution at the raised price"),
            ("be_loss", "Option A: break-even client loss"), ("mid_price", "Option C: middle price"),
            ("mid_cut", "Option C: hours cut at the middle price")]
    with p2.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Figure"] + [o["name"] for o in offers])
        for k, lab in keys:
            w.writerow([lab] + [("" if r.get(k) is None else (round(r[k], 4) if isinstance(r.get(k), float) else r.get(k)))
                                for r in res["offers"]])
    return [p1, p2]


def formulas_md():
    return f"""
## Rebuild it in any spreadsheet

Per offer, per sale (or per month for monthly work):

- Net revenue = price x (1 less refund rate)
- Cash costs = price x fee rate + contractor + tools + team hours x team cost an hour
- Direct cost = cash costs + your hours x your rate
- Overhead per client hour = monthly overheads / (client hours a week x working weeks a year / 12)
- Full cost = direct cost + (your hours + team hours) x overhead per client hour
- Price floor = (full cost less fees) / ((1 less refund rate) x (1 less target margin) less fee rate)
- What the price pays you an hour = (net revenue less cash costs less overhead share) / your hours
- Verdict: Hold at or above the floor, or within {pct(1 - AT_FLOOR)} below it and above the cost floor; otherwise
  Restructure when a cut in hours of at most the restructure limit closes the gap, else Raise
"""


# ------------------------------------------------------------------ commands
def load(path):
    p = Path(path)
    if not p.exists():
        raise InputError(f"there is no file at {path}")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise InputError(f"{path} is not valid JSON ({e.msg} at line {e.lineno})")


def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")  # Consultoría -> consultoria
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40] or "business"


def cmd_compute(a):
    raw = load(a.inputs)
    biz, offers, notes, needs = normalise(raw)
    res = compute(biz, offers)
    plausibility(biz, offers, res)
    cur = biz["currency"]
    print(f"{biz['business']} | {biz['date']} | currency {cur} | country {biz['country'] or 'not given'} | "
          f"number style {biz['decimal'] or 'not needed'}")
    print(f"Your hour {money(biz['your_rate'], cur)} ({biz['your_rate_src']}); buffer {pct(biz['target_margin'])}; "
          f"overheads {money(biz['overheads_month'], cur)} a month over {hours(biz['client_hours_week'])} client hours a week = "
          f"{money(res['oh_per_hour'], cur)} per client hour")
    for o, r in zip(offers, res["offers"]):
        print(f"\n== {o['name']} ({o['billing']}, {money(o['price'], cur)} {o['unit']})")
        if not r["complete"]:
            if r.get("floor_only") is not None:
                print(f"   no price yet, so no verdict. Price floor before any sales tax: {money(r['floor_only'], cur)}; "
                      f"cost floor {money(r['cost_floor_only'], cur)}")
            else:
                print("   needs a price and your hours")
            continue
        for k, lab, kind in [("contribution", "contribution", "m"), ("cmargin", "contribution margin", "p"),
                             ("overhead_share", "overhead share", "m"), ("full_cost", "full cost", "m"),
                             ("cost_floor", "cost floor", "m"), ("price_floor", "price floor", "m"),
                             ("real_margin", "buffer after full cost", "p"), ("eff_rate", "pays you an hour", "m"),
                             ("cut", "hours cut needed", "p"), ("rec_price", "recommended price", "m"),
                             ("be_loss", "break-even client loss", "p")]:
            v = r.get(k)
            if k in ("be_loss", "cut") and r["verdict"] == "Hold":
                continue
            if k == "be_loss" and r.get("be_any"):
                print(f"   {lab}: any, counting freed hours at your rate")
                print(f"   break-even client loss in plain cash: {pct(r.get('be_cash'))}")
                continue
            if k == "be_loss":
                print(f"   {lab}, counting freed hours at your rate: {pct(v)}")
                print(f"   break-even client loss in plain cash: {pct(r.get('be_cash'))}")
                continue
            print(f"   {lab}: {money(v, cur) if kind == 'm' else pct(v)}")
        print(f"   VERDICT: {verdict_label(r)}{' (below cost floor)' if r['below_cost'] else ''}")
        print("   " + reasoning(o, r, biz))
    bv = res.get("business")
    if bv:
        print(f"\nWHOLE BUSINESS: sales {money(bv['sales_year'], cur)} a year; left for you before tax "
              f"{money(bv['left_year'], cur)} a year against {money(bv['target_year'], cur)} ({bv['target_src']}"
              + (", after tax, so not like for like" if biz.get("target_pay_basis") == "after tax" else "") + "); "
              f"sales at the recommended prices {money(bv['sales_year_rec'], cur)} a year")
    if after_tax(biz) and sensitivity_line(biz, offers, res):
        print("BEFORE-TAX SENSITIVITY: " + sensitivity_line(biz, offers, res))
    if biz.get("stated_rate_below"):
        print(f"HOUR CHECK: the {money(biz['stated_rate_below'], cur)} rate you gave is below the "
              f"{money(biz['pay_hour'], cur)} an hour that {money(biz['target_pay_year'], cur)} after tax needs before "
              "any tax, so the floors use the higher figure")
    for x in notes:
        print("NOTE:", x)
    for x in needs:
        print("NEED:", x)
    if a.json_out:
        Path(a.json_out).write_text(json.dumps({"business": biz, "offers": offers, "results": res,
                                                 "needs": needs, "notes": notes}, indent=2, default=str), encoding="utf-8")
    sys.exit(1 if needs else 0)


def _note_problems(a_note, raw, biz, offers, res, needs, notes, prev):
    if not Path(a_note).exists():
        raise InputError(f"there is no note file at {a_note}")
    note_text = Path(a_note).read_text(encoding="utf-8").strip()
    md_plain = summary_md(biz, offers, res, needs, notes, prev=prev, raw=raw)
    probs, warns = check_note(note_text, md_plain, price_figures(offers, res), offers, res, biz,
                              input_figures(raw, biz, offers))
    return note_text, probs, warns


def cmd_checknote(a):
    """Check a note against the figures without building anything: fast, so a rewrite costs one run."""
    raw = load(a.inputs)
    biz, offers, notes, needs = normalise(raw)
    res = compute(biz, offers)
    plausibility(biz, offers, res)
    prev = load(a.previous) if a.previous else None
    _t, probs, warns = _note_problems(a.note, raw, biz, offers, res, needs, notes, prev)
    for p in probs:
        print("PROBLEM:", p)
    for w in warns:
        print("WARN:", w)
    print(f"{len(probs)} problems, {len(warns)} warnings")
    sys.exit(2 if probs else 0)


def cmd_build(a):
    raw = load(a.inputs)
    biz, offers, notes, needs = normalise(raw)
    res = compute(biz, offers)
    plausibility(biz, offers, res)
    note_text = None
    prev = load(a.previous) if a.previous else None
    if a.note:
        note_text, probs, warns = _note_problems(a.note, raw, biz, offers, res, needs, notes, prev)
        for w in warns:
            print("WARN:", w)
        if probs:
            for p in probs:
                print("PROBLEM:", p)
            print("STOP: the note was not used. Fix it (check it with the checknote command) and run build again. "
                  "Nothing was written.")
            sys.exit(2)
    md = summary_md(biz, offers, res, needs, notes, note_text, prev, raw)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    stem = f"price-floor-{slug(biz['business'])}-{biz['date']}"
    written = []
    try:
        _write_all(a, out, stem, biz, offers, res, md, needs, notes, written, note_text)
    except BaseException:
        for p in written:
            try:
                Path(p).unlink()
            except OSError:
                pass
        raise
    for p in written:
        print("WROTE:", p)
    for x in needs:
        print("NEED:", x)
    sys.exit(1 if needs else 0)


def _write_all(a, out, stem, biz, offers, res, md, needs, notes, written, note_text=None):
    fmt = a.format
    if fmt in ("auto", "xlsx"):
        try:
            import openpyxl  # noqa: F401
            p = out / f"{stem}.xlsx"
            NOTES_FOR_BOOK[:] = notes
            written.append(p)
            write_xlsx(p, biz, offers, res)
            if not a.no_recalc and recalc_with_libreoffice(p):
                print("NOTE: workbook recalculated, so previews show the figures as well as the formulas.")
            else:
                print("NOTE: workbook holds live formulas without stored values; Excel, Numbers, Sheets and LibreOffice "
                      "calculate them on opening, but a quick preview may show empty cells.")
        except ImportError:
            if fmt == "xlsx":
                print("STOP: openpyxl is not installed; use --format csv")
                sys.exit(2)
            fmt = "csv"
            print("NOTE: openpyxl is not available here, so the workbook is written as CSV files with the formulas in the summary.")
    if fmt == "csv":
        written.extend(write_csv(out, stem, biz, offers, res))
        md += formulas_md()
    md = finish_md(md, biz, note_text)
    pm = out / f"{stem}-summary.md"
    written.append(pm)
    pm.write_text(md, encoding="utf-8")
    ph = out / f"{stem}-summary.html"
    written.append(ph)
    ph.write_text(md_to_html(md, f"Price floor: {biz['business']}", biz), encoding="utf-8")
    pj = Path(a.results) if getattr(a, "results", None) else out / f"{stem}-results.json"
    pj.parent.mkdir(parents=True, exist_ok=True)
    written.append(pj)
    pj.write_text(json.dumps({"business": biz, "offers": offers, "results": res, "needs": needs, "notes": notes},
                             indent=2, default=str), encoding="utf-8")


TEMPLATE = {
    "business": None, "currency": None, "country": None, "decimal": None, "date": None, "locale": None,
    "working_weeks_year": None, "day_hours": None, "confirmed": [],
    "target_pay_year": None, "target_pay_basis": None, "your_client_hours_week": None, "your_rate": None,
    "target_margin": None, "overheads_month": None, "client_hours_week": None, "paid_by": None, "card_share": None,
    "full_hours_week": None,
    "offers": [{"name": None, "billing": None, "price": None, "your_hours": None, "team_hours": None, "team_rate": None,
                "contractor": None, "tools": None, "paid_by": None, "fee_rate": None, "refund_rate": None,
                "per_month": None, "alternative": None, "instalments": None, "proposed": None, "unit_label": None,
                "prefer": None}],
    "sources": {},
    "_how": "Every value starts empty. Fill only what the founder gave or what the intake guide derives; anything left "
            "empty takes a stated default or a [NEED] flag.",
}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("template")
    c = sub.add_parser("compute")
    c.add_argument("inputs")
    c.add_argument("--json-out")
    b = sub.add_parser("build")
    b.add_argument("inputs")
    b.add_argument("--out", required=True)
    b.add_argument("--note")
    b.add_argument("--previous", help="the inputs file from the last run (memory.py read), for the Since section")
    b.add_argument("--format", default="auto", choices=["auto", "xlsx", "csv"])
    b.add_argument("--no-recalc", action="store_true", help="skip the LibreOffice pass that stores calculated values")
    b.add_argument("--results", help="where to write the results file for the memory step (default: the output folder)")
    n = sub.add_parser("checknote")
    n.add_argument("inputs")
    n.add_argument("note")
    n.add_argument("--previous")
    a = ap.parse_args()
    if a.cmd == "template":
        print(json.dumps(TEMPLATE, indent=2))
    elif a.cmd == "compute":
        cmd_compute(a)
    elif a.cmd == "build":
        cmd_build(a)
    elif a.cmd == "checknote":
        cmd_checknote(a)
    else:
        ap.print_help()
        sys.exit(2)


if __name__ == "__main__":
    try:
        main()
    except AskError as e:
        print(f"STOP: {e}. Nothing was written.")
        print(f"ASK: {e.question}")
        sys.exit(2)
    except InputError as e:
        print(f"STOP: {e}. Nothing was written.")
        sys.exit(2)
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print(f"STOP: the calculator could not finish ({type(e).__name__}: {e}). Nothing usable was written; "
              "check the inputs file and run again.")
        sys.exit(2)
