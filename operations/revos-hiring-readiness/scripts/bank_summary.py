#!/usr/bin/env python3
"""Hiring Readiness Check: read a bank export (CSV) into monthly money in and out.

Usage:
  python3 scripts/bank_summary.py <export.csv> [--exclude "transfer to savings,owner loan"]
        [--month-first | --day-first] [--decimal-comma | --decimal-point] [--from YYYY-MM-DD --to YYYY-MM-DD]

Finds the date column and either one signed amount column or separate money in and money out
columns, by header name in a fixed order of preference (so a bank's "Details: CREDIT/DEBIT" column is
never read as the description). Reads the delimiter (comma, semicolon, tab), the export's own number
style (1,234.56 or 1.234,56) and its date order, and asks only when every date could be read both ways.
Prints each month's money in, money out and net, the average of the last three full months, money in by
month, the latest balance (the chronologically last row, whichever way the file is sorted) and the row
it came from, rows after it with no balance (pending), groups of rows that look like transfers, loans
or owner money, the largest single payments in the averaged months, and every row it could not read.
--exclude matches every text cell in a row and warns when a term matches nothing. Never guesses a figure.
Figures are printed in the export's own number style. Exit codes: 0 read, 2 STOP.
Standard library only. No network calls.
"""
import csv
import re
import sys
from collections import OrderedDict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from locale_numbers import Ambiguous, Unreadable, detect_decimal_style, parse_number  # noqa: E402

DATE_HEADS = ("date", "transaction date", "posting date", "posted", "value date", "completed date", "booking date",
              "buchungstag", "fecha", "datum")
AMOUNT_HEADS = ("amount", "transaction amount", "amount (gbp)", "amount(gbp)", "betrag", "importe", "montant", "value")
IN_HEADS = ("money in", "paid in", "credit amount", "credits", "credit", "deposits", "in")
OUT_HEADS = ("money out", "paid out", "debit amount", "debits", "debit", "withdrawals", "out")
BAL_HEADS = ("balance", "running balance", "closing balance", "available balance", "saldo")
# Preference order matters: Chase puts "Details" (CREDIT or DEBIT) before "Description".
DESC_HEADS = ("description", "transaction description", "narrative", "memo", "payee", "name", "merchant",
              "reference", "verwendungszweck", "concepto", "details")
TRANSFER_WORDS = re.compile(r"transfer|xfer|\bsav\b|savings|\bloan\b|owner|director|drawings|capital|"
                            r"\bto sav|\bfrom sav|internal|own account|between accounts", re.I)
ORDER = {"v": "dmy"}
STYLE = {"decimal": None}


def amt(s):
    """One amount in the export's own style; '(45.00)', '45.00 DR' and '-45' are money out."""
    if s is None:
        return None
    t = str(s).strip()
    if not t:
        return None
    neg = bool(re.search(r"\bDR\b", t, re.I)) or t.endswith("-")
    t = re.sub(r"\b(CR|DR)\b", "", t, flags=re.I).strip().rstrip("-+").strip()
    try:
        v = parse_number(t, STYLE["decimal"], allow_words=False)[0]
    except (Ambiguous, Unreadable):
        return None
    return -abs(v) if neg else v


def fmt(v):
    s = f"{v:,.2f}"
    if STYLE["decimal"] == "comma":
        s = s.replace(",", "\u0000").replace(".", ",").replace("\u0000", ".")
    return s


def order_of(values):
    """'dmy' or 'mdy' from the export itself: a first part above 12 means day first, a second part above 12 means
    month first. None when every numeric date could be read either way."""
    first = second = False
    for s in values:
        m = re.match(r"\s*(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})", str(s or ""))
        if m:
            first |= int(m.group(1)) > 12
            second |= int(m.group(2)) > 12
    if first and not second:
        return "dmy"
    if second and not first:
        return "mdy"
    return None


def dt(s):
    t = str(s or "").strip()
    m = re.match(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", t)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.match(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})", t)
    if m:
        y = int(m.group(3))
        y = y + 2000 if y < 100 else y
        a, b = int(m.group(1)), int(m.group(2))
        return date(y, a, b) if ORDER["v"] == "mdy" else date(y, b, a)
    m = re.match(r"(\d{1,2})[ -]([A-Za-z]{3})[a-z]*[ -](\d{2,4})", t)
    if m:
        mon = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"].index(m.group(2).lower()[:3]) + 1
        y = int(m.group(3))
        return date(y + 2000 if y < 100 else y, mon, int(m.group(1)))
    return None


def find(heads, names, taken=()):
    """The column for the first name, in the given order of preference, that matches a header exactly; then by
    containment. Columns already taken are skipped."""
    for n in names:
        for i, h in enumerate(heads):
            if h == n and i not in taken:
                return i
    for n in names:
        if len(n) <= 3:
            continue
        for i, h in enumerate(heads):
            if n in h and i not in taken:
                return i
    return None


def group_key(desc):
    k = re.sub(r"\d[\d\-/:.#]*", "#", desc.lower())
    k = re.sub(r"[^a-z# ]+", " ", k)
    return re.sub(r"\s+", " ", k).strip()[:48]


def month_range(a, b):
    y, m = a.year, a.month
    while (y, m) <= (b.year, b.month):
        yield f"{y}-{m:02d}"
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def arg(name):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv and sys.argv.index(name) + 1 < len(sys.argv) else None


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    p = Path(sys.argv[1])
    if not p.exists():
        print(f"STOP: there is no file at {p}. Nothing was read.")
        return 2
    excl = [x.strip().lower() for x in (arg("--exclude") or "").split(",") if x.strip()]
    text = p.read_text(encoding="utf-8-sig", errors="replace")
    sample = "\n".join(text.splitlines()[:20])
    delim = max((";", ",", "\t"), key=lambda d: sample.count(d))
    rows = list(csv.reader(text.splitlines(), delimiter=delim))
    if any(sum(1 for c in r if re.fullmatch(r"\s*[A-Za-z]{3}[- ]\d{2,4}\s*", c)) >= 3 for r in rows[:12]):
        print("STOP: this looks like a profit and loss report with months as columns, not a bank export. Read revenue, "
              "direct costs and expenses month by month from it (intake guide, a P&L). Nothing was read.")
        return 2
    hi = next((i for i, r in enumerate(rows[:15]) if find([c.strip().lower() for c in r], DATE_HEADS) is not None), None)
    if hi is None:
        print("STOP: no date column found in the first 15 rows. Ask the founder for a CSV export with a date column. Nothing was read.")
        return 2
    heads = [c.strip().lower() for c in rows[hi]]
    di = find(heads, DATE_HEADS)
    ai = find(heads, AMOUNT_HEADS, (di,))
    ii, oi = find(heads, IN_HEADS, (di,)), find(heads, OUT_HEADS, (di,))
    bi = find(heads, BAL_HEADS, (di, ai, ii, oi))
    de = find(heads, DESC_HEADS, (di, ai, ii, oi, bi))
    body = rows[hi + 1:]
    seen = order_of(r[di] for r in body if di < len(r))
    if "--month-first" in sys.argv:
        ORDER["v"] = "mdy"
    elif "--day-first" in sys.argv:
        ORDER["v"] = "dmy"
    elif seen:
        ORDER["v"] = seen
    elif any(re.match(r"\s*\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}", r[di]) for r in body if di < len(r)):
        print("STOP: every date in the export could be day first or month first. Run again with --day-first or "
              "--month-first (ask the founder how their bank writes 3 April). Nothing was read.")
        return 2
    money_cols = [c for c in (ai, ii, oi, bi) if c is not None]
    nums = [r[c] for r in body for c in money_cols if c < len(r) and r[c].strip()]
    if "--decimal-comma" in sys.argv:
        STYLE["decimal"] = "comma"
    elif "--decimal-point" in sys.argv:
        STYLE["decimal"] = "dot"
    else:
        STYLE["decimal"] = detect_decimal_style(nums)
    print(f"DATES: read {'month first' if ORDER['v'] == 'mdy' else 'day first'}")
    print(f"NUMBERS: decimal {'comma' if STYLE['decimal'] == 'comma' else 'point'}"
          + ("" if STYLE["decimal"] else " (no decimals seen in the export)"))
    print(f"COLUMNS: date '{heads[di]}', " + (f"amount '{heads[ai]}'" if ai is not None else f"in '{heads[ii]}', out '{heads[oi]}'")
          + (f", balance '{heads[bi]}'" if bi is not None else "") + (f", description '{heads[de]}'" if de is not None else ""))
    if ai is None and (ii is None or oi is None):
        print("STOP: no amount column, and no pair of money in and money out columns. Nothing was read.")
        return 2
    lo_arg, hi_arg = arg("--from"), arg("--to")
    recs, unread, skipped = [], [], []
    hits = {x: 0 for x in excl}
    for n, r in enumerate(body, hi + 2):
        if not any(c.strip() for c in r):
            continue
        d = dt(r[di]) if di < len(r) else None
        if d is None:
            unread.append(f"row {n}: date '{r[di] if di < len(r) else ''}'")
            continue
        desc = (r[de] if de is not None and de < len(r) else "").strip()
        if ai is not None:
            v = amt(r[ai]) if ai < len(r) else None
        else:
            vi = amt(r[ii]) if ii < len(r) else None
            vo = amt(r[oi]) if oi < len(r) else None
            v = None if vi is None and vo is None else (vi or 0.0) - abs(vo or 0.0)
        if v is None:
            unread.append(f"row {n}: amount")
            continue
        row_text = " ".join(c for i, c in enumerate(r) if i not in (ai, ii, oi, bi)).lower()
        hit = [x for x in excl if x in row_text]
        bal = amt(r[bi]) if bi is not None and bi < len(r) else None
        rec = {"n": n, "d": d, "v": v, "desc": desc, "bal": bal, "order": len(recs)}
        if hit:
            for x in hit:
                hits[x] += 1
            skipped.append(rec)
            continue
        recs.append(rec)
    if not recs and not skipped:
        print("STOP: no rows could be read. Nothing was read.")
        return 2
    allrecs = sorted(recs + skipped, key=lambda x: x["order"])
    newest_first = len(allrecs) > 1 and allrecs[0]["d"] > allrecs[-1]["d"]
    first_d = date.fromisoformat(lo_arg) if lo_arg else min(x["d"] for x in allrecs)
    last_d = date.fromisoformat(hi_arg) if hi_arg else max(x["d"] for x in allrecs)
    months = OrderedDict((k, {"in": 0.0, "out": 0.0, "rows": []}) for k in month_range(first_d, last_d))
    for x in recs:
        k = f"{x['d'].year}-{x['d'].month:02d}"
        if k in months:
            months[k]["in" if x["v"] > 0 else "out"] += abs(x["v"])
            months[k]["rows"].append(x)
    keys = list(months)
    print(f"ORDER: {'newest first' if newest_first else 'oldest first'}")
    print("Month | Money in | Money out | Net")
    for k in keys:
        mm = months[k]
        print(f"{k} | {fmt(mm['in'])} | {fmt(mm['out'])} | {fmt(mm['in'] - mm['out'])}")
    # full months: every month strictly inside the export's range; the edge months only if the range covers them
    full = [k for k in keys[1:-1]]
    if keys and first_d.day <= 3:
        full = [keys[0]] + full if len(keys) > 1 else [keys[0]]
    if len(keys) > 1 and last_d.day >= 26:
        full.append(keys[-1])
    last3 = full[-3:]
    if len(last3) == 3:
        ain = sum(months[k]["in"] for k in last3) / 3
        aout = sum(months[k]["out"] for k in last3) / 3
        print(f"AVERAGE of {', '.join(last3)}: money in {fmt(ain)} a month, money out {fmt(aout)} a month")
        freq = {}
        for x in recs:
            freq[group_key(x["desc"]).split("#")[0].strip()[:30]] = freq.get(group_key(x["desc"]).split("#")[0].strip()[:30], 0) + 1
        rare = [x for k in last3 for x in months[k]["rows"] if x["v"] < 0 and -x["v"] >= 0.1 * aout
                and freq.get(group_key(x["desc"]).split("#")[0].strip()[:30], 0) <= len(keys) / 2]
        for x in sorted(rare, key=lambda x: x["v"])[:5]:
            print(f"BIG ONE-OFF OUT in the averaged months: row {x['n']}, {x['d'].isoformat()}, {fmt(x['v'])}, {x['desc'][:50]}"
                  " (a bill you also enter as a known bill is left out of the average with --exclude)")
    else:
        print(f"AVERAGE: fewer than three full months in the export ({len(full)}); ask for a longer export or use the founder's own figures")
    print("MONEY IN BY MONTH (oldest first, full months only): " + ", ".join(f"{k}: {months[k]['in']:.2f}" for k in full))
    # latest balance: the chronologically last row that carries one
    with_bal = [x for x in allrecs if x["bal"] is not None]
    if with_bal:
        last = max(with_bal, key=lambda x: (x["d"], -x["order"] if newest_first else x["order"]))
        print(f"LATEST BALANCE: {fmt(last['bal'])} on {last['d'].isoformat()} (row {last['n']}: {last['desc'][:50]})")
        later = [x for x in allrecs if x["bal"] is None and (x["d"] > last["d"] or (
            x["d"] == last["d"] and ((x["order"] < last["order"]) if newest_first else (x["order"] > last["order"]))))]
        if later:
            tot = sum(x["v"] for x in later)
            for x in later:
                print(f"AFTER IT, NO BALANCE (pending?): row {x['n']}, {x['d'].isoformat()}, {fmt(x['v'])}, {x['desc'][:50]}")
            print(f"BALANCE WITH THOSE ROWS: {fmt(last['bal'] + tot)} (ask the founder which is today's balance)")
    else:
        print("LATEST BALANCE: not in the export; ask for today's balance")
    groups = OrderedDict()
    for x in allrecs:
        if x["desc"] and TRANSFER_WORDS.search(x["desc"]):
            g = groups.setdefault(group_key(x["desc"]), {"n": 0, "in": 0.0, "out": 0.0, "eg": x["desc"][:60], "left": 0})
            g["n"] += 1
            g["in" if x["v"] > 0 else "out"] += abs(x["v"])
            g["left"] += 1 if x in skipped else 0
    for g in groups.values():
        print(f"TRANSFERS?: {g['n']} row(s) like '{g['eg']}': in {fmt(g['in'])}, out {fmt(g['out'])}"
              + (" (left out)" if g["left"] == g["n"] else ""))
    payees = OrderedDict()
    for x in recs:
        if x["v"] < 0 and x["desc"]:
            g = payees.setdefault(group_key(x["desc"]).split("#")[0].strip()[:30], {"n": 0, "out": 0.0, "eg": x["desc"][:50]})
            g["n"] += 1
            g["out"] += -x["v"]
    top = sorted((g for g in payees.values() if g["n"] >= 3), key=lambda g: -g["out"])[:6]
    for g in top:
        print(f"REGULAR OUT: {g['n']} rows like '{g['eg']}', {fmt(g['out'])} in all")
    for x in excl:
        if not hits[x]:
            print(f'WARN: nothing matched "{x}"; no rows were left out for it')
    for x in skipped:
        print(f"LEFT OUT: row {x['n']}: {x['desc'][:40]} {fmt(x['v'])}")
    for x in unread:
        print("UNREAD:", x)
    print("Money in from a bank export includes any sales tax the founder collects, owner loans and transfers; "
          "ask about each TRANSFERS? group that is not trading, and rerun with --exclude.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        sys.exit(0)
    except Exception as e:  # noqa: BLE001
        print(f"STOP: the export could not be read ({type(e).__name__}: {e}). Nothing was read.")
        sys.exit(2)
