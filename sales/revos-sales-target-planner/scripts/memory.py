#!/usr/bin/env python3
"""Read, write and check the Sales Target Planner memory file.

Usage:
  python3 scripts/memory.py read <memory.md> [--json-out previous.json]
        turn a saved memory file back into an inputs file for target_plan.py (with the last plan's figures)
  python3 scripts/memory.py changes <old-inputs.json> <new-inputs.json>
        list what changed between two runs
  python3 scripts/memory.py write <inputs.json> --results <results.json> --out <memory.md>
        [--existing <old memory.md>] [--history "made | lever chosen | verdict"]
        [--learning "rule | evidence | step | status"]
        write the memory file; keeps old Learnings and History and appends the new rows
  python3 scripts/memory.py validate <memory.md>
        check the file still has the shape this skill reads

The memory file is plain markdown the founder can read and edit by hand. Write only after the founder has
approved what is saved. Standard library only. No network calls. Any error prints one STOP line and exits 2.
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

SKILL = "revos-sales-target-planner"
PROFILE = [  # label, inputs key
    ("Business", "business"), ("Currency", "currency"), ("Numbers written", "number_style"), ("Country", "country"),
    ("Dates written", "date_style"), ("Spelling", "spelling"),
    ("Your name on the plan", "owner"),
    ("Who books calls", "books_calls"), ("Profit you need a month", "target_profit_month"),
    ("Profit figure is", "target_basis"), ("Your pay on top of that profit", "founder_pay_month"),
    ("Profit a year", "target_profit_year"), ("Yearly figure is", "target_kind"),
    ("Profit to make by the target date", "target_profit_by_date"),
    ("Revenue target a month", "target_revenue_month"),
    ("Sales a month now", "sales_month_now"), ("Target date", "target_date"), ("Margin", "margin"),
    ("Clients pay", "billing"), ("Months a client stays", "months_retained"),
    ("Clients paying now", "active_clients_now"),
    ("Price per sale, before any sales tax", "price"),
    ("Delivery cost per sale", "delivery_cost"), ("Running costs a month", "running_costs_month"),
    ("Show rate, your estimate", "show_rate"),
    ("Close rate on held calls, your estimate", "close_rate"), ("Booking rate, your estimate", "booking_rate"),
    ("Calls are mostly", "channel_type"), ("Leads a month now", "leads_month_now"),
    ("Hours a week for sales calls", "selling_hours_week"), ("Hours per call held", "call_hours"),
    ("Selling days a month", "working_days_month"), ("Days you take calls", "call_days"),
    ("Days you take no calls", "no_call_days"), ("Dated days off", "days_off"),
    ("New clients a month you can deliver for", "new_clients_month_max"),
    ("Share of the price paid in the month they sign", "cash_share"),
]
ACT_COLS = [("Month", "month"), ("Leads", "leads"), ("Booked", "booked"), ("Held", "showed"),
            ("Offers", "offers"), ("Sales", "closed")]
CH_COLS = [("Channel", "name"), ("Leads in 90 days", "leads"), ("Booked", "booked"), ("Held", "showed")]
LAST = [("Date", "date"), ("Price planned on", "price"), ("Sales a month", "closes"), ("Held calls a month", "held"),
        ("Bookings a month", "booked"), ("Leads a month", "leads"), ("Bookings a week", "pace_booked"),
        ("What breaks first", "binding"), ("Re-plan by", "replan")]
LEARN_HEAD = "| # | Learning | Evidence | Applies to step | Status | Added |"
HIST_HEAD = "| Date | Made | Lever chosen | Verdict |"
STATUSES = {"watch", "active", "retired"}
STEPS = {"intake", "diagnose", "make", "check", "deliver", "learn"}
NEVER_SAVE = {"date", "sources", "actuals", "channels", "confirmed"}
LIST_KEYS = {"no_call_days", "days_off"}
# labels from version 1.0 files: read where they still mean the same thing; tax labels are no longer used
OLD_LABELS = {"Price per sale": "price"}
RETIRED = {"VAT registered", "Price includes VAT"}


class Stop(Exception):
    pass


def cell(v):
    if v is None:
        return ""
    if isinstance(v, list):
        v = ", ".join(str(x) for x in v)
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v).replace("|", "/").replace("\n", " ").strip()


def table(text, heading):
    m = re.search(rf"^## {re.escape(heading)}\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not m:
        return None, []
    lines = [ln.strip() for ln in m.group(1).splitlines() if ln.strip().startswith("|")]
    if len(lines) < 2:
        return (lines[0] if lines else None), []
    head = [c.strip() for c in lines[0].strip("|").split("|")]
    rows = []
    for ln in lines[2:]:
        cells = [c.strip() for c in ln.strip("|").split("|")]
        rows.append(dict(zip(head, cells + [""] * (len(head) - len(cells)))))
    return lines[0], rows


def load(path):
    p = Path(path)
    if not p.exists():
        raise Stop(f"there is no file at {path}")
    return p.read_text(encoding="utf-8")


def cmd_read(a):
    text = load(a.memory)
    if f"Skill: {SKILL}" not in text:
        raise Stop("this is not a Sales Target Planner memory file (no 'Skill: revos-sales-target-planner' line)")
    _h, prof = table(text, "Profile")
    upd = re.search(r"Updated:\s*(\d{4}-\d{2}-\d{2})", text)
    when = upd.group(1) if upd else "an earlier run"
    data, sources = {}, {}
    lab2key = dict(PROFILE)
    lab2key.update(OLD_LABELS)
    for r in prof:
        if r.get("Field", "") in RETIRED and r.get("Value", ""):
            print(f"IGNORED: '{r['Field']}' from an earlier version; this planner no longer uses tax status")
        k = lab2key.get(r.get("Field", ""))
        if k and r.get("Value", "") != "":
            v = r["Value"]
            data[k] = [x.strip() for x in v.split(",")] if k in LIST_KEYS else v
            sources[k] = f"saved memory: {r.get('Source', '') or 'founder said'}, {r.get('Updated', '') or when}"
    _h, acts = table(text, "Actuals")
    data["actuals"] = [{k: r.get(lab, "") for lab, k in ACT_COLS if r.get(lab, "") != ""} for r in acts
                       if r.get("Month")]
    _h, chans = table(text, "Channels")
    data["channels"] = [{k: r.get(lab, "") for lab, k in CH_COLS if r.get(lab, "") != ""} for r in chans
                        if r.get("Channel")]
    _h, last = table(text, "Last plan")
    lp = {}
    lab2 = dict(LAST)
    for r in last:
        k = lab2.get(r.get("Field", ""))
        if k:
            lp[k] = r.get("Value", "")
    data["_last_plan"] = lp
    data["sources"] = sources
    _h, learn = table(text, "Learnings")
    data["_learnings_active"] = [f"{r.get('Learning')} (step: {r.get('Applies to step')})" for r in learn
                                 if r.get("Status", "").lower() == "active"]
    data["_learnings_watch"] = [r.get("Learning") for r in learn if r.get("Status", "").lower() == "watch"]
    data["_memory_updated"] = when
    out = json.dumps(data, indent=2)
    if a.json_out:
        Path(a.json_out).write_text(out, encoding="utf-8")
        print(f"WROTE: {a.json_out} (saved {when}; {len(data['actuals'])} months of actuals, "
              f"{len(data['_learnings_active'])} active learnings)")
        for x in data["_learnings_active"]:
            print(f"ACTIVE LEARNING: {x}")
    else:
        print(out)
    return 0


def _norm(v):
    if isinstance(v, list):
        return ",".join(sorted(str(x).strip().lower() for x in v))
    s = re.sub(r"s\$|a\$|hk\$|[£$€₹¥₱]", "", str(v if v is not None else "").strip().lower().replace(",", ""))
    try:
        return f"{float(s.rstrip('%')):g}"
    except ValueError:
        return s


def changes(old, new):
    out = []
    for lab, k in PROFILE:
        if _norm(old.get(k)) != _norm(new.get(k)) and (old.get(k) or new.get(k)):
            out.append(f"{lab}: {cell(old.get(k)) or 'not set'} to {cell(new.get(k)) or 'not set'}")
    om = {x.get("month") for x in old.get("actuals") or []}
    for x in new.get("actuals") or []:
        if x.get("month") not in om:
            out.append(f"New actuals for {x.get('month') or 'a month'}")
    return out


def cmd_changes(a):
    old = json.loads(load(a.old))
    new = json.loads(load(a.new))
    ch = changes(old, new)
    for c in ch:
        print("CHANGED:", c)
    print(f"{len(ch)} changes")
    return 0


def worked_out(expr):
    """The value of a sum such as '=250000/12', with the planner's own reader (same number style rules)."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import target_plan as T  # noqa: E402
        return T.to_num(expr, None, "value")
    except Exception:  # noqa: BLE001
        return None


def plain(v, style):
    """A value written without grouping, with the founder's decimal mark: 20833.33 or 20833,33."""
    t = f"{round(v, 2):.2f}".rstrip("0").rstrip(".")
    return t.replace(".", ",") if style == "comma" else t


def cmd_write(a):
    inp = json.loads(load(a.inputs))
    res = json.loads(load(a.results)) if a.results else {}
    today = date.today().isoformat()
    old_text = Path(a.existing).read_text(encoding="utf-8") if a.existing and Path(a.existing).exists() else ""
    old_prof = {}
    if old_text:
        _h, rows = table(old_text, "Profile")
        old_prof = {r.get("Field"): r for r in rows}
    src = inp.get("sources") or {}
    lines = [f"# Sales Target Planner memory", "",
             f"Skill: {SKILL} | Memory version: 1 | Updated: {res.get('date') or today}", "",
             "Keep this file. Attach it next time (or leave it in your merigrove-memory folder, or your Claude "
             "Project) and the planner picks up where you left off. You can edit it by hand.", "",
             "## Profile", "", "| Field | Value | Source | Updated |", "|---|---|---|---|"]
    today_iso = res.get("date") or today
    style = (res.get("inputs") or {}).get("number_style") or inp.get("number_style") or ""
    detected = {"number_style": "detected from your figures", "currency": "read from your figures"}
    for lab, k in PROFILE:
        v = inp.get(k)
        if v in (None, "", []) and k in detected and (res.get("inputs") or {}).get(k):
            v = res["inputs"][k]
            src = dict(src, **{k: detected[k]})
        if v in (None, "", []) or k in NEVER_SAVE:
            continue
        if k == "days_off":
            v = [str(x) for x in (v if isinstance(v, list) else [v]) if str(x) >= today_iso]
            if not v:
                continue
        o = old_prof.get(lab)
        s = str(src.get(k) or "founder said")
        if s.startswith("saved memory"):
            s = (o or {}).get("Source") or "founder said"
        if isinstance(v, str) and v.strip().startswith("="):
            # a sum Claude wrote out: keep the value, readable by hand, and say how it was worked out
            got = worked_out(v)
            if got is not None:
                s = f"{s}; worked out from {v.strip().lstrip('=').strip()}"
                v = plain(got, style)
        upd = (o or {}).get("Updated") if o and _norm(o.get("Value")) == _norm(v) else (res.get("date") or today)
        lines.append(f"| {lab} | {cell(v)} | {cell(s)} | {upd} |")
    lines += ["", "## Actuals", "", "What actually happened, month by month. The planner measures your rates from the "
              "last three months.", "", "| " + " | ".join(l for l, _ in ACT_COLS) + " |",
              "|" + "---|" * len(ACT_COLS)]
    for x in inp.get("actuals") or []:
        lines.append("| " + " | ".join(cell(x.get(k)) for _, k in ACT_COLS) + " |")
    lines += ["", "## Channels", "", "| " + " | ".join(l for l, _ in CH_COLS) + " |", "|" + "---|" * len(CH_COLS)]
    for x in inp.get("channels") or []:
        lines.append("| " + " | ".join(cell(x.get(k)) for _, k in CH_COLS) + " |")
    lines += ["", "## Last plan", "", "| Field | Value |", "|---|---|"]
    if res:
        ch = res.get("chain") or {}
        vals = {"date": res.get("date"), "price": round(res["price"], 2) if res.get("price") else "",
                "closes": ch.get("closes"), "held": ch.get("held"),
                "booked": ch.get("booked"), "leads": ch.get("leads") or "not known",
                "pace_booked": (res.get("pace") or {}).get("booked"), "binding": res.get("binding") or "none",
                "replan": res.get("replan")}
        for lab, k in LAST:
            lines.append(f"| {lab} | {cell(vals.get(k))} |")
    # learnings: keep old rows, append new ones
    learn_rows = []
    if old_text:
        _h, rows = table(old_text, "Learnings")
        for r in rows:
            if r.get("Learning") and not r.get("Learning", "").startswith("<"):
                learn_rows.append([r.get("Learning"), r.get("Evidence"), r.get("Applies to step"),
                                   r.get("Status"), r.get("Added")])
    for L in a.learning or []:
        parts = [x.strip() for x in L.split("|")]
        if len(parts) != 4:
            raise Stop(f"a learning needs four parts, 'rule | evidence | step | status': '{L}'")
        if parts[3].lower() not in STATUSES:
            raise Stop(f"learning status must be watch, active or retired, not '{parts[3]}'")
        if parts[2].lower() not in STEPS:
            raise Stop(f"learning step must be one of {', '.join(sorted(STEPS))}, not '{parts[2]}'")
        learn_rows.append(parts + [res.get("date") or today])
    active = [r for r in learn_rows if str(r[3]).lower() == "active"]
    if len(active) > 25:
        raise Stop("more than 25 active learnings; condense or retire some before adding")
    lines += ["", "## Learnings", "", LEARN_HEAD, "|---|---|---|---|---|---|"]
    for i, r in enumerate(learn_rows, 1):
        lines.append(f"| {i} | " + " | ".join(cell(x) for x in r) + " |")
    lines += ["", "Status: watch (seen once), active (approved or repeated), retired (kept for the record, no longer "
              "applied).", "", "## History", "", HIST_HEAD, "|---|---|---|---|"]
    if old_text:
        _h, rows = table(old_text, "History")
        for r in rows:
            if r.get("Date") and not r["Date"].startswith("YYYY"):
                lines.append(f"| {r.get('Date')} | {r.get('Made')} | {r.get('Lever chosen')} | {r.get('Verdict')} |")
    if a.history:
        parts = [x.strip() for x in a.history.split("|")] + ["", "", ""]
        lines.append(f"| {res.get('date') or today} | {cell(parts[0])} | {cell(parts[1])} | {cell(parts[2])} |")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"WROTE: {a.out}")
    return 0


def cmd_validate(a):
    text = load(a.memory)
    probs = []
    if f"Skill: {SKILL}" not in text:
        probs.append("no 'Skill: revos-sales-target-planner' line")
    for h in ("Profile", "Actuals", "Last plan", "Learnings", "History"):
        if not re.search(rf"^## {h}\s*$", text, re.M):
            probs.append(f"no '## {h}' section")
    _h, learn = table(text, "Learnings")
    for r in learn:
        st = r.get("Status", "").lower()
        if st and st not in STATUSES:
            probs.append(f"learning '{r.get('Learning')}' has status '{st}'")
    if sum(1 for r in learn if r.get("Status", "").lower() == "active") > 25:
        probs.append("more than 25 active learnings")
    if "\u2014" in text or "\u2013" in text:
        probs.append("em or en dash in the file")
    for p in probs:
        print("PROBLEM:", p)
    print(f"{len(probs)} problems")
    return 1 if probs else 0


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("read")
    r.add_argument("memory")
    r.add_argument("--json-out")
    c = sub.add_parser("changes")
    c.add_argument("old")
    c.add_argument("new")
    w = sub.add_parser("write")
    w.add_argument("inputs")
    w.add_argument("--results")
    w.add_argument("--out", required=True)
    w.add_argument("--existing")
    w.add_argument("--history")
    w.add_argument("--learning", action="append")
    v = sub.add_parser("validate")
    v.add_argument("memory")
    a = p.parse_args()
    return {"read": cmd_read, "changes": cmd_changes, "write": cmd_write, "validate": cmd_validate}[a.cmd](a)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Stop as e:
        print(f"STOP: {e}. Nothing was written.")
        sys.exit(2)
    except (json.JSONDecodeError, OSError) as e:
        print(f"STOP: could not read a file ({type(e).__name__}: {e}). Nothing was written.")
        sys.exit(2)
