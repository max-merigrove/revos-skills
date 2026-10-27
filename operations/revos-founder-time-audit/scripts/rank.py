#!/usr/bin/env python3
"""Founder Time Audit: categories, shares, flags, the ranked handover list, the value of the hours
and a proposed week, from one audit file.

Usage:
  python3 scripts/rank.py <audit.json> --out <results.json> [--previous <previous.json>]

The audit file is the activities.json written by parse_calendar.py, with Claude's judgement added
to every row (category, function, action, who, reason), plus what the founder said (hours worked
in a week, rate or monthly sales, team, protected work). A recall-only audit is the same file with
"source": "recall" and rows typed from the founder's description.

Rules this script enforces (they come from the method, not from taste):
  - every row has one category (1 only you, 2 someone with instruction, 3 nobody should) and one
    action; category 1 is keep, category 3 is delete, category 2 is delegate or automate (keep
    only with a reason);
  - deletions come first; handovers are ranked by hours per instance times instances per month,
    never by ease;
  - hours reconcile: rows plus "not placed" equal the week the founder gave (or the calendar plus
    the stated allowance); rows that add to more than that stop the run;
  - only-you rows that look like admin, reporting or scheduling must carry the founder's answer to
    one challenge (challenge_answer) before the report is built;
  - Doing (delivery plus admin) above 50% and Strategy below 15% are flagged; a strategy block of at
    least 4 hours a week goes into the proposed week when Strategy is below 15%.

Exit codes: 0 clean, 1 written with NEED or CHALLENGE lines to resolve, 2 stopped (STOP line).
Standard library only. No network calls.
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import locale_numbers as LN  # noqa: E402
import timeparse  # noqa: E402
from timeparse import (SYMBOL_FOR, WEEKS_PER_MONTH, AmbiguousInput, InputError, currency_of, fmt_money,  # noqa: E402
                       hourly_amount, hours as parse_hours, monthly_amount, per_month as parse_per_month,
                       week_hours as parse_week_hours)

SKILL = "revos-founder-time-audit"

# Working thresholds and defaults, in one place. Sources in references/method.md.
DOING_FLAG = 0.50            # Doing above this share of the week: hand over the top-ranked task
STRATEGY_FLAG = 0.15         # Strategy below this share: fix a protected block
STRATEGY_BLOCK_HOURS = 4.0   # the protected block, at least this many hours a week
UNTRACKED_DEFAULT = 0.20     # calendars miss email and admin: calendar plus 20% when no total is given (to confirm)
GOOD_COVERAGE = 0.70         # the calendar holds at least this share of the stated week: confidence good
FAIR_COVERAGE = 0.40
OVER_TOLERANCE_HOURS = 1.0   # rows may exceed the stated week by this much before the run stops
HELD_SHARE = 0.5             # a handover held when the activity's weekly hours fell by at least half
SELLING_SLOT_CAP = 3.0       # selling laid into one morning or afternoon, at most this many hours; the rest is shown as free
CAPACITY_SLACK = 0.05        # rounding only: a helper's handovers never run visibly over their spare hours
# Plausibility stops on headline figures (Build Standard section 13): outside these, ask before building.
WEEK_MIN, WEEK_MAX = 10.0, 100.0     # hours worked in a week
SPARE_MAX = 60.0                     # a helper's spare hours a week
FIXED_WORDS = re.compile(r"\b(evenings?|nights?|nightly|overnight|weekends?|after[- ]hours|late)\b", re.I)
# The founder's country, read from their calendar's time zone or a single-country currency, sets paper, date
# order and clock (locale_numbers.locale_defaults). Never from spelling. Unknown: A4, day first, 24-hour, said.
TZ_COUNTRY = {
    "America/New_York": "US", "America/Chicago": "US", "America/Denver": "US", "America/Phoenix": "US",
    "America/Los_Angeles": "US", "America/Anchorage": "US", "Pacific/Honolulu": "US", "America/Detroit": "US",
    "America/Toronto": "CA", "America/Vancouver": "CA", "America/Edmonton": "CA", "America/Halifax": "CA",
    "America/Mexico_City": "MX", "America/Sao_Paulo": "BR", "America/Bogota": "CO", "America/Santiago": "CL",
    "America/Argentina/Buenos_Aires": "AR", "America/Lima": "PE", "Europe/London": "GB", "Europe/Dublin": "IE",
    "Europe/Lisbon": "PT", "Europe/Paris": "FR", "Europe/Berlin": "DE", "Europe/Amsterdam": "NL",
    "Europe/Brussels": "BE", "Europe/Madrid": "ES", "Europe/Rome": "IT", "Europe/Zurich": "CH", "Europe/Vienna": "AT",
    "Europe/Stockholm": "SE", "Europe/Oslo": "NO", "Europe/Copenhagen": "DK", "Europe/Warsaw": "PL",
    "Europe/Prague": "CZ", "Europe/Athens": "GR", "Europe/Helsinki": "FI", "Europe/Istanbul": "TR",
    "Asia/Singapore": "SG", "Asia/Kuala_Lumpur": "MY", "Asia/Hong_Kong": "HK", "Asia/Shanghai": "CN",
    "Asia/Manila": "PH", "Asia/Taipei": "TW", "Asia/Tokyo": "JP", "Asia/Seoul": "KR", "Asia/Jakarta": "ID",
    "Asia/Bangkok": "TH", "Asia/Ho_Chi_Minh": "VN", "Asia/Kolkata": "IN", "Asia/Calcutta": "IN", "Asia/Dubai": "AE",
    "Asia/Riyadh": "SA", "Asia/Karachi": "PK", "Asia/Dhaka": "BD", "Asia/Jerusalem": "IL", "Africa/Johannesburg": "ZA",
    "Africa/Lagos": "NG", "Africa/Nairobi": "KE", "Africa/Cairo": "EG", "Pacific/Auckland": "NZ",
}
CURRENCY_COUNTRY = {"JPY": "JP", "SGD": "SG", "INR": "IN", "AUD": "AU", "NZD": "NZ", "GBP": "GB", "MYR": "MY",
                    "PHP": "PH", "HKD": "HK", "ZAR": "ZA", "AED": "AE", "CHF": "CH", "CAD": "CA", "KRW": "KR",
                    "THB": "TH", "CNY": "CN", "NGN": "NG", "KES": "KE", "BRL": "BR", "MXN": "MX"}
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

CAT = {"1": 1, "only you": 1, "only-you": 1, "only me": 1, "only": 1, "founder": 1, "you": 1,
       "2": 2, "with instruction": 2, "someone with instruction": 2, "instruction": 2, "delegable": 2,
       "someone else": 2, "could hand over": 2,
       "3": 3, "nobody": 3, "nobody should": 3, "no one": 3, "none": 3, "delete": 3, "nobody should be doing": 3}
CAT_LABEL = {1: "Only you", 2: "With instruction", 3: "Nobody should"}
FUNC = {"strategy": "strategy", "planning": "strategy", "thinking": "strategy", "direction": "strategy",
        "selling": "selling", "sales": "selling", "sell": "selling", "marketing": "selling", "business development": "selling",
        "managing": "managing", "management": "managing", "team": "managing", "people": "managing",
        "delivery": "delivery", "doing": "delivery", "client work": "delivery", "production": "delivery", "fulfilment": "delivery",
        "admin": "admin", "administration": "admin", "finance admin": "admin", "operations": "admin"}
FUNC_LABEL = {"strategy": "Strategy", "selling": "Selling", "managing": "Managing", "delivery": "Delivery", "admin": "Admin"}
ACTIONS = {"delete": "delete", "stop": "delete", "drop": "delete", "delegate": "delegate", "hand over": "delegate",
           "handover": "delegate", "automate": "automate", "keep": "keep"}
CHALLENGE = re.compile(r"\b(invoice|invoicing|admin|e-?mails?|inbox|expenses|bookkeeping|payroll|schedul\w*|diary|"
                       r"reports?|reporting|timesheets?|filing|data entry|booking|status|minutes|chasing|paperwork|"
                       r"formatting|receipts|certs?|certificates)\b", re.I)


class Stop(Exception):
    pass


def norm_key(v, table, what, row):
    if v is None or str(v).strip() == "":
        return None
    k = str(v).strip().lower()
    if k in table:
        return table[k]
    raise Stop(f"row '{row}': {what} '{v}' is not one I know ({', '.join(sorted(set(str(x) for x in table.values())))})")


def r1(x):
    return round(x + 1e-9, 1)


def load(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise Stop(f"there is no file at {path}")
    except json.JSONDecodeError as e:
        raise Stop(f"{path} is not valid JSON ({e.msg}, line {e.lineno}); fix it and run again")


def founder_strings(a):
    """Every value the founder typed, for detecting their decimal style and where they put the currency mark."""
    out = [a.get("stated_week_hours"), a.get("monthly_revenue"), a.get("rate"), a.get("untracked_week_hours")]
    for t in a.get("team") or []:
        if isinstance(t, dict):
            out += [t.get("cost_hour"), t.get("spare_week")]
    for r in list(a.get("activities") or []) + list(a.get("repeats_outside_window") or []):
        if isinstance(r, dict):
            out += [r.get("hours_each"), r.get("per_month"), r.get("times")]
    return [x for x in out if isinstance(x, str)]


def build(a, previous=None):
    if not isinstance(a, dict):
        raise Stop("the audit file should be one JSON object with an 'activities' list")
    rows_in = a.get("activities")
    if not isinstance(rows_in, list):
        raise Stop("the audit file has no 'activities' list")
    rows_in = list(rows_in) + [r for r in (a.get("repeats_outside_window") or []) if isinstance(r, dict) and r.get("include", True)]
    if not rows_in:
        raise Stop("there are no activities to audit; parse a calendar or type the week first")
    notes, needs, problems = [], [], []
    unread = []          # every value the scripts could not read, asked together in one message
    confirmed = {str(x).strip().lower() for x in (a.get("confirmed") or [])}
    loc_in = a.get("locale") or {}
    typed = founder_strings(a)
    decimal = loc_in.get("decimal") if loc_in.get("decimal") in ("dot", "comma") else timeparse.detect_style(typed)
    timeparse.DECIMAL = decimal
    sym_after = bool(loc_in.get("symbol_after")) if "symbol_after" in loc_in else timeparse.symbol_after(typed)

    def read(fn, value, *args):
        """Read one founder value; on failure, keep the question and carry on so every question is asked at once."""
        try:
            return fn(value, *args)
        except AmbiguousInput as e:
            unread.append(f"{e} (it reads two ways; ask which)")
        except InputError as e:
            unread.append(str(e))
        return None, None

    period = a.get("period") or {}
    weeks = float(period.get("weeks") or 1)
    source = (a.get("source") or "calendar").lower()
    pattern = work_pattern(a, period)
    work_days = len(pattern["days"]) if pattern["days"] else timeparse.WORK_DAYS_PER_WEEK
    if pattern["day_hours"]:
        timeparse.DAY_HOURS = pattern["day_hours"]
    if not pattern["known"]:
        needs.append("NEED: the founder's usual working days and hours; the proposed week is laid out on "
                     f"{len(pattern['day_names'])} days of {timeparse.DAY_HOURS:g} hours until they say")
    currency, sym = money_style(a)
    loc = locale_of(a, currency)
    if loc.get("assumed"):
        notes.append("paper, date order and clock are A4, day first and 24-hour because your country is not known; "
                     "say where you work to change them")

    rows = []
    excluded_window = 0.0
    for i, r in enumerate(rows_in, 1):
        if not isinstance(r, dict):
            raise Stop(f"activity {i} is not an object")
        name = str(r.get("activity") or "").strip()
        if not name:
            raise Stop(f"activity {i} has no name")
        cat_raw = str(r.get("category") or "").strip().lower()
        if cat_raw in ("personal", "not work") or r.get("include") is False:
            excluded_window += float(r.get("window_hours") or 0)
            continue
        he, n1 = read(parse_hours, r.get("hours_each"), f"hours each for '{name}'")
        if r.get("per_month") is None and r.get("times") is not None:
            pm, n2 = read(parse_per_month, f"{r.get('times')} a {r.get('per') or 'week'}", work_days, f"how often for '{name}'")
        else:
            pm, n2 = read(parse_per_month, r.get("per_month"), work_days, f"how often for '{name}'")
        if he is None or pm is None:
            if r.get("hours_each") in (None, "") or (r.get("per_month") in (None, "") and r.get("times") is None):
                problems.append(f"'{name}' needs hours each and how often")
            continue
        for nt in (n1, n2):
            if nt:
                notes.append(f"{name}: {nt}")
        if he > 14:
            notes.append(f"{name}: {r1(he)} hours each is long for one sitting; check it is not a weekly total")
        try:
            cat = norm_key(r.get("category"), CAT, "category", name)
            fn = norm_key(r.get("function"), FUNC, "function", name)
            act = norm_key(r.get("action"), ACTIONS, "action", name)
        except Stop as e:
            problems.append(str(e))
            continue
        if cat is None:
            problems.append(f"'{name}' has no category")
        if fn is None:
            problems.append(f"'{name}' has no function (strategy, selling, managing, delivery or admin)")
        if act is None:
            act = {1: "keep", 3: "delete"}.get(cat)
            if act is None:
                problems.append(f"'{name}' has no action")
        if cat == 1 and act not in ("keep", None):
            problems.append(f"'{name}' is only-you but marked {act}; only-you work is kept. Change the category or the action")
        if cat == 3 and act not in ("delete", None):
            problems.append(f"'{name}' is nobody-should but marked {act}; if it has to happen, it is category 2")
        if cat == 2 and act == "keep" and not str(r.get("reason") or "").strip():
            problems.append(f"'{name}' could be handed over but is kept; give the reason (for example nobody to take it yet)")
        if cat == 2 and act == "delete":
            problems.append(f"'{name}' is marked delete; work nobody should do is category 3")
        prot = bool(r.get("protected")) or any(
            p and (p.lower() in name.lower() or name.lower() in p.lower()) for p in (a.get("protected") or []) if isinstance(p, str))
        if prot and cat not in (1, None):
            problems.append(f"'{name}' is work the founder said stays with them, but it is category {cat}. Ask, or mark it only-you")
        src = (r.get("source") or source or "calendar").lower()
        conf = "low" if src in ("recall", "estimate", "told me") else "good"
        monthly = he * pm
        fixed = r.get("fixed")
        if fixed is None:  # work the founder does at set times outside the day (evening calls, nightly email) stays as now
            fixed = (bool(FIXED_WORDS.search(name)) or outside_day(r.get("hours_each"), pattern)
                     or off_days_only(r.get("per_month"), pattern))
        rows.append({
            "activity": name, "source": src, "confidence": conf, "hours_each": he, "per_month": pm,
            "per_month_basis": r.get("per_month_basis") or "", "monthly_hours": monthly,
            "weekly_hours": monthly / WEEKS_PER_MONTH, "window_hours": float(r.get("window_hours") or 0),
            "category": cat, "category_label": CAT_LABEL.get(cat, ""), "function": fn,
            "function_label": FUNC_LABEL.get(fn, ""), "action": act, "who": str(r.get("who") or "").strip(),
            "reason": str(r.get("reason") or "").strip(), "protected": prot, "fixed": bool(fixed),
            "challenge": bool(cat == 1 and (fn == "admin" or CHALLENGE.search(name))),
            "challenge_answer": str(r.get("challenge_answer") or "").strip(),
            "entries": int(r.get("entries") or 0),
            "days_named": named_days(r.get("per_month"), pattern),
        })

    # ---- the founder's figures: every unreadable one is collected, then asked together
    stated, stated_note = read(parse_week_hours, a.get("stated_week_hours"), "hours worked a week", work_days)
    rate_stated, rn = read(hourly_amount, a.get("rate"), "your hourly rate")
    rev_month, mn = read(monthly_amount, a.get("monthly_revenue"), "monthly sales")
    team = a.get("team") or []
    if not isinstance(team, list):
        raise Stop("'team' should be a list of people, each with a name")
    for t in team:
        if not isinstance(t, dict) or not t.get("name"):
            continue
        if t.get("cost_hour") not in (None, ""):
            t["cost_hour_value"] = read(hourly_amount, t["cost_hour"], f"{t['name']}'s cost an hour")[0]
        if t.get("spare_week") not in (None, ""):
            t["spare_week_value"] = (0.0 if str(t["spare_week"]).strip() in ("0", "0.0", "none", "full", "nothing")
                                     else read(parse_week_hours, t["spare_week"], f"{t['name']}'s spare hours a week")[0])
    if unread and stated is not None and not (WEEK_MIN <= stated <= WEEK_MAX) and "week" not in confirmed:
        unread.append(f"I read the hours you work in a week as {r1(stated)} (from '{a.get('stated_week_hours')}'); is that right?")
    if unread:
        raise Stop("these values could not be read; ask the founder about all of them in one message, then pass the "
                   "answers as they give them: " + "; ".join(f"({k}) {u}" for k, u in enumerate(unread, 1)))
    if problems:
        raise Stop("fix these rows first: " + "; ".join(problems))
    if not rows:
        raise Stop("every row is personal or excluded, so there is no work to audit")

    # ---- the week
    cal_hours = float(a.get("calendar_hours") or 0)
    cal_week = float(a.get("calendar_week_hours") or (cal_hours / weeks if weeks else 0))
    cal_rows_window = sum(x["window_hours"] for x in rows if x["source"] in ("calendar", "tracked")) + excluded_window
    if source in ("calendar", "tracked", "calendar+recall") and cal_hours and abs(cal_rows_window - cal_hours) > 0.05:
        raise Stop(f"the calendar rows hold {r1(cal_rows_window)} hours but the calendar counted {r1(cal_hours)}; "
                   "a calendar row was dropped or edited. Re-run parse_calendar.py rather than editing hours by hand")
    if excluded_window and weeks:
        cal_week = max(0.0, cal_week - excluded_window / weeks)
    placed = sum(x["weekly_hours"] for x in rows)
    if stated_note:
        notes.append(stated_note)
    allowance = a.get("untracked_allowance")
    untracked_hours = a.get("untracked_week_hours")
    if stated is not None:
        week, week_src = stated, "what you told me"
    elif untracked_hours not in (None, "") and cal_week:
        week = cal_week + float(untracked_hours)
        week_src = f"your calendar plus the {r1(float(untracked_hours))} hours a week it missed last time"
    elif cal_week and source != "recall":
        al = float(allowance) if allowance not in (None, "") else UNTRACKED_DEFAULT
        week = cal_week * (1 + al)
        week_src = f"default: your calendar plus {round(al * 100)}% for email and admin it does not show"
        needs.append("NEED: roughly how many hours you worked in a typical week; the audit used your calendar plus "
                     f"{round(al * 100)}%")
    else:
        week, week_src = placed, "the activities you described"
    if placed > week + OVER_TOLERANCE_HOURS and placed > week * 1.02:
        raise Stop(f"the activities add up to {r1(placed)} hours a week, but the week is {r1(week)} ({week_src}). "
                   "Ask the founder which is right: a longer week, or a row counted twice")
    not_placed = max(0.0, week - placed)
    if not_placed < 0.25:
        not_placed = 0.0
    if not_placed:
        notes.append(f"{r1(not_placed)} hours a week are not placed in any activity")

    # ---- confidence
    if source == "recall" or (source not in ("tracked",) and not cal_week):
        confidence, conf_why = "low", "from what you remembered, not a calendar or a tracked week; recall flatters, so treat the figures as a first pass"
    elif source == "tracked":
        confidence, conf_why = "good", "from a week you tracked as you went"
    else:
        cov = cal_week / week if week else 0
        if cov >= GOOD_COVERAGE:
            confidence, conf_why = "good", f"your calendar holds {round(cov * 100)}% of the week"
        elif cov >= FAIR_COVERAGE:
            confidence, conf_why = "fair", f"your calendar holds {round(cov * 100)}% of the week; the rest is from what you told me"
        else:
            confidence, conf_why = "low", f"your calendar holds only {round(cov * 100)}% of the week; the rest is from memory"

    # ---- rates
    for nt in (rn, mn):
        if nt:
            notes.append(nt)
    rate_rev = rev_month / (week * WEEKS_PER_MONTH) if rev_month and week else None
    if rate_stated:
        rate_used, rate_label = rate_stated, "the rate you gave"
    elif rate_rev:
        rate_used, rate_label = rate_rev, "your monthly sales divided by your hours"
    else:
        rate_used, rate_label = None, None
        needs.append("NEED: what an hour of your time is worth, or roughly what the business bills a month, to put a value on the hours")

    # ---- plausibility: a headline figure that cannot be right stops the run with a plain question
    money_s = lambda x: fmt_money(x, sym, decimal, sym_after)  # noqa: E731
    implausible = []
    if not (WEEK_MIN <= week <= WEEK_MAX) and "week" not in confirmed:
        implausible.append(f"I read the hours you work in a week as {r1(stated)} (from '{a.get('stated_week_hours')}'); is that right?"
                           if stated is not None else
                           f"the week comes out at {r1(week)} hours ({week_src}); roughly how many hours do you work in a week?")
    helpers = [(t["name"], t["cost_hour_value"]) for t in team if isinstance(t, dict) and t.get("cost_hour_value")]
    for nm, c in helpers:
        if c < 1 and nm.lower() not in confirmed:
            implausible.append(f"I read {nm}'s cost as {money_s(c)} an hour (from '{next(t['cost_hour'] for t in team if t.get('name') == nm)}'); is that right?")
    for t in team:
        if isinstance(t, dict) and (t.get("spare_week_value") or 0) > SPARE_MAX and str(t.get("name", "")).lower() not in confirmed:
            implausible.append(f"I read {t['name']}'s spare time as {r1(t['spare_week_value'])} hours a week (from '{t['spare_week']}'); is that right?")
    if rate_used is not None and "rate" not in confirmed:
        top = max(helpers, key=lambda h: h[1]) if helpers else None
        basis = (f"your hourly rate as {money_s(rate_stated)} (from '{a.get('rate')}')" if rate_stated else
                 f"your monthly sales as {money_s(rev_month)} (from '{a.get('monthly_revenue')}')")
        if rate_used < 1:
            implausible.append(f"an hour of your time comes out at {money_s(rate_used) if rate_used >= 0.5 else 'under ' + money_s(1)}. "
                               f"I read {basis}; is that right?")
        elif top and rate_used < top[1]:
            implausible.append(f"an hour of your time comes out at {money_s(rate_used)}, below the {money_s(top[1])} an hour "
                               f"{top[0]} costs. I read {basis}; is that right?")
    if implausible:
        raise Stop("before building, check these figures with the founder in one message: "
                   + " ".join(f"({k}) {q}" for k, q in enumerate(implausible, 1))
                   + " If a figure is right as read, add its name to \"confirmed\" in the audit file (\"rate\", \"week\" "
                     "or the helper's name); if not, pass the corrected figure as they say it")

    for x in rows:
        x["share"] = x["weekly_hours"] / week if week else 0

    # ---- the order: by hours a month, unless the founder named an order ("Ana's work first"); theirs wins,
    # and the hours stay on show so they can see what the hours alone would say
    forder = [str(n).strip().lower() for n in (a.get("founder_order") or []) if str(n).strip()]
    known = {x["activity"].lower() for x in rows}
    unknown_order = [n for n in forder if n not in known]
    if unknown_order:
        raise Stop("founder_order names activities that are not rows: " + ", ".join(unknown_order)
                   + ". Use the activity labels exactly as in the audit file")

    def order_key(x):
        nm = x["activity"].lower()
        return (forder.index(nm) if nm in forder else len(forder), -x["monthly_hours"])

    # ---- helpers' capacity: handovers to one person are taken in rank order; one that does not fit waits (stated)
    capacity = []
    for t in team:
        if not isinstance(t, dict) or not t.get("name") or t.get("spare_week_value") is None:
            continue
        sp = t["spare_week_value"]
        nm = str(t["name"]).lower()
        mine = sorted([x for x in rows if x["action"] == "delegate" and re.search(r"\b" + re.escape(nm) + r"\b", x["who"].lower())],
                      key=order_key)
        used, waiting = 0.0, []
        for x in mine:
            if used + x["weekly_hours"] <= sp + CAPACITY_SLACK or a.get("capacity_waits") is False:
                used += x["weekly_hours"]
            else:
                x["action"] = "keep"
                x["reason"] = f"waits until {t['name']} has room"
                x["waits_for"] = t["name"]
                waiting.append(x["activity"])
        capacity.append({"name": t["name"], "spare_week": sp, "assigned_week": used,
                         "rows": [x["activity"] for x in mine if x["activity"] not in waiting], "waiting": waiting})
        if waiting:
            notes.append(f"{', '.join(waiting)} wait{'s' if len(waiting) == 1 else ''} until {t['name']} has room: "
                         f"{t['name']} has {r1(sp)} spare hours a week and the handovers ranked above use {r1(used)}")
        if used > sp + CAPACITY_SLACK:
            needs.append(f"NEED: {t['name']} has {r1(sp)} spare hours a week but the handovers to {t['name']} need {r1(used)}. "
                         "Ask which waits, or whether their hours can grow")

    def helper_cost(who):
        if not who:
            return None
        for t in team:
            if isinstance(t, dict) and t.get("name") and str(t["name"]).lower() in who.lower() and t.get("cost_hour_value") is not None:
                return t["cost_hour_value"]
        return None

    for x in rows:
        x["value_month"] = x["monthly_hours"] * rate_used if rate_used and x["action"] in ("delete", "delegate", "automate") else None
        hc = helper_cost(x["who"]) if x["action"] == "delegate" else None
        x["helper_rate"] = hc
        x["helper_cost_month"] = x["monthly_hours"] * hc if hc is not None else None
        x["helper_cost_week"] = x["weekly_hours"] * hc if hc is not None else None

    # ---- each helper: what their handovers cost a week, and the share of the freed hours that must earn the
    # founder's rate for the help to pay for itself (helper's hourly cost over the founder's hourly value)
    for cap in capacity:
        hc = helper_cost(cap["name"])
        cap["cost_hour"] = hc
        cap["cost_week"] = cap["assigned_week"] * hc if hc is not None else None
        cap["break_even_share"] = hc / rate_used if hc is not None and rate_used else None

    # ---- totals
    cats = {}
    for c in (1, 2, 3):
        h = sum(x["weekly_hours"] for x in rows if x["category"] == c)
        cats[c] = {"label": CAT_LABEL[c], "week": h, "share": h / week if week else 0}
    cats["not_placed"] = {"label": "Not placed", "week": not_placed, "share": not_placed / week if week else 0}
    funcs = {}
    for f in FUNC_LABEL:
        h = sum(x["weekly_hours"] for x in rows if x["function"] == f)
        funcs[f] = {"label": FUNC_LABEL[f], "week": h, "share": h / week if week else 0}
    doing = funcs["delivery"]["week"] + funcs["admin"]["week"]
    funcs["doing"] = {"label": "Doing (delivery and admin)", "week": doing, "share": doing / week if week else 0}
    flags = []
    if funcs["doing"]["share"] > DOING_FLAG:
        flags.append({"code": "doing_high", "share": funcs["doing"]["share"]})
    if funcs["strategy"]["share"] < STRATEGY_FLAG:
        flags.append({"code": "strategy_low", "share": funcs["strategy"]["share"]})

    deletions = sorted([x for x in rows if x["action"] == "delete"], key=lambda x: -x["monthly_hours"])
    handovers = sorted([x for x in rows if x["action"] in ("delegate", "automate")], key=order_key)
    by_hours = [x["activity"] for x in sorted(handovers, key=lambda x: -x["monthly_hours"])]
    order = {"source": "founder" if forder and [x["activity"] for x in handovers] != by_hours else "hours",
             "by_hours": by_hours}
    kept2 = sorted([x for x in rows if x["category"] == 2 and x["action"] == "keep"], key=lambda x: -x["monthly_hours"])
    for i, x in enumerate(handovers, 1):
        x["rank"] = i
    for i, x in enumerate(deletions, 1):
        x["delete_rank"] = i
    del_m = sum(x["monthly_hours"] for x in deletions)
    hand_m = sum(x["monthly_hours"] for x in handovers)
    top5_m = sum(x["monthly_hours"] for x in handovers[:5])
    helper_known = [x for x in handovers[:5] if x["action"] == "delegate" and x["helper_cost_month"] is not None]
    reclaimed = {
        "delete_month": del_m, "handover_month": hand_m, "total_month": del_m + hand_m,
        "total_week": (del_m + hand_m) / WEEKS_PER_MONTH, "first_five_month": del_m + top5_m,
        "first_five_week": (del_m + top5_m) / WEEKS_PER_MONTH,
        "value_month": (del_m + top5_m) * rate_used if rate_used else None,
        "value_all_month": (del_m + hand_m) * rate_used if rate_used else None,
        "helper_cost_month": sum(x["helper_cost_month"] for x in helper_known) if helper_known else None,
        "helper_cost_rows": len(helper_known),
        "helper_cost_week": sum(x["helper_cost_week"] for x in helper_known) if helper_known else None,
        "value_week": (del_m + top5_m) / WEEKS_PER_MONTH * rate_used if rate_used else None,
        "delegate_rows_top5": len([x for x in handovers[:5] if x["action"] == "delegate"]),
        "automate_rows_top5": len([x for x in handovers[:5] if x["action"] == "automate"]),
    }
    to_find = [x for x in handovers if x["action"] == "delegate" and (not x["who"] or re.search(r"\b(to find|nobody yet|a va|a contractor|freelancer|someone)\b", x["who"], re.I))]
    role = {"week": sum(x["weekly_hours"] for x in to_find), "rows": [x["activity"] for x in to_find]}

    challenges_open = [x["activity"] for x in rows if x["challenge"] and not x["challenge_answer"]]
    for nm in challenges_open:
        needs.append(f"CHALLENGE: '{nm}' is marked only-you but reads as admin, reporting or scheduling. Ask the founder once "
                     "why it must be them, and record the answer in challenge_answer")

    # ---- the plan and the proposed week
    removed = {f: sum(x["weekly_hours"] for x in rows if x["function"] == f and x["action"] in ("delete", "delegate", "automate"))
               for f in FUNC_LABEL}
    planned = {f: funcs[f]["week"] - removed[f] for f in FUNC_LABEL}
    freed = sum(removed.values())
    strat_target = planned["strategy"]
    if funcs["strategy"]["share"] < STRATEGY_FLAG:
        strat_target = max(planned["strategy"], STRATEGY_BLOCK_HOURS)
    extra_strat = strat_target - planned["strategy"]
    planned["strategy"] = strat_target
    available = freed - extra_strat
    freed_to = str(a.get("freed_to") or "selling").lower()
    if freed_to not in ("selling", "strategy", "fewer hours", "delivery"):
        freed_to = "selling"
    planned_week = week - freed + extra_strat
    if available > 0:
        if freed_to == "fewer hours":
            pass
        else:
            planned[freed_to] += available
            planned_week += available
    elif available < 0:
        notes.append(f"the strategy block needs {r1(extra_strat)} hours and the changes free {r1(freed)}, "
                     f"so the week runs {r1(-available)} hours longer until the next handover lands")
    planned_doing = planned["delivery"] + planned["admin"]
    plan = {"by_function": planned, "week": planned_week, "not_placed": not_placed, "freed_week": freed,
            "strategy_added": extra_strat, "freed_to": freed_to, "available": available,
            "doing_share": planned_doing / planned_week if planned_week else 0,
            "strategy_share": planned["strategy"] / planned_week if planned_week else 0,
            "strategy_15_hours": STRATEGY_FLAG * planned_week}
    as_now = [(x["activity"], x["weekly_hours"], x["function"]) for x in rows if x["fixed"] and x["action"] == "keep"]
    layout = dict(planned)
    for _n, h, f in as_now:
        layout[f] = max(0.0, layout[f] - h)
    pinned = []  # kept work the founder said happens on named days goes on those days ("every saturday", "mon to fri")
    for x in rows:
        if x["action"] == "keep" and not x["fixed"] and x["days_named"]:
            for d in x["days_named"]:
                pinned.append((x["function"], d, x["weekly_hours"] / len(x["days_named"])))
    proposed = lay_out_week(layout, pattern, twelve=loc.get("clock") == "12",
                            freed_selling=available if freed_to == "selling" and available > 0 else 0.0, pinned=pinned)
    proposed["as_now"] = [{"activity": n, "week": h} for n, h, _f in as_now]
    proposed["not_placed"] = not_placed

    out = {
        "skill": SKILL, "business": a.get("business") or "Your business", "date": a.get("date") or date.today().isoformat(),
        "currency": currency, "symbol": sym, "locale": loc, "number_style": {"decimal": decimal, "symbol_after": sym_after},
        "work_pattern": pattern, "source": source, "confidence": confidence, "confidence_why": conf_why,
        "period": period, "weeks": weeks,
        "week": {"hours": week, "source": week_src, "calendar_week": cal_week, "calendar_hours": cal_hours,
                 "placed": placed, "not_placed": not_placed,
                 "untracked": max(0.0, week - cal_week) if cal_week else None},
        "left_out": a.get("left_out") or {}, "personal_hours": a.get("personal_hours") or 0,
        "personal_count": a.get("personal_count") or 0, "overlap_hours": a.get("overlap_hours") or 0,
        "rows": rows, "categories": {str(k): v for k, v in cats.items()}, "functions": funcs, "flags": flags,
        "deletions": [x["activity"] for x in deletions], "handovers": [x["activity"] for x in handovers],
        "order": order,
        "kept_category_two": [x["activity"] for x in kept2],
        "kept_category_two_week": sum(x["weekly_hours"] for x in kept2),
        "reclaimed": reclaimed,
        "rates": {"stated": rate_stated, "revenue_based": rate_rev, "monthly_revenue": rev_month, "used": rate_used,
                  "used_label": rate_label, "hours_month": week * WEEKS_PER_MONTH,
                  "helper_max": max((h[1] for h in helpers), default=None)},
        "confirmed": sorted(confirmed),
        "role_shape": role, "capacity": capacity, "plan": plan, "proposed_week": proposed,
        "team": team, "protected": a.get("protected") or [],
        "challenges_open": challenges_open, "needs": needs, "notes": notes + list(a.get("notes") or []),
        "thresholds": {"doing": DOING_FLAG, "strategy": STRATEGY_FLAG, "block": STRATEGY_BLOCK_HOURS},
    }
    if previous:
        out["previous"] = compare(previous, out)
    return out


def outside_day(hours_each, pattern):
    """True when the founder's own words put the work at a clock time outside their working day ('9pm to 10:30')."""
    if not isinstance(hours_each, str) or not pattern.get("known"):
        return False
    if not re.search(r"\d\s*(am|pm|a\.m\.|p\.m\.)|\d:\d\d|\b(1[3-9]|2[0-3])\b", hours_each.lower()):
        return False  # "2-3 hours" is a length, not a time of day
    m = re.search(r"(\d{1,2}(?:[:.]\d{2})?\s*(?:am|pm)?)\s*(?:-|to|until|till)\s*(\d{1,2}(?:[:.]\d{2})?\s*(?:am|pm)?)", hours_each.lower())
    if not m:
        return False
    span = parse_hours_span(f"{m.group(1)}-{m.group(2)}")
    if not span:
        return False
    return span[0] >= pattern["end"] or span[1] <= pattern["start"]


def named_days(per_month, pattern):
    """The working days a row's own words name ('every saturday', 'mon to fri'), as day names, when they are a
    subset of the founder's working days; otherwise an empty list."""
    if not isinstance(per_month, str) or not pattern.get("known") or not pattern.get("days"):
        return []
    _n, names = timeparse._days_in(per_month.lower())
    days = [d for a3 in names for d in pattern["days"] if d[:3].lower() == a3]
    return days if days and len(days) == len(names) and len(days) < len(pattern["days"]) + 1 else []


def off_days_only(per_month, pattern):
    """True when the founder's words name only days outside their working week ('every saturday' for Mon to Fri)."""
    if not isinstance(per_month, str) or not pattern.get("known") or not pattern.get("days"):
        return False
    _n, names = timeparse._days_in(per_month.lower())
    work = {d[:3].lower() for d in pattern["days"]}
    return bool(names) and not (set(names) & work)


def _clock_h(text):
    m = re.fullmatch(r"(\d{1,2})(?:[:.](\d{2}))?\s*(am|pm)?", text.strip().lower())
    if not m:
        return None, None
    h = int(m.group(1)) + int(m.group(2) or 0) / 60
    if m.group(3) == "pm" and h < 12:
        h += 12
    if m.group(3) == "am" and h >= 12:
        h -= 12
    return h, m.group(3)


def parse_hours_span(text):
    """'8:30-17:30', '9-6', '8am-5pm', '9 to 5:30' -> (start, end) in hours, or None."""
    if not text:
        return None
    t = re.sub(r"\b(about|around|roughly|usually|normally|ish|or so|till|til)\b|ish\b|~", lambda m: " to " if m.group(0) in ("till", "til") else " ",
               str(text).strip().lower().replace("\u2013", "-"))
    parts = [x for x in re.split(r"\s*(?:-|\bto\b|until)\s*", re.sub(r"\s+", " ", t).strip()) if x.strip()]
    if len(parts) != 2:
        return None
    (a, ap), (b, bp) = _clock_h(parts[0]), _clock_h(parts[1])
    if a is None or b is None:
        return None
    if bp is None and b <= a and b + 12 <= 24:
        b += 12
    return (a, b) if b > a else None


def parse_day_names(v):
    if not v:
        return []
    if isinstance(v, list):
        out = []
        for x in v:
            k = str(x).strip()[:3].lower()
            out += [d for d in DAY_NAMES if d[:3].lower() == k]
        return out
    t = str(v).strip().lower()
    idx = {d[:3].lower(): i for i, d in enumerate(DAY_NAMES)}
    m = re.fullmatch(r"([a-z]{3})[a-z]*\s*(?:-|to)\s*([a-z]{3})[a-z]*", t)
    if m and m.group(1) in idx and m.group(2) in idx:
        a, b = idx[m.group(1)], idx[m.group(2)]
        return [DAY_NAMES[(a + k) % 7] for k in range((b - a) % 7 + 1)]
    return [DAY_NAMES[idx[x[:3]]] for x in re.split(r"[,/\s]+|\band\b", t) if x[:3] in idx]


def split_day(start, end):
    """Morning and afternoon of a working day, with an hour's break when the day runs through 13:00. A day that
    ends by 13:00 is all morning; one that starts at 13:00 or later is all afternoon."""
    if end <= 13:
        return end, max(0.0, end - start), 0.0
    if start >= 13:
        return start, 0.0, max(0.0, end - start)
    return 13.0, 13.0 - start, max(0.0, end - 14.0)


def work_pattern(a, period):
    """The founder's working days and hours: what they said in the audit file, else what the parser read from
    their calendar. Hours may differ by day ({"mon-fri": "7:30-19:00", "sat": "7:30-12:30"}). Nothing is
    assumed: unknown is reported as unknown."""
    names = parse_day_names(a.get("work_days")) if not isinstance(a.get("work_days"), (int, float)) else []
    src = "founder" if names else None
    wh = a.get("work_hours")
    per_day, span, hsrc = {}, None, None
    if isinstance(wh, dict):
        for k, v in wh.items():
            sp = parse_hours_span(v)
            if not sp:
                continue
            if str(k).strip().lower() in ("default", "usual", "other days", "rest", "all", "weekdays", "most days"):
                span = sp
            else:
                for d in parse_day_names(k):
                    per_day[d] = sp
        if span is None and per_day:
            vals = list(per_day.values())
            span = max(set(vals), key=vals.count)
        hsrc = "founder" if span else None
        if not names and per_day:
            names = [d for d in DAY_NAMES if d in per_day]
            src = "founder"
    else:
        span = parse_hours_span(wh)
        hsrc = "founder" if span else None
    if not names:
        names = parse_day_names(period.get("work_day_names"))
        src = period.get("work_pattern_source") if names else None
    count = a.get("work_days") if isinstance(a.get("work_days"), (int, float)) else period.get("work_days")
    if not names and isinstance(count, (int, float)) and count:
        names = [f"Day {i + 1}" for i in range(int(count))]
        src = src or "founder"
    if not span:
        span = parse_hours_span(period.get("work_hours"))
        hsrc = period.get("work_pattern_source") if span else None
    known = bool(names) and bool(span)
    if not known:
        names = names or [f"Day {i + 1}" for i in range(5)]
        return {"known": False, "days": names if names[0] != "Day 1" else [], "day_names": names, "start": None,
                "end": None, "day_hours": None, "source": "unknown", "spans": {}}
    _l, am, pm = split_day(*span)
    spans = {d: per_day.get(d, span) for d in names}
    return {"known": True, "days": names, "day_names": names, "start": span[0], "end": span[1],
            "day_hours": am + pm, "source": hsrc or src, "spans": spans,
            "own_hours": {d: list(spans[d]) for d in names if spans[d] != span}}


def money_style(a):
    """Currency follows the founder: the code they gave, else the mark on the figures they typed."""
    code = str(a.get("currency") or "").strip().upper() or None
    sym = a.get("symbol")
    if code and not sym:
        sym = SYMBOL_FOR.get(code, code + " ")
    if not code and not sym:
        figs = [a.get("rate"), a.get("monthly_revenue")] + [t.get("cost_hour") for t in (a.get("team") or [])
                                                             if isinstance(t, dict)]
        for f in figs:
            c, s_ = currency_of(f)
            if c or s_:
                code = code or c
                sym = sym or s_
                break
    if code and not sym:
        sym = SYMBOL_FOR.get(code, code + " ")
    return code, sym or ""


def locale_of(a, currency=None):
    """Paper, date order and clock follow the founder's country (locale_numbers.locale_defaults), never their
    spelling. The country is the one Claude recorded from what the founder said, else the one their calendar's
    time zone sits in, else the one country that uses their currency. Unknown: A4, day first, 24-hour, said.
    Paper or clock the founder named themselves win."""
    loc = dict(a.get("locale") or {})
    country = str(loc.get("country") or "").strip().upper() or None
    csrc = "founder" if country else None
    if not country:
        tz = str((a.get("period") or {}).get("tz") or a.get("tz") or "")
        country = TZ_COUNTRY.get(tz)
        csrc = "your calendar's time zone" if country else None
    if not country and currency:
        country = CURRENCY_COUNTRY.get(str(currency).upper())
        csrc = "your currency" if country else None
    d = LN.locale_defaults(country or "")
    if country:
        style = "mdy" if d["date_order"] == "MDY" else "dmy"
    else:
        style = loc.get("date_style") or {"mdy": "mdy", "dmy": "dmy"}.get(loc.get("date_order") or "") or "dmy"
    paper = str(loc.get("paper") or d["paper"]).lower()
    clock = str(loc.get("clock") or ("12" if d["clock"] == "12h" else "24")).lower().replace("h", "")
    return {"date_style": style, "spelling": loc.get("spelling"), "paper": paper, "lang": loc.get("lang"), "clock": clock,
            "country": country, "country_source": csrc, "assumed": country is None and not (loc.get("paper") and loc.get("clock"))}


def lay_out_week(planned, pattern, twelve=False, freed_selling=0.0, pinned=()):
    """Place each function's planned hours into mornings and afternoons, in half hours, on the founder's own
    working days and each day's own hours. Hours the founder works at set times outside the day (evening calls)
    are not moved: the caller lists them as kept as now. Time not placed in any activity is not laid out.
    Selling takes at most SELLING_SLOT_CAP hours of any one morning or afternoon; freed hours that do not fit are
    shown as free for selling or fewer hours, never as hours beyond the working day."""
    names = pattern["day_names"]
    if pattern["known"]:
        start, end = pattern["start"], pattern["end"]
        lunch, am_def, pm_def = split_day(start, end)
        caps = {d: split_day(*pattern["spans"][d])[1:] for d in names}
    else:
        start = end = lunch = None
        caps = {d: (timeparse.DAY_HOURS / 2, timeparse.DAY_HOURS / 2) for d in names}
    slots = {(d, s): {"cap": caps[d][0] if s == "morning" else caps[d][1], "items": []} for d in names for s in ("morning", "afternoon")}

    def half(x):
        return round(x * 2) / 2

    want = {f: half(planned.get(f, 0)) for f in ("strategy", "delivery", "selling", "managing", "admin")}
    full = [d for d in names if slots[(d, "afternoon")]["cap"] > 0] or names
    mid = full[1:-1] if len(full) >= 3 else full
    prefer = {
        "strategy": [(d, "morning") for d in names],
        "delivery": [(d, "morning") for d in names],
        "managing": [(full[len(full) // 2], "afternoon")],
        "admin": [(full[-1], "afternoon")],
        "selling": [(d, "afternoon") for d in mid] + [(d, "afternoon") for d in names if d not in mid],
    }
    anyslot = [(d, "afternoon") for d in names] + [(d, "morning") for d in names]
    label = {"strategy": "Strategy (protected)", "delivery": "Delivery", "selling": "Selling", "managing": "Team",
             "admin": "Admin batch"}
    left = dict(want)

    def used(key, f=None):
        return sum(h for l_, h in slots[key]["items"] if f is None or l_ == label[f])

    def free(key, f):
        fr = slots[key]["cap"] - used(key)
        if f == "selling":
            fr = min(fr, SELLING_SLOT_CAP - used(key, "selling"))
        return max(0.0, fr)

    def put(f, key, amount):
        s = slots[key]
        for k, (l_, h) in enumerate(s["items"]):
            if l_ == label[f]:
                s["items"][k] = (l_, h + amount)
                return
        s["items"].append((label[f], amount))

    # pass 0: kept work the founder ties to named days goes on those days, mornings first
    for f, d, h in pinned:
        h = min(half(h) if half(h) > 0 else h, left.get(f, 0))
        for key in ((d, "morning"), (d, "afternoon")):
            if h <= 0 or key not in slots:
                continue
            take = min(h, free(key, f))
            if take > 0:
                put(f, key, take)
                left[f] -= take
                h -= take
    # pass 1: preferred slots; the strategy block stays whole where it fits
    for f in ("strategy", "delivery", "managing", "admin", "selling"):
        for key in prefer[f]:
            if left[f] <= 0:
                break
            fr = free(key, f)
            if f == "strategy" and fr < min(left[f], slots[key]["cap"]):
                continue
            take = min(left[f], fr)
            if take > 0:
                put(f, key, take)
                left[f] -= take
    # pass 2: anything left goes into any open slot, afternoons first
    for f in ("selling", "admin", "managing", "delivery", "strategy"):
        for key in anyslot:
            if left[f] <= 0:
                break
            take = min(left[f], free(key, f))
            if take > 0:
                put(f, key, take)
                left[f] -= take
    # selling that does not fit is free time, for selling or fewer hours, not hours beyond the day
    free_selling = max(0.0, left["selling"])
    left["selling"] = 0.0
    # pass 3: other work beyond the working day, shown honestly as extra hours
    extra = {d: [] for d in names}
    for f in ("delivery", "admin", "managing", "strategy"):
        i = 0
        while left[f] > 0.01:
            d = names[i % len(names)]
            step = min(0.5, left[f])
            got = [k for k, (l_, h) in enumerate(extra[d]) if l_ == label[f]]
            if got:
                extra[d][got[0]] = (label[f], extra[d][got[0]][1] + step)
            else:
                extra[d].append((label[f], step))
            left[f] -= step
            i += 1
    days = []
    own = pattern.get("own_hours") or {}
    for d in names:
        days.append({"day": d,
                     "hours": (f"{fmt_clock(own[d][0], twelve)} to {fmt_clock(own[d][1], twelve)}" if d in own else ""),
                     "morning": sorted([(l_, h) for l_, h in slots[(d, "morning")]["items"] if h > 0], key=lambda t: not t[0].startswith("Strategy")),
                     "afternoon": sorted([(l_, h) for l_, h in slots[(d, "afternoon")]["items"] if h > 0], key=lambda t: not t[0].startswith("Strategy")),
                     "morning_off": slots[(d, "morning")]["cap"] <= 0, "afternoon_off": slots[(d, "afternoon")]["cap"] <= 0,
                     "extra": [(l_, h) for l_, h in extra[d] if h > 0]})
    total_extra = sum(h for d in names for _l, h in extra[d])
    extra_by = {}
    for d in names:
        for l_, h in extra[d]:
            extra_by[l_] = extra_by.get(l_, 0) + h
    return {"days": days, "strategy_block": want["strategy"],
            "morning": f"{fmt_clock(start, twelve)} to {fmt_clock(lunch if lunch > start else end, twelve)}" if start is not None else "",
            "afternoon": (f"{fmt_clock(lunch + (1 if start < 13 < end else 0), twelve)} to {fmt_clock(end, twelve)}"
                          if start is not None and end > 13 else ""),
            "extra_hours": total_extra, "extra_by_label": extra_by, "free_selling": free_selling,
            "capacity": sum(s["cap"] for s in slots.values())}


def fmt_clock(h, twelve=False):
    hh, mm = int(h), int(round((h - int(h)) * 60))
    if mm == 60:
        hh, mm = hh + 1, 0
    if twelve:
        return f"{(hh - 1) % 12 + 1}:{mm:02d} {'AM' if hh < 12 or hh == 24 else 'PM'}"
    return f"{hh:02d}:{mm:02d}"


def compare(prev, cur):
    """What changed since the saved audit, and whether each handover held."""
    pa = prev.get("last_audit") or {}
    out = {"date": pa.get("date") or prev.get("_memory_updated"), "changes": [], "handovers": []}
    pairs = [("Hours a week", pa.get("week_hours"), cur["week"]["hours"], "h"),
             ("Only you", pa.get("only_share"), cur["categories"]["1"]["share"], "%"),
             ("Nobody should", pa.get("nobody_share"), cur["categories"]["3"]["share"], "%"),
             ("Doing", pa.get("doing_share"), cur["functions"]["doing"]["share"], "%"),
             ("Strategy", pa.get("strategy_share"), cur["functions"]["strategy"]["share"], "%")]
    for label, before, now, kind in pairs:
        if before in (None, ""):
            continue
        try:
            b = float(str(before).rstrip("%")) / (100 if str(before).endswith("%") else 1)
        except ValueError:
            continue
        out["changes"].append({"label": label, "before": b, "now": now, "kind": kind})
    cur_by = {x["activity"].lower(): x for x in cur["rows"]}
    for h in prev.get("handovers") or []:
        name = str(h.get("activity", "")).strip()
        if not name:
            continue
        try:
            before = float(h.get("weekly_hours") or 0)
        except ValueError:
            before = 0.0
        now_row = cur_by.get(name.lower())
        now = round(now_row["weekly_hours"], 2) if now_row else 0.0
        if before <= 0:
            status = "no figure saved"
        elif now <= before * (1 - HELD_SHARE) + 0.01:
            status = "held" if now == 0 else "partly held"
        else:
            status = "came back" if (h.get("status") or "").lower() in ("held", "done") else "not moved yet"
        out["handovers"].append({"activity": name, "action": h.get("action", ""), "who": h.get("who", ""),
                                 "before": before, "now": now, "status": status})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("audit")
    ap.add_argument("--out", required=True)
    ap.add_argument("--previous")
    args = ap.parse_args()
    try:
        a = load(args.audit)
        prev = load(args.previous) if args.previous else None
        res = build(a, prev)
    except Stop as e:
        msg = str(e).rstrip()
        print(f"STOP: {msg}{' ' if msg.endswith(('?', '.')) else '. '}Nothing was written.")
        sys.exit(2)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")
    sym = res["symbol"]
    ns = res.get("number_style") or {}
    mon = lambda x: fmt_money(x, sym, ns.get("decimal"), ns.get("symbol_after"))  # noqa: E731
    wk = res["week"]["hours"]
    c = res["categories"]
    print(f"Week: {r1(wk)} hours ({res['week']['source']}). Confidence: {res['confidence']} ({res['confidence_why']}).")
    print(f"Only you {r1(c['1']['week'])} ({round(c['1']['share'] * 100)}%), with instruction {r1(c['2']['week'])} "
          f"({round(c['2']['share'] * 100)}%), nobody should {r1(c['3']['week'])} ({round(c['3']['share'] * 100)}%), "
          f"not placed {r1(c['not_placed']['week'])}.")
    f = res["functions"]
    print("Functions: " + ", ".join(f"{v['label']} {r1(v['week'])} ({round(v['share'] * 100)}%)" for k, v in f.items()))
    for fl in res["flags"]:
        print(f"FLAG: {fl['code']} at {round(fl['share'] * 100)}%")
    rows = {x["activity"]: x for x in res["rows"]}
    for n in res["deletions"]:
        x = rows[n]
        print(f"DELETE: {n}: {r1(x['hours_each'])} x {r1(x['per_month'])} = {r1(x['monthly_hours'])} hours a month")
    for n in res["handovers"]:
        x = rows[n]
        v = f", worth {mon(x['value_month'])}" if x["value_month"] is not None else ""
        print(f"HANDOVER {x['rank']}: {n}: {r1(x['hours_each'])} x {r1(x['per_month'])} = {r1(x['monthly_hours'])} "
              f"hours a month, {x['action']} to {x['who'] or '[who]'}{v}")
    rc = res["reclaimed"]
    print(f"Reclaimed: deletions plus the top five handovers {r1(rc['first_five_month'])} hours a month "
          f"({r1(rc['first_five_week'])} a week)" + (f", worth {mon(rc['value_month'])} at {mon(res['rates']['used'])} an hour"
                                                    if rc["value_month"] is not None else ""))
    for cap in res["capacity"]:
        line = f"HELPER: {cap['name']}: {r1(cap['assigned_week'])} of {r1(cap['spare_week'])} spare hours a week"
        if cap.get("cost_week") is not None:
            line += f", costs {mon(cap['cost_week'])} a week"
        if cap.get("break_even_share") is not None:
            line += f", pays for itself if {round(cap['break_even_share'] * 100)}% of the hours it frees earn your rate"
        if cap.get("waiting"):
            line += f"; waiting: {', '.join(cap['waiting'])}"
        print(line)
    for n in res["notes"]:
        print("NOTE:", n)
    for n in res["needs"]:
        print(n)
    print(f"WROTE: {args.out}")
    sys.exit(1 if res["needs"] else 0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print(f"STOP: the audit could not be worked out ({type(e).__name__}: {e}). Nothing was written.")
        sys.exit(2)
