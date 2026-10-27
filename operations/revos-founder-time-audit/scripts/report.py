#!/usr/bin/env python3
"""Founder Time Audit: write the one-page report (.docx) and the workbook (.xlsx) from rank.py results.

Usage:
  python3 scripts/report.py <results.json> --out <folder> [--note note.md] [--md <summary.md>]
  python3 scripts/report.py log-template --out <file.xlsx|file.csv>     the one-week time log

The report is the main file: headline hours by category, the deletions, the top five handovers with
their hours and value, the two flags, anything questioned, the proposed week and the basis. The
workbook holds the full log with live formulas (yellow cells are the founder's to change), the
ranked list, the proposed week and the basis.

The note (at most 90 words, written by Claude) is checked before anything is written: every figure
in it must be one the scripts computed, small numbers need a unit, and banned phrases stop it.
Standard library only (zipfile and XML). No network calls.
Exit codes: 0 written, 2 stopped (STOP line; nothing written).
"""
import argparse
import json
import re
import sys
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parent))
from timeparse import fmt_money, fmt_number  # noqa: E402

SKILL_NAME = "Founder Time Audit"
CREDIT = "Made with Merigrove Founder Time Audit"
NOTE_MAX_WORDS = 90
WPM = 52 / 12
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]


class Stop(Exception):
    pass


NUM = {"decimal": None, "after": False}  # the founder's number style, set from the results


def h1(x):
    return fmt_number(round(float(x) + 1e-9, 1), 1, NUM["decimal"])


def pct(x):
    return f"{round(float(x) * 100)}%"


def money(x, sym):
    return fmt_money(x, sym, NUM["decimal"], NUM["after"])


DATE_STYLE = ["dmy"]
PAPER = ["a4"]  # set from the results: month first for a founder who writes dates that way


def long_date(iso):
    d = date.fromisoformat(str(iso)[:10])
    if DATE_STYLE[0] == "mdy":
        return f"{MONTHS[d.month - 1]} {d.day}, {d.year}"
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def span(a, b):
    da, db = date.fromisoformat(a), date.fromisoformat(b)
    mdy = DATE_STYLE[0] == "mdy"
    if da.year == db.year and da.month == db.month:
        return (f"{MONTHS[da.month - 1]} {da.day} to {db.day}, {db.year}" if mdy
                else f"{da.day} to {db.day} {MONTHS[db.month - 1]} {db.year}")
    if da.year == db.year:
        return (f"{MONTHS[da.month - 1]} {da.day} to {MONTHS[db.month - 1]} {db.day}, {db.year}" if mdy
                else f"{da.day} {MONTHS[da.month - 1]} to {db.day} {MONTHS[db.month - 1]} {db.year}")
    return f"{long_date(a)} to {long_date(b)}"


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-") or "your-business"


def hrs(x):
    v = h1(x)
    return f"{v} hour" if v == "1" else f"{v} hours"


def h2(x):
    return fmt_number(round(float(x) + 1e-9, 2), 2, NUM["decimal"])


ISO_DATE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")


def human_dates(text):
    """Dates in founder-facing text are spelled out in the founder's order, never ISO."""
    return ISO_DATE.sub(lambda m: long_date(m.group(0)), str(text))


# ----------------------------------------------------------------------------- the words
SOURCE_TEXT = {"calendar": "your calendar", "tracked": "the week you tracked", "recall": "what you remembered",
               "calendar+recall": "your calendar plus what you told me", "tracked+recall": "your tracked week plus what you told me"}


def content(res, note):
    """Everything the report says, as structured blocks shared by the docx and the markdown copy."""
    sym = res["symbol"]
    rows = {x["activity"]: x for x in res["rows"]}
    c = res["categories"]
    wk = res["week"]["hours"]
    per = res.get("period") or {}
    B = []
    title = "Founder time audit"
    files = ", ".join(per.get("files") or [])
    when = span(per["from"], per["to"]) if per.get("from") and per.get("to") else f"the week before {long_date(res['date'])}"
    sub = f"{res['business']} | {when} | from {SOURCE_TEXT.get(res['source'], res['source'])} | Confidence: {res['confidence']}"
    B.append(("title", title))
    B.append(("sub", sub))
    if res["confidence"] == "low":
        B.append(("warn", f"Low confidence: {res['confidence_why']}. Track one real week with the log template and run it again "
                          "before you hand anything big over."))
    head = (f"You work about {hrs(wk)} a week: {hrs(c['1']['week'])} only you can do, {hrs(c['2']['week'])} someone could do "
            f"with instruction, and " + (f"{hrs(c['3']['week'])} nobody should be doing." if c['3']['week'] > 0.04
                                       else "nothing that nobody should be doing."))
    if c["not_placed"]["week"]:
        head += f" Another {hrs(c['not_placed']['week'])} are not placed in any activity."
    B.append(("headline", head))
    if c["not_placed"]["week"]:
        B.append(("small", f"To place those {hrs(c['not_placed']['week'])}, track one week as you go with the one-week log "
                           "(attached) and run the audit again."))
    rc = res["reclaimed"]
    rate = res["rates"]["used"]
    n5 = min(5, len(res["handovers"]))
    words = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}
    nd = len(res["deletions"])
    parts = []
    dpart = (f"the {words.get(nd, str(nd))} deletion{'s' if nd != 1 else ''}") if nd else ""
    hpart = (f"the top {words[n5]} handovers" if n5 > 1 else "the top-ranked handover") if n5 else ""
    if dpart or hpart:
        parts.append(" and ".join(x for x in (dpart, hpart) if x))
    if parts:
        verb = "holds" if not (nd and n5) and (nd == 1 or n5 == 1) else "hold"
        line = (f"{parts[0][0].upper() + parts[0][1:]} {verb} {hrs(rc['first_five_month'])} a month "
                f"({h1(rc['first_five_week'])} a week) of your time.")
        if rate:
            basis = ("the rate you gave" if res["rates"]["used_label"] == "the rate you gave"
                     else "your monthly sales over your hours")
            line += (f" At {money(rate, sym)} an hour ({basis}) that time is worth {money(rc['value_month'], sym)} a month"
                     + (f" ({money(rc['value_week'], sym)} a week)" if rc.get("value_week") is not None else "") + f", "
                     f"if it goes into {'selling' if res['plan']['freed_to'] == 'selling' else res['plan']['freed_to']}"
                     f"{' and earns at that rate' if res['plan']['freed_to'] != 'fewer hours' else ''}.")
            if res["plan"]["freed_to"] == "fewer hours":
                line = line.replace("that time is worth", "that is").replace(
                    ", if it goes into fewer hours.", " of your time, which you have said you will take back as time off rather than sell.")
        else:
            line += " [NEED: what an hour of your time is worth, or your monthly sales, to put a value on it.]"
        if rc["helper_cost_month"] is not None:
            who = sorted({x["who"] for x in res["rows"] if x["activity"] in res["handovers"][:5] and x["helper_cost_month"] is not None})
            nw = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}[rc["helper_cost_rows"]]
            rate_h = sorted({x["helper_rate"] for x in res["rows"] if x["activity"] in res["handovers"][:5] and x["helper_rate"]})
            wk_cost = f" ({money(rc['helper_cost_week'], sym)} a week)" if rc.get("helper_cost_week") is not None else ""
            line += (f" {who[0]}'s time on {nw} of them costs {money(rc['helper_cost_month'], sym)} a month{wk_cost} at "
                     f"{money(rate_h[0], sym)} an hour"
                     if len(who) == 1 else f" Paying for the help on {nw} of them costs {money(rc['helper_cost_month'], sym)} a month{wk_cost}")
            line += "."
        if rc.get("automate_rows_top5"):
            line += " Tool costs for the automations are not counted."
        B.append(("value", line))
    if note:
        B.append(("note", note))
    fl = []
    f = res["functions"]
    for x in res["flags"]:
        if x["code"] == "doing_high":
            dp = pct(f['doing']['share']) if pct(f['doing']['share']) != "50%" else f"{round(f['doing']['share'] * 100, 1):g}%"
            fl.append(f"Doing is {dp} of your week (delivery {pct(f['delivery']['share'])}, admin "
                      f"{pct(f['admin']['share'])}), above the 50% line: hand over the top-ranked task first.")
        if x["code"] == "strategy_low":
            had = f["strategy"]["week"] >= 4
            fl.append(f"Strategy is {pct(f['strategy']['share'])} of your week, below 15%: the week below "
                      f"{'keeps' if had else 'fixes'} a protected block of {hrs(res['proposed_week']['strategy_block'])}"
                      + ((", paid for by the " + ("deletions and handovers" if res["deletions"] and res["handovers"] else
                                                   "deletions" if res["deletions"] else "handovers") + ".")
                         if res["plan"]["available"] >= 0 and (res["deletions"] or res["handovers"]) and not had else ".")
                      + f" Four hours is the floor; 15% of this week would be {hrs(res['plan']['strategy_15_hours'])}.")
    if fl:
        B.append(("h2", "Two flags" if len(fl) == 2 else "One flag"))
        for x in fl:
            B.append(("bullet", x))
    if res["deletions"]:
        B.append(("h2", "Delete first"))
        t = [["Stop doing", "Hours a week", "Hours a month", "Why"]]
        for n in res["deletions"]:
            x = rows[n]
            t.append([n, h1(x["weekly_hours"]), h1(x["monthly_hours"]), x["reason"] or "nobody needs it"])
        B.append(("table", t))
    if res["handovers"]:
        founder_order = (res.get("order") or {}).get("source") == "founder"
        B.append(("h2", "Hand over, in the order you chose" if founder_order else "Hand over, in this order"))
        t = [["#", "Work", "Hours each x times a month", "Hours a week", "Hours a month", "Action", "Worth a month"]]
        for n in res["handovers"][:5]:
            x = rows[n]
            act = {"delegate": f"Delegate to {x['who'] or '[NEED: who]'}", "automate": f"Automate: {x['who'] or '[NEED: how]'}"}[x["action"]]
            t.append([str(x["rank"]), n + (" (from memory)" if x["confidence"] == "low" and res["source"] != "recall" else ""),
                      f"{h2(x['hours_each'])} x {h2(x['per_month'])}", h1(x["weekly_hours"]), h1(x["monthly_hours"]), act,
                      money(x["value_month"], sym) if x["value_month"] is not None else "[NEED]"])
        B.append(("table", t))
        be = [c for c in res.get("capacity") or [] if c.get("break_even_share") is not None and c.get("rows")]
        if be:
            B.append(("small", "Paying for the help: " + "; ".join(
                f"{c['name']}'s handovers cost {money(c['cost_week'], sym)} a week and pay for themselves if "
                f"{pct(c['break_even_share'])} of the hours they free go into work at your rate" for c in be) + "."))
        if founder_order:
            B.append(("small", "By hours a month alone the order would be: "
                      + ", ".join(f"{n} ({hrs(rows[n]['monthly_hours'])})" for n in res["order"]["by_hours"][:5]) + "."))
        rest = res["handovers"][5:]
        if rest:
            B.append(("small", "Next on the list: " + ", ".join(f"{n} ({hrs(rows[n]['monthly_hours'])} a month)" for n in rest) + "."))
    for cap in res.get("capacity") or []:
        if cap["assigned_week"] > cap["spare_week"] + 0.25 and not cap.get("waiting"):
            B.append(("warn", f"[NEED: {cap['name']} has {hrs(cap['spare_week'])} spare a week; these handovers need "
                              f"{h1(cap['assigned_week'])}. Decide which waits.]"))
    if res["kept_category_two"]:
        k = [rows[n] for n in res["kept_category_two"]]
        groups = {}
        for x in k:
            groups.setdefault(x["reason"], []).append(x["activity"])

        def soft(s, i):
            return s[0].lower() + s[1:] if i and len(s) > 1 and s[1].islower() else s
        items = []
        for reason, names in groups.items():
            nm = names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]
            items.append(soft(nm, len(items)) + (f" ({reason})" if reason else ""))
        joined = items[0] if len(items) == 1 else "; ".join(items[:-1]) + "; and " + items[-1]
        B.append(("para", f"Could be handed over but kept for now, {hrs(res['kept_category_two_week'])} a week: {joined}."))
    ch = [x for x in res["rows"] if x["challenge"] or x["challenge_answer"]]
    if ch:
        B.append(("h2", "Questioned once"))
        for x in ch:
            if x["challenge"]:
                B.append(("bullet", f"{x['activity']}, {hrs(x['weekly_hours'])} a week, kept with you: "
                                    f"{clause(x['challenge_answer']) or '[NEED: not answered yet]'}"))
            else:
                B.append(("bullet", f"{x['activity']}, {hrs(x['weekly_hours'])} a week, moved after one question: "
                                    f"{clause(x['challenge_answer'])}"))
    prev = res.get("previous")
    if prev:
        B.append(("h2", f"Since your last audit ({long_date(prev['date']) if prev.get('date') else 'last time'})"))
        for chg in prev["changes"]:
            if chg["kind"] == "h":
                B.append(("bullet", f"{chg['label']}: {h1(chg['before'])} then, {h1(chg['now'])} now."))
            else:
                B.append(("bullet", f"{chg['label']}: {pct(chg['before'])} then, {pct(chg['now'])} now."))
        for hv in prev["handovers"]:
            B.append(("bullet", f"{hv['activity']} ({hv['action']}{' to ' + hv['who'] if hv['who'] and hv['action'] == 'delegate' else ''}): "
                                f"{hv['status']}, {hrs(hv['before'])} a week then, {h1(hv['now'])} now."))
    pw = res["proposed_week"]
    B.append(("h2", "Proposed week"))
    t = [["", f"Morning, {pw['morning']}" if pw["morning"] else "Morning",
          f"Afternoon, {pw['afternoon']}" if pw["afternoon"] else "Afternoon"]]
    for d in pw["days"]:
        def cell(items, off):
            return "Not working" if off else (", ".join(f"{l} {h1(hh)}h" for l, hh in items) or "Open")
        t.append([d["day"] + (f" ({d['hours']})" if d.get("hours") else ""), cell(d["morning"], d.get("morning_off")),
                  cell(d["afternoon"], d.get("afternoon_off"))])
    B.append(("table", t))
    plan = res["plan"]
    wp = res.get("work_pattern") or {}
    pl = ("" if wp.get("known", True) else "[NEED: your usual working days and hours; this week is laid out on "
          f"{len(wp.get('day_names') or [])} plain days until you say.] ")
    pl += (f"After the changes: Doing {pct(plan['doing_share'])} and Strategy {pct(plan['strategy_share'])} of a "
          f"{h1(plan['week'])}-hour week.")
    if pw.get("as_now"):
        an = pw["as_now"]
        pl += " Kept as now, at the times you do them: " + ", ".join(f"{x['activity']} {h1(x['week'])}h" for x in an) + " a week."
    if pw.get("free_selling", 0) > 0.01:
        pl += f" Free for selling or fewer hours: {hrs(pw['free_selling'])} a week, left open rather than packed into the days."
    if pw["extra_hours"] > 0.01:
        ex = pw.get("extra_by_label") or {}
        pl += (f" Still beyond your working day: {hrs(pw['extra_hours'])} a week ("
               + ", ".join(f"{l.lower()} {h1(v)}" for l, v in ex.items())
               + "). The next handovers are where it comes from.")
    if pw.get("not_placed", 0) > 0.01:
        pl += f" The {hrs(pw['not_placed'])} not placed in any activity are not laid out."
    B.append(("small", pl))
    # basis
    w = res["week"]
    basis = []
    if res["source"] in ("calendar", "calendar+recall", "tracked", "tracked+recall"):
        lo = res.get("left_out") or {}
        lefts = []
        if lo.get("declined"):
            lefts.append(f"{lo['declined']} declined")
        if lo.get("all_day"):
            lefts.append(f"{lo['all_day']} all-day")
        if res.get("personal_count"):
            lefts.append(f"{res['personal_count']} personal")
        basis.append(f"Hours from {files or 'your calendar'}, {when}: {h1(w['calendar_week'])} a week counted"
                     + (f" ({', '.join(lefts)} left out; overlaps shared)" if lefts else "") + ".")
    basis.append(f"A {h1(w['hours'])}-hour week, from {w['source']}.")
    hols = per.get("holidays") or []
    if hols:
        n = len(hols)
        basis.append(f"{'One day' if n == 1 else str(n) + ' days'} in these weeks "
                     f"{'was a public holiday or day off' if n == 1 else 'were public holidays or days off'} "
                     f"({'from your calendar' if all(h.get('source') == 'calendar' for h in hols) else 'from your calendar or as you said'}), "
                     "so the week may be lighter than usual.")
    if rate:
        if res["rates"]["used_label"] == "the rate you gave":
            basis.append(f"Value at the {money(rate, sym)} an hour you gave.")
        else:
            basis.append(f"Value at {money(rate, sym)} an hour: {money(res['rates']['monthly_revenue'], sym)} sales a month over "
                         f"{hrs(res['rates']['hours_month'])} of yours. Freed hours earn that only if you fill them with paid or selling work.")
    if any(x["action"] == "delegate" for x in res["rows"]):
        basis.append("Planning, not employment, tax or legal advice: whether someone who works for you is an employee or a "
                     "contractor depends on the rules where you both work; ask your accountant or an employment adviser.")
    else:
        basis.append("A planning tool, not employment, tax or legal advice.")
    B.append(("basis", " ".join(basis)))
    return B


def clause(text):
    """The founder's answer as a tidy clause: first letter lower case unless a name, one closing full stop."""
    t = str(text or "").strip().rstrip(".")
    if not t:
        return ""
    if t[:1].isupper() and t[1:2].islower() and t.split()[0].lower() in ("ok", "okay", "yes", "yeah", "no", "well", "so", "the",
                                                                         "they", "clients", "it", "we", "i", "because", "only"):
        t = t[0].lower() + t[1:]
    return t + "."


def to_markdown(B):
    out = []
    for kind, v in B:
        if kind == "title":
            out.append(f"# {v}")
        elif kind == "sub":
            out.append(v)
        elif kind == "headline":
            out.append(f"**{v}**")
        elif kind == "h2":
            out.append(f"## {v}")
        elif kind == "bullet":
            out.append(f"- {v}")
        elif kind == "table":
            out.append("| " + " | ".join(x.replace("|", "/") for x in v[0]) + " |")
            out.append("|" + "---|" * len(v[0]))
            for r in v[1:]:
                out.append("| " + " | ".join(str(x).replace("|", "/") for x in r) + " |")
        else:
            out.append(v)
        out.append("")
    return "\n".join(out)


# ----------------------------------------------------------------------------- note gate
UNIT_AFTER = r"\s*(?:-?\s*)(?:[a-z'-]+\s+){0,2}?(hours?|hrs?|h\b|a week|a month|times|days?|weeks?|months?|minutes|mins|people|calls?|rows?|handovers?|deletions?|clients?|of them|am|pm|per cent|%)"
PROMISES = (r"\b(guarantee\w*|you (will |'ll )?(make|earn|double|grow|get back|save|free up|gain)\b|double your|triple|10x|"
            r"will definitely)")
NUM_TOKEN = r"\d[\d.,]*\d|\d"


def set_style(res):
    """Read the founder's number style and date order from the results, for every writer and checker here."""
    ns = res.get("number_style") or {}
    NUM["decimal"] = ns.get("decimal")
    NUM["after"] = bool(ns.get("symbol_after"))
    DATE_STYLE[0] = (res.get("locale") or {}).get("date_style") or "dmy"
    PAPER[0] = (res.get("locale") or {}).get("paper") or "a4"


def canon(tok):
    """A figure as the founder's style writes it ('1.325.481', '57,5') back to a plain number string."""
    if NUM["decimal"] == "comma":
        return tok.replace(".", "").replace(",", ".")
    return tok.replace(",", "")


def allowed_figures(res):
    vals = set()

    def walk(o, key=""):
        if isinstance(o, bool):
            return
        if isinstance(o, (int, float)):
            x = float(o)
            for s in (f"{round(x + 1e-9, 1):g}", f"{round(x)}", f"{round(x, 2):g}"):
                vals.add(s)
            if 0 <= x <= 1.5:
                vals.add(f"{round(x * 100)}")
                vals.add(f"{round(x * 100, 1):g}")
        elif isinstance(o, dict):
            for k, v in o.items():
                walk(v, k)
        elif isinstance(o, list):
            for v in o:
                walk(v, key)
        elif isinstance(o, str):
            for m in re.finditer(r"\d+(?:\.\d+)?", o):
                vals.add(m.group(0))
    walk(res)
    for k in (50, 15, 4):  # the method's own thresholds
        vals.add(str(k))
    return vals


def check_note(note, res):
    probs = []
    words = len(re.findall(r"\b\w[\w'-]*\b", note))
    if words > NOTE_MAX_WORDS:
        probs.append(f"the note is {words} words; the limit is {NOTE_MAX_WORDS}")
    if re.search(r"[\u2014\u2013]", note):
        probs.append("the note has an em or en dash")
    if re.search(PROMISES, note, re.I):
        probs.append("the note promises a result")
    allowed = allowed_figures(res)
    for m in re.finditer(r"((?:US|S|A|AU|NZ|C|CA|HK)?\$|[£€¥₹₱₩฿]|\bRM|\b(?:USD|SGD|AUD|NZD|CAD|HKD|GBP|EUR|INR|MYR|AED|ZAR|CHF|PHP|JPY)\s?)?"
                         r"\s?(" + NUM_TOKEN + r")(\s*%|\s?[€£])?", note):
        raw = canon(m.group(2))
        try:
            v = float(raw)
        except ValueError:
            continue
        if re.match(r"(19|20)\d\d$", raw):
            continue
        after = note[m.end():m.end() + 30]
        if v <= 12 and not m.group(1) and not m.group(3) and not re.match(UNIT_AFTER, after, re.I):
            probs.append(f"'{m.group(0).strip()}' needs a unit (hours, a week, times) or should be a word")
            continue
        if raw not in allowed and f"{v:g}" not in allowed:
            probs.append(f"'{m.group(0).strip()}' is not a figure the audit computed")
    return probs


# ----------------------------------------------------------------------------- docx
def _run(text, bold=False, size=None, colour=None, italic=False):
    pr = ""
    if bold:
        pr += "<w:b/>"
    if italic:
        pr += "<w:i/>"
    if colour:
        pr += f'<w:color w:val="{colour}"/>'
    if size:
        pr += f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>'
    rpr = f"<w:rPr>{pr}</w:rPr>" if pr else ""
    return f'<w:r>{rpr}<w:t xml:space="preserve">{escape(text)}</w:t></w:r>'


def _inline(text, size=None, colour=None, bold=False):
    out = []
    for part in re.split(r"(\*\*[^*]+\*\*|\[NEED:[^\]]*\])", text):
        if not part:
            continue
        if part.startswith("**"):
            out.append(_run(part[2:-2], bold=True, size=size, colour=colour))
        elif part.startswith("[NEED"):
            out.append(_run(part, bold=True, size=size, colour="9A3412"))
        else:
            out.append(_run(part, bold=bold, size=size, colour=colour))
    return "".join(out)


def _p(inner, before=0, after=80, keep=False, ind=None, line=None):
    sp = f'<w:spacing w:before="{before}" w:after="{after}"' + (f' w:line="{line}" w:lineRule="auto"' if line else "") + "/>"
    extra = "<w:keepNext/>" if keep else ""
    if ind:
        extra += f'<w:ind w:left="{ind}" w:hanging="200"/>'
    return f"<w:p><w:pPr>{extra}{sp}</w:pPr>{inner}</w:p>"


def _table(rows, widths, size=16):
    tw = sum(widths)
    grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in widths)
    out = [f'<w:tbl><w:tblPr><w:tblW w:w="{tw}" w:type="dxa"/><w:tblLayout w:type="fixed"/>'
           '<w:tblBorders><w:top w:val="nil"/><w:left w:val="nil"/><w:bottom w:val="nil"/><w:right w:val="nil"/>'
           '<w:insideH w:val="nil"/><w:insideV w:val="nil"/></w:tblBorders>'
           '<w:tblCellMar><w:top w:w="20" w:type="dxa"/><w:left w:w="60" w:type="dxa"/><w:bottom w:w="20" w:type="dxa"/>'
           f'<w:right w:w="60" w:type="dxa"/></w:tblCellMar></w:tblPr><w:tblGrid>{grid}</w:tblGrid>']
    for i, r in enumerate(rows):
        cells = []
        for j, v in enumerate(r):
            shade = ""
            txt = _inline(str(v), size=size - (1 if i == 0 else 0), colour="555555" if i == 0 else None, bold=(i == 0))
            cells.append(f'<w:tc><w:tcPr><w:tcW w:w="{widths[j]}" w:type="dxa"/>{shade}</w:tcPr>'
                         f'<w:p><w:pPr><w:spacing w:before="0" w:after="0"/></w:pPr>{txt}</w:p></w:tc>')
        hdr = "<w:trPr><w:tblHeader/><w:cantSplit/></w:trPr>" if i == 0 else "<w:trPr><w:cantSplit/></w:trPr>"
        out.append(f"<w:tr>{hdr}{''.join(cells)}</w:tr>")
    out.append("</w:tbl>")
    return "".join(out)


def build_docx(B, path, business, paper="a4", lang="en-GB"):
    body = []
    usable = (12240 if paper == "letter" else 11906) - 2 * 900
    for kind, v in B:
        if kind == "title":
            body.append(_p(_run(v, bold=True, size=30), after=20))
        elif kind == "sub":
            body.append(_p(_run(v, size=16, colour="666666"), after=140))
        elif kind == "warn":
            body.append(_p(_inline(v, size=17, colour="9A3412"), after=100))
        elif kind == "headline":
            body.append(_p(_run(v, bold=True, size=22), after=100, line=264))
        elif kind == "value":
            body.append(_p(_inline(v, size=18), after=100, line=252))
        elif kind == "note":
            body.append(_p(_inline(v, size=18, colour="333333"), after=100, line=252))
        elif kind == "h2":
            body.append(_p(_run(v, bold=True, size=19), before=120, after=40, keep=True))
        elif kind == "bullet":
            body.append(_p(_run("•  ", size=17) + _inline(v, size=17), after=30, ind=240))
        elif kind == "table":
            n = len(v[0])
            if n == 7:
                widths = [300, 2500, 1700, 900, 1000, usable - 7600, 1200]
            elif n == 6:
                widths = [300, 2900, 1900, 1100, 2700, 1200]
            elif n == 4 and v[0][0] == "Stop doing":
                widths = [3000, 1000, 1100, usable - 5100]
            elif n == 3 and v[0][0] == "Stop doing":
                widths = [3200, 1300, usable - 4500]
            elif n == 3:
                dw = 1900 if any("(" in str(r[0]) for r in v[1:]) else 1300
                widths = [dw, (usable - dw) // 2, (usable - dw) // 2]
            elif n == 4:
                widths = [1300, 3400, 3400, usable - 8100]
            else:
                widths = [usable // n] * n
            body.append(_table(v, widths, size=16))
            body.append(_p("", after=40))
        elif kind == "small":
            body.append(_p(_inline(v, size=16, colour="444444"), before=20, after=60))
        elif kind == "basis":
            body.append(_p(_inline(v, size=14, colour="666666"), before=100, after=0, line=228))
        else:
            body.append(_p(_inline(v, size=17), after=80))
    pw_, ph_ = (12240, 15840) if paper == "letter" else (11906, 16838)
    sect = (f'<w:sectPr><w:pgSz w:w="{pw_}" w:h="{ph_}"/><w:pgMar w:top="760" w:right="900" w:bottom="700" w:left="900" '
            'w:header="400" w:footer="400" w:gutter="0"/></w:sectPr>')
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
           'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
           f"<w:body>{''.join(body)}{sect}</w:body></w:document>")
    styles = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:docDefaults><w:rPrDefault><w:rPr>'
              '<w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri" w:eastAsia="Calibri"/><w:sz w:val="18"/>'
              f'<w:szCs w:val="18"/><w:lang w:val="{escape(lang)}"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr>'
              '<w:spacing w:after="80" w:line="240" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>'
              '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style></w:styles>')
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    core = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            f"<dc:title>Founder time audit, {escape(business)}</dc:title><dc:creator>{CREDIT}</dc:creator>"
            f"<dc:description>{CREDIT}</dc:description>"
            f'<dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created></cp:coreProperties>')
    app = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
           f"<Application>{CREDIT}</Application></Properties>")
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
          '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
          '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
          '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
          '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
            '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
            '</Relationships>')
    drels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
             '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
             '</Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", doc)
        z.writestr("word/styles.xml", styles)
        z.writestr("word/_rels/document.xml.rels", drels)
        z.writestr("docProps/core.xml", core)
        z.writestr("docProps/app.xml", app)


# ----------------------------------------------------------------------------- xlsx
def col(n):
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


class Sheet:
    def __init__(self, name):
        self.name = name
        self.cells = {}
        self.widths = {}
        self.freeze = None
        self.validations = []
        self.merges = []

    def set(self, r, c, v, style=0, formula=None):
        self.cells[(r, c)] = (v, style, formula)


# style ids: 0 plain, 1 bold, 2 header, 3 input number, 4 input text, 5 one decimal, 6 percent, 7 money,
# 8 title, 9 wrapped, 10 input money, 11 small grey, 12 bold one decimal
STYLES_XML = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
              '<numFmts count="3"><numFmt numFmtId="164" formatCode="0.0"/><numFmt numFmtId="165" formatCode="0%"/>'
              '<numFmt numFmtId="166" formatCode="&quot;{sym}&quot;#,##0"/></numFmts>'
              '<fonts count="4"><font><sz val="10"/><name val="Calibri"/></font><font><b/><sz val="10"/><name val="Calibri"/></font>'
              '<font><b/><sz val="14"/><name val="Calibri"/></font><font><sz val="9"/><color rgb="FF666666"/><name val="Calibri"/></font></fonts>'
              '<fills count="4"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill>'
              '<fill><patternFill patternType="solid"><fgColor rgb="FFFFF2B3"/><bgColor indexed="64"/></patternFill></fill>'
              '<fill><patternFill patternType="solid"><fgColor rgb="FFF2F2F2"/><bgColor indexed="64"/></patternFill></fill></fills>'
              '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
              '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
              '<cellXfs count="13">'
              '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
              '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>'
              '<xf numFmtId="0" fontId="1" fillId="3" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>'
              '<xf numFmtId="164" fontId="0" fillId="2" borderId="0" xfId="0" applyNumberFormat="1" applyFill="1"/>'
              '<xf numFmtId="0" fontId="0" fillId="2" borderId="0" xfId="0" applyFill="1"/>'
              '<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>'
              '<xf numFmtId="165" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>'
              '<xf numFmtId="166" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>'
              '<xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1"/>'
              '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>'
              '<xf numFmtId="166" fontId="0" fillId="2" borderId="0" xfId="0" applyNumberFormat="1" applyFill="1"/>'
              '<xf numFmtId="0" fontId="3" fillId="0" borderId="0" xfId="0" applyFont="1" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>'
              '<xf numFmtId="164" fontId="1" fillId="0" borderId="0" xfId="0" applyNumberFormat="1" applyFont="1"/>'
              '</cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>')


def sheet_xml(sh):
    rows = {}
    for (r, c), v in sh.cells.items():
        rows.setdefault(r, []).append((c, v))
    out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
           'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">']
    if sh.freeze:
        out.append(f'<sheetViews><sheetView workbookViewId="0"><pane ySplit="{sh.freeze - 1}" topLeftCell="A{sh.freeze}" '
                   'activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>')
    if sh.widths:
        out.append("<cols>" + "".join(f'<col min="{c}" max="{c}" width="{w}" customWidth="1"/>' for c, w in sorted(sh.widths.items())) + "</cols>")
    out.append("<sheetData>")
    for r in sorted(rows):
        out.append(f'<row r="{r}">')
        for c, (v, st, f) in sorted(rows[r]):
            ref = f"{col(c)}{r}"
            if f is not None:
                if isinstance(v, str):
                    out.append(f'<c r="{ref}" s="{st}" t="str"><f>{escape(f)}</f><v>{escape(v)}</v></c>')
                else:
                    out.append(f'<c r="{ref}" s="{st}"><f>{escape(f)}</f><v>{"" if v is None else repr(float(v))}</v></c>')
            elif v is None or v == "":
                out.append(f'<c r="{ref}" s="{st}"/>')
            elif isinstance(v, (int, float)) and not isinstance(v, bool):
                out.append(f'<c r="{ref}" s="{st}"><v>{repr(float(v))}</v></c>')
            else:
                out.append(f'<c r="{ref}" s="{st}" t="inlineStr"><is><t xml:space="preserve">{escape(str(v))}</t></is></c>')
        out.append("</row>")
    out.append("</sheetData>")
    if sh.merges:
        out.append(f'<mergeCells count="{len(sh.merges)}">' + "".join(f'<mergeCell ref="{m}"/>' for m in sh.merges) + "</mergeCells>")
    if sh.validations:
        out.append(f'<dataValidations count="{len(sh.validations)}">')
        for rng, items in sh.validations:
            out.append(f'<dataValidation type="list" allowBlank="1" showErrorMessage="1" sqref="{rng}">'
                       f'<formula1>"{escape(",".join(items))}"</formula1></dataValidation>')
        out.append("</dataValidations>")
    size = 1 if PAPER[0] == "letter" else 9
    out.append('<pageMargins left="0.5" right="0.5" top="0.6" bottom="0.6" header="0.3" footer="0.3"/>'
               f'<pageSetup paperSize="{size}" orientation="landscape" fitToWidth="1" fitToHeight="0"/></worksheet>')
    return "".join(out)


def write_xlsx(path, sheets, sym, title):
    wb = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
          'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><bookViews><workbookView/></bookViews><sheets>']
    for i, sh in enumerate(sheets, 1):
        wb.append(f'<sheet name="{escape(sh.name)}" sheetId="{i}" r:id="rId{i}"/>')
    wb.append('</sheets><calcPr calcId="191029" fullCalcOnLoad="1"/></workbook>')
    rels = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">']
    for i, _sh in enumerate(sheets, 1):
        rels.append(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>')
    rels.append(f'<Relationship Id="rId{len(sheets) + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>')
    ct = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
          '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
          '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>']
    for i, _sh in enumerate(sheets, 1):
        ct.append(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>')
    ct.append("</Types>")
    root = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
            '</Relationships>')
    core = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/">'
            f"<dc:title>{escape(title)}</dc:title><dc:creator>{CREDIT}</dc:creator><dc:description>{CREDIT}</dc:description>"
            "</cp:coreProperties>")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", "".join(ct))
        z.writestr("_rels/.rels", root)
        z.writestr("xl/workbook.xml", "".join(wb))
        z.writestr("xl/_rels/workbook.xml.rels", "".join(rels))
        z.writestr("xl/styles.xml", STYLES_XML.replace("{sym}", escape(sym or "")))
        z.writestr("docProps/core.xml", core)
        for i, sh in enumerate(sheets, 1):
            z.writestr(f"xl/worksheets/sheet{i}.xml", sheet_xml(sh))


def build_workbook(res, path):
    sym = res["symbol"]
    rows = res["rows"]
    wk = res["week"]["hours"]
    rate = res["rates"]["used"]
    rev = res["rates"]["monthly_revenue"]
    S, L, H, W, Bs = Sheet("Summary"), Sheet("Log"), Sheet("Handovers"), Sheet("Proposed week"), Sheet("Basis")
    # ---- Log
    L.set(1, 1, f"Activity log: {res['business']}", 8)
    L.set(2, 1, "Yellow cells are yours to change. Hours a month = hours each x times a month. "
                "Change a category or action and the Summary updates; ask Claude to re-rank.", 11)
    L.merges.append("A2:N2")
    hdr = ["#", "Activity", "Source", "Hours each", "Times a month", "Hours a month", "Hours a week", "Share of week",
           "Category", "Function", "Action", "Who or how", "Why", "How often, from"]
    for j, h in enumerate(hdr, 1):
        L.set(3, j, h, 2)
    L.freeze = 4
    first = 4
    order = sorted(rows, key=lambda x: (-(x["monthly_hours"])))
    rowpos = {}
    for i, x in enumerate(order):
        r = first + i
        rowpos[x["activity"]] = r
        L.set(r, 1, i + 1)
        L.set(r, 2, x["activity"], 9)
        L.set(r, 3, {"recall": "told me", "calendar repeat": "calendar repeat"}.get(x["source"], x["source"]))
        L.set(r, 4, round(x["hours_each"], 4), 3)
        L.set(r, 5, round(x["per_month"], 4), 3)
        L.set(r, 6, round(x["hours_each"], 4) * round(x["per_month"], 4), 5, f"D{r}*E{r}")
        L.set(r, 7, round(x["hours_each"], 4) * round(x["per_month"], 4) / WPM, 5, f"F{r}/(52/12)")
        L.set(r, 8, (round(x["hours_each"], 4) * round(x["per_month"], 4) / WPM) / wk, 6, f"G{r}/Summary!$B$5")
        L.set(r, 9, x["category_label"], 4)
        L.set(r, 10, x["function_label"], 4)
        L.set(r, 11, x["action"].capitalize(), 4)
        L.set(r, 12, x["who"], 4)
        L.set(r, 13, (x["reason"] + (f" Questioned once: {x['challenge_answer']}" if x["challenge_answer"] else "")).strip(), 9)
        L.set(r, 14, x["per_month_basis"] or "", 9)
    last = first + len(order) - 1
    L.validations += [(f"I{first}:I{last + 20}", ["Only you", "With instruction", "Nobody should"]),
                      (f"J{first}:J{last + 20}", ["Strategy", "Selling", "Managing", "Delivery", "Admin"]),
                      (f"K{first}:K{last + 20}", ["Keep", "Delete", "Delegate", "Automate"])]
    tot = last + 1
    L.set(tot, 2, "Total placed", 1)
    placed_cached = sum(round(x["hours_each"], 4) * round(x["per_month"], 4) for x in order)
    L.set(tot, 6, placed_cached, 12, f"SUM(F{first}:F{last})")
    L.set(tot, 7, placed_cached / WPM, 12, f"SUM(G{first}:G{last})")
    for c_, w in {1: 4, 2: 34, 3: 14, 4: 10, 5: 11, 6: 11, 7: 10, 8: 10, 9: 16, 10: 11, 11: 10, 12: 26, 13: 44, 14: 30}.items():
        L.widths[c_] = w
    rng = lambda c_: f"Log!${c_}${first}:${c_}${last}"  # noqa: E731

    def sumif(colc, val, sumc="G"):
        return f'SUMIF({rng(colc)},"{val}",{rng(sumc)})'

    def cached_sum(field, val, key="weekly"):
        return sum((round(x["hours_each"], 4) * round(x["per_month"], 4)) / (WPM if key == "weekly" else 1)
                   for x in order if x[field] == val)
    # ---- Summary
    S.set(1, 1, f"Founder time audit: {res['business']}", 8)
    per = res.get("period") or {}
    S.set(2, 1, f"{span(per['from'], per['to']) if per.get('from') else long_date(res['date'])}. Confidence: {res['confidence']} "
                f"({res['confidence_why']}).", 11)
    S.merges.append("A2:D2")
    S.set(4, 1, "Your week", 2)
    S.set(4, 2, "Hours", 2)
    S.set(4, 3, "Share", 2)
    S.set(5, 1, "Hours worked in a week (change it here)")
    S.set(5, 2, round(wk, 4), 3)
    placed_w = placed_cached / WPM
    cats = [("Only you can do", "category_label", "Only you"), ("Someone could do with instruction", "category_label", "With instruction"),
            ("Nobody should be doing", "category_label", "Nobody should")]
    r = 6
    for lab, fld, val in cats:
        v = cached_sum(fld, val)
        S.set(r, 1, lab)
        S.set(r, 2, v, 5, sumif("I", val))
        S.set(r, 3, v / wk, 6, f"B{r}/$B$5")
        r += 1
    S.set(r, 1, "Not placed in any activity")
    S.set(r, 2, max(0.0, wk - placed_w), 5, f"MAX(0,B5-Log!G{tot})")
    S.set(r, 3, max(0.0, wk - placed_w) / wk, 6, f"B{r}/$B$5")
    r += 2
    S.set(r, 1, "By function", 2)
    S.set(r, 2, "Hours", 2)
    S.set(r, 3, "Share", 2)
    S.set(r, 4, "Check", 2)
    r += 1
    fr = {}
    for lab in ("Strategy", "Selling", "Managing", "Delivery", "Admin"):
        v = cached_sum("function_label", lab)
        S.set(r, 1, lab)
        S.set(r, 2, v, 5, sumif("J", lab))
        S.set(r, 3, v / wk, 6, f"B{r}/$B$5")
        fr[lab] = r
        r += 1
    doing_v = cached_sum("function_label", "Delivery") + cached_sum("function_label", "Admin")
    S.set(r, 1, "Doing (delivery and admin)", 1)
    S.set(r, 2, doing_v, 12, f"B{fr['Delivery']}+B{fr['Admin']}")
    S.set(r, 3, doing_v / wk, 6, f"B{r}/$B$5")
    S.set(r, 4, "Above 50%: hand over the top task" if doing_v / wk > 0.5 else "At or below 50%", 0,
          f'IF(C{r}>0.5,"Above 50%: hand over the top task","At or below 50%")')
    S.set(fr["Strategy"], 4, "Below 15%: protect a 4 hour block" if cached_sum("function_label", "Strategy") / wk < 0.15 else "15% or more", 0,
          f'IF(C{fr["Strategy"]}<0.15,"Below 15%: protect a 4 hour block","15% or more")')
    r += 2
    S.set(r, 1, "Value of your time", 2)
    S.set(r, 2, "", 2)
    S.set(r, 3, "", 2)
    r += 1
    rev_r = r
    S.set(r, 1, "Sales a month (change it here)")
    S.set(r, 2, rev if rev is not None else None, 10)
    r += 1
    rate_r = r
    S.set(r, 1, "An hour of your time is worth")
    if res["rates"]["stated"]:
        S.set(r, 2, res["rates"]["stated"], 10)
        S.set(r, 3, "the rate you gave", 11)
    else:
        S.set(r, 2, rate if rate is not None else "", 7, f'IF(N(B{rev_r})>0,B{rev_r}/(B5*52/12),"")')
        S.set(r, 3, "sales a month over your hours", 11)
    r += 1
    del_m = sum(round(x["hours_each"], 4) * round(x["per_month"], 4) for x in order if x["action"] == "delete")
    hand_m = sum(round(x["hours_each"], 4) * round(x["per_month"], 4) for x in order if x["action"] in ("delegate", "automate"))
    byn = {x["activity"]: x for x in rows}
    first_rows = res["deletions"] + res["handovers"][:5]
    five_m = sum(round(byn[n]["hours_each"], 4) * round(byn[n]["per_month"], 4) for n in first_rows)
    five_last = 3 + len(first_rows)  # the Handovers sheet lists deletions, then handovers in rank order, from row 4
    S.set(r, 1, "Hours a month, the deletions plus the top five handovers (as in the report)", 9)
    S.set(r, 2, five_m, 5, f"SUM(Handovers!E4:E{five_last})" if first_rows else "0")
    fr_ = r
    r += 1
    S.set(r, 1, "Worth a month, the deletions plus the top five, at your rate (as in the report)", 9)
    S.set(r, 2, five_m * rate if rate else "", 7, f'IF(N(B{rate_r})>0,B{fr_}*B{rate_r},"")')
    r += 1
    S.set(r, 1, "Hours a month in deletions")
    S.set(r, 2, del_m, 5, f'SUMIF({rng("K")},"Delete",{rng("F")})')
    dr = r
    r += 1
    S.set(r, 1, "Hours a month in all handovers")
    S.set(r, 2, hand_m, 5, f'SUMIF({rng("K")},"Delegate",{rng("F")})+SUMIF({rng("K")},"Automate",{rng("F")})')
    hr_ = r
    r += 1
    S.set(r, 1, "Worth a month, the deletions plus all handovers, at your rate", 9)
    S.set(r, 2, (del_m + hand_m) * rate if rate else "", 7, f'IF(N(B{rate_r})>0,(B{dr}+B{hr_})*B{rate_r},"")')
    r += 1
    S.set(r, 1, "Worth means the hours earn your rate only if they go into paid or selling work.", 11)
    S.widths.update({1: 46, 2: 14, 3: 30, 4: 34})
    # ---- Handovers
    H.set(1, 1, "Delete first, then hand over in this order", 8)
    H.set(2, 1, "Ranked by hours a month (hours each x times a month), never by ease. Figures follow the Log.", 11)
    H.merges.append("A2:H2")
    for j, h in enumerate(["#", "Work", "Hours each", "Times a month", "Hours a month", "Action", "Who or how", "Worth a month"], 1):
        H.set(3, j, h, 2)
    r = 4
    byname = {x["activity"]: x for x in rows}
    for kind, names in (("Delete", res["deletions"]), ("Hand over", res["handovers"])):
        for i, n in enumerate(names, 1):
            x = byname[n]
            lr = rowpos[n]
            mh = round(x["hours_each"], 4) * round(x["per_month"], 4)
            H.set(r, 1, f"{'D' if kind == 'Delete' else ''}{i}")
            H.set(r, 2, n, 9)
            H.set(r, 3, round(x["hours_each"], 4), 5, f"Log!D{lr}")
            H.set(r, 4, round(x["per_month"], 4), 5, f"Log!E{lr}")
            H.set(r, 5, mh, 5, f"Log!F{lr}")
            H.set(r, 6, x["action"].capitalize())
            H.set(r, 7, x["who"], 9)
            H.set(r, 8, mh * rate if rate else "", 7, f'IF(N(Summary!$B${rate_r})>0,E{r}*Summary!$B${rate_r},"")')
            r += 1
    H.widths.update({1: 5, 2: 34, 3: 11, 4: 13, 5: 13, 6: 11, 7: 30, 8: 14})
    # ---- Proposed week
    pw = res["proposed_week"]
    W.set(1, 1, "Proposed week", 8)
    W.set(2, 1, "Hours by block. Strategy goes first and is protected. Calls sit together in afternoons so mornings stay whole.", 11)
    W.merges.append("A2:D2")
    heads = ["Day", f"Morning, {pw['morning']}", f"Afternoon, {pw['afternoon']}", "Beyond your hours"]
    for j, h in enumerate(heads, 1):
        W.set(3, j, h, 2)
    for i, d in enumerate(pw["days"]):
        W.set(4 + i, 1, d["day"] + (f" ({d['hours']})" if d.get("hours") else ""), 9)
        for j, k in ((2, "morning"), (3, "afternoon"), (4, "extra")):
            off = d.get(f"{k}_off") if k != "extra" else False
            W.set(4 + i, j, "Not working" if off else ", ".join(f"{l} {h1(hh)}h" for l, hh in d[k]), 9)
    rr = 5 + len(pw["days"])
    for x in pw.get("as_now") or []:
        W.set(rr, 1, "Kept as now", 1)
        W.set(rr, 2, f"{x['activity']} {h1(x['week'])}h a week, at the times you do it now", 9)
        rr += 1
    if pw.get("free_selling", 0) > 0.01:
        W.set(rr, 1, "Free", 1)
        W.set(rr, 2, f"{h1(pw['free_selling'])}h a week for selling or fewer hours", 9)
        rr += 1
    if pw.get("not_placed", 0) > 0.01:
        W.set(rr, 1, "Not placed", 1)
        W.set(rr, 2, f"{h1(pw['not_placed'])}h a week not in any activity; not laid out. Track one week to place it.", 9)
    W.widths.update({1: 22, 2: 40, 3: 40, 4: 28})
    # ---- Basis
    Bs.set(1, 1, "Basis and assumptions", 8)
    lines = [f"Source: {SOURCE_TEXT.get(res['source'], res['source'])}. Confidence {res['confidence']}: {res['confidence_why']}.",
             f"Week: {h1(wk)} hours, from {res['week']['source']}."]
    if res["week"].get("calendar_week"):
        lines.append(f"Calendar: {h1(res['week']['calendar_week'])} hours a week counted, "
                     f"{span(per['from'], per['to']) if per.get('from') and per.get('to') else 'in the weeks audited'}, "
                     f"time zone {per.get('tz')}. Overlapping events share their time; declined, cancelled and all-day events are left out.")
    lines += ["Categories: only you (your judgement is what the client pays for), with instruction (someone could do it from a "
              "written process), nobody should (no decision or reader depends on it).",
              "Order: delete first, because it is free. Then hand over by hours a month, never by ease.",
              "Flags: Doing (delivery and admin) above 50% of the week; Strategy below 15%, which gets a protected block of at "
              "least 4 hours.",
              "A month is 52/12 weeks. 'Daily' means each of your working days; 'weekdays' means Monday to Friday."]
    if rate:
        lines.append("Value: hours times your rate. Freed hours earn that only if you fill them with paid or selling work. "
                     "Helper and tool costs are shown only where you gave them.")
    lines += [f"Note: {human_dates(n)}" for n in res.get("notes", [])]
    lines.append("A planning tool, not employment, tax or legal advice.")
    for i, ln in enumerate(lines):
        Bs.set(3 + i, 1, ln, 9)
    Bs.widths[1] = 120
    write_xlsx(path, [S, L, H, W, Bs], sym, f"Founder time audit, {res['business']}")


def log_template(path):
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    times = [f"{h:02d}:{m:02d}" for h in range(6, 24) for m in (0, 30)]
    if str(path).lower().endswith(".csv"):
        lines = ["One-week time log", "Week starting (the date of the first day you log),", "Write what you did in each half hour. Repeat a line with \" or leave it blank if you were not working.",
                 ",".join(["Time"] + days)]
        lines += [",".join([t] + [""] * 7) for t in times]
        Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
        return
    sh = Sheet("Time log")
    sh.set(1, 1, "One-week time log", 8)
    sh.set(2, 1, "Week starting (date)", 1)
    sh.set(2, 2, "", 4)
    sh.set(3, 1, "Write a few words for each half hour as you go (\"client call Fenwick\", \"invoices\", \"email\"). "
                 "Type \" to repeat the line above. Leave a block empty when you were not working. Then attach this file.", 11)
    sh.merges.append("A3:H3")
    sh.set(4, 1, "Time", 2)
    for j, d in enumerate(days, 2):
        sh.set(4, j, d, 2)
    for i, t in enumerate(times):
        sh.set(5 + i, 1, t, 1)
        for j in range(2, 9):
            sh.set(5 + i, j, "", 4)
    sh.freeze = 5
    sh.widths.update({1: 8, **{j: 24 for j in range(2, 9)}})
    write_xlsx(path, [sh], "", "One-week time log")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "log-template":
        ap = argparse.ArgumentParser()
        ap.add_argument("cmd")
        ap.add_argument("--out", required=True)
        a = ap.parse_args()
        log_template(a.out)
        print(f"WROTE: {a.out}")
        return
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("results")
    ap.add_argument("--out", required=True)
    ap.add_argument("--note")
    ap.add_argument("--md")
    a = ap.parse_args()
    try:
        res = json.loads(Path(a.results).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise Stop(f"there is no results file at {a.results}; run rank.py first")
    except json.JSONDecodeError as e:
        raise Stop(f"{a.results} is not valid JSON ({e.msg})")
    if not isinstance(res, dict) or "rows" not in res or "proposed_week" not in res:
        raise Stop(f"{a.results} is not a rank.py results file")
    if res.get("challenges_open"):
        raise Stop("ask the founder once about " + ", ".join(f"'{x}'" for x in res["challenges_open"]) +
                   " (marked only-you but reads as admin, reporting or scheduling), record each answer as challenge_answer, "
                   "and run rank.py again")
    note = ""
    if a.note:
        try:
            note = Path(a.note).read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            raise Stop(f"there is no note at {a.note}")
        note = re.sub(r"\s+", " ", re.sub(r"^#.*$", "", note, flags=re.M)).strip()
        set_style(res)
        probs = check_note(note, res)
        if probs:
            raise Stop("the note fails its check: " + "; ".join(probs) + ". Rewrite it using only figures from rank.py")
    set_style(res)
    B = content(res, note)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    base = f"founder-time-audit-{slug(res['business'])}-{res['date']}"
    docx = out / f"{base}.docx"
    xlsx = out / f"{base}-workings.xlsx"
    try:
        loc = res.get("locale") or {}
        lang = loc.get("lang") or ("en-US" if loc.get("spelling") == "american" or loc.get("date_style") == "mdy" else "en-GB")
        build_docx(B, docx, res["business"], paper=loc.get("paper") or "a4", lang=lang)
        build_workbook(res, xlsx)
    except Exception:
        for p in (docx, xlsx):
            if p.exists():
                p.unlink()
        raise
    md = to_markdown(B)
    if a.md:
        Path(a.md).parent.mkdir(parents=True, exist_ok=True)
        Path(a.md).write_text(md, encoding="utf-8")
        print(f"WROTE: {a.md}")
    print(f"WROTE: {docx}")
    print(f"WROTE: {xlsx}")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Stop as e:
        print(f"STOP: {e}. Nothing was written.")
        sys.exit(2)
    except Exception as e:  # noqa: BLE001
        print(f"STOP: the report could not be written ({type(e).__name__}: {e}). Nothing was written.")
        sys.exit(2)
