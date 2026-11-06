/* How a pencil is made: the 3D shots. Units: 1 = 10 cm. Timing comes from reel.json marks. */
(function () {
  const THREE = window.THREE;
  const { after, seg, ease, lerp, clamp, rng } = HM;

  // ---------- shared materials ----------
  const M = {
    yellow: () => HM.mat.paint("#f2b10a", { roughness: 0.3 }),
    cedar: (seed = 7) => HM.mat.wood({ seed, base: "#c98d58", dark: "#94603a" }),
    lead: () => HM.mat.graphite({ color: "#3d3d42", roughness: 0.38 }),
    dough: () => HM.mat.clay("#3f3e42", { seed: 4 }),
    ferrule: () => HM.mat.metal({ color: "#d8cfbd", roughness: 0.35 }),
    eraser: () => HM.mat.rubber("#e5838a"),
    paper: () => HM.mat.matte("#7d776c", { roughness: 0.95 }),
  };

  // Lumpy sphere (dough, rock): seeded displacement along the normal.
  function lump(radius, amp, seed, detail = 5) {
    const ico = new THREE.IcosahedronGeometry(radius, detail);
    ico.deleteAttribute("normal");
    ico.deleteAttribute("uv");
    const g = THREE.mergeVertices(ico); // shared vertices, so the normals come out smooth
    const r = rng(seed);
    const dirs = Array.from({ length: 7 }, () => new THREE.Vector3(r() - 0.5, r() - 0.5, r() - 0.5).normalize().multiplyScalar(2 + r() * 5));
    const ph = dirs.map(() => r() * 6.28);
    const p = g.attributes.position;
    const v = new THREE.Vector3();
    for (let i = 0; i < p.count; i++) {
      v.fromBufferAttribute(p, i);
      const n = v.clone().normalize();
      let d = 0;
      dirs.forEach((dir, k) => (d += Math.sin(n.dot(dir) + ph[k]) / dirs.length));
      v.copy(n.multiplyScalar(radius * (1 + amp * d)));
      p.setXYZ(i, v.x, v.y, v.z);
    }
    g.computeVertexNormals();
    return g;
  }

  // A pencil along +y: body from 0 to L, sharpened cone above, ferrule and eraser below.
  function pencil(o = {}) {
    const g = new THREE.Group();
    const L = o.length ?? 1.6;
    const R = 0.04;
    const body = new THREE.Mesh(HM.hexPrism(R, L), o.bodyMat ?? M.yellow());
    body.position.y = L / 2;
    const core = new THREE.Mesh(new THREE.CylinderGeometry(0.011, 0.011, L + 0.004, 20), o.coreMat ?? M.lead());
    core.position.y = L / 2;
    g.add(body, core);
    const refs = { group: g, body, core, L };
    if (o.sharp !== false) {
      const cone = new THREE.Mesh(new THREE.CylinderGeometry(0.012, R * 0.93, 0.19, 36), o.coneMat ?? M.cedar(9));
      cone.position.y = L + 0.095;
      const tip = new THREE.Mesh(new THREE.CylinderGeometry(0.0015, 0.012, 0.055, 24), o.coreMat ?? M.lead());
      tip.position.y = L + 0.19 + 0.0275;
      g.add(cone, tip);
      Object.assign(refs, { cone, tip });
    }
    if (o.ferrule !== false) {
      const ferrule = new THREE.Group();
      const band = new THREE.Mesh(new THREE.CylinderGeometry(R * 1.04, R * 1.04, 0.1, 36), M.ferrule());
      ferrule.add(band);
      [-0.03, 0.03].forEach((y) => {
        const ring = new THREE.Mesh(new THREE.TorusGeometry(R * 1.05, 0.004, 8, 36), M.ferrule());
        ring.rotation.x = Math.PI / 2;
        ring.position.y = y;
        ferrule.add(ring);
      });
      ferrule.position.y = -0.04;
      const eraser = new THREE.Mesh(new THREE.CylinderGeometry(R * 0.97, R * 0.97, 0.1, 36), M.eraser());
      eraser.position.y = -0.13;
      g.add(ferrule, eraser);
      Object.assign(refs, { ferrule, eraser });
    }
    HM.shade(g);
    return refs;
  }

  // The hero pencil, centred on its middle and tilted, spinning about its own length.
  function hero(scene, y = 0.92, tilt = 0.45) {
    const p = pencil();
    const tiltG = new THREE.Group();
    const spin = new THREE.Group();
    p.group.position.y = -0.83;
    spin.add(p.group);
    tiltG.add(spin);
    tiltG.position.y = y;
    tiltG.rotation.set(0.12, 0, tilt);
    scene.add(tiltG);
    return { ...p, spin, tiltG };
  }

  // A grooved cedar slat, length along x. Grooves are cut by shrinking the "fill" strips.
  const SLAT = { len: 1.84, width: 0.7, base: 0.03, ridge: 0.026, n: 9, groove: 0.03 };
  const grooveZ = (k) => -SLAT.width / 2 + (SLAT.width / SLAT.n) * (k + 0.5);
  function slat(seed = 7, cut = true) {
    const g = new THREE.Group();
    const mat = M.cedar(seed);
    const { len, width, base, ridge, n, groove } = SLAT;
    const b = new THREE.Mesh(new THREE.BoxGeometry(len, base, width), mat);
    b.position.y = base / 2;
    g.add(b);
    const edges = [-width / 2];
    for (let k = 0; k < n; k++) edges.push(grooveZ(k) - groove / 2, grooveZ(k) + groove / 2);
    edges.push(width / 2);
    for (let i = 0; i < edges.length; i += 2) {
      const w = edges[i + 1] - edges[i];
      const r = new THREE.Mesh(new THREE.BoxGeometry(len, ridge, w), mat);
      r.position.set(0, base + ridge / 2, (edges[i] + edges[i + 1]) / 2);
      g.add(r);
    }
    const fills = [];
    for (let k = 0; k < n; k++) {
      const f = new THREE.Mesh(new THREE.BoxGeometry(len, ridge, groove), mat);
      f.position.set(0, base + ridge / 2, grooveZ(k));
      f.visible = !cut;
      g.add(f);
      fills.push(f);
    }
    HM.shade(g);
    return { group: g, fills, mat };
  }
  // Fill strips: the uncut wood runs from slat x to the +x end; it shrinks as the cutter passes.
  function cutTo(fills, x) {
    const L = SLAT.len;
    const remain = clamp((L / 2 - x) / L, 0.0001, 1);
    for (const f of fills) {
      f.visible = remain > 0.001;
      f.scale.x = remain;
      f.position.x = L / 2 - (L * remain) / 2;
    }
  }
  function leads(n = SLAT.n) {
    const out = [];
    for (let k = 0; k < n; k++) {
      const m = new THREE.Mesh(new THREE.CylinderGeometry(0.011, 0.011, SLAT.len - 0.02, 16), M.lead());
      m.rotation.z = Math.PI / 2;
      m.castShadow = true;
      out.push(m);
    }
    return out;
  }

  // ============ 1. hook: a pencil, then an X-ray of what's inside ============
  HM.shot("hook", {
    set: { keyPos: [-3, 6, 4], floorY: -0.2, fog: 0.05 },
    build(scene) {
      const p = hero(scene);
      [p.body.material, p.cone.material].forEach((m) => (m.transparent = true));
      const glint = HM.glow("#fff3dc", 0.12, 0);
      scene.add(glint);
      return { ...p, glint };
    },
    camera: [
      { p: 0, pos: [0.25, 1.3, 4.5], look: [0, 1.1, 0], fov: 34 },
      { p: 0.6, pos: [0.1, 1.25, 4.0], look: [0, 1.1, 0], fov: 34 },
      { p: 1, pos: [-0.05, 1.2, 3.5], look: [0, 1.1, 0], fov: 33 },
    ],
    update(r, p, local, dur, t, shot) {
      r.spin.rotation.y = 0.6 + local * 0.5;
      const x = after(local, shot.marks.xray, 0.6);
      r.body.material.opacity = lerp(1, 0.13, x);
      r.cone.material.opacity = lerp(1, 0.2, x);
      r.body.material.depthWrite = r.cone.material.depthWrite = x < 0.5;
      r.core.material.emissive.set("#3b3f4a");
      r.core.material.emissiveIntensity = x;
      r.tip.getWorldPosition(r.glint.position);
      r.glint.material.opacity = 0.7 * after(local, shot.marks.lead, 0.3) * (1 - x * 0.5);
    },
    anchors: {
      tip: (r, v) => r.tip.localToWorld(v.set(0, 0.02, 0)),
      core: (r, v) => r.core.localToWorld(v.set(0, -0.15, 0)),
    },
  });

  // ============ 2. mix: graphite and clay swirl into grey dough ============
  HM.shot("mix", {
    set: { keyPos: [-2.5, 5, 3], fog: 0.06, floorColor: "#1d1a17" },
    build(scene) {
      const N = 650;
      const r = rng(21);
      const make = (mat, cx, seed) => {
        const m = HM.spheres(N, { radius: 0.019, material: mat, segments: 12 });
        const rr = rng(seed);
        const heap = [];
        const ball = [];
        for (let i = 0; i < N; i++) {
          const a = rr() * 6.283;
          const rad = Math.sqrt(rr()) * 0.17;
          heap.push([cx + Math.cos(a) * rad, 0.019 + (0.17 - rad) * 0.85 * rr(), Math.sin(a) * rad]);
          const u = rr() * 6.283;
          const w = Math.acos(2 * rr() - 1);
          const br = Math.cbrt(rr()) * 0.2;
          ball.push([Math.sin(w) * Math.cos(u) * br, 0.22 + Math.cos(w) * br, Math.sin(w) * Math.sin(u) * br]);
        }
        scene.add(m);
        return { m, heap, ball, delay: Array.from({ length: N }, () => r() * 0.5) };
      };
      const gr = make(HM.mat.graphite({ color: "#26262a", roughness: 0.3 }), -0.24, 3);
      const cl = make(HM.mat.clay("#8f8478", { seed: 8 }), 0.24, 5);
      const dough = new THREE.Mesh(lump(0.215, 0.06, 13), M.dough());
      dough.position.y = 0.215;
      dough.castShadow = true;
      scene.add(dough);
      return { gr, cl, dough };
    },
    camera: [
      { p: 0, pos: [0, 1.05, 1.95], look: [0, 0.14, 0], fov: 34 },
      { p: 1, pos: [0.25, 0.8, 1.55], look: [0, 0.18, 0], fov: 34 },
    ],
    update(r, p, local, dur, t, shot) {
      const doughK = after(local, shot.marks.dough, 0.5);
      for (const set of [r.gr, r.cl]) {
        for (let i = 0; i < set.heap.length; i++) {
          const k = after(local, shot.marks.swirl + set.delay[i], 1.3);
          const a = set.heap[i];
          const b = set.ball[i];
          const ang = Math.sin(k * Math.PI) * 2.4;
          let x = lerp(a[0], b[0], k);
          let z = lerp(a[2], b[2], k);
          const y = lerp(a[1], b[1], k) + Math.sin(k * Math.PI) * 0.18;
          const c = Math.cos(ang);
          const s = Math.sin(ang);
          [x, z] = [x * c - z * s, x * s + z * c];
          set.m.place(i, x, y, z, 1 - doughK);
        }
        set.m.done();
      }
      r.dough.scale.setScalar(Math.max(0.001, ease.outBack(doughK)));
      r.dough.rotation.y = local * 0.3;
    },
    anchors: {
      gpile: (r, v) => v.set(-0.24, 0.16, 0),
      cpile: (r, v) => v.set(0.24, 0.16, 0),
    },
  });

  // ============ 3. grade: more clay is harder, more graphite is darker ============
  const GRADES = ["#8b8b90", "#6a6a6f", "#4b4b50", "#323236", "#1c1c1f"];
  const STROKES = ["#b9b8b6", "#8f8e8d", "#5f5f60", "#3a3a3c", "#1d1d1f"];
  HM.shot("grade", {
    set: { keyPos: [-2, 5, 4], fog: 0.05 },
    build(scene) {
      const paper = new THREE.Mesh(new THREE.PlaneGeometry(1.6, 1.2), M.paper());
      paper.rotation.x = -Math.PI / 2;
      paper.position.y = 0.002;
      paper.receiveShadow = true;
      scene.add(paper);
      const cores = [];
      const strokes = [];
      GRADES.forEach((c, i) => {
        const x = -0.3 + i * 0.15;
        const m = new THREE.Mesh(new THREE.CylinderGeometry(0.032, 0.032, 0.62, 28), HM.mat.graphite({ color: c, roughness: 0.3 + i * 0.05 }));
        m.position.set(x, 0.31, -0.18);
        m.castShadow = true;
        scene.add(m);
        cores.push(m);
        const s = new THREE.Mesh(new THREE.BoxGeometry(0.07, 0.003, 1), HM.mat.matte(STROKES[i], { roughness: 0.6, metalness: 0.2 }));
        s.position.set(x, 0.004, -0.1);
        scene.add(s);
        strokes.push(s);
      });
      return { cores, strokes };
    },
    camera: [
      { p: 0, pos: [0, 1.2, 2.8], look: [0, 0.24, -0.1], fov: 34 },
      { p: 1, pos: [0.1, 1.0, 2.45], look: [0, 0.26, -0.1], fov: 34 },
    ],
    update(r, p, local, dur, t, shot) {
      r.strokes.forEach((s, i) => {
        const k = after(local, 0.15 + i * 0.12, 0.7);
        const len = Math.max(0.001, k * 0.55);
        s.scale.z = len;
        s.position.z = -0.12 + len / 2;
      });
      const hb = after(local, shot.marks.hb, 0.4);
      r.cores.forEach((c, i) => (c.position.y = 0.31 + (i === 2 ? hb * 0.06 : 0)));
    },
    anchors: {
      c0: (r, v) => r.cores[0].localToWorld(v.set(0, 0.31, 0)),
      c2: (r, v) => r.cores[2].localToWorld(v.set(0, 0.31, 0)),
      c4: (r, v) => r.cores[4].localToWorld(v.set(0, 0.31, 0)),
    },
  });

  // ============ 4. extrude: dough pushed through tiny holes, cut to length ============
  const HOLES = [-0.26, -0.13, 0, 0.13, 0.26];
  HM.shot("extrude", {
    set: { floor: false, keyPos: [-2, 4, 3], keyTarget: [0, 1, 0], fog: 0.07 },
    build(scene) {
      const die = new THREE.Mesh(new THREE.RoundedBoxGeometry(0.78, 0.22, 0.36, 4, 0.02), HM.mat.metal({ color: "#8e9197", roughness: 0.4 }));
      die.position.y = 1.5;
      die.castShadow = true;
      scene.add(die);
      const hopper = new THREE.Mesh(lump(0.3, 0.05, 31), M.dough());
      hopper.scale.set(1.2, 0.45, 0.55);
      hopper.position.y = 1.68;
      scene.add(hopper);
      const rods = [];
      const drops = [];
      HOLES.forEach((x) => {
        const ring = new THREE.Mesh(new THREE.TorusGeometry(0.03, 0.006, 8, 24), HM.mat.metal({ color: "#5d6066" }));
        ring.rotation.x = Math.PI / 2;
        ring.position.set(x, 1.389, 0);
        scene.add(ring);
        const geo = new THREE.CylinderGeometry(0.024, 0.024, 1, 20);
        geo.translate(0, -0.5, 0);
        const rod = new THREE.Mesh(geo, M.dough());
        rod.position.set(x, 1.389, 0);
        rod.castShadow = true;
        scene.add(rod);
        rods.push(rod);
        const drop = new THREE.Mesh(geo, M.dough());
        scene.add(drop);
        drops.push(drop);
      });
      const blade = new THREE.Mesh(new THREE.BoxGeometry(0.9, 0.008, 0.36), HM.mat.metal({ color: "#c9ccd2", roughness: 0.25 }));
      scene.add(blade);
      return { die, rods, drops, blade };
    },
    camera: [
      { p: 0, pos: [0.25, 1.05, 2.3], look: [0, 1.05, 0], fov: 34 },
      { p: 1, pos: [-0.15, 0.95, 1.95], look: [0, 1.0, 0], fov: 34 },
    ],
    update(r, p, local, dur, t, shot) {
      const speed = 0.22;
      const tc = shot.marks.cut + 0.1;
      const grown = (u) => Math.max(0.001, speed * Math.max(0, u));
      const start = shot.marks.push - 0.2;
      const lenAtCut = grown(tc - start);
      r.rods.forEach((rod, i) => {
        const wob = Math.sin(local * 3 + i) * 0.01;
        if (local < tc) {
          rod.scale.y = grown(local - start);
          r.drops[i].visible = false;
        } else {
          rod.scale.y = 0.12 + grown(local - tc);
          const fall = local - tc;
          const d = r.drops[i];
          d.visible = true;
          d.scale.y = lenAtCut - 0.12;
          d.position.set(HOLES[i] + wob, 1.389 - 0.12 - 0.5 * 4.5 * fall * fall, 0);
          d.rotation.z = fall * (i % 2 ? 0.12 : -0.1);
        }
        rod.position.x = HOLES[i] + wob * 0.3;
      });
      const b = after(local, shot.marks.cut - 0.1, 0.35, ease.inOut);
      r.blade.position.set(0, 1.389 - 0.12, lerp(0.7, -0.7, b));
      r.blade.visible = b > 0 && b < 1;
    },
    anchors: { die: (r, v) => v.set(0.3, 1.5, 0.18) },
  });

  // ============ 5. kiln: rods baked at about 1,000 °C ============
  HM.shot("kiln", {
    set: { keyPos: [-2, 5, 3], fog: 0.06, key: 0.7, floorColor: "#151210" },
    bloom: { strength: 0.6, radius: 0.55, threshold: 0.8 },
    build(scene) {
      const tray = new THREE.Mesh(new THREE.BoxGeometry(1.1, 0.03, 0.8), HM.mat.metal({ color: "#3e3e42", roughness: 0.6 }));
      tray.position.y = 0.05;
      scene.add(HM.shade(tray));
      const hot = HM.mat.hot("#2c2c30", "#ff3a08", { roughness: 0.45 });
      const r = rng(41);
      const rods = [];
      for (let i = 0; i < 14; i++) {
        // rods point at the lens, side by side, so each one reads on its own
        const m = new THREE.Mesh(new THREE.CylinderGeometry(0.017, 0.017, 0.7, 16), hot);
        m.rotation.x = Math.PI / 2;
        m.rotation.y = (r() - 0.5) * 0.05;
        m.position.set(-0.4 + i * 0.0615, 0.082, (r() - 0.5) * 0.06);
        m.castShadow = true;
        scene.add(m);
        rods.push(m);
      }
      const coilMat = HM.mat.hot("#3a2a20", "#ff4a10");
      const coils = [];
      for (let i = 0; i < 7; i++) {
        const c = new THREE.Mesh(new THREE.TorusGeometry(0.09, 0.012, 10, 36), coilMat);
        c.position.set(-0.6 + i * 0.2, 0.55, -0.75);
        scene.add(c);
        coils.push(c);
      }
      const wall = new THREE.Mesh(new THREE.BoxGeometry(2.4, 1.6, 0.05), HM.mat.matte("#2a211b", { roughness: 0.95 }));
      wall.position.set(0, 0.8, -0.85);
      scene.add(wall);
      const glows = coils.map((c) => {
        const g = HM.glow("#ff7a2a", 0.35, 0);
        g.position.copy(c.position).add(new THREE.Vector3(0, 0, 0.05));
        scene.add(g);
        return g;
      });
      const heat = new THREE.PointLight("#ff6a20", 0, 3, 1.5);
      heat.position.set(0, 0.5, -0.4);
      scene.add(heat);
      return { tray, hot, coilMat, glows, heat };
    },
    camera: [
      { p: 0, pos: [0.0, 1.5, 2.3], look: [0, 0.25, -0.25], fov: 34 },
      { p: 1, pos: [0.2, 1.15, 1.95], look: [0, 0.22, -0.25], fov: 34 },
    ],
    update(r, p, local, dur, t, shot) {
      const k = after(local, shot.marks.heat, 2.2, ease.inOut);
      r.coilMat.emissiveIntensity = 0.3 + 1.4 * k;
      r.hot.emissiveIntensity = 0.85 * after(local, shot.marks.heat + 0.6, 2.2);
      r.hot.emissive.setRGB(1, lerp(0.12, 0.26, k), lerp(0.01, 0.04, k));
      r.glows.forEach((g) => (g.material.opacity = 0.35 * k));
      r.heat.intensity = 1.2 * k;
    },
    anchors: { tray: (r, v) => v.set(0.1, 0.09, 0.05) },
  });

  // ============ 6. slat: cedar sliced into slats, nine grooves cut ============
  HM.shot("slat", {
    set: { keyPos: [-3, 6, 3], fog: 0.045 },
    build(scene) {
      const block = new THREE.Mesh(new THREE.BoxGeometry(SLAT.len, 0.5, SLAT.width), M.cedar(17));
      block.rotation.y = Math.PI / 2;
      block.position.set(0, 0.25, -1.95);
      scene.add(HM.shade(block));
      const s = slat(7, false);
      s.group.rotation.y = Math.PI / 2;
      scene.add(s.group);
      const cutter = new THREE.Group();
      const discMat = HM.mat.metal({ color: "#c8ccd4", roughness: 0.5 });
      for (let k = 0; k < SLAT.n; k++) {
        const d = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.08, 0.022, 40), discMat);
        d.rotation.x = Math.PI / 2;
        d.rotation.z = Math.PI / 2;
        d.position.x = grooveZ(k);
        cutter.add(d);
      }
      const axle = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.02, 0.95, 16), discMat);
      axle.rotation.z = Math.PI / 2;
      cutter.add(axle);
      scene.add(HM.shade(cutter));
      const dust = HM.spheres(160, { radius: 0.006, material: HM.mat.matte("#d9a66f"), segments: 6 });
      scene.add(dust);
      return { s, cutter, dust, block, dr: rng(55) };
    },
    camera: [
      { p: 0, pos: [1.15, 1.55, 1.75], look: [0, 0.05, -0.15], fov: 34 },
      { p: 1, pos: [0.8, 1.2, 1.45], look: [0, 0.05, 0.05], fov: 34 },
    ],
    update(r, p, local, dur, t, shot) {
      const sl = after(local, shot.marks.slice, 0.9, ease.out);
      r.s.group.position.set(0, lerp(0.44, 0, sl), lerp(-1.95, 0, sl));
      // cutter travels along the slat (z, since the slat is turned) from far to near
      const c = after(local, shot.marks.cut, 1.9, ease.inOut);
      // near end first, then away from the lens, so the gang never fills the frame
      const along = lerp(SLAT.len / 2 + 0.15, -SLAT.len / 2 - 0.15, c);
      r.cutter.position.set(0, SLAT.base + 0.07, along);
      r.cutter.visible = sl > 0.98 && c > 0 && c < 1;
      r.cutter.rotation.x = -local * 30;
      // the slat is turned, so world z = -(slat x): uncut wood is slat x > -along
      cutTo(r.s.fills, -along);
      // sawdust thrown up behind the cutter, a pure function of time
      const on = c > 0 && c < 1;
      for (let i = 0; i < 160; i++) {
        const born = (i / 160) * 1.9;
        const age = local - shot.marks.cut - born;
        if (!on || age < 0 || age > 0.6) {
          r.dust.place(i, 0, -10, 0, 0.0001);
          continue;
        }
        const z0 = lerp(SLAT.len / 2 + 0.15, -SLAT.len / 2 - 0.15, ease.inOut(clamp(born / 1.9)));
        const h = Math.sin(i * 12.9898) * 0.5 + 0.5;
        const x = grooveZ(i % 9) + (h - 0.5) * 0.05;
        r.dust.place(i, x + (h - 0.5) * age * 0.6, SLAT.base + 0.05 + age * 1.1 - 2.5 * age * age, z0 + age * 0.5, 1);
      }
      r.dust.done();
    },
    anchors: {
      slat: (r, v) => r.s.group.localToWorld(v.set(0.4, 0.06, 0.2)),
      cutter: (r, v) => r.cutter.localToWorld(v.set(0.25, 0.1, 0)),
    },
  });

  // ============ 7. fill: leads drop in, glue, the second slat closes it ============
  HM.shot("fill", {
    set: { keyPos: [-3, 6, 3], fog: 0.045 },
    build(scene) {
      const s = slat(7, true);
      s.group.rotation.y = Math.PI / 2;
      scene.add(s.group);
      const ls = leads();
      ls.forEach((m, k) => {
        m.rotation.set(0, Math.PI / 2, Math.PI / 2);
        scene.add(m);
      });
      const glue = new THREE.Mesh(
        new THREE.BoxGeometry(SLAT.width - 0.02, 0.004, SLAT.len - 0.04),
        new THREE.MeshPhysicalMaterial({ color: "#f4efe2", roughness: 0.05, clearcoat: 1, transparent: true, opacity: 0 }),
      );
      glue.position.y = SLAT.base + SLAT.ridge + 0.003;
      scene.add(glue);
      const top = slat(19, true);
      top.group.rotation.set(Math.PI, Math.PI / 2, 0);
      scene.add(top.group);
      return { s, ls, glue, top };
    },
    camera: [
      { p: 0, pos: [0.8, 1.2, 1.45], look: [0, 0.05, 0.05], fov: 34 },
      { p: 0.55, pos: [0.7, 0.85, 1.35], look: [0, 0.06, 0.05], fov: 34 },
      { p: 1, pos: [0.95, 0.85, 1.75], look: [0, 0.08, 0.0], fov: 34 },
    ],
    update(r, p, local, dur, t, shot) {
      const yRest = SLAT.base + 0.011;
      r.ls.forEach((m, k) => {
        const d = after(local, shot.marks.drop + k * 0.11, 0.45, ease.in);
        m.position.set(grooveZ(k), lerp(0.9, yRest, d), 0);
        m.visible = local > shot.marks.drop + k * 0.11 - 0.6;
      });
      r.glue.material.opacity = 0.14 * after(local, shot.marks.glue, 0.5);
      const c = after(local, shot.marks.close, 1.1, ease.inOut);
      const closed = 2 * (SLAT.base + SLAT.ridge);
      r.top.group.position.set(0, lerp(1.0, closed, c), 0);
      r.top.group.rotation.z = lerp(0.35, 0, c);
      r.top.group.visible = local > shot.marks.close - 0.4;
    },
    anchors: { glue: (r, v) => v.set(0.2, SLAT.base + SLAT.ridge, 0.4) },
  });

  // ============ 8. shape: cutters shave six sides, the sandwich splits into nine ============
  HM.shot("shape", {
    set: { keyPos: [-3, 6, 3], fog: 0.045 },
    build(scene) {
      const clipBlock = new THREE.Plane(new THREE.Vector3(0, 0, -1), 0);
      const clipPencils = new THREE.Plane(new THREE.Vector3(0, 0, 1), 0);
      const sandwich = new THREE.Group();
      const a = slat(7, true);
      const b = slat(19, true);
      b.group.rotation.x = Math.PI;
      b.group.position.y = 2 * (SLAT.base + SLAT.ridge);
      sandwich.add(a.group, b.group);
      sandwich.rotation.y = Math.PI / 2;
      sandwich.traverse((o) => o.isMesh && (o.material = o.material.clone(), (o.material.clippingPlanes = [clipBlock])));
      scene.add(sandwich);
      const cy = SLAT.base + SLAT.ridge;
      const ps = [];
      for (let k = 0; k < SLAT.n; k++) {
        const pc = pencil({ sharp: false, ferrule: false, length: SLAT.len - 0.02, bodyMat: M.cedar(30 + k) });
        pc.body.material.clippingPlanes = [clipPencils];
        pc.core.material = pc.core.material.clone();
        pc.core.material.clippingPlanes = [clipPencils];
        pc.group.scale.set(0.95, 1, 0.95);
        pc.group.rotation.x = Math.PI / 2;
        pc.group.position.set(grooveZ(k), cy, -(SLAT.len - 0.02) / 2);
        scene.add(pc.group);
        ps.push(pc);
      }
      const rollerMat = HM.mat.metal({ color: "#a9adb5", roughness: 0.3 });
      const rollers = [cy + 0.11, cy - 0.11].map((y) => {
        const m = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 0.8, 32), rollerMat);
        m.rotation.z = Math.PI / 2;
        m.position.y = y;
        scene.add(HM.shade(m));
        return m;
      });
      return { sandwich, ps, rollers, clipBlock, clipPencils, cy };
    },
    camera: [
      { p: 0, pos: [0.95, 0.85, 1.75], look: [0, 0.08, 0.0], fov: 34 },
      { p: 0.6, pos: [0.85, 1.0, 1.25], look: [0, 0.06, 0.0], fov: 34 },
      { p: 1, pos: [0.6, 1.35, 1.0], look: [0, 0.03, -0.05], fov: 34 },
    ],
    update(r, p, local, dur, t, shot) {
      const L = SLAT.len / 2 + 0.05;
      const c = after(local, shot.marks.cut + 0.2, 3.0, ease.inOut);
      const z = lerp(-L, L, c); // cutters run from far to near; pencils behind them
      // block: keep points nearer than the cutter (z > cut) -> normal (0,0,1), constant -cut
      r.clipBlock.normal.set(0, 0, 1);
      r.clipBlock.constant = -z;
      // pencils: keep points behind the cutter (z < cut) -> normal (0,0,-1), constant cut
      r.clipPencils.normal.set(0, 0, -1);
      r.clipPencils.constant = z;
      r.rollers.forEach((m, i) => {
        m.position.z = z;
        m.rotation.x = local * (i ? -12 : 12);
        m.visible = c > 0 && c < 1;
      });
      const s = after(local, shot.marks.split, 1.2, ease.out);
      r.ps.forEach((pc, k) => {
        const off = k - (SLAT.n - 1) / 2;
        pc.group.position.x = grooveZ(k) + off * 0.06 * s;
        pc.group.position.y = r.cy + Math.abs(off) * -0.004 * s + s * 0.03;
        pc.group.rotation.y = off * 0.05 * s;
      });
    },
    anchors: { mid: (r, v) => r.ps[4].group.localToWorld(v.set(0, 0.6, 0.04)) },
  });

  // ============ 9. paint: coats of yellow, the band, the eraser ============
  HM.shot("paint", {
    set: { keyPos: [-3, 6, 4], floorY: -0.1, fog: 0.05 },
    build(scene) {
      const xs = [-0.2, 0, 0.2];
      const ps = xs.map((x, i) => {
        const pc = pencil({ sharp: false, length: 1.5, bodyMat: M.cedar(60 + i) });
        const coat = new THREE.Mesh(HM.hexPrism(0.0405, 1.5), M.yellow());
        coat.material.transparent = true;
        coat.position.y = 0.75;
        coat.castShadow = true;
        pc.group.add(coat);
        pc.coat = coat;
        pc.group.rotation.set(Math.PI, i * 0.5, 0); // tip end down, ferrule end up
        pc.group.position.set(x, 1.62 + (i === 1 ? 0.06 : 0), i === 1 ? 0.12 : 0);
        scene.add(pc.group);
        return pc;
      });
      return { ps };
    },
    camera: [
      { p: 0, pos: [0.0, 1.0, 3.4], look: [0, 0.95, 0], fov: 34 },
      { p: 1, pos: [0.1, 1.3, 2.75], look: [0, 1.2, 0], fov: 34 },
    ],
    update(r, p, local, dur, t, shot) {
      const coats = clamp((local - shot.marks.coats) / 1.6) * 10;
      const band = after(local, shot.marks.band, 0.5, ease.out);
      const er = after(local, shot.marks.eraser, 0.45, ease.out);
      r.ps.forEach((pc, i) => {
        pc.coat.material.opacity = clamp(coats / 3);
        pc.coat.material.depthWrite = coats > 2.5;
        pc.group.rotation.y = i * 0.5 + local * 0.35;
        // group is flipped, so local -y is up in the world
        pc.ferrule.position.y = lerp(-0.7, -0.04, band);
        pc.ferrule.visible = band > 0;
        pc.eraser.position.y = lerp(-0.9, -0.13, er);
        pc.eraser.visible = er > 0;
      });
    },
    anchors: { body: (r, v) => r.ps[1].group.localToWorld(v.set(0.04, 0.9, 0)) },
  });

  // ============ 10. history: a black rock that marked like lead ============
  HM.shot("history", {
    set: { keyPos: [-2, 5, 2.5], fog: 0.06, floorColor: "#24211e", key: 0.9 },
    build(scene) {
      const paper = new THREE.Mesh(new THREE.PlaneGeometry(1.1, 0.8), M.paper());
      paper.rotation.x = -Math.PI / 2;
      paper.rotation.z = 0.12;
      paper.position.set(0.05, 0.003, 0.1);
      paper.receiveShadow = true;
      scene.add(paper);
      const rock = new THREE.Mesh(lump(0.16, 0.22, 77), HM.mat.graphite({ color: "#1f1f22", roughness: 0.28 }));
      rock.castShadow = true;
      scene.add(rock);
      const streak = new THREE.Mesh(new THREE.BoxGeometry(0.09, 0.002, 1), HM.mat.matte("#2a2a2d", { roughness: 0.5, metalness: 0.35 }));
      streak.position.y = 0.005;
      scene.add(streak);
      const stones = new THREE.Group();
      const sr = rng(91);
      for (let i = 0; i < 9; i++) {
        const s = new THREE.Mesh(lump(0.05 + sr() * 0.07, 0.25, 100 + i, 3), HM.mat.matte("#3a3632", { roughness: 0.9 }));
        const a = sr() * 6.28;
        s.position.set(Math.cos(a) * (1.0 + sr() * 0.6), 0.03, Math.sin(a) * (0.8 + sr() * 0.4) - 0.5);
        stones.add(s);
      }
      void stones; // background stones read as floating against the black; left out
      return { rock, streak };
    },
    camera: [
      { p: 0, pos: [0.0, 2.3, 2.1], look: [0, 0.05, 0], fov: 34 },
      { p: 1, pos: [0.35, 1.35, 1.95], look: [0.05, 0.1, 0.05], fov: 34 },
    ],
    update(r, p, local, dur, t, shot) {
      const k = after(local, shot.marks.marked, 1.4, ease.inOut);
      const x0 = -0.32;
      const x1 = 0.3;
      const z = 0.12;
      const lift = after(local, shot.marks.found, 0.6) * (1 - after(local, shot.marks.marked - 0.15, 0.3));
      r.rock.position.set(lerp(x0, x1, k), 0.14 + lift * 0.12, z);
      r.rock.rotation.set(0.3 + local * 0.05, local * 0.25, k * 0.8);
      const len = Math.max(0.001, (x1 - x0) * k);
      r.streak.scale.z = len;
      r.streak.rotation.y = Math.PI / 2;
      r.streak.position.set(x0 + len / 2, 0.005, z);
      r.streak.visible = k > 0;
    },
    anchors: { rock: (r, v) => r.rock.localToWorld(v.set(0, 0.12, 0)) },
  });

  // ============ 11. payoff: the name stuck ============
  HM.shot("payoff", {
    set: { keyPos: [-2.5, 5, 3], fog: 0.05 },
    build(scene) {
      const paper = new THREE.Mesh(new THREE.PlaneGeometry(1.4, 1.0), M.paper());
      paper.rotation.x = -Math.PI / 2;
      paper.position.y = 0.002;
      paper.receiveShadow = true;
      scene.add(paper);
      const p = pencil({ length: 1.5 });
      scene.add(p.group);
      const line = new THREE.Mesh(new THREE.BoxGeometry(1, 0.002, 0.018), HM.mat.matte("#3a3a3d", { roughness: 0.45, metalness: 0.3 }));
      line.position.y = 0.004;
      scene.add(line);
      return { ...p, line };
    },
    camera: [
      { p: 0, pos: [0.55, 1.15, 2.1], look: [0.15, 0.4, 0], fov: 34 },
      { p: 1, pos: [0.35, 1.0, 1.8], look: [0.2, 0.4, 0], fov: 34 },
    ],
    update(r, p, local, dur, t, shot) {
      const k = clamp(local / dur);
      const x = lerp(-0.4, 0.35, ease.inOut(k));
      // pencil leans back along -x, tip touching the paper at (x, 0, 0)
      r.group.rotation.set(0, 0, 2.45); // tip down and to the left
      const tipLocal = new THREE.Vector3(0, r.L + 0.245, 0).applyEuler(r.group.rotation);
      r.group.position.set(x - tipLocal.x, -tipLocal.y + 0.004, Math.sin(k * 9) * 0.01);
      const len = Math.max(0.001, x + 0.4);
      r.line.scale.x = len;
      r.line.position.set(-0.4 + len / 2, 0.004, 0);
    },
  });

  // ============ 12. cta: the hero pencil ============
  HM.shot("cta", {
    set: { keyPos: [-3, 6, 4], floorY: -0.2, fog: 0.05 },
    build(scene) {
      return hero(scene);
    },
    camera: [
      { p: 0, pos: [-0.05, 1.2, 3.5], look: [0, 1.1, 0], fov: 33 },
      { p: 1, pos: [0.3, 1.15, 4.7], look: [0, 0.95, 0], fov: 34 },
    ],
    update(r, p, local) {
      r.spin.rotation.y = 2.0 + local * 0.4;
    },
  });
})();
