# RevOS Skills

Claude skills for the Merigrove RevOS product, grouped by business category.

```
revos-skills/
├── sales/
├── marketing/
│   └── revos-vsl-writer/
│       ├── SKILL.md
│       └── references/
├── branding/
│   ├── revos-brand-voice/
│   │   ├── SKILL.md
│   │   ├── references/
│   │   ├── scripts/
│   │   └── assets/
│   ├── revos-carousel-copywriter/
│   │   ├── SKILL.md
│   │   └── references/
│   ├── revos-product-flythrough/
│   │   ├── SKILL.md
│   │   ├── references/
│   │   ├── scripts/
│   │   └── assets/
│   └── revos-product-flythrough-slim/
│       └── SKILL.md
├── operations/
└── finance/
```

## Conventions

- One folder per skill, named `revos-<skill>`, inside its category.
- The `name:` in the `SKILL.md` frontmatter matches the folder name.
- Supporting material (examples, templates, scripts) goes in subfolders of the skill, such as `references/`.
- Each category `README.md` lists its skills.

## Skills

| Category | Skill | What it does |
|---|---|---|
| Marketing | [revos-vsl-writer](marketing/revos-vsl-writer/) | Writes a VSL or call-funnel video script from a fact-gathering intake, using a 14-section flow (hook, credibility, opportunity, price-first offer, objections, fit, CTA, proof, plus a skeptic pass for long versions), then QA-checks it. |
| Branding | [revos-brand-voice](branding/revos-brand-voice/) | Builds a measured voice guide and a ready-to-paste AI voice prompt from a founder's own writing and speech, so ChatGPT, Claude, a VA or an agency writes like them. Counts every habit with a script, keeps the founder's own spelling, phrasing, money and dates, and calibrates against their ear. |
| Branding | [revos-carousel-copywriter](branding/revos-carousel-copywriter/) | Turns any idea into slide-by-slide copy for an Instagram carousel or LinkedIn document post, plus a paste-ready Claude Design prompt. |
| Branding | [revos-product-flythrough](branding/revos-product-flythrough/) | Turns the current project or website into a 15 to 25 second product flythrough video with motion, sound effects and share copy, built and rendered with HyperFrames. Adapted from [/brag](https://github.com/latent-spaces/brag) by Shunit Haviv Hakimi (MIT); music tracks not included. |
| Branding | [revos-product-flythrough-slim](branding/revos-product-flythrough-slim/) | The single-file Opus 5.5 version of the product flythrough: builds the whole video with the tools already on the machine. Adapted from /brag-slim (MIT). |
| Operations | [revos-delivery-capacity-check](operations/revos-delivery-capacity-check/) | Works out how many clients a founder can hold per offer and the three delivery tasks to hand over first. For service businesses of one to five people; does the sums with a script and keeps a memory file between runs. |

## Installing a skill

Copy the skill folder into `~/.claude/skills/` for Claude Code, or zip the folder and upload it under Settings → Capabilities → Skills in Claude.
