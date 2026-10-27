#!/usr/bin/env python3
"""Read, write and check the Hiring Readiness Check memory file.

Usage:
  python3 scripts/memory.py read <memory.md> --json-out <inputs.json> [--previous-out <previous.json>]
        turn a saved memory file into an inputs file to edit, and a previous-results file for the comparison
  python3 scripts/memory.py write <results.json or, for a pack only, inputs.json> --out <memory.md> [--existing <old memory.md>]
        [--history "made | route chosen | verdict"] [--learning "rule | evidence | step | status"]
  python3 scripts/memory.py validate <memory.md>

The memory file is plain markdown the founder can read and edit. Write only after the founder approves.
Never saves a placeholder, a default the founder did not confirm, or pipeline deals (they go stale).
Exit codes: 0 clean, 1 problems found, 2 STOP. Standard library only. No network calls.
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

SKILL = "revos-hiring-readiness"
PROFILE = [  # label, key in inputs, kind. Defaults the founder never set are not saved.
    ("Business", "business", "text"), ("Currency", "currency", "text"), ("Currency mark", "currency_symbol", "text"),
    ("Country", "country", "text"),
    ("Locale (dates and spelling)", "locale", "text"), ("Number style", "decimal_style", "text"),
    ("Cash floor, months of costs", "cover_target_months", "num"),
    ("Bad quarter: money in lower by", "stress_revenue_cut", "pct"),
    ("Bad quarter: payment delay, days", "stress_extra_days", "num"),
    ("Bad quarter cut applies to all revenue", "stress_cut_all_revenue", "flag"),
    ("Gross margin floor", "margin_floor", "pct"),
    ("Gross margin, last two months (as of the last check)", "gross_margin_months", "pctlist"),
    ("Gross margin, rough range (as of the last check)", "gross_margin_rough", "rough"),
    ("Repeat revenue a month", "repeat_revenue_month", "num"),
    ("Share of revenue from returning clients", "repeat_share", "pct"),
    ("Payroll provider seen in your bank export", "payroll_provider_seen", "text"),
    ("Monthly costs include your own pay", "costs_include_founder_pay", "bool"),
    ("Your pay a month (if outside costs)", "founder_pay_month", "num"),
    ("Recurring revenue a month", "recurring_revenue_month", "num"),
    ("Contractor rate an hour", "contractor_rate_hour", "num"),
    ("Contractor line, hours a week", "contractor_line_hours", "num"),
    ("How full you are now", "capacity_now", "num"), ("Most you can take on", "capacity_max", "num"), ("Capacity measured in", "capacity_unit", "text"),
    ("Room for this many more", "capacity_room_for", "num"),
    ("A typical new client a month", "typical_client_month", "num"),
    ("Bad quarter: costs fall by this share of revenue lost", "variable_costs_share", "pct"),
]
ROLE = [("Title", "title"), ("Type", "type"), ("Employee or contractor", "employment"), ("Hours a week", "hours_week"),
        ("Salary a year", "salary_year"), ("Monthly cost", "monthly_cost"), ("Cost basis", "cost_basis"),
        ("Cost from", "cost_from"),
        ("One-off costs", "one_off"), ("Freed hours go to", "freed_hours_use"),
        ("Freed hours lead to revenue", "freed_use_has_revenue_path"), ("Tasks form one job", "role_coherent"),
        ("Why", "role_coherent_reason"), ("Price rise tested", "price_rise_tested"), ("Price rise tested (yes or no)", "price_rise_value"),
        ("Days", "days")]
TOP_ROLE = {"freed_hours_use", "freed_use_has_revenue_path", "role_coherent", "role_coherent_reason", "price_rise_tested",
            "price_rise_value"}
MARGIN_LABELS = ("Gross margin, last two months (as of the last check)", "Gross margin, last two months",
                 "Gross margin, rough range (as of the last check)")
LEARN_HEAD = "| # | Learning | Evidence | Applies to step | Status | Added |"
HIST_HEAD = "| Date | Made | Route chosen | Verdict |"
STATUSES = {"watch", "active", "retired"}
STEPS = {"intake", "diagnose", "make", "check", "deliver", "learn"}


class Stop(Exception):
    pass


def c(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, float):
        v = round(v, 2)
        if v.is_integer():
            v = int(v)
    return str(v).replace("|", "/").replace("\n", " ").strip()


def table(text, heading):
    m = re.search(rf"^## {re.escape(heading)}\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not m:
        return None, []
    lines = [ln.strip() for ln in m.group(1).splitlines() if ln.strip().startswith("|")]
    if len(lines) < 2:
        return (lines[0] if lines else None), []
    head = [x.strip() for x in lines[0].strip("|").split("|")]
    rows = []
    for ln in lines[2:]:
        cells = [x.strip() for x in ln.strip("|").split("|")]
        rows.append(dict(zip(head, cells + [""] * (len(head) - len(cells)))))
    return lines[0], rows


def write(a):
    rp = Path(a.results)
    if not rp.exists():
        raise Stop(f"there is no results file at {a.results}")
    res = json.loads(rp.read_text(encoding="utf-8"))
    if isinstance(res, dict) and "conditions" not in res and "role" in res:
        # pack only: an inputs file, no check run
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from cash_scenario import normalise
        b0 = normalise(res)
        res = {"inputs": b0, "role": b0["role"], "date": b0["date"], "conditions": [], "verdict": "not checked"}
    b = res.get("inputs")
    if not isinstance(b, dict):
        raise Stop("that is not a results file from conditions.py or an inputs file")
    today = res.get("date") or date.today().isoformat()
    defaults = set(b.get("defaults_used") or [])
    old = {}
    old_learn, old_hist = [], []
    if a.existing and Path(a.existing).exists():
        t = Path(a.existing).read_text(encoding="utf-8")
        _h, rows = table(t, "Profile")
        old = {r.get("Field"): r for r in rows}
        _h, old_learn = table(t, "Learnings")
        _h, old_hist = table(t, "History")
    src = b.get("sources") or {}
    vals = dict(b)
    if b.get("currency"):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from cash_scenario import set_style, symbol
        set_style(b.get("locale"), b.get("country"), b.get("decimal_style"), b.get("currency"), b.get("currency_symbol"),
                  b.get("bare_dollar", True))
        vals["currency_symbol"] = symbol(b["currency"]) or None
    vals["capacity_max"] = (b.get("capacity") or {}).get("max")
    vals["capacity_now"] = (b.get("capacity") or {}).get("now")
    vals["capacity_unit"] = (b.get("capacity") or {}).get("unit")
    vals["capacity_room_for"] = (b.get("capacity") or {}).get("room_for")
    L = ["# Hiring Readiness Check memory", "",
         f"Skill: {SKILL} | Memory version: 1 | Updated: {today}", "",
         "Keep this file. Attach it next time (or leave it in your merigrove-memory folder, or your Claude Project) and the "
         "check picks up where you left off. You can edit it by hand.", "", "## Profile", "",
         "| Field | Value | Source | Updated |", "|---|---|---|---|"]
    if b.get("repeat_from_share"):
        vals["repeat_revenue_month"] = None  # worked out from the share; the share is saved instead
    derived = {"decimal_style", "currency_symbol", "country"}
    for lab, key, kind in PROFILE:
        v = vals.get(key)
        if key in defaults or v is None or v == "":
            if lab in old and old[lab].get("Value"):
                r = old[lab]
                L.append(f"| {lab} | {r['Value']} | {r.get('Source', '')} | {r.get('Updated', '')} |")
            continue
        if kind in ("pctlist", "rough") and not v:
            continue
        if kind == "flag" and v is not True:
            continue
        if kind == "pct":
            shown = f"{round(v * 100, 2):g}%"
        elif kind == "pctlist":
            shown = ", ".join(f"{round(x * 100, 2):g}%" for x in v)
        elif kind == "rough":
            shown = str(v.get("said") or "")
        else:
            shown = c(v)
        o = old.get(lab)
        if o and o.get("Value") == shown:
            L.append(f"| {lab} | {shown} | {o.get('Source', '')} | {o.get('Updated', '')} |")
        else:
            L.append(f"| {lab} | {shown} | {c(src.get(key)) or ('read from what you wrote' if key in derived else 'founder said')} | {today} |")
    role = res.get("role") or {}
    L += ["", "## Role", "", "| Field | Value |", "|---|---|"]
    for lab, key in ROLE:
        if key == "role_coherent":
            v = (b.get("role_coherent") or {}).get("value")
        elif key == "role_coherent_reason":
            v = (b.get("role_coherent") or {}).get("reason")
        elif key == "price_rise_tested":
            v = (b.get("price_rise_tested") or {}).get("said")
        elif key == "price_rise_value":
            v = (b.get("price_rise_tested") or {}).get("value")
        elif key == "monthly_cost" and role.get("cost_from_salary"):
            v = None  # worked out from the salary; the salary is saved instead
        elif key in TOP_ROLE:
            v = b.get(key)
        else:
            v = role.get(key)
        if key == "title" and str(v).startswith("[NEED"):
            continue
        if v not in (None, "", 0.0) or key == "one_off" or v is False:
            L.append(f"| {lab} | {c(v)} |")
    L += ["", "## Tasks", "", "| Task | Hours a week | Written down |", "|---|---|---|"]
    for t in b.get("tasks") or []:
        L.append(f"| {c(t['task'])} | {c(t['hours_week'])} | {c(t['written_down'])} |")
    lows = b.get("low_periods") or []
    if lows:
        L += ["", "## Known low periods", "", "| What | From | To | Money in lower by | Costs lower by |", "|---|---|---|---|---|"]
        for lp in lows:
            L.append(f"| {c(lp['what'])} | {c(lp.get('from_said') or lp['from'])} | {c(lp.get('to_said') or lp['to'])} | {round(lp['revenue_cut'] * 100, 2):g}% | {round(lp['costs_cut'] * 100, 2):g}% |")
    hist = b.get("revenue_history") or []
    labs = b.get("revenue_months") or []
    if hist and labs and len(labs) == len(hist):
        L += ["", "## Revenue by month", "", "By month: " + ", ".join(f"{k} {c(round(x, 2))}" for k, x in list(zip(labs, hist))[-24:])]
    else:
        L += ["", "## Revenue by month", "", "Oldest first: " + ", ".join(c(round(x, 2)) for x in hist[-24:]) if hist else "Oldest first: none saved"]
    L += ["", "## Last check", "", f"Date: {today} | Verdict: {res.get('verdict')}", "",
          "| # | Condition | Result |", "|---|---|---|"]
    for cd in res.get("conditions") or []:
        L.append(f"| {cd['n']} | {cd['name']} | {cd['status']} |")
    sc = res.get("scenario") or {}
    if sc:
        L += ["", f"End of window: usual {c(round(sc['base_end']))}, bad quarter {c(round(sc['stress_end']))}, floor {c(round(sc['floor']))}"]
    figs = [(k, b.get(k)) for k in ("cash_today", "monthly_revenue", "costs_month_total")]
    if all(v is not None for _k, v in figs):
        L += ["", "Figures then: " + ", ".join(f"{k} {c(round(v, 2))}" for k, v in figs)
              + (f", role_cost {c(round(role['monthly_cost'], 2))}" if role.get("monthly_cost") is not None else "")]
    L += ["", "## Learnings", "", LEARN_HEAD, "|---|---|---|---|---|---|"]
    n = 0
    for r in old_learn:
        n += 1
        L.append(f"| {n} | {r.get('Learning', '')} | {r.get('Evidence', '')} | {r.get('Applies to step', '')} | {r.get('Status', '')} | {r.get('Added', '')} |")
    for ln in a.learning or []:
        parts = [x.strip() for x in ln.split("|")]
        if len(parts) != 4 or parts[3].lower() not in STATUSES or parts[2].lower() not in STEPS:
            raise Stop(f"a learning must be 'rule | evidence | step | status' with a step from {sorted(STEPS)} and a status from {sorted(STATUSES)}")
        n += 1
        L.append(f"| {n} | {c(parts[0])} | {c(parts[1])} | {parts[2].capitalize()} | {parts[3].lower()} | {today} |")
    if sum(1 for ln in L if ln.endswith(" active |") or "| active |" in ln) > 25:
        raise Stop("more than 25 active learnings; condense before adding")
    L += ["", "Status: watch (seen once), active (approved or repeated), retired (kept for the record, no longer applied).",
          "", "## History", "", HIST_HEAD, "|---|---|---|---|"]
    for r in old_hist:
        L.append(f"| {r.get('Date', '')} | {r.get('Made', '')} | {r.get('Route chosen', '')} | {r.get('Verdict', '')} |")
    if a.history:
        parts = [x.strip() for x in a.history.split("|")]
        parts += [""] * (3 - len(parts))
        L.append(f"| {today} | {c(parts[0])} | {c(parts[1])} | {c(parts[2])} |")
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"WROTE: {out}")
    return validate_text(out.read_text(encoding="utf-8"))


def read(a):
    p = Path(a.memory)
    if not p.exists():
        raise Stop(f"there is no memory file at {a.memory}")
    t = p.read_text(encoding="utf-8")
    probs = validate_text(t, quiet=True)
    if probs:
        raise Stop("the memory file has lost its shape (" + "; ".join(probs[:2]) + "); treat this as a first run")
    _h, prof = table(t, "Profile")
    pv = {r["Field"]: r["Value"] for r in prof}
    inp, sources = {}, {}
    saved_margin = None
    for lab, key, kind in PROFILE:
        v = pv.get(lab)
        if kind == "pctlist" and not v:
            v = pv.get("Gross margin, last two months")  # memory files from 1.1
        if not v:
            continue
        if kind in ("pctlist", "rough"):
            saved_margin = {"value": v, "kind": "months" if kind == "pctlist" else "rough"}
            continue  # a margin is reused only when the founder confirms it for this run
        if key in ("capacity_max", "capacity_unit", "capacity_now", "capacity_room_for"):
            inp.setdefault("capacity", {})[key.split("_", 1)[1]] = v
        elif kind == "pctlist":
            inp[key] = [x.strip() for x in v.split(",") if x.strip()]
        else:
            inp[key] = v
        src = next((r.get("Source") for r in prof if r["Field"] == lab), "")
        sources[key] = f"saved {src}".strip()
    _h, rrows = table(t, "Role")
    rv = {r["Field"]: r["Value"] for r in rrows}
    role = {}
    for lab, key in ROLE:
        if rv.get(lab) and key not in TOP_ROLE:
            role["one_off_costs" if key == "one_off" else key] = rv[lab]
    if rv.get("Full monthly cost") and not role.get("monthly_cost"):  # memory files from version 1.0
        role["monthly_cost"] = rv["Full monthly cost"]
    inp["role"] = role
    if rv.get("Freed hours go to"):
        inp["freed_hours_use"] = rv["Freed hours go to"]
    if rv.get("Freed hours lead to revenue"):
        inp["freed_use_has_revenue_path"] = rv["Freed hours lead to revenue"]
    if rv.get("Tasks form one job"):
        inp["role_coherent"] = {"value": rv["Tasks form one job"], "reason": rv.get("Why", "")}
    if rv.get("Price rise tested") or rv.get("Price rise tested (yes or no)"):
        inp["price_rise_tested"] = {"value": rv.get("Price rise tested (yes or no)", ""), "said": rv.get("Price rise tested", "")}
    if rv.get("Days"):
        role["days"] = rv["Days"]
    _h, lrows = table(t, "Known low periods")
    if lrows:
        inp["known_low_periods"] = [{"what": r["What"], "from": r["From"], "to": r["To"], "revenue_cut": r["Money in lower by"],
                                     "costs_cut": r["Costs lower by"]} for r in lrows]
    _h, trows = table(t, "Tasks")
    inp["tasks"] = [{"task": r["Task"], "hours_week": r["Hours a week"], "written_down": r["Written down"]} for r in trows]
    m = re.search(r"Oldest first: (.+)", t)
    mb = re.search(r"By month: (.+)", t)
    if mb:
        inp["revenue_history"] = {k: v for k, v in re.findall(r"(\d{4}-\d{2}) (-?[\d.]+)", mb.group(1))}
    elif m and m.group(1).strip() != "none saved":
        inp["revenue_history"] = [x.strip() for x in m.group(1).split(",") if x.strip()]
    inp["sources"] = sources
    upd = re.search(r"Updated:\s*(\d{4}-\d{2}-\d{2})", t)
    when = upd.group(1) if upd else None
    _h, lc = table(t, "Last check")
    vm = re.search(r"Verdict: ([A-Za-z ]+)", t)
    prev = {"date": when, "verdict": vm.group(1).strip() if vm else None,
            "conditions": [{"n": int(r["#"]), "name": r["Condition"], "status": r["Result"]} for r in lc if r.get("#", "").isdigit()],
            "inputs": {"role": {"monthly_cost": None}}}
    wk = re.search(r"End of window: usual (-?[\d.]+), bad quarter (-?[\d.]+), floor (-?[\d.]+)", t)
    if wk:
        prev["scenario"] = {"base_end": float(wk.group(1)), "stress_end": float(wk.group(2)), "floor": float(wk.group(3))}
    fm = re.search(r"Figures then: (.+)", t)
    if fm:
        for k, v in re.findall(r"(\w+) (-?[\d.]+)", fm.group(1)):
            if k == "role_cost":
                prev["inputs"]["role"]["monthly_cost"] = float(v)
            else:
                prev["inputs"][k] = float(v)
    _h, learn = table(t, "Learnings")
    active = [r for r in learn if r.get("Status", "").lower() == "active"]
    Path(a.json_out).write_text(json.dumps(inp, indent=1), encoding="utf-8")
    print(f"WROTE: {a.json_out}")
    if a.previous_out:
        Path(a.previous_out).write_text(json.dumps(prev, indent=1), encoding="utf-8")
        print(f"WROTE: {a.previous_out}")
    print(f"SAVED ON: {when} | role: {role.get('title', '[none]')} | last verdict: {prev['verdict']}")
    if saved_margin:
        prev["saved_margin"] = saved_margin
        Path(a.previous_out).write_text(json.dumps(prev, indent=1), encoding="utf-8") if a.previous_out else None
        print(f"SAVED MARGIN (from {when}; not put in the inputs): {saved_margin['value']}. Reuse a month only when the founder "
              "confirms it for this run; ask for this month's margin in the return question.")
    for r in active:
        print(f"ACTIVE LEARNING ({r.get('Applies to step')}): {r.get('Learning')}")
    return 0


def validate_text(t, quiet=False):
    probs = []
    if f"Skill: {SKILL}" not in t:
        probs.append("missing the 'Skill:' line")
    for h in ("Profile", "Role", "Tasks", "Learnings", "History"):
        if not re.search(rf"^## {h}\s*$", t, re.M):
            probs.append(f"missing the '## {h}' section")
    if LEARN_HEAD not in t:
        probs.append("the Learnings table header has changed")
    if HIST_HEAD not in t:
        probs.append("the History table header has changed")
    _h, learn = table(t, "Learnings")
    for r in learn:
        if r.get("Status", "").lower() not in STATUSES:
            probs.append(f"learning {r.get('#')}: status must be watch, active or retired")
    if re.search(r"\[NEED|\[not known\]", t):
        probs.append("a placeholder was saved as if it were a figure")
    if not quiet:
        for x in probs:
            print("PROBLEM:", x)
        print(f"{len(probs)} problems")
    return 1 if probs and not quiet else (probs if quiet else 0)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    r = sub.add_parser("read")
    r.add_argument("memory")
    r.add_argument("--json-out", required=True)
    r.add_argument("--previous-out")
    w = sub.add_parser("write")
    w.add_argument("results")
    w.add_argument("--out", required=True)
    w.add_argument("--existing")
    w.add_argument("--history")
    w.add_argument("--learning", action="append")
    v = sub.add_parser("validate")
    v.add_argument("memory")
    a = ap.parse_args()
    if a.cmd == "read":
        return read(a)
    if a.cmd == "write":
        return write(a)
    if a.cmd == "validate":
        p = Path(a.memory)
        if not p.exists():
            raise Stop(f"there is no memory file at {a.memory}")
        return validate_text(p.read_text(encoding="utf-8"))
    print(__doc__)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Stop as e:
        print(f"STOP: {e}. Nothing was written.")
        sys.exit(2)
    except Exception as e:  # noqa: BLE001
        print(f"STOP: the memory step failed ({type(e).__name__}: {e}). Nothing was written.")
        sys.exit(2)
