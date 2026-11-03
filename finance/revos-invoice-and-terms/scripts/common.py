#!/usr/bin/env python3
"""Shared helpers for the Invoice and Terms Builder scripts (this skill only).

Money is held as integers in the currency's minor unit (cents, pence, or whole yen).
Every founder-typed number goes through locale_numbers.py. Standard library only. No network calls.
"""
import json
import os
import re
import sys
import traceback
from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_EVEN, InvalidOperation
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import locale_numbers as LN  # noqa: E402

CREDIT = "Made with Merigrove Invoice and Terms Builder"


class Stop(Exception):
    """A plain message for the founder or for Claude. Printed as STOP: ... and exit 2."""


def run_main(fn):
    """Run a script's main(); never show a traceback to anyone."""
    try:
        code = fn()
    except Stop as e:
        print(f"STOP: {e}")
        sys.exit(2)
    except SystemExit:
        raise
    except BrokenPipeError:
        sys.exit(0)
    except Exception as e:  # noqa: BLE001
        if os.environ.get("INVOICE_DEBUG"):
            traceback.print_exc()
        print(f"STOP: something in the input could not be read ({type(e).__name__}: {e}). "
              "Check the inputs file against `python3 scripts/invoice_calc.py template` and run again.")
        sys.exit(2)
    sys.exit(code or 0)


def load_json(path, what="file"):
    if not path or not os.path.exists(path):
        raise Stop(f"there is no {what} at {path}")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise Stop(f"the {what} at {path} is not valid JSON (line {e.lineno}: {e.msg}). Fix it and run again")


def save_json(obj, path):
    d = os.path.dirname(os.path.abspath(path))
    os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    return path


# ---------------------------------------------------------------- currency minor units (ISO 4217)
ZERO_DECIMAL = {"JPY", "KRW", "VND", "CLP", "ISK", "UGX", "XAF", "XOF", "XPF", "PYG", "KMF", "RWF", "VUV",
                "GNF", "DJF", "BIF"}
THREE_DECIMAL = {"KWD", "BHD", "OMR", "JOD", "TND", "IQD", "LYD"}
KNOWN_CODES = set("""AED AFN ALL AMD ANG AOA ARS AUD AWG AZN BAM BBD BDT BGN BHD BIF BMD BND BOB BRL BSD BTN BWP BYN BZD
CAD CDF CHF CLP CNY COP CRC CUP CVE CZK DJF DKK DOP DZD EGP ERN ETB EUR FJD FKP GBP GEL GHS GIP GMD GNF GTQ GYD HKD HNL
HTG HUF IDR ILS INR IQD IRR ISK JMD JOD JPY KES KGS KHR KMF KPW KRW KWD KYD KZT LAK LBP LKR LRD LSL LYD MAD MDL MGA MKD
MMK MNT MOP MRU MUR MVR MWK MXN MYR MZN NAD NGN NIO NOK NPR NZD OMR PAB PEN PGK PHP PKR PLN PYG QAR RON RSD RUB RWF SAR
SBD SCR SDG SEK SGD SHP SLE SOS SRD SSP STN SYP SZL THB TJS TMT TND TOP TRY TTD TWD TZS UAH UGX USD UYU UZS VES VND VUV
WST XAF XCD XOF XPF YER ZAR ZMW ZWL""".split())


def minor_units(code):
    c = (code or "").upper()
    if c in ZERO_DECIMAL:
        return 0
    if c in THREE_DECIMAL:
        return 3
    return 2


def to_minor(value, code, mode="half_up"):
    """Decimal or Fraction amount in major units to an integer in minor units, rounded once."""
    mu = minor_units(code)
    if isinstance(value, Fraction):
        value = Decimal(value.numerator) / Decimal(value.denominator)
    q = Decimal(1).scaleb(-mu) if mu else Decimal(1)
    rounding = ROUND_HALF_EVEN if mode == "half_even" else ROUND_HALF_UP
    return int((Decimal(value).quantize(q, rounding=rounding) * (10 ** mu)).to_integral_value())


def frac_round(fr, mode="half_up"):
    """Round a Fraction (in minor units) to an int, half up (away from zero) or half even. Independent of Decimal."""
    sign = -1 if fr < 0 else 1
    a = abs(fr)
    n, rem = divmod(a.numerator, a.denominator)
    twice = 2 * rem
    if twice > a.denominator or (twice == a.denominator and (mode == "half_up" or n % 2 == 1)):
        n += 1
    return sign * n


def dec(value):
    """Founder number already parsed to float: to a clean Decimal (no binary noise)."""
    return Decimal(str(round(float(value), 8))).normalize()


# ---------------------------------------------------------------- reading founder figures
def read_amount(text, style, what, need=None):
    """Read a founder-typed amount. Returns Decimal. style is 'dot', 'comma' or None."""
    if text is None or (isinstance(text, str) and not text.strip()):
        raise Stop(f"{what} is empty")
    if isinstance(text, (int, float)) and not isinstance(text, bool):
        return dec(text)
    t = str(text).strip()
    t = re.sub(r"(?i)\b(at cost|actuals?|actual|approx\.?|only|each|ea\.?|per day|a day|/day|per hour|/hr|an hour)\b", " ", t)
    try:
        v, _cur, notes = LN.parse_money(t, style)
    except LN.Ambiguous as e:
        raise Stop(f"please check {what}: {e}. Ask the founder which they mean, then put the figure in again")
    except LN.Unreadable as e:
        raise Stop(f"{what} could not be read ({e}). Ask the founder to restate it")
    if "approximate" in notes:
        raise Stop(f"{what} is approximate ('{text}'). An invoice needs the exact figure: ask the founder for it")
    return dec(v)


def read_qty(text, style, what):
    if text is None or text == "":
        return Decimal(1)
    if isinstance(text, (int, float)) and not isinstance(text, bool):
        return dec(text)
    t = str(text).strip().lower()
    t = re.sub(r"\b(days?|hours?|hrs?|h|units?|items?|rounds?|sessions?|pcs?|pieces?|x|nos?\.?|tage?|stunden?|日|時間)\b", " ", t)
    try:
        v, notes = LN.parse_number(t.strip(), style)
    except LN.Ambiguous as e:
        raise Stop(f"please check {what}: {e}")
    except LN.Unreadable as e:
        raise Stop(f"{what} could not be read ({e}). Ask the founder to restate it")
    if "approximate" in notes:
        raise Stop(f"{what} is approximate ('{text}'). Ask the founder for the exact quantity")
    return dec(v)


def read_percent(text, style, what):
    if isinstance(text, (int, float)) and not isinstance(text, bool):
        return dec(text)
    try:
        v, notes = LN.parse_percent(str(text).strip(), style)
    except (LN.Ambiguous, LN.Unreadable) as e:
        raise Stop(f"{what} could not be read as a percentage ({e}). Ask the founder to restate it")
    return dec(v)


def style_from(samples, given=None):
    """The founder's decimal style, from what they typed. Returns 'dot', 'comma' or None."""
    if given in ("dot", "comma"):
        return given
    return LN.detect_decimal_style([str(s) for s in samples if s is not None])


# ---------------------------------------------------------------- writing figures in the founder's style
def group_digits(intpart, sep, indian=False):
    s = str(intpart)
    if not sep:
        return s
    if indian and len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        return sep.join(parts + [tail])
    out = []
    while len(s) > 3:
        out.insert(0, s[-3:])
        s = s[:-3]
    out.insert(0, s)
    return sep.join(out)


class Money:
    """Formats integer minor units in the founder's style."""

    def __init__(self, code, decimal="dot", group=None, indian=False, code_after=None):
        self.code = (code or "").upper()
        self.mu = minor_units(self.code)
        self.decimal = "," if decimal == "comma" else "."
        if group is None:
            group = "." if decimal == "comma" else ","
        self.group = group
        self.indian = indian
        self.code_after = (decimal == "comma") if code_after is None else code_after

    def num(self, minor):
        neg = minor < 0
        a = abs(int(minor))
        if self.mu:
            ip, fp = divmod(a, 10 ** self.mu)
            s = group_digits(ip, self.group, self.indian) + self.decimal + str(fp).zfill(self.mu)
        else:
            s = group_digits(a, self.group, self.indian)
        return ("-" if neg else "") + s

    def full(self, minor):
        n = self.num(minor)
        return f"{n} {self.code}" if self.code_after else f"{self.code} {n}"

    def plain_decimal(self, minor):
        """For spreadsheets: a Decimal in major units."""
        return Decimal(int(minor)).scaleb(-self.mu)


GROUPS = {"space": "\u00a0", "dot": ".", "comma": ",", "apostrophe": "'", "none": ""}


def sample_style(s):
    """How one founder-typed figure is written: (decimal 'dot'|'comma'|None, grouping 'space'|'dot'|'comma'|'apostrophe'|None)."""
    t = re.sub(r"[^\d.,' \u00a0]", "", str(s or "")).strip()
    dec_ = "comma" if re.search(r"\d,\d{1,2}$", t) else ("dot" if re.search(r"\d\.\d{1,2}$", t) else None)
    grp = None
    if re.search(r"\d[ \u00a0]\d{3}(?!\d)", t):
        grp = "space"
    elif re.search(r"\d'\d{3}(?!\d)", t):
        grp = "apostrophe"
    elif re.search(r"\d\.\d{3}(?!\d)", t) and dec_ != "dot":
        grp = "dot"
    elif re.search(r"\d,\d{3}(?!\d)", t) and dec_ != "comma":
        grp = "comma"
    return dec_, grp


def money_for(plan, code=None):
    """The founder's money format, exactly as the plan worked it out (decimal mark, grouping, Indian grouping)."""
    return Money(code or plan.get("currency") or "XXX", plan.get("decimal_style") or "dot",
                 group=plan.get("group"), indian=plan.get("indian"))


def unit_price_text(value, money):
    """A unit price may carry more decimals than the currency; show at least the minor units."""
    d = Decimal(value)
    mu = money.mu
    exp = -d.as_tuple().exponent if d.as_tuple().exponent < 0 else 0
    places = max(mu, min(exp, 6))
    q = d.quantize(Decimal(1).scaleb(-places)) if places else d.quantize(Decimal(1))
    sign = "-" if q < 0 else ""
    q = abs(q)
    ip = int(q)
    s = group_digits(ip, money.group, money.indian)
    if places:
        frac = str(q).split(".")[1] if "." in str(q) else "0" * places
        s += money.decimal + frac.ljust(places, "0")
    return sign + s


def qty_text(q, money):
    d = Decimal(q).normalize()
    if d == d.to_integral_value():
        return group_digits(int(d), money.group, money.indian)
    s = format(d, "f")
    return s.replace(".", money.decimal)


def safe_filename(s):
    s = re.sub(r"[\\/:*?\"<>|]+", "-", str(s)).strip()
    s = re.sub(r"\s+", " ", s)
    return s[:120]


def iso(d):
    return d.isoformat() if d else None


# ---------------------------------------------------------------- vague descriptions (working default)
VAGUE = {"consulting", "consultancy", "services", "service", "work", "design", "professional", "fees", "fee", "misc",
         "miscellaneous", "sundries", "as", "agreed", "project", "support", "development", "invoice", "charges",
         "general", "various", "items", "stuff", "job", "time", "hours", "labour", "labor", "other", "for", "the",
         "and", "of", "a", "an", "to", "in", "on", "with", "per", "our", "my", "your", "rendered", "provided"}


def vague_description(text):
    words = re.findall(r"[^\W\d_][\w'&.-]*", str(text or ""), re.U)
    if len(words) < 3:
        return "fewer than three words"
    if all(w.lower().strip(".") in VAGUE for w in words):
        return "too general to tell what the work was"
    return None


# ---------------------------------------------------------------- planted instructions in pasted text
INJECTION = re.compile(
    r"(?i)(\b(any|an|the|dear|hey|attention|note to( the)?)\s+(ai|a\.i\.|assistant|chat ?gpt|claude|gpt|llm|language model|bot)\b"
    r"|\bignore (all |any )?(the )?(previous|above|prior|earlier) (instructions?|rules?)"
    r"|\bsystem prompt\b|\byou are (now )?(an?|the) (ai|assistant)\b|\bas an ai\b|\bto (the )?(ai|assistant|model) reading)")


def find_injections(text):
    out = []
    for line in str(text or "").splitlines():
        if INJECTION.search(line):
            out.append(line.strip())
    return out
