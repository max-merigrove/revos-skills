#!/usr/bin/env python3
"""Hiring Readiness Check: the role pack (scorecard, job ad, interview guide, first 90 days) and its checks.

Usage:
  python3 scripts/role_pack.py template                                print a blank role pack file
  python3 scripts/role_pack.py check <rolepack.json> --inputs <inputs.json>
        check the structure (outcomes measurable and dated, each traced to a task the founder named,
        one interview question per outcome, decision rights at each stage, pay range or the founder's
        choice), the job ad wording (words that describe the person instead of the work, and recruitment
        cliches) and that the pack stays jurisdiction-neutral (no country's employment or tax terms)

The wording check is a prompt to review, never a compliance verdict: the founder checks the employment and
anti-discrimination rules where they hire. Exit codes: 0 clean, 1 PROBLEM lines
to fix, 2 STOP (file unreadable). Standard library only. No network calls.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_copy import check as copy_check  # noqa: E402

# Words that describe the person (age, sex, race or nationality, disability, family status) instead of the work.
# They put applicants off and are restricted in many places. Review, not a verdict. List: references/role-pack.md
RISK_TERMS = {
    r"\byoung\b|\byouthful\b|\byoung,? (dynamic|vibrant) team\b": "age: describes the people you want by age",
    r"\b(recent|new) graduates?\b|\bgraduates? only\b": "age: tends to exclude older applicants; describe the skill instead",
    r"\bdigital natives?\b": "age: a coded word for younger applicants; name the tools instead",
    r"\benergetic\b|\bhigh[- ]energy\b|\bfresh\b": "age: often read as wanting younger applicants",
    r"\bmature\b|\bearly[- ]career\b|\bjunior,? (person|individual)\b": "age: describes the person, not the work",
    r"\b(no more than|up to|maximum (of )?|max\.?)\s*\d+\s*years?'? (of )?experience\b": "age: a ceiling on experience can exclude older applicants",
    r"\b\d+\+?\s*years?'? (of )?experience\b": "age (indirect): a set number of years can exclude; say what they must be able to do",
    r"\b(he|him|his|himself)\b": "sex: use 'you' or 'they'",
    r"\b(she|her|hers|herself)\b": "sex: use 'you' or 'they'",
    r"\b(salesman|chairman|manpower|girl friday|waitress|handyman|foreman)\b": "sex: gendered job word",
    r"\b(aggressive|dominant|competitive spirit)\b": "sex (coded): tends to put women off applying; describe the result wanted",
    r"\bnative (english )?speakers?\b|\bmother tongue\b": "race or nationality: ask for the level of English the work needs",
    r"\b[a-z]+ (nationals?|citizens?) only\b|\bmust be an? [a-z]+ (national|citizen)\b|\bcitizens only\b": "race or nationality: describes the person, not the work",
    r"\blocals? only\b|\bmust be local\b": "race or nationality (indirect): say where the work is done instead",
    r"\b(able[- ]bodied|physically fit|excellent health|clean bill of health)\b": "disability: include only if the work needs it, and say what",
    r"\bclean driving licen[cs]e\b|\bown car\b": "disability (indirect): include only if driving is part of the job",
    r"\bno (family|childcare) commitments\b|\bavailable (at )?any ?time\b|\bavailable 24/?7\b": "sex or pregnancy and maternity (indirect): state the real hours instead",
    r"\bculture fit\b": "a vague test that can hide bias; name the behaviour you need",
    r"\b(attractive|good[- ]looking|presentable)\b": "appearance: describes the person, not the work",
    r"\b(single|married) (person|applicants?|candidates?)\b|\bno kids\b|\bwithout children\b": "family status: describes the person, not the work",
}
# Country-specific employment, tax or benefit terms keep a pack from travelling. The founder's adviser adds them.
JURISDICTION_TERMS = (r"\b(right to work|work permit|visa sponsorship|national insurance|auto-?enrol(?:ment)?|workplace pension|"
                      r"401\(?k\)?|superannuation|super guarantee|\bcpf\b|\bmpf\b|\bpaye\b|ir35|w-?2|1099|equality act|"
                      r"equal opportunit(?:y|ies) employer|\beeo\b|at-will|probation(?:ary)? period of \d+|statutory|minimum wage|"
                      r"living wage|holiday entitlement|annual leave entitlement)\b")
CLICHES = {
    r"\brock ?stars?\b|\bninjas?\b|\bgurus?\b|\bwizards?\b|\bunicorns?\b": "recruitment cliche (also male-coded)",
    r"\bfast[- ]paced\b": "recruitment cliche: say what the week holds",
    r"\bwork hard,? play hard\b": "recruitment cliche",
    r"\bpassionate\b|\bpassion for\b": "recruitment cliche: name the evidence you want instead",
    r"\bself[- ]starter\b|\bproactive\b|\bgo[- ]getter\b|\bhit the ground running\b": "recruitment cliche: say what they will own",
    r"\b(like )?a family\b": "recruitment cliche: blurs what the job is",
    r"\bwear many hats\b|\bteam player\b|\bdetail[- ]oriented\b|\bexcellent communication skills\b": "recruitment cliche: say how it is tested",
    r"\bcompetitive salary\b": "hides the pay: give the range",
}


def wording(text):
    probs, warns = [], []
    for pat, why in RISK_TERMS.items():
        for m in re.finditer(pat, text, re.I):
            frag = text[max(0, m.start() - 25):m.end() + 25].replace("\n", " ").strip()
            line = f"{why}: '{frag}'"
            (warns if why.startswith("age (indirect)") else probs).append(line)
    for pat, why in CLICHES.items():
        for m in re.finditer(pat, text, re.I):
            probs.append(f"{why}: '{text[max(0, m.start() - 20):m.end() + 20].strip()}'")
    return probs, warns


TEMPLATE = {
    "employment": "employee or contractor",
    "mission": "One line: why this role exists, in terms of the work it takes over",
    "outcomes": [{"outcome": "", "measure": "", "by": "day 90", "from_task": "", "hours_week": None}],
    "competencies": [{"competency": "", "for_outcome": 1}],
    "ad": {"headline": "", "about": "", "what_you_will_do": "", "what_you_will_own": [], "good_at_90_days": "",
           "pay": None, "pay_note": None, "hours": "", "location": "", "how_to_apply": ""},
    "interview": [{"outcome": 1, "question": "", "strong_answer": ""}],
    "work_sample": {"task": "", "time": "", "paid": "founder to decide"},
    "ninety_days": [{"weeks": "1 to 4", "focus": "", "decision_rights": ""},
                    {"weeks": "5 to 8", "focus": "", "decision_rights": ""},
                    {"weeks": "9 to 12", "focus": "", "decision_rights": ""}],
    "handover_test": "A task counts as handed over when they have produced it unaided and you have reviewed it, at least twice.",
    "one_to_one": [],
    "contractor_deliverables": [{"deliverable": "", "done_when": ""}],
}


def ad_text(rp):
    ad = rp.get("ad") or {}
    parts = [ad.get("headline"), ad.get("about"), ad.get("what_you_will_do"), " ".join(ad.get("what_you_will_own") or []),
             ad.get("good_at_90_days"), ad.get("hours"), ad.get("location"), ad.get("how_to_apply")]
    return "\n".join(str(p) for p in parts if p)


def check(rp, inputs):
    P, W = [], []
    if not isinstance(rp, dict):
        return ["the role pack must be one JSON object"], []
    tasks = [str(t.get("task", "")).lower() for t in (inputs.get("tasks") or []) if isinstance(t, dict)]
    emp = str(rp.get("employment", "")).lower()
    outs = rp.get("outcomes") or []
    if not 3 <= len(outs) <= 5:
        P.append(f"{len(outs)} outcomes; the scorecard needs three to five")
    for i, o in enumerate(outs, 1):
        txt = f"{o.get('outcome', '')} {o.get('measure', '')}"
        if not re.search(r"\d", txt):
            P.append(f"outcome {i} has no number to measure it by")
        if not str(o.get("by") or "").strip():
            P.append(f"outcome {i} has no date ('by day 90', 'by 31 March')")
        ft = str(o.get("from_task") or "").lower().strip()
        if not ft:
            P.append(f"outcome {i} does not say which task or hours it comes from")
        elif tasks and not any(ft in t or t in ft for t in tasks):
            P.append(f"outcome {i} comes from '{o.get('from_task')}', which is not one of the tasks the founder named")
    iv = rp.get("interview") or []
    mapped = {q.get("outcome") for q in iv}
    for i in range(1, len(outs) + 1):
        if i not in mapped:
            P.append(f"outcome {i} has no interview question")
    for j, q in enumerate(iv, 1):
        if q.get("outcome") not in range(1, len(outs) + 1):
            P.append(f"interview question {j} does not map to an outcome")
        if not str(q.get("strong_answer") or "").strip():
            P.append(f"interview question {j} has no note on what a strong answer includes")
    ws = rp.get("work_sample") or {}
    if not ws.get("task"):
        W.append("no work sample task; a short one tests the outcomes better than a conversation")
    elif str(ws.get("paid", "")).lower() not in ("paid", "unpaid", "founder to decide"):
        W.append("say whether the work sample is paid, unpaid or the founder's decision")
    ad = rp.get("ad") or {}
    if not ad.get("pay") and not ad.get("pay_note"):
        P.append("the ad has no pay range and no note that leaving it out is the founder's choice")
    for k in ("what_you_will_do", "good_at_90_days", "hours", "location", "how_to_apply"):
        if not ad.get(k):
            P.append(f"the ad is missing '{k.replace('_', ' ')}'")
    stages = rp.get("ninety_days") or []
    if emp != "contractor":
        if len(stages) != 3:
            P.append(f"the first 90 days has {len(stages)} stages; it needs three (weeks 1 to 4, 5 to 8, 9 to 12)")
        for s in stages:
            if not str(s.get("decision_rights") or "").strip():
                P.append(f"weeks {s.get('weeks')} have no decision rights")
    else:
        dl = rp.get("contractor_deliverables") or []
        if not dl or any(not d.get("done_when") for d in dl):
            P.append("a contractor brief needs each deliverable with its definition of done")
    if not rp.get("one_to_one") and emp != "contractor":
        P.append("no one-to-one agenda")
    wp, ww = wording(ad_text(rp))
    P += [f"ad wording: {x}" for x in wp]
    W += [f"ad wording: {x}" for x in ww]
    everything = json.dumps(rp, ensure_ascii=False)
    for m in re.finditer(JURISDICTION_TERMS, everything, re.I):
        P.append(f"jurisdiction-specific term '{m.group(0)}': keep the pack neutral; the founder's adviser adds what applies where they hire")
    cp, cw, _ = copy_check(everything)
    P += [f"copy: {x}" for x in cp]
    return P, W


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("template", "check"):
        print(__doc__)
        return 2
    if sys.argv[1] == "template":
        print(json.dumps(TEMPLATE, indent=2))
        return 0
    if len(sys.argv) < 3:
        print("STOP: give the role pack file: python3 scripts/role_pack.py check <rolepack.json> --inputs <inputs.json>. Nothing was checked.")
        return 2
    p = Path(sys.argv[2])
    inp = {}
    if "--inputs" in sys.argv:
        ip = Path(sys.argv[sys.argv.index("--inputs") + 1])
        if not ip.exists():
            print(f"STOP: there is no inputs file at {ip}. Nothing was checked.")
            return 2
        inp = json.loads(ip.read_text(encoding="utf-8"))
    if not p.exists():
        print(f"STOP: there is no role pack file at {p}. Nothing was checked.")
        return 2
    try:
        rp = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"STOP: the role pack is not valid JSON ({e.msg} at line {e.lineno}). Nothing was checked.")
        return 2
    P, W = check(rp, inp)
    for x in P:
        print("PROBLEM:", x)
    for x in W:
        print("WARN:", x)
    print(f"{len(P)} problems, {len(W)} warnings")
    return 1 if P else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001
        print(f"STOP: the role pack could not be checked ({type(e).__name__}: {e}). Nothing was checked.")
        sys.exit(2)
