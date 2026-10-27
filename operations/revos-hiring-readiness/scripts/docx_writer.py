#!/usr/bin/env python3
"""A small Word (.docx) writer for the report, standard library only.

Turns a plain markdown subset into a .docx: '# ' title, '## ' and '### ' headings, paragraphs,
'- ' bullets, '1. ' numbered lines, '| a | b |' tables, **bold** runs and '> ' callouts.
Typography and space carry the structure; no ruled lines or boxes. A footer carries the
planning-not-advice line; the "Made with" credit sits in the document properties only. Imported by build.py; not run on its own.
"""
import re
import zipfile
from datetime import datetime, timezone
from xml.sax.saxutils import escape

FONT = "Calibri"
INK = "1A1A1A"
MUTED = "5F5F5F"


def _runs(text, size=None, color=None, bold_all=False):
    out = []
    for i, part in enumerate(re.split(r"\*\*(.+?)\*\*", text)):
        if not part:
            continue
        bold = bold_all or i % 2 == 1
        rpr = f'<w:rFonts w:ascii="{FONT}" w:hAnsi="{FONT}" w:cs="{FONT}"/>'
        if bold:
            rpr += "<w:b/>"
        rpr += f'<w:color w:val="{color or INK}"/>'
        if size:
            rpr += f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>'
        out.append(f'<w:r><w:rPr>{rpr}</w:rPr><w:t xml:space="preserve">{escape(part)}</w:t></w:r>')
    return "".join(out)


def _p(text, style=None, size=None, color=None, bold=False, before=0, after=120, indent=0, keep=False):
    ppr = ""
    if style:
        ppr += f'<w:pStyle w:val="{style}"/>'
    if keep:
        ppr += "<w:keepNext/>"
    ppr += f'<w:spacing w:before="{before}" w:after="{after}" w:line="276" w:lineRule="auto"/>'
    if indent:
        ppr += f'<w:ind w:left="{indent}" w:hanging="{min(indent, 280)}"/>'
    return f"<w:p><w:pPr>{ppr}</w:pPr>{_runs(text, size, color, bold)}</w:p>"


def _is_num(c):
    return bool(re.fullmatch(r"-?(?:[A-Z]{0,3}[$\u00a3\u20ac\u20b9\u00a5\u20b1])?[\d,.]+(?: [A-Z]{3}| ?[\u20ac\u00a3])?( \(below\))?|-?[\d,.]+%", c.strip()))


def _table(rows):
    ncol = max(len(r) for r in rows)
    width = 9360
    weight = []
    for ci in range(ncol):
        lens = [len(r[ci]) if ci < len(r) else 0 for r in rows]
        weight.append(min(max(max(lens), 5), 70))
    tot = sum(weight)
    colw = [max(700, int(width * w / tot)) for w in weight]
    colw[-1] += width - sum(colw)
    numcol = [ci > 0 and all(_is_num(r[ci]) for r in rows[1:] if ci < len(r) and r[ci].strip()) for ci in range(ncol)]
    grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in colw)
    xml = [f'<w:tbl><w:tblPr><w:tblW w:w="{width}" w:type="dxa"/><w:tblLayout w:type="fixed"/>'
           '<w:tblBorders><w:top w:val="nil"/><w:left w:val="nil"/><w:bottom w:val="nil"/><w:right w:val="nil"/>'
           '<w:insideH w:val="nil"/><w:insideV w:val="nil"/></w:tblBorders>'
           '<w:tblCellMar><w:top w:w="60" w:type="dxa"/><w:left w:w="0" w:type="dxa"/><w:bottom w:w="60" w:type="dxa"/>'
           f'<w:right w:w="160" w:type="dxa"/></w:tblCellMar></w:tblPr><w:tblGrid>{grid}</w:tblGrid>']
    for ri, r in enumerate(rows):
        r = r + [""] * (ncol - len(r))
        xml.append('<w:tr><w:trPr><w:cantSplit/></w:trPr>')
        for ci, c in enumerate(r):
            jc = '<w:jc w:val="right"/>' if numcol[ci] else ""
            body = _runs(c.strip(), 18 if ri > 0 else 17, MUTED if ri == 0 else INK, bold_all=(ri == 0))
            xml.append(f'<w:tc><w:tcPr><w:tcW w:w="{colw[ci]}" w:type="dxa"/></w:tcPr><w:p><w:pPr>{jc}'
                       f'<w:spacing w:before="0" w:after="0"/></w:pPr>{body}</w:p></w:tc>')
        xml.append("</w:tr>")
    xml.append("</w:tbl>")
    return "".join(xml) + _p("", after=60)


def md_to_body(md):
    out, table = [], []
    lines = md.splitlines()
    for i, raw in enumerate(lines):
        line = raw.rstrip()
        if line.startswith("|"):
            cells = [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
            if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                table.append(cells)
            continue
        if table:
            out.append(_table(table))
            table = []
        if not line.strip():
            continue
        if line.startswith("# "):
            out.append(_p(line[2:], size=40, bold=True, after=60))
        elif line.startswith("## "):
            out.append(_p(line[3:], "Heading1", size=28, bold=True, before=360, after=120, keep=True))
        elif line.startswith("### "):
            out.append(_p(line[4:], "Heading2", size=22, bold=True, before=200, after=80, keep=True))
        elif line.startswith("VERDICT: "):
            out.append(_p(line[9:], size=48, bold=True, before=240, after=60))
        elif line.startswith("> "):
            out.append(_p(line[2:], size=22, color=INK, before=60, after=160, indent=0))
        elif re.match(r"^- ", line):
            out.append(_p("•  " + line[2:], indent=280, after=60))
        elif re.match(r"^\d+\. ", line):
            out.append(_p(line, indent=360, after=60))
        elif line.startswith("_") and line.endswith("_"):
            out.append(_p(line.strip("_"), size=18, color=MUTED, after=80))
        else:
            out.append(_p(line))
    if table:
        out.append(_table(table))
    return "".join(out)


PAPER = {"A4": (11906, 16838), "Letter": (12240, 15840)}


def write_docx(path, md, title, footer, paper="A4", lang="en-GB", credit=None):
    """credit: the "Made with" line, kept in the document properties only, never on the page.
    paper: A4 or Letter, from the founder's country (locale_defaults), never from their spelling."""
    body = md_to_body(md)
    pw, ph = PAPER.get(paper, PAPER["A4"])
    ns = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
          'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"')
    sect = ('<w:sectPr><w:footerReference w:type="default" r:id="rIdFooter"/>'
            f'<w:pgSz w:w="{pw}" w:h="{ph}"/><w:pgMar w:top="1300" w:right="1270" w:bottom="1300" w:left="1270" '
            'w:header="600" w:footer="600" w:gutter="0"/></w:sectPr>')
    doc = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {ns}><w:body>{body}{sect}</w:body></w:document>'
    foot = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:ftr {ns}>'
            + _p(footer, size=16, color=MUTED, after=0) + "</w:ftr>")
    styles = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
              f'<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="{FONT}" w:hAnsi="{FONT}" w:cs="{FONT}"/>'
              f'<w:sz w:val="21"/><w:szCs w:val="21"/><w:lang w:val="{lang}"/></w:rPr></w:rPrDefault></w:docDefaults>'
              '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>'
              '<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/>'
              '<w:pPr><w:outlineLvl w:val="0"/></w:pPr></w:style>'
              '<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/>'
              '<w:pPr><w:outlineLvl w:val="1"/></w:pPr></w:style></w:styles>')
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
          '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
          '<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>'
          '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
          '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
          '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
            '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
            '</Relationships>')
    drels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
             '<Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
             '<Relationship Id="rIdFooter" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>'
             '</Relationships>')
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    core = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            f'<dc:title>{escape(title)}</dc:title><dc:description>{escape(credit or footer)}</dc:description>'
            f'<dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created></cp:coreProperties>')
    app = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
           f'<Application>{escape(credit or footer)}</Application></Properties>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", doc)
        z.writestr("word/styles.xml", styles)
        z.writestr("word/footer1.xml", foot)
        z.writestr("word/_rels/document.xml.rels", drels)
        z.writestr("docProps/core.xml", core)
        z.writestr("docProps/app.xml", app)
