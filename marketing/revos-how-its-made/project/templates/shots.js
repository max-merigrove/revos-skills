/* {{TITLE}}: the 3D shots. Units: 1 = 10 cm. Timing comes from reel.json marks. */
(function () {
  const THREE = window.THREE;
  const { after, seg, ease, lerp, clamp, rng } = HM;

  HM.shot("hook", {
    set: { keyPos: [-3, 6, 4], fog: 0.05 },
    build(scene) {
      const hero = new THREE.Mesh(new THREE.RoundedBoxGeometry(0.6, 0.6, 0.6, 4, 0.06), HM.mat.paint("#c8452f"));
      hero.position.y = 0.6;
      scene.add(HM.shade(hero));
      return { hero };
    },
    camera: [
      { p: 0, pos: [0.3, 1.2, 3.6], look: [0, 0.6, 0], fov: 34 },
      { p: 1, pos: [0.0, 1.1, 3.0], look: [0, 0.6, 0], fov: 34 },
    ],
    update(r, p, local) {
      r.hero.rotation.y = 0.5 + local * 0.3;
    },
    anchors: { top: (r, v) => r.hero.localToWorld(v.set(0, 0.3, 0)) },
  });
})();
