// Exports the Reach test scene for pictures: runs the reach test, colours the plugs and pods (green / amber / red), and writes a GLB of the whole scene and a triangle list (JSON) for
// scripts/render_reach.py, for the coloured result with the arm folded and for one example pod the arm reaches (its pose from the test), plus table.json (the table).
// Usage: node --experimental-strip-types scripts/export-reach.ts OUT_DIR
import loadMujoco from '@mujoco/mujoco';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { reachMjcf } from '../src/reach/layout.ts';
import { Rig, colourParts, runReach, summary, type Target } from '../src/reach/test.ts';
import { stations } from '../src/reach/station.ts';
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
const HOME = stations('leg A', 180).find((s) => Math.abs(s.at - 1.0) < 1e-6)!;   // the pose shown by default: rolled 180 degrees about leg A's own axis, 1.0 m
rig.pose(HOME, { A: 0, B: 0, C: 0, D: 0, E: 0 });
write('result');
// the cart as it is and rolled 180 degrees about leg A, arm folded, at the same height, to show which way the arm faces
rig.pose(stations('leg A', 0).find((s) => Math.abs(s.at - 1.0) < 1e-6)!, { A: 0, B: 0, C: 0, D: 0, E: 0 }); write('cart-asis');
rig.pose(HOME, { A: 0, B: 0, C: 0, D: 0, E: 0 }); write('cart-rolled');
// an example the arm reaches: the first green or amber part, else the first red one that works at another roll angle
const ex = results.find((t) => t.colour !== 'red') ?? results.find((t) => t.other.ok)!;
const exA = ex.colour === 'green' ? ex.direct : ex.colour === 'amber' ? ex.rolled : ex.other;
rig.pose(exA.station!, exA.joints!, JAW_CAP_DEG);
write('example');
writeFileSync(join(out, 'table.json'), JSON.stringify({ summary: summary(results), example: ex.id, exampleStation: exA.station!.label, results, passes }, null, 1));
const word = (a: Target['direct']) => (a.ok ? `reachable: ${a.station!.label}` : `${a.reason}: ${a.detail}`);
const md = ['| Part | Colour | As is (best station) | Rolled 180° (best station) | Any other roll |', '|---|---|---|---|---|', ...results.map((t) => `| ${t.id} | ${t.colour} | ${word(t.direct)} | ${word(t.rolled)} | ${t.colour === 'red' ? word(t.other) : '-'} |`)];
writeFileSync(join(out, 'table.md'), md.join('\n') + '\n');
console.log(JSON.stringify(summary(results)), 'example', ex.id, exA.station!.label);
