#!/usr/bin/env python3
"""Read, write and check the Funnel Constraint Finder memory file.

Usage:
  python3 scripts/memory.py read <memory.md> --json-out <previous.json> [--inputs-out <inputs.json>]
        turn a saved memory file into the previous-run file (for 'funnel.py build --previous') and a draft
        inputs file with every saved fact filled and every count left empty for this run
  python3 scripts/memory.py write <results.json> --out <memory.md> [--existing <old memory.md>]
        [--history "made | verdict"] [--learning "rule | evidence | step | status"]
        write the memory file; keeps the old Learnings and History, appends the new rows, and keeps the
        founder's best two months so far per stage
  python3 scripts/memory.py validate <memory.md>
        check the file still has the shape this skill reads

The memory file is plain markdown the founder can read and edit by hand. Write only after the founder has
approved what is saved. Standard library only. No network calls.
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

SKILL = "revos-funnel-constraint-finder"
PROFILE = [  # label, results/inputs key
    ("Business", "business"), ("Country", "country"), ("English", "locale"), ("Currency", "currency"),
    ("Paper", "paper"), ("Working week", "working_week"), ("Funnel model", "model"),
    ("Route these counts cover", "route"), ("Routes mixed in the counts", "routes_mixed"),
    ("Where the last clients came from", "last_ten"), ("Reach measured from", "reach_source"),
    ("Capture: what a stranger can take", "capture"), ("Follow-up after an enquiry", "nurture"),
    ("Sales meeting", "meeting"), ("Has a sales meeting", "has_meeting"), ("Average sale", "average_sale"),
    ("Sale basis", "sale_basis"), ("Most clients at once", "capacity_max"), ("Active clients", "active_clients"),
    ("New clients you can start a month", "onboard_max"),
    ("What keeps clients", "retain"), ("Count definitions", "definitions"), ("Stage names", "stage_names"),
    ("Spelling", "spelling"), ("Decimal style", "decimal_style"), ("Count filters for exports", "count_filters"),
    ("Count view", "count_view"),
]
RUN_FIELDS = [("Date", "date"), ("People who saw you a month", "reach_month"), ("Enquiries in 60 days", "leads"),
              ("Booked in 60 days", "booked"), ("Held in 60 days", "held"), ("New clients in 60 days", "clients"),
              ("Constraint", "constraint"),
              ("Constraint stage", "constraint_key"), ("Worth, clients a month", "prize_month"),
              ("Worth, money a month", "prize_money"), ("Verdict", "verdict"), ("Counts given over", "counts_period")]
RATE_KEYS = [("capture", "Enquiry rate"), ("booking", "Booking rate"), ("show", "Show rate"), ("close", "Close rate")]
LEARN_HEAD = "| # | Learning | Evidence | Applies to step | Status | Added |"
HIST_HEAD = "| Date | Made | Verdict |"
STATUSES = {"watch", "active", "retired"}
STEPS = {"intake", "diagnose", "make", "check", "deliver", "learn"}


class Stop(Exception):
    pass


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


def pct_to_float(s):
    m = re.match(r"^\s*(\d+(?:\.\d+)?)\s*%?\s*$", str(s or ""))
    if not m:
        return None
    x = float(m.group(1))
    return x / 100.0 if (str(s).strip().endswith("%") or x > 1) else x


def unify(text):
    """Labels are read in one spelling; an American file ('Inquiries') reads the same as a British one."""
    return re.sub(r"\b([Ii])nquir", lambda m: ("E" if m.group(1) == "I" else "e") + "nquir", text)


def cmd_read(a):
    text = unify(Path(a.memory).read_text(encoding="utf-8"))
    probs = validate(text)
    if probs:
        raise Stop("the memory file does not have the shape this skill reads (" + "; ".join(probs[:3]) +
                   "). Run as a first run, or fix the file by hand")
    _h, prof = table(text, "Profile")
    _h, run = table(text, "Last run")
    _h, best = table(text, "Best so far")
    _h, learn = table(text, "Learnings")
    upd = re.search(r"Updated:\s*(\d{4}-\d{2}-\d{2})", text)
    when = upd.group(1) if upd else None
    lab = dict(PROFILE)
    profile, sources = {}, {}
    for r in prof:
        k = lab.get(r.get("Field", ""))
        if k and r.get("Value", "") != "":
            profile[k] = r["Value"]
            sources[k] = f"saved memory: {r.get('Source', '') or 'founder said'}, {r.get('Updated', '') or when}"
    runl = dict(RUN_FIELDS)
    runl.update({"Enquiries": "leads", "Booked": "booked", "Held": "held", "New clients": "clients"})  # before 1.3
    last = {}
    for r in run:
        k = runl.get(r.get("Field", ""))
        if k:
            last[k] = r.get("Value", "")
    rates = {}
    for key, label in RATE_KEYS:
        row = next((r for r in run if r.get("Field") == label), None)
        if row:
            rates[key] = pct_to_float(row.get("Value"))
    best_rates = {}
    best_from = {}
    for r in best:
        key = next((k for k, lb in RATE_KEYS if lb == r.get("Stage")), None)
        x = pct_to_float(r.get("Rate"))
        if key and x is not None:
            best_rates[key] = x
            best_from[key] = r.get("From", "")

    def num(v):
        try:
            return float(str(v).replace(",", ""))
        except (TypeError, ValueError):
            return None
    prev = {"date": last.get("date") or when, "constraint": last.get("constraint") or None,
            "constraint_key": last.get("constraint_key") or None, "verdict": last.get("verdict") or None,
            "counts": {k: num(last.get(k)) for k in ("leads", "booked", "held", "clients")},
            "counts_period": last.get("counts_period") or None,
            "rates": rates, "best_rates": best_rates, "best_from": best_from,
            "learnings_active": [r.get("Learning") for r in learn if r.get("Status", "").strip().lower() == "active"],
            "learnings_watch": [r.get("Learning") for r in learn if r.get("Status", "").strip().lower() == "watch"],
            "memory_updated": when}
    Path(a.json_out).write_text(json.dumps(prev, indent=2), encoding="utf-8")
    print(f"WROTE: {a.json_out} (last run {prev['date']}, constraint then: {prev['constraint'] or 'not named'}, "
          f"{len(prev['learnings_active'])} active learnings)")
    if a.inputs_out:
        inp = {k: profile.get(k) for _l, k in PROFILE}
        for k in ("definitions", "count_filters"):
            if inp.get(k):
                inp[k] = [x.strip() for x in str(inp[k]).split(";") if x.strip()]
        if inp.get("stage_names"):
            sn = {}
            for part in str(inp["stage_names"]).split(";"):
                if "=" in part:
                    kk, vv = part.split("=", 1)
                    sn[kk.strip()] = vv.strip()
            inp["stage_names"] = sn
        inp.update({"date": None, "counts_period": "last 60 days", "leads": None, "booked": None, "held": None,
                    "clients": None, "reach": None, "normal_period": None, "actions": [], "sources": sources})
        if best_rates:
            inp["best"] = {"label": "your best so far",
                           "rates": {k: f"{round(v * 100, 2):g}%" for k, v in best_rates.items()}}
        Path(a.inputs_out).write_text(json.dumps(inp, indent=2), encoding="utf-8")
        print(f"WROTE: {a.inputs_out} (saved facts filled; counts for this run left empty)")
    if profile.get("count_filters"):
        print("COUNT FILTERS: pass each to 'funnel.py count' as --where: " + profile["count_filters"])
    if profile.get("count_view"):
        print("COUNT VIEW: " + profile["count_view"] + " (set in the inputs file)")
    for x in prev["learnings_active"]:
        print("ACTIVE LEARNING:", x)
    for x in prev["learnings_watch"]:
        print("WATCH (not applied):", x)


def fmtv(v):
    if v is None or v == "":
        return ""
    if isinstance(v, float):
        return f"{v:g}" if abs(v) < 1e6 else f"{v:.0f}"
    return str(v)


def cmd_write(a):
    res = json.loads(Path(a.results).read_text(encoding="utf-8"))
    if res.get("skill") != SKILL or "profile" not in res:
        raise Stop("that is not a results file from funnel.py build (look for <name>-results.json beside the "
                   "inputs file)")
    today = str(res.get("date") or date.today().isoformat())
    old_text = Path(a.existing).read_text(encoding="utf-8") if a.existing and Path(a.existing).exists() else ""
    old_text = unify(old_text)
    _h, old_prof = table(old_text, "Profile") if old_text else (None, [])
    _h, old_best = table(old_text, "Best so far") if old_text else (None, [])
    _h, learn_rows = table(old_text, "Learnings") if old_text else (None, [])
    _h, hist_rows = table(old_text, "History") if old_text else (None, [])
    old_by = {r.get("Field"): r for r in old_prof}
    L = ["# Funnel Constraint Finder memory", "",
         f"Skill: {SKILL} | Memory version: 1 | Updated: {today}", "",
         "Keep this file. Attach it next time (or leave it in your merigrove-memory folder, or your Claude Project) "
         "and the next run asks only for your new numbers. You can edit it by hand.", "",
         "## Profile", "", "| Field | Value | Source | Updated |", "|---|---|---|---|"]
    prof = res["profile"]
    for label, k in PROFILE:
        v = prof.get(k)
        if v in (None, "", NKS):
            continue
        v = fmtv(v)
        o = old_by.get(label)
        if o and o.get("Value", "") == cell(v):
            L.append(f"| {label} | {cell(v)} | {o.get('Source', '') or 'founder said'} | {o.get('Updated', '') or today} |")
        else:
            L.append(f"| {label} | {cell(v)} | founder said | {today} |")
    c = res.get("counts") or {}
    L += ["", "## Last run", "", "| Field | Value |", "|---|---|"]
    vals = {"date": today, "reach_month": None if c.get("reach") is None else round(c["reach"] / 2, 1),
            "leads": c.get("leads"), "booked": c.get("booked"), "held": c.get("held"), "clients": c.get("clients"),
            "constraint": res.get("constraint"), "constraint_key": res.get("constraint_key"),
            "prize_month": res.get("prize_month"), "prize_money": res.get("prize_money"), "verdict": res.get("verdict"),
            "counts_period": res.get("counts_period")}
    for label, k in RUN_FIELDS:
        L.append(f"| {label} | {cell(fmtv(vals.get(k)))} |")
    for key, label in RATE_KEYS:
        r = (res.get("rates") or {}).get(key)
        if r is not None:
            L.append(f"| {label} | {round(r * 100, 2):g}% |")
    # best so far (v1.2): a rate becomes "best" only when it beats an earlier saved run (the saved best, else the
    # last run's rate) by more than one event's swing, on ten or more events as the founder counted them. A first
    # save holds no best: one period is a baseline, not a target.
    best = {}
    for r in old_best:
        key = next((k for k, lb in RATE_KEYS if lb == r.get("Stage")), None)
        x = pct_to_float(r.get("Rate"))
        if key and x is not None:
            best[key] = (x, r.get("From", ""))
    _h, old_run = table(old_text, "Last run") if old_text else (None, [])
    old_rates = {k: pct_to_float(next((r.get("Value") for r in old_run if r.get("Field") == lb), None))
                 for k, lb in RATE_KEYS}
    old_date = next((r.get("Value") for r in old_run if r.get("Field") == "Date"), "") or "your last run"
    dens = res.get("rates_den_given") or {}
    for key, x in (res.get("rates_firm") or {}).items():
        dg = dens.get(key)
        ref = best[key][0] if key in best else old_rates.get(key)
        if ref is None or not dg or dg < 10:
            continue
        if x - ref > 1.0 / dg + 1e-12:
            best[key] = (x, f"your counts, the 60 days to {today} (beat {round(ref * 100, 2):g}% from {old_date} by "
                            f"more than one event)")
    L += ["", "## Best so far", "", "Your own best rate per stage: saved only when a run beats an earlier one by more "
          "than one event, on ten or more events. The next run uses it as the target where it beats today by more "
          "than one event.", "", "| Stage | Rate | From |", "|---|---|---|"]
    for key, label in RATE_KEYS:
        if key in best:
            L.append(f"| {label} | {round(best[key][0] * 100, 2):g}% | {cell(best[key][1])} |")
    L += ["", "## Learnings", "", LEARN_HEAD, "|---|---|---|---|---|---|"]
    n = 0
    for r in learn_rows:
        n += 1
        L.append(f"| {n} | {r.get('Learning', '')} | {r.get('Evidence', '')} | {r.get('Applies to step', '')} | "
                 f"{r.get('Status', '')} | {r.get('Added', '')} |")
    for x in a.learning or []:
        parts = [p.strip() for p in x.split("|")] + ["", "", "", ""]
        if not parts[0]:
            continue
        n += 1
        L.append(f"| {n} | {cell(parts[0])} | {cell(parts[1])} | {cell(parts[2] or 'Make')} | "
                 f"{cell(parts[3] or 'watch')} | {today} |")
    L += ["", "Status: watch (seen once), active (approved or repeated), retired (kept for the record, no longer "
          "applied).", "", "## History", "", HIST_HEAD, "|---|---|---|"]
    for r in hist_rows:
        L.append(f"| {r.get('Date', '')} | {r.get('Made', '')} | {r.get('Verdict', '')} |")
    if a.history:
        parts = [p.strip() for p in a.history.split("|")] + ["", ""]
        L.append(f"| {today} | {cell(parts[0])} | {cell(parts[1])} |")
    out_text = "\n".join(L) + "\n"
    if res.get("us"):  # the founder writes American English: their memory file does too
        out_text = re.sub(r"\b([Ee])nquir", lambda m: ("I" if m.group(1) == "E" else "i") + "nquir", out_text)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(out_text, encoding="utf-8")
    probs = validate(Path(a.out).read_text(encoding="utf-8"))
    for p in probs:
        print("PROBLEM:", p)
    print(f"WROTE: {a.out} ({n} learnings, {len(hist_rows) + (1 if a.history else 0)} history rows, "
          f"best so far on {len(best)} stages)")
    sys.exit(1 if probs else 0)


NKS = "not known"


def validate(text):
    text = unify(text)
    p = []
    if not re.search(rf"Skill:\s*{SKILL}", text):
        p.append(f"header line 'Skill: {SKILL}' missing")
    if not re.search(r"Updated:\s*\d{4}-\d{2}-\d{2}", text):
        p.append("header has no Updated: YYYY-MM-DD date")
    for h in ("Profile", "Last run", "Best so far", "Learnings", "History"):
        if not re.search(rf"^## {h}\s*$", text, re.M):
            p.append(f"section '## {h}' missing")
    _h, prof = table(text, "Profile")
    if not any(r.get("Field") == "Business" and r.get("Value") for r in prof):
        p.append("Profile has no Business row")
    _h, best = table(text, "Best so far")
    for r in best:
        x = pct_to_float(r.get("Rate"))
        if x is None or not 0 <= x <= 1:
            p.append(f"Best so far: '{r.get('Rate')}' for {r.get('Stage')} is not a rate between 0% and 100%")
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
    r.add_argument("--inputs-out")
    w = sub.add_parser("write")
    w.add_argument("results")
    w.add_argument("--out", required=True)
    w.add_argument("--existing")
    w.add_argument("--history")
    w.add_argument("--learning", action="append")
    v = sub.add_parser("validate")
    v.add_argument("memory")
    a = ap.parse_args()
    if a.cmd is None:
        ap.print_help()
        sys.exit(2)
    for attr in ("memory", "results"):
        path = getattr(a, attr, None)
        if path and not Path(path).exists():
            raise Stop(f"there is no file at {path}")
    {"read": cmd_read, "write": cmd_write, "validate": cmd_validate}[a.cmd](a)


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:  # output piped into a reader that stopped early: not an error
        import os
        os._exit(0)
    except Stop as e:
        print(f"STOP: {e}. Nothing was changed.")
        sys.exit(2)
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print(f"STOP: the memory file could not be handled ({type(e).__name__}: {e}). Nothing was changed.")
        sys.exit(2)
