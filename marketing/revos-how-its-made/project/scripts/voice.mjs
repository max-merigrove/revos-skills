#!/usr/bin/env node
// The voiceover, in two steps around the TTS call.
//
//   node scripts/voice.mjs text reels/<dir>   script.txt -> assets/voice/chunks.json (what the voice reads)
//   node scripts/voice.mjs join reels/<dir>   assets/voice/part1.mp3 ... -> assets/vo.wav
//
// text: blocks of script.txt separated by a blank line become one TTS call each (a block
// over the limit is split at sentences). reel.json "pronounce" respells words that are
// written one way and said another ("lead": "led"), whole words only, keeping capitals.
// Delivery tags like [pause] in script.txt pass through to the voice.
//
// join: trims each part's edges, puts a breath between parts, levels to -16 LUFS.
import { readFileSync, writeFileSync, mkdirSync, existsSync, readdirSync } from "node:fs";
import { join, resolve } from "node:path";
import { execFileSync } from "node:child_process";

const [cmd, d] = process.argv.slice(2);
const dir = resolve(d || "");
if (!["text", "join"].includes(cmd) || !existsSync(join(dir, "reel.json"))) {
  console.error("usage: node scripts/voice.mjs text|join reels/<dir>");
  process.exit(1);
}
const reel = JSON.parse(readFileSync(join(dir, "reel.json"), "utf8"));
const vdir = join(dir, "assets/voice");
mkdirSync(vdir, { recursive: true });
const LIMIT = reel.voiceChunkBytes ?? 470; // Fish free plan: 500 bytes a call

if (cmd === "text") {
  const pron = reel.pronounce ?? {};
  const respell = (s) =>
    Object.entries(pron).reduce(
      (acc, [w, say]) =>
        acc.replace(new RegExp(`\\b${w}\\b`, "gi"), (m) => (m[0] !== m[0].toLowerCase() ? say[0].toUpperCase() + say.slice(1) : say)),
      s,
    );
  const blocks = readFileSync(join(dir, "script.txt"), "utf8")
    .split(/\n\s*\n/)
    .map((b) => respell(b.replace(/\s+/g, " ").trim()))
    .filter(Boolean);
  const chunks = [];
  for (const b of blocks) {
    if (Buffer.byteLength(b) <= LIMIT) {
      chunks.push(b);
      continue;
    }
    let cur = "";
    for (const s of b.match(/[^.!?]+[.!?]+["']?\s*|.+$/g)) {
      if (cur && Buffer.byteLength(cur + s) > LIMIT) {
        chunks.push(cur.trim());
        cur = "";
      }
      cur += s;
    }
    if (cur.trim()) chunks.push(cur.trim());
  }
  writeFileSync(join(vdir, "chunks.json"), JSON.stringify(chunks, null, 2) + "\n");
  chunks.forEach((c, i) => console.log(`part${i + 1}  ${Buffer.byteLength(c)} bytes\n  ${c}\n`));
  console.log(`${chunks.length} parts, ${chunks.reduce((n, c) => n + Buffer.byteLength(c), 0)} bytes (about that many Fish credits)`);
}

if (cmd === "join") {
  const parts = readdirSync(vdir)
    .filter((f) => /^part\d+\.(mp3|wav)$/.test(f))
    .sort((a, b) => parseInt(a.slice(4)) - parseInt(b.slice(4)));
  if (!parts.length) throw new Error(`no part1.mp3 ... in ${vdir}`);
  const gap = reel.voiceGap ?? 0.4;
  const trim =
    "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.03,areverse," +
    "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.08,areverse,aresample=48000,aformat=channel_layouts=mono";
  const graph =
    parts.map((_, i) => `[${i}]${trim}${i < parts.length - 1 ? `,apad=pad_dur=${gap}` : ""}[p${i}]`).join(";") +
    `;${parts.map((_, i) => `[p${i}]`).join("")}concat=n=${parts.length}:v=0:a=1,loudnorm=I=-16:TP=-1.5:LRA=11[out]`;
  const gfile = join(vdir, "join.filter");
  writeFileSync(gfile, graph);
  // ffmpeg 8 reads a filter graph from a file with -/filter_complex
  execFileSync("ffmpeg", ["-v", "error", "-y", ...parts.flatMap((p) => ["-i", join(vdir, p)]), "-/filter_complex", gfile, "-map", "[out]", "-ar", "48000", join(dir, "assets/vo.wav")], {
    stdio: "inherit",
  });
  const dur = execFileSync("ffprobe", ["-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", join(dir, "assets/vo.wav")]).toString().trim();
  console.log(`assets/vo.wav from ${parts.length} parts: ${(+dur).toFixed(2)} s`);
}
