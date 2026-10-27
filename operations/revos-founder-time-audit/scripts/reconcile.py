#!/usr/bin/env python3
"""Founder Time Audit: check that the hours reconcile and the rules held, before anything is shown.

Usage:
  python3 scripts/reconcile.py <results.json> [--events <events.json>] [--summary <summary.md>]

Checks:
  1. The calendar: counted event hours equal the calendar total the audit used.
  2. The week: activity rows plus "not placed" equal the week; categories and functions each add up to it.
  3. Every row has one category and one action, and the pair is allowed.
  4. Deletions come first; deletions and handovers are each ranked by hours a month, largest first, unless the
     founder chose the handover order (founder_order), which is then checked against the same set of handovers.
  5. The value line equals the hours times the rate shown.
  6. Every only-you row that reads as admin, reporting or scheduling carries the founder's answer.
  7. A recall-only audit is marked low confidence, and the summary says so.
  8. The summary: every figure in it is one the audit computed, and the headline parts add to the total.
  9. Plausibility: the hourly value is at least 1 unit of currency and not below the dearest helper's cost an hour,
     and the week is 10 to 100 hours, unless the founder confirmed the figure (rank.py stops first; this is the net).
Prints PROBLEM lines and a count. Exit 0 clean, 1 problems found, 2 could not run. Standard library only.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import report  # noqa: E402
from report import NUM_TOKEN, allowed_figures, canon, h1  # noqa: E402

WPM = 52 / 12
TOL = 0.02


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("results")
    ap.add_argument("--events")
    ap.add_argument("--summary")
    a = ap.parse_args()
    try:
        res = json.loads(Path(a.results).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"STOP: could not read {a.results} ({e}). Run rank.py first.")
        sys.exit(2)
    P = []
    report.set_style(res)
    wk = res["week"]["hours"]
    rows = res["rows"]
    # 1 calendar
    if a.events:
        try:
            ev = json.loads(Path(a.events).read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"STOP: could not read {a.events} ({e}).")
            sys.exit(2)
        counted = sum(e["counted_hours"] for e in ev["events"])
        if abs(counted - ev["calendar_hours"]) > TOL:
            P.append(f"events add to {h1(counted)} hours but the calendar total is {h1(ev['calendar_hours'])}")
        if abs(ev["calendar_hours"] - (res["week"].get("calendar_hours") or 0)) > TOL:
            P.append(f"the audit used {res['week'].get('calendar_hours')} calendar hours; the calendar holds {ev['calendar_hours']}")
    # 2 week
    placed = sum(x["weekly_hours"] for x in rows)
    if abs(placed + res["week"]["not_placed"] - wk) > TOL and placed < wk:
        P.append(f"rows {h1(placed)} plus not placed {h1(res['week']['not_placed'])} do not equal the {h1(wk)}-hour week")
    if placed > wk + 1.0 + TOL:
        P.append(f"rows add to {h1(placed)} hours, more than the {h1(wk)}-hour week")
    cs = sum(res["categories"][k]["week"] for k in ("1", "2", "3", "not_placed"))
    if abs(cs - max(wk, placed)) > TOL:
        P.append(f"categories add to {h1(cs)}, not {h1(wk)}")
    fs = sum(res["functions"][k]["week"] for k in ("strategy", "selling", "managing", "delivery", "admin")) + res["week"]["not_placed"]
    if abs(fs - max(wk, placed)) > TOL:
        P.append(f"functions add to {h1(fs)}, not {h1(wk)}")
    for x in rows:
        if abs(x["hours_each"] * x["per_month"] - x["monthly_hours"]) > 1e-6 or abs(x["monthly_hours"] / WPM - x["weekly_hours"]) > 1e-6:
            P.append(f"'{x['activity']}': hours a month is not hours each times times a month")
    # 3 categories and actions
    ok = {1: {"keep"}, 2: {"delegate", "automate", "keep"}, 3: {"delete"}}
    for x in rows:
        if x["category"] not in ok:
            P.append(f"'{x['activity']}' has no category")
        elif x["action"] not in ok[x["category"]]:
            P.append(f"'{x['activity']}': category {x['category']} with action {x['action']}")
        if x["category"] == 2 and x["action"] == "keep" and not x["reason"]:
            P.append(f"'{x['activity']}' is kept without a reason")
    # 4 order
    by = {x["activity"]: x for x in rows}
    for name, lst in (("deletions", res["deletions"]), ("handovers", res["handovers"])):
        if name == "handovers" and (res.get("order") or {}).get("source") == "founder":
            if sorted(lst) != sorted((res.get("order") or {}).get("by_hours") or []):
                P.append("handovers in the founder's order do not match the handovers ranked by hours")
            continue  # the founder chose the order; the report shows the hours and the hours-only order
        hs = [by[n]["monthly_hours"] for n in lst]
        if hs != sorted(hs, reverse=True):
            P.append(f"{name} are not ranked by hours a month")
    if set(res["deletions"]) & set(res["handovers"]):
        P.append("an activity is both a deletion and a handover")
    # 5 value
    rc, rate = res["reclaimed"], res["rates"]["used"]
    five = sum(by[n]["monthly_hours"] for n in res["handovers"][:5]) + sum(by[n]["monthly_hours"] for n in res["deletions"])
    if abs(five - rc["first_five_month"]) > TOL:
        P.append("hours back a month do not equal the deletions plus the top five handovers")
    if rate and rc["value_month"] is not None and abs(rc["value_month"] - five * rate) > 0.5:
        P.append("the value a month is not hours back times the rate")
    if rate is None and rc["value_month"] is not None:
        P.append("a value is shown with no rate")
    # 6 challenge
    for x in rows:
        if x["challenge"] and not x["challenge_answer"]:
            P.append(f"'{x['activity']}' was not questioned")
    # 7 confidence
    if res["source"] == "recall" and res["confidence"] != "low":
        P.append("a recall-only audit must be marked low confidence")
    # 8 summary
    if a.summary:
        try:
            s = Path(a.summary).read_text(encoding="utf-8")
        except FileNotFoundError:
            print(f"STOP: there is no summary at {a.summary}")
            sys.exit(2)
        if f"Confidence: {res['confidence']}" not in s:
            P.append("the summary does not state the confidence")
        if res["source"] == "recall" and "Low confidence" not in s:
            P.append("a recall-only summary must say Low confidence at the top")
        allowed = allowed_figures(res)
        body = re.sub(r"\b(19|20)\d\d\b", "", s)
        body = re.sub(r"\d{1,2}:\d{2}", "", body)
        body = re.sub(r"[\w.-]+\.(ics|csv|xlsx)", "", body)
        for m in re.finditer(r"(?<![\w.,])(" + NUM_TOKEN + r")", body):
            raw = canon(m.group(1))
            if raw not in allowed and f"{float(raw):g}" not in allowed:
                P.append(f"the summary shows {m.group(1)}, which the audit did not compute")
        n_ = r"([\d.,]+)"
        m = re.search(rf"about {n_} hours? a week: {n_} hours? only you can do, {n_} hours? someone could do "
                      rf"with instruction, and (?:{n_} hours? nobody should be doing|nothing that nobody should be doing)\.(?: Another {n_} hours?)?", s)
        if not m:
            P.append("the summary has no headline split of the week")
        else:
            parts = [float(canon(x)) for x in m.groups()[1:] if x]
            if abs(sum(parts) - float(canon(m.group(1)))) > 0.05 * len(parts) + 1e-9:
                P.append(f"the headline parts add to {h1(sum(parts))}, not {m.group(1)}")
    # 9 plausibility
    conf = {str(x).lower() for x in res.get("confirmed") or []}
    if rate is not None and "rate" not in conf:
        if rate < 1:
            P.append(f"an hour is valued at under 1 unit of currency ({rate:.4g}); a figure was misread")
        hm = (res.get("rates") or {}).get("helper_max")
        if hm and rate < hm:
            P.append(f"an hour is valued at {rate:,.2f}, below the dearest helper's {hm:,.2f} an hour; check the sales or rate figure")
    if not (10 <= wk <= 100) and "week" not in conf:
        P.append(f"a {h1(wk)}-hour week is outside 10 to 100 hours; check it with the founder")
    for x in P:
        print("PROBLEM:", x)
    print(f"{len(P)} problems")
    sys.exit(1 if P else 0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print(f"STOP: the check could not run ({type(e).__name__}: {e}).")
        sys.exit(2)
