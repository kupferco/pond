import * as THREE from 'three';
import type { MainModule, MjData, MjModel } from '@mujoco/mujoco';

/** What the viewer needs from a simulation: a model, its data and the MuJoCo module. */
export interface SimLike { mujoco: MainModule; model: MjModel; data: MjData }

// Renders every MuJoCo geom as a three.js mesh and copies xpos/xmat each frame.
export class Viewer {
  private renderer = new THREE.WebGLRenderer({ antialias: true });
  private scene = new THREE.Scene();
  private camera = new THREE.PerspectiveCamera(40, 1, 0.01, 10);
  private ro: ResizeObserver;
  private meshes: THREE.Mesh[] = [];
  private orbit = { az: 0.9, el: 0.45, dist: 0.7 };
  private maxDist = 2;
  private target = new THREE.Vector3(0.08, 0, 0.12);

  constructor(private host: HTMLElement, private sim: SimLike, opts: { target?: [number, number, number]; dist?: number; maxDist?: number; az?: number; el?: number; far?: number } = {}) {
    if (opts.target) this.target.set(...opts.target);
    if (opts.dist) this.orbit.dist = opts.dist;
    if (opts.az !== undefined) this.orbit.az = opts.az;
    if (opts.el !== undefined) this.orbit.el = opts.el;
    if (opts.maxDist) this.maxDist = opts.maxDist;
    if (opts.far) { this.camera.far = opts.far; this.camera.updateProjectionMatrix(); }
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    host.appendChild(this.renderer.domElement);
    this.scene.background = new THREE.Color(0xf6f9fc);
    this.scene.add(new THREE.HemisphereLight(0xffffff, 0x334455, 1.6));
    const sun = new THREE.DirectionalLight(0xffffff, 2.2);
    sun.position.set(0.5, -0.4, 1);
    this.scene.add(sun);
    this.buildMeshes();
    this.bindOrbit();
    this.ro = new ResizeObserver(() => this.resize());
    this.ro.observe(host);
    this.resize();
  }

  // MuJoCo is Z-up, three.js is Y-up: wrap everything in a rotated group.
  private root = (() => { const g = new THREE.Group(); g.rotation.x = -Math.PI / 2; this.scene.add(g); return g; })();

  private buildMeshes() {
    const m = this.sim.model;
    const T = this.sim.mujoco.mjtGeom;
    for (let i = 0; i < m.ngeom; i++) {
      const type = m.geom_type[i];
      const s = [m.geom_size[3 * i], m.geom_size[3 * i + 1], m.geom_size[3 * i + 2]];
      let geo: THREE.BufferGeometry;
      if (type === T.mjGEOM_PLANE.value) {
        geo = new THREE.PlaneGeometry(s[0] * 2, s[1] * 2);
      } else if (type === T.mjGEOM_BOX.value) {
        geo = new THREE.BoxGeometry(s[0] * 2, s[1] * 2, s[2] * 2);
      } else if (type === T.mjGEOM_SPHERE.value) {
        geo = new THREE.SphereGeometry(s[0], 24, 16);
      } else if (type === T.mjGEOM_CYLINDER.value) {
        geo = new THREE.CylinderGeometry(s[0], s[0], s[1] * 2, 32).rotateX(Math.PI / 2);
      } else if (type === T.mjGEOM_CAPSULE.value) {
        geo = new THREE.CapsuleGeometry(s[0], s[1] * 2, 8, 16).rotateX(Math.PI / 2);
      } else {
        continue; // unsupported: skip, keep index alignment via sparse array
      }
      const c = m.geom_rgba;
      const mat = new THREE.MeshStandardMaterial({
        color: new THREE.Color(c[4 * i], c[4 * i + 1], c[4 * i + 2]),
        roughness: 0.6,
        metalness: 0.1,
      });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.matrixAutoUpdate = false;
      this.root.add(mesh);
      this.meshes[i] = mesh;
    }
  }

  private bindOrbit() {
    const el = this.renderer.domElement;
    // touch-action: none (set in CSS too) so drags on the canvas orbit instead of scrolling the page;
    // the rest of the page still scrolls normally. One pointer orbits, two pointers pinch-zoom.
    el.style.touchAction = 'none';
    const pts = new Map<number, { x: number; y: number }>();
    const pinchDist = () => { const [a, b] = [...pts.values()]; return Math.hypot(a.x - b.x, a.y - b.y); };
    let lastPinch = 0;
    const centroid = () => { const [a, b] = [...pts.values()]; return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 }; };
    el.addEventListener('pointerdown', (e) => {
      pts.set(e.pointerId, { x: e.clientX, y: e.clientY });
      el.setPointerCapture(e.pointerId);
      if (pts.size === 2) lastPinch = pinchDist();
    });
    const up = (e: PointerEvent) => { pts.delete(e.pointerId); if (pts.size === 2) lastPinch = pinchDist(); };
    el.addEventListener('pointerup', up);
    el.addEventListener('pointercancel', up);
    // Pan: right-drag, Shift+drag, or a two-finger drag (the centroid of the two touches). One pointer without those rotates; the pinch zooms.
    const buttons = new Map<number, number>();
    el.addEventListener('contextmenu', (e) => e.preventDefault());
    el.addEventListener('pointerdown', (e) => buttons.set(e.pointerId, e.button));
    el.addEventListener('pointermove', (e) => {
      const p = pts.get(e.pointerId);
      if (!p) return;
      const before = pts.size >= 2 ? centroid() : null;
      const dx = e.clientX - p.x, dy = e.clientY - p.y;
      p.x = e.clientX; p.y = e.clientY;
      if (before) {
        const c = centroid();
        this.pan(c.x - before.x, c.y - before.y);
        const d = pinchDist();
        if (lastPinch > 0 && d > 0) this.orbit.dist = Math.min(this.maxDist, Math.max(0.2, this.orbit.dist * (lastPinch / d)));
        lastPinch = d;
        return;
      }
      if (e.shiftKey || (buttons.get(e.pointerId) ?? 0) === 2 || (e.buttons & 2) !== 0) { this.pan(dx, dy); return; }
      this.orbit.az -= dx * 0.008;
      this.orbit.el = Math.min(1.5, Math.max(0.02, this.orbit.el + dy * 0.008));
    });
    el.addEventListener('wheel', (e) => {
      e.preventDefault();
      this.orbit.dist = Math.min(this.maxDist, Math.max(0.2, this.orbit.dist * Math.exp(e.deltaY * 0.001)));
    }, { passive: false });
  }

  /** Shift the look-at point in the screen plane by a drag of (dx, dy) pixels: the scene follows the pointer. */
  private pan(dx: number, dy: number) {
    const { az, el, dist } = this.orbit, k = dist * 0.0012;
    const right = new THREE.Vector3(Math.cos(az), 0, -Math.sin(az));
    const up = new THREE.Vector3(-Math.sin(el) * Math.sin(az), Math.cos(el), -Math.sin(el) * Math.cos(az));
    const d = right.multiplyScalar(-dx * k).add(up.multiplyScalar(dy * k));   // three's Y-up frame; the target is Z-up
    this.target.add(new THREE.Vector3(d.x, -d.z, d.y));
  }

  private resize() {
    const w = this.host.clientWidth, h = this.host.clientHeight;
    this.renderer.setSize(w, h, false);
    this.renderer.domElement.style.width = '100%';
    this.renderer.domElement.style.height = '100%';
    this.camera.aspect = w / Math.max(h, 1);
    this.camera.updateProjectionMatrix();
  }

  dispose() {
    this.ro.disconnect();
    this.scene.traverse((o) => {
      if (o instanceof THREE.Mesh) { o.geometry.dispose(); (o.material as THREE.Material).dispose(); }
    });
    this.renderer.dispose();
    this.renderer.domElement.remove();
  }

  render() {
    const d = this.sim.data;
    const mat = new THREE.Matrix4();
    const x = d.geom_xpos, r = d.geom_xmat;
    this.meshes.forEach((mesh, i) => {
      if (!mesh) return;
      // Plane geoms and the rest share the same transform; MuJoCo xmat is row-major 3x3.
      mat.set(
        r[9 * i], r[9 * i + 1], r[9 * i + 2], x[3 * i],
        r[9 * i + 3], r[9 * i + 4], r[9 * i + 5], x[3 * i + 1],
        r[9 * i + 6], r[9 * i + 7], r[9 * i + 8], x[3 * i + 2],
        0, 0, 0, 1,
      );
      mesh.matrix.copy(mat);
      mesh.matrixWorldNeedsUpdate = true;
    });
    const { az, el, dist } = this.orbit;
    // Camera position in three's Y-up frame (target is given in MuJoCo Z-up, convert).
    const t = new THREE.Vector3(this.target.x, this.target.z, -this.target.y);
    this.camera.position.set(
      t.x + dist * Math.cos(el) * Math.sin(az),
      t.y + dist * Math.sin(el),
      t.z + dist * Math.cos(el) * Math.cos(az),
    );
    this.camera.lookAt(t);
    this.renderer.render(this.scene, this.camera);
  }
}
