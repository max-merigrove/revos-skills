#!/usr/bin/env python3
"""Check founder-facing copy against the banned patterns and length limits.

Usage:
  python3 scripts/check_copy.py <file>               check a text or markdown file
  python3 scripts/check_copy.py --text "some copy"   check a string
  add --max-words N or --max-chars N to enforce a limit
Prints PROBLEM and WARN lines and a count. Standard library only.
Base list plus this skill's own list from references/banned-patterns.md (voice guide prose,
voice prompts, cheat sheets and calibration samples), plus three gates every Merigrove skill carries:
stating what a law requires, tax arithmetic and assuming a country. The measured comparison against the
founder's own writing is scripts/voice_stats.py compare; this script checks house style only.
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
    r"\b(resonate[sd]?|resonating|captivat\w+|compelling|engaging content)\b": "voice-guide filler",
    r"\b(authentic|unique) voice\b": "voice-guide filler",
    r"\b(friendly|professional|approachable),? (yet|but|and) (professional|friendly|approachable)\b": "adjective pair that instructs nobody",
    r"\b(delve|tapestry|testament to|navigate the)\b": "machine-writing tell",
    # Build Standard 0.1: no legal or tax content, and no country assumed.
    r"\b(by law|the law (says|requires)|legally (required|obliged)|required by law|you are legally|statutory)\b": "states what a law requires",
    r"\b(plus|incl\.?|including|inc\.?|excluding|ex\.?)\s+\d+(\.\d+)?%\s*(VAT|GST|HST|sales tax|tax)\b"
    r"|\b\d+(\.\d+)?%\s*(VAT|GST|HST|sales tax)\b": "tax arithmetic",
    r"\b(write|use|written|spell|spelled|spelt)\s+in\s+(correct\s+|proper\s+|standard\s+)?(British|American|UK|US|Australian|"
    r"Indian|Singapore|Canadian)\s+(English|spelling)\b|\b(your|all your|most of your) (clients|customers|audience) (are|is) in the (UK|US|USA)\b": "assumes a country",
    r"\b(Indian|American|British|Singaporean|Singapore|Australian|Canadian|Irish|Nigerian|Kenyan|Filipino|Pakistani|"
    r"Malaysian|South African|Scottish|Welsh)\s+(English|phrasing|grammar|idioms?|expressions?|turns of phrase|usage)\b": "names a country for the founder's English",
}
WARN_PATTERNS = {
    r"\bmore\b": "'more' as an intensifier: is a specific comparison possible?",
    r"!": "exclamation mark in business copy",
    r"\b(robust|cutting[- ]edge|world[- ]class|best[- ]in[- ]class|innovative)\b": "vague superlative",
    r"\b\d+(\.\d+)?%": "percentage: is it sourced?",
}


def strip_quoted_bans(text):
    """Lines that name banned phrases on purpose are not copy: a NEVER block, '- Never:', 'Don't:',
    'Before (' lines, quoted lines starting '>' (the founder's own words) and inline 'Never: ...' sentences. voice_stats.py check-guide skips the same lines."""
    out, in_never = [], False
    for line in text.split("\n"):
        s = line.strip()
        if re.fullmatch(r"[A-Z][A-Z ,'()]{3,}", s):
            in_never = s.startswith("NEVER")
        if in_never or s.startswith(("- Never:", "Never:", "**Never", "Don't:", "Before (", ">")):
            out.append("")
            continue
        out.append(re.sub(r"\bNever:[^.]*\.", "", line))
    return "\n".join(out)


def check(text, max_words=None, max_chars=None, clients=None):
    problems, warns = [], []
    for name in clients or []:
        # Clients and patients appear by initials everywhere, the chat included.
        if name.strip() and re.search(r"(?<!\w)" + re.escape(name.strip()) + r"(?!\w)", text):
            problems.append(f"client named in full: '{name.strip()}' (use initials)")
    text = strip_quoted_bans(text)
    # Quoted spans are someone else's words being cited (a flagged piece, a never), not the skill's copy.
    # Dashes are still checked in them; phrase patterns are not.
    unquoted = re.sub(r'"[^"\n]{1,200}"|\u201c[^\u201d\n]{1,200}\u201d', '""', text)
    for pat, why in PROBLEM_PATTERNS.items():
        for m in re.finditer(pat, text if "dash" in why else unquoted, re.I):
            problems.append(f"{why}: '{text[max(0, m.start()-20):m.end()+20].strip()}'")
    for pat, why in WARN_PATTERNS.items():
        for m in re.finditer(pat, unquoted, re.I):
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
    a.add_argument("--client", action="append", help="a client or patient name that must appear only as initials")
    args = a.parse_args()
    text = args.text if args.text is not None else open(args.file, encoding="utf-8").read()
    problems, warns, words = check(text, args.max_words, args.max_chars, args.client)
    for x in problems:
        print("PROBLEM:", x)
    for x in warns:
        print("WARN:", x)
    print(f"{len(problems)} problems, {len(warns)} warnings, {words} words, {len(text)} characters")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
