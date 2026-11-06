// Bundles Three.js and the add-ons the kit uses into kit/three.bundle.js (window.THREE),
// so every reel loads 3D from a local file: no CDN modules at render time.
import { build } from "esbuild";
import { writeFileSync, readFileSync, mkdirSync } from "node:fs";

mkdirSync("scratch", { recursive: true });
writeFileSync(
  "scratch/three-entry.js",
  `import * as THREE from "three";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";
import { RoundedBoxGeometry } from "three/examples/jsm/geometries/RoundedBoxGeometry.js";
import { EffectComposer } from "three/examples/jsm/postprocessing/EffectComposer.js";
import { RenderPass } from "three/examples/jsm/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/examples/jsm/postprocessing/UnrealBloomPass.js";
import { OutputPass } from "three/examples/jsm/postprocessing/OutputPass.js";
import { mergeGeometries, mergeVertices } from "three/examples/jsm/utils/BufferGeometryUtils.js";
window.THREE = Object.assign({}, THREE, {
  RoomEnvironment, RoundedBoxGeometry, EffectComposer, RenderPass, UnrealBloomPass, OutputPass, mergeGeometries, mergeVertices,
});
`,
);
await build({
  entryPoints: ["scratch/three-entry.js"],
  bundle: true,
  minify: true,
  format: "iife",
  outfile: "kit/three.bundle.js",
  target: "chrome120",
  logLevel: "info",
  // HyperFrames renders must be deterministic: Three's ids use a seeded PRNG instead of
  // Math.random, and its (unused) animation loop never names requestAnimationFrame.
  banner: {
    js: "window.__hmRandom=(function(){let s=0x9e3779b9;return function(){s=(s+0x6d2b79f5)>>>0;let t=s;t=Math.imul(t^(t>>>15),t|1);t^=t+Math.imul(t^(t>>>7),t|61);return((t^(t>>>14))>>>0)/4294967296;};})();",
  },
  define: { "Math.random": "window.__hmRandom" },
});
const out = "kit/three.bundle.js";
writeFileSync(out, readFileSync(out, "utf8").replace(/requestAnimationFrame/g, "hmNoFrameLoop").replace(/cancelAnimationFrame/g, "hmNoFrameStop"));
