#!/usr/bin/env python3
"""Read, write and check the Price Floor Calculator memory file.

Usage:
  python3 scripts/memory.py read <memory.md> [--json-out inputs.json]
        turn a saved memory file back into an inputs file for price_floor.py
  python3 scripts/memory.py changes <old-inputs.json> <new-inputs.json>
        list what changed between two runs (for the return-run summary)
  python3 scripts/memory.py write <inputs.json> --out <memory.md> [--existing <old memory.md>]
        [--history "made | option chosen | verdict"] [--learning "rule | evidence | step | status"]
        write the memory file; keeps the old Learnings and History and appends the new rows
  python3 scripts/memory.py validate <memory.md>
        check the file still has the shape this skill reads

The memory file is plain markdown the founder can read and edit by hand. Write only after the
founder has approved what is saved. Standard library only. No network calls.
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

SKILL = "revos-price-floor-calculator"
PROFILE = [  # field label, inputs key
    ("Business", "business"), ("Currency", "currency"), ("Country", "country"), ("Number style", "decimal"),
    ("Your English", "locale"), ("Your hourly rate", "your_rate"),
    ("Pay you want a year", "target_pay_year"), ("Pay basis", "target_pay_basis"),
    ("Your client hours a week", "your_client_hours_week"), ("Working weeks a year", "working_weeks_year"),
    ("Hours in a working day", "day_hours"),
    ("Target margin", "target_margin"), ("Monthly overheads, excluding your pay", "overheads_month"),
    ("Client hours a week", "client_hours_week"), ("Clients pay by", "paid_by"),
    ("Payment fee rate", "fee_rate"), ("Client hours a week if full", "full_hours_week"),
    ("Largest hours cut for a restructure", "rescope_limit"), ("Figures you confirmed", "confirmed"),
    ("Line at the top of the summary", "pinned_line"),
]
OFFER_COLS = [
    ("Offer", "name"), ("Billing", "billing"), ("Price", "price"), ("Your hours", "your_hours"),
    ("Team hours", "team_hours"), ("Team cost an hour", "team_rate"), ("Contractor", "contractor"),
    ("Tools and other", "tools"), ("Fee rate", "fee_rate"), ("Refunds", "refund_rate"),
    ("Sales a month", "per_month"), ("Alternative", "alternative"), ("Instalments", "instalments"),
    ("Price label", "unit_label"), ("Preferred route", "prefer"),
]
NUMERIC_PROFILE = {"your_rate", "target_pay_year", "your_client_hours_week", "working_weeks_year", "day_hours",
                   "target_margin", "overheads_month", "client_hours_week", "fee_rate", "full_hours_week", "rescope_limit"}
NUMERIC_OFFER = {"price", "your_hours", "team_hours", "team_rate", "contractor", "tools", "fee_rate", "refund_rate",
                 "per_month", "alternative"}
STYLE = {"decimal": None}  # the founder's number style, so the file reads and is written their way
LEARN_HEAD = "| # | Learning | Evidence | Applies to step | Status | Added |"
HIST_HEAD = "| Date | Made | Option chosen | Verdict |"
STATUSES = {"watch", "active", "retired"}
STEPS = {"intake", "diagnose", "make", "check", "deliver", "learn"}


def cell(v):
    if v is None:
        return ""
    if isinstance(v, (list, tuple)):
        v = "; ".join(str(x) for x in v)
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    if isinstance(v, float) and STYLE["decimal"] == "comma":
        v = str(v).replace(".", ",")  # written the founder's way, so a hand edit in the same style reads right
    return str(v).replace("|", "/").replace("\n", " ").strip()


def pct_cell(v):
    s = f"{round(v * 100, 4):g}%"
    return s.replace(".", ",") if STYLE["decimal"] == "comma" else s


def table(text, heading):
    m = re.search(rf"^## {re.escape(heading)}\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not m:
        return None, []
    lines = [ln.strip() for ln in m.group(1).splitlines() if ln.strip().startswith("|")]
    if len(lines) < 2:
        return lines[0] if lines else None, []
    head = [c.strip() for c in lines[0].strip("|").split("|")]
    rows = []
    for ln in lines[2:]:
        cells = [c.strip() for c in ln.strip("|").split("|")]
        rows.append(dict(zip(head, cells + [""] * (len(head) - len(cells)))))
    return lines[0], rows


def cmd_read(a):
    text = Path(a.memory).read_text(encoding="utf-8")
    _h, prof = table(text, "Profile")
    _h, offs = table(text, "Offers")
    upd = re.search(r"Updated:\s*(\d{4}-\d{2}-\d{2})", text)
    when = upd.group(1) if upd else "an earlier run"
    data, sources = {}, {}
    lab2key = dict(PROFILE)
    for r in prof:
        k = lab2key.get(r.get("Field", ""))
        if k and r.get("Value", "") != "":
            data[k] = r["Value"]
            sources[k] = f"saved memory: {r.get('Source', '') or 'founder said'}, {r.get('Updated', '') or when}"
    data["offers"] = []
    for r in offs:
        o = {}
        for lab, k in OFFER_COLS:
            v = r.get(lab, "")
            if v != "":
                o[k] = v
        if o.get("name"):
            data["offers"].append(o)
    data["sources"] = sources
    data["date"] = when  # the saved run's date; set today's date in the new inputs file
    _h, learn = table(text, "Learnings")
    data["_learnings_active"] = [r.get("Learning") for r in learn if r.get("Status", "").lower() == "active"]
    data["_learnings_watch"] = [r.get("Learning") for r in learn if r.get("Status", "").lower() == "watch"]
    data["_memory_updated"] = when
    out = json.dumps(data, indent=2)
    if a.json_out:
        Path(a.json_out).write_text(out, encoding="utf-8")
        print(f"WROTE: {a.json_out} ({len(data['offers'])} offers, {len(data['_learnings_active'])} active learnings)")
    else:
        print(out)


def _norm(v):
    s = str(v if v is not None else "").strip().lower().replace(",", "").replace("£", "").replace("$", "").replace("€", "").replace("₹", "").replace("¥", "")
    try:
        return f"{float(s.rstrip('%')):g}" + ("%" if s.endswith("%") else "")
    except ValueError:
        return s


def changes(old, new):
    out = []
    for lab, k in PROFILE:
        if _norm(old.get(k)) != _norm(new.get(k)) and (old.get(k) or new.get(k)):
            out.append(f"{lab}: {old.get(k) or 'not set'} to {new.get(k) or 'not set'}")
    on = {o.get("name"): o for o in old.get("offers", [])}
    nn = {o.get("name"): o for o in new.get("offers", [])}
    for name in nn:
        if name not in on:
            out.append(f"New offer: {name}")
            continue
        for lab, k in OFFER_COLS[1:]:
            a, b = on[name].get(k), nn[name].get(k)
            if _norm(a) != _norm(b) and (a not in (None, "", 0) or b not in (None, "", 0)):
                out.append(f"{name}, {lab.lower()}: {a if a not in (None, '') else 'not set'} to {b if b not in (None, '') else 'not set'}")
    for name in on:
        if name not in nn:
            out.append(f"Dropped offer: {name}")
    return out


def cmd_changes(a):
    old = json.loads(Path(a.old).read_text(encoding="utf-8"))
    new = json.loads(Path(a.new).read_text(encoding="utf-8"))
    try:  # compare the figures as the calculator reads them, so "1,500" and "1.5k" are the same
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import price_floor as pf
        b0, o0, _n, _d = pf.normalise(old)
        b1, o1, _n, _d = pf.normalise(new)
        ch = pf.norm_changes(b0, o0, b1, o1)
        names0, names1 = {o["name"] for o in o0}, {o["name"] for o in o1}
        ch += [f"new offer: {n}" for n in sorted(names1 - names0)] + [f"dropped offer: {n}" for n in sorted(names0 - names1)]
    except Exception:  # noqa: BLE001
        ch = changes(old, new)
    for c in ch:
        print("CHANGED:", c)
    print(f"{len(ch)} changes")


def flatten_results(res):
    """A results file from price_floor.py build holds the normalised figures; save those."""
    b = res["business"]
    flat = {"date": b.get("date"), "sources": {}}
    pct_keys = {"target_margin", "fee_rate", "rescope_limit"}
    for _lab, k in PROFILE:
        bk = "working_weeks" if k == "working_weeks_year" else k
        if bk in b and b[bk] not in (None, ""):
            srcv = str(b.get(bk + "_src", ""))
            if srcv.startswith(("a placeholder", "[NEED]", "not given", "not asked")):
                continue  # never remember a placeholder as if the founder had said it
            if k == "your_rate" and srcv.startswith("worked out"):
                continue  # keep the pay and hours instead, so a new pay figure re-runs without questions
            if k == "locale" and srcv.startswith("default"):
                continue
            if k in ("working_weeks_year", "day_hours") and srcv.startswith(("default", "assumption")):
                continue  # an assumption is restated each run, never saved as if the founder had said it
            if k == "client_hours_week" and srcv.startswith(("your ", "worked out")):
                continue  # derived each run from your own hours and the offers
            if k in ("decimal", "country") and not b.get(bk):
                continue
            if k == "confirmed" and not b.get(bk):
                continue
            if k == "fee_rate" and srcv.startswith(("clients pay by", "default")):
                continue  # how clients pay is saved; the rate follows from it
            v = b["stated_client_hours_week"] if k == "your_client_hours_week" and b.get("stated_client_hours_week") else b[bk]
            flat[k] = pct_cell(v) if k in pct_keys and isinstance(v, (int, float)) else (
                round(v, 2) if isinstance(v, float) else v)
            flat["sources"][k] = b.get(bk + "_src", "founder said")
    flat["offers"] = []
    for o in res["offers"]:
        x = {}
        for _lab, k in OFFER_COLS:
            v = o.get("plan_text") if k == "instalments" else o.get(k)
            if k == "unit_label":
                v = o.get("unit") if o.get("unit") not in ("each", "a month") else None
            if k == "fee_rate" and o.get("fee_src") == "business default":
                v = None  # only an offer's own fee is saved; the business rate applies otherwise
            if k in ("fee_rate", "refund_rate") and isinstance(v, (int, float)):
                v = pct_cell(v)
            elif isinstance(v, float):
                v = round(v, 2)
            x[k] = v
        flat["offers"].append(x)
    return flat


def cmd_write(a):
    inp = json.loads(Path(a.inputs).read_text(encoding="utf-8"))
    STYLE["decimal"] = (inp.get("business") or {}).get("decimal") if "results" in inp else inp.get("decimal")
    if "results" in inp and "business" in inp:
        inp = flatten_results(inp)
    today = str(inp.get("date") or date.today().isoformat())
    src = inp.get("sources", {}) or {}
    learn_rows, hist_rows = [], []
    if a.existing and Path(a.existing).exists():
        old = Path(a.existing).read_text(encoding="utf-8")
        _h, learn_rows = table(old, "Learnings")
        _h, hist_rows = table(old, "History")
    L = ["# Price Floor Calculator memory", "",
         f"Skill: {SKILL} | Memory version: 1 | Updated: {today}", "",
         "Keep this file. Attach it next time (or leave it in your merigrove-memory folder, or your Claude Project) "
         "and the calculator picks up where you left off. You can edit it by hand.", "",
         "## Profile", "", "| Field | Value | Source | Updated |", "|---|---|---|---|"]
    for lab, k in PROFILE:
        v = inp.get(k)
        if v in (None, ""):
            continue
        s = src.get(k, "founder said")
        m = re.match(r"^saved memory: (.*), (\d{4}-\d{2}-\d{2})$", s)
        when = today
        if m:  # unchanged since the saved run: keep its source and its date
            s, when = m.group(1), m.group(2)
        L.append(f"| {lab} | {cell(v)} | {cell(s)} | {when} |")
    L += ["", "## Offers", "", "| " + " | ".join(c for c, _k in OFFER_COLS) + " |",
          "|" + "---|" * len(OFFER_COLS)]
    for o in inp.get("offers", []):
        L.append("| " + " | ".join(cell(o.get(k)) for _c, k in OFFER_COLS) + " |")
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
        L.append(f"| {r.get('Date', '')} | {r.get('Made', '')} | {r.get('Option chosen', '')} | {r.get('Verdict', '')} |")
    if a.history:
        parts = [p.strip() for p in a.history.split("|")] + ["", "", ""]
        L.append(f"| {today} | {cell(parts[0])} | {cell(parts[1])} | {cell(parts[2])} |")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text("\n".join(L) + "\n", encoding="utf-8")
    probs = validate(Path(a.out).read_text(encoding="utf-8"))
    for p in probs:
        print("PROBLEM:", p)
    print(f"WROTE: {a.out} ({len(inp.get('offers', []))} offers, {n} learnings, {len(hist_rows) + (1 if a.history else 0)} history rows)")
    sys.exit(1 if probs else 0)


def validate(text):
    p = []
    if not re.search(rf"Skill:\s*{SKILL}", text):
        p.append(f"header line 'Skill: {SKILL}' missing")
    if not re.search(r"Updated:\s*\d{4}-\d{2}-\d{2}", text):
        p.append("header has no Updated: YYYY-MM-DD date")
    for h in ("Profile", "Offers", "Learnings", "History"):
        if not re.search(rf"^## {h}\s*$", text, re.M):
            p.append(f"section '## {h}' missing")
    _h, offs = table(text, "Offers")
    if not offs:
        p.append("Offers table is empty")
    for r in offs:
        if not r.get("Offer") or not r.get("Price"):
            p.append(f"offer row without a name or price: {r}")
    p += figure_problems(text)
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


def figure_problems(text):
    """Every figure must read one way in the founder's saved number style; a hand edit such as 1.650 in a file
    saved as 1,234.56 style would read as 1.65, so it is flagged here rather than priced."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import locale_numbers as ln
    _h, prof = table(text, "Profile")
    _h, offs = table(text, "Offers")
    style = {"comma": "comma", "dot": "dot"}.get(next((r.get("Value", "").strip().lower() for r in prof
                                                       if r.get("Field") == "Number style"), ""), None)
    lab2key = dict(PROFILE)
    cells = [(r.get("Field"), r.get("Value", ""), lab2key.get(r.get("Field", ""))) for r in prof]
    for r in offs:
        cells += [(f"{r.get('Offer')}: {lab}", r.get(lab, ""), k) for lab, k in OFFER_COLS]
    out = []
    for lab, v, k in cells:
        if k not in NUMERIC_PROFILE | NUMERIC_OFFER or not v or not re.search(r"\d", v):
            continue
        t = v.rstrip("%").strip()
        if re.search(r"[=+*/x]|\bto\b|-", t):
            continue  # a sum or range: the calculator works it out and stops on anything it cannot read
        try:
            val = ln.parse_number(t, style)[0]
        except ln.Ambiguous:
            out.append(f"{lab}: '{v}' can be read two ways; write it as you write other figures, or set the Number "
                       "style row (1.234,56 is comma, 1,234.56 is dot)")
            continue
        except ln.Unreadable:
            out.append(f"{lab}: '{v}' is not a figure the calculator can read")
            continue
        if k == "price" and val < 10:
            out.append(f"{lab}: '{v}' reads as {val:g}; check it is written in your number style")
    return out


def cmd_validate(a):
    text = Path(a.memory).read_text(encoding="utf-8")
    probs = validate(text)
    _h, prof = table(text, "Profile")
    if not any(r.get("Field") in ("Your hourly rate", "Pay you want a year") and r.get("Value") for r in prof):
        print("NOTE: no hourly rate saved; the next run asks for it")
    for x in probs:
        print("PROBLEM:", x)
    print(f"{len(probs)} problems")
    sys.exit(1 if probs else 0)


def _guard(path):
    if not Path(path).exists():
        print(f"STOP: there is no file at {path}. Nothing was changed.")
        sys.exit(2)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    r = sub.add_parser("read")
    r.add_argument("memory")
    r.add_argument("--json-out")
    c = sub.add_parser("changes")
    c.add_argument("old")
    c.add_argument("new")
    w = sub.add_parser("write")
    w.add_argument("inputs")
    w.add_argument("--out", required=True)
    w.add_argument("--existing")
    w.add_argument("--history")
    w.add_argument("--learning", action="append")
    v = sub.add_parser("validate")
    v.add_argument("memory")
    a = ap.parse_args()
    for attr in ("memory", "old", "new", "inputs"):
        if getattr(a, attr, None):
            _guard(getattr(a, attr))
    {"read": cmd_read, "changes": cmd_changes, "write": cmd_write, "validate": cmd_validate}.get(
        a.cmd, lambda _a: (ap.print_help(), sys.exit(2)))(a)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print(f"STOP: the memory file could not be handled ({type(e).__name__}: {e}). Nothing was changed.")
        sys.exit(2)
