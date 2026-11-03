#!/usr/bin/env python3
"""Check the five follow-up emails in a Lead Magnet Factory spec.

Usage:
  python3 scripts/emails.py check <spec.json> [--previous <earlier spec.json>] [--subjects-file <file>]

Per email: a job, two different subject lines under 50 characters, preview text that does not repeat a subject,
a body of 120 to 220 words, at most one link, the founder's sign-off, a P.S. (email one may drop it when the spec
says so). Across the five: the magnet link only in email one, the booking link only in email five (the hard ask),
email two carries one paragraph per tier for a scorecard, email five says who the call is not for, merge tags only
from the named set. With --previous (or a subjects file of earlier subject lines, one per line): no subject line
repeats and no body shares a run of 12 or more words with the earlier pack.
Exit 0 clean; 1 PROBLEM lines; 2 STOP. Standard library only. No network calls.
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

LINK = re.compile(r"\{\{(magnet_link|booking_link)\}\}|https?://\S+")
SHINGLE = 12


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s']", " ", str(s or "").lower())).strip()


def shingles(text, n=SHINGLE):
    w = norm(text).split()
    return {" ".join(w[i:i + n]) for i in range(len(w) - n + 1)}


def check(spec, previous=None, old_subjects=()):
    problems, warns = [], []
    P, W = problems.append, warns.append
    la = spec.get("launch") or {}
    ems = la.get("emails") or []
    f = spec.get("founder") or {}
    signoff = str(f.get("signoff") or "").strip()
    if len(ems) != 5:
        P(f"the sequence has exactly five emails; this one has {len(ems)}")
    fmt = spec.get("format")
    tiers = [t.get("name") for t in (spec.get("magnet") or {}).get("tiers") or []] if fmt == "scorecard" else []
    all_subjects = []
    no_ps_first = bool((la.get("rules") or {}).get("no_ps_email_one"))
    for i, e in enumerate(ems, 1):
        tag = f"email {i}"
        if not str(e.get("job") or "").strip():
            P(f"{tag}: say its one job")
        subs = e.get("subjects") or []
        if len(subs) != 2:
            P(f"{tag}: write two subject lines (A and B)")
        for s in subs:
            if len(s) >= 50:
                P(f"{tag}: subject '{s}' is {len(s)} characters; keep it under 50")
            if not s.strip():
                P(f"{tag}: an empty subject line")
        if len(subs) == 2 and norm(subs[0]) == norm(subs[1]):
            P(f"{tag}: the two subject lines are the same")
        all_subjects += [norm(s) for s in subs]
        pv = str(e.get("preview") or "").strip()
        if not pv:
            P(f"{tag}: preview text is missing")
        elif any(norm(pv) == norm(s) or norm(pv).startswith(norm(s)) for s in subs):
            P(f"{tag}: the preview repeats the subject; say the next thing instead")
        elif len(pv) > 110:
            W(f"{tag}: preview is {len(pv)} characters; most inboxes show about 90")
        body = str(e.get("body") or "")
        n = len(C.words(re.sub(r"\{\{[^}]+\}\}", "x", body)))
        if not 120 <= n <= 220:
            P(f"{tag}: the body is {n} words; write 120 to 220")
        links = LINK.findall(body) + LINK.findall(str(e.get("ps") or ""))
        if len(links) > 1:
            P(f"{tag}: {len(links)} links; one email carries at most one")
        alltext = body + " " + str(e.get("ps") or "") + " " + " ".join(subs) + " " + pv
        for tagm in re.findall(r"\{\{[^}]*\}\}", alltext):
            if tagm not in C.MERGE_TAGS:
                P(f"{tag}: merge tag {tagm} is not in the named set ({', '.join(sorted(C.MERGE_TAGS))})")
        if re.search(r"\{\{unsubscribe_link\}\}", body):
            W(f"{tag}: the unsubscribe link sits in the body; the email tool adds it in the footer")
        if "{{magnet_link}}" in alltext and i != 1:
            P(f"{tag}: the magnet link belongs in email one only (later emails point back by name)")
        if "{{booking_link}}" in alltext and i != 5:
            P(f"{tag}: the booking link belongs in email five only; emails one to four ask softly (reply, think)")
        if i == 1 and "{{magnet_link}}" not in alltext:
            P("email 1: carries the link to the lead magnet ({{magnet_link}})")
        if re.search(r"https?://", alltext):
            P(f"{tag}: write links as merge tags ({{{{booking_link}}}}), not addresses, so the email tool fills them")
        so = str(e.get("signoff") or signoff).strip()
        if signoff and so != signoff:
            P(f"{tag}: signs off '{so}'; the founder signs '{signoff}'")
        if signoff and body.rstrip().endswith(signoff):
            W(f"{tag}: the body already ends with the sign-off; it is added from the spec")
        if not str(e.get("ps") or "").strip() and not (i == 1 and no_ps_first):
            P(f"{tag}: add a P.S.")
        if "{{first_name}}" not in body:
            W(f"{tag}: no {{{{first_name}}}} in the body")
        paras = [p for p in re.split(r"\n\s*\n", body) if p.strip()]
        if i == 2 and tiers:
            for t in tiers:
                hits = [p for p in paras if re.search(r"\b" + re.escape(t) + r"\b", p, re.I)]
                if len(hits) != 1:
                    P(f"email 2: needs one paragraph for the tier '{t}' (found it in {len(hits)})")
            if not re.search(r"\breply\b", body, re.I):
                P("email 2: ask them to reply with their score")
        if i == 5:
            if not re.search(r"\b(not|isn'?t|won'?t be|aren'?t) (for|right for|a fit|the right)\b", body, re.I):
                P("email 5: say plainly who the call is not for")
            has_link = "{{booking_link}}" in alltext
            route = ((spec.get("magnet") or {}).get("cta") or {}).get("link") or (spec.get("offer") or {}).get("link")
            if route and not has_link:
                P("email 5: the one invitation needs the booking link ({{booking_link}})")
    if len(set(all_subjects)) != len(all_subjects):
        P("two emails share a subject line")
    if previous:
        old = previous.get("launch", {}).get("emails") or []
        old_subjects = list(old_subjects) + [norm(s) for e in old for s in e.get("subjects") or []]
        old_sh = set()
        for e in old:
            old_sh |= shingles(e.get("body"))
        for i, e in enumerate(ems, 1):
            shared = shingles(e.get("body")) & old_sh
            if shared:
                P(f"email {i}: shares a run of {SHINGLE} words with the earlier pack: '{sorted(shared)[0]}'")
    for i, e in enumerate(ems, 1):
        for s in e.get("subjects") or []:
            if norm(s) in set(old_subjects):
                P(f"email {i}: subject '{s}' was used in an earlier pack")
    return problems, warns


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["check"])
    ap.add_argument("spec")
    ap.add_argument("--previous")
    ap.add_argument("--subjects-file")
    a = ap.parse_args()
    spec = C.load_spec(a.spec)
    prev = C.load_spec(a.previous) if a.previous else None
    olds = []
    if a.subjects_file:
        olds = [norm(x) for x in C.read_text(a.subjects_file).splitlines() if x.strip()]
    if not prev and spec.get("previous_spec"):
        p = spec["previous_spec"]
        p = p if os.path.isabs(p) else os.path.join(os.path.dirname(spec["_path"]), p)
        if os.path.exists(p):
            prev = C.load_spec(p)
    olds += [norm(x) for x in spec.get("previous_subjects") or []]
    problems, warns = check(spec, prev, olds)
    for x in problems:
        print("PROBLEM:", x)
    for x in warns:
        print("WARN:", x)
    for i, e in enumerate((spec.get("launch") or {}).get("emails") or [], 1):
        n = len(C.words(re.sub(r"\{\{[^}]+\}\}", "x", str(e.get("body") or ""))))
        print(f"email {i}: {n} words; subjects {', '.join(str(len(s)) for s in e.get('subjects') or [])} characters")
    print(f"{len(problems)} problems, {len(warns)} warnings")
    return 1 if problems else 0


if __name__ == "__main__":
    C.run_main(main)
