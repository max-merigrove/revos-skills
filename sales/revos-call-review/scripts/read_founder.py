#!/usr/bin/env python3
"""Read the figures the founder typed (not the call's), the way they wrote them, before anything is scored.

Usage:
  python3 scripts/read_founder.py --message <file holding the founder's messages as typed>
        [--country US] [--price "4k/mo"] [--length "about 50 min"] [--percent "discount=20%"]
        [--figure "budget=around 150"]... [--measure <scratch>/measure.json] [--json-out <scratch>/founder.json]

Every reading goes through locale_numbers (copied unchanged from the Merigrove Build Standard):
  - the decimal style is detected once, from everything the founder typed, and passed to every reader;
  - a figure that can be read two ways prints one ASK line (put it to the founder as one question);
  - a figure that cannot be read prints an ASK line asking the founder to restate it;
  - a headline figure that is not plausible (a price of 0, a call over four hours, a discount over 100%) prints a
    CHECK line, and nothing is scored until the founder confirms it;
  - with --measure, the founder's price is set against every price the seller said on the call, and a difference is
    printed so the readback can say which figure was used (the call's, unless the founder corrects it);
  - date order, paper size and clock come from the founder's country (locale_defaults), never from their spelling.
    With no country, the date order is read from a date the founder wrote that can only be read one way; failing that,
    one ASK line asks where they are based.
Each figure is also written back in the founder's own style (1.200,50 to a founder who writes that way).

Exit 0: read, nothing to ask. Exit 3: ASK or CHECK lines to put to the founder first. Exit 2: STOP (a file is missing).
Standard library only. No network calls. Never converts a currency and never works out a tax.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import locale_numbers as LN  # noqa: E402

DATE_STYLE = {"MDY": "month day year", "DMY": "day month year", "YMD": "year month day"}


def stop(msg):
    print(f"STOP: {msg}. Nothing was read.")
    sys.exit(2)


def as_written(value, decimal, indian=False):
    """A number back in the founder's style: 4,500.5 / 4.500,5 / 4,50,000 (Indian grouping when they use it)."""
    neg = value < 0
    value = abs(value)
    whole = int(value)
    frac = round(value - whole, 2)
    digits = str(whole)
    if indian and len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        grouped = ",".join(groups + [tail])
    else:
        grouped = f"{whole:,}"
    dec = f"{frac:.2f}"[1:] if frac else ""
    if decimal == "comma":
        grouped = grouped.replace(",", ".")
        dec = dec.replace(".", ",")
    return ("-" if neg else "") + grouped + dec


def date_order_from_writing(text):
    """MDY or DMY from a date the founder wrote that can only be read one way (10/16 or 14/10), else None."""
    seen = set()
    for m in re.finditer(r"(?<![\d/.-])(\d{1,2})[/.-](\d{1,2})(?:[/.-](\d{2,4}))?(?![\d/.-])", text or ""):
        a, b = int(m.group(1)), int(m.group(2))
        if a > 12 and 1 <= b <= 12:
            seen.add("DMY")
        elif b > 12 and 1 <= a <= 12:
            seen.add("MDY")
    return seen.pop() if len(seen) == 1 else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--message", required=True, help="a file holding the founder's own messages, as typed")
    ap.add_argument("--country", help="the founder's country as an ISO code (US, GB, IN, AE, SG ...), if known")
    ap.add_argument("--price", help="the founder's price as they typed it")
    ap.add_argument("--length", help="the call's length or their usual call length, as they typed it")
    ap.add_argument("--percent", action="append", default=[], help="name=value, such as discount=20%%")
    ap.add_argument("--figure", action="append", default=[], help="name=value for any other figure the founder gave")
    ap.add_argument("--measure", help="measure.json, to set the founder's price against the call's")
    ap.add_argument("--json-out")
    a = ap.parse_args()
    if not os.path.exists(a.message):
        stop(f"there is no file at {a.message}")
    text = open(a.message, encoding="utf-8", errors="replace").read()
    samples = [text] + [x for x in (a.price, a.length) if x] + [p.partition("=")[2] for p in a.percent + a.figure]
    decimal = LN.detect_decimal_style(samples)
    indian = bool(re.search(r"\d{1,2},\d{2},\d{3}\b|\blakhs?\b|\bcrores?\b", text, re.I))
    asks, checks, notes = [], [], []
    out = {"decimal_style": decimal, "indian_grouping": indian}

    # ---------------------------------------------------------------- locale: from the country, never from spelling
    country = (a.country or "").strip().upper() or None
    written = date_order_from_writing(text)
    if country:
        loc = LN.locale_defaults(country)
        date_order = loc["date_order"]
        if written and written != date_order and date_order != "YMD":
            notes.append(f"your own dates read {DATE_STYLE[written]}, though {country} usually writes {DATE_STYLE[date_order]};"
                         f" the review follows how you wrote it")
            date_order = written
        out.update(country=country, paper=loc["paper"], clock=loc["clock"], date_style=DATE_STYLE[date_order],
                   locale_source="your country")
    elif written:
        out.update(country=None, paper="Letter" if written == "MDY" else "A4", clock=None, date_style=DATE_STYLE[written],
                   locale_source="a date you wrote; paper size assumed from it")
        notes.append(f"date order read from a date you wrote ({DATE_STYLE[written]}); say if you are based somewhere that uses "
                     "different paper")
    else:
        out.update(country=None, paper=None, clock=None, date_style=None, locale_source=None)
        asks.append("Which country are you based in? It sets the date order and paper size of your review.")

    def read(kind, raw):
        try:
            if kind == "money":
                v, cur, n = LN.parse_money(raw, decimal)
                return {"as_typed": raw, "value": v, "currency": cur, "notes": n,
                        "as_you_write": as_written(v, decimal, indian)}
            if kind == "percent":
                v, n = LN.parse_percent(raw, decimal)
                return {"as_typed": raw, "value": v, "notes": n, "as_you_write": as_written(v, decimal) + "%"}
            if kind == "minutes":
                t = raw.strip()
                if re.fullmatch(r"[~\d.,\s]+(?:ish)?|(?:about|around|roughly)\s+[\d.,]+", t, re.I):
                    v, n = LN.parse_number(t, decimal, allow_words=False)
                    n = n + ["a bare number is read as minutes"]
                else:
                    h, n = LN.parse_hours(t, decimal=decimal)
                    v = h * 60
                return {"as_typed": raw, "value": round(v, 1), "notes": n, "as_you_write": as_written(round(v), decimal) + " minutes"}
        except LN.Ambiguous as e:
            asks.append(f"{raw}: {e}")
        except LN.Unreadable:
            asks.append(f"I could not read '{raw}'. Could you restate it as a figure?")
        return None

    if a.price:
        p = read("money", a.price)
        out["price"] = p
        if p:
            if p["value"] <= 0:
                checks.append(f"a price of {p['as_you_write']} is not a price; what do you charge?")
            if p["currency"] and "_OR_" in p["currency"]:
                notes.append(f"'{a.price}' could be more than one currency ({p['currency'].replace('_OR_', ' or ')}); "
                             "it is shown exactly as you wrote it, never converted")
    if a.length:
        m = read("minutes", a.length)
        out["length"] = m
        if m and not 5 <= m["value"] <= 240:
            checks.append(f"a call of {m['as_you_write']} is not a usual sales call; how many minutes did it run?")
    out["percents"] = {}
    for x in a.percent:
        name, _s, raw = x.partition("=")
        r = read("percent", raw or name)
        out["percents"][name.strip() if raw else "percent"] = r
        if r and not 0 <= r["value"] <= 100:
            checks.append(f"{name.strip()} of {r['as_you_write']} is outside 0 to 100%; what was it?")
    out["figures"] = {}
    for x in a.figure:
        name, _s, raw = x.partition("=")
        out["figures"][name.strip()] = read("money", raw or name)

    # ---------------------------------------------------------------- the founder's price against the call's
    if a.measure and out.get("price"):
        try:
            mj = json.load(open(a.measure, encoding="utf-8"))
        except (OSError, ValueError):
            stop(f"{a.measure} is not a measure file from measure_call.py")
        said = [x for x in mj.get("prices", []) if x.get("role") == "seller" and isinstance(x.get("amount"), (int, float))]
        price_at = (mj.get("measures") or {}).get("price_said")
        mine = out["price"]["value"]
        on_call = [x for x in said if x["at"] == price_at] or said
        if on_call and not any(abs(x["amount"] - mine) < 0.5 for x in on_call):
            x = on_call[0]
            out["price_conflict"] = {"founder": a.price, "call": x["phrase"], "at": x["at"]}
            line = (f"you wrote {a.price}; the call says \"{x['phrase']}\" at {x['at']}. The review uses the call's figure "
                    "unless you correct it; say so in the readback")
            ratio = max(mine, x["amount"]) / max(min(mine, x["amount"]), 1e-9)
            (checks if ratio >= 10 else notes).append(line + ("; they differ tenfold or more, so confirm before scoring"
                                                              if ratio >= 10 else ""))
    for name, r in (out.get("figures") or {}).items():
        pv = (out.get("price") or {}) or {}
        if r and pv and pv.get("value") and r["value"] and pv["value"] / r["value"] >= 100:
            notes.append(f"{name} '{r['as_typed']}' is far below the price and has no unit; quote it as said and never "
                         "supply a unit for it")

    print("# Founder's figures, as typed")
    print(f"Decimal style: {decimal or 'not shown (no figure with a decimal or a group separator)'}"
          + ("; Indian grouping (lakh, crore)" if indian else ""))
    if out.get("date_style"):
        print(f"Date order: {out['date_style']}; paper: {out.get('paper')}; clock: {out.get('clock') or 'not known'} "
              f"(from {out.get('locale_source')})")
    for key in ("price", "length"):
        r = out.get(key)
        if r:
            cur = f", currency as written: {r['currency']}" if r.get("currency") else ""
            print(f"{key.capitalize()}: '{r['as_typed']}' reads {r['value']:g}{cur}; written back as {r['as_you_write']}"
                  + (f" ({'; '.join(r['notes'])})" if r.get("notes") else ""))
    for name, r in list(out["percents"].items()) + list(out["figures"].items()):
        if r:
            print(f"{name}: '{r['as_typed']}' reads {r['value']:g}; written back as {r['as_you_write']}")
    for n in notes:
        print(f"NOTE: {n}")
    for c in checks:
        print(f"CHECK: {c}")
    for q in asks:
        print(f"ASK: {q}")
    if a.json_out:
        out.update(asks=asks, checks=checks, notes=notes)
        os.makedirs(os.path.dirname(os.path.abspath(a.json_out)), exist_ok=True)
        json.dump(out, open(a.json_out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        print(f"WROTE: {a.json_out}")
    if asks or checks:
        print("Put these to the founder as one message before scoring (they count towards the five intake questions).")
        return 3
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print(f"STOP: the founder's figures could not be read ({type(e).__name__}: {e}). Ask the founder to restate them.")
        sys.exit(2)
