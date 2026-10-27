#!/usr/bin/env python3
"""Check founder-facing copy against the banned patterns.

Usage:
  python3 scripts/check_copy.py <file>               check a text or markdown file
  python3 scripts/check_copy.py --text "some copy"   check a string
  python3 scripts/check_copy.py --client "message"   also apply the client-message rules
  add --max-words N or --max-chars N to enforce a limit
Prints PROBLEM and WARN lines and a count. Exit 0 clean, 1 problems, 2 STOP. Standard library only.
PROBLEM_PATTERNS carry the Merigrove base list and this skill's scope list (references/banned-patterns.md).
CLIENT_PATTERNS apply to words the founder will send to a client (scope_kit.py applies them to every response).
"""
import argparse
import os
import re
import sys

PROBLEM_PATTERNS = {
    "[\u2014\u2013]": "em or en dash",
    r"\bin today'?s (fast-paced|digital|ever-changing|busy)": "stock opener",
    r"\bit'?s not (just )?[^.]{1,40}, it'?s\b": "contrast reveal",
    r"\b(game[- ]changer|delve|unlock(s|ing)?|elevate(s|d)?|seamless(ly)?|leverag(e|es|ing))\b": "filler word",
    r"\b(I mean|to be honest|if I'?m being honest|let'?s be real|honestly)\b": "announced honesty",
    r"\[STAT\]|\[VERIFY\]|\[TODO\]": "internal placeholder left in founder copy; use [NEED: ...]",
    # scope list
    r"\b(unfortunately|sadly)\b": "regret before a price (scope list)",
    r"\bI'?m afraid\b": "regret before a price (scope list)",
    r"\bas per my (last|previous) email\b": "passive-aggressive (scope list)",
    r"\bper our (agreement|contract)\b": "legalistic in a client message (scope list)",
    r"\b(legally binding|(is|are|be|fully|clause is|clauses are) enforceable|watertight|iron[- ]?clad|bulletproof (contract|clause)|protects you legally|legally protect(s|ed)?|you can (sue|enforce))\b":
        "legal claim: the skill never says a clause is enforceable",
    r"\b(guarantee[sd]?|guaranteed|you will (win|get paid|keep the client)|this will stop)\b": "promise of a result",
    r"\b(simply|just) (say no|charge them|tell them)\b": "advice with no wording",
    r"\bknow your (value|worth)\b|\bcharge what you'?re worth\b": "platitude",
    r"\bmost (clients|agencies|freelancers|founders|businesses|consultants) (will|do|expect|accept|assume)\b": "claim about other businesses with no source",
    r"\b\d+(\.\d+)?\s?(%|per cent) of (businesses|founders|agencies|clients|freelancers|projects)\b": "unsourced statistic",
    r"\bMerigrove (practice|recommends|says)\b": "internal authority in founder copy",
    # global rules (Build Standard 0.1): no statement of what a law requires, no tax arithmetic, no assumed country
    r"\b(the law (requires|says|states)|(legally|statutorily) (required|obliged|entitled)|required by law|by law,? (you|they|we|the client) (must|have to|are)|"
    r"you are (legally|statutorily) (required|entitled)|under (the )?[A-Z][A-Za-z]+( [A-Z][A-Za-z]+)* (Act|Regulations?|Directive)\b|statutory \w+)":
        "states what a law requires: point to a lawyer instead",
    r"(\b\d+([.,]\d+)?\s?(%|per ?cent)\s?(VAT|GST|HST|sales tax|tax|MwSt|USt|TVA|IVA|BTW|moms)\b|\b(VAT|GST|HST|sales tax|tax|MwSt|USt|TVA|IVA|BTW) (at|of|von|de) \d|"
    r"\b(with|incl\.?|including|inc\.?|inkl\.?) (VAT|GST|HST|sales tax|tax|MwSt\.?|USt\.?)[, ]+[£$€₹]?\d|\btax (on|is|would be|comes to) [£$€₹]?\d|"
    r"\d (with|incl\.?|including|inc\.?|inkl\.?) (VAT|GST|HST|sales tax|tax|MwSt|USt)\b|\bbrutto\b)":
        "tax arithmetic: prices stay before any sales tax; the accountant confirms the rest",
    r"\b((UK|US|English|Scots|Australian|Singapore|EU) law|under (UK|US|EU) (rules|law)|in the (UK|US),? (you|clients|businesses|the law))\b":
        "assumes a country: currency, dates, rules and holidays follow the founder",
}
WARN_PATTERNS = {
    r"\bmore\b": "'more' as an intensifier: is a specific comparison possible?",
    r"!": "exclamation mark in business copy",
    r"\b(robust|cutting[- ]edge|world[- ]class|best[- ]in[- ]class|innovative)\b": "vague superlative",
    r"\b(ongoing support|as needed|as required|ad[- ]hoc|unlimited)\b": "open-ended scope wording: give a quantity or a cap",
}
# Words the founder sends to a client. A price is not an apology and not a telling-off.
CLIENT_PATTERNS = {
    r"\b(sorry|apologi[sz]e|apologies)\b": "apology in a priced reply: you are offering work, not admitting a fault",
    r"\bscope creep\b": "jargon that blames the client",
    r"\b(you keep (asking|adding|sending|changing|wanting|requesting|coming back)|again and again|yet another|once again|every time you)\b": "telling-off tone",
    r"\b(I'?m (only|just) (asking|saying)|hope that'?s (ok|okay|alright)|if that'?s (ok|okay|alright)|does that make sense|"
    r"(is|would) (that|this) (be )?(ok|okay|alright|all right|fine)( for you)?|hope you don'?t mind)\b": "hedging that invites a no",
    r"\b(contract|clause|breach|terms and conditions|T&Cs?)\b": "legal word in a client message: say 'what we agreed'",
    r"\b(policy|policies)\b": "policy language: you are a person, not a department",
}
REFUSAL_WORDS = re.compile(
    r"\b(outside|beyond|not (part of|included|covered|in (the|our|your))|isn'?t (part of|included|covered)|out of scope|not in scope|"
    r"can'?t|cannot|won'?t|unable|don'?t (usually|normally|do)|unfortunately|extra charge|additional charge|chargeable)\b", re.I)
YES_WORDS = re.compile(r"\b(happy|love|great|good|lovely|yes|sure|of course|keen|glad|smart|nice|brilliant|makes sense|idea|can see|know)\b", re.I)


def _hits(patterns, text):
    out = []
    for pat, why in patterns.items():
        for m in re.finditer(pat, text, re.I):
            out.append(f"{why}: '{text[max(0, m.start() - 25):m.end() + 25].strip()}'")
    return out


def check(text, max_words=None, max_chars=None, client=False):
    # A [NEED: ...] flag is the honest gap marker, so its inner words are not judged as copy.
    scan = re.sub(r"\[NEED:[^\]]*\]", "[NEED]", text)
    problems = _hits(PROBLEM_PATTERNS, scan)
    warns = _hits(WARN_PATTERNS, scan)
    if client:
        problems += _hits(CLIENT_PATTERNS, scan)
        body = re.sub(r"^\W*(hi|hey|hello|dear|morning|afternoon|evening)\b[^.!?,\n]{0,30}[!,.]?\s*", "", scan.strip(), flags=re.I)
        first = re.split(r"(?<=[.?!])\s+|\n", body, maxsplit=1)[0] if body else ""
        if REFUSAL_WORDS.search(first) and not YES_WORDS.search(first):
            problems.append(f"opens with a refusal; open with yes, or with what the client wants: '{first[:70]}'")
    words = len(re.findall(r"\b\w[\w'-]*\b", text))
    if max_words and words > max_words:
        problems.append(f"{words} words, limit {max_words}")
    if max_chars and len(text) > max_chars:
        problems.append(f"{len(text)} characters, limit {max_chars}")
    return problems, warns, words


def main():
    a = argparse.ArgumentParser()
    a.add_argument("file", nargs="?")
    a.add_argument("--text")
    a.add_argument("--client")
    a.add_argument("--max-words", type=int)
    a.add_argument("--max-chars", type=int)
    args = a.parse_args()
    if args.client is not None:
        text, client = args.client, True
    elif args.text is not None:
        text, client = args.text, False
    else:
        if not args.file or not os.path.exists(args.file):
            print(f"STOP: there is no file at {args.file}. Nothing was checked.")
            sys.exit(2)
        text, client = open(args.file, encoding="utf-8").read(), False
    problems, warns, words = check(text, args.max_words, args.max_chars, client)
    for x in problems:
        print("PROBLEM:", x)
    for x in warns:
        print("WARN:", x)
    print(f"{len(problems)} problems, {len(warns)} warnings, {words} words, {len(text)} characters")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
