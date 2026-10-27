#!/usr/bin/env python3
"""Read money, hours and dates the way founders actually type them, in any country.

Imported by scope_kit.py. Standard library only. Numbers, money and durations go through locale_numbers.py
(Merigrove's shared reader, copied here unchanged), so 9.800,00 €, 7,5 Std., 2 Tage, 1 234,56 and 18,00,000
all read correctly. Every reader returns (value, note). value is None when the text cannot be read with
confidence; the caller turns None into a [NEED: ...] line, or, when the note starts "ASK:", one plain question
for the founder. Never a guess.

  money("£1.9k pm")          -> (1900.0, "")        the period and currency are read separately
  money("9.800,00 € netto")  -> (9800.0, "")
  money("12.500 €")          -> (None, "ASK: ...")  thousands or decimals, unless the founder's style is known
  hours("half a day", 8)     -> (4.0, "half a day at 8 hours a day")
  hours("7,5 Std.")          -> (7.5, "")
  hours("3-4 days", 7)       -> (24.5, "3 to 4 days: 21 to 28 hours, the middle (24.5) used")
  date_("3rd Sept", today)   -> (date(2026, 9, 3), "")

Nothing here assumes a country. The working day, the currency, the decimal style and the order of day and month
all come from the founder: call set_order() and set_style() before reading.
"""
import re
from datetime import date, timedelta

import locale_numbers as L

MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}
WORDNUM = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
           "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "couple": 2, "a couple": 2,
           "a couple of": 2, "half": 0.5, "a half": 0.5, "half a": 0.5, "quarter": 0.25}
# Month names founders type in other languages, first three letters (the English ones read as they are).
MONTH_ALIASES = {"okt": "oct", "dez": "dec", "m\u00e4r": "mar", "mrz": "mar", "mai": "may", "ene": "jan", "abr": "apr",
                 "ago": "aug", "set": "sep", "dic": "dec", "f\u00e9v": "feb", "avr": "apr", "jui": "jul", "ao\u00fb": "aug",
                 "d\u00e9c": "dec", "gen": "jan", "giu": "jun", "lug": "jul", "ott": "oct", "mei": "may"}
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
# Sales-tax words in the languages founders write their own prices in. Kept as the founder's words, never computed.
TAX_WORDS = r"(vat|gst|hst|pst|qst|sales tax|tax|mwst\.?|ust\.?|tva|iva|btw|moms|igv|ppn|sst)"
PLUS_WORDS = r"(\+|plus|zzgl\.?|zuz\u00fcglich|ex\.?|exc\.?|excl\.?|excluding|hors|exkl\.?)"
INCL_WORDS = r"(inc|incl|including|inclusive of|inkl\.?|inklusive|ttc|iva incluido|incl\u00edda)"
NET_WORDS = r"\b(netto|net|ht|hors taxes|h\.t\.)\b"
GROSS_WORDS = r"\b(brutto|gross|ttc)\b"
ORDER = None          # "dmy" or "mdy": how the founder writes 3/9. None until the founder shows or says it.
DECIMAL = None        # "dot" or "comma": how the founder writes decimals. None until their figures show it.
STYLE = {"decimal": None, "group": ",", "sign_after": False}   # how figures are written back to the founder
DEFAULT_HOURS_PER_DAY = 8.0
MONTH_ONLY = "month only: no day given"
CURRENCY_CODES = ("USD", "GBP", "EUR", "AUD", "NZD", "CAD", "SGD", "HKD", "INR", "MYR", "PHP", "IDR", "THB", "JPY", "CNY", "KRW",
                  "AED", "SAR", "ZAR", "NGN", "KES", "CHF", "SEK", "NOK", "DKK", "PLN", "CZK", "BRL", "MXN", "TRY", "ILS", "QAR",
                  "KWD", "TWD", "VND", "PKR", "LKR", "BDT", "EGP", "CLP", "COP", "ARS", "PEN")


def set_order(order):
    global ORDER
    order = str(order or "").lower().replace("/", "").replace("-", "").strip()
    ORDER = "dmy" if order.startswith(("d", "day")) else "mdy" if order.startswith(("m", "month")) else None
    return ORDER


def set_style(samples, said=None):
    """Read the founder's number style once, from the figures they typed (never from dates or our own '=' sums).
    said: a sample of their style from memory or their own words ("1.234,50 €"). Returns the STYLE dict."""
    global DECIMAL
    texts = [str(x) for x in samples if isinstance(x, str) and x.strip() and not x.strip().startswith("=")]
    dec = L.detect_decimal_style([said]) if said else None
    dec = dec or L.detect_decimal_style(texts)
    DECIMAL = dec
    look = " ".join(([str(said)] if said else []) + texts)
    group = ","
    if dec == "comma":
        group = "\u00a0" if re.search(r"\d[ \u00a0\u202f]\d{3}\b", look) else "."
    elif re.search(r"\d'\d{3}", look):
        group = "'"
    after = bool(re.search(r"\d\s?(€|£|\$|¥|₹|kr|zł|Kč|CHF|EUR|USD|GBP|SEK|NOK|DKK|PLN|CZK|MYR|SGD|AUD|NZD|CAD|INR|JPY)", look)) and \
        not re.search(r"(€|£|\$|¥|₹)\s?\d", look)
    if said and "sign after" in str(said):
        after = True
    STYLE.update({"decimal": dec, "group": group, "sign_after": after})
    return STYLE


def style_sample():
    """How the founder writes money, as a sample memory can keep: '1,234.50', '1.234,50 €'."""
    dec = "," if STYLE["decimal"] == "comma" else "."
    s = f"1{STYLE['group']}234{dec}50"
    return s + " (sign after)" if STYLE["sign_after"] else s


def fmt_number(v, decimals=0):
    """A figure in the founder's own style: 9,800 or 9.800; 7.5 or 7,5."""
    neg = v < 0
    v = abs(v)
    if decimals:
        whole, frac = f"{v:.{decimals}f}".split(".")
    else:
        whole, frac = str(int(v // 1 + (1 if v % 1 >= 0.5 else 0))), ""
    grouped = ""
    while len(whole) > 3:
        grouped = STYLE["group"] + whole[-3:] + grouped
        whole = whole[:-3]
    grouped = whole + grouped
    if frac:
        grouped += ("," if STYLE["decimal"] == "comma" else ".") + frac
    return ("-" if neg else "") + grouped


def fmt_plain(v):
    """A short figure such as hours or months: 7.5 or 7,5; 24 not 24.0."""
    v = round(v, 2)
    t = f"{v:g}"
    return t.replace(".", ",") if STYLE["decimal"] == "comma" else t


def infer_order(texts):
    """Read the founder's date order from dates that can only be one way round (25/9 or 9/25)."""
    seen = set()
    for t in texts:
        for a, b in re.findall(r"\b(\d{1,2})[/.](\d{1,2})\b", str(t or "")):
            a, b = int(a), int(b)
            if a > 12 >= b:
                seen.add("dmy")
            elif b > 12 >= a:
                seen.add("mdy")
    return seen.pop() if len(seen) == 1 else None


def _blank(s):
    return s is None or str(s).strip().lower() in ("", "none", "n/a", "na", "-", "?", "unknown", "not sure", "dunno", "skip", "tbc")


def _safe_expr(expr):
    """Evaluate '=2 + 3 + 1.5' or '= 1900 * 12 / 52' with numbers and + - * / ( ) only (dot decimals: Claude writes these)."""
    e = expr.strip().lstrip("=").replace("x", "*").replace("×", "*")
    if not re.fullmatch(r"[\d\s.+\-*/()]+", e):
        return None
    try:
        v = eval(e, {"__builtins__": {}}, {})  # noqa: S307  the pattern above allows digits and operators only
    except Exception:  # noqa: BLE001
        return None
    return float(v)


def _num(tok):
    """One number as the founder typed it, in their decimal style. Raises L.Ambiguous or L.Unreadable."""
    return L.parse_number(tok, DECIMAL, allow_words=False)[0]


def _ask(text, e):
    if isinstance(e, L.Ambiguous):
        return f"ASK: {e}"
    return f"ASK: '{text}' could not be read; ask the founder to restate it as a plain number"


PERIOD_WORDS = (r"(p\.?m\.?\b|/\s*mo(nth)?\b|/\s*m\b|a month|per month|monthly|pcm|each month|every month|a mth|/mth|"
                r"p\.?w\.?\b|/\s*w(ee)?k\b|a week|per week|weekly|each week|every week|"
                r"p\.?a\.?\b|/\s*y(ea)?r\b|a year|per year|per annum|annually|yearly|im monat|pro monat|monatlich|par mois|al mes)")


def period_of(s):
    s = s.lower()
    if re.search(r"(p\.?m\.?\b|/\s*mo(nth)?\b|/\s*m\b|a month|per month|monthly|pcm|each month|every month|a mth|/mth)", s):
        return "month"
    if re.search(r"(p\.?w\.?\b|/\s*w(ee)?k\b|a week|per week|weekly|each week|every week)", s):
        return "week"
    if re.search(r"(p\.?a\.?\b|/\s*y(ea)?r\b|a year|per year|per annum|annually|yearly)", s):
        return "year"
    if re.search(r"(/\s*day|a day|per day|daily)\b", s) and not re.search(r"half a day|a day'?s", s):
        return "day"
    return None


def _clean_money(t):
    """Strip the words founders put beside a price that are not the price: tax words, periods, 'approx'. Case is kept,
    because S$ and s$ are not the same to the currency reader."""
    I = re.I
    t = re.sub(rf"{PLUS_WORDS}\s*(\d+(?:[.,]\d+)?\s*%\s*)?{TAX_WORDS}(?!\w)", " ", t, flags=I)
    t = re.sub(rf"\b{INCL_WORDS}\.?\s*(\d+(?:[.,]\d+)?\s*%\s*)?{TAX_WORDS}(?!\w)", " ", t, flags=I)
    t = re.sub(NET_WORDS + "|" + GROSS_WORDS, " ", t, flags=I)
    t = re.sub(r"\b(summe|gesamt|total|fixed price|fixed|flat|festpreis|pauschal|retainer|fee)\b", " ", t, flags=I)
    t = re.sub(PERIOD_WORDS, " ", t, flags=I)
    t = re.sub(r"\b(about|around|roughly|approx\.?|circa|ca\.|c\.|approximately|ungef\u00e4hr|etwa)\b|~", " ", t, flags=I)
    t = re.sub(r"(?<=\d)\s*-?ish\b", " ", t, flags=I)
    return re.sub(r"\s+", " ", t).strip(" ,;:")


def money(s):
    """Return (amount, note). k, m, grand, lakh, crore, 万 and the founder's decimal style are read by locale_numbers.
    Periods are reported by period_of, not applied here. A range gives its middle, said in the note."""
    if isinstance(s, (int, float)):
        return float(s), ""
    if _blank(s):
        return None, "not given"
    t = str(s).strip()
    if t.startswith("="):
        v = _safe_expr(t)
        return (v, f"worked out from {t.lstrip('=').strip()}") if v is not None else (None, f"could not read '{t}'")
    low = _clean_money(t)
    if re.match(r"^\s*[-\u2212]\s*\D?\s*\d", low) or re.match(r"^\s*\(.*\)\s*$", low):
        return None, f"'{t}' is negative"
    m = re.fullmatch(r"(?:between\s+)?(.+?)\s*(?:-|\u2013|to|and|bis|a)\s*(.+)", low)
    if m and re.search(r"\d", m.group(1)) and re.search(r"\d", m.group(2)):
        try:
            a, b = L.parse_money(m.group(1), DECIMAL)[0], L.parse_money(m.group(2), DECIMAL)[0]
            if b > a > 0:
                return (a + b) / 2, f"read as {fmt_plain(a)} to {fmt_plain(b)}, using {fmt_plain((a + b) / 2)}"
        except (L.Ambiguous, L.Unreadable):
            pass
    try:
        v, _cur, _notes = L.parse_money(low, DECIMAL)
    except L.Ambiguous as e:
        return None, _ask(t, e)
    except L.Unreadable as e:
        m2 = re.search(r"\b(a|one|two|three|four|five|ten)\s+(grand|thousand|k)\b", low)
        if m2:
            return float(WORDNUM.get(m2.group(1), 1)) * 1000, ""
        return None, _ask(t, e) if re.search(r"\d", low) else f"could not read '{t}'"
    if v < 0:
        return None, f"'{t}' is negative"
    return v, ""


def currency_of(s):
    """(code, sign) from how the founder wrote a figure: 'S$4,500' -> ('SGD', 'S$'); '$4,500' -> ('$', '$');
    '4500 MYR' -> ('MYR', ''); '9.800,00 €' -> ('EUR', '€'). (None, '') when nothing names a currency.
    A bare '$' stays '$' and '¥' stays '¥': never a country guess."""
    t = str(s or "")
    code = L.find_currency(t)
    if not code:
        return None, ""
    sign = ""
    for sym, c in L._SYMBOLS:  # longest first, the same order locale_numbers reads them in
        if sym in ("Rs", "Rs.", "kr", "RM"):
            if re.search(r"(?<![A-Za-z])" + re.escape(sym) + r"(?=\s?[\d.,])|(?<=[\d\s])" + re.escape(sym) + r"\b", t):
                sign = sym
                break
            continue
        if sym in t:
            sign = sym
            break
    if code == "DOLLAR":
        return "$", sign or "$"
    if "_OR_" in code or code in ("PESO", "SHILLING"):
        return (sign or code), sign
    if re.fullmatch(r"[A-Z]{3}", code) and re.search(rf"\b{code}\b", t.upper()) and not sign:
        return code, ""
    return code, sign


def tax_wording(s):
    """How the founder writes sales tax beside a price, kept in their own words, never interpreted.
    '1.9k pm + VAT' -> ('plus', 'VAT'); 'S$3,600 + GST' -> ('plus', 'GST'); '$900 incl. tax' -> ('including', 'tax');
    '9.800 € zzgl. 19% MwSt.' -> ('plus', 'MwSt.'); '9.800,00 € netto' -> ('net', 'netto'). The rate is never kept."""
    raw = str(s or "")
    low = raw.lower()

    def word(w):
        w = w.strip()
        hit = re.search(re.escape(w), raw, re.I)
        out = hit.group(0) if hit else w
        return out.upper() if out.lower() in ("vat", "gst", "hst", "pst", "qst", "tva", "iva", "btw", "igv", "ppn", "sst") else out
    m = re.search(rf"{PLUS_WORDS}\s*(?:\d+(?:[.,]\d+)?\s*%\s*)?{TAX_WORDS}(?!\w)", low)
    if m:
        return "plus", word(m.group(2))
    m = re.search(rf"\b{INCL_WORDS}\.?\s*(?:\d+(?:[.,]\d+)?\s*%\s*)?{TAX_WORDS}(?!\w)", low)
    if m:
        return "including", word(m.group(2))
    m = re.search(GROSS_WORDS, low)
    if m:
        return "including", word(m.group(1))
    m = re.search(NET_WORDS, low)
    if m:
        return "net", word(m.group(1))
    return None, ""


VAGUE_HOURS = r"\b(few|several|some|lots|loads|ages|bit|forever|endless)\b"


def hours_range(s, hours_per_day=DEFAULT_HOURS_PER_DAY):
    """(low, high) in hours when the founder gave a range ('30-40 hrs', '3 to 4 days'), else None."""
    v, note = hours(s, hours_per_day)
    m = re.search(r"([\d.,]+) to ([\d.,]+) hours, the middle", note or "")
    if v is None or not m:
        return None
    return float(m.group(1).replace(",", ".")), float(m.group(2).replace(",", "."))


def hours(s, hours_per_day=DEFAULT_HOURS_PER_DAY):
    """Return (hours, note). Reads 6, '6h', '7,5 Std.', '1.5 hours', '90 mins', '1:30', 'half a day', '2 Tage',
    'a day and a half', 'an hour', 'a couple of hours', '4-6', '3-4 days' (the middle of the range, said in the
    note), '=2+3+1.5'. 'A few hours' and a unit it does not know are not read: (None, note), never a bare number.
    Days use the founder's working day (hours_per_day), stated in the kit."""
    if isinstance(s, (int, float)):
        return (float(s), "") if s >= 0 else (None, "negative hours")
    if _blank(s):
        return None, "not given"
    t = str(s).strip()
    expr = t if t.startswith("=") else (t.split("=", 1)[1] if "=" in t else None)
    if expr is not None:
        v = _safe_expr(expr)
        if v is None:
            return None, f"could not read '{t}'"
        return (v, f"worked out from {expr.lstrip('=').strip()}") if v >= 0 else (None, "negative hours")
    low = t.lower()
    if re.search(r"\b(each|apiece|per (item|piece|post|page|one|round))\b|\bje\b|\bpro (stück|seite|runde)\b", low):
        return None, f"'{t}' is per item; write the total, for example =3*2 for two at 3 hours"
    low = re.sub(r"\b(about|around|roughly|approx\.?|approximately|circa|ca\.|c\.|maybe|probably|prob|at least|easily|like|"
                 r"just|only|max|ungefähr|etwa|vielleicht)\b|~", " ", low)
    low = re.sub(r"(?<=\d)\s*-?ish\b", " ", low)
    low = re.sub(r"\b(of work|of dev|dev|work|in total|total|all in|idk|i think|i guess|or so)\b", " ", low)
    more = bool(re.search(r"\b(or )?more\b|(?<=\d)\s*\+(?!\s*\d)", low))
    low = re.sub(r"\b(maybe |or |probably )?more\b|(?<=\d)\s*\+(?!\s*\d)|\bw/.*$|\bwith .*$", " ", low)
    if re.search(r"\d", low):
        low = re.sub(PERIOD_WORDS, " ", low)  # '20 hrs a month': the period is read by per_month, not here
    low = re.sub(r"\s+", " ", low).strip(" ,;:?")
    if re.search(VAGUE_HOURS, low) and not re.search(r"\d", low):
        return None, f"'{t}' is not a number of hours"
    if re.match(r"^\s*[-\u2212]\s*\d", low):
        return None, "negative hours"
    m = re.fullmatch(r"([\d.,]+)\s*-?\s*(?:hours?|hrs?|h|std\.?|stunden)\s*(?:working\s+|work\s+)?(?:days?|tage?|a day|per day|am tag)", low)
    if m:  # '8 hour days', '7,5 Std. am Tag': the length of a working day
        try:
            return _num(m.group(1)), ""
        except (L.Ambiguous, L.Unreadable) as e:
            return None, _ask(t, e)
    if re.search(r"\b(a|one|1)\s+(?:full\s+)?day and a half\b|\bday and a half\b|\bone and a half days\b", low):
        return 1.5 * hours_per_day, f"a day and a half at {fmt_plain(hours_per_day)} hours a day"
    m = re.fullmatch(r"([\d.,]+)\s*(?:h|hrs?|hours?)\s*(?:and\s*)?([\d.,]+)\s*(?:m|mins?|minutes?)", low)
    if m:
        try:
            v = _num(m.group(1)) + _num(m.group(2)) / 60
        except (L.Ambiguous, L.Unreadable) as e:
            return None, _ask(t, e)
        return v, f"{t} read as {fmt_plain(v)} hours"
    m = re.fullmatch(r"([\d.,]+)\s*(?:x|×|\*|lots of|times)\s*([\d.,]+)\s*(h|hrs?|hours?|mins?|minutes?)?", low)
    if m and (m.group(3) is None):
        try:
            v = _num(m.group(1)) * _num(m.group(2))
        except (L.Ambiguous, L.Unreadable) as e:
            return None, _ask(t, e)
        return v, f"{m.group(0).strip()} read as {fmt_plain(v)} hours"
    try:
        v, notes = L.parse_hours(low, day_hours=hours_per_day, decimal=DECIMAL)
    except L.Ambiguous as e:
        return None, _ask(t, e)
    except L.Unreadable as e:
        return None, _ask(t, e) if re.search(r"\d", low) else f"could not read '{t}'"
    if v < 0:
        return None, "negative hours"
    note = f"{t}: read as {fmt_plain(v)} hours; you said it could be more, so treat it as a floor" if more else ""
    for n in notes:
        rm = re.match(r"range ([\d.]+) to ([\d.]+) hours, midpoint used", n)
        if rm:
            a, b = float(rm.group(1)), float(rm.group(2))
            note = f"{t}: {fmt_plain(a)} to {fmt_plain(b)} hours, the middle ({fmt_plain(v)}) used" + (", and you said it could be more" if more else "")
            if any(n2.startswith("day =") for n2 in notes) or re.search(r"\bday|tag|jour|día|week", low):
                note += f", at {fmt_plain(hours_per_day)} hours a day"
            break
        if n.startswith("day ="):
            note = f"{t} at {fmt_plain(hours_per_day)} hours a day"
        elif n.startswith("week ="):
            note = f"{t} at {fmt_plain(hours_per_day)} hours a day, 5 days a week"
        elif "or two" in n or n.startswith("'a "):
            note = f"{t} read as {fmt_plain(v)} hours"
    return v, note


def per_month(value, text, default_period):
    """Turn a figure into a monthly one using the period written beside it ('5 a week', '£23k a year')."""
    p = period_of(str(text)) or default_period
    if value is None:
        return None, ""
    if p == "week":
        return value * 52 / 12, f"{value:g} a week, times 52, divided by 12"
    if p == "year":
        return value / 12, f"{value:g} a year, divided by 12"
    return value, ""


def _year_for(mo, d, today, prefer):
    """Pick the year: past dates for things that happened, nearest for dates due."""
    cands = []
    for y in (today.year - 1, today.year, today.year + 1):
        try:
            cands.append(date(y, mo, d))
        except ValueError:
            pass
    if not cands:
        return None
    if prefer == "past":
        past = [c for c in cands if c <= today + timedelta(days=1)]
        return max(past) if past else min(cands)
    return min(cands, key=lambda c: abs((c - today).days))


def date_(s, today, prefer="nearest"):
    """Return (date, note). prefer='past' for when something was asked or done; 'nearest' for due dates."""
    if isinstance(s, date):
        return s, ""
    if _blank(s):
        return None, "not given"
    t = str(s).strip()
    low = t.lower().strip().rstrip(".")
    low = re.sub(r"\b(since|from|around|about|on|by|the|early|start of|beginning of|w/c|week commencing|wc|week of)\b", " ", low)
    low = re.sub(r"\s+", " ", low).strip()
    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", low)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3))), ""
        except ValueError:
            return None, f"'{t}' is not a real date"
    if low in ("today", "now", "this week"):
        return today, ""
    if low == "yesterday":
        return today - timedelta(days=1), ""
    if low == "tomorrow":
        return today + timedelta(days=1), ""
    m = re.fullmatch(r"(\d+|a|an|one|two|three|four|five|six)\s+(days?|weeks?|months?)\s+ago", low)
    if m:
        n = int(WORDNUM.get(m.group(1), 0) or m.group(1))
        days = {"d": 1, "w": 7, "m": 30}[m.group(2)[0]] * n
        return today - timedelta(days=days), f"{t}, counted back from {today.isoformat()}"
    m = re.fullmatch(r"in\s+(\d+|a|one|two|three|four)\s+(days?|weeks?|months?)", low)
    if m:
        n = int(WORDNUM.get(m.group(1), 0) or m.group(1))
        days = {"d": 1, "w": 7, "m": 30}[m.group(2)[0]] * n
        return today + timedelta(days=days), f"{t}, counted on from {today.isoformat()}"
    m = re.fullmatch(r"(next|last|this)\s+(mon|tues|wednes|thurs|fri|satur|sun)(day)?", low)
    if m:
        wd = [w[:3] for w in WEEKDAYS].index(m.group(2)[:3])
        delta = (wd - today.weekday()) % 7
        if m.group(1) == "next":
            delta = delta or 7
            return today + timedelta(days=delta), f"{t} from {today.isoformat()}"
        if m.group(1) == "last":
            back = (today.weekday() - wd) % 7 or 7
            return today - timedelta(days=back), f"{t} from {today.isoformat()}"
        return today + timedelta(days=delta), ""
    if re.fullmatch(r"end of (this |the )?month|month end|eom", low):
        nxt = date(today.year + (today.month == 12), today.month % 12 + 1, 1)
        return nxt - timedelta(days=1), "end of this month"
    m = re.fullmatch(r"(\d{1,2})[/.](\d{1,2})(?:[/.](\d{2,4}))?", low)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        order = ORDER or ("dmy" if a > 12 else "mdy" if b > 12 else "same" if a == b else None)
        if order is None:
            return None, (f"'{t}' could be {a} {list(MONTHS)[b - 1].title()} or {list(MONTHS)[a - 1].title()} {b}; "
                          "say which way round you write dates")
        d, mo = (b, a) if order == "mdy" else (a, b)
        if mo > 12:
            return None, f"'{t}' is not a real date written {'month first' if order == 'mdy' else 'day first'}"
        if m.group(3):
            y = int(m.group(3))
            y += 2000 if y < 100 else 0
            try:
                return date(y, mo, d), ""
            except ValueError:
                return None, f"'{t}' is not a real date"
        got = _year_for(mo, d, today, prefer)
        return (got, "") if got else (None, f"'{t}' is not a real date")
    m = re.fullmatch(r"(\d{1,2})(?:st|nd|rd|th|\.)?\s+(?:of\s+)?([^\W\d_]{3,9})\.?(?:\s+(\d{2,4}))?", low)
    m2 = re.fullmatch(r"([^\W\d_]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(\d{2,4}))?", low)
    if m or m2:
        if m:
            d, mon, y = int(m.group(1)), m.group(2)[:3], m.group(3)
        else:
            mon, d, y = m2.group(1)[:3], int(m2.group(2)), m2.group(3)
        mon = MONTH_ALIASES.get(mon, mon)
        if mon not in MONTHS:
            return None, f"could not read '{t}'"
        if y:
            yy = int(y) + (2000 if int(y) < 100 else 0)
            try:
                return date(yy, MONTHS[mon], d), ""
            except ValueError:
                return None, f"'{t}' is not a real date"
        got = _year_for(MONTHS[mon], d, today, prefer)
        return (got, "") if got else (None, f"'{t}' is not a real date")
    m = re.fullmatch(r"([^\W\d_]{3,9})(?:\s+(\d{4}))?", low)
    if m and MONTH_ALIASES.get(m.group(1)[:3], m.group(1)[:3]) in MONTHS:
        mo = MONTHS[MONTH_ALIASES.get(m.group(1)[:3], m.group(1)[:3])]
        if m.group(2):
            return date(int(m.group(2)), mo, 1), MONTH_ONLY
        got = _year_for(mo, 1, today, prefer)
        return got, MONTH_ONLY
    return None, f"could not read '{t}' as a date"


def recurring_day(s):
    """'5th of each month', 'by the 5th monthly', 'every Monday' -> ('month', 5) or ('week', 0)."""
    low = str(s or "").lower()
    m = (re.search(r"(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(?:each|every|the)\s+month", low)
         or re.search(r"(?:monthly|each month|every month)\D{0,12}(\d{1,2})(?:st|nd|rd|th)", low)
         or re.search(r"(\d{1,2})(?:st|nd|rd|th)\s*(?:,\s*)?(?:monthly|each month|every month)", low))
    if m:
        return "month", int(m.group(1))
    for i, w in enumerate(WEEKDAYS):
        if re.search(rf"(every|each|by)\s+{w}", low):
            return "week", i
    if re.search(r"\bweekly\b", low):
        return "week", 0
    return None


def long_date(d):
    """Written the way the founder writes dates: '3 September 2026', or 'September 3, 2026' when month comes first."""
    if not d:
        return ""
    return f"{d.strftime('%B')} {d.day}, {d.year}" if ORDER == "mdy" else f"{d.day} {d.strftime('%B')} {d.year}"


def short_date(d, month_only=False):
    """'3 Sep' or 'Sep 3' in the founder's order; 'Sep 2026' when they gave only the month (never a made-up 1st)."""
    if not d:
        return ""
    if month_only:
        return f"{d.strftime('%b')}\u00a0{d.year}"
    return f"{d.strftime('%b')}\u00a0{d.day}" if ORDER == "mdy" else f"{d.day}\u00a0{d.strftime('%b')}"


def month_text(d):
    """A month-only date as memory keeps it, so it reads back as month only: 'Sep 2026'."""
    return f"{d.strftime('%b')} {d.year}" if d else ""
