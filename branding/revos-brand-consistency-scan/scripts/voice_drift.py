#!/usr/bin/env python3
"""Measure how each asset sounds, and where the voice drifts between them. Counted, never judged by eye.

Usage:
  python3 scripts/voice_drift.py <clean/assets.json> --out <voice.json> [--sells me|me_and_others|team]
                                 [--previous <previous.json>]

Per asset: words, sentences, average sentence length, reading level (Flesch-Kincaid grade, shown
as plain, business or dense), who is speaking (I, we, or neither, with counts), contractions per
100 words and exclamation marks. Then the drift findings between assets: I against we, sentence
length, reading level and register. Assets under 40 words (a headline, a bio) get the person count
only. --previous carries the saved markers of assets the founder did not paste again this time.
It also counts spelling markers (colour or color, optimise or optimize) across the assets and reports
which English the founder writes, so what Claude writes can match it; mixed or too few markers report
unknown. Exit 0 written; exit 2 with one STOP line if the input cannot be used. Standard library only.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scan_common as C  # noqa: E402

I_WORDS = {"i", "i'm", "i've", "i'll", "i'd", "me", "my", "mine", "myself"}
WE_WORDS = {"we", "we're", "we've", "we'll", "we'd", "us", "our", "ours", "ourselves"}
YOU_WORDS = {"you", "you're", "you've", "you'll", "you'd", "your", "yours", "yourself"}
CONTRACTION_RE = re.compile(r"\b\w+'(?:s|re|ve|ll|d|m|t)\b", re.I)


def syllables(word):
    w = word.lower()
    w = re.sub(r"[^a-z]", "", w)
    if not w:
        return 0
    if len(w) <= 3:
        return 1
    w = re.sub(r"(?:[^laeiouy]es|[^laeiouy]ed|[^laeiouy]e)$", "", w)
    w = re.sub(r"^y", "", w)
    n = len(re.findall(r"[aeiouy]{1,2}", w))
    return max(1, n)


def sentences(text):
    t = C.unwrap(text)  # a PDF's hard line breaks are layout, not sentence ends
    t = re.sub(r"\s+\|\s+", "\n", t)  # LinkedIn headlines: "Founder | Brand strategist"
    parts = re.split(r"(?<=[.!?])\s+|\n+|\s+[\u2022\u00b7]\s+", t)
    return [p.strip(" -*\u2022\t") for p in parts if len(C.words(p)) >= 1]


def measure(text):
    t = C.norm_text(C.unwrap(text)).replace("[client]", "client").replace("[fee]", "fee")
    ws = C.words(t)
    n = len(ws)
    sents = sentences(text)
    # headings, labels and sign-offs ("Our approach", "Attn: [client]") are not sentences: a sentence ends in . ! or ?,
    # or runs to six words or more
    real = [s for s in sents if len(C.words(s)) >= 6 or (re.search(r"[.!?][\"')\u201d]?$", s) and len(C.words(s)) >= 3)]
    sents = real or [s for s in sents if len(C.words(s)) >= 2] or sents
    ns = max(1, len(sents))
    syl = sum(syllables(w) for w in ws)
    # "US" in capitals is a country ("a US-based team"), never the pronoun
    cased = C.words(C.unwrap(text).replace("\u2019", "'"))
    lw = [w.lower() for w in cased if w != "US"]
    i_n = sum(1 for w in lw if w in I_WORDS)
    we_n = sum(1 for w in lw if w in WE_WORDS)
    you_n = sum(1 for w in lw if w in YOU_WORDS)
    if i_n + we_n < 2:
        person = "neither"
    elif i_n >= 2 and i_n / (i_n + we_n) >= 0.6:
        person = "I"
    elif we_n >= 2 and we_n / (i_n + we_n) >= 0.6:
        person = "we"
    else:
        person = "mixed"
    measurable = n >= C.MIN_MEASURE_WORDS
    avg = round(n / ns, 1) if n else 0.0
    grade = round(0.39 * (n / ns) + 11.8 * (syl / max(1, n)) - 15.59, 1) if n else 0.0
    level = "plain" if grade < 8 else ("business" if grade <= 12 else "dense")
    return {
        "words": n, "sentences": len(sents), "avg_sentence_words": avg if measurable else None,
        "grade": grade if measurable else None, "level": level if measurable else None,
        "i": i_n, "we": we_n, "you": you_n, "person": person,
        "contractions_per_100": round(100 * len(CONTRACTION_RE.findall(t)) / max(1, n), 1) if measurable else None,
        "exclamations": text.count("!"), "measurable": measurable,
        "spelling": C.spelling_markers(text),
    }


def findings(assets, m, sells, sold_by=None):
    out = []
    by = {a["id"]: a for a in assets}
    lab = lambda i: C.in_sentence(by[i]["label"])  # noqa: E731
    i_side = [i for i in m if m[i]["person"] == "I"]
    we_side = [i for i in m if m[i]["person"] == "we"]
    if i_side and we_side:
        a = max(i_side, key=lambda i: m[i]["i"])
        b = max(we_side, key=lambda i: m[i]["we"])
        out.append({"kind": "person", "assets": [a, b],
                    "text": f"Your {lab(a)} speaks as \"I\" ({m[a]['i']} times); your {lab(b)} speaks as \"we\" ({m[b]['we']} times)."})
    others = {k for k, v in (sold_by or {}).items() if v in ("others", "team")}
    if sells == "me":  # an asset someone else sells (sold_by) may say "we"
        for i in [x for x in m if m[x]["person"] == "mixed" and x not in others]:
            out.append({"kind": "founder_fronted", "assets": [i],
                        "text": f"Your {lab(i)} switches between \"I\" ({m[i]['i']} times) and \"we\" ({m[i]['we']} times). "
                                f"Pick one; as you sell personally, \"I\" is the one buyers will meet."})
        for i in [x for x in we_side if x not in others]:
            out.append({"kind": "founder_fronted", "assets": [i],
                        "text": f"You sell personally, and your {lab(i)} says \"we\" {m[i]['we']} times against \"I\" {m[i]['i']}. "
                                f"Buyers meet you, so \"we\" here describes a team they may never speak to."})
    meas = [i for i in m if m[i]["measurable"]]
    if len(meas) >= 2:
        hi = max(meas, key=lambda i: m[i]["avg_sentence_words"])
        lo = min(meas, key=lambda i: m[i]["avg_sentence_words"])
        a_hi, a_lo = m[hi]["avg_sentence_words"], m[lo]["avg_sentence_words"]
        if a_lo and a_hi / a_lo >= 1.6 and a_hi - a_lo >= 6:
            out.append({"kind": "sentence_length", "assets": [lo, hi],
                        "text": f"Sentences average {a_lo:g} words in your {lab(lo)} and {a_hi:g} in your {lab(hi)}."})
        levels = {m[i]["level"] for i in meas}
        if len(levels) > 1:
            hard = max(meas, key=lambda i: m[i]["grade"])
            easy = min(meas, key=lambda i: m[i]["grade"])
            out.append({"kind": "reading_level", "assets": [easy, hard],
                        "text": f"Your {lab(easy)} reads as {m[easy]['level']} (grade {m[easy]['grade']:g}); "
                                f"your {lab(hard)} reads as {m[hard]['level']} (grade {m[hard]['grade']:g})."})
        big = [i for i in meas if m[i]["words"] >= 80]
        casual = [i for i in big if (m[i]["contractions_per_100"] or 0) >= 2]
        formal = [i for i in big if (m[i]["contractions_per_100"] or 0) == 0]
        if casual and formal:
            c, f = casual[0], formal[0]
            out.append({"kind": "register", "assets": [c, f],
                        "text": f"Your {lab(c)} uses contractions ({m[c]['contractions_per_100']:g} per 100 words: \"we're\", \"don't\"); "
                                f"your {lab(f)} uses none, so it reads more formal."})
    return out


def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("manifest")
    a.add_argument("--out", required=True)
    a.add_argument("--sells", choices=["me", "me_and_others", "team"])
    a.add_argument("--previous")
    args = a.parse_args()
    man = C.load_json(args.manifest, "clean assets file")
    if not isinstance(man, dict) or not isinstance(man.get("assets"), list):
        C.stop("the clean assets file has no asset list. Run redact.py first and pass <clean>/assets.json.")
    assets = [x for x in man["assets"] if isinstance(x, dict) and x.get("kind") != "agreed"]
    sells = args.sells or man.get("founder_sells") or "me"
    m = {}
    for x in assets:
        m[x["id"]] = measure(C.read_text(x["file"], f"clean text of '{x.get('id')}'"))
        m[x["id"]]["source"] = "measured today"
    if args.previous:
        prev = C.load_json(args.previous, "previous run file")
        for pid, pv in (prev.get("voice") or {}).items():
            if pid not in m and isinstance(pv, dict):
                pv = dict(pv)
                pv["source"] = f"saved {prev.get('date', 'last run')}"
                m[pid] = pv
                label = next((p.get("label") for p in prev.get("assets", []) if p.get("id") == pid), pid)
                assets.append({"id": pid, "label": label, "kind": "carried"})
    for k in m:
        m[k].setdefault("measurable", m[k].get("avg_sentence_words") is not None)
    f = findings(assets, m, sells, man.get("sold_by"))
    tot = {"british": 0, "american": 0}
    for v in m.values():
        for k in tot:
            tot[k] += (v.get("spelling") or {}).get(k, 0)
    english = C.english_of(tot)
    if english is None and args.previous:
        english = ((prev.get("locale") or {}).get("english")) or None
    Path(args.out).write_text(json.dumps({"founder_sells": sells, "english": english, "spelling": tot, "assets": m, "findings": f},
                                         indent=2), encoding="utf-8")
    for x in assets:
        v = m[x["id"]]
        meas = (f"{v['avg_sentence_words']:g} words a sentence, reads {v['level']}" if v.get("measurable")
                else "too short for sentence measures")
        size = v["source"] if str(v.get("source", "")).startswith("saved") else f"{v['words']} words"
        print(f"{x['label']}: {size}, speaks as {v['person']} (I {v['i']}, we {v['we']}, you {v['you']}), {meas}.")
    for x in f:
        print(f"DRIFT: {x['text']}")
    if not f:
        print("DRIFT: none found between the assets measured.")
    print(f"ENGLISH: {english or 'unknown'} ({tot['british']} British or Commonwealth spellings, {tot['american']} American)."
          + ("" if english else " Ask the founder, or leave spelling as they write it."))
    print(f"WROTE: {args.out}")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print(f"STOP: the voice measures could not finish ({type(e).__name__}: {e}). Check the clean assets file.")
        sys.exit(2)
