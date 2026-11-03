#!/usr/bin/env python3
"""Read the finished invoice back and check every printed figure ties out, before anything is called ready.

Usage: python3 scripts/verify_invoice.py <plan.json> <invoice .docx> [<invoice .pdf>] [--preview]
A preview (a later stage, plan made with "preview": true) carries no number, date or due date; --preview, or the
plan's own preview mark, checks it as a preview.
Reads the Word file's tables (and the PDF's text where a text reader is available), reads every amount in
the founder's number style, and checks: the lines add to the subtotal; subtotal, discount and tax give the
total; the total less anything paid gives the amount due; the project summary adds up; every printed figure
matches the plan; the currency code is on every total; the number, dates, payment details and reference are
there; supplied wording is printed exactly; nothing marked [NEED] sits on a READY invoice; and no sentence
claims what a law requires unless the founder supplied it.
Prints PROBLEM and WARN lines and a count. Exit 0 clean, 1 problems (do not deliver), 2 STOP.
Standard library only. No network calls.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import zipfile
import zlib
from decimal import Decimal, InvalidOperation
from xml.sax.saxutils import unescape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

LEGAL = re.compile(r"(?i)\b(statutory|by law|under the law|the law|legal(ly)?|required to|entitled|mandatory|penalt(y|ies)|"
                   r"interest at|per annum|enforceable|legislation|regulations?)\b")


def tables(docx):
    with zipfile.ZipFile(docx) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    out = []
    for t in re.findall(r"<w:tbl>.*?</w:tbl>", xml, re.S):
        rows = []
        for tr in re.findall(r"<w:tr>.*?</w:tr>", t, re.S):
            cells = []
            for tc in re.findall(r"<w:tc>.*?</w:tc>", tr, re.S):
                bits = re.findall(r"<w:t(?: [^>]*)?>(.*?)</w:t>|(<w:br/>)", tc, re.S)
                cells.append(unescape("".join(x if x else "\n" for x, _b in bits)).strip())
            rows.append(cells)
        out.append(rows)
    return out


def all_text(docx):
    with zipfile.ZipFile(docx) as z:
        xml = z.read("word/document.xml").decode("utf-8")
        props = z.read("docProps/core.xml").decode("utf-8") if "docProps/core.xml" in z.namelist() else ""
        foot = z.read("word/footer1.xml").decode("utf-8") if "word/footer1.xml" in z.namelist() else ""
    paras = re.findall(r"<w:p[ >].*?</w:p>", xml, re.S)
    txt = "\n".join(unescape("".join(re.findall(r"<w:t(?: [^>]*)?>(.*?)</w:t>", p, re.S))) for p in paras)
    return txt, props, unescape("".join(re.findall(r"<w:t(?: [^>]*)?>(.*?)</w:t>", foot, re.S)))


def pdf_text(pdf):
    exe = shutil.which("pdftotext")
    if exe:
        try:
            r = subprocess.run([exe, "-layout", pdf, "-"], capture_output=True, text=True, timeout=60)
            if r.returncode == 0:
                return r.stdout, "pdftotext"
        except (subprocess.TimeoutExpired, OSError):
            pass
    data = open(pdf, "rb").read()
    if b"/Producer (Made with Merigrove" in data or b"/Subject (Made with Merigrove" in data:
        chunks = []
        for m in re.finditer(rb"stream\n(.*?)\nendstream", data, re.S):
            body = m.group(1)
            try:
                body = zlib.decompress(body)
            except zlib.error:
                pass
            lines = []
            for tj in re.finditer(rb"\((.*?)(?<!\\)\) Tj", body, re.S):
                lines.append(tj.group(1).replace(b"\\(", b"(").replace(b"\\)", b")").replace(b"\\\\", b"\\").decode("cp1252", "replace"))
            chunks.append("\n".join(lines))
        return "\n".join(chunks), "the plain PDF's own text"
    return None, None


def norm(s):
    return re.sub(r"\s+", " ", str(s or "")).strip()


def read_printed(text, M):
    """Read an amount as printed in the founder's style back to minor units."""
    t = str(text).replace(M.code, "").strip()
    neg = t.startswith("-")
    t = t.lstrip("-").strip()
    if M.group in ("\u00a0", " "):
        t = re.sub(r"[ \u00a0]", "", t)
    elif M.group:
        t = t.replace(M.group, "")
    t = t.replace(M.decimal, ".") if M.mu else t
    try:
        v = Decimal(t)
    except InvalidOperation:
        return None
    return (-1 if neg else 1) * int((v * (10 ** M.mu)).to_integral_value())


def verify(plan, docx, pdf=None, preview=False):
    probs, warns = [], []
    doc, L = plan.get("doc"), plan["labels"]
    if not doc:
        raise C.Stop("this plan has no invoice to verify")
    if preview and not doc.get("preview"):
        raise C.Stop("--preview was given but this plan is not a preview; run the plan with \"preview\": true for a later stage")
    preview = bool(doc.get("preview"))
    M = C.money_for(plan)
    if not os.path.exists(docx):
        raise C.Stop(f"there is no Word file at {docx}")
    tbls = tables(docx)
    text, props, foot = all_text(docx)
    flat = norm(text)
    # lines table
    lt = next((t for t in tbls if t and t[0] and t[0][0] == L["description"]), None)
    if lt is None:
        probs.append("the lines table was not found in the Word file")
        printed_lines = []
    else:
        printed_lines = [read_printed(r[-1], M) for r in lt[1:]]
        if None in printed_lines:
            probs.append("a line amount could not be read back")
        want = [l["amount_minor"] for l in doc["lines"]]
        if printed_lines != want:
            probs.append(f"line amounts printed {printed_lines} do not match the plan {want}")
    # totals table
    tt = next((t for t in tbls if any(len(r) == 3 and r[1] == L["total"] for r in t)), None)
    got = {}
    if tt is None:
        probs.append("the totals were not found in the Word file")
    else:
        by_label = [(r[1], r[2]) for r in tt if len(r) == 3]
        for t in doc["totals"]:
            hit = [v for (lab, v) in by_label if lab == t["label"]]
            if not hit:
                probs.append(f"'{t['label']}' is missing from the totals")
                continue
            val = read_printed(hit[0], M)
            got.setdefault(t["key"], []).append(val)
            if val != t["minor"]:
                probs.append(f"'{t['label']}' prints {hit[0]}, the plan says {t['text']}")
            if t["key"] in ("total", "amount_due") and M.code not in hit[0]:
                probs.append(f"'{t['label']}' has no currency code ({M.code})")
        sub = (got.get("subtotal") or [0])[0] or 0
        disc = sum(-(x or 0) for x in got.get("discount", []))
        taxes = sum((v or 0) for k, vs in got.items() if k.startswith("tax_") for v in vs)
        total = (got.get("total") or [None])[0]
        paid = sum(-(x or 0) for x in got.get("paid", []))
        due = (got.get("amount_due") or [None])[0]
        sign = -1 if doc["type"] == "credit_note" else 1
        if printed_lines and None not in printed_lines and sum(printed_lines) != sub:
            probs.append(f"the lines add to {M.full(sum(printed_lines))} but the subtotal prints {M.full(sub)}")
        inclusive = plan.get("tax_setup", {}).get("prices_include_tax")
        if total is not None:
            expect = sub - sign * disc + (0 if inclusive else taxes)
            if expect != total:
                probs.append(f"subtotal, discount and tax give {M.full(expect)} but the total prints {M.full(total)}")
        if total is not None and due is not None and total - sign * paid != due:
            probs.append(f"the total less paid gives {M.full(total - sign * paid)} but the amount due prints {M.full(due)}")
    # project summary
    if doc.get("project_summary"):
        pt = next((t for t in tbls if t and t[0] and t[0][0] == doc["project_summary"][0]["label"]), None)
        if pt is None:
            probs.append("the project summary was not found")
        else:
            vals = []
            for r, want in zip(pt, doc["project_summary"]):
                if r[0] != want["label"]:
                    probs.append(f"project summary row '{r[0]}' should be '{want['label']}'")
                v = read_printed(r[1], M) if r[1] != L["nothing_before"] else 0
                vals.append(v)
                if v != want["minor"]:
                    probs.append(f"project summary '{r[0]}' prints {r[1]}, the plan says {want['text']}")
                if r[1] != L["nothing_before"] and M.code not in r[1]:
                    probs.append(f"project summary '{r[0]}' has no currency code")
            if None not in vals and len(vals) >= 4:
                proj, *before, this, rem = vals
                if proj - sum(before) - this != rem:
                    probs.append("the project summary does not add up: total less billed before less this invoice is not the remainder")
                if total is not None and this != total:
                    probs.append("'This invoice' in the project summary is not the invoice total")
    # presence
    must = [doc["title"], *doc["issuer"][:1], *doc["client"][:1]]
    if not preview:
        must += [doc["number"], doc["issue_text"]]
    elif L["preview_banner"] not in text:
        probs.append("a preview must carry the preview line at the top")
    if doc.get("due_text") and not doc.get("preview"):
        must.append(doc["due_text"])
    if doc.get("work_text"):
        must.append(doc["work_text"])
    for k, v in doc.get("payment") or []:
        must.append(v)
    if doc.get("reference") and not doc.get("preview"):
        must.append(doc["reference"])
    if doc.get("po"):
        must.append(doc["po"])
    if not doc.get("preview"):
        must += doc.get("terms") or []
    must += doc.get("notes") or []
    for s in must:
        if s and norm(s) not in flat:
            probs.append(f"'{s}' should be on the invoice and is not")
    if doc["status"] == "READY" and "[NEED" in text:
        probs.append("the invoice is marked READY but still holds a [NEED] gap")
    for r in doc.get("still_to_come") or []:
        if norm(r["label"]) not in flat or norm(r["text"]) not in flat:
            probs.append(f"'{r['label']}: {r['text']}' (still to come) is not on the invoice")
    if doc.get("still_to_come") and doc.get("project_summary"):
        if sum(r["minor"] for r in doc["still_to_come"]) != doc["project_summary"][-1]["minor"]:
            probs.append("the stages still to come do not add up to the remainder in the project summary")
    if doc["status"] == "DRAFT" and L["draft_banner"] not in text:
        probs.append("a DRAFT invoice must carry the draft line at the top")
    if doc["status"] != "DRAFT" and L["draft_banner"] in text:
        probs.append("the draft line is on an invoice that is not a draft")
    # no legal claims except in wording the founder supplied
    scrub = text
    for s in (doc.get("notes") or []) + (doc.get("terms") or [])[1:]:
        scrub = scrub.replace(s, "")
    for c in doc["client"] + doc["issuer"]:
        scrub = scrub.replace(c, "")
    for m in LEGAL.finditer(scrub):
        probs.append(f"'{scrub[max(0, m.start() - 30):m.end() + 30].strip()}' reads as a claim about the law; only wording you supplied may say that")
    if "\u2014" in text or "\u2013" in text:
        probs.append("a long dash is in the invoice")
    if C.CREDIT not in props:
        warns.append("the file properties do not carry the credit line")
    # PDF
    if pdf:
        if not os.path.exists(pdf):
            probs.append(f"there is no PDF at {pdf}")
        else:
            ptxt, how = pdf_text(pdf)
            if ptxt is None:
                warns.append("the PDF text could not be read here; it was made from the checked Word file")
            else:
                pflat = norm(ptxt).replace(" ,", ",")
                for s in [t["text"] for t in doc["totals"]] + [l["amount"] for l in doc["lines"]] + \
                         ([doc["number"], doc["issue_text"]] if not preview else []) + \
                         ([doc["due_text"]] if doc.get("due_text") and not doc.get("preview") else []) + \
                         [v for _k, v in doc.get("payment") or []]:
                    if s and norm(s) not in pflat:
                        probs.append(f"PDF ({how}): '{s}' was not found in the PDF text")
                if doc["status"] == "READY" and "[NEED" in ptxt:
                    probs.append("PDF: a [NEED] gap is printed on a READY invoice")
    return probs, warns


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("docx")
    ap.add_argument("pdf", nargs="?")
    ap.add_argument("--preview", action="store_true", help="check a later-stage preview (no number, date or due date)")
    a = ap.parse_args()
    plan = C.load_json(a.plan, "plan file")
    probs, warns = verify(plan, a.docx, a.pdf, a.preview)
    for p in probs:
        print("PROBLEM:", p)
    for w in warns:
        print("WARN:", w)
    print(f"{len(probs)} problems, {len(warns)} warnings")
    if not probs:
        print("TIES OUT: every printed figure matches the plan and adds up" + (" (checked as a preview)" if (plan.get("doc") or {}).get("preview") else ""))
    return 1 if probs else 0


if __name__ == "__main__":
    C.run_main(main)
