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
│   └── revos-carousel-copywriter/
│       ├── SKILL.md
│       └── references/
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
| Branding | [revos-carousel-copywriter](branding/revos-carousel-copywriter/) | Turns any idea into slide-by-slide copy for an Instagram carousel or LinkedIn document post, plus a paste-ready Claude Design prompt. |

## Installing a skill

Copy the skill folder into `~/.claude/skills/` for Claude Code, or zip the folder and upload it under Settings → Capabilities → Skills in Claude.
