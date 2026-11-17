// Exports the Transplant scene for pictures: runs the four steps headless and writes, for the start and after each step, a GLB of the whole scene (for the 3D viewer), plus triangle lists
// (JSON) of those poses and of frames through every step, which scripts/render_tris.py turns into PNGs and clips (there is no GPU here, so the pictures are drawn by a small software renderer).
// Usage: node --experimental-strip-types scripts/export-transplant.ts OUT_DIR
import loadMujoco from '@mujoco/mujoco';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { transplantMjcf } from '../src/transplant/layout.ts';
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

const triangles = () => triangles0(mj, model, data);
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
