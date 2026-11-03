#!/usr/bin/env python3
"""Check founder-facing copy for Client Credit Check.

Usage (paths relative to this skill's folder):
  python3 scripts/check_copy.py <file>                       general copy check (banned patterns, dashes)
  python3 scripts/check_copy.py --wording <wording.md> --results <results.json>
        the client-facing wording: no mention of the check, no accusation, no law, every figure, percentage
        and day count one the scripts produced, the founder's spelling
  python3 scripts/check_copy.py --brief <brief.docx> --results <results.json>   the built brief
  python3 scripts/check_copy.py --self-test
Prints PROBLEM and WARN lines and a count. Exit 0 clean, 1 problems, 2 STOP (unreadable input).
Standard library only. No network calls.
"""
import json
import re
import sys

BASE = {
    r"[\u2014\u2013]": "em or en dash",
    r"\bin today'?s (fast-paced|digital|ever-changing)": "stock opener",
    r"\bit'?s not (just )?[^.]{1,40}, it'?s\b": "contrast reveal",
    r"\b(game[- ]changer|delve|unlock(s|ing)?|elevate(s|d)?|seamless(ly)?|leverag(e|es|ing)|robust)\b": "filler word",
    r"\b(I mean|to be honest|if I'?m being honest|let'?s be real)\b": "announced honesty",
}
DOMAIN = {  # never in anything the skill writes in its own voice
    r"\bcredit[- ]?worth(y|iness)\b": "creditworthy as a verdict",
    r"\bcredit limit\b": "credit limit",
    r"\bsafe (client|to sign|bet)\b|\bis safe\b": "'safe': a Go is never 'safe'",
    r"\brisk[- ]free\b": "risk-free",
    r"\bguarantee(d|s)?\b": "guarantee",
    r"\b(fraud(ulent|ster)?|scam(mer)?s?|dodgy|deadbeat|crook)\b": "accusation",
    r"\bblacklist(ed|ing)?\b": "blacklist",
    r"\b(insolvent|bankrupt)\b": "insolvent or bankrupt in the skill's own voice",
    r"\bthe law (requires|allows|says)\b|\blegally\b|\byou are entitled\b|\bstatutory\b|\bstatute\b": "a statement of law",
    r"\bunfortunately\b": "unfortunately",
    r"\breaching out\b": "reaching out",
    r"\bvalued client\b": "valued client",
    r"\bjust to be safe\b": "just to be safe",
    r"\bindustry standard\b|\beveryone asks for\b|\bmost freelancers\b": "a benchmark claim",
    r"\btrust issues\b|\bI do not trust\b|\bI don'?t trust\b": "trust accusation",
    r"\bscore\b|\bgrade\b|\b\d+ ?/ ?100\b|\bout of (10|100)\b": "a score or grade",
}
LAWCODE = {  # case-sensitive
    r"§|\b[Ss]ection \d+|\bBGB\b|\bHGB\b|\bUCC\b|\b[A-Z][a-z]+ Act\b": "a statute or legal code",
}
WORDING_ONLY = {  # the client must never read about the check
    r"\b(credit|check(ed|ing)?|vet(ted|ting)?|look(ed)? (you|them) up|background|research(ed)?|register|registry|due diligence|reviews?)\b":
        "mentions the check; the wording to the client never does",
    r"\b(risk|risky|worried|concern(ed|s)?|red flag|suspicious|caution|stop)\b": "sounds like an accusation",
    r"\bsorry\b|\bapologi[sz]e\b|\bI'?m afraid\b": "apology; terms are how the founder works, not a favour",
    r"\[NEED": "an unfilled [NEED] gap",
    # the same in the languages founders most often send terms in
    r"\b(bonit\w*|kreditw\w*|geprüft|überprüf\w*|recherch\w*|handelsregister|risiko|bedenken|kredietwaardig\w*|gecontroleerd|"
    r"risico|solvabilit\w*|vérifi\w*|risque|solvencia|verificad\w*|riesgo|affidabilit\w*|rischio)\b":
        "mentions the check or risk; the wording to the client never does",
    r"\b(leider|entschuldig\w*|helaas|sorry|désolé\w*|malheureusement|lo siento|lamentablemente|purtroppo)\b":
        "apology; terms are how the founder works, not a favour",
}
WARN = {
    r"!": "exclamation mark in business copy",
    r"\bmore\b": "'more' as an intensifier: is a specific comparison possible?",
}
NOT_US = r"\b(instalments?|authoris\w*|organis\w*|recognis\w*|prioritis\w*|finalis\w*|cheque|colour|favour\w*|behaviour)\b"
NOT_UK = r"\b(installments?|authoriz\w*|organiz\w*|recogniz\w*|prioritiz\w*|finaliz\w*|color|favor\w*|behavior)\b"
MONEY = re.compile(r"(?:\b[A-Z]{3}\s?|(?:A|AU|NZ|C|CA|S|HK|US)\$|[$€£₹¥])\s?\d[\d.,]*\d|\d[\d.,]*\d?\s?(?:€|EUR\b)|\d[\d.,]*\s?(?:lakh|crore)")


def snip(text, m):
    return text[max(0, m.start() - 25):m.end() + 25].replace("\n", " ").strip()


def scan(text, table, flags=re.I):
    out = []
    for pat, why in table.items():
        for m in re.finditer(pat, text, flags):
            out.append(f"{why}: '{snip(text, m)}'")
    return out


def spelling(text, english):
    loc = str(english or "").lower().replace("_", "-")
    if not loc.startswith("en") or loc == "en":
        return []
    pat, want = (NOT_US, "American") if loc in {"en-us", "en-ph"} else ((r"\b(authoris\w*|organis\w*|colour)\b", "Canadian") if loc == "en-ca" else (NOT_UK, "the founder's"))
    if loc == "en-ca":
        pat = r"\b(authoris\w*|organis\w*)\b"
    return [f"'{m.group(0)}' is not {want} spelling" for m in re.finditer(pat, text, re.I)]


def norm(s):
    return re.sub(r"\s+", "", s)


def check_wording(text, res):
    problems = scan(text, BASE) + scan(text, DOMAIN) + scan(text, LAWCODE, 0) + scan(re.sub(r"(?im)^## .*$", "", text), WORDING_ONLY)
    figures = {norm(f) for f in res.get("figures", [])}
    body = re.sub(r"(?m)^## .*$", "", text)
    for m in MONEY.finditer(body):
        tok = norm(m.group(0))
        if tok not in figures:
            problems.append(f"the figure '{m.group(0)}' is not one the scripts produced; copy figures exactly")
    pcts = {round(float(p["pct"]), 2) for p in res.get("rec_pays", []) if p.get("pct") is not None}
    pcts |= {round(float(c.get("deposit")), 2) for c in res.get("concessions", {}).values() if c.get("deposit") is not None}
    for m in re.finditer(r"(\d+(?:[.,]\d+)?)\s?%", body):
        v = round(float(m.group(1).replace(",", ".")), 2)
        if v not in pcts:
            problems.append(f"the percentage '{m.group(0)}' is not one in the recommended terms")
    days_ok = {res.get("rung_terms", {}).get("days"), res.get("their_terms", {}).get("days")}
    days_ok |= {c.get("days") for c in res.get("concessions", {}).values()}
    for m in re.finditer(r"\b(\d+)\s+(?:days|Tage|Tagen|dagen|jours|días|dias|giorni|dni)\b", body, re.I):
        if int(m.group(1)) not in days_ok:
            problems.append(f"'{m.group(0)}' is not a day count in the terms")
    problems += spelling(body, res.get("english"))
    return problems


def check_brief(text, res):
    own = "\n".join(l for l in text.splitlines() if not l.startswith("Planning view of public facts"))
    own = re.sub(r"'[^'\n]{0,200}'", "''", own)  # quoted source words are the source's, not ours
    problems = scan(own, BASE) + scan(own, DOMAIN) + scan(own, LAWCODE, 0)
    problems += [p for p in scan(own, {r"\bcredit score\b|\brating\b": "score or rating word"})]
    if re.search(r"\b(VAT|GST|sales tax)\b[^.\n]{0,40}\b\d+(\.\d+)?\s?%", text):
        problems.append("a tax rate appears; never state one")
    if res.get("verdict") == "GO" and not res.get("entity_verified") and res.get("their", {}).get("peak", 0) > res.get("limit", 0):
        problems.append("a Go for an unverified entity above the limit")
    return problems


def self_test():
    ok = fail = 0
    res = {"figures": ["7.000 €", "3.500 €", "14.000 €"], "rec_pays": [{"pct": 50}, {"pct": 25}, {"pct": 25}],
           "rung_terms": {"days": 14}, "their_terms": {"days": 60}, "concessions": {}, "english": "en-GB"}
    good = "## Proposal\n\nFor projects of this size I work in stages: 50% (7.000 €) when we sign, then 3.500 € at week 5, " \
           "then 3.500 € on delivery, each due within 14 days.\n"
    bad = "## Proposal\n\nUnfortunately, after checking your company register I need a 50% deposit (7.500 €) within 30 days " \
          "\u2014 just to be safe, as the law requires!\n"
    for txt, want, label in [(good, 0, "good wording"), (bad, 1, "bad wording")]:
        n = len(check_wording(txt, res))
        if (n == 0) == (want == 0):
            ok += 1
        else:
            fail += 1
            print("FAIL", label, check_wording(txt, res))
    probs = check_wording(bad, res)
    for need in ["mentions the check", "not one the scripts", "dash", "statement of law", "unfortunately", "day count"]:
        if any(need in p for p in probs):
            ok += 1
        else:
            fail += 1
            print("FAIL missing", need)
    b = check_brief("Planning view of public facts. Not a credit score, rating, legal opinion or accusation.\n"
                    "The register shows the status as 'in liquidation, insolvent'", {"verdict": "STOP"})
    ok, fail = (ok + 1, fail) if not b else (ok, fail + 1)
    b = check_brief("This client is safe to sign. Credit score 72/100. Under § 286 BGB they are insolvent.", {"verdict": "GO"})
    ok, fail = (ok + 1, fail) if len(b) >= 4 else (ok, fail + 1)
    if spelling("installment", "en-GB") and spelling("organise", "en-US") and not spelling("organise", "en-AU"):
        ok += 1
    else:
        fail += 1
        print("FAIL spelling")
    print(f"{ok} passed, {fail} failed")
    return fail == 0


def main(argv):
    if not argv or argv[0] in {"-h", "--help"}:
        print(__doc__)
        return 0
    if argv[0] == "--self-test":
        return 0 if self_test() else 1
    try:
        res = json.load(open(argv[argv.index("--results") + 1], encoding="utf-8")) if "--results" in argv else {}
        if "--wording" in argv:
            problems, warns = check_wording(open(argv[argv.index("--wording") + 1], encoding="utf-8").read(), res), []
        elif "--brief" in argv:
            sys.path.insert(0, __file__.rsplit("/", 1)[0])
            import docx_lite
            text = docx_lite.docx_text(argv[argv.index("--brief") + 1])
            problems, warns = check_brief(text, res), []
        else:
            text = open(argv[0], encoding="utf-8").read()
            problems, warns = scan(text, BASE) + scan(text, DOMAIN) + scan(text, LAWCODE, 0), scan(text, WARN)
    except (OSError, ValueError, IndexError, KeyError) as e:
        print(f"STOP: the file could not be read ({e.__class__.__name__}). Nothing was checked.")
        return 2
    for p in problems:
        print("PROBLEM:", p)
    for w in warns:
        print("WARN:", w)
    print(f"{len(problems)} problems, {len(warns)} warnings")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
