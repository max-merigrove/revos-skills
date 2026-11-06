/* How-it's-made studio kit (window.HM).
 *
 * A dark product studio in Three.js, driven only by timeline time so HyperFrames can
 * seek any frame in any order. A reel registers shots with HM.shot(id, def); the
 * timing (when each shot starts, how it comes in) comes from window.REEL, written by
 * scripts/build-reel.mjs from the voiceover's word times.
 *
 * Shot definition:
 *   HM.shot("mix", {
 *     set: { floor: true, floorY: 0, key: 1, rim: 1, fog: 0.06, env: 0.35 },
 *     build(scene, kit) { ...add meshes...; return refs },
 *     camera: [{ p: 0, pos: [x,y,z], look: [x,y,z], fov: 32 }, { p: 1, ... }],
 *     update(refs, p, local, dur, t, shot) { ...move things... },   // p = 0..1 through the shot;
 *                                     // shot.marks.<name> = local seconds of a word (reel.json marks)
 *     anchors: { core: (refs) => refs.core.getWorldPosition(new THREE.Vector3()) },
 *   });
 */
(function () {
  const THREE = window.THREE;
  const HM = (window.HM = window.HM || {});
  const shotDefs = new Map();

  // ---------- maths ----------
  const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
  const lerp = (a, b, k) => a + (b - a) * k;
  const smooth = (k) => k * k * (3 - 2 * k);
  const ease = {
    linear: (k) => k,
    inOut: (k) => (k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2),
    out: (k) => 1 - Math.pow(1 - k, 3),
    in: (k) => k * k * k,
    outBack: (k) => 1 + 2.4 * Math.pow(k - 1, 3) + 1.4 * Math.pow(k - 1, 2),
    smooth,
  };
  // Progress through [a, b] of a parent progress p, eased.
  const seg = (p, a, b, fn = ease.inOut) => fn(clamp((p - a) / (b - a)));
  // Progress of a move that starts at a word mark (local seconds) and lasts d seconds.
  const after = (local, mark, d = 0.6, fn = ease.inOut) => fn(clamp((local - (mark ?? 0)) / d));
  function rng(seed) {
    let s = seed >>> 0;
    return function () {
      s = (s + 0x6d2b79f5) >>> 0;
      let t = s;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  Object.assign(HM, { clamp, lerp, smooth, ease, seg, after, rng });

  // ---------- textures ----------
  function canvasTex(w, h, draw, { repeat = [1, 1], srgb = true } = {}) {
    const c = document.createElement("canvas");
    c.width = w;
    c.height = h;
    draw(c.getContext("2d"), w, h);
    const t = new THREE.CanvasTexture(c);
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.repeat.set(repeat[0], repeat[1]);
    t.anisotropy = 8;
    if (srgb) t.colorSpace = THREE.SRGBColorSpace;
    return t;
  }
  // Fine noise, for roughness and bump maps.
  function noiseTex(seed = 1, { size = 256, lo = 90, hi = 200, repeat = [4, 4] } = {}) {
    const r = rng(seed);
    return canvasTex(
      size,
      size,
      (g, w, h) => {
        const img = g.createImageData(w, h);
        for (let i = 0; i < w * h; i++) {
          const v = lo + r() * (hi - lo);
          img.data.set([v, v, v, 255], i * 4);
        }
        g.putImageData(img, 0, 0);
      },
      { repeat, srgb: false },
    );
  }
  // Long-grain wood: stripes along x with wobble and a few darker late-wood lines.
  function woodTex(seed = 7, { base = "#b9824f", dark = "#8a5a32", size = 512, rings = 34 } = {}) {
    const r = rng(seed);
    return canvasTex(size, size, (g, w, h) => {
      g.fillStyle = base;
      g.fillRect(0, 0, w, h);
      for (let i = 0; i < rings; i++) {
        const y0 = r() * h;
        const amp = 2 + r() * 7;
        const freq = 0.004 + r() * 0.01;
        const ph = r() * 6.28;
        g.strokeStyle = dark;
        g.globalAlpha = 0.18 + r() * 0.35;
        g.lineWidth = 1 + r() * 3.5;
        g.beginPath();
        for (let x = 0; x <= w; x += 8) {
          const y = y0 + Math.sin(x * freq + ph) * amp;
          x === 0 ? g.moveTo(x, y) : g.lineTo(x, y);
        }
        g.stroke();
      }
      g.globalAlpha = 0.07;
      for (let i = 0; i < 4000; i++) {
        g.fillStyle = r() > 0.5 ? "#000" : "#fff";
        g.fillRect(r() * w, r() * h, 1 + r() * 6, 1);
      }
      g.globalAlpha = 1;
    });
  }
  // Soft round sprite for glows and sparks.
  let glowTexCache = null;
  function glowTex() {
    if (glowTexCache) return glowTexCache;
    glowTexCache = canvasTex(128, 128, (g, w, h) => {
      const grd = g.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, w / 2);
      grd.addColorStop(0, "rgba(255,255,255,1)");
      grd.addColorStop(0.18, "rgba(255,255,255,0.75)");
      grd.addColorStop(0.45, "rgba(255,255,255,0.18)");
      grd.addColorStop(1, "rgba(255,255,255,0)");
      g.fillStyle = grd;
      g.fillRect(0, 0, w, h);
    });
    return glowTexCache;
  }
  HM.tex = { canvas: canvasTex, noise: noiseTex, wood: woodTex, glow: glowTex };

  // ---------- materials ----------
  HM.mat = {
    wood: (o = {}) =>
      new THREE.MeshStandardMaterial({
        map: woodTex(o.seed ?? 7, o),
        roughness: o.roughness ?? 0.62,
        bumpMap: noiseTex((o.seed ?? 7) + 1, { repeat: [6, 6] }),
        bumpScale: 0.6,
      }),
    paint: (color, o = {}) =>
      new THREE.MeshPhysicalMaterial({
        color,
        roughness: o.roughness ?? 0.32,
        clearcoat: o.clearcoat ?? 0.8,
        clearcoatRoughness: 0.18,
      }),
    graphite: (o = {}) =>
      new THREE.MeshStandardMaterial({
        color: o.color ?? "#2b2b2e",
        metalness: 0.55,
        roughness: o.roughness ?? 0.42,
        roughnessMap: noiseTex(o.seed ?? 3, { repeat: [3, 3] }),
      }),
    metal: (o = {}) =>
      new THREE.MeshStandardMaterial({
        color: o.color ?? "#9a9da3",
        metalness: 1,
        roughness: o.roughness ?? 0.45,
        roughnessMap: noiseTex(o.seed ?? 5, { repeat: [1, 12], lo: 120, hi: 220 }),
      }),
    rubber: (color = "#d9867e", o = {}) =>
      new THREE.MeshStandardMaterial({ color, roughness: o.roughness ?? 0.85 }),
    clay: (color = "#8d8a86", o = {}) =>
      new THREE.MeshStandardMaterial({
        color,
        roughness: 0.92,
        bumpMap: noiseTex(o.seed ?? 11, { repeat: [5, 5] }),
        bumpScale: 1.2,
      }),
    matte: (color, o = {}) => new THREE.MeshStandardMaterial({ color, roughness: o.roughness ?? 0.7, metalness: o.metalness ?? 0 }),
    // Hot parts: emissive that the shot can turn up (mat.emissiveIntensity).
    hot: (color = "#3a2c22", glow = "#ff6a1a", o = {}) =>
      new THREE.MeshStandardMaterial({ color, roughness: o.roughness ?? 0.6, emissive: glow, emissiveIntensity: 0 }),
    glass: (o = {}) =>
      new THREE.MeshPhysicalMaterial({
        color: o.color ?? "#ffffff",
        roughness: 0.08,
        transmission: 0,
        transparent: true,
        opacity: o.opacity ?? 0.18,
        clearcoat: 1,
        depthWrite: false,
      }),
  };

  // ---------- parts ----------
  HM.glow = function (color = "#ffb347", size = 1, opacity = 1) {
    const s = new THREE.Sprite(
      new THREE.SpriteMaterial({
        map: glowTex(),
        color,
        transparent: true,
        opacity,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      }),
    );
    s.scale.setScalar(size);
    return s;
  };
  // Instanced spheres; set positions per frame with set(i, x, y, z, scale).
  HM.spheres = function (count, { radius = 0.05, material, segments = 20 } = {}) {
    const mesh = new THREE.InstancedMesh(new THREE.SphereGeometry(radius, segments, segments / 2), material, count);
    mesh.castShadow = true;
    const m = new THREE.Matrix4();
    const q = new THREE.Quaternion();
    const v = new THREE.Vector3();
    const sc = new THREE.Vector3();
    mesh.place = function (i, x, y, z, s = 1) {
      v.set(x, y, z);
      sc.setScalar(Math.max(1e-4, s));
      m.compose(v, q, sc);
      mesh.setMatrixAt(i, m);
    };
    mesh.done = () => {
      mesh.instanceMatrix.needsUpdate = true;
    };
    return mesh;
  };
  HM.hexPrism = (radius, length, o = {}) => {
    const g = new THREE.CylinderGeometry(radius, radius, length, 6, o.heightSegments ?? 1);
    g.rotateY(Math.PI / 6);
    return g;
  };
  HM.shade = (obj, cast = true, receive = true) => {
    obj.traverse((o) => {
      if (o.isMesh) {
        o.castShadow = cast;
        o.receiveShadow = receive;
      }
    });
    return obj;
  };

  // ---------- the set ----------
  function makeSet(renderer, pmrem, o = {}) {
    const scene = new THREE.Scene();
    const bg = new THREE.Color(o.bg ?? "#0c0b0a");
    scene.background = bg;
    if (o.fog !== 0) scene.fog = new THREE.FogExp2(bg, o.fog ?? 0.045);
    scene.environment = pmrem.envTex;
    scene.environmentIntensity = o.env ?? 0.35;

    const key = new THREE.SpotLight(o.keyColor ?? "#ffe2c2", 55 * (o.key ?? 1), 0, Math.PI / 5, 0.65, 1.6);
    key.position.set(...(o.keyPos ?? [-4, 7, 5]));
    key.target.position.set(...(o.keyTarget ?? [0, 0, 0]));
    key.castShadow = true;
    key.shadow.mapSize.set(2048, 2048);
    key.shadow.bias = -0.0004;
    key.shadow.normalBias = 0.02;
    key.shadow.radius = 6;
    scene.add(key, key.target);

    const rim = new THREE.DirectionalLight(o.rimColor ?? "#a9bcff", 1.6 * (o.rim ?? 1));
    rim.position.set(...(o.rimPos ?? [5, 3, -6]));
    scene.add(rim);
    scene.add(new THREE.HemisphereLight("#2a2622", "#050404", 0.6 * (o.fill ?? 1)));

    if (o.floor !== false) {
      const fade = canvasTex(
        512,
        512,
        (g, w, h) => {
          const grd = g.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, w / 2);
          grd.addColorStop(0, "#ffffff");
          grd.addColorStop(0.3, "#8a8a8a");
          grd.addColorStop(0.75, "#101010");
          grd.addColorStop(1, "#000000");
          g.fillStyle = grd;
          g.fillRect(0, 0, w, h);
        },
        { srgb: false },
      );
      fade.wrapS = fade.wrapT = THREE.ClampToEdgeWrapping;
      const floor = new THREE.Mesh(
        new THREE.PlaneGeometry(o.floorSize ?? 9, o.floorSize ?? 9),
        // fade by alpha, not colour: grazing reflections ignore the colour map and leave a horizon
        new THREE.MeshStandardMaterial({
          color: o.floorColor ?? "#1b1815",
          roughness: 0.78,
          metalness: 0,
          alphaMap: fade,
          transparent: true,
          depthWrite: false,
          roughnessMap: noiseTex(99, { repeat: [10, 10] }),
        }),
      );
      floor.rotation.x = -Math.PI / 2;
      floor.position.y = o.floorY ?? 0;
      floor.receiveShadow = true;
      scene.add(floor);
      scene.userData.floor = floor;
    }
    scene.userData.key = key;
    scene.userData.rim = rim;
    return scene;
  }

  // ---------- camera paths ----------
  function cameraAt(keys, p, cam) {
    let a = keys[0];
    let b = keys[keys.length - 1];
    for (let i = 0; i < keys.length - 1; i++) {
      if (p >= keys[i].p && p <= keys[i + 1].p) {
        a = keys[i];
        b = keys[i + 1];
        break;
      }
    }
    if (p < keys[0].p) b = a;
    const span = b.p - a.p || 1;
    const k = (b.ease ? ease[b.ease] : ease.inOut)(clamp((p - a.p) / span));
    const v = (x, y) => [lerp(x[0], y[0], k), lerp(x[1], y[1], k), lerp(x[2], y[2], k)];
    cam.position.set(...v(a.pos, b.pos));
    const look = v(a.look ?? [0, 0, 0], b.look ?? a.look ?? [0, 0, 0]);
    cam.up.set(0, 1, 0);
    cam.lookAt(...look);
    if (a.roll || b.roll) cam.rotateZ(lerp(a.roll ?? 0, b.roll ?? 0, k));
    const fov = lerp(a.fov ?? 32, b.fov ?? a.fov ?? 32, k);
    if (cam.fov !== fov) {
      cam.fov = fov;
      cam.updateProjectionMatrix();
    }
  }

  // ---------- final pass: dissolve + vignette + grain ----------
  const finalShader = {
    uniforms: {
      tA: { value: null },
      tB: { value: null },
      mixK: { value: 0 },
      dim: { value: 1 },
      vignette: { value: 0.55 },
      grain: { value: 0.035 },
      seed: { value: 0 },
      aspect: { value: 1080 / 1920 },
    },
    vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }`,
    fragmentShader: `
      uniform sampler2D tA; uniform sampler2D tB; uniform float mixK; uniform float dim;
      uniform float vignette; uniform float grain; uniform float seed; uniform float aspect;
      varying vec2 vUv;
      float hash(vec2 p){ p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32 + seed); return fract(p.x * p.y); }
      void main(){
        vec3 a = texture2D(tA, vUv).rgb;
        vec3 b = texture2D(tB, vUv).rgb;
        vec3 c = mix(a, b, mixK);
        vec2 q = (vUv - 0.5) * vec2(aspect, 1.0) * 1.6;
        float v = 1.0 - vignette * smoothstep(0.25, 1.05, dot(q, q));
        c *= v * dim;
        c += (hash(vUv * vec2(1080.0, 1920.0)) - 0.5) * grain;
        gl_FragColor = vec4(clamp(c, 0.0, 1.0), 1.0);
      }`,
  };

  // ---------- the studio ----------
  HM.shot = (id, def) => shotDefs.set(id, def);

  HM.createStudio = function ({ canvas, width = 1080, height = 1920, bloom = {}, look = {} }) {
    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true, powerPreference: "high-performance" });
    renderer.setPixelRatio(1);
    renderer.setSize(width, height, false);
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = look.exposure ?? 1.0;
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.localClippingEnabled = true;

    const pmremGen = new THREE.PMREMGenerator(renderer);
    const pmrem = { envTex: pmremGen.fromScene(new THREE.RoomEnvironment(), 0.04).texture };

    const reel = window.REEL || { duration: 10, shots: [] };
    const shots = reel.shots.map((s) => {
      const def = shotDefs.get(s.id);
      if (!def) throw new Error(`HM: no shot registered for "${s.id}"`);
      const scene = makeSet(renderer, pmrem, def.set || {});
      const camera = new THREE.PerspectiveCamera(32, width / height, 0.01, 200);
      const refs = def.build ? def.build(scene, HM, s) || {} : {};
      return { ...s, def, scene, camera, refs };
    });

    function makeChain() {
      const rt = new THREE.WebGLRenderTarget(width, height, { type: THREE.HalfFloatType, samples: 4 });
      const composer = new THREE.EffectComposer(renderer, rt);
      composer.renderToScreen = false;
      const pass = new THREE.RenderPass(new THREE.Scene(), new THREE.PerspectiveCamera());
      composer.addPass(pass);
      const bloomPass = new THREE.UnrealBloomPass(new THREE.Vector2(width / 2, height / 2), bloom.strength ?? 0.55, bloom.radius ?? 0.5, bloom.threshold ?? 0.82);
      composer.addPass(bloomPass);
      composer.addPass(new THREE.OutputPass());
      return { composer, pass, bloomPass };
    }
    const chains = [makeChain(), makeChain()];
    const quadScene = new THREE.Scene();
    const quadMat = new THREE.ShaderMaterial({ ...finalShader, uniforms: THREE.UniformsUtils.clone(finalShader.uniforms), depthTest: false, depthWrite: false });
    quadMat.uniforms.vignette.value = look.vignette ?? 0.55;
    quadMat.uniforms.grain.value = look.grain ?? 0.035;
    quadMat.uniforms.aspect.value = width / height;
    quadScene.add(new THREE.Mesh(new THREE.PlaneGeometry(2, 2), quadMat));
    const quadCam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);

    function pose(shot, t) {
      const dur = shot.end - shot.start;
      const local = t - shot.start;
      const p = local / dur;
      cameraAt(shot.def.camera || [{ p: 0, pos: [0, 1, 6], look: [0, 0.5, 0] }], clamp(p, -0.2, 1.2), shot.camera);
      if (shot.def.update) shot.def.update(shot.refs, p, local, dur, t, shot);
      shot.camera.updateMatrixWorld();
    }
    function draw(chain, shot) {
      chain.pass.scene = shot.scene;
      chain.pass.camera = shot.camera;
      if (shot.def.bloom) Object.assign(chain.bloomPass, shot.def.bloom);
      else Object.assign(chain.bloomPass, { strength: bloom.strength ?? 0.55, radius: bloom.radius ?? 0.5, threshold: bloom.threshold ?? 0.82 });
      chain.composer.render();
      return chain.composer.readBuffer.texture;
    }

    // Which shot(s) show at t, and the dissolve weight.
    function active(t) {
      let i = shots.findIndex((s) => t >= s.start && t < s.end);
      if (i < 0) i = t < (shots[0]?.start ?? 0) ? 0 : shots.length - 1;
      const cur = shots[i];
      const next = shots[i + 1];
      if (next && next.in === "dissolve") {
        const d = next.inDur ?? 0.45;
        if (t >= next.start - d) return { a: cur, b: next, k: smooth(clamp((t - (next.start - d)) / d)) };
      }
      return { a: cur, b: null, k: 0 };
    }

    // Callouts: DOM elements tracked to 3D anchors (written by build-reel into world.html).
    const v3 = new THREE.Vector3();
    function anchorScreen(shot, name) {
      const fn = shot.def.anchors && shot.def.anchors[name];
      if (fn) v3.copy(fn(shot.refs, v3));
      else {
        const obj = shot.scene.getObjectByName(name);
        if (!obj) return null;
        obj.getWorldPosition(v3);
      }
      v3.project(shot.camera);
      return { x: (v3.x * 0.5 + 0.5) * width, y: (-v3.y * 0.5 + 0.5) * height };
    }
    const callouts = [...document.querySelectorAll(".hm-callout, .hm-stat")].map((el) => ({
      el,
      inner: el.firstElementChild,
      shot: el.dataset.shot,
      anchor: el.dataset.anchor,
      start: parseFloat(el.dataset.start),
      dur: parseFloat(el.dataset.duration),
      from: parseFloat(el.dataset.countFrom ?? "NaN"),
      to: parseFloat(el.dataset.countTo ?? "NaN"),
      decimals: parseInt(el.dataset.decimals ?? "0", 10),
      num: el.querySelector(".hm-num"),
      fixed: el.dataset.x ? { x: parseFloat(el.dataset.x), y: parseFloat(el.dataset.y) } : null,
    }));
    const fmt = (n, d) => n.toLocaleString("en-GB", { minimumFractionDigits: d, maximumFractionDigits: d });

    function placeCallouts(t, shown) {
      for (const c of callouts) {
        const local = t - c.start;
        if (local < 0 || local >= c.dur) continue;
        const shot = shots.find((s) => s.id === c.shot) || shown;
        let pt = c.fixed;
        if (c.anchor) pt = anchorScreen(shot, c.anchor) || pt;
        if (pt) c.el.style.transform = `translate(${pt.x.toFixed(1)}px, ${pt.y.toFixed(1)}px)`;
        // reveal: dot pops, leader draws, text rises; fade before the end
        const inK = clamp(local / 0.45);
        const outK = clamp((c.dur - local) / 0.2);
        c.inner.style.setProperty("--k", (ease.out(inK) * outK).toFixed(3));
        c.inner.style.setProperty("--draw", ease.inOut(clamp(local / 0.3)).toFixed(3));
        c.inner.style.setProperty("--text", ease.out(clamp((local - 0.15) / 0.3)).toFixed(3));
        if (c.num && !Number.isNaN(c.to)) {
          const from = Number.isNaN(c.from) ? 0 : c.from;
          const k = ease.out(clamp((local - 0.1) / Math.min(1.4, c.dur * 0.6)));
          c.num.textContent = fmt(lerp(from, c.to, k), c.decimals);
        }
      }
    }

    function render(t) {
      const { a, b, k } = active(t);
      pose(a, t);
      const tA = draw(chains[0], a);
      let tB = tA;
      if (b) {
        pose(b, t);
        tB = draw(chains[1], b);
      }
      const u = quadMat.uniforms;
      u.tA.value = tA;
      u.tB.value = tB;
      u.mixK.value = b ? k : 0;
      // a fade from black at the head and to black at the tail, if asked
      const fi = reel.fadeIn ?? 0;
      const fo = reel.fadeOut ?? 0;
      u.dim.value = Math.min(fi ? clamp(t / fi) : 1, fo ? clamp((reel.duration - t) / fo) : 1);
      u.seed.value = Math.floor(t * 30) % 97;
      renderer.setRenderTarget(null);
      renderer.render(quadScene, quadCam);
      placeCallouts(t, b && k > 0.5 ? b : a);
    }

    return { renderer, shots, render };
  };

  // Boot inside a HyperFrames scene: one canvas, drawn from hf-seek time.
  HM.boot = function (opts) {
    window.__hf = window.__hf || {};
    window.__hf.buildReady = window.__hf.buildReady || {};
    let studio = null;
    let last = 0;
    const ready = (document.fonts ? document.fonts.ready : Promise.resolve()).then(() => {
      studio = HM.createStudio(opts);
      studio.render(last);
    });
    window.__hf.buildReady["hm-world"] = ready;
    window.addEventListener("hf-seek", (e) => {
      last = e.detail.time;
      if (studio) studio.render(last);
      else e.detail.waitUntil(ready.then(() => studio.render(last)));
    });
    return ready;
  };
})();
