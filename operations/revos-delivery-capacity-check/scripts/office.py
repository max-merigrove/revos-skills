#!/usr/bin/env python3
"""Minimal .xlsx and .docx writers, Python standard library only.

Used by capacity.py. The workbook keeps live formulas and stores the calculated value beside
each one, so file previews that do not calculate still show the figures. No network calls.
"""
import re
import zipfile
from xml.sax.saxutils import escape


def _x(s):
    return escape(str(s), {'"': "&quot;"})


def col_letter(c):
    s = ""
    while c:
        c, r = divmod(c - 1, 26)
        s = chr(65 + r) + s
    return s


def ref(r, c):
    return f"{col_letter(c)}{r}"


# ---------------------------------------------------------------- xlsx

# style ids, in the order of cellXfs below
S_TEXT, S_BOLD, S_HEAD, S_IN_NUM, S_NUM1, S_INT, S_PCT, S_IN_TEXT, S_WRAP, S_TITLE, S_BOLD_NUM1, S_IN_PCT, S_NOTE, S_SIDE = range(14)

_STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<numFmts count="1"><numFmt numFmtId="164" formatCode="0.0"/></numFmts>
<fonts count="4">
<font><sz val="11"/><name val="Calibri"/><family val="2"/></font>
<font><b/><sz val="11"/><name val="Calibri"/><family val="2"/></font>
<font><b/><sz val="14"/><name val="Calibri"/><family val="2"/></font>
<font><i/><sz val="10"/><color rgb="FF555555"/><name val="Calibri"/><family val="2"/></font>
</fonts>
<fills count="4">
<fill><patternFill patternType="none"/></fill>
<fill><patternFill patternType="gray125"/></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FFFFF2CC"/><bgColor indexed="64"/></patternFill></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FFF2F2F2"/><bgColor indexed="64"/></patternFill></fill>
</fills>
<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="14">
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top"/></xf>
<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1" applyAlignment="1"><alignment vertical="top"/></xf>
<xf numFmtId="0" fontId="1" fillId="3" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>
<xf numFmtId="164" fontId="0" fillId="2" borderId="0" xfId="0" applyNumberFormat="1" applyFill="1" applyAlignment="1"><alignment vertical="top"/></xf>
<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1" applyAlignment="1"><alignment vertical="top"/></xf>
<xf numFmtId="1" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1" applyAlignment="1"><alignment vertical="top"/></xf>
<xf numFmtId="9" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1" applyAlignment="1"><alignment vertical="top"/></xf>
<xf numFmtId="0" fontId="0" fillId="2" borderId="0" xfId="0" applyFill="1" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>
<xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1"/>
<xf numFmtId="164" fontId="1" fillId="0" borderId="0" xfId="0" applyNumberFormat="1" applyFont="1" applyAlignment="1"><alignment vertical="top"/></xf>
<xf numFmtId="9" fontId="0" fillId="2" borderId="0" xfId="0" applyNumberFormat="1" applyFill="1" applyAlignment="1"><alignment vertical="top"/></xf>
<xf numFmtId="0" fontId="3" fillId="0" borderId="0" xfId="0" applyFont="1" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>
<xf numFmtId="0" fontId="3" fillId="0" borderId="0" xfId="0" applyFont="1" applyAlignment="1"><alignment vertical="top"/></xf>
</cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>"""


class Sheet:
    def __init__(self, name):
        self.name = name
        self.cells = {}
        self.widths = {}
        self.freeze = None

    def set(self, r, c, value=None, style=S_TEXT, formula=None):
        """value is the stored (or cached) value; formula without the leading '='."""
        self.cells[(r, c)] = (value, style, formula)

    def xml(self):
        out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
               '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
               'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">']
        if self.freeze:
            out.append('<sheetViews><sheetView workbookViewId="0"><pane ySplit="%d" topLeftCell="A%d" '
                       'activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>' % (self.freeze - 1, self.freeze))
        if self.widths:
            out.append("<cols>")
            for c in sorted(self.widths):
                out.append(f'<col min="{c}" max="{c}" width="{self.widths[c]}" customWidth="1"/>')
            out.append("</cols>")
        out.append("<sheetData>")
        rows = sorted({r for r, _c in self.cells})
        for r in rows:
            out.append(f'<row r="{r}">')
            for c in sorted(cc for rr, cc in self.cells if rr == r):
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
        out.append('<pageMargins left="0.5" right="0.5" top="0.6" bottom="0.6" header="0.3" footer="0.3"/>')
        out.append("</worksheet>")
        return "".join(out)


def _num(v):
    if isinstance(v, float):
        if v != v or v in (float("inf"), float("-inf")):
            return "0"
        return repr(round(v, 10))
    return str(v)


def write_xlsx(path, sheets, title="", creator="Merigrove"):
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
    wb.append('</sheets><calcPr calcId="191029" fullCalcOnLoad="1"/></workbook>')
    wbrels = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
              '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">']
    for i, _s in enumerate(sheets, 1):
        wbrels.append(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>')
    n = len(sheets) + 1
    wbrels.append(f'<Relationship Id="rId{n}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>')
    wbrels.append("</Relationships>")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", "".join(ct))
        z.writestr("_rels/.rels", rels)
        z.writestr("docProps/core.xml", _core(title, creator))
        z.writestr("xl/workbook.xml", "".join(wb))
        z.writestr("xl/_rels/workbook.xml.rels", "".join(wbrels))
        z.writestr("xl/styles.xml", _STYLES)
        for i, s in enumerate(sheets, 1):
            z.writestr(f"xl/worksheets/sheet{i}.xml", s.xml())


def _core(title, creator):
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            f'<dc:title>{_x(title)}</dc:title><dc:creator>{_x(creator)}</dc:creator>'
            '<dc:description>Made with Merigrove Delivery Capacity Check</dc:description>'
            '</cp:coreProperties>')


# ---------------------------------------------------------------- docx

class Doc:
    """Paragraphs, simple tables and a footer. Text may carry **bold** spans."""

    PAPER = {"a4": (11906, 16838), "letter": (12240, 15840)}  # twentieths of a point

    def __init__(self, scale=1.0, paper="a4"):
        self.body = []
        self.scale = scale
        self.paper = paper if paper in self.PAPER else "a4"
        self.height = 0.0  # estimated height in points, to keep the page to one sheet
        # page width less the margins below, plus the estimate's allowance
        self.TEXT_WIDTH_PT = 535 + (self.PAPER[self.paper][0] - self.PAPER["a4"][0]) / 20

    def _est(self, text, size, width_pt=None):
        plain = re.sub(r"\*\*", "", str(text))
        per_line = max(8, (width_pt or self.TEXT_WIDTH_PT) / (size * 0.5))
        lines = max(1, -(-len(plain) // int(per_line)))
        return lines * size * 1.22

    def _runs(self, text, size=None, bold=False, italic=False, color=None):
        parts = re.split(r"(\*\*[^*]+\*\*)", str(text))
        out = []
        for p in parts:
            if not p:
                continue
            b = bold or (p.startswith("**") and p.endswith("**"))
            t = p[2:-2] if p.startswith("**") and p.endswith("**") else p
            rpr = ""
            if b:
                rpr += "<w:b/>"
            if italic:
                rpr += "<w:i/>"
            if color:
                rpr += f'<w:color w:val="{color}"/>'
            if size:
                rpr += f'<w:sz w:val="{int(size * 2)}"/><w:szCs w:val="{int(size * 2)}"/>'
            out.append(f'<w:r><w:rPr>{rpr}</w:rPr><w:t xml:space="preserve">{_x(t)}</w:t></w:r>')
        return "".join(out)

    def para(self, text, size=10, bold=False, italic=False, before=0, after=80, color=None, indent=0, keep=False):
        size, before, after = size * self.scale, int(before * self.scale), int(after * self.scale)
        self.height += self._est(text, size, self.TEXT_WIDTH_PT - indent / 20) + (before + after) / 20
        ppr = f'<w:spacing w:before="{before}" w:after="{after}" w:line="252" w:lineRule="auto"/>'
        if indent:
            ppr += f'<w:ind w:left="{indent}" w:hanging="{min(indent, 260)}"/>'
        if keep:
            ppr += "<w:keepNext/>"
        self.body.append(f"<w:p><w:pPr>{ppr}</w:pPr>{self._runs(text, size, bold, italic, color)}</w:p>")

    def heading(self, text, size=11.5, before=200, after=60):
        self.para(text, size=size, bold=True, before=before, after=after, keep=True)

    def table(self, rows, widths, header=True, size=8.5):
        """rows: list of lists of text. widths in twentieths of a point."""
        size = size * self.scale
        for row in rows:
            self.height += max(self._est(c, size, w / 20 - 6) for c, w in zip(row, widths)) + 3
        grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in widths)
        out = ['<w:tbl><w:tblPr><w:tblW w:w="0" w:type="auto"/><w:tblLayout w:type="fixed"/>'
               '<w:tblCellMar><w:top w:w="30" w:type="dxa"/><w:left w:w="60" w:type="dxa"/>'
               '<w:bottom w:w="30" w:type="dxa"/><w:right w:w="60" w:type="dxa"/></w:tblCellMar>'
               f'</w:tblPr><w:tblGrid>{grid}</w:tblGrid>']
        for i, row in enumerate(rows):
            out.append("<w:tr><w:trPr><w:cantSplit/></w:trPr>")
            for j, cell in enumerate(row):
                shade = '<w:shd w:val="clear" w:color="auto" w:fill="F2F2F2"/>' if header and i == 0 else ""
                out.append(f'<w:tc><w:tcPr><w:tcW w:w="{widths[j]}" w:type="dxa"/>{shade}</w:tcPr>'
                           f'<w:p><w:pPr><w:spacing w:before="0" w:after="0"/></w:pPr>'
                           f'{self._runs(cell, size, bold=(header and i == 0))}</w:p></w:tc>')
            out.append("</w:tr>")
        out.append("</w:tbl>")
        self.body.append("".join(out))
        self.para("", size=4 / self.scale, after=0)

    def save(self, path, footer="", title="", paper=None, lang="en-GB"):
        pw, ph = self.PAPER.get(paper or self.paper, self.PAPER["a4"])
        lang = re.sub(r"[^A-Za-z-]", "", lang or "en-GB") or "en-GB"
        doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
               '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
               'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><w:body>'
               + "".join(self.body)
               + '<w:sectPr><w:footerReference w:type="default" r:id="rId2"/>'
               f'<w:pgSz w:w="{pw}" w:h="{ph}"/>'
               '<w:pgMar w:top="700" w:right="980" w:bottom="620" w:left="1000" w:header="360" w:footer="300" w:gutter="0"/>'
               '</w:sectPr></w:body></w:document>')
        ftr = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
               '<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
               f'<w:p><w:pPr><w:spacing w:before="0" w:after="0"/></w:pPr>{self._runs(footer, 7.5, color="777777")}</w:p></w:ftr>')
        styles = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                  '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                  '<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/>'
                  f'<w:sz w:val="20"/><w:lang w:val="{lang}"/></w:rPr></w:rPrDefault>'
                  '<w:pPrDefault><w:pPr><w:spacing w:after="80"/></w:pPr></w:pPrDefault></w:docDefaults>'
                  '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>'
                  '</w:styles>')
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
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml", ct)
            z.writestr("_rels/.rels", rels)
            z.writestr("docProps/core.xml", _core(title, "Merigrove"))
            z.writestr("word/document.xml", doc)
            z.writestr("word/styles.xml", styles)
            z.writestr("word/footer1.xml", ftr)
            z.writestr("word/_rels/document.xml.rels", drels)
