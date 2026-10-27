#!/usr/bin/env python3
"""Read, check and update revos-thumbnail-builder-memory.md. Standard library only.

Usage
  python3 scripts/memory_tool.py check FILE
      the three sections are present, the tables have their columns, statuses are valid,
      no more than 25 active learnings
  python3 scripts/memory_tool.py add-run FILE --date 2026-10-20 --video "Title" --direction panel \
      --hook "Month end in ONE day" --verdict "spot on"
      append one History row (CTR left blank until the founder reports it)
  python3 scripts/memory_tool.py add-ctr FILE --video "Title" --ctr 6.1 [--impressions 4200] [--date 2026-10-27]
      record a click-through rate the founder reports against the matching History row
  python3 scripts/memory_tool.py summary FILE
      click-through by style and by number of words, with the number of videos behind
      each figure; under five videos a pattern is a hint, not a finding

The founder edits this file by hand too, so every reader is forgiving about spacing.
"""
import argparse
import datetime as dt
import re
import statistics
import sys
import unicodedata

HISTORY_COLS = ["Date", "Video", "Direction", "Hook", "Words", "Verdict", "CTR %", "Impressions", "CTR noted"]
LEARN_COLS = ["#", "Learning", "Evidence", "Applies to step", "Status", "Added"]
STATUSES = {"watch", "active", "retired"}


def hook_units(text):
    """Words a hook reads as, in any language (the same house rule as thumbnail.py)."""
    n = 0
    for tok in text.split():
        if not re.search(r"\w", tok):
            continue
        cjk = sum(1 for ch in tok if 0x3040 <= ord(ch) <= 0x30FF or 0x3400 <= ord(ch) <= 0x9FFF)
        sea = sum(1 for ch in tok if (0x0E00 <= ord(ch) <= 0x0EFF or 0x1000 <= ord(ch) <= 0x109F
                                      or 0x1780 <= ord(ch) <= 0x17FF) and not unicodedata.category(ch).startswith("M"))
        n += max(1, -(-cjk // 2) + -(-sea // 3)) if (cjk or sea) else 1
    return n


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def section(text, name):
    m = re.search(r"^## " + re.escape(name) + r"\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    return m.group(1) if m else None


def table(block):
    rows = [l.strip() for l in (block or "").splitlines() if l.strip().startswith("|")]
    if len(rows) < 2:
        return [], []
    head = [c.strip() for c in rows[0].strip("|").split("|")]
    body = []
    for r in rows[2:]:
        cells = [c.strip() for c in r.strip("|").split("|")]
        body.append(dict(zip(head, cells + [""] * (len(head) - len(cells)))))
    return head, body


def cmd_check(a):
    text = read(a.file)
    problems = []
    for s in ("Profile", "Winning style", "Learnings", "History"):
        if section(text, s) is None:
            problems.append(f"missing section '## {s}'")
    head, rows = table(section(text, "Learnings"))
    if head and head != LEARN_COLS:
        problems.append(f"Learnings columns are {head}, expected {LEARN_COLS}")
    active = 0
    for r in rows:
        st = re.sub(r"[~*]", "", r.get("Status", "")).strip().lower()
        if st and st not in STATUSES:
            problems.append(f"learning {r.get('#')}: status '{st}' is not watch, active or retired")
        active += st == "active"
    if active > 25:
        problems.append(f"{active} active learnings; condense to 25 or fewer")
    head, rows = table(section(text, "History"))
    if head and head != HISTORY_COLS:
        problems.append(f"History columns are {head}, expected {HISTORY_COLS}")
    for r in rows:
        c = r.get("CTR %", "")
        if c and not re.fullmatch(r"\d+(\.\d+)?", c):
            problems.append(f"History '{r.get('Video')}': CTR '{c}' is not a number")
    for p in problems:
        print("PROBLEM", p)
    print(f"{len(problems)} problem(s); {active} active learning(s); {len(rows)} run(s) in history")
    return 1 if problems else 0


def write_rows(text, rows):
    block = section(text, "History") or ""
    lines = ["| " + " | ".join(HISTORY_COLS) + " |", "|" + "---|" * len(HISTORY_COLS)]
    for r in rows:
        lines.append("| " + " | ".join(r.get(c, "") for c in HISTORY_COLS) + " |")
    new_block = "\n\n" + "\n".join(lines) + "\n\n"
    if block:
        return text.replace(block, new_block, 1)
    return text.rstrip() + "\n\n## History" + new_block


def cmd_add_run(a):
    text = read(a.file)
    _, rows = table(section(text, "History"))
    rows = [r for r in rows if any(v and not v.startswith("YYYY") for v in r.values())]
    rows.append({"Date": a.date or dt.date.today().isoformat(), "Video": a.video.replace("|", "/"),
                 "Direction": a.direction, "Hook": " ".join(a.hook.replace("|", " ").split()),
                 "Words": str(hook_units(a.hook.replace("|", " "))), "Verdict": a.verdict, "CTR %": "", "Impressions": "",
                 "CTR noted": ""})
    with open(a.file, "w", encoding="utf-8") as fh:
        fh.write(write_rows(text, rows))
    print(f"Added run: {a.video} ({a.direction})")
    return 0


def cmd_add_ctr(a):
    text = read(a.file)
    _, rows = table(section(text, "History"))
    hit = [r for r in rows if r.get("Video", "").lower() == a.video.lower()] or \
          [r for r in rows if a.video.lower() in r.get("Video", "").lower()]
    if not hit:
        print(f"PROBLEM no History row matches '{a.video}'")
        return 1
    r = hit[-1]
    r["CTR %"] = f"{a.ctr:g}"
    r["Impressions"] = str(a.impressions or "")
    r["CTR noted"] = a.date or dt.date.today().isoformat()
    with open(a.file, "w", encoding="utf-8") as fh:
        fh.write(write_rows(text, rows))
    print(f"Recorded {a.ctr:g}% for {r['Video']}")
    return 0


def cmd_summary(a):
    text = read(a.file)
    _, rows = table(section(text, "History"))
    data = [r for r in rows if re.fullmatch(r"\d+(\.\d+)?", r.get("CTR %", ""))]
    if not data:
        print("No click-through reported yet. Ask for it a week or so after a video goes out.")
        return 0
    print(f"{len(data)} video(s) with a reported click-through rate.")
    alias = {"split": "panel", "card": "poster", "bleed": "cinema"}
    for key, label in (("Direction", "style"), ("Words", "number of words")):
        groups = {}
        for r in data:
            k = r.get(key) or "?"
            k = alias.get(k.lower(), k) if key == "Direction" else k
            groups.setdefault(k, []).append(float(r["CTR %"]))
        print(f"By {label}:")
        for k, v in sorted(groups.items(), key=lambda kv: -statistics.median(kv[1])):
            print(f"  {k}: median {statistics.median(v):.1f}% across {len(v)} video(s)")
    if len(data) < 5:
        print("Under five videos: treat any pattern as a hint to test, not a finding. Click-through also moves "
              "with the topic, the title and where the impressions came from.")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("file")
    r = sub.add_parser("add-run")
    r.add_argument("file")
    r.add_argument("--date")
    r.add_argument("--video", required=True)
    r.add_argument("--direction", required=True)
    r.add_argument("--hook", required=True)
    r.add_argument("--verdict", default="")
    t = sub.add_parser("add-ctr")
    t.add_argument("file")
    t.add_argument("--video", required=True)
    t.add_argument("--ctr", type=float, required=True)
    t.add_argument("--impressions", type=int)
    t.add_argument("--date")
    s = sub.add_parser("summary")
    s.add_argument("file")
    a = ap.parse_args()
    return {"check": cmd_check, "add-run": cmd_add_run, "add-ctr": cmd_add_ctr, "summary": cmd_summary}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
