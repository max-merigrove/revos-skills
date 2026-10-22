# Brand Voice

Make every AI draft sound like you wrote it. Paste five things you wrote and get one file to paste into ChatGPT or Claude, a voice guide for anyone who writes for you, and a memory file so the next run picks up where this one stopped. Built by Merigrove.

## What you get

- **PASTE THIS INTO YOUR AI** (`.txt`): the top says exactly where it goes (a ChatGPT Project first, then a custom GPT, a Claude Project or a Gemini Gem). Below that is a full prompt and a short version, each between clear START and END lines. The short version only applies when you ask for writing for your business, so your other chats stay as they are.
- **Your voice guide** (`.docx`): page one is the whole thing on one page, never-list first, for your VA or the top of a brief. The pages after it hold the detail: your habits measured, do and don't pairs in your own sentences, how you shift between posts, emails and speech, and limits that stop your habits turning into tics.
- **A memory file**: what was learned about your voice, plus the pieces of your own writing it measured (clients' names cut to initials), so a refresh works without pasting them again.

It keeps your English. Your spelling (colour or color, organise or organize, or both), your phrasing, your currency, how you write numbers (14,500 or 14.500, 18 lakh or $18k) and how you write dates are measured from your own writing and copied, never corrected and never swapped for another country's. If English is not your first language, the way you write is treated as your voice, not as mistakes; say "polish" if you would rather have the grammar tidied.

## Install

**Claude (web or desktop app)**
1. Download the `revos-brand-voice` zip file you were sent (do not unzip it).
2. In Claude, open Customize, then Skills, then Upload a skill, and choose the zip. Code execution needs to be on (Settings, Capabilities).
3. Start a new chat and paste the first prompt below.

**Cowork:** Customize, Skills, Install, choose the zip.
**Claude Code:** unzip into `~/.claude/skills/`.

## Your first prompt

> Use revos-brand-voice to work out how I write and give me something to paste into ChatGPT. Here are some posts and client emails I wrote myself: (paste or attach)

Leave out anything an AI tool, a VA or an agency drafted: it measures their habits instead of yours. If you're not sure, paste it anyway and say so; the skill flags anything that reads unlike the rest and asks you. Fewer than five pieces? It tells you the fastest way to get five, including three short voice notes on your phone.

## How it works

1. It sorts what you paste and asks about anything that looks like someone else's: another name on the sign-off, a helper named in your note, stock AI phrases, or a piece whose habits sit far from the rest of your writing.
2. A script measures your own pieces, including your spelling, currency and date style. Nothing is counted by eye.
3. It writes two short samples in your voice and you mark any line that isn't you. Every miss changes a rule, not just the line.
4. You get the three files. You answer at most five questions before the samples, usually two.

## It remembers you

When a draft comes back wrong, paste the draft and your fixed version: the skill reads what you changed, proposes the rules behind it, and updates the guide and the PASTE file together. Keep the memory file and attach it next time.

## Safety

Read SKILL.md before installing; it is plain text. This skill makes no network calls and sends nothing anywhere. The memory file holds your measured figures, the pieces of your own writing that were measured (with clients' names cut to initials) and your voice guide, whose Before examples quote the pieces that were left out because someone else wrote them.

## Want the full system?

Your voice is written down. Whether what you say in it lands with the buyers you want is a positioning question; the Merigrove Business Audit scores that for you: [BUSINESS_AUDIT_URL]
