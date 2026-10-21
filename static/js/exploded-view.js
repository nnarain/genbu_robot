import * as THREE from 'https://esm.sh/three@0.160.0';
import { GLTFLoader } from 'https://esm.sh/three@0.160.0/examples/jsm/loaders/GLTFLoader.js';
import { OrbitControls } from 'https://esm.sh/three@0.160.0/examples/jsm/controls/OrbitControls.js';

(async () => {
  const canvas = document.getElementById('ev-canvas');
  const slider = document.getElementById('ev-slider');
  const pctLabel = document.getElementById('ev-pct');

  if (!canvas || !slider || !pctLabel) {
    return;
  }

  const showError = (msg) => {
    pctLabel.textContent = 'ERR';
    const root = document.getElementById('ev-root');
    if (root) {
      const err = document.createElement('div');
      err.style.cssText = 'padding:8px 12px;color:#fca5a5;background:#111827;border-top:1px solid #374151;font-size:12px;';
      err.textContent = `Exploded view failed: ${msg}`;
      root.appendChild(err);
    }
  };

  try {
    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0d1117);

  const camera = new THREE.PerspectiveCamera(45, 1, 0.001, 20);
  camera.position.set(0.55, 0.4, 0.55);

  scene.add(new THREE.AmbientLight(0xffffff, 0.6));

  const sun = new THREE.DirectionalLight(0xffffff, 1.8);
  sun.position.set(1.5, 3, 2);
  sun.castShadow = true;
  sun.shadow.camera.near = 0.1;
  sun.shadow.camera.far = 10;
  sun.shadow.camera.left = -1;
  sun.shadow.camera.right = 1;
  sun.shadow.camera.top = 1;
  sun.shadow.camera.bottom = -1;
  scene.add(sun);

  const fill = new THREE.DirectionalLight(0x5577aa, 0.5);
  fill.position.set(-2, 1, -2);
  scene.add(fill);

  scene.add(new THREE.GridHelper(1.2, 12, 0x374151, 0x1f2937));

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.target.set(0, 0.08, 0);
  controls.enableDamping = true;
  controls.dampingFactor = 0.06;
  controls.minDistance = 0.1;
  controls.maxDistance = 3;
  controls.update();

  const world = new THREE.Group();
  scene.add(world);

  const urdfToThree = (x, y, z) => new THREE.Vector3(x, z, -y);

  const T = new THREE.Matrix4().set(1, 0, 0, 0, 0, 0, 1, 0, 0, -1, 0, 0, 0, 0, 0, 1);
  const Tinv = new THREE.Matrix4().set(1, 0, 0, 0, 0, 0, -1, 0, 0, 1, 0, 0, 0, 0, 0, 1);

  const urdfRpyToQuat = (rpy) => {
    const Rurdf = new THREE.Matrix4().makeRotationFromEuler(
      new THREE.Euler(rpy[0], rpy[1], rpy[2], 'XYZ')
    );
    const Rthree = T.clone().multiply(Rurdf).multiply(Tinv);
    return new THREE.Quaternion().setFromRotationMatrix(Rthree);
  };

  let manifest = {};
  try {
    const res = await fetch('assets/manifest.json');
    if (res.ok) {
      manifest = await res.json();
    } else {
      console.warn('[exploded-view] manifest.json not available (HTTP', res.status, ')');
    }
  } catch (e) {
    console.warn('[exploded-view] Could not fetch manifest.json:', e.message);
  }

  const loader = new GLTFLoader();

  const loadGlb = (url) =>
    new Promise((resolve) =>
      loader.load(
        url,
        (gltf) => resolve(gltf.scene),
        undefined,
        () => {
          console.warn('[exploded-view] Failed to load:', url);
          resolve(null);
        }
      )
    );

  const parts = [];

  for (const [srcName, entry] of Object.entries(manifest)) {
    const glbName = entry.name || (srcName.replace(/\.[^.]+$/, '') + '.glb');
    const [ux, uy, uz] = entry.xyz || [0, 0, 0];
    const assembledPos = urdfToThree(ux, uy, uz);

    const group = new THREE.Group();
    group.position.copy(assembledPos);
    group.quaternion.copy(urdfRpyToQuat(entry.rpy || [0, 0, 0]));
    world.add(group);

    const mesh = await loadGlb(`assets/meshes/${glbName}`);
    if (mesh) {
      mesh.traverse((child) => {
        if (child.isMesh) {
          child.castShadow = true;
          child.receiveShadow = true;
        }
      });
      group.add(mesh);
    }

    const explodeDir = assembledPos.lengthSq() < 1e-6
      ? new THREE.Vector3(0, 0, 0)
      : assembledPos.clone().normalize();
    parts.push({
      group,
      assembledPos: assembledPos.clone(),
      explodeDir,
    });
  }

  const MAX_EXPLODE = 0.3;

  function applyExplode(factor) {
    for (const { group, assembledPos, explodeDir } of parts) {
      group.position.copy(assembledPos).addScaledVector(explodeDir, factor * MAX_EXPLODE);
    }
  }

  slider.addEventListener('input', () => {
    const f = Number(slider.value) / 100;
    pctLabel.textContent = `${Math.round(f * 100)}%`;
    applyExplode(f);
  });

  const onResize = () => {
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  };

  new ResizeObserver(onResize).observe(canvas);
  onResize();

    const animate = () => {
      requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };

    animate();
  } catch (e) {
    console.error('[exploded-view] Fatal error:', e);
    showError(e?.message || String(e));
  }
})();
