#!/usr/bin/env python3
"""Read, write and check the Invoice and Terms Builder memory file.

Usage (paths relative to this skill's folder):
  python3 scripts/memory.py read <memory.md> --json-out <inputs.json> --history-out <history.json> --today YYYY-MM-DD
        [--client "name"] [--plan "plan id or client name"]
        turns the saved file into a starting inputs file (your details, payment details, tax setup as you
        supplied it, number format and last number, terms, locale, labels) and a history file (documents,
        billing plans, voids). --client fills that client's saved details. --plan sets up the next stage of an
        open billing plan, with its project lines and what earlier stages were billed. Prints what it found.
  python3 scripts/memory.py write --inputs <inputs.json> --plan <plan.json> --history <history.json> --out <memory.md>
        [--existing <old memory.md>] [--history-line "made | option | verdict"]
        [--learning "rule | evidence | step | status"]
        writes the file: profile, tax setup, clients, billing plans and their lines, documents, gaps and voids,
        learnings and history (old learnings and history rows are kept, new ones appended).
  python3 scripts/memory.py validate <memory.md>
Plain markdown the founder can read and edit. It holds the founder's own payment details, so it stays in their
folder or Project. Write only what the founder approved. Standard library only. No network calls.
Exit 0 done, 1 validate found problems, 2 STOP.
"""
import argparse
import json
import os
import re
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

SKILL = "revos-invoice-and-terms"
SECTIONS = ["## Profile", "## Payment details", "## Tax setup (supplied by you)", "## Clients", "## Billing plans",
            "## Project lines", "## Documents", "## Gaps and voids", "## Learnings", "## History"]
PROFILE = [("Business name", "issuer.name"), ("Address", "issuer.address"), ("Email", "issuer.email"),
           ("Phone", "issuer.phone"), ("Tax number label", "issuer.tax_number_label"), ("Tax number", "issuer.tax_number"),
           ("Other lines under your details", "issuer.other_lines"), ("Country", "country"), ("Invoice language", "language"),
           ("Your English", "english"), ("Currency", "currency"), ("How you write numbers", "decimal_style"),
           ("Number grouping", "number_style"), ("Thousands separator", "grouping"), ("Print decimals as", "print_decimal"), ("Date style", "date_format"), ("Last invoice number", "number.last"),
           ("New year numbering", "number.rollover"), ("Usual terms", "terms.type"), ("Usual terms, days", "terms.days"),
           ("Days off", "days_off"), ("Holidays you named", "holidays"), ("Tax charged", "tax.charged"),
           ("Prices include tax", "tax.prices_include_tax"), ("Tax rounding", "tax.rounding"),
           ("Tax wording (verbatim)", "tax.wording"), ("Required wording (verbatim)", "required_wording"),
           ("Late fee", "late_fee.path"), ("Late fee clause (verbatim)", "late_fee.clause"),
           ("Late fee agreed in", "late_fee.source"), ("Payment reference", "payment.reference"),
           ("Payment link", "payment.link"), ("Bank change line", "payment.confirm_changes_line"),
           ("Logo file", "logo"), ("Accent colour", "colour"), ("Font", "font"), ("Your name for messages", "founder_name"),
           ("How you greet clients", "greeting"), ("Your sign-off", "signoff")]
LIST_KEYS = {"issuer.address", "issuer.other_lines", "days_off", "holidays", "tax.wording", "required_wording"}
BOOL_KEYS = {"tax.charged", "tax.prices_include_tax", "payment.confirm_changes_line"}
CLIENT_COLS = [("Client", "name"), ("Address", "address"), ("Contact", "contact"), ("Email", "email"),
               ("Tax number label", "tax_number_label"), ("Tax number", "tax_number"), ("PO needed", "po_needed"),
               ("PO or reference", "client_reference"), ("Their usual payment days", "pays_in"), ("Notes", "notes")]
DOC_COLS = [("Number", "number"), ("Type", "type"), ("Client", "client"), ("Project", "project"), ("Issue date", "issue_date"),
            ("Due date", "due_date"), ("Currency", "currency"), ("Net", "net"), ("Tax", "tax"), ("Total", "total"),
            ("Paid", "paid"), ("Status", "status"), ("Paid date", "paid_date"), ("PO", "po"), ("File", "file")]
PLAN_COLS = [("Plan", "id"), ("Client", "client"), ("Name", "name"), ("Currency", "currency"), ("Project total", "project_total"),
             ("Stage", "stage"), ("Label", "label"), ("Share", "share"), ("Trigger", "trigger"), ("Stage total", "total"),
             ("Number", "number"), ("Issue date", "issue_date"), ("Status", "status"), ("Paid date", "paid_date"),
             ("Tax on this stage", "tax_mode")]
LINE_COLS = [("Plan", "plan"), ("Description", "description"), ("Qty", "qty"), ("Unit", "unit"), ("Unit price", "unit_price"),
             ("Tax", "tax"), ("Stage", "stage")]
TAX_COLS = [("Id", "id"), ("Label", "label"), ("Rate", "rate"), ("Default", "default"), ("Supplied on", "date")]
LEARN_HEAD = "| # | Learning | Evidence | Applies to step | Status | Added |"
HIST_HEAD = "| Date | Made | Option chosen | Verdict |"


def cell(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, list):
        return " / ".join(str(x) for x in v)
    return str(v).replace("|", "/").replace("\n", " ").strip()


def get(d, path):
    for k in path.split("."):
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def put(d, path, v):
    ks = path.split(".")
    for k in ks[:-1]:
        d = d.setdefault(k, {})
    d[ks[-1]] = v


def table(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    for r in rows:
        out.append("| " + " | ".join(cell(x) for x in r) + " |")
    return "\n".join(out)


def parse_tables(text):
    """Section heading to list of dict rows."""
    out = {}
    cur = None
    head = None
    for line in text.splitlines():
        if line.startswith("## "):
            cur, head = line.strip(), None
            out[cur] = []
            continue
        if cur and line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if head is None:
                head = cells
            elif all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
                continue
            else:
                out[cur].append(dict(zip(head, cells)))
    return out


def unbool(v):
    return str(v).strip().lower() in ("yes", "true", "1")


def read(path, today, client=None, plan_id=None):
    if not os.path.exists(path):
        raise C.Stop(f"there is no memory file at {path}")
    text = open(path, encoding="utf-8").read()
    if SKILL not in text:
        raise C.Stop("this is not an Invoice and Terms Builder memory file")
    t = parse_tables(text)
    inp = {"today": today}
    for row in t.get("## Profile", []):
        label, val = row.get("Field"), row.get("Value", "")
        key = dict(PROFILE).get(label)
        if not key or val == "":
            continue
        if key in LIST_KEYS:
            v = [x.strip() for x in val.split(" / ") if x.strip()]
        elif key in BOOL_KEYS:
            v = unbool(val)
        else:
            v = val
        put(inp, key, v)
    fields = [[r["Field"], r["Value"]] for r in t.get("## Payment details", []) if r.get("Value")]
    if fields:
        inp.setdefault("payment", {})["fields"] = fields
    cats = []
    default = None
    for r in t.get("## Tax setup (supplied by you)", []):
        cats.append({"id": r["Id"], "label": r["Label"], "rate": r["Rate"]})
        if unbool(r.get("Default")):
            default = r["Id"]
    if cats:
        inp.setdefault("tax", {})["categories"] = cats
        inp["tax"]["default"] = default or cats[0]["id"]
    hist = {"documents": [], "plans": [], "voids": [], "settings": {}}
    for r in t.get("## Documents", []):
        hist["documents"].append({k: r.get(lab, "") for lab, k in DOC_COLS})
    plans = {}
    for r in t.get("## Billing plans", []):
        p = plans.setdefault(r["Plan"], {"id": r["Plan"], "client": r["Client"], "name": r.get("Name", ""),
                                         "currency": r["Currency"], "project_total": r["Project total"], "stages": [], "lines": []})
        p["stages"].append({"stage": int(r["Stage"]), "label": r["Label"], "share": r["Share"], "trigger": r["Trigger"],
                            "total": r["Stage total"], "number": r["Number"] or None, "issue_date": r["Issue date"],
                            "status": r["Status"], "paid_date": r["Paid date"], "tax_mode": r.get("Tax on this stage") or "share"})
    for r in t.get("## Project lines", []):
        if r["Plan"] in plans:
            plans[r["Plan"]]["lines"].append({k: r.get(lab, "") for lab, k in LINE_COLS if k != "plan"})
    hist["plans"] = list(plans.values())
    for r in t.get("## Gaps and voids", []):
        hist["voids"].append({"number": r["Number"], "reason": r["Reason"], "date": r.get("Date", "")})
    inp.setdefault("number", {})["used"] = [d["number"] for d in hist["documents"]] + [v["number"] for v in hist["voids"]]
    clients = t.get("## Clients", [])
    found = []
    if client:
        m = [r for r in clients if r["Client"].lower() == client.lower()] or \
            [r for r in clients if client.lower() in r["Client"].lower()]
        if len(m) > 1:
            raise C.Stop(f"two saved clients match '{client}': {', '.join(r['Client'] for r in m)}. Ask the founder which")
        if m:
            c = m[0]
            inp["client"] = {"name": c["Client"], "address": [x.strip() for x in c["Address"].split(" / ") if x.strip()],
                             "contact": c.get("Contact", ""), "email": c.get("Email", ""),
                             "tax_number_label": c.get("Tax number label", ""), "tax_number": c.get("Tax number", "")}
            if c.get("PO needed"):
                inp["po_needed"] = unbool(c["PO needed"])
            if c.get("PO or reference"):
                inp["client_reference"] = c["PO or reference"]
            found.append(f"client {c['Client']}")
    if plan_id:
        m = [p for p in hist["plans"] if p["id"].lower() == plan_id.lower()] or \
            [p for p in hist["plans"] if plan_id.lower() in (p["id"] + " " + p["client"] + " " + p["name"]).lower()]
        m = [p for p in m if any(s["status"] in ("waiting", "") or not s.get("number") for s in p["stages"])] or m
        if not m:
            raise C.Stop(f"no open billing plan matches '{plan_id}'")
        if len(m) > 1:
            raise C.Stop(f"two billing plans match '{plan_id}': {', '.join(p['id'] for p in m)}. Ask the founder which")
        p = m[0]
        nxt = next((s["stage"] for s in p["stages"] if not s.get("number")), None)
        if nxt is None:
            raise C.Stop(f"every stage of {p['id']} is already invoiced")
        if not p["lines"]:
            raise C.Stop(f"the project lines for {p['id']} are not in the memory file; ask the founder for them")
        inp["lines"] = p["lines"]
        inp["billing_plan"] = {"id": p["id"], "name": p["name"], "current_stage": nxt, "stages": [
            {"label": s["label"], "share": s["share"] if s["share"] not in ("balance",) else None, "trigger": s["trigger"],
             "number": s.get("number"), "issue_date": s.get("issue_date") or None,
             "issued_total": s["total"] if s.get("number") else None, "paid_date": s.get("paid_date") or None,
             "tax": s.get("tax_mode") or "share", "status": s.get("status") or None} for s in p["stages"]]}
        if not client:
            return read(path, today, p["client"], plan_id)
        found.append(f"plan {p['id']}, next stage {nxt}")
    m = re.search(r"## Invoice labels.*?```json\n(.*?)\n```", text, re.S)
    if m:
        try:
            inp["labels"] = json.loads(m.group(1))
            found.append("your invoice labels")
        except json.JSONDecodeError:
            raise C.Stop("the Invoice labels block in the memory file is not valid; fix it or delete the section")
    learnings = [r for r in t.get("## Learnings", []) if r.get("Status", "").lower() == "active"]
    return inp, hist, learnings, found


def write(inp, plan, hist, out, existing=None, history_line=None, learnings=(), no_payment=False):
    today = plan.get("today") or date.today().isoformat()
    old = {}
    if existing and os.path.exists(existing):
        old_text = open(existing, encoding="utf-8").read()
        old = parse_tables(old_text)
        lm = re.search(r"## Invoice labels.*?```json\n(.*?)\n```", old_text, re.S)
        if lm:
            try:
                old["_labels_raw"] = json.loads(lm.group(1))
            except json.JSONDecodeError:
                pass
    prof_rows = []
    issued_now = plan.get("doc") and plan["status"] == "READY" and not plan["doc"].get("preview")
    snap = json.loads(json.dumps(inp))
    if not snap.get("grouping") and plan.get("group") not in (None, "." if plan.get("decimal_style") == "comma" else ","):
        snap["grouping"] = {v: k for k, v in C.GROUPS.items()}.get(plan.get("group"))
    if not snap.get("decimal_style") and plan.get("decimal_style"):
        snap["decimal_style"] = plan["decimal_style"]
    if issued_now:
        put(snap, "number.last", plan["number"])
    elif not get(snap, "number.last"):
        old_last = next((r["Value"] for r in old.get("## Profile", []) if r.get("Field") == "Last invoice number"), None)
        if old_last:
            put(snap, "number.last", old_last)
    oldprof = {r.get("Field"): r for r in old.get("## Profile", [])}
    for label, key in PROFILE:
        v = get(snap, key)
        if key in ("terms.type", "terms.days") and not (inp.get("terms") or {}).get("type"):
            v = None
        if v in (None, "", []):
            if label in oldprof and oldprof[label].get("Value"):
                prof_rows.append([label, oldprof[label]["Value"], oldprof[label].get("Source", ""), oldprof[label].get("Updated", "")])
            continue
        o = oldprof.get(label)
        same = o and o.get("Value") == cell(v)
        prof_rows.append([label, v, "you said" if key != "number.last" else "this run", o.get("Updated") if same else today])
    pay_rows = [[f, v, today] for f, v in (get(inp, "payment.fields") or []) if v]
    if no_payment:
        pay_rows = []
    elif not pay_rows:
        pay_rows = [[r["Field"], r["Value"], r.get("Updated", "")] for r in old.get("## Payment details", [])]
    tax_rows = []
    for c in get(inp, "tax.categories") or []:
        tax_rows.append([c.get("id"), c.get("label"), c.get("rate"), "yes" if str(c.get("id")) == str(get(inp, "tax.default") or "") else "", today])
    if not tax_rows:
        tax_rows = [[r["Id"], r["Label"], r["Rate"], r.get("Default", ""), r.get("Supplied on", "")] for r in old.get("## Tax setup (supplied by you)", [])]
    clients = {r["Client"]: [r.get(lab, "") for lab, _k in CLIENT_COLS] for r in old.get("## Clients", [])}
    cl = inp.get("client") or {}
    if cl.get("name"):
        prev = clients.get(cl["name"], [""] * len(CLIENT_COLS))
        row = []
        for i, (lab, k) in enumerate(CLIENT_COLS):
            v = {"name": cl.get("name"), "address": cl.get("address"), "contact": cl.get("contact"), "email": cl.get("email"),
                 "tax_number_label": cl.get("tax_number_label"), "tax_number": cl.get("tax_number"),
                 "po_needed": inp.get("po_needed"), "client_reference": inp.get("client_reference"),
                 "pays_in": cl.get("pays_in"), "notes": cl.get("notes")}.get(k)
            row.append(cell(v) if v not in (None, "", []) else prev[i])
        clients[cl["name"]] = row
    plan_rows, line_rows = [], []
    for p in hist.get("plans", []):
        for s in p["stages"]:
            plan_rows.append([p["id"], p["client"], p.get("name", ""), p["currency"], p["project_total"], s["stage"], s["label"],
                              s.get("share") or "", s.get("trigger") or "", s.get("total") or "", s.get("number") or "",
                              s.get("issue_date") or "", s.get("status") or "", s.get("paid_date") or "", s.get("tax_mode") or "share"])
    cur_bp = plan.get("billing_plan")
    this_id = None
    if cur_bp:
        this_id = cur_bp.get("id") or ""
        for p in hist.get("plans", []):
            if p["id"] == this_id or (not this_id and p["client"] == (cl.get("name") or "")):
                this_id = p["id"]
    old_lines = old.get("## Project lines", [])
    for r in old_lines:
        if r["Plan"] != this_id:
            line_rows.append([r.get(lab, "") for lab, _k in LINE_COLS])
    if cur_bp and this_id:
        for ln in inp.get("lines") or []:
            line_rows.append([this_id, ln.get("description"), ln.get("qty") or "1", ln.get("unit") or "", ln.get("unit_price"),
                              ln.get("tax") or "", ln.get("stage") or ""])
    doc_rows = [[d.get(k, "") for _l, k in DOC_COLS] for d in hist.get("documents", [])]
    void_rows = [[v["number"], v["reason"], v.get("date", "")] for v in hist.get("voids", [])]
    learn = [r for r in old.get("## Learnings", [])]
    learn_rows = [[r.get("#"), r.get("Learning"), r.get("Evidence"), r.get("Applies to step"), r.get("Status"), r.get("Added")] for r in learn]
    for l in learnings or ():
        parts = [x.strip() for x in l.split("|")]
        if len(parts) != 4 or parts[3] not in ("watch", "active", "retired"):
            raise C.Stop("--learning must be 'rule | evidence | step | watch or active'")
        learn_rows.append([len(learn_rows) + 1] + parts[:3] + [parts[3], today])
    active = sum(1 for r in learn_rows if str(r[4]).lower() == "active")
    if active > 25:
        raise C.Stop("more than 25 active learnings; condense two before adding another")
    hist_rows = [[r.get("Date"), r.get("Made"), r.get("Option chosen"), r.get("Verdict")] for r in old.get("## History", [])]
    if history_line:
        parts = [x.strip() for x in history_line.split("|")]
        while len(parts) < 3:
            parts.append("")
        hist_rows.append([today] + parts[:3])
    md = [f"# Invoice and Terms Builder memory", "",
          f"Skill: {SKILL} | Memory version: 1 | Updated: {today}", "",
          ("You asked for your payment details to be left out, so the next run asks for them and reads them back. "
           if no_payment else "Keep this file private: it holds your payment details. ") +
          "Attach it next time (or leave it in your merigrove-memory "
          "folder, or your Claude Project) and the next invoice carries on from the last. You can edit it by hand.", "",
          "## Profile", "", table(["Field", "Value", "Source", "Updated"], prof_rows), "",
          "## Payment details", "", ("Not saved, at your request." if no_payment else "Read back to you on every run before they are printed."), "",
          table(["Field", "Value", "Updated"], pay_rows), "",
          "## Tax setup (supplied by you)", "", "From you and your accountant; this skill never sets a rate.", "",
          table([c[0] for c in TAX_COLS], tax_rows), "",
          "## Clients", "", table([c[0] for c in CLIENT_COLS], list(clients.values())), "",
          "## Billing plans", "", table([c[0] for c in PLAN_COLS], plan_rows), "",
          "## Project lines", "", table([c[0] for c in LINE_COLS], line_rows), "",
          "## Documents", "", table([c[0] for c in DOC_COLS], doc_rows), "",
          "## Gaps and voids", "", table(["Number", "Reason", "Date"], void_rows), "",
          ]
    labels = inp.get("labels")
    if not labels and old.get("_labels_raw"):
        labels = old["_labels_raw"]
    if labels and (inp.get("language") or "en")[:2] != "en":
        md += ["## Invoice labels", "", "The words printed on your invoices, in your invoice language. Edit any you would word differently.", "",
               "```json", json.dumps(labels, ensure_ascii=False, indent=1), "```", ""]
    md += ["## Learnings", "", LEARN_HEAD, "|---|---|---|---|---|---|"]
    for r in learn_rows:
        md.append("| " + " | ".join(cell(x) for x in r) + " |")
    md += ["", "Status: watch (seen once), active (approved or repeated), retired (kept for the record, no longer applied).", "",
           "## History", "", HIST_HEAD, "|---|---|---|---|"]
    for r in hist_rows:
        md.append("| " + " | ".join(cell(x) for x in r) + " |")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    return out


def validate(path):
    probs = []
    text = open(path, encoding="utf-8").read()
    if SKILL not in text:
        probs.append("the skill name line is missing")
    for s in SECTIONS:
        if s not in text:
            probs.append(f"section '{s}' is missing")
    t = parse_tables(text)
    active = 0
    for r in t.get("## Learnings", []):
        st = (r.get("Status") or "").lower()
        if st not in ("watch", "active", "retired"):
            probs.append(f"learning '{r.get('Learning')}' has status '{st}'")
        active += st == "active"
    if active > 25:
        probs.append(f"{active} active learnings; the cap is 25")
    nums = [r.get("Number") for r in t.get("## Documents", [])]
    dup = {n for n in nums if nums.count(n) > 1}
    if dup:
        probs.append(f"numbers used twice: {', '.join(sorted(dup))}")
    for r in t.get("## Payment details", []):
        if "card" in (r.get("Field") or "").lower() and re.search(r"\d{12,}", r.get("Value") or ""):
            probs.append("a card number is stored; remove it")
    return probs


ACCOUNT_FIELD = re.compile(r"(?i)iban|account (number|no)|acc(oun)?t\.? ?(no|#|number)?$|a/c|konto|kontonummer|compte|cuenta|account$")
NOT_ACCOUNT = re.compile(r"(?i)name|holder|bank$|swift|bic|routing|sort|branch|ifsc|aba|bsb")


def account_tail(fields):
    """The last four characters of the account number or IBAN (never the SWIFT, routing or branch code)."""
    vals = [(str(f).strip(), str(v)) for f, v in fields if v]
    pick = [v for f, v in vals if ACCOUNT_FIELD.search(f) and not NOT_ACCOUNT.search(f)]
    if not pick:
        pick = [v for f, v in vals if not NOT_ACCOUNT.search(f) and re.search(r"\d{4}", v)]
    return re.sub(r"\s", "", pick[0])[-4:] if pick else ""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    r = sub.add_parser("read")
    r.add_argument("memory")
    r.add_argument("--json-out", required=True)
    r.add_argument("--history-out", required=True)
    r.add_argument("--today", required=True)
    r.add_argument("--client")
    r.add_argument("--plan")
    w = sub.add_parser("write")
    w.add_argument("--inputs", required=True)
    w.add_argument("--plan", required=True)
    w.add_argument("--history", required=True)
    w.add_argument("--out", required=True)
    w.add_argument("--existing")
    w.add_argument("--history-line")
    w.add_argument("--learning", action="append", default=[])
    w.add_argument("--no-payment", action="store_true", help="leave the payment details out of the saved file")
    v = sub.add_parser("validate")
    v.add_argument("memory")
    a = ap.parse_args()
    if a.cmd == "read":
        inp, hist, learnings, found = read(a.memory, a.today, a.client, a.plan)
        C.save_json(inp, a.json_out)
        C.save_json(hist, a.history_out)
        tail = account_tail(get(inp, "payment.fields") or [])
        print(f"USING: {get(inp, 'issuer.name') or '[no business name]'}, {inp.get('currency') or '[no currency]'}, "
              f"last invoice {get(inp, 'number.last') or '[none]'}" + (f", payment details ending {tail}" if tail else ""))
        for f in found:
            print(f"FOUND: {f}")
        for l in learnings:
            print(f"LEARNING: {l.get('Learning')} (applies to {l.get('Applies to step')})")
        print(f"WROTE: {a.json_out} and {a.history_out}")
        return 0
    if a.cmd == "write":
        out = write(C.load_json(a.inputs, "inputs file"), C.load_json(a.plan, "plan file"), C.load_json(a.history, "history file"),
                    a.out, a.existing, a.history_line, a.learning, a.no_payment)
        probs = validate(out)
        for p in probs:
            print("PROBLEM:", p)
        print(f"WROTE: {out}")
        return 1 if probs else 0
    if a.cmd == "validate":
        if not os.path.exists(a.memory):
            raise C.Stop(f"there is no memory file at {a.memory}")
        probs = validate(a.memory)
        for p in probs:
            print("PROBLEM:", p)
        print(f"{len(probs)} problems")
        return 1 if probs else 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    C.run_main(main)
