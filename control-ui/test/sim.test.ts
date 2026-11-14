// Headless check of the sim and command layer (node, no browser).
import loadMujoco from '@mujoco/mujoco';
import { SimDriver } from '../src/drivers/simDriver.ts';
import { RealDriver } from '../src/drivers/realDriver.ts';
import { CommandLayer } from '../src/commands.ts';

import { SCENE_INFOS, resolveSceneId } from '../src/scenes/list.ts';
import { Attempt } from '../src/arm/attempt.ts';
import { graspPoint, solveDown } from '../src/arm/kinematics.ts';
import { clampToReach, farEnough, inReach, randomPlacement } from '../src/arm/placement.ts';
import { trajectoryJson, gzipJson } from '../src/arm/trajectory.ts';
import { CartMotion, L_ARC, L_VERT, TRACK_LENGTH_CM, frameQuat, pathAt, randomTarget } from '../src/cart/track.ts';
import { cartMjcf } from '../src/cart/model.ts';
import { BASE_BOTTOM, LID_Z, PIPE_Z, SPINE_Y, POD_COUNT, POD_PITCH, ROW_PITCH, ROW_X0, SPINE_R, STORE_CAP, STORE_ROWS, STORE_START, TRAY_CX, TRAY_HX, TRAY_SLOTS, podGrabMjcf, seatPos, storePos } from '../src/podgrab/layout.ts';
import { PodTask, PodWorld, fillJobs } from '../src/podgrab/task.ts';
import { HOLD_DEG, POD_D, REACH } from '../src/arm/dims.ts';

const MOTORS_JOINT: Record<string, string> = { A: 'shoulder_pan', B: 'shoulder_lift', C: 'elbow_flex', D: 'wrist_flex', E: 'wrist_roll' };
const mj = await loadMujoco();
const sim = new SimDriver(mj);
const cmd = new CommandLayer(sim, new RealDriver());
const run = (s: number) => { for (let i = 0; i < s / 0.002; i++) mj.mj_step(sim.model, sim.data); };
let fail = 0;
const check = (name: string, ok: boolean, info = '') => { console.log(ok ? 'ok  ' : 'FAIL', name, info); if (!ok) fail++; };

run(1);
const rest = sim.readJoints();
check('home holds near 0 under gravity', Math.abs(rest.B) < 3 && Math.abs(rest.C) < 3, JSON.stringify(rest));

check('clamps to joint limit', cmd.setJointTarget('A', 500) === 110);
cmd.setJointTarget('A', 25);
run(1.5);
check('motor A reaches 25 deg', Math.abs(sim.readJoints().A - 25) < 1, String(sim.readJoints().A));

cmd.setAllTargets({ B: 40, C: -30, D: 20, E: 90, F: 50 });
run(2);
const j = sim.readJoints();
check('go-all reaches pose', Math.abs(j.B - 40) < 4 && Math.abs(j.C + 30) < 4 && Math.abs(j.E - 90) < 2 && Math.abs(j.F - 50) < 2, JSON.stringify(j));

cmd.home();
run(2.5);
const h = sim.readJoints();
check('home returns', Object.values(h).every((v) => Math.abs(v) < 3), JSON.stringify(h));

let msg = '';
try { await cmd.setMode('real'); } catch (e) { msg = (e as Error).message; }
check('real mode refuses, stays on sim', msg.includes('not connected') && cmd.mode === 'sim');

check('seven scenes, two groups', SCENE_INFOS.length === 7 && SCENE_INFOS.filter((s) => s.group === 'Tests').length === 5);
check('scene default is arm', resolveSceneId('', null) === 'arm');
check('scene URL wins over stored', resolveSceneId('?scene=cart', 'pillar') === 'cart');
check('stored scene used without URL', resolveSceneId('', 'pillar') === 'pillar');
check('bad scene falls back', resolveSceneId('?scene=nope', 'zzz') === 'arm');

// --- Arm scene: kinematics, placement, scripted task, trajectory ---------------------------------
{
  // IK solution put through MuJoCo's own forward kinematics lands on the requested grasp point.
  let worst = 0, unreachable = 0;
  for (const [r, a, z] of [[0.12, 0, 0.02], [0.2, 0, 0.02], [0.16, 60, 0.02], [0.2, -80, 0.056], [0.12, 80, 0.09], [0.2, 40, 0.09]]) {
    const x = r * Math.cos(a * Math.PI / 180), y = r * Math.sin(a * Math.PI / 180);
    const ik = solveDown(x, y, z);
    if (!ik) { unreachable++; continue; }
    sim.reset();
    for (const id of ['A', 'B', 'C', 'D', 'E']) sim.data.qpos[sim.model.jnt_qposadr[sim.model.jnt(MOTORS_JOINT[id]).id]] = (ik as any)[id] * Math.PI / 180;
    mj.mj_forward(sim.model, sim.data);
    const h = sim.bodyPose('hand');
    const gl = [0.068, 0, 0.0065];
    const g = [0, 1, 2].map((i) => h.pos[i] + h.rot[3 * i] * gl[0] + h.rot[3 * i + 1] * gl[1] + h.rot[3 * i + 2] * gl[2]);
    worst = Math.max(worst, Math.hypot(g[0] - x, g[1] - y, g[2] - z), Math.hypot(...(graspPoint(ik).map((v, i) => v - [x, y, z][i]) as [number, number, number])));
  }
  check('IK matches MuJoCo forward kinematics', unreachable === 0 && worst < 1e-4, `worst ${(worst * 1000).toFixed(3)} mm, unreachable ${unreachable}`);
  check('IK refuses out-of-reach points', solveDown(0.4, 0, 0.02) === null && solveDown(0.02, 0, 0.02) === null);
  check('jaws close on a pod width', Math.abs(Math.sin(HOLD_DEG * Math.PI / 180) * 0.048 - POD_D) < 1e-6);

  let okPlace = true;
  for (let s = 0; s < 200; s++) { const p = randomPlacement(s); okPlace &&= inReach(p.pod) && inReach(p.slot) && farEnough(p.pod, p.slot) && solveDown(p.pod[0], p.pod[1], 0.02) !== null && [0.02, 0.056, 0.08, 0.09].every((z) => solveDown(p.pod[0], p.pod[1], z) !== null && solveDown(p.slot[0], p.slot[1], z) !== null); }
  // Worst corners of the reach region at every height the controller uses.
  const corners: Array<[number, number]> = [[REACH.rMin, 0], [REACH.rMax, 0], [REACH.rMin, REACH.angMax], [REACH.rMax, REACH.angMax], [REACH.rMax, -REACH.angMax]];
  check('region corners reachable at all controller heights', corners.every(([r, a]) => [0.02, 0.056, 0.08, 0.09].every((z) => solveDown(r * Math.cos(a * Math.PI / 180), r * Math.sin(a * Math.PI / 180), z) !== null)));
  check('200 random placements are reachable and apart', okPlace);
  check('clampToReach lands inside the region', inReach(clampToReach([0.5, 0.5])) && inReach(clampToReach([0.01, 0])) && inReach(clampToReach([-0.2, 0])));
  const same = JSON.stringify(randomPlacement(7)) === JSON.stringify(randomPlacement(7));
  check('placement is deterministic per seed', same);

  const runOne = (seed: number) => {
    const p = randomPlacement(seed);
    const a = new Attempt(sim, cmd, { ...p, seed });
    while (!a.advance(1));
    return a;
  };
  const a1 = runOne(1);
  check('scripted pick-and-place seats the pod', a1.result!.success && a1.result!.posErrMm <= 3 && a1.result!.tiltErrDeg <= 5, JSON.stringify(a1.result));
  check('pod ends in the slot in the sim data', Math.hypot(...[0, 1].map((i) => sim.bodyPose('pod').pos[i] - sim.bodyPose('slot').pos[i])) < 0.003);
  const a1b = runOne(1);
  check('same seed, same result', JSON.stringify(a1.result) === JSON.stringify(a1b.result) && JSON.stringify(a1.samples) === JSON.stringify(a1b.samples));

  const phasesSeen = new Set(a1.samples.map((s) => s.ph));
  check('trajectory covers every phase and has held samples', [0, 1, 2, 3, 4, 5, 6, 7].every((p) => phasesSeen.has(p)) && a1.samples.some((s) => s.held) && a1.samples.length > 100);
  const traj = trajectoryJson(a1, { runId: 'abc12345', batchId: 'batch1234', batchIndex: 0, batchSize: 1, startedAt: 'x' });
  const blob = await gzipJson(traj);
  check('trajectory gzips well under the 300 kB rule limit', blob.size > 0 && blob.size < 100 * 1024, `${blob.size} bytes`);
  check('trajectory columns line up', traj.t.length === traj.q.length && traj.q.length === traj.cmd.length && traj.cmd.length === traj.pod.length && traj.pod[0].length === 7 && traj.q[0].length === 6);

  // A pod outside the reach region must fail cleanly, not hang or throw.
  const bad = new Attempt(sim, cmd, { pod: [0.35, 0], slot: [0.16, 0.08], seed: 3 });
  while (!bad.advance(1));
  check('unreachable pod fails with a reason', !bad.result!.success && bad.result!.reason.startsWith('unreachable'), bad.result!.reason);

  // Batch of randomized attempts: most succeed, and every outcome carries finite numbers.
  let ok = 0, finite = true;
  for (let i = 0; i < 20; i++) { const r = runOne(500 + i).result!; if (r.success) ok++; finite &&= Number.isFinite(r.posErrMm) && Number.isFinite(r.tiltErrDeg) && r.durationS > 0; }
  check('20 randomized attempts: at least 16 succeed', ok >= 16 && finite, `${ok}/20`);
  void REACH;
}

// Cart track: path continuity, clamping, motion and the model.
{
  let maxJump = 0, prev = pathAt(0);
  for (let s = 0.1; s <= TRACK_LENGTH_CM; s += 0.1) { const p = pathAt(s); maxJump = Math.max(maxJump, Math.hypot(p.x - prev.x, p.z - prev.z) * 100); prev = p; }
  check('cart path is continuous (0.1 cm steps move 0.1 cm)', maxJump < 0.1001, maxJump.toFixed(4));
  check('cart path sections', pathAt(L_VERT - 1).section === 'vertical' && pathAt(L_VERT + L_ARC / 2).section === 'curve' && pathAt(L_VERT + L_ARC + 1).section === 'horizontal');
  const mid = pathAt(L_VERT + L_ARC / 2);
  check('bend mid-point tangent is 45 deg', Math.abs(mid.tx - Math.SQRT1_2) < 1e-9 && Math.abs(mid.tz - Math.SQRT1_2) < 1e-9);
  check('path starts at the bottom and goes up', pathAt(5).z > pathAt(0).z && pathAt(0).tz === 1);
  check('path clamps at the ends', pathAt(-5).z === pathAt(0).z && pathAt(1e6).x === pathAt(TRACK_LENGTH_CM).x);
  const q = frameQuat(pathAt(TRACK_LENGTH_CM));
  check('horizontal end: half turn about x (body inside the bend, below the pipe)', Math.abs(q[1] - 1) < 1e-9 && Math.abs(q[3]) < 1e-9);
  const cm = new CartMotion(); cm.speed = 10;
  cm.nudge(5); cm.nudge(5);
  check('step taps accumulate', cm.goal === 10);
  let t = 0; while (cm.moving) { cm.advance(0.01); t += 0.01; }
  check('cart arrives at 10 cm in 1 s at 10 cm/s', cm.s === 10 && Math.abs(t - 1) < 0.02, `${cm.s} ${t.toFixed(2)}`);
  cm.nudge(-100);
  check('cart clamps at 0', cm.goal === 0);
  cm.moveTo(1e6);
  check('cart clamps at the far end', cm.goal === TRACK_LENGTH_CM);
  const rt = Array.from({ length: 50 }, (_, i) => randomTarget(i));
  check('random targets stay on the track and vary', rt.every((v) => v >= 0 && v <= TRACK_LENGTH_CM) && new Set(rt).size > 25);
  const cartModel = mj.MjModel.from_xml_string(cartMjcf());
  check('cart model loads with cart and marker mocap bodies', cartModel.nmocap === 2, String(cartModel.nmocap));
  cartModel.delete();
}

// Pod grab: the arm on the cart takes pods out of the sloped store rows and lowers them into the silicone collars of the 4 x 4 tray.
{
  const pg = new SimDriver(mj, podGrabMjcf());
  check('pod grab model has the cart as its one mocap body (the arm base is rigid in it); the pods are free bodies', pg.model.nmocap === 1 && pg.model.nbody > POD_COUNT, String(pg.model.nmocap));
  check('store holds enough pods for the tray', STORE_ROWS * STORE_START >= TRAY_SLOTS && STORE_START < STORE_CAP);
  check('unit layout: track 150 mm over the lid, store slopes down to the pick line, tray flat and left of the store',
    PIPE_Z - LID_Z > 0.14 && storePos(0, 1)[2] > storePos(0, 0)[2] && storePos(0, 1)[1] > storePos(0, 0)[1] && seatPos(0)[2] === seatPos(TRAY_SLOTS - 1)[2] && seatPos(TRAY_SLOTS - 1)[0] < ROW_X0);
  check('trays clear of the spine: seedling tray left of it, store right of it, neither touching',
    TRAY_CX + TRAY_HX < -SPINE_R - 0.05 && ROW_X0 - ROW_PITCH / 2 > SPINE_R + 0.02);
  {
    const names = podGrabMjcf();
    const baseBody = pg.model.body('base'), cartBody = pg.model.body('cart');
    check('arm base is a rigid child of the cart (no joint, no mocap of its own)',
      pg.model.body_parentid[baseBody.id] === cartBody.id && pg.model.body_jntnum[baseBody.id] === 0 && pg.model.body_mocapid[baseBody.id] === -1 && names.includes('xyaxes'));
    check('spine and brackets are in the scene', pg.model.ngeom > 200 && names.split('\n').filter((l) => l.includes('cylinder') && l.includes('fromto="0 ' + SPINE_Y)).length >= 1);
  }
  {
    const names = podGrabMjcf();
    check('spine is at least double the 33.7 mm tube', SPINE_R * 2 >= 2 * 0.0337);
    check('end effector is a two-finger claw (no pin)', pg.model.nu === 8 && names.includes('claw_l') && names.includes('claw_r') && !names.includes('name="pin"'));
    check('each store row has an end gate at the back', names.split('\n').filter((l) => l.includes('rgba="0.95 0.75 0.2 1"')).length >= STORE_ROWS);
    pg.step();
    const b = pg.model.body('base'), id = b.id; b.delete();
    const bx = pg.data.xpos[3 * id] - pg.data.xpos[3 * pg.model.body('cart').id];
    // Rendered orientation: the base's up axis is the plate normal, and its underside lies in the plate's front face.
    {
      const bid = pg.model.body('base').id, cid = pg.model.body('cart').id;
      const xm = pg.data.xmat, R = (b: number, i: number, j: number) => xm[9 * b + 3 * i + j];
      const up = [R(bid, 0, 2), R(bid, 1, 2), R(bid, 2, 2)];
      let plate = -1;                                      // the cart plate: the biggest thin (6 mm along cart y) box on the cart
      for (let g = 0; g < pg.model.ngeom; g++) if (pg.model.geom_bodyid[g] === cid && Math.abs(pg.model.geom_size[3 * g + 1] - 0.003) < 1e-9 && pg.model.geom_size[3 * g + 2] > 0.05) plate = g;
      check('cart plate found', plate >= 0);
      const gm = pg.data.geom_xmat, n = [gm[9 * plate + 1], gm[9 * plate + 4], gm[9 * plate + 7]];   // plate thickness axis = its normal
      const dot = up[0] * n[0] + up[1] * n[1] + up[2] * n[2];
      check('arm base up axis is parallel to the cart plate normal', Math.abs(Math.abs(dot) - 1) < 1e-6, String(dot));
      check('arm base up axis is horizontal (it stands out of the vertical plate, not up from a deck)', Math.abs(up[2]) < 1e-6, String(up[2]));
      const c = [0, 1, 2].map((k) => pg.data.geom_xpos[3 * plate + k]);
      const under = [0, 1, 2].map((k) => pg.data.xpos[3 * bid + k] + BASE_BOTTOM * up[k]);
      const off = [0, 1, 2].map((k) => under[k] - c[k]);
      const faceOff = Math.abs(off[0] * n[0] + off[1] * n[1] + off[2] * n[2]) - 0.003;   // distance of the base underside from the plate's far face along the normal
      check('arm base underside is in contact with the plate face', Math.abs(faceOff) < 1e-6, String(faceOff));
      const inPlane = [off[0] - (off[0] * n[0] + off[1] * n[1] + off[2] * n[2]) * n[0], off[1] - (off[0] * n[0] + off[1] * n[1] + off[2] * n[2]) * n[1], off[2] - (off[0] * n[0] + off[1] * n[1] + off[2] * n[2]) * n[2]];
      check('arm base sits within the plate outline', Math.abs(inPlane[0]) < 0.056 - 0.0225 && Math.abs(inPlane[2]) < pg.model.geom_size[3 * plate + 2] - 0.0225, inPlane.join());
      check('only one arm base: the cart carries just the plate and the two wheel sets (no deck or pad)', !names.includes('DECK_') && !names.includes('deck'));
      // the arm's pan axis (base x at pan 0) points down the plate: the claw hangs down
      check('pan 0 points down the plate (base x is world down)', Math.abs(R(bid, 2, 0) + 1) < 1e-6, String(R(bid, 2, 0)));
    }
    check('arm base is on the middle of the cart base (not off its end)', Math.abs(bx) < 0.056, String(bx));
  }
  const pgCmd = new CommandLayer(pg, new RealDriver());
  const world = new PodWorld(pg);

  // Settled store: every pod rests on its channel, none above the roof or out of its row.
  for (let i = 0; i < 1500; i++) { pg.step(); }
  check('store pods rest in position 0..3 of their row', world.rowCount(0) === STORE_START && world.frontPod(0) >= 0 && world.frontPod(5) >= 0);
  const second = world.rowPods(2)[1], z1 = world.pos(second);

  // One pod: store row 3 -> socket A1; the roof keeps the second pod down, the row behind slides one place.
  let task = new PodTask(world, pgCmd, { jobs: [{ row: 2, slot: 0 }], seed: 1 });
  let zMax = 0, yMove = 0;
  while (!task.done) { task.advance(0.1); const p = world.pos(second); zMax = Math.max(zMax, p[2] - z1[2]); yMove = Math.max(yMove, Math.abs(p[1] - z1[1]) + Math.abs(p[0] - z1[0])); if (world.pods[second].state !== 'store') break; }
  check('one pod is seated in collar A1', task.failReason === '' && world.trayPod(0) >= 0, task.failReason);
  check('roof: the second pod is not lifted or dragged while the first is picked', zMax < 0.002, String(zMax));
  for (let i = 0; i < 1000; i++) pg.step();
  const row2 = world.rowPods(2).map((i) => Math.round(world.slopePos(i) / POD_PITCH));
  check('row 3 slid down one position', row2.join() === Array.from({ length: STORE_START - 1 }, (_, k) => k).join() && world.frontPod(2) === second, row2.join());

  check('pods conserved over the first pick', world.violation === '' && world.pods.length === POD_COUNT, world.violation);

  // The integrity check catches a pod that teleports and a pod that appears.
  world.reset();
  for (let i = 0; i < 20; i++) { pg.step(); world.tick(0.002); }
  check('quiet store: no violation', world.violation === '');
  const dropped = world.pos(3);
  pg.setFreeBody('pod_3', [dropped[0] + 0.1, dropped[1], dropped[2] + 0.2], [1, 0, 0, 0]);
  pg.step(); world.tick(0.002);
  check('a teleported pod is caught', world.violation.includes('pod 3 teleported'), world.violation);
  world.reset();
  for (let i = 0; i < 20; i++) { pg.step(); world.tick(0.002); }
  world.pods[5].state = 'tray'; world.pods[5].slot = 0;           // bookkeeping says the pod left the store, but it is still there
  pg.step(); world.tick(0.002);
  check('a pod that is not where the books say is caught', world.violation !== '', world.violation);

  // Fill the whole tray from several rows.
  world.reset();
  task = new PodTask(world, pgCmd, { jobs: fillJobs(world), seed: 7 });
  while (!task.done) task.advance(0.5);
  const rowsUsed = new Set(task.cfg.jobs.map((j) => j.row)).size;
  check('whole 4 x 4 tray filled', task.failReason === '' && world.trayCount === TRAY_SLOTS, `${world.trayCount}/${TRAY_SLOTS} ${task.failReason}`);
  check('pods came from several rows', rowsUsed >= 2, String(rowsUsed));
  check('full run: no pod appeared, disappeared or teleported, and the arm hit nothing', world.violation === '', world.violation);
  check('pod count conserved: 16 in the tray, the rest in the store', world.trayCount === TRAY_SLOTS && world.storeCount === POD_COUNT - TRAY_SLOTS, `${world.trayCount} ${world.storeCount}`);
  check('every seated pod stands in its collar', task.results.every((r) => r.success && r.posErrMm <= 4), JSON.stringify(task.results.map((r) => r.posErrMm)));

  // A pin that misses the hole fails the job instead of faking success.
  world.reset();
  task = new PodTask(world, pgCmd, { jobs: [{ row: 2, slot: 5 }], seed: 3, noiseMm: 8 });
  while (!task.done) task.advance(0.5);
  check('8 mm of perception error misses the hole', task.failReason.includes('missed'), task.failReason);
  pg.dispose();
}

const t0 = performance.now(); run(5); const ms = performance.now() - t0;
console.log(`5 s of sim took ${ms.toFixed(0)} ms in node`);
process.exit(fail ? 1 : 0);
