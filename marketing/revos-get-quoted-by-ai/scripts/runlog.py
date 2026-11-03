#!/usr/bin/env python3
"""The query test workbook: write the run sheet, read the founder's results, score them honestly.

Usage:
  python3 scripts/runlog.py sheet --settings settings.json --panel panel-checked.json --facts facts.json --out-dir <out>   (or --out file.xlsx)
        [--baseline baseline.json] [--proxy proxy.json]
      A workbook with every run laid out to fill in (Questions, Runs, Results, Panel, Sources, Accuracy,
      How to run, and Search proxy when given). Live formulas, with their values stored beside them.
  python3 scripts/runlog.py score --settings settings.json --panel panel-checked.json --facts facts.json
        --results <runs .xlsx/.csv/.txt> --out ai-query-test.xlsx --json-out results.json [--baseline baseline.json]
      Reads results in any column order (yes/ja/oui/1/x), scores them and rewrites the workbook with the runs in.
  python3 scripts/runlog.py wilson X N        the 95% range for X of N

Rules: a rate is always written "x of y, n equals y"; fewer than 3 runs is UNKNOWN; PASS when named in at
least half the runs, FAIL below half; the 95% Wilson range sits beside every rate; a change against the
baseline is called "moved" only when the two ranges do not overlap, otherwise "no clear change". The test
cannot show that a page change caused a change. Branded questions check accuracy and are never counted
in the headline. Exit 0 done, 1 when nothing could be scored, 2 with STOP. No network calls.
"""
import argparse
import csv
import io
import math
import os
import re
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import MONEY_RE, domain_of, fmt_date, fold, load_json, norm, parse_date, read_text, same_word, save_json, slug, spell, stop  # noqa: E402
import office as O  # noqa: E402
from locale_numbers import find_currency, parse_money, Ambiguous, Unreadable  # noqa: E402

Z = 1.96
MIN_RUNS = 3
YES = {"yes", "y", "ja", "j", "oui", "si", "sí", "true", "1", "x", "✓", "✔", "yep", "named", "cited"}
NO = {"no", "n", "nee", "nein", "non", "false", "0", "-", "nope", "not named", "nah"}
AGAINST = {"against", "tegen", "dagegen", "contre", "en contra", "warned against", "recommended against"}
ENGINES = [(r"chat\s?gpt|openai|gpt", "ChatGPT"), (r"perplex", "Perplexity"), (r"gemini|bard", "Gemini"),
           (r"ai ?overview|ai ?mode|google", "Google AI answers"), (r"copilot|bing", "Copilot"), (r"claude", "Claude"),
           (r"grok", "Grok"), (r"meta ai", "Meta AI"), (r"deepseek", "DeepSeek"), (r"you\.com", "You.com")]
HEADERS = {
    "question": ["q", "q#", "#", "no", "question", "question number", "qid", "query", "prompt", "vraag", "frage", "pregunta"],
    "engine": ["engine", "assistant", "assistent", "ai", "ki", "ia", "tool", "platform", "model", "app", "where asked", "moteur", "motor"],
    "run": ["run", "run #", "run number", "attempt", "try", "poging", "versuch"],
    "date": ["date", "datum", "day", "when", "fecha"],
    "location": ["location", "place", "where", "plaats", "city", "ort"],
    "named": ["named", "mentioned", "brand mentioned", "us named", "genoemd", "mention", "were we named", "named?", "genannt", "erwähnt",
              "cité", "nommé", "mencionado", "nombrado"],
    "cited": ["cited", "listed my site", "my site listed", "site listed", "our site listed", "our site cited", "site cited", "link to us", "geciteerd", "own site cited", "cited?", "zitiert", "source citée", "citado"],
    "recommended": ["recommended", "recommend", "shortlist", "aanbevolen", "recommended?", "empfohlen", "recommandé", "recomendado"],
    "framing": ["framing", "tone", "how framed", "how it was framed", "framed"],
    "sources": ["sources", "sources listed", "cited sources", "bronnen", "links", "domains", "source", "source1", "source 1", "quellen",
                "quelle", "fuentes", "sites listed", "urls", "websites"],
    "said": ["said", "what it said", "what it said about us", "notes", "answer", "comment", "opmerking", "about us"],
}
STD_ORDER = ["question", "question_text", "engine", "run", "date", "location", "named", "cited", "recommended", "framing", "sources", "said"]
DIRECTORY = ["zomato", "justdial", "sulekha", "indiamart", "urbancompany", "gelbeseiten", "dasoertliche", "das-oertliche", "11880",
             "myhammer", "check24", "werkenntdenbesten", "pagesjaunes", "paginasamarillas", "habitissimo", "yelp", "clutch.co", "goodfirms", "trustpilot", "maps.google", "google.com/maps", "tripadvisor", "yell.com",
             "checkatrade", "houzz", "bark.com", "thumbtack", "angi", "homeadvisor", "g2.com", "capterra", "upwork", "fiverr",
             "linkedin", "facebook", "instagram", "truelocal", "hotfrog", "yellowpages", "bbb.org", "productreview",
             "hipages", "oneflare", "glassdoor", "crunchbase", "werkspot", "trustoo", "nextdoor", "zocdoc", "sortlist",
             "designrush", "dribbble", "behance", "directory", "listing", "reviews", "unbiased", "vouchedfor", "xing", "kvk"]
MEDIA = ["news", "times", "herald", "guardian", "bbc", "forbes", "abc.net", "journal", "magazine", "tribune", "cnn", "reuters",
         "post.com", "gazette", "nos.nl", "nrc.nl", "smh.com", "theage", "gulfnews", "khaleejtimes", "thestar"]
FORUM = ["reddit", "quora", "forum", "community", "stackexchange", "whirlpool", "tweakers"]
VIDEO = ["youtube", "youtu.be", "vimeo", "tiktok"]


def wilson(x, n):
    if n <= 0:
        return None, None
    p = x / n
    den = 1 + Z * Z / n
    centre = p + Z * Z / (2 * n)
    half = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n))
    return max(0.0, (centre - half) / den), min(1.0, (centre + half) / den)


def rate_text(x, n):
    return "no runs" if n == 0 else f"{x} of {n}, n equals {n}"


def pct(v):
    return "" if v is None else f"{round(v * 100)}%"


def movement(cur, base):
    """'moved up', 'moved down' or 'no clear change', from non-overlapping 95% ranges only."""
    if not base or not cur or cur[1] < MIN_RUNS or base[1] < MIN_RUNS:
        return "not comparable"
    cl, ch = wilson(*cur)
    bl, bh = wilson(*base)
    if cl > bh:
        return "moved up"
    if ch < bl:
        return "moved down"
    return "no clear change"


def engine_name(text):
    t = str(text or "").strip().lower()
    for pat, name in ENGINES:
        if re.search(pat, t):
            return name
    return str(text or "").strip() or None


def yn(v):
    if v is None:
        return None
    t = str(v).strip().lower().rstrip(".")
    if t == "":
        return None
    if t in YES or t.startswith("yes"):
        return "yes"
    if t in AGAINST or "against" in t:
        return "against"
    if t in NO or t.startswith("no"):
        return "no"
    return "?"


# ---------------------------------------------------------------- reading results

def _rows_from_file(path):
    if path.lower().endswith((".xlsx", ".xlsm")):
        try:
            book = O.read_xlsx(path)
        except ValueError as e:
            stop(f"{e}. Save the workbook again (or export the Runs sheet as CSV) and send it back.")
        name = next((n for n in book if n.lower() == "runs"), None)
        if name is None:
            name = max(book, key=lambda n: len(book[n]))
        rows = book[name]
        return [[("" if c is None else c) for c in r] for r in rows]
    text = read_text(path, "the results file")
    if not text.strip():
        stop("the results file is empty. Send the workbook back, a CSV export of the Runs sheet, or paste the rows.")
    sample = "\n".join(text.splitlines()[:10])
    delim = max([",", ";", "\t", "|"], key=lambda d: sample.count(d))
    rows = list(csv.reader(io.StringIO(text), delimiter=delim))
    return [[c.strip() for c in r] for r in rows if any(c.strip() for c in r)]


def _header_map(row):
    m = {}
    for i, cell in enumerate(row):
        c = norm(cell)
        if re.fullmatch(r"(sources?|quellen?|fuentes?|bronnen?)\s?\d+", c) and "sources" in m:
            m.setdefault("sources_extra", []).append(i)  # source2, source3: read with the first source column
            continue
        for key, names in HEADERS.items():
            if key in m:
                continue
            if c in [norm(x) for x in names] or (len(c) > 3 and any(c.startswith(norm(x)) for x in names if len(x) > 3)):
                m[key] = i
                break
    return m


def read_results(path, panel, order="DMY", today=None):
    rows = _rows_from_file(path)
    hi, hmap = None, {}
    for i, r in enumerate(rows[:15]):
        m = _header_map(r)
        if "question" in m and ("named" in m or "engine" in m):
            hi, hmap = i, m
            break
    if hi is None:
        if rows and len(rows[0]) >= 9:
            hi, hmap = -1, {k: i for i, k in enumerate(STD_ORDER)}
        else:
            stop("could not find the columns. Send the workbook back as it was, or put a header row with at least "
                 "Question, Engine and Named.")
    allq = [q for q in panel["questions"] if not q.get("cut")] + panel.get("branded", [])
    out, skipped = [], []
    counters = {}
    for r in rows[hi + 1:]:
        def g(k):
            i = hmap.get(k)
            return r[i] if i is not None and i < len(r) else ""
        qraw = str(g("question")).strip()
        if not qraw and not any(str(c).strip() for c in r):
            continue
        q = None
        m = re.fullmatch(r"(?i)\s*([QB])?\s*(\d+)\s*", qraw)
        if m:
            pref = (m.group(1) or "Q").upper()
            q = next((x for x in allq if x.get("id") == f"{pref}{int(m.group(2))}"), None)
        if q is None and qraw:
            best = max(allq, key=lambda x: _sim(qraw, x.get("text", "")))
            if _sim(qraw, best.get("text", "")) >= 0.6:
                q = best
        if q is None:
            skipped.append(f"'{qraw[:40]}': not a question in the panel")
            continue
        eng = engine_name(g("engine"))
        if not eng:
            skipped.append(f"{q['id']}: no engine named")
            continue
        named = yn(g("named"))
        if named == "?":
            skipped.append(f"{q['id']} {eng}: 'Named' reads '{g('named')}', not yes or no")
            continue
        key = (q["id"], eng)
        counters[key] = counters.get(key, 0) + 1
        try:
            run_no = int(float(g("run"))) if str(g("run")).strip() else counters[key]
        except ValueError:
            run_no = counters[key]
        d = parse_date(g("date"), order, today)
        out.append({"q": q["id"], "text": q.get("text", ""), "engine": eng, "run": run_no, "date": d,
                    "date_raw": str(g("date")), "location": str(g("location") or ""), "named": named,
                    "cited": yn(g("cited")) if yn(g("cited")) != "?" else None,
                    "recommended": yn(g("recommended")) if yn(g("recommended")) != "?" else None,
                    "framing": {"favorable": "favourable", "positive": "favourable", "positiv": "favourable", "positief": "favourable",
                                "negative": "against", "negativ": "against", "negatief": "against"}.get(
                        str(g("framing") or "").strip().lower(), str(g("framing") or "").strip().lower()), "sources": " ".join([str(g("sources") or "")] + [str(r[j]) for j in hmap.get("sources_extra", []) if j < len(r)]),
                    "said": str(g("said") or "")})
    return out, skipped


def _sim(a, b):
    sa, sb = set(norm(a).split()), set(norm(b).split())
    return len(sa & sb) / max(1, len(sa | sb))


# ---------------------------------------------------------------- scoring

def classify(domain, own, competitors):
    d = domain.lower()
    if own and (d == own or d.endswith("." + own)):
        return "own"
    for c in competitors:
        cd = domain_of(c.get("domain", "")) if isinstance(c, dict) else ""
        if cd and (d == cd or d.endswith("." + cd)):
            return "competitor"
    for group, words in (("directory or review site", DIRECTORY), ("forum", FORUM), ("video", VIDEO), ("media", MEDIA)):
        if any(w in d for w in words):
            return group
    return "other"


def score(runs, panel, settings, facts, baseline):
    pq = {q["id"]: q for q in panel["questions"] if not q.get("cut")}
    engines = list(dict.fromkeys(list(settings.get("engines") or []) + [r["engine"] for r in runs]))
    recorded = [r for r in runs if r["named"] in ("yes", "no")]
    cells = []
    for qid, q in pq.items():
        for e in engines:
            rs = [r for r in recorded if r["q"] == qid and r["engine"] == e]
            n = len(rs)
            x = sum(r["named"] == "yes" for r in rs)
            c = sum(r["cited"] == "yes" for r in rs)
            rec = sum(r["recommended"] == "yes" for r in rs)
            ag = sum(r["recommended"] == "against" or r["framing"] == "against" for r in rs)
            lo, hi = wilson(x, n)
            verdict = "UNKNOWN" if n < MIN_RUNS else ("PASS" if x >= n / 2 else "FAIL")
            frames = {}
            for r in rs:
                if r["named"] == "yes" and r["framing"]:
                    frames[r["framing"]] = frames.get(r["framing"], 0) + 1
            cells.append({"q": qid, "text": q["text"], "engine": e, "n": n, "named": x, "cited": c, "recommended": rec,
                          "against": ag, "low": lo, "high": hi, "verdict": verdict, "framing": frames,
                          "flag": "seen in some runs" if verdict == "FAIL" and x > 0 else ("" if n >= MIN_RUNS else
                                                                                         f"{n} run(s) recorded; 3 needed")})
    pr = [r for r in recorded if r["q"] in pq]
    N, X = len(pr), sum(r["named"] == "yes" for r in pr)
    C, R = sum(r["cited"] == "yes" for r in pr), sum(r["recommended"] == "yes" for r in pr)
    head = {"n": N, "named": X, "cited": C, "recommended": R, "range": wilson(X, N),
            "text": f"named in {X} of {N} runs, n equals {N}" if N else "no runs yet"}
    per_engine = {}
    for e in engines:
        er = [r for r in pr if r["engine"] == e]
        if er:
            ex = sum(r["named"] == "yes" for r in er)
            per_engine[e] = {"n": len(er), "named": ex, "range": wilson(ex, len(er)),
                             "cited": sum(r["cited"] == "yes" for r in er), "recommended": sum(r["recommended"] == "yes" for r in er)}
    move, notes = "no baseline", []
    if baseline:
        move = movement((X, N), (baseline.get("named", 0), baseline.get("n", 0)))
        if set(baseline.get("engines") or []) and set(baseline.get("engines")) != set(per_engine):
            notes.append(f"engines differ from the baseline ({', '.join(baseline['engines'])} then, {', '.join(per_engine)} now)")
        if baseline.get("questions") and set(baseline["questions"]) != {r["q"] for r in pr}:
            notes.append("the questions run differ from the baseline")
    # dates and window
    ds = sorted(r["date"] for r in recorded if r["date"])
    if ds and (ds[-1] - ds[0]).days > 3:
        notes.append(f"runs spread over {(ds[-1] - ds[0]).days + 1} days ({fmt_date(ds[0], settings.get('date_order', 'DMY'))} to "
                     f"{fmt_date(ds[-1], settings.get('date_order', 'DMY'))}); the protocol asks for a 72 hour window")
    undated = sum(1 for r in recorded if not r["date"])
    if undated:
        notes.append(f"{undated} run(s) have no readable date")
    # sources
    own = domain_of(settings.get("domain", ""))
    comps = settings.get("competitors") or []
    tally = {}
    for r in runs:
        for tok in re.split(r"[,;\s]+", r["sources"]):
            tok = tok.strip().strip("()[]<>\"'")
            if not tok or "." not in tok or len(tok) < 4:
                continue
            d = domain_of(tok)
            if not re.match(r"^[a-z0-9.-]+\.[a-z]{2,}$", d):
                continue
            t = tally.setdefault(d, {"domain": d, "group": classify(d, own, comps), "count": 0, "questions": set()})
            t["count"] += 1
            t["questions"].add(r["q"])
    sources = sorted(({**v, "questions": sorted(v["questions"])} for v in tally.values()), key=lambda v: (-v["count"], v["domain"]))
    accuracy = check_accuracy(runs, facts, settings, panel)
    failing = sorted({c["q"] for c in cells if c["verdict"] == "FAIL"})
    unknown = [c for c in cells if c["verdict"] == "UNKNOWN" and c["n"] > 0]
    return {"cells": cells, "headline": head, "per_engine": per_engine, "movement": move, "notes": notes,
            "sources": sources, "accuracy": accuracy, "failing": failing, "engines": engines,
            "unknown_cells": [f"{c['q']} {c['engine']} ({c['n']} run(s))" for c in unknown],
            "baseline": baseline, "dates": [d.isoformat() for d in ds[:1] + ds[-1:]]}


PLACE_PAT = re.compile(r"\b(?:based|located|headquartered|gevestigd|ansässig|situé|ubicad[oa]|offices?|office|is|are|sits?|works?|operates?|"
                       r"serves?|covers?|studio|shop|firm|business|company|agency|team)?\s*"
                       r"(?:in|at|from|near|around|outside|aus|bei|nahe|im|te|uit|bij|nabij|à|près de|en|cerca de|desde)\s+"
                       r"(?:the\s+)?([A-ZÀ-Ý][\w'-]+(?:[ -][A-ZÀ-Ý][\w'-]+)?)")
NOT_PLACES = {"english", "hindi", "german", "deutsch", "dutch", "french", "spanish", "google", "maps", "google maps", "instagram",
              "facebook", "linkedin", "whatsapp", "youtube", "chatgpt", "perplexity", "gemini", "copilot", "claude", "reddit", "yelp",
              "justdial", "zomato", "the", "a", "an", "our", "your", "their", "its", "this", "that", "general", "person", "house",
              "studio", "january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
              "november", "december", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "i", "we"}
WHERE_WORDS = re.compile(r"(?i)\b(where|located|based|which (city|area|town)|wo\b|waar|où|dónde|donde|serve|serves|bedient)\b")


def _place_ok(place, reg_places, extra_ok):
    p = fold(place)
    if not p or p in NOT_PLACES or any(same_word(p, x) or p in x or x in p for x in reg_places):
        return True
    return any(p in fold(x) for x in extra_ok)


def check_accuracy(runs, facts, settings, panel=None):
    """Compare what assistants said about the business with the fact register. Returns rows with kind
    'wrong' (a place or price that is not in the register) or 'missing' (an answer to where-you-are names no place).
    Claude still reads every branded answer itself: a script cannot catch every wrong description."""
    out = []
    reg = facts.get("facts", [])
    places = [f for f in reg if f.get("kind") in ("location", "area", "address") and f.get("status") == "confirmed"]
    reg_places = {fold(w) for f in places for w in re.split(r"[,;/()]| and | und | en | et | y |\bund\b", f.get("value", "")) if fold(w)}
    reg_places |= {fold(w) for f in places for w in re.findall(r"[A-ZÀ-Ý][\w'-]+", f.get("value", ""))}
    biz = [settings.get("business", "")] + list(settings.get("aliases") or [])
    extra_ok = biz + [c.get("name", "") if isinstance(c, dict) else str(c) for c in settings.get("competitors") or []]
    reg_places |= {fold(x) for x in list((panel or {}).get("locations") or []) + list(settings.get("locations") or []) if fold(x)}
    prices = [f for f in reg if f.get("kind") == "price" and f.get("status") in ("confirmed", "declined")]
    dec = settings.get("decimal")
    price_vals = set()
    for f in prices:
        for m in re.finditer(r"[\d][\d.,' ]*", f.get("value", "")):
            try:
                price_vals.add(round(parse_money(m.group(0).strip(), dec)[0], 2))
            except (Ambiguous, Unreadable, ValueError):
                pass
    branded = {b.get("id"): b.get("text", "") for b in (panel or {}).get("branded", []) if isinstance(b, dict)}
    reg_txt = "; ".join(f["value"] for f in places) or "no place in your register"
    for r in runs:
        said = r.get("said") or ""
        if not said.strip():
            continue
        found = []
        for m in PLACE_PAT.finditer(said):
            place = m.group(1).strip()
            if _place_ok(place, reg_places, extra_ok):
                if fold(place) not in NOT_PLACES:
                    found.append(place)
                continue
            found.append(place)
            if reg_places:
                out.append({"q": r["q"], "engine": r["engine"], "run": r["run"], "fact": "location", "kind": "wrong",
                            "register": reg_txt, "said": said.strip()[:160],
                            "problem": f"names '{place}' as where you are or work"})
        is_where = r["q"] in branded and (WHERE_WORDS.search(branded[r["q"]]) or r["q"] == "B3")
        if is_where and reg_places and not found and not any(x in fold(said) for x in reg_places if len(x) > 3):
            out.append({"q": r["q"], "engine": r["engine"], "run": r["run"], "fact": "location", "kind": "missing",
                        "register": reg_txt, "said": said.strip()[:160], "problem": "no place stated"})
        for m in MONEY_RE.finditer(said):
            try:
                v = round(parse_money(m.group(0), dec)[0], 2)
            except (Ambiguous, Unreadable, ValueError):
                continue
            if prices and v not in price_vals:
                out.append({"q": r["q"], "engine": r["engine"], "run": r["run"], "fact": "price", "kind": "wrong",
                            "register": "; ".join(f["value"] for f in prices), "said": said.strip()[:160],
                            "problem": f"states a price of '{m.group(0)}'"})
            elif not prices and r["q"].startswith("B"):
                out.append({"q": r["q"], "engine": r["engine"], "run": r["run"], "fact": "price", "kind": "wrong",
                            "register": "no price published", "said": said.strip()[:160],
                            "problem": f"states a price of '{m.group(0)}' you have not published"})
    return out


# ---------------------------------------------------------------- workbook

def build_workbook(path, settings, panel, facts, runs=None, res=None, baseline=None, proxy=None):
    order = settings.get("date_order", "DMY")
    datefmt = {"MDY": "mmm d, yyyy", "YMD": "yyyy-mm-dd"}.get(order, "d mmm yyyy")
    engines = settings.get("engines") or ["ChatGPT"]
    nruns = int(settings.get("runs", 3))
    quick = bool(settings.get("quick"))
    qs = [q for q in panel["questions"] if not q.get("cut")]
    branded = panel.get("branded", [])
    run_qs = [q for q in qs if (q.get("quick") if quick else q.get("priority") == "run first")]
    run_engines = engines[:1] if quick else engines
    eng = settings.get("english") or ""
    sheets = []

    how = O.Sheet("How to run")
    how.widths = {1: 110}
    lines = [
        (f"How to run your test: {settings.get('business', '')}", O.S_TITLE),
        (f"{len(run_qs)} questions x {len(run_engines)} assistant(s) x {nruns} runs = {len(run_qs) * len(run_engines) * nruns} runs, "
         f"plus the 3 branded questions once on each assistant. Do them all within 72 hours.", O.S_WRAP),
        ("1. Open a private or logged-out window, with chat history and memory off where the assistant allows it. Use search mode where there is one.", O.S_WRAP),
        ("2. Paste each question exactly as written. Never add your business name to a question that does not already have it.", O.S_WRAP),
        ("3. Start a new chat for every run. Fill one row of the Runs sheet per run: date, where you are, and the yellow columns.", O.S_WRAP),
        ("4. Named: is your business named in the answer? Cited: is one of your own pages listed as a source? Recommended: are you put forward as an option to choose (or warned against)?", O.S_WRAP),
        (spell("5. Framing: favourable, neutral, hedged or against. Sources: paste the web addresses the answer lists. What it said: anything it says about you, word for word where you can.", eng), O.S_WRAP),
        ("6. Send the workbook back (or a CSV of the Runs sheet, or the rows pasted in a message). Fewer than 3 runs for a question and assistant reads UNKNOWN, never a pass or a fail.", O.S_WRAP),
        ("Results update as you fill in rows: rates are written 'x of y, n equals y' with a 95% range beside them. One run is one sample of an answer that changes every time.", O.S_NOTE),
    ]
    for i, (t, s) in enumerate(lines, 1):
        how.set(i, 1, t, s)
        how.heights[i] = 30 if s == O.S_WRAP else None
    how.heights = {k: v for k, v in how.heights.items() if v}
    sheets.append(how)

    qsh = O.Sheet("Questions")
    qsh.widths = {1: 6, 2: 60, 3: 12, 4: 10, 5: 40, 6: 26, 7: 14}
    qsh.freeze_row = 2
    qsh.row(1, ["#", "Question (paste exactly)", "Family", "Source", "Where it came from", "Page that should answer it", "Run"], O.S_HEAD)
    r = 2
    for q in qs:
        qsh.row(r, [q["id"], q["text"], q["family"], q["tag"], q.get("source", ""), q.get("page") or "no page yet",
                    ("quick panel" if q.get("quick") else "run first") if q.get("priority") == "run first" else "spare"], O.S_WRAP)
        r += 1
    for b in branded:
        qsh.row(r, [b["id"], b["text"], "branded", "accuracy", "checks what assistants say about you", "", "once each"], O.S_WRAP)
        r += 1
    cuts = [q for q in panel["questions"] if q.get("cut")]
    if cuts:
        r += 1
        qsh.set(r, 1, "Cut by you", O.S_BOLD)
        for q in cuts:
            r += 1
            qsh.row(r, ["", q["text"], q.get("family", ""), q.get("tag", ""), q.get("cut_reason", "")], O.S_NOTE)
    sheets.append(qsh)

    rsh = O.Sheet("Runs")
    rsh.widths = {1: 6, 2: 44, 3: 14, 4: 6, 5: 13, 6: 14, 7: 9, 8: 9, 9: 13, 10: 13, 11: 36, 12: 40}
    rsh.freeze_row = 2
    rsh.row(1, ["#", "Question", "Engine", "Run", "Date", "Location", "Named", "Cited", "Recommended", "Framing",
                "Sources listed", "What it said about you"], O.S_HEAD)
    laid = []
    if runs:
        laid = sorted(runs, key=lambda x: (x["q"][0] != "Q", int(re.sub(r"\D", "", x["q"]) or 0), x["engine"], x["run"]))
    else:
        for q in run_qs:
            for e in run_engines:
                for k in range(1, nruns + 1):
                    laid.append({"q": q["id"], "text": q["text"], "engine": e, "run": k})
        for b in branded:
            for e in run_engines:
                laid.append({"q": b["id"], "text": b["text"], "engine": e, "run": 1})
    r = 2
    for x in laid:
        rsh.row(r, [x["q"], x.get("text", ""), x["engine"], x["run"]], O.S_TEXT)
        rsh.set(r, 4, x["run"], O.S_INT)
        if x.get("date"):
            rsh.set(r, 5, x["date"], O.S_DATE)
        for c, k in ((6, "location"), (7, "named"), (8, "cited"), (9, "recommended"), (10, "framing"), (11, "sources"), (12, "said")):
            v = x.get(k)
            rsh.set(r, c, v if v not in (None, "?") else None, O.S_STATUS if c in (7, 8, 9, 10) else O.S_WRAP)
        r += 1
    last = max(r - 1, 2) + 200
    rsh.validations = [(f"G2:H{last}", ["yes", "no"]), (f"I2:I{last}", ["yes", "no", "against"]),
                       (f"J2:J{last}", [spell("favourable", eng), "neutral", "hedged", "against"])]
    rsh.autofilter = f"A1:L{max(r - 1, 2)}"
    sheets.append(rsh)

    # Results
    res_sh = O.Sheet("Results")
    res_sh.widths = {1: 6, 2: 44, 3: 14, 4: 9, 5: 8, 6: 8, 7: 12, 8: 22, 9: 9, 10: 9, 11: 10, 12: 22}
    res_sh.freeze_row = 2
    res_sh.row(1, ["#", "Question", "Engine", "Runs", "Named", "Cited", "Recommended", "Named rate", "Range low",
                   "Range high", "Verdict", "Note"], O.S_HEAD)
    cellmap = {(c["q"], c["engine"]): c for c in (res or {}).get("cells", [])}
    res_engines = (res or {}).get("engines") or engines
    r = 2
    first_res = 2
    for q in qs:
        for e in res_engines:
            c = cellmap.get((q["id"], e), {"n": 0, "named": 0, "cited": 0, "recommended": 0, "low": None, "high": None,
                                           "verdict": "UNKNOWN", "flag": "0 run(s) recorded; 3 needed"})
            crit = f'Runs!$A:$A,$A{r},Runs!$C:$C,$C{r}'
            res_sh.row(r, [q["id"], q["text"], e], O.S_WRAP)
            res_sh.set(r, 4, c["n"], O.S_INT, f'COUNTIFS({crit},Runs!$G:$G,"?*")')
            res_sh.set(r, 5, c["named"], O.S_INT, f'COUNTIFS({crit},Runs!$G:$G,"yes")')
            res_sh.set(r, 6, c["cited"], O.S_INT, f'COUNTIFS({crit},Runs!$H:$H,"yes")')
            res_sh.set(r, 7, c["recommended"], O.S_INT, f'COUNTIFS({crit},Runs!$I:$I,"yes")')
            res_sh.set(r, 8, rate_text(c["named"], c["n"]), O.S_TEXT,
                       f'IF(D{r}=0,"no runs",E{r}&" of "&D{r}&", n equals "&D{r})')
            res_sh.set(r, 9, c["low"] if c["low"] is not None else "", O.S_PCT, _wilson_f(f"E{r}", f"D{r}", -1))
            res_sh.set(r, 10, c["high"] if c["high"] is not None else "", O.S_PCT, _wilson_f(f"E{r}", f"D{r}", 1))
            res_sh.set(r, 11, c["verdict"], O.S_BOLD, f'IF(D{r}<3,"UNKNOWN",IF(E{r}>=D{r}/2,"PASS","FAIL"))')
            note = "seen in some runs" if c["verdict"] == "FAIL" and c["named"] > 0 else ""
            res_sh.set(r, 12, note, O.S_TEXT, f'IF(AND(K{r}="FAIL",E{r}>0),"seen in some runs","")')
            r += 1
    last_res = r - 1
    res_sh.set(r + 1, 1, "PASS: named in at least half the runs. FAIL: named in fewer than half, with at least 3 runs. "
                         "UNKNOWN: fewer than 3 runs. The range is where the true rate probably sits (95% Wilson range).", O.S_NOTE)
    res_sh.merges.append(f"A{r + 1}:L{r + 1}")
    res_sh.heights[r + 1] = 30
    sheets.append(res_sh)

    # Panel headline
    ps = O.Sheet("Panel")
    ps.widths = {1: 30, 2: 10, 3: 10, 4: 30, 5: 11, 6: 11, 7: 20}
    ps.set(1, 1, "Panel headline", O.S_TITLE)
    ps.row(3, ["", "Runs", "Named", "Named rate", "Range low", "Range high", "Against the baseline"], O.S_HEAD)
    head = (res or {}).get("headline") or {"n": 0, "named": 0, "cited": 0, "recommended": 0, "range": (None, None)}
    rng = f"Results!$D${first_res}:$D${last_res}"
    ps.set(4, 1, "All questions, all engines", O.S_BOLD)
    ps.set(4, 2, head["n"], O.S_INT, f"SUM({rng})")
    ps.set(4, 3, head["named"], O.S_INT, f"SUM(Results!$E${first_res}:$E${last_res})")
    ps.set(4, 4, ("named in %d of %d runs, n equals %d" % (head["named"], head["n"], head["n"])) if head["n"] else "no runs yet",
           O.S_TEXT, 'IF(B4=0,"no runs yet","named in "&C4&" of "&B4&" runs, n equals "&B4)')
    lo, hi = head["range"] if head["range"] else (None, None)
    ps.set(4, 5, lo if lo is not None else "", O.S_PCT, _wilson_f("C4", "B4", -1))
    ps.set(4, 6, hi if hi is not None else "", O.S_PCT, _wilson_f("C4", "B4", 1))
    rowb = 5
    if baseline:
        bx, bn = baseline.get("named", 0), baseline.get("n", 0)
        bl, bh = wilson(bx, bn)
        ps.set(5, 1, f"Baseline, {fmt_date(parse_date(baseline.get('date'), 'DMY'), order) or baseline.get('date', '')}", O.S_BOLD)
        ps.set(5, 2, bn, O.S_INT)
        ps.set(5, 3, bx, O.S_INT)
        ps.set(5, 4, f"named in {bx} of {bn} runs, n equals {bn}", O.S_TEXT)
        ps.set(5, 5, bl if bl is not None else "", O.S_PCT)
        ps.set(5, 6, bh if bh is not None else "", O.S_PCT)
        mv = (res or {}).get("movement") or "not comparable"
        ps.set(4, 7, mv, O.S_BOLD, 'IF(OR(B4<3,B5<3),"not comparable",IF(E4>F5,"moved up",IF(F4<E5,"moved down","no clear change")))')
        rowb = 6
    r = rowb + 1
    ps.row(r, ["By engine", "Runs", "Named", "Named rate", "Range low", "Range high", "Cited"], O.S_HEAD)
    for e in res_engines:
        r += 1
        pe = ((res or {}).get("per_engine") or {}).get(e, {"n": 0, "named": 0, "cited": 0, "range": (None, None)})
        ps.set(r, 1, e, O.S_TEXT)
        ps.set(r, 2, pe["n"], O.S_INT, f'SUMIF(Results!$C${first_res}:$C${last_res},A{r},{rng})')
        ps.set(r, 3, pe["named"], O.S_INT, f'SUMIF(Results!$C${first_res}:$C${last_res},A{r},Results!$E${first_res}:$E${last_res})')
        ps.set(r, 4, rate_text(pe["named"], pe["n"]), O.S_TEXT, f'IF(B{r}=0,"no runs",C{r}&" of "&B{r}&", n equals "&B{r})')
        elo, ehi = pe["range"] if pe.get("range") else (None, None)
        ps.set(r, 5, elo if elo is not None else "", O.S_PCT, _wilson_f(f"C{r}", f"B{r}", -1))
        ps.set(r, 6, ehi if ehi is not None else "", O.S_PCT, _wilson_f(f"C{r}", f"B{r}", 1))
        ps.set(r, 7, pe.get("cited", 0), O.S_INT, f'SUMIF(Results!$C${first_res}:$C${last_res},A{r},Results!$F${first_res}:$F${last_res})')
    r += 2
    for t in ["Moved means the two ranges do not overlap. Anything else is no clear change, however the numbers look.",
              "This test shows whether rates changed, never why. A page going live and a change in rates can happen together by chance.",
              "Rates are snapshots: assistants change their answers from run to run and month to month."]:
        ps.set(r, 1, t, O.S_NOTE)
        ps.merges.append(f"A{r}:G{r}")
        r += 1
    sheets.append(ps)

    ss = O.Sheet("Sources")
    ss.widths = {1: 34, 2: 24, 3: 8, 4: 30}
    ss.row(1, ["Domain", "Group", "Times listed", "Questions"], O.S_HEAD)
    srcs = (res or {}).get("sources") or []
    if not srcs:
        ss.set(2, 1, "No runs yet. The domains the assistants list will be counted here.", O.S_NOTE)
    for i, s in enumerate(srcs, 2):
        ss.row(i, [s["domain"], s["group"]], O.S_TEXT)
        ss.set(i, 3, s["count"], O.S_INT, f'COUNTIF(Runs!$K:$K,"*"&A{i}&"*")')
        ss.set(i, 4, ", ".join(s["questions"]), O.S_TEXT)
    sheets.append(ss)

    acc = O.Sheet("Accuracy")
    acc.widths = {1: 18, 2: 40, 3: 12, 4: 50, 5: 30}
    acc.row(1, ["Fact", "Your fact register says", "Status", "What an assistant said", "Problem"], O.S_HEAD)
    r = 2
    flagged = (res or {}).get("accuracy") or []
    for f in facts.get("facts", []):
        hits = [a for a in flagged if a["fact"] == f.get("kind")]
        acc.row(r, [f.get("label") or f.get("kind", ""), f.get("value", ""), f.get("status", "")], O.S_WRAP)
        if hits and f.get("kind") in ("location", "price"):
            acc.set(r, 4, f"{len(hits)} run(s): " + hits[0]["said"], O.S_WRAP)
            acc.set(r, 5, hits[0]["problem"] + f" ({', '.join(sorted({h['engine'] for h in hits}))})", O.S_WRAP)
        elif res:
            acc.set(r, 4, "nothing contradicting it was recorded", O.S_NOTE)
        else:
            acc.set(r, 4, "not checked yet: fill in 'What it said' for the branded questions", O.S_NOTE)
        r += 1
    sheets.append(acc)

    if proxy:
        px = O.Sheet("Search proxy")
        px.widths = {1: 6, 2: 50, 3: 50, 4: 30}
        px.set(1, 1, f"A web search of each question without your name, run by Claude on "
                     f"{fmt_date(parse_date(proxy.get('date'), 'DMY'), order) or proxy.get('date', '')}. Not an assistant's answer; never scored.", O.S_NOTE)
        px.merges.append("A1:D1")
        px.row(2, ["#", "Question", "Domains that came up", "Businesses named"], O.S_HEAD)
        for i, row in enumerate(proxy.get("rows", []), 3):
            px.row(i, [row.get("q", ""), row.get("text", ""), ", ".join(row.get("domains", [])), ", ".join(row.get("named", []))], O.S_WRAP)
        sheets.append(px)
    paper = settings.get("paper") or "A4"
    O.write_xlsx(path, sheets, title=f"AI query test: {settings.get('business', '')}", date_fmt=datefmt, paper=paper)
    return len(laid)


def _wilson_f(x, n, sign):
    s = "-" if sign < 0 else "+"
    return (f'IF({n}<1,"",({x}/{n}+1.96^2/(2*{n}){s}1.96*SQRT({x}/{n}*(1-{x}/{n})/{n}+1.96^2/(4*{n}^2)))/(1+1.96^2/{n}))')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["sheet", "score", "wilson"])
    ap.add_argument("args", nargs="*")
    ap.add_argument("--settings")
    ap.add_argument("--panel")
    ap.add_argument("--facts")
    ap.add_argument("--results")
    ap.add_argument("--baseline")
    ap.add_argument("--proxy")
    ap.add_argument("--out")
    ap.add_argument("--out-dir", help="instead of --out: the workbook is named ai-query-test_<business slug>_<date>.xlsx in this folder")
    ap.add_argument("--json-out")
    a = ap.parse_args()
    if a.mode == "wilson":
        try:
            x, n = int(a.args[0]), int(a.args[1])
        except (IndexError, ValueError):
            stop("give two whole numbers: runlog.py wilson 3 48")
        if n < 1 or x < 0 or x > n:
            stop("X must be between 0 and N, and N at least 1.")
        lo, hi = wilson(x, n)
        print(f"{rate_text(x, n)}: range {pct(lo)} to {pct(hi)}{'' if n >= MIN_RUNS else ' (UNKNOWN: fewer than 3 runs)'}")
        return 0
    if not a.out and a.out_dir and a.settings:
        _s = load_json(a.settings, "the settings file")
        _d = parse_date(_s.get("today")) if _s.get("today") else date.today()
        a.out = os.path.join(a.out_dir, f"ai-query-test_{slug(_s.get('business') or 'business')}_{(_d or date.today()).isoformat()}.xlsx")
    for k in ("settings", "panel", "facts", "out"):
        if not getattr(a, k):
            stop(f"--{k} is needed. See the usage at the top of scripts/runlog.py.")
    settings = load_json(a.settings, "the settings file")
    panel = load_json(a.panel, "the checked panel")
    facts = load_json(a.facts, "the fact register")
    if not any(q.get("id") for q in panel.get("questions", [])):
        stop("the panel has no question numbers. Run queries.py validate with --out first and use that file.")
    if not settings.get("engines"):
        stop("settings.json has no engines. Default: [\"ChatGPT\", \"Perplexity\"].")
    try:
        if not 1 <= int(settings.get("runs", 3)) <= 10:
            stop("runs per question must be between 1 and 10 (3 is the minimum for a verdict).")
    except (TypeError, ValueError):
        stop("settings 'runs' must be a whole number such as 3.")
    baseline = load_json(a.baseline, "the baseline file") if a.baseline else None
    proxy = load_json(a.proxy, "the proxy file") if a.proxy else None
    today = parse_date(settings.get("today")) if settings.get("today") else date.today()
    if a.mode == "sheet":
        n = build_workbook(a.out, settings, panel, facts, baseline=baseline, proxy=proxy)
        print(f"WROTE {a.out}: {n} rows laid out to fill in; no rates (no runs yet)")
        return 0
    if not a.results:
        stop("--results is needed: the workbook, a CSV of the Runs sheet, or the pasted rows saved as a text file.")
    runs, skipped = read_results(a.results, panel, settings.get("date_order", "DMY"), today)
    for s in skipped[:20]:
        print("SKIPPED:", s)
    recorded = [r for r in runs if r["named"] in ("yes", "no")]
    if not recorded:
        build_workbook(a.out, settings, panel, facts, baseline=baseline, proxy=proxy)
        print("STOP: no runs with Named filled in. Every rate stays UNKNOWN. Ask the founder to fill in the yellow columns and send it back.")
        return 1
    future = [r for r in recorded if r["date"] and r["date"] > today + timedelta(days=1)]
    if future:
        print(f"WARN: {len(future)} run(s) dated in the future (for example {future[0]['date_raw']}); check the date order")
    res = score(runs, panel, settings, facts, baseline)
    build_workbook(a.out, settings, panel, facts, runs=runs, res=res, baseline=baseline, proxy=proxy)
    h = res["headline"]
    lo, hi = h["range"]
    print(f"HEADLINE: {h['text']} (range {pct(lo)} to {pct(hi)}); cited {h['cited']} of {h['n']}; recommended {h['recommended']} of {h['n']}")
    if baseline:
        bl, bh = wilson(baseline.get("named", 0), baseline.get("n", 0))
        print(f"BASELINE: named in {baseline.get('named')} of {baseline.get('n')} runs, n equals {baseline.get('n')} "
              f"(range {pct(bl)} to {pct(bh)}), {baseline.get('date', '')}")
        print(f"MOVEMENT: {res['movement']} (moved only when the ranges do not overlap); the test cannot show what caused it")
    for e, pe in res["per_engine"].items():
        print(f"ENGINE: {e}: {rate_text(pe['named'], pe['n'])} (range {pct(pe['range'][0])} to {pct(pe['range'][1])}), cited {pe['cited']}")
    for c in res["cells"]:
        if c["n"]:
            print(f"CELL {c['verdict']}: {c['q']} {c['engine']}: {rate_text(c['named'], c['n'])}{(' (' + c['flag'] + ')') if c['flag'] else ''}")
    for c in res["accuracy"]:
        print(f"ACCURACY {c.get('kind', 'wrong').upper()}: {c['q']} {c['engine']} run {c['run']}: {c['problem']}; your register says {c['register']}")
    print("READ: the branded answers yourself as well; a script cannot catch every wrong description. Add any it missed to kit.next.accuracy.")
    for s in res["sources"][:12]:
        print(f"SOURCE: {s['domain']} ({s['group']}) listed {s['count']} time(s) for {', '.join(s['questions'])}")
    for n in res["notes"]:
        print("NOTE:", n)
    print(f"FAILING: {', '.join(res['failing']) or 'none'}; UNKNOWN with some runs: {', '.join(res['unknown_cells']) or 'none'}")
    print(f"WROTE {a.out}: {len(recorded)} runs scored, {len(skipped)} row(s) skipped")
    if a.json_out:
        out = dict(res)
        out["headline"] = {**h, "range": list(h["range"])}
        out["per_engine"] = {e: {**v, "range": list(v["range"])} for e, v in res["per_engine"].items()}
        save_json(a.json_out, out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
