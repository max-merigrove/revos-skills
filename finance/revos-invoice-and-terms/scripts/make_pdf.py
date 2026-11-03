#!/usr/bin/env python3
"""Make the PDF beside the Word file.

Usage: python3 scripts/make_pdf.py <invoice .docx> --plan <plan.json> [--no-soffice]
1. LibreOffice (soffice) present: converts the Word file, so the PDF matches it exactly.
2. Otherwise: a plain PDF written with the standard library from the same plan (built-in Helvetica,
   the founder's paper size, the same sections in the same order). Characters outside the PDF's basic
   character set fall back to plain letters, so a currency symbol becomes its code.
3. Neither: prints "Word file only" and exits 0; the Word file stands.
Exit 0 done, 2 STOP. Standard library only. No network calls.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402


def _bi():
    import build_invoice
    return build_invoice


class _Lazy:
    def __getattr__(self, k):
        return getattr(_bi(), k)


BI = _Lazy()

HELV = {32: 278, 33: 278, 34: 355, 35: 556, 36: 556, 37: 889, 38: 667, 39: 191, 40: 333, 41: 333, 42: 389, 43: 584,
        44: 278, 45: 333, 46: 278, 47: 278, 58: 278, 59: 278, 60: 584, 61: 584, 62: 584, 63: 556, 64: 1015, 65: 667,
        66: 667, 67: 722, 68: 722, 69: 667, 70: 611, 71: 778, 72: 722, 73: 278, 74: 500, 75: 667, 76: 556, 77: 833,
        78: 722, 79: 778, 80: 667, 81: 778, 82: 722, 83: 667, 84: 611, 85: 722, 86: 667, 87: 944, 88: 667, 89: 667,
        90: 611, 91: 278, 92: 278, 93: 278, 94: 469, 95: 556, 96: 333, 97: 556, 98: 556, 99: 500, 100: 556, 101: 556,
        102: 278, 103: 556, 104: 556, 105: 222, 106: 222, 107: 500, 108: 222, 109: 833, 110: 556, 111: 556, 112: 556,
        113: 556, 114: 333, 115: 500, 116: 278, 117: 556, 118: 500, 119: 722, 120: 500, 121: 500, 122: 500, 123: 334,
        124: 260, 125: 334, 126: 584}
for _d in range(48, 58):
    HELV[_d] = 556
SUBS = {"₹": "INR ", "₩": "KRW ", "₱": "PHP ", "₦": "NGN ", "₪": "ILS ", "฿": "THB ",
        "₺": "TRY ", "₫": "VND ", "ł": "l", "Ł": "L", " ": " ", " ": " ", " ": " ",
        "‘": "'", "’": "'", "“": '"', "”": '"'}


def count_pages(pdf):
    return len(re.findall(rb"/Type\s*/Page(?!s)", open(pdf, "rb").read()))


def soffice(docx):
    exe = shutil.which("soffice") or shutil.which("libreoffice")
    if not exe:
        return None, "LibreOffice is not installed here"
    out_dir = os.path.dirname(os.path.abspath(docx))
    with tempfile.TemporaryDirectory() as prof:
        try:
            r = subprocess.run([exe, f"-env:UserInstallation=file://{prof}", "--headless", "--convert-to", "pdf",
                                "--outdir", out_dir, docx], capture_output=True, text=True, timeout=180)
        except (subprocess.TimeoutExpired, OSError) as e:
            return None, f"LibreOffice did not finish ({e})"
    pdf = os.path.splitext(os.path.abspath(docx))[0] + ".pdf"
    if r.returncode != 0 or not os.path.exists(pdf):
        return None, "LibreOffice could not convert the file"
    return pdf, "LibreOffice"


def enc(s):
    for k, v in SUBS.items():
        s = s.replace(k, v)
    out = []
    for ch in s:
        try:
            ch.encode("cp1252")
            out.append(ch)
        except UnicodeEncodeError:
            base = unicodedata.normalize("NFKD", ch).encode("ascii", "ignore").decode() or "?"
            out.append(base)
    return "".join(out)


def width(s, size):
    return sum(HELV.get(ord(c), 556) for c in s) * size / 1000.0


def esc(s):
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def wrap(text, size, maxw):
    words = enc(str(text)).split(" ")
    lines, cur = [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if width(t, size) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


class Canvas:
    def __init__(self, paper):
        self.W, self.H = {"A4": (595, 842), "Letter": (612, 792)}.get(paper, (595, 842))
        self.m = 52
        self.pages = [[]]
        self.top = 40
        self.y = self.H - self.top
        self.footer = ""

    def need(self, h):
        if self.y - h < 40 + 16:
            self.pages.append([])
            self.y = self.H - self.top

    def text(self, x, s, size=9.5, bold=False, align="left", colw=None):
        s = enc(str(s))
        if align == "right":
            x = x + (colw or 0) - width(s, size)
        self.pages[-1].append(("t", x, self.y, size, bold, s))

    def rule(self, x1, x2):
        self.pages[-1].append(("l", x1, self.y + 3, x2))

    def down(self, h):
        self.y -= h

    def row(self, cells, size=9.5, bold=False):
        """cells: list of (x, width, text, align). Wraps the first column; returns the height used."""
        wrapped = [wrap(t, size, w - 6) for (x, w, t, a) in cells]
        n = max(len(w) for w in wrapped)
        h = n * size * 1.35
        self.need(h)
        for (x, w, t, a), lines in zip(cells, wrapped):
            yy = self.y
            for ln in lines:
                self.pages[-1].append(("t", x if a == "left" else x + w - width(ln, size), yy - size, size, bold, ln))
                yy -= size * 1.35
        self.y -= h + 2
        return h

    def para(self, s, size=9.5, bold=False, x=None, w=None):
        x = self.m if x is None else x
        w = (self.W - 2 * self.m) if w is None else w
        for ln in wrap(s, size, w):
            self.need(size * 1.4)
            self.y -= size * 1.4
            self.pages[-1].append(("t", x, self.y, size, bold, ln))

    def save(self, path, title, credit):
        objs = ["<< /Type /Catalog /Pages 2 0 R >>", None,
                "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
                "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>"]
        kids = []
        total = len(self.pages)
        for pi, pg in enumerate(self.pages):
            st = []
            for item in pg:
                if item[0] == "t":
                    _k, x, y, size, bold, s = item
                    st.append(f"BT /{'F2' if bold else 'F1'} {size:.1f} Tf 1 0 0 1 {x:.1f} {y:.1f} Tm ({esc(s)}) Tj ET")
                else:
                    _k, x1, y, x2 = item
                    st.append(f"0.6 G 0.5 w {x1:.1f} {y:.1f} m {x2:.1f} {y:.1f} l S 0 G")
            foot = enc(f"{self.footer}")
            st.append(f"BT /F1 7.5 Tf 1 0 0 1 {self.m:.1f} 28 Tm ({esc(foot)}) Tj ET")
            pg_txt = enc(f"{self.page_word} {pi + 1} {self.of_word} {total}")
            st.append(f"BT /F1 7.5 Tf 1 0 0 1 {self.W - self.m - width(pg_txt, 7.5):.1f} 28 Tm ({esc(pg_txt)}) Tj ET")
            body = "\n".join(st).encode("cp1252", "replace")
            objs.append(f"<< /Length {len(body)} >>\nstream\n".encode("latin-1") + body + b"\nendstream")
            cid = len(objs)
            objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {self.W} {self.H}] "
                        f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {cid} 0 R >>")
            kids.append(len(objs))
        objs[1] = f"<< /Type /Pages /Kids [{' '.join(f'{k} 0 R' for k in kids)}] /Count {len(kids)} >>"
        out = bytearray(b"%PDF-1.4\n")
        offs = []
        for i, o in enumerate(objs, 1):
            offs.append(len(out))
            ob = o if isinstance(o, bytes) else o.encode("latin-1")
            out += f"{i} 0 obj\n".encode() + ob + b"\nendobj\n"
        info = len(objs) + 1
        offs.append(len(out))
        out += (f"{info} 0 obj\n<< /Title ({esc(enc(title))}) /Subject ({esc(credit)}) /Keywords ({esc(credit)}) "
                f"/Producer ({esc(credit)}) >>\nendobj\n").encode("latin-1")
        x = len(out)
        out += f"xref\n0 {info + 1}\n0000000000 65535 f \n".encode()
        for o in offs:
            out += f"{o:010d} 00000 n \n".encode()
        out += f"trailer\n<< /Size {info + 1} /Root 1 0 R /Info {info} 0 R >>\nstartxref\n{x}\n%%EOF\n".encode()
        with open(path, "wb") as f:
            f.write(out)


def plain_pdf(plan, path, preview=False):
    doc, L = plan["doc"], plan["labels"]
    cv = Canvas(plan.get("paper", "A4"))
    cv.page_word, cv.of_word = L["page"], L["of"]
    m, W = cv.m, cv.W - 2 * cv.m
    if preview:
        cv.para(L["preview_banner"], 11, True)
    elif doc["status"] == "DRAFT":
        cv.para(L["draft_banner"], 11, True)
    cv.down(10)
    cv.para(doc["title"], 22, True)
    cv.down(10)
    meta = []
    if not preview:
        meta += [(doc["number_label"], doc["number"]), (doc["date_label"], doc["issue_text"])]
    if doc.get("due_text") and not preview:
        meta.append((L["due_date"], doc["due_text"]))
    if doc.get("po"):
        meta.append((L["po"], doc["po"]))
    if doc.get("project_ref"):
        meta.append((L["project_ref"], doc["project_ref"]))
    left = [L["from"]] + doc["issuer"]
    for i in range(max(len(left), len(meta))):
        cells = []
        if i < len(left):
            cells.append((m, W * 0.5, left[i], "left"))
        if i < len(meta):
            cells.append((m + W * 0.5, W * 0.2, meta[i][0], "right"))
            cells.append((m + W * 0.7, W * 0.3, meta[i][1], "right"))
        cv.row(cells, 9, bold=False)
    cv.down(10)
    bill = [L["bill_to"]] + doc["client"]
    work = [L["work_covered"], doc.get("work_text") or ""]
    for i in range(max(len(bill), len(work))):
        cells = []
        if i < len(bill):
            cells.append((m, W * 0.5, bill[i], "left"))
        if i < len(work):
            cells.append((m + W * 0.5, W * 0.5, work[i], "left"))
        cv.row(cells, 9)
    cv.down(12)
    if doc.get("credits"):
        cv.para(doc["credits"]["text"], 9.5, True)
        if doc["credits"].get("reason"):
            cv.para(doc["credits"]["reason"], 9.5)
        cv.down(6)
    if doc.get("stage_heading"):
        cv.para(doc["stage_heading"], 10.5, True)
        cv.down(4)
    tax = doc["has_tax_col"]
    compact, cols = BI.line_columns(doc)
    xs = [m]
    for c in cols[:-1]:
        xs.append(xs[-1] + W * c)
    mid = [] if compact else [L["qty"], L["unit_price"]]
    head = [L["description"]] + mid + ([L["tax"]] if tax else []) + [f"{L['amount']} ({doc['currency']})"]
    cv.row([(xs[i], W * cols[i], head[i], "left" if i == 0 else "right") for i in range(len(head))], 9, True)
    cv.rule(m, m + W)
    cv.down(4)
    for ln in doc["lines"]:
        mid = [] if compact else [ln["qty"], ln["unit_price"]]
        vals = [ln["description"]] + mid + ([ln["tax"]] if tax else []) + [ln["amount"]]
        cv.row([(xs[i], W * cols[i], vals[i], "left" if i == 0 else "right") for i in range(len(vals))], 9)
    cv.rule(m, m + W)
    cv.down(8)
    for t in doc["totals"]:
        due = t["key"] == "amount_due"
        size = 13 if due else (10 if t["key"] == "total" else 9)
        if due:
            cv.down(4)
            cv.rule(m + W * 0.4, m + W)
            cv.down(2)
        cv.row([(m + W * 0.4, W * 0.33, t["label"], "right"), (m + W * 0.73, W * 0.27, t["text"], "right")], size,
               bold=due or t["key"] == "total")
    if doc.get("project_summary"):
        cv.down(10)
        cv.para(L["project_summary"], 10, True)
        cv.down(2)
        for r in doc["project_summary"]:
            cv.row([(m, W * 0.6, r["label"], "left"), (m + W * 0.6, W * 0.4, r["text"], "right")], 9)
        if doc.get("still_to_come"):
            cv.down(4)
            cv.para(L["still_to_come"], 8)
            for r in doc["still_to_come"]:
                cv.row([(m, W * 0.6, r["label"], "left"), (m + W * 0.6, W * 0.4, r["text"], "right")], 8)
    if doc.get("payment") or doc.get("payment_link"):
        cv.down(10)
        cv.para(L["how_to_pay"], 10, True)
        cv.down(2)
        rows = list(doc["payment"])
        if doc.get("payment_link"):
            rows.append([L["pay_online"], doc["payment_link"]])
        if doc.get("reference"):
            rows.append([L["payment_reference"], doc["reference"] if not preview else ""])
        if doc.get("due_text") and not preview:
            rows.append([L["due_date"], doc["due_text"]])
        if doc.get("terms") and not preview:
            rows += [[L["terms"] if i == 0 else "", t] for i, t in enumerate(doc["terms"])]
        rows += [[L["notes"] if i == 0 else "", t] for i, t in enumerate(doc.get("notes") or [])]
        for k, v in rows:
            cv.row([(m, W * 0.3, k, "left"), (m + W * 0.3, W * 0.7, v, "left")], 9)
    elif doc.get("terms") and not preview:
        cv.down(10)
        cv.para(L["terms"], 10, True)
        for t in doc["terms"]:
            cv.para(t, 9)
    if doc.get("notes") and not (doc.get("payment") or doc.get("payment_link")):
        cv.down(10)
        cv.para(L["notes"], 10, True)
        for t in doc["notes"]:
            cv.para(t, 9)
    for f in doc.get("footer") or []:
        cv.down(6)
        cv.para(f, 8)
    issuer = doc["issuer"][0] if doc["issuer"] else ""
    cv.footer = f"{issuer}  |  {doc['title']} {doc['number'] if not preview else ''}".strip()
    cv.save(path, f"{doc['title']} {doc['number']}", C.CREDIT)
    return path


def make(docx, plan, preview=False, use_soffice=True):
    pdf, how = (None, "skipped") if not use_soffice else soffice(docx)
    if pdf:
        return pdf, how
    path = os.path.splitext(docx)[0] + ".pdf"
    try:
        plain_pdf(plan, path, preview)
        return path, "the plain standard-library writer (LibreOffice was not available)"
    except Exception as e:  # noqa: BLE001
        return None, f"the PDF could not be made ({type(e).__name__})"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("docx")
    ap.add_argument("--plan", required=True)
    ap.add_argument("--no-soffice", action="store_true")
    ap.add_argument("--preview", action="store_true")
    a = ap.parse_args()
    if not os.path.exists(a.docx):
        raise C.Stop(f"there is no Word file at {a.docx}. Run build_invoice.py first")
    plan = C.load_json(a.plan, "plan file")
    pdf, how = make(a.docx, plan, a.preview, not a.no_soffice)
    if not pdf:
        print(f"Word file only: {how}. Open the Word file and use Save as PDF.")
        return 0
    print(f"WROTE: {pdf} (made with {how})")
    print(f"PAGES: {count_pages(pdf)}")
    return 0


if __name__ == "__main__":
    C.run_main(main)
