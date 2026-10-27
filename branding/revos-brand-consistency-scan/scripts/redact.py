#!/usr/bin/env python3
"""Remove client personal data from the founder's pasted assets before anything is read for the scan.

Usage:
  python3 scripts/redact.py <assets.json> --out <clean folder> [--client "Company"]... [--person "Full Name"]... [--keep "Name"]...
                            [--address "text"]... [--delete-raw]

assets.json (written by Claude from what the founder pasted):
  {"business": "Northlight Studio", "founder": "Ana Ruiz",
   "assets": [{"id": "web", "kind": "website", "label": "Website home and about", "file": "raw/web.txt"}, ...]}

What it removes, everywhere: email addresses, phone numbers, postal codes, street addresses, bank
and registration numbers, every company given with --client, every person given with --person (and each of their names alone,
so "Nurul, as discussed" goes too), every text given with --address, and names
it finds itself: after a greeting (Dear, Hi, Kia ora, Salam ...) with or without a title (Mr, Dr,
Datuk, Herr ...), after Prepared for, Client:, Attn:, on a testimonial dash line, and companies by
their legal form in any country (Ltd, Inc, LLC, Corp, Pte Ltd, Pty Ltd, Sdn Bhd, GmbH, SA, BV, KK,
PT ...). Names in any script and with particles (van der, bin, binti, de la, a/l) are handled. In
client-facing assets (proposal, deck, onboarding, invoice, client email) it also removes fees in any
currency. The founder's own name and business, and anything passed with --keep, are never removed.

It writes <out>/<id>.txt for each asset, <out>/assets.json pointing at the clean copies, and
<out>/redaction.json holding counts (distinct client names and mentions), the founder's decimal style
and one-way fingerprints of the removed names, never the names themselves, so later checks can prove
no name reached the report or the memory file. A company's first word alone ("Acme's team") goes too,
and the company on a testimonial line ("- Dan Ode, VP Sales, Brightline Freight"). The founder's own
contact details (a line with their business name or an email at their domain) are removed but counted
as their own, never as client data. It prints counts only, and an ASK line when a number in the
copy reads two ways. It stops (exit 2, nothing written) if cleaning would take out over half an asset. Exit 0 written; exit 2 with one STOP line if the input cannot be used.
Standard library only. No network.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scan_common as C  # noqa: E402

PLACE = {"address": "[address]", "client": "[client]", "email": "[email]", "phone": "[phone]", "postcode": "[postal code]",
         "fee": "[fee]", "bank": "[bank details]"}
LABELS = {"address": ("street address", "street addresses"), "client": ("client name", "client names"), "email": ("email address", "email addresses"),
          "phone": ("phone number", "phone numbers"), "postcode": ("postal code", "postal codes"),
          "fee": ("fee", "fees"), "bank": ("bank or registration number", "bank or registration numbers")}

# Upper-case letters in every cased script (Latin with accents, Vietnamese, Greek, Cyrillic), built once.
UP = "".join(ch for ch in map(chr, range(0x41, 0x2000)) if ch.isupper()).replace("\\", "").replace("]", "").replace("^", "").replace("-", "")
UP = re.escape(UP)
CJK = C.CJK
# Scripts without capitals (Arabic, Hebrew, Devanagari, Thai, Chinese, Japanese, Korean) start a name with any letter.
UNCASED = "\u0590-\u05ff\u0600-\u06ff\u0750-\u077f\u0900-\u0dff\u0e00-\u0e7f" + CJK
TOKEN = rf"(?:[{UP}][^\W\d_]*|[{UNCASED}][^\W\d_]*)(?:['\u2019\-][^\W\d_]+)*\.?"
PARTICLE = (r"(?:van|von|der|den|de|del|della|degli|di|da|dos|das|do|du|la|le|zu|ter|te|ten|op|bin|binti|binte|bte|bt|ibn|"
            r"bint|ben|ap|y|e|al|el|a/l|a/p|s/o|d/o)")
NAME = rf"(?:(?:al|el|ad|ar|as|at|an|ash|ad-)?-?{TOKEN}(?:[ \t]+(?:{PARTICLE}[ \t]+)*{TOKEN}){{0,4}})"
TITLES = (r"(?:Mr|Mrs|Ms|Miss|Mx|Dr|Prof|Professor|Sir|Dame|Lord|Lady|Rev|Datuk|Dato['\u2019]?|Datin|Tan Sri|Puan Sri|Tun|"
          r"Puan|Encik|Cik|Tuan|Haji|Hajah|Hj|Shri|Sri|Smt|Kumari|Herr|Frau|Monsieur|Madame|Mme|Mlle|M|Se\u00f1or|Se\u00f1ora|Sr|Sra|Srta|"
          r"Don|Do\u00f1a|Dona|Sig|Sig\.ra|Signor|Signora|Sheikh|Sayyid|Ustaz|Engr|Atty|Hon)\.?")
GREETINGS = (r"(?:Dear|Hi|Hello|Hey|Hiya|Morning|Afternoon|Evening|Good morning|Good afternoon|Good evening|Greetings|"
             r"Kia ora|G['\u2019]day|Salam|Assalamualaikum|Namaste|Hola|Bonjour|Hallo|Ciao|Ol\u00e1|Ola|Hej|Sawasdee|Selamat pagi|Selamat petang)")
SALUTE_RE = re.compile(rf"^[ \t]*{GREETINGS}[ \t]+((?:{TITLES}[ \t]+(?:(?:and|&)[ \t]+{TITLES}[ \t]+)?)?)([^,\n:;!.\u2014\u2013]{{1,70}})", re.M)
LABEL_RE = re.compile(rf"(?:(?:Prepared for|Proposal for|Prepared exclusively for|For the attention of|Bill to|Billed to|Invoice to|Quote for)"
                      rf"[ \t]*[:\-\u2013\u2014]?|(Client name|Client|Attention|Attn|Company|Contact|Customer|Account|To|Cc|CC|cc)[ \t]*:)[ \t]*"
                      rf"({TITLES}[ \t]+)?([^\n,;]{{2,80}})")
PERSON_LABELS = {"attention", "attn", "contact", "cc", "client name"}
# Legal forms of a company, after the name (Ltd, Inc, Pte. Ltd., Sdn Bhd, GmbH ...) or before it (PT, CV, OOO, \u682a\u5f0f\u4f1a\u793e).
FORMS = [
    r"Pte\.?\s?Ltd\.?", r"Pvt\.?\s?Ltd\.?", r"Private Limited", r"\(Pty\)\s?Ltd\.?", r"Pty\.?\s?Ltd\.?", r"Pty\.?", r"Sdn\.?\s?Bhd\.?",
    r"Bhd\.?", r"Berhad", r"Co\.?,?\s?Ltd\.?", r"Ltd\.?", r"Limited", r"LLP", r"L\.L\.P\.", r"LP", r"plc", r"PLC", r"Inc\.?", r"Incorporated",
    r"LLC", r"L\.L\.C\.", r"PLLC", r"P\.C\.", r"Corp\.?", r"Corporation", r"Co\.", r"Company", r"GmbH(?:\s&\sCo\.\sKG)?", r"AG", r"KG",
    r"UG", r"e\.V\.", r"S\.A\. de C\.V\.", r"SA de CV", r"S\.A\.S\.", r"SAS", r"S\.A\.", r"SA", r"SARL", r"S\.\u00e0 r\.l\.", r"S\.L\.", r"SL",
    r"S\.p\.A\.", r"SpA", r"S\.r\.l\.", r"Srl", r"B\.V\.", r"BV", r"N\.V\.", r"NV", r"AB", r"A/S", r"ASA", r"AS", r"ApS", r"Oyj", r"Oy",
    r"K\.K\.", r"KK", r"GK", r"Ltda\.?", r"Sp\. z o\.o\.", r"s\.r\.o\.", r"a\.s\.", r"d\.o\.o\.", r"Kft\.", r"Zrt\.", r"SE", r"ULC",
    r"CIC", r"FZE", r"FZ-LLC", r"FZCO", r"FZ LLC", r"WLL", r"W\.L\.L\.", r"DMCC", r"JSC", r"Tbk\.?", r"Holdings",
]
FORM = "(?:" + "|".join(FORMS) + ")"
ORGTOK = rf"(?:{TOKEN}|&|\+|and|of|the|for|und|et|y|e|dan|da|de|del|des|du|van|von|\d+)"
SUFFIX_RE = re.compile(rf"(?<![\w])((?:{TOKEN})(?:[ \t]+{ORGTOK}){{0,4}}?),?[ \t]+({FORM})(?![\w])")
PREFIX_RE = re.compile(rf"(?<![\w])(PT|CV|OOO|ZAO|PAO|OAO|Kabushiki Kaisha|\u682a\u5f0f\u4f1a\u793e)[ \t]+({TOKEN}(?:[ \t]+{TOKEN}){{0,3}})")
HONORIFIC_TAIL = re.compile(r"[-\s](?:san|sama|sensei|kun|chan|ssi|nim|ji)$|(?:\u3055\u3093|\u69d8|\u5148\u751f|\u6c0f)$", re.I)
TESTIMONIAL_RE = re.compile(rf"(?:[\"\u201d\u300d]\s*[\-\u2013\u2014~]+[ \t]*(?:{TITLES}[ \t]+)*({NAME})|"
                            rf"^[ \t]*[\-\u2013\u2014~]+[ \t]*(?:{TITLES}[ \t]+)*({NAME})[ \t]*(?:,|$))", re.M)
STOPWORDS = {"The", "This", "That", "Our", "Your", "We", "You", "All", "And", "For", "With", "Team", "Hi", "Dear",
             "Hello", "Thanks", "Thank", "Kind", "Best", "Regards", "Proposal", "Client", "Scope", "Fee", "Fees",
             "Project", "Phase", "Stage", "Week", "Month", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
             "January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
             "November", "December", "Ltd", "Limited", "Group", "Holdings", "Mr", "Mrs", "Ms", "Dr", "Miss",
             "Everyone", "There", "Founder", "Director", "Manager", "Head", "Lead", "CEO", "COO", "CFO", "CTO", "CMO", "Of",
             "Sir", "Madam", "Sir or Madam", "Friends", "Folks", "All", "Both", "Colleagues", "Partner", "Partners", "Owner",
             "Board", "Customer", "Customers", "Clients", "Members", "Hiring Manager", "Inc", "Corp", "LLC", "Company", "Co"}
LOWER_STOP = {w.lower() for w in STOPWORDS} | {"there", "all", "team", "everyone", "both", "again", "folks", "you", "y'all", "friend"}
# Words that mark a job title on a testimonial line, not a company.
TITLE_WORDS = {"vp", "svp", "evp", "director", "head", "manager", "founder", "co-founder", "cofounder", "ceo", "coo", "cfo", "cto",
               "cmo", "cpo", "owner", "partner", "lead", "chief", "president", "officer", "engineering", "operations", "ops",
               "marketing", "sales", "md", "gm", "principal", "consultant", "coach", "editor", "producer", "chair", "trustee",
               "of", "at", "and"}
# English words that are also two-letter surnames; never removed on their own.
SHORT_COMMON = {"an", "as", "at", "be", "by", "do", "go", "he", "if", "in", "is", "it", "me", "my", "no", "of", "on", "or",
                "so", "to", "up", "us", "we", "ok", "hi", "am", "ah", "oh", "ma", "pa", "id"}


def kept(term, keep):
    t = C.norm_text(term)
    return any(k and (k in t or t in k) for k in keep)


def _tidy(f):
    f = re.sub(r"\s+", " ", f or "").strip(" .,:;-\u2013\u2014\"'")
    toks = f.split()
    while toks and toks[-1].lower() in {"and", "of", "the", "&", "for", "y", "et", "und", "dan", "da", "de"}:
        toks.pop()
    return " ".join(toks)


def _name_ok(f, keep):
    if not f or f in STOPWORDS or kept(f, keep):
        return False
    first = f.split()[0]
    if first.lower() in LOWER_STOP:
        return False
    if not (re.match(rf"[{UP}{UNCASED}]", first) or re.match(r"(?:al|el|ad|ar|as|at|an|ash)-", first)):
        return False  # "Dear valued partner": not a name
    return len(f) >= 2


def person_parts(f, keep):
    """A person's full name also yields each given or family name alone ('Sarah, as discussed'); particles and
    titles are skipped, and two-letter names (Ng, Le, Wu) only when they are not also English words."""
    out = set()
    base = HONORIFIC_TAIL.sub("", f).strip()
    if base != f and _name_ok(base, keep):
        out.add(base)  # Tanaka-san gives Tanaka
    parts = [p.strip(".") for p in base.split() if not re.fullmatch(PARTICLE, p.lower()) and not re.fullmatch(TITLES, p)]
    if len(parts) >= 2:
        for p in parts:
            if p in STOPWORDS or kept(p, keep) or not re.match(rf"[{UP}{UNCASED}]", p):
                continue
            if len(p) >= 3 or re.search(f"[{CJK}]", p) or (len(p) == 2 and p.lower() not in SHORT_COMMON):
                out.add(p)
    return out


def candidate_names(text, client_facing, keep):
    people, orgs = set(), set()
    for m in SALUTE_RE.finditer(text):
        raw = m.group(2)
        for piece in re.split(r"\s+(?:and|&)\s+", raw):
            people.add(piece)
    for m in TESTIMONIAL_RE.finditer(text):
        people.add((m.group(1) or m.group(2)).rstrip("."))
        rest = text[m.end():].split("\n", 1)[0]
        fields = [x.strip(" .\t") for x in re.split(r"[,|/]", rest) if x.strip(" .\t")]
        if fields:  # "- Daniel Okafor, VP Engineering, Brightline Freight": the last field is the company
            last = fields[-1]
            toks = {t.lower().strip(".") for t in last.split()}
            if (len(fields) >= 2 or not toks & TITLE_WORDS) and not toks & TITLE_WORDS and re.match(rf"[{UP}{UNCASED}]", last):
                orgs.add(last)
    for m in SUFFIX_RE.finditer(text):  # a legal form marks a company in any asset
        orgs.add(f"{m.group(1)} {m.group(2)}")
        orgs.add(m.group(1))
    for m in PREFIX_RE.finditer(text):
        orgs.add(f"{m.group(1)} {m.group(2)}")
        orgs.add(m.group(2))
    if client_facing:
        for m in LABEL_RE.finditer(text):
            val = m.group(3).strip()
            fm = SUFFIX_RE.search(val)
            if fm:
                orgs.add(fm.group(0))
            elif m.group(2) or (m.group(1) or "").lower() in PERSON_LABELS:
                people.add(val)  # Attn: Ms Nurul Aisyah binti Rahman is a person, so each name is removed too
            else:
                orgs.add(val)
    out = set()
    for f in orgs:
        f = _tidy(f)
        if _name_ok(f, keep) and len(f) >= 3:
            out.add(f)
    for f in people:
        f = _tidy(f)
        f = re.sub(rf"^(?:{TITLES}\s+)+", "", f)
        if not _name_ok(f, keep):
            continue
        if len(f) < 3 and not re.search(f"[{CJK}]", f) and (len(f) != 2 or f.lower() in SHORT_COMMON):
            continue
        out.add(f)
        out |= person_parts(f, keep)
    return out


def own_line(line, business, domains):
    """A line holding the founder's own contact and payment details: their business name, or an email at their own domain."""
    nl = C.norm_text(line)
    if business and len(business) >= 4 and business in nl:
        return True
    for em in C.EMAIL_RE.findall(line):
        dom = re.sub(r"[^a-z]", "", em.split("@", 1)[1].split(".")[0].lower())
        if dom and any(len(dom) >= 5 and (dom in d or d in dom) for d in domains):
            return True
    return False


def redact(text, kind, names, addresses=(), exact=(), business="", domains=(), matched=None):
    """Clean one asset. names are removed in any case; exact names (a company's first word) only as written.
    Contact details on the founder's own lines are removed too but counted as 'own', never as client data."""
    counts = {k: 0 for k in PLACE}
    counts["own"] = 0
    if business or domains:
        lines = text.split("\n")
        for i, ln in enumerate(lines):
            if own_line(ln, business, domains):
                n0 = 0
                for pat, key in [(C.EMAIL_RE, "email")] + [(r, "bank") for r in C.BANK_RES]:
                    ln, k = pat.subn(PLACE[key], ln)
                    n0 += k
                for ph in sorted(set(C.phone_hits(ln)), key=len, reverse=True):
                    n0 += ln.count(ph)
                    ln = ln.replace(ph, PLACE["phone"])
                for pat, key in [(r, "address") for r in C.ADDRESS_RES] + [(r, "postcode") for r in C.POSTCODE_RES]:
                    ln, k = pat.subn(PLACE[key], ln)
                    n0 += k
                lines[i] = ln
                counts["own"] += n0
        text = "\n".join(lines)

    counts["client_words"] = 0

    def sub(pattern, key, s, flags=0):
        n = 0

        def rep(_m):
            nonlocal n
            n += 1
            if key == "client":
                counts["client_words"] += len(C.words(_m.group(0)))
            return PLACE[key]
        s2 = re.sub(pattern, rep, s, flags=flags) if isinstance(pattern, str) else pattern.sub(rep, s)
        counts[key] += n
        return s2

    for lit in sorted({a.strip() for a in addresses if a and a.strip()}, key=len, reverse=True):
        text = sub(re.compile(re.escape(lit), re.I), "address", text)
    text = sub(C.EMAIL_RE, "email", text)
    for r in C.BANK_RES:
        text = sub(r, "bank", text)
    if kind in C.CLIENT_FACING:
        text = sub(C.MONEY_RE, "fee", text)
        text = sub(C.FEE_EXTRA_RE, "fee", text)
    for ph in sorted(set(C.phone_hits(text)), key=len, reverse=True):
        n = text.count(ph)
        if n:
            text = text.replace(ph, PLACE["phone"])
            counts["phone"] += n
    for r in C.ADDRESS_RES:
        text = sub(r, "address", text)
    for r in C.POSTCODE_RES:
        text = sub(r, "postcode", text)
    for nm in sorted(names, key=len, reverse=True):
        short = len(nm) <= 2 and not re.search(f"[{CJK}]", nm)
        if re.search(f"[{CJK}]", nm):  # no spaces between words in these scripts, so no word boundary either
            pat = re.compile(re.escape(nm))
        else:
            body = r",?\s+".join(re.escape(t) for t in nm.split())  # "Halcyon Foods Inc" also matches "Halcyon Foods, Inc."
            pat = re.compile(r"(?<![\w\[])" + body + r"(?![\w\]])", 0 if short else re.I)
        before = counts["client"]
        text = sub(pat, "client", text)
        if matched is not None and counts["client"] > before:
            matched.add(nm)
    for nm in sorted(exact, key=len, reverse=True):  # "Acme" from "Acme Logistics Inc.", as written; "Acme's" too
        pat = re.compile(r"(?<![\w\[])" + re.escape(nm) + r"(?![\w\]])")
        before = counts["client"]
        text = sub(pat, "client", text)
        if matched is not None and counts["client"] > before:
            matched.add(nm)
    text = re.sub(r"\[client\](?:[ \t]+\[client\])+", "[client]", text)
    text = re.sub(r"\[address\](?:,?[ \t]*(?:\[(?:address|postal code)\]|\d{4,6}\b))+", "[address]", text)
    return text, counts


def say(counts, distinct=None):
    """'4 client names (7 mentions), 2 fees'. distinct is the number of different client names, when known."""
    parts = []
    for k in ["client", "fee", "email", "phone", "address", "postcode", "bank"]:
        n = counts.get(k, 0)
        if not n:
            continue
        if k == "client" and distinct is not None and distinct != n:
            parts.append(f"{distinct} {LABELS[k][0] if distinct == 1 else LABELS[k][1]} ({n} mentions)")
        else:
            parts.append(f"{n} {LABELS[k][0] if n == 1 else LABELS[k][1]}")
    out = ", ".join(parts) if parts else "nothing"
    if counts.get("own"):
        out += f"; your own contact and payment details ({counts['own']}) left out of the reading"
    return out


def roots(matched, names):
    """Distinct clients among the names that matched: 'Priya', 'Raman' and 'Priya Raman' are one person."""
    def part_of(n, m):
        tn, tm = C.norm_text(n).split(), C.norm_text(m).split()
        return n != m and len(tn) < len(tm) and all(t in tm for t in tn)
    allnames = set(names) | set(matched)
    out = set()
    for n in matched:
        bigger = [m for m in allnames if part_of(n, m)]
        out.add(max(bigger, key=len) if bigger else n)
    # a root that is itself part of another root (Acme Logistics inside Acme Logistics Inc.) folds in
    return {r for r in out if not any(part_of(r, o) for o in out)}


def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("manifest")
    a.add_argument("--out", required=True)
    a.add_argument("--client", action="append", default=[], help="a client company or brand name to remove as written (repeat)")
    a.add_argument("--person", action="append", default=[], help="a client's or contact's full name; each part is removed too (repeat)")
    a.add_argument("--keep", action="append", default=[], help="a name never to remove (repeat)")
    a.add_argument("--address", action="append", default=[], help="an address, registration number or other client detail to remove as written (repeat)")
    a.add_argument("--delete-raw", action="store_true", help="delete the raw pasted files once the clean copies are written")
    args = a.parse_args()

    man = C.load_json(args.manifest, "assets file")
    if not isinstance(man, dict) or not isinstance(man.get("assets"), list) or not man["assets"]:
        C.stop('the assets file needs {"business": ..., "assets": [{"id", "kind", "label", "file"}, ...]} with at least one asset.')
    keep = {C.norm_text(x) for x in args.keep + [man.get("business", ""), man.get("founder", "")] if x and len(x.strip()) >= 2}
    base = Path(args.manifest).resolve().parent
    seen, assets, texts = set(), [], {}
    for i, raw in enumerate(man["assets"], 1):
        if not isinstance(raw, dict):
            C.stop(f"asset {i} is not an object with id, kind, label and file.")
        aid = str(raw.get("id") or "").strip()
        if not re.fullmatch(r"[a-z0-9_]{1,20}", aid):
            C.stop(f"asset {i} needs a short id in lower case letters, digits or _ (for example web, li, prop).")
        if aid in seen:
            C.stop(f"two assets share the id '{aid}'. Give each its own id.")
        seen.add(aid)
        kind = C.kind_of(raw.get("kind"))
        if kind is None or kind == "agreed":
            C.stop(f"asset '{aid}' has kind '{raw.get('kind')}', which the scan does not know. Use one of: "
                   + ", ".join(k for k in C.KIND_WEIGHTS if k != "agreed") + ".")
        f = Path(raw.get("file") or "")
        if not f.is_absolute():
            f = base / f
        text = C.read_text(f, f"text of asset '{aid}'")
        if len(C.words(text)) < 3:
            C.stop(f"asset '{aid}' ({raw.get('label') or kind}) is empty. Paste its text, or drop it from the scan.")
        texts[aid] = text
        assets.append({"id": aid, "kind": kind, "label": (raw.get("label") or C.KIND_NAMES[kind]).strip(),
                       "weight": C.KIND_WEIGHTS[kind], "client_facing": kind in C.CLIENT_FACING})

    names = {n.strip() for n in args.client if n and n.strip() and not kept(n, keep)}
    for n in [x for x in args.person if x and x.strip()]:  # a person given in full is removed by each name too
        n = _tidy(re.sub(rf"^(?:{TITLES}[ \t]+(?:(?:and|&)[ \t]+)?)+", "", n.strip()))
        if not n or kept(n, keep):
            continue
        names.add(n)
        for piece in re.split(r"\s+(?:and|&)\s+", n):  # "Claire & James P." is two people
            piece = _tidy(piece)
            if len(piece) >= 3 and not kept(piece, keep):
                names.add(piece)
            names |= person_parts(piece, keep)
    given = len(names)
    for asset in assets:
        names |= candidate_names(texts[asset["id"]], asset["client_facing"], keep)
    auto = len(names) - given
    companies = {n.strip() for n in args.client if n and n.strip()}
    for n in list(names):  # a company given with its legal form is removed without it too
        m = re.match(rf"^(.+?),?\s+{FORM}$", n)
        if m and not kept(m.group(1), keep) and len(m.group(1)) >= 3:
            names.add(m.group(1))
            companies.add(n)
        m = PREFIX_RE.fullmatch(n)
        if m and not kept(m.group(2), keep):
            names.add(m.group(2))
            companies.add(n)
    for asset in assets:  # testimonial companies found on a dash line
        for t in TESTIMONIAL_RE.finditer(texts[asset["id"]]):
            rest = texts[asset["id"]][t.end():].split("\n", 1)[0]
            fields = [x.strip(" .\t") for x in re.split(r"[,|/]", rest) if x.strip(" .\t")]
            if fields and fields[-1] in names:
                companies.add(fields[-1])
    # A company's first word on its own ("Acme's operations team"), as written, unless the founder's own copy
    # uses that word in lower case as an ordinary word.
    alltext = "\n".join(texts.values())
    exact = set()
    for c in companies:
        toks = c.replace(",", " ").split()
        if len(toks) < 2:
            continue
        first = toks[0].strip(".")
        if (len(first) >= 3 and first[0].isupper() and first not in STOPWORDS and first.lower() not in LOWER_STOP
                and not kept(first, keep) and not re.search(r"\b" + re.escape(first.lower()) + r"\b", alltext)
                and not re.fullmatch(PARTICLE, first.lower())):
            exact.add(first)

    business = C.norm_text(man.get("business", ""))
    biz_letters = re.sub(r"[^a-z]", "", business)
    domains = {biz_letters} if len(biz_letters) >= 5 else set()
    decimal = C.detect_decimal(list(texts.values()))  # the founder's decimal style, read once from everything pasted
    report, totals, cleans, matched = {}, {k: 0 for k in list(PLACE) + ["own", "client_words"]}, {}, set()
    for asset in assets:
        clean, counts = redact(texts[asset["id"]], asset["kind"], names, args.address, exact, business, domains, matched)
        cleans[asset["id"]] = clean
        report[asset["id"]] = counts
        for k, v in counts.items():
            totals[k] += v
    # Plausibility: names that take out a large share of an asset's words have matched ordinary words, not a client.
    for asset in assets:
        raw_n = len(C.words(texts[asset["id"]]))
        gone = report[asset["id"]].pop("client_words", 0)
        if (raw_n >= 40 and gone > 0.4 * raw_n) or (raw_n >= 120 and gone > 0.2 * raw_n):
            C.stop(f"client names took out {gone} of the {raw_n} words in {asset['label']}, more than names ever take. A --client "
                   f"or --person name probably matches ordinary words; check them (use --keep for any word of the founder's) "
                   f"and run again. Nothing was written.")
    totals.pop("client_words", None)
    distinct = len(roots(matched, names))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for asset in assets:
        (out / f"{asset['id']}.txt").write_text(cleans[asset["id"]], encoding="utf-8")
        asset["file"] = str((out / f"{asset['id']}.txt").resolve())
        counts = report[asset["id"]]
        print(f"{asset['label']} ({C.KIND_NAMES[asset['kind']]}, weight {asset['weight']:g}): removed {say(counts)}.")
        if asset["client_facing"] and counts["client"] == 0:
            print(f"NOTE: no client name found in {asset['label']}. Read it once by eye; if a client or person "
                  f"is named, run again with --client \"<name>\".")
    if auto and not args.client and not args.person:
        print("NOTE: every name removed was found automatically. Read each asset once by eye and pass anyone else named "
              "(in running prose, a testimonial, a company without Ltd or Inc) with --person or --client.")
    hashes = sorted({C.term_hash(n) for n in names | exact if C.fingerprint_ok(n)})
    amb = [] if decimal else C.ambiguous_numbers(list(cleans.values()))
    (out / "redaction.json").write_text(json.dumps(
        {"assets": report, "totals": totals, "client_names": distinct, "own_contact": totals["own"],
         "names_removed": len(names), "names_found_automatically": max(0, auto), "decimal_style": decimal,
         "hashes": hashes, "note": "Fingerprints only. The removed names are not stored anywhere."}, indent=2), encoding="utf-8")
    (out / "assets.json").write_text(json.dumps(
        {"business": man.get("business", ""), "founder_sells": man.get("founder_sells", ""), "sold_by": man.get("sold_by") or {},
         "decimal_style": decimal, "assets": assets}, indent=2), encoding="utf-8")
    print(f"WROTE: {len(assets)} clean assets, {out / 'assets.json'} and {out / 'redaction.json'}")
    if args.delete_raw:
        for raw in man["assets"]:
            f = Path(raw.get("file") or "")
            f = f if f.is_absolute() else base / f
            if f.exists() and f.resolve().parent != out.resolve():
                f.unlink()
        print("DELETED: the raw pasted copies. Only the clean copies remain.")
    print(f"In total removed {say(totals, distinct)}. Quote only from the clean copies from here on.")
    print(f"NUMBERS: the founder writes decimals with a {decimal}." if decimal else "NUMBERS: decimal style not shown in the paste.")
    if amb:
        print(f"ASK: your copy has {', '.join(amb[:3])}, which reads two ways. Ask the founder in one question whether "
              f"{amb[0]} is a whole number with a thousands separator or a decimal, and set locale.decimal to dot or comma.")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print(f"STOP: the redaction could not finish ({type(e).__name__}: {e}). Nothing usable was written; check the assets file.")
        sys.exit(2)
