#!/usr/bin/env python3
"""Turn a voice guide or cheat sheet written in plain markdown into a .docx.

Usage:
  python3 scripts/build_docx.py <input.md> <output.docx> [--title "Title"] [--compact]
          [--country US | --paper letter|a4]

Paper size comes from the founder's country (locale_numbers.locale_defaults: US Letter
for the US, Canada, Mexico, the Philippines and a few others, A4 elsewhere), never
from their spelling. --paper overrides it. With neither, the file is A4 and a line
says so, so the founder can be asked once.

Supports: # to #### headings, paragraphs (one per line), "- " bullets,
"1. " numbered items, "> " quotes, pipe tables, fenced code blocks,
**bold**, *italic*, `code`, and <!-- pagebreak -->. --compact sets tighter
spacing for a one-page cheat sheet. The document property "Made with
Merigrove Brand Voice" is set; nothing is added to the page itself.
Standard library only (zipfile and xml escaping). No network.
"""
import argparse
import os
import re
import sys
import zipfile
from datetime import datetime, timezone
from xml.sax.saxutils import escape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from locale_numbers import locale_defaults  # noqa: E402

PAPER = {"a4": (11906, 16838), "letter": (12240, 15840)}

FONT = "Calibri"
MONO = "Consolas"


def run(text, bold=False, italic=False, mono=False, size=None, colour=None):
    props = []
    if mono:
        props.append(f'<w:rFonts w:ascii="{MONO}" w:hAnsi="{MONO}" w:cs="{MONO}"/>')
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


INLINE_RE = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`|(?<![\w*])\*[^*\s][^*]*\*(?![\w*]))")


def inline(text, base_italic=False, size=None, colour=None):
    out = []
    for part in INLINE_RE.split(text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            out.append(run(part[2:-2], bold=True, italic=base_italic, size=size, colour=colour))
        elif part.startswith("`") and part.endswith("`"):
            out.append(run(part[1:-1], mono=True, size=size, colour=colour))
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            out.append(run(part[1:-1], italic=True, size=size, colour=colour))
        else:
            out.append(run(part, italic=base_italic, size=size, colour=colour))
    return "".join(out)


def para(content, style=None, keep_next=False, spacing=None, indent=None):
    ppr = []
    if style:
        ppr.append(f'<w:pStyle w:val="{style}"/>')
    if keep_next:
        ppr.append("<w:keepNext/>")
    if spacing:
        ppr.append(spacing)
    if indent:
        ppr.append(indent)
    p = f"<w:pPr>{''.join(ppr)}</w:pPr>" if ppr else ""
    return f"<w:p>{p}{content}</w:p>"


def table(rows):
    header, body = rows[0], rows[1:]
    ncol = len(header)
    width = 9000 // max(1, ncol)
    grid = "".join(f'<w:gridCol w:w="{width}"/>' for _ in range(ncol))
    def cell(text, bold):
        return (f'<w:tc><w:tcPr><w:tcW w:w="{width}" w:type="dxa"/></w:tcPr>'
                f'{para(inline(text) if not bold else run(text, bold=True), "TableText")}</w:tc>')
    out = [f'<w:tbl><w:tblPr><w:tblW w:w="0" w:type="auto"/><w:tblCellMar><w:top w:w="40" w:type="dxa"/>'
           f'<w:left w:w="0" w:type="dxa"/><w:bottom w:w="40" w:type="dxa"/><w:right w:w="160" w:type="dxa"/>'
           f'</w:tblCellMar><w:tblLook w:val="0000"/></w:tblPr><w:tblGrid>{grid}</w:tblGrid>']
    out.append("<w:tr>" + "".join(cell(c, True) for c in header) + "</w:tr>")
    for r in body:
        r = (r + [""] * ncol)[:ncol]
        out.append("<w:tr>" + "".join(cell(c, False) for c in r) + "</w:tr>")
    out.append("</w:tbl>")
    out.append(para("", spacing='<w:spacing w:after="60"/>'))
    return "".join(out)


LEAD_RE = re.compile(r"^(Never|Rule \d+|Trait \d+|Tone axis \d+|Ceiling|Edge case|Signature phrase)(:)\s*(.*)$")


def piped(s, bullet=False):
    """'Never: x | instead: y | stated 2026-10-20' becomes a lead line and indented labelled detail lines."""
    parts = [x.strip() for x in s.split(" | ")]
    lead, rest = parts[0], parts[1:]
    m = LEAD_RE.match(lead)
    head = run("\u2022\t") if bullet else ""
    if m:
        head += run(m.group(1) + m.group(2) + " ", bold=True) + inline(m.group(3))
    else:
        head += inline(lead)
    out = [para(head, "ListItem" if bullet else None, keep_next=bool(rest))]
    for k, r in enumerate(rest):
        km = re.match(r"^([a-z][a-z ]{1,24}):\s*(.*)$", r)
        content = (run(km.group(1) + ": ", italic=True) + inline(km.group(2))) if km else inline(r)
        out.append(para(content, "Detail", keep_next=k < len(rest) - 1))
    return "".join(out)


def convert(md):
    lines = md.replace("\r\n", "\n").split("\n")
    body, i, title = [], 0, None
    num = 0
    while i < len(lines):
        line = lines[i]
        s = line.rstrip()
        if s.strip() == "<!-- pagebreak -->":
            body.append('<w:p><w:r><w:br w:type="page"/></w:r></w:p>')
            i += 1
            continue
        if s.startswith("```"):
            i += 1
            block = []
            while i < len(lines) and not lines[i].startswith("```"):
                block.append(lines[i])
                i += 1
            i += 1
            for b in block:
                body.append(para(run(b, mono=True, size=18) if b else "", "Code"))
            continue
        if s.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|$", lines[i + 1].strip()):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                if not re.match(r"^\|[\s:|-]+\|$", lines[i].strip()):
                    rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            body.append(table(rows))
            continue
        m = re.match(r"^(#{1,4})\s+(.*)$", s)
        if m:
            level = len(m.group(1))
            text = m.group(2).strip()
            if level == 1 and title is None:
                title = text
            body.append(para(inline(text), f"Heading{level}", keep_next=True))
            num = 0
            i += 1
            continue
        if not s.strip():
            i += 1
            continue
        if s.strip().endswith("(measured)"):
            s = s.strip()[:-len("(measured)")].rstrip()
        if re.match(r"^\s*[-*]\s+", s):
            item = re.sub(r"^\s*[-*]\s+", "", s)
            if " | " in item:
                body.append(piped(item, bullet=True))
            else:
                body.append(para(run("\u2022\t") + inline(item), "ListItem"))
            i += 1
            continue
        mn = re.match(r"^\s*(\d{1,2})[.)]\s+(.*)$", s)
        if mn:
            body.append(para(run(mn.group(1) + ".\t") + inline(mn.group(2)), "ListItem"))
            i += 1
            continue
        if s.startswith(">"):
            q = s.lstrip("> ").strip()
            q = re.sub(r"\[([^\]]*)\]\s*$", lambda m_: "(" + m_.group(1).replace(" | ", ", ") + ")", q)
            body.append(para(inline(q, base_italic=True), "Quote"))
            i += 1
            continue
        if " | " in s:
            body.append(piped(s.strip()))
        else:
            body.append(para(inline(s.strip())))
        i += 1
    return title, "".join(body)


STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="{font}" w:hAnsi="{font}" w:cs="{font}" w:eastAsia="{font}"/>
<w:sz w:val="{size}"/><w:szCs w:val="{size}"/><w:lang w:val="en-GB"/></w:rPr></w:rPrDefault>
<w:pPrDefault><w:pPr><w:spacing w:after="{after}" w:line="{line}" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:rPr><w:color w:val="1A1A1A"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>
<w:pPr><w:keepNext/><w:spacing w:before="0" w:after="{h1after}"/><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:sz w:val="{h1}"/><w:szCs w:val="{h1}"/><w:color w:val="000000"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>
<w:pPr><w:keepNext/><w:spacing w:before="{h2before}" w:after="{h2after}"/><w:outlineLvl w:val="1"/></w:pPr><w:rPr><w:b/><w:sz w:val="{h2}"/><w:szCs w:val="{h2}"/><w:color w:val="000000"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>
<w:pPr><w:keepNext/><w:spacing w:before="{h3before}" w:after="60"/><w:outlineLvl w:val="2"/></w:pPr><w:rPr><w:b/><w:sz w:val="{h3}"/><w:szCs w:val="{h3}"/><w:color w:val="333333"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading4"><w:name w:val="heading 4"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>
<w:pPr><w:keepNext/><w:spacing w:before="120" w:after="40"/><w:outlineLvl w:val="3"/></w:pPr><w:rPr><w:i/><w:color w:val="333333"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="ListItem"><w:name w:val="List Item"/><w:basedOn w:val="Normal"/>
<w:pPr><w:tabs><w:tab w:val="left" w:pos="360"/></w:tabs><w:ind w:left="360" w:hanging="360"/><w:spacing w:after="{listafter}"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="Detail"><w:name w:val="Detail"/><w:basedOn w:val="Normal"/>
<w:pPr><w:ind w:left="720"/><w:spacing w:before="0" w:after="20"/></w:pPr><w:rPr><w:color w:val="555555"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Quote"><w:name w:val="Quote"/><w:basedOn w:val="Normal"/>
<w:pPr><w:ind w:left="360"/></w:pPr><w:rPr><w:i/><w:color w:val="404040"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Code"><w:name w:val="Code"/><w:basedOn w:val="Normal"/>
<w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/><w:ind w:left="0"/></w:pPr><w:rPr><w:rFonts w:ascii="{mono}" w:hAnsi="{mono}" w:cs="{mono}"/><w:sz w:val="18"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="TableText"><w:name w:val="Table Text"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:after="0"/></w:pPr></w:style>
</w:styles>"""


def build(md_path, out_path, title=None, compact=False, paper="a4"):
    md = open(md_path, encoding="utf-8").read()
    found_title, body = convert(md)
    title = title or found_title or "Voice guide"
    margin = 1150 if compact else 1300
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
           'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
           f'<w:body>{body}<w:sectPr><w:pgSz w:w="{PAPER[paper][0]}" w:h="{PAPER[paper][1]}"/>'
           f'<w:pgMar w:top="{margin}" w:right="{margin}" w:bottom="{margin}" w:left="{margin}" w:header="500" w:footer="500" w:gutter="0"/>'
           '</w:sectPr></w:body></w:document>')
    sizes = dict(font=FONT, mono=MONO, size=22 if compact else 21, after=130 if compact else 120, line=290 if compact else 276,
                 h1=44 if compact else 44, h1after=200 if compact else 160, h2=23 if compact else 28, h2before=140 if compact else 360,
                 h2after=40 if compact else 100, h3=20 if compact else 23, h3before=80 if compact else 200, listafter=60 if compact else 60)
    styles = STYLES
    for k, v in sizes.items():
        styles = styles.replace("{" + k + "}", str(v))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    core = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            f'<dc:title>{escape(title)}</dc:title><dc:creator>Merigrove Brand Voice</dc:creator>'
            '<dc:description>Made with Merigrove Brand Voice</dc:description><cp:keywords>voice guide</cp:keywords>'
            f'<dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>'
            f'<dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified></cp:coreProperties>')
    app = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
           '<Application>Merigrove Brand Voice</Application></Properties>')
    ctypes = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
              '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
              '<Default Extension="xml" ContentType="application/xml"/>'
              '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
              '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
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
                '</Relationships>')
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ctypes)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", doc)
        z.writestr("word/styles.xml", styles)
        z.writestr("word/_rels/document.xml.rels", doc_rels)
        z.writestr("docProps/core.xml", core)
        z.writestr("docProps/app.xml", app)
    print(f"Wrote {out_path} ({title}, {'US Letter' if paper == 'letter' else 'A4'})")


def main():
    a = argparse.ArgumentParser()
    a.add_argument("input")
    a.add_argument("output")
    a.add_argument("--title")
    a.add_argument("--compact", action="store_true")
    a.add_argument("--country", help="two-letter country code from what the founder said; sets the paper size")
    a.add_argument("--paper", choices=["a4", "letter"], help="overrides the country")
    args = a.parse_args()
    if args.paper:
        paper = args.paper
    elif args.country:
        paper = locale_defaults(args.country)["paper"].lower()
    else:
        paper = "a4"
        print("NOTE: no country given, so the file is A4; pass --country (or --paper letter) if the founder uses US Letter")
    try:
        build(args.input, args.output, args.title, args.compact, paper)
    except OSError as e:
        print(f"Cannot build the document: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()
