#!/usr/bin/env python3
"""Check founder-facing copy against the banned patterns and length limits.

Usage:
  python3 scripts/check_copy.py <file>               check a text, markdown or .docx file
  python3 scripts/check_copy.py --text "some copy"   check a string
  add --max-words N or --max-chars N to enforce a limit
Prints PROBLEM and WARN lines and a count; exit 1 on any PROBLEM, 2 if the file is missing.
PROBLEM_PATTERNS carry the Merigrove base list plus this skill's capacity list from
references/banned-patterns.md. Standard library only. No network calls.
"""
import argparse
import os
import re
import sys
import zipfile

PROBLEM_PATTERNS = {
    "[\u2014\u2013]": "em or en dash",
    r"\bin today'?s (fast-paced|digital|ever-changing|busy)": "stock opener",
    r"\bit'?s not (just )?[^.]{1,40}, it'?s\b": "contrast reveal",
    r"\b(game[- ]changer|delve|unlock(s|ing)?|elevate(s|d)?|seamless(ly)?|leverag(e|es|ing))\b": "filler word",
    r"\b(I mean|to be honest|if I'?m being honest|let'?s be real|honestly)\b": "announced honesty",
    # capacity list (references/banned-patterns.md, this skill's list)
    r"\bdelegate (everything|it all|all of it)\b": "delegate everything",
    r"\b(outsource|hand off) (everything|it all)\b": "delegate everything",
    r"\b(just|simply)? ?(hire|get) an? (VA|virtual assistant|assistant)\b": "hire a VA as a default",
    r"\bwork smarter\b": "platitude",
    r"\b(work[- ]life balance|hustle|grind|burn ?out)\b": "platitude",
    r"\b(just|simply) (delegate|hire|outsource|say no)\b": "advice with no figure",
    r"\b(you might want to|you may want to|consider (hiring|delegating|outsourcing)|it depends)\b": "advice with no figure",
    r"\b(industry standard|industry average|best practice says|the ideal utili[sz]ation|healthy utili[sz]ation)\b": "benchmark with no source",
    r"\bmost (founders|agencies|consultants|coaches|freelancers|businesses|owners|people) (can|hold|handle|manage|work|have|run)\b": "benchmark with no source",
    r"\b\d+(\.\d+)?\s?(%|per cent) of (businesses|founders|agencies|consultants|freelancers|companies|owners|people)\b": "unsourced statistic about the world",
    r"\[STAT\]|\[VERIFY\]": "internal placeholder left in founder copy; use [NEED: ...]",
    r"\b(guarantee[sd]?|you will (make|earn|double|free up)|double your|triple your|10x)\b": "promise of a result",
    r"\b(Merigrove practice|Merigrove standard|our methodology says)\b": "internal authority in founder copy",
    r"\bRevOS\b": "internal name in founder copy",
    r"\bfreedom\b": "vague promise",
    r"\bceiling (is|of) \d+\b(?![^\n]{0,140}?\b(hours?|divided)\b)": "a ceiling quoted without its working nearby",
    # scope boundaries: no statement of what a law requires, no tax or payroll arithmetic, no assumed country
    r"\b(the law (says|requires)|required by law|by law,? you|legally (required|obliged|entitled)|you are (legally )?entitled to|"
    r"statutory (holiday|leave|minimum|entitlement|sick)|minimum wage)\b": "states what a law requires; send it to their lawyer or accountant",
    r"\b(employer'?s? (national\s+insurance|NI|payroll tax(es)?|contributions?|social (security|charges))|on-?costs? of \d|"
    r"\d+(\.\d+)?\s?(%|per cent) (tax|VAT|GST|sales tax|payroll tax|super(annuation)?|CPF|pension)|"
    r"(after|before|less|plus) (income )?tax (of|at) \d|(VAT|GST|sales tax) (registration )?threshold)\b": "tax, payroll or on-cost arithmetic; the founder's accountant or payroll provider supplies it",
    r"\b(HM\s?RC|I\.?R\.?S|ATO|IRAS|CRA|gov\.uk|bank holidays?|National\s+Insurance|PAY\s?E)\b": "country-specific rule or institution; follow the founder's own place and words",
    # a ratio worked out in words is still arithmetic done by eye
    r"\b(nearly |almost |about |roughly )?(double[sd]?|triple[sd]?|twice (as|the|that|what)|half (as|the|of|what)|"
    r"(two|three|four|five|six|seven|eight|nine|ten|\d+(\.\d+)?) times (as|the|more|less|over|what|that|your)|"
    r"(two|three|four|five|six|seven|eight|nine|ten|\d+)-fold)\b": "comparison worked out in prose; give the two figures the script printed",
}
WARN_PATTERNS = {
    r"\bmore\b": "'more' as an intensifier: is a specific comparison possible?",
    r"!": "exclamation mark in business copy",
    r"\b(robust|cutting[- ]edge|world[- ]class|best[- ]in[- ]class|innovative)\b": "vague superlative",
    r"\b(bandwidth|scalable|synergy|optimi[sz]e)\b": "jargon: say it plainly",
    r"\b(theory of constraints|e-myth|goldratt|gerber)\b": "framework name: is the plain idea stated with a figure?",
    r"\b(?<!not )(tax|VAT|GST|salary|wage)\b|\bpayroll\b(?! provider)": "money rule word: fine as the founder's own step name; never a figure or a rule the skill worked out",
}


def docx_text(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8")
        for n in z.namelist():
            if n.startswith("word/footer"):
                xml += z.read(n).decode("utf-8")
    xml = re.sub(r"</w:p>", "\n", xml)
    xml = re.sub(r"</w:tc>", " | ", xml)
    text = re.sub(r"<[^>]+>", "", xml)
    return text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')


def check(text, max_words=None, max_chars=None):
    problems, warns = [], []
    for pat, why in PROBLEM_PATTERNS.items():
        for m in re.finditer(pat, text, re.I):
            problems.append(f"{why}: '{text[max(0, m.start() - 20):m.end() + 20].strip()}'")
    for pat, why in WARN_PATTERNS.items():
        for m in re.finditer(pat, text, re.I):
            warns.append(f"{why}: '{text[max(0, m.start() - 20):m.end() + 20].strip()}'")
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
    if args.text is not None:
        text = args.text
    elif args.file.lower().endswith(".docx"):
        try:
            text = docx_text(args.file)
        except (zipfile.BadZipFile, KeyError):
            print(f"STOP: {args.file} is not a readable .docx. Nothing was checked.")
            sys.exit(2)
    else:
        text = open(args.file, encoding="utf-8", errors="replace").read()
    problems, warns, words = check(text, args.max_words, args.max_chars)
    for x in problems:
        print("PROBLEM:", x)
    for x in warns:
        print("WARN:", x)
    print(f"{len(problems)} problems, {len(warns)} warnings, {words} words, {len(text)} characters")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
