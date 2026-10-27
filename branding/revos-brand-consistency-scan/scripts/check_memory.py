#!/usr/bin/env python3
"""Write, read and check the Brand Consistency Scan memory file. It never holds client data.

Usage:
  python3 scripts/check_memory.py write <results.json> --out <memory.md> [--existing <old memory.md>]
        [--redaction <clean/redaction.json>] [--history "made | line chosen | verdict"]
        [--learning "rule | evidence | step | status"]...
      build the memory file from build_report.py's results, keeping the old Learnings and History.
      Prices in stored quotes are saved as [price]. Refuses (exit 1, nothing written) if any client
      name, email, phone number, postal code, address, bank detail or amount would be saved.
  python3 scripts/check_memory.py read <memory.md> --json-out <previous.json>
      turn a saved memory file into previous.json for a return run
  python3 scripts/check_memory.py check <memory.md> [--redaction <clean/redaction.json>]
      the sections and columns are intact, statuses are valid, at most 25 active learnings,
      and nothing personal to a client is in it

The founder can edit the file by hand; every reader is forgiving about spacing.
Exit 0 fine; 1 problems; 2 STOP. Standard library only. No network.
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scan_common as C  # noqa: E402

SECTIONS = ["Profile", "Agreed answers", "Assets", "Voice markers", "Last scores", "Learnings", "History"]
LEARN_COLS = ["#", "Learning", "Evidence", "Applies to step", "Status", "Added"]
HIST_COLS = ["Date", "Made", "Line chosen", "Verdict"]
ASSET_COLS = ["Id", "Asset", "Kind", "Weight", "Last scanned"] + [C.QLABEL[q] for q in C.QKEYS]
VOICE_COLS = ["Id", "Speaks as", "I", "We", "You", "Words a sentence", "Grade", "Reads as", "Contractions per 100 words"]
STATUSES = {"watch", "active", "retired"}
STEPS = {"start", "memory check", "intake", "diagnose", "make", "check", "deliver", "learn", "next step"}


def cell(v):
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v).replace("|", "/").replace("\n", " ").strip()


def section(text, name):
    m = re.search(r"^## " + re.escape(name) + r"\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    return m.group(1) if m else None


def table(block):
    rows = [ln.strip() for ln in (block or "").splitlines() if ln.strip().startswith("|")]
    if len(rows) < 2:
        return [], []
    head = [c.strip() for c in rows[0].strip("|").split("|")]
    body = []
    for r in rows[2:]:
        cells = [c.strip() for c in r.strip("|").split("|")]
        body.append(dict(zip(head, cells + [""] * (len(head) - len(cells)))))
    return head, body


def md_table(cols, rows):
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        out.append("| " + " | ".join(cell(x) for x in r) + " |")
    return "\n".join(out)


def privacy_problems(text, hashes=None):
    probs = [f"{'an' if k[0] in 'aeiou' else 'a'} {k} would be saved" for k, _v in C.personal_data_hits(text)]
    for m in C.MONEY_RE.finditer(text):
        probs.append(f"an amount would be saved ('{m.group(0)}')")
    for t in C.leaked_terms(text, hashes or []):
        probs.append(f"a removed client name would be saved ('{t}')")
    return sorted(set(probs))


def mask_money(s):
    return C.MONEY_RE.sub("[price]", s) if isinstance(s, str) else s


def cmd_check(a):
    p = Path(a.memory)
    if not p.exists():
        C.stop(f"{p} does not exist.")
    text = p.read_text(encoding="utf-8")
    probs = []
    for s in SECTIONS:
        if section(text, s) is None:
            probs.append(f"missing section '## {s}'")
    head, rows = table(section(text, "Learnings"))
    if head and head != LEARN_COLS:
        probs.append(f"Learnings columns are {head}, expected {LEARN_COLS}")
    active = 0
    for r in rows:
        st = r.get("Status", "").strip("~ ").lower()
        if st and st not in STATUSES:
            probs.append(f"learning '{r.get('Learning', '')[:40]}' has status '{st}' (watch, active or retired)")
        if st == "active":
            active += 1
        step = r.get("Applies to step", "").strip().lower()
        if step and step not in STEPS:
            probs.append(f"learning '{r.get('Learning', '')[:40]}' applies to '{step}', which is not a step in SKILL.md")
    if active > 25:
        probs.append(f"{active} active learnings; condense to 25 or fewer")
    hh, _ = table(section(text, "History"))
    if hh and hh != HIST_COLS:
        probs.append(f"History columns are {hh}, expected {HIST_COLS}")
    ah, _ = table(section(text, "Assets"))
    if ah and ah != ASSET_COLS:
        probs.append(f"Assets columns are {ah}, expected {ASSET_COLS}")
    hashes = (C.load_json(a.redaction, "redaction file").get("hashes") if a.redaction else None)
    probs += [f"privacy: {x}" for x in privacy_problems(text, hashes)]
    for x in probs:
        print("PROBLEM:", x)
    print(f"{len(probs)} problems")
    return 1 if probs else 0


def _asset_id(label, assets):
    lab = C.norm_text(label)
    for r in assets:
        if C.norm_text(r.get("Asset", "")) == lab or C.norm_text(r.get("Id", "")) == lab:
            return r.get("Id")
    return None


def parse_left(v, assets):
    """'Proposal: who you serve, what you do (aimed at ops buyers)' back to skip and its reason."""
    skip, why = {}, {}
    phrase2q = {C.QPHRASE[q]: q for q in C.QKEYS}
    for part in [x.strip() for x in (v or "").split(";") if x.strip()]:
        m = re.match(r"(.+?):\s*(.+?)(?:\s*\((.*)\))?$", part)
        if not m:
            continue
        aid = _asset_id(m.group(1), assets)
        qs = [phrase2q[p.strip()] for p in m.group(2).split(",") if p.strip() in phrase2q]
        if aid and qs:
            skip[aid] = qs
            if m.group(3):
                why[aid] = m.group(3)
    return skip, why


def parse_declined(v, assets):
    out = []
    phrase2q = {C.QPHRASE[q]: q for q in C.QKEYS}
    for part in [x.strip() for x in (v or "").split(";") if x.strip()]:
        m = re.match(r"(.+?):\s*(.+?)(\s*\(held for the decision\))?(?:\s*\((.*)\))?$", part)
        if m and _asset_id(m.group(1), assets) and m.group(2).strip() in phrase2q:
            out.append({"asset": _asset_id(m.group(1), assets), "question": phrase2q[m.group(2).strip()],
                        "by": "decision" if m.group(3) else "founder", "reason": m.group(4) or ""})
    return out


def parse_sold(v, assets):
    out = {}
    for part in [x.strip() for x in (v or "").split(";") if x.strip()]:
        lab, _, who = part.partition(":")
        aid = _asset_id(lab, assets)
        if aid:
            out[aid] = "others" if "else" in who else "me"
    return out


def cmd_read(a):
    p = Path(a.memory)
    if not p.exists():
        C.stop(f"{p} does not exist.")
    text = p.read_text(encoding="utf-8")
    if section(text, "Profile") is None:
        C.stop(f"{p} is not a Brand Consistency Scan memory file (no Profile section). Run as a first scan.")
    upd = re.search(r"Updated:\s*(\d{4}-\d{2}-\d{2})", text)
    _h, prof = table(section(text, "Profile"))
    pf = {r.get("Field", ""): r for r in prof}
    _h, agreed = table(section(text, "Agreed answers"))
    lab2q = {C.QLABEL[q]: q for q in C.QKEYS}
    _h, assets = table(section(text, "Assets"))
    _h, voice = table(section(text, "Voice markers"))
    _h, scores = table(section(text, "Last scores"))
    _h, learn = table(section(text, "Learnings"))

    def num(x):
        try:
            return float(x) if "." in x else int(x)
        except (ValueError, TypeError):
            return None
    sc = {}
    for r in scores:
        q = lab2q.get(r.get("Question", ""))
        if q:
            sc[q] = num(r.get("Points", ""))
        elif r.get("Question", "").lower() == "total":
            sc["total"] = num(r.get("Points", ""))
        elif r.get("Question", "").lower().startswith("alignment"):
            sc["alignment"] = num(r.get("Points", ""))
    out = {
        "date": upd.group(1) if upd else "",
        "business": pf.get("Business", {}).get("Value", ""),
        "founder_sells": C.sells_from_words(pf.get("Who sells", {}).get("Value", "me")),
        "sold_by": parse_sold(pf.get("Who sells which asset", {}).get("Value", ""), assets),
        "skip": parse_left(pf.get("Left out of the scan", {}).get("Value", ""), assets)[0],
        "skip_reasons": parse_left(pf.get("Left out of the scan", {}).get("Value", ""), assets)[1],
        "declined": parse_declined(pf.get("Edits you declined", {}).get("Value", ""), assets),
        "english_source": {"counted from your spelling": "counted", "founder said": "founder"}.get(
            pf.get("English", {}).get("Source", ""), "country"),
        "core_line": pf.get("Core line", {}).get("Value", ""),
        "core_line_date": pf.get("Core line", {}).get("Updated", ""),
        "excluded": pf.get("Left out of the scan", {}).get("Value", ""),
        "locale": {
            "country": (lambda v: v if re.fullmatch(r"[A-Z]{2}", v or "") else None)(pf.get("Country", {}).get("Value", "")),
            "english": C.english_from_label(pf.get("English", {}).get("Value", "")),
            "decimal": {"point": "dot", "comma": "comma"}.get(((pf.get("Decimals", {}).get("Value", "") or "").split() or [""])[0]),
            "paper": (lambda v: v.lower() if v in ("A4", "Letter") else None)(pf.get("Paper", {}).get("Value", "")),
            "dates": DATE_STYLE_READ.get(pf.get("Date style", pf.get("Dates", {})).get("Value", "")),
        },
        "agreed_answers": {lab2q[r["Question"]]: r.get("Agreed answer", "") for r in agreed if r.get("Question") in lab2q and r.get("Agreed answer")},
        "scores": sc,
        "assets": [{"id": r.get("Id"), "label": r.get("Asset"), "kind": r.get("Kind"), "weight": num(r.get("Weight", "")),
                    "last_scanned": r.get("Last scanned"),
                    "quotes": {q: (r.get(C.QLABEL[q]) or None) if r.get(C.QLABEL[q]) not in ("", "not stated") else None
                               for q in C.QKEYS}} for r in assets if r.get("Id")],
        "voice": {r.get("Id"): {"person": r.get("Speaks as"), "i": num(r.get("I", "")) or 0, "we": num(r.get("We", "")) or 0,
                                "you": num(r.get("You", "")) or 0,
                                "avg_sentence_words": num(r.get("Words a sentence", "")), "grade": num(r.get("Grade", "")),
                                "level": r.get("Reads as") or None,
                                "contractions_per_100": num(r.get("Contractions per 100 words", "")),
                                "words": 0, "exclamations": 0,
                                "measurable": num(r.get("Words a sentence", "")) is not None} for r in voice if r.get("Id")},
        "learnings_active": [{"learning": r.get("Learning"), "step": r.get("Applies to step")} for r in learn
                             if r.get("Status", "").lower() == "active"],
        "learnings_watch": [{"learning": r.get("Learning"), "step": r.get("Applies to step")} for r in learn
                            if r.get("Status", "").lower() == "watch"],
    }
    Path(a.json_out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"WROTE: {a.json_out} (saved {out['date'] or 'undated'}: core line, {len(out['agreed_answers'])} agreed answers, "
          f"{len(out['assets'])} assets, last score {sc.get('total')}, {len(out['learnings_active'])} active learnings)")
    return 0


# The date style is a format, not a date: "day month year (20 October 2026)" was once read as a scan date.
DATE_STYLE_LABEL = {"dmy": "day month year, as in 20 October 2026", "mdy": "month day, year, as in October 20, 2026",
                    "ymd": "year-month-day, as in 2026-10-20"}
DATE_STYLE_READ = dict({v: k for k, v in DATE_STYLE_LABEL.items()},
                       **{"20 October 2026": "dmy", "October 20, 2026": "mdy", "2026-10-20": "ymd"})  # files saved before 1.3


def cmd_write(a):
    res = C.load_json(a.results, "results file")
    if res.get("skill") != C.SKILL:
        C.stop("that results file was not made by build_report.py for this skill.")
    old = Path(a.existing).read_text(encoding="utf-8") if a.existing and Path(a.existing).exists() else ""
    today = res.get("date") or date.today().isoformat()
    _h, old_prof = table(section(old, "Profile"))
    oldp = {r.get("Field"): r for r in old_prof}

    def prof_row(field, value, source):
        o = oldp.get(field)
        if o and C.norm_text(o.get("Value", "")) == C.norm_text(str(value)):
            return [field, o.get("Value"), o.get("Source"), o.get("Updated")]
        return [field, value, source, today]
    labels = {x["id"]: x.get("label") or x["id"] for x in res.get("assets") or []}

    def plain(v):  # "; " separates entries in these cells, so a reason never carries one
        return str(v or "").replace(";", ",").replace("(", "").replace(")", "").strip()
    left = [f"{plain(x.get('label'))}, whole asset ({plain(x.get('reason'))})" if isinstance(x, dict) else plain(x)
            for x in res.get("excluded") or []]
    for aid, qs in (res.get("skip") or {}).items():
        qs = [q for q in qs if q in C.QKEYS]
        if qs:
            why = (res.get("skip_reasons") or {}).get(aid)
            left.append(f"{labels.get(aid, aid)}: {', '.join(C.QPHRASE[q] for q in qs)}" + (f" ({plain(why)})" if why else ""))
    excluded = "; ".join(left)
    declined = "; ".join(f"{labels.get(d['asset'], d['asset'])}: {C.QPHRASE.get(d['question'], d['question'])}"
                         + (" (held for the decision)" if d.get("by") == "decision" else "")
                         + (f" ({plain(d['reason'])})" if d.get("reason") else "") for d in res.get("declined") or [])
    sold = "; ".join(f"{labels.get(a, a)}: {'someone else' if v in ('others', 'team') else 'me'}"
                     for a, v in (res.get("sold_by") or {}).items())
    profile = [prof_row("Business", res.get("business", ""), "founder said"),
               prof_row("Who sells", C.SELLS_WORDS.get(res.get("founder_sells", "me"), "me"), "founder said"),
               prof_row("Who sells which asset", sold, "founder said"),
               prof_row("Core line", mask_money(res.get("core_line", "")),
                        {"founder": "chosen by founder", "memory": "kept from an earlier scan"}.get(res.get("core_line_by"), "recommended, not yet agreed by you")),
               prof_row("Left out of the scan", excluded, "founder said"),
               prof_row("Edits you declined", declined, "founder said")]
    loc = res.get("locale") or {}
    esrc = {"counted": "counted from your spelling", "founder": "founder said",
            "country": "from your country; your copy had too few spelling markers to count"}.get(res.get("english_source"), "not known")
    profile += [prof_row("Country", loc.get("country") or "not known", "founder said or read from the assets"),
                prof_row("English", C.english_label(loc.get("english"), loc.get("country")), esrc),
                prof_row("Decimals", {"dot": "point (1,234.56)", "comma": "comma (1.234,56)"}.get(loc.get("decimal"), "not known"),
                         "read from your copy"),
                prof_row("Paper", {"a4": "A4", "letter": "Letter"}.get(loc.get("paper"), "not known"), "follows the country"),
                prof_row("Date style", DATE_STYLE_LABEL.get(loc.get("dates"), DATE_STYLE_LABEL["ymd"]),
                         "follows the country")]
    agreed = [[C.QLABEL[q], mask_money(res.get("agreed_answers", {}).get(q, "")), today] for q in C.QKEYS]
    _h, old_assets = table(section(old, "Assets"))
    new_ids = {x["id"] for x in res.get("assets", [])}
    arows = []
    for x in res.get("assets", []):
        last = x.get("from_memory") or today
        arows.append([x["id"], x["label"], x["kind"], x["weight"], last] +
                     [mask_money(x.get("quotes", {}).get(q)) or "not stated" for q in C.QKEYS])
    for r in old_assets:
        if r.get("Id") and r["Id"] not in new_ids:
            arows.append([r.get(c, "") for c in ASSET_COLS])
    vrows = []
    for k, v in (res.get("voice") or {}).items():
        vrows.append([k, v.get("person"), v.get("i"), v.get("we"), v.get("you"), v.get("avg_sentence_words"), v.get("grade"),
                      v.get("level"), v.get("contractions_per_100")])
    sc = res.get("scores", {})
    srows = [[C.QLABEL[q], sc.get(q), C.QWEIGHT[q]] for q in C.QKEYS] + [["Total", sc.get("total"), 100]]
    if sc.get("alignment") is not None:
        srows.append(["Alignment with the agreed answers", sc.get("alignment"), 100])
    _h, learn = table(section(old, "Learnings"))
    lrows = [[r.get(c, "") for c in LEARN_COLS] for r in learn]
    for spec in a.learning or []:
        parts = [x.strip() for x in spec.split("|")]
        if len(parts) != 4:
            C.stop('a learning is "rule | evidence | step | status", four parts separated by |.')
        if parts[3].lower() not in STATUSES:
            C.stop(f"learning status '{parts[3]}' must be watch, active or retired.")
        if parts[2].lower() not in STEPS:
            C.stop(f"learning step '{parts[2]}' must be one of the SKILL.md steps (Intake, Make, Check, Deliver ...).")
        lrows.append([len(lrows) + 1, parts[0], parts[1], parts[2], parts[3].lower(), today])
    _h, hist = table(section(old, "History"))
    hrows = [[r.get(c, "") for c in HIST_COLS] for r in hist]
    if a.history:
        parts = [x.strip() for x in a.history.split("|")]
        parts = (parts + ["", "", ""])[:3]
        hrows.append([today] + parts)
    text = "\n".join([
        "# Brand Consistency Scan memory", "",
        f"Skill: {C.SKILL} | Memory version: 1 | Updated: {today}", "",
        "Keep this file. Attach it next time (or leave it in your merigrove-memory folder, or your Claude Project) and the "
        "scan picks up where you left off: it scores your changed assets against the line you agreed. You can edit it by hand. "
        "It holds no client names, fees or contact details; they are removed before anything is read, and this file is "
        "checked for them before it is saved.", "",
        "## Profile", "", md_table(["Field", "Value", "Source", "Updated"], profile), "",
        "## Agreed answers", "", md_table(["Question", "Agreed answer", "Updated"], agreed), "",
        "## Assets", "", "Quotes are word for word from the last scan, after client names and fees were removed.", "",
        md_table(ASSET_COLS, arows), "",
        "## Voice markers", "", md_table(VOICE_COLS, vrows), "",
        "## Last scores", "", md_table(["Question", "Points", "Out of"], srows), "",
        "## Learnings", "", md_table(LEARN_COLS, lrows), "",
        "Status: watch (seen once), active (approved or repeated), retired (kept for the record, no longer applied).", "",
        "## History", "", md_table(HIST_COLS, hrows), ""])
    hashes = C.load_json(a.redaction, "redaction file").get("hashes") if a.redaction else None
    probs = privacy_problems(text, hashes)
    if probs:
        for x in probs:
            print("PROBLEM: privacy:", x)
        print(f"{len(probs)} problems. The memory file was not written. Remove the personal detail and run again.")
        return 1
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"WROTE: {out}")
    a.memory = str(out)
    return cmd_check(a)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    w = sub.add_parser("write")
    w.add_argument("results")
    w.add_argument("--out", required=True)
    w.add_argument("--existing")
    w.add_argument("--redaction")
    w.add_argument("--history")
    w.add_argument("--learning", action="append")
    r = sub.add_parser("read")
    r.add_argument("memory")
    r.add_argument("--json-out", required=True)
    c = sub.add_parser("check")
    c.add_argument("memory")
    c.add_argument("--redaction")
    a = ap.parse_args()
    if a.cmd == "write":
        sys.exit(cmd_write(a))
    if a.cmd == "read":
        sys.exit(cmd_read(a))
    if a.cmd == "check":
        sys.exit(cmd_check(a))
    print(__doc__)
    sys.exit(2)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print(f"STOP: the memory step could not finish ({type(e).__name__}: {e}). Nothing was written.")
        sys.exit(2)
