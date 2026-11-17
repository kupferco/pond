// Exports the Reach test scene for pictures: runs the reach test, colours the plugs and pods (green / amber / red), and writes a GLB of the whole scene and a triangle list (JSON) for
// scripts/render_reach.py, for the coloured result with the arm folded and for one example pod the arm reaches (its pose from the test), plus table.json (the table).
// Usage: node --experimental-strip-types scripts/export-reach.ts OUT_DIR
import loadMujoco from '@mujoco/mujoco';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { reachMjcf } from '../src/reach/layout.ts';
import { Rig, colourParts, runReach, summary } from '../src/reach/test.ts';
import { checkPass } from '../src/reach/pass.ts';
import { JAW_CAP_DEG } from '../src/transplant/layout.ts';
import { glb, triangles } from './tri-export.ts';

const out = process.argv[2];
if (!out) throw new Error('usage: export-reach.ts OUT_DIR');
mkdirSync(out, { recursive: true });
const mj = await loadMujoco();
const model = mj.MjModel.from_xml_string(reachMjcf());
const data = new mj.MjData(model);
const results = runReach(mj, model, data);
const passes = checkPass(mj, model, data, [0, 90, 180, 270]);
colourParts(model, results);
const rig = new Rig(mj, model, data);
const round = (t: number[][]) => t.map((r) => r.map((v, i) => (i < 9 ? +v.toFixed(4) : v)));
const write = (id: string) => { const t = triangles(mj, model, data); writeFileSync(join(out, id + '.glb'), glb(t, 'pond control-ui export-reach')); writeFileSync(join(out, id + '.json'), JSON.stringify(round(t))); };
rig.pose(false, 0.63, { A: 0, B: 0, C: 0, D: 0, E: 0 });
write('result');
const ex = results.find((t) => t.colour === 'green' && t.kind === 'pod')!;
rig.pose(false, ex.direct.cartZ!, ex.direct.joints!, JAW_CAP_DEG);
write('example');
writeFileSync(join(out, 'table.json'), JSON.stringify({ summary: summary(results), example: ex.id, results, passes }, null, 1));
console.log(JSON.stringify(summary(results)), 'example', ex.id);
