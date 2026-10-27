#!/usr/bin/env python3
"""Read, write and check the Get Paid memory file.

Usage (paths relative to this skill's folder):
  python3 scripts/memory.py read <memory.md> --json-out <inputs.json> [--date YYYY-MM-DD]
        turn a saved memory file back into an inputs file for chase_plan.py; prints what it found,
        and an ASSUMED SENT line for each message saved as drafted but not confirmed
  python3 scripts/memory.py write <results.json> --out <memory.md> [--existing <old memory.md>]
        [--drafted] [--confirmed] [--history "made | choice | verdict"]
        [--learning "rule | evidence | step | status"] [--voice "short notes on how the founder writes"]
        write the memory file: profile, clients, open invoices (paid ones dropped), messages sent;
        keeps the old Learnings and History and appends new rows. --drafted records today's
        send-now messages as drafted, so the next run asks whether they went out; --confirmed marks
        messages saved as drafted on an earlier run as sent, once the founder says they went out
  python3 scripts/memory.py validate <memory.md>
        check the file still has the shape this skill reads

Plain markdown the founder can read and edit. Write only what the founder approved.
Standard library only. No network calls. Exit 2 with a STOP line on any error.
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

SKILL = "revos-get-paid"
PROFILE = [  # label, key
    ("Business", "business"), ("Your name for sign-offs", "founder_name"), ("Your greeting", "greeting"),
    ("Country", "country"), ("Currency", "currency"), ("Your English", "locale"), ("Date order", "date_order"),
    ("How you write numbers", "decimal_style"), ("Days you don't work", "weekend"),
    ("Your holidays (you gave these)", "holidays"), ("Your usual payment terms", "default_terms"),
    ("Your contract sets a late fee or interest", "own_has"), ("Late interest rate (founder supplied)", "own_rate"),
    ("Late fee (founder supplied)", "own_fee"), ("Grace days before the late fee", "own_grace"),
    ("Late payment clause", "own_clause"), ("Payment plan offer", "plan"), ("Smallest amount offered a plan", "min_plan"),
    ("Deposit for new work", "deposit_pct"),
    ("Milestone split", "milestones"), ("Card or account on file", "card_on_file"),
    ("Bank details line in messages", "bank_line"), ("How you write", "voice_notes"),
]
CLIENT_COLS = [("Client", "name"), ("Business", "is_business"), ("How much they matter", "tier"),
               ("Charge late fee", "charge_late_fee"), ("Contact", "contact"), ("Send to", "to"),
               ("Ongoing work", "ongoing_work"), ("Final notice step", "final_action"), ("Terms", "terms"),
               ("Approved in writing", "approval"), ("Approved on", "approval_date"), ("Held until paid", "held_until_paid"),
               ("Days between messages", "gap_days"), ("Days to final notice", "final_after_days")]
INVOICE_COLS = [("Client", "client"), ("Invoice", "number"), ("Amount", "amount"), ("Invoice date", "invoice_date"),
                ("Due date", "due_date"), ("Terms", "terms"), ("Part payments", "payments"), ("Disputed", "disputed"),
                ("Disputed part", "disputed_amount"), ("Total shown on their copy", "total_shown")]
DEFAULT_KEYS = {"weekend": "weekend", "plan": "plan", "deposit_pct": "deposit_pct", "milestones": "milestones",
                "card_on_file": "card_on_file", "bank_line": "bank_line", "default_terms": "default_terms"}
SECTIONS = ["## Profile", "## Clients", "## Open invoices", "## Messages sent", "## Learnings", "## History"]
LEARN_HEAD = "| # | Learning | Evidence | Applies to step | Status | Added |"
HIST_HEAD = "| Date | Made | Choice | Verdict |"
TIER_WORDS = {"valued": "keep at all costs", "normal": "normal", "persistent": "always pays late"}


def stop(msg):
    print(f"STOP: {msg}. Nothing was written.")
    sys.exit(2)


def cell(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, list):
        return ", ".join(str(x) for x in v)
    return str(v).replace("|", "/").replace("\n", " ").strip()


def split_row(line):
    line = line.strip()
    if not line.startswith("|"):
        return None
    return [c.strip() for c in line.strip("|").split("|")]


def tables(text):
    """Map section heading to its table rows (list of dicts keyed by header)."""
    out, current, header = {}, None, None
    for line in text.splitlines():
        if line.startswith("## "):
            current = line.strip()
            out[current] = []
            header = None
            continue
        row = split_row(line)
        if current is None or row is None:
            continue
        if header is None:
            header = row
            continue
        if all(re.fullmatch(r":?-{2,}:?", c) for c in row if c):
            continue
        out[current].append(dict(zip(header, row + [""] * (len(header) - len(row)))))
    return out


def yesno(v):
    s = str(v or "").strip().lower()
    if s in {"yes", "y", "true"}:
        return True
    if s in {"no", "n", "false"}:
        return False
    return None


def tier_key(v):
    s = str(v or "").strip().lower()
    for k, words in TIER_WORDS.items():
        if s in {k, words}:
            return k
    return s or "normal"


def read(path, json_out, today):
    p = Path(path)
    if not p.exists():
        stop(f"there is no memory file at {path}")
    text = p.read_text(encoding="utf-8")
    problems = shape_problems(text)
    if problems:
        stop("the memory file has lost its shape (" + "; ".join(problems) + "); run without it or fix it by hand")
    t = tables(text)
    # Rows the skill defaulted stay defaults: they are said out loud again, never read back as the founder's choice.
    prof = {r.get("Field", ""): r.get("Value", "") for r in t["## Profile"] if r.get("Source", "").strip().lower() != "default"}
    v = {key: prof.get(label, "") for label, key in PROFILE}
    inputs = {"date": today}
    for key in ("business", "founder_name", "greeting", "country", "currency", "locale", "decimal_style", "default_terms", "voice_notes"):
        if v[key]:
            inputs[key] = v[key]
    if v["date_order"] and not v["country"]:
        inputs["date_order"] = v["date_order"]
    if v["weekend"]:
        inputs["weekend"] = [x.strip() for x in v["weekend"].split(",") if x.strip()]
    if v["holidays"]:
        inputs["holidays"] = [x.strip() for x in v["holidays"].split(",") if x.strip()]
    inputs["own_late_terms"] = {"has": bool(yesno(v["own_has"])), "rate": v["own_rate"] or None, "fee": v["own_fee"] or None,
                                "grace_days": v["own_grace"] or None, "clause": v["own_clause"] or None}
    if v["plan"]:
        m = re.match(r"\s*(\d+)\D+(week|fortnight|month)", v["plan"])
        if m:
            inputs["plan"] = {"instalments": int(m.group(1)), "every": m.group(2)}
    if v["min_plan"]:
        inputs.setdefault("plan", {})["min_amount"] = v["min_plan"]
    prev = {}
    if v["deposit_pct"]:
        prev["deposit_pct"] = v["deposit_pct"].rstrip("%")
    if v["milestones"]:
        prev["milestones"] = v["milestones"]
    if v["card_on_file"]:
        prev["card_on_file"] = yesno(v["card_on_file"])
    if prev:
        inputs["prevention"] = prev
    inputs["bank_line"] = yesno(v["bank_line"]) if yesno(v["bank_line"]) is not None else True
    clients, byname = [], {}
    for r in t["## Clients"]:
        c = {}
        for label, key in CLIENT_COLS:
            val = r.get(label, "")
            if key in {"is_business", "charge_late_fee", "ongoing_work"}:
                c[key] = yesno(val)  # "n/a (no contract fee)" reads as unknown, so the default applies
            elif key == "tier":
                c[key] = tier_key(val)
            else:
                c[key] = val or None
        if c["charge_late_fee"] is None:
            c["charge_late_fee"] = True
        if c["is_business"] is None:
            c["is_business"] = True
        c["invoices"], c["stages_sent"] = [], []
        clients.append(c)
        byname[c["name"]] = c
    for r in t["## Open invoices"]:
        name = r.get("Client", "")
        if name not in byname:
            byname[name] = {"name": name, "invoices": [], "stages_sent": []}
            clients.append(byname[name])
        inv = {}
        for label, key in INVOICE_COLS[1:]:
            val = r.get(label, "")
            if key == "payments":
                inv[key] = [{"date": a.strip(), "amount": b.strip()} for a, b in
                            (x.strip().split(" ", 1) if " " in x.strip() else (x, "") for x in val.split(";") if x.strip())]
            elif key == "disputed":
                inv[key] = bool(yesno(val))
            elif key in {"disputed_amount", "total_shown"}:
                inv[key] = val or None
            else:
                inv[key] = val or None
        byname[name]["invoices"].append(inv)
    assumed = []
    for r in t["## Messages sent"]:
        name = r.get("Client", "")
        if name in byname and r.get("Stage", "") != "" and r.get("Date"):
            byname[name]["stages_sent"].append({"stage": r["Stage"], "date": r["Date"]})
            if r.get("Status", "").lower().startswith("draft"):
                what = "the message about the dispute" if str(r["Stage"]).strip() == "0" else f"stage {r['Stage']}"
                assumed.append(f"{name}, {what} drafted on {r['Date']}")
    inputs["clients"] = clients
    Path(json_out).parent.mkdir(parents=True, exist_ok=True)
    Path(json_out).write_text(json.dumps(inputs, indent=2), encoding="utf-8")
    learn = [r for r in t["## Learnings"] if r.get("Status", "").lower() == "active"]
    hist = t["## History"]
    print(f"READ: {len(clients)} clients, {sum(len(c['invoices']) for c in clients)} open invoices, "
          f"{len(learn)} active learnings, last run {hist[-1].get('Date') if hist else 'none'}")
    for a in assumed:
        print(f"ASSUMED SENT: {a}. Confirm with the founder; remove it from stages_sent if it did not go out.")
    for r in learn:
        print(f"ACTIVE LEARNING ({r.get('Applies to step', '')}): {r.get('Learning', '')}")
    print(f"WROTE: {json_out}")


def write(results_path, out, existing, drafted, history, learnings, voice, confirmed=False):
    rp = Path(results_path)
    if not rp.exists():
        stop(f"there is no results file at {results_path}")
    try:
        res = json.loads(rp.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        stop(f"{results_path} is not valid JSON")
    if not isinstance(res, dict) or res.get("skill") != SKILL:
        stop("that is not a results file from chase_plan.py compute")
    raw = res.get("inputs") or {}
    today = res.get("as_of") or date.today().isoformat()
    old, old_learn, old_hist, old_sent = {}, [], [], []
    if existing:
        ep = Path(existing)
        if not ep.exists():
            stop(f"there is no memory file at {existing}")
        t = tables(ep.read_text(encoding="utf-8"))
        old = {r.get("Field", ""): r for r in t.get("## Profile", [])}
        old_learn = t.get("## Learnings", [])
        old_hist = t.get("## History", [])
        old_sent = t.get("## Messages sent", [])
    own = raw.get("own_late_terms") or {}
    if not isinstance(own, dict):
        own = {"has": True, "clause": own}
    pv = res.get("prevention") or {}
    plan = res.get("plan") or {}
    vals = {"business": raw.get("business"), "founder_name": raw.get("founder_name"), "greeting": res.get("greeting") or None,
            "country": res.get("country") or None, "currency": res.get("currency"),
            "locale": res.get("locale"), "date_order": res.get("date_order"), "decimal_style": res.get("decimal_style") or None,
            "weekend": res.get("weekend"),
            "holidays": raw.get("holidays") or None, "default_terms": res.get("default_terms"),
            "own_has": bool(res["own_terms"]["has"]), "own_rate": own.get("rate"), "own_fee": own.get("fee"),
            "own_grace": own.get("grace_days"), "own_clause": own.get("clause"),
            "plan": f"{plan.get('instalments')} {'installments' if str(res.get('locale', '')).lower() in {'en-us', 'en-ph'} else 'instalments'}, every {plan.get('every')}" if plan else None,
            "min_plan": plan.get("min_amount"),
            "deposit_pct": (pv.get("deposit_pct") + "%") if pv.get("deposit_pct") else None,
            "milestones": "/".join(pv.get("milestones") or []) or None, "card_on_file": pv.get("card_on_file"),
            "bank_line": res.get("bank_line"),
            "voice_notes": voice if voice is not None else (old.get("How you write", {}).get("Value") or raw.get("voice_notes"))}
    lines = ["# Get Paid memory", "",
             f"Skill: {SKILL} | Memory version: 1 | Updated: {today}", "",
             "Keep this file. Attach it next time (or leave it in your merigrove-memory folder, or your Claude Project) and the skill picks up where you left off. You can edit it by hand.", "",
             "## Profile", "", "| Field | Value | Source | Updated |", "|---|---|---|---|"]
    defaulted = set(res.get("defaults_used") or [])
    for label, key in PROFILE:
        v = cell(vals.get(key))
        if v == "":
            continue
        prev = old.get(label)
        if key in defaulted:
            src, upd = "default", (prev.get("Updated", today) if prev and prev.get("Value", "") == v else today)
        elif prev and prev.get("Value", "") == v and prev.get("Source", "") != "default":
            src, upd = prev.get("Source", "founder said"), prev.get("Updated", today)
        else:
            if "founder supplied" in label or key in {"own_clause", "holidays"}:
                src = "founder supplied"
            elif key == "date_order" and not raw.get("date_order"):
                src = "from your country" if res.get("country") else "default"
            elif key == "decimal_style" and not raw.get("decimal_style"):
                src = "from your figures"
            elif key == "voice_notes":
                src = "pasted email"
            else:
                src = "founder said"
            upd = today
        lines.append(f"| {label} | {v} | {src} | {upd} |")
    lines += ["", "## Clients", "", "| " + " | ".join(c for c, _ in CLIENT_COLS) + " |", "|" + "---|" * len(CLIENT_COLS)]
    raw_clients = {c.get("name"): c for c in (raw.get("clients") or []) if isinstance(c, dict)}
    for cl in res["clients"]:
        rc = raw_clients.get(cl["name"], {})
        row = {"name": cl["name"], "is_business": cl["is_business"], "tier": TIER_WORDS.get(cl["tier"], cl["tier"]),
               "charge_late_fee": cl["charge_late_fee"], "contact": cl.get("contact"), "to": cl.get("to"),
               "ongoing_work": cl.get("ongoing_work"), "final_action": cl.get("final_action"), "terms": rc.get("terms"),
               "approval": cl.get("approval") or rc.get("approval"), "approval_date": cl.get("approval_date") or rc.get("approval_date"),
               "held_until_paid": cl.get("held_until_paid") or rc.get("held_until_paid"),
               "gap_days": rc.get("gap_days") or raw.get("gap_days"), "final_after_days": rc.get("final_after_days") or raw.get("final_after_days")}
        if not (res.get("own_terms") or {}).get("has"):
            row["charge_late_fee"] = "n/a (no contract fee)"
        lines.append("| " + " | ".join(cell(row[k]) for _, k in CLIENT_COLS) + " |")
    lines += ["", "## Open invoices", "", "| " + " | ".join(c for c, _ in INVOICE_COLS) + " |", "|" + "---|" * len(INVOICE_COLS)]
    raw_inv = {}
    for c in raw_clients.values():
        for i in c.get("invoices") or []:
            if isinstance(i, dict):
                raw_inv[(c.get("name"), str(i.get("number") or i.get("invoice") or "").strip())] = i
    for r in res["invoices"]:
        if r["status"] in {"paid", "paid_late"}:
            continue
        ri = raw_inv.get((r["client"], r["number"]), {})
        pays = "; ".join(f"{d} {a}" for d, a in r.get("payments", []))
        row = {"client": r["client"], "number": r["number"], "amount": r["amount"] or cell(ri.get("amount")),
               "invoice_date": r.get("invoice_date") or cell(ri.get("invoice_date")),
               "due_date": r.get("due_date") if (ri.get("due_date") or ri.get("due")) else "",
               "terms": ri.get("terms"), "payments": pays, "disputed": r.get("disputed") or r.get("part_disputed"),
               "disputed_amount": r.get("disputed_part") if r.get("part_disputed") else "",
               "total_shown": r.get("total_shown") or ""}
        lines.append("| " + " | ".join(cell(row[k]) for _, k in INVOICE_COLS) + " |")
    lines += ["", "## Messages sent", "", "Stage 0 is a message about a dispute; 1 reminder, 2 firm reminder, 3 call or plan offer, 4 final notice.", "",
              "| Client | Stage | Date | Status |", "|---|---|---|---|"]
    seen = set()
    open_clients = {r["client"] for r in res["invoices"] if r["status"] not in {"paid", "paid_late"}}
    for cl in res["clients"]:
        if cl["name"] not in open_clients:
            continue
        for st, d in cl.get("stages_sent", []):
            seen.add((cl["name"], str(st), d))
            status = next((r.get("Status", "sent") for r in old_sent if r.get("Client") == cl["name"] and r.get("Stage") == str(st) and r.get("Date") == d), "sent")
            if confirmed and status.lower().startswith("draft"):
                status = "sent"
            lines.append(f"| {cell(cl['name'])} | {st} | {d} | {cell(status) or 'sent'} |")
        for d in cl.get("dispute_sent", []):
            seen.add((cl["name"], "0", d))
            status = next((r.get("Status", "sent") for r in old_sent if r.get("Client") == cl["name"] and r.get("Stage") == "0" and r.get("Date") == d), "sent")
            if confirmed and status.lower().startswith("draft"):
                status = "sent"
            lines.append(f"| {cell(cl['name'])} | 0 | {d} | {cell(status) or 'sent'} |")
        if drafted and cl.get("now"):
            key = (cl["name"], str(cl["now"]["stage"]), cl["now"]["send"])
            if key not in seen:
                lines.append(f"| {cell(cl['name'])} | {cl['now']['stage']} | {cl['now']['send']} | drafted |")
        if drafted and cl.get("disputed") and not cl.get("dispute_sent"):
            lines.append(f"| {cell(cl['name'])} | 0 | {today} | drafted |")
    lines += ["", "## Learnings", "", LEARN_HEAD, "|---|---|---|---|---|---|"]
    n = 0
    for r in old_learn:
        if not r.get("Learning"):
            continue
        n += 1
        lines.append(f"| {n} | {cell(r.get('Learning'))} | {cell(r.get('Evidence'))} | {cell(r.get('Applies to step'))} | {cell(r.get('Status'))} | {cell(r.get('Added'))} |")
    for item in learnings or []:
        parts = [x.strip() for x in item.split("|")]
        if len(parts) < 3:
            stop("--learning needs 'rule | evidence | step | status'")
        status = parts[3] if len(parts) > 3 and parts[3] in {"watch", "active", "retired"} else "watch"
        n += 1
        lines.append(f"| {n} | {cell(parts[0])} | {cell(parts[1])} | {cell(parts[2])} | {status} | {today} |")
    if sum(1 for x in lines if x.startswith("| ") and "| active |" in x) > 25:
        stop("more than 25 active learnings; condense them before adding another")
    lines += ["", "Status: watch (seen once), active (approved or repeated), retired (kept for the record, no longer applied).",
              "", "## History", "", HIST_HEAD, "|---|---|---|---|"]
    for r in old_hist:
        if r.get("Date"):
            lines.append(f"| {cell(r.get('Date'))} | {cell(r.get('Made'))} | {cell(r.get('Choice'))} | {cell(r.get('Verdict'))} |")
    if history:
        parts = [x.strip() for x in history.split("|")] + ["", "", ""]
        lines.append(f"| {today} | {cell(parts[0])} | {cell(parts[1])} | {cell(parts[2])} |")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"WROTE: {out}")


def shape_problems(text):
    probs = []
    if SKILL not in text:
        probs.append("it does not name this skill")
    for s in SECTIONS:
        if s not in text:
            probs.append(f"missing '{s}'")
    t = tables(text)
    for r in t.get("## Profile", []):
        if "Field" not in r or "Value" not in r:
            probs.append("Profile table has no Field and Value columns")
            break
    for r in t.get("## Clients", []):
        if "Client" not in r:
            probs.append("Clients table has no Client column")
            break
    for r in t.get("## Learnings", []):
        if r.get("Status") and r["Status"].strip("~ ").lower() not in {"watch", "active", "retired"}:
            probs.append(f"learning status '{r['Status']}' should be watch, active or retired")
    return probs


def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = a.add_subparsers(dest="cmd")
    r = sub.add_parser("read")
    r.add_argument("memory")
    r.add_argument("--json-out", required=True)
    r.add_argument("--date", default=date.today().isoformat())
    w = sub.add_parser("write")
    w.add_argument("results")
    w.add_argument("--out", required=True)
    w.add_argument("--existing")
    w.add_argument("--drafted", action="store_true")
    w.add_argument("--confirmed", action="store_true")
    w.add_argument("--history")
    w.add_argument("--learning", action="append")
    w.add_argument("--voice")
    v = sub.add_parser("validate")
    v.add_argument("memory")
    args = a.parse_args()
    if args.cmd == "read":
        read(args.memory, args.json_out, args.date)
    elif args.cmd == "write":
        write(args.results, args.out, args.existing, args.drafted, args.history, args.learning, args.voice, args.confirmed)
    elif args.cmd == "validate":
        p = Path(args.memory)
        if not p.exists():
            stop(f"there is no memory file at {args.memory}")
        probs = shape_problems(p.read_text(encoding="utf-8"))
        for x in probs:
            print("PROBLEM:", x)
        print(f"{len(probs)} problems")
        sys.exit(1 if probs else 0)
    else:
        a.print_help()
        sys.exit(2)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        stop(f"something unexpected went wrong ({type(e).__name__}: {e})")
