#!/usr/bin/env python3
"""Turn the reviewer's verdicts on one call into the score, then into the review the founder reads.

Usage:
  python3 scripts/score_call.py score <verdicts.json> --measure <measure.json> --out <results.json>
                                [--history <previous.json>]
        checks every verdict against the transcript and the method, applies the failure caps and the
        weights, judges each objection against the six steps, grades the next step, checks stated and
        real loss reasons, and, with --history (from memory.py read), runs the trend check
  python3 scripts/score_call.py score <verdicts.json> --recall --out <results.json> [--history ...]
        the same for a recall review (no transcript; nothing is quoted as verbatim)
  python3 scripts/score_call.py render <results.json> --out <review.md>
        writes the review in the fixed order the founder reads it

The verdicts shape is in references/verdicts-schema.md.

Weights (working defaults): low 1, standard 2, high 3. The overall score is the weighted mean of the five
dimension scores after caps, times ten, rounded down (never up). Caps: pitched before pain caps Discovery
and Gap Build at 4; control handed over and not taken back caps Intro and Frame at 4; no question about what
the problem costs followed by a stall caps Cost of Inaction at 1; folding on an objection caps Objection
Handling at 3. All four are kept in WEIGHTS and CAPS below, in one place.

Exit 0: written. Exit 1: PROBLEM lines; nothing was written; fix the verdicts and run again.
Exit 2: STOP; the input is missing or the wrong shape; do what the STOP line says.
Standard library only. No network calls.
"""
import argparse
import json
import os
import re
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_review as CR  # noqa: E402

# ---------------------------------------------------------------- working defaults, in one place (method sections 3 and 4)
METHOD_VERSION = "2026-10-21"
WEIGHTS = {"low": 1, "standard": 2, "high": 3}
DIMENSIONS = [  # name, weight, the stages it reads (by number in the five standard stages)
    ("Intro and Frame", "low", "1 Opening and Frame"),
    ("Discovery and Gap Build", "high", "2 Discovery"),
    ("Cost of Inaction", "high", "2 Discovery; 3 Diagnosis"),
    ("Objection Handling", "high", "wherever an objection came up"),
    ("Close Attempt", "standard", "4 Pitch; 5 Close"),
]
DIM_NAMES = [d for d, _w, _s in DIMENSIONS]
CAPS = {
    "pitched_before_pain": ("Discovery and Gap Build", 4, "the pitch started before the prospect had said what was wrong"),
    "frame_no_control": ("Intro and Frame", 4, "control was handed to the prospect at the start and never taken back"),
    "coi_missing_then_stall": ("Cost of Inaction", 1, "nobody asked what the problem costs, and the prospect stalled"),
    "folded": ("Objection Handling", 3, "the seller folded on an objection and handed the next move over"),
}
RUNGS = {  # method section 3: each dimension is scored by naming the rung the call reached; the score comes from the rung
    "Intro and Frame": [
        ("prospect_led", 1, "no opening from the seller: the prospect ran the call from the first minute"),
        ("straight_to_pitch", 2, "the seller went straight into presenting (portfolio, slides, past work) with no length, agenda or agreed ending"),
        ("handed_over", 3, "the seller asked the prospect where to start or offered a way out, and set no length or agreed ending"),
        ("not_recalled", 4, "recall only: the recall says nothing at all about how the call opened; if it says what came first (the portfolio, a presentation, past projects), that is the evidence and the rung is straight_to_pitch"),
        ("one_element", 4, "one of length, agenda or how the call ends was set; nothing agreed"),
        ("two_elements", 5, "two of length, agenda and how the call ends were set; the prospect was not asked to agree"),
        ("all_unagreed", 6, "length, agenda and how the call ends all set; the prospect was not asked to agree"),
        ("agreed", 8, "length, agenda and how the call ends set, and the prospect agreed"),
        ("agreed_deciders", 9, "as agreed, and who else decides was checked at the start"),
        ("agreed_own_items", 10, "as agreed_deciders, and the prospect added their own item to the agenda"),
    ],
    "Discovery and Gap Build": [
        ("no_discovery", 1, "nobody asked about the problem and the prospect never named one"),
        ("seller_named_problem", 2, "the seller described the problem and the prospect only agreed"),
        ("pitched_then_surface", 3, "the pitch came before the prospect said what was wrong, and later questions stopped at the first answer"),
        ("pain_volunteered", 4, "the prospect named the pain in their own words, but unasked or during the pitch, and it was not followed up or agreed"),
        ("one_layer", 5, "asked, and answered in the prospect's words, one layer deep; what it affects was not explored"),
        ("layers_no_gap", 6, "several layers in the prospect's words (problem, cause, what it affects, the goal), but the seller never said the situation back and had it agreed"),
        ("layers_one_open", 7, "several layers in their words, and the seller said the situation back and the prospect agreed it; at least one of the gap as a target, what they expect to spend, or how the decision gets made left unasked"),
        ("gap_and_decision", 8, "several layers, the situation and the gap said back and agreed, and what they expect to spend and how the decision gets made both asked"),
        ("gap_decision_tried", 9, "as gap_and_decision, and what was tried before and why it did not work"),
        ("complete", 10, "all of it in the prospect's words before any solution, the gap agreed, nothing material left unasked"),
    ],
    "Cost of Inaction": [
        ("never_raised", 1, "nobody asked what the problem costs"),
        ("costs_named_not_built", 2, "the prospect mentioned what it costs unprompted, and nobody turned it into a number"),
        ("seller_supplied", 3, "asked, but the seller supplied or answered the number, or the prospect doubted it"),
        ("asked_dropped", 4, "asked once; a vague answer was accepted and the question dropped"),
        ("in_words", 5, "the prospect described the cost in their own words; it was never added up"),
        ("number_not_agreed", 6, "the prospect built a number, but it was not said back and agreed, or covered only today and not if nothing changes"),
        ("number_agreed", 7, "the prospect built the number and agreed it, today and if nothing changes"),
        ("number_why_now", 8, "as number_agreed, and why this time would be different from the last stretch was asked"),
        ("complete", 10, "as number_why_now, the silence held after it, and the prospect tied it to their own deadline"),
    ],
    "Objection Handling": [
        ("none_not_invited", 5, "no objection came up, and the seller never asked what might stop them"),
        ("none_invited", 8, "no objection came up after the seller asked what might stop them"),
        ("argued_or_ignored", 2, "no objection got past an argument or evidence: argued, ignored or folded"),
        ("acknowledged", 3, "at least one objection was agreed fair, isolated or questioned, but none was partly handled"),
        ("two_steps_each", 4, "every objection got two or more of the six steps, none folded, none partly handled"),
        ("partly", 5, "at least one objection partly handled (isolated, agreed fair and one more step)"),
        ("partly_shift_checked", 7, "every objection at least partly handled, and the shift checked on each"),
        ("one_through", 8, "one objection handled all the way through, the rest at least partly"),
        ("all_through", 10, "every objection taken through all six steps"),
    ],
    "Close Attempt": [
        ("no_price", 1, "no price was said"),
        ("price_answered_or_cut", 2, "the price came only as a bare answer to the prospect's question, with no pitch tied to what they said and no ask (a term or price cut after it is scored in Objection Handling, not here)"),
        ("price_no_ask", 3, "the price said once and plainly, but no silence held and no clear ask, and the prospect left holding the next step"),
        ("price_ask_prospect_holds", 4, "the price said and a clear ask made or the silence held, but the prospect still left holding the next step"),
        ("booked_no_ask", 5, "a decision call booked live with a date, but no ask for the decision itself"),
        ("booked_silence", 6, "the price once after the cost, silence held, a decision call booked with a date and agenda; no ask for the prospect's own yes"),
        ("asked_and_booked", 8, "pitch, price, silence and ask in order, and a decision call with a date and agenda where someone else must decide"),
        ("closed", 10, "pitch, price, silence and ask, and closed on the call"),
    ],
}
RUNG_SCORE = {d: {k: n for k, n, _t in rs} for d, rs in RUNGS.items()}
RUNG_TEXT = {d: {k: t for k, _n, t in rs} for d, rs in RUNGS.items()}
WEAK_AT = 3          # a dimension at or under this is weak, for the trend check
TREND_WINDOW = 3     # the last n reviews of the same seller, this one included
TREND_HITS = 2       # weak in this many of them is a structure problem
DEFAULT_STAGES = ["Opening and Frame", "Discovery", "Diagnosis", "Pitch", "Close"]
STAGE_POINTS = {"done": 2, "partial": 1, "missed": 0}
LOOP = ["isolated", "belief_named", "validated", "cost_exposed", "reframed", "shift_confirmed"]
LOOP_WORDS = {"isolated": "isolated it", "belief_named": "named the belief", "validated": "agreed it was fair",
              "cost_exposed": "showed what keeping the belief costs", "reframed": "gave evidence",
              "shift_confirmed": "checked it had shifted"}
NEXT_STEP = {"closed": "Closed on the call", "decision_call_booked": "Decision call booked live",
             "prospect_in_control": "Prospect left in control of the next step"}
LOSS_REASONS = ["Never reached or no-show", "Disqualified late", "No offer made", "Price or value belief unresolved",
                "Partner or authority unresolved", "Timing or parked with a date", "Trust or burned",
                "Chose DIY or competitor", "Ghosted after offer"]
OUTCOMES = {"won", "lost", "open", "not a fit"}
CALL_TYPES = {"first call", "second call", "proposal review"}
DATE_STYLES = {"day month year", "month day year", "year month day"}  # the founder's, read from their own writing
CONSENT_LINE = "Check the consent rules for recording calls where you and the prospect are."
QUOTE_KEYS = {"quote"}


class Stop(Exception):
    pass


def load(path, what):
    if not path or not os.path.exists(path):
        raise Stop(f"there is no {what} at {path}")
    try:
        return json.load(open(path, encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise Stop(f"{path} is not valid JSON ({e.msg} at line {e.lineno}); fix the file and run again")


def need_dict(v, where):
    if not isinstance(v, dict):
        raise Stop(f"{where} must be an object with named fields; see references/verdicts-schema.md")
    return v


def need_list(v, where):
    if v is None:
        return []
    if not isinstance(v, list):
        raise Stop(f"{where} must be a list; see references/verdicts-schema.md")
    return v


def text_fields(obj, path=""):
    """Every string the reviewer wrote (not a transcript quote), with where it sits."""
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in QUOTE_KEYS or k.endswith("_quote") or k in ("at", "appeared_at", "created_at", "grade", "verdict", "flag",
                                                                  "kind", "date"):
                continue
            out += text_fields(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out += text_fields(v, f"{path}[{i}]")
    elif isinstance(obj, str):
        out.append((path, obj))
    return out


def handling(o):
    loop = o.get("loop") or {}
    done = [k for k in LOOP if loop.get(k)]
    missing = [k for k in LOOP if not loop.get(k)]
    if o.get("folded"):
        return "folded", done, missing
    if len(done) == len(LOOP):
        return "handled all the way through", done, missing
    if loop.get("isolated") and loop.get("validated") and len(done) >= 3:
        return "partly handled", done, missing
    return "not handled", done, missing


def objection_rung(objs):
    """The Objection Handling rung the six-step record supports (method section 3), or None with no objections."""
    objs = [o for o in objs if isinstance(o, dict)]
    if not objs:
        return None
    hs = [handling(o) for o in objs]
    level = [h[0] for h in hs]
    through = [x == "handled all the way through" for x in level]
    partly = [x in ("partly handled", "handled all the way through") for x in level]
    if all(through):
        return "all_through"
    if any(through) and all(partly):
        return "one_through"
    if all(partly) and all((o.get("loop") or {}).get("shift_confirmed") for o in objs):
        return "partly_shift_checked"
    if any(partly):
        return "partly"
    if all(len(h[1]) >= 2 for h in hs) and not any(o.get("folded") for o in objs):
        return "two_steps_each"
    if any(set(h[1]) - {"reframed"} for h in hs):
        return "acknowledged"
    return "argued_or_ignored"


def cmd_score(a):
    v = need_dict(load(a.verdicts, "verdicts file"), "the verdicts file")
    recall = a.recall or v.get("mode") == "recall"
    measure = None if recall else CR.load_measure(a.measure) if a.measure else None
    if not recall and measure is None:
        raise Stop("a transcript review needs --measure (the file measure_call.py wrote); for a recall review pass --recall")
    hist = load(a.history, "history file") if a.history else {}
    P, W = [], []

    # ------------------------------------------------ shape
    if v.get("call_date") and v.get("date_style") not in DATE_STYLES:
        P.append("'date_style' must be the founder's own: one of " + ", ".join(sorted(DATE_STYLES)) +
                 " (read it from how they write dates; if nothing shows it, state the one you used in 'defaults')")
    for k in ("seller", "call_type", "outcome", "dimensions", "coaching", "drill", "next_step", "headline", "what_happened"):
        if v.get(k) in (None, "", [], {}):
            P.append(f"'{k}' is missing")
    dims = need_dict(v.get("dimensions") or {}, "dimensions")
    flags = need_list(v.get("flags"), "flags")
    objs = need_list(v.get("objections"), "objections")
    stages = need_list(v.get("stages"), "stages")
    coaching = need_list(v.get("coaching"), "coaching")
    cps = need_list(v.get("creation_points"), "creation_points")
    reds = need_list(v.get("red_lines"), "red_lines")
    dismissed = need_list(v.get("dismissed_flags"), "dismissed_flags")
    ns = need_dict(v.get("next_step") or {}, "next_step")
    drill = need_dict(v.get("drill") or {}, "drill")
    if v.get("call_type") and v["call_type"] not in CALL_TYPES:
        P.append(f"call_type must be one of {sorted(CALL_TYPES)}")
    if v.get("outcome") and v["outcome"] not in OUTCOMES:
        P.append(f"outcome must be one of {sorted(OUTCOMES)}")

    # ------------------------------------------------ positions and quotes against the transcript
    def cite(where, pos, quote=None, role=None):
        if recall:
            if pos not in (None, "", "recall"):
                P.append(f"{where}: a recall review cites no position ('{pos}'); describe the moment instead")
            return
        if not pos:
            P.append(f"{where}: no position; every finding cites one")
            return
        i = CR.find_turn(measure, pos)
        if i is None:
            P.append(f"{where}: position {pos} is not the start of any turn; copy it from the measure output")
            return
        if quote is not None:
            if not str(quote).strip():
                P.append(f"{where}: no quote")
                return
            ok, why = CR.quote_ok(measure, pos, quote)
            if not ok:
                P.append(f"{where}: quote \"{str(quote)[:50]}\" {why}")
            elif role and measure["turns"][i]["role"] != role:
                P.append(f"{where}: the quote at {pos} is the {measure['turns'][i]['role']}'s, not the {role}'s")

    scores = {}
    for d in DIM_NAMES:
        x = dims.get(d)
        if not isinstance(x, dict):
            P.append(f"dimension '{d}' is missing")
            continue
        rung = x.get("rung")
        if rung not in RUNG_SCORE[d]:
            P.append(f"dimension '{d}' needs a 'rung', the highest step the call reached: " +
                     "; ".join(f"{k} ({n}): {t}" for k, n, t in RUNGS[d]))
            continue
        if rung == "not_recalled" and not recall:
            P.append(f"dimension '{d}': rung not_recalled is for a recall review only; read the opening in the transcript")
        if x.get("score") is not None and x.get("score") != RUNG_SCORE[d][rung]:
            P.append(f"dimension '{d}': score {x.get('score')} does not match rung {rung} ({RUNG_SCORE[d][rung]}); "
                     "the rung sets the score, so pick the rung the evidence shows and leave the score out")
            continue
        x["score"] = RUNG_SCORE[d][rung]
        scores[d] = x["score"]
        if not (x.get("why") or "").strip():
            P.append(f"dimension '{d}' needs a 'why' line")
        cite(f"dimension '{d}'", x.get("at"), x.get("quote"))

    # ------------------------------------------------ flags and caps
    keys = [f.get("flag") for f in flags if isinstance(f, dict)]
    for o in objs:
        if isinstance(o, dict) and o.get("folded") and "folded" not in keys:
            flags.append({"flag": "folded", "at": o.get("at"), "note": "folded on the objection here"})
            keys.append("folded")
    capped = []
    for f in flags:
        k = f.get("flag")
        if k not in CAPS:
            P.append(f"unknown flag '{k}'; use one of {', '.join(CAPS)}")
            continue
        cite(f"flag {k}", f.get("at"), f.get("quote"))
        dim, cap, why = CAPS[k]
        if dim in scores and scores[dim] > cap:
            capped.append({"flag": k, "dimension": dim, "from": scores[dim], "to": cap, "at": f.get("at"), "why": why})
            scores[dim] = cap
    if "coi_missing_then_stall" in keys and v.get("coi_at"):
        P.append("flag coi_missing_then_stall says nobody asked what the problem costs, but coi_at is set; one of them is wrong")
    if measure:
        for c in measure.get("candidates", []):
            if c["flag"] in CAPS and c["flag"] not in keys and not any(
                    isinstance(d, dict) and d.get("flag") == c["flag"] for d in dismissed):
                P.append(f"measure found a candidate {c['flag']} at {c['at']}; confirm it in 'flags' or dismiss it in "
                         "'dismissed_flags' with the reason")
    for d in dismissed:
        if not (isinstance(d, dict) and (d.get("why") or "").strip()):
            P.append("each dismissed flag needs a 'why'")

    # ------------------------------------------------ the cost question, the price and the red line
    coi_at = v.get("coi_at")
    om = v.get("offer_made") or {}
    if not recall:
        if coi_at:
            cite("coi_at", coi_at)
        if om.get("made"):
            cite("offer_made", om.get("at"))
    price_first = False
    if om.get("made"):
        if not coi_at:
            price_first = True
        elif not recall:
            i, j = CR.find_turn(measure, om.get("at")), CR.find_turn(measure, coi_at)
            price_first = i is not None and j is not None and i < j
        else:
            price_first = bool(v.get("price_before_cost"))
    if price_first and not any(r.get("kind") == "price_before_cost" for r in reds if isinstance(r, dict)):
        reds.insert(0, {"kind": "price_before_cost", "at": om.get("at"),
                        "note": "The price came before anyone asked what the problem costs. The fix is the order of the call, not the price."})
    for r in reds:
        if not isinstance(r, dict) or r.get("kind") not in ("price_before_cost", "deadline", "promise", "price_asked_early", "untrusted"):
            P.append("each red line needs kind: price_before_cost, deadline, promise, price_asked_early or untrusted")
            continue
        if r.get("kind") == "untrusted" and r.get("at") == "header":
            continue  # a line above the first speaker turn: quoted as found, no position to cite
        if r.get("kind") != "price_before_cost":
            cite(f"red line {r.get('kind')}", r.get("at"), r.get("quote"))
    if measure:
        for key, kind in (("deadlines", "deadline"), ("promises", "promise"), ("untrusted", "untrusted")):
            for c in measure.get(key, []):
                if c.get("at") == "header":
                    continue
                if not any(isinstance(r, dict) and r.get("kind") == kind and str(r.get("at")) == str(c["at"]) for r in reds) and \
                        not any(isinstance(d, dict) and d.get("flag") == kind and str(d.get("at")) == str(c["at"]) for d in dismissed):
                    P.append(f"measure found a {kind} line at {c['at']}; list it in 'red_lines' or dismiss it in 'dismissed_flags' "
                             "with the reason")

    # ------------------------------------------------ stages
    stage_rows = []
    for s in stages:
        if not isinstance(s, dict) or s.get("verdict") not in STAGE_POINTS:
            P.append("each stage needs a verdict: done, partial or missed")
            continue
        if s["verdict"] != "missed":
            cite(f"stage {s.get('name')}", s.get("at"), s.get("quote"))
        if s["verdict"] in ("partial", "missed") and not re.search(r"\S.{6,}", s.get("say_instead") or ""):
            P.append(f"stage '{s.get('name')}' is {s['verdict']}: give say_instead, the words to use next time")
        stage_rows.append(s)
    if not stage_rows:
        P.append("no stages: give a verdict for each of the founder's stages, or the five standard ones")

    # ------------------------------------------------ objections
    obj_rows = []
    for idx, o in enumerate(objs, 1):
        if not isinstance(o, dict):
            P.append(f"objection {idx} must be an object")
            continue
        cite(f"objection {idx}", o.get("at"), o.get("quote"), role="prospect")
        if not (o.get("belief") or "").strip():
            P.append(f"objection {idx}: name the belief underneath it")
        verdict, done, missing = handling(o)
        if missing and not re.search(r"\S.{6,}", o.get("say_instead") or ""):
            P.append(f"objection {idx} missed {', '.join(LOOP_WORDS[m] for m in missing)}: give say_instead")
        obj_rows.append({**o, "handling": verdict, "done": [LOOP_WORDS[k] for k in done],
                         "missing": [LOOP_WORDS[k] for k in missing]})

    # ------------------------------------------------ next step
    g = ns.get("grade")
    if g not in NEXT_STEP:
        P.append("next_step.grade must be closed, decision_call_booked or prospect_in_control")
        ns_verdict = "fail"
    elif g == "decision_call_booked" and not (ns.get("date") and ns.get("agenda")):
        ns_verdict = "partial"
    else:
        ns_verdict = "fail" if g == "prospect_in_control" else "pass"
    for k, ex in enumerate(need_list(ns.get("exchange"), "next_step.exchange"), 1):
        if isinstance(ex, dict):
            cite(f"closing exchange line {k}", ex.get("at"), ex.get("quote"))
    if not recall and not ns.get("exchange"):
        P.append("next_step.exchange: quote the closing exchange")
    rung_of = {d: (dims.get(d) or {}).get("rung") for d in DIM_NAMES if isinstance(dims.get(d), dict)}
    cr = rung_of.get("Close Attempt")
    if cr in RUNG_SCORE["Close Attempt"]:
        made = bool(om.get("made"))
        if (cr == "no_price") == made:
            P.append(f"Close Attempt rung {cr} does not match offer_made.made ({made}): no_price is for a call where no price was said, and only then")
        allowed = {"prospect_in_control": {"no_price", "price_answered_or_cut", "price_no_ask", "price_ask_prospect_holds"},
                   "decision_call_booked": {"booked_no_ask", "booked_silence", "asked_and_booked"},
                   "closed": {"closed"}}.get(g, set())
        if g in NEXT_STEP and cr not in allowed:
            P.append(f"Close Attempt rung {cr} does not fit the next step ({g}); use one of: {', '.join(sorted(allowed))}")
        if cr in ("booked_silence", "asked_and_booked") and not (ns.get("date") and ns.get("agenda")):
            P.append(f"Close Attempt rung {cr} needs a decision call with a date and an agenda in next_step; without both use booked_no_ask")
    cor = rung_of.get("Cost of Inaction")
    if cor in RUNG_SCORE["Cost of Inaction"]:
        if coi_at and cor in ("never_raised", "costs_named_not_built"):
            P.append(f"Cost of Inaction rung {cor} says nobody asked what the problem costs, but coi_at is set; one of them is wrong")
        if not recall and not coi_at and cor not in ("never_raised", "costs_named_not_built"):
            P.append(f"Cost of Inaction rung {cor} needs coi_at, the first question about what the problem costs")
    orr = rung_of.get("Objection Handling")
    if orr in RUNG_SCORE["Objection Handling"]:
        want = objection_rung(objs)
        if want is None and not orr.startswith("none_"):
            P.append(f"Objection Handling rung {orr}: no objection is listed, so use none_not_invited or none_invited")
        elif want is not None and orr != want:
            P.append(f"Objection Handling rung {orr} does not match the six-step record of the objections listed, which reads "
                     f"{want} ({RUNG_TEXT['Objection Handling'][want]}); fix the loop record or the rung")
    if g == "prospect_in_control" and scores.get("Close Attempt", 0) > 4:
        P.append("the prospect was left in control of the next step but Close Attempt is above 4; score the structure, not the warmth")

    # ------------------------------------------------ creation points: every failure traced
    def order_of(pos):
        if recall:
            return None
        return CR.find_turn(measure, pos)

    for k, c in enumerate(cps, 1):
        if not isinstance(c, dict):
            P.append(f"creation point {k} must be an object")
            continue
        for f_ in ("failure", "appeared_at", "created_at", "what_happened", "for"):
            if not c.get(f_):
                P.append(f"creation point {k} needs '{f_}'")
        if not recall:
            cite(f"creation point {k} (appeared)", c.get("appeared_at"), c.get("appeared_quote"))
            cite(f"creation point {k} (created)", c.get("created_at"), c.get("created_quote"))
            i, j = order_of(c.get("appeared_at")), order_of(c.get("created_at"))
            if i is not None and j is not None and j > i:
                P.append(f"creation point {k}: created at {c.get('created_at')} is after it appeared at {c.get('appeared_at')}")
    traced = {str(c.get("for")) for c in cps if isinstance(c, dict)}
    for f in flags:
        if f.get("flag") in CAPS and f.get("flag") not in traced:
            P.append(f"failure '{f.get('flag')}' has no creation point (give one with \"for\": \"{f.get('flag')}\")")
    if ns_verdict == "fail" and "next_step" not in traced:
        P.append("the next step failed and has no creation point (give one with \"for\": \"next_step\")")

    # ------------------------------------------------ coaching and the drill
    if len(coaching) != 2:
        P.append(f"exactly two coaching points, found {len(coaching)}; the rest belongs in the scorecard")
    for k, c in enumerate(coaching, 1):
        if not isinstance(c, dict):
            P.append(f"coaching point {k} must be an object")
            continue
        for f_ in ("title", "cause_effect", "fix", "say"):
            if not (c.get(f_) or "").strip():
                P.append(f"coaching point {k} needs '{f_}'")
        if not recall:
            cite(f"coaching point {k}", c.get("at"), c.get("quote"))
        elif not (c.get("described") or "").strip():
            P.append(f"coaching point {k}: describe the moment (recall)")
        if c.get("cause_effect") and not re.match(r"^\s*because\b", c["cause_effect"], re.I):
            P.append(f"coaching point {k}: cause_effect starts 'Because ...' and names what the prospect did next")
        if c.get("say") and len(c["say"].strip().strip('"')) < 8:
            P.append(f"coaching point {k}: 'say' is the full line to say next time")
        scope = " ".join(str(c.get(x) or "") for x in ("title", "cause_effect", "fix", "say"))
        for w in CR.FRAMEWORK_WORDS:
            if re.search(w, scope, re.I):
                P.append(f"coaching point {k} names a framework at the seller; describe the behaviour instead")
                break
    for f_ in ("behaviour", "reps", "by"):
        if not (drill.get(f_) or "").strip():
            P.append(f"the drill needs '{f_}'")
    dtext = " ".join(str(drill.get(x) or "") for x in ("behaviour", "reps", "by"))
    if re.search(r"\b(read|watch|study|course|book|video|article|podcast|research)\b", dtext, re.I):
        P.append("the drill must be doable before the next call with nothing else to read or watch")
    if drill.get("dimension") and drill["dimension"] not in DIM_NAMES:
        P.append(f"drill.dimension must be one of {DIM_NAMES}")

    # ------------------------------------------------ stated and real reasons
    out = v.get("outcome")
    rr = v.get("real_reason") or {}
    if out == "lost":
        if rr.get("reason") not in LOSS_REASONS:
            P.append("a lost deal needs real_reason.reason, one of: " + "; ".join(LOSS_REASONS))
        if not (v.get("stated_reason") or "").strip():
            P.append("a lost deal needs stated_reason: what the prospect said, or 'not given'")
        if rr.get("reason") == "Timing or parked with a date" and scores.get("Cost of Inaction", 10) <= WEAK_AT:
            P.append("the real reason is given as timing, but nobody made the cost of waiting real (Cost of Inaction "
                     f"{scores.get('Cost of Inaction')}); timing is the stated reason here, not the real one")
        if not recall:
            cite("real_reason", rr.get("at"))
    elif rr.get("reason") and rr["reason"] not in LOSS_REASONS:
        P.append("real_reason.reason must be one of the nine loss reasons")
    wb = v.get("way_back_in")
    if out == "open" and g == "prospect_in_control" and not (isinstance(wb, dict) and len((wb.get("message") or "").split()) >= 12):
        P.append("an open deal needs way_back_in.message: the short message the seller can send today to get the next step "
                 "back, built from this call's details, promising nothing the call did not hold (method section 9)")
    if isinstance(wb, dict) and wb.get("message") and len(wb["message"].split()) > 120:
        P.append("way_back_in.message: keep it under 120 words; one ask, two named days")

    # ------------------------------------------------ a recall review cites no time anywhere
    if recall:
        def times(o, path=""):
            if isinstance(o, dict):
                for k, x in o.items():
                    if k in ("at", "appeared_at", "created_at") and isinstance(x, str) and re.search(r"\d{1,2}:\d{2}", x):
                        P.append(f"{path}.{k}: a recall review cites no position ('{x}'); describe the moment instead")
                    else:
                        times(x, f"{path}.{k}" if path else k)
            elif isinstance(o, list):
                for i, x in enumerate(o):
                    times(x, f"{path}[{i}]")
            elif isinstance(o, str) and re.search(r"\b\d{1,2}:\d{2}\b", o):
                P.append(f"{path}: a recall review cites no time ('{o[:40]}'); describe the moment instead")
            elif isinstance(o, str) and re.search(r"\b\d+\s*(?:min|mins|minutes)\s+(?:in|into)\b|\bat\s+(?:about\s+|around\s+|roughly\s+)?(?:minute\s+\d+|\d+\s*(?:min|mins|minutes))\b", o, re.I):
                P.append(f"{path}: a recall review places no moment by the clock ('{o[:50]}'); say what came before it "
                         "instead ('after the price', 'near the end')")
        times({k: x for k, x in v.items() if k not in ("call_date", "date_style", "length_minutes", "defaults")})

    for where, s_ in text_fields(v):
        for hit in CR.cut_money(s_):
            P.append(f"{where}: an amount reads '{hit}' with its first digits and symbol missing; a shell probably ate '$' "
                     "and a digit; write the verdicts with the file tool or a quoted heredoc")
    # ------------------------------------------------ Say lines print inside one pair of quotation marks
    for where, s_ in text_fields(v):
        if re.search(r"(^|\.)(say|say_instead)$", where) and re.search(r'["\u201c\u201d]', s_.strip().strip('"\u201c\u201d')):
            P.append(f"{where}: the line is printed inside quotation marks, so it holds none of its own; quote the prospect "
                     "with single quotation marks and put a direction such as [Stop. Count to five.] in square brackets")

    # ------------------------------------------------ names, blame, held-out wording in what the reviewer wrote
    pros = CR.prospects_of(measure) if measure else {}
    if recall:
        pn = (v.get("prospect_name") or "").strip()
        if not pn:
            P.append("recall: give 'prospect_name', the name the founder used for the prospect ('not given' if none), so the "
                     "check can make sure it never appears; it is never printed or saved")
        elif pn.lower() != "not given":
            pros = {pn: v.get("prospect") or "the prospect"}
    third = CR.third_parties_of(measure, v)
    hidden = ("seller", "business", "seller_name", "prospect_name", "third_parties")
    for where, s in text_fields({k: v[k] for k in v if k not in hidden}):
        for name in pros:
            if re.match(r"^(speaker|participant|unknown|guest|caller)\b", name, re.I):
                continue
            for part in [name] + [x for x in name.split() if len(x) > 2]:
                if re.search(r"\b" + re.escape(part) + r"\b", s):
                    P.append(f"{where}: the prospect's name '{part}' appears; use initials ({pros[name]})")
                    break
        if not re.search(r"(^|\.)(say|say_instead|described_quote|message)$", where):
            for n in third:
                if re.search(r"\b" + re.escape(n) + r"\b", s):
                    P.append(f"{where}: '{n}' is someone the prospect named; outside quotes and Say lines, refer to them by role "
                             "(her business partner, their bookkeeper)")
        bp, _bw = CR.copy_check(s)
        for b in bp:
            P.append(f"{where}: {b}")

    # ------------------------------------------------ the arithmetic
    if P:
        return P, None
    total_w = sum(WEIGHTS[w] for _d, w, _s in DIMENSIONS)
    weighted = sum(WEIGHTS[w] * scores[d] for d, w, _s in DIMENSIONS) / total_w
    overall = int(weighted * 10 + 1e-9)  # rounded down, never up
    order = sorted(DIMENSIONS, key=lambda d: (scores[d[0]], -WEIGHTS[d[1]]))
    weakest = order[0][0]

    # ------------------------------------------------ trend from memory
    seller = v.get("seller")
    trend = []
    this_call = call_key(v, measure)
    past = [h for h in (hist.get("history") or []) if (h.get("seller") or "").lower() == (seller or "").lower()
            and not same_call(h, this_call)]   # a re-review of this same call is not a second data point
    window = past[-(TREND_WINDOW - 1):]
    for d in DIM_NAMES:
        hits = sum(1 for h in window if isinstance((h.get("scores") or {}).get(d), (int, float)) and h["scores"][d] <= WEAK_AT)
        hits += 1 if scores[d] <= WEAK_AT else 0
        if hits >= TREND_HITS:
            trend.append({"dimension": d, "hits": hits, "of": len(window) + 1})
    if trend and drill.get("dimension") not in [t["dimension"] for t in trend]:
        return [f"{trend[0]['dimension']} has been weak in {trend[0]['hits']} of {seller}'s last {trend[0]['of']} reviews: "
                f"that is a structure problem, so the drill must work on it (set drill.dimension to '{trend[0]['dimension']}')"], None

    # ------------------------------------------------ confidence
    if recall:
        confidence, cwhy = "low", "built from your recall, with no recording to check positions or exact words"
    elif not measure.get("has_timestamps"):
        confidence, cwhy = "medium", "the transcript has no timestamps, so positions are turn numbers"
    elif v.get("structure") in (None, "default"):
        confidence, cwhy = "medium", "scored against the five standard stages, not your own call structure"
    else:
        confidence, cwhy = "high", "a full transcript with timestamps, scored against your own stages"

    stage_counts = {k: sum(1 for s in stage_rows if s["verdict"] == k) for k in STAGE_POINTS}
    res = {
        "method_version": METHOD_VERSION, "mode": "recall" if recall else "transcript",
        "overall": overall, "weighted_mean": round(weighted, 4), "weakest": weakest,
        "scores": scores, "raw_scores": {d: int(dims[d]["score"]) for d in DIM_NAMES}, "rungs": {d: dims[d].get("rung") for d in DIM_NAMES}, "capped": capped,
        "weights": {d: w for d, w, _s in DIMENSIONS}, "stage_points": sum(STAGE_POINTS[s["verdict"]] for s in stage_rows),
        "stage_max": 2 * len(stage_rows), "stage_counts": stage_counts, "price_before_cost": price_first,
        "next_step_verdict": ns_verdict, "objections": obj_rows, "red_lines": reds, "flags": flags,
        "trend": trend, "confidence": confidence, "confidence_why": cwhy,
        "measures": (measure or {}).get("measures", {}), "length_minutes": (measure or {}).get("length_minutes"),
        "has_timestamps": (measure or {}).get("has_timestamps"), "prospects": pros,
        "previous_reviews": len(past), "verdicts": v, "call_id": this_call["id"], "third_parties": third,
    }
    return [], res


def call_key(v, measure):
    """What identifies this call in memory without holding anything from it: the transcript's one-way fingerprint, or
    for a recall review a fingerprint of the date, seller, call type and offer."""
    cid = (measure or {}).get("call_id")
    if not cid:
        import hashlib
        raw = "|".join(str(v.get(k) or "") for k in ("call_date", "seller", "call_type", "offer")).lower()
        cid = "r" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:10]
    return {"id": cid, "date": v.get("call_date") or "", "seller": (v.get("seller") or "").lower(),
            "call_type": (v.get("call_type") or "").lower()}


def same_call(h, key):
    if h.get("call_id"):
        return h["call_id"] == key["id"]
    return (str(h.get("date") or "") == key["date"] and (h.get("seller") or "").lower() == key["seller"]
            and (h.get("call_type") or "").lower() == key["call_type"])


# ---------------------------------------------------------------- render

def long_date(iso, style="year month day"):
    """The call date in the founder's own order, with the month spelt out so it cannot be misread."""
    try:
        d = date.fromisoformat(iso)
    except (TypeError, ValueError):
        return iso or "date not given"
    month = d.strftime("%B")
    if style == "month day year":
        return f"{month} {d.day}, {d.year}"
    if style == "day month year":
        return f"{d.day} {month} {d.year}"
    return d.isoformat()


def q(pos, text, pros, recall):
    if recall or not pos:
        return f"\"{CR.mask_names(text, pros)}\" (recall, unverified)" if text else "(recall, unverified)"
    return f"[{pos}] \"{CR.mask_names(text, pros)}\""


def cell(s):
    return str(s or "").replace("|", "/").replace("\n", " ").strip()


def render(res):
    v = res["verdicts"]
    recall = res["mode"] == "recall"

    def ru(text):  # every finding in a recall review carries the mark
        text = (text or "").strip()
        if not recall or not text or "(recall, unverified)" in text:
            return text
        return text + " (recall, unverified)"
    pros = res.get("prospects") or {}
    m = res.get("measures") or {}
    L = []
    who = v.get("prospect") or "the prospect"
    L.append(f"# Call review: {v.get('seller')} with {who}, {long_date(v.get('call_date'), v.get('date_style'))}")
    L.append("")
    L.append(f"**{res['overall']} out of 100.** {v.get('headline', '').strip()}")
    L.append("")
    length = f"{res['length_minutes']} minutes" if res.get("length_minutes") is not None else (
        f"{v.get('length_minutes')} minutes (as you recalled it)" if v.get("length_minutes") else "length not known")
    L.append(f"Call: {v.get('call_type')}, {length} | Seller: {v.get('seller')} | Prospect: {who} | "
             f"Outcome: {v.get('outcome')}" + (f" | Offer: {v.get('offer')}" if v.get("offer") else ""))
    L.append("")
    L.append(f"Mode: {res['mode']}")
    L.append(f"Confidence: {res['confidence']}, {res['confidence_why']}.")
    L.append("")
    L.append(v.get("what_happened", "").strip())
    L.append("")
    if res.get("trend"):
        t = res["trend"][0]
        L.append(f"**Pattern:** {t['dimension']} has been weak in {t['hits']} of {v.get('seller')}'s last {t['of']} reviewed calls. "
                 "That is the structure of the call, not this prospect, so the drill below works on it.")
        L.append("")

    L.append("## The two things to change")
    L.append("")
    for k, c in enumerate(v.get("coaching") or [], 1):
        L.append(f"### {k}. {c['title'].strip().rstrip('.')}")
        L.append("")
        L.append(q(c.get("at"), c.get("quote"), pros, recall) if not recall else f"What happened: {c.get('described').strip()} (recall, unverified)")
        L.append("")
        L.append(c["cause_effect"].strip())
        L.append("")
        L.append(f"Next time: {c['fix'].strip()}")
        L.append("")
        L.append(f"Say: \"{c['say'].strip().strip(chr(34))}\"")
        L.append("")
    d = v.get("drill") or {}
    L.append("## The drill")
    L.append("")
    beh = d.get("behaviour", "").strip()
    L.append(beh if beh.endswith((".", "?")) else beh + ".")
    L.append("")
    reps = d.get("reps", "").strip().rstrip(".")
    L.append(f"{reps[:1].upper() + reps[1:]}, {d.get('by', '').strip().rstrip('.')}.")
    L.append("")

    L.append("## Where the deal was lost")
    L.append("")
    for c in v.get("creation_points") or []:
        if recall:
            L.append(f"- {c['failure'].strip().rstrip('.')}. Showed up: {c['appeared_at'].strip().rstrip('.')}. "
                     f"Started: {c['created_at'].strip().rstrip('.')}. {c['what_happened'].strip()} (recall, unverified)")
        else:
            aq = f" \"{CR.mask_names(c['appeared_quote'], pros).rstrip('.')}\"" if c.get("appeared_quote") else ""
            cq = f" \"{CR.mask_names(c['created_quote'], pros).rstrip('.')}\"" if c.get("created_quote") else ""
            L.append(f"- {c['failure'].strip()}: appeared at [{c['appeared_at']}]{aq}, created at [{c['created_at']}]{cq}. "
                     f"{c['what_happened'].strip()}")
    if not v.get("creation_points"):
        L.append("- No failure to trace: nothing on this call was left for the prospect to decide on their own.")
    L.append("")

    L.append("## Scorecard")
    L.append("")
    dims = v.get("dimensions") or {}
    if recall:
        L.append("Every row below is from your recall, unverified.")
        L.append("")
        L.append("| Dimension | Weight | Score | Why |")
        L.append("|---|---|---|---|")
    else:
        L.append("| Dimension | Weight | Score | Where | Why |")
        L.append("|---|---|---|---|---|")
    for d, w, _s in DIMENSIONS:
        x = dims.get(d) or {}
        if recall:
            L.append(f"| {d} | {w} | {res['scores'][d]} of 10 | {cell(ru(x.get('why')))} |")
        else:
            where = f"[{x.get('at')}]" if x.get("at") else ""
            L.append(f"| {d} | {w} | {res['scores'][d]} of 10 | {where} | {cell(x.get('why'))} |")
    L.append("")
    capped_flags = {c["flag"] for c in res["capped"]}
    for c in res["capped"]:
        at = "" if recall else f" at [{c['at']}]"
        L.append(f"Cap: {c['dimension']} held at {c['to']} (scored {c['from']}) because {c['why']}{at}.")
    for f in res.get("flags") or []:
        if f.get("flag") in CAPS and f["flag"] not in capped_flags:
            dim, cap, why = CAPS[f["flag"]]
            at = "" if recall or not f.get("at") else f" at [{f['at']}]"
            L.append(f"Failure confirmed{at}: {why}. {dim} was already at or under its cap of {cap}, so the score stands.")
            capped_flags.add(f["flag"])
    if not res.get("flags"):
        L.append("No cap applied: none of the four failures that cap a score happened on this call.")
    L.append(f"The overall score is the weighted average of the five scores after any cap, out of 100, rounded down.")
    L.append("")
    wk = v.get("worked") or {}
    if wk.get("quote") or wk.get("described"):
        L.append("What worked, so you keep it on purpose: " + (q(wk.get("at"), wk.get("quote"), pros, recall) if not recall
                                                               else f"{wk.get('described')} (recall, unverified)")
                 + (f" {wk.get('why').strip()}" if wk.get("why") else ""))
        L.append("")

    L.append("## Stage by stage")
    L.append("")
    struct = "your own call structure" if v.get("structure") not in (None, "default") else "the five standard stages (no call structure was given)"
    L.append(f"Read against {struct}. {res['stage_points']} of {res['stage_max']} points: done {res['stage_counts']['done']}, "
             f"partial {res['stage_counts']['partial']}, missed {res['stage_counts']['missed']}.")
    L.append("")
    if recall:
        L.append("| Stage | Verdict | What happened | Say instead |")
        L.append("|---|---|---|---|")
    else:
        L.append("| Stage | Verdict | Where | What happened | Say instead |")
        L.append("|---|---|---|---|---|")
    for s in v.get("stages") or []:
        say = f"\"{cell(s.get('say_instead')).strip(chr(34))}\"" if s.get("say_instead") else ""
        if recall:
            L.append(f"| {cell(s.get('name'))} | {s['verdict']} | {cell(ru(s.get('note')))} | {say} |")
        else:
            where = f"[{s.get('at')}]" if s.get("at") else "not on the call"
            L.append(f"| {cell(s.get('name'))} | {s['verdict']} | {where} | {cell(s.get('note'))} | {say} |")
    L.append("")

    L.append("## Objections")
    L.append("")
    if not res["objections"]:
        L.append("No objection came up on this call.")
        L.append("")
    for k, o in enumerate(res["objections"], 1):
        L.append(f"{k}. {q(o.get('at'), o.get('quote'), pros, recall) if not recall else CR.mask_names(o.get('quote') or o.get('described') or '', pros) + ' (recall, unverified)'}")
        L.append(f"   Belief underneath: {o.get('belief', '').strip()}")
        L.append(f"   Done: {', '.join(o['done']) or 'nothing'}. Missing: {', '.join(o['missing']) or 'nothing'}. Verdict: {o['handling']}.")
        if o.get("note"):
            L.append(f"   {ru(o['note'])}")
        if o.get("say_instead"):
            L.append(f"   Say instead: \"{o['say_instead'].strip().strip(chr(34))}\"")
        L.append("")

    ns = v.get("next_step") or {}
    L.append("## The next step")
    L.append("")
    grade = NEXT_STEP.get(ns.get("grade"), ns.get("grade"))
    extra = ""
    if ns.get("grade") == "decision_call_booked":
        extra = f" ({ns.get('date') or 'no date'}; agenda: {ns.get('agenda') or 'none agreed'})"
    L.append(f"{grade}{extra}: {res['next_step_verdict']}.")
    L.append("")
    ex_lines = []
    for ex in ns.get("exchange") or []:
        if recall:
            said = (ex.get("quote") or ex.get("described") or "").strip()
            if said:
                ex_lines.append(f"> {CR.mask_names(said, pros)} (recall, unverified)")
        else:
            ex_lines.append(f"> [{ex.get('at')}] \"{CR.mask_names(ex.get('quote'), pros)}\"")
    if ex_lines:
        L += ex_lines + [""]
    if ns.get("note"):
        L.append(ns["note"].strip() + (" (recall, unverified)" if recall and "(recall" not in ns["note"] else ""))
        L.append("")

    L.append("## Red lines")
    L.append("")
    labels = {"price_before_cost": "Price before cost", "deadline": "Deadline or scarcity said on the call",
              "promise": "A promise said on the call", "price_asked_early": "Price asked early",
              "untrusted": "A line in the transcript addressed to an AI"}
    if not res["red_lines"]:
        L.append("None found.")
    for r in res["red_lines"]:
        where = ""
        if not recall and r.get("at") == "header":
            where = " (in the file, above the call)" + (f": \"{CR.mask_names(r['quote'], pros)}\"" if r.get("quote") else "")
        elif not recall and r.get("at"):
            where = f" [{r['at']}]" + (f" \"{CR.mask_names(r['quote'], pros)}\"" if r.get("quote") else "")
        L.append(f"- {labels[r['kind']]}{where}: {r.get('note', '').strip()}")
    L.append("")

    L.append("## Stated reason and real reason")
    L.append("")
    rr = v.get("real_reason") or {}
    if v.get("outcome") == "lost":
        L.append(f"Stated: {v.get('stated_reason', 'not given').strip()}")
        at = "" if recall or not rr.get("at") else f" Created at [{rr['at']}]."
        L.append(f"Real: {rr.get('reason')}.{at} {rr.get('note', '').strip()}")
    else:
        L.append(f"The deal is {v.get('outcome')}, so there is no loss reason yet." + (
            f" {rr.get('note').strip()}" if rr.get("note") else ""))
    L.append("")

    wb = v.get("way_back_in") or {}
    if wb.get("message"):
        L.append("## The way back in")
        L.append("")
        if wb.get("why"):
            L.append(wb["why"].strip())
            L.append("")
        for line in wb["message"].strip().splitlines():
            L.append(f"> {line}" if line.strip() else ">")
        L.append("")

    L.append("## The numbers behind it")
    L.append("")
    if recall:
        L.append("Not measured: timings and the talk ratio need a transcript.")
    else:
        L.append("Context, not marks.")
        L.append("")
        L.append(f"- Talk ratio: the seller said {m.get('talk_ratio')}% of the words.")
        L.append(f"- Questions from the seller: {m.get('seller_questions')}, the first at [{m.get('first_question')}].")
        L.append(f"- Price first said: " + (f"[{v.get('offer_made', {}).get('at')}]" if (v.get("offer_made") or {}).get("made") else "not said on this call") + ".")
        L.append(f"- First question about what the problem costs: " + (f"[{v.get('coi_at')}]" if v.get("coi_at") else "never asked") + ".")
        L.append(f"- Longest seller turn: {m.get('longest_turn_words')} words at [{m.get('longest_turn_at')}].")
    L.append("")

    L.append("## Notes")
    L.append("")
    for x in v.get("defaults") or []:
        L.append(f"- {x.strip()}")
    if recall:
        L.append("- Prospects appear by initials. Nothing you told me is saved except what you approve for memory.")
    else:
        L.append("- Prospects appear by initials. The copy of the transcript I worked from is deleted when this review is finished, "
                 "and your own file is not touched; only what you approve for memory is saved, and that holds scores, never the "
                 "call's words or names.")
    L.append(f"- {CONSENT_LINE}")
    L.append("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    s = sub.add_parser("score")
    s.add_argument("verdicts")
    s.add_argument("--measure")
    s.add_argument("--recall", action="store_true")
    s.add_argument("--history")
    s.add_argument("--out", required=True)
    r = sub.add_parser("render")
    r.add_argument("results")
    r.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.cmd == "score":
        problems, res = cmd_score(a)
        if problems:
            for p in problems:
                print("PROBLEM:", p)
            print(f"{len(problems)} problems. Nothing was written: fix the verdicts and run again.")
            return 1
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        json.dump(res, open(a.out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        print(f"Score: {res['overall']} out of 100 (weighted average {res['weighted_mean']:.2f} of 10, rounded down)")
        print("Scores after caps: " + "; ".join(f"{d} {res['scores'][d]} ({w})" for d, w, _s in DIMENSIONS))
        for c in res["capped"]:
            print(f"CAP {c['dimension']} {c['from']} to {c['to']} ({c['flag']} at {c['at']})")
        print(f"Weakest: {res['weakest']}")
        print(f"Price before any question about cost: {'yes' if res['price_before_cost'] else 'no'}")
        print(f"Next step: {res['next_step_verdict']}")
        for o in res["objections"]:
            print(f"Objection at {o.get('at') or 'recall'}: {o['handling']}")
        for t in res["trend"]:
            print(f"TREND {t['dimension']} weak in {t['hits']} of the last {t['of']} reviews of this seller")
        if not res["trend"] and res["previous_reviews"] == 0:
            print("Trend: no earlier review of this seller in memory; this one is the baseline")
        print(f"Confidence: {res['confidence']} ({res['confidence_why']})")
        print(f"WROTE: {a.out}")
        return 0
    if a.cmd == "render":
        res = load(a.results, "results file")
        if not isinstance(res, dict) or "verdicts" not in res or "overall" not in res:
            raise Stop(f"{a.results} is not a results file from 'score_call.py score'; run score first")
        md = render(res)
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        open(a.out, "w", encoding="utf-8").write(md)
        print(f"WROTE: {a.out}")
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Stop as e:
        print(f"STOP: {e}. Nothing was written.")
        sys.exit(2)
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print(f"STOP: the scorer could not run ({type(e).__name__}: {e}). Check the verdicts against "
              "references/verdicts-schema.md. Nothing was written.")
        sys.exit(2)
