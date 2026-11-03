#!/usr/bin/env python3
"""Read, write and check the Dead Lead Revival memory file.

The memory holds the founder's profile (offer, voice, locale, pace, channels, how their groups came onto the list),
standing exclusions by name, learnings and one History line per run. It never holds the contact list: the
workbook is the contact log and lives in the founder's own files.

Usage:
  python3 scripts/memory.py read <memory.md> --json-out <settings-from-memory.json>
  python3 scripts/memory.py write --settings <settings.json> --out <memory.md> [--plan <work>/plan-built.json]
        [--existing <old memory.md>] [--history "verdict"] [--learning "rule | evidence | step | status"]
        [--replied N --booked N --bounced N --no-reply N] [--exclude "name | why"]
  python3 scripts/memory.py validate <memory.md>
Write only after the founder has approved what is saved. Standard library only. No network calls.
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from segment import ABBR, SEGMENT_ORDER  # noqa: E402

SKILL = "revos-dead-lead-revival"
PROFILE = [  # label, settings key
    ("Business", "business"), ("What you sell", "offer"), ("Next step you want", "next_step"),
    ("What has changed since", "changed"), ("Your name in messages", "sign_off"), ("Country", "country"),
    ("Your English", "english"), ("Date order", "date_order"), ("Number style", "decimal"),
    ("Sending days", "working_days"), ("Days off", "days_off"), ("Messages a day", "daily_cap"),
    ("Channels", "channels"), ("Texts only to people who texted you", "text_only_if_texted"),
    ("Cooldown months", "cooldown_months"), ("Your prices", "prices"), ("Prices in messages from touch", "price_from_touch"),
    ("Words never in a first message", "never_in_first_touches"), ("Hand-written first messages", "tier_a"),
    ("How unknown contacts came onto your list", "source_default"), ("Source rules", "source_rules"),
    ("Opt-out line for email", "opt_out_email"), ("Opt-out line for texts and DMs", "opt_out_short"),
    ("Language of your messages", "message_language"), ("Your phrases for the personal field", "context_phrases"),
    ("Month names in your messages", "month_names"),
]
AUTO_EXCLUDE = {"asked_to_stop": "asked to stop", "unsubscribed": "unsubscribed", "dispute": "dispute on file: ring, "
                "don't message", "off_limits": "you said leave them out"}
LISTS = {"changed", "days_off", "channels", "prices", "never_in_first_touches", "month_names"}
LEARN_HEAD = "| # | Learning | Evidence | Applies to step | Status | Added |"
HIST_HEAD = "| Date | Made | People by group | Held back | Replied | Calls booked | Bounced | No reply | Verdict |"
EXCL_HEAD = "| Name | Why | Added |"
STEPS = {"intake", "diagnose", "make", "check", "deliver", "learn"}
STATUSES = {"watch", "active", "retired"}


def cell(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, dict):
        return "; ".join(f"{k} = {x}" for k, x in v.items()).replace("|", "/")
    if isinstance(v, (list, tuple)):
        if v and isinstance(v[0], dict):
            return "; ".join(f"{x.get('match')} = {x.get('source')}" for x in v)
        return "; ".join(str(x) for x in v)
    return str(v).replace("|", "/").replace("\n", " ").strip()


def section(text, heading):
    m = re.search(rf"^## {re.escape(heading)}\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not m:
        return None
    lines = [ln.strip() for ln in m.group(1).splitlines() if ln.strip().startswith("|")]
    if len(lines) < 2:
        return []
    head = [c.strip() for c in lines[0].strip("|").split("|")]
    rows = []
    for ln in lines[2:]:
        cells = [c.strip() for c in ln.strip("|").split("|")]
        rows.append(dict(zip(head, cells + [""] * (len(head) - len(cells)))))
    return rows


def parse_value(key, v):
    if v == "":
        return None
    if key in LISTS:
        return [x.strip() for x in v.split(";") if x.strip()]
    if key == "context_phrases":
        out = {}
        for part in v.split(";"):
            if "=" in part:
                a, b = part.split("=", 1)
                out[a.strip()] = b.strip()
        return out
    if key == "source_rules":
        out = []
        for part in v.split(";"):
            if "=" in part:
                a, b = part.split("=", 1)
                out.append({"match": a.strip(), "source": b.strip()})
        return out
    if key == "text_only_if_texted":
        return v.lower() in ("yes", "true", "1")
    if key in ("daily_cap", "cooldown_months", "tier_a", "price_from_touch"):
        m = re.search(r"\d+", v)
        return int(m.group(0)) if m else None
    return v


def cmd_read(a):
    p = Path(a.memory)
    if not p.exists():
        print(f"STOP: cannot find {p}")
        sys.exit(2)
    text = p.read_text(encoding="utf-8")
    prof = section(text, "Profile")
    if prof is None:
        print("STOP: this file has no Profile section; it is not a Dead Lead Revival memory file")
        sys.exit(2)
    lab = dict(PROFILE)
    out = {}
    for r in prof:
        k = lab.get(r.get("Field", ""))
        if k:
            val = parse_value(k, r.get("Value", ""))
            if val not in (None, [], ""):
                out[k] = val
    excl = section(text, "Standing exclusions") or []
    out["exclude"] = [r["Name"] for r in excl if r.get("Name")]
    out["exclude_notes"] = {r["Name"]: f"standing exclusion: {r.get('Why') or 'you said leave them out'}" for r in excl
                            if r.get("Name")}
    learn = section(text, "Learnings") or []
    act = [r for r in learn if r.get("Status", "").lower() == "active"]
    watch = [r for r in learn if r.get("Status", "").lower() == "watch"]
    hist = section(text, "History") or []
    upd = re.search(r"Updated:\s*(\d{4}-\d{2}-\d{2})", text)
    out["previous_run"] = hist[-1].get("Date") if hist else (upd.group(1) if upd else None)
    if a.json_out:
        Path(a.json_out).write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"WROTE: {a.json_out}")
    else:
        print(json.dumps(out, indent=1, ensure_ascii=False))
    print(f"REMEMBERED: {out.get('business', 'your business')}; {out.get('daily_cap', 15)} a day on "
          f"{out.get('working_days', 'mon-fri')}; channels {', '.join(out.get('channels', ['email']))}; "
          f"last run {out['previous_run'] or 'not recorded'}; {len(out['exclude'])} standing exclusions")
    for r in act:
        print(f"ACTIVE: {r.get('Learning')} (step {r.get('Applies to step')})")
    for r in watch:
        print(f"WATCH: {r.get('Learning')} (not applied until the founder approves it)")


def cmd_write(a):
    s = json.loads(Path(a.settings).read_text(encoding="utf-8"))
    plan = json.loads(Path(a.plan).read_text(encoding="utf-8")) if a.plan else None
    old = Path(a.existing).read_text(encoding="utf-8") if a.existing and Path(a.existing).exists() else ""
    today = (plan["settings"]["today"] if plan else s.get("today")) or date.today().isoformat()
    learn = section(old, "Learnings") or []
    hist = section(old, "History") or []
    excl = section(old, "Standing exclusions") or []
    for x in a.learning or []:
        parts = [p.strip() for p in x.split("|")]
        if len(parts) != 4 or parts[3].lower() not in STATUSES or parts[2].lower() not in STEPS:
            print("STOP: --learning needs 'rule | evidence | step | status', step one of "
                  f"{', '.join(sorted(STEPS))} and status watch, active or retired")
            sys.exit(2)
        learn.append({"Learning": parts[0], "Evidence": parts[1], "Applies to step": parts[2].capitalize(),
                      "Status": parts[3].lower(), "Added": today})
    if sum(1 for r in learn if r.get("Status") == "active") > 25:
        print("STOP: more than 25 active learnings; condense or retire some first")
        sys.exit(2)
    names = {r["Name"].lower() for r in excl}
    for x in a.exclude or []:
        n, _, why = x.partition("|")
        if n.strip() and n.strip().lower() not in names:
            excl.append({"Name": n.strip(), "Why": why.strip() or "you said leave them out", "Added": today})
    for n in s.get("exclude", []) or []:
        if n.lower() not in names and n.lower() not in {r["Name"].lower() for r in excl}:
            excl.append({"Name": n, "Why": "you said leave them out", "Added": today})
    # anyone this run held back for good (asked to stop, unsubscribed, a dispute, off limits) is remembered by name,
    # so a new list next time keeps them out even without the tracker
    auto = 0
    for h in (plan or {}).get("held", []):
        code = h.get("held_code")
        nm = str(h.get("name") or "").strip()
        if code in AUTO_EXCLUDE and nm and "@" not in nm and nm.lower() not in {r["Name"].lower() for r in excl}:
            excl.append({"Name": nm, "Why": AUTO_EXCLUDE[code], "Added": today})
            auto += 1
    if plan:
        cs = plan["contacts"]
        groups = "; ".join(f"{ABBR[g]} {sum(1 for c in cs if c['segment'] == g)}" for g in SEGMENT_ORDER
                           if any(c["segment"] == g for c in cs))
        hist.append({"Date": today, "Made": f"tracker and messages, {len(cs)} people", "People by group": groups,
                     "Held back": str(len(plan["held"])), "Replied": str(a.replied if a.replied is not None else "not yet"),
                     "Calls booked": str(a.booked if a.booked is not None else "not yet"),
                     "Bounced": str(a.bounced if a.bounced is not None else "not yet"),
                     "No reply": str(a.no_reply if a.no_reply is not None else "not yet"),
                     "Verdict": a.history or "not given"})
    lines = [f"# Dead Lead Revival memory", "",
             f"Skill: {SKILL} | Memory version: 1 | Updated: {today}", "",
             "Keep this file. Attach it next time (or leave it in your merigrove-memory folder, or your Claude Project) "
             "with the tracker, and the skill picks up where you left off. You can edit it by hand. It holds no "
             "contact list: your tracker does.", "", "## Profile", "", "| Field | Value | Source | Updated |",
             "|---|---|---|---|"]
    for label, k in PROFILE:
        v = s.get(k)
        if v in (None, "", [], {}):
            continue
        lines.append(f"| {label} | {cell(v)} | founder said | {today} |")
    lines += ["", "## Standing exclusions", "", EXCL_HEAD, "|---|---|---|"]
    for r in excl:
        lines.append(f"| {cell(r.get('Name'))} | {cell(r.get('Why'))} | {cell(r.get('Added'))} |")
    lines += ["", "## Learnings", "", LEARN_HEAD, "|---|---|---|---|---|---|"]
    for i, r in enumerate(learn, 1):
        lines.append(f"| {i} | {cell(r.get('Learning'))} | {cell(r.get('Evidence'))} | {cell(r.get('Applies to step'))} | "
                     f"{cell(r.get('Status'))} | {cell(r.get('Added'))} |")
    lines += ["", "Status: watch (seen once), active (approved or repeated), retired (kept for the record, no longer "
              "applied). A reply-rate learning needs at least 20 people in the group before it becomes active.", "",
              "## History", "", HIST_HEAD, "|---|---|---|---|---|---|---|---|---|"]
    for r in hist:
        lines.append("| " + " | ".join(cell(r.get(h, "")) for h in
                                       ["Date", "Made", "People by group", "Held back", "Replied", "Calls booked",
                                        "Bounced", "No reply", "Verdict"]) + " |")
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"WROTE: {out}")
    print(f"EXCLUSIONS: {len(excl)} standing ({auto} added from this run's held-back list: asked to stop, unsubscribed, "
          "disputes, off limits): " + ("; ".join(f"{r['Name']} ({r.get('Why')})" for r in excl) or "none"))


def cmd_validate(a):
    p = Path(a.memory)
    if not p.exists():
        print(f"STOP: cannot find {p}")
        sys.exit(2)
    text = p.read_text(encoding="utf-8")
    P = []
    if SKILL not in text:
        P.append("the file does not name this skill")
    for h in ("Profile", "Standing exclusions", "Learnings", "History"):
        if section(text, h) is None:
            P.append(f"missing section: {h}")
    for r in section(text, "Learnings") or []:
        if r.get("Status", "").lower() not in STATUSES:
            P.append(f"learning '{r.get('Learning')}' has status '{r.get('Status')}'")
        if r.get("Applies to step", "").lower() not in STEPS:
            P.append(f"learning '{r.get('Learning')}' applies to unknown step '{r.get('Applies to step')}'")
    if re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}", text):
        P.append("an email address is in the memory file; it must hold no contact details")
    if re.search(r"\+?\d[\d ()-]{8,}\d", re.sub(r"\d{4}-\d{2}-\d{2}", "", text)):
        P.append("a phone number appears to be in the memory file")
    if "\u2014" in text or "\u2013" in text:
        P.append("dash in the memory file")
    for x in P:
        print("PROBLEM:", x)
    print(f"{len(P)} problems")
    sys.exit(1 if P else 0)


def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = a.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("read")
    r.add_argument("memory")
    r.add_argument("--json-out")
    w = sub.add_parser("write")
    w.add_argument("--settings", required=True)
    w.add_argument("--out", required=True)
    w.add_argument("--plan")
    w.add_argument("--existing")
    w.add_argument("--history")
    w.add_argument("--learning", action="append")
    w.add_argument("--exclude", action="append")
    for k in ("replied", "booked", "bounced", "no-reply"):
        w.add_argument(f"--{k}", type=int)
    v = sub.add_parser("validate")
    v.add_argument("memory")
    a2 = a.parse_args()
    try:
        {"read": cmd_read, "write": cmd_write, "validate": cmd_validate}[a2.cmd](a2)
    except (OSError, json.JSONDecodeError, KeyError) as e:
        print(f"STOP: could not use the files given ({type(e).__name__}: {e})")
        sys.exit(2)


if __name__ == "__main__":
    main()
