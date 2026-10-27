# Thumbnail Builder

Finished video thumbnails from your own photo, in three genuinely different styles side by side, tested at the size people really see them. Built by Merigrove.

![Plain Claude on the left, Thumbnail Builder on the right](assets/before-after.png)

## Install

**Claude (web or desktop app)**
1. Download `revos-thumbnail-builder-v1.3.0.zip` (do not unzip it).
2. In Claude, open Customize, then Skills, then Upload a skill, and choose the zip. Code execution needs to be on (Settings, Capabilities).
3. Start a new chat and paste the first prompt below.

**Cowork:** Customize, Skills, Install, choose the zip.
**Claude Code:** unzip into `~/.claude/skills/`.

## Your first prompt

> Use revos-thumbnail-builder to make a thumbnail for my next video. Title: <your title>. The video delivers <what it shows> at about <time>. Photo attached. <Your brand colours (codes or a screenshot), or "keep it plain">.

## What you get

- Thumbnail PNGs at 1280x720 for YouTube, and at 1080x1080 or 1080x1920 if you ask, in three styles: a bold dark panel, a light poster with you in a circle, and a full-photo cinematic look.
- A comparison sheet: every direction at phone, desktop and sidebar size, in a dark and a light feed, with the duration badge in place, and a pass or fix verdict under each.
- Three to five words written for the thumbnail from your title and what the video delivers, never more than the video can back up.
- A notes file with the reasoning, the promise and where the video pays it off.
- Words in your language, spelling and currency, exactly as you write them: "$10k", "₹5 लाख", "10万円". Hindi, Arabic, Chinese and other scripts are drawn with a font that has every letter; if none on the machine does, it tells you and asks for one rather than printing empty boxes.

Already have a thumbnail? Attach it and ask what is wrong with it. It is tested first, then rebuilt.

## It remembers you

After each run it offers to save your look, your photo's crop, what you corrected and, if you tell it, each thumbnail's click-through rate. Keep the memory file and the next run asks almost nothing and holds your channel's look.

## Fonts and your photo

It uses your own font file if you supply one, otherwise an open-licence font already on the machine. If your font lacks a letter your words need (often ₹, or a whole script), it uses an open-licence font that has it and tells you. It bundles and downloads no fonts. Your photo is read and composited on the machine running the skill and never sent anywhere. It never generates or alters a face.

## Safety

Read SKILL.md before installing; it is plain text. This skill makes no network calls and sends nothing anywhere.

## Want the full system?

A thumbnail earns the click; whether those viewers become enquiries depends on the rest of your funnel. The Merigrove Business Audit scores where it leaks: [BUSINESS_AUDIT_URL]
