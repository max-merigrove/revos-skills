#!/usr/bin/env python3
"""Read, write and check the Founder Time Audit memory file.

Usage:
  python3 scripts/memory.py read <memory.md> --out <folder>
        writes <folder>/map.json (saved activity rules for parse_calendar.py --map),
        <folder>/previous.json (last audit and handovers, for rank.py --previous) and
        <folder>/defaults.json (profile values and remembered rows to copy into the audit file)
  python3 scripts/memory.py write <results.json> --out <memory.md> [--map <map.json>] [--existing <old memory.md>]
        [--history "made | option chosen | verdict"] [--learning "rule | evidence | step | status"]
  python3 scripts/memory.py validate <memory.md>

What is saved: business facts the founder gave, the untracked hours the calendar missed, each recurring
activity's label with its category, function, action and owner, the last audit's shares, the
handovers with their hours, learnings and a history line. What is never saved: personal or
not-work entries, attendee names or emails, event descriptions, or anything the founder did not
approve. Write only after the founder has approved. Standard library only. No network calls.
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

SKILL = "revos-founder-time-audit"
PROFILE = ["Business", "Currency", "Country", "Number style", "Dates and spelling", "Hours worked a week, last time",
           "Hours a week the calendar misses", "Your hourly rate", "Monthly sales", "Time zone", "Working hours",
           "Working days", "Freed hours go to", "Work that stays with you", "Team"]
ACT_HEAD = "| Match | Activity | Category | Function | Action | Who or how | Why | Hours each | How often |"
AUDIT_HEAD = "| Field | Value |"
HAND_HEAD = "| Activity | Action | Who or how | Hours a week then | Set on | Status |"
LEARN_HEAD = "| # | Learning | Evidence | Applies to step | Status | Added |"
HIST_HEAD = "| Date | Made | Option chosen | Verdict |"
STATUSES = {"watch", "active", "retired"}
STEPS = {"intake", "diagnose", "make", "check", "deliver", "learn"}
CAT_WORDS = {1: "Only you", 2: "With instruction", 3: "Nobody should"}
NOT_WORK = "Not work"  # placeholder holds and buffers, saved so they stay out on a return run; personal rules never are
WPM = 52 / 12


def cell(v):
    """A table cell. A pipe inside a value (a regex rule such as re:(clinet|client) sync) is escaped as \\| so the
    table keeps its shape and the rule comes back unchanged."""
    if v is None:
        return ""
    if isinstance(v, float):
        v = round(v, 2)
        if v.is_integer():
            v = int(v)
    return str(v).replace("\\|", "|").replace("|", "\\|").replace("\n", " ").strip()


def split_row(line):
    """Split a markdown table row on unescaped pipes, and unescape \\| inside each cell."""
    inner = line.strip()
    if inner.startswith("|"):
        inner = inner[1:]
    if inner.endswith("|") and not inner.endswith("\\|"):
        inner = inner[:-1]
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", inner)]


def plain(x, dp=2):
    """A number saved plainly (no thousands separator, a dot for decimals) so any founder's style reads it back."""
    if x is None:
        return None
    v = round(float(x), dp)
    return str(int(v)) if v.is_integer() else f"{v:.{dp}f}".rstrip("0").rstrip(".")


def table(text, heading):
    m = re.search(rf"^## {re.escape(heading)}\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not m:
        return None, []
    lines = [ln.strip() for ln in m.group(1).splitlines() if ln.strip().startswith("|")]
    if len(lines) < 2:
        return (lines[0] if lines else None), []
    head = split_row(lines[0])
    rows = []
    for ln in lines[2:]:
        cells = split_row(ln)
        rows.append(dict(zip(head, cells + [""] * (len(head) - len(cells)))))
    return lines[0], rows


def stop(msg):
    print(f"STOP: {msg}. Nothing was changed.")
    sys.exit(2)


def cat_num(s):
    s = str(s).strip().lower()
    for k, v in CAT_WORDS.items():
        if s == v.lower() or s == str(k):
            return k
    if s == NOT_WORK.lower():
        return "not work"
    return s or None


def cmd_read(a):
    text = Path(a.memory).read_text(encoding="utf-8")
    probs = validate(text)
    if probs:
        stop("the memory file has lost its shape (" + "; ".join(probs) + "). Run as a first time, or fix the file by hand")
    upd = re.search(r"Updated:\s*(\d{4}-\d{2}-\d{2})", text)
    when = upd.group(1) if upd else None
    _h, prof = table(text, "Profile")
    p = {r["Field"]: r["Value"] for r in prof if r.get("Value")}
    _h, acts = table(text, "Activities")
    rules, recall = [], []
    for r in acts:
        row = {"activity": r.get("Activity"), "category": cat_num(r.get("Category")), "function": (r.get("Function") or "").lower() or None,
               "action": (r.get("Action") or "").lower() or None, "who": r.get("Who or how") or None, "reason": r.get("Why") or None}
        if r.get("Match") in ("(told me)", ""):
            row.update({"source": "recall", "hours_each": r.get("Hours each") or None, "per_month": r.get("How often") or None,
                        "remembered": True})
            recall.append(row)
        elif r.get("Match"):
            rules.append({"match": r["Match"], **{k: v for k, v in row.items() if v not in (None, "")}})
    _h, aud = table(text, "Last audit")
    la = {r["Field"]: r["Value"] for r in aud}
    _h, hands = table(text, "Handovers")
    _h, learn = table(text, "Learnings")
    team = []
    cost_rx = r",\s*((?:[A-Z]{1,3}\s?)?[$£€¥₹₱₩฿]?\s?\d[\d,.]*(?:\s?[€£])?)\s*(?:an hour|/\s*h(?:ou)?r|per hour|an hr)"
    spare_rx = (r",\s*(\d+(?:[.,]\d+)?(?:\s*(?:-|to)\s*\d+(?:[.,]\d+)?)?)\s*(?:spare\s+)?(?:hours?|hrs?|h)?\b"
                r"(?:\s*(?:/\s*wk|/\s*week|a week|per week|weekly))?(?:\s+spare)?(?:\s+hours?)?(?:\s+a week)?(?=\s*(?:,|$))")
    for part in [x.strip() for x in (p.get("Team") or "").split(";") if x.strip()]:
        nm, _sep, rest = part.partition(":")
        t = {"name": nm.strip()}
        mc = re.search(cost_rx, rest, re.I)
        if mc:
            t["cost_hour"] = mc.group(1).strip()
            rest = rest[:mc.start()] + rest[mc.end():]
        ms = [m for m in re.finditer(spare_rx, rest, re.I) if re.search(r"spare|week|wk", m.group(0), re.I)]
        if ms:
            t["spare_week"] = ms[-1].group(1)
            rest = rest[:ms[-1].start()] + rest[ms[-1].end():]
        t["role"] = rest.strip().strip(",").strip()
        team.append(t)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "map.json").write_text(json.dumps({"rules": rules}, indent=2), encoding="utf-8")
    prev = {"_memory_updated": when,
            "last_audit": {"date": la.get("Date"), "week_hours": la.get("Hours worked a week"),
                           "only_share": la.get("Only you"), "nobody_share": la.get("Nobody should"),
                           "doing_share": la.get("Doing"), "strategy_share": la.get("Strategy")},
            "handovers": [{"activity": h.get("Activity"), "action": (h.get("Action") or "").lower(), "who": h.get("Who or how"),
                           "weekly_hours": h.get("Hours a week then"), "status": h.get("Status")} for h in hands]}
    (out / "previous.json").write_text(json.dumps(prev, indent=2), encoding="utf-8")
    ds = (p.get("Dates and spelling") or "").lower()
    nsty = (p.get("Number style") or "").strip()
    locale = {k: v for k, v in {"date_style": "mdy" if "month first" in ds else ("dmy" if "day first" in ds else None),
                                "spelling": "american" if "american" in ds else ("british" if "british" in ds else None),
                                "country": (p.get("Country") or "").strip().upper()[:2] or None,
                                "decimal": "comma" if nsty.startswith("1.234,5") else ("dot" if nsty.startswith("1,234.5") else None),
                                "symbol_after": True if "after" in nsty else None}.items() if v}
    defaults = {"business": p.get("Business"), "currency": p.get("Currency") or None, "locale": locale,
                "untracked_week_hours": p.get("Hours a week the calendar misses"),
                "rate": p.get("Your hourly rate"), "monthly_revenue": p.get("Monthly sales"),
                "tz": p.get("Time zone"), "work_hours": work_hours_back(p.get("Working hours")), "work_days": p.get("Working days") or p.get("Working days a week"),
                "freed_to": p.get("Freed hours go to"),
                "protected": [x.strip() for x in (p.get("Work that stays with you") or "").split(";") if x.strip()],
                "team": team, "last_week_hours": p.get("Hours worked a week, last time"),
                "remembered_rows": recall,
                "learnings_active": [r.get("Learning") for r in learn if r.get("Status", "").strip().lower() == "active"],
                "learnings_watch": [r.get("Learning") for r in learn if r.get("Status", "").strip().lower() == "watch"]}
    (out / "defaults.json").write_text(json.dumps(defaults, indent=2), encoding="utf-8")
    print(f"WROTE: {out / 'map.json'} ({len(rules)} activity rules), {out / 'previous.json'} "
          f"({len(prev['handovers'])} handovers from {la.get('Date') or when}), {out / 'defaults.json'} "
          f"({len(defaults['learnings_active'])} active learnings, {len(recall)} remembered rows)")


def work_hours_back(v):
    """'7:30-19; Sat 7:30-12:30' back to the map rank.py reads; a single span stays a string."""
    if not v or ";" not in v:
        return v
    parts = [x.strip() for x in v.split(";") if x.strip()]
    out = {"default": parts[0]}
    for x in parts[1:]:
        day, _sp, span = x.partition(" ")
        out[day.lower()] = span.strip()
    return out


def dates_and_spelling(loc):
    parts = []
    if loc.get("date_style"):
        parts.append("month first" if loc["date_style"] == "mdy" else "day first")
    if loc.get("spelling"):
        parts.append(f"{loc['spelling'].capitalize()} spelling")
    return ", ".join(parts) or None


def wh_text(res):
    wp = res.get("work_pattern") or {}
    if not wp.get("known"):
        return None
    f = lambda h: f"{int(h)}:{int(round((h - int(h)) * 60)):02d}" if h % 1 else f"{int(h)}"  # noqa: E731
    own = wp.get("own_hours") or {}
    extra = "".join(f"; {d[:3]} {f(v[0])}-{f(v[1])}" for d, v in own.items())
    return f"{f(wp['start'])}-{f(wp['end'])}{extra}"


def pat_src(res):
    return {"founder": "founder said", "calendar settings": "your Outlook working-hours setting",
            "calendar": "what your calendar showed"}.get((res.get("work_pattern") or {}).get("source"), "founder said")


def cmd_write(a):
    res = json.loads(Path(a.results).read_text(encoding="utf-8"))
    if "rows" not in res:
        stop(f"{a.results} is not a rank.py results file")
    today = str(res.get("date") or date.today().isoformat())
    rules = []
    if a.map:
        m = json.loads(Path(a.map).read_text(encoding="utf-8"))
        rules = m.get("rules", m) if isinstance(m, dict) else m
    old_text = Path(a.existing).read_text(encoding="utf-8") if a.existing and Path(a.existing).exists() else ""
    learn_rows, hist_rows, old_prof, old_set = [], [], {}, {}
    if old_text:
        _h, learn_rows = table(old_text, "Learnings")
        _h, hist_rows = table(old_text, "History")
        _h, pr = table(old_text, "Profile")
        old_prof = {r["Field"]: r for r in pr}
        _h, oh = table(old_text, "Handovers")
        old_set = {r.get("Activity"): r.get("Set on") for r in oh}
        if not rules:
            _h, oa = table(old_text, "Activities")
            rules = [{"match": r["Match"], "activity": r["Activity"], "category": cat_num(r.get("Category"))}
                     for r in oa if r.get("Match") not in ("", "(told me)")]
    sym = res.get("symbol") or ""
    per = res.get("period") or {}
    wk = res["week"]
    team = "; ".join(
        f"{t.get('name')}: {t.get('role') or ''}".strip().rstrip(":")
        + (f", {sym}{plain(t['cost_hour_value'])} an hour" if t.get("cost_hour_value") is not None else "")
        + (f", {plain(t['spare_week_value'])} spare hours a week" if t.get("spare_week_value") is not None else "")
        for t in res.get("team") or [] if isinstance(t, dict) and t.get("name"))
    ns = res.get("number_style") or {}
    num_style = None
    if ns.get("decimal"):
        num_style = ("1.234,56" if ns["decimal"] == "comma" else "1,234.56") + (", symbol after" if ns.get("symbol_after") else "")
    loc = res.get("locale") or {}
    untracked = wk.get("untracked") if res.get("source") not in ("recall",) and wk.get("calendar_week") else None
    prof_vals = {
        "Business": (res.get("business"), "founder said"),
        "Currency": (res.get("currency") or (res.get("symbol") or "").strip() or None, "founder said"),
        "Country": (loc.get("country"), {"founder": "founder said"}.get(loc.get("country_source"), f"from {loc.get('country_source')}")),
        "Number style": (num_style, "founder's own figures"),
        "Dates and spelling": (dates_and_spelling(res.get("locale") or {}), "founder's own writing"),
        "Hours worked a week, last time": (plain(wk["hours"], 1), wk["source"]),
        "Hours a week the calendar misses": (plain(untracked, 1) if untracked else None, "last audit: your week less your calendar"),
        "Your hourly rate": (plain(res["rates"].get("stated")), "founder said"),
        "Monthly sales": (plain(res["rates"].get("monthly_revenue")), "founder said"),
        "Time zone": (per.get("tz"), "calendar export"),
        "Working hours": (wh_text(res), pat_src(res)),
        "Working days": (", ".join(d[:3] for d in (res.get("work_pattern") or {}).get("days") or []) or None, pat_src(res)),
        "Freed hours go to": (res["plan"].get("freed_to"), "founder said or default"),
        "Work that stays with you": ("; ".join(res.get("protected") or []), "founder said"),
        "Team": (team, "founder said"),
    }
    L = ["# Founder Time Audit memory", "", f"Skill: {SKILL} | Memory version: 1 | Updated: {today}", "",
         "Keep this file. Attach it next time (or leave it in your merigrove-memory folder, or your Claude Project) and the "
         "audit picks up where you left off. It holds activity labels and your decisions only: no personal entries, "
         "no names of the people you meet, no event details. You can edit it by hand.", "",
         "## Profile", "", "| Field | Value | Source | Updated |", "|---|---|---|---|"]
    for f in PROFILE:
        v, s = prof_vals[f]
        if v in (None, "", 0):
            continue
        old = old_prof.get(f)
        when = old["Updated"] if old and old.get("Value") == cell(v) else today
        L.append(f"| {f} | {cell(v)} | {cell(old['Source'] if old and old.get('Value') == cell(v) else s)} | {when} |")
    L += ["", "## Activities", "", "Saved rules: a calendar entry whose title contains Match becomes Activity, already sorted. "
          "Rows matched as (told me) are hours you described rather than calendar entries.", "", ACT_HEAD,
          "|---|---|---|---|---|---|---|---|---|"]
    by = {x["activity"]: x for x in res["rows"]}
    seen = set()
    for r in rules:
        catl = str(r.get("category", "")).lower()
        if catl == "personal":
            continue  # personal entries are never remembered
        if catl == "not work":  # a placeholder hold or buffer: its rule is kept, so it stays out next time
            key = (r.get("match"), r.get("activity"))
            if key in seen or PRIVATE.search(f"{r.get('match')} {r.get('activity')}"):
                continue
            seen.add(key)
            L.append(f"| {cell(r.get('match'))} | {cell(r.get('activity') or 'Not work')} | {NOT_WORK} |  |  |  | "
                     f"{cell(r.get('reason') or 'not work time; left out of the hours')} |  |  |")
            continue
        x = by.get(r.get("activity"))
        if x is None:
            continue
        key = (r.get("match"), x["activity"])
        if key in seen:
            continue
        seen.add(key)
        L.append(f"| {cell(r.get('match'))} | {cell(x['activity'])} | {CAT_WORDS[x['category']]} | {cell(x['function_label'])} | "
                 f"{x['action'].capitalize()} | {cell(x['who'])} | {cell(x['reason'])} |  |  |")
    for x in res["rows"]:
        if x["source"] in ("recall", "estimate", "told me"):
            L.append(f"| (told me) | {cell(x['activity'])} | {CAT_WORDS[x['category']]} | {cell(x['function_label'])} | "
                     f"{x['action'].capitalize()} | {cell(x['who'])} | {cell(x['reason'])} | {plain(x['hours_each'])} | "
                     f"{plain(x['per_month'])} a month |")
    c, f = res["categories"], res["functions"]
    L += ["", "## Last audit", "", AUDIT_HEAD, "|---|---|",
          f"| Date | {today} |", f"| Hours worked a week | {cell(round(wk['hours'], 1))} |",
          f"| Only you | {round(c['1']['share'] * 100)}% |", f"| With instruction | {round(c['2']['share'] * 100)}% |",
          f"| Nobody should | {round(c['3']['share'] * 100)}% |", f"| Doing | {round(f['doing']['share'] * 100)}% |",
          f"| Strategy | {round(f['strategy']['share'] * 100)}% |", f"| Confidence | {res['confidence']} |",
          "", "## Handovers", "", HAND_HEAD, "|---|---|---|---|---|---|"]
    prev_status = {h["activity"]: h["status"] for h in (res.get("previous") or {}).get("handovers", [])}
    for n in res["deletions"] + res["handovers"]:
        x = by[n]
        L.append(f"| {cell(n)} | {x['action'].capitalize()} | {cell(x['who'])} | {plain(x['weekly_hours'])} | {old_set.get(n) or today} | "
                 f"{prev_status.get(n, 'set')} |")
    L += ["", "## Learnings", "", LEARN_HEAD, "|---|---|---|---|---|---|"]
    n = 0
    for r in learn_rows:
        n += 1
        L.append(f"| {n} | {cell(r.get('Learning', ''))} | {cell(r.get('Evidence', ''))} | {cell(r.get('Applies to step', ''))} | "
                 f"{cell(r.get('Status', ''))} | {cell(r.get('Added', ''))} |")
    for x in a.learning or []:
        parts = [q.strip() for q in x.split("|")] + ["", "", "", ""]
        n += 1
        L.append(f"| {n} | {cell(parts[0])} | {cell(parts[1])} | {cell(parts[2] or 'Make')} | {cell(parts[3] or 'watch')} | {today} |")
    L += ["", "Status: watch (seen once), active (approved or repeated), retired (kept for the record, no longer applied).",
          "", "## History", "", HIST_HEAD, "|---|---|---|---|"]
    for r in hist_rows:
        L.append(f"| {cell(r.get('Date', ''))} | {cell(r.get('Made', ''))} | {cell(r.get('Option chosen', ''))} | {cell(r.get('Verdict', ''))} |")
    if a.history:
        parts = [q.strip() for q in a.history.split("|")] + ["", "", ""]
        L.append(f"| {today} | {cell(parts[0])} | {cell(parts[1])} | {cell(parts[2])} |")
    text = "\n".join(L) + "\n"
    probs = validate(text)
    for q in probs:
        print("PROBLEM:", q)
    if probs:
        stop("the memory file would not be valid")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(text, encoding="utf-8")
    print(f"WROTE: {a.out} ({len(seen)} activity rules, {n} learnings, {len(hist_rows) + (1 if a.history else 0)} history rows)")


PRIVATE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+|\b(dentist|doctor|gp|school|nursery|therapy|counselling|hospital|kids?)\b", re.I)


def validate(text):
    p = []
    if not re.search(rf"Skill:\s*{SKILL}", text):
        p.append(f"header line 'Skill: {SKILL}' missing")
    if not re.search(r"Updated:\s*\d{4}-\d{2}-\d{2}", text):
        p.append("header has no Updated: YYYY-MM-DD date")
    for h in ("Profile", "Activities", "Last audit", "Handovers", "Learnings", "History"):
        if not re.search(rf"^## {h}\s*$", text, re.M):
            p.append(f"section '## {h}' missing")
    h, acts = table(text, "Activities")
    if h and h != ACT_HEAD:
        p.append("Activities header changed; expected: " + ACT_HEAD)
    for r in acts:
        if not r.get("Activity"):
            p.append(f"activity row without a name: {r}")
        if PRIVATE.search(" ".join(r.values())):
            p.append(f"activity row holds personal details: {r.get('Activity')}")
    h, hands = table(text, "Handovers")
    if h and h != HAND_HEAD:
        p.append("Handovers header changed; expected: " + HAND_HEAD)
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
    text = Path(a.memory).read_text(encoding="utf-8")
    probs = validate(text)
    for x in probs:
        print("PROBLEM:", x)
    print(f"{len(probs)} problems")
    sys.exit(1 if probs else 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    r = sub.add_parser("read")
    r.add_argument("memory")
    r.add_argument("--out", required=True)
    w = sub.add_parser("write")
    w.add_argument("results")
    w.add_argument("--out", required=True)
    w.add_argument("--map")
    w.add_argument("--existing")
    w.add_argument("--history")
    w.add_argument("--learning", action="append")
    v = sub.add_parser("validate")
    v.add_argument("memory")
    a = ap.parse_args()
    for attr in ("memory", "results", "map"):
        val = getattr(a, attr, None)
        if val and not Path(val).exists():
            stop(f"there is no file at {val}")
    {"read": cmd_read, "write": cmd_write, "validate": cmd_validate}.get(
        a.cmd, lambda _a: (ap.print_help(), sys.exit(2)))(a)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print(f"STOP: the memory file could not be handled ({type(e).__name__}: {e}). Nothing was changed.")
        sys.exit(2)
