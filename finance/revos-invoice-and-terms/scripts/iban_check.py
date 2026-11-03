#!/usr/bin/env python3
"""Check an IBAN by its own check digits (the ISO 13616 mod 97 test) and print it in groups of four.

Usage: python3 scripts/iban_check.py "IE29 AIBK 9311 5212 3456 78"
Pure arithmetic on the characters: no country tables, no length rules, no bank lookup, no network.
A pass means the digits are consistent with each other, not that the account exists or belongs to anyone.
Exit 0 passes, 1 fails (ask the founder to re-read it from their bank), 2 STOP.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402


def clean(iban):
    return re.sub(r"[\s.-]+", "", str(iban or "")).upper()


def check(iban):
    """Return (ok, reason, grouped)."""
    s = clean(iban)
    if not s:
        return False, "it is empty", ""
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{8,30}", s):
        return False, "it is not two letters, two check digits and then letters and digits", group4(s)
    rearranged = s[4:] + s[:4]
    digits = "".join(str(int(ch, 36)) for ch in rearranged)
    ok = int(digits) % 97 == 1
    return ok, ("check digits agree" if ok else "the check digits do not match the rest; one character is probably mistyped"), group4(s)


def group4(s):
    s = clean(s)
    return " ".join(s[i:i + 4] for i in range(0, len(s), 4))


def looks_like_iban(text):
    return bool(re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{8,30}", clean(text)))


def main():
    if len(sys.argv) != 2:
        raise C.Stop("give one IBAN in quotes")
    ok, why, grouped = check(sys.argv[1])
    print(f"{'PASS' if ok else 'FAIL'}: {grouped}: {why}")
    return 0 if ok else 1


if __name__ == "__main__":
    C.run_main(main)
