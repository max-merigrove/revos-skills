#!/usr/bin/env python3
"""Read, write and check the Call Review memory file.

Usage:
  python3 scripts/memory.py read <memory.md> --json-out <scratch>/previous.json
        turn a saved memory file into the history the scorer's trend check reads, plus the profile
        and the active learnings
  python3 scripts/memory.py write --results <results.json> --out <memory.md> [--existing <old memory.md>]
        [--profile "Field=Value"]... [--learning "rule | evidence | step | status"]... [--verdict "spot on"]
        [--promote N] [--retire N]
        write the memory file after the founder approves; keeps old learnings and history, adds this
        review's history row (scores only: never a quote, a name or anything else from the transcript)
  python3 scripts/memory.py validate <memory.md>
        check the file still has the shape this skill reads

Profile fields: Business, What you sell, Price, Sellers, Call structure, Typical call length, Currency, Date style,
Spelling, Country, Market. Currency, date style and spelling are the founder's own, read from what they write; never
assumed. --profile "Field=Value | source" sets the source; without one, each field takes its usual source (Spelling and
Currency "read from your messages", Business and What you sell "read from the call" on a transcript review).
A second review of the same call (same Call ID, or for older rows the same date, seller and call type) replaces its
history row instead of adding one, so the pattern check never counts one call twice.
Steps a learning can apply to: Intake, Diagnose, Measure, Score, Coaching, Check, Deliver, Learn.
Exit 0 done; 1 problems in the file; 2 STOP (a file is missing or unreadable). Standard library only.
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

SKILL = "revos-call-review"
PROFILE = ["Business", "What you sell", "Price", "Sellers", "Call structure", "Typical call length", "Currency", "Date style",
           "Spelling", "Country", "Market"]
DEFAULT_SOURCE = {"Spelling": "read from your messages", "Currency": "read from your messages",
                  "Country": "read from your messages", "Date style": "read from how you write dates"}
DIMS = [("Intro and Frame", "IF"), ("Discovery and Gap Build", "DG"), ("Cost of Inaction", "CI"),
        ("Objection Handling", "OH"), ("Close Attempt", "CA")]
LEARN_HEAD = "| # | Learning | Evidence | Applies to step | Status | Added |"
HIST_COLS = ["Date", "Seller", "Call type", "Score", "Weakest", "Scores", "Failures", "Outcome", "Verdict", "Call ID"]
HIST_HEAD = "| " + " | ".join(HIST_COLS) + " |"
HIST_HEAD_V1 = "| " + " | ".join(HIST_COLS[:-1]) + " |"     # files written before 1.2.0 are still read
STATUSES = {"watch", "active", "retired"}
STEPS = {"intake", "diagnose", "measure", "score", "coaching", "check", "deliver", "learn"}


def stop(msg):
    print(f"STOP: {msg}. Nothing was changed.")
    sys.exit(2)


def cell(v):
    return str(v if v is not None else "").replace("|", "/").replace("\n", " ").strip()


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


def parse_scores(s):
    out = {}
    for name, ab in DIMS:
        m = re.search(rf"\b{ab}\s+(\d+)\b", s or "")
        if m:
            out[name] = int(m.group(1))
    return out


def cmd_read(a):
    text = Path(a.memory).read_text(encoding="utf-8")
    _h, prof = table(text, "Profile")
    _h, learn = table(text, "Learnings")
    _h, hist = table(text, "History")
    upd = re.search(r"Updated:\s*(\d{4}-\d{2}-\d{2})", text)
    data = {"updated": upd.group(1) if upd else None,
            "profile": {r.get("Field"): r.get("Value") for r in prof if r.get("Field") and r.get("Value")},
            "learnings_active": [{"learning": r.get("Learning"), "step": r.get("Applies to step")} for r in learn
                                 if r.get("Status", "").strip().lower() == "active"],
            "learnings_watch": [{"learning": r.get("Learning"), "step": r.get("Applies to step")} for r in learn
                                if r.get("Status", "").strip().lower() == "watch"],
            "history": [{"date": r.get("Date"), "seller": r.get("Seller"), "call_type": r.get("Call type"),
                         "score": int(r["Score"]) if (r.get("Score") or "").isdigit() else None,
                         "weakest": r.get("Weakest"), "scores": parse_scores(r.get("Scores")),
                         "failures": r.get("Failures"), "outcome": r.get("Outcome"), "verdict": r.get("Verdict"),
                         "call_id": r.get("Call ID") or None} for r in hist]}
    out = json.dumps(data, indent=1, ensure_ascii=False)
    if a.json_out:
        Path(a.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.json_out).write_text(out, encoding="utf-8")
        print(f"WROTE: {a.json_out} (profile {len(data['profile'])} fields, {len(data['learnings_active'])} active learnings, "
              f"{len(data['history'])} earlier reviews)")
    else:
        print(out)


def cmd_write(a):
    res = json.loads(Path(a.results).read_text(encoding="utf-8"))
    if "verdicts" not in res or "overall" not in res:
        stop(f"{a.results} is not a results file from score_call.py")
    v = res["verdicts"]
    today = date.today().isoformat()
    old_prof, learn_rows, hist_rows = {}, [], []
    if a.existing:
        if not Path(a.existing).exists():
            stop(f"there is no memory file at {a.existing}")
        old = Path(a.existing).read_text(encoding="utf-8")
        _h, pr = table(old, "Profile")
        old_prof = {r.get("Field"): r for r in pr if r.get("Field")}
        _h, learn_rows = table(old, "Learnings")
        _h, hist_rows = table(old, "History")
    prof = {k: dict(r) for k, r in old_prof.items()}

    def setp(field, value, source):
        if field not in PROFILE:
            stop(f"'{field}' is not a profile field; use one of {', '.join(PROFILE)}")
        if value in (None, ""):
            return
        cur = prof.get(field)
        if cur and cur.get("Value") == str(value):
            return
        prof[field] = {"Field": field, "Value": cell(value), "Source": source, "Updated": today}

    src = v.get("sources") or {}
    read = "founder said" if res.get("mode") == "recall" else "read from the call"
    if v.get("business"):
        setp("Business", v["business"], src.get("business") or read)
    if v.get("offer"):
        setp("What you sell", v["offer"], src.get("offer") or read)
    sellers = [s.strip() for s in (prof.get("Sellers", {}).get("Value") or "").split(",") if s.strip()]
    if v.get("seller") and v["seller"] not in sellers:
        sellers.append(v["seller"])
        setp("Sellers", ", ".join(sellers), "founder said")
    if v.get("date_style"):
        setp("Date style", v["date_style"], "read from how you write dates")
    if isinstance(v.get("structure"), list) and v["structure"]:
        setp("Call structure", "; ".join(str(s.get("name") if isinstance(s, dict) else s) for s in v["structure"]), "founder pasted")
    for x in a.profile or []:
        if "=" not in x:
            stop(f"--profile takes Field=Value, not '{x}'")
        k, val = x.split("=", 1)
        val, _sep, source = val.partition(" | ")
        setp(k.strip(), val.strip(), source.strip() or DEFAULT_SOURCE.get(k.strip(), "founder said"))

    L = ["# Call Review memory", "",
         f"Skill: {SKILL} | Memory version: 1 | Updated: {today}", "",
         "Keep this file. Attach it next time (or leave it in your merigrove-memory folder, or your Claude Project) and the "
         "next review skips what it already knows and checks for patterns across your calls. You can edit it by hand. "
         "It holds scores only: no transcript, no quotes, no prospect names.", "",
         "## Profile", "", "| Field | Value | Source | Updated |", "|---|---|---|---|"]
    for f in PROFILE:
        r = prof.get(f)
        if r and r.get("Value"):
            L.append(f"| {f} | {cell(r.get('Value'))} | {cell(r.get('Source') or 'founder said')} | {cell(r.get('Updated') or today)} |")
    L += ["", "## Learnings", "", LEARN_HEAD, "|---|---|---|---|---|---|"]
    n = 0
    promote = {int(x) for x in (a.promote or [])}
    retire = {int(x) for x in (a.retire or [])}
    for r in learn_rows:
        n += 1
        status = r.get("Status", "")
        learning = r.get("Learning", "")
        evidence = r.get("Evidence", "")
        if n in promote and status != "active":
            status = "active"
            evidence = f"{evidence}; repeated or approved {today}"
        if n in retire:
            status = "retired"
            learning = learning if learning.startswith("~~") else f"~~{learning}~~"
        L.append(f"| {n} | {learning} | {cell(evidence)} | {r.get('Applies to step', '')} | "
                 f"{status} | {r.get('Added', '')} |")
    for x in a.learning or []:
        parts = [p.strip() for p in x.split("|")] + ["", "", "", ""]
        n += 1
        L.append(f"| {n} | {cell(parts[0])} | {cell(parts[1])} | {cell(parts[2] or 'Coaching')} | {cell(parts[3] or 'watch')} | {today} |")
    L += ["", "Status: watch (seen once), active (approved or repeated), retired (kept for the record, no longer applied).",
          "", "## History", "", HIST_HEAD, "|" + "---|" * len(HIST_COLS)]
    rows = [{h: cell(r.get(h)) for h in HIST_COLS} for r in hist_rows]
    replaced = False
    if not a.no_history:
        sc = ", ".join(f"{ab} {res['scores'][d]}" for d, ab in DIMS)
        names = {"pitched_before_pain": "pitched before pain", "frame_no_control": "control handed over",
                 "coi_missing_then_stall": "no cost then a stall", "folded": "folded"}
        caps = ", ".join(dict.fromkeys(names.get(f.get("flag"), str(f.get("flag"))) for f in res.get("flags", []))) or "none"
        new = {"Date": cell(v.get("call_date") or today), "Seller": cell(v.get("seller")), "Call type": cell(v.get("call_type")),
               "Score": str(res["overall"]), "Weakest": cell(res.get("weakest")), "Scores": sc, "Failures": caps,
               "Outcome": cell(v.get("outcome")), "Verdict": cell(a.verdict or "not asked"), "Call ID": cell(res.get("call_id"))}
        for i, r in enumerate(rows):
            same = (r.get("Call ID") == new["Call ID"]) if r.get("Call ID") and new["Call ID"] else (
                r["Date"] == new["Date"] and r["Seller"].lower() == new["Seller"].lower()
                and r["Call type"].lower() == new["Call type"].lower())
            if same:
                rows[i] = new
                replaced = True
                break
        if not replaced:
            rows.append(new)
    for r in rows:
        L.append("| " + " | ".join(r.get(h, "") for h in HIST_COLS) + " |")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text("\n".join(L) + "\n", encoding="utf-8")
    probs = validate(Path(a.out).read_text(encoding="utf-8"))
    for p in probs:
        print("PROBLEM:", p)
    print(f"WROTE: {a.out} ({len(prof)} profile fields, {n} learnings, {len(rows)} reviews in history"
          + ("; this call was already in history, so its row was replaced, not added" if replaced else "") + ")")
    sys.exit(1 if probs else 0)


def validate(text):
    p = []
    if not re.search(rf"Skill:\s*{SKILL}\b", text):
        p.append(f"header line 'Skill: {SKILL}' missing")
    if not re.search(r"Updated:\s*\d{4}-\d{2}-\d{2}", text):
        p.append("header has no Updated: YYYY-MM-DD date")
    for h in ("Profile", "Learnings", "History"):
        if not re.search(rf"^## {h}\s*$", text, re.M):
            p.append(f"section '## {h}' missing")
    _h, prof = table(text, "Profile")
    for r in prof:
        if r.get("Field") not in PROFILE:
            p.append(f"profile field '{r.get('Field')}' is not one this skill reads")
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
    h, hist = table(text, "History")
    if h and h not in (HIST_HEAD, HIST_HEAD_V1):
        p.append("History header changed; expected: " + HIST_HEAD)
    for r in hist:
        if any('"' in (x or "") or "\u201c" in (x or "") for x in r.values()):
            p.append(f"history row {r.get('Date')} holds a quotation; memory keeps scores only, never transcript words")
        if r.get("Score") and not r["Score"].isdigit():
            p.append(f"history row {r.get('Date')}: score '{r.get('Score')}' is not a whole number")
        if r.get("Scores") and len(parse_scores(r["Scores"])) != 5:
            p.append(f"history row {r.get('Date')}: scores must read 'IF n, DG n, CI n, OH n, CA n'")
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
    r.add_argument("--json-out")
    w = sub.add_parser("write")
    w.add_argument("--results", required=True)
    w.add_argument("--out", required=True)
    w.add_argument("--existing")
    w.add_argument("--profile", action="append")
    w.add_argument("--learning", action="append")
    w.add_argument("--verdict")
    w.add_argument("--promote", action="append", help="learning number to make active (founder approved or repeated it)")
    w.add_argument("--retire", action="append", help="learning number to retire (kept, struck through)")
    w.add_argument("--no-history", action="store_true")
    v = sub.add_parser("validate")
    v.add_argument("memory")
    a = ap.parse_args()
    for attr in ("memory", "results"):
        if getattr(a, attr, None) and not Path(getattr(a, attr)).exists():
            stop(f"there is no file at {getattr(a, attr)}")
    {"read": cmd_read, "write": cmd_write, "validate": cmd_validate}.get(a.cmd, lambda _a: (ap.print_help(), sys.exit(2)))(a)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print(f"STOP: the memory file could not be handled ({type(e).__name__}: {e}). Nothing was changed.")
        sys.exit(2)
