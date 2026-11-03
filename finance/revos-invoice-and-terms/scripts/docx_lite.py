#!/usr/bin/env python3
"""A small Word (.docx) writer using only the Python standard library, for invoices and the terms page.

Paragraphs with styled runs, tables with set column widths and right-aligned cells, a footer with page
numbers, an optional logo (PNG or JPEG), paper size and document properties. Opens in Word, Pages,
Google Docs and LibreOffice. No network calls.
"""
import os
import re
import struct
import zipfile
from datetime import datetime, timezone
from xml.sax.saxutils import escape

NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
      'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
      'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
      'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"')
PAPER = {"A4": (11906, 16838), "Letter": (12240, 15840)}
MARGIN = 1080  # 0.75 inch, left and right
MARGIN_TB = 820  # about 0.57 inch, top and bottom, so a full invoice fits one page


def _hex(c):
    c = str(c or "").strip().lstrip("#")
    return c.upper() if re.fullmatch(r"[0-9A-Fa-f]{6}", c) else None


def run(text, bold=False, size=None, colour=None, italic=False):
    rpr = ""
    if bold:
        rpr += "<w:b/>"
    if italic:
        rpr += "<w:i/>"
    if colour and _hex(colour):
        rpr += f'<w:color w:val="{_hex(colour)}"/>'
    if size:
        rpr += f'<w:sz w:val="{int(size * 2)}"/><w:szCs w:val="{int(size * 2)}"/>'
    rpr = f"<w:rPr>{rpr}</w:rPr>" if rpr else ""
    parts = str(text).split("\n")
    out = []
    for i, p in enumerate(parts):
        if i:
            out.append("<w:r><w:br/></w:r>")
        out.append(f'<w:r>{rpr}<w:t xml:space="preserve">{escape(p)}</w:t></w:r>')
    return "".join(out)


def para(runs, align=None, after=80, before=0, keep=False):
    ppr = f'<w:spacing w:before="{before}" w:after="{after}"/>'
    if align in ("right", "center"):
        ppr += f'<w:jc w:val="{"right" if align == "right" else "center"}"/>'
    if keep:
        ppr = "<w:keepNext/>" + ppr
    return f"<w:p><w:pPr>{ppr}</w:pPr>{runs}</w:p>"


def image_size(data):
    """(width, height) in pixels for PNG or JPEG, else None."""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        w, h = struct.unpack(">II", data[16:24])
        return w, h, "png"
    if data[:2] == b"\xff\xd8":
        i = 2
        while i < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xC0, 0xC1, 0xC2):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                return w, h, "jpeg"
            seg = struct.unpack(">H", data[i + 2:i + 4])[0]
            i += 2 + seg
    return None


class Document:
    def __init__(self, paper="A4", lang="en", font=None):
        self.paper = paper if paper in PAPER else "A4"
        self.lang = lang or "en"
        self.font = font or "Arial"
        self.body = []
        self.text = []
        self.media = []  # (name, bytes, kind)
        self.footer_text = ""
        self.width = PAPER[self.paper][0] - 2 * MARGIN

    def add(self, xml, text=None):
        self.body.append(xml)
        if text is not None:
            self.text.append(text)

    def p(self, text, bold=False, size=None, colour=None, align=None, after=80, before=0, italic=False, keep=False):
        self.add(para(run(text, bold, size, colour, italic), align, after, before, keep), str(text))

    def spacer(self, pts=6):
        self.add(f'<w:p><w:pPr><w:spacing w:before="0" w:after="{int(pts * 20)}"/></w:pPr></w:p>')

    def table(self, rows, widths, align=None, bold_rows=(), sizes=None, rule_after=(), rule_top=(), colours=None,
              header=False, cell_after=40):
        """rows: list of lists of text (or list of (text, opts) tuples). widths: fractions of the text width."""
        tw = [int(self.width * w) for w in widths]
        grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in tw)
        out = [f'<w:tbl><w:tblPr><w:tblW w:w="{sum(tw)}" w:type="dxa"/><w:tblLayout w:type="fixed"/>'
               '<w:tblCellMar><w:top w:w="30" w:type="dxa"/><w:left w:w="0" w:type="dxa"/>'
               '<w:bottom w:w="30" w:type="dxa"/><w:right w:w="100" w:type="dxa"/></w:tblCellMar></w:tblPr>'
               f"<w:tblGrid>{grid}</w:tblGrid>"]
        for ri, row in enumerate(rows):
            trpr = "<w:trPr><w:cantSplit/>" + ("<w:tblHeader/>" if header and ri == 0 else "") + "</w:trPr>"
            out.append(f"<w:tr>{trpr}")
            for ci, cell in enumerate(row):
                opts = cell if isinstance(cell, dict) else {"t": cell}
                txt = str(opts.get("t", ""))
                al = opts.get("align") or (align[ci] if align else None)
                b = opts.get("b", ri in bold_rows)
                sz = opts.get("size") or (sizes[ri] if sizes and ri < len(sizes) and sizes[ri] else 9.5)
                col = opts.get("colour") or (colours[ri] if colours and ri < len(colours) else None)
                borders = ""
                if opts.get("norule"):
                    pass
                elif ri in rule_after:
                    borders += '<w:bottom w:val="single" w:sz="4" w:space="0" w:color="999999"/>'
                if ri in rule_top and not opts.get("norule"):
                    borders += '<w:top w:val="single" w:sz="4" w:space="0" w:color="999999"/>'
                tcpr = f'<w:tcW w:w="{tw[ci]}" w:type="dxa"/>' + (f"<w:tcBorders>{borders}</w:tcBorders>" if borders else "")
                if opts.get("paras"):
                    inner = "".join(para(run(str(q.get("t", "")), q.get("b", False), q.get("size") or 9.5, q.get("colour")),
                                         q.get("align") or al, q.get("after", 30)) for q in opts["paras"])
                    out.append(f"<w:tc><w:tcPr>{tcpr}</w:tcPr>{inner}</w:tc>")
                    self.text.extend(str(q.get("t", "")) for q in opts["paras"])
                    continue
                out.append(f"<w:tc><w:tcPr>{tcpr}</w:tcPr>{para(run(txt, b, sz, col), al, cell_after)}</w:tc>")
                self.text.append(txt)
            out.append("</w:tr>")
        out.append("</w:tbl>")
        self.add("".join(out))

    def logo(self, path, max_w_cm=4.5, max_h_cm=2.0):
        """Add a logo at the top, scaled to fit. Returns False if the file cannot be used."""
        try:
            data = open(path, "rb").read()
        except OSError:
            return False
        info = image_size(data)
        if not info:
            return False
        w, h, kind = info
        emu_cm = 360000
        scale = min(max_w_cm * emu_cm / w, max_h_cm * emu_cm / h)
        cx, cy = int(w * scale), int(h * scale)
        n = len(self.media) + 1
        name = f"logo{n}.{'png' if kind == 'png' else 'jpeg'}"
        self.media.append((name, data, kind))
        rid = f"rIdImg{n}"
        xml = (f'<w:p><w:pPr><w:spacing w:after="120"/></w:pPr><w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0">'
               f'<wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="{n}" name="Logo {n}"/>'
               '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
               f'<pic:pic><pic:nvPicPr><pic:cNvPr id="{n}" name="{name}"/><pic:cNvPicPr/></pic:nvPicPr>'
               f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
               f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
               '</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>')
        self.add(xml)
        return True

    def footer(self, text, page_word="Page", of_word="of"):
        self.footer_text = text
        self.page_word, self.of_word = page_word, of_word

    def save(self, path, title="", author="", description="", keywords=""):
        pw, ph = PAPER[self.paper]
        fref = '<w:footerReference w:type="default" r:id="rIdFooter"/>'
        sect = (f'<w:sectPr>{fref}'
                f'<w:pgSz w:w="{pw}" w:h="{ph}"/><w:pgMar w:top="{MARGIN_TB}" w:right="{MARGIN}" w:bottom="{MARGIN_TB}" '
                f'w:left="{MARGIN}" w:header="400" w:footer="400" w:gutter="0"/></w:sectPr>')
        doc = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {NS}><w:body>'
               + "".join(self.body) + sect + "</w:body></w:document>")
        fld = lambda instr: (f'<w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText xml:space="preserve"> {instr} </w:instrText></w:r>'
                             '<w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:rPr><w:sz w:val="15"/></w:rPr><w:t>1</w:t></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r>')
        footer = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:ftr {NS}>'
                  f'<w:p><w:pPr><w:tabs><w:tab w:val="right" w:pos="{self.width}"/></w:tabs></w:pPr>'
                  f'<w:r><w:rPr><w:color w:val="666666"/><w:sz w:val="15"/></w:rPr><w:t xml:space="preserve">{escape(self.footer_text or "")}</w:t></w:r>'
                  f'<w:r><w:rPr><w:sz w:val="15"/></w:rPr><w:tab/><w:t xml:space="preserve">{escape(getattr(self, "page_word", "Page"))} </w:t></w:r>'
                  + fld("PAGE") + f'<w:r><w:rPr><w:sz w:val="15"/></w:rPr><w:t xml:space="preserve"> {escape(getattr(self, "of_word", "of"))} </w:t></w:r>' + fld("NUMPAGES")
                  + "</w:p></w:ftr>")
        styles = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles {NS}><w:docDefaults><w:rPrDefault><w:rPr>'
                  f'<w:rFonts w:ascii="{escape(self.font)}" w:hAnsi="{escape(self.font)}" w:cs="{escape(self.font)}" w:eastAsia="{escape(self.font)}"/>'
                  f'<w:sz w:val="19"/><w:szCs w:val="19"/><w:lang w:val="{escape(self.lang)}"/></w:rPr></w:rPrDefault>'
                  '<w:pPrDefault><w:pPr><w:spacing w:after="80" w:line="264" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>'
                  '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style></w:styles>')
        media_types = "".join(f'<Default Extension="{ext}" ContentType="image/{ext}"/>' for ext in sorted({m[0].rsplit(".", 1)[1] for m in self.media}))
        ctypes = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                  '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                  '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                  '<Default Extension="xml" ContentType="application/xml"/>' + media_types +
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
        doc_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
                    '<Relationship Id="rIdFooter" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>'
                    + "".join(f'<Relationship Id="rIdImg{i + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/{m[0]}"/>'
                              for i, m in enumerate(self.media)) + "</Relationships>")
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        core = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
                'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
                'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
                f"<dc:title>{escape(title)}</dc:title><dc:creator>{escape(author)}</dc:creator>"
                f"<dc:description>{escape(description)}</dc:description><cp:keywords>{escape(keywords)}</cp:keywords>"
                f'<dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created></cp:coreProperties>')
        tmp = str(path) + ".part"
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml", ctypes)
            z.writestr("_rels/.rels", rels)
            z.writestr("word/_rels/document.xml.rels", doc_rels)
            z.writestr("word/document.xml", doc)
            z.writestr("word/styles.xml", styles)
            z.writestr("word/footer1.xml", footer)
            z.writestr("docProps/core.xml", core)
            for name, data, _k in self.media:
                z.writestr(f"word/media/{name}", data)
        os.replace(tmp, path)
        return path


def docx_text(path):
    """The visible text of any .docx, one paragraph per line (table cells are separate paragraphs)."""
    from xml.sax.saxutils import unescape
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    out = []
    for p in re.findall(r"<w:p[ >].*?</w:p>|<w:p/>", xml, re.S):
        bits = re.findall(r"<w:t(?: [^>]*)?>(.*?)</w:t>|(<w:br/>)|(<w:tab/>)", p, re.S)
        s = "".join(t if t else ("\n" if br else "\t") for t, br, tab in bits)
        out.append(unescape(s))
    return "\n".join(out)


def docx_props(path):
    with zipfile.ZipFile(path) as z:
        return z.read("docProps/core.xml").decode("utf-8")
