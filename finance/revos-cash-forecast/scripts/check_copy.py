#!/usr/bin/env python3
"""Check the forecast's founder-facing copy (the reading, the note, the chat summary) against the banned
patterns in references/banned-patterns.md and length limits.

Usage:
  python3 scripts/check_copy.py <file>               check a text or markdown file
  python3 scripts/check_copy.py --text "some copy"   check a string
  add --max-words N or --max-chars N to enforce a limit
  add --currency USD (the founder's currency) to flag any other currency's sign in the copy
Prints PROBLEM and WARN lines and a count. Standard library only.
Exit 0 clean, 1 with problems, 2 when the file is missing.
"""
import argparse
import re
import sys
from pathlib import Path

PROBLEM_PATTERNS = {
    r"[\u2014\u2013]": "em or en dash",
    r"\bin today'?s (fast-paced|digital|ever-changing)": "stock opener",
    r"\bit'?s not (just )?[^.]{1,40}, it'?s\b": "contrast reveal",
    r"\b(game[- ]changer|delve|unlock(s|ing)?|elevate(s|d)?|seamless(ly)?|leverag(e|es|ing))\b": "filler word",
    r"\b(I mean|to be honest|if I'?m being honest|let'?s be real)\b": "announced honesty",
    r"\b(healthy|in good shape|in great shape|comfortable position|looking good|solid position)\b":
        "comfort word with no number: say the lowest balance and the week",
    r"\b(should be (fine|ok|okay|alright)|you'?ll be (fine|ok|okay)|you will be (fine|ok|okay)|nothing to worry|"
    r"no need to worry|you'?re (fine|safe|good|ok|okay))\b": "reassurance the forecast cannot give",
    r"\b(safe|safely|plenty|can easily afford|you can afford|no problem)\b": "promise: give the stress-case figure instead",
    r"\bguarantee(d|s)?\b": "promise of a result",
    r"\bcash is king\b": "slogan",
    r"\b(you should|I recommend|I'?d recommend|consider) (borrow|taking a loan|a loan|an overdraft|getting an overdraft|"
    r"a credit card|invoice finance|factoring)": "borrowing advice: send it to the accountant",
    r"\byou(?:'ll| will)? owe\b": "tax or a bill worked out: amounts come from the founder or their accountant",
    r"\b(set aside|put aside|reserve) (about |around |roughly )?\d+ ?(%|per ?cent) (of [a-z ]+ )?for tax": "tax worked out by rate: the figure comes from the accountant",
    r"\btax (rate|bill|liability) (of|is|will be) (about |around )?\S*\d": "tax worked out: the figure comes from the accountant",
    r"\b(by law|legally|the law (requires|says)|you are required to|statutory (deadline|interest|penalt\w*)|"
    r"penalt(y|ies) for (paying )?late|must (legally )?be (paid|filed|submitted|lodged|made)|require[sd]?|requirement|"
    r"deadlines?|due by law|compulsory|mandatory)\b": "says what a law or an authority requires: that is for the founder's accountant or lawyer",
    r"\b(norm|industry|benchmarks?|most (small |other )?(businesses|firms|companies|founders)|typical(ly)? (for|of|in)|"
    r"average (for|among|business|firm|company)|businesses like yours|rule of thumb)\b":
        "a claim about other businesses: the forecast only knows this business's own figures",
    r"\b(bank holidays?|federal holidays?|public holidays?|tax year (starts|ends|runs))\b": "assumes a country's calendar: dates come from the founder",
    r"\[STAT\]": "internal placeholder in founder copy",
    r"\b(Merigrove|Business Audit)\b": "promotion in the founder's file: the bridge line goes in chat only",
    r"\bin today'?s (economy|climate|market)\b": "stock opener",
}
WARN_PATTERNS = {
    r"\bmore\b": "'more' as an intensifier: is a specific comparison possible?",
    r"!": "exclamation mark in business copy",
    r"\b(robust|cutting[- ]edge|world[- ]class|best[- ]in[- ]class|innovative)\b": "vague superlative",
    r"\b\d+(\.\d+)?%": "percentage: is it sourced?",
    r"\b(about|around|roughly|approximately|circa)\s+\S{0,3}\d": "rounded figure in prose: copy the script's figure",
    r"\bprobably\b": "hedge: say what the forecast shows",
}


SIGNS = {"GBP": "£", "EUR": "€", "INR": "₹", "JPY": "¥"}


def check(text, max_words=None, max_chars=None, currency=None):
    problems, warns = [], []
    if currency:
        cur = currency.upper()
        for code, sym in SIGNS.items():
            if code != cur and sym in text:
                problems.append(f"'{sym}' in copy for a founder whose currency is {cur}: assumes a country")
        if cur not in ("USD", "AUD", "SGD", "CAD", "NZD", "HKD") and re.search(r"(?<![A-Z])\$\d", text):
            problems.append(f"'$' in copy for a founder whose currency is {cur}: assumes a country")
    for pat, why in PROBLEM_PATTERNS.items():
        for m in re.finditer(pat, text, re.I):
            problems.append(f"{why}: '{text[max(0, m.start()-20):m.end()+20].strip()}'")
    for pat, why in WARN_PATTERNS.items():
        for m in re.finditer(pat, text, re.I):
            warns.append(f"{why}: '{text[max(0, m.start()-20):m.end()+20].strip()}'")
    for sent in re.split(r"(?<=[.!?])\s+", text):
        if re.search(r"\brunway\b", sent, re.I) and not re.search(r"bad[- ]quarter|stress", sent, re.I):
            problems.append(f"runway quoted without saying it is the bad-quarter figure: '{sent.strip()[:80]}'")
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
    a.add_argument("--currency")
    args = a.parse_args()
    if args.text is None and (not args.file or not Path(args.file).exists()):
        print(f"STOP: there is no file at {args.file}. Nothing was checked.")
        sys.exit(2)
    text = args.text if args.text is not None else Path(args.file).read_text(encoding="utf-8")
    problems, warns, words = check(text, args.max_words, args.max_chars, args.currency)
    for x in problems:
        print("PROBLEM:", x)
    for x in warns:
        print("WARN:", x)
    print(f"{len(problems)} problems, {len(warns)} warnings, {words} words, {len(text)} characters")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
