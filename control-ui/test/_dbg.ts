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
const task = new PodTask(world, cmd, { jobs: fillJobs(world), seed: 1 });
let prev = world.pos(1), n = 0;
while (!task.done) { task.advance(0.002); const p = world.pos(1); if (task.jobIndex === 1 && task.time > 20.5) { if (n++ < 40 || task.done) console.log(task.time.toFixed(3), task.label, world.pods[1].state, p.map((v) => (v*1000).toFixed(2)).join(' '), 'pin', world.pin().map((v) => (v*1000).toFixed(2)).join(' ')); } prev = p; }
