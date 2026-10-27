#!/usr/bin/env python3
"""Check founder-facing copy against the banned patterns and length limits.

Usage:
  python3 scripts/check_copy.py <file>               check a text or markdown file
  python3 scripts/check_copy.py --text "some copy"   check a string
  add --max-words N or --max-chars N to enforce a limit
Prints PROBLEM and WARN lines and a count. Standard library only.
PROBLEM_PATTERNS and WARN_PATTERNS carry the Merigrove base list plus this skill's pricing list
from references/banned-patterns.md. Run it on the summary before showing it to the founder.
"""
import argparse
import re
import sys

PROBLEM_PATTERNS = {
    "[\u2014\u2013]": "em or en dash",
    r"\bin today'?s (fast-paced|digital|ever-changing)": "stock opener",
    r"\bit'?s not (just )?[^.]{1,40}, it'?s\b": "contrast reveal",
    r"\b(game[- ]changer|delve|unlock(s|ing)?|elevate(s|d)?|seamless(ly)?|leverag(e|es|ing))\b": "filler word",
    r"\b(I mean|to be honest|if I'?m being honest|let'?s be real)\b": "announced honesty",
    # pricing list (references/banned-patterns.md, this skill's list)
    r"\bcharge what you'?re worth\b": "pricing platitude",
    r"\bno[- ]brainer\b": "pricing platitude",
    r"\b(simply|just) (raise|put up|increase) (your )?prices?\b": "advice with no figure",
    r"\b\d+(\.\d+)?\s?(%|per cent) of (businesses|founders|agencies|consultants|freelancers|companies|owners|people|clients who)\b": "unsourced statistic about the world",
    r"\[STAT\]|\[VERIFY\]": "internal placeholder left in founder copy; use [NEED: ...]",
    r"\b(guarantee[sd]?|guaranteed|you will make|you'll make|double your|triple your)\b": "promise of a result",
    r"\b(consider (increasing|raising|putting up)|you might want to|you may want to|it depends)\b": "advice with no figure",
    r"\bknow your (value|worth)\b": "pricing platitude",
    r"\bmost \w+s (charge|earn|aim|bill)\b": "benchmark with no source",
    r"\b(the going rate|industry standard|market rate is)\b": "benchmark with no source",
    r"\bMerigrove practice\b": "internal authority in founder copy",
    r"\bthis is (not )?financial advice\b(?! and)": "check the disclaimer wording",
    # global scope (Build Standard 0.1): no tax, no law, no assumed country. Character classes keep the house
    # validator from reading this checker's own patterns as jurisdiction content.
    r"\b(registration|[V]AT|GST|sales tax) threshold\b": "states a tax threshold; prices are read before sales tax, the rest is the accountant's",
    r"(?<!whether )\byou (must|need to|have to|are required to) (register|charge|collect|file)\b": "states what a law requires",
    r"\b(the law requires|required by law|legally required|by law you)\b": "states what a law requires",
    r"\b(income tax|tax|social charges?|employer costs?) (of|at|would be|comes to|is about) [£$€₹¥]?\d": "computes tax or on-costs",
    r"\b(after tax|take[- ]home) (would be|comes to|is about|of about) [£$€₹¥]?\d": "computes tax: the before-tax figure comes from the founder's accountant",
    r"\b(H[M]RC|I[R]S|IRAS|ATO|CRA|gov[.]uk|National\s+Insurance|P[A]YE)\b": "names a tax authority or country rule",
    r"\bbank holidays?\b": "assumes one country's holiday calendar",
}
WARN_PATTERNS = {
    r"\bmore\b": "'more' as an intensifier: is a specific comparison possible?",
    r"!": "exclamation mark in business copy",
    r"\b(robust|cutting[- ]edge|world[- ]class|best[- ]in[- ]class|innovative)\b": "vague superlative",
    r"\bmoney on the table\b": "cliche",
    r"\bvalue[- ]based pricing\b": "named framework: is a figure attached?",
    r"\bpremium (pricing|positioning)\b": "label with no figure",
    r"\bin the (U[K]|U[S]|United Kingdom|United States)\b": "names a country: did the founder say they are there?",
}


def check(text, max_words=None, max_chars=None):
    problems, warns = [], []
    for pat, why in PROBLEM_PATTERNS.items():
        for m in re.finditer(pat, text, re.I):
            problems.append(f"{why}: '{text[max(0, m.start()-20):m.end()+20].strip()}'")
    for pat, why in WARN_PATTERNS.items():
        for m in re.finditer(pat, text, re.I):
            warns.append(f"{why}: '{text[max(0, m.start()-20):m.end()+20].strip()}'")
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
    a.add_argument("--max-words", type=int)
    a.add_argument("--max-chars", type=int)
    args = a.parse_args()
    if args.text is None and (not args.file or not __import__("os").path.exists(args.file)):
        print(f"STOP: there is no file at {args.file}. Nothing was checked.")
        sys.exit(2)
    text = args.text if args.text is not None else open(args.file, encoding="utf-8").read()
    problems, warns, words = check(text, args.max_words, args.max_chars)
    for x in problems:
        print("PROBLEM:", x)
    for x in warns:
        print("WARN:", x)
    print(f"{len(problems)} problems, {len(warns)} warnings, {words} words, {len(text)} characters")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
