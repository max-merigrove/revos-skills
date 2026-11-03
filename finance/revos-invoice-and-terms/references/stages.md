# Deposits and stage invoices

## The pattern

One project total. A billing plan: a list of stages, each a share ("30%") or a fixed amount, with a trigger in the founder's words ("on acceptance", "at design sign-off", "when it goes live") and an optional planned date. One invoice per payment, each carrying a project summary:

| Project summary | |
|---|---|
| Project total | EUR 5,129.40 |
| Billed before: INV-0019, 2 November 2026 | EUR 2,564.70 |
| This invoice: INV-0024 | EUR 2,564.70 |
| Remaining after this invoice | EUR 0.00 |

Why separate invoices: practitioners use both (one invoice less a deposit, or one per payment) and disagree on when tax arises on a deposit. Separate invoices give the client's accounts team one document per payment, and the summary shows where the project stands. If the founder or their accountant prefers another pattern, follow them.

## The stage rule (working default)

1. A share applies to every line in proportion, unless the founder says a line is billed in a particular stage (a cost passed on at actuals, a licence billed when bought). Set `"stage": N` on that line; the shares then apply to the other lines.
2. Each line's stage amount is worked out to the smallest unit; the last stage takes the remainder, so the stages add to the project total exactly.
3. Tax is worked per category on each stage's net. The last stage's tax is the balance of the project's tax, so the tax adds up exactly too; the script flags when that differs from rate times net by a unit.
4. A fixed-amount stage is read as what the client pays on that stage, tax included where tax is charged, and the script says so.
5. The script says in one line which rule it used. The founder can change it.

## Layout

A stage invoice whose lines are all shares of the project drops the Qty and Unit price columns (they would only repeat 1 and the amount). The project summary's "Remaining after this invoice" row carries no stage names; the later stages sit in the small "Still to come" list. How to pay, the payment reference, the due date and the terms sit in one block. The standard three-stage example is one page on A4 and Letter, from LibreOffice and from the plain PDF writer.

## Tax on a deposit

Ask once, because the answer differs by place: "Should tax appear on the deposit invoice? Default: the same share of the tax as the share of the work; confirm it with your accountant." If they say no tax on the deposit, set `"tax": "none"` on that stage; the last stage then carries the rest. Store the answer as supplied by them.

## Later stages

Built only when their trigger is reached, with the next number and today's date. Until then the current invoice lists them under "Still to come" (stage, label, trigger where it adds something, amount; they add to the remainder), and the chat says what each will be. A preview PDF (no number, no date, the word PREVIEW at the top) is made only when the founder asks to see one. The register shows them as waiting. A stage built later reads the earlier stages' numbers, dates and totals from memory or the register; if the project lines no longer give the total that was invoiced, the script stops rather than guess.

## What is the founder's call, not the skill's

Whether a deposit is refundable, what happens on cancellation, and what it is called (deposit, booking fee, advance) are commercial terms. The chat names them as the founder's to add and "commercial wording to check with your lawyer"; the terms wording never carries a gap for them.

## Worked splits

- 50/50 on USD 3,200 + 2 x 450 + 186.40, sales tax 8.25% on the third line only as supplied: deposit 1,600.00 + 450.00 + 93.20 = 2,143.20 net, tax 7.69, USD 2,150.89; balance the same; project USD 4,301.78.
- 40/40/20 on USD 9,000.00, no tax: 3,600.00, 3,600.00, 1,800.00.
- 30/40/30 on USD 10,000.00 + 10% as supplied: 3,000.00 + 300.00, 4,000.00 + 400.00, 3,000.00 + 300.00; project USD 11,000.00.
- Thirds on 1,000.00: 333.33, 333.33, 333.34 (the last takes the remainder).
