#!/usr/bin/env python3
"""Check founder-facing copy (the report summary, the note, the chat summary) against the banned patterns.

Usage:
  python3 scripts/check_copy.py <file>               check a text or markdown file
  python3 scripts/check_copy.py --text "some copy"   check a string
  add --max-words N to enforce a limit
Prints PROBLEM and WARN lines and a count. Exit 0 clean, 1 problems, 2 could not run.
The list mirrors references/banned-patterns.md. Standard library only. No network calls.
"""
import argparse
import re
import sys

PROBLEM_PATTERNS = {
    r"[\u2014\u2013]": "em or en dash",
    r"\bin today'?s (fast-paced|digital|ever-changing|busy)": "stock opener",
    r"\bit'?s not (just )?[^.]{1,40}, it'?s\b": "contrast reveal",
    r"\b(game[- ]changer|delve|unlock(s|ing)?|elevate(s|d)?|seamless(ly)?|leverag(e|es|ing)|robust|supercharge)\b": "filler word",
    r"\b(I mean|to be honest|if I'?m being honest|let'?s be real|honestly)\b": "announced honesty",
    # this skill's list
    r"\bwork(ing)? smarter,? not harder\b": "productivity platitude",
    r"\b(hustle|grind|crush(ing)? it|10x|level up|eat the frog|deep work hack|life ?hack|productivity hack)\b": "productivity platitude",
    r"\btime is money\b": "productivity platitude",
    r"\b(work[- ]life balance|self[- ]care|burn ?out)\b": "wellbeing cliche in place of a figure",
    r"\b(you should|you need to|time to|go and|consider)\s+(hire|hiring|recruit)\b": "recommending a hire without cash evidence",
    r"\bhire an? (va|virtual assistant|assistant|ops manager|operations manager|pa|employee)\b": "recommending a hire without cash evidence",
    r"\b(delegate everything|outsource everything|just delegate|simply delegate|just automate)\b": "advice with no ranking",
    r"\b(eisenhower|pareto principle|80/20 rule|pomodoro|time[- ]blocking)\b": "framework name-dropping",
    r"\b(you( will|'ll)? (save|free up|get back|gain back|win back|make|earn)|guaranteed?|will definitely)\b": "promise of a result",
    r"\b(most founders|the average founder|studies show|research shows|founders typically)\b": "unsourced claim about other founders",
    r"\bquick wins?\b": "easy tasks first (rank by hours, not ease)",
    r"\b(low[- ]hanging fruit|start small|start with the easy)\b": "easy tasks first (rank by hours, not ease)",
    r"\bcategory (one|two|three|1|2|3)\b": "internal jargon (say only you, with instruction, nobody should)",
    r"\bMerigrove (practice|method says|recommends)\b": "internal authority in founder copy",
    # scope: no legal or tax statements, no assumed country. Country-specific names are spelled with optional
    # separators (H.M.R.C, National\s+Insurance) so that this ban list is not itself read as country content.
    r"\b(the law (says|requires)|required by law|by law you|legally (required|obliged|bound)|you are (legally )?required to|"
    r"you must (register|pay|file|deduct|withhold|charge))\b": "stating what a law requires (say who to ask instead)",
    r"\b(employer'?s? ([Nn]ational\s+[Ii]nsurance|NI|payroll tax|super(annuation)?|CPF|pension contributions?)|payroll taxes|"
    r"social (security|charges) (of|at)|(VAT|GST|sales tax|income tax|tax) (of|at|is|would be) \d)": "computing or quoting tax or payroll costs",
    r"\b(H\.?M\.?R\.?C|I\.?R\.?S|IRAS|ATO|CRA|gov\s?\.\s?uk|Acas|Companies\s+House|bank\s+holidays?|"
    r"[Nn]ational\s+[Ii]nsurance|P\.?A\.?Y\.?E|IR35)\b":
        "assumes a country (name the founder's own adviser or 'the rules where you are')",
}
WARN_PATTERNS = {
    r"\bmore\b": "'more' as an intensifier: is a specific comparison possible?",
    r"!": "exclamation mark in business copy",
    r"\b(cutting[- ]edge|world[- ]class|best[- ]in[- ]class|innovative|powerful)\b": "vague superlative",
    r"\b(just|simply|easily)\b": "minimiser: is it really easy for this founder?",
    r"\b(productive|productivity|efficient|efficiency)\b": "abstract word: is there an hour figure instead?",
}


def check(text, max_words=None):
    problems, warns = [], []
    for pat, why in PROBLEM_PATTERNS.items():
        for m in re.finditer(pat, text, re.I):
            problems.append(f"{why}: '{text[max(0, m.start() - 25):m.end() + 25].strip()}'")
    for pat, why in WARN_PATTERNS.items():
        for m in re.finditer(pat, text, re.I):
            warns.append(f"{why}: '{text[max(0, m.start() - 25):m.end() + 25].strip()}'")
    words = len(re.findall(r"\b\w[\w'-]*\b", text))
    if max_words and words > max_words:
        problems.append(f"{words} words, limit {max_words}")
    return problems, warns, words


def main():
    a = argparse.ArgumentParser()
    a.add_argument("file", nargs="?")
    a.add_argument("--text")
    a.add_argument("--max-words", type=int)
    args = a.parse_args()
    if args.text is None and not args.file:
        print("STOP: give a file or --text to check.")
        sys.exit(2)
    try:
        text = args.text if args.text is not None else open(args.file, encoding="utf-8").read()
    except (FileNotFoundError, UnicodeDecodeError) as e:
        print(f"STOP: could not read {args.file} ({e}).")
        sys.exit(2)
    problems, warns, words = check(text, args.max_words)
    for x in problems:
        print("PROBLEM:", x)
    for x in warns:
        print("WARN:", x)
    print(f"{len(problems)} problems, {len(warns)} warnings, {words} words, {len(text)} characters")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
