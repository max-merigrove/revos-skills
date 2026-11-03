#!/usr/bin/env python3
"""Writes and checks "Price rise letters <date>.docx" for The Price Rise Pack.

Usage:
  python3 scripts/letters.py check <letters.docx> <results.json>
        merge check (no empty field, no stray bracket), the new fee and the date in the first three
        lines of every letter, the reason matching the plan, HOLD on every letter with a [NEED],
        and the banned patterns. Prints PROBLEM lines and a count; exit 1 on any problem.
  python3 scripts/letters.py text <letters.docx>
        prints the plain text of the document

rise_plan.py build calls build() here; you do not run it by hand. Standard library only: the
.docx is written with zipfile and plain XML (headings, paragraphs, page breaks, one table per
page at most, a footer with the founder's business name). No network calls.
"""
import json
import re
import sys
import zipfile
from datetime import date, timedelta
from pathlib import Path
from xml.sax.saxutils import escape, unescape

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from dates import is_working_day  # noqa: E402

W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" ' \
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
UNIT = {"month": "a month", "quarter": "a quarter", "year": "a year", "project": "a project", "week": "a week"}

STYLES = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles {W}>
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:sz w:val="21"/><w:szCs w:val="21"/><w:lang w:val="LANG"/></w:rPr></w:rPrDefault>
<w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="276" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:after="80"/></w:pPr><w:rPr><w:b/><w:sz w:val="36"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:before="240" w:after="120"/><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:sz w:val="30"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:before="240" w:after="80"/><w:outlineLvl w:val="1"/></w:pPr><w:rPr><w:b/><w:sz w:val="23"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Small"><w:name w:val="Small"/><w:basedOn w:val="Normal"/><w:rPr><w:color w:val="555555"/><w:sz w:val="18"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Status"><w:name w:val="Status"/><w:basedOn w:val="Normal"/><w:rPr><w:b/><w:sz w:val="20"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Letter"><w:name w:val="Letter"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:after="160"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="Bullet"><w:name w:val="Bullet"/><w:basedOn w:val="Normal"/><w:pPr><w:ind w:left="360" w:hanging="240"/><w:spacing w:after="60"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="Footer"><w:name w:val="footer"/><w:basedOn w:val="Normal"/><w:rPr><w:color w:val="777777"/><w:sz w:val="16"/></w:rPr></w:style>
</w:styles>"""

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>
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
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>
</Relationships>"""


class Doc:
    def __init__(self, lang="en", paper="A4"):
        self.lang, self.letter_paper = lang, str(paper).lower() == "letter"
        self.body, self.text = [], []

    def p(self, text, style=None, bold=False):
        ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
        rpr = "<w:rPr><w:b/></w:rPr>" if bold else ""
        self.body.append(f'<w:p>{ppr}<w:r>{rpr}<w:t xml:space="preserve">{escape(str(text))}</w:t></w:r></w:p>')
        self.text.append(str(text))

    def title(self, t):
        self.p(t, "Title")

    def h1(self, t):
        self.p(t, "Heading1")

    def h2(self, t):
        self.p(t, "Heading2")

    def bullet(self, t):
        self.p("•  " + t, "Bullet")

    def numbered(self, n, t):
        self.p(f"{n}.  {t}", "Bullet")

    def page_break(self):
        self.body.append('<w:p><w:r><w:br w:type="page"/></w:r></w:p>')
        self.text.append("\f")

    def table(self, rows):
        out = ['<w:tbl><w:tblPr><w:tblW w:w="5000" w:type="pct"/><w:tblCellMar><w:top w:w="50" w:type="dxa"/>'
               '<w:left w:w="80" w:type="dxa"/><w:bottom w:w="50" w:type="dxa"/><w:right w:w="80" w:type="dxa"/>'
               '</w:tblCellMar></w:tblPr>']
        for i, row in enumerate(rows):
            out.append("<w:tr>")
            for cell in row:
                shade = '<w:shd w:val="clear" w:color="auto" w:fill="EFEFEF"/>' if i == 0 else ""
                out.append(f'<w:tc><w:tcPr>{shade}</w:tcPr><w:p><w:pPr><w:spacing w:after="0"/></w:pPr><w:r><w:rPr>'
                           f'{"<w:b/>" if i == 0 else ""}<w:sz w:val="17"/></w:rPr><w:t xml:space="preserve">'
                           f'{escape(str(cell))}</w:t></w:r></w:p></w:tc>')
            out.append("</w:tr>")
            self.text.append(" | ".join(str(x) for x in row))
        out.append("</w:tbl>")
        self.body.append("".join(out))
        self.p("")

    def save(self, path, title, footer):
        size = '<w:pgSz w:w="12240" w:h="15840"/>' if self.letter_paper else '<w:pgSz w:w="11906" w:h="16838"/>'
        doc = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {W}><w:body>' + "".join(self.body)
               + f'<w:sectPr><w:footerReference w:type="default" r:id="rId2"/>{size}<w:pgMar w:top="1134" '
               'w:right="1134" w:bottom="1134" w:left="1134" w:header="567" w:footer="567" w:gutter="0"/></w:sectPr>'
               "</w:body></w:document>")
        foot = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:ftr {W}><w:p><w:pPr><w:pStyle w:val="Footer"/>'
                f'</w:pPr><w:r><w:t xml:space="preserve">{escape(footer)}</w:t></w:r></w:p></w:ftr>')
        core = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><cp:coreProperties '
                'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
                'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
                'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
                f'<dc:title>{escape(title)}</dc:title><dc:creator>Made with Merigrove Price Rise Pack</dc:creator>'
                f'<dc:description>Made with Merigrove Price Rise Pack</dc:description></cp:coreProperties>')
        tmp = str(path) + ".part"
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml", CONTENT_TYPES)
            z.writestr("_rels/.rels", RELS)
            z.writestr("word/_rels/document.xml.rels", DOC_RELS)
            z.writestr("word/document.xml", doc)
            z.writestr("word/styles.xml", STYLES.replace("LANG", escape(self.lang)))
            z.writestr("word/footer1.xml", foot)
            z.writestr("docProps/core.xml", core)
        import os
        os.replace(tmp, path)


def docx_text(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    out = []
    body = re.sub(r"<w:tbl>.*?</w:tbl>", "", xml, flags=re.S)
    for p in re.findall(r"<w:p>(.*?)</w:p>", body, re.S):
        if 'w:type="page"' in p:
            out.append("\f")
            continue
        out.append(unescape("".join(re.findall(r"<w:t(?:\s[^>]*)?>(.*?)</w:t>", p, re.S))))
    for row in re.findall(r"<w:tr>(.*?)</w:tr>", xml, re.S):
        out.append(" | ".join(unescape("".join(re.findall(r"<w:t(?:\s[^>]*)?>(.*?)</w:t>", c, re.S)))
                              for c in re.findall(r"<w:tc>(.*?)</w:tc>", row, re.S)))
    return "\n".join(out)


# ====================================================================== words
def _d(st, iso, weekday=False):
    return st.d(date.fromisoformat(iso), weekday=weekday) if iso else ""


TITLES = re.compile(r"^(frau|herr|dr|prof|mr|mrs|ms|mx|miss|madame|monsieur|mme|m|señora?|sra?|sig(nora?)?|"
                    r"mevrouw|meneer|dhr|mevr)\.?\s", re.I)


def greeting(c):
    """'Hi Sarah,' for a first name; 'Dear Frau Dr. Weiß,' when the founder gave a title; else 'Hello,'."""
    who = str(c.get("contact") or "").strip()
    if not who:
        return "Hello,"
    return f"Dear {who}," if TITLES.match(who + " ") else f"Hi {who},"


def reply_by(res, c):
    send = date.fromisoformat(res["send"])
    eff = date.fromisoformat(c["eff1"])
    rb = eff - timedelta(days=14)
    return max(rb, send + timedelta(days=7))


def letter_lines(res, st, c):
    """The letter for one client: (subject, [lines]). Fee and date sit in the first three lines."""
    fw = res["fee_word"]
    unit = UNIT.get(c["per"], "")
    d1 = _d(st, c["eff1"])
    old, s1 = st.money(c["fee"]), st.money(c["step1"]) if c["step1"] is not None else "[NEED: the fee]"
    greet = greeting(c)
    same = c.get("same_line") or "the work, the way we work together and how you are invoiced"
    rb = st.d(reply_by(res, c))
    seg = c["segment"]
    lines = []
    if seg == "Two steps":
        subject = f"Your {fw} from {d1}"
        lines.append(f"From {d1}, your {fw} will be {s1} {unit}, up from {old}, and from {_d(st, c['eff2'])} it will be "
                     f"{st.money(c['step2'])}.")
        lines.append("I am giving you both dates now so you can plan ahead.")
    elif seg == "At renewal":
        subject = f"Your {fw} when we renew on {d1}"
        te = f" on {_d(st, c['term_end'])}" if c.get("term_end") else ""
        lines.append(f"When your current term ends{te}, your {fw} from {d1} will be {s1} {unit}, up from {old}.")
    elif seg == "Reset the scope":
        subject = f"Your {fw} from {d1}: two options"
        inc = c.get("scope_b_hours")
        inc_t = st.num(inc, 0 if inc and float(inc).is_integer() else 1) if inc else "[NEED: hours]"
        rate = st.money(c["extras_rate"]) if c.get("extras_rate") else "[NEED: your hourly fee for extra work]"
        lines.append(f"From {d1}, your {fw} moves to one of two options.")
        lines.append(f"Option A: the same work as today for {s1} {unit}, up from {old}.")
        now_h = f" (the work currently runs to about {st.num(c['hours'], 0 if float(c['hours']).is_integer() else 1)} hours a month)" if c.get("hours") else ""
        lines.append(f"Option B: {old} {unit} as now, for a defined {inc_t} hours a month{now_h}, with anything beyond "
                     f"that at {rate} an hour, agreed with you before it starts.")
    elif seg == "Price to keep":
        subject = f"Your {fw} from {d1}"
        lines.append(f"From {d1}, your {fw} will be {s1} {unit}, up from {old}.")
    else:
        subject = f"Your {fw} from {d1}"
        lines.append(f"From {d1}, your {fw} will be {s1} {unit}, up from {old}.")
    if c.get("reason"):
        lines.append(c["reason"])
    if seg == "Price to keep":
        lines.append(f"That is the {fw} at which I can keep doing this work for you.")
        lines.append(f"If it does not fit your plans, tell me by {rb} and we will agree how to finish the current work.")
    elif seg == "Reset the scope":
        lines.append(f"Everything else stays as it is: {c.get('same_line') or 'the way we work together and how you are invoiced'}.")
        lines.append(f"Reply with A or B by {rb}. If I have not heard from you by then, Option A applies from {d1}.")
    elif seg == "At renewal":
        lines.append(f"Everything else stays as it is: {same}.")
        lines.append(f"Reply to confirm you would like to renew on that basis, or to find a time to talk it through "
                     f"before {rb}.")
    elif c["per"] == "project":
        lines.append(f"Everything else stays as it is: {same}.")
        lines.append(f"Projects already agreed keep today's {fw}; the new {fw} applies to projects agreed from {d1}. "
                     f"If you would like to talk it through first, reply to this email and we will find a time before {rb}.")
    else:
        lines.append(f"Everything else stays as it is: {same}.")
        lines.append(f"If you are happy to carry on, there is nothing you need to do: the new {fw} will be on the "
                     f"invoice dated {d1}. If you would like to talk it through first, reply to this email and we will "
                     f"find a time before {rb}.")
    if c.get("since_year"):
        lines.append(f"Thank you for the work we have done together since {c['since_year']}.")
    lines.append(res.get("sign_off") or "[your name]")
    return subject, greet, [localise_line(x, st) for x in lines]


def localise_line(t, st):
    from rise_plan import localise
    return localise(t, st.american)


def template_for(seg, fw):
    m = {
        "Raise now": [f"From [effective date], your {fw} will be [new fee] [a month], up from [current fee].",
                      "[the one reason]",
                      "Everything else stays as it is: [what stays the same].",
                      f"If you are happy to carry on, there is nothing you need to do: the new {fw} will be on the invoice "
                      "dated [effective date]. If you would like to talk it through first, reply to this email and we "
                      "will find a time before [reply-by date]."],
        "Two steps": [f"From [step 1 date], your {fw} will be [step 1 fee] [a month], up from [current fee], and from "
                      "[step 2 date] it will be [step 2 fee].",
                      "I am giving you both dates now so you can plan ahead.", "[the one reason]",
                      "Everything else stays as it is: [what stays the same].", "[the choice, as in Raise now]"],
        "At renewal": [f"When your current term ends, your {fw} from [renewal date] will be [new fee] [a month], up "
                       "from [current fee].", "[the one reason]", "Everything else stays as it is: [what stays the same].",
                       "Reply to confirm you would like to renew on that basis, or to find a time to talk it through "
                       "before [reply-by date]."],
        "Reset the scope": [f"From [effective date], your {fw} moves to one of two options.",
                            "Option A: the same work as today for [new fee] [a month], up from [current fee].",
                            "Option B: [current fee] [a month] as now, for a defined [included hours] hours a month, "
                            "with anything beyond that at [your hourly fee] an hour, agreed with you before it starts.",
                            "[the one reason: what has grown]",
                            "Reply with A or B by [reply-by date]. If I have not heard from you by then, Option A "
                            "applies from [effective date]."],
        "Price to keep": [f"From [effective date], your {fw} will be [fee to keep] [a month], up from [current fee].",
                          "[the one reason]", f"That is the {fw} at which I can keep doing this work for you.",
                          "If it does not fit your plans, tell me by [reply-by date] and we will agree how to finish "
                          "the current work."],
    }
    return m.get(seg, [])


SEND_RULE = {
    "Raise now": "Notice terms confirmed; the reason is one you gave; the client is not mid-way through a deadline you know of.",
    "Two steps": "As Raise now, and you are content to commit to both dates now.",
    "At renewal": "The renewal date is right and the change is not inside the notice period.",
    "Reset the scope": "You have set the hours Option B includes and your hourly fee for extra work.",
    "Price to keep": "You would genuinely be content if they chose to finish rather than pay it.",
}


# ====================================================================== build
def footer_text(res, what):
    """The founder's own footer: their business and the document, never the tool that made it."""
    return f"{res['business']}, {what}" if res.get("business") else what[0].upper() + what[1:]


def build_return(res, st, path):
    """Return run: what happened, the confirmations to send, and the next wave."""
    from rise_plan import localise, outcome_verdict
    am = st.american
    L = lambda t: localise(t, am)  # noqa: E731
    lang = "en-US" if am else "en-GB" if res.get("country") in ("GB", "IE") else "en"
    doc = Doc(lang, res.get("paper", "A4"))
    fw = res["fee_word"]
    o = res["outcomes"]
    plan = {c["name"]: c for c in res["clients"]}
    doc.title("Price rise follow-up" + (f": {res['business']}" if res["business"] else ""))
    doc.p(L(f"Letters went on {st.d(date.fromisoformat(res['send']), weekday=True)}. Figures cover the "
            f"{res['window_months']} months to {st.d(date.fromisoformat(res['window_end']))}."), "Small")
    doc.h1("1. What happened")
    doc.p(L(outcome_verdict(o, st)))
    rows = [["Client", "Result", "Realised in the window", "Planned", "Difference"]]
    for r in o["rows"]:
        rows.append([r["client"], r["result"], st.money(r["realised12"]), st.money(r["planned12"]), st.money(r["diff"])])
    rows.append(["Total", "", st.money(o["realised12"]), st.money(o["planned12"]), st.money(o["diff"])])
    doc.table(rows)
    for r in o["rows"]:
        if r.get("if_paid_new"):
            from rise_plan import leaver_line
            doc.p(L(leaver_line(r, st)))
    if o["refill"]:
        doc.p(L(f"Only if you refill the freed hours at {st.money(res['hour_value'])} an hour: "
                f"{st.money(o['refill'])} in the window. Not counted above."))
    if o["exceptions"]:
        doc.p("Concessions, each with its end date (also on the Exceptions sheet):", bold=True)
        for e in o["exceptions"]:
            doc.bullet(L(f"{e['client']}: {e['what']}. Ends {st.d(date.fromisoformat(e['until']))}. Costs "
                         f"{st.money(e['cost'])} against the plan in the window."))
    doc.page_break()
    doc.h1("2. Confirmations to send")
    doc.p(L("One short note to each client who agreed different terms, so the terms are in writing with their end date."))
    any_conf = False
    for r in o["rows"]:
        if r["result"] != "countered":
            continue
        any_conf = True
        c = plan[r["client"]]
        greet = greeting(c)
        terms = r["terms"]
        doc.h2(r["client"])
        ex = next((e for e in o["exceptions"] if e["client"] == r["client"]), None)
        doc.p(f"Subject: {L('Confirming your ' + fw)}", bold=True)
        doc.p(greet, "Letter")
        unit = UNIT.get(c["per"], "")
        # Terms at today's fee are a stay, not a change: say "stays at" and the date it ends, never a start date.
        changes = [(date.fromisoformat(fr), f) for fr, f in terms if abs(f - c["fee"]) > 0.005]
        if not changes:
            until = f" until {st.d(date.fromisoformat(ex['until']))}, when we will review it together" if ex else ""
            doc.p(L(f"Confirming what we agreed: your {fw} stays at {st.money(c['fee'])} {unit}{until}."), "Letter")
        else:
            first_from, first_fee = changes[0]
            if first_from > date.fromisoformat(c["eff1"]) or len(changes) < len(terms):
                doc.p(L(f"Confirming what we agreed: your {fw} stays at {st.money(c['fee'])} until "
                        f"{st.d(first_from - timedelta(days=1))}, and from {st.d(first_from)} it is "
                        f"{st.money(first_fee)} {unit}."), "Letter")
            else:
                until = (f", until {st.d(date.fromisoformat(ex['until']))}, when we will review it together"
                         if ex and len(changes) == 1 else "")
                doc.p(L(f"Confirming what we agreed: from {st.d(first_from)} your {fw} is {st.money(first_fee)} "
                        f"{unit}{until}."), "Letter")
            for fr, f in changes[1:]:
                doc.p(L(f"From {st.d(fr)} it is {st.money(f)}."), "Letter")
        doc.p(L("Everything else stays as it is. Thank you for working this through with me."), "Letter")
        doc.p(res.get("sign_off") or "[your name]", "Letter")
    if not any_conf:
        doc.p("No client agreed different terms, so there is nothing to confirm.")
    doc.page_break()
    doc.h1("3. The next wave")
    if o["next_wave"]:
        for n in o["next_wave"]:
            when = st.d(date.fromisoformat(n["when"])) if n.get("when") else "at your annual review"
            doc.bullet(L(f"{n['client']}: {when}. {n['why'][0].upper() + n['why'][1:]}."))
    else:
        doc.p("Nobody is below target. Check again when your new-client price changes.")
    left = [r["client"] for r in o["rows"] if r["result"] == "left"]
    if left:
        doc.p(L(f"Not in the next wave: {', '.join(left)} (left). Nobody already moved is raised again before their "
                f"review date."))
    doc.p(L("Check what your contracts and the rules where you and your clients are say about changing a price and "
            "giving notice; if your clients are individuals rather than businesses, check that too."))
    doc.p(L("Planning, not advice."), "Small")
    doc.save(path, "Price rise follow-up", footer_text(res, "price rise follow-up"))
    return path


def build(res, st, path):
    from rise_plan import localise
    if res.get("outcomes"):
        return build_return(res, st, path)
    am = st.american
    L = lambda t: localise(t, am)  # noqa: E731
    lang = "en-US" if am else "en-GB" if res.get("country") in ("GB", "IE") else "en"
    doc = Doc(lang, res.get("paper", "A4"))
    fw = res["fee_word"]
    cl = res["clients"]
    to_write = [c for c in cl if c["segment"] != "Hold"]
    held = [c for c in cl if c["segment"] == "Hold"]
    send = date.fromisoformat(res["send"])
    doc.title("Price rise letters" + (f": {res['business']}" if res["business"] else ""))
    doc.p(f"Letters go on {st.d(send, weekday=True)}" + (" (assumed: confirm the date)" if res["send_assumed"] else "")
          + f". {len(to_write)} letter{'s' if len(to_write) != 1 else ''}"
          + (f"; held, no letter: {', '.join(c['name'] for c in held)}" if held else "") + ".", "Small")

    doc.p(L("In this document: 1 How to send these; 2 The call outline; 3 The letters by group; 4 Client by client, "
            "one page each; 5 Replies to pushback (four replies, each with a hold and a trade version) and the silence "
            "follow-ups; 6 Before you send."), "Small")

    # 1 How to send these
    doc.h1("1. How to send these")
    calls = [c for c in to_write if c["call_first"]]
    calls.sort(key=lambda c: -c["annual_fee"])
    rest = [c for c in to_write if not c["call_first"]]
    rest.sort(key=lambda c: -c["annual_fee"])
    doc.p(L("The order:"), bold=True)
    if calls:
        doc.p(L("Ring these first, using the call outline, then send each one's letter the same day as the written "
                "record:"))
    n = 1
    for c in calls:
        doc.numbered(n, L(f"{c['name']} ({', '.join(c['call_why'])})"))
        n += 1
    if rest:
        doc.p(L("Then send these letters:"))
    for c in rest:
        doc.numbered(n, L(c['name']))
        n += 1
    doc.p(L(f"When: on {st.d(send, weekday=True)}, in the morning, from your own email address. One letter per client, "
            f"never one group email."))
    doc.p("Reminders, one line each, ten days before each date, in date order:", bold=True)
    rems = []
    for c in calls + rest:
        if c["step1"] is None:
            continue
        steps = [(c["eff1"], c["step1"])] + ([(c["eff2"], c["step2"])] if c.get("step2") else [])
        for eff, fee in steps:
            rem = max(date.fromisoformat(eff) - timedelta(days=10), send + timedelta(days=1))
            while not is_working_day(rem, res.get("working_days")) and rem > send + timedelta(days=1):
                rem -= timedelta(days=1)
            if c["segment"] == "Reset the scope":
                text = (f"{c['name']}: once they have chosen, confirm their option and its {fw} in one line; "
                        f"if they have not replied, ring them.")
            else:
                text = f"{c['name']}, \"A reminder that from {_d(st, eff)} your {fw} is {st.money(fee)}.\""
            rems.append((rem, text))
    for rem, text in sorted(rems, key=lambda x: x[0]):
        doc.bullet(L(f"{st.d(rem, weekday=True)}: {text}"))
    doc.p(L("Silence: a week before each reply-by date, send the follow-up in section 5 to anyone who has not replied. "
            "For a letter that only needs a reply if they want to talk (Raise now, Two steps, Price to keep), no reply "
            "after that means the new fee goes on the invoice as the letter said. Renewal and scope-reset clients need "
            "an answer: ring them."))
    doc.p(L("Anything you agree that differs from the letter (a later start, a lower fee, a smaller scope) goes on the "
            "Exceptions sheet of the plan with its end date. A concession with no end date becomes the new fee."))
    doc.page_break()

    # 2 Call outline
    doc.h1("2. The call outline")
    doc.p(L("For the clients you ring first. Ten minutes. Say each part once."))
    for i, t in enumerate(["The reason, once: the one line from their letter.",
                           f"The new {fw} and the date, once, as a plain figure.",
                           "Silence. Let them answer first.",
                           "The choice: carry on at the new fee, or talk through the scope (Option B where you offer one).",
                           "The next step: \"I'll send it in writing today.\" Then send the letter."], start=1):
        doc.numbered(i, L(t))
    doc.p("Not to say:", bold=True)
    for t in ["An apology for the fee, in any form.",
              "Your costs, unless you gave a figure for them.",
              "A discount or a delay you have not priced. If you agree one, log it with an end date.",
              "Anything to fill the silence after the figure."]:
        doc.bullet(L(t))
    if calls:
        doc.p("Your calls:", bold=True)
        for c in calls:
            if c["step1"] is None:
                continue
            extra = f", then {st.money(c['step2'])} from {_d(st, c['eff2'])}" if c["step2"] else ""
            doc.bullet(L(f"{c['name']}: {st.money(c['fee'])} to {st.money(c['step1'])} {UNIT.get(c['per'], '')} from "
                         f"{_d(st, c['eff1'])}{extra}. Reason: {c['reason'] or 'none given, state the change plainly'}"))
    doc.page_break()

    # 3 Letters by group
    doc.h1("3. The letters by group")
    doc.p(L("One template for each group in your plan. Words in square brackets are filled from your list on the "
            "client pages that follow."))
    doc.p(L("The reason, first that applies: what new clients pay now; how the scope has grown, in your own words; "
            "the date your fee last changed, if you gave it; a cost you can put a figure on. If none applies, the letter "
            "states the change with no reason. It never blames costs unless you gave a figure for them."))
    for seg in ["Raise now", "Two steps", "At renewal", "Reset the scope", "Price to keep"]:
        if not any(c["segment"] == seg for c in to_write):
            continue
        doc.h2(seg)
        for t in template_for(seg, fw):
            doc.p(L(t), "Letter")
        doc.p(L("Before it is sent: " + SEND_RULE[seg]), "Small")
    doc.page_break()

    # 4 Client by client
    doc.h1("4. Client by client")
    for i, c in enumerate(to_write):
        subject, greet, lines = letter_lines(res, st, c)
        doc.h2(c["name"])
        status = "READY" if c["letter"] == "READY" else f"HOLD: {c['hold_why']}"
        doc.p(L(status), "Status")
        doc.p(f"Subject: {L(subject)}", bold=True)
        doc.p(greet, "Letter")
        for ln in lines:
            doc.p(ln, "Letter")
        if c.get("reason_src"):
            doc.p(L(f"Reason from: {c['reason_src']}. Notice: {c['notice']} ({c['notice_src']})."), "Small")
        if i < len(to_write) - 1:
            doc.page_break()
    doc.page_break()

    # 5 Pushback
    doc.h1("5. Replies to pushback")
    doc.p(L("Each reply comes in two versions. Hold keeps the fee. Trade gives something only in return for something, "
            "with an end date, and the cost goes on the Exceptions sheet."))
    raised = [c for c in to_write if c["raised"] and c["step1"] is not None]
    pb = pushback(res, st, raised)
    for title, hold, trade, note in pb:
        doc.h2(title)
        doc.p("Hold: " + L(hold), "Letter")
        doc.p("Trade: " + L(trade), "Letter")
        doc.p("Note for you, not the client: " + L(note), "Small")
    if raised:
        doc.p(L(f"For your notes, not for clients: what each month at the old {fw} costs you (the step 1 rise for one "
                f"month)"), bold=True)
        rows = [["Client", f"One month at today's {fw}", "Three months"]]
        for c in raised:
            per_month = (c["step1"] - c["fee"]) / (12 / c["units_year"]) if c["per"] != "project" and c["units_year"] else None
            rows.append([c["name"], st.money(per_month) if per_month is not None else "per project: the rise on each project",
                         st.money(per_month * 3) if per_month is not None else ""])
        doc.table(rows)
    doc.h2("The silence follow-ups")
    doc.p(L("Send one a week before the reply-by date if a client has not replied. Renewal and scope-reset clients "
            "need an answer, so ring them instead."), "Small")
    for c in to_write:
        if c["step1"] is None:
            continue
        greet = greeting(c)
        rb = reply_by(res, c)
        if c["segment"] in ("At renewal", "Reset the scope"):
            doc.bullet(L(f"{c['name']}: ring them by {st.d(rb - timedelta(days=7), weekday=True)}; their letter needs "
                         f"a reply."))
            continue
        doc.bullet(L(f"{c['name']}, on {st.d(rb - timedelta(days=7), weekday=True)}: \"{greet} a quick check that my note "
                     f"of {st.d(send)} reached you: from {_d(st, c['eff1'])} your {fw} is {st.money(c['step1'])}. Reply if "
                     f"you would like to talk it through before {st.d(rb)}.\""))
    doc.page_break()

    # 6 Before you send
    doc.h1("6. Before you send")
    checks = [
        "Your contracts: the notice and any renewal-only terms match what is in the plan. The skill does not say "
        "whether a date meets a contract.",
        "Fees are written the way you usually invoice them, with the currency. Enter fees before any sales tax (VAT, GST or similar); ask "
        "your accountant whether you need to charge it.",
        "Your sign-off is right at the end of each letter.",
        "You know who will answer replies, and you have the pushback page to hand.",
        "Each letter marked HOLD is fixed or confirmed first.",
    ]
    for t in checks:
        doc.bullet(L(t))
    doc.p(L("Check what your contracts and the rules where you and your clients are say about changing a price and "
            "giving notice; if your clients are individuals rather than businesses, check that too."))
    open_items = [f"{c['name']}: HOLD, {c['hold_why']}" for c in to_write if c["letter"] == "HOLD"] + res["needs"]
    doc.p("Open items:", bold=True)
    for t in open_items or ["None."]:
        doc.bullet(L(t))
    doc.p(L("Planning, not advice."), "Small")
    doc.save(path, "Price rise letters", footer_text(res, "price rise letters"))
    return path


def pushback(res, st, raised):
    """Four replies: (title, hold reply, trade reply, note for the founder). Replies are written to the client."""
    fw = res["fee_word"]
    reasons = {c["reason"] for c in raised if c.get("reason")}
    why = (next(iter(reasons)).rstrip(".") if len(reasons) == 1 else "the one in my letter, and it has not changed")
    new_price = res.get("new_client_fee") is not None and res.get("anchor_src") == "new_client_price" and bool(raised) \
        and all(c.get("hours") and c.get("rate_now") is not None and
                ((c["last"] - (c.get("cost") or 0)) / c["hours_unit"]) <= res["anchor_rate"] + 0.01 for c in raised)
    one_step = [c["name"] for c in raised if c["segment"] in ("Raise now", "Price to keep")]
    return [
        ("\"We can't afford it.\"",
         f"I understand. The new {fw} is the {fw} for this work now, and I would like to keep doing it for you. If the "
         f"budget is fixed, the way to make it fit is a smaller scope, not a lower {fw}.",
         f"We can keep today's {fw} if we narrow the work: tell me which part matters most, and I will send you "
         f"what today's {fw} would cover.",
         f"A smaller scope keeps the cash the same and gives you hours back. Log it on the Exceptions sheet with an end "
         f"date, your next review at the latest."),
        ("\"I've been with you for years.\"",
         "You have, and that is why you are hearing it from me directly, with notice."
         + (f" For the hours your work takes, the new {fw} is still below what new clients pay." if new_price else ""),
         f"If you confirm the next twelve months by the reply-by date in my letter, I will hold today's {fw} for a further "
         f"three months before the new one starts.",
         f"Three months at the old {fw} costs you the amount in the table below for that client. Log it with its end "
         f"date; never offer it without the twelve months in return."),
        ("\"Someone else is cheaper.\"",
         f"They may be. I would like to keep working with you, the work stays as it is, and the new {fw} is what it costs.",
         f"If keeping the cost down matters most, choose the part of the work you could do in-house and I will price "
         f"the rest at the new level.",
         "No discount on the same work. If they leave over price alone, the break-even sheet shows what that costs you."),
        ("\"Why now, and why this much?\"",
         f"The reason is {why}. I am telling you now so you have the dates and the figure well before anything changes.",
         f"If the size of the step is the problem, we can split it: half on the date in my letter and the rest three "
         f"months later, both dates in writing.",
         "Use the split only for clients on one step" + (f" ({_join(one_step)})" if one_step else "")
         + "; two-step and renewal clients already have dates. Log the difference with its end date."),
    ]


def _join(xs):
    xs = list(xs)
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


# ====================================================================== check
BANNED_EXTRA = [r"\[(?!NEED)[^\]]*\]", r"\{[^}]*\}"]


def check(docx, results):
    from check_copy import check as copy_check
    res = json.loads(Path(results).read_text(encoding="utf-8"))
    text = docx_text(docx)
    problems = []
    if res.get("outcomes"):
        for e in res["outcomes"]["exceptions"]:
            if e["client"] not in text:
                problems.append(f"{e['client']}: concession not in the follow-up")
        for r in res["outcomes"]["rows"]:
            if r["result"] == "countered" and f"\n{r['client']}\n" not in "\n" + text + "\n":
                problems.append(f"{r['client']}: no confirmation note")
        stray = [m for pat in BANNED_EXTRA for m in re.findall(pat, text) if m != "[your name]"]
        if stray:
            problems.append(f"unfilled field(s) {stray}")
        p2, _w, _n = copy_check(text, letters=True)
        return problems + p2
    pages = text.split("\f")
    plan = {c["name"]: c for c in res["clients"]}
    client_part = text.split("4. Client by client", 1)[-1].split("5. Replies to pushback", 1)[0]
    found = 0
    for page in client_part.split("\f"):
        lines = [x for x in page.split("\n") if x.strip()]
        if not lines:
            continue
        name = lines[0].strip()
        if name not in plan:
            continue
        found += 1
        c = plan[name]
        status = lines[1] if len(lines) > 1 else ""
        body = [x for x in lines[4:] if x.strip()]
        first3 = " ".join(body[:3])
        from rise_plan import Style
        st = Style(**res["style"])
        if c["step1"] is not None and st.money(c["step1"]) not in first3:
            problems.append(f"{name}: the new fee is not in the first three lines")
        if c["eff1"] and st.d(date.fromisoformat(c["eff1"])) not in first3:
            problems.append(f"{name}: the effective date is not in the first three lines")
        if c["reason"] and c["reason"] not in page.replace("\n", " ") and c["reason"] not in page:
            problems.append(f"{name}: the reason in the letter does not match the plan")
        if c["raised"] and not c["reason"] and "[NEED" not in " ".join(res["needs"]):
            problems.append(f"{name}: no reason and no [NEED] flag in the plan")
        stray = [m for pat in BANNED_EXTRA for m in re.findall(pat, "\n".join(lines[2:]))]
        stray = [s for s in stray if s not in ("[your name]",)]
        if stray:
            problems.append(f"{name}: unfilled field(s) {stray}")
        if "[NEED" in page and not status.startswith("HOLD"):
            problems.append(f"{name}: has a [NEED] but is not marked HOLD")
        if c["letter"] == "HOLD" and not status.startswith("HOLD"):
            problems.append(f"{name}: should be marked HOLD")
        letter_body = [x for x in body if not x.startswith(("Reason from:", "Subject:"))]
        if letter_body and letter_body[-1].strip() == (res.get("sign_off") or "[your name]").strip():
            letter_body = letter_body[:-1]
        joined = " ".join(letter_body)
        tp = re.search(r"\b(they|their|them|theirs|themselves)\b", joined, re.I)
        if tp and status.startswith("READY"):
            problems.append(f"{name}: the letter talks about the client in the third person "
                            f"('{joined[max(0, tp.start() - 30):tp.end() + 20].strip()}'); write to them as 'you'")
        if re.search(r"\b" + re.escape(name) + r"\b", joined) and status.startswith("READY"):
            problems.append(f"{name}: the letter names the client inside its own body; write to them as 'you'")
        ncf, nper = res.get("new_client_fee"), res.get("new_client_per") or "month"
        if ncf is not None and c.get("last") is not None and st.money(ncf) in joined:
            months = {"month": 1, "quarter": 3, "year": 12, "week": 12 / 52}
            if c["per"] == "project" or nper == "project":
                ncf_here = ncf if c["per"] == nper else None
            else:
                ncf_here = ncf * months.get(c["per"], 1) / months.get(nper, 1)
            scaled = c.get("hours") and re.search(r"an hour; your work runs to about", joined)
            if ncf_here is not None and not scaled and c["last"] > ncf_here + 0.005:
                problems.append(f"{name}: the letter gives the new-client price ({st.money(ncf)}) as the reason for a "
                                f"new fee above it ({st.money(c['last'])})")
    expected = sum(1 for c in res["clients"] if c["segment"] != "Hold")
    if found != expected:
        problems.append(f"{found} client letters found, {expected} expected")
    for c in res["clients"]:
        if c["segment"] == "Hold" and re.search(r"^" + re.escape(c["name"]) + r"$", client_part, re.M):
            problems.append(f"{c['name']} is held but has a letter")
    p2, _w, _n = copy_check(text, letters=True)
    problems += p2
    return problems


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "text":
        if not Path(sys.argv[2]).exists():
            print(f"STOP: there is no file at {sys.argv[2]}.")
            return 2
        print(docx_text(sys.argv[2]))
        return 0
    if len(sys.argv) != 4 or sys.argv[1] != "check":
        print(__doc__)
        return 2
    for p in sys.argv[2:]:
        if not Path(p).exists():
            print(f"STOP: there is no file at {p}. Nothing was checked.")
            return 2
    try:
        problems = check(sys.argv[2], sys.argv[3])
    except (zipfile.BadZipFile, KeyError, json.JSONDecodeError) as e:
        print(f"STOP: could not read the letters or the results file ({type(e).__name__}). Rebuild and run again.")
        return 2
    for p in problems:
        print("PROBLEM:", p)
    print(f"{len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
