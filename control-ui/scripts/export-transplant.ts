// Exports the Transplant scene for pictures: runs the four steps headless and writes, for the start and after each step, a GLB of the whole scene (for the 3D viewer), plus triangle lists
// (JSON) of those poses and of frames through every step, which scripts/render_tris.py turns into PNGs and clips (there is no GPU here, so the pictures are drawn by a small software renderer).
// Usage: node --experimental-strip-types scripts/export-transplant.ts OUT_DIR
import loadMujoco from '@mujoco/mujoco';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { BODIES, transplantMjcf } from '../src/transplant/layout.ts';
import { Binder } from '../src/transplant/apply.ts';
import { STEPS, TransplantRun } from '../src/transplant/task.ts';
import { glb as glb0, triangles as triangles0, type Tri } from './tri-export.ts';
const glb = (t: Tri[]) => glb0(t, 'pond control-ui export-transplant');

const out = process.argv[2];
if (!out) throw new Error('usage: export-transplant.ts OUT_DIR');
mkdirSync(out, { recursive: true });
const mj = await loadMujoco();
const model = mj.MjModel.from_xml_string(transplantMjcf());
const data = new mj.MjData(model);
const bind = new Binder(mj, model, data);

// Drawings only (OpenPocket #459, owner review): the cart faces the FRONT of the unit and the one insertion is at the front. The sim's arm works from the track towards the pipe; the picture is the sim turned about
// the y axis (x -> -x, a mirror), so the arm, the seedling tray and the hole all face +x (the unit's front) and nothing in the sim changes. The plug holder and the parked plug are left out (one insertion only).
const plugBody = model.body(BODIES.plug).id;
let plugParked = false;
const hidden = (g: number) => (model.geom(g).name ?? '').startsWith('holder_') || (plugParked && model.geom_bodyid[g] === plugBody);
const mirror = (t: Tri[]): Tri[] => t.map((r) => [-r[0], r[1], r[2], -r[6], r[7], r[8], -r[3], r[4], r[5], ...r.slice(9)]);   // x -> -x, and two vertices swapped to keep the winding
const triangles = () => mirror(triangles0(mj, model, data, hidden));
const run = new TransplantRun();
run.reset();
const round = (t: Tri[]) => t.map((r) => r.map((v, i) => (i < 9 ? +v.toFixed(4) : v)));
const stages: { id: string; label: string }[] = [{ id: 'step0', label: 'Start' }];
bind.apply(run.pose); plugParked = run.pose.places.plug === 'park';
writeFileSync(join(out, 'step0.glb'), glb(triangles()));
writeFileSync(join(out, 'step0.json'), JSON.stringify(round(triangles())));
for (let s = 0; s < STEPS.length; s++) {
  run.step();
  let t = 0, nextFrame = 0, f = 0;
  const frames: Tri[][] = [];
  while (run.busy) {
    run.advance(0.01); t += 0.01; bind.apply(run.pose); plugParked = run.pose.places.plug === 'park';
    if (t >= nextFrame) { frames.push(round(triangles())); nextFrame += 0.5; f++; }
  }
  bind.apply(run.pose); plugParked = run.pose.places.plug === 'park';
  const id = `step${s + 1}`;
  stages.push({ id, label: STEPS[s].title });
  writeFileSync(join(out, `${id}.glb`), glb(triangles()));
  writeFileSync(join(out, `${id}.json`), JSON.stringify(round(triangles())));
  writeFileSync(join(out, `${id}-frames.json`), JSON.stringify(frames));
  console.log(id, STEPS[s].title, `${t.toFixed(1)} s, ${f} frames`);
}
writeFileSync(join(out, 'stages.json'), JSON.stringify({ stages, holeOpenS: run.holeTimes }));
