#!/usr/bin/env python3
"""Turn the scope kit's markdown into a Word document (.docx). Standard library only.

Usage: python3 scripts/md_to_docx.py <input.md> <output.docx> [--title "Title"]
Supports: # to ### headings, paragraphs, "- " bullets, "1. " numbered items, "> " quotes (client
messages), pipe tables, **bold**, *italic*, "<!-- pagebreak -->" and form lines written as "Label: ____".
Page numbers sit in the footer. The document property reads "Made with Merigrove Scope Guard";
nothing promotional is added to the page. Plain black and white: structure comes from space and type.
"""
import re
import sys
import zipfile
from datetime import datetime, timezone
from xml.sax.saxutils import escape

FONT = "Calibri"
CREDIT = "Made with Merigrove Scope Guard"


def run(text, bold=False, italic=False, size=None, colour=None):
    props = []
    if bold:
        props.append("<w:b/>")
    if italic:
        props.append("<w:i/>")
    if colour:
        props.append(f'<w:color w:val="{colour}"/>')
    if size:
        props.append(f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>')
    rpr = f"<w:rPr>{''.join(props)}</w:rPr>" if props else ""
    return f'<w:r>{rpr}<w:t xml:space="preserve">{escape(text)}</w:t></w:r>'


INLINE_RE = re.compile(r"(\*\*[^*]+\*\*|(?<![\w*])\*[^*\s][^*]*\*(?![\w*]))")


def inline(text, italic=False, colour=None, bold=False):
    if "<br>" in text:
        return '<w:r><w:br/></w:r>'.join(inline(t.strip(), italic, colour, bold) for t in text.split("<br>"))
    out = []
    for part in INLINE_RE.split(text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            out.append(run(part[2:-2], bold=True, italic=italic, colour=colour))
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            out.append(run(part[1:-1], italic=True, bold=bold, colour=colour))
        else:
            out.append(run(part, italic=italic, colour=colour, bold=bold))
    return "".join(out)


def para(content, style=None, keep_next=False, extra=""):
    ppr = []
    if style:
        ppr.append(f'<w:pStyle w:val="{style}"/>')
    if keep_next:
        ppr.append("<w:keepNext/>")
    if extra:
        ppr.append(extra)
    p = f"<w:pPr>{''.join(ppr)}</w:pPr>" if ppr else ""
    return f"<w:p>{p}{content}</w:p>"


def table(rows):
    header, body = rows[0], rows[1:]
    ncol = len(header)
    total = 9400
    # width by the longest text in each column, within limits, so a long description gets the room
    cols = [[re.sub(r"\*", "", (r + [""] * ncol)[i]) for r in rows] for i in range(ncol)]
    floor = [max([len(w) for c in col for w in c.split()] + [4]) + 2 for col in cols]   # no word is ever split
    pref = [min(max(len(c) for c in col), 48) for col in cols]
    weights = [max(f, p) for f, p in zip(floor, pref)]
    budget = 92  # characters across the page at table size
    if sum(weights) > budget:
        spare = sum(weights) - budget
        flex = [w - f for w, f in zip(weights, floor)]
        if sum(flex) > 0:
            cut = min(spare, sum(flex))
            weights = [w - cut * fl / sum(flex) for w, fl in zip(weights, flex)]
    widths = [int(total * w / sum(weights)) for w in weights]
    grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in widths)

    def cell(text, i, head):
        content = run(text, bold=True) if head else inline(text)
        return (f'<w:tc><w:tcPr><w:tcW w:w="{widths[i]}" w:type="dxa"/></w:tcPr>'
                f'{para(content, "TableHead" if head else "TableText")}</w:tc>')
    out = [f'<w:tbl><w:tblPr><w:tblW w:w="{total}" w:type="dxa"/><w:tblLayout w:type="fixed"/>'
           '<w:tblCellMar><w:top w:w="50" w:type="dxa"/><w:left w:w="0" w:type="dxa"/>'
           '<w:bottom w:w="70" w:type="dxa"/><w:right w:w="200" w:type="dxa"/></w:tblCellMar>'
           f'<w:tblLook w:val="0000"/></w:tblPr><w:tblGrid>{grid}</w:tblGrid>']
    out.append('<w:tr><w:trPr><w:tblHeader/><w:cantSplit/></w:trPr>' + "".join(cell(c, i, True) for i, c in enumerate(header)) + "</w:tr>")
    for r in body:
        r = (r + [""] * ncol)[:ncol]
        out.append('<w:tr><w:trPr><w:cantSplit/></w:trPr>' + "".join(cell(c, i, False) for i, c in enumerate(r)) + "</w:tr>")
    out.append("</w:tbl>")
    out.append(para("", extra='<w:spacing w:after="80"/>'))
    return "".join(out)


def convert(md):
    lines = md.replace("\r\n", "\n").split("\n")
    body, i, title = [], 0, None
    while i < len(lines):
        s = lines[i].rstrip()
        if s.strip() == "<!-- pagebreak -->":
            body.append('<w:p><w:r><w:br w:type="page"/></w:r></w:p>')
            i += 1
            continue
        if s.strip().startswith("<!--"):
            i += 1
            continue
        if s.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|$", lines[i + 1].strip()):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                if not re.match(r"^\|[\s:|-]+\|$", lines[i].strip()):
                    cells = re.split(r"(?<!\\)\|", lines[i].strip().strip("|"))
                    rows.append([c.strip().replace("\\|", "|") for c in cells])
                i += 1
            body.append(table(rows))
            continue
        m = re.match(r"^(#{1,3})\s+(.*)$", s)
        if m:
            level, text = len(m.group(1)), m.group(2).strip()
            if level == 1 and title is None:
                title = text
            body.append(para(inline(text), f"Heading{level}", keep_next=True))
            i += 1
            continue
        if not s.strip():
            i += 1
            continue
        if re.match(r"^\s*[-*]\s+", s):
            body.append(para(run("•\t") + inline(re.sub(r"^\s*[-*]\s+", "", s)), "ListItem"))
            i += 1
            continue
        mn = re.match(r"^\s*(\d{1,2})[.)]\s+(.*)$", s)
        if mn:
            body.append(para(run(mn.group(1) + ".\t") + inline(mn.group(2)), "ListItem"))
            i += 1
            continue
        if s.startswith(">"):
            body.append(para(inline(s.lstrip("> ").strip()), "Message"))
            i += 1
            continue
        fm = re.match(r"^([A-Z][^:]{1,40}):\s*(_{3,})\s*$", s)
        if fm:
            body.append(para(run(fm.group(1) + ":", bold=True) + run("\t"), "FormLine"))
            i += 1
            continue
        if s.startswith("*") and s.endswith("*") and not s.startswith("**"):
            body.append(para(inline(s.strip()), "Small"))
        else:
            body.append(para(inline(s.strip())))
        i += 1
    return title, "".join(body)


STYLES = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="{FONT}" w:hAnsi="{FONT}" w:cs="{FONT}" w:eastAsia="{FONT}"/>
<w:sz w:val="21"/><w:szCs w:val="21"/><w:lang w:val="LANG"/></w:rPr></w:rPrDefault>
<w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="276" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:rPr><w:color w:val="1A1A1A"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>
<w:pPr><w:keepNext/><w:spacing w:before="0" w:after="120"/><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:sz w:val="40"/><w:szCs w:val="40"/><w:color w:val="000000"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>
<w:pPr><w:keepNext/><w:spacing w:before="420" w:after="120"/><w:outlineLvl w:val="1"/></w:pPr><w:rPr><w:b/><w:sz w:val="28"/><w:szCs w:val="28"/><w:color w:val="000000"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>
<w:pPr><w:keepNext/><w:spacing w:before="240" w:after="60"/><w:outlineLvl w:val="2"/></w:pPr><w:rPr><w:b/><w:sz w:val="22"/><w:szCs w:val="22"/><w:color w:val="333333"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="ListItem"><w:name w:val="List Item"/><w:basedOn w:val="Normal"/>
<w:pPr><w:tabs><w:tab w:val="left" w:pos="360"/></w:tabs><w:ind w:left="360" w:hanging="360"/><w:spacing w:after="60"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="Message"><w:name w:val="Message"/><w:basedOn w:val="Normal"/>
<w:pPr><w:ind w:left="480" w:right="480"/><w:spacing w:before="60" w:after="160"/></w:pPr><w:rPr><w:sz w:val="22"/><w:szCs w:val="22"/><w:color w:val="000000"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Small"><w:name w:val="Small"/><w:basedOn w:val="Normal"/>
<w:pPr><w:spacing w:after="80"/></w:pPr><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/><w:color w:val="555555"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="FormLine"><w:name w:val="Form Line"/><w:basedOn w:val="Normal"/>
<w:pPr><w:tabs><w:tab w:val="left" w:leader="underscore" w:pos="9000"/></w:tabs><w:spacing w:before="200" w:after="120"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="TableHead"><w:name w:val="Table Head"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:after="0"/></w:pPr><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/><w:color w:val="555555"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="TableText"><w:name w:val="Table Text"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:after="0" w:line="250" w:lineRule="auto"/></w:pPr><w:rPr><w:sz w:val="19"/><w:szCs w:val="19"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Footer"><w:name w:val="footer"/><w:basedOn w:val="Normal"/><w:pPr><w:jc w:val="right"/></w:pPr><w:rPr><w:sz w:val="16"/><w:color w:val="777777"/></w:rPr></w:style>
</w:styles>"""


def build(md, out_path, title=None, lang="en", paper="a4"):
    """lang and paper follow the founder: en-GB, en-US or plain en; a4 or letter."""
    found, body = convert(md)
    title = title or found or "Scope kit"
    letter = paper == "letter"
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
           'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
           f'<w:body>{body}<w:sectPr><w:footerReference w:type="default" r:id="rId2"/><w:pgSz w:w="{12240 if letter else 11906}" w:h="{15840 if letter else 16838}"/>'
           '<w:pgMar w:top="1250" w:right="1250" w:bottom="1250" w:left="1250" w:header="500" w:footer="500" w:gutter="0"/>'
           '</w:sectPr></w:body></w:document>')
    footer = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
              '<w:p><w:pPr><w:pStyle w:val="Footer"/></w:pPr>'
              '<w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText xml:space="preserve"> PAGE </w:instrText></w:r>'
              '<w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:t>1</w:t></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r></w:p></w:ftr>')
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    core = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            f'<dc:title>{escape(title)}</dc:title><dc:creator>Merigrove Scope Guard</dc:creator>'
            f'<dc:description>{CREDIT}</dc:description><cp:keywords>scope kit</cp:keywords>'
            f'<dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>'
            f'<dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified></cp:coreProperties>')
    app = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
           '<Application>Merigrove Scope Guard</Application></Properties>')
    ctypes = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
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
    doc_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
                '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>'
                '</Relationships>')
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ctypes)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", doc)
        z.writestr("word/styles.xml", STYLES.replace("LANG", lang))
        z.writestr("word/footer1.xml", footer)
        z.writestr("word/_rels/document.xml.rels", doc_rels)
        z.writestr("docProps/core.xml", core)
        z.writestr("docProps/app.xml", app)
    return title


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    try:
        title = None
        if "--title" in sys.argv:
            title = sys.argv[sys.argv.index("--title") + 1]
        md = open(sys.argv[1], encoding="utf-8").read()
        build(md, sys.argv[2], title)
        print(f"WROTE: {sys.argv[2]}")
    except OSError as e:
        print(f"STOP: the document could not be written ({e}). Nothing was written.")
        sys.exit(2)


if __name__ == "__main__":
    main()
