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
| Marketing | [revos-funnel-constraint-finder](marketing/revos-funnel-constraint-finder/) | Finds the one stage of a founder's sales funnel costing the most customers, from their own rough counts, and prices the fix in clients and money a month. |
| Branding | [revos-brand-voice](branding/revos-brand-voice/) | Builds a measured voice guide and a ready-to-paste AI voice prompt from a founder's own writing and speech, so ChatGPT, Claude, a VA or an agency writes like them. Counts every habit with a script, keeps the founder's own spelling, phrasing, money and dates, and calibrates against their ear. |
| Branding | [revos-carousel-copywriter](branding/revos-carousel-copywriter/) | Turns any idea into slide-by-slide copy for an Instagram carousel or LinkedIn document post, plus a paste-ready Claude Design prompt. |
| Branding | [revos-product-flythrough](branding/revos-product-flythrough/) | Turns the current project or website into a 15 to 25 second product flythrough video with motion, sound effects and share copy, built and rendered with HyperFrames. Adapted from [/brag](https://github.com/latent-spaces/brag) by Shunit Haviv Hakimi (MIT); music tracks not included. |
| Branding | [revos-product-flythrough-slim](branding/revos-product-flythrough-slim/) | The single-file Opus 5.5 version of the product flythrough: builds the whole video with the tools already on the machine. Adapted from /brag-slim (MIT). |
| Branding | [revos-brand-consistency-scan](branding/revos-brand-consistency-scan/) | Finds where a founder's website, LinkedIn and proposals contradict each other, quoted side by side, and gives one core line to align them on. |
| Branding | [revos-thumbnail-builder](branding/revos-thumbnail-builder/) | Designs finished video thumbnail PNGs from the founder's photo in three styles, tested at phone size. |
| Sales | [revos-call-review](sales/revos-call-review/) | Scores one sales call out of 100, finds where the deal was lost and why, and gives two coaching points with the words to say. |
| Sales | [revos-sales-target-planner](sales/revos-sales-target-planner/) | Works back from the profit a founder needs to the sales, calls and leads each month takes, checks it against their calendar and names what breaks first. |
| Operations | [revos-delivery-capacity-check](operations/revos-delivery-capacity-check/) | Works out how many clients a founder can hold per offer and the three delivery tasks to hand over first. For service businesses of one to five people; does the sums with a script and keeps a memory file between runs. |
| Operations | [revos-founder-time-audit](operations/revos-founder-time-audit/) | Audits where a founder's week goes, ranks what to stop and hand over by the hours it gives back, costs each handover and writes the handover brief. |
| Operations | [revos-hiring-readiness](operations/revos-hiring-readiness/) | Tests whether a small business can afford and needs its next hire: Ready, Not yet or No, the most the hire can cost, then the scorecard, job ad and first 90 days. |
| Operations | [revos-scope-guard](operations/revos-scope-guard/) | Builds a scope kit for a service founder: a scope statement, what extras have cost, and the words to price extra work. |
| Finance | [revos-cash-forecast](finance/revos-cash-forecast/) | Builds a 13-week cash forecast from a business bank export and names the first week cash drops below a safety line, in a normal and a bad quarter. |
| Finance | [revos-get-paid](finance/revos-get-paid/) | Builds a plan to get overdue invoices paid: who to chase first, today's message in the founder's voice, dated follow-ups and a payment plan offer. |
| Finance | [revos-price-floor-calculator](finance/revos-price-floor-calculator/) | Works out the lowest price each service offer can charge with the founder's own hours paid, and gives a raise, hold or restructure verdict. |

## Installing a skill

Copy the skill folder into `~/.claude/skills/` for Claude Code, or zip the folder and upload it under Settings → Capabilities → Skills in Claude.
