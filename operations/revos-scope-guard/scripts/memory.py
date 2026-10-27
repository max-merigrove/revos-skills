#!/usr/bin/env python3
"""Read, write and check the Scope Guard memory file.

Usage:
  python3 scripts/memory.py read <memory.md> [--client "Name"] [--json-out prefill.json]
        turn a saved memory file into a starter kit.json. With --client, the kit is prefilled with
        that client's offer, fee, planned hours, not-included list, relationship and logged requests.
  python3 scripts/memory.py write <results.json> --out <memory.md> [--existing <old memory.md>]
        [--voice "greeting Hi Sam!, signs off Priya x, short sentences"] [--history "made | reply chosen | verdict"]
        [--learning "rule | evidence | step | status"] [--retire N]
        write the memory file from a build's results; keeps the other clients and offers, the Learnings
        and the History, and appends the new rows. Write only what the founder approved.
  python3 scripts/memory.py validate <memory.md>
        check the file still has the shape this skill reads

The memory file is plain markdown the founder can read and edit by hand. Standard library only. No network.
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import parse as P  # noqa: E402

SKILL = "revos-scope-guard"
PROFILE = [("Business", "business"), ("Founder", "founder"), ("Country", "country"), ("Currency", "currency"),
           ("Number style", "number_style"), ("Date order", "date_order"),
           ("English", "english"), ("Price wording", "price_wording"), ("Hours in a working day", "hpd"),
           ("Extras policy", "policy"), ("Goodwill allowance, hours", "allowance"),
           ("Rate for extra work", "rate_changes"), ("Voice", "voice")]
OFFER_HEAD = ["Offer", "Billing", "Fee", "Planned hours", "Rounds of changes", "Also included", "Not included", "Assumptions"]
CLIENT_HEAD = ["Client", "Offer", "Relationship", "Count starts", "Outcome", "Rate at last run", "Last run"]
LEDGER_HEAD = ["Client", "Date", "Request", "In or out", "Hours", "Status"]
DELIV_HEAD = ["Offer", "Deliverable", "How much", "Hours", "Who does it", "Done when"]
DEP_HEAD = ["Client", "What they provide", "By when", "Received"]
DEP_HEAD_V2 = ["Client", "What they provide", "By when"]   # memory version 2: read, and rewritten with Received
LEARN_HEAD = ["#", "Learning", "Evidence", "Applies to step", "Status", "Added"]
HIST_HEAD = ["Date", "Made", "Reply chosen", "Verdict"]
STATUSES = {"watch", "active", "retired"}
STEPS = {"intake", "diagnose", "make", "check", "deliver", "learn"}


SEP = " · "  # separates list items inside one table cell


def cell(v):
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    if isinstance(v, float):
        v = round(v, 2)
    return str(v).replace("|", "/").replace("\n", " ").strip()


def table(text, heading):
    m = re.search(rf"^## {re.escape(heading)}\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not m:
        return None, []
    lines = [ln.strip() for ln in m.group(1).splitlines() if ln.strip().startswith("|")]
    if not lines:
        return None, []
    head = [c.strip() for c in lines[0].strip("|").split("|")]
    rows = []
    for ln in lines[2:]:
        cells = [c.strip() for c in ln.strip("|").split("|")]
        rows.append(dict(zip(head, cells + [""] * (len(head) - len(cells)))))
    return head, rows


def md_table(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for r in rows:
        out.append("| " + " | ".join(cell(r.get(h, "")) for h in head) + " |")
    return out


MISSING = ("", "not yet", "no", "none", "none yet", "missing", "not received", "still missing", "not arrived", "outstanding")


def carry_over(due_text, received_text, today):
    """What the client still owes carries over: anything recurring, anything not yet received (however late, or with
    no date at all), and anything still ahead. Only a one-off item that has arrived stays behind."""
    if P.recurring_day(due_text):
        return True
    if str(received_text or "").strip().lower() in MISSING:
        return True
    d, _n = P.date_(due_text, today, "nearest")
    return d is not None and d >= today


def num(v):
    """A figure memory.py wrote (always with a dot decimal), back as a number so no reader can misread it."""
    try:
        return float(v) if re.fullmatch(r"-?\d+(\.\d+)?", str(v or "").strip()) else (v or None)
    except ValueError:
        return v or None


def cmd_read(a):
    today = P.date_(a.today, date.today())[0] if a.today else date.today()
    text = Path(a.memory).read_text(encoding="utf-8")
    probs = validate(text)
    if probs:
        for p in probs:
            print("PROBLEM:", p)
        print("STOP: the memory file has lost its shape; run as a first run and offer a fresh memory file at the end.")
        sys.exit(2)
    _h, prof = table(text, "Profile")
    _h, offers = table(text, "Offers")
    _h, clients = table(text, "Clients")
    _h, ledger = table(text, "Ledger")
    _h, deliv = table(text, "Deliverables")
    _h, deps = table(text, "Client dependencies")
    _h, learn = table(text, "Learnings")
    _h, hist = table(text, "History")
    upd = re.search(r"Updated:\s*(\d{4}-\d{2}-\d{2})", text)
    p = {r.get("Field", ""): r.get("Value", "") for r in prof}
    kit = {"date": None, "business": p.get("Business") or None, "founder": p.get("Founder") or None,
           "country": p.get("Country") or None, "currency": p.get("Currency") or None,
           "number_style": p.get("Number style") or None, "date_order": p.get("Date order") or None,
           "english": p.get("English") or None, "price_wording": p.get("Price wording") or None,
           "extras_policy": p.get("Extras policy") or None, "allowance_hours": num(p.get("Goodwill allowance, hours")),
           "rate_for_changes": num(p.get("Rate for extra work")), "hours_per_day": num(p.get("Hours in a working day")),
           "sources": {}}
    # A version 1.0 memory recorded "VAT registered: yes" because the founder wrote their fee "+ VAT".
    # Carry that over as their own price wording; nothing is worked out from it.
    if not kit["price_wording"] and str(p.get("VAT registered", "")).strip().lower() == "yes":
        kit["price_wording"] = "plus VAT"
        kit["sources"]["price_wording"] = "carried over from 'VAT registered: yes' in an earlier memory file"
    for k in ("price_wording", "date_order", "english", "hours_per_day", "extras_policy", "allowance_hours", "rate_for_changes",
              "country", "number_style"):
        if kit[k] and k not in kit["sources"]:
            kit["sources"][k] = f"saved memory, {upd.group(1) if upd else 'earlier run'}"
    saved = {"memory_updated": upd.group(1) if upd else None, "voice": p.get("Voice") or "",
             "offers": [r.get("Offer") for r in offers], "clients": [r.get("Client") for r in clients],
             "learnings_active": [f"{r.get('Learning')} (step: {r.get('Applies to step')})" for r in learn if r.get("Status", "").lower() == "active"],
             "learnings_watch": [r.get("Learning") for r in learn if r.get("Status", "").lower() == "watch"]}
    if a.client:
        cl = next((r for r in clients if r.get("Client", "").lower() == a.client.lower()), None)
        if not cl:
            print(f"NOTE: no saved client called '{a.client}'. Saved clients: {', '.join(saved['clients']) or 'none'}")
        else:
            off = next((r for r in offers if r.get("Offer", "").lower() == cl.get("Offer", "").lower()), {})
            kit.update({"client": cl.get("Client"), "offer": cl.get("Offer") or None, "relationship": cl.get("Relationship") or None,
                        "period_start": cl.get("Count starts") or None, "billing": off.get("Billing") or None,
                        "fee": num(off.get("Fee")), "planned_hours": num(off.get("Planned hours")),
                        "revision_rounds": off.get("Rounds of changes") or None,
                        "scope": {"outcome": cl.get("Outcome") or None,
                                  "included": [x.strip() for x in (off.get("Also included") or "").split(" · ") if x.strip()],
                                  "not_included": [x.strip() for x in (off.get("Not included") or "").split(" · ") if x.strip()],
                                  "assumptions": [x.strip() for x in (off.get("Assumptions") or "").split(" · ") if x.strip()],
                                  "deliverables": [{"name": d.get("Deliverable"), "quantity": d.get("How much"),
                                                    "hours": num(d.get("Hours")), "who": d.get("Who does it"),
                                                    "acceptance": d.get("Done when")}
                                                   for d in deliv if d.get("Offer", "").lower() == cl.get("Offer", "").lower()],
                                  "dependencies": [{"what": d.get("What they provide"), "owner": cl.get("Client"), "due": d.get("By when") or None,
                                                    "received": d.get("Received") or ""}
                                                   for d in deps if d.get("Client", "").lower() == a.client.lower()
                                                   and carry_over(d.get("By when"), d.get("Received"), today)]},
                        "requests": [],
                        "previous": {"date": cl.get("Last run") or None, "effective_rate": cl.get("Rate at last run") or None},
                        # only a History row that records it: a last run alone does not mean the founder sent the note
                        "reset_already_sent": any(a.client.lower() in (h.get("Made") or "").lower() and "reset note sent" in
                                                  " ".join(h.values()).lower() for h in hist)})
            for k in ("fee", "planned_hours", "relationship"):
                if kit.get(k):
                    kit["sources"][k] = f"saved memory, {saved['memory_updated']}"
            for i, r in enumerate([r for r in ledger if r.get("Client", "").lower() == a.client.lower()], 1):
                kit["requests"].append({"id": i, "what": r.get("Request"), "date": r.get("Date"), "hours": num(r.get("Hours")),
                                        "class": (r.get("In or out") or "").lower() or None,
                                        "status": {"done, not billed": "done", "done, in scope": "done", "done, billed": "billed",
                                                   "asked": "asked", "swapped": "swapped",
                                                   "declined": "declined"}.get((r.get("Status") or "").lower(), r.get("Status"))})
    kit["_saved"] = saved
    out = json.dumps(kit, indent=2)
    if a.json_out:
        Path(a.json_out).write_text(out, encoding="utf-8")
        print(f"WROTE: {a.json_out} ({len(saved['offers'])} offers, {len(saved['clients'])} clients, "
              f"{len(saved['learnings_active'])} active learnings)")
        for x in saved["learnings_active"]:
            print(f"ACTIVE LEARNING: {x}")
    else:
        print(out)


def cmd_write(a):
    res = json.loads(Path(a.results).read_text(encoding="utf-8"))
    if res.get("scope_guard_results") != 1:
        print("STOP: that file is not a Scope Guard results file (from `scope_kit.py build`). Nothing was written.")
        sys.exit(2)
    m, today = res["model"], str(res.get("date") or date.today().isoformat())
    old = Path(a.existing).read_text(encoding="utf-8") if a.existing and Path(a.existing).exists() else ""
    _h, oprof = table(old, "Profile")
    _h, ooffers = table(old, "Offers")
    _h, oclients = table(old, "Clients")
    _h, oledger = table(old, "Ledger")
    _h, odeliv = table(old, "Deliverables")
    _h, odeps = table(old, "Client dependencies")
    _h, olearn = table(old, "Learnings")
    _h, ohist = table(old, "History")
    prof = {r.get("Field"): r for r in oprof}
    srcs = m.get("sources") or {}

    def put(label, value, source):
        if value in (None, "", 0) and label != "Goodwill allowance, hours":
            return
        prev = prof.get(label)
        if prev and str(prev.get("Value")) == cell(value):
            return  # unchanged: keep its source and date
        prof[label] = {"Field": label, "Value": cell(value), "Source": source, "Updated": today}
    put("Business", m.get("business"), "founder said")
    put("Founder", m.get("founder"), "founder said")
    put("Country", m.get("country"), srcs.get("country", "founder said"))
    put("Currency", (m.get("sym") or "").strip() or m.get("currency"), "as the founder writes it")
    put("Number style", m.get("number_style"), "from the figures the founder typed")
    if m.get("date_order"):
        put("Date order", "month first" if m["date_order"] == "mdy" else "day first", srcs.get("date_order", "from the dates the founder wrote"))
    if m.get("english") in ("american", "british"):
        put("English", m["english"], srcs.get("english", "from a message the founder pasted"))
    put("Price wording", m.get("price_wording"), srcs.get("price_wording", "how the founder writes their own fee"))
    prof.pop("VAT registered", None)  # version 1.0 field, replaced by the founder's own price wording
    put("Extras policy", m.get("policy"), srcs.get("extras_policy", "founder chose"))
    if m.get("policy") == "allowance":
        put("Goodwill allowance, hours", m.get("allowance"), srcs.get("allowance_hours", "founder chose"))
    if str(m.get("rate_changes_src", "")).startswith("your own"):
        put("Rate for extra work", m.get("rate_changes"), "founder said")
    if m.get("hpd") and m.get("hpd_src") == "founder said":
        put("Hours in a working day", m["hpd"], srcs.get("hours_per_day", "founder said"))
    if a.voice:
        put("Voice", a.voice, "from a message the founder pasted")
    offers = {r.get("Offer", "").lower(): r for r in ooffers}
    oname = m.get("offer") or "Main offer"
    fee = m.get("fee")
    offers[oname.lower()] = {"Offer": oname, "Billing": m.get("billing"),
                             "Fee": f"{fee:g}" if isinstance(fee, (int, float)) else "",
                             "Planned hours": f"{m['planned']:g}" if isinstance(m.get("planned"), (int, float)) else "",
                             "Rounds of changes": m.get("revisions"),
                             "Also included": " · ".join(m.get("included") or []),
                             "Not included": " · ".join(m.get("not_included") or []),
                             "Assumptions": " · ".join(m.get("assumptions") or [])}
    clients = {r.get("Client", "").lower(): r for r in oclients}
    clients[m["client"].lower()] = {"Client": m["client"], "Offer": oname, "Relationship": m.get("relationship"),
                                    "Count starts": m.get("period_start") or "", "Outcome": m.get("outcome") or "",
                                    "Rate at last run": (f"{res['results']['effective_rate']:.2f}" if isinstance(res["results"].get("effective_rate"), (int, float)) else ""),
                                    "Last run": today}
    deliv = [r for r in odeliv if r.get("Offer", "").lower() != oname.lower()]
    for d in m.get("deliverables") or []:
        deliv.append({"Offer": oname, "Deliverable": d.get("name"), "How much": d.get("quantity"),
                      "Hours": "" if d.get("hours") is None else f"{d['hours']:g}", "Who does it": d.get("who"),
                      "Done when": d.get("acceptance")})
    deps = [r for r in odeps if r.get("Client", "").lower() != m["client"].lower()]
    for d in m.get("dependencies") or []:
        got = d.get("received") or ("" if d.get("missing") else d.get("received_text") or "")
        if not d.get("recurring") and got and (not d.get("due") or str(d.get("due")) < today):
            continue  # a one-off item that has arrived belongs to that run; anything still owed carries over
        deps.append({"Client": m["client"], "What they provide": d.get("what"), "By when": d.get("due_text"),
                     # a recurring item starts each month afresh; a blank means not yet due, so the next run asks
                     "Received": "" if d.get("recurring") else (got or ("not yet" if d.get("missing") else ""))})
    ledger = [r for r in oledger if r.get("Client", "").lower() != m["client"].lower()]
    for r in m.get("requests", []):
        when = r.get("date") or r.get("date_text") or ""
        if r.get("month_only") and r.get("date"):
            when = P.month_text(date.fromisoformat(r["date"]))  # 'Sep 2026', never a made-up 1st
        status = r.get("status")
        if r.get("class") == "In" and str(status).startswith("Done"):
            status = "Done, in scope"  # in-scope work done is not an unbilled extra
        hrs = "" if r.get("hours") is None else f"{r['hours']:g}"
        if r.get("hours_lo") is not None and r.get("hours_hi") is not None:
            hrs = f"{r['hours_lo']:g} to {r['hours_hi']:g}"  # a range stays a range, so the next run quotes both ends
        ledger.append({"Client": m["client"], "Date": when, "Request": r.get("what"),
                       "In or out": r.get("class"), "Hours": hrs,
                       "Status": status})
    learn = list(olearn)
    for idx in a.retire or []:
        for r in learn:
            if r.get("#") == str(idx):
                r["Status"] = "retired"
                r["Learning"] = f"~~{r['Learning'].strip('~')}~~"
    for x in a.learning or []:
        parts = [p.strip() for p in x.split("|")] + ["", "", "", ""]
        learn.append({"Learning": parts[0], "Evidence": parts[1], "Applies to step": parts[2] or "Make",
                      "Status": parts[3] or "watch", "Added": today})
    for i, r in enumerate(learn, 1):
        r["#"] = str(i)
    hist = list(ohist)
    if a.history:
        parts = [p.strip() for p in a.history.split("|")] + ["", "", ""]
        made = parts[0] + ("; reset note sent" if a.reset_sent else "")
        hist.append({"Date": today, "Made": made, "Reply chosen": parts[1], "Verdict": parts[2]})
    elif a.reset_sent:
        hist.append({"Date": today, "Made": f"{m['client']}; reset note sent", "Reply chosen": "", "Verdict": ""})
    L = ["# Scope Guard memory", "", f"Skill: {SKILL} | Memory version: 3 | Updated: {today}", "",
         "Keep this file. Attach it next time (or leave it in your merigrove-memory folder, or your Claude Project) and "
         "Scope Guard picks up where you left off. You can edit it by hand.", "", "## Profile", ""]
    L += md_table(["Field", "Value", "Source", "Updated"], [prof[k] for k, _ in PROFILE if k in prof] +
                  [v for k, v in prof.items() if k not in dict(PROFILE)])
    L += ["", "## Offers", ""] + md_table(OFFER_HEAD, offers.values())
    L += ["", "## Deliverables", ""] + md_table(DELIV_HEAD, deliv)
    L += ["", "## Clients", ""] + md_table(CLIENT_HEAD, clients.values())
    L += ["", "## Client dependencies", ""] + md_table(DEP_HEAD, deps)
    L += ["", "## Ledger", ""] + md_table(LEDGER_HEAD, ledger)
    L += ["", "## Learnings", ""] + md_table(LEARN_HEAD, learn)
    L += ["", "Status: watch (seen once), active (approved or repeated), retired (kept for the record, no longer applied).",
          "", "## History", ""] + md_table(HIST_HEAD, hist)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text("\n".join(L) + "\n", encoding="utf-8")
    probs = validate(Path(a.out).read_text(encoding="utf-8"))
    for p in probs:
        print("PROBLEM:", p)
    print(f"WROTE: {a.out} ({len(offers)} offers, {len(clients)} clients, {len(ledger)} ledger rows, "
          f"{len(learn)} learnings, {len(hist)} history rows)")
    sys.exit(1 if probs else 0)


def validate(text):
    p = []
    if not re.search(rf"Skill:\s*{SKILL}\b", text):
        p.append(f"header line 'Skill: {SKILL}' missing")
    if not re.search(r"Updated:\s*\d{4}-\d{2}-\d{2}", text):
        p.append("header has no Updated: YYYY-MM-DD date")
    for h, head in (("Profile", ["Field", "Value", "Source", "Updated"]), ("Offers", OFFER_HEAD), ("Clients", CLIENT_HEAD),
                    ("Ledger", LEDGER_HEAD), ("Deliverables", DELIV_HEAD), ("Client dependencies", DEP_HEAD), ("Learnings", LEARN_HEAD), ("History", HIST_HEAD)):
        got, _rows = table(text, h)
        if got is None and not re.search(rf"^## {h}\s*$", text, re.M):
            p.append(f"section '## {h}' missing")
        elif got is not None and got != head and not (h == "Client dependencies" and got == DEP_HEAD_V2):
            p.append(f"{h} header changed; expected: | {' | '.join(head)} |")
    _h, learn = table(text, "Learnings")
    active = 0
    for r in learn:
        st = r.get("Status", "").strip().lower()
        if st not in STATUSES:
            p.append(f"learning {r.get('#')}: status '{r.get('Status')}' is not watch, active or retired")
        active += st == "active"
        if r.get("Applies to step", "").strip().lower() not in STEPS:
            p.append(f"learning {r.get('#')}: step '{r.get('Applies to step')}' is not one of {sorted(STEPS)}")
    if active > 25:
        p.append(f"{active} active learnings; condense to 25 or fewer")
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
    r.add_argument("--client")
    r.add_argument("--json-out")
    r.add_argument("--today")
    w = sub.add_parser("write")
    w.add_argument("results")
    w.add_argument("--out", required=True)
    w.add_argument("--existing")
    w.add_argument("--voice")
    w.add_argument("--history")
    w.add_argument("--learning", action="append")
    w.add_argument("--retire", action="append", type=int)
    w.add_argument("--reset-sent", action="store_true",
                   help="the founder says they sent the reset note; recorded in History so the next run does not write another")
    v = sub.add_parser("validate")
    v.add_argument("memory")
    a = ap.parse_args()
    for attr in ("memory", "results"):
        path = getattr(a, attr, None)
        if path and not Path(path).exists():
            print(f"STOP: there is no file at {path}. Nothing was changed.")
            sys.exit(2)
    handler = {"read": cmd_read, "write": cmd_write, "validate": cmd_validate}.get(a.cmd)
    if not handler:
        ap.print_help()
        sys.exit(2)
    handler(a)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print(f"STOP: the memory file could not be handled ({type(e).__name__}: {e}). Nothing was changed.")
        sys.exit(2)
