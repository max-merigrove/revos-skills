#!/usr/bin/env python3
"""Read, write and check the Client Credit Check memory file.

Usage (paths relative to this skill's folder):
  python3 scripts/memory.py read <memory.md> --json-out <saved.json> [--date YYYY-MM-DD]
        what was saved: the founder's settings (to copy into case.json), the client log, active learnings,
        outcome counts by verdict and any client whose check is past the re-check window
  python3 scripts/memory.py write <results.json> --out <memory.md> [--existing <old memory.md>]
        [--history "what was made | option chosen | founder verdict"] [--learning "rule | evidence | step | status"]
        [--set "Field=value" ...] [--signed yes|no|unknown]
        write the profile (only what the founder gave), add or update this client's row in the log, keep old
        learnings and history and append new rows
  python3 scripts/memory.py outcome <memory.md> --client "<name>" [--signed yes|no] [--outcome "<words>"] [--date YYYY-MM-DD]
        log what happened with a client checked before (signed, paid on time, paid late, unpaid)
  python3 scripts/memory.py counts <memory.md>      the founder's own counts by verdict, no percentages under ten
  python3 scripts/memory.py validate <memory.md>    check the file still has the shape this skill reads

Never stores contract text, bank details, personal data or anything the founder did not give or approve.
Standard library only. No network calls. Exit 2 with a STOP line on any error.
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

SKILL = "revos-client-credit-check"
PROFILE = [  # label, case.json founder key
    ("Business", "business"), ("Your name", "name"), ("Sign-off", "sign_off"), ("Country", "country"),
    ("Your English", "english"), ("Currency", "currency"), ("How you write numbers", "decimal"),
    ("How you write dates", "date_style"), ("Your limit (most unpaid work you can carry)", "limit"),
    ("Your usual deposit", "usual_deposit"), ("Your usual days to pay", "usual_days"),
    ("Your usual billing for ongoing work", "usual_billing"), ("What counts as a large amount", "large"),
    ("Re-check window (days)", "recheck_days"), ("Most you ask up front", "max_deposit"),
    ("Voice for client wording", "voice"), ("How you write", "voice_notes"),
]
LOG_COLS = ["Client", "Country", "Checked", "Verdict", "Rung proposed", "Peak as offered", "Peak recommended",
            "Signals", "Signed", "Outcome", "Outcome date"]
LEARN_HEAD = "| # | Learning | Evidence | Applies to step | Status | Added |"
HIST_HEAD = "| Date | Made | Choice | Verdict |"
SECTIONS = ["## Profile", "## Client log", "## Learnings", "## History"]
VERDICTS = {"GO", "CAUTION", "STOP"}
STATUSES = {"watch", "active", "retired"}


def stop(msg):
    print(f"STOP: {msg}. Nothing was written.")
    sys.exit(2)


def cell(v):
    if v is None:
        return ""
    return str(v).replace("|", "/").replace("\n", " ").strip()


def split_row(line):
    line = line.strip()
    if not line.startswith("|"):
        return None
    return [c.strip() for c in line.strip("|").split("|")]


def tables(text):
    out, cur, head = {}, None, None
    for line in text.splitlines():
        if line.startswith("## "):
            cur, head = line.strip(), None
            out[cur] = []
            continue
        row = split_row(line)
        if cur is None or row is None:
            continue
        if head is None:
            head = row
            out[cur + "#head"] = row
            continue
        if all(re.fullmatch(r":?-{2,}:?", c) for c in row if c):
            continue
        out[cur].append(dict(zip(head, row + [""] * (len(head) - len(row)))))
    return out


def load(path):
    p = Path(path)
    if not p.exists():
        stop(f"there is no memory file at {path}")
    text = p.read_text(encoding="utf-8")
    for s in SECTIONS:
        if s not in text:
            stop(f"the memory file has no '{s}' section; it may have been edited by hand")
    return text, tables(text)


def outcome_kind(words):
    w = str(words or "").lower()
    if not w:
        return ""
    if re.search(r"never paid|unpaid|not paid|didn'?t pay|written off|still owe", w):
        return "unpaid"
    if re.search(r"late|overdue|chas", w):
        return "paid late"
    if re.search(r"on time|in full|paid|early", w):
        return "paid on time"
    if re.search(r"didn'?t sign|not signed|walked|declined|lost", w):
        return "not signed"
    return w


def counts(log):
    by = {}
    for r in log:
        v, o = r.get("Verdict", "").upper(), outcome_kind(r.get("Outcome"))
        if v not in VERDICTS or not o or o == "not signed":
            continue
        by.setdefault(v, {}).setdefault(o, 0)
        by[v][o] += 1
    n = sum(sum(d.values()) for d in by.values())
    lines = []
    for v in ["GO", "CAUTION", "STOP"]:
        if v in by:
            total = sum(by[v].values())
            parts = ", ".join(f"{k} {c}" for k, c in sorted(by[v].items()))
            lines.append(f"{v.title()} clients with an outcome: {total} ({parts})")
    if n == 0:
        lines.append("No outcomes logged yet.")
    elif n < 10:
        lines.append(f"{n} outcome{'s' if n != 1 else ''} so far: too few to read a pattern; these are counts, not rates.")
    return lines, n


def cmd_read(args):
    text, t = load(args.path)
    today = date.fromisoformat(args.date) if args.date else date.today()
    prof = {r.get("Field"): r.get("Value") for r in t.get("## Profile", [])}
    founder = {}
    for label, key in PROFILE:
        v = prof.get(label)
        if v:
            founder[key] = v
    log = t.get("## Client log", [])
    window = int(re.sub(r"\D", "", founder.get("recheck_days", "") or "") or 90)
    stale = []
    for r in log:
        try:
            if (today - date.fromisoformat(r.get("Checked", ""))).days > window:
                stale.append(r.get("Client"))
        except ValueError:
            pass
    learn = [r for r in t.get("## Learnings", []) if r.get("Status", "").lower() == "active"]
    watch = [r for r in t.get("## Learnings", []) if r.get("Status", "").lower() == "watch"]
    lines, n = counts(log)
    out = {"founder": founder, "clients": log, "active_learnings": learn, "watch_learnings": watch,
           "counts": lines, "outcomes": n, "stale": stale}
    json.dump(out, open(args.json_out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"USING: {len(founder)} saved settings, {len(log)} client(s) in the log, {len(learn)} active learning(s)")
    for k, v in founder.items():
        print(f"SAVED: {k} = {v}")
    for r in log:
        print(f"CLIENT: {r.get('Client')} | {r.get('Checked')} | {r.get('Verdict')} | rung {r.get('Rung proposed')} | "
              f"signed {r.get('Signed') or '?'} | outcome {r.get('Outcome') or 'not reported'}")
    for r in learn:
        print(f"APPLY: {r.get('Learning')} (at {r.get('Applies to step')})")
    for s in stale:
        print(f"STALE: {s} was checked over {window} days ago; re-run the lookups before relying on it")
    for line in lines:
        print("COUNTS:", line)
    return 0


def render(founder_rows, log, learnings, history, today):
    out = ["# Client Credit Check memory", "",
           f"Skill: {SKILL} | Memory version: 1 | Updated: {today}", "",
           "Keep this file. Attach it next time (or leave it in your merigrove-memory folder, or your Claude Project) and the "
           "skill picks up where you left off. You can edit it by hand. It holds company names and verdicts only: no contract "
           "text, bank details or personal details.", "", "## Profile", "", "| Field | Value | Source | Updated |",
           "|---|---|---|---|"]
    for label, _ in PROFILE:
        r = founder_rows.get(label)
        if r and r.get("Value"):
            out.append(f"| {label} | {cell(r['Value'])} | {cell(r.get('Source'))} | {cell(r.get('Updated'))} |")
    out += ["", "## Client log", "", "| " + " | ".join(LOG_COLS) + " |", "|" + "---|" * len(LOG_COLS)]
    for r in log:
        out.append("| " + " | ".join(cell(r.get(c)) for c in LOG_COLS) + " |")
    out += ["", "## Learnings", "", LEARN_HEAD, "|---|---|---|---|---|---|"]
    for i, r in enumerate(learnings, 1):
        out.append(f"| {i} | {cell(r.get('Learning'))} | {cell(r.get('Evidence'))} | {cell(r.get('Applies to step'))} | "
                   f"{cell(r.get('Status'))} | {cell(r.get('Added'))} |")
    out += ["", "Status: watch (seen once), active (approved or repeated), retired (kept for the record, no longer applied).",
            "", "## History", "", HIST_HEAD, "|---|---|---|---|"]
    for r in history:
        out.append(f"| {cell(r.get('Date'))} | {cell(r.get('Made'))} | {cell(r.get('Choice'))} | {cell(r.get('Verdict'))} |")
    return "\n".join(out) + "\n"


def cmd_write(args):
    try:
        res = json.load(open(args.results, encoding="utf-8"))
    except (OSError, ValueError):
        stop("the results file could not be read")
    today = res.get("check_date") or date.today().isoformat()
    founder_rows, log, learnings, history = {}, [], [], []
    if args.existing and Path(args.existing).exists():
        _, t = load(args.existing)
        founder_rows = {r.get("Field"): r for r in t.get("## Profile", [])}
        log, learnings, history = t.get("## Client log", []), t.get("## Learnings", []), t.get("## History", [])
    f = res.get("founder") or {}
    for label, key in PROFILE:
        v = f.get(key)
        if key == "limit" and res.get("limit_default"):
            continue
        if v not in (None, "", []):
            old = founder_rows.get(label, {})
            if old.get("Value") != str(v):
                founder_rows[label] = {"Value": v, "Source": "you said", "Updated": today}
    for kv in args.set or []:
        if "=" not in kv:
            stop(f"--set needs Field=value, got '{kv}'")
        k, v = kv.split("=", 1)
        labels = [l for l, _ in PROFILE]
        if k not in labels:
            stop(f"'{k}' is not a profile field; use one of: {', '.join(labels)}")
        founder_rows[k] = {"Value": v, "Source": "you said", "Updated": today}
    client = (res.get("client") or {}).get("name")
    if not client or res.get("verdict") not in VERDICTS:
        stop("the results file has no client or verdict")
    row = {"Client": client, "Country": (res.get("client") or {}).get("country", ""), "Checked": today,
           "Verdict": res["verdict"], "Rung proposed": str(res.get("rung")),
           "Peak as offered": (res.get("their") or {}).get("peak_text", ""),
           "Peak recommended": (res.get("rec") or {}).get("peak_text", ""),
           "Signals": ", ".join(x["id"] for x in res.get("findings", []) if x.get("confidence") != "unverified"),
           "Signed": args.signed or "", "Outcome": "", "Outcome date": ""}
    log = [r for r in log if not (r.get("Client") == client and r.get("Checked") == today)] + [row]
    for spec in args.learning or []:
        parts = [p.strip() for p in spec.split("|")]
        if len(parts) != 4 or parts[3] not in STATUSES:
            stop("--learning needs 'rule | evidence | step | status' with status watch, active or retired")
        learnings.append({"Learning": parts[0], "Evidence": parts[1], "Applies to step": parts[2], "Status": parts[3], "Added": today})
    if sum(1 for r in learnings if r.get("Status") == "active") > 25:
        stop("more than 25 active learnings; retire or merge some first")
    if args.history:
        parts = [p.strip() for p in args.history.split("|")]
        # the date is added here; a date typed as the first part is dropped so it never shows twice
        if parts and re.fullmatch(r"\d{1,4}[./-]\d{1,2}[./-]\d{1,4}|\d{4}-\d{2}-\d{2}", parts[0]):
            parts = parts[1:]
        parts += ["", "", ""]
        history.append({"Date": today, "Made": parts[0] or "brief", "Choice": parts[1], "Verdict": parts[2] or res.get("verdict", "")})
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(render(founder_rows, log, learnings, history, today), encoding="utf-8")
    print(f"SAVED: {args.out} ({len(log)} client(s) in the log)")
    return 0


def cmd_outcome(args):
    text, t = load(args.path)
    log = t.get("## Client log", [])
    hits = [r for r in log if r.get("Client", "").lower().startswith(args.client.lower().strip())]
    if not hits:
        stop(f"no client named '{args.client}' in the log")
    r = sorted(hits, key=lambda x: x.get("Checked", ""))[-1]
    if args.signed:
        r["Signed"] = args.signed
    if args.outcome:
        r["Outcome"] = outcome_kind(args.outcome) + (f" ({args.outcome})" if outcome_kind(args.outcome) != args.outcome.lower() else "")
        r["Outcome date"] = args.date or date.today().isoformat()
    founder_rows = {x.get("Field"): x for x in t.get("## Profile", [])}
    Path(args.path).write_text(render(founder_rows, log, t.get("## Learnings", []), t.get("## History", []),
                                      args.date or date.today().isoformat()), encoding="utf-8")
    print(f"LOGGED: {r['Client']}: signed {r.get('Signed') or '?'}, outcome {r.get('Outcome') or 'not reported'}")
    return 0


def cmd_counts(args):
    _, t = load(args.path)
    lines, _ = counts(t.get("## Client log", []))
    for line in lines:
        print("COUNTS:", line)
    return 0


def cmd_validate(args):
    text, t = load(args.path)
    problems = []
    if t.get("## Client log#head") and t["## Client log#head"] != LOG_COLS:
        problems.append("the client log columns have changed")
    for r in t.get("## Client log", []):
        if r.get("Verdict", "").upper() not in VERDICTS:
            problems.append(f"client '{r.get('Client')}' has verdict '{r.get('Verdict')}'")
        if re.search(r"\b(IBAN|sort code|account number|routing)\b", " ".join(r.values()), re.I):
            problems.append("bank details found in the client log; remove them")
    act = 0
    for r in t.get("## Learnings", []):
        st = r.get("Status", "").lower().strip("~ ")
        if st not in STATUSES:
            problems.append(f"learning '{r.get('Learning')}' has status '{r.get('Status')}'")
        act += st == "active"
    if act > 25:
        problems.append(f"{act} active learnings; the cap is 25")
    for p in problems:
        print("PROBLEM:", p)
    print(f"{len(problems)} problems")
    return 1 if problems else 0


def main(argv):
    a = argparse.ArgumentParser()
    sub = a.add_subparsers(dest="cmd")
    r = sub.add_parser("read")
    r.add_argument("path")
    r.add_argument("--json-out", required=True)
    r.add_argument("--date")
    w = sub.add_parser("write")
    w.add_argument("results")
    w.add_argument("--out", required=True)
    w.add_argument("--existing")
    w.add_argument("--history")
    w.add_argument("--learning", action="append")
    w.add_argument("--set", action="append")
    w.add_argument("--signed")
    o = sub.add_parser("outcome")
    o.add_argument("path")
    o.add_argument("--client", required=True)
    o.add_argument("--signed")
    o.add_argument("--outcome")
    o.add_argument("--date")
    c = sub.add_parser("counts")
    c.add_argument("path")
    v = sub.add_parser("validate")
    v.add_argument("path")
    if not argv:
        print(__doc__)
        return 0
    try:
        args = a.parse_args(argv)
    except SystemExit:
        print("STOP: the command was not understood; run with no arguments for usage.")
        return 2
    return {"read": cmd_read, "write": cmd_write, "outcome": cmd_outcome, "counts": cmd_counts,
            "validate": cmd_validate}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
