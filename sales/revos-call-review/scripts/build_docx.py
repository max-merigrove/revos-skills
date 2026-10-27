#!/usr/bin/env python3
"""Turn the review written by score_call.py render into a Word document.

Usage:
  python3 scripts/build_docx.py <review.md> <call-review-xx-yyyy-mm-dd.docx> [--results <results.json>]
                                [--paper A4|Letter] [--lang en-US]

Paper size comes from the founder's country (verdicts "country", via locale_numbers.locale_defaults), or, when the
country is not known, Letter for a founder who writes dates month day year and A4 otherwise. Proofing language comes
from the founder's spelling (verdicts "spelling"); when it is not known no language is set, so Word uses the reader's own.
--paper and --lang override both.

Supports # to ### headings, paragraphs, "- " bullets, "1. " numbered items with indented follow-on lines,
"> " quotes, pipe tables and **bold**. The document property "Made with Merigrove Call Review" is set;
nothing is added to the page itself. Standard library only (zipfile and XML escaping). No network.
Exit 0 written; exit 2 with a STOP line when the input is missing or empty.
"""
import argparse
import json
import os
import re
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import locale_numbers as LN  # noqa: E402
from datetime import datetime, timezone
from xml.sax.saxutils import escape

FONT = "Calibri"
PROPERTY = "Made with Merigrove Call Review"
PAPER = {"A4": (11906, 16838), "Letter": (12240, 15840)}
SPELLING_LANG = {"american": "en-US", "us": "en-US", "british": "en-GB", "uk": "en-GB", "indian": "en-IN",
                 "australian": "en-AU", "canadian": "en-CA", "new zealand": "en-NZ", "south african": "en-ZA",
                 "irish": "en-IE", "singapore": "en-SG", "singaporean": "en-SG", "nigerian": "en-NG", "kenyan": "en-KE",
                 "philippine": "en-PH", "filipino": "en-PH"}


def page_setup(results_path=None, paper=None, lang=None):
    """(paper name, language or None) from the founder's country and spelling, never from a UK default."""
    v = {}
    if results_path:
        try:
            v = (json.load(open(results_path, encoding="utf-8")) or {}).get("verdicts") or {}
        except (OSError, ValueError):
            v = {}
    if not paper:
        country = (v.get("country") or "").strip()
        if country:
            paper = LN.locale_defaults(country)["paper"]
        else:
            paper = "Letter" if v.get("date_style") == "month day year" else "A4"
    if not lang:
        lang = SPELLING_LANG.get(str(v.get("spelling") or "").strip().lower())
    return paper, lang


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


INLINE_RE = re.compile(r"(\*\*[^*]+\*\*)")


def inline(text, italic=False, size=None, colour=None):
    out = []
    for part in INLINE_RE.split(text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            out.append(run(part[2:-2], bold=True, italic=italic, size=size, colour=colour))
        else:
            out.append(run(part, italic=italic, size=size, colour=colour))
    return "".join(out)


def para(content, style=None, keep_next=False):
    ppr = []
    if style:
        ppr.append(f'<w:pStyle w:val="{style}"/>')
    if keep_next:
        ppr.append("<w:keepNext/>")
    p = f"<w:pPr>{''.join(ppr)}</w:pPr>" if ppr else ""
    return f"<w:p>{p}{content}</w:p>"


def table(rows):
    header, body = rows[0], rows[1:]
    ncol = len(header)
    total = 9300
    widths = [total // ncol] * ncol
    if ncol == 5:
        widths = [1900, 900, 900, 900, 4700] if header[1].lower() == "weight" else [1500, 900, 900, 2900, 3100]
    grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in widths)

    def cell(text, bold, w):
        return (f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/></w:tcPr>'
                f'{para(run(text, bold=True, size=18) if bold else inline(text, size=18), "TableText")}</w:tc>')
    out = ['<w:tbl><w:tblPr><w:tblW w:w="9300" w:type="dxa"/><w:tblLayout w:type="fixed"/><w:tblCellMar><w:top w:w="50" w:type="dxa"/>'
           '<w:left w:w="0" w:type="dxa"/><w:bottom w:w="50" w:type="dxa"/><w:right w:w="160" w:type="dxa"/>'
           f'</w:tblCellMar><w:tblLook w:val="0000"/></w:tblPr><w:tblGrid>{grid}</w:tblGrid>']
    out.append('<w:tr><w:trPr><w:tblHeader/></w:trPr>' + "".join(cell(c, True, widths[i]) for i, c in enumerate(header)) + "</w:tr>")
    for r in body:
        r = (r + [""] * ncol)[:ncol]
        out.append("<w:tr><w:trPr><w:cantSplit/></w:trPr>" + "".join(cell(c, False, widths[i]) for i, c in enumerate(r)) + "</w:tr>")
    out.append("</w:tbl>")
    out.append(para(""))
    return "".join(out)


def convert(md):
    lines = md.replace("\r\n", "\n").split("\n")
    body, i, title = [], 0, None
    while i < len(lines):
        s = lines[i].rstrip()
        if s.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|$", lines[i + 1].strip()):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                if not re.match(r"^\|[\s:|-]+\|$", lines[i].strip()):
                    rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            body.append(table(rows))
            continue
        m = re.match(r"^(#{1,3})\s+(.*)$", s)
        if m:
            level = len(m.group(1))
            if level == 1 and title is None:
                title = m.group(2).strip()
            body.append(para(inline(m.group(2).strip()), f"Heading{level}", keep_next=True))
            i += 1
            continue
        if not s.strip():
            i += 1
            continue
        if re.match(r"^\s{2,}\S", s):
            body.append(para(inline(s.strip()), "Detail"))
        elif re.match(r"^-\s+", s):
            body.append(para(run("\u2022\t") + inline(s[2:].strip()), "ListItem"))
        elif re.match(r"^\d{1,2}\.\s+", s):
            mm = re.match(r"^(\d{1,2})\.\s+(.*)$", s)
            body.append(para(run(mm.group(1) + ".\t", bold=True) + inline(mm.group(2)), "ListItem", keep_next=True))
        elif s.startswith(">"):
            body.append(para(inline(s.lstrip("> ").strip(), italic=True), "Quote"))
        elif re.match(r"^\[[^\]]+\]\s*\"", s):
            body.append(para(inline(s.strip(), italic=True), "Quote"))
        elif s.startswith("Say:") or s.startswith("Say instead:"):
            k = s.index(":")
            body.append(para(run(s[:k + 1] + " ", bold=True) + inline(s[k + 1:].strip()), "SayLine"))
        elif re.match(r"^(Mode|Confidence|Call): ", s):
            body.append(para(inline(s.strip(), size=18, colour="555555"), "Meta"))
        else:
            body.append(para(inline(s.strip())))
        i += 1
    return title, "".join(body)


STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="{font}" w:hAnsi="{font}" w:cs="{font}" w:eastAsia="{font}"/>
<w:sz w:val="21"/><w:szCs w:val="21"/>{lang}</w:rPr></w:rPrDefault>
<w:pPrDefault><w:pPr><w:spacing w:after="110" w:line="276" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:rPr><w:color w:val="1A1A1A"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>
<w:pPr><w:keepNext/><w:spacing w:before="0" w:after="160"/><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:sz w:val="36"/><w:szCs w:val="36"/><w:color w:val="000000"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>
<w:pPr><w:keepNext/><w:spacing w:before="360" w:after="100"/><w:outlineLvl w:val="1"/></w:pPr><w:rPr><w:b/><w:sz w:val="27"/><w:szCs w:val="27"/><w:color w:val="000000"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>
<w:pPr><w:keepNext/><w:spacing w:before="220" w:after="60"/><w:outlineLvl w:val="2"/></w:pPr><w:rPr><w:b/><w:sz w:val="23"/><w:szCs w:val="23"/><w:color w:val="222222"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="ListItem"><w:name w:val="List Item"/><w:basedOn w:val="Normal"/>
<w:pPr><w:tabs><w:tab w:val="left" w:pos="360"/></w:tabs><w:ind w:left="360" w:hanging="360"/><w:spacing w:after="60"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="Detail"><w:name w:val="Detail"/><w:basedOn w:val="Normal"/>
<w:pPr><w:ind w:left="360"/><w:spacing w:before="0" w:after="40"/></w:pPr><w:rPr><w:color w:val="333333"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Quote"><w:name w:val="Quote"/><w:basedOn w:val="Normal"/>
<w:pPr><w:ind w:left="360"/><w:spacing w:after="80"/></w:pPr><w:rPr><w:i/><w:color w:val="404040"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="SayLine"><w:name w:val="Say Line"/><w:basedOn w:val="Normal"/>
<w:pPr><w:ind w:left="360"/><w:spacing w:before="40" w:after="160"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="Meta"><w:name w:val="Meta"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:after="20"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="TableText"><w:name w:val="Table Text"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:after="0"/></w:pPr></w:style>
</w:styles>"""


def build(md_path, out_path, paper="A4", lang=None):
    if not os.path.exists(md_path) or os.path.getsize(md_path) == 0:
        print(f"STOP: there is no review at {md_path}. Run score_call.py render first. Nothing was written.")
        sys.exit(2)
    md = open(md_path, encoding="utf-8").read()
    title, body = convert(md)
    title = title or "Call review"
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
           'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
           f'<w:body>{body}<w:sectPr><w:pgSz w:w="{PAPER[paper][0]}" w:h="{PAPER[paper][1]}"/>'
           '<w:pgMar w:top="1250" w:right="1250" w:bottom="1250" w:left="1250" w:header="500" w:footer="500" w:gutter="0"/>'
           '</w:sectPr></w:body></w:document>')
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    core = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            f'<dc:title>{escape(title)}</dc:title><dc:creator>Merigrove Call Review</dc:creator>'
            f'<dc:description>{PROPERTY}</dc:description><cp:keywords>call review</cp:keywords>'
            f'<dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>'
            f'<dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified></cp:coreProperties>')
    app = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
           '<Application>Merigrove Call Review</Application></Properties>')
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
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ctypes)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", doc)
        z.writestr("word/styles.xml", STYLES.replace("{font}", FONT).replace(
            "{lang}", f'<w:lang w:val="{lang}"/>' if lang else ""))
        z.writestr("word/_rels/document.xml.rels", doc_rels)
        z.writestr("docProps/core.xml", core)
        z.writestr("docProps/app.xml", app)
    print(f"WROTE: {out_path} ({title}; {paper} paper, proofing language {lang or 'not set, the reader decides'})")


def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("input")
    a.add_argument("output")
    a.add_argument("--results", help="results.json from score_call.py; its verdicts give the country and spelling")
    a.add_argument("--paper", choices=sorted(PAPER))
    a.add_argument("--lang", help="proofing language such as en-US, en-GB or en-IN")
    args = a.parse_args()
    paper, lang = page_setup(args.results, args.paper, args.lang)
    if lang and not re.fullmatch(r"[a-z]{2}(-[A-Z]{2})?", lang):
        print(f"STOP: '{lang}' is not a language tag like en-US. Nothing was written.")
        sys.exit(2)
    try:
        build(args.input, args.output, paper, lang)
    except OSError as e:
        print(f"STOP: the document could not be written ({e}). Nothing was written.")
        sys.exit(2)


if __name__ == "__main__":
    main()
