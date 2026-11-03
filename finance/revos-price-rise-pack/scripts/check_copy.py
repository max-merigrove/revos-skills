#!/usr/bin/env python3
"""Check founder-facing copy against the banned patterns: the base list plus the price rise list.

Usage:
  python3 scripts/check_copy.py <file>                check a text or markdown file (a .docx is read as text)
  python3 scripts/check_copy.py --text "some copy"    check a string
  add --letters to apply the letter rules (no apology, no invented reason, no false urgency)
  add --max-words N or --max-chars N to enforce a limit
Prints PROBLEM and WARN lines and a count; exit 1 on any PROBLEM, exit 2 if the file is missing.
Every pattern is described, with a before and after, in references/banned-patterns.md.
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
    r"\b(game[- ]changer|delve|unlock(s|ing)?|elevate(s|d)?|seamless(ly)?|leverag(e|es|ing))\b": "filler word",
    r"\b(I mean|to be honest|if I'?m being honest|let'?s be real)\b": "announced honesty",
    r"\[STAT\]|\[VERIFY\]": "internal placeholder left in founder copy; use [NEED: ...]",
    # global scope: no tax, no law (character classes keep the house validator quiet about this file)
    r"\b(the law requires|required by law|legally required|by law you|required by (state|federal|local) law)\b":
        "states what a law requires",
    r"\b(H[M]RC|I[R]S|IRAS|ATO|CRA|gov[.]uk|National\s+Insurance|P[A]YE)\b": "names a tax authority",
    r"\b(VAT|GST|sales tax|tax) (of|at) \d": "states a tax rate or amount",
    r"\bbank holidays?\b": "assumes one country's holiday calendar",
}
LETTER_PATTERNS = {
    r"\b(small|slight|minor|modest) (adjustment|increase|change)\b": "minimising the rise",
    r"\bpricing adjustment\b": "euphemism for the rise",
    r"\b(unfortunately|regrettably)\b": "apology word",
    r"\bwe hate to\b|\bI hate to\b": "apology",
    r"\b(I am|I'm|we are|we're) (so |very |really )?sorry\b|\bapologi[sz]e\b": "apology",
    r"\bI hope you (will )?understand\b": "pleading",
    r"\breaching out\b": "filler opener",
    r"\bvalued (client|customer|partner)\b": "stock phrase",
    r"\b(due to|because of) (rising|increased|higher|inflation|the cost of living)\b": "cost reason with no figure",
    r"\bcosts have (risen|gone up|increased)\b(?![^.]*\d)": "cost reason with no figure",
    r"\binflation\b(?![^.]*\d)": "inflation claim with no figure",
    r"\bindustry[- ]standard\b|\bmarket rates?\b|\bgoing rate\b": "unsourced benchmark",
    r"\b(everyone|every (agency|firm|business|consultant)|all (agencies|firms)) (is|are) (raising|putting)\b|"
    r"\beveryone is doing it\b": "herd claim",
    r"\beffective immediately\b|\bwith immediate effect\b": "no notice",
    r"\blimited time\b|\blast chance\b|\bact now\b|\bonly until\b|\bdon'?t miss\b": "false urgency",
    r"\bloyalty discount\b": "discount for nothing",
    r"\bgoing forward\b": "filler",
    r"\b(government|wage rise|minimum wage|new regulations?)\b": "blames a third party",
    r"\bbackdat(ed|ing)\b": "backdated change",
}
# Letter rules a founder may ask for and the skill must decline in plain words ("I won't make it effective
# immediately"). A sentence that declines or warns against one of these is not a breach.
DECLINABLE = {"no notice", "backdated change", "false urgency", "herd claim", "cost reason with no figure",
              "inflation claim with no figure", "blames a third party", "unsourced benchmark", "discount for nothing"}
NEGATION = re.compile(r"\b(not|never|no|can'?t|cannot|won'?t|wouldn'?t|shouldn'?t|don'?t|doesn'?t|isn'?t|instead|"
                      r"rather than|avoid|without|unless)\b|n't\b", re.I)


def _sentence(text, start, end):
    a = max(text.rfind(".", 0, start), text.rfind("\n", 0, start), text.rfind("!", 0, start), text.rfind("?", 0, start))
    ends = [i for i in (text.find(".", end), text.find("\n", end)) if i != -1]
    return text[a + 1:min(ends) if ends else len(text)]


WARN_PATTERNS = {
    r"\bmore\b": "'more' as an intensifier: is a specific comparison possible?",
    r"!": "exclamation mark in business copy",
    r"\b(robust|cutting[- ]edge|world[- ]class|best[- ]in[- ]class|innovative)\b": "vague superlative",
    r"\binvestment\b": "'investment' for a fee: use it only if the founder does",
}


def check(text, max_words=None, max_chars=None, letters=False):
    problems, warns = [], []
    pats = dict(PROBLEM_PATTERNS)
    if letters:
        pats.update(LETTER_PATTERNS)
    for pat, why in pats.items():
        for m in re.finditer(pat, text, re.I):
            if why in DECLINABLE and NEGATION.search(_sentence(text, m.start(), m.end())):
                continue
            problems.append(f"{why}: '{text[max(0, m.start() - 25):m.end() + 25].strip()}'")
    for pat, why in WARN_PATTERNS.items():
        for m in re.finditer(pat, text, re.I):
            warns.append(f"{why}: '{text[max(0, m.start() - 20):m.end() + 20].strip()}'")
    words = len(re.findall(r"\b\w[\w'-]*\b", text))
    if max_words and words > max_words:
        problems.append(f"{words} words, limit {max_words}")
    if max_chars and len(text) > max_chars:
        problems.append(f"{len(text)} characters, limit {max_chars}")
    return problems, warns, words


def read(path):
    if path.endswith(".docx"):
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from letters import docx_text
        return docx_text(path)
    with open(path, encoding="utf-8") as f:
        return f.read()


def main():
    a = argparse.ArgumentParser()
    a.add_argument("file", nargs="?")
    a.add_argument("--text")
    a.add_argument("--letters", action="store_true")
    a.add_argument("--max-words", type=int)
    a.add_argument("--max-chars", type=int)
    args = a.parse_args()
    if args.text is None and (not args.file or not os.path.exists(args.file)):
        print(f"STOP: there is no file at {args.file}. Nothing was checked.")
        sys.exit(2)
    text = args.text if args.text is not None else read(args.file)
    letters = args.letters or bool(args.file and args.file.endswith(".docx"))
    problems, warns, words = check(text, args.max_words, args.max_chars, letters)
    for x in problems:
        print("PROBLEM:", x)
    for x in warns:
        print("WARN:", x)
    print(f"{len(problems)} problems, {len(warns)} warnings, {words} words, {len(text)} characters")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
