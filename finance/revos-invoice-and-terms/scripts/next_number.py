#!/usr/bin/env python3
"""The next invoice number, carried on from the founder's last one.

Usage:
  python3 scripts/next_number.py <last number> [--issue-year 2026] [--used "INV-0019,INV-0020"] [--rollover restart|continue]
Keeps the prefix, separators, a year if there is one, and the zero padding: INV-0018 -> INV-0019,
KIC/2026/031 -> KIC/2026/032, 2026-0044 -> 2026-0045, 118 -> 119.
An issued or voided number is never reused. Where the number carries a year and the invoice date is in a later
year, it asks whether to restart the count (prints ASK and exits 1) unless --rollover says.
Exit 0 done, 1 a question to put to the founder, 2 STOP. Standard library only. No network calls.
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402


def split_number(last):
    s = str(last or "").strip()
    if not s:
        raise C.Stop("the last invoice number is empty")
    groups = list(re.finditer(r"\d+", s))
    if not groups:
        raise C.Stop(f"'{s}' has no digits to count on from. Ask the founder for their last invoice number")
    counter = groups[-1]
    year = None
    for g in groups[:-1]:
        v = g.group(0)
        if len(v) == 4 and 2000 <= int(v) <= 2099:
            year = g
    if year is None and len(groups) == 1 and len(counter.group(0)) >= 8:
        # a date-stamped number such as 20261102001 is still counted on as one number
        pass
    return s, counter, year


def next_after(last, issue_year=None, rollover=None, used=()):
    """Return (number, notes). notes may hold an ASK line."""
    s, counter, year = split_number(last)
    notes = []
    width = len(counter.group(0))
    head, tail = s[:counter.start()], s[counter.end():]
    if year is not None and issue_year and int(year.group(0)) < int(issue_year):
        if rollover not in ("restart", "continue"):
            notes.append(f"ASK: your numbers carry the year {year.group(0)} and this invoice is dated {issue_year}. "
                         f"Start the count again for {issue_year} ({head.replace(year.group(0), str(issue_year))}"
                         f"{'1'.zfill(width)}{tail}) or carry on? Default: start again")
            rollover = "restart"
        if rollover == "restart":
            head = s[:year.start()] + str(issue_year) + s[year.end():counter.start()]
            cand = head + "1".zfill(width) + tail
            return _skip_used(cand, used, notes)
        head = s[:year.start()] + str(issue_year) + s[year.end():counter.start()]
    n = int(counter.group(0)) + 1
    cand = head + str(n).zfill(width) + tail
    return _skip_used(cand, used, notes)


def _skip_used(cand, used, notes):
    used = {str(u).strip() for u in used or () if u}
    tries = 0
    while cand in used:
        notes.append(f"FLAG: {cand} is already used or voided in your register, so it is skipped and never reused")
        cand, _ = next_after(cand)
        tries += 1
        if tries > 1000:
            raise C.Stop("could not find an unused number after 1,000 tries. Check the register")
    return cand, notes


def first_number(prefix=None):
    return (prefix or "") + "0001"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("last")
    ap.add_argument("--issue-year", type=int)
    ap.add_argument("--used", default="")
    ap.add_argument("--rollover", choices=["restart", "continue"])
    a = ap.parse_args()
    num, notes = next_after(a.last, a.issue_year, a.rollover, [x for x in a.used.split(",") if x.strip()])
    for n in notes:
        print(n)
    print(f"NEXT: {num}")
    return 1 if any(n.startswith("ASK") for n in notes) else 0


if __name__ == "__main__":
    C.run_main(main)
