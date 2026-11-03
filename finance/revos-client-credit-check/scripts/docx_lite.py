#!/usr/bin/env python3
"""A small Word (.docx) writer using only the Python standard library.

Enough for a one-page client credit brief: a title, headings, paragraphs, bullets and plain tables,
set small enough to fit one page. Opens in Word, Pages, Google Docs and LibreOffice. No network calls.
"""
import zipfile
from datetime import datetime, timezone
from xml.sax.saxutils import escape

W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'

STYLES_T = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:sz w:val="{SZ}"/><w:szCs w:val="{SZ}"/><w:lang w:val="{LANG}"/></w:rPr></w:rPrDefault>
<w:pPrDefault><w:pPr><w:spacing w:after="50" w:line="240" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:after="20"/></w:pPr><w:rPr><w:b/><w:sz w:val="30"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:before="60" w:after="20"/><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:sz w:val="40"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:before="110" w:after="30"/><w:outlineLvl w:val="1"/></w:pPr><w:rPr><w:b/><w:sz w:val="{H2}"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Small"><w:name w:val="Small"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:after="20"/></w:pPr><w:rPr><w:color w:val="555555"/><w:sz w:val="{SM}"/><w:szCs w:val="{SM}"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Email"><w:name w:val="Email"/><w:basedOn w:val="Normal"/><w:pPr><w:ind w:left="360"/><w:spacing w:after="0"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="Bullet"><w:name w:val="Bullet"/><w:basedOn w:val="Normal"/><w:pPr><w:ind w:left="240" w:hanging="160"/><w:spacing w:after="10"/></w:pPr></w:style>
<w:style w:type="table" w:styleId="Plain"><w:name w:val="Plain"/><w:tblPr><w:tblCellMar><w:top w:w="20" w:type="dxa"/><w:left w:w="60" w:type="dxa"/><w:bottom w:w="20" w:type="dxa"/><w:right w:w="60" w:type="dxa"/></w:tblCellMar></w:tblPr></w:style>
</w:styles>"""

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
</Types>"""

RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
</Relationships>"""

DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""


def _run(text, bold=False):
    rpr = "<w:rPr><w:b/></w:rPr>" if bold else ""
    return f'<w:r>{rpr}<w:t xml:space="preserve">{escape(text)}</w:t></w:r>'


class Document:
    def __init__(self, locale=None, paper="A4", size=19):
        """locale is the founder's English (the language tag); paper comes from their country, never from spelling."""
        loc = str(locale or "").strip().replace("_", "-")
        self.lang = loc if loc else "en"
        self.letter = str(paper or "").lower() == "letter"
        self.size = size
        self.body = []
        self.text = []  # plain text copy, for checks and tests

    def _p(self, text, style=None, bold=False):
        ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
        self.body.append(f"<w:p>{ppr}{_run(text, bold)}</w:p>")
        self.text.append(text)

    def title(self, text):
        self._p(text, "Title")

    def h1(self, text):
        self._p(text, "Heading1")

    def h2(self, text):
        self._p(text, "Heading2")

    def para(self, text, style=None, bold=False):
        for chunk in str(text).split("\n\n"):
            self._p(chunk.replace("\n", " "), style, bold)

    def bullet(self, text):
        self._p("•  " + text, "Bullet")

    def email(self, to, subject, body):
        if to:
            self._p(f"To: {to}", "Email", bold=False)
        self._p(f"Subject: {subject}", "Email", bold=True)
        self._p("", "Email")
        for line in body.split("\n"):
            self._p(line, "Email")
        self._p("")

    def table(self, rows, widths=None, header=True):
        out = ['<w:tbl><w:tblPr><w:tblStyle w:val="Plain"/><w:tblW w:w="5000" w:type="pct"/><w:tblLayout w:type="fixed"/></w:tblPr>']
        if widths:
            out.append("<w:tblGrid>" + "".join(f'<w:gridCol w:w="{w}"/>' for w in widths) + "</w:tblGrid>")
        for i, row in enumerate(rows):
            out.append("<w:tr>")
            for j, cell in enumerate(row):
                shade = '<w:shd w:val="clear" w:color="auto" w:fill="F0F0F0"/>' if header and i == 0 else ""
                bold = header and i == 0
                wd = f'<w:tcW w:w="{widths[j]}" w:type="dxa"/>' if widths and j < len(widths) else ""
                out.append(f'<w:tc><w:tcPr>{wd}{shade}</w:tcPr><w:p><w:pPr><w:spacing w:after="0"/></w:pPr>'
                           f'<w:r><w:rPr>{"<w:b/>" if bold else ""}<w:sz w:val="{self.size - 1}"/><w:szCs w:val="{self.size - 1}"/></w:rPr><w:t xml:space="preserve">{escape(str(cell))}</w:t></w:r></w:p></w:tc>')
                self.text.append(str(cell))
            out.append("</w:tr>")
        out.append("</w:tbl>")
        self.body.append("".join(out))

    def save(self, path, title="", description="", creator=""):
        doc = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {W}><w:body>'
               + "".join(self.body)
               + ('<w:sectPr><w:pgSz w:w="12240" w:h="15840"/>' if self.letter else '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>')
               + '<w:pgMar w:top="680" w:right="794" w:bottom="680" w:left="794" w:header="340" w:footer="340" w:gutter="0"/></w:sectPr>'
               + "</w:body></w:document>")
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        core = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
                'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
                'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
                f"<dc:title>{escape(title)}</dc:title><dc:subject>{escape(description)}</dc:subject><dc:creator>{escape(creator)}</dc:creator>"
                f"<dc:description>{escape(description)}</dc:description>"
                f'<dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created></cp:coreProperties>')
        tmp = str(path) + ".part"
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml", CONTENT_TYPES)
            z.writestr("_rels/.rels", RELS)
            z.writestr("word/_rels/document.xml.rels", DOC_RELS)
            z.writestr("word/document.xml", doc)
            z.writestr("word/styles.xml", STYLES_T.replace("{LANG}", escape(self.lang)).replace("{SZ}", str(self.size))
                       .replace("{SM}", str(self.size - 3)).replace("{H2}", str(self.size + 3)))
            z.writestr("docProps/core.xml", core)
        import os
        os.replace(tmp, path)
        return path


def docx_text(path):
    """Plain text of a .docx written by this module (for tests)."""
    import re
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    paras = re.findall(r"<w:p>(.*?)</w:p>", xml)
    from xml.sax.saxutils import unescape
    return "\n".join(unescape("".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", p))) for p in paras)
