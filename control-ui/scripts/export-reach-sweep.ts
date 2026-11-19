// Exports the cart-turned-90-degrees round of the Reach test (OpenPocket #313) for pictures: the sweep, parts coloured by it (green: reached at 270 degrees, amber: at another angle, red: at none),
// the cart turned 90 degrees ccw on leg A (arm folded) and the arm on one hole it reaches, GLB + triangle JSON for scripts/render_reach.py, and sweep.json / sweep.md (the tables).
// Usage: node --experimental-strip-types scripts/export-reach-sweep.ts OUT_DIR
import loadMujoco from '@mujoco/mujoco';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { reachMjcf } from '../src/reach/layout.ts';
import { Rig, colourParts, type Target } from '../src/reach/test.ts';
import { TURN_90, runSweep } from '../src/reach/sweep.ts';
import { stations } from '../src/reach/station.ts';
import { JAW_CAP_DEG } from '../src/transplant/layout.ts';
import { glb, triangles } from './tri-export.ts';

const out = process.argv[2];
if (!out) throw new Error('usage: export-reach-sweep.ts OUT_DIR');
mkdirSync(out, { recursive: true });
const mj = await loadMujoco();
const model = mj.MjModel.from_xml_string(reachMjcf()), data = new mj.MjData(model);
const sw = await runSweep(mj, model, data);
colourParts(model, sw.targets.map((t) => ({ id: t.id, kind: t.kind, colour: t.colour90 })) as unknown as Target[]);
const rig = new Rig(mj, model, data), FOLD = { A: 0, B: 0, C: 0, D: 0, E: 0 };
const round = (t: number[][]) => t.map((r) => r.map((v, i) => (i < 9 ? +v.toFixed(4) : v)));
const write = (id: string) => { const t = triangles(mj, model, data); writeFileSync(join(out, id + '.glb'), glb(t, 'pond control-ui export-reach-sweep')); writeFileSync(join(out, id + '.json'), JSON.stringify(round(t))); };
rig.pose(stations('leg A', TURN_90).find((s) => Math.abs(s.at - 1.0) < 1e-6)!, FOLD); write('turn90');
const ex = sw.targets.find((t) => t.cell90.withNeighbour.ok)!;
rig.pose(ex.cell90.own.station!, ex.cell90.own.joints!, JAW_CAP_DEG); write('turn90-example');
writeFileSync(join(out, 'sweep.json'), JSON.stringify(sw, null, 1));
const w = (c: (typeof sw.targets)[0]['cell90']) => (c.withNeighbour.ok ? `reaches (${c.own.station!.at.toFixed(2)} m, ${c.own.margin!.toFixed(0)}° margin)` : c.own.ok ? `neighbour: ${c.withNeighbour.detail}` : `${c.own.reason}: ${c.own.detail}`);
const md = ['| Part | Colour | Cart turned 270° (90° ccw) | Best angle | All angles |', '|---|---|---|---|---|', ...sw.targets.map((t) => `| ${t.id} | ${t.colour90} | ${w(t.cell90)} | ${t.best ? t.best.roll + '°' : '-'} | ${t.cells.filter((c) => c.own.ok).map((c) => c.roll).join(', ') || '-'} |`)];
writeFileSync(join(out, 'sweep.md'), md.join('\n') + '\n');
console.log('example', ex.id, 'most', sw.mostRoll);
