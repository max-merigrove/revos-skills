# RevOS Skills

Claude skills for the Merigrove RevOS product, grouped by business category.

```
revos-skills/
├── sales/
│   ├── revos-call-review/
│   ├── revos-dead-lead-revival/
│   └── revos-sales-target-planner/
├── marketing/
│   ├── revos-buyer-language-miner/
│   ├── revos-funnel-constraint-finder/
│   ├── revos-get-quoted-by-ai/
│   ├── revos-lead-magnet-factory/
│   └── revos-vsl-writer/
├── branding/
│   ├── revos-brand-consistency-scan/
│   ├── revos-brand-voice/
│   ├── revos-carousel-copywriter/
│   ├── revos-product-flythrough/
│   ├── revos-product-flythrough-slim/
│   └── revos-thumbnail-builder/
├── operations/
│   ├── revos-delivery-capacity-check/
│   ├── revos-founder-time-audit/
│   ├── revos-hiring-readiness/
│   └── revos-scope-guard/
├── finance/
│   ├── revos-cash-forecast/
│   ├── revos-client-credit-check/
│   ├── revos-get-paid/
│   ├── revos-invoice-and-terms/
│   ├── revos-price-floor-calculator/
│   └── revos-price-rise-pack/
└── building/
    └── revos-replica/
        ├── revos-replica-architect/
        ├── revos-replica-backend/
        ├── revos-replica-brand/
        ├── revos-replica-build/
        ├── revos-replica-deploy/
        ├── revos-replica-design/
        ├── revos-replica-diff/
        ├── revos-replica-entrepreneur/
        ├── revos-replica-launch/
        ├── revos-replica-recon/
        ├── revos-replica-test/
        └── tests/
```

Inside each skill folder there is a `SKILL.md`, and where the skill needs them, `references/`, `scripts/` and `assets/` subfolders, a `LICENSE` and a `README.md`.

## Conventions

- One folder per skill, named `revos-<skill>`, inside its category.
- The `name:` in the `SKILL.md` frontmatter matches the folder name.
- Supporting material (examples, templates, scripts) goes in subfolders of the skill, such as `references/`.
- Each category `README.md` lists its skills.

## Skills

| Category | Skill | What it does |
|---|---|---|
| Sales | [revos-call-review](sales/revos-call-review/) | Scores one sales call out of 100, finds where the deal was lost and why, and gives two coaching points with the words to say. |
| Sales | [revos-sales-target-planner](sales/revos-sales-target-planner/) | Works back from the profit a founder needs to the sales, calls and leads each month takes, checks it against their calendar and names what breaks first. |
| Sales | [revos-dead-lead-revival](sales/revos-dead-lead-revival/) | Turns old leads, stalled proposals, no-shows and lapsed clients into a dated revival plan: who went quiet and why, short messages per group and the ten to message today. Sends nothing. |
| Marketing | [revos-vsl-writer](marketing/revos-vsl-writer/) | Writes a VSL or call-funnel video script from a fact-gathering intake, using a 14-section flow (hook, credibility, opportunity, price-first offer, objections, fit, CTA, proof, plus a skeptic pass for long versions), then QA-checks it. |
| Marketing | [revos-funnel-constraint-finder](marketing/revos-funnel-constraint-finder/) | Finds the one stage of a founder's sales funnel costing the most customers, from their own rough counts, and prices the fix in clients and money a month. |
| Marketing | [revos-buyer-language-miner](marketing/revos-buyer-language-miner/) | Writes two or three ready-to-run ads in the words buyers actually used, backed by a bank of every phrase checked word for word and counted by how many different people said it. |
| Marketing | [revos-get-quoted-by-ai](marketing/revos-get-quoted-by-ai/) | Tests whether ChatGPT, Perplexity, Gemini and Copilot name a business for its buyers' questions, then writes the pages, structured data and llms.txt they can quote. |
| Marketing | [revos-lead-magnet-factory](marketing/revos-lead-magnet-factory/) | Builds a finished scorecard or checklist lead magnet from the founder's own material, with the opt-in page and five follow-up emails that move the right people towards a call. |
| Branding | [revos-brand-voice](branding/revos-brand-voice/) | Builds a measured voice guide and a ready-to-paste AI voice prompt from a founder's own writing and speech, so ChatGPT, Claude, a VA or an agency writes like them. Counts every habit with a script, keeps the founder's own spelling, phrasing, money and dates, and calibrates against their ear. |
| Branding | [revos-carousel-copywriter](branding/revos-carousel-copywriter/) | Turns any idea into slide-by-slide copy for an Instagram carousel or LinkedIn document post, plus a paste-ready Claude Design prompt. |
| Branding | [revos-product-flythrough](branding/revos-product-flythrough/) | Turns the current project or website into a 15 to 25 second product flythrough video with motion, sound effects and share copy, built and rendered with HyperFrames. Adapted from [/brag](https://github.com/latent-spaces/brag) by Shunit Haviv Hakimi (MIT); music tracks not included. |
| Branding | [revos-product-flythrough-slim](branding/revos-product-flythrough-slim/) | The single-file Opus 5.5 version of the product flythrough: builds the whole video with the tools already on the machine. Adapted from /brag-slim (MIT). |
| Branding | [revos-brand-consistency-scan](branding/revos-brand-consistency-scan/) | Finds where a founder's website, LinkedIn and proposals contradict each other, quoted side by side, and gives one core line to align them on. |
| Branding | [revos-thumbnail-builder](branding/revos-thumbnail-builder/) | Designs finished video thumbnail PNGs from the founder's photo in three styles, tested at phone size. |
| Operations | [revos-delivery-capacity-check](operations/revos-delivery-capacity-check/) | Works out how many clients a founder can hold per offer and the three delivery tasks to hand over first. For service businesses of one to five people; does the sums with a script and keeps a memory file between runs. |
| Operations | [revos-founder-time-audit](operations/revos-founder-time-audit/) | Audits where a founder's week goes, ranks what to stop and hand over by the hours it gives back, costs each handover and writes the handover brief. |
| Operations | [revos-hiring-readiness](operations/revos-hiring-readiness/) | Tests whether a small business can afford and needs its next hire: Ready, Not yet or No, the most the hire can cost, then the scorecard, job ad and first 90 days. |
| Operations | [revos-scope-guard](operations/revos-scope-guard/) | Builds a scope kit for a service founder: a scope statement, what extras have cost, and the words to price extra work. |
| Finance | [revos-cash-forecast](finance/revos-cash-forecast/) | Builds a 13-week cash forecast from a business bank export and names the first week cash drops below a safety line, in a normal and a bad quarter. |
| Finance | [revos-get-paid](finance/revos-get-paid/) | Builds a plan to get overdue invoices paid: who to chase first, today's message in the founder's voice, dated follow-ups and a payment plan offer. |
| Finance | [revos-price-floor-calculator](finance/revos-price-floor-calculator/) | Works out the lowest price each service offer can charge with the founder's own hours paid, and gives a raise, hold or restructure verdict. |
| Finance | [revos-invoice-and-terms](finance/revos-invoice-and-terms/) | Makes a complete, numbered invoice as PDF and Word, totals checked by script, tax only as the founder supplies it, plus deposit and stage invoices. |
| Finance | [revos-client-credit-check](finance/revos-client-credit-check/) | Gives a Go, Caution or Stop verdict on whether a new client is likely to pay, with every finding sourced and dated, and the deposit and payment terms to match. |
| Finance | [revos-price-rise-pack](finance/revos-price-rise-pack/) | Plans a price rise for existing clients: who to raise, by how much and from when, the break-even client loss, 12-month cash, a live workbook and a letter per client. |
| Building | [revos-replica-recon](building/revos-replica/revos-replica-recon/) | Reverse-engineers any app into a recon map: screens, flows, components, an inferred data model and a feature matrix, from public pages, screenshots, store listings and the user's own account. |
| Building | [revos-replica-architect](building/revos-replica/revos-replica-architect/) | Plans the stack, database schema and API for the clone, and orders the build as a thin vertical slice first. |
| Building | [revos-replica-design](building/revos-replica/revos-replica-design/) | Rebuilds the design system as tokens and component specs, with open fonts and icons, and checks every colour pair for WCAG contrast. |
| Building | [revos-replica-build](building/revos-replica/revos-replica-build/) | Rebuilds the app screen by screen from the recon map, every state included, ticking off the feature matrix as it goes. |
| Building | [revos-replica-backend](building/revos-replica/revos-replica-backend/) | Auth, database access rules, Stripe payments, email, jobs and integrations through official APIs only, plus a security checklist. |
| Building | [revos-replica-test](building/revos-replica/revos-replica-test/) | Writes a test plan from the flows, Playwright end-to-end tests and bug reports by severity, and fixes S1 and S2 bugs test first. |
| Building | [revos-replica-diff](building/revos-replica/revos-replica-diff/) | Scores the clone against the original: a weighted feature parity score with the missing list, and a screenshot layout diff that ignores colour. |
| Building | [revos-replica-entrepreneur](building/revos-replica/revos-replica-entrepreneur/) | Reads what the app's users hate in real, linked reviews and turns it into a fix plan and a positioning angle you can sell. |
| Building | [revos-replica-brand](building/revos-replica/revos-replica-brand/) | Names and rebrands the clone: name checks to run, a new palette, a logo brief, a voice, and a sweep that finds anything of the original left in the code. |
| Building | [revos-replica-launch](building/revos-replica/revos-replica-launch/) | Writes the landing page, pricing and App Store and Google Play listing, and lints the listing against store limits and copycat rules. |
| Building | [revos-replica-deploy](building/revos-replica/revos-replica-deploy/) | Runs the preflight gate, sets up production, gives the DNS records for your domain and ships it when you say go. |

## Installing a skill

Copy the skill folder into `~/.claude/skills/` for Claude Code, or zip the folder and upload it under Settings → Capabilities → Skills in Claude.

The Replica skills in `building/revos-replica/` are one pack: copy all eleven `revos-replica-*` folders from it side by side, because some of them call each other's scripts. Run order and tools are in [building/revos-replica/README.md](building/revos-replica/README.md).
