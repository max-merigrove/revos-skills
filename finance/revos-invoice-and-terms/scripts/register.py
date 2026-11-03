#!/usr/bin/env python3
"""The invoice register: every number issued, what is owed and by when, billing plans, gaps and voids.

Usage (paths relative to this skill's folder):
  python3 scripts/register.py build --plan <plan.json> [--history <history.json>] --out "<folder>/Invoice register.xlsx"
        adds this run's document and billing plan to the history and writes the workbook (live formulas for
        balance, days late and the summary). Without openpyxl it writes "Invoice register.csv" instead.
        Also writes the merged history next to --history (or beside the workbook) for the memory file.
  python3 scripts/register.py read <Invoice register.xlsx or .csv> --out <history.json>
  python3 scripts/register.py update --history <history.json> [--paid "NUMBER=DATE[=AMOUNT]"] [--void "NUMBER=REASON"]
        [--issued NUMBER] --today YYYY-MM-DD
        marks money received (in the account, not promised), records a voided number with its reason, or marks a
        draft as issued once the founder sends it.
Exit 0 done, 2 STOP. Standard library only, plus openpyxl when present (CSV otherwise). No network calls.
"""
import argparse
import csv
import json
import os
import re
import sys
from datetime import date
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402
import dates as D  # noqa: E402
import locale_numbers as LN  # noqa: E402

REG_COLS = ["Number", "Type", "Client", "Project", "Issue date", "Due date", "Currency", "Net", "Tax", "Total", "Paid",
            "Balance", "Status", "Paid date", "Days late", "PO or reference", "File"]
PLAN_COLS = ["Plan", "Client", "Currency", "Project total", "Stage", "Label", "Share", "Trigger", "Planned date",
             "Stage total", "Number", "Issue date", "Status", "Paid date"]
STATUSES = ["draft", "issued", "part paid", "paid", "overdue", "void", "credited"]


def money_dec(minor, code):
    return Decimal(int(minor)).scaleb(-C.minor_units(code))


def to_minor_plain(v, code):
    if v in (None, ""):
        return 0
    return C.to_minor(Decimal(str(v).replace(",", "")), code)


def empty_history():
    return {"documents": [], "plans": [], "voids": [], "settings": {}}


def merge(history, plan):
    h = json.loads(json.dumps(history or empty_history()))
    for k in ("documents", "plans", "voids"):
        h.setdefault(k, [])
    row = plan.get("register_row")
    if row and row.get("number"):
        cur = row["currency"]
        rec = {"number": row["number"], "type": row["type"], "client": row["client"], "project": row["project"],
               "issue_date": row["issue_date"], "due_date": row["due_date"], "currency": cur,
               "net": str(money_dec(row["net"], cur)), "tax": str(money_dec(row["tax"], cur)),
               "total": str(money_dec(row["total"], cur)), "paid": str(money_dec(row["paid"], cur)),
               "status": row["status"], "paid_date": "", "po": row.get("po") or "", "file": row.get("file") or ""}
        h["documents"] = [d for d in h["documents"] if d["number"] != rec["number"]] + [rec]
        cr = (plan.get("doc") or {}).get("credits") or {}
        if row["type"] == "credit note" and cr.get("number"):
            orig = [d for d in h["documents"] if d["number"] == cr["number"]]
            if orig and plan["status"] == "READY":
                if Decimal(orig[0]["total"]) + Decimal(rec["total"]) == 0:
                    orig[0]["status"] = "credited"
                    rec["status"] = "credited"
                else:
                    rec["project"] = (rec["project"] or "") + f" (part credit of {cr['number']})"
    bp = plan.get("billing_plan")
    if bp and bp.get("stages") and plan.get("doc"):
        cur = plan["currency"]
        pid = bp.get("id") or f"{plan['doc']['client'][0] if plan['doc']['client'] else 'Client'} {bp.get('name') or ''}".strip()
        stages = []
        for s in bp["stages"]:
            st = dict(s)
            if s["stage"] == bp["current_stage"] and not plan["doc"].get("preview"):
                st["number"] = plan["number"]
                st["issue_date"] = plan["issue_date"]
                st["status"] = "issued" if plan["status"] == "READY" else "draft"
            elif st.get("status") == "this invoice":
                st["status"] = "waiting"
            st["total"] = str(money_dec(s["total"], cur))
            stages.append({k: st.get(k) for k in ("stage", "label", "share", "trigger", "planned", "total", "number",
                                                  "issue_date", "status", "paid_date")})
        rec = {"id": pid, "client": plan["doc"]["client"][0] if plan["doc"]["client"] else "", "name": bp.get("name") or "",
               "currency": cur, "project_total": str(money_dec(bp["project_total"], cur)), "stages": stages}
        h["plans"] = [p for p in h["plans"] if p["id"] != pid] + [rec]
    return h


def status_of(d, today):
    if d["status"] in ("void", "credited", "draft"):
        return d["status"]
    if d["status"] == "overdue" and not (d.get("due_date") or ""):
        d = dict(d, status="issued")
    bal = Decimal(d["total"] or 0) - Decimal(d["paid"] or 0)
    if bal <= 0 and Decimal(d["total"] or 0) > 0:
        return "paid"
    due = D.parse_iso(d.get("due_date") or "")
    if due and today > due and bal > 0:
        return "overdue"
    if Decimal(d["paid"] or 0) > 0:
        return "part paid"
    return d["status"] or "issued"


def write_xlsx(h, path, today, settings):
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
        from openpyxl.worksheet.datavalidation import DataValidation
    except ImportError:
        return None
    wb = openpyxl.Workbook()
    yellow = PatternFill("solid", fgColor="FFF2CC")
    bold = Font(bold=True)
    ws_sum = wb.active
    ws_sum.title = "Summary"
    ws = wb.create_sheet("Register")
    ws.append(REG_COLS)
    for c in ws[1]:
        c.font = bold
    docs = sorted(h["documents"], key=lambda d: (d.get("issue_date") or "", d["number"]))
    for i, d in enumerate(docs, start=2):
        cur = d["currency"]
        fmt = "#,##0" if C.minor_units(cur) == 0 else ("#,##0.000" if C.minor_units(cur) == 3 else "#,##0.00")
        idate = D.parse_iso(d.get("issue_date") or "")
        ddate = D.parse_iso(d.get("due_date") or "")
        pdate = D.parse_iso(d.get("paid_date") or "")
        ws.append([d["number"], d["type"], d["client"], d.get("project") or "", idate, ddate, cur,
                   float(Decimal(d["net"])), float(Decimal(d["tax"])), float(Decimal(d["total"])), float(Decimal(d["paid"] or 0)),
                   f"=IF(OR(M{i}=\"void\",M{i}=\"credited\",M{i}=\"draft\"),0,J{i}-K{i})", status_of(d, today), pdate,
                   f"=IF(AND(L{i}>0,F{i}<>\"\",TODAY()>F{i}),TODAY()-F{i},0)", d.get("po") or "", d.get("file") or ""])
        for col in "HIJKL":
            ws[f"{col}{i}"].number_format = fmt
        for col in "EFN":
            ws[f"{col}{i}"].number_format = "yyyy-mm-dd"
        for col in "KMN":
            ws[f"{col}{i}"].fill = yellow
    last = max(2, len(docs) + 1)
    dv = DataValidation(type="list", formula1='"' + ",".join(STATUSES) + '"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"M2:M{last + 200}")
    widths = [16, 11, 26, 22, 12, 12, 9, 12, 11, 12, 12, 12, 11, 12, 10, 18, 44]
    for col, w in zip("ABCDEFGHIJKLMNOPQ", widths):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "A2"
    # Summary
    ws_sum["A1"] = "Invoice register"
    ws_sum["A1"].font = Font(bold=True, size=14)
    ws_sum["A2"] = f"Updated {today.isoformat()}. Yellow cells on the Register are yours to fill: Paid, Status, Paid date. Balance, days late and these totals recalculate."
    ws_sum.append([])
    ws_sum.append(["Client", "Currency", "Outstanding", "Overdue", "Overdue invoices"])
    for c in ws_sum[4]:
        c.font = bold
    pairs = sorted({(d["client"], d["currency"]) for d in docs})
    r = 5
    for client, cur in pairs:
        fmt = "#,##0" if C.minor_units(cur) == 0 else "#,##0.00"
        cl = client.replace('"', '""')
        ws_sum.append([client, cur,
                       f'=SUMIFS(Register!L:L,Register!C:C,"{cl}",Register!G:G,"{cur}")',
                       f'=SUMIFS(Register!L:L,Register!C:C,"{cl}",Register!G:G,"{cur}",Register!O:O,">0")',
                       f'=COUNTIFS(Register!C:C,"{cl}",Register!G:G,"{cur}",Register!O:O,">0")'])
        ws_sum[f"C{r}"].number_format = fmt
        ws_sum[f"D{r}"].number_format = fmt
        r += 1
    for cur in sorted({d["currency"] for d in docs}):
        fmt = "#,##0" if C.minor_units(cur) == 0 else "#,##0.00"
        ws_sum.append([f"All clients ({cur})", cur, f'=SUMIFS(Register!L:L,Register!G:G,"{cur}")',
                       f'=SUMIFS(Register!L:L,Register!G:G,"{cur}",Register!O:O,">0")',
                       f'=COUNTIFS(Register!G:G,"{cur}",Register!O:O,">0")'])
        for col in "ABCDE":
            ws_sum[f"{col}{r}"].font = bold
        ws_sum[f"C{r}"].number_format = fmt
        ws_sum[f"D{r}"].number_format = fmt
        r += 1
    ws_sum.append([])
    ws_sum.append(["Next due"])
    ws_sum[f"A{r + 1}"].font = bold
    upcoming = sorted([d for d in docs if status_of(d, today) in ("issued", "part paid", "overdue") and d.get("due_date")],
                      key=lambda d: d["due_date"])
    for d in upcoming[:10]:
        ws_sum.append([d["client"], d["currency"], d["number"], D.parse_iso(d["due_date"])])
        ws_sum.cell(ws_sum.max_row, 4).number_format = "yyyy-mm-dd"
    waiting = [(p, s) for p in h["plans"] for s in p["stages"] if s.get("status") == "waiting"]
    if waiting:
        ws_sum.append([])
        ws_sum.append(["Stages waiting on their trigger"])
        ws_sum.cell(ws_sum.max_row, 1).font = bold
        for p, s in waiting:
            ws_sum.append([p["client"], p["currency"], f"Stage {s['stage']}: {s['label']}", s.get("trigger") or "",
                           float(Decimal(s["total"]))])
    needs = settings.get("open_needs") or []
    if needs:
        ws_sum.append([])
        ws_sum.append(["Still to fill in"])
        ws_sum.cell(ws_sum.max_row, 1).font = bold
        for n in needs:
            ws_sum.append([n])
    for col, w in zip("ABCDE", [34, 10, 16, 16, 16]):
        ws_sum.column_dimensions[col].width = w
    # Billing plans
    wp = wb.create_sheet("Billing plans")
    wp.append(PLAN_COLS)
    for c in wp[1]:
        c.font = bold
    for p in h["plans"]:
        for s in p["stages"]:
            wp.append([p["id"], p["client"], p["currency"], float(Decimal(p["project_total"])), s["stage"], s["label"],
                       s.get("share") or "", s.get("trigger") or "", D.parse_iso(s.get("planned") or "") or (s.get("planned") or ""),
                       float(Decimal(s["total"])), s.get("number") or "", D.parse_iso(s.get("issue_date") or "") or "",
                       s.get("status") or "", D.parse_iso(s.get("paid_date") or "") or ""])
    for col, w in zip("ABCDEFGHIJKLMN", [22, 24, 9, 14, 7, 16, 9, 26, 12, 13, 16, 12, 12, 12]):
        wp.column_dimensions[col].width = w
    # Gaps and voids
    wv = wb.create_sheet("Gaps and voids")
    wv.append(["Number", "Reason", "Date"])
    for c in wv[1]:
        c.font = bold
    for v in h["voids"]:
        wv.append([v["number"], v["reason"], v.get("date") or ""])
    wv.column_dimensions["A"].width = 18
    wv.column_dimensions["B"].width = 60
    # Settings
    wset = wb.create_sheet("Settings")
    wset.append(["Setting", "Value"])
    for c in wset[1]:
        c.font = bold
    for k, v in settings.get("rows", []):
        wset.append([k, v])
    wset.column_dimensions["A"].width = 34
    wset.column_dimensions["B"].width = 90
    wb.properties.creator = settings.get("business") or ""
    wb.properties.description = C.CREDIT
    wb.properties.keywords = C.CREDIT
    tmp = path + ".part.xlsx"
    wb.save(tmp)
    os.replace(tmp, path)
    return path


def carry_overdue(h, plan):
    """An overdue invoice the founder asked to chase belongs in the register: add it, or fill its missing due date."""
    out = []
    nums = {d["number"]: d for d in h["documents"]}
    for r in plan.get("reminders") or []:
        num = r.get("number")
        if not num:
            continue
        amt = str(money_dec(r["amount_minor"], r["currency"]))
        if num in nums:
            d = nums[num]
            if not d.get("due_date") and r.get("due_date"):
                d["due_date"] = r["due_date"]
                out.append(f"{num}: due date {r['due_date']} from your message")
            if d.get("status") in ("paid",):
                out.append(f"{num} is marked paid in your register but you asked to chase it; check which is right")
            continue
        h["documents"].append({"number": num, "type": "invoice", "client": r.get("client") or "", "project": "",
                               "issue_date": "", "due_date": r.get("due_date") or "", "currency": r["currency"],
                               "net": amt, "tax": "0", "total": amt, "paid": "0", "status": "issued", "paid_date": "",
                               "po": "", "file": "", "source": "your message (the invoice you asked to chase)"})
        out.append(f"{num} {r.get('client') or ''}, {r['amount']}, due {r.get('due_date')}: the invoice you asked to chase")
    return out


def summary_lines(h, plan, today):
    """OVERDUE and OUTSTANDING lines, also stored in the history so check_copy.py --also history.json allows them."""
    outstanding, lines, overdue = {}, [], []
    for d in h["documents"]:
        st = status_of(d, today)
        if st in ("issued", "part paid", "overdue"):
            outstanding[d["currency"]] = outstanding.get(d["currency"], Decimal(0)) + Decimal(d["total"]) - Decimal(d["paid"] or 0)
    for d in sorted(h["documents"], key=lambda d: d.get("due_date") or ""):
        if status_of(d, today) == "overdue":
            due = D.parse_iso(d.get("due_date") or "")
            M = C.money_for(plan, d["currency"] or "XXX")
            bal = C.to_minor(Decimal(d["total"]) - Decimal(d["paid"] or 0), d["currency"] or "XXX")
            when = f"due {due.isoformat()}, {(today - due).days} days ago" if due else "no due date recorded"
            line = f"OVERDUE: {d['number']} {d['client']} {M.full(bal)}, {when}, not marked paid"
            lines.append(line)
            overdue.append({"number": d["number"], "client": d["client"], "balance": M.full(bal),
                            "due_date": due.isoformat() if due else "", "days_late": (today - due).days if due else None})
    totals = []
    for cur, v in sorted(outstanding.items()):
        M = C.money_for(plan, cur or "XXX")
        totals.append(M.full(C.to_minor(v, cur or "XXX")))
        lines.append(f"OUTSTANDING: {totals[-1]}")
    unknown_due = [d["number"] for d in h["documents"] if status_of(d, today) in ("issued", "part paid") and not d.get("due_date")]
    if unknown_due:
        lines.append(f"NO DUE DATE: {', '.join(unknown_due)}; they cannot show as overdue until the founder gives the dates")
    h["summary"] = {"as_of": today.isoformat(), "outstanding": totals, "overdue": overdue}
    return lines


def write_csv(h, path, today):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(REG_COLS)
        for d in sorted(h["documents"], key=lambda d: (d.get("issue_date") or "", d["number"])):
            bal = Decimal(d["total"]) - Decimal(d["paid"] or 0)
            st = status_of(d, today)
            if st in ("void", "credited", "draft"):
                bal = Decimal(0)
            due = D.parse_iso(d.get("due_date") or "")
            late = (today - due).days if (due and bal > 0 and today > due) else 0
            w.writerow([d["number"], d["type"], d["client"], d.get("project") or "", d.get("issue_date") or "",
                        d.get("due_date") or "", d["currency"], d["net"], d["tax"], d["total"], d["paid"], str(bal), st,
                        d.get("paid_date") or "", late, d.get("po") or "", d.get("file") or ""])
    return path


def settings_rows(plan, h):
    ts = plan.get("tax_setup") or {}
    rows = []
    doc = plan.get("doc") or {}
    if doc.get("issuer"):
        rows.append(["Business", doc["issuer"][0]])
    rows.append(["Last number used", plan.get("number") or ""])
    rows.append(["Currency", plan.get("currency") or ""])
    if plan.get("country"):
        rows.append(["Country", plan["country"]])
    rows.append(["Number style", "Indian grouping" if plan.get("indian") else C.money_for(plan, "XXX").num(123456)])
    rows.append(["Date style", plan.get("date_pattern") or ""])
    rows.append(["Paper", plan.get("paper") or ""])
    t = plan.get("terms") or {}
    rows.append(["Payment terms", f"{t.get('type') or 'days'} {t.get('days') or ''}".strip()])
    if ts.get("charged"):
        for c in ts.get("categories") or []:
            rows.append([f"Tax category {c['id']}", f"{c['label']} {c['rate']}%: supplied by you on {plan['today']}"])
        rows.append(["Prices entered", "including tax (you said so; confirm with your accountant)" if ts.get("prices_include_tax") else "before tax"])
        rows.append(["Rounding", ("each line, half up" if ts.get("rounding") == "line" else "each tax category's total, half up")
                     + ", to the currency's smallest unit; confirm the rounding method with your accountant"])
        for w in ts.get("wording") or []:
            rows.append(["Tax wording (supplied by you)", w])
    else:
        rows.append(["Tax", "none on these invoices. Enter prices before any sales tax (VAT, GST or similar); ask your accountant whether you need to charge it"])
    lf = plan.get("late_fee") or {}
    if lf.get("path") == "agreed":
        rows.append(["Late fee (supplied by you)", f"{lf.get('clause')} (as agreed in {lf.get('source')})"])
    rows.append(["Note", "A record and planning tool, not tax or accounting advice. Your accountant can confirm what your invoices must show."])
    return {"rows": rows, "business": doc.get("issuer", [""])[0] if doc else "", "open_needs": plan.get("needs") or []}


HEADINGS = {
    "number": ["number", "invoice number", "invoice no", "invoice no.", "invoice #", "invoice", "inv", "inv no", "inv #", "no",
               "no.", "#", "ref", "reference", "doc", "document"],
    "type": ["type", "document type"],
    "client": ["client", "customer", "bill to", "billed to", "company", "name", "client name", "customer name"],
    "project": ["project", "job", "description", "work"],
    "issue_date": ["issue date", "invoice date", "date", "date issued", "issued", "sent", "date sent"],
    "due_date": ["due date", "due", "payment due", "due by", "due on"],
    "currency": ["currency", "cur", "ccy"],
    "net": ["net", "subtotal", "excl vat", "ex vat", "excl tax", "ex gst", "before tax"],
    "tax": ["tax", "vat", "gst", "sales tax"],
    "total": ["total", "amount", "invoice total", "total due", "gross", "value", "incl vat", "inc vat", "amount due", "sum"],
    "paid": ["paid", "paid?", "amount paid", "received", "paid amount", "payment"],
    "status": ["status", "state"],
    "paid_date": ["paid date", "date paid", "paid on", "payment date", "received on"],
    "po": ["po or reference", "po", "po number", "purchase order", "their ref"],
    "file": ["file"],
}
PAID_WORDS = re.compile(r"(?i)^\s*(yes|y|paid|done|received|settled|cleared|ok)\b")
UNPAID_WORDS = re.compile(r"(?i)^\s*(no|n|unpaid|not paid|outstanding|open|owing|due|overdue|pending|chasing)?\s*$")


def map_headings(head):
    """Match the founder's own column headings to the register's fields. Returns {field: index}, [unused headings]."""
    found, unused = {}, []
    for i, h in enumerate(head):
        key = re.sub(r"\s+", " ", str(h or "").strip().lower()).strip(" :")
        hit = None
        for field, names in HEADINGS.items():
            if key in names and field not in found:
                hit = field
                break
        if hit is None and key:
            for field, names in HEADINGS.items():
                if field not in found and any(re.search(rf"\b{re.escape(n)}\b", key) for n in names if len(n) > 3):
                    hit = field
                    break
        if hit:
            found[hit] = i
        elif key:
            unused.append(str(h))
    return found, unused


def _cell_date(v, order, today, year_hint=None):
    """A founder's date cell: a real date, ISO, 12/08/2026, 01 Sept 2026, 15 Aug, 14/10 (year taken as the latest not in the future)."""
    if v in (None, ""):
        return None
    if hasattr(v, "date") and callable(v.date):
        return v.date()
    if isinstance(v, date):
        return v
    t = str(v).strip()
    try:
        return D.read_date(t, order, today, prefer="past")
    except C.Stop:
        pass
    m = re.fullmatch(r"(\d{1,2})[./-](\d{1,2})", t)
    if m:
        for y in (today.year, today.year - 1):
            try:
                d = D.read_date(f"{m.group(1)}/{m.group(2)}/{y}", order, today, prefer="past")
            except C.Stop:
                return None
            if d <= today:
                return d
    return None


def _cell_amount(v, style, code):
    if v in (None, ""):
        return None, code
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return Decimal(str(v)), code
    t = str(v).strip()
    try:
        num, cur, _notes = LN.parse_money(t, style)
    except (LN.Ambiguous, LN.Unreadable):
        return None, code
    return C.dec(num), (cur if cur in C.KNOWN_CODES else code)


def _amt(v, code):
    code = code or "XXX"
    return str(money_dec(C.to_minor(Decimal(v), code), code))


def read_table(rows, today, order="DMY", currency=None, source=""):
    """Turn the founder's own register rows (first row = headings) into history documents, saying what was understood."""
    h = empty_history()
    h["gaps"] = []
    report = []
    if not rows:
        return h, ["CHECK: the register is empty"]
    head, body = rows[0], rows[1:]
    cols, unused = map_headings(head)
    if "number" not in cols:
        raise C.Stop(f"no invoice number column was found in {source or 'the register'} (headings: {', '.join(str(x) for x in head)}). "
                     "Ask the founder which column holds the invoice numbers")
    get = lambda r, f: (r[cols[f]] if f in cols and cols[f] < len(r) else None)
    samples = [str(get(r, f)) for r in body for f in ("total", "net", "tax", "paid") if get(r, f) not in (None, "")]
    style = LN.detect_decimal_style(samples) or "dot"
    unread, amounts, docs = [], 0, []
    for n, r in enumerate(body, 2):
        num = str(get(r, "number") or "").strip()
        if not num:
            continue
        rest = [x for i, x in enumerate(r) if i != cols["number"] and str(x or "").strip()]
        if not rest:
            h["gaps"].append({"number": num, "reason": "a blank row in your register: no client, date or amount"})
            continue
        code = (str(get(r, "currency") or "").strip().upper() or None) if "currency" in cols else None
        total, code2 = _cell_amount(get(r, "total"), style, code or currency)
        net, _ = _cell_amount(get(r, "net"), style, code2)
        tax, _ = _cell_amount(get(r, "tax"), style, code2)
        code = code or code2 or currency or ""
        if total is None and net is not None:
            total = net + (tax or Decimal(0))
        if total is None:
            unread.append(f"row {n} ({num}): amount '{get(r, 'total') or ''}'")
            total = Decimal(0)
        else:
            amounts += 1
        if net is None:
            net, tax = total, Decimal(0)
        idate = _cell_date(get(r, "issue_date"), order, today)
        if get(r, "issue_date") not in (None, "") and not idate:
            unread.append(f"row {n} ({num}): date '{get(r, 'issue_date')}'")
        ddate = _cell_date(get(r, "due_date"), order, today) if "due_date" in cols else None
        if "due_date" in cols and get(r, "due_date") not in (None, "") and not ddate:
            unread.append(f"row {n} ({num}): due date '{get(r, 'due_date')}'")
        paid_cell = get(r, "paid")
        status_cell = str(get(r, "status") or "").strip().lower()
        paid_amt, pdate = Decimal(0), _cell_date(get(r, "paid_date"), order, today) if "paid_date" in cols else None
        pc = str(paid_cell or "").strip()
        if pc:
            if PAID_WORDS.match(pc):
                paid_amt = total
                m = re.search(r"\d{1,4}[./-]\d{1,2}(?:[./-]\d{1,4})?|\d{1,2}\s+[A-Za-z]{3,}(?:\s+\d{4})?", pc)
                if m and not pdate:
                    pdate = _cell_date(m.group(0), order, today)
            elif UNPAID_WORDS.match(pc):
                paid_amt = Decimal(0)
            else:
                v, _ = _cell_amount(pc, style, code)
                if v is not None and "paid" in cols and head[cols["paid"]] and "?" not in str(head[cols["paid"]]):
                    paid_amt = v
                else:
                    unread.append(f"row {n} ({num}): paid '{pc}'")
        if status_cell in ("paid", "settled") and not paid_amt:
            paid_amt = total
        status = "issued"
        if status_cell in STATUSES and status_cell not in ("overdue", "part paid", "paid"):
            status = status_cell
        if paid_amt and paid_amt >= total and total > 0:
            status = "paid"
        elif paid_amt:
            status = "part paid"
        docs.append({"number": num, "type": str(get(r, "type") or "invoice").strip().lower() or "invoice",
                     "client": str(get(r, "client") or "").strip(), "project": str(get(r, "project") or "").strip(),
                     "issue_date": idate.isoformat() if idate else "", "due_date": ddate.isoformat() if ddate else "",
                     "currency": code, "net": _amt(net, code), "tax": _amt(tax or 0, code), "total": _amt(total, code),
                     "paid": _amt(paid_amt, code),
                     "status": status, "paid_date": pdate.isoformat() if pdate else "",
                     "po": str(get(r, "po") or "").strip(), "file": str(get(r, "file") or "").strip(), "source": "your register"})
    h["documents"] = docs
    understood = [f"{head[i]} ({f.replace('_', ' ')})" for f, i in sorted(cols.items(), key=lambda x: x[1])]
    report.append(f"READ: {len(body)} rows: {len(docs)} invoices, {amounts} amounts read, {len(h['gaps'])} blank rows")
    report.append("COLUMNS: understood " + ", ".join(understood) + (f"; not used: {', '.join(unused)}" if unused else ""))
    if "due_date" not in cols:
        report.append("CHECK: there is no due date column, so nothing from this register can show as overdue until the "
                      "founder gives the due dates (or the terms they used)")
    for u in unread:
        report.append(f"UNREAD: {u}; ask the founder")
    if docs and amounts == 0:
        report.append("CHECK: no amounts could be read; do not build totals from this register until the founder confirms them")
    for g in h["gaps"]:
        report.append(f"GAP: {g['number']} is {g['reason']}. Ask whether it was sent; if not, the next invoice can use it")
    seen = {}
    for d in docs:
        if d["status"] not in ("paid",) and Decimal(d["total"]) > 0:
            k = (d["client"].lower(), d["total"], d["currency"])
            if k in seen:
                shown = C.Money(d["currency"] or "XXX", style).full(C.to_minor(Decimal(d["total"]), d["currency"] or "XXX"))
                report.append(f"CHECK: {seen[k]} and {d['number']} are both {d['client']}, {shown}, neither marked paid: "
                              "one invoice entered twice, or two separate jobs?")
            else:
                seen[k] = d["number"]
    for d in docs:
        if d["status"] in ("paid", "part paid"):
            report.append(f"PAID: {d['number']} {d['client']}" + (f", {d['paid_date']}" if d["paid_date"] else ", no paid date"))
    return h, report


def read_register(path, today=None, order="DMY", currency=None):
    """Read the skill's own register or the founder's own spreadsheet (xlsx or csv, any sensible headings)."""
    today = today or date.today()
    if path.lower().endswith(".csv") or path.lower().endswith(".txt"):
        raw = open(path, encoding="utf-8-sig").read()
        first = raw.splitlines()[0] if raw.strip() else ""
        delim = max([",", ";", "\t"], key=first.count) if first else ","
        rows = [r for r in csv.reader(raw.splitlines(), delimiter=delim)]
        return read_table(rows, today, order, currency, path)
    try:
        import openpyxl
    except ImportError:
        raise C.Stop("this machine cannot read .xlsx files; ask the founder to save the register as CSV, or use the memory file")
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb["Register"] if "Register" in wb.sheetnames else wb.worksheets[0]
    rows = [list(r) for r in ws.iter_rows(values_only=True)]
    while rows and not any(x not in (None, "") for x in rows[0]):
        rows.pop(0)
    h, report = read_table(rows, today, order, currency, path)
    if "Billing plans" in wb.sheetnames:
        plans = {}
        wp = wb["Billing plans"]
        ph = [c.value for c in wp[1]]
        for row in wp.iter_rows(min_row=2, values_only=True):
            if not row or not row[0]:
                continue
            r = dict(zip(ph, row))
            p = plans.setdefault(r["Plan"], {"id": r["Plan"], "client": r["Client"], "name": "", "currency": r["Currency"],
                                             "project_total": str(r["Project total"]), "stages": []})
            p["stages"].append({"stage": int(r["Stage"]), "label": r["Label"], "share": r["Share"], "trigger": r["Trigger"],
                                "planned": _d(r["Planned date"]), "total": str(r["Stage total"]), "number": r["Number"] or None,
                                "issue_date": _d(r["Issue date"]), "status": r["Status"], "paid_date": _d(r["Paid date"])})
        h["plans"] = list(plans.values())
    if "Gaps and voids" in wb.sheetnames:
        for row in wb["Gaps and voids"].iter_rows(min_row=2, values_only=True):
            if row and row[0]:
                h["voids"].append({"number": str(row[0]), "reason": row[1] or "", "date": _d(row[2]) if len(row) > 2 else ""})
    return h, report


def _d(v):
    if v in (None, ""):
        return ""
    if hasattr(v, "date"):
        return v.date().isoformat()
    if isinstance(v, date):
        return v.isoformat()
    return str(v)


MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def paid_date(text, country, today):
    """Read a paid date in the founder's own order (from their country). A date like 11/6 with no country is a question."""
    t = str(text).strip()
    m = re.fullmatch(r"(\d{1,2})[./-](\d{1,2})(?:[./-](\d{2,4}))?", t)
    if m and not country and int(m.group(1)) <= 12 and int(m.group(2)) <= 12 and m.group(1) != m.group(2):
        raise C.Stop(f"'{t}' could be day first or month first. Ask the founder which month they mean, or pass --country")
    order = LN.locale_defaults(country.upper())["date_order"] if country else "DMY"
    if m and not m.group(3):
        t = f"{m.group(1)}/{m.group(2)}/{today.year}"
        d = D.read_date(t, order, today, prefer="past")
        if d > today:
            d = D.read_date(f"{m.group(1)}/{m.group(2)}/{today.year - 1}", order, today, prefer="past")
        return d, order
    return D.read_date(t, order, today, prefer="past"), order


def update(h, paid=(), void=(), issued=(), today=None, country=None, report=None):
    nums = {d["number"]: d for d in h["documents"]}
    country = country or (h.get("settings") or {}).get("Country")
    report = report if report is not None else []
    for p in paid:
        parts = p.split("=")
        if len(parts) < 2 or parts[0] not in nums:
            raise C.Stop(f"'{p}': give NUMBER=DATE[=AMOUNT] for a number in the register")
        d = nums[parts[0]]
        pd, order = paid_date(parts[1], country, today)
        if pd > today:
            raise C.Stop(f"{parts[0]} is marked paid on {pd.isoformat()}, which is in the future. Only money received counts")
        amt = Decimal(parts[2].replace(",", "")) if len(parts) > 2 else Decimal(d["total"]) - Decimal(d["paid"] or 0)
        d["paid"] = str(Decimal(d["paid"] or 0) + amt)
        d["paid_date"] = pd.isoformat()
        d["status"] = "paid" if Decimal(d["paid"]) >= Decimal(d["total"]) else "part paid"
        idt = D.parse_iso(d.get("issue_date") or "")
        if idt and pd < idt:
            report.append(f"CHECK: {d['number']} is marked paid on {pd.isoformat()}, before it was issued on {idt.isoformat()}; check the date")
        how = {"MDY": "month first", "DMY": "day first", "YMD": "year first"}.get(order, order)
        report.append(f"PAID: {d['number']} {d['status']} on {pd.day} {MONTHS[pd.month - 1]} {pd.year} "
                      f"('{parts[1]}' read {how}{', from ' + country if country else ''}); say it back to the founder")
        for pl in h["plans"]:
            for s in pl["stages"]:
                if s.get("number") == d["number"] and d["status"] == "paid":
                    s["status"] = "paid"
                    s["paid_date"] = pd.isoformat()
    for v in void:
        num, _, reason = v.partition("=")
        if not reason.strip():
            raise C.Stop("a voided number needs a reason, e.g. --void \"INV-0020=sent to the wrong client, replaced by INV-0021\"")
        h["voids"].append({"number": num, "reason": reason.strip(), "date": today.isoformat()})
        if num in nums:
            nums[num]["status"] = "void"
    for n in issued:
        if n not in nums:
            raise C.Stop(f"{n} is not in the register")
        nums[n]["status"] = "issued"
    return h


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    b = sub.add_parser("build")
    b.add_argument("--plan", required=True)
    b.add_argument("--history")
    b.add_argument("--out", required=True)
    b.add_argument("--csv", action="store_true", help="write the CSV even if openpyxl is present (to test)")
    r = sub.add_parser("read")
    r.add_argument("register")
    r.add_argument("--out", required=True)
    r.add_argument("--country", help="where the founder is (sets day or month first)")
    r.add_argument("--currency", help="the founder's currency code, for amounts written without one")
    r.add_argument("--today")
    u = sub.add_parser("update")
    u.add_argument("--history", required=True)
    u.add_argument("--paid", action="append", default=[])
    u.add_argument("--void", action="append", default=[])
    u.add_argument("--issued", action="append", default=[])
    u.add_argument("--today")
    u.add_argument("--country", help="where the founder is; sets day or month first (else the register's saved country)")
    a = ap.parse_args()
    if a.cmd == "build":
        plan = C.load_json(a.plan, "plan file")
        today = D.parse_iso(plan.get("today") or "") or date.today()
        hist = C.load_json(a.history, "history file") if a.history and os.path.exists(a.history) else empty_history()
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        h = merge(hist, plan)
        carried = carry_overdue(h, plan)
        settings = settings_rows(plan, h)
        h["settings"] = {k: v for k, v in settings["rows"]}
        out = None if a.csv else write_xlsx(h, a.out, today, settings)
        if not out:
            out = write_csv(h, os.path.splitext(a.out)[0] + ".csv", today)
            print("NOTE: spreadsheet library not available here, so the register is a CSV with the same columns")
        lines = summary_lines(h, plan, today)
        hist_out = a.history or os.path.join(os.path.dirname(os.path.abspath(a.plan)), "history.json")
        C.save_json(h, hist_out)
        print(f"WROTE: {out}")
        print(f"HISTORY: {hist_out}")
        for c in carried:
            print(f"ADDED: {c}")
        for line in lines:
            print(line)
        return 0
    if a.cmd == "read":
        if not os.path.exists(a.register):
            raise C.Stop(f"there is no register at {a.register}")
        today = D.parse_iso(a.today or "") or date.today()
        order = LN.locale_defaults((a.country or "").upper())["date_order"] if a.country else "DMY"
        h, report = read_register(a.register, today, order, (a.currency or "").upper() or None)
        C.save_json(h, a.out)
        for line in report:
            print(line)
        if not a.country:
            print("CHECK: no --country given, so dates like 03/04 were read day first; pass --country to be sure")
        print(f"WROTE: {a.out} ({len(h['documents'])} documents, {len(h['plans'])} billing plans, {len(h['voids'])} voids)")
        return 0
    if a.cmd == "update":
        h = C.load_json(a.history, "history file")
        today = D.parse_iso(a.today or "") or date.today()
        rep = []
        h = update(h, a.paid, a.void, a.issued, today, a.country, rep)
        C.save_json(h, a.history)
        for line in rep:
            print(line)
        print(f"UPDATED: {a.history}")
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    C.run_main(main)
