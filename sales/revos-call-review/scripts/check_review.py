#!/usr/bin/env python3
"""Check a written call review, or any copy, before the founder sees it.

Usage:
  python3 scripts/check_review.py <review.md> --measure <measure.json> [--results <results.json>]
        full check of a review: every [position] "quote" is verbatim from the transcript at that
        position, exactly two coaching points each ending in a line to say, a drill, creation points,
        prospects by initials only, no banned or held-out wording, no Merigrove line in the file
  python3 scripts/check_review.py --copy <file>       copy check only (chat summary, a note)
  python3 scripts/check_review.py --text "some copy"  copy check of a string

Prints PROBLEM and WARN lines and a count. Exit 0 clean, 1 problems found, 2 STOP (a file is missing).
Standard library only. No network calls.
"""
import argparse
import json
import os
import re
import sys

# ---------------------------------------------------------------- copy patterns (references/banned-patterns.md)
BASE_PROBLEMS = {
    "[\u2014\u2013]": "em or en dash",
    r"\bin today'?s (fast-paced|digital|ever-changing)": "stock opener",
    r"\bit'?s not (just )?[^.\n]{1,40}, it'?s\b": "contrast reveal",
    r"\b(game[- ]changer|delve|unlock(s|ing)?|elevate(s|d)?|seamless(ly)?|leverag(e|es|ing))\b": "filler word",
    r"\b(I mean|to be honest|if I'?m being honest|let'?s be real)\b": "announced honesty",
    r"\[STAT\]|\[VERIFY\]": "internal placeholder left in founder copy; use [NEED: ...]",
}
DOMAIN_PROBLEMS = {
    r"\bgreat (job|work) (on |at )?(building )?rapport\b": "coaching cliche",
    r"\boverall,? (a |this was a |it was a )?(solid|good|great|decent|strong) call\b": "coaching cliche",
    r"\bareas? (for|of) (improvement|growth|development)\b": "coaching cliche",
    r"\bstrengths and (weaknesses|areas)\b": "coaching cliche",
    r"\bkeep up the (good|great) work\b": "coaching cliche",
    r"\b(build|building) (more |better )?rapport\b": "coaching cliche with no behaviour",
    r"\bask (more )?open[- ]ended questions\b": "coaching cliche with no behaviour",
    r"\bbe (more )?(confident|assertive)\b": "coaching cliche with no behaviour",
    r"\b(trust the process|always be closing)\b": "coaching cliche",
    r"\b(well done|nice work|you did (great|well)|great call)\b": "praise with no quote",
    r"\b(time[- ]?waster|tyre[- ]?kicker|tire[- ]?kicker|bad lead|cheapskate|flaky|never going to buy|"
    r"(was|were) not serious|(wasn'?t|weren'?t) serious|difficult (prospect|client|person)|"
    r"(prospect|client|she|he|they) (was|were) (rude|stubborn|unreasonable|difficult))\b": "blames the prospect",
    r"\bthis is (not )?legal advice\b(?! and)": "check the disclaimer wording",
    r"\b(you will|you'?ll) (definitely )?(close|win|get the deal)\b": "promise of a result",
    # Build Standard 0.1: no legal or tax advice, no country assumed. A prospect's own words, quoted, are exempt.
    r"\b(the law (says|requires|states)|required by law|by law|legally (required|obliged|obligated|bound)|"
    r"(you|they|we) (are|'re|were) (legally )?(required|obliged|obligated) to|(it'?s|it is|is|was) (illegal|unlawful)|"
    r"(one|two|single|all|dual)[- ]party consent|consent law)\b": "states what a law requires; use the one generic consent line",
    r"\b(GDPR|" + "PE" + r"CR|TCPA|CCPA|CPRA|CAN-SPAM|HIPAA|PDPA|DPDP|CASL|LGPD|POPIA|Ofcom|FTC|FCA)\b": "names a law or regulator; use the one generic consent line",
    r"\b(solicitor|attorney|lawyer|(UK|US|EU|Indian|Australian|Singapore|British|American) (law|rules|regulations?)|"
    r"bank holidays?|federal holidays?)\b": "assumes a country or refers the founder to a lawyer; use the one generic consent line",
    r"\b\d+(\.\d+)?\s?(%|per ?cent) (VAT|GST|sales tax|tax)\b|"
    r"\b(VAT|GST|sales tax|tax(es)?)\b[^.\n]{0,20}\b(would be|comes to|works out|adds up to|makes it|that'?s|is)\s?"
    r"[$\u00a3\u20ac\u20b9\u00a5]?\s?\d|\b(after[- ]tax|pre[- ]tax|tax[- ]deductible|tax (relief|break|credit|saving)s?|"
    r"write (it|this|that) off)\b": "works out tax or gives tax advice; show the price exactly as said on the call",
}
COPY_WARNS = {
    r"\bmore\b": "'more' as an intensifier: is a specific comparison possible?",
    r"!": "exclamation mark in business copy",
    r"\b(robust|cutting[- ]edge|world[- ]class|best[- ]in[- ]class|innovative)\b": "vague superlative",
    r"\b(perhaps|it might be worth|you might want to|consider (asking|trying))\b": "softened coaching: say what to do",
}
FRAMEWORK_WORDS = [r"cost of inaction", r"gap build", r"belief[- ]change", r"the loop\b", r"scorecard", r"dimension",
                   r"\bCOI\b", r"\bBANT\b", r"\bMEDDI?CC?\b", r"\bSPIN\b", r"\bSandler\b", r"\bChallenger\b",
                   r"pain funnel", r"objection handling", r"\bframework\b"]

# ---------------------------------------------------------------- held-out wording
# A register of wording and method this skill never teaches, carried as data. Each pattern is written in
# pieces joined by "+" so this file never holds the wording as readable text. A hit is always a PROBLEM.
# Transcript quotes that the checker has verified are excluded: a seller may have said one of these.
_LEAD_ACTION = (r"(?:(?:it )?lo" + r"oks like you|i (?:can )?(?:notic|see|saw)\w* (?:that )?you|i gather you|"
                r"mentioned you|you (?:recently |just |kindly )?(?:downloaded|filled|signed up|registered|requested|"
                r"opted|enquired|clicked|visited|watched|came through|reached out|got in touch|booked|grabbed|asked about))")
_AGREE_TAG = (r"(?:\bright\s*\?|\bcorrect\s*\?|\bis that (?:right|correct|so)\s*\?|\bdidn'?t you\s*\?|\bdid you not\s*\?|"
              r"\bhaven'?t you\s*\?|\bweren'?t you\s*\?|\bwasn'?t it\s*\?|\byeah\s*\?|\byes\s*\?)")
HELD_OUT = (
    ("a stated-reason line before a question", (
        r"\bthe rea" + r"son (?:that )?i(?:'m| am)? ask(?:ing)?\b",
        r"\b(?:rea" + r"son|why) i(?:'m| am) ask" + r"ing\b",
        r"\bso you know why " + r"i(?:'m| am)? ask",
        r"\bso (?:that )?you know why " + r"i(?:'m| am)? (?:ask|rais|bring)",
        r"\bi(?:'m| am)? (?:only |just )?ask" + r"(?:ing)? (?:you )?(?:this |that )?(?:is )?because\b",
        r"\brea" + r"son (?:for|behind) (?:the|this|my) question\b",
        r"\bso i'?m not gue" + r"ss",
        r"\bcontextu" + r"ali[sz](?:e|ed|es|ing|ation)\b[^.\n]{0,40}\bquestions?\b",
        r"\bexplain(?:s|ing)? why (?:the|a|each|this) " + r"question is (?:being )?asked\b")),
    ("a posture line", (
        r"\bsales " + r"hat\b",
        r"\bdetached " + r"(?:but|and|yet) (?:certain|confident|sure)\b",
        r"\bstay(?:s|ing)? " + r"detached\b",
        r"\bdetach(?:ed|ment)? " + r"from the (?:outcome|result|sale|deal)\b",
        r"\btonal" + r"ity\b")),
    ("an opener that puts the lead's action to them for agreement", (
        r"\b" + _LEAD_ACTION + r"\b[^\n]{0,160}?" + _AGREE_TAG,
        r"\byou [a-z' ]{3,40}, ri" + r"ght\s*\?")),
    ("a permission opener, time check or callback line", (
        r"\bsoft" + r"en(?:er|ers|ing)?\b[^.\n]{0,20}\bdiffuse\b",
        r"\bdiffuse " + r"(?:the |any |their )?resistance\b",
        r"\bpermission[- ]" + r"based (?:phone )?opener\b",
        r"\b(?:have i |did i )?ca" + r"(?:ught|tch) you at a (?:bad|good|busy|convenient|difficult) (?:time|moment)\b",
        r"\bis (?:this|now) a (?:bad|good|convenient|ok|okay) (?:time|moment)\b",
        r"\bif (?:now|this) is(?:n'?t| not| no)? (?:no )?(?:good|a good time|convenient|a bad time)\b",
        r"\b(?:do you have|have you got|you got|can you spare|could you spare|can i (?:have|take|grab|borrow)|"
        r"could i (?:have|take|grab|borrow)|give me) (?:just |a )?(?:thirty|30|twenty|20|sixty|60|ten|10|a few|a couple of|"
        r"two|one|a) (?:quick )?(?:seconds?|secs?|minutes?|mins?|moments?)\b",
        r"\bwhen (?:should|shall|can|could|would|do you want|would you like) (?:i|me to) (?:ring|call|phone|try) "
        r"(?:you )?(?:back|again)\b",
        r"\b(?:ring|call|phone) you ba" + r"ck (?:later|another time|tomorrow|this afternoon|in a bit)\b",
        r"\b(?:better|good) time (?:for me )?to (?:ring|call|phone) (?:you )?(?:back)?\b")),
    ("a permission preface before a question", (
        r"\bjust so i'?m not " + r"wasting your time\b",
        r"\bnot wasting " + r"your time or mine\b",
        r"\bwasting each " + r"other'?s time\b",
        r"\bso (?:that )?(?:we|i)(?:'re|'m| are| am)? not (?:wasting|going to waste)\b",
        r"\b(?:would it be|is it) (?:all ?right|alright|ok|okay|fine)(?: with you)? (?:if|for) (?:i|me to) "
        r"(?:ask|asked|touch(?:ed)? on|rais(?:e|ed)|talk(?:ed)? about|get into|went into)\b[^\n]{0,60}"
        r"\b(?:budget|money|invest\w*|price|pricing|spend|afford\w*|number|figure|finances|cost|fees?)\b",
        r"\b(?:would you mind|do you mind|mind) if i (?:ask|asked)\b[^\n]{0,60}"
        r"\b(?:budget|money|invest\w*|price|pricing|spend|afford\w*|number|figure|finances|cost|fees?)\b")),
    ("a named question type or source this skill does not use", (
        r"\bconse" + r"quence questions?\b",
        r"\bconn" + r"ecting questions?\b",
        r"\bproblem[- ]aware" + r"ness questions?\b",
        r"\bsolution[- ]aware" + r"ness questions?\b",
        r"\bcommit" + r"ting questions?\b",
        r"\bneuro[- ]?" + r"emotional\b",
        r"\bN" + r"EPQ\b",
        r"\b(?:7|seven)" + r"th level\b",
        r"\b7" + r"L\b",
        r"\bjeremy " + r"miner\b",
        r"\bformer " + r"employer\b")),
)
_HELD = [(lab, re.compile("|".join("(?:%s)" % p for p in ps), re.I)) for lab, ps in HELD_OUT]


def held_out(text):
    """[(label, matched text)] for every held-out hit in text."""
    t = (text or "").replace("\u2019", "'").replace("\u2018", "'")
    out = []
    for lab, rx in _HELD:
        for m in rx.finditer(t):
            out.append((lab, m.group(0)))
    return out


QUOTED = re.compile(r"\"[^\"\n]*\"|\u201c[^\u201d\n]*\u201d|(?<!\w)'(?:[^'\n]|(?<=\w)'(?=\w)){2,160}'(?!\w)")


def copy_check(text, framework_scope=None):
    problems, warns = [], []
    # warnings are about the reviewer's words, not words quoted from the call or a recalled objection as the founder gave it
    unquoted = re.sub(r"(?m)^\s*\d+\. [^\n]*\(recall, unverified\)\s*$", " ", QUOTED.sub(" ", text))
    for pats, sink, src in ((BASE_PROBLEMS, problems, text), (DOMAIN_PROBLEMS, problems, text), (COPY_WARNS, warns, unquoted)):
        for pat, why in pats.items():
            for m in re.finditer(pat, src, re.I):
                sink.append(f"{why}: '{src[max(0, m.start() - 25):m.end() + 25].strip()}'")
    for lab, hit in held_out(text):
        problems.append(f"held-out wording ({lab}): '{hit}'; coach a different behaviour")
    if framework_scope is not None:
        for w in FRAMEWORK_WORDS:
            for m in re.finditer(w, framework_scope, re.I):
                problems.append(f"names a framework at the seller ('{m.group(0)}'); describe the behaviour instead")
    return problems, warns


# ---------------------------------------------------------------- transcript matching

def norm(s):
    s = (s or "").replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
    s = re.sub(r"[^\w'\[\] ]+", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def mask_names(text, prospects):
    """Replace each prospect's name (full, first, last) with [initials]."""
    out = text or ""
    for name, ini in prospects.items():
        if re.match(r"^(speaker|participant|unknown|guest|caller)\b", name, re.I):
            continue
        parts = [p for p in re.split(r"\s+", name) if len(p) > 1]
        for variant in [name] + parts:
            out = re.sub(r"\b" + re.escape(variant) + r"\b", f"[{ini}]", out)
    return out


def load_measure(path):
    if not path or not os.path.exists(path):
        print(f"STOP: there is no measure file at {path}. Run measure_call.py with --json-out first. Nothing was checked.")
        sys.exit(2)
    try:
        m = json.load(open(path, encoding="utf-8"))
        assert isinstance(m, dict) and isinstance(m.get("turns"), list)
    except Exception:  # noqa: BLE001
        print(f"STOP: {path} is not a measure file from measure_call.py. Run it again. Nothing was checked.")
        sys.exit(2)
    return m


def prospects_of(measure):
    return {t["who"]: t["initials"] for t in measure["turns"] if t["role"] == "prospect"}


def third_parties_of(measure, verdicts=None):
    """People the prospect named (from the measure, plus any the reviewer listed), minus the prospect and the seller."""
    names = list((measure or {}).get("third_parties") or []) + list((verdicts or {}).get("third_parties") or [])
    skip = set()
    for w in list(prospects_of(measure).keys()) if measure else []:
        skip.update(w.split())
    for w in ((verdicts or {}).get("seller") or "", (verdicts or {}).get("prospect_name") or ""):
        skip.update(w.split())
    out = []
    for n in names:
        n = str(n).strip()
        if n and n not in skip and n not in out:
            out.append(n)
    return out


def find_turn(measure, pos):
    """The turn index a cited position points at, or None. Accepts 16:32, 00:16:32, 1:02:03 and T14."""
    if pos is None:
        return None
    p = str(pos).strip().strip("[]")
    turns = measure["turns"]
    if re.fullmatch(r"T\d+", p, re.I):
        i = int(p[1:]) - 1
        return i if 0 <= i < len(turns) else None
    m = re.fullmatch(r"(?:(\d{1,2}):)?(\d{1,2}):(\d{2})", p)
    if not m:
        return None
    sec = int(m.group(1) or 0) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
    for i, t in enumerate(turns):
        if t.get("seconds") == sec:
            return i
    return None


def quote_ok(measure, pos, quote):
    """(True, '') when the quote is verbatim from the turn at pos (or the next turn by the same speaker)."""
    i = find_turn(measure, pos)
    if i is None:
        return False, f"position {pos} is not the start of any turn in the transcript"
    turns = measure["turns"]
    pros = prospects_of(measure)
    pool = [turns[i]]
    if i + 1 < len(turns) and turns[i + 1]["who"] == turns[i]["who"]:
        pool.append(turns[i + 1])
    hay = norm(" ".join(mask_names(t["text"], pros) for t in pool))
    hay_raw = norm(" ".join(t["text"] for t in pool))
    segs = [norm(x) for x in re.split(r"\.\.\.|\u2026", quote) if norm(x)]
    if not segs:
        return False, "empty quote"
    for h in (hay, hay_raw):
        at, ok = 0, True
        for sgm in segs:
            k = h.find(sgm, at)
            if k < 0:
                ok = False
                break
            at = k + len(sgm)
        if ok:
            return True, ""
    return False, f"not found word for word in the turn at {pos} ({turns[i]['initials'] if turns[i]['role'] == 'prospect' else turns[i]['who']})"


QUOTE_RE = re.compile(r"\[(?P<pos>(?:\d{1,2}:)?\d{1,2}:\d{2}|T\d+)\]\s*(?:[A-Z][\w.' ]{0,30}:\s*)?\"(?P<q>[^\"\n]{3,})\"")


CUT_MONEY = re.compile(r"(?:(?<=\s)|(?<=^)|(?<=\())[,.]\d{3}\b(?![,.]?\d)", re.M)


def cut_money(text):
    """Amounts that lost their leading digits and symbol (a shell ate "$4" from "$4,500")."""
    return [m.group(0) for m in CUT_MONEY.finditer(text or "")]


def section(text, heading):
    m = re.search(r"^" + re.escape(heading) + r"\s*$(.*?)(?=^## |\Z)", text, flags=re.M | re.S)
    return m.group(1) if m else ""


def check_review(text, measure, results=None):
    problems, warns = [], []
    recall = bool(re.search(r"^Mode: recall", text, re.M)) or (results or {}).get("mode") == "recall"
    # quotes
    verified_spans = []
    quotes = list(QUOTE_RE.finditer(text))
    if recall:
        if quotes:
            problems.append("a recall review cites a transcript position with a quote; recall reviews quote nothing as verbatim")
        if re.search(r"\b\d{1,2}:\d{2}\b", re.sub(r"Updated: .*|\d{4}-\d{2}-\d{2}", "", text)):
            problems.append("a recall review cites a time; never cite an unverifiable time as if verified")
        if "(recall, unverified)" not in text:
            problems.append("a recall review must mark its findings '(recall, unverified)'")
    else:
        if measure is None:
            problems.append("no measure file: quotes cannot be verified")
        else:
            for m in quotes:
                ok, why = quote_ok(measure, m.group("pos"), m.group("q"))
                if ok:
                    verified_spans.append((m.start(), m.end()))
                else:
                    problems.append(f"quote [{m.group('pos')}] \"{m.group('q')[:50]}\": {why}")
            if len(quotes) < 4:
                problems.append(f"only {len(quotes)} quoted moments; every finding cites a position and quotes the transcript")
            for m in re.finditer(r"\[((?:\d{1,2}:)?\d{1,2}:\d{2}|T\d+)\]", text):
                if find_turn(measure, m.group(1)) is None:
                    problems.append(f"position [{m.group(1)}] is not the start of any turn in the transcript")
    # strip verified quotes before scanning copy, so a seller's own words are not charged to the review
    scan = text
    for a, b in reversed(verified_spans):
        scan = scan[:a] + " " + scan[b:]
    coach = section(text, "## The two things to change")
    drill = section(text, "## The drill")
    coach_scan = coach
    for m in QUOTE_RE.finditer(coach):
        coach_scan = coach_scan.replace(m.group(0), " ")
    p2, w2 = copy_check(scan, framework_scope=coach_scan + "\n" + drill)
    problems += p2
    warns += w2
    # structure
    heads = ["## The two things to change", "## The drill", "## Where the deal was lost", "## Scorecard",
             "## Stage by stage", "## Objections", "## The next step", "## Stated reason and real reason"]
    for h in heads:
        if not re.search(r"^" + re.escape(h) + r"\s*$", text, re.M):
            problems.append(f"missing section {h}")
    points = re.findall(r"^### (\d)\. ", coach, re.M)
    if len(points) != 2:
        problems.append(f"exactly two coaching points, found {len(points)}")
    for blk in re.split(r"^### \d\. ", coach, flags=re.M)[1:]:
        if not re.search(r"Say:\s*\"[^\"]{8,}\"\s*$", blk.strip(), re.M):
            problems.append("a coaching point does not end in the line to say, in quotation marks ('Say: \"...\"')")
        if not re.search(r"\bbecause\b", blk, re.I):
            problems.append("a coaching point has no cause and effect ('Because ...')")
    if not drill.strip():
        problems.append("the drill is empty")
    elif re.search(r"\b(read|watch|study|course|book|video|article|podcast|research)\b", drill, re.I):
        problems.append("the drill asks the founder to read or watch something; it must be doable with nothing else to read")
    lost = section(text, "## Where the deal was lost")
    if "No failure to trace" in lost:
        pass
    elif recall:
        if not re.search(r"Showed up:", lost) or not re.search(r"Started:", lost):
            problems.append("Where the deal was lost needs each failure as 'Showed up: ... Started: ...' in a recall review")
    elif not re.search(r"appeared at", lost) or not re.search(r"created at", lost):
        problems.append("Where the deal was lost needs each failure as 'appeared at ... created at ...'")
    for hit in cut_money(text):
        problems.append(f"an amount reads '{hit}' with its first digits and symbol missing; a shell probably ate '$' and a digit; "
                        "write files with the file tool or a quoted heredoc and render again")
    # prospects by initials only; people the prospect named, by role outside quotes and Say lines
    v = (results or {}).get("verdicts") or {}
    pros = prospects_of(measure) if measure else {}
    pn = (v.get("prospect_name") or "").strip()
    if pn and pn.lower() != "not given":
        pros = {**pros, pn: v.get("prospect") or "initials"}
    third = third_parties_of(measure, v)
    if third:
        wb = section(scan, "## The way back in")   # the message the seller sends uses the names, like a Say line
        wb_lines = {ln for ln in wb.split("\n") if ln.strip().startswith(">")}
        plain = "\n".join(ln for ln in scan.split("\n") if not re.match(r"^\s*(Say|Say instead):", ln.strip())
                           and ln not in wb_lines)
        plain = re.sub(r"\|\s*\"[^|]*\"\s*\|\s*$", "|", plain, flags=re.M)   # the Say instead column of the stage table
        plain = QUOTED.sub(" ", plain) if recall else plain
        for n in third:
            if re.search(r"\b" + re.escape(n) + r"\b", plain):
                problems.append(f"'{n}', someone the prospect named, appears outside a quote or Say line; refer to them by role")
    if pros:
        for name in pros:
            if re.match(r"^(speaker|participant|unknown|guest|caller)\b", name, re.I):
                continue
            for part in [name] + [p for p in name.split() if len(p) > 2]:
                if re.search(r"\b" + re.escape(part) + r"\b", text):
                    problems.append(f"the prospect's name '{part}' appears; prospects by initials only")
                    break
    # the score
    sm = re.search(r"\*\*(\d{1,3}) out of 100\.\*\*", text)
    if not sm:
        problems.append("no score line ('**n out of 100.**')")
    elif results and int(sm.group(1)) != results.get("overall"):
        problems.append(f"the score in the file ({sm.group(1)}) is not the scorer's ({results.get('overall')})")
    if re.search(r"Merigrove|BUSINESS_AUDIT_URL", text):
        problems.append("the Merigrove line belongs at the end of the chat, never in the review file")
    if re.search(r"^Confidence: ", text, re.M) is None:
        problems.append("no Confidence line")
    return problems, warns


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", nargs="?")
    ap.add_argument("--measure")
    ap.add_argument("--results")
    ap.add_argument("--copy")
    ap.add_argument("--text")
    a = ap.parse_args()
    if a.text is not None or a.copy:
        if a.copy and not os.path.exists(a.copy):
            print(f"STOP: there is no file at {a.copy}. Nothing was checked.")
            sys.exit(2)
        text = a.text if a.text is not None else open(a.copy, encoding="utf-8").read()
        problems, warns = copy_check(text)
    else:
        if not a.file or not os.path.exists(a.file):
            print(f"STOP: there is no review file at {a.file}. Nothing was checked.")
            sys.exit(2)
        text = open(a.file, encoding="utf-8").read()
        recall = bool(re.search(r"^Mode: recall", text, re.M))
        measure = None if (recall and not a.measure) else load_measure(a.measure)
        results = None
        if a.results:
            if not os.path.exists(a.results):
                print(f"STOP: there is no results file at {a.results}. Nothing was checked.")
                sys.exit(2)
            results = json.load(open(a.results, encoding="utf-8"))
        problems, warns = check_review(text, measure, results)
    for x in problems:
        print("PROBLEM:", x)
    for x in warns:
        print("WARN:", x)
    print(f"{len(problems)} problems, {len(warns)} warnings")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print(f"STOP: the check could not run ({type(e).__name__}: {e}). Nothing was checked.")
        sys.exit(2)
