#!/usr/bin/env python3
"""Check revival messages (and any founder-facing text) against the banned patterns and the message rules.

Messages in another language (settings message_language) get every check that does not depend on English: length,
question marks, money and the founder's prices, the founder's own opt-out line word for word, quotations, merge
fields, dashes, exclamation marks, emoji, the reason to write, the sender's name in a first text. The English phrase
lists are skipped and the build says so.

Message rules (references/rubric.md): one question per message, exactly one on touch 1; under 90 words for
email, 300 characters for a text, 60 words for a DM; no money, percentage or the founder's prices before the
touch the founder allows (never, by default); no urgency, discount or deadline; no new offer, result or booking
ask on touch 1, and nothing the founder said has changed before touch 3; an opt-out line on touch 1 and the
last touch; every phrase in double quotation marks found in that contact's own notes; touch 1 carries a reason
to write (their date, their words, when you last spoke); no leftover {fields}.

Usage:
  python3 scripts/check_copy.py <file>              check any text file (chat summary, notes) for banned patterns
  python3 scripts/check_copy.py --text "..."        check a string
Called from revival.py for every rendered message. Prints PROBLEM and WARN lines and a count; exit 1 on any
PROBLEM, exit 2 with STOP: on bad input. Standard library only. No network calls.
"""
import argparse
import re
import sys
import unicodedata
from pathlib import Path

BASE_PROBLEMS = {
    r"[\u2014\u2013]": "em or en dash",
    r"\bin today'?s (fast-paced|digital|ever-changing|busy)": "stock opener",
    r"\bit'?s not (just )?[^.?]{1,40}, it'?s\b": "contrast reveal",
    r"\b(game[- ]changer|delve|unlock(s|ing)?|elevate(s|d)?|seamless(ly)?|leverag(e|es|ing)|synerg(y|ies))\b": "filler word",
    r"\b(I mean|to be honest|if I'?m being honest|let'?s be real|honestly)\b": "announced honesty",
}
BASE_WARNS = {
    r"(?<!any )(?<!no )(?<!once )\bmore\b": "'more' as an intensifier: is a specific comparison possible?",
    r"\b(robust|cutting[- ]edge|world[- ]class|best[- ]in[- ]class|innovative)\b": "vague superlative",
}
DOMAIN_PROBLEMS = {
    r"\bjust (checking|touching|following|wanted to|circling)\b": "'just checking in' style filler",
    r"\bchecking in\b": "'checking in'",
    r"\bcircling back\b": "'circling back'",
    r"\btouch(ing)? base\b": "'touching base'",
    r"\bbump(ing)? (this|it|up)\b": "'bumping this'",
    r"\bfollowing up on my (last|previous|earlier) (email|message|note)\b": "'following up on my last email'",
    r"\bany updates?\b": "'any update'",
    r"\bper my last\b": "'per my last'",
    r"\bI hope (this|you'?re|you are|all is|everything)\b.{0,25}\b(finds|well|good)\b": "'I hope this finds you well'",
    r"\bI noticed you haven'?t\b": "'I noticed you haven't'",
    r"\b(we|I) miss(ed)? you\b": "'we miss you'",
    r"\blast chance\b": "urgency: 'last chance'",
    r"\blimited[- ]time\b": "urgency: 'limited time'",
    r"\bfinal (reminder|notice|call)\b": "urgency: 'final reminder'",
    r"\bbefore it'?s too late\b": "urgency: 'before it's too late'",
    r"\bdon'?t miss (out|this)\b": "urgency: 'don't miss out'",
    r"\bonly \d+ (left|spots?|places?|slots?)\b": "staged scarcity",
    r"\b(expires?|expiring|ends) (soon|today|tomorrow|friday|this week|on)\b": "urgency: a deadline",
    r"\btoday only\b|\bact now\b|\bhurry\b": "urgency",
    r"\bI never heard back\b|\byou never (replied|got back|answered)\b|\bhaven'?t heard (back )?from you\b": "guilt opener",
    r"\b(came across|saw|was looking at|stumbled on) your (profile|post|website|company)\b": "fake personalisation",
    r"\b(I'?m|I am|we'?re|we are) reaching out\b|\breaching out (to|because|as)\b": "'reaching out'",
    r"\bsorry to (bother|chase|pester)\b": "apology the founder did not make",
    r"\b(I|we) (apologi[sz]e|am sorry|'m sorry) (for|about) (the|my|our) (silence|delay|radio silence)\b": "apology the founder did not make",
    r"\bthat'?s on me\b|\bmy bad\b": "apology the founder did not make",
    r"\bfriendly reminder\b|\bgentle (reminder|nudge)\b": "reminder language",
    r"\bpick your brain\b": "'pick your brain'",
    r"\b(discount|\d+ ?% off|special (offer|price|rate)|free (bonus|gift|upgrade)|bonus)\b": "discount or bonus",
    r"[\U0001F300-\U0001FAFF☀-➿]": "emoji",
    r"!": "exclamation mark",
    r"\b(GDPR|CAN-SPAM|compliant|legally|the law (says|requires|allows))\b": "a statement about law",
    r"\btax[- ](deductible|rate|saving|break)\b|\bsave (on )?tax\b|\byou can claim\b": "tax advice",
}
SUBJECT_PROBLEMS = {
    r"^\s*quick (question|one|q)\s*\??\s*$": "'quick question' subject with nothing behind it",
    r"^\s*(re|fwd?|aw|wg|tr|rv|sv|vs):": "fake reply or forward subject",
    r"checking in|following up|touching base|any update": "chaser subject",
}
NO_ORIENTED = r"\bhave you (given up|decided (not|against)|moved on from)\b|\bare you (against|opposed to)\b"
MONEY = (r"([$£€¥₹]|\b(USD|GBP|EUR|AUD|CAD|NZD|SGD|INR|CHF|AED)\b)\s?\d|\d[\d.,]*\s?(k\b|€|\$|"
         r"\b(USD|GBP|EUR|AUD|CAD|NZD|SGD|INR|CHF|AED|dollars|pounds|euros?)\b)|\d+(\.\d+)?\s?%|\bper ?cent\b|\bpercent\b")
PITCH_T1 = (r"\b(book (a|in a|your) (call|time|slot)|schedule a (call|time)|hop on a call|grab (a|some) time|calendly|"
            r"link to book|(our|my) (new )?(package|offer|programme|program|service|product)s?\b|we now offer|"
            r"we('ve| have) (just )?launched|introducing)\b")
RESULTS = r"\b(we helped|helped (a|one|another) client|clients? (saw|see|got|get)|\d+x\b|increased? .{0,30} by \d)"
OPT_OUT = (r"(rather (I|we) (didn'?t|did not|don'?t|do not|stopped|stop)|prefer (I|we) (didn'?t|did not|don'?t)|"
           r"(won'?t|will not|not|never) (get in touch|write|message|text|contact you|follow up|email|chase) again|"
           r"(not|no) (to )?(hear|get) (from me|in touch)|(say|reply|let me know) (and|if) .{0,30}(stop|leave it|won'?t)|"
           r"reply stop|unsubscribe|leave you (be|alone)|close (your|the) file|closing (your|the) file|last (time|note|message) (I|I'll)|"
           r"won'?t (chase|bother|nudge))")
STOP = set("about above after again against all also am an and any are as at be because been before being below between "
           "both but by can could did do does doing down during each few for from further had has have having he her "
           "here hers him his how i if in into is it its just me might more most my no nor not now of off on once only "
           "or other our out over own same she should so some such than that the their them then there these they this "
           "those through to too under until up very was we were what when where which while who whom why will with "
           "would you your yours said told asked never still back last month week year call email".split())
LIMITS = {"email": ("words", 90), "text": ("chars", 300), "dm": ("words", 60)}


def fold(text):
    t = unicodedata.normalize("NFKD", str(text or ""))
    return "".join(ch for ch in t if not unicodedata.combining(ch)).lower()


def words(text):
    return len(re.findall(r"\b[\w'’-]+\b", text))


def snippet(text, m):
    return text[max(0, m.start() - 25):m.end() + 25].replace("\n", " ").strip()


LANG_FREE = {"emoji", "exclamation mark", "a statement about law", "fake reply or forward subject", "em or en dash"}


def normal(text):
    return re.sub(r"\s+", " ", fold(text)).strip()


def has_own_opt_out(body, s):
    b = normal(body)
    return any(x and normal(x) in b for x in (s.get("opt_out_email"), s.get("opt_out_short")))


def generic(text, english=True):
    problems, warns = [], []
    for pat, why in BASE_PROBLEMS.items():
        if not english and why not in LANG_FREE:
            continue
        for m in re.finditer(pat, text, re.I):
            problems.append(f"{why}: '{snippet(text, m)}'")
    for pat, why in BASE_WARNS.items():
        if not english:
            continue
        for m in re.finditer(pat, text, re.I):
            warns.append(f"{why}: '{snippet(text, m)}'")
    return problems, warns


def price_patterns(prices):
    pats = []
    for p in prices or []:
        digits = re.sub(r"\D", "", str(p).split(",")[0] if re.search(r",\d{2}$", str(p)) else str(p))
        if len(digits) >= 3:
            core = digits.rstrip("0") if len(digits) > 4 else digits
            spaced = r"[.,'  ]?".join(list(digits))
            pats.append(spaced)
            if digits.endswith("000"):
                pats.append(re.escape(digits[:-3]) + r"(\.\d)?\s?k\b")
            _ = core
    return pats


def check_message(msg, touch_n, last, contact, s, kind="templated"):
    """msg: {'channel','subject','body'}. Returns (problems, warns)."""
    body = msg.get("body", "") or ""
    subject = msg.get("subject", "") or ""
    ch = msg.get("channel", "email")
    full = (subject + "\n" + body) if subject else body
    eng = (s.get("message_language") or "en") == "en"
    problems, warns = generic(full, eng)
    for pat, why in DOMAIN_PROBLEMS.items():
        if not eng and why not in LANG_FREE:
            continue
        for m in re.finditer(pat, full, re.I):
            problems.append(f"{why}: '{snippet(full, m)}'")
    for pat, why in SUBJECT_PROBLEMS.items():
        if not eng and why not in LANG_FREE:
            continue
        if subject and re.search(pat, subject, re.I):
            problems.append(f"subject: {why}: '{subject}'")
    if ch == "email" and not subject.strip():
        problems.append("email has no subject line")
    if len(subject) > 60:
        problems.append(f"subject is {len(subject)} characters; keep it under 60")
    unit, lim = LIMITS.get(ch, ("words", 90))
    n = words(body) if unit == "words" else len(body)
    if n > lim:
        problems.append(f"{ch} touch {touch_n} is {n} {'words' if unit == 'words' else 'characters'}, limit {lim}")
    q = body.count("?")
    if touch_n == 1 and q != 1:
        problems.append(f"touch 1 must ask exactly one question; it asks {q}")
    elif q > 1:
        problems.append(f"touch {touch_n} asks {q} questions; one ask per message")
    allow_from = s.get("price_from_touch")
    if not allow_from or touch_n < allow_from:
        for m in re.finditer(MONEY, full, re.I):
            problems.append(f"money or a percentage in touch {touch_n}: '{snippet(full, m)}'")
        for pat in price_patterns(s.get("prices")):
            for m in re.finditer(r"(?<![\d.,])" + pat + r"(?![\d])", full):
                problems.append(f"one of your prices appears in touch {touch_n}: '{snippet(full, m)}'")
    if touch_n == 1 and eng:
        for m in re.finditer(PITCH_T1, full, re.I):
            problems.append(f"touch 1 pitches (an offer or a booking ask): '{snippet(full, m)}'")
    if touch_n == 1:
        for w in s.get("never_in_first_touches", []):
            if w and re.search(r"\b" + re.escape(w) + r"\b", full, re.I):
                problems.append(f"'{w}' is in a first message, and you asked never to mention it there")
    if touch_n <= 2:
        for m in (re.finditer(RESULTS, full, re.I) if eng else []):
            problems.append(f"a result or claim in touch {touch_n}: '{snippet(full, m)}'")
        for item in s.get("changed", []):
            keys = [w for w in re.findall(r"[a-z]{5,}", fold(item)) if w not in STOP]
            hits = [w for w in keys if re.search(r"\b" + w + r"\b", fold(full))]
            if keys and len(hits) >= min(2, len(keys)):
                problems.append(f"what has changed ('{item}') appears in touch {touch_n}; it waits until touch 3")
    for m in (re.finditer(NO_ORIENTED, full, re.I) if eng else []):
        if touch_n < 3 or contact.get("segment") != "quiet_after_proposal":
            problems.append(f"the no-oriented question is for touch 3 or later of the went-quiet-after-a-proposal group: '{snippet(full, m)}'")
    if not last and eng:
        for m in re.finditer(r"\b(ask(ing)? (you )?(just )?once|only (ask|asking) once|one last (time|note|try)|no chasing|"
                             r"not chasing|(won'?t|will not) chase|this is my last)\b", body, re.I):
            problems.append(f"touch {touch_n} promises not to follow up, but the sequence continues: '{snippet(body, m)}'")
    if (touch_n == 1 or last) and not has_own_opt_out(body, s) and not (eng and re.search(OPT_OUT, body, re.I)):
        own = s.get("opt_out_short") if ch in ("text", "dm") else s.get("opt_out_email")
        problems.append(f"touch {touch_n} needs your opt-out line word for word ({{opt_out}} fills it): '{own}'")
    if re.search(r"[{}]", full):
        problems.append(f"a merge field was left in: '{full[:60]}'")
    src = fold(" ".join(str(contact.get(k, "")) for k in ("notes", "raw", "reason", "reply_notes", "parked_phrase")))
    src_n = re.sub(r"[^a-z0-9]+", " ", src)
    for m in re.finditer(r"[\"“„]([^\"“”„]{3,})[\"”]", full):
        before = full[max(0, m.start() - 16):m.start()]
        if re.search(r"(^|[^\w])[1-5]\s?[.):=]?\s?(\w+\s){0,2}$", before):
            continue  # a labelled reply option ("1 for \"still on\""), the founder's own words, not a quotation
        quote = re.sub(r"[^a-z0-9]+", " ", fold(m.group(1))).strip()
        if quote and quote not in src_n:
            problems.append(f"quotation not found in their notes: '{m.group(1)}'")
    if touch_n == 1:
        reasons = [contact.get("context"), contact.get("when"), contact.get("their_date"), contact.get("detail")]
        ok = any(r and fold(r) in fold(full) for r in reasons)
        months = "january february march april may june july august september october november december".split()
        for key in ("last_contact", "parked_date"):
            v = str(contact.get(key) or "")
            if not ok and re.match(r"\d{4}-\d{2}", v):
                mname = months[int(v[5:7]) - 1]
                ok = bool(re.search(r"\b" + mname + r"\b", fold(full))) or (v[:4] in full and key == "last_contact")
        if not ok:
            distinct = [w for w in re.findall(r"[a-zà-ÿ]{5,}", src) if w not in STOP]
            ok = any(re.search(r"\b" + re.escape(w) + r"\b", fold(full)) for w in distinct)
        if not ok:
            problems.append("touch 1 has no reason to write: name when you last spoke, their date, or something they said")
        if kind == "hand-written" and contact.get("first") and fold(contact["first"]) not in fold(body):
            warns.append(f"hand-written touch 1 does not use {contact['first']}'s name")
    if ch == "text" and touch_n == 1 and s.get("sign_off") and fold(s["sign_off"]).split()[0] not in fold(body):
        problems.append("a first text from you must say who it is from (your name)")
    lc = str(contact.get("last_contact") or "")
    today = s.get("today")
    if eng and re.match(r"\d{4}-\d{2}", lc) and hasattr(today, "year"):
        age = (today.year - int(lc[:4])) * 12 + today.month - int(lc[5:7])
        mname = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
                 "November", "December"][int(lc[5:7]) - 1]
        if age >= 10 and int(lc[:4]) < today.year:
            for m in re.finditer(r"(?<![Ll]ast )(?<![Tt]his )\b" + mname + r"\b(?!\s*(,\s*)?\d{4}|\s+(last|this|next) year|"
                                 r"\s+\d{1,2}(,\s*\d{4})?\b)", body):
                warns.append(f"'{mname}' with no year, {age} months ago: say 'last year' or the year, or it reads as recent")
                break
    if re.search(r"\btax\b|\bVAT\b|\bGST\b", full, re.I):
        warns.append("mentions tax: make sure nothing reads as tax advice")
    return problems, warns


def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("file", nargs="?")
    a.add_argument("--text")
    args = a.parse_args()
    if args.text is None and not args.file:
        print("STOP: give a file to check or --text")
        sys.exit(2)
    if args.text is not None:
        text = args.text
    else:
        p = Path(args.file)
        if not p.exists():
            print(f"STOP: cannot find {p}")
            sys.exit(2)
        text = p.read_text(encoding="utf-8", errors="replace")
    problems, warns = generic(text)
    for pat, why in DOMAIN_PROBLEMS.items():
        if why in ("exclamation mark", "discount or bonus", "a statement about law", "tax advice"):
            continue  # a chat summary may say "no discount" or name the compliance line; messages are checked in full
        for m in re.finditer(pat, text, re.I):
            problems.append(f"{why}: '{snippet(text, m)}'")
    for x in problems:
        print("PROBLEM:", x)
    for x in warns:
        print("WARN:", x)
    print(f"{len(problems)} problems, {len(warns)} warnings, {words(text)} words")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
