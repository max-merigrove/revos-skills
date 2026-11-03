#!/usr/bin/env python3
"""Read, write and validate the Buyer Language Miner memory file.

Usage:
  memory_tool.py read <memory.md> [--json-out previous.json]
  memory_tool.py write --run <run folder> --bank <bank.json> --out <memory.md> [--existing <old memory.md>]
                       [--profile "Field=value"]... [--learning "rule | evidence | step | status"]...
                       [--retire <learning number>]... [--history "what was made | option chosen | verdict"]
  memory_tool.py validate <memory.md>

Sections: Profile, Bank (every phrase with its ID, so a return run keeps the IDs and can say what changed),
Clusters, Source yield, Learnings, History. Voices are stored only as one-way codes (h + 10 characters), never as
names or handles; phrases are the buyers' public words, already scrubbed. Writing keeps every earlier learning
(retired ones stay, struck through) and never writes anything the founder did not give or approve: call it only
after the founder says yes. Every error prints one "STOP: <what to do>" line and exits 2. Standard library only.
"""
import argparse
import json
import os
import re
import signal
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ledger import stop, load_json, load_ledger, EMAIL, PROFILE_URL, MENTION  # noqa: E402
from rank import compute  # noqa: E402

SECTIONS = ["Profile", "Bank", "Clusters", "Source yield", "Learnings", "History"]
STEPS = {"Start", "Memory", "Intake", "Collect", "Ingest", "Diagnose", "Tag", "Cluster", "Angles", "Make", "Check", "Deliver", "Learn", "Sheet"}
STATUS = {"watch", "active", "retired"}
MAX_ACTIVE, MAX_BANK = 25, 300
HEADERS = {
    "Profile": "| Field | Value | Source | Updated |",
    "Bank": "| ID | Phrase | Tag | Cluster | Voice | Source type | Origin | Date | Intensity | Stake |",
    "Clusters": "| ID | Name | Voices | Score | Rank | Run |",
    "Source yield": "| Run | Source | Type | Origin | Items | Voices |",
    "Learnings": "| # | Learning | Evidence | Applies to step | Status | Added |",
    "History": "| Date | Made | Option chosen | Verdict |",
}


def cell(s):
    return str(s if s is not None else "").replace("|", "/").replace("\n", " ").strip()


def parse(path):
    if not os.path.exists(path):
        stop(f"cannot find the memory file {path}")
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    data = {s: [] for s in SECTIONS}
    sec = None
    for line in text.splitlines():
        if line.startswith("## "):
            sec = line[3:].strip()
            data.setdefault(sec, [])
            continue
        if sec and line.startswith("|") and not re.match(r"^\|[\s:|-]+\|$", line.strip()):
            data[sec].append([c.strip() for c in line.strip().strip("|").split("|")])
    for s in SECTIONS:
        if data[s] and data[s][0] and data[s][0][0].lower() in ("field", "id", "#", "date", "run"):
            data[s] = data[s][1:]
    if not any(data[s] for s in SECTIONS):
        stop(f"{path} has no memory tables; is it the Buyer Language Miner memory file?")
    return data


def to_json(d):
    prof = {r[0]: r[1] for r in d["Profile"] if len(r) >= 2}
    bank = []
    for r in d["Bank"]:
        if len(r) < 9:
            continue
        try:
            inten = int(r[8])
        except ValueError:
            inten = 2
        bank.append({"id": r[0], "phrase": r[1][1:-1] if len(r[1]) > 1 and r[1][0] == '"' and r[1][-1] == '"' else r[1], "tag": r[2], "cluster": r[3], "voice": r[4], "source_type": r[5], "origin": r[6],
                     "date": r[7] if r[7] not in ("", "undated") else None, "intensity": inten, "stake": r[9] if len(r) > 9 else ""})
    runs = sorted({r[5] for r in d["Clusters"] if len(r) >= 6})
    last = runs[-1] if runs else None
    clusters = [{"id": r[0], "name": r[1], "voices": int(r[2]) if r[2].isdigit() else 0, "score": r[3], "rank": r[4], "run": r[5]}
                for r in d["Clusters"] if len(r) >= 6 and r[5] == last]
    learn = []
    for r in d["Learnings"]:
        if len(r) >= 5:
            st = r[4].strip("~").strip().lower()
            learn.append({"n": r[0], "learning": r[1].strip("~"), "evidence": r[2], "step": r[3], "status": st, "added": r[5] if len(r) > 5 else ""})
    hist = [{"date": r[0], "made": r[1], "option": r[2] if len(r) > 2 else "", "verdict": r[3] if len(r) > 3 else ""} for r in d["History"] if len(r) >= 2]
    return {"profile": prof, "bank": bank, "clusters": clusters, "last_run": last, "learnings": learn, "history": hist,
            "yield": [{"run": r[0], "source": r[1], "type": r[2], "origin": r[3], "items": r[4], "voices": r[5]} for r in d["Source yield"] if len(r) >= 6]}


def problems_of(d, j):
    probs = []
    text = "\n".join("|".join(r) for s in SECTIONS for r in d[s])
    if EMAIL.search(text):
        probs.append("contains an email address")
    if PROFILE_URL.search(text):
        probs.append("contains a profile link")
    if MENTION.search(text):
        probs.append(f"contains a handle ({MENTION.search(text).group(0)})")
    for b in j["bank"]:
        if not re.fullmatch(r"h[0-9a-f]{10}", b["voice"]):
            probs.append(f"Bank {b['id']}: voice '{b['voice']}' is not a one-way code; never store names or handles")
        if not re.fullmatch(r"Q-\d{3,4}", b["id"]):
            probs.append(f"Bank row '{b['id']}': IDs look like Q-001")
        if b["date"]:
            try:
                date.fromisoformat(b["date"])
            except ValueError:
                probs.append(f"Bank {b['id']}: date '{b['date']}' is not YYYY-MM-DD")
    act = 0
    for l in j["learnings"]:
        if l["status"] not in STATUS:
            probs.append(f"learning {l['n']}: status '{l['status']}' must be watch, active or retired")
        if l["step"] not in STEPS:
            probs.append(f"learning {l['n']}: step '{l['step']}' must be one of {', '.join(sorted(STEPS))}")
        act += l["status"] == "active"
        if re.search(r"stop flagging|don'?t flag|skip (the )?check|invent|make up|no need to verify", l["learning"], re.I):
            probs.append(f"learning {l['n']}: lowers honesty; this skill never learns that")
    if act > MAX_ACTIVE:
        probs.append(f"{act} active learnings; condense to {MAX_ACTIVE} or fewer")
    return probs


def cmd_read(a):
    d = parse(a.memory)
    j = to_json(d)
    probs = problems_of(d, j)
    for p in probs:
        print("PROBLEM:", p)
    if probs:
        stop("the memory file has problems (listed above); fix them by hand or start without it")
    p = j["profile"]
    print(f"MEMORY: {p.get('Business', 'unknown business')}; last run {j['last_run'] or 'none'}; {len(j['bank'])} phrases; "
          f"{len(j['clusters'])} clusters; window {p.get('Window', '90 days')}")
    for l in j["learnings"]:
        if l["status"] == "active":
            print(f"APPLY at {l['step']}: {l['learning']} (learning {l['n']})")
        elif l["status"] == "watch":
            print(f"WATCH (do not apply): {l['learning']}")
    if a.json_out:
        with open(a.json_out, "w", encoding="utf-8") as f:
            json.dump(j, f, ensure_ascii=False, indent=1)
        print(f"WROTE {a.json_out}")


def cmd_validate(a):
    d = parse(a.memory)
    j = to_json(d)
    probs = problems_of(d, j)
    for p in probs:
        print("PROBLEM:", p)
    print(f"{len(probs)} problems; {len(j['bank'])} phrases, {len(j['learnings'])} learnings, {len(j['history'])} runs")
    sys.exit(1 if probs else 0)


def cmd_write(a):
    L = load_ledger(a.run)
    B = load_json(a.bank, "bank")
    R = compute(L, B)
    if R["problems"]:
        stop("the bank still has problems; run check_bank.py and fix them before saving memory")
    old = to_json(parse(a.existing)) if a.existing else {"profile": {}, "learnings": [], "history": [], "yield": [], "bank": [], "clusters": []}
    today = L["today"]
    prof = dict(old["profile"])
    src = {}
    auto = {"Business": L["business"], "Country": L["country"] or "", "Date order": L["date_order"], "Window": f"{L['window_days']} days",
            "Fresh band": f"{L['fresh_days']} days", "Competitors": ", ".join(L.get("competitors", [])), "Language": B.get("lang", "en"),
            "English": B.get("english", ""), "Offer": B.get("offer", ""), "Buyer": B.get("buyer", ""), "Uses first": B.get("uses_first", "")}
    for k, v in auto.items():
        if v:
            prof[k] = v
            src[k] = "this run"
    for kv in a.profile or []:
        if "=" not in kv:
            stop(f"--profile '{kv}' should be Field=value")
        k, v = kv.split("=", 1)
        prof[k.strip()] = v.strip()
        src[k.strip()] = "founder said"
    vh = {vid: v["hash"] for vid, v in L["voices"].items()}
    cl_of = {q: c["id"] for c in R["clusters"] for q in c["all_phrases"]}
    bank_rows = []
    for pid in sorted(R["phrases"]):
        p = R["phrases"][pid]
        it = p.get("_item")
        if not it:
            continue
        bank_rows.append([pid, '"' + cell(p["text"]) + '"', p["tag"], cl_of.get(pid, ""), vh.get(it["voice"], ""), it["source_type"], it["origin"],
                          it["date"] or "undated", str(p["intensity"]), cell(p.get("stake", ""))])
    if len(bank_rows) > MAX_BANK:
        bank_rows.sort(key=lambda r: r[7] if r[7] != "undated" else "0000")
        bank_rows = bank_rows[-MAX_BANK:]
        bank_rows.sort(key=lambda r: r[0])
    bcl = {c["id"]: c for c in B.get("clusters", [])}
    cl_rows = [[c["id"], cell(bcl.get(c["id"], c).get("name", c["id"])), str(c["voices"]), str(c["score"]), str(c["rank"] or c["tier"]), today]
               for c in R["clusters"]]
    new_y = []
    for s in L["sources"]:
        if s["type"] == "previous":
            continue
        its = [i for i in L["items"] if i["source"] == s["id"]]
        new_y.append([today, cell(s["label"])[:80], s["type"], s["origin"], str(len(its)), str(len({i["voice"] for i in its}))])
    keys = {(r[0], r[1], r[2]) for r in new_y}  # saving twice in one run replaces this run's rows instead of repeating them
    y_rows = [[r["run"], r["source"], r["type"], r["origin"], r["items"], r["voices"]] for r in old["yield"] if (r["run"], r["source"], r["type"]) not in keys] + new_y
    learn = old["learnings"]
    for n in a.retire or []:
        for l in learn:
            if l["n"] == str(n):
                l["status"] = "retired"
    for spec in a.learning or []:
        parts = [x.strip() for x in spec.split("|")]
        if len(parts) != 4:
            stop("--learning needs 'rule | evidence | step | status'")
        rule, ev, step, st = parts
        if step not in STEPS:
            stop(f"step must be one of {', '.join(sorted(STEPS))}")
        if st not in STATUS:
            stop("status must be watch, active or retired")
        if re.search(r"stop flagging|don'?t flag|skip (the )?check|invent|make up|no need to verify", rule, re.I):
            stop("that learning would lower honesty; this skill does not save it")
        same = next((l for l in learn if l["learning"].strip().lower() == rule.lower() and l["status"] != "retired"), None)
        if same:  # a repeat of a saved learning: it becomes active, never a second row
            same["status"] = "retired" if st == "retired" else "active"
            continue
        learn.append({"n": str(len(learn) + 1), "learning": rule, "evidence": ev, "step": step, "status": st, "added": today})
    if sum(1 for l in learn if l["status"] == "active") > MAX_ACTIVE:
        stop(f"more than {MAX_ACTIVE} active learnings; retire or merge some first (--retire N)")
    hist = old["history"]
    if a.history:
        parts = [x.strip() for x in a.history.split("|")] + ["", ""]
        row = {"date": today, "made": parts[0], "option": parts[1], "verdict": parts[2]}
        hist = [h for h in hist if not (h["date"] == today and h["made"] == row["made"])] + [row]  # one line per run, the latest verdict
    out = [f"# Buyer Language Miner memory", "",
           f"Skill: revos-buyer-language-miner | Memory version: 1 | Updated: {today}", "",
           "Keep this file. Attach it next time (or leave it in your merigrove-memory folder, or your Claude Project) and the next run "
           "keeps every phrase ID, tells you what changed and asks one question at most. You can edit it by hand. Voices are stored as "
           "one-way codes, never names.", "", "## Profile", "", HEADERS["Profile"], "|---|---|---|---|"]
    for k, v in prof.items():
        out.append(f"| {cell(k)} | {cell(v)} | {src.get(k, 'earlier run')} | {today if k in src else ''} |")
    out += ["", "## Bank", "", HEADERS["Bank"], "|---|---|---|---|---|---|---|---|---|---|"]
    out += ["| " + " | ".join(r) + " |" for r in bank_rows]
    out += ["", "## Clusters", "", HEADERS["Clusters"], "|---|---|---|---|---|---|"]
    out += ["| " + " | ".join(r) + " |" for r in cl_rows]
    out += ["", "## Source yield", "", HEADERS["Source yield"], "|---|---|---|---|---|---|"]
    out += ["| " + " | ".join(cell(x) for x in r) + " |" for r in y_rows]
    out += ["", "## Learnings", "", HEADERS["Learnings"], "|---|---|---|---|---|---|"]
    for l in learn:
        rule = f"~~{cell(l['learning'])}~~" if l["status"] == "retired" else cell(l["learning"])
        out.append(f"| {l['n']} | {rule} | {cell(l['evidence'])} | {l['step']} | {l['status']} | {l['added']} |")
    out += ["", "Status: watch (seen once, not applied yet), active (approved or repeated; applied at its step), retired (kept for the record).",
            "", "## History", "", HEADERS["History"], "|---|---|---|---|"]
    out += [f"| {h['date']} | {cell(h['made'])} | {cell(h['option'])} | {cell(h['verdict'])} |" for h in hist]
    text = "\n".join(out) + "\n"
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    tmp = a.out + ".part"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    d = parse(tmp)
    probs = problems_of(d, to_json(d))
    if probs:
        os.remove(tmp)
        for p in probs:
            print("PROBLEM:", p)
        stop("the memory file would hold something it must not; nothing was saved")
    os.replace(tmp, a.out)
    print(f"WROTE {a.out}: {len(bank_rows)} phrases, {len(cl_rows)} clusters, {sum(1 for l in learn if l['status'] == 'active')} active learnings, {len(hist)} runs")


def main():
    if hasattr(signal, "SIGPIPE"):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("read")
    p.add_argument("memory")
    p.add_argument("--json-out")
    p = sub.add_parser("validate")
    p.add_argument("memory")
    p = sub.add_parser("write")
    p.add_argument("--run", required=True)
    p.add_argument("--bank", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--existing")
    p.add_argument("--profile", action="append")
    p.add_argument("--learning", action="append")
    p.add_argument("--retire", action="append")
    p.add_argument("--history")
    try:
        a = ap.parse_args()
    except SystemExit as e:
        if e.code not in (0, None):
            stop("the command was not understood; see the usage at the top of scripts/memory_tool.py")
        raise
    if not a.cmd:
        stop("give a command: read, write or validate")
    try:
        {"read": cmd_read, "validate": cmd_validate, "write": cmd_write}[a.cmd](a)
    except (OSError, KeyError, ValueError, TypeError) as e:
        stop(f"could not finish ({type(e).__name__}: {e}); check the paths and the files, then run again")


if __name__ == "__main__":
    main()
