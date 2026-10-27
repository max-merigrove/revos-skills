# Sales Target Planner

Know exactly how many sales calls your profit target needs. Six numbers in; out comes your monthly plan, your weekly pace, and the one thing that breaks before you hit it. Built by Merigrove for founders of service businesses who sell on calls.

## Install

**Claude (web or desktop app)**
1. Download `revos-sales-target-planner-v1.2.0.zip` (do not unzip it).
2. In Claude, open Customize, then Skills, then Upload a skill, and choose the zip. Code execution needs to be on (Settings, Capabilities).
3. Start a new chat and paste the first prompt below.

**Cowork:** Customize, Skills, Install, choose the zip.
**Claude Code:** unzip into `~/.claude/skills/`.

## Your first prompt

> Use revos-sales-target-planner to work out how many sales calls I need. I want to make (your profit) a month. My main offer is (price), and (paste anything else: last quarter's calls, a CRM export, or just describe it)

You can be rough, in your own currency and your own way of writing numbers. "12k profit, packages at $3,600, a freelancer costs me about $1,200 a client, maybe 6 of 10 calls show and I close 1 in 4" is enough to start, and so are "S$12k profit, I take calls Sunday to Thursday", "15.000 € de bénéfice, contrats à 4.850,00 € HT" and "$3,500/mo retainers, 5 clients now, they stay about 7 months".

## What you get

One workbook, `sales-target-plan_<date>.xlsx`:

- **Plan:** the headline, your monthly sales, held calls, bookings and leads, each rate labelled measured or assumed, whether your calendar can carry it, what breaks first with its number, your weekly pace and a dated first week. Prints to one page width.
- **Try a lever:** yellow cells for your price, rates and hours. Change one and the whole plan moves.
- **Scenarios:** what a better show rate (to the 70% planning default), a price rise of a tenth or a better close rate each buys, and all three together.
- **Assumptions:** every default it used and where each figure came from.

## How it thinks

It starts at the profit you need, not a revenue number, because revenue can be hit with nothing left over. If clients pay you monthly, it counts the clients already paying and the ones who leave, and works out the new clients a month to reach your target by your date. If you give a yearly figure, it asks whether you mean the rate you want to be running at or money to make by a date, and says how many months are left. It checks your diary before it calls a plan possible. When your calendar cannot carry the target, it says so plainly and works out the price that would fit, because extra calls cannot fix a calendar that is already full.

## Wherever you are

It works in your currency and never converts it, reads and writes numbers the way you do (1,250.50 or 1.250,50), stops and asks when a figure could be read two ways, takes date order and paper size from your country, follows your working week and the days off you give it, and mirrors your English. It holds no country's tax rates, thresholds or holiday calendar. Enter prices before any sales tax (VAT, GST or similar); ask your accountant whether you need to charge it.

## It remembers you

After each run it offers to save your figures and the plan. Next month, tell it what actually happened (enquiries, calls booked, calls held, sales) and it swaps its estimates for your real rates, shows you the month against the plan, and re-plans in a couple of minutes.

## Safety

Read SKILL.md before installing; it is plain text. This skill makes no network calls and sends nothing anywhere. It is a planning tool, not financial, tax or legal advice: it never works out tax, and any figure that depends on tax comes from your accountant.

## Want the full system?

Your plan names what breaks first. Whether that is a price, show rate or sales system problem is what the Merigrove Business Audit scores: [BUSINESS_AUDIT_URL]
