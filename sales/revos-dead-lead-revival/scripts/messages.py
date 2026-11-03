#!/usr/bin/env python3
"""Fill every scheduled touch from the messages file the model wrote, and check each one.

messages.json:
{
  "templates": {"<group>": {"1": {"purpose": "...", "email": {"subject": "...", "body": "..."},
                                  "text": "...", "dm": "..."}, "2": {...}}},
  "tier_a": {"C012": {"subject": "...", "body": "..."}},           touch 1 written by hand for the top contacts
  "overrides": {"C030": {"2": {"subject": "...", "body": "..."}}}  any other touch written for one contact
}
Fields a template may use: {first_name} {full_name} {detail} {company} {context} {when} {their_date} {sender} {business}
{next_step} {changed} {opt_out}. {detail} is optional (one sentence from their notes, or nothing). Any other field with no value becomes
[NEED: ...] and the message is marked not ready;
no raw {field} ever reaches the founder. Standard library only. No network calls.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CONTEXT_KEYS, OPT_OUT_EMAIL, OPT_OUT_SHORT, Stop  # noqa: E402
import check_copy  # noqa: E402

FIELDS = {"first_name", "full_name", "last_name", "greeting", "detail", "company", "context", "when", "their_date", "sender",
          "business", "next_step", "changed", "opt_out"}
NEED_TEXT = {"first_name": "their first name", "full_name": "their full name", "last_name": "their surname",
             "greeting": "a greeting for this person", "company": "their company", "context": "what they asked about or when "
             "you last spoke", "when": "when you last spoke", "their_date": "the date they gave",
             "sender": "your name", "business": "your business name", "next_step": "the next step you want",
             "changed": "what has changed since"}


def validate_messages(m, needed):
    """needed: {group: [touch numbers]}, channels per group. Returns list of what is missing."""
    if not isinstance(m, dict):
        raise Stop("the messages file must be one JSON object with 'templates'")
    tpl = m.get("templates") or {}
    missing = []
    for (grp, n, ch) in needed:
        t = (tpl.get(grp) or {}).get(str(n)) or {}
        if ch == "email":
            e = t.get("email") or {}
            if not (isinstance(e, dict) and e.get("body")):
                missing.append(f"{grp} touch {n} email (subject and body)")
        else:
            if not (t.get(ch) or (ch == "dm" and t.get("text"))):
                missing.append(f"{grp} touch {n} {ch}")
    for grp, touches in tpl.items():
        for n, t in touches.items():
            for part in (t.get("email") or {}).values() if isinstance(t.get("email"), dict) else []:
                for f in re.findall(r"\{(\w+)\}", str(part)):
                    if f not in FIELDS:
                        raise Stop(f"template {grp} touch {n} uses {{{f}}}, which is not a field. Fields: "
                                   + ", ".join(sorted(FIELDS)))
            for k in ("text", "dm"):
                for f in re.findall(r"\{(\w+)\}", str(t.get(k, ""))):
                    if f not in FIELDS:
                        raise Stop(f"template {grp} touch {n} {k} uses {{{f}}}, which is not a field")
    return missing


def values_for(c, s):
    changed = s.get("changed") or []
    full = c.get("name") if c.get("name") and "@" not in str(c.get("name")) else ""
    parts = str(full).split()
    last = parts[-1] if len(parts) > 1 else ""
    greet = c.get("greeting") or ""
    if not greet and s.get("greeting_default"):
        g = str(s["greeting_default"])
        need_any = re.findall(r"\{(\w+)\}", g)
        have = {"first_name": c.get("first") or "", "full_name": full, "last_name": last}
        if all(have.get(f) for f in need_any):
            greet = re.sub(r"\{(\w+)\}", lambda m: have.get(m.group(1), ""), g)
    return {
        "last_name": last,
        "greeting": greet,
        "first_name": c.get("first") or "",
        "full_name": c.get("name") if c.get("name") and "@" not in str(c.get("name")) else "",
        "detail": (str(c.get("detail")).strip() + " ") if c.get("detail") else "",
        "company": re.sub(r"\s*\([A-Z]{2,3}\)\s*$", "", str(c.get("company") or "")),
        "context": c.get("context") or "",
        "when": c.get("when") or "",
        "their_date": c.get("their_date") or "",
        "sender": s.get("sign_off") or "",
        "business": s.get("business") or "",
        "next_step": s.get("next_step") or "",
        "changed": changed[0] if changed else "",
        "opt_out": s.get("opt_out_short") if c.get("channel") in ("text", "dm") else s.get("opt_out_email"),
    }


def fill(text, vals, needs):
    def rep(m):
        f = m.group(1)
        v = vals.get(f, "")
        if v or f == "detail":
            return str(v)
        needs.append(NEED_TEXT.get(f, f))
        return f"[NEED: {NEED_TEXT.get(f, f)}]"
    return re.sub(r"\{(\w+)\}", rep, text or "")


def render_one(c, touch, m, s):
    n = touch["n"]
    ch = touch["channel"]
    grp = c["segment"]
    needs = []
    kind = "templated"
    tn = (c.get("template_nums") or list(range(1, c["touch_count"] + 1)))[n - 1]
    over = ((m.get("overrides") or {}).get(c["ref"]) or {}).get(str(n))
    if n == 1 and c.get("tier") == "A" and (m.get("tier_a") or {}).get(c["ref"]):
        src = m["tier_a"][c["ref"]]
        kind = "hand-written"
    elif over:
        src = over
        kind = "hand-written"
    else:
        t = ((m.get("templates") or {}).get(grp) or {}).get(str(tn)) or {}
        if ch == "email":
            src = t.get("email") or {}
        else:
            body = t.get(ch) or (t.get("text") if ch == "dm" else "")
            src = {"body": body}
        if n == 1 and c.get("tier") == "A":
            needs.append("a hand-written first message for this top contact")
    vals = values_for(c, s)
    subject = fill(src.get("subject", "") if ch == "email" else "", vals, needs)
    body = fill(src.get("body", ""), vals, needs)
    if not body.strip():
        needs.append(f"the {ch} version of touch {n} for this group")
    purpose = (((m.get("templates") or {}).get(grp) or {}).get(str(tn)) or {}).get("purpose", "")
    msg = {"ref": c["ref"], "n": n, "template": tn, "of": c["touch_count"], "date": touch["date"], "channel": ch, "subject": subject,
           "body": body, "kind": kind, "purpose": purpose, "last": touch.get("last", False)}
    probs, warns = ([], [])
    if body.strip():
        probs, warns = check_copy.check_message(msg, n, touch.get("last"), c, s, kind)
        if kind == "templated" and c.get("context"):
            raw_all = (src.get("subject", "") if ch == "email" else "") + "\n" + src.get("body", "")
            for why, chunk in junction_problems(raw_all, vals, str(c["context"])):
                probs.append(f"the personal field '{c['context']}' reads wrongly here ({why}): '{chunk}'")
    msg["problems"] = probs
    msg["warns"] = warns
    msg["needs"] = sorted(set(needs))
    msg["ready"] = not needs and not probs
    return msg


def render_all(contacts, m, s):
    out = []
    for c in contacts:
        c["messages"] = []
        for t in c.get("touches", []):
            msg = render_one(c, t, m, s)
            c["messages"].append(msg)
            out.append(msg)
    return out


BROKEN = [
    (r"\b(after|since|in|from|of|about|on|at|to|with|for|by|around|over|before|until) when\b", "a preposition before 'when'"),
    (r"\b(my|your|our|the|a|an|his|her|their) (my|your|our|the|a|an|his|her|their)\b", "two articles in a row"),
    (r"\b(from|in|since|after|about|on|of) (from|in|since|after|about|on|of)\b", "two prepositions in a row"),
    (r"\b([a-z]{3,}) \1\b", "a doubled word"),
]


def junction_problems(raw, vals, phrase):
    """Fill the template with this personal-field phrase and check only where the phrase meets the template's words."""
    out = []
    pieces = fill(raw.replace("{context}", "\x00"), dict(vals, context=""), []).split("\x00")
    words = phrase.split()
    for i in range(len(pieces) - 1):
        left = pieces[i][-30:] + " ".join(words[:2])
        right = " ".join(words[-2:]) + pieces[i + 1][:30]
        for chunk in (left, right):
            for pat, why in BROKEN:
                mm = re.search(pat, chunk, re.I)
                if mm:
                    out.append((why, chunk.replace("\n", " ").strip()))
    return out


def phrase_samples(s):
    """Every personal-field phrase the script can write, filled with a sample date, in the message language."""
    own = s.get("context_phrases") or {}
    lang = s.get("message_language") or "en"
    out = []
    for k, eng in CONTEXT_KEYS.items():
        p = own.get(k) or (eng if lang == "en" else None)
        if p:
            out.append(p.replace("{when}", "March 2025" if lang == "en" else "03/2025").replace("{deal}", "audit"))
    return out


def template_problems(m, s):
    """Check each template once with neutral sample values, so a bad template is reported once, not per contact;
    then render it with every personal-field phrase the script can write, with and without a detail, and fail
    any that reads wrongly ("after when we were last in touch")."""
    found = []
    lang = s.get("message_language") or "en"
    if lang != "en" and (s.get("opt_out_email") == OPT_OUT_EMAIL or s.get("opt_out_short") == OPT_OUT_SHORT):
        found.append(f"settings: messages are in '{lang}' but the opt-out lines are the English defaults; write "
                     "opt_out_email and opt_out_short in the founder's language")
    sample = {"ref": "TEMPLATE", "first": "Sam", "company": "Sample Co", "context": "our call in March 2025",
              "when": "March 2025", "their_date": "Q3", "notes": "", "segment": ""}
    phrases = phrase_samples(s)
    for grp, touches in (m.get("templates") or {}).items():
        nmax = max(int(k) for k in touches) if touches else 0
        for n, t in touches.items():
            n = int(n)
            for ch in ("email", "text", "dm"):
                part = t.get(ch)
                if not part:
                    continue
                src = part if isinstance(part, dict) else {"body": part}
                c = dict(sample, segment=grp, channel=ch)
                vals = values_for(c, s)
                vals = {k: (v or f"<{k}>") for k, v in vals.items()}
                vals["detail"] = ""
                needs = []
                msg = {"channel": ch, "subject": fill(src.get("subject", ""), vals, needs) if ch == "email" else "",
                       "body": fill(src.get("body", ""), vals, needs)}
                body_raw = src.get("body", "")
                p, _w = check_copy.check_message(msg, n, n == nmax, c, s, "templated")
                p = [x for x in p if not x.startswith("touch 1 has no reason") and "quotation not found" not in x]
                if n == 1 and not re.search(r"\{(context|when|their_date)\}", body_raw + src.get("subject", "")):
                    p.append("touch 1 template must use {context}, {when} or {their_date} so each person gets a reason to write")
                raw_all = src.get("subject", "") + "\n" + body_raw
                if "{context}" in raw_all:
                    seen = set()
                    for ph in phrases:
                        for det in ("", "You'd said the board wants to see the numbers first. "):
                            for why, chunk in junction_problems(raw_all, dict(vals, detail=det), ph):
                                if (why, ph) not in seen:
                                    seen.add((why, ph))
                                    p.append(f"reads wrongly with the personal field '{ph}' ({why}): '{chunk}'. "
                                             "Rewrite the sentence so any phrase fits, or set a better context for "
                                             "those people")
                for x in p:
                    found.append(f"{grp} touch {n} {ch}: {x}")
    return found
