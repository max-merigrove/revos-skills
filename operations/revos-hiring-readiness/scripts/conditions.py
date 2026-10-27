#!/usr/bin/env python3
"""Hiring Readiness Check: the six conditions, the verdict and the contractor alternative.

Usage:
  python3 scripts/conditions.py <inputs.json> --json-out <results.json> [--previous <old results.json>]

Reads the founder's figures (see cash_scenario.py template), runs the 13-week cash scenario with the
hire loaded, tests the six conditions, and prints the verdict (Ready, Not yet or No) with every figure
the report may quote. build.py turns results.json into the report and the workbook.

Exit codes: 0 clean, 1 ran with [NEED] flags, 2 STOP (nothing usable; fix the input and run again).
Standard library only. No network calls.
"""
import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cash_scenario import (DEFAULTS, WEEKS, WEEKS_PER_MONTH, AskFounder, InputError, cost_who, first_breach, later_start,  # noqa: E402
                           load, long_date, money, normalise, pct, ready_for_cash, scenario, simulate, fmt_plain)
import math  # noqa: E402
import calendar  # noqa: E402

PASS, FAIL, UNKNOWN = "Pass", "Fail", "Unknown"
SHORT = {1: "cash in a bad quarter", 2: "margin", 3: "six months of cover", 4: "a rising worst month",
         5: "a real role with a use for your hours", 6: "being near full after a price rise"}
NUMBER = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "All six"}
NAMES = {
    1: "Cash holds in a bad quarter",
    2: "Margin above your floor for two months",
    3: "Six months of the role covered",
    4: "Your worst month is rising",
    5: "A real role, and a use for your freed hours",
    6: "You are near full, and a price rise came first",
}
ORDER_NOTE = {
    "admin": "Admin and operations support is the usual first hire: the cheapest, it frees the most of your hours and carries the least risk.",
    "operations": "Admin and operations support is the usual first hire: the cheapest, it frees the most of your hours and carries the least risk.",
    "delivery": "Delivery usually comes second, once the delivery steps are written down well enough that someone can produce the work unaided. It raises how many clients you can serve.",
    "setter": "A setter usually comes third, once you have more leads than selling hours and your sales call is written down.",
    "closer": "A closer usually comes last. Until your sales call is written and proven, your own close rate is the business's best asset; hire for admin or delivery first unless both are already handed over.",
    "other": "The usual order is admin and operations support first, then delivery, then a setter, and a closer last. Check where this role sits before you recruit.",
}


def cond(n, status, evidence, must=None, needs=None):
    return {"n": n, "name": NAMES[n], "status": status, "evidence": evidence, "must_be_true": must or [], "needs": needs or []}


def run(raw):
    b = normalise(raw)
    cur = b["currency"]
    today = date.fromisoformat(b["date"])
    role = b["role"]
    hm = role["monthly_cost"]
    m = lambda v: money(v, cur)  # noqa: E731
    res = {"business": b["business"], "currency": cur, "date": b["date"], "role": role, "conditions": [],
           "needs": list(b["needs"]), "notes": b["notes"], "assumptions": b["assumptions"], "inputs": b}
    start_d = date.fromisoformat(role["start"])

    # 1. Cash cover
    sc = None
    if not ready_for_cash(b):
        res["conditions"].append(cond(1, UNKNOWN, "The scenario needs cash today, monthly revenue and monthly costs.",
                                      needs=["cash today, monthly revenue and monthly costs"]))
    elif hm is None:
        res["conditions"].append(cond(1, UNKNOWN, "The hire's monthly cost is missing, so the scenario cannot load it.",
                                      [f"The hire's fully loaded monthly cost, from {cost_who(b)}"]))
    else:
        sc = scenario(b, hm, role["start_week"], role["one_off"])
        wk = sc["stress_breach"]
        brk_date = today + timedelta(days=7 * (wk - 1)) if wk else None
        endw = sc["m3_week"]
        sc["end_week"] = endw
        sc["end_date"] = (today + timedelta(days=7 * (endw - 1))).isoformat()
        winw = sc["window_weeks"]
        ev = (f"With the hire loaded from {long_date(start_d)} (week {role['start_week']}), the bank in week {endw}, the hire's "
              f"13th week, is {m(sc['base_end'])} in a usual quarter and {m(sc['stress_end'])} in a bad one, against a floor of "
              f"{m(sc['floor'])}.")
        if winw > endw:
            lows = ", ".join(p["what"] for p in b["low_periods"])
            ev += (f" The test runs on to week {winw} to take in {lows}; there the bank is {m(sc['base_window_end'])} in a usual "
                   f"quarter and {m(sc['stress_window_end'])} in a bad one.")
        if role["cost_basis"] == "salary_only":
            ev += " These balances carry pay alone, so they understate the hire."
        surplus = b["monthly_revenue"] - b["costs_month_total"]
        if b["cash_today"] < sc["floor_before_start"]:
            ev += f" The bank is already below one month of today's costs ({m(sc['floor_before_start'])})."
        if wk:
            ev += f" In the bad quarter it first drops below the floor in week {wk} (the week of {long_date(brk_date)})."
            if sc["nohire_shortfall"] > 0.5:
                ev += (f" Without the hire, the same bad quarter already leaves you {m(sc['nohire_shortfall'])} short of "
                       f"{'one month' if abs(b['cover_target_months'] - 1) < 1e-9 else fmt_plain(b['cover_target_months'], 1) + ' months'} "
                       f"of costs (week {sc['nohire_shortfall_week']}); the hire adds {m(sc['hire_adds'])}.")
            else:
                ev += " Without the hire, the same bad quarter stays above the floor: the gap comes from the hire."
            must = f"An extra {m(sc['shortfall'])} in the bank before the start, with today's revenue and costs"
            if sc["nohire_shortfall"] > 0.5:
                must += f" ({m(sc['nohire_shortfall'])} of it is needed with or without the hire)"
            if surplus <= 0:
                must = (f"Money in above money out every month before any fixed cost is added (today it is {m(-surplus)} a month short); "
                        f"then an extra {m(sc['shortfall'])} in the bank before the start, at today's figures")
            ls = later_start(b, hm, role["one_off"], role["start_week"])
            sc["later_start_week"] = ls
            if ls and (wk >= 9 or ls - role["start_week"] <= 8):
                ls_d = today + timedelta(days=7 * (ls - 1))
                sc["later_start_date"] = ls_d.isoformat()
                must += f"; or, with no extra cash, a start on or after {long_date(ls_d)}, if revenue and costs hold at today's figures"
            elif sc["base_breach"] is None:
                holds = ("prepaid packages, memberships or bookings paid ahead" if b["stress_extra_days"] == 0
                         else "deposits, shorter payment terms" if (b["contracted_next_6_months"] or b["recurring_revenue_month"])
                         else "contracted work, deposits, shorter payment terms")
                must += f", or revenue that holds up in a bad quarter ({holds})"
            res["conditions"].append(cond(1, FAIL, ev, [must]))
        else:
            res["conditions"].append(cond(1, PASS, ev + f" In the bad quarter it stays above the floor in every one of the {winw} weeks."))
    res["scenario"] = sc

    # 2. Margin
    gm, fl = b["gross_margin_months"], b["margin_floor"]
    rough = b.get("gross_margin_rough")
    if len(gm) < 2 and rough:
        lo, hi = rough["low"], rough["high"]
        rng_ = pct(lo) if abs(hi - lo) < 1e-9 else f"{pct(lo)} to {pct(hi)}"
        txt = f"You put gross margin at roughly {rng_}, not month by month, against your floor of {pct(fl)}."
        if lo >= fl - 1e-9:
            res["conditions"].append(cond(2, PASS, txt + " It clears the floor even at the low end; your monthly figures "
                                          "from your bookkeeper or accounts would confirm it."))
        elif hi < fl - 1e-9:
            res["conditions"].append(cond(2, FAIL, txt + " Even the high end is below it.",
                                          [f"Two months in a row with gross margin at or above {pct(fl)}"]))
        else:
            res["conditions"].append(cond(2, UNKNOWN, txt + " The floor sits inside your range, so it cannot be judged from it.",
                                          ["Gross margin for each of the last two months, from your accounts"],
                                          ["gross margin for each of the last two months, from your accounts"]))
    elif len(gm) < 2:
        res["conditions"].append(cond(2, UNKNOWN, "Gross margin for the last two months is missing.",
                                      ["Gross margin for each of the last two months (what is left after the direct costs of delivering)"],
                                      ["gross margin for each of the last two months"]))
    else:
        txt = f"Gross margin was {pct(gm[0])} and then {pct(gm[1])}, against your floor of {pct(fl)}."
        if all(x >= fl - 1e-9 for x in gm):
            res["conditions"].append(cond(2, PASS, txt))
        else:
            k = sum(1 for x in gm if x >= fl - 1e-9)
            res["conditions"].append(cond(2, FAIL, txt + f" {'One month' if k == 1 else 'Neither month'} cleared it.",
                                          [f"Two months in a row with gross margin at or above {pct(fl)}"]))

    # 3. Role cover
    rec6 = b["contracted_next_6_months"] if b["contracted_next_6_months"] is not None else (
        b["recurring_revenue_month"] * 6 if b["recurring_revenue_month"] is not None else None)
    rep6 = b["repeat_revenue_month"] * 6 if b["repeat_revenue_month"] is not None else None
    if hm is None or (rec6 is None and rep6 is None):
        miss = [] if hm is not None else ["the role's full monthly cost"]
        if rec6 is None and rep6 is None:
            miss.append("recurring, contracted or repeat revenue for the next six months (retainers, memberships, plans, "
                        "or what comes from regulars)")
        res["conditions"].append(cond(3, UNKNOWN, "Needs " + " and ".join(miss) + ".", needs=miss))
    else:
        pw = b["pipeline_weighted"] or 0.0
        need = hm * 6
        have = (rec6 or 0.0) + (rep6 or 0.0) + pw
        parts = []
        if b["contracted_next_6_months"] is not None:
            parts.append(f"contracted revenue for the next six months ({m(rec6)})")
        elif b["recurring_revenue_month"] is not None and not (b["recurring_revenue_month"] == 0 and rep6 is not None):
            parts.append(f"recurring revenue of {m(b['recurring_revenue_month'])} a month for six months ({m(rec6)})")
        if rep6 is not None:
            how = f", {pct(b['repeat_share'])} of revenue" if b.get("repeat_share") is not None else ""
            parts.append(f"repeat revenue from regulars, memberships or plans of {m(b['repeat_revenue_month'])} a month{how}, "
                         f"for six months ({m(rep6)})")
        src = " plus ".join(parts)
        txt = (f"{src[0].upper() + src[1:]}, plus weighted pipeline of {m(pw)}, comes to {m(have)}, "
               f"against {m(need)} for six months of the role.")
        if b["pipeline_weighted"] is None:
            txt += " No pipeline was given, so none is counted."
        res["cover"] = {"have": have, "need": need, "recurring_6": rec6, "repeat_6": rep6, "pipeline_weighted": pw}
        if have >= need - 1e-9:
            res["conditions"].append(cond(3, PASS, txt))
        else:
            res["conditions"].append(cond(3, FAIL, txt, [f"A further {m(need - have)} of recurring, contracted or repeat revenue, "
                                                         "or weighted pipeline, over the next six months"]))

    # 4. Rising floor
    rh, labs = b["revenue_history"], b.get("revenue_months") or []

    def mname(i):
        return f" ({calendar.month_name[int(labs[i][5:])]} {labs[i][:4]})" if labs else ""

    if len(rh) < 12:
        res["conditions"].append(cond(4, UNKNOWN, f"Needs twelve months of revenue, month by month; {len(rh)} given.",
                                      ["Twelve months of revenue, month by month (a bank export or your accounting software's monthly report)"],
                                      ["twelve months of revenue, month by month"]))
    elif len(rh) >= 18:
        n = len(rh)
        last6, year6 = rh[-6:], rh[-18:-12]
        il, iy = n - 6 + last6.index(min(last6)), n - 18 + year6.index(min(year6))
        wl, wy = min(last6), min(year6)
        txt = (f"Your worst month in the last six was {m(wl)}{mname(il)}; in the same six months a year earlier it was "
               f"{m(wy)}{mname(iy)}.")
        res["floor_months"] = {"worst_last6": wl, "worst_year_before": wy, "basis": "year on year"}
        if wl > wy:
            res["conditions"].append(cond(4, PASS, txt + " Season for season, the floor is rising."))
        else:
            res["conditions"].append(cond(4, FAIL, txt + " Season for season, the floor is flat or falling: good months, not yet growth.",
                                          [f"Your worst month in the next six above {m(wy)}, the same season's low a year before"]))
    else:
        n = len(rh)
        last6, prev6 = rh[-6:], rh[-12:-6]
        il, ip = n - 6 + last6.index(min(last6)), n - 12 + prev6.index(min(prev6))
        wl, wp = min(last6), min(prev6)
        txt = f"Your worst month in the last six was {m(wl)}{mname(il)}; in the six before it was {m(wp)}{mname(ip)}."
        res["floor_months"] = {"worst_last6": wl, "worst_prev6": wp, "basis": "half on half"}
        if wl > wp:
            res["conditions"].append(cond(4, PASS, txt + " The floor is rising."))
        else:
            res["conditions"].append(cond(4, UNKNOWN, txt + " These two halves cover different seasons, so a lower worst month "
                                          "may be a season, not a fall. Comparing the same months a year apart needs at least "
                                          "18 months of revenue.",
                                          ["Revenue for the same six months a year earlier, so the worst month can be compared season for season"],
                                          ["revenue for the same six months a year earlier (18 months of monthly revenue in all)"]))

    # 5. Coherent role and a use for the freed hours
    tasks = b["tasks"]
    th = sum(t["hours_week"] or 0 for t in tasks)
    rh_ = role["hours_week"]
    fails, needs5 = [], []
    if not tasks:
        fails.append("No tasks named for the role yet")
        needs5.append("the tasks this person would take off you, with rough hours a week")
    elif rh_:
        share = th / rh_
        if share < DEFAULTS["role_filled_share"][0] - 1e-9:
            fails.append(f"Named tasks fill {fmt_plain(th, 1)} of the role's {fmt_plain(rh_, 1)} hours a week; the rest has no named work")
    if b["role_coherent"]["value"] is False:
        fails.append(f"The tasks do not form one job{': ' + b['role_coherent']['reason'] if b['role_coherent']['reason'] else ''}")
    big = max(tasks, key=lambda t: t["hours_week"] or 0) if tasks else None
    big_unknown = bool(big) and big["written_down"] == "unknown"
    if big and big["written_down"] == "no":
        fails.append(f"The biggest task, {big['task']}, is not written down, so there is nothing to hand over yet")
    if big_unknown:
        needs5.append(f"Is {big['task']} written down anywhere?")
    if not b["freed_hours_use"]:
        fails.append("No named use for the hours you get back")
        needs5.append("what you would do with the hours you get back")
    elif b["freed_use_has_revenue_path"] is False:
        fails.append(f"The freed hours go to '{b['freed_hours_use']}', which has no route to revenue")
    txt = (f"Tasks named: {', '.join(t['task'] + ' (' + fmt_plain(t['hours_week'] or 0, 1) + ' h)' for t in tasks) or 'none'}. "
           f"Role: {fmt_plain(rh_, 1) if rh_ else '[NEED]'} hours a week. Freed hours go to: {b['freed_hours_use'] or '[NEED]'}.")
    if fails:
        must = []
        for f in fails:
            if f.startswith("Named tasks fill"):
                must.append(f"Name the work for the remaining {fmt_plain(rh_ - th, 1)} hours a week, or cut the role to {fmt_plain(th, 1)} hours")
            elif f.startswith("The biggest task"):
                must.append(f"{big['task']} written down well enough that someone else could do it from the notes")
            elif f.startswith("No named use"):
                must.append("A named use for the freed hours, with a route to revenue (usually selling)")
            elif "no route to revenue" in f:
                must.append("The freed hours pointed at work that brings in revenue, usually selling")
            elif f.startswith("The tasks do not"):
                must.append("The tasks grouped into one job one person could own")
        res["conditions"].append(cond(5, FAIL, txt + " " + ". ".join(fails) + ".", must, needs5))
    elif big_unknown:
        res["conditions"].append(cond(5, UNKNOWN, txt + f" Whether {big['task']}, the biggest task, is written down is not known.",
                                      [f"{big['task']} written down well enough that someone else could do it from the notes"], needs5))
    elif b["role_coherent"]["value"] is None:
        res["conditions"].append(cond(5, UNKNOWN, txt + " Whether the tasks form one job has not been judged.",
                                      ["A judgement on whether the tasks form one job"]))
    else:
        res["conditions"].append(cond(5, PASS, txt))

    # 6. Capacity and a price rise first
    cap = b["capacity"]
    prt = b["price_rise_tested"]
    if (cap["now"] is None or cap["max"] is None) and cap.get("room_for") is not None:
        said = f" ('{cap['said']}')" if cap.get("said") else ""
        res["conditions"].append(cond(6, UNKNOWN, f"You said you have room for about {fmt_plain(cap['room_for'], 1)} more "
                                      f"{cap['unit']}{said}. How full that is depends on how many you have now, which is not given.",
                                      [f"How many {cap['unit']} you have now, so room for {fmt_plain(cap['room_for'], 1)} more can be read as a share",
                                       "A price rise for new clients tested first: the cheapest capacity there is"] if b["price_rise_tested"]["value"] is not True
                                      else [f"How many {cap['unit']} you have now, so room for {fmt_plain(cap['room_for'], 1)} more can be read as a share"],
                                      [f"how many {cap['unit']} you have now"]))
    elif cap["now"] is None or cap["max"] is None:
        res["conditions"].append(cond(6, UNKNOWN, "Needs how full you are now against the most you can take on.",
                                      ["How many client hours (or clients) you have now, and the most you can take on"],
                                      ["how full you are now against the most you can take on"]))
    else:
        share = cap["now"] / cap["max"]
        nc = DEFAULTS["near_ceiling"][0]
        txt = f"You are at {fmt_plain(cap['now'], 1)} of the {fmt_plain(cap['max'], 1)} {cap['unit']} you can take on ({pct(share)})."
        must = []
        if share < nc - 1e-9:
            must.append(f"Working at {pct(nc)} or more of what you can take on before adding fixed cost (your figure is {pct(share)})")
        if prt["value"] is not True:
            txt += f" A price rise for new clients: {'not tested' if prt['value'] is False else 'not said'}."
            must.append("A price rise for new clients tested first: the cheapest capacity there is")
        else:
            txt += f" Price rise tested: {prt['said']}."
        res["conditions"].append(cond(6, FAIL if must else PASS, txt, must,
                                      [] if prt["value"] is not None else ["whether you have put prices up for new clients recently"]))

    # what the hire can cost, and what it has to bring in
    res["ceiling"] = ceiling(b, role, sc)
    res["pays_its_way"] = pays_its_way(b, role)

    # contractor alternative
    res["contractor"] = contractor(b, m)
    res["order_note"] = ORDER_NOTE.get(role["type"], ORDER_NOTE["other"])
    for c in res["conditions"]:
        for n in c["needs"]:
            if not any(n.lower() in x.lower() or x.lower() in n.lower() for x in res["needs"]):
                res["needs"].append(n[0].upper() + n[1:])
    res["cost_loaded"] = role["cost_basis"] == "loaded" and hm is not None
    res["verdict"], res["verdict_reason"] = verdict(b, res, m)
    res["defaults"] = {k: DEFAULTS[k][1] for k in DEFAULTS}
    return res


def _holds(b, cost, start_week, one_off, stress):
    rows = simulate(b, cost, start_week, one_off, stress=stress)
    return first_breach(rows, b, cost, start_week) is None


def ceiling(b, role, sc):
    """The most the hire can cost a month, all in, with the cash holding the floor in every week to its 13th week (and
    through any named low period), in a usual and a bad quarter. Plain arithmetic on the founder's own figures: it says
    how much room the business has for the whole cost, never what goes on top of pay. 0 means the floor breaks even
    without the hire. Rounded down to a whole 10."""
    if sc is None and not ready_for_cash(b):
        return None
    sw, one = role["start_week"], role["one_off"] or 0.0
    out = {}
    for key, stress in (("usual", False), ("bad", True)):
        if not _holds(b, 0.0, sw, one, stress):
            out[key] = 0.0
            continue
        lo, hi = 0.0, max(b["monthly_revenue"], b["costs_month_total"], 1.0) * 4
        if _holds(b, hi, sw, one, stress):
            out[key] = hi
            continue
        for _ in range(60):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if _holds(b, mid, sw, one, stress) else (lo, mid)
        out[key] = math.floor(lo / 10) * 10
    hm = role["monthly_cost"]
    out["cost_used"] = hm
    out["basis"] = role["cost_basis"]
    if hm is not None:
        out["room_usual"] = out["usual"] - hm
        out["room_bad"] = out["bad"] - hm
    return out


def pays_its_way(b, role):
    """Extra revenue a month the hire has to bring in, or protect, to cover its own cost at today's gross margin, and
    how many typical new clients that is when the founder gave a typical client's monthly fee."""
    hm = role["monthly_cost"]
    gm = b["gross_margin_months"][-1] if b["gross_margin_months"] else (
        b["gross_margin_rough"]["low"] if b.get("gross_margin_rough") else None)
    if hm is None or not gm or gm <= 0:
        return None
    rev = hm / gm
    out = {"revenue_month": rev, "margin": gm, "cost": hm, "basis": role["cost_basis"]}
    if b.get("typical_client_month"):
        out["typical_client_month"] = b["typical_client_month"]
        out["clients"] = math.ceil(rev / b["typical_client_month"] - 1e-9)
    return out


def contractor(b, m):
    role = b["role"]
    rate, hrs = b["contractor_rate_hour"], role["hours_week"]
    line = b["contractor_line_hours"]
    out = {"line": line, "rate": rate, "runs": []}
    if rate is None or not hrs or not ready_for_cash(b):
        out["status"] = "not run"
        out["need"] = "A contractor's hourly rate (a quote from a freelancer or agency you would use)" if rate is None else \
            "the role's hours and the business figures"
        return out
    for h in sorted({hrs, min(hrs, line)}, reverse=True):
        month = rate * h * 52 / 12
        sc = scenario(b, month, b["role"]["start_week"], 0.0)
        out["runs"].append({"hours_week": h, "monthly": month, "passes": sc["stress_breach"] is None,
                            "stress_breach": sc["stress_breach"], "stress_end": sc["stress_end"], "base_end": sc["base_end"],
                            "floor": sc["floor"]})
    out["status"] = "run"
    return out


def verdict(b, res, m):
    st = {c["n"]: c["status"] for c in res["conditions"]}
    role = b["role"]
    hrs = role["hours_week"]
    if role["employment"] != "contractor" and hrs and hrs < b["contractor_line_hours"] - 1e-9:
        return "No", (f"Not as an employee. At {fmt_plain(hrs, 1)} hours a week the work sits under the "
                      f"{fmt_plain(b['contractor_line_hours'])} hour line, where a contractor you can stop is the right first step.")
    sc = res.get("scenario")
    surplus = (b["monthly_revenue"] - b["costs_month_total"]) if ready_for_cash(b) else None
    if sc and surplus is not None and surplus <= 0 and sc["base_breach"]:
        return "No", (f"Not with today's figures. The business already spends {m(-surplus)} a month more than it brings in, "
                      f"and even the usual quarter drops below the floor in week {sc['base_breach']}. A hire adds to the gap.")
    c5 = next(c for c in res["conditions"] if c["n"] == 5)
    if not b["tasks"] and not b["freed_hours_use"] and c5["status"] == FAIL and not b.get("provisional"):
        return "No", "Not yet a job. There are no named tasks for the person and no named use for the hours you would get back."
    if all(v == PASS for v in st.values()) and res["cost_loaded"]:
        return "Ready", "All six conditions pass with the fully loaded cost of the hire and a bad quarter assumed."
    fails = [c for c in res["conditions"] if c["status"] != PASS]
    if not fails and role["cost_basis"] == "salary_only":
        return "Not yet", ("Every condition passes on pay alone, which understates the hire. Get the fully loaded monthly cost "
                           f"from {cost_who(b)} and run it again.")
    if not fails:
        return "Not yet", (f"Every condition passes on {m(role['monthly_cost'])} a month, but that is not confirmed as the fully loaded "
                           f"cost. Check it with {cost_who(b)} and run it again.")
    def join(xs):
        return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]
    failed = [SHORT[c["n"]] for c in fails if c["status"] == FAIL]
    unknown = [SHORT[c["n"]] for c in fails if c["status"] == UNKNOWN]
    parts = []
    if failed:
        parts.append(f"{NUMBER[len(failed)].lower()} {'fails' if len(failed) == 1 else 'fail'} on today's figures: {join(failed)}")
    if unknown:
        parts.append(f"{NUMBER[len(unknown)].lower()} {'needs' if len(unknown) == 1 else 'need'} "
                     f"a figure before {'it' if len(unknown) == 1 else 'they'} can be judged: {join(unknown)}")
    return "Not yet", "Of the six conditions, " + "; ".join(parts) + "."


def changes(prev, res):
    out = []
    pc = {c["n"]: c["status"] for c in prev.get("conditions", [])}
    for c in res["conditions"]:
        if c["n"] in pc and pc[c["n"]] != c["status"]:
            out.append(f"Condition {c['n']} ({c['name']}): {pc[c['n']]} to {c['status']}")
    if prev.get("verdict") and prev["verdict"] != res["verdict"]:
        out.append(f"Verdict: {prev['verdict']} to {res['verdict']}")
    pi, ni = prev.get("inputs", {}), res["inputs"]
    for k, lab in (("cash_today", "Cash today"), ("monthly_revenue", "Monthly revenue"), ("costs_month_total", "Monthly costs")):
        if pi.get(k) is not None and ni.get(k) is not None and abs(pi[k] - ni[k]) > 0.5:
            out.append(f"{lab}: {money(pi[k], res['currency'])} to {money(ni[k], res['currency'])}")
    pr, nr = (pi.get("role") or {}), ni["role"]
    if pr.get("monthly_cost") is not None and nr.get("monthly_cost") is not None and abs(pr["monthly_cost"] - nr["monthly_cost"]) > 0.5:
        out.append(f"Role cost a month: {money(pr['monthly_cost'], res['currency'])} to {money(nr['monthly_cost'], res['currency'])}")
    psc, nsc = prev.get("scenario"), res.get("scenario")
    if psc and nsc:
        out.append(f"Bad quarter, 13th week of the hire: {money(psc['stress_end'], res['currency'])} last time, {money(nsc['stress_end'], res['currency'])} now")
    return {"since": prev.get("date"), "lines": out}


def printout(res):
    cur = res["currency"]
    prov = " (provisional: first answer before the questions)" if res["inputs"].get("provisional") else ""
    print(f"VERDICT{prov}: {res['verdict']}. {res['verdict_reason']}")
    sc = res.get("scenario")
    b = res["inputs"]
    print(f"NUMBERS: read with a decimal {'comma' if b.get('decimal_style') == 'comma' else 'point'}"
          f"{'' if b.get('decimal_style') else ' (no decimals seen; set decimal_style if the founder writes 1.234,56)'}; "
          f"country {b.get('country') or 'not given'}; dates {b.get('date_style')}; paper {b.get('paper')}")
    if sc:
        print(f"MONTH THREE: base {money(sc['base_end'], cur)}, stress {money(sc['stress_end'], cur)}, floor {money(sc['floor'], cur)}, "
              f"stress first below floor: {('week ' + str(sc['stress_breach'])) if sc['stress_breach'] else 'never'}")
        if sc["window_weeks"] > sc["m3_week"]:
            print(f"WINDOW: runs to week {sc['window_weeks']} for the low periods named; there: base {money(sc['base_window_end'], cur)}, "
                  f"stress {money(sc['stress_window_end'], cur)}")
        print(f"NO HIRE: the same bad quarter without the hire is short of the floor by {money(sc['nohire_shortfall'], cur)} at most"
              + (f" (week {sc['nohire_shortfall_week']}); the hire adds {money(sc['hire_adds'], cur)}" if sc["nohire_shortfall"] > 0.5 else ""))
    ce = res.get("ceiling")
    if ce:
        if ce["usual"] <= 0:
            print("CEILING: none. The usual quarter breaks the floor even without the hire.")
        else:
            line = (f"CEILING: the most the hire can cost a month, all in, with the cash holding the floor to its 13th week: "
                    f"{money(ce['usual'], cur)} in a usual quarter, "
                    + (f"{money(ce['bad'], cur)} in a bad one" if ce["bad"] > 0 else "none in a bad one (the bad quarter breaks the floor even without the hire)"))
            if ce.get("cost_used") is not None:
                lab = "pay alone" if ce["basis"] == "salary_only" else "the cost used"

                def rm(v):
                    return f"room of {money(v, cur)}" if v >= 0 else f"over by {money(-v, cur)}"
                line += f". Against {lab} of {money(ce['cost_used'], cur)}: {rm(ce['room_usual'])} a month in a usual quarter"
                line += f", {rm(ce['room_bad'])} in a bad one" if ce["bad"] > 0 else ""
                if ce["basis"] == "salary_only":
                    line += "; whatever goes on top of pay has to fit inside that room"
            print(line)
    pw_ = res.get("pays_its_way")
    if pw_:
        line = (f"PAYS ITS WAY: at {pct(pw_['margin'])} gross margin the hire has to bring in or protect {money(pw_['revenue_month'], cur)} "
                f"a month of revenue to cover {money(pw_['cost'], cur)}" + (" (pay alone, so the real figure is higher)" if pw_["basis"] == "salary_only" else ""))
        if pw_.get("clients"):
            line += f"; at {money(pw_['typical_client_month'], cur)} a typical client, {pw_['clients']} new clients"
        print(line)
    for s in b.get("season") or []:
        print("SEASON:", s["text"])
    for c in res["conditions"]:
        print(f"{c['n']}. {c['name']}: {c['status']}. {c['evidence']}")
        for x in c["must_be_true"]:
            print(f"   must be true: {x}")
    ct = res["contractor"]
    if ct["status"] == "run":
        for r in ct["runs"]:
            print(f"CONTRACTOR: {fmt_plain(r['hours_week'], 1)} h a week at {money(ct['rate'], cur)} = {money(r['monthly'], cur)} a month: "
                  f"{'passes the cash test' if r['passes'] else 'fails the cash test in week ' + str(r['stress_breach'])}")
    else:
        print(f"CONTRACTOR: not run. NEED: {ct['need']}")
    basis = res["role"].get("cost_basis")
    print("COST BASIS: " + {"loaded": "the fully loaded figure the founder supplied",
                            "salary_only": "pay alone; the scenario understates the hire and Ready is blocked"}.get(
        basis, "not confirmed as fully loaded; Ready is blocked until it is"))
    for a in res["assumptions"]:
        print("ASSUMED:", a)
    for n in res["notes"]:
        print("NOTE:", n)
    for n in res["needs"]:
        print("NEED:", n)
    if res.get("changes"):
        for x in res["changes"]["lines"]:
            print("SINCE:", x)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs")
    ap.add_argument("--json-out")
    ap.add_argument("--previous")
    a = ap.parse_args()
    res = run(load(a.inputs))
    if a.previous:
        p = Path(a.previous)
        if not p.exists():
            raise InputError(f"there is no previous results file at {a.previous}")
        res["changes"] = changes(json.loads(p.read_text(encoding="utf-8")), res)
    if a.json_out:  # written before printing, so a cut-off print never loses the results
        Path(a.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.json_out).write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    printout(res)
    if a.json_out:
        print(f"WROTE: {a.json_out}")
    return 1 if res["needs"] else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        sys.exit(0)
    except AskFounder as e:
        for q in e.questions:
            print("ASK:", q)
        print("STOP: one or more figures need the founder's answer first (ASK lines). Nothing was written.")
        sys.exit(2)
    except InputError as e:
        print(f"STOP: {e}. Nothing was written.")
        sys.exit(2)
    except Exception as e:  # noqa: BLE001
        print(f"STOP: the script could not read these inputs ({type(e).__name__}: {e}). Check the inputs file. Nothing was written.")
        sys.exit(2)
