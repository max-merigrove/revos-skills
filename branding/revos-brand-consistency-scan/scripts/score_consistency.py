#!/usr/bin/env python3
"""Score how consistently the founder's assets answer the five questions. Arithmetic in code, from the table.

Usage:
  python3 scripts/score_consistency.py <extraction.json> [--previous <previous.json>] [--out <score.json>]

Claude's only judgement is which answers mean the same thing (the same group letter), and which
groups are compatible (one is a narrower or broader form of the other). Everything else is counted:

  For each question, every pair of assets is compared, weighted by both assets' weights
  (proposal, deck, onboarding, invoice, client email 3; website 2; LinkedIn 1.5; other 1).
  Same group 1, compatible 0.5, either silent 0.25, different 0. The question's points are its
  weight (who 25, what 25, result 20, why 20, next 10) times the weighted share. Total out of 100.

On a return run with the founder's agreed answers saved, each asset is also scored against those
answers: the alignment score. Contradictions are ranked by the points they cost.
Prints the score, the five rows and the ranked contradictions; --out writes them as JSON.
Exit 0; exit 2 with one STOP line if the table cannot be scored. Standard library only.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scan_common as C  # noqa: E402

STATUS_WORDS = {"conflict": "Conflicts", "partial": "Partly agrees", "gaps": "Gaps", "agree": "Agrees",
                "missing": "Never answered"}
RELATION_WORDS = {"anchor": "", "same": "Same answer", "compatible": "Narrower or broader",
                  "conflict": "Different answer", "missing": "Not stated", "skipped": "Left out on purpose"}


def validate(ext):
    if not isinstance(ext, dict):
        C.stop("the extraction file must be one JSON object. Start from assets/extraction-template.json.")
    assets = ext.get("assets")
    if not isinstance(assets, list) or not assets:
        C.stop("the extraction file lists no assets.")
    ids = set()
    for a in assets:
        if not isinstance(a, dict) or not a.get("id"):
            C.stop("every asset needs an id, a kind, a label and a file.")
        k = C.kind_of(a.get("kind"))
        if k is None:
            C.stop(f"asset '{a['id']}' has kind '{a.get('kind')}', which the scan does not know.")
        a["kind"] = k
        a["weight"] = C.KIND_WEIGHTS[k]
        a.setdefault("label", C.KIND_NAMES[k])
        ids.add(a["id"])
    scored = [a for a in assets if a["kind"] != "agreed"]
    has_ref = any(a["kind"] == "agreed" for a in assets)
    if len(scored) < 2:
        C.stop("a consistency scan compares at least two assets, and only one was given. Ask the founder for a "
               "second (their website home page, LinkedIn about section, or a recent proposal), then run again.")
    answers = ext.get("answers")
    if not isinstance(answers, dict):
        C.stop("the extraction file has no answers table. Fill answers.who, .what, .result, .why and .next.")
    missing_q = [q for q in C.QKEYS if q not in answers]
    if missing_q:
        C.stop("the answers table is missing " + ", ".join(missing_q) + ". Add each, with null for an asset that never answers.")
    for q in C.QKEYS:
        row = answers[q]
        if not isinstance(row, dict):
            C.stop(f"answers.{q} must map each asset id to {{\"quote\": ..., \"group\": ...}} or null.")
        for aid, cell in row.items():
            if aid not in ids:
                C.stop(f"answers.{q} names asset '{aid}', which is not in the asset list.")
            if cell is None:
                continue
            if isinstance(cell, str):
                C.stop(f"answers.{q}.{aid} is a bare string. Give it a group letter: {{\"quote\": \"...\", \"group\": \"A\"}}.")
            if not isinstance(cell, dict) or not str(cell.get("group") or "").strip():
                C.stop(f"answers.{q}.{aid} has no group letter. Answers that mean the same thing share a letter.")
            if not str(cell.get("quote") or "").strip():
                C.stop(f"answers.{q}.{aid} has a group but no quote. Quote the line, or set the cell to null.")
            cell["group"] = str(cell["group"]).strip().upper()
        for a in assets:
            row.setdefault(a["id"], None)
    facts = ext.get("facts") or []
    if not isinstance(facts, list):
        C.stop("facts must be a list: [{\"what\": \"team size\", \"cells\": [{\"asset\": \"web\", \"quote\": ...}, ...]}].")
    for k, f in enumerate(facts, 1):
        cells = f.get("cells") if isinstance(f, dict) else None
        if not isinstance(cells, list) or len({c.get("asset") for c in cells if isinstance(c, dict)}) < 2:
            C.stop(f"fact {k} needs \"what\" and at least two cells from two different assets, each with a quote.")
        for c in cells:
            if c.get("asset") not in ids or not str(c.get("quote") or "").strip():
                C.stop(f"fact {k}: every cell needs an asset from the asset list and a quote.")
    return assets, scored, has_ref


STOP_WORDS = {"about", "after", "their", "there", "these", "those", "which", "while", "where", "would", "could", "should",
              "every", "other", "through", "within", "without", "before", "because", "between", "people", "really"}


def overlap_hints(ext, texts, res):
    """Where one asset's answer is named inside another asset's text: grouped as different, possibly compatible."""
    out = []
    for r in res["rows"]:
        cells = [c for c in r["cells"] if c["group"] and c["relation"] != "skipped"]
        for a in cells:
            toks = [w for w in re.findall(r"[^\W_]+(?:-[^\W_]+)*", C.norm_text(a["quote"]))]
            key = {w for w in toks if "-" in w and all(len(x) >= 3 for x in w.split("-"))}  # first-time, high-growth
            key |= {f"{x} {y}" for x, y in zip(toks, toks[1:]) if len(x) >= 4 and len(y) >= 4
                    and x not in STOP_WORDS and y not in STOP_WORDS}  # two content words in a row
            for b in cells:
                if a is b or a["group"] == b["group"] or b["asset"] not in texts:
                    continue
                if frozenset((a["group"], b["group"])) in compat_pairs(ext, r["q"]):
                    continue
                body = C.norm_text(texts[b["asset"]])
                hits = sorted(w for w in key if re.search(r"(?<![\w-])" + re.escape(w) + r"(?![\w-])", body))
                if hits:
                    shared = '", "'.join(hits[:3])
                    out.append(f"{r['label']}: your {C.in_sentence(b['label'])} also uses \"{shared}\" from "
                               f"your {C.in_sentence(a['label'])}'s answer. If a buyer would hear one answer inside the other, "
                               f"list {a['group']} and {b['group']} as compatible; if not, leave them different.")
    return sorted(set(out))


def compat_pairs(ext, q):
    out = set()
    for item in (ext.get("compatible") or {}).get(q) or []:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            g1, g2 = str(item[0]).strip().upper(), str(item[1]).strip().upper()
            out.add(frozenset((g1, g2)))
    return out


def pair_value(g1, g2, comp):
    if g1 is None or g2 is None:
        return C.VALUE_MISSING
    if g1 == g2:
        return C.VALUE_SAME
    if frozenset((g1, g2)) in comp:
        return C.VALUE_COMPATIBLE
    return C.VALUE_CONFLICT


def score(ext, previous=None):
    assets, scored, has_ref = validate(ext)
    by = {a["id"]: a for a in assets}
    skip, _why = C.skip_map(ext)
    for a in scored:  # a proposal's next step is to sign: it is not scored against a website's call to action
        if a["kind"] in C.CLIENT_FACING and "next" not in skip.setdefault(a["id"], []):
            skip[a["id"]].append("next")
    answers = ext["answers"]
    rows, total, align_num, align_den = [], 0, 0.0, 0
    order = {a["id"]: i for i, a in enumerate(assets)}
    for q in C.QKEYS:
        comp = compat_pairs(ext, q)
        live = [a for a in scored if q not in (skip.get(a["id"]) or [])]
        grp = {a["id"]: (answers[q][a["id"]] or {}).get("group") if answers[q][a["id"]] else None for a in live}
        stated = [a for a in live if grp[a["id"]]]
        ref = None
        if has_ref:
            r = next(a for a in assets if a["kind"] == "agreed")
            cell = answers[q].get(r["id"])
            ref = cell["group"] if cell else None
        # pairwise consistency
        num = den = 0.0
        statuses = set()
        for i in range(len(live)):
            for j in range(i + 1, len(live)):
                w = live[i]["weight"] * live[j]["weight"]
                v = pair_value(grp[live[i]["id"]], grp[live[j]["id"]], comp)
                num += w * v
                den += w
                statuses.add({C.VALUE_SAME: "agree", C.VALUE_COMPATIBLE: "partial", C.VALUE_MISSING: "gaps",
                              C.VALUE_CONFLICT: "conflict"}[v])
        if not stated:
            share, status = 0.0, "missing"
        elif den == 0:
            share, status = (1.0 if stated else C.VALUE_MISSING), ("agree" if stated else "missing")
        else:
            share = num / den
            status = next(s for s in ["conflict", "partial", "gaps", "agree"] if s in statuses)
        pts = C.round_half_up(C.QWEIGHT[q] * share)
        total += pts
        # anchor: the agreed answer on a return run, otherwise the answer carrying the most weight
        if ref:
            anchor = ref
        elif stated:
            weights = {}
            for a in stated:
                weights.setdefault(grp[a["id"]], []).append(a)
            anchor = sorted(weights, key=lambda g: (-sum(x["weight"] for x in weights[g]),
                                                    -max(x["weight"] for x in weights[g]),
                                                    min(order[x["id"]] for x in weights[g])))[0]
        else:
            anchor = None
        cells = []
        for a in sorted(scored, key=lambda x: (-x["weight"], order[x["id"]])):
            cell = answers[q][a["id"]]
            if q in (skip.get(a["id"]) or []):
                rel = "skipped"
            elif not cell:
                rel = "missing"
            elif anchor is None:
                rel = "missing"
            elif cell["group"] == anchor:
                rel = "anchor"
            elif frozenset((cell["group"], anchor)) in comp:
                rel = "compatible"
            else:
                rel = "conflict"
            cells.append({"asset": a["id"], "label": a["label"], "kind": a["kind"], "weight": a["weight"],
                          "client_facing": a["kind"] in C.CLIENT_FACING,
                          "quote": cell["quote"] if cell else None, "group": cell["group"] if cell else None,
                          "relation": rel})
        # where the anchor group is held by several assets, the heaviest is shown as the anchor and the rest as same
        first_anchor = next((c for c in cells if c["relation"] == "anchor"), None)
        for c in cells:
            if c["relation"] == "anchor" and c is not first_anchor:
                c["relation"] = "same"
        align = None
        if ref:
            an = ad = 0.0
            for a in live:
                g = grp[a["id"]]
                v = pair_value(g, ref, comp)
                an += a["weight"] * v
                ad += a["weight"]
            align = C.round_half_up(C.QWEIGHT[q] * an / ad) if ad else 0
            align_num += align
            align_den += C.QWEIGHT[q]
        rows.append({"q": q, "label": C.QLABEL[q], "phrase": C.QPHRASE[q], "weight": C.QWEIGHT[q], "points": pts,
                     "lost": round(C.QWEIGHT[q] * (1 - share), 2), "share": round(share, 3), "status": status,
                     "status_word": STATUS_WORDS[status], "anchor": anchor, "cells": cells, "alignment": align})
    contradictions = []
    for r in rows:
        if r["status"] != "conflict":
            continue
        conf = [c for c in r["cells"] if c["relation"] == "conflict"]
        anch = next((c for c in r["cells"] if c["relation"] == "anchor"), None)
        if not anch and len({c["group"] for c in conf}) >= 2:  # no asset holds the agreed answer: compare the two heaviest
            conf = sorted(conf, key=lambda c: (-c["weight"], order[c["asset"]]))
            anch = conf[0]
            conf = [c for c in conf[1:] if c["group"] != anch["group"]]
        if not conf or not anch:
            continue
        other = max(conf, key=lambda c: (c["weight"], -order[c["asset"]]))
        contradictions.append({
            "q": r["q"], "label": r["label"], "phrase": r["phrase"], "lost": r["lost"], "cost": r["weight"] - r["points"],
            "client_facing": any(c["client_facing"] for c in conf + [anch]),
            "a": anch, "b": other, "cells": r["cells"],
            "sentence": f"Your {C.in_sentence(anch['label'])} and your {C.in_sentence(other['label'])} give different answers to {r['phrase']}."})
    contradictions.sort(key=lambda c: (-c["lost"], not c["client_facing"], -C.QWEIGHT[c["q"]]))
    missing = []
    for r in rows:
        for c in r["cells"]:
            if c["relation"] == "missing":
                missing.append({"q": r["q"], "label": r["label"], "phrase": r["phrase"], "asset": c["asset"],
                                "asset_label": c["label"], "weight": c["weight"]})
    missing.sort(key=lambda m: (-m["weight"], -C.QWEIGHT[m["q"]]))
    if contradictions:
        headline = contradictions[0]["sentence"]
    elif missing:
        m0 = missing[0]
        headline = f"Your assets agree where they speak, but your {C.in_sentence(m0['asset_label'])} never says {m0['phrase']}."
    else:
        headline = "Your assets tell one story. What is left is wording, not position."
    word, reading = C.band(total)
    out = {"business": ext.get("business", ""), "date": ext.get("date", ""), "total": total, "band": word,
           "band_line": reading, "headline": headline, "rows": rows, "contradictions": contradictions,
           "missing": missing, "facts": [dict(f, cells=[dict(c, label=by[c["asset"]]["label"]) for c in f["cells"]])
                                         for f in ext.get("facts") or []],
           "alignment": C.round_half_up(100 * align_num / align_den) if align_den else None,
           "assets": [{"id": a["id"], "label": a["label"], "kind": a["kind"], "weight": a["weight"],
                       "from_memory": a.get("from_memory")} for a in assets]}
    if previous:
        ps = previous.get("scores") or {}
        out["movement"] = {r["q"]: (r["points"] - ps[r["q"]]) if isinstance(ps.get(r["q"]), (int, float)) else None
                           for r in rows}
        out["previous_total"] = ps.get("total")
        out["previous_date"] = previous.get("date")
        out["previous_alignment"] = ps.get("alignment")
    return out


def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("extraction")
    a.add_argument("--previous")
    a.add_argument("--out")
    args = a.parse_args()
    ext = C.load_json(args.extraction, "extraction file")
    prev = C.load_json(args.previous, "previous run file") if args.previous else None
    res = score(ext, prev)
    base = Path(args.extraction).resolve().parent
    texts = {}
    for a in ext["assets"]:
        f = Path(a.get("file") or "")
        f = f if f.is_absolute() else base / f
        if a["kind"] != "agreed" and not a.get("from_memory") and f.exists():
            texts[a["id"]] = C.read_text(f)
    decimal = (ext.get("locale") or {}).get("decimal") or C.detect_decimal(list(texts.values()))
    print(f"SCORE: {res['total']} of 100 ({res['band']}). {res['headline']}")
    if res["alignment"] is not None:
        print(f"ALIGNMENT with the agreed answers: {res['alignment']} of 100")
    for r in res["rows"]:
        mv = ""
        if res.get("movement") and res["movement"].get(r["q"]) is not None:
            mv = f" ({res['movement'][r['q']]:+d} since {res.get('previous_date')})"
        print(f"  {r['label']}: {r['points']} of {r['weight']}, {r['status_word']}{mv}")
    for i, c in enumerate(res["contradictions"], 1):
        print(f"CONTRADICTION {i} (costs {c['cost']} points): {c['a']['label']} \"{c['a']['quote']}\" against "
              f"{c['b']['label']} \"{c['b']['quote']}\"")
    for m in res["missing"]:
        print(f"MISSING: your {C.in_sentence(m['asset_label'])} never says {m['phrase']}.")
    for f in res["facts"]:
        print("FACT: " + "; ".join(f"{c['label']} \"{c['quote']}\"" for c in f["cells"]) + f" ({f.get('what', '')}). Shown first on the report.")
    listed = {(c["asset"], C.norm_text(c["quote"])) for f in res["facts"] for c in f["cells"]}
    for cand in C.fact_candidates(texts, {a["id"]: a["label"] for a in ext["assets"]}, decimal):
        if not any(a == cand["a"] for a, _q in listed) or not any(a == cand["b"] for a, _q in listed):
            print(f"CHECK FACT: your {C.in_sentence(cand['a_label'])} says \"{cand['a_words']}\" and your "
                  f"{C.in_sentence(cand['b_label'])} says \"{cand['b_words']}\" ({cand['what']}). If both describe the same "
                  f"thing, add it to \"facts\" with a quote from each; a buyer who reads both will ask which is true.")
    for aid, w in C.implausible_facts(texts, decimal):
        print(f"ASK: \"{w}\" in {aid} does not look right. Ask the founder before quoting it.")
    for h in overlap_hints(ext, texts, res):
        print(f"CHECK OVERLAP: {h}")
    if args.out:
        Path(args.out).write_text(json.dumps(res, indent=2), encoding="utf-8")
        print(f"WROTE: {args.out}")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print(f"STOP: the score could not be worked out ({type(e).__name__}: {e}). Check the answers table's shape.")
        sys.exit(2)
