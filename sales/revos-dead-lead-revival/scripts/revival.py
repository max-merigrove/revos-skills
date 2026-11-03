#!/usr/bin/env python3
"""Dead Lead Revival: read the list, sort it, date it, then build the tracker and the messages document.

Usage:
  python3 scripts/revival.py preview <list file> --settings <settings.json> --work <scratch folder>
         [--annotations <annotations.json>] [--map field=Column ...] [--previous <earlier tracker.xlsx>]
      Reads and sorts every row, dates every touch, and prints the counts, the held-back list, the first ten,
      every flag, and the templates the messages file must hold. Writes <work>/plan.json. Writes no founder file.
  python3 scripts/revival.py build --work <scratch folder> --messages <messages.json> --out <output folder>
      Fills and checks every message. On any copy problem prints PROBLEM lines and writes nothing (exit 1).
      Otherwise writes dead-lead-revival_YYYY-MM-DD.xlsx and revival-messages_YYYY-MM-DD.docx, runs
      check_plan.py on them, and prints the chat summary figures (exit 0).

Exit 2 with STOP: (and ASK: when the founder must answer) on anything that cannot be read safely; nothing is
written. Standard library only. No network calls. Nothing is ever sent.
"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402
import check_plan  # noqa: E402
import ingest as ig  # noqa: E402
import locale_numbers as ln  # noqa: E402
import messages as msgs  # noqa: E402
import schedule as sch  # noqa: E402
import segment as seg  # noqa: E402
from common import OPT_OUT_EMAIL, OPT_OUT_SHORT, Stop, fold, is_english, load_json, load_settings, long_date, show_date  # noqa: E402

LANG_WORDS = {
    "en": "the and after said never with call sent was they she he but not then about",
    "de": "und der die das nicht nie mit hat ist wollte nach kein noch sich auf fur ein eine",
    "fr": "le la les et pas avec pour une est des il elle mais sur apres",
    "es": "el los las y con para una pero que del despues dijo nunca",
    "nl": "de het en niet met een voor nog maar heeft wil",
    "it": "il che con per una non gli della dopo",
    "pt": "o os com para uma nao que depois disse nunca",
}
LANG_NAME = {"en": "English", "de": "German", "fr": "French", "es": "Spanish", "nl": "Dutch", "it": "Italian",
             "pt": "Portuguese"}


def notes_language(contacts):
    """The language most of the notes are written in, by common words; None when there is too little to tell."""
    words = []
    for c in contacts:
        words += fold(" ".join(str(c.get(k) or "") for k in ("notes", "reason", "stage", "raw"))).split()
    if len(words) < 30:
        return None
    score = {lg: sum(1 for w in words if w in set(ws.split())) for lg, ws in LANG_WORDS.items()}
    best = max(score, key=score.get)
    return best if score[best] >= 5 else None


def assign_today(contacts, meta, s):
    """The first ten are the people who can be messaged on the first sending day: top of the ranking, first touch
    dated that day, and an address on file. Hand-written first messages go to them."""
    start = meta["start"]
    sendable = [c for c in contacts if c.get("next_date") == start and not c.get("address_needed")]
    top = {c["ref"] for c in sendable[: s["tier_a"]]}
    n = 0
    for c in contacts:
        if c["ref"] in top:
            n += 1
            c["tier"], c["today_rank"] = "A", n
        else:
            c["tier"] = "B"
            c.pop("today_rank", None)


def _jsonable(o):
    if isinstance(o, date):
        return o.isoformat()
    raise TypeError(str(type(o)))


def plausibility(data, s):
    """Headline figures that cannot be right stop with a question before anything is built."""
    prices = []
    for p in s.get("prices") or []:
        try:
            prices.append(ln.parse_money(str(p), data.get("decimal"))[0])
        except (ln.Ambiguous, ln.Unreadable):
            continue
    top = max(prices) if prices else None
    for c in data["contacts"]:
        v = c.get("value")
        if isinstance(v, (int, float)) and v != 0:
            if v < 1:
                raise Stop(f"row {c['row']} has a value of {c.get('value_as_given', v)}, under 1 unit of currency",
                           ask=f"Row {c['row']} shows a value of {c.get('value_as_given', v)}. What was the deal worth?")
            if top and v > 10 * top and "values" not in (s.get("confirmed") or []):
                raise Stop(f"row {c['row']} has a value of {c.get('value_as_given', v)}, over ten times your highest price",
                           ask=f"Is {c.get('value_as_given', v)} on row {c['row']} right? Your highest price is {top:,.0f}.")


def preview(args):
    s = load_settings(args.settings)
    gm = {}
    for m in args.map or []:
        if "=" not in m:
            raise Stop(f"--map needs field=Column, got '{m}'")
        k, v = m.split("=", 1)
        gm[k] = v
    data = ig.ingest(args.list, s.get("date_order"), s.get("decimal"), s["today"], s.get("country"), gm)
    plausibility(data, s)
    ann = load_json(args.annotations, "the annotations file") if args.annotations else {}
    if not isinstance(ann, dict):
        raise Stop("the annotations file must be one JSON object keyed by ref (C012) or row number")
    status_in_counts = {}
    if data["kind"] == "tracker":
        for c in data["contacts"]:
            if c.get("sheet") == "Contacts":
                k = str(c.get("status") or "not started").strip().lower()
                status_in_counts[k] = status_in_counts.get(k, 0) + 1
    prev = None
    if args.previous:
        prev = ig.ingest(args.previous, None, None, s["today"], s.get("country"), {})
        if prev["kind"] != "tracker":
            raise Stop("--previous must be a tracker this skill made (it needs the Contacts and Held back sheets)")
    res = seg.plan_contacts(data, s, ann, prev)
    contacts, held = res["contacts"], res["held"]
    if data["kind"] == "tracker":
        for c in contacts:
            c["status_in"] = "sent" if str(c.get("status", "")).lower() == "sent" else "not started"
    limit = s.get("batch_limit")
    if limit:
        contacts = contacts[: int(limit)]
    meta = sch.schedule(contacts, s, data["date_order"])
    assign_today(contacts, meta, s)
    rows_in = data["rows_in"]
    if len(contacts) + len(held) != rows_in and not limit:
        raise Stop(f"{rows_in} rows came in but {len(contacts)} + {len(held)} were accounted for; this is a bug, "
                   "do not deliver")
    needed = sorted({(c["segment"], tn, c["channel"]) for c in contacts
                     for t, tn in zip(c["touches"], [c["template_nums"][t["n"] - 1] for t in c["touches"]])})
    country = (s.get("country") or "").upper()
    paper = ln.locale_defaults(country)["paper"] if country else "A4"
    sset = dict(s)
    sset["today"] = s["today"].isoformat()
    plan = {"settings": sset, "rows_in": rows_in, "kind": data["kind"], "date_order": data["date_order"],
            "date_order_note": data.get("date_order_note"), "decimal": data.get("decimal"), "mapped": data["mapped"],
            "bulk_date": data.get("bulk_date"), "contacts": contacts, "held": held, "schedule": meta,
            "needed": needed, "paper": paper, "list_file": str(args.list), "status_in_counts": status_in_counts,
            "notes_language": notes_language(data["contacts"])}
    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)
    (work / "plan.json").write_text(json.dumps(plan, indent=1, default=_jsonable, ensure_ascii=False), encoding="utf-8")
    print_preview(plan)


def print_preview(plan):
    s = plan["settings"]
    order = plan["date_order"]
    contacts, held = plan["contacts"], plan["held"]
    print(f"READ: {plan['rows_in']} rows ({plan['kind']}); dates "
          + {"dmy": "day first", "mdy": "month first", "ymd": "year first"}[order]
          + (f" ({plan['date_order_note']})" if plan.get("date_order_note") else "")
          + f"; columns used: " + ", ".join(f"{k}={v}" for k, v in plan["mapped"].items()))
    if plan.get("kind") == "tracker":
        print("FROM YOUR TRACKER: " + status_counts(plan))
    groups = [g for g in seg.SEGMENT_ORDER if any(c["segment"] == g for c in contacts)]
    print(f"COUNTS: {len(contacts)} to message in {len(groups)} groups, {len(held)} held back; "
          f"{plan['rows_in']} in, {len(contacts) + len(held)} accounted for")
    for g in groups:
        ppl = [c for c in contacts if c["segment"] == g]
        print(f"GROUP: {seg.SEGMENTS[g]['label']} | {len(ppl)} | " + ", ".join(c.get("name") or c.get("email", "") for c in ppl[:12])
              + (" ..." if len(ppl) > 12 else ""))
    codes = {}
    for h in held:
        codes.setdefault(h["held_code"], []).append(h)
    for code, hs in sorted(codes.items(), key=lambda x: -len(x[1])):
        print(f"HELD: {seg.HOLD[code][0]} | {len(hs)} | " + ", ".join((h.get("name") or h.get("email") or h["ref"]) for h in hs[:12]))
    print(f"PACE: up to {s['daily_cap']} a day on " + ", ".join(seg_day(i) for i in plan["schedule"]["workdays"])
          + f"; first sends {long_date(plan['schedule']['start'], order)}; last send "
          + (long_date(plan["schedule"]["last_send"], order) if plan["schedule"]["last_send"] else "none"))
    first_day = plan["schedule"]["start"]
    n_today = sum(1 for c in contacts if c.get("next_date") == first_day)
    print(f"TODAY: {n_today} first messages on {show_date(first_day, order)}")
    for c in [x for x in contacts if x["tier"] == "A"]:
        print(f"TOP {c['today_rank']}: {c['ref']} | {c.get('name') or c.get('email', '')} | {c.get('company', '')} | "
              f"{seg.SEGMENTS[c['segment']]['short']} | {c['channel']} | first send {show_date(c['next_date'], order)} | "
              f"why: {c.get('why', '')} | context: {c.get('context') or '[none: write one]'}"
              + (f" | their date: {c.get('their_date')}" if c.get("their_date") else ""))
    print_later(plan)
    for c in contacts + held:
        if c.get("corrections"):
            print(f"CORRECTED: {c['ref']} {c.get('name') or c.get('email', '')}: " + "; ".join(c["corrections"]))
    for c in contacts + held:
        for f in c.get("notes_flags", []):
            print(f"FLAG: {c['ref']} {c.get('name') or c.get('email', '')}: {f}")
        if c.get("why_inferred"):
            print(f"FLAG: {c['ref']} {c.get('name') or ''}: reason inferred ({c.get('why')})")
    rich = [c for c in contacts if c["tier"] != "A" and c.get("rich_notes") and not c.get("detail")]
    if rich:
        print(f"DETAIL WORTH WRITING: {len(rich)} people's notes hold a specific fact their template would miss. Write one "
              "sentence each as 'detail' in annotations, from their notes only:")
        for c in rich[:60]:
            print(f"DETAIL: {c['ref']} {c.get('name') or c.get('email', '')} | {seg.SEGMENTS[c['segment']]['short']} | "
                  f"notes: {c.get('why', '')}")
    no_ctx = [c for c in contacts if not c.get("context")]
    if no_ctx:
        print(f"CONTEXT MISSING: {len(no_ctx)} people have no personal field yet (add 'context' in annotations, "
              "or their messages will carry [NEED]): " + ", ".join(c["ref"] for c in no_ctx[:20]))
    if plan.get("bulk_date"):
        print(f"FLAG: over a third of the list shares the date {plan['bulk_date']}: read as an import stamp, treated as unknown")
    need = {}
    for g, tn, ch in plan["needed"]:
        need.setdefault((g, ch), []).append(tn)
    for (g, ch), ns in need.items():
        print(f"TEMPLATES NEEDED: {g} | {ch} | touches {', '.join(map(str, ns))} | purpose: see references/segments.md")
    print_language(plan)
    print("TIER A: write touch 1 by hand for " + ", ".join(c["ref"] for c in contacts if c["tier"] == "A"))
    print("NEXT: write the messages file (references/segments.md), then run revival.py build")


def print_later(plan):
    """Who is not in the first ten and why: a date they gave, an address still missing, no usable channel."""
    s, order = plan["settings"], plan["date_order"]
    start = plan["schedule"]["start"]
    parked = [c for c in plan["contacts"] if c.get("next_date") and c["next_date"] > start and c["segment"] == "parked"]
    if parked:
        print("PARKED: " + "; ".join(f"{c.get('name') or c['ref']} (due {show_date(c['next_date'], order)}, "
                                     f"they said {c.get('their_date') or 'a date'})" for c in parked))
    need = [c for c in plan["contacts"] if c.get("address_needed")]
    if need:
        what = {"email": "an email", "text": "a number", "dm": "a handle"}
        print(f"NEEDS ADDRESS: {len(need)} planned people need an address from your phone or inbox before you can send: "
              + ", ".join(f"{c.get('name') or c['ref']} ({what[c['channel']]})" for c in need))
    noch = [h for h in plan["held"] if h["held_code"] == "no_channel"]
    if noch:
        print(f"CHANNEL: {len(noch)} held back because your channels ({', '.join(s['channels'])}) cannot reach them: "
              + "; ".join(f"{h.get('name') or h['ref']} ({h['held_reason'].split('(', 1)[-1].rstrip(')')})" for h in noch)
              + ". Ask once: may they get another channel?")


def print_language(plan):
    s = plan["settings"]
    lang = s.get("message_language") or "en"
    nl = plan.get("notes_language")
    if nl and nl != lang:
        print(f"LANGUAGE: the notes are mostly {LANG_NAME.get(nl, nl)}; messages will be in "
              f"{LANG_NAME.get(lang, lang)} (settings message_language). Say which language your clients get, unless "
              "the founder already did.")
    if lang != "en":
        if s.get("opt_out_email") == OPT_OUT_EMAIL or s.get("opt_out_short") == OPT_OUT_SHORT:
            print(f"OPT-OUT NEEDED: write opt_out_email and opt_out_short in {LANG_NAME.get(lang, lang)} in settings "
                  "(the founder's own wording); every first and last message must carry them word for word")
        from common import CONTEXT_KEYS
        missing = [k for k in CONTEXT_KEYS if k not in (s.get("context_phrases") or {})]
        if missing:
            print(f"CONTEXT PHRASES NEEDED: write settings context_phrases in {LANG_NAME.get(lang, lang)} for: "
                  + ", ".join(f"{k} (English: '{CONTEXT_KEYS[k]}')" for k in missing)
                  + ". Each must read after 'since' or 'about' in that language. Then run preview again.")


def status_counts(plan):
    st = plan.get("status_in_counts") or {}
    return ", ".join(f"{n} {k}" for k, n in st.items()) + " (your own counts, as you set them)"


def seg_day(i):
    return ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][i]


def build_run(args):
    work = Path(args.work)
    plan = load_json(work / "plan.json", "the plan (run preview first)")
    m = load_json(args.messages, "the messages file")
    s = load_settings(plan["settings"])
    missing = msgs.validate_messages(m, [tuple(x) for x in plan["needed"]])
    tier_missing = [c["ref"] for c in plan["contacts"] if c["tier"] == "A" and c["ref"] not in (m.get("tier_a") or {})]
    tprobs = msgs.template_problems(m, s)
    rendered = msgs.render_all(plan["contacts"], m, s)
    probs = [(x["ref"], x["n"], p) for x in rendered for p in x["problems"]]
    if missing:
        for x in missing:
            print(f"MISSING: template {x}")
    if tprobs or probs or missing:
        for x in tprobs:
            print(f"PROBLEM: {x}")
        seen = set()
        for ref, n, p in probs:
            key = (ref, n, p)
            if key in seen:
                continue
            seen.add(key)
            print(f"PROBLEM: {ref} touch {n}: {p}")
        print(f"NOT BUILT: {len(tprobs)} template problems, {len(probs)} message problems, {len(missing)} missing "
              "templates. Fix the messages file and run build again. Nothing was written.")
        sys.exit(1)
    plan["messages"] = rendered
    plan["messages_file"] = m
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    day = plan["settings"]["today"]
    xlsx = out / f"dead-lead-revival_{day}.xlsx"
    docx = out / f"revival-messages_{day}.docx"
    build.build_workbook(plan, xlsx)
    build.build_docx(plan, docx)
    (work / "plan-built.json").write_text(json.dumps(plan, indent=1, default=_jsonable, ensure_ascii=False), encoding="utf-8")
    problems = check_plan.check(xlsx, docx, plan)
    if problems:
        for p in problems:
            print(f"PROBLEM: {p}")
        print("CHECK FAILED: the files were written but fail the plan checks; do not deliver them. Fix and rebuild.")
        sys.exit(1)
    summary(plan, xlsx, docx, tier_missing)


def summary(plan, xlsx, docx, tier_missing):
    s = plan["settings"]
    order = plan["date_order"]
    contacts, held, ms = plan["contacts"], plan["held"], plan["messages"]
    print(f"WROTE: {xlsx}")
    print(f"WROTE: {docx}")
    groups = [g for g in seg.SEGMENT_ORDER if any(c["segment"] == g for c in contacts)]
    print(f"SUMMARY 1: Sorted {plan['rows_in']} rows: {len(contacts)} to message in {len(groups)} groups ("
          + ", ".join(f"{sum(1 for c in contacts if c['segment'] == g)} {seg.SEGMENTS[g]['short']}" for g in groups)
          + f"); {len(held)} held back.")
    top = sorted([c for c in contacts if c["tier"] == "A"], key=lambda x: x["today_rank"])
    print(f"SUMMARY 2: First {len(top)} to send on {long_date(plan['schedule']['start'], order)}: " + "; ".join(
        f"{c.get('name') or c.get('email', '')}" + (f" ({c['company']})" if c.get("company") else "")
        + f", {seg.SEGMENTS[c['segment']]['short']}" for c in top))
    print_later(plan)
    codes = {}
    for h in held:
        codes[h["held_code"]] = codes.get(h["held_code"], 0) + 1
    not_ready = [x for x in ms if not x["ready"]]
    inferred = sum(1 for c in contacts if c.get("why_inferred"))
    approx = sum(1 for c in contacts if c.get("date_approx") and not str(c["date_approx"]).startswith("month only"))
    corrected = sum(1 for c in contacts + held if c.get("corrections"))
    if plan.get("kind") == "tracker":
        print("FROM YOUR TRACKER: " + status_counts(plan))
    print("SUMMARY 3: Held back: " + ("; ".join(f"{n} {seg.HOLD_SHORT[k]}" for k, n in
                                               sorted(codes.items(), key=lambda x: -x[1])) or "none")
          + f". Not ready ([NEED]): {len(not_ready)} of {len(ms)} messages. Reasons inferred: {inferred}. "
          + f"Approximate dates: {approx}. Corrected from what you told me: {corrected}.")
    loads = plan["schedule"]["loads"]
    print(f"PACE: {len(ms)} messages from {long_date(plan['schedule']['start'], order)} to "
          f"{long_date(plan['schedule']['last_send'], order)}, at most {max(loads.values()) if loads else 0} a day "
          f"(cap {s['daily_cap']}).")
    if tier_missing:
        print("WARN: no hand-written first message for " + ", ".join(tier_missing) + "; their touch 1 is [NEED]")
    for x in ms:
        for w in x.get("warns", []):
            print(f"WARN: {x['ref']} touch {x['n']}: {w}")
    if not is_english(s):
        print(f"LANGUAGE: messages in {LANG_NAME.get(s['message_language'], s['message_language'])}: checked for length, "
              "one question, money and your prices, your opt-out line word for word, quotations, merge fields, dashes, "
              "exclamation marks and emoji. The English phrase lists (stock openers, chasers, pitch words in touch 1, "
              "claimed results) were not run: read the messages against references/banned-patterns.md yourself.")
    print("CHECK: 0 problems")


def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = a.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("preview")
    p.add_argument("list")
    p.add_argument("--settings", required=True)
    p.add_argument("--work", required=True)
    p.add_argument("--annotations")
    p.add_argument("--map", action="append")
    p.add_argument("--previous", help="an earlier tracker, so a new list keeps its stops and cooldowns")
    b = sub.add_parser("build")
    b.add_argument("--work", required=True)
    b.add_argument("--messages", required=True)
    b.add_argument("--out", required=True)
    args = a.parse_args()
    try:
        if args.cmd == "preview":
            preview(args)
        else:
            build_run(args)
    except Stop as e:
        print(f"STOP: {e}")
        if getattr(e, "ask", None):
            print(f"ASK: {e.ask}")
        sys.exit(2)
    except (ValueError, KeyError, TypeError, OSError) as e:
        print(f"STOP: something in the inputs could not be used ({type(e).__name__}: {e}). Check the settings, "
              "annotations and messages files against references/intake-guide.md and run again.")
        sys.exit(2)


if __name__ == "__main__":
    main()
