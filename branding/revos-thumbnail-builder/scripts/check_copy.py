#!/usr/bin/env python3
"""Check founder-facing copy against the banned patterns and length limits.

Usage:
  python3 scripts/check_copy.py <file>               check a text or markdown file
  python3 scripts/check_copy.py --text "some copy"   check a string
  add --max-words N or --max-chars N to enforce a limit
Prints PROBLEM and WARN lines and a count. Standard library only.
Add --hooks to check a file of hook options, one per line: each must be 2 to 6 words (in Chinese and
Japanese about two characters count as a word; in Thai, Lao, Khmer and Burmese about three),
with no full stop, no dash, and no clickbait phrasing from references/banned-patterns.md.
"""
import argparse
import re
import sys
import unicodedata

PROBLEM_PATTERNS = {
    r"[\u2014\u2013]": "em or en dash",
    r"\bin today'?s (fast-paced|digital|ever-changing)": "stock opener",
    r"\bit'?s not (just )?[^.]{1,40}, it'?s\b": "contrast reveal",
    r"\b(game[- ]changer|delve|unlock(s|ing)?|elevate(s|d)?|seamless(ly)?|leverag(e|es|ing))\b": "filler word",
    r"\b(I mean|to be honest|if I'?m being honest|let'?s be real)\b": "announced honesty",
}
HOOK_PROBLEMS = {
    r"\byou won'?t believe\b": "clickbait: you won't believe",
    r"\b(shocking|insane|mind[- ]?blowing|jaw[- ]?dropping)\b": "clickbait adjective",
    r"\bwatch (till|until) the end\b": "watch-till-the-end bait",
    r"\b(gone wrong|not clickbait)\b": "clickbait phrase",
    r"\?{2,}|!{2,}": "stacked punctuation",
}
WARN_PATTERNS = {
    r"\bmore\b": "'more' as an intensifier: is a specific comparison possible?",
    r"!": "exclamation mark in business copy",
    r"\b(robust|cutting[- ]edge|world[- ]class|best[- ]in[- ]class|innovative)\b": "vague superlative",
    r"\b\d+(\.\d+)?%": "percentage: is it sourced?",
}


def hook_units(text):
    """Words a hook reads as. Space-separated words count one each; in Chinese and Japanese about two
    characters make a word, in Thai, Lao, Khmer and Burmese about three (a house working rule, the same
    one thumbnail.py uses)."""
    n = 0
    for tok in text.split():
        if not re.search(r"\w", tok):
            continue
        cjk = sum(1 for ch in tok if 0x3040 <= ord(ch) <= 0x30FF or 0x3400 <= ord(ch) <= 0x9FFF
                  or 0xF900 <= ord(ch) <= 0xFAFF)
        sea = sum(1 for ch in tok if (0x0E00 <= ord(ch) <= 0x0EFF or 0x1000 <= ord(ch) <= 0x109F
                                      or 0x1780 <= ord(ch) <= 0x17FF) and not unicodedata.category(ch).startswith("M"))
        n += max(1, -(-cjk // 2) + -(-sea // 3)) if (cjk or sea) else 1
    return n


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


def check_hooks(text):
    problems = []
    for n, line in enumerate([l.strip() for l in text.splitlines() if l.strip()], 1):
        line = re.sub(r"^[-*\d.)\s]+(?=\D)", "", line) if re.match(r"^[-*]|\d+[.)]\s", line) else line
        line = line.replace("|", " ")
        w = hook_units(line)
        if w > 6:
            problems.append(f"option {n} '{line}': {w} words, six is the hard limit")
        if re.search(r"[\U0001F000-\U0001FAFF\u2600-\u27BF]", line):
            problems.append(f"option {n} '{line}': an emoji prints as an empty box in a thumbnail typeface")
        if w < 2:
            problems.append(f"option {n} '{line}': one word is a label, not a hook")
        if line.endswith("."):
            problems.append(f"option {n} '{line}': ends in a full stop")
        hook_warns = {k: v for k, v in WARN_PATTERNS.items() if "%" not in k}  # numbers are checked against the payoff
        for pat, why in {**PROBLEM_PATTERNS, **HOOK_PROBLEMS, **hook_warns}.items():
            if re.search(pat, line, re.I):
                problems.append(f"option {n} '{line}': {why}")
    return problems


def main():
    a = argparse.ArgumentParser()
    a.add_argument("file", nargs="?")
    a.add_argument("--text")
    a.add_argument("--max-words", type=int)
    a.add_argument("--max-chars", type=int)
    a.add_argument("--hooks", action="store_true", help="the input is hook options, one per line")
    args = a.parse_args()
    text = args.text if args.text is not None else open(args.file, encoding="utf-8").read()
    if args.hooks:
        probs = check_hooks(text)
        for x in probs:
            print("PROBLEM:", x)
        print(f"{len(probs)} problems")
        sys.exit(1 if probs else 0)
    problems, warns, words = check(text, args.max_words, args.max_chars)
    for x in problems:
        print("PROBLEM:", x)
    for x in warns:
        print("WARN:", x)
    print(f"{len(problems)} problems, {len(warns)} warnings, {words} words, {len(text)} characters")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
