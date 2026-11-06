# Dead Lead Revival

Paste your old leads, lapsed clients and no-shows, and get them sorted by why they went quiet, a short honest sequence for each group in the language your clients speak, the ten you can message today written out by hand, and a tracker with every send dated. It sends nothing. Built by Merigrove.

## Card copy

The fastest pipeline you can build is the one you already have. Paste your old leads, lapsed clients and no-shows. Dead Lead Revival sorts them by why they went quiet and how long ago, writes three to five short messages per group, names the ten to contact today, and hands you a dated tracker. It sends nothing.

## Install

**Claude (web or desktop app)**
1. Download `revos-dead-lead-revival.zip` (do not unzip it).
2. In Claude, open Customize, then Skills, then Upload a skill, and choose the zip. Code execution needs to be on (Settings, Capabilities).
3. Start a new chat and paste the first prompt below.

**Cowork:** Customize, Skills, Install, choose the zip.
**Claude Code:** unzip into `~/.claude/skills/`.

## Your first prompt

> Use revos-dead-lead-revival. These are my old leads, can you sort out who to chase and what to say? (paste your notes, or attach a CRM export or spreadsheet)

Messy is fine: "Dan, ghosted after the proposal in January" or "Sarah K, budget frozen till Q3" is enough. A HubSpot, Pipedrive or Xero export works as it comes, in your own date and number format. Column headers and common notes are recognized in English, German, French and Spanish, with headers also in Italian, Dutch and Portuguese; notes in other languages are read by Claude, and every reading it is unsure of is shown to you to correct.

## What you get

**The tracker**, `dead-lead-revival_YYYY-MM-DD.xlsx`:

- **Today:** how many people, in which groups, who is held back, your first ten to message today (people you have an address for, whose first message is due today) with the reason for each, who still needs a number or email from you, and status totals that update as you work.
- **Segments:** the nine groups (parked with a date, past clients, went quiet after a proposal, said not now, talked with no proposal, stopped at the price, no-shows, enquired or met, chose someone else), each with its angle, touches and stop.
- **Contacts:** one row per person with their group, the reason from your own notes, the next touch and its date, and a Status drop-down you update.
- **Send queue:** every message, dated on your working days at the number you can send in a day, ready to paste.
- **Held back:** everyone not messaged and why (asked to stop, a current client, a dispute, a duplicate, an unknown list), with what would release them.
- **Rules:** how people were ranked, the touch plans, the stop rules and every assumption, so you can disagree.

**The messages**, `revival-messages_YYYY-MM-DD.docx`: the rules in one page, today's ten written for each person from your notes, every group's sequence ending with its close-the-file message (with [first name] style labels where each person's details go), what to do when someone replies, and how to bring the tracker back.

## How it thinks

- **Why first, how long ago second.** "Budget frozen till Q3" and "went with another agency" get different messages. Price with no price ever sent is treated as an unfinished conversation, not an objection.
- **The first message never pitches.** One honest question, built on their own words or date, with a plain way to say no. No prices, discounts or deadlines you did not give.
- **Stops are built into the dates.** Any reply stops that person's sequence, the last message closes the file, and nobody is written to again for six months.
- **Paced like a person.** 15 a day by default, on your working days, skipping the days off you give it. Texts only to people who have texted you, unless you say otherwise, and nobody on a channel you have no address for.
- **In your clients' language.** German, French, Spanish or any other: you give it your own opt-out line once and it keeps it in every first and last message.
- **Honest about permission.** It asks how each group came onto your list, holds back bought or unknown lists, and reminds you to check the rules for email, texts and calls where you and your contacts are. It never says what any law allows.

## It remembers you

After each run it offers to save your setup, your voice and language, the people never to contact (everyone who asked to stop is kept by name) and what has worked. In Cowork or Claude Code it saves a file in a `merigrove-memory` folder; on claude.ai it hands you the file to download. Next time, bring the tracker back with the Status column updated: replies and stops come off, finished sequences rest, and the next batch is dated for you. It asks one question at most.

## Safety

Read SKILL.md before installing; it is plain text. Your list stays in this conversation and in the files saved to your own folder. The scripts make no network calls. The skill looks nothing up about anyone on your list; the only web page it may read, and only with Claude's own web tools when you give it the address, is your own website, to suggest what has changed for you to confirm. It sends nothing and drafts nothing into your mailbox. It is planning, not legal advice.

## Want the full system?

These people went cold for reasons, and the reasons repeat. Fixing where deals die is a sales system job; the Merigrove Business Audit scores yours: [BUSINESS_AUDIT_URL]
