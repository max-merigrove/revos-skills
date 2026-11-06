#!/usr/bin/env node
// Creates (or updates) a how-it's-made project from the copy packed inside the skill.
//   node ~/.claude/skills/revos-how-its-made/project/scripts/setup.mjs "<folder>"            new project
//   node ~/.claude/skills/revos-how-its-made/project/scripts/setup.mjs "<folder>" --update   refresh kit, scripts, templates; reels untouched
// Then installs packages, builds the 3D bundle, adds the pencil example and runs the doctor.
import { cpSync, existsSync, mkdirSync, readFileSync } from "node:fs";
import { join, dirname, resolve } from "node:path";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const SRC = resolve(dirname(fileURLToPath(import.meta.url)), ".."); // the packed project
const EXAMPLE = resolve(SRC, "../examples/pencil");
const target = process.argv[2] && resolve(process.argv[2]);
const update = process.argv.includes("--update");
if (!target) {
  console.error('usage: node setup.mjs "<folder>" [--update]');
  process.exit(1);
}
if (target === SRC) {
  console.error("that is the skill's own copy: choose a folder for the project");
  process.exit(1);
}
const isProject = existsSync(join(target, "package.json")) && JSON.parse(readFileSync(join(target, "package.json"), "utf8")).name === "merigrove-how-its-made";
if (existsSync(target) && !isProject && !update) {
  const empty = !existsSync(target) || execFileSync("ls", ["-A", target]).toString().trim() === "";
  if (!empty) {
    console.error(`${target} exists and is not a how-it's-made project: choose an empty or new folder`);
    process.exit(1);
  }
}
if (isProject && !update) {
  console.error(`${target} is already a project: add --update to refresh its kit, scripts and templates`);
  process.exit(1);
}
mkdirSync(join(target, "reels"), { recursive: true });
for (const p of ["STYLE.md", "README.md", "package.json", "package-lock.json", ".gitignore", "kit", "scripts", "templates"]) {
  if (existsSync(join(SRC, p))) cpSync(join(SRC, p), join(target, p), { recursive: true });
}
console.log(`${update ? "updated" : "created"} ${target}`);
const sh = (cmd, args) => execFileSync(cmd, args, { cwd: target, stdio: "inherit" });
sh("npm", ["install", "--no-audit", "--no-fund"]);
sh("npm", ["run", "vendor"]);
const ex = join(target, "reels/example_Pencil");
if (!existsSync(ex) && existsSync(EXAMPLE)) {
  cpSync(EXAMPLE, ex, { recursive: true });
  sh("node", ["scripts/build-reel.mjs", ex]);
  console.log(`example reel: ${ex}`);
}
sh("node", ["scripts/doctor.mjs"]);
