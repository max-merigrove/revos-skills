#!/usr/bin/env python3
"""Shared helpers for Lead Magnet Factory scripts. Standard library only. No network calls.

Every script exits 0 when done, 1 when it printed PROBLEM lines (fix the spec and run again),
and 2 on a STOP line (do what it says; never show output from a run that stopped).
"""
import datetime as dt
import json
import os
import re
import sys
import traceback
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import locale_numbers as LN  # noqa: E402

CREDIT = "Made with Merigrove Lead Magnet Factory"
FORMATS = ("scorecard", "checklist", "guide")
MERGE_TAGS = {"{{first_name}}", "{{magnet_link}}", "{{booking_link}}", "{{reply_address}}", "{{unsubscribe_link}}"}
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]


class Stop(Exception):
    """A plain instruction for Claude or the founder. Printed as STOP and exit 2."""


def run_main(fn):
    try:
        code = fn()
    except Stop as e:
        print(f"STOP: {e}")
        sys.exit(2)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"STOP: the spec file is not valid JSON ({e}). Fix the file and run again.")
        sys.exit(2)
    except (LN.Ambiguous, LN.Unreadable) as e:
        print(f"STOP: ASK: {e}")
        sys.exit(2)
    except KeyboardInterrupt:
        sys.exit(2)
    except Exception as e:  # noqa: BLE001  never a raw traceback in front of a founder
        if os.environ.get("LMF_DEBUG"):
            traceback.print_exc()
        where = ""
        tb = traceback.extract_tb(e.__traceback__)
        if tb:
            last = tb[-1]
            where = f" at {os.path.basename(last.filename)} line {last.lineno}, in {last.name}"
        print(f"STOP: unexpected error{where} ({type(e).__name__}: {e}). This is a fault in the skill's script, not "
              "in what the founder gave: check the spec field it names against references/spec.md, and run again "
              "with LMF_DEBUG=1 for the full trace.")
        sys.exit(2)
    sys.exit(code or 0)


def load_spec(path):
    if not path or not os.path.exists(path):
        raise Stop(f"cannot find the spec file {path}. Write it first (references/spec.md).")
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    if not raw.strip():
        raise Stop(f"{path} is empty. Write the spec first (references/spec.md).")
    spec = json.loads(raw)
    if not isinstance(spec, dict):
        raise Stop("the spec must be a JSON object with format, founder, topic and the magnet (references/spec.md).")
    spec["_path"] = os.path.abspath(path)
    return spec


def read_text(path):
    for enc in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            with open(path, encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    raise Stop(f"cannot read {path} as text")


def sources_text(spec):
    """All founder-given text the spec names in `sources`, plus every founder reply recorded in the spec."""
    base = os.path.dirname(spec.get("_path", "."))
    out = []
    for s in spec.get("sources") or []:
        p = s if os.path.isabs(s) else os.path.join(base, s)
        if not os.path.exists(p):
            raise Stop(f"the source file {s} named in the spec is not there. Save what the founder pasted to that "
                       "path, exactly as given, or remove it from `sources`.")
        out.append(read_text(p))
    for r in spec.get("founder_replies") or []:
        out.append(str(r))
    return "\n".join(out)


def slugify(text, maxlen=48):
    t = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-zA-Z0-9]+", "-", t).strip("-").lower()
    t = t[:maxlen].rstrip("-")
    return t or "lead-magnet"


def parse_date(s, what="date"):
    try:
        return dt.date.fromisoformat(str(s))
    except ValueError:
        raise Stop(f"{what} '{s}' is not a date written YYYY-MM-DD") from None


def country_defaults(spec):
    c = ((spec.get("founder") or {}).get("country") or "").upper()
    return LN.locale_defaults(c)


def human_date(d, spec):
    """A date in the founder's own order: 2 November 2026, November 2, 2026, or 2026-11-02."""
    order = country_defaults(spec)["date_order"]
    if order == "MDY":
        return f"{MONTHS[d.month - 1]} {d.day}, {d.year}"
    if order == "YMD":
        return d.isoformat()
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def normalise_typed(text):
    """Founder habits the shared number reader does not take: the Dutch and German ',-' price ending."""
    t = str(text).strip()
    t = re.sub(r"(\d)[,.]-+(?=\s|$|[^\d])", r"\1", t)
    t = re.sub(r"(?<=\d)[.,]+$", "", t)
    return t


def decimal_style(spec, samples=()):
    st = ((spec.get("founder") or {}).get("decimal") or "").lower()
    if st in ("dot", "comma"):
        return st
    joined = " ".join(str(x) for x in samples)
    if re.search(r"\d,-", joined):
        return "comma"
    return LN.detect_decimal_style([normalise_typed(x) for x in samples])


def read_money(text, decimal):
    try:
        return LN.parse_money(normalise_typed(text), decimal)
    except (LN.Ambiguous, LN.Unreadable):
        raise
    except (ValueError, TypeError):
        raise LN.Unreadable(f"'{text}' could not be read as one number") from None


def contrast(fg, bg):
    def lum(h):
        h = h.lstrip("#")
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        rgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        rgb = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
        return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]
    a, b = lum(fg), lum(bg)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def is_hex(c):
    return bool(re.fullmatch(r"#?[0-9A-Fa-f]{6}|#?[0-9A-Fa-f]{3}", str(c or "")))


def words(text):
    return re.findall(r"[^\W\d_][\w'’-]*|\d[\d.,]*", str(text or ""))


def file_names(spec):
    d = parse_date(spec.get("date") or dt.date.today().isoformat(), "spec date")
    slug = slugify((spec.get("topic") or {}).get("slug") or (spec.get("magnet") or {}).get("title") or "lead-magnet")
    ds = d.isoformat()
    fmt = spec.get("format")
    names = {"pack": f"lead-magnet-launch-pack_{ds}.docx", "optin": f"opt-in-page_{ds}.html"}
    if fmt == "scorecard":
        names["main"] = f"{slug}-scorecard_{ds}.html"
        names["twin"] = f"{slug}-scorecard-printable_{ds}.docx"
    elif fmt == "checklist":
        names["main"] = f"{slug}-checklist_{ds}.docx"
        names["pdf"] = f"{slug}-checklist_{ds}.pdf"
    else:
        names["main"] = f"{slug}-one-page-guide_{ds}.docx"
        names["pdf"] = f"{slug}-one-page-guide_{ds}.pdf"
    return names, d


def magnet_link_tag():
    return "{{magnet_link}}"


def founder_strings(spec):
    """Every founder-facing string in the spec, with a label saying where it sits. Scanned by check_copy.py."""
    out = []

    def add(label, v):
        if isinstance(v, str) and v.strip():
            out.append((label, v))

    t = spec.get("topic") or {}
    for k in ("problem", "format_reason", "not_given_away", "drafted", "previous"):
        add(f"topic.{k}", t.get(k))
    for r in t.get("runners_up") or []:
        add("topic.runner_up", r.get("topic"))
        add("topic.runner_up.why_not", r.get("why_not"))
    m = spec.get("magnet") or {}
    for k in ("title", "promise", "who_for", "who_not_for", "strength_fallback", "not_a_fit", "footer"):
        add(f"magnet.{k}", m.get(k))
    for q in m.get("questions") or []:
        add(f"{q.get('id')}.text", q.get("text"))
        add(f"{q.get('id')}.label", q.get("label"))
        for k in ("strength", "strength_mid", "fix_low", "fix_high"):
            add(f"{q.get('id')}.{k}", q.get(k))
        for o in q.get("options") or []:
            add(f"{q.get('id')}.option", o.get("label"))
    for q in m.get("fit_questions") or []:
        add(f"{q.get('id')}.text", q.get("text"))
        for o in q.get("options") or []:
            add(f"{q.get('id')}.option", o.get("label"))
    for t in m.get("tiers") or []:
        add(f"tier {t.get('name')}.name", t.get("name"))
        add(f"tier {t.get('name')}.description", t.get("description"))
    door = m.get("door") or {}
    add("door.question", door.get("question"))
    add("door.sentence", door.get("sentence"))
    cta = m.get("cta") or {}
    add("cta.label", cta.get("label"))
    add("cta.line", cta.get("line"))
    add("cta.line_top_tier", cta.get("line_top_tier"))
    c = spec.get("checklist") or {}
    for k in ("title", "who_for", "not_covered", "next_step"):
        add(f"checklist.{k}", c.get(k))
    for si, s in enumerate(c.get("sections") or []):
        add(f"checklist.section{si + 1}.heading", s.get("heading"))
        for ii, it in enumerate(s.get("items") or []):
            add(f"checklist.item{si + 1}.{ii + 1}", it.get("text"))
            add(f"checklist.item{si + 1}.{ii + 1}.detail", it.get("detail"))
    g = spec.get("guide") or {}
    for k in ("title", "who_for", "idea", "example_label", "example", "next_step", "not_covered"):
        add(f"guide.{k}", g.get(k))
    for i, st in enumerate(g.get("steps") or []):
        add(f"guide.step{i + 1}", st.get("text") if isinstance(st, dict) else st)
    la = spec.get("launch") or {}
    op = la.get("optin") or {}
    for k in ("headline", "subhead", "expectation", "button", "signoff_line"):
        add(f"optin.{k}", op.get(k))
    for i, b in enumerate(op.get("bullets") or []):
        add(f"optin.bullet{i + 1}", b)
    ty = la.get("thankyou") or {}
    for k in ("headline", "body", "link_label", "next_step"):
        add(f"thankyou.{k}", ty.get(k))
    for i, e in enumerate(la.get("emails") or []):
        n = i + 1
        for j, s in enumerate(e.get("subjects") or []):
            add(f"email{n}.subject{j + 1}", s)
        for k in ("preview", "body", "ps"):
            add(f"email{n}.{k}", e.get(k))
    for r in la.get("result_map") or []:
        for k in ("dealing_with", "ask", "next_step"):
            add(f"result_map {r.get('when')}.{k}", r.get(k))
    return out
