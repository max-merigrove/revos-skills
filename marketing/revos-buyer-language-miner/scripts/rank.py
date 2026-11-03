#!/usr/bin/env python3
"""Score and rank the clusters in a bank, from the ledger's counts. Claude clusters and tags; this script counts.

Usage:
  python3 scripts/rank.py --run <run folder> <bank.json> [--csv <out.csv>] [--json-out <ranked.json>]

bank.json carries the phrases (id, item, text, tag, intensity 1 to 3, stake) and the clusters (id, name, phrases).
Each cluster's score out of 100 (working defaults, stated to the founder as defaults, not research findings):
  distinct voices, up to 10, at 4 points each (40); distinct source types, up to 4, at 5 each (20);
  mean intensity scaled to 25; share of its voices heard in the fresh band (default last 30 days) times 15.
Tiers: established at 3 or more voices (ranked), emerging at 2 (shown, not ranked), single at 1 (held back).
Bank tier, decided on the voices QUOTED (people with at least one verified phrase in the bank), not the voices read:
under 5, no ranked bank; 5 to 14, a starter bank with at most 5 ranked clusters; 15 or more across at least 2 source
types, a full bank (at most 10 ranked clusters). A vendor ping, a suspect review or a one-line question read but not
quoted never lifts the tier.
A voice is a person, not a mention: one person posting three times is one voice. Items outside the window,
suspected duplicates, excluded items and text addressed to a model are never counted.
Prints the table and PROBLEM lines; exit 1 on any PROBLEM, 2 on bad input. Standard library only. No network.
"""
import argparse
import csv
import json
import os
import re
import signal
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ledger import stop, load_json, load_ledger, counted, stats, norm, words, verify_bank  # noqa: E402

TAGS = ["pain", "trigger", "objection", "outcome", "alternative"]
# The tags follow the four forces of progress: pain and trigger push, outcome pulls, objection is anxiety, alternative is habit.
# To fold "alternative" into "pain", set FOLD_ALTERNATIVE = True.
FOLD_ALTERNATIVE = False
ANGLE_TYPES = {
    "name-the-pain": "Name the pain", "cost-of-waiting": "Cost of waiting (leans on fear)", "the-moment": "The moment it hit",
    "answer-the-doubt": "Answer the doubt", "the-after": "The after", "switch-story": "Switch story",
}
ALLOWED = {
    "pain": {"name-the-pain", "cost-of-waiting", "the-after", "switch-story"},
    "trigger": {"the-moment", "name-the-pain", "the-after"},
    "objection": {"answer-the-doubt", "switch-story"},
    "outcome": {"the-after", "switch-story"},
    "alternative": {"switch-story", "answer-the-doubt", "the-after"},
}
STAKE_KINDS = {"money", "time", "event", "feeling", "repetition"}
W_VOICES, CAP_VOICES, W_TYPES, CAP_TYPES, W_INT, W_FRESH = 4, 10, 5, 4, 25, 15
ESTABLISHED, EMERGING = 3, 2
STARTER_CAP, FULL_CAP = 5, 10


def tag_of(t):
    return "pain" if FOLD_ALTERNATIVE and t == "alternative" else t


def all_phrases(L, B):
    """Bank phrases plus any previous-bank phrases the bank did not restate (they keep their IDs and clusters)."""
    phrases = [dict(p) for p in B.get("phrases", [])]
    have = {p.get("id") for p in phrases}
    for it in L["items"]:
        pv = it.get("previous")
        if pv and pv["id"] not in have:
            phrases.append({"id": pv["id"], "item": it["id"], "text": it["text"], "tag": pv.get("tag"), "intensity": pv.get("intensity", 2),
                            "stake": pv.get("stake", ""), "cluster_hint": pv.get("cluster"), "previous": True})
    return phrases


def compute(L, B):
    problems, warns = [], []
    items = {i["id"]: i for i in L["items"]}
    phrases = all_phrases(L, B)
    clusters = [dict(c) for c in B.get("clusters", [])]
    cl_ids = [c.get("id") for c in clusters]
    if len(cl_ids) != len(set(cl_ids)):
        problems.append("two clusters share an ID")
    # previous phrases with a cluster hint join that cluster unless placed explicitly
    placed = {pid for c in clusters for pid in c.get("phrases", [])}
    for p in phrases:
        if p.get("previous") and p["id"] not in placed:
            c = next((c for c in clusters if c.get("id") == p.get("cluster_hint")), None)
            if c is None:
                prev = next((pc for pc in L.get("previous_clusters", []) if pc.get("id") == p.get("cluster_hint")), None)
                c = {"id": p.get("cluster_hint") or "C-prev", "name": (prev or {}).get("name", "Earlier cluster"), "phrases": [], "from_previous": True}
                clusters.append(c)
            c.setdefault("phrases", []).append(p["id"])
    pmap = {}
    for p in phrases:
        pid = p.get("id", "")
        if not re.fullmatch(r"Q-\d{3,4}", pid or ""):
            problems.append(f"phrase ID '{pid}' should look like Q-001")
        if pid in pmap:
            problems.append(f"{pid}: used twice")
        pmap[pid] = p
        t = tag_of(p.get("tag"))
        if t not in TAGS:
            problems.append(f"{pid}: tag '{p.get('tag')}' is not one of {', '.join(TAGS)}")
        p["tag"] = t
        inten = p.get("intensity")
        if inten not in (1, 2, 3):
            problems.append(f"{pid}: intensity must be 1, 2 or 3")
            p["intensity"] = 2
        it = items.get(p.get("item"))
        if not it:
            problems.append(f"{pid}: item {p.get('item')} is not in the ledger")
            continue
        p["_item"] = it
        if inten == 3:
            st = p.get("stake") or ""
            m = re.match(r"^\s*(\w+)\s*:\s*(.+)$", st)
            if not m or m.group(1) not in STAKE_KINDS:
                problems.append(f"{pid}: intensity 3 needs a stake marker 'kind: words' (kind one of {', '.join(sorted(STAKE_KINDS))})")
            elif norm(m.group(2)) not in norm(it["text"]):
                problems.append(f"{pid}: the stake words '{m.group(2)}' are not in what this person said")
    for pid, why in verify_bank(L, {"phrases": [p for p in phrases if not p.get("previous")]}):
        problems.append(f"{pid}: {why}")
    seen = {}
    for c in clusters:
        for pid in c.get("phrases", []):
            if pid not in pmap:
                problems.append(f"cluster {c.get('id')}: phrase {pid} is not in the bank")
            elif pid in seen:
                problems.append(f"{pid} is in two clusters ({seen[pid]} and {c.get('id')}); one cluster per phrase")
            seen[pid] = c.get("id")
    for pid in pmap:
        if pid not in seen:
            problems.append(f"{pid} is in no cluster; put it in one (a cluster of one is fine)")
    # metrics
    for c in clusters:
        ps = [pmap[x] for x in c.get("phrases", []) if x in pmap and "_item" in pmap[x]]
        cps = [p for p in ps if counted(p["_item"])]
        voices = sorted({p["_item"]["voice"] for p in cps})
        types = sorted({p["_item"]["source_type"] for p in cps if p["_item"]["source_type"] != "previous"} |
                       {p["_item"]["source_type"] for p in cps if p["_item"]["source_type"] == "previous"})
        fresh_v = {p["_item"]["voice"] for p in cps if p["_item"].get("fresh")}
        dated_v = {p["_item"]["voice"] for p in cps if p["_item"]["date"]}
        mean_int = sum(p["intensity"] for p in cps) / len(cps) if cps else 0
        tags = [p["tag"] for p in cps]
        dom = max(TAGS, key=lambda t: (tags.count(t), -TAGS.index(t))) if tags else (ps[0]["tag"] if ps else "pain")
        score = (min(len(voices), CAP_VOICES) * W_VOICES + min(len(types), CAP_TYPES) * W_TYPES
                 + (max(mean_int, 1) - 1) / 2 * W_INT + (len(fresh_v) / len(voices) if voices else 0) * W_FRESH)
        last = max((p["_item"]["date"] for p in cps if p["_item"]["date"]), default=None)
        first = min((p["_item"]["date"] for p in cps if p["_item"]["date"]), default=None)
        obj_v = {p["_item"]["voice"] for p in cps if p["tag"] in ("objection", "alternative")}
        c.update({"voices": len(voices), "voice_ids": voices, "source_types": types, "fresh_voices": len(fresh_v), "dated_voices": len(dated_v),
                  "undated_voices": len(set(voices) - dated_v), "objection_voices": len(obj_v),
                  "mean_intensity": round(mean_int, 2), "score": round(score), "dominant_tag": dom, "tag_mix": {t: tags.count(t) for t in TAGS if tags.count(t)},
                  "counted_phrases": [p["id"] for p in cps], "all_phrases": [p["id"] for p in ps], "last_seen": last, "first_seen": first,
                  "tier": "established" if len(voices) >= ESTABLISHED else "emerging" if len(voices) == EMERGING else "single" if voices else "outside window"})
    S = stats(L)
    q_items = [p["_item"] for p in phrases if "_item" in p and counted(p["_item"])]
    q_voices = {i["voice"] for i in q_items}
    q_types = {i["source_type"] for i in q_items}
    quoted = {"voices": len(q_voices), "source_types": sorted(q_types), "sources": len({i["source"] for i in q_items}),
              "undated_voices": len(q_voices - {i["voice"] for i in q_items if i["date"]})}
    read_items = [i for i in L["items"] if counted(i)]
    read_v = {i["voice"] for i in read_items}
    S["undated_voices"] = len(read_v - {i["voice"] for i in read_items if i["date"]})
    S["outside_voices"] = len({i["voice"] for i in L["items"] if i["in_window"] == "no"} - read_v)
    S["voices_by_type"] = {t: len({i["voice"] for i in read_items if i["source_type"] == t}) for t in sorted({i["source_type"] for i in read_items})}
    bank_tier = "none" if len(q_voices) < 5 else "full" if len(q_voices) >= 15 and len(q_types) >= 2 else "starter"
    est = sorted([c for c in clusters if c["tier"] == "established"], key=lambda c: (-c["score"], -c["voices"], c["id"]))
    cap = 0 if bank_tier == "none" else STARTER_CAP if bank_tier == "starter" else FULL_CAP
    ranked = est[:cap]
    for i, c in enumerate(ranked, 1):
        c["rank"] = i
    for c in est[cap:]:
        c["rank"] = None
        c["held_reason"] = "no ranked bank under 5 voices quoted" if cap == 0 else f"over the {cap}-cluster cap for a {bank_tier} bank"
    for c in clusters:
        c.setdefault("rank", None)
    # twelve phrases to use first: by cluster rank, then intensity, then most recent, at most 3 per cluster on the first pass
    top = []
    for pass_cap in (3, 99):
        for c in ranked:
            cps = sorted([pmap[x] for x in c["counted_phrases"]], key=lambda p: (-p["intensity"], -(int((p["_item"]["date"] or "0000-00-00").replace("-", "")))))
            n = sum(1 for t in top if t["cluster"] == c["id"])
            for p in cps:
                if len(top) >= 12:
                    break
                if any(t["id"] == p["id"] for t in top) or n >= pass_cap:
                    continue
                top.append({"id": p["id"], "cluster": c["id"]})
                n += 1
    # return-run delta
    delta = []
    prev = {pc["id"]: pc for pc in L.get("previous_clusters", [])}
    if L.get("previous_run"):
        prev_ids = {it["previous"]["id"] for it in L["items"] if it.get("previous")}
        for c in clusters:
            pc = prev.get(c["id"])
            new_ph = [x for x in c["counted_phrases"] if x not in prev_ids]
            new_voices = len({pmap[x]["_item"]["voice"] for x in new_ph} - {pmap[x]["_item"]["voice"] for x in c["counted_phrases"] if x in prev_ids})
            before = int(pc.get("voices", 0)) if pc else 0
            if not pc:
                status = "new"
            elif c["voices"] > before and new_ph:
                status = "rising"
            elif not new_ph:
                status = "faded"
            else:
                status = "steady"
            retired = [x for x in c["all_phrases"] if x in prev_ids and pmap[x]["_item"]["in_window"] == "no"]
            delta.append({"cluster": c["id"], "name": c.get("name", ""), "status": status, "voices_before": before, "voices_now": c["voices"],
                          "new_phrases": len(new_ph), "new_voices": new_voices, "retired_outside_window": retired})
        for pid_, pc in prev.items():
            if pid_ not in {c["id"] for c in clusters}:
                delta.append({"cluster": pid_, "name": pc.get("name", ""), "status": "faded", "voices_before": int(pc.get("voices", 0)), "voices_now": 0,
                              "new_phrases": 0, "new_voices": 0, "retired_outside_window": []})
    return {"stats": S, "quoted": quoted, "bank_tier": bank_tier, "clusters": clusters, "ranked": [c["id"] for c in ranked], "phrases": pmap, "top12": top,
            "delta": delta, "problems": problems, "warns": warns, "cap": cap}


def write_csv(L, R, path):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["ID", "Phrase", "Tag", "Cluster", "Voice", "Source", "Source type", "Origin", "Date", "Date status", "In window",
                    "Intensity", "Stake marker", "Flags"])
        cl = {pid: c["id"] for c in R["clusters"] for pid in c.get("all_phrases", [])}
        for pid in sorted(R["phrases"]):
            p = R["phrases"][pid]
            it = p.get("_item")
            if not it:
                continue
            flags = list(it.get("flags", []))
            if it["in_window"] == "no":
                flags.insert(0, "outside window")
            w.writerow([pid, p["text"], p["tag"], cl.get(pid, ""), it["voice"], it["source"], it["source_type"], it["origin"], it["date"] or "",
                        it["date_status"], {"yes": "yes", "no": "no", "unknown": "undated"}[it["in_window"]], p["intensity"], p.get("stake", ""),
                        "; ".join(flags)])
        quoted = {p["_item"]["id"] for p in R["phrases"].values() if p.get("_item")}
        for it in L["items"]:  # read but not quoted, and left out of every count: shown so the founder can see why
            if it["source"] == "P" or it["id"] in quoted or not (it["in_window"] == "no" or it.get("dup_of") or it.get("suspicious") or it.get("excluded")):
                continue
            flags = list(it.get("flags", []))
            if it["in_window"] == "no":
                flags.insert(0, "outside window")
            w.writerow([it["id"], "(not quoted) " + it["text"], "", "", it["voice"], it["source"], it["source_type"], it["origin"], it["date"] or "",
                        it["date_status"], {"yes": "yes", "no": "no", "unknown": "undated"}[it["in_window"]], "", "", "; ".join(flags)])


def main():
    if hasattr(signal, "SIGPIPE"):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("bank")
    ap.add_argument("--csv")
    ap.add_argument("--json-out")
    try:
        a = ap.parse_args()
    except SystemExit as e:
        if e.code not in (0, None):
            stop("the command was not understood; see the usage at the top of scripts/rank.py")
        raise
    L = load_ledger(a.run)
    B = load_json(a.bank, "bank")
    if not isinstance(B, dict) or not isinstance(B.get("phrases", []), list) or not isinstance(B.get("clusters", []), list):
        stop("bank.json must be an object with 'phrases' and 'clusters' lists; see references/bank-format.md")
    R = compute(L, B)
    S = R["stats"]
    Q = R["quoted"]
    print(f"BANK: {R['bank_tier']} ({Q['voices']} voices quoted across {len(Q['source_types'])} source types; {S['voices']} voices read; "
          f"{'no ranked bank under 5 voices quoted' if R['cap'] == 0 else 'at most ' + str(R['cap']) + ' clusters ranked'})")
    if Q["voices"] < S["voices"]:
        print(f"NOTE: {S['voices'] - Q['voices']} voices read but not quoted; the tier counts only voices with a verified phrase in the bank")
    for c in sorted(R["clusters"], key=lambda c: (c["rank"] is None, c["rank"] or 0, -c["score"])):
        lab = f"#{c['rank']}" if c["rank"] else c["tier"] + (f" ({c['held_reason']})" if c.get("held_reason") else "")
        print(f"{c['id']} {lab}: score {c['score']}, {c['voices']} voices, {len(c['source_types'])} source types, "
              f"{c['fresh_voices']} fresh, intensity {c['mean_intensity']}, mostly {c['dominant_tag']}: {c.get('name', '')}")
    for d in R["delta"]:
        print(f"CHANGE {d['cluster']} {d['status']}: {d['voices_before']} to {d['voices_now']} voices, {d['new_phrases']} new phrases"
              f"{', ' + str(len(d['retired_outside_window'])) + ' now outside the window' if d['retired_outside_window'] else ''}")
    for p in R["problems"]:
        print("PROBLEM:", p)
    if a.csv:
        write_csv(L, R, a.csv)
        print(f"WROTE {a.csv}")
    if a.json_out:
        out = {k: v for k, v in R.items() if k != "phrases"}
        out["phrases"] = {k: {kk: vv for kk, vv in v.items() if kk != "_item"} for k, v in R["phrases"].items()}
        with open(a.json_out, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"{len(R['problems'])} problems")
    sys.exit(1 if R["problems"] else 0)


if __name__ == "__main__":
    main()
