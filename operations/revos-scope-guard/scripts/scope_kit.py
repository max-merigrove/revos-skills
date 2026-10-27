#!/usr/bin/env python3
"""Scope Guard: work out what scope creep has cost, price each extra, check the wording, build the kit.

Usage:
  python3 scripts/scope_kit.py template > kit.json
        a starter kit file with every field empty (fill it from what the founder gave you)
  python3 scripts/scope_kit.py compute <kit.json> [--today YYYY-MM-DD] [--json-out figures.json]
        read the founder's figures and print the rates, the creep ledger, a price and swap candidates
        for every open request, the client's dependency dates and every [NEED] line. No files written.
  python3 scripts/scope_kit.py build <kit.json> --out <folder> [--today YYYY-MM-DD] [--results <file>]
        check the wording you wrote into kit.json and, if it passes, write
        scope-kit-<client>-<date>.docx (the main file) and creep-ledger-<client>-<date>.xlsx.
        --results (default: next to kit.json) holds the figures for memory.py; it is not for the founder.
  python3 scripts/scope_kit.py blank-form <out.docx>
        a blank change request form

Exit codes: 0 done; 1 written with [NEED] flags (expected when the founder skipped a figure);
2 STOP: nothing usable was written. Read the STOP line, fix kit.json, run again.
Standard library only. No network calls. Every figure the founder sees comes from this script.
No country is assumed: currency, date order, the working day and any sales-tax wording come from the founder.
No tax is computed: prices are before any sales tax, with one neutral line pointing to the founder's accountant.
"""
import argparse
import json
import math
import unicodedata
import re
import sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_copy  # noqa: E402
import locale_numbers as L  # noqa: E402
import md_to_docx  # noqa: E402
import parse as P  # noqa: E402
import xlsx_writer  # noqa: E402

# ---- Working defaults (stated to the founder, changeable) -----------------------------------
DEFAULT_HOURS_PER_DAY = 8.0       # only used where the founder gave hours in days and did not say how long their day is
DEFAULT_REVISION_ROUNDS = 2
DEFAULT_ALLOWANCE_HOURS = 2
PRICE_STEP = 5                    # prices of 100 or more round to the nearest 5; under 100 to the nearest 1
SWAP_TOLERANCE = 0.25             # an equal-effort swap is within 25% of the request's hours (or 1 hour)
MAX_MESSAGE_WORDS = 80
MAX_RESET_WORDS = 140
MAX_WHY_WORDS = 30
MAX_NOTE_WORDS = 120

SYMBOLS = {"GBP": "£", "USD": "$", "EUR": "€", "AUD": "A$", "CAD": "C$", "NZD": "NZ$", "SGD": "S$", "HKD": "HK$",
           "INR": "₹", "$": "$"}
SALES_TAX_LINE = ("Prices are before any sales tax (VAT, GST or similar); ask your accountant whether you need to charge it")
LAWYER_LINE = ("Draft for your own use. Before any of this goes into a contract or agreement, have a lawyer read it. "
               "Nothing here is legal advice, and nothing here says how a court would read any of it.")
CLASSES = {"in": "In", "out": "Out", "grey": "Unclear", "unclear": "Unclear", "drift": "Out"}
STATUSES = {"done": "Done, not billed", "done, not billed": "Done, not billed", "absorbed": "Done, not billed",
            "done, in scope": "Done, not billed", "billed": "Done, billed", "done, billed": "Done, billed", "asked": "Asked", "open": "Asked",
            "pending": "Asked", "new": "Asked", "swapped": "Swapped", "swap": "Swapped", "declined": "Declined", "refused": "Declined", "dropped": "Declined"}
DIAGNOSES = {"creep": "Creep on a defined scope", "vague offer": "A vague offer: nothing written says what is in",
             "fulfilment drift": "Fulfilment drift: you are doing the client's part for them",
             "blank slate": "A new scope, written before the first extra arrives",
             "one request": "One request to price"}
OPTION_LABELS = {"price": "Price it", "swap": "Swap it", "later": "Next phase", "allowance": "Use the goodwill allowance",
                 "scope": "Scope it first"}
SCOPE_STEP = re.compile(r"\b(scop\w*|spec(ification)?|map (it|this|that) out|discovery|plan (it|this) out|work out exactly|"
                        r"firm (price|quote)|short plan|written plan)\b", re.I)
# Plausibility stops (Build Standard 13): a headline figure outside these bounds is put to the founder before anything is built.
MIN_RATE = 10                     # an hourly rate below 10 units of any currency is far likelier a misread than a price
MAX_HOURS_PER_DAY = 16
MAX_MONTH_HOURS = 744             # more hours than a month has
MAX_REQUEST_HOURS = 2000
OPEN_TOP = re.compile(r"(\b(maybe|or|possibly|probably|could be|might be|perhaps)\s+(more|longer|higher)\b|\bat least\b|\d\s*\+|\bplus\b(?!\s*(vat|gst|tax|mwst)))", re.I)
NOT_A_CAP = re.compile(r"\b(not a (cap|ceiling|limit|fixed price)|before (scoping|we scope|the plan)|could (go|run|come in|land|be) (higher|over|above|more)|"
                       r"(push|take) it (higher|up|over)|may be more|might be more|could be more|rough(ly)?|early estimate|estimate)\b", re.I)
VAGUE_QTY = re.compile(r"\b(ongoing|unlimited|as needed|as required|ad[- ]hoc|general support|and more|etc|whatever|any)\b", re.I)
SUBJECTIVE = re.compile(r"\b(happy|satisf(ied|action)|love[sd]? it|likes? it|perfect|until (they|the client) (are|is) happy|to the client'?s liking)\b", re.I)
NUMBER_WORDS = r"\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|thirty|single|a)\b"
STOP_WORDS = set("the a an and or for of to on in with our your their new extra one two more some this that from into page pages "
                 "piece pieces quick small little just also another few few".split())


RANGE_WORD = ["to"]               # the founder's word between two ends of a range ("bis"), kept on every rebuild
HOURS_LABEL = [""]                # the founder's word for hours ("Std."), kept on every rebuild


def founder_units(md):
    """Write hours and ranges in the founder's own words, when they asked for them, across the whole kit text."""
    if HOURS_LABEL[0]:
        md = re.sub(r"(?<=\d) hours?\b", " " + HOURS_LABEL[0], md)
    if RANGE_WORD[0] != "to":
        md = re.sub(r"(?<=[\d€£$¥]) to (?=(?:[$£€¥]|[A-Z]{1,3}\$)?\s?\d)", f" {RANGE_WORD[0]} ", md)
    return md


class Stop(Exception):
    pass


# ---------------------------------------------------------------- helpers
def r5(x):
    """Round a price the way the workbook does: nearest 5 at 100 or more, else nearest 1 (halves up)."""
    if x is None:
        return None
    step = PRICE_STEP if x >= 100 else 1
    return math.floor(x / step + 0.5) * step


def fmt_money(v, sym, decimals=False):
    """Money in the founder's own style: $9,800, 9.800 €, S$1,425; to the cent only when asked and not whole."""
    if v is None:
        return "[NEED]"
    num = P.fmt_number(v, 2) if (decimals and abs(v - round(v)) > 0.004) else P.fmt_number(math.floor(v + 0.5))
    sym = (sym or "").strip()
    if not sym:
        return num
    if P.STYLE["sign_after"]:
        return f"{num} {sym}"
    return f"{sym} {num}" if re.fullmatch(r"[A-Z]{3}", sym) else f"{sym}{num}"


def fmt_rate(v, sym):
    """An hourly rate: to the cent when it is not a whole number ($162.50), so a price built from it can be checked."""
    return fmt_money(v, sym, decimals=True)


def fmt_h(v):
    if v is None:
        return "[NEED]"
    return P.fmt_plain(v)


def price_text(p, sym, wording=""):
    """A price as the replies must state it: one figure, or both ends when the founder gave the hours as a range."""
    if p.get("price") is None:
        return "[NEED: price]"
    t = (f"{fmt_money(p['price_lo'], sym)} to {fmt_money(p['price_hi'], sym)}" if p.get("price_lo") is not None
         else fmt_money(p["price"], sym))
    return t + (f" {wording}" if wording else "")


def has_fig(fig, text):
    """Is this figure in the text, however the space beside the currency sign was typed?"""
    norm = lambda x: re.sub(r"[\u00a0\u202f ]", " ", x)  # noqa: E731
    return norm(fig) in norm(text) or norm(fig).replace(" ", "") in norm(text).replace(" ", "")


def hours_text(p):
    if p.get("hours_lo") is not None:
        return f"{fmt_h(p['hours_lo'])} to {fmt_h(p['hours_hi'])} hours"
    return f"{fmt_h(p['hours'])} {hours_word(p['hours'])}" if p.get("hours") is not None else "hours [NEED]"


def hours_word(v):
    return "hour" if v is not None and abs(v - 1) < 1e-9 else "hours"


def words(s):
    return len(re.findall(r"\b\w[\w'-]*\b", s or ""))


def sentences(s):
    """Sentences a client reads; a greeting, a sign-off or a two-word line ('Great idea.') does not count."""
    parts = re.split(r"(?<=[.?!])\s+|\n+", (s or "").strip())
    return len([x for x in parts if words(x) > 3])


def slug(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9]+", "-", (s or "client").lower()).strip("-")
    return s[:40] or "client"


def _stem(w):
    for suf in ("ings", "ing", "es", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            return w[: -len(suf)]
    return w


def key_words(s):
    return {_stem(w) for w in re.findall(r"[a-z][a-z'-]{3,}", (s or "").lower()) if w not in STOP_WORDS}


def msg_md(s):
    """A client message as one quoted block; the founder's line breaks (greeting, sign-off) are kept."""
    return "<br>".join(x.strip() for x in str(s).strip().splitlines() if x.strip())


def mdcell(s):
    return str(s if s is not None else "").replace("|", "\\|").replace("\n", " ").strip()


# ---------------------------------------------------------------- load and normalise
def load(path):
    p = Path(path)
    if not p.exists():
        raise Stop(f"there is no file at {path}")
    try:
        kit = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise Stop(f"{path} is not valid JSON (line {e.lineno}: {e.msg}); fix the file and run again")
    if not isinstance(kit, dict):
        raise Stop("the kit file must be one JSON object with fields like client, fee and requests, not a list")
    for k, kind in (("requests", list), ("responses", list), ("scope", dict)):
        if k in kit and kit[k] is not None and not isinstance(kit[k], kind):
            raise Stop(f"'{k}' must be a {'list' if kind is list else 'set of fields'}; see `scope_kit.py template`")
    sc = kit.get("scope") or {}
    for k in ("deliverables", "dependencies", "included", "not_included", "assumptions"):
        if k in sc and sc[k] is not None and not isinstance(sc[k], list):
            raise Stop(f"scope.{k} must be a list")
    for i, r in enumerate(kit.get("requests") or [], 1):
        if not isinstance(r, dict) or not str(r.get("what", "")).strip():
            raise Stop(f"request {i} needs at least a 'what' (what the client asked for)")
    return kit


COUNTRY_WORDS = {"usa": "US", "united states": "US", "america": "US", "uk": "GB", "united kingdom": "GB", "britain": "GB",
                 "england": "GB", "scotland": "GB", "wales": "GB", "germany": "DE", "deutschland": "DE", "france": "FR",
                 "singapore": "SG", "australia": "AU", "canada": "CA", "india": "IN", "ireland": "IE", "netherlands": "NL",
                 "spain": "ES", "italy": "IT", "new zealand": "NZ", "philippines": "PH", "malaysia": "MY", "japan": "JP",
                 "mexico": "MX", "south africa": "ZA", "uae": "AE", "switzerland": "CH", "austria": "AT", "sweden": "SE"}


def country_code(v):
    t = str(v or "").strip()
    if re.fullmatch(r"[A-Za-z]{2}", t):
        return t.upper()
    return COUNTRY_WORDS.get(t.lower(), "")


def figure_samples(kit):
    """Every figure the founder typed (never dates, never Claude's own '=' sums): the evidence for their decimal style."""
    sc = kit.get("scope") or {}
    out = [kit.get(k) for k in ("fee", "planned_hours", "actual_hours", "rate_for_changes", "allowance_hours", "hours_per_day")]
    out += [r.get("hours") for r in (kit.get("requests") or []) if isinstance(r, dict)]
    out += [d.get("hours") for d in (sc.get("deliverables") or []) if isinstance(d, dict)]
    return [x for x in out if isinstance(x, str)]


def normalise(kit, today):
    m = {"needs": [], "notes": [], "assumed": [], "asks": [], "checks": []}
    need, note, assumed, ask = m["needs"].append, m["notes"].append, m["assumed"].append, m["asks"].append
    m["client"] = str(kit.get("client") or "").strip() or "This client"
    m["offer"] = str(kit.get("offer") or "").strip()
    m["business"] = str(kit.get("business") or "").strip()
    m["founder"] = str(kit.get("founder") or "").strip()
    m["today"] = today
    m["confirmed"] = {str(x).strip().lower() for x in (kit.get("confirmed") or [])}
    # the founder's country sets paper, and date order when their dates do not show it; never their spelling
    m["country"] = country_code(kit.get("country"))
    loc = L.locale_defaults(m["country"])
    # how the founder writes numbers: read once from every figure they typed, then used by every reader
    style = P.set_style(figure_samples(kit), said=kit.get("number_style"))
    m["number_style"] = P.style_sample() if style["decimal"] else ""
    if style["decimal"] == "comma":
        assumed(f"Figures read with a comma for decimals and written back that way ({P.style_sample().split(' (')[0]}), as you write them")
    # how the founder writes dates: said, read from a date that can only be one way round, or their country's order
    texts = [kit.get("period_start")] + [r.get("date") for r in (kit.get("requests") or []) if isinstance(r, dict)]
    for d in ((kit.get("scope") or {}).get("dependencies") or []):
        if isinstance(d, dict):
            texts += [d.get("due"), d.get("received")]
    m["date_order"] = P.set_order(kit.get("date_order")) or P.set_order(P.infer_order(texts))
    if not kit.get("date_order") and m["date_order"]:
        assumed(f"Dates read {'month first' if m['date_order'] == 'mdy' else 'day first'}, the way you wrote them")
    elif not m["date_order"] and m["country"]:
        m["date_order"] = P.set_order("mdy" if loc["date_order"] in ("MDY", "YMD") else "dmy")
        assumed(f"Dates such as 3/9 read {'month first' if m['date_order'] == 'mdy' else 'day first'}, as they are written where you are")
    eng = str(kit.get("english") or "").lower()
    RANGE_WORD[0] = str(kit.get("range_word") or "").strip() or "to"
    HOURS_LABEL[0] = str(kit.get("hours_label") or "").strip()
    m["english"] = "american" if eng.startswith(("am", "us", "en-us")) else "british" if eng.startswith(("br", "uk", "en-gb")) else "neutral"
    # currency: the founder's own sign or code; never a default country
    ccode, csign = P.currency_of(kit.get("fee", ""))
    given = str(kit.get("currency") or "").strip()
    if given:
        gcode, gsign = P.currency_of(given)
        cur = gcode or given.upper()
        csign = csign if (ccode in (None, "$", cur)) and csign else (gsign or SYMBOLS.get(cur, ""))
    else:
        cur = ccode
    m["currency"] = cur or ""
    m["sym"] = csign or (SYMBOLS.get(cur, cur) if cur else "")
    if not cur:
        need("the currency you bill this client in (a sign or code, such as $, £, €, S$ or AUD); prices show without one until then")
    # paper: the founder's country; failing that, dollars billed in North America or month-first dates; else A4, said
    if m["country"]:
        m["paper"] = loc["paper"].lower()
    elif m["date_order"] == "mdy" or m["currency"] in ("USD", "CAD", "MXN"):
        m["paper"] = "letter"
        assumed("Letter paper, from your month-first dates or your currency; say if you print on A4")
    else:
        m["paper"] = "a4"
        assumed("A4 paper, because your country was not given; say if you print on Letter")
    m["lang"] = {"american": "en-US", "british": "en-GB"}.get(m["english"]) or {"US": "en-US", "GB": "en-GB"}.get(m["country"], "en")
    # sales tax: never computed. If the founder writes their fee with tax words, keep their wording for the replies.
    pw = str(kit.get("price_wording") or "").strip()
    how, word = P.tax_wording(kit.get("fee", ""))
    if how == "including":
        need("the fee before any sales tax: you wrote it including tax, and every rate here works on prices before tax. "
             "Your accountant or your invoices give the figure")
    if not pw and how == "plus":
        pw = f"plus {word}"
    elif not pw and how == "net":
        pw = word
    m["price_wording"] = pw
    billing = str(kit.get("billing") or "").lower()
    if not billing:
        billing = "monthly" if P.period_of(str(kit.get("fee", ""))) in ("month", "week", "year") else "project"
        assumed(f"Billing read as {billing} from how the fee was written")
    m["billing"] = "monthly" if billing.startswith(("month", "retainer", "recurring", "subscription")) else "project"
    mon = m["billing"] == "monthly"

    def read(kind, value, label, hpd=None):
        v, n = (P.money(value) if kind == "money" else P.hours(value, hpd))
        if n.startswith("ASK:"):
            ask(f"{label}: {n[4:].strip()}")
            return None, ""
        return v, n

    hpd_given = read("hours", kit.get("hours_per_day"), "hours in your working day", DEFAULT_HOURS_PER_DAY)[0]
    m["hpd"] = hpd_given or DEFAULT_HOURS_PER_DAY
    m["hpd_src"] = "founder said" if hpd_given else "default"

    fee, fnote = read("money", kit.get("fee"), "the fee")
    if how == "including":
        fee = None
    if fee is not None and mon:
        fee, n2 = P.per_month(fee, kit.get("fee", ""), "month")
        fnote = fnote or n2
    m["fee"] = fee if fee else None
    if not m["fee"] and how != "including":
        need("what the client pays " + ("a month" if mon else "for the project") + ": without it there is no rate to price extras at")
    elif fnote:
        note(f"Fee: {fnote}")
    ph, pnote = read("hours", kit.get("planned_hours"), "the planned hours", m["hpd"])
    if ph is not None and mon:
        ph, n2 = P.per_month(ph, kit.get("planned_hours", ""), "month")
        pnote = pnote or n2
    m["planned"] = ph if ph else None
    if not m["planned"]:
        need("the hours you planned " + ("a month" if mon else "for the project") + " when you priced it")
    elif pnote:
        note(f"Planned hours: {pnote}")
    ah, anote = read("hours", kit.get("actual_hours"), "the hours you actually work", m["hpd"])
    if ah is not None and mon:
        ah, n2 = P.per_month(ah, kit.get("actual_hours", ""), "month")
    m["actual"] = ah if ah else None

    ag_text = re.sub(r"^\s*(up to|max(imum)?|no more than|capped at|at most)\s+", "", str(kit.get("agreed_hours") or ""), flags=re.I)
    agh, _an = read("hours", ag_text, "the hours in the signed agreement", m["hpd"])
    if agh is not None and mon:
        agh, _n2 = P.per_month(agh, ag_text, "month")
    m["agreed"] = agh if agh else None
    m["agreed_differs"] = bool(m["agreed"] and m["planned"] and abs(m["agreed"] - m["planned"]) > 0.05)
    lg, _ln = read("hours", kit.get("hours_logged_this_month"), "the hours logged so far this month", m["hpd"])
    m["logged"] = lg if (lg is not None and mon) else None
    m["rate_priced"] = (m["fee"] / m["planned"]) if (m["fee"] and m["planned"]) else None
    m["rate_agreed"] = (m["fee"] / m["agreed"]) if (m["fee"] and m["agreed_differs"]) else None
    rc, rnote = read("money", kit.get("rate_for_changes"), "your rate for extra work", m["hpd"])
    if rc:
        m["rate_changes"], m["rate_changes_src"] = rc, "your own rate for extra work"
    elif m["rate_priced"]:
        m["rate_changes"], m["rate_changes_src"] = m["rate_priced"], "the rate you priced the work at: fee divided by planned hours"
        assumed(f"Extras priced at {fmt_rate(m['rate_priced'], m['sym'])} an hour, the rate the fee works out at, unless you name another rate")
    else:
        m["rate_changes"], m["rate_changes_src"] = None, "not known"

    # plausibility stops: a headline figure a misread would produce is put to the founder, never built on
    sym = m["sym"]

    def check(key, text):
        if key not in m["confirmed"]:
            m["checks"].append((key, text))
    if m["rate_priced"] is not None and m["rate_priced"] < MIN_RATE:
        check("rate", f"the fee reads as {fmt_money(m['fee'], sym)} for {fmt_h(m['planned'])} planned hours, which is "
                      f"{fmt_rate(m['rate_priced'], sym)} an hour. Is the fee {fmt_money(m['fee'], sym)} and are the hours {fmt_h(m['planned'])}?")
    if m["rate_changes_src"].startswith("your own") and m["rate_changes"] < MIN_RATE:
        check("rate_for_changes", f"your rate for extra work reads as {fmt_rate(m['rate_changes'], sym)} an hour. Is that right?")
    if hpd_given and not (1 <= hpd_given <= MAX_HOURS_PER_DAY):
        check("hours_per_day", f"your working day reads as {fmt_h(hpd_given)} hours. How many hours is it?")
    if mon and m["planned"] and m["planned"] > MAX_MONTH_HOURS:
        check("planned_hours", f"the planned hours read as {fmt_h(m['planned'])} a month, more than a month has. How many is it?")

    pol = str(kit.get("extras_policy") or "").lower()
    # an allowance is a promise to the client, so it is only ever the founder's choice, never a default
    m["policy"] = "allowance" if pol.startswith(("allow", "goodwill")) else "swap" if pol.startswith("swap") else "price"
    if not pol:
        assumed("Every extra priced; no goodwill allowance, because you have not chosen one. Say if you want a small one")
    al, _n = read("hours", kit.get("allowance_hours"), "the goodwill allowance", m["hpd"])
    m["allowance"] = (al if al is not None else DEFAULT_ALLOWANCE_HOURS) if m["policy"] == "allowance" else 0
    if m["policy"] == "allowance" and kit.get("allowance_hours") in (None, ""):
        assumed(f"Goodwill allowance of {DEFAULT_ALLOWANCE_HOURS} hours {'a month' if mon else 'on the project'} (the default)")
    rel = str(kit.get("relationship") or "").lower()
    m["relationship"] = "fragile" if rel.startswith("frag") else "renewing" if rel.startswith(("renew", "about")) else "strong"
    if not rel:
        assumed("Relationship read as strong, so the replies are direct")

    rr = kit.get("revision_rounds")
    rv = None
    if rr not in (None, ""):
        mm = re.search(r"\d+", str(rr)) or re.search(NUMBER_WORDS, str(rr).lower())
        if mm:
            g = mm.group(0)
            rv = int(g) if g.isdigit() else {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "a": 1, "single": 1}.get(g, None)
    if rv is None:
        rv = DEFAULT_REVISION_ROUNDS
        assumed(f"{DEFAULT_REVISION_ROUNDS} rounds of changes per deliverable (the default)")
    m["revisions"] = rv

    # requests
    reqs = []
    for i, r in enumerate(kit.get("requests") or [], 1):
        x = {"id": int(r.get("id") or i), "what": str(r.get("what")).strip(), "kind": str(r.get("kind") or "extra").lower()}
        cl = str(r.get("class") or "").lower().strip()
        if cl not in CLASSES:
            raise Stop(f"request {x['id']} ('{x['what']}'): class must be in, out or unclear, not '{r.get('class')}'")
        x["class"] = CLASSES[cl]
        if cl == "drift":
            x["kind"] = "drift"
        res = str(r.get("resolved_as") or "").lower()
        if x["class"] == "Unclear" and res in ("in", "out"):
            x["class"], x["resolved"] = CLASSES[res], True
        st = str(r.get("status") or "").lower().strip()
        if st not in STATUSES:
            raise Stop(f"request {x['id']} ('{x['what']}'): status must be done, billed, swapped, asked or declined, not '{r.get('status')}'")
        x["status"] = STATUSES[st]
        h, hn = read("hours", r.get("hours"), f"the hours for request {x['id']} ('{x['what']}')", m["hpd"])
        x["hours"], x["hours_note"] = h, hn
        rg = P.hours_range(r.get("hours"), m["hpd"]) if h is not None else None
        x["hours_lo"], x["hours_hi"] = rg if rg else (None, None)
        x["open_top"] = bool(h is not None and OPEN_TOP.search(str(r.get("hours") or "") + " " + str(r.get("hours_note") or "")))
        if h is not None and h > MAX_REQUEST_HOURS:
            check(f"request {x['id']}", f"request {x['id']} ('{x['what']}') reads as {fmt_h(h)} hours. Is that right?")
        per = str(r.get("per") or "").lower()
        x["per"] = " a month" if (per.startswith("month") or P.period_of(str(r.get("hours") or "")) == "month") else ""
        if h is None and not hn.startswith("ASK"):
            need(f"rough hours for request {x['id']} ('{x['what']}'); it is left out of the totals until then")
        elif hn:
            note(f"Request {x['id']} hours: {hn}")
        d, dn = P.date_(r.get("date"), today, "past")
        x["date"], x["date_text"] = d, str(r.get("date") or "")
        x["month_only"] = dn == P.MONTH_ONLY
        if r.get("date") and d is None:
            (need if "which way round" in dn else note)(f"Request {x['id']} date: {dn}")
        reqs.append(x)
    ids = [x["id"] for x in reqs]
    if len(ids) != len(set(ids)):
        raise Stop("two requests share an id; give each request its own number")
    m["requests"] = reqs

    # period for a monthly fee
    if mon:
        ps, pn = P.date_(kit.get("period_start"), today, "past")
        if ps is None:
            dated = [x["date"] for x in reqs if x["date"]]
            if dated:
                first = min(dated)
                ps = date(first.year, first.month, 1)
                assumed(f"The count starts on {P.long_date(ps)}, the start of the month of the first request, because no start date was given")
        if ps and ps > today:
            raise Stop(f"the start of the count ({P.long_date(ps)}) is after today; give a date in the past")
        m["period_start"] = ps
        m["months"] = round(max((today - ps).days, 1) / (365.25 / 12), 1) if ps else None
        if m["months"] is not None and m["months"] < 0.5:
            m["months"] = 0.5
            note("Less than half a month since the start: counted as half a month")
    else:
        m["period_start"], m["months"] = None, 1

    # scope
    sc = kit.get("scope") or {}
    dl = []
    for d in sc.get("deliverables") or []:
        if isinstance(d, str):
            d = {"name": d}
        hh, _ = read("hours", d.get("hours"), f"the hours for '{d.get('name')}'", m["hpd"])
        dl.append({"name": str(d.get("name") or "").strip(), "quantity": str(d.get("quantity") or "").strip(),
                   "who": str(d.get("who") or "").strip(), "acceptance": str(d.get("acceptance") or "").strip(), "hours": hh})
    m["deliverables"] = dl
    deps = []
    for d in sc.get("dependencies") or []:
        if isinstance(d, str):
            d = {"what": d}
        due_t = str(d.get("due") or "").strip()
        rec = P.recurring_day(due_t)
        due, _dn = (None, "") if rec else P.date_(due_t, today, "nearest")
        rtxt = str(d.get("received") or "").strip().lower()
        missing = rtxt in ("not yet", "no", "none", "none yet", "missing", "not received", "still missing", "not arrived", "outstanding")
        got, _gn = (None, "") if missing else P.date_(d.get("received"), today, "past")
        deps.append({"what": str(d.get("what") or "").strip(), "owner": str(d.get("owner") or m["client"]).strip(),
                     "due_text": due_t, "due": due, "recurring": rec, "received": got,
                     "received_text": str(d.get("received") or "").strip(), "missing": missing, "effect": str(d.get("effect") or "").strip()})
    m["dependencies"] = deps
    for k in ("outcome", "changes"):
        m[k] = str(sc.get(k) or "").strip()
    for k in ("included", "not_included", "assumptions"):
        m[k] = [str(x).strip() for x in (sc.get(k) or []) if str(x).strip()]
    m["diagnosis"] = kit.get("diagnosis") or {}
    m["responses"] = kit.get("responses") or []
    m["reset_message"] = str(kit.get("reset_message") or "").strip()
    m["allowance_line"] = str(kit.get("allowance_line") or "").strip()
    m["note"] = str(kit.get("note") or "").strip()
    m["reset_already_sent"] = bool(kit.get("reset_already_sent"))
    # what the founder owes the client and let slip: the reset note owns it in one clause
    m["founder_owes"] = [str(x).strip() for x in (kit.get("founder_owes") or []) if str(x).strip()]
    prev = kit.get("previous") or {}
    pd, _ = P.date_(prev.get("date"), today, "past") if prev.get("date") else (None, "")
    pr, _ = P.money(prev.get("effective_rate")) if prev.get("effective_rate") else (None, "")
    m["previous"] = {"date": pd, "rate": pr} if (pd and pr) else None
    m["sources"] = kit.get("sources") or {}
    if m["hpd_src"] == "default" and any("hours a day" in n for n in m["notes"]):
        assumed(f"A working day counts as {fmt_h(m['hpd'])} hours where you gave hours in days. "
                "If your day is longer or shorter, say so and every figure that used it changes")
    return m


# ---------------------------------------------------------------- compute
def compute(m):
    mon = m["billing"] == "monthly"
    sym = m["sym"]
    rp, rc = m["rate_priced"], m["rate_changes"]
    out_req = [r for r in m["requests"] if r["class"] == "Out"]
    absorbed = [r for r in out_req if r["status"] == "Done, not billed" and r["hours"] is not None]
    pending = [r for r in out_req if r["status"] == "Asked"]
    unclear = [r for r in m["requests"] if r["class"] == "Unclear"]
    absorbed_h = sum(r["hours"] for r in absorbed)
    res = {"absorbed_hours": absorbed_h, "absorbed_count": len(absorbed),
           "out_count": len(out_req), "out_hours_known": sum(r["hours"] or 0 for r in out_req),
           "pending_ids": [r["id"] for r in pending], "unclear_ids": [r["id"] for r in unclear]}
    months = m["months"] or 0
    res["fee_period"] = (m["fee"] * months) if (m["fee"] and months) else None
    res["planned_period"] = (m["planned"] * months) if (m["planned"] and months) else None
    if res["fee_period"] and res["planned_period"]:
        res["effective_rate"] = res["fee_period"] / (res["planned_period"] + absorbed_h)
        res["rate_drop"] = 1 - res["effective_rate"] / rp
    else:
        res["effective_rate"] = res["rate_drop"] = None
    res["creep_value"] = absorbed_h * rp if rp is not None else None
    # actual hours, when the founder gave them
    res["actual_rate"] = res["over_plan_period"] = res["unexplained_hours"] = None
    if m["actual"] and m["fee"]:
        res["actual_rate"] = m["fee"] / m["actual"]
        if m["planned"]:
            over = (m["actual"] - m["planned"]) * months
            res["over_plan_period"] = over
            res["unexplained_hours"] = max(over - absorbed_h, 0) if over > 0 else 0
    # allowance
    al = m["allowance"]
    if al and rp is not None:
        res["allowance_year_hours"] = al * (12 if mon else 1)
        res["allowance_year_value"] = res["allowance_year_hours"] * rp
        res["rate_with_allowance"] = m["fee"] / (m["planned"] + al) if (m["fee"] and m["planned"]) else None
        cover = min(absorbed_h, al * (months if mon else 1))
        res["allowance_past_covered"] = cover
        res["allowance_past_rest"] = absorbed_h - cover
        res["allowance_past_rest_value"] = (absorbed_h - cover) * rp
    else:
        for k in ("allowance_year_hours", "allowance_year_value", "rate_with_allowance", "allowance_past_covered",
                  "allowance_past_rest", "allowance_past_rest_value"):
            res[k] = None
    # pending requests: price (before any sales tax), swap candidates, later
    pend = []
    for r in pending:
        p = {"id": r["id"], "what": r["what"], "hours": r["hours"], "per": r["per"], "hours_lo": r["hours_lo"], "hours_hi": r["hours_hi"],
             "open_top": r.get("open_top", False)}
        p["price"] = r5(r["hours"] * rc) if (r["hours"] is not None and rc) else None
        p["price_lo"] = r5(r["hours_lo"] * rc) if (r["hours_lo"] is not None and rc) else None
        p["price_hi"] = r5(r["hours_hi"] * rc) if (r["hours_hi"] is not None and rc) else None
        top = r["hours_hi"] if r["hours_hi"] is not None else r["hours"]
        # a build as big as the month's plan (or half a project) is scoped before it is priced as one figure
        p["scope_first"] = bool(top is not None and m["planned"] and top >= (m["planned"] if mon else m["planned"] / 2))
        p["fits_allowance"] = bool(al and r["hours"] is not None and r["hours"] <= al)
        cands, nearest = [], None
        if r["hours"] is not None:
            tol = max(SWAP_TOLERANCE * r["hours"], 1.0)
            for d in m["deliverables"]:
                if d["hours"] is None:
                    continue
                gap = abs(d["hours"] - r["hours"])
                if gap <= tol:
                    cands.append({"name": d["name"], "hours": d["hours"]})
                if nearest is None or gap < abs(nearest["hours"] - r["hours"]):
                    nearest = {"name": d["name"], "hours": d["hours"]}
        p["swap_candidates"], p["swap_nearest"] = cands, nearest
        if mon:
            nxt = date(m["today"].year + (m["today"].month == 12), m["today"].month % 12 + 1, 1)
            p["later_when"] = f"from {P.long_date(nxt)}, in next month's plan"
        else:
            p["later_when"] = "as a second phase after this project is signed off"
        p["suggested"] = suggest(m, p)
        pend.append(p)
    res["pending"] = pend
    res["pending_hours"] = sum(p["hours"] or 0 for p in pend)
    # capacity: what is left of this month's planned hours, and which open requests would fit in it
    res["hours_left"] = None
    if m.get("logged") is not None and m["planned"]:
        res["hours_left"] = max(m["planned"] - m["logged"], 0)
        for p in pend:
            top = p["hours_hi"] if p["hours_hi"] is not None else p["hours"]
            p["fits_month"] = None if top is None else top <= res["hours_left"]
    known_prices = [p["price"] for p in pend if p["price"] is not None]
    res["pending_value"] = sum(known_prices) if known_prices else None
    # open requests as a range when any was given as one: both ends, never a total of rounded middles
    res["pending_range"] = None
    if any(p["hours_lo"] is not None for p in pend) and rc:
        known = [p for p in pend if p["hours"] is not None]
        lo_h = sum(p["hours_lo"] if p["hours_lo"] is not None else p["hours"] for p in known)
        hi_h = sum(p["hours_hi"] if p["hours_hi"] is not None else p["hours"] for p in known)
        res["pending_range"] = {"hours_lo": lo_h, "hours_hi": hi_h, "value_lo": r5(lo_h * rc), "value_hi": r5(hi_h * rc),
                                "open_top": any(p["open_top"] for p in known)}
    # dependencies
    deps = []
    for d in m["dependencies"]:
        x = dict(d)
        if d["recurring"]:
            kind, n = d["recurring"]
            x["due_label"] = f"the {n}{_th(n)} of each month" if kind == "month" else f"every {P.WEEKDAYS[n].title()}"
            x["status"] = "recurring"
            if kind == "month" and d["received"] is not None:
                try:
                    due_then = date(d["received"].year, d["received"].month, n)
                    late = (d["received"] - due_then).days
                except ValueError:
                    late = 0
                x["days_late"] = max(late, 0)
                x["status"] = (f"last received {P.short_date(d['received'])}, {late} days late" if late > 0
                               else f"last received {P.short_date(d['received'])}, on time")
            elif kind == "month" and d["missing"] and m["today"].day > n:
                x["status"] = f"due on the {n}{_th(n)}; not yet received this month, {m['today'].day - n} days late"
                x["days_late"] = m["today"].day - n
        elif d["due"]:
            x["due_label"] = P.long_date(d["due"])
            if d["received"]:
                late = (d["received"] - d["due"]).days
                x["days_late"] = max(late, 0)
                x["status"] = f"received {P.short_date(d['received'])}, {late} days late" if late > 0 else f"received {P.short_date(d['received'])}"
            elif d["due"] < m["today"] and d["missing"]:
                x["days_late"] = (m["today"] - d["due"]).days
                x["status"] = f"not yet received, {x['days_late']} days late"
            elif d["due"] < m["today"]:
                x["status"] = "date passed; mark it received, or 'not yet'"
                m["needs"].append(f"whether the client has sent '{d['what']}' (due {P.long_date(d['due'])})")
            else:
                x["status"] = f"due in {(d['due'] - m['today']).days} days"
        else:
            x["due_label"] = "[NEED: a date]"
            x["status"] = ""
            m["needs"].append(f"a date for the client's part: '{d['what']}'")
        if x.get("due") and not d["recurring"] and x["due"].weekday() >= 5 and not d["received"]:
            fri = x["due"] - timedelta(days=x["due"].weekday() - 4)
            x["weekend"] = (f"{d['what']} is due on {P.WEEKDAYS[x['due'].weekday()].title()} {P.long_date(x['due'])}, a weekend. "
                            f"If neither side works weekends, the Friday before, {P.long_date(fri)}, is the date that holds")
        deps.append(x)
    res["dependencies"] = deps
    res["weekend_dates"] = [x["weekend"] for x in deps if x.get("weekend")]
    res["late_days_total"] = sum(d.get("days_late") or 0 for d in deps)
    return res


def _th(n):
    return "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


def suggest(m, p):
    """The default recommendation (references/method.md section 5). Saved learnings may change it."""
    if m["policy"] == "swap":
        return "swap" if p["swap_candidates"] else "later"
    if p["scope_first"]:
        return "scope"
    if p["fits_allowance"] and m["policy"] == "allowance":
        return "allowance"
    if m["relationship"] == "renewing":
        return "later"
    if m["relationship"] == "fragile" and p["swap_candidates"]:
        return "swap"
    return "price"


# ---------------------------------------------------------------- headline (deterministic wording)
def headline(m, res):
    """Paragraphs for 'At a glance'. The first is the one-line verdict, in bold."""
    sym, mon = m["sym"], m["billing"] == "monthly"
    rp, ab_n, ab_h, n_out = m["rate_priced"], res["absorbed_count"], res["absorbed_hours"], res["out_count"]
    what = "retainer" if mon else "project"
    paras = []
    if not m["requests"]:
        if rp is not None:
            paras.append(f"**No extras yet. At {fmt_money(m['fee'], sym)} {'a month' if mon else ''} for {fmt_h(m['planned'])} hours, "
                         f"the work is priced at {fmt_rate(rp, sym)} an hour, the rate each extra will be priced at.**".replace("  ", " "))
        else:
            paras.append("**No extras logged yet. The scope below sets the line before the first one arrives.**")
    elif res["effective_rate"] is not None and ab_h > 0:
        paras.append(f"**{m['client']} now pays you {fmt_rate(res['effective_rate'], sym)} an hour, against the "
                     f"{fmt_rate(rp, sym)} you priced the work at.**")
    elif res["effective_rate"] is not None:
        paras.append(f"**{m['client']} still pays you the {fmt_rate(rp, sym)} an hour you priced the work at.**")
    elif ab_h > 0:
        paras.append(f"**{m['client']} has had {fmt_h(ab_h)} {hours_word(ab_h)} of unbilled extras.** "
                     "[NEED: the fee and the hours you planned] would show what that has done to your hourly rate.")
    else:
        paras.append(f"**{m['client']}: {n_out} {'request' if n_out == 1 else 'requests'} outside what you agreed.**")
    if m["requests"]:
        since = f"Since {P.long_date(m['period_start'])}" if (mon and m["period_start"]) else "On this project"
        t = (f"{since}, {m['client']} has had {n_out} {'thing' if n_out == 1 else 'things'} outside what you agreed, "
             f"about {fmt_h(res['out_hours_known'])} {hours_word(res['out_hours_known'])} of work."
             if n_out else f"{since}, every request {m['client']} made sits inside what you agreed.")
        if ab_n:
            t += f" You did {ab_n} of them without billing, {fmt_h(ab_h)} {hours_word(ab_h)} in all"
            if res["creep_value"] is not None:
                t += (f", worth {fmt_money(res['creep_value'], sym)} at your priced rate. That is time you gave away, "
                      "not cash that left your account")
            t += "."
        if res["effective_rate"] is not None and ab_h > 0 and mon:
            t += f" The hourly figure counts the {fmt_h(m['months'])} months since then."
        paras.append(t)
    if m.get("previous") and res["effective_rate"] is not None:
        pv = m["previous"]
        moved = "up from" if res["effective_rate"] > pv["rate"] + 0.5 else "down from" if res["effective_rate"] < pv["rate"] - 0.5 else "level with"
        paras.append(f"Since your last kit on {P.long_date(pv['date'])}: {fmt_rate(res['effective_rate'], sym)} an hour now, "
                     f"{moved} {fmt_rate(pv['rate'], sym)} then.")
    if res["unexplained_hours"]:
        paras.append(f"Your hours also run over plan, and the extras explain only part of it: {fmt_h(res['unexplained_hours'])} hours "
                     "of in-scope work took longer than you priced. A scope statement will not fix that on its own.")
    if res["pending"]:
        n = len(res["pending"])
        pr = res.get("pending_range")
        if pr:
            more = " or more, since you said it could run higher" if pr["open_top"] else ""
            paras.append(f"Open now: {n} {'request' if n == 1 else 'requests'} outside scope, {fmt_h(pr['hours_lo'])} {RANGE_WORD[0]} "
                         f"{fmt_h(pr['hours_hi'])} {hours_word(2)}, {fmt_money(pr['value_lo'], sym)} {RANGE_WORD[0]} "
                         f"{fmt_money(pr['value_hi'], sym)} at your rate{more}. The replies are in section 1.")
        else:
            val = f", {fmt_money(res['pending_value'], sym)} at your rate" if res["pending_value"] is not None else ""
            paras.append(f"Open now: {n} {'request' if n == 1 else 'requests'} outside scope, "
                         f"{fmt_h(res['pending_hours'])} {hours_word(res['pending_hours'])}{val}. The replies are in section 1.")
    if m.get("agreed_differs"):
        paras.append(f"**Your agreement and your pricing disagree.** The agreement the client signed says {fmt_h(m['agreed'])} "
                     f"{hours_word(m['agreed'])}{' a month' if mon else ''}; you priced on {fmt_h(m['planned'])}. The figures here use "
                     f"your {fmt_h(m['planned'])}, which gives {fmt_rate(rp, sym)} an hour; on the agreement's {fmt_h(m['agreed'])} it is "
                     f"{fmt_rate(m['rate_agreed'], sym)}. The scope statement quotes what the client signed. Changing it is a "
                     "conversation with the client, not an edit to the kit.")
    for w in res.get("weekend_dates") or []:
        paras.append(f"**Date check:** {w}.")
    if res.get("hours_left") is not None:
        fits = [p["what"] for p in res["pending"] if p.get("fits_month")]
        paras.append(f"**This month:** {fmt_h(m['logged'])} of your {fmt_h(m['planned'])} planned hours are used, {fmt_h(res['hours_left'])} left. "
                     + (f"Only these open requests would fit in what is left: {'; '.join(fits)}." if fits
                        else "None of the open requests fits in what is left without moving something."))
    late = [d for d in res["dependencies"] if d.get("days_late")]
    if late:
        worst = max(d["days_late"] for d in late)
        paras.append(f"The client's side is behind on {len(late)} {'item' if len(late) == 1 else 'items'}, "
                     f"the latest by {worst} {'day' if worst == 1 else 'days'}. Section 2 lists the dates, so a delay on their side is on record.")
    return paras


# ---------------------------------------------------------------- wording gates
_CODES = "|".join(P.CURRENCY_CODES)
_NUM = r"\d(?:[\d.,'  ]|\s(?=\d{3}\b))*\d|\d"
_SIGN = r"(?-i:(?:US|AU|A|NZ|S|CA|C|HK|R)?\$|[£€₹¥₱₦₩₪₺฿]|\bRM\b|zł|Kč|\bkr\b|\b(?:" + _CODES + r")\b)"
MONEY_RE = re.compile(r"(?P<s1>" + _SIGN + r")\s?(?P<n1>" + _NUM + r")\s?(?P<k1>k\b)?"
                      r"|(?P<n2>" + _NUM + r")\s?(?P<k2>k\b)?\s?(?P<s2>" + _SIGN + r"|pounds|quid|dollars|bucks|euros|rupees)", re.I)
HOURS_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s?(hours?|hrs?|h|std\.?|stunden)\b", re.I)
PCT_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s?(%|per ?cent)", re.I)


def quantity_hours(text):
    """Hours the founder wrote into a deliverable's own quantity ('1 session of 1 hour'), allowed back in the copy."""
    out = set()
    for mm in HOURS_RE.finditer(text or ""):
        try:
            out.add(P._num(mm.group(1)))
        except (L.Ambiguous, L.Unreadable):
            pass
    for mm in re.finditer(r"\b(an?|one)\s+hour\b", text or "", re.I):
        out.add(1.0)
    return out


def allowed_figures(m, res):
    money = {(m["previous"] or {}).get("rate"), m["fee"], m["rate_priced"], m["rate_changes"], res.get("effective_rate"), res.get("creep_value"),
             res.get("fee_period"), res.get("pending_value"), res.get("allowance_year_value"), res.get("rate_with_allowance"),
             res.get("allowance_past_rest_value"), res.get("actual_rate"), m.get("rate_agreed")}
    if res.get("pending_range"):
        money.update({res["pending_range"]["value_lo"], res["pending_range"]["value_hi"]})
    hours = {m["planned"], m["actual"], res.get("absorbed_hours"), res.get("pending_hours"), res.get("out_hours_known"),
             m["allowance"], res.get("allowance_year_hours"), res.get("allowance_past_covered"), res.get("allowance_past_rest"),
             res.get("planned_period"), res.get("unexplained_hours"), m["hpd"], m.get("agreed"), m.get("logged"), res.get("hours_left")}
    if res.get("pending_range"):
        hours.update({res["pending_range"]["hours_lo"], res["pending_range"]["hours_hi"]})
    for r in m["requests"]:
        hours.update({r["hours"], r["hours_lo"], r["hours_hi"]})
        for h in (r["hours"], r["hours_lo"], r["hours_hi"]):
            if h is not None and m["rate_changes"]:
                money.add(r5(h * m["rate_changes"]))
                if m["rate_priced"]:
                    money.add(h * m["rate_priced"])
    for p in res["pending"]:
        money.update({p["price"], p["price_lo"], p["price_hi"]})
    for d in m["deliverables"]:
        hours.add(d["hours"])
        hours.update(quantity_hours(d["quantity"]))
    pct = set()
    if res.get("rate_drop") is not None:
        pct.add(round(res["rate_drop"] * 100))
    return {x for x in money if x is not None}, {x for x in hours if x is not None}, pct


def _read_fig(raw):
    """A figure in Claude's copy, read in the founder's style (9.800 € or $9,800). None if it cannot be read."""
    try:
        return L.parse_number(raw.replace(" ", " ").replace(" ", " "), P.DECIMAL, allow_words=False)[0]
    except (L.Ambiguous, L.Unreadable):
        try:
            return L.parse_number(raw, "comma" if P.DECIMAL == "comma" else "dot", allow_words=False)[0]
        except (L.Ambiguous, L.Unreadable):
            return None


def figure_problems(text, allowed, where):
    money, hours, pct = allowed
    probs = []
    for mm in MONEY_RE.finditer(text):
        raw, kilo = (mm.group("n1"), mm.group("k1")) if mm.group("n1") else (mm.group("n2"), mm.group("k2"))
        v = _read_fig(raw)
        if v is None:
            probs.append(f"{where}: '{mm.group(0).strip()}' cannot be read as one figure; write it as the calculator printed it")
            continue
        if kilo:
            v *= 1000
        if not any(abs(v - a) <= 0.5 or (v >= 1000 and abs(v - a) <= 50 and kilo) for a in money):
            probs.append(f"{where}: {mm.group(0).strip()} is not a figure the calculator worked out; use the figures from `compute`")
    for mm in HOURS_RE.finditer(text):
        v = _read_fig(mm.group(1))
        if v is None or (not any(abs(v - a) <= 0.05 for a in hours) and not (v == math.floor(v) and v <= 2 and re.search(r"\b(within|in|takes?)\b", text[max(0, mm.start() - 12):mm.start()]))):
            probs.append(f"{where}: '{mm.group(0)}' is not an hours figure from the founder or the calculator")
    for mm in PCT_RE.finditer(text):
        v = _read_fig(mm.group(1))
        if v is None or not any(abs(v - a) <= 0.5 for a in pct):
            probs.append(f"{where}: {mm.group(0)} is not a percentage the calculator worked out")
    return probs


def copy_problems(text, where, client=False, max_words=None):
    probs, warns, _w = check_copy.check(text, max_words=max_words, client=client)
    return [f"{where}: {p}" for p in probs], [f"{where}: {w}" for w in warns]


def gate(m, res):
    """Every check on what Claude wrote. Returns (problems, warnings). Problems stop the build."""
    probs, warns = [], []
    allowed = allowed_figures(m, res)
    sym = m["sym"]

    def text_check(text, where, client=False, max_words=None):
        if not text:
            return
        p, w = copy_problems(text, where, client, max_words)
        probs.extend(p)
        warns.extend(w)
        probs.extend(figure_problems(text, allowed, where))

    # diagnosis
    dg = str(m["diagnosis"].get("type") or "").lower()
    if dg not in DIAGNOSES:
        probs.append(f"diagnosis.type must be one of: {', '.join(DIAGNOSES)}")
    if not str(m["diagnosis"].get("evidence") or "").strip():
        probs.append("diagnosis.evidence is empty: name what in the founder's words shows the diagnosis")
    text_check(str(m["diagnosis"].get("evidence") or ""), "diagnosis")
    # unclear requests must be settled
    for r in m["requests"]:
        if r["class"] == "Unclear":
            probs.append(f"request {r['id']} ('{r['what']}') is still unclear: ask the founder or set resolved_as to in or out, "
                         "and name it in the included or not-included list")
    # scope statement
    if not m["deliverables"]:
        probs.append("scope.deliverables is empty: list what the client gets, each with a quantity or limit")
    for d in m["deliverables"]:
        nm = d["name"] or "a deliverable"
        if not d["name"]:
            probs.append("a deliverable has no name")
        q = d["quantity"]
        if not q:
            probs.append(f"deliverable '{nm}' has no quantity or limit (for example '12 a month', 'one page, up to 800 words')")
        elif VAGUE_QTY.search(q) or not (re.search(r"\d", q) or re.search(NUMBER_WORDS, q.lower())):
            probs.append(f"deliverable '{nm}': '{q}' is open-ended; give a number or a cap")
        if not d["acceptance"]:
            probs.append(f"deliverable '{nm}' has no 'done when' line (what makes it finished)")
        elif SUBJECTIVE.search(d["acceptance"]):
            probs.append(f"deliverable '{nm}': 'done when' is a feeling ('{d['acceptance']}'); make it something either side can check")
        text_check(" ".join([d["name"], d["quantity"], d["acceptance"]]), f"deliverable '{nm}'")
    if len(m["not_included"]) < 3 and m["deliverables"]:
        probs.append(f"the not-included list has {len(m['not_included'])} items; name at least three things clients assume are included "
                     "(references/common-assumed-items.md)")
    out_text = " ".join(m["not_included"]).lower()
    out_words = key_words(out_text)
    for r in m["requests"]:
        if r["class"] == "Out" and r["status"] != "Declined":
            if not (key_words(r["what"]) & out_words):
                probs.append(f"the not-included list does not name request {r['id']} ('{r['what']}'); this client's own extras belong on it")
    for d in m["dependencies"]:
        if not d["what"]:
            probs.append("a client dependency has no description")
    if m["deliverables"] and not m["dependencies"]:
        warns.append("no client dependencies listed: most scopes need at least one thing from the client by a date")
    for k in ("outcome", "changes"):
        text_check(m[k], f"scope.{k}")
    # the scope statement is for the client: it quotes what the client signed, never the founder's private planning figure
    if m.get("agreed_differs"):
        client_text = " ".join([m["outcome"], m["changes"]] + m["included"] + m["assumptions"]
                               + [" ".join([d["name"], d["quantity"], d["acceptance"]]) for d in m["deliverables"]])
        for mm in HOURS_RE.finditer(client_text):
            v = _read_fig(mm.group(1))
            if v is not None and abs(v - m["planned"]) < 0.05:
                probs.append(f"scope statement: '{mm.group(0)}' is your planning figure, but the agreement the client signed says "
                             f"{fmt_h(m['agreed'])}. Quote {fmt_h(m['agreed'])}, or leave the hours out until you have agreed a change with the client")
                break
    for k in ("included", "not_included", "assumptions"):
        for i, x in enumerate(m[k], 1):
            if VAGUE_QTY.search(x) and k == "included":
                warns.append(f"included item {i} is open-ended: '{x}'")
            text_check(x, f"scope.{k} {i}")
    # responses
    by_id = {}
    for rr in m["responses"]:
        if not isinstance(rr, dict) or "request" not in rr:
            probs.append("each response needs a 'request' number")
            continue
        by_id[int(rr["request"])] = rr
    for p in res["pending"]:
        rr = by_id.get(p["id"])
        where = f"request {p['id']}"
        if not rr:
            probs.append(f"{where} ('{p['what']}') is open and has no replies: write price, swap and later options in responses")
            continue
        has_swap = bool(p["swap_candidates"])
        needed = (["price"] + (["swap"] if has_swap else []) + ["later"]
                  + (["allowance"] if p["fits_allowance"] and m["policy"] == "allowance" else [])
                  + (["scope"] if p["scope_first"] else []))
        offered = needed + (["swap"] if (not has_swap and isinstance(rr.get("swap"), dict) and str(rr["swap"].get("message") or "").strip()) else [])
        rec = str(rr.get("recommended") or "").lower()
        if rec not in offered:
            probs.append(f"{where}: recommended must be one of {', '.join(offered)}")
        for opt in offered:
            o = rr.get(opt)
            if not isinstance(o, dict) or not str(o.get("message") or "").strip():
                probs.append(f"{where}: the '{opt}' option needs a message the founder can send")
                continue
            msg, why = str(o["message"]).strip(), str(o.get("why") or "").strip()
            w = f"{where} {opt}"
            text_check(msg, w, client=True, max_words=MAX_MESSAGE_WORDS)
            if sentences(msg) > 5:
                probs.append(f"{w}: {sentences(msg)} sentences; a reply the client reads on a phone is five at most")
            if not why:
                probs.append(f"{w}: add a one-line 'why' (when this option is the right one)")
            text_check(why, f"{w} why", max_words=MAX_WHY_WORDS)
            if opt == "price":
                if p["price"] is None:
                    if "[NEED" not in msg:
                        probs.append(f"{w}: the price is not known yet, so the message must carry [NEED: price] rather than a figure")
                elif p["price_lo"] is not None:
                    lo, hi = fmt_money(p["price_lo"], sym), fmt_money(p["price_hi"], sym)
                    if not (has_fig(lo, msg) and has_fig(hi, msg)):
                        probs.append(f"{w}: the founder gave a range of hours, so the message must state both ends of the price, "
                                     f"{lo} to {hi}, not one figure")
                elif not has_fig(fmt_money(p["price"], sym), msg):
                    probs.append(f"{w}: the message must state the price, {fmt_money(p['price'], sym)}")
                own = str(o.get("price_wording") or "").strip()  # the founder's wording for this one reply ("excl. VAT" in English)
                if (m["price_wording"] or own) and p["price"] is not None:
                    tw = (own or m["price_wording"]).split()[-1]
                    if not re.search(rf"(?<!\w){re.escape(tw)}(?!\w)", msg, re.I):
                        probs.append(f"{w}: you write your prices '{m['price_wording']}', so say it here too and the invoice "
                                     "matches the reply")
            if opt == "swap":
                sf = str(o.get("swap_for") or "").strip()
                dmatch = [d for d in m["deliverables"] if sf and (sf.lower() in d["name"].lower() or d["name"].lower() in sf.lower())]
                if not sf:
                    probs.append(f"{w}: name the deliverable it swaps for in 'swap_for'")
                elif not dmatch:
                    probs.append(f"{w}: '{sf}' is not one of the deliverables in the scope")
                elif not (key_words(sf) & key_words(msg)) and sf.lower() not in msg.lower():
                    probs.append(f"{w}: the message must name what is swapped out ('{sf}')")
                elif o.get("swap_hours") not in (None, ""):
                    # part of a deliverable ('six of the twelve feed posts'): the share is written as a sum, '=10*6/12'
                    sh = P.hours(o.get("swap_hours"), m["hpd"])[0]
                    tol = max(SWAP_TOLERANCE * (p["hours"] or 0), 1.0)
                    if sh is None or p["hours"] is None or abs(sh - p["hours"]) > tol:
                        probs.append(f"{w}: the part swapped out comes to {fmt_h(sh)} hours against {hours_text(p)}, not equal effort")
                elif not any(c["name"] == dmatch[0]["name"] for c in p["swap_candidates"]):
                    dh = dmatch[0]["hours"]
                    probs.append(f"{w}: '{dmatch[0]['name']}' is " + (f"{fmt_h(dh)} {hours_word(dh)} against {hours_text(p)}, not equal effort"
                                 if dh is not None else "a deliverable with no hours, so the swap cannot be checked as equal effort")
                                 + "; drop the swap option (it is optional when compute finds no equal-effort swap), give the hours, or for part "
                                 "of a deliverable set swap_hours to the share, such as '=10*6/12' for six of twelve posts")
            if opt == "later" and not re.search(r"\b(next|month|week|phase|after|January|February|March|April|May|June|July|August|"
                                                 r"September|October|November|December|quarter|renewal|once|when)\b|\d", msg, re.I):
                probs.append(f"{w}: say when it would happen")
            if opt == "allowance" and not re.search(r"\b(allowance|goodwill|on us|on the house|no charge|included this month)\b", msg, re.I):
                probs.append(f"{w}: say it comes out of the goodwill allowance, so the client sees the gift")
            if p.get("open_top") and opt in ("price", "scope") and MONEY_RE.search(msg) and not NOT_A_CAP.search(msg):
                probs.append(f"{w}: you said this could run higher than your range, so say the figure is an estimate before scoping, "
                             "not a cap (for example 'that's before scoping, not a cap')")
            if opt == "scope" and not SCOPE_STEP.search(msg):
                probs.append(f"{w}: name the scoping step (a short written plan or spec with a firm price) before the build is priced")
    for i in by_id:
        if i not in res["pending_ids"]:
            warns.append(f"responses hold request {i}, which is not an open out-of-scope request; it is not printed")
    if res["absorbed_count"] and not m["reset_message"] and not m["reset_already_sent"]:
        probs.append("there are extras you did without billing: write reset_message, the note that tells the client how extras work from now")
    text_check(m["reset_message"], "reset_message", client=True, max_words=MAX_RESET_WORDS)
    gift = re.compile(r"\b(on (us|me|the house)|no charge|free of charge|for free|goodwill|allowance|included at no)\b", re.I)
    if m["policy"] != "allowance":
        for txt, where in [(m["reset_message"], "reset_message"), (m["allowance_line"], "allowance_line")] + \
                [(str((rr.get(o) or {}).get("message") or ""), f"request {rr.get('request')} {o}") for rr in m["responses"]
                 if isinstance(rr, dict) for o in ("price", "swap", "later", "scope")]:
            if txt and gift.search(txt):
                probs.append(f"{where}: it promises free work, but the founder has not chosen a goodwill allowance. Never put a policy "
                             "in the founder's mouth; drop it, or ask them and set extras_policy to allowance")
    for item in m["founder_owes"]:
        if m["reset_message"] and not (key_words(item) & key_words(m["reset_message"])):
            probs.append(f"reset_message: you owe the client '{item}'; own it in one clause, so the note does not read as one-sided")
    text_check(m["allowance_line"], "allowance_line", client=True, max_words=60)
    text_check(m["note"], "note", max_words=MAX_NOTE_WORDS)
    return probs, warns


# ---------------------------------------------------------------- render the kit (markdown, then docx)
def changes_text(m, res):
    if m["changes"]:
        return m["changes"]
    sym, mon = m["sym"], m["billing"] == "monthly"
    rate = fmt_rate(m["rate_changes"], sym) if m["rate_changes"] else "[NEED: your rate]"
    t = (f"Anything not listed above is a change. For each one I will send a short change request with what it is, the hours, "
         f"the price at {rate} an hour, and any effect on dates. Work on it starts once you approve it in writing; an email reply is enough.")
    if m["policy"] == "allowance" and m["allowance"]:
        t += (f" Each {'month' if mon else 'project'} includes {fmt_h(m['allowance'])} {hours_word(m['allowance'])} of small extras at no charge. "
              "I will tell you when one is used, and anything beyond that is priced as above.")
    if m["policy"] == "swap":
        t += " Where you would rather keep the fee where it is, we can swap the change for a listed item of the same effort."
    return t


def render(m, res, title_date):
    sym, mon = m["sym"], m["billing"] == "monthly"
    L = []
    a = L.append
    a(f"# Scope kit: {m['client']}")
    a(f"{m['offer'] + ', ' if m['offer'] else ''}prepared {title_date}{' by ' + m['founder'] if m['founder'] else ''}")
    a(f"*{LAWYER_LINE}*")
    a("")
    a("## At a glance")
    for line in headline(m, res):
        a(line)
    dg = str(m["diagnosis"].get("type") or "").lower()
    if dg in DIAGNOSES:
        a(f"**What is going on:** {DIAGNOSES[dg]}. {m['diagnosis'].get('evidence', '').strip()}")
    if m["note"]:
        a(m["note"])
    if m["founder_owes"]:
        a(f"**Before you send anything:** your side still owes {m['client']} this: {'; '.join(m['founder_owes'])}. "
          + ("The reset note owns it in one clause, so the scope arrives with your side in order." if m["reset_message"]
             else "Send it, or say when it is coming, before the scope goes out."))
    a("")
    # 1 responses
    a("## 1. What to say")
    if m["reset_message"] and not m["requests"]:
        a("### Send this with the scope")
        a("Before the work starts, so the scope arrives as the plan rather than a correction.")
        a(f"> {msg_md(m['reset_message'])}")
    elif m["reset_message"]:
        a("### First, reset how extras work")
        a("Send this once, with the scope statement attached, before you answer the next request.")
        a(f"> {msg_md(m['reset_message'])}")
    if res["pending"]:
        a("Ways to say yes to each open request, with the one to use first. Edit the words until they sound like you.")
        by_id = {int(r["request"]): r for r in m["responses"] if isinstance(r, dict) and "request" in r}
        for p in res["pending"]:
            rr = by_id.get(p["id"], {})
            hrs = hours_text(p) + (p["per"] if p["hours"] is not None else "")
            price = f", {price_text(p, sym)}{p['per']}" if p["price"] is not None else ""
            if price and m["price_wording"]:
                price += f" {m['price_wording']}"
            a(f"### Request {p['id']}: {p['what']}")
            a(f"*{hrs[0].upper() + hrs[1:]}{price}*")
            if p["hours_lo"] is not None and p["price"] is not None:
                a(f"You gave a range, so every reply quotes both ends. Only the hours totals count the middle, {fmt_h(p['hours'])} hours.")
            if p.get("open_top"):
                a("You said this could run higher than your range, so the replies call the range an estimate before scoping, not a cap.")
            if not p["swap_candidates"]:
                a("No swap reply: " + (f"nothing in the plan is equal effort (the nearest, {p['swap_nearest']['name']}, is "
                  f"{fmt_h(p['swap_nearest']['hours'])} {hours_word(p['swap_nearest']['hours'])})."
                  if p["swap_nearest"] else "the plan's deliverables have no hours to match it against."))
            rec = str(rr.get("recommended") or "")
            order = [rec] + [o for o in ("scope", "price", "swap", "later", "allowance") if o != rec]
            for opt in order:
                o = rr.get(opt)
                if not isinstance(o, dict) or not o.get("message"):
                    continue
                lab = OPTION_LABELS[opt]
                a(f"**{'Recommended: ' if opt == rec else ''}{lab}.** {str(o.get('why') or '').strip()}")
                a(f"> {msg_md(o['message'])}")
    elif not m["reset_message"]:
        a("No open requests to answer. When the next one arrives, log it in the spreadsheet and use the change request form in section 4.")
    a("")
    # 2 scope
    a("## 2. Scope statement")
    a("*Draft. If you plan to put this into a contract, check it with a lawyer first. The 'done when' lines and the line on late items "
      "are proposals, not terms from your agreement: keep, change or cut each before you send it.*")
    if m["outcome"]:
        a(f"**The outcome.** {m['outcome']}")
    else:
        a("**The outcome.** [NEED: one sentence on what the client gets from this work]")
    a("### What you get")
    a("| Deliverable | How much | Who does it | Done when |")
    a("|---|---|---|---|")
    for d in m["deliverables"]:
        a(f"| {mdcell(d['name'])} | {mdcell(d['quantity'])} | {mdcell(d['who'] or 'Us')} | {mdcell(d['acceptance'])} |")
    if m["included"]:
        a("### Also included")
        for x in m["included"]:
            a(f"- {x}")
    a("### Not included")
    a("These are priced separately if you want them.")
    for x in m["not_included"]:
        a(f"- {x}")
    if m["assumptions"]:
        a("### Assumptions")
        for x in m["assumptions"]:
            a(f"- {x}")
    a("### What we need from you, and by when")
    if res["dependencies"]:
        a("| What | Who | By when | Status today |")
        a("|---|---|---|---|")
        for d in res["dependencies"]:
            a(f"| {mdcell(d['what'])} | {mdcell(d['owner'])} | {mdcell(d['due_label'])} | {mdcell(d['status'])} |")
        a("If something on this list arrives late, the dates that depend on it move by the same number of days.")
    else:
        a("[NEED: what the client must provide, and by when]")
    a("### Rounds of changes")
    a(f"Each deliverable includes {m['revisions']} {'round' if m['revisions'] == 1 else 'rounds'} of changes. "
      "A further round, or a change of direction after sign-off, is priced as a change.")
    a("### How changes work")
    a(changes_text(m, res))
    a("")
    # 2 ledger
    a("## 3. Creep ledger")
    if m["requests"]:
        a("| Date | Request | In or out | Hours | Status | Worth at your rate | Reply |")
        a("|---|---|---|---|---|---|---|")
        rec = {int(r.get("request")): str(r.get("recommended") or "") for r in m["responses"] if isinstance(r, dict) and "request" in r}
        for r in sorted(m["requests"], key=lambda x: (x["date"] or date.max, x["id"])):
            pend = next((x for x in res["pending"] if x["id"] == r["id"]), None)
            if pend and pend["price"] is not None:
                worth = price_text(pend, sym)  # an open request shows the price its replies quote
            else:
                worth = fmt_money(r["hours"] * m["rate_priced"], sym) if (r["class"] == "Out" and r["hours"] is not None and m["rate_priced"]) else ""
            reply = OPTION_LABELS.get(rec.get(r["id"], ""), "") if r["status"] == "Asked" else ""
            kind = " (doing their part)" if r["kind"] == "drift" else ""
            status = "Done" if (r["class"] == "In" and r["status"].startswith("Done")) else r["status"]
            a(f"| {P.short_date(r['date'], r['month_only']) or mdcell(r['date_text'])} | {mdcell(r['what'])}{kind} | {r['class']} | "
              f"{fmt_h(r['hours'])} | {status} | {worth} | {reply} |")
        tail = f"Done without billing: {fmt_h(res['absorbed_hours'])} {hours_word(res['absorbed_hours'])}"
        if res["creep_value"] is not None:
            tail += f", worth {fmt_money(res['creep_value'], sym)} at your priced rate of {fmt_rate(m['rate_priced'], sym)} an hour"
        a(tail + ".")
        if res["effective_rate"] is not None and res["absorbed_hours"]:
            basis = (f"{fmt_money(m['fee'], sym)} a month for {fmt_h(m['months'])} months, divided by {fmt_h(res['planned_period'])} planned hours "
                     f"plus {fmt_h(res['absorbed_hours'])} unbilled") if mon else \
                (f"{fmt_money(m['fee'], sym)} divided by {fmt_h(m['planned'] + res['absorbed_hours'])} hours: the {fmt_h(m['planned'])} "
                 f"you planned plus the {fmt_h(res['absorbed_hours'])} you gave away")
            a(f"What the work now pays you: {fmt_rate(res['effective_rate'], sym)} an hour ({basis}).")
        a("The spreadsheet holds the same ledger with live formulas. Add each new request there as it arrives.")
    else:
        a("Nothing logged yet. Use the spreadsheet to log each request as it arrives, with rough hours.")
    a("")
    # 4 form
    a("## 4. Change request form")
    rr_all = {int(r["request"]): r for r in m["responses"] if isinstance(r, dict) and "request" in r}
    if res["pending"]:
        a("Filled in for each open request. A blank copy follows.")
    for first in res["pending"]:
        rr = rr_all.get(first["id"], {})
        reason = str(rr.get("reason") or "").strip() or "[NEED: why the client wants it, in their words]"
        a(f"### {first['what']}")
        a("| Field | Detail |")
        a("|---|---|")
        a(f"| Change requested | {mdcell(first['what'])} |")
        a(f"| Why | {mdcell(reason)} |")
        a(f"| Effort | {hours_text(first)}{first['per']}{', an estimate before scoping, not a cap' if first.get('open_top') else ''} |")
        pv = (price_text(first, sym) + first["per"]) if first["price"] is not None else "[NEED: price]"
        if first["price"] is not None and m["price_wording"]:
            pv += f" {m['price_wording']}"
        a(f"| Price | {pv} |")
        a(f"| Effect on dates | {mdcell(str(rr.get('date_impact') or '').strip() or '[NEED: what moves, and by how many days]')} |")
        fr = next((r for r in m["requests"] if r["id"] == first["id"]), {})
        a(f"| Requested by and date | {mdcell(m['client'])}, {P.short_date(fr.get('date'), fr.get('month_only')) or '[NEED: date]'} |")
        a("Approved by: ____")
        a("Signature: ____")
        a("Date: ____")
        a("")
    a("### Blank form")
    for f in ("Change requested", "Why it is needed", "Effort (hours)", "Price", "Effect on dates", "Requested by", "Approved by", "Signature", "Date"):
        a(f"{f}: ____")
    a("")
    # 5 allowance
    if m["policy"] == "allowance" and m["allowance"]:
        a("## 5. Goodwill allowance")
        per = "a month" if mon else "on this project"
        line = f"You give {fmt_h(m['allowance'])} {hours_word(m['allowance'])} of small extras {per}, and the client can see it."
        if res["allowance_year_value"] is not None:
            line += (f" At your priced rate that is {fmt_money(res['allowance_year_value'], sym)} "
                     f"{'a year' if mon else 'in all'}, given on purpose rather than leaking away.")
        a(line)
        if res["absorbed_hours"] and res["allowance_past_covered"] is not None:
            a(f"Had it been in place{' since ' + P.long_date(m['period_start']) if (mon and m['period_start']) else ''}, it would have covered "
              f"{fmt_h(res['allowance_past_covered'])} of the {fmt_h(res['absorbed_hours'])} unbilled hours; the other "
              f"{fmt_h(res['allowance_past_rest'])}, worth {fmt_money(res['allowance_past_rest_value'], sym)}, would have been priced.")
        if res["rate_with_allowance"] is not None and mon:
            a(f"With the allowance used in full, the monthly fee pays {fmt_rate(res['rate_with_allowance'], sym)} an hour "
              f"against the {fmt_rate(m['rate_priced'], sym)} you priced.")
        if m["allowance_line"]:
            a("How to tell the client:")
            a(f"> {msg_md(m['allowance_line'])}")
        a("")
    # assumptions
    a("## What this kit assumed")
    for x in m["assumed"]:
        a(f"- {x}.")
    a(f"- {SALES_TAX_LINE}.")
    for x in m["notes"]:
        if "worked out from" not in x:
            a(f"- {x}.")
    for x in m["needs"]:
        a(f"- [NEED: {x}]")
    a("*Planning, not legal or tax advice. Contract wording and disputes go to a lawyer; sales tax to your accountant.*")
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- workbook
def xl_date(d):
    """A date as a spreadsheet serial number (days since 30 December 1899)."""
    return (d - date(1899, 12, 30)).days if d else None


def workbook(m, res, path):
    sym, mon = m["sym"], m["billing"] == "monthly"
    reqs = sorted(m["requests"], key=lambda x: (x["date"] or date.max, x["id"]))
    # Months counted is live: from the start date to the 'count up to' date, or to today when that cell is blank,
    # so logging next month's requests moves the hourly figure the way the kit says it will.
    months_f = ('=IF(N(B6)>0,MAX(ROUND(MAX(IF(N(B7)>0,B7,TODAY())-B6,1)/30.4375,1),0.5),"")' if mon else "=1")
    rate_rows = [
        [("Rates and creep", "title")],
        [("Yellow cells are yours to change. Everything else recalculates.", "small")],
        [],
        [("What the client pays" + (" a month" if mon else " for the project"), "bold"), (m["fee"], "input_money")],
        [("Hours you planned" + (" a month" if mon else " for the project"), "bold"), (m["planned"], "input_hours")],
        [("Count starts (the first day the hourly figure counts)" if mon else "Count starts (not used for a project)", "bold"),
         (xl_date(m["period_start"]) if mon else None, "input_date")],
        [("Count up to (leave blank to count to today)", "bold"), (None, "input_date")],
        [("Months counted" if mon else "Months counted (1 for a project)", "bold"), (months_f, "hours", m["months"] if mon else 1)],
        [("Your rate for extra work (leave blank to use the priced rate)", "bold"),
         (m["rate_changes"] if m["rate_changes_src"].startswith("your own") else None, "input_money")],
        [("Goodwill allowance, hours" + (" a month" if mon else ""), "bold"), (m["allowance"] or 0, "input_hours")],
        [],
        [("The rate you priced it at (fee divided by planned hours)", "text"),
         ("=IF(AND(B4>0,B5>0),B4/B5,\"\")", "money2", m["rate_priced"])],
        [("Rate used to price extras", "text"), ("=IF(N(B9)>0,B9,B12)", "money2", m["rate_changes"])],
        [("Out-of-scope hours done without billing", "text"),
         ("=SUMIFS(Ledger!D:D,Ledger!C:C,\"Out\",Ledger!E:E,\"Done, not billed\")", "hours", res["absorbed_hours"])],
        [("What the work now pays you an hour", "text"),
         ("=IF(AND(B4>0,B5>0,N(B8)>0),B4*B8/(B5*B8+B14),\"\")", "money2", res["effective_rate"])],
        [("Unbilled work at your priced rate", "text"), ("=IF(N(B12)>0,B14*B12,\"\")", "money", res["creep_value"])],
        [("Open requests outside scope, hours", "text"),
         ("=SUMIFS(Ledger!D:D,Ledger!C:C,\"Out\",Ledger!E:E,\"Asked\")", "hours", res["pending_hours"])],
        [("Open requests at your rate (single prices; a range shows in its own row)", "text"),
         ("=SUMIFS(Ledger!G:G,Ledger!C:C,\"Out\",Ledger!E:E,\"Asked\")", "money", res["pending_value"] or 0)],
        [("Goodwill allowance a year at your priced rate" if mon else "Goodwill allowance at your priced rate", "text"),
         (f"=IF(N(B12)>0,B10*{12 if mon else 1}*B12,\"\")", "money", res["allowance_year_value"] or 0)],
        [],
        [("Worth at your priced rate is time given away, not cash lost. Prices round to the nearest 5 at 100 or more. "
          "Where you gave hours as a range, the ledger counts the middle; the replies quote both ends.", "small")],
        [(SALES_TAX_LINE + ".", "small")],
        [("Planning, not legal or tax advice.", "small")],
    ]
    led = [[("Date", "head"), ("Request", "head"), ("In or out", "head"), ("Hours", "head"), ("Status", "head"),
            ("Worth at your priced rate", "head"), ("Price at your rate", "head"), ("Reply chosen", "head")]]
    rec = {int(r.get("request")): OPTION_LABELS.get(str(r.get("recommended") or ""), "")
           for r in m["responses"] if isinstance(r, dict) and "request" in r}
    worth_f = '=IF(AND(C{i}="Out",N(D{i})>0,N(Rates!$B$12)>0),D{i}*Rates!$B$12,"")'
    price_f = ('=IF(AND(C{i}="Out",N(D{i})>0,N(Rates!$B$13)>0),IF(D{i}*Rates!$B$13>=100,ROUND(D{i}*Rates!$B$13/5,0)*5,'
               'ROUND(D{i}*Rates!$B$13,0)),"")')
    for i, r in enumerate(reqs, 2):
        worth = r["hours"] * m["rate_priced"] if (r["class"] == "Out" and r["hours"] is not None and m["rate_priced"]) else ""
        price = r5(r["hours"] * m["rate_changes"]) if (r["class"] == "Out" and r["hours"] is not None and m["rate_changes"]) else ""
        pcell = (price_f.format(i=i), "money", price)
        if r["status"] == "Asked" and r["hours_lo"] is not None and m["rate_changes"]:
            pcell = (f"{fmt_money(r5(r['hours_lo'] * m['rate_changes']), sym)} to {fmt_money(r5(r['hours_hi'] * m['rate_changes']), sym)}"
                     + (" or more" if r.get("open_top") else ""), "text")
        status = "Done" if (r["class"] == "In" and r["status"].startswith("Done")) else r["status"]
        led.append([(P.short_date(r["date"], r["month_only"]) or r["date_text"], "input_text"), (r["what"], "input_text"),
                    (r["class"], "input_choice"), (r["hours"], "input_hours"), (status, "input_choice"),
                    (worth_f.format(i=i), "money", worth), pcell,
                    (rec.get(r["id"], "") if r["status"] == "Asked" else "", "input_text")])
    for i in range(len(reqs) + 2, len(reqs) + 32):  # empty rows ready for the next requests
        led.append([("", "input_text"), ("", "input_text"), ("", "input_choice"), ("", "input_hours"), ("", "input_choice"),
                    (worth_f.format(i=i), "money", ""), (price_f.format(i=i), "money", ""), ("", "input_text")])
    last = len(led)
    xlsx_writer.write(path, [
        {"name": "Ledger", "rows": led, "widths": [11, 46, 11, 8, 17, 16, 14, 18], "freeze_row": 1,
         "validations": [(f"C2:C{last}", ["In", "Out", "Unclear"]),
                         (f"E2:E{last}", ["Asked", "Done, not billed", "Done, billed", "Done", "Swapped", "Declined"])]},
        {"name": "Rates", "rows": rate_rows, "widths": [62, 16]},
    ], symbol=sym.strip(), title=f"Creep ledger: {m['client']}", credit="Made with Merigrove Scope Guard",
        paper=m["paper"], sign_after=P.STYLE["sign_after"], date_order=m["date_order"])


# ---------------------------------------------------------------- commands
def print_figures(m, res):
    sym = m["sym"]
    print(f"CLIENT: {m['client']} | offer: {m['offer'] or '[not named]'} | billing: {m['billing']} | currency: {m['currency'] or '[NEED]'}"
          f" | dates: {'month first' if m['date_order'] == 'mdy' else 'day first' if m['date_order'] == 'dmy' else 'order not known'}"
          f" | working day: {fmt_h(m['hpd'])} hours ({m['hpd_src']})")
    print(f"LOCALE: country {m['country'] or '[not given]'} | paper {m['paper'].upper() if m['paper'] == 'a4' else 'Letter'} | "
          f"document language {m['lang']} | numbers written {P.style_sample() if P.STYLE['decimal'] else 'as 1,234.50 (no comma decimals seen)'}")
    print(f"FEE: {fmt_money(m['fee'], sym)}{' a month' if m['billing'] == 'monthly' else ''} | planned hours: {fmt_h(m['planned'])}"
          f"{' | actual hours: ' + fmt_h(m['actual']) if m['actual'] else ''}")
    print(f"RATE PRICED: {fmt_rate(m['rate_priced'], sym)} an hour | rate for extras: {fmt_rate(m['rate_changes'], sym)} ({m['rate_changes_src']})")
    if m.get("agreed_differs"):
        print(f"AGREED DIFFERS: the signed agreement says {fmt_h(m['agreed'])} hours, you priced on {fmt_h(m['planned'])}. "
              f"At the agreement's hours the fee is {fmt_rate(m['rate_agreed'], sym)} an hour. Tell the founder both in the first reply; "
              f"client-facing text quotes {fmt_h(m['agreed'])} (what the client signed), never {fmt_h(m['planned'])}")
    if m["billing"] == "monthly":
        print(f"PERIOD: from {P.long_date(m['period_start']) or '[NEED]'} | months counted: {fmt_h(m['months']) if m['months'] is not None else '[NEED]'}")
    print(f"ABSORBED: {res['absorbed_count']} out-of-scope requests done without billing, {fmt_h(res['absorbed_hours'])} hours, "
          f"worth {fmt_money(res['creep_value'], sym)} at the priced rate")
    print(f"EFFECTIVE RATE: {fmt_rate(res['effective_rate'], sym)} an hour"
          + (f" ({round(res['rate_drop'] * 100)}% below the priced rate)" if res["rate_drop"] else ""))
    if res["actual_rate"]:
        print(f"ACTUAL: at the hours you say you work, {fmt_rate(res['actual_rate'], sym)} an hour; "
              f"{fmt_h(res['unexplained_hours'])} hours over plan that no extra explains")
    if m["policy"] == "allowance":
        print(f"ALLOWANCE: {fmt_h(m['allowance'])} hours | {'a year' if m['billing'] == 'monthly' else 'on the project'} at the priced rate: {fmt_money(res['allowance_year_value'], sym)} | "
              f"would have covered {fmt_h(res['allowance_past_covered'])} of the unbilled hours")
    print(f"POLICY: {m['policy']} | relationship: {m['relationship']} | rounds of changes: {m['revisions']} | "
          f"price wording: {m['price_wording'] or 'none (prices stated before any sales tax)'}")
    for p in res["pending"]:
        pw = f" {m['price_wording']}" if (m["price_wording"] and p["price"] is not None) else ""
        sw = ", ".join(f"{c['name']} ({fmt_h(c['hours'])}h)" for c in p["swap_candidates"]) or \
            (f"none of equal effort (nearest {p['swap_nearest']['name']}, {fmt_h(p['swap_nearest']['hours'])}h): leave the swap reply out"
             if p["swap_nearest"] else "No equal-effort swap yet: [NEED: hours per deliverable]; leave the swap reply out")
        rng = f" (the middle, {fmt_h(p['hours'])} hours, {fmt_money(p['price'], sym)}, goes in the totals)" if p["hours_lo"] is not None else ""
        print(f"OPEN {p['id']}: {p['what']} | {hours_text(p)} | price {price_text(p, sym)}{pw}{rng} | "
              f"fits allowance: {'yes' if p['fits_allowance'] else 'no'} | swap: {sw} | later: {p['later_when']} | "
              f"scope it first: {'yes, at least the month' + chr(39) + 's planned hours' if (p['scope_first'] and m['billing'] == 'monthly') else 'yes, at least half the project' if p['scope_first'] else 'no'} | "
              f"suggested: {p['suggested']}"
              + (" | TOP OPEN: the founder said it could run higher; every reply that quotes it calls the range an estimate, not a cap"
                 if p.get("open_top") else ""))
    for r in m["requests"]:
        if r["class"] == "Unclear":
            print(f"UNCLEAR {r['id']}: {r['what']} | ask the founder whether it was part of what they agreed")
    if res.get("hours_left") is not None:
        fits = [p["what"] for p in res["pending"] if p.get("fits_month")]
        print(f"CAPACITY: {fmt_h(m['logged'])} of {fmt_h(m['planned'])} planned hours used this month, {fmt_h(res['hours_left'])} left | "
              f"fits in what is left: {', '.join(fits) if fits else 'none of the open requests'}. Say so in the first reply")
    pr = res.get("pending_range")
    if pr:
        print(f"OPEN TOTAL: {fmt_h(pr['hours_lo'])} to {fmt_h(pr['hours_hi'])} hours, {fmt_money(pr['value_lo'], sym)} to "
              f"{fmt_money(pr['value_hi'], sym)}{' or more (the founder said it could run higher)' if pr['open_top'] else ''}; "
              "quote this range, never a total of the middles")
    for d in res["dependencies"]:
        print(f"CLIENT PART: {d['what']} | {d['owner']} | by {d['due_label']} | {d['status']}")
    for w in res.get("weekend_dates") or []:
        print(f"DATE CHECK: {w}. Say so in the first reply; use the founder's answer, never move the date yourself")
    for x in m["assumed"]:
        print(f"DEFAULT: {x}")
    for x in m["notes"]:
        print(f"NOTE: {x}")
    for x in m["needs"]:
        print(f"NEED: {x}")
    for x in m["asks"]:
        print(f"ASK: {x}")
    for _k, x in m["checks"]:
        print(f"CHECK: {x}")


def results_json(m, res):
    def ser(v):
        if isinstance(v, date):
            return v.isoformat()
        if isinstance(v, dict):
            return {k: ser(x) for k, x in v.items()}
        if isinstance(v, (list, tuple)):
            return [ser(x) for x in v]
        return v
    keep = {k: m[k] for k in ("client", "offer", "business", "founder", "currency", "sym", "billing", "fee", "planned", "actual",
                              "rate_priced", "rate_changes", "rate_changes_src", "price_wording", "policy", "allowance", "relationship",
                              "revisions", "hpd", "hpd_src", "date_order", "english", "not_included", "included", "assumptions", "outcome",
                              "deliverables", "dependencies", "period_start", "months", "sources", "country", "paper",
                              "number_style", "founder_owes")}
    keep["requests"] = m["requests"]
    keep["recommended"] = {int(r["request"]): r.get("recommended") for r in m["responses"] if isinstance(r, dict) and "request" in r}
    keep["diagnosis"] = m["diagnosis"]
    return ser({"scope_guard_results": 1, "date": m["today"], "model": keep, "results": res, "needs": m["needs"]})


def stop_on_checks(m):
    if m["checks"]:
        for _k, x in m["checks"]:
            print(f"CHECK: {x}")
        keys = ", ".join(f'"{k}"' for k, _x in m["checks"])
        raise Stop(f"a headline figure looks misread. Put each CHECK line to the founder as one plain question and fix kit.json; "
                   f"if they confirm the figure is right, add {keys} to \"confirmed\" in kit.json. Nothing was built")


def cmd_compute(a, today):
    m = normalise(load(a.kit), today)
    stop_on_checks(m)
    res = compute(m)
    print_figures(m, res)
    if a.json_out:
        Path(a.json_out).write_text(json.dumps(results_json(m, res), indent=2, default=str), encoding="utf-8")
        print(f"WROTE: {a.json_out}")
    print(f"{len(m['needs'])} NEED lines, {len(m['asks'])} ASK lines")
    return 1 if (m["needs"] or m["asks"]) else 0


def cmd_build(a, today):
    m = normalise(load(a.kit), today)
    stop_on_checks(m)
    if m["asks"]:
        for x in m["asks"]:
            print(f"ASK: {x}")
        raise Stop("a figure can be read two ways or not at all. Ask the founder each ASK line as one question, write their answer "
                   "into kit.json in their own words, and build again. Nothing was written")
    res = compute(m)
    probs, warns = gate(m, res)
    md = founder_units(render(m, res, P.long_date(today)))
    p2, w2, _ = check_copy.check(md)
    probs += [f"kit text: {x}" for x in p2]
    for w in warns:
        print("WARN:", w)
    if probs:
        for p in probs:
            print("PROBLEM:", p)
        raise Stop(f"{len(probs)} problems in the wording or scope; fix kit.json and run build again. Nothing was written")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    base = f"{slug(m['client'])}-{today.isoformat()}"
    docx = out / f"scope-kit-{base}.docx"
    xlsx = out / f"creep-ledger-{base}.xlsx"
    written = []
    try:
        md_to_docx.build(md, str(docx), f"Scope kit: {m['client']}", lang=m["lang"], paper=m["paper"])
        written.append(docx)
        workbook(m, res, str(xlsx))
        written.append(xlsx)
    except Exception:
        for f in written:
            f.unlink(missing_ok=True)
        raise
    rpath = Path(a.results) if a.results else Path(a.kit).with_name(f"scope-guard-results-{base}.json")
    rpath.write_text(json.dumps(results_json(m, res), indent=2, default=str), encoding="utf-8")
    mdpath = rpath.with_suffix(".md")
    mdpath.write_text(md, encoding="utf-8")
    print(f"WROTE: {docx}")
    print(f"WROTE: {xlsx}")
    print(f"RESULTS (for memory, not the founder): {rpath}")
    print(f"TEXT COPY (for checking): {mdpath}")
    for x in m["needs"]:
        print(f"NEED: {x}")
    return 1 if m["needs"] else 0


TEMPLATE = {
    "date": None, "business": None, "founder": None, "client": None, "offer": None,
    "country": None, "currency": None, "date_order": None, "number_style": None, "english": None, "price_wording": None,
    "hours_label": None, "range_word": None,
    "billing": None, "fee": None, "planned_hours": None, "agreed_hours": None, "hours_logged_this_month": None, "actual_hours": None, "rate_for_changes": None,
    "period_start": None, "hours_per_day": None, "extras_policy": None, "allowance_hours": None,
    "relationship": None, "revision_rounds": None, "founder_owes": [], "confirmed": [],
    "sources": {"fee": "founder said", "planned_hours": "founder said"},
    "_diagnosis_types": list(DIAGNOSES),
    "diagnosis": {"type": None, "evidence": None},
    "scope": {"outcome": None,
              "deliverables": [{"name": None, "quantity": None, "hours": None, "who": None, "acceptance": None}],
              "included": [], "not_included": [], "assumptions": [],
              "dependencies": [{"what": None, "owner": None, "due": None, "received": None}], "changes": None},
    "requests": [{"id": 1, "what": None, "date": None, "hours": None, "class": None, "status": None, "kind": "extra", "resolved_as": None}],
    "responses": [{"request": 1, "recommended": None, "reason": None, "date_impact": None,
                   "price": {"message": None, "why": None}, "swap": {"message": None, "why": None, "swap_for": None, "swap_hours": None},
                   "later": {"message": None, "why": None}, "scope": {"message": None, "why": None}}],
    "reset_message": None, "allowance_line": None, "note": None,
}


def cmd_blank_form(a):
    md = ("# Change request\n*Use one form per change. Work starts once it is approved in writing.*\n\n"
          + "\n".join(f"{f}: ____" for f in ("Client", "Change requested", "Why it is needed", "Effort (hours)", "Price",
                                              "Effect on dates", "Requested by", "Date requested", "Approved by", "Signature", "Date approved"))
          + "\n")
    md_to_docx.build(md, a.out, "Change request")
    print(f"WROTE: {a.out}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("template")
    c = sub.add_parser("compute")
    c.add_argument("kit")
    c.add_argument("--today")
    c.add_argument("--json-out")
    b = sub.add_parser("build")
    b.add_argument("kit")
    b.add_argument("--out", required=True)
    b.add_argument("--today")
    b.add_argument("--results")
    f = sub.add_parser("blank-form")
    f.add_argument("out")
    a = ap.parse_args()
    if a.cmd == "template":
        print(json.dumps(TEMPLATE, indent=2))
        return 0
    if a.cmd == "blank-form":
        return cmd_blank_form(a)
    if a.cmd not in ("compute", "build"):
        ap.print_help()
        return 2
    today = date.today()
    if getattr(a, "today", None):
        t, _n = P.date_(a.today, date.today())
        if not t:
            raise Stop(f"--today '{a.today}' is not a date; use YYYY-MM-DD")
        today = t
    else:
        try:
            kd = json.loads(Path(a.kit).read_text(encoding="utf-8")).get("date") if Path(a.kit).exists() else None
            if kd:
                t, _n = P.date_(kd, date.today())
                today = t or today
        except (json.JSONDecodeError, AttributeError):
            pass
    return cmd_compute(a, today) if a.cmd == "compute" else cmd_build(a, today)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Stop as e:
        print(f"STOP: {e}.")
        sys.exit(2)
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print(f"STOP: the kit could not be built ({type(e).__name__}: {e}). Nothing usable was written; check kit.json against `scope_kit.py template`.")
        sys.exit(2)
