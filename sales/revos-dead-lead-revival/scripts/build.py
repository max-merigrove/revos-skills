#!/usr/bin/env python3
"""Build the revival tracker (.xlsx, six sheets) and the messages document (.docx) from a checked plan.

Called by revival.py build. Standard library only (office.py writes both files). No network calls.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import office  # noqa: E402
from common import (COMPLIANCE_LINE, DAY_NAMES, date_fmt_code, long_date, show_date)  # noqa: E402
from segment import ABBR, ANGLE, HOLD, SEGMENT_ORDER, SEGMENTS, CAME_LABEL  # noqa: E402
from office import S_BIG, S_BOLD, S_DATE, S_HEAD, S_INT, S_NOTE, S_STATUS, S_TEXT, S_TITLE, S_WRAP  # noqa: E402

STATUSES = ["not started", "sent", "replied", "call booked", "won", "no reply", "stopped", "bounced"]
CONTACT_COLS = ["Ref", "Name", "Company", "Email", "Phone", "DM handle", "Group", "Why", "Reason inferred", "Came onto the list",
                "Last real contact", "Months since", "Recency", "Score", "Rank", "Tier", "Channel", "Next touch",
                "Next touch date", "Touch dates", "Message ref", "Personal field", "Status", "Reply notes",
                "Stop date", "Cooldown until", "Their notes", "Flags"]
STATUS_COL = CONTACT_COLS.index("Status") + 1
HELD_COLS = ["Ref", "Name", "Company", "Email", "Phone", "Reason code", "Reason", "What would release it", "Revisit on",
             "Last real contact", "Their notes", "Flags"]
RULES_8 = [
    "One ask per message: one question, nothing else to do.",
    "The first touch never pitches: no price, no offer, no result, no deadline.",
    "Every message rests on their words, their date, or when you last spoke.",
    "No deadline, discount or bonus you did not give.",
    "Any reply stops the sequence for that person. Answer it yourself, the same working day.",
    "The last touch closes the file, plainly. Nobody is messaged after it.",
    "Send a few a day, by hand, from your own account. It is a conversation, not a campaign.",
    "You press send. Nothing here sends anything.",
]
REPLIES = [
    ("Yes, let's talk", "Offer two times for {next_step} in your reply. Status: call booked."),
    ("Not now, with a date", "Thank them, put the date in Reply notes and Next touch date, and write on that day. Status: replied."),
    ("Not now, no date", "Thank them and ask one thing: is there a better month to try? Then leave it. Status: replied."),
    ("How did you get my details?", "Say plainly how: when and how they first got in touch with you. Offer to remove them. Status: replied."),
    ("I went with someone else", "Wish them well and ask nothing. Status: replied; no more touches."),
    ("Remove me, or stop", "Confirm in one line that you will not write again, and mean it. Status: stopped."),
    ("Out of office", "Stop the sequence. Write once more by hand after the date they give. Status: replied."),
    ("Angry or hostile", "Do not argue in writing. Apologise for the intrusion, confirm you will not write again. Status: stopped."),
    ("It bounced", "Find a working address if you can; otherwise leave it. Status: bounced."),
]


def money(v, decimal):
    if v is None or v == "":
        return ""
    s = f"{v:,.0f}" if float(v).is_integer() else f"{v:,.2f}"
    if decimal == "comma":
        s = s.replace(",", " ").replace(".", ",").replace(" ", ".")
    return s


def build_workbook(plan, path):
    s = plan["settings"]
    order = plan["date_order"]
    contacts, held = plan["contacts"], plan["held"]
    msgs = plan["messages"]
    today = date.fromisoformat(s["today"])
    sheets = []

    # Contacts first so Today can point at it
    sc = office.Sheet("Contacts")
    sc.row(1, CONTACT_COLS, S_HEAD)
    sc.freeze_row = 2
    first_msg = {}
    for m in msgs:
        first_msg.setdefault(m["ref"], m)
    for i, c in enumerate(contacts, start=2):
        nm = first_msg.get(c["ref"])
        ref_txt = msg_ref(c, nm) if nm else ""
        last = date.fromisoformat(c["last_contact"]) if c.get("last_contact") else None
        stop = date.fromisoformat(c["stop_after"]) if c.get("stop_after") else None
        cool = add_months_iso(c["stop_after"], s["cooldown_months"]) if c.get("stop_after") else None
        vals = [c["ref"], c.get("name") or c.get("email", ""), c.get("company", ""), c.get("email", ""), c.get("phone", ""),
                c.get("handle", ""), SEGMENTS[c["segment"]]["label"], c.get("why", ""), "yes" if c.get("why_inferred") else "",
                CAME_LABEL.get(c.get("came_from"), c.get("came_from", "")), last,
                c.get("months_since") if c.get("months_since") is not None else "", c.get("band", ""), c["score"],
                c["rank"], "A, today, hand-written" if c["tier"] == "A" else "B, templated", c["channel"],
                f"{c['next_touch']} of {c['touch_count']}" if c.get("next_touch") else "",
                date.fromisoformat(c["next_date"]) if c.get("next_date") else None,
                "; ".join(t["date"] for t in c.get("touches", [])), ref_txt, c.get("context", ""),
                c.get("status_in") or "not started", c.get("reply_notes", ""), stop, cool,
                c.get("notes") or c.get("raw") or "", "; ".join(c.get("notes_flags", []))]
        for j, v in enumerate(vals, start=1):
            st = S_TEXT
            if isinstance(v, date):
                st = S_DATE
            elif CONTACT_COLS[j - 1] in ("Months since", "Score", "Rank"):
                st = S_INT
            elif CONTACT_COLS[j - 1] in ("Why", "Personal field", "Their notes", "Flags"):
                st = S_WRAP
            if j == STATUS_COL:
                st = S_STATUS
            sc.set(i, j, v, st)
    last_row = max(2, len(contacts) + 1)
    sc.autofilter = f"A1:{office.col_letter(len(CONTACT_COLS))}{last_row}"
    sc.validations.append((f"{office.col_letter(STATUS_COL)}2:{office.col_letter(STATUS_COL)}{last_row + 200}", STATUSES))
    widths = [6, 18, 18, 24, 14, 16, 20, 34, 9, 18, 12, 8, 14, 7, 6, 14, 8, 9, 12, 26, 9, 30, 13, 26, 11, 12, 40, 30]
    sc.widths = {i: w for i, w in enumerate(widths, 1)}
    sc.landscape = True

    # Today
    st = office.Sheet("Today")
    st.widths = {1: 6, 2: 22, 3: 20, 4: 24, 5: 44, 6: 9, 7: 14, 8: 12}
    st.set(1, 1, f"Revival plan: {s.get('business') or 'your old leads'}", S_TITLE)
    rows_in = plan["rows_in"]
    groups = [g for g in SEGMENT_ORDER if any(c["segment"] == g for c in contacts)]
    first_day = plan["schedule"].get("start")
    st.wide(2, (f"Made {long_date(today, order)}. {rows_in} rows read: {len(contacts)} to message in {len(groups)} "
                f"groups, {len(held)} held back. Every row is on Contacts or Held back exactly once."), S_WRAP, height=28)
    top = sorted([c for c in contacts if c["tier"] == "A"], key=lambda x: x["today_rank"])
    todays = [c for c in contacts if c.get("next_date") == first_day]
    need = [c for c in todays if c.get("address_needed")]
    st.wide(3, (f"Start here: send the {len(todays)} first messages dated {long_date(first_day, order)} "
                f"(on Send queue), the hand-written ones first"
                + (f"; {len(need)} of them need an address from your phone or inbox first" if need else "")
                + ". Update Status on Contacts as you go."), S_BIG, height=34)
    r = 5
    st.set(r, 1, f"Your first {len(top)}: the people most likely to reply who you can message on "
                 f"{long_date(first_day, order)}", S_BOLD)
    r += 1
    st.row(r, ["Rank", "Name", "Company", "Group", "Why (from your notes)", "Channel", "Message", "Send on"], S_HEAD)
    for c in top:
        r += 1
        nm = first_msg.get(c["ref"])
        st.row(r, [c["today_rank"], c.get("name") or c.get("email", ""), c.get("company", ""), SEGMENTS[c["segment"]]["label"],
                   c.get("why", ""), c["channel"], msg_ref(c, nm) if nm else "",
                   date.fromisoformat(c["next_date"]) if c.get("next_date") else ""], S_WRAP)
    later_rows = [(c.get("name") or c["ref"], f"add {'an email' if c['channel'] == 'email' else 'a number' if c['channel'] == 'text' else 'their handle'} "
                   f"before {show_date(c['next_date'], order)}") for c in contacts if c.get("address_needed")]
    if later_rows:
        r += 2
        st.set(r, 1, "Planned, but you need their address first (it is not in your notes)", S_BOLD)
        r += 1
        st.row(r, ["", "Name", "What to add"], S_HEAD)
        for nm_, what in later_rows:
            r += 1
            st.row(r, ["", nm_, what], S_WRAP)
    r += 2
    st.set(r, 1, "Groups", S_BOLD)
    r += 1
    st.row(r, ["", "Group", "People", "First send", "What it means"], S_HEAD)
    for g in groups:
        r += 1
        people = [c for c in contacts if c["segment"] == g]
        fs = min(c["next_date"] for c in people if c.get("next_date"))
        st.row(r, ["", SEGMENTS[g]["label"], len(people), date.fromisoformat(fs), ANGLE[g][0]], S_WRAP)
    r += 2
    st.set(r, 1, "Held back (on the Held back sheet, with what would release each one)", S_BOLD)
    r += 1
    st.row(r, ["", "Reason", "People"], S_HEAD)
    codes = {}
    for h in held:
        codes[h["held_code"]] = codes.get(h["held_code"], 0) + 1
    for code, n in sorted(codes.items(), key=lambda x: -x[1]):
        r += 1
        st.row(r, ["", HOLD[code][0], n], S_WRAP)
    r += 2
    st.set(r, 1, "Status totals (these update as you change Status on Contacts)", S_BOLD)
    r += 1
    st.row(r, ["", "Status", "People"], S_HEAD)
    colL = office.col_letter(STATUS_COL)
    for stt in STATUSES:
        r += 1
        cached = sum(1 for c in contacts if (c.get("status_in") or "not started") == stt)
        st.set(r, 2, stt)
        st.set(r, 3, cached, S_INT, formula=f'COUNTIF(Contacts!${colL}$2:${colL}${last_row + 200},"{stt}")')
    r += 1
    st.set(r, 2, "total", S_BOLD)
    st.set(r, 3, len(contacts), S_INT, formula=f"SUM(C{r - len(STATUSES)}:C{r - 1})")
    r += 2
    st.set(r, 1, "The next ten working days", S_BOLD)
    r += 1
    st.row(r, ["", "Day", "Messages"], S_HEAD)
    loads = plan["schedule"]["loads"]
    for d in sorted(loads)[:10]:
        r += 1
        dd = date.fromisoformat(d)
        st.row(r, ["", f"{DAY_NAMES[dd.weekday()]} {show_date(dd, order)}", loads[d]])
    dates = [c for c in contacts if c.get("parked_date") and c["parked_date"] > s["today"]]
    later = [h for h in held if h.get("revisit")]
    if dates or later:
        r += 2
        st.set(r, 1, "Dates to remember", S_BOLD)
        r += 1
        st.row(r, ["", "Name", "Date", "Why"], S_HEAD)
        for c in sorted(dates, key=lambda x: x["parked_date"]):
            r += 1
            st.row(r, ["", c.get("name", ""), date.fromisoformat(c["parked_date"]), f"they said {c.get('their_date', '')}: first message that day"], S_WRAP)
        for h in sorted(later, key=lambda x: x["revisit"]):
            r += 1
            st.row(r, ["", h.get("name", ""), date.fromisoformat(h["revisit"]), HOLD[h["held_code"]][0]], S_WRAP)
    r += 2
    st.wide(r, COMPLIANCE_LINE, S_NOTE, height=26)
    sheets.append(st)

    # Segments
    sg = office.Sheet("Segments")
    sg.widths = {1: 30, 2: 8, 3: 50, 4: 9, 5: 16, 6: 18, 7: 34}
    sg.row(1, ["Group", "People", "The angle", "Touches", "Day offsets", "Channels", "The stop"], S_HEAD)
    sg.freeze_row = 2
    r = 1
    for g in SEGMENT_ORDER:
        people = [c for c in contacts if c["segment"] == g]
        if not people:
            continue
        r += 1
        chans = {}
        for c in people:
            chans[c["channel"]] = chans.get(c["channel"], 0) + 1
        tc = sorted({c["touch_count"] for c in people})
        offs = sorted({", ".join(map(str, c["offsets"])) for c in people})
        sg.row(r, [SEGMENTS[g]["label"], len(people), ANGLE[g][0], " or ".join(map(str, tc)),
                   "; ".join("days " + o for o in offs), ", ".join(f"{k} {v}" for k, v in chans.items()), ANGLE[g][1]], S_WRAP)
    r += 2
    sg.set(r, 1, "How long ago they went quiet", S_BOLD)
    r += 1
    bands = ["1 to 3 months", "3 to 6 months", "6 to 18 months", "18 to 36 months", "over 36 months", "date unknown"]
    sg.row(r, ["Group"] + bands, S_HEAD)
    for g in SEGMENT_ORDER:
        people = [c for c in contacts if c["segment"] == g]
        if not people:
            continue
        r += 1
        sg.row(r, [SEGMENTS[g]["label"]] + [sum(1 for c in people if c.get("band") == b) for b in bands])
    sg.widths = {1: 30, 2: 10, 3: 50, 4: 12, 5: 16, 6: 14, 7: 30}
    sheets.append(sg)
    sheets.append(sc)

    # Send queue
    sq = office.Sheet("Send queue")
    cols = ["Date", "Day", "Ref", "Name", "Company", "Group", "Touch", "Channel", "Email or phone", "Purpose",
            "Subject", "Message", "Ready", "Written"]
    sq.row(1, cols, S_HEAD)
    sq.freeze_row = 2
    sq.widths = {1: 11, 2: 5, 3: 6, 4: 16, 5: 16, 6: 18, 7: 7, 8: 7, 9: 22, 10: 26, 11: 26, 12: 60, 13: 22, 14: 12}
    sq.landscape = True
    byref = {c["ref"]: c for c in contacts}
    for i, m in enumerate(sorted(msgs, key=lambda x: (x["date"], byref[x["ref"]]["rank"], x["n"])), start=2):
        c = byref[m["ref"]]
        dd = date.fromisoformat(m["date"])
        body = (f"Subject: {m['subject']}\n\n{m['body']}" if m["subject"] else m["body"])
        ready = "ready" if m["ready"] else "; ".join(f"[NEED: {x}]" for x in m["needs"]) or "fix: " + "; ".join(m["problems"])
        if c.get("address_needed") and m["ready"]:
            ready = {"email": "add their email first", "text": "add their number first",
                     "dm": "add their handle first"}[m["channel"]]
        addr = {"email": c.get("email", ""), "text": c.get("phone", ""), "dm": c.get("handle", "")}[m["channel"]]
        sq.row(i, [dd, DAY_NAMES[dd.weekday()], m["ref"], c.get("name") or c.get("email", ""), c.get("company", ""),
                   SEGMENTS[c["segment"]]["label"], f"{m['n']} of {m['of']}", m["channel"],
                   addr or "[address not in your notes: add it]", m.get("purpose", ""),
                   m["subject"], body, ready, m["kind"]], S_WRAP)
        sq.set(i, 1, dd, S_DATE)
    sq.autofilter = f"A1:N{max(2, len(msgs) + 1)}"
    sheets.append(sq)

    # Held back
    sh = office.Sheet("Held back")
    sh.row(1, HELD_COLS, S_HEAD)
    sh.freeze_row = 2
    sh.widths = {1: 6, 2: 18, 3: 18, 4: 24, 5: 14, 6: 14, 7: 40, 8: 40, 9: 12, 10: 12, 11: 40, 12: 30}
    for i, h in enumerate(sorted(held, key=lambda x: (x["held_code"], x["row"])), start=2):
        sh.row(i, [h["ref"], h.get("name") or h.get("email", ""), h.get("company", ""), h.get("email", ""),
                   h.get("phone", ""), h["held_code"], h["held_reason"], h["release"],
                   date.fromisoformat(h["revisit"]) if h.get("revisit") else "",
                   date.fromisoformat(h["last_contact"]) if h.get("last_contact") else "",
                   h.get("notes") or h.get("raw") or "", "; ".join(h.get("notes_flags", []))], S_WRAP)
        if h.get("revisit"):
            sh.set(i, 9, date.fromisoformat(h["revisit"]), S_DATE)
        if h.get("last_contact"):
            sh.set(i, 10, date.fromisoformat(h["last_contact"]), S_DATE)
    sh.autofilter = f"A1:L{max(2, len(held) + 1)}"
    sh.landscape = True
    sheets.append(sh)

    # Rules
    sr = office.Sheet("Rules")
    sr.widths = {1: 34, 2: 70}
    r = 1
    sr.set(r, 1, "How this plan was made", S_TITLE)
    r += 2
    sr.set(r, 1, "Priority score (higher goes first; change the plan by telling Claude, not by editing scores)", S_BOLD)
    r += 1
    sr.row(r, ["Factor", "Points"], S_HEAD)
    for g in SEGMENT_ORDER:
        r += 1
        sr.row(r, [f"Group: {SEGMENTS[g]['label']}", SEGMENTS[g]["warmth"]])
    for b, p in (("6 to 18 months since you spoke", 15), ("3 to 6 months", 12), ("1 to 3 months", 8),
                 ("18 to 36 months", 6), ("over 36 months", 0), ("date unknown", 3),
                 ("Their come-back date has arrived (or is within 14 days)", 15),
                 ("Past value in the top quarter of your list", 10), ("Past value in the second quarter", 5),
                 ("Their own words are on file", 5), ("Shared inbox address (info@, sales@)", -5),
                 ("You asked to move them up or down", "the points you gave")):
        r += 1
        sr.row(r, [b, p])
    r += 1
    sr.wide(r, ("Recency only orders and paces. The 6 to 18 month window scoring highest is a working default "
                "from sales practitioners, not a measured rate; your own replies replace it after a few runs."), S_NOTE,
            last_col=2, height=26)
    r += 2
    sr.set(r, 1, "Touch plans", S_BOLD)
    r += 1
    sr.row(r, ["Group", "Touches and day offsets"], S_HEAD)
    for g in SEGMENT_ORDER:
        r += 1
        sr.row(r, [SEGMENTS[g]["label"], f"{SEGMENTS[g]['touches']} touches on days "
                   + ", ".join(map(str, SEGMENTS[g]["offsets"])) + ". Over three years since you spoke: three touches."], S_WRAP)
    r += 2
    sr.set(r, 1, "Stop rules", S_BOLD)
    for line in ("Any reply stops that person's sequence: a yes, a no, a question, an out-of-office.",
                 "An opt-out, a bounce or a complaint stops it for good.",
                 "The last touch closes the file. Nobody is scheduled after it.",
                 f"After a finished sequence, nobody is messaged again for {s['cooldown_months']} months (the cooldown).",
                 "Anyone who asked to stop is never scheduled, on this run or any other."):
        r += 1
        sr.set(r, 1, "•", S_TEXT)
        sr.set(r, 2, line, S_WRAP)
    r += 2
    sr.set(r, 1, "Assumptions in force", S_BOLD)
    wd = ", ".join(DAY_NAMES[i] for i in plan["schedule"]["workdays"])
    for k, v in (("Dates", {"dmy": "day first", "mdy": "month first", "ymd": "year first"}[order]
                  + (f" ({plan.get('date_order_note')})" if plan.get("date_order_note") else "")),
                 ("Number style", {"comma": "1.234,56", "dot": "1,234.56"}.get(plan.get("decimal") or "dot")),
                 ("Sending days", wd), ("Days off you gave", ", ".join(show_date(d, order) for d in plan["schedule"]["days_off"]) or "none"),
                 ("Messages a day, at most", s["daily_cap"]), ("Hand-written first messages", s["tier_a"]),
                 ("Cooldown after a sequence", f"{s['cooldown_months']} months"),
                 ("Too recent to revive", f"under {s['too_recent_days']} days since you last spoke"),
                 ("Prices in messages", "never" if not s.get("price_from_touch") else f"from touch {s['price_from_touch']}, as you word them"),
                 ("Next step you want", s.get("next_step", "")),
                 ("What has changed since", "; ".join(s.get("changed") or []) or "nothing, so messages are honest questions"),
                 ("Channels you allowed", ", ".join(s["channels"]) + ("; texts only to people who texted you before"
                                                                     if "text" in s["channels"] and s.get("text_only_if_texted", True) else ""))):
        r += 1
        sr.row(r, [k, v], S_WRAP)
    r += 2
    sr.wide(r, COMPLIANCE_LINE, S_NOTE, last_col=2, height=26)
    fixes = [c for c in contacts + held if c.get("corrections")]
    if fixes:
        r += 2
        sr.set(r, 1, "Changes made from what you told me (say if any is wrong)", S_BOLD)
        r += 1
        sr.row(r, ["Who", "What changed"], S_HEAD)
        for c in fixes:
            r += 1
            sr.row(r, [f"{c['ref']} {c.get('name') or c.get('email', '')}", "; ".join(c["corrections"])], S_WRAP)
    r += 2
    sr.set(r, 1, "Keeping the log", S_BOLD)
    for line in ("Change Status on Contacts as things happen: sent, replied, call booked, won, no reply, stopped, bounced.",
                 "Put what they said in Reply notes. A date they give goes in Reply notes too.",
                 "Next time, bring this file back. Replies come off the plan, finished sequences go into the cooldown, "
                 "and the next batch is dated for you."):
        r += 1
        sr.set(r, 1, "•")
        sr.set(r, 2, line, S_WRAP)
    sheets.append(sr)
    paper = "Letter" if plan.get("paper") == "Letter" else "A4"
    office.write_xlsx(path, sheets, title=f"Revival plan {s.get('business', '')}".strip(), date_fmt=date_fmt_code(order),
                      paper=paper)


def add_months_iso(d, n):
    from common import add_months
    return add_months(date.fromisoformat(d), n)


def msg_ref(c, m):
    if m and m["kind"] == "hand-written" and m["n"] == 1:
        return f"T{c.get('today_rank') or c['rank']}"
    return f"{ABBR[c['segment']]}-{m['template'] if m else 1}"


LABELS = {"first_name": "[first name]", "full_name": "[full name]", "last_name": "[surname]", "greeting": "[greeting]",
          "company": "[company]",
          "context": "[personal field]", "when": "[when you last spoke]", "their_date": "[the date they gave]"}


def plain(text, s, ch):
    """A template as the founder reads it: their own name, offer and opt-out filled in, the per-person parts as plain
    labels in square brackets, never raw {fields}."""
    import re
    vals = {"sender": s.get("sign_off") or "[your name]", "business": s.get("business") or "[your business]",
            "next_step": s.get("next_step") or "[next step]", "changed": (s.get("changed") or ["[what has changed]"])[0],
            "opt_out": s.get("opt_out_short") if ch in ("text", "dm") else s.get("opt_out_email"), "detail": ""}
    return re.sub(r"\{(\w+)\}", lambda m: str(vals.get(m.group(1)) if m.group(1) in vals else LABELS.get(m.group(1), "[" + m.group(1) + "]")),
                  text or "")


def build_docx(plan, path):
    s = plan["settings"]
    order = plan["date_order"]
    contacts, msgs = plan["contacts"], plan["messages"]
    m_all = plan["messages_file"]
    today = date.fromisoformat(s["today"])
    d = office.Doc(paper="letter" if plan.get("paper") == "Letter" else "a4")
    biz = s.get("business") or "your business"
    d.para(f"Revival messages: {biz}", size=20, bold=True, after=60)
    d.para(f"Made {long_date(today, order)}. {len(contacts)} people to message, {len(plan['held'])} held back.",
           color="555555", after=200)
    d.h1("Read first")
    for rule in RULES_8:
        d.bullet(rule)
    d.para(COMPLIANCE_LINE, italic=True, before=120)
    d.para("How to use this with the tracker: the workbook's Send queue lists every message by date, ready to paste. "
           "This document holds the hand-written first messages, every group's sequence with its rules, and what to "
           "do when someone replies. Change Status on Contacts as you go and bring the workbook back next time.")
    d.page_break()
    top = sorted([c for c in contacts if c["tier"] == "A"], key=lambda x: x["today_rank"])
    d.h1(f"Today's {len(top)}" if len(top) != 10 else "Today's ten")
    d.para(f"The people most likely to reply who you can message on {long_date(plan['schedule']['start'], order)}. "
           "Written for each person from your notes. Read each one, change anything that does not sound like you, "
           "and send it yourself.")
    first = {}
    for m in msgs:
        first.setdefault(m["ref"], []).append(m)
    for c in top:
        ms = first.get(c["ref"], [])
        if not ms:
            continue
        m1 = ms[0]
        d.h3(f"T{c['today_rank']}. {c.get('name') or c.get('email', '')}" + (f", {c['company']}" if c.get("company") else ""))
        d.para(f"**{SEGMENTS[c['segment']]['label']}.** {c.get('why', '')}" + (" (reason inferred)" if c.get("why_inferred") else ""))
        addr = {"email": c.get("email"), "text": c.get("phone"), "dm": c.get("handle")}[m1["channel"]]
        d.para(f"Send on {long_date(m1['date'], order)} by {m1['channel']}" + (f" to {addr}" if addr else "") + ".",
               color="555555")
        if m1["subject"]:
            d.message(f"Subject: {m1['subject']}")
        d.message(m1["body"] if m1["body"] else "[NEED: the first message]")
        if not m1["ready"]:
            d.para("Not ready: " + "; ".join([f"[NEED: {x}]" for x in m1["needs"]] + m1["problems"]), bold=True)
        if len(ms) > 1:
            m2 = ms[1]
            d.para(f"Then touch 2 on {long_date(m2['date'], order)}: {m2.get('purpose') or 'the group sequence'} "
                   f"(message {ABBR[c['segment']]}-{m2['template']}, rendered for them on the Send queue).", color="555555")
    d.page_break()
    d.h1("The sequences")
    d.para("One block per group on your list. Words in square brackets are filled in for each person on the Send "
           "queue, where every message is written out in full; some people also get one line from their own notes at "
           "the start of their first message. The last touch in each group closes the file: it says plainly that you "
           "will not write again and leaves the door open. It never threatens or guilts, and it is often the message "
           "people answer.")
    tpl = m_all.get("templates", {})
    for g in SEGMENT_ORDER:
        people = [c for c in contacts if c["segment"] == g]
        if not people:
            continue
        d.h2(f"{SEGMENTS[g]['label']} ({len(people)} {'person' if len(people) == 1 else 'people'})")
        d.para(f"**The angle.** {ANGLE[g][0]}")
        d.para(f"**The stop.** {ANGLE[g][1]}")
        chans = sorted({c["channel"] for c in people})
        offs = SEGMENTS[g]["offsets"]
        for n in range(1, SEGMENTS[g]["touches"] + 1):
            t = (tpl.get(g) or {}).get(str(n)) or {}
            last = n == SEGMENTS[g]["touches"]
            d.h3(f"{ABBR[g]}-{n}. Day {offs[n - 1]}" + (": closing the file" if last else "")
                 + (f". {t.get('purpose')}" if t.get("purpose") and not (last and t["purpose"].lower().startswith("clos"))
                    else ""))
            for ch in chans:
                part = t.get(ch) if ch != "dm" else (t.get("dm") or t.get("text"))
                if not part:
                    d.para(f"[NEED: the {ch} version]", bold=True)
                    continue
                if isinstance(part, dict):
                    if part.get("subject"):
                        d.message(f"Subject: {plain(part['subject'], s, ch)}")
                    body = part.get("body", "")
                else:
                    body = part
                d.message(plain(body, s, ch))
    d.page_break()
    d.h1("When someone replies")
    d.para("Reply the same working day, yourself. Any reply stops that person's sequence: change their Status before "
           "the next day's sends.")
    rows = [["They say", "You do"]] + [[a, b.format(next_step=s.get("next_step") or "a call")] for a, b in REPLIES]
    d.table(rows, [2800, 6900])
    d.h1("Logging and the next run")
    for line in ("Change Status on the Contacts sheet as things happen. Put what they said in Reply notes.",
                 "A date someone gives you goes in Reply notes; next time it becomes their next touch.",
                 f"When a sequence ends with no reply, that person rests for {s['cooldown_months']} months.",
                 "Next time, bring the workbook back, or just say who replied and what they said. Replies and stops "
                 "come off the plan, the cooldown is respected, and the next batch is dated for you.",
                 "Your own reply and booked-call counts are the only numbers that matter here. Nothing in this plan "
                 "is a forecast."):
        d.bullet(line)
    d.save(path, footer=f"{biz}: revival messages, {show_date(today, order)}", title=f"Revival messages {biz}",
           lang=s.get("english") or "en")
