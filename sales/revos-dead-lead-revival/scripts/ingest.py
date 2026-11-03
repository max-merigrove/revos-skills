#!/usr/bin/env python3
"""Read an old-leads list in whatever shape the founder has it, and turn it into one clean contact list.

Reads CSV and TSV (any delimiter, UTF-8 or Windows-1252), XLSX (no library needed), or a JSON list the
model wrote from a pasted list ({"rows": [{"name": ..., "notes": ..., "raw": "the line as pasted"}]}).
Maps headers by synonym in several languages (or --map field=Column), reads the date order from the data,
reads money in the founder's number style, marks month-only and seasonal dates as approximate, merges
duplicates (email, phone, or name plus company), and flags role addresses, bad addresses, missing contact
detail, dates in the future, bulk import date stamps and notes that carry instructions.

Usage (normally called through revival.py):
  python3 scripts/ingest.py <list file> [--date-order dmy|mdy|ymd] [--decimal dot|comma] [--today YYYY-MM-DD]
         [--country GB] [--map field=Column ...] [--json-out contacts.json]
Exit 0 on success. Exit 2 with a STOP: line (and an ASK: line when the founder must answer) on anything
that cannot be read safely. Standard library only. No network calls.
"""
import argparse
import csv
import io
import json
import re
import sys
import unicodedata
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import locale_numbers as ln  # noqa: E402
import office  # noqa: E402

MAX_ROWS = 2000


from common import Stop, fold  # noqa: E402


# ---------------------------------------------------------------- headers

FIELDS = {
    "ref": r"^ref$",
    "first_name": r"^(first ?name|given name|vorname|prenom|nombre de pila|fname)$",
    "last_name": r"^(last ?name|surname|family name|nachname|nom de famille|apellidos?|lname)$",
    "name": r"^(name|full ?name|contact( name)?|contact person|person|lead( name)?|client( name)?|customer( name)?|"
            r"ansprechpartner|kontakt|nom|nombre|nome|naam|who)$",
    "company": r"^(company|company name|organi[sz]ation|org|business|account( name)?|firma|unternehmen|societe|"
               r"entreprise|empresa|azienda|bedrijf)$",
    "email": r"(e-?mail|mail address|courriel|correo)",
    "phone": r"(phone|mobile|cell|tel|telefon|handy|portable|movil|whatsapp|sms number)",
    "last_contact": r"(last (contact|activity|touch|email|mail|invoice|meeting|call|reply|seen)|date of last|"
                    r"close ?date|closed (on|date)|lost (on|date)|date lost|letzter kontakt|dernier contact|"
                    r"ultimo contacto|last ?mail|^date$|^datum$|^when$|last invoice date|invoice date)",
    "stage": r"^(deal ?stage|stage|pipeline stage|status|lead status|phase|etape|estado|stadium|lifecycle stage)$",
    "reason": r"(lost reason|reason( lost)?|closed lost reason|why lost|loss reason|verlustgrund|grund|raison|motivo)",
    "notes": r"(notes?|notiz(en)?|comments?|remarks?|description|details|kommentar|commentaires?|notas?|memo|history)",
    "value": r"(amount|deal value|value|total invoiced|invoiced|revenue|total|angebot|betrag|montant|importe|wert|budget)",
    "source": r"(^source$|lead source|original source|how (did|they)|came from|channel source|origin|quelle|herkunft|"
              r"provenance|origen|list)",
    "channel": r"^(channel|preferred channel|contact method|kanal|canal)$",
    "deal": r"^(deal ?name|deal|opportunity( name)?|project|projekt|projet|proyecto|service|package)$",
    "invoices": r"(number of invoices|invoices count|# invoices|invoice count)",
    "status": r"^status$",
    "reply_notes": r"^reply notes$",
}
TRACKER_LABELS = (("ref", "ref"), ("name", "name"), ("company", "company"), ("email", "email"), ("phone", "phone"),
                  ("group", "group"), ("why", "why"), ("came_from", "came onto the list"),
                  ("last_contact", "last real contact"), ("channel", "channel"), ("next_touch", "next touch"),
                  ("next_date", "next touch date"), ("touch_dates", "touch dates"), ("personal", "personal field"),
                  ("tier", "tier"), ("status", "status"), ("reply_notes", "reply notes"), ("stop_date", "stop date"),
                  ("cooldown_until", "cooldown until"), ("notes", "their notes"), ("held_code", "reason code"),
                  ("revisit", "revisit on"), ("sheet", "_sheet"), ("value", "value"), ("held_reason_in", "reason"),
                  ("handle", "dm handle"))


def map_headers(heads, given):
    """Return {field: column index}. given: {field: header text} from --map."""
    out = {}
    fh = [fold(h) for h in heads]
    for field, col in given.items():
        if fold(col) not in fh:
            raise Stop(f"there is no column called '{col}'. The columns are: {', '.join(str(h) for h in heads)}")
        out[field] = fh.index(fold(col))
    order = ["ref", "first_name", "last_name", "email", "phone", "invoices", "reason", "last_contact", "deal",
             "company", "stage", "notes", "value", "source", "channel", "reply_notes", "name"]
    if "name" not in out and "first_name" not in out:
        for pref in (r"^(full ?name|contact ?name|contact person|person|ansprechpartner)$", r"^name$"):
            hit = [i for i, h in enumerate(fh) if re.search(pref, h) and i not in out.values()]
            if hit:
                out["name"] = hit[0]
                if "company" not in out:
                    bare = [i for i, h in enumerate(fh) if h in ("contact", "account", "client", "customer")
                            and i not in out.values()]
                    if bare:
                        out["company"] = bare[0]
                break
    for field in order:
        if field in out:
            continue
        exact = [i for i, h in enumerate(fh) if h.replace(" ", "_") == field and i not in out.values()]
        if exact:
            out[field] = exact[0]
            continue
        for i, h in enumerate(fh):
            if i in out.values() or not h:
                continue
            if re.search(FIELDS[field], h):
                out[field] = i
                break
    return out


# ---------------------------------------------------------------- dates

MONTHS = {
    1: "jan january januar janvier enero gennaio januari janeiro jän jaen janv ene gen",
    2: "feb february februar fevrier febrero febbraio februari fevereiro fev fevr febr",
    3: "mar march marz maerz mars marzo maart marco mrz mär",
    4: "apr april avril abril aprile",
    5: "may mai mayo maggio mei maio",
    6: "jun june juni juin junio giugno junho",
    7: "jul july juli juillet julio luglio julho juil",
    8: "aug august aout agosto augustus ago",
    9: "sep sept september septembre septiembre settembre setembro set",
    10: "oct october oktober octobre octubre ottobre outubro okt ott out",
    11: "nov november novembre noviembre novembro",
    12: "dec december dezember decembre diciembre dicembre dezembro dez dic",
}
MONTH_WORD = {}
for _n, _ws in MONTHS.items():
    for _w in _ws.split():
        MONTH_WORD[fold(_w)] = _n
MONTH_RX = "|".join(sorted((re.escape(w) for w in MONTH_WORD), key=len, reverse=True))
SOUTH = {"AU", "NZ", "ZA", "AR", "CL", "BR", "UY", "PY", "PE", "BO"}
SEASONS = {"spring": 4, "fruhling": 4, "fruhjahr": 4, "printemps": 4, "primavera": 4,
           "summer": 7, "sommer": 7, "ete": 7, "verano": 7, "estate": 7,
           "autumn": 10, "fall": 10, "herbst": 10, "automne": 10, "otono": 10, "autunno": 10,
           "winter": 1, "hiver": 1, "invierno": 1, "inverno": 1}


def _season_month(word, country):
    m = SEASONS[word]
    if (country or "").upper() in SOUTH:
        m = (m + 6 - 1) % 12 + 1
    return m


def _y(s):
    y = int(s)
    return y + 2000 if y < 100 else y


def date_order_from(values):
    """'dmy', 'mdy' or None from numeric dates; raise Stop if both orders appear."""
    first = second = False
    for v in values:
        m = re.match(r"\s*(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2,4})\b", str(v or ""))
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            first |= a > 12
            second |= b > 12
    if first and second:
        raise Stop("the dates are written day first in some rows and month first in others, so none can be read "
                   "safely", ask="Which order do your dates use: day first (3/4 = 3 April) or month first (3/4 = March 4)? "
                   "If it differs by column or by person, fix the odd ones and send it again.")
    return "dmy" if first else "mdy" if second else None


def needs_order(values):
    return any(re.match(r"\s*(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2,4})\b", str(v or "")) for v in values)


def parse_when(value, order="dmy", country="", today=None):
    """Return (date, approx, note) or (None, False, reason)."""
    today = today or date.today()
    if value is None:
        return None, False, "no date"
    if isinstance(value, date):
        return value, False, ""
    if isinstance(value, (int, float)) and 20000 < float(value) < 80000:
        return date(1899, 12, 30) + timedelta(days=int(value)), False, ""
    s = fold(value)
    s = re.sub(r"\s+", " ", s).strip(" ,;")
    if not s or s in ("-", "n/a", "na", "none", "?", "unknown", "unbekannt"):
        return None, False, "no date"
    m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if m:
        return _mk(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.match(r"(\d{4})[/.](\d{1,2})[/.](\d{1,2})\b", s)
    if m:
        return _mk(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.match(r"(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2,4})\b", s)
    if m:
        a, b, y = int(m.group(1)), int(m.group(2)), _y(m.group(3))
        d, mo = (b, a) if order == "mdy" else (a, b)
        return _mk(y, mo, d)
    m = re.match(r"(\d{1,2})(?:st|nd|rd|th|\.)?\s*(?:of\s+)?(" + MONTH_RX + r")\.?,?\s*(\d{2,4})\b", s)
    if m:
        return _mk(_y(m.group(3)), MONTH_WORD[m.group(2)], int(m.group(1)))
    m = re.match(r"(" + MONTH_RX + r")\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b", s)
    if m:
        return _mk(int(m.group(3)), MONTH_WORD[m.group(1)], int(m.group(2)))
    m = re.match(r"(?:(early|mid|late|end of|beginning of|anfang|mitte|ende|debut|fin)\s+)?(" + MONTH_RX + r")\.?,?\s+"
                 r"(?:of\s+)?(" + LAST_RX + "|" + THIS_RX + "|" + NEXT_RX + r")\s+(?:year|jahr(?:es)?|annee|ano)\b", s)
    if m:
        mo = MONTH_WORD[m.group(2)]
        y = today.year + (-1 if re.fullmatch(LAST_RX, m.group(3)) else 1 if re.fullmatch(NEXT_RX, m.group(3)) else 0)
        day = {"early": 5, "beginning of": 5, "anfang": 5, "debut": 5, "late": 25, "end of": 25, "ende": 25, "fin": 25}.get(m.group(1) or "", 15)
        d, _a, _n = _mk(y, mo, day)
        return d, True, f"'{value}' read as {MONTH_EN[mo - 1]} {y}"
    m = re.match(r"(?:(" + MONTH_RX + r")\.?,?\s+)?(" + LAST_RX + "|" + THIS_RX + r")\s+(spring|summer|autumn|fall|winter|sommer|"
                 r"herbst|fruhling|fruhjahr|ete|hiver|automne|printemps|verano|invierno|otono|primavera)\b", s)
    if m:
        d = _season_date(m.group(3), country, today, last=bool(re.fullmatch(LAST_RX, m.group(2))),
                         month=MONTH_WORD.get(m.group(1)) if m.group(1) else None)
        hemi = "southern" if (country or "").upper() in SOUTH else "northern"
        return d, True, f"'{value}' read as {MONTH_EN[d.month - 1]} {d.year} ({hemi} hemisphere seasons)"
    m = re.fullmatch(r"(\d{1,2})[/.](\d{1,2})\.?", s)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        dd, mo = (b, a) if order == "mdy" else (a, b)
        if 1 <= mo <= 12:
            cand, _a, _n = _mk(today.year, mo, dd)
            if cand and cand > today:
                cand, _a, _n = _mk(today.year - 1, mo, dd)
            if cand:
                return cand, True, f"no year given: '{value}' read as {cand.day} {MONTH_EN[mo - 1]} {cand.year}, the most recent one"
    m = re.match(r"(?:(early|mid|late|end of|beginning of|anfang|mitte|ende|debut|fin)\s+)?(" + MONTH_RX + r")\.?\s*'?(\d{2,4})\b", s)
    if m:
        day = {"early": 5, "beginning of": 5, "anfang": 5, "debut": 5, "late": 25, "end of": 25, "ende": 25, "fin": 25}.get(m.group(1) or "", 15)
        d, _a, _n = _mk(_y(m.group(3)), MONTH_WORD[m.group(2)], day)
        return d, True, "month only, read as the %s" % day
    m = re.match(r"(\d{1,2})[/.](\d{4})\b", s)
    if m:
        d, _a, _n = _mk(int(m.group(2)), int(m.group(1)), 15)
        return d, True, "month only, read as the 15th"
    m = re.match(r"q([1-4])\s*'?(\d{2,4})\b", s) or re.match(r"(\d{2,4})\s*q([1-4])\b", s)
    if m:
        q, y = (int(m.group(1)), _y(m.group(2))) if s.startswith("q") else (int(m.group(2)), _y(m.group(1)))
        return date(y, 3 * q - 1, 15), True, f"quarter only, read as mid Q{q}"
    m = re.match(r"(early|mid|late|end of|spring|summer|autumn|fall|winter|sommer|herbst|winter|fruhling|fruhjahr)\s+(\d{4})\b", s)
    if m:
        w, y = m.group(1), int(m.group(2))
        if w in SEASONS:
            return date(y, _season_month(w, country), 15), True, f"{w} only, read as the middle of it"
        mo = {"early": 2, "mid": 7, "late": 11, "end of": 11}[w]
        return date(y, mo, 15), True, f"{w} {y}, read as the middle of that part of the year"
    m = re.fullmatch(r"(?:in\s+)?(\d{4})", s)
    if m and 1990 < int(m.group(1)) <= today.year:
        return date(int(m.group(1)), 7, 1), True, "year only, read as 1 July"
    m = re.match(r"(\d+|a|an|one|two|three|four|five|six|a couple of|a few)\s+(day|week|month|year)s?\s+ago", s)
    if m:
        n = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
             "a couple of": 2, "a few": 3}.get(m.group(1)) or int(m.group(1))
        days = {"day": 1, "week": 7, "month": 30, "year": 365}[m.group(2)] * n
        return today - timedelta(days=days), True, f"'{value}' counted back from today"
    rel = {"yesterday": 1, "last week": 7, "last month": 30, "last year": 365}
    if s in rel:
        return today - timedelta(days=rel[s]), True, f"'{value}' counted back from today"
    m = re.match(r"(?:(?:" + LAST_RX + r")\s+)?(" + MONTH_RX + r")\b", s)
    if m:
        mo = MONTH_WORD[m.group(1)]
        y = today.year if mo <= today.month else today.year - 1
        return date(y, mo, 15), True, f"no year given: '{value}' read as {MONTH_EN[mo - 1]} {y}, the most recent one"
    return None, False, f"'{value}' is not a date I can read"


LAST_RX = r"(?:last|past|letzte[nrs]?|vergangene[nrs]?|dernier|derniere|pasado|pasada|scorso|scorsa|vorig[e]?)"
THIS_RX = r"(?:this|dieses|diesen|diese[nrs]?|cette|cet|ce|este|esta|quest[oa])"
NEXT_RX = r"(?:next|nachste[nrs]?|prochain[e]?|proximo|proxima)"
MONTH_EN = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
            "November", "December"]


def _season_date(word, country, today, last=True, month=None):
    """'last winter', 'this summer', 'June last winter', by the founder's hemisphere. Returns a date."""
    key = {"ete": "summer", "hiver": "winter", "automne": "autumn", "printemps": "spring", "verano": "summer",
           "invierno": "winter", "otono": "autumn", "primavera": "spring"}.get(word, word)
    mid = _season_month(key if key in SEASONS else word, country)
    cand = date(today.year, mid, 15)
    if last:
        while cand + timedelta(days=45) > today:
            cand = date(cand.year - 1, mid, 15)
    else:
        while cand - timedelta(days=45) > today:
            cand = date(cand.year - 1, mid, 15)
    if month:
        diff = (month - mid + 6) % 12 - 6
        if -1 <= diff <= 1:
            y, mo = cand.year, mid + diff
            if mo < 1:
                y, mo = y - 1, mo + 12
            elif mo > 12:
                y, mo = y + 1, mo - 12
            return date(y, mo, 15)
    return cand


def _mk(y, mo, d):
    try:
        return date(y, mo, d), False, ""
    except ValueError:
        return None, False, f"{d}/{mo}/{y} is not a real date"


def parse_future(phrase, anchor, order="dmy", country=""):
    """Read a come-back date ("till Q3", "after the summer break", "ask in January", "after the 20th").
    Returns (date, approx, note) for the first matching date after the anchor, or (None, False, why)."""
    s = fold(phrase)
    after = bool(re.search(r"\b(after|nach|apres|despues|dopo|once|when)\b", s))
    d, approx, note = parse_when(re.sub(r"^.*?\b(till|until|bis|jusqu'?a|hasta|after|nach|apres|despues|in|im|"
                                        r"en|around|from|ab|by)\s+(the\s+|der\s+|dem\s+|le\s+|el\s+)?", "", s),
                                 order, country, anchor)
    explicit_year = bool(re.search(r"\b(19|20)\d{2}\b|'\d{2}\b", s))
    by = re.search(r"\b(?:erst|not (?:until|before)|nicht vor|pas avant|no antes de)\s+(?:in |im |ab )?((?:19|20)\d{2})\b", s)
    if by:
        return date(int(by.group(1)), 1, 5), True, "a year, read as early January of it"
    if d and explicit_year:
        return (_end_of(d, s) if after else _start_of(d, s)), True, "from their words"
    m = re.search(r"\bq([1-4])\b", s)
    if m:
        q = int(m.group(1))
        y = anchor.year
        start = date(y, 3 * q - 2, 5)
        if start <= anchor and not (start.year == anchor.year and 3 * q >= anchor.month and not after):
            start = date(y + 1, 3 * q - 2, 5)
        if after:
            end_month = 3 * q
            start = date(start.year + (1 if end_month == 12 else 0), 1 if end_month == 12 else end_month + 1, 5)
        return start, True, f"Q{q} read as the 5th of {'the month after' if after else 'its first month'}"
    if re.search(r"summer ?(break|holiday|holidays|pause)|sommerpause|sommerferien|after (the )?summer|nach dem sommer|"
                 r"apres l'?ete|vacances d'?ete|rentree", s):
        mo = 2 if (country or "").upper() in SOUTH else 9
        return _next_occurrence(anchor, mo, 1), True, "after the summer break, read as the 1st of the month after"
    if re.search(r"\bharvest|ernte|vendange|cosecha", s):
        mo = 4 if (country or "").upper() in SOUTH else 10
        return _next_occurrence(anchor, mo, 1), True, "after harvest, read as the 1st of October (April in the south)"
    m = re.search(r"\b(spring|summer|autumn|fall|winter|sommer|herbst|fruhling|fruhjahr)\b", s)
    if m:
        mo = _season_month(m.group(1), country)
        if after:
            mo = (mo + 3 - 1) % 12 + 1
        return _next_occurrence(anchor, mo, 1), True, f"{m.group(1)} read as the 1st of its first month"
    if re.search(r"heizperiode|heizsaison|heating season|saison de chauffe", s):
        mo = 4 if after else 10
        if (country or "").upper() in SOUTH:
            mo = 10 if after else 4
        return _next_occurrence(anchor, mo, 1), True, "the heating season, read as ending in April (October in the south)"
    if re.search(r"christmas|xmas|weihnacht|noel|navidad|natale|the holidays", s):
        if after:
            return _next_occurrence(anchor, 1, 5), True, "after Christmas, read as 5 January"
        return _next_occurrence(anchor, 12, 1), True, "Christmas, read as 1 December"
    if re.search(r"new year|neuen jahr|neujahr|nouvel an|ano nuevo|next year|nachstes jahr|l'?annee prochaine", s):
        return date(anchor.year + 1, 1, 5), True, "the new year, read as 5 January"
    m = re.search(r"\b(" + MONTH_RX + r")\b", s)
    if m:
        mo = MONTH_WORD[m.group(1)]
        if after:
            return _next_occurrence(anchor, mo % 12 + 1, 1), True, "after that month, read as the 1st of the next"
        return _next_occurrence(anchor, mo, 5), True, "a month, read as the 5th of it"
    m = re.search(r"\b(\d{1,2})(?:st|nd|rd|th|\.)\b", s)
    if m:
        day = int(m.group(1)) + (1 if after else 0)
        cand = _safe(anchor.year, anchor.month, day)
        if cand is None or cand <= anchor:
            ny, nm = (anchor.year + 1, 1) if anchor.month == 12 else (anchor.year, anchor.month + 1)
            cand = _safe(ny, nm, day)
        if cand:
            return cand, True, "a day of the month, read as the next one"
    m = re.search(r"\b(\d+|a|one|two|three|four|six)\s+(week|month)s?\b", s)
    if m:
        n = {"a": 1, "one": 1, "two": 2, "three": 3, "four": 4, "six": 6}.get(m.group(1)) or int(m.group(1))
        return anchor + timedelta(days=(7 if m.group(2) == "week" else 30) * n), True, "counted on from when they said it"
    if d:
        return (_end_of(d, s) if after else d), approx, note
    return None, False, f"could not read a date in '{phrase}'"


def _safe(y, m, d):
    try:
        return date(y, m, d)
    except ValueError:
        return None


def _next_occurrence(anchor, month, day):
    cand = date(anchor.year, month, day)
    if cand <= anchor:
        cand = date(anchor.year + 1, month, day)
    return cand


def _start_of(d, s):
    if re.search(r"\bq[1-4]\b", s):
        q = (d.month - 1) // 3
        return date(d.year, 3 * q + 1, 1)
    return d


def _end_of(d, s):
    if re.search(r"\bq[1-4]\b", s):
        q = (d.month - 1) // 3 + 1
        return date(d.year + (1 if q == 4 else 0), 1 if q == 4 else 3 * q + 1, 1)
    return d + timedelta(days=1)


# ---------------------------------------------------------------- reading files

def read_text(path):
    data = path.read_bytes()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return data.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1", errors="replace"), "latin-1"


def read_table(path):
    """Return (headers, rows as lists, kind, extra). kind: csv, xlsx, json, tracker."""
    p = Path(path)
    if not p.exists():
        raise Stop(f"cannot find the file {p.name}. Save the founder's list to a file first and give its path")
    suf = p.suffix.lower()
    if suf in (".xlsx", ".xlsm"):
        try:
            book = office.read_xlsx(p)
        except ValueError as e:
            raise Stop(f"{p.name} could not be opened ({e}). Ask the founder to save it again as .xlsx or .csv") from e
        except Exception as e:  # noqa: BLE001
            raise Stop(f"{p.name} could not be opened as a workbook. Ask the founder to save it as .csv") from e
        if "Contacts" in book:
            heads, out = [], []
            for sheet in ("Contacts", "Held back"):
                rows = [r for r in book.get(sheet, []) if any(v not in (None, "") for v in r)]
                hdr_i = next((i for i, r in enumerate(rows) if r and fold(r[0]) == "ref"), None)
                if hdr_i is None:
                    continue
                hs = [str(h or "") for h in rows[hdr_i]]
                for h in hs:
                    if h not in heads:
                        heads.append(h)
                for r in rows[hdr_i + 1:]:
                    rec = dict(zip(hs, r))
                    rec["_sheet"] = sheet
                    out.append(rec)
            if heads:
                heads.append("_sheet")
                return heads, [[rec.get(h) for h in heads] for rec in out], "tracker", book
        for name, rows in book.items():
            rows = [r for r in rows if any(v not in (None, "") for v in r)]
            if len(rows) >= 2:
                return [str(h or "") for h in rows[0]], rows[1:], "xlsx", None
        raise Stop(f"{p.name} has no sheet with a header row and at least one contact")
    if suf in (".xls", ".numbers", ".ods"):
        raise Stop(f"{p.name} is in a format this cannot read. Ask the founder to save it as .xlsx or .csv")
    if suf == ".json":
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise Stop(f"{p.name} is not valid JSON ({e}). Rewrite it as a list of rows") from e
        rows = data.get("rows") if isinstance(data, dict) else data
        if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
            raise Stop('the JSON must be {"rows": [{...}, ...]} with one object per contact')
        heads = []
        for r in rows:
            for k in r:
                if k not in heads:
                    heads.append(k)
        return heads, [[r.get(h) for h in heads] for r in rows], "json", None
    text, _enc = read_text(p)
    if not text.strip():
        raise Stop(f"{p.name} is empty")
    if suf in (".txt", ".md", ".text", ""):
        return read_lines(text)
    sample = text[:5000]
    delim = max([",", ";", "\t", "|"], key=lambda d: sample.count(d))
    rows = list(csv.reader(io.StringIO(text), delimiter=delim))
    rows = [r for r in rows if any(c.strip() for c in r)]
    if len(rows) < 2:
        raise Stop(f"{p.name} has a header row but no contacts")
    return rows[0], rows[1:], "csv", None


DATE_PHRASE = re.compile(
    r"(\d{4}-\d{1,2}-\d{1,2}|\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4}|\d{1,2}(?:st|nd|rd|th)?\s+(?:%s)\.?,?\s+\d{4}|"
    r"(?:(?:early|mid|late|end of)\s+)?(?:%s)\.?\s+'?\d{2,4}|q[1-4]\s*'?\d{2,4}|"
    r"(?:spring|summer|autumn|fall|winter|early|mid|late)\s+\d{4}|\b(?:19|20)\d{2}\b)" % ("{M}", "{M}"), re.I)
MONEY_PHRASE = re.compile(r"([$\u00a3\u20ac\u20b9]|\b(?:USD|GBP|EUR|AUD|CAD|NZD|SGD)\s?)\s?\d[\d.,]*\s?k?\b|\b\d[\d.,]*\s?(?:\u20ac|EUR|USD|GBP)\b", re.I)
PHONE_PHRASE = re.compile(r"(?<![\w/.])\+?\d[\d ()\-]{8,}\d(?![\w/])")
EMAIL_FIND = re.compile(r"[A-Za-z0-9._%+'\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
COME_BACK_WORDS = re.compile(r"\b(till|until|after|ask in|ring (me )?in|back in|by|from|bis|nach)\s*$", re.I)


def read_lines(text):
    """A pasted list, one contact per line, in any shape. Pulls out what it can; the line stays as the notes."""
    heads = ["name", "company", "email", "phone", "last_contact", "value", "notes", "raw"]
    rows = []
    month_rx = MONTH_RX
    dp = re.compile(DATE_PHRASE.pattern.replace("{M}", month_rx), re.I)
    for line in text.splitlines():
        raw = line.strip()
        if not raw or re.fullmatch(r"[-=*#_ ]+", raw):
            continue
        body = re.sub(r"^\s*(?:[-*\u2022]|\d{1,3}[.)])\s+", "", raw)
        if re.match(r"^(name|contact)\b.*\b(email|date|notes)\b", body, re.I) and len(rows) == 0:
            continue
        email = (EMAIL_FIND.search(body) or [None])[0] if EMAIL_FIND.search(body) else None
        rest = EMAIL_FIND.sub(" ", body)
        phone_m = PHONE_PHRASE.search(rest)
        phone = phone_m.group(0) if phone_m else None
        company = None
        m = re.search(r"\(([^)]{2,40})\)", rest)
        if m and not dp.search(m.group(1)) and not re.search(r"\d", m.group(1)) and len(m.group(1).split()) <= 5 \
                and re.match(r"[A-Z]", m.group(1)):
            company = m.group(1).strip()
        lead_co = re.match(r"\s*[A-Z][\w'\u00c0-\u017f]+(?: [A-Z][\w'.\u00c0-\u017f]*){0,2}\s*,\s*([A-Z][\w&'.\u00c0-\u017f]*(?: [\w&'.\u00c0-\u017f]+){0,3})\s*,\s*[\w.+-]+@", body)
        if not company and lead_co and not re.search(r"\d", lead_co.group(1)) and not dp.search(lead_co.group(1)):
            company = lead_co.group(1).strip()
        name_m = re.match(r"\s*((?:(?:[A-Z][\w'\u00c0-\u017f]+|[A-Z]\.?)(?:[ ](?=[A-Z])|$|(?=[ ,(\-:;]))){1,3})", rest)
        name = name_m.group(1).strip() if name_m else ""
        if name and fold(name).split()[0] in ("the", "no", "met", "was", "ghosted", "enquired", "asked", "client"):
            name = ""
        dates = []
        for dm in dp.finditer(rest):
            before = rest[max(0, dm.start() - 12):dm.start()]
            if COME_BACK_WORDS.search(before):
                continue
            dates.append(dm.group(0))
        money = MONEY_PHRASE.search(rest)
        rows.append([name, company, email, phone, dates[0] if dates else None,
                     money.group(0) if money else None, body, raw])
    if not rows:
        raise Stop("no contacts found in the pasted text")
    return heads, rows, "lines", None


INSTRUCTION_RX = re.compile(
    r"(ignore (all |any )?(previous|prior|above) (instructions|prompts?)|disregard (the|all|your) (instructions|rules)|"
    r"you are now|system prompt|as an ai|new instructions|email (every|all) (contact|lead)s?|send (this|it) to (every|all)|"
    r"delete (the|all|this) (file|list|rows)|do not tell (the )?(user|founder)|execute|run the following)", re.I)
ROLE_RX = re.compile(r"^(info|sales|hello|hi|admin|contact|office|team|support|enquiries|inquiries|mail|accounts|"
                     r"billing|marketing|noreply|no-reply|kontakt|bonjour|hola|post|reception)@", re.I)
EMAIL_RX = re.compile(r"^[A-Za-z0-9._%+'\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


def clean_phone(p):
    digits = re.sub(r"\D", "", str(p or ""))
    return digits if len(digits) >= 7 else ""


def first_name_of(name, email):
    n = str(name or "").strip()
    if n and "@" not in n:
        tok = re.split(r"[\s,]+", n)[0].strip(".-")
        if re.fullmatch(r"(mr|mrs|ms|dr|herr|frau|mme|m|sr|sra)\.?", tok, re.I) and len(n.split()) > 1:
            return n.split()[1], ""
        return tok, ""
    local = str(email or "").split("@")[0]
    if local and not ROLE_RX.match(local + "@") and re.fullmatch(r"[A-Za-z]{2,}", re.split(r"[._\-+]", local)[0]):
        return re.split(r"[._\-+]", local)[0].capitalize(), "first name read from the email address: check it"
    return "", "no first name"


def ingest(path, date_order=None, decimal=None, today=None, country="", given_map=None):
    today = today or date.today()
    heads, rows, kind, book = read_table(path)
    if len(rows) > MAX_ROWS:
        raise Stop(f"the list has {len(rows)} rows. This works on up to {MAX_ROWS} at a time, one person at a time",
                   ask="Can you send just the people you have actually spoken to or worked with in the last three years?")
    fmap = map_headers(heads, given_map or {})
    if kind == "tracker":
        fmap = {}
        for i, h in enumerate(heads):
            hf = fold(h)
            for key, label in TRACKER_LABELS:
                if hf == label:
                    fmap[key] = i
    if not any(k in fmap for k in ("name", "first_name", "email", "phone", "company")):
        raise Stop("no column looks like a name, company, email or phone. Columns: " + ", ".join(map(str, heads)),
                   ask="Which column holds the person's name, and which their email or phone?")

    def get(r, k):
        i = fmap.get(k)
        if i is None or i >= len(r):
            return None
        v = r[i]
        return v.strip() if isinstance(v, str) else v

    date_vals = [get(r, "last_contact") for r in rows]
    order = date_order
    found = date_order_from([v for v in date_vals if isinstance(v, str)])
    if order and found and found != order:
        raise Stop(f"you said dates are {order}, but some dates in the file only make sense {found}",
                   ask="Some dates only make sense the other way round. Which order does the file use?")
    order = order or found
    if not order and needs_order([v for v in date_vals if isinstance(v, str)]):
        cc = (country or "").upper()
        if cc:
            order = ln.locale_defaults(cc)["date_order"].lower()
            if order == "ymd":
                order = "dmy"
            order_note = f"no date settles the order, so read {order[:1].upper()}-first as usual for {cc}"
        else:
            sample = next(v for v in date_vals if isinstance(v, str) and re.match(r"\s*\d{1,2}[/.\-]\d{1,2}[/.\-]", v))
            a, b = re.match(r"\s*(\d{1,2})[/.\-](\d{1,2})", sample).groups()
            mname = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
                     "October", "November", "December"]
            raise Stop("no date in the list shows whether day or month comes first",
                       ask=f"Is {sample} the {int(a)} {mname[int(b) - 1]} or {mname[int(a) - 1]} {int(b)}?")
    else:
        order_note = ""
    order = order or "dmy"

    money_texts = [str(get(r, "value")) for r in rows if get(r, "value") not in (None, "") and isinstance(get(r, "value"), str)]
    style = decimal or ln.detect_decimal_style(money_texts)
    contacts, problems = [], []
    for n, r in enumerate(rows, start=1):
        rec = {"row": n, "flags": []}
        for k in ("ref", "name", "first_name", "last_name", "company", "email", "phone", "stage", "reason", "notes",
                  "source", "channel", "deal", "status", "reply_notes", "group", "next_touch", "next_date", "stop_date",
                  "cooldown_until", "why", "came_from", "personal", "invoices", "touch_dates", "tier", "held_code",
                  "revisit", "sheet", "held_reason_in", "handle"):
            v = get(r, k)
            if v not in (None, ""):
                rec[k] = v if isinstance(v, (date, int, float)) else str(v)
        if kind in ("json", "lines"):
            src = dict(zip(heads, r))
            for extra in ("raw", "parked_until", "parked_phrase", "context", "segment", "came_onto_list", "off_limits",
                          "texted_before", "value", "handle"):
                if src.get(extra) not in (None, ""):
                    rec[extra] = src[extra]
        if not rec.get("company") and "company" not in fmap and rec.get("deal") and re.search(r"\s[-|:]\s", str(rec["deal"])):
            co, _sep, rest_deal = re.split(r"(\s[-|:]\s)", str(rec["deal"]), maxsplit=1)
            rec["company"], rec["deal"] = co.strip(), rest_deal.strip()
        if not rec.get("name") and (rec.get("first_name") or rec.get("last_name")):
            rec["name"] = " ".join(x for x in (rec.get("first_name"), rec.get("last_name")) if x)
        if not rec.get("name") and rec.get("company") and not rec.get("email"):
            rec["name"] = ""
        email = str(rec.get("email") or "").strip().strip("<>").strip()
        if email:
            if EMAIL_RX.match(email):
                rec["email"] = email.lower()
                if ROLE_RX.match(email):
                    rec["flags"].append("shared inbox address")
            else:
                rec["flags"].append(f"email '{email}' is not a working address")
                rec.pop("email", None)
        ph = clean_phone(rec.get("phone"))
        if rec.get("phone") and not ph:
            rec["flags"].append("phone number unreadable")
        if ph:
            rec["phone_digits"] = ph
        if not rec.get("name") and rec.get("email"):
            rec["name"] = ""
        fn, fnote = first_name_of(rec.get("first_name") or rec.get("name"), rec.get("email"))
        rec["first"] = fn
        if fnote and fnote != "no first name":
            rec["flags"].append(fnote)
        raw_date = get(r, "last_contact")
        d, approx, note = parse_when(raw_date, order, country, today)
        if raw_date not in (None, "") and d is None:
            rec["flags"].append(f"date not read: {note}")
        if d:
            if d > today:
                rec["flags"].append("last contact date is in the future: check it")
                rec["future_date"] = True
            rec["last_contact"] = d.isoformat()
            rec["date_as_given"] = str(raw_date) if not isinstance(raw_date, date) else d.isoformat()
            if approx:
                rec["date_approx"] = note
                if note.startswith("no year given") or "' read as" in note:
                    rec["flags"].append(f"date {note}: if that is wrong, correct it (annotation last_contact)")
        raw_val = rec.get("value") if kind in ("json", "lines") else get(r, "value")
        if raw_val not in (None, ""):
            try:
                val = ln.parse_money(raw_val, style)[0] if isinstance(raw_val, str) else float(raw_val)
                rec["value"] = val
                rec["value_as_given"] = str(raw_val)
            except ln.Ambiguous as e:
                problems.append(("ask", f"row {n}: {e}"))
            except (ln.Unreadable, ValueError):
                rec["flags"].append(f"value '{raw_val}' not read")
                rec.pop("value", None)
        text_all = " ".join(str(rec.get(k, "")) for k in ("notes", "reason", "stage", "raw", "reply_notes"))
        if INSTRUCTION_RX.search(text_all):
            rec["instruction_text"] = True
            rec["flags"].append("the notes hold an instruction to an AI; it was ignored")
        contacts.append(rec)
    asks = [m for k, m in problems if k == "ask"]
    if asks:
        raise Stop("a value can be read two ways: " + asks[0],
                   ask="Do you write a dot for thousands (12.500 = twelve thousand five hundred) or for decimals?")

    dated = [c["last_contact"] for c in contacts if c.get("last_contact") and not c.get("date_approx")]
    bulk = None
    if len(dated) >= 10:
        top = max(set(dated), key=dated.count)
        if dated.count(top) > len(contacts) / 3:
            bulk = top
            for c in contacts:
                if c.get("last_contact") == top:
                    c["flags"].append("this date is shared by over a third of the list, probably an import stamp: treated as unknown")
                    c["bulk_date"] = top
                    c.pop("last_contact", None)

    # duplicates: email, phone, or name plus company
    keep = {}
    for c in contacts:
        keys = []
        if c.get("email"):
            keys.append("e:" + c["email"])
        if c.get("phone_digits"):
            keys.append("p:" + c["phone_digits"][-9:])
        if c.get("name") and c.get("company"):
            keys.append("n:" + fold(c["name"]) + "|" + fold(c["company"]))
        hit = next((keep[k] for k in keys if k in keep), None)
        if hit is not None and kind != "tracker":
            winner, loser = (hit, c)
            if (c.get("last_contact") or "") > (hit.get("last_contact") or ""):
                winner, loser = c, hit
            loser["duplicate_of"] = winner["row"]
            for k in ("notes", "reason", "raw"):
                if loser.get(k) and loser.get(k) not in str(winner.get(k, "")):
                    winner[k] = (str(winner.get(k, "")) + " / " + str(loser[k])).strip(" /")
            for k in ("email", "phone", "phone_digits", "company", "value", "first"):
                if not winner.get(k) and loser.get(k):
                    winner[k] = loser[k]
            for k in keys:
                keep[k] = winner
            if loser is hit:
                for k, v in list(keep.items()):
                    if v is loser:
                        keep[k] = winner
            continue
        for k in keys:
            keep[k] = c
    # a winner that was later superseded must not itself be marked
    for c in contacts:
        if c.get("duplicate_of"):
            target = next(x for x in contacts if x["row"] == c["duplicate_of"])
            while target.get("duplicate_of"):
                target = next(x for x in contacts if x["row"] == target["duplicate_of"])
            c["duplicate_of"] = target["row"]
    # the same full name on two rows that were not merged (different email or phone): ask, never guess
    if kind != "tracker":
        by_name = {}
        for c in contacts:
            nm = fold(c.get("name"))
            if c.get("duplicate_of") or len(nm.split()) < 2 or "@" in nm:
                continue
            by_name.setdefault(nm, []).append(c)
        for nm, cs in by_name.items():
            if len(cs) < 2:
                continue
            for c in cs:
                others = ", ".join(f"row {o['row']}" for o in cs if o is not c)
                c["flags"].append(f"same name as {others} with different details: if it is the same person, say so "
                                  "and the rows are merged (annotation hold duplicate on the older row)")
                c["same_name_as"] = [o["row"] for o in cs if o is not c]
    for c in contacts:
        if not c.get("email") and not c.get("phone_digits") and kind not in ("lines", "json"):
            c["flags"].append("no email or phone")
        if re.search(r"\b(studio|ltd|limited|llc|inc|gmbh|agency|co|company|group|partners|consulting)\b",
                     str(c.get("name", "")), re.I) and not c.get("first_name"):
            c["flags"].append("the name looks like a business, so the first name may be wrong: check it")
        if not c.get("ref"):
            c["ref"] = f"C{c['row']:03d}"
    return {
        "kind": kind, "rows_in": len(rows), "date_order": order, "date_order_note": order_note,
        "decimal": style, "headers": [str(h) for h in heads],
        "mapped": {k: str(heads[v]) for k, v in fmap.items() if v < len(heads)},
        "bulk_date": bulk, "contacts": contacts,
    }


def jsonable(o):
    if isinstance(o, date):
        return o.isoformat()
    raise TypeError(str(type(o)))


def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("file")
    a.add_argument("--date-order", choices=["dmy", "mdy", "ymd"])
    a.add_argument("--decimal", choices=["dot", "comma"])
    a.add_argument("--today")
    a.add_argument("--country", default="")
    a.add_argument("--map", action="append", default=[])
    a.add_argument("--json-out")
    args = a.parse_args()
    try:
        today = date.fromisoformat(args.today) if args.today else date.today()
        gm = {}
        for m in args.map:
            if "=" not in m:
                raise Stop(f"--map needs field=Column, got '{m}'")
            k, v = m.split("=", 1)
            if k not in FIELDS:
                raise Stop(f"--map field '{k}' is not one of: {', '.join(FIELDS)}")
            gm[k] = v
        res = ingest(args.file, args.date_order, args.decimal, today, args.country, gm)
    except Stop as e:
        print(f"STOP: {e}")
        if e.ask:
            print(f"ASK: {e.ask}")
        sys.exit(2)
    except ValueError as e:
        print(f"STOP: {e}")
        sys.exit(2)
    out = json.dumps(res, indent=1, default=jsonable, ensure_ascii=False)
    if args.json_out:
        Path(args.json_out).write_text(out, encoding="utf-8")
        print(f"WROTE: {args.json_out} ({res['rows_in']} rows, date order {res['date_order']})")
    else:
        print(out)


if __name__ == "__main__":
    main()
