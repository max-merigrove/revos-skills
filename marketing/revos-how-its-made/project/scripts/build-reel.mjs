#!/usr/bin/env node
// Builds a how-it's-made reel's HyperFrames scenes from reel.json and the voiceover's
// word times. Everything is timed by words, so a new take re-times the whole film.
//
//   node scripts/build-reel.mjs reels/<dir>
//
// Reads   reels/<dir>/reel.json, reels/<dir>/<transcript> (word times)
// Writes  assets/timing.js, assets/kit/*, index.html, compositions/world.html,
//         compositions/captions.html, compositions/plates.html
//
// An "at" is a spoken word ("graphite"), its nth time ("lead#2"), with an offset
// ("baked+0.2"), alternatives ("1000|thousand"), or plain seconds (12.4). Shots search forward from the previous
// shot; callouts, stats and plates search forward from their shot's first word.
import { readFileSync, writeFileSync, mkdirSync, copyFileSync, existsSync } from "node:fs";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const dir = resolve(process.argv[2] || "");
if (!process.argv[2] || !existsSync(join(dir, "reel.json"))) {
  console.error("usage: node scripts/build-reel.mjs reels/<dir>   (needs reels/<dir>/reel.json)");
  process.exit(1);
}
const reel = JSON.parse(readFileSync(join(dir, "reel.json"), "utf8"));
const W = 1080;
const H = 1920;
const FPS = reel.fps ?? 30;

// ---------- words ----------
const rawWords = (() => {
  const j = JSON.parse(readFileSync(join(dir, reel.transcript ?? "assets/transcript.json"), "utf8"));
  const list = Array.isArray(j) ? j : j.words ?? j.segments?.flatMap((s) => s.words) ?? [];
  return list
    .map((w) => ({ text: String(w.text ?? w.word ?? "").trim(), start: +w.start, end: +w.end }))
    .filter((w) => w.text && !/^\[.*\]$/.test(w.text) && !Number.isNaN(w.start));
})();
// corrections: { "wrong": "right" } applied to the caption text only
const fixes = reel.captions?.fix ?? {};
// pronounce: { written: spoken } respellings sent to the voice ("lead": "led"); the
// voice says and Whisper hears the spoken form, so captions map it back to the written one
const respelled = Object.fromEntries(Object.entries(reel.pronounce ?? {}).map(([w, s]) => [s.toLowerCase(), w]));
function fixWord(text) {
  if (fixes[text] !== undefined) return fixes[text];
  const [, pre, core, post] = text.match(/^([^A-Za-z0-9]*)(.*?)([^A-Za-z0-9']*)$/);
  const to = fixes[core] ?? fixes[core.toLowerCase()] ?? respelled[core.toLowerCase()];
  if (to === undefined) return text;
  const upper = core[0] !== core[0].toLowerCase();
  return pre + (upper ? to[0].toUpperCase() + to.slice(1) : to) + post;
}
const words = rawWords.map((w) => ({ ...w, text: fixWord(w.text) }));
const norm = (s) =>
  String(s)
    .toLowerCase()
    .replace(/[’']/g, "'")
    .replace(/[^a-z0-9']/g, "");
const voiceEnd = words.length ? words[words.length - 1].end : 0;
const duration = +(reel.duration ?? voiceEnd + (reel.tail ?? 0.8)).toFixed(3);

function resolveAt(at, from = 0, what = "") {
  if (typeof at === "number") return { t: at, i: from };
  const m = String(at).match(/^(.+?)(?:#(\d+))?(?:([+-]\d*\.?\d+))?$/);
  const targets = m[1].split("|").map(norm); // "1000|thousand": Whisper writes numbers either way
  let nth = m[2] ? +m[2] : 1;
  const off = m[3] ? +m[3] : 0;
  for (let i = from; i < words.length; i++) {
    if (targets.includes(norm(words[i].text)) && --nth === 0) return { t: words[i].start + off, i };
  }
  const ahead = words.slice(from, from + 12).map((w) => w.text).join(" ");
  throw new Error(`${what}: "${at}" not found after word ${from} ("${ahead} ...")`);
}

// ---------- shots ----------
let cursor = 0;
const shots = reel.shots.map((s, n) => {
  const r = n === 0 && s.at === undefined ? { t: 0, i: 0 } : resolveAt(s.at, cursor, `shot ${s.id}`);
  cursor = r.i;
  return { ...s, start: n === 0 ? 0 : +r.t.toFixed(3), wordIndex: r.i };
});
shots.forEach((s, n) => (s.end = n + 1 < shots.length ? shots[n + 1].start : duration));

const timing = {
  duration,
  fadeIn: reel.fadeIn ?? 0,
  fadeOut: reel.fadeOut ?? 0.5,
  shots: shots.map((s) => ({
    id: s.id,
    start: s.start,
    end: s.end,
    in: s.in ?? "cut",
    inDur: s.inDur ?? 0.45,
    // marks: { name: word } -> seconds from the shot's start, for moves inside the shot
    marks: Object.fromEntries(
      Object.entries(s.marks ?? {}).map(([k, at]) => [k, +(resolveAt(at, s.wordIndex, `shot ${s.id} mark ${k}`).t - s.start).toFixed(3)]),
    ),
  })),
};

// ---------- copy the kit ----------
mkdirSync(join(dir, "assets/kit"), { recursive: true });
mkdirSync(join(dir, "compositions"), { recursive: true });
for (const f of ["three.bundle.js", "studio.js"]) copyFileSync(join(ROOT, "kit", f), join(dir, "assets/kit", f));
writeFileSync(join(dir, "assets/timing.js"), `window.REEL = ${JSON.stringify(timing, null, 2)};\n`);
const css = readFileSync(join(ROOT, "kit/overlay.css"), "utf8");
const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const f3 = (n) => (+n).toFixed(3);

// ---------- world: callouts and stats ----------
const overlays = [];
let uid = 0;
for (const s of shots) {
  const until = (u) => (u === undefined ? s.end - 0.05 : resolveAt(u, s.wordIndex, `shot ${s.id} until`).t);
  for (const c of s.callouts ?? []) {
    const start = c.at === undefined ? s.start + 0.3 : resolveAt(c.at, s.wordIndex, `callout ${c.text}`).t;
    const end = until(c.until);
    const cls = ["hm-callout", "clip", c.down ? "hm-down" : ""].join(" ").trim();
    overlays.push(
      `<div id="co-${++uid}" class="${cls}" data-start="${f3(start)}" data-duration="${f3(end - start)}" data-track-index="2" data-shot="${s.id}"` +
        `${c.anchor ? ` data-anchor="${c.anchor}"` : ""}${c.x !== undefined ? ` data-x="${c.x}" data-y="${c.y}"` : ""} data-layout-allow-overflow>` +
        `<div class="hm-in" style="--lead:${c.lead ?? 150}px;--angle:${c.angle ?? 0}deg"><i class="hm-dot"></i><i class="hm-leader"></i>` +
        `<div class="hm-tip"><span class="hm-label">${esc(c.text)}</span></div></div></div>`,
    );
  }
  for (const st of s.stats ?? []) {
    const start = st.at === undefined ? s.start + 0.3 : resolveAt(st.at, s.wordIndex, `stat ${st.num}`).t;
    const end = until(st.until);
    const counts = typeof st.num === "number";
    const cls = ["hm-stat", "clip", st.anchor ? "" : "hm-nolead", st.down ? "hm-down" : ""].join(" ").replace(/\s+/g, " ").trim();
    const shown = counts ? (st.from ?? 0).toLocaleString("en-GB") : esc(st.num);
    overlays.push(
      `<div id="st-${++uid}" class="${cls}" data-start="${f3(start)}" data-duration="${f3(end - start)}" data-track-index="2" data-shot="${s.id}"` +
        `${st.anchor ? ` data-anchor="${st.anchor}"` : ""}${st.x !== undefined ? ` data-x="${st.x}" data-y="${st.y}"` : ""}` +
        `${counts ? ` data-count-from="${st.from ?? 0}" data-count-to="${st.num}" data-decimals="${st.decimals ?? 0}"` : ""} data-layout-allow-overflow>` +
        `<div class="hm-in" style="--lead:${st.anchor ? st.lead ?? 150 : 0}px;--angle:${st.angle ?? 0}deg"><i class="hm-dot"></i><i class="hm-leader"></i>` +
        `<div class="hm-tip"><span class="hm-label">${esc(st.before ?? "")}<b class="hm-num">${shown}</b>${st.suffix ? `<b class="hm-num-after">${esc(st.suffix)}</b>` : ""} ${esc(st.unit ?? "")}</span></div></div></div>`,
    );
  }
}

const world = `<template>
  <style>
    #root { position: absolute; inset: 0; background: #0c0b0a; overflow: hidden; }
    #hm-canvas { position: absolute; left: 0; top: 0; width: ${W}px; height: ${H}px; }
${css}
  </style>
  <div id="root" data-composition-id="world" data-width="${W}" data-height="${H}" data-start="0" data-duration="${duration}">
    <canvas id="hm-canvas" width="${W}" height="${H}" data-layout-ignore></canvas>
    ${overlays.join("\n    ")}
  </div>
  <script src="assets/kit/three.bundle.js"></script>
  <script src="assets/kit/studio.js"></script>
  <script src="assets/timing.js"></script>
  <script src="assets/shots.js"></script>
  <script>
    HM.boot({
      canvas: document.getElementById("hm-canvas"),
      width: ${W},
      height: ${H},
      bloom: ${JSON.stringify(reel.bloom ?? {})},
      look: ${JSON.stringify(reel.look ?? {})},
    });
    const tl = gsap.timeline({ paused: true });
    tl.set({}, {}, ${duration});
    window.__timelines["world"] = tl;
  </script>
</template>
`;
writeFileSync(join(dir, "compositions/world.html"), world);

// ---------- captions ----------
const cap = reel.captions ?? {};
const maxWords = cap.maxWords ?? 5;
// highlights: "word", "word#2" or { w, emoji }; each takes its first unused match in order
const hl = new Map();
{
  let from = 0;
  for (const h of cap.highlight ?? []) {
    const spec = typeof h === "string" ? { w: h } : h;
    const r = resolveAt(spec.w, from, "highlight");
    hl.set(r.i, spec);
    from = r.i + 1;
  }
}
const SMALL = new Set(["a", "an", "the", "to", "of", "in", "on", "and", "or", "but", "like", "with", "for", "at", "is", "it", "its", "into", "that", "so"]);
const groups = [];
let g = [];
words.forEach((w, i) => {
  g.push(i);
  const next = words[i + 1];
  const gap = next ? next.start - w.end : 1;
  const stop = /[.?!]$/.test(w.text);
  const soft = /[,;:]$/.test(w.text) && g.length >= 2;
  if (!next || stop || soft || gap >= 0.3 || g.length >= maxWords) {
    // never end a line on a little word ("a", "the", "like"): carry it to the next line
    const carry = next && !stop && !soft && g.length > 2 && SMALL.has(norm(w.text)) ? [g.pop()] : [];
    groups.push(g);
    g = carry;
  }
});
let capHtml = "";
let capJs = "";
groups.forEach((ix, n) => {
  const first = words[ix[0]];
  const last = words[ix[ix.length - 1]];
  const nextStart = groups[n + 1] ? words[groups[n + 1][0]].start : duration;
  const start = Math.max(0, first.start - 0.04);
  const end = Math.min(nextStart - 0.02, last.end + 0.5);
  const spans = ix
    .map((i) => {
      const h = hl.get(i);
      const emo = h?.emoji ? `<span class="emo">${h.emoji}</span>` : "";
      if (h) return `${emo}<span id="cw${i}" class="w kw"><i class="box"></i><i class="hd a"></i><i class="hd b"></i>${esc(words[i].text)}</span>`;
      return `<span id="cw${i}" class="w">${esc(words[i].text)}</span>`;
    })
    .join("");
  capHtml += `    <div id="cg${n}" class="hm-cap clip" data-start="${f3(start)}" data-duration="${f3(end - start)}" data-track-index="1">${spans}</div>\n`;
  ix.forEach((i, k) => {
    const w = words[i];
    capJs += `    tl.set("#cw${i}", { display: "inline-block" }, ${f3(w.start)});\n`;
    capJs += `    tl.fromTo("#cw${i}", { opacity: 0, y: 10 }, { opacity: 1, y: 0, color: "#ffffff", duration: 0.12, ease: "power2.out" }, ${f3(w.start)});\n`;
    const after = ix[k + 1] !== undefined ? words[ix[k + 1]].start : null;
    // dim once the next word is spoken, never before this word's own fade-in has finished
    if (after !== null && !hl.has(i)) capJs += `    tl.to("#cw${i}", { color: "rgba(255,255,255,0.42)", duration: 0.1 }, ${f3(Math.max(after, w.start + 0.121))});\n`;
  });
});
// words before their time are hidden
const captions = `<template>
  <style>
    #root { position: absolute; inset: 0; overflow: visible; }
${css}
    .hm-cap .w { opacity: 0; }
  </style>
  <div id="root" data-composition-id="captions" data-width="${W}" data-height="${H}" data-start="0" data-duration="${duration}">
${capHtml}  </div>
  <script>
    const tl = gsap.timeline({ paused: true });
${capJs}    tl.set({}, {}, ${duration});
    window.__timelines["captions"] = tl;
  </script>
</template>
`;
writeFileSync(join(dir, "compositions/captions.html"), captions);

// ---------- plates: analogy objects, prints, archive, generated clips ----------
let plHtml = "";
let plJs = "";
(reel.plates ?? []).forEach((p, n) => {
  const shot = shots.find((s) => s.id === p.shot) ?? shots[0];
  const start = p.at === undefined ? shot.start : resolveAt(p.at, shot.wordIndex, `plate ${n}`).t;
  const end = p.until === undefined ? shot.end : resolveAt(p.until, shot.wordIndex, `plate ${n} until`).t;
  const d = end - start;
  const id = `pl${n}`;
  let inner = `<div class="bg"></div>`;
  if (p.kind === "full") inner += `<img id="${id}-m" class="full" src="${p.src}" alt="" />`;
  if (p.kind === "video") inner += `<video id="${id}-m" class="full" src="${p.src}" muted playsinline data-start="${f3(start)}" data-duration="${f3(d)}"></video>`;
  if (p.kind === "print") inner += `<div id="${id}-m" class="print"><img src="${p.src}" alt="" /></div>${p.name ? `<div class="print-name">${esc(p.name)}</div>` : ""}`;
  if (p.kind === "float") inner += `<img id="${id}-m" class="full" src="${p.src}" alt="" style="object-fit:contain" />`;
  if (p.year) inner += `<div id="${id}-y" class="year">${esc(p.year)}</div>`;
  plHtml += `    <div id="${id}" class="hm-plate clip" data-start="${f3(start)}" data-duration="${f3(d)}" data-track-index="1">${inner}</div>\n`;
  const push = p.push ?? 0.06;
  if (p.kind === "print")
    plJs += `    tl.fromTo("#${id}-m", { y: 60, rotation: -6, scale: 1.04, opacity: 0 }, { y: 0, rotation: -2.5, scale: 1, opacity: 1, duration: 0.5, ease: "power3.out" }, ${f3(start)});\n    tl.to("#${id}-m", { scale: ${1 + push}, rotation: -1, duration: ${f3(d - 0.5)}, ease: "none" }, ${f3(start + 0.5)});\n`;
  else if (p.kind !== "video") plJs += `    tl.fromTo("#${id}-m", { scale: 1 }, { scale: ${1 + push}, duration: ${f3(d)}, ease: "none" }, ${f3(start)});\n`;
  if (p.year) plJs += `    tl.fromTo("#${id}-y", { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.4, ease: "power2.out" }, ${f3(start + 0.3)});\n`;
});
const plates = `<template>
  <style>
    #root { position: absolute; inset: 0; overflow: hidden; }
${css}
  </style>
  <div id="root" data-composition-id="plates" data-width="${W}" data-height="${H}" data-start="0" data-duration="${duration}">
${plHtml}  </div>
  <script>
    const tl = gsap.timeline({ paused: true });
${plJs}    tl.set({}, {}, ${duration});
    window.__timelines["plates"] = tl;
  </script>
</template>
`;
writeFileSync(join(dir, "compositions/plates.html"), plates);

// ---------- index ----------
const audio = [];
if (reel.voice) audio.push(`<audio id="vo" class="clip" src="${reel.voice}" data-start="0" data-track-index="10" data-volume="${reel.voiceVolume ?? 1}"></audio>`);
if (reel.music)
  audio.push(
    `<audio id="music" class="clip" src="${reel.music.src}" data-start="0" data-duration="${duration}" data-track-index="11" data-volume="${reel.music.volume ?? 0.12}" data-fade-out="1.2"></audio>`,
  );
(reel.sfx ?? []).forEach((s, n) => {
  const t = typeof s.at === "number" ? s.at : resolveAt(s.at, 0, `sfx ${n}`).t;
  audio.push(`<audio id="sfx${n}" class="clip" src="${s.src}" data-start="${f3(t + (s.offset ?? 0))}" data-track-index="12" data-volume="${s.volume ?? 0.5}"></audio>`);
});
const index = `<!doctype html>
<html lang="en-GB">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=${W}, height=${H}" />
    <title>${esc(reel.title ?? "How it's made")}</title>
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
    <style>
      * { margin: 0; padding: 0; box-sizing: border-box; }
      html, body { width: ${W}px; height: ${H}px; overflow: hidden; background: #0c0b0a; }
      #ground { position: absolute; inset: 0; background: #0c0b0a; }
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="${duration}" data-width="${W}" data-height="${H}" data-fps="${FPS}">
      <div id="ground"></div>
      <div id="world" data-composition-id="world" data-composition-src="compositions/world.html" data-start="0" data-duration="${duration}" data-track-index="1" data-track-kind="graphics" data-width="${W}" data-height="${H}" style="z-index:1"></div>
      <div id="plates" data-composition-id="plates" data-composition-src="compositions/plates.html" data-start="0" data-duration="${duration}" data-track-index="2" data-track-kind="graphics" data-width="${W}" data-height="${H}" style="z-index:2"></div>
      <div id="captions" data-composition-id="captions" data-composition-src="compositions/captions.html" data-start="0" data-duration="${duration}" data-track-index="3" data-track-kind="captions" data-width="${W}" data-height="${H}" style="z-index:3"></div>
      ${audio.join("\n      ")}
    </div>
    <script>
      const tl = gsap.timeline({ paused: true });
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
`;
writeFileSync(join(dir, "index.html"), index);
for (const f of ["hyperframes.json", "meta.json"]) {
  if (!existsSync(join(dir, f))) {
    const body =
      f === "meta.json"
        ? { id: dir.split("/").pop(), name: reel.title ?? dir.split("/").pop(), createdAt: new Date().toISOString() }
        : { $schema: "https://hyperframes.heygen.com/schema/hyperframes.json", paths: { blocks: "compositions", assets: "assets" }, media: { autoProxy: true } };
    writeFileSync(join(dir, f), JSON.stringify(body, null, 2) + "\n");
  }
}

console.log(`built ${dir.split("/").pop()}: ${duration}s, ${shots.length} shots, ${groups.length} caption groups, ${overlays.length} overlays`);
for (const s of shots) console.log(`  ${s.start.toFixed(2).padStart(6)}  ${(s.end - s.start).toFixed(2).padStart(5)}s  ${s.in ?? "cut"}  ${s.id}`);
