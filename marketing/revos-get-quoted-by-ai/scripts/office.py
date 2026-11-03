#!/usr/bin/env python3
"""Minimal .xlsx and .docx writers and .xlsx and .docx readers, Python standard library only.

Copied from a sibling helper and adapted for this skill (credit line, no shaded table headers, code blocks).

The workbook keeps live formulas and stores the calculated value beside each one, so previews
that do not calculate still show the figures. The reader handles workbooks saved by Excel,
LibreOffice, Numbers or Google Sheets (shared strings, inline strings, dates by number format).
No network calls.
"""
import os
import re
import zipfile
from datetime import date, timedelta
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

MADE_WITH = "Made with Merigrove Get Quoted by AI"


def _x(s):
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(s))
    return escape(s, {'"': "&quot;"})


def col_letter(c):
    s = ""
    while c:
        c, r = divmod(c - 1, 26)
        s = chr(65 + r) + s
    return s


def ref(r, c):
    return f"{col_letter(c)}{r}"


def excel_serial(d):
    return (d - date(1899, 12, 30)).days


# ---------------------------------------------------------------- xlsx writer

S_TEXT, S_BOLD, S_HEAD, S_WRAP, S_TITLE, S_NOTE, S_DATE, S_INT, S_STATUS, S_BIG, S_NUM, S_PCT = range(12)


def _styles(date_fmt):
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<numFmts count="2"><numFmt numFmtId="164" formatCode="{_x(date_fmt)}"/><numFmt numFmtId="165" formatCode="#,##0"/></numFmts>
<fonts count="5">
<font><sz val="10"/><name val="Calibri"/><family val="2"/></font>
<font><b/><sz val="10"/><name val="Calibri"/><family val="2"/></font>
<font><b/><sz val="15"/><name val="Calibri"/><family val="2"/></font>
<font><i/><sz val="9"/><color rgb="FF555555"/><name val="Calibri"/><family val="2"/></font>
<font><b/><sz val="12"/><name val="Calibri"/><family val="2"/></font>
</fonts>
<fills count="4">
<fill><patternFill patternType="none"/></fill>
<fill><patternFill patternType="gray125"/></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FFFFF2CC"/><bgColor indexed="64"/></patternFill></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FFEFEFEF"/><bgColor indexed="64"/></patternFill></fill>
</fills>
<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="12">
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top"/></xf>
<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1" applyAlignment="1"><alignment vertical="top"/></xf>
<xf numFmtId="0" fontId="1" fillId="3" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>
<xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1"/>
<xf numFmtId="0" fontId="3" fillId="0" borderId="0" xfId="0" applyFont="1" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>
<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1" applyAlignment="1"><alignment horizontal="left" vertical="top"/></xf>
<xf numFmtId="1" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1" applyAlignment="1"><alignment horizontal="left" vertical="top"/></xf>
<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1" applyProtection="1" applyAlignment="1"><alignment vertical="top"/><protection locked="0"/></xf>
<xf numFmtId="0" fontId="4" fillId="0" borderId="0" xfId="0" applyFont="1" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>
<xf numFmtId="165" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1" applyAlignment="1"><alignment horizontal="left" vertical="top"/></xf>
<xf numFmtId="9" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1" applyAlignment="1"><alignment horizontal="left" vertical="top"/></xf>
</cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>"""


class Sheet:
    def __init__(self, name):
        self.name = name[:31]
        self.cells = {}
        self.widths = {}
        self.freeze_row = None
        self.autofilter = None
        self.validations = []  # (range, [options])
        self.landscape = False
        self.merges = []
        self.heights = {}

    def set(self, r, c, value=None, style=S_TEXT, formula=None):
        """value is the stored (or cached) value; formula without the leading '='. Dates become serials."""
        if isinstance(value, date):
            value = excel_serial(value)
            if style == S_TEXT:
                style = S_DATE
        self.cells[(r, c)] = (value, style, formula)

    def row(self, r, values, style=S_TEXT, start=1):
        for i, v in enumerate(values):
            st = style
            if isinstance(v, date) and style in (S_TEXT, S_WRAP):
                st = S_DATE
            self.set(r, start + i, v, st)

    def wide(self, r, value, style, last_col=8, height=None):
        """A line of text across columns A to last_col, wrapped, with a set height."""
        self.set(r, 1, value, style)
        self.merges.append(f"A{r}:{col_letter(last_col)}{r}")
        if height:
            self.heights[r] = height

    def max_row(self):
        return max([r for r, _c in self.cells] or [0])

    def xml(self):
        out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
               '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
               'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">']
        out.append('<sheetPr><pageSetUpPr fitToPage="1"/></sheetPr>')
        if self.freeze_row:
            fr = self.freeze_row
            out.append('<sheetViews><sheetView workbookViewId="0"><pane ySplit="%d" topLeftCell="A%d" '
                       'activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>' % (fr - 1, fr))
        if self.widths:
            out.append("<cols>")
            for c in sorted(self.widths):
                out.append(f'<col min="{c}" max="{c}" width="{self.widths[c]}" customWidth="1"/>')
            out.append("</cols>")
        out.append("<sheetData>")
        by_row = {}
        for (r, c) in self.cells:
            by_row.setdefault(r, []).append(c)
        for r in sorted(by_row):
            ht = f' ht="{self.heights[r]}" customHeight="1"' if r in self.heights else ""
            out.append(f'<row r="{r}"{ht}>')
            for c in sorted(by_row[r]):
                v, s, f = self.cells[(r, c)]
                a = ref(r, c)
                if f is not None:
                    if isinstance(v, (int, float)) and not isinstance(v, bool):
                        out.append(f'<c r="{a}" s="{s}"><f>{_x(f)}</f><v>{_num(v)}</v></c>')
                    elif v is None:
                        out.append(f'<c r="{a}" s="{s}"><f>{_x(f)}</f></c>')
                    else:
                        out.append(f'<c r="{a}" s="{s}" t="str"><f>{_x(f)}</f><v>{_x(v)}</v></c>')
                elif v is None or v == "":
                    out.append(f'<c r="{a}" s="{s}"/>')
                elif isinstance(v, (int, float)) and not isinstance(v, bool):
                    out.append(f'<c r="{a}" s="{s}"><v>{_num(v)}</v></c>')
                else:
                    out.append(f'<c r="{a}" s="{s}" t="inlineStr"><is><t xml:space="preserve">{_x(v)}</t></is></c>')
            out.append("</row>")
        out.append("</sheetData>")
        if self.autofilter:
            out.append(f'<autoFilter ref="{self.autofilter}"/>')
        if self.merges:
            out.append(f'<mergeCells count="{len(self.merges)}">')
            for m in self.merges:
                out.append(f'<mergeCell ref="{m}"/>')
            out.append("</mergeCells>")
        if self.validations:
            out.append(f'<dataValidations count="{len(self.validations)}">')
            for rng, opts in self.validations:
                lst = ",".join(opts)
                out.append(f'<dataValidation type="list" allowBlank="1" showInputMessage="1" showErrorMessage="1" '
                           f'errorStyle="warning" sqref="{rng}"><formula1>"{_x(lst)}"</formula1></dataValidation>')
            out.append("</dataValidations>")
        out.append('<pageMargins left="0.4" right="0.4" top="0.5" bottom="0.5" header="0.3" footer="0.3"/>')
        orient = "landscape" if self.landscape else "portrait"
        out.append(f'<pageSetup paperSize="{{PAPER}}" orientation="{orient}" fitToWidth="1" fitToHeight="0"/>')
        out.append('<headerFooter><oddFooter>&amp;R&amp;P of &amp;N</oddFooter></headerFooter>')
        out.append("</worksheet>")
        return "".join(out)


def _num(v):
    if isinstance(v, float):
        if v != v or v in (float("inf"), float("-inf")):
            return "0"
        return repr(round(v, 10))
    return str(v)


def _core(title, description):
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            f'<dc:title>{_x(title)}</dc:title><dc:creator>Merigrove</dc:creator>'
            f'<dc:description>{_x(description)}</dc:description>'
            '</cp:coreProperties>')


def write_xlsx(path, sheets, title="", date_fmt="dd/mm/yyyy", paper="A4"):
    paper_code = "1" if str(paper).lower() == "letter" else "9"
    ct = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
          '<Default Extension="xml" ContentType="application/xml"/>',
          '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
          '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>',
          '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>']
    for i, _s in enumerate(sheets, 1):
        ct.append(f'<Override PartName="/xl/worksheets/sheet{i}.xml" '
                  'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>')
    ct.append("</Types>")
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
            '</Relationships>')
    wb = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
          '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
          'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>']
    for i, s in enumerate(sheets, 1):
        wb.append(f'<sheet name="{_x(s.name)}" sheetId="{i}" r:id="rId{i}"/>')
    wb.append("</sheets><definedNames>")
    for i, s in enumerate(sheets):
        if s.autofilter:
            a, b = s.autofilter.split(":")
            ca, ra = re.match(r"([A-Z]+)(\d+)", a).groups()
            cb, rb = re.match(r"([A-Z]+)(\d+)", b).groups()
            wb.append(f'<definedName name="_xlnm._FilterDatabase" localSheetId="{i}" hidden="1">'
                      f"'{_x(s.name)}'!${ca}${ra}:${cb}${rb}</definedName>")
    wb.append('</definedNames><calcPr calcId="191029" fullCalcOnLoad="1"/></workbook>')
    wbx = "".join(wb).replace("<definedNames></definedNames>", "")
    wbrels = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
              '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">']
    for i, _s in enumerate(sheets, 1):
        wbrels.append(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>')
    n = len(sheets) + 1
    wbrels.append(f'<Relationship Id="rId{n}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>')
    wbrels.append("</Relationships>")
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", "".join(ct))
        z.writestr("_rels/.rels", rels)
        z.writestr("docProps/core.xml", _core(title, MADE_WITH))
        z.writestr("xl/workbook.xml", wbx)
        z.writestr("xl/_rels/workbook.xml.rels", "".join(wbrels))
        z.writestr("xl/styles.xml", _styles(date_fmt))
        for i, s in enumerate(sheets, 1):
            z.writestr(f"xl/worksheets/sheet{i}.xml", s.xml().replace("{PAPER}", paper_code))


# ---------------------------------------------------------------- xlsx reader

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
RNS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
DATE_BUILTIN = set(range(14, 23)) | {45, 46, 47}


def _is_date_fmt(code):
    c = re.sub(r'"[^"]*"|\[[^\]]*\]|\\.', "", code or "").lower()
    return bool(re.search(r"[dy]", c)) or (bool(re.search(r"m", c)) and not re.search(r"[0#]", c))


def _col_index(cell_ref):
    letters = re.match(r"([A-Z]+)", cell_ref).group(1)
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n


def read_xlsx(path):
    """Return {sheet name: [[values]]} with dates as datetime.date. Raises ValueError on a broken file."""
    try:
        z = zipfile.ZipFile(path)
    except zipfile.BadZipFile as e:
        raise ValueError("the file is not a readable .xlsx workbook") from e
    names = set(z.namelist())
    shared = []
    if "xl/sharedStrings.xml" in names:
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in root.findall("m:si", NS):
            shared.append("".join(t.text or "" for t in si.iter("{%s}t" % NS["m"])))
    date_styles = set()
    if "xl/styles.xml" in names:
        st = ET.fromstring(z.read("xl/styles.xml"))
        custom = {}
        nf = st.find("m:numFmts", NS)
        if nf is not None:
            for f in nf.findall("m:numFmt", NS):
                custom[int(f.get("numFmtId"))] = f.get("formatCode")
        xfs = st.find("m:cellXfs", NS)
        if xfs is not None:
            for i, xf in enumerate(xfs.findall("m:xf", NS)):
                fid = int(xf.get("numFmtId", "0"))
                if fid in DATE_BUILTIN or (fid in custom and _is_date_fmt(custom[fid])):
                    date_styles.add(i)
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    target = {r.get("Id"): r.get("Target") for r in rels}
    date1904 = False
    pr = wb.find("m:workbookPr", NS)
    if pr is not None and pr.get("date1904") in ("1", "true"):
        date1904 = True
    base = date(1904, 1, 1) if date1904 else date(1899, 12, 30)
    out = {}
    for sh in wb.find("m:sheets", NS).findall("m:sheet", NS):
        t = target.get(sh.get(RNS), "")
        t = t.lstrip("/")
        p = t if t.startswith("xl/") else "xl/" + t
        if p not in names:
            continue
        root = ET.fromstring(z.read(p))
        rows = []
        for row in root.iter("{%s}row" % NS["m"]):
            vals = {}
            for c in row.findall("m:c", NS):
                r = c.get("r")
                idx = _col_index(r) if r else len(vals) + 1
                typ = c.get("t", "n")
                s = int(c.get("s", "0"))
                v = c.find("m:v", NS)
                val = None
                if typ == "s" and v is not None:
                    val = shared[int(v.text)]
                elif typ == "inlineStr":
                    val = "".join(x.text or "" for x in c.iter("{%s}t" % NS["m"]))
                elif typ in ("str", "e") and v is not None:
                    val = v.text or ""
                elif typ == "b" and v is not None:
                    val = v.text == "1"
                elif v is not None and v.text not in (None, ""):
                    try:
                        num = float(v.text)
                    except ValueError:
                        num = v.text
                    if isinstance(num, float) and s in date_styles and 0 < num < 2958466:
                        val = base + timedelta(days=int(num))
                    elif isinstance(num, float) and num.is_integer():
                        val = int(num)
                    else:
                        val = num
                vals[idx] = val
            rn = int(row.get("r", len(rows) + 1))
            while len(rows) < rn - 1:
                rows.append([])
            width = max(vals) if vals else 0
            rows.append([vals.get(i) for i in range(1, width + 1)])
        out[sh.get("name")] = rows
    return out


def core_description(path):
    try:
        z = zipfile.ZipFile(path)
        x = z.read("docProps/core.xml").decode("utf-8", "ignore")
    except (KeyError, zipfile.BadZipFile):
        return ""
    m = re.search(r"<dc:description>(.*?)</dc:description>", x, re.S)
    return m.group(1) if m else ""


# ---------------------------------------------------------------- docx writer

class Doc:
    """Headings, paragraphs, simple tables, page breaks and a footer. Text may carry **bold** spans."""

    PAPER = {"a4": (11906, 16838), "letter": (12240, 15840)}

    def __init__(self, paper="a4"):
        self.body = []
        self.paper = paper.lower() if paper.lower() in self.PAPER else "a4"
        self.texts = []  # plain text of every paragraph, for checks

    def _runs(self, text, size=None, bold=False, italic=False, color=None, mono=False):
        parts = re.split(r"(\*\*[^*]+\*\*)", str(text))
        out = []
        for p in parts:
            if not p:
                continue
            b = bold or (p.startswith("**") and p.endswith("**"))
            t = p[2:-2] if p.startswith("**") and p.endswith("**") else p
            rpr = ""
            if mono:
                rpr += '<w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/>'
            if b:
                rpr += "<w:b/>"
            if italic:
                rpr += "<w:i/>"
            if color:
                rpr += f'<w:color w:val="{color}"/>'
            if size:
                rpr += f'<w:sz w:val="{int(size * 2)}"/><w:szCs w:val="{int(size * 2)}"/>'
            lines = t.split("\n")
            for i, ln in enumerate(lines):
                br = "<w:br/>" if i else ""
                out.append(f'<w:r><w:rPr>{rpr}</w:rPr>{br}<w:t xml:space="preserve">{_x(ln)}</w:t></w:r>')
        return "".join(out)

    def para(self, text, size=None, bold=False, italic=False, before=0, after=100, color=None, indent=0,
             keep=False, style=None, shade=None):
        self.texts.append(re.sub(r"\*\*", "", str(text)))
        ppr = ""
        if style:
            ppr += f'<w:pStyle w:val="{style}"/>'
        if keep:
            ppr += "<w:keepNext/>"
        ppr += f'<w:spacing w:before="{before}" w:after="{after}"/>'
        if indent:
            ppr += f'<w:ind w:left="{indent}"/>'
        if shade:
            ppr += f'<w:shd w:val="clear" w:color="auto" w:fill="{shade}"/>'
        self.body.append(f"<w:p><w:pPr>{ppr}</w:pPr>{self._runs(text, size, bold, italic, color)}</w:p>")

    def h1(self, text):
        self.para(text, style="Heading1", keep=True, before=240, after=120)

    def h2(self, text):
        self.para(text, style="Heading2", keep=True, before=200, after=80)

    def h3(self, text):
        self.para(text, style="Heading3", keep=True, before=160, after=60)

    def bullet(self, text):
        self.para("• " + str(text), indent=300, after=60)

    def message(self, text):
        """A message ready to copy: indented, no box."""
        self.para(text, indent=360, after=120)

    def code(self, text, size=8):
        """Text to paste as it stands (JSON-LD, llms.txt, robots lines): monospace, indented, no box."""
        self.texts.append(str(text))
        lines = str(text).split("\n")
        runs = []
        for i, ln in enumerate(lines):
            br = "<w:br/>" if i else ""
            runs.append('<w:r><w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas" w:cs="Consolas"/>'
                        f'<w:sz w:val="{size * 2}"/><w:szCs w:val="{size * 2}"/></w:rPr>{br}'
                        f'<w:t xml:space="preserve">{_x(ln)}</w:t></w:r>')
        self.body.append('<w:p><w:pPr><w:spacing w:before="60" w:after="160"/><w:ind w:left="360"/></w:pPr>'
                         + "".join(runs) + "</w:p>")

    def page_break(self):
        self.body.append('<w:p><w:r><w:br w:type="page"/></w:r></w:p>')

    def table(self, rows, widths, header=True, size=9):
        for row in rows:
            self.texts.append(" | ".join(re.sub(r"\*\*", "", str(c)) for c in row))
        grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in widths)
        out = ['<w:tbl><w:tblPr><w:tblW w:w="0" w:type="auto"/><w:tblLayout w:type="fixed"/>'
               '<w:tblCellMar><w:top w:w="40" w:type="dxa"/><w:left w:w="80" w:type="dxa"/>'
               '<w:bottom w:w="40" w:type="dxa"/><w:right w:w="80" w:type="dxa"/></w:tblCellMar>'
               f'</w:tblPr><w:tblGrid>{grid}</w:tblGrid>']
        for i, row in enumerate(rows):
            out.append("<w:tr><w:trPr><w:cantSplit/></w:trPr>")
            for j, cell in enumerate(row):
                sh = ""
                out.append(f'<w:tc><w:tcPr><w:tcW w:w="{widths[j]}" w:type="dxa"/>{sh}</w:tcPr>'
                           f'<w:p><w:pPr><w:spacing w:before="0" w:after="0"/></w:pPr>'
                           f'{self._runs(cell, size, bold=(header and i == 0))}</w:p></w:tc>')
            out.append("</w:tr>")
        out.append("</w:tbl>")
        self.body.append("".join(out))
        self.para("", after=60)

    def save(self, path, footer="", title="", lang="en-GB"):
        pw, ph = self.PAPER[self.paper]
        lang = re.sub(r"[^A-Za-z-]", "", lang or "en-GB") or "en-GB"
        doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
               '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
               'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><w:body>'
               + "".join(self.body)
               + '<w:sectPr><w:footerReference w:type="default" r:id="rId2"/>'
               f'<w:pgSz w:w="{pw}" w:h="{ph}"/>'
               '<w:pgMar w:top="1000" w:right="1100" w:bottom="1000" w:left="1100" w:header="500" w:footer="400" w:gutter="0"/>'
               '</w:sectPr></w:body></w:document>')
        ftr = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
               '<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
               f'<w:p><w:pPr><w:spacing w:before="0" w:after="0"/></w:pPr>{self._runs(footer, 8, color="777777")}</w:p></w:ftr>')
        heading = ('<w:style w:type="paragraph" w:styleId="Heading{n}"><w:name w:val="heading {n}"/>'
                   '<w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>'
                   '<w:pPr><w:keepNext/><w:outlineLvl w:val="{lvl}"/></w:pPr>'
                   '<w:rPr><w:b/><w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/></w:rPr></w:style>')
        styles = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                  '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                  '<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/>'
                  f'<w:sz w:val="21"/><w:lang w:val="{lang}"/></w:rPr></w:rPrDefault>'
                  '<w:pPrDefault><w:pPr><w:spacing w:after="100" w:line="264" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>'
                  '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style>'
                  + heading.format(n=1, lvl=0, sz=32) + heading.format(n=2, lvl=1, sz=26) + heading.format(n=3, lvl=2, sz=22)
                  + '</w:styles>')
        ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
              '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
              '<Default Extension="xml" ContentType="application/xml"/>'
              '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
              '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
              '<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>'
              '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
              '</Types>')
        rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
                '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
                '</Relationships>')
        drels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                 '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                 '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
                 '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>'
                 '</Relationships>')
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml", ct)
            z.writestr("_rels/.rels", rels)
            z.writestr("docProps/core.xml", _core(title, MADE_WITH))
            z.writestr("word/document.xml", doc)
            z.writestr("word/styles.xml", styles)
            z.writestr("word/footer1.xml", ftr)
            z.writestr("word/_rels/document.xml.rels", drels)


def read_docx_text(path):
    """Plain text of a .docx, one paragraph per line (tables row by row)."""
    try:
        z = zipfile.ZipFile(path)
        x = z.read("word/document.xml")
    except (KeyError, zipfile.BadZipFile) as e:
        raise ValueError("the file is not a readable .docx") from e
    w = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    root = ET.fromstring(x)
    lines = []
    for p in root.iter(w + "p"):
        buf = []
        for node in p.iter():
            if node.tag == w + "t":
                buf.append(node.text or "")
            elif node.tag == w + "br":
                buf.append("\n")
        lines.append("".join(buf))
    return "\n".join(lines)
