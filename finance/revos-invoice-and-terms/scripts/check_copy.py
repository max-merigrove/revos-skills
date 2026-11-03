#!/usr/bin/env python3
"""Check anything written for the founder or their client: the chat reply, the reminder, the terms wording.

Usage:
  python3 scripts/check_copy.py <file> [--plan <plan.json>] [--supplied "wording the founder gave"] [--english en-US]
  python3 scripts/check_copy.py --text "some copy" [--plan <plan.json>]
Checks the banned patterns (references/banned-patterns.md), claims about what a law requires or allows, threats,
and, with --plan, that every amount and percentage in the text is one the script produced or the founder gave.
Wording the founder supplied (--supplied, and the plan's notes and late fee clause) is exempt from the law check.
Prints PROBLEM and WARN lines and a count. Exit 0 clean, 1 problems, 2 STOP. Standard library only.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

PROBLEM_PATTERNS = {
    "[\u2014\u2013]": "em or en dash",
    r"\bin today'?s (fast-paced|digital|ever-changing)": "stock opener",
    r"\bit'?s not (just )?[^.]{1,40}, it'?s\b": "contrast reveal",
    r"\b(game[- ]changer|delve|unlock(s|ing)?|elevate(s|d)?|seamless(ly)?|leverag(e|es|ing)|robust)\b": "filler word",
    r"\b(I mean|to be honest|if I'?m being honest|let'?s be real)\b": "announced honesty",
    # this skill's list
    r"\bkindly\b": "'kindly' reads as passive aggressive",
    r"\b(as )?per my (last|previous) (email|message)\b": "'per my last email'",
    r"\bfriendly reminder\b": "'friendly reminder': say what is due instead",
    r"\bpay(ment)? immediately\b|\bASAP\b|\burgent(ly)?\b": "pressure words",
    r"\blegal (action|proceedings|backing)\b|\btake legal\b|\bcourt\b|\bsue\b|\bdebt collect\w*": "legal threat",
    r"\breserve the right to (suspend|stop|withhold|remove)\b|\btake (the|your) (site|website) (offline|down)\b|\bsuspend (hosting|services?)\b": "suspension or take-down threat",
    r"\bstatutory\b|\bby law\b|\bunder the law\b|\brequired by law\b|\blegally (required|entitled|obliged|bound)\b|\benforceable\b|\bmandatory\b": "claim about what the law requires",
    r"\bpenalt(y|ies)\b": "'penalty': use the founder's own word for a fee they agreed",
    r"\binterest at\b|\bper annum\b|\bp\.a\.\b": "interest wording the founder did not supply",
    r"\bwithin 24 hours\b": "pressure deadline",
    r"\bthank you for your continued support\b|\bvalued (client|customer)\b": "stock filler",
    r"\bnet ?(7|10|14|15|30|45|60|90)\b(?![^.]*\b(by|on|due)\b[^.]*\d)": "'net N' with no date beside it",
    r"\byou'?re (right|correct) (about|that)\b[^.]{0,60}\b(tax|vat|gst|exempt)": "agrees with a tax belief",
    r"\[STAT\]|\[VERIFY\]|\[INSERT": "placeholder left in; use [NEED: ...]",
}
WARN_PATTERNS = {
    r"\bmore\b": "'more' as an intensifier: is a specific comparison possible?",
    r"!": "exclamation mark in business copy",
    r"\bas discussed\b": "'as discussed' with no reference: name the call or email",
    r"\bjust (checking|following) (in|up)\b": "'just checking in' undersells the ask",
    r"\bsorry to (bother|chase)\b": "apologising for asking to be paid",
}
NUM = r"\d{1,3}(?:[ ,.'\u00a0]\d{2,3})+(?:[.,]\d{1,3})?|\d+(?:[.,]\d{1,3})?"
CODE_AMT = re.compile(rf"\b([A-Z]{{3}})\s?({NUM})|({NUM})\s?([A-Z]{{3}})\b")
SYM_AMT = re.compile(rf"[$€£¥₹]\s?({NUM})")
PCT = re.compile(r"(\d+(?:[.,]\d+)?)\s?(%|per ?cent\b|percent\b)")
QUOTED = re.compile(r'"[^"\n]{1,200}"|\u201c[^\u201d\n]{1,200}\u201d|`[^`\n]{1,200}`|^>.*$', re.M)
OWN_WORDS = re.compile(r"(?i)\b(your (last|old|previous) invoice (said|says|had|showed|used)|you (wrote|said|had|used))\b[^.\n]{0,80}")
NOT_US = r"\b(instalments?|authoris\w*|organis\w*|recognis\w*|apologis\w*|cancelled)\b"
NOT_UK = r"\b(installments?|authoriz\w*|organiz\w*)\b"


def strings_in(obj, acc):
    if isinstance(obj, dict):
        for v in obj.values():
            strings_in(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            strings_in(v, acc)
    elif obj is not None:
        acc.append(str(obj))
    return acc


def norm_amount(s):
    return re.sub(r"[\s']", "", s)


def check(text, plan=None, supplied=(), english=None, also=None):
    problems, warns = [], []
    scrub = text
    exempt = list(supplied or [])
    if plan:
        doc = plan.get("doc") or {}
        exempt += doc.get("notes") or []
        lf = plan.get("late_fee") or {}
        if lf.get("clause"):
            exempt.append(lf["clause"])
    for s in exempt:
        if s:
            scrub = scrub.replace(s, " ")
    # the founder's own words quoted back to them ("your last invoice said "Net 15"") are not our copy
    quoted = QUOTED.sub(" ", scrub)
    quoted = OWN_WORDS.sub(" ", quoted)
    for pat, why in PROBLEM_PATTERNS.items():
        src = scrub if why in ("em or en dash",) else quoted
        for m in re.finditer(pat, src, re.I):
            problems.append(f"{why}: '{src[max(0, m.start() - 25):m.end() + 25].strip()}'")
    for pat, why in WARN_PATTERNS.items():
        for m in re.finditer(pat, scrub, re.I):
            warns.append(f"{why}: '{scrub[max(0, m.start() - 20):m.end() + 20].strip()}'")
    eng = (english or (plan or {}).get("english") or "").lower()
    if eng in ("en-us", "en-ph"):
        for m in re.finditer(NOT_US, text, re.I):
            problems.append(f"'{m.group(0)}' is not American spelling")
    elif eng.startswith("en-") and eng not in ("en-ca",):
        for m in re.finditer(NOT_UK, text, re.I):
            problems.append(f"'{m.group(0)}' is not the founder's spelling")
    if plan is not None:
        allowed = set()
        allowed_pct = set()
        for s in strings_in(plan, []):
            for m in CODE_AMT.finditer(s):
                allowed.add(norm_amount(m.group(2) or m.group(3)))
            for m in re.finditer(NUM, s):
                allowed.add(norm_amount(m.group(0)))
            for m in PCT.finditer(s):
                allowed_pct.add(m.group(1))
        for s in list(supplied or []) + strings_in(also or [], []):
            for m in re.finditer(NUM, s):
                allowed.add(norm_amount(m.group(0)))
            for m in PCT.finditer(s):
                allowed_pct.add(m.group(1))
        rates = [c.get("rate") for c in ((plan.get("tax_setup") or {}).get("categories") or [])]
        shares = [st.get("share") for st in ((plan.get("billing_plan") or {}).get("stages") or [])]
        for x in rates + shares:
            m = re.match(r"\s*(\d+(?:[.,]\d+)?)", str(x or ""))
            if m:
                allowed_pct.add(m.group(1))
        for m in list(CODE_AMT.finditer(scrub)) + list(SYM_AMT.finditer(scrub)):
            amt = norm_amount((m.group(2) or m.group(3)) if m.re is CODE_AMT else m.group(1))
            if amt.rstrip(".,") not in allowed and amt not in allowed:
                problems.append(f"the amount '{m.group(0).strip()}' did not come from the script or the founder")
        for m in PCT.finditer(scrub):
            if m.group(1) not in allowed_pct:
                problems.append(f"the percentage '{m.group(0)}' did not come from the script or the founder")
    return problems, warns


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", nargs="?")
    ap.add_argument("--text")
    ap.add_argument("--plan")
    ap.add_argument("--supplied", action="append", default=[])
    ap.add_argument("--english")
    ap.add_argument("--also", action="append", default=[],
                    help="another JSON file whose figures may be quoted: history.json (register totals), a preview stage's plan")
    a = ap.parse_args()
    if a.text is None and not a.file:
        raise C.Stop("give a file or --text")
    if a.text is not None:
        text = a.text
    else:
        if not os.path.exists(a.file):
            raise C.Stop(f"there is no file at {a.file}")
        text = open(a.file, encoding="utf-8").read()
    plan = C.load_json(a.plan, "plan file") if a.plan else None
    also = [C.load_json(x, "file") for x in a.also]
    problems, warns = check(text, plan, a.supplied, a.english, also)
    for p in problems:
        print("PROBLEM:", p)
    for w in warns:
        print("WARN:", w)
    print(f"{len(problems)} problems, {len(warns)} warnings")
    return 1 if problems else 0


if __name__ == "__main__":
    C.run_main(main)
