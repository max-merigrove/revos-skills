#!/usr/bin/env python3
"""Founder-typed numbers, money, durations and locale defaults, for any country.

Reference module for Merigrove standalone skills. Skills are independent, so each
skill copies this file into its own scripts/ folder (unchanged where possible) and
imports it. Standard library only. Every reader returns a value and notes; anything
it cannot read with confidence raises Ambiguous or Unreadable with a plain message
for Claude to put to the founder as one question.

Covers:
  numbers   1,234.56  1.234,56  1 234,56  1'234.56  12.500 (asks)  18,00,000 (Indian)
            k  m  mn  million  bn  billion  grand  lakh  lac  crore  cr  万  萬  億  亿  千
            (1,250.00)  -1,250  1.5k  ₹2.4 lakh  S$1.2k  "about 40"  "40ish"  "~40"
  money     strips symbols and codes ($ US$ S$ A$ C$ NZ$ HK$ £ € ¥ ₹ ₱ ₦ ₩ ₪ ₺ ฿ R RM zł kr Kč
            AED SAR CHF and any 3-letter ISO code) and returns the currency it saw
  percent   "1,4%"  "12.5 %"  "12 percent"  bare "1" is 1 (never 100)
  duration  7.5hr  7,5 Std.  1h30  1:30  90 mins  90 minutos  half a day  2 days  2 Tage
            3 to 4 days (midpoint, flagged)  "an hour or two" (midpoint, flagged)
  locale    paper size, date order and clock from a country code, never from spelling
"""
import re
import unicodedata


class Ambiguous(ValueError):
    """The text can be read two ways; ask the founder which."""


class Unreadable(ValueError):
    """The text could not be read as a number; ask the founder to restate it."""


# ---------------------------------------------------------------- locale defaults
LETTER_COUNTRIES = {"US", "CA", "MX", "PH", "CL", "CO", "VE", "CR", "GT", "DO", "PA", "PR", "SV", "HN", "NI", "BZ"}
MDY_COUNTRIES = {"US", "PR", "PH", "FM", "MH", "PW"}
YMD_COUNTRIES = {"CN", "JP", "KR", "TW", "HU", "LT", "MN", "IR", "KP"}
CLOCK_12H = {"US", "CA", "AU", "NZ", "PH", "IN", "PK", "BD", "EG", "SA", "CO", "MX", "IE", "MY"}


def locale_defaults(country):
    """Paper, date order and clock for an ISO country code. Unknown country: A4, DMY, 24h, flagged."""
    c = (country or "").strip().upper()
    if not c:
        return {"paper": "A4", "date_order": "DMY", "clock": "24h", "assumed": True}
    return {
        "paper": "Letter" if c in LETTER_COUNTRIES else "A4",
        "date_order": "MDY" if c in MDY_COUNTRIES else "YMD" if c in YMD_COUNTRIES else "DMY",
        "clock": "12h" if c in CLOCK_12H else "24h",
        "assumed": False,
    }


# ---------------------------------------------------------------- currency
_SYMBOLS = [  # longest first
    ("US$", "USD"), ("S$", "SGD"), ("A$", "AUD"), ("AU$", "AUD"), ("C$", "CAD"), ("CA$", "CAD"),
    ("NZ$", "NZD"), ("HK$", "HKD"), ("R$", "BRL"), ("RM", "MYR"), ("zł", "PLN"), ("Kč", "CZK"),
    ("£", "GBP"), ("€", "EUR"), ("₹", "INR"), ("₱", "PHP"), ("₦", "NGN"), ("₩", "KRW"), ("₪", "ILS"),
    ("₺", "TRY"), ("฿", "THB"), ("₫", "VND"), ("₴", "UAH"), ("₽", "RUB"), ("¥", "JPY_OR_CNY"),
    ("Rs.", "INR_OR_PKR_OR_LKR"), ("Rs", "INR_OR_PKR_OR_LKR"), ("kr", "SEK_OR_NOK_OR_DKK"), ("$", "DOLLAR"),
]
_WORDS = {
    "dollars": "DOLLAR", "dollar": "DOLLAR", "bucks": "DOLLAR", "pounds": "GBP", "quid": "GBP",
    "euros": "EUR", "euro": "EUR", "rupees": "INR_OR_PKR_OR_LKR", "rupee": "INR_OR_PKR_OR_LKR",
    "pesos": "PESO", "peso": "PESO", "yen": "JPY", "yuan": "CNY", "rmb": "CNY", "rand": "ZAR",
    "ringgit": "MYR", "baht": "THB", "dirhams": "AED", "dirham": "AED", "riyal": "SAR", "riyals": "SAR",
    "naira": "NGN", "shillings": "SHILLING", "francs": "CHF_OR_OTHER", "won": "KRW", "dong": "VND",
    "zloty": "PLN", "krona": "SEK", "kronor": "SEK", "krone": "NOK_OR_DKK", "kroner": "NOK_OR_DKK",
}
_ISO = re.compile(r"\b(USD|GBP|EUR|INR|SGD|AUD|CAD|NZD|HKD|JPY|CNY|MYR|PHP|ZAR|AED|SAR|CHF|SEK|NOK|DKK|PLN|"
                  r"CZK|BRL|MXN|NGN|KES|KRW|THB|IDR|VND|PKR|LKR|BDT|EGP|TRY|ILS|QAR|KWD|TWD|CLP|COP|ARS|PEN)\b")


def find_currency(text):
    """Return the currency code (or an *_OR_* family to ask about) seen in text, else None."""
    t = text or ""
    m = _ISO.search(t.upper())
    if m:
        return m.group(1)
    for sym, code in _SYMBOLS:
        if sym == "R":
            continue
        if sym in ("Rs", "Rs.", "kr", "RM"):
            if re.search(r"(?<![A-Za-z])" + re.escape(sym) + r"(?=\s?[\d.,])", t):
                return code
            continue
        if sym in t:
            return code
    if re.search(r"(?<![A-Za-z])R\s?\d", t):
        return "ZAR"
    low = t.lower()
    for w, code in _WORDS.items():
        if re.search(r"\b" + re.escape(w) + r"\b", low):
            return code
    return None


def _strip_currency(t):
    t = _ISO.sub(" ", t)
    t = re.sub(r"\b(?:USD|GBP|EUR)\b", " ", t, flags=re.I)
    for sym, _ in _SYMBOLS:
        t = t.replace(sym, " ")
    t = re.sub(r"(?<![A-Za-z])R(?=\s?\d)", " ", t)
    for w in _WORDS:
        t = re.sub(r"\b" + re.escape(w) + r"\b", " ", t, flags=re.I)
    return t


# ---------------------------------------------------------------- numbers
_MULT = [
    (r"crores?|cr\b", 1e7), (r"lakhs?|lacs?\b|lac\b", 1e5), (r"billions?|bn\b", 1e9), (r"millions?|mn\b|mio\b|mil\b", 1e6),
    (r"thousand|grand|tsd\.?|mil\s?euros", 1e3), (r"k\b", 1e3), (r"m\b", 1e6), (r"b\b", 1e9),
]
_CJK = {"万": 1e4, "萬": 1e4, "億": 1e8, "亿": 1e8, "千": 1e3, "百": 1e2}
_WORDNUM = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
            "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20, "thirty": 30,
            "forty": 40, "fifty": 50, "sixty": 60, "a hundred": 100, "a dozen": 12, "dozen": 12,
            "half": 0.5, "a half": 0.5, "a quarter": 0.25, "quarter": 0.25, "a couple": 2, "couple": 2, "a few": 3}


def detect_decimal_style(samples):
    """'dot', 'comma' or None, from a list of strings the founder typed."""
    dot = comma = 0
    for s in samples or []:
        for m in re.finditer(r"\d[\d.,'   ]*\d", str(s)):
            n = m.group(0)
            if re.search(r",\d{1,2}$", n) or re.search(r"\.\d{3},", n) or re.search(r"\.\d{3}\.\d{3}", n):
                comma += 1
            elif re.search(r"\.\d{1,2}$", n) or re.search(r",\d{3}\.", n) or re.search(r",\d{3},\d{3}", n):
                dot += 1
    if dot and not comma:
        return "dot"
    if comma and not dot:
        return "comma"
    return None


def _core_number(s, decimal):
    s = s.strip().replace(" ", " ").replace(" ", " ").replace("'", "").replace("’", "")
    if not re.fullmatch(r"[\d., ]+", s):
        raise Unreadable(f"'{s}' is not a number")
    s = s.strip()
    if " " in s:  # space grouping: 1 234,56 or 1 234.56
        if re.fullmatch(r"\d{1,3}( \d{3})+([.,]\d+)?", s):
            s = s.replace(" ", "")
        else:
            raise Unreadable(f"'{s}' has spaces in an unexpected place")
    has_dot, has_comma = "." in s, "," in s
    if has_dot and has_comma:
        if s.rfind(",") > s.rfind("."):
            return float(s.replace(".", "").replace(",", "."))
        return float(s.replace(",", ""))
    if has_comma:
        if re.fullmatch(r"\d{1,3}(,\d{2})+,\d{3}", s):  # Indian 18,00,000
            return float(s.replace(",", ""))
        if re.fullmatch(r"\d{1,3}(,\d{3})+", s):
            if decimal == "comma" and s.count(",") == 1:
                raise Ambiguous(f"'{s}': thousands or decimals? (you usually write a comma for decimals)")
            if decimal == "comma":
                raise Ambiguous(f"'{s}' looks like thousands, but you usually write a comma for decimals")
            return float(s.replace(",", ""))
        if decimal == "dot" and re.fullmatch(r"\d+,\d{1,2}", s):
            raise Ambiguous(f"'{s}': is the comma a decimal point?")
        return float(s.replace(",", "."))
    if has_dot:
        if re.fullmatch(r"\d{1,3}(\.\d{3}){2,}", s):
            return float(s.replace(".", ""))
        if re.fullmatch(r"\d{1,3}\.\d{3}", s):
            if decimal == "comma":
                return float(s.replace(".", ""))
            if decimal == "dot":
                return float(s)
            raise Ambiguous(f"'{s}': is that {s.replace('.', ',')} (thousands) or {s} (a decimal)?")
        return float(s)
    return float(s)


def parse_number(text, decimal=None, allow_words=True):
    """Read one founder-typed number. Returns (value, notes). decimal: 'dot', 'comma' or None."""
    notes = []
    if text is None:
        raise Unreadable("no value given")
    if isinstance(text, (int, float)):
        return float(text), notes
    t = unicodedata.normalize("NFKC", str(text)).strip()
    t = re.sub(r"[\u2212\u2013\u2014]", "-", t)
    t = _strip_currency(t)
    low = t.lower()
    if re.search(r"\b(about|around|roughly|approx\.?|circa|ca\.)\b|~|-?ish\b", low):
        notes.append("approximate")
        low = re.sub(r"\b(about|around|roughly|approx\.?|circa|ca\.)\b|~|-?ish\b", " ", low)
    neg = bool(re.match(r"^\s*\(.*\)\s*$", low)) or bool(re.match(r"^\s*-", low))
    low = low.strip().strip("()").lstrip("-").strip()
    low = re.sub(r"\b(per|a|an|/)\s*(month|mo|year|yr|week|wk|hour|hr)\b.*$", "", low).strip()
    low = re.sub(r"(?:\b|(?<=\d))(pm|pa|p\.a\.|p/m|p/a|/mo|/yr|/month|/year|incl\.?|excl\.?|net|gross|\+\s?vat|\+\s?gst)(?![a-z])", " ", low).strip()
    for ch, mult in _CJK.items():
        if ch in low:
            m = re.fullmatch(r"\s*([\d.,]+)\s*" + ch + r"\s*(?:円|元)?\s*", low)
            if not m:
                raise Unreadable(f"'{text}': could not read the {ch} amount")
            return (-1 if neg else 1) * _core_number(m.group(1), decimal) * mult, notes + [f"x{int(mult)} ({ch})"]
    if allow_words:
        for w in sorted(_WORDNUM, key=len, reverse=True):
            if re.fullmatch(r"\s*" + re.escape(w) + r"\s*", low):
                return float(_WORDNUM[w]), notes + ["from words"]
    if re.search(r"\d\s*(?:-|to|or|\u2013)\s*\d", low) and not re.fullmatch(r"[\d., ]+", low):
        raise Ambiguous(f"'{text}' is a range; give one figure or say to use the middle")
    mult = 1.0
    for pat, m in _MULT:
        mm = re.search(r"(?<=[\d\s.,])\s*(?:" + pat + ")", low)
        if mm:
            mult = m
            notes.append(f"x{int(m)} ({mm.group(0).strip()})")
            low = low[:mm.start()] + low[mm.end():]
            break
    low = low.strip()
    if not re.fullmatch(r"[\d.,' ]+", low or "x"):
        raise Unreadable(f"'{text}' could not be read as one number")
    return (-1 if neg else 1) * _core_number(low, decimal) * mult, notes


def parse_money(text, decimal=None):
    """Returns (amount, currency_or_None, notes)."""
    cur = find_currency(str(text))
    val, notes = parse_number(text, decimal)
    return val, cur, notes


def parse_percent(text, decimal=None):
    """'1,4%' -> 1.4; '12.5 percent' -> 12.5; bare '1' -> 1.0 (one per cent, never 100)."""
    t = re.sub(r"\s*(%|percent|per cent|pct|prozent|por ciento|pour cent)\s*$", "", str(text).strip(), flags=re.I)
    val, notes = parse_number(t, decimal, allow_words=False)
    return val, notes


# ---------------------------------------------------------------- durations
_UNIT_H = [  # (pattern, hours per unit or 'DAY' or 'WEEK')
    (r"minutos|minuten|minutes|minute|mins?\b|min\.?|m\b(?!o)", 1 / 60),
    (r"hours?|hrs?\b|hr\.?|h\b|std\.?|stunden?|horas?|heures?|ore\b|uur\b|timer?\b|jam\b|giờ|時間|小时|小時", 1.0),
    (r"days?\b|tage?n?\b|d[ií]as?\b|jours?\b|giorni\b|dagen?\b|hari\b|日", "DAY"),
    (r"weeks?\b|wks?\b|wochen?\b|semanas?\b|semaines?\b", "WEEK"),
]
_FRACTIONS = {"half an hour": 0.5, "half hour": 0.5, "an hour": 1.0, "a quarter of an hour": 0.25,
              "an hour and a half": 1.5, "hour and a half": 1.5, "a day": "DAY1", "half a day": "DAY0.5",
              "half day": "DAY0.5", "a week": "WEEK1"}


def parse_hours(text, day_hours=8.0, week_days=5, decimal=None):
    """Read a duration in hours. Returns (hours, notes). Ranges give the midpoint, flagged."""
    notes = []
    t = unicodedata.normalize("NFKC", str(text)).strip().lower()
    t = re.sub(r"[\u2013\u2014]", "-", t)
    t = re.sub(r"\b(about|around|roughly|approx\.?|ish|maybe)\b|~|-ish", " ", t).strip()
    for phrase, v in sorted(_FRACTIONS.items(), key=lambda kv: -len(kv[0])):
        if re.fullmatch(re.escape(phrase), t):
            if isinstance(v, str) and v.startswith("DAY"):
                return float(v[3:]) * day_hours, [f"day = {day_hours:g} hours"]
            if isinstance(v, str) and v.startswith("WEEK"):
                return float(v[4:]) * day_hours * week_days, [f"week = {week_days} x {day_hours:g} hours"]
            return float(v), notes
    m = re.fullmatch(r"(?:an?|one)\s+(hour|day|week)\s+or\s+two", t)
    if m:
        h, n2 = parse_hours("1.5 " + m.group(1), day_hours, week_days)
        return h, n2 + ["'or two' read as 1.5, midpoint used"]
    m = re.fullmatch(r"a\s+(couple|few)\s+(?:of\s+)?(hours?|days?)", t)
    if m:
        q = 2 if m.group(1) == "couple" else 3
        h, n2 = parse_hours(f"{q} {m.group(2)}", day_hours, week_days)
        return h, n2 + [f"'a {m.group(1)}' read as {q}"]
    m = re.fullmatch(r"(\d+)\s*:\s*(\d{2})", t)
    if m:
        return int(m.group(1)) + int(m.group(2)) / 60, notes
    m = re.fullmatch(r"(\d+(?:[.,]\d+)?)\s*h\s*(\d{1,2})\s*(?:m|min|mins)?", t)
    if m:
        return parse_number(m.group(1), decimal)[0] + int(m.group(2)) / 60, notes
    m = re.fullmatch(r"(\d+(?:[.,]\d+)?)\s*(?:hrs?|hours?|h)\s*(?:x|×|\*)\s*(\d+(?:[.,]\d+)?)\s*(days?|weeks?)?", t)
    if m:
        a, b = parse_number(m.group(1), decimal)[0], parse_number(m.group(2), decimal)[0]
        return a * b, [f"{a:g} hours x {b:g}"]
    m = re.fullmatch(r"(\d+(?:[.,]\d+)?)\s*(?:x|×|\*)\s*(\d+(?:[.,]\d+)?)\s*(.*)", t)
    if m:
        a = parse_number(m.group(1), decimal)[0]
        h, n2 = parse_hours(m.group(2) + " " + (m.group(3) or "h"), day_hours, week_days, decimal)
        return a * h, n2 + [f"{a:g} x"]
    rng = re.fullmatch(r"(?:an?\s+)?(\S+)\s*(?:-|to|or|bis|a)\s*(\S+)\s*(.*)", t)
    if rng and re.search(r"\d|an? |one|two|three|four|five", t):
        unit = rng.group(3) or ""
        try:
            lo, _ = parse_hours(f"{rng.group(1)} {unit}".strip(), day_hours, week_days, decimal)
            hi, _ = parse_hours(f"{rng.group(2)} {unit}".strip(), day_hours, week_days, decimal)
            return (lo + hi) / 2, [f"range {lo:g} to {hi:g} hours, midpoint used"]
        except (Ambiguous, Unreadable):
            pass
    m = re.fullmatch(r"(an?|one|two|three|four|five|six|half an?|[\d.,]+)\s*(.*)", t)
    if not m:
        raise Unreadable(f"'{text}' could not be read as a length of time")
    qty_s, unit_s = m.group(1), m.group(2).strip().rstrip(".")
    qty = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
           "half a": 0.5, "half an": 0.5}.get(qty_s)
    if qty is None:
        qty = parse_number(qty_s, decimal, allow_words=False)[0]
    if not unit_s:
        notes.append("no unit given, read as hours")
        return qty, notes
    for pat, per in _UNIT_H:
        if re.fullmatch(r"(?:" + pat + r")\.?", unit_s):
            if per == "DAY":
                return qty * day_hours, notes + [f"day = {day_hours:g} hours"]
            if per == "WEEK":
                return qty * day_hours * week_days, notes + [f"week = {week_days} x {day_hours:g} hours"]
            return qty * per, notes
    raise Unreadable(f"'{text}': unit '{unit_s}' not recognised; give the time in hours")


# ---------------------------------------------------------------- weekday ranges
_DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def count_weekdays(text):
    """'mon to fri' -> 5, 'mon-sat' -> 6, 'sun-thu' -> 5, 'weekdays' -> 5, 'mon, wed, fri' -> 3."""
    t = str(text).lower()
    if re.search(r"\bweekdays?\b|every weekday", t):
        return 5
    m = re.search(r"\b(mon|tue|wed|thu|fri|sat|sun)\w*\s*(?:-|to|through|thru|till|until)\s*(mon|tue|wed|thu|fri|sat|sun)\w*", t)
    if m:
        a, b = _DAYS.index(m.group(1)), _DAYS.index(m.group(2))
        return (b - a) % 7 + 1
    found = {d for d in _DAYS if re.search(r"\b" + d, t)}
    if found:
        return len(found)
    raise Unreadable(f"'{text}': which days?")


if __name__ == "__main__":
    import sys
    for arg in sys.argv[1:]:
        try:
            print(arg, "->", parse_number(arg))
        except ValueError as e:
            print(arg, "->", type(e).__name__, e)
