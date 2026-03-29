# Exploded View

Interactive 3D exploded (blowout) view of the Genbu robot assembly.

Drag to orbit, scroll to zoom, and use the **Explode** slider to pull the
components apart and see how they fit together.

<script type="importmap">
{
  "imports": {
    "three": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
    "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"
  }
}
</script>

<div id="ev-root" style="border:1px solid #374151;border-radius:8px;overflow:hidden;margin:1rem 0;">
  <canvas id="ev-canvas" style="width:100%;height:500px;display:block;background:#0d1117;"></canvas>
  <div style="padding:10px 16px;background:#111827;border-top:1px solid #374151;">
    <label for="ev-slider" style="color:#9ca3af;font-size:13px;">
      Explode&nbsp;
      <input type="range" id="ev-slider" min="0" max="100" value="0" style="width:200px;vertical-align:middle;">
      &nbsp;<span id="ev-pct" style="color:#d1d5db;font-size:13px;display:inline-block;min-width:3em;">0%</span>
    </label>
    <span style="float:right;color:#4b5563;font-size:11px;line-height:2.2;">Drag to orbit &middot; Scroll to zoom</span>
  </div>
</div>

<script type="module">
import * as THREE from 'three';
import { GLTFLoader }   from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

(async () => {
  const canvas   = document.getElementById('ev-canvas');
  const slider   = document.getElementById('ev-slider');
  const pctLabel = document.getElementById('ev-pct');

  /* ── Renderer ── */
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;

  /* ── Scene ── */
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0d1117);

  /* ── Camera ── */
  const camera = new THREE.PerspectiveCamera(45, 1, 0.001, 20);
  camera.position.set(0.55, 0.4, 0.55);

  /* ── Lights ── */
  scene.add(new THREE.AmbientLight(0xffffff, 0.6));

  const sun = new THREE.DirectionalLight(0xffffff, 1.8);
  sun.position.set(1.5, 3, 2);
  sun.castShadow = true;
  sun.shadow.camera.near   =  0.1;
  sun.shadow.camera.far    = 10;
  sun.shadow.camera.left   = -1;
  sun.shadow.camera.right  =  1;
  sun.shadow.camera.top    =  1;
  sun.shadow.camera.bottom = -1;
  scene.add(sun);

  const fill = new THREE.DirectionalLight(0x5577aa, 0.5);
  fill.position.set(-2, 1, -2);
  scene.add(fill);

  /* ── Grid floor ── */
  scene.add(new THREE.GridHelper(1.2, 12, 0x374151, 0x1f2937));

  /* ── Orbit controls ── */
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.target.set(0, 0.08, 0);
  controls.enableDamping  = true;
  controls.dampingFactor  = 0.06;
  controls.minDistance    = 0.1;
  controls.maxDistance    = 3;
  controls.update();

  /* ── Coordinate-system bridge ──────────────────────────────────────────────
   *  URDF / ROS uses Z-up (X-forward, Y-left, Z-up).
   *  Three.js / GLTF uses Y-up.
   *
   *  All robot parts are children of `world`, which is rotated -90° around X.
   *  This maps URDF +Z (up) → Three.js +Y (up), so positions and explode
   *  offsets can be given directly in URDF / manifest coordinates.
   * ── */
  const world = new THREE.Group();
  world.rotation.x = -Math.PI / 2;
  scene.add(world);

  /* ── Fetch manifest ── */
  let manifest = {};
  try {
    const res = await fetch('../assets/manifest.json');
    if (res.ok) {
      manifest = await res.json();
    } else {
      console.warn('[exploded-view] manifest.json not available (HTTP', res.status, ')');
    }
  } catch (e) {
    console.warn('[exploded-view] Could not fetch manifest.json:', e.message);
  }

  /* ── Load GLB meshes ── */
  const loader = new GLTFLoader();

  const loadGlb = (url) => new Promise((resolve) =>
    loader.load(
      url,
      (gltf) => resolve(gltf.scene),
      undefined,
      () => { console.warn('[exploded-view] Failed to load:', url); resolve(null); }
    )
  );

  /*
   * parts[] stores per-mesh animation data:
   *   group        – Three.js Group in URDF (Z-up) space
   *   assembledPos – position at factor = 0 (from manifest xyz)
   *   explodeDir   – unit vector to move along when exploding
   *
   * Root parts (assembled xyz ≈ origin) stay fixed; all other parts are pushed
   * straight up (+Z in URDF = +Y in the Three.js world) so the assembly
   * separates vertically – matching the physical stack of components.
   */
  const parts = [];

  for (const [srcName, entry] of Object.entries(manifest)) {
    /* Prefer the `name` field written by generate_mesh_assets.py; fall back to
       deriving the GLB filename from the source file stem. */
    const glbName     = entry.name || (srcName.replace(/\.[^.]+$/, '') + '.glb');
    const assembledPos = new THREE.Vector3(...(entry.xyz || [0, 0, 0]));
    const rpy          = entry.rpy || [0, 0, 0];

    const group = new THREE.Group();
    group.position.copy(assembledPos);
    /* URDF RPY: R = Rz(yaw)·Ry(pitch)·Rx(roll)
       Three.js Euler 'ZYX': M = Rz(euler.z)·Ry(euler.y)·Rx(euler.x) → matches. */
    group.rotation.set(rpy[0], rpy[1], rpy[2], 'ZYX');
    world.add(group);

    const mesh = await loadGlb(`../assets/meshes/${glbName}`);
    if (mesh) {
      mesh.traverse((child) => {
        if (child.isMesh) {
          child.castShadow    = true;
          child.receiveShadow = true;
        }
      });
      group.add(mesh);
    }

    const isRoot = assembledPos.lengthSq() < 1e-6;
    parts.push({
      group,
      assembledPos : assembledPos.clone(),
      explodeDir   : isRoot ? new THREE.Vector3(0, 0, 0)   // root stays fixed
                            : new THREE.Vector3(0, 0, 1),  // others move up (+Z URDF)
    });
  }

  /* ── Explode / reassemble ── */
  const MAX_EXPLODE = 0.30; // metres in URDF space

  function applyExplode(factor) {
    for (const { group, assembledPos, explodeDir } of parts) {
      group.position
        .copy(assembledPos)
        .addScaledVector(explodeDir, factor * MAX_EXPLODE);
    }
  }

  slider.addEventListener('input', () => {
    const f = slider.value / 100;
    pctLabel.textContent = `${Math.round(f * 100)}%`;
    applyExplode(f);
  });

  /* ── Responsive resize ── */
  const onResize = () => {
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  };
  new ResizeObserver(onResize).observe(canvas);
  onResize();

  /* ── Render loop ── */
  const animate = () => {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
  };
  animate();
})();
</script>
