// Runs the roll sweep (src/reach/sweep.ts) headless: the cart turned 90 degrees on leg A and every roll in 15-degree steps, best angle per hole and pod, clashes on the way.
// Usage: node --experimental-strip-types scripts/check-sweep.ts [out.json]
import loadMujoco from '@mujoco/mujoco';
import { writeFileSync } from 'node:fs';
import { reachMjcf } from '../src/reach/layout.ts';
import { TURN_90, TURN_90_FROM_ZERO, runSweep, clashWords } from '../src/reach/sweep.ts';

const mj = await loadMujoco();
const model = mj.MjModel.from_xml_string(reachMjcf()), data = new mj.MjData(model);
const t0 = Date.now();
const sw = await runSweep(mj, model, data);
const f = (c: { own: { ok: boolean; margin?: number; reason?: string; detail?: string }; withNeighbour: { ok: boolean } }) => (c.own.ok ? (c.withNeighbour.ok ? `ok ${c.own.margin!.toFixed(0)}°` : 'ok, NEIGHBOUR') : `${c.own.reason}`);
for (const t of sw.targets) console.log(`${t.id.padEnd(4)} ${t.colour90.padEnd(6)} best ${t.bestAngle === null ? '-' : t.bestAngle + '°'} | 270: ${f(t.cell90)} | 90: ${f(t.cells.find((c) => c.roll === TURN_90_FROM_ZERO)!)}`);
console.log('roll  holes(own/with neighbour) pods(own/with neighbour)');
for (const c of sw.counts) console.log(`${String(c.roll).padStart(3)}  ${c.holes}/${c.holesClear}  ${c.pods}/${c.podsClear}`);
console.log('most (clear of neighbour):', sw.mostRoll, 'pose clashes after recheck:', sw.poseClashes);
for (const t of sw.travel) console.log(`travel roll ${String(t.roll).padStart(3)}: ${t.touches.length ? t.touches.join(', ') + ' | ' + t.where : 'clear'}`);
console.log(`${((Date.now() - t0) / 1000).toFixed(0)} s`, TURN_90, clashWords([]));
if (process.argv[2]) writeFileSync(process.argv[2], JSON.stringify(sw, null, 1));
