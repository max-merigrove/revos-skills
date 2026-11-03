#!/usr/bin/env python3
"""Read, write and check The Price Rise Pack memory file.

Usage:
  python3 scripts/memory.py read <memory.md> --json-out <inputs.json> [--next-wave]
        turn a saved memory file back into an inputs file for rise_plan.py. The saved plan is kept
        exactly as it was sent (fixed steps), so outcomes are measured against it. --next-wave
        starts the next wave instead: each client's agreed fee becomes the current fee.
  python3 scripts/memory.py write <inputs.json> --results <results.json> --out <memory.md>
        [--existing <old memory.md>] [--history "what was made | wave and cap | verdict"]
        [--learning "rule | evidence | step | watch or active"] [--retire "words"] [--activate "words"]
        [--initials]
        write the memory file; keeps the old Learnings and History and appends the new rows;
        --retire and --activate change the status of every saved learning containing those words
  python3 scripts/memory.py validate <memory.md>
        check the file still has the shape this skill reads (statuses, at most 25 active learnings)

Plain markdown the founder can read and edit. Written only after the founder approves.
Standard library only. No network calls.
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

SKILL = "revos-price-rise-pack"
PROFILE = [
    ("Business", "business"), ("Your name", "founder_name"), ("Sign-off", "sign_off"), ("Currency", "currency"),
    ("Country", "country"), ("Your English", "english"), ("Number style", "decimal"), ("Number grouping", "grouping"),
    ("Date order", "date_order"), ("Date separator", "date_sep"), ("Date style", "date_style"),
    ("Word for the fee", "fee_word"),
    ("New-client price", "anchor.new_client_fee"), ("New-client price per", "anchor.per"),
    ("New-client hours", "anchor.new_client_hours"), ("Hourly target", "anchor.hourly_target"),
    ("Biggest single step", "step_cap"), ("One step when it reaches", "closure"),
    ("Months between steps", "second_step_months"), ("Rounding", "rounding"), ("Billing day", "billing_day"),
    ("Your usual notice", "notice"), ("Notice runs to", "notice_align"), ("Notice when unknown", "notice_default"),
    ("Call first from tenure of (years)", "call_first_tenure_years"),
    ("Call first for your largest quarter", "call_first_top_quartile"), ("Value of an hour", "hour_value"),
    ("Your fees last changed", "last_change"), ("Cost figure you gave", "cost_fact"),
    ("Cash window (months)", "window_months"), ("Fees before tax", "fees_tax"), ("Working days", "working_days"),
    ("Reason order", "reason_order"), ("Pence or cents in amounts", "money_decimals"),
    ("Your line for the new-client price", "new_client_line"), ("Clients to ring first (at most)", "call_first_max"),
    ("Letters sent on", "send_date"),
]
CLIENT_COLS = [
    ("Client", "name"), ("Contact", "contact"), ("Fee before this wave", "fee"), ("Fee per", "per"),
    ("Billed every (months)", "billed_every"), ("Billing months", "billing_months"), ("Hours a month", "hours"),
    ("Since", "since"), ("Direct cost", "direct_cost"), ("Notice", "notice"), ("Notice runs to", "notice_align"),
    ("Renewal only", "renewal_only"), ("Term ends", "term_end"), ("Renewal date", "renewal_date"),
    ("Projects a year", "projects_per_year"), ("Flags", "_flags"), ("Scope line", "scope_line"),
    ("Your reason", "reason"), ("Included hours (Option B)", "included_hours"),
    ("Group", "_segment"), ("Step 1", "_step1"), ("Step 1 date", "_date1"), ("Step 2", "_step2"),
    ("Step 2 date", "_date2"), ("Outcome", "_outcome"), ("Agreed fee now", "_agreed"),
]
FLAG_KEYS = ["scope_crept", "scope_ok", "scope_confirmed", "priced_low", "relieved", "gentle", "hold"]
LEARN_HEAD = "| # | Learning | Evidence | Applies to step | Status | Added |"
HIST_HEAD = "| Date | Made | Wave and cap | Verdict |"
STATUSES = {"watch", "active", "retired"}
STEPS = {"intake", "diagnose", "make", "check", "deliver", "learn", "dates", "letters"}


def cell(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "yes" if v else ""
    if isinstance(v, (list, tuple)):
        return "; ".join(str(x) for x in v)
    if isinstance(v, dict):
        return "; ".join(f"{k}={x}" for k, x in v.items())
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


def get(d, dotted):
    cur = d
    for part in dotted.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def put(d, dotted, v):
    parts = dotted.split(".")
    for p in parts[:-1]:
        d = d.setdefault(p, {})
    d[parts[-1]] = v


def untext(key, v):
    if v == "":
        return None
    if key in ("call_first_top_quartile", "renewal_only"):
        return v.lower() in ("yes", "true", "1")
    if key == "billing_months":
        return [int(x) for x in re.findall(r"\d+", v)]
    if key == "reason_order":
        return [x.strip() for x in v.split(";") if x.strip()]
    if key == "rounding":
        return {k: float(x) for k, x in re.findall(r"(\w+)=([\d.]+)", v)}
    if key in ("billed_every", "billing_day", "second_step_months", "window_months", "money_decimals", "call_first_max"):
        try:
            return int(float(v))
        except ValueError:
            return v
    return v


def cmd_read(a):
    p = Path(a.memory)
    if not p.exists():
        print(f"STOP: there is no memory file at {a.memory}. Run as a first run.")
        return 2
    text = p.read_text(encoding="utf-8")
    _h, prof = table(text, "Profile")
    _h, cls = table(text, "Clients")
    if not prof:
        print("STOP: the memory file has no Profile table. Run as a first run and offer to save a fresh file.")
        return 2
    upd = re.search(r"Updated:\s*(\d{4}-\d{2}-\d{2})", text)
    when = upd.group(1) if upd else None
    data, sources = {}, {}
    lab2key = dict(PROFILE)
    for r in prof:
        k = lab2key.get(r.get("Field", ""))
        v = untext(k or "", r.get("Value", ""))
        if k and v is not None:
            put(data, k, v)
            sources[k] = f"saved memory ({r.get('Source') or 'you said'}, {r.get('Updated') or when})"
    clients = []
    for r in cls:
        c = {}
        for lab, k in CLIENT_COLS:
            v = r.get(lab, "")
            if k.startswith("_") or v == "":
                continue
            c[k] = untext(k, v)
        for f in FLAG_KEYS:
            if f.replace("_", " ") in r.get("Flags", "").lower():
                c[f] = True
        if not c.get("name"):
            continue
        outcome = r.get("Outcome", "").lower()
        if a.next_wave:
            if outcome.startswith("left"):
                continue
            if r.get("Agreed fee now"):
                c["fee"] = r["Agreed fee now"]
            for k in ("renewal_only", "term_end", "renewal_date"):
                c.pop(k, None)
        elif r.get("Step 1"):
            c["fixed_steps"] = {"step1": r["Step 1"], "date1": r.get("Step 1 date"),
                                "step2": r.get("Step 2") or None, "date2": r.get("Step 2 date") or None}
        clients.append(c)
    data["clients"] = clients
    data["sources"] = sources
    _h, learn = table(text, "Learnings")
    data["_learnings_active"] = [f"{r.get('Learning')} (step: {r.get('Applies to step')})" for r in learn
                                 if r.get("Status", "").lower() == "active"]
    data["_learnings_watch"] = [r.get("Learning") for r in learn if r.get("Status", "").lower() == "watch"]
    data["_memory_updated"] = when
    if a.next_wave:
        data.pop("send_date", None)
    out = json.dumps(data, indent=1, ensure_ascii=False)
    if a.json_out:
        Path(a.json_out).write_text(out, encoding="utf-8")
        print(f"WROTE: {a.json_out} ({len(clients)} clients, {len(data['_learnings_active'])} active learnings"
              f"{', next wave' if a.next_wave else ', saved plan kept as sent'})")
        if data["_learnings_active"]:
            print("ACTIVE: " + " / ".join(data["_learnings_active"]))
        if data["_learnings_watch"]:
            print("WATCH (apply only if it changes wording or format, never a figure, date or check): "
                  + " / ".join(x for x in data["_learnings_watch"] if x))
    else:
        print(out)
    return 0


def esc_rows(text, heading):
    _h, rows = table(text, heading) if text else (None, [])
    return rows


def cmd_write(a):
    inp = json.loads(Path(a.inputs).read_text(encoding="utf-8"))
    res = json.loads(Path(a.results).read_text(encoding="utf-8")) if a.results else {"clients": []}
    today = (res.get("today") or date.today().isoformat())
    old = Path(a.existing).read_text(encoding="utf-8") if a.existing and Path(a.existing).exists() else ""
    src = inp.get("sources", {})
    lines = ["# The Price Rise Pack memory", "",
             f"Skill: {SKILL} | Memory version: 1 | Updated: {today}", "",
             "Keep this file. Attach it next time (or leave it in your merigrove-memory folder, or your Claude "
             "Project) and the skill picks up where you left off: it asks one question and measures what happened "
             "against this plan. You can edit it by hand.", "", "## Profile", "",
             "| Field | Value | Source | Updated |", "|---|---|---|---|"]
    if res.get("send") and not inp.get("send_date"):
        inp["send_date"] = res["send"]
    for lab, k in PROFILE:
        v = get(inp, k)
        if v in (None, "", [], {}):
            continue
        if k == "send_date" and res.get("send"):
            v = res["send"]
        lines.append(f"| {lab} | {cell(v)} | {cell(src.get(k) or 'you said')} | {today} |")
    lines += ["", "## Clients", "", "| " + " | ".join(l for l, _ in CLIENT_COLS) + " |",
              "|" + "---|" * len(CLIENT_COLS)]
    by = {c["name"]: c for c in res.get("clients", [])}
    outs = {r["client"]: r for r in ((res.get("outcomes") or {}).get("rows") or [])}
    for i, c in enumerate(inp.get("clients", [])):
        rc = by.get(c.get("name"), {})
        name = c.get("name", "")
        if a.initials:
            name = "".join(w[0] for w in re.findall(r"[A-Za-z]+", name)).upper() or name
        row = []
        for lab, k in CLIENT_COLS:
            if k == "name":
                row.append(cell(name))
            elif k == "_flags":
                row.append("; ".join(f.replace("_", " ") for f in FLAG_KEYS if c.get(f)))
            elif k == "_segment":
                row.append(cell(rc.get("segment")))
            elif k == "_step1":
                row.append(cell(rc.get("step1")) if rc.get("segment") not in (None, "Hold") else "")
            elif k == "_date1":
                row.append(cell(rc.get("eff1")) if rc.get("segment") not in (None, "Hold") else "")
            elif k == "_step2":
                row.append(cell(rc.get("step2")))
            elif k == "_date2":
                row.append(cell(rc.get("eff2")))
            elif k == "_outcome":
                o = outs.get(c.get("name"))
                row.append(cell(o["result"] + (f" ({o['said']})" if o.get("said") else "")) if o else "")
            elif k == "_agreed":
                o = outs.get(c.get("name"))
                row.append(cell(o.get("agreed_fee")) if o and o["result"] != "left" else "")
            elif k == "fee":
                row.append(cell(c.get("fee")))
            else:
                row.append(cell(c.get(k)))
        lines.append("| " + " | ".join(row) + " |")
    lines += ["", "## Learnings", "", LEARN_HEAD, "|---|---|---|---|---|---|"]
    learn = esc_rows(old, "Learnings")
    n = 0
    for r in learn:
        for words, status in [(w, "retired") for w in (a.retire or [])] + [(w, "active") for w in (a.activate or [])]:
            if words.lower() in str(r.get("Learning", "")).lower():
                r["Status"] = status
        n += 1
        lines.append(f"| {n} | {r.get('Learning', '')} | {r.get('Evidence', '')} | {r.get('Applies to step', '')} | "
                     f"{r.get('Status', '')} | {r.get('Added', '')} |")
    for l in a.learning or []:
        parts = [x.strip() for x in l.split("|")]
        if len(parts) != 4:
            print(f"STOP: a learning needs four parts, rule | evidence | step | status: '{l}'")
            return 2
        n += 1
        lines.append(f"| {n} | {cell(parts[0])} | {cell(parts[1])} | {cell(parts[2])} | {parts[3].lower()} | {today} |")
    lines += ["", "## History", "", HIST_HEAD, "|---|---|---|---|"]
    for r in esc_rows(old, "History"):
        lines.append(f"| {r.get('Date', '')} | {r.get('Made', '')} | {r.get('Wave and cap', '')} | {r.get('Verdict', '')} |")
    if a.history:
        parts = [x.strip() for x in a.history.split("|")] + ["", "", ""]
        lines.append(f"| {today} | {cell(parts[0])} | {cell(parts[1])} | {cell(parts[2])} |")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"WROTE: {a.out}")
    return validate(a.out)


def validate(path):
    p = Path(path)
    if not p.exists():
        print(f"STOP: there is no memory file at {path}.")
        return 2
    text = p.read_text(encoding="utf-8")
    problems = []
    for h in ("Profile", "Clients", "Learnings", "History"):
        if not re.search(rf"^## {h}\s*$", text, re.M):
            problems.append(f"no '## {h}' section")
    _h, prof = table(text, "Profile")
    labels = {l for l, _ in PROFILE}
    for r in prof:
        if r.get("Field") and r["Field"] not in labels:
            problems.append(f"Profile field '{r['Field']}' is not one this skill reads")
    head, cls = table(text, "Clients")
    for r in cls:
        if not r.get("Client") or not r.get("Fee before this wave"):
            problems.append("a client row has no name or no fee")
    _h, learn = table(text, "Learnings")
    active = 0
    for r in learn:
        s = r.get("Status", "").lower()
        if s not in STATUSES:
            problems.append(f"learning '{r.get('Learning', '')[:40]}' has status '{s}' (use watch, active or retired)")
        if s == "active":
            active += 1
        if r.get("Applies to step", "").lower() not in STEPS:
            problems.append(f"learning '{r.get('Learning', '')[:40]}' names step '{r.get('Applies to step')}'")
    if active > 25:
        problems.append(f"{active} active learnings, limit 25: condense before adding")
    if re.search(r"[\u2014\u2013]", text):
        problems.append("contains an em or en dash")
    for x in problems:
        print("PROBLEM:", x)
    print(f"{len(problems)} problems")
    return 1 if problems else 0


def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = a.add_subparsers(dest="cmd")
    r = sub.add_parser("read")
    r.add_argument("memory")
    r.add_argument("--json-out")
    r.add_argument("--next-wave", action="store_true")
    w = sub.add_parser("write")
    w.add_argument("inputs")
    w.add_argument("--results")
    w.add_argument("--out", required=True)
    w.add_argument("--existing")
    w.add_argument("--history")
    w.add_argument("--learning", action="append")
    w.add_argument("--retire", action="append")
    w.add_argument("--activate", action="append")
    w.add_argument("--initials", action="store_true")
    v = sub.add_parser("validate")
    v.add_argument("memory")
    args = a.parse_args()
    try:
        if args.cmd == "read":
            return cmd_read(args)
        if args.cmd == "write":
            return cmd_write(args)
        if args.cmd == "validate":
            return validate(args.memory)
    except (json.JSONDecodeError, OSError, KeyError, ValueError) as e:
        print(f"STOP: could not read a file ({type(e).__name__}: {e}). Check the paths and run again.")
        return 2
    a.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
