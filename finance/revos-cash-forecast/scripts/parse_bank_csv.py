#!/usr/bin/env python3
"""Read a business bank export (CSV) into clean, dated transactions and the last balance.

Usage:
  python3 scripts/parse_bank_csv.py <export.csv> [<more.csv> ...] --out <scratch>/transactions.json
        [--map "date=Date; amount=Value; desc=Description; balance=Balance; dates=day-first; sign=as-is"]
        [--dates day-first|month-first] [--today YYYY-MM-DD]

Reads any export by its column names (or, with no header row, by its content), and knows the layouts in
references/bank-formats.md, from the US (Chase, Bank of America, Wells Fargo, American Express, Mercury),
Singapore (DBS, OCBC), Australia (Commonwealth Bank, ANZ), the UK (Barclays, HSBC, Lloyds, NatWest, Monzo,
Starling, Tide, Revolut Business) and Wise. Layouts no published source confirms are marked not verified.
Handles split money in and money out columns, signed amounts, CR and DR markers, pending and declined rows,
repeated header rows, overlapping exports, preamble lines, descriptions that run onto a second row,
newest-first files and day-first or month-first dates (read from the data; asked once when the data cannot
tell). Where the export carries a running balance, every row is checked against it; that check is what proves
the columns were read the right way round.

Exit codes:
  0  read and checked; the summary says what was read
  1  read, but something needs the founder (usually: no balance column, so the opening balance is a [NEED])
  2  STOP: nothing usable; the line says what to do
  3  ASK: the layout or the date order could not be proved from the data. The ASK lines hold one question
     for the founder; run again with --map (or --dates) once they answer. Save the MAP line in memory so it is
     never asked again.
Standard library only. No network calls.
"""
import argparse
import csv
import hashlib
import io
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cashlib import (CODES, InputError, currency_in, date_shape, iso, long_date, money, money_or_none,  # noqa: E402
                     resolve_num, set_number_style, set_style)

# ------------------------------------------------------------------ what each column can be called
SYN = {  # role: [(normalised header, priority)], higher priority wins. Headers are normalised with any
    # currency code in brackets removed first ("Amount (GBP)" and "Withdrawals (SGD)" read as amount, withdrawals).
    "date": [("datecompletedutc", 9), ("completeddate", 9), ("datecompleted", 9), ("transactiondate", 8),
             ("postingdate", 8), ("posteddate", 8), ("date", 7), ("dateutc", 7), ("bookingdate", 6), ("bookeddate", 6),
             ("txndate", 6), ("finishedon", 5), ("valuedate", 3), ("datestartedutc", 2), ("starteddate", 2),
             ("startdate", 2), ("createdon", 2)],
    "amount": [("totalamount", 3), ("amount", 8), ("value", 7), ("transactionamount", 8),
               ("netamount", 6), ("amountinaccountcurrency", 7), ("sum", 4)],
    "in": [("moneyin", 8), ("paidin", 8), ("creditamount", 8), ("credit", 7), ("credits", 7), ("receipts", 7),
           ("in", 5), ("deposit", 6), ("deposits", 7), ("paidinamount", 8), ("amountin", 8)],
    "out": [("moneyout", 8), ("paidout", 8), ("debitamount", 8), ("debit", 7), ("debits", 7), ("payments", 7),
            ("out", 5), ("withdrawal", 6), ("withdrawals", 7), ("paidoutamount", 8), ("amountout", 8)],
    "balance": [("balance", 8), ("runningbalance", 8), ("runningbal", 8), ("closingbalance", 6),
                ("ledgerbalance", 6), ("availablebalance", 3)],
    "desc": [("transactiondescription", 8), ("description", 8), ("narrative", 8), ("memo", 7), ("details", 6),
             ("transactiondetails", 7), ("particulars", 6), ("name", 5), ("counterparty", 6), ("payee", 6),
             ("merchant", 5), ("reference", 4), ("beneficiary", 4), ("payer", 4), ("payeename", 5), ("payername", 5)],
    "type": [("type", 6), ("transactiontype", 7), ("subcategory", 5), ("creditdebit", 8), ("debitcredit", 8),
             ("drcr", 8), ("crdr", 8), ("direction", 6), ("indicator", 6)],
    "state": [("state", 8), ("status", 8), ("transactionstatus", 8)],
    "fee": [("fee", 8), ("fees", 8), ("totalfees", 8)],
    "currency": [("currency", 6), ("paymentcurrency", 7), ("balancecurrency", 1)],
}
DESC_PARTS = ("name", "counterparty", "payee", "merchant", "beneficiary", "payer", "transactiondescription",
              "description", "narrative", "memo", "details", "transactiondetails", "particulars", "reference",
              "payeename", "payername")

# ------------------------------------------------------------------ known layouts (references/bank-formats.md)
# Each: name, header keys that identify it (a subset unless exact), status (starts with "not verified" when no
# published source confirms it), the role map, and optional: dates (documented order), sign ("flip" when money
# out is shown as a plus), desc (description columns, in order), currency (what the bank's accounts are held in,
# used only when the file itself names none), kind ("card" for a card account).
BANKS = [
    dict(name="Revolut Business", ident={"datestartedutc", "datecompletedutc", "description", "amount", "fee", "balance"},
         status="columns reported by an integration partner; date format not verified",
         roles={"date": "datecompletedutc", "amount": "amount", "fee": "fee", "balance": "balance", "state": "state",
                "currency": "paymentcurrency", "type": "type"}),
    dict(name="Monzo", ident={"transactionid", "date", "time", "type", "name", "emoji", "category", "amount", "currency"},
         status="columns reported in the Monzo community; day-first dates confirmed by a converter's documentation",
         roles={"date": "date", "amount": "amount", "currency": "currency", "type": "type", "balance": "balance"},
         dates="day-first"),
    dict(name="Lloyds", ident={"transactiondate", "transactiontype", "sortcode", "accountnumber", "transactiondescription",
                               "debitamount", "creditamount", "balance"},
         status="header from an open-source Lloyds parser; date order read from the data",
         roles={"date": "transactiondate", "out": "debitamount", "in": "creditamount", "balance": "balance",
                "type": "transactiontype", "desc": "transactiondescription"}, currency="GBP"),
    dict(name="Lloyds Commercial Banking", ident={"account", "date", "type", "narrative", "valuedate", "payments",
                                                  "receipts", "balance"},
         status="from Lloyds' own CSV layout guide for Commercial Banking Online",
         roles={"date": "date", "out": "payments", "in": "receipts", "balance": "balance", "type": "type",
                "desc": "narrative"}, currency="GBP"),
    dict(name="NatWest", ident={"date", "type", "description", "value", "balance", "accountname", "accountnumber"},
         status="not verified: the widely reported NatWest online banking layout",
         roles={"date": "date", "amount": "value", "balance": "balance", "type": "type", "desc": "description"},
         currency="GBP"),
    dict(name="Starling", ident={"date", "counterparty", "reference", "type", "amount", "balance", "spendingcategory"},
         status="day-first dates and the amount column confirmed by a converter's documentation; exact names not verified",
         roles={"date": "date", "amount": "amount", "balance": "balance", "type": "type"}, dates="day-first"),
    dict(name="Tide", ident={"date", "transactiondescription", "paidin", "paidout"},
         status="not verified: no public description of Tide's CSV columns was found",
         roles={"date": "date", "in": "paidin", "out": "paidout", "desc": "transactiondescription"}, currency="GBP"),
    dict(name="Barclays", ident={"number", "date", "account", "amount", "subcategory", "memo"},
         status="header confirmed by two independent write-ups",
         roles={"date": "date", "amount": "amount", "type": "subcategory", "desc": "memo"}, currency="GBP"),
    dict(name="HSBC", ident={"date", "type", "description", "amount", "balance"}, exact=True,
         status="community-reported layout; HSBC also offers a headerless download, read by inference",
         roles={"date": "date", "amount": "amount", "balance": "balance", "type": "type", "desc": "description"}),
    dict(name="Chase", ident={"details", "postingdate", "description", "amount", "type", "balance"},
         status="Posting Date and month-first dates confirmed by a converter's documentation; the other column "
                "names are community-reported",
         roles={"date": "postingdate", "amount": "amount", "balance": "balance", "type": "type", "desc": "description"},
         dates="month-first", desc=["description"], currency="USD"),
    dict(name="Bank of America", ident={"date", "description", "amount", "runningbal"},
         status="summary lines above the header and the Running Bal. column confirmed by a converter's "
                "documentation; date order read from the data",
         roles={"date": "date", "amount": "amount", "balance": "runningbal", "desc": "description"}, currency="USD"),
    dict(name="American Express", ident={"date", "description", "amount", "cardmember"},
         status="charges shown as a plus confirmed by a converter's documentation; column names not verified",
         roles={"date": "date", "amount": "amount", "desc": "description"}, sign="flip", kind="card"),
    dict(name="American Express", ident={"date", "description", "amount", "extendeddetails"},
         status="charges shown as a plus confirmed by a converter's documentation; column names not verified",
         roles={"date": "date", "amount": "amount", "desc": "description"}, sign="flip", kind="card"),
    dict(name="Mercury", ident={"dateutc", "description", "amount", "status", "sourceaccount"},
         status="not verified: Mercury's help pages describe the export but not its columns",
         roles={"date": "dateutc", "amount": "amount", "state": "status", "desc": "description"},
         desc=["description", "bankdescription"], currency="USD"),
    dict(name="DBS", ident={"transactiondate", "reference", "debitamount", "creditamount", "transactionref1"},
         status="not verified: no published description of DBS's CSV columns was found",
         roles={"date": "transactiondate", "out": "debitamount", "in": "creditamount", "type": "reference"},
         desc=["transactionref1", "transactionref2", "transactionref3"], currency="SGD"),
    dict(name="OCBC", ident={"transactiondate", "valuedate", "description", "withdrawals", "deposits"},
         status="not verified: no published description of OCBC's CSV columns was found",
         roles={"date": "transactiondate", "out": "withdrawals", "in": "deposits", "desc": "description"},
         currency="SGD"),
    dict(name="Wise", ident={"transferwiseid", "date", "amount", "currency", "description"},
         status="day-first dates, the Currency column and amounts net of fees confirmed by a converter's "
                "documentation; exact column names not verified",
         roles={"date": "date", "amount": "amount", "currency": "currency", "balance": "runningbalance",
                "desc": "description"}, dates="day-first", desc=["description", "paymentreference"]),
]
PREAMBLE_BALANCE = re.compile(r"\b(ledger balance|closing balance|current balance|ending balance|book balance)\b", re.I)

PENDING_WORDS = re.compile(r"\b(pending|authori[sz]ed|not yet cleared|uncleared|in progress|processing|reserved)\b", re.I)
DROP_WORDS = re.compile(r"\b(declined|reverted|reversed|failed|cancell?ed|rejected|refused)\b", re.I)
DONE_WORDS = re.compile(r"\b(completed?|settled|posted|booked|cleared|done)\b", re.I)
SUMMARY_ROW = re.compile(r"(balance (brought|carried) forward|opening balance|closing balance|beginning balance|"
                         r"ending balance|^total|start balance|"
                         r"end balance|statement (opening|closing))", re.I)
CREDIT_MARK = re.compile(r"^(cr|c|credit|credits|in|paid in|money in|deposit|receipt|\+)$", re.I)
DEBIT_MARK = re.compile(r"^(dr|d|debit|debits|out|paid out|money out|withdrawal|payment|-)$", re.I)


def norm(h):
    """A header as a key: lower case, letters and digits only, with any currency code in brackets removed."""
    h = re.sub(r"\(\s*(?:" + "|".join(CODES) + r")\s*\)", "", str(h or ""), flags=re.I)
    return re.sub(r"[^a-z0-9]", "", h.lower())


def stop(msg):
    raise InputError(msg)


# ------------------------------------------------------------------ reading the file
def read_text(path):
    p = Path(path)
    if not p.exists():
        stop(f"there is no file at {path}")
    raw = p.read_bytes()
    if not raw.strip():
        stop(f"{p.name} is empty. Export the transactions again and attach the new file")
    if raw[:4] == b"PK\x03\x04":
        stop(f"{p.name} is an Excel workbook, not a CSV. Open it and save as CSV, or export CSV from the bank")
    if raw[:5] == b"%PDF-":
        stop(f"{p.name} is a PDF statement. Most banks offer a CSV download on the same screen as the PDF; "
             "use that (references/bank-formats.md says where)")
    head = raw[:400].decode("latin-1", "ignore").upper()
    if "OFXHEADER" in head or "<OFX>" in head or head.startswith("!TYPE:"):
        stop(f"{p.name} is an OFX or QIF file. Choose CSV (sometimes called 'Excel' or 'spreadsheet') in the "
             "bank's export options and attach that")
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    return text


def sniff_rows(text):
    lines = [ln for ln in text.split("\n")]
    sample = "\n".join([ln for ln in lines if ln.strip()][:40])
    best, best_score = ",", -1
    for d in (",", ";", "\t", "|"):
        try:
            rows = list(csv.reader(io.StringIO(sample), delimiter=d))
        except csv.Error:
            continue
        counts = [len(r) for r in rows if any(c.strip() for c in r)]
        if not counts:
            continue
        modal = max(set(counts), key=counts.count)
        score = (counts.count(modal) / len(counts)) * (modal if modal > 1 else 0)
        if score > best_score:
            best, best_score = d, score
    if best_score <= 0:
        stop("the file has only one column, so it is not a bank transaction export. Export CSV from the bank")
    try:
        rows = list(csv.reader(io.StringIO(text), delimiter=best))
    except csv.Error as e:
        stop(f"the file could not be read as CSV ({e})")
    clean = []
    for r in rows:
        clean.append([re.sub(r"\s+", " ", c.replace("\t", " ")).strip().strip('"').strip() for c in r])
    return clean


def role_candidates(keys):
    found = {}
    for role, syns in SYN.items():
        pr = dict(syns)
        hits = [(pr[k], i) for i, k in enumerate(keys) if k in pr]
        if hits:
            found[role] = sorted(hits, reverse=True)
    return found


def find_header(rows):
    for i, r in enumerate(rows[:40]):
        keys = [norm(c) for c in r]
        cands = role_candidates(keys)
        has_date = "date" in cands
        has_amt = "amount" in cands or ("in" in cands and "out" in cands)
        if has_date and has_amt and len(cands) >= 2:
            return i, keys
    return None, None


# ------------------------------------------------------------------ mapping
def parse_map(s, keys):
    """--map 'date=Date; amount=Value; in=Paid in; out=Paid out; desc=Description; balance=Balance;
    dates=day-first; sign=flip'. Column names or 0-based positions."""
    m, opts = {}, {}
    for part in re.split(r";", s or ""):
        if "=" not in part:
            continue
        k, v = [x.strip() for x in part.split("=", 1)]
        k = k.lower()
        if k in ("dates", "sign"):
            opts[k] = v.lower()
            continue
        if k == "description":
            k = "desc"
        if k not in SYN:
            stop(f"--map has an unknown part '{k}'. Use date, amount, in, out, desc, balance, type, state, fee")
        if re.fullmatch(r"\d+", v):
            idx = int(v)
        else:
            nv = norm(v)
            if keys is None:
                stop("this file has no header row, so name the columns by position in --map, counting from 0 "
                     "(for example: date=0; desc=1; amount=2)")
            if nv not in keys:
                stop(f"--map names a column '{v}' that is not in the file's header. If the map came from memory, the "
                     "bank has changed its layout: run again without --map and save the new MAP line")
            idx = keys.index(nv)
        m[k] = idx
    return m, opts


def auto_map(keys):
    cands = role_candidates(keys)
    m, ambiguous = {}, []
    for role, hits in cands.items():
        m[role] = hits[0][1]
        if len(hits) > 1 and hits[0][0] == hits[1][0] and role in ("date", "amount", "balance"):
            ambiguous.append(f"two columns could be the {role}: {keys[hits[0][1]]} and {keys[hits[1][1]]}")
    used = set(v for k, v in m.items() if k != "desc")
    desc_cols = [i for i, k in enumerate(keys) if k in DESC_PARTS and i not in used]
    m["desc_cols"] = desc_cols or ([m["desc"]] if "desc" in m else [])
    if len(cands.get("date", [])) > 1:
        m["date_alt"] = cands["date"][1][1]
    if "totalamount" in keys:
        m["total"] = keys.index("totalamount")
        if keys[m.get("amount", -1)] == "totalamount" and "amount" in keys:
            m["amount"] = keys.index("amount")
    return m, ambiguous


def known_bank(keys):
    ks = set(k for k in keys if k)
    for b in BANKS:
        ident = b["ident"]
        if (ks == ident) if b.get("exact") else ident <= ks:
            m = {}
            for role, key in b["roles"].items():
                if key in keys:
                    m[role] = keys.index(key)
            auto, _amb = auto_map(keys)
            for role in ("state", "currency", "fee", "balance", "type", "date_alt"):
                if role not in m and role in auto:
                    m[role] = auto[role]
            if "total" in auto:
                m["total"] = auto["total"]
            if b.get("desc"):
                m["desc_cols"] = [keys.index(k) for k in b["desc"] if k in keys]
            else:
                m["desc_cols"] = [i for i, k in enumerate(keys) if k in DESC_PARTS and i not in m.values()]
                if "desc" in m and m["desc"] not in m["desc_cols"]:
                    m["desc_cols"].insert(0, m["desc"])
            return b, m
    return None, None


def headerless_map(rows):
    """No header: infer the date, amount and balance columns from the content."""
    data = [r for r in rows if any(c for c in r)][:200]
    width = max(len(r) for r in data)

    def vals(col):
        return [r[col] for r in data if col < len(r) and r[col] != ""]

    def share(col, fn):
        v = vals(col)
        return (sum(1 for x in v if fn(x)) / len(data)) if v else 0
    date_cols = [c for c in range(width) if share(c, lambda v: date_shape(v) is not None) >= 0.8]
    num_cols = [c for c in range(width) if c not in date_cols and share(c, lambda v: money_or_none(v) is not None) >= 0.6]
    # text columns that say something: not empty, not one repeated marker (Wells Fargo's '*' column)
    text_cols = [c for c in range(width) if c not in date_cols and c not in num_cols and len(set(vals(c))) > 2]
    text_cols.sort(key=lambda c: -sum(len(x) for x in vals(c)))
    if not date_cols or not num_cols:
        return None
    m = {"date": date_cols[0], "desc_cols": sorted(text_cols[:2])}
    if len(num_cols) == 1:
        m["amount"] = num_cols[0]
    elif len(num_cols) >= 2:
        m["amount"], m["balance"] = num_cols[0], num_cols[1]
        if len(num_cols) >= 3:
            m["in"], m["out"] = num_cols[0], num_cols[1]
            m.pop("amount")
            m["balance"] = num_cols[2]
            m["_guess_split"] = True
    return m


def preamble_balance(rows):
    """A ledger or closing balance printed above the header (DBS, OCBC and others do this)."""
    for r in rows:
        joined = " ".join(r)
        if PREAMBLE_BALANCE.search(joined) and not re.search(r"available", joined, re.I):
            for c in r:
                v = money_or_none(re.sub(r"[A-Za-z:]", "", c)) if re.search(r"\d", c) else None
                if v is not None and not date_shape(c):
                    return {"balance": v, "label": PREAMBLE_BALANCE.search(joined).group(1).lower(),
                            "currency": currency_in(joined)}
    return None


# ------------------------------------------------------------------ the read
def read_file(path, map_str=None):
    text = read_text(path)
    rows = sniff_rows(text)
    hi, keys = find_header(rows)
    seg = {"file": Path(path).name, "preamble": 0, "header": None, "bank": None, "status": None, "map": None,
           "ambiguous": [], "headerless": False, "body": [], "layout": {}, "pre_balance": None}
    if hi is None:
        hm = headerless_map(rows)
        if map_str:
            m, opts = parse_map(map_str, None)
            m.setdefault("desc_cols", [i for i in range(max(len(r) for r in rows)) if i not in m.values()][:2])
            seg.update(map=m, opts=opts, headerless=True, status="mapped by the founder", body=rows)
            return seg
        if not hm:
            first = next((r for r in rows if any(c for c in r)), [])
            if first and all(date_shape(c) is None and money_or_none(c) is None for c in first if c):
                stop(f"{Path(path).name} has the columns {', '.join(c for c in first if c)[:120]}, but no date and amount "
                     "columns a bank export would have. It does not look like bank transactions; attach the CSV from "
                     "the bank's transactions screen")
            stop(f"{Path(path).name} has no header row and no column that reads as dates and amounts. "
                 "It may not be a transaction export; attach the CSV from the bank's transactions screen")
        seg.update(map=hm, headerless=True, status="inferred from the content (no header row)", body=rows, opts={})
        return seg
    seg["preamble"] = hi
    seg["header"] = rows[hi]
    seg["pre_balance"] = preamble_balance(rows[:hi])
    seg["header_currency"] = next((currency_in(c) for c in rows[hi] if currency_in(c)), None)
    if map_str:
        m, opts = parse_map(map_str, keys)
        if "desc" in m and "desc_cols" not in m:
            m["desc_cols"] = [m["desc"]]
        m.setdefault("desc_cols", [i for i, k in enumerate(keys) if k in DESC_PARTS and i not in m.values()])
        b, _m = known_bank(keys)
        seg.update(map=m, opts=opts, status="columns as confirmed and saved", layout=b or {},
                   bank=(b or {}).get("name") or "your bank (saved layout)")
    else:
        b, m = known_bank(keys)
        if b:
            seg.update(bank=b["name"], status=b["status"], map=m, opts={}, layout=b)
        else:
            m, amb = auto_map(keys)
            seg.update(bank=None, status="read by its column names (not a layout this skill knows)", map=m,
                       ambiguous=amb, opts={})
    seg["keys"] = keys
    seg["body"] = rows[hi + 1:]
    return seg


def _trim(xs):
    while xs and xs[-1] == "":
        xs = xs[:-1]
    return xs


def cell(r, i):
    return r[i] if i is not None and i < len(r) else ""


def rows_to_records(seg):
    m, keys = seg["map"], seg.get("keys")
    recs, skipped = [], {"repeat_header": 0, "blank": 0, "no_date": 0, "summary": 0, "no_amount": 0, "continuation": 0}
    samples = []
    money_cols = [m.get(k) for k in ("amount", "in", "out", "balance") if m.get(k) is not None]
    for r in seg["body"]:
        if not any(c for c in r):
            skipped["blank"] += 1
            continue
        if keys and _trim([norm(c) for c in r]) == _trim(list(keys)):
            skipped["repeat_header"] += 1
            recs.append({"_segment_break": True})
            continue
        d_raw = cell(r, m.get("date"))
        shape = date_shape(d_raw)
        if shape is None and not d_raw and m.get("date_alt") is not None:
            d_raw = cell(r, m.get("date_alt"))  # e.g. a pending row with no completed date yet
            shape = date_shape(d_raw)
        parts = {}
        for i in m.get("desc_cols", []):
            x = cell(r, i)
            if x and x.lower() not in parts:
                parts[x.lower()] = x
        desc = " ".join(parts.values()).strip()
        if shape is None:
            joined = " ".join(r)
            if SUMMARY_ROW.search(joined):
                skipped["summary"] += 1
            elif (not d_raw and desc and recs and "shape" in recs[-1]
                  and not any(cell(r, i) for i in money_cols)):
                recs[-1]["desc"] = (recs[-1]["desc"] + " " + desc).strip()[:240]  # description on a second row
                skipped["continuation"] += 1
            else:
                skipped["no_date"] += 1
                if len(samples) < 3:
                    samples.append(", ".join(r)[:80])
            continue
        if SUMMARY_ROW.search(desc) and not (cell(r, m.get("amount")) or cell(r, m.get("in")) or cell(r, m.get("out"))):
            skipped["summary"] += 1
            continue
        rec = {"shape": shape, "raw_date": d_raw, "desc": desc[:240],
               "type": cell(r, m.get("type")), "state": cell(r, m.get("state")),
               "currency": cell(r, m.get("currency")),
               "amount_raw": cell(r, m.get("amount")), "total_raw": cell(r, m.get("total")),
               "in_raw": cell(r, m.get("in")), "out_raw": cell(r, m.get("out")),
               "fee_raw": cell(r, m.get("fee")), "balance_raw": cell(r, m.get("balance"))}
        recs.append(rec)
    return recs, skipped, samples


def decide_day_first(recs, forced=None, documented=None):
    """Returns (day_first or None when it cannot be told, note). Read from the data; never from a country."""
    nums = [r["shape"][1] for r in recs if "shape" in r and r["shape"][0] == "num"]
    if not nums:
        return True, None
    if forced in ("day-first", "dmy"):
        return True, "read day first, as you confirmed"
    if forced in ("month-first", "mdy"):
        return False, "read month first, as you confirmed"
    a_big = any(a > 12 for a, _b, _y in nums)
    b_big = any(b > 12 for _a, b, _y in nums)
    if a_big and b_big:
        stop("the dates in this file are written two different ways (some day first, some month first). "
             "Export it again from the bank without editing it in a spreadsheet")
    if a_big:
        return True, None
    if b_big:
        return False, None

    def monotonic(day_first):
        ds = []
        for p in nums:
            try:
                ds.append(resolve_num(p, day_first))
            except ValueError:
                return False
        return ds == sorted(ds) or ds == sorted(ds, reverse=True)
    if len({(a, b) for a, b, _y in nums}) == len({(a, b) for a, b, _y in nums if a == b}):
        return True, None  # every date has day equal to month: either reading is the same
    dm, md = monotonic(True), monotonic(False)
    if md and not dm:
        return False, "every date could be read either way; read month first because only that keeps them in order"
    if dm and not md:
        return True, "every date could be read either way; read day first because only that keeps them in order"
    if documented:
        return documented == "day-first", f"every date could be read either way; read {documented.replace('-', ' ')}, as this bank writes them"
    return None, None


def amounts(recs, seg):
    """Turn the raw cells into one signed amount per row (money in positive)."""
    m = seg["map"]
    notes = []
    has_amount = "amount" in m
    has_split = "in" in m and "out" in m

    def col_negative_share(key):
        vals = [money_or_none(r[key]) for r in recs if "shape" in r and r[key]]
        vals = [v for v in vals if v]
        return (sum(1 for v in vals if v < 0) / len(vals)) if vals else 0.0

    out_neg = col_negative_share("out_raw") > 0.5 if has_split else False
    in_neg = col_negative_share("in_raw") > 0.5 if has_split else False
    amt_has_negative = any((money_or_none(r["amount_raw"]) or 0) < 0 for r in recs if "shape" in r) if has_amount else False
    use_marker = has_amount and not amt_has_negative and "type" in m and any(
        CREDIT_MARK.match(r["type"] or "") or DEBIT_MARK.match(r["type"] or "") for r in recs if "shape" in r)
    if has_amount and not amt_has_negative and not use_marker and not has_split:
        seg["unsigned"] = True
    for r in recs:
        if "shape" not in r:
            continue
        a = None
        if has_amount:
            a = money_or_none(r["amount_raw"])
            if a is not None and use_marker:
                t = (r["type"] or "").strip()
                if DEBIT_MARK.match(t):
                    a = -abs(a)
                elif CREDIT_MARK.match(t):
                    a = abs(a)
        if a is None and has_split:
            vi, vo = money_or_none(r["in_raw"]), money_or_none(r["out_raw"])
            if vi is not None or vo is not None:
                vi = (vi or 0.0) if not in_neg else -(vi or 0.0)
                vo = (vo or 0.0)
                vo = -vo if out_neg else vo
                a = vi - vo
        r["amount"] = a
        r["fee"] = money_or_none(r["fee_raw"]) or 0.0
        r["total"] = money_or_none(r["total_raw"])
        r["balance"] = money_or_none(r["balance_raw"])
    if use_marker:
        notes.append("amounts carry no minus sign, so money in and out were read from the CR and DR markers")
    if has_split:
        notes.append("money in and money out sit in separate columns; combined into one figure per row")
    return notes


def reconcile(chrono, fee_mode):
    checked = matched = 0
    prev = None
    for r in chrono:
        if r.get("balance") is None:
            continue
        if prev is not None:
            checked += 1
            if abs(prev + effective(r, fee_mode) - r["balance"]) < 0.011:
                matched += 1
        prev = r["balance"]
    return checked, matched


def effective(r, fee_mode):
    a = r["amount"]
    if fee_mode == "total" and r.get("total") is not None:
        return r["total"]
    if fee_mode == "minus" and r.get("fee"):
        return a - abs(r["fee"])
    if fee_mode == "plus" and r.get("fee"):
        return a + r["fee"]
    return a


def build(paths, map_str=None, today=None, dates_opt=None):
    segs = [read_file(p, map_str) for p in paths]
    sigs = {tuple(s.get("keys") or ()) for s in segs}
    if len(sigs) > 1:
        names = ", ".join(f"{s['file']} ({s['bank'] or 'unknown layout'})" for s in segs)
        stop(f"these files have different layouts, so they look like different accounts: {names}. "
             "Forecast one account at a time: attach the main business account's exports only")
    opts = dict(segs[0].get("opts", {}) or {})
    if dates_opt:
        opts["dates"] = dates_opt
    seg0 = segs[0]
    layout = seg0.get("layout") or {}
    notes, asks = [], []
    all_recs, skipped_total, samples = [], {}, []
    for si, s in enumerate(segs):
        recs, skipped, smp = rows_to_records(s)
        samples += smp
        for k, v in skipped.items():
            skipped_total[k] = skipped_total.get(k, 0) + v
        segno = si * 1000
        for r in recs:
            if r.get("_segment_break"):
                segno += 1
                continue
            r["segment"] = segno
            all_recs.append(r)
    if not all_recs:
        stop("no transactions were found in the file. Check it is the transactions export, not a summary or a statement list")
    day_first, dnote = decide_day_first(all_recs, opts.get("dates"), layout.get("dates"))
    date_unsure = day_first is None
    if date_unsure:
        day_first = True  # provisional, only so the rows can be shown back; the founder is asked (exit 3)
    if dnote:
        notes.append(dnote)
    set_style(month_first=(day_first is False) and not date_unsure)
    for r in all_recs:
        sh = r["shape"]
        try:
            r["date"] = sh[1] if sh[0] == "fixed" else resolve_num(sh[1], day_first)
        except ValueError:
            stop(f"'{r['raw_date']}' is not a real date when read {'day' if day_first else 'month'} first")
    notes += amounts(all_recs, seg0)
    no_amt = [r for r in all_recs if r["amount"] is None]
    skipped_total["no_amount"] = skipped_total.get("no_amount", 0) + len(no_amt)
    recs = [r for r in all_recs if r["amount"] is not None]
    if not recs:
        stop("no row has an amount that reads as money. The amount column may be missing from the export")

    # currency: a currency column, a code in the header, codes in the cells, then the bank's own currency
    curs = {}
    for r in recs:
        c = (r.get("currency") or "").upper().strip()
        if c:
            curs[c] = curs.get(c, 0) + 1
    currency, cur_source = None, None
    if curs:
        currency = max(curs, key=curs.get)
        cur_source = "from the export's currency column"
        if len(curs) > 1:
            n_other = sum(v for k, v in curs.items() if k != currency)
            recs = [r for r in recs if (r.get("currency") or currency).upper() == currency]
            notes.append(f"{n_other} row(s) in other currencies were left out; this forecast is in {currency}")
    elif seg0.get("header_currency"):
        currency, cur_source = seg0["header_currency"], "from the export's column names"
    else:
        cell_cur = {}
        for r in recs[:200]:
            c = currency_in(r["amount_raw"] or r["in_raw"] or r["out_raw"] or "")
            if c:
                cell_cur[c] = cell_cur.get(c, 0) + 1
        if cell_cur:
            currency, cur_source = max(cell_cur, key=cell_cur.get), "from the amounts in the export"
        elif (seg0.get("pre_balance") or {}).get("currency"):
            currency, cur_source = seg0["pre_balance"]["currency"], "from the balance line at the top of the export"
        elif layout.get("currency"):
            currency, cur_source = layout["currency"], (f"a guess from the layout: {layout['name']} accounts are usually "
                                                         f"in {layout['currency']}; confirm it with the founder")

    # pending and declined rows
    pending, dropped_state = [], 0
    has_bal_col = "balance" in seg0["map"]
    kept = []
    for r in recs:
        st = " ".join([r.get("state") or "", r.get("type") or ""])
        text = st + " " + (r.get("desc") or "")
        if DROP_WORDS.search(st) or (not r.get("state") and DROP_WORDS.search(r.get("desc") or "")
                                     and re.search(r"\bdeclined\b", r.get("desc") or "", re.I)):
            dropped_state += 1
            continue
        is_pending = bool(r.get("state")) and PENDING_WORDS.search(r["state"]) and not DONE_WORDS.search(r["state"])
        if not r.get("state") and PENDING_WORDS.search(text):
            is_pending = True
        if is_pending:
            pending.append(r)
            continue
        kept.append(r)
    if has_bal_col:
        with_bal = sum(1 for r in kept if r["balance"] is not None)
        if with_bal >= max(3, int(0.8 * len(kept))):
            nb = [r for r in kept if r["balance"] is None]
            if nb and len(nb) <= max(3, len(kept) // 10):
                pending += nb
                kept = [r for r in kept if r["balance"] is not None]
                notes.append(f"{len(nb)} row(s) had no balance while every other row did; treated as not yet cleared")
    recs = kept

    # chronological order, segment by segment
    chrono = []
    for segno in sorted({r["segment"] for r in recs}):
        part = [r for r in recs if r["segment"] == segno]
        if len(part) > 1 and part[0]["date"] > part[-1]["date"]:
            part = part[::-1]
        chrono.append(part)
    # overlapping exports and repeated rows
    seen_keys, merged, overlap, dup_same = set(), [], 0, 0
    for part in chrono:
        keys_here = []
        for r in part:
            k = (r["date"], round(r["amount"], 2), re.sub(r"\W", "", (r["desc"] or "").lower()),
                 None if r["balance"] is None else round(r["balance"], 2))
            if k in seen_keys:
                overlap += 1
                continue
            if k in keys_here and k[3] is not None:
                dup_same += 1
                continue
            keys_here.append(k)
            merged.append(r)
        seen_keys.update(keys_here)
    merged.sort(key=lambda r: r["date"])  # stable: keeps each day's order
    identical = 0
    if not has_bal_col:
        ks = [(r["date"], round(r["amount"], 2), r["desc"]) for r in merged]
        identical = len(ks) - len(set(ks))

    # running balance check: proves the sign convention and the row order
    variants = []
    fee_modes = ["none"]
    if "fee" in seg0["map"] or any(r.get("total") is not None for r in merged):
        fee_modes = ["none", "minus", "plus", "total"]
    for flip in (False, True):
        for intraday in ("as-is", "reversed"):
            for fm in fee_modes:
                rows = [dict(r, amount=-r["amount"] if flip else r["amount"]) for r in merged]
                if intraday == "reversed":
                    rows = regroup(rows)
                c, mt = reconcile(rows, fm)
                variants.append((mt / c if c else 0, c, flip, intraday, fm, rows))
    variants.sort(key=lambda v: (v[0], v[2] is False, v[3] == "as-is", v[4] == "none"), reverse=True)
    rate, checked, flip, intraday, fee_mode, chosen = variants[0]
    want_flip = opts.get("sign") == "flip" or (opts.get("sign") is None and layout.get("sign") == "flip")
    if checked == 0:
        chosen = merged
        flip, intraday, fee_mode = want_flip, "as-is", "none"
        if flip:
            chosen = [dict(r, amount=-r["amount"]) for r in merged]
            notes.append(f"{layout.get('name', 'this export')} shows money out as a plus; every sign was turned round"
                         if opts.get("sign") is None else "every sign was turned round, as you confirmed")
    elif opts.get("sign") == "flip" and not flip:
        chosen = [dict(r, amount=-r["amount"]) for r in merged]
        flip = True
    if flip and checked and rate >= 0.9 and opts.get("sign") != "flip":
        notes.append("the amounts run the other way from the balance (money out shown as a plus); every sign "
                     "was turned round so the balance adds up")
    if fee_mode in ("minus", "plus") and checked and rate >= 0.9:
        notes.append("card and transfer fees sit in their own column; taken off each payment so the balance adds up")
    elif fee_mode == "total" and checked and rate >= 0.9:
        notes.append("used the total amount column, which includes fees, because that is what moves the balance")
    elif "fee" in seg0["map"] and not checked:
        notes.append("fees sit in their own column and there is no balance to check them against; fees were taken off each payment")
        chosen = [dict(r, amount=effective(r, "minus")) for r in chosen]
    if fee_mode != "none" and checked:
        chosen = [dict(r, amount=effective(r, fee_mode)) for r in chosen]

    # opening balance: the last balance in the export, else a ledger balance printed above the header
    opening = None
    last_bal = None
    for i in range(len(chosen) - 1, -1, -1):
        if chosen[i]["balance"] is not None:
            last_bal = i
            break
    if last_bal is not None:
        after = chosen[last_bal + 1:]
        bal = chosen[last_bal]["balance"] + sum(r["amount"] for r in after)
        opening = {"balance": round(bal, 2), "date": iso(chosen[-1]["date"]),
                   "source": f"last balance in the export, {long_date(chosen[last_bal]['date'])}"
                   + (f", plus {len(after)} later row(s) without a balance" if after else "")}
    elif seg0.get("pre_balance") and not len(segs) > 1:
        pb = seg0["pre_balance"]
        opening = {"balance": round(pb["balance"], 2), "date": iso(chosen[-1]["date"]),
                   "source": f"the {pb['label']} printed at the top of the export, read as at its last transaction "
                             f"({long_date(chosen[-1]['date'])})"}
        notes.append(f"the opening balance is the {pb['label']} at the top of the file; the export has no running "
                     "balance, so the rows cannot be checked against it")

    first, last = chosen[0]["date"], chosen[-1]["date"]
    days = (last - first).days + 1
    status = seg0["status"]
    proved = (checked >= 3 and rate >= 0.9) or (checked >= 2 and rate == 1.0)
    if checked >= 3 and rate < 0.9:
        notes.append(f"the balance column adds up on only {round(rate * 100)}% of rows; the opening balance is still "
                     "the bank's own last figure, but check the columns below")
    if date_unsure:
        notes.append("every date in this file could be day first or month first, and the order of the rows "
                     "does not settle it")
    needs_ask = False
    if map_str:
        needs_ask = False
    elif seg0["headerless"] and not proved:
        needs_ask = True
        asks.append("This export has no column names, so I worked them out from the content.")
    elif seg0.get("ambiguous"):
        needs_ask = True
        asks += seg0["ambiguous"]
    elif layout.get("kind") == "card":
        needs_ask = True
        asks.append(f"This looks like {'an' if layout['name'][0] in 'AEIOU' else 'a'} {layout['name']} card export, not a bank account. A cash forecast runs on the "
                    "bank account the card bill is paid from, where the card shows as one regular payment. Attach that "
                    "export instead, or say 'use this card' and I will forecast the card on its own.")
    elif seg0.get("unsigned") and not proved and not want_flip:
        needs_ask = True
        asks.append("Every amount in this file is a plus figure and there is no balance to tell money in from money out.")
    elif not seg0["bank"] and not proved:
        needs_ask = True
        asks.append("I do not know this layout and there is no running balance to prove I read it right.")
    elif seg0["bank"] and status.startswith("not verified") and not proved:
        needs_ask = True
        asks.append(f"This looks like {'an' if seg0['bank'][0] in 'AEIOU' else 'a'} {seg0['bank']} export, a layout I could not check against a published "
                    "source, and there is no running balance to prove it.")
    date_ask = date_unsure and not opts.get("dates")
    if skipped_total.get("continuation"):
        notes.append(f"{skipped_total['continuation']} description(s) ran onto a second row and were joined to the row above")
    if days < 28:
        notes.append(f"the export covers {days} days; monthly bills that did not fall in that window will be missed, "
                     "so three months gives the best read")
    if today and (today - last).days > 10:
        notes.append(f"the export ends on {long_date(last)}, {(today - last).days} days ago; anything paid since is "
                     "not in the opening balance")
    if identical:
        notes.append(f"{identical} pair(s) of identical rows (same day, amount and description) were kept: they may be "
                     "two real payments; the export has no balance to tell")
    out = {
        "files": [s["file"] for s in segs], "bank": seg0["bank"] or ("headerless" if seg0["headerless"] else "unknown layout"),
        "format_status": status, "proved_by_balance": proved, "account_kind": layout.get("kind") or "bank",
        "header": seg0.get("header"), "mapping": describe_map(seg0), "map_string": map_string(seg0, None if (date_ask or not any(r["shape"][0] == "num" for r in all_recs))
                                 else day_first, flip),
        "header_signature": hashlib.sha1("|".join(seg0.get("keys") or ["headerless"]).encode()).hexdigest()[:10],
        "date_order": (None if date_ask else ("day-first" if day_first else "month-first")) if any(
            r["shape"][0] == "num" for r in all_recs) else None,
        "date_order_source": ("asked" if date_ask else ("read from the data" if any(r["shape"][0] == "num" for r in all_recs)
                                                         else "the export writes months as names or year first")),
        "sign_flipped": flip, "fee_mode": fee_mode,
        "currency": currency, "currency_source": cur_source,
        "number_style": number_style(all_recs),
        "range": {"first": iso(first), "last": iso(last), "days": days},
        "opening": opening, "reconciliation": {"checked": checked, "matched": round(rate * checked)},
        "dropped": {"declined_or_reversed": dropped_state, "repeated_header_rows": skipped_total.get("repeat_header", 0),
                    "overlapping_rows": overlap, "duplicate_rows_same_balance": dup_same,
                    "rows_without_a_date": skipped_total.get("no_date", 0),
                    "balance_or_total_lines": skipped_total.get("summary", 0),
                    "rows_without_an_amount": skipped_total.get("no_amount", 0),
                    "preamble_lines": sum(s["preamble"] for s in segs)},
        "undated_samples": samples,
        "pending": [{"date": iso(r["date"]), "amount": round(r["amount"], 2), "description": r["desc"]} for r in pending],
        "transactions": [{"date": iso(r["date"]), "amount": round(r["amount"], 2), "description": r["desc"],
                          "type": r.get("type") or "", "balance": r["balance"]} for r in chosen],
        "notes": notes, "asks": asks, "date_ask": date_ask,
        "status": "ask" if (needs_ask or date_ask) else ("need" if not opening else "ok"),
        "preview": [r for r in (segs[0]["body"][:3])],
    }
    return out


def regroup(rows):
    out, i = [], 0
    while i < len(rows):
        j = i
        while j < len(rows) and rows[j]["date"] == rows[i]["date"]:
            j += 1
        out += rows[i:j][::-1]
        i = j
    return out


def describe_map(seg):
    m, hdr = seg["map"], seg.get("header")

    def nm(i):
        if i is None:
            return None
        return hdr[i] if hdr and i < len(hdr) else f"column {i + 1}"
    d = {k: nm(m.get(k)) for k in ("date", "amount", "in", "out", "balance", "type", "state", "fee", "currency") if k in m}
    d["description"] = [nm(i) for i in m.get("desc_cols", [])]
    return d


def map_string(seg, day_first, flip):
    m, hdr = seg["map"], seg.get("header")
    parts = []
    for k in ("date", "amount", "in", "out", "balance", "type", "state", "fee"):
        if k in m and m[k] is not None:
            parts.append(f"{k}={hdr[m[k]] if hdr else m[k]}")
    if m.get("desc_cols"):
        parts.append(f"desc={hdr[m['desc_cols'][0]] if hdr else m['desc_cols'][0]}")
    if day_first is not None:
        parts.append(f"dates={'day-first' if day_first else 'month-first'}")
    parts.append(f"sign={'flip' if flip else 'as-is'}")
    return "; ".join(parts)


def number_style(recs):
    """How the export writes its figures (group and decimal marks), so the forecast can write them back the same way
    when the founder has typed none of their own."""
    group = dec = None
    for r in recs:
        for k in ("amount_raw", "in_raw", "out_raw", "balance_raw"):
            v = str(r.get(k) or "").strip()
            if not re.search(r"\d", v):
                continue
            if re.search(r"\d[ \u00a0\u202f]\d{3}(?!\d)", v):
                group = group or " "
            elif re.search(r"\d\.\d{3}(?!\d)", v) and re.search(r",\d{1,2}$", v):
                group = group or "."
            elif re.search(r"\d,\d{3}(?!\d)", v):
                group = group or ","
            if re.search(r",\d{2}\s*(?:cr|dr|-)?$", v, re.I) and not re.search(r",\d{3}", v):
                dec = dec or ","
            elif re.search(r"\.\d{2}\s*(?:cr|dr|-)?$", v, re.I):
                dec = dec or "."
        if group and dec:
            break
    return {"group": group, "decimal": dec}


def print_summary(o, out_path):
    cur = o["currency"]
    ns = o.get("number_style") or {}
    set_number_style(ns.get("group"), ns.get("decimal"))
    tx = o["transactions"]
    print(f"BANK: {o['bank']} ({o['format_status']})")
    print(f"READ: {len(tx)} transactions, {o['range']['first']} to {o['range']['last']} ({o['range']['days']} days)")
    mp = o["mapping"]
    cols = ", ".join(f"{k}: {v}" for k, v in mp.items() if v and k != "description")
    print(f"COLUMNS: {cols}; description from {', '.join(x for x in mp.get('description', []) if x) or 'none'}")
    if o.get("date_ask"):
        print("DATES: not settled from the data: ask once (see ASK below)")
    else:
        print(f"DATES: {o['date_order'] or 'no day and month order to settle'} ({o['date_order_source']})")
    if cur:
        print(f"CURRENCY: {cur} ({o['currency_source']})")
    else:
        print("CURRENCY: not shown in the export. Ask the founder which currency the account is in, in the same "
              "message as the other questions, and put it in the inputs as currency")
    rec = o["reconciliation"]
    if rec["checked"]:
        print(f"BALANCE CHECK: {rec['matched']} of {rec['checked']} rows add up to the running balance")
    else:
        print("BALANCE CHECK: no running balance in this export")
    if o["opening"]:
        print(f"OPENING BALANCE: {money(o['opening']['balance'], cur, pence=True)} on {o['opening']['date']} ({o['opening']['source']})")
    else:
        print("NEED: the export has no balance. Ask: 'What was the balance in this account at the end of "
              f"{long_date(o['range']['last'])}, or today?' and put it in the forecast inputs as the opening balance")
    total_in = sum(t["amount"] for t in tx if t["amount"] > 0)
    total_out = -sum(t["amount"] for t in tx if t["amount"] < 0)
    print(f"MONEY IN: {money(total_in, cur)}; MONEY OUT: {money(total_out, cur)}")
    d = {k: v for k, v in o["dropped"].items() if v}
    if d:
        print("LEFT OUT: " + "; ".join(f"{v} {k.replace('_', ' ')}" for k, v in d.items()))
    if o["pending"]:
        print(f"PENDING (not in the balance, not counted): {len(o['pending'])} row(s), "
              + "; ".join(f"{p['date']} {money(p['amount'], cur, pence=True)} {p['description'][:30]}" for p in o["pending"][:5]))
    for n in o["notes"]:
        print("NOTE:", n)
    print(f"MAP: {o['map_string']}")
    if o["status"] == "ask":
        for a in o["asks"]:
            print("ASK:", a)
        if o.get("date_ask"):
            amb = next((t for t in tx if t["date"][5:7] != t["date"][8:10]), tx[0])
            print(f"ASK: Your dates could be read either way (is {amb['date'][8:10]}/{amb['date'][5:7]} day then month, or "
                  "month then day?). Do you write dates day first (31/10) or month first (10/31)? Run again with "
                  "--dates day-first or --dates month-first, and save the answer.")
        if o["asks"]:
            sample = o["transactions"][:3]
            example = "; ".join(f"{long_date(t['date'])} {money(t['amount'], cur, pence=True)} {t['description'][:25]}" for t in sample)
            print(f"ASK: Here is how I read the first rows: {example}. Is money out shown as a minus, and are these the "
                  "right dates and amounts? Answer yes, or tell me which column is which.")
            print("ASK: Once answered, run again with --map (edit the MAP line above) and save that MAP line in memory.")
    print(f"WROTE: {out_path}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--map")
    ap.add_argument("--dates", choices=["day-first", "month-first"])
    ap.add_argument("--today")
    a = ap.parse_args()
    today = date.fromisoformat(a.today) if a.today else date.today()
    o = build(a.files, a.map, today, a.dates)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(o, indent=2, default=str), encoding="utf-8")
    print_summary(o, a.out)
    sys.exit({"ok": 0, "need": 1, "ask": 3}[o["status"]])


if __name__ == "__main__":
    try:
        main()
    except InputError as e:
        print(f"STOP: {e}. Nothing was written.")
        sys.exit(2)
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print(f"STOP: the export could not be read ({type(e).__name__}: {e}). Nothing was written; "
              "attach the CSV exactly as the bank gave it, or say which bank it came from.")
        sys.exit(2)
