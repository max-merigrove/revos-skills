#!/usr/bin/env python3
"""Shared helpers for Dead Lead Revival scripts: settings, dates written the founder's way, folding.

Standard library only. No network calls.
"""
import json
import re
import unicodedata
from datetime import date, timedelta
from pathlib import Path

MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
               "October", "November", "December"]
DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
COMPLIANCE_LINE = ("Before you send, check the rules for email, texts and calls where you and your contacts are. "
                   "This is planning, not legal advice.")
OPT_OUT_EMAIL = "If you'd rather I didn't get in touch again, just say and I won't."
OPT_OUT_SHORT = "Just say if you'd rather I didn't message again."

DEFAULTS = {
    "daily_cap": 15, "working_days": "mon-fri", "cooldown_months": 6, "tier_a": 10, "too_recent_days": 30,
    "channels": ["email"], "text_only_if_texted": True, "price_from_touch": None, "changed": [],
    "next_step": "a 20-minute call", "days_off": [], "exclude": [], "never_in_first_touches": [],
    "source_default": None, "source_rules": [], "country": "", "english": "en", "prices": [],
    "message_language": "en", "context_phrases": {}, "month_names": [], "exclude_notes": {}, "greeting_default": "",
}
# Month names for {when} in messages written in another language. Any other language: give month_names in settings.
MONTHS_BY_LANG = {
    "de": "Januar Februar März April Mai Juni Juli August September Oktober November Dezember",
    "fr": "janvier février mars avril mai juin juillet août septembre octobre novembre décembre",
    "es": "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre",
    "it": "gennaio febbraio marzo aprile maggio giugno luglio agosto settembre ottobre novembre dicembre",
    "nl": "januari februari maart april mei juni juli augustus september oktober november december",
    "pt": "janeiro fevereiro março abril maio junho julho agosto setembro outubro novembro dezembro",
    "sv": "januari februari mars april maj juni juli augusti september oktober november december",
    "da": "januar februar marts april maj juni juli august september oktober november december",
}
# The personal-field phrases the script writes in English. In another language the founder's phrases replace them
# (settings context_phrases, same keys; {when} and {deal} are filled). Each is a noun phrase, so it reads after
# "after", "since", "about" or "from" and at the start of a sentence.
CONTEXT_KEYS = {
    "proposal": "my proposal from {when}",
    "proposal_deal": "my {deal} proposal from {when}",
    "price_talk": "the price we talked about in {when}",
    "met": "the time we met in {when}",
    "enquiry": "your enquiry in {when}",
    "exchange": "our last exchange in {when}",
    "conversation": "the conversation we had in {when}",
    "booked_call": "the call we had lined up around {when}",
    "work": "the work we did together in {when}",
    "work_deal": "the {deal} work we did together in {when}",
}


class Stop(Exception):
    def __init__(self, msg, ask=None):
        super().__init__(msg)
        self.ask = ask


def fold(text):
    t = unicodedata.normalize("NFKD", str(text or ""))
    return "".join(ch for ch in t if not unicodedata.combining(ch)).strip().lower()


def load_json(path, what):
    p = Path(path)
    if not p.exists():
        raise Stop(f"cannot find {what} at {p}")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise Stop(f"{what} ({p.name}) is not valid JSON: {e}") from e


def load_settings(path):
    """path: a settings.json path, a dict already loaded, or None for the defaults."""
    s = dict(DEFAULTS)
    if path:
        raw = dict(path) if isinstance(path, dict) else load_json(path, "the settings file")
        if not isinstance(raw, dict):
            raise Stop("the settings file must be one JSON object")
        unknown = set(raw) - set(DEFAULTS) - {"today", "business", "founder_name", "sign_off", "offer", "start",
                                               "date_order", "decimal", "opt_out_email", "opt_out_short",
                                               "previous_run", "notes", "confirmed", "batch_limit"}
        if unknown:
            raise Stop(f"unknown settings: {', '.join(sorted(unknown))}. Check the spelling against references/intake-guide.md")
        s.update({k: v for k, v in raw.items() if v is not None or k in ("price_from_touch",)})
    try:
        s["today"] = date.fromisoformat(str(s.get("today") or date.today().isoformat()))
    except ValueError as e:
        raise Stop(f"settings 'today' must be YYYY-MM-DD, got {s.get('today')}") from e
    for k in ("daily_cap", "tier_a", "cooldown_months", "too_recent_days"):
        try:
            s[k] = int(float(str(s[k]).strip()))
        except (TypeError, ValueError) as e:
            raise Stop(f"settings '{k}' must be a whole number, got {s[k]!r}") from e
    if not 1 <= s["daily_cap"] <= 200:
        raise Stop(f"a daily cap of {s['daily_cap']} is not a pace one person can keep",
                   ask="How many messages can you send by hand in a day? Most founders manage 10 to 25.")
    s["tier_a"] = max(1, min(15, s["tier_a"]))
    if isinstance(s["channels"], str):
        s["channels"] = [x.strip() for x in re.split(r"[,/ ]+", s["channels"]) if x.strip()]
    s["channels"] = [{"sms": "text", "whatsapp": "text", "linkedin": "dm", "instagram": "dm"}.get(fold(c), fold(c))
                     for c in s["channels"]]
    bad = [c for c in s["channels"] if c not in ("email", "text", "dm")]
    if bad:
        raise Stop(f"channels must be email, text or dm, got {', '.join(bad)}")
    if s.get("price_from_touch") not in (None, "", "never"):
        s["price_from_touch"] = max(3, int(s["price_from_touch"]))
    else:
        s["price_from_touch"] = None
    s.setdefault("opt_out_email", OPT_OUT_EMAIL)
    s.setdefault("opt_out_short", OPT_OUT_SHORT)
    s["sign_off"] = s.get("sign_off") or s.get("founder_name") or ""
    lang = fold(s.get("message_language") or "en").replace("_", "-").split("-")[0] or "en"
    s["message_language"] = lang
    if not isinstance(s.get("context_phrases"), dict):
        raise Stop("settings 'context_phrases' must be an object keyed by: " + ", ".join(CONTEXT_KEYS))
    bad = set(s["context_phrases"]) - set(CONTEXT_KEYS)
    if bad:
        raise Stop(f"settings 'context_phrases' has unknown keys {', '.join(sorted(bad))}; use: " + ", ".join(CONTEXT_KEYS))
    mn = s.get("month_names") or []
    if isinstance(mn, str):
        mn = mn.split()
    if mn and len(mn) != 12:
        raise Stop("settings 'month_names' must list all twelve months, January first")
    s["month_names"] = mn
    return s


def is_english(s):
    return (s.get("message_language") or "en") == "en"


def month_names_for(s):
    """The twelve month names for messages in the founder's message language, or None (numeric dates)."""
    lang = s.get("message_language") or "en"
    if lang == "en":
        return MONTH_NAMES
    if s.get("month_names"):
        return list(s["month_names"])
    if lang in MONTHS_BY_LANG:
        return MONTHS_BY_LANG[lang].split()
    return None


def month_year_in(d, s, order="dmy"):
    if isinstance(d, str):
        d = date.fromisoformat(d)
    names = month_names_for(s)
    if names:
        return f"{names[d.month - 1]} {d.year}"
    return f"{d.year}-{d.month:02d}" if order == "ymd" else f"{d.month:02d}/{d.year}"


def date_fmt_code(order):
    return {"mdy": "mm/dd/yyyy", "ymd": "yyyy-mm-dd"}.get(order, "dd/mm/yyyy")


def show_date(d, order="dmy", sep=None):
    if d is None:
        return ""
    if isinstance(d, str):
        d = date.fromisoformat(d)
    if order == "mdy":
        return f"{d.month:02d}/{d.day:02d}/{d.year}"
    if order == "ymd":
        return d.isoformat()
    return f"{d.day:02d}{sep or '/'}{d.month:02d}{sep or '/'}{d.year}"


def long_date(d, order="dmy"):
    if isinstance(d, str):
        d = date.fromisoformat(d)
    day = DAY_NAMES[d.weekday()]
    if order == "mdy":
        return f"{day} {MONTH_NAMES[d.month - 1]} {d.day}, {d.year}"
    return f"{day} {d.day} {MONTH_NAMES[d.month - 1]} {d.year}"


def month_year(d):
    if isinstance(d, str):
        d = date.fromisoformat(d)
    return f"{MONTH_NAMES[d.month - 1]} {d.year}"


def add_months(d, n):
    y, m = divmod(d.month - 1 + n, 12)
    y += d.year
    m += 1
    for day in (d.day, 30, 29, 28):
        try:
            return date(y, m, min(d.day, day))
        except ValueError:
            continue
    return d + timedelta(days=30 * n)


def months_between(a, b):
    """Whole months from a to b (b later)."""
    if isinstance(a, str):
        a = date.fromisoformat(a)
    if isinstance(b, str):
        b = date.fromisoformat(b)
    m = (b.year - a.year) * 12 + (b.month - a.month)
    if b.day < a.day:
        m -= 1
    return max(0, m)
