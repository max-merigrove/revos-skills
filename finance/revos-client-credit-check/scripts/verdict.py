#!/usr/bin/env python3
"""The verdict rule: Go, Caution or Stop from the logged signals, with a trace.

Usage (paths relative to this skill's folder):
  python3 scripts/verdict.py <signals.json>     print the verdict and the trace
  python3 scripts/verdict.py --self-test        30 signal combinations with their expected verdicts

signals.json: {"findings": [...], "entity_verified": true|false, "peak_as_offered": 14000, "limit": 3000,
               "refused_all_rungs": false}
Each finding: {"id": "R6", "status": "found" | "clear" | "not_checked", "confidence": "verified" |
"public report" | "founder reported" | "unverified", "severity": "stop" | "major" | "minor" | "context",
"source": "...", "checked": "YYYY-MM-DD"}

The rule (working defaults, shown in the brief):
  STOP     a verified stop signal, or the client has refused every rung of the terms (return run only)
  CAUTION  any major signal (verified, public report or founder reported), or two or more minor signals,
           or the entity could not be verified and the peak unpaid work under the client's terms is above
           the founder's limit
  GO       otherwise, which means only that no stop or major signal was found in what could be checked
Unverified findings never count; they become questions. Only verified signals can decide Stop.
Exit 0 done; 1 a found signal has no source or confidence; 2 unreadable input.
Standard library only. No network calls.
"""
import json
import sys

COUNTING = {"verified", "public report", "founder reported"}


def decide(findings, entity_verified, peak_as_offered=None, limit=None, refused_all_rungs=False):
    """Returns (verdict, deciding, trace, questions)."""
    trace, questions = [], []
    stops, majors, minors = [], [], []
    for f in findings:
        if f.get("status") != "found":
            continue
        conf, sev = f.get("confidence"), f.get("severity")
        if conf == "unverified":
            questions.append(f["id"])
            trace.append(f"{f['id']} unverified: shown as a question, not counted")
            continue
        if conf not in COUNTING:
            continue
        if sev == "stop":
            if conf == "verified":
                stops.append(f["id"])
            else:
                majors.append(f["id"])
                trace.append(f"{f['id']} is a stop signal but {conf}, not verified: counted as major")
        elif sev == "major":
            majors.append(f["id"])
        elif sev == "minor":
            minors.append(f["id"])
    over = (peak_as_offered is not None and limit is not None and peak_as_offered > limit + 0.005)
    if stops:
        trace.append(f"Verified stop signal: {', '.join(stops)} -> STOP")
        return "STOP", "stop signal " + ", ".join(stops), trace, questions
    if refused_all_rungs:
        trace.append("The client refused every rung of the terms -> STOP")
        return "STOP", "every rung of the terms refused", trace, questions
    reasons = []
    if majors:
        reasons.append("major signal " + ", ".join(majors))
    if len(minors) >= 2:
        reasons.append(f"{len(minors)} minor signals ({', '.join(minors)})")
    if not entity_verified and over:
        reasons.append("entity not verified and the unpaid work under their terms is above your limit")
    if reasons:
        trace.append("CAUTION because: " + "; ".join(reasons))
        return "CAUTION", reasons[0], trace, questions
    if len(minors) == 1:
        trace.append(f"One minor signal ({minors[0]}) alone does not decide Caution")
    if not entity_verified:
        trace.append("Entity not verified, but the unpaid work under their terms is within your limit")
    trace.append("No stop or major signal found in what could be checked -> GO")
    return "GO", "no stop or major signal found in what could be checked", trace, questions


def validate(findings):
    bad = []
    for f in findings:
        if f.get("status") == "found" and (not f.get("source") or f.get("confidence") not in COUNTING | {"unverified"}):
            bad.append(f.get("id", "?"))
    return bad


CASES = [  # (description, findings as (id, severity, confidence), entity_verified, peak, limit, refused, expected)
    ("nothing found, verified", [], True, 5000, 10000, False, "GO"),
    ("one minor alone", [("F1", "minor", "founder reported")], True, 5000, 10000, False, "GO"),
    ("two minors", [("F1", "minor", "founder reported"), ("F4", "minor", "founder reported")], True, 14000, 3000, False, "CAUTION"),
    ("minor verified plus founder minor", [("R5", "minor", "verified"), ("F1", "minor", "founder reported")], True, 1, 10, False, "CAUTION"),
    ("one major founder", [("F3", "major", "founder reported")], True, 1, 10, False, "CAUTION"),
    ("F2 alone", [("F2", "major", "founder reported")], True, 1, 10, False, "CAUTION"),
    ("verified stop", [("R2", "stop", "verified")], True, 1, 10, False, "STOP"),
    ("verified stop plus reassurance", [("R2", "stop", "verified"), ("F7", "context", "founder reported")], True, 1, 10, False, "STOP"),
    ("stop from public report only", [("R3", "stop", "public report")], True, 1, 10, False, "CAUTION"),
    ("stop unverified", [("R3", "stop", "unverified")], True, 1, 10, False, "GO"),
    ("unverified entity above limit", [], False, 14000, 3000, False, "CAUTION"),
    ("unverified entity within limit", [], False, 2000, 3000, False, "GO"),
    ("unverified entity, limit unknown", [], False, 2000, None, False, "GO"),
    ("unverified entity at the limit exactly", [], False, 3000, 3000, False, "GO"),
    ("context only", [("R9", "context", "verified"), ("R12", "context", "verified")], True, 1, 10, False, "GO"),
    ("context plus one minor", [("R9", "context", "verified"), ("R6", "minor", "verified")], True, 1, 10, False, "GO"),
    ("three review reports major", [("R10", "major", "public report")], True, 1, 10, False, "CAUTION"),
    ("two review reports minor plus F1", [("R10", "minor", "public report"), ("F1", "minor", "founder reported")], True, 1, 10, False, "CAUTION"),
    ("R1 verified", [("R1", "stop", "verified")], False, 1, 10, False, "STOP"),
    ("refused every rung", [], True, 1, 10, True, "STOP"),
    ("major plus minors", [("R4", "major", "verified"), ("F1", "minor", "founder reported"), ("F4", "minor", "founder reported")], True, 1, 10, False, "CAUTION"),
    ("unverified minors do not count", [("R7", "minor", "unverified"), ("R8", "minor", "unverified")], True, 1, 10, False, "GO"),
    ("one unverified, one counted minor", [("R7", "minor", "unverified"), ("F6", "minor", "founder reported")], True, 1, 10, False, "GO"),
    ("cleared signals ignored", [("R2", "stop", "verified", "clear"), ("R5", "minor", "verified", "clear")], True, 1, 10, False, "GO"),
    ("not checked ignored", [("R3", "stop", "verified", "not_checked")], True, 1, 10, False, "GO"),
    ("sole trader above limit", [], False, 9500, 3000, False, "CAUTION"),
    ("sole trader above limit with F3", [("F3", "major", "founder reported")], False, 9500, 3000, False, "CAUTION"),
    ("stop beats refused", [("R2", "stop", "verified")], True, 1, 10, True, "STOP"),
    ("major R5 two periods", [("R5", "major", "verified")], True, 1, 10, False, "CAUTION"),
    ("four minors", [("F1", "minor", "founder reported"), ("F4", "minor", "founder reported"), ("F8", "minor", "founder reported"), ("R6", "minor", "verified")], True, 1, 10, False, "CAUTION"),
]


def _self_test():
    ok = fail = 0
    for desc, fs, ev, peak, limit, refused, expected in CASES:
        findings = [{"id": x[0], "severity": x[1], "confidence": x[2], "status": x[3] if len(x) > 3 else "found",
                     "source": "test"} for x in fs]
        got = decide(findings, ev, peak, limit, refused)[0]
        if got == expected:
            ok += 1
        else:
            fail += 1
            print(f"FAIL {desc}: got {got}, expected {expected}")
    bad = validate([{"id": "R2", "status": "found", "confidence": "verified", "source": ""}])
    if bad == ["R2"]:
        ok += 1
    else:
        fail += 1
        print("FAIL source check")
    print(f"{ok} passed, {fail} failed ({len(CASES)} combinations)")
    return fail == 0


def main(argv):
    if not argv or argv[0] in {"-h", "--help"}:
        print(__doc__)
        return 0
    if argv[0] == "--self-test":
        return 0 if _self_test() else 1
    try:
        data = json.load(open(argv[0], encoding="utf-8"))
        findings = data["findings"]
        if not isinstance(findings, list):
            raise ValueError
    except (OSError, ValueError, KeyError, TypeError):
        print("STOP: the signals file could not be read; it needs a 'findings' list. Nothing was decided.")
        return 2
    bad = validate(findings)
    if bad:
        print(f"PROBLEM: found signal(s) {', '.join(bad)} have no source or confidence; add them or drop the finding.")
        return 1
    v, deciding, trace, questions = decide(findings, bool(data.get("entity_verified")), data.get("peak_as_offered"),
                                           data.get("limit"), bool(data.get("refused_all_rungs")))
    print(f"VERDICT: {v} ({deciding})")
    for t in trace:
        print("TRACE:", t)
    for q in questions:
        print("QUESTION:", q)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
