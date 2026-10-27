#!/usr/bin/env python3
"""Check copy written for the founder against the banned patterns in references/banned-patterns.md.

Usage:
  python3 scripts/check_copy.py <file>                 check a text, markdown or html file
  python3 scripts/check_copy.py --text "some copy"     check a string
  python3 scripts/check_copy.py --extraction <extraction.json>
        check only what Claude wrote in the extraction (core lines, rationales, proposed edits,
        reasons, the decision); the founder's own quotes are theirs and are never checked
Prints PROBLEM and WARN lines and a count. Exit 0 clean, 1 problems, 2 STOP. Standard library only.
build_report.py adds two checks that need the founder's assets: spelling in the founder's English, and
no country or currency the assets never mention.
"""
import argparse
import json
import re
import sys
from pathlib import Path

# "GDPR compliant", "FDA approved", "fully compliant": a claim about the law. A credential ("ICF certified",
# "FSC certified", "ISO 9001 certified") is not; it is checked as a fact instead (no credential the assets do
# not name). A compliance phrase the founder's own assets already use is theirs to keep (build_report passes them).
COMPLIANCE = r"\b(?:[A-Z][A-Z0-9-]{1,9}(?: \d{1,5})?[- ]?(?:compliant|approved)|(?:[Ff]ully|[Ll]egally) compliant)\b"
PROBLEM_PATTERNS = {
    r"[\u2014\u2013]": "em or en dash",
    r"\bin today'?s (fast-paced|digital|ever-changing|competitive)": "stock opener",
    r"\bit'?s not (just )?[^.]{1,40}, it'?s\b": "contrast reveal",
    r"\b(game[- ]changer|delve|unlock(s|ing|ed)?|elevate(s|d)?|seamless(ly)?|leverag(e|es|ing|ed))\b": "filler word",
    r"\b(I mean|to be honest|if I'?m being honest|let'?s be real|honestly)\b": "announced honesty",
    # this skill's list
    r"\b(your )?messaging could be (stronger|clearer|sharper)": "vague verdict with no quote",
    r"\bconsider (clarifying|refining|tightening|strengthening|making|adding|reviewing|updating)\b": "advice with no line",
    r"\bmake (it|this|them|the copy) (clearer|stronger|sharper|punchier|more \w+)": "edit that is not a line",
    r"\bstrengthen (your|the) (messaging|brand|positioning|story)\b": "vague verdict with no quote",
    r"\bcohesive\b": "'cohesive' with nothing behind it",
    r"\bresonat(e|es|ing) with\b": "unprovable claim about the reader",
    r"\boverall,? (your )?(messaging|brand|copy|story) (is|feels|looks) (consistent|strong|solid|good|clear)": "upbeat summary in place of a finding",
    r"\b(you might want to|it might be worth|you could consider|it may be worth)\b": "soft advice",
    r"\b(on-brand|brand alignment|brand equity|brand architecture|value proposition|USP)\b": "jargon in founder copy",
    r"\b(guarantee[sd]?|will (double|triple|transform)|10x)\b": "promise of a result",
    r"\bjourney\b": "stock word",
    # scope: no legal or tax advice, no country assumed (Build Standard 0.1)
    r"\b(legally required|required by law|by law,? you|the law (requires|says|states)|you are (legally )?(required|obliged) to|"
    r"it is (illegal|unlawful|against the law)|you must (register|charge|collect|file|declare))\b": "states what a law requires",
    r"\b\d+(\.\d+)?\s?%\s?(VAT|GST|HST|PST|sales tax|tax)\b|\b(VAT|GST|HST|sales tax|tax) (at|of) \d": "states or computes a tax rate",
    COMPLIANCE: "claims legal compliance",
}
WARN_PATTERNS = {
    r"\bmore\b": "'more' as an intensifier: is a specific comparison possible?",
    r"!": "exclamation mark in business copy",
    r"\b(robust|cutting[- ]edge|world[- ]class|best[- ]in[- ]class|innovative|holistic|synergy)\b": "vague superlative",
    r"\b(compelling|powerful|impactful)\b": "adjective doing the work a quote should do",
    r"\b\d+(\.\d+)?%": "percentage: is it in the founder's own assets?",
}
# Phrases any competitor could write. A core line that uses one fails the "could a competitor write it" test.
COMPETITOR_PHRASES = [
    r"\bhelp(s|ing)? (businesses|brands|companies|clients|organisations|organizations|you|people|founders|teams) (to )?(grow|succeed|scale|thrive|reach|achieve)",
    r"\btailored\b", r"\bbespoke solutions?\b", r"\btrusted (partner|advisor|adviser)\b", r"\bresults[- ]driven\b",
    r"\bpassionate\b", r"\bone[- ]stop[- ]shop\b", r"\bend[- ]to[- ]end solutions?\b", r"\bnext level\b",
    r"\bgrowth partner\b", r"\bdata[- ]driven\b", r"\bhigh[- ]quality\b", r"\binnovative\b", r"\bsolutions?\b",
    r"\breach (your|their) (full )?potential\b", r"\bmake a difference\b", r"\bexceptional (service|results)\b",
    r"\bcustomer[- ]centric\b", r"\bbest[- ]in[- ]class\b", r"\bworld[- ]class\b",
]


def stock_phrases(text):
    return [m.group(0) for p in COMPETITOR_PHRASES for m in re.finditer(p, text, re.I)]


def check(text, sources=None):
    """PROBLEM and WARN lines for one piece of Claude's copy. sources: the founder's asset texts, when known;
    a compliance phrase found word for word in them is the founder's own claim and is not refused."""
    problems, warns = [], []
    src = " ".join(sources or []).lower()
    for pat, why in PROBLEM_PATTERNS.items():
        flags = 0 if (pat == COMPLIANCE or "\\u2014" in pat) else re.I
        for m in re.finditer(pat, text, flags):
            if pat == COMPLIANCE and src and m.group(0).lower() in src:
                continue
            problems.append(f"{why}: '{text[max(0, m.start() - 25):m.end() + 25].strip()}'")
    for pat, why in WARN_PATTERNS.items():
        for m in re.finditer(pat, text, re.I):
            warns.append(f"{why}: '{text[max(0, m.start() - 25):m.end() + 25].strip()}'")
    return problems, warns


def written_fields(ext):
    """Everything Claude wrote in the extraction, labelled, never the founder's quotes."""
    out = []
    for i, cl in enumerate(ext.get("core_lines") or [], 1):
        out.append((f"core line {i}", cl.get("line", "")))
        out.append((f"core line {i} 'if you choose'", cl.get("if_you_choose", "")))
        out.append((f"core line {i} rationale", cl.get("rationale", "")))
        for t, g in (cl.get("gate") or {}).items():
            if isinstance(g, dict):
                out.append((f"core line {i} gate {t}", g.get("why", "")))
    for i, e in enumerate(ext.get("edits") or [], 1):
        out.append((f"edit {i} proposed", e.get("proposed", "")))
        out.append((f"edit {i} why", e.get("why", "")))
    for q, items in (ext.get("compatible") or {}).items():
        for it in items or []:
            if isinstance(it, (list, tuple)) and len(it) > 2:
                out.append((f"compatible reason ({q})", str(it[2])))
    ch = ext.get("chosen") if isinstance(ext.get("chosen"), dict) else {}
    if ch.get("by") == "founder":  # the founder's own line is theirs; only Claude's reason for it is checked
        out.append(("chosen line reason", ch.get("why", "")))
    for i, x in enumerate(ext.get("also") or [], 1):
        if isinstance(x, dict):
            out.append((f"also worth fixing {i}", x.get("what", "")))
            out.append((f"also worth fixing {i} note", x.get("note", "")))
    out.append(("decision", ext.get("decide", "")))
    return [(k, v) for k, v in out if v]


def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("file", nargs="?")
    a.add_argument("--text")
    a.add_argument("--extraction")
    args = a.parse_args()
    problems, warns, n = [], [], 0
    if args.extraction:
        p = Path(args.extraction)
        if not p.exists():
            print(f"STOP: {p} does not exist.")
            sys.exit(2)
        try:
            ext = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"STOP: {p} is not valid JSON ({e.msg}, line {e.lineno}).")
            sys.exit(2)
        sources = []
        for x in ext.get("assets") or []:
            f = Path(x.get("file") or "")
            f = f if f.is_absolute() else p.resolve().parent / f
            if f.exists() and x.get("kind") != "agreed":
                sources.append(f.read_text(encoding="utf-8", errors="replace"))
        for label, text in written_fields(ext):
            pr, wr = check(text, sources)
            problems += [f"{label}: {x}" for x in pr]
            warns += [f"{label}: {x}" for x in wr]
            n += len(text)
    else:
        if args.text is not None:
            text = args.text
        elif args.file:
            p = Path(args.file)
            if not p.exists():
                print(f"STOP: {p} does not exist.")
                sys.exit(2)
            text = p.read_text(encoding="utf-8")
            if p.suffix.lower() in {".html", ".htm"}:
                text = re.sub(r"<style.*?</style>|<[^>]+>", " ", text, flags=re.S)
        else:
            print(__doc__)
            sys.exit(2)
        problems, warns = check(text)
        n = len(text)
    for x in problems:
        print("PROBLEM:", x)
    for x in warns:
        print("WARN:", x)
    print(f"{len(problems)} problems, {len(warns)} warnings, {n} characters checked")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
