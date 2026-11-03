#!/usr/bin/env python3
"""Unpaid work under a set of payment terms, and the terms ladder.

The question it answers: at the worst moment, how much finished work has the founder delivered that the client
has not yet paid for, for how long, and how much cash is in by the end of the work?

Model (all working defaults, shown in the brief):
- Work is delivered evenly across the project (or across each stage, if the founder gives stage values).
- A deposit is paid at signature, before work starts (day 0).
- A stage is invoiced when it completes (or on the founder's invoice day of the month after it completes) and
  paid the stated number of days later.
- Ongoing work: each month's work is delivered evenly across that month, invoiced at its start (in advance) or
  end (in arrears), paid the stated number of days later.

Usage (paths relative to this skill's folder):
  python3 scripts/exposure.py --self-test      closed form checked against a brute-force simulation of 200
                                               random schedules, plus the ladder rules
Imported by brief.py. Standard library only. No network calls.
"""
import calendar
import random
import sys
from datetime import date, timedelta

PROJECT_RUNGS = {
    1: {"deposit": 30, "stages": [(70, 1.0)], "days": 14, "held": False,
        "label": "30% deposit, balance on delivery, 14 days"},
    2: {"deposit": 50, "stages": [(25, 0.5), (25, 1.0)], "days": 14, "held": False,
        "label": "50% deposit, then two stage payments, 14 days"},
    3: {"deposit": 50, "stages": [(25, 1 / 3), (15, 2 / 3), (10, 1.0)], "days": 7, "held": True,
        "label": "50% deposit, stages of 25%, 15% and 10% (the last on handover), 7 days, files held until paid"},
}
FIRST_PHASE_SHARE = 25  # rung 4: a first phase of about a quarter of the work, paid in full before it starts
RETAINER_RUNGS = {
    1: {"billing": "advance", "days": None, "pause": False, "card": False, "label": "monthly in advance, your usual days"},
    2: {"billing": "advance", "days": 14, "pause": True, "card": False,
        "label": "monthly in advance, 14 days, work pauses on an overdue invoice"},
    3: {"billing": "advance", "days": 7, "pause": True, "card": True,
        "label": "monthly in advance, 7 days, card or direct debit on file where you take them, pause on overdue"},
}
VERDICT_FLOOR = {"GO": 0, "CAUTION": 2, "STOP": 4}
MONTH_DAYS = 30.4375


class TermsError(ValueError):
    """Plain question for the founder; brief.py prints it as a STOP line."""


# ------------------------------------------------------------------ calendar helpers
def add_months(d, n):
    y, m = divmod(d.month - 1 + n, 12)
    y += d.year
    m += 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def next_invoice_day(d, day):
    """First date on or after d whose day of month is `day` (clipped to short months)."""
    for k in range(0, 3):
        base = add_months(date(d.year, d.month, 1), k)
        cand = date(base.year, base.month, min(day, calendar.monthrange(base.year, base.month)[1]))
        if cand >= d:
            return cand
    raise TermsError("could not place the invoice day")


# ------------------------------------------------------------------ schedules
def project_schedule(fee, length_days, deposit_pct, stages, days, start=None, invoice_day=None, stage_values=None):
    """stages: list of (pct, fraction of the project at which it completes). Returns (payments, segments).
    payments: list of dicts with amount, invoice, paid (days from start), label. segments: (start, end, value)."""
    if fee < 1:
        raise TermsError("the fee is below 1; please check the figure")
    if not 7 <= length_days <= 104 * 7:
        raise TermsError("the project length should be between 1 and 104 weeks; please check it")
    if not 0 <= deposit_pct <= 100:
        raise TermsError("the deposit should be between 0% and 100%; please check it")
    if days < 0 or days > 365:
        raise TermsError("days to pay should be between 0 and 365; please check them")
    total_pct = deposit_pct + sum(p for p, _ in stages)
    if abs(total_pct - 100) > 0.01:
        raise TermsError(f"the deposit and stage payments add up to {total_pct:g}%, not 100%; please check them")
    for _, f in stages:
        if not 0 < f <= 1:
            raise TermsError("each stage must complete during the project")
    pays, running = [], 0.0
    parts = ([("deposit", deposit_pct, 0.0)] if deposit_pct else []) + [(f"stage {i + 1}", p, f) for i, (p, f) in enumerate(stages)]
    for i, (label, pct, frac) in enumerate(parts):
        amt = round(fee * pct / 100, 2) if i < len(parts) - 1 else round(fee - running, 2)
        running += amt
        if label == "deposit":
            pays.append({"label": "deposit", "pct": pct, "amount": amt, "complete": 0.0, "invoice": 0.0, "paid": 0.0})
            continue
        complete = frac * length_days
        inv = complete
        if invoice_day and start:
            d = start + timedelta(days=round(complete))
            inv = (next_invoice_day(d, invoice_day) - start).days
        pays.append({"label": label, "pct": pct, "amount": amt, "complete": complete, "invoice": float(inv),
                     "paid": float(inv) + days})
    if stage_values:
        segs, prev = [], 0.0
        for (pct, frac), v in zip(stages, stage_values):
            segs.append((prev, frac * length_days, fee * v / 100))
            prev = frac * length_days
    else:
        segs = [(0.0, float(length_days), float(fee))]
    return pays, segs


def retainer_schedule(monthly_fee, months, billing, days, start, invoice_day=None, prepaid=False):
    if monthly_fee < 1:
        raise TermsError("the monthly fee is below 1; please check the figure")
    if not 1 <= months <= 36:
        raise TermsError("the engagement should run between 1 and 36 months; please check it")
    if days < 0 or days > 365:
        raise TermsError("days to pay should be between 0 and 365; please check them")
    pays, segs = [], []
    for k in range(months):
        s = (add_months(start, k) - start).days
        e = (add_months(start, k + 1) - start).days
        segs.append((float(s), float(e), float(monthly_fee)))
        if prepaid:
            inv, paid = s, s
        else:
            inv = s if billing == "advance" else e
            if invoice_day:
                inv = (next_invoice_day(start + timedelta(days=inv), invoice_day) - start).days
            paid = inv + days
        amt = round(monthly_fee, 2) if k < months - 1 else round(monthly_fee * months - round(monthly_fee, 2) * (months - 1), 2)
        pays.append({"label": f"month {k + 1}", "pct": None, "amount": amt, "complete": float(e),
                     "invoice": float(inv), "paid": float(paid)})
    return pays, segs


# ------------------------------------------------------------------ the closed form
def delivered(t, segs):
    out = 0.0
    for s, e, v in segs:
        if t >= e:
            out += v
        elif t > s:
            out += v * (t - s) / (e - s)
    return out


def cash_before(t, pays):
    return sum(p["amount"] for p in pays if p["paid"] < t)


def cash_by(t, pays):
    return sum(p["amount"] for p in pays if p["paid"] <= t)


def exposure(pays, segs, limit=None):
    """Peak unpaid work, days with unpaid work, days above the limit, cash by the end of the work."""
    end = max(e for _, e, _ in segs)
    points = sorted({0.0, end} | {s for s, _, _ in segs} | {e for _, e, _ in segs} | {p["paid"] for p in pays})
    peak, peak_at = 0.0, 0.0
    for t in points:
        if t <= 0:
            continue
        u = delivered(t, segs) - cash_before(t, pays)
        if u > peak + 1e-9:
            peak, peak_at = u, t
    carried = above = 0.0
    for a, b in zip(points, points[1:]):
        ua = delivered(a, segs) - cash_by(a, pays)
        ub = delivered(b, segs) - cash_before(b, pays)
        carried += _positive_len(a, b, ua, ub, 0.0)
        if limit is not None:
            above += _positive_len(a, b, ua, ub, limit)
    last = max(p["paid"] for p in pays)
    return {"peak": round(peak, 2), "peak_day": peak_at, "days_carried": carried, "days_above_limit": above,
            "cash_by_end": round(cash_by(end, pays), 2), "end_day": end, "last_payment_day": last,
            "weeks_carried": round(carried / 7, 1), "weeks_to_last_payment": round(last / 7, 1)}


EPS = 0.01  # one cent: rounding residue is not unpaid work


def _positive_len(a, b, ua, ub, level):
    ua, ub = ua - level - EPS, ub - level - EPS
    if ua > 0 and ub > 0:
        return b - a
    if ua <= 0 and ub <= 0:
        return 0.0
    x = a + (b - a) * (0 - ua) / (ub - ua)
    return (b - x) if ub > 0 else (x - a)


def brute_force(pays, segs, step=0.05):
    end = max(max(e for _, e, _ in segs), max(p["paid"] for p in pays)) + 1
    t, peak, carried = step, 0.0, 0.0
    while t <= end:
        u = delivered(t, segs) - cash_by(t, pays)
        u_left = delivered(t, segs) - cash_before(t, pays)
        peak = max(peak, u, u_left)
        if u > EPS:
            carried += step
        t += step
    return peak, carried


# ------------------------------------------------------------------ the ladder
def project_rung_terms(rung, usual_deposit, usual_days):
    if rung == 0:
        d = usual_deposit if usual_deposit is not None else 30
        return {"deposit": d, "stages": [(100 - d, 1.0)] if d < 100 else [], "days": usual_days if usual_days is not None else 14,
                "held": False, "label": f"your usual terms: {d:g}% deposit, balance on delivery, "
                                         f"{usual_days if usual_days is not None else 14:g} days"}
    return PROJECT_RUNGS[rung]


def choose(verdict, limit, evaluate, max_rung=3, deposit_cap=None, rung_deposit=None, floor=None):
    """Lightest rung at or above the verdict's floor whose peak is within the limit.
    evaluate(rung) -> exposure dict. Returns (rung, fits, tried) where tried maps rung to its exposure."""
    floor = VERDICT_FLOOR[verdict] if floor is None else max(floor, VERDICT_FLOOR[verdict])
    if floor >= 4:
        return 4, True, {}
    tried, skipped = {}, []
    for r in range(floor, max_rung + 1):
        if deposit_cap is not None and rung_deposit and rung_deposit(r) > deposit_cap + 1e-9:
            skipped.append(r)
            continue
        tried[r] = evaluate(r)
        if r > floor and 0 in tried and tried[r]["peak"] >= tried[0]["peak"] - 0.005:
            continue  # never step to a rung that is not tighter than the founder's own terms
        if limit is None or tried[r]["peak"] <= limit + 0.005:
            return r, True, tried
    if not tried:
        return floor, False, tried
    return max(tried), False, tried


# ------------------------------------------------------------------ self-test
def _self_test():
    ok = fail = 0

    def check(cond, label):
        nonlocal ok, fail
        if cond:
            ok += 1
        else:
            fail += 1
            print("FAIL", label)

    # Hand-worked cases
    p, s = project_schedule(14000, 70, 0, [(100, 1.0)], 60)
    e = exposure(p, s, 3000)
    check(e["peak"] == 14000 and abs(e["weeks_to_last_payment"] - 18.6) < 0.05, f"net 60 at end: {e}")
    check(e["cash_by_end"] == 0, "no cash by end")
    p, s = project_schedule(14000, 70, 50, [(25, 0.5), (25, 1.0)], 14)
    e = exposure(p, s, 3000)
    check(e["peak"] == 3500, f"rung 2 on 14,000 over 10 weeks: {e['peak']}")
    p, s = retainer_schedule(38000 / 6, 6, "arrears", 30, date(2026, 11, 2))
    e = exposure(p, s)
    check(12000 < e["peak"] < 13500, f"monthly arrears net 30 (a short February adds two days): {e['peak']}")
    p, s = retainer_schedule(38000 / 6, 6, "advance", 30, date(2026, 11, 2))
    check(6333 < exposure(p, s)["peak"] < 7000, "monthly advance net 30")
    p, s = retainer_schedule(1000, 3, "advance", 0, date(2026, 11, 2), prepaid=True)
    check(exposure(p, s)["peak"] == 0, "prepaid month peak 0")
    p, s = project_schedule(9500, 56, 50, [(25, 0.5), (25, 1.0)], 14)
    check(exposure(p, s)["peak"] == 2375, "rung 2 on 9,500")
    # Invoice day: completion on day 84 from 2 Nov 2026 is 25 Jan 2027; next 5th is 5 Feb 2027
    p, s = project_schedule(450000, 84, 0, [(100, 1.0)], 90, start=date(2026, 11, 2), invoice_day=5)
    check((date(2026, 11, 2) + timedelta(days=p[-1]["invoice"])) == date(2027, 2, 5), "invoice on the 5th")
    # Stops
    for args, label in [((0.5, 70, 0, [(100, 1.0)], 30), "fee"), ((1000, 3, 0, [(100, 1.0)], 30), "length"),
                        ((1000, 70, 120, [], 30), "deposit"), ((1000, 70, 30, [(60, 1.0)], 30), "sum"),
                        ((1000, 70, 0, [(100, 1.0)], 400), "days")]:
        try:
            project_schedule(*args)
            check(False, f"no stop on {label}")
        except TermsError:
            check(True, label)
    # Ladder
    ev = lambda r: exposure(*project_schedule(18000, 56, *({0: (30, [(70, 1.0)], 14)}.get(r) or
                                                             (PROJECT_RUNGS[r]["deposit"], PROJECT_RUNGS[r]["stages"], PROJECT_RUNGS[r]["days"]))))
    r, fits, tried = choose("GO", 4000, ev)
    check(r == 3 and fits, f"Go with low limit climbs to 3: {r} {[(k, v['peak']) for k, v in tried.items()]}")
    r, fits, _ = choose("CAUTION", 100, ev)
    check(r == 3 and not fits, "no rung fits")
    r, _, _ = choose("STOP", 4000, ev)
    check(r == 4, "stop is rung 4")
    r, fits, _ = choose("GO", 4000, ev, deposit_cap=30, rung_deposit=lambda k: 30 if k < 2 else 50)
    check(not fits and r == 1, "deposit cap blocks rungs 2 and 3")
    # Brute force over 200 random schedules
    rnd = random.Random(7)
    worst = 0.0
    for i in range(200):
        fee = rnd.choice([900, 4500, 14000, 22000, 38000, 450000])
        length = rnd.randint(7, 40 * 7)
        dep = rnd.choice([0, 10, 25, 30, 50])
        n = rnd.randint(1, 4)
        cuts = sorted(rnd.uniform(0.05, 1.0) for _ in range(n - 1)) + [1.0]
        rest = 100 - dep
        shares = [rnd.random() for _ in range(n)]
        pcts = [rest * x / sum(shares) for x in shares]
        days = rnd.choice([0, 7, 14, 30, 45, 60, 90])
        if rnd.random() < 0.25:
            pays, segs = retainer_schedule(fee / 6, rnd.randint(1, 12), rnd.choice(["advance", "arrears"]), days,
                                           date(2026, 1, 31))
        else:
            sv = None
            if rnd.random() < 0.3:
                w = [rnd.random() for _ in range(n)]
                sv = [100 * x / sum(w) for x in w]
            pays, segs = project_schedule(fee, length, dep, list(zip(pcts, cuts)), days, stage_values=sv)
        e = exposure(pays, segs)
        bp, bc = brute_force(pays, segs)
        tol = max(1.0, max(v / max(b - a, 1e-9) for a, b, v in segs) * 0.05 * 1.2)
        if abs(bp - e["peak"]) > tol or abs(bc - e["days_carried"]) > 0.2 + 0.002 * e["days_carried"]:
            check(False, f"brute force {i}: peak {e['peak']} vs {bp:.2f}, carried {e['days_carried']:.2f} vs {bc:.2f}")
        else:
            check(True, "bf")
        worst = max(worst, abs(bp - e["peak"]))
    ev2 = lambda r: {"peak": {0: 4080, 1: 4760, 2: 2720, 3: 793}[r]}
    r, fits, _ = choose("GO", 5000, ev2)
    check(r == 0, "usual terms within limit stay")
    r, fits, _ = choose("GO", 4000, ev2)
    check(r == 2, f"a rung looser than the founder's own terms is skipped: {r}")
    print(f"{ok} passed, {fail} failed (largest brute-force gap {worst:.2f})")
    return fail == 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--self-test":
        sys.exit(0 if _self_test() else 1)
    print(__doc__)
    sys.exit(0)
