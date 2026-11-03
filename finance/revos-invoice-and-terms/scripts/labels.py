#!/usr/bin/env python3
"""The words printed on the invoice. English is built in; any other language is written by Claude into
inputs.json "labels" (every key below, same placeholders) and checked here for gaps.

Usage: python3 scripts/labels.py            prints the English set as JSON, to copy and translate
Standard library only. No network calls.
"""
import json
import re
import sys

EN = {
    "invoice": "Invoice",
    "credit_note": "Credit note",
    "number": "Invoice number",
    "credit_number": "Credit note number",
    "date": "Invoice date",
    "credit_date": "Date",
    "due_date": "Due date",
    "po": "Your reference",
    "project_ref": "Project",
    "from": "From",
    "bill_to": "Bill to",
    "tax_number": "Tax number",
    "work_covered": "Work covered",
    "description": "Description",
    "qty": "Qty",
    "unit_price": "Unit price",
    "amount": "Amount",
    "tax": "Tax",
    "subtotal": "Subtotal",
    "includes": "Includes",
    "discount": "Discount",
    "total": "Total",
    "paid": "Paid",
    "amount_due": "Amount due",
    "amount_credited": "Amount credited",
    "project_summary": "Project summary",
    "project_total": "Project total",
    "project_total_incl": "Project total, including {tax}",
    "tax_line": "{label} {rate} on {net}",
    "billed_before": "Billed before",
    "this_invoice": "This invoice",
    "remaining": "Remaining after this invoice",
    "paid_on": "paid {date}",
    "nothing_before": "nothing billed before",
    "how_to_pay": "How to pay",
    "payment_reference": "Payment reference",
    "pay_online": "Pay online",
    "terms": "Terms",
    "notes": "Notes",
    "page": "Page",
    "of": "of",
    "draft_banner": "DRAFT: not for sending",
    "preview_banner": "PREVIEW: not issued, no number yet",
    "credits_invoice": "This credit note reverses invoice {number} of {date}.",
    "credit_reason": "Reason: {reason}",
    "stage_line": "{desc}: {share} of {total}",
    "stage_heading": "Stage {n} of {count}: {label}",
    "still_to_come": "Still to come",
    "later_stage": "Stage {n}: {label}",
    "untaxed_mark": "-",
    "range_joiner": "to",
    "terms_days": "Payment due within {days} days of the invoice date, by {due}.",
    "terms_eom_plus": "Payment due {days} days after the end of the invoice month, by {due}.",
    "terms_end_next_month": "Payment due by the end of the month after the invoice date: {due}.",
    "terms_next_month_day": "Payment due on day {days} of the month after the invoice date: {due}.",
    "terms_on_receipt": "Payment due on receipt: {due}.",
    "terms_fixed": "Payment due by {due}.",
    "terms_in_advance": "Payment due before the work starts, by {due}.",
    "late_fee_agreed": "As agreed in {source}: {clause}",
    "bank_change_line": "We confirm any change to our bank details by phone. Please call us before paying to new details.",
    "paid_line": "{label} {ref} {date}",
    "months": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
               "November", "December"],
    "weekdays": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
}

# Keys added in 1.1.0. A set of labels written for 1.0.0 may lack them: they fall back to English and
# invoice_calc.py prints a WARN naming them, so Claude can add the translation.
OPTIONAL = {"still_to_come", "later_stage", "untaxed_mark"}

PLACEHOLDERS = {k: set(re.findall(r"\{(\w+)\}", v)) for k, v in EN.items() if isinstance(v, str)}


def resolve(language, given):
    """Return (labels, problems). English fills any key not given; another language must give every key."""
    lang = (language or "en").lower()[:2]
    given = dict(given or {})
    problems = []
    out = dict(EN)
    if lang != "en":
        missing = [k for k in EN if k not in OPTIONAL and (k not in given or given[k] in ("", None, []))]
        if missing:
            problems.append(f"labels for '{language}' are missing: {', '.join(missing)}. "
                            f"Print the English set with `python3 scripts/labels.py`, translate every key and add it as \"labels\"")
    for k, v in given.items():
        if k not in EN:
            continue
        if isinstance(EN[k], list):
            n = len(EN[k])
            if not isinstance(v, list) or len(v) != n or any(not str(x).strip() for x in v):
                problems.append(f"label '{k}' needs {n} names")
                continue
        elif isinstance(v, str):
            if not v.strip():
                problems.append(f"label '{k}' is empty")
                continue
            have = set(re.findall(r"\{(\w+)\}", v))
            if have != PLACEHOLDERS.get(k, set()):
                problems.append(f"label '{k}' must keep the placeholders {sorted(PLACEHOLDERS.get(k, set()))}")
                continue
        out[k] = v
    return out, problems


def fallback_keys(language, given):
    """Optional keys a non-English label set did not give (printed in English until added)."""
    if (language or "en").lower()[:2] == "en":
        return []
    given = given or {}
    return sorted(k for k in OPTIONAL if k not in given or given[k] in ("", None, []))


if __name__ == "__main__":
    json.dump(EN, sys.stdout, indent=2, ensure_ascii=False)
    print()
