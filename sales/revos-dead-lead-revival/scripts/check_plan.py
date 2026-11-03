#!/usr/bin/env python3
"""Open the finished tracker and messages document and prove the plan keeps its promises.

Checks: the six sheets in order; every row read is on Contacts or Held back exactly once (when the plan is given);
every Send queue row points at a Contacts row and none at a held-back contact; every send date is a working day,
no day over the cap, touches in order at least two days apart and nothing after a sequence's last touch; the
status column has its drop-down; [NEED counts match the not-ready messages; every group in the document has 3 to
5 touches ending with a close-the-file message; no em or en dash anywhere; both files carry the credit in their
properties; no price or money in touches 1 and 2.

Usage: python3 scripts/check_plan.py <tracker.xlsx> <messages.docx> [--plan <work>/plan-built.json]
Prints PROBLEM lines and a count; exit 1 on any problem, exit 2 with STOP: if a file cannot be opened.
Standard library only. No network calls.
"""
import argparse
import json
import re
import sys
import zipfile
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import office  # noqa: E402

SHEETS = ["Today", "Segments", "Contacts", "Send queue", "Held back", "Rules"]
import check_copy  # noqa: E402
CLOSE_RX = re.compile(r"(clos(e|ing) (your|the|my) file|(won'?t|will not|not|never) (write|message|get in touch|follow up|"
                      r"chase|email|text|contact you) again|last (note|message|time)|leave (it|you) (there|be|alone)|"
                      r"stop (writing|messaging)|(take|taking) (you|this) off|this is my last|" + check_copy.OPT_OUT[1:-1] + ")",
                      re.I)
MONEY = re.compile(r"[$£€¥₹]\s?\d|\d\s?(€|%)|\d+\s?(USD|GBP|EUR|AUD|CAD|NZD|SGD)\b")


def table(rows):
    if not rows:
        return [], []
    head = [str(h or "") for h in rows[0]]
    body = [dict(zip(head, r)) for r in rows[1:] if any(v not in (None, "") for v in r)]
    return head, body


def as_date(v):
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


def check(xlsx, docx, plan=None):
    P = []
    try:
        book = office.read_xlsx(xlsx)
    except Exception as e:  # noqa: BLE001
        return [f"the workbook cannot be opened: {e}"]
    names = list(book)
    if names != SHEETS:
        P.append(f"sheets are {names}, expected {SHEETS}")
    _h, contacts = table(book.get("Contacts", []))
    _h, queue = table(book.get("Send queue", []))
    _h, held = table(book.get("Held back", []))
    cref = {c.get("Ref") for c in contacts}
    href = {h.get("Ref") for h in held}
    if cref & href:
        P.append(f"on both Contacts and Held back: {sorted(cref & href)[:5]}")
    if len(cref) != len(contacts):
        P.append("a contact appears twice on Contacts")
    if plan:
        n_in = plan["rows_in"]
        limit = plan["settings"].get("batch_limit")
        if not limit and len(contacts) + len(held) != n_in:
            P.append(f"{n_in} rows read but {len(contacts)} on Contacts and {len(held)} on Held back")
    for q in queue:
        if q.get("Ref") not in cref:
            P.append(f"Send queue row for {q.get('Ref')} has no Contacts row")
        if q.get("Ref") in href:
            P.append(f"held-back contact {q.get('Ref')} is in the Send queue")
    workdays = set(plan["schedule"]["workdays"]) if plan else None
    off = {date.fromisoformat(d) for d in plan["schedule"]["days_off"]} if plan else set()
    cap = plan["settings"]["daily_cap"] if plan else None
    per_day, per_ref = {}, {}
    for q in queue:
        d = as_date(q.get("Date"))
        if not d:
            P.append(f"Send queue row for {q.get('Ref')} has no date")
            continue
        per_day[d] = per_day.get(d, 0) + 1
        m = re.match(r"(\d+) of (\d+)", str(q.get("Touch") or ""))
        if not m:
            P.append(f"Send queue row for {q.get('Ref')} has no touch number")
            continue
        per_ref.setdefault(q.get("Ref"), []).append((int(m.group(1)), int(m.group(2)), d, q))
        if workdays is not None and (d.weekday() not in workdays or d in off):
            P.append(f"{q.get('Ref')} touch {m.group(1)} is dated {d}, not one of your working days")
        if int(m.group(1)) <= 2 and MONEY.search(str(q.get("Message") or "")):
            P.append(f"{q.get('Ref')} touch {m.group(1)} carries money or a percentage")
    if cap:
        for d, n in per_day.items():
            if n > cap:
                P.append(f"{d} has {n} messages, over your cap of {cap}")
    for ref, ts in per_ref.items():
        ts.sort()
        nums = [t[0] for t in ts]
        if nums != list(range(nums[0], nums[0] + len(nums))):
            P.append(f"{ref} touches are not in sequence: {nums}")
        if ts[-1][0] != ts[-1][1]:
            P.append(f"{ref} sequence does not end on its last touch ({ts[-1][0]} of {ts[-1][1]})")
        for a, b in zip(ts, ts[1:]):
            if b[2] < a[2] + timedelta(days=2):
                P.append(f"{ref} touch {b[0]} is less than two days after touch {a[0]}")
        last_msg = str(ts[-1][3].get("Message") or "")
        if "[NEED" not in str(ts[-1][3].get("Ready")) and not CLOSE_RX.search(last_msg) and \
                not (plan and check_copy.has_own_opt_out(last_msg, plan["settings"])):
            P.append(f"{ref} last touch does not close the file")
    need_rows = sum(1 for q in queue if "[NEED" in str(q.get("Ready") or ""))
    if plan:
        nr = sum(1 for m in plan["messages"] if not m["ready"])
        if nr != need_rows:
            P.append(f"{nr} messages are not ready but {need_rows} Send queue rows say [NEED")
    try:
        z = zipfile.ZipFile(xlsx)
        sheet3 = z.read("xl/worksheets/sheet3.xml").decode("utf-8")
        if "<dataValidation " not in sheet3 or "not started" not in sheet3:
            P.append("the Status column on Contacts has no drop-down")
    except (KeyError, zipfile.BadZipFile):
        P.append("cannot read the Contacts sheet XML")
    texts = []
    for sh, rows in book.items():
        for r in rows:
            for v in r:
                if isinstance(v, str):
                    texts.append((sh, v))
    for sh, v in texts:
        if "\u2014" in v or "\u2013" in v:
            P.append(f"dash in the workbook ({sh}): '{v[:50]}'")
            break
    try:
        dt = office.read_docx_text(docx)
    except ValueError as e:
        return P + [str(e)]
    if "\u2014" in dt or "\u2013" in dt:
        P.append("dash in the document")
    for f in (xlsx, docx):
        if office.core_description(f) != office.MADE_WITH:
            P.append(f"{Path(f).name} properties do not carry '{office.MADE_WITH}'")
    if re.search(r"\{[a-z_]+\}", " ".join(q.get("Message") or "" for q in queue)):
        P.append("a raw {field} reached the Send queue")
    if re.search(r"\{[a-z_]+\}", dt):
        P.append("a raw {field} is in the messages document")
    # sequences in the document: 3 to 5 touches per group, last closes the file
    blocks = re.split(r"\n(?=[A-Z]{2}-1\. Day 0)", dt)
    groups = re.findall(r"\n([A-Z]{2})-(\d)\. Day (\d+)(: closing the file)?", dt)
    by = {}
    for ab, n, _day, closing in groups:
        by.setdefault(ab, []).append((int(n), bool(closing)))
    if plan and not by:
        P.append("the document has no sequences")
    for ab, ts in by.items():
        if not 3 <= len(ts) <= 5:
            P.append(f"group {ab} has {len(ts)} touches in the document; 3 to 5 required")
        if not ts[-1][1]:
            P.append(f"group {ab} does not end with the close-the-file message")
    _ = blocks
    return P


def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("xlsx")
    a.add_argument("docx")
    a.add_argument("--plan")
    args = a.parse_args()
    for f in (args.xlsx, args.docx):
        if not Path(f).exists():
            print(f"STOP: cannot find {f}")
            sys.exit(2)
    plan = None
    if args.plan:
        try:
            plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            print(f"STOP: the plan file cannot be read ({e})")
            sys.exit(2)
    P = check(args.xlsx, args.docx, plan)
    for p in P:
        print("PROBLEM:", p)
    print(f"{len(P)} problems")
    sys.exit(1 if P else 0)


if __name__ == "__main__":
    main()
