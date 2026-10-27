#!/usr/bin/env python3
"""Check founder-facing copy (the note, the chat summary, any text you write) against the banned patterns.

Usage:
  python3 scripts/check_copy.py <file>               check a text or markdown file
  python3 scripts/check_copy.py --text "some copy"   check a string
  add --max-words N to enforce a limit
Prints PROBLEM and WARN lines and a count; exit 1 on any PROBLEM, 2 when there is nothing to check.
Carries the Merigrove base list and this skill's sales list from references/banned-patterns.md, plus a check
that every conversion rate quoted carries its tag (measured, your estimate, planning default).
Standard library only.
"""
import argparse
import os
import re
import sys

PROBLEM_PATTERNS = {
    "[\u2014\u2013]": "em or en dash",
    r"\bin today'?s (fast-paced|digital|ever-changing|competitive)": "stock opener",
    r"\bit'?s not (just )?[^.]{1,40}, it'?s\b": "contrast reveal",
    r"\b(game[- ]changer|delve|unlock(s|ing)?|elevate(s|d)?|seamless(ly)?|leverag(e|es|ing)|robust)\b": "filler word",
    r"\b(I mean|to be honest|if I'?m being honest|let'?s be real)\b": "announced honesty",
    # this skill's sales list
    r"\bjust (increase|up|ramp up|boost) (your )?(outreach|activity|volume|prospecting)\b": "activity advice with no figure",
    r"\b(increase|ramp up|boost) your outreach\b": "activity advice with no figure",
    r"\bdouble (your )?(leads|outreach|calls|activity)\b": "volume advice with no figure",
    r"\bstay consistent\b": "platitude",
    r"\b(it'?s )?a numbers game\b": "platitude",
    r"\b(hustle|grind) (harder|more)\b": "platitude",
    r"\b(guarantee[sd]?|you will (hit|close|make|reach)|you'll (hit|close|make|reach)|will definitely)\b": "promise of a result",
    r"\b\d+(\.\d+)?\s?(%|per cent) of (businesses|founders|agencies|consultants|coaches|sales calls|prospects|leads)\b": "unsourced statistic about the world",
    r"\b(industry (standard|average|benchmark)|the average (founder|business|agency) (closes|converts|books))\b": "benchmark with no source",
    r"\bmost (founders|businesses|agencies|consultants|coaches) (close|convert|book|get|see)\b": "benchmark with no source",
    r"\[STAT\]|\[VERIFY\]": "internal placeholder left in founder copy; use [NEED: ...]",
    r"\b(read|lus?|taken|treated|planned|counted)\s+(as|comme)\s+[^.\n]{0,25}\b(HT|TTC|hors TVA|TVA comprise|ex(cl)?\.? (VAT|GST)|before (VAT|GST|sales tax)|zzgl\. MwSt|sin IVA)\b|\bas (HT|TTC) means\b": "sales-tax commentary in the chat: the plan's one neutral line covers it",
    r"\b(Founder|User|Speaker|Message|Turn) \d+\b(?! (sales|calls|clients|leads|bookings|hours|months|weeks|days))": "internal label from a file; call it what it is to the founder ('your note', 'your second message')",
    r"\b(consider (increasing|raising|boosting)|you might want to|you may want to|it depends)\b": "advice with no figure",
    r"\bfalse urgency\b|\bonly \d+ (spots|places) left\b": "fake urgency",
    # Build Standard 0.1: no tax or legal statements, no assumed country
    r"\b(the law (says|requires|states)|legally (required|obliged|bound)|required by law|by law,? you|the rules? (say|says|require)s?)\b": "states what a law requires",
    r"\byou (must|have to|need to|are required to) (register|charge|collect|file|pay)\b[^.]{0,30}\b(vat|gst|sales tax|tax|returns?)\b": "states what a law requires",
    r"\b(you'?ll|you will|you would|you'?d) (pay|owe|keep|take home)\b[^.]{0,40}\b(tax|vat|gst|after tax)\b": "works out tax",
    r"\b(gross(ed|ing)? (it )?up|grossed[- ]up|before[- ]tax equivalent)\b": "works out tax",
    r"\b\d+(\.\d+)?\s?(%|per ?cent) (of )?(vat|gst|sales tax|income tax|corporation tax|tax|national insurance|social (security|charges))\b": "works out tax",
    r"\b(vat|gst|sales tax|tax|income tax) (at|of|rate of) \d": "works out tax",
    r"\b(vat|gst|sales tax) (registration )?threshold\b": "tax threshold: outside this skill",
    r"\b(tax office|tax authority|revenue (service|authority)|government (says|requires|website)|bank holidays?|in the UK|UK (founders?|businesses))\b": "assumes a country or its institutions",
}
WARN_PATTERNS = {
    r"\bmore\b": "'more' as an intensifier: is a specific figure possible?",
    r"!": "exclamation mark in business copy",
    r"\b(cutting[- ]edge|world[- ]class|best[- ]in[- ]class|innovative)\b": "vague superlative",
    r"\b(pipeline velocity|funnel optimisation|conversion optimisation|CAC|LTV|SQL|MQL)\b": "jargon in founder copy",
}
RATE_WORDS = r"(show|close|closing|booking|conversion|offer)"
TAGS = r"(measured|your estimate|estimate|planning default|default|assumed|not known|directional|you gave|your count|counted)"


def untagged_rates(text):
    """A sentence that quotes a conversion rate as a percentage must say what it rests on."""
    out = []
    for sent in re.split(r"(?<=[.;\n])\s+", text):
        if re.search(rf"\b{RATE_WORDS}\b[^.]{{0,40}}\d+(\.\d+)?\s?(%|per cent)|\d+(\.\d+)?\s?(%|per cent)[^.]{{0,25}}\b{RATE_WORDS}\b",
                     sent, re.I) and not re.search(TAGS, sent, re.I):
            out.append(sent.strip()[:120])
    return out


SALES_TAX_WORDS = r"\b(VAT|GST|HST|sales tax|TVA|TTC|MwSt|USt|IVA|BTW|IGV)\b|\bHT\b"


def chat_tax(text):
    """In the chat, sales tax is never commented on: the plan's one neutral line covers it. A question asking for
    the price before sales tax (a sentence ending in '?') is the one allowed mention."""
    out = []
    for sent in re.split(r"(?<=[.!?\n])\s+", text):
        if re.search(SALES_TAX_WORDS, sent) and not sent.strip().endswith("?"):
            out.append(sent.strip()[:120])
    return out


def check(text, max_words=None, chat=False):
    problems, warns = [], []
    if chat:
        for x in chat_tax(text):
            problems.append(f"sales tax mentioned in the chat (the file's one line covers it; only a question for "
                            f"the before-tax price may name it): '{x}'")
    for pat, why in PROBLEM_PATTERNS.items():
        for m in re.finditer(pat, text, re.I):
            problems.append(f"{why}: '{text[max(0, m.start() - 20):m.end() + 20].strip()}'")
    for s in untagged_rates(text):
        problems.append(f"rate with no tag (say measured, your estimate or planning default): '{s}'")
    for pat, why in WARN_PATTERNS.items():
        for m in re.finditer(pat, text, re.I if "CAC" not in pat else 0):
            warns.append(f"{why}: '{text[max(0, m.start() - 20):m.end() + 20].strip()}'")
    words = len(re.findall(r"\b\w[\w'-]*\b", text))
    if max_words and words > max_words:
        problems.append(f"{words} words, limit {max_words}")
    return problems, warns, words


def main():
    a = argparse.ArgumentParser()
    a.add_argument("file", nargs="?")
    a.add_argument("--text")
    a.add_argument("--max-words", type=int)
    a.add_argument("--chat", action="store_true", help="the text is the chat reply: no sales-tax mentions")
    args = a.parse_args()
    if args.text is None and (not args.file or not os.path.exists(args.file)):
        print(f"STOP: there is no file at {args.file}. Nothing was checked.")
        sys.exit(2)
    text = args.text if args.text is not None else open(args.file, encoding="utf-8").read()
    problems, warns, words = check(text, args.max_words, args.chat)
    for x in problems:
        print("PROBLEM:", x)
    for x in warns:
        print("WARN:", x)
    print(f"{len(problems)} problems, {len(warns)} warnings, {words} words")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
