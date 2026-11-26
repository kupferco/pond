// Pod grab: clearance sweep of the cart along the whole pipe and one pick-and-place to every tray socket (OpenPocket #461).
// Usage: node --experimental-strip-types scripts/check-podgrab.ts
import loadMujoco from '@mujoco/mujoco';
import { SimDriver } from '../src/drivers/simDriver.ts';
import { RealDriver } from '../src/drivers/realDriver.ts';
import { CommandLayer } from '../src/commands.ts';
import { podGrabMjcf, TRAY_SLOTS, STORE_ROWS, slotLabel } from '../src/podgrab/layout.ts';
import { PodTask, PodWorld, fillJobs } from '../src/podgrab/task.ts';
import { cartCloud, clashesAt } from '../src/podgrab/clearance.ts';

const mj = await loadMujoco();
const sim = new SimDriver(mj, podGrabMjcf());
const cmd = new CommandLayer(sim, new RealDriver());
const world = new PodWorld(sim);
for (let i = 0; i < 1500; i++) sim.step();
const cloud = cartCloud(sim);   // all the cart's CAD points (also those on the tank side of the pipe: they are tested against the station and the lid)
const bad: string[] = []; let n = 0;
for (let x = -0.33; x <= 0.2801; x += 0.005) { n++; for (const c of clashesAt(cloud, x, ['spine', 'bracket', 'rod', 'pipe', 'station', 'lid'], 0.0005)) bad.push(`${(x * 100).toFixed(1)} cm ${c.obstacle} ${(c.depth * 1000).toFixed(1)} mm (${c.part})`); }
console.log(`sweep: ${n} stops from -33 to +28 cm, ${bad.length} clashes`);
const byObs = new Map<string, { n: number; max: number; x0: number; x1: number }>();
for (const b of bad) { const [x, , o, d] = b.split(' '); const k = o; const e = byObs.get(k) ?? { n: 0, max: 0, x0: 9, x1: -9 }; e.n++; e.max = Math.max(e.max, +d); e.x0 = Math.min(e.x0, +x); e.x1 = Math.max(e.x1, +x); byObs.set(k, e); }
for (const [k, e] of byObs) console.log(`  ${k}: ${e.n} stops, deepest ${e.max} mm, from ${e.x0} to ${e.x1} cm`);
if (process.argv[2] !== 'nofill') {
  let ok = 0;
  for (let s = 0; s < TRAY_SLOTS; s++) {
    world.reset();
    const task = new PodTask(world, cmd, { jobs: [{ row: s % STORE_ROWS, slot: s }], seed: 1 });
    while (!task.done) task.advance(0.5);
    const r = task.results[0];
    console.log(`socket ${slotLabel(s)} (store lane ${s % STORE_ROWS + 1}): ${task.failReason === '' && r?.success ? 'ok' : 'FAIL ' + task.failReason}`);
    if (task.failReason === '' && r?.success) ok++;
  }
  console.log(`single picks reaching their socket: ${ok}/${TRAY_SLOTS}`);
  world.reset();
  const task = new PodTask(world, cmd, { jobs: fillJobs(world), seed: 7 });
  while (!task.done) task.advance(0.5);
  console.log(`Fill the whole tray: ${world.trayCount}/${TRAY_SLOTS} ${task.failReason}`);
}
