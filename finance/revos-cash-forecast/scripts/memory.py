#!/usr/bin/env python3
"""Read, write and check the 13-Week Cash Forecast memory file.

Usage:
  python3 scripts/memory.py read <memory.md> --json-out <scratch>/previous.json
        turn a saved memory file into what find_recurring.py (--memory-json) and forecast.py (--previous) read
  python3 scripts/memory.py write <scratch>/results.json --out <memory.md> [--existing <old memory.md>]
        [--history "made | option chosen | verdict"] [--learning "rule | evidence | step | status"]
        [--item "label | match | category | cadence | amount | keep or ignore"] [--late "client | days late | evidence"]
        [--map "the MAP line parse_bank_csv.py printed"]
        write the memory file; keeps old Learnings, History, checks and ignored items, and appends the new rows
  python3 scripts/memory.py validate <memory.md>

The memory file is plain markdown the founder can read and edit. Write only what the founder approved.
Standard library only. No network calls.
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

SKILL = "revos-cash-forecast"
PROFILE = [  # label, key
    ("Business", "business"), ("Currency", "currency"), ("Dates written", "date_order"), ("Bank", "bank"),
    ("Bank column map", "map_string"), ("Export layout id", "header_signature"), ("Safety line", "floor"),
    ("Payment terms on new invoices (days)", "payment_terms_days"), ("Bad quarter: money in lower by", "stress_cut"),
    ("Bad quarter: money in later by (days)", "stress_delay"), ("Bad quarter: payment plan failures", "plan_default"),
    ("Country", "country"), ("Decimals written with", "decimal_style"), ("Last forecast opened on", "last_opening"),
]
ITEM_COLS = ["Label", "Match", "Category", "Cadence", "Amount", "Day", "Next date", "Status", "Source"]
LATE_COLS = ["Client", "Days late", "Evidence", "Updated"]
KNOWN_COLS = ["Label", "Kind", "Amount", "Rhythm", "Next or only date", "Supplied by", "Updated"]
PROJ_COLS = ["Week ends", "Money in forecast", "Balance forecast"]
CHECK_COLS = ["Checked on", "From", "To", "Money in forecast", "Money in actual", "Difference"]
LEARN_HEAD = "| # | Learning | Evidence | Applies to step | Status | Added |"
HIST_HEAD = "| Date | Made | Option chosen | Verdict |"
STATUSES = {"watch", "active", "retired"}
STEPS = {"intake", "diagnose", "make", "check", "deliver", "learn"}


def cell(v):
    if v is None:
        return ""
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


def floor_from_text(s):
    s = (s or "").strip().lower()
    if not s or s.startswith("one month"):
        return {"mode": "one_month", "value": None}
    m = re.match(r"([\d.]+)\s*weeks?", s)
    if m:
        return {"mode": "weeks", "value": float(m.group(1))}
    return {"mode": "figure", "value": s}


def floor_to_text(model):
    b = model.get("floor_basis") or ""
    if b == "the figure you set":
        return cell(model.get("floor"))
    if "weeks" in b:
        return b.replace(" of outgoings", "") + " of outgoings"
    return "one month of outgoings"


def cmd_read(a):
    text = Path(a.memory).read_text(encoding="utf-8")
    _h, prof = table(text, "Profile")
    upd = re.search(r"Updated:\s*(\d{4}-\d{2}-\d{2})", text)
    when = upd.group(1) if upd else None
    p = {}
    lab2key = dict(PROFILE)
    for r in prof:
        k = lab2key.get(r.get("Field", ""))
        if k and r.get("Value", "") != "":
            p[k] = r["Value"]
    order = (p.get("date_order") or "").lower()
    profile = {"business": p.get("business"), "currency": p.get("currency"), "country": p.get("country"),
               "decimal_style": {"dot": "dot", "comma": "comma", "a dot": "dot", "a comma": "comma"}.get(
                   (p.get("decimal_style") or "").lower().strip()),
               "date_order": "day-first" if order.startswith("day") else ("month-first" if order.startswith("month") else None),
               "floor": floor_from_text(p.get("floor")) if p.get("floor") else None,
               "payment_terms_days": p.get("payment_terms_days"), "client_late_days": {}, "known_outgoings": []}
    _h, known = table(text, "Known payments you listed")
    for r in known:
        if not r.get("Label"):
            continue
        k = {"label": r["Label"], "kind": r.get("Kind") or "other", "amount": r.get("Amount") or None,
             "source": f"{r.get('Supplied by') or 'you'}, saved {r.get('Updated') or when}"}
        rhythm = (r.get("Rhythm") or "").strip().lower()
        if rhythm and rhythm not in ("once", "one date"):
            k.update(cadence=rhythm, next_date=r.get("Next or only date"))
        else:
            k["date"] = r.get("Next or only date")
        profile["known_outgoings"].append(k)
    if p.get("stress_cut") or p.get("stress_delay"):
        profile["stress"] = {"receipts_cut": p.get("stress_cut") or "20%", "delay_days": p.get("stress_delay") or 15,
                             "plan_default": p.get("plan_default") or "10%"}
    _h, lates = table(text, "Client payment habits")
    for r in lates:
        try:
            profile["client_late_days"][r["Client"]] = int(float(r.get("Days late") or 0))
        except ValueError:
            pass
    _h, items = table(text, "Regular items")
    reg = [{"label": r.get("Label"), "match": r.get("Match"), "category": r.get("Category"), "cadence": r.get("Cadence"),
            "amount": r.get("Amount"), "day": r.get("Day") or None, "next_date": r.get("Next date") or None,
            "status": r.get("Status") or "keep"} for r in items if r.get("Match")]
    _h, proj = table(text, "Last forecast")
    _h, checks = table(text, "Forecast checks")
    _h, learn = table(text, "Learnings")
    out = {"profile": profile, "regular_items": reg, "map_string": p.get("map_string"),
           "header_signature": p.get("header_signature"), "bank": p.get("bank"),
           "_opening_date": p.get("last_opening"),
           "_projection": [{"week_end": r["Week ends"], "receipts": float(r["Money in forecast"] or 0),
                            "closing": float(r["Balance forecast"] or 0)} for r in proj if r.get("Week ends")],
           "_checks": [{"from": r["From"], "to": r["To"], "forecast": float(r["Money in forecast"] or 0),
                        "actual": float(r["Money in actual"] or 0), "diff": float(r["Difference"] or 0)} for r in checks if r.get("From")],
           "_learnings_active": [r.get("Learning") for r in learn if r.get("Status", "").lower() == "active"],
           "_learnings_watch": [r.get("Learning") for r in learn if r.get("Status", "").lower() == "watch"],
           "_memory_updated": when}
    Path(a.json_out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"WROTE: {a.json_out}")
    print(f"REMEMBERED: saved {when}; bank {p.get('bank') or 'not saved'}; safety line {p.get('floor') or 'not saved'}; "
          f"currency {p.get('currency') or 'not saved'}; dates {p.get('date_order') or 'not saved'}; "
          f"{len(profile['known_outgoings'])} known payments you listed; {len(reg)} regular items ({sum(1 for r in reg if r['status'].lower() != 'keep')} ignored); "
          f"{len(profile['client_late_days'])} client payment habits; {len(out['_learnings_active'])} active learnings")
    for x in out["_learnings_active"]:
        print("APPLY:", x)


def profile_values(model, a, old):
    exp = model.get("export") or {}
    v = {"business": model.get("business"), "currency": model.get("currency") or old.get("currency"),
         "date_order": {"day-first": "day first", "month-first": "month first"}.get(model.get("date_order"))
         or old.get("date_order"), "bank": exp.get("bank") or old.get("bank"),
         "map_string": a.map or exp.get("map_string") or old.get("map_string"),
         "header_signature": exp.get("header_signature") or old.get("header_signature"), "floor": floor_to_text(model),
         "payment_terms_days": model.get("terms") if model.get("terms_src") == "your figure" else old.get("payment_terms_days"),
         "stress_cut": f"{round(model.get('cut', 0.2) * 100)}%", "stress_delay": model.get("delay"),
         "plan_default": f"{round(model.get('plan_default', 0.1) * 100)}%", "last_opening": model.get("opening_date"),
         "country": model.get("country") or old.get("country"),
         "decimal_style": {"dot": "a dot (1,234.50)", "comma": "a comma (1.234,50)"}.get(model.get("decimal_style"))
         or old.get("decimal_style")}
    return v


def cmd_write(a):
    data = json.loads(Path(a.inputs).read_text(encoding="utf-8"))
    if "model" not in data or "results" not in data:
        print("STOP: write takes the results.json that forecast.py build wrote. Nothing was written.")
        sys.exit(2)
    model, res = data["model"], data["results"]
    today = str(model.get("today") or date.today().isoformat())
    old_text = Path(a.existing).read_text(encoding="utf-8") if a.existing and Path(a.existing).exists() else ""
    old = {}
    if old_text:
        _h, prof = table(old_text, "Profile")
        lab2key = dict(PROFILE)
        for r in prof:
            k = lab2key.get(r.get("Field", ""))
            if k:
                old[k] = r.get("Value")
    pv = profile_values(model, a, old)
    L = ["# 13-Week Cash Forecast memory", "", f"Skill: {SKILL} | Memory version: 1 | Updated: {today}", "",
         "Keep this file. Attach it next time (or leave it in your merigrove-memory folder, or your Claude Project) and "
         "the forecast picks up where you left off: your bank's layout, your regular bills, the payments you listed "
         "and how your clients pay. You can edit it by hand.", "", "## Profile", "", "| Field | Value | Source | Updated |", "|---|---|---|---|"]
    for lab, k in PROFILE:
        v = pv.get(k)
        if v in (None, ""):
            continue
        src = "your answers and export" if k not in ("stress_cut", "stress_delay", "plan_default") else (
            "default" if str(v) in ("20%", "15", "10%") else "your figure")
        L.append(f"| {lab} | {cell(v)} | {src} | {today} |")
    # regular items: the forecast's lines, plus any the founder told us to ignore
    L += ["", "## Regular items", "", "| " + " | ".join(ITEM_COLS) + " |", "|" + "---|" * len(ITEM_COLS)]
    # rows are keyed by match and day, so two lines with one payee (pay on the 15th and at month end) stay two rows
    rows = {}
    st = ITEM_COLS.index("Status")
    if old_text:
        _h, olds = table(old_text, "Regular items")
        for r in olds:
            if r.get("Match"):
                rows[(r["Match"].lower(), (r.get("Day") or "").strip())] = [r.get(c, "") for c in ITEM_COLS]
    for o in model.get("out", []) + model.get("ins", []):
        mt = (o.get("match") or o.get("label") or "").lower()
        nxt = str(o.get("next") or "")[:10]
        day = str(int(nxt[8:10])) if len(nxt) == 10 else ""
        key = (mt, day)
        same = [k for k in rows if k[0] == mt]
        if any(rows[k][st].lower() != "keep" for k in same):
            continue
        for k in same:
            if k[1] == "" or (k[1].isdigit() and day.isdigit() and abs(int(k[1]) - int(day)) <= 7):
                rows.pop(k)  # superseded by this run's line for the same payee and day
        rows[key] = [o.get("label"), mt, o.get("category") or "regular client", o.get("cadence"), o.get("amount"), day,
                     nxt, "keep", "confirmed in the forecast"]
    for x in a.item or []:
        parts = [p.strip() for p in x.split("|")] + [""] * 6
        mt = parts[1].lower() or parts[0].lower()
        for k in [k for k in rows if k[0] == mt and parts[5].lower() in ("ignore", "stopped", "one-off")]:
            rows.pop(k)
        rows[(mt, "")] = [parts[0], mt, parts[2], parts[3], parts[4], "", "", parts[5] or "keep", "founder said"]
    for r in rows.values():
        L.append("| " + " | ".join(cell(x) for x in r) + " |")
    L += ["", "## Client payment habits", "", "| " + " | ".join(LATE_COLS) + " |", "|" + "---|" * len(LATE_COLS)]
    lates = {}
    if old_text:
        _h, olds = table(old_text, "Client payment habits")
        for r in olds:
            lates[r["Client"].lower()] = [r.get(c, "") for c in LATE_COLS]
    for inv in (data.get("model") or {}).get("invoices", []):
        c = str(inv.get("client") or "").strip()
        if c and c.lower() not in lates:  # invoiced clients are remembered, so a return run keeps them out of the pattern
            lates[c.lower()] = [c, str(int(inv.get("late") or 0)), "invoices listed; days late as given", today]
    for x in a.late or []:
        parts = [p.strip() for p in x.split("|")] + ["", "", ""]
        lates[parts[0].lower()] = [parts[0], parts[1], parts[2], today]
    for r in lates.values():
        L.append("| " + " | ".join(cell(x) for x in r) + " |")
    L += ["", "## Known payments you listed", "",
          "Tax, payroll and other payments you gave, with the figure's source. Founder supplied: confirm them with your "
          "accountant or payroll provider when they change.", "",
          "| " + " | ".join(KNOWN_COLS) + " |", "|" + "---|" * len(KNOWN_COLS)]
    for k in model.get("known", []):
        rhythm = k.get("cadence") or "once"
        nxt = k.get("next") or (k.get("dates") or [None])[-1]
        L.append("| " + " | ".join(cell(x) for x in [k.get("label"), k.get("kind"), k.get("amount"), rhythm, nxt,
                                                       k.get("who") or "you", today]) + " |")
    L += ["", "## Last forecast", "", f"Opened on {model.get('opening_date')} with {cell(model.get('opening'))} in the bank.", "",
          "| " + " | ".join(PROJ_COLS) + " |", "|" + "---|" * len(PROJ_COLS)]
    for p in data.get("projection", []):
        L.append(f"| {p['week_end']} | {p['receipts']} | {p['closing']} |")
    L += ["", "## Forecast checks", "", "| " + " | ".join(CHECK_COLS) + " |", "|" + "---|" * len(CHECK_COLS)]
    if old_text:
        _h, olds = table(old_text, "Forecast checks")
        for r in olds:
            L.append("| " + " | ".join(cell(r.get(c, "")) for c in CHECK_COLS) + " |")
    var = data.get("variance")
    if var:
        L.append(f"| {today} | {var['from']} | {var['to']} | {var['forecast']} | {var['actual']} | {var['diff']} |")
    L += ["", "## Learnings", "", LEARN_HEAD, "|---|---|---|---|---|---|"]
    n = 0
    learn_rows = table(old_text, "Learnings")[1] if old_text else []
    for r in learn_rows:
        n += 1
        L.append(f"| {n} | {r.get('Learning', '')} | {r.get('Evidence', '')} | {r.get('Applies to step', '')} | "
                 f"{r.get('Status', '')} | {r.get('Added', '')} |")
    for x in a.learning or []:
        parts = [p.strip() for p in x.split("|")] + ["", "", "", ""]
        n += 1
        L.append(f"| {n} | {cell(parts[0])} | {cell(parts[1])} | {cell(parts[2] or 'Make')} | {cell(parts[3] or 'watch')} | {today} |")
    L += ["", "Status: watch (seen once), active (approved or repeated), retired (kept for the record, no longer applied).",
          "", "## History", "", HIST_HEAD, "|---|---|---|---|"]
    hist = table(old_text, "History")[1] if old_text else []
    for r in hist:
        L.append(f"| {r.get('Date', '')} | {r.get('Made', '')} | {r.get('Option chosen', '')} | {r.get('Verdict', '')} |")
    if a.history:
        parts = [p.strip() for p in a.history.split("|")] + ["", "", ""]
        L.append(f"| {today} | {cell(parts[0])} | {cell(parts[1])} | {cell(parts[2])} |")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text("\n".join(L) + "\n", encoding="utf-8")
    probs = validate(Path(a.out).read_text(encoding="utf-8"))
    for p in probs:
        print("PROBLEM:", p)
    print(f"WROTE: {a.out} ({len(rows)} regular items, {len(lates)} client habits, {n} learnings, "
          f"{len(hist) + (1 if a.history else 0)} history rows)")
    sys.exit(1 if probs else 0)


def validate(text):
    p = []
    if not re.search(rf"Skill:\s*{SKILL}", text):
        p.append(f"header line 'Skill: {SKILL}' missing")
    if not re.search(r"Updated:\s*\d{4}-\d{2}-\d{2}", text):
        p.append("header has no Updated: YYYY-MM-DD date")
    for h in ("Profile", "Regular items", "Client payment habits", "Known payments you listed", "Last forecast",
              "Forecast checks", "Learnings", "History"):
        if not re.search(rf"^## {h}\s*$", text, re.M):
            p.append(f"section '## {h}' missing")
    _h, items = table(text, "Regular items")
    for r in items:
        if (r.get("Status") or "").lower() not in ("keep", "ignore", "one-off", "stopped"):
            p.append(f"regular item '{r.get('Label')}': status '{r.get('Status')}' is not keep, ignore, one-off or stopped")
    _h, lates = table(text, "Client payment habits")
    for r in lates:
        if not re.fullmatch(r"-?\d+", (r.get("Days late") or "").strip()):
            p.append(f"client '{r.get('Client')}': days late '{r.get('Days late')}' is not a whole number")
    h, learn = table(text, "Learnings")
    if h and h != LEARN_HEAD:
        p.append("Learnings header changed; expected: " + LEARN_HEAD)
    active = 0
    for r in learn:
        st = r.get("Status", "").strip().lower().strip("~")
        if st not in STATUSES:
            p.append(f"learning {r.get('#')}: status '{r.get('Status')}' is not watch, active or retired")
        if st == "active":
            active += 1
        if r.get("Applies to step", "").strip().lower() not in STEPS:
            p.append(f"learning {r.get('#')}: step '{r.get('Applies to step')}' is not one of {sorted(STEPS)}")
    if active > 25:
        p.append(f"{active} active learnings; condense to 25 or fewer")
    h, _hist = table(text, "History")
    if h and h != HIST_HEAD:
        p.append("History header changed; expected: " + HIST_HEAD)
    return p


def cmd_validate(a):
    probs = validate(Path(a.memory).read_text(encoding="utf-8"))
    for x in probs:
        print("PROBLEM:", x)
    print(f"{len(probs)} problems")
    sys.exit(1 if probs else 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    r = sub.add_parser("read")
    r.add_argument("memory")
    r.add_argument("--json-out", required=True)
    w = sub.add_parser("write")
    w.add_argument("inputs")
    w.add_argument("--out", required=True)
    w.add_argument("--existing")
    w.add_argument("--history")
    w.add_argument("--learning", action="append")
    w.add_argument("--item", action="append")
    w.add_argument("--late", action="append")
    w.add_argument("--map")
    v = sub.add_parser("validate")
    v.add_argument("memory")
    a = ap.parse_args()
    for attr in ("memory", "inputs"):
        if getattr(a, attr, None) and not Path(getattr(a, attr)).exists():
            print(f"STOP: there is no file at {getattr(a, attr)}. Nothing was changed.")
            sys.exit(2)
    {"read": cmd_read, "write": cmd_write, "validate": cmd_validate}.get(a.cmd, lambda _a: (ap.print_help(), sys.exit(2)))(a)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print(f"STOP: the memory file could not be handled ({type(e).__name__}: {e}). Nothing was changed.")
        sys.exit(2)
