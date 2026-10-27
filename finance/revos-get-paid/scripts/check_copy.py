#!/usr/bin/env python3
"""Check founder-facing copy and the chase messages against the banned patterns and the figures.

Usage:
  python3 scripts/check_copy.py <file>                                  check any text or markdown
  python3 scripts/check_copy.py --text "some copy"                      check a string
  python3 scripts/check_copy.py --chasers <chasers.md> --results <results.json>
        check every message: banned patterns, the facts each one must carry (invoice, amount, due
        date, the one ask), every figure against the calculation, no threat the founder has not
        chosen, no legal threat at all, and no statement of what any law allows
Prints PROBLEM and WARN lines and a count. Exit 0 clean, 1 problems found, 2 STOP.
Standard library only. The lists mirror references/banned-patterns.md.
"""
import argparse
import calendar
import json
import re
import sys
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

PROBLEM_PATTERNS = {
    "[\u2014\u2013]": "em or en dash",
    r"\bin today'?s (fast-paced|digital|ever-changing)": "stock opener",
    r"\bit'?s not (just )?[^.]{1,40}, it'?s\b": "contrast reveal",
    r"\b(game[- ]changer|delve|unlock(s|ing)?|elevate(s|d)?|seamless(ly)?|leverag(e|es|ing))\b": "filler word",
    r"\b(I mean|to be honest|if I'?m being honest|let'?s be real)\b": "announced honesty",
    # this skill's list (references/banned-patterns.md)
    r"\bkindly\b": "'kindly' reads as passive aggressive in a chaser",
    r"\b(as per|per) my (last|previous) (email|message)\b": "'as per my last email'",
    r"\bI hope (this|you) (email )?finds? you well\b": "stock opener",
    r"\b(no|left with no|have no) (other )?(choice|option) but\b": "cornered threat",
    r"\bguarantee[sd]?\b": "certainty the founder cannot promise",
    # stating what a law says, or naming a country's rules
    r"\b(the law|by law|under (the )?law|statute|statutory|legislation)\b[^.]{0,40}\b(allow|let|permit|entitle|require|say|give|set)s?\b": "states what a law allows or requires",
    r"\b(statutory|legally (entitled|obliged|required|bound)|you are (legally )?entitled to|by law)\b": "states what a law allows or requires",
    r"\b[A-Z][a-z]+ (of )?(Commercial )?(Debts?|Payments?) (\(Interest\) )?Act\b|\bAct (19|20)\d\d\b": "names a statute",
    r"\b(HM[R]C|I[R]S|ATO|IRAS|CRA)\b": "names a country's tax or government body",
    r"\b(small business commissioner|county court|small claims court)\b": "names a country's institution",
    r"\b(U[K]|US|U\.S\.|Australian|British|American|federal|state) (law|rules?|statute)\b": "assumes a country's law",
    r"(\b(calculat\w+|work\w* out|add\w*|charg\w+|includ\w+|incl\.?|plus)|\+) (the |any )?(VAT|GST|HST|sales tax|tax due|income tax)\b": "computes or charges tax",
    r"\[STAT\]|\[VERIFY\]": "internal placeholder left in founder copy; use [NEED: ...]",
}
WARN_PATTERNS = {
    r"\bmore\b": "'more' as an intensifier: is a specific comparison possible?",
    r"!": "exclamation mark in business copy",
    r"\b(robust|cutting[- ]edge|world[- ]class|best[- ]in[- ]class|innovative)\b": "vague superlative",
    r"\bjust (checking|following|circling|touching) (in|up|back|base)\b": "'just checking in' undersells the ask",
    r"\bfriendly reminder\b": "'friendly reminder' is a stock phrase; say what is due",
    r"\bsorry to (bother|chase|trouble)\b": "apologising for asking to be paid",
    r"\bas previously (mentioned|stated)\b": "'as previously mentioned'",
    r"\b(URGENT|ACTION REQUIRED|IMMEDIATE(LY)?)\b": "shouting in capitals",
}
# Steps a message may name only in the final notice, and only the one the founder chose.
CHOSEN_STEPS = {
    "lawyer": r"\b(lawyers?|solicitors?|attorneys?|legal counsel)\b",
    "collections": r"\b(debt collect\w*|collections? (service|agency)|collection agency|debt recovery (agency|service))\b",
    "pause": r"\b(pause|stop|suspend|hold)\b[^.]{0,30}\b(work|services?|deliver\w*|project|support)\b",
    "advice": r"\btake advice\b",
}
# Threats and legal steps this skill never writes into a message, at any stage.
NEVER = (r"\b(court|legal action|legal proceedings|proceedings|sue|suing|lawsuit|litigation|judg(e)?ment|ccj|bailiffs?|"
         r"sheriff|enforcement|letter before (action|claim)|demand letter|credit (rating|score|file|bureau|report\w*)|"
         r"blacklist\w*|name and shame|report you|post about|public review|bad review|online review|google review|leave a review|\d[- ]star|social media|linkedin|facebook)\b")
FEE_WORDS = r"\b(interest|late fee|late payment fee|late charge|penalt(y|ies)|surcharge)\b"
MAX_WORDS = 230  # prose only; payment plan lines are data and are not counted
PLAN_LINE = re.compile(r"^(instal\w*|install\w*|payment)\s+\d+\s*:", re.I)

_SYM = (r"(?:US\$|AU\$|A\$|CA\$|C\$|NZ\$|S\$|HK\$|R\$|\$|£|€|₹|¥|₱|₦|₩|₪|₺|฿|RM|zł|Kč|kr|"
        r"R(?=\s?\d)|\b(?:GBP|EUR|USD|AUD|CAD|NZD|SGD|HKD|INR|ZAR|AED|CHF|JPY|SEK|NOK|DKK|PLN|CZK|BRL|MXN|MYR|PHP|THB|KRW|CNY)\b)")
_NUM = r"\d{1,3}(?:[  ']\d{3})+(?:[.,]\d+)?|\d[\d.,]*\d|\d"
MONEY_RE = re.compile(rf"(?:{_SYM})\s?({_NUM})(\s?k\b)?|({_NUM})\s?(?:{_SYM})")
PCT_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s?(?:%|per cent|percent)")
BARE_DOT = re.compile(r"(?<![\w.,/:-])(\d{1,3}(?:,\d{3})+\.\d{2}|\d+\.\d{2})(?![\w%])")
BARE_COMMA = re.compile(r"(?<![\w.,/:-])(\d{1,3}(?:\.\d{3})+,\d{2}|\d+,\d{2})(?![\w%])")
# Spellings that give away the wrong English for the founder (the script's own words and close cousins).
NOT_US = r"\b(instalments?|authoris\w*|organis\w*|recognis\w*|apologis\w*|prioritis\w*|finalis\w*)\b"
NOT_UK = r"\b(installments?|authoriz\w*)\b"


def _num(s, dec):
    s = s.replace(" ", "").replace(" ", "").replace("'", "")
    if dec == "comma":
        return s.replace(".", "").replace(",", ".")
    if dec == "dot":
        return s.replace(",", "")
    if re.search(r",\d{1,2}$", s) and not re.search(r"\.\d{1,2}$", s):  # no style known: read 1.200,50 the way it is written
        return s.replace(".", "").replace(",", ".")
    return s.replace(",", "")


def pct_value(token):
    return Decimal(token.replace(",", ".")).normalize()


def spelling_problems(text, locale):
    loc = str(locale or "").strip().lower().replace("_", "-")
    if not loc.startswith("en"):
        return []
    if loc in {"en-us", "en-ph"}:
        pat, want = NOT_US, "American"
    elif loc == "en-ca":
        pat, want = r"\b(authoris\w*|organis\w*)\b", "Canadian"
    else:
        pat, want = NOT_UK, "the founder's"
    return [f"'{m.group(0)}' is not {want} spelling" for m in re.finditer(pat, text, re.I)]


def stop(msg):
    print(f"STOP: {msg}. Nothing was checked.")
    sys.exit(2)


def _snip(text, m):
    return text[max(0, m.start() - 25):m.end() + 25].replace("\n", " ").strip()


def check(text, max_words=None, max_chars=None):
    problems, warns = [], []
    for pat, why in PROBLEM_PATTERNS.items():
        flags = 0 if pat.startswith((r"\b[A-Z]", r"\b(HM")) else re.I
        for m in re.finditer(pat, text, flags):
            problems.append(f"{why}: '{_snip(text, m)}'")
    for pat, why in WARN_PATTERNS.items():
        for m in re.finditer(pat, text, re.I if pat != r"\b(URGENT|ACTION REQUIRED|IMMEDIATE(LY)?)\b" else 0):
            warns.append(f"{why}: '{_snip(text, m)}'")
    words = len(re.findall(r"\b\w[\w'-]*\b", text))
    if max_words and words > max_words:
        problems.append(f"{words} words, limit {max_words}")
    if max_chars and len(text) > max_chars:
        problems.append(f"{len(text)} characters, limit {max_chars}")
    return problems, warns, words


def money_values(text, bare=False, dec=None):
    vals = []
    for m in MONEY_RE.finditer(text):
        raw = m.group(1) or m.group(3)
        try:
            v = Decimal(_num(raw, dec))
        except InvalidOperation:
            continue
        if m.group(2):
            v *= 1000
        vals.append((v.quantize(Decimal("0.01")), m.group(0).strip()))
    if bare:
        for m in (BARE_COMMA if dec == "comma" else BARE_DOT).finditer(text):
            if not any(m.group(1) in raw for _, raw in vals):
                vals.append((Decimal(_num(m.group(1), dec)).quantize(Decimal("0.01")), m.group(1)))
    return vals


def date_pattern(iso, order=None):
    """A date as the founder writes it: month-first for MDY, day-first otherwise; ISO always."""
    d = date.fromisoformat(iso)
    names = [calendar.month_name[d.month], calendar.month_abbr[d.month]] + (["Sept"] if d.month == 9 else [])
    mon = "|".join(names)
    day = str(d.day)
    yr = rf"(/({d.year}|{str(d.year)[2:]}))?"
    dm = rf"\b{day}(st|nd|rd|th)?\s+(of\s+)?({mon})\.?\b|\b0?{d.day}[/.]0?{d.month}{yr}\b"
    md = rf"\b({mon})\.?\s+{day}(st|nd|rd|th)?\b|\b0?{d.month}/0?{d.day}{yr}\b"
    forms = md if order == "MDY" else (dm if order in ("DMY", "YMD") else f"{dm}|{md}")
    return re.compile(rf"({forms}|{iso})", re.I)


def _q(x):
    return Decimal(x).quantize(Decimal("0.01"))


def allowed_money(res, cl, p):
    vals = set()
    for r in res["invoices"]:
        if r["client"] == cl["name"]:
            for k in ("amount", "outstanding", "interest", "fee", "total", "daily", "disputed_part", "total_shown"):
                if r.get(k):
                    vals.add(_q(r[k]))
            for _, pa in r.get("payments", []):
                vals.add(_q(pa))
    if p:
        for k in ("owed", "interest", "fee", "total", "daily"):
            vals.add(_q(p[k]))
        vals.add(_q(Decimal(p["interest"]) + Decimal(p["fee"])))
        if p.get("plan"):
            vals.add(_q(p["plan_total"]))
            for _, a in p["plan"]:
                vals.add(_q(a))
    return vals


def all_money(res):
    vals = set()
    for v in res["totals"].values():
        if isinstance(v, str):
            vals.add(_q(v))
    for cl in res["clients"]:
        vals.add(_q(cl["owed"]))
        for p in ([cl["now"]] if cl["now"] else []) + cl["later"]:
            vals |= allowed_money(res, cl, p)
        vals |= allowed_money(res, cl, None)
        if cl.get("paid_late_fee"):
            vals.add(_q(cl["paid_late_fee"]))
    pv = res.get("prevention") or {}
    for k in ("example_price",):
        if pv.get(k):
            vals.add(_q(pv[k]))
    for k in ("deposit_example", "milestone_example"):
        for a in pv.get(k) or []:
            vals.add(_q(a))
    return vals


def all_rates(res):
    out = set()
    own = res.get("own_terms") or {}
    if own.get("annual_rate"):
        out.add(Decimal(own["annual_rate"]).normalize())
    for src in (own.get("clause"), own.get("rate_typed"), own.get("fee_typed"), own.get("rate_basis")):
        for m in PCT_RE.finditer(str(src or "")):
            out.add(pct_value(m.group(1)))
    pv = res.get("prevention") or {}
    if pv.get("deposit_pct"):
        out.add(Decimal(pv["deposit_pct"]).normalize())
    for m in pv.get("milestones") or []:
        out.add(Decimal(m).normalize())
    return out


def check_note_figures(note, res):
    problems = []
    ok = all_money(res)
    for v, raw in money_values(note, bare=not res.get("currency"), dec=res.get("decimal_style")):
        if v not in ok:
            problems.append(f"figure {raw} is not one the calculation produced")
    rates = all_rates(res)
    for m in PCT_RE.finditer(note):
        if pct_value(m.group(1)) not in rates:
            problems.append(f"percentage {m.group(0)} is not a rate the calculation used")
    for m in re.finditer(NEVER, note, re.I):
        problems.append(f"legal threat or step this skill never writes: '{_snip(note, m)}'")
    return problems


def check_chasers(text, res):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from chase_plan import expected_chasers, parse_chasers, ACTIONS  # noqa: E402
    problems, warns = [], []
    found = parse_chasers(text)
    exp = expected_chasers(res)
    ids = [c.get("id") for c in found]
    for cid in exp:
        if cid not in ids:
            problems.append(f"{cid}: message missing (or its marker lines were changed)")
    for cid in ids:
        if cid not in exp:
            problems.append(f"{cid}: not a message the plan scheduled; do not add or rename messages")
    if text.count("<!-- chaser") != len(found):
        problems.append("a message marker has no matching '<!-- end -->' line")
    bare = not res.get("currency")
    dec, order = res.get("decimal_style") or None, res.get("date_order")
    for c in found:
        cid = c.get("id")
        if cid not in exp:
            continue
        cl, p = exp[cid]
        whole = c["subject"] + "\n" + c["body"]
        tag = cid
        pr, wa, _ = check(whole)
        problems += [f"{tag}: {x}" for x in pr]
        warns += [f"{tag}: {x}" for x in wa]
        prose = "\n".join(line for line in whole.splitlines() if not PLAN_LINE.match(line.strip()))
        words = len(re.findall(r"\b\w[\w'-]*\b", prose))
        if words > MAX_WORDS:
            problems.append(f"{tag}: {words} words; a message should be under {MAX_WORDS}")
        if not c["subject"]:
            problems.append(f"{tag}: no subject line")
        kind = c.get("kind", "")
        nums = cl["disputed"] if kind == "dispute" else cl["invoices"]
        for n in nums:
            if not re.search(rf"(?<![\w-]){re.escape(n)}(?![\w-])", whole):
                problems.append(f"{tag}: invoice {n} is not named")
        ok = allowed_money(res, cl, p)
        for v, raw in money_values(whole, bare=bare, dec=dec):
            if v not in ok:
                problems.append(f"{tag}: figure {raw} is not one the calculation produced for this client")
        rates = all_rates(res)
        for m in PCT_RE.finditer(whole):
            if pct_value(m.group(1)) not in rates:
                problems.append(f"{tag}: percentage {m.group(0)} is not a rate from your terms")
        for m in re.finditer(NEVER, whole, re.I):
            problems.append(f"{tag}: legal threat or step this skill never writes: '{_snip(whole, m)}'")
        action = cl.get("final_action", "advice")
        for key, pat in CHOSEN_STEPS.items():
            for m in re.finditer(pat, whole, re.I):
                if not (kind.startswith("final") and key == action):
                    where = ("only the final notice may name a next step, and only the one the founder chose"
                             if not kind.startswith("final") else f"the founder chose '{ACTIONS.get(action, action)}', not this")
                    problems.append(f"{tag}: '{_snip(whole, m)}': {where}")
        if re.search(r"\b(final|last)( (and|or) \w+)? (notice|reminder|demand|warning|chance|request|opportunity)\b|\bfinal\b(?! (files?|cut|edit|version|deliverables?|delivery|draft|design|images?|photos?|video|footage|assets?|artwork|report|invoice|phase|stage|payment|instalment|installment|handover|walkthrough|inspection))", whole, re.I) and not kind.startswith("final"):
            problems.append(f"{tag}: 'final' before the final notice")
        fee_ok = p is not None and p.get("fees") and (kind in {"late_fee", "final", "call_plan"} or p.get("terms_named"))
        if not fee_ok:
            for m in re.finditer(FEE_WORDS, whole, re.I):
                problems.append(f"{tag}: '{_snip(whole, m)}': a late fee or interest is only raised when your own contract sets one, and not at this stage")
        problems += [f"{tag}: {x}" for x in spelling_problems(whole, res.get("locale"))]
        if "[NEED" in whole or "[NEED" in c["to"]:
            warns.append(f"{tag}: has a [NEED: ...] the founder must fill before sending")
        if p is None:
            continue
        key_amount = p["total"] if kind in {"late_fee", "final"} else p["owed"]
        if _q(key_amount) not in {v for v, _ in money_values(whole, bare=bare, dec=dec)}:
            problems.append(f"{tag}: the amount due ({key_amount}) is not stated")
        dues = sorted(r["due_date"] for r in res["invoices"] if r["client"] == cl["name"] and r["number"] in cl["invoices"])
        if dues and not date_pattern(dues[0], order).search(whole):
            problems.append(f"{tag}: the due date ({dues[0]}) is not stated")
        if p.get("pay_by"):
            if not date_pattern(p["pay_by"], order).search(whole):
                problems.append(f"{tag}: the pay-by date ({p['pay_by']}) is missing: every message after the first names one date to pay by")
        elif "?" not in c["body"]:
            problems.append(f"{tag}: the first reminder should end on one question (when will it be paid?)")
        if p.get("first"):
            for r in res["invoices"]:
                if r["client"] != cl["name"] or r["number"] not in cl["invoices"]:
                    continue
                if r.get("part_disputed") and _q(r["disputed_part"]) not in {v for v, _ in money_values(whole, bare=bare, dec=dec)}:
                    problems.append(f"{tag}: the first message must name the disputed part of {r['number']} ({r['disputed_part']}) and offer to settle it")
                if r.get("total_shown") and p.get("fresh") and not re.search(r"\bcorrect(ed|ion)\b", whole, re.I):
                    problems.append(f"{tag}: the invoice they have shows the wrong total; say a corrected invoice is attached")
        if p.get("plan"):
            lines = [ln for ln in whole.splitlines() if PLAN_LINE.match(ln.strip())]
            for i, (d, a) in enumerate(p["plan"]):
                hit = [ln for ln in lines if re.match(rf"(instal\w*|install\w*|payment)\s+{i + 1}\b", ln.strip(), re.I)
                       and _q(a) in {v for v, _ in money_values(ln, bare=bare, dec=dec)} and date_pattern(d, order).search(ln)]
                if not hit:
                    problems.append(f"{tag}: the payment plan line {i + 1} ({a} by {d}) is missing or changed; keep each line as the script wrote it")
                    break
        if c["body"].count("?") > 2:
            warns.append(f"{tag}: several questions; keep to one next step")
        if kind.startswith("final") and not re.search(CHOSEN_STEPS[action], whole, re.I):
            problems.append(f"{tag}: the final notice must say the one thing the founder will do next ({ACTIONS[action]})")
    return problems, warns


def main():
    a = argparse.ArgumentParser()
    a.add_argument("file", nargs="?")
    a.add_argument("--text")
    a.add_argument("--chasers")
    a.add_argument("--results")
    a.add_argument("--max-words", type=int)
    a.add_argument("--max-chars", type=int)
    args = a.parse_args()
    if args.chasers:
        if not args.results:
            stop("--chasers needs --results <results.json> from the compute step")
        for f in (args.chasers, args.results):
            if not Path(f).exists():
                stop(f"there is no file at {f}")
        try:
            res = json.loads(Path(args.results).read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            stop(f"{args.results} is not valid JSON")
        if not isinstance(res, dict) or res.get("skill") != "revos-get-paid":
            stop("that results file did not come from chase_plan.py compute")
        problems, warns = check_chasers(Path(args.chasers).read_text(encoding="utf-8"), res)
        for x in problems:
            print("PROBLEM:", x)
        for x in warns:
            print("WARN:", x)
        print(f"{len(problems)} problems, {len(warns)} warnings")
        sys.exit(1 if problems else 0)
    if args.text is None and (not args.file or not Path(args.file).exists()):
        stop(f"there is no file at {args.file}")
    text = args.text if args.text is not None else Path(args.file).read_text(encoding="utf-8")
    problems, warns, words = check(text, args.max_words, args.max_chars)
    for m in re.finditer(NEVER, text, re.I):
        problems.append(f"legal threat or step this skill never writes: '{_snip(text, m)}'")
    for x in problems:
        print("PROBLEM:", x)
    for x in warns:
        print("WARN:", x)
    print(f"{len(problems)} problems, {len(warns)} warnings, {words} words, {len(text)} characters")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
