# Building

RevOS skills for building software. One folder per skill, named `revos-<skill>`, each with a `SKILL.md`.

The eleven `revos-replica-*` skills are one pack: they rebuild what an existing app does (its features and flows, clean-room style, never its code, logo, copy or content), test it, then rebrand it and ship it as your own. Run them in order. Each one reads what the last one wrote, in a `replica/` folder in your project:

```
recon -> architect -> design -> build -> backend -> test -> diff -> entrepreneur -> brand -> launch -> deploy
```

Any one also runs on its own. `/revos-replica-entrepreneur` on an app you are only thinking about cloning is a quick way to find out if you should.

| Skill | What it does |
|---|---|
| [revos-replica-recon](revos-replica-recon/) | Reverse-engineers any app into a recon map: screens, flows, components, an inferred data model and a feature matrix, from public pages, screenshots, store listings and the user's own account. |
| [revos-replica-architect](revos-replica-architect/) | Plans the stack, database schema and API for the clone, and orders the build as a thin vertical slice first. |
| [revos-replica-design](revos-replica-design/) | Rebuilds the design system as tokens and component specs, with open fonts and icons, and checks every colour pair for WCAG contrast. |
| [revos-replica-build](revos-replica-build/) | Rebuilds the app screen by screen from the recon map, every state included, ticking off the feature matrix as it goes. |
| [revos-replica-backend](revos-replica-backend/) | Auth, database access rules, Stripe payments, email, jobs and integrations through official APIs only, plus a security checklist. |
| [revos-replica-test](revos-replica-test/) | Writes a test plan from the flows, Playwright end-to-end tests and bug reports by severity, and fixes S1 and S2 bugs test first. |
| [revos-replica-diff](revos-replica-diff/) | Scores the clone against the original: a weighted feature parity score with the missing list, and a screenshot layout diff that ignores colour. |
| [revos-replica-entrepreneur](revos-replica-entrepreneur/) | Reads what the app's users hate in real, linked reviews and turns it into a fix plan and a positioning angle you can sell. |
| [revos-replica-brand](revos-replica-brand/) | Names and rebrands the clone: name checks to run, a new palette, a logo brief, a voice, and a sweep that finds anything of the original left in the code. |
| [revos-replica-launch](revos-replica-launch/) | Writes the landing page, pricing and App Store and Google Play listing, and lints the listing against store limits and copycat rules. |
| [revos-replica-deploy](revos-replica-deploy/) | Runs the preflight gate, sets up production, gives the DNS records for your domain and ships it when you say go. |

## The tools

Six standard-library Python scripts, in the `scripts/` folder of the skill that uses them. None touch the network. They need Python 3.8 or newer and nothing to install.

```bash
python3 revos-replica-diff/scripts/imgdiff.py original.png clone.png --out diff.png   # layout diff, ignores colour
python3 revos-replica-diff/scripts/parity.py replica/features.csv                     # parity score + missing list
python3 revos-replica-entrepreneur/scripts/reviews.py replica/reviews.csv             # what users hate, ranked, linked
python3 revos-replica-design/scripts/contrast.py replica/design/tokens.json           # WCAG contrast on your tokens
python3 revos-replica-brand/scripts/sweep.py . --avoid "Original App"                 # anything of the original left?
python3 revos-replica-launch/scripts/listing.py replica/launch/listing.json           # store limits + copycat checks
```

Their tests are in `tests/`:

```bash
python3 -m unittest discover -s building/tests -v
```

## Installing the pack

Copy all eleven `revos-replica-*` folders into `~/.claude/skills/` side by side. `revos-replica-brand` and `revos-replica-deploy` call the other skills' scripts by relative path (`../revos-replica-diff/scripts/parity.py`), so they need to sit next to each other.

## The fine print

- **It rebuilds functionality and UX patterns, clean-room style.** It never copies the target's source code, assets, logos, trademarks, copy or private APIs.
- **It only reads what you are allowed to read.** Public pages and your own account. No scraping behind a login, no paywalls, no one else's account.
- **It always rebrands before launch.** `/revos-replica-deploy` will not ship until the sweep is clean.
- **"Clone any app" means the features and the flow,** not the content, the network or the licences an app owns.
- **The Entrepreneur never makes things up.** Every quote is verbatim and linked, and the sample size is stated.
- **Check before you sell.** Run the trademark checks `/revos-replica-brand` lists, read the terms of anything you used, and talk to a lawyer before launch if there is money on the line. This is not legal advice.

## Credits

The `revos-replica-*` skills are adapted from [replica-skill](https://github.com/Jakeschincariol/replica-skill) by Jake Schincariol ([opusjake.ai](https://opusjake.ai)), under the MIT licence (a copy is in each skill folder). Changes here: the skills are renamed with the `revos-` prefix, scripts moved into `scripts/` and templates into `assets/`, and the plugin manifest is left out.
