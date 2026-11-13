import loadMujoco from '@mujoco/mujoco';
import { SimDriver } from '../src/drivers/simDriver.ts';
import { RealDriver } from '../src/drivers/realDriver.ts';
import { CommandLayer } from '../src/commands.ts';
import { podGrabMjcf } from '../src/podgrab/layout.ts';
import { PodTask, PodWorld, fillJobs } from '../src/podgrab/task.ts';
const mj = await loadMujoco();
const pg = new SimDriver(mj, podGrabMjcf());
const cmd = new CommandLayer(pg, new RealDriver());
const world = new PodWorld(pg);
for (let i = 0; i < 1500; i++) pg.step();
console.log('rows', [0,1,2,3,4,5].map((r) => world.rowCount(r)).join());
const full = process.argv[2] === 'full';
const task = new PodTask(world, cmd, { jobs: full ? fillJobs(world) : [{ row: 2, slot: 0 }], seed: 1 });
let last = '';
while (!task.done) { task.advance(0.1); if (task.label !== last) { last = task.label; console.log(task.time.toFixed(1), last, task.jobIndex); } }
console.log('done', task.failReason, world.trayCount, world.violation, task.results.map((r) => r.posErrMm).join());
console.log(task.label, task.time.toFixed(2), task.jobIndex);
