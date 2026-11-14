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
import { cartMjcf, WHEEL_OPEN_M, cartActuators, cartBody, setMotors } from '../src/cart/model.ts';
import { HINGE_DEG_S_CAD, LIFT_CM, TOP_S_CM, TransferRun, applyPose, initialState, kinematics, worstContact, type CartState } from '../src/cart/transfer.ts';
import { transferMjcf } from '../src/cart/transfer-model.ts';
import * as DIMS from '../src/cart/dims.ts';
import { readFileSync } from 'node:fs';
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
  { const am = mj.MjModel.from_xml_string(`<mujoco><worldbody>${cartBody(140)}</worldbody>${cartActuators()}</mujoco>`), ad = new mj.MjData(am);
    check('each wheel system has 3 motors (A drive, B rotation, C clamp): 6 actuators and 6 motor bodies', ['drive1', 'drive2', 'rot1', 'rot2', 'clamp1', 'clamp2'].every((n) => am.actuator(n).id >= 0) && am.nu === 6 && ['motor_drive1', 'motor_drive2', 'motor_rot1', 'motor_rot2', 'motor_clamp1', 'motor_clamp2'].every((n) => am.body(n).id > 0));
    setMotors(am, ad, 1.5, -0.5, 0.7); mj.mj_forward(am, ad);
    check('drive motors turn only wheel joints; motor bodies are rigid (no joint on any motor/worm geom body)', am.jnt_type.length === 11 && ad.qpos[am.jnt_qposadr[am.jnt('w1f').id]] === 1.5 && ad.ctrl[am.actuator('drive1').id] === 1.5);
    check('both rotation motors share the swing about the pipe axis', Math.abs(ad.qpos[am.jnt_qposadr[am.jnt('rot1').id]] + ad.qpos[am.jnt_qposadr[am.jnt('rot2').id]] - 0.7) < 1e-9);
    // Nothing may encircle the pipe: every ring-shaped part of the rotation motors (stator and rotor) is an open C, so the pipe can leave sideways.
    for (const h of [1, 2]) {
      const angs: number[] = [];
      for (let g = 0; g < am.ngeom; g++) {
        const bn = am.body(am.geom_bodyid[g]).name, x = am.geom_pos[3 * g], y = am.geom_pos[3 * g + 1], z = am.geom_pos[3 * g + 2];
        const r = Math.hypot(y, z);
        if ((bn === `motor_rot${h}` || bn === `hand${h}`) && am.geom_type[g] === 6 && x < -0.045 && r > 0.02 && r < 0.06) angs.push(Math.atan2(y, z) * 180 / Math.PI);
      }
      angs.sort((a, b) => a - b);
      let gap = 360 - (angs[angs.length - 1] - angs[0]);
      for (let i = 1; i < angs.length; i++) gap = Math.max(gap, angs[i] - angs[i - 1]);
      check(`rotation motor ${h}: ring parts form an open C (no closed ring round the pipe)`, angs.length > 4 && gap >= 90, `${angs.length} parts, widest opening ${gap.toFixed(0)} deg`);
    }
    // The rotor rings ride on the base (body plateflip, relative to the plate centre): also open C-shapes.
    { const angs: number[] = [];
      for (let g = 0; g < am.ngeom; g++) {
        if (am.body(am.geom_bodyid[g]).name !== 'plateflip' || am.geom_type[g] !== 6) continue;
        const x = am.geom_pos[3 * g], y = am.geom_pos[3 * g + 1], z = am.geom_pos[3 * g + 2] - 0.07, r = Math.hypot(y, z);
        if (x < -0.05 && r > 0.03 && r < 0.045) angs.push(Math.atan2(y, z) * 180 / Math.PI);
      }
      angs.sort((a, b) => a - b); let gap = 360 - (angs[angs.length - 1] - angs[0]); for (let i = 1; i < angs.length; i++) gap = Math.max(gap, angs[i] - angs[i - 1]);
      check('rotation motor rotor rings (on the base) form an open C', angs.length > 4 && gap >= 90, `${angs.length} parts, opening ${gap.toFixed(0)} deg`); }
    // Hinge chain: the riding hand stays still while the base swings about its pipe axis; motor bodies belong to the hand, the rotor to the base.
    { const hh = (n: string) => am.jnt_qposadr[am.jnt(n).id];
      setMotors(am, ad, 0, 0, 0.5, 2); mj.mj_forward(am, ad);
      const h2 = am.body('hand2').id, h1 = am.body('hand1').id, m2 = am.body('motor_rot2').id;
      check('rotation motor B is a hinge between hand and base: riding hand 2 stays put, free hand 1 swings with the base', Math.abs(ad.xquat[4 * h2] - 1) < 1e-9 && Math.abs(ad.xquat[4 * h1] - Math.cos(0.25)) < 1e-9 && Math.abs(ad.qpos[hh('bh2')] + 0.5) < 1e-9 && Math.abs(ad.ctrl[am.actuator('rot2').id] + 0.5) < 1e-9);
      check('rotation motor stator is rigid on its wheel system (motor_rot2 moves with hand 2, which does not swing)', Math.abs(ad.xpos[3 * m2] - ad.xpos[3 * h2]) < 1e-9 && Math.abs(ad.xpos[3 * m2 + 2] - ad.xpos[3 * h2 + 2]) < 1e-9);
      const rotor = [...Array(am.ngeom).keys()].find((g) => am.body(am.geom_bodyid[g]).name === 'plateflip' && am.geom_type[g] === 6 && am.geom_pos[3 * g] < -0.05)!;
      check('rotation motor rotor is carried by the base (swings with it, no joint of its own)', am.body(am.geom_bodyid[rotor]).name === 'plateflip'); }
    check('clamp travel is only what clamping needs (at most 25 mm)', WHEEL_OPEN_M <= 0.025, String(WHEEL_OPEN_M));
    ad.delete(); am.delete(); }
}


// --- Transfer scene (v2 cart, cad/cart_base.py): 120 mm pipes, plate between two hinges, one hand releases and the plate swings on the other's hinge ---------------
{
  // The TypeScript layout numbers are the CAD's: read cad/cart_dims.py and hand_sleeve.py and compare.
  const py = (f: string) => readFileSync(new URL(`../../cad/${f}`, import.meta.url), 'utf8');
  // "NAME = 1.5" or "A, B = 1.5, 2" at the start of a line
  const num = (src: string, name: string) => {
    const one = src.match(new RegExp(`^${name}\\s*=\\s*(-?[0-9.]+)\\s*(#|$)`, 'm')); if (one) return parseFloat(one[1]);
    for (const m of src.matchAll(/^([A-Z_0-9]+(?:\s*,\s*[A-Z_0-9]+)+)\s*=\s*(-?[0-9.]+(?:\s*,\s*-?[0-9.]+)+)/gm)) { const ns = m[1].split(',').map((x) => x.trim()), vs = m[2].split(',').map(parseFloat), i = ns.indexOf(name); if (i >= 0) return vs[i]; }
    return NaN;
  };
  const cd = py('cart_dims.py'), hs = py('hand_sleeve.py');
  check('pipe spacing is 120 mm, as in cad/cart_dims.py', num(cd, 'PIPE_SPACING') === 120 && DIMS.PIPE_SPACING === 120 && Math.abs(DIMS.PIPE_X.C - DIMS.PIPE_X.B - 120) < 1e-9);
  const same = (names: string[], src: string, ts: Record<string, number>) => names.filter((n) => num(src, n) !== ts[n]);
  const bad = [...same(['HINGE_R', 'HINGE_LEAF_T', 'PLATE_T', 'HINGE_CLEAR', 'WHEEL_Z', 'WORM_M', 'WHEEL_Z0', 'WHEEL_T', 'KNUCKLE_Z', 'ARM_BASE_W', 'PART_GAP', 'END_GAP'], cd, DIMS as any),
    ...same(['PAD_X0', 'PAD_X1', 'PAD_Y0', 'PAD_Y1', 'WALL_OUT_R'], hs, { PAD_X0: DIMS.PAD_X0, PAD_X1: DIMS.PAD_X1, PAD_Y0: DIMS.PAD_Y0, PAD_Y1: DIMS.PAD_Y1, WALL_OUT_R: DIMS.SLEEVE_R })];
  check('hinge, plate and hand numbers in cart/dims.ts equal the CAD files', bad.length === 0, bad.join(','));
  check('derived layout: hinge axes at -90 and +66, plate -83..59, arm at -12', DIMS.hingeX(2) === -90 && DIMS.hingeX(1) === 66 && DIMS.PLATE_X0 === -83 && DIMS.PLATE_X1 === 59 && DIMS.ARM_X === -12 && DIMS.PLATE_Y0 === -52);
  check('pipe D is where hand B lands swung about hinge C (252 mm)', DIMS.PIPE_X.D === 252);

  const tm = mj.MjModel.from_xml_string(transferMjcf()), td = new mj.MjData(tm);
  const g = (n: string) => tm.geom(n).id, bodyOf = (n: string) => tm.body(tm.geom_bodyid[g(n)]).name;
  check('transfer model: one mocap plate, 6 actuators (2 drive, 2 hinge, 2 clamp), no free or ball joints', tm.nmocap === 1 && tm.nu === 6 && [...Array(tm.njnt).keys()].every((j) => tm.jnt_type[j] === 3 || tm.jnt_type[j] === 2), `nu ${tm.nu}`);
  applyPose(tm, td, initialState()); mj.mj_forward(tm, td);
  const gx = (n: string, i: number) => td.geom_xpos[3 * g(n) + i];
  check('pipes B and C are 120 mm apart in the scene', Math.abs(gx('pipeC', 0) - gx('pipeB', 0) - 0.12) < 1e-9);
  const hingeAt = (j: string) => { const id = tm.jnt(j).id; return [td.xanchor[3 * id], td.xanchor[3 * id + 1], td.xaxis[3 * id + 2]]; };
  check('each hinge axis is parallel to the pipes (vertical), on the pad edge: x -0.09 and +0.066, 43 mm in front', hingeAt('hinge2').every((v, i) => Math.abs(v - [-0.09, -0.043, 1][i]) < 1e-9) && hingeAt('hinge1').every((v, i) => Math.abs(v - [0.066, -0.043, 1][i]) < 1e-9));
  check('the plate hangs between the hinge axes', gx('plate', 0) - 0.071 > -0.09 && gx('plate', 0) + 0.071 < 0.066);
  check('drive motors, arm base and battery are on the plate (rigid: no joint between)', ['motor_drive1', 'motor_drive2', 'armbase', 'armcolumn', 'battery'].every((n) => bodyOf(n) === 'plate'));
  check('battery sits above the arm on a shelf: same x as the arm base, higher than the plate top', Math.abs(gx('battery', 0) - gx('armbase', 0)) < 1e-9 && gx('battery', 2) - 0.035 > gx('plate', 2) + 0.056);
  check('the two drive motors are on the plate in front of it; the arm base is a block on the plate face', gx('motor_drive1', 1) < gx('plate', 1) && gx('motor_drive2', 1) < gx('plate', 1) && Math.abs(gx('armbase', 1) - (gx('plate', 1) - 0.003 - 0.004)) < 1e-9);
  check('hinges are position-controlled and self-locking: position actuators on hinge1/hinge2 and friction on the joints', ['hinge1', 'hinge2'].every((n) => tm.actuator(n).id >= 0 && tm.actuator_trnid[2 * tm.actuator(n).id] === tm.jnt(n).id) && tm.dof_frictionloss[tm.jnt_dofadr[tm.jnt('hinge1').id]] > 0 && tm.dof_frictionloss[tm.jnt_dofadr[tm.jnt('hinge2').id]] > 0);
  check('exactly one wheel pair per hand moves (clamp slide joints h1p, h2p)', [...Array(tm.njnt).keys()].filter((j) => tm.jnt_type[j] === 2).map((j) => tm.jnt(j).name).sort().join() === 'h1p,h2p');

  // Kinematics: hand C never moves; the plate turns half a turn about hinge C; hand B arrives on pipe D, in the orientation it started.
  const handAt = (st: CartState, h: 1 | 2) => { applyPose(tm, td, st); mj.mj_forward(tm, td); const b = tm.body('hand' + h).id; return { x: td.xpos[3 * b], y: td.xpos[3 * b + 1], z: td.xpos[3 * b + 2], qw: td.xquat[4 * b], qz: td.xquat[4 * b + 3] }; };
  { let worstC = 0; const rest1 = handAt(initialState(), 1);
    for (let i = 0; i <= 100; i++) { const st = initialState(); st.t = i / 100; const h = handAt(st, 1); worstC = Math.max(worstC, Math.hypot(h.x - 0.06, h.y, h.z - st.s / 100), Math.abs(h.qz - rest1.qz), Math.abs(h.qw - rest1.qw)); }
    check('hand C stays exactly where it is (on pipe C, not turning) through the whole swing', worstC < 1e-9, String(worstC));
    const st = initialState(); st.t = 1; const d = handAt(st, 2); const r = initialState(), b0 = handAt(r, 2);
    check('hand B lands on pipe D, 252 mm out, in the pipe plane, orientation as at the start', Math.hypot(d.x - 0.252, d.y) < 1e-9 && Math.abs(Math.abs(d.qw) - Math.abs(b0.qw)) < 1e-9 && Math.hypot(b0.x + 0.06, b0.y) < 1e-9);
    const mid = initialState(); mid.t = 0.5; const mq = handAt(mid, 2);
    check('mid-swing the plate is out in front of the pipes (-y), never behind them', mq.y < -0.1);
    let behind = 0; for (let i = 0; i <= 100; i++) { const s2 = initialState(); s2.t = i / 100; if (handAt(s2, 2).y > 1e-9) behind++; }
    check('hand B stays in front of the pipe plane all through the swing', behind === 0, `${behind} samples`);
    const k1 = kinematics(1);
    check('at the far end the plate has turned half a turn and hinge B a further half turn', Math.abs(k1.alpha - Math.PI) < 1e-12 && Math.abs(k1.hinge2 - Math.PI) < 1e-12 && Math.abs(k1.hinge1 + Math.PI) < 1e-12); }

  // Contact check can fail: a cart pushed into a pipe, a hand turned into the plate.
  { const st = initialState(); applyPose(tm, td, st); const mc = tm.body_mocapid[tm.body('cart').id]; td.mocap_pos[3 * mc] += 0.015; mj.mj_forward(tm, td);
    check('contact check sees the cart pushed 15 mm into the pipes', worstContact(tm, td).depth < -0.005, String(worstContact(tm, td).depth));
    applyPose(tm, td, st); td.qpos[tm.jnt_qposadr[tm.jnt('hinge2').id]] = -0.5; mj.mj_forward(tm, td);
    const touching: string[] = []; for (let i = 0; i < td.ncon; i++) { const c = td.contact.get(i)!; if (c.dist < 0) touching.push(tm.geom(c.geom1).name + '/' + tm.geom(c.geom2).name); }
    check('contact check sees the plate swung into a hand (hand B turned 29 deg the wrong way)', touching.some((n) => n.includes('plate') && n.includes('pad2')), touching.join(' ')); }

  // Step riding: both hands clamped, up and down the pipes, arm out and folded: nothing touches.
  { let bad = 0;
    for (const fold of [0, 1]) for (let s = 15; s <= TOP_S_CM; s += 0.5) { const st = initialState(); st.s = s; st.fold = fold; applyPose(tm, td, st); mj.mj_forward(tm, td); if (worstContact(tm, td).depth < 0) bad++; }
    check('riding up and down both pipes, arm out or folded: no contact', bad === 0, `${bad} poses`); }

  // Interlocks of the controls.
  { const r = new TransferRun();
    check('rotate is refused with the arm out', !r.rotate(1) && r.msg.includes('Fold'));
    r.fold(true); for (let i = 0; i < 400; i++) r.advance(0.02);
    check('rotate is refused with hand B still clamped', !r.rotate(1) && r.msg.includes('Release'));
    check('releasing hand C while hand B is released is refused (the cart would let go)', r.clampHand(2, true) && !r.clampHand(1, true) && r.msg.includes('not clamped'));
    for (let i = 0; i < 100; i++) r.advance(0.02);
    check('rotate is refused until the cart is lifted over the pipe end', !r.rotate(1) && r.msg.includes('Lift'));
    check('hand B cannot clamp while lifted above its pipe end', (r.nudge(100), true) && (() => { for (let i = 0; i < 600; i++) r.advance(0.02); return r.st.s === TOP_S_CM + LIFT_CM; })() && !r.clampHand(2, false));
    check('cart cannot lift past the pipe end with hand B clamped', (() => { const q = new TransferRun(); q.nudge(100); for (let i = 0; i < 300; i++) q.advance(0.02); return q.st.s === TOP_S_CM; })()); }

  // Full transfers, stepped like the scene does, there and back: every frame is checked against the pipes and the plate against both hands.
  for (const dir of ['to D', 'back to B'] as const) {
    const r = new TransferRun(); if (dir === 'back to B') { r.st.t = 1; r.goal.t = 1; }
    r.swingDegS = 30; r.setSpeed(10); r.start();
    const phases: string[] = []; let frames = 0, bad = 0, deep = 0, swingFrames = 0, swingOk = true, tMoved = 0, handsOpen = 0, prevT = r.st.t, maxStep = 0, h1 = kinematics(r.st.t).hinge1, h2 = kinematics(r.st.t).hinge2, spinMoved = false, armDuring = true;
    while (!r.done && frames < 20000) {
      const during = r.current; r.advance(0.02); frames++;
      const k = applyPose(tm, td, r.st); mj.mj_forward(tm, td);
      if (r.current && phases[phases.length - 1] !== r.current) phases.push(r.current);
      const w = worstContact(tm, td); if (w.depth < 0) { bad++; deep = Math.min(deep, w.depth); }
      if (r.st.t !== prevT) { tMoved++; if (during !== 'swing') swingOk = false; }
      if (r.st.t > 0 && r.st.t < 1) { swingFrames++; if (!(r.st.open2 === 1 && r.st.open1 === 0 && r.st.fold === 1 && r.st.s === TOP_S_CM + LIFT_CM)) swingOk = false; }
      maxStep = Math.max(maxStep, Math.abs(k.hinge1 - h1), Math.abs(k.hinge2 - h2)); h1 = k.hinge1; h2 = k.hinge2; prevT = r.st.t;
      if (r.st.open1 > 0 || (r.st.open2 > 0.5 && r.st.open1 > 0)) handsOpen++;
      if (r.current === 'lift' && r.st.spin1 !== 0) spinMoved = true;
      if (r.st.t > 0 && r.st.t < 1 && r.st.fold < 1) armDuring = false;
    }
    check(`full transfer ${dir}: completes in the right order`, r.done && phases.join('>') === 'fold>release>lift>swing>lower>clamp>unfold', phases.join('>') + ` (${frames} frames)`);
    check(`full transfer ${dir}: zero contacts, cart against the pipes and plate against the hands (${frames} frames)`, bad === 0, `${bad} frames, worst ${(deep * 1000).toFixed(2)} mm`);
    check(`full transfer ${dir}: the plate swings only in the swing step, with the arm folded, hand B released, hand C clamped, cart lifted`, swingFrames > 100 && swingOk && armDuring && handsOpen === 0, `${swingFrames} swing frames`);
    check(`full transfer ${dir}: the hinge drives never exceed the speed limit (30 deg/s)`, maxStep <= (30 * Math.PI / 180) * 0.02 + 1e-9, `${(maxStep / 0.02 * 180 / Math.PI).toFixed(1)} deg/s`);
    check(`full transfer ${dir}: the drive wheels turn the cart up and down pipe C`, spinMoved);
    const fin = handAt(r.st, 2), want = dir === 'to D' ? DIMS.PIPE_X.D / 1000 : DIMS.PIPE_X.B / 1000;
    check(`full transfer ${dir}: hand B ends clamped on its pipe, hand C still on pipe C, arm unfolded`, Math.abs(fin.x - want) < 1e-9 && r.st.open2 === 0 && r.st.open1 === 0 && r.st.fold === 0 && Math.abs(handAt(r.st, 1).x - 0.06) < 1e-9 && r.st.s === TOP_S_CM);
  }
  check('CAD hinge worm drive speed is 60 rpm / 38 (about 9.5 deg/s)', Math.abs(HINGE_DEG_S_CAD - 9.47) < 0.01);
  td.delete(); tm.delete();
}

const t0 = performance.now(); run(5); const ms = performance.now() - t0;
console.log(`5 s of sim took ${ms.toFixed(0)} ms in node`);
process.exit(fail ? 1 : 0);
