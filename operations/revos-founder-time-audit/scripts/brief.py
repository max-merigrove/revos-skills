#!/usr/bin/env python3
"""Write a handover brief for one helper from an audit's results: what they will own, the hours each task
takes, when it happens now, what stays with the founder, when to come back, and the first weeks.

Usage:
  python3 brief.py <results.json> --who Ana --out <output folder> [--events events.json] [--facts facts.json]

facts.json holds only what the founder said, in their words (all optional):
  {"founder": "Maria",
   "tasks": {"Social scheduling": {"how": "content is in the Moss & Pine Shared drive; post once I have approved the batch",
                                   "access": "Buffer login from me"}},
   "all_tasks": {"access": "shared drive invite from me"},
   "keeps": ["pricing and scope on every proposal"],
   "escalate": ["any disputed invoice over $2,500"],
   "first_weeks": ["Thu 22 Oct: walk-through with me", "Fri 23 Oct: first social batch, I check it"]}

Anything the founder has not said is left as a [bracket] for them to fill: nothing is invented. Pay and contract
terms are never written into a brief. Figures come from results.json. Exit 2 and STOP: nothing was written.
"""
import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import report  # noqa: E402

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


class Stop(Exception):
    pass


def clock(hhmm, twelve):
    h, m = int(hhmm[:2]), int(hhmm[3:5])
    if not twelve:
        return f"{h:02d}:{m:02d}"
    sfx = "am" if h < 12 else "pm"
    h12 = h % 12 or 12
    return f"{h12}{'' if m == 0 else ':' + f'{m:02d}'}{sfx}"


def when_now(activity, events, twelve):
    """'Fridays 3pm' from the calendar entries of this activity: the most common day and start time."""
    seen = Counter()
    for e in events:
        if e.get("activity") != activity:
            continue
        try:
            st = datetime.fromisoformat(e["start"])
        except (KeyError, ValueError):
            continue
        seen[(st.weekday(), st.strftime("%H:%M"))] += 1
    if not seen:
        return ""
    days = sorted({d for d, _t in seen})
    times = Counter(t for (_d, t), n in seen.items() for _ in range(n)).most_common(1)[0][0]
    if len(days) >= 5:
        dtext = "Weekdays"
    else:
        dtext = ", ".join(DAYS[d] + "s" for d in days)
    return f"{dtext}, {clock(times, twelve)}"


def build(res, who, events, facts):
    rows = [x for x in res["rows"] if x["action"] == "delegate" and x.get("who")
            and re.search(r"\b" + re.escape(who.lower()) + r"\b", x["who"].lower())]
    if not rows:
        names = sorted({x["who"] for x in res["rows"] if x["action"] == "delegate" and x.get("who")})
        raise Stop(f"no handovers to {who} in the results" + (f"; handovers go to {', '.join(names)}" if names else ""))
    order = {n: i for i, n in enumerate(res["handovers"])}
    rows.sort(key=lambda x: order.get(x["activity"], 99))
    twelve = (res.get("locale") or {}).get("clock") == "12"
    tasks = facts.get("tasks") or {}
    me = facts.get("founder") or "me"
    total = sum(x["weekly_hours"] for x in rows)
    B = [("title", f"Handover brief for {who}"),
         ("sub", f"{res['business']} | from {me} | about {report.hrs(total)} a week")]
    B.append(("para", f"From now on you own the work below. Each line says what it is, roughly how long it takes, and when "
                      f"it happens now, so you can take the same slot. Ask {me} before you change how "
                      "something is done for a client."))
    B.append(("h2", "What you will own"))
    t = [["Work", "Hours a week", "When it happens now", "How to do it"]]
    for x in rows:
        tk = {**(facts.get("all_tasks") or {}), **(tasks.get(x["activity"]) or {})}
        how = tk.get("how") or "[steps, tools and where things live]"
        if tk.get("access"):
            how += f" Access: {tk['access']}."
        elif not tk.get("how"):
            how += " [logins and access]"
        t.append([x["activity"], report.h1(x["weekly_hours"]), when_now(x["activity"], events, twelve) or "[day and time]", how])
    B.append(("table", t))
    B.append(("h2", f"What stays with {me}"))
    keeps = facts.get("keeps") or res.get("protected") or []
    if keeps:
        for k in keeps:
            B.append(("bullet", str(k)))
    else:
        B.append(("bullet", "[the decisions that stay with me: prices, scope, client approvals]"))
    B.append(("h2", "When to come to me"))
    for e in facts.get("escalate") or ["[the amount, client decision or kind of problem that comes back to me]",
                                       "Anything you are unsure about, before it goes to a client."]:
        B.append(("bullet", str(e)))
    B.append(("h2", "First weeks"))
    for f in facts.get("first_weeks") or ["[date]: walk-through with me, doing each task once together",
                                          "[date]: first run on your own; I check it before it goes out",
                                          "[date]: check-in on what is unclear"]:
        B.append(("bullet", str(f)))
    B.append(("small", "A task is fully yours once you have done it on your own and I have reviewed it twice without changes."))
    return B


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("results")
    ap.add_argument("--who", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--events")
    ap.add_argument("--facts")
    a = ap.parse_args()
    try:
        res = json.loads(Path(a.results).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise Stop(f"could not read {a.results} ({e}); run rank.py first")
    events = []
    if a.events:
        try:
            events = json.loads(Path(a.events).read_text(encoding="utf-8")).get("events") or []
        except (FileNotFoundError, json.JSONDecodeError):
            events = []
    facts = {}
    if a.facts:
        try:
            facts = json.loads(Path(a.facts).read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError) as e:
            raise Stop(f"could not read {a.facts} ({e})")
    blob = json.dumps(facts).lower()
    if re.search(r"\b(per hour|an hour|/hr|hourly rate|salary|wage|contract terms?)\b", blob):
        raise Stop("pay and contract terms do not go in a handover brief; take them out of the facts file")
    report.set_style(res)
    B = build(res, a.who, events, facts)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    base = f"handover-brief-{report.slug(a.who)}-{report.slug(res['business'])}-{res['date']}"
    loc = res.get("locale") or {}
    lang = loc.get("lang") or ("en-US" if loc.get("spelling") == "american" or loc.get("date_style") == "mdy" else "en-GB")
    report.build_docx(B, out / f"{base}.docx", res["business"], paper=loc.get("paper") or "a4", lang=lang)
    md = report.to_markdown(B)
    (out / f"{base}.md").write_text(md, encoding="utf-8")
    left = []  # every bracket the founder still has to fill, counted in the brief itself, with where it sits
    section = ""
    for line in md.splitlines():
        if line.startswith("## "):
            section = line[3:]
        cells = [c.strip() for c in line.strip("|").split("|")] if line.startswith("|") else [line]
        for c in cells:
            for b in re.findall(r"\[[^\]]+\]", c):
                where = section + (f", {cells[0]}" if line.startswith("|") and cells[0] != c else "")
                left.append(f"{b} ({where})")
    print(f"WROTE: {out / (base + '.docx')}")
    print(f"WROTE: {out / (base + '.md')}")
    print(f"BRACKETS LEFT: {len(left)} (name these to the founder exactly; ask for them in one message)")
    for b in left:
        print(f"BRACKET: {b}")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Stop as e:
        print(f"STOP: {e}. Nothing was written.")
        sys.exit(2)
    except Exception as e:  # noqa: BLE001
        print(f"STOP: the brief could not be written ({type(e).__name__}: {e}). Nothing was written.")
        sys.exit(2)
