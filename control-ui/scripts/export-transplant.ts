// Exports the Transplant scene for pictures: runs the four steps headless and writes, for the start and after each step, a GLB of the whole scene (for the 3D viewer), plus triangle lists
// (JSON) of those poses and of frames through every step, which scripts/render_tris.py turns into PNGs and clips (there is no GPU here, so the pictures are drawn by a small software renderer).
// Usage: node --experimental-strip-types scripts/export-transplant.ts OUT_DIR
import loadMujoco from '@mujoco/mujoco';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { transplantMjcf } from '../src/transplant/layout.ts';
import { Binder } from '../src/transplant/apply.ts';
import { STEPS, TransplantRun } from '../src/transplant/task.ts';

const out = process.argv[2];
if (!out) throw new Error('usage: export-transplant.ts OUT_DIR');
mkdirSync(out, { recursive: true });
const mj = await loadMujoco();
const model = mj.MjModel.from_xml_string(transplantMjcf());
const data = new mj.MjData(model);
const bind = new Binder(mj, model, data);
const T = mj.mjtGeom;

type Tri = number[];   // x0 y0 z0 x1 y1 z1 x2 y2 z2 r g b a
/** All visible geoms of the current pose as triangles (world coordinates). Planes are left out (the floor is drawn by the renderer). */
function triangles(): Tri[] {
  const tris: Tri[] = [];
  for (let g = 0; g < model.ngeom; g++) {
    const type = model.geom_type[g], a = model.geom_rgba[4 * g + 3];
    if (a === 0 || type === T.mjGEOM_PLANE.value) continue;
    const s = [model.geom_size[3 * g], model.geom_size[3 * g + 1], model.geom_size[3 * g + 2]];
    const p = [data.geom_xpos[3 * g], data.geom_xpos[3 * g + 1], data.geom_xpos[3 * g + 2]];
    const R = Array.from({ length: 9 }, (_, k) => data.geom_xmat[9 * g + k]);
    const col = [model.geom_rgba[4 * g], model.geom_rgba[4 * g + 1], model.geom_rgba[4 * g + 2], a];
    const w = (l: number[]) => [p[0] + R[0] * l[0] + R[1] * l[1] + R[2] * l[2], p[1] + R[3] * l[0] + R[4] * l[1] + R[5] * l[2], p[2] + R[6] * l[0] + R[7] * l[1] + R[8] * l[2]];
    const quad = (a0: number[], b0: number[], c0: number[], d0: number[]) => {
      const [A, B, C, D] = [w(a0), w(b0), w(c0), w(d0)];
      tris.push([...A, ...B, ...C, ...col], [...A, ...C, ...D, ...col]);
    };
    if (type === T.mjGEOM_BOX.value) {
      const [x, y, z] = s;
      quad([x, -y, -z], [x, y, -z], [x, y, z], [x, -y, z]); quad([-x, y, -z], [-x, -y, -z], [-x, -y, z], [-x, y, z]);
      quad([-x, y, -z], [x, y, -z], [x, y, z], [-x, y, z]); quad([x, -y, -z], [-x, -y, -z], [-x, -y, z], [x, -y, z]);
      quad([-x, -y, z], [x, -y, z], [x, y, z], [-x, y, z]); quad([-x, y, -z], [x, y, -z], [x, -y, -z], [-x, -y, -z]);
    } else if (type === T.mjGEOM_CYLINDER.value) {
      const n = 28, r = s[0], h = s[1];
      for (let k = 0; k < n; k++) {
        const a0 = 2 * Math.PI * k / n, a1 = 2 * Math.PI * (k + 1) / n;
        const c0 = [r * Math.cos(a0), r * Math.sin(a0)], c1 = [r * Math.cos(a1), r * Math.sin(a1)];
        quad([c0[0], c0[1], -h], [c1[0], c1[1], -h], [c1[0], c1[1], h], [c0[0], c0[1], h]);
        const T0 = w([0, 0, h]), T1 = w([c0[0], c0[1], h]), T2 = w([c1[0], c1[1], h]);
        tris.push([...T0, ...T1, ...T2, ...col]);
        const B0 = w([0, 0, -h]), B1 = w([c0[0], c0[1], -h]), B2 = w([c1[0], c1[1], -h]);
        tris.push([...B0, ...B2, ...B1, ...col]);
      }
    }
  }
  return tris;
}

/** A GLB (one mesh per colour, flat normals) from triangles. */
function glb(tris: Tri[]): Buffer {
  const groups = new Map<string, Tri[]>();
  for (const t of tris) { const k = t.slice(9).map((v) => v.toFixed(3)).join(','); (groups.get(k) ?? groups.set(k, []).get(k)!).push(t); }
  const bufs: Buffer[] = [], views: object[] = [], accs: object[] = [], mats: object[] = [], meshes: object[] = [], nodes: object[] = [];
  let off = 0;
  const push = (b: Buffer, target: number) => { views.push({ buffer: 0, byteOffset: off, byteLength: b.length, target }); bufs.push(b); off += b.length; return views.length - 1; };
  // glTF is Y up: (x, y, z) -> (x, z, -y)
  const toGl = (x: number, y: number, z: number): [number, number, number] => [x, z, -y];
  for (const [k, list] of groups) {
    const col = k.split(',').map(Number), pos = new Float32Array(list.length * 9), nor = new Float32Array(list.length * 9);
    const mn = [1e9, 1e9, 1e9], mx = [-1e9, -1e9, -1e9];
    list.forEach((t, i) => {
      const v = [0, 1, 2].map((q) => toGl(t[3 * q], t[3 * q + 1], t[3 * q + 2]));
      const e1 = [v[1][0] - v[0][0], v[1][1] - v[0][1], v[1][2] - v[0][2]], e2 = [v[2][0] - v[0][0], v[2][1] - v[0][1], v[2][2] - v[0][2]];
      let n = [e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]]; const l = Math.hypot(...n) || 1; n = n.map((c) => c / l);
      v.forEach((p, q) => { for (let c = 0; c < 3; c++) { pos[9 * i + 3 * q + c] = p[c]; nor[9 * i + 3 * q + c] = n[c]; mn[c] = Math.min(mn[c], p[c]); mx[c] = Math.max(mx[c], p[c]); } });
    });
    const pv = push(Buffer.from(pos.buffer), 34962), nv = push(Buffer.from(nor.buffer), 34962);
    accs.push({ bufferView: pv, componentType: 5126, count: list.length * 3, type: 'VEC3', min: mn, max: mx }, { bufferView: nv, componentType: 5126, count: list.length * 3, type: 'VEC3' });
    mats.push({ pbrMetallicRoughness: { baseColorFactor: col, metallicFactor: 0.1, roughness: 0.6 }, alphaMode: col[3] < 1 ? 'BLEND' : 'OPAQUE', doubleSided: true });
    meshes.push({ primitives: [{ attributes: { POSITION: accs.length - 2, NORMAL: accs.length - 1 }, material: mats.length - 1 }] });
    nodes.push({ mesh: meshes.length - 1 });
  }
  let bin = Buffer.concat(bufs); while (bin.length % 4) bin = Buffer.concat([bin, Buffer.alloc(1)]);
  const json = { asset: { version: '2.0', generator: 'pond control-ui export-transplant' }, scene: 0, scenes: [{ nodes: nodes.map((_, i) => i) }], nodes, meshes, materials: mats, accessors: accs, bufferViews: views, buffers: [{ byteLength: bin.length }] };
  let js = Buffer.from(JSON.stringify(json)); while (js.length % 4) js = Buffer.concat([js, Buffer.from(' ')]);
  const head = Buffer.alloc(12), jh = Buffer.alloc(8), bh = Buffer.alloc(8);
  head.writeUInt32LE(0x46546c67, 0); head.writeUInt32LE(2, 4); head.writeUInt32LE(12 + 8 + js.length + 8 + bin.length, 8);
  jh.writeUInt32LE(js.length, 0); jh.writeUInt32LE(0x4e4f534a, 4); bh.writeUInt32LE(bin.length, 0); bh.writeUInt32LE(0x004e4942, 4);
  return Buffer.concat([head, jh, js, bh, bin]);
}

const run = new TransplantRun();
run.reset();
const round = (t: Tri[]) => t.map((r) => r.map((v, i) => (i < 9 ? +v.toFixed(4) : v)));
const stages: { id: string; label: string }[] = [{ id: 'step0', label: 'Start' }];
bind.apply(run.pose);
writeFileSync(join(out, 'step0.glb'), glb(triangles()));
writeFileSync(join(out, 'step0.json'), JSON.stringify(round(triangles())));
for (let s = 0; s < STEPS.length; s++) {
  run.step();
  let t = 0, nextFrame = 0, f = 0;
  const frames: Tri[][] = [];
  while (run.busy) {
    run.advance(0.01); t += 0.01; bind.apply(run.pose);
    if (t >= nextFrame) { frames.push(round(triangles())); nextFrame += 0.5; f++; }
  }
  bind.apply(run.pose);
  const id = `step${s + 1}`;
  stages.push({ id, label: STEPS[s].title });
  writeFileSync(join(out, `${id}.glb`), glb(triangles()));
  writeFileSync(join(out, `${id}.json`), JSON.stringify(round(triangles())));
  writeFileSync(join(out, `${id}-frames.json`), JSON.stringify(frames));
  console.log(id, STEPS[s].title, `${t.toFixed(1)} s, ${f} frames`);
}
writeFileSync(join(out, 'stages.json'), JSON.stringify({ stages, holeOpenS: run.holeTimes }));
