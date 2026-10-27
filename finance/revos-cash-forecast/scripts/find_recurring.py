#!/usr/bin/env python3
"""Find the regular bills, regular receipts, everyday spending and one-offs in a parsed bank export, list
payments that look like tax or other government payments, and write a draft forecast inputs file the founder
corrects rather than fills in.

Usage:
  python3 scripts/find_recurring.py <transactions.json> --out <scratch>/forecast-inputs.json
        [--memory-json <scratch>/previous.json] [--today YYYY-MM-DD] [--business "Name"]

<transactions.json> is what parse_bank_csv.py wrote. With --memory-json (from memory.py read), saved
labels, categories and ignored items are applied, and saved answers (currency, date order, safety line,
client payment habits, known payments the founder listed) are carried into the draft.

Tax, payroll taxes and other government payments are never projected from the export. Payments that look
like one are listed under TAX-LIKE SEEN for the founder to confirm; what goes into the forecast is what the
founder lists (what, amount, date or rhythm), labelled founder supplied.

Prints the list to show the founder (REGULAR OUT, REGULAR IN, TAX-LIKE SEEN, EVERYDAY, ONE-OFFS, FLOOR) and
writes the draft. Exit 0 on success, 2 with a STOP line on bad input. Standard library only. No network calls.
"""
import argparse
import json
import re
import statistics
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cashlib import InputError, from_iso, iso, long_date, money, month_end, set_number_style, set_style  # noqa: E402

# Words banks add to descriptions, from several countries' exports. Stripped before payees are grouped.
NOISE = re.compile(
    r"\b(card payment to|card payment|payment to|direct debit to|direct debit|standing order to|standing order|"
    r"faster payment to|faster payment|bill payment to|bill payment|contactless card purchase|contactless|"
    r"counter credit|funds transfer|bank giro credit|card purchase|debit card purchase|pos debit|pos purchase|"
    r"ach debit|ach credit|ach|online transfer|online banking transfer|wire transfer|wire|zelle|recurring|"
    r"purchase|online payment|mobile payment|paynow|giro|bpay|osko|eftpos|interac|e-transfer|"
    r"dd|so|sto|fpo|fpi|bgc|bp|tfr|vis|pos|deb|cr|dr|ref|reference|on|via|ltd|limited|plc|llc|inc|pte|pty|corp|co|"
    r"the|bacs|faster|payment|card|transfer|debit|credit|ppd|ccd|web|id|orig|des|indn|checkcard|acb|eft|ib|"
    r"debit order|magtape|internet banking|immediate payment|rtc|confirmation|conf|trn|seq|pmt det)\b", re.I)
SOFTWARE = re.compile(r"google|gsuite|workspace|microsoft|msft|office 365|adobe|xero|quickbooks|intuit|"
                      r"sage|slack|zoom|notion|canva|hubspot|shopify|aws|amazon web|dropbox|figma|mailchimp|calendly|"
                      r"linkedin|openai|anthropic|github|atlassian|squarespace|wix|godaddy|apple\.com|icloud|monday\.com|"
                      r"asana|clickup|airtable|zapier|docusign|1password|lastpass|webflow|klaviyo|semrush|myob|gusto|"
                      r"deel|rippling", re.I)
RULES = [  # category, pattern: plain words, no country's institutions
    ("payroll", r"salary|salaries|wages|payroll|net pay|pay run"),
    ("owner pay", r"dividend|drawings|owner'?s? draw|director'?s? (loan|pay)|owner pay|distribution"),
    ("pension", r"pension|retirement|401k|superannuation"),
    ("rent", r"\brent\b|landlord|wework|regus|office space|co-?working|serviced office|letting|property management"),
    ("insurance", r"insurance|insur|assurance|policy|premium|\bins prem\b"),
    ("loan or lease", r"\blease\b|leasing|hire purchase|car finance|van finance|equipment finance|\bloan\b|"
                      r"loan repay|loan pmt|finance repay|mortgage"),
    ("credit card", r"amex|american express|card repayment|credit card|card payment thank|card bill|autopay"),
    ("phone and utilities", r"telecom|mobile|broadband|internet|wireless|water|electric|energy|power|gas bill|utility|"
                            r"utilities|verizon|at&t|comcast|singtel|telstra|vodafone"),
    ("accountant", r"accountant|accountancy|accounting|bookkeep|cpa\b|chartered|tax adviser|tax advisor"),
    ("own transfer", r"to savings|tfr to|transfer to (my|own|savings|reserve|tax|sav\b)|pot transfer|to pot|savings|reserve acc|"
                     r"tax pot|tax reserve|internal transfer|own account|to isa|between accounts"),
    ("bank charges", r"account fee|monthly fee|service charge|service fee|commission|bank charge|maintenance fee|plan fee"),
]
OWN_IN = re.compile(r"from savings|tfr from|transfer from|pot transfer|from pot|internal transfer|own account|"
                    r"director'?s? loan|capital introduced|owner contribution|loan drawdown|loan proceeds|\bloan\b|"
                    r"tax refund|refund of tax|between accounts", re.I)
PROCESSORS = re.compile(r"stripe|paypal|square|gocardless|sumup|zettle|izettle|shopify|worldpay|adyen|"
                        r"klarna|amazon payments|etsy|ebay|toast|clover", re.I)
# Payments that look like tax or another government payment. Generic words only: the founder confirms which
# they are, and nothing found here is projected.
# Generic payroll-tax and social-charge acronyms are listed here only so the line is shown to the founder and left
# out; nothing is ever worked out from them.
TAX_LIKE = re.compile(r"tax(?!i)|\bvat\b|\bgst\b|\bhst\b|\bpst\b|sales tax|withholding|revenue|customs|\bduty\b|"
                      r"social security|government|\bgovt\b|treasury|payroll tax|\bpaye\b|\bemp ?201\b|\beftps\b|"
                      r"\bfica\b|\bfuta\b|\bsuta\b|\b94[01]\b|\bcpf\b|\bpayg\b|\bsss\b|\buif\b|\bsdl\b|\bepf\b|"
                      r"\besic?\b|\btds\b|\bsocso\b|national insurance|social insurance|\bnic\b|\burssaf\b", re.I)


_CUT = re.compile(r"\s(?:CO ID|ID|INDN|SND BK|PMT DET|TRN|SEQ|Confirmation#?|Conf#?|REF|Ref)\s*[:#]", re.I)


def clean_desc(desc):
    """The payee part of a bank description, without the codes banks add: 'GUSTO DES:NET B0BC77 ID:7KX3Q9M18
    INDN:...' becomes 'GUSTO NET'; a wire's 'ORIG:NORTHWIND HEALTH SYS ID:...' becomes 'NORTHWIND HEALTH SYS';
    'CHECKCARD 0502 AMAZON WEB SERVICES ...' becomes 'AMAZON WEB SERVICES ...'. Generic: no bank is assumed."""
    s = re.sub(r"\s+", " ", str(desc or "")).strip()
    m = re.search(r"\bORIG(?:INATOR)?\s*:\s*(.+?)(?=\s+(?:ID|SND BK|PMT DET|OBI|REF)\s*:|$)", s, re.I)
    if m and re.search(r"\bWIRE\b", s, re.I):
        return m.group(1).strip()
    m = re.search(r"\bDES\s*:\s*", s)
    if m:
        payee, rest = s[:m.start()].strip(), s[m.end():]
        c = _CUT.search(" " + rest)
        rest = (" " + rest)[:c.start()] if c else rest
        s = f"{payee} {rest}"
    else:
        c = _CUT.search(s)
        s = s[:c.start()] if c else s
    s = re.sub(r"^(?:CHECKCARD|CHECK CARD|DEBIT CARD|POS PURCHASE|POS DEBIT|PURCHASE|CARD PURCHASE)\s+\d{4}\s+", "", s, flags=re.I)
    toks = [w for w in s.split() if not re.search(r"\d", w) or re.fullmatch(r"\d{1,2}(?:st|nd|rd|th)?", w, re.I)]
    return " ".join(toks).strip() or str(desc or "").strip()


DEPOSIT = re.compile(r"\b(?:DEP|DEPOSIT|ADVANCE|UPFRONT|\d{2}\s?(?:PCT|%))\b", re.I)
NOT_DEPOSIT = re.compile(r"\b(?:MOBILE|ATM|BRANCH|CASH|CHECK|CHEQUE|REMOTE|COUNTER)\b", re.I)
REF = re.compile(r"(?:PMT DET|REF(?:ERENCE)?|INV(?:OICE)?)\s*[:#.-]?\s*[A-Z]*-?\d[\w-]*|\b(?:DEP(?:OSIT)?|BAL(?:ANCE)?|"
                 r"FINAL|\d{2}\s?PCT)\b", re.I)


def ref_of(desc):
    """The invoice number or deposit and balance words in a receipt, so the founder's own claims can be checked."""
    found = []
    for mt in REF.finditer(str(desc or "")):
        x = re.sub(r"^PMT DET\s*:\s*", "", mt.group(0).strip(), flags=re.I)
        if x.upper() not in (f.upper() for f in found):
            found.append(x)
    return ", ".join(found[:3])


def key_of(desc):
    s = clean_desc(desc).lower()
    s = re.sub(r"\*\w+", " ", s)
    s = " ".join(w for w in s.split() if not re.search(r"\d", w))
    s = NOISE.sub(" ", s)
    s = re.sub(r"[^a-z& ]", " ", s)
    words = [w for w in s.split() if len(w) > 1]
    return " ".join(words[:3]) or str(desc or "").lower()[:12]


KEEP_UPPER = {"vat", "gst", "aws", "llc", "llp", "plc", "pte", "pty", "ach", "atm", "usa", "uk", "us", "nz", "sg", "au",
              "paye", "cpf", "uif"}
TWO_LETTER_WORDS = {"to", "of", "co", "on", "at", "by", "in", "de", "la", "an", "or", "my", "is", "it", "as", "up", "no",
                    "do", "go", "me", "we", "be", "so", "if", "am", "us", "el", "le", "da", "di", "du", "en", "et"}
SMALL = {"to", "and", "of", "for", "the", "a", "on", "at", "by"}
WORDS = {"tfr": "transfer", "sal": "salary", "dd": "", "so": "", "sto": "", "fpo": "", "fpi": "", "bgc": "", "vis": "",
         "bp": "", "deb": "", "pos": ""}


LABEL_PREFIX = re.compile(r"^(?:(?:debit order|direct debit|standing order|ib payment to|ib transfer to|ib payment|"
                          r"acb credit|acb debit|eft credit|eft debit|eft payment|credit transfer|internet banking|"
                          r"online banking|faster payment to|faster payment|bill payment to|bill payment|card payment to|"
                          r"card payment|payment to|pos purchase|pos debit|ach debit|ach credit)\b[\s:-]*)+", re.I)


def pretty(desc):
    """A readable line name from a bank description: 'TFR TO SAVINGS 40123456' becomes 'Transfer to savings'."""
    s = clean_desc(desc).replace("*", " ")
    s = LABEL_PREFIX.sub("", s).strip() or s
    s = re.sub(r"\b[\w-]*\d{4,}[\w-]*\b", " ", s)
    toks = []
    for w in s.split():
        if "@" in w or re.search(r"\w\.\w", w) or w.lower().startswith(("http", "www")):
            continue  # a web address the card network added
        w = w.split("_")[0]
        if toks and w.lower() == toks[-1].lower():
            continue
        toks.append(w)
    if len(toks) > 2 and re.fullmatch(r"[A-Z]{2}", toks[-1]) and toks[-1].lower() not in KEEP_UPPER:
        toks = toks[:-1]  # a two-letter place code at the end of a card line
    if len(toks) > 1 and len(toks[-1]) == 1:
        toks = toks[:-1]
    s = " ".join(toks)
    words = []
    for w in re.split(r"\s+", s.strip()):
        lw = w.lower().strip(".,")
        if not lw:
            continue
        lw = WORDS.get(lw, lw)
        if not lw:
            continue
        no_vowel = ((len(lw) <= 4 and lw.isalpha() and not re.search(r"[aeiouy]", lw))  # BT, CPF, an acronym
                    or (len(w.strip(".,")) == 2 and w.strip(".,").isupper() and w.strip(".,").isalpha()
                        and lw not in TWO_LETTER_WORDS)) \
            and lw not in ("ltd", "mr", "mrs", "ms", "dr", "st", "jr", "cld")
        if "-" in lw and any(x in KEEP_UPPER for x in lw.split("-")) and all(len(x) <= 4 for x in lw.split("-") if x):
            words.append(lw.upper())
            continue
        words.append(lw.upper() if (lw in KEEP_UPPER or no_vowel) else (lw if lw in SMALL and words else lw.capitalize()))
    out = " ".join(words[:5]).strip()
    if not out:
        return desc.strip()[:40]
    return (out[0].upper() + out[1:])[:40]


PAY_PROVIDER = re.compile(r"\b(gusto|adp|paychex|deel|rippling|justworks|trinet|wagepoint|employment hero|keypay|"
                          r"remote\.com|oyster|papaya)\b", re.I)


def category_of(desc):
    d = clean_desc(desc)
    if re.search(dict(RULES)["payroll"], d, re.I) or (PAY_PROVIDER.search(d) and re.search(r"\b(net|wages?|salar\w*|pay)\b", d, re.I)):
        return "payroll"  # before software: a payroll provider's net pay is pay, not a subscription
    desc = d
    if SOFTWARE.search(desc):
        return "software"
    for cat, pat in RULES:
        if re.search(pat, desc, re.I):
            return cat
    return "other regular"


def _ord(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def tax_like(desc):
    """Looks like a payment to a tax or government body, and is not money moved to the founder's own tax pot."""
    own = dict(RULES)["own transfer"]
    d = clean_desc(desc or "")
    return bool(TAX_LIKE.search(d)) and not re.search(own, d, re.I)


def cadence_of(dates):
    if len(dates) < 2:
        return None, None
    gaps = [(b - a).days for a, b in zip(dates, dates[1:])]
    g = statistics.median(gaps)
    for name, lo, hi, each in (("weekly", 5, 9, (4, 11)), ("fortnightly", 12, 16, (10, 18)),
                               ("monthly", 26, 35, (20, 40)), ("quarterly", 84, 98, (75, 105))):
        if lo <= g <= hi and all(each[0] <= x <= each[1] for x in gaps):
            return name, g
    return None, g


def day_key(d):
    return "end" if d == month_end(d.year, d.month) else d.day


def dom(d):
    """Day of the month, with the last day of any month read as 31."""
    return 31 if d == month_end(d.year, d.month) else d.day


def _circ(a, b):
    x = abs(a - b) % 31
    return min(x, 31 - x)


def twice_monthly(g):
    """A payee paid twice a month around two days (the 15th and the last day, or debits a day or two before them,
    common for payroll): two monthly groups, earlier day first, or None. Read from the founder's own payments; no
    country's pay rules are assumed."""
    if len(g) < 4:
        return None
    best = None
    for t0 in range(1, 32):
        a = [t for t in g if (dom(t["date"]) - t0) % 31 < 15]
        ida = {id(t) for t in a}
        b = [t for t in g if id(t) not in ida]
        if len(a) < 2 or len(b) < 2:
            continue
        a, b = sorted(a, key=lambda t: t["date"]), sorted(b, key=lambda t: t["date"])
        if cadence_of([t["date"] for t in a])[0] != "monthly" or cadence_of([t["date"] for t in b])[0] != "monthly":
            continue
        spread = max(max(_circ(dom(x["date"]), dom(y["date"])) for x in p for y in p) for p in (a, b))
        if spread > 7:
            continue
        if best is None or spread < best[0]:
            best = (spread, [a, b])
    if not best:
        return None
    return sorted(best[1], key=lambda p: statistics.median(dom(t["date"]) for t in p))


def half_name(p):
    """'month end' or 'around the 13th', from the days the payments left."""
    med = round(statistics.median(dom(t["date"]) for t in p))
    return "month end" if med >= 29 else f"around the {_ord(med)}"


def plausible(cad, n, days, amts, varies):
    """Two coffees a month apart are not a bill. Short cycles need most of their expected payments;
    long cycles and pairs need a steady amount."""
    expected = days / {"weekly": 7, "fortnightly": 14, "monthly": 30.4, "quarterly": 91}[cad]
    if cad in ("weekly", "fortnightly") and n < max(3, int(expected * 0.6)):
        return False
    if cad == "quarterly" and (max(amts) - min(amts)) > 0.02 * statistics.median(amts):
        return False
    if n == 2 and varies:
        return False
    return True


MONTHLY_FACTOR = {"weekly": 52 / 12, "fortnightly": 26 / 12, "monthly": 1.0, "quarterly": 1 / 3, "annual": 1 / 12}


def next_on_or_after(cad, dates, after):
    last = dates[-1]
    if cad == "monthly":
        day = round(statistics.median(d.day for d in dates))
        y, m = after.year, after.month
        for _ in range(3):
            try:
                cand = date(y, m, day)
            except ValueError:
                cand = month_end(y, m)
            if cand > after:
                return cand, day
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    step = {"weekly": 7, "fortnightly": 14, "four-weekly": 28, "quarterly": 91, "annual": 365}[cad]
    cand = last
    while cand <= after:
        cand += timedelta(days=step)
    return cand, None


def cluster(items):
    """Split one payee's payments into groups of similar amounts (within 15 per cent)."""
    groups = []
    for t in sorted(items, key=lambda t: abs(t["amount"])):
        for g in groups:
            med = statistics.median(abs(x["amount"]) for x in g)
            if abs(abs(t["amount"]) - med) <= max(0.15 * med, 1.0):
                g.append(t)
                break
        else:
            groups.append([t])
    return [sorted(g, key=lambda t: t["date"]) for g in groups]


def payee_groups(items):
    """The regular groups in one payee's payments: two monthly halves, or the whole payee on one rhythm (amounts may
    vary: a card bill, a cloud bill), or groups of similar amounts (rent and a service charge to one landlord)."""
    tm = twice_monthly(items)
    if tm:
        return [(tm[0], "early"), (tm[1], "late")]
    cad, _g = cadence_of(sorted(t["date"] for t in items))
    if cad and len(items) >= 3:
        return [(sorted(items, key=lambda t: t["date"]), "")]
    out = []
    for g in cluster(items):
        tm = twice_monthly(g)
        out += [(tm[0], "early"), (tm[1], "late")] if tm else [(g, "")]
    return out


def base_match(match):
    return re.sub(r" (early|late)$", "", str(match or "").lower().strip())


def saved_matches(saved, item):
    """Whether a saved memory row is this found line: the same match, or the same payee read by this version."""
    sm, im = str(saved.get("match") or "").lower().strip(), str(item.get("match") or "").lower().strip()
    if not sm:
        return False
    if sm == im:
        return True
    if base_match(sm) != base_match(im) and key_of(saved.get("label") or "") != base_match(im):
        sw, iw = base_match(sm).split(), base_match(im).split()
        if not (sw and iw and sw[0] == iw[0] and len(sw[0]) >= 4):
            return False
    sd, idy = str(saved.get("day") or "").strip(), item.get("day")
    if sd and idy and sd.isdigit() and str(idy).isdigit() and _circ(int(sd), int(idy)) > 7:
        return False
    return True


def apply_memory(items, mem):
    rows = [r for r in (mem or {}).get("regular_items", []) if r.get("match")]
    out = []
    for it in items:
        r = next((x for x in rows if str(x.get("match")).lower() == it["match"]), None) or next(
            (x for x in rows if saved_matches(x, it)), None)
        if r:
            it["_saved"] = True
            st = (r.get("status") or "keep").lower()
            if st in ("ignore", "ignored", "stopped", "one-off"):
                it["_ignored"] = st
            if r.get("label"):
                it["label"] = r["label"]
            if r.get("category"):
                it["category"] = r["category"]
            it["source"] += "; label and category from your saved list"
        out.append(it)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("transactions")
    ap.add_argument("--out", required=True)
    ap.add_argument("--memory-json")
    ap.add_argument("--today")
    ap.add_argument("--business")
    a = ap.parse_args()
    p = Path(a.transactions)
    if not p.exists():
        raise InputError(f"there is no file at {a.transactions}; run parse_bank_csv.py first")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        raise InputError(f"{a.transactions} is not the JSON file parse_bank_csv.py writes")
    if not isinstance(data, dict) or not isinstance(data.get("transactions"), list) or not data["transactions"]:
        raise InputError("the transactions file holds no transactions; run parse_bank_csv.py on the bank export first")
    mem = json.loads(Path(a.memory_json).read_text(encoding="utf-8")) if a.memory_json else {}
    today = date.fromisoformat(a.today) if a.today else date.today()
    saved = (mem or {}).get("profile", {})
    cur = data.get("currency") or saved.get("currency")
    set_style(month_first=(data.get("date_order") or saved.get("date_order")) == "month-first")
    _ns = data.get("number_style") or {}
    set_number_style(_ns.get("group"), _ns.get("decimal"))
    tx = []
    for t in data["transactions"]:
        tx.append({"date": from_iso(t["date"]), "amount": float(t["amount"]), "desc": t.get("description") or "",
                   "type": t.get("type") or ""})
    first, last = tx[0]["date"], tx[-1]["date"]
    days = max(1, (last - first).days + 1)
    weeks = days / 7
    opening = data.get("opening") or {}
    after = from_iso(opening["date"]) if opening.get("date") else last

    # payments that look like tax or another government payment: listed for the founder, never projected
    taxlike = []
    for t in tx:
        if t["amount"] < 0 and tax_like(t["desc"]):
            t["_tax"] = True
            taxlike.append(t)
    # group the rest by payee
    outs, ins = {}, {}
    for t in tx:
        if t.get("_tax"):
            continue
        (outs if t["amount"] < 0 else ins).setdefault(key_of(t["desc"]), []).append(t)

    regular_out, used = [], set()
    for k, items in outs.items():
        for g, half in payee_groups(items):
            dates = [t["date"] for t in g]
            cad, _gap = cadence_of(dates)
            if not cad:
                continue
            amts = [abs(t["amount"]) for t in g]
            spread = (max(amts) - min(amts)) / statistics.median(amts)
            varies = spread > 0.05
            amt = statistics.median(amts) if spread > 0.15 else abs(g[-1]["amount"])
            if not plausible(cad, len(g), days, amts, varies):
                continue
            nxt, day = next_on_or_after(cad, dates, after)
            stale = (last - dates[-1]).days > {"weekly": 14, "fortnightly": 24, "monthly": 45, "quarterly": 120}[cad]
            label = pretty(g[-1]["desc"])
            if half:
                label = f"{label} ({half_name(g)})"
            cur_ = data.get("currency") or saved.get("currency")
            vtxt = ("" if not varies else (f"; amount varies from {money(min(amts), cur_)} to {money(max(amts), cur_)}, "
                                           "the middle figure is used" if spread > 0.15 else "; amount varies a little, latest used"))
            regular_out.append({
                "label": label, "match": k + (f" {half}" if half else ""), "category": category_of(g[-1]["desc"]), "amount": round(amt, 2),
                "cadence": cad, "day": day, "next_date": iso(nxt), "keep": not stale, "_desc": g[-1]["desc"],
                "source": f"seen {len(g)} times, last {long_date(dates[-1])}" + vtxt
                          + ("; twice a month, placed on the day the money left your account" if half else "")
                          + ("; may have stopped" if stale else "")})
            used.update(id(t) for t in g)
    regular_out = apply_memory(regular_out, mem)
    cur_ = cur

    regular_in = []
    for k, items in ins.items():
        if PROCESSORS.search(items[0]["desc"]) or OWN_IN.search(items[0]["desc"]):
            continue
        for g in cluster(items):
            dates = [t["date"] for t in g]
            cad, _gap = cadence_of(dates)
            amts = [t["amount"] for t in g]
            if not cad or (max(amts) - min(amts)) > 0.10 * statistics.median(amts):
                continue
            nxt, day = next_on_or_after(cad, dates, after)
            if (last - dates[-1]).days > 45:
                continue
            client = pretty(g[-1]["desc"])
            regular_in.append({"label": client, "client": client, "match": k, "amount": round(g[-1]["amount"], 2),
                               "cadence": cad, "day": day, "next_date": iso(nxt), "category": "regular client",
                               "source": f"paid {len(g)} times, last {long_date(dates[-1])}"})
            used.update(id(t) for t in g)
    regular_in = apply_memory(regular_in, mem)

    # saved regular items this export did not find again (a short export, a bill that fell outside it): carried
    # forward from memory, unless the export is longer than the item's cycle and never shows it
    carried, not_placed = carry_forward(mem, regular_out + regular_in, tx, used, after, days, cur_)
    for c in carried:
        (regular_in if c["category"] == "regular client" else regular_out).append(c)

    # what is left: everyday spending, one-offs, own transfers, owner pay, other receipts
    rest_out = [t for t in tx if t["amount"] < 0 and id(t) not in used and not t.get("_tax")]
    own_out = [t for t in rest_out if category_of(t["desc"]) == "own transfer"]
    owner_irreg = [t for t in rest_out if category_of(t["desc"]) == "owner pay"]
    plain = [t for t in rest_out if t not in own_out and t not in owner_irreg]
    med = statistics.median([abs(t["amount"]) for t in plain]) if plain else 0
    big = max(500.0, 5 * med)
    one_offs = [t for t in plain if abs(t["amount"]) > big]
    # a payee that turns up three or more times among the one-offs is not a one-off: show it as repeating
    by_payee = {}
    for t in one_offs:
        by_payee.setdefault(key_of(t["desc"]), []).append(t)
    repeats = {k: g for k, g in by_payee.items() if len(g) >= 3}
    one_offs = [t for t in one_offs if key_of(t["desc"]) not in repeats]
    rep_ids = {id(t) for g in repeats.values() for t in g}
    everyday = [t for t in plain if t not in one_offs and id(t) not in rep_ids]
    rest_in = [t for t in tx if t["amount"] > 0 and id(t) not in used]
    own_in = [t for t in rest_in if OWN_IN.search(t["desc"])]
    pattern_in = [t for t in rest_in if t not in own_in]

    every_w = round(sum(-t["amount"] for t in everyday) / weeks, 2)
    owner_w = round(sum(-t["amount"] for t in owner_irreg) / weeks, 2) if owner_irreg else 0.0
    pattern_w = round(sum(t["amount"] for t in pattern_in) / weeks, 2)
    payers = {}
    for t in pattern_in:
        pk = key_of(t["desc"])
        x = payers.setdefault(pk, {"payer": pk, "label": pretty(t["desc"]), "amount": 0.0, "count": 0})
        x["amount"] = round(x["amount"] + t["amount"], 2)
        x["count"] += 1
    payer_list = sorted(payers.values(), key=lambda x: -x["amount"])
    top = payer_list[:4]
    biggest_share = (top[0]["amount"] / sum(x["amount"] for x in payer_list)) if payer_list else 0
    # clients whose invoices the founder listed before (saved habits): their receipts come in as invoices, so they
    # are left out of the usual pattern on a return run
    habit_clients = list(((mem or {}).get("profile") or {}).get("client_late_days") or {})
    # money in by calendar month (all receipts except own transfers), to see whether income is seasonal
    month_in = {}
    for t in tx:
        if t["amount"] > 0 and not OWN_IN.search(t["desc"]):
            ym = f"{t['date'].year}-{t['date'].month:02d}"
            month_in[ym] = round(month_in.get(ym, 0) + t["amount"], 2)
    full = [ym for ym in sorted(month_in) if not (ym == f"{first.year}-{first.month:02d}" and first.day > 3)
            and not (ym == f"{last.year}-{last.month:02d}" and last != month_end(last.year, last.month) and last.day < 28)]
    seasonal = False
    vals = [month_in[ym] for ym in full]
    for x0, x1 in zip(vals, vals[1:]):
        if max(x0, x1) > 0 and abs(x1 - x0) / max(min(x0, x1), 1) > 0.5:
            seasonal = True
    months_covered = month_span(first, last)

    # tax-like payments, grouped by payee, with the rhythm seen (for the founder to confirm, not to project)
    tax_groups = {}
    for t in taxlike:
        tax_groups.setdefault(key_of(t["desc"]), []).append(t)
    tax_seen = []
    for k, g in tax_groups.items():
        g = sorted(g, key=lambda t: t["date"])
        cad, gap = cadence_of([t["date"] for t in g])
        tm = twice_monthly(g)
        if tm:
            cad = "twice a month, " + " and ".join(half_name(p) for p in tm)
        amts = [-t["amount"] for t in g]
        tax_seen.append({"label": pretty(g[-1]["desc"]), "match": k, "times": len(g),
                         "last_amount": round(-g[-1]["amount"], 2), "last_date": iso(g[-1]["date"]),
                         "low": round(min(amts), 2), "high": round(max(amts), 2),
                         "rhythm_seen": cad or (f"about every {round(gap)} days" if gap else "once"),
                         "payments": [{"amount": round(-t["amount"], 2), "date": iso(t["date"])} for t in g]})
    tax_seen.sort(key=lambda x: -x["times"] * x["last_amount"])

    # short capital words on an ordinary line can be a tax or government payment with no telling words
    checks = []
    for r in regular_out:
        if r["category"] == "other regular" and r.get("keep", True):
            payee = LABEL_PREFIX.sub("", clean_desc(r.get("_desc") or r["label"])).strip()
            lead = re.split(r"[\s-]+", payee)[0] if payee else ""
            if (re.fullmatch(r"[A-Z]{2,4}", lead) and lead.lower() not in SHORT_OK) or re.search(
                    r"\b(city of|council|municipal|borough|county|ministry|department of|dept of)\b", payee, re.I):
                checks.append(r["label"])
                r["ask"] = "is this a tax, payroll tax or government payment?"

    ns = data.get("number_style") or {}
    draft = {
        "business": a.business or saved.get("business"), "currency": cur,
        "currency_source": data.get("currency_source") if data.get("currency") else ("saved memory" if cur else None),
        "date_order": data.get("date_order") or saved.get("date_order"),
        "country": saved.get("country"), "decimal_style": saved.get("decimal_style"),
        "number_style": {"group": ns.get("group"), "decimal": ns.get("decimal"), "source": "the export"},
        "today": iso(today),
        "opening": opening or {"balance": None, "date": iso(last), "source": "[NEED] the export has no balance column"},
        "export": {"bank": data.get("bank"), "files": data.get("files"), "first": iso(first), "last": iso(last),
                   "days": days, "map_string": data.get("map_string"), "header_signature": data.get("header_signature"),
                   "account_kind": data.get("account_kind")},
        "floor": saved.get("floor") or {"mode": "one_month", "value": None},
        "known_outgoings": [k for k in (saved.get("known_outgoings") or [])
                            if k.get("cadence") or str(k.get("date") or "") >= iso(today)],
        "recurring_out": [strip_private(r) for r in regular_out if not r.get("_ignored")],
        "everyday_spending_week": {"amount": every_w, "source": f"{len(everyday)} payment{'s' if len(everyday) != 1 else ''} over {days} days, "
                                   "leaving out regular bills, tax-like payments, transfers to your own accounts and one-offs"},
        "owner_pay_irregular_week": ({"amount": owner_w, "source": f"{len(owner_irreg)} irregular owner payments over {days} days"}
                                     if owner_irreg else None),
        "recurring_in": [strip_private(r) for r in regular_in if not r.get("_ignored")],
        "receipts_pattern_week": {"amount": pattern_w, "use": True, "weeks": round(weeks, 4),
                                  "months_covered": months_covered, "seasonal_check": seasonal,
                                  "months_off": [], "exclude": habit_clients,
                                  "payers": payer_list[:15],
                                  "source": f"{len(pattern_in)} receipt{'s' if len(pattern_in) != 1 else ''} over {days} days ({months_covered}) from everyone "
                                            "except your regular clients, leaving out transfers from your own accounts and loans"},
        "invoices": [], "payment_terms_days": saved.get("payment_terms_days"), "instalments": [], "one_offs": [],
        "client_late_days": saved.get("client_late_days") or {}, "commitment": None,
        "stress": saved.get("stress") or {"receipts_cut": "20%", "delay_days": 15, "plan_default": "10%"},
        "asked_about": [],
        "history_daily": {},
        "seen": {"one_offs": [{"label": pretty(t["desc"]), "amount": round(-t["amount"], 2), "date": iso(t["date"])} for t in one_offs],
                 "repeating": [{"label": pretty(g[-1]["desc"]), "times": len(g), "low": round(min(-t["amount"] for t in g), 2),
                                "high": round(max(-t["amount"] for t in g), 2), "last": iso(g[-1]["date"])} for g in repeats.values()],
                 "own_transfers_out": [{"label": pretty(t["desc"]), "amount": round(-t["amount"], 2), "date": iso(t["date"])} for t in own_out],
                 "own_transfers_in": [{"label": pretty(t["desc"]), "amount": round(t["amount"], 2), "date": iso(t["date"])} for t in own_in],
                 "tax_like": tax_seen,
                 "top_payers": [{"payer": x["label"], "amount": x["amount"]} for x in top],
                 "receipts_by_month": {ym: month_in[ym] for ym in sorted(month_in)},
                 "saved_not_placed": not_placed,
                 "ignored_from_memory": [r["label"] for r in regular_out + regular_in if r.get("_ignored")]},
        "sources": {},
    }
    for t in tx:
        dd = draft["history_daily"].setdefault(iso(t["date"]), [0.0, 0.0])
        if t["amount"] > 0 and t not in own_in:
            dd[0] = round(dd[0] + t["amount"], 2)
        elif t["amount"] < 0:
            dd[1] = round(dd[1] - t["amount"], 2)
    # own transfers out that repeat become a line of their own, so the forecast keeps paying them
    for r in draft["recurring_out"]:
        if r["category"] == "own transfer":
            r["source"] += "; money you move to your own account: kept in the forecast, left out of the floor"

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(draft, indent=2, default=str), encoding="utf-8")

    # what to show the founder
    print(f"FROM: {data.get('bank')} export, {long_date(first)} to {long_date(last)} ({days} days, {months_covered})")
    print(f"REGULAR OUT ({len(draft['recurring_out'])}):")
    for r in draft["recurring_out"]:
        print(f"  - {r['label']} | {r['category']} | {money(r['amount'], cur, pence=True)} {r['cadence']} | "
              f"next {r['next_date']} | {r['source']}" + ("" if r["keep"] else " | LEFT OUT unless the founder says it continues"))
    print(f"REGULAR IN ({len(draft['recurring_in'])}):")
    for r in draft["recurring_in"]:
        print(f"  - {r['label']} | {money(r['amount'], cur, pence=True)} {r['cadence']} | next {r['next_date']} | {r['source']}")
    if carried:
        print(f"CARRIED FROM YOUR SAVED LIST ({len(carried)}): " + "; ".join(
            f"{c['label']}{'' if c['keep'] else ' (may have stopped: ask)'}" for c in carried))
    for x in not_placed:
        print(f"SAVED, NOT PLACED: {x} (ask for its next date, or leave it out)")
    if cur:
        guess = "guess" in str(draft.get("currency_source") or "")
        print(f"CURRENCY: {cur} ({draft.get('currency_source')})" + (
            ". If the founder's own writing fits it (their $ or k figures, their city), state it as a default "
            "instead of asking" if guess else ""))
    else:
        print("CURRENCY: [NEED] not shown in the export or memory: take it from the founder's own writing "
              "(R250k, S$, 4.2k AUD) or ask once")
    print(f"DATE ORDER: {draft['date_order'] or 'not known yet (set it from a typed date that reads one way, the founder country, or ask)'}")
    if ns.get("group") or ns.get("decimal"):
        print(f"NUMBERS WRITTEN: thousands '{ns.get('group') or ','}', decimals '{ns.get('decimal') or '.'}' (from the export; "
              "the founder's own typing overrides it)")
    print("TAX-LIKE SEEN (not in the forecast until the founder lists what is due, how much and when):")
    if not tax_seen:
        print("  - none found by name; ask anyway: some tax and payroll payments carry no telling words")
    for g in tax_seen[:5]:
        span = (f"{money(g['low'], cur)} to {money(g['high'], cur)}" if g["low"] != g["high"] else money(g["last_amount"], cur, pence=True))
        print(f"  - {g['label']}: {g['times']} payment(s), {span}, {g['rhythm_seen']}, last on {long_date(g['last_date'])}")
    if len(tax_seen) > 5:
        print(f"  - and {len(tax_seen) - 5} more payee(s); see seen.tax_like in the draft")
    for lab in checks:
        print(f"CHECK: '{lab}' may be a tax, payroll tax or government payment (a short code in capitals, or a city or "
              "government body); ask the founder which it is")
    if draft["known_outgoings"]:
        print("KNOWN PAYMENTS FROM MEMORY (founder supplied; ask once whether any changed): " + "; ".join(
            f"{k.get('label')} {k.get('amount')} {k.get('cadence') or k.get('date')}" for k in draft["known_outgoings"]))
    passed = [k for k in (saved.get("known_outgoings") or []) if k not in draft["known_outgoings"]]
    if passed:
        print("PASSED SINCE LAST TIME (dropped): " + "; ".join(f"{k.get('label')} on {k.get('date')}" for k in passed))
    print(f"EVERYDAY SPENDING: {money(every_w, cur)} a week ({draft['everyday_spending_week']['source']})")
    if owner_irreg:
        print(f"OWNER PAY, IRREGULAR: {money(owner_w, cur)} a week on average")
    print(f"OTHER RECEIPTS PATTERN: {money(pattern_w, cur)} a week ({draft['receipts_pattern_week']['source']})")
    if top:
        print("  biggest payers in that pattern: " + "; ".join(f"{x['label']} {money(x['amount'], cur)}" for x in top)
              + (f". The largest is {round(biggest_share * 100)}% of it: if the founder lists that client's invoices, the "
                 "forecast takes the client out of the pattern" if biggest_share >= 0.4 else ""))
    for x in top:
        if not payer_list or x["amount"] < 0.2 * sum(y["amount"] for y in payer_list):
            continue
        allp = sorted((t for t in pattern_in if key_of(t["desc"]) == x["payer"]), key=lambda t: t["date"])
        last = allp[-3:]
        gaps = [(b["date"] - a["date"]).days for a, b in zip(allp, allp[1:])]
        print(f"  last receipts from {x['label']} (check them against anything the founder said this client owes): "
              + "; ".join(f"{long_date(t['date'])} {money(t['amount'], cur)}" + (f" ({ref_of(t['desc'])})" if ref_of(t["desc"]) else "")
                          for t in reversed(last))
              + (f". Days between their payments, oldest first: {', '.join(str(g) for g in gaps)}" if len(gaps) >= 2 else ""))
    deps = [t for t in rest_in if DEPOSIT.search(t["desc"]) and not NOT_DEPOSIT.search(t["desc"])
            and (tx[-1]["date"] - t["date"]).days <= 120]
    if deps:
        print("DEPOSITS SEEN (money already in for work still to deliver: ask whether a balance is still to come, and what "
              "that work costs to deliver and when): " + "; ".join(
                  f"{pretty(t['desc'])} {money(t['amount'], cur)} on {long_date(t['date'])}" for t in deps[-6:]))
    if habit_clients:
        print("  left out of the pattern (their invoices are listed, from your saved list; ask for the open ones): "
              + ", ".join(habit_clients))
    if seasonal:
        print("SEASONAL CHECK: money in moved by more than half from one month to the next ("
              + "; ".join(f"{date(int(ym[:4]), int(ym[5:]), 1).strftime('%B')} {money(month_in[ym], cur)}" for ym in full)
              + "). Ask, inside question 3: is your income "
              "seasonal, and which months are quiet? Quiet months go in receipts_pattern_week.months_off")
    if one_offs:
        print("ONE-OFFS LEFT OUT (ask if any will come again in the next 13 weeks): "
              + "; ".join(f"{pretty(t['desc'])} {money(-t['amount'], cur)} on {long_date(t['date'])}" for t in one_offs[:12])
              + (f"; and {len(one_offs) - 12} more" if len(one_offs) > 12 else ""))
    for g in repeats.values():
        print(f"REPEATING, NOT REGULAR ENOUGH TO PLACE: {pretty(g[-1]['desc'])}, {len(g)} payments of "
              f"{money(min(-t['amount'] for t in g), cur)} to {money(max(-t['amount'] for t in g), cur)}, last "
              f"{long_date(g[-1]['date'])}. Ask whether it continues, and its amount and day")
    if own_out:
        print("OWN TRANSFERS OUT: " + "; ".join(f"{pretty(t['desc'])} {money(-t['amount'], cur)} on {long_date(t['date'])}" for t in own_out[:4]))
    if own_in:
        print("LEFT OUT OF RECEIPTS (own transfers, loans, refunds): " + "; ".join(
            f"{pretty(t['desc'])} {money(t['amount'], cur)}" for t in own_in[:4]))
    if days < 56:
        print(f"NOTE: only {days} days of history; the patterns above rest on few payments")
    try:
        import forecast as fc
        mo, parts = fc.monthly_outgoings_from_raw(draft)
        print(f"FLOOR PREVIEW (one month of outgoings): {money(mo, cur)} = " + "; ".join(f"{k} {money(v, cur)}" for k, v in parts))
    except Exception:  # noqa: BLE001
        pass
    print(f"WROTE: {a.out}")


SHORT_OK = {"the", "and", "ltd", "pty", "llc", "inc", "co", "of", "for", "bank", "card", "fee", "pmt", "pos", "atm", "plc",
            "llp", "pte", "corp", "usa", "uk", "us", "nz", "sg", "au", "aws", "net", "sav", "chk", "wa", "ny", "ca", "tx", "fl",
            "bp", "dd", "so", "sto", "tfr", "vis", "acb", "eft", "ib", "web", "app", "one", "pay", "gym", "it", "hr", "tv"}
CYCLE_DAYS = {"weekly": 7, "fortnightly": 14, "four-weekly": 28, "monthly": 31, "quarterly": 92, "annual": 366}


def strip_private(r):
    return {k: v for k, v in r.items() if not k.startswith("_")}


def month_span(first, last):
    a, b = first.strftime("%B"), last.strftime("%B")
    if (first.year, first.month) == (last.year, last.month):
        return f"{a} {first.year}"
    return f"{a} {first.year} to {b} {last.year}" if first.year != last.year else f"{a} to {b} {last.year}"


def roll_forward(cad, nxt, after):
    """The saved next date moved on by its rhythm until it falls after the opening balance date."""
    from cashlib import add_months
    k, d = 0, nxt
    while d <= after and k < 400:
        k += 1
        if cad in ("monthly", "quarterly", "annual"):
            d = add_months(nxt, {"monthly": 1, "quarterly": 3, "annual": 12}[cad] * k)
        else:
            d = nxt + timedelta(days={"weekly": 7, "fortnightly": 14, "four-weekly": 28}[cad] * k)
    return d


def carry_forward(mem, found, tx, used, after, days, cur):
    """Saved 'keep' items the new export did not find as regular lines. Each is carried with its saved amount,
    rhythm and next date (moved on past the opening date), or the amount and day seen in this export when it
    appears once; its payments in the export are marked used so they are not counted again as everyday spending,
    one-offs or the receipts pattern. Left out (keep false, 'may have stopped') only when the export is longer than
    its cycle and never shows it."""
    from cashlib import parse_money
    out, not_placed = [], []
    for s in (mem or {}).get("regular_items", []):
        if (s.get("status") or "keep").lower() != "keep" or not s.get("match"):
            continue
        if any(saved_matches(s, f) for f in found):
            continue
        cad = str(s.get("cadence") or "monthly").lower()
        if cad not in CYCLE_DAYS:
            continue
        is_in = (s.get("category") or "").lower() == "regular client"
        base = base_match(s["match"])
        alt = key_of(s.get("label") or "")
        sday = str(s.get("day") or "").strip()
        seen = [t for t in tx if (t["amount"] > 0) == is_in and id(t) not in used and not t.get("_tax")
                and (key_of(t["desc"]) in (base, alt))
                and (not sday.isdigit() or _circ(dom(t["date"]), int(sday)) <= 7)]
        seen.sort(key=lambda t: t["date"])
        try:
            saved_amt = abs(parse_money(s.get("amount"))) if s.get("amount") not in (None, "") else None
        except Exception:  # noqa: BLE001
            saved_amt = None
        label = s.get("label") or base
        item = {"label": label, "match": str(s["match"]).lower(), "category": (s.get("category") or "other regular").lower(),
                "cadence": cad, "keep": True}
        if is_in:
            item["client"] = label
        if not seen and days > CYCLE_DAYS[cad] + 10:
            nd = s.get("next_date")
            item.update(amount=saved_amt, next_date=nd or None, day=None, keep=False,
                        source=f"from your saved list; not seen in this export of {days} days, which is longer than its "
                               "cycle: it may have stopped")
            if item["next_date"]:
                out.append(item)
            continue
        if seen:
            nxt, day = next_on_or_after(cad if cad in ("weekly", "fortnightly", "monthly", "quarterly") else "monthly",
                                        [t["date"] for t in seen], after) if cad != "annual" else (None, None)
            got = abs(seen[-1]["amount"])
            src = (f"from your saved list; seen in this export, {money(got, cur, pence=True)} on "
                   f"{long_date(seen[-1]['date'])}")
            if saved_amt and abs(got - saved_amt) > 0.15 * saved_amt:
                amount = saved_amt  # one payment of an amount that varies is not a new figure
                src += f"; your saved figure of {money(saved_amt, cur, pence=True)} is kept: ask if it has changed"
            else:
                amount = got
            used.update(id(t) for t in seen)
        else:
            nxt, day, amount = None, None, saved_amt
            src = "from your saved list, not seen in this export (it is shorter than the item's cycle)"
        if nxt is None and s.get("next_date"):
            try:
                nxt = roll_forward(cad, from_iso(s["next_date"]), after)
            except ValueError:
                nxt = None
        if nxt is None and sday.isdigit() and cad == "monthly":
            nxt, day = next_on_or_after("monthly", [date(after.year, after.month, min(int(sday), 28))], after)
        if nxt is None or amount is None:
            not_placed.append(label)
            continue
        item.update(amount=round(amount, 2), next_date=iso(nxt), day=day, source=src)
        out.append(item)
    return out, not_placed


if __name__ == "__main__":
    try:
        main()
    except InputError as e:
        print(f"STOP: {e}. Nothing was written.")
        sys.exit(2)
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print(f"STOP: the regular payments could not be worked out ({type(e).__name__}: {e}). Nothing was written.")
        sys.exit(2)
