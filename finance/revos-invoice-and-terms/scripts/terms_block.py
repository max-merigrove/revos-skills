#!/usr/bin/env python3
"""Payment terms wording for proposals and contracts, in three lengths, from the founder's own schedule.

Usage (paths relative to this skill's folder):
  python3 scripts/terms_block.py <plan.json> --inputs <inputs.json> [--text-out <terms.md>] [--out <output folder>]
Prints the wording for chat: two lines, a paragraph and, only where the founder supplied a late fee clause, a
paragraph with it. With --out (only when the founder asks for a page) it also writes "Payment terms <Business>.docx":
the schedule and the versions, clean and ready to paste, with no notes to the founder on it.
Uses only what the founder gave: the stage shares and triggers, the payment terms, tax as supplied (only taxes with
a rate above 0 are named) and a late fee clause only where they supplied one.
CHAT: lines are for the chat reply, never for the page (what to agree, what is still missing, who to check with).
Exit 0 done, 1 written with [NEED] gaps, 2 STOP. Standard library only. No network calls.
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402
import docx_lite as DX  # noqa: E402
import invoice_calc as IC  # noqa: E402

LATE_NEED = "[NEED: your late fee, from your lawyer]"


def join(items, us=False):
    items = [i for i in items if i]
    if len(items) <= 1:
        return "".join(items)
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + ("," if us else "") + f" and {items[-1]}"


def due_phrase(terms):
    t = (terms or {}).get("type") or ""
    d = str((terms or {}).get("days") or "").strip()
    return {
        "days": f"Each invoice is due within {d} days of its date." if d else "",
        "eom_plus": f"Each invoice is due {d} days after the end of the month it is dated in." if d else "",
        "end_next_month": "Each invoice is due by the end of the month after the month it is dated in.",
        "next_month_day": f"Each invoice is due on day {d} of the month after it is dated." if d else "",
        "on_receipt": "Each invoice is due on receipt.",
        "fixed": "Each invoice is due by the date shown on it.",
        "in_advance": "Each invoice is due before the work it covers starts.",
    }.get(t, "")


def stages_of(plan, inputs):
    bp = plan.get("billing_plan") or {}
    out = []
    raw = (inputs.get("billing_plan") or {}).get("stages") or []
    for i, s in enumerate(bp.get("stages") or []):
        share = s.get("share") or ""
        if share in ("", "balance") and i < len(raw) and raw[i].get("amount"):
            share = str(raw[i]["amount"])
        if share == "balance" or not share:
            share = "the balance"
        elif re.fullmatch(r"\d+(?:[.,]\d+)?", str(share)):
            share = f"{share}%"
        out.append({"label": s.get("label") or f"Stage {i + 1}", "share": share, "trigger": (s.get("trigger") or "").strip()})
    return out


def build(plan, inputs):
    us = str(plan.get("english") or inputs.get("english") or "").lower() in ("en-us", "en-ph")
    stages = stages_of(plan, inputs)
    terms = inputs.get("terms") or {k: v for k, v in (plan.get("terms") or {}).items() if k in ("type", "days")}
    due = due_phrase(terms)
    pay = inputs.get("payment") or {}
    fields = [f for f in (pay.get("fields") or []) if f and f[1]]
    tax = inputs.get("tax") or {}
    needs = []
    if not stages:
        parts_short = "Payment in full on one invoice."
        parts_long = "The fee is invoiced in full."
    else:
        bits = [f"{s['share']} {s['trigger']}".strip() for s in stages]
        parts_short = f"Payment: {join(bits, us)}."
        word = {2: "two", 3: "three", 4: "four", 5: "five"}.get(len(stages), str(len(stages)))
        parts_long = f"The fee is invoiced in {word} parts: {join(bits, us)}." if len(stages) > 1 else f"The fee is invoiced as {bits[0]}."
    if not due:
        needs.append("[NEED: when each invoice is due, e.g. within 14 days of its date]")
        due = "Each invoice is due [NEED: within how many days of its date]."
    how = ""
    if fields:
        how = "Payment by bank transfer to the account shown on each invoice, quoting the invoice number."
        if pay.get("link") and not any("iban" in f[0].lower() or "account" in f[0].lower() for f in fields):
            how = "Payment by the link on each invoice, quoting the invoice number."
    elif pay.get("link"):
        how = "Payment by the link on each invoice, quoting the invoice number."
    else:
        how = "Please quote the invoice number when you pay."
    tax_line = ""
    if tax.get("charged") and tax.get("categories"):
        labels = []
        for c in tax["categories"]:
            lab = IC.mid_sentence(c.get("label"))  # "Sales tax" reads as "sales tax" mid-sentence; VAT and GST stay
            if lab and positive_rate(c.get("rate")) and lab not in labels:
                labels.append(lab)
        if labels:
            tax_line = f"Prices are before {join(labels, us)}, which is added to each invoice as shown."
    short = f"{parts_short} {due}".strip()
    para = " ".join(x for x in [parts_long, due, how, tax_line] if x)
    lf = inputs.get("late_fee") or {}
    path = (lf.get("path") or "none").lower()
    late = None
    chat = ["Agree these terms before the work starts and attach them to the proposal or contract; each invoice then repeats them."]
    if path == "agreed" and lf.get("clause"):
        late = f"{para} {str(lf['clause']).strip()}"
    elif path == "new" and lf.get("clause"):
        clause = str(lf["clause"]).strip()
        late = f"{para} {clause if clause.endswith('.') else clause + '.'}"
        chat.append(f"The late fee version uses your own wording (\"{clause}\"), for contracts from now on. It stays off invoices "
                    "for work the client agreed before it existed. Before it goes into a contract, check with your lawyer that you "
                    "can charge it where you and your clients are.")
    elif path == "new" or (path == "agreed" and not lf.get("clause")):
        needs.append(LATE_NEED)
        chat.append("Late fee: none is written in. When your lawyer gives you the clause (the figure, and whether you can "
                    "charge it where you and your client are), I'll add a third version with it.")
    deposit = any(re.search(r"(?i)deposit|upfront|up front|advance|booking|to start|on acceptance|on signing", s["label"] + " " + s["trigger"]) for s in stages)
    if deposit:
        chat.append(f"If you take a deposit, decide what happens to it if the project is {'canceled' if us else 'cancelled'} "
                    "and what you call it (deposit, booking fee, advance); those are your commercial terms to add.")
    chat.append("This is commercial wording; check it with your lawyer, including refunds and cancellation.")
    return {"short": short, "paragraph": para, "late": late, "stages": stages, "deposit": deposit, "needs": needs,
            "us": us, "chat": chat}


def positive_rate(rate):
    m = re.search(r"\d+(?:[.,]\d+)?", str(rate or ""))
    if not m:
        return rate in (None, "")  # a rate still to come is named; a zero rate is not
    return float(m.group(0).replace(",", ".")) > 0


def write_docx(plan, inputs, b, path):
    D = DX.Document(plan.get("paper", "A4"), "en", plan.get("font"))
    business = (inputs.get("issuer") or {}).get("name") or ""
    D.p("Payment terms", bold=True, size=20, after=60)
    if business:
        D.p(business, size=10, colour="666666", after=200)
    if b["stages"]:
        D.p("Schedule", bold=True, size=11, after=60)
        rows = [[{"t": "Stage", "b": True}, {"t": "Share", "b": True}, {"t": "Invoiced", "b": True}]]
        for i, s in enumerate(b["stages"], 1):
            rows.append([f"{i}. {s['label']}", s["share"], s["trigger"] or s["label"]])
        D.table(rows, [0.35, 0.2, 0.45], rule_after=(0,))
        D.spacer(8)
    D.p("Two lines", bold=True, size=11, after=60)
    D.p(b["short"], after=160)
    D.p("A paragraph", bold=True, size=11, after=60)
    D.p(b["paragraph"], after=160)
    if b["late"]:
        D.p("A paragraph with your late fee", bold=True, size=11, after=60)
        D.p(b["late"], after=160)
    D.footer(business, "Page", "of")
    D.save(path, title="Payment terms", author=business, description=C.CREDIT, keywords=C.CREDIT)
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--inputs", required=True)
    ap.add_argument("--out", help="write the Word page too (only when the founder asks for a page)")
    ap.add_argument("--text-out")
    a = ap.parse_args()
    plan = C.load_json(a.plan, "plan file")
    inputs = C.load_json(a.inputs, "inputs file")
    b = build(plan, inputs)
    path = None
    if a.out:
        os.makedirs(a.out, exist_ok=True)
        business = (inputs.get("issuer") or {}).get("name") or ""
        name = C.safe_filename(f"Payment terms {business}".strip()) + ".docx"
        path = write_docx(plan, inputs, b, os.path.join(a.out, name))
    text = ["Two lines:", b["short"], "", "A paragraph:", b["paragraph"]]
    if b["late"]:
        text += ["", "A paragraph with your late fee:", b["late"]]
    print("\n".join(text))
    if a.text_out:
        with open(a.text_out, "w", encoding="utf-8") as f:
            f.write("\n".join(text) + "\n")
    for c in b["chat"]:
        print("CHAT: " + c)
    for n in b["needs"]:
        print("NEED: " + n.strip("[]").replace("NEED: ", ""))
    if path:
        print(f"WROTE: {path}")
    return 1 if b["needs"] else 0


if __name__ == "__main__":
    C.run_main(main)
