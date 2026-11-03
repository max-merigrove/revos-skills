#!/usr/bin/env python3
"""Date every touch on the founder's working days, at no more than their daily number, in priority order.

- A contact who named a come-back date gets touch 1 on that date (or the next working day), or as soon as
  possible if the date has passed.
- Touch n+1 is never earlier than touch n plus two days; offsets come from the group's touch plan.
- No day carries more than the daily cap, counting every touch of every contact.
- Founder days off are skipped. Nothing is scheduled after the last touch of a sequence.
Standard library only. No network calls.
"""
import re
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import Stop, fold  # noqa: E402
import ingest as ig  # noqa: E402

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
DAY_WORDS = {
    "mon": "mon monday montag mo lundi lun lunes lu", "tue": "tue tues tuesday dienstag di mardi mar martes",
    "wed": "wed wednesday mittwoch mi mercredi mer miercoles", "thu": "thu thur thurs thursday donnerstag do jeudi jeu jueves ju",
    "fri": "fri friday freitag fr vendredi ven viernes vi", "sat": "sat saturday samstag sa samedi sam sabado",
    "sun": "sun sunday sonntag so dimanche dim domingo",
}
WORD_DAY = {w: k for k, ws in DAY_WORDS.items() for w in ws.split()}


def working_days(text):
    """'mon-fri', 'Monday to Saturday', 'Sun-Thu', 'Mo-Fr', 'weekdays', 'mon, wed, fri' -> set of 0..6."""
    t = fold(text or "mon-fri")
    t = t.replace("\u2013", "-").replace(" to ", "-").replace(" bis ", "-").replace(" a ", "-").replace(" au ", "-")
    if re.search(r"week ?days|weekdays|wochentags|en semaine", t):
        return {0, 1, 2, 3, 4}
    if re.search(r"every ?day|7 days|all week|daily|taglich|tous les jours", t):
        return set(range(7))
    out = set()
    for part in re.split(r"[,;/&]|\band\b|\bund\b|\bet\b|\by\b", t):
        part = part.strip()
        if not part:
            continue
        m = re.fullmatch(r"([a-z]+)\.?\s*-\s*([a-z]+)\.?", part)
        if m and m.group(1) in WORD_DAY and m.group(2) in WORD_DAY:
            a, b = DAYS.index(WORD_DAY[m.group(1)]), DAYS.index(WORD_DAY[m.group(2)])
            i = a
            while True:
                out.add(i)
                if i == b:
                    break
                i = (i + 1) % 7
            continue
        w = part.strip(". ")
        if w in WORD_DAY:
            out.add(DAYS.index(WORD_DAY[w]))
            continue
        raise Stop(f"could not read the working days '{text}'",
                   ask="Which days do you send messages, for example Monday to Friday?")
    if not out:
        raise Stop(f"no working days in '{text}'", ask="Which days do you send messages?")
    return out


def days_off(items, order, country, today):
    """Founder-given days off: dates or ranges as written. Returns a set of dates."""
    out = set()
    for it in items or []:
        txt = str(it).strip()
        if not txt:
            continue
        parts = re.split(r"\s+(?:to|until|bis|au|al|-)\s+|\s*\u2013\s*|(?<=\d)\s*-\s*(?=\d{1,2}[./ ])", txt)
        if len(parts) == 2:
            a = _day(parts[0], order, country, today, ref=parts[1])
            b = _day(parts[1], order, country, today)
            if a and b and a <= b and (b - a).days < 60:
                d = a
                while d <= b:
                    out.add(d)
                    d += timedelta(days=1)
                continue
        d = _day(txt, order, country, today)
        if d is None:
            raise Stop(f"could not read the day off '{txt}'",
                       ask=f"What date is '{txt}'? Write it like 24 December 2026.")
        out.add(d)
    return out


def _day(txt, order, country, today, ref=None):
    t = txt.strip().rstrip(".")
    d, _a, _n = ig.parse_when(t, order, country, today)
    if d and not re.search(r"\d{4}|'\d{2}", t) and d < today:
        d = date(d.year + 1, d.month, d.day)
    if d and _a and re.fullmatch(r"[A-Za-z]+", t):
        d = None
    if d is None:
        m = re.fullmatch(r"(\d{1,2})[./]?\s*(?:of\s+)?([A-Za-zäéû]+)?\.?", t)
        if m and m.group(2):
            d = _day(f"{m.group(1)} {m.group(2)} {today.year}", order, country, today)
        elif m and ref:
            r = _day(ref, order, country, today)
            if r:
                d = date(r.year, r.month, int(m.group(1)))
        else:
            m = re.fullmatch(r"(\d{1,2})[./](\d{1,2})\.?", t)
            if m:
                a, b = int(m.group(1)), int(m.group(2))
                dd, mm = (b, a) if order == "mdy" else (a, b)
                try:
                    d = date(today.year, mm, dd)
                except ValueError:
                    return None
        if d and d < today:
            d = date(d.year + 1, d.month, d.day)
    return d


class Calendar:
    def __init__(self, workdays, off, cap, start):
        self.workdays, self.off, self.cap = workdays, off, cap
        self.load = {}
        self.start = self.next_open(start, ignore_cap=True)

    def is_work(self, d):
        return d.weekday() in self.workdays and d not in self.off

    def next_open(self, d, ignore_cap=False):
        for _ in range(3000):
            if self.is_work(d) and (ignore_cap or self.load.get(d, 0) < self.cap):
                return d
            d += timedelta(days=1)
        raise Stop("no working day found in the next eight years; check the working days and days off")

    def take(self, d):
        self.load[d] = self.load.get(d, 0) + 1


def schedule(contacts, s, order):
    wd = working_days(s.get("working_days"))
    off = days_off(s.get("days_off"), order, s.get("country"), s["today"])
    start = s.get("start")
    start = date.fromisoformat(start) if start else s["today"]
    if start < s["today"]:
        start = s["today"]
    cal = Calendar(wd, off, s["daily_cap"], start)
    for c in contacts:
        first = cal.start
        if c.get("parked_date"):
            pd = date.fromisoformat(c["parked_date"])
            if pd > first:
                first = pd
        offsets = c["offsets"]
        n0 = c.get("start_touch", 1)
        touches = []
        prev = None
        t1 = None
        for n in range(n0, c["touch_count"] + 1):
            if prev is None:
                d = cal.next_open(first)
                t1 = d
                base_offset = offsets[n - 1]
            else:
                target = t1 + timedelta(days=offsets[n - 1] - base_offset)
                d = cal.next_open(max(target, prev + timedelta(days=2)))
            cal.take(d)
            touches.append({"n": n, "date": d.isoformat(), "channel": c["channel"],
                            "last": n == c["touch_count"]})
            prev = d
        c["touches"] = touches
        c["next_touch"] = touches[0]["n"] if touches else None
        c["next_date"] = touches[0]["date"] if touches else None
        c["stop_after"] = touches[-1]["date"] if touches else None
    loads = sorted(cal.load.items())
    return {"workdays": sorted(wd), "days_off": sorted(d.isoformat() for d in off), "start": cal.start.isoformat(),
            "loads": {d.isoformat(): n for d, n in loads},
            "last_send": loads[-1][0].isoformat() if loads else None}
