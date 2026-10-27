#!/usr/bin/env python3
"""Check founder-facing copy against the banned patterns and length limits.

Usage:
  python3 scripts/check_copy.py <file>               check a text or markdown file
  python3 scripts/check_copy.py --text "some copy"   check a string
  add --max-words N or --max-chars N to enforce a limit
Prints PROBLEM and WARN lines and a count. Exit 0 clean, 1 problems, 2 STOP (no file).
Carries the Merigrove base list plus this skill's hiring list from references/banned-patterns.md.
Standard library only. No network calls.
"""
import argparse
import os
import re
import sys

PROBLEM_PATTERNS = {
    "[\u2014\u2013]": "em or en dash",
    r"\bin today'?s (fast-paced|digital|ever-changing)": "stock opener",
    r"\bit'?s not (just )?[^.]{1,40}, it'?s\b": "contrast reveal",
    r"\b(game[- ]changer|delve|unlock(s|ing)?|elevate(s|d)?|seamless(ly)?|leverag(e|es|ing)|robust)\b": "filler word",
    r"\b(I mean|to be honest|if I'?m being honest|let'?s be real)\b": "announced honesty",
    r"\[STAT\]|\[VERIFY\]": "internal placeholder left in founder copy; use [NEED: ...]",
    # hiring list (references/banned-patterns.md, this skill's list)
    r"\byou can (definitely|easily|comfortably) afford\b|\byou can afford (it|this|to hire)\b": "affordability promise",
    r"\binvest in yourself\b|\btake the leap\b|\bgo for it\b|\bjust hire\b": "hiring cheerleading",
    r"\b(you'?ll|you will|you should) be ready (to hire )?(by|in)\b|\bready by (january|february|march|april|may|june|july|august|september|october|november|december|spring|summer|autumn|winter|next)\b": "readiness date: state conditions, not a date",
    r"\bin \d+ (months|weeks) you (can|could|will be able to) hire\b": "readiness date: state conditions, not a date",
    r"\b(guarantee[sd]?|guaranteed|risk[- ]free|you will make|you'll make)\b": "promise of a result",
    r"\b(consider hiring|you might want to|you may want to|it depends)\b": "advice with no figure",
    r"\bmost (founders|businesses|small businesses|owners) (hire|can|should|wait)\b": "benchmark with no source",
    r"\b\d+(\.\d+)?\s?(%|per cent) of (businesses|founders|small businesses|hires|companies|owners)\b": "unsourced statistic about the world",
    r"\b(this is|this isn'?t|not) (legal|tax|employment) advice\b(?! and)": "check the disclaimer wording",
    r"\b(rock ?star|ninja|guru|fast[- ]paced|work hard,? play hard|self[- ]starter)\b": "recruitment cliche",
    # scope (Build Standard 0.1): no statement of what a law requires, no status ruling, no tax or on-cost sums
    r"\b(the law|legislation|regulations?) (requires?|says you must|obliges?)\b|\brequired by law\b|\bby law,? you\b|"
    r"\byou are (legally )?(required|obliged) to\b|\byou('re| are) legally\b|\bit is (illegal|unlawful)\b|\byou must legally\b":
        "states what a law requires: name the professional where they hire instead",
    r"\b(they|she|he|this person|the hire|your va|the role) (is|are|would be|counts? as|will count as) "
    r"(legally |technically )?(self-employed|an? employee|an? contractor|an? worker|an? freelancer)\b(?! or)":
        "judges employee or contractor status: the skill never decides it; name the professional",
    r"\b(so|then) (no|you won'?t need|you don'?t need|you do not need) (payroll|a contract|to (pay|withhold|deduct))\b":
        "draws a legal or payroll conclusion: name the professional",
}
WARN_PATTERNS = {
    r"\bmore\b": "'more' as an intensifier: is a specific comparison possible?",
    r"!": "exclamation mark in business copy",
    r"\b(cutting[- ]edge|world[- ]class|best[- ]in[- ]class|innovative)\b": "vague superlative",
    r"\bburn ?out\b|\bburnt out\b": "keep the founder's own words; do not diagnose",
}
# A line that puts a rate on an employer charge or tax is a regulated calculation the skill never makes
ONCOST_LINE = re.compile(r"(employer|payroll|social|on-?costs?|pension|retirement|withholding|contributions?)", re.I)
RATE = re.compile(r"\d(\.\d+)?\s?(%|per cent)")
CHARGE = re.compile(r"\b(tax|taxes|contributions?|charges?|on-?costs?|withholding|insurance)\b", re.I)
# Country-specific tax, payroll and employment terms: a sign the copy assumed a country. Mirror the founder's own
# words only; never introduce one.
JURISDICTION = re.compile(r"\b(hmrc|irs|paye|ir35|fica|futa|suta|w-?2|1099|cpf|mpf|superannuation|super guarantee|"
                          r"national insurance|employment allowance|living wage|gov\.uk|right to work)\b", re.I)


def check(text, max_words=None, max_chars=None):
    problems, warns = [], []
    for pat, why in PROBLEM_PATTERNS.items():
        for m in re.finditer(pat, text, re.I):
            problems.append(f"{why}: '{text[max(0, m.start()-20):m.end()+20].strip()}'")
    for pat, why in WARN_PATTERNS.items():
        for m in re.finditer(pat, text, re.I):
            warns.append(f"{why}: '{text[max(0, m.start()-20):m.end()+20].strip()}'")
    for line in text.splitlines():
        if ONCOST_LINE.search(line) and CHARGE.search(line) and RATE.search(line):
            problems.append(f"looks like a tax or employer-charge calculation; the skill never makes one: '{line.strip()[:90]}'")
        for m in JURISDICTION.finditer(line):
            warns.append(f"country-specific term '{m.group(0)}': keep it only if the founder used it, never as a rule")
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
    if args.text is None and (not args.file or not os.path.exists(args.file)):
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
