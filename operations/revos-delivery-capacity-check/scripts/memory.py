#!/usr/bin/env python3
"""Read, write and check the Delivery Capacity Check memory file.

Usage:
  python3 scripts/memory.py read <memory.md> --json-out <scratch>/inputs.json [--previous-out <scratch>/previous.json]
        turn a saved memory file back into an inputs file for capacity.py (and the last run's
        ceilings, for the "since your last check" lines)
  python3 scripts/memory.py write <results.json> --out <memory.md> [--existing <old memory.md>]
        [--history "made | handover chosen | verdict"] [--learning "rule | evidence | step | status"]
        write the memory file from a build's results file; keeps old Learnings, History and Ceiling history
  python3 scripts/memory.py validate <memory.md>
        check the file still has the shape this skill reads

Write only after the founder has approved what is saved. Plain markdown the founder can edit.
Exit 2 with a STOP line on any error. Standard library only. No network calls.
"""
import argparse
import json
import re
import sys
from pathlib import Path

SKILL = "revos-delivery-capacity-check"
PROFILE = [  # label, inputs key
    ("Business", "business"), ("Delivery hours a week, after selling and admin", "delivery_hours_week"),
    ("Working hours a week", "working_hours_week"), ("Selling, admin and marketing hours a week", "selling_admin_hours_week"),
    ("The week you want, working hours", "target_working_hours_week"),
    ("The week you want, delivery hours", "target_delivery_hours_week"),
    ("Delivery takes now, hours a week", "delivery_hours_now_week"), ("Working weeks a year", "working_weeks_year"),
    ("Helper planning line", "helper_planning_line"), ("Helper low line", "helper_low_line"),
    ("Steps to hand over per round", "handover_count"), ("Country", "country"), ("English", "english"),
    ("Number style", "number_style"),
    ("Weeks off a year", "weeks_off_year"), ("Working day, hours", "day_hours"),
    ("Working days a week", "working_days_week"), ("Paper", "paper"),
]
# Where a value came from when the founder's inputs file does not say: never "founder said" for something
# Claude read from how they write, or for a figure the script worked out.
DEFAULT_SOURCE = {"country": "from what you mentioned", "english": "read from how you write",
                  "number_style": "read from how you write numbers"}
OFFER_COLS = [("Offer", "name"), ("Billing", "billing"), ("Active clients", "active_clients"),
              ("Months a client stays or a project runs", "months_per_client"), ("Price, before any sales tax", "price")]
STEP_COLS = [("Offer", "offer"), ("Step", "step"), ("Hours each time", "hours"), ("How often", "how_often"),
             ("Who does it", "owner"), ("Flag", "flag"), ("Why", "reason"), ("Quality check", "gate"),
             ("Check hours after handover", "check_hours_after"), ("Moves to", "handover_to")]
HELPER_COLS = [("Helper", "name"), ("Kind", "kind"), ("Paid hours a week", "hours_week")]
CEIL_HEAD = "| Date | Offer | Active clients | Your hours per client a month | Ceiling | Ceiling after handover |"
LEARN_HEAD = "| # | Learning | Evidence | Applies to step | Status | Added |"
HIST_HEAD = "| Date | Made | Handover chosen | Verdict |"
STATUSES = {"watch", "active", "retired"}
STEPS = {"intake", "diagnose", "make", "check", "deliver", "learn", "flags", "hours"}


class Stop(Exception):
    pass


def cell(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    if isinstance(v, float):
        v = round(v, 2)
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


def cmd_read(a):
    text = Path(a.memory).read_text(encoding="utf-8")
    probs = validate(text)
    if probs:
        raise Stop("the memory file has lost its shape (" + "; ".join(probs[:3]) + "). Run as a first run, or fix the file")
    upd = re.search(r"Updated:\s*(\d{4}-\d{2}-\d{2})", text)
    when = upd.group(1) if upd else None
    data = {"sources": {}}
    lab2key = dict(PROFILE)
    _h, prof = table(text, "Profile")
    for r in prof:
        k = lab2key.get(r.get("Field", ""))
        if k == "delivery_hours_now_week":
            data["_delivery_now_last"] = r.get("Value", "")  # a snapshot of that run: asked again, not carried in
            continue
        if str(r.get("Source", "")).lower().startswith("worked out"):
            continue  # worked out from other saved figures, which are read instead
        if k == "english" and re.fullmatch(r"[a-z]{2}-[A-Z]{2}", r.get("Value", "")):
            k = "locale"  # a file saved before 1.2
        if k and r.get("Value", "") != "":
            data[k] = r["Value"]
            data["sources"][k] = f"saved memory: {r.get('Source', '') or 'founder said'}, {r.get('Updated', '') or when}"
    for sec, cols, key in (("Offers", OFFER_COLS, "offers"), ("Steps", STEP_COLS, "steps"), ("Helpers", HELPER_COLS, "helpers")):
        _h, rows = table(text, sec)
        items = []
        for r in rows:
            o = {}
            for lab, k in cols:
                v = r.get(lab, "")
                if v != "":
                    o[k] = v
            if o:
                items.append(o)
        data[key] = items
    _h, learn = table(text, "Learnings")
    data["_learnings_active"] = [f"{r.get('Learning')} (step: {r.get('Applies to step')})" for r in learn
                                 if r.get("Status", "").lower() == "active"]
    data["_learnings_watch"] = [r.get("Learning") for r in learn if r.get("Status", "").lower() == "watch"]
    data["_memory_updated"] = when
    data["date"] = None  # set today's date before running
    Path(a.json_out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.json_out).write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"WROTE: {a.json_out} ({len(data['offers'])} offers, {len(data['steps'])} steps, "
          f"{len(data['_learnings_active'])} active learnings, saved {when})")
    if data.get("_delivery_now_last"):
        print(f"ASK ON RETURN: on {when} the founder said delivery takes '{data['_delivery_now_last']}' a week; ask whether that is still right")
    for x in data["_learnings_active"]:
        print("APPLY:", x)
    for x in data["_learnings_watch"]:
        print("WATCH (do not apply):", x)
    if a.previous_out:
        _h, ch = table(text, "Ceiling history")
        last_date = max((r.get("Date", "") for r in ch), default="")
        prev = {"date": last_date or when, "result_offers": {}, "step_flags": {}}
        for r in ch:
            if r.get("Date") == last_date:
                prev["result_offers"][r.get("Offer")] = {
                    "active": _f(r.get("Active clients")), "FW": _f(r.get("Your hours per client a month")),
                    "ceiling_whole": _i(r.get("Ceiling")), "ceiling_after_whole": _i(r.get("Ceiling after handover"))}
        for s in data["steps"]:
            fl = str(s.get("flag", "")).strip().upper()
            if fl in ("F", "W", "T"):
                prev["step_flags"][f"{s.get('offer')}|{s.get('step')}"] = fl
        Path(a.previous_out).write_text(json.dumps(prev, indent=2), encoding="utf-8")
        print(f"WROTE: {a.previous_out} (ceilings from {prev['date']})")


def _f(v):
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _i(v):
    x = _f(v)
    return int(x) if x is not None else None


def cmd_write(a):
    res = json.loads(Path(a.results).read_text(encoding="utf-8"))
    if res.get("skill") != SKILL or "inputs" not in res:
        raise Stop("that is not a results file from capacity.py build. Use the file passed to --results")
    inp = res["inputs"]
    biz = res["business"]
    today = res.get("date")
    src = inp.get("sources") or {}
    learn_rows, hist_rows, ceil_rows = [], [], []
    if a.existing and Path(a.existing).exists():
        old = Path(a.existing).read_text(encoding="utf-8")
        _h, learn_rows = table(old, "Learnings")
        _h, hist_rows = table(old, "History")
        _h, ceil_rows = table(old, "Ceiling history")
    L = ["# Delivery Capacity Check memory", "",
         f"Skill: {SKILL} | Memory version: 2 | Updated: {today}", "",
         "Keep this file. Attach it next time (or leave it in your merigrove-memory folder, or your Claude Project) "
         "and the check picks up where you left off. You can edit it by hand.", "",
         "## Profile", "", "| Field | Value | Source | Updated |", "|---|---|---|---|"]
    vals = {"business": biz.get("business")}
    for k in ("delivery_hours_week", "working_hours_week", "selling_admin_hours_week", "target_working_hours_week",
              "target_delivery_hours_week", "delivery_hours_now_week", "working_weeks_year", "helper_planning_line",
              "helper_low_line", "handover_count", "weeks_off_year", "day_hours", "working_days_week", "paper"):
        vals[k] = inp.get(k)  # as the founder gave them
    derived = {}
    if biz.get("delivery_hours_src") == "default":
        vals["delivery_hours_week"] = None  # never remember a default as if the founder had said it
    elif inp.get("delivery_hours_week") in (None, "") and str(biz.get("delivery_hours_src", "")).startswith("worked out"):
        vals["delivery_hours_week"] = cell(round(float(biz.get("today_delivery_hours_week") or biz.get("delivery_hours_week")), 2))
        derived["delivery_hours_week"] = str(biz.get("delivery_hours_src"))
    if biz.get("country"):
        vals["country"] = biz["country"]
    eng = inp.get("english") or (inp.get("locale") if inp.get("locale") else None)
    if eng:
        vals["english"] = "American" if str(eng).strip().lower() in ("en-us", "us", "american", "american english") else eng
    if inp.get("number_style") or biz.get("number_style"):
        vals["number_style"] = inp.get("number_style") or biz.get("number_style")
    for lab, k in PROFILE:
        v = vals.get(k)
        if v in (None, ""):
            continue
        s = derived.get(k) or src.get(k) or (src.get("locale") if k in ("english", "country") and src.get("locale") else None) \
            or DEFAULT_SOURCE.get(k, "founder said")
        if k == "country" and inp.get("country") and str(inp.get("country")).strip().upper() != str(v).upper() \
                and str(inp.get("country")).strip().lower() not in str(s).lower():
            s = f"{s} ({inp.get('country')})"
        when = today
        m = re.match(r"^saved memory: (.*), (\d{4}-\d{2}-\d{2})$", str(s))
        if m:
            s, when = m.group(1), m.group(2)
        L.append(f"| {lab} | {cell(v)} | {cell(s)} | {when} |")
    for sec, cols, key in (("Offers", OFFER_COLS, "offers"), ("Steps", STEP_COLS, "steps"), ("Helpers", HELPER_COLS, "helpers")):
        L += ["", f"## {sec}", "", "| " + " | ".join(c for c, _k in cols) + " |", "|" + "---|" * len(cols)]
        for o in inp.get(key) or []:
            if not isinstance(o, dict) or not any(o.get(k) not in (None, "") for _c, k in cols):
                continue
            row = dict(o)
            if key == "steps" and isinstance(row.get("flag"), str):
                row["flag"] = row["flag"].strip().upper()
            L.append("| " + " | ".join(cell(row.get(k)) for _c, k in cols) + " |")
    L += ["", "## Ceiling history", "", CEIL_HEAD, "|---|---|---|---|---|---|"]
    for r in ceil_rows:
        if r.get("Date") == today:
            continue
        L.append("| " + " | ".join(r.get(c.strip(), "") for c in CEIL_HEAD.strip("|").split("|")) + " |")
    for r in res.get("offers", []):
        L.append(f"| {today} | {cell(r['name'])} | {cell(r.get('active'))} | {cell(round(r['FW'], 2))} | "
                 f"{cell(r.get('ceiling_whole')) or 'no limit'} | {cell(r.get('ceiling_after_whole')) or 'no limit'} |")
    L += ["", "## Learnings", "", LEARN_HEAD, "|---|---|---|---|---|---|"]
    n = 0
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
    for r in hist_rows:
        L.append(f"| {r.get('Date', '')} | {r.get('Made', '')} | {r.get('Handover chosen', '')} | {r.get('Verdict', '')} |")
    if a.history:
        parts = [p.strip() for p in a.history.split("|")] + ["", "", ""]
        L.append(f"| {today} | {cell(parts[0])} | {cell(parts[1])} | {cell(parts[2])} |")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text("\n".join(L) + "\n", encoding="utf-8")
    probs = validate(Path(a.out).read_text(encoding="utf-8"))
    for p in probs:
        print("PROBLEM:", p)
    print(f"WROTE: {a.out} ({len(inp.get('offers') or [])} offers, {len(inp.get('steps') or [])} steps, {n} learnings)")
    return 1 if probs else 0


def validate(text):
    p = []
    if not re.search(rf"Skill:\s*{SKILL}", text):
        p.append(f"header line 'Skill: {SKILL}' missing")
    if not re.search(r"Updated:\s*\d{4}-\d{2}-\d{2}", text):
        p.append("header has no Updated: YYYY-MM-DD date")
    for h in ("Profile", "Offers", "Steps", "Ceiling history", "Learnings", "History"):
        if not re.search(rf"^## {h}\s*$", text, re.M):
            p.append(f"section '## {h}' missing")
    _h, offs = table(text, "Offers")
    if not offs:
        p.append("Offers table is empty")
    names = {r.get("Offer", "").lower() for r in offs}
    _h, steps = table(text, "Steps")
    if not steps:
        p.append("Steps table is empty")
    for r in steps:
        if not r.get("Step"):
            p.append(f"step row without a name: {r}")
        if r.get("Offer", "").lower() not in names and r.get("Offer", "").lower() not in (
                "all", "", "business", "business-wide", "business wide", "whole business", "overhead"):
            p.append(f"step '{r.get('Step')}' names an offer not in the Offers table: {r.get('Offer')}")
        if r.get("Flag", "").strip() and r.get("Flag", "").strip().upper() not in ("F", "W", "T"):
            p.append(f"step '{r.get('Step')}': flag '{r.get('Flag')}' is not F, W or T")
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
    h, _x = table(text, "History")
    if h and h != HIST_HEAD:
        p.append("History header changed; expected: " + HIST_HEAD)
    h, _x = table(text, "Ceiling history")
    if h and h != CEIL_HEAD:
        p.append("Ceiling history header changed; expected: " + CEIL_HEAD)
    return p


def cmd_validate(a):
    probs = validate(Path(a.memory).read_text(encoding="utf-8"))
    for x in probs:
        print("PROBLEM:", x)
    print(f"{len(probs)} problems")
    return 1 if probs else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
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
    if a.cmd is None:
        ap.print_help()
        return 2
    for attr in ("memory", "results"):
        if getattr(a, attr, None) and not Path(getattr(a, attr)).exists():
            raise Stop(f"there is no file at {getattr(a, attr)}")
    return {"read": cmd_read, "write": cmd_write, "validate": cmd_validate}[a.cmd](a) or 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Stop as e:
        print(f"STOP: {e}. Nothing was changed.")
        sys.exit(2)
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print(f"STOP: the memory file could not be handled ({type(e).__name__}: {e}). Nothing was changed.")
        sys.exit(2)
