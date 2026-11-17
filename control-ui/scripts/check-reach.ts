// Runs the Reach test (src/reach/test.ts) headless and prints the result for all 24 holes and 16 pods, as_is and rolled 180 degrees.
// Usage: node --experimental-strip-types scripts/check-reach.ts [out.json]
import loadMujoco from '@mujoco/mujoco';
import { writeFileSync } from 'node:fs';
import { reachMjcf } from '../src/reach/layout.ts';
import { runReach, summary, whyRed, type Target } from '../src/reach/test.ts';

const mj = await loadMujoco();
const model = mj.MjModel.from_xml_string(reachMjcf());
const data = new mj.MjData(model);
const t0 = Date.now();
const res = runReach(mj, model, data);
const fmt = (a: Target['direct']) => (a.ok ? `ok at ${a.cartZ!.toFixed(3)} m (margin ${a.margin!.toFixed(0)}°)` : `${a.reason}: ${a.detail}`) + (a.looseErr !== undefined ? ` [position ok, hand ${a.looseErr.toFixed(0)}° off at ${a.looseZ!.toFixed(2)} m]` : '');
for (const x of res) console.log(`${x.id.padEnd(4)} ${x.colour.padEnd(6)} as is: ${fmt(x.direct)} | rolled: ${fmt(x.rolled)}`);
console.log(JSON.stringify(summary(res)), `${((Date.now() - t0) / 1000).toFixed(0)} s`);
if (process.argv[2]) writeFileSync(process.argv[2], JSON.stringify(res, null, 1));
void whyRed;
import { checkPass } from '../src/reach/pass.ts';
console.log('--- passing the spine bracket and the pipe on the track\'s top and bottom run (arm stowed): which rolls about the run touch what');
for (const r of checkPass(mj, model, data, [0, 45, 90, 135, 180, 225, 270, 315])) console.log(`${r.run.padEnd(6)} run, rolled ${String(r.roll).padStart(3)}°: bracket ${r.bracket ? `TOUCHED (${(-r.bracketWorst * 1000).toFixed(1)} mm, ${r.bracketNames})` : 'clear'}, pipe/collars ${r.pipe ? 'TOUCHED' : 'clear'}, rest ${r.other ? 'TOUCHED' : 'clear'}${r.worst < 0 ? ` (worst ${(-r.worst * 1000).toFixed(1)} mm: ${r.names})` : ''}`);
