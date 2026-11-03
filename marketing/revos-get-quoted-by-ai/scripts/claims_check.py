#!/usr/bin/env python3
"""The fact register and the claims gate: nothing goes on a page that the founder did not give.

Usage:
  python3 scripts/claims_check.py register <facts.json>
      Checks the register: every fact has a kind, a value as the founder wrote it, a status
      (confirmed, NEED or declined), a source, and a confirmed date when confirmed.
  python3 scripts/claims_check.py check <facts.json> --source <pasted text> [--source ...] <file> [<file> ...]
        [--no-entities]
      Reads every page fragment, JSON-LD file, llms.txt or text file and fails any price, number,
      year, web address, email, phone number or invention-prone term (tiers, awards, guarantees, tax
      or regulation words, review counts) that is not in the confirmed register (figures may also
      come from a buyer's own question, with --panel), and any capitalised name or place that is in
      neither the register nor what the founder pasted. Old page copy is not proof: its claims count
      only once the founder confirms them in the register. Prices must also be written as the founder writes them (€ 4.800 stays
      € 4.800). Machine fields in JSON-LD are matched by value. Declined facts must not appear at all.
      --no-entities skips the capitalised-name check for languages that capitalise every noun.
Exit 0 clean, 1 with PROBLEM lines, 2 with STOP. No network calls.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import MONEY_NUM, MONEY_RE, date_spans, fold, load_json, norm, read_text, stop, strip_html  # noqa: E402
from locale_numbers import Ambiguous, Unreadable, find_currency, parse_number  # noqa: E402

KINDS = {"name", "location", "area", "service", "audience", "price", "duration", "team", "person", "credential",
         "years", "count", "result", "url", "booking", "phone", "email", "address", "hours", "language", "other"}
STATUSES = {"confirmed", "NEED", "declined"}
NUM = MONEY_NUM
NUM_RE = re.compile(NUM)
URL_RE = re.compile(r"\bhttps?://[^\s\"'<>)]+|\b(?:www\.)?[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:example|com|net|org|io|co|nl|au|ca|uk|ae|de|fr|es|app|dev|ai)(?:/[^\s\"'<>)]*)?\b", re.I)
EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
PHONE_RE = re.compile(r"(?:\+\d{1,3}[\s.-]?)?(?:\(\d{1,4}\)[\s.-]?)?\d{2,4}[\s.-]\d{3,4}[\s.-]?\d{3,4}\b")
RISKY = ["pre-seed", "preseed", "tier", "tiers", "retainer", "guarantee", "guaranteed", "garantie", "award", "award-winning",
         "certified", "accredited", "gecertificeerd", "rated", "five-star", "5-star", "stars", "reviews", "beoordelingen",
         "tax", "taxes", "payroll", "compliance", "compliant", "regulation", "regulatory", "gdpr", "avg", "privacy act", "hipaa",
         "iso", "insured", "licensed", "established", "founded", "since", "sinds", "number one", "#1", "leading", "best",
         "top-rated", "trusted by", "years of experience", "jaar ervaring", "clients", "klanten", "satisfaction", "money-back",
         "free consultation", "gratis", "discount", "korting", "sr&ed", "audit-ready", "investor-ready", "24/7", "fastest", "cheapest"]
# Promise and comparison language: a page may say it only where a confirmed fact says it (the fact's own words).
# The softer phrases ("always", "in writing", "on time") count only in a sentence where the business commits to
# something (we, our, the business name, "you get", "you can"); advice to the buyer ("ask any provider for it in
# writing") is not a promise. The rest count wherever they appear.
WEAK = {"always", "never", "any time", "in writing", "before any", "after every", "every time", "on time", "a promise or superlative"}
COMMIT = re.compile(r"(?i)\b(we|we'?ll|we'?re|our|ours|us|wir|unser\w*|uns|wij|we|onze|ons|nous|notre|nos|nosotros|nuestr\w*|"
                    r"you (will |can |'ll )?(get|receive|can|have|pay|keep)|sie (erhalten|bekommen|können)|u (krijgt|kunt)|"
                    r"vous (recevez|pouvez)|usted (recibe|puede)|clients|customers|kunden|klanten)\b")
PROMISES = [
    (r"\balways\b", "always"), (r"\bnever\b", "never"), (r"\bany ?time\b", "any time"), (r"\bguarantee[sd]?\b", "guarantee"),
    (r"\brefund(s|ed|able)?\b", "refund"), (r"\bmoney[- ]back\b", "money back"), (r"\b(no|zero) risk\b|\brisk[- ]free\b", "no risk"),
    (r"\bno (hidden|extra) (fees?|costs?|charges?)\b", "no hidden costs"), (r"\bin writing\b", "in writing"),
    (r"\bbefore (any|every)\b", "before any"), (r"\bafter every\b", "after every"), (r"\bevery (time|single)\b", "every time"),
    (r"\b(the )?most (affordable|experienced|trusted|popular|reliable|reputable|qualified|recommended|loved)\b", "most ..."),
    (r"\b(quickest|lowest|biggest|largest|cheapest price|lowest price)\b", "a superlative"),
    (r"\baffordable\b", "affordable"), (r"\bon time\b", "on time"), (r"\bno obligation\b", "no obligation"),
    (r"\bwill (increase|improve|save|grow|boost|double|raise|cut|reduce)\b", "a promised result"),
    (r"\b(increase|improve|boost|double|grow)s? (your )?(sales|orders|bookings|revenue|enquiries|leads)\b", "a promised result"),
    (r"\b(higher|more) (orders|sales|bookings|revenue|enquiries)\b", "a promised result"),
    (r"\b100 ?%", "100%"),
    # German, Dutch, French, Spanish: softer words first (they count only where the business commits), then the rest
    (r"\b(immer|niemals|nie|jederzeit|pünktlich|altijd|nooit|op elk moment|op tijd|toujours|jamais|à tout moment|à l'heure|"
     r"siempre|nunca|en cualquier momento|a tiempo)\b", "a promise or superlative"),
    (r"\b(garantiert|garantie|erstattung|rückerstattung|günstigste[nrs]?|schnellste[nrs]?|beste[nrs]?|billigste[nrs]?|risikofrei|"
     r"terugbetaling|goedkoopste|snelste|risicovrij|gegarandeerd|remboursement|remboursé|moins cher|le plus rapide|sans risque|"
     r"garanti|reembolso|más barato|el más rápido|sin riesgo|garantizado)\b", "a promise or comparison"),
]
ALWAYS_OK = {"faq", "i", "ok", "q", "a", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
             "january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november",
             "december", "last", "updated", "laatst", "bijgewerkt", "written", "geschreven"}


def _num(s, dec):
    """A number token as a value, or None when it is not one number (a date such as 02.11.2026, a phone fragment)."""
    s = re.sub(r"[\s\u00a0\u202f]", "", s).rstrip(".,")
    for style in (dec, "dot"):
        try:
            return round(parse_number(s, style)[0], 2)
        except (Ambiguous, Unreadable, ValueError, TypeError, OverflowError):
            continue
    return None


def _compact(s):
    return re.sub(r"[\s  ]+", "", s).replace(",-", "").replace(",\u2013", "")


def validate_register(reg):
    probs = []
    facts = reg.get("facts")
    if not isinstance(facts, list) or not facts:
        stop("facts.json has no 'facts' list. Each fact: kind, value (as the founder wrote it), status, source.")
    for i, f in enumerate(facts, 1):
        lab = f"fact {i} ({f.get('label') or f.get('kind', '?')})"
        if f.get("kind") not in KINDS:
            probs.append(f"{lab}: kind must be one of {', '.join(sorted(KINDS))}")
        if f.get("status") not in STATUSES:
            probs.append(f"{lab}: status must be confirmed, NEED or declined")
        if not (f.get("source") or "").strip():
            probs.append(f"{lab}: no source (pasted page, founder said, document)")
        if f.get("status") == "confirmed" and not (f.get("value") or "").strip():
            probs.append(f"{lab}: confirmed with no value")
        if f.get("status") == "confirmed" and not f.get("confirmed_on"):
            probs.append(f"{lab}: confirmed facts carry the date they were confirmed")
        if f.get("status") == "NEED" and not (f.get("need") or "").strip():
            probs.append(f"{lab}: a NEED fact says what would fill it (need)")
    return probs


def _texts(path):
    """Return (prose text, machine values list, is_json)."""
    raw = read_text(path, "a file to check")
    if path.endswith(".json"):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            return None, [], f"{os.path.basename(path)} is not valid JSON (line {e.lineno}: {e.msg})"
        prose, machine = [], []

        def walk(o, key=""):
            if isinstance(o, dict):
                for k, v in o.items():
                    walk(v, k)
            elif isinstance(o, list):
                for v in o:
                    walk(v, key)
            elif isinstance(o, (int, float)) and not isinstance(o, bool):
                machine.append((key, str(o)))
            elif isinstance(o, str):
                if key.startswith("@") or key in ("priceCurrency", "addressCountry", "inLanguage", "currency"):
                    return
                if key in ("price", "minPrice", "maxPrice", "value", "postalCode", "telephone", "foundingDate", "datePublished", "dateModified"):
                    machine.append((key, o))
                else:
                    prose.append(o)
        walk(data)
        return "\n".join(prose), machine, None
    if path.endswith((".html", ".htm")):
        return strip_html(raw), [], None
    return raw, [], None


def check(reg, sources, files, entities=True, questions=""):
    """sources: the founder's paste, used only to recognise names and places. Figures, prices, links,
    contact details and risky terms must be in the register (or, for figures, a buyer's own question)."""
    probs = []
    dec = reg.get("decimal")
    confirmed = [f for f in reg["facts"] if f.get("status") == "confirmed"]
    declined = [f for f in reg["facts"] if f.get("status") == "declined"]
    reg_text = " \n".join(f"{f.get('label', '')} {f.get('value', '')}" for f in confirmed) + " " + " ".join(reg.get("allow") or [])
    src_text = "\n".join(sources)
    vocab = norm(reg_text + " " + src_text + " " + questions + " " + reg.get("business", ""))
    strict = (reg_text + " " + questions + " " + reg.get("business", "")).lower()
    vocab_words = set(vocab.split())
    reg_money = []
    for f in confirmed:
        for m in MONEY_RE.finditer(f.get("value", "")):
            n = m.group("n1") or m.group("n2")
            reg_money.append((_num(n, dec), _compact(m.group(0)), find_currency(m.group(0)), m.group(0).strip()))
    allow = [str(x) for x in (reg.get("allow") or [])]
    reg_nums = {v for v in (_num(m.group(0), dec) for t in [f.get("value", "") for f in confirmed] + allow for m in NUM_RE.finditer(t))
                if v is not None}
    src_nums = {v for v in (_num(m.group(0), dec) for m in NUM_RE.finditer(questions)) if v is not None}
    words_num = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
                 "eleven": 11, "twelve": 12, "twee": 2, "drie": 3, "vier": 4, "vijf": 5, "zes": 6}
    for w, v in words_num.items():
        if re.search(rf"\b{w}\b", (reg_text + " " + questions).lower()):
            reg_nums.add(float(v))
    for path in files:
        name = os.path.basename(path)
        prose, machine, err = _texts(path)
        if err:
            probs.append(err)
            continue
        dates = date_spans(prose)
        in_date = lambda s: any(a <= s < b for a, b in dates)  # noqa: E731
        money_spans = []
        for m in MONEY_RE.finditer(prose):
            if in_date(m.start()):
                continue
            money_spans.append(m.span())
            n = m.group("n1") or m.group("n2")
            v = _num(n, dec)
            hits = [r for r in reg_money if r[0] == v]
            if not hits:
                probs.append(f"{name}: price '{m.group(0).strip()}' is not in the fact register")
            elif _compact(m.group(0)) not in {h[1] for h in hits}:
                probs.append(f"{name}: '{m.group(0).strip()}' is written differently from the founder ('{hits[0][3]}'); copy their form")
            elif hits[0][2] and find_currency(m.group(0)) and find_currency(m.group(0)) != hits[0][2]:
                probs.append(f"{name}: '{m.group(0).strip()}' uses a different currency from the register")
        for m in NUM_RE.finditer(prose):
            if in_date(m.start()) or any(a <= m.start() < b for a, b in money_spans):
                continue
            ctx = prose[max(0, m.start() - 1):m.end() + 1]
            if re.match(r"[A-Za-z]", ctx[:1]) and m.start() > 0:  # part of a word like B2B or H1
                continue
            v = _num(m.group(0), dec)
            if v is None or v in reg_nums or v in src_nums:
                continue
            probs.append(f"{name}: number '{m.group(0)}' is not in the fact register or what the founder pasted")
        for key, val in machine:
            if key in ("price", "minPrice", "maxPrice", "value"):
                v = _num(str(val), "dot")
                if v is not None and v not in {r[0] for r in reg_money} and v not in reg_nums:
                    probs.append(f"{name}: {key} {val} is not a figure in the fact register")
            elif key in ("telephone", "postalCode", "foundingDate") and norm(val) not in norm(reg_text):
                probs.append(f"{name}: {key} '{val}' is not in the fact register")
        low = prose.lower()
        for u in set(URL_RE.findall(prose)) | {v for k, v in machine if str(v).startswith("http")}:
            d = re.sub(r"^https?://(www\.)?", "", u.lower()).rstrip("/.")
            if d.split("/")[0] not in strict:
                probs.append(f"{name}: web address '{u}' is not in the fact register")
        for e in set(EMAIL_RE.findall(prose)):
            if e.lower() not in strict:
                probs.append(f"{name}: email '{e}' is not in the fact register")
        for p in set(PHONE_RE.findall(prose)):
            if re.sub(r"\D", "", p) not in re.sub(r"\D", "", reg_text):
                probs.append(f"{name}: phone number '{p.strip()}' is not in the fact register")
        for term in RISKY:
            if re.search(rf"(?<![\w-]){re.escape(term)}(?![\w-])", low) and not re.search(rf"(?<![\w-]){re.escape(term)}(?![\w-])", strict):
                probs.append(f"{name}: '{term}' is not something the founder said; remove it or confirm it in the register")
        strict_f = fold(strict)
        for sent in re.split(r"(?<=[.?!:;])\s+|\n+", prose):
            sl = sent.lower()
            commits = bool(COMMIT.search(sent)) or any(fold(b) and fold(b) in fold(sent) for b in [reg.get("business", "")] if b)
            for pat, what in PROMISES:
                for m in re.finditer(pat, sl):
                    if fold(m.group(0)) and fold(m.group(0)) in strict_f:
                        continue
                    if what in WEAK and not commits:
                        continue
                    probs.append(f"{name}: '{m.group(0)}' ({what}) is a promise or comparison the founder did not make: "
                                 f"'{sent.strip()[:90]}'. Cut it, or confirm the founder's own words for it in the register")
        for f in declined:
            val = (f.get("value") or "").strip()
            if val and len(val) > 2 and norm(val) in norm(prose):
                probs.append(f"{name}: '{val}' was declined by the founder and must not appear")
        if entities:
            for sent in re.split(r"(?<=[.?!:])\s+|\n+", prose):
                toks = re.findall(r"[A-Za-zÀ-ÿ][\w'&-]*", sent)
                for k, t in enumerate(toks):
                    t = re.sub(r"['\u2019]s$", "", t)
                    if k == 0 or not t[0].isupper() or t.lower() in ALWAYS_OK:
                        continue
                    if norm(t) in vocab_words or norm(t) in vocab:
                        continue
                    probs.append(f"{name}: '{t}' looks like a name, place or product not in the register or the paste "
                                 "(headings go in sentence case; real names go in the register)")
    seen, out = set(), []
    for p in probs:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["register", "check"])
    ap.add_argument("facts")
    ap.add_argument("files", nargs="*")
    ap.add_argument("--source", action="append", default=[])
    ap.add_argument("--no-entities", action="store_true")
    ap.add_argument("--panel", help="the checked panel: buyers' own questions may carry their own figures")
    a = ap.parse_args()
    reg = load_json(a.facts, "the fact register")
    probs = validate_register(reg)
    if a.mode == "register":
        for p in probs:
            print("PROBLEM:", p)
        c = sum(f.get("status") == "confirmed" for f in reg["facts"])
        nd = sum(f.get("status") == "NEED" for f in reg["facts"])
        dl = sum(f.get("status") == "declined" for f in reg["facts"])
        print(f"REGISTER: {c} confirmed, {nd} NEED, {dl} declined")
        print(f"{len(probs)} problems")
        return 1 if probs else 0
    if probs:
        for p in probs:
            print("PROBLEM:", p)
        print("Fix the register first.")
        return 1
    if not a.files:
        stop("name the files to check (site-files/*.html, *.json, llms.txt).")
    sources = [read_text(s, "a source file") for s in a.source]
    qtext = ""
    if a.panel:
        pan = load_json(a.panel, "the panel")
        qtext = " ".join(q.get("text", "") for q in pan.get("questions", []) if not q.get("cut"))
    probs = check(reg, sources, a.files, entities=not a.no_entities, questions=qtext)
    for p in probs:
        print("PROBLEM:", p)
    print(f"CLAIMS: {len(a.files)} file(s) checked against {sum(f.get('status') == 'confirmed' for f in reg['facts'])} confirmed facts")
    print(f"{len(probs)} problems")
    return 1 if probs else 0


if __name__ == "__main__":
    sys.exit(main())
