#!/usr/bin/env python3
"""Read, write and validate the Lead Magnet Factory memory file.

Usage:
  python3 scripts/memory_tool.py read <memory.md> [--json-out memory.json]
  python3 scripts/memory_tool.py write --out <memory.md> [--existing <old memory.md>] [--today YYYY-MM-DD]
        [--profile "Field=Value | source"] ...
        [--magnet "title | format | tier names or item count | topic | subject lines separated by ;"] ...
        [--learning "rule | evidence | step | status"] ... [--retire <learning number>] ...
        [--history "what was made | option chosen | verdict"] ...
  python3 scripts/memory_tool.py validate <memory.md>

Four sections: Profile, Magnets built, Learnings, History. Writing keeps every earlier row; a retired learning
stays, struck through. Dates in Magnets built and History are written in the founder's own date order (from the
Country field). Call write only after the founder approves what will be saved. Never pass anything the founder
did not give: no placeholders, no [NEED] items, no reader's personal data.
Exit 0 done; 1 PROBLEM lines (validate); 2 STOP. Standard library only. No network calls.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

SECTIONS = ["Profile", "Magnets built", "Learnings", "History"]
HEADERS = {
    "Profile": ["Field", "Value", "Source", "Updated"],
    "Magnets built": ["Date", "Title", "Format", "Tiers or items", "Topic", "Subject lines used"],
    "Learnings": ["#", "Learning", "Evidence", "Applies to step", "Status", "Added"],
    "History": ["Date", "Made", "Option chosen", "Verdict"],
}
STEPS = {"Start", "Memory check", "Intake", "Diagnose", "Make", "Check", "Deliver", "Learn", "Topic", "Format",
         "Questions", "Fit", "Tiers", "Emails", "Look"}
STATUS = {"watch", "active", "retired"}
NEVER = re.compile(r"\[NEED|\[YOUR|<[a-z ]+>|TBC|lorem", re.I)


def cell(s):
    return str(s).replace("|", "/").replace("\n", " ").strip()


def parse(path):
    if not os.path.exists(path):
        raise C.Stop(f"cannot find the memory file {path}. Run as a first run.")
    text = C.read_text(path)
    data = {s: [] for s in SECTIONS}
    sec = None
    for line in text.splitlines():
        if line.startswith("## "):
            sec = line[3:].strip()
            data.setdefault(sec, [])
            continue
        if sec and line.strip().startswith("|") and not re.match(r"^\|[\s:|-]+\|$", line.strip()):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if sec in HEADERS and [c.lower() for c in cells] == [h.lower() for h in HEADERS[sec]]:
                continue
            data[sec].append(cells)
    return data


def to_json(data):
    prof = {}
    for r in data["Profile"]:
        if len(r) >= 2 and r[0]:
            prof[r[0]] = {"value": r[1], "source": r[2] if len(r) > 2 else "", "updated": r[3] if len(r) > 3 else ""}
    learn = []
    for r in data["Learnings"]:
        if len(r) >= 5:
            struck = r[1].startswith("~~")
            learn.append({"n": r[0], "rule": r[1].strip("~"), "evidence": r[2], "step": r[3],
                          "status": "retired" if struck else r[4].lower(), "added": r[5] if len(r) > 5 else ""})
    mags = [dict(zip(HEADERS["Magnets built"], r)) for r in data["Magnets built"] if len(r) >= 5]
    subjects = []
    for mg in mags:
        subjects += [s.strip() for s in mg.get("Subject lines used", "").split(";") if s.strip()]
    return {"profile": prof, "learnings": learn, "magnets": mags, "history": data["History"],
            "past_subjects": subjects, "past_topics": [mg.get("Topic") for mg in mags]}


def render(data, today):
    out = ["# Lead Magnet Factory memory", "",
           f"Skill: revos-lead-magnet-factory | Memory version: 1 | Updated: {today.isoformat()}", "",
           "Keep this file. Attach it next time (or leave it in your merigrove-memory folder, or your Claude "
           "Project) and the next lead magnet starts from what is here. You can edit it by hand.", ""]
    for s in SECTIONS:
        out.append(f"## {s}")
        out.append("")
        h = HEADERS[s]
        out.append("| " + " | ".join(h) + " |")
        out.append("|" + "---|" * len(h))
        for r in data[s]:
            r = (list(r) + [""] * len(h))[:len(h)]
            out.append("| " + " | ".join(cell(c) for c in r) + " |")
        if s == "Learnings":
            out.append("")
            out.append("Status: watch (seen once), active (approved or repeated), retired (kept for the record, no "
                       "longer applied).")
        out.append("")
    return "\n".join(out)


def validate(data, quiet=False):
    problems = []
    for s in SECTIONS:
        if s not in data:
            problems.append(f"section '{s}' is missing")
    for r in data.get("Learnings", []):
        if len(r) < 6:
            problems.append(f"learning row has {len(r)} cells, needs 6: {r}")
            continue
        st = r[4].lower()
        if st not in STATUS:
            problems.append(f"learning {r[0]}: status '{r[4]}' must be watch, active or retired")
        if r[3] not in STEPS:
            problems.append(f"learning {r[0]}: step '{r[3]}' is not a step this skill has ({', '.join(sorted(STEPS))})")
    active = sum(1 for r in data.get("Learnings", []) if len(r) > 4 and r[4].lower() == "active")
    if active > 25:
        problems.append(f"{active} active learnings; condense to 25 or fewer")
    for s in SECTIONS:
        for r in data.get(s, []):
            for c in r:
                if NEVER.search(c):
                    problems.append(f"{s}: '{c}' is a placeholder or an unconfirmed item; memory keeps only what the "
                                    "founder gave and approved")
    if not quiet:
        for x in problems:
            print("PROBLEM:", x)
    return problems


def split(s, n, what):
    parts = [p.strip() for p in s.split("|")]
    if len(parts) != n:
        raise C.Stop(f"{what} needs {n} parts separated by |; got {len(parts)}: '{s}'")
    return parts


def date_for(data, today):
    country = ""
    for r in data["Profile"]:
        if r and r[0].lower() == "country":
            country = r[1]
    return C.human_date(today, {"founder": {"country": country}})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["read", "write", "validate"])
    ap.add_argument("path", nargs="?")
    ap.add_argument("--out")
    ap.add_argument("--existing")
    ap.add_argument("--json-out")
    ap.add_argument("--today")
    ap.add_argument("--profile", action="append", default=[])
    ap.add_argument("--magnet", action="append", default=[])
    ap.add_argument("--learning", action="append", default=[])
    ap.add_argument("--retire", action="append", default=[])
    ap.add_argument("--history", action="append", default=[])
    a = ap.parse_args()
    if a.cmd in ("read", "validate"):
        if not a.path:
            raise C.Stop(f"{a.cmd} needs the memory file path")
        data = parse(a.path)
        probs = validate(data, quiet=(a.cmd == "read"))
        if a.cmd == "validate":
            print(f"{len(probs)} problems")
            return 1 if probs else 0
        j = to_json(data)
        if a.json_out:
            with open(a.json_out, "w", encoding="utf-8") as fh:
                json.dump(j, fh, indent=1, ensure_ascii=False)
        prof = j["profile"]
        print("PROFILE: " + "; ".join(f"{k}: {v['value']}" for k, v in prof.items()))
        for lg in j["learnings"]:
            if lg["status"] in ("active", "watch"):
                print(f"LEARNING {lg['status'].upper()} ({lg['step']}): {lg['rule']}")
        for mg in j["magnets"]:
            print(f"MAGNET BUILT: {mg.get('Date')}: {mg.get('Title')} ({mg.get('Format')}; {mg.get('Tiers or items')})")
        if probs:
            print(f"NOTE: {len(probs)} problem(s) in the file; it was still read. Fix them when you next save.")
        return 0
    if not a.out:
        raise C.Stop("write needs --out <memory.md>")
    today = C.parse_date(a.today, "--today") if a.today else dt.date.today()
    data = parse(a.existing) if a.existing else {s: [] for s in SECTIONS}
    for s in SECTIONS:
        data.setdefault(s, [])
    for p in a.profile:
        if "=" not in p:
            raise C.Stop(f"--profile needs Field=Value | source; got '{p}'")
        field, _, rest = p.partition("=")
        value, _, source = rest.partition("|")
        field, value, source = field.strip(), value.strip(), (source.strip() or "founder said")
        if NEVER.search(value):
            raise C.Stop(f"'{value}' is a placeholder; do not save it")
        row = [field, value, source, today.isoformat()]
        for i, r in enumerate(data["Profile"]):
            if r and r[0].lower() == field.lower():
                if r[1] == value:
                    row = r
                data["Profile"][i] = row
                break
        else:
            data["Profile"].append(row)
    shown = date_for(data, today)
    for m in a.magnet:
        title, fmt, tiers, topic, subs = split(m, 5, "--magnet")
        data["Magnets built"].append([shown, title, fmt, tiers, topic, subs])
    for n in a.retire:
        for r in data["Learnings"]:
            if r and r[0] == str(n) and not r[1].startswith("~~"):
                r[1] = f"~~{r[1]}~~"
                r[4] = "retired"
    for lg in a.learning:
        rule, ev, step, status = split(lg, 4, "--learning")
        if status not in STATUS:
            raise C.Stop(f"learning status must be watch, active or retired; got '{status}'")
        if step not in STEPS:
            raise C.Stop(f"learning step '{step}' must be one of {', '.join(sorted(STEPS))}")
        for r in data["Learnings"]:
            if len(r) > 4 and r[1].strip("~").lower() == rule.lower():
                r[4] = status
                r[2] = f"{r[2]}; {ev}" if ev and ev not in r[2] else r[2]
                break
        else:
            nums = [int(r[0]) for r in data["Learnings"] if r and r[0].isdigit()]
            data["Learnings"].append([str(max(nums, default=0) + 1), rule, ev, step, status, today.isoformat()])
    for h in a.history:
        made, opt, verdict = split(h, 3, "--history")
        data["History"].append([shown, made, opt, verdict])
    probs = validate(data, quiet=True)
    if probs:
        for x in probs:
            print("PROBLEM:", x)
        print("Nothing was written.")
        return 1
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(render(data, today))
    print(f"WROTE: {a.out}")
    return 0


if __name__ == "__main__":
    C.run_main(main)
