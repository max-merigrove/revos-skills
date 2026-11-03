#!/usr/bin/env python3
"""Check founder-facing copy (pages, the kit text, the chat summary) against the banned patterns.

Usage:
  python3 scripts/check_copy.py <file> [<file> ...]       text, markdown or an HTML fragment
  python3 scripts/check_copy.py --text "some copy"
  add --max-words N, --chat (the chat summary: at most 12 lines), --allow-quotes (kit and chat: quoted words are
  the founder's or a buyer's, so they are not scored)
A percentage needs its sample size beside it only in a sentence about being named, cited, recommended or seen
in answers; a founder's own figures are checked against the fact register by claims_check.py instead.
Prints PROBLEM and WARN lines and a count. Exit 1 on any PROBLEM, 2 with STOP. Standard library only.
The patterns are listed with reasons in references/banned-patterns.md.
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import read_text, stop, strip_html  # noqa: E402

PROBLEM_PATTERNS = {
    r"[\u2014\u2013]": "em or en dash",
    r"\bin today'?s (fast-paced|digital|ever-changing)": "stock opener",
    r"\bit'?s not (just )?[^.]{1,40}, it'?s\b": "contrast reveal",
    r"\b(game[- ]changer|delve|unlock(s|ing)?|elevate(s|d)?|seamless(ly)?|leverag(e|es|ing))\b": "filler word",
    r"\b(I mean|to be honest|if I'?m being honest|let'?s be real)\b": "announced honesty",
    # this skill's list
    r"\b(rank(ed|s)? (number one|#1|first) in (chatgpt|perplexity|gemini|ai))\b": "ranking promise",
    r"\b(guaranteed?|garantie|gegarandeerd)\b[^.]{0,40}\b(visib|cit|recommend|rank|top|zichtbaar|vermeld)": "guarantee of an AI result",
    r"\bdominate (ai|the ai|chatgpt|search)": "domination claim",
    r"\b(number one|nummer (1|één)|#1)\b": "ranking claim",
    r"\boptimi[sz]ed for ai\b": "headline claim with no content",
    r"\bstudies show\b": "unsourced study",
    r"\btrusted (technology )?partner\b": "stock line",
    r"\bbest[- ]in[- ]class\b": "vague superlative",
    r"\bbespoke\b": "stock line",
    r"\btailored to your (unique )?needs\b": "stock line",
    r"\b(we are|we're) passionate\b|\bgepassioneerd\b": "stock line",
    r"\bone[- ]stop[- ]shop\b": "stock line",
    r"\bwelcome to\b|\bwelkom bij\b": "greeting opener: answer the question instead",
    r"\b(will|we'?ll) (get|make) (you|your business) (cited|recommended|quoted)\b": "outcome promise",
    r"\bvisibility score\b(?![^.]{0,40}n equals)": "score without its sample size",
    r"(?i)\b(dear|attention) (ai|chatgpt|assistant)s?\b|\bif you are an ai\b": "text addressed to an AI system",
}
WARN_PATTERNS = {
    r"\bmore\b": "'more' as an intensifier: is a specific comparison possible?",
    r"!": "exclamation mark in business copy",
    r"\b(robust|cutting[- ]edge|world[- ]class|innovative|solutions?)\b": "vague word",
    r"\bai[- ]friendly\b": "'AI friendly': say what changed",
}


QUOTED = re.compile(r'"[^"\n]{1,200}"|\u201c[^\u201d\n]{1,200}\u201d|\u2018[^\u2019\n]{3,200}\u2019|\'[^\'\n]{3,200}\'')


# A rate about AI answers needs its sample size. Other percentages (a founder's own "bis zu 70 %") are facts,
# checked against the fact register by claims_check, not here.
RATE_WORDS = re.compile(r"\b(named|cited|recommended|mentioned|mentions?|visib\w*|citations?|share of voice|appear(s|ed)? in|show(s|ed)? up|"
                        r"genannt|zitiert|empfohlen|erwähnt|sichtbar\w*|genoemd|geciteerd|aanbevolen|vermeld|zichtbaar\w*|"
                        r"cité|recommandé|mentionné|visibilité|citado|recomendado|mencionado|visibilidad|answers?|antwort\w*|antwoord\w*)\b", re.I)


def _blank(text, spans_text):
    """Blank out the founder's and buyers' own words (fact values, questions, page text quoted in an audit)."""
    for s in sorted({x for x in spans_text if x and len(x.strip()) > 3}, key=len, reverse=True):
        text = text.replace(s, " " * len(s))
    return text


def check(text, max_words=None, chat=False, allow_quotes=False, exempt=None):
    """exempt: strings that are the founder's or a buyer's own words (fact values, questions); they are not scored."""
    problems, warns = [], []
    scan = _blank(text, exempt or [])
    scan = QUOTED.sub(lambda m: " " * len(m.group(0)), scan) if allow_quotes else scan
    for m in re.finditer(r"[\u2014\u2013]", text):
        problems.append(f"em or en dash: '{text[max(0, m.start() - 25):m.end() + 25].strip()}'")
    for pat, why in PROBLEM_PATTERNS.items():
        if why == "em or en dash":
            continue
        for m in re.finditer(pat, scan, re.I):
            problems.append(f"{why}: '{text[max(0, m.start() - 25):m.end() + 25].strip()}'")
    for pat, why in WARN_PATTERNS.items():
        for m in re.finditer(pat, scan, re.I):
            warns.append(f"{why}: '{text[max(0, m.start() - 20):m.end() + 20].strip()}'")
    for m in re.finditer(r"\b\d{1,3}([.,]\d)?\s?(%|per ?cent|procent|prozent)", scan, re.I):
        a = max(scan.rfind(".", 0, m.start()), scan.rfind("\n", 0, m.start())) + 1
        b = min([x for x in (scan.find(".", m.end()), scan.find("\n", m.end())) if x != -1] or [len(scan)])
        sentence = scan[a:b]
        if not RATE_WORDS.search(sentence):
            continue
        window = text[max(0, m.start() - 120):m.end() + 120]
        if not re.search(r"n equals|n gleich|n is|n =|of \d+ runs|\d+ (of|von|van|de|sur) \d+|range|bereik|spanne|bereich|plage|rango", window, re.I):
            problems.append(f"a percentage with no sample size beside it: '{text[max(0, m.start() - 30):m.end() + 10].strip()}'")
    if chat:
        lines = [ln for ln in text.splitlines() if ln.strip()]
        if len(lines) > 12:
            problems.append(f"chat summary is {len(lines)} lines; keep it to five short lines plus the bridge")
    words = len([t for t in text.split() if re.search(r"\w", t)])
    if max_words and words > max_words:
        problems.append(f"{words} words, limit {max_words}")
    return problems, warns, words


def main():
    a = argparse.ArgumentParser()
    a.add_argument("files", nargs="*")
    a.add_argument("--text")
    a.add_argument("--max-words", type=int)
    a.add_argument("--chat", action="store_true")
    a.add_argument("--allow-quotes", action="store_true",
                   help="kit and chat only: text inside quotation marks is the founder's or a buyer's own words")
    args = a.parse_args()
    if args.text is None and not args.files:
        stop("give a file to check or --text \"...\"")
    items = [("text", args.text)] if args.text is not None else []
    for f in args.files:
        t = read_text(f, "the copy")
        items.append((os.path.basename(f), strip_html(t) if f.endswith((".html", ".htm")) else t))
    total_p = 0
    for name, text in items:
        problems, warns, words = check(text, args.max_words, args.chat, args.allow_quotes)
        for x in problems:
            print(f"PROBLEM: {name}: {x}")
        for x in warns:
            print(f"WARN: {name}: {x}")
        total_p += len(problems)
        print(f"{name}: {len(problems)} problems, {len(warns)} warnings, {words} words")
    print(f"{total_p} problems")
    sys.exit(1 if total_p else 0)


if __name__ == "__main__":
    main()
