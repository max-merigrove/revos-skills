#!/usr/bin/env node
// Checks everything a how-it's-made reel needs, ending with a real 3D test render.
//   node scripts/doctor.mjs            all checks
//   node scripts/doctor.mjs --quick    skip the test render
// Exits 1 if anything required is missing; each failure prints the command that fixes it.
import { execFileSync, spawnSync } from "node:child_process";
import { existsSync, mkdirSync, writeFileSync, rmSync, readdirSync, copyFileSync, statfsSync } from "node:fs";
import { join, dirname, resolve } from "node:path";
import { homedir, platform } from "node:os";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const HF = "hyperframes@0.9.9"; // the version the kit was built and tested on
const quick = process.argv.includes("--quick");
const mac = platform() === "darwin";
let failed = 0;
let warned = 0;

const run = (cmd, args, opts = {}) => spawnSync(cmd, args, { encoding: "utf8", ...opts });
function line(ok, name, detail, fix, optional = false) {
  const mark = ok ? "✓" : optional ? "!" : "✗";
  console.log(`  ${mark} ${name.padEnd(22)} ${detail}`);
  if (!ok && fix) console.log(`    ${" ".repeat(22)} fix: ${fix}`);
  if (!ok) optional ? warned++ : failed++;
}

console.log("\nhow-it's-made doctor\n");

// 1. Node
const nodeMajor = +process.versions.node.split(".")[0];
line(nodeMajor >= 22, "Node.js", `v${process.versions.node}`, mac ? "brew install node@22  (or nvm install 22)" : "install Node 22 from nodejs.org");

// 2. ffmpeg / ffprobe (8+ for -/filter_complex, used by scripts/voice.mjs join)
for (const bin of ["ffmpeg", "ffprobe"]) {
  const r = run(bin, ["-version"]);
  const v = r.stdout?.match(/version (n?\d+)\.?(\d*)/);
  const major = v ? parseInt(v[1].replace("n", ""), 10) : 0;
  line(r.status === 0 && major >= 8, bin, r.status === 0 ? `version ${v?.[1]}${v?.[2] ? "." + v[2] : ""}` : "not found", mac ? "brew install ffmpeg" : "install ffmpeg 8 or newer");
}

// 3. HyperFrames CLI + its own doctor (Chrome, whisper)
const hf = run("npx", ["--yes", HF, "doctor", "--json"], { cwd: ROOT, timeout: 240000 });
let hfChecks = [];
try {
  hfChecks = JSON.parse(hf.stdout.slice(hf.stdout.indexOf("{"))).checks;
} catch {
  /* reported below */
}
line(hfChecks.length > 0, "HyperFrames CLI", hfChecks.length ? HF : "could not run", `npx --yes ${HF} doctor`);
const hfc = (name) => hfChecks.find((c) => c.name === name);
const chrome = hfc("Chrome");
line(!!chrome?.ok, "Render browser", chrome?.ok ? "Chrome headless shell" : chrome?.detail ?? "unknown", `npx ${HF} browser ensure`);
const whisper = hfc("whisper-cpp");
line(
  !!whisper?.ok || /first use/i.test(whisper?.detail ?? ""),
  "Whisper (word times)",
  whisper?.detail ?? "unknown",
  mac ? "brew install whisper-cpp  (or let `hyperframes transcribe` install it on first use)" : "let `hyperframes transcribe` install it on first use",
);
const disk = statfsSync(ROOT);
const freeGb = (disk.bavail * disk.bsize) / 1e9;
line(freeGb > 5, "Disk space", `${freeGb.toFixed(1)} GB free (a reel's master render is ~400 MB)`, "free up space");

// 4. The project
line(existsSync(join(ROOT, "node_modules/three")), "Project packages", "three, esbuild", `cd "${ROOT}" && npm install`);
line(existsSync(join(ROOT, "kit/three.bundle.js")), "3D bundle", "kit/three.bundle.js", `cd "${ROOT}" && npm run vendor`);

// 5. Python for the pronunciation check
const py = run("python3", ["-c", "import numpy, scipy; print(numpy.__version__, scipy.__version__)"]);
line(py.status === 0, "Python numpy + scipy", py.status === 0 ? py.stdout.trim() : "missing (scripts/check-vowel.py)", "python3 -m pip install --user numpy scipy");

// 6. Emoji font for the caption emoji
const emoji = mac ? existsSync("/System/Library/Fonts/Apple Color Emoji.ttc") : existsSync("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf");
line(emoji, "Emoji font", mac ? "Apple Color Emoji" : "Noto Color Emoji", mac ? "comes with macOS" : "sudo apt install fonts-noto-color-emoji, then set src: local(\"Noto Color Emoji\") in kit/overlay.css", true);

// 7. Skills this one calls
const skills = join(homedir(), ".claude/skills");
const need = [
  ["hyperframes", true, `npx ${HF} skills`],
  ["hyperframes-cli", true, `npx ${HF} skills`],
  ["hook-method", false, "optional: Max's Triple Hook skill; without it, judge hooks by STYLE.md section 2"],
  ["ig-human", false, "optional: strips AI tells from the script; without it, read the script aloud once"],
];
for (const [name, required, fix] of need) line(existsSync(join(skills, name, "SKILL.md")), `Skill: ${name}`, required ? "required" : "optional", fix, !required);

// 8. A real render: one shot of the kit, snapshotted, checked for a lit 3D object
if (!quick && failed === 0) {
  const t = join(ROOT, "scratch/doctor-smoke");
  rmSync(t, { recursive: true, force: true });
  mkdirSync(join(t, "assets"), { recursive: true });
  writeFileSync(
    join(t, "reel.json"),
    JSON.stringify({ title: "Doctor", transcript: "assets/transcript.json", tail: 0.5, shots: [{ id: "hook", callouts: [{ text: "Test", anchor: "top", at: "test" }] }], captions: { highlight: ["render"] } }),
  );
  const ws = ["This", "is", "a", "test", "render."].map((text, i) => ({ text, start: 0.2 + i * 0.35, end: 0.5 + i * 0.35 }));
  writeFileSync(join(t, "assets/transcript.json"), JSON.stringify(ws));
  copyFileSync(join(ROOT, "templates/shots.js"), join(t, "assets/shots.js"));
  const b = run("node", [join(ROOT, "scripts/build-reel.mjs"), t]);
  const snap = b.status === 0 ? run("npx", ["--yes", HF, "snapshot", "--at", "1.6", "--no-end", "--timeout", "120000"], { cwd: t, timeout: 300000 }) : b;
  let lum = 0;
  let png = "";
  try {
    const sdir = join(t, ".hyperframes/artifacts/snapshots");
    const last = readdirSync(sdir).sort().pop();
    png = join(sdir, last, readdirSync(join(sdir, last)).find((f) => f.endsWith(".png")));
    // mean brightness of the middle of the frame, where the lit test cube sits
    const raw = execFileSync("ffmpeg", ["-v", "error", "-i", png, "-vf", "crop=500:500:290:600,scale=1:1", "-f", "rawvideo", "-pix_fmt", "gray", "-"]);
    lum = raw[0];
  } catch {
    /* reported below */
  }
  line(lum > 25, "Test render (WebGL)", lum ? `3D drew (brightness ${lum})` : (snap.stderr || snap.stdout || "failed").trim().split("\n").pop(), "the 3D did not draw: run `npx hyperframes doctor`, and try `snapshot --no-browser-gpu` to test software WebGL");
  if (lum > 25) console.log(`    ${" ".repeat(22)} frame: ${png}`);
} else if (!quick) {
  console.log("  - Test render            skipped until the failures above are fixed");
}

// 9. Things only Claude can check
console.log(`
  Claude checks these itself (no command line):
  - Fish Audio connector authorised (get_credit_balance answers), if the voice is TTS
  - Web search available, for step 2's research
`);
console.log(failed ? `${failed} required item(s) missing.` : warned ? `Ready (${warned} optional item(s) missing).` : "Ready.");
process.exit(failed ? 1 : 0);
