#!/usr/bin/env python3
"""Word files for Lead Magnet Factory, written with the standard library.

Builds the printable scorecard, the checklist, the one-page guide and the launch pack from the spec.
Called by magnet.py build; it can also run on its own for one file:
  python3 scripts/build_docx.py <spec.json> --what twin|checklist|guide|pack --out <file.docx>
Plain by design: one sans serif, black on white (or the founder's heading colour when it reads at 3 to 1 or
better on white), structure by space and type, no borders, no boxes. Paper size from the founder's country.
The file property reads "Made with Merigrove Lead Magnet Factory"; nothing is added to the pages.
Exit 0 written; 2 STOP. No network calls.
"""
import argparse
import datetime as dt
import os
import re
import sys
import zipfile
from xml.sax.saxutils import escape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

PAPER = {"A4": (11906, 16838), "Letter": (12240, 15840)}
LANG = {"british": "en-GB", "american": "en-US", "indian": "en-IN", "australian": "en-AU", "canadian": "en-CA"}
BOX = "☐"

STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="{font}" w:hAnsi="{font}" w:cs="{font}" w:eastAsia="{font}"/>
<w:sz w:val="21"/><w:szCs w:val="21"/>{lang}</w:rPr></w:rPrDefault>
<w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="276" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:rPr><w:color w:val="1A1A1A"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>
<w:pPr><w:keepNext/><w:spacing w:before="0" w:after="200" w:line="252" w:lineRule="auto"/><w:outlineLvl w:val="0"/></w:pPr>
<w:rPr><w:b/><w:sz w:val="44"/><w:szCs w:val="44"/><w:color w:val="{head}"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>
<w:pPr><w:keepNext/><w:spacing w:before="480" w:after="140"/><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:sz w:val="30"/><w:szCs w:val="30"/><w:color w:val="{head}"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>
<w:pPr><w:keepNext/><w:spacing w:before="320" w:after="100"/><w:outlineLvl w:val="1"/></w:pPr><w:rPr><w:b/><w:sz w:val="24"/><w:szCs w:val="24"/><w:color w:val="{head}"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Lead"><w:name w:val="Lead"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:after="200"/></w:pPr><w:rPr><w:sz w:val="26"/><w:szCs w:val="26"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Meta"><w:name w:val="Meta"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:after="60"/></w:pPr><w:rPr><w:color w:val="4D4D4D"/><w:sz w:val="19"/><w:szCs w:val="19"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Label"><w:name w:val="Label"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:before="160" w:after="40"/></w:pPr><w:rPr><w:b/><w:caps/><w:color w:val="4D4D4D"/><w:spacing w:val="10"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="ListItem"><w:name w:val="List Item"/><w:basedOn w:val="Normal"/>
<w:pPr><w:tabs><w:tab w:val="left" w:pos="360"/></w:tabs><w:ind w:left="360" w:hanging="360"/><w:spacing w:after="80"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="Option"><w:name w:val="Option"/><w:basedOn w:val="Normal"/>
<w:pPr><w:tabs><w:tab w:val="left" w:pos="780"/><w:tab w:val="right" w:pos="{right}"/></w:tabs><w:ind w:left="780" w:hanging="420"/><w:spacing w:after="50"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="Detail"><w:name w:val="Detail"/><w:basedOn w:val="Normal"/><w:pPr><w:ind w:left="420"/><w:spacing w:after="200"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="Body2"><w:name w:val="Email Body"/><w:basedOn w:val="Normal"/><w:pPr><w:ind w:left="0"/><w:spacing w:after="140"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="TableText"><w:name w:val="Table Text"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:after="0" w:line="252" w:lineRule="auto"/></w:pPr><w:rPr><w:sz w:val="19"/><w:szCs w:val="19"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Footer"><w:name w:val="footer"/><w:basedOn w:val="Normal"/><w:rPr><w:color w:val="6A6A6A"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr></w:style>
</w:styles>"""


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
    out = []
    for i, part in enumerate(str(text).split("\n")):
        if i:
            out.append(f"<w:r>{rpr}<w:br/></w:r>")
        segs = part.split("\t")
        for j, seg in enumerate(segs):
            if j:
                out.append(f"<w:r>{rpr}<w:tab/></w:r>")
            if seg:
                out.append(f'<w:r>{rpr}<w:t xml:space="preserve">{escape(seg)}</w:t></w:r>')
    return "".join(out)


class Doc:
    def __init__(self, spec):
        self.spec = spec
        self.body = []
        c = (spec.get("founder") or {}).get("country")
        self.paper = C.LN.locale_defaults(c)["paper"]
        look = spec.get("look") or {}
        self.font = (look.get("docx_font") or "Calibri").replace("<", "").replace("&", "")
        head = (look.get("accent") or "").lstrip("#")
        self.head = head.upper() if re.fullmatch(r"[0-9A-Fa-f]{6}", head) and C.contrast(head, "FFFFFF") >= 3 else "111111"
        self.lang = LANG.get(((spec.get("founder") or {}).get("spelling") or "").lower(), "")

    def p(self, content, style=None, keep=False, page_break=False, raw=False):
        ppr = []
        if style:
            ppr.append(f'<w:pStyle w:val="{style}"/>')
        if keep:
            ppr.append("<w:keepNext/>")
        if page_break:
            ppr.append("<w:pageBreakBefore/>")
        pp = f"<w:pPr>{''.join(ppr)}</w:pPr>" if ppr else ""
        self.body.append(f"<w:p>{pp}{content if raw else run(content)}</w:p>")

    def title(self, t):
        self.p(t, "Title", keep=True)

    def h1(self, t, page_break=False):
        self.p(t, "Heading1", keep=True, page_break=page_break)

    def h2(self, t):
        self.p(t, "Heading2", keep=True)

    def lead(self, t):
        self.p(t, "Lead")

    def meta(self, t, keep=False):
        self.p(t, "Meta", keep=keep)

    def label(self, t):
        self.p(t, "Label", keep=True)

    def text(self, t, bold=False, keep=False):
        self.p(run(t, bold=bold), keep=keep, raw=True)

    def paras(self, block, style=None, keep_last=0, keep_all=False):
        """keep_last: the last N paragraphs stay on the page with what follows (an email's close and sign-off)."""
        parts = [x.strip() for x in re.split(r"\n\s*\n", str(block or "").strip()) if x.strip()]
        for i, part in enumerate(parts):
            self.p(part, style, keep=keep_all or i >= len(parts) - keep_last)

    def pair(self, label, value, bold=False, keep=True):
        """A label and its value. keep=True holds the value with the next pair, so a short block never splits."""
        self.label(label)
        self.text(value, bold=bold, keep=keep)

    def bullets(self, items, mark="•", keep=False):
        for x in items:
            self.p(run(f"{mark}\t") + run(x), "ListItem", keep=keep, raw=True)

    def numbered(self, items):
        for i, x in enumerate(items, 1):
            self.p(run(f"{i}.\t") + run(x), "ListItem", raw=True)

    def box(self, t, bold=True, keep=True):
        self.p(run(f"{BOX}\t", size=26) + run(t, bold=bold), "ListItem", keep=keep, raw=True)

    def option(self, label, points=None):
        tail = (run("\t") + run(f"{points} point{'s' if points != 1 else ''}", colour="4D4D4D")) if points is not None else ""
        self.p(run(f"{BOX}\t", size=24) + run(label) + tail, "Option", raw=True)

    def detail(self, t):
        self.p(t, "Detail")

    def table(self, rows, widths):
        grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in widths)
        total = sum(widths)
        out = [f'<w:tbl><w:tblPr><w:tblW w:w="{total}" w:type="dxa"/><w:tblLayout w:type="fixed"/>'
               '<w:tblBorders><w:top w:val="nil"/><w:left w:val="nil"/><w:bottom w:val="nil"/><w:right w:val="nil"/>'
               '<w:insideH w:val="nil"/><w:insideV w:val="nil"/></w:tblBorders>'
               '<w:tblCellMar><w:top w:w="90" w:type="dxa"/><w:left w:w="0" w:type="dxa"/><w:bottom w:w="90" w:type="dxa"/>'
               f'<w:right w:w="200" w:type="dxa"/></w:tblCellMar><w:tblLook w:val="0000"/></w:tblPr><w:tblGrid>{grid}</w:tblGrid>']
        for ri, r in enumerate(rows):
            head = ri == 0
            trpr = "<w:trPr><w:tblHeader/><w:cantSplit/></w:trPr>" if head else "<w:trPr><w:cantSplit/></w:trPr>"
            cells = []
            for ci, c in enumerate(r):
                bold = head or ci == 0
                colour = "4D4D4D" if head else None
                cells.append(f'<w:tc><w:tcPr><w:tcW w:w="{widths[ci]}" w:type="dxa"/></w:tcPr>'
                             f'<w:p><w:pPr><w:pStyle w:val="TableText"/></w:pPr>{run(c, bold=bold, colour=colour)}</w:p></w:tc>')
            out.append(f"<w:tr>{trpr}{''.join(cells)}</w:tr>")
        out.append("</w:tbl>")
        self.body.append("".join(out))
        self.p("")

    @property
    def text_width(self):
        return PAPER[self.paper][0] - 2 * 1300

    def save(self, path, title, footer_left):
        pw, ph = PAPER[self.paper]
        sect = (f'<w:sectPr><w:footerReference w:type="default" r:id="rIdFooter"/><w:pgSz w:w="{pw}" w:h="{ph}"/>'
                '<w:pgMar w:top="1300" w:right="1300" w:bottom="1300" w:left="1300" w:header="600" w:footer="600" w:gutter="0"/>'
                '</w:sectPr>')
        doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
               '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
               'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
               f'<w:body>{"".join(self.body)}{sect}</w:body></w:document>')
        fld = lambda instr: (f'<w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText xml:space="preserve"> {instr} </w:instrText></w:r>'  # noqa: E731
                             '<w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:t>1</w:t></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r>')
        footer = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                  '<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                  f'<w:p><w:pPr><w:pStyle w:val="Footer"/><w:tabs><w:tab w:val="right" w:pos="{self.text_width}"/></w:tabs></w:pPr>'
                  f'{run(footer_left)}<w:r><w:tab/></w:r>{run("Page ")}{fld("PAGE")}{run(" of ")}{fld("NUMPAGES")}</w:p></w:ftr>')
        now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        f = self.spec.get("founder") or {}
        core = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
                'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
                'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
                f'<dc:title>{escape(title)}</dc:title><dc:creator>{escape(f.get("name") or "")}</dc:creator>'
                f'<dc:description>{C.CREDIT}</dc:description>'
                f'<dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>'
                f'<dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified></cp:coreProperties>')
        app = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
               '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
               f'<Application>Microsoft Office Word</Application><Company>{escape(f.get("business") or "")}</Company></Properties>')
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
                    '<Relationship Id="rIdFooter" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>'
                    '</Relationships>')
        styles = (STYLES.replace("{font}", escape(self.font)).replace("{head}", self.head)
                  .replace("{lang}", f'<w:lang w:val="{self.lang}"/>' if self.lang else "")
                  .replace("{right}", str(self.text_width)))
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml", ctypes)
            z.writestr("_rels/.rels", rels)
            z.writestr("word/document.xml", doc)
            z.writestr("word/styles.xml", styles)
            z.writestr("word/footer1.xml", footer)
            z.writestr("word/_rels/document.xml.rels", doc_rels)
            z.writestr("docProps/core.xml", core)
            z.writestr("docProps/app.xml", app)
        return path


def founder_line(spec):
    f = spec.get("founder") or {}
    return ", ".join(x for x in (f.get("name"), f.get("business")) if x)


def thresholds(q):
    pts = sorted(o["points"] for o in q["options"])
    lo, hi = pts[0], pts[-1]
    mid = [p for p in pts if hi == lo or (p - lo) / (hi - lo) >= 0.5]
    return min(mid)


# ------------------------------------------------------------------ the printable scorecard
def scorecard_twin(spec, path):
    m = spec["magnet"]
    d = Doc(spec)
    d.title(m["title"])
    d.lead(m["promise"])
    d.meta(m["who_for"])
    if m.get("who_not_for"):
        d.meta(m["who_not_for"])
    d.h1("How to score yourself")
    d.text("Tick one answer for each of the five questions and add up the points beside your answers. Find your total "
           "in the table after the questions. Then find your three lowest-scoring questions (if two tie, take the "
           "earlier one first) and read their lines under Fix these first. Your best two questions are what is working.")
    for i, q in enumerate(m["questions"], 1):
        if q.get("label"):
            d.label(q["label"])
        d.h2(f"{i}. {q['text']}")
        for o in q["options"]:
            d.option(o["label"], o["points"])
    fqs = m.get("fit_questions") or []
    if fqs:
        d.h1("Two last questions" if len(fqs) == 2 else "One last question")
        who = "we" if (spec.get("founder") or {}).get("we") else "I"
        d.meta(f"So {who} can point you to the right next step. These do not change your score.")
        for q in fqs:
            d.h2(q["text"])
            for o in q["options"]:
                d.option(o["label"])
    d.h1("Add up your score")
    hi = sum(max(o["points"] for o in q["options"]) for q in m["questions"])
    d.lead(f"Your total: ________ out of {hi}")
    tw = d.text_width
    rows = [["Score", "Where you are", "What it means"]]
    for t in m["tiers"]:
        rows.append([f"{t['min']} to {t['max']}", t["name"], t["description"]])
    d.table(rows, [int(tw * 0.14), int(tw * 0.24), tw - int(tw * 0.14) - int(tw * 0.24)])
    d.h1("What is working, and what to fix first")
    d.meta("For each question: the line to read depends on the points you ticked.")
    for i, q in enumerate(m["questions"], 1):
        th = thresholds(q)
        top = max(o["points"] for o in q["options"])
        d.h2(f"{i}. {q.get('label') or q['text']}")
        d.pair(f"What is working ({top} points)", q["strength"])
        if q.get("strength_mid") and th < top:
            span = f"{th} points" if th == top - 1 else f"{th} to {top - 1} points"
            d.pair(f"What is working ({span})", q["strength_mid"])
        d.pair(f"Fix this first (under {th} points)", q["fix_low"])
        d.pair(f"Tighten this ({th} points or more, but one of your three lowest)", q["fix_high"], keep=False)
    d.pair("If every question scored under the line", m["strength_fallback"], keep=False)
    d.h1("The question this leaves open")
    d.lead(m["door"]["question"])
    d.text(m["door"]["sentence"])
    d.h1("Your next step")
    cta = m.get("cta") or {}
    if cta.get("line"):
        d.text(cta["line"])
    if cta.get("line_top_tier") and m.get("tiers"):
        d.pair(f"If you scored in {m['tiers'][-1]['name']}", cta["line_top_tier"], keep=False)
    if cta.get("link"):
        d.text(f"{cta.get('label') or 'Book a call'}: {cta['link']}", bold=True)
    if fqs and m.get("not_a_fit"):
        nf = [o["label"] for q in fqs for o in q["options"] if o["fit"] is False]
        d.label("If you ticked " + " or ".join(f"\"{x}\"" for x in nf))
        d.text(m["not_a_fit"])
    d.meta(founder_line(spec))
    return d.save(path, m["title"], founder_line(spec))


# ------------------------------------------------------------------ checklist and guide
def checklist_doc(spec, path):
    c = spec["checklist"]
    d = Doc(spec)
    d.title(c["title"])
    d.lead(c["who_for"])
    if c.get("minutes"):
        d.meta(f"Takes about {c['minutes']} minutes to work through. Tick each box as you go.")
    n = 0
    for s in c["sections"]:
        items = [it for it in s["items"] if not it.get("need")]
        if not items:
            continue
        if s.get("heading"):
            d.h1(s["heading"])
        for it in items:
            n += 1
            d.box(f"{n}. {it['text']}")
            d.detail(it["detail"])
    d.h1("What this does not cover")
    d.text(c["not_covered"])
    d.h1("Your next step")
    d.text(c["next_step"])
    link = ((spec.get("offer") or {}).get("link") or "").strip()
    if link:
        d.text(link, bold=True)
    d.meta(founder_line(spec))
    return d.save(path, c["title"], founder_line(spec))


def guide_doc(spec, path):
    g = spec["guide"]
    d = Doc(spec)
    d.title(g["title"])
    d.meta(g["who_for"])
    d.lead(g["idea"])
    d.h1("How to do it")
    d.numbered([s.get("text") if isinstance(s, dict) else s for s in g["steps"]])
    d.h1(g["example_label"])
    d.paras(g["example"])
    d.h1("What this does not cover")
    d.text(g["not_covered"])
    d.h1("Your next step")
    d.text(g["next_step"])
    link = ((spec.get("offer") or {}).get("link") or "").strip()
    if link:
        d.text(link, bold=True)
    d.meta(founder_line(spec))
    return d.save(path, g["title"], founder_line(spec))


# ------------------------------------------------------------------ launch pack
CONSENT = ("Before you switch the emails on, check the consent and email marketing rules where you and your "
           "subscribers are, and set your email tool's sign-up form to match.")


def magnet_title(spec):
    fmt = spec["format"]
    if fmt == "scorecard":
        return spec["magnet"]["title"]
    return (spec.get(fmt) or {}).get("title") or "Lead magnet"


TAG_MEANING = {
    "{{first_name}}": "the reader's first name",
    "{{magnet_link}}": "the address of the {what}",
    "{{booking_link}}": "your booking page",
    "{{reply_address}}": "the address replies go to",
    "{{unsubscribe_link}}": "the unsubscribe link",
}


def merge_tag_line(spec):
    """One line naming every merge tag the emails use, each written in double braces exactly as in the emails."""
    what = "scorecard page" if spec.get("format") == "scorecard" else "file"
    alltext = " ".join(str(v) for e in (spec.get("launch") or {}).get("emails") or []
                       for v in (e.get("body"), e.get("ps"), e.get("preview"), " ".join(e.get("subjects") or [])))
    used = [t for t in TAG_MEANING if t in alltext]
    for t in ("{{first_name}}", "{{magnet_link}}"):
        if t not in used:
            used.insert(0, t)
    parts = [f"{t} is {TAG_MEANING[t].format(what=what)}" for t in TAG_MEANING if t in used]
    return ("; ".join(parts) + ". Swap them for your email tool's own tags. Your email tool adds the unsubscribe "
            "link: check it is on every email.")


def launch_pack(spec, path, sim=None, info=None, optin_built=False):
    info = info or {}
    fmt = spec["format"]
    la = spec["launch"]
    t = spec.get("topic") or {}
    names, day = C.file_names(spec)
    d = Doc(spec)
    title = magnet_title(spec)
    m = spec.get("magnet") or {}
    d.title(f"Launch pack: {title}")
    d.meta(f"For {founder_line(spec)}. Built {C.human_date(day, spec)}. This pack is for you and anyone helping you "
           "launch; it is not for readers.")

    # 1 Read first
    d.h1("1. Read first")
    d.label("The promise")
    d.text(la["optin"]["headline"])
    who_for = m.get("who_for") if fmt == "scorecard" else (spec.get(fmt) or {}).get("who_for")
    d.label("Who it is for")
    d.text(who_for or "")
    not_for = m.get("who_not_for") or m.get("not_a_fit") or (spec.get("offer") or {}).get("not_for")
    if not_for:
        d.label("Who it is not for")
        d.text(not_for)
    d.label("The one door it leaves open")
    door = (m.get("door") or {}).get("question") if fmt == "scorecard" else (spec.get(fmt) or {}).get("not_covered")
    d.text(door or t.get("not_given_away", ""))
    d.label("Three things to do to go live")
    host = (spec.get("hosting") or "").lower()
    if fmt == "scorecard":
        first = (f"Put {names['main']} on your own website as a page of its own (any site that lets you upload a "
                 "file or paste a page will do), and keep the printable version for anyone who asks for paper.")
        if "cannot" in host or "no site" in host or host == "none":
            first = (f"You said you cannot host a web page yet: send {names['twin']} (or a PDF of it) as the download "
                     "for now, and put the web page up when you have somewhere to host it.")
    else:
        first = f"Save {names['main']} as a PDF and upload it to your email tool or website as the download."
    d.numbered([first,
                "Connect your opt-in form (section 3) to your email tool and load the five emails (section 5) with "
                "the timing given.",
                "Test the whole path with five real people before you announce it (section 8)."])
    if t.get("drafted"):
        d.label("Read these as the expert")
        d.text(t["drafted"])
    d.label("Before you switch it on")
    d.text(CONSENT)

    # 2 Topic
    d.h1("2. The topic and why")
    d.label("The problem it takes on")
    d.text(t.get("problem", ""))
    d.label("Where it came from")
    if t.get("inferred"):
        d.text(f"Inferred, not quoted: {t.get('source', '')}. Confirm it is how your buyers say it.")
    else:
        d.text(f"“{t.get('source_line', '')}” ({t.get('source', 'your material')})")
    if t.get("runners_up"):
        d.label("The runners-up and why they lost")
        d.bullets([f"{r.get('topic')}: {r.get('why_not')}" for r in t["runners_up"]])
    d.label(f"Why a {'one-page guide' if fmt == 'guide' else fmt}")
    d.text(t.get("format_reason", ""))
    d.label("What it deliberately does not give away")
    d.text(t.get("not_given_away", ""))
    if t.get("previous"):
        d.label("What changed from your last lead magnet")
        d.text(t["previous"])
    if sim:
        d.label("How the scoring works")
        shares = "; ".join(f"{k}: {v:g}%" for k, v in sim["shares"].items())
        d.text(f"Scores run from {sim['min']} to {sim['max']}. Every one of the {sim['answer_sets']} possible answer "
               f"sets lands in exactly one tier ({shares}). Someone who picks the middle answer every time scores "
               f"{sim['middle_total']:g} and lands in {sim['middle_tier']}. These shares describe the arithmetic of "
               "the scoring, not real readers; your own readers will tell you where they land.")
        d.text("The result always shows what is working before what to fix, and a reader whose answers say the offer "
               "is not for them sees a plain line saying so in place of the call to action.")
    held = info.get("held") or []
    if held:
        d.label("Held back until you confirm them")
        d.bullets([f"{it.get('text')}: {it.get('need')}" for it in held])

    # 3 Opt-in
    op = la["optin"]
    d.h1("3. The opt-in page")
    if optin_built:
        d.meta(f"Built as {names['optin']}, posting to your own form address. The blocks are here too.", keep=True)
    else:
        d.meta("Paste these blocks into your website builder or your email tool's landing page. A ready page is "
               "built only from the form address or embed code your email tool gives you.", keep=True)
    d.pair("Headline", op["headline"], bold=True)
    d.pair("Subhead", op["subhead"])
    d.label("What they will see")
    d.bullets(op["bullets"], keep=True)
    d.pair("Form fields", ", ".join(op.get("fields") or ["First name", "Email"]))
    d.pair("Button", op["button"])
    d.pair("Under the button", op["expectation"], keep=bool(op.get("signoff_line")))
    if op.get("signoff_line"):
        d.pair("Sign-off line", op["signoff_line"], keep=False)

    # 4 Thank-you
    ty = la["thankyou"]
    d.h1("4. The thank-you page")
    d.pair("Headline", ty["headline"], bold=True)
    d.label("Body")
    d.paras(ty["body"], keep_all=True)
    what = "the scorecard page" if fmt == "scorecard" else "the file"
    d.pair("The link", f"{ty.get('link_label') or 'Open it now'}: link to {what} where you host it.")
    d.pair("One next step", ty["next_step"], keep=False)

    # 5 Emails
    rules = la.get("rules") or {}
    d.h1("5. The five emails", page_break=True)
    d.label("What starts it")
    d.text(rules.get("starts") or "Someone confirms their address on the opt-in form.")
    d.label("What stops it")
    d.bullets(rules.get("stops") or [])
    d.label("Remove before you switch it on")
    d.bullets(rules.get("remove_before") or [])
    days = rules.get("timing_days") or [0, 1, 3, 5, 7]
    d.label("Timing")
    d.text("Email " + ", email ".join(f"{i + 1} on day {x}" for i, x in enumerate(days)) +
           ". Day 0 is the day they opt in.")
    d.label("Merge tags")
    d.text(merge_tag_line(spec))
    for i, em in enumerate(la["emails"]):
        dd = days[i] if i < len(days) else ""
        d.h2(f"Email {i + 1}, day {dd}: {em.get('job')}")
        d.pair("Subject A", em["subjects"][0])
        d.pair("Subject B", em["subjects"][1])
        d.pair("Preview text", em["preview"])
        d.label("Body")
        d.paras(em["body"], "Body2", keep_last=2)
        has_ps = bool(em.get("ps"))
        d.text(em.get("signoff") or (spec.get("founder") or {}).get("signoff"), keep=has_ps)
        if has_ps:
            d.text(f"P.S. {em['ps']}")

    # 6 Result map
    d.h1("6. The result map", page_break=True)
    d.meta("For your calls. What a reader in each place is probably dealing with, the first question to ask, and the "
           "next step to offer." if fmt == "scorecard" else
           "For your calls and replies. What a reader's reply tells you, the first question to ask, and the next "
           "step to offer.")
    for r in la["result_map"]:
        d.h2(r["when"])
        d.pair("What they are probably dealing with", r["dealing_with"])
        d.pair("The first question to ask", r["ask"])
        d.pair("The next step to offer", r["next_step"], keep=False)

    # 7 Measure
    d.h1("7. What to measure, and when to rebuild")
    third = "readers who finish the scorecard" if fmt == "scorecard" else "readers who reply or book"
    d.text(f"Count three things each week: visits to the opt-in page, opt-ins, and {third}; then how many of those "
           "book a call. There is no benchmark here on purpose: the conversion figures that circulate online mostly come "
           "from companies that sell quiz tools, and none of them describes your audience. Your own first 60 days are the baseline.")
    d.text("The rebuild rule: if most of the people who opt in are the wrong people, change the title and the fit "
           "questions, not the traffic. If the right people opt in but nobody books, look at emails four and five "
           "first.")
    rows = [["Week", "Opt-in page visits", "Opt-ins", "Finished" if fmt == "scorecard" else "Replied", "Booked"]]
    rows += [[str(i), "", "", "", ""] for i in range(1, 9)]
    tw = d.text_width
    d.table(rows, [int(tw * 0.12)] + [int(tw * 0.22)] * 4)

    # 8 Go-live
    d.h1("8. Go-live checklist")
    items = []
    if fmt == "scorecard":
        items.append("The scorecard page is online at its own address and opens on a phone.")
        items.append("The printable version is saved as a PDF for anyone who asks for paper.")
    else:
        items.append("The file is saved as a PDF and the download link works.")
    items += ["The opt-in form is connected to your email tool and adds people to the five-email sequence.",
              "The thank-you page links to the " + ("scorecard page." if fmt == "scorecard" else "file."),
              "The five emails are loaded with the timing above, with your sign-off and an unsubscribe link on each.",
              "Current clients and anyone already in a conversation with you are removed or excluded first.",
              "Five real people have run the whole path: opted in, received email one, opened the link on a phone"
              + (", finished the scorecard and seen a result." if fmt == "scorecard" else ", and opened the file."),
              "You have checked that email one arrives in an inbox, not a spam folder, from at least two providers.",
              "Your booking link works and shows times you can keep." if (m.get("cta") or {}).get("link") or
              (spec.get("offer") or {}).get("link") else "You know who answers replies, and how fast.",
              "You have checked the consent and email marketing rules where you and your subscribers are."]
    items += la.get("golive") or []
    for it in items:
        d.box(it, bold=False, keep=False)
    return d.save(path, f"Launch pack: {title}", f"Launch pack: {title}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec")
    ap.add_argument("--what", required=True, choices=["twin", "checklist", "guide", "pack"])
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    spec = C.load_spec(a.spec)
    fn = {"twin": scorecard_twin, "checklist": checklist_doc, "guide": guide_doc, "pack": launch_pack}[a.what]
    print("WROTE:", fn(spec, a.out))
    return 0


if __name__ == "__main__":
    C.run_main(main)
