#!/usr/bin/env python3
"""Write a small .xlsx workbook with live formulas and their current values. Standard library only.

Imported by scope_kit.py. Each cell is (value, style) or ("=FORMULA", style, cached_value). Formulas carry
the value the script worked out, so a preview that does not calculate still shows figures, and Excel,
Numbers, Google Sheets and LibreOffice recalculate on open (fullCalcOnLoad).
Styles: text, bold, head, input_text, input_money, input_hours, money, hours, pct, small, input_choice.
"""
import re
import zipfile
from xml.sax.saxutils import escape

STYLE_IDS = {"text": 0, "bold": 1, "head": 2, "input_text": 3, "input_money": 4, "input_hours": 5,
             "money": 6, "hours": 7, "pct": 8, "small": 9, "input_choice": 10, "title": 11, "money2": 12, "input_date": 13}


def col_letter(n):
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def styles_xml(symbol, sign_after=False, date_order="dmy"):
    """Number formats follow the founder: the sign before or after the figure (9.800 € or $9,800); the separators are
    the reader's own spreadsheet settings. Dates show in the founder's order."""
    sym = escape(symbol)
    if sym and sign_after:
        money_fmt, money2_fmt = f'#,##0\\ &quot;{sym}&quot;', f'#,##0.00\\ &quot;{sym}&quot;'
    else:
        money_fmt, money2_fmt = f'&quot;{sym}&quot;#,##0', f'&quot;{sym}&quot;#,##0.00'
    date_fmt = "mmm d, yyyy" if date_order == "mdy" else "d mmm yyyy"
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<numFmts count="5"><numFmt numFmtId="164" formatCode="{money_fmt}"/><numFmt numFmtId="165" formatCode="0.0#"/><numFmt numFmtId="166" formatCode="0%"/><numFmt numFmtId="167" formatCode="{money2_fmt}"/><numFmt numFmtId="168" formatCode="{date_fmt}"/></numFmts>
<fonts count="4"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font>
<font><sz val="9"/><color rgb="FF555555"/><name val="Calibri"/></font><font><b/><sz val="14"/><name val="Calibri"/></font></fonts>
<fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FFFFF2B3"/><bgColor indexed="64"/></patternFill></fill></fills>
<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="14">
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>
<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>
<xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1" applyAlignment="1"><alignment vertical="bottom" wrapText="1"/></xf>
<xf numFmtId="0" fontId="0" fillId="2" borderId="0" xfId="0" applyFill="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>
<xf numFmtId="164" fontId="0" fillId="2" borderId="0" xfId="0" applyNumberFormat="1" applyFill="1"/>
<xf numFmtId="165" fontId="0" fillId="2" borderId="0" xfId="0" applyNumberFormat="1" applyFill="1"/>
<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
<xf numFmtId="165" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
<xf numFmtId="166" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
<xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>
<xf numFmtId="0" fontId="0" fillId="2" borderId="0" xfId="0" applyFill="1"/>
<xf numFmtId="0" fontId="3" fillId="0" borderId="0" xfId="0" applyFont="1"/>
<xf numFmtId="167" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
<xf numFmtId="168" fontId="0" fillId="2" borderId="0" xfId="0" applyNumberFormat="1" applyFill="1"/>
</cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>"""


def _cell(ref, spec):
    if spec is None:
        return ""
    if not isinstance(spec, tuple):
        spec = (spec, "text")
    value, style = spec[0], spec[1]
    s = STYLE_IDS[style]
    if isinstance(value, str) and value.startswith("="):
        cached = spec[2] if len(spec) > 2 else None
        f = escape(value[1:])
        if isinstance(cached, (int, float)) and not isinstance(cached, bool):
            return f'<c r="{ref}" s="{s}"><f>{f}</f><v>{cached!r}</v></c>'
        if isinstance(cached, str):
            return f'<c r="{ref}" s="{s}" t="str"><f>{f}</f><v>{escape(cached)}</v></c>'
        return f'<c r="{ref}" s="{s}"><f>{f}</f></c>'
    if value is None or value == "":
        return f'<c r="{ref}" s="{s}"/>' if style.startswith("input") else ""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f'<c r="{ref}" s="{s}"><v>{value!r}</v></c>'
    return f'<c r="{ref}" s="{s}" t="inlineStr"><is><t xml:space="preserve">{escape(str(value))}</t></is></c>'


def sheet_xml(rows, widths, validations=None, freeze_row=None, paper="a4"):
    out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
           'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">']
    if freeze_row:
        out.append(f'<sheetViews><sheetView workbookViewId="0"><pane ySplit="{freeze_row}" topLeftCell="A{freeze_row + 1}" '
                   'activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>')
    out.append("<cols>" + "".join(f'<col min="{i}" max="{i}" width="{w}" customWidth="1"/>' for i, w in enumerate(widths, 1)) + "</cols>")
    out.append("<sheetData>")
    for r, row in enumerate(rows, 1):
        cells = "".join(_cell(f"{col_letter(c)}{r}", spec) for c, spec in enumerate(row, 1))
        out.append(f'<row r="{r}">{cells}</row>')
    out.append("</sheetData>")
    if validations:
        out.append(f'<dataValidations count="{len(validations)}">')
        for rng, options in validations:
            lst = ",".join(options)
            out.append(f'<dataValidation type="list" allowBlank="1" showErrorMessage="1" sqref="{rng}">'
                       f'<formula1>"{escape(lst)}"</formula1></dataValidation>')
        out.append("</dataValidations>")
    out.append('<pageMargins left="0.5" right="0.5" top="0.6" bottom="0.6" header="0.3" footer="0.3"/>')
    out.append(f'<pageSetup orientation="landscape" paperSize="{1 if paper == "letter" else 9}" fitToWidth="1" fitToHeight="0"/>')
    out.append("</worksheet>")
    return "".join(out)


def write(path, sheets, symbol="", title="Workbook", credit="Made with Merigrove", paper="a4", sign_after=False, date_order="dmy"):
    """sheets: list of dicts {name, rows, widths, validations, freeze_row}. symbol is the founder's currency sign
    (none when unknown); paper is "a4" or "letter", following the founder."""
    names = [re.sub(r"[\[\]:*?/\\]", "", s["name"])[:31] for s in sheets]
    wb = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
          'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
          + "".join(f'<sheet name="{escape(n)}" sheetId="{i}" r:id="rId{i}"/>' for i, n in enumerate(names, 1))
          + '</sheets><calcPr calcId="191029" fullCalcOnLoad="1"/></workbook>')
    wb_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
               '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
               + "".join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>'
                         for i in range(1, len(sheets) + 1))
               + f'<Relationship Id="rId{len(sheets) + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
               '</Relationships>')
    ctypes = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
              '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
              '<Default Extension="xml" ContentType="application/xml"/>'
              '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
              '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
              + "".join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                        for i in range(1, len(sheets) + 1))
              + '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
              '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
            '</Relationships>')
    core = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/">'
            f'<dc:title>{escape(title)}</dc:title><dc:creator>Merigrove Scope Guard</dc:creator>'
            f'<dc:description>{escape(credit)}</dc:description></cp:coreProperties>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ctypes)
        z.writestr("_rels/.rels", rels)
        z.writestr("docProps/core.xml", core)
        z.writestr("xl/workbook.xml", wb)
        z.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        z.writestr("xl/styles.xml", styles_xml(symbol, sign_after, date_order))
        for i, s in enumerate(sheets, 1):
            z.writestr(f"xl/worksheets/sheet{i}.xml",
                       sheet_xml(s["rows"], s.get("widths", []), s.get("validations"), s.get("freeze_row"), paper))
