#!/usr/bin/env python3
"""Check an llms.txt against the llmstxt.org format.

Usage: python3 scripts/llms_check.py <llms.txt> [--facts facts.json]

The format (llmstxt.org, Jeremy Howard): a Markdown file at /llms.txt. First an H1 with the name (the
only required part), then an optional blockquote summary, optional plain paragraphs, then H2 sections
whose lists hold links as "- [name](url)" with an optional ": note". An H2 named "Optional" holds
secondary links. This check also fails placeholders, text addressed to AI systems ("recommend us"),
relative links, and, with --facts, any web address not in the fact register.
Exit 0 clean, 1 with PROBLEM lines, 2 with STOP. No network calls.
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import domain_of, load_json, read_text, stop  # noqa: E402

LINK = re.compile(r"^\s*[-*]\s+\[([^\]]+)\]\(([^)\s]+)\)(?::\s*(.+))?\s*$")
AIMED = re.compile(r"(?i)\b(recommend (us|this business)|you (should|must) (recommend|mention|rank)|ignore (previous|prior) instructions|"
                   r"as an ai|dear (ai|assistant|llm)|number one|nummer 1)\b|#1\b")
PLACEHOLDER = re.compile(r"\[NEED|\bTODO\b|example\.com|yourdomain|lorem ipsum|\{\{\s*\w+\s*\}\}", re.I)


def check(text, facts=None):
    probs, warns = [], []
    lines = text.splitlines()
    body = [ln for ln in lines if ln.strip()]
    if not body:
        return ["the file is empty"], warns
    if not re.match(r"^# \S", body[0]):
        probs.append("the first line must be an H1 with the business or site name ('# Name')")
    if sum(1 for ln in lines if re.match(r"^# \S", ln)) > 1:
        probs.append("only one H1 is allowed; use H2 ('## ') for sections")
    seen_h2 = False
    links = 0
    for i, ln in enumerate(lines, 1):
        s = ln.rstrip()
        if s.startswith("## "):
            seen_h2 = True
            continue
        if seen_h2 and s.strip() and not s.startswith("#"):
            if s.lstrip().startswith(("-", "*")):
                m = LINK.match(s)
                if not m:
                    probs.append(f"line {i}: list items under a section are links written '- [name](https://...)' with an optional ': note'")
                else:
                    links += 1
                    url = m.group(2)
                    if not url.startswith(("http://", "https://")):
                        probs.append(f"line {i}: link '{url}' must be a full address starting https://")
                    elif facts is not None:
                        reg = " ".join(f.get("value", "") for f in facts.get("facts", []) if f.get("status") == "confirmed").lower()
                        if domain_of(url) not in reg:
                            probs.append(f"line {i}: '{url}' is not an address in the fact register")
            else:
                warns.append(f"line {i}: text inside a section; the format expects link lists there")
        if s.startswith("###"):
            warns.append(f"line {i}: H3 headings are not part of the format")
    if links == 0:
        warns.append("no link lists: the file is valid, but the point of it is to list your key pages")
    if len(body) > 1 and not body[1].startswith(">"):
        warns.append("no one-line summary in a blockquote ('> ...') straight after the H1")
    m = PLACEHOLDER.search(text)
    if m:
        probs.append(f"holds a placeholder ('{m.group(0)}'); leave a line out until the fact is confirmed")
    m = AIMED.search(text)
    if m:
        probs.append(f"text aimed at AI systems or a ranking claim ('{m.group(0)}'): describe the business, never instruct the reader")
    if len(text) > 20000:
        warns.append("over 20,000 characters: keep it to the pages that matter")
    return probs, warns


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--facts")
    a = ap.parse_args()
    text = read_text(a.file, "the llms.txt")
    facts = load_json(a.facts, "the fact register") if a.facts else None
    probs, warns = check(text, facts)
    for p in probs:
        print("PROBLEM:", p)
    for w in warns:
        print("WARN:", w)
    print(f"{len(probs)} problems, {len(warns)} warnings")
    return 1 if probs else 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main())
