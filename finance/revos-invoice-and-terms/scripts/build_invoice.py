#!/usr/bin/env python3
"""Write the invoice (or credit note) as a Word file and a PDF from the plan file.

Usage (paths relative to this skill's folder):
  python3 scripts/build_invoice.py <plan.json> --out <output folder> [--preview-stage N] [--no-pdf] [--no-soffice]
Writes "<Invoice|Credit note> <number> <Client> <YYYY-MM-DD>.docx" and ".pdf" (LibreOffice when present,
otherwise a plain standard-library PDF; if neither works, the Word file only, said in one line).
A preview (plan made with "preview": true, or --preview) is a later stage with no number and no date, for the founder
to look at: only its PDF goes to --out; its Word file stays beside the plan (the scratch folder) for verify_invoice.py.
Every figure printed comes from the plan; nothing is worked out here.
Exit 0 written, 2 STOP. Standard library only. No network calls.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402
import docx_lite as DX  # noqa: E402
import make_pdf as MP  # noqa: E402

GREY = "666666"


def line_columns(doc):
    """Column widths for the lines table. A stage invoice whose lines are all shares of the project drops the
    Qty and Unit price columns (they would only repeat 1 and the amount), which keeps it on one page."""
    compact = bool(doc.get("compact_lines"))
    if compact:
        widths = [0.62, 0.17] if doc["has_tax_col"] else [0.75]
    else:
        widths = [0.44, 0.08, 0.15, 0.15] if doc["has_tax_col"] else [0.52, 0.1, 0.17]
    widths.append(round(1 - sum(widths), 3))
    return compact, widths


def lines_rows(doc, L):
    cur = doc["currency"]
    compact, widths = line_columns(doc)
    head = [{"t": L["description"], "b": True}]
    if not compact:
        head += [{"t": L["qty"], "b": True, "align": "right"}, {"t": L["unit_price"], "b": True, "align": "right"}]
    if doc["has_tax_col"]:
        head.append({"t": L["tax"], "b": True, "align": "right"})
    head.append({"t": f"{L['amount']} ({cur})", "b": True, "align": "right"})
    rows = [head]
    for ln in doc["lines"]:
        r = [ln["description"]]
        if not compact:
            r += [{"t": ln["qty"], "align": "right"}, {"t": ln["unit_price"], "align": "right"}]
        if doc["has_tax_col"]:
            r.append({"t": ln["tax"], "align": "right"})
        r.append({"t": ln["amount"], "align": "right"})
        rows.append(r)
    return rows, widths


def build_docx(plan, path, preview=False):
    doc = plan["doc"]
    L = plan["labels"]
    accent = plan.get("colour")
    D = DX.Document(plan.get("paper", "A4"), plan.get("language", "en"), plan.get("font"))
    if preview:
        D.p(L["preview_banner"], bold=True, size=11, after=120)
    elif doc["status"] == "DRAFT":
        D.p(L["draft_banner"], bold=True, size=11, after=120)
    if plan.get("logo"):
        if not D.logo(plan["logo"]):
            print(f"WARN: the logo at {plan['logo']} could not be read (PNG or JPEG only); the invoice is built without it")
    D.p(doc["title"], bold=True, size=22, colour=accent, after=60)
    # From block and the invoice facts side by side
    meta = []
    if not preview:
        meta.append((doc["number_label"], doc["number"]))
        meta.append((doc["date_label"], doc["issue_text"]))
    if doc.get("due_text") and not preview:
        meta.append((L["due_date"], doc["due_text"]))
    if doc.get("po"):
        meta.append((L["po"], doc["po"]))
    if doc.get("project_ref"):
        meta.append((L["project_ref"], doc["project_ref"]))
    left = [{"t": L["from"], "b": True, "colour": GREY, "size": 8.5}] + \
        [{"t": x, "b": i == 0} for i, x in enumerate(doc["issuer"])]
    labels_col = [{"t": "", "size": 8.5}] + [{"t": k, "colour": GREY, "size": 9.5, "align": "right"} for k, _v in meta]
    values_col = [{"t": "", "size": 8.5}] + [{"t": v, "b": True, "align": "right"} for _k, v in meta]
    D.table([[{"paras": left}, {"paras": labels_col}, {"paras": values_col}]], [0.48, 0.2, 0.32], cell_after=0)
    D.spacer(4)
    bill = [{"t": L["bill_to"], "b": True, "colour": GREY, "size": 8.5}] + [{"t": x, "b": i == 0} for i, x in enumerate(doc["client"])]
    work = [{"t": L["work_covered"], "b": True, "colour": GREY, "size": 8.5}, {"t": doc.get("work_text") or ""}]
    D.table([[{"paras": bill}, {"paras": work}]], [0.48, 0.52], cell_after=0)
    D.spacer(6)
    if doc.get("credits"):
        D.p(doc["credits"]["text"], bold=True)
        if doc["credits"].get("reason"):
            D.p(doc["credits"]["reason"])
    if doc.get("stage_heading"):
        D.p(doc["stage_heading"], bold=True, size=10.5, after=60, keep=True)
    rows, widths = lines_rows(doc, L)
    D.table(rows, widths, rule_after=(0, len(rows) - 1), header=True, cell_after=20)
    D.spacer(6)
    trows = []
    big = []
    for i, t in enumerate(doc["totals"]):
        is_due = t["key"] == "amount_due"
        is_total = t["key"] == "total"
        size = 14 if is_due else (10.5 if is_total else 9.5)
        trows.append([{"t": "", "norule": True}, {"t": t["label"], "b": is_due or is_total, "size": size, "align": "right"},
                      {"t": t["text"], "b": is_due or is_total, "size": size, "align": "right", "colour": accent if is_due else None}])
        if is_due:
            big.append(i)
    D.table(trows, [0.4, 0.33, 0.27], rule_top=tuple(big), cell_after=0)
    if doc.get("project_summary"):
        D.spacer(4)
        D.p(L["project_summary"], bold=True, size=10, after=40, keep=True)
        D.table([[{"t": r["label"]}, {"t": r["text"], "align": "right"}] for r in doc["project_summary"]], [0.6, 0.4], cell_after=0)
        if doc.get("still_to_come"):
            D.p(L["still_to_come"], size=8.5, colour=GREY, before=60, after=0, keep=True)
            D.table([[{"t": r["label"], "size": 8.5, "colour": GREY}, {"t": r["text"], "size": 8.5, "colour": GREY, "align": "right"}]
                     for r in doc["still_to_come"]], [0.6, 0.4], cell_after=0)
    if doc.get("payment") or doc.get("payment_link"):
        D.spacer(4)
        D.p(L["how_to_pay"], bold=True, size=10, after=40, keep=True)
        prow = [[{"t": k, "colour": GREY}, {"t": v}] for k, v in doc["payment"]]
        if doc.get("payment_link"):
            prow.append([{"t": L["pay_online"], "colour": GREY}, {"t": doc["payment_link"]}])
        if doc.get("reference"):
            prow.append([{"t": L["payment_reference"], "colour": GREY}, {"t": doc["reference"] if not preview else "", "b": True}])
        if doc.get("due_text") and not preview:
            prow.append([{"t": L["due_date"], "colour": GREY}, {"t": doc["due_text"], "b": True}])
        # the terms and any notes sit in the same block as how to pay, so the due date, reference and terms stay together
        if doc.get("terms") and not preview:
            for i, t in enumerate(doc["terms"]):
                prow.append([{"t": L["terms"] if i == 0 else "", "colour": GREY}, {"t": t}])
        for i, t in enumerate(doc.get("notes") or []):
            prow.append([{"t": L["notes"] if i == 0 else "", "colour": GREY}, {"t": t}])
        D.table(prow, [0.3, 0.7], cell_after=0)
    elif doc.get("terms") and not preview:
        D.spacer(4)
        D.p(L["terms"], bold=True, size=10, after=40, keep=True)
        for t in doc["terms"]:
            D.p(t, after=40)
    if doc.get("notes") and not (doc.get("payment") or doc.get("payment_link")):
        D.spacer(6)
        D.p(L["notes"], bold=True, size=10, after=40, keep=True)
        for t in doc["notes"]:
            D.p(t)
    for f in doc.get("footer") or []:
        D.p(f, size=8.5, colour=GREY, before=80)
    issuer = doc["issuer"][0] if doc["issuer"] else ""
    D.footer(f"{issuer}  |  {doc['title']} {doc['number'] if not preview else ''}".strip(), L["page"], L["of"])
    D.save(path, title=f"{doc['title']} {doc['number']}", author=issuer, description=C.CREDIT, keywords=C.CREDIT)
    return D


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--out", required=True)
    ap.add_argument("--preview", action="store_true", help="build a stage preview (plan made with \"preview\": true)")
    ap.add_argument("--no-pdf", action="store_true")
    ap.add_argument("--no-soffice", action="store_true", help="skip LibreOffice (to test the plain PDF)")
    a = ap.parse_args()
    plan = C.load_json(a.plan, "plan file")
    if not plan.get("doc"):
        raise C.Stop("this plan has no invoice in it (terms or reminder only). Nothing to build")
    os.makedirs(a.out, exist_ok=True)
    doc = plan["doc"]
    base = doc["file_base"]
    a.preview = a.preview or bool(doc.get("preview"))
    docx_dir = os.path.dirname(os.path.abspath(a.plan)) if a.preview else a.out
    docx = os.path.join(docx_dir, base + ".docx")
    build_docx(plan, docx, preview=a.preview)
    print(f"WROTE: {docx}" + (" (working copy for the check; not for the founder)" if a.preview else ""))
    if a.no_pdf:
        return 0
    pdf, how = MP.make(docx, plan, preview=a.preview, use_soffice=not a.no_soffice)
    if pdf and a.preview and os.path.dirname(os.path.abspath(pdf)) != os.path.abspath(a.out):
        dest = os.path.join(a.out, os.path.basename(pdf))
        os.replace(pdf, dest)
        pdf = dest
    if pdf:
        print(f"WROTE: {pdf} (made with {how})")
        print(f"PAGES: {MP.count_pages(pdf)}")
    else:
        print(f"Word file only: {how}. Open the Word file and use Save as PDF.")
    return 0


if __name__ == "__main__":
    C.run_main(main)
