<script>
(async function () {
  const S = __SQMETA__;
  const canvas = document.getElementById("sq-gl"), foot = document.getElementById("sq-foot");
  if (!window.THREE) return;
  async function gunzip(id) {
    const bin = Uint8Array.from(atob(document.getElementById(id).textContent.trim()), c => c.charCodeAt(0));
    return new Response(new Blob([bin]).stream().pipeThrough(new DecompressionStream("gzip"))).arrayBuffer();
  }
  const geoBuf = await gunzip("d-sqgeo"), anim = new Float32Array(await gunzip("d-sqanim"));
  const q = new Uint16Array(geoBuf, 0, S.verts * 3), idx = new Uint32Array(geoBuf.slice(S.verts * 6));
  const pos = new Float32Array(S.verts * 3);
  for (let i = 0; i < S.verts; i++) for (let k = 0; k < 3; k++) pos[i * 3 + k] = S.lo[k] + q[i * 3 + k] / 65535 * (S.hi[k] - S.lo[k]);
  const posAttr = new THREE.BufferAttribute(pos, 3);
  const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const mat = new THREE.MeshStandardMaterial({ roughness: 0.75 });
  const barMat = new THREE.MeshStandardMaterial({ roughness: 0.4, metalness: 0.6 });
  const theme = () => { mat.color.set(css("--bone")); barMat.color.set("#7d8796"); };
  theme(); new MutationObserver(theme).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  matchMedia("(prefers-color-scheme: dark)").addEventListener?.("change", theme);

  const scene = new THREE.Scene();
  scene.add(new THREE.HemisphereLight(0xffffff, 0x50576a, 0.75));
  const kl = new THREE.DirectionalLight(0xffffff, 0.75); kl.position.set(1.5, 3, 2.5); scene.add(kl);
  const rl = new THREE.DirectionalLight(0xffffff, 0.35); rl.position.set(-2, 1.5, -2.5); scene.add(rl);
  // Feet stay planted, so centre the model on its rest-pose footprint.
  const off = new THREE.Vector3(-(S.lo[0] + S.hi[0]) / 2, -S.lo[1], -(S.lo[2] + S.hi[2]) / 2);
  const root = new THREE.Group(); root.position.copy(off); scene.add(root);
  // Parts share one position buffer: compute normals once over all of it and share them.
  const all = new THREE.BufferGeometry(); all.setAttribute("position", posAttr);
  all.setIndex(new THREE.BufferAttribute(idx, 1)); all.computeVertexNormals();
  const normals = all.getAttribute("normal");
  const parts = S.ranges.map(([name, start, count]) => {
    const g = new THREE.BufferGeometry(); g.setAttribute("position", posAttr);
    g.setIndex(new THREE.BufferAttribute(idx.subarray(start, start + count), 1));
    g.setAttribute("normal", normals);
    const m = new THREE.Mesh(g, mat); m.matrixAutoUpdate = false; root.add(m); return m;
  });
  const bar = new THREE.Mesh(new THREE.CylinderGeometry(0.014, 0.014, 2.0, 16), barMat); root.add(bar);

  const N = S.frames, P = parts.length, tmpA = new THREE.Vector3(), tmpB = new THREE.Vector3();
  const qa = new THREE.Quaternion(), qb = new THREE.Quaternion(), one = new THREE.Vector3(1, 1, 1);
  function apply(t) { // t in 0..1 of descent
    const f = t * (N - 1), f0 = Math.floor(f), f1 = Math.min(N - 1, f0 + 1), u = f - f0;
    for (let i = 0; i < P; i++) {
      const a = (f0 * P + i) * 7, b = (f1 * P + i) * 7;
      tmpA.set(anim[a], anim[a + 1], anim[a + 2]).lerp(tmpB.set(anim[b], anim[b + 1], anim[b + 2]), u);
      qa.set(anim[a + 3], anim[a + 4], anim[a + 5], anim[a + 6]); qb.set(anim[b + 3], anim[b + 4], anim[b + 5], anim[b + 6]);
      qa.slerp(qb, u); parts[i].matrix.compose(tmpA, qa, one);
    }
    const h0 = S.bar[f0], h1 = S.bar[f1];
    const L = new THREE.Vector3(h0[0], h0[1], h0[2]).lerp(new THREE.Vector3(h1[0], h1[1], h1[2]), u);
    const R = new THREE.Vector3(h0[3], h0[4], h0[5]).lerp(new THREE.Vector3(h1[3], h1[4], h1[5]), u);
    bar.position.copy(L).add(R).multiplyScalar(0.5); bar.position.y += 0.02;
    bar.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), R.clone().sub(L).normalize());
  }

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  const cam = new THREE.PerspectiveCamera(30, 1, 0.01, 50);
  const ctl = new THREE.OrbitControls(cam, canvas); ctl.enableDamping = true; ctl.dampingFactor = 0.12;
  const DIRS = { front: [0, 0.1, 1], side: [-1, 0.1, 0.25], back: [0, 0.1, -1] };
  function view(v) {
    const d = new THREE.Vector3(...DIRS[v]).normalize();
    ctl.target.set(0, 0.7, 0); cam.position.set(d.x * 3.4, 0.7 + d.y * 3.4, d.z * 3.4); ctl.update();
    document.querySelectorAll("[data-sqview]").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.sqview === v)));
  }
  document.querySelectorAll("[data-sqview]").forEach(b => b.addEventListener("click", () => view(b.dataset.sqview)));
  view("side");

  const slider = document.getElementById("sq-t"), playBtn = document.getElementById("sq-play");
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  let playing = !reduce, phase = 0, last = performance.now();
  const sync = () => { playBtn.textContent = playing ? "Pause" : "Play"; playBtn.setAttribute("aria-pressed", String(playing)); };
  sync();
  playBtn.addEventListener("click", () => { playing = !playing; sync(); });
  slider.addEventListener("input", () => { playing = false; sync(); phase = slider.value / 2000; });
  function size() { const r = canvas.getBoundingClientRect(); renderer.setSize(r.width, r.height, false); cam.aspect = r.width / r.height; cam.updateProjectionMatrix(); }
  new ResizeObserver(size).observe(canvas); size();
  (function loop(now) {
    const dt = (now - last) / 1000; last = now;
    if (playing) phase = (phase + dt / 4) % 1;          // 4 s per rep: 2 s down, 2 s up
    const t = phase < 0.5 ? phase * 2 : 2 - phase * 2;   // ping-pong
    if (playing) slider.value = Math.round(t * 1000);
    apply(t);
    foot.textContent = `${P} bone meshes · ${S.tris.toLocaleString()} triangles (25%) · depth ${Math.round(t * 100)}%`;
    ctl.update(); renderer.render(scene, cam); requestAnimationFrame(loop);
  })(last);
})();
</script>
