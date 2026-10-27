#!/usr/bin/env python3
"""Sales Target Planner: work back from the profit a founder needs to the sales, calls, bookings and leads
each month takes, check the founder's calendar before calling it feasible, name what breaks first, and
write the plan as one workbook with live formulas.

Usage (paths relative to the skill folder):
  python3 scripts/target_plan.py template                         print a blank inputs file
  python3 scripts/target_plan.py compute <inputs.json> [--json-out results.json]
        print every figure, the binding constraint, the scenarios, the pace and the first week
  python3 scripts/target_plan.py build <inputs.json> --out <folder> [--note note.md]
        [--previous previous.json] [--json-out results.json] [--no-cache]
        write sales-target-plan_<date>.xlsx (Plan, Try a lever, Scenarios, Assumptions)

Inputs are JSON. Values may be messy strings ("12k", "about 3,600", "6 of 10", "8hrs", "a day a week",
"half"); the script reads them and records what it did. Missing values get a stated default or a
[NEED] line, never an invented figure.

Exit codes: 0 done; 1 done with [NEED] lines (expected when something was skipped);
2 STOP: nothing usable was written. A STOP line says what to fix.
Standard library only. No network calls.
"""
import argparse
import copy
import html
import json
import math
import re
import sys
import unicodedata
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path

SKILL_NAME = "Sales Target Planner"
WEEKS_PER_MONTH = 52 / 12.0

# ---------------------------------------------------------------- sales tax: one neutral line, no figures
# This skill never holds a tax rate, threshold or rule for any country. Prices are planned as entered, before
# any sales tax, and the plan says so once.
SALES_TAX_LINE = ("Enter prices before any sales tax (VAT, GST or similar); ask your accountant whether you need "
                  "to charge it.")
ADVICE_LINE = "A planning tool, not financial, tax or legal advice."

# ---------------------------------------------------------------- planning defaults
# Working defaults for founders with no history. Each is shown to the founder as a default and is a
# yellow cell in the workbook. None is a statistic about other businesses.
DEFAULT_RATES = {"inbound": {"show": 60.0, "close": 20.0}, "outbound": {"show": 70.0, "close": 10.0}}
CALL_HOURS = 1.5          # a 45 to 60 minute call plus preparation and follow-up
SELLING_HOURS = 8.0       # hours a week for sales calls when the founder skips
WORKING_DAYS = 20.0       # selling days a month for a founder
CASH_SHARE = 100.0        # share of the price paid in the month the client signs
TIGHT = 0.75              # from three quarters of the selling hours the plan fits, tightly
SHOW_ALARM = 65.0         # show rate below this binds
CLOSE_FLOOR = 20.0        # close rate on held calls below this binds
VOLUME_LIMIT = 3.0        # leads needed at three times today's or more binds
MIN_EVENTS = 10           # a rate on fewer events is directional
CHANNEL_MIN_LEADS = 10    # a channel with fewer leads in 90 days is a capped experiment
LEVER = {"show": 70.0, "deal_step": 0.10, "close": 30.0, "offer": 100.0}
RAMP = {"productive": "weeks 3 to 4", "full_pace_week": 8}
REPLAN_ASSUMED, REPLAN_MEASURED = 30, 90
RET_HORIZON = 6         # monthly fees: whole months to reach the target when no date is given

# Display symbols only. No currency is assumed and nothing is ever converted.
SYMBOLS = {"GBP": "£", "USD": "$", "EUR": "€", "AUD": "A$", "CAD": "C$", "NZD": "NZ$", "SGD": "S$", "HKD": "HK$",
           "INR": "₹", "JPY": "¥", "CNY": "¥", "MYR": "RM", "PHP": "₱", "DOLLARS": "$", "PLN": "zł", "ZAR": "R",
           "BRL": "R$", "KRW": "₩", "THB": "฿", "NGN": "₦", "ILS": "₪", "TRY": "₺", "VND": "₫", "CZK": "Kč",
           "JPY_OR_CNY": "¥", "INR_OR_PKR_OR_LKR": "Rs", "SEK_OR_NOK_OR_DKK": "kr"}
# symbol written in a figure -> currency code (an unqualified $ is read as 'dollars', not as any one country)
SYMBOL_CODES = [("s$", "SGD"), ("hk$", "HKD"), ("a$", "AUD"), ("c$", "CAD"), ("nz$", "NZD"), ("us$", "USD"),
                ("£", "GBP"), ("€", "EUR"), ("₹", "INR"), ("₱", "PHP"), ("rm", "MYR"), ("$", "DOLLARS")]
CODES = (r"gbp|usd|eur|aud|cad|nzd|sgd|hkd|inr|jpy|myr|php|aed|cny|idr|thb|zar|chf|sek|nok|dkk|krw|vnd|pln|czk|brl|"
         r"mxn|ngn|kes|pkr|lkr|bdt|egp|try|ils|qar|kwd|twd|clp|cop|ars|pen|sar")
MONEY_KEYS = ("price", "target_profit_month", "target_profit_year", "target_profit_by_date", "target_revenue_month",
              "delivery_cost", "running_costs_month", "sales_month_now", "founder_pay_month")
DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
DEFAULT_CALL_DAYS = [0, 1, 2, 3, 4]
# founder-facing wording that differs in American English (the founder's own spelling wins)
AMERICAN = [("per cent", "percent"), ("Per cent", "Percent"), ("enquiries", "inquiries"), ("Enquiries", "Inquiries"),
            ("enquiry", "inquiry"), ("Enquiry", "Inquiry"), ("your diary", "your calendar"), ("Your diary", "Your calendar")]
STYLE = {"month_first": False, "american": False, "decimal": None, "group": ",", "sym_after": False}


def spell(text):
    """Mirror the founder's English: American spelling where the founder writes American English."""
    if not STYLE["american"] or not isinstance(text, str):
        return text
    for a, b in AMERICAN:
        text = text.replace(a, b)
    return text


class InputError(Exception):
    """Shown to the founder as one plain STOP line."""


# ================================================================ parsing messy values
# Every founder-typed figure goes through locale_numbers (the Merigrove reader for any country's number style):
# 15.000 €, 4.850,00, 15 000 €, 1,5h, 68,3%, ₹1,50,000, 450万. What this skill adds on top: arithmetic the
# founder or Claude writes as parts ("=4450 - 1200"), ranges read as their midpoint (noted), voice-note words
# ("five grand", "six fifty"), and a refusal to pick silently when one value holds two figures.
import locale_numbers as LN  # noqa: E402


class Question(InputError):
    """A figure that reads two ways, or not at all: one plain question for the founder."""


APPROX = (r"\b(?:about|roughly|around|approx\.?|approximately|circa|ca\.|maybe|say|probably|give or take|or so|"
          r"at least|at most|nearly|almost|environ|vers|à peu près|aprox\.?|aproximadamente|unos|unas|etwa|"
          r"ungefähr|rund|ongeveer|circa|cerca de|mais ou menos)\b|~|-?ish\b")
# sales-tax wording in any language: before-tax markers are only stripped; inclusive markers raise a [NEED]
TAX_INCL = (r"\b(?:inc|incl|including|with|inkl|inklusive|incluido|incluida|incluso|inclusa|inbegrepen|incl\.)\.?\s*"
            r"(?:vat|gst|sales tax|tax|mwst|ust|iva|btw|tva|taxes)\b|\bttc\b|\btoutes taxes comprises\b|"
            r"\b(?:vat|gst|mwst|iva|btw|tva)\s*(?:inc|incl|included|inclusive|inkl|incluido|inbegrepen)\b|"
            r"\bcon iva\b|\bbrutto\b")
TAX_EXCL = (r"\b(?:ex|excl|excluding|exkl|zzgl|plus|before|sin|más|mas|hors|excl\.|exclusief|sem|senza)\.?\s*"
            r"(?:vat|gst|sales tax|tax|taxes|mwst|ust|iva|btw|tva|impuestos|imposto|impostos)\b|\bht\b|\bh\.t\.|"
            r"\bhors taxes?\b|\bnetto\b|\+\s*(?:vat|gst|iva|btw|tva|mwst)\b|\bbefore taxes\b")
PERIOD = (r"(?:\s*(?:/|\bper\b|\ban?\b|\beach\b|\bevery\b|\bpar\b|\bpor\b|\bpro\b|\bal\b|\bau\b)\s*"
          r"(?:month|mo|mth|week|wk|year|yr|sale|client|customer|call|contract|deal|project|job|"
          r"mois|mes|monat|maand|semaine|semana|woche|week|an|année|año|jahr|jaar|contrat|contrato|vertrag|"
          r"auftrag|dossier|mission|projet|proyecto|cliente|kunde|klant|appel|llamada)s?\b\.?)")
WORDS_OUT = (r"\b(?:monthly|weekly|yearly|annually|in profit|profit|revenue|turnover|sales|net|gross|clients?|"
             r"bénéfice|beneficio|gewinn|winst|lucro|chiffre d'affaires|before taxes?|pre[- ]?tax|after costs?)\b")
NUMTOK = r"\d{1,3}(?:[   ]\d{3})+(?:[.,]\d+)?(?!\d)|\d[\d.,']*\d|\d"
MULT = r"k|m|mn|million|bn|lakhs?|lacs?|crores?|cr|grand|thousand"
RANGE_SEP = r"(?:-|\u2013|to|or|and|à|a|bis|tot|o|y)"


def style_decimal():
    return STYLE.get("decimal")


def _mult(x):
    x = (x or "").lower()
    if x.startswith(("lakh", "lac")):
        return 100000.0
    if x.startswith("cr"):
        return 10000000.0
    if x in ("m", "mn", "million"):
        return 1000000.0
    if x == "bn":
        return 1e9
    return 1000.0 if x in ("k", "grand", "thousand") else 1.0


def _tok(tok, label, raw):
    """One numeric token in the founder's number style. Ambiguous becomes one question, never a guess."""
    tok = tok.strip().rstrip(".,")
    try:
        return LN.parse_number(tok, style_decimal(), allow_words=False)[0]
    except LN.Ambiguous as e:
        raise Question(f"{label}: '{raw}' can be read two ways ({e}). Ask the founder: do you write one thousand "
                       "two hundred and fifty as 1,250.00 or as 1.250,00? Then set number_style and run again")
    except LN.Unreadable:
        raise Question(f"{label}: could not read '{raw}' as a figure. Ask the founder to restate it")


def _safe_eval(expr):
    import ast
    import operator as op
    ops = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv, ast.USub: op.neg}

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


def _expr(s, label, raw):
    """'=4450 - 1200', '6 x 1.5 + 3', '=1.400*7' in the founder's style: each figure read by locale_numbers."""
    def sub(m):
        return repr(_tok(m.group(1), label, raw) * _mult(m.group(2)))
    body = re.sub(r"(" + NUMTOK + r")\s*(" + MULT + r")?\b", sub, s.replace("×", "x"))
    body = re.sub(r"(?<=[\d)])\s*x\s*(?=[\d(])", "*", body)
    return _safe_eval(body)


SMALL = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen "
                                    "fourteen fifteen sixteen seventeen eighteen nineteen".split())}
TENS = {w: 10 * i for i, w in enumerate("_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()) if i > 1}


def words_to_num(s):
    """'five grand' 5000, 'two thousand four hundred' 2400, 'six hundred and fifty' 650, 'six fifty' 650,
    'nineteen fifty' 1950, 'a couple of grand' None (too vague). Digits are left alone."""
    toks = [t for t in re.findall(r"[a-z]+", s.lower()) if t not in ("and", "a", "about", "roughly", "around", "pounds",
                                                                       "quid", "per", "month", "week", "each", "maybe", "hours", "hour", "hrs", "a week", "weeks", "months", "an", "of")]
    if not toks or not all(t in SMALL or t in TENS or t in ("hundred", "thousand", "grand", "k") for t in toks):
        return None
    if len(toks) >= 2 and not any(t in ("hundred", "thousand", "grand", "k") for t in toks):
        first = SMALL.get(toks[0])
        rest = sum(SMALL.get(t, 0) + TENS.get(t, 0) for t in toks[1:])
        if first is not None and 10 <= rest <= 99:
            return float(first * 100 + rest)
    total, cur = 0, 0
    for t in toks:
        if t in SMALL:
            cur += SMALL[t]
        elif t in TENS:
            cur += TENS[t]
        elif t == "hundred":
            cur = (cur or 1) * 100
        else:
            total += (cur or 1) * 1000
            cur = 0
    return float(total + cur)


EMPTY = ("", "none", "nothing", "zero", "nil", "n/a", "na", "unknown", "not known", "no idea", "?", "skip", "dunno",
         "don't know", "dont know", "not sure", "aucun", "rien", "nada", "keine", "geen")


def _strip(raw, hours_field=False):
    """Words around a figure that carry no amount: approximations, periods, tax markers, 'profit'."""
    s = unicodedata.normalize("NFKC", str(raw)).strip()
    s = re.sub("[\u2013\u2014\u2212]", "-", s)
    approx = bool(re.search(APPROX, s, re.I))
    s = re.sub(APPROX, " ", s, flags=re.I)
    s = re.sub(TAX_INCL, " ", s, flags=re.I)
    s = re.sub(TAX_EXCL, " ", s, flags=re.I)
    s = re.sub(PERIOD, " ", s, flags=re.I)
    s = re.sub(PERIOD, " ", s, flags=re.I)
    if not hours_field:
        s = re.sub(WORDS_OUT, " ", s, flags=re.I)
    return re.sub(r"\s+", " ", s).strip(" ,;:"), approx


HOUR_PHRASES = [(r"\b(?:an?|one) hour and a half\b", 1.5), (r"\bhalf an? hour\b", 0.5),
                (r"\b(?:an?|one) (?:full )?day\b", 7.5), (r"\b(?:an?|one) hour\b", 1.0)]


def to_num(v, notes=None, label="", hours_field=False):
    """A number from what the founder typed, in their number style. None when nothing is there.
    Raises Question when the value can be read two ways or holds two figures that are not a range."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, (list, dict)):
        raise InputError(f"{label or 'a value'} should be one figure, not a list")
    raw = str(v).strip()
    if raw.lower() in EMPTY:
        return 0.0 if raw.lower() in ("none", "nothing", "zero", "nil", "aucun", "rien", "nada", "keine", "geen") else None
    def note(val, how):
        if notes is not None:
            notes.append(f"{label}: read '{raw}' as {fmt(val, 2)}" + (f" ({how})" if how else ""))
    # arithmetic written as parts
    if raw.startswith("="):
        try:
            val = _expr(raw[1:], label, raw)
        except (ValueError, SyntaxError, ZeroDivisionError):
            raise InputError(f"{label}: could not work out '{raw}'")
        if notes is not None:
            notes.append(f"{label}: {fmt(val, 2)}, worked out from {raw.lstrip('=').strip()}")
        return val
    s, approx = _strip(raw, hours_field)
    if s.lower() in EMPTY:
        return None
    if re.fullmatch(r"[\d.,\s+\-*/()x×']+", s) and re.search(r"\d\s*[+*/x×]\s*[\d(]", s):
        try:
            val = _expr(s, label, raw)
            if notes is not None:
                notes.append(f"{label}: {fmt(val, 2)}, worked out from {s}")
            return val
        except (ValueError, SyntaxError, ZeroDivisionError):
            pass
    if hours_field:
        try:
            val, hn = LN.parse_hours(s, day_hours=7.5, decimal=style_decimal())
            if s != fmt_plain(val):
                note(val, "; ".join(x for x in hn if x != "approximate"))
            return val
        except LN.Ambiguous as e:
            raise Question(f"{label}: '{raw}' can be read two ways ({e}). Ask the founder which they mean")
        except LN.Unreadable:
            pass
    # a range: the midpoint, noted
    m = re.fullmatch(r"(?:between\s+)?(?:[^\d\s]{0,4}\s?)(" + NUMTOK + r")\s*(" + MULT + r")?\s*" + RANGE_SEP + r"\s*"
                     r"(?:[^\d\s]{0,4}\s?)(" + NUMTOK + r")\s*(" + MULT + r")?\s*(?:[^\d\s]{0,4})?", s, re.I)
    if m:
        a = _tok(m.group(1), label, raw) * _mult(m.group(2) or m.group(4))
        b = _tok(m.group(3), label, raw) * _mult(m.group(4))
        if b >= a:
            mid = (a + b) / 2
            if notes is not None:
                notes.append(f"{label}: read '{raw}' as the midpoint, {fmt(mid, 2)}")
            return mid
    if not hours_field:
        try:
            val, nn = LN.parse_number(s, style_decimal())
            if any(x.startswith("x") for x in nn) and notes is not None and not re.fullmatch(r"[\d.,]+\s*k", s, re.I):
                note(val, "")
            return val
        except LN.Ambiguous as e:
            if "is a range" not in str(e):
                raise Question(f"{label}: '{raw}' can be read two ways ({e}). Ask the founder: do you write one "
                               "thousand two hundred and fifty as 1,250.00 or as 1.250,00? Then set number_style and "
                               "run again")
        except LN.Unreadable:
            pass
    # a sentence: convert spoken durations, then insist on exactly one figure
    t = s.lower()
    vals = []
    if hours_field:
        def ph(val):
            vals.append(val)
            return f" §{len(vals) - 1}§ "
        for pat, val in HOUR_PHRASES:
            t = re.sub(pat, lambda _m, v_=val: ph(v_), t)
        t = re.sub(r"(" + NUMTOK + r")\s*(?:mins?|minutes?|minutos|minuten)\b",
                   lambda mm: ph(_tok(mm.group(1), label, raw) / 60.0), t)
        t = re.sub(r"(" + NUMTOK + r")\s*(?:days?|jours?|d[ií]as?|tage?n?)\b",
                   lambda mm: ph(_tok(mm.group(1), label, raw) * 7.5), t)
    t = re.sub(r"(?<=[\d§])\s*(?:hours?|hrs?|h|std\.?|heures?|horas?|uur|pm|pa|p/m|/mo(?:nth)?|/m|/wk|/week|"
               r"each|clients?|sales?|calls?|ish|net|gross)\b\.?", " ", t)
    found = []
    for mm in re.finditer(r"§(\d+)§|(" + NUMTOK + r")\s*(" + MULT + r")?(?![\w])", t):
        if mm.group(1) is not None:
            found.append(vals[int(mm.group(1))])
        else:
            found.append(_tok(mm.group(2), label, raw) * _mult(mm.group(3)))
    distinct = sorted(set(round(x, 6) for x in found))
    if len(distinct) > 1:
        raise Question(f"I read {len(distinct)} figures in '{raw}' for {label.lower() or 'one value'}: "
                       + " and ".join(fmt(x, 2) for x in distinct) + ". Ask the founder which one the plan should use")
    if distinct:
        val = distinct[0]
        note(val, "")
        return val
    w = words_to_num(t)
    if w is not None:
        note(w, "")
        return w
    raise Question(f"{label}: could not read '{raw}' as a figure. Ask the founder to restate it")


def fmt_plain(v):
    return f"{v:g}"


WORD_SHARES = {"all": 100.0, "all of it": 100.0, "full": 100.0, "in full": 100.0, "upfront": 100.0,
               "up front": 100.0, "everything": 100.0, "half": 50.0, "a half": 50.0, "a third": 100 / 3.0,
               "third": 100 / 3.0, "one third": 100 / 3.0, "a quarter": 25.0, "quarter": 25.0,
               "two thirds": 200 / 3.0, "three quarters": 75.0}


def to_rate(v, label, notes):
    """A conversion rate. Q3 asks 'of 10 booked calls, how many turn up', so a bare 1 to 10 reads as
    'out of 10'. '60%' or '68,3 %' is per cent; '0.6' is a fraction; '1 in 4' is an estimate; 'a of b' with b
    above 10 and no 'about' is a count with b events.
    Returns (per cent, kind, events) where kind is 'estimate' or 'counted'."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, str) and v.strip().lower() in EMPTY:
        return None
    s = unicodedata.normalize("NFKC", str(v)).strip().lower()
    if s in WORD_SHARES:
        return WORD_SHARES[s], "estimate", None
    m = re.search(r"(\d[\d.,]*)\s*(?:of|out of|/|in|sur|de|von|van|su|em)\s*(?:every\s*|chaque\s*|cada\s*)?(\d[\d.,]*)", s)
    if m:
        a, b = _tok(m.group(1), label, v), _tok(m.group(2), label, v)
        if b <= 0:
            raise InputError(f"{label}: '{v}' divides by nothing")
        if a > b:
            raise InputError(f"{label}: '{v}' has more succeeding than tried. Check the two figures")
        val = 100.0 * a / b
        if b <= 10 or re.search(APPROX + r"|guess|think|environ|à peu près", s, re.I):
            return val, "estimate", None
        notes.append(f"{label}: {fmt(val, 1)}%, worked out from {fmt(a)} of {fmt(b)}")
        return val, "counted", int(b)
    is_pct = bool(re.search(r"%|per ?cent|pour ?cent|por ?ciento|prozent|procent", s))
    x = to_num(re.sub(r"%|per ?cent|pour ?cent|por ?ciento|prozent|procent", "", s), None, label)
    if x is None:
        return None
    if is_pct:
        val = x
    elif x < 1:
        val = x * 100
    elif x <= 10:
        val = x * 10
        notes.append(f"{label}: read '{v}' as {fmt(x)} out of 10, {fmt(val)}%")
    else:
        val = x
    if val < 0 or val > 100:
        raise InputError(f"{label} of {fmt(val)}% cannot be right. Give it as 'out of 10' or a percentage")
    if val == 0:
        raise InputError(f"{label} of 0% means no call ever moves on, so no plan can climb it. Check the figure")
    return val, "estimate", None


def to_share(v, label="Share of the price paid in the month they sign"):
    """A percentage from 0 to 100. A fraction such as 0.34 is refused: give 34."""
    if v is None or (isinstance(v, str) and v.strip().lower() in EMPTY):
        return None
    s = unicodedata.normalize("NFKC", str(v)).strip().lower()
    if s in WORD_SHARES:
        return WORD_SHARES[s]
    is_pct = "%" in s
    x = to_num(re.sub(r"%|per ?cent|pour ?cent|por ?ciento|prozent|procent", "", s), None, label)
    if x is None:
        raise InputError(f"{label}: could not read '{v}'. Give a percentage from 0 to 100")
    if 0 < x < 1 and not is_pct:
        raise InputError(f"{label}: '{v}' reads as a fraction. Give the percentage instead "
                         f"({fmt(x * 100)} for {fmt(x * 100)} per cent)")
    if x < 0 or x > 100:
        raise InputError(f"{label}: {fmt(x)} is outside 0 to 100")
    return x


def yes_no(v):
    s = str(v if v is not None else "").strip().lower()
    if re.match(r"^(y|yes|yep|yeah|true|it does|includes?|including|incl?)\b", s):
        return "yes"
    if re.match(r"^(n|no|nope|false|it does not|it doesn'?t|excludes?|excluding|excl?|before|plus)\b", s):
        return "no"
    return None


def currency_of(raw, assume):
    """The founder's currency: as given, or read from a symbol or code in their figures. Never assumed."""
    cur = str(raw.get("currency") or "").strip()
    if cur:
        up_ = cur.upper()
        for sym, code in SYMBOL_CODES:
            if cur.lower() == sym:
                return code
        return {"DOLLAR": "DOLLARS", "POUNDS": "GBP", "EUROS": "EUR", "RUPEES": "INR"}.get(up_, up_)
    text = " ".join(str(raw.get(k) or "") for k in MONEY_KEYS)
    low = text.lower()
    m = re.search(r"\b(" + CODES + r")\b", low)
    if m:
        return m.group(1).upper()
    for sym, code in SYMBOL_CODES:
        if (sym == "rm" and re.search(r"\brm\s*\d", low)) or (sym != "rm" and sym in low):
            if code == "DOLLARS":
                assume.append(("Currency", "dollars, from the $ in your figures; say which dollars if it matters "
                               "(nothing is converted)", "assumed"))
            return code
    seen = LN.find_currency(text)
    if seen:
        if "_OR_" in seen or seen in ("DOLLAR", "PESO", "SHILLING"):
            assume.append(("Currency", f"{SYMBOLS.get(seen, seen.split('_')[0])} from your figures; say which "
                           "currency if it matters (nothing is converted)", "assumed"))
            return {"DOLLAR": "DOLLARS"}.get(seen, seen)
        return seen
    assume.append(("Currency", "not given, so amounts carry no symbol; nothing is converted", "assumed"))
    return ""


def basis_of(v):
    s = str(v or "").lower()
    if re.search(r"take[- ]?home|after tax|in my pocket|in hand|net of tax|after tax and", s):
        return "take-home"
    if re.search(r"before tax|pre[- ]?tax|gross", s):
        return "before tax"
    return None


def day_names(text):
    out = []
    for w in re.findall(r"[a-z]+", text.lower()):
        w = w[:-1] if w.endswith("s") and w[:-1] in DAYS else w
        for i, d in enumerate(DAYS):
            if w == d or (len(w) >= 3 and d.startswith(w)):
                out.append(i)
                break
    return out


def call_days_of(v):
    """The days the founder takes calls: 'Monday to Friday', 'Sun-Thu', 'Mon to Sat', ['Tue', 'Thu']."""
    if not v:
        return None
    text = " ".join(str(x) for x in v) if isinstance(v, list) else str(v)
    m = re.search(r"([a-z]+)\s*(?:to|-|through|thru|until)\s*([a-z]+)", text.lower())
    if m:
        a, b = day_names(m.group(1)), day_names(m.group(2))
        if a and b:
            i, out = a[0], [a[0]]
            while i != b[0]:
                i = (i + 1) % 7
                out.append(i)
            return sorted(set(out))
    days = sorted(set(day_names(text)))
    return days or None


def dates_off(v, notes):
    """Dated days the founder takes no calls (public holidays, leave), founder supplied."""
    if not v:
        return []
    items = v if isinstance(v, list) else re.split(r"[;,]\s*(?=\d{4}-)|\s+and\s+", str(v))
    out = []
    for x in items:
        x = str(x).strip()
        got = None
        for f_ in ("%Y-%m-%d", "%d %B %Y", "%B %d %Y", "%d %b %Y", "%b %d %Y"):
            try:
                got = datetime.strptime(x.replace(",", ""), f_).date()
                break
            except ValueError:
                pass
        if got:
            out.append(got)
        elif x:
            notes.append(f"Days off: could not read '{x}' as a date (write it YYYY-MM-DD), so it is not skipped")
    return sorted(set(out))


def day_list(v):
    if not v:
        return []
    text = " ".join(str(x) for x in v) if isinstance(v, list) else str(v)
    out = []
    for w in re.findall(r"[a-z]+", text.lower()):
        w = w[:-1] if w.endswith("s") and w[:-1] in DAYS else w
        for i, d in enumerate(DAYS):
            if w == d or (len(w) >= 3 and d.startswith(w) and w not in ("sat", "sun") or w in ("sat", "sun") and d.startswith(w)):
                out.append(i)
    return sorted(set(out))


# ================================================================ formatting
def localise(s):
    """'12,345.6' written the founder's way: '12.345,6', '12 345,6' or '12'345.6'."""
    dec = "," if STYLE.get("decimal") == "comma" else "."
    grp = STYLE.get("group") or ","
    if dec == "." and grp == ",":
        return s
    return s.replace(",", "\x00").replace(".", dec).replace("\x00", grp)


def fmt(v, dp=None):
    if v is None:
        return "[NEED]"
    if dp is None:
        dp = 0 if abs(v) >= 100 or abs(v - round(v)) < 1e-9 else 1
    s = f"{v:,.{dp}f}"
    if dp and "." in s:
        s = s.rstrip("0").rstrip(".")
    return localise(s)


def indian(v):
    """12,34,567: the grouping founders in India write."""
    s = f"{v:.0f}"
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts + [tail])


def money(v, cur):
    if v is None:
        return "[NEED]"
    sym = SYMBOLS.get(cur or "", "")
    sign = "-" if v < 0 else ""
    body = indian(abs(v)) if cur == "INR" and STYLE.get("decimal") != "comma" else localise(f"{abs(v):,.0f}")
    if sym and STYLE.get("sym_after"):
        return f"{sign}{body}\u00a0{sym}"
    if sym:
        return f"{sign}{sym}{body}"
    return f"{sign}{body} {cur}" if cur else f"{sign}{body}"


def pct(v, dp=None):
    if v is None:
        return "[NEED]"
    if dp is None:
        dp = 0 if abs(v - round(v)) < 0.05 else 1
    return localise(f"{v:.{dp}f}") + "%"


def hours_text(v, dp=1):
    """'1 hour', '1.4 hours', in the founder's number style."""
    return f"{fmt(v, dp)} {'hour' if abs(v - 1) < 1e-9 else 'hours'}"


def round1(x):
    """Half up to one decimal, as ROUND(x,1) does in the workbook."""
    return None if x is None else math.floor(round(x, 6) * 10 + 0.5) / 10.0


def up(x):
    """Round up to a whole number, as ROUNDUP(ROUND(x,6),0) does in the workbook."""
    return None if x is None else int(math.ceil(round(x, 6)))


def down1(x):
    """Round down to one decimal, so a capped weekly figure never asks for more than the ceiling."""
    return None if x is None else math.floor(round(x, 6) * 10) / 10.0


def plural(n, word, many=None):
    return f"{fmt(n)} {word if n == 1 else (many or word + 's')}"


def long_date(d):
    """A weekday and date in the founder's order: 'Wednesday 21 October' or 'Wednesday, October 21'."""
    if STYLE["month_first"]:
        return f"{d.strftime('%A')}, {d.strftime('%B')} {d.day}"
    return f"{d.strftime('%A')} {d.day} {d.strftime('%B')}"


def long_date_y(d):
    if STYLE["month_first"]:
        return f"{d.strftime('%B')} {d.day}, {d.year}"
    return f"{d.day} {d.strftime('%B %Y')}"


def full_date(d):
    return f"{d.strftime('%A')}, {long_date_y(d)}" if STYLE["month_first"] else f"{d.strftime('%A')} {long_date_y(d)}"


def day_month(d):
    return f"{d.strftime('%B')} {d.day}" if STYLE["month_first"] else f"{d.day} {d.strftime('%B')}"


def round_price(p):
    if p is None:
        return None
    step = 10 if p < 500 else 50 if p < 2000 else 100 if p < 10000 else 500
    return math.ceil(round(p, 6) / step) * step


def number_style_of(raw, assume):
    """The founder's decimal mark, set once: from number_style if given, else detected from every figure they typed.
    Also the grouping mark and where the currency symbol sits, so figures are written back their way."""
    ns = str(raw.get("number_style") or "").strip().lower()
    texts = []
    for k in FIGURE_KEYS:
        v = raw.get(k)
        if isinstance(v, str) and not v.strip().startswith("="):
            texts.append(v)
    for grp in ("actuals", "channels"):
        for r_ in raw.get(grp) or []:
            if isinstance(r_, dict):
                texts += [str(x) for x in r_.values() if isinstance(x, str)]
    if ns:
        dec = "comma" if re.search(r"comma|virgule|coma|komma|\d\.\d{3},\d|\d \d{3},\d|^1\.250|,00$", ns) else "dot"
    else:
        dec = LN.detect_decimal_style(texts)
    STYLE["decimal"] = dec
    joined = " | ".join(texts + [ns])
    if any(re.search(r"(?<![\d.,])\d{1,3}[ \u00a0\u202f]\d{3}(?![\d.]|\s*[+\-*/x])", t_) and
           not re.search(r"[+*/x]\s*\d", t_) for t_ in texts + [ns]):
        STYLE["group"] = "\u00a0"
    elif re.search(r"\d{1,3}'\d{3}", joined):
        STYLE["group"] = "'"
    else:
        STYLE["group"] = "." if dec == "comma" else ","
    STYLE["sym_after"] = bool(re.search(r"\d\s*(?:€|£|zł|kr|Kč|₫|₺|₽|\$)(?![\w$])", " ".join(
        str(raw.get(k) or "") for k in MONEY_KEYS)))
    if dec == "comma":
        assume.append(("Numbers", "written your way, with a comma for decimals (1.250,50)", "assumed"))
    return dec or ""


def read_date(text):
    t = str(text or "").strip().replace(",", "")
    for f_ in ("%Y-%m-%d", "%d %B %Y", "%B %d %Y", "%d %b %Y", "%b %d %Y", "%Y-%m", "%B %Y", "%b %Y"):
        try:
            d_ = datetime.strptime(t, f_).date()
            if f_ in ("%Y-%m", "%B %Y", "%b %Y"):  # a month alone means the end of it
                nxt = date(d_.year + (d_.month == 12), d_.month % 12 + 1, 1)
                d_ = nxt - timedelta(days=1)
            return d_
        except ValueError:
            pass
    m = re.fullmatch(r"(\d{1,2})[/.](\d{1,2})[/.](\d{4})", t)
    if m:
        a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        d_, mo = (b, a) if STYLE["month_first"] else (a, b)
        try:
            return date(y, mo, d_)
        except ValueError:
            return None
    return None


def whole_months(d0, d1):
    """Whole calendar months of selling between today and the target date: the months after this one that end
    on or before the date. At least one."""
    n, y, mo = 0, d0.year, d0.month
    while True:
        y, mo = (y + 1, 1) if mo == 12 else (y, mo + 1)
        end = date(y + (mo == 12), mo % 12 + 1, 1) - timedelta(days=1)
        if end > d1:
            break
        n += 1
    return max(n, 1)


def month_after(d0, k):
    """The calendar month k months after d0's month, as a date on its first day."""
    y, mo = d0.year, d0.month + k
    y += (mo - 1) // 12
    mo = (mo - 1) % 12 + 1
    return date(y, mo, 1)


# ================================================================ inputs
TEMPLATE = {
    "made_so_far": "", "month_to_date": {}, "business": "", "currency": "", "date": "", "date_style": "", "spelling": "", "owner": "", "books_calls": "",
    "target_profit_month": "", "founder_pay_month": "", "target_basis": "", "target_revenue_month": "",
    "target_date": "", "sales_month_now": "", "margin": "", "price": "", "delivery_cost": "", "running_costs_month": "",
    "price_includes_sales_tax": "", "show_rate": "", "close_rate": "", "booking_rate": "",
    "channel_type": "inbound", "actuals": [], "leads_month_now": "", "selling_hours_week": "", "call_hours": "",
    "working_days_month": "", "call_days": "", "no_call_days": [], "days_off": [], "weeks_ahead": "", "pace_whole": "", "active_clients_max": "", "new_clients_month_max": "",
    "cash_share": "", "number_style": "", "country": "", "billing": "one-off", "months_retained": "",
    "active_clients_now": "", "target_profit_year": "", "target_kind": "", "target_profit_by_date": "",
    "confirmed": [], "channels": [], "sources": {},
}
FIGURE_KEYS = MONEY_KEYS + ("margin", "show_rate", "close_rate", "booking_rate", "leads_month_now",
                            "selling_hours_week", "call_hours", "working_days_month", "new_clients_month_max",
                            "cash_share", "months_retained", "active_clients_now")


def validate_shape(raw):
    if not isinstance(raw, dict):
        raise InputError("the inputs file must be one JSON object of named fields, not a list or a single value")
    for k in ("actuals", "channels"):
        v = raw.get(k)
        if v not in (None, "", []) and not isinstance(v, (list, dict)):
            raise InputError(f"'{k}' must be a list of named fields")
        if isinstance(v, list):
            for i, x in enumerate(v):
                if not isinstance(x, dict):
                    raise InputError(f"'{k}' item {i + 1} must be a set of named fields, not '{x}'")
    if raw.get("sources") is not None and not isinstance(raw["sources"], dict):
        raise InputError("'sources' must be a set of named fields")


def normalise(raw):
    validate_shape(raw)
    notes, needs, assume = [], [], []
    src = raw.get("sources") or {}
    I = {}

    def nonneg(key, label, hours_field=False):
        v = to_num(raw.get(key), notes, label, hours_field)
        if v is not None and v < 0:
            raise InputError(f"{label} cannot be negative (read '{raw.get(key)}')")
        return v

    I["business"] = str(raw.get("business") or "").strip()
    I["number_style"] = number_style_of(raw, assume)
    I["currency"] = currency_of(raw, assume)
    d = str(raw.get("date") or "")
    try:
        I["date"] = datetime.strptime(d, "%Y-%m-%d").date() if d else date.today()
    except ValueError:
        raise InputError(f"date '{d}' must be written YYYY-MM-DD")
    # date order and paper size follow the founder's country (never their spelling); their own writing wins
    country = str(raw.get("country") or "").strip().upper()
    loc = LN.locale_defaults(country if re.fullmatch(r"[A-Z]{2}", country) else "")
    I["country"] = country if not loc["assumed"] else ""
    I["paper"] = None if loc["assumed"] else loc["paper"]
    dollar_home = {"US": "USD", "CA": "CAD", "AU": "AUD", "NZ": "NZD", "SG": "SGD", "HK": "HKD"}
    if I["currency"] == "DOLLARS" and country in dollar_home:
        I["currency"] = dollar_home[country]
        assume[:] = [x for x in assume if x[0] != "Currency"]
    ds = str(raw.get("date_style") or "").strip().lower()
    STYLE["month_first"] = bool(re.search(r"month|mdy|m/d", ds)) if ds else loc["date_order"] == "MDY"
    if not ds and loc["assumed"]:
        assume.append(("Dates", "written day first, month in words (21 October); say which country you are in if "
                       "you write the month first", "assumed"))
    sp = str(raw.get("spelling") or "").strip().lower()
    STYLE["american"] = sp.startswith(("us", "american", "en-us"))
    I["date_style"] = "month first" if STYLE["month_first"] else "day first"
    I["spelling"] = "American" if STYLE["american"] else "British"
    I["owner"] = str(raw.get("owner") or "").strip() or "You"
    I["books_calls"] = str(raw.get("books_calls") or "").strip() or I["owner"]
    I["sources"] = src
    cf = raw.get("confirmed") or []
    I["confirmed"] = [str(x).strip().lower() for x in (cf if isinstance(cf, list) else str(cf).split(",")) if str(x).strip()]

    # ---- billing: one-off price per sale, or a monthly fee that recurs while the client stays
    bill = str(raw.get("billing") or "").strip().lower()
    I["billing"] = "monthly" if re.search(r"month|retainer|recurr|subscri|mensuel|mensual|monatlich|maandelijks", bill) \
        else "one-off"
    I["months_retained"] = nonneg("months_retained", "Months a client stays on average")
    I["active_now"] = nonneg("active_clients_now", "Clients paying you now")
    if I["billing"] == "one-off" and (I["months_retained"] or I["active_now"]):
        raise Question("the inputs give months a client stays or clients paying now, but billing is one-off. Ask the "
                       "founder: do clients pay once per sale, or a fee every month while they stay? Set billing to "
                       "'monthly' for a retainer")

    # ---- the target, and the date it is due by
    I["pay"] = nonneg("founder_pay_month", "Your pay on top of that profit")
    I["revenue_target"] = nonneg("target_revenue_month", "Revenue target a month")
    I["sales_now"] = nonneg("sales_month_now", "Sales a month now")
    I["basis"] = basis_of(raw.get("target_basis"))
    td = str(raw.get("target_date") or "").strip()
    I["target_date"] = None
    if td:
        I["target_date"] = read_date(td)
        if I["target_date"] is None:
            raise Question(f"could not read the target date '{td}'. Write it YYYY-MM-DD")
        if I["target_date"] <= I["date"]:
            raise Question(f"the target date {td} is not after today. Ask the founder for the date the target is due by")
    month = nonneg("target_profit_month", "Profit you need a month")
    year = nonneg("target_profit_year", "Profit a year")
    total = nonneg("target_profit_by_date", "Profit to make by the target date")
    kind = str(raw.get("target_kind") or "").strip().lower()
    I["target_kind"], I["profit_total"], I["year_figure"] = "run rate", None, None
    if year is not None and month is None and total is None:
        I["year_figure"] = year
        if re.search(r"run|rate|rhythm|monthly|a month|pace", kind):
            month = year / 12.0
            notes.append(f"Profit a year: {fmt(year)} read as a run rate, {fmt(month, 2)} a month, as you confirmed")
        elif re.search(r"date|by|total|end|in the bank|year end|this year", kind):
            total = year
            if I["target_date"] is None:
                I["target_date"] = date(I["date"].year, 12, 31)
                assume.append(("Target date", f"{long_date_y(I['target_date'])}, the end of this calendar year; say "
                               "if your year ends on another date", "assumed"))
        else:
            raise Question(f"the target is a yearly figure ({fmt(year)}). Ask the founder: is that the yearly rate "
                           f"you want the business running at ({fmt(year / 12.0)} a month), or profit you want made "
                           "between now and a date (which date)? Then set target_kind to 'run rate' or 'by date'")
    made = nonneg("made_so_far", "Profit already made towards the target")
    I["made_so_far"], I["target_full"] = None, None
    if total is not None:
        if I["target_date"] is None:
            raise Question("a profit to make by a date needs the date. Ask the founder for it (YYYY-MM-DD)")
        I["target_kind"] = "by date"
        if made:
            if made >= total:
                raise InputError(f"the {fmt(made)} already made meets the {fmt(total)} target, so there is nothing "
                                 "left to plan to that date. Ask the founder for the next target")
            I["made_so_far"], I["target_full"] = made, total
            notes.append(f"Profit already made: {fmt(made)} of the {fmt(total)}, so {fmt(total - made)} is left to "
                         "make by the date")
            total = total - made
        I["profit_total"] = total
    elif made:
        notes.append("Profit already made is used only for a target with a date; a monthly rate starts from today")
    I["profit"] = month
    I["months_left"] = None
    I["whole_months"] = None
    if I["target_date"]:
        I["months_left"] = (I["target_date"] - I["date"]).days / (365.25 / 12)
        I["whole_months"] = whole_months(I["date"], I["target_date"])
    m_ = raw.get("margin")
    I["margin"] = None
    if m_ not in (None, ""):
        x = to_num(re.sub(r"%|per ?cent", "", str(m_)), notes, "Margin")
        if x is not None:
            x = x * 100 if x < 1 else x
            if not 0 < x < 100:
                raise InputError(f"Margin of {fmt(x)}% cannot be right: it must sit between 0 and 100")
            I["margin"] = x

    # ---- price and costs. Prices are planned as entered, before any sales tax; no tax is ever taken off here.
    monthly = I["billing"] == "monthly"
    I["price_given"] = nonneg("price", "Monthly fee per client" if monthly else "Price per sale")
    I["delivery"] = nonneg("delivery_cost", "Delivery cost per client a month" if monthly else "Delivery cost per sale")
    I["running"] = nonneg("running_costs_month", "Running costs a month")
    I["price"] = I["price_given"]
    inc = yes_no(raw.get("price_includes_sales_tax"))
    if inc is None:  # files from version 1.0 used this key
        inc = yes_no(raw.get("prices_include_vat"))
    if inc is None and re.search(TAX_INCL, str(raw.get("price") or ""), re.I):
        inc = "yes"
    if inc is None and re.search(TAX_EXCL, str(raw.get("price") or ""), re.I):
        inc = "no"  # the plan's one neutral sales-tax line covers it; no second line about the reading
    I["price_includes_sales_tax"] = inc
    if inc == "yes":
        needs.append("Your price reads as including sales tax. The plan needs the price before any sales tax and "
                     "uses the figure as given until you give it; your accountant can confirm the figure. This plan "
                     "never works tax out")
    if I["price"] is None or I["price"] <= 0:
        raise InputError("the plan needs the price of one sale (what one client pays). Ask question 2 and run again")

    # ---- rates
    I["channel_type"] = "outbound" if str(raw.get("channel_type") or "").lower().startswith("out") else "inbound"
    I["show_est"] = to_rate(raw.get("show_rate"), "Show rate", notes)
    I["close_est"] = to_rate(raw.get("close_rate"), "Close rate on held calls", notes)
    I["booking_est"] = to_rate(raw.get("booking_rate"), "Booking rate", notes)
    I["actuals"] = read_actuals(raw.get("actuals"))
    mtd = raw.get("month_to_date")
    I["mtd"] = None
    if isinstance(mtd, dict) and mtd:
        to_ = read_date(str(mtd.get("to") or "")) if mtd.get("to") else I["date"]
        if to_ is None:
            raise InputError("month_to_date 'to' must be a date, YYYY-MM-DD")
        x = {"to": to_, "leads": _count(mtd, "leads", "enquiries"),
             "booked": _count(mtd, "booked", "bookings", "calls_booked"),
             "showed": _count(mtd, "showed", "held", "calls_held", "shows"),
             "closed": _count(mtd, "closed", "sales", "won", "closes")}
        if any(x[k] is not None for k in ("leads", "booked", "showed", "closed")):
            I["mtd"] = x
    I["leads_now"] = nonneg("leads_month_now", "Leads a month now")

    # ---- time and capacity
    I["selling_hours"] = nonneg("selling_hours_week", "Hours a week for sales calls", True)
    I["call_hours"] = nonneg("call_hours", "Hours per call held", True)
    I["working_days"] = nonneg("working_days_month", "Selling days a month")
    I["no_call_days"] = day_list(raw.get("no_call_days"))
    given = call_days_of(raw.get("call_days"))
    days = given if given is not None else list(DEFAULT_CALL_DAYS)
    I["call_days"] = [d_ for d_ in days if d_ not in I["no_call_days"]]
    if not I["call_days"]:
        raise InputError("no day is left to take calls on. Check the call days and the days you take no calls")
    if given is None and not I["no_call_days"]:
        assume.append(("Days you take calls", "Monday to Friday; say if your working week differs", "assumed"))
    I["days_off"] = dates_off(raw.get("days_off"), notes)
    I["pace_whole"] = yes_no(raw.get("pace_whole")) == "yes"
    wa = nonneg("weeks_ahead", "Weeks to show week by week")
    I["weeks_ahead"] = int(min(max(wa, 1), 26)) if wa else 6
    if I["days_off"]:
        notes.append("Days off you gave, skipped in the first week: " + ", ".join(day_month(x) for x in I["days_off"]))
    I["delivery_max"] = nonneg("new_clients_month_max", "New clients a month you can deliver for")
    am = nonneg("active_clients_max", "Clients you can serve at once")
    I["active_max"] = int(math.floor(am)) if am and monthly else None
    if am and not monthly:
        notes.append("Clients you can serve at once is used only for a monthly fee")
    elif I["active_max"]:
        notes.append(f"Clients your team can serve at once: {fmt(I['active_max'])}, the ceiling on paying clients")
    if I["call_hours"] is not None and I["call_hours"] <= 0:
        raise InputError("Hours per call held must be above zero")
    if I["selling_hours"] is not None and I["selling_hours"] <= 0:
        raise InputError("Hours a week for sales calls is zero, so no call can be held. Check the figure")
    if I["selling_hours"] is not None and I["selling_hours"] > 80:
        raise InputError(f"{fmt(I['selling_hours'])} hours a week for sales calls cannot be right. Check the figure")
    if I["delivery_max"] is not None and I["delivery_max"] <= 0:
        I["delivery_max"] = None
    I["cash_share"] = to_share(raw.get("cash_share"))
    if monthly and I["cash_share"] is not None and I["cash_share"] != 100:
        notes.append("Share paid on signing: not used for a monthly fee, because each month's fee lands that month")
    I["channels"] = read_channels(raw.get("channels"))
    for key, lab in (("selling_hours_week", "Hours a week for sales calls"), ("call_hours", "Hours per call held")):
        rv = raw.get(key)
        if isinstance(rv, str) and rv.strip() and I[{"selling_hours_week": "selling_hours", "call_hours": "call_hours"}[key]] is not None:
            got = I[{"selling_hours_week": "selling_hours", "call_hours": "call_hours"}[key]]
            if not any(n.startswith(lab + ":") for n in notes):
                notes.append(f"{lab}: {fmt(got, 2)}, as you gave it" if rv.strip() == fmt_plain(got) else
                             f"{lab}: read '{rv.strip()}' as {fmt(got, 2)}")
    plausible(I, raw)
    return I, notes, needs, assume


def plausible(I, raw):
    """Stops on a headline figure that is almost certainly misread, unless the founder confirmed it."""
    ok_ = I["confirmed"]

    def ask(key, text):
        if key not in ok_:
            raise Question(text + f" If the founder confirms it, add '{key}' to confirmed and run again")
    if I["call_hours"] is not None:
        if I["call_hours"] > 4:
            ask("call_hours", f"I read {fmt(I['call_hours'], 2)} hours for one sales call with its preparation and "
                f"follow-up (from '{raw.get('call_hours')}'). That is unusually long. Ask the founder how long one "
                "call takes, in hours.")
        if I["call_hours"] < 0.25:
            ask("call_hours", f"I read {fmt(I['call_hours'], 2)} hours for one sales call (from "
                f"'{raw.get('call_hours')}'). Ask the founder how long one call takes, in hours.")
    if I["selling_hours"] is not None and I["selling_hours"] > 60:
        ask("selling_hours_week", f"I read {fmt(I['selling_hours'])} hours a week for sales calls (from "
            f"'{raw.get('selling_hours_week')}'). Ask the founder to confirm the hours a week.")
    if I["price"] is not None and I["price"] < 50:
        ask("price", f"I read the price as {money(I['price'], I['currency'])} (from '{raw.get('price')}'). That is "
            "very low for a sale on a call. Ask the founder to confirm the price, and how they write one thousand two "
            "hundred and fifty (1,250.00 or 1.250,00).")
    for key, val in (("target_profit_month", I["profit"]), ("target_profit_by_date", I["profit_total"]),
                     ("target_revenue_month", I["revenue_target"])):
        if val is not None and 0 < val < 100:
            ask(key, f"I read the target as {money(val, I['currency'])} (from '{raw.get(key)}'). Ask the founder to "
                "confirm it, and how they write one thousand two hundred and fifty (1,250.00 or 1.250,00).")
    if I["price"] and I["profit"] and I["profit"] > 1000 * I["price"]:
        ask("price", f"I read a target of {money(I['profit'], I['currency'])} a month against a price of "
            f"{money(I['price'], I['currency'])}: over a thousand sales a month. Ask the founder to confirm both figures.")
    if I["months_retained"] is not None and not 1 <= I["months_retained"] <= 120:
        ask("months_retained", f"I read {fmt(I['months_retained'], 1)} months as how long a client stays (from "
            f"'{raw.get('months_retained')}'). Ask the founder for the average number of months a client pays for.")
    if I["active_now"] is not None and I["active_now"] > 5000:
        ask("active_clients_now", f"I read {fmt(I['active_now'])} clients paying now. Ask the founder to confirm it.")


def _count(d, *keys):
    for k in keys:
        if k in d and d[k] not in (None, ""):
            v = to_num(d[k], None, k)
            if v is not None:
                if v < 0:
                    raise InputError(f"a count cannot be negative ({k}: '{d[k]}')")
                return v
    return None


def read_actuals(v):
    if v in (None, "", []):
        return []
    rows = v if isinstance(v, list) else [v]
    out = []
    for r in rows:
        x = {"month": str(r.get("month") or r.get("window") or "").strip(),
             "leads": _count(r, "leads", "enquiries"), "booked": _count(r, "booked", "bookings", "calls_booked"),
             "showed": _count(r, "showed", "held", "calls_held", "shows"), "offers": _count(r, "offers", "offers_made"),
             "closed": _count(r, "closed", "sales", "won", "closes")}
        if x["booked"] is not None and x["showed"] is not None and x["showed"] > x["booked"]:
            raise InputError(f"actuals {x['month'] or ''}: {fmt(x['showed'])} calls held but only {fmt(x['booked'])} "
                             "booked. Check the two counts (a rescheduled call counts once, when it is held)")
        if x["showed"] is not None and x["closed"] is not None and x["closed"] > x["showed"]:
            raise InputError(f"actuals {x['month'] or ''}: {fmt(x['closed'])} sales from {fmt(x['showed'])} held calls. "
                             "Check the counts, or leave sales that never had a call out of them")
        if x["leads"] is not None and x["booked"] is not None and x["booked"] > x["leads"]:
            raise InputError(f"actuals {x['month'] or ''}: {fmt(x['booked'])} booked from {fmt(x['leads'])} leads. "
                             "Check the counts")
        if any(x[k] is not None for k in ("leads", "booked", "showed", "closed")):
            out.append(x)
    out.sort(key=lambda r: r["month"])
    return out[-3:]


def read_channels(v):
    if v in (None, "", []):
        return []
    rows = v if isinstance(v, list) else [v]
    out = []
    for r in rows:
        name = str(r.get("name") or r.get("channel") or r.get("source") or "").strip()
        if not name:
            continue
        out.append({"name": name, "leads": _count(r, "leads", "enquiries"),
                    "booked": _count(r, "booked", "bookings"), "showed": _count(r, "showed", "held")})
    return out


# ================================================================ the plan
def rate(value, tag, n=None, basis=""):
    return {"value": value, "tag": tag, "n": n, "basis": basis}


def rates_from(I):
    """Each rate the chain climbs, tagged: measured (10 or more events), measured, directional (fewer),
    your estimate, assumed (planning default) or unknown."""
    A = I["actuals"]
    tot = {k: (sum(r[k] for r in A if r[k] is not None) if any(r[k] is not None for r in A) else None)
           for k in ("leads", "booked", "showed", "offers", "closed")}
    months = len(A)
    win = ("your last month" if months == 1 else f"your last {months} months" if months else "")
    chans = [ch for ch in I["channels"] if ch["leads"] is not None and ch["booked"] is not None]
    if not A and chans:
        # no monthly counts, but counts by source over 90 days: their totals are the measured window
        tot["leads"] = sum(ch["leads"] for ch in chans)
        tot["booked"] = sum(ch["booked"] for ch in chans)
        if all(ch["showed"] is not None for ch in chans):
            tot["showed"] = sum(ch["showed"] for ch in chans)
        months = 3
        win = "your channel counts, last 90 days"
    dflt = DEFAULT_RATES[I["channel_type"]]
    R = {}

    def from_counts(num, den, label):
        if num is None or not den:
            return None
        v = 100.0 * num / den
        tag = "measured" if den >= MIN_EVENTS else "measured, directional"
        return rate(v, tag, int(den), f"{fmt(num)} of {fmt(den)} {label}, {win}")

    R["show"] = from_counts(tot["showed"], tot["booked"], "booked calls")
    R["close"] = from_counts(tot["closed"], tot["showed"], "held calls")
    R["booking"] = from_counts(tot["booked"], tot["leads"], "leads")
    for k, est, d in (("show", I["show_est"], dflt["show"]), ("close", I["close_est"], dflt["close"]),
                      ("booking", I["booking_est"], None)):
        if R[k] and R[k]["tag"] == "measured, directional":
            R[k]["pessimistic"] = d if d is not None else R[k]["value"]
        if R[k] is None and est is not None:
            v, kind, n = est
            if kind == "counted":
                tag = "measured" if n >= MIN_EVENTS else "measured, directional"
                R[k] = rate(v, tag, n, f"your count, {fmt(round(v * n / 100))} of {fmt(n)}")
                if tag == "measured, directional":
                    R[k]["pessimistic"] = d if d is not None else v
            else:
                R[k] = rate(v, "your estimate", None, "your estimate")
        if R[k] is None:
            if d is not None:
                R[k] = rate(d, "assumed", None, f"planning default for {I['channel_type']} calls")
            else:
                R[k] = rate(None, "unknown", None, "leads are not counted, so the booking rate is not known")
    # offers: separated only where offers are counted on 10 or more held calls and 10 or more offers
    R["offer"] = R["offer_conv"] = None
    if tot["offers"] and tot["showed"] and tot["closed"] is not None and tot["showed"] >= MIN_EVENTS \
            and tot["offers"] >= MIN_EVENTS and tot["offers"] <= tot["showed"]:
        R["offer"] = rate(100.0 * tot["offers"] / tot["showed"], "measured", int(tot["showed"]),
                          f"{fmt(tot['offers'])} offers on {fmt(tot['showed'])} held calls, {win}")
        R["offer_conv"] = rate(100.0 * tot["closed"] / tot["offers"], "measured", int(tot["offers"]),
                               f"{fmt(tot['closed'])} sales from {fmt(tot['offers'])} offers, {win}")
    leads_now = I["leads_now"]
    if leads_now is None and tot["leads"] and months:
        leads_now = tot["leads"] / months
    return R, tot, months, leads_now


def per_held(R):
    """Sales per held call."""
    if R.get("offer"):
        return R["offer"]["value"] / 100.0 * R["offer_conv"]["value"] / 100.0
    return R["close"]["value"] / 100.0


def climb(closes, R):
    """Up the chain from whole sales: held, booked and leads are each rounded up to whole calls."""
    c = {"closes": closes}
    if R.get("offer"):
        c["offers"] = up(closes / (R["offer_conv"]["value"] / 100.0))
        c["held"] = up(c["offers"] / (R["offer"]["value"] / 100.0))
    else:
        c["offers"] = None
        c["held"] = up(closes / (R["close"]["value"] / 100.0))
    c["booked"] = up(c["held"] / (R["show"]["value"] / 100.0))
    b = R["booking"]["value"]
    c["leads"] = up(c["booked"] / (b / 100.0)) if b else None
    return c


def unit_of(P, price):
    """What one sale (one-off) or one paying client for a month (monthly fee) is worth against the target."""
    if P["form"] == "contribution":
        return price - P["delivery"]
    if P["form"] == "margin":
        return price * P["inputs"]["margin"] / 100.0
    return price


def ret_closes(P, price, L=None):
    """Monthly fees: paying clients needed, and new clients a month to get there by the date and hold it.
    Clients leave at 1 in L a month (L = average months a client stays), so active clients move as
    A(k) = A(k-1) x (1 - 1/L) + N. Run rate: A(T) must reach the clients needed. By date: the paying
    client-months from now to the date must cover the profit, the running costs and your pay."""
    u = unit_of(P, price)
    if u <= 0:
        return None
    R_ = P["ret"]
    L = R_["L"] if L is None else L
    T, A0 = R_["T"], R_["A0"]
    out = {"unit": u, "A": None, "build": 0, "hold": 0}
    if R_["mode"] == "run rate":
        A = up(P["need_ret"] / u)
        out["A"] = A
        if L:
            rT = (1 - 1.0 / L) ** T
            out["build"] = up(max(0.0, A - A0 * rT) / (L * (1 - rT)))
            out["hold"] = up(A / L)
        else:
            out["build"] = up(max(0.0, A - A0) / T)
        out["closes"] = max(out["build"], out["hold"])
    else:
        U = (R_["total"] + T * R_["fixed"]) / u
        out["client_months"] = U
        if L:
            rT = (1 - 1.0 / L) ** T
            S = (L - 1) * (1 - rT)
            out["now_carry"] = A0 * S
            out["build"] = up(max(0.0, U - A0 * S) / (L * (T - S)))
        else:
            out["now_carry"] = A0 * T
            out["build"] = up(max(0.0, U - A0 * T) / (T * (T + 1) / 2.0))
        out["closes"] = out["build"]
    return out


def closes_needed(P, price, cps=None, L=None):
    """Whole sales (new clients, for a monthly fee) a month for the plan's target at a given price."""
    if P.get("billing") == "monthly":
        r_ = ret_closes(P, price, L)
        return None if r_ is None else r_["closes"]
    if P["form"] == "contribution":
        c = (cps if cps is not None else price - P["delivery"])
        if c <= 0:
            return None
        return up(P["need"] / c)
    return up(P["revenue_req"] / price)


def price_for_closes(P, k):
    """The lowest price at which the target needs k sales (or new clients) a month or fewer."""
    if P.get("billing") != "monthly":
        if P["form"] == "contribution":
            return P["need"] / k + P["delivery"]
        return P["revenue_req"] / k
    hi = P["price"]
    for _ in range(60):
        c_ = closes_needed(P, hi)
        if c_ is not None and c_ <= k:
            break
        hi *= 2
    else:
        return None
    lo = P["price"]
    for _ in range(80):
        mid = (lo + hi) / 2
        c_ = closes_needed(P, mid)
        if c_ is not None and c_ <= k:
            hi = mid
        else:
            lo = mid
    return hi


def simulate(P, n_build, n_hold, months):
    """Paying clients and profit month by month at a pace of new clients (monthly fees only)."""
    R_ = P["ret"]
    L, A, u = R_["L"], R_["A0"], P["ret_res"]["unit"]
    target_A = P["ret_res"].get("A")
    rows, reached = [], False
    for k in range(1, months + 1):
        n = n_hold if reached and n_hold is not None else n_build
        A = A * (1 - 1.0 / L) + n if L else A + n
        if R_.get("M"):
            A = min(A, float(R_["M"]))
        prof = A * u - R_["fixed"]
        rows.append({"month": month_after(datetime.strptime(P["date"], "%Y-%m-%d").date(), k).isoformat(),
                     "new": n, "active": A, "profit": prof})
        if target_A is not None and A >= target_A - 1e-6:
            reached = True
    return rows


def plan(I):
    notes, needs, assume = I.pop("_notes"), I.pop("_needs"), I.pop("_assume")
    cur = I["currency"]
    P = {"inputs": {k: (v.isoformat() if isinstance(v, date) else v) for k, v in I.items()}, "currency": cur,
         "business": I["business"], "date": I["date"].isoformat()}
    price = I["price"]
    P["price"] = price
    # ---- defaults said out loud
    sell = I["selling_hours"] if I["selling_hours"] is not None else SELLING_HOURS
    if I["selling_hours"] is None:
        assume.append(("Hours a week for sales calls", f"{fmt(SELLING_HOURS)} (planning default)", "assumed"))
    callh = I["call_hours"] if I["call_hours"] is not None else CALL_HOURS
    if I["call_hours"] is None:
        assume.append(("Hours per call held", f"{fmt(CALL_HOURS)}: a 45 to 60 minute call plus preparation and "
                       "follow-up (planning default; your own figure wins)", "assumed"))
    callable_days = len(I["call_days"])
    wdays = I["working_days"] if I["working_days"] else WORKING_DAYS * callable_days / 5.0
    if not I["working_days"]:
        assume.append(("Selling days a month", f"{fmt(wdays, 1)}" + (" (planning default of 20 for a five-day week, "
                       f"scaled to your {callable_days} call days)" if callable_days != 5 else " (planning default)"),
                       "assumed"))
    share = I["cash_share"] if I["cash_share"] is not None and I["billing"] != "monthly" else CASH_SHARE
    if I["cash_share"] is None and I["billing"] != "monthly":
        assume.append(("Share of the price paid in the month they sign", "100% (default: paid in full on signing)",
                       "assumed"))
    if I["delivery_max"] is None:
        assume.append(("New clients a month you can deliver for", "not limited (you did not give a limit)",
                       "assumed"))
    P.update({"sell": sell, "callh": callh, "wdays": wdays, "share": share, "delivery_max": I["delivery_max"]})

    # ---- step 1: from profit to sales
    P["delivery"] = I["delivery"]
    P["running"] = I["running"]
    P["billing"] = I["billing"]
    monthly = I["billing"] == "monthly"
    P["sale_word"] = "new client" if monthly else "sale"
    P["target_kind"] = I["target_kind"]
    P["target_date"] = I["target_date"].isoformat() if I["target_date"] else None
    P["months_left"], P["whole_months"] = I["months_left"], I["whole_months"]
    if I["target_kind"] == "by date":
        # money to make by a date: the months left are counted, never assumed to be a year
        P["profit_total"] = I["profit_total"]
        P["made_so_far"], P["target_full"] = I.get("made_so_far"), I.get("target_full")
        I["profit"] = I["profit_total"] / I["whole_months"]
        if not monthly:
            notes.append(f"Profit by {long_date_y(I['target_date'])}: {money(I['profit_total'], cur)} over "
                         f"{plural(I['whole_months'], 'whole month')} of selling is {money(I['profit'], cur)} a month")
    profit, pay = I["profit"], I["pay"] or 0.0
    P["profit"], P["pay"] = profit, pay
    P["basis"] = I["basis"]
    P["form"], P["revenue_req"], P["need"], P["cps"] = None, None, None, None
    cross = None
    if profit is not None and profit > 0:
        if I["delivery"] is not None:
            cps = price - I["delivery"]
            if cps <= 0:
                raise InputError(
                    f"at a {'monthly fee' if monthly else 'price'} of {money(price, cur)} and a delivery cost of "
                    f"{money(I['delivery'], cur)}{' a month' if monthly else ''}, each "
                    f"{'client' if monthly else 'sale'} loses {money(-cps, cur)}{' a month' if monthly else ''}, so "
                    "no number of sales reaches a profit. If both figures are right, the price is the first problem, "
                    "before any sales plan. Check them and run again")
            running = I["running"]
            if running is None:
                running = 0.0
                needs.append("Running costs a month (software, insurance, accountant, premises): not given, so none "
                             "are counted and the plan is short by whatever they are")
            P["running"] = running
            P["cps"] = cps
            P["need"] = profit + pay + running
            P["form"] = "contribution"
            if I["margin"]:
                cross = (profit / (I["margin"] / 100.0)) / price
        elif I["margin"]:
            P["form"] = "margin"
            P["revenue_req"] = profit / (I["margin"] / 100.0)
            notes.append(f"Margin {pct(I['margin'])} is your figure: the plan takes revenue as profit over margin. "
                         "With what one client costs to deliver and your running costs, it can check that")
        elif I["revenue_target"]:
            P["form"] = "revenue"
            P["revenue_req"] = I["revenue_target"]
            needs.append("What one client costs to deliver (or your margin): without it the plan cannot start from "
                         "your profit, so it runs on the revenue you gave. A revenue target without costs may be the "
                         "wrong target")
        else:
            raise InputError("to work back from profit the plan needs what one client costs to deliver, or your "
                             "margin. Ask question 2 and run again")
    elif I["revenue_target"]:
        P["form"] = "revenue"
        P["revenue_req"] = I["revenue_target"]
        if I["delivery"] is not None:
            P["cps"] = price - I["delivery"]
            P["running"] = I["running"] or 0.0
        needs.append("The profit you need a month: the plan runs on the revenue you gave. Revenue can be hit with "
                     "nothing left over, so give the profit and it will start there")
    else:
        raise InputError("the plan needs a target: the profit the business must make each month (or, if that is "
                         "all you have, a revenue target). Ask question 1 and run again")
    if P["basis"] == "take-home" and profit:
        needs.append("Your profit figure is take-home. The business has to make more than that before tax, so every "
                     "figure in this plan is too low. Ask your accountant for the before-tax figure and re-run; this "
                     "plan never works out tax")
    elif P["basis"] is None and profit:
        needs.append("Is the profit figure before tax or what you want to take home? The plan reads it as before "
                     "tax. If it is take-home, every figure here is too low until your accountant gives the "
                     "before-tax figure")

    P["ret"] = None
    if monthly:
        L = I["months_retained"]
        if L is None:
            needs.append("How many months a client stays on average: not given, so the plan counts no client leaving. "
                         "Every client who leaves adds one more new client a month to the plan")
        A0 = I["active_now"]
        if A0 is None:
            A0 = 0.0
            needs.append("How many clients pay you now: not given, so the plan starts from none")
        T = I["whole_months"]
        if T is None:
            T = RET_HORIZON
            assume.append(("When the target is due", f"in {RET_HORIZON} whole months (planning default); give a date "
                           "and the plan works to it", "assumed"))
        fixed = (pay + (P["running"] or 0.0)) if P["form"] == "contribution" else 0.0
        P["need_ret"] = {"contribution": P["need"], "margin": profit}.get(P["form"], P["revenue_req"])
        P["ret"] = {"A0": A0, "L": L, "T": T, "mode": I["target_kind"], "fixed": fixed,
                    "total": I.get("profit_total") if P["form"] != "revenue" else None}
        if I["target_kind"] == "by date" and P["form"] == "revenue":
            raise InputError("a target by a date is planned from profit; give the profit to make by the date")
        P["ret"]["M"] = I.get("active_max")
        res = ret_closes(P, price)
        P["ret_res"] = res
        closes = res["closes"]
        P["closes_exact"] = float(closes)
        P["revenue_req"] = (res["A"] or 0) * price
    else:
        closes = closes_needed(P, price)
        if P["form"] == "contribution":
            P["closes_exact"] = P["need"] / P["cps"]
            P["revenue_req"] = P["closes_exact"] * price
        else:
            P["closes_exact"] = P["revenue_req"] / price
    P["closes"] = closes
    P["revenue_plan"] = closes * price
    if cross is not None:
        diff = abs(cross - P["closes_exact"]) / max(P["closes_exact"], 1e-9)
        P["cross"] = {"margin_sales": cross, "contribution_sales": P["closes_exact"], "apart": diff}
        if diff > 0.10:
            needs.append(f"Your margin of {pct(I['margin'])} gives {fmt(cross, 1)} sales a month; your costs give "
                         f"{fmt(P['closes_exact'], 1)}. The plan runs on your costs. Which margin did you mean?")
    if P["form"] == "revenue" and P["cps"] is not None:
        P["profit_at_revenue"] = closes * P["cps"] - P["running"]
    P["now"] = None
    if monthly and P["ret"]["A0"] and P["cps"] is not None:
        P["now"] = {"active": P["ret"]["A0"], "left": P["ret"]["A0"] * P["cps"] - (P["running"] or 0) - pay}
    elif I.get("sales_now") and P["cps"] is not None:
        left = I["sales_now"] / price * P["cps"] - (P["running"] or 0) - pay
        P["now"] = {"sales": I["sales_now"], "left": left}

    # ---- step 2: the chain
    R, tot, months, leads_now = rates_from(I)
    P["rates"], P["actuals_total"], P["months"], P["leads_now"] = R, tot, months, leads_now
    for k, lab, hi in (("show", "Show rate", 90), ("close", "Close rate on held calls", 50)):
        if R[k]["tag"] == "your estimate" and R[k]["value"] > hi:
            notes.append(f"{lab} {pct(R[k]['value'])} is your estimate and sits high. Plan on what has happened, "
                         "not on a hope; if it is a hope, say so and the planning default is used")
    c = climb(closes, R)
    P["chain"] = c
    if c["leads"] is None:
        needs.append("Leads: not known until you count how many enquiries turn into a booked call")
    P["multiple"] = c["leads"] / leads_now if (c["leads"] and leads_now) else None
    if any(R[k].get("pessimistic") is not None for k in ("show", "close", "booking")):
        rp = copy.deepcopy(R)
        for k in ("show", "close", "booking"):
            if rp[k].get("pessimistic") is not None:
                rp[k]["value"] = rp[k]["pessimistic"]
        P["pessimistic"] = climb(closes, rp)
    not_measured = [k for k in ("show", "close", "booking") if R[k]["tag"] != "measured"]
    P["not_measured"] = not_measured
    short = bool(months) and months < 3
    P["short_window"] = short
    P["replan"] = (I["date"] + timedelta(days=REPLAN_ASSUMED if (not_measured or short) else REPLAN_MEASURED)).isoformat()

    # ---- step 3: time and capacity
    cr = per_held(R)
    P["per_held"] = cr
    hrs = c["held"] * callh / WEEKS_PER_MONTH
    P["hours_week"] = hrs
    P["hours_share"] = hrs / sell
    P["calendar"] = "breaks" if hrs > sell + 1e-9 else ("fits, tightly" if hrs >= TIGHT * sell else "fits")
    P["max_held"] = sell * WEEKS_PER_MONTH / callh
    P["cal_closes"] = P["max_held"] * cr
    P["delivery_state"] = None
    if I["delivery_max"]:
        P["delivery_state"] = "breaks" if closes > I["delivery_max"] + 1e-9 else "fits"

    # ---- clients at once (monthly fees): the team's ceiling on paying clients
    P["active_bind"] = None
    M_ = I.get("active_max") if monthly else None
    if M_:
        rr_ = P["ret_res"]
        if P["ret"]["mode"] == "run rate" and rr_["A"] > M_:
            P["active_bind"] = (f"the target needs {plural(rr_['A'], 'paying client')} at once and your team can serve "
                                f"{fmt(M_)}")
        elif P["ret"]["mode"] != "run rate" and rr_.get("client_months", 0) > M_ * P["ret"]["T"] + 1e-6:
            P["active_bind"] = (f"the target needs about {fmt(rr_['client_months'], 1)} paying client-months by the "
                                f"date, and serving {fmt(M_)} at once gives at most {fmt(M_ * P['ret']['T'])}")
        if P["active_bind"]:
            P["delivery_state"] = "breaks"

    # ---- step 4: binding constraint, in the order calendar (and delivery), show, volume, skill
    bind, because = None, None
    cal_b, del_b = P["calendar"] == "breaks", P["delivery_state"] == "breaks"
    if cal_b or del_b:
        if cal_b and del_b:
            if (I["delivery_max"] or 0) <= P["cal_closes"]:
                bind = "delivery"
            else:
                bind = "calendar"
        else:
            bind = "calendar" if cal_b else "delivery"
        if P["active_bind"]:
            bind = "delivery"
        if bind == "delivery" and P["active_bind"]:
            because = P["active_bind"]
        elif bind == "calendar":
            because = (f"the plan needs {plural(c['held'], 'held call')} a month, {fmt(hrs, 1)} hours a week at "
                       f"{plural(round(callh, 1), 'hour')} a call, against your {fmt(sell, 1)}. Your calendar breaks at "
                       f"{fmt(P['max_held'], 1)} held calls a month, which at your rates is {fmt(P['cal_closes'], 1)} "
                       + (f"new clients a month" if monthly else f"sales and {money(P['cal_closes'] * price, cur)} of sales"))
        else:
            because = (f"the plan needs {plural(closes, 'new client')} a month and you can deliver for "
                       f"{fmt(I['delivery_max'])}")
    elif R["show"]["value"] < SHOW_ALARM:
        bind = "show rate"
        at = up(c["held"] / (LEVER["show"] / 100.0))
        because = (f"{pct(R['show']['value'])} of booked calls turn up ({R['show']['tag']}), under the 65% line; "
                   f"at {pct(LEVER['show'])} you would need {at} bookings a month, not {c['booked']}")
        P["show_lever_booked"] = at
    elif P["multiple"] is not None and P["multiple"] >= VOLUME_LIMIT:
        bind = "lead volume"
        because = (f"the plan needs {c['leads']} leads a month, {fmt(P['multiple'], 1)} times the "
                   f"{fmt(leads_now, 1)} you get now. Change a rate or the target before spending on leads")
    elif R["close"]["value"] < CLOSE_FLOOR and not R.get("offer"):
        bind = "close rate"
        because = (f"{pct(R['close']['value'])} of held calls buy ({R['close']['tag']}), under 20%")
    P["binding"], P["because"] = bind, because
    if bind is None and c["leads"] is None:
        P["volume_note"] = "Lead volume cannot be checked: leads are not counted."
    elif bind is None and P["multiple"] is not None and P["multiple"] > 1.05:
        P["volume_note"] = (f"The gap to watch is lead volume: the plan needs {c['leads']} leads a month, "
                            f"{fmt(P['multiple'], 1)} times the {fmt(leads_now, 1)} you get now. That is under the "
                            "three times line, so it is a gap to close, not the thing that breaks.")

    # ---- the price the ceiling needs (when calendar or delivery binds)
    P["price_needed"] = None
    if bind == "delivery" and P["active_bind"] and P["ret"]["mode"] == "run rate" and P["form"] == "contribution":
        pr = round_price(P["need_ret"] / M_ + P["delivery"])
        cn = closes_needed(P, pr)
        if cn is not None:
            cc = climb(cn, R)
            h2 = cc["held"] * callh / WEEKS_PER_MONTH
            P["price_needed"] = {"price": pr, "closes": cn, "held": cc["held"], "booked": cc["booked"], "hours": h2,
                                 "fit": "fits, tightly" if h2 >= TIGHT * sell else ("fits" if h2 <= sell else "breaks"),
                                 "rise": (pr - price) / price * 100}
    elif bind in ("calendar", "delivery") and not P["active_bind"]:
        ceil_closes = P["cal_closes"] if bind == "calendar" else I["delivery_max"]
        if bind == "delivery" and cal_b:
            ceil_closes = min(ceil_closes, P["cal_closes"])
        k = math.floor(round(ceil_closes, 6))
        found = None
        while k >= 1:
            pn = price_for_closes(P, k)
            if pn is None:
                break
            pr = round_price(pn)
            cn = closes_needed(P, pr)
            cc = climb(cn, R)
            h2 = cc["held"] * callh / WEEKS_PER_MONTH
            ok_cal = h2 <= sell + 1e-9
            ok_del = (I["delivery_max"] is None) or cn <= I["delivery_max"] + 1e-9
            if ok_cal and ok_del:
                found = {"price": pr, "closes": cn, "held": cc["held"], "booked": cc["booked"], "hours": h2,
                         "fit": "fits, tightly" if h2 >= TIGHT * sell else "fits",
                         "rise": (pr - price) / price * 100}
                break
            k -= 1
        P["price_needed"] = found

    # ---- step 5 and 6: scenarios
    P["scenarios"] = scenarios(P, R, price)
    singles = [s for s in P["scenarios"] if s["kind"] == "lever"]
    comb = next((s for s in P["scenarios"] if s["kind"] == "combined"), None)
    P["three_bets"] = bool(P["calendar"] == "breaks" and comb and comb["fits"] and singles
                           and not any(s["fits"] for s in singles))
    P["met"] = [s for s in P["scenarios"] if s["kind"] == "met"]

    # ---- step 7: channels
    P["channels"] = channel_loads(I["channels"], c, R)

    # ---- step 8: hiring trigger
    if bind == "delivery":
        P["hire"] = ("Not a sales hire: delivery is the limit, and a sales hire adds no delivery capacity. "
                     "Price and fit first.")
        P["hire_state"] = "delivery"
    elif comb and not comb["fits_cal"]:
        start = ""
        if I["target_date"]:
            sd = I["target_date"] - timedelta(weeks=RAMP["full_pace_week"])
            start = (f" To be at full pace by {long_date_y(I['target_date'])}, they would start by {long_date_y(sd)}."
                     if sd >= I["date"] else
                     f" Your target date of {long_date_y(I['target_date'])} is under {RAMP['full_pace_week']} weeks "
                     "away, so a hire cannot be at full pace in time.")
        ramp = (f"Planning default: a setter first, to take booking and qualifying off your hours; productive in "
                f"{RAMP['productive']}, at full pace from week {RAMP['full_pace_week']}.{start}")
        pn = P.get("price_needed")
        if pn and pn["rise"] <= 100:
            P["hire"] = (f"Triggered only if the price stays at {money(price, cur)}: even with the levers together the calls "
                         f"need {fmt(comb['hours'], 1)} hours a week against your {fmt(sell, 1)}. At "
                         f"{money(pn['price'], cur)} no hire is needed. If you keep today's price, the planning default is "
                         f"{ramp[len('Planning default: '):]}")
            P["hire_state"] = "triggered at today's price"
        else:
            P["hire"] = (f"A hire is triggered: even with the levers together the calls need {fmt(comb['hours'], 1)} hours "
                         f"a week against your {fmt(sell, 1)}. {ramp} Hiring is never the first lever: fix the rates "
                         "first.")
            P["hire_state"] = "triggered"
    else:
        P["hire"] = "Not triggered: the levers in the scenarios bring the plan inside your hours. No hire is planned."
        P["hire_state"] = "not reached"
    P["hire_start"] = None
    if P["hire_state"].startswith("triggered") and I["target_date"]:
        sd = I["target_date"] - timedelta(weeks=RAMP["full_pace_week"])
        P["hire_start"] = sd if sd >= I["date"] else None

    # ---- step 9: pace, never above a ceiling
    ceilings = [P["cal_closes"]] + ([I["delivery_max"]] if I["delivery_max"] else [])
    lim = min(ceilings)
    P["capped"] = closes > lim + 1e-9
    if P["capped"]:
        pc = lim
        held_m = pc / cr
        booked_m = held_m / (R["show"]["value"] / 100.0)
        P["pace"] = {"closes": down1(pc / WEEKS_PER_MONTH), "held": down1(held_m / WEEKS_PER_MONTH),
                     "booked": down1(booked_m / WEEKS_PER_MONTH),
                     "offers": down1(held_m * R["offer"]["value"] / 100.0 / WEEKS_PER_MONTH) if R.get("offer") else None,
                     "per_day": down1(booked_m / wdays), "held_day": down1(held_m / wdays),
                     "closes_day": down1(pc / wdays), "closes_month": down1(pc),
                     "basis": "your calendar" if lim == P["cal_closes"] else "your delivery limit"}
    else:
        # uncapped: the plan's own figures a week, to one decimal; never above a ceiling
        P["pace"] = {"closes": round1(closes / WEEKS_PER_MONTH),
                     "held": min(round1(c["held"] / WEEKS_PER_MONTH), down1(sell / callh)),
                     "booked": round1(c["booked"] / WEEKS_PER_MONTH),
                     "offers": round1(c["offers"] / WEEKS_PER_MONTH) if c["offers"] else None,
                     "per_day": round1(c["booked"] / wdays), "held_day": round1(c["held"] / wdays),
                     "closes_day": round1(closes / wdays), "closes_month": closes, "basis": "the plan"}
        if I["delivery_max"]:
            P["pace"]["closes"] = min(P["pace"]["closes"], down1(I["delivery_max"] / WEEKS_PER_MONTH))

    # ---- cash, kept apart from sales
    if monthly:
        A_t = (P["ret_res"].get("A") or 0)
        P["cash_in_month"] = A_t * price
        P["cash_gap_first_month"] = 0.0
    else:
        P["cash_in_month"] = closes * price * share / 100.0
        P["cash_gap_first_month"] = P["revenue_plan"] - P["cash_in_month"]

    # ---- the date: months left, and when the target is first reached
    reach = {}
    n_cap = math.floor(round(lim, 6)) if P["capped"] else None
    if monthly:
        rr = P["ret_res"]
        Tm = P["ret"]["T"]
        horizon = max(Tm, 12)
        plan_rows = simulate(P, closes, rr["hold"] if rr["hold"] else closes, horizon)
        reach["rows"] = plan_rows[:max(Tm, 1)]
        if P["ret"]["mode"] == "run rate":
            hit = next((r_ for r_ in simulate(P, closes, rr["hold"] or closes, 60) if r_["active"] >= rr["A"] - 1e-6), None)
            reach["month"] = hit["month"] if hit else None
            if n_cap is not None:
                cap_rows = simulate(P, n_cap, n_cap, 60)
                hit2 = next((r_ for r_ in cap_rows if r_["active"] >= rr["A"] - 1e-6), None)
                reach["cap_month"] = hit2["month"] if hit2 else None
                reach["cap_long_run"] = (n_cap * P["ret"]["L"]) if P["ret"]["L"] else None
        else:
            reach["total_plan"] = sum(r_["profit"] for r_ in plan_rows[:Tm])
            if n_cap is not None:
                reach["total_cap"] = sum(r_["profit"] for r_ in simulate(P, n_cap, n_cap, Tm))
        reach["cap_n"] = n_cap
        if P["form"] == "contribution" and closes:
            n12 = n_cap if n_cap is not None else closes
            h12 = rr["hold"] if (n_cap is None and rr["hold"]) else n12
            reach["twelve"] = sum(r_["profit"] for r_ in simulate(P, n12, h12, 12))
    elif P["form"] in ("contribution",) and n_cap is not None:
        reach["cap_n"] = n_cap
        reach["cap_profit_month"] = n_cap * P["cps"] - (P["running"] or 0) - pay
        if I["target_kind"] == "by date":
            reach["total_cap"] = reach["cap_profit_month"] * I["whole_months"]
    P["reach"] = reach

    # ---- step 10: first week and headline
    P["first_week"] = first_week(P, I, R)
    P["pace_whole"] = I.get("pace_whole")
    P["weeks"] = weeks_ahead(P, I, I.get("weeks_ahead") or 6)
    P["mtd"] = month_so_far(P, I)
    outside = [d for d in I["days_off"] if d.weekday() not in (I["call_days"] or [0, 1, 2, 3, 4]) and d > I["date"]]
    P["off_days_note"] = (", ".join(f"{long_date(d)}" for d in outside) + (" falls" if len(outside) == 1 else " fall")
                          + " outside the days you take calls, so it costs no selling day." if outside else None)
    if P["off_days_note"]:
        notes.append(P["off_days_note"].rstrip("."))
    P["headline"] = headline(P, R)
    P["needs"], P["notes"], P["assume"] = needs, notes, assume
    P["tax_line"] = SALES_TAX_LINE
    P["style"] = dict(STYLE)
    return P


def scenarios(P, R, price):
    """Current rates, each lever alone, then all three together, each from whole sales. A lever the rates
    already meet gets no row. Where the calendar or delivery binds, the price the ceiling needs is a row."""
    out = []
    sell, callh, wdays = P["sell"], P["callh"], P["wdays"]
    sep = bool(R.get("offer"))

    def row(name, kind, rr, pr, L=None):
        cl = closes_needed(P, pr, L=L)
        if cl is None:
            return
        cc = climb(cl, rr)
        h = cc["held"] * callh / WEEKS_PER_MONTH
        fits_cal = h <= sell + 1e-9
        fits_del = P["delivery_max"] is None or cl <= P["delivery_max"] + 1e-9
        out.append({"name": name, "kind": kind, "price": pr, "show": rr["show"]["value"],
                    "close": rr["close"]["value"] if not sep else None,
                    "offer": rr["offer"]["value"] if sep else None, "closes": cl, "held": cc["held"],
                    "booked": cc["booked"], "leads": cc["leads"], "per_day": cc["booked"] / wdays, "hours": h,
                    "fits_cal": fits_cal, "fits": fits_cal and fits_del,
                    "L": L if L is not None else (P["ret"]["L"] if P.get("ret") else None),
                    "verdict": ("breaks" if not (fits_cal and fits_del) else
                                "fits, tightly" if h >= TIGHT * sell else "fits")})

    row("Today's rates", "current", R, price)
    rs = copy.deepcopy(R)
    if R["show"]["value"] >= LEVER["show"]:
        out.append({"name": f"Show rate to {pct(LEVER['show'])} (planning default)", "kind": "met",
                    "note": f"already met: {pct(R['show']['value'])}"})
    else:
        rs["show"]["value"] = LEVER["show"]
        row(f"Show rate to {pct(LEVER['show'])} (planning default)", "lever", rs, price)
    row(f"{'Fee' if P.get('billing') == 'monthly' else 'Price'} up 10% (to "
        f"{money(price * (1 + LEVER['deal_step']), P['currency'])})", "lever", R,
        price * (1 + LEVER["deal_step"]))
    rc = copy.deepcopy(R)
    if sep:
        if R["offer"]["value"] >= LEVER["offer"]:
            out.append({"name": "Offer made on every held call", "kind": "met",
                        "note": f"already met: {pct(R['offer']['value'])}"})
        else:
            rc["offer"]["value"] = LEVER["offer"]
            row("Offer made on every held call", "lever", rc, price)
    else:
        if R["close"]["value"] >= LEVER["close"]:
            out.append({"name": f"Close rate on held calls to {pct(LEVER['close'])} (planning default)", "kind": "met",
                        "note": f"already met: {pct(R['close']['value'])}"})
        else:
            rc["close"]["value"] = LEVER["close"]
            row(f"Close rate on held calls to {pct(LEVER['close'])} (planning default)", "lever", rc, price)
    cb = copy.deepcopy(rc)
    cb["show"]["value"] = max(R["show"]["value"], LEVER["show"])
    if sum(1 for o in out if o["kind"] == "lever") >= 2:
        row("All three together" if not any(o["kind"] == "met" for o in out) else "The levers together", "combined",
            cb, price * (1 + LEVER["deal_step"]))
    if P.get("ret") and P["ret"]["L"]:
        L2 = P["ret"]["L"] + 2
        row(f"Clients stay 2 months longer (to {fmt(L2, 1)} months)", "retention", R, price, L=L2)
    if P.get("price_needed"):
        row(f"The {'fee' if P.get('billing') == 'monthly' else 'price'} your "
            f"{'calendar' if P['binding'] == 'calendar' else 'delivery limit'} needs "
            f"({money(P['price_needed']['price'], P['currency'])})", "price", R, P["price_needed"]["price"])
    return out


def channel_loads(chans, c, R):
    if not chans:
        return {"split": False, "lines": ["Not split by channel: no counts by source were given. An even split "
                                          "would be an invented figure."]}
    counted = [ch for ch in chans if ch["booked"] is not None and ch["leads"] is not None]
    if not counted:
        names = ", ".join(ch["name"] for ch in chans)
        return {"split": False, "lines": [f"Not split by channel ({names}): no leads and bookings by source over "
                                          "the last 90 days. An even split would be an invented figure."]}
    total_b = sum(ch["booked"] for ch in counted) or 0
    lines, rows = [], []
    for ch in sorted(counted, key=lambda x: -(x["booked"] or 0)):
        if ch["leads"] < CHANNEL_MIN_LEADS or not ch["booked"] or not total_b:
            lines.append(f"{ch['name']}: {plural(ch['leads'], 'lead')} in 90 days, too few for its own rate. "
                         "Run it as a capped experiment, not a channel the plan rests on.")
            rows.append({"name": ch["name"], "experiment": True})
            continue
        sh = ch["booked"] / total_b
        need_b = c["booked"] * sh
        br = 100.0 * ch["booked"] / ch["leads"]
        show_own = None
        if ch.get("showed") is not None and ch["booked"] >= MIN_EVENTS:
            show_own = 100.0 * ch["showed"] / ch["booked"]
            held_need = c["held"] * (ch["showed"] / max(sum(x.get("showed") or 0 for x in counted), 1))
            need_b = held_need / (show_own / 100.0) if show_own else need_b
        need_l = up(need_b / (br / 100.0))
        lines.append(f"{ch['name']}: {fmt(need_b, 1)} bookings a month ({pct(sh * 100)} of today's bookings) at its "
                     f"own booking rate of {pct(br, 1)} ({fmt(ch['booked'])} of {fmt(ch['leads'])}, measured) needs "
                     f"{need_l} leads a month" + (f"; it shows at {pct(show_own, 1)} of its own" if show_own else "")
                     + ".")
        rows.append({"name": ch["name"], "share": sh, "booked": need_b, "rate": br, "leads": need_l,
                     "show": show_own, "experiment": False})
    planned = sum(r_["booked"] for r_ in rows if not r_["experiment"])
    rest = c["booked"] - planned
    if rest > 0.05 and any(r_["experiment"] for r_ in rows):
        lines.append(f"The other {fmt(rest, 1)} bookings a month would have to come from the thin channels above, "
                     "which have no measured rate yet: a gap to test, not a load to count on.")
    return {"split": True, "lines": lines, "rows": rows}


def next_days(start, n, call_days, days_off=()):
    """The next n days the founder takes calls, skipping their dated days off."""
    d, out = start, []
    while len(out) < n:
        d += timedelta(days=1)
        if d.weekday() in call_days and d not in days_off:
            out.append(d)
    return out


def first_week(P, I, R):
    days = next_days(I["date"], 5, I["call_days"], I["days_off"])
    d1, d2, d3, d_last = days[0], days[1], days[2], days[-1]
    own, bk, cur = I["owner"], I["books_calls"], P["currency"]
    pace = P["pace"]
    w = []
    b = P["binding"]
    if b in ("calendar", "delivery"):
        if P["price_needed"] and P["price_needed"]["rise"] <= 100:
            w.append((d1, own, f"Decide the {'fee' if P.get('billing') == 'monthly' else 'price'} for new clients. "
                      f"This target needs about {money(P['price_needed']['price'], cur)} "
                      f"{'a month' if P.get('billing') == 'monthly' else 'a sale'} to fit your "
                      f"{'calendar' if b == 'calendar' else 'delivery limit'}; put it on the next proposal you send"))
        else:
            hs = (f"; if you hire, a setter starts by {long_date_y(P['hire_start'])} to be at full pace in time"
                  if P.get("hire_start") else "")
            w.append((d1, own, "Decide which gives: the target, your hours or a hire. At today's rates the plan does "
                      f"not fit, and no sensible price closes the gap on its own{hs}"))
        w.append((d1, bk, f"Hold bookings to the weekly pace ({fmt(pace['booked'], 1)} a week), not to the target. "
                  + ("Your diary is the ceiling" if b == "calendar" else "Your delivery limit is the ceiling")))
    elif b == "show rate":
        w.append((d1, bk, "Offer every new enquiry a call slot within two working days, and confirm each call twice: "
                  "the day before and an hour before"))
        if R["show"]["tag"] != "measured":
            w.append((d2, bk, "Count this week's booked calls and how many turn up, so the show rate is measured next "
                      "month"))
    elif b == "lead volume":
        best = max((r_ for r_ in P["channels"].get("rows", []) if not r_.get("experiment")), key=lambda r_: r_["rate"],
                   default=None)
        pick_ = (f"Load {best['name']} first: it books {pct(best['rate'], 1)} of its leads (measured)" if best else
                 "Pick the one channel with the best booking rate and load it first")
        w.append((d2, own, f"{pick_}. The plan needs {fmt(P['multiple'], 1)} times today's leads, so change a rate or "
                  "the target before spending anything"))
    elif b == "close rate":
        w.append((d3, own, "Write up your next three sales calls straight after each one: where it stalled, and "
                  "what the prospect said just before it did"))
    elif P["chain"]["closes"]:
        w.append((d1, bk, f"Book toward the pace: about {fmt(pace['booked'], 1)} calls a week, "
                  f"{plural(P['chain']['booked'], 'booking')} a month"))
    if P["not_measured"]:
        w.append((d2 if b != "lead volume" else d3, bk, "Start one tally, by source: every enquiry, call booked, call "
                  "held, offer made and sale, so next month's rates are measured, not estimated"))
    else:
        w.append((d2 if b != "lead volume" else d3, bk, "Keep the tally by source (enquiries, calls booked, calls held, "
                  "offers, sales) so next month's re-plan runs on three months, not one"
                  if P["months"] == 1 else "Keep the tally by source going, so the next re-plan stays measured"))
    w.append((d_last, own, f"Check the week against the pace: {fmt(pace['booked'], 1)} booked, "
              f"{fmt(pace['held'], 1)} held, {plural(pace['closes'], P['sale_word'])}"))
    w.sort(key=lambda x: x[0])
    return [{"date": d.isoformat(), "day": long_date(d), "owner": o, "action": a} for d, o, a in w]


def weeks_ahead(P, I, n=6):
    """The next n weeks, each with its selling days (call days less dated days off) and the weekly pace scaled
    to them, so a short week shows a short target instead of the full one."""
    cd = I["call_days"] or [0, 1, 2, 3, 4]
    start_wd = 6 if (6 in cd and 0 in cd and 5 not in cd) else 0
    first = I["date"] + timedelta(days=1)
    ws = first - timedelta(days=(first.weekday() - start_wd) % 7)
    pc, full, out = P["pace"], len(cd), []
    for k in range(n):
        w0 = ws + timedelta(weeks=k)
        days = [w0 + timedelta(days=j) for j in range(7)]
        sell = [d for d in days if d >= first and d.weekday() in cd and d not in I["days_off"]]
        off = [d for d in days if d >= first and d.weekday() in cd and d in I["days_off"]]
        f = len(sell) / full if full else 0
        out.append({"week": w0.isoformat(), "from": sell[0].isoformat() if sell else None, "days": len(sell),
                    "off": [d.isoformat() for d in off], "booked": round1(pc["booked"] * f),
                    "held": round1(pc["held"] * f), "closes": round1(pc["closes"] * f)})
    return out


def month_so_far(P, I):
    """This month so far against the plan: counts to a date, against the plan's month scaled to the selling
    days gone (call days less days off). Never folded into the measured rates: the month is unfinished."""
    m = I.get("mtd")
    if not m or not P["chain"]["closes"]:
        return None
    to_ = m["to"]
    first = to_.replace(day=1)
    nxt = month_after(first, 1)
    cd = I["call_days"] or [0, 1, 2, 3, 4]
    days = [first + timedelta(days=k) for k in range((nxt - first).days)]
    sell = [d for d in days if d.weekday() in cd and d not in I["days_off"]]
    gone = [d for d in sell if d <= to_]
    f = len(gone) / len(sell) if sell else 0
    c = P["chain"]
    rows = []
    for k, lab, plan_k in (("leads", "leads", "leads"), ("booked", "booked", "booked"), ("showed", "held", "held"),
                           ("closed", "new clients" if P.get("billing") == "monthly" else "sales", "closes")):
        if m[k] is None or not c.get(plan_k):
            continue
        due = round1(c[plan_k] * f)
        rows.append({"what": lab, "have": m[k], "month": c[plan_k], "due": due,
                     "state": "ahead" if m[k] > due + 1e-9 else ("on pace" if abs(m[k] - due) < 0.5 else "behind")})
    return {"to": to_.isoformat(), "days_gone": len(gone), "days": len(sell), "rows": rows}


def mtd_lines(P):
    m = P.get("mtd")
    if not m or not m["rows"]:
        return []
    to_ = datetime.strptime(m["to"], "%Y-%m-%d").date()
    out = [f"To {long_date(to_)}: {m['days_gone']} of this month's {m['days']} selling days gone."]
    for r_ in m["rows"]:
        out.append(f"{r_['what'][0].upper() + r_['what'][1:]}: {fmt(r_['have'])} so far, against {fmt(r_['due'], 1)} due by now "
                   f"and {fmt(r_['month'])} for the month: {r_['state']}.")
    behind = [r_["what"] for r_ in m["rows"] if r_["state"] == "behind"]
    out.append(("Behind at " + ", ".join(behind) + ". The earliest stage behind is where to look first."
                if behind else "On pace or ahead at every stage counted.")
               + " These counts are not folded into the measured rates until the month closes.")
    return out


def week_lines(P):
    sw = "new clients" if P.get("billing") == "monthly" else "sales"
    out = []
    for w in P.get("weeks") or []:
        w0 = datetime.strptime(w["week"], "%Y-%m-%d").date()
        lab = f"Week of {long_date(w0)}"
        bits = []
        if w["from"] and w["from"] != w["week"] and w0 < datetime.strptime(P["date"], "%Y-%m-%d").date() + timedelta(days=1):
            bits.append(f"from {long_date(datetime.strptime(w['from'], '%Y-%m-%d').date())}")
        if w["off"]:
            bits.append("closed " + ", ".join(long_date(datetime.strptime(x, "%Y-%m-%d").date()) for x in w["off"]))
        lab += f" ({'; '.join(bits)})" if bits else ""
        if not w["days"]:
            out.append(f"{lab}: no selling days.")
            continue
        one = P["sale_word"] if P.get("billing") != "monthly" else "new client"
        out.append(f"{lab}: {plural(w['days'], 'selling day')}, {wn(P, w['booked'])} "
                   f"{'booking' if w['booked'] == 1 else 'bookings'}, {wn(P, w['held'])} "
                   f"{'held call' if w['held'] == 1 else 'held calls'}, {wn(P, w['closes'])} "
                   f"{one if w['closes'] == 1 else sw}.")
    return out


def wn(P, v):
    """A weekly figure as shown: one decimal, or whole calls when the founder asked (rounded up so the target is
    still met; rounded down on a capped plan so the pace never passes the ceiling)."""
    if not P.get("pace_whole") or v is None:
        return fmt(v, 1)
    return fmt(math.floor(round(v, 6)) if P["capped"] else math.ceil(round(v, 6)))


def pace_text(P, day=True):
    pc = P["pace"]
    if P.get("pace_whole"):
        sw = "new clients" if P.get("billing") == "monthly" else "sales"
        return (f"{wn(P, pc['booked'])} bookings, {wn(P, pc['held'])} held calls"
                + (f", {wn(P, pc['offers'])} offers" if pc.get("offers") else "")
                + f" and {wn(P, pc['closes'])} {sw} a week, in whole calls ("
                + ("rounded down to stay inside " + pc["basis"] if P["capped"] else "rounded up so the month is still met")
                + f"; to one decimal: {fmt(pc['booked'], 1)} bookings, {fmt(pc['held'], 1)} held calls)")
    sw = "new clients" if P.get("billing") == "monthly" else ("sales" if pc["closes"] != 1 else P["sale_word"])
    t = (f"{fmt(pc['booked'], 1)} bookings, {fmt(pc['held'], 1)} held calls"
         + (f", {fmt(pc['offers'], 1)} offers" if pc.get("offers") else "")
         + f" and {fmt(pc['closes'], 1)} {sw} a week" + (f", set at {pc['basis']}" if P["capped"] else ""))
    if day and pc.get("held_day") is not None:
        def w_(v, one, many):
            return f"{fmt(v, 1)} {one if v == 1 else many}"
        t += (f"; a selling day, {w_(pc['per_day'], 'booking', 'bookings')}, {w_(pc['held_day'], 'held call', 'held calls')}"
              f" and " + (w_(pc['closes_day'], 'new client', 'new clients') if P.get('billing') == 'monthly'
                          else w_(pc['closes_day'], P['sale_word'], 'sales')))
    return t


def month_name(iso):
    d_ = datetime.strptime(iso, "%Y-%m-%d").date()
    return d_.strftime("%B %Y")


def target_text(P):
    cur = P["currency"]
    if P.get("target_kind") == "by date":
        t = (f"{money(P['profit_total'], cur)} of profit between today and "
             f"{long_date_y(datetime.strptime(P['target_date'], '%Y-%m-%d').date())}")
        if P.get("made_so_far"):
            t += (f" (your {money(P['target_full'], cur)} less the {money(P['made_so_far'], cur)} already made)")
    elif P["form"] in ("contribution", "margin"):
        t = f"{money(P['profit'], cur)} of profit a month"
    else:
        t = f"{money(P['revenue_req'] if P.get('billing') != 'monthly' else P['inputs']['revenue_target'], cur)} of sales a month"
    if P.get("billing") == "monthly" and P.get("target_kind") != "by date":
        t += (f" by {long_date_y(datetime.strptime(P['target_date'], '%Y-%m-%d').date())}" if P.get("target_date")
              else f" within {P['ret']['T']} months (a planning default; give a date and the plan works to it)")
    if P.get("basis") == "take-home" and P["form"] in ("contribution", "margin"):
        t += " (your take-home figure, so every number here is too low until it is the before-tax figure)"
    return t


def made_tail(P, total):
    if not P.get("made_so_far"):
        return ""
    return (f"; with the {money(P['made_so_far'], cur_of(P))} already made, about "
            f"{money(P['made_so_far'] + total, cur_of(P))} by then, against your {money(P['target_full'], cur_of(P))}")


def cur_of(P):
    return P["currency"]


def reach_line(P):
    """For a date or a monthly fee: when the target is first reached, or what the ceiling reaches instead; for a
    monthly fee, the profit the next twelve months make at that pace."""
    base = _reach_line(P)
    tw = (P.get("reach") or {}).get("twelve")
    if P.get("billing") == "monthly" and tw is not None:
        pace = ("at the most you can carry" if (P.get("reach") or {}).get("cap_n") is not None else "at this pace")
        base = (base + " " if base else "") + f"Over the next 12 months {pace}, profit is about {money(tw, P['currency'])}."
    return base


def _reach_line(P):
    rc, cur = P.get("reach") or {}, P["currency"]
    sw = P["sale_word"]
    if P.get("billing") == "monthly":
        if P["ret"]["mode"] == "run rate":
            if rc.get("cap_n") is not None:
                if rc.get("cap_month"):
                    return (f"At the most you can carry ({plural(rc['cap_n'], 'new client')} a month), the target is "
                            f"first reached in {month_name(rc['cap_month'])}.")
                lr = rc.get("cap_long_run")
                return (f"At the most you can carry ({plural(rc['cap_n'], 'new client')} a month) the target is never "
                        "reached" + (f": with clients staying {fmt(P['ret']['L'], 1)} months, that pace holds about "
                                     f"{fmt(lr, 1)} paying clients against the {P['ret_res']['A']} needed." if lr else "."))
            if rc.get("month"):
                return f"At this pace the target is first reached in {month_name(rc['month'])}."
            return ""
        if rc.get("cap_n") is not None and rc.get("total_cap") is not None:
            return (f"At the most you can carry ({plural(rc['cap_n'], 'new client')} a month), profit from today to "
                    f"{long_date_y(datetime.strptime(P['target_date'], '%Y-%m-%d').date())} is about "
                    f"{money(rc['total_cap'], cur)}" + made_tail(P, rc['total_cap']) + ".")
        return ""
    if rc.get("cap_n") is not None and rc.get("cap_profit_month") is not None:
        if P.get("target_kind") == "by date" and rc.get("total_cap") is not None:
            return (f"At the most you can carry ({plural(rc['cap_n'], sw)} a month), profit from today to "
                    f"{long_date_y(datetime.strptime(P['target_date'], '%Y-%m-%d').date())} is about "
                    f"{money(rc['total_cap'], cur)}" + made_tail(P, rc['total_cap']) + ".")
        return (f"At the most you can carry ({plural(rc['cap_n'], sw)} a month), profit is about "
                f"{money(rc['cap_profit_month'], cur)} a month.")
    return ""


def headline(P, R):
    cur = P["currency"]
    c = P["chain"]
    sw = P["sale_word"]
    monthly = P.get("billing") == "monthly"
    what = "fee" if monthly else "price"
    tgt = target_text(P)
    extra = reach_line(P)
    if c["closes"] == 0:
        return [f"Your {fmt(P['ret']['A0'])} paying clients already carry {tgt}: the plan needs no new clients.",
                "Keep the tally of enquiries and calls going, so the next re-plan is measured."]
    have = ""
    if monthly and P["ret"]["mode"] == "run rate":
        have = (f"You need {plural(P['ret_res']['A'], 'paying client')} at once and have {fmt(P['ret']['A0'])}. ")
    if P["binding"] in ("calendar", "delivery"):
        lim = "calendar" if P["binding"] == "calendar" else "delivery"
        if P.get("active_bind"):
            h1 = have + f"At today's {what} of {money(P['price'], cur)}, your delivery cannot carry {tgt}: {P['active_bind']}"
        elif lim == "calendar":
            h1 = (have + f"At today's {what} of {money(P['price'], cur)}, your {lim} cannot carry {tgt}: it needs "
                  f"{plural(c['closes'], sw)}, {plural(c['held'], 'held call')} and {plural(c['booked'], 'booking')} "
                  f"a month, {fmt(P['hours_week'], 1)} hours a week of calls against your {fmt(P['sell'], 1)}")
        else:
            h1 = (have + f"At today's {what} of {money(P['price'], cur)}, {tgt} needs {plural(c['closes'], 'new client')} "
                  f"a month, and you can deliver for {fmt(P['delivery_max'])}")
        pn = P["price_needed"]
        if pn and pn["rise"] > 100:
            h2 = (f"Only a {what} of {money(pn['price'], cur)}, a {pct(pn['rise'])} rise, would fit on its own, so "
                  f"the {what} alone will not close this: the target, your hours or a hire has to move.")
        elif pn:
            h2 = (f"At {money(pn['price'], cur)} the same target needs {plural(pn['closes'], sw)}, "
                  f"{plural(pn['held'], 'held call')} and {fmt(pn['hours'], 1)} hours a week, which {pn['fit']}. "
                  f"The {what} is the first thing to move.")
        else:
            h2 = f"No {what} in the scenarios fits on its own; the target, your hours or a hire has to move."
        return [h1 + ".", h2] + ([extra] if extra else [])
    h1 = (have + f"To make {tgt} you need {plural(c['closes'], sw)}, {plural(c['held'], 'held call')} and "
          f"{plural(c['booked'], 'booking')} a month" + (f", from {c['leads']} leads" if c["leads"] else "")
          + f": {fmt(P['pace']['booked'], 1)} bookings a week.")
    if P["binding"]:
        h2 = f"What breaks first is your {P['binding']}: {P['because']}."
    else:
        h2 = (f"Nothing breaks at these rates: the calls take {fmt(P['hours_week'], 1)} of your {fmt(P['sell'], 1)} "
              f"selling hours a week, which {P['calendar']}.")
    return [h1, h2] + ([extra] if extra else [])


# ================================================================ the plan as text
TAG_SHOWN = {"measured": "measured", "measured, directional": "measured on under 10, directional",
             "your estimate": "your estimate", "assumed": "planning default", "unknown": "not known"}


def rate_text(r):
    if r["value"] is None:
        return f"not known ({r['basis']})"
    t = TAG_SHOWN[r["tag"]]
    extra = f", {r['basis']}" if r["tag"] in ("measured", "measured, directional") else ""
    return f"{pct(r['value'], 1)} ({t}{extra})"


def whole(P):
    ex, n = P["closes_exact"], P["closes"]
    if abs(ex - n) < 1e-6:
        return plural(n, "sale")
    return f"{fmt(ex, 1)} sales, rounded up to {plural(n, 'whole sale')}"


def ret_lines(P):
    """Section 1 for a monthly fee: paying clients needed, clients leaving, new clients a month, month by month."""
    cur, R_, rr = P["currency"], P["ret"], P["ret_res"]
    out = []
    u = rr["unit"]
    fee, d_ = P["price"], P["delivery"]
    if P["form"] == "contribution":
        out.append(f"Each client pays {money(fee, cur)} a month and leaves {money(u, cur)} a month after delivery "
                   f"({money(fee, cur)} less {money(d_, cur)}).")
    elif P["form"] == "margin":
        out.append(f"Each client pays {money(fee, cur)} a month; at your {pct(P['inputs']['margin'])} margin that "
                   f"leaves {money(u, cur)} a month.")
    leave = (f"Clients stay {fmt(R_['L'], 1)} months on average, so about 1 in {fmt(R_['L'], 1)} leave each month."
             if R_["L"] else "No figure for how long clients stay, so none are counted as leaving.")
    if R_["mode"] == "run rate":
        if P["form"] == "contribution":
            parts = [f"profit {money(P['profit'], cur)}"] + ([f"your pay {money(P['pay'], cur)}"] if P["pay"] else []) \
                + [f"running costs {money(P['running'], cur)}"]
            out.append(f"The business must leave {money(P['need'], cur)} a month ({', '.join(parts)}), so you need "
                       f"{plural(rr['A'], 'paying client')} at once ({fmt(P['need_ret'] / u, 1)}, rounded up).")
        else:
            out.append(f"That needs {plural(rr['A'], 'paying client')} at once ({fmt(P['need_ret'] / u, 1)}, rounded up).")
        out.append(f"You have {fmt(R_['A0'])} now. {leave}")
        if R_["L"]:
            out.append(f"Holding {plural(rr['A'], 'paying client')} takes {plural(rr['hold'], 'new client')} a month "
                       f"({fmt(rr['A'] / R_['L'], 1)}, rounded up).")
        when = ("by " + long_date_y(datetime.strptime(P["target_date"], "%Y-%m-%d").date()) if P.get("target_date")
                else f"within {R_['T']} months")
        out.append(f"Reaching {plural(rr['A'], 'paying client')} {when} takes {plural(rr['build'], 'new client')} a "
                   f"month; the plan sets {plural(P['closes'], 'new client')} a month"
                   + (f", then {plural(rr['hold'], 'new client')} a month to hold it." if rr["hold"] and rr["hold"] < P["closes"] else "."))
    else:
        out.append(f"{money(R_['total'], cur)} of profit over {plural(R_['T'], 'whole month')}, plus "
                   f"{money(R_['fixed'], cur)} a month of running costs" + (" and your pay" if P["pay"] else "")
                   + f", needs {fmt(rr['client_months'], 1)} paying client-months at {money(u, cur)} each.")
        out.append(f"You have {fmt(R_['A0'])} paying clients now. {leave} They carry about {fmt(rr['now_carry'], 1)} "
                   f"of those client-months, so the rest needs {plural(P['closes'], 'new client')} a month from now.")
    rows = (P.get("reach") or {}).get("rows") or []
    if rows and P["closes"]:
        out.append("Month by month at this pace: " + "; ".join(
            f"{month_name(r_['month'])}, about {fmt(r_['active'], 1)} paying clients and {money(r_['profit'], cur)} "
            "of profit" for r_ in rows[:6]) + ".")
    if P.get("now"):
        out.append(f"Today: {fmt(R_['A0'])} paying clients leave about {money(P['now']['left'], cur)} a month after "
                   "delivery and running costs" + (f", against the {money(P['profit'], cur)} you need." if
                                                   R_["mode"] == "run rate" and P["profit"] else "."))
    return out


def render(P):
    """The plan as sections of lines. Used for the chat, the Plan sheet and the note gate."""
    cur, c, R = P["currency"], P["chain"], P["rates"]
    S = []
    top = list(P["headline"])
    if P["chain"]["closes"]:
        fw = P["first_week"][0] if P["first_week"] else None
        top.append(f"Weekly pace: {pace_text(P)}.")
        if fw:
            top.append(f"First action: {fw['day']}: {fw['action']}.")
    S.append(("Headline", top))
    if P.get("since"):
        S.append(("Since your last plan", P["since"]))
    if mtd_lines(P):
        S.append(("This month so far", mtd_lines(P)))
    # step 1
    l1 = []
    if P.get("target_date"):
        td_ = datetime.strptime(P["target_date"], "%Y-%m-%d").date()
        T_ = P["whole_months"]
        l1.append(f"From today to {long_date_y(td_)} is {fmt(P['months_left'], 1)} months: {plural(T_, 'whole month')} of "
                  f"selling ({', '.join(month_after(datetime.strptime(P['date'], '%Y-%m-%d').date(), k).strftime('%B') for k in range(1, T_ + 1))}).")
    if P.get("billing") == "monthly":
        l1 += ret_lines(P)
    elif P["form"] == "contribution":
        parts = [f"profit {money(P['profit'], cur)}"]
        if P["pay"]:
            parts.append(f"your pay {money(P['pay'], cur)}")
        parts.append(f"running costs {money(P['running'], cur)}")
        l1.append(f"The business must leave {money(P['need'], cur)} a month ({', '.join(parts)}).")
        l1.append(f"Each sale leaves {money(P['cps'], cur)} after delivery ({money(P['price'], cur)} less "
                  f"{money(P['delivery'], cur)}), so you need {whole(P)} a month, "
                  f"{money(P['revenue_plan'], cur)} of sales.")
        if P.get("cross"):
            l1.append(f"Check against your margin: {fmt(P['cross']['margin_sales'], 1)} sales a month on the margin "
                      f"you gave; the plan runs on your costs.")
    elif P["form"] == "margin":
        l1.append(f"Profit {money(P['profit'], cur)} over your {pct(P['inputs']['margin'])} margin is "
                  f"{money(P['revenue_req'], cur)} of sales a month: at {money(P['price'], cur)} a sale that is "
                  f"{whole(P)}.")
    else:
        l1.append(f"Planned from revenue, as you gave it: {money(P['revenue_req'], cur)} a month at "
                  f"{money(P['price'], cur)} a sale is {whole(P)}.")
        if P.get("profit_at_revenue") is not None:
            l1.append(f"At your costs that revenue leaves {money(P['profit_at_revenue'], cur)} a month after delivery "
                      "and running costs.")
    if P.get("now") and P.get("billing") != "monthly":
        nw = P["now"]
        l1.append(f"Today: you sell about {money(nw['sales'], cur)} a month. At the costs you gave, that leaves about "
                  f"{money(nw['left'], cur)} a month" + (f", against the {money(P['profit'], cur)} you need."
                                                         if P["profit"] else "."))
    if P.get("billing") == "monthly":
        if P["ret"]["mode"] == "run rate":
            l1.append(f"Cash, kept apart from sales: clients pay monthly, so cash follows paying clients; at "
                      f"{plural(P['ret_res']['A'], 'paying client')} {money(P['cash_in_month'], cur)} a month comes in.")
    else:
        l1.append(f"Cash, kept apart from sales: with {pct(P['share'])} of the price paid in the month they sign, "
                  f"{money(P['cash_in_month'], cur)} lands in the month from this month's sales"
                  + (f"; in the first month of the plan, cash runs {money(P['cash_gap_first_month'], cur)} behind sales "
                     "until earlier instalments land." if P["cash_gap_first_month"] > 0.5 else "."))
    if P.get("billing") != "monthly" and P.get("reach", {}).get("cap_n") is not None:
        rl = reach_line(P)
        if rl:
            l1.append(rl)
    if P.get("basis") == "take-home":
        l1.append("Your profit figure is take-home, so these figures are too low until it is replaced with the "
                  "before-tax figure.")
    S.append(("1. From profit to sales", l1))
    # step 2
    l2 = [f"{'New clients' if P.get('billing') == 'monthly' else 'Sales'} a month: {c['closes']}"]
    if c["offers"] is not None:
        l2.append(f"Offers made a month: {c['offers']}, at {rate_text(R['offer_conv'])} of offers buying")
        l2.append(f"Calls held a month: {c['held']}, at an offer on {rate_text(R['offer'])} of held calls")
    else:
        l2.append(f"Calls held a month: {c['held']}, at a close rate on held calls of {rate_text(R['close'])}")
    l2.append(f"Calls booked a month: {c['booked']}, at a show rate of {rate_text(R['show'])}")
    if c["leads"]:
        l2.append(f"Leads a month: {c['leads']}, at a booking rate of {rate_text(R['booking'])}")
    else:
        l2.append("Leads a month: not known until you count how many enquiries turn into a booked call")
    if P["leads_now"] and c["leads"]:
        l2.append(f"Leads now: {fmt(P['leads_now'], 1)} a month, so the plan needs {fmt(P['multiple'], 1)} times today's.")
    if P.get("pessimistic"):
        pp = P["pessimistic"]
        l2.append(f"If the rates measured on under 10 calls fall back to the planning defaults: {pp['held']} held "
                  f"and {pp['booked']} booked a month.")
    S.append(("2. The chain, every rate tagged", l2))
    # step 3
    l3 = [f"{plural(c['held'], 'held call')} a month at {hours_text(round(P['callh'], 2), 2)} each is "
          f"{hours_text(P['hours_week'])} a week against your {fmt(P['sell'], 1)}: {P['calendar']} "
          f"({pct(P['hours_share'] * 100)} of your selling hours)."]
    l3.append(f"Your calendar's ceiling: {fmt(P['max_held'], 1)} held calls a month, which at your rates is "
              f"{fmt(P['cal_closes'], 1)} {'new clients' if P.get('billing') == 'monthly' else 'sales'}.")
    if P["delivery_max"]:
        l3.append(f"Delivery: {plural(c['closes'], 'new client')} a month needed against the "
                  f"{fmt(P['delivery_max'])} you can take on: "
                  f"{'fits' if c['closes'] <= P['delivery_max'] else 'breaks'}.")
    if P.get("billing") == "monthly" and P["ret"].get("M"):
        if P["ret"]["mode"] == "run rate":
            l3.append(f"Clients at once: {plural(P['ret_res']['A'], 'paying client')} needed against the "
                      f"{fmt(P['ret']['M'])} your team can serve: {'breaks' if P.get('active_bind') else 'fits'}.")
        elif P.get("active_bind"):
            l3.append(f"Clients at once: {P['active_bind']}: breaks.")
    S.append(("3. Your calendar, checked before the plan is called possible", l3))
    # step 4
    l4 = []
    if P["binding"]:
        l4.append(f"{P['binding'][0].upper() + P['binding'][1:]}: {P['because']}.")
    else:
        l4.append("None breaks at this target on these rates.")
        if P.get("volume_note"):
            l4.append(P["volume_note"])
    if P["price_needed"]:
        pn = P["price_needed"]
        l4.append(f"The {'fee' if P.get('billing') == 'monthly' else 'price'} that fits: {money(pn['price'], cur)}, a {pct(pn['rise'])} rise. It needs "
                  f"{plural(pn['closes'], P['sale_word'])}, {plural(pn['held'], 'held call')}, {plural(pn['booked'], 'booking')} "
                  f"and {fmt(pn['hours'], 1)} hours a week.")
    S.append(("4. What breaks first", l4))
    S.append(("5. Fix order, largest effect first", fix_order(P)))
    l6 = []
    if P["three_bets"]:
        l6.append("Only the three levers together fit your hours: that is three bets, not a plan.")
    for m in P["met"]:
        l6.append(f"{m['name']}: no row, {m['note']}.")
    S.append(("6. Scenarios", l6))
    S.append(("7. By channel", P["channels"]["lines"]))
    S.append(("8. Hiring", [P["hire"]]))
    pc = P["pace"]
    l9 = [f"Bookings {fmt(pc['booked'], 1)}, held calls {fmt(pc['held'], 1)}, "
          + (f"offers {fmt(pc['offers'], 1)}, " if pc.get("offers") else "")
          + f"{'new clients' if P.get('billing') == 'monthly' else 'sales'} {fmt(pc['closes'], 1)} a week; "
          f"{plural(pc['per_day'], 'booking')} a selling day."]
    if P["capped"]:
        l9.append(f"Set at {pc['basis']} ({fmt(pc['closes_month'], 1)} {'new clients' if P.get('billing') == 'monthly' else 'sales'} "
                  f"a month), not at the {c['closes']} the target needs: a weekly target above what you can carry is "
                  "never set.")
    elif pc["held"] < 2:
        l9.append(f"Under two held calls a week: about {fmt(round1(pc['held'] * 2), 1)} a fortnight, "
                  f"{plural(c['held'], 'held call')} a month.")
    if P["chain"]["closes"]:
        l9.append("Week by week, scaled to the days you take calls (a table with totals is on the Week by week sheet):")
        l9 += week_lines(P)
    S.append(("9. Weekly pace", l9))
    S.append(("10. Your first week", [f"{x['day']} | {x['owner']}: {x['action']}" for x in P["first_week"]]))
    rp = datetime.strptime(P["replan"], "%Y-%m-%d").date()
    S.append(("Re-plan", [f"Re-plan by {full_date(rp)}: " + (
        "a rate is estimated or a default (" + ", ".join({"show": "show rate", "close": "close rate",
                                                          "booking": "booking rate"}[k] for k in P["not_measured"])
        + "), so replace it with what actually happened." if P["not_measured"] else
        f"every rate is measured, on {plural(P['months'], 'month')} of counts; re-plan monthly until three months "
        "are counted." if P.get("short_window") else "every rate is measured; quarterly.")]))
    a = [P["tax_line"]]
    for lab, val, tag in P["assume"]:
        a.append(f"{lab}: {val}.")
    for n in P["notes"]:
        a.append(n + ".")
    a.append(ADVICE_LINE)
    S.append(("Assumptions", a))
    if P["needs"]:
        S.append(("Still needed", [f"[NEED: {n}]" for n in P["needs"]]))
    return [(spell(t), [spell(x) for x in ls]) for t, ls in S]


def plan_title(P):
    if P["business"]:
        return f"Sales target plan: {P['business']}"
    own = P["inputs"].get("owner")
    return f"Sales target plan for {own}" if own and own != "You" else "Sales target plan"


def fix_order(P):
    """The levers ranked by what each buys in this plan (fewest held calls needed, then fewest bookings),
    so the fix order always agrees with the Scenarios table. Ties keep the usual order: show, price, close."""
    kinds = {"Show": ("show rate", "a process fix and the fastest (book soon after the enquiry, confirm twice)"),
             "Fee": ("fee", "a framing and structure fix"), "Price": ("price", "a framing and structure fix"),
             "Close": ("close rate", "the slowest, and it compounds"),
             "Offer": ("offer on every held call", "a call structure fix")}
    sw = "new clients" if P.get("billing") == "monthly" else "sales"
    levers = [s for s in P["scenarios"] if s["kind"] == "lever"]
    order = {k: i for i, k in enumerate(["Show", "Fee", "Price", "Close", "Offer"])}
    levers.sort(key=lambda s: (s["held"], s["booked"], order.get(s["name"].split()[0], 9)))
    out = []
    for i, s in enumerate(levers, 1):
        why = kinds.get(s["name"].split()[0], ("", ""))[1]
        out.append(f"{i}. {s['name']}: {s['closes']} {sw}, {s['held']} held calls and {s['booked']} bookings a month"
                   + (f"; {why}" if why else "") + ".")
    for m in P.get("met", []):
        out.append(f"{m['name']}: {m['note']}, so it buys nothing here.")
    if not levers:
        out.append("No lever is left to pull at these rates; the target, the price or your hours has to move.")
    out.append("Hiring comes after these, never first: a hire under a leaky process pays for the leak.")
    return out


def chat_lines(P):
    """Lines the chat copies word for word, so the chat never disagrees with the workbook."""
    if P["binding"]:
        brk = f"What breaks first: your {P['binding']}: {P['because']}."
        close = (f"Your plan breaks first at your {P['binding']}. Whether that is a price, show rate or sales system "
                 "problem is what the Merigrove Business Audit scores: [BUSINESS_AUDIT_URL].")
    else:
        tight = []
        if P["delivery_max"] and P["chain"]["closes"] >= P["delivery_max"] - 1e-9:
            tight.append(f"delivery has no slack: {plural(P['chain']['closes'], 'new client' if P.get('billing') == 'monthly' else P['sale_word'])} "
                         f"a month needed against the {fmt(P['delivery_max'])} you can take on, so one slow month cannot be made up")
        if P["calendar"] == "fits, tightly":
            tight.append(f"your calendar is tight: {fmt(P['hours_week'], 1)} of your {fmt(P['sell'], 1)} selling hours a week")
        brk = ("What breaks first: nothing at these rates" + (", but " + "; and ".join(tight) if tight else "") + "."
               + (f" {P['volume_note']}" if P.get("volume_note") else ""))
        close = ("Your plan fits at today's rates. Whether those rates hold as volume grows is what the Merigrove "
                 "Business Audit scores: [BUSINESS_AUDIT_URL].")
    fo = [x for x in fix_order(P) if x[:2] == "1."]
    fw = P["first_week"][0] if P["first_week"] else None
    out = [f"CHAT-BREAKS: {brk}"]
    if P.get("target_date"):
        td_ = datetime.strptime(P["target_date"], "%Y-%m-%d").date()
        out.append(f"CHAT-DATE: From today to {long_date_y(td_)} is {fmt(P['months_left'], 1)} months, "
                   f"{plural(P['whole_months'], 'whole month')} of selling.")
    rl = reach_line(P)
    if rl:
        out.append(f"CHAT-REACH: {rl}")
    if P["chain"]["closes"]:
        out.append(f"CHAT-PACE: Weekly pace: {pace_text(P)}.")
    for ln in mtd_lines(P):
        out.append(f"CHAT-MONTH-SO-FAR: {ln}")
    if P.get("off_days_note"):
        out.append(f"CHAT-DAYS-OFF: {P['off_days_note']}")
    if fo:
        lev = sorted([s_ for s_ in P["scenarios"] if s_["kind"] == "lever"],
                     key=lambda s_: (s_["held"], s_["booked"]))
        c_ = P["chain"]
        if lev and lev[0]["held"] >= c_["held"] and lev[0]["booked"] >= c_["booked"]:
            out.append(f"CHAT-BIGGEST-LEVER: No single lever cuts the {plural(c_['held'], 'held call')} a month at "
                       f"whole-{'client' if P.get('billing') == 'monthly' else 'sale'} level here; the closest is "
                       f"{fo[0][3:][0].lower() + fo[0][3:][1:]}")
        else:
            out.append(f"CHAT-BIGGEST-LEVER: {fo[0][3:]}")
    if fw:
        out.append(f"CHAT-FIRST-ACTION: {fw['day']}: {fw['action']}.")
    out.append(f"CHAT-REPLAN: Re-plan by {full_date(datetime.strptime(P['replan'], '%Y-%m-%d').date())}.")
    out.append(f"CHAT-CLOSING: {close}")
    return out


def render_text(P, note=None):
    out = [f"# {plan_title(P)}, {long_date_y(datetime.strptime(P['date'], '%Y-%m-%d').date())}", ""]
    for title, lines in render(P):
        out.append(f"## {title}")
        out.extend(lines)
        if title == "6. Scenarios":
            mo_ = P.get("billing") == "monthly"
            out.append(f"| Scenario | {'Fee' if mo_ else 'Price'} | {'New clients' if mo_ else 'Sales'} | Held | Booked | "
                       "Leads | Bookings a day | Hours a week | Fits |")
            out.append("|---|---|---|---|---|---|---|---|---|")
            for s in P["scenarios"]:
                if s["kind"] == "met":
                    continue
                out.append(f"| {s['name']} | {money(s['price'], P['currency'])} | {s['closes']} | {s['held']} | "
                           f"{s['booked']} | {s['leads'] if s['leads'] else 'not known'} | {fmt(s['per_day'], 1)} | "
                           f"{fmt(s['hours'], 1)} | {s['verdict']} |")
        if title == "Headline" and note:
            out.append("")
            out.append(note.strip())
        out.append("")
    return "\n".join(out)


# ================================================================ note gate
PROMISES = r"\b(guarantee[sd]?|you will (hit|close|make|reach)|you'll (hit|close|make|reach)|double your|triple your|will definitely)\b"


def _num_re():
    """Figures as the founder writes them: 12,345.6 / 12.345,6 / 12 345,6 / 12,34,567; plus a trailing k."""
    sp = "[ \u00a0\u202f]"
    if STYLE.get("decimal") == "comma":
        body = r"\d{1,3}(?:(?:\.|" + sp + r"|')\d{3})+(?:,\d+)?|\d+(?:,\d+)?"
    else:
        body = r"\d{1,3}(?:,\d{2})+,\d{3}|\d{1,3}(?:(?:,|" + sp + r"|')\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?"
    return re.compile(r"(?<![\d.,])(" + body + r")(k\b)?", re.I)


def _to_float(tok):
    t = re.sub(r"[ \u00a0\u202f']", "", tok)
    if STYLE.get("decimal") == "comma":
        return float(t.replace(".", "").replace(",", "."))
    return float(t.replace(",", ""))


CONTEXT = [  # what a figure counts, read from the words straight after it
    ("hours_week", r"(?:hours?|hrs?) (?:a|per) week|selling hours|hours? of calls"),
    ("hours_call", r"(?:hours?|hrs?) (?:each|a call|per call|for each call|with prep)"),
    ("held", r"held(?: sales)? calls?|calls? held|sales calls? held"),
    ("booked", r"bookings?|calls? booked|booked calls?"),
    ("leads", r"leads?|enquir\w*|inquir\w*"),
    ("clients", r"paying clients?|clients? (?:at once|paying)"),
    ("sales", r"(?:whole )?sales\b|new clients?|contracts?|deals?|clients?\b"),
]
GENERIC = {"hours": r"(?:hours?|hrs?)\b", "calls": r"calls?\b"}


def classify(text, end):
    """The thing a figure counts, from the words after it; 'N of your M hours' gives N the same thing as M."""
    after = text[end:end + 60].lower().lstrip(" \u00a0")
    after = re.sub(r"^(?:of|out of) (?:your |the |our )?[\d.,\u00a0]+\s*", "", after)
    after = re.sub(r"^(?:more |extra |new |whole |a |an )", lambda m: m.group(0) if m.group(0).strip() in ("new", "whole") else "", after)
    for name, pat in CONTEXT:
        if re.match(r"(?:" + pat + r")", after):
            return name
    for name, pat in GENERIC.items():
        if re.match(pat, after):
            return name
    return None


def figures(text):
    out = []
    rx = _num_re()
    for m in rx.finditer(text):
        try:
            v = _to_float(m.group(1)) * (1000 if m.group(2) else 1)
        except ValueError:
            continue
        out.append((v, classify(text, m.end()), m.group(0)))
    return out


def plan_values(P):
    """The plan's own figures for each thing a note can count, as printed (to one decimal where shown so)."""
    c, pk, pn = P["chain"], P["pace"], P.get("price_needed") or {}
    sc = [x for x in P["scenarios"] if x["kind"] != "met"]
    one = lambda v: None if v is None else float(v)  # noqa: E731
    r1 = lambda v: None if v is None else round(v, 1)  # noqa: E731
    out = {
        "hours_week": [r1(P["hours_week"]), one(P["sell"]), r1(pn.get("hours"))] + [r1(x["hours"]) for x in sc],
        "hours_call": [one(P["callh"]), r1(P["callh"])],
        "held": [one(c["held"]), one(pk["held"]), r1(P["max_held"]), one(pn.get("held"))] + [one(x["held"]) for x in sc]
        + [one((P.get("pessimistic") or {}).get("held"))],
        "booked": [one(c["booked"]), one(pk["booked"]), r1(pk["per_day"]), one(pn.get("booked")),
                   one(P.get("show_lever_booked"))] + [one(x["booked"]) for x in sc]
        + [one((P.get("pessimistic") or {}).get("booked"))],
        "leads": [one(c["leads"]), r1(P.get("leads_now"))] + [one(x["leads"]) for x in sc],
        "sales": [one(c["closes"]), r1(P["closes_exact"]), one(pk["closes"]), r1(P["cal_closes"]), one(pn.get("closes")),
                  one(P.get("delivery_max")), one(pk.get("closes_month"))] + [one(x["closes"]) for x in sc],
        "clients": [],
    }
    if P.get("ret"):
        rr = P["ret_res"]
        out["clients"] = [one(rr.get("A")), one(P["ret"]["A0"]), one(rr.get("build")), one(rr.get("hold"))]
        out["sales"] += out["clients"]
    tot = P.get("actuals_total") or {}
    last = (P["inputs"].get("actuals") or [{}])[-1] if P["inputs"].get("actuals") else {}
    for k, kk in (("held", "showed"), ("booked", "booked"), ("leads", "leads"), ("sales", "closed")):
        out[k] += [one(tot.get(kk)), one(last.get(kk))]
    lp = (P.get("_prev") or {}).get("_last_plan") or {}
    for k, kk in (("held", "held"), ("booked", "booked"), ("sales", "closes"), ("leads", "leads")):
        try:
            out[k].append(float(lp.get(kk)))
        except (TypeError, ValueError):
            pass
    return out


def check_note(note, P):
    """Every figure in Claude's note must be one this script printed, for the same thing: a figure followed by
    'held calls' must be a held-call figure from this plan, not just any number in it. No promises; 120 words."""
    probs = []
    plan_figs = figures(render_text(P))
    allowed_all = {round(v, 6) for v, _k, _t in plan_figs}
    by_kind = {}
    for v, k, _t in plan_figs:
        if k:
            by_kind.setdefault(k, set()).add(round(v, 6))
    for k, vals in plan_values(P).items():
        by_kind.setdefault(k, set()).update(round(v, 6) for v in vals if v is not None)
        allowed_all.update(round(v, 6) for v in vals if v is not None)
    union = {"hours": ("hours_week", "hours_call"), "calls": ("held", "booked"), "sales": ("sales", "clients")}
    for v, k, tok in figures(note):
        fv = round(v, 6)
        if k:
            pool = set()
            for kk in union.get(k, (k,)):
                pool |= by_kind.get(kk, set())
            if k == "hours":
                pool |= by_kind.get("hours", set())
            if pool and fv not in pool:
                what = {"hours_week": "hours a week", "hours_call": "hours a call", "held": "held calls",
                        "booked": "bookings", "calls": "calls", "clients": "paying clients"}.get(k, k)
                probs.append(f"the note says {tok.strip()} {what}, which is not this plan's figure for {what}")
                continue
        if fv not in allowed_all:
            probs.append(f"the note says {tok.strip()}, which the plan did not compute")
    def opening(t):
        return " ".join(re.findall(r"[a-z]+", t.lower())[:5])
    heads = {opening(h) for h in P["headline"]} | {"nothing breaks at these rates", "what breaks first is your"}
    for sent in re.split(r"(?<=[.!?])\s+", note.strip()):
        if sent and (opening(sent) in heads or opening(sent).startswith("nothing breaks")):
            probs.append("the note repeats the headline ('" + sent[:40] + "...'); say what it means for this "
                         "founder instead, the headline already sits above it")
            break
    if re.search(PROMISES, note, re.I):
        probs.append("the note promises a result")
    if "\u2014" in note or "\u2013" in note:
        probs.append("the note has an em or en dash")
    words = len(re.findall(r"\b\w[\w'-]*\b", note))
    if words > 120:
        probs.append(f"the note is {words} words; keep it to 120")
    return probs


# ================================================================ a standard-library xlsx writer
def col(n):
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def ref(c_, r_, abs_=False):
    return f"${col(c_)}${r_}" if abs_ else f"{col(c_)}{r_}"


STYLES = ["default", "bold", "title", "head", "input", "input_pct", "input_money", "money", "pct", "num1", "int",
          "wrap", "label", "note", "input_num1", "headline", "centre"]


def styles_xml(cur):
    sym = SYMBOLS.get(cur, "")
    mfmt = f'&quot;{sym}&quot;#,##0' if sym else '#,##0'
    if sym and STYLE.get("sym_after"):
        mfmt = f'#,##0&quot;\u00a0{sym}&quot;'
    if cur == "INR":
        q = f'&quot;{sym}&quot;'
        mfmt = f'[&gt;=10000000]{q}##\\,##\\,##\\,##0;[&gt;=100000]{q}##\\,##\\,##0;{q}##,##0'
    fonts = ('<fonts count="5"><font><sz val="10"/><name val="Arial"/></font>'
             '<font><b/><sz val="10"/><name val="Arial"/></font>'
             '<font><b/><sz val="14"/><name val="Arial"/></font>'
             '<font><i/><sz val="9"/><color rgb="FF555555"/><name val="Arial"/></font>'
             '<font><b/><sz val="11"/><name val="Arial"/></font></fonts>')
    fills = ('<fills count="4"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill>'
             '<fill><patternFill patternType="solid"><fgColor rgb="FFFFF2B3"/><bgColor indexed="64"/></patternFill></fill>'
             '<fill><patternFill patternType="solid"><fgColor rgb="FFEFEFEF"/><bgColor indexed="64"/></patternFill></fill></fills>')
    numfmts = (f'<numFmts count="3"><numFmt numFmtId="164" formatCode="{mfmt}"/>'
               '<numFmt numFmtId="165" formatCode="0.0"/><numFmt numFmtId="166" formatCode="0.0%"/></numFmts>')
    al_wrap = '<alignment wrapText="1" vertical="top"/>'
    al_top = '<alignment vertical="top"/>'
    xfs = [  # font, fill, numfmt, alignment
        (0, 0, 0, al_top), (1, 0, 0, al_top), (2, 0, 0, al_top), (1, 3, 0, al_wrap), (0, 2, 0, al_top),
        (0, 2, 166, al_top), (0, 2, 164, al_top), (0, 0, 164, al_top), (0, 0, 166, al_top), (0, 0, 165, al_top),
        (0, 0, 1, al_top), (0, 0, 0, al_wrap), (1, 0, 0, al_wrap), (3, 0, 0, al_wrap), (0, 2, 165, al_top),
        (4, 0, 0, al_wrap), (0, 0, 0, '<alignment horizontal="center" vertical="top"/>')]
    xf = "".join(f'<xf numFmtId="{n}" fontId="{f}" fillId="{fi}" borderId="0" applyFont="1" applyFill="1" '
                 f'applyNumberFormat="1" applyAlignment="1">{a.replace("<alignment", "<alignment")}</xf>'
                 for f, fi, n, a in xfs)
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f'{numfmts}{fonts}{fills}<borders count="1"><border/></borders>'
            '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
            f'<cellXfs count="{len(xfs)}">{xf}</cellXfs>'
            '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>')


class Sheet:
    def __init__(self, name, widths):
        self.name, self.widths, self.cells, self.merges = name, widths, {}, []
        self.print_fit = False
        self.paper = None

    def set(self, c_, r_, value=None, style="default", formula=None):
        self.cells[(r_, c_)] = (value, STYLES.index(style), formula)

    def xml(self, cache=True):
        rows = {}
        for (r_, c_), v in self.cells.items():
            rows.setdefault(r_, []).append((c_, v))
        out = []
        for r_ in sorted(rows):
            cs = []
            for c_, (value, s, f) in sorted(rows[r_]):
                a = f'r="{ref(c_, r_)}" s="{s}"'
                if f is not None:
                    fx = f"<f>{html.escape(f, quote=False)}</f>"
                    if not cache or value is None:
                        cs.append(f"<c {a}>{fx}</c>")
                    elif isinstance(value, str):
                        cs.append(f'<c {a} t="str">{fx}<v>{html.escape(value, quote=False)}</v></c>')
                    elif isinstance(value, bool):
                        cs.append(f'<c {a} t="b">{fx}<v>{int(value)}</v></c>')
                    else:
                        cs.append(f"<c {a}>{fx}<v>{repr(float(value))}</v></c>")
                elif value is None or value == "":
                    cs.append(f"<c {a}/>")
                elif isinstance(value, (int, float)) and not isinstance(value, bool):
                    cs.append(f"<c {a}><v>{repr(float(value))}</v></c>")
                else:
                    t = html.escape(str(value), quote=False)
                    cs.append(f'<c {a} t="inlineStr"><is><t xml:space="preserve">{t}</t></is></c>')
            out.append(f'<row r="{r_}">{"".join(cs)}</row>')
        cols = "".join(f'<col min="{i + 1}" max="{i + 1}" width="{w}" customWidth="1"/>' for i, w in enumerate(self.widths))
        merges = ""
        if self.merges:
            merges = f'<mergeCells count="{len(self.merges)}">' + "".join(
                f'<mergeCell ref="{m}"/>' for m in self.merges) + "</mergeCells>"
        pr = '<sheetPr><pageSetUpPr fitToPage="1"/></sheetPr>' if self.print_fit else ""
        ps = ('<pageMargins left="0.5" right="0.5" top="0.6" bottom="0.6" header="0.3" footer="0.3"/>'
              '<pageSetup ' + ({"A4": 'paperSize="9" ', "Letter": 'paperSize="1" '}.get(self.paper or "", ""))
              + 'orientation="portrait" fitToWidth="1" fitToHeight="0"/>')
        return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                f'{pr}<sheetViews><sheetView workbookViewId="0"/></sheetViews><sheetFormatPr defaultRowHeight="13"/>'
                f'<cols>{cols}</cols><sheetData>{"".join(out)}</sheetData>{merges}{ps}</worksheet>')


def write_xlsx(path, sheets, cur, title, cache=True, paper=None):
    for s_ in sheets:
        s_.paper = paper
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
          '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
          '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
          + "".join(f'<Override PartName="/xl/worksheets/sheet{i + 1}.xml" '
                    'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                    for i in range(len(sheets))) + '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
            '</Relationships>')
    wb = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
          'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
          + "".join(f'<sheet name="{html.escape(s.name)}" sheetId="{i + 1}" r:id="rId{i + 1}"/>' for i, s in enumerate(sheets))
          + '</sheets><calcPr calcId="191029" fullCalcOnLoad="1"/></workbook>')
    wbrels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
              + "".join(f'<Relationship Id="rId{i + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
                        f'relationships/worksheet" Target="worksheets/sheet{i + 1}.xml"/>' for i in range(len(sheets)))
              + f'<Relationship Id="rId{len(sheets) + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
                'relationships/styles" Target="styles.xml"/></Relationships>')
    core = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            f'<dc:title>{html.escape(title)}</dc:title><dc:creator>Made with Merigrove {SKILL_NAME}</dc:creator>'
            f'<dc:description>Made with Merigrove {SKILL_NAME}</dc:description></cp:coreProperties>')
    tmp = Path(str(path) + ".part")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("xl/workbook.xml", wb)
        z.writestr("xl/_rels/workbook.xml.rels", wbrels)
        z.writestr("xl/styles.xml", styles_xml(cur))
        z.writestr("docProps/core.xml", core)
        for i, s in enumerate(sheets):
            z.writestr(f"xl/worksheets/sheet{i + 1}.xml", s.xml(cache))
    tmp.replace(path)


# ================================================================ the workbook
def build_model(P):
    """'Try a lever': yellow inputs and live formulas for the whole chain. Cached values are computed here with
    the same arithmetic, so a preview that does not calculate still shows the run's figures."""
    sh = Sheet("Try a lever", [46, 16, 62])
    cur, R = P["currency"], P["rates"]
    sep = bool(R.get("offer"))
    sh.set(1, 1, "Try a lever: change a yellow cell and every figure below moves", "title")
    sh.set(1, 2, spell("Rounded up to whole sales and whole calls, as the plan is. Rates are per cent."), "note")
    r = 4
    sh.set(1, r, "Your figures", "head"); sh.set(2, r, "", "head"); sh.set(3, r, "Where it came from", "head")
    cells = {}

    def inp(key, label, value, style, note):
        nonlocal r
        r += 1
        sh.set(1, r, label, "label")
        sh.set(2, r, value, style)
        sh.set(3, r, note, "note")
        cells[key] = ref(2, r)

    tag_note = lambda x: f"{TAG_SHOWN[x['tag']]}" + (f", {x['basis']}" if x["tag"].startswith("measured") else "")  # noqa: E731
    monthly = P.get("billing") == "monthly"
    bydate = P.get("target_kind") == "by date"
    ptxt = "Monthly fee per client" if monthly else "Price of one sale"
    dtxt = "What one client costs to deliver a month" if monthly else "What one sale costs to deliver"
    if monthly and bydate and P["form"] != "revenue":
        inp("total", "Profit to make by the target date", P["profit_total"], "input_money", "your target")
    elif P["form"] in ("contribution", "margin"):
        inp("profit", "Profit you need a month", P["profit"], "input_money",
            f"your {money(P['profit_total'], cur)} over {plural(P['whole_months'], 'whole month')}" if bydate else "your target")
    if P["form"] == "contribution":
        inp("pay", "Your pay on top of that", P["pay"], "input_money", "0 if your pay is inside the profit figure")
        inp("running", "Running costs a month", P["running"], "input_money", "costs that stay with no clients")
        inp("price", ptxt, P["price"], "input_money", "your fee" if monthly else "your price")
        inp("delivery", dtxt, P["delivery"], "input_money",
            "freelancers, tools and materials for one client, not your own time")
    elif P["form"] == "margin":
        inp("margin", "Your margin", P["inputs"]["margin"] / 100.0, "input_pct", "profit as a share of sales")
        inp("price", ptxt, P["price"], "input_money", "your fee" if monthly else "your price")
    else:
        inp("revenue", "Sales you want a month", P["inputs"]["revenue_target"] if monthly else P["revenue_req"],
            "input_money", "your revenue target")
        inp("price", ptxt, P["price"], "input_money", "your fee" if monthly else "your price")
    if monthly:
        inp("L", "Months a client stays on average", P["ret"]["L"], "input_num1",
            "blank means no client leaves" if P["ret"]["L"] is None else "your figure")
        inp("A0", "Clients paying you now", P["ret"]["A0"], "input", "your figure")
        inp("T", "Whole months to the target date" if P.get("target_date") else "Whole months to reach the target",
            P["ret"]["T"], "input", "from today" if P.get("target_date") else "planning default")
    if sep:
        inp("offer", "Offer made on held calls", R["offer"]["value"] / 100.0, "input_pct", tag_note(R["offer"]))
        inp("offer_conv", "Offers that buy", R["offer_conv"]["value"] / 100.0, "input_pct", tag_note(R["offer_conv"]))
    else:
        inp("close", "Close rate on held calls", R["close"]["value"] / 100.0, "input_pct", tag_note(R["close"]))
    inp("show", "Show rate (booked calls that happen)", R["show"]["value"] / 100.0, "input_pct", tag_note(R["show"]))
    inp("booking", "Booking rate (leads that book a call)",
        R["booking"]["value"] / 100.0 if R["booking"]["value"] else None, "input_pct",
        tag_note(R["booking"]) if R["booking"]["value"] else "not known: leave blank, or type your rate")
    inp("callh", "Hours per call held, with prep and follow-up", P["callh"], "input_num1",
        "your figure" if P["inputs"]["call_hours"] is not None else "planning default; your own figure wins")
    inp("sell", "Hours a week you can give to sales calls", P["sell"], "input_num1",
        "your figure" if P["inputs"]["selling_hours"] is not None else "planning default")
    inp("wdays", "Selling days a month", P["wdays"], "input_num1", "for bookings a selling day")
    inp("dmax", "New clients a month you can deliver for", P["delivery_max"], "input",
        "blank means no limit")
    inp("share", "Share of the price paid in the month they sign", P["share"] / 100.0, "input_pct",
        "cash, kept apart from sales")
    C = cells
    r += 2
    sh.set(1, r, "The plan", "head"); sh.set(2, r, "", "head"); sh.set(3, r, "How it is worked out", "head")
    out = {}

    def calc(key, label, formula, value, style, note):
        nonlocal r
        r += 1
        sh.set(1, r, label, "label")
        sh.set(2, r, value, style, formula)
        sh.set(3, r, note, "note")
        out[key] = ref(2, r)

    W = "(52/12)"
    if monthly:
        rr = P["ret_res"]
        unit_f = (f"{C['price']}-{C['delivery']}" if P["form"] == "contribution" else
                  f"{C['price']}*{C['margin']}" if P["form"] == "margin" else C["price"])
        calc("unit", "Each client leaves a month", unit_f, rr["unit"], "money",
             {"contribution": "fee less delivery", "margin": "fee x margin"}.get(P["form"], "fee"))
        rT_val = (1 - 1.0 / P["ret"]["L"]) ** P["ret"]["T"] if P["ret"]["L"] else 1.0
        calc("rT", "Share of today's clients still paying at the date", f"IF(N({C['L']})>0,(1-1/{C['L']})^{C['T']},1)",
             rT_val, "pct", "about 1 in (months a client stays) leaves each month")
        if not bydate:
            need_f = (f"{C['profit']}+{C['pay']}+{C['running']}" if P["form"] == "contribution" else
                      C["profit"] if P["form"] == "margin" else C["revenue"])
            calc("need", "The business must leave a month" if P["form"] != "revenue" else "Sales you want a month",
                 need_f, P["need_ret"], "money", "profit + your pay + running costs" if P["form"] == "contribution"
                 else "your target")
            calc("A", "Paying clients needed at once", f"ROUNDUP(ROUND({out['need']}/{out['unit']},6),0)", rr["A"],
                 "int", "rounded up to whole clients")
            calc("build", "New clients a month to get there by the date",
                 f"IF(N({C['L']})>0,ROUNDUP(ROUND(MAX(0,{out['A']}-N({C['A0']})*{out['rT']})/({C['L']}*(1-{out['rT']})),6),0),"
                 f"ROUNDUP(ROUND(MAX(0,{out['A']}-N({C['A0']}))/{C['T']},6),0))", rr["build"], "int",
                 "clients leaving are replaced along the way")
            calc("hold", "New clients a month to hold it", f"IF(N({C['L']})>0,ROUNDUP(ROUND({out['A']}/{C['L']},6),0),0)",
                 rr["hold"], "int", "paying clients needed over months a client stays")
            calc("closes", "New clients a month", f"MAX({out['build']},{out['hold']})", P["closes"], "int",
                 "the higher of the two")
        else:
            fixed_f = f"({C['pay']}+{C['running']})" if P["form"] == "contribution" else "0"
            calc("U", "Paying client-months needed by the date", f"({C['total']}+{C['T']}*{fixed_f})/{out['unit']}",
                 rr["client_months"], "num1", "profit plus running costs and your pay, over what one client leaves a month")
            S_val = (P["ret"]["L"] - 1) * (1 - rT_val) if P["ret"]["L"] else None
            calc("S", "Months each of today's clients is still paying, on average",
                 f"IF(N({C['L']})>0,({C['L']}-1)*(1-{out['rT']}),{C['T']})",
                 S_val if S_val is not None else P["ret"]["T"], "num1", "before the date")
            calc("closes", "New clients a month",
                 f"IF(N({C['L']})>0,ROUNDUP(ROUND(MAX(0,{out['U']}-N({C['A0']})*{out['S']})/({C['L']}*({C['T']}-{out['S']})),6),0),"
                 f"ROUNDUP(ROUND(MAX(0,{out['U']}-N({C['A0']})*{C['T']})/({C['T']}*({C['T']}+1)/2),6),0))",
                 P["closes"], "int", "rounded up to whole clients")
    elif P["form"] == "contribution":
        calc("need", "The business must leave a month", f"{C['profit']}+{C['pay']}+{C['running']}", P["need"], "money",
             "profit + your pay + running costs")
        calc("cps", "Each sale leaves after delivery", f"{C['price']}-{C['delivery']}", P["cps"], "money",
             "price less delivery cost")
        calc("closes", "Sales a month", f'IF({out["cps"]}>0,ROUNDUP(ROUND({out["need"]}/{out["cps"]},6),0),"never")',
             P["closes"], "int", "rounded up to whole sales")
    elif P["form"] == "margin":
        calc("rev", "Sales you need a month", f"{C['profit']}/{C['margin']}", P["revenue_req"], "money",
             "profit over margin")
        calc("closes", "Sales a month", f"ROUNDUP(ROUND({out['rev']}/{C['price']},6),0)", P["closes"], "int",
             "rounded up to whole sales")
    else:
        calc("closes", "Sales a month", f"ROUNDUP(ROUND({C['revenue']}/{C['price']},6),0)", P["closes"], "int",
             "rounded up to whole sales")
    ch = P["chain"]
    if monthly and not bydate:
        calc("revplan", "Fees a month at the target", f"{out['A']}*{C['price']}", P["cash_in_month"], "money",
             "paying clients x monthly fee")
    elif not monthly:
        calc("revplan", "Sales value a month", f"{out['closes']}*{C['price']}", P["revenue_plan"], "money",
             "whole sales x price")
    if sep:
        calc("offers", "Offers made a month", f"ROUNDUP(ROUND({out['closes']}/{C['offer_conv']},6),0)", ch["offers"],
             "int", "sales over offers that buy")
        calc("held", "Calls held a month", f"ROUNDUP(ROUND({out['offers']}/{C['offer']},6),0)", ch["held"], "int",
             "offers over offer rate")
        perheld = f"({C['offer']}*{C['offer_conv']})"
    else:
        calc("held", "Calls held a month", f"ROUNDUP(ROUND({out['closes']}/{C['close']},6),0)", ch["held"], "int",
             "sales over close rate")
        perheld = C["close"]
    calc("booked", "Calls booked a month", f"ROUNDUP(ROUND({out['held']}/{C['show']},6),0)", ch["booked"], "int",
         "held over show rate")
    calc("leads", "Leads a month", f'IF(N({C["booking"]})>0,ROUNDUP(ROUND({out["booked"]}/{C["booking"]},6),0),"not known")',
         ch["leads"] if ch["leads"] else "not known", "int", "booked over booking rate")
    calc("hours", "Hours a week of calls", f"{out['held']}*{C['callh']}/{W}", P["hours_week"], "num1",
         "held calls x hours a call, over weeks in a month")
    verdict = P["calendar"]
    calc("fit", "Your calendar", f'IF({out["hours"]}>{C["sell"]},"breaks",IF({out["hours"]}>={TIGHT}*{C["sell"]},'
         f'"fits, tightly","fits"))', verdict, "default", "against your selling hours")
    calc("maxheld", "Most held calls your calendar can carry a month", f"{C['sell']}*{W}/{C['callh']}", P["max_held"],
         "num1", "selling hours over hours a call")
    calc("calcloses", "Sales your calendar can carry a month", f"{out['maxheld']}*{perheld}", P["cal_closes"], "num1",
         "at your rates")
    if monthly:
        pass
    elif P["form"] == "contribution":
        pn_val = P["need"] / math.floor(round(P["cal_closes"], 6)) + P["delivery"] if P["cal_closes"] >= 1 else "none"
        calc("pricecal", "Lowest price at which your calendar carries this target",
             f'IF(ROUNDDOWN(ROUND({out["calcloses"]},6),0)>=1,{out["need"]}/ROUNDDOWN(ROUND({out["calcloses"]},6),0)'
             f'+{C["delivery"]},"none")', pn_val, "money", "before rounding up to a price you would quote")
    elif P["form"] == "margin":
        pn_val = P["revenue_req"] / math.floor(round(P["cal_closes"], 6)) if P["cal_closes"] >= 1 else "none"
        calc("pricecal", "Lowest price at which your calendar carries this target",
             f'IF(ROUNDDOWN(ROUND({out["calcloses"]},6),0)>=1,{out["rev"]}/ROUNDDOWN(ROUND({out["calcloses"]},6),0),'
             '"none")', pn_val, "money", "before rounding up to a price you would quote")
    if not monthly:
        calc("cash", "Cash landing in the month from this month's sales", f"{out['revplan']}*{C['share']}",
             P["cash_in_month"], "money", "sales value x share paid on signing; later instalments land later")
    # pace, capped at the lower ceiling
    lim_f = f'IF(N({C["dmax"]})>0,MIN({out["calcloses"]},{C["dmax"]}),{out["calcloses"]})'
    calc("pacecl", "Sales a month the weekly pace is set at", f'MIN({out["closes"]},{lim_f})',
         min(P["closes"], P["cal_closes"], P["delivery_max"] or 1e18), "num1",
         "the plan, or your calendar or delivery limit if lower")
    pk = P["pace"]
    sh_pace_b = f"ROUNDDOWN(ROUND({out['pacecl']}/{perheld}/{C['show']}/{W},6),1)"
    calc("pace_b", "Bookings a week", f'IF({out["pacecl"]}<{out["closes"]},{sh_pace_b},ROUND(ROUND({out["booked"]}/{W},6),1))',
         pk["booked"], "num1", "never above what your calendar or delivery can carry")
    calc("pace_h", "Held calls a week", f'IF({out["pacecl"]}<{out["closes"]},ROUNDDOWN(ROUND({out["pacecl"]}/{perheld}/{W},6),1),'
         f'MIN(ROUND(ROUND({out["held"]}/{W},6),1),ROUNDDOWN(ROUND({C["sell"]}/{C["callh"]},6),1)))', pk["held"], "num1", "")
    calc("pace_c", "New clients a week" if monthly else "Sales a week",
         f'IF({out["pacecl"]}<{out["closes"]},ROUNDDOWN(ROUND({out["pacecl"]}/{W},6),1),'
         f'MIN(ROUND(ROUND({out["closes"]}/{W},6),1),IF(N({C["dmax"]})>0,ROUNDDOWN(ROUND({C["dmax"]}/{W},6),1),1E+9)))',
         pk["closes"], "num1", "")
    sh.print_fit = True
    return sh, C, out


def build_scenarios(P, C, O):
    cur, R = P["currency"], P["rates"]
    sep = bool(R.get("offer"))
    monthly = P.get("billing") == "monthly"
    bydate = P.get("target_kind") == "by date"
    A_ = lambda v: "'Try a lever'!$" + re.sub(r"(\d+)$", r"$\1", v)  # noqa: E731
    C = {k: A_(v) for k, v in C.items()}
    O = {k: A_(v) for k, v in O.items()}
    heads = ["Scenario", "Fee" if monthly else "Price", "Show rate", "Offer rate" if sep else "Close rate"]
    if monthly:
        heads += ["Months a client stays"] + ([] if bydate else ["Paying clients needed"])
    heads += ["New clients" if monthly else "Sales", "Held", "Booked", "Leads", "Bookings a day", "Hours a week",
              "Your calendar"]
    widths = [44, 12, 10, 10] + ([12] + ([] if bydate else [12]) if monthly else []) + [9, 9, 9, 9, 12, 12, 14]
    sh = Sheet("Scenarios", widths)
    last = col(len(heads))
    sh.set(1, 1, "Scenarios: what each lever buys", "title")
    sh.set(1, 2, "One lever at a time, then all three. Yellow cells are the lever; change one to test your own. "
                 "Every row starts from whole " + ("new clients." if monthly else "sales."), "note")
    sh.merges.append(f"A2:{last}2")
    for i, h in enumerate(heads):
        sh.set(i + 1, 4, h, "head")
    r = 4
    W = "(52/12)"
    for s_ in P["scenarios"]:
        r += 1
        if s_["kind"] == "met":
            sh.set(1, r, f"{s_['name']}: {s_['note']}", "wrap")
            continue
        sh.set(1, r, s_["name"], "wrap")
        k = 2
        pr = ref(k, r); sh.set(k, r, s_["price"], "input_money"); k += 1
        sw = ref(k, r); sh.set(k, r, s_["show"] / 100.0, "input_pct"); k += 1
        cl = ref(k, r); sh.set(k, r, (s_["offer"] if sep else s_["close"]) / 100.0, "input_pct"); k += 1
        if monthly:
            Lr = ref(k, r); sh.set(k, r, s_.get("L"), "input_num1"); k += 1
            unit = (f"({pr}-{C['delivery']})" if P["form"] == "contribution" else
                    f"({pr}*{C['margin']})" if P["form"] == "margin" else pr)
            rT = f"(1-1/{Lr})^{C['T']}"
            if not bydate:
                rr_ = ret_closes(P, s_["price"], s_.get("L"))
                Ar = ref(k, r)
                sh.set(k, r, rr_["A"], "int", f"ROUNDUP(ROUND({O['need']}/{unit},6),0)"); k += 1
                f_cl = (f'IF({unit}<=0,"never",IF(N({Lr})>0,MAX(ROUNDUP(ROUND(MAX(0,{Ar}-N({C["A0"]})*{rT})/({Lr}*(1-{rT})),6),0),'
                        f'ROUNDUP(ROUND({Ar}/{Lr},6),0)),ROUNDUP(ROUND(MAX(0,{Ar}-N({C["A0"]}))/{C["T"]},6),0)))')
            else:
                fixed = f"({C['pay']}+{C['running']})" if P["form"] == "contribution" else "0"
                U = f"(({C['total']}+{C['T']}*{fixed})/{unit})"
                S = f"(({Lr}-1)*(1-{rT}))"
                f_cl = (f'IF({unit}<=0,"never",IF(N({Lr})>0,ROUNDUP(ROUND(MAX(0,{U}-N({C["A0"]})*{S})/({Lr}*({C["T"]}-{S})),6),0),'
                        f'ROUNDUP(ROUND(MAX(0,{U}-N({C["A0"]})*{C["T"]})/({C["T"]}*({C["T"]}+1)/2),6),0)))')
        elif P["form"] == "contribution":
            f_cl = (f'IF({pr}-{C["delivery"]}>0,ROUNDUP(ROUND(({C["profit"]}+{C["pay"]}+{C["running"]})/'
                    f'({pr}-{C["delivery"]}),6),0),"never")')
        elif P["form"] == "margin":
            f_cl = f"ROUNDUP(ROUND({C['profit']}/{C['margin']}/{pr},6),0)"
        else:
            f_cl = f"ROUNDUP(ROUND({C['revenue']}/{pr},6),0)"
        sales = ref(k, r); sh.set(k, r, s_["closes"], "int", f_cl); k += 1
        if sep:
            f_h = f"ROUNDUP(ROUND(ROUNDUP(ROUND({sales}/{C['offer_conv']},6),0)/{cl},6),0)"
        else:
            f_h = f"ROUNDUP(ROUND({sales}/{cl},6),0)"
        held = ref(k, r); sh.set(k, r, s_["held"], "int", f_h); k += 1
        bkd = ref(k, r); sh.set(k, r, s_["booked"], "int", f"ROUNDUP(ROUND({held}/{sw},6),0)"); k += 1
        sh.set(k, r, s_["leads"] if s_["leads"] else "not known", "int",
               f'IF(N({C["booking"]})>0,ROUNDUP(ROUND({bkd}/{C["booking"]},6),0),"not known")'); k += 1
        sh.set(k, r, s_["per_day"], "num1", f"{bkd}/{C['wdays']}"); k += 1
        h = ref(k, r); sh.set(k, r, s_["hours"], "num1", f"{held}*{C['callh']}/{W}"); k += 1
        sh.set(k, r, s_["verdict"], "centre",
               f'IF(OR({h}>{C["sell"]},AND(N({C["dmax"]})>0,{sales}>N({C["dmax"]}))),"breaks",'
               f'IF({h}>={TIGHT}*{C["sell"]},"fits, tightly","fits"))')
    r += 2
    if P["three_bets"]:
        sh.set(1, r, "Only the three levers together fit your hours: that is three bets, not a plan.", "bold")
        r += 1
    sh.set(1, r, "Lever lines are planning defaults: show rate to 70%, price up 10%, close rate on held calls to 30%"
           + ("; clients staying 2 months longer." if monthly and P["ret"]["L"] else "."), "note")
    sh.merges.append(f"A{r}:{last}{r}")
    sh.print_fit = True
    return sh


def build_plan_sheet(P, note):
    sh = Sheet("Plan", [100])
    rd = datetime.strptime(P["date"], "%Y-%m-%d").date()
    sh.set(1, 1, plan_title(P), "title")
    sh.set(1, 2, f"Planned on {long_date_y(rd)}. Figures are as planned that day; to test a change, use the "
                 "Try a lever sheet.", "note")
    r = 3
    for title, lines in render(P):
        r += 1
        if title == "Headline":
            for ln in lines:
                r += 1
                sh.set(1, r, ln, "headline")
            if note:
                r += 1
                sh.set(1, r, note.strip(), "wrap")
            continue
        sh.set(1, r, title, "head")
        for ln in lines:
            r += 1
            sh.set(1, r, ln, "wrap")
        if title == "6. Scenarios":
            r += 1
            sh.set(1, r, "The table and its live formulas are on the Scenarios sheet.", "note")
    r += 2
    sh.set(1, r, f"Made with Merigrove {SKILL_NAME}.", "note")
    sh.print_fit = True
    return sh


def build_assumptions(P):
    sh = Sheet("Assumptions", [44, 30, 60])
    sh.set(1, 1, "What the plan assumed, and where each figure came from", "title")
    for i, h in enumerate(["Item", "Value", "Basis"]):
        sh.set(i + 1, 3, h, "head")
    r = 3
    R = P["rates"]
    rows = []
    for k, lab in (("show", "Show rate"), ("close", "Close rate on held calls"), ("booking", "Booking rate"),
                   ("offer", "Offer made on held calls"), ("offer_conv", "Offers that buy")):
        x = R.get(k)
        if not x:
            continue
        rows.append((lab, pct(x["value"], 1) if x["value"] is not None else "not known",
                     TAG_SHOWN[x["tag"]] + (f": {x['basis']}" if x["basis"] and x["basis"] != TAG_SHOWN[x["tag"]]
                                            and x["basis"] != x["tag"] else "")))
    for lab, val, tag in P["assume"]:
        rows.append((lab, val, "default; change it in Try a lever" if tag == "assumed" else tag))
    src = P["inputs"].get("sources") or {}
    for k, v in src.items():
        rows.append((f"Source of {k.replace('_', ' ')}", "", str(v)))
    for n in P["notes"]:
        rows.append(("Read from what you gave", "", n))
    for n in P["needs"]:
        rows.append(("Still needed", "", f"[NEED: {n}]"))
    rows.append(("Planning defaults", "show 60%, close 20% on held calls (inbound); 70% and 10% (outbound); "
                 "1.5 hours a call; 8 selling hours a week; 20 selling days a month",
                 "used only where you gave no figure; never a statistic about other businesses"))
    rows.append(("Advice", "", ADVICE_LINE))
    for a, b, c_ in rows:
        r += 1
        sh.set(1, r, spell(a), "label")
        sh.set(2, r, spell(b), "wrap")
        sh.set(3, r, spell(c_), "wrap")
    return sh


def build_weeks(P):
    """Week by week: the weekly pace scaled to each week's selling days, with a total row."""
    sw = "New clients" if P.get("billing") == "monthly" else "Sales"
    sh = Sheet("Week by week", [44, 14, 12, 12, 12, 14])
    sh.set(1, 1, "Week by week", "title")
    sh.set(1, 2, "Each week is the weekly pace scaled to the days you take calls in it, less your days off. The total "
                 "is the sum of the weeks shown, not the monthly target.", "note")
    for i, h in enumerate(["Week of", "Selling days", "Bookings", "Held calls", sw, "Hours of calls"]):
        sh.set(i + 1, 4, h, "head")
    r, first = 4, 5
    for w in P.get("weeks") or []:
        r += 1
        w0 = datetime.strptime(w["week"], "%Y-%m-%d").date()
        lab = long_date(w0)
        bits = []
        if w["from"] and w["from"] != w["week"] and r == first:
            bits.append("from " + long_date(datetime.strptime(w["from"], "%Y-%m-%d").date()))
        if w["off"]:
            bits.append("closed " + ", ".join(long_date(datetime.strptime(x, "%Y-%m-%d").date()) for x in w["off"]))
        sh.set(1, r, spell(lab + (f" ({'; '.join(bits)})" if bits else "")), "wrap")
        sh.set(2, r, w["days"], "int")
        if P.get("pace_whole"):
            g = (lambda v: float(math.floor(round(v, 6)) if P["capped"] else math.ceil(round(v, 6))))
            sh.set(3, r, g(w["booked"]), "int")
            sh.set(4, r, g(w["held"]), "int")
            sh.set(5, r, g(w["closes"]), "int")
        else:
            sh.set(3, r, w["booked"], "num1")
            sh.set(4, r, w["held"], "num1")
            sh.set(5, r, w["closes"], "num1")
        sh.set(6, r, round1(w["held"] * P["callh"]), "num1")
    last = r
    if last >= first:
        r += 1
        sh.set(1, r, f"Total, {plural(last - first + 1, 'week')}", "bold")
        for c_ in range(2, 7):
            tot = sum((sh.cells[(k, c_)][0] or 0) for k in range(first, last + 1))
            sh.set(c_, r, round(tot, 6), "int" if c_ == 2 else "num1", f"SUM({ref(c_, first)}:{ref(c_, last)})")
    sh.print_fit = True
    return sh


def build(P, out_dir, note=None, cache=True):
    out_dir.mkdir(parents=True, exist_ok=True)
    plan_sh = build_plan_sheet(P, note)
    model, C, O = build_model(P)
    scen = build_scenarios(P, C, O)
    assum = build_assumptions(P)
    sheets = [plan_sh] + ([build_weeks(P)] if P["chain"]["closes"] and P.get("weeks") else []) + [model, scen, assum]
    name = f"sales-target-plan_{P['date']}.xlsx"
    path = out_dir / name
    write_xlsx(path, sheets, P["currency"], plan_title(P), cache, P["inputs"].get("paper"))
    return path


# ================================================================ consistency gate before anything is written
def gate(P):
    probs = []
    c = P["chain"]
    pk = P["pace"]
    if not isinstance(c["closes"], int):
        probs.append("sales are not whole")
    if pk["held"] is not None and pk["held"] > P["max_held"] / WEEKS_PER_MONTH + 1e-6:
        probs.append("the weekly pace asks for more held calls than the calendar carries")
    if P["delivery_max"] and pk["closes"] * WEEKS_PER_MONTH > P["delivery_max"] + 0.05 and P["capped"]:
        probs.append("the weekly pace asks for more sales than delivery carries")
    for k in ("show", "close", "booking"):
        if P["rates"][k]["tag"] not in TAG_SHOWN:
            probs.append(f"{k} rate untagged")
    if not P["first_week"] or any(not x["owner"] or not x["date"] for x in P["first_week"]):
        probs.append("first week without a date or owner")
    if sum(1 for _ in [P["binding"]] if _) > 1:
        probs.append("more than one binding constraint")
    return probs


# ================================================================ commands
def load_inputs(path):
    p = Path(path)
    if not p.exists():
        raise InputError(f"there is no inputs file at {path}")
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise InputError(f"the inputs file is not valid JSON ({e.msg} at line {e.lineno})")
    I, notes, needs, assume = normalise(raw)
    I["_notes"], I["_needs"], I["_assume"] = notes, needs, assume
    return raw, I


def results_json(P):
    def clean(o):
        if isinstance(o, dict):
            return {k: clean(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [clean(v) for v in o]
        if isinstance(o, date):
            return o.isoformat()
        return o
    return clean(P)


def since_lines(P, prev):
    """Return-run comparison: the last plan's monthly figures against what actually happened."""
    if not prev:
        return []
    lp = prev.get("_last_plan") or {}
    tot = P["actuals_total"]
    A = P["inputs"].get("actuals") or []
    last = A[-1] if A else None
    out = []
    if lp and last:
        for k, lab in (("booked", "calls booked"), ("held", "calls held"), ("closes", "sales")):
            key = {"booked": "booked", "held": "showed", "closes": "closed"}[k]
            if lp.get(k) not in (None, "") and last.get(key) is not None:
                out.append(f"{fmt(float(last[key]))} {lab} against {fmt(float(lp[k]))} planned")
    if out:
        def nice(v, fmt_in, fmt_out):
            try:
                d = datetime.strptime(str(v), fmt_in).date()
                return fmt_out(d)
            except ValueError:
                return str(v or "")
        when = nice(lp.get("date"), "%Y-%m-%d", day_month) or "last time"
        month = nice(last.get("month"), "%Y-%m", lambda d: d.strftime("%B %Y")) or "last month"
        return [f"Against your plan of {when}, {month} came in at " + ", ".join(out) + "."]
    return []


def cmd_compute(a):
    raw, I = load_inputs(a.inputs)
    P = plan(I)
    probs = gate(P)
    if probs:
        raise InputError("the plan failed its own checks (" + "; ".join(probs) + "). Nothing was written")
    print(render_text(P))
    print("\n".join(chat_lines(P)))
    if a.json_out:
        Path(a.json_out).write_text(json.dumps(results_json(P), indent=1, default=str), encoding="utf-8")
        print(f"JSON: {a.json_out}")
    for n in P["needs"]:
        print(f"NEED: {spell(n)}")
    return 1 if P["needs"] else 0


def cmd_build(a):
    raw, I = load_inputs(a.inputs)
    P = plan(I)
    probs = gate(P)
    if probs:
        raise InputError("the plan failed its own checks (" + "; ".join(probs) + "). Nothing was written")
    prev = None
    if a.previous:
        pp = Path(a.previous)
        if pp.exists():
            prev = json.loads(pp.read_text(encoding="utf-8"))
    P["since"] = since_lines(P, prev)
    P["_prev"] = prev
    note = None
    if a.note:
        np_ = Path(a.note)
        if not np_.exists():
            raise InputError(f"there is no note file at {a.note}")
        note = np_.read_text(encoding="utf-8").strip()
        bad = check_note(note, P)
        if bad:
            raise InputError("the note was refused: " + "; ".join(bad) + ". Rewrite it from the plan's own figures")
    P.pop("_prev", None)
    path = build(P, Path(a.out), note, cache=not a.no_cache)
    if a.json_out:
        Path(a.json_out).write_text(json.dumps(results_json(P), indent=1, default=str), encoding="utf-8")
    print(render_text(P, note))
    print("\n".join(chat_lines(P)))
    print(f"WROTE: {path}")
    for n in P["needs"]:
        print(f"NEED: {spell(n)}")
    return 1 if P["needs"] else 0


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("template")
    c = sub.add_parser("compute")
    c.add_argument("inputs")
    c.add_argument("--json-out")
    b = sub.add_parser("build")
    b.add_argument("inputs")
    b.add_argument("--out", required=True)
    b.add_argument("--note")
    b.add_argument("--previous")
    b.add_argument("--json-out")
    b.add_argument("--no-cache", action="store_true", help="formulas only (for testing recalculation)")
    a = p.parse_args()
    if a.cmd == "template":
        print(json.dumps(TEMPLATE, indent=2))
        return 0
    return {"compute": cmd_compute, "build": cmd_build}[a.cmd](a)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except InputError as e:
        print(f"STOP: {e}. Nothing was written.")
        sys.exit(2)
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print(f"STOP: the planner hit an error it did not expect ({type(e).__name__}: {e}). Check the inputs file "
              "against the template and run again. Nothing was written.")
        sys.exit(2)
