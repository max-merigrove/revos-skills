#!/usr/bin/env python3
"""Check founder-facing copy against the banned patterns and length limits.

Usage:
  python3 scripts/check_copy.py <file>                check a text or markdown file (the report, the note)
  python3 scripts/check_copy.py --text "some copy"    check a string (the chat summary)
  add --report to also refuse anything promotional or internal inside a founder's file
  add --max-words N or --max-chars N to enforce a limit
Prints PROBLEM and WARN lines and a count; exit 1 on any PROBLEM, 2 on a missing file. Standard library only.
PROBLEM_PATTERNS carry the Merigrove base list plus this skill's funnel list (references/banned-patterns.md),
including stating what a law requires, computing tax and naming one country's rules.
"""
import argparse
import hashlib
import os
import re
import sys

PROBLEM_PATTERNS = {
    "[\u2014\u2013]": "em or en dash",
    r"->|\u2192|\u21d2|=>": "arrow; write the words",
    r"\bin today'?s (fast-paced|digital|ever-changing|competitive)": "stock opener",
    r"\bit'?s not (just )?[^.]{1,40}, it'?s\b": "contrast reveal",
    r"\b(game[- ]changer|delve|unlock(s|ing)?|elevate(s|d)?|seamless(ly)?|leverag(e|es|ing)|supercharge|"
    r"skyrocket|turbocharge)\b": "filler word",
    r"\b(I mean|to be honest|if I'?m being honest|let'?s be real|honestly)\b": "announced honesty",
    # funnel list (references/banned-patterns.md, this skill's list)
    r"\bleaky (bucket|funnel)\b|\bplug (the|your|those) leaks?\b": "funnel cliche",
    r"\boptimi[sz]e (every|each|all) (stage|step)s?\b|\boptimi[sz]e your (whole |entire )?funnel\b": "advice with no stage",
    r"\b(industry (average|standard|benchmark)s?|typical(ly)? (conversion|close|show|booking|opt-?in) rates?|"
    r"average (conversion|close|show|booking|opt-?in) rates?|benchmark (conversion|close|show) rates?)\b":
        "benchmark the method does not hold",
    r"\bmost (small )?(businesses|founders|agencies|coaches|consultants|companies|people|firms|studios|"
    r"freelancers|practices) (see|get|convert|close|achieve|aim for|hit|average|manage|expect)\b":
        "benchmark the method does not hold",
    r"\b\d+(\.\d+)?\s?(%|per cent) of (leads|businesses|founders|people|prospects|buyers|visitors|enquiries|"
    r"companies|customers) (never|don'?t|do not|will|are|who)\b": "unsourced statistic about the world",
    r"\b(conversion|close|closing|show|show-up|booking|opt-?in) rates?\b[^.]{0,40}\b(typically|usually|normally|"
    r"tend to|generally)\b|\b(well-run|top|good|healthy) (firms|businesses|agencies|coaches) (often )?(hit|get|see|"
    r"convert|close)\b": "benchmark the method does not hold",
    r"\b(just|simply) (get|buy|generate|add) (more )?leads\b|\bmore leads\b": "volume as the reflex answer",
    r"\b(funnel|growth) hacks?\b|\bhack your\b": "hype",
    r"\b(guarantee[sd]?|you will (get|make|win|close|double)|double your|triple your|10x your)\b": "promise of a result",
    r"\b(it depends|you might want to|you may want to|consider (improving|optimi[sz]ing|looking at))\b":
        "soft verdict",
    r"\bblended (conversion |close |show )?rates?\b": "blended rate",
    r"[,;:]\s*\.(?!\d)|\s[,.;:](?=\s|$)": "stray punctuation; a phrase was cut or left half-edited",
    r"\[STAT\]|\[VERIFY\]": "internal placeholder left in founder copy; use [NEED: ...]",
    # global by default (Build Standard 0.1): never say what a law requires, never compute tax
    r"\b(the law|by law|legally|regulations?)\b[^.]{0,30}\b(requires?|required|must|obliged|says)\b|"
    r"\blegal requirement\b|\byou must register\b": "states what a law requires; point to the rules where the "
                                                     "founder and their contacts are instead",
    r"\btax (bill|due|owed|liability|rate|return)\b|\b(VAT|GST|sales tax|income tax|payroll tax|social charges?)\b"
    r"[^.]{0,15}\b(at|of|is|comes to)\s+[^.]{0,6}\d": "computes or quotes tax; the founder's accountant supplies it",
    r"\b(GDPR|CAN-SPAM|CASL|TCPA|CCPA|PDPA)\b": "names one country's rules; use the one generic line instead",
}
# Named rule-makers and internal people are matched by hash, so this file does not itself name them.
NAME_HASHES = {
    "f67234c0520b7198": "internal source named in founder copy",
    "15524f77be9736fa": "internal source named in founder copy",
    "fa193c8cc820b3b2": "names one country's rules; use the one generic line instead",
    "8c78b239a5940288": "names one country's tax authority; the founder's accountant is the route",
    "384c0b6dc96e6cef": "names one country's tax authority; the founder's accountant is the route",
}
REPORT_ONLY = {
    r"\bMerigrove\b": "Merigrove named inside the founder's file; the one line belongs at the end of the chat",
    r"\[BUSINESS_AUDIT_URL\]|\bBusiness Audit\b": "the bridge belongs in the chat, not the file",
    r"\bMRG-\d+": "internal source named in founder copy",
}
WARN_PATTERNS = {
    r"\bmore\b": "'more' as an intensifier: is a specific comparison possible?",
    r"!": "exclamation mark in business copy",
    r"\b(robust|cutting[- ]edge|world[- ]class|best[- ]in[- ]class|innovative|powerful)\b": "vague superlative",
    r"\b(TOFU|MOFU|BOFU|AARRR|CAC|LTV|CRO|MQL|SQL)\b": "jargon: say it in plain words",
    r"\boverall conversion( rate)?\b": "an overall rate hides where people drop; is it needed?",
    r"\bfunnel\b.*\bfunnel\b.*\bfunnel\b": "the word funnel three times in one line",
}


def check(text, max_words=None, max_chars=None, report=False):
    problems, warns = [], []
    pats = dict(PROBLEM_PATTERNS)
    if report:
        pats.update(REPORT_ONLY)
    for pat, why in pats.items():
        for m in re.finditer(pat, text, re.I):
            problems.append(f"{why}: '{text[max(0, m.start() - 25):m.end() + 25].strip()}'")
    for m in re.finditer(r"[A-Za-z][A-Za-z-]+", text):
        why = NAME_HASHES.get(hashlib.sha256(m.group(0).lower().encode()).hexdigest()[:16])
        if why:
            problems.append(f"{why}: '{text[max(0, m.start() - 25):m.end() + 25].strip()}'")
    for pat, why in WARN_PATTERNS.items():
        for m in re.finditer(pat, text, re.I):
            warns.append(f"{why}: '{text[max(0, m.start() - 25):m.end() + 25].strip()}'")
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
    a.add_argument("--report", action="store_true")
    a.add_argument("--max-words", type=int)
    a.add_argument("--max-chars", type=int)
    args = a.parse_args()
    if args.text is None and (not args.file or not os.path.exists(args.file)):
        print(f"STOP: there is no file at {args.file}. Nothing was checked.")
        sys.exit(2)
    text = args.text if args.text is not None else open(args.file, encoding="utf-8").read()
    problems, warns, words = check(text, args.max_words, args.max_chars, args.report)
    for x in problems:
        print("PROBLEM:", x)
    for x in warns:
        print("WARN:", x)
    print(f"{len(problems)} problems, {len(warns)} warnings, {words} words, {len(text)} characters")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
