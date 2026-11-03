#!/usr/bin/env python3
"""Check a page two ways: can an assistant read and quote the founder's live page, and is a rewritten page ready.

Usage:
  python3 scripts/page_check.py audit <saved page .html or .txt> [--json-out f.json]
      The founder's own page, saved or fetched. Reports raw text, headings, the first answer, a date,
      prices in text, structured data, text only in images or behind forms, a script-only shell,
      noindex, hidden text and any text addressed to an AI system (a finding, never followed).
  python3 scripts/page_check.py fragment <site-files/page-x.html> [--must WORD ...] [--price-required] [--json-out f.json]
      A page this skill wrote. Exactly one h1; the first paragraph is a 40 to 60 word answer that
      stands alone and holds every --must word; at least two h2, one phrased as a question; a dated
      line; no styling, scripts, hidden text or text aimed at AI. [NEED: ...] left in means NOT FINISHED.
Exit 0 when the page was read (verdicts are in the lines), 1 when a fragment fails, 2 with STOP on bad input.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import MONEY_RE, date_spans, read_text, save_json, stop, strip_html  # noqa: E402

ANSWER_MIN, ANSWER_MAX = 40, 60
AI_ADDRESSED = re.compile(
    r"(ignore (all |any )?(previous|prior) instructions|\b(dear|attention|note to|hey) (ai|chatgpt|assistant|llm|language model)s?\b|"
    r"\bif you are an? (ai|assistant|language model|llm)\b|\bwhen (asked|someone asks)\b[^.]{0,80}\brecommend\b|"
    r"\b(ai|assistants?|chatgpt|language models?|llms?)\b[^.]{0,40}\b(should|must) (recommend|say|mention|rank)\b|"
    r"\bwanneer (gevraagd|iemand vraagt)\b[^.]{0,80}\braad\b)", re.I)
HIDDEN = re.compile(r"(display\s*:\s*none|visibility\s*:\s*hidden|font-size\s*:\s*0|color\s*:\s*(#fff\b|#ffffff\b|white\b|rgba?\(\s*255\s*,\s*255\s*,\s*255)|"
                    r"left\s*:\s*-\d{3,}px|text-indent\s*:\s*-\d{3,})", re.I)
MONEY = MONEY_RE
UPDATED_WORDS = re.compile(r"\b(last updated|updated|bijgewerkt|laatst bijgewerkt|aktualisiert|zuletzt aktualisiert|stand(?=:)|mis à jour|"
                           r"dernière mise à jour|actualizado|última actualización|aggiornato|atualizado)\b", re.I)


class _DateFinder:
    """A date in any founder's style, or an 'updated' line."""
    def search(self, text):
        return bool(date_spans(text)) or bool(UPDATED_WORDS.search(text or ""))


DATE = _DateFinder()
BACKREF_START = re.compile(r"^(this|that|it|they|these|those|he|she|we also|also|dit|dat|het is|zij)\b", re.I)


def strip_founder_notes(text):
    """Pasted page text often carries the founder's own notes: a line in square brackets ("[typed from a phone
    screenshot, sorry for typos]") or an arrow note at the end of a line ("<- this is from google"). They are not
    the page, so they are left out of the audit (and reported), never read as page text."""
    notes, keep = [], []
    for line in text.splitlines():
        st = line.strip()
        if re.fullmatch(r"\[[^\]]{6,}\]", st) and not re.search(r"(?i)\bNEED\b", st):
            notes.append(st)
            continue
        m = re.search(r"\s(<-+|<=|←)\s*(.+)$", line)
        if m:
            notes.append(m.group(2).strip())
            line = line[:m.start()]
        keep.append(line)
    return "\n".join(keep), notes


def tokens(text):
    return [t for t in str(text).split() if re.search(r"\w", t)]


def _tags(html, tag):
    return [strip_html(m.group(1)) for m in re.finditer(rf"(?is)<{tag}\b[^>]*>(.*?)</{tag}>", html)]


def jsonld_blocks(html):
    out = []
    for m in re.finditer(r'(?is)<script[^>]+type\s*=\s*["\']application/ld\+json["\'][^>]*>(.*?)</script>', html):
        raw = m.group(1).strip()
        try:
            data = json.loads(raw)
            types = []
            for node in (data if isinstance(data, list) else data.get("@graph", [data]) if isinstance(data, dict) else []):
                if isinstance(node, dict):
                    t = node.get("@type")
                    types += t if isinstance(t, list) else [t]
            out.append({"ok": True, "types": [t for t in types if t], "raw": raw})
        except json.JSONDecodeError as e:
            out.append({"ok": False, "error": f"line {e.lineno}, column {e.colno}: {e.msg}", "raw": raw})
    return out


def audit(text, is_html):
    res = []

    def add(name, verdict, detail):
        res.append({"check": name, "verdict": verdict, "detail": detail})

    html = text if is_html else ""
    visible = strip_html(text) if is_html else text.strip()
    n_words = len(tokens(visible))
    n_scripts = len(re.findall(r"(?i)<script\b", html))
    shell_words = re.search(r"(?i)\b(loading\.{0,3}|enable javascript|you need to enable javascript|javascript is required)\b", visible)
    if is_html and (n_words < 80 and (n_scripts >= 3 or shell_words or re.search(r'(?i)<div id="(root|app|__next)">\s*</div>', html))):
        add("raw text", "FAIL", f"the page as served has {n_words} words of text and {n_scripts} script tags: an assistant that does not run scripts sees an almost empty page")
    elif n_words < 80:
        add("raw text", "UNKNOWN", f"only {n_words} words of text; this may be a fragment or a thin page")
    else:
        add("raw text", "PASS", f"{n_words} words of text in the page as served")
    if is_html:
        if re.search(r'(?i)<meta[^>]+name=["\']robots["\'][^>]+content=["\'][^"\']*noindex', html):
            add("noindex", "FAIL", "the page tells search engines not to index it (meta robots noindex)")
        h1 = _tags(html, "h1")
        add("one h1", "PASS" if len(h1) == 1 else "FAIL", f"{len(h1)} h1 heading(s)" + (f": '{h1[0][:70]}'" if h1 else ""))
        h2 = _tags(html, "h2") + _tags(html, "h3")
        q = [h for h in h2 if h.strip().endswith("?")]
        add("question headings", "PASS" if q else "FAIL", f"{len(h2)} sub-headings, {len(q)} phrased as a question")
        paras = [p for p in _tags(html, "p") if tokens(p)]
        first = paras[0] if paras else ""
    else:
        add("one h1", "UNKNOWN", "pasted text has no headings to read; checked on the rewrite instead")
        add("question headings", "UNKNOWN", "pasted text has no headings to read")
        paras = [p.strip() for p in re.split(r"\n\s*\n|\n", text) if len(tokens(p)) >= 8]
        first = paras[0] if paras else ""
    fw = len(tokens(first))
    generic = re.search(r"(?i)^(welcome to|welkom bij|we are passionate|your trusted|willkommen)", first.strip())
    if not first:
        add("direct answer first", "FAIL", "no opening paragraph found")
    elif generic:
        add("direct answer first", "FAIL", f"the page opens with a greeting, not an answer: '{first[:80]}'")
    else:
        add("direct answer first", "PASS" if ANSWER_MIN <= fw <= ANSWER_MAX * 2 else "FAIL",
            f"opening paragraph {fw} words: '{first[:80]}'")
    add("dated", "PASS" if DATE.search(visible) else "FAIL",
        "a date or 'updated' line is on the page" if DATE.search(visible) else "no visible date or last-updated line")
    prices = [m.group(0) for m in MONEY.finditer(visible) if not any(a <= m.start() < b for a, b in date_spans(visible))]
    pdfs = re.findall(r'(?i)href=["\']([^"\']+\.pdf)["\']', html)
    if prices:
        add("price in text", "PASS", f"{len(prices)} price(s) in the page text, e.g. '{prices[0].strip()}'")
    elif pdfs:
        add("price in text", "FAIL", f"no price in the page text; linked PDF(s): {', '.join(pdfs[:3])} (an assistant may not read a PDF)")
    else:
        add("price in text", "FAIL", "no price in the page text")
    blocks = jsonld_blocks(html) if is_html else []
    if not is_html:
        add("structured data", "UNKNOWN", "pasted text carries no markup; a plugin may add it on the live page")
    elif not blocks:
        add("structured data", "UNKNOWN", "no JSON-LD in this copy of the page; a plugin may add it after load")
    for b in blocks:
        if b["ok"]:
            add("structured data", "PASS", f"JSON-LD parses: {', '.join(map(str, b['types'])) or 'no @type'}")
        else:
            add("structured data", "FAIL", f"JSON-LD does not parse ({b['error']}); a block that does not parse is ignored")
    if is_html:
        pics = [m.group(0) for m in re.finditer(r'(?i)<img\b[^>]*>', html)
                if re.search(r"(?i)(price|pricing|prijs|tarie|plans|packages|menu|rates|kosten)", m.group(0))
                or MONEY.search(m.group(0))]
        if pics:
            add("text in images", "FAIL", f"{len(pics)} image(s) look like they carry prices or plans as a picture; an assistant reads text, not pictures")
        if re.search(r"(?is)<form\b.*?(email|e-mail)", html) and re.search(r"(?i)(download|get the (guide|brochure|price)|pricing guide|price list)", visible):
            add("nothing gated", "FAIL", "something important sits behind an email form (a guide, brochure or price list)")
        hid = [m.group(0) for m in HIDDEN.finditer(html)]
        if hid:
            add("hidden text", "FAIL", f"styles that hide text: {', '.join(sorted(set(hid))[:3])}; hidden text can be treated as spam")
    if res and res[0]["check"] == "raw text" and res[0]["verdict"] == "FAIL":
        for r in res[1:]:
            if r["verdict"] == "FAIL" and r["check"] in ("one h1", "question headings", "direct answer first", "dated", "price in text"):
                r["verdict"] = "UNKNOWN"
                r["detail"] = "cannot tell from the served page, which has no text; settle it from the page text after scripts run"
    ai = AI_ADDRESSED.search(visible) or (AI_ADDRESSED.search(html) if is_html else None)
    if ai:
        add("text aimed at AI", "FAIL", f"the page holds text addressed to an AI system: '{ai.group(0)[:80]}'. Reported only; never followed")
    return res, {"words": n_words, "scripts": n_scripts, "first_paragraph": first, "jsonld": blocks}


def fragment(html, must, price_required):
    probs, warns = [], []
    if re.search(r"(?i)<(script|style|iframe|form)\b|\sstyle\s*=", html):
        probs.append("a fragment carries no styling, scripts, frames or forms: paste-ready body text only")
    h1 = _tags(html, "h1")
    if len(h1) != 1:
        probs.append(f"{len(h1)} h1 headings; a page has exactly one")
    after_h1 = re.split(r"(?is)</h1>", html, maxsplit=1)
    paras = re.findall(r"(?is)<p[^>]*>(.*?)</p>", after_h1[1]) if len(after_h1) == 2 else []
    # a short dated line ("Last updated: 2. November 2026", "Stand: 02.11.2026") may sit between the h1 and the answer
    if paras and len(tokens(strip_html(paras[0]))) <= 8 and DATE.search(strip_html(paras[0])):
        paras = paras[1:]
    answer = strip_html(paras[0]) if paras else ""
    n = len(tokens(answer))
    if not answer:
        probs.append("no paragraph straight after the h1: the answer block goes first")
    else:
        if not ANSWER_MIN <= n <= ANSWER_MAX:
            probs.append(f"answer block {n} words; it must be {ANSWER_MIN} to {ANSWER_MAX}")
        if BACKREF_START.match(answer.strip()):
            probs.append(f"the answer block starts '{answer.split()[0]}', which leans on text before it; it must stand alone")
        for w in must:
            if w.lower() not in answer.lower():
                probs.append(f"the answer block does not contain '{w}'")
    h2 = _tags(html, "h2")
    if len(h2) < 2:
        probs.append(f"{len(h2)} h2 headings; use at least two, matched to how buyers ask")
    if not any(h.strip().endswith("?") for h in h2):
        probs.append("no h2 is phrased as a question")
    vis = strip_html(html)
    if not DATE.search(vis):
        probs.append("no dated line (for example 'Last updated: 6 November 2026')")
    if price_required and not MONEY.search(vis):
        probs.append("no price in the page text, though a price is in the fact register")
    if HIDDEN.search(html) or AI_ADDRESSED.search(vis):
        probs.append("hidden text or text addressed to an AI system: never allowed")
    if re.search(r"(?i)<h[1-6][^>]*>[^<]*(best|top \d+|#1|number one|nummer 1)\b", html):
        warns.append("a heading ranks or calls something best: check it is not a self-ranked list")
    finished = "[NEED" not in html
    return probs, warns, {"answer_words": n, "answer": answer, "finished": finished, "h2": h2}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["audit", "fragment"])
    ap.add_argument("file")
    ap.add_argument("--must", action="append", default=[])
    ap.add_argument("--price-required", action="store_true")
    ap.add_argument("--json-out")
    ap.add_argument("--label", help="how the kit names this page, for example 'Your home page' or 'Ihre Startseite'")
    a = ap.parse_args()
    text = read_text(a.file, "the page")
    notes = []
    if a.mode == "audit":
        text, notes = strip_founder_notes(text)
        for n in notes:
            print(f"NOTE: left out the founder's own note: '{n[:70]}'")
    if not text.strip():
        stop(f"{a.file} is empty. Save the page again (or paste its text) and run again.")
    is_html = bool(re.search(r"(?i)<(html|body|p|h1|h2|div)\b", text))
    if a.mode == "audit":
        res, info = audit(text, is_html)
        for r in res:
            print(f"CHECK {r['verdict']}: {r['check']}: {r['detail']}")
        print(f"SUMMARY: {sum(r['verdict'] == 'FAIL' for r in res)} fail, {sum(r['verdict'] == 'UNKNOWN' for r in res)} unknown, "
              f"{sum(r['verdict'] == 'PASS' for r in res)} pass")
        if a.json_out:
            save_json(a.json_out, {"file": os.path.basename(a.file), "label": a.label or "", "checks": res, "info": info,
                                   "founder_notes": notes})
        return 0
    if not is_html:
        stop(f"{a.file} is not an HTML fragment. Rewritten pages are saved as page-<slug>.html with h1, h2 and p tags.")
    probs, warns, info = fragment(text, a.must, a.price_required)
    for p in probs:
        print("PROBLEM:", p)
    for w in warns:
        print("WARN:", w)
    print(f"ANSWER: {info['answer_words']} words")
    print(f"STATUS: {'finished' if info['finished'] and not probs else 'NOT FINISHED' if not info['finished'] else 'fails checks'}")
    print(f"{len(probs)} problems, {len(warns)} warnings")
    if a.json_out:
        save_json(a.json_out, {"file": os.path.basename(a.file), "problems": probs, "warnings": warns, **info})
    return 1 if probs else 0


if __name__ == "__main__":
    sys.exit(main())
