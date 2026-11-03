#!/usr/bin/env python3
"""The skill's memory file: write it after approval, read it back on a return run, check its shape.

Usage:
  python3 scripts/memory_tool.py write --settings settings.json --facts facts.json --panel panel-checked.json
        --out revos-get-quoted-by-ai-memory.md [--results results.json] [--pages pages.json]
        [--existing old-memory.md] [--history "what was made | verdict"] [--learning "rule | evidence | step | status"]
  python3 scripts/memory_tool.py read <memory.md> --out-dir <scratch>
      Writes settings.json, facts.json, panel-checked.json, baseline.json, previous.json, pages.json and
      learnings.json back out, and prints one line on what was remembered.
  python3 scripts/memory_tool.py validate <memory.md>

The memory holds the business profile, the fact register, the panel, every scored result with its date
and n, the pages published with dates, learnings and history. It never holds run-by-run answers, and
never anything the founder did not give or approve. Exit 0 fine, 1 with PROBLEM lines, 2 with STOP.
"""
import argparse
import json
import os
import re
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ensure_parent, load_json, read_text, save_json, stop  # noqa: E402

SKILL = "revos-get-quoted-by-ai"
SECTIONS = ["Profile", "Fact register", "Panel", "Results", "Pages published", "Learnings", "History"]
PROFILE_KEYS = ["business", "aliases", "domain", "sells", "buyers", "where", "country", "language", "english", "decimal",
                "currency", "date_order", "paper", "engines", "runs", "quick", "cadence_weeks", "platform", "editor",
                "robots_owner", "reach_finding", "competitors", "locations", "offer_words", "local"]
STATUSES = {"watch", "active", "retired"}


def esc(v):
    return str(v if v is not None else "").replace("|", "\\|").replace("\n", " ").strip()


def table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    for r in rows:
        out.append("| " + " | ".join(esc(c) for c in r) + " |")
    return "\n".join(out)


def parse_tables(text):
    """{section: [row dicts]} for every '## Section' with a markdown table under it."""
    out = {}
    cur = None
    headers = None
    for line in text.splitlines():
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m:
            cur, headers = m.group(1).strip(), None
            out.setdefault(cur, [])
            continue
        if cur is None or not line.strip().startswith("|"):
            continue
        cells = [c.replace("\\|", "|").strip() for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]
        if all(re.fullmatch(r":?-{3,}:?", c) for c in cells if c):
            continue
        if headers is None:
            headers = cells
            continue
        out[cur].append(dict(zip(headers, cells)))
    return out


def write(a):
    settings = load_json(a.settings, "the settings file")
    facts = load_json(a.facts, "the fact register")
    panel = load_json(a.panel, "the checked panel")
    results = load_json(a.results, "the results file") if a.results else None
    pages = load_json(a.pages, "the pages file") if a.pages else []
    old = parse_tables(read_text(a.existing, "the old memory")) if a.existing else {}
    today = settings.get("today") or date.today().isoformat()
    prof = []
    for k in PROFILE_KEYS:
        if k in settings and settings[k] not in (None, "", []):
            v = settings[k]
            prof.append([k, json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict, bool)) else v, "founder said or pasted", today])
    fr = [[f.get("kind", ""), f.get("label", ""), f.get("value", ""), f.get("status", ""), f.get("source", ""),
           f.get("confirmed_on", ""), f.get("need", "")] for f in facts.get("facts", [])]
    pr = []
    for q in panel.get("questions", []):
        pr.append([q.get("id", "cut"), q.get("text", ""), q.get("family", ""), q.get("tag", "") + (" (reworded)" if q.get("reworded") else ""),
                   q.get("source", ""),
                   q.get("quote", ""), q.get("page", ""), "cut: " + q.get("cut_reason", "") if q.get("cut") else
                   (q.get("priority", "") + (", quick" if q.get("quick") else ""))])
    for b in panel.get("branded", []):
        pr.append([b.get("id", ""), b.get("text", ""), "branded", "accuracy", "", "", "", "once each"])
    res_rows = [[r.get("Date", ""), r.get("Engines", ""), r.get("Runs (n)", ""), r.get("Named", ""), r.get("Cited", ""),
                 r.get("Range", ""), r.get("Kind", ""), r.get("Note", "")] for r in old.get("Results", [])]
    if results and results.get("headline", {}).get("n"):
        h = results["headline"]
        lo, hi = h["range"]
        kind = "baseline" if not res_rows else "retest"
        res_rows.append([settings.get("results_date") or today, ", ".join(results.get("per_engine", {}).keys()), h["n"], h["named"],
                         h["cited"], f"{round(lo * 100)}% to {round(hi * 100)}%", kind,
                         results.get("movement", "") if kind == "retest" else "before any page went live"])
    pg = [[r.get("Page", ""), r.get("Question owned", ""), r.get("Went live", ""), r.get("Address", "")] for r in old.get("Pages published", [])]
    known = {p[0] for p in pg}
    for p in pages:
        if p.get("slug") in known:
            for row in pg:
                if row[0] == p.get("slug") and p.get("went_live"):
                    row[2] = p["went_live"]
            continue
        pg.append([p.get("slug", ""), p.get("question", ""), p.get("went_live", "not yet"), p.get("address", "")])
    learn = [[r.get("#", ""), r.get("Learning", ""), r.get("Evidence", ""), r.get("Applies to step", ""), r.get("Status", ""),
              r.get("Added", "")] for r in old.get("Learnings", [])]
    for raw in a.learning or []:
        parts = [x.strip() for x in raw.split("|")]
        if len(parts) != 4 or parts[3] not in STATUSES:
            stop("a learning is 'rule | evidence | step | status', status watch, active or retired.")
        learn.append([str(len(learn) + 1), parts[0], parts[1], parts[2], parts[3], today])
    hist = [[r.get("Date", ""), r.get("Made", ""), r.get("Verdict", "")] for r in old.get("History", [])]
    if a.history:
        made, _, verdict = a.history.partition("|")
        hist.append([today, made.strip(), verdict.strip()])
    text = "\n\n".join([
        "# Get Quoted by AI memory",
        f"Skill: {SKILL} | Memory version: 1 | Updated: {today}",
        "Keep this file. Attach it next time (or leave it in your merigrove-memory folder, or your Claude Project) and the "
        "skill picks up where you left off: your facts, your questions and your baseline. You can edit it by hand.",
        "## Profile\n\n" + table(["Field", "Value", "Source", "Updated"], prof),
        "## Fact register\n\n" + table(["Kind", "Label", "Value", "Status", "Source", "Confirmed", "Need"], fr),
        "## Panel\n\n" + table(["#", "Question", "Family", "Tag", "Source", "Quote", "Page", "Run"], pr),
        "## Results\n\n" + table(["Date", "Engines", "Runs (n)", "Named", "Cited", "Range", "Kind", "Note"], res_rows),
        "## Pages published\n\n" + table(["Page", "Question owned", "Went live", "Address"], pg),
        "## Learnings\n\n" + table(["#", "Learning", "Evidence", "Applies to step", "Status", "Added"], learn)
        + "\n\nStatus: watch (seen once), active (approved or repeated), retired (kept for the record, no longer applied).",
        "## History\n\n" + table(["Date", "Made", "Verdict"], hist),
    ]) + "\n"
    with open(ensure_parent(a.out), "w", encoding="utf-8") as fh:
        fh.write(text)
    probs = validate_text(text)
    for p in probs:
        print("PROBLEM:", p)
    print(f"WROTE {a.out}: {len(fr)} facts, {len(pr)} questions, {len(res_rows)} result row(s), {len(pg)} page(s), "
          f"{sum(1 for x in learn if x[4] == 'active')} active learning(s)")
    return 1 if probs else 0


def validate_text(text):
    probs = []
    if not text.startswith("# Get Quoted by AI memory"):
        probs.append("the first line must be '# Get Quoted by AI memory'")
    if f"Skill: {SKILL}" not in text:
        probs.append("the skill line is missing")
    t = parse_tables(text)
    for s in SECTIONS:
        if s not in t:
            probs.append(f"section '## {s}' is missing")
    for r in t.get("Fact register", []):
        if r.get("Status") not in ("confirmed", "NEED", "declined"):
            probs.append(f"fact '{r.get('Label')}' has status '{r.get('Status')}'")
    active = 0
    for r in t.get("Learnings", []):
        if r.get("Status") not in STATUSES:
            probs.append(f"learning {r.get('#')} has status '{r.get('Status')}'")
        active += r.get("Status") == "active"
    if active > 25:
        probs.append(f"{active} active learnings; condense to 25 or fewer")
    for r in t.get("Results", []):
        try:
            n = int(r.get("Runs (n)", "0"))
            x = int(r.get("Named", "0"))
            if x > n:
                probs.append(f"result {r.get('Date')}: named {x} is more than n {n}")
        except ValueError:
            probs.append(f"result {r.get('Date')}: runs and named must be whole numbers")
    if re.search(r"(?i)what it said|run 1 \||sources listed", text):
        probs.append("the memory holds run-by-run answers; keep only the scored totals")
    return probs


def read(a):
    text = read_text(a.memory, "the memory file")
    probs = validate_text(text)
    if probs:
        for p in probs:
            print("PROBLEM:", p)
        stop("the memory file is damaged. Ask the founder for the last good copy, or run as a first visit.")
    t = parse_tables(text)
    os.makedirs(a.out_dir, exist_ok=True)
    settings = {}
    for r in t["Profile"]:
        v = r.get("Value", "")
        try:
            v = json.loads(v) if v[:1] in "[{" or v in ("true", "false") else v
        except json.JSONDecodeError:
            pass
        if r.get("Field") in ("runs", "cadence_weeks"):
            try:
                v = int(v)
            except ValueError:
                pass
        settings[r.get("Field")] = v
    facts = {"business": settings.get("business", ""), "decimal": settings.get("decimal"), "facts": []}
    for r in t["Fact register"]:
        f = {"kind": r.get("Kind"), "label": r.get("Label"), "value": r.get("Value"), "status": r.get("Status"),
             "source": r.get("Source")}
        if r.get("Confirmed"):
            f["confirmed_on"] = r["Confirmed"]
        if r.get("Need"):
            f["need"] = r["Need"]
        facts["facts"].append(f)
    panel = {"business": settings.get("business", ""), "aliases": settings.get("aliases") or [],
             "locations": settings.get("locations") or [], "offer_words": settings.get("offer_words") or [],
             "questions": [], "branded": []}
    for r in t["Panel"]:
        if r.get("Family") == "branded":
            panel["branded"].append({"id": r.get("#"), "text": r.get("Question")})
            continue
        tag = (r.get("Tag") or "").strip()
        q = {"id": r.get("#"), "text": r.get("Question"), "family": r.get("Family"), "tag": tag.split(" ")[0],
             "source": r.get("Source"), "quote": r.get("Quote"), "page": r.get("Page")}
        if "reworded" in tag:
            q["reworded"] = True
        run = r.get("Run", "")
        if run.endswith(", quick"):
            run, q["quick"] = run[:-7], True
        if run.startswith("cut"):
            q["cut"], q["cut_reason"] = True, run[4:].strip(": ")
            q.pop("id", None)
        else:
            q["priority"] = run or "spare"
        panel["questions"].append(q)
    kept = [q for q in panel["questions"] if not q.get("cut")]
    if not any(q.get("quick") for q in kept):
        for i, q in enumerate([q for q in kept if q["priority"] == "run first"]):
            q["quick"] = i < 5
    res = t["Results"]
    def row(r):
        return {"date": r.get("Date"), "n": int(r.get("Runs (n)") or 0), "named": int(r.get("Named") or 0),
                "cited": int(r.get("Cited") or 0) if (r.get("Cited") or "").isdigit() else 0,
                "engines": [e.strip() for e in r.get("Engines", "").split(",") if e.strip()],
                "questions": [q["id"] for q in kept if q.get("priority") == "run first"]}
    base = next((row(r) for r in res if r.get("Kind") == "baseline"), row(res[0]) if res else None)
    prev = row(res[-1]) if res else None
    pages = [{"slug": r.get("Page"), "question": r.get("Question owned"), "went_live": r.get("Went live"),
              "address": r.get("Address")} for r in t["Pages published"]]
    learnings = [r for r in t["Learnings"] if r.get("Status") == "active"]
    save_json(os.path.join(a.out_dir, "settings.json"), settings)
    save_json(os.path.join(a.out_dir, "facts.json"), facts)
    save_json(os.path.join(a.out_dir, "panel-checked.json"), panel)
    save_json(os.path.join(a.out_dir, "pages.json"), pages)
    save_json(os.path.join(a.out_dir, "learnings.json"), learnings)
    if base:
        save_json(os.path.join(a.out_dir, "baseline.json"), base)
    if prev:
        save_json(os.path.join(a.out_dir, "previous.json"), prev)
    eng = settings.get("engines") or []
    print(f"REMEMBERED: {settings.get('business', '?')}; {len(facts['facts'])} facts; {len(kept)} questions; "
          f"engines {', '.join(eng) if isinstance(eng, list) else eng}; "
          + (f"baseline named in {base['named']} of {base['n']} runs, n equals {base['n']} ({base['date']}); " if base else "no baseline yet; ")
          + f"{len(pages)} page(s) on record; {len(learnings)} active learning(s)")
    for l in learnings:
        print(f"LEARNING ({l.get('Applies to step')}): {l.get('Learning')}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["write", "read", "validate"])
    ap.add_argument("memory", nargs="?")
    ap.add_argument("--settings")
    ap.add_argument("--facts")
    ap.add_argument("--panel")
    ap.add_argument("--results")
    ap.add_argument("--pages")
    ap.add_argument("--existing")
    ap.add_argument("--history")
    ap.add_argument("--learning", action="append")
    ap.add_argument("--out")
    ap.add_argument("--out-dir")
    a = ap.parse_args()
    if a.mode == "write":
        for k in ("settings", "facts", "panel", "out"):
            if not getattr(a, k):
                stop(f"--{k} is needed to write the memory.")
        return write(a)
    if not a.memory:
        stop("name the memory file.")
    if a.mode == "read":
        if not a.out_dir:
            stop("--out-dir is needed: where to put the settings, facts and panel read back.")
        return read(a)
    probs = validate_text(read_text(a.memory, "the memory file"))
    for p in probs:
        print("PROBLEM:", p)
    print(f"{len(probs)} problems")
    return 1 if probs else 0


if __name__ == "__main__":
    sys.exit(main())
