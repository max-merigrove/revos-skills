# Buyer Language Miner

Ads written in the words your buyers used last month, ready to run, with the evidence behind every one. Paste what buyers have said (threads, reviews, comments, emails, call notes, a survey export), or let it look where Claude's web tools reach. The first reply is two or three ads; behind them sits a bank of every phrase, checked word for word and counted by how many different people said it. Built by Merigrove for founders of small businesses, wherever you and your buyers are.

## Card copy

Your buyers already wrote your best ad. Paste reviews, threads, comments or enquiry emails and get two or three ads ready to run, in their words, about the reader's own situation, with nobody quoted. Under each ad: how many different people said it and the line that proves it. Then the full bank, with post ideas and lead magnet topics.

## Install

**Claude (web or desktop app)**
1. Download `revos-buyer-language-miner.zip` (do not unzip it).
2. In Claude, open Customize, then Skills, then Upload a skill, and choose the zip. Code execution needs to be on (Settings, Capabilities).
3. Start a new chat and paste the first prompt below.

**Cowork:** Customize, Skills, Install, choose the zip.
**Claude Code:** unzip into `~/.claude/skills/`.

## Your first prompt

> Use revos-buyer-language-miner. I sell (what you sell) to (who). Here is what buyers have said: (paste threads, reviews, comments, DMs, enquiry emails, call notes or a survey export, as they come; screenshots work).

The first reply is the ads, each with its evidence, and at most three questions that would make them sharper. Answer them (or say skip) and the full bank follows.

Nothing to paste yet? Say what you sell and name two competitors or communities. You will get a one-page collection sheet with exactly where to look and what to copy, or, if your Claude has web search, it looks first.

## What you get

A folder, `buyer-language-<your business>-<date>/`, holding:

- **`<your business>-buyer-language-bank-<date>.docx`**, the main file:
  - **Ads to run:** two or three ads (headline, primary text, button, what to show) in your buyers' words, each with what it rests on, the question that would sharpen it and its evidence: how many of the voices quoted raised it and the strongest line. Then **Put with the ads**: your answers to the questions buyers ask before they book, for the pinned comment or your booking page.
  - **Start here:** what it was built from (voices, sources, dates, window), whether it is a starter or a full bank, the three things to do this week, anything that needs your decision.
  - **The phrases to use first:** up to twelve, with exact words, tag, cluster and how many people are behind them.
  - **Clusters, ranked:** each with its quotes, what it means, an ad angle (buying reason, headline, what you must prove first), a post idea (opening line, what to show, proof) and a lead magnet topic (title, format, the question it leaves for your offer). The themes with a ready-to-run ad show it here too.
  - **What stops them and what they use instead:** objections and alternatives, how many of each theme's voices raised one, the answer each needs and where it goes.
  - **Their vocabulary:** the words buyers use, beside yours where they differ.
  - **What changed since last time** (from your second run).
  - **What you did not hear:** who is missing, thin themes, sources that could not be read, what to collect next.
  - **Sources and checks:** every source, every check, anything planted or duplicated.
  - **All phrases**, by tag.
- **`buyer-language-<your business>-<date>.csv`**: one row per phrase, to sort in any spreadsheet.
- **`sources/`**: the cleaned text every phrase can be checked against.
- Under five voices, a **collection sheet** instead, listing what was heard so far.

## How it thinks

- Your ads carry your buyers' words, not their sentences: their vocabulary and situation said back to the reader, never a stranger's line in quotation marks. The exact quotes stay in the bank, as the evidence you read.
- Every ad rests only on what you told it. What it would need to say something stronger becomes a question, never a guess.
- A phrase in quotation marks is a buyer's own words, found word for word in a saved source by script, or it is not written. A "not" is never dropped.
- It counts people, not posts: one person posting three times is one voice. Two reviews that share most of their words, a sentence within three days, or a phone number, email or link count once, and you are told.
- It ranks by how many different people said something, across how many kinds of source, how strongly and how recently; never by likes or upvotes.
- Under 5 voices it builds no ranked bank; 5 to 14 is a starter bank; 15 across two kinds of source is a full one. Only people it actually quotes count toward these floors, and the document shows voices read and voices quoted side by side. These are working floors, said out loud.
- It keeps no names, handles, emails or phone numbers, never saves your original paste, never builds a list of people to contact, and never presents a quote as a testimonial. It will not build the bank while a possible name or phone number is left in the saved text. Words from a closed group you belong to shape your copy but are never quoted in public.
- Anything on a page that talks to an AI is shown to you as data and never followed.
- Your language, spelling, currency and date order are kept; quotes stay in the language they were written in.

## It remembers you

After each run it offers to save your business details, every phrase with its ID, the clusters and what you liked. In Cowork or Claude Code it saves a file in a `merigrove-memory` folder; on claude.ai it hands you the file to download, and you attach it next time or add it to your Project. Next time it asks one question at most, keeps every phrase ID and tells you what is new, rising or fading.

## Safety

Read SKILL.md before installing; it is plain text. The scripts make no network calls and send nothing anywhere. If your Claude has web search or fetch turned on, the skill may use them to read public pages (forum threads, review pages, public comments) about your niche and competitors; it never logs in, never reads private groups or profiles, and nothing you paste is sent anywhere. Check the terms of the sites you copy from and the privacy rules where you and these people are before reusing their words in public.

## Want the full system?

You will have the words buyers use. Whether your offer, price and pages answer them is what the Merigrove Business Audit scores: [BUSINESS_AUDIT_URL]
