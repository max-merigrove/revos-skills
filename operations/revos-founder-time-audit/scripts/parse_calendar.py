#!/usr/bin/env python3
"""Founder Time Audit: read calendar exports and a tracked week into activities with hours.

Usage:
  python3 scripts/parse_calendar.py <file> [<file> ...] --out <folder>
        [--weeks 2] [--from YYYY-MM-DD --to YYYY-MM-DD] [--today YYYY-MM-DD]
        [--tz America/New_York] [--me you@example.com] [--date-order dmy|mdy]
        [--work-hours 8:30-17:30] [--work-days mon-fri] [--holidays 2026-11-26,2026-11-27]
        [--map map.json]

Founder's locale, never assumed:
  Time zone   --tz, else the calendar's own zone (X-WR-TIMEZONE, then the zone most events use).
              Floating times (most CSVs, the one-week log) need no zone. Times given only in UTC
              with no zone named stop the run with one question.
  Working week --work-days and --work-hours when the founder gave them, else Outlook's own
              working-hours setting in the export, else what the events show (the weekdays booked in
              at least half the weeks, from the typical first start to the typical last finish).
              Too thin a calendar to tell: an ASK line, and no empty-diary count.
  Holidays    --holidays (dates the founder named), plus all-day events in the calendar that say
              they are a public holiday, come from a holidays calendar, or are the founder's own day
              off ("Annual leave", "Day off", "PTO", "Out of office", Outlook's out-of-office status).
              No country's holiday list is built in.
  Dates       CSV day or month first: --date-order, else the dates themselves (a day above 12), else
              the reading that puts the entries in recent weeks; if both readings fit, one question.

Reads:
  .ics   Google Calendar, Outlook (desktop, web, new Outlook) and Apple Calendar exports.
         Repeating events are expanded from their RRULE (DAILY, WEEKLY, MONTHLY, YEARLY with
         INTERVAL, COUNT, UNTIL, BYDAY with positions, BYMONTHDAY, BYMONTH, BYSETPOS, WKST),
         with EXDATE, RDATE and moved or cancelled single instances (RECURRENCE-ID).
         Time zones: IANA names, Windows names ("GMT Standard Time"), Outlook display names,
         and the file's own VTIMEZONE blocks when the computer has no time zone data.
  .csv   Outlook's calendar CSV export (day or month first), or any CSV with a title, a start and
         an end or duration column (a time tracker export, a spreadsheet).
  .csv / .xlsx  The one-week time log from this skill's assets (30-minute blocks).

Leaves out: all-day events (listed), meetings you declined, cancelled events, and events
outside the audit window. Overlapping events share the overlapping time, so hours are never
counted twice. Writes <out>/activities.json (the draft audit, one row per activity) and
<out>/events.json (every counted instance). Prints a summary to read back to the founder.

Exit codes: 0 written, 2 stopped (a STOP line says what to do). Standard library only.
No network calls.
"""
import argparse
import csv
import io
import json
import re
import statistics
import sys
import zipfile
from datetime import date, datetime, time, timedelta, timezone, tzinfo
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
from timeparse import DAY_HOURS, WEEKS_PER_MONTH, InputError, hours as parse_hours  # noqa: E402

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:  # very old Python: fall back to the file's own VTIMEZONE blocks
    ZoneInfo = None
    ZoneInfoNotFoundError = Exception
if __import__("os").environ.get("TIME_AUDIT_TEST_NO_TZDATA"):  # tests: behave like a computer with no zone data
    ZoneInfo = None

SKILL = "revos-founder-time-audit"
DAYS_PER_MONTH = 7 * WEEKS_PER_MONTH

# Public holidays are never looked up: they come from the founder (--holidays) or from all-day events
# in the calendar itself. These words recognise them.
PUBLIC_HOLIDAY_WORDS = re.compile(r"\b(public|bank|national|federal|government|stat|state|civic) holiday\b|"
                                  r"\bholidays? in [A-Z]|\bobservance\b", re.I)
OWN_DAY_OFF = re.compile(r"^\s*(my |me )?(annual leave|day off|days off|holiday|holidays|vacation|vacation day|pto|leave|"
                         r"on leave|out of office|ooo|off|office closed|closed|public holiday|bank holiday)\b", re.I)
# Anywhere in the title: the business is closed, so the founder is off too ("Indigenous Peoples' Day - studio closed").
CLOSED_ANYWHERE = re.compile(r"\b(closed|close early|no work|shut for|office shut|studio shut|business shut)\b", re.I)
# Anywhere in the title, unless a person's name comes first ("Devin OOO" is a colleague's absence, not the founder's).
OFF_ANYWHERE = re.compile(r"\b(day off|days off|ooo|out of office|pto|annual leave|on leave|vacation)\b", re.I)
_OFF_WORDS = r"(?:day off|days off|ooo|out of office|pto|annual leave|on leave|vacation|off|away|holiday)"
SOMEONE_ELSE = re.compile(r"^\s*(?!(?i:my|me|team|studio|office|company|whole|all|everyone|the)\b)[A-Z][\w'.-]*"
                          r"(?:\s+(?!(?i:" + _OFF_WORDS[3:-1] + r")\b)[A-Z][\w'.-]*)?(?:'s)?\s*[:(-]?\s*(?i:" + _OFF_WORDS[3:-1] + r")\b")


def own_day_off(title, busy=""):
    """True when an all-day entry is the founder's own day off or a day the business is closed."""
    if OWN_DAY_OFF.match(title) or busy == "OOF" or CLOSED_ANYWHERE.search(title):
        return True
    return bool(OFF_ANYWHERE.search(title)) and not SOMEONE_ELSE.match(title)

# Clock rules for common zones, used only when the computer has no time zone database and the export
# carries no VTIMEZONE block for the zone. Each: standard offset, and (daylight offset, start rule,
# start local time, end rule, end local time) or None. Rules are RRULE text, as in a VTIMEZONE.
_US = ("FREQ=YEARLY;BYMONTH=3;BYDAY=2SU", (2, 0), "FREQ=YEARLY;BYMONTH=11;BYDAY=1SU", (2, 0))
_EU = ("FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU", None, "FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU", None)  # 01:00 UTC
_AU = ("FREQ=YEARLY;BYMONTH=10;BYDAY=1SU", (2, 0), "FREQ=YEARLY;BYMONTH=4;BYDAY=1SU", (3, 0))
_NZ = ("FREQ=YEARLY;BYMONTH=9;BYDAY=-1SU", (2, 0), "FREQ=YEARLY;BYMONTH=4;BYDAY=1SU", (3, 0))
ZONE_RULES = {
    "America/New_York": (-5, _US), "America/Toronto": (-5, _US), "America/Chicago": (-6, _US),
    "America/Denver": (-7, _US), "America/Phoenix": (-7, None), "America/Los_Angeles": (-8, _US),
    "America/Vancouver": (-8, _US), "America/Anchorage": (-9, _US), "Pacific/Honolulu": (-10, None),
    "Europe/London": (0, _EU), "Europe/Dublin": (0, _EU), "Europe/Lisbon": (0, _EU), "Europe/Paris": (1, _EU),
    "Europe/Berlin": (1, _EU), "Europe/Amsterdam": (1, _EU), "Europe/Madrid": (1, _EU), "Europe/Rome": (1, _EU),
    "Europe/Stockholm": (1, _EU), "Europe/Warsaw": (1, _EU), "Europe/Athens": (2, _EU), "Europe/Helsinki": (2, _EU),
    "Asia/Singapore": (8, None), "Asia/Kuala_Lumpur": (8, None), "Asia/Hong_Kong": (8, None), "Asia/Shanghai": (8, None),
    "Asia/Manila": (8, None), "Asia/Taipei": (8, None), "Asia/Tokyo": (9, None), "Asia/Seoul": (9, None),
    "Asia/Jakarta": (7, None), "Asia/Bangkok": (7, None), "Asia/Ho_Chi_Minh": (7, None), "Asia/Kolkata": (5.5, None),
    "Asia/Dubai": (4, None), "Africa/Johannesburg": (2, None), "Africa/Lagos": (1, None), "Africa/Nairobi": (3, None),
    "Australia/Sydney": (10, _AU), "Australia/Melbourne": (10, _AU), "Australia/Hobart": (10, _AU),
    "Australia/Adelaide": (9.5, _AU), "Australia/Brisbane": (10, None), "Australia/Darwin": (9.5, None),
    "Australia/Perth": (8, None), "Pacific/Auckland": (12, _NZ), "UTC": (0, None),
}

WINDOWS_TZ = {
    "gmt standard time": "Europe/London", "greenwich standard time": "Atlantic/Reykjavik",
    "w. europe standard time": "Europe/Berlin", "romance standard time": "Europe/Paris",
    "central europe standard time": "Europe/Budapest", "central european standard time": "Europe/Warsaw",
    "e. europe standard time": "Europe/Chisinau", "fle standard time": "Europe/Kiev", "gtb standard time": "Europe/Bucharest",
    "russian standard time": "Europe/Moscow", "turkey standard time": "Europe/Istanbul", "israel standard time": "Asia/Jerusalem",
    "south africa standard time": "Africa/Johannesburg", "arabian standard time": "Asia/Dubai",
    "india standard time": "Asia/Kolkata", "singapore standard time": "Asia/Singapore", "china standard time": "Asia/Shanghai",
    "tokyo standard time": "Asia/Tokyo", "aus eastern standard time": "Australia/Sydney",
    "e. australia standard time": "Australia/Brisbane", "cen. australia standard time": "Australia/Adelaide",
    "w. australia standard time": "Australia/Perth", "new zealand standard time": "Pacific/Auckland",
    "eastern standard time": "America/New_York", "central standard time": "America/Chicago",
    "mountain standard time": "America/Denver", "us mountain standard time": "America/Phoenix",
    "pacific standard time": "America/Los_Angeles", "alaskan standard time": "America/Anchorage",
    "hawaiian standard time": "Pacific/Honolulu", "atlantic standard time": "America/Halifax",
    "canada central standard time": "America/Regina", "sa pacific standard time": "America/Bogota",
    "e. south america standard time": "America/Sao_Paulo", "argentina standard time": "America/Buenos_Aires",
    "malay peninsula standard time": "Asia/Singapore", "se asia standard time": "Asia/Bangkok",
    "korea standard time": "Asia/Seoul", "taipei standard time": "Asia/Taipei",
    "aus central standard time": "Australia/Darwin", "tasmania standard time": "Australia/Hobart",
    "nz standard time": "Pacific/Auckland", "pakistan standard time": "Asia/Karachi", "bangladesh standard time": "Asia/Dhaka",
    "egypt standard time": "Africa/Cairo", "w. central africa standard time": "Africa/Lagos",
    "e. africa standard time": "Africa/Nairobi", "us eastern standard time": "America/Indianapolis",
    "utc": "UTC", "coordinated universal time": "UTC",
}
CITY_TZ = {"london": "Europe/London", "dublin": "Europe/Dublin", "edinburgh": "Europe/London", "lisbon": "Europe/Lisbon",
           "paris": "Europe/Paris", "berlin": "Europe/Berlin", "amsterdam": "Europe/Amsterdam", "madrid": "Europe/Madrid",
           "brussels": "Europe/Brussels", "rome": "Europe/Rome", "stockholm": "Europe/Stockholm", "athens": "Europe/Athens",
           "helsinki": "Europe/Helsinki", "eastern time": "America/New_York", "central time": "America/Chicago",
           "mountain time": "America/Denver", "pacific time": "America/Los_Angeles", "sydney": "Australia/Sydney",
           "melbourne": "Australia/Melbourne", "brisbane": "Australia/Brisbane", "perth": "Australia/Perth",
           "auckland": "Pacific/Auckland", "dubai": "Asia/Dubai", "singapore": "Asia/Singapore", "tokyo": "Asia/Tokyo",
           "johannesburg": "Africa/Johannesburg", "toronto": "America/Toronto", "new york": "America/New_York",
           "chicago": "America/Chicago", "denver": "America/Denver", "los angeles": "America/Los_Angeles",
           "san francisco": "America/Los_Angeles", "seattle": "America/Los_Angeles", "vancouver": "America/Vancouver",
           "boston": "America/New_York", "washington": "America/New_York", "miami": "America/New_York",
           "austin": "America/Chicago", "dallas": "America/Chicago", "phoenix": "America/Phoenix",
           "hong kong": "Asia/Hong_Kong", "kuala lumpur": "Asia/Kuala_Lumpur", "jakarta": "Asia/Jakarta",
           "bangkok": "Asia/Bangkok", "manila": "Asia/Manila", "shanghai": "Asia/Shanghai", "beijing": "Asia/Shanghai",
           "seoul": "Asia/Seoul", "taipei": "Asia/Taipei", "mumbai": "Asia/Kolkata", "delhi": "Asia/Kolkata",
           "bangalore": "Asia/Kolkata", "bengaluru": "Asia/Kolkata", "kolkata": "Asia/Kolkata",
           "adelaide": "Australia/Adelaide", "canberra": "Australia/Sydney", "hobart": "Australia/Hobart",
           "darwin": "Australia/Darwin", "wellington": "Pacific/Auckland", "lagos": "Africa/Lagos",
           "nairobi": "Africa/Nairobi", "cape town": "Africa/Johannesburg", "abu dhabi": "Asia/Dubai"}
WD = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

HINT_WORDS = {
    "personal": r"\b(gym|dentist|doctor|gp|physio|school run|school|nursery|pick ?up|drop ?off|kids?|lunch|dinner|"
                r"birthday|haircut|hair|workout|yoga|swim|holiday|vacation|annual leave|date night|family|wedding|vet|"
                r"personal|private|pilates|football|tennis|golf|church|therapy|counselling|walk the dog|dog walk)\b",
    "delete test": r"\b(status|update|catch ?up|catch-up|check ?in|check-in|sync|stand ?up|stand-up|huddle|weekly meeting|"
                   r"team meeting|all hands|touch ?base)\b",
    "admin": r"\b(invoice|invoicing|admin|e-?mails?|inbox|expenses|bookkeeping|payroll|scheduling|diary|reports?|"
             r"reporting|timesheets?|xero|quickbooks|filing|data entry|booking|bank|vat|gst|sales tax|accounts|chasing|paperwork)\b",
    "selling": r"\b(discovery|sales|prospect|demo|intro|pitch|proposal|follow ?up|lead|networking|consultation|"
               r"strategy call|enquiry|quote)\b",
    "strategy": r"\b(strategy|planning|plan|think|thinking|quarterly|offsite|pricing|roadmap|budget|board|goals|"
                r"review the month|monthly review|deep work)\b",
    "managing": r"\b(1:1|1-1|121|one to one|one-to-one|1on1|team|hiring|interview|training|onboard \w+ hire|appraisal|"
                r"supervision)\b",
}
CHALLENGE_WORDS = r"\b(invoice|invoicing|admin|e-?mails?|inbox|expenses|bookkeeping|payroll|schedul\w*|diary|reports?|" \
                  r"reporting|timesheets?|filing|data entry|booking|status|minutes|chasing|paperwork|formatting)\b"


def stop(msg):
    print(f"STOP: {msg}")
    sys.exit(2)


# ----------------------------------------------------------------------------- time zones
class VTimezone(tzinfo):
    """A tzinfo built from a file's VTIMEZONE block: used when the computer has no zone data."""

    def __init__(self, tzid, comps):
        self.tzid = tzid
        self.comps = comps  # list of dicts: kind, start (naive), off_from, off_to, rule, rdates
        self._cache = {}

    def _transitions(self, year):
        if year in self._cache:
            return self._cache[year]
        out = []
        for c in self.comps:
            starts = []
            if c["rule"]:
                rule = parse_rrule(c["rule"])
                lo = datetime(year - 1, 1, 1)
                hi = datetime(year + 1, 12, 31)
                starts = [s for s in expand_rule(c["start"], rule, hi, None) if s >= lo]
            else:
                starts = [c["start"]]
            starts += c["rdates"]
            out += [(s, c["off_from"], c["off_to"], c["kind"]) for s in starts]
        out.sort()
        self._cache[year] = out
        return out

    def _active(self, dt):
        naive = dt.replace(tzinfo=None)
        tr = [t for t in self._transitions(naive.year) if t[0] <= naive]
        if tr:
            return tr[-1]
        first = sorted(self.comps, key=lambda c: c["start"])[0]
        return (first["start"], first["off_from"], first["off_from"], first["kind"])

    def utcoffset(self, dt):
        return self._active(dt)[2] if dt is not None else timedelta(0)

    def dst(self, dt):
        if dt is None:
            return timedelta(0)
        a = self._active(dt)
        std = [c["off_to"] for c in self.comps if c["kind"] == "STANDARD"]
        return a[2] - std[0] if std and a[3] == "DAYLIGHT" else timedelta(0)

    def tzname(self, dt):
        return self.tzid


def _offset(s):
    m = re.fullmatch(r"([+-])(\d{2})(\d{2})(\d{2})?", s.strip())
    if not m:
        return timedelta(0)
    d = timedelta(hours=int(m.group(2)), minutes=int(m.group(3)), seconds=int(m.group(4) or 0))
    return -d if m.group(1) == "-" else d


class TZResolver:
    def __init__(self, vtimezones, default_name, notes):
        self.vtz = vtimezones
        self.notes = notes
        self.cache = {}
        self.default = self.get(default_name) if default_name else None

    def _zone(self, name):
        if ZoneInfo is None:
            return None
        try:
            return ZoneInfo(name)
        except (ZoneInfoNotFoundError, ValueError, KeyError, OSError):
            return None

    def get(self, tzid):
        if tzid in self.cache:
            return self.cache[tzid]
        name = (tzid or "").strip().strip('"').lstrip("/")
        z = None
        if name.upper() in ("UTC", "Z", "GMT", "ETC/UTC"):
            z = timezone.utc
        if z is None:
            z = self._zone(name)
        if z is None and name.lower() in WINDOWS_TZ:
            z = self._zone(WINDOWS_TZ[name.lower()])
        if z is None:
            low = name.lower()
            for city, iana in CITY_TZ.items():
                if city in low:
                    z = self._zone(iana)
                    if z:
                        break
        if z is None and tzid in self.vtz:
            z = self.vtz[tzid]
        if z is None and name in self.vtz:
            z = self.vtz[name]
        if z is None:
            z = builtin_zone(WINDOWS_TZ.get(name.lower(), name))
        if z is None:
            low = name.lower()
            for city, iana in CITY_TZ.items():
                if city in low:
                    z = builtin_zone(iana)
                    if z:
                        break
        if z is None:
            fallback = getattr(self, "default", None)
            if fallback is None:
                raise InputError(f"the time zone '{name}' is not one I recognise; say which city or time zone you work in")
            self.notes.append(f"time zone '{name}' not recognised; read those times in the audit's time zone")
            z = fallback
        self.cache[tzid] = z
        return z


def builtin_zone(name):
    """Clock rules for a common zone from ZONE_RULES, for computers with no zone data. None if not covered."""
    spec = ZONE_RULES.get(name)
    if spec is None:
        return None
    std_h, dst = spec
    std = timedelta(hours=std_h)
    if dst is None:
        return VTimezone(name, [{"kind": "STANDARD", "start": datetime(1970, 1, 1), "off_from": std, "off_to": std,
                                 "rule": None, "rdates": []}])
    on_rule, on_at, off_rule, off_at = dst
    day = std + timedelta(hours=1)
    if on_at is None:  # the European rule: 01:00 UTC, so the local time depends on the zone
        on_local = datetime(1996, 1, 1, 1, 0) + std
        off_local = datetime(1996, 1, 1, 1, 0) + day
        on_at, off_at = (on_local.hour, on_local.minute), (off_local.hour, off_local.minute)
    return VTimezone(name, [
        {"kind": "DAYLIGHT", "start": datetime(1996, 1, 1, *on_at), "off_from": std, "off_to": day,
         "rule": on_rule, "rdates": []},
        {"kind": "STANDARD", "start": datetime(1996, 1, 1, *off_at), "off_from": day, "off_to": std,
         "rule": off_rule, "rdates": []},
    ])


# ----------------------------------------------------------------------------- RRULE
def parse_rrule(s):
    r = {}
    for part in s.strip().split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            r[k.strip().upper()] = v.strip()
    out = {"FREQ": r.get("FREQ", "").upper(), "INTERVAL": max(1, int(r.get("INTERVAL", "1") or 1)),
           "COUNT": int(r["COUNT"]) if r.get("COUNT", "").isdigit() else None, "UNTIL": r.get("UNTIL"),
           "WKST": WD.get(r.get("WKST", "MO").upper(), 0), "BYDAY": [], "BYMONTHDAY": [], "BYMONTH": [], "BYSETPOS": [],
           "UNSUPPORTED": [k for k in r if k in ("BYYEARDAY", "BYWEEKNO", "BYHOUR", "BYMINUTE", "BYSECOND")]}
    for tok in filter(None, r.get("BYDAY", "").upper().split(",")):
        m = re.fullmatch(r"([+-]?\d{1,2})?(MO|TU|WE|TH|FR|SA|SU)", tok.strip())
        if m:
            out["BYDAY"].append((int(m.group(1)) if m.group(1) else None, WD[m.group(2)]))
    for k in ("BYMONTHDAY", "BYMONTH", "BYSETPOS"):
        out[k] = [int(x) for x in r.get(k, "").split(",") if re.fullmatch(r"[+-]?\d+", x.strip())]
    return out


def _days_in_month(y, m):
    return ((date(y + (m == 12), m % 12 + 1, 1)) - date(y, m, 1)).days


def _month_dates(y, m, rule, dstart):
    n = _days_in_month(y, m)
    md = None
    if rule["BYMONTHDAY"]:
        md = set()
        for d in rule["BYMONTHDAY"]:
            dd = d if d > 0 else n + d + 1
            if 1 <= dd <= n:
                md.add(date(y, m, dd))
    wd = None
    if rule["BYDAY"]:
        wd = set()
        for pos, day in rule["BYDAY"]:
            alld = [date(y, m, i) for i in range(1, n + 1) if date(y, m, i).weekday() == day]
            if pos is None:
                wd.update(alld)
            elif 1 <= abs(pos) <= len(alld):
                wd.add(alld[pos - 1] if pos > 0 else alld[pos])
    if md is not None and wd is not None:
        return sorted(md & wd)
    if md is not None:
        return sorted(md)
    if wd is not None:
        return sorted(wd)
    return [date(y, m, dstart.day)] if dstart.day <= n else []


def _setpos(dates, rule):
    if not rule["BYSETPOS"] or not dates:
        return dates
    dates = sorted(dates)
    out = []
    for p in rule["BYSETPOS"]:
        if 1 <= abs(p) <= len(dates):
            out.append(dates[p - 1] if p > 0 else dates[p])
    return sorted(set(out))


def expand_rule(dtstart, rule, end_limit, until, max_periods=200000):
    """Expand a parsed RRULE from a naive wall-clock dtstart. Returns naive datetimes up to end_limit
    (inclusive), stopping at UNTIL (naive, same wall clock) and COUNT. DTSTART is always the first."""
    freq, iv = rule["FREQ"], rule["INTERVAL"]
    if freq not in ("DAILY", "WEEKLY", "MONTHLY", "YEARLY"):
        return [dtstart]
    t = dtstart.time()
    out = [dtstart]
    count = rule["COUNT"]
    d0 = dtstart.date()

    def keep(c):
        if c <= dtstart:
            return True
        if until is not None and c > until:
            return False
        if c > end_limit:
            return False
        out.append(c)
        return count is None or len(out) < count

    def done():
        return count is not None and len(out) >= count

    for p in range(max_periods):
        if done():
            break
        if freq == "DAILY":
            d = d0 + timedelta(days=p * iv)
            cands = [d]
            if rule["BYMONTH"] and d.month not in rule["BYMONTH"]:
                cands = []
            if rule["BYMONTHDAY"]:
                n = _days_in_month(d.year, d.month)
                if not any((x if x > 0 else n + x + 1) == d.day for x in rule["BYMONTHDAY"]):
                    cands = []
            if rule["BYDAY"] and d.weekday() not in [w for _p, w in rule["BYDAY"]]:
                cands = []
            pstart = d
        elif freq == "WEEKLY":
            ws = d0 - timedelta(days=(d0.weekday() - rule["WKST"]) % 7) + timedelta(weeks=p * iv)
            days = [w for _p, w in rule["BYDAY"]] or [d0.weekday()]
            cands = sorted(ws + timedelta(days=(w - rule["WKST"]) % 7) for w in set(days))
            if rule["BYMONTH"]:
                cands = [c for c in cands if c.month in rule["BYMONTH"]]
            cands = _setpos(cands, rule)
            pstart = ws
        elif freq == "MONTHLY":
            mi = d0.month - 1 + p * iv
            y, m = d0.year + mi // 12, mi % 12 + 1
            if rule["BYMONTH"] and m not in rule["BYMONTH"]:
                cands = []
            else:
                cands = _setpos(_month_dates(y, m, rule, d0), rule)
            pstart = date(y, m, 1)
        else:  # YEARLY
            y = d0.year + p * iv
            months = rule["BYMONTH"] or [d0.month]
            cands = []
            if rule["BYDAY"] and not rule["BYMONTH"] and not rule["BYMONTHDAY"] and any(pp for pp, _w in rule["BYDAY"]):
                yd = [date(y, 1, 1) + timedelta(days=i) for i in range(366 if _days_in_month(y, 2) == 29 else 365)]
                for pos, day in rule["BYDAY"]:
                    alld = [x for x in yd if x.weekday() == day]
                    if pos is None:
                        cands += alld
                    elif 1 <= abs(pos) <= len(alld):
                        cands.append(alld[pos - 1] if pos > 0 else alld[pos])
            else:
                for m in months:
                    if rule["BYDAY"] or rule["BYMONTHDAY"]:
                        cands += _month_dates(y, m, rule, d0)
                    elif d0.day <= _days_in_month(y, m):
                        cands.append(date(y, m, d0.day))
            cands = _setpos(sorted(set(cands)), rule)
            pstart = date(y, 1, 1)
        if datetime.combine(pstart, time(0)) > end_limit or (until is not None and datetime.combine(pstart, time(0)) > until):
            break
        for c in cands:
            if not keep(datetime.combine(c, t)):
                return sorted(set(out))
    return sorted(set(out))


# ----------------------------------------------------------------------------- ICS reading
def _split_prop(line):
    inq = False
    for i, ch in enumerate(line):
        if ch == '"':
            inq = not inq
        elif ch == ":" and not inq:
            head, value = line[:i], line[i + 1:]
            break
    else:
        return None
    parts = []
    buf, inq = "", False
    for ch in head:
        if ch == '"':
            inq = not inq
            buf += ch
        elif ch == ";" and not inq:
            parts.append(buf)
            buf = ""
        else:
            buf += ch
    parts.append(buf)
    name = parts[0].strip().upper()
    params = {}
    for p in parts[1:]:
        if "=" in p:
            k, v = p.split("=", 1)
            params[k.strip().upper()] = v.strip().strip('"')
    return name, params, value


def _unescape(s):
    return s.replace("\\n", " ").replace("\\N", " ").replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\").strip()


def read_text(path):
    data = Path(path).read_bytes()
    for enc in ("utf-8-sig", "utf-16", "cp1252", "latin-1"):
        try:
            txt = data.decode(enc)
            if enc == "utf-16" and "BEGIN" not in txt and "," not in txt:
                continue
            return txt
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1", errors="replace")


def parse_ics(text):
    lines = []
    for raw in re.split(r"\r\n|\n|\r", text):
        if raw[:1] in (" ", "\t") and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    stack, cal, events, vtz_raw = [], {}, [], {}
    cur = None
    for ln in lines:
        if not ln.strip():
            continue
        pr = _split_prop(ln)
        if not pr:
            continue
        name, params, value = pr
        if name == "BEGIN":
            comp = {"_type": value.strip().upper(), "_props": {}, "_children": []}
            if stack:
                stack[-1]["_children"].append(comp)
            stack.append(comp)
            continue
        if name == "END":
            if stack:
                comp = stack.pop()
                if comp["_type"] == "VEVENT":
                    events.append(comp)
                elif comp["_type"] == "VTIMEZONE":
                    tzid = comp["_props"].get("TZID", [({}, "")])[0][1]
                    vtz_raw[tzid] = comp
                elif comp["_type"] == "VCALENDAR":
                    cal = comp
            continue
        if stack:
            cur = stack[-1]
            cur["_props"].setdefault(name, []).append((params, value))
    if not cal and events:
        cal = {"_props": {}}
    return cal, events, vtz_raw


def build_vtimezones(vtz_raw):
    out = {}
    for tzid, comp in vtz_raw.items():
        comps = []
        for ch in comp["_children"]:
            if ch["_type"] not in ("STANDARD", "DAYLIGHT"):
                continue
            pp = ch["_props"]
            try:
                start = datetime.strptime(pp["DTSTART"][0][1].strip()[:15], "%Y%m%dT%H%M%S")
            except (KeyError, ValueError):
                start = datetime(1970, 1, 1)
            rdates = []
            for _p, v in pp.get("RDATE", []):
                for x in v.split(","):
                    try:
                        rdates.append(datetime.strptime(x.strip()[:15], "%Y%m%dT%H%M%S"))
                    except ValueError:
                        pass
            comps.append({"kind": ch["_type"], "start": start,
                          "off_from": _offset(pp.get("TZOFFSETFROM", [({}, "+0000")])[0][1]),
                          "off_to": _offset(pp.get("TZOFFSETTO", [({}, "+0000")])[0][1]),
                          "rule": pp.get("RRULE", [({}, None)])[0][1], "rdates": rdates})
        if comps:
            out[tzid] = VTimezone(tzid, comps)
    return out


def parse_dt(value, params, tzr):
    """Return (aware datetime or date, is_date, wall naive, tz)."""
    v = value.strip()
    if params.get("VALUE", "").upper() == "DATE" or re.fullmatch(r"\d{8}", v):
        d = datetime.strptime(v[:8], "%Y%m%d").date()
        return d, True, datetime.combine(d, time(0)), tzr.default
    m = re.fullmatch(r"(\d{8}T\d{6})(Z?)", v[:16] if v.endswith("Z") else v[:15])
    if not m:
        raise InputError(f"could not read the date '{value}' in the calendar file")
    naive = datetime.strptime(m.group(1), "%Y%m%dT%H%M%S")
    if v.endswith("Z"):
        tz = timezone.utc
    elif "TZID" in params:
        tz = tzr.get(params["TZID"])
    else:
        tz = tzr.default
    return naive.replace(tzinfo=tz), False, naive, tz


def parse_duration(s):
    m = re.fullmatch(r"([+-])?P(?:(\d+)W)?(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?", s.strip())
    if not m:
        return None
    d = timedelta(weeks=int(m.group(2) or 0), days=int(m.group(3) or 0), hours=int(m.group(4) or 0),
                  minutes=int(m.group(5) or 0), seconds=int(m.group(6) or 0))
    return -d if m.group(1) == "-" else d


def ics_instances(path, text, args, notes, me, win_lo, win_hi, audit_tz):
    cal, events, vtz_raw = parse_ics(text)
    if not events:
        return [], {}
    cp = cal.get("_props", {})
    calname = cp.get("X-WR-CALNAME", [({}, "")])[0][1].strip()
    if "@" in calname and not args.me:
        me.add(calname.lower())
        notes.append(f"read declined meetings for {calname}, the calendar's owner")
    vtzs = build_vtimezones(vtz_raw)
    tzr = TZResolver(vtzs, None, notes)
    tzr.default = audit_tz
    meta = {"x_wr_timezone": cp.get("X-WR-TIMEZONE", [({}, "")])[0][1].strip(), "calname": calname}
    masters, overrides = {}, {}
    singles = []
    for i, ev in enumerate(events):
        p = ev["_props"]
        uid = p.get("UID", [({}, f"no-uid-{i}")])[0][1].strip()
        if "RECURRENCE-ID" in p:
            overrides.setdefault(uid, []).append(ev)
        elif "RRULE" in p or "RDATE" in p:
            masters.setdefault(uid, []).append(ev)
        else:
            singles.append((uid, ev))
    out = []
    unsupported = set()
    # expansion bounds in wall-clock terms, with a day of margin each side for zone differences
    lo_naive = (win_lo - timedelta(days=2)).replace(tzinfo=None)
    hi_naive = (win_hi + timedelta(days=2)).replace(tzinfo=None)

    def base(ev, uid):
        p = ev["_props"]
        if "DTSTART" not in p:
            return None
        sp, sv = p["DTSTART"][0]
        start, is_date, wall, tz = parse_dt(sv, sp, tzr)
        if "DTEND" in p:
            ep, evv = p["DTEND"][0]
            end, _d, _w, _t = parse_dt(evv, ep, tzr)
        elif "DURATION" in p and parse_duration(p["DURATION"][0][1]) is not None:
            end = start + parse_duration(p["DURATION"][0][1])
        else:
            end = start + (timedelta(days=1) if is_date else timedelta(0))
        dur = end - start if not is_date else (end - start)
        att = p.get("ATTENDEE", [])
        partstat = None
        for ap, av in att:
            em = re.sub(r"^mailto:", "", av.strip(), flags=re.I).lower()
            if em in me:
                partstat = ap.get("PARTSTAT", "").upper() or None
        any_declined = any(ap.get("PARTSTAT", "").upper() == "DECLINED" for ap, _v in att)
        busy = p.get("X-MICROSOFT-CDO-BUSYSTATUS", [({}, "")])[0][1].strip().upper()
        return {"uid": uid, "summary": _unescape(p.get("SUMMARY", [({}, "(no title)")])[0][1]) or "(no title)",
                "start": start, "is_date": is_date, "wall": wall, "tz": tz, "dur": dur,
                "status": p.get("STATUS", [({}, "")])[0][1].strip().upper(),
                "transp": p.get("TRANSP", [({}, "")])[0][1].strip().upper(), "busy": busy,
                "partstat": partstat, "any_declined": any_declined, "attendees": len(att),
                "rrule": p.get("RRULE", [({}, None)])[0][1],
                "desc": _unescape(p.get("DESCRIPTION", [({}, "")])[0][1])[:200]}

    def key_of(dt, is_date):
        return dt.isoformat() if is_date else dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%S")

    def exdates(ev, tz):
        keys = set()
        for xp, xv in ev["_props"].get("EXDATE", []):
            for x in xv.split(","):
                x = x.strip()
                if not x:
                    continue
                try:
                    d, isd, _w, _t = parse_dt(x, xp, tzr)
                except InputError:
                    continue
                keys.add(key_of(d, isd))
        return keys

    def emit(b, start, series, rule_text):
        if b["is_date"]:
            st = datetime.combine(start if isinstance(start, date) and not isinstance(start, datetime) else start.date(),
                                  time(0), tzinfo=audit_tz)
            en = st + b["dur"]
            allday = True
        else:
            st = start.astimezone(audit_tz)
            en = st + b["dur"]
            allday = False
        src_tz = None if b["is_date"] or not isinstance(start, datetime) or start.tzinfo is None else \
            (getattr(start.tzinfo, "key", None) or getattr(start.tzinfo, "tzid", None))
        src_wall = start.strftime("%H:%M") if src_tz else None
        out.append({"set_in": src_tz, "set_at": src_wall, "uid": b["uid"], "summary": b["summary"], "start": st, "end": en, "all_day": allday,
                    "series": series, "rule": rule_text, "status": b["status"], "transp": b["transp"], "busy": b["busy"],
                    "partstat": b["partstat"], "any_declined": b["any_declined"], "attendees": b["attendees"],
                    "file": Path(path).name, "desc": b.get("desc", ""), "calname": calname})

    for uid, ev in singles:
        b = base(ev, uid)
        if b:
            emit(b, b["start"], False, None)
    series_rules = {}
    for uid, evs in masters.items():
        ev = evs[0]
        b = base(ev, uid)
        if not b:
            continue
        rule_text = b["rrule"]
        exk = exdates(ev, b["tz"])
        ov = {}
        for o in overrides.get(uid, []):
            rp, rv = o["_props"]["RECURRENCE-ID"][0]
            try:
                rid, risd, _w, _t = parse_dt(rv, rp, tzr)
            except InputError:
                continue
            ov[key_of(rid, risd)] = o
        walls = []
        if rule_text:
            rule = parse_rrule(rule_text)
            unsupported.update(rule["UNSUPPORTED"])
            until = None
            if rule["UNTIL"]:
                try:
                    u, uisd, uwall, _t = parse_dt(rule["UNTIL"], {}, tzr)
                    if uisd:
                        until = datetime.combine(u, time(23, 59, 59))
                    elif rule["UNTIL"].strip().endswith("Z") and b["tz"] is not None and not b["is_date"]:
                        until = u.astimezone(b["tz"]).replace(tzinfo=None)
                    else:
                        until = uwall
                except InputError:
                    until = None
            walls = expand_rule(b["wall"], rule, hi_naive, until)
            series_rules[uid] = {"rule": rule, "rule_text": rule_text, "wall": b["wall"], "tz": b["tz"], "until": until, "is_date": b["is_date"],
                                 "summary": b["summary"], "dur": b["dur"], "partstat": b["partstat"]}
        else:
            walls = [b["wall"]]
        for xp, xv in ev["_props"].get("RDATE", []):
            for x in xv.split(","):
                try:
                    d, isd, w, _t = parse_dt(x.strip(), xp, tzr)
                    walls.append(w if not isd else datetime.combine(d, b["wall"].time()))
                except InputError:
                    continue
        for w in sorted(set(walls)):
            if w < lo_naive - timedelta(days=1) and w + b["dur"] < lo_naive:
                continue
            if b["is_date"]:
                inst = w.date()
                k = key_of(inst, True)
            else:
                tz = b["tz"] or audit_tz
                inst = w.replace(tzinfo=tz)
                k = key_of(inst, False)
            if k in exk:
                continue
            if k in ov:
                ob = base(ov.pop(k), uid)
                if ob and ob["status"] != "CANCELLED":
                    if ob["partstat"] is None:
                        ob["partstat"] = b["partstat"]
                    emit(ob, ob["start"], True, rule_text)
                continue
            emit(b, inst, True, rule_text)
        for _k, o in ov.items():  # overrides whose original slot fell outside the expansion
            ob = base(o, uid)
            if ob and ob["status"] != "CANCELLED":
                emit(ob, ob["start"], True, rule_text)
    # overrides with no master in the file (exported singly)
    for uid, evs in overrides.items():
        if uid in masters:
            continue
        for o in evs:
            ob = base(o, uid)
            if ob:
                emit(ob, ob["start"], True, None)
    if unsupported:
        notes.append(f"repeat rules using {', '.join(sorted(unsupported))} were read at their start time only")
    meta["series_rules"] = series_rules
    meta["tzr"] = tzr
    return out, meta


# ----------------------------------------------------------------------------- CSV and the one-week log
ALIASES = {
    "title": ["subject", "title", "summary", "event", "event name", "activity", "task", "description", "what", "name"],
    "start_date": ["start date", "startdate", "date", "day"],
    "start_time": ["start time", "starttime", "from"],
    "end_date": ["end date", "enddate"],
    "end_time": ["end time", "endtime", "to", "until"],
    "start": ["start", "start datetime", "starts", "begin"],
    "end": ["end", "end datetime", "ends", "finish"],
    "duration": ["duration", "hours", "length", "time spent", "duration (h)", "duration (hours)"],
    "all_day": ["all day event", "all day", "all-day", "allday"],
    "show_as": ["show time as", "show as", "busy status"],
    "required": ["required attendees"],
}


def _find_cols(header):
    low = [h.strip().lower() for h in header]
    cols = {}
    for key, names in ALIASES.items():
        for n in names:
            if n in low:
                cols[key] = low.index(n)
                break
    return cols


DATE_FORMATS_DMY = ["%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d", "%d %b %Y", "%d %B %Y", "%a %d %b %Y"]
DATE_FORMATS_MDY = ["%m/%d/%Y", "%m/%d/%y", "%m-%d-%Y", "%Y-%m-%d", "%b %d %Y", "%B %d %Y", "%b %d, %Y", "%B %d, %Y"]
TIME_FORMATS = ["%H:%M:%S", "%H:%M", "%I:%M:%S %p", "%I:%M %p", "%I:%M:%S%p", "%I:%M%p", "%I %p", "%I%p", "%H.%M"]


def _date_order(rows, idxs):
    a_big = b_big = False
    for r in rows:
        for i in idxs:
            if i is None or i >= len(r):
                continue
            m = re.match(r"\s*(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})", r[i])
            if m:
                if int(m.group(1)) > 12:
                    a_big = True
                if int(m.group(2)) > 12:
                    b_big = True
    if a_big and not b_big:
        return "dmy", True
    if b_big and not a_big:
        return "mdy", True
    return None, False


def _pdate(s, order):
    s = re.sub(r"\s+", " ", s.strip().replace(",", ", ").replace(" ,", ",")).strip()
    for f in (DATE_FORMATS_DMY if order == "dmy" else DATE_FORMATS_MDY):
        try:
            return datetime.strptime(s.replace(", ", ",").replace(",", ", ") if "%b %d," in f or "%B %d," in f else s, f).date()
        except ValueError:
            continue
    raise InputError(f"could not read the date '{s}'")


def _ptime(s):
    s = s.strip().upper().replace(".", ":") if re.search(r"\d\.\d{2}", s) else s.strip().upper()
    for f in TIME_FORMATS:
        try:
            return datetime.strptime(s, f).time()
        except ValueError:
            continue
    raise InputError(f"could not read the time '{s}'")


def _pdatetime(s, order):
    s = s.strip()
    m = re.match(r"(\d{4}-\d{2}-\d{2})[T ](\d{1,2}:\d{2}(?::\d{2})?)", s)
    if m:
        return datetime.combine(date.fromisoformat(m.group(1)), _ptime(m.group(2)))
    m = re.match(r"(.+?)\s+(\d{1,2}[:.]\d{2}(?::\d{2})?\s*(?:[AaPp][Mm])?)$", s)
    if m:
        return datetime.combine(_pdate(m.group(1), order), _ptime(m.group(2)))
    return datetime.combine(_pdate(s, order), time(0))


def csv_rows(text):
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    return [r for r in csv.reader(io.StringIO(text), dialect) if any(c.strip() for c in r)]


def is_log(rows):
    for r in rows[:12]:
        low = [c.strip().lower() for c in r]
        if low and low[0] in ("time", "start", "block") and any(x in low for x in ("monday", "mon")):
            return True
    return False


def log_instances(rows, path, args, notes, audit_tz, today):
    hdr_i = next(i for i, r in enumerate(rows[:12]) if r and r[0].strip().lower() in ("time", "start", "block")
                 and any(x.strip().lower() in ("monday", "mon") for x in r))
    week_start = None
    for r in rows[:hdr_i]:
        for c in r:
            c = c.strip()
            if not c:
                continue
            if re.fullmatch(r"\d{5}(\.0+)?", c):
                week_start = date(1899, 12, 30) + timedelta(days=int(float(c)))
                break
            reads = []
            for order in ([args.date_order] if args.date_order else ["dmy", "mdy"]):
                try:
                    reads.append(_pdate(c, order))
                except InputError:
                    continue
            if reads:
                # day or month first: the reading in recent weeks wins
                week_start = sorted(set(reads), key=lambda d: (not (today - timedelta(days=84) <= d <= today + timedelta(days=7)),
                                                               abs((today - d).days)))[0]
                if len(set(reads)) > 1:
                    notes.append(f"read the log's week-starting date '{c}' as {week_start.isoformat()}, the reading in recent weeks")
            if week_start:
                break
        if week_start:
            break
    if week_start is None:
        if args.date_from:
            week_start = date.fromisoformat(args.date_from)
        else:
            week_start = today - timedelta(days=today.weekday() + 7)
        notes.append(f"the log has no week-starting date; read it as the week of {week_start.isoformat()}")
    head = [c.strip().lower()[:3] for c in rows[hdr_i]]
    day_col = {}
    for i, h in enumerate(head):
        for k, v in (("mon", 0), ("tue", 1), ("wed", 2), ("thu", 3), ("fri", 4), ("sat", 5), ("sun", 6)):
            if h == k:
                day_col[v] = i
    slots = []
    for r in rows[hdr_i + 1:]:
        if not r or not r[0].strip():
            continue
        c0 = r[0].strip()
        try:
            if re.fullmatch(r"0?\.\d+", c0):
                mins = round(float(c0) * 24 * 60)
                tt = time(mins // 60 % 24, mins % 60)
            else:
                tt = _ptime(re.split(r"\s*(?:-|to)\s*", c0)[0])
        except InputError:
            continue
        slots.append((tt, r))
    if len(slots) < 2:
        stop(f"{Path(path).name} looks like the one-week log but has fewer than two time rows; fill it in 30-minute rows")
    step = timedelta(minutes=30)
    t0, t1 = datetime.combine(week_start, slots[0][0]), datetime.combine(week_start, slots[1][0])
    if t1 > t0:
        step = t1 - t0
    out = []
    ditto = {'"', "''", "ditto", "same", "^", "as above", "cont", "cont.", "contd", "..."}
    for day, ci in day_col.items():
        prev = None
        cur = None
        for tt, r in slots:
            txt = r[ci].strip() if ci < len(r) else ""
            if txt.lower() in ditto and prev:
                txt = prev
            st = datetime.combine(week_start + timedelta(days=(day - week_start.weekday()) % 7), tt).replace(tzinfo=audit_tz)
            if txt and cur and cur["summary"].lower() == txt.lower() and cur["end"] == st:
                cur["end"] = st + step
            else:
                if cur:
                    out.append(cur)
                cur = None
                if txt:
                    cur = {"uid": f"log-{day}-{tt}", "summary": txt, "start": st, "end": st + step, "all_day": False,
                           "series": False, "rule": None, "status": "", "transp": "", "busy": "", "partstat": None,
                           "any_declined": False, "attendees": 0, "file": Path(path).name, "tracked": True}
            prev = txt
        if cur:
            out.append(cur)
    if not out:
        stop(f"{Path(path).name} is the one-week log but it is empty. Write a few words for each half hour as you go "
             "through the week, then attach it again")
    notes.append(f"read {Path(path).name} as a tracked week in {int(step.total_seconds() // 60)}-minute blocks")
    return out, week_start


def xlsx_rows(path):
    try:
        z = zipfile.ZipFile(path)
    except zipfile.BadZipFile:
        stop(f"{Path(path).name} is not a readable spreadsheet; save it as .xlsx or .csv and attach it again")
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in root.findall("m:si", ns):
            shared.append("".join(t.text or "" for t in si.iter("{%s}t" % ns["m"])))
    sheets = sorted(n for n in z.namelist() if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n))
    if not sheets:
        stop(f"{Path(path).name} has no worksheet I can read")
    best = []
    for sh in sheets:
        root = ET.fromstring(z.read(sh))
        grid = {}
        for c in root.iter("{%s}c" % ns["m"]):
            ref = c.get("r", "")
            m = re.fullmatch(r"([A-Z]+)(\d+)", ref)
            if not m:
                continue
            col = 0
            for ch in m.group(1):
                col = col * 26 + ord(ch) - 64
            row = int(m.group(2))
            t = c.get("t")
            v = c.find("m:v", ns)
            if t == "s" and v is not None:
                val = shared[int(v.text)]
            elif t == "inlineStr":
                val = "".join(x.text or "" for x in c.iter("{%s}t" % ns["m"]))
            else:
                val = v.text if v is not None and v.text is not None else ""
            grid[(row, col)] = val
        if not grid:
            continue
        nr, nc = max(r for r, _c in grid), max(c for _r, c in grid)
        rows = [[grid.get((r, c), "") for c in range(1, nc + 1)] for r in range(1, nr + 1)]
        rows = [r for r in rows if any(str(x).strip() for x in r)]
        if is_log(rows):
            return rows
        if not best:
            best = rows
    return best


DATE_ORDER_SEEN = [None]


def slashed_any(body, cols):
    sc = cols.get("start_date", cols.get("start", 0))
    return any(r and sc < len(r) and re.match(r"\s*\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}", r[sc]) for r in body)


def csv_instances(rows, path, args, notes, audit_tz, today):
    hdr = None
    for i, r in enumerate(rows[:5]):
        cols = _find_cols(r)
        if "title" in cols and ("start" in cols or "start_date" in cols):
            hdr = i
            break
    if hdr is None:
        stop(f"{Path(path).name} does not look like a calendar export: I need columns for a title and a start "
             "(Outlook: File, Open and Export, Import/Export, Export to a file, Comma Separated Values, Calendar)")
    cols = _find_cols(rows[hdr])
    low = [h.strip().lower() for h in rows[hdr]]
    if any(h in low for h in ("amount", "balance", "debit", "credit", "paid out", "paid in", "money in", "money out")):
        stop(f"{Path(path).name} looks like a bank statement, not a calendar. Attach a calendar export "
             "(Google Calendar: Settings, Import and export, Export; Outlook: File, Save Calendar), or describe last week")
    if not any(k in cols for k in ("start_time", "end_time", "end", "duration")) and "start" not in cols:
        stop(f"{Path(path).name} has dates but no times or durations, so there are no hours to count. "
             "Attach a calendar export, or describe last week")
    body = rows[hdr + 1:]
    order = args.date_order
    if not order:
        order, sure = _date_order(body, [cols.get("start_date"), cols.get("end_date"), cols.get("start"), cols.get("end")])
        sc = cols.get("start_date", cols.get("start", 0))
        slashed = [r[sc] for r in body if r and sc < len(r) and re.match(r"\s*\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}", r[sc])]
        if not order and slashed:
            # both readings are possible: keep the one that puts the entries in recent weeks
            def recent(o):
                n = 0
                for v in slashed:
                    try:
                        d = _pdate(re.split(r"[ T]", v.strip())[0], o)
                    except InputError:
                        continue
                    n += (today - timedelta(days=84)) <= d <= (today + timedelta(days=7))
                return n
            dmy, mdy = recent("dmy"), recent("mdy")
            if dmy != mdy:
                order = "dmy" if dmy > mdy else "mdy"
                notes.append(f"dates in {Path(path).name} could be day first or month first; read them "
                             f"{'day first' if order == 'dmy' else 'month first'}, the only reading that puts them in recent weeks")
            else:
                stop(f"the dates in {Path(path).name} could be day first or month first ('{slashed[0].strip()}'), and both "
                     "readings are plausible. Ask the founder which, then run again with --date-order dmy (day first) or "
                     "--date-order mdy (month first)")
        order = order or "dmy"
    DATE_ORDER_SEEN[0] = DATE_ORDER_SEEN[0] or (order if slashed_any(body, cols) else None)
    out = []
    for n, r in enumerate(body, start=hdr + 2):
        g = lambda k: (r[cols[k]].strip() if k in cols and cols[k] < len(r) else "")  # noqa: E731
        title = g("title") or "(no title)"
        try:
            if "start_date" in cols:
                sd = _pdate(g("start_date"), order)
                st_t = _ptime(g("start_time")) if g("start_time") else time(0)
                st = datetime.combine(sd, st_t)
            else:
                st = _pdatetime(g("start"), order)
            if g("end_date") or g("end_time"):
                ed = _pdate(g("end_date"), order) if g("end_date") else st.date()
                et = _ptime(g("end_time")) if g("end_time") else time(0)
                en = datetime.combine(ed, et)
            elif g("end"):
                en = _pdatetime(g("end"), order)
            elif g("duration"):
                h, _note = parse_hours(g("duration"), "duration")
                en = st + timedelta(hours=h or 0)
            else:
                en = st
        except InputError as e:
            notes.append(f"row {n} of {Path(path).name} skipped: {e}")
            continue
        allday = g("all_day").lower() in ("true", "yes", "1", "y")
        if en < st:
            en += timedelta(days=1)
        show = g("show_as").lower()
        out.append({"uid": f"csv-{n}", "summary": title, "start": st.replace(tzinfo=audit_tz),
                    "end": en.replace(tzinfo=audit_tz), "all_day": allday, "series": False, "rule": None, "status": "",
                    "transp": "TRANSPARENT" if show in ("0", "free") else "", "busy": "", "partstat": None,
                    "any_declined": False, "attendees": len([x for x in re.split(r";", g("required")) if x.strip()]),
                    "file": Path(path).name})
    return out


# ----------------------------------------------------------------------------- grouping and output
def norm_title(s):
    s = s.lower()
    s = re.sub(r"\b(re|fw|fwd|updated invitation|invitation|canceled|cancelled|accepted|tentative)\s*:\s*", "", s)
    s = re.sub(r"\d{1,2}[:.]\d{2}\s*(am|pm)?", " ", s)
    s = re.sub(r"\b\d{1,2}(st|nd|rd|th)?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)\w*\b", " ", s)
    s = re.sub(r"[^\w&/+ ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s or "(no title)"


def load_map(path):
    if not path:
        return []
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        stop(f"there is no map file at {path}")
    except json.JSONDecodeError as e:
        stop(f"the map file is not valid JSON ({e.msg} on line {e.lineno}); fix it and run again")
    rules = data.get("rules", data) if isinstance(data, dict) else data
    if not isinstance(rules, list):
        stop("the map file should hold a list of rules, each with 'match' and 'activity'")
    out = []
    for i, r in enumerate(rules, 1):
        if not isinstance(r, dict) or not r.get("match") or not r.get("activity"):
            stop(f"map rule {i} needs a 'match' and an 'activity'")
        m = str(r["match"])
        try:
            rx = re.compile(m[3:], re.I) if m.startswith("re:") else re.compile(re.escape(m.lower()), re.I)
        except re.error as e:
            stop(f"map rule {i} has a pattern that is not valid ({e}); fix it and run again")
        out.append((rx, r))
    return out


def match_map(title, rules):
    for rx, r in rules:
        if rx.search(title):
            return r
    return None


def hints(label, titles):
    text = " ".join([label] + titles).lower()
    out = [k for k, rx in HINT_WORDS.items() if re.search(rx, text)]
    if "personal" in out and any(k in out for k in ("selling", "admin", "managing", "strategy")):
        out.remove("personal")
    return out


def someone_out(allday, d_from, d_to):
    """All-day entries that are a colleague's absence ('Devin OOO'): {name: set of dates}."""
    out = {}
    for x in allday:
        if x["status"] == "CANCELLED" or x["partstat"] == "DECLINED":
            continue
        m = SOMEONE_ELSE.match(x["summary"].strip())
        if not m:
            continue
        name = re.sub(r"'s?$", "", re.match(r"\s*([A-Z][\w'.-]*)", x["summary"]).group(1))
        d0 = max(x["start"].date(), d_from)
        d1 = min((x["end"] - timedelta(seconds=1)).date(), d_to)
        while d0 <= d1:
            out.setdefault(name, set()).add(d0)
            d0 += timedelta(days=1)
    return out


def find_clashes(work, personal, holidays, away):
    """Things a sharp assistant would point out in the first reply: double bookings, work booked over a
    personal entry (never named), work booked on a day off, and meetings with a colleague the calendar shows
    as out that day. Grouped by the entries involved, with every date."""
    groups = {}

    def add(kind, entries, x, y=None):
        lo = x["start"] if y is None else max(x["start"], y["start"])
        hi = x["end"] if y is None else min(x["end"], y["end"])
        key = (kind, tuple(entries))
        g = groups.setdefault(key, {"kind": kind, "entries": list(entries), "when": []})
        w = f"{DAY_NAMES[lo.weekday()][:3]} {lo.date().isoformat()} {lo:%H:%M}-{hi:%H:%M}"
        if w not in g["when"]:
            g["when"].append(w)

    home = getattr(work[0]["start"].tzinfo, "key", None) or getattr(work[0]["start"].tzinfo, "tzid", None) if work else None

    def label(x):
        t = x["summary"].strip()
        z = x.get("set_in")
        if z and home and z != home and z not in ("UTC", "Etc/UTC", "GMT"):
            t += f" (set for {x['set_at']} {z} time)"
        return t

    def looks_personal(x):
        return not x.get("map") and "personal" in hints(x["summary"], [])

    priv = [p for p in personal if str((p.get("map") or {}).get("category", "")).lower() == "personal"]
    priv += [x for x in work if looks_personal(x)]
    ws = sorted([x for x in work if not looks_personal(x)], key=lambda x: x["start"])
    for i, a in enumerate(ws):
        for b in ws[i + 1:]:
            if b["start"] >= a["end"]:
                break
            if a["summary"].strip() != b["summary"].strip():
                add("double booked", sorted([label(a), label(b)]), a, b)
    for a in ws:
        for p in priv:
            if p["start"] < a["end"] and p["end"] > a["start"]:
                add("booked over a personal entry", [a["summary"].strip()], a, p)
        if a["start"].date() in holidays:
            add("booked on a day off", [a["summary"].strip()], a)
        for name, dates in away.items():
            if a["start"].date() in dates and re.search(r"\b" + re.escape(name) + r"\b", a["summary"], re.I):
                add(f"booked with {name} on a day the calendar shows {name} out", [a["summary"].strip()], a)
    return sorted(groups.values(), key=lambda g: (g["when"][0][4:], g["kind"]))


def sweep(insts):
    """Give each instance its share of time, splitting overlaps equally. Returns union hours."""
    pts = []
    for i, x in enumerate(insts):
        x["counted_hours"] = 0.0
        if x["end"] > x["start"]:
            pts.append((x["start"], 1, i))
            pts.append((x["end"], -1, i))
    pts.sort(key=lambda p: (p[0], p[1]))
    active, last, union, overlap = set(), None, 0.0, 0.0
    for t, kind, i in pts:
        if last is not None and active and t > last:
            seg = (t - last).total_seconds() / 3600
            union += seg
            if len(active) > 1:
                overlap += seg
            for j in active:
                insts[j]["counted_hours"] += seg / len(active)
        if kind == 1:
            active.add(i)
        else:
            active.discard(i)
        last = t
    return union, overlap


def rule_per_month(info, win_lo_naive):
    """Times a month from a repeat rule, over the 52 weeks from the window start. None if the series ends sooner."""
    rule = info["rule"]
    span_end = win_lo_naive + timedelta(days=364)
    walls = expand_rule(info["wall"], rule, span_end, info["until"])
    inside = [w for w in walls if win_lo_naive <= w < span_end]
    if (info["until"] is not None and info["until"] < span_end - timedelta(days=1)) or \
            (rule["COUNT"] is not None and len(walls) >= rule["COUNT"] and walls and walls[-1] < span_end - timedelta(days=7)):
        return None
    return len(inside) / 12 if inside else None


def describe_rule(rule_text):
    if not rule_text:
        return ""
    r = parse_rrule(rule_text)
    f = {"DAILY": "day", "WEEKLY": "week", "MONTHLY": "month", "YEARLY": "year"}.get(r["FREQ"], r["FREQ"].lower())
    every = f"every {r['INTERVAL']} {f}s" if r["INTERVAL"] > 1 else f"every {f}"
    if r["BYDAY"]:
        names = []
        for pos, wd in r["BYDAY"]:
            nm = DAY_NAMES[wd]
            if pos:
                nm = {1: "first", 2: "second", 3: "third", 4: "fourth", -1: "last"}.get(pos, f"{pos}th") + " " + nm
            names.append(nm)
        every += " on " + ", ".join(names)
    return "repeats " + every


WD3 = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


def clock(t):
    return f"{t.hour}:{t.minute:02d}" if t.minute else f"{t.hour}"


def parse_work_hours(text):
    m = re.fullmatch(r"(\d{1,2})(?:[:.](\d{2}))?\s*(am|pm)?\s*(?:-|to)\s*(\d{1,2})(?:[:.](\d{2}))?\s*(am|pm)?",
                     text.strip().lower())
    if not m:
        stop("--work-hours should look like 9-18, 8:30-17:30 or 8am-5pm")
    h1, h2 = int(m.group(1)), int(m.group(4))
    if m.group(3) == "pm" and h1 < 12:
        h1 += 12
    if m.group(6) == "pm" and h2 < 12:
        h2 += 12
    if not m.group(6) and h2 <= h1 and h2 + 12 <= 23:
        h2 += 12
    a, b = time(h1 % 24, int(m.group(2) or 0)), time(min(h2, 23), int(m.group(5) or 0) if h2 < 24 else 59)
    if b <= a:
        stop("--work-hours should end after it starts, like 9-18")
    return a, b


def order_days(days):
    """Order working days as a week reads: start after the longest run of days off."""
    days = sorted(set(days))
    if not days or len(days) == 7:
        return days
    best, start = -1, days[0]
    for i, d in enumerate(days):
        prev = days[i - 1]
        gap = (d - prev) % 7
        if gap > best:
            best, start = gap, d
    return [(start + k) % 7 for k in range(7) if (start + k) % 7 in days]


def parse_work_days(text):
    t = text.strip().lower()
    m = re.fullmatch(r"([a-z]{3})[a-z]*\s*(?:-|to)\s*([a-z]{3})[a-z]*", t)
    if m and m.group(1) in WD3 and m.group(2) in WD3:
        a, b = WD3[m.group(1)], WD3[m.group(2)]
        return [(a + k) % 7 for k in range((b - a) % 7 + 1)]
    days = [WD3[x[:3]] for x in re.split(r"[,/\s]+|\band\b", t) if x[:3] in WD3]
    if not days:
        stop("--work-days should look like mon-fri, sun-thu or mon,tue,wed,thu,fri,sat")
    return order_days(days)


def outlook_work_hours(loaded):
    """Outlook writes the owner's own working hours into an .ics export. Returns ((start, end), days) or None."""
    for _p, kind, data in loaded:
        if kind != "ics":
            continue
        a = re.search(r"^X-MS-OLK-WKHRSTART[^:\r\n]*:(\d{2})(\d{2})", data, re.M)
        b = re.search(r"^X-MS-OLK-WKHREND[^:\r\n]*:(\d{2})(\d{2})", data, re.M)
        d = re.search(r"^X-MS-OLK-WKHRDAYS:([A-Z,]+)", data, re.M)
        hours = (time(int(a.group(1)), int(a.group(2))), time(int(b.group(1)), int(b.group(2)))) if a and b else None
        days = order_days([WD[x] for x in d.group(1).split(",") if x in WD]) if d else None
        if hours or days:
            return hours, days
    return None


def infer_pattern(day_segs, holidays):
    """The working week the events show: weekdays booked for at least an hour in at least half the weeks (and two
    hours on average), from the typical first start to the typical last finish, to the half hour.
    Returns ((start, end) or None, [weekdays] or None)."""
    by_wd = {}
    for d, segs in day_segs.items():
        if d in holidays:
            continue
        booked = sum((e - s).total_seconds() for s, e in segs) / 3600
        by_wd.setdefault(d.weekday(), []).append((d, booked, segs))
    days = []
    for wd, occ in by_wd.items():
        active = [x for x in occ if x[1] >= 1]
        if len(active) * 2 >= len(occ) and sum(x[1] for x in occ) / len(occ) >= 2:
            days.append(wd)
    active_dates = [x for wd in days for x in by_wd[wd] if x[1] >= 1]
    if len(days) < 3 or len(active_dates) < 3:
        return None, None
    starts = sorted(x[2][0][0].hour * 60 + x[2][0][0].minute for x in active_dates)
    ends = sorted(x[2][-1][1].hour * 60 + x[2][-1][1].minute or 24 * 60 for x in active_dates)
    st = statistics.median_low(starts) // 30 * 30
    en = -(-statistics.median_high(ends) // 30) * 30
    if en <= st or en - st < 4 * 60:
        return None, order_days(days)
    en = min(en, 23 * 60 + 59)
    return (time(st // 60, st % 60), time(en // 60, en % 60)), order_days(days)


def fmt(x, dp=1):
    return f"{round(x, dp):g}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--weeks", type=float, default=2)
    ap.add_argument("--from", dest="date_from")
    ap.add_argument("--to", dest="date_to")
    ap.add_argument("--today")
    ap.add_argument("--tz")
    ap.add_argument("--me", default="")
    ap.add_argument("--date-order", choices=["dmy", "mdy"])
    ap.add_argument("--work-hours")
    ap.add_argument("--work-days")
    ap.add_argument("--holidays", default="")
    ap.add_argument("--map")
    args = ap.parse_args()
    notes = []
    today = date.fromisoformat(args.today) if args.today else date.today()
    me = {x.strip().lower() for x in args.me.split(",") if x.strip()}
    rules = load_map(args.map)

    pattern_src = None
    wh_start = wh_end = work_days = None
    if args.work_hours:
        wh_start, wh_end = parse_work_hours(args.work_hours)
    if args.work_days:
        work_days = parse_work_days(args.work_days)
    founder_holidays = set()
    for x in re.split(r"[,\s]+", args.holidays.strip()):
        if x and x.lower() != "none":
            try:
                founder_holidays.add(date.fromisoformat(x))
            except ValueError:
                stop(f"--holidays should be dates like 2026-11-26, separated by commas ('{x}' is not one)")

    # read every file first, to learn the time zone
    loaded = []
    for f in args.files:
        p = Path(f)
        if not p.exists():
            stop(f"there is no file at {f}; attach the calendar export again")
        if p.suffix.lower() in (".zip",):
            stop(f"{p.name} is a zip; Google exports a zip of calendars. Unzip it and attach the .ics for your main calendar")
        if p.suffix.lower() == ".xlsx":
            loaded.append((p, "xlsx", xlsx_rows(p)))
            continue
        text = read_text(p)
        if "BEGIN:VCALENDAR" in text.upper()[:5000] or "BEGIN:VEVENT" in text.upper():
            loaded.append((p, "ics", text))
        elif p.suffix.lower() in (".csv", ".txt", ".tsv") or "," in text[:500]:
            loaded.append((p, "csv", csv_rows(text)))
        else:
            stop(f"{p.name} is not a calendar export I can read. Attach an .ics or .csv export "
                 "(Google Calendar: Settings, Import and export, Export; Outlook: File, Save Calendar, or Export to CSV)")
    tzname, tz_vtz, tz_src = args.tz, {}, "founder"
    if not tzname:  # the calendar's own zone; a holidays calendar or a bare UTC never outranks the founder's own
        named = []
        for p, kind, data in loaded:
            if kind == "ics":
                mm = re.search(r"^X-WR-TIMEZONE:(.+?)\s*$", data, re.M)
                cn = re.search(r"^X-WR-CALNAME:(.+?)\s*$", data, re.M)
                if mm:
                    hol = bool(cn and re.search(r"holiday", cn.group(1), re.I))
                    named.append((hol, mm.group(1).strip().upper() in ("UTC", "GMT", "ETC/UTC"), mm.group(1).strip()))
        if named:
            tzname, tz_src = sorted(named)[0][2], "calendar"
    if not tzname:  # the zone most of the events are written in
        counts = {}
        for p, kind, data in loaded:
            if kind == "ics":
                for z in re.findall(r"^DTSTART;[^:\r\n]*?TZID=\"?([^\";:\r\n]+)\"?[;:]", data, re.M):
                    counts[z.strip()] = counts.get(z.strip(), 0) + 1
                tz_vtz.update(build_vtimezones(parse_ics(data)[2]))
        if counts:
            raw = max(sorted(counts), key=lambda k: counts[k])
            tzname, tz_src = WINDOWS_TZ.get(raw.lower(), raw), "events"
            notes.append(f"used {tzname}, the time zone the export names ({raw})")
    floating = False
    if not tzname:
        utc_only = any(kind == "ics" and re.search(r"^DTSTART(;[^:]*)?:\d{8}T\d{6}Z", data, re.M) for _p, kind, data in loaded)
        if utc_only:
            stop("the export gives its times in UTC and does not say which time zone you work in. Ask the founder "
                 "which city or time zone they work in, then run again with --tz (for example --tz America/New_York, "
                 "--tz Asia/Singapore, --tz Australia/Sydney)")
        floating, tz_src = True, "none needed"
        notes.append("the times carry no time zone; read them as written, in your local time")
    tzr0 = TZResolver(tz_vtz, None, notes)
    try:
        audit_tz = timezone.utc if floating else tzr0.get(tzname)
    except InputError as e:
        stop(f"{e}, then run again with --tz (for example --tz America/Chicago or --tz Asia/Kolkata)")
    tz_label = "local time as written (no time zone in the file)" if floating else tzname

    if args.date_from and args.date_to:
        d_from, d_to = date.fromisoformat(args.date_from), date.fromisoformat(args.date_to)
    elif args.date_from:
        d_from = date.fromisoformat(args.date_from)
        d_to = d_from + timedelta(days=round(args.weeks * 7) - 1)
    else:
        last_sun = today - timedelta(days=today.weekday() + 1)
        d_to = last_sun
        d_from = d_to - timedelta(days=round(args.weeks * 7) - 1)
    if d_to < d_from:
        stop("the audit window ends before it starts; check --from and --to")
    if (d_to - d_from).days > 62:
        stop("the audit window is over two months; audit one or two typical weeks")

    def window(df, dt):
        return (datetime.combine(df, time(0), tzinfo=audit_tz), datetime.combine(dt + timedelta(days=1), time(0), tzinfo=audit_tz))

    win_lo, win_hi = window(d_from, d_to)
    all_insts, series_rules, any_ics = [], {}, False
    log_week = None
    for p, kind, data in loaded:
        try:
            if kind == "ics":
                any_ics = True
                insts, meta = ics_instances(p, data, args, notes, me, win_lo - timedelta(days=400), win_hi + timedelta(days=400), audit_tz)
                series_rules.update(meta.get("series_rules", {}))
            else:
                rows = data
                if is_log(rows):
                    insts, log_week = log_instances(rows, p, args, notes, audit_tz, today)
                else:
                    if kind == "xlsx":
                        stop(f"{p.name} is a spreadsheet but not the one-week log; export the calendar as .ics or .csv instead")
                    insts = csv_instances(rows, p, args, notes, audit_tz, today)
        except InputError as e:
            stop(f"{p.name}: {e}")
        all_insts += insts
    seen, deduped = set(), []
    for x in all_insts:  # the same meeting in two exported calendars counts once
        x["summary"] = re.sub(r"\s+", " ", x["summary"].replace("\u2013", "-").replace("\u2014", "-")).strip() or "(no title)"
        k = (x["summary"].strip().lower(), x["start"].astimezone(timezone.utc), x["end"].astimezone(timezone.utc))
        if k in seen:
            continue
        seen.add(k)
        deduped.append(x)
    all_insts = deduped
    if not all_insts:
        stop("the files hold no events at all. Check you exported the right calendar (Google exports one .ics per calendar)")
    if log_week and not args.date_from:
        d_from, d_to = log_week, log_week + timedelta(days=6)
        win_lo, win_hi = window(d_from, d_to)

    def in_win(x):
        return x["end"] > win_lo and x["start"] < win_hi

    timed = [x for x in all_insts if not x["all_day"]]
    if not any(in_win(x) for x in timed) and not args.date_from:
        latest = max((x["start"] for x in timed), default=None)
        if latest is None:
            stop("the export holds only all-day events, so there are no hours to count. Export the calendar with your meetings in it")
        if latest < win_lo:
            ld = latest.date()
            d_to = ld + timedelta(days=6 - ld.weekday())
            d_from = d_to - timedelta(days=round(args.weeks * 7) - 1)
            win_lo, win_hi = window(d_from, d_to)
            notes.append(f"the export ends on {ld.isoformat()}, so I audited {d_from.isoformat()} to {d_to.isoformat()}, "
                         "the last weeks it covers. Export a newer copy for last week")
    if not any(in_win(x) for x in timed):
        first = min((x["start"] for x in timed), default=None)
        last = max((x["start"] for x in timed), default=None)
        stop(f"no timed events between {d_from.isoformat()} and {d_to.isoformat()}. The export runs from "
             f"{first.date().isoformat() if first else '?'} to {last.date().isoformat() if last else '?'}. "
             "Pick weeks inside that range, or export again")

    days = (d_to - d_from).days + 1
    weeks = days / 7
    one_offs = [x["start"] for x in timed if not x["series"]]
    if one_offs and max(one_offs) < win_lo:
        notes.append(f"the last one-off event in the export is on {max(one_offs).date().isoformat()}, before these weeks; "
                     "only repeating events fall in them. This may be an old export: export a fresh copy")
    window_insts = [x for x in all_insts if in_win(x)]
    allday = [x for x in window_insts if x["all_day"]]
    declined = [x for x in window_insts if not x["all_day"] and x["partstat"] == "DECLINED"]
    cancelled = [x for x in window_insts if x["status"] == "CANCELLED"]
    unknown_decline = [x for x in window_insts if not x["all_day"] and x["partstat"] is None and x["any_declined"] and not me]
    work = [x for x in window_insts if not x["all_day"] and x["partstat"] != "DECLINED" and x["status"] != "CANCELLED"]
    if unknown_decline:
        notes.append(f"{len(unknown_decline)} meetings have someone who declined, and I could not tell if it was you; "
                     "give your email with --me to leave out the ones you declined")
    # clip to the window
    for x in work:
        x["start"], x["end"] = max(x["start"], win_lo), min(x["end"], win_hi)
        x["hours"] = (x["end"] - x["start"]).total_seconds() / 3600
        r = match_map(x["summary"], rules)
        x["activity"] = (r or {}).get("activity") or None
        x["map"] = r
    personal = [x for x in work if x["map"] and str(x["map"].get("category", "")).lower() in ("personal", "not work")]
    work = [x for x in work if x not in personal]
    zero = [x for x in work if x["hours"] <= 0]
    work = [x for x in work if x["hours"] > 0]
    long_ones = [x for x in work if x["hours"] > 12]
    for x in long_ones:
        notes.append(f"'{x['summary']}' on {x['start'].date().isoformat()} runs {fmt(x['hours'])} hours; "
                     "if it is a placeholder or a holiday block, map it as personal")
    if not work:
        stop(f"nothing with a length to count between {d_from.isoformat()} and {d_to.isoformat()} "
             f"({len(allday)} all-day, {len(declined)} declined, {len(personal)} personal, {len(zero)} with no length). "
             "Attach the calendar you work from, or describe last week")
    union, overlap = sweep(work)
    personal_hours = sum(x["hours"] for x in personal)

    # public holidays and days off: from the founder, or from all-day events in the calendar itself
    holidays = {}
    maybe_off = []  # other all-day entries: asked about by date, never named, in case one was a day off
    for d in sorted(founder_holidays):
        if d_from <= d <= d_to:
            holidays[d] = {"date": d.isoformat(), "source": "founder", "what": "day you said was a holiday or day off"}
    for x in allday:
        if x["status"] == "CANCELLED" or x["partstat"] == "DECLINED":
            continue
        title = x["summary"].strip()
        public = bool(PUBLIC_HOLIDAY_WORDS.search(title) or PUBLIC_HOLIDAY_WORDS.search(x.get("desc", ""))
                      or re.search(r"holiday", x.get("calname", ""), re.I))
        own = own_day_off(title, x.get("busy") or "")
        if not (public or own):
            if not SOMEONE_ELSE.match(title):  # a colleague's absence is not asked about; it feeds the clash check
                maybe_off.append(x)
            continue
        d0 = max(x["start"].date(), d_from)
        d1 = min((x["end"] - timedelta(seconds=1)).date(), d_to)
        while d0 <= d1:
            holidays.setdefault(d0, {"date": d0.isoformat(), "source": "calendar",
                                     "what": f"public holiday ({title})" if public else f"day off ({title})"})
            d0 += timedelta(days=1)
    for h in sorted(holidays):
        notes.append(f"{DAY_NAMES[h.weekday()]} {h.isoformat()} is a {holidays[h]['what']}"
                     f"{', from your calendar' if holidays[h]['source'] == 'calendar' else ''}; "
                     "it is not counted as a working day, and the week may be lighter than usual")

    # what was booked each day
    day_segs = {}
    for i in range(days):
        d = d_from + timedelta(days=i)
        day_lo = datetime.combine(d, time(0), tzinfo=audit_tz)
        segs = sorted((max(x["start"], day_lo), min(x["end"], day_lo + timedelta(days=1)))
                      for x in work if x["end"] > day_lo and x["start"] < day_lo + timedelta(days=1))
        merged = []
        for s_, e_ in segs:
            if merged and s_ <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], e_)
            else:
                merged.append([s_, e_])
        day_segs[d] = merged

    # the working week: the founder's words, else Outlook's own setting, else what the events show
    if wh_start is not None or work_days is not None:
        pattern_src = "founder"
    if wh_start is None or work_days is None:
        olk = outlook_work_hours(loaded)
        if olk:
            if wh_start is None and olk[0]:
                wh_start, wh_end = olk[0]
            if work_days is None and olk[1]:
                work_days = olk[1]
            pattern_src = pattern_src or "calendar settings"
    if wh_start is None or work_days is None:
        inf_hours, inf_days = infer_pattern(day_segs, holidays)
        if work_days is None and inf_days:
            work_days = inf_days
            pattern_src = pattern_src or "calendar"
        if wh_start is None and inf_hours and work_days:
            wh_start, wh_end = inf_hours
            pattern_src = pattern_src or "calendar"
    pattern_known = wh_start is not None and work_days is not None
    if not pattern_known:
        pattern_src = "unknown"

    gap_by_day, outside = [], (0.0 if pattern_known else None)
    for i in range(days):
        d = d_from + timedelta(days=i)
        if not pattern_known:
            break
        merged = day_segs[d]
        ws = datetime.combine(d, wh_start, tzinfo=audit_tz)
        we = datetime.combine(d, wh_end, tzinfo=audit_tz)
        inside = sum(max(0, (min(e_, we) - max(s_, ws)).total_seconds()) for s_, e_ in merged) / 3600
        total = sum((e_ - s_).total_seconds() for s_, e_ in merged) / 3600
        outside += total - inside
        if d.weekday() in work_days and d not in holidays:
            span = (we - ws).total_seconds() / 3600
            gap_by_day.append({"date": d.isoformat(), "day": DAY_NAMES[d.weekday()], "booked": round(inside, 2),
                               "gap": round(span - inside, 2)})
    work_hours_text = f"{clock(wh_start)}-{clock(wh_end)}" if pattern_known else None
    work_day_names = [DAY_NAMES[i] for i in work_days] if work_days else []

    clashes = find_clashes(work, personal, holidays, someone_out(allday, d_from, d_to))

    # group into activities
    groups = {}
    for x in work:
        key = x["activity"] or norm_title(x["summary"])
        g = groups.setdefault(key, {"label": x["activity"] or x["summary"].strip(), "insts": [], "map": x["map"]})
        g["insts"].append(x)
    acts = []
    win_lo_naive = win_lo.replace(tzinfo=None)
    for key, g in groups.items():
        ins = g["insts"]
        n = len(ins)
        wh = sum(x["counted_hours"] for x in ins)
        uids = {x["uid"] for x in ins}
        basis, pm = None, None
        if len(uids) == 1 and all(x["series"] for x in ins) and next(iter(uids)) in series_rules:
            info = series_rules[next(iter(uids))]
            pm = rule_per_month(info, win_lo_naive)
            if pm:
                basis = describe_rule(ins[0]["rule"])
        if pm is None:
            pm = n * DAYS_PER_MONTH / days
            basis = f"{n} in the {days} days audited"
        hours_each = wh / n
        titles = sorted({x["summary"].strip() for x in ins})
        mp = g["map"] or {}
        label = g["label"]
        a = {"activity": label, "source": "tracked" if all(x.get("tracked") for x in ins) else "calendar",
             "entries": n, "window_hours": round(wh, 4), "hours_each": round(hours_each, 4),
             "per_month": round(pm, 4), "per_month_basis": basis,
             "category": mp.get("category"), "function": mp.get("function"), "action": mp.get("action"),
             "who": mp.get("who"), "reason": mp.get("reason"), "protected": bool(mp.get("protected")),
             "hints": hints(label, titles) if not mp else [], "titles": titles[:8]}
        if not mp and re.search(CHALLENGE_WORDS, (label + " " + " ".join(titles)).lower()):
            a["hints"].append("challenge if marked only-you")
        if n == 1 and not basis.startswith("repeats"):
            a["hints"].append("once in the window: ask how often it really happens")
        acts.append(a)
    acts.sort(key=lambda a: -a["window_hours"])

    # repeating events with no instance in the window (monthly board meeting, quarterly review)
    seen_uids = {x["uid"] for x in work} | {x["uid"] for x in personal}
    outside_rows = []
    for uid, info in series_rules.items():
        if uid in seen_uids or info["is_date"] or info["partstat"] == "DECLINED":
            continue
        pm = rule_per_month(info, win_lo_naive)
        if not pm or pm >= DAYS_PER_MONTH * 7 / days:
            continue
        r = match_map(info["summary"], rules)
        if r and str(r.get("category", "")).lower() in ("personal", "not work"):
            continue
        h = info["dur"].total_seconds() / 3600
        if h <= 0 or h > 12:
            continue
        outside_rows.append({"activity": (r or {}).get("activity") or info["summary"], "source": "calendar repeat",
                             "entries": 0, "window_hours": 0.0, "hours_each": round(h, 4), "per_month": round(pm, 4),
                             "per_month_basis": describe_rule(info["rule_text"]) + ", none in these weeks",
                             "category": (r or {}).get("category"), "function": (r or {}).get("function"),
                             "action": (r or {}).get("action"), "who": (r or {}).get("who"), "reason": (r or {}).get("reason"),
                             "hints": hints(info["summary"], []) if not r else [], "titles": [info["summary"]],
                             "include": True})
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    cal_week = union / weeks
    src = "tracked" if all(a["source"] == "tracked" for a in acts) else ("calendar" if any_ics or not log_week else "tracked")
    audit = {
        "skill": SKILL, "business": None, "date": today.isoformat(), "currency": None,
        "source": src,
        "locale": {"date_order": DATE_ORDER_SEEN[0]},
        "period": {"from": d_from.isoformat(), "to": d_to.isoformat(), "days": days, "weeks": round(weeks, 4),
                   "tz": tz_label, "tz_source": tz_src, "files": [p.name for p, _k, _d in loaded],
                   "work_hours": work_hours_text, "work_days": len(work_days) if work_days else None,
                   "work_day_names": work_day_names, "work_pattern_source": pattern_src,
                   "holidays": [holidays[h] for h in sorted(holidays)]},
        "calendar_hours": round(union, 4), "calendar_week_hours": round(cal_week, 4),
        "overlap_hours": round(overlap, 4), "outside_work_hours": round(outside, 4) if outside is not None else None,
        "personal_hours": round(personal_hours, 4), "personal_count": len(personal),
        "left_out": {"all_day": len(allday), "declined": len(declined), "cancelled": len(cancelled), "zero_length": len(zero)},
        "gaps": gap_by_day,
        "clashes": clashes,
        "stated_week_hours": None, "untracked_allowance": None, "rate": None, "monthly_revenue": None,
        "team": [], "protected": [], "freed_to": None,
        "activities": acts, "repeats_outside_window": outside_rows, "notes": notes,
    }
    (out_dir / "activities.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    ev_out = [{"activity": x["activity"] or norm_title(x["summary"]), "summary": x["summary"],
               "start": x["start"].isoformat(), "end": x["end"].isoformat(), "hours": round(x["hours"], 4),
               "counted_hours": round(x["counted_hours"], 4), "series": x["series"]} for x in work]
    (out_dir / "events.json").write_text(json.dumps({"calendar_hours": round(union, 4), "events": ev_out}, indent=2),
                                         encoding="utf-8")

    # the readback
    print(f"Window: {d_from.isoformat()} ({DAY_NAMES[d_from.weekday()]}) to {d_to.isoformat()} ({DAY_NAMES[d_to.weekday()]}), "
          f"{days} days, {fmt(weeks, 2)} week{'' if weeks == 1 else 's'}; time zone {tz_label}")
    if pattern_known:
        src_txt = {"founder": "as you said", "calendar settings": "from your Outlook working-hours setting",
                   "calendar": "from what your calendar shows; say if not"}[pattern_src]
        print(f"Working week: {', '.join(n[:3] for n in work_day_names)}, {wh_start:%H:%M} to {wh_end:%H:%M} ({src_txt}).")
    else:
        print("ASK: the calendar is too thin to show a working week. Ask the founder their usual working days and hours, "
              "then run again with --work-days and --work-hours (empty-diary time is not counted until then).")
    ask_days = set()
    for x in maybe_off:
        d0 = max(x["start"].date(), d_from)
        d1 = min((x["end"] - timedelta(seconds=1)).date(), d_to)
        while d0 <= d1:
            if d0 not in holidays and (not work_days or d0.weekday() in work_days):
                ask_days.add(d0)
            d0 += timedelta(days=1)
    if ask_days:
        print("ASK: other all-day entries fall on " + ", ".join(f"{DAY_NAMES[d.weekday()]} {d.isoformat()}" for d in sorted(ask_days))
              + ". In question 5, ask by date (never by the entry's name) whether any of these was a public holiday or a day off "
                "for the founder; if so, run again with --holidays.")
    counted = (f"Counted: {len(work)} events, {fmt(union, 2)} hours ({fmt(cal_week, 2)} a week). "
               f"Overlaps shared: {fmt(overlap, 2)} hours." + (f" Outside {work_hours_text}: {fmt(outside, 2)} hours." if pattern_known else ""))
    print(counted.replace(" 1 hours", " 1 hour"))
    lo = audit["left_out"]
    print(f"Left out: {lo['all_day']} all-day, {lo['declined']} declined, {lo['cancelled']} cancelled, "
          f"{len(personal)} personal ({fmt(personal_hours, 2)} hours), {lo['zero_length']} with no length.")
    gap_total = sum(g["gap"] for g in gap_by_day)
    if pattern_known:
        print(f"Empty diary time inside working hours: {fmt(gap_total, 2)} hours across {len(gap_by_day)} working days.")
    print("")
    print("ACTIVITY | entries | hours each | times a month | hours a month | hours in window | basis | hints")
    for a in acts:
        print(f"{a['activity']} | {a['entries']} | {fmt(a['hours_each'], 2)} | {fmt(a['per_month'], 2)} | "
              f"{fmt(a['hours_each'] * a['per_month'], 1)} | {fmt(a['window_hours'], 2)} | {a['per_month_basis']} | {', '.join(a['hints'])}")
    if outside_rows:
        print("")
        print("REPEATS NOT IN THESE WEEKS (check they are real work):")
        for a in outside_rows:
            print(f"{a['activity']} | {fmt(a['hours_each'], 2)} hours | {fmt(a['per_month'], 2)} a month | "
                  f"{fmt(a['hours_each'] * a['per_month'], 1)} hours a month | {a['per_month_basis']}")
    if clashes:
        print("")
        print("CLASHES (tell the founder in your first reply; a personal entry is never named):")
        for c in clashes[:12]:
            print(f"{c['kind']}: {' / '.join(c['entries'])} | {', '.join(c['when'])}")
        if len(clashes) > 12:
            print(f"and {len(clashes) - 12} more in activities.json")
    for nt in notes:
        print("NOTE:", nt)
    print(f"WROTE: {out_dir / 'activities.json'} ({len(acts)} activities) and {out_dir / 'events.json'}")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except BrokenPipeError:
        sys.exit(0)
    except InputError as e:
        print(f"STOP: {e}. Nothing was written.")
        sys.exit(2)
    except Exception as e:  # noqa: BLE001
        print(f"STOP: the calendar could not be read ({type(e).__name__}: {e}). Nothing was written. "
              "Attach a fresh export, or describe the week instead.")
        sys.exit(2)
