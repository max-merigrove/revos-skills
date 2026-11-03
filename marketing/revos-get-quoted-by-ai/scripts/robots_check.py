#!/usr/bin/env python3
"""Read a founder's robots.txt and say, crawler by crawler, who can reach the site and what that means.

Usage:
  python3 scripts/robots_check.py <robots.txt> [--path /services/ ...] [--json-out report.json] [--fix-out robots-lines.txt]
  python3 scripts/robots_check.py --none [--json-out report.json]      no robots.txt to hand: every line UNKNOWN

Group rules follow the robots.txt standard (RFC 9309): a crawler obeys the group that names it and
ignores the * group; groups naming the same crawler are combined; the longest matching rule wins and
Allow wins a tie; * and $ work as wildcards. Crawler purposes come from references/agents.json, each
row with the date its source was checked. When a search crawler is blocked, --fix-out writes the
exact lines to change and the whole corrected file, re-checked so no other crawler changes.
Exit 0 when read (findings are in the report), 2 with STOP on input it cannot read. No network calls.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ensure_parent, read_text, save_json, stop  # noqa: E402

AGENTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references", "agents.json")


def load_agents():
    try:
        with open(AGENTS_FILE, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        stop("references/agents.json is missing or broken. Reinstall the skill.")


def parse(text):
    """Return (groups, sitemaps, problems). A group is {'agents': [...], 'rules': [(kind, pattern, line_no)], 'lines': [...]}."""
    groups, sitemaps, problems = [], [], []
    cur = None
    last_was_agent = False
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if ":" not in line:
            problems.append(f"line {n} is not a robots.txt rule: '{raw.strip()[:60]}'")
            continue
        key, _, val = line.partition(":")
        key, val = key.strip().lower(), val.strip()
        if key in ("user-agent", "useragent", "user agent"):
            if cur is None or not last_was_agent:
                cur = {"agents": [], "rules": [], "lines": []}
                groups.append(cur)
            cur["agents"].append(val)
            cur["lines"].append(n)
            last_was_agent = True
        elif key in ("allow", "disallow"):
            last_was_agent = False
            if cur is None:
                problems.append(f"line {n}: a {key} rule before any User-agent line is ignored by crawlers")
                continue
            cur["rules"].append((key, val, n))
            cur["lines"].append(n)
        elif key == "sitemap":
            sitemaps.append(val)
            last_was_agent = False
        else:
            last_was_agent = False  # crawl-delay, host and others are ignored here
    return groups, sitemaps, problems


def _pattern_regex(pat):
    anchored = pat.endswith("$")
    body = pat[:-1] if anchored else pat
    rx = "".join(".*" if ch == "*" else re.escape(ch) for ch in body)
    return re.compile("^" + rx + ("$" if anchored else ""))


def rules_for(groups, token):
    named = [g for g in groups if any(a.lower() == token.lower() for a in g["agents"])]
    if named:
        return [r for g in named for r in g["rules"]], "own"
    star = [g for g in groups if any(a.strip() == "*" for a in g["agents"])]
    if star:
        return [r for g in star for r in g["rules"]], "star"
    return [], "none"


def allowed(rules, path):
    """Longest match wins; Allow wins a tie; an empty Disallow allows everything."""
    best = None
    for kind, pat, n in rules:
        if pat == "":
            continue
        if _pattern_regex(pat).match(path):
            length = len(pat.rstrip("$"))
            if best is None or length > best[0] or (length == best[0] and kind == "allow"):
                best = (length, kind, pat, n)
    return (best is None or best[1] == "allow"), best


def check(text, paths, agents_data):
    groups, sitemaps, problems = parse(text)
    rows = []
    for a in agents_data["agents"]:
        rules, via = rules_for(groups, a["token"])
        blocked_paths, deciding = [], []
        for p in paths:
            ok, best = allowed(rules, p)
            if not ok:
                blocked_paths.append(p)
                d = f"line {best[3]}: Disallow: {best[2]}"
                if d not in deciding:
                    deciding.append(d)
        if not blocked_paths:
            status = "allowed"
        elif "/" in blocked_paths:
            status = "blocked"
        else:
            status = "partly blocked"
        if status == "allowed":
            verdict = "PASS"
        elif a["purpose"] == "search":
            verdict = "FAIL"
        elif a["purpose"] == "training":
            verdict = "training only"
        else:
            verdict = "WARN"
        rows.append({"token": a["token"], "operator": a["operator"], "purpose": a["purpose"], "product": a["product"],
                     "status": status, "verdict": verdict, "via": {"own": "its own group", "star": "the * group",
                                                                    "none": "no rule"}[via],
                     "blocked_paths": blocked_paths, "deciding_rules": deciding,
                     "if_blocked": a["if_blocked"], "checked_on": a["checked_on"], "source": a["source"]})
    return {"rows": rows, "sitemaps": sitemaps, "problems": problems, "groups": len(groups)}


def corrected_file(text, report, paths):
    """Return (corrected text, change lines) unblocking every blocked search crawler and nothing else."""
    groups, _s, _p = parse(text)
    targets = [r["token"] for r in report["rows"] if r["purpose"] == "search" and r["status"] != "allowed"]
    if not targets:
        return None, []
    lines = text.splitlines()
    drop_lines = set()
    changes = []
    new_groups = []
    for tok in targets:
        rules, via = rules_for(groups, tok)
        keep = [r for r in rules if not (r[0] == "disallow" and r[1] and any(_pattern_regex(r[1]).match(p) for p in paths))]
        for g in groups:
            for idx, ag in enumerate(g["agents"]):
                if ag.lower() == tok.lower():
                    drop_lines.add(g["lines"][idx])
        body = [f"{k.capitalize()}: {p}" for k, p, _n in keep if p] or []
        body.append("Allow: /")
        new_groups.append([f"User-agent: {tok}"] + body)
        if via == "own":
            changes.append(f"{tok}: remove the line 'User-agent: {tok}' from the group that blocks it, then add the new {tok} group below.")
        else:
            changes.append(f"{tok}: it is blocked by the * group. Add its own group (below) so it can read the site; the * group stays as it is for everyone else.")
    # drop groups whose every agent line was removed, with their rules
    for g in groups:
        agent_lines = g["lines"][:len(g["agents"])]
        if agent_lines and all(n in drop_lines for n in agent_lines):
            drop_lines.update(g["lines"])
    out = []
    for i, ln in enumerate(lines, 1):
        if i in drop_lines or (not ln.strip() and out and not out[-1].strip()):
            continue
        out.append(ln)
    while out and not out[-1].strip():
        out.pop()
    for ng in new_groups:
        out.append("")
        out.extend(ng)
    return "\n".join(out) + "\n", changes


def render(report, paths):
    out = []
    order = {"search": 0, "user": 1, "training": 2}
    for r in sorted(report["rows"], key=lambda x: order[x["purpose"]]):
        why = f" ({'; '.join(r['deciding_rules'])})" if r["deciding_rules"] else ""
        out.append(f"AGENT {r['verdict']}: {r['token']} [{r['operator']}, {r['purpose']}] {r['status']} via {r['via']}{why}. "
                   f"{r['if_blocked'] if r['status'] != 'allowed' else ''}".rstrip())
    for p in report["problems"]:
        out.append(f"FILE: {p}")
    for s in report["sitemaps"]:
        out.append(f"SITEMAP: {s}")
    dates = sorted({r["checked_on"] for r in report["rows"] if re.match(r"\d{4}-\d\d-\d\d", r["checked_on"])})
    unchecked = [r["token"] for r in report["rows"] if not re.match(r"\d{4}-\d\d-\d\d", r["checked_on"])]
    out.append(f"CHECKED ON: crawler purposes checked {dates[0] if dates else 'never'}"
               + (f"; not yet checked against the live source: {', '.join(unchecked)}" if unchecked else ""))
    blocked = [r["token"] for r in report["rows"] if r["verdict"] == "FAIL"]
    out.append("SUMMARY: " + (f"search crawler blocked: {', '.join(blocked)}" if blocked else "no search crawler blocked")
               + f"; paths checked: {', '.join(paths)}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("robots", nargs="?")
    ap.add_argument("--none", action="store_true", help="no robots.txt to hand")
    ap.add_argument("--path", action="append", default=[])
    ap.add_argument("--json-out")
    ap.add_argument("--fix-out")
    a = ap.parse_args()
    agents = load_agents()
    paths = ["/"] + [p if p.startswith("/") else "/" + p for p in a.path if p not in ("/", "")]
    if a.none or not a.robots:
        rows = [{"token": x["token"], "operator": x["operator"], "purpose": x["purpose"], "product": x["product"],
                 "status": "unknown", "verdict": "UNKNOWN", "via": "no file seen", "blocked_paths": [],
                 "deciding_rules": [], "if_blocked": x["if_blocked"], "checked_on": x["checked_on"], "source": x["source"]}
                for x in agents["agents"]]
        report = {"rows": rows, "sitemaps": [], "problems": ["no robots.txt seen: open your address plus /robots.txt and paste what it shows"],
                  "groups": 0, "seen": False}
        for r in rows:
            print(f"AGENT UNKNOWN: {r['token']} [{r['operator']}, {r['purpose']}] not seen. Settle it by pasting your robots.txt.")
        print("SUMMARY: robots.txt not seen; every crawler line is UNKNOWN, not FAIL")
        if a.json_out:
            save_json(a.json_out, report)
        return 0
    text = read_text(a.robots, "the robots.txt")
    head = text.lstrip()[:200].lower()
    if head.startswith("<!doctype") or head.startswith("<html") or "<body" in head:
        stop("that file is a web page, not a robots.txt. Your site may return a page for /robots.txt "
             "(often meaning there is none, so every crawler is allowed). Paste exactly what your address plus /robots.txt shows, or say 'none'.")
    if len(text) > 500_000:
        stop("that robots.txt is over 500 KB; crawlers stop reading at 500 KB. Paste the file as served, or the first part of it.")
    if not text.strip():
        report = check("", paths, agents)
        report["problems"].append("the file is empty: every crawler is allowed")
    else:
        report = check(text, paths, agents)
        if report["groups"] == 0 and not report["sitemaps"]:
            stop("no User-agent, Allow, Disallow or Sitemap lines found. Is this the robots.txt? Paste exactly what your address plus /robots.txt shows.")
    report["seen"] = True
    for line in render(report, paths):
        print(line)
    if a.fix_out:
        fixed, changes = corrected_file(text, report, paths)
        if fixed:
            after = check(fixed, paths, agents)
            before_map = {r["token"]: r["status"] for r in report["rows"]}
            for r in after["rows"]:
                if r["purpose"] == "search" and r["status"] != "allowed":
                    stop(f"internal check failed: {r['token']} still blocked after the fix. Do the change by hand.")
                if r["purpose"] != "search" and r["status"] != before_map[r["token"]]:
                    stop(f"internal check failed: the fix changed {r['token']}. Do the change by hand.")
            with open(ensure_parent(a.fix_out), "w", encoding="utf-8") as fh:
                fh.write("Robots.txt change: lets the search crawlers named below read your site again.\n")
                fh.write("Training crawlers you block stay blocked. Changes can take about a day to be picked up.\n\n")
                for c in changes:
                    fh.write(f"- {c}\n")
                fh.write("\nThe whole corrected file, ready to paste in place of the old one:\n\n")
                fh.write(fixed)
            print(f"FIX: wrote {a.fix_out} ({len(changes)} change(s)); re-checked: no other crawler changed")
        else:
            print("FIX: no search crawler is blocked; no robots-lines.txt written")
    if a.json_out:
        save_json(a.json_out, report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
