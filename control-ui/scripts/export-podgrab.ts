// Exports the Pod grab scene on the omni cart for pictures (OpenPocket #284): poses of one pick-and-place (store row 3 to socket A1) and the cart standing at the spine, as triangle lists
// (JSON, for scripts/render_scene_stages.py: there is no GPU here) and GLBs of the whole scene (for the 3D viewer).
// Usage: node --experimental-strip-types scripts/export-podgrab.ts OUT_DIR
import loadMujoco from '@mujoco/mujoco';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { SimDriver } from '../src/drivers/simDriver.ts';
import { RealDriver } from '../src/drivers/realDriver.ts';
import { CommandLayer } from '../src/commands.ts';
import { CART_QUAT, CART_Z, PIPE_Y, PIPE_Z, podGrabMjcf } from '../src/podgrab/layout.ts';
import { PodTask, PodWorld } from '../src/podgrab/task.ts';
import { glb, triangles, type Tri } from './tri-export.ts';

const out = process.argv[2];
if (!out) throw new Error('usage: export-podgrab.ts OUT_DIR');
mkdirSync(out, { recursive: true });
const mj = await loadMujoco();
const sim = new SimDriver(mj, podGrabMjcf());
const cmd = new CommandLayer(sim, new RealDriver());
const world = new PodWorld(sim);
for (let i = 0; i < 1500; i++) sim.step();   // let the store settle
const round = (t: Tri[]) => t.map((r) => r.map((v, i) => (i < 9 ? +v.toFixed(4) : v)));
const list: object[] = [];
const snap = (id: string, label: string, note = '', centre = [0, 0.0, 0.42], half = 0.5) => {
  mj.mj_forward(sim.model, sim.data);
  const tris = triangles(mj, sim.model, sim.data);
  writeFileSync(join(out, id + '.json'), JSON.stringify(round(tris)));
  writeFileSync(join(out, id + '.glb'), glb(tris, 'pond control-ui export-podgrab'));
  list.push({ id, label, note, centre, half });
  console.log(id, label, note);
};
snap('1-start', 'Start: cart on the bottom pipe, arm raised, over the tank', `cart x ${world.cartX.toFixed(2)} m`);
const task = new PodTask(world, cmd, { jobs: [{ row: 2, slot: 0 }], seed: 1 });
const want = new Map<string, [string, string]>([
  ['Closing the claw on the pod', ['2-pick', 'Pick: the claw is down through the lid hole round the pod, cart at store row 3']],
  ['Driving to socket A1', ['3-carry', 'Carry: pod lifted out, the cart drives to the tray']],
  ['Lowering the pod through the lid into the silicone collar', ['4-place', 'Place: the pod lowered into socket A1 of the seedling tray']],
]);
const seen = new Set<string>();
while (!task.done) {
  task.advance(0.02);
  const hit = want.get(task.label);
  if (hit && !seen.has(task.label)) {
    seen.add(task.label);
    // the pod and the claw are where the move starts; run the move a little so the picture shows the action, not the first frame
    snap(hit[0], hit[1], `cart x ${world.cartX.toFixed(2)} m`);
  }
}
snap('5-done', 'Done: pod seated in the tray', task.failReason === '' ? 'seated' : task.failReason);
// the spine crossing (#461): the sleeves are turned so their 18 mm slot faces the bracket; the cart at three stops across the spine (arm at its ready pose), close up
world.reset();
for (const [id, x] of [['6-spine-m10', -0.1], ['7-spine-0', 0], ['8-spine-p10', 0.1]] as const) {
  sim.setMocap('cart', [x, PIPE_Y, CART_Z], CART_QUAT);
  const probe = world.probeCart(x);
  snap(id, `The cart at ${x * 100} cm: the bracket goes through the slot of the sleeves`, `spine ${(-probe.by.spine_tube * 1000).toFixed(1)} mm, bracket ${(-probe.by.track_bracket * 1000).toFixed(1)} mm`, [0, PIPE_Y, PIPE_Z - 0.06], 0.26);
}
writeFileSync(join(out, 'stages.json'), JSON.stringify(list));
