#!/usr/bin/env python3
"""Shared constants and helpers for the Brand Consistency Scan scripts.

Every weight, value and band the score uses lives here, in one place, so a reviewer
can change them without hunting through the code. Standard library only. No network.
"""
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import locale_numbers as LN  # noqa: E402  (copied unchanged from the Merigrove standard library)

SKILL ="revos-brand-consistency-scan"
DISPLAY = "Brand Consistency Scan"
CREDIT = "Made with Merigrove Brand Consistency Scan"

# The five questions every asset is read for. Weights total 100.
# Working defaults set 20 October 2026; Jack to confirm (see evals/TEST_REPORT.md).
QUESTIONS = [
    # key, label in the report, phrase used in sentences, weight
    ("who", "Who you serve", "who you serve", 25),
    ("what", "What you do", "what you do", 25),
    ("result", "The result you promise", "what the buyer ends up with", 20),
    ("why", "Why you over the alternatives", "why a buyer should choose you", 20),
    ("next", "What to do next", "what a buyer should do next", 10),
]
QKEYS = [q[0] for q in QUESTIONS]
QLABEL = {q[0]: q[1] for q in QUESTIONS}
QPHRASE = {q[0]: q[2] for q in QUESTIONS}
QWEIGHT = {q[0]: q[3] for q in QUESTIONS}

# Asset weights. Client-facing surfaces, where money changes hands, weigh most.
CLIENT_FACING = {"proposal", "deck", "onboarding", "invoice", "client_email"}
KIND_WEIGHTS = {
    "proposal": 3.0, "deck": 3.0, "onboarding": 3.0, "invoice": 3.0, "client_email": 3.0,
    "website": 2.0,
    "linkedin": 1.5,
    "social": 1.0, "bio": 1.0, "other": 1.0,
    "agreed": 0.0,  # the founder's agreed answers from memory: a reference, never scored as an asset
}
KIND_ALIASES = {
    "proposals": "proposal", "quote": "proposal", "scope": "proposal", "statement of work": "proposal", "sow": "proposal",
    "sales deck": "deck", "pitch deck": "deck", "slides": "deck", "credentials deck": "deck", "deck or proposal": "deck",
    "welcome email": "onboarding", "welcome pack": "onboarding", "onboarding email": "onboarding",
    "email to clients": "client_email", "client email": "client_email", "email": "client_email",
    "site": "website", "web": "website", "home page": "website", "homepage": "website", "about page": "website",
    "about": "website", "services page": "website", "landing page": "website", "case study": "website",
    "linked in": "linkedin", "linkedin profile": "linkedin", "linkedin about": "linkedin",
    "instagram": "social", "ig": "social", "tiktok": "social", "x": "social", "twitter": "social",
    "facebook": "social", "youtube": "social", "threads": "social",
    "email signature": "bio", "signature": "bio", "instagram bio": "bio", "link in bio": "bio",
}
KIND_NAMES = {
    "proposal": "proposal", "deck": "sales deck", "onboarding": "onboarding email", "invoice": "invoice",
    "client_email": "client email", "website": "website", "linkedin": "LinkedIn", "social": "social profile",
    "bio": "bio", "other": "other asset", "agreed": "agreed answers",
}

# How far one answer is from another. Same meaning 1, compatible (one is a narrower or
# broader form of the other) 0.5, silent 0.25, contradicting 0.
VALUE_SAME = 1.0
VALUE_COMPATIBLE = 0.5
VALUE_MISSING = 0.25
VALUE_CONFLICT = 0.0

BANDS = [  # lowest score in band, word, one-line reading
    (85, "Consistent", "A buyer who reads everything hears one story."),
    (65, "Drifting", "One story, with cracks a careful buyer will notice."),
    (40, "Split", "A buyer who reads two of these could describe two different businesses."),
    (0, "Different stories", "Each asset tells its own version of the business, so a referral has no one sentence to repeat."),
]

MIN_MEASURE_WORDS = 40  # below this, an asset is too short for sentence and reading measures


PROPER_NOUNS = {"LinkedIn", "Instagram", "TikTok", "YouTube", "Facebook", "X", "Substack", "Google", "Etsy", "Shopify", "Threads", "Pinterest", "Twitter", "Medium", "Behance", "Dribbble", "Upwork", "Fiverr"}


def in_sentence(label):
    """An asset label as it reads mid-sentence: 'your website', but 'your LinkedIn'."""
    label = (label or "").strip()
    first = label.split(" ")[0] if label else ""
    if not first or first in PROPER_NOUNS or first.isupper() or any(ch.isupper() for ch in first[1:]):
        return label
    return first[0].lower() + label[1:]


def round_half_up(x):
    """Whole-number rounding the way a person does it: 12.5 is 13, never 12."""
    return int(x + 0.5) if x >= 0 else -int(-x + 0.5)


def band(score):
    for low, word, line in BANDS:
        if score >= low:
            return word, line
    return BANDS[-1][1], BANDS[-1][2]


def stop(msg, code=2):
    """Print one plain STOP line and exit 2. Claude reads exit 2 as: nothing usable was produced."""
    print(f"STOP: {msg}")
    sys.exit(code)


def kind_of(raw):
    k = (raw or "").strip().lower().replace("-", " ").replace("_", " ")
    k = re.sub(r"\s+", " ", k)
    if k.replace(" ", "_") in KIND_WEIGHTS:
        return k.replace(" ", "_")
    if k in KIND_ALIASES:
        return KIND_ALIASES[k]
    for alias, kind in KIND_ALIASES.items():
        if alias in k:
            return kind
    for kind in KIND_WEIGHTS:
        if kind in k:
            return kind
    return None


def norm_text(s):
    """Normalise for word-for-word matching: straight quotes, one kind of ellipsis, single spaces, lower case."""
    s = unicodedata.normalize("NFKC", s or "")
    s = s.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
    s = s.replace("\u2026", "...").replace("\u00a0", " ")
    s = re.sub(r"\s+", " ", s)
    return s.strip().lower()


CJK = "\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af\uf900-\ufaff"


def words(s):
    """Word tokens in any script: Latin with accents, Vietnamese, Greek, Cyrillic, Arabic, Devanagari, CJK."""
    return re.findall(r"[^\W_]+(?:['\u2019][^\W\d_]+)*", s or "")


def load_json(path, what="file"):
    p = Path(path)
    if not p.exists():
        stop(f"the {what} {path} does not exist. Check the path and run again.")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        stop(f"the {what} {path} is not valid JSON (line {e.lineno}: {e.msg}). Fix it and run again.")


def read_text(path, what="file"):
    p = Path(path)
    if not p.exists():
        stop(f"the {what} {path} does not exist. Check the path and run again.")
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return p.read_text(encoding="latin-1")


def term_hash(term):
    t = " ".join(w.lower() for w in words(norm_text(term)))
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def leaked_terms(text, hashes, max_n=6):
    """Return the word runs in text whose hash is in hashes. The hashes stand for client names
    removed by redact.py; the names themselves are never written anywhere."""
    if not hashes:
        return []
    hs = set(hashes)
    toks = words(text)
    found = []
    for n in range(1, max_n + 1):
        for i in range(0, len(toks) - n + 1):
            run = " ".join(toks[i:i + n]).lower()
            if term_hash(run) in hs:
                found.append(run)
    for tok in toks:  # names in Chinese, Japanese or Korean script run on into the next word, so test every slice
        if re.search(f"[{CJK}]", tok) and len(tok) > 1:
            for a in range(len(tok)):
                for b in range(a + 2, min(len(tok), a + 8) + 1):
                    if term_hash(tok[a:b]) in hs:
                        found.append(tok[a:b])
    return sorted(set(found))


def fingerprint_ok(name):
    """Single short tokens (Ng, Le, Wu) are not fingerprinted: as words they occur in ordinary copy in other languages."""
    toks = words(norm_text(name))
    if not toks:
        return False
    return len(toks) > 1 or len(toks[0]) >= 3 or bool(re.search(f"[{CJK}]", toks[0]))


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

# Money in any currency: a symbol or code before or after the number, thousands written with commas,
# dots, spaces or the South Asian lakh grouping, an optional k/m and an optional period or sales tax tail.
CUR_SYM = "\u00a3\u20ac\u00a5\u20b9\u20a9\u20b1\u20a6\u20ab\u0e3f\u20aa\u20ba\u20b4\u20bd\u20b2\u20a1"  # pound, euro, yen, rupee, won, peso, naira, dong, baht, shekel, lira, hryvnia, rouble, guarani, colon
CUR_CODES = ("GBP|USD|EUR|SGD|AUD|NZD|CAD|HKD|INR|JPY|CNY|RMB|MYR|IDR|PHP|THB|VND|KRW|TWD|AED|SAR|QAR|ZAR|NGN|KES|GHS|"
             "CHF|SEK|NOK|DKK|PLN|CZK|HUF|BRL|MXN|ARS|CLP|COP|PEN|TRY|ILS|EGP|PKR|BDT|LKR")
_NUM = r"\d{1,3}(?:[,.\u00a0\u202f ]\d{2,3})+(?:[.,]\d{1,2})?|\d+(?:[.,]\d+)?"
_MULT = r"(?:\s?(?:k|K|m|M|mn|bn|million|lakh|lakhs|crore|crores)\b)?"
_TAX = r"(?:VAT|GST|HST|PST|QST|SST|IVA|TVA|MwSt|USt|BTW|moms|JCT|sales tax|consumption tax|tax)"
_TAIL = (r"(?:\s?(?:\+\s?" + _TAX + r"|(?:plus|excl(?:uding)?|exc|ex|inc(?:l(?:uding)?)?)\.?\s" + _TAX
         + r"|per\s(?:day|month|hour|week|year|annum|session|person)|a\s(?:day|month|week|year)|/\s?(?:day|month|mo|hr|hour|wk|week|yr|year)"
         + r"|pcm|p/m|pm|pa|monthly|yearly)){0,2}")
MONEY_RE = re.compile(
    r"(?:(?<![\w])(?:[A-Z]{1,3})?\$\s?(?:" + _NUM + r")" + _MULT + _TAIL
    + r"|[" + CUR_SYM + r"]\s?(?:" + _NUM + r")" + _MULT + _TAIL
    + r"|\b(?:" + CUR_CODES + r"|RM|Rs\.?|Rp\.?|kr|z\u0142|Fr\.?)\s?(?:" + _NUM + r")" + _MULT + _TAIL
    + r"|\b(?:" + _NUM + r")" + _MULT + r"\s?(?:[" + CUR_SYM + r"]|" + CUR_CODES
    + r"|pounds|dollars|euros|rupees|ringgit|yen|yuan|pesos|rand|francs|kronor|kroner|zloty)" + _TAIL + r")")
FEE_EXTRA_RE = re.compile(r"\b(?:" + _NUM + r")" + _MULT + r"\s?(?:\+\s?|(?:plus|excl(?:uding)?|exc|ex)\.?\s)" + _TAX + r"\b", re.I)

PHONE_RE = re.compile(r"(?<![\w" + CUR_SYM + r"$])(?:\+\d{1,3}[ \t.-]?(?:\(0\)[ \t]?)?)?(?:\(?\d{2,5}\)?[ \t.-]?){2,5}\d{2,4}(?![\w%])")
# A number labelled as a phone is removed even when it is short (8 digits in Singapore or Hong Kong).
PHONE_LABEL_RE = re.compile(r"(?i:\b(?:tel|phone|mobile|mob|cell|whatsapp|call|text|hp|h/p|ph)\b\.?(?:\s*(?:me|us|her|him|them)\s+on)?[:\s]*)"
                            r"(\+?\(?\d[\d \t().-]{6,18}\d)")

# Postal codes, by the shapes that cannot be mistaken for prices or years. A street address line is
# caught by ADDRESS_RES; anything these miss, Claude passes to redact.py with --address.
POSTCODE_RES = [
    re.compile(r"\b[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\b"),                                        # United Kingdom
    re.compile(r"\b(?:A[LKZR]|C[AOT]|D[EC]|FL|GA|HI|I[ADLN]|K[SY]|LA|M[ADEINOST]|N[CDEHJMVY]|O[HKR]|PA|PR|RI|S[CD]|"
               r"T[NX]|UT|V[AIT]|W[AIVY])\s+\d{5}(?:-\d{4})?\b"),                                 # United States: state and ZIP
    re.compile(r"\b[ABCEGHJ-NPRSTVXY]\d[ABCEGHJ-NPRSTV-Z]\s?\d[ABCEGHJ-NPRSTV-Z]\d\b"),         # Canada
    re.compile(r"\b(?:NSW|VIC|QLD|SA|WA|TAS|ACT|NT)\s+\d{4}\b"),                                 # Australia
    re.compile(r"\b(?:Singapore|S)\s?\(?\d{6}\)?(?!\d)"),                                       # Singapore
    re.compile(r"(?:\u3012\s?)\d{3}-\d{4}\b"),                                                   # Japan, with the postal mark
    re.compile(r"\b\d{5}\s+(?=(?:Kuala Lumpur|Petaling Jaya|Shah Alam|Johor Bahru|George Town|Penang|Ipoh|Kota Kinabalu|"
               r"Kuching|Cyberjaya|Putrajaya|Seremban|Melaka|Subang Jaya)\b)"),                   # Malaysia, before the city
    re.compile(r"(?i:\b(?:pin(?:\s?code)?|postcode|post code|postal code|zip(?:\s?code)?|eircode|plz)\b[:\s]*)[A-Z0-9][A-Z0-9 -]{2,9}[A-Z0-9]\b"),
]
_STREET = (r"Road|Rd|Street|St|Grove|Lane|Ln|Avenue|Ave|Close|Drive|Dr|Way|Place|Pl|Crescent|Terrace|Gardens|Court|Ct|Mews|Row|Hill|"
           r"Park|Square|Sq|Walk|View|Rise|Green|Parade|Yard|Boulevard|Blvd|Highway|Hwy|Parkway|Pkwy|Circle|Cir|Trail|Plaza|Quay|"
           r"Wharf|Esplanade|Broadway|Turnpike|Pike|Expressway|Marg|Nagar|Chowk")
_CAPW = r"[A-Z\u00c0-\u00de][^\W\d_]+"
_TOWN = r"[A-Z\u00c0-\u00de][a-z\u00df-\u00ff][^\W\d_]*"  # a town name, never a postcode such as HG1
ADDRESS_RES = [
    # 22 Mill Lane, Otley; 1100 Congress Ave, Suite 400; 1 Raffles Place
    re.compile(r"(?:\b(?:Level|Lvl|Floor|Fl|Suite|Unit)\.?[ \t]?\d{1,3}[A-Za-z]?,?[ \t]+)?"  # Level 2, 88 Harris St
               r"\b\d{1,5}[A-Za-z]?,?[ \t]+(?:" + _CAPW + r"[ \t]+){1,3}(?:" + _STREET + r")\b\.?"
               r"(?:[ \t]+(?:N|S|E|W|NE|NW|SE|SW)\b\.?)?"  # 228 Park Ave S
               r"(?:,?[ \t]+(?:Suite|Ste|Unit|Floor|Fl|Level|Lvl|Apt|#)\.?[ \t]*[\w-]+)?(?:,?[ \t]+" + _TOWN + r"(?:[ \t]+" + _TOWN + r")?)?"),
    # No. 8, Jalan Ampang; Blk 123 Ang Mo Kio Ave 3; Jalan Sultan 12
    re.compile(r"(?:\b(?:No\.?|Lot|Blk|Block)\s?\d+[A-Z]?,?\s+)?\b(?:Jalan|Jln|Lorong|Lrg|Persiaran|Lebuh|Lebuhraya|Jl\.?)\s+(?:" + _CAPW + r"\s?){1,4}(?:\d+[A-Z]?)?"),
    re.compile(r"\b(?:Blk|Block)\s?\d+[A-Z]?\s+(?:" + _CAPW + r"\s){1,4}(?:Ave(?:nue)?|St(?:reet)?|Rd|Road|Drive|Dr|Crescent)\s?\d*"),
    # Hauptstrasse 5; Kerkstraat 12; Rue de Rivoli 12; 12 rue de Rivoli; Calle Mayor 5; Via Roma 10
    re.compile(r"\b" + _CAPW + r"(?:stra\u00dfe|strasse|str\.|weg|allee|platz|gasse|ring|damm|straat|laan|gracht|plein|v\u00e4gen|gatan|gade|vej)\s+\d+[a-z]?\b"),
    re.compile(r"\b(?:\d{1,4},?\s+)?(?:[Rr]ue|[Aa]venue|[Bb]oulevard|[Cc]alle|[Aa]venida|[Aa]v\.|[Vv]ia|[Vv]iale|[Pp]iazza|[Rr]ua|[Tt]ravessa|[Cc]hemin|[Pp]aseo|[Cc]arrer)"
               r"\s+(?:(?:de|del|de la|des|du|da|do|dos|das|di|della)\s+)?(?:" + _CAPW + r"\s?){1,3}(?:,?\s?\d{1,4}[a-z]?)?"),
    # Unit numbers: #20-01 (Singapore), 1-2-3 Shibuya (Japan)
    re.compile(r"#\d{1,3}-\d{1,5}\b"),
    re.compile(r"\b\d{1,2}-\d{1,2}-\d{1,3},?\s+" + _CAPW + r"(?:-ku|-shi|-cho)?\b"),
]
ADDRESS_RE = ADDRESS_RES[0]  # kept for older callers

# Bank and registration numbers: labelled forms in any country, and a bare IBAN.
_ID_LABELS = (r"sort\s?code|bsb|routing(?:\s(?:number|no\.?))?|aba|account(?:\s(?:number|no\.?|#))?|a/c(?:\sno\.?)?|acct(?:\sno\.?)?|iban|swift|bic|ifsc|"
              r"transit(?:\snumber)?|bank\scode|branch\scode|clabe|ein|tin|itin|ssn|abn|acn|nzbn|uen|crn|brn|ssm|pan|gstin|cin|"
              r"(?:vat|gst|hst|tax|company|business|registration|reg\.?)\s?(?:reg(?:istration)?\.?\s?)?(?:no\.?|number|id|#)|"
              r"steuernummer|ust-?idnr\.?|siret|siren|kvk|cif|nif|rfc|cnpj|cpf")
_IDTOK = r"[A-Za-z0-9]*\d(?:[A-Za-z0-9./-]*[A-Za-z0-9])?"  # one group of an account or registration number: holds a digit
BANK_RES = [
    re.compile(r"(?i:\b(?:" + _ID_LABELS + r")\b)[\s.:#-]*" + _IDTOK + r"(?: " + _IDTOK + r"){0,7}"),
    re.compile(r"\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]{4}){2,7}(?:\s?[A-Z0-9]{1,4})?\b"),                 # IBAN, any country
]
BANK_RE = BANK_RES[1]  # kept for older callers


def phone_hits(text):
    hits = []
    for m in PHONE_LABEL_RE.finditer(text):
        digits = re.sub(r"\D", "", m.group(1))
        if 7 <= len(digits) <= 15:
            hits.append(m.group(1).strip())
    for m in PHONE_RE.finditer(text):
        s = m.group(0).strip()
        digits = re.sub(r"\D", "", s)
        if 10 <= len(digits) <= 15 and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
            hits.append(s)
    return hits


def postcode_hits(text):
    return [m.group(0) for r in POSTCODE_RES for m in r.finditer(text)]


def address_hits(text):
    return [m.group(0) for r in ADDRESS_RES for m in r.finditer(text)]


def bank_hits(text):
    return [m.group(0) for r in BANK_RES for m in r.finditer(text)]


def personal_data_hits(text):
    """Patterns that must never reach a report or a memory file: emails, phone numbers, postal codes,
    street addresses, bank and registration numbers. Money is checked separately, against the public assets."""
    out = []
    out += [("email address", x) for x in EMAIL_RE.findall(text)]
    out += [("phone number", x) for x in phone_hits(text)]
    out += [("postal code", x) for x in postcode_hits(text)]
    out += [("street address", x) for x in address_hits(text)]
    out += [("bank or registration number", x) for x in bank_hits(text)]
    return out


# ---------------------------------------------------------------- locale
# Formatting only: which paper the founder's printer holds, how they write a date, which English they spell.
# Nothing here is a rule, a rate or a law. The founder's own answer always wins over the country default.
# Paper, date order and clock come from locale_numbers.locale_defaults(country), never from spelling.
LANG_TAGS = {"american": "en-US", "british": "en-GB"}
# Fallback only, when the founder's own spelling does not settle it. Canada and countries where English is not
# the first business language stay unknown, so spelling is left as the founder writes it.
AMERICAN_SPELLING = {"US", "PH", "PR", "LR"}
COMMONWEALTH_SPELLING = {"GB", "IE", "AU", "NZ", "ZA", "IN", "SG", "MY", "HK", "PK", "BD", "LK", "NG", "KE", "GH", "UG",
                         "TZ", "ZM", "ZW", "MT", "CY", "JM", "TT", "BB", "BW", "NA", "MU", "FJ"}


def resolve_locale(loc):
    """Fill paper and date style from the country where the founder did not say. Unknown stays unknown:
    the page then prints on the viewer's own default paper and dates are written 2026-10-20."""
    loc = dict(loc or {})
    cc = str(loc.get("country") or "").strip().upper()[:2] or None
    loc["country"] = cc
    d = LN.locale_defaults(cc) if cc else None
    paper = str(loc.get("paper") or "").strip().lower()
    loc["paper"] = paper if paper in ("a4", "letter") else (d["paper"].lower() if d else None)
    dates = str(loc.get("dates") or "").strip().lower()
    loc["dates"] = dates if dates in ("dmy", "mdy", "ymd") else (d["date_order"].lower() if d else "ymd")
    loc["clock"] = d["clock"] if d else None  # the report prints no times; kept so the memory has it
    eng = str(loc.get("english") or "").strip().lower()
    eng = {"commonwealth": "british", "us": "american"}.get(eng, eng)
    loc["english"] = eng if eng in ("american", "british") else (
        "american" if cc in AMERICAN_SPELLING else "british" if cc in COMMONWEALTH_SPELLING else None)
    dec = str(loc.get("decimal") or "").strip().lower()
    loc["decimal"] = dec if dec in ("dot", "comma") else None
    return loc


def english_label(english, country=None):
    """How the founder's English is named back to them: never 'british' to an Australian."""
    if english == "american":
        return "American spelling" + (f" (en-{country})" if country else "")
    if english == "british":
        if country in (None, "GB"):
            return "British spelling (en-GB)"
        return f"Commonwealth spelling (en-{country})"
    return "not known"


def english_from_label(v):
    v = (v or "").strip().lower()
    if v.startswith("american"):
        return "american"
    if v.startswith(("british", "commonwealth")):
        return "british"
    return None


SELLS_WORDS = {"me": "me", "me_and_others": "me and others", "team": "a team"}


def sells_from_words(v):
    v = (v or "").strip().lower().replace("_", " ")
    for k, w in SELLS_WORDS.items():
        if v == w or v == k.replace("_", " ") or (k == "team" and v == "team"):
            return k
    return "me"


def lang_tag(loc):
    eng, cc = loc.get("english"), loc.get("country")
    if eng == "american" and cc in (None, "US"):
        return "en-US"
    if eng == "british" and cc in (None, "GB"):
        return "en-GB"
    if cc and re.fullmatch(r"[A-Z]{2}", cc):
        return f"en-{cc}"
    return LANG_TAGS.get(eng, "en")


def fmt_date(iso, style="ymd"):
    """A date the way the founder writes it: 20 October 2026, October 20, 2026, or 2026-10-20."""
    from datetime import date as _d
    try:
        d = _d.fromisoformat(str(iso)[:10])
    except ValueError:
        return str(iso)
    if style == "dmy":
        return f"{d.day} {d.strftime('%B %Y')}"
    if style == "mdy":
        return f"{d.strftime('%B')} {d.day}, {d.year}"
    return d.isoformat()


# Spelling pairs (British or Commonwealth form, American form). Counted in the founder's assets to tell which
# English they write, and checked in what Claude writes so the edits read in the founder's own spelling.
SPELLING_PAIRS = [
    ("colour", "color"), ("colours", "colors"), ("favour", "favor"), ("favourite", "favorite"), ("behaviour", "behavior"),
    ("labour", "labor"), ("honour", "honor"), ("neighbour", "neighbor"), ("rumour", "rumor"), ("humour", "humor"),
    ("centre", "center"), ("centres", "centers"), ("metre", "meter"), ("theatre", "theater"), ("fibre", "fiber"),
    ("analyse", "analyze"), ("analysed", "analyzed"), ("catalogue", "catalog"), ("defence", "defense"), ("offence", "offense"),
    ("travelled", "traveled"), ("travelling", "traveling"), ("cancelled", "canceled"), ("modelling", "modeling"),
    ("labelled", "labeled"), ("fulfil", "fulfill"), ("enrol", "enroll"), ("jewellery", "jewelry"), ("grey", "gray"),
    ("cheque", "check"), ("mum", "mom"), ("ageing", "aging"), ("programme", "program"),
    ("organise", "organize"), ("organised", "organized"), ("organisation", "organization"), ("organisations", "organizations"),
    ("optimise", "optimize"), ("optimised", "optimized"), ("optimisation", "optimization"), ("optimising", "optimizing"),
    ("prioritise", "prioritize"), ("realise", "realize"), ("recognise", "recognize"), ("specialise", "specialize"),
    ("specialised", "specialized"), ("specialising", "specializing"), ("customise", "customize"), ("customised", "customized"),
    ("apologise", "apologize"), ("minimise", "minimize"), ("maximise", "maximize"), ("standardise", "standardize"),
    ("personalise", "personalize"), ("personalised", "personalized"), ("summarise", "summarize"), ("emphasise", "emphasize"),
    ("utilise", "utilize"), ("finalise", "finalize"), ("visualise", "visualize"), ("criticise", "criticize"),
    ("sceptic", "skeptic"), ("sceptics", "skeptics"), ("sceptical", "skeptical"),
]
_BRIT = {b for b, _a in SPELLING_PAIRS}
_AMER = {a for _b, a in SPELLING_PAIRS if a not in ("check", "program", "meter")}  # also ordinary words in both
_AMER_TO_BRIT = {a: b for b, a in SPELLING_PAIRS}
_BRIT_TO_AMER = {b: a for b, a in SPELLING_PAIRS}


def spelling_markers(text):
    ws = [w.lower() for w in words(text)]
    return {"british": sum(1 for w in ws if w in _BRIT), "american": sum(1 for w in ws if w in _AMER)}


def english_of(counts):
    """Which English the founder writes, from spelling markers across their assets: two or more markers,
    and at least three to one in one direction. Otherwise None (ask, or leave spelling unchecked)."""
    b, a = counts.get("british", 0), counts.get("american", 0)
    if b + a < 2:
        return None
    if b >= 3 * max(a, 1) or (a == 0 and b >= 2):
        return "british"
    if a >= 3 * max(b, 1) or (b == 0 and a >= 2):
        return "american"
    return None


def wrong_spellings(text, english):
    """Words in Claude's copy spelt the other way from the founder's English, with the form to use."""
    out = []
    for w in words(text):
        lw = w.lower()
        if english == "american" and lw in _BRIT_TO_AMER and lw not in ("programme",):
            out.append((w, _BRIT_TO_AMER[lw]))
        elif english == "american" and lw == "programme":
            out.append((w, "program"))
        elif english == "british" and lw in _AMER and lw in _AMER_TO_BRIT:
            out.append((w, _AMER_TO_BRIT[lw]))
    return out


# Places and currencies Claude might write into a line out of habit. A line that names one the founder's
# own assets never mention assumes a country the founder did not give.
PLACE_WORDS = [r"\bUK\b", r"\bU\.K\.", r"\bUnited Kingdom\b", r"\bBritain\b", r"\bBritish\b", r"\bEngland\b", r"\bUS\b", r"\bU\.S\.",
               r"\bUSA\b", r"\bAmerica\b", r"\bAmerican\b", r"\bUnited States\b", r"\bEU\b", r"\bEurope(?:an)?\b",
               r"\bAustralia(?:n)?\b", r"\bNew Zealand\b", r"\bCanad(?:a|ian)\b", r"\bSingapore(?:an)?\b", r"\bMalaysia(?:n)?\b",
               r"\bIndia(?:n)?\b", r"\bIreland\b", r"\bIrish\b", r"\bHong Kong\b", r"\bDubai\b", r"\bUAE\b",
               r"\bnationwide\b", r"\bnationally\b", r"\bsterling\b", r"\bpounds?\b", r"\bdollars?\b", r"\beuros?\b",
               r"\brupees?\b", r"\bringgit\b"]


def assumed_places(text, sources):
    src = " ".join(sources)
    out = []
    for p in PLACE_WORDS:
        m = re.search(p, text)
        if m and not re.search(p, src, re.I if p.islower() else 0):
            out.append(m.group(0))
    syms = set(re.findall(r"[" + CUR_SYM + r"$]", text)) - set(re.findall(r"[" + CUR_SYM + r"$]", src))
    return out + sorted(syms)


# Figures. Every number is read through locale_numbers with the founder's decimal style, so "9.800" from a
# founder who writes decimal commas is 9800, and "9,800" from one who writes decimal points is 9800 too.
NUM_RE = re.compile(r"(?<![\w.,])(\d{1,3}(?:[,.  ' ]\d{3})+(?:[.,]\d{1,2})?|\d+(?:[.,]\d+)?)"
                    r"(\s?(?:%|per ?cent|x\b|times\b|k\b|m\b)?)", re.I)
NUM_WORDS = {"double": "x2", "doubled": "x2", "doubles": "x2", "triple": "x3", "tripled": "x3", "triples": "x3",
             "quadruple": "x4", "tenfold": "x10", "half": "1/2", "halve": "1/2", "halved": "1/2"}
# Number words a founder writes ("nine years", "a team of four", "dropped by a third"). Read on the founder's side
# only, so a bio may say "9 yrs" where the website says "nine years"; Claude's own number words are not figures.
_UNITS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
          "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
          "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
          "seventy": 70, "eighty": 80, "ninety": 90, "a hundred": 100, "one hundred": 100, "a dozen": 12, "dozen": 12}
_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
_FRACTION_WORDS = {"a third": "1/3", "one third": "1/3", "a quarter": "1/4", "one quarter": "1/4", "half": "1/2",
                   "a half": "1/2", "two thirds": "2/3", "three quarters": "3/4"}
WORDNUM_RE = re.compile(r"\b(?:(" + "|".join(_TENS) + r")[- ](one|two|three|four|five|six|seven|eight|nine)|("
                        + "|".join(sorted(_UNITS, key=len, reverse=True)) + r"))\b", re.I)


def word_numbers(text):
    """Values of the number words in text: 'nine' 9, 'twenty-five' 25, 'a third' 1/3."""
    out = set()
    low = norm_text(text)
    for m in WORDNUM_RE.finditer(low):
        if m.group(1):
            out.add(f"{_TENS[m.group(1).lower()] + _UNITS[m.group(2).lower()]:g}")
        else:
            out.add(f"{_UNITS[m.group(3).lower()]:g}")
    for w, f in _FRACTION_WORDS.items():
        if re.search(r"\b" + w + r"\b", low):
            out.add(f)
    return out


def detect_decimal(texts):
    """The founder's decimal style ('dot', 'comma' or None) from everything they pasted, read once."""
    return LN.detect_decimal_style([t for t in texts if t])


def ambiguous_numbers(texts, decimal=None):
    """Numbers locale_numbers cannot read without knowing the founder's decimal style ('12.500', '4,500' ...)."""
    out = []
    for t in texts:
        for m in NUM_RE.finditer(norm_text(t)):
            try:
                LN.parse_number(m.group(1), decimal, allow_words=False)
            except LN.Ambiguous:
                out.append(m.group(1))
            except LN.Unreadable:
                pass
    return sorted(set(out))


def _value(raw, decimal):
    """One figure's value as text ('9800', '1.5'), or its raw form when it cannot be read with confidence."""
    try:
        v, _n = LN.parse_number(raw, decimal, allow_words=False)
        return f"{v:g}"
    except (LN.Ambiguous, LN.Unreadable):
        return raw


def figure_tokens(text, decimal=None):
    """[(value with unit, raw form)] for the digits in text, placeholders such as [fee] left out."""
    t = norm_text(text)
    t = re.sub(r"\[[a-z ]+\]", " ", t)
    out = []
    for m in NUM_RE.finditer(t):
        unit = m.group(2).strip().replace(" ", "").replace("percent", "%").replace("times", "x")
        out.append((_value(m.group(1), decimal) + unit, m.group(1)))
    return out


def figures(text, decimal=None, words_too=False):
    """The figures a sentence asserts: numbers (with %, x, k) and multiplier words. Used to
    refuse any core line or edit that claims a figure the founder's assets never state.
    words_too reads number words as figures too; it is used on the founder's own assets only."""
    out = {v for v, _raw in figure_tokens(text, decimal)}
    for w in words(norm_text(text)):
        if w.lower() in NUM_WORDS:
            out.add(NUM_WORDS[w.lower()])
    if words_too:
        out |= word_numbers(text)
    return out


def figures_supported(text, sources, decimal=None):
    """Figures in text that do not appear anywhere in the sources (bare numbers match with or without a unit;
    a digit matches the founder's number word: '9' is supported by 'nine')."""
    have = set()
    bare = set()
    for s in sources:
        for f in figures(s, decimal, words_too=True):
            have.add(f)
            bare.add(re.sub(r"[^\d./]", "", f))
    missing = []
    for f in figures(text, decimal):
        if f in have:
            continue
        b = re.sub(r"[^\d./]", "", f)
        if b and b in bare:
            continue
        missing.append(f)
    return sorted(missing)


def figure_style_problems(text, sources, decimal=None):
    """Figures Claude wrote with different separators from the founder's own way of writing the same value:
    '4,500' to a founder who writes '4.500'. Returns [(as written, the founder's form)]."""
    forms = {}
    for s in sources:
        for v, raw in figure_tokens(s, decimal):
            forms.setdefault(re.sub(r"[^\d./]", "", v), set()).add(raw)
    out = []
    for v, raw in figure_tokens(text, decimal):
        if not re.search(r"[,.'   ]", raw):
            continue
        theirs = forms.get(re.sub(r"[^\d./]", "", v)) or set()
        grouped = [x for x in theirs if re.search(r"[,.'   ]", x)]
        if grouped and raw not in theirs:
            out.append((raw, sorted(grouped)[0]))
    return out


# ---------------------------------------------------------------- facts that disagree
# A number attached to the same thing in two assets ("a team of four" against "a team of six"). The script only
# suggests; Claude confirms each one into the extraction's "facts" list, which the report shows first.
FACT_NOUNS = {"team": "team size", "people": "team size", "staff": "team size", "employees": "team size",
              "coaches": "team size", "consultants": "team size", "designers": "team size", "specialists": "team size",
              "experts": "team size", "advisers": "team size", "advisors": "team size", "partners": "team size",
              "years": "years", "yrs": "years", "clients": "clients", "customers": "clients", "brands": "brands",
              "projects": "projects", "offices": "offices", "outlets": "outlets", "locations": "locations",
              "countries": "countries", "cities": "cities"}
_WORDNUM_ALT = (r"(?:(?:" + "|".join(_TENS) + r")[- ](?:one|two|three|four|five|six|seven|eight|nine)|(?:"
                + "|".join(sorted(_UNITS, key=len, reverse=True)) + r"))")
_NUMTOK = r"(\d{1,3}(?:[,.]\d{3})+|\d+(?:[.,]\d+)?\+?|" + _WORDNUM_ALT + r")"
FACT_RES = [
    re.compile(r"\bteam of " + _NUMTOK, re.I),
    re.compile(_NUMTOK + r"(?:[- ](?:[a-z]+))?[ -](" + "|".join(FACT_NOUNS) + r")\b", re.I),
]
FACT_LIMITS = {"team size": 100000, "years": 100, "clients": 10000000, "brands": 1000000, "projects": 10000000}


def _fact_value(raw, decimal):
    raw = raw.strip().rstrip("+")
    vals = word_numbers(raw)
    if vals and not re.search(r"\d", raw):
        return float(sorted(vals)[0]) if "/" not in sorted(vals)[0] else None
    try:
        return LN.parse_number(raw, decimal, allow_words=False)[0]
    except (LN.Ambiguous, LN.Unreadable):
        return None


def fact_mentions(text, decimal=None):
    """[(what, value, the words around it)] for numbers attached to a team, years, clients and the like."""
    t = unicodedata.normalize("NFKC", text or "")
    t = re.sub(r"(\w)-\n(\w)", r"\1\2", t).replace("\n", " ")
    out = []
    for i, r in enumerate(FACT_RES):
        for m in r.finditer(t):
            if i == 0:
                what, raw = "team size", m.group(1)
            else:
                raw = m.group(1)
                what = FACT_NOUNS[m.group(m.lastindex).lower()]
            val = _fact_value(raw, decimal)
            if val is None:
                continue
            start = max(0, m.start() - 20)
            out.append((what, val, t[start:m.end()].strip()))
    seen, uniq = set(), []
    for f in out:
        k = (f[0], f[1])
        if k not in seen:
            seen.add(k)
            uniq.append(f)
    return uniq


def fact_candidates(texts, labels, decimal=None):
    """Pairs of assets that attach different numbers to the same thing. texts: {asset id: clean text}."""
    found = {aid: fact_mentions(t, decimal) for aid, t in texts.items()}
    out = []
    ids = list(texts)
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = ids[i], ids[j]
            for wa, va, ca in found[a]:
                for wb, vb, cb in found[b]:
                    if wa == wb and va != vb and wa == "team size":
                        out.append({"what": wa, "a": a, "b": b, "a_words": ca, "b_words": cb,
                                    "a_label": labels.get(a, a), "b_label": labels.get(b, b)})
    return out


def implausible_facts(texts, decimal=None):
    """Numbers attached to a team, years or clients that cannot be right (a team of 0, 150 years)."""
    out = []
    for aid, t in texts.items():
        for what, val, words_ in fact_mentions(t, decimal):
            lim = FACT_LIMITS.get(what)
            if val <= 0 or (lim and val > lim):
                out.append((aid, words_))
    return out


# ---------------------------------------------------------------- platform limits
# Character limits for the short assets whose whole text has to fit one field. Counted in code after every edit.
PLATFORM_LIMITS = {"instagram": ("Instagram bio", 150), "tiktok": ("TikTok bio", 80), "x": ("X bio", 160),
                   "twitter": ("X bio", 160), "threads": ("Threads bio", 150), "linkedin_headline": ("LinkedIn headline", 220)}


def platform_of(asset):
    """The platform whose bio limit applies to an asset, from its 'platform' field or its label."""
    p = str(asset.get("platform") or "").strip().lower().replace(" ", "_")
    if p in PLATFORM_LIMITS:
        return p
    if asset.get("kind") not in ("bio", "social"):
        return None
    lab = (asset.get("label") or "").lower()
    for key in ("instagram", "tiktok", "threads", "twitter"):
        if key in lab:
            return key
    if re.search(r"\bx\b", lab):
        return "x"
    return None


def apply_edits(text, edits):
    """The asset's text after the edits: each 'current' line replaced, each added line put after 'after'."""
    out = text
    # added lines first, anchored on the text as it stands, then the replacements
    for e in sorted(edits, key=lambda x: 0 if not x.get("current") else 1):
        prop = (e.get("proposed") or "").strip()
        if e.get("current"):
            pat = r"\s+".join(re.escape(w) for w in (e["current"] or "").split())
            out, n = re.subn(pat, lambda _m: prop, out, count=1, flags=re.I)
        elif e.get("after"):
            pat = r"\s+".join(re.escape(w) for w in (e["after"] or "").split())
            m = re.search(pat, out, re.I)
            if m:
                eol = out.find("\n", m.end())
                eol = len(out) if eol < 0 else eol
                out = out[:eol] + "\n" + prop + out[eol:]
            else:
                out = out.rstrip("\n") + "\n" + prop
        else:
            out = out.rstrip("\n") + "\n" + prop
    return out


# ---------------------------------------------------------------- skips and line wraps

def skip_map(ext):
    """skip: {"prop": ["who"]} or {"prop": {"questions": ["who", "what"], "reason": "aimed at ops buyers"}}.
    Returns ({asset: [questions]}, {asset: reason})."""
    qs, why = {}, {}
    for aid, v in (ext.get("skip") or {}).items():
        if isinstance(v, dict):
            qs[aid] = [q for q in (v.get("questions") or []) if q in QKEYS]
            if v.get("reason"):
                why[aid] = str(v["reason"])
        else:
            qs[aid] = [q for q in (v or []) if q in QKEYS]
    return qs, why


def unwrap(text):
    """Join the hard line breaks a PDF puts inside a paragraph ('peo-\\nple', a sentence carried to the next line).
    Used for measuring and matching only; the clean copy and every quote keep the founder's text."""
    t = (text or "").replace("\r", "")
    t = re.sub(r"(\w)-\n(\w)", r"\1\2", t)
    lines = t.split("\n")
    out = []
    for ln in lines:
        prev = out[-1] if out else None
        joinable = (prev is not None and len(prev.strip()) >= 40 and not re.search(r"[.!?:;]\s*$", prev)
                    and ln.strip() and not re.match(r"\s*[-*•·]", ln)
                    and (re.match(r"\s*[a-z0-9(]", ln) or re.search(r",\s*$", prev)))
        if joinable:
            out[-1] = prev.rstrip() + " " + ln.strip()
        else:
            out.append(ln)
    return "\n".join(out)


# ---------------------------------------------------------------- credentials
CREDENTIAL_RE = re.compile(r"\b([A-Z][A-Za-z0-9&]{1,9}(?:[ -][0-9A-Z]{1,6})?)[ -](?:certified|accredited|registered|chartered)\b")


def unstated_credentials(text, sources):
    """Credentials in Claude's copy ('ISO certified') whose name no asset mentions: an added claim."""
    src = " ".join(sources)
    return [m.group(0) for m in CREDENTIAL_RE.finditer(text or "") if not re.search(r"\b" + re.escape(m.group(1)) + r"\b", src)]


def slug(s):
    s = re.sub(r"[^a-z0-9]+", "-", (s or "business").lower()).strip("-")
    return s[:40] or "business"
