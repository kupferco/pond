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
import { cartMjcf, cartActuators, cartBody, clampTrackContacts, pipeGeoms, setCart, setMotors } from '../src/cart/model.ts';
import { PIPE_GAP_M, TRANSFER_HORIZ_MM, TransferRun, buildSwingTable, cartPose, cartTrims, other, pipePoint, swingNeeded, type Pipe } from '../src/cart/transfer.ts';
import { makeClearCheck } from '../src/cart/clearance.ts';
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
  const xferModel = mj.MjModel.from_xml_string(`<mujoco><worldbody>${pipeGeoms(0, -1, TRANSFER_HORIZ_MM, 'b')}${pipeGeoms(PIPE_GAP_M, 1, TRANSFER_HORIZ_MM, 'c')}${cartBody(140)}</worldbody>${cartActuators()}</mujoco>`);
  check('transfer model loads with one cart mocap body', xferModel.nmocap === 1, String(xferModel.nmocap));
  const xd = new mj.MjData(xferModel); setCart(xferModel, xd.qpos, 0, 1, -1); mj.mj_forward(xferModel, xd);
  check('wheel pair joints can be driven', xferModel.nq === 13 && xferModel.nu === 4 && Math.abs(xd.qpos[xferModel.jnt_qposadr[xferModel.jnt('h2d').id]] - 0.032) < 1e-9, String(xferModel.nq)); xd.delete();
  xferModel.delete();
  { const am = mj.MjModel.from_xml_string(`<mujoco><worldbody>${cartBody(140)}</worldbody>${cartActuators()}</mujoco>`), ad = new mj.MjData(am);
    check('cart has 4 motors: 2 drive and 2 rotation actuators', ['drive1', 'drive2', 'rot1', 'rot2'].every((n) => am.actuator(n).id >= 0) && am.nu === 4);
    setMotors(am, ad, 1.5, -0.5, 0.7); mj.mj_forward(am, ad);
    check('drive motors turn only wheel joints; motor bodies are rigid (no joint on any motor/worm geom body)', am.jnt_type.length === 13 && ad.qpos[am.jnt_qposadr[am.jnt('w1f').id]] === 1.5 && ad.ctrl[am.actuator('drive1').id] === 1.5);
    check('both rotation motors share the swing about the pipe axis', Math.abs(ad.qpos[am.jnt_qposadr[am.jnt('rot1').id]] + ad.qpos[am.jnt_qposadr[am.jnt('rot2').id]] - 0.7) < 1e-9);
    ad.delete(); am.delete(); }
  check('B top bar runs left, C top bar runs right', pipePoint('B', 200).x < -0.1 && pipePoint('C', 200).x > PIPE_GAP_M + 0.1);
  // The cart is symmetric: riding on B and on C put both hands on the same two pipes and the plate in the same place.
  const rot = (q: number[], v: number[]) => { const [w, x, y, z] = q; const t = [2 * (y * v[2] - z * v[1]), 2 * (z * v[0] - x * v[2]), 2 * (x * v[1] - y * v[0])];
    return [v[0] + w * t[0] + (y * t[2] - z * t[1]), v[1] + w * t[1] + (z * t[0] - x * t[2]), v[2] + w * t[2] + (x * t[1] - y * t[0])]; };
  const world = (p: 'B' | 'C', v: number[]) => { const c = cartPose(p, 40); const r = rot(c.q, v); return [c.x + r[0], r[1], c.z + r[2]]; };
  // Collisions: sweep the cart over both pipes with the hands closed, open and mixed; no cart geometry may enter a pipe.
  const xm = mj.MjModel.from_xml_string(`<mujoco><worldbody>${pipeGeoms(0, -1, TRANSFER_HORIZ_MM, 'b')}${pipeGeoms(PIPE_GAP_M, 1, TRANSFER_HORIZ_MM, 'c')}${cartBody(140)}</worldbody>${cartActuators()}</mujoco>`);
  const xdd = new mj.MjData(xm), cmo = xm.body_mocapid[xm.body('cart').id];
  const maxS = L_VERT + L_ARC + TRANSFER_HORIZ_MM / 10;
  const table = buildSwingTable(makeClearCheck(mj, xm, xdd));
  let worst = 0, hits = 0, probes = 0;
  for (const pp of ['B', 'C'] as Pipe[]) for (let sc = 0; sc <= maxS; sc += 1) for (const [o1, o2] of [[0, 1], [0, 0.5], [0.5, 0]] as const) {
    if (sc > L_VERT && o2 < 1 && o2 > 0) continue;
    const sw = (pp === 'B' ? -1 : 1) * swingNeeded(table, pp, sc);   // the rotation motors swing the free clamp just clear over the diverging bends
    const c = cartPose(pp, sc), tr = cartTrims(pp, c, sw);
    xdd.mocap_pos[3 * cmo] = c.x; xdd.mocap_pos[3 * cmo + 1] = 0; xdd.mocap_pos[3 * cmo + 2] = c.z;
    for (let k = 0; k < 4; k++) xdd.mocap_quat[4 * cmo + k] = c.q[k];
    setCart(xm, xdd.qpos, o1, o2, c.plateSide, tr.hand1, tr.hand2); setMotors(xm, xdd, 0, 0, sw); mj.mj_forward(xm, xdd);
    probes++;
    for (let i = 0; i < xdd.ncon; i++) { const d = xdd.contact.get(i)?.dist ?? 0; if (d < -0.0005) { hits++; worst = Math.min(worst, d); } }
    if (o1 === 0 && o2 === 1) { /* nothing more */ }
  }
  check(`cart never goes into a pipe (${probes} poses, worst ${(worst * 1000).toFixed(2)} mm)`, hits === 0, `${hits} contacts`);
  // Without the swing the free clamp does hit the other pipe on the bends: the check sees it (the sleeves are real collision geoms).
  { const c = cartPose('B', 64), tr = cartTrims('B', c); xdd.mocap_pos[3 * cmo] = c.x; xdd.mocap_pos[3 * cmo + 2] = c.z;
    for (let k = 0; k < 4; k++) xdd.mocap_quat[4 * cmo + k] = c.q[k];
    setCart(xm, xdd.qpos, 0, 1, c.plateSide, tr.hand1, tr.hand2); setMotors(xm, xdd, 0, 0, 0); mj.mj_forward(xm, xdd);
    check('unswung free clamp on the bend is reported as a clamp–track contact', clampTrackContacts(xdd) < -0.002, String(clampTrackContacts(xdd))); }
  // The test must be able to fail: push the cart into pipe C and expect contacts.
  { const c = cartPose('C', 40); xdd.mocap_pos[3 * cmo] = c.x + 0.012; xdd.mocap_pos[3 * cmo + 2] = c.z;
    for (let k = 0; k < 4; k++) xdd.mocap_quat[4 * cmo + k] = c.q[k];
    setCart(xm, xdd.qpos, 0, 1, c.plateSide); mj.mj_forward(xm, xdd);
    check('collision check sees a cart pushed into the pipe', xdd.ncon > 0, String(xdd.ncon)); }
  // Full transfers, stepped like the scene does, from several start heights and both pipes: no clamp–track contact at any frame.
  for (const [startPipe, startS] of [['B', 0], ['B', 40], ['B', 100], ['B', 190], ['C', 5], ['C', 30], ['C', 150]] as [Pipe, number][]) {
    const r = new TransferRun(table); r.pipe = startPipe; r.open[startPipe] = 0; r.open[other(startPipe)] = 1; r.motion.s = startS; r.motion.goal = startS;
    r.motion.speed = 10; r.start();
    let frames = 0, deep = 0, bad = 0, maxSwing = 0, held = 0, outOfBend = 0, rotated = 0;
    const armPos: number[][] = [];
    while (!r.done && frames < 20000) {
      r.advance(0.02); frames++;
      const c = cartPose(r.pipe, r.motion.s), t = cartTrims(r.pipe, c, r.swing);
      xdd.mocap_pos[3 * cmo] = c.x; xdd.mocap_pos[3 * cmo + 1] = 0; xdd.mocap_pos[3 * cmo + 2] = c.z;
      for (let k = 0; k < 4; k++) xdd.mocap_quat[4 * cmo + k] = c.q[k];
      setCart(xm, xdd.qpos, r.open[r.pipe], r.open[other(r.pipe)], c.plateSide, t.hand1, t.hand2); setMotors(xm, xdd, r.spin[0], r.spin[1], r.swing); mj.mj_forward(xm, xdd);
      maxSwing = Math.max(maxSwing, Math.abs(r.swingW)); if (r.swingW > 0) { rotated++; if (r.motion.s < 50 || r.motion.s > 80) outOfBend++; } if (r.swingW !== r.swingGoal || r.swingW === 0) { /* in motion or home */ } else held++;
      const h = clampTrackContacts(xdd); if (h < 0) { bad++; deep = Math.min(deep, h); }
      // The arm base, relative to the cart's centre point in the world, must not move off the plate's world side.
      const gi = xm.geom('armmount').id, gp = xdd.geom_xpos;
      armPos.push([gp[3 * gi] - (c.x), gp[3 * gi + 1], gp[3 * gi + 2] - c.z]);
    }
    check(`transfer from ${startPipe} at ${startS} cm completes with no clamp–track contact (${frames} frames)`, r.done && bad === 0, `${bad} contact frames, worst ${(deep * 1000).toFixed(2)} mm`);
    check(`transfer from ${startPipe} at ${startS} cm: rotation only round the bend (cart at 50 to 80 cm), never on the straights`, rotated > 0 && outOfBend === 0, `${rotated} rotated frames, ${outOfBend} outside the bend`);
    check(`rotation is the minimum needed (at most 35 deg) from ${startPipe} at ${startS} cm`, maxSwing > 0.2 && maxSwing <= 0.61, `max ${(maxSwing * 180 / Math.PI).toFixed(1)} deg`);
    check(`cart is back on the pipe (swing 0) at the end from ${startPipe} at ${startS} cm`, r.swingW === 0);
    const gy = armPos.map((a) => a[1]);
    check(`arm base stays on the same world side of the track plane during a transfer from ${startPipe}`, gy.every((y) => y > 0.04 || y < -0.04) && (gy.every((y) => y > 0) || gy.every((y) => y < 0)), `y ${Math.min(...gy).toFixed(3)}..${Math.max(...gy).toFixed(3)}`);
  }
  // Free riding up the whole track and back (the Step controls): the rotation motors swing the free clamp clear on the bends, no contact.
  for (const startPipe of ['B', 'C'] as Pipe[]) {
    const r = new TransferRun(table); r.pipe = startPipe; r.open[startPipe] = 0; r.open[other(startPipe)] = 1; r.motion.speed = 30;
    let bad = 0, frames = 0, sw = 0;
    for (const goal of [190, 0]) { r.goTo(goal); while (r.motion.s !== r.motion.goal && frames++ < 20000) {
      r.advance(0.02); const c = cartPose(r.pipe, r.motion.s), t = cartTrims(r.pipe, c, r.swing);
      xdd.mocap_pos[3 * cmo] = c.x; xdd.mocap_pos[3 * cmo + 2] = c.z; for (let k = 0; k < 4; k++) xdd.mocap_quat[4 * cmo + k] = c.q[k];
      setCart(xm, xdd.qpos, r.open[r.pipe], r.open[other(r.pipe)], c.plateSide, t.hand1, t.hand2); setMotors(xm, xdd, r.spin[0], r.spin[1], r.swing); mj.mj_forward(xm, xdd);
      if (clampTrackContacts(xdd) < 0) bad++; sw = Math.max(sw, Math.abs(r.swingW)); } }
    check(`riding ${startPipe} up and down with the step controls: no clamp–track contact, cart swung away on the bends`, bad === 0 && sw > 0.2 && r.motion.s === 0, `${bad} contact frames, swing ${sw.toFixed(2)}, end ${r.motion.s}`);
  }
  xdd.delete(); xm.delete();
  // Shorter cart: the plate ends where the clamps end; the arm base is a fixed block on the plate's outer face.
  { const cm2 = mj.MjModel.from_xml_string(`<mujoco><worldbody>${cartBody(140)}</worldbody>${cartActuators()}</mujoco>`), cd = new mj.MjData(cm2);
    setCart(cm2, cd.qpos, 0, 0, 1); mj.mj_forward(cm2, cd);
    const pl = cm2.geom('plate').id, am = cm2.geom('armmount').id;
    check('cart plate is 208 mm long: 140 mm between the hands plus 34 mm sleeve radius at each end', Math.abs(cm2.geom_size[3 * pl + 2] * 2 - 0.208) < 1e-9 && Math.abs(cd.geom_xpos[3 * pl + 2] + 0.07) < 1e-9, String(cm2.geom_size[3 * pl + 2] * 2));
    check('arm base sits on top of the plate (side +1)', Math.abs(cd.geom_xpos[3 * am + 1] - (cd.geom_xpos[3 * pl + 1] + 0.003 + 0.02)) < 1e-9);
    cd.delete(); cm2.delete(); }
  const sameP = (a: number[], b: number[]) => a.every((n, i) => Math.abs(n - b[i]) < 1e-9);
  check('hand 1 on B is hand 2 on C', sameP(world('B', [0, 0, 0]), world('C', [0, 0, -0.14])) && sameP(world('B', [0, 0, -0.14]), world('C', [0, 0, 0])));
  const py = 0.043;
  check('plate is centred between the hands on the same side on both pipes', sameP(world('B', [0, -py, -0.07]), world('C', [0, py, -0.07])) && Math.abs(world('C', [0, py, -0.07])[0] - PIPE_GAP_M / 2) < 1e-9);
}

const t0 = performance.now(); run(5); const ms = performance.now() - t0;
console.log(`5 s of sim took ${ms.toFixed(0)} ms in node`);
process.exit(fail ? 1 : 0);
