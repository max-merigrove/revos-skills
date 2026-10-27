#!/usr/bin/env python3
"""Check the scan against every gate, then write the one-page report and the line-edits document.

Usage:
  python3 scripts/build_report.py <extraction.json> --voice <voice.json> --redaction <clean/redaction.json>
                                  --out <output folder> [--previous <previous.json>] [--results <results.json>]

Gates, all run before anything is written:
  1. every quote is word for word (verify_quotes.py)
  2. the score is counted from the table (score_consistency.py)
  3. three core lines, each with the three tests answered; a line using a phrase any competitor
     could write cannot pass "only you could say it"; the recommended line passes all three; when
     the founder sells personally it does not hide them behind "we"
  4. edits are line level and cover every asset that answers differently from the recommended line
  5. no figure in a core line or an edit that the assets never state
  6. the copy Claude wrote passes check_copy.py
  7. no client name, email, phone number, postal code, street address, bank or registration number,
     or client fee in any output
  8. what Claude wrote is spelt in the founder's English, and names no country or currency the
     founder's assets do not

Locale (extraction "locale": {"country": "US", "english": "american", "paper": "letter", "dates": "mdy"},
every field optional): the report prints on Letter or A4 and dates read the founder's way. Paper and
date style follow the country where not given; English follows the founder's own spelling (voice.json).
Unknown stays unknown: the page prints on the viewer's default paper and dates read 2026-10-20.

Writes, only when every gate passes:
  <out>/brand-scan-<business>-<date>.html             the one-page report (open first; prints to one Letter or A4 page)
  <out>/brand-scan-<business>-<date>-line-edits.docx  the full table, voice drift and every line edit
  <results.json> (default: beside the extraction)     what the memory file is built from
Exit 0 written; exit 1 a gate failed and nothing was written; exit 2 STOP (input cannot be used).
Standard library only. No network.
"""
import argparse
import html
import json
import re
import sys
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape as xesc

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scan_common as C  # noqa: E402
import verify_quotes as VQ  # noqa: E402
import score_consistency as SC  # noqa: E402
import check_copy as CC  # noqa: E402

GATE_KEYS = [("picture", "Can a buyer picture it?"), ("provable", "Could it be shown true or false?"),
             ("unique", "Could only you say it?")]
GATE_SHORT = {"picture": "picturable", "provable": "provable", "unique": "only you could say it"}
WE_RE = re.compile(r"\b(we|we're|we've|we'll|us|our|ours)\b", re.I)
I_RE = re.compile(r"\b(i|i'm|i've|i'll|me|my)\b", re.I)
SHOW_WORDS = 26  # the one-page report shows long quotes to this many words, marked with "..."


LOCALE = C.resolve_locale({})  # set in main() from the extraction and voice files
ENGLISH_SOURCE = None  # "counted" (from the founder's spelling), "founder" (they said), "country" (fallback) or None


def long_date(iso):
    return C.fmt_date(iso, LOCALE["dates"])


def short_quote(q, limit=SHOW_WORDS):
    w = q.split()
    return q if len(w) <= limit else " ".join(w[:limit]).rstrip(",;:") + " ..."


# ---------------------------------------------------------------- gates

def gate_lines(ext, res, sources, sells, founder, decimal=None):
    probs = []
    lines = ext.get("core_lines") or []
    ch0 = ext.get("chosen")
    if not lines and isinstance(ch0, dict) and ch0.get("by") == "memory":
        if not (ch0.get("line") or "").strip() or not isinstance(ch0.get("aligns_with"), dict):
            probs.append("chosen: a saved line needs its text and 'aligns_with' (the agreed group letter per question).")
        return probs
    if len(lines) != 3:
        probs.append(f"core lines: {len(lines)} given; write exactly three candidates.")
        return probs
    rec = ext.get("recommended")
    if not isinstance(rec, int) or not 0 <= rec < 3:
        probs.append("core lines: 'recommended' must be 0, 1 or 2 (the index of the line you recommend).")
        rec = None
    groups = {r["q"]: {c["group"] for c in r["cells"] if c["group"]} for r in res["rows"]}
    for i, cl in enumerate(lines):
        n = i + 1
        line = (cl.get("line") or "").strip()
        nw = len(C.words(line))
        if not 6 <= nw <= 30:
            probs.append(f"core line {n}: {nw} words; a core line is 6 to 30 words.")
        gate = cl.get("gate") or {}
        for key, _q in GATE_KEYS:
            g = gate.get(key)
            if not isinstance(g, dict) or not isinstance(g.get("pass"), bool) or len(C.words(g.get("why", ""))) < 4:
                probs.append(f"core line {n}: gate '{key}' needs {{\"pass\": true or false, \"why\": a reason of four words or more}}.")
        stock = CC.stock_phrases(line)
        if stock and (gate.get("unique") or {}).get("pass") is True:
            probs.append(f"core line {n}: uses \"{stock[0]}\", which any competitor could write; mark 'unique' false or rewrite the line.")
        miss = C.figures_supported(line, sources, decimal)
        if miss:
            probs.append(f"core line {n}: states {', '.join(miss)}, which no asset states. Remove it or use a figure the founder published.")
        for cred in C.unstated_credentials(line, sources):
            probs.append(f"core line {n}: says \"{cred}\", a credential no asset names. Use only credentials the founder's assets state.")
        if len(C.words(cl.get("rationale", ""))) < 5:
            probs.append(f"core line {n}: give a one-line rationale.")
        al = cl.get("aligns_with")
        if not isinstance(al, dict) or not al:
            probs.append(f"core line {n}: 'aligns_with' must say which answer it keeps per question (a group letter, or \"new\").")
        else:
            for q, g in al.items():
                if q not in C.QKEYS:
                    probs.append(f"core line {n}: aligns_with has unknown question '{q}'.")
                elif g not in (None, "new") and str(g).upper() not in groups.get(q, set()):
                    probs.append(f"core line {n}: aligns_with.{q} is '{g}', which is not a group in that question.")
        we = WE_RE.search(line)
        if sells == "me" and we and not I_RE.search(line) and not (founder and founder.lower() in line.lower()):
            msg = (f"core line {n}: says \"{we.group(0)}\" though the founder sells personally; keep them visible "
                   f"(\"I\", their name, or no pronoun).")
            if rec == i:
                probs.append(msg)
    if rec is not None:
        g = lines[rec].get("gate") or {}
        failed = [GATE_SHORT[k] for k, _ in GATE_KEYS if not (g.get(k) or {}).get("pass")]
        if failed and not ext.get("chosen"):
            probs.append(f"core line {rec + 1} is recommended but fails: {', '.join(failed)}. Recommend a line that passes all three, or rewrite it.")
    ch = ext.get("chosen")
    if ch is not None:
        if not isinstance(ch, dict) or not (ch.get("line") or "").strip():
            probs.append("chosen: give {\"line\": the founder's chosen or rewritten line, \"by\": \"founder\"}.")
        else:
            miss = C.figures_supported(ch["line"], sources, decimal)
            if miss:
                probs.append(f"chosen line: states {', '.join(miss)}, which no asset states. Ask the founder where it is shown.")
    return probs


def chosen_alignment(ext):
    lines = ext.get("core_lines") or []
    rec = ext.get("recommended") if isinstance(ext.get("recommended"), int) else 0
    ch = ext.get("chosen") or {}
    if isinstance(ch, dict) and isinstance(ch.get("aligns_with"), dict):
        return {k: (str(v).upper() if v not in (None, "new") else v) for k, v in ch["aligns_with"].items()}
    if lines and 0 <= rec < len(lines) and isinstance(lines[rec].get("aligns_with"), dict):
        return {k: (str(v).upper() if v not in (None, "new") else v) for k, v in lines[rec]["aligns_with"].items()}
    return {}


def declined_map(ext):
    """{(asset, question): {"by": "founder" or "decision", "reason": ...}} for edits the scan must not make."""
    out = {}
    for d in ext.get("declined") or []:
        if isinstance(d, dict) and d.get("asset") and d.get("question") in C.QKEYS:
            out[(d["asset"], d["question"])] = {"by": d.get("by") or "founder", "reason": str(d.get("reason") or "").strip()}
    return out


def gate_edits(ext, res, sources, decimal=None, texts=None, founder=""):
    probs = []
    edits = ext.get("edits") or []
    ids = {a["id"]: a for a in res["assets"]}
    raw_assets = {a["id"]: a for a in ext.get("assets") or []}
    texts = texts or {}
    sold_by = ext.get("sold_by") or {}
    have = set()
    cell_quote = {(c["asset"], r["q"]): c["quote"] for r in res["rows"] for c in r["cells"] if c["quote"]}
    for k, e in enumerate(edits, 1):
        aid, q = e.get("asset"), e.get("question")
        if aid not in ids or ids[aid]["kind"] == "agreed":
            probs.append(f"edit {k}: asset '{aid}' is not one of the founder's assets.")
            continue
        if q not in C.QKEYS:
            probs.append(f"edit {k}: 'question' must be one of {', '.join(C.QKEYS)}.")
            continue
        prop = (e.get("proposed") or "").strip()
        if not prop:
            probs.append(f"edit {k}: no proposed line.")
            continue
        if e.get("current") and C.norm_text(e["current"]) == C.norm_text(prop):
            probs.append(f"edit {k}: the proposed line is the same as the current one.")
        if not e.get("current") and not e.get("after") and len(C.words(prop)) < 3:
            probs.append(f"edit {k}: an added line needs to be a full line, and 'after' to say where it goes if it matters.")
        if len(C.words(prop)) > 60:
            probs.append(f"edit {k}: proposed line is {len(C.words(prop))} words; an edit is a line, at most 60 words.")
        miss = C.figures_supported(prop, sources, decimal)
        if miss:
            probs.append(f"edit {k}: states {', '.join(miss)}, which no asset states. Remove it or use [NEED: ...].")
        for mine, theirs in C.figure_style_problems(prop, sources, decimal):
            probs.append(f"edit {k}: writes {mine}; the founder writes it {theirs}. Write numbers the founder's way.")
        for cred in C.unstated_credentials(prop, sources):
            probs.append(f"edit {k}: says \"{cred}\", a credential no asset names. Use only credentials the founder's assets state.")
        if (aid, q) in declined_map(ext):
            probs.append(f"edit {k}: the founder declined an edit to their {C.in_sentence(ids[aid]['label'])} on {C.QPHRASE[q]}; leave it out.")
        if sold_by.get(aid) in ("others", "team"):  # someone else sells this one: do not put the founder in it
            cur = e.get("current") or ""
            added_i = [w for w in C.words(prop) if w.lower() in ("i", "i'm", "i've", "i'll", "my", "me")
                       and w.lower() not in {x.lower() for x in C.words(cur)}]
            first = (founder or "").split()[0] if founder else ""
            if added_i or (first and len(first) > 2 and re.search(r"\b" + re.escape(first) + r"\b", prop) and first not in cur):
                probs.append(f"edit {k}: puts you into your {C.in_sentence(ids[aid]['label'])}, which you said someone else sells. "
                             f"Keep the edit in that asset's own voice.")
        have.add((aid, q))
        cur = C.norm_text(e.get("current") or "")
        if cur:  # one edit to a line that also answers another question covers that question too
            for (a2, q2), quote in cell_quote.items():
                if a2 == aid and q2 != q and C.norm_text(quote) in cur:
                    have.add((aid, q2))
    # two edits on overlapping lines of one asset would print two replacements for one line
    for i, e1 in enumerate(edits, 1):
        for j, e2 in enumerate(edits, 1):
            if i >= j or e1.get("asset") != e2.get("asset") or not e1.get("current") or not e2.get("current"):
                continue
            c1, c2 = C.norm_text(e1["current"]), C.norm_text(e2["current"])
            if c1 in c2 or c2 in c1:
                big, small = (i, j) if len(c1) >= len(c2) else (j, i)
                probs.append(f"edit {small}: changes part of the line edit {big} already replaces. Drop edit {small}; "
                             f"edit {big} covers both questions.")
    align = chosen_alignment(ext)
    skip, _why = C.skip_map(ext)
    declined = declined_map(ext)
    decide = C.norm_text(ext.get("decide") or "")
    for (aid, q), d in declined.items():
        if aid not in ids:
            probs.append(f"declined: asset '{aid}' is not one of the founder's assets.")
        elif d["by"] == "decision":
            a = ids[aid]
            named = C.norm_text(a["label"]).split()[0] in decide or C.KIND_NAMES[a["kind"]].split()[-1] in decide
            if a["kind"] not in C.CLIENT_FACING or q not in ("who", "what") or not named:
                probs.append(f"declined: an edit is held for the decision only on who you serve or what you do in a proposal, "
                             f"deck or other client-facing asset, and the decision must name it ('{a['label']}').")
        elif not d["reason"]:
            probs.append(f"declined: say why the founder declined the edit to '{aid}' on '{q}' (their words, a few of them).")
    for r in res["rows"]:
        q = r["q"]
        target = align.get(q)
        if target is None or q == "next":
            continue
        for c in r["cells"]:
            if c["relation"] == "skipped" or q in (skip.get(c["asset"]) or []) or (c["asset"], q) in declined:
                continue
            needs = False
            if c["group"] is None:
                needs = q in ("who", "what")
            elif target == "new" or c["group"] != target:
                needs = True
            if needs and (c["asset"], q) not in have:
                what = "never says" if c["group"] is None else "answers differently on"
                probs.append(f"edits: your {C.in_sentence(c['label'])} {what} {r['phrase']}, and no edit fixes it. Add an edit with "
                             f"asset '{c['asset']}', question '{q}', or, if the founder said to leave it, list it under 'declined'.")
    for k, f in enumerate(res.get("facts") or [], 1):
        quotes = [(c["asset"], C.norm_text(c["quote"])) for c in f["cells"]]
        fixed = any(e.get("asset") == a and e.get("current") and (qn in C.norm_text(e["current"]) or C.norm_text(e["current"]) in qn)
                    for e in edits for a, qn in quotes)
        if not fixed:
            probs.append(f"facts: your assets disagree on {f.get('what') or 'a fact'} and no edit fixes it. Add an edit on one of the "
                         f"quoted lines, or [NEED: which is true] if only the founder knows.")
    for aid, a in raw_assets.items():  # short assets that must fit one field
        plat = C.platform_of(dict(a, kind=ids.get(aid, {}).get("kind", a.get("kind"))))
        mine = [e for e in edits if e.get("asset") == aid]
        if not mine or aid not in texts:
            continue
        if plat:
            name, limit = C.PLATFORM_LIMITS[plat]
            before = len(texts[aid].strip())
            after = len(C.apply_edits(texts[aid], mine).strip())
            if after > max(limit, before):
                probs.append(f"edits: your {name} would be {after} characters after these edits; it allows {limit}. "
                             f"Shorten the proposed lines until the whole {name} fits.")
        if ids.get(aid, {}).get("kind") == "linkedin":
            name, limit = C.PLATFORM_LIMITS["linkedin_headline"]
            for ln in C.apply_edits(texts[aid], mine).splitlines():
                if re.match(r"\s*headline\s*:", ln, re.I) and len(ln.split(":", 1)[1].strip()) > limit:
                    probs.append(f"edits: your LinkedIn headline would be {len(ln.split(':', 1)[1].strip())} characters; "
                                 f"LinkedIn allows {limit}.")
    return probs


def gate_decide(ext):
    d = (ext.get("decide") or "").strip()
    n = len(C.words(d))
    if not d:
        return ["decision: write the one choice only the founder can make, as a question."]
    out = []
    if not d.endswith("?"):
        out.append("decision: phrase it as the question the founder must answer, ending with '?'.")
    if not 6 <= n <= 45:
        out.append(f"decision: {n} words; keep it to one question of 6 to 45 words.")
    return out


def gate_also(ext):
    """Things a sharp reader would catch outside the five questions: a claim nothing backs, a date that has
    passed, figures that do not reconcile, a typo. Each names its asset and says what to do in one line."""
    items = ext.get("also") or []
    if not isinstance(items, list):
        return ["also: a list of {\"what\", \"asset\", \"quote\", \"note\"} objects."]
    ids = {a["id"] for a in ext.get("assets", [])}
    out = []
    for i, x in enumerate(items, 1):
        if not isinstance(x, dict):
            out.append(f"also {i}: write it as {{\"what\", \"asset\", \"quote\", \"note\"}}.")
            continue
        if x.get("asset") not in ids:
            out.append(f"also {i}: name the asset it is in (one of {', '.join(sorted(ids))}).")
        if not 2 <= len(C.words(x.get("what") or "")) <= 12:
            out.append(f"also {i}: 'what' is a 2 to 12 word label.")
        if not 4 <= len(C.words(x.get("note") or "")) <= 45:
            out.append(f"also {i}: 'note' says what to do about it in 4 to 45 words.")
    if len(items) > 6:
        out.append("also: keep it to the six that matter most.")
    return out


_MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"


def wrong_date_order(text):
    """Dates Claude writes in the other order from the founder's (21 October 2026 to a US founder)."""
    style = (LOCALE or {}).get("dates")
    out = []
    if style == "mdy":
        for m in re.finditer(r"\b(\d{1,2}) (" + _MONTHS + r")(,? (\d{4}))?\b", text):
            out.append((m.group(0), f"{m.group(2)} {m.group(1)}" + (f", {m.group(4)}" if m.group(4) else "")))
    elif style == "dmy":
        for m in re.finditer(r"\b(" + _MONTHS + r") (\d{1,2})(?:st|nd|rd|th)?\b(,? (\d{4}))?", text):
            out.append((m.group(0), f"{m.group(2)} {m.group(1)}" + (f" {m.group(4)}" if m.group(4) else "")))
    return out


def gate_locale(ext, sources, english):
    """Claude's copy in the founder's spelling, and no country or currency the founder never mentions."""
    probs = []
    for label, text in CC.written_fields(ext):
        for w, fix in C.wrong_spellings(text, english) if english else []:
            probs.append(f"copy, {label}: \"{w}\" is spelt the other way from the founder's {english.title()} English; write \"{fix}\".")
        for d, fix in wrong_date_order(text):
            probs.append(f"copy, {label}: \"{d}\" reads in the other date order from the founder's; write \"{fix}\".")
        for place in C.assumed_places(text, sources):
            probs.append(f"copy, {label}: names \"{place}\", which none of the founder's assets mention. Do not assume a country "
                         f"or currency; use the founder's own words.")
    return probs


def gate_privacy(texts, hashes, public_sources):
    probs = []
    allowed_money = set()
    for s in public_sources:
        allowed_money |= {C.norm_text(m.group(0)) for m in C.MONEY_RE.finditer(s)}
    for where, t in texts:
        for kind, val in C.personal_data_hits(t):
            probs.append(f"privacy: {where} contains {'an' if kind[0] in 'aeiou' else 'a'} {kind}. Use the clean copies only.")
        for term in C.leaked_terms(t, hashes):
            probs.append(f"privacy: {where} contains a removed client name (\"{term}\"). Quote the clean copy, where it reads [client].")
        for m in C.MONEY_RE.finditer(t):
            if C.norm_text(m.group(0)) not in allowed_money:
                probs.append(f"privacy: {where} contains the amount \"{m.group(0)}\", which is not on a public asset. Fees stay out of the report.")
    return sorted(set(probs))


# ---------------------------------------------------------------- html

CSS = """
:root { --ink: #111111; --soft: #6b6b6b; --faint: #a6a6a6; --paper: #ffffff; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --ink: #eeeeea; --soft: #a3a39e; --faint: #6f6f6b; --paper: #141414; } }
:root[data-theme="dark"] { --ink: #eeeeea; --soft: #a3a39e; --faint: #6f6f6b; --paper: #141414; }
@page { size: __PAGE__; margin: 12mm 14mm; }
* { box-sizing: border-box; }
html { background: var(--paper); }
body { margin: 0 auto; max-width: 54rem; padding: 3.5rem 1rem 4rem; color: var(--ink); background: var(--paper);
  font: 15px/1.5 "Helvetica Neue", Helvetica, Arial, sans-serif; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
.kicker, h2, .asset, .stat-label, .cost, .letter, footer { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; }
.kicker { font-size: 0.72rem; letter-spacing: 0.14em; text-transform: uppercase; color: var(--soft); margin: 0 0 2.2rem; }
.top { display: grid; grid-template-columns: auto 1fr; gap: 0 2.6rem; align-items: end; }
.score { font-size: 5.6rem; line-height: 0.82; font-weight: 300; letter-spacing: -0.04em; margin: 0; }
.score small { font-size: 1.1rem; letter-spacing: 0; color: var(--soft); font-weight: 400; margin-left: 0.2rem; }
.band { font-size: 0.72rem; letter-spacing: 0.14em; text-transform: uppercase; color: var(--soft); margin: 0.9rem 0 0; }
h1 { font: 400 1.75rem/1.2 Georgia, "Iowan Old Style", "Times New Roman", serif; margin: 0; letter-spacing: -0.005em; }
.sub { color: var(--soft); margin: 0.6rem 0 0; font-size: 0.92rem; }
h2 { font-size: 0.72rem; font-weight: 600; letter-spacing: 0.14em; text-transform: uppercase; color: var(--soft); margin: 3.2rem 0 1rem; }
.core { font: 400 1.6rem/1.28 Georgia, "Iowan Old Style", "Times New Roman", serif; margin: 0; max-width: 40rem; }
.core-why { color: var(--soft); margin: 0.7rem 0 0; max-width: 40rem; font-size: 0.92rem; }
.conflict { margin: 0 0 2.2rem; break-inside: avoid; }
.conflict h3 { font: 600 1rem/1.3 "Helvetica Neue", Helvetica, Arial, sans-serif; margin: 0 0 0.9rem; }
.conflict h3 .cost { font-weight: 400; color: var(--soft); font-size: 0.85rem; margin-left: 0.6rem; }
.cols { display: grid; gap: 1.2rem 2.4rem; }
.cols.n2 { grid-template-columns: 1fr 1fr; } .cols.n3 { grid-template-columns: repeat(3, 1fr); } .cols.n4 { grid-template-columns: repeat(4, 1fr); }
.asset { font-size: 0.7rem; letter-spacing: 0.12em; text-transform: uppercase; color: var(--soft); margin: 0 0 0.35rem; }
.asset .letter { color: var(--ink); font-weight: 600; margin-left: 0.4rem; letter-spacing: 0.04em; }
.quote { font: italic 400 1.02rem/1.4 Georgia, "Iowan Old Style", "Times New Roman", serif; margin: 0; }
.quote.none { font-style: normal; color: var(--faint); font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; font-size: 0.9rem; }
.five { display: grid; grid-template-columns: repeat(5, 1fr); gap: 1rem 1.6rem; }
.stat-label { font-size: 0.7rem; letter-spacing: 0.1em; text-transform: uppercase; color: var(--soft); margin: 0 0 0.3rem; min-height: 2.8em; }
.legend { color: var(--soft); font-size: 0.85rem; margin: -0.4rem 0 1.4rem; }
.stat { font-size: 1.6rem; font-weight: 300; margin: 0; letter-spacing: -0.02em; }
.stat small { font-size: 0.8rem; color: var(--soft); letter-spacing: 0; }
.stat-word { margin: 0.15rem 0 0; font-size: 0.85rem; }
.stat-move { margin: 0.1rem 0 0; font-size: 0.78rem; color: var(--soft); }
.decide { font: 400 1.25rem/1.35 Georgia, "Iowan Old Style", "Times New Roman", serif; margin: 0; max-width: 42rem; }
.gaps p { margin: 0 0 0.5rem; }
footer { margin-top: 3.2rem; color: var(--soft); font-size: 0.75rem; max-width: 44rem; }
footer p { margin: 0 0 0.3rem; }
@media (max-width: 640px) {
  body { padding: 2rem 16px 3rem; }
  .top { grid-template-columns: 1fr; gap: 1rem; }
  .score { font-size: 4.2rem; }
  .cols.n2, .cols.n3, .cols.n4 { grid-template-columns: 1fr; }
  .five { grid-template-columns: repeat(2, 1fr); }
}
@media print {
  body { padding: 0; max-width: none; font-size: 9.2pt; line-height: 1.34; }
  .kicker { margin-bottom: 5mm; font-size: 6.6pt; }
  .score { font-size: 52pt; } .score small { font-size: 10pt; } .band { font-size: 6.6pt; margin-top: 2.4mm; }
  h1 { font-size: 17pt; } .sub { font-size: 8.8pt; margin-top: 1.5mm; }
  h2 { font-size: 6.6pt; margin: 8mm 0 2.8mm; }
  .core { font-size: 15pt; } .core-why { font-size: 8.6pt; margin-top: 1.8mm; }
  .legend { font-size: 8pt; margin: -1mm 0 3.4mm; }
  .conflict { margin-bottom: 5mm; } .conflict h3 { font-size: 9.6pt; margin-bottom: 2.2mm; } .conflict h3 .cost { font-size: 8.2pt; }
  .cols { gap: 2mm 7mm; } .asset { font-size: 6.3pt; margin-bottom: 0.9mm; } .quote { font-size: 9.6pt; } .quote.none { font-size: 8.4pt; }
  .five { gap: 2mm 5mm; } .stat-label { font-size: 6.1pt; } .stat { font-size: 14pt; } .stat-word, .stat-move { font-size: 7.8pt; }
  .decide { font-size: 11.5pt; }
  footer { margin-top: 7mm; font-size: 6.8pt; }
  body.dense { font-size: 8.4pt; } body.dense h2 { margin: 5.5mm 0 2.2mm; } body.dense .score { font-size: 44pt; }
  body.dense h1 { font-size: 15pt; } body.dense .core { font-size: 13pt; } body.dense .quote { font-size: 8.4pt; }
  body.dense .cols { gap: 1.6mm 5mm; } body.dense .conflict { margin-bottom: 3.6mm; } body.dense .decide { font-size: 10.5pt; }
  body.dense .kicker { margin-bottom: 3.5mm; } body.dense footer { margin-top: 5mm; }
}
"""


PRINT_BUDGET_MM = 245  # Letter is 279 mm tall; less 24 mm of margins leaves 255 mm. A4 is taller, so Letter decides.


def print_height_mm(res, line, why, decide, red, carried=False):
    """Estimate the printed height of the normal layout from element heights measured in Chromium at print
    size (evals/TEST_REPORT.md). Over budget, the report switches to the denser print layout so it stays on
    one page of Letter or A4. Accurate to about one line; the budget leaves ten millimetres for that."""
    import math
    n = len(res["contradictions"][:3])
    h = 57 + 4.1 * n + 3.1 + 20.6 + 15.5 + 18.2 + (3.8 if n else 0)  # spacing, kicker, score, headings, five questions, legend
    h += 6.8 * math.ceil(len(line) / 75) + 4.1 * math.ceil(len(why) / 120) + 5.45 * math.ceil(len(decide) / 90)
    per_line = {1: 120, 2: 64, 3: 38, 4: 27}
    for c in res["contradictions"][:3]:
        cells = [x for x in c["cells"] if x["relation"] != "skipped"][:4]
        longest = max([len(short_quote(x["quote"])) + 2 if x["quote"] else 10 for x in cells] or [10])
        h += 10.3 + 4.8 * math.ceil(longest / per_line.get(len(cells), 27))
        h += 3.2 if carried else 0  # "saved 14 August 2026" lengthens the asset labels to two lines
    for f in res.get("facts") or []:
        cells = f["cells"][:4]
        longest = max([len(short_quote(x["quote"])) + 2 for x in cells] or [10])
        h += 10.3 + 4.8 * math.ceil(longest / per_line.get(len(cells), 27))
    if res.get("facts"):
        h += 15.5 / 3  # one more heading
    also = res.get("also") or []
    if also:
        h += 15.5 / 3 + sum(4.1 * math.ceil((len(x.get("what", "")) + len(x.get("note", "")) + 4) / 115) + 1.2 for x in also[:3])
    kinds = len([v for v in (red.get("totals") or {}).values() if v])
    h += 3.2 * math.ceil((350 + 30 * kinds + (120 if carried else 0)) / 115)
    return h


def letter_text(c, row):
    if c["group"] is None:
        return ""
    if c["relation"] == "compatible":
        return f"{c['group']}, close to {row['anchor']}"
    return c["group"]


def top_headline(res):
    """A fact two assets state differently is what a buyer checks first, whatever it costs in points."""
    facts = res.get("facts") or []
    if not facts:
        return res["headline"]
    f0 = facts[0]
    labs = []
    for c in f0["cells"]:
        if C.in_sentence(c["label"]) not in labs:
            labs.append(C.in_sentence(c["label"]))
    who = (f"Your {labs[0]} and your {labs[1]}" if len(labs) == 2 else "Your " + ", ".join(labs[:-1]) + f" and {labs[-1]}")
    return who + " state different facts" + (f" about {f0['what']}." if f0.get("what") else ".")


def html_report(ext, res, voice, red, out_docx_name):
    e = html.escape
    biz = ext.get("business") or "Your business"
    dt = long_date(ext.get("date") or date.today().isoformat())
    ch = ext.get("chosen") if isinstance(ext.get("chosen"), dict) else None
    rec = ext["core_lines"][ext["recommended"]] if ext.get("core_lines") else {}
    line = ch["line"] if ch else rec["line"]
    why = (ch.get("why") if ch else None) or rec.get("rationale", "")
    sub = res["band_line"]
    facts = res.get("facts") or []
    headline = top_headline(res)
    if facts:
        sub = f"{sub} {res['headline']}"
    if res.get("previous_total") is not None:
        sub = f"{sub} {'Up' if res['total'] >= res['previous_total'] else 'Down'} from {res['previous_total']} on {long_date(res.get('previous_date'))}."
    if res.get("alignment") is not None:
        sub += f" Alignment with the line you chose: {res['alignment']} of 100."
    dense = (any(len([x for x in c["cells"] if x["relation"] != "skipped"]) >= 4 for c in res["contradictions"][:3])
             or print_height_mm(res, line, why, ext.get("decide", ""), red,
                                any(a.get("from_memory") for a in res["assets"])) > PRINT_BUDGET_MM)
    limit = 18 if dense else SHOW_WORDS
    parts = [f'<p class="kicker">Brand consistency scan &middot; {e(biz)} &middot; {e(dt)}</p>',
             '<div class="top">',
             f'<div><p class="score">{res["total"]}<small>/100</small></p><p class="band">{e(res["band"])}</p></div>',
             f'<div><h1>{e(headline)}</h1><p class="sub">{e(sub)}</p></div>',
             '</div>']
    if facts:
        parts.append("<h2>Facts that disagree</h2>")
        for i, f in enumerate(facts, 1):
            cells = f["cells"][:4]
            parts.append(f'<div class="conflict"><h3>{e((f.get("what") or "A fact").capitalize())}'
                         f'<span class="cost">a buyer who reads both will ask which is true</span></h3>'
                         f'<div class="cols n{min(4, max(2, len(cells)))}">')
            for x in cells:
                parts.append(f'<div><p class="asset">{e(x["label"])}</p><p class="quote">&ldquo;{e(short_quote(x["quote"], limit))}&rdquo;</p></div>')
            parts.append("</div></div>")
    rec_if = (rec.get("if_you_choose") or "").strip() if not ch else ""
    heading = ("The line you chose to align on" if ch else
               f"The line to align on, if you choose {rec_if}" if rec_if else "The line to align on")
    parts += [f'<h2>{e(heading)}</h2>',
             f'<p class="core">{e(line)}</p>',
             f'<p class="core-why">{e(why)}</p>']
    if res["contradictions"]:
        parts.append("<h2>Where your assets disagree</h2>")
        parts.append('<p class="legend">Same letter, same answer. Two different letters mean a buyer who reads both hears two different businesses.</p>')
        for i, c in enumerate(res["contradictions"][:3], 1):
            row = next(r for r in res["rows"] if r["q"] == c["q"])
            cells = [x for x in c["cells"] if x["relation"] != "skipped"]
            if len(cells) > 4:
                keep = [x for x in cells if x["group"]][:4]
                cells = keep
            n = min(4, max(2, len(cells)))
            parts.append(f'<div class="conflict"><h3>{i}. {e(c["label"])}<span class="cost">costs {c["cost"]} of {row["weight"]} points</span></h3>')
            parts.append(f'<div class="cols n{n}">')
            saved = {a["id"]: a.get("from_memory") for a in res["assets"]}
            for x in cells:
                lt = letter_text(x, row)
                letter = f'<span class="letter">Answer {e(lt)}</span>' if lt else ""
                q = (f'<p class="quote">&ldquo;{e(short_quote(x["quote"], limit))}&rdquo;</p>' if x["quote"]
                     else '<p class="quote none">Not stated</p>')
                when = f' &middot; saved {e(long_date(saved[x["asset"]]))}' if saved.get(x["asset"]) else ""
                parts.append(f'<div><p class="asset">{e(x["label"])}{when}{letter}</p>{q}</div>')
            parts.append("</div></div>")
    else:
        parts.append("<h2>No contradictions</h2>")
        gaps = res["missing"][:4]
        if gaps:
            parts.append('<div class="gaps">' + "".join(
                f'<p>Your {e(C.in_sentence(m["asset_label"]))} never says {e(m["phrase"])}.</p>' for m in gaps) + "</div>")
        else:
            parts.append('<div class="gaps"><p>Every asset answers all five questions the same way.</p></div>')
    also_all = [x for x in ext.get("also") or [] if isinstance(x, dict)]
    also = also_all[:3]
    if also:
        labs = {a["id"]: a["label"] for a in res["assets"]}
        parts.append("<h2>Also worth fixing</h2><div class=\"gaps\">")
        for x in also:
            parts.append(f'<p><strong>{e(x["what"])}</strong> ({e(C.in_sentence(labs.get(x["asset"], x["asset"])))}). {e(x["note"])}</p>')
        if len(also_all) > 3:
            n = len(also_all) - 3
            parts.append(f'<p>{n} more {"is" if n == 1 else "are"} in {e(out_docx_name)}.</p>')
        parts.append("</div>")
    parts.append("<h2>All five questions</h2><div class=\"five\">")
    mv = res.get("movement") or {}
    for r in res["rows"]:
        move = ""
        if mv.get(r["q"]) is not None:
            move = f'<p class="stat-move">{mv[r["q"]]:+d} since last scan</p>'
        parts.append(f'<div><p class="stat-label">{e(r["label"])}</p><p class="stat">{r["points"]}<small>/{r["weight"]}</small></p>'
                     f'<p class="stat-word">{e(r["status_word"])}</p>{move}</div>')
    parts.append("</div>")
    parts.append("<h2>The one thing only you can decide</h2>")
    parts.append(f'<p class="decide">{e(ext["decide"])}</p>')
    removed = dict(red.get("totals") or {})
    if red.get("client_names") is not None:  # distinct names, not mentions: "4 client names", never "7"
        removed["client"] = red["client_names"]
    rm = []
    for k, (one, many) in [("client", ("client name", "client names")), ("fee", ("fee", "fees")),
                           ("email", ("email address", "email addresses")), ("phone", ("phone number", "phone numbers")),
                           ("address", ("street address", "street addresses")), ("postcode", ("postal code", "postal codes")),
                           ("bank", ("bank or registration number", "bank or registration numbers"))]:
        if removed.get(k):
            rm.append(f"{removed[k]} {one if removed[k] == 1 else many}")
    rm_join = (", ".join(rm[:-1]) + " and " + rm[-1]) if len(rm) > 1 else "".join(rm)
    rm_line = ("Before reading, " + rm_join + (" was" if len(rm) == 1 and rm[0].startswith("1 ") else " were")
               + " taken out of what you pasted; none of it appears here or is saved."
               if rm else "Nothing personal to clients was found in what you pasted; nothing personal is saved.")
    if red.get("own_contact"):
        rm_line += " Your own contact and payment details were left out of the reading too."
    carried = [a for a in res["assets"] if a.get("from_memory") and a["kind"] != "agreed"]
    carried_line = ""
    if carried:
        names = " and ".join(C.in_sentence(a["label"]) for a in carried)
        carried_line = (f" You did not paste your {names} again, so {'their' if len(carried) > 1 else 'its'} quotes come from "
                        f"your scan of {long_date(carried[0]['from_memory'])}.")
    weighting = (", with client-facing assets such as a proposal weighted highest." if any(a["kind"] in C.CLIENT_FACING for a in res["assets"])
                 else ", each pair of assets weighted by how closely buyers read them.")
    parts.append("<footer>"
                 "<p>Every quote is word for word from what you pasted." + e(carried_line) + " Answers that mean the same thing share a letter. "
                 "The score is counted from the five-question table" + weighting + "</p>"
                 f"<p>{e(rm_line)} The full table, your voice measures and every line edit are in {e(out_docx_name)}.</p>"
                 "</footer>")
    title = f"Brand scan: {biz}"
    page_size = {"a4": "A4", "letter": "letter"}.get(LOCALE["paper"], "auto")
    css = CSS.replace("__PAGE__", page_size)  # built outside the f-string: reusing its quotes inside {} needs Python 3.12
    return ("<!doctype html>\n<html lang=\"" + C.lang_tag(LOCALE) + "\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            f"<meta name=\"generator\" content=\"{C.CREDIT}\">\n<title>{e(title)}</title>\n<style>{css}</style>\n</head>\n<body>\n"
            + "\n".join(parts) + "\n</body>\n</html>\n").replace(
                "<body>", '<body class="dense">' if dense else "<body>", 1)


# ---------------------------------------------------------------- docx

def r_(text, bold=False, italic=False, size=None, colour=None, caps=False):
    p = []
    if bold:
        p.append("<w:b/>")
    if italic:
        p.append("<w:i/>")
    if caps:
        p.append("<w:caps/><w:spacing w:val=\"20\"/>")
    if colour:
        p.append(f'<w:color w:val="{colour}"/>')
    if size:
        p.append(f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>')
    rpr = f"<w:rPr>{''.join(p)}</w:rPr>" if p else ""
    return f'<w:r>{rpr}<w:t xml:space="preserve">{xesc(text)}</w:t></w:r>'


def p_(runs, style=None, before=None, after=None, keep=False, indent=None):
    ppr = []
    if style:
        ppr.append(f'<w:pStyle w:val="{style}"/>')
    if keep:
        ppr.append("<w:keepNext/>")
    if before is not None or after is not None:
        ppr.append(f'<w:spacing w:before="{before or 0}" w:after="{after if after is not None else 120}"/>')
    if indent:
        ppr.append(f'<w:ind w:left="{indent}"/>')
    pp = f"<w:pPr>{''.join(ppr)}</w:pPr>" if ppr else ""
    if isinstance(runs, str) and not runs.startswith("<w:r>"):
        runs = r_(runs)
    return f"<w:p>{pp}{runs}</w:p>"


def tbl(rows, widths, head=True):
    grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in widths)
    none = "".join(f'<w:{s} w:val="nil"/>' for s in ["top", "left", "bottom", "right", "insideH", "insideV"])
    out = [f'<w:tbl><w:tblPr><w:tblW w:w="{sum(widths)}" w:type="dxa"/><w:tblBorders>{none}</w:tblBorders>'
           '<w:tblLayout w:type="fixed"/><w:tblCellMar><w:top w:w="50" w:type="dxa"/><w:left w:w="0" w:type="dxa"/>'
           '<w:bottom w:w="90" w:type="dxa"/><w:right w:w="220" w:type="dxa"/></w:tblCellMar></w:tblPr>'
           f'<w:tblGrid>{grid}</w:tblGrid>']
    for i, row in enumerate(rows):
        cells = []
        for j, val in enumerate(row):
            runs = val if isinstance(val, str) and val.startswith("<w:r>") else r_(
                str(val), bold=(head and i == 0), colour=("6B6B6B" if head and i == 0 else None), size=(16 if head and i == 0 else None),
                caps=(head and i == 0))
            cells.append(f'<w:tc><w:tcPr><w:tcW w:w="{widths[j]}" w:type="dxa"/></w:tcPr>'
                         f'<w:p><w:pPr><w:spacing w:before="0" w:after="0"/></w:pPr>{runs}</w:p></w:tc>')
        out.append(("<w:tr><w:trPr><w:cantSplit/></w:trPr>" if True else "<w:tr>") + "".join(cells) + "</w:tr>")
    out.append("</w:tbl>")
    out.append(p_("", after=80))
    return "".join(out)


def docx_body(ext, res, voice, red):
    b = []
    H = lambda t: b.append(p_(r_(t.upper(), bold=True, size=16, colour="6B6B6B"), before=360, after=120, keep=True))  # noqa: E731
    biz = ext.get("business") or "Your business"
    b.append(p_(r_("Brand consistency scan", caps=True, size=16, colour="6B6B6B"), after=60))
    b.append(p_(r_(biz, size=44), after=40))
    b.append(p_(r_(long_date(ext.get("date") or date.today().isoformat()), colour="6B6B6B"), after=360))
    b.append(p_(r_(f"{res['total']}", size=72) + r_(" of 100  ", colour="6B6B6B") + r_(res["band"], bold=True), after=80))
    facts = res.get("facts") or []
    b.append(p_(r_(top_headline(res), size=28), after=60))
    extra = res["band_line"] + (f" {res['headline']}" if facts else "")
    if res.get("previous_total") is not None:
        extra += f" Last scan, {long_date(res.get('previous_date'))}: {res['previous_total']} of 100."
    if res.get("alignment") is not None:
        extra += f" Alignment with the line you chose: {res['alignment']} of 100."
    b.append(p_(r_(extra, colour="6B6B6B"), after=200))

    if facts:
        H("Facts that disagree")
        b.append(p_(r_("Two assets state different facts. A buyer who reads both will ask which is true, so these come first, "
                       "whatever they cost in points.", colour="6B6B6B"), after=120))
        for f in facts:
            b.append(p_(r_((f.get("what") or "A fact").capitalize(), bold=True), before=80, after=60, keep=True))
            b.append(tbl([["Asset", "In its own words"]] + [[c["label"], r_(f"\u201c{c['quote']}\u201d", italic=True)] for c in f["cells"]],
                         [2800, 6300]))
    also = [x for x in ext.get("also") or [] if isinstance(x, dict)]
    if also:
        labs = {a["id"]: a["label"] for a in res["assets"]}
        H("Also worth fixing")
        b.append(p_(r_("Outside the five questions, these are what a careful buyer would notice.", colour="6B6B6B"), after=120))
        for x in also:
            b.append(p_(r_(x["what"], bold=True) + r_(f"   {labs.get(x['asset'], x['asset'])}", colour="6B6B6B"),
                        before=80, after=40, keep=True))
            if x.get("quote"):
                b.append(p_(r_(f"\u201c{x['quote']}\u201d", italic=True), after=40, indent=360, keep=True))
            b.append(p_(r_(x["note"]), after=120, indent=360))
    ch = ext.get("chosen") if isinstance(ext.get("chosen"), dict) else None
    rec_i = ext.get("recommended", 0)
    rec_if = "" if ch or not ext.get("core_lines") else (ext["core_lines"][rec_i].get("if_you_choose") or "").strip()
    H("The line you chose to align on" if ch else (f"The line to align on, if you choose {rec_if}" if rec_if else "The line to align on"))
    b.append(p_(r_(ch["line"] if ch else ext["core_lines"][rec_i]["line"], size=30), after=80))
    b.append(p_(r_(ch.get("why", "Your own wording, chosen in this scan.") if ch else ext["core_lines"][rec_i].get("rationale", ""),
                   colour="444444"), after=200))
    if ext.get("core_lines"):
        b.append(p_(r_("The three lines considered", bold=True), before=120, after=80, keep=True))
    for i, cl in enumerate(ext.get("core_lines") or []):
        tag = "  Recommended" if i == rec_i else ""
        failed = [GATE_SHORT[k] for k, _ in GATE_KEYS if not (cl["gate"].get(k) or {}).get("pass")]
        b.append(p_(r_(f"{i + 1}. ", bold=True) + r_(cl["line"]) + r_(tag, bold=True, colour="6B6B6B"), after=40, keep=True))
        for k, label in GATE_KEYS:
            g = cl["gate"][k]
            b.append(p_(r_(f"{label} ", colour="6B6B6B") + r_("Yes. " if g["pass"] else "No. ", bold=True) + r_(g["why"]),
                        after=20, indent=360))
        b.append(p_(r_("Fails: " + ", ".join(failed) if failed else "Passes all three tests.", italic=True, colour="6B6B6B")
                    + r_("  " + cl.get("rationale", ""), colour="444444"), after=160, indent=360))

    H("The one thing only you can decide")
    b.append(p_(r_(ext["decide"], size=26), after=120))

    H("Line edits, asset by asset")
    b.append(p_(r_("Each edit replaces one line with one line. Hand this section to whoever updates each asset.", colour="6B6B6B"),
                after=120))
    declined = declined_map(ext)
    if not ext.get("edits") and not declined:
        b.append(p_("No line needs changing: every asset already gives the same answers."))
    by = {}
    for e in ext.get("edits") or []:
        by.setdefault(e["asset"], []).append(e)
    for a in res["assets"]:
        held = [(q, d) for (aid, q), d in declined.items() if aid == a["id"]]
        if a["id"] not in by and not held:
            continue
        if a["id"] not in by:
            b.append(p_(r_(a["label"], bold=True, size=24), before=200, after=80, keep=True))
        b.append(p_(r_(a["label"], bold=True, size=24), before=200, after=80, keep=True))
        for k, e in enumerate(by[a["id"]], 1):
            b.append(p_(r_(f"{k}. {C.QLABEL[e['question']]}", bold=True, colour="444444"), after=40, keep=True))
            if e.get("current"):
                b.append(p_(r_("Now  ", colour="6B6B6B") + r_(f"\u201c{e['current']}\u201d", italic=True), after=40, indent=360, keep=True))
            else:
                where = f" after \u201c{e['after']}\u201d" if e.get("after") else ""
                b.append(p_(r_(f"Not stated. Add it{where}.", colour="6B6B6B"), after=40, indent=360, keep=True))
            b.append(p_(r_("Change to  ", colour="6B6B6B") + r_(e["proposed"], bold=True), after=40, indent=360,
                        keep=bool(e.get("why"))))
            if e.get("why"):
                b.append(p_(r_(e["why"], colour="6B6B6B"), after=140, indent=360))
        for q, d in held:
            note = ("Left as is at your request" + (f": {d['reason']}" if d["reason"] else ".")) if d["by"] != "decision" else (
                "Held until you decide the question above; this one is written for a different buyer on purpose."
                + (f" {d['reason']}" if d["reason"] else ""))
            b.append(p_(r_(f"{C.QLABEL[q]}", bold=True, colour="444444"), after=40, keep=True))
            b.append(p_(r_(note if note.endswith(".") else note + ".", colour="6B6B6B"), after=140, indent=360))

    H("Where your assets disagree, ranked by the points each costs")
    if not res["contradictions"]:
        b.append(p_("No two assets contradict each other. The gaps below are what is left."))
    for i, c in enumerate(res["contradictions"], 1):
        row = next(r for r in res["rows"] if r["q"] == c["q"])
        b.append(p_(r_(f"{i}. {c['label']}", bold=True) + r_(f"   costs {c['cost']} of {row['weight']} points", colour="6B6B6B"),
                    before=120, after=60, keep=True))
        b.append(p_(r_(c["sentence"]), after=60, keep=True))
        rows = [["Asset", "Answer", "In its own words"]]
        for x in c["cells"]:
            if x["relation"] == "skipped":
                continue
            rows.append([x["label"], letter_text(x, row) or "",
                         r_(f"\u201c{x['quote']}\u201d", italic=True) if x["quote"] else r_("Not stated", colour="8A8A8A")])
        b.append(tbl(rows, [2300, 1500, 5300]))

    H("The five questions, asset by asset")
    b.append(p_(r_("Answers that mean the same thing share a letter. \"Close to A\" means a narrower or broader form of answer A.",
                   colour="6B6B6B"), after=120))
    mv = res.get("movement") or {}
    for r in res["rows"]:
        mvs = f", {mv[r['q']]:+d} since last scan" if mv.get(r["q"]) is not None else ""
        b.append(p_(r_(r["label"], bold=True) + r_(f"   {r['points']} of {r['weight']}, {r['status_word'].lower()}{mvs}", colour="6B6B6B"),
                    before=160, after=60, keep=True))
        rows = [["Asset", "Answer", "In its own words"]]
        for x in r["cells"]:
            if x["relation"] == "skipped":
                reason = C.skip_map(ext)[1].get(x["asset"])
                why_skip = ("A proposal's next step is to sign, so it is not scored against your public calls to action."
                            if r["q"] == "next" and x["client_facing"] and r["q"] not in (C.skip_map(ext)[0].get(x["asset"]) or [])
                            else "You said this asset is aimed elsewhere on this question"
                            + (f" ({reason})." if reason else "."))
                rows.append([x["label"], "Not scored", r_(why_skip, colour="8A8A8A")])
                continue
            rows.append([x["label"], letter_text(x, r) or "",
                         r_(f"\u201c{x['quote']}\u201d", italic=True) if x["quote"] else r_("Not stated", colour="8A8A8A")])
        b.append(tbl(rows, [2300, 1500, 5300]))
        comp = (ext.get("compatible") or {}).get(r["q"]) or []
        for it in comp:
            if isinstance(it, (list, tuple)) and len(it) > 2:
                b.append(p_(r_(f"{it[0]} and {it[1]}: {it[2]}", italic=True, colour="6B6B6B"), after=60))

    H("Questions an asset never answers")
    if res["missing"]:
        for m in res["missing"]:
            b.append(p_(r_(f"Your {C.in_sentence(m['asset_label'])} never says {m['phrase']}."), after=40))
    else:
        b.append(p_("Every asset answers every question."))

    H("Voice drift")
    vm = voice.get("assets") or {}
    rows = [["Asset", "Speaks as", "Sentence", "Reads as", "Contractions"]]
    for a in res["assets"]:
        v = vm.get(a["id"])
        if a["kind"] == "agreed" or not v:
            continue
        rows.append([a["label"], f"{v['person']} (I {v['i']}, we {v['we']})",
                     f"{v['avg_sentence_words']:g} words" if v.get("avg_sentence_words") is not None else "too short",
                     f"{v['level']} (grade {v['grade']:g})" if v.get("level") else "too short",
                     f"{v['contractions_per_100']:g} per 100 words" if v.get("contractions_per_100") is not None else "too short"])
    b.append(tbl(rows, [1900, 1800, 1300, 2000, 2100]))
    for f in voice.get("findings") or []:
        b.append(p_(r_("\u2022\t") + r_(f["text"]), after=40, indent=0))
    if not voice.get("findings"):
        b.append(p_("No drift found between the assets measured."))

    H("How the score works")
    b.append(p_("Each asset is read for five questions: who you serve (25 points), what you do (25), the result you promise (20), "
                "why you over the alternatives (20) and what to do next (10). For each question, every pair of assets is compared. "
                "The same answer counts in full, a narrower or broader form of it counts half, a silent asset counts a quarter, "
                "and a different answer counts nothing.", after=80))
    b.append(p_("Pairs are weighted by the assets in them: a proposal, sales deck, onboarding email or invoice 3, the website 2, "
                "LinkedIn 1.5 and anything else 1, because a buyer about to pay reads the client-facing ones most closely. "
                "The arithmetic is done by a script from the table above, never by eye.", after=80))
    removed = dict(red.get("totals") or {})
    if red.get("client_names") is not None:
        removed["client"] = red["client_names"]
    rml = [f"{v} {k if v == 1 else (k + 'es' if k.endswith('ss') else k + 's')}" for k, v in
           [("client name", removed.get("client", 0)), ("fee", removed.get("fee", 0)),
            ("email address", removed.get("email", 0)), ("phone number", removed.get("phone", 0)),
            ("street address", removed.get("address", 0)), ("postal code", removed.get("postcode", 0)),
            ("bank or registration number", removed.get("bank", 0))] if v]
    rm = (", ".join(rml[:-1]) + " and " + rml[-1]) if len(rml) > 1 else "".join(rml)
    H("What was taken out")
    b.append(p_((f"Before anything was read, {rm} {'was' if len(rml) == 1 and rml[0].startswith('1 ') else 'were'} removed from what "
                 f"you pasted. They do not appear in this document and are not saved." if rm else
                 "No client names, fees or contact details were found in what you pasted. Nothing personal is saved.")
                + (" Your own contact and payment details were left out of the reading too." if red.get("own_contact") else "")))
    return "".join(b)


STYLES_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Helvetica Neue" w:hAnsi="Helvetica Neue" w:cs="Arial" w:eastAsia="Arial"/>
<w:sz w:val="20"/><w:szCs w:val="20"/><w:color w:val="111111"/><w:lang w:val="__LANG__"/></w:rPr></w:rPrDefault>
<w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="276" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
</w:styles>"""


def write_docx(path, body, title):
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
           'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
           f'<w:body>{body}<w:sectPr><w:pgSz w:w="{12240 if LOCALE["paper"] == "letter" else 11906}" '
           f'w:h="{15840 if LOCALE["paper"] == "letter" else 16838}"/>'
           '<w:pgMar w:top="1300" w:right="1400" w:bottom="1300" w:left="1400" w:header="500" w:footer="500" w:gutter="0"/>'
           '</w:sectPr></w:body></w:document>')
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    core = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            f'<dc:title>{xesc(title)}</dc:title><dc:creator>Merigrove Brand Consistency Scan</dc:creator>'
            f'<dc:description>{C.CREDIT}</dc:description>'
            f'<dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>'
            f'<dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified></cp:coreProperties>')
    app = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
           '<Application>Merigrove Brand Consistency Scan</Application></Properties>')
    ctypes = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
              '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
              '<Default Extension="xml" ContentType="application/xml"/>'
              '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
              '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
              '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
              '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
              '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
            '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
            '</Relationships>')
    doc_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
                '</Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ctypes)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", doc)
        z.writestr("word/styles.xml", STYLES_XML.replace("__LANG__", C.lang_tag(LOCALE)))
        z.writestr("word/_rels/document.xml.rels", doc_rels)
        z.writestr("docProps/core.xml", core)
        z.writestr("docProps/app.xml", app)


def docx_text(body):
    return re.sub(r"<[^>]+>", " ", body.replace("</w:p>", "\n"))


# ---------------------------------------------------------------- results for memory

def results_for_memory(ext, res, voice):
    align = chosen_alignment(ext)
    ch = ext.get("chosen") if isinstance(ext.get("chosen"), dict) else None
    line = ch["line"] if ch else ext["core_lines"][ext["recommended"]]["line"]
    by = "founder" if ch and ch.get("by") != "memory" else ("memory" if ch else "recommended")
    agreed = dict(ext.get("agreed_answers") or {})
    for r in res["rows"]:
        if r["q"] in agreed:
            continue
        g = align.get(r["q"])
        if g and g != "new":
            pick = sorted([c for c in r["cells"] if c["group"] == g], key=lambda c: (c["client_facing"], -c["weight"]))
            if pick:
                agreed[r["q"]] = pick[0]["quote"]
        elif g == "new":
            ed = next((e for e in ext.get("edits") or [] if e.get("question") == r["q"]), None)
            if ed:
                agreed[r["q"]] = ed["proposed"]
    quotes = {}
    for r in res["rows"]:
        for c in r["cells"]:
            quotes.setdefault(c["asset"], {})[r["q"]] = c["quote"]
    vm = voice.get("assets") or {}
    return {
        "skill": C.SKILL, "business": ext.get("business", ""), "date": ext.get("date") or date.today().isoformat(),
        "founder_sells": ext.get("founder_sells", "me"),
        "locale": {k: LOCALE.get(k) for k in ("country", "english", "paper", "dates", "clock", "decimal")},
        "core_line": line, "core_line_by": by,
        "agreed_answers": agreed,
        "scores": dict({r["q"]: r["points"] for r in res["rows"]}, total=res["total"], alignment=res.get("alignment")),
        "assets": [dict(a, quotes=quotes.get(a["id"], {})) for a in res["assets"] if a["kind"] != "agreed"],
        "skip": C.skip_map(ext)[0],
        "skip_reasons": C.skip_map(ext)[1],
        "declined": [{"asset": a, "question": q, "by": d["by"], "reason": d["reason"]} for (a, q), d in declined_map(ext).items()],
        "sold_by": ext.get("sold_by") or {},
        "english_source": ENGLISH_SOURCE,
        "excluded": ext.get("excluded") or [],
        "voice": {k: {x: v.get(x) for x in ["words", "person", "i", "we", "you", "avg_sentence_words", "grade", "level",
                                              "contractions_per_100", "measurable"]} for k, v in vm.items()},
        "edits_proposed": len(ext.get("edits") or []),
    }


# ---------------------------------------------------------------- main

def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("extraction")
    a.add_argument("--voice", required=True)
    a.add_argument("--redaction", required=True)
    a.add_argument("--out", required=True)
    a.add_argument("--previous")
    a.add_argument("--results")
    args = a.parse_args()
    xp = Path(args.extraction)
    ext = C.load_json(xp, "extraction file")
    voice = C.load_json(args.voice, "voice file")
    red = C.load_json(args.redaction, "redaction file")
    prev = C.load_json(args.previous, "previous run file") if args.previous else None
    if not isinstance(ext, dict):
        C.stop("the extraction file must be one JSON object.")
    ext.setdefault("date", date.today().isoformat())
    res = SC.score(ext, prev)  # validates shape; STOP on a table that cannot be scored
    res["also"] = [x for x in ext.get("also") or [] if isinstance(x, dict)]
    base = xp.resolve().parent
    texts = VQ.asset_texts(ext, base)
    kinds = {x["id"]: x["kind"] for x in ext["assets"]}
    sources = [t for k, t in texts.items() if kinds.get(k) != "agreed"]
    said = [str(x) for x in ext.get("founder_said") or [] if str(x).strip()]
    for i, x in enumerate(said, 1):
        if len(C.words(x)) > 40:
            C.stop(f"founder_said {i} is over 40 words; keep only the founder's own sentence that gives the fact.")
    claim_sources = sources + said  # facts the founder gave in chat, in their words, may be written into edits
    public = [t for k, t in texts.items() if kinds.get(k) not in C.CLIENT_FACING and kinds.get(k) != "agreed"]
    sells = ext.get("founder_sells") or voice.get("founder_sells") or "me"
    global LOCALE, ENGLISH_SOURCE
    loc = dict(ext.get("locale") or {})
    ENGLISH_SOURCE = "founder" if loc.get("english") else None
    if not loc.get("english") and voice.get("english"):
        loc["english"] = voice["english"]  # counted from the founder's own spelling
        ENGLISH_SOURCE = "counted"
    if not loc.get("country") and prev and (prev.get("locale") or {}).get("country"):
        loc = dict(prev["locale"], **{k: v for k, v in loc.items() if v})
        if not ENGLISH_SOURCE and loc.get("english"):
            ENGLISH_SOURCE = prev.get("english_source") or "country"
    LOCALE = C.resolve_locale(loc)
    if LOCALE.get("english") and not ENGLISH_SOURCE:
        ENGLISH_SOURCE = "country"
    if not LOCALE.get("decimal") and red.get("decimal_style"):
        LOCALE["decimal"] = red["decimal_style"]

    decimal = LOCALE.get("decimal") or red.get("decimal_style") or C.detect_decimal(sources)
    # plausibility: a scan where no asset answers any question means the table was not filled from the assets
    if not any(c for q in C.QKEYS for c in (ext["answers"].get(q) or {}).values()):
        C.stop("no asset answers any of the five questions, so a score of 0 would be meaningless. Check the extraction "
               "was filled from the clean copies, or ask the founder for the pages that say who they serve and what they do.")
    live = {k: t for k, t in texts.items() if kinds.get(k) != "agreed"
            and not next((a.get("from_memory") for a in ext["assets"] if a["id"] == k), None)}
    problems, _ok = VQ.check(ext, base)
    problems += gate_lines(ext, res, claim_sources, sells, ext.get("founder", ""), decimal)
    if not problems:
        problems += gate_edits(ext, res, claim_sources, decimal, live, ext.get("founder", ""))
    problems += gate_decide(ext)
    problems += gate_also(ext)
    for label, text in CC.written_fields(ext):
        pr, _w = CC.check(text, claim_sources)
        problems += [f"copy, {label}: {x}" for x in pr]
    problems += gate_locale(ext, claim_sources, LOCALE["english"])
    if problems:
        for p in problems:
            print("PROBLEM:", p)
        print(f"{len(problems)} problems. Nothing was written. Fix the extraction file and run again.")
        sys.exit(1)

    biz_slug = C.slug(ext.get("business"))
    stem = f"brand-scan-{biz_slug}-{ext['date']}"
    docx_name = f"{stem}-line-edits.docx"
    page = html_report(ext, res, voice, red, docx_name)
    body = docx_body(ext, res, voice, red)
    page_text = re.sub(r"<style.*?</style>|<[^>]+>", " ", page, flags=re.S)
    priv = gate_privacy([("the one-page report", html.unescape(page_text)), ("the line-edits document", html.unescape(docx_text(body)))],
                        red.get("hashes") or [], public)
    if priv:
        for p in priv:
            print("PROBLEM:", p)
        print(f"{len(priv)} problems. Nothing was written. Fix the extraction file and run again.")
        sys.exit(1)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{stem}.html").write_text(page, encoding="utf-8")
    write_docx(out / docx_name, body, f"Brand consistency scan: {ext.get('business') or ''}")
    rp = Path(args.results) if args.results else base / "results.json"
    rp.write_text(json.dumps(results_for_memory(ext, res, voice), indent=2), encoding="utf-8")
    print(f"SCORE: {res['total']} of 100 ({res['band']}). {res['headline']}")
    paper = {"a4": "A4", "letter": "Letter"}.get(LOCALE["paper"], "the viewer's default paper (country not known)")
    print(f"LOCALE: prints on {paper}; dates as {long_date(ext['date'])}; "
          f"{C.english_label(LOCALE['english'], LOCALE['country'])} checked in the copy; language tag {C.lang_tag(LOCALE)}.")
    print(f"WROTE: {out / (stem + '.html')}")
    print(f"WROTE: {out / docx_name}")
    print(f"WROTE: {rp} (for the memory file; not for the founder)")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print(f"STOP: the report could not be built ({type(e).__name__}: {e}). Nothing usable was written; check the extraction file.")
        sys.exit(2)
