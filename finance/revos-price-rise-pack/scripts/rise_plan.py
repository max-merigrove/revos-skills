#!/usr/bin/env python3
"""The Price Rise Pack planner: who to raise, by how much, from when, and what it adds to cash.

Usage:
  python3 scripts/rise_plan.py compute <inputs.json> [--results <results.json>]
        works out every figure and prints the plan, the headline and every flag
  python3 scripts/rise_plan.py build <inputs.json> --out <folder> [--results <results.json>] [--csv]
        writes "Price rise plan <today>.xlsx" (live formulas) and "Price rise letters <today>.docx"; a file
        of the same name already there is moved into <folder>/superseded/ first
  add --provisional to compute or build when a client is listed twice with different fees: the higher
        fee is used, that client's letter is HOLD, and a FLAG asks which is current (no STOP)
  python3 scripts/rise_plan.py selfcheck <inputs.json>
        recomputes the break-even by brute force over every subset of the raised clients

Exit codes: 0 clean; 1 built or computed with [NEED] flags or HOLD letters (expected when
something is unknown); 2 STOP (nothing usable: read the STOP line, fix the inputs or ask the
founder the ASK question, and run again). Never show figures from a run that exited 2.

Every fee, date, cash figure, break-even and scenario the founder sees comes from here. The rules
are planning defaults (see references/method.md), not market facts. No tax is computed;
fees are read as entered, before any sales tax. Standard library only, openpyxl when present.
No network calls.
"""
import argparse
import itertools
import json
import math
import os
import re
import statistics
import sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dates as D  # noqa: E402
from locale_numbers import (Ambiguous, Unreadable, detect_decimal_style, find_currency,  # noqa: E402
                            locale_defaults, parse_number, parse_percent)

VERSION = "1.2.0"
SEGMENTS = ["Hold", "Price to keep", "Reset the scope", "At renewal", "Two steps", "Raise now"]
UNIT_MONTHS = {"month": 1, "quarter": 3, "year": 12, "week": 12 / 52}
UNIT_WORDS = {"month": "a month", "quarter": "a quarter", "year": "a year", "project": "a project", "week": "a week"}
REASON_ORDER = ["new_client_price", "scope", "last_change", "cost"]
INJECTION = re.compile(r"(\bany (ai|assistant|llm|model)\b|\bignore (all |any |the )?(previous|prior|above)|"
                       r"\b(chatgpt|claude|gpt|copilot)\b|\bsystem prompt\b|\bto (the )?(ai|assistant)\b|"
                       r"\bset every\b|\byou are now\b)", re.I)
DECIMAL_WORDS = {"dot": "dot", ".": "dot", "point": "dot", "period": "dot", "fullstop": "dot",
                 "comma": "comma", ",": "comma", "komma": "comma", "virgule": "comma", "coma": "comma"}
SYMBOLS = {"GBP": "£", "EUR": "€", "INR": "₹", "USD": "$", "AUD": "$", "CAD": "$", "NZD": "$", "SGD": "S$",
           "JPY": "¥", "ZAR": "R", "PHP": "₱", "NGN": "₦"}


class Stop(Exception):
    """Nothing usable can be built. The message is one plain line; ask is the question for the founder."""

    def __init__(self, msg, ask=None):
        super().__init__(msg)
        self.ask = ask


# ====================================================================== style
class Style:
    def __init__(self, decimal="dot", group=",", symbol="", after=False, decimals=0, order="DMY", sep="/",
                 american=False, indian=False, short=False):
        self.decimal, self.group, self.symbol, self.after = decimal, group, symbol, after
        self.decimals, self.order, self.sep, self.american, self.indian = decimals, order, sep, american, indian
        self.short = short  # the founder writes dates as numbers (05/04/2027): use that everywhere

    def num(self, x, decimals=None):
        dp = self.decimals if decimals is None else decimals
        neg = x < 0
        x = abs(x)
        s = f"{x:.{dp}f}"
        whole, _, frac = s.partition(".")
        if self.indian and len(whole) > 3:
            head, tail = whole[:-3], whole[-3:]
            parts = []
            while len(head) > 2:
                parts.insert(0, head[-2:])
                head = head[:-2]
            if head:
                parts.insert(0, head)
            whole = ",".join(parts) + "," + tail
        else:
            g = self.group
            whole = f"{int(whole):,}".replace(",", "\u0001").replace("\u0001", g)
        out = whole + ((("," if self.decimal == "comma" else ".") + frac) if frac else "")
        return ("-" if neg else "") + out

    def money(self, x, decimals=None):
        s = self.num(x, decimals)
        if not self.symbol:
            return s
        if self.after:
            return f"{s} {self.symbol}"
        if s.startswith("-"):
            return "-" + self.symbol + s[1:]
        return self.symbol + s

    def pct(self, frac, dp=1):
        v = round(frac * 100, dp)
        s = f"{v:.{dp}f}".rstrip("0").rstrip(".")
        if self.decimal == "comma":
            s = s.replace(".", ",")
        return s + "%"

    def d(self, dt, long=True, weekday=False):
        if self.short:
            long, weekday = False, False
        return D.fmt(dt, self.order, self.sep, long=long, weekday=weekday, american=self.american)

    def xl_money(self):
        dp = "0" * self.decimals
        core = "#,##0" + ("." + dp if dp else "")
        if self.indian:
            core = "[>=10000000]##\\,##\\,##\\,##0;[>=100000]##\\,##\\,##0;##,##0"
            return core
        if not self.symbol:
            return core
        return (core + f' "{self.symbol}"') if self.after else (f'"{self.symbol}"' + core)


US_WORDS = {"realised": "realized", "realise": "realize", "organise": "organize", "favour": "favor",
            "honour": "honor", "colour": "color", "centre": "center", "analyse": "analyze", "behaviour": "behavior",
            "prioritise": "prioritize", "programme": "program", "cancelled": "canceled", "per cent": "percent",
            "licence": "license", "practise": "practice", "recognise": "recognize", "summarise": "summarize"}


def localise(text, american):
    if not american:
        return text
    for a, b in US_WORDS.items():
        text = re.sub(r"\b" + a + r"\b", b, text)
        text = re.sub(r"\b" + a.capitalize() + r"\b", b.capitalize(), text)
    return text


# ====================================================================== reading
def collect_figures(inp):
    out = []
    for c in inp.get("clients", []):
        for k in ("fee", "direct_cost", "target_fee", "keep_fee"):
            if c.get(k) not in (None, ""):
                out.append(str(c[k]))
    an = inp.get("anchor") or {}
    for k in ("new_client_fee", "hourly_target"):
        if an.get(k) not in (None, ""):
            out.append(str(an[k]))
    if inp.get("hour_value"):
        out.append(str(inp["hour_value"]))
    return out


def detect_style(inp):
    figs = collect_figures(inp)
    hours = [str(c.get("hours")) for c in inp.get("clients", []) if c.get("hours") not in (None, "")]
    dec = inp.get("decimal")
    if dec not in (None, ""):
        key = re.sub(r"[^a-z.,]", "", str(dec).lower().replace("decimal", ""))
        dec = DECIMAL_WORDS.get(key)
        if dec is None:
            raise Stop(f"decimal style '{inp.get('decimal')}' not known (use \"dot\" or \"comma\")",
                       ask="Do you write a decimal with a point (1,250.50) or a comma (1.250,50)?")
    dec = dec or detect_decimal_style(figs + hours)
    if dec is None:
        seps = re.findall(r"\d([.,])(\d+)", " ".join(figs))
        if not seps or all(s == "," and len(d) == 3 for s, d in seps):
            dec = "dot"  # 1,800 and 3,000: commas group thousands
        elif any(s == "." and len(d) != 3 for s, d in seps) and not any(s == "," for s, d in seps):
            dec = "dot"  # 7.5 and 1.25: points are decimals
        else:
            bad = [f for f in figs if re.search(r"\d\.\d{3}(?!\d)", f)] or figs
            raise Stop("a figure can be read two ways", ask=f"When you write {bad[0]}, is the point separating "
                       f"thousands (as in 1.250,00) or decimals (as in 1,250.00)?")
    joined = " ".join(figs)
    indian = bool(inp.get("grouping") == "indian" or re.search(r"lakh|lac\b|crore|\d,\d\d,\d{3}", joined, re.I))
    cur = (inp.get("currency") or "").upper()
    symbol, after = "", False
    seen = [s for s in ("€", "£", "₹", "$", "S$", "¥", "₱", "₦") if s in joined]
    if seen:
        symbol = seen[0] if not (seen[0] == "$" and cur == "SGD") else "S$"
        with_sym = [f for f in figs if symbol in f]
        after = sum(1 for f in with_sym if re.search(r"\d[\d.,\-]*\s?" + re.escape(symbol), f)) > len(with_sym) / 2
    if not symbol and cur in SYMBOLS:
        symbol = SYMBOLS[cur]
        after = cur == "EUR" and dec == "comma"
    decimals = 2 if any(re.search(r"[.,]\d{2}(?!\d)\s*\S*$", f) and not re.search(r"[.,]00(?!\d)", f) for f in figs) else 0
    if inp.get("money_decimals") not in (None, ""):  # the founder's choice: 2.750,00 € or 2.750 €
        try:
            decimals = int(inp["money_decimals"])
        except (TypeError, ValueError):
            decimals = -1
        if decimals not in (0, 2):
            raise Stop("money_decimals must be 0 or 2", ask="Do you write amounts with cents (2,750.00) or without (2,750)?")
    country = (inp.get("country") or "").upper()
    loc = locale_defaults(country)
    english = str(inp.get("english") or "").lower()
    american = english in ("en-us", "american", "us")
    order = inp.get("date_order") or loc["date_order"]
    sep = inp.get("date_sep") or ("/" if order != "YMD" else "-")
    return Style(decimal=dec, group="." if dec == "comma" else ",", symbol=symbol, after=after, decimals=decimals,
                 order=order, sep=sep, american=american, indian=indian,
                 short=str(inp.get("date_style") or "").lower() == "short"), loc


def money_in(text, dec, label, required=True):
    if text in (None, ""):
        if required:
            raise Stop(f"{label} is missing", ask=f"What is {label}?")
        return None
    if isinstance(text, (int, float)):
        return float(text)
    t = APPROX.sub("", str(text)).strip()
    if t.startswith("="):
        expr = t[1:].replace(" ", "")
        if not re.fullmatch(r"[\d.,+\-*/()]+", expr):
            raise Stop(f"{label}: '{text}' is not a sum I can work out", ask=f"What is {label}, as one figure?")
        nums = re.findall(r"[\d.,]+", expr)
        for n in nums:
            expr = expr.replace(n, repr(parse_number(n, dec)[0]), 1)
        try:
            return float(eval(expr, {"__builtins__": {}}, {}))  # digits and operators only, checked above
        except Exception:
            raise Stop(f"{label}: '{text}' could not be worked out", ask=f"What is {label}, as one figure?") from None
    t = re.sub(r"\s*\b(monthly|quarterly|annually|yearly|weekly|each|per project|a project|per (month|quarter|year|week)|"
               r"a (month|quarter|year|week)|im monat|pro monat|monatlich|mensual(es)?|par mois)\b\.?", " ", t, flags=re.I).strip()
    t = re.sub(r"\s*/\s*(month|mo|m|quarter|qtr|q|year|yr|y|project|week|wk)\b\.?", " ", t, flags=re.I).strip()
    t = re.sub(r"\s*(,-|\.-)\s*$", "", t)  # 890,- €
    t = re.sub(r"(\d),-(\s|$)", r"\1\2", t)
    try:
        return parse_number(t, dec)[0]
    except Ambiguous as e:
        raise Stop(f"{label}: {e}", ask=f"{label}: did you mean {e}?") from None
    except Unreadable as e:
        raise Stop(f"{label}: {e}", ask=f"Could you restate {label} as one figure?") from None


def hours_in(text, dec, label):
    if text in (None, ""):
        return None
    if isinstance(text, (int, float)):
        return float(text)
    from locale_numbers import parse_hours
    t = APPROX.sub("", str(text))
    t = re.sub(r"\s*(a|per|/|im|pro)\s*(month|mo|m|monat|mes|mois)\b\.?", "", t, flags=re.I).strip()
    t = re.sub(r"(hrs?|hours?|h|std\.?|stunden)\s*/\s*(mo|month)$", r"\1", t, flags=re.I)
    try:
        return parse_hours(t, decimal=dec)[0]
    except (Ambiguous, Unreadable) as e:
        raise Stop(f"{label}: {e}", ask=f"Roughly how many hours a month does {label.split(' hours')[0]} take?") from None


def pct_in(text, dec, label, default):
    if text in (None, ""):
        return default
    if isinstance(text, (int, float)):
        v = float(text)
        return v / 100 if v > 1 else v
    try:
        v = parse_percent(str(text), dec)[0]
    except (Ambiguous, Unreadable) as e:
        raise Stop(f"{label}: {e}", ask=f"What should {label} be, as a percentage?") from None
    return v / 100


def floor_round(x, small, large, threshold, floor_at):
    """Round down to the step (small below the threshold, large from it), never below floor_at."""
    x = round(x, 6)
    unit = small if x < threshold else large
    r = math.floor(x / unit) * unit if unit else x
    if r <= floor_at:
        r = math.floor(x)
    return float(r)


# ====================================================================== planning
def per_unit(c):
    per = str(c.get("per") or "month").lower()
    per = {"monthly": "month", "mo": "month", "quarterly": "quarter", "annual": "year", "yearly": "year",
           "annually": "year", "per project": "project", "weekly": "week"}.get(per, per)
    if per not in UNIT_MONTHS and per != "project":
        raise Stop(f"{c.get('name')}: billing unit '{c.get('per')}' not known",
                   ask=f"Is {c.get('name')}'s fee per month, per quarter, per year or per project?")
    return per


def fill_line(line, c, st):
    """The founder's own sentence, with {hours} and {fee} filled for this client."""
    hrs = st.num(c["hours"], 0 if c["hours"] and float(c["hours"]).is_integer() else 1) if c.get("hours") else ""
    out = str(line).replace("{hours}", hrs).replace("{fee}", st.money(c["fee"]))
    if "{hours}" in str(line) and not hrs:
        out = re.sub(r"[;,]?[^;,.]*\{hours\}[^;,.]*", "", str(line)).replace("{fee}", st.money(c["fee"]))
    return out.strip().rstrip(".") + "."


def poss(name):
    """Hartley's, Orchid Interiors' (never Interiors's)."""
    name = str(name)
    return name + ("'" if name.endswith(("s", "S")) else "'s")


APPROX = re.compile(r"^\s*(~|≈|c\.|ca\.?|circa|about|approx\.?|approximately|around|roughly|maybe|nearly|almost|"
                    r"ungef[äa]hr|etwa|rund|environ|à peu près|aprox\.?|aproximadamente|unos|unas|lagbhag|takriban)\s*",
                    re.I)


def resolve_duplicates(raw_clients, dec, st):
    """--provisional: a client listed twice with different fees keeps the higher fee, marked fee_unsure.

    The higher fee gives the smaller rise and the smaller cash figure, so a provisional plan never overstates.
    Fields from both rows are kept; where both rows give a field, the row with the higher fee wins.
    """
    groups, order = {}, []
    for rc in raw_clients:
        if not isinstance(rc, dict) or not rc.get("name"):
            order.append(rc)
            continue
        key = re.sub(r"[^a-z0-9]", "", str(rc["name"]).lower())
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(rc)
    out = []
    for item in order:
        if not isinstance(item, str):
            out.append(item)
            continue
        rows = groups[item]
        fees = [money_in(r.get("fee"), dec, f"the fee for {r['name']}") for r in rows]
        if len({round(f, 2) for f in fees}) <= 1:
            out.extend(rows)
            continue
        ranked = sorted(zip(fees, range(len(rows))), reverse=True)
        merged = {}
        for _f, i in reversed(ranked):
            merged.update({k: v for k, v in rows[i].items() if v not in (None, "")})
        lo, hi = min(fees), max(fees)
        merged["fee_unsure"] = f"{st.money(lo)} or {st.money(hi)}"
        out.append(merged)
    return out


def plan(inp, today=None, provisional=False):
    if not isinstance(inp, dict) or not isinstance(inp.get("clients"), list) or not inp["clients"]:
        raise Stop("the inputs file has no clients list", ask="Who are your clients and what does each pay?")
    for i, rc in enumerate(inp["clients"]):
        if not isinstance(rc, dict) or not rc.get("name") or rc.get("fee") in (None, ""):
            what = rc.get("name") if isinstance(rc, dict) and rc.get("name") else f"client {i + 1}"
            raise Stop(f"{what} needs a name and a fee in the inputs file",
                       ask=f"What does {what} pay?" if isinstance(rc, dict) and rc.get("name") else
                       "What is the name of each client and what does each pay?")
    if not isinstance(inp.get("anchor") or {}, dict):
        raise Stop("the anchor in the inputs file must be a set of fields (new_client_fee, new_client_hours, per)")
    st, loc = detect_style(inp)
    dec = st.decimal
    today = today or (D.parse_date(inp["date"]) if inp.get("date") else date.today())
    flags, needs, notes = [], [], []
    confirmed = {str(x).lower() for x in inp.get("confirmed", [])}

    # ---- send date and window
    send_assumed = not inp.get("send_date")
    try:
        send = D.parse_date(inp.get("send_date") or today.isoformat(), st.order, today)
    except D.DateStop as e:
        raise Stop(f"send date: {e}", ask="On what date will the letters go out?") from None
    return_run = bool(inp.get("outcomes")) or any(isinstance(c, dict) and c.get("fixed_steps") for c in inp["clients"])
    if send < today and not return_run:
        raise Stop(f"the send date {st.d(send)} is in the past; letters are dated from the day they are sent and "
                   f"cannot be backdated", ask="When will the letters actually go out (today or later)?")
    if send_assumed:
        needs.append(f"[NEED: the date the letters go out] I have used today, {st.d(send, weekday=True)}; "
                     f"every letter is HOLD until you confirm it")
    if not D.is_working_day(send, inp.get("working_days")):
        flags.append(f"The send date {st.d(send, weekday=True)} is not one of your working days.")
    window_months = int(inp.get("window_months") or 12)
    window_end = D.add_months(send, window_months)
    start_floor = None
    if inp.get("start_no_earlier"):
        try:
            start_floor = D.parse_date(inp["start_no_earlier"], st.order, today)
        except D.DateStop as e:
            raise Stop(f"start date: {e}", ask="From what date do you want the new fees to start?") from None

    # ---- rules
    cap = pct_in(inp.get("step_cap"), dec, "the biggest single step", 0.20)
    if cap <= 0:
        raise Stop("the step cap must be above zero", ask="What is the biggest single rise you are comfortable with?")
    if cap > 0.5 and "step cap" not in confirmed:
        raise Stop(f"a single step of {st.pct(cap)} is very large for an existing client",
                   ask=f"Do you want steps of up to {st.pct(cap)} in one go? Say yes and I'll use it.")
    closure = pct_in(inp.get("closure"), dec, "the one-step closure rule", 0.95)
    gap_months = int(inp.get("second_step_months") or 6)
    rnd = inp.get("rounding") or {}
    small, large = float(rnd.get("small", 10)), float(rnd.get("large", 50))
    threshold = float(rnd.get("threshold", 1000))
    billing_day = int(inp.get("billing_day") or 1)
    notice_default_raw = inp.get("notice_default") or "60 days"
    try:
        notice_default = D.parse_notice(notice_default_raw)
    except D.DateStop as e:
        raise Stop(f"planning default notice: {e}", ask="What notice should I assume where a contract is unknown?") from None
    tenure_years = float(inp.get("call_first_tenure_years") or 4)
    top_q = inp.get("call_first_top_quartile", True)
    fee_word = inp.get("fee_word") or "fee"
    reason_order = inp.get("reason_order") or REASON_ORDER
    tax = (inp.get("fees_tax") or "before").lower()
    hour_value = money_in(inp.get("hour_value"), dec, "the value of an hour", required=False)

    # ---- anchor
    an = inp.get("anchor") or {}
    anchor_rate, anchor_src, anchor_text = None, None, ""
    ncf = money_in(an.get("new_client_fee"), dec, "the new-client price", required=False)
    nch = hours_in(an.get("new_client_hours"), dec, "the new-client hours") if an.get("new_client_hours") else None
    ncf_per = per_unit({"per": an.get("per") or "month", "name": "new clients"})
    if ncf is not None and nch:
        anchor_rate = ncf / nch if ncf_per == "project" else ncf / UNIT_MONTHS[ncf_per] / nch
        anchor_src = "new_client_price"
        anchor_text = (f"your new-client price, {st.money(ncf)} {UNIT_WORDS[ncf_per]} for about {st.num(nch, 0)} "
                       f"hours{'' if ncf_per == 'project' else ' a month'}")
    elif an.get("hourly_target"):
        anchor_rate = money_in(an["hourly_target"], dec, "the hourly target")
        anchor_src = "hourly_target"
        anchor_text = f"your hourly target of {st.money(anchor_rate)}"
    elif ncf is not None:
        needs.append("[NEED: roughly how many hours new clients get for "
                     f"{st.money(ncf)}] without it the new-client price cannot be scaled to each client")

    # ---- clients
    raw_clients = inp["clients"]
    if provisional or inp.get("provisional"):
        raw_clients = resolve_duplicates(raw_clients, dec, st)
    names = {}
    clients = []
    injected = []
    for i, rc in enumerate(raw_clients):
        if not isinstance(rc, dict) or not rc.get("name"):
            raise Stop(f"client {i + 1} has no name", ask="What is the name of each client on your list?")
        for k, v in rc.items():
            if isinstance(v, str) and INJECTION.search(v):
                injected.append(f"{rc['name']} ({k}): \"{v[:80]}\"")
                rc[k] = "" if k not in ("name", "fee") else v
        name = str(rc["name"]).strip()
        key = re.sub(r"[^a-z0-9]", "", name.lower())
        c = {"name": name, "raw": rc}
        c["per"] = per_unit(rc)
        c["fee"] = money_in(rc.get("fee"), dec, f"the fee for {name}")
        if key in names:
            other = names[key]
            if abs(other["fee"] - c["fee"]) < 0.005:
                flags.append(f"{name} appears twice with the same fee; merged into one row.")
                continue
            raise Stop(f"{name} appears twice with different fees ({st.money(other['fee'])} and "
                       f"{st.money(c['fee'])}); run again with --provisional for a first plan on the higher fee",
                       ask=f"Which is {poss(name)} current fee: {st.money(other['fee'])} or {st.money(c['fee'])}?")
        if rc.get("fee_unsure"):
            c["fee_unsure"] = str(rc["fee_unsure"])
            flags.append(f"{name} was listed with two fees ({c['fee_unsure']}). This plan uses {st.money(c['fee'])}, "
                         f"the higher, so it does not overstate the rise; any letter for them is HOLD until you say "
                         f"which is current.")
        unread = rc.get("unread")
        if isinstance(unread, dict):
            unread = [f"{k}: {v}" for k, v in unread.items() if str(v).strip()]
        elif isinstance(unread, str):
            unread = [unread] if unread.strip() else []
        c["unread"] = [str(x) for x in (unread or []) if str(x).strip()]
        if c["unread"]:
            flags.append(f"{name}: your list has a note the plan has not read ({'; '.join(c['unread'])}). Check it for "
                         f"a price lock, a renewal or a scope change; their letter is HOLD until it is in the plan.")
        sl = str(rc.get("scope_line") or "") if rc.get("scope_crept") else ""
        if rc.get("reason"):
            sl = (sl + " " + str(rc["reason"])).strip()
        tp = re.search(r"\b(they|their|them|theirs|themselves|he|she|his|her|hers)\b", sl, re.I)
        if not tp and sl:
            tp = re.search(r"\b" + re.escape(name.split()[0]) + r"\b", sl) if len(name.split()[0]) > 2 else None
        c["third_person"] = (sl if len(sl) <= 90 else sl[max(0, tp.start() - 30):tp.end() + 40].strip()) \
            if tp else None
        names[key] = c
        if c["fee"] < 1:
            raise Stop(f"{poss(name)} fee reads as {st.money(c['fee'], 2)}, under one unit of your currency",
                       ask=f"What does {name} pay, as you would write it on an invoice?")
        c["hours"] = hours_in(rc.get("hours"), dec, f"{name} hours")
        if c["hours"] is not None and c["hours"] <= 0:
            c["hours"] = None
        if c["hours"] and c["per"] != "project" and c["hours"] > 200 and f"{name} hours" not in confirmed:
            raise Stop(f"{name} reads as {st.num(c['hours'], 0)} hours a month, above one person's working month",
                       ask=f"Is {st.num(c['hours'], 0)} hours a month right for {name}?")
        c["cost"] = money_in(rc.get("direct_cost"), dec, f"the direct cost for {name}", required=False) or 0.0
        c["target_given"] = money_in(rc.get("target_fee"), dec, f"{poss(name)} target fee", required=False)
        c["keep_fee"] = money_in(rc.get("keep_fee"), dec, f"{poss(name)} price to keep", required=False)
        c["fixed_steps"] = rc.get("fixed_steps")
        if c["per"] == "project":
            c["ppy"] = money_in(rc.get("projects_per_year"), dec, f"{poss(name)} projects a year", required=False)
            c["units_year"] = c["ppy"] or 0.0
            c["every"] = None
            c["units_per_bill"] = 1.0
        else:
            every = rc.get("billed_every")
            every = int(every) if every not in (None, "") else int(UNIT_MONTHS[c["per"]]) if c["per"] != "week" else 1
            c["every"] = every
            c["units_year"] = 12 / UNIT_MONTHS[c["per"]]
            c["units_per_bill"] = every / UNIT_MONTHS[c["per"]]
        c["hours_unit"] = None
        if c["hours"]:
            c["hours_unit"] = c["hours"] if c["per"] == "project" else c["hours"] * UNIT_MONTHS[c["per"]]
        c["rate_now"] = (c["fee"] - c["cost"]) / c["hours_unit"] if c["hours_unit"] else None
        y, m = D.parse_year(rc.get("since"))
        c["since_year"], c["since_month"] = y, m
        c["tenure"] = None
        if y:
            c["tenure"] = (send.year - y) + ((send.month - m) / 12 if m else 0)
        clients.append(c)
    if injected:
        flags.append("Ignored, because it was written to an AI rather than about a client: " + "; ".join(injected))

    if anchor_rate is None:
        rates = [c["rate_now"] for c in clients if c["rate_now"]]
        if len(rates) >= 2:
            anchor_rate = statistics.median(rates)
            anchor_src = "median"
            anchor_text = (f"the middle of your own clients' hourly rates, {st.money(anchor_rate)} an hour "
                           f"(your own median; give me what new clients pay and it becomes specific)")
            notes.append("No new-client price or hourly target was given, so each target is your own median rate "
                         "times that client's hours.")
    blanket = not anchor_rate and all(c["target_given"] is None for c in clients)
    if blanket:
        notes.append("This is a blanket rise: with no hours and no target, every client gets the same step. "
                     "Roughly how many hours a month each client takes would make it client by client.")
    if all(c["target_given"] is not None and c["target_given"] < c["fee"] for c in clients) \
            and "targets" not in confirmed:
        raise Stop("every target fee is below the client's current fee, so nobody would be raised",
                   ask="Are those target fees right? They are all below what clients pay now.")

    # ---- per-client target, segment, steps, dates
    fees_annual = sorted((c["fee"] * c["units_year"] for c in clients), reverse=True)
    k_top = math.ceil(len(fees_annual) / 4) if fees_annual else 0
    med = statistics.median(fees_annual) if fees_annual else 0
    q_cut = fees_annual[k_top - 1] if fees_annual else 0
    if q_cut <= med:  # ties at the boundary: only clients clearly above the middle count as largest
        above = [f for f in fees_annual if f > med]
        q_cut = min(above) if above else float("inf")
    for c in clients:
        rc = c["raw"]
        name = c["name"]
        c["cap"] = cap
        if rc.get("step_cap"):
            c["cap"] = pct_in(rc["step_cap"], dec, f"{poss(name)} step cap", cap)
        elif rc.get("gentle"):
            c["cap"] = round(cap / 2, 6)
        # target
        c["target"], c["target_src"] = None, None
        if c["target_given"] is not None:
            c["target"], c["target_src"] = c["target_given"], "your target for this client"
        elif anchor_rate and c["hours_unit"]:
            c["target"] = anchor_rate * c["hours_unit"] + c["cost"]
            c["target_src"] = {"new_client_price": "new-client price scaled to these hours",
                               "hourly_target": "your hourly target times these hours",
                               "median": "your own median rate times these hours"}[anchor_src]
        # segment
        seg, why = None, ""
        crept = bool(rc.get("scope_crept"))
        renewal = bool(rc.get("renewal_only") or rc.get("term_end") or rc.get("renewal_date"))
        if rc.get("hold"):
            seg, why = "Hold", "you asked to hold this client"
        elif c["target"] is not None and c["fee"] >= c["target"] - 0.005:
            seg, why = "Hold", "already at or above target"
        elif rc.get("relieved") or c["fee"] - c["cost"] <= 0:
            seg = "Price to keep"
            why = "you would be relieved to lose them" if rc.get("relieved") else "costs you money at today's fee"
        elif crept:
            seg, why = "Reset the scope", "the scope has crept"
        elif renewal:
            seg, why = "At renewal", "the price can only change at renewal"
        c["segment"], c["why"] = seg, why
        if c["target"] is not None and c["rate_now"] and seg not in ("Hold",) and not crept and not rc.get("scope_ok"):
            if c["fee"] < 0.5 * c["target"]:
                c.setdefault("asks", []).append(
                    f"{name} pays under half your target for the hours. Has the scope crept? If so, say so and "
                    f"it becomes a scope reset.")
        # notice
        notice_raw = rc.get("notice") or inp.get("notice")
        c["notice_src"] = "founder supplied" if notice_raw else "planning default"
        try:
            parsed, text_align = D.parse_notice_full(notice_raw) if notice_raw else (notice_default, None)
        except D.DateStop as e:
            raise Stop(f"{poss(name)} notice: {e}", ask=f"What notice do you give {name} before a price change, and does "
                       f"it run to a month end, a quarter end or neither?") from None
        c["notice"] = parsed
        field_align = rc.get("notice_align") or (inp.get("notice_align") if not rc.get("notice") else None)
        if field_align and text_align and str(field_align).lower() != text_align:
            raise Stop(f"{name}: the notice says '{notice_raw}' but notice_align says '{field_align}'",
                       ask=f"Does {poss(name)} notice run to a {text_align.replace('_', ' ')} or a "
                           f"{str(field_align).lower().replace('_', ' ')}?")
        c["align"] = str(field_align or text_align or (inp.get("notice_align") if not rc.get("notice") else None)
                         or "none").lower().replace(" ", "_").replace("-", "_")
        if c["align"] not in D.ALIGNMENTS:
            raise Stop(f"{name}: notice alignment '{c['align']}' not known",
                       ask=f"Does {poss(name)} notice run to a month end, a quarter end, or neither?")
        bday = int(rc.get("billing_day") or billing_day)
        c["billing_day"] = bday
        months = rc.get("billing_months")
        if c["per"] != "project" and c["every"] and c["every"] > 1 and not months:
            anchor_m = None
            for k in ("renewal_date", "term_end"):
                if rc.get(k):
                    dd = D.parse_date(rc[k], st.order, today)
                    anchor_m = (dd + timedelta(days=1)).month if k == "term_end" else dd.month
                    break
            months = D.default_months(c["every"], anchor_m or c["since_month"] or 1)
        c["billing_months"] = months
        nend = D.notice_end(send, c["notice"])
        aligned = D.align(nend, c["align"])
        earliest = aligned + timedelta(days=1) if c["align"] != "none" else nend
        c["notice_ends"] = aligned
        c["start_note"] = None
        if start_floor and start_floor > earliest:
            earliest = start_floor
            c["start_floor_used"] = True
        elif start_floor and start_floor < earliest:
            c["start_note"] = True
        c["renewal_moved"] = None
        if renewal:
            if rc.get("renewal_date"):
                ren = D.parse_date(rc["renewal_date"], st.order, today)
            elif rc.get("term_end"):
                c["term_end_d"] = D.parse_date(rc["term_end"], st.order, today)
                ren = c["term_end_d"] + timedelta(days=1)
            else:
                ren = earliest
            term = int(rc.get("term_months") or 12)
            first_ren = ren
            while ren < earliest:
                ren = D.add_months(ren, term)
            if ren != first_ren:
                c["renewal_moved"] = (first_ren, ren)
            earliest = ren
        if c["per"] == "project":
            eff1 = earliest
        else:
            eff1 = D.first_billing_on_or_after(earliest, c["every"], bday, months)
        c["eff1"] = eff1
        c["latest_send"] = None
        if (start_floor or send_assumed) and c["per"] != "project" and not renewal:
            probe = eff1
            while probe > send:  # the last day the letter can go and still keep this date
                ne = D.align(D.notice_end(probe, c["notice"]), c["align"])
                ne = ne + timedelta(days=1) if c["align"] != "none" else ne
                ne = max(ne, start_floor) if start_floor else ne
                if D.first_billing_on_or_after(ne, c["every"], bday, months) <= eff1:
                    while not D.is_working_day(probe, inp.get("working_days")) and probe > send:
                        probe -= timedelta(days=1)
                    c["latest_send"] = probe
                    break
                probe -= timedelta(days=1)
        # steps
        c["step1"] = c["step2"] = None
        c["eff2"] = None
        x_target = c["target"]
        if seg == "Hold":
            c["step1"] = c["fee"]
        elif seg == "Price to keep":
            k = c["keep_fee"] if c["keep_fee"] is not None else x_target
            if k is None:
                c["step1"] = None
                needs.append(f"[NEED: the fee you would be glad to keep {name} at] their letter is HOLD")
            else:
                c["step1"] = k if c["keep_fee"] is not None else floor_round(k, small, large, threshold, c["fee"])
                c["step1"] = max(c["step1"], c["fee"])
        else:
            capped = c["fee"] * (1 + c["cap"])
            x = capped if x_target is None else min(x_target, capped)
            c["step1"] = floor_round(x, small, large, threshold, c["fee"])
            if seg is None:
                if rc.get("gentle") or (x_target is not None and c["step1"] < closure * x_target - 1e-9):
                    seg, why = "Two steps", ("you asked to go gently" if rc.get("gentle")
                                             else "the gap is bigger than one step")
                else:
                    seg = "Raise now"
                    why = (f"one step comes within {round((1 - closure) * 100):g}% of target" if x_target is not None
                           else "hours not given, flat step")
                c["segment"], c["why"] = seg, why
            if seg == "Two steps":
                capped2 = c["step1"] * (1 + c["cap"])
                x2 = capped2 if x_target is None else min(x_target, capped2)
                c["step2"] = floor_round(x2, small, large, threshold, c["step1"])
                e2 = D.add_months(eff1, gap_months)
                c["eff2"] = e2 if c["per"] == "project" else D.first_billing_on_or_after(
                    e2, c["every"], bday, months)
        if c["fixed_steps"]:  # a plan already sent: keep it as it was
            fs = c["fixed_steps"]
            c["step1"] = money_in(fs.get("step1"), dec, f"{poss(name)} planned step 1")
            c["eff1"] = D.parse_date(fs["date1"], st.order, today)
            c["step2"] = money_in(fs.get("step2"), dec, f"{poss(name)} planned step 2", required=False)
            c["eff2"] = D.parse_date(fs["date2"], st.order, today) if fs.get("date2") else None
        c["last"] = c["step2"] if c["step2"] is not None else c["step1"]
        c["change_unit"] = (c["last"] - c["fee"]) if c["last"] is not None else 0.0
        c["raised"] = c["change_unit"] > 0.005
        c["gap"] = max(0.0, x_target - c["last"]) if (x_target is not None and c["last"] is not None) else None
        if c["gap"] is not None and c["gap"] < 0.5:
            c["gap"] = 0.0
        c["steps_to_close"] = 0
        if c["gap"] and seg not in ("Hold", "Price to keep"):
            f = c["last"]
            while f < closure * x_target - 1e-9 and c["steps_to_close"] < 12:
                f = floor_round(min(x_target, f * (1 + c["cap"])), small, large, threshold, f)
                c["steps_to_close"] += 1
        # reset the scope choices
        if seg == "Reset the scope":
            inc = hours_in(rc.get("included_hours"), dec, f"{name} included hours") if rc.get("included_hours") else None
            extras = hours_in(rc.get("extras_hours"), dec, f"{name} extra hours") if rc.get("extras_hours") else None
            c["scope_b_src"] = "you said" if inc is not None else None
            if inc is None and c["hours"] and extras and extras < c["hours"]:
                inc, c["scope_b_src"] = c["hours"] - extras, "your hours less the extras you named"
            if inc is None and c["hours"] and c["step1"]:
                # today's fee buys fewer hours at Option A's hourly rate: a real choice, never a free hold
                inc = math.floor(c["hours"] * c["fee"] / c["step1"] * 2) / 2
                c["scope_b_src"] = "the hours today's fee buys at Option A's hourly rate"
            c["scope_b_hours"] = inc
            c["extras_rate"] = anchor_rate
            c["rate_a"] = (c["step1"] / (c["hours"] * (UNIT_MONTHS.get(c["per"], 1)))) if c["hours"] else None
            c["rate_b"] = (c["fee"] / (inc * UNIT_MONTHS.get(c["per"], 1))) if inc else None
            if inc is None:
                needs.append(f"[NEED: how many hours a month {poss(name)} defined scope should include] their letter is HOLD")
            if inc is not None and c["hours"]:
                notes.append(f"{name}: Option B keeps {st.money(c['fee'])} for "
                             f"{st.num(inc, 0 if float(inc).is_integer() else 1)} hours a month, with extra work at "
                             f"{st.money(anchor_rate) if anchor_rate else '[NEED: your hourly fee]'} an hour."
                             + (f" Option B works out at {st.money(c['rate_b'])} an hour against the "
                                f"{st.money(anchor_rate)} you charge for extras; give Option B fewer hours if you want "
                                f"the two closer." if c.get("rate_b") and anchor_rate and c["rate_b"] < 0.8 * anchor_rate
                                else ""))
            if x_target and c["step1"] < 0.5 * x_target:
                c["deep_gap"] = True
                notes.append(f"{name}: even {st.money(c['step1'])} for {st.num(c['hours'] or 0, 0)} hours stays under "
                             f"half your target. A bigger percentage will not fix it. The two routes are a price to keep "
                             f"(the fee at which you would be glad to keep them) or a smaller defined scope.")
        # call first
        annual = c["fee"] * c["units_year"]
        c["annual_fee"] = annual
        c["call_first"] = False
        c["call_why"] = []
        if seg not in ("Hold",):
            if top_q and len(clients) >= 4 and annual >= q_cut:
                c["call_first"] = True
                c["call_why"].append("one of your largest clients")
            if c["tenure"] is not None and c["tenure"] >= tenure_years - 1e-9:
                c["call_first"] = True
                c["call_why"].append(f"with you since {c['since_year']}")
        if c["renewal_moved"]:
            a, b = c["renewal_moved"]
            flags.append(f"{name}: the renewal on {st.d(a)} falls inside the notice period, so the change moves to "
                         f"the next renewal, {st.d(b)}.")

    # ---- call first: a short list, ranked by annual fee, so it means something
    to_letter = [c for c in clients if c["segment"] != "Hold"]
    call_cap = int(inp.get("call_first_max") or min(3, max(1, math.ceil(len(to_letter) / 3))))
    ranked = sorted((c for c in to_letter if c["call_first"]), key=lambda c: (-c["annual_fee"], c["name"]))
    for c in ranked[call_cap:]:
        c["call_first"] = False
        c["call_why"] = []

    # ---- reasons
    last_change_text = inp.get("last_change")
    lc_years = None
    if last_change_text:
        m = re.search(r"(\d+(?:[.,]\d+)?|one|two|three|four|five|six|seven|eight|nine|ten)\s+years?", str(last_change_text), re.I)
        words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
        if m:
            g = m.group(1).lower()
            lc_years = words.get(g) or float(g.replace(",", "."))
        y, _ = D.parse_year(last_change_text)
        if y:
            lc_years = send.year - y
    for c in clients:
        rc = c["raw"]
        options = {}
        if ncf is not None and (c["per"] == "project") == (ncf_per == "project"):
            # The reason must be true for this client: scaled to their hours, or left out when their new fee
            # would sit above the new-client price with nothing to show the work is bigger.
            month_word = "" if ncf_per == "project" else " a month"
            new_last = c["last"] if c["last"] is not None else c["fee"]
            ncf_same_unit = ncf * (1 if c["per"] == "project" else
                                   UNIT_MONTHS[c["per"]] / UNIT_MONTHS[ncf_per])
            if nch and c["hours"] and anchor_src == "new_client_price":
                hourly = ncf / nch if ncf_per == "project" else ncf / UNIT_MONTHS[ncf_per] / nch
                hrs_c = st.num(c["hours"], 0 if float(c["hours"]).is_integer() else 1)
                if (new_last - c["cost"]) / c["hours_unit"] <= hourly + 0.01:
                    options["new_client_price"] = (
                        f"New clients now pay {st.money(ncf)} {UNIT_WORDS[ncf_per]} for about {st.num(nch, 0)} "
                        f"hours, which is {st.money(hourly)} an hour; your work runs to about "
                        f"{hrs_c} hours{'' if c['per'] == 'project' else ' a month'}.",
                        "you said what new clients pay and for how many hours, set beside this client's hours")
            elif new_last <= ncf_same_unit + 0.005:
                hrs = f" for about {st.num(nch, 0)} hours{month_word}" if nch else ""
                options["new_client_price"] = (f"New clients now pay {st.money(ncf)} {UNIT_WORDS[ncf_per]}{hrs}.",
                                               "you said what new clients pay")
        if rc.get("scope_crept") and rc.get("scope_line"):
            options["scope"] = (f"The work has grown since we set your {fee_word}: {rc['scope_line'].rstrip('.')}.",
                                "you described how the scope has grown")
        if rc.get("priced_low"):
            options["priced_low"] = (f"I set your {fee_word} too low when we started, and I am putting that right.",
                                     "you said this client was priced low from the start")
        lc = rc.get("last_change")
        if lc:
            options["last_change"] = (f"Your {fee_word} has not changed since {lc}.", "you gave the date of the last change")
        elif last_change_text and (not c["since_year"] or not lc_years or send.year - c["since_year"] >= lc_years - 0.5):
            options["last_change"] = (f"My {fee_word}s have not changed in {last_change_text}.",
                                      "you said when your fees last changed")
        cf = rc.get("cost_fact") or inp.get("cost_fact")
        if cf and re.search(r"\d", str(cf)):
            options["cost"] = (str(cf).rstrip(".") + ".", "you gave the cost figure")
        if inp.get("new_client_line") and "new_client_price" in options:
            options["new_client_price"] = (fill_line(inp["new_client_line"], c, st), "your own wording for the "
                                           "new-client price")
        if rc.get("reason"):
            options["founder"] = (str(rc["reason"]).strip().rstrip(".") + ".", "your own words for this client")
        c["reason"], c["reason_src"], c["reason_key"] = "", "", None
        first = ["founder"] if "founder" in options else ["priced_low"] if "priced_low" in options else []
        for k in first + list(reason_order):
            if k in options:
                c["reason"], c["reason_src"] = options[k]
                c["reason_key"] = k
                break
        if c["segment"] == "Reset the scope" and "scope" in options and "scope" in reason_order:
            c["reason"], c["reason_src"] = options["scope"]
            c["reason_key"] = "scope"
        if c["raised"] and not c["reason"]:
            needs.append(f"[NEED: one true reason for {c['name']}] the letter states the change with no reason")

    # ---- letter status
    for c in clients:
        hold = []
        if c["segment"] == "Hold":
            c["letter"] = "NONE"
            c["hold_why"] = "held: no letter"
            continue
        if c["notice_src"] == "planning default":
            hold.append(f"notice is a planning default ({D.notice_text(c['notice'])}), not your contract: confirm it")
        if tax != "before":
            hold.append("fees as supplied, tax status unconfirmed: ask your accountant whether they are before tax")
        if send_assumed:
            hold.append("send date not confirmed")
        if c["step1"] is None:
            hold.append("no fee to keep them at")
        if c["segment"] == "Reset the scope" and c.get("scope_b_hours") is None:
            hold.append("the defined scope needs its hours")
        elif c["segment"] == "Reset the scope" and not c["raw"].get("scope_confirmed"):
            hold.append(f"confirm Option B ({st.num(c['scope_b_hours'], 0 if float(c['scope_b_hours']).is_integer() else 1)} "
                        f"hours a month at today's fee, extra work at "
                        f"{st.money(c['extras_rate']) if c.get('extras_rate') else 'your hourly fee'} an hour)")
        if c["per"] == "project" and not c.get("ppy"):
            hold.append("expected projects a year not given (cash figure left out)")
        if c.get("fee_unsure"):
            hold.append(f"which fee is current, {c['fee_unsure']}? Planned on {st.money(c['fee'])} for now")
        if c.get("unread"):
            hold.append("a note in your list is not yet in the plan: " + "; ".join(c["unread"]))
        if c.get("third_person"):
            hold.append(f"the reason talks about the client ('{c['third_person']}'); write it to them, "
                        f"as 'you ...'")
        c["letter"] = "HOLD" if hold else "READY"
        c["hold_why"] = "; ".join(hold)

    # ---- cash in the window
    tot = {"cash12": 0.0, "run_rate": 0.0}
    for c in clients:
        c["n1"] = c["n2"] = 0.0
        c["bills"] = []
        if c["step1"] is None or c["segment"] == "Hold":
            c["cash12"] = 0.0
            c["run_rate"] = 0.0
            continue
        if c["per"] == "project":
            span = (window_end - send).days
            def frac(a, b):
                a, b = max(a, send), min(b, window_end)
                return max(0.0, (b - a).days / span) if span else 0.0
            ppy = c.get("ppy") or 0.0
            e2 = c["eff2"] or window_end
            c["n1"] = round(ppy * window_months / 12 * frac(c["eff1"], e2), 4)
            c["n2"] = round(ppy * window_months / 12 * frac(c["eff2"], window_end), 4) if c["eff2"] else 0.0
        else:
            bills = D.billing_dates(send, window_end, c["every"], c["billing_day"], c["billing_months"])
            c["bills"] = bills
            for b in bills:
                if c["eff2"] and b >= c["eff2"]:
                    c["n2"] += c["units_per_bill"]
                elif b >= c["eff1"]:
                    c["n1"] += c["units_per_bill"]
        c["cash12"] = (c["step1"] - c["fee"]) * c["n1"] + ((c["step2"] - c["fee"]) * c["n2"] if c["step2"] else 0.0)
        c["run_rate"] = c["change_unit"] * c["units_year"]
        tot["cash12"] += c["cash12"]
        tot["run_rate"] += c["run_rate"]

    # ---- break-even
    raised = [c for c in clients if c["raised"]]
    for c in clients:
        c["new_contrib"] = ((c["last"] or c["fee"]) - c["cost"]) * c["units_year"]
        c["old_contrib"] = (c["fee"] - c["cost"]) * c["units_year"]
        c["lost12"] = (c["fee"] - c["cost"]) * (c["n1"] + c["n2"])
        c["be_share"] = (c["run_rate"] / c["new_contrib"]) if (c["raised"] and c["new_contrib"] > 0) else None
    be = {"share": None, "raised": len(raised)}
    if raised:
        sum_change = sum(c["run_rate"] for c in raised)
        sum_new = sum(c["new_contrib"] for c in raised)
        sum_old = sum(c["old_contrib"] for c in raised)
        be["share"] = sum_change / sum_new if sum_new > 0 else None
        be["sum_change"], be["sum_new"], be["sum_old"] = sum_change, sum_new, sum_old
        be["raised_revenue_now"] = sum(c["fee"] * c["units_year"] for c in raised)
        be["raised_revenue_new"] = sum((c["last"]) * c["units_year"] for c in raised)

        def walk(order):
            net, rows, count, breaker = sum_change, [], 0, None
            for c in order:
                net = net - c["run_rate"] - c["old_contrib"]
                rows.append((c["name"], net))
                if net >= -0.005 and breaker is None:
                    count += 1
                elif breaker is None:
                    breaker = c["name"]
            return rows, count, breaker

        small_first = sorted(raised, key=lambda c: (c["new_contrib"], c["name"]))
        large_first = sorted(raised, key=lambda c: (-c["new_contrib"], c["name"]))
        be["small_rows"], be["small_count"], be["small_breaker"] = walk(small_first)
        be["large_rows"], be["large_count"], be["large_breaker"] = walk(large_first)
        be["small_order"] = [c["name"] for c in small_first]
        be["large_order"] = [c["name"] for c in large_first]
        be["loss_table"] = [(s, (1 - s) * sum_new - sum_old) for s in (0, 0.05, 0.10, 0.15, 0.20, 0.25)]
        be["lumpy"] = len(raised) <= 10
    # ---- scenarios default: nobody leaves
    scen = {"net12": tot["cash12"], "net_run": tot["run_rate"]}

    # ---- outcomes (return run)
    outcomes = outcomes_calc(inp, clients, st, dec, send, window_end, today, hour_value, needs, flags)

    # ---- blanket check
    if inp.get("founder_rise"):
        fr = pct_in(inp["founder_rise"], dec, "the rise you named", cap)
        held = [c for c in clients if c["segment"] == "Hold" and c["rate_now"] and anchor_rate]
        if held:
            parts = [f"{c['name']} ({st.money(c['rate_now'])} an hour against your {st.money(anchor_rate)})" for c in held]
            flags.append(f"A flat {st.pct(fr, 0)} on everyone would also have raised " + ", ".join(parts)
                         + "; the plan holds " + ("it" if len(held) == 1 else "them") + f" and uses {st.pct(fr, 0)} "
                         "as the biggest step for everyone else.")
    nohours = [c["name"] for c in clients if not c["hours"] and c["segment"] not in ("Hold",) and c["target_given"] is None]
    if nohours and not blanket:
        needs.append("[NEED: hours a month for " + ", ".join(nohours) + "] they get a flat step of the cap, marked "
                     "\"hours not given\"; with hours they would be planned like the rest")
    for c in clients:
        for q in c.get("asks", []):
            flags.append(q)

    early = [c for c in clients if c.get("start_note") and c["segment"] != "Hold"]
    if early:
        grp = {}
        for c in early:
            grp.setdefault((c["eff1"], D.notice_text(c["notice"]), c["notice_src"]), []).append(c["name"])
        parts = [f"{st.d(e)} for {_names(n)} ({nt} notice, {src})" for (e, nt, src), n in sorted(grp.items())]
        flags.append(f"You asked for {st.d(start_floor)}. Notice and renewal terms put the earliest dates at "
                     + "; ".join(parts) + ". The letters use those dates, never an earlier one.")
    ls = [c for c in clients if c.get("latest_send") and c["segment"] != "Hold"]
    if ls:
        by = {}
        for c in ls:
            by.setdefault((c["latest_send"], c["eff1"]), []).append(c["name"])
        for (lsd, e1), nm in sorted(by.items()):
            notes.append(f"To keep {st.d(e1)} for {_names(nm)}, the letters can go as late as {st.d(lsd, weekday=True)}.")
    if tax != "before":
        notes.append("Fees are as supplied (tax status unconfirmed). A percentage step is the same either way; if these "
                     "fees include tax, the cash figures are overstated by that tax. Ask your accountant whether they "
                     "are before tax.")

    res = {
        "version": VERSION, "business": inp.get("business") or "", "founder": inp.get("founder_name") or "",
        "sign_off": inp.get("sign_off") or inp.get("founder_name") or "", "currency": inp.get("currency") or "",
        "send": send.isoformat(), "send_assumed": send_assumed, "return_run": return_run, "window_end": window_end.isoformat(),
        "window_months": window_months, "today": today.isoformat(),
        "cap": cap, "cap_given": bool(inp.get("step_cap")), "closure": closure, "gap_months": gap_months, "rounding": [small, large, threshold],
        "anchor_rate": anchor_rate, "anchor_src": anchor_src, "anchor_text": anchor_text,
        "new_client_fee": ncf, "new_client_hours": nch, "new_client_per": ncf_per, "blanket": blanket,
        "fee_word": fee_word, "tax": tax, "working_days": inp.get("working_days") or "mon-fri", "hour_value": hour_value, "billing_day": billing_day,
        "notice_default": D.notice_text(notice_default), "tenure_years": tenure_years,
        "style": vars(st), "country": (inp.get("country") or "").upper(), "paper": loc["paper"],
        "totals": tot, "break_even": be, "scenarios": scen, "outcomes": outcomes,
        "flags": flags, "needs": needs, "notes": notes, "injected": injected,
        "clients": [client_out(c, st) for c in clients],
    }
    res["selfcheck"] = selfcheck(clients, be)
    if not res["selfcheck"]["ok"]:
        raise Stop("internal check failed: the break-even did not match a brute-force check (" +
                   "; ".join(res["selfcheck"]["problems"]) + "). Nothing was built.")
    return res, st, clients


def client_out(c, st):
    keep = ["name", "per", "fee", "hours", "cost", "units_year", "units_per_bill", "every", "hours_unit", "rate_now",
            "target", "target_src", "segment", "why", "cap", "step1", "step2", "last", "gap", "steps_to_close",
            "change_unit", "raised", "notice_src", "align", "billing_day", "call_first", "call_why", "reason",
            "reason_src", "reason_key", "letter", "hold_why", "n1", "n2", "cash12", "run_rate", "new_contrib",
            "old_contrib", "lost12", "be_share", "annual_fee", "tenure", "since_year", "scope_b_hours", "extras_rate",
            "rate_a", "rate_b", "deep_gap", "ppy", "billing_months"]
    out = {k: c.get(k) for k in keep}
    out["notice"] = D.notice_text(c["notice"])
    out["notice_days_or_months"] = list(c["notice"])
    for k in ("eff1", "eff2", "notice_ends"):
        out[k] = c[k].isoformat() if c.get(k) else None
    out["contact"] = c["raw"].get("contact") or ""
    out["same_line"] = c["raw"].get("same_line") or ""
    out["gentle"] = bool(c["raw"].get("gentle"))
    out["term_end"] = c["term_end_d"].isoformat() if c.get("term_end_d") else None
    out["scope_b_src"] = c.get("scope_b_src")
    out["fixed"] = bool(c["fixed_steps"])
    return out


# ====================================================================== outcomes
def schedule_cash(c, send, window_end, fee_at):
    """Cash over the window for a fee schedule fee_at(date) -> fee or None (gone)."""
    total = 0.0
    if c["per"] == "project":
        return None
    for b in c["bills"] or D.billing_dates(send, window_end, c["every"], c["billing_day"], c["billing_months"]):
        f = fee_at(b)
        if f is not None:
            total += f * c["units_per_bill"]
    return total


def outcomes_calc(inp, clients, st, dec, send, window_end, today, hour_value, needs, flags):
    outs = inp.get("outcomes") or []
    if not outs:
        return None
    by = {re.sub(r"[^a-z0-9]", "", c["name"].lower()): c for c in clients}
    rows, exceptions = [], []
    plan_total, real_total, refill = 0.0, 0.0, 0.0
    real_run = 0.0
    seen = set()
    for o in outs:
        key = re.sub(r"[^a-z0-9]", "", str(o.get("client", "")).lower())
        c = by.get(key)
        if not c:
            raise Stop(f"outcome for '{o.get('client')}' does not match a client in the plan",
                       ask=f"Which client is '{o.get('client')}'?")
        seen.add(key)
        result = str(o.get("result") or "pending").lower()
        if result not in ("accepted", "countered", "left", "pending", "held"):
            raise Stop(f"{c['name']}: result '{result}' not known", ask=f"Did {c['name']} accept, counter or leave?")
        old = c["fee"]
        if c.get("bills") is None or (not c["bills"] and c["per"] != "project"):
            c["bills"] = D.billing_dates(send, window_end, c["every"], c["billing_day"], c["billing_months"])

        def plan_fee(b, c=c):
            if c["segment"] == "Hold" or c["step1"] is None:
                return c["fee"]
            if c["eff2"] and b >= c["eff2"]:
                return c["step2"]
            if b >= c["eff1"]:
                return c["step1"]
            return c["fee"]
        base = schedule_cash(c, send, window_end, lambda b: old) or 0.0
        planned = (schedule_cash(c, send, window_end, plan_fee) or 0.0) - base
        terms = []
        if result == "countered":
            for t in o.get("terms") or []:
                f = money_in(t.get("fee"), dec, f"{poss(c['name'])} agreed fee")
                fr = D.parse_date(t.get("from"), st.order, today) if t.get("from") else c["eff1"]
                terms.append((fr, f))
            if not terms:
                raise Stop(f"{c['name']} countered but no terms were given",
                           ask=f"What did {c['name']} agree to pay, and from when?")
            terms.sort()
        end = D.parse_date(o["end_date"], st.order, today) if (result == "left" and o.get("end_date")) else None
        if result == "left" and not end:
            end = c["eff1"] - timedelta(days=1)

        def real_fee(b, c=c, result=result, terms=terms, end=end):
            if result in ("accepted", "pending"):
                return plan_fee(b)
            if result == "held":
                return old
            if result == "left":
                return old if b <= end else None
            f = old
            for fr, fee in terms:
                if b >= fr:
                    f = fee
            return f
        realised = (schedule_cash(c, send, window_end, real_fee) or 0.0) - base
        last_real = real_fee(window_end - timedelta(days=1))
        if_paid_new = 0.0
        if result == "left" and end:  # convention: a leaver is counted at the old fee up to their end date
            if_paid_new = (schedule_cash(c, send, window_end,
                                         lambda b, c=c, end=end: plan_fee(b) if b <= end else None) or 0.0) \
                - (schedule_cash(c, send, window_end, lambda b, end=end: old if b <= end else None) or 0.0)
        if result == "left":
            rr = -c["old_contrib"]
            freed = 0.0
            if hour_value and c["hours"]:
                months_gone = sum(c["units_per_bill"] * UNIT_MONTHS.get(c["per"], 1)
                                  for b in c["bills"] if b > end)
                freed = c["hours"] * hour_value * months_gone
            refill += freed
        else:
            rr = ((last_real or old) - old) * c["units_year"]
            freed = 0.0
        plan_total += planned
        real_total += realised
        real_run += rr
        row = {"client": c["name"], "result": result, "said": o.get("said") or "", "planned12": planned,
               "realised12": realised, "diff": realised - planned, "run_rate": rr, "freed_if_refilled": freed,
               "terms": [(a.isoformat(), b) for a, b in terms], "end": end.isoformat() if end else None,
               "agreed_fee": last_real, "if_paid_new": if_paid_new}
        rows.append(row)
        if result == "countered":
            until = o.get("until")
            until_d = D.parse_date(until, st.order, today) if until else None
            if until_d is None:
                first_from = terms[0][0]
                if first_from > c["eff1"]:
                    until_d = first_from - timedelta(days=1)
                else:
                    until_d = D.add_months(c["eff1"], 12) - timedelta(days=1)
            what = o.get("conceded") or ("; ".join(f"{st.money(f)} from {st.d(fr)}" for fr, f in terms))
            exceptions.append({"client": c["name"], "what": what, "until": until_d.isoformat(),
                               "cost": planned - realised, "approved": o.get("approved") or "you"})
    for c in clients:
        key = re.sub(r"[^a-z0-9]", "", c["name"].lower())
        if key not in seen and c["raised"]:
            flags.append(f"No outcome given for {c['name']}; counted as planned (pending).")
    # next wave
    nxt = []
    for c in clients:
        o = next((r for r in rows if re.sub(r"[^a-z0-9]", "", r["client"].lower())
                  == re.sub(r"[^a-z0-9]", "", c["name"].lower())), None)
        res_ = o["result"] if o else ("held" if c["segment"] == "Hold" else "pending")
        if res_ == "left":
            continue
        agreed = (o["agreed_fee"] if o else None) or c["last"] or c["fee"]
        last_eff = c["eff2"] or c["eff1"]
        if o and o["terms"]:
            last_eff = max(last_eff, date.fromisoformat(o["terms"][-1][0]))
        review = D.add_months(last_eff, 12) if last_eff else None
        gap = (c["target"] - agreed) if c["target"] is not None else None
        if c["segment"] == "Hold":
            nxt.append({"client": c["name"], "when": review.isoformat() if review else None, "gap": 0,
                        "why": "held: check again at your annual review"})
        elif gap and gap > 0.5:
            nxt.append({"client": c["name"], "when": review.isoformat() if review else None, "gap": gap,
                        "why": f"still {st.money(gap)} below target after the agreed fee of {st.money(agreed)}"})
    nxt.sort(key=lambda r: (-(r["gap"] or 0)))
    return {"rows": rows, "planned12": plan_total, "realised12": real_total, "diff": real_total - plan_total,
            "real_run": real_run, "refill": refill, "exceptions": exceptions, "next_wave": nxt}


# ====================================================================== self-check
def selfcheck(clients, be):
    problems = []
    raised = [c for c in clients if c["raised"]]
    if raised and be.get("share") is not None:
        s = be["share"]
        net = (1 - s) * be["sum_new"] - be["sum_old"]
        if abs(net) > 0.01:
            problems.append(f"share does not level the plan (net {net:.2f})")
        sum_fee_old = sum(c["fee"] * c["units_year"] for c in raised)
        d = be["sum_change"] / sum_fee_old
        cm = be["sum_old"] / sum_fee_old
        if abs(d / (cm + d) - s) > 1e-9:
            problems.append("share differs from d over (CM plus d)")
        if len(raised) <= 12:
            best_keep, worst_break = 0, None
            for k in range(len(raised) + 1):
                for sub in itertools.combinations(raised, k):
                    net = be["sum_change"] - sum(c["run_rate"] + c["old_contrib"] for c in sub)
                    if net >= -0.005:
                        best_keep = max(best_keep, k)
                    elif worst_break is None or k < worst_break:
                        worst_break = k
            if best_keep != be["small_count"]:
                problems.append(f"smallest-first count {be['small_count']} but brute force allows {best_keep}")
            exp_large = (worst_break - 1) if worst_break is not None else len(raised)
            if exp_large != be["large_count"]:
                problems.append(f"largest-first count {be['large_count']} but brute force gives {exp_large}")
    for c in clients:
        if c["step1"] is not None and c["segment"] not in ("Hold", "Price to keep") and not c["fixed_steps"]:
            if c["step1"] > c["fee"] * (1 + c["cap"]) + 0.01:
                problems.append(f"{c['name']} step 1 above the cap")
            if c["step2"] and c["step2"] > c["step1"] * (1 + c["cap"]) + 0.01:
                problems.append(f"{c['name']} step 2 above the cap")
            if c["target"] is not None and c["last"] > c["target"] + 0.01:
                problems.append(f"{c['name']} above target")
            if c["step1"] < c["fee"] - 0.01:
                problems.append(f"{c['name']} lowered")
    return {"ok": not problems, "problems": problems, "subsets_checked": min(len(raised), 12)}


# ====================================================================== printing
def unit_word(c):
    return UNIT_WORDS.get(c["per"], "")


def headline(res, st):
    t, be = res["totals"], res["break_even"]
    lines = []
    n = len(res["clients"])
    raised = [c for c in res["clients"] if c["raised"]]
    held = [c["name"] for c in res["clients"] if c["segment"] == "Hold"]
    lines.append(f"{n} client{'s' if n != 1 else ''}: {len(raised)} raised, {len(held)} held"
                 + (f" ({', '.join(held)})" if held else "") + ".")
    lines.append(f"Cash added in the next {res['window_months']} months, after notice: {st.money(t['cash12'])}. "
                 f"Full-year run rate once every step lands: {st.money(t['run_rate'])} a year.")
    if be.get("share") is not None and len(raised) == 1:
        c = raised[0]
        lines.append(f"Break-even: the rise leaves you level as long as the chance {c['name']} leaves over it is below "
                     f"{st.pct(be['share'])}. If they stay, you gain {st.money(c['run_rate'])} a year. If they go, you "
                     f"lose {st.money(c['old_contrib'])} a year.")
        return lines
    if be.get("share") is not None:
        s = be["share"]
        one_in = round(1 / s) if s > 0 else None
        lines.append(f"Break-even: you can lose {st.pct(s)} of the revenue you are raising"
                     + (f" (about 1 client in {one_in})" if one_in and one_in >= 2 else "") + " and still be level.")
        sb, lb = be["small_breaker"], be["large_breaker"]
        so = be["small_order"]
        if be["small_count"] > 0:
            kept = so[:be["small_count"]]
            lines.append(f"Smallest first: lose {_names(kept)} and you are still ahead"
                         + (f"; lose {sb} as well and you are behind." if sb else "; even losing all of them leaves you level."))
        else:
            lines.append(f"Smallest first: lose {so[0]} and you are already behind.")
        if be["large_count"] == 0:
            lines.append(f"Largest first: lose {be['large_order'][0]} and you are behind.")
        else:
            lines.append(f"Largest first: you can lose {_names(be['large_order'][:be['large_count']])} and still be "
                         f"level" + (f"; lose {lb} as well and you are behind." if lb else "."))
        if be.get("lumpy"):
            lines.append(f"With {len(raised)} client{'s' if len(raised) != 1 else ''} being raised, each departure is a "
                         f"big step: plan on the named clients, not the percentage.")
    lines += option_b_lines(res, st)
    return lines


def option_b_lines(res, st):
    """Cash counts Option A for a scope reset (it applies if the client does not reply); say what B takes off."""
    out = []
    for c in res["clients"]:
        if c["segment"] == "Reset the scope" and c["raised"] and c.get("scope_b_hours"):
            out.append(f"The figures count Option A for {c['name']}, which applies if they do not reply. If they choose "
                       f"Option B, take {st.money(c['cash12'])} off the next 12 months and {st.money(c['run_rate'])} off "
                       f"the run rate; you get "
                       f"{st.num(c['hours'] - c['scope_b_hours'], 0 if float(c['hours'] - c['scope_b_hours']).is_integer() else 1)}"
                       f" hours a month back instead.")
    return out


def _names(xs):
    xs = list(xs)
    if len(xs) <= 1:
        return "".join(xs)
    return ", ".join(xs[:-1]) + " and " + xs[-1]


def leaver_line(r, st):
    return (f"{r['client']} is counted at the old fee until {st.d(date.fromisoformat(r['end']))}. If they paid the new "
            f"fee on their invoices before then, add {st.money(r['if_paid_new'])}.")


def outcome_verdict(o, st):
    gained = sum(r["realised12"] for r in o["rows"] if r["realised12"] > 0)
    lost = [r for r in o["rows"] if r["result"] == "left"]
    lost_sum = -sum(r["realised12"] for r in lost)
    if not lost:
        return (f"Nobody left. The rises that landed add {st.money(gained)} in the window, "
                f"{st.money(o['planned12'] - o['realised12'])} short of the plan because of what was conceded.")
    names = _names([r["client"] for r in lost])
    if lost_sum > gained:
        return (f"Losing {names} cost {st.money(lost_sum)} in the window; the rises that landed added "
                f"{st.money(gained)}. The departure cost more than the rise added: the window is "
                f"{st.money(o['realised12'])} on doing nothing, before any refill of the freed hours.")
    most = " That departure took most of what the rise added." if lost_sum >= 0.75 * gained else ""
    return (f"Losing {names} cost {st.money(lost_sum)} in the window; the rises that landed added {st.money(gained)}, "
            f"so you are {st.money(o['realised12'])} ahead of doing nothing, before any refill of the freed hours.{most}")


def print_plan(res, st):
    print(f"ANCHOR: {res['anchor_text'] or 'none (flat steps)'}")
    print(f"SEND: {st.d(date.fromisoformat(res['send']), weekday=True)}{' (assumed: today)' if res['send_assumed'] else ''}; "
          f"window to {st.d(date.fromisoformat(res['window_end']))}")
    print(f"RULES: biggest step {st.pct(res['cap'])}, one step when it reaches {st.pct(res['closure'], 0)} of target, "
          f"second step {res['gap_months']} months later, rounded down to {st.num(res['rounding'][0], 0)} below "
          f"{st.num(res['rounding'][2], 0)} and {st.num(res['rounding'][1], 0)} from it")
    print("PLAN:")
    for c in res["clients"]:
        line = f"  {c['name']}: {c['segment']} ({c['why']})"
        if c["segment"] != "Hold" and c["step1"] is not None:
            line += f"; {st.money(c['fee'])} to {st.money(c['step1'])} {unit_word(c)} from {st.d(date.fromisoformat(c['eff1']), weekday=True)}"
            if c["step2"]:
                line += f", then {st.money(c['step2'])} from {st.d(date.fromisoformat(c['eff2']), weekday=True)}"
            if c["gap"]:
                line += f"; gap left {st.money(c['gap'])}" + (
                    f" ({c['steps_to_close']} further step{'s' if c['steps_to_close'] != 1 else ''} at review to come within "
                    f"{st.pct(1 - res['closure'], 0)})" if c["steps_to_close"] else
                    f" (within {st.pct(1 - res['closure'], 0)} of target: no further step planned)")
            line += f"; 12 months {st.money(c['cash12'])}, run rate {st.money(c['run_rate'])}"
            line += f"; notice {c['notice']} ({c['notice_src']}); letter {c['letter']}"
            if c["call_first"]:
                line += " ; CALL FIRST (" + ", ".join(c["call_why"]) + ")"
        elif c["segment"] == "Hold":
            line += f"; stays at {st.money(c['fee'])}, no letter"
        print(line)
        if c["reason"] and c["segment"] != "Hold":
            print(f"    reason: {c['reason']} ({c['reason_src']})")
        if c["hold_why"] and c["letter"] == "HOLD":
            print(f"    HOLD: {c['hold_why']}")
    print("HEADLINE:")
    for ln in headline(res, st):
        print("  " + ln)
    for ln in res["notes"]:
        print("NOTE:", ln)
    for ln in res["flags"]:
        print("FLAG:", ln)
    for ln in res["needs"]:
        print("NEED:", ln)
    o = res["outcomes"]
    if o:
        print("OUTCOMES:")
        for r in o["rows"]:
            print(f"  {r['client']}: {r['result']}; realised {st.money(r['realised12'])} against planned "
                  f"{st.money(r['planned12'])}")
            if r.get("if_paid_new"):
                print(f"    {leaver_line(r, st)}")
        print(f"  Realised in the window: {st.money(o['realised12'])} against {st.money(o['planned12'])} planned "
              f"(difference {st.money(o['diff'])}). Run rate now {st.money(o['real_run'])} a year.")
        if o["refill"]:
            print(f"  Only if you refill the freed hours at {st.money(res['hour_value'])} an hour: "
                  f"{st.money(o['refill'])} in the window.")
        for e in o["exceptions"]:
            print(f"  EXCEPTION: {e['client']}: {e['what']} (ends {st.d(date.fromisoformat(e['until']))}); costs "
                  f"{st.money(e['cost'])} against the plan in the window")
        print("  VERDICT: " + outcome_verdict(o, st))
        for n in o["next_wave"]:
            print(f"  NEXT: {n['client']}: {n['why']}" + (f"; review {st.d(date.fromisoformat(n['when']))}" if n["when"] else ""))
    sc = res["selfcheck"]
    n_ = sc['subsets_checked']
    print(f"SELF-CHECK: break-even matched a brute-force check over {n_} raised client{'s' if n_ != 1 else ''}.")


# ====================================================================== workbook
def _dt(x):
    return x if isinstance(x, date) else date.fromisoformat(x)


def build_workbook(res, st, clients, path):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter as L
    wb = Workbook()
    yellow = PatternFill("solid", fgColor="FFF2CC")
    head = Font(bold=True)
    mfmt = st.xl_money()
    pfmt = "0.0%"
    wrap = Alignment(wrap_text=True, vertical="top")
    am = st.american

    def W(ws, ref, v, fmt=None, bold=False, fill=None):
        ws[ref] = v
        if fmt:
            ws[ref].number_format = fmt
        if bold:
            ws[ref].font = head
        if fill:
            ws[ref].fill = fill
        return ws[ref]

    # ---------------- Assumptions (built first so other sheets can refer to it)
    sa = wb.active
    sa.title = "Summary"
    ass = wb.create_sheet("Plan")
    sbe = wb.create_sheet("Break-even")
    ssc = wb.create_sheet("Scenarios")
    sex = wb.create_sheet("Exceptions")
    sou = wb.create_sheet("Outcomes")
    sas = wb.create_sheet("Assumptions")
    sp = ass
    A = sas
    W(A, "A1", "Assumptions and sources", bold=True)
    W(A, "A2", "Yellow cells are inputs. Change one and the Plan, Break-even and Scenarios update. Re-run the "
               "skill to re-sort clients into groups or re-date the letters.")
    rows = [
        ("Biggest single step (step cap)", res["cap"], pfmt, True, "you said" if res.get("cap_given") else "default; change it if you like"),
        ("One step when it reaches this share of target", res["closure"], pfmt, True, "default; change it if you like"),
        ("Round down to (below the threshold)", res["rounding"][0], "0", True, "default; change it if you like"),
        ("Round down to (from the threshold)", res["rounding"][1], "0", True, "default; change it if you like"),
        ("Rounding threshold", res["rounding"][2], "0", True, "default; change it if you like"),
        ("Anchor: what an hour should bring in", res["anchor_rate"] if res["anchor_rate"] else "", mfmt, True,
         res["anchor_text"] or "none given: flat steps"),
        ("Value of an hour, for the refill view", res["hour_value"] if res["hour_value"] else "", mfmt, True,
         "you said" if res["hour_value"] else "not given"),
        ("Months between step 1 and step 2", res["gap_months"], "0", False, "default"),
        ("Send date", st.d(date.fromisoformat(res["send"]), weekday=True), None, False,
         "assumed: today. Confirm it" if res["send_assumed"] else "you said"),
        ("Cash window", f"{res['window_months']} months from the send date, to {st.d(date.fromisoformat(res['window_end']))}",
         None, False, "default"),
        ("Notice when your contract is unknown", res["notice_default"], None, False,
         "planning default, not your contract"),
        ("Reply-by date in the letters", "two weeks before the effective date, never sooner than a week after sending",
         None, False, "default"),
        ("Billing day", res["billing_day"], "0", False, "you said or default"),
        ("Call first", f"tenure of at least {st.num(res['tenure_years'], 0)} years, or a top quarter client by annual fee",
         None, False, "default"),
        ("Currency and number style", f"{res['currency'] or 'as you wrote them'}; written like {st.money(1234.5 if st.decimals else 1250)}",
         None, False, "from your figures"),
        ("Fees", "as entered, before any sales tax" if res["tax"] == "before" else
         "as supplied (tax status unconfirmed)", None, False,
         "you said" if res["tax"] == "before" else "ask your accountant whether these include tax"),
    ]
    refs = {}
    for i, (lab, val, fmt, inp_, src) in enumerate(rows, start=4):
        W(A, f"A{i}", lab)
        c = W(A, f"B{i}", val, fmt, fill=yellow if inp_ else None)
        W(A, f"C{i}", src)
        refs[lab] = f"Assumptions!$B${i}"
    r = 4 + len(rows) + 1
    W(A, f"A{r}", "The rules, in plain words", bold=True)
    rules = [
        "Each client's target is what your anchor pays for that client's hours (plus any direct cost). Clients at or above it are held and told nothing.",
        "A rise is never bigger than the step cap in one go. If one capped step reaches the closure share of target, one step; otherwise two steps, the second six months later, each capped. Any gap left goes to your annual review.",
        "New fees are rounded down, never above the cap or the target, never below today's fee.",
        "The effective date is the first billing date on or after the notice ends (rolled to a month or quarter end where your notice says so), or the renewal date where the price can only change at renewal.",
        "Cash in the window counts only what is billed after each effective date. The run rate is the full year once every step lands.",
        "Break-even counts contribution: the fee less the direct costs you gave. Overheads stay when a client goes, so they are left out.",
        "Planning, not advice. Check what your contracts and the rules where you and your clients are say about changing a price and giving notice; if your clients are individuals rather than businesses, check that too.",
        "Enter fees before any sales tax (VAT, GST or similar); ask your accountant whether you need to charge it.",
    ]
    for j, t in enumerate(rules, start=r + 1):
        W(A, f"A{j}", localise(t, am)).alignment = wrap
        A.merge_cells(f"A{j}:C{j}")
        A.row_dimensions[j].height = 30
    A.column_dimensions["A"].width = 48
    A.column_dimensions["B"].width = 22
    A.column_dimensions["C"].width = 60
    CAP, CLO = refs["Biggest single step (step cap)"], refs["One step when it reaches this share of target"]
    SM, LG, TH = (refs["Round down to (below the threshold)"], refs["Round down to (from the threshold)"],
                  refs["Rounding threshold"])
    ANC, HV = refs["Anchor: what an hour should bring in"], refs["Value of an hour, for the refill view"]

    # ---------------- Plan
    cols = ["Client", "Billed", "Fee per", "Current fee", "Hours a month", "Direct cost per fee", "Fee units a year",
            "Hours per fee", "Hourly rate now", "Target fee", "Target from", "Group", "Why", "Reason in the letter",
            "Reason from", "Step cap", "Step 1 fee", "Step 1 date", "Step 2 fee", "Step 2 date", "Gap left to target",
            "Further steps at review", "Notice", "Notice source", "Call first", "Run-rate change a year",
            "Fee units billed at step 1 in window", "Fee units billed at step 2 in window", "Next 12 months cash",
            "Letter", "HOLD because", "Your status", "New contribution a year", "Old contribution a year",
            "Break-even share", "Raised (1 or 0)", "Contribution lost in window if they leave"]
    ci = {n: i + 1 for i, n in enumerate(cols)}
    col = {n: L(i) for n, i in ci.items()}
    for n, i in ci.items():
        W(sp, f"{L(i)}1", n, bold=True).alignment = wrap
    sp.row_dimensions[1].height = 45
    sp.freeze_panes = "B2"
    plan_rows = {}
    for k, c in enumerate(clients, start=2):
        plan_rows[c["name"]] = k
        cl = lambda n: f"{col[n]}{k}"  # noqa: E731
        W(sp, cl("Client"), c["name"])
        W(sp, cl("Billed"), "per project" if c["per"] == "project" else
          {1: "monthly", 3: "quarterly", 12: "yearly"}.get(c["every"], f"every {c['every']} months"))
        W(sp, cl("Fee per"), c["per"])
        W(sp, cl("Current fee"), c["fee"], mfmt, fill=yellow)
        W(sp, cl("Hours a month"), c["hours"] if c["hours"] else "", "0.0", fill=yellow)
        W(sp, cl("Direct cost per fee"), c["cost"], mfmt, fill=yellow)
        W(sp, cl("Fee units a year"), c["units_year"], "0.##")
        mul = 1 if c["per"] == "project" else UNIT_MONTHS[c["per"]]
        W(sp, cl("Hours per fee"), f'=IF({cl("Hours a month")}="","",{cl("Hours a month")}*{mul})', "0.0")
        W(sp, cl("Hourly rate now"), f'=IF({cl("Hours per fee")}="","",({cl("Current fee")}-{cl("Direct cost per fee")})/{cl("Hours per fee")})', mfmt)
        if c["target_given"] is not None:
            W(sp, cl("Target fee"), c["target_given"], mfmt, fill=yellow)
        elif c["target"] is not None:
            W(sp, cl("Target fee"), f'=IF(OR({ANC}="",{cl("Hours per fee")}=""),"",{ANC}*{cl("Hours per fee")}+{cl("Direct cost per fee")})', mfmt)
        else:
            W(sp, cl("Target fee"), "")
        W(sp, cl("Target from"), c["target_src"] or "hours not given")
        W(sp, cl("Group"), c["segment"])
        W(sp, cl("Why"), c["why"])
        W(sp, cl("Reason in the letter"), c["reason"] or ("" if not c["raised"] else "[NEED: one true reason]"))
        W(sp, cl("Reason from"), c["reason_src"])
        if c["cap"] == res["cap"]:
            W(sp, cl("Step cap"), f"={CAP}", pfmt, fill=yellow)
        else:
            W(sp, cl("Step cap"), c["cap"], pfmt, fill=yellow)
        D_, T_, M_ = cl("Current fee"), cl("Target fee"), cl("Step cap")

        def rnd(x, floor_ref):
            unit = f"IF(ROUND({x},6)<{TH},{SM},{LG})"
            fl = f"FLOOR(ROUND({x},6),{unit})"
            return f"IF({fl}<={floor_ref},ROUNDDOWN(ROUND({x},6),0),{fl})"
        seg = c["segment"]
        if c["fixed_steps"] or (seg == "Price to keep" and c["keep_fee"] is not None):
            W(sp, cl("Step 1 fee"), c["step1"] if c["step1"] is not None else "", mfmt, fill=yellow)
        elif seg == "Hold":
            W(sp, cl("Step 1 fee"), f"={D_}", mfmt)
        elif seg == "Price to keep":
            if c["step1"] is None:
                W(sp, cl("Step 1 fee"), "", mfmt, fill=yellow)
            else:
                W(sp, cl("Step 1 fee"), f"=MAX({D_},{rnd(T_, D_)})", mfmt)
        else:
            x1 = f'IF({T_}="",{D_}*(1+{M_}),MIN({T_},{D_}*(1+{M_})))'
            W(sp, cl("Step 1 fee"), "=" + rnd(x1, D_), mfmt)
        S1 = cl("Step 1 fee")
        W(sp, cl("Step 1 date"), st.d(_dt(c["eff1"]), weekday=True) if (c["eff1"] and seg != "Hold") else "")
        if c["step2"] is not None:
            if c["fixed_steps"]:
                W(sp, cl("Step 2 fee"), c["step2"], mfmt, fill=yellow)
            else:
                x2 = f'IF({T_}="",{S1}*(1+{M_}),MIN({T_},{S1}*(1+{M_})))'
                W(sp, cl("Step 2 fee"), "=" + rnd(x2, S1), mfmt)
            W(sp, cl("Step 2 date"), st.d(_dt(c["eff2"]), weekday=True))
        else:
            W(sp, cl("Step 2 fee"), "")
            W(sp, cl("Step 2 date"), "")
        S2 = cl("Step 2 fee")
        LAST = f'IF({S2}="",IF({S1}="",{D_},{S1}),{S2})'
        W(sp, cl("Gap left to target"), f'=IF({T_}="","",MAX(0,{T_}-{LAST}))', mfmt)
        W(sp, cl("Further steps at review"), c["steps_to_close"] if c["gap"] else 0, "0")
        W(sp, cl("Notice"), c["notice"] if isinstance(c["notice"], str) else D.notice_text(c["notice"]))
        W(sp, cl("Notice source"), c["notice_src"])
        W(sp, cl("Call first"), ("yes: " + ", ".join(c["call_why"])) if c["call_first"] else "no")
        U = cl("Fee units a year")
        W(sp, cl("Run-rate change a year"), f"=({LAST}-{D_})*{U}", mfmt)
        W(sp, cl("Fee units billed at step 1 in window"), c["n1"], "0.##")
        W(sp, cl("Fee units billed at step 2 in window"), c["n2"], "0.##")
        N1, N2 = cl("Fee units billed at step 1 in window"), cl("Fee units billed at step 2 in window")
        W(sp, cl("Next 12 months cash"), f'=IF({S1}="",0,({S1}-{D_})*{N1})+IF({S2}="",0,({S2}-{D_})*{N2})', mfmt)
        W(sp, cl("Letter"), c["letter"])
        W(sp, cl("HOLD because"), c["hold_why"] if c["letter"] == "HOLD" else "")
        W(sp, cl("Your status"), "", fill=yellow)
        C_ = cl("Direct cost per fee")
        W(sp, cl("New contribution a year"), f"=({LAST}-{C_})*{U}", mfmt)
        W(sp, cl("Old contribution a year"), f"=({D_}-{C_})*{U}", mfmt)
        RAISED = cl("Raised (1 or 0)")
        W(sp, cl("Break-even share"), f'=IF({RAISED}=1,{cl("Run-rate change a year")}/{cl("New contribution a year")},"")', pfmt)
        W(sp, RAISED, f'=IF({LAST}>{D_}+0.004,1,0)', "0")
        W(sp, cl("Contribution lost in window if they leave"), f"=({D_}-{C_})*({N1}+{N2})", mfmt)
    last_row = 1 + len(clients)
    for n, i in ci.items():
        sp.column_dimensions[L(i)].width = 14 if n not in ("Client", "Reason in the letter", "Why", "HOLD because", "Reason from", "Target from", "Call first") else 30
    rng = lambda n: f"Plan!${col[n]}$2:${col[n]}${last_row}"  # noqa: E731
    tot_row = last_row + 2
    W(sp, f"A{tot_row}", "Totals", bold=True)
    for n in ("Run-rate change a year", "Next 12 months cash"):
        W(sp, f"{col[n]}{tot_row}", f"=SUM({col[n]}2:{col[n]}{last_row})", mfmt, bold=True)
    TOT12 = f"Plan!${col['Next 12 months cash']}${tot_row}"
    TOTRR = f"Plan!${col['Run-rate change a year']}${tot_row}"

    # ---------------- Break-even
    B = sbe
    be = res["break_even"]
    W(B, "A1", "Break-even: how many clients can leave and you are still level", bold=True)
    W(B, "A2", "Contribution is the fee less the direct costs you gave. Overheads stay when a client goes, so they are left out.")
    W(B, "A4", "Share of the raised revenue that can leave", bold=True)
    W(B, "B4", f'=IF(SUMIF({rng("Raised (1 or 0)")},1,{rng("New contribution a year")})=0,"",'
               f'SUMIF({rng("Raised (1 or 0)")},1,{rng("Run-rate change a year")})/'
               f'SUMIF({rng("Raised (1 or 0)")},1,{rng("New contribution a year")}))', pfmt, bold=True)
    W(B, "A6", "Per client: the largest share of that client that could go", bold=True)
    W(B, "A7", "Client", bold=True)
    W(B, "B7", "Break-even share", bold=True)
    rr = 8
    for c in clients:
        if c["raised"]:
            k = plan_rows[c["name"]]
            W(B, f"A{rr}", c["name"])
            W(B, f"B{rr}", f"=Plan!{col['Break-even share']}{k}", pfmt)
            rr += 1
    rr += 1
    order_cells = {}
    for title, key in (("Departures, smallest first", "small_order"), ("Departures, largest first", "large_order")):
        W(B, f"A{rr}", title, bold=True)
        W(B, f"B{rr}", "Net a year after this departure", bold=True)
        start = rr
        rr += 1
        W(B, f"A{rr}", "Nobody leaves")
        W(B, f"B{rr}", f"=SUMIF({rng('Raised (1 or 0)')},1,{rng('Run-rate change a year')})", mfmt)
        prev = f"B{rr}"
        rr += 1
        for name in be.get(key, []):
            k = plan_rows[name]
            W(B, f"A{rr}", name)
            W(B, f"B{rr}", f"={prev}-Plan!{col['Run-rate change a year']}{k}-Plan!{col['Old contribution a year']}{k}", mfmt)
            prev = f"B{rr}"
            order_cells.setdefault(key, []).append(f"B{rr}")
            rr += 1
        rr += 1
    W(B, f"A{rr}", "Loss table: share of the raised revenue that leaves", bold=True)
    W(B, f"B{rr}", "Net a year", bold=True)
    rr += 1
    loss_cells = []
    for s in (0, 0.05, 0.10, 0.15, 0.20, 0.25):
        W(B, f"A{rr}", s, "0%")
        W(B, f"B{rr}", f"=(1-A{rr})*SUMIF({rng('Raised (1 or 0)')},1,{rng('New contribution a year')})"
                       f"-SUMIF({rng('Raised (1 or 0)')},1,{rng('Old contribution a year')})", mfmt)
        loss_cells.append(f"B{rr}")
        rr += 1
    B.column_dimensions["A"].width = 50
    B.column_dimensions["B"].width = 26

    # ---------------- Scenarios
    S = ssc
    W(S, "A1", "Scenarios: put 1 in Leaves for anyone you think might go", bold=True)
    hdr = ["Client", "Leaves (1 or 0)", "Gain a year if they stay", "Contribution lost a year if they go",
           "Net a year", "Next 12 months gain if they stay", "Lost in the window if they go", "Net in the window",
           "Freed hours a year, only if you refill them"]
    for i, h in enumerate(hdr, start=1):
        W(S, f"{L(i)}3", h, bold=True).alignment = wrap
    S.row_dimensions[3].height = 45
    sr = 4
    scen_rows = {}
    for c in clients:
        if not c["raised"]:
            continue
        k = plan_rows[c["name"]]
        scen_rows[c["name"]] = sr
        W(S, f"A{sr}", c["name"])
        W(S, f"B{sr}", 0, "0", fill=yellow)
        W(S, f"C{sr}", f"=Plan!{col['Run-rate change a year']}{k}", mfmt)
        W(S, f"D{sr}", f"=Plan!{col['Old contribution a year']}{k}", mfmt)
        W(S, f"E{sr}", f"=(1-B{sr})*C{sr}-B{sr}*D{sr}", mfmt)
        W(S, f"F{sr}", f"=Plan!{col['Next 12 months cash']}{k}", mfmt)
        W(S, f"G{sr}", f"=Plan!{col['Contribution lost in window if they leave']}{k}", mfmt)
        W(S, f"H{sr}", f"=(1-B{sr})*F{sr}-B{sr}*G{sr}", mfmt)
        W(S, f"I{sr}", f'=IF({HV}="","",B{sr}*Plan!{col["Hours a month"]}{k}*12*{HV})', mfmt)
        sr += 1
    W(S, f"A{sr + 1}", "Total", bold=True)
    for cc in "EHI":
        W(S, f"{cc}{sr + 1}", f"=SUM({cc}4:{cc}{max(4, sr - 1)})" if sr > 4 else 0, mfmt, bold=True)
    SCEN_RUN, SCEN_12 = f"Scenarios!$E${sr + 1}", f"Scenarios!$H${sr + 1}"
    W(S, f"A{sr + 3}", "The freed hours column counts only if you fill those hours with other paid work at the value you gave. "
                       "It is left blank when you gave no value for an hour.")
    S.column_dimensions["A"].width = 30
    for cc in "BCDEFGHI":
        S.column_dimensions[cc].width = 17

    # ---------------- Exceptions
    X = sex
    W(X, "A1", "Exceptions: every concession, its end date and what it costs", bold=True)
    W(X, "A2", "A concession with no end date becomes the new fee. Log each one here.")
    for i, h in enumerate(["Client", "What was conceded", "Until", "Cost against the plan in the window", "Who approved"], start=1):
        W(X, f"{L(i)}4", h, bold=True)
    o = res["outcomes"]
    xr = 5
    if o and o["exceptions"]:
        for e in o["exceptions"]:
            k = plan_rows[e["client"]]
            W(X, f"A{xr}", e["client"])
            W(X, f"B{xr}", e["what"])
            W(X, f"C{xr}", st.d(date.fromisoformat(e["until"])))
            W(X, f"D{xr}", f"=Plan!{col['Next 12 months cash']}{k}-Outcomes!E{6 + [r['client'] for r in o['rows']].index(e['client'])}", mfmt)
            W(X, f"E{xr}", e["approved"])
            xr += 1
    else:
        first = next((c for c in clients if c["raised"] and c["segment"] not in ("Price to keep",)), None)
        if first:
            k = plan_rows[first["name"]]
            W(X, f"A{xr}", f"Example only, delete: {first['name']}")
            W(X, f"B{xr}", "today's fee held a further three months in return for a 12-month commitment")
            W(X, f"C{xr}", st.d(D.add_months(_dt(first["eff1"]), 3) - timedelta(days=1)))
            W(X, f"D{xr}", f"=(Plan!{col['Step 1 fee']}{k}-Plan!{col['Current fee']}{k})*3*Plan!{col['Fee units a year']}{k}/12", mfmt)
            W(X, f"E{xr}", "you")
    X.column_dimensions["A"].width = 34
    X.column_dimensions["B"].width = 50
    X.column_dimensions["C"].width = 22
    X.column_dimensions["D"].width = 22

    # ---------------- Outcomes
    O = sou
    W(O, "A1", "Outcomes: who accepted, countered or left", bold=True)
    W(O, "A2", "Blank on a first run. Tell the skill what happened and it fills this in and plans the next wave.")
    for i, h in enumerate(["Client", "Result", "New terms", "What they said", "Realised in the window",
                           "Planned in the window", "Realised less planned", "Run rate now a year"], start=1):
        W(O, f"{L(i)}5", h, bold=True)
    if o:
        for j, r_ in enumerate(o["rows"], start=6):
            k = plan_rows[r_["client"]]
            W(O, f"A{j}", r_["client"])
            W(O, f"B{j}", r_["result"])
            terms = "; ".join(f"{st.money(f)} from {st.d(date.fromisoformat(a))}" for a, f in r_["terms"])
            if r_["end"]:
                terms = f"finishes {st.d(date.fromisoformat(r_['end']))}"
            W(O, f"C{j}", terms)
            W(O, f"D{j}", r_["said"])
            W(O, f"E{j}", r_["realised12"], mfmt)
            W(O, f"F{j}", f"=Plan!{col['Next 12 months cash']}{k}", mfmt)
            W(O, f"G{j}", f"=E{j}-F{j}", mfmt)
            W(O, f"H{j}", r_["run_rate"], mfmt)
        endr = 6 + len(o["rows"])
        W(O, f"A{endr + 1}", "Total", bold=True)
        for cc in "EFGH":
            W(O, f"{cc}{endr + 1}", f"=SUM({cc}6:{cc}{endr - 1})", mfmt, bold=True)
        if o["refill"]:
            W(O, f"A{endr + 3}", f"Only if you refill the freed hours at {st.money(res['hour_value'])} an hour")
            W(O, f"E{endr + 3}", o["refill"], mfmt)
        nr = endr + 5
        W(O, f"A{nr}", "Next wave", bold=True)
        for j, n in enumerate(o["next_wave"], start=nr + 1):
            W(O, f"A{j}", n["client"])
            W(O, f"B{j}", st.d(date.fromisoformat(n["when"])) if n["when"] else "")
            W(O, f"C{j}", n["why"])
    for cc, wdt in zip("ABCDEFGH", (30, 12, 34, 34, 18, 18, 18, 18)):
        O.column_dimensions[cc].width = wdt

    # ---------------- Summary
    Sm = sa
    W(Sm, "A1", f"Price rise plan{(' for ' + res['business']) if res['business'] else ''}", bold=True).font = Font(bold=True, size=14)
    W(Sm, "A2", f"Letters go on {st.d(date.fromisoformat(res['send']), weekday=True)}"
                + (" (assumed: confirm the date)" if res["send_assumed"] else "")
                + f". Fees {'before any sales tax' if res['tax'] == 'before' else 'as supplied (tax status unconfirmed)'}.")
    W(Sm, "A4", f"Cash added in the next {res['window_months']} months, after notice", bold=True)
    W(Sm, "B4", f"={TOT12}", mfmt).font = Font(bold=True, size=13)
    W(Sm, "A5", "Full-year run rate once every step lands", bold=True)
    W(Sm, "B5", f"={TOTRR}", mfmt).font = Font(bold=True, size=13)
    W(Sm, "A6", "Share of the raised revenue that can leave and you are still level", bold=True)
    W(Sm, "B6", "='Break-even'!B4", pfmt).font = Font(bold=True, size=13)
    hl = headline(res, st)
    rr = 7
    for ln in hl[3:]:
        W(Sm, f"A{rr}", localise(ln, am))
        Sm.merge_cells(f"A{rr}:D{rr}")
        rr += 1
    W(Sm, f"A{rr}", "If your scenario guesses come true (Scenarios sheet)")
    W(Sm, f"B{rr}", f"={SCEN_12}", mfmt)
    W(Sm, f"C{rr}", "in the window")
    rr += 2
    W(Sm, f"A{rr}", "Clients by group", bold=True)
    W(Sm, f"B{rr}", "Clients", bold=True).alignment = Alignment(horizontal="right")
    W(Sm, f"C{rr}", "Run-rate change a year", bold=True).alignment = Alignment(horizontal="right")
    rr += 1
    for sgm in SEGMENTS:
        if any(c["segment"] == sgm for c in clients):
            W(Sm, f"A{rr}", sgm)
            W(Sm, f"B{rr}", f'=COUNTIF({rng("Group")},"{sgm}")', "0")
            W(Sm, f"C{rr}", f'=SUMIF({rng("Group")},"{sgm}",{rng("Run-rate change a year")})', mfmt)
            rr += 1
    rr += 1
    W(Sm, f"A{rr}", "Speak to these first", bold=True)
    rr += 1
    for c in first_five(res):
        W(Sm, f"A{rr}", c["name"])
        W(Sm, f"B{rr}", "call first" if c["call_first"] else "letter")
        W(Sm, f"C{rr}", ", ".join(c["call_why"]) or c["segment"])
        rr += 1
    rr += 1
    W(Sm, f"A{rr}", "Flags", bold=True)
    rr += 1
    flag_lines = [f"HOLD: {c['name']}: {c['hold_why']}" for c in res["clients"] if c["letter"] == "HOLD"]
    flag_lines += res["needs"] + res["flags"] + res["notes"]
    for ln in dict.fromkeys(flag_lines) or ["None"]:
        W(Sm, f"A{rr}", localise(ln, am)).alignment = wrap
        Sm.merge_cells(f"A{rr}:D{rr}")
        Sm.row_dimensions[rr].height = 15 * max(1, math.ceil(len(ln) / 105))
        rr += 1
    rr += 1
    W(Sm, f"A{rr}", "What moves the answer most", bold=True)
    rr += 1
    for ln in movers(res, st):
        W(Sm, f"A{rr}", localise(ln, am)).alignment = wrap
        Sm.merge_cells(f"A{rr}:D{rr}")
        Sm.row_dimensions[rr].height = 15 * max(1, math.ceil(len(ln) / 105))
        rr += 1
    rr += 1
    W(Sm, f"A{rr}", "Planning, not advice. Yellow cells on every sheet are inputs.")
    Sm.column_dimensions["A"].width = 62
    Sm.column_dimensions["B"].width = 18
    Sm.column_dimensions["C"].width = 30
    Sm.column_dimensions["D"].width = 20
    for ws in wb.worksheets:
        ws.page_setup.paperSize = ws.PAPERSIZE_LETTER if res["paper"] == "Letter" else ws.PAPERSIZE_A4
        ws.page_setup.orientation = "landscape"
    wb.properties.title = "Price rise plan"
    wb.properties.creator = "Made with Merigrove Price Rise Pack"
    wb.properties.description = "Made with Merigrove Price Rise Pack"
    wb.save(path)
    return {"plan_rows": plan_rows, "col": col, "tot_row": tot_row, "scen_rows": scen_rows,
            "scen_total_row": sr + 1, "loss_cells": loss_cells, "order_cells": order_cells}


def first_five(res):
    cand = [c for c in res["clients"] if c["segment"] != "Hold"]
    cand.sort(key=lambda c: (not c["call_first"], -(c["annual_fee"] or 0)))
    return cand[:5]


def movers(res, st):
    out = []
    nohrs = [c["name"] for c in res["clients"] if not c["hours"] and c["segment"] != "Hold"]
    if res["anchor_rate"]:
        out.append(f"Hours per client: each target is {st.money(res['anchor_rate'])} an hour times that client's hours, "
                   f"so each hour a month added or removed moves a target by {st.money(res['anchor_rate'])}"
                   + (f" ({st.money(res['anchor_rate'] * 3)} a quarter)" if any(c['per'] == 'quarter' for c in res['clients']) else "") + ".")
    if nohrs:
        out.append("No hours for " + _names(nohrs) + ": they get a flat step until you give them.")
    out.append(f"The step cap ({st.pct(res['cap'])}): a bigger cap closes gaps sooner and raises the break-even risk; "
               f"change the yellow cell on Assumptions to see it.")
    if res["tax"] != "before":
        out.append("Tax status: a percentage step is the same either way, but if these fees include tax the cash "
                   "figures are overstated by that tax.")
    return out


def write_csvs(res, st, clients, folder, stem):
    import csv
    paths = []
    p = Path(folder) / f"{stem} Plan.csv"
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Client", "Fee per", "Current fee", "Hours a month", "Target fee", "Group", "Reason", "Step 1 fee",
                    "Step 1 date", "Step 2 fee", "Step 2 date", "Gap left", "Notice", "Notice source", "Call first",
                    "Run-rate change a year", "Next 12 months cash", "Letter", "HOLD because"])
        for c in res["clients"]:
            w.writerow([c["name"], c["per"], st.money(c["fee"]), c["hours"] or "", st.money(c["target"]) if c["target"] else "",
                        c["segment"], c["reason"], st.money(c["step1"]) if c["step1"] is not None else "",
                        st.d(date.fromisoformat(c["eff1"])) if c["eff1"] and c["segment"] != "Hold" else "",
                        st.money(c["step2"]) if c["step2"] else "", st.d(date.fromisoformat(c["eff2"])) if c["eff2"] else "",
                        st.money(c["gap"]) if c["gap"] else "", c["notice"], c["notice_src"], "yes" if c["call_first"] else "no",
                        st.money(c["run_rate"]), st.money(c["cash12"]), c["letter"], c["hold_why"]])
    paths.append(p)
    p = Path(folder) / f"{stem} Summary.csv"
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for ln in headline(res, st):
            w.writerow([localise(ln, st.american)])
        w.writerow([])
        w.writerow(["Rebuild in any spreadsheet: run-rate change = (last step fee - current fee) x fee units a year; "
                    "next 12 months cash = (step 1 - current) x units billed at step 1 + (step 2 - current) x units "
                    "billed at step 2; break-even share = total run-rate change / total new contribution."])
    paths.append(p)
    return paths


SUPERSEDED = []


def out_name(folder, base, ext, stamp):
    """The file keeps one name; an earlier file of that name moves into superseded/, so no stale copy sits beside it."""
    p = Path(folder) / f"{base} {stamp}.{ext}"
    if p.exists():
        old = Path(folder) / "superseded"
        old.mkdir(exist_ok=True)
        dest, n = old / p.name, 2
        while dest.exists():
            dest = old / f"{base} {stamp} ({n}).{ext}"
            n += 1
        os.replace(p, dest)
        SUPERSEDED.append(dest)
    return p


# ====================================================================== main
def load(path):
    p = Path(path)
    if not p.exists():
        raise Stop(f"there is no inputs file at {path}")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise Stop(f"the inputs file is not valid JSON (line {e.lineno}): fix it and run again") from None


def jsonable(o):
    if isinstance(o, (date,)):
        return o.isoformat()
    if isinstance(o, tuple):
        return list(o)
    return str(o)


def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("cmd", choices=["compute", "build", "selfcheck"])
    a.add_argument("inputs")
    a.add_argument("--out")
    a.add_argument("--results")
    a.add_argument("--csv", action="store_true", help="write CSV files instead of a workbook (as if openpyxl were missing)")
    a.add_argument("--no-workbook", action="store_true", help="single client: letters only")
    a.add_argument("--provisional", action="store_true",
                   help="a client listed twice with different fees: plan on the higher fee, HOLD that letter, ask")
    args = a.parse_args()
    try:
        inp = load(args.inputs)
        res, st, clients = plan(inp, provisional=args.provisional)
        if args.results:
            Path(args.results).write_text(json.dumps(res, indent=1, default=jsonable), encoding="utf-8")
        if args.cmd == "selfcheck":
            print("SELF-CHECK:", "ok" if res["selfcheck"]["ok"] else "FAILED", res["selfcheck"])
            sys.exit(0)
        print_plan(res, st)
        if args.cmd == "build":
            if not args.out:
                raise Stop("build needs --out <folder>")
            Path(args.out).mkdir(parents=True, exist_ok=True)
            wrote = []
            stamp = res["today"]
            if not args.no_workbook:
                use_csv = args.csv
                if not use_csv:
                    try:
                        import openpyxl  # noqa: F401
                    except ImportError:
                        use_csv = True
                        print("NOTE: openpyxl is not available here, so the plan is written as CSV files with the formulas to rebuild it.")
                if use_csv:
                    wrote += write_csvs(res, st, clients, args.out, f"Price rise plan {stamp}")
                else:
                    xp = out_name(args.out, "Price rise plan", "xlsx", stamp)
                    meta = build_workbook(res, st, clients, xp)
                    res["workbook_meta"] = meta
                    wrote.append(xp)
            import letters
            dp = out_name(args.out, "Price rise follow-up" if res.get("outcomes") else "Price rise letters", "docx", stamp)
            letters.build(res, st, dp)
            wrote.append(dp)
            res["files"] = [str(p) for p in wrote]
            if args.results:
                Path(args.results).write_text(json.dumps(res, indent=1, default=jsonable), encoding="utf-8")
            for p in wrote:
                print(f"WROTE: {p}")
            for p in SUPERSEDED:
                print(f"MOVED: the earlier file is now {p}; the new one replaces it")
        held_letters = any(c["letter"] == "HOLD" for c in res["clients"])
        sys.exit(1 if (res["needs"] or held_letters) else 0)
    except Stop as e:
        print(f"STOP: {e}")
        if e.ask:
            print(f"ASK: {e.ask}")
        sys.exit(2)
    except D.DateStop as e:
        print(f"STOP: a date could not be read: {e}")
        print("ASK: Could you give that date as day, month and year?")
        sys.exit(2)
    except (KeyError, TypeError, ValueError, AttributeError, IndexError) as e:
        print(f"STOP: the inputs file has a field in an unexpected shape ({type(e).__name__}: {e}). "
              f"Check it against references/intake-guide.md and run again.")
        sys.exit(2)


if __name__ == "__main__":
    main()
