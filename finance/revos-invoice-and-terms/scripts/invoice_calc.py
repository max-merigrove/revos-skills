#!/usr/bin/env python3
"""Work out every figure, date and number on the invoice, check it is complete, and write the plan file.

Usage (paths relative to this skill's folder):
  python3 scripts/invoice_calc.py template                       print the inputs.json shape
  python3 scripts/invoice_calc.py plan <inputs.json> --out <plan.json>
        lines, discounts, tax per category exactly as the founder supplied it, rounding to the currency,
        totals, amounts paid, balance due, the stage plan and project summary, the next number, the
        issue and due dates, the IBAN check, the completeness checklist and any overdue reminder facts.
        Prints READY or DRAFT, then NEED:, ASK:, FLAG:, WARN: and DEFAULT: lines.

Exit 0 READY (or nothing to build), 1 DRAFT with NEED or ASK lines to put to the founder,
2 STOP (nothing usable was produced: fix the input or ask the question it names).
The model never adds, multiplies, rounds or counts days; this script does, and checks itself a second way.
Standard library only. No network calls. No tax rate, legal wording or country rule is built in.
"""
import argparse
import json
import os
import re
import sys
from datetime import date, timedelta
from decimal import Decimal
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402
import dates as D  # noqa: E402
import iban_check as IB  # noqa: E402
import labels as L  # noqa: E402
import locale_numbers as LN  # noqa: E402
import next_number as NN  # noqa: E402

TEMPLATE = {
    "today": "YYYY-MM-DD (the session date)",
    "mode": "invoice | credit_note | none (terms block or reminder only)",
    "country": "ISO code where the founder is, e.g. IE, US, IN, JP",
    "language": "invoice language, en by default",
    "english": "the founder's English, e.g. en-IE, en-US",
    "decimal_style": "dot | comma | null to detect from what they typed",
    "number_style": "indian for 2,11,770.00 grouping, else null",
    "grouping": "space | dot | comma | apostrophe | none, or null to follow how they typed (14 500,00 gives space)",
    "print_decimal": "dot | comma, only when they want figures printed differently from how they typed them",
    "date_format": "optional, e.g. 'yyyy/MM/dd', 'M/d/yyyy', 'd MMMM yyyy'",
    "currency": "ISO code, e.g. EUR",
    "issuer": {"name": "", "address": ["line", "line"], "email": "", "phone": "", "tax_number": "", "tax_number_label": "",
               "other_lines": []},
    "client": {"name": "", "address": ["line"], "contact": "", "email": "", "tax_number": "", "tax_number_label": "",
               "is_company": True},
    "client_reference": "PO or their reference, as given",
    "po_needed": "true | false | null (not asked yet)",
    "project_reference": "",
    "number": {"last": "the founder's last number", "explicit": None, "rollover": "restart | continue | null",
               "used": ["numbers already issued or voided"]},
    "issue_date": "as typed, null for today",
    "work_period": {"from": "as typed", "to": "as typed", "text": "or words, e.g. 'shoot completed 30 October 2026'"},
    "lines": [{"description": "the founder's words", "qty": "as typed", "unit": "", "unit_price": "as typed",
               "tax": "category id, or none for a line with no tax", "discount": "10% or an amount, optional", "stage": "stage number, optional"}],
    "discount": {"label": "", "value": "10% or an amount, before tax"},
    "tax": {"charged": False, "categories": [{"id": "A", "label": "the founder's word, e.g. VAT", "rate": "as supplied"}],
            "default": "A (lines with no tax set take it), or none", "prices_include_tax": False,
            "no_number": "true when the founder says there is no tax number to print", "rounding": "category | line", "wording": ["verbatim"]},
    "billing_plan": {"id": "", "name": "", "current_stage": 1,
                     "stages": [{"label": "Deposit", "share": "50%", "amount": None, "trigger": "on acceptance",
                                 "tax": "share | none", "number": None, "issue_date": None, "issued_total": None,
                                 "paid_date": None}]},
    "credits": {"number": "", "date": "", "reason": ""},
    "paid": [{"label": "Paid", "reference": "", "amount": "", "date": ""}],
    "terms": {"type": "days | eom_plus | end_next_month | next_month_day | on_receipt | fixed | in_advance",
              "days": "14", "date": "", "start": ""},
    "days_off": ["Sat", "Sun"],
    "holidays": ["dates the founder named"],
    "payment": {"fields": [["Account name", ""], ["IBAN", ""], ["BIC", ""]], "link": "", "reference": "",
                "confirm_changes_line": False},
    "late_fee": {"path": "none | agreed | new", "clause": "verbatim: the clause in their contract (agreed), or the fee they want in future terms in their own words (new)",
                 "source": "document and date (agreed only)"},
    "required_wording": ["verbatim lines the founder's accountant gave"],
    "notes": ["short notes the founder asked for"],
    "labels": {},
    "logo": None, "colour": None, "font": None,
    "quoted_total": None,
    "overdue": [{"number": "", "client": "", "contact": "", "amount": "", "currency": "", "due": "", "pay_by": None}],
    "founder_name": "",
    "confirmed": ["keys of plausibility stops the founder confirmed"],
    "open_questions": ["each question still open in your reply that could change this invoice; it stays DRAFT until answered"],
}

UNTAXED = ""
NO_TAX = {"none", "no", "no tax", "untaxed", "0", "null", "-", "n/a", "na"}
DAY_NAMES = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


class Plan:
    def __init__(self, inp):
        self.inp = inp
        self.needs, self.asks, self.flags, self.warns, self.defaults = [], [], [], [], []
        self.confirmed = set(inp.get("confirmed") or [])

    def need(self, s):
        if s not in self.needs:
            self.needs.append(s)

    def plaus(self, key, msg):
        if key not in self.confirmed:
            raise C.Stop(f"please check: {msg} If the founder confirms it, add \"{key}\" to \"confirmed\" and run again")


def _lines_of(v):
    if not v:
        return []
    if isinstance(v, str):
        return [x.strip() for x in re.split(r"\n|,(?![^()]*\))", v) if x.strip()]
    return [str(x).strip() for x in v if str(x).strip()]


def collect_samples(inp):
    s = []
    for ln in inp.get("lines") or []:
        s += [ln.get("unit_price"), ln.get("qty"), ln.get("discount")]
    for p in inp.get("paid") or []:
        s.append(p.get("amount"))
    for o in inp.get("overdue") or []:
        s.append(o.get("amount"))
    bp = inp.get("billing_plan") or {}
    for st in bp.get("stages") or []:
        s += [st.get("amount"), st.get("issued_total")]
    s.append(inp.get("quoted_total"))
    return [x for x in s if isinstance(x, str)]


def compute(inp):
    P = Plan(inp)
    today = D.parse_iso(inp.get("today") or "") or date.today()
    mode = (inp.get("mode") or "invoice").strip().lower()
    if mode not in ("invoice", "credit_note", "none"):
        raise C.Stop(f"mode '{mode}' must be invoice, credit_note or none")
    country = (inp.get("country") or "").strip().upper()
    loc = LN.locale_defaults(country)
    if loc["assumed"]:
        P.asks.append("ASK: which country are you in? It sets the date order and the paper size. Default: A4, day first")
    language = (inp.get("language") or "en").strip()
    labels, lprobs = L.resolve(language, inp.get("labels"))
    if lprobs:
        raise C.Stop("; ".join(lprobs))
    fb = L.fallback_keys(language, inp.get("labels"))
    if fb and (inp.get("billing_plan") or any(str((l or {}).get("tax") or "").lower() in NO_TAX for l in inp.get("lines") or [])):
        P.warns.append(f"WARN: labels {', '.join(fb)} are not in your {language} set, so they print in English. "
                       "Add them to \"labels\" (print the English set with scripts/labels.py)")
    months, weekdays = labels["months"], labels["weekdays"]
    order = loc["date_order"]
    pattern = inp.get("date_format") or D.default_format(country, language)
    us_style = order == "MDY"

    def dtext(d):
        return D.fmt(d, pattern, months)

    def dwk(d):
        return D.fmt_weekday(d, pattern, months, weekdays, us_style, language)

    samples = collect_samples(inp)
    style = C.style_from(samples, inp.get("decimal_style"))
    seen_styles = [C.sample_style(x) for x in samples]
    decs = [d for d, _g in seen_styles if d]
    if style is None and decs:
        style = decs[0]  # mixed: the first figure with decimals sets it, and the founder hears which
        other = "1,234.56" if style == "comma" else "1 234,56 or 1.234,56"
        P.defaults.append(f"DEFAULT: you wrote figures more than one way; the invoice prints them like your first one "
                          f"({next(x for x in samples if C.sample_style(x)[0] == style).strip()}). Say if you prefer {other}")
    # how figures are printed: as the founder typed them, unless they asked for another style
    pstyle = inp.get("print_decimal") if inp.get("print_decimal") in ("dot", "comma") else style
    group = C.GROUPS.get(str(inp.get("grouping") or "").lower())
    if group is None:
        grps = [g for d, g in seen_styles if g and (d in (None, style))]
        if "space" in grps:
            group = C.GROUPS["space"]
        elif "apostrophe" in grps:
            group = C.GROUPS["apostrophe"]
    currency = (inp.get("currency") or "").strip().upper()
    if not currency:
        seen = {LN.find_currency(str(x)) for x in collect_samples(inp)} - {None}
        codes = {c for c in seen if c in C.KNOWN_CODES}
        if len(codes) == 1:
            currency = codes.pop()
            P.defaults.append(f"DEFAULT: currency {currency}, from the amounts you typed")
        elif seen:
            fam = sorted(seen)[0]
            raise C.Stop(f"the currency is not clear ('{fam}'). Ask the founder for the three-letter code, e.g. USD, AUD, SGD")
    if currency and currency not in C.KNOWN_CODES:
        raise C.Stop(f"'{currency}' is not a currency code. Ask the founder for the three-letter code")
    indian = (inp.get("number_style") == "indian") or (country == "IN" and inp.get("number_style") is None)
    M = C.Money(currency or "XXX", pstyle or "dot", group=group, indian=indian)
    mu = M.mu
    out = {"version": 1, "today": today.isoformat(), "mode": mode, "country": country, "language": language,
           "english": inp.get("english") or "en", "paper": loc["paper"], "date_pattern": pattern,
           "decimal_style": pstyle or "dot", "group": M.group, "indian": indian, "currency": currency, "minor_units": mu,
           "labels": labels, "credit": C.CREDIT, "font": inp.get("font"), "colour": inp.get("colour"),
           "logo": inp.get("logo")}

    days_off = [DAY_NAMES[str(x).lower()[:3]] for x in (inp.get("days_off") or ["Sat", "Sun"]) if str(x).lower()[:3] in DAY_NAMES]
    if not inp.get("days_off"):
        P.defaults.append("DEFAULT: Saturday and Sunday are your days off; no public holidays allowed for unless you name them")
    holidays = []
    for h in inp.get("holidays") or []:
        holidays.append(D.read_date(h, order, today, months=months))

    # ---- overdue reminders (any mode)
    out["reminders"] = reminders(inp, P, today, order, months, dtext, dwk, style, indian, days_off, holidays, currency, group, pstyle)

    if mode == "none":
        out["status"] = "NONE"
        out["doc"] = None
        out["terms"] = terms_info(inp, P, None, None, labels, dwk)
        out["billing_plan"] = plan_outline(inp, P, style)
        finish(out, P)
        return out

    if not currency:
        P.need("NEED: the currency (a three-letter code such as EUR, USD, INR)")
        M = C.Money("XXX", pstyle or "dot", group=group, indian=indian)

    # ---- dates
    issue = today
    if inp.get("issue_date"):
        asked = D.read_date(inp["issue_date"], order, today, months=months)
        if asked < today:
            P.flags.append(f"FLAG: backdating refused. An invoice is dated the day it is issued, so this one is dated "
                           f"{dtext(today)}, not {dtext(asked)}. The dates the work was done go on their own line")
        elif asked > today + timedelta(days=30):
            P.plaus("issue_far_future", f"the invoice date {dtext(asked)} is over 30 days away.")
            issue = asked
        else:
            issue = asked
    out["issue_date"] = issue.isoformat()

    # ---- number
    num_in = inp.get("number") or {}
    used = [str(u) for u in (num_in.get("used") or [])]
    explicit = num_in.get("explicit")
    if explicit:
        if str(explicit) in used:
            raise C.Stop(f"{explicit} is already issued or voided in the register; a number is never reused. Use the next one")
        number = str(explicit)
    elif num_in.get("last"):
        number, notes = NN.next_after(num_in["last"], issue.year, num_in.get("rollover"), used)
        for n in notes:
            (P.asks if n.startswith("ASK") else P.flags).append(n)
    else:
        number = NN.first_number(num_in.get("prefix"))
        P.asks.append(f"ASK: what was your last invoice number? I have started at {number}; if you have invoiced before, "
                      "the sequence should carry on from your last one")
    preview = bool(inp.get("preview"))
    if preview:
        number = ""
        P.flags.append("FLAG: preview only: no number is used and no date is set until this stage is issued")
    out["number"] = number

    # ---- tax setup (founder supplied only)
    tax = inp.get("tax") or {}
    charged = bool(tax.get("charged")) and bool(tax.get("categories"))
    cats = {}
    if charged:
        for c in tax["categories"]:
            cid = str(c.get("id") or c.get("label") or "A")
            if c.get("rate") in (None, ""):
                P.need(f"NEED: the rate for '{c.get('label') or cid}', from your accountant")
                rate = None
            else:
                rate = C.read_percent(c["rate"], style, f"the {c.get('label', 'tax')} rate")
                if rate < 0 or rate > 30:
                    P.plaus(f"tax_rate_{cid}", f"a {c.get('label', 'tax')} rate of {rate}% is outside 0 to 30.")
            label = str(c.get("label") or "").strip()
            if not label:
                P.need("NEED: the name of the tax as your accountant writes it (VAT, GST, sales tax or similar)")
            cats[cid] = {"id": cid, "label": label, "rate": rate}
    elif tax.get("charged") and not tax.get("categories"):
        P.need("NEED: the tax name and rate your accountant gave you")
    raw_default = tax.get("default")
    if charged and raw_default is not None and str(raw_default).strip().lower() in NO_TAX:
        default_cat = UNTAXED
    else:
        default_cat = str(raw_default or (next(iter(cats)) if cats else ""))
    inclusive = bool(tax.get("prices_include_tax"))
    if inclusive and not charged:
        raise C.Stop("prices are marked as including tax but no tax rate was supplied. Ask the founder for the rate")
    rounding = "line" if tax.get("rounding") == "line" else "category"
    out["tax_setup"] = {"charged": charged, "categories": [{"id": k, "label": v["label"], "rate": str(v["rate"]) if v["rate"] is not None else None}
                                                           for k, v in cats.items()],
                        "prices_include_tax": inclusive, "rounding": rounding, "wording": list(tax.get("wording") or []),
                        "source": "supplied by you"}
    if not charged and (inp.get("issuer") or {}).get("tax_number") and not tax.get("confirmed_none"):
        P.asks.append("ASK: you gave a tax registration number. Do you charge tax on this invoice? If so: its name, the rate "
                      "your accountant gave you, whether your prices already include it, and any line treated differently. "
                      "Default: no tax lines")
    if not charged:
        P.defaults.append("DEFAULT: no tax lines. Enter prices before any sales tax (VAT, GST or similar); ask your accountant whether you need to charge it")

    def rate_text(r):
        if r is None:
            return "[NEED: rate]"
        s = format(Decimal(r).normalize(), "f")
        return (s.replace(".", ",") if (pstyle == "comma") else s) + "%"

    # ---- lines
    raw_lines = inp.get("lines") or []
    if not raw_lines:
        P.need("NEED: what the invoice is for: at least one line with a description and a price")
    lines = []
    defaulted = []
    for i, ln in enumerate(raw_lines, 1):
        desc = str(ln.get("description") or "").strip()
        why = C.vague_description(desc)
        if why:
            P.need(f"NEED: line {i} ('{desc or 'no description'}') is {why}. What was the work, in a few words, with when it happened?")
        qty = C.read_qty(ln.get("qty"), style, f"the quantity on line {i}")
        if qty <= 0:
            raise C.Stop(f"the quantity on line {i} is {qty}. Use a credit note to take something off")
        if qty > 10000:
            P.plaus(f"qty_{i}", f"line {i} has a quantity of {qty}.")
        if ln.get("unit_price") in (None, ""):
            P.need(f"NEED: the price for line {i} ('{desc}')")
            price = Decimal(0)
        else:
            price = C.read_amount(ln.get("unit_price"), style, f"the price on line {i}")
            if price < 0:
                raise C.Stop(f"the price on line {i} is negative. Use the invoice discount or a credit note instead")
            if mu and price < 1:
                P.plaus(f"unit_price_{i}", f"line {i} costs {price} {currency}, under one unit of the currency.")
        amount = C.to_minor(qty * price, currency)
        disc_minor = 0
        disc_text = None
        if ln.get("discount") not in (None, ""):
            disc_minor, disc_text = read_discount(ln["discount"], amount, style, currency, f"the discount on line {i}")
        if not charged:
            cat = UNTAXED
        elif ln.get("tax") in (None, ""):
            cat = default_cat
            if cat != UNTAXED:
                defaulted.append(i)
        elif str(ln["tax"]).strip().lower() in NO_TAX:
            cat = UNTAXED
        else:
            cat = str(ln["tax"]).strip()
        if charged and cat != UNTAXED and cat not in cats:
            raise C.Stop(f"line {i} uses tax category '{cat}', which is not in the tax setup. Use one of {', '.join(cats)}, "
                         "or \"none\" for a line that carries no tax")
        lines.append({"n": i, "description": desc, "unit": ln.get("unit") or "", "qty": str(qty), "price": str(price),
                      "gross_minor": amount, "discount_minor": disc_minor, "discount_text": disc_text,
                      "amount_minor": amount - disc_minor, "tax": cat, "stage": ln.get("stage")})

    untaxed_n = [l["n"] for l in lines if charged and l["tax"] == UNTAXED]
    if charged and untaxed_n and defaulted:
        dc = cats[default_cat]
        P.defaults.append(f"DEFAULT: line{'s' if len(defaulted) > 1 else ''} {', '.join(map(str, defaulted))} had no tax set, so "
                          f"{'they carry' if len(defaulted) > 1 else 'it carries'} {dc['label']} {rate_text(dc['rate'])} (the default). "
                          "Set \"tax\": \"none\" on any line with no tax")
    if untaxed_n:
        P.defaults.append(f"DEFAULT: line{'s' if len(untaxed_n) > 1 else ''} {', '.join(map(str, untaxed_n))} carr{'y' if len(untaxed_n) > 1 else 'ies'} "
                          "no tax, as you said; the tax column shows a dash. Confirm with your accountant")

    # ---- invoice discount, spread over the lines in proportion (largest remainder), before tax
    inv_disc = 0
    inv_disc_label = None
    d_in = inp.get("discount")
    if d_in and (d_in.get("value") not in (None, "")):
        base = sum(l["amount_minor"] for l in lines)
        inv_disc, txt = read_discount(d_in["value"], base, style, currency, "the invoice discount")
        inv_disc_label = (d_in.get("label") or labels["discount"]) + (f" {txt}" if txt and txt.endswith("%") else "")
        spread(lines, inv_disc, "inv_disc_minor")
    for l in lines:
        l.setdefault("inv_disc_minor", 0)
        l["net_minor"] = l["amount_minor"] - l["inv_disc_minor"]

    # ---- tax-inclusive prices: back the net out of each line
    if inclusive:
        for l in lines:
            r = (cats[l["tax"]]["rate"] or Decimal(0)) if l["tax"] in cats else Decimal(0)
            gross = l["net_minor"]
            l["incl_gross_minor"] = gross
            l["net_minor"] = C.to_minor(Decimal(gross) / (1 + r / 100) / (10 ** mu), currency)
        P.flags.append("FLAG: prices entered including tax, as you said; the net is worked back from your rate. Confirm with your accountant")

    # ---- billing plan (deposit and stages)
    bp = inp.get("billing_plan")
    stage_info = None
    project = None
    if bp and bp.get("stages"):
        stage_info, project = stage_plan(bp, lines, cats, charged, inclusive, rounding, currency, mu, style, P)
        if inp.get("preview"):  # a preview may sit after stages not issued yet; they are named, not gaps
            P.needs = [n for n in P.needs if "the invoice number used for stage" not in n]

    # ---- this invoice's lines and tax
    sign = -1 if mode == "credit_note" else 1
    if stage_info:
        cur = stage_info["current"]
        doc_lines = cur["lines"]
        cat_net = cur["cat_net"]
        cat_tax = cur["cat_tax"]
    else:
        doc_lines = [{"description": l["description"], "qty": l["qty"], "price": l["price"], "unit": l["unit"],
                      "amount_minor": l["amount_minor"], "discount_minor": l["discount_minor"],
                      "discount_text": l["discount_text"], "gross_minor": l["gross_minor"], "tax": l["tax"],
                      "net_minor": l["net_minor"], "incl_gross_minor": l.get("incl_gross_minor")} for l in lines]
        cat_net, cat_tax = tax_by_category(lines, cats, charged, inclusive, rounding, currency, mu)

    if stage_info:
        subtotal = sum(l["amount_minor"] for l in doc_lines)
        inv_disc_this = 0
        net_total = sum(cat_net.values())
        tax_total = sum(cat_tax.values())
        total = net_total + tax_total
    elif inclusive:
        subtotal = sum(l["amount_minor"] for l in doc_lines)
        inv_disc_this = inv_disc
        total = subtotal - inv_disc
        tax_total = sum(cat_tax.values())
        net_total = total - tax_total
        if sum(cat_net.values()) + tax_total != total:
            raise C.Stop("internal check failed: tax-inclusive lines do not add back. Nothing was produced")
    else:
        subtotal = sum(l["amount_minor"] for l in doc_lines)
        inv_disc_this = inv_disc
        net_total = subtotal - inv_disc
        tax_total = sum(cat_tax.values()) if charged else 0
        total = net_total + tax_total
        if charged and sum(cat_net.values()) != net_total:
            raise C.Stop("internal check failed: the subtotal less the discount does not equal the net. Nothing was produced")

    # ---- paid against this invoice
    paid_rows = []
    paid_total = 0
    for p in inp.get("paid") or []:
        amt = C.to_minor(C.read_amount(p.get("amount"), style, "an amount already paid"), currency)
        pdate = D.read_date(p["date"], order, today, prefer="past", months=months) if p.get("date") else None
        paid_rows.append({"label": p.get("label") or labels["paid"], "reference": p.get("reference") or "",
                          "date": pdate.isoformat() if pdate else None, "minor": amt})
        paid_total += amt
    if paid_total > total:
        raise C.Stop("the amounts already paid are larger than the invoice total. Check the figures with the founder")
    due_minor = total - paid_total

    if total == 0 and lines:
        P.plaus("zero_total", "the invoice total is zero.")
    if inp.get("quoted_total") not in (None, ""):
        q = C.to_minor(C.read_amount(inp["quoted_total"], style, "the total you mentioned"), currency)
        if stage_info:
            cands = {"project total": project["total"], "project subtotal before tax": project["net"]}
        else:
            cands = {"total": total, "subtotal before tax": net_total}
        cands["amount due"] = due_minor
        if all(abs(q - v) > 1 for v in cands.values()):
            what = "project" if stage_info else "lines"
            P.flags.append(f"FLAG: you mentioned {M.full(q)}; the {what} give a subtotal before tax of "
                           f"{M.full(cands.get('project subtotal before tax', cands.get('subtotal before tax')))} and a total of "
                           f"{M.full(cands.get('project total', cands.get('total')))}, so neither matches (a gap of "
                           f"{M.full(abs(q - cands.get('project subtotal before tax', cands.get('subtotal before tax'))))} on the "
                           "subtotal). Check which is right before sending")
            if "quoted_total" not in P.confirmed:
                P.asks.append("ASK: your figure and the lines disagree; which is right? (When they confirm the lines, "
                              "set quoted_total to null or add \"quoted_total\" to confirmed.) Default: the lines")

    # ---- due date
    C_terms = dict(inp.get("terms") or {})
    if not C_terms:
        C_terms = {"type": "days", "days": "14"}
        P.defaults.append("DEFAULT: due 14 days from the invoice date (change it if your agreement says otherwise)")
    due, tnotes = D.resolve_due(issue, C_terms, order, today, months)
    P.flags += tnotes
    warn = D.day_off_warning(due, days_off, holidays)
    if warn:
        P.warns.append(f"WARN: the due date {dwk(due)} {warn}. It is not moved; change the terms if you want a working day")
    out["due_date"] = due.isoformat()

    # ---- work period
    wp = inp.get("work_period") or {}
    work_text = ""
    if wp.get("text"):
        work_text = str(wp["text"]).strip()
    elif wp.get("from"):
        a = D.read_date(wp["from"], order, today, prefer="past", months=months)
        b = D.read_date(wp["to"], order, today, prefer="past", months=months) if wp.get("to") else None
        if b and b < a:
            raise C.Stop("the work period ends before it starts. Check the dates with the founder")
        work_text = D.fmt_range(a, b, pattern, months, labels["range_joiner"])
        out["work_from"], out["work_to"] = a.isoformat(), (b or a).isoformat()
    if not work_text:
        P.need("NEED: the date or period the work covers (it goes on its own line, separate from the invoice date)")
    elif not re.search(r"\d", work_text) and not preview:
        P.need("NEED: a date in the Work covered line (when the work was done; for a deposit, when the proposal was "
               "accepted or the work starts)")

    # ---- parties
    iss = inp.get("issuer") or {}
    cli = inp.get("client") or {}
    if not str(iss.get("name") or "").strip():
        P.need("NEED: your business name as it should appear at the top")
    if not _lines_of(iss.get("address")):
        P.need("NEED: your business address")
    if not str(cli.get("name") or "").strip():
        P.need("NEED: the client's name (the company, or the person paying)")
    if not _lines_of(cli.get("address")):
        P.need(f"NEED: {cli.get('name') or 'the client'}'s address")
    if not (iss.get("email") or iss.get("phone")):
        P.warns.append("WARN: no email or phone for you on the invoice; the client's accounts team may need one")
    if not (cli.get("email") or cli.get("contact")) and cli.get("is_company", True):
        P.warns.append("WARN: no contact or accounts email for the client; check who pays the bill")
    if cli.get("is_company", True) and not inp.get("client_reference") and inp.get("po_needed") is None:
        P.asks.append(f"ASK: does {cli.get('name') or 'the client'}'s accounts team need a PO number or reference on it? Default: no")
    if inp.get("po_needed") and not inp.get("client_reference"):
        P.need("NEED: the client's PO number or reference")
    if charged and any(c["rate"] == 0 and any(l["tax"] == cid for l in lines) for cid, c in cats.items()) and not out["tax_setup"]["wording"]:
        P.warns.append("WARN: a line carries 0% tax. If your accountant gives you wording that explains it, add it and it "
                       "prints exactly as given; accounts teams often ask")
    if charged and not iss.get("tax_number") and not tax.get("no_number"):
        P.warns.append("WARN: you charge tax but gave no tax registration number to print; your accountant can say whether it must appear")

    # ---- payment details
    pay = inp.get("payment") or {}
    fields = []
    iban_result = None
    for f in pay.get("fields") or []:
        if not isinstance(f, (list, tuple)) or len(f) != 2:
            raise C.Stop("payment fields must be pairs like [\"IBAN\", \"IE29 ...\"]")
        lab, val = str(f[0]).strip(), str(f[1]).strip()
        if not val:
            continue
        if "iban" in lab.lower() or (IB.looks_like_iban(val) and "account" not in lab.lower()):
            ok, why, grouped = IB.check(val)
            iban_result = {"ok": ok, "why": why, "grouped": grouped}
            if not ok:
                P.need(f"NEED: the IBAN {grouped} fails its check digits ({why}). Re-read it from your bank and send it again")
                val = "[NEED: IBAN, re-read from your bank]"
            else:
                val = grouped
        fields.append([lab, val])
    link = str(pay.get("link") or "").strip()
    norm = lambda x: re.sub(r"[^a-z0-9]", "", str(x or "").lower())
    for lab, val in fields:
        if re.search(r"(?i)name|holder|inhaber|titular|titulaire|beneficiary", lab) and iss.get("name") and norm(val) != norm(iss["name"]):
            P.warns.append(f"WARN: the account name '{val}' differs from your business name '{iss['name']}' on the invoice. "
                           "Accounts teams check that they match; if the account is held by a company name, consider showing it in your details")
    if not fields and not link:
        P.need("NEED: how the client should pay: your account details or a payment link")
    reference = str(pay.get("reference") or number).strip()

    # ---- late fee
    lf = inp.get("late_fee") or {}
    path = (lf.get("path") or "none").lower()
    late_line = None
    if path == "agreed":
        if lf.get("clause") and lf.get("source"):
            late_line = labels["late_fee_agreed"].format(source=str(lf["source"]).strip(), clause=str(lf["clause"]).strip())
        else:
            P.flags.append("FLAG: a late fee that first appears on an invoice may not be one the client agreed. "
                           "This invoice shows the due date only; put the fee in your terms before the next job")
            path = "none"
    elif path == "new" and int(((inp.get("billing_plan") or {}).get("current_stage")) or 1) <= 1:
        if lf.get("clause"):
            P.flags.append("FLAG: your late fee is kept off this invoice, because this client never agreed to it; a fee that "
                           "first appears on an invoice seldom gets paid. Your own wording goes into your payment terms for the "
                           "next contract (terms_block.py); check with your lawyer that you can charge it where you and your clients are")
        else:
            P.flags.append("FLAG: a new late fee is kept off this invoice. The figure, and whether you can charge it where "
                           "you and your client are, come from your lawyer; it goes in your terms before the work starts")

    # ---- terms text
    tkind = C_terms.get("type") or "days"
    tpl = labels.get(f"terms_{tkind}") or labels["terms_fixed"]
    days_val = C_terms.get("days")
    terms_lines = [tpl.format(days=str(days_val or "").strip(), due=dwk(due))]
    if late_line:
        terms_lines.append(late_line)

    # ---- notes and wording, verbatim
    notes = []
    for w in out["tax_setup"]["wording"]:
        notes.append(str(w).strip())
    for w in inp.get("required_wording") or []:
        notes.append(str(w).strip())
    for w in inp.get("notes") or []:
        notes.append(str(w).strip())
    if inclusive:
        pass  # the flag is for the founder, not the client
    footer = []
    if pay.get("confirm_changes_line"):
        footer.append(labels["bank_change_line"])

    # ---- credit note
    credits = None
    if mode == "credit_note":
        cr = inp.get("credits") or {}
        if not cr.get("number"):
            P.need("NEED: the number of the invoice this credit note reverses")
        cdate = D.read_date(cr["date"], order, today, prefer="past", months=months) if cr.get("date") else None
        if not cdate:
            P.need("NEED: the date of the invoice this credit note reverses")
        credits = {"number": cr.get("number"), "date": cdate.isoformat() if cdate else None,
                   "text": labels["credits_invoice"].format(number=cr.get("number") or "[NEED]", date=dtext(cdate) if cdate else "[NEED]"),
                   "reason": labels["credit_reason"].format(reason=cr["reason"]) if cr.get("reason") else None}
        P.flags.append("FLAG: ask your accountant whether to correct with a credit note and a new invoice, as here, or another way where you are")

    # ---- printable lines and totals
    psum = None
    if stage_info:
        psum = project_summary(stage_info, project, labels, M, dtext, number, issue, preview)
    has_tax_col = charged and (len(cats) > 1 or any(l["tax"] == UNTAXED for l in lines))
    pl = []
    for l in doc_lines:
        desc = l["description"]
        if l.get("discount_text"):
            desc = f"{desc} ({labels['discount'].lower()} {l['discount_text']})"
        qty_t = C.qty_text(Decimal(l["qty"]), M) + (f" {l['unit']}" if l.get("unit") else "")
        amt = sign * l["amount_minor"]
        pl.append({"description": desc, "qty": qty_t, "unit_price": C.unit_price_text(Decimal(l["price"]) * sign, M) if not l.get("stage_line") else M.num(amt),
                   "amount": M.num(amt), "amount_minor": amt,
                   "stage_line": bool(l.get("stage_line")),
                   "tax": (f"{cats[l['tax']]['label']} {rate_text(cats[l['tax']]['rate'])}" if charged and l.get("tax") in cats
                           else (labels["untaxed_mark"] if charged else ""))})
    totals = [{"key": "subtotal", "label": labels["subtotal"], "minor": sign * subtotal, "text": M.full(sign * subtotal)}]
    tax_rows = []
    if inv_disc_this:
        totals.append({"key": "discount", "label": inv_disc_label, "minor": -sign * inv_disc_this, "text": M.full(-sign * inv_disc_this)})
    if charged:
        for cid, c in cats.items():
            if cid in cat_net:
                lab = f"{c['label']} {rate_text(c['rate'])}"
                if inclusive:
                    lab = f"{labels['includes']} {lab}"
                else:
                    lab = labels["tax_line"].format(label=c["label"], rate=rate_text(c["rate"]), net=M.num(sign * cat_net[cid]))
                tax_rows.append({"key": f"tax_{cid}", "label": lab, "minor": sign * cat_tax[cid], "text": M.full(sign * cat_tax[cid]),
                               "net_text": M.num(sign * cat_net[cid])})
    if inclusive:
        totals.append({"key": "total", "label": labels["total"], "minor": sign * total, "text": M.full(sign * total)})
        totals += tax_rows
    else:
        totals += tax_rows
        totals.append({"key": "total", "label": labels["total"], "minor": sign * total, "text": M.full(sign * total)})
    for p in paid_rows:
        d_ = D.parse_iso(p["date"]) if p["date"] else None
        lab = labels["paid_line"].format(label=p["label"], ref=p["reference"], date=dtext(d_) if d_ else "").strip()
        lab = re.sub(r"\s+", " ", lab)
        totals.append({"key": "paid", "label": lab, "minor": -p["minor"], "text": M.full(-p["minor"])})
    due_label = labels["amount_credited"] if mode == "credit_note" else labels["amount_due"]
    totals.append({"key": "amount_due", "label": due_label, "minor": sign * due_minor, "text": M.full(sign * due_minor)})

    for q in inp.get("open_questions") or []:
        if str(q).strip():
            P.asks.append(f"ASK: {str(q).strip()}")

    # ---- checklist extras
    if mode == "invoice" and not reference and not preview:
        P.need("NEED: a payment reference")

    status = "PREVIEW" if preview else ("DRAFT" if (P.needs or P.asks) else "READY")
    client_name = str(cli.get("name") or "Client").strip()
    title_word = labels["credit_note"] if mode == "credit_note" else labels["invoice"]
    base = C.safe_filename(f"{title_word} {number} {client_name} {issue.isoformat()}")
    if preview and stage_info:
        base = C.safe_filename(f"Preview {title_word} {client_name} stage {stage_info['current']['index']} of {stage_info['current']['count']}")
    doc = {
        "type": mode, "title": title_word, "status": status, "number": number,
        "number_label": labels["credit_number"] if mode == "credit_note" else labels["number"],
        "date_label": labels["credit_date"] if mode == "credit_note" else labels["date"],
        "issue_text": dtext(issue), "due_text": dwk(due) if mode != "credit_note" else "",
        "po": str(inp.get("client_reference") or "").strip(),
        "project_ref": str(inp.get("project_reference") or (bp or {}).get("name") or "").strip(),
        "issuer": party(iss, labels, "your business"), "client": party(cli, labels, "the client's"), "work_text": work_text,
        "has_tax_col": has_tax_col, "lines": pl, "totals": totals, "amount_due_text": M.full(sign * due_minor),
        "project_summary": psum, "stage_heading": stage_info["current"]["heading"] if stage_info else None,
        "still_to_come": (stage_info["current"].get("still_to_come") or []) if stage_info else [],
        "compact_lines": bool(pl) and all(x["stage_line"] for x in pl),
        "payment": fields if mode != "credit_note" else [], "payment_link": link if mode != "credit_note" else "",
        "reference": reference if mode != "credit_note" else "",
        "terms": terms_lines if mode != "credit_note" else [], "notes": notes, "footer": footer, "credits": credits,
        "currency": currency, "file_base": base, "preview": preview,
    }
    out["doc"] = doc
    out["status"] = status
    out["figures"] = {"subtotal": subtotal * sign, "discount": inv_disc_this, "net": net_total * sign,
                      "tax": {k: v * sign for k, v in cat_tax.items()}, "tax_total": tax_total * sign,
                      "total": total * sign, "paid": paid_total, "due": due_minor * sign,
                      "lines": [l["amount_minor"] for l in pl]}
    out["iban"] = iban_result
    out["late_fee"] = {"path": path, "clause": lf.get("clause"), "source": lf.get("source")}
    out["terms"] = terms_info(inp, P, C_terms, due, labels, dwk)
    out["billing_plan"] = stage_info["public"] if stage_info else None
    out["project"] = project
    out["register_row"] = {
        "number": number, "type": ("credit note" if mode == "credit_note" else ("stage" if stage_info else "invoice")),
        "client": client_name, "project": doc["project_ref"] or (bp or {}).get("name") or "",
        "issue_date": issue.isoformat(), "due_date": due.isoformat() if mode != "credit_note" else "",
        "currency": currency, "net": net_total * sign, "tax": tax_total * sign, "total": total * sign,
        "paid": paid_total, "status": "draft" if status == "DRAFT" else "issued", "po": doc["po"],
        "file": base + ".pdf"}
    out["chat"] = {"total": M.full(sign * total), "due": M.full(sign * due_minor), "due_date": dwk(due),
                   "issue_date": dtext(issue), "number": number, "client": client_name,
                   "tax_lines": [f"{t['label']}: {M.full(t['minor'])}" for t in totals if t["key"].startswith("tax_")]}
    selfcheck(out, lines, cats, charged, inclusive, rounding, mu, stage_info, sign, paid_total, inv_disc if not stage_info else 0)
    finish(out, P)
    return out


def party(p, labels, who="your"):
    lines = [str(p.get("name") or "").strip()] if p.get("name") else [f"[NEED: {who} name]"]
    if not _lines_of(p.get("address")):
        lines.append(f"[NEED: {who} address]")
    if p.get("contact") and p.get("contact") != p.get("name"):
        lines.append(str(p["contact"]).strip())
    lines += _lines_of(p.get("address"))
    for k in ("email", "phone"):
        if p.get(k):
            lines.append(str(p[k]).strip())
    if p.get("tax_number"):
        lines.append(f"{(p.get('tax_number_label') or labels['tax_number']).strip()}: {str(p['tax_number']).strip()}")
    lines += _lines_of(p.get("other_lines"))
    return [x for x in lines if x]


def read_discount(v, base_minor, style, currency, what):
    s = str(v).strip()
    if s.endswith("%") or re.search(r"(?i)percent|per cent", s):
        pct = C.read_percent(s, style, what)
        if pct < 0 or pct > 100:
            raise C.Stop(f"{what} of {pct}% is not between 0 and 100")
        amt = C.to_minor(Decimal(base_minor) * pct / 100 / (10 ** C.minor_units(currency)), currency)
        return amt, s
    amt = C.to_minor(C.read_amount(s, style, what), currency)
    if amt > base_minor:
        raise C.Stop(f"{what} is larger than the amount it applies to")
    return amt, None


def spread(lines, amount, key):
    """Share an amount over lines in proportion to amount_minor, largest remainder, so it adds back exactly."""
    base = sum(l["amount_minor"] for l in lines)
    if base == 0:
        for l in lines:
            l[key] = 0
        return
    shares = []
    for l in lines:
        fr = Fraction(amount * l["amount_minor"], base)
        shares.append([int(fr), fr - int(fr), l])
    left = amount - sum(s[0] for s in shares)
    for s in sorted(shares, key=lambda s: s[1], reverse=True)[:left]:
        s[0] += 1
    for s in shares:
        s[2][key] = s[0]


def tax_by_category(lines, cats, charged, inclusive, rounding, currency, mu):
    cat_net, cat_tax = {}, {}
    if not charged:
        return {"": sum(l["net_minor"] for l in lines)}, {}
    for l in lines:
        cat_net[l["tax"]] = cat_net.get(l["tax"], 0) + l["net_minor"]
    for cid, net in cat_net.items():
        if cid == UNTAXED:
            continue
        r = cats[cid]["rate"] or Decimal(0)
        if inclusive:
            gross = sum(l["incl_gross_minor"] for l in lines if l["tax"] == cid)
            cat_tax[cid] = gross - net
        elif rounding == "line":
            cat_tax[cid] = sum(C.to_minor(Decimal(l["net_minor"]) * r / 100 / (10 ** mu), currency) for l in lines if l["tax"] == cid)
        else:
            cat_tax[cid] = C.to_minor(Decimal(net) * r / 100 / (10 ** mu), currency)
    return cat_net, cat_tax


def stage_plan(bp, lines, cats, charged, inclusive, rounding, currency, mu, style, P):
    if inclusive:
        raise C.Stop("stage invoices with prices entered including tax are not supported. Enter the prices before tax")
    stages_in = bp["stages"]
    n = len(stages_in)
    cur_i = int(bp.get("current_stage") or 1)
    if not 1 <= cur_i <= n:
        raise C.Stop(f"current_stage {cur_i} is not one of the {n} stages")
    proj_net, proj_tax = tax_by_category(lines, cats, charged, False, rounding, currency, mu)
    proj_total = sum(proj_net.values()) + sum(proj_tax.values())
    prop = [l for l in lines if not l.get("stage")]
    fixed_lines = [l for l in lines if l.get("stage")]
    for l in fixed_lines:
        try:
            s = int(str(l["stage"]).strip())
        except ValueError:
            raise C.Stop(f"line {l['n']} has stage '{l['stage']}'; give the stage number")
        if not 1 <= s <= n:
            raise C.Stop(f"line {l['n']} is placed in stage {s}, but there are {n} stages")
        l["stage_no"] = s
    prop_gross = sum(l["net_minor"] for l in prop)
    if charged:
        prop_gross += sum(C.to_minor(Decimal(l["net_minor"]) * (cats[l["tax"]]["rate"] or 0) / 100 / (10 ** mu), currency)
                          for l in prop if l["tax"] in cats)
    shares = []
    total_pct = Fraction(0)
    balance_idx = None
    for i, st in enumerate(stages_in, 1):
        sh, am = st.get("share"), st.get("amount")
        if sh not in (None, "") and re.fullmatch(r"(?i)\s*(balance|rest|remainder|remaining|the rest)\s*", str(sh)):
            sh = None
            balance_idx = i
        if sh not in (None, ""):
            pct = Fraction(str(C.read_percent(sh, style, f"the share for stage {i}")))
            if pct <= 0 or pct > 100:
                raise C.Stop(f"stage {i} is {pct}% of the project; a share is between 0 and 100")
            shares.append(pct / 100)
            total_pct += pct
        elif am not in (None, ""):
            a = C.to_minor(C.read_amount(am, style, f"the amount for stage {i}"), currency)
            if prop_gross == 0:
                raise C.Stop("a fixed stage amount needs lines to split")
            fr = Fraction(a, prop_gross)
            shares.append(fr)
            total_pct += fr * 100
            P.flags.append(f"FLAG: stage {i} is a fixed amount, read as what the client pays on that stage, tax included where you charge it")
        else:
            if i != n:
                raise C.Stop(f"stage {i} has no share or amount; only the last stage can be 'the balance'")
            shares.append(None)
            balance_idx = i
    if balance_idx is None and total_pct != 100:
        raise C.Stop(f"the stages add to {float(total_pct):g}% of the project, not 100%. Ask the founder how to split it")
    if total_pct > 100:
        raise C.Stop(f"the stages add to {float(total_pct):g}%, over 100%")
    # per line per stage, last stage takes the remainder
    per = {l["n"]: [0] * n for l in lines}
    for l in prop:
        acc = 0
        for i in range(n - 1):
            v = 0 if shares[i] is None else C.frac_round(Fraction(l["net_minor"]) * shares[i])
            per[l["n"]][i] = v
            acc += v
        per[l["n"]][n - 1] = l["net_minor"] - acc
    for l in fixed_lines:
        per[l["n"]][l["stage_no"] - 1] = l["net_minor"]
    # tax per stage per category; a stage marked tax none carries none and the last stage takes the rest
    stage_cat_net = [{} for _ in range(n)]
    stage_cat_tax = [{} for _ in range(n)]
    for i in range(n):
        for l in lines:
            if per[l["n"]][i]:
                k = l["tax"] if charged else ""
                stage_cat_net[i][k] = stage_cat_net[i].get(k, 0) + per[l["n"]][i]
    if charged:
        for cid in proj_net:
            if cid == UNTAXED:
                continue
            acc = 0
            r = cats[cid]["rate"] or Decimal(0)
            for i in range(n - 1):
                no_tax = str(stages_in[i].get("tax") or "share").lower() == "none"
                v = 0 if no_tax else C.to_minor(Decimal(stage_cat_net[i].get(cid, 0)) * r / 100 / (10 ** mu), currency)
                if cid in stage_cat_net[i] or v:
                    stage_cat_tax[i][cid] = v
                    stage_cat_net[i].setdefault(cid, 0)
                acc += v
            last = proj_tax[cid] - acc
            stage_cat_tax[n - 1][cid] = last
            stage_cat_net[n - 1].setdefault(cid, 0)
            plain = C.to_minor(Decimal(stage_cat_net[n - 1].get(cid, 0)) * r / 100 / (10 ** mu), currency)
            if last != plain and all(str(s.get("tax") or "share").lower() != "none" for s in stages_in[:-1]):
                P.flags.append(f"FLAG: the {cats[cid]['label']} on the last stage is the balance of the project's tax, "
                               f"so the stages add up exactly; it differs from rate times net by {abs(last - plain)} of the smallest unit")
    totals = []
    for i in range(n):
        g = sum(stage_cat_net[i].values()) + sum(stage_cat_tax[i].values())
        totals.append(g)
    if sum(totals) != proj_total:
        raise C.Stop("internal check failed: the stages do not add to the project total. Nothing was produced")
    # earlier stages: compare with what was issued
    for i in range(cur_i - 1):
        st = stages_in[i]
        if not st.get("number"):
            P.need(f"NEED: the invoice number used for stage {i + 1} ({st.get('label') or ''}), so the summary can name it")
        if st.get("issued_total") not in (None, ""):
            it = C.to_minor(C.read_amount(st["issued_total"], style, f"the total issued for stage {i + 1}"), currency)
            if it != totals[i]:
                raise C.Stop(f"stage {i + 1} was invoiced at {it} (smallest units) but these lines give {totals[i]}. "
                             "Check the project lines against the earlier invoice before building the next stage")
    cur = cur_i - 1
    rule = "every line is split by the stage shares" if not fixed_lines else \
        "lines placed in a stage are billed in full there; the other lines are split by the stage shares"
    P.flags.append(f"FLAG: stage rule: {rule}; the last stage takes the remainder so the stages add up to the project total exactly")
    cur_lines = []
    for l in lines:
        v = per[l["n"]][cur]
        if not v:
            continue
        if l.get("stage_no"):
            cur_lines.append({"description": l["description"], "qty": l["qty"], "price": l["price"], "unit": l["unit"],
                              "amount_minor": v, "net_minor": v, "tax": l["tax"], "discount_text": l["discount_text"]})
        else:
            share = shares[cur]
            share_txt = None
            if share is not None:
                pct = share * 100
                share_txt = pct_text(pct, style)
            cur_lines.append({"description": l["description"], "qty": "1", "price": str(Decimal(v).scaleb(-mu)), "unit": "",
                              "amount_minor": v, "net_minor": v, "tax": l["tax"], "stage_line": True,
                              "line_total_minor": l["net_minor"], "share_text": share_txt})
    label = stages_in[cur].get("label") or f"Stage {cur + 1}"
    public = {"id": bp.get("id") or "", "name": bp.get("name") or "", "project_total": proj_total, "current_stage": cur_i,
              "stages": []}
    for i, st in enumerate(stages_in):
        if i == cur:
            status = "this invoice"
        elif st.get("paid_date"):
            status = "paid"
        else:
            status = st.get("status") or ("issued" if st.get("number") and i < cur else "waiting")
        public["stages"].append({"stage": i + 1, "label": st.get("label") or f"Stage {i + 1}",
                                 "share": str(st.get("share") or ("balance" if shares[i] is None else "")),
                                 "trigger": st.get("trigger") or "", "planned": st.get("planned"),
                                 "total": totals[i], "net": sum(stage_cat_net[i].values()),
                                 "tax": sum(stage_cat_tax[i].values()), "number": st.get("number"),
                                 "issue_date": st.get("issue_date"), "paid_date": st.get("paid_date"), "status": status})
    info = {"current": {"lines": cur_lines, "cat_net": stage_cat_net[cur] if charged else {"": stage_cat_net[cur].get("", 0)},
                        "cat_tax": stage_cat_tax[cur] if charged else {},
                        "heading": None, "label": label, "index": cur_i, "count": n},
            "totals": totals, "public": public, "stages_in": stages_in}
    info["current"]["heading_parts"] = {"n": cur_i, "count": n, "label": label}
    tax_labels = []
    for cid in proj_tax:
        lab = mid_sentence(cats[cid]["label"])
        if (cats[cid]["rate"] or 0) > 0 and proj_tax[cid] and lab not in tax_labels:
            tax_labels.append(lab)
    project = {"total": proj_total, "net": sum(proj_net.values()), "tax": sum(proj_tax.values()), "tax_labels": tax_labels}
    return info, project


def mid_sentence(label):
    """'Sales tax' inside a phrase reads 'sales tax'; VAT, GST and 'MwSt.' keep their capitals."""
    lab = str(label or "").strip()
    if lab and not lab.isupper() and lab[:1].isupper() and not lab[1:2].isupper() and lab.lower().startswith(("sales", "consumption", "goods", "service", "tax")):
        return lab[0].lower() + lab[1:]
    return lab


def pct_text(pct, style):
    """A share as the founder would write it: 50%, 33.33%, 12,5%."""
    d = (Decimal(pct.numerator) / Decimal(pct.denominator)).quantize(Decimal("0.01"))
    t = format(d.normalize(), "f")
    if "." in t:
        t = t.rstrip("0").rstrip(".")
    return (t.replace(".", ",") if style == "comma" else t) + "%"


def project_summary(info, project, labels, M, dtext, number, issue, preview=False):
    n = info["current"]["index"]
    tl = project.get("tax_labels") or []
    head = labels["project_total_incl"].format(tax=" / ".join(tl)) if tl else labels["project_total"]
    rows = [{"label": head, "text": M.full(project["total"]), "minor": project["total"]}]
    before = 0
    for st in info["public"]["stages"][:n - 1]:
        d_ = D.parse_iso(st["issue_date"]) if st.get("issue_date") else None
        if st.get("number"):
            lab = f"{labels['billed_before']}: {st['number']}" + (f", {dtext(d_)}" if d_ else "")
        elif preview:
            lab = f"{labels['billed_before']}: {labels['later_stage'].format(n=st['stage'], label=st['label'])}"
        else:
            lab = f"{labels['billed_before']}: [NEED: number]"
        pd_ = D.parse_iso(st["paid_date"]) if st.get("paid_date") else None
        if pd_:
            lab += ", " + labels["paid_on"].format(date=dtext(pd_))
        rows.append({"label": lab, "text": M.full(st["total"]), "minor": st["total"]})
        before += st["total"]
    if n == 1:
        rows.append({"label": labels["billed_before"], "text": labels["nothing_before"], "minor": 0})
    this = info["totals"][n - 1]
    rows.append({"label": f"{labels['this_invoice']}: {number}" if number else labels["this_invoice"], "text": M.full(this), "minor": this})
    rem = project["total"] - before - this
    later = [s_ for s_ in info["public"]["stages"][n:]]
    rows.append({"label": labels["remaining"], "text": M.full(rem), "minor": rem})
    # the later stages, as a short separate list under the summary (their amounts add to the remainder)
    info["current"]["still_to_come"] = []
    for s_ in later:
        lab = labels["later_stage"].format(n=s_["stage"], label=s_["label"])
        trig = (s_.get("trigger") or "").strip()
        if trig and not _redundant(trig, s_["label"]):
            lab += f", {trig}"
        info["current"]["still_to_come"].append({"label": lab, "text": M.full(s_["total"]), "minor": s_["total"]})
    info["current"]["heading"] = labels["stage_heading"].format(n=n, count=info["current"]["count"], label=info["current"]["label"])
    # stage lines now get their wording
    for l in info["current"]["lines"]:
        if l.get("stage_line") and l.get("share_text"):
            l["description"] = labels["stage_line"].format(desc=l["description"], share=l["share_text"], total=M.num(l["line_total_minor"]))
    return rows


STOPWORDS = {"when", "the", "is", "are", "on", "at", "a", "an", "of", "to", "once", "after", "upon", "and", "be", "been", "it", "its"}


def _redundant(trigger, label):
    """True when the trigger only repeats the stage label ("when the planting plan is approved" under "Planting plan approved")."""
    words = lambda x: {w.rstrip("s") for w in re.findall(r"[a-z0-9]+", x.lower()) if w not in STOPWORDS}
    t = words(trigger)
    return not t or t <= words(label)


def plan_outline(inp, P, style):
    bp = inp.get("billing_plan")
    if not bp or not bp.get("stages"):
        return None
    total = Fraction(0)
    out = []
    for i, st in enumerate(bp["stages"], 1):
        sh = st.get("share")
        if sh not in (None, ""):
            pct = Fraction(str(C.read_percent(sh, style, f"the share for stage {i}")))
            total += pct
            out.append({"stage": i, "label": st.get("label") or f"Stage {i}", "share": f"{float(pct):g}%", "trigger": st.get("trigger") or ""})
        else:
            out.append({"stage": i, "label": st.get("label") or f"Stage {i}", "share": st.get("amount") or "balance", "trigger": st.get("trigger") or ""})
    if total and total != 100 and all(s.get("share") for s in bp["stages"]):
        raise C.Stop(f"the stages add to {float(total):g}%, not 100%. Ask the founder how to split it")
    return {"stages": out, "adds_to": f"{float(total):g}%" if total else None}


def terms_info(inp, P, terms, due, labels, dwk):
    t = terms or inp.get("terms") or {}
    return {"type": t.get("type") or ("days" if t else None), "days": t.get("days"), "due_text": dwk(due) if due else None}


def reminders(inp, P, today, order, months, dtext, dwk, style, indian, days_off, holidays, currency_default, group=None, pstyle=None):
    out = []
    for o in inp.get("overdue") or []:
        cur = (o.get("currency") or currency_default or "").upper()
        if not cur:
            raise C.Stop(f"the currency of overdue invoice {o.get('number')} is not known. Ask the founder")
        M = C.Money(cur, pstyle or "dot", group=group, indian=indian)
        amt = C.to_minor(C.read_amount(o.get("amount"), style, f"the amount on invoice {o.get('number')}"), cur)
        if not o.get("due"):
            raise C.Stop(f"the due date of invoice {o.get('number')} is needed to count the days. Ask the founder")
        due = D.read_date(o["due"], order, today, prefer="past", months=months)
        late = (today - due).days
        if late <= 0:
            P.flags.append(f"FLAG: invoice {o.get('number')} is not overdue yet (due {dtext(due)})")
        if o.get("pay_by"):
            pay_by = D.read_date(o["pay_by"], order, today, prefer="future", months=months)
            pb_default = False
        else:
            pay_by = today + timedelta(days=7)
            while pay_by.weekday() in days_off or pay_by in holidays:
                pay_by += timedelta(days=1)
            pb_default = True
            P.defaults.append(f"DEFAULT: the reminder asks for payment by {dwk(pay_by)}, a week from today; change it if you prefer")
        num = str(o.get("number") or "")
        contact = (o.get("contact") or "").strip()
        greet = f"Hi {contact}," if contact else "Hello,"
        sign = (inp.get("founder_name") or "").strip() or "[NEED: your name]"
        ago = f"{late} day{'s' if late != 1 else ''} ago" if late > 0 else "today"
        draft = (f"Subject: Invoice {num}, {M.full(amt)}, due {dtext(due)}\n\n{greet}\n\n"
                 f"Invoice {num} for {M.full(amt)} was due on {dtext(due)}, {ago}. Could you pay it by {dwk(pay_by)}? "
                 "If anything on it needs fixing, or it is waiting on something at your end, tell me and I'll sort it.\n\n"
                 f"The payment details and reference are on the invoice.\n\nThanks,\n{sign}")
        out.append({"draft": draft, "number": num, "client": o.get("client") or "", "contact": o.get("contact") or "",
                    "amount": M.full(amt), "amount_minor": amt, "currency": cur, "due_text": dtext(due),
                    "due_date": due.isoformat(), "days_late": late, "pay_by_text": dwk(pay_by),
                    "pay_by_default": pb_default})
    return out


def selfcheck(out, lines, cats, charged, inclusive, rounding, mu, stage_info, sign, paid, inv_disc):
    """Recompute the invoice a second way (exact fractions, integer rounding) and stop on any difference."""
    f = out["figures"]
    if not stage_info:
        for l in lines:
            exact = Fraction(l["qty"]) * Fraction(l["price"]) * (10 ** mu)
            if C.frac_round(exact) != l["gross_minor"]:
                raise C.Stop(f"internal check failed on line {l['n']}. Nothing was produced")
        if not inclusive:
            nets = {}
            for l in lines:
                nets[l["tax"]] = nets.get(l["tax"], 0) + l["net_minor"]
            tax_total = 0
            if charged:
                for cid, net in nets.items():
                    if cid == UNTAXED:
                        continue
                    r = Fraction(str(cats[cid]["rate"] or 0))
                    if rounding == "line":
                        tax_total += sum(C.frac_round(Fraction(l["net_minor"]) * r / 100) for l in lines if l["tax"] == cid)
                    else:
                        tax_total += C.frac_round(Fraction(net) * r / 100)
            if sign * (sum(nets.values()) + tax_total) != f["total"]:
                raise C.Stop("internal check failed: the total does not recompute. Nothing was produced")
            if sum(l["gross_minor"] - l["discount_minor"] for l in lines) - inv_disc != sign * f["net"]:
                raise C.Stop("internal check failed: the net does not recompute. Nothing was produced")
    shown = sum(t["minor"] for t in out["doc"]["totals"] if t["key"].startswith("tax_"))
    if shown != f["tax_total"]:
        raise C.Stop("internal check failed: the tax lines do not add up. Nothing was produced")
    if sum(out["figures"]["lines"]) != f["subtotal"] and not inclusive:
        raise C.Stop("internal check failed: the lines do not add to the subtotal. Nothing was produced")
    if f["due"] != sign * (sign * f["total"] - paid):
        raise C.Stop("internal check failed: the amount due does not recompute. Nothing was produced")


def finish(out, P):
    out["needs"], out["asks"], out["flags"], out["warns"], out["defaults"] = P.needs, P.asks, P.flags, P.warns, P.defaults


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("template")
    p = sub.add_parser("plan")
    p.add_argument("inputs")
    p.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.cmd == "template":
        print(json.dumps(TEMPLATE, indent=2))
        return 0
    if a.cmd != "plan":
        ap.print_help()
        return 2
    inp = C.load_json(a.inputs, "inputs file")
    if not isinstance(inp, dict):
        raise C.Stop("the inputs file must be one JSON object")
    out = compute(inp)
    C.save_json(out, a.out)
    print(out["status"] if out["status"] != "NONE" else "NO INVOICE (terms or reminder only)")
    if out.get("doc"):
        ch = out["chat"]
        if out["doc"].get("preview"):
            print(f"DOC: preview of {out['doc']['stage_heading'] or 'a later stage'} for {ch['client']}, total {ch['total']}; no number or date until it is issued")
        elif out["mode"] == "credit_note":
            print(f"DOC: {out['doc']['title']} {ch['number']} to {ch['client']}, {ch['total']}, issued {ch['issue_date']}, "
                  f"reversing {(out['doc'].get('credits') or {}).get('number')}")
        else:
            print(f"DOC: {out['doc']['title']} {ch['number']} to {ch['client']}, total {ch['total']}, amount due {ch['due']}, "
                  f"issued {ch['issue_date']}, due {ch['due_date']}")
        if out.get("project"):
            M = C.money_for(out)
            print(f"PROJECT: total {M.full(out['project']['total'])}; stages: " +
                  "; ".join(f"{s['stage']} {s['label']} {M.full(s['total'])} ({s['status']})" for s in out["billing_plan"]["stages"]))
    for r in out.get("reminders") or []:
        print(f"OVERDUE: {r['number']} {r['amount']} due {r['due_text']}, {r['days_late']} days late; pay by {r['pay_by_text']}")
    for k in ("needs", "asks", "flags", "warns", "defaults"):
        for line in out[k]:
            print(line)
    print(f"WROTE: {a.out}")
    return 1 if (out["needs"] or out["asks"]) else 0


if __name__ == "__main__":
    C.run_main(main)
