#!/usr/bin/env python3
"""Build and check the buyer-question panel.

Usage:
  python3 scripts/queries.py suggest --intake intake.json
      Prints derived candidate questions (English templates) from the offer words, buyer type,
      place and alternatives. Claude rewrites them in the buyers' language and wording.
  python3 scripts/queries.py validate <panel.json> --source <pasted text file> [--source ...] [--out panel-checked.json]
      Every rule below, then numbers the panel (Q1.., branded B1..B3) and marks the questions to run first.

Rules: 5 to 12 questions kept (cuts are recorded, not deleted); each has a family (category, choosing,
problem, objection, cost), a tag (heard or derived) and a source. A heard question is the buyer's
words unchanged, question mark or not, and its quote is found in what the founder pasted. A heard
message written to the business ("do you shoot at our place?") names no service or place, so it is
refused as it stands: keep the quote, reword the text as a buyer asks an assistant, set reworded: true.
A derived question names offer words that appear in what the founder pasted (matched word by word,
across spellings: food photography is in "food and hospitality photography", Wärmepumpe in waermepumpe).
No other question is a keyword string. No unbranded question holds the business name. Near duplicates
are refused. A local business keeps its place in at least three of the questions run first and three of
the five quick ones (place-bearing questions are moved up to make it so). Exactly three branded questions
check what assistants say about the business. Exit 0 clean, 1 with PROBLEM lines, 2 with STOP on unreadable input. No network calls.
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import fold, load_json, norm, read_text, same_word, save_json, stop  # noqa: E402

FAMILIES = ["category", "choosing", "problem", "objection", "cost"]
QWORDS = {
    # English
    "what", "whats", "who", "whos", "which", "how", "hows", "where", "wheres", "when", "why", "is", "are", "do", "does", "did", "can",
    "could", "should", "would", "will", "has", "have", "any", "much", "need", "best", "anyone", "recommend",
    # German (verb-first questions are normal: "lohnt sich ...", "bekommt man ...")
    "was", "wer", "welche", "welcher", "welches", "wie", "wieviel", "wo", "woher", "wann", "warum", "weshalb", "gibt", "kann", "koennen",
    "kostet", "lohnt", "bekommt", "braucht", "brauche", "muss", "sollte", "soll", "ist", "sind", "hat", "habe", "darf", "macht", "baut",
    "empfehlt", "kennt",
    # Dutch
    "wat", "welke", "welk", "hoe", "hoeveel", "waar", "wanneer", "waarom", "zijn", "doen", "kan", "kun", "kunnen", "moet", "mag", "kost",
    "loont", "heb", "hebben", "wordt", "ben", "weet", "raad",
    # French
    "quel", "quelle", "quels", "quelles", "qui", "comment", "ou", "combien", "pourquoi", "quand", "est", "est-ce", "faut", "faut-il",
    "peut", "peut-on", "dois", "dois-je", "vaut", "y", "existe",
    # Spanish
    "que", "quien", "cual", "cuales", "como", "donde", "cuanto", "cuanta", "cuando", "por", "hay", "puedo", "vale", "cuesta",
    "necesito", "debo", "conviene", "es", "son", "merece",
}
RUN_FIRST, QUICK = 8, 5
# A message written to the business itself ("do you shoot at our restaurant?"), not a question for an assistant.
TO_VENDOR = re.compile(r"(?i)\b(you|your|u|ur|yours|ihr|euch|euer|eure|ihnen|jullie|jij|je|uw|vous|votre|vos|tu|usted|ustedes|su)\b")
STOP_TOKENS = {"and", "the", "for", "with", "und", "der", "die", "das", "fuer", "von", "en", "de", "het", "een", "voor", "et", "le",
               "la", "les", "pour", "y", "el", "los", "las", "para", "in", "of", "a", "an"}


def is_question(text):
    t = text.strip()
    toks = fold(t).split()
    if len(toks) < 4:
        return False
    return t.endswith("?") or toks[0] in QWORDS


def toks(text):
    return [w for w in fold(text).split() if len(w) >= 3 and w not in STOP_TOKENS]


def has_words(text, phrase, need_all=False):
    """Offer words matched word by word across spellings: 'food photography' is in 'food and hospitality photography';
    'Wärmepumpe' is in 'waermepumpe'."""
    have = toks(text)
    want = toks(phrase) or fold(phrase).split()
    hits = [any(same_word(w, h) for h in have) for w in want]
    return all(hits) if need_all else any(hits)


def jaccard(a, b):
    sa, sb = set(norm(a).split()), set(norm(b).split())
    return len(sa & sb) / max(1, len(sa | sb))


def suggest(intake):
    cat = intake.get("category") or (intake.get("offer_words") or ["your service"])[0]
    seg = intake.get("buyer") or "a business like mine"
    place = (intake.get("locations") or [""])[0]
    where = f" in {place}" if place else ""
    alts = intake.get("alternatives") or []
    out = [
        ("category", f"What does a {cat} do for {seg}?"),
        ("choosing", f"Who are the best {cat} providers for {seg}{where}?"),
        ("choosing", f"How do I choose a {cat}{where}?"),
        ("cost", f"How much does {cat} cost for {seg}{where}?"),
        ("problem", f"Who can help {seg}{where} with {cat}?"),
        ("objection", f"Is it worth paying for {cat} or should we do it ourselves?"),
    ]
    for alt in alts[:2]:
        out.append(("choosing", f"Should I use a {cat} or {alt}?"))
    return out


def validate(panel, sources):
    probs, warns = [], []
    src = norm(" ".join(sources))
    src_raw = " ".join(sources)
    biz = [panel.get("business", "")] + list(panel.get("aliases") or [])
    biz = [b for b in biz if b and len(b) > 2]
    offer = [w for w in (panel.get("offer_words") or []) if w]
    locs = [l for l in (panel.get("locations") or []) if l]
    for w in offer:
        if not has_words(src_raw, w, need_all=True):
            probs.append(f"offer word '{w}' is not in anything the founder pasted or said; use their words")
    qs = panel.get("questions")
    if not isinstance(qs, list) or not qs:
        stop("panel.json has no 'questions' list. Each question needs text, family, tag (heard or derived) and source.")
    kept = [q for q in qs if not q.get("cut")]
    for q in qs:
        if q.get("cut") and not q.get("cut_reason"):
            probs.append(f"cut question '{q.get('text', '')[:50]}' has no cut_reason; record why the founder cut it")
    if not 5 <= len(kept) <= 12:
        probs.append(f"{len(kept)} questions kept; the panel holds 5 to 12")

    def says_what(t):
        return any(has_words(t, w, need_all=True) for w in offer) or any(has_words(t, l, need_all=True) for l in locs)

    for i, q in enumerate(kept):
        t = (q.get("text") or "").strip()
        lab = f"'{t[:60]}'"
        if not t:
            probs.append(f"question {i + 1} has no text")
            continue
        if q.get("family") not in FAMILIES:
            probs.append(f"{lab}: family must be one of {', '.join(FAMILIES)}")
        tag = q.get("tag")
        if tag not in ("heard", "derived"):
            probs.append(f"{lab}: tag must be heard or derived")
        if not (q.get("source") or "").strip():
            probs.append(f"{lab}: no source (where it was heard, or the offer words it was built from)")
        for b in biz:
            if norm(b) and (re.search(r"\b" + re.escape(norm(b)) + r"\b", norm(t)) or fold(b) in fold(t)):
                probs.append(f"{lab}: an unbranded question must not contain the business name '{b}'")
        quote = (q.get("quote") or "").strip()
        exact = tag == "heard" and quote and norm(quote) == norm(t) and norm(quote) in src
        if tag == "heard":
            if not quote:
                probs.append(f"{lab}: a heard question needs the quote it came from")
            elif norm(quote) not in src:
                probs.append(f"{lab}: its quote is not in anything the founder pasted; tag it derived or use their exact words")
            elif norm(quote) != norm(t) and not q.get("reworded"):
                probs.append(f"{lab}: a heard question keeps the buyer's words unchanged (quote: '{quote[:60]}'); "
                             "if you reworded it for an assistant, set reworded: true and keep the quote")
            elif q.get("reworded") and not says_what(t):
                probs.append(f"{lab}: a reworded question must carry the offer words or the place, so an assistant knows what is asked")
        # the buyer's exact words are kept as typed, question mark or not; anything else must read as a question
        if not exact and not is_question(t):
            probs.append(f"{lab}: reads as a keyword string, not a question a buyer would type")
        if exact and not says_what(t):
            if TO_VENDOR.search(t) or not is_question(t):
                probs.append(f"{lab}: this is a message to the business, not a question for an assistant: pasted into ChatGPT it names no "
                             "service and no place. Keep the quote, reword the text as a buyer would ask an assistant "
                             "(with the offer words and the place), and set reworded: true")
            else:
                warns.append(f"{lab}: names neither the offer words nor a place; an assistant may answer it without any business in mind")
        if tag == "derived" and offer and not any(has_words(t, w) or has_words(q.get("source", ""), w) for w in offer):
            probs.append(f"{lab}: a derived question names the offer words it was built from in its text or source")
    for i in range(len(kept)):
        for j in range(i + 1, len(kept)):
            if jaccard(kept[i].get("text", ""), kept[j].get("text", "")) >= 0.8:
                probs.append(f"near duplicates: '{kept[i]['text'][:45]}' and '{kept[j]['text'][:45]}'")
    fams = {q.get("family") for q in kept}
    if len(fams) < 3:
        warns.append(f"only {len(fams)} question families; a panel usually spans at least three")
    # number and choose what runs first: heard first, then one per family, then the rest in order
    for n, q in enumerate(kept, 1):
        q["id"] = f"Q{n}"
    order = [q for q in kept if q.get("tag") == "heard"]
    for f in FAMILIES:
        for q in kept:
            if q.get("family") == f and q not in order:
                order.append(q)
                break
    order += [q for q in kept if q not in order]
    if panel.get("run_first"):
        want = [x for x in panel["run_first"]]
        chosen = [q for q in kept if q["id"] in want or q.get("text") in want]
        order = chosen + [q for q in order if q not in chosen]
    local = bool(panel.get("local", bool(locs)) and locs)
    has_loc = lambda q: any(has_words(q["text"], l, need_all=True) for l in locs)  # noqa: E731
    first = order[:RUN_FIRST]
    if local:
        # the quick five carry the place at least three times, as buyers ask with the place in: move place-bearing
        # questions up inside the run-first set, keeping the founder's order otherwise
        quick = first[:QUICK]
        need = min(3, len(quick)) - sum(has_loc(q) for q in quick)
        if need > 0:
            spare_loc = [q for q in order[QUICK:] if has_loc(q)][:need]
            drop = [q for q in reversed(quick) if not has_loc(q)][:len(spare_loc)]
            quick = [q for q in quick if q not in drop] + spare_loc
            order = quick + [q for q in order if q not in quick]
    for rank, q in enumerate(order, 1):
        q["priority"] = "run first" if rank <= RUN_FIRST else "spare"
        q["quick"] = rank <= QUICK
    if local:
        run1 = [q for q in kept if q["priority"] == "run first"]
        qk = [q for q in kept if q["quick"]]
        if sum(has_loc(q) for q in run1) < min(3, len(run1)):
            probs.append(f"only {sum(has_loc(q) for q in run1)} of the questions run first name a place ({', '.join(locs[:4])}); "
                         "a local business needs at least three, as buyers ask with the place in")
        elif sum(has_loc(q) for q in qk) < min(3, len(qk)):
            probs.append(f"only {sum(has_loc(q) for q in qk)} of the five quick questions name a place; add place-bearing questions")
    branded = panel.get("branded") or []
    if len(branded) != 3:
        probs.append(f"{len(branded)} branded questions; the panel carries exactly three (what you do, what you charge or how you compare, where you are and who you serve)")
    for k, b in enumerate(branded, 1):
        t = (b.get("text") if isinstance(b, dict) else str(b)) or ""
        if not any(norm(x) in norm(t) or fold(x) in fold(t) for x in biz):
            probs.append(f"branded question '{t[:50]}' does not name the business")
        if isinstance(b, dict):
            b["id"] = f"B{k}"
    panel["branded"] = [b if isinstance(b, dict) else {"id": f"B{k}", "text": b} for k, b in enumerate(branded, 1)]
    return probs, warns


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["suggest", "validate"])
    ap.add_argument("panel", nargs="?")
    ap.add_argument("--intake")
    ap.add_argument("--source", action="append", default=[])
    ap.add_argument("--out")
    a = ap.parse_args()
    if a.mode == "suggest":
        if not a.intake:
            stop("give --intake intake.json (category, buyer, locations, alternatives).")
        for fam, q in suggest(load_json(a.intake, "the intake file")):
            print(f"SUGGEST {fam}: {q}")
        print("Derived candidates only. Rewrite each in the buyers' own words and language, keep the ones a buyer would ask, tag them derived.")
        return 0
    if not a.panel:
        stop("give the panel file: python3 scripts/queries.py validate panel.json --source paste.txt")
    panel = load_json(a.panel, "the panel file")
    if not a.source:
        stop("give at least one --source file: the text the founder pasted or said, so heard questions can be traced.")
    sources = [read_text(s, "a source file") for s in a.source]
    probs, warns = validate(panel, sources)
    for p in probs:
        print("PROBLEM:", p)
    for w in warns:
        print("WARN:", w)
    kept = [q for q in panel["questions"] if not q.get("cut")]
    if not probs:
        for q in kept:
            print(f"{q['id']} [{q['family']}, {q['tag']}, {q['priority']}{', quick' if q['quick'] else ''}] {q['text']}")
        for b in panel["branded"]:
            print(f"{b['id']} [branded, accuracy check] {b['text']}")
        heard = sum(q.get("tag") == "heard" for q in kept)
        print(f"PANEL: {len(kept)} questions ({heard} heard, {len(kept) - heard} derived), "
              f"{sum(q['priority'] == 'run first' for q in kept)} to run first, 3 branded; "
              f"{sum(1 for q in panel['questions'] if q.get('cut'))} cut")
        if a.out:
            save_json(a.out, panel)
    print(f"{len(probs)} problems, {len(warns)} warnings")
    return 1 if probs else 0


if __name__ == "__main__":
    sys.exit(main())
