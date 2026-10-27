# Get Paid

Get paid on late invoices without losing the client. Paste your overdue invoices; get who to chase first, the message to send today in your own voice, the follow-ups dated and ready, a payment plan the client can say yes to, and draft terms so it happens less next time. Built by Merigrove for founders of small businesses, wherever you and your clients are.

## Install

**Claude (web or desktop app)**
1. Download `revos-get-paid.zip` (do not unzip it).
2. In Claude, open Customize, then Skills, then Upload a skill, and choose the zip. Code execution needs to be on (Settings, Capabilities).
3. Start a new chat and paste the first prompt below.

**Cowork:** Customize, Skills, Install, choose the zip.
**Claude Code:** unzip into `~/.claude/skills/`.

## Your first prompt

> Use revos-get-paid. These clients are late paying me: (paste your overdue invoices: client, invoice number, amount, and the invoice or due date. A screenshot of your unpaid invoices list works.)

You can be rough: "Copperline owe me $8.5k from an invoice on 8/15, Bluefin $4,200 and $3,150, net 30, they always pay late" is enough to start.

## What you get

One Word document, `get-paid-plan-<your business>-<date>.docx`:

- **Who to chase, in order:** each client, what they owe, how late, and the next message with its date.
- **Send now:** the message for each client, at the right stage, ready to paste into email.
- **What you're owed:** per invoice, the due date and days late, and any late fee your own contract sets, with the working.
- **If they still haven't paid:** the next messages, dated.
- **If they ask to pay in parts:** a payment plan per client, every instalment and date, adding up exactly.
- **The escalation ladder:** reminder, firm reminder, call and payment plan, final notice, then stop work or a collections service or lawyer as options to take advice on.
- **Terms for future work:** deposit, milestone billing, card on file and a late fee placeholder, as drafts to check with your lawyer.

## How it thinks

- It matches the chase to the client: one you want to keep gets a nudge, a call and a plan, with any late fee waived if they pay by a date; one who always pays late skips the nudge.
- It adds a late fee or interest only if your own contract sets one, using your rate in plain arithmetic. It never says what any law allows.
- The final notice names one thing you will do next, the one you choose. No empty threats, no legal threats.
- Your currency, the way you write numbers (1,200.50 or 1.200,50), days off and holidays come from you; date order and page size follow your country. Nothing assumes a country, and no country's holiday calendar is built in: tell it any holidays in the next 8 weeks.
- If a client disputes only part of an invoice, it chases the rest and offers to settle that part separately.

## It remembers you

After each run it offers to save your clients, open invoices, the messages that went out and how you write. In Cowork or Claude Code it saves a file in a `merigrove-memory` folder; on claude.ai it hands you the file to download, and you attach it next time or add it to your Project. Next time it asks one question (who paid, what went out, anything new) and picks up at the next message.

## Safety

Read SKILL.md before installing; it is plain text. This skill makes no network calls and sends nothing anywhere. It is a planning tool, not legal or tax advice: check any late fee and the draft terms with your lawyer.

## Want the full system?

You know who owes what and what to send. Designing terms and billing so you stop chasing is part of the Merigrove Business Audit: [BUSINESS_AUDIT_URL]
