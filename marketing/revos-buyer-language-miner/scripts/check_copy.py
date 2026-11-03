#!/usr/bin/env python3
"""The writing check for everything this skill writes for the founder (angles, post ideas, lead magnet topics,
the start page). It reports; it never rewrites. Text inside quotation marks is the buyers' own words and is
skipped by check_bank.py before it calls this, so a buyer who wrote "honestly" is never flagged.

Usage:
  python3 scripts/check_copy.py <file>                 check a text or markdown file
  python3 scripts/check_copy.py --text "some copy"     check a string
  options: --lang en|de|hi|...   (English pattern checks run only for en; structural checks run for all)
           --allow-emoji  --allow-exclamations  (only when the founder's own writing shows them)
           --source <source.txt>  (a phrase pattern the founder said word for word is kept, as a WARN)
           --never "word"  (repeatable: words the founder never uses)
Prints PROBLEM and WARN lines and a count; exit 1 if any PROBLEM, 2 on bad input.
Pattern families follow references/banned-patterns.md (stock openers and hooks, contrast reveals, filler and
borrowed authority, claims about the market, legal and result promises), strongest first.
Standard library only. No network.
"""
import argparse
import os
import re
import signal
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

EMOJI = re.compile("[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F2FF\U00002B00-\U00002BFF️]")
DASHES = re.compile(r"[\u2012\u2013\u2014\u2015\u2e3a\u2e3b]|(?<=\w) - (?=\w)|(?<=\w) -- (?=\w)|(?<=\w)--(?=\w)")

# English pattern checks: (pattern, label, problem?)
EN_PATTERNS = [
    # A. staging: stock openers and hooks every feed has seen
    (r"^\s*(in today'?s (fast-paced|digital|ever-changing|modern|busy)|in a world where|let'?s dive in|here'?s the thing|picture this|imagine a world"
     r"|ever wondered|have you ever (wondered|noticed)|we'?ve all been there|let me tell you|buckle up|the truth is|the truth about"
     r"|most (founders|people|business owners|owners|entrepreneurs) (think|believe|assume|get this wrong)|nobody talks about|no one talks about"
     r"|what nobody tells you|what no one tells you|here'?s what i learned|unpopular opinion|hot take|i'?m (so )?(excited|thrilled|humbled|proud) to (share|announce)"
     r"|key takeaways|in my latest (conversation|podcast|episode)|stop doing this|you'?re doing \w+ wrong|this changed everything|(it|this) is a sign)",
     "stock opener", True),
    (r"^\s*\d+\s+(lessons|things|ways|tips|mistakes|reasons|truths|rules|steps|secrets|signs)\b", "numbered listicle hook", True),
    (r"\b(i almost didn'?t post this|i'?ve never told anyone|this is hard to (write|share)|i was today years old|confession:|vulnerable moment|i'?ll be honest)\b",
     "manufactured vulnerability", True),
    (r"\b(let that sink in|read that again|agree\?|thoughts\?|what do you think\?|comment below|drop an? \w+ (below|in the comments)|tag (someone|a friend)"
     r"|repost if|like if|who else\b|follow for more|save this( post)?|share if|can i get an amen|smash that)",
     "engagement bait", True),
    (r"\b(as i told|in my latest conversation|thought leader(ship)?)\b", "self-promotion tell", True),
    # B. rhythm by rule: contrast reveals and negation lists
    (r"\b(it|this|that)(?:'s| is| was|'s really| is really) not (just |only |about )?[^.;:\n]{1,60}[,;] (it|this|that)(?:'s| is| was)\b", "contrast reveal ('it's not X, it's Y')", True),
    (r"\bnot (just|only|merely) [^.;\n]{1,60}, but (also )?\b", "contrast reveal ('not just X, but Y')", True),
    (r"\b(this|it|that) (does not|doesn'?t|isn'?t|is not|wasn'?t|was not) (mean|about) [^.\n]{1,60}\.\s+(it|this|that) (means|is about|was about)\b", "contrast reveal (split across two sentences)", True),
    (r"\b(isn'?t|is not|wasn'?t|was not|aren'?t|are not) (about|the) [^.\n]{1,50}\.\s+(it'?s|it is|they'?re|they are|this is) (about|the)\b", "contrast reveal (split across two sentences)", True),
    (r"\bless [a-z]+, more [a-z]+\b", "contrast slogan ('less X, more Y')", True),
    (r"(?:^|[.!?]\s+)(no|not) [^.\n]{1,30}\.\s+(no|not) [^.\n]{1,30}\.\s+(no|not) [^.\n]{1,30}\.", "negation list", True),
    (r"(?:^|\n|[.!?]\s+)(the (result|answer|catch|kicker|secret|twist|problem|truth|lesson|fix|reason)|why|how|what happened( next)?|the best part)\?\s", "self-answered question", True),
    (r"\b(here'?s (why|how|the thing|what happened)|the (secret|kicker|catch|twist|lesson) ?:)", "colon reveal", True),
    # C. inflation: filler and borrowed authority
    (r"\b(delve[sd]?|delving|tapestry|pivotal|testament to|underscores?|underscored|realm|embark(ed|ing)?|foster(s|ed|ing)?|harness(es|ed|ing)?"
     r"|empower(s|ed|ing)?|synerg(y|ies)|holistic|cutting[- ]edge|ever[- ]evolving|unlock(s|ed|ing)?|elevate[sd]?|elevating|seamless(ly)?|robust"
     r"|leverag(e|es|ed|ing)|game[- ]changer|game[- ]changing|paradigm|transformative|navigat(e|ing) the)\b", "filler word", True),
    (r"\b(the|today'?s|this|our|the current) (business |digital |competitive |marketing )?landscape\b", "'landscape' as an abstract noun", True),
    (r"\b(studies show|research shows|experts (agree|say)|according to experts|it'?s (widely )?known that|science says|data shows)\b", "borrowed authority", True),
    (r"\b(to be honest|honestly,|if i'?m being honest|i mean,? |let'?s be real|truth be told|frankly,|candidly,)", "announced honesty", True),
    (r"\bmore and more\b|\bmore than ever\b", "'more' as an intensifier", True),
    (r"\bmore\b(?![^.\n]{0,30}\bthan\b)", "'more' with no comparison: is a specific figure possible?", False),
    (r"\b(world[- ]class|best[- ]in[- ]class|innovative|unparalleled|second to none|next[- ]level|revolutionary)\b", "vague superlative", True),
    # F. wrong reader: legal, tax, country
    (r"\b(by law|the law (says|requires)|legally (required|obliged)|required by law|you are legally|statutory)\b", "states what a law requires", True),
    (r"\b(guarantee[sd]?|guaranteed) (results|reach|growth|leads|clients|ranking)\b", "promises a result", True),
    # this skill's own list
    (r"(?:^|[.!?]\s+|\n)(tired of|struggling with|ready to|sick of|fed up with|want to|looking to)\b[^.?\n]{0,80}\?", "generic question hook", True),
    (r"\b(buyers|customers|clients|people|everyone|the market|your market|most (buyers|people|customers|sellers|owners)) (want|wants|love|loves|hate|hates|need|needs|think|thinks|agree|always|never)\b"
     r"|(?<!what )(?<!how )(?<!where )\b(buyers|customers|clients|people|everyone|most (buyers|people|customers)) (say|says)\b", "claim about buyers in general (say how many voices instead, or 'what buyers said')", True),
    (r"\b(the market says|everybody knows|all buyers|every buyer|no buyer)\b", "claim about the market", True),
    (r"\b(testimonial|as one (client|customer) (said|put it)|our (clients|customers) (say|said)|said one (client|customer))\b", "presents a public post as a testimonial", True),
]
TRIPLET = re.compile(r"\b(\w[\w'’-]*(?: \w[\w'’-]*){0,2}), (\w[\w'’-]*(?: \w[\w'’-]*){0,2}),? (and|or) (\w[\w'’-]*(?: \w[\w'’-]*){0,2})\b(?! [a-z]+ing\b)")
CLAUSE_WORDS = {"i", "we", "you", "he", "she", "they", "it", "that's", "it's", "i'm", "we're", "if", "because", "when", "which", "who",
                "so", "but", "then", "how", "what", "where", "why", "including", "is", "was", "are", "were", "to", "i'd", "i've", "there's"}


def is_list(m):
    """A real three-item list: short noun-like items, not three clauses strung together."""
    for g in (m.group(1), m.group(2), m.group(4)):
        if any(w.lower().replace("’", "'") in CLAUSE_WORDS for w in g.split()):
            return False
    return True
HASHTAG = re.compile(r"(?<![\w&])#[\wÀ-ɏ]+")


def lines_of(text):
    return [l for l in text.split("\n") if l.strip()]


def sentences(line):
    return [s for s in re.split(r"(?<=[.!?])\s+", line.strip()) if s.strip()]


def norm(s):
    s = s.lower().replace("’", "'")
    return re.sub(r"\s+", " ", re.sub(r"[^\w' ]+", " ", s)).strip()


def check_text(text, lang="en", allow_emoji=False, allow_exclaim=False, source_text="", nevers=None):
    """Return (problems, warns, stats). Every finding is a short string with the offending span."""
    problems, warns = [], []
    src = " " + norm(source_text) + " " if source_text else ""

    def ctx(m, t):
        return t[max(0, m.start() - 25):m.end() + 25].replace("\n", " ").strip()

    for m in DASHES.finditer(text):
        problems.append(f"dash: '{ctx(m, text)}' (use a full stop, comma, colon or brackets)")
    emoji = EMOJI.findall(text)
    if emoji and not allow_emoji:
        problems.append(f"{len(emoji)} emoji: the founder's own writing shows none on this channel")
    for l in lines_of(text):
        if EMOJI.match(l.strip()):
            problems.append(f"emoji used as a bullet: '{l.strip()[:40]}'")
    ex = text.count("!")
    if ex and not allow_exclaim:
        problems.append(f"{ex} exclamation mark(s): business copy without the founder's own habit of them")
    tags = HASHTAG.findall(text)
    if len(tags) > 5:
        problems.append(f"{len(tags)} hashtags (more than five reads as bait)")
    elif len(tags) > 3:
        warns.append(f"{len(tags)} hashtags")
    for w in nevers or []:
        if w.strip() and re.search(r"(?<!\w)" + re.escape(w.strip()) + r"(?!\w)", text, re.I):
            problems.append(f"uses '{w.strip()}', which the founder never uses")
    ls = lines_of(text)
    if len(ls) >= 8:
        short_single = sum(1 for l in ls if len(sentences(l)) == 1 and len(l.split()) <= 10)
        share = short_single / len(ls)
        if share >= 0.9:
            problems.append(f"broetry: {short_single} of {len(ls)} lines are one short sentence; join some into paragraphs")
        elif share >= 0.75:
            warns.append(f"close to broetry: {short_single} of {len(ls)} lines are one short sentence")
    if lang == "en":
        for pat, label, is_problem in EN_PATTERNS:
            flags = re.I | re.M
            for m in re.finditer(pat, text, flags):
                span = norm(m.group(0))
                if src and span and (" " + span + " ") in src and label != "dash":
                    warns.append(f"kept, the founder said it: {label}: '{ctx(m, text)}'")
                    continue
                (problems if is_problem else warns).append(f"{label}: '{ctx(m, text)}'")
        trip = [m for m in TRIPLET.finditer(text) if is_list(m)]
        trip = [m for m in trip if not (src and (" " + norm(m.group(0)) + " ") in src)]
        if len(trip) >= 3:
            problems.append(f"{len(trip)} three-item lists in one piece (two at most): " + "; ".join(f"'{m.group(0)}'" for m in trip[:3]))
        elif trip:
            warns.extend(f"three-item list: '{m.group(0)}'" for m in trip)
    words = len(re.findall(r"[\wऀ-ॿ'’-]+", text))
    return problems, warns, {"words": words, "characters": len(text), "emoji": len(emoji), "exclamations": ex,
                             "hashtags": len(tags), "lang_patterns": lang == "en"}


def main():
    if hasattr(signal, "SIGPIPE"):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?")
    ap.add_argument("--text")
    ap.add_argument("--lang", default="en")
    ap.add_argument("--allow-emoji", action="store_true")
    ap.add_argument("--allow-exclamations", action="store_true")
    ap.add_argument("--source")
    ap.add_argument("--never", action="append")
    try:
        a = ap.parse_args()
    except SystemExit as e:
        if e.code not in (0, None):
            print("STOP: the command was not understood; see the usage at the top of scripts/check_copy.py")
            sys.exit(2)
        raise
    if a.text is None and not a.file:
        print("STOP: give a file to check or --text")
        sys.exit(2)
    if a.text is None and not os.path.exists(a.file):
        print(f"STOP: cannot find {a.file}")
        sys.exit(2)
    text = a.text if a.text is not None else open(a.file, encoding="utf-8").read()
    src = ""
    if a.source:
        if not os.path.exists(a.source):
            print(f"STOP: cannot find the source file {a.source}")
            sys.exit(2)
        src = open(a.source, encoding="utf-8").read()
    problems, warns, st = check_text(text, a.lang, a.allow_emoji, a.allow_exclamations, src, a.never)
    for p in problems:
        print("PROBLEM:", p)
    for w in warns:
        print("WARN:", w)
    note = "" if st["lang_patterns"] else " (English-only patterns not run for this language: review those by hand)"
    print(f"{len(problems)} problems, {len(warns)} warnings, {st['words']} words, {st['characters']} characters{note}")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
