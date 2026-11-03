#!/usr/bin/env python3
"""Shared helpers for Get Quoted by AI. Standard library only, no network calls.

Every script reads its inputs through these helpers so a bad input ends in one plain
"STOP: <what to do>" line and exit code 2, never a traceback.
"""
import json
import re
import sys
import unicodedata
from datetime import date, datetime, timedelta

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]
MONTH_WORDS = {m.lower(): i + 1 for i, m in enumerate(MONTHS)}
MONTH_WORDS.update({m[:3].lower(): i + 1 for i, m in enumerate(MONTHS)})
MONTH_WORDS.update({"sept": 9, "januari": 1, "februari": 2, "maart": 3, "mei": 5, "juni": 6, "juli": 7,
                    "augustus": 8, "oktober": 10, "januar": 1, "februar": 2, "märz": 3, "mai": 5, "dezember": 12,
                    "janvier": 1, "février": 2, "mars": 3, "avril": 4, "juin": 6, "juillet": 7, "août": 8,
                    "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12, "enero": 1, "febrero": 2,
                    "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7, "agosto": 8, "septiembre": 9,
                    "octubre": 10, "noviembre": 11, "diciembre": 12})
MONTH_WORDS.update({"okt": 10, "dez": 12, "mär": 3, "mrz": 3, "mrt": 3, "juil": 7, "févr": 2, "déc": 12, "ene": 1, "abr": 4,
                    "ago": 8, "dic": 12, "janv": 1, "avr": 4, "sep": 9, "dezembro": 12, "novembro": 11, "outubro": 10,
                    "setembro": 9, "janeiro": 1, "fevereiro": 2, "março": 3, "maio": 5, "junho": 6, "julho": 7, "gennaio": 1,
                    "febbraio": 2, "aprile": 4, "maggio": 5, "giugno": 6, "luglio": 7, "settembre": 9, "ottobre": 10,
                    "dicembre": 12, "styczeń": 1, "listopad": 11, "listopada": 11, "grudzień": 12, "grudnia": 12})

# Money as founders write it, symbol before or after the number. No \b after a symbol: "14.500 €" is a price.
CUR_SYMBOLS = r"(?:US\$|A\$|AU\$|C\$|CA\$|NZ\$|S\$|HK\$|R\$|[$€£¥₹₩₪₫₱₦₺₴₽฿]|Rs\.?(?=\s?\d)|RM(?=\s?\d))"
CUR_AFTER = r"(?:€|£|₹|¥|₺|₽|₴|₩|₪|₫|₱|₦|฿|zł|Kč|kr\.?|Ft|lei|Lei|CHF|Fr\.)"
CUR_CODES = (r"(?:AUD|USD|CAD|AED|EUR|GBP|INR|SGD|NZD|CHF|SAR|ZAR|HKD|JPY|CNY|PLN|SEK|NOK|DKK|CZK|HUF|RON|TRY|BRL|MXN|KRW|THB|"
             r"MYR|IDR|PHP|ILS|QAR|KES|NGN|PKR|LKR|BDT|EGP|VND|TWD|CLP|COP|ARS|PEN|KWD)")
MONEY_NUM = r"\d[\d.,'\u00a0\u202f ]*\d|\d"
MONEY_RE = re.compile(
    rf"(?P<c1>{CUR_SYMBOLS}|(?<![A-Za-z]){CUR_CODES}(?![A-Za-z]))\s?(?P<n1>{MONEY_NUM})(?:,-|,\u2013)?"
    rf"|(?P<n2>{MONEY_NUM})(?:,-)?\s?(?P<c2>{CUR_AFTER}(?![^\W\d_])|(?<![A-Za-z]){CUR_CODES}(?![A-Za-z]))")

# Dates, so a "Last updated" line in any founder's style is never read as an unsourced figure.
_DATE_PATS = [
    r"\b(?:19|20)\d\d-\d{1,2}-\d{1,2}\b",
    r"\b\d{1,2}[./-]\d{1,2}[./-](?:19|20)?\d\d\b",
    r"\b(?:19|20)\d\d/\d{1,2}/\d{1,2}\b",
    r"\b\d{1,2}(?:st|nd|rd|th|er|e|\.)?\s+(?:de\s+)?(?P<m1>[^\W\d_]{3,12})\.?,?\s+(?:de\s+)?(?:19|20)\d\d\b",
    r"\b(?P<m2>[^\W\d_]{3,12})\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+(?:19|20)\d\d\b",
    r"\b(?P<m3>[^\W\d_]{3,12})\s+(?:19|20)\d\d\b",
]
DATE_RES = [re.compile(p, re.I) for p in _DATE_PATS]


def date_spans(text):
    """Character spans of every date in text: ISO, 02.11.2026, 02/11/2026, 2. November 2026, 2nd Nov 2026,
    November 2, 2026, 2 de noviembre de 2026, November 2026. Month words are checked against MONTH_WORDS."""
    spans = []
    for rx in DATE_RES:
        for m in rx.finditer(text or ""):
            mon = next((m.group(k) for k in ("m1", "m2", "m3") if k in rx.groupindex and m.group(k)), None)
            if mon is not None and mon.lower().strip(".") not in MONTH_WORDS:
                continue
            spans.append(m.span())
    return spans


def fold(text):
    """For matching words across spellings: lower case, ä to ae, ö to oe, ü to ue, ß to ss, other accents dropped."""
    t = str(text or "").lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss"), ("&", " and ")):
        t = t.replace(a, b)
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", t)).strip()


def same_word(a, b):
    """Two folded words match when equal, or when both are 5+ letters and share their first five (photo, photos, photography)."""
    if a == b:
        return True
    return len(a) >= 5 and len(b) >= 5 and a[:5] == b[:5]


# English spellings the kit and workbook print, by the founder's English (settings "english").
US_SPELLING = {"favourable": "favorable", "colour": "color", "colours": "colors", "organise": "organize", "recognise": "recognize",
               "behaviour": "behavior", "analyse": "analyze", "catalogue": "catalog", "optimise": "optimize", "prioritise": "prioritize"}


def is_us_english(english):
    """'American', 'en-US', 'US English', "American, but 'modelling'" all read as American English."""
    e = str(english or "").strip().lower().replace("_", "-")
    return bool(re.match(r"^(en-us\b|us\b|u\.s\.|american)", e))


def spell(text, english):
    """The kit's fixed English in the founder's English: British, Australian, Indian and most others keep 'favourable';
    American English gets 'favorable'. Words in the founder's own facts are never touched (only fixed text goes through this)."""
    if not is_us_english(english):
        return text
    out = str(text)
    for gb, us in US_SPELLING.items():
        out = re.sub(rf"\b{gb}\b", us, out)
        out = re.sub(rf"\b{gb.capitalize()}\b", us.capitalize(), out)
    return out


def stop(msg, code=2):
    print(f"STOP: {msg}")
    sys.exit(code)


def read_text(path, what="the file"):
    try:
        with open(path, encoding="utf-8-sig", errors="strict") as fh:
            return fh.read()
    except FileNotFoundError:
        stop(f"{what} was not found at {path}. Save it there first, or check the path.")
    except UnicodeDecodeError:
        try:
            with open(path, encoding="cp1252") as fh:
                return fh.read()
        except Exception:  # noqa: BLE001
            stop(f"{what} at {path} is not readable text. Save it as plain text (UTF-8) and try again.")
    except IsADirectoryError:
        stop(f"{path} is a folder, not {what}.")


def load_json(path, what="the JSON file"):
    raw = read_text(path, what)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        stop(f"{what} at {path} is not valid JSON (line {e.lineno}, column {e.colno}: {e.msg}). Fix it and run again.")


def ensure_parent(path):
    """Create the folder a file is about to be written into, so a first run never fails on a missing folder."""
    import os
    d = os.path.dirname(os.path.abspath(path))
    os.makedirs(d, exist_ok=True)
    return path


def save_json(path, data):
    ensure_parent(path)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def slug(text, maxlen=40):
    t = str(text)
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("Ä", "Ae"), ("Ö", "Oe"), ("Ü", "Ue"), ("ß", "ss"), ("&", " and ")):
        t = t.replace(a, b)
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-zA-Z0-9]+", "-", t).strip("-").lower()
    return (t[:maxlen].rstrip("-")) or "business"


def norm(text):
    """Lower case, accents kept, punctuation and repeated spaces removed: for tracing quotes."""
    t = unicodedata.normalize("NFKC", str(text)).lower()
    t = re.sub(r"[‘’“”'\"`]", "", t)
    t = re.sub(r"[^\w\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def fmt_date(d, order="DMY", months=None):
    """Dates written out, so nobody misreads 06/10: '6 October 2026', 'October 6, 2026' or '2026-10-06'.
    months: the twelve month names in the founder's language (default English)."""
    if not d:
        return ""
    names = months or MONTHS
    if order == "MDY":
        return f"{names[d.month - 1]} {d.day}, {d.year}"
    if order == "YMD":
        return d.isoformat()
    return f"{d.day} {names[d.month - 1]} {d.year}"


def parse_date(text, order="DMY", today=None):
    """Read a date as founders type it. Returns a date or None. ISO first, then day/month by order."""
    if text is None or text == "":
        return None
    if isinstance(text, datetime):
        return text.date()
    if isinstance(text, date):
        return text
    if isinstance(text, (int, float)) and 20000 < float(text) < 80000:
        return date(1899, 12, 30) + timedelta(days=int(text))
    t = str(text).strip().lower().replace(",", " ")
    today = today or date.today()
    if t in ("today", "vandaag", "heute"):
        return today
    if t in ("yesterday", "gisteren", "gestern"):
        return today - timedelta(days=1)
    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})(?:[t ].*)?", t)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    m = re.fullmatch(r"(\d{1,2})[./-](\d{1,2})(?:[./-](\d{2,4}))?", t)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        y = int(m.group(3)) if m.group(3) else today.year
        if y < 100:
            y += 2000
        d_, mo = (b, a) if order == "MDY" else (a, b)
        if mo > 12 and d_ <= 12:
            d_, mo = mo, d_
        try:
            return date(y, mo, d_)
        except ValueError:
            return None
    words = t.split()
    nums = [w for w in words if re.fullmatch(r"\d{1,4}(st|nd|rd|th)?", w)]
    mon = next((MONTH_WORDS[w.strip(".")] for w in words if w.strip(".") in MONTH_WORDS), None)
    if mon and nums:
        vals = [int(re.sub(r"\D", "", n)) for n in nums]
        day = next((v for v in vals if v <= 31), None)
        year = next((v for v in vals if v > 31), today.year)
        if day:
            try:
                return date(year, mon, day)
            except ValueError:
                return None
    return None


def domain_of(url):
    u = str(url or "").strip().lower()
    u = re.sub(r"^[a-z]+://", "", u)
    u = u.split("/")[0].split("?")[0].split("#")[0]
    u = re.sub(r":\d+$", "", u)
    return u[4:] if u.startswith("www.") else u


def words(text):
    return re.findall(r"[\w][\w'’-]*", str(text), re.UNICODE)


def strip_html(html):
    import html as _h
    t = re.sub(r"(?is)<(script|style|noscript|template)[^>]*>.*?</\1>", " ", html)
    t = re.sub(r"(?s)<!--.*?-->", " ", t)
    t = re.sub(r"(?i)<br\s*/?>|</(p|h[1-6]|li|div|tr|section|article)>", "\n", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = _h.unescape(t)
    t = re.sub(r"[ \t\r\f\v]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n", t).strip()
