#!/usr/bin/env node
// Starts a how-it's-made reel: reels/<YYYY-MM-DD>_<Slug>/ with the templates filled in.
//   node scripts/new-reel.mjs "How a pencil is made" [Slug]
import { mkdirSync, readFileSync, writeFileSync, existsSync } from "node:fs";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const title = process.argv[2];
if (!title) {
  console.error('usage: node scripts/new-reel.mjs "How a pencil is made" [Slug]');
  process.exit(1);
}
const slug =
  process.argv[3] ??
  title
    .replace(/^how (an? |the )?/i, "")
    .replace(/ (is|are) made$/i, "")
    .split(/\s+/)
    .map((w) => w[0].toUpperCase() + w.slice(1))
    .join("_")
    .replace(/[^A-Za-z0-9_]/g, "");
const date = new Date().toLocaleDateString("en-CA");
const dir = join(ROOT, "reels", `${date}_${slug}`);
if (existsSync(dir)) {
  console.error(`${dir} already exists`);
  process.exit(1);
}
mkdirSync(join(dir, "assets/images"), { recursive: true });
mkdirSync(join(dir, "Output"), { recursive: true });
const fill = (s) => s.replaceAll("{{TITLE}}", title);
writeFileSync(join(dir, "PROMPT.md"), fill(readFileSync(join(ROOT, "templates/PROMPT.md"), "utf8")));
writeFileSync(join(dir, "IMAGES.md"), fill(readFileSync(join(ROOT, "templates/IMAGES.md"), "utf8")));
writeFileSync(join(dir, "reel.json"), fill(readFileSync(join(ROOT, "templates/reel.json"), "utf8")));
writeFileSync(join(dir, "assets/shots.js"), fill(readFileSync(join(ROOT, "templates/shots.js"), "utf8")));
writeFileSync(join(dir, "script.txt"), "");
writeFileSync(join(dir, "facts.md"), `# ${title}: facts\n\n| Claim in the script | Source |\n| --- | --- |\n`);
console.log(dir);
