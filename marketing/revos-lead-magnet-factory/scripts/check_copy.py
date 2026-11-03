#!/usr/bin/env python3
"""Copy checks for Lead Magnet Factory: banned patterns, dashes, the claim scan, locale and scope.

Usage:
  python3 scripts/check_copy.py --spec <spec.json>                 every founder-facing line in the spec
  python3 scripts/check_copy.py --spec <spec.json> --gate          also print the per-line gate list to review
  python3 scripts/check_copy.py --spec <spec.json> --files a.docx b.html c.txt
                                                                   the built files too (text pulled out of them)
  python3 scripts/check_copy.py --text "some copy"                 one string, banned patterns only

The claim scan finds every percentage, ratio ("9 out of 10"), multiplier ("doubled", "3x"), "most people",
"studies show", "on average" and amount of money, and fails any not matched to a `facts` entry that names its
source (money may also match a figure the founder wrote in their own material). Option labels in a question
may carry ranges ("Under 15k a month"): those are answer bins, not claims, and are not scanned for figures.
Exit 0 clean; 1 PROBLEM lines; 2 STOP. Standard library only. No network calls.
"""
import argparse
import html
import os
import re
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

BASE = [
    ("[\u2014\u2013]", "em or en dash: use a full stop, comma or colon"),
    (r"\bin today'?s (fast-paced|digital|ever-changing|busy|modern)", "stock opener"),
    (r"\b(it'?s|this is|that'?s) not (just )?(about )?[^.;:]{1,40}[,;] (it'?s|this is|that'?s)\b", "contrast reveal"),
    (r"\bnot (just )?[a-z ]{1,25}, but\b", "contrast reveal"),
    (r"\b(game[- ]?chang(er|ing)|delve|unlock(s|ed|ing)?|elevat(e|es|ed|ing)|seamless(ly)?|leverag(e|es|ed|ing)|"
     r"robust|synerg\w*|empower\w*|cutting[- ]edge|next[- ]level|world[- ]class|best[- ]in[- ]class)\b",
     "filler word"),
    (r"\b(I mean|to be honest|if I'?m (being )?honest|let'?s be real|truth be told)\b|(?:^|[.?!]\s+)honestly\b|\bhonestly,",
     "announced honesty"),
    (r"!", "exclamation mark in business copy"),
    (r"[\U0001F300-\U0001FAFF☀-☏☓-⛿✀-➿]", "emoji"),
]
DOMAIN = [
    (r"\bultimate guide\b", "'ultimate guide'"),
    (r"\bsecrets?\b(?! (santa|garden))", "'secret': promise what it does instead"),
    (r"\bhacks?\b", "'hacks'"),
    (r"\bfree value\b", "'free value'"),
    (r"\bjust checking in\b|\bcircling back\b|\btouching base\b|\bbumping this\b", "empty follow-up opener"),
    (r"\bforbidden knowledge\b|\bthey don'?t want you to know\b", "conspiracy hook"),
    (r"\blimited time\b|\bact now\b|\blast chance\b|\bdon'?t miss( out)?\b|\bhurry\b|\bonly \d+ (spots|places|seats)\b|"
     r"\bclosing soon\b|\bbefore it'?s gone\b|\bexpires (tonight|today|soon)\b", "false urgency"),
    (r"\bdownload now\b|\bclick here\b", "a button or link that says nothing"),
    (r"\bguarantee(d|s)?\b|\bno[- ]brainer\b|\bskyrocket\w*\b|\bsupercharg\w*\b|\b10x\b|\bcrush(ing)? it\b|"
     r"\blife[- ]changing\b|\brevolutionary\b|\btransform your (business|life)\b", "hype or a promise of outcome"),
    (r"\bI hope (this|you('| a)re)\b|\bhope this (email )?finds you\b|\bhey there\b", "stock email opener"),
    (r"\bthat'?s where \w+ comes in\b|\bhere'?s the (thing|kicker|truth)\b|\bthe best part\?", "stock reveal"),
]
LEGAL = (r"\b(GDPR|PDPA|CAN[- ]SPAM|CASL|P[E]CR|POPIA|LGPD|CCPA|APPs?)\b|\blawful basis\b|\blegally (required|compliant)\b|"
         r"\b(is|are|be|fully) compliant\b|\bcompl(y|ies) with\b|\bthe law (says|requires)\b")
TAX = r"\b(VAT|GST|HST|sales tax|tax[- ](deductible|deduction|relief|return|rule|rate|code|bracket)|write it off)\b"
CLAIMS = [
    ("percentage", r"\b\d+(?:[.,]\d+)?\s?(?:%|per ?cent\b|percent\b)"),
    ("ratio", r"\b(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+(?:out of|in)\s+(?:\d+|ten|five|four|"
              r"three|a hundred|hundred)\b(?! (minutes|days|weeks|months|years))"),
    ("ratio", r"\b(?:nine|9) times out of (?:ten|10)\b"),
    ("multiplier", r"\b\d+(?:[.,]\d+)?\s?x\b|\b(?:doubl(?:e|ed|es|ing)|tripl(?:e|ed|es|ing)|twice as|"
                   r"(?:two|three|four|five|ten|\d+) times (?:more|as|faster|higher|bigger|the))\b"),
    ("generalisation", r"(?<!the )(?<!the very )\b(?:most|the majority of|almost all|nearly all|almost every|nearly every|nearly everyone|"
                       r"almost everyone|everyone knows|half of|a third of|a quarter of|two thirds of)\s+"
                       r"(?:of\s+)?(?:you\b|them\b|us\b|the\s+[a-z]+s\b|your\s+[a-z]+s\b|[a-z]+(?:s|ple|ers)\b)"),
    ("research", r"\b(?:studies|research|data|science|surveys?|experts?|statistics|the numbers)\s+(?:show|shows|prove|"
                 r"proves|says|say|suggests?|found|finds|tells? us)\b|\b(?:statistically|scientifically|"
                 r"research[- ]backed|evidence[- ]based|according to|proven)\b"),
    # "on average" is a claim only beside a figure or a research word; "I know it on average" is behaviour wording
    ("average claim", r"(?:\b\d[\d.,]*\s?%?|\b(?:studies|research|data|survey|surveys)\b)(?:\W+\w+){0,8}?\W+on average\b|"
                      r"\bon average\b(?:\W+\w+){0,8}?\W+(?:\d[\d.,]*|studies|research|data|surveys?)\b"),
    ("money", r"(?:[$€£¥₹]|\b(?:US\$|S\$|A\$|C\$|NZ\$|HK\$)|\b(?:USD|EUR|GBP|SGD|AUD|CAD|INR|NZD|HKD|CHF|SEK|NOK|DKK|JPY|"
              r"CNY|AED|ZAR|MYR|PHP)\s?)\s?\d[\d.,]*(?:\s?(?:k|m|million|thousand|lakh|crore)\b)?|"
              r"\b\d[\d.,]*\s?(?:k\s)?(?:USD|EUR|GBP|SGD|AUD|CAD|INR|dollars|euros|pounds|rupees)\b|\b\d[\d.,]*\s?€"),
]
GEN_EXEMPT = {"days", "weeks", "times", "mornings", "evenings", "nights", "months", "years", "questions", "answers",
              "items", "steps", "emails", "pages", "readers"}
SPELL = {  # british: american
    "colour": "color", "colours": "colors", "behaviour": "behavior", "behaviours": "behaviors", "favourite": "favorite",
    "honour": "honor", "labour": "labor", "neighbour": "neighbor", "organise": "organize", "organised": "organized",
    "organising": "organizing", "organisation": "organization", "realise": "realize", "realised": "realized",
    "prioritise": "prioritize", "prioritised": "prioritized", "recognise": "recognize", "apologise": "apologize",
    "analyse": "analyze", "analysed": "analyzed", "centre": "center", "travelled": "traveled", "cancelled": "canceled",
    "modelling": "modeling", "catalogue": "catalog", "cheque": "check", "defence": "defense", "practise": "practice",
    "enrol": "enroll", "fulfil": "fulfill", "judgement": "judgment", "summarise": "summarize", "customise": "customize",
    "emphasise": "emphasize", "minimise": "minimize", "maximise": "maximize", "optimise": "optimize",
    "programme": "program", "worktop": "countertop", "diarise": "calendar",
}
CURRENCY_SYMBOL = {"USD": "$", "CAD": "$", "AUD": "$", "SGD": "$", "NZD": "$", "HKD": "$", "MXN": "$", "EUR": "€",
                   "GBP": "£", "INR": "₹", "JPY": "¥", "CNY": "¥"}


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s%.,$€£¥₹]", " ", str(s or "").lower())).strip()


def ctx(text, m, pad=28):
    return text[max(0, m.start() - pad):m.end() + pad].replace("\n", " ").strip()


RESULT_SENT = re.compile(r"\b(?:check|look in|watch|see)\s+your\s+(?:inbox|email)\b[^.?!]{0,30}\b(?:results?|score)\b|"
                         r"\b(?:results?|score)\b[^.?!]{0,20}\b(?:sent|emailed|delivered|arrives?|lands?)\b[^.?!]{0,20}"
                         r"\b(?:inbox|email)\b|\b(?:we|I)(?:'ll| will)?\s+(?:email|send)\s+you\s+your\s+(?:results?|score)\b",
                         re.I)
HEADLINE_LABELS = ("magnet.title", "magnet.promise", "optin.headline", "optin.subhead", "optin.button",
                   "thankyou.headline", "checklist.title", "guide.title", "cta.label")
OUTCOME = re.compile(r"\b(?:fix|double|triple|grow|boost|increase|scale|transform|maximi[sz]e|skyrocket|multiply|"
                     r"explode|10x|supercharge|turbocharge)\s+your\b|\b(?:get|win|land|make|earn)\s+more\b", re.I)
MORE = re.compile(r"(?<!or )(?<!hear )(?<!any )(?<!no )(?<!once )\bmore\b(?! than\b)", re.I)


def is_headline(label):
    return label in HEADLINE_LABELS or bool(re.match(r"email\d+\.subject\d", label))


def banned(text, label, problems, warns, never=()):
    for pat, why in BASE + DOMAIN:
        for m in re.finditer(pat, text, re.I):
            problems.append(f"{label}: {why}: '{ctx(text, m)}'")
    head = is_headline(label)
    for m in MORE.finditer(text):
        clause = re.split(r"[.;:?!]", text[m.end():])[0]
        if re.search(r"\bthan\b", clause, re.I):
            continue  # "more calls than last year" is a comparison
        if head:
            problems.append(f"{label}: 'more' with no comparison in a headline, subject or button: '{ctx(text, m)}'. "
                            "Say what the reader will see or know instead.")
        else:
            warns.append(f"{label}: 'more' with no comparison? '{ctx(text, m)}'")
    if head:
        for m in OUTCOME.finditer(text):
            problems.append(f"{label}: promises an outcome the magnet cannot deliver: '{ctx(text, m)}'. Promise what "
                            "the reader will find out ('Find out where the cash goes'), not what the offer sells.")
    for w in never:
        for m in re.finditer(r"\b" + re.escape(w) + r"\b", text, re.I):
            problems.append(f"{label}: '{w}' is a word the founder asked never to see: '{ctx(text, m)}'")
    for m in re.finditer(LEGAL, text):
        problems.append(f"{label}: states or implies what a law requires: '{ctx(text, m)}'. Use the one generic line "
                        "on checking the rules where the founder and their subscribers are.")
    for m in re.finditer(TAX, text, re.I):
        problems.append(f"{label}: tax wording: '{ctx(text, m)}'. Give no tax view; say the founder's accountant "
                        "confirms anything about tax.")


def money_values(text, decimal):
    vals = set()
    for m in re.finditer(CLAIMS[-1][1], text, re.I):
        try:
            v, _c, _n = C.read_money(m.group(0), decimal)
            vals.add(round(v, 2))
        except (C.LN.Ambiguous, C.LN.Unreadable):
            pass
    for m in re.finditer(r"\b\d[\d.,]*\s?(?:k|m)?\b", text):
        try:
            v, _n = C.LN.parse_number(C.normalise_typed(m.group(0)), decimal)
            vals.add(round(v, 2))
        except (C.LN.Ambiguous, C.LN.Unreadable, ValueError):
            pass
    return vals


def claim_scan(items, spec, src, decimal, problems):
    bad_source = re.compile(r"\b(heard|somewhere|not sure|unknown|i think|read it|don'?t know)\b", re.I)
    facts = [norm(f.get("claim")) for f in spec.get("facts") or []
             if str(f.get("source") or "").strip() and not bad_source.search(str(f.get("source")))]
    src_money = money_values(src, decimal)
    price = (spec.get("offer") or {}).get("_price")
    if price:
        src_money.add(round(price, 2))
    count = 0
    for label, text in items:
        is_option = label.endswith(".option")
        own_words = is_option and re.match(r"\s*(I|We|I'm|We're|My|Our)\b", text)
        for kind, pat in CLAIMS:
            if is_option and kind in ("money", "percentage", "ratio", "generalisation"):
                continue
            if own_words and kind in ("research", "average claim"):
                continue  # an answer in the reader's own voice describes what they do, not a finding
            for m in re.finditer(pat, text, re.I):
                hit = m.group(0)
                if kind == "generalisation":
                    last = hit.split()[-1].lower()
                    if last in GEN_EXEMPT:
                        continue
                n = norm(hit)
                sentence = norm(re.split(r"(?<=[.?!])\s+", text[:m.end()])[-1] + text[m.end():].split(".")[0])
                if any(n in fa or (fa and fa in sentence) for fa in facts):
                    continue
                if kind == "money":
                    try:
                        v, _c, _n = C.read_money(hit, decimal)
                        if round(v, 2) in src_money:
                            continue
                    except (C.LN.Ambiguous, C.LN.Unreadable):
                        pass
                count += 1
                problems.append(f"{label}: unsourced {kind}: '{ctx(text, m)}'. Use the founder's own figure with its "
                                "source in `facts`, or cut it.")
    return count


def locale_checks(items, spec, decimal, problems):
    f = spec.get("founder") or {}
    cur = (f.get("currency") or "").upper()
    ok = CURRENCY_SYMBOL.get(cur)
    others = {"$", "€", "£", "₹", "¥"} - ({ok} if ok else set())
    words_bad = {"$": r"\bdollars?\b", "€": r"\beuros?\b", "£": r"\bpounds?\b|\bquid\b", "₹": r"\brupees?\b"}
    for label, text in items:
        for sym in others:
            if sym in text:
                problems.append(f"{label}: '{sym}' in copy for a founder who works in {cur}: '{text[:60]}'")
            w = words_bad.get(sym)
            if w and re.search(w, text, re.I):
                problems.append(f"{label}: a currency word that is not the founder's ({cur}): '{text[:60]}'")
        if decimal == "comma" and re.search(r"\b\d{1,3},\d{3}\b", text):
            problems.append(f"{label}: thousands written with a comma, but the founder writes 1.200 style: '{text[:60]}'")
        if decimal == "dot" and re.search(r"\b\d{1,3}\.\d{3}\b(?![.,]\d)", text):
            problems.append(f"{label}: thousands written with a dot, but the founder writes 1,200 style: '{text[:60]}'")
    sp = (f.get("spelling") or "").lower()
    if sp in ("british", "american", "australian", "canadian", "indian"):
        wrong = list(SPELL.values()) if sp in ("british", "australian", "indian") else list(SPELL.keys())
        if sp == "canadian":
            wrong = []
        for label, text in items:
            for w in wrong:
                if w in ("program", "check", "practice", "countertop", "calendar", "license"):
                    continue
                if re.search(r"\b" + re.escape(w) + r"\b", text, re.I):
                    problems.append(f"{label}: '{w}' is {('American' if sp != 'american' else 'British')} spelling; "
                                    f"the founder writes {sp.capitalize()} English")


def file_text(path):
    if path.endswith(".docx"):
        with zipfile.ZipFile(path) as z:
            xml = z.read("word/document.xml").decode("utf-8")
        xml = re.sub(r"</w:p>", "\n", xml)
        return html.unescape(re.sub(r"<[^>]+>", "", xml))
    t = C.read_text(path)
    if path.endswith(".html"):
        t = re.sub(r"<style.*?</style>", " ", t, flags=re.S)
        data = re.findall(r'<script type="application/json"[^>]*>(.*?)</script>', t, flags=re.S)
        t = re.sub(r"<script.*?</script>", " ", t, flags=re.S)
        t = html.unescape(re.sub(r"<[^>]+>", " ", t)) + "\n" + "\n".join(data)
    return t


GATE_LABELS = ("magnet.title", "magnet.promise", "optin.headline", "optin.subhead", "thankyou.headline",
               "checklist.title", "guide.title", "door.question")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--spec")
    ap.add_argument("--text")
    ap.add_argument("--files", nargs="*")
    ap.add_argument("--gate", action="store_true")
    a = ap.parse_args()
    problems, warns = [], []
    if a.text is not None:
        banned(a.text, "text", problems, warns)
        n = claim_scan([("text", a.text)], {}, "", None, problems)
        print(f"Claim scan: {n} unsourced claim(s).")
    elif a.spec:
        spec = C.load_spec(a.spec)
        src = C.sources_text(spec)
        decimal = C.decimal_style(spec, [src])
        offer = spec.get("offer") or {}
        if offer.get("price_as_typed"):
            try:
                offer["_price"] = C.read_money(offer["price_as_typed"], decimal)[0]
            except (C.LN.Ambiguous, C.LN.Unreadable):
                pass
        never = (spec.get("founder") or {}).get("never_words") or []
        items = C.founder_strings(spec)
        for label, text in items:
            banned(text, label, problems, warns, never)
        n = claim_scan(items, spec, src, decimal, problems)
        locale_checks(items, spec, decimal, problems)
        if spec.get("format") == "scorecard":
            for label, text in items:
                if not label.startswith(("optin.", "thankyou.", "magnet.")):
                    continue
                mm = RESULT_SENT.search(text)
                if mm:
                    problems.append(f"{label}: '{ctx(text, mm)}' says the result arrives by email; the result shows "
                                    "on the scorecard page and nothing sends it.")
        for path in a.files or []:
            if not os.path.exists(path):
                raise C.Stop(f"cannot find {path}")
            t = file_text(path)
            for lab, opt in items:  # answer bins are not claims, in the files as in the spec
                if lab.endswith(".option"):
                    t = t.replace(opt, " ")
            quoted = (spec.get("topic") or {}).get("source_line")
            if quoted:  # the founder's own words, quoted as the topic's source in the pack
                t = t.replace(quoted, " ")
            base = os.path.basename(path)
            lines = [(f"{base}", ln) for ln in t.splitlines() if ln.strip()]
            for label, ln in lines:
                banned(ln, label, problems, warns, never)
            n += claim_scan([(lab, ln) for lab, ln in lines
                             if not re.match("^\\s*☐", ln) and "possible answer sets" not in ln],
                            spec, src, decimal, problems)
        print(f"Claim scan: {n} unsourced claim(s).")
        if a.gate:
            print("GATE (read each: can the reader picture it? can it be proved true or false? could a competitor "
                  "write it word for word? Two fails: rewrite):")
            for label, text in items:
                if label in GATE_LABELS or ".subject" in label:
                    print(f"  {label}: {text}")
    elif a.files:
        for path in a.files:
            t = file_text(path)
            for ln in t.splitlines():
                if ln.strip():
                    banned(ln, os.path.basename(path), problems, warns)
    else:
        raise C.Stop("give --spec <spec.json>, --text \"copy\" or --files <file> ...")
    for x in dict.fromkeys(problems):
        print("PROBLEM:", x)
    for x in dict.fromkeys(warns):
        print("WARN:", x)
    print(f"{len(set(problems))} problems, {len(set(warns))} warnings")
    return 1 if problems else 0


if __name__ == "__main__":
    C.run_main(main)
