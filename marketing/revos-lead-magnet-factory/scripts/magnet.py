#!/usr/bin/env python3
"""Lead Magnet Factory: one spec file in, a checked lead magnet and its launch pack out.

Usage:
  python3 scripts/magnet.py validate <spec.json>
  python3 scripts/magnet.py simulate <spec.json> [--json-out sim.json]
  python3 scripts/magnet.py render   <spec.json> --out <folder>
  python3 scripts/magnet.py audit    <page.html> --spec <spec.json> [--page scorecard|optin]
  python3 scripts/magnet.py result   <spec.json> --answers "q1=0,q2=2,...,f1=1"
  python3 scripts/magnet.py build    <spec.json> --out <folder> [--pdf]
  python3 scripts/magnet.py init     --format scorecard|checklist|guide --out <spec.json> [--source <paste file>]
                                     [--name ..] [--business ..] [--country ..] [--currency ..] [--signoff ..]

init writes a spec with every field in place and "FILL: what goes here" in each value; validate refuses any FILL
line still left, so a half-written spec can never build.

build runs everything in order and writes nothing while any check fails: validate, simulate (scorecards),
the copy and claim checks (check_copy.py), the email checks (emails.py), then renders the files, audits the
page and prints the five facts the chat summary needs.

Files written by build (names fixed; the date is the spec date):
  scorecard  <topic>-scorecard_YYYY-MM-DD.html and <topic>-scorecard-printable_YYYY-MM-DD.docx
  checklist  <topic>-checklist_YYYY-MM-DD.docx (and .pdf with --pdf when LibreOffice is present)
  guide      <topic>-one-page-guide_YYYY-MM-DD.docx (and .pdf the same way)
  always     lead-magnet-launch-pack_YYYY-MM-DD.docx
  only with a form address or embed from the founder: opt-in-page_YYYY-MM-DD.html

Exit 0 done; 1 PROBLEM lines (nothing written; fix the spec); 2 STOP (do what it says).
Standard library only. No network calls. The page it writes makes none either.
"""
import argparse
import html
import itertools
import json
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(os.path.dirname(HERE), "assets")
VERDICT_WORDS = {"fail", "failing", "failed", "failure", "broken", "bad", "poor", "weak", "terrible", "worst",
                 "hopeless", "doomed", "disaster", "critical", "danger", "red", "dead", "lost", "chaos", "mess",
                 "toxic", "beginner", "amateur", "loser", "flop", "sinking", "bleeding", "crisis"}
MAX_SIMULATED = 1024
SHARE_MIN, SHARE_MAX = 10.0, 60.0
WPM = 200
SECONDS_PER_QUESTION = 6


def walk(obj, path=""):
    """Every (path, value) pair in a nested spec, for the scaffold check."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if not str(k).startswith("_"):
                yield from walk(v, f"{path}.{k}" if path else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk(v, f"{path}[{i}]")
    else:
        yield path, obj


def norm(s):
    s = str(s or "").lower().replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = re.sub(r"[^\w\s']", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def found_in(quote, text):
    return norm(quote) in norm(text) if quote else False


# ------------------------------------------------------------------ validate
def range_numbers(label, decimal):
    """Numbers inside an option label like 'Under 1.000', '15k to 50k a month', '$15,000 to $30,000'."""
    vals = []
    for m in re.finditer(r"[$€£¥₹]?\s?\d[\d.,']*\s?(?:k|m|mn|lakh|crore)?\b", label, re.I):
        t = m.group(0).strip()
        try:
            v, _cur, _n = C.read_money(t, decimal)
            vals.append(v)
        except (C.LN.Ambiguous, C.LN.Unreadable):
            continue
    return vals


def check_ranges(q, decimal, P, W):
    """P and W are the callables that record a PROBLEM and a WARN line (list.append works)."""
    labels = [o.get("label", "") for o in q.get("options") or []]
    numbered = [(i, range_numbers(lab, decimal)) for i, lab in enumerate(labels)]
    numbered = [(i, v) for i, v in numbered if v]
    if len(numbered) < 2:
        return
    prev_hi = None
    for i, vals in numbered:
        lo, hi = min(vals), max(vals)
        if prev_hi is not None and lo < prev_hi:
            low_word = re.search(r"\b(under|below|less than|fewer than|up to)\b", labels[i], re.I)
            if not low_word:
                P(f"{q.get('id')}: option '{labels[i]}' overlaps the option before it. Ranges must run "
                  "low to high with no overlap.")
        prev_hi = hi if prev_hi is None else max(prev_hi, hi)
    if any(re.search(r"[$€£¥₹]|\bmoney\b|\brs\.?\s?\d|revenue|turnover|sales|budget|spend|income|fee|lakh|crore", lab + " " +
                     q.get("text", ""), re.I) for lab in labels):
        if not any(re.search(r"not sure|don'?t know|prefer not", lab, re.I) for lab in labels):
            W(f"{q.get('id')}: a money range with no 'Not sure' option. Readers quit on money questions "
              "they cannot answer; add one unless the founder said otherwise.")
    style_problem(labels, decimal, q.get("id"), P)


def style_problem(labels, decimal, where, P):
    for lab in labels:
        if decimal == "comma" and re.search(r"\b\d{1,3},\d{3}\b", lab):
            P(f"{where}: '{lab}' writes thousands with a comma, but the founder writes 1.200 style. "
              "Write it the founder's way.")
        if decimal == "dot" and re.search(r"\b\d{1,3}\.\d{3}\b(?![.,]\d)", lab):
            P(f"{where}: '{lab}' writes thousands with a dot, but the founder writes 1,200 style. "
              "Write it the founder's way.")


def score_bounds(questions):
    lo = sum(min(o["points"] for o in q["options"]) for q in questions)
    hi = sum(max(o["points"] for o in q["options"]) for q in questions)
    return lo, hi


def wc(text):
    return len(C.words(text))


def validate(spec, quiet=False):
    problems, warns = [], []
    P, W = problems.append, warns.append
    fills = [path for path, v in walk(spec) if isinstance(v, str) and v.strip().startswith("FILL:")]
    if fills:
        P(f"{len(fills)} scaffold values still say FILL: {', '.join(fills[:8])}{' ...' if len(fills) > 8 else ''}. "
          "Write each one from what the founder gave, or remove optional ones.")
        if not quiet:
            print("PROBLEM:", problems[0])
        return problems, warns, {"decimal": None}
    fmt = spec.get("format")
    if fmt not in C.FORMATS:
        raise C.Stop(f"format must be one of {', '.join(C.FORMATS)}; got '{fmt}'.")
    f = spec.get("founder") or {}
    for k in ("name", "business", "currency", "signoff"):
        if not str(f.get(k) or "").strip():
            P(f"founder.{k} is missing")
    if not re.fullmatch(r"[A-Za-z]{2}", str(f.get("country") or "")):
        W("founder.country is not a two-letter country code: paper size and date order fall back to A4 and day "
          "first. Say this default to the founder or ask once.")
    try:
        C.parse_date(spec.get("date"), "spec date")
    except C.Stop:
        P("date must be the build date, written YYYY-MM-DD")
    src = C.sources_text(spec)
    if not src.strip():
        P("sources is empty: save what the founder pasted or said (exactly as given) to a file and name it in "
          "`sources`, or record their replies in `founder_replies`. Every question, item and claim is traced to it.")
    decimal = C.decimal_style(spec, [src])
    offer = spec.get("offer") or {}
    if offer.get("price_as_typed"):
        try:
            v, cur, _ = C.read_money(offer["price_as_typed"], decimal)
        except C.LN.Ambiguous as e:
            raise C.Stop(f"ASK: {e}") from None
        except C.LN.Unreadable:
            raise C.Stop(f"ASK: I could not read the price '{offer['price_as_typed']}'. Ask the founder to write it "
                         "again as a plain figure.") from None
        if v < 1:
            raise C.Stop(f"ASK: the price reads as {v:g}, which cannot be right. Ask the founder what one client pays.")
        if offer.get("price_value") is not None and abs(float(offer["price_value"]) - v) > 0.5:
            P(f"offer.price_value {offer['price_value']} does not match '{offer['price_as_typed']}' read as {v:g}")
        offer["_price"] = v
    t = spec.get("topic") or {}
    for k in ("slug", "problem", "format_reason", "not_given_away"):
        if not str(t.get(k) or "").strip():
            P(f"topic.{k} is missing")
    if t.get("source_line"):
        if not found_in(t["source_line"], src) and not t.get("inferred"):
            P(f"topic.source_line \"{t['source_line'][:80]}\" is not in the founder's material. Quote it exactly, or "
              "set topic.inferred to true and say so in the chat.")
    elif not t.get("inferred"):
        P("topic.source_line is missing: quote the line the topic came from, or set topic.inferred to true")
    if t.get("inferred"):
        W("topic is inferred, not quoted: say so in the chat summary")
    if len(t.get("runners_up") or []) < 2:
        W("topic.runners_up: name the two runners-up and why they lost (launch pack section 2)")
    facts = spec.get("facts") or []
    for i, fa in enumerate(facts):
        if not str(fa.get("claim") or "").strip() or not str(fa.get("source") or "").strip():
            P(f"facts[{i}]: every fact needs the claim and where it comes from")
        elif re.search(r"\b(heard|somewhere|not sure|unknown|i think|read it|don'?t know)\b", fa["source"], re.I):
            P(f"facts[{i}]: '{fa['source']}' is not a source. Leave the claim out, or ask the founder where it "
              "comes from.")
    look = spec.get("look") or {}
    text, bg = look.get("text") or "#111111", look.get("background") or "#FFFFFF"
    accent = look.get("accent") or text
    accent_text = look.get("accent_text") or bg
    muted = look.get("muted") or "#4D4D4D"
    for name, c in (("text", text), ("background", bg), ("accent", accent), ("accent_text", accent_text),
                    ("muted", muted)):
        if not C.is_hex(c):
            P(f"look.{name} '{c}' is not a hex colour like #1F3A5F")
    if not problems:
        for a, b, what in ((text, bg, "text on the background"), (muted, bg, "small grey text on the background"),
                           (accent_text, accent, "button text on the button")):
            r = C.contrast(a, b)
            if r < 4.5:
                P(f"look: {what} is {r:.1f} to 1; at least 4.5 to 1 is needed. Use a darker shade or plain black.")
        r = C.contrast(accent, bg)
        if r < 3:
            P(f"look: the accent on the background is {r:.1f} to 1; at least 3 to 1 is needed for the button edge.")
    info = {"decimal": decimal}
    if fmt == "scorecard":
        validate_scorecard(spec, src, decimal, P, W, info)
    elif fmt == "checklist":
        validate_checklist(spec, src, P, W, info)
    else:
        validate_guide(spec, src, P, W, info)
    validate_launch(spec, P, W, info)
    if not quiet:
        for x in problems:
            print("PROBLEM:", x)
        for x in warns:
            print("WARN:", x)
    return problems, warns, info


def validate_scorecard(spec, src, decimal, P, W, info):
    m = spec.get("magnet") or {}
    for k in ("title", "promise", "who_for", "door", "cta"):
        if not m.get(k):
            P(f"magnet.{k} is missing")
    qs = m.get("questions") or []
    if len(qs) != 5:
        P(f"a scorecard has exactly five scored questions; this one has {len(qs)}")
    ids = set()
    lines = []
    for q in qs:
        qid = q.get("id") or "?"
        if qid in ids:
            P(f"question id {qid} is used twice")
        ids.add(qid)
        if not str(q.get("text") or "").strip():
            P(f"{qid}: question text is missing")
        if not str(q.get("source") or "").strip():
            P(f"{qid}: every question needs a source (the line or reply it came from)")
        if q.get("source_quote") and not found_in(q["source_quote"], src):
            P(f"{qid}: source_quote \"{q['source_quote'][:70]}\" is not in the founder's material")
        opts = q.get("options") or []
        if not 3 <= len(opts) <= 4:
            P(f"{qid}: needs three or four options; has {len(opts)}")
        pts = [o.get("points") for o in opts]
        if any(not isinstance(p, int) or isinstance(p, bool) or p < 0 for p in pts):
            P(f"{qid}: every option needs whole-number points of 0 or more")
        elif len(set(pts)) != len(pts):
            P(f"{qid}: two options carry the same points; each option must score differently")
        for k in ("strength", "strength_mid", "fix_low", "fix_high"):
            if not str(q.get(k) or "").strip():
                P(f"{qid}: {k} line is missing" + (" (what is true for a reader who picked an upper answer but not "
                                                   "the top one: 'You know a typical order', not 'You know each "
                                                   "order')" if k == "strength_mid" else ""))
            else:
                lines.append((f"{qid}.{k}", q[k]))
        check_ranges(q, decimal, P, W)
        if re.search(r"\bexact(ly)?\b|\bprecise\b|\bto the (dollar|euro|pound|cent)\b", q.get("text", ""), re.I):
            W(f"{qid}: asks for an exact figure; ranges with a 'Not sure' option finish better")
    seen = {}
    for lab, line in lines:
        k = norm(line)
        if k in seen:
            P(f"{lab} repeats {seen[k]} word for word; each line must say something different")
        seen[k] = lab
    fqs = m.get("fit_questions") or []
    if len(fqs) > 2:
        P(f"at most two fit questions; this one has {len(fqs)}")
    for q in fqs:
        qid = q.get("id") or "?"
        if qid in ids:
            P(f"question id {qid} is used twice")
        ids.add(qid)
        opts = q.get("options") or []
        if not 2 <= len(opts) <= 4:
            P(f"{qid}: a fit question needs two to four options")
        if any(not isinstance(o.get("fit"), bool) for o in opts):
            P(f"{qid}: every fit option needs \"fit\": true or false")
        elif not any(o["fit"] for o in opts) or all(o["fit"] for o in opts):
            P(f"{qid}: a fit question needs at least one fit and one not-fit option")
        if not str(q.get("source") or "").strip():
            P(f"{qid}: every fit question needs a source (the founder's own 'who should not call me', or 'default "
              "fit question, said aloud')")
        check_ranges(q, decimal, P, W)
    signals = len(fqs) + (1 if str(m.get("who_not_for") or "").strip() else 0)
    if signals < 2:
        P(f"fit is tested {signals} time(s); at least two fit signals are needed (fit questions, plus the "
          "who_not_for line). With no disqualifier from the founder, add the default readiness question and say so.")
    if fqs and not str(m.get("not_a_fit") or "").strip():
        P("not_a_fit is missing: the line a reader sees in place of the call to action when a fit answer says the "
          "offer is not for them")
    if not str(m.get("strength_fallback") or "").strip():
        P("strength_fallback is missing: the honest 'What is working' line for a reader whose answers are all low")
    tiers = m.get("tiers") or []
    if not 3 <= len(tiers) <= 5:
        P(f"three to five tiers are needed; this one has {len(tiers)}")
    if qs and not any("points" not in o for q in qs for o in q.get("options") or []):
        try:
            lo, hi = score_bounds(qs)
        except (TypeError, ValueError):
            lo = hi = None
        if lo is not None and tiers:
            info["score_range"] = (lo, hi)
            ordered = sorted(tiers, key=lambda x: (x.get("min", 0)))
            if [x.get("name") for x in ordered] != [x.get("name") for x in tiers]:
                P("list the tiers from the lowest score to the highest")
            expect = lo
            for x in ordered:
                a, b = x.get("min"), x.get("max")
                if not isinstance(a, int) or not isinstance(b, int) or a > b:
                    P(f"tier '{x.get('name')}': min and max must be whole numbers with min no higher than max")
                    break
                if a != expect:
                    P(f"tier '{x.get('name')}' starts at {a}; it must start at {expect} so there is no gap or overlap")
                expect = b + 1
            else:
                if expect - 1 != hi:
                    P(f"the top tier ends at {expect - 1}; it must end at the maximum score, {hi}")
    names = [norm(x.get("name")) for x in tiers]
    if len(set(names)) != len(names):
        P("two tiers share a name")
    descs = [norm(x.get("description")) for x in tiers]
    if len(set(descs)) != len(descs):
        P("two tiers share a description")
    for x in tiers:
        n = wc(x.get("description"))
        if not 40 <= n <= 70:
            P(f"tier '{x.get('name')}' description is {n} words; write 40 to 70")
        bad = set(norm(x.get("name")).split()) & VERDICT_WORDS
        if bad:
            P(f"tier name '{x.get('name')}' uses a verdict word ({', '.join(sorted(bad))}). Name what is true at "
              "that level, not a judgement.")
    door = m.get("door") or {}
    if not str(door.get("question") or "").strip() or not str(door.get("sentence") or "").strip():
        P("door needs a question and one sentence: the next question the scorecard cannot answer")
    cta = m.get("cta") or {}
    if not str(cta.get("label") or "").strip() and not str(cta.get("line") or "").strip():
        P("cta needs a label (and a link), or a reply line when there is no link")
    if not str(cta.get("line_top_tier") or "").strip():
        P("cta.line_top_tier is missing: the line a reader in the top tier sees in place of cta.line. They have few "
          "gaps, so do not tell them the gaps look familiar; say honestly whether a call is worth their time yet.")
    elif norm(cta.get("line_top_tier")) == norm(cta.get("line")):
        P("cta.line_top_tier repeats cta.line; a top-tier reader needs a different, honest line")
    link = str(cta.get("link") or "").strip()
    if link and not re.fullmatch(r"(https://[^\s\"'<>]+\.[^\s\"'<>]+|mailto:[^\s\"'<>@]+@[^\s\"'<>]+)", link):
        P(f"cta.link '{link}' must be a full https:// address or a mailto: address")
    if link and re.search(r"[?&](score|tier|answer|result|q\d)=", link, re.I):
        P("cta.link carries a score or answer; no score or answer ever goes in a link")
    if not link:
        W("no call link: the page asks readers to reply to the email that sent them the link. Say this default "
          "aloud.")
    # time to finish
    text_words = sum(wc(q.get("text")) + wc(q.get("label")) + sum(wc(o.get("label")) for o in q.get("options") or []) for q in qs + fqs)
    secs = text_words / WPM * 60 + SECONDS_PER_QUESTION * (len(qs) + len(fqs))
    info["seconds"] = round(secs)
    if secs > 180:
        P(f"the questions take about {secs / 60:.1f} minutes to answer; cut words until it is under three")
    stated = m.get("minutes")
    if stated is not None and (not isinstance(stated, (int, float)) or stated > 3 or stated * 60 < secs):
        P(f"magnet.minutes says {stated}; the estimate is {max(1, round(secs / 60 + 0.49))}. State an honest time of "
          "three minutes or under.")


def validate_checklist(spec, src, P, W, info):
    c = spec.get("checklist") or {}
    for k in ("title", "who_for", "not_covered", "next_step"):
        if not str(c.get(k) or "").strip():
            P(f"checklist.{k} is missing")
    items, held = [], []
    for s in c.get("sections") or []:
        for it in s.get("items") or []:
            (held if it.get("need") else items).append(it)
    info["held"] = held
    info["items"] = len(items)
    if not 10 <= len(items) <= 15:
        P(f"a checklist has 10 to 15 items ready to publish; this one has {len(items)}"
          + (f" ({len(held)} held as [NEED: confirm])" if held else ""))
    if len(items) > 10 and len(c.get("sections") or []) < 2:
        P("above ten items, group them under short headings (two sections or more)")
    for it in items + held:
        label = (it.get("text") or "?")[:50]
        if not str(it.get("text") or "").strip():
            P("a checklist item has no text")
        if not str(it.get("source") or "").strip():
            P(f"item '{label}': every item needs a source (a pasted line, a founder reply, or 'founder confirmed')")
        if it.get("source_quote") and not found_in(it["source_quote"], src):
            P(f"item '{label}': source_quote \"{it['source_quote'][:60]}\" is not in the founder's material")
        det = str(it.get("detail") or "")
        sentences = [x for x in re.split(r"(?<=[.?!])\s+", det.strip()) if x]
        if not 1 <= len(sentences) <= 2:
            P(f"item '{label}': the detail must be one or two sentences; it has {len(sentences)}")
    m = re.match(r"\s*(\d+)[- ]point\b", c.get("title") or "", re.I)
    if m and int(m.group(1)) != len(items):
        P(f"the title says {m.group(1)} points but {len(items)} items are ready to publish")
    total = sum(wc(it.get("text")) + wc(it.get("detail")) for it in items)
    info["words"] = total
    if total > 700:
        P(f"the items run to {total} words; a checklist fits two pages at about 700. Cut the details.")
    if c.get("minutes") is not None and c["minutes"] > 15:
        W("the checklist says it takes over 15 minutes; check that is honest and short enough")


def validate_guide(spec, src, P, W, info):
    g = spec.get("guide") or {}
    for k in ("title", "who_for", "idea", "example", "example_label", "next_step", "not_covered"):
        if not str(g.get(k) or "").strip():
            P(f"guide.{k} is missing")
    if g.get("example_label") and not re.search(r"example|illustrat|for instance", g["example_label"], re.I):
        P("guide.example_label must say plainly that the example is an example (or name the client the founder "
          "supplied, with their words)")
    steps = g.get("steps") or []
    if not 3 <= len(steps) <= 5:
        P(f"a one-page guide carries three to five steps; this one has {len(steps)}")
    for st in steps:
        if isinstance(st, dict) and not str(st.get("source") or "").strip():
            P(f"guide step '{str(st.get('text'))[:40]}' needs a source")
    total = wc(g.get("idea")) + wc(g.get("example")) + sum(wc(s.get("text") if isinstance(s, dict) else s) for s in steps)
    info["words"] = total
    if total > 550:
        P(f"the guide runs to {total} words; one page holds about 550")


def validate_launch(spec, P, W, info):
    la = spec.get("launch") or {}
    op = la.get("optin") or {}
    for k in ("headline", "subhead", "expectation", "button"):
        if not str(op.get(k) or "").strip():
            P(f"launch.optin.{k} is missing")
    if len(op.get("bullets") or []) != 3:
        P("launch.optin.bullets: write exactly three lines on what they will see")
    if re.fullmatch(r"\s*(download( now)?|submit|click here|get it now)\s*", op.get("button") or "", re.I):
        P(f"opt-in button '{op.get('button')}' says nothing; name what they get ('Send me the scorecard')")
    exp = op.get("expectation") or ""
    if exp and not re.search(r"unsubscribe", exp, re.I):
        P("the opt-in expectation line must say they can unsubscribe at any time")
    fields = [x.lower() for x in (op.get("fields") or ["First name", "Email"])]
    if len(fields) > 2:
        W(f"the opt-in form asks for {len(fields)} fields; first name and email is the default. Fit is tested "
          "inside the magnet, not on the form.")
    if op.get("form_action") and not re.fullmatch(r"https://[^\s\"'<>]+", op["form_action"]):
        P("launch.optin.form_action must be the full https address the founder's email tool gave them")
    ty = la.get("thankyou") or {}
    for k in ("headline", "body", "next_step"):
        if not str(ty.get(k) or "").strip():
            P(f"launch.thankyou.{k} is missing")
    rm = la.get("result_map") or []
    if spec.get("format") == "scorecard":
        tiers = [x.get("name") for x in (spec.get("magnet") or {}).get("tiers") or []]
        if [r.get("when") for r in rm] != tiers:
            P("launch.result_map needs one entry per tier, in tier order, with `when` set to the tier name")
    elif len(rm) < 2:
        P("launch.result_map needs at least two entries (what a reader's reply tells you)")
    for r in rm:
        for k in ("dealing_with", "ask", "next_step"):
            if not str(r.get(k) or "").strip():
                P(f"result_map '{r.get('when')}': {k} is missing")
    rules = la.get("rules") or {}
    if not rules.get("stops"):
        P("launch.rules.stops: say what stops the sequence (a booked call, a reply that signals interest)")
    if not rules.get("remove_before"):
        P("launch.rules.remove_before: who must be removed before the sequence is switched on (current clients)")


# ------------------------------------------------------------------ result logic (mirrored in the page)
def q_data(spec):
    m = spec["magnet"]
    out = []
    for q in m["questions"]:
        pts = [o["points"] for o in q["options"]]
        out.append({"id": q["id"], "p": pts, "min": min(pts), "max": max(pts)})
    return out


def compute(spec, picks, fit_picks=None):
    """picks: option index per scored question, in order. fit_picks: option index (or None) per fit question."""
    m = spec["magnet"]
    qd = q_data(spec)
    total, rels = 0, []
    for i, (q, idx) in enumerate(zip(qd, picks)):
        p = q["p"][idx]
        total += p
        rels.append((((p - q["min"]) / (q["max"] - q["min"])) if q["max"] > q["min"] else 1.0, i))
    asc = sorted(rels, key=lambda r: (r[0], r[1]))
    fix = asc[:3]
    rest = sorted(asc[3:], key=lambda r: (-r[0], r[1]))
    work = [r for r in rest if r[0] >= 0.5][:2]
    tier = next((t["name"] for t in m["tiers"] if t["min"] <= total <= t["max"]), None)
    top = bool(m["tiers"]) and tier == m["tiers"][-1]["name"]
    notfit = False
    for fq, idx in zip(m.get("fit_questions") or [], fit_picks or []):
        if idx is not None and fq["options"][idx]["fit"] is False:
            notfit = True
    return {
        "total": total, "tier": tier,
        "working": [m["questions"][r[1]]["id"] for r in work] or ["fallback"],
        "working_kind": ["full" if r[0] >= 1.0 or not m["questions"][r[1]].get("strength_mid") else "mid"
                         for r in work] or ["fallback"],
        "top_tier": top,
        "fix": [(m["questions"][r[1]]["id"], "low" if r[0] < 0.5 else "high") for r in fix],
        "fix_heading": "Fix these first" if any(r[0] < 0.5 for r in fix) else "Where to tighten next",
        "notfit": notfit,
    }


def simulate(spec, quiet=False):
    m = spec.get("magnet") or {}
    qs = m.get("questions") or []
    tiers = m.get("tiers") or []
    sizes = [len(q["options"]) for q in qs]
    n = 1
    for s in sizes:
        n *= s
    if n > MAX_SIMULATED:
        raise C.Stop(f"{n} answer sets is above the {MAX_SIMULATED} this check walks; five questions of three or four "
                     "options stay within it.")
    counts = {t["name"]: 0 for t in tiers}
    problems = []
    for picks in itertools.product(*[range(s) for s in sizes]):
        total = sum(qs[i]["options"][j]["points"] for i, j in enumerate(picks))
        hit = [t["name"] for t in tiers if t["min"] <= total <= t["max"]]
        if len(hit) != 1:
            problems.append(f"the answer set {list(picks)} totals {total} and lands in {len(hit)} tiers")
            break
        counts[hit[0]] += 1
    shares = {k: round(100.0 * v / n, 1) for k, v in counts.items()}
    for k, v in shares.items():
        if counts[k] == 0:
            problems.append(f"tier '{k}' is unreachable: no answer set lands in it")
        elif v < SHARE_MIN:
            problems.append(f"tier '{k}' holds {v}% of possible answer sets, under the {SHARE_MIN:g}% floor; widen it")
        elif v > SHARE_MAX:
            problems.append(f"tier '{k}' holds {v}% of possible answer sets, over the {SHARE_MAX:g}% ceiling; a tier "
                            "almost everyone lands in tells nobody anything")
    mid_total = 0.0
    for q in qs:
        pts = sorted(o["points"] for o in q["options"])
        k = len(pts)
        mid_total += pts[k // 2] if k % 2 else (pts[k // 2 - 1] + pts[k // 2]) / 2
    mid_r = int(mid_total + 0.5)
    mid_tier = next((t["name"] for t in tiers if t["min"] <= mid_r <= t["max"]), None)
    if len(tiers) >= 3 and mid_tier in (tiers[0]["name"], tiers[-1]["name"]):
        problems.append(f"a middle pattern of answers ({mid_total:g} points) lands in '{mid_tier}', an end tier. "
                        "Move the bands so an average reader lands in a middle tier.")
    lo, hi = score_bounds(qs)
    res = {"answer_sets": n, "counts": counts, "shares": shares, "middle_total": mid_total, "middle_tier": mid_tier,
           "min": lo, "max": hi, "problems": problems}
    if not quiet:
        print(f"Answer sets walked: {n}. Scores run {lo} to {hi}.")
        for t in tiers:
            print(f"  {t['name']} ({t['min']} to {t['max']}): {counts[t['name']]} sets, {shares[t['name']]}%")
        print(f"Middle pattern: {mid_total:g} points, lands in '{mid_tier}'.")
        for x in problems:
            print("PROBLEM:", x)
        print("These shares describe the arithmetic of the scoring, not real readers.")
    return res


# ------------------------------------------------------------------ render
FONT_STACK = 'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'


def e(s):
    return html.escape(str(s or ""), quote=True)


def css_vars(spec):
    look = spec.get("look") or {}
    text = look.get("text") or "#111111"
    bg = look.get("background") or "#FFFFFF"
    accent = look.get("accent") or text
    return {"%%TEXT%%": text, "%%BG%%": bg, "%%ACCENT%%": accent, "%%ACCENT_TEXT%%": look.get("accent_text") or bg,
            "%%MUTED%%": look.get("muted") or "#4D4D4D",
            "%%FONT%%": (look.get("font_stack") or FONT_STACK).replace("<", "").replace("{", "").replace("}", "")}


def lang_attr(spec):
    sp = ((spec.get("founder") or {}).get("spelling") or "").lower()
    return {"british": "en-GB", "american": "en-US", "australian": "en-AU", "canadian": "en-CA", "indian": "en-IN"}.get(
        sp, (spec.get("founder") or {}).get("language") or "en")


def render_scorecard(spec, out_path):
    m = spec["magnet"]
    tpl = C.read_text(os.path.join(ASSETS, "scorecard-template.html"))
    qs, fqs = m["questions"], m.get("fit_questions") or []
    total_q = len(qs)
    blocks = []
    for i, q in enumerate(qs, 1):
        opts = "".join(
            f'<label class="opt"><input type="radio" name="{e(q["id"])}" value="{j}"><span>{e(o["label"])}</span></label>'
            for j, o in enumerate(q["options"]))
        topic = f'<span class="qtopic">{e(q["label"])}</span>' if q.get("label") else ""
        blocks.append(f'<fieldset id="fs-{e(q["id"])}"><legend><span class="qnum">Question {i} of {total_q}</span>'
                      f'{topic}{e(q["text"])}</legend>{opts}</fieldset>')
    fit_html = ""
    if fqs:
        fb = []
        for q in fqs:
            opts = "".join(
                f'<label class="opt"><input type="radio" name="{e(q["id"])}" value="{j}" data-fit="{str(o["fit"]).lower()}">'
                f'<span>{e(o["label"])}</span></label>' for j, o in enumerate(q["options"]))
            fb.append(f'<fieldset id="fs-{e(q["id"])}"><legend>{e(q["text"])}</legend>{opts}</fieldset>')
        lead = "One last question" if len(fqs) == 1 else "Two last questions"
        who = "we" if (spec.get("founder") or {}).get("we") else "I"
        fit_html = (f'<div class="fit"><h2 class="fit-h">{lead}, so {who} can point you to the right next step</h2>'
                    f'<p class="meta">These do not change your score.</p>{"".join(fb)}</div>')
    data = {
        "q": [{"id": q["id"], "p": [o["points"] for o in q["options"]], "strength": q["strength"],
               "strength_mid": q.get("strength_mid") or q["strength"],
               "fix_low": q["fix_low"], "fix_high": q["fix_high"]} for q in qs],
        "f": [{"id": q["id"], "fit": [o["fit"] for o in q["options"]]} for q in fqs],
        "tiers": [{"name": t["name"], "min": t["min"], "max": t["max"], "desc": t["description"]} for t in m["tiers"]],
        "fallback": m["strength_fallback"],
    }
    data["max"] = sum(max(x["p"]) for x in data["q"])
    cta = m.get("cta") or {}
    link = (cta.get("link") or "").strip()
    top_line = cta.get("line_top_tier") or cta.get("line") or cta.get("label")
    if link:
        cta_html = (f'<p class="cta-line" id="r-cta-line">{e(cta.get("line"))}</p>' if cta.get("line") else "") + \
            f'<p class="cta-line" id="r-cta-top" hidden>{e(top_line)}</p>' + \
            f'<p><a class="button" id="r-cta-link" href="{e(link)}">{e(cta.get("label") or "Book a call")}</a></p>'
    else:
        cta_html = (f'<p class="cta-line" id="r-cta-line">{e(cta.get("line") or cta.get("label"))}</p>'
                    f'<p class="cta-line" id="r-cta-top" hidden>{e(top_line)}</p>')
    f = spec["founder"]
    footer = e(m.get("footer") or f"{f.get('name')}, {f.get('business')}")
    who = f'<p class="who">{e(m["who_for"])}</p>'
    if m.get("who_not_for"):
        who += f'<p class="who">{e(m["who_not_for"])}</p>'
    minutes = m.get("minutes") or 3
    count_words = {5: "five", 6: "six", 7: "seven"}.get(total_q, str(total_q))
    time_line = f"About {minutes} minutes. {count_words.capitalize()} questions" + \
        (f", then {'one' if len(fqs) == 1 else 'two'} about you" if fqs else "") + \
        ". Your answers stay on this page: nothing is sent or saved."
    repl = {
        "%%LANG%%": lang_attr(spec), "%%TITLE%%": e(m["title"]), "%%PROMISE%%": e(m["promise"]),
        "%%TIME%%": e(time_line), "%%WHO%%": who, "%%QUESTIONS%%": "".join(blocks), "%%FIT%%": fit_html,
        "%%NQ%%": str(total_q), "%%CTA%%": cta_html, "%%NOTFIT%%": e(m.get("not_a_fit") or ""),
        "%%DOOR_Q%%": e((m.get("door") or {}).get("question")), "%%DOOR_S%%": e((m.get("door") or {}).get("sentence")),
        "%%FOOTER%%": footer, "%%CREDIT%%": e(C.CREDIT), "%%AUTHOR%%": e(f.get("name")),
        "%%DATA%%": json.dumps(data, ensure_ascii=False).replace("</", "<\\/"),
    }
    repl.update(css_vars(spec))
    out = tpl
    for k, v in repl.items():
        out = out.replace(k, v)
    left = re.findall(r"%%[A-Z_]+%%", out)
    if left:
        raise C.Stop(f"the template kept {left}; the scorecard template in assets/ has been changed by hand")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(out)
    return out_path


def render_optin(spec, out_path, names):
    la = spec["launch"]
    op = la["optin"]
    tpl = C.read_text(os.path.join(ASSETS, "optin-template.html"))
    if op.get("embed"):
        form = op["embed"]
    else:
        fields = op.get("fields") or ["First name", "Email"]
        rows = []
        for fld in fields:
            low = fld.lower()
            nm = "email" if "mail" in low else "first_name" if "name" in low else C.slugify(fld).replace("-", "_")
            typ = "email" if nm == "email" else "text"
            auto = ' autocomplete="email"' if typ == "email" else ' autocomplete="given-name"'
            req = " required" if typ == "email" else ""
            rows.append(f'<label class="field"><span>{e(fld)}</span><input type="{typ}" name="{e(nm)}"{auto}{req}></label>')
        form = (f'<form method="post" action="{e(op["form_action"])}">{"".join(rows)}'
                f'<button type="submit">{e(op["button"])}</button></form>')
    bullets = "".join(f"<li>{e(b)}</li>" for b in op["bullets"])
    f = spec["founder"]
    repl = {"%%LANG%%": lang_attr(spec), "%%HEADLINE%%": e(op["headline"]), "%%SUBHEAD%%": e(op["subhead"]),
            "%%BULLETS%%": bullets, "%%FORM%%": form, "%%EXPECTATION%%": e(op["expectation"]),
            "%%SIGNOFF%%": e(op.get("signoff_line") or ""), "%%FOOTER%%": e(f"{f.get('name')}, {f.get('business')}"),
            "%%CREDIT%%": e(C.CREDIT), "%%AUTHOR%%": e(f.get("name"))}
    repl.update(css_vars(spec))
    out = tpl
    for k, v in repl.items():
        out = out.replace(k, v)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(out)
    return out_path


# ------------------------------------------------------------------ audit
PLACEHOLDER = re.compile(r"\[(?:NEED|YOUR|INSERT|ADD|LINK|NAME|TBC|TODO|STAT|CLIENT|URL|[A-Z][A-Z _]{2,})[^\]]*\]|%%[A-Z_]+%%"
                         r"|\{\{[^}]*\}\}|\[(?:need|your|insert|add|link|name)\b[^\]]*\]|(?i:lorem ipsum)|\bTODO\b|\bTBC\b"
                         r"|\bxxx\b")


def json_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from json_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from json_strings(v)
FALSE_SEND = re.compile(r"check your (inbox|email)|we('ve| have) (sent|emailed)|sent to your (inbox|email)|"
                        r"(is|are) on (its|their) way to your inbox|emailed (you|to you)|in your inbox", re.I)


def audit(path, spec, page="scorecard", quiet=False):
    t = C.read_text(path)
    problems, warns = [], []
    P = problems.append
    cta_link = ((spec.get("magnet") or {}).get("cta") or {}).get("link") or ""
    allowed = {cta_link} if cta_link else set()
    allowed_hosts = set()
    if page == "optin":
        op = (spec.get("launch") or {}).get("optin") or {}
        if op.get("form_action"):
            allowed.add(op["form_action"])
        for u in re.findall(r"https?://[^\s\"'<>)]+", op.get("embed") or ""):
            allowed_hosts.add(re.sub(r"^https?://([^/:]+).*$", r"\1", u))
    body = re.sub(r'<script type="application/json"[^>]*>.*?</script>', "", t, flags=re.S)
    for u in re.findall(r"(?:https?:)?//[^\s\"'<>)]+", body):
        if u.startswith("//") and not re.match(r"//[a-z0-9.-]+\.[a-z]{2,}", u, re.I):
            continue
        host = re.sub(r"^(?:https?:)?//([^/:]+).*$", r"\1", u)
        if u not in allowed and host not in allowed_hosts:
            P(f"web address in the page that is not the founder's own link: {u[:80]}")
    if page == "scorecard":
        for pat, why in ((r"\bfetch\s*\(", "fetch call"), (r"XMLHttpRequest", "XMLHttpRequest"),
                         (r"sendBeacon", "sendBeacon"), (r"WebSocket", "WebSocket"), (r"<form\b", "a form"),
                         (r"localStorage|sessionStorage|indexedDB|document\.cookie", "browser storage"),
                         (r"<script[^>]+\bsrc\s*=", "a script loaded from a file or address"),
                         (r"<link[^>]+rel=[\"']?stylesheet", "a stylesheet loaded from an address"),
                         (r"@import", "a CSS import"), (r"<iframe|<img[^>]+src=[\"']?https?:", "embedded remote content"),
                         (r"\.href\s*=|location\s*=|location\.(assign|replace)|window\.open", "the page changing a link")):
            if re.search(pat, t, re.I):
                P(f"the page contains {why}; a scorecard posts nothing, stores nothing and loads nothing")
        if cta_link:
            n = len(re.findall(r'href="' + re.escape(html.escape(cta_link, quote=True)) + '"', t))
            if n != 1:
                P(f"the call link should appear exactly once as a link; found {n}")
        if 'aria-live' not in t:
            P("the result is not announced to screen readers (aria-live)")
        data_m = re.search(r'<script type="application/json" id="lm-data">(.*?)</script>', t, re.S)
        if not data_m:
            P("the scoring data block is missing")
        else:
            data = json.loads(data_m.group(1).replace("<\\/", "</"))
            m = spec.get("magnet") or {}
            if [x["p"] for x in data["q"]] != [[o["points"] for o in q["options"]] for q in m.get("questions") or []]:
                P("the points in the page differ from the spec; render again from the spec")
            for q in m.get("fit_questions") or []:
                flags = re.findall(r'name="' + re.escape(q["id"]) + r'" value="\d+" data-fit="(true|false)"', t)
                if flags != [str(o["fit"]).lower() for o in q["options"]]:
                    P(f"{q['id']}: the fit flags in the page differ from the spec")
    else:
        if (spec.get("launch") or {}).get("optin", {}).get("form_action") and not re.search(r"<form\b", t):
            P("the opt-in page has no form")
    vis = re.sub(r"<script.*?</script>|<style.*?</style>", " ", t, flags=re.S)
    vis = re.sub(r"<[^>]+>", " ", vis)
    hits = set(PLACEHOLDER.findall(vis)) | set(re.findall(r"%%[A-Z_]+%%", t))
    data_txt = ""
    if page == "scorecard" and data_m:
        data_txt = " ".join(json_strings(json.loads(data_m.group(1).replace("<\\/", "</"))))
    hits |= set(PLACEHOLDER.findall(data_txt))
    for h in sorted(hits):
        P(f"placeholder or merge tag on a page the founder will publish: {h}")
    for mm in FALSE_SEND.finditer(vis + " " + data_txt):
        P(f"the page says something was sent that the page does not send: '{mm.group(0)}'")
    if len(re.findall(r"<h1\b", t)) != 1:
        P("the page needs exactly one main heading (h1)")
    if not re.search(r'<meta name="viewport"[^>]+width=device-width', t):
        P("no mobile viewport tag")
    for mm in re.finditer(r"<input\b[^>]*>", t):
        tag = mm.group(0)
        if 'type="hidden"' in tag:
            continue
        before = t[:mm.start()]
        open_label = before.rfind("<label")
        close_label = before.rfind("</label>")
        idm = re.search(r'id="([^"]+)"', tag)
        if not (open_label > close_label or (idm and re.search(r'<label[^>]+for="' + re.escape(idm.group(1)) + '"', t))):
            P(f"an input without a label: {tag[:60]}")
    for mm in re.finditer(r"(?<![-\w])(min-)?width\s*:\s*(\d+)px", t):
        if int(mm.group(2)) > 343:
            P(f"a fixed width of {mm.group(2)}px will scroll sideways on a 375 pixel phone")
    style = re.search(r"<style>(.*?)</style>", t, re.S)
    if style and re.search(r"(?<![-\w])border(-top|-bottom|-left|-right)?\s*:\s*(?!0|none)", style.group(1)):
        P("the page draws a border or rule; structure comes from space and type")
    if style and re.search(r"box-shadow\s*:\s*(?!none)", style.group(1)):
        P("the page draws a shadowed box")
    v = css_vars(spec)
    for a, b, what in ((v["%%TEXT%%"], v["%%BG%%"], "text"), (v["%%MUTED%%"], v["%%BG%%"], "grey text"),
                       (v["%%ACCENT_TEXT%%"], v["%%ACCENT%%"], "button text")):
        r = C.contrast(a, b)
        if r < 4.5:
            P(f"{what} contrast is {r:.1f} to 1; at least 4.5 to 1 is needed")
    size = os.path.getsize(path)
    limit = 600_000 if "font-face" in t else 150_000
    if size > limit:
        P(f"the page weighs {size // 1000} KB, over the {limit // 1000} KB limit")
    nf = (spec.get("founder") or {}).get("never_words") or []
    for w in nf:
        if re.search(r"\b" + re.escape(w) + r"\b", vis + " " + data_txt, re.I):
            P(f"the page uses '{w}', a word the founder asked never to see")
    if not quiet:
        for x in problems:
            print("PROBLEM:", x)
        for x in warns:
            print("WARN:", x)
        print(f"Audit of {os.path.basename(path)}: {len(problems)} problems, {size // 1000 or 1} KB.")
    return problems


# ------------------------------------------------------------------ init
def F(what):
    return f"FILL: {what}"


def skeleton(fmt, a):
    q = lambda n: {"id": f"q{n}", "label": F("optional short heading in the founder's words, or remove"),
                   "text": F(f"question {n}, one behaviour the reader can answer honestly"),
                   "source": F("where it came from: a pasted line, a founder reply, or 'drafted, said aloud'"),
                   "source_quote": F("the exact words from the paste, or remove this field"),
                   "options": [{"label": F("lowest option"), "points": 0}, {"label": F("option"), "points": 1},
                               {"label": F("option"), "points": 2}, {"label": F("best option, what the founder "
                                                                                "teaches"), "points": 3}],
                   "strength": F("What is working, for the top answer (one sentence, no figures)"),
                   "strength_mid": F("What is working, for an upper answer that is not the top one"),
                   "fix_low": F("first step for a low answer, doable this week"),
                   "fix_high": F("how to tighten an upper answer")}
    spec = {
        "format": fmt, "date": __import__("datetime").date.today().isoformat(),
        "hosting": F("where the page will live, in the founder's words"),
        "founder": {"name": a.name or F("founder's name"), "first_name": F("first name"),
                    "business": a.business or F("business name"), "country": a.country or F("two-letter country"),
                    "spelling": F("british, american, australian, canadian or indian"),
                    "decimal": F("dot or comma, from how they write numbers"),
                    "currency": a.currency or F("three-letter currency"), "signoff": a.signoff or F("sign-off"),
                    "never_words": [], "we": False},
        "offer": {"name": F("the offer"), "price_as_typed": F("price exactly as they wrote it, or remove"),
                  "link": F("booking link, or remove"), "route": "book"},
        "sources": [a.source or "founder-paste.txt"],
        "founder_replies": [],
        "topic": {"slug": F("short-topic-slug"), "problem": F("the problem in the buyer's words"),
                  "source_line": F("the line it came from, copied exactly"), "source": F("kind of source, never a "
                                                                                        "client's name"),
                  "inferred": False,
                  "runners_up": [{"topic": F("runner-up"), "why_not": F("why it lost")},
                                 {"topic": F("runner-up"), "why_not": F("why it lost")}],
                  "format_reason": F("why this format"), "not_given_away": F("what the offer keeps"),
                  "drafted": F("what you drafted for them to read as the expert")},
        "facts": [], "look": {},
        "launch": {
            "optin": {"headline": F("one specific outcome the magnet gives, not the offer's"),
                      "subhead": F("what it is and how long it takes"),
                      "bullets": [F("what they will see"), F("what they will see"), F("what they will see")],
                      "fields": ["First name", "Email"], "button": F("names what they get"),
                      "expectation": F("what they get, how often, and that they can unsubscribe at any time"),
                      "signoff_line": F("founder's sign-off line")},
            "thankyou": {"headline": F("confirmation"), "body": F("one or two lines"), "link_label": F("link text"),
                         "next_step": F("one next step")},
            "rules": {"starts": "Someone confirms their address on the opt-in form.",
                      "stops": [F("what stops it, such as a booked call")],
                      "remove_before": [F("who is removed first, such as current clients")],
                      "timing_days": [0, 1, 3, 5, 7]},
            "emails": [{"day": d, "job": F(job), "subjects": [F("subject A under 50 characters"),
                                                              F("subject B under 50 characters")],
                        "preview": F("says the next thing, not the subject"),
                        "body": F("120 to 220 words, {{first_name}} in the greeting, paragraphs split by a blank line"
                                  + ("; carries {{magnet_link}}" if n == 1 else "")
                                  + ("; carries {{booking_link}} if there is a link, and says who the call is not for"
                                     if n == 5 else "")),
                        "ps": F("one useful line")}
                       for n, (d, job) in enumerate(zip([0, 1, 3, 5, 7], [
                           "deliver the magnet and say how to read it", "the weak spot by result",
                           "a worked example, labelled as an illustration", "the door: the question it cannot answer",
                           "the one invitation"]), 1)],
            "result_map": []}}
    if fmt == "scorecard":
        spec["magnet"] = {
            "title": F("the headline: one specific question or outcome"), "promise": F("what they will know"),
            "minutes": 3, "who_for": F("who it is for"), "who_not_for": F("who it is not for"),
            "questions": [q(n) for n in range(1, 6)],
            "fit_questions": [{"id": "f1", "text": F("fit question from the founder's 'who should not call me'"),
                               "source": F("where it came from"),
                               "options": [{"label": F("not a fit answer"), "fit": False},
                                           {"label": F("fit answer"), "fit": True},
                                           {"label": "Not sure", "fit": True}]}],
            "strength_fallback": F("honest What is working line when every answer is low"),
            "tiers": [{"name": F("lowest tier, what is true there, never a verdict"), "min": 0, "max": 4,
                       "description": F("40 to 70 words")},
                      {"name": F("middle tier"), "min": 5, "max": 10, "description": F("40 to 70 words")},
                      {"name": F("top tier"), "min": 11, "max": 15, "description": F("40 to 70 words")}],
            "door": {"question": F("the next question the scorecard cannot answer"),
                     "sentence": F("where that question gets answered")},
            "cta": {"label": F("button label"), "link": F("https booking link or mailto, or remove"),
                    "line": F("line above the button for most readers"),
                    "line_top_tier": F("honest line for a top-tier reader, who has few gaps")},
            "not_a_fit": F("kind line shown in place of the call to action"),
            "footer": F("founder's name and business")}
        spec["launch"]["result_map"] = [{"when": F(f"tier {i} name, exactly"), "dealing_with": F("what they face"),
                                         "ask": F("first question on a call"), "next_step": F("next step to offer")}
                                        for i in (1, 2, 3)]
    elif fmt == "checklist":
        spec["checklist"] = {"title": F("N-point ... checklist (N must match the items)"), "who_for": F("who for"),
                             "minutes": 10,
                             "sections": [{"heading": F("section heading"), "items": [
                                 {"text": F("an action in a few words"), "detail": F("one or two sentences"),
                                  "source": F("where it came from"), "source_quote": F("exact words, or remove")}
                                 for _ in range(5)]} for _ in range(2)],
                             "not_covered": F("what it does not cover: the door"), "next_step": F("next step")}
        spec["launch"]["result_map"] = [{"when": F("what a reader's reply says"), "dealing_with": F("what they face"),
                                         "ask": F("first question"), "next_step": F("next step")} for _ in (1, 2)]
    else:
        spec["guide"] = {"title": F("title"), "who_for": F("who for"), "idea": F("the one idea in two or three "
                                                                                    "sentences"),
                         "steps": [{"text": F("step"), "source": F("where it came from")} for _ in range(3)],
                         "example_label": "An example", "example": F("one worked example, labelled as an example"),
                         "not_covered": F("the door"), "next_step": F("next step")}
        spec["launch"]["result_map"] = [{"when": F("what a reader's reply says"), "dealing_with": F("what they face"),
                                         "ask": F("first question"), "next_step": F("next step")} for _ in (1, 2)]
    return spec


def init(a):
    if a.format not in C.FORMATS:
        raise C.Stop(f"init needs --format {' | '.join(C.FORMATS)}")
    if not a.out:
        raise C.Stop("init needs --out <spec.json> in your scratch folder")
    if os.path.exists(a.out) and not a.force:
        raise C.Stop(f"{a.out} already exists; edit it, or add --force to start again")
    spec = skeleton(a.format, a)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(spec, fh, indent=1, ensure_ascii=False)
    n = sum(1 for _p, v in walk(spec) if isinstance(v, str) and v.startswith("FILL:"))
    print(f"WROTE: {a.out} ({a.format}, {n} values to fill). Replace every FILL line; remove optional fields you do "
          "not use. Then run build.")
    return 0


# ------------------------------------------------------------------ build
def run_script(args):
    r = subprocess.run([sys.executable] + args, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def pack_tag_problems(pack):
    """Every merge tag in the launch pack must be written in double braces, exactly as the emails use them."""
    import zipfile
    with zipfile.ZipFile(pack) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    text = html.unescape(re.sub(r"<[^>]+>", "", xml))
    out = []
    for mm in re.finditer(r"(?<!\{)\{([a-z_]+)\}(?!\})", text):
        out.append(f"the launch pack shows a broken merge tag '{{{mm.group(1)}}}'; it must read '{{{{{mm.group(1)}}}}}'")
    for tag in re.findall(r"\{\{[^{}]*\}\}", text):
        if tag not in C.MERGE_TAGS:
            out.append(f"the launch pack shows a merge tag that is not in the named set: {tag}")
    return out


def pdf_from_docx(docx, out_dir):
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        return None
    try:
        subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", out_dir, docx],
                       capture_output=True, timeout=120)
    except (subprocess.TimeoutExpired, OSError):
        return None
    pdf = os.path.join(out_dir, os.path.splitext(os.path.basename(docx))[0] + ".pdf")
    return pdf if os.path.exists(pdf) else None


def pdf_pages(pdf):
    try:
        with open(pdf, "rb") as fh:
            raw = fh.read()
        m = re.findall(rb"/Type\s*/Pages\b[^>]*?/Count\s+(\d+)", raw)
        return max(int(x) for x in m) if m else None
    except OSError:
        return None


def warn_lines(txt):
    return [ln[len("WARN:"):].strip() for ln in txt.splitlines() if ln.startswith("WARN:")]


def print_warnings(warns):
    if warns:
        print(f"WARNINGS ({len(warns)}): fix each one in the spec, or tell the founder in one line why it stays.")
        for x in dict.fromkeys(warns):
            print("WARN:", x)


def build(spec, out, want_pdf=False):
    import build_docx as B
    problems, warns, info = validate(spec, quiet=True)
    for x in problems:
        print("PROBLEM:", x)
    if any("scaffold values still say FILL" in x for x in problems):
        print("1 problem. Nothing was written: fill the spec and run build again.")
        return 1
    sim = None
    if spec["format"] == "scorecard" and not problems:
        sim = simulate(spec)
        problems += sim["problems"]
    path = spec["_path"]
    for script in (["check_copy.py", "--spec", path], ["emails.py", "check", path]):
        code, txt = run_script([os.path.join(HERE, script[0])] + script[1:])
        warns += warn_lines(txt)
        if code != 0:
            print("\n".join(ln for ln in txt.strip().splitlines() if not ln.startswith("WARN:")))
            if code == 2:
                return 2
            problems.append(f"{script[0]} found problems (above)")
    if problems:
        print_warnings(warns)
        print(f"{len(problems)} problems. Nothing was written: fix the spec and run build again.")
        return 1
    os.makedirs(out, exist_ok=True)
    names, d = C.file_names(spec)
    written = []
    page_problems = []
    if spec["format"] == "scorecard":
        page = render_scorecard(spec, os.path.join(out, names["main"]))
        page_problems = audit(page, spec, "scorecard", quiet=True)
        written.append(page)
        written.append(B.scorecard_twin(spec, os.path.join(out, names["twin"])))
    elif spec["format"] == "checklist":
        written.append(B.checklist_doc(spec, os.path.join(out, names["main"])))
    else:
        written.append(B.guide_doc(spec, os.path.join(out, names["main"])))
    op = (spec.get("launch") or {}).get("optin") or {}
    optin = None
    if op.get("form_action") or op.get("embed"):
        optin = render_optin(spec, os.path.join(out, names["optin"]), names)
        page_problems += audit(optin, spec, "optin", quiet=True)
        written.append(optin)
    pages = None
    if want_pdf and spec["format"] in ("checklist", "guide"):
        pdf = pdf_from_docx(written[0], out)
        if pdf:
            written.append(pdf)
            pages = pdf_pages(pdf)
            cap = 2 if spec["format"] == "checklist" else 1
            if pages and pages > cap:
                page_problems.append(f"the {spec['format']} prints on {pages} pages; the cap is {cap}. Cut the details.")
    pack = B.launch_pack(spec, os.path.join(out, names["pack"]), sim, info, optin_built=bool(optin))
    written.append(pack)
    page_problems += pack_tag_problems(pack)
    if page_problems:
        for x in page_problems:
            print("PROBLEM:", x)
        for wpath in written:
            try:
                os.remove(wpath)
            except OSError:
                pass
        print(f"{len(page_problems)} problems in the rendered files. They were removed: fix the spec and build again.")
        return 1
    for wpath in written:
        print(f"WROTE: {wpath}")
    print_warnings(warns)
    print("SUMMARY:")
    if sim:
        shares = ", ".join(f"{k} {v:g}%" for k, v in sim["shares"].items())
        print(f"  Tier shares across all {sim['answer_sets']} possible answer sets: {shares}. A middle pattern of "
              f"answers lands in '{sim['middle_tier']}'.")
        print(f"  About {max(1, round(info.get('seconds', 0) / 60 + 0.49))} minutes to finish by estimate.")
    if spec["format"] == "checklist":
        print(f"  {info.get('items')} items ready, {len(info.get('held') or [])} held as [NEED: confirm]"
              + (f"; prints on {pages} page(s)" if pages else ""))
        for it in info.get("held") or []:
            print(f"  HELD: {it.get('text')}: {it.get('need')}")
    if not optin:
        print("  No opt-in page built: no form address or embed from the founder. The copy is in the launch pack.")
    if spec.get("topic", {}).get("inferred"):
        print("  Topic inferred, not quoted: say so.")
    print(f"  Dates written {C.country_defaults(spec)['date_order']}; build date {C.human_date(d, spec)}.")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["validate", "simulate", "render", "audit", "result", "build", "init"])
    ap.add_argument("path", nargs="?")
    ap.add_argument("--out")
    ap.add_argument("--spec")
    ap.add_argument("--page", default="scorecard", choices=["scorecard", "optin"])
    ap.add_argument("--json-out")
    ap.add_argument("--answers")
    ap.add_argument("--pdf", action="store_true")
    for k in ("format", "source", "name", "business", "country", "currency", "signoff"):
        ap.add_argument(f"--{k}")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    if a.cmd == "init":
        return init(a)
    if not a.path:
        raise C.Stop(f"{a.cmd} needs the spec file: magnet.py {a.cmd} <spec.json>")
    if a.cmd == "audit":
        if not a.spec:
            raise C.Stop("audit needs --spec <spec.json> so it knows the founder's own link")
        if not os.path.exists(a.path):
            raise C.Stop(f"cannot find the page {a.path}")
        return 1 if audit(a.path, C.load_spec(a.spec), a.page) else 0
    spec = C.load_spec(a.path)
    if a.cmd == "validate":
        problems, warns, _ = validate(spec)
        print(f"{len(problems)} problems, {len(warns)} warnings")
        return 1 if problems else 0
    if a.cmd == "simulate":
        if spec.get("format") != "scorecard":
            raise C.Stop("simulate is for scorecards only")
        problems, _w, _ = validate(spec, quiet=True)
        if problems:
            for x in problems:
                print("PROBLEM:", x)
            print("Fix these before simulating.")
            return 1
        res = simulate(spec)
        if a.json_out:
            with open(a.json_out, "w", encoding="utf-8") as fh:
                json.dump(res, fh, indent=1)
        return 1 if res["problems"] else 0
    if a.cmd == "result":
        if spec.get("format") != "scorecard":
            raise C.Stop("result is for scorecards only")
        given = dict(x.split("=") for x in (a.answers or "").split(",") if "=" in x)
        m = spec["magnet"]
        picks = [int(given[q["id"]]) for q in m["questions"]]
        fits = [int(given[q["id"]]) if q["id"] in given else None for q in m.get("fit_questions") or []]
        print(json.dumps(compute(spec, picks, fits), indent=1))
        return 0
    if a.cmd == "render":
        if not a.out:
            raise C.Stop("render needs --out <folder>")
        return build(spec, a.out, a.pdf)
    if not a.out:
        raise C.Stop("build needs --out <folder>: /mnt/user-data/outputs when it exists, else the working folder")
    return build(spec, a.out, a.pdf)


if __name__ == "__main__":
    C.run_main(main)
