// Exports the Pod grab scene on the omni cart for pictures (OpenPocket #284): poses of one pick-and-place (store row 3 to socket A1) and the cart standing at the spine, as triangle lists
// (JSON, for scripts/render_scene_stages.py: there is no GPU here) and GLBs of the whole scene (for the 3D viewer).
// Usage: node --experimental-strip-types scripts/export-podgrab.ts OUT_DIR
import loadMujoco from '@mujoco/mujoco';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { SimDriver } from '../src/drivers/simDriver.ts';
import { RealDriver } from '../src/drivers/realDriver.ts';
import { CommandLayer } from '../src/commands.ts';
import { CART_QUAT, CART_Z, PIPE_Y, PIPE_Z, podGrabMjcf, armR, armU, seatPos, storePos, trayX, TRANSIT_Z, TRANSIT_PITCH, STORE_PITCH_DEG } from '../src/podgrab/layout.ts';
import { probe } from '../src/podgrab/reach.ts';
import { MOTORS } from '../src/model.ts';
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
snap('1-start', 'Start: the whole unit as in the Transplant drawings: spine on the tank centre, the unit loop, the cart on its bottom run', `cart x ${world.cartX.toFixed(2)} m`, [0, 0, 0.95], 1.1);
const task = new PodTask(world, cmd, { jobs: [{ row: 2, slot: 0 }], seed: 1 });
const want = new Map<string, [string, string]>([
  ['Closing the claw on the pod', ['2-pick', 'Pick: the claw is down through the lid slot round the pod on the landing, store lane 3']],
  ['Driving to cell A1', ['3-carry', 'Carry: pod lifted out through the lid slot, the cart drives to the tray']],
  ['Lowering the pod through the lid slot onto the tray', ['4-place', 'Place: the pod lowered through the lid slot onto cell A1 of the seedling tray']],
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
snap('5-done', 'End of the pick-and-place: store lane 3 to cell A1', task.failReason === '' ? 'seated' : task.failReason, [0, 0, 0.5], 0.6);
// mid-reach to tray row D and the store pick (#461): the arm is put at the IK pose of the waypoint with every joint held inside its limit, so the picture shows how far it gets
const reachPose = (id: string, label: string, x: number, z: number, y: number, pitch: number, centre: number[], half: number) => {
  world.reset();
  const p = probe(armR(z), armU(y), pitch);
  const j = p.joints!;
  const h = sim.model.opt.timestep;
  world.setCart(x);
  for (let k = 0; k < 4000; k++) {
    for (const m of MOTORS.slice(0, 4)) cmd.setJointTarget(m.id, Math.max(m.min + 0.5, Math.min(m.max - 0.5, j[m.id])));
    sim.step(); world.tick(h);
  }
  snap(id, label, `shoulder to wrist ${(p.d * 1000).toFixed(0)} mm, ${p.ok ? 'inside the joint limits' : 'joints held at their limit (the waypoint is out of reach)'}`, centre, half);
};
const D1 = seatPos(15);   // C4: the far row of the tray, the one the arm reaches least well
// mid-reach to a cell of the last row (C4): the pod carried over the cell with the claw tilted as the task does (TRANSIT_PITCH)
const tilt = TRANSIT_PITCH;
reachPose('2-reach-row-c', `Mid-reach to tray row C (cell C4): the pod carried over the cell with the claw tilted ${tilt} degrees (the arm cannot hold it upright at lid height)`, trayX(3), TRANSIT_Z, D1[1], tilt, [trayX(3), -0.1, 0.4], 0.4);
const P0 = storePos(0, 0);
reachPose('3-store-pick', 'The store pick: the claw down through the lid slot round the pod on the landing', P0[0], P0[2], P0[1], STORE_PITCH_DEG, [P0[0], -0.1, 0.35], 0.3);
// the spine crossing (#461): the sleeves are turned so their 18 mm slot faces the bracket; the cart at three stops across the spine (arm at its ready pose), close up
world.reset();
for (const [id, x] of [['6-spine-m10', -0.1], ['7-spine-0', 0], ['8-spine-p10', 0.1]] as const) {
  sim.setMocap('cart', [x, PIPE_Y, CART_Z], CART_QUAT);
  const probe = world.probeCart(x);
  snap(id, `The cart at ${x * 100} cm: the bracket goes through the slot of the sleeves`, `spine ${(-probe.by.spine_tube * 1000).toFixed(1)} mm, bracket ${(-probe.by.track_bracket * 1000).toFixed(1)} mm`, [0, PIPE_Y, PIPE_Z - 0.06], 0.26);
}
// the pod store under the lid (#461): the 15 degree ramp with its flat landing at the front, the whole store under the lid
world.reset();
snap('9-store', 'The pod store: the whole store sits under the lid; the pods slide down the ramp to the landing under the lid slot', 'slope 15 degrees', [0.175, 0, 0.26], 0.24);
writeFileSync(join(out, 'stages.json'), JSON.stringify(list));
