#!/usr/bin/env python3
"""Count a CRM or spreadsheet export into monthly actuals and channel counts for target_plan.py.

Usage:
  python3 scripts/count_export.py <export.csv> [--today YYYY-MM-DD] [--date-col NAME] [--stage-col NAME]
        [--source-col NAME] [--map "status=stage" ...] [--dates day-first|month-first] [--json-out counts.json]

One row per lead or enquiry. The script finds the date, status and source columns by their headings (or use the
flags), reads each row's status as the furthest stage it reached (lead, booked, held, offer, sale), and counts
the last three whole months before --today. Every status it read is printed with the stage it was given, so you
can read the mapping back to the founder. A status it cannot place is listed as UNMAPPED: ask the founder, then
pass --map "Status text=held" (stages: lead, booked, held, offer, sale).

Dates: the order of day and month in dates such as 03/07/2026 follows the founder. The script reads it from the
export itself (a date such as 23/07 or 07/23 settles it); if every such date could be either, it stops and asks
for --dates day-first or --dates month-first. No country is assumed. Standard library only. No network calls.
Exit codes: 0 counted; 1 counted with UNMAPPED statuses or skipped rows; 2 STOP.
"""
import argparse
import csv
import io
import json
import re
import sys
import unicodedata
from datetime import date, datetime
from pathlib import Path

ORDER = ["lead", "booked", "held", "offer", "sale"]
RULES = [  # first match wins; checked on the status lowercased with accents removed (so "Gagné" reads as "gagne")
    (r"not booked|never booked|unbooked|did not book|didn'?t book|no call|pas de rdv|sin cita|kein termin", "lead"),
    (r"no[- ]?show|did not (show|attend)|didn'?t show|cancel+ed|resched|annule|absent|pas venu|no se presento|"
     r"no asistio|cancelad|nicht erschienen|abgesagt|verschoben|niet verschenen|geannuleerd|nao compareceu|"
     r"reporte|reprogramad", "booked"),
    (r"\b(won|closed[- ]?won|sold|signed|paid|deposit|client|customer|converted|enrolled|bought|purchased|gagne|"
     r"signe|vendu|ganad[oa]|vendid[oa]|cerrad[oa] ganad[oa]|gewonnen|verkauft|unterschrieben|ganho|fechad[oa]|"
     r"vinto|vinta|cliente)\b", "sale"),
    (r"proposal|offer( made| sent)?|pitched|quote sent|contract sent|negotiat|proposition|devis|offre|propuesta|"
     r"presupuesto|cotizacion|angebot|offerte|voorstel|proposta|orcamento|preventivo|negoci|verhandl", "offer"),
    (r"\b(lost|closed[- ]?lost|not interested after call|declined|perdu|refuse|perdid[oa]|verloren|abgelehnt|"
     r"perso|persa)\b", "held"),
    (r"held|showed|attended|completed|call done|had call|met|discovery done|follow[- ]?up|effectue|realise|"
     r"rdv fait|realizad[oa]|celebrad[oa]|stattgefunden|gefuhrt|durchgefuhrt|gehad|gevoerd|realizad|svolt|"
     r"relance|seguimiento|nachfass", "held"),
    (r"booked|scheduled|call set|appointment|meeting set|confirmed|rdv|rendez[- ]?vous|planifie|agendad[oa]|"
     r"programad[oa]|cita|reunion|termin|gebucht|vereinbart|afspraak|ingepland|gepland|agendad|marcad[oa]|"
     r"appuntamento|fissat", "booked"),
    (r"enquir|inquir|lead|new|contacted|dm|opt[- ]?in|no reply|ghost|unqualified|disqualified|not booked|cold|nurture|"
     r"open|nouveau|nouvelle|contacte|prospect|nuev[oa]|contactad[oa]|neu|kontaktiert|anfrage|nieuw|gecontacteerd|"
     r"novo|nova|contatad|nuovo|nuova|contattat|sans reponse|sin respuesta|keine antwort", "lead"),
]
DATE_HEADS = (r"date|created|enquiry|inquiry|received|added|first contact|when|fecha|data|datum|creado|cree|creation|"
              r"erstellt|aangemaakt|criado|creato")
STAGE_HEADS = r"status|stage|outcome|result|pipeline|statut|etape|estado|etapa|fase|phase|stufe|resultat|esito|stato"
SOURCE_HEADS = (r"source|channel|where from|came from|how (did|they)|referr|origin|medium|canal|origen|origem|"
                r"origine|quelle|herkunft|bron|kanal|fuente|provenance|fonte")
MONTHS = "jan feb mar apr may jun jul aug sep oct nov dec".split()


class Stop(Exception):
    pass


def date_order(values):
    """'day-first', 'month-first' or None (no slash dates, or none that settles it). STOP if the export mixes both."""
    first = second = False
    for v in values:
        m = re.match(r"\s*(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2,4})", str(v or ""))
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            first |= a > 12
            second |= b > 12
    if first and second:
        raise Stop("the export writes some dates day first and some month first, so they cannot be read safely. "
                   "Ask the founder which order each part uses, or fix the column, and run again")
    return "day-first" if first else "month-first" if second else None


def ambiguous_dates(values):
    return any(re.match(r"\s*(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2,4})", str(v or "")) for v in values)


def parse_date(s, us=False):
    s = str(s or "").strip()
    if not s:
        return None
    m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.match(r"(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2,4})", s)
    if m:
        a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        y = y + 2000 if y < 100 else y
        d, mo = (b, a) if us else (a, b)
        if mo > 12 and d <= 12:
            d, mo = mo, d
        try:
            return date(y, mo, d)
        except ValueError:
            return None
    m = re.match(r"(\d{1,2})(?:st|nd|rd|th)?\s+([a-z]{3})[a-z]*\.?,?\s+(\d{4})", s.lower())
    if m and m.group(2) in MONTHS:
        return date(int(m.group(3)), MONTHS.index(m.group(2)) + 1, int(m.group(1)))
    m = re.match(r"([a-z]{3})[a-z]*\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})", s.lower())
    if m and m.group(1) in MONTHS:
        return date(int(m.group(3)), MONTHS.index(m.group(1)) + 1, int(m.group(2)))
    return None


def fold(text):
    """Lowercase with accents removed: 'Date de création' and 'Gagné' match however the export spells them."""
    t = unicodedata.normalize("NFKD", str(text or ""))
    return "".join(ch for ch in t if not unicodedata.combining(ch)).strip().lower()


def stage_of(status, extra):
    s = fold(status)
    for k, v in extra.items():
        if s == fold(k):
            return v, "your mapping"
    if not s:
        return "lead", "blank status read as a lead"
    for rx, st in RULES:
        if re.search(rx, s):
            note = "read as a held call that did not buy; say if it was lost before the call" if st == "held" and \
                re.search(r"lost|declined|perdu|refuse|perdid|verloren|abgelehnt|perso", s) else ""
            return st, note
    return None, ""


def pick(heads, rx, given):
    if given:
        for h in heads:
            if fold(h) == fold(given):
                return h
        raise Stop(f"there is no column called '{given}'. The columns are: {', '.join(heads)}")
    for h in heads:
        if re.search(rx, fold(h)):
            return h
    return None


def read_text(path):
    """UTF-8 first (with or without a byte-order mark); then Windows-1252, which Excel writes in much of Europe and
    the Americas; then Latin-1, which reads any byte. Says which it used."""
    data = path.read_bytes()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return data.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1", errors="replace"), "latin-1"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("export")
    p.add_argument("--today")
    p.add_argument("--date-col")
    p.add_argument("--stage-col")
    p.add_argument("--source-col")
    p.add_argument("--map", action="append", default=[])
    p.add_argument("--dates", choices=["day-first", "month-first"])
    p.add_argument("--us-dates", action="store_true", help="same as --dates month-first")
    p.add_argument("--json-out")
    a = p.parse_args()
    path = Path(a.export)
    if not path.exists():
        raise Stop(f"there is no file at {a.export}")
    raw, enc = read_text(path)
    lines = [ln for ln in raw.splitlines() if ln.strip()]
    # skip title lines above the header: the header is the first line with a date-like and a status-like heading
    start = 0
    for i, ln in enumerate(lines[:10]):
        low = fold(ln)
        if re.search(DATE_HEADS, low) and re.search(STAGE_HEADS, low):
            start = i
            break
    dialect = csv.Sniffer().sniff(lines[start], delimiters=",;\t") if lines else csv.excel
    rows = list(csv.DictReader(io.StringIO("\n".join(lines[start:])), dialect=dialect))
    if not rows:
        raise Stop("the export has no rows under its header")
    heads = list(rows[0].keys())
    dcol = pick(heads, DATE_HEADS, a.date_col)
    scol = pick(heads, STAGE_HEADS, a.stage_col)
    ocol = pick(heads, SOURCE_HEADS, a.source_col)
    if not dcol or not scol:
        raise Stop("could not find a date column and a status column. Name them with --date-col and --stage-col. "
                   f"The columns are: {', '.join(heads)}")
    extra = {}
    for m in a.map:
        if "=" not in m or m.split("=", 1)[1].strip().lower() not in ORDER + ["sale"]:
            raise Stop(f"--map needs 'Status text=stage' with a stage of {', '.join(ORDER)}: '{m}'")
        k, v = m.split("=", 1)
        extra[k.strip()] = v.strip().lower()
    today = datetime.strptime(a.today, "%Y-%m-%d").date() if a.today else date.today()
    order = a.dates or ("month-first" if a.us_dates else None)
    found = date_order(r.get(dcol) for r in rows)
    if order and found and order != found:
        raise Stop(f"you passed --dates {order}, but the export has dates that only read {found}. Check with the founder")
    order = order or found
    if order is None and ambiguous_dates(r.get(dcol) for r in rows):
        raise Stop("every date such as 03/07/2026 could be read either way. Ask the founder whether they write the day "
                   "or the month first, then pass --dates day-first or --dates month-first")
    month_first = order == "month-first"
    this_month = (today.year, today.month)
    by_month, by_src, seen, unmapped, skipped, names = {}, {}, {}, {}, 0, {}
    parsed = []
    for r in rows:
        d = parse_date(r.get(dcol), month_first)
        if d is None:
            skipped += 1
            continue
        st, note = stage_of(r.get(scol), extra)
        label = str(r.get(scol) or "").strip() or "(blank)"
        if st is None:
            unmapped[label] = unmapped.get(label, 0) + 1
            continue
        seen.setdefault(label, [st, note, 0])[2] += 1
        parsed.append((d, st, str(r.get(ocol) or "").strip() if ocol else ""))
    months = sorted({(d.year, d.month) for d, _s, _o in parsed if (d.year, d.month) < this_month})[-3:]
    has_offer = any(s == "offer" for _d, s, _o in parsed)
    for d, st, src in parsed:
        key = (d.year, d.month)
        if key not in months:
            continue
        lvl = ORDER.index(st)
        m = by_month.setdefault(key, {"leads": 0, "booked": 0, "showed": 0, "offers": 0, "closed": 0})
        m["leads"] += 1
        m["booked"] += lvl >= 1
        m["showed"] += lvl >= 2
        m["offers"] += lvl >= 3
        m["closed"] += lvl >= 4
        if ocol:
            key_ = fold(src) or "source not recorded"
            names.setdefault(key_, src.strip() or "Source not recorded")
            c = by_src.setdefault(key_, {"leads": 0, "booked": 0, "showed": 0})
            c["leads"] += 1
            c["booked"] += lvl >= 1
            c["showed"] += lvl >= 2
    actuals = []
    for key in months:
        m = by_month[key]
        row = {"month": f"{key[0]}-{key[1]:02d}", "leads": m["leads"], "booked": m["booked"], "showed": m["showed"],
               "closed": m["closed"]}
        if has_offer:
            row["offers"] = m["offers"]
        actuals.append(row)
    channels = [{"name": names.get(k, k), **v} for k, v in sorted(by_src.items(), key=lambda kv: -kv[1]["leads"])]
    print(f"Read as {'UTF-8' if enc == 'utf-8-sig' else 'Windows-1252' if enc == 'cp1252' else 'Latin-1'}. "
          f"Columns used: date '{dcol}', status '{scol}'" + (f", source '{ocol}'" if ocol else ", no source column")
          + (f"; dates read {order}" if order else ""))
    print("How each status was read (furthest stage reached):")
    for label, (st, note, n) in sorted(seen.items(), key=lambda kv: -kv[1][2]):
        print(f"- '{label}' ({n} row{'' if n == 1 else 's'}): {st}" + (f" ({note})" if note else ""))
    for label, n in unmapped.items():
        print(f"UNMAPPED: '{label}' ({n} row{'' if n == 1 else 's'}). Ask the founder which stage it means, then pass --map \"{label}=<stage>\"")
    if skipped:
        print(f"SKIPPED: {skipped} rows with no readable date")
    if not months:
        raise Stop("no whole month before today has any rows. Check the dates, or pass --today")
    print("| Month | Leads | Booked | Held |" + (" Offers |" if has_offer else "") + " Sales |")
    for r in actuals:
        print(f"| {r['month']} | {r['leads']} | {r['booked']} | {r['showed']} |"
              + (f" {r['offers']} |" if has_offer else "") + f" {r['closed']} |")
    for c in channels:
        print(f"Channel {c['name']}: {c['leads']} leads, {c['booked']} booked, {c['showed']} held")
    cur_rows = [(d, st) for d, st, _o in parsed if (d.year, d.month) == this_month and d <= today]
    mtd = None
    if cur_rows:
        lv = [ORDER.index(st) for _d, st in cur_rows]
        mtd = {"to": max(d for d, _s in cur_rows).isoformat(), "leads": len(lv), "booked": sum(x >= 1 for x in lv),
               "showed": sum(x >= 2 for x in lv), "closed": sum(x >= 4 for x in lv)}
        print(f"This month so far (to {mtd['to']}, the latest date in the export): {mtd['leads']} leads, "
              f"{mtd['booked']} booked, {mtd['showed']} held, {mtd['closed']} sales. Kept apart from the whole months and "
              "the rates; copy it to month_to_date so the plan shows this month against the pace")
    out = {"actuals": actuals, "channels": channels if by_src else []}
    if mtd:
        out["month_to_date"] = mtd
    if a.json_out and unmapped:
        print(f"NOT WRITTEN: {a.json_out}. {len(unmapped)} status{'es are' if len(unmapped) > 1 else ' is'} unmapped, so "
              "these counts are incomplete. Ask the founder, pass --map for each, and run again")
    elif a.json_out:
        Path(a.json_out).write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"WROTE: {a.json_out}")
    return 1 if (unmapped or skipped) else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Stop as e:
        print(f"STOP: {e}. Nothing was written.")
        sys.exit(2)
    except (csv.Error, UnicodeDecodeError) as e:
        print(f"STOP: could not read the export as a spreadsheet ({e}). Save it as CSV and try again. Nothing was written.")
        sys.exit(2)
