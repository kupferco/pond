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
import { JOINT_CM, P_TOP_CM, ROLL_STATION_CM, S_FLAT_CM, placeTransfer, transferContacts, transferMjcf as transferMjcfO, blockedBy, type Trim } from '../src/cart/omni-transfer.ts';
import { CORRIDORS, JAW_A1_DEG, TransferRun, rollPlan, type Variant } from '../src/cart/omni-transfer-run.ts';
import { S_MAX_CM, S_MIN_CM, transferMjcf, worldToCad } from '../src/cart/transfer-model.ts';
import * as DIMS from '../src/cart/dims.ts';
import * as OC from '../src/cart/omni.ts';
import { BEND_TRIM_ROWS, NO_TRIM, bendTrim, omniTrackMjcf, placeOmniCart, trackContacts } from '../src/cart/omni-track.ts';
import { RollMotion, ROLL_HOME_TOL_DEG, canRoll, driveLimit, pickRollDirection, sweep } from '../src/cart/roll.ts';
import { POINT_CM, POINT_WINDOW_DEG, RING_CM, RING_W_CM, hall, runHoming } from '../src/cart/homing.ts';
import { LOAD_N, PIPES, maxCantileverMm, sagTable } from '../src/cart/track-sag.ts';
import * as TS from '../src/cart/track-supports.ts';
import { readFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { ARM_Y, BASE_BOTTOM, CART_Z, LID_Z, PIPE_Y, PIPE_Z, SPINE_Y, POD_COUNT, POD_PITCH, ROW_PITCH, ROW_X0, SPINE_R, STORE_CAP, STORE_ROWS, STORE_START, TRAY_CX, TRAY_HX, TRAY_SLOTS, podGrabMjcf, seatPos, storePos } from '../src/podgrab/layout.ts';
import { PodTask, PodWorld, fillJobs } from '../src/podgrab/task.ts';
import * as LAYOUT from '../src/layout.ts';

import { HOLD_DEG, POD_D, REACH } from '../src/arm/dims.ts';
import { transplantMjcf, ARM_CY, CUP_ROOT, D_CUP, LID as LID_TOP, TRAY_CAP_TOP, CART_Z0, CART_Z1, CART_ZP, YC, XT, LEG, PSI, CUP_DROP, SEAT_CAP_TOP, PARK_CAP_TOP, ZH, ZP, P0, U_CAP, CAP_T, HOLDER_FLOOR_X, X_TOP, RECESS_T } from '../src/transplant/layout.ts';
import { TransplantRun, STEPS, ikTool, toolOf } from '../src/transplant/task.ts';
import { Binder, worstContact as podContact } from '../src/transplant/apply.ts';

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

check('nine scenes, two groups, Transplant seedling and Reach test under the Tests', SCENE_INFOS.length === 9 && SCENE_INFOS.filter((s) => s.group === 'Tests').length === 7 && SCENE_INFOS.some((s) => s.id === 'transplant' && s.group === 'Tests') && SCENE_INFOS.some((s) => s.id === 'reach-test' && s.group === 'Tests'));
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


// --- Transfer scene on the omni cart (OpenPocket #283): 120 mm pipes, one hand releases and the whole cart rolls about the other pipe; the hinge-era tests are replaced by the roll and clearance tests ---------------
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
  // Pond #279: cad/cart_hinge.py and the hinge and worm constants are gone from the CAD (rigid base on the omni wheels). This TypeScript
  // scene is still the old hinge scene until the scene part of the plan (docs/plans/cart-roll-redesign-plan.md section 10), so only the
  // numbers that still exist in cart_dims.py are compared, and the hinge-era numbers in cart/dims.ts are frozen legacy values.
  const bad = [...same(['PLATE_T', 'ARM_BASE_W', 'PART_GAP', 'END_GAP'], cd, DIMS as any),
    // PAD_X0 is the hinge-era -24 in cart/dims.ts (frozen legacy: its hinge axes and plate -83..83 are derived from it); the CAD pad is -20 since #312 (layout B motors)
    ...same(['PAD_X1'], hs, { PAD_X1: DIMS.PAD_X1 })];
  check('plate and pad numbers in cart/dims.ts that still exist in the CAD equal the CAD files', bad.length === 0, bad.join(','));
  check('derived layout (mirrored hands): hinge axes at -90 and +90, plate -83..+83 (166 wide), arm at 0, motors at +-53', DIMS.hingeX(2) === -90 && DIMS.hingeX(1) === 90 && DIMS.PLATE_X0 === -83 && DIMS.PLATE_X1 === 83 && DIMS.ARM_X === 0 && DIMS.MOTOR_B_X === -53 && DIMS.MOTOR_C_X === 53 && DIMS.PLATE_Y0 === -52);
  check('the scene has only two pipes, B and C: no pipe D anywhere', Object.keys(DIMS.PIPE_X).join() === 'B,C' && !/pipeD/.test(transferMjcf()));

  // ---- Transfer on the omni cart (OpenPocket #283, plan task 265 part 9): the roll about the static pipe replaces the hinge swing ----
  // The legacy hinge model above (transfer-model.ts) stays only for the Transplant scene until plan task 10 moves it over; the Transfer scene itself is src/cart/omni-transfer.ts.
  const ot = (variant: Variant) => { const mm = mj.MjModel.from_xml_string(transferMjcfO({ jawA1: JAW_A1_DEG[variant] })), dd = new mj.MjData(mm); mm.geom_margin.fill(0.0001); return { mm, dd }; };
  const probeAt = (w: { mm: any; dd: any }, rider: 'B' | 'C', s: number, roll: number, open = 1, trim?: Trim) => { placeTransfer(w.mm, w.dd, { rider, s, roll, open, trim }); mj.mj_forward(w.mm, w.dd); const d = transferContacts(w.mm, w.dd, rider); return { what: blockedBy(d), d }; };
  const cadW = ot('cad'), wideW = ot('wide');
  check('transfer model: one mocap cart, 8 actuators (2 drive, 2 roll motor, 2 roll joint, 2 jaw), the jaws are hinges 0 to 92 degrees, no hinge1/hinge2, rods and rings on both pipes',
    cadW.mm.nmocap === 1 && cadW.mm.nu === 8 && ['jawB', 'jawC'].every((n) => cadW.mm.jnt(n).id >= 0 && Math.abs(cadW.mm.jnt_range[2 * cadW.mm.jnt(n).id + 1] - OC.JAW_OPEN_RAD) < 1e-9) && !/hinge[12]/.test(transferMjcfO()) && JOINT_CM.every((_, i) => ['B', 'C'].every((h) => cadW.mm.geom(`rod${h}${i}`).id >= 0 && cadW.mm.geom(`ring${h}${i}`).id >= 0)));
  check('jaw wedge numbers: CAD 0 to 110 degrees and 92 degrees open (cad/cart_sleeves.py), the proposed wedge 150', OC.JAW_A1 === 110 && JAW_A1_DEG.cad === 110 && JAW_A1_DEG.wide === 150 && OC.JAW_OPEN_DEG === 92 && /^JAW_A0, JAW_A1 = 0\.0, 110\.0/m.test(py('cart_sleeves.py')) && /^JAW_OPEN = 92\.0/m.test(py('cart_sleeves.py')));
  // placement: the riding hand's pipe axis sits on its own pipe, hand B and C mirror each other
  { const at = (rider: 'B' | 'C', s: number, roll = 0) => { placeTransfer(cadW.mm, cadW.dd, { rider, s, roll, open: 0 }); mj.mj_forward(cadW.mm, cadW.dd); const p = (n: string) => [cadW.dd.xpos[3 * cadW.mm.body(n).id], cadW.dd.xpos[3 * cadW.mm.body(n).id + 1], cadW.dd.xpos[3 * cadW.mm.body(n).id + 2]]; return { B: p('handB'), C: p('handC') }; };
    const a = at('C', 30), b = at('B', 30);
    check('on the leg both hands sit on their pipes (x -0.06 and +0.06, z 0.30) whichever hand is the rider', [a, b].every((r) => Math.abs(r.B[0] + 0.06) < 1e-6 && Math.abs(r.C[0] - 0.06) < 1e-6 && Math.abs(r.B[2] - 0.3) < 1e-6 && Math.abs(r.C[2] - 0.3) < 1e-6));
    const bendS = L_VERT + L_ARC / 2, c = at('C', bendS), d2 = at('B', bendS);
    check('on the bend the rider is on its own pipe and the two trips are exact mirror images (x mirrored, y and z equal)', c.C[0] > 0.1 && d2.B[0] < -0.1 && Math.abs(c.C[0] + d2.B[0]) < 1e-9 && Math.abs(c.C[2] - d2.B[2]) < 1e-9 && Math.abs(c.B[0] + d2.C[0]) < 1e-9 && Math.abs(c.B[2] - d2.C[2]) < 1e-9);
    const r1 = at('C', 30, 90), r2 = at('B', 30, 90);
    check('a positive roll turns the free hand to the plate side (-y) for both trips, round the static pipe (120 mm radius)', r1.B[1] < -0.1 && r2.C[1] < -0.1 && Math.abs(Math.hypot(r1.B[0] - 0.06, r1.B[1]) - 0.12) < 1e-6 && Math.abs(Math.hypot(r2.C[0] + 0.06, r2.C[1]) - 0.12) < 1e-6 && Math.abs(r1.C[0] - 0.06) < 1e-9 && Math.abs(r2.B[0] + 0.06) < 1e-9, JSON.stringify([r1.B, r2.C])); }
  // clamped on the leg and a jaw opened on its own pipe touch nothing; the rods are passed at roll 0
  check('both hands clamped, riding the whole leg every 1 cm: no collision (rods and rings included)', [S_MIN_CM, 20, 30, 40, 50, 55].every((s) => ['B', 'C'].every((r) => probeAt(cadW, r as 'B' | 'C', s, 0, 0).what === '')));
  check('a jaw open 92 degrees round its own pipe at roll 0, on the leg: the free hand touches nothing (both hands)', ['B', 'C'].every((r) => [S_MIN_CM, 30, 50].every((s) => probeAt(cadW, r as 'B' | 'C', s, 0, 1).what === '')));
  // ---- the go or no-go: the roll corridors, both directions, both trips, both jaw wedges ----
  for (const rider of ['C', 'B'] as const) {
    const free = rider === 'C' ? 'B' : 'C', trip = rider === 'C' ? 'up pipe C (hand B released)' : 'up pipe B (hand C released)';
    const firstHit = (w: typeof cadW, dir: 1 | -1) => { for (let a = 0; a <= 180; a++) { const r = probeAt(w, rider, ROLL_STATION_CM, dir * a); if (r.what) return { a, what: r.what }; } return null; };
    const cp = firstHit(cadW, 1), cs = firstHit(cadW, -1);
    check(`CAD jaw wedge (0 to 110), trip ${trip}: neither direction clears: the plate side hits the free hand's own pipe within 5 degrees (${cp?.a}), the spine side within 5 degrees (${cs?.a})`, !!cp && !!cs && cp.a <= 5 && cs.a <= 5 && /free:pipe/.test(cp.what) && /free:pipe/.test(cs.what));
    const wp = firstHit(wideW, 1), ws = firstHit(wideW, -1);
    check(`wedge 0 to 150, trip ${trip}: the plate side rolls 0 to 180 degrees at the roll station without touching anything, the spine side still hits (${ws?.a} degrees)`, wp === null && !!ws && ws.a <= 5);
    // held through the bend: roll angles in the corridor, every 0.25 cm from the roll station to the roll-back point
    const heldBad = (deg: number) => { let n = 0; for (let s = ROLL_STATION_CM; s <= S_FLAT_CM + 1e-9; s += 0.25) if (probeAt(wideW, rider, s, deg).what) n++; return n; };
    check(`wedge 150, trip ${trip}: the roll held at 35, 90 and 180 degrees through the whole bend (every 0.25 cm, ${Math.round((S_FLAT_CM - ROLL_STATION_CM) / 0.25) + 1} poses each): no contact`, [35, 90, 180].every((d) => heldBad(d) === 0));
    check(`wedge 150, trip ${trip}: below the corridor (20 and 30 degrees) the free hand still catches pipe ${free}'s bend`, heldBad(20) > 0 && heldBad(30) > 0);
    check(`wedge 150, trip ${trip}: the roll back at the start of the top run (every 1 degree, 90 to 0) is clear and the flat cart with the jaw open clears the top bar every 0.5 cm`, sweep(90, 0, 1).every((a) => probeAt(wideW, rider, S_FLAT_CM, a).what === '') && (() => { for (let s = S_FLAT_CM; s <= P_TOP_CM + 1e-9; s += 0.5) if (probeAt(wideW, rider, s, 0).what) return false; return true; })());
  }
  check('the two trips have the same corridors (the hands are true mirrors): the roll corridor table is the same for B and C in both variants', JSON.stringify(CORRIDORS.cad.B) === JSON.stringify(CORRIDORS.cad.C) && JSON.stringify(CORRIDORS.wide.B) === JSON.stringify(CORRIDORS.wide.C));
  check('roll plan: the CAD wedge has no direction (stop and ask the owner, Q3); the wide wedge rolls 90 degrees to the plate side, inside 35 to 180', rollPlan('cad', 'C').dir === null && /ask the owner/.test(rollPlan('cad', 'C').reason!) && rollPlan('wide', 'C').dir === 1 && rollPlan('wide', 'C').roll === 90 && rollPlan('wide', 'B').roll === 90 && CORRIDORS.wide.C.plate![0] <= 90 && CORRIDORS.wide.C.plate![1] >= 90);
  // the rider's own sleeve on the bend is a separate finding (cart on track scene): it is not a collision of the transfer, and the rods are passed at roll 0
  { let w = 0; for (let s = L_VERT; s <= L_VERT + L_ARC; s += 1) w = Math.min(w, probeAt(wideW, 'C', s, 0, 0).d['rider:pipe']);
    check('known finding kept apart: the riding sleeve on the 150 mm bend still penetrates its own pipe by 3 to 5 mm (rigid 124 mm sleeve), which is not counted as a collision of the transfer', w < -0.002 && w > -0.006, `${(w * 1000).toFixed(2)} mm`); }
  // ---- controller ----
  const stepAll = (r: TransferRun, w: typeof cadW | null, max = 4000, dt = 1 / 30) => {
    const phases: string[] = r.current ? [r.current] : []; let bad = 0, frames = 0, maxRoll = 0, rolledOutsideRoll = 0, rollStepOutsideWindow = 0, maxRollStep = 0, drivenRolledOutsideMove = 0, prevRoll = r.st.roll, what = '';
    while (frames < max) {
      const before = r.current, s0 = r.st.s; r.advance(dt); frames++;
      if (r.current && phases[phases.length - 1] !== r.current) phases.push(r.current);
      maxRoll = Math.max(maxRoll, Math.abs(r.st.roll)); maxRollStep = Math.max(maxRollStep, Math.abs(r.st.roll - prevRoll) / dt); prevRoll = r.st.roll;
      if (r.rolled && before !== 'roll' && before !== 'rollBack' && before !== 'move' && before !== 'moveBack' && r.st.s !== s0) drivenRolledOutsideMove++;
      if (r.st.roll !== 0 && r.st.roll !== prevRoll && (before !== 'roll' && before !== 'rollBack')) rolledOutsideRoll++;
      if (w) { const x = probeAt(w, r.rider, r.st.s, r.st.roll, r.open(r.free), undefined); const p = x.what; if (p) { bad++; what = p; } placeTransfer(w.mm, w.dd, { rider: r.rider, s: r.st.s, roll: r.st.roll, open: r.open(r.free), riderOpen: r.open(r.rider) }); mj.mj_forward(w.mm, w.dd); if (blockedBy(transferContacts(w.mm, w.dd, r.rider))) { bad++; what = blockedBy(transferContacts(w.mm, w.dd, r.rider)); } }
      if (r.done && !r.busy) break;
    }
    return { phases, bad, frames, maxRoll, maxRollStep, rolledOutsideRoll, drivenRolledOutsideMove, what, rollStepOutsideWindow };
  };
  { const r = new TransferRun('cad'); r.reset(30);
    check('CAD wedge: the transfer refuses to start and says no roll direction clears (Q3: stop and come back to the owner)', !r.start('B') && /Neither roll direction clears/.test(r.msg) && !r.busy && r.st.s === 30, r.msg);
    check('CAD wedge: the other trip refuses too, and a manual roll to clear is refused', !r.start('C') && (r.clampHand('B', true), r.advance(2.5), !r.rollTo(1)) && /Neither roll direction clears|ask the owner/.test(r.msg));
    r.reset(ROLL_STATION_CM); r.clampHand('B', true); for (let i = 0; i < 100; i++) r.advance(0.05);
    check('CAD wedge: rolling by hand 20 degrees anyway (the "try" button) is allowed and the contact check sees the free hand hit its own pipe', r.rollTo(1, 20) && (() => { for (let i = 0; i < 100; i++) r.advance(0.05); return probeAt(cadW, r.rider, r.st.s, r.st.roll).what.includes('free:pipe'); })()); }
  { const r = new TransferRun('wide'); r.reset(30);
    check('wide wedge: roll refused with both jaws clamped, with only the static jaw open, away from the roll station and on the run', !r.rollTo(1) && /Release hand B first/.test(r.msg) && (r.clampHand('B', true), r.advance(0.2), !r.rollTo(1)) && /Release hand B first/.test(r.msg));
    for (let i = 0; i < 100; i++) r.advance(0.05);
    check('wide wedge: with hand B fully open at 30 cm the roll is refused (the rolled sleeve would hit the track-joint rods, the roll station is 47 to 50 cm)', !r.rollTo(1) && /roll station/.test(r.msg) && r.st.roll === 0);
    check('wide wedge: releasing hand C as well is refused (the cart would let go)', !r.clampHand('C', true) && /not clamped/.test(r.msg));
    check('wide wedge: nudging the cart to the top of the leg and rolling works there; a rolled cart refuses to jaw or release', r.nudge(40) && (() => { for (let i = 0; i < 400; i++) r.advance(0.05); return r.st.s === S_MAX_CM && r.rollTo(1); })() && (() => { for (let i = 0; i < 100; i++) r.advance(0.05); return r.st.roll === 90 && !r.clampHand('B', false); })());
    check('wide wedge: rolled, forward drives round the bend only up to the end of the bend (the run needs roll 0), further is clipped with the reason', r.nudge(100) && r.goal.s === S_FLAT_CM && /run needs roll 0/.test(r.msg));
    check('wide wedge: rolled cart cannot be driven with the free jaw not fully open (jaw moving)', (() => { const q = new TransferRun('wide'); q.reset(S_MAX_CM); q.clampHand('B', true); for (let i = 0; i < 100; i++) q.advance(0.05); q.rollTo(1); for (let i = 0; i < 100; i++) q.advance(0.05); q.goal.openB = 0; q.advance(0.5); const s0 = q.st.s; q.goal.s = s0 + 5; q.advance(0.5); return q.st.s === s0; })()); }
  // full transfers, both ways, with every frame contact-checked
  for (const s0 of [S_MIN_CM, 30, S_MAX_CM]) for (const rel of ['B', 'C'] as const) {
    const r = new TransferRun('wide'); r.reset(s0), r.setSpeed(20);
    const started = r.start(rel), out = stepAll(r, wideW), top = rel === 'B' ? 'right' : 'left';
    check(`trip releasing hand ${rel} from ${s0} cm: starts, runs toStation > release > roll > move > rollBack > moveTop and finishes`, started && r.done && out.phases.join('>') === 'toStation>release>roll>move>rollBack>moveTop', out.phases.join('>'));
    check(`trip releasing hand ${rel} from ${s0} cm: zero collisions of the free hand, base and rods on every frame (${out.frames} frames), the roll never above 90 degrees and never faster than the roll speed`, out.bad === 0 && out.maxRoll === 90 && out.maxRollStep <= r.rollDegS + 1e-6, `${out.bad} bad ${out.what}, max roll ${out.maxRoll}, ${out.maxRollStep.toFixed(1)} deg/s`);
    check(`trip releasing hand ${rel} from ${s0} cm: ends at the top ${top} of pipe ${rel === 'B' ? 'C' : 'B'}, flat, hand ${rel} open, the other clamped, and the cart travelled round the bend (more than 60 cm)`, r.st.s === P_TOP_CM && r.st.roll === 0 && r.open(rel) === 1 && r.open(rel === 'B' ? 'C' : 'B') === 0 && P_TOP_CM - s0 > 60);
    check(`trip releasing hand ${rel} from ${s0} cm: the cart rolls only in the roll steps and never drives rolled outside the move steps`, out.rolledOutsideRoll === 0 && out.drivenRolledOutsideMove === 0);
  }
  { // there and back, and on to the other pipe: press three times
    const r = new TransferRun('wide'); r.reset(S_MAX_CM); r.setSpeed(30); const ends: string[] = [], seq: string[] = []; let bad = 0;
    for (let p = 0; p < 3; p++) { const ok = r.press(); const o = stepAll(r, wideW); bad += o.bad; seq.push(o.phases.join('>')); ends.push(`${ok}:${r.st.s.toFixed(1)}:${r.rider}`); }
    check('three presses: up C, then (back and) up B, then (back and) up C, ending on the top bar each time', ends.join(' ') === `true:${P_TOP_CM.toFixed(1)}:C true:${P_TOP_CM.toFixed(1)}:B true:${P_TOP_CM.toFixed(1)}:C`, ends.join(' '));
    check('press 2 comes back: drive flat to the bend end, roll, drive back round the bend rolled, roll flat, clamp, then the trip up the other pipe', seq[1] === 'moveFlat>roll>moveBack>rollBack>clamp>toStation>release>roll>move>rollBack>moveTop', seq[1]);
    check('three presses: zero collisions on every frame', bad === 0, String(bad)); }
  { const r = new TransferRun('wide'); r.reset(S_MAX_CM); r.setSpeed(30); r.start('B'); const o = stepAll(r, wideW); r.reset(); const t0 = r.start('C');
    check('reset: cart back at the top of the leg, both clamped, ready for another transfer; reset again and the other trip starts', o.bad === 0 && t0 && r.st.openB === 0 && r.st.openC === 0 && r.current === 'toStation'); }
  { const r = new TransferRun('wide'); r.reset(S_MAX_CM); r.start('B'); r.advance(0.1); const msg = r.start('B'), stopped = (r.stop(), r.msg === 'Stopped.' && !r.busy);
    check('a running transfer refuses a second start and stop() ends it where it is', !msg && stopped); }
  cadW.mm.delete(); cadW.dd.delete(); wideW.mm.delete(); wideW.dd.delete();
}

// Pod grab: the arm on the cart takes pods out of the sloped store rows and lowers them into the silicone collars of the 4 x 4 tray.
{
  const pg = new SimDriver(mj, podGrabMjcf());
  check('pod grab model has the cart as its one mocap body (the arm base is rigid in it); the pods are free bodies', pg.model.nmocap === 1 && pg.model.nbody > POD_COUNT, String(pg.model.nmocap));
  // OpenPocket #364: ONE shared layout (cad/layout.json). The sim's tank, lid and bottom track height are that file's numbers, and the cart (165 mm under the track in the CAD) clears the lid with the layout's air gap.
  check('shared layout: sim tank, lid and bottom track height are the numbers of cad/layout.json, and the cart hangs clear of the lid',
    LID_Z === LAYOUT.TANK_H && PIPE_Z === LAYOUT.TRACK_BOTTOM_Z && PIPE_Z - (LAYOUT.LID_TOP + LAYOUT.CART_BELOW_TRACK) >= LAYOUT.CART_CLEARANCE - 1e-9 && LAYOUT.CART_CLEARANCE > 0,
    `track ${(PIPE_Z * 1000).toFixed(0)} mm, lid ${(LAYOUT.LID_TOP * 1000).toFixed(0)}, cart ${(LAYOUT.CART_BELOW_TRACK * 1000).toFixed(0)} under the track, air ${(LAYOUT.CART_CLEARANCE * 1000).toFixed(0)} mm (ASSUMED)`);
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
    check('collars are collision geometry the arm can hit (named collar_*, arm bit set)', names.includes('name="collar_0_0"') && names.split('\n').filter((l) => l.includes('name="collar_') && l.includes('conaffinity="3"')).length >= 8 * (STORE_ROWS + TRAY_SLOTS));
    check('each store row has an end gate at the back', names.split('\n').filter((l) => l.includes('rgba="0.95 0.75 0.2 1"')).length >= STORE_ROWS);
    pg.step();
    const b = pg.model.body('base'), id = b.id; b.delete();
    const bx = pg.data.xpos[3 * id] - pg.data.xpos[3 * pg.model.body('cart').id];
    // Rendered orientation: the base's up axis is the plate normal, and its underside lies in the plate's front face.
    {
      const bid = pg.model.body('base').id;
      const xm = pg.data.xmat, R = (b: number, i: number, j: number) => xm[9 * b + 3 * i + j];
      const up = [R(bid, 0, 2), R(bid, 1, 2), R(bid, 2, 2)];
      const pgeom = pg.model.geom('plate'), plate = pgeom.id; pgeom.delete();   // the cart plate (omni cart, 6 mm along cart y), in a body below the cart
      check('cart plate found', plate >= 0);
      const gm = pg.data.geom_xmat, n = [gm[9 * plate + 1], gm[9 * plate + 4], gm[9 * plate + 7]];   // plate thickness axis = its normal
      const dot = up[0] * n[0] + up[1] * n[1] + up[2] * n[2];
      check('arm base up axis is parallel to the cart plate normal', Math.abs(Math.abs(dot) - 1) < 1e-6, String(dot));
      check('arm base up axis is horizontal (it stands out of the vertical plate, not up from a deck)', Math.abs(up[2]) < 1e-6, String(up[2]));
      const c = [0, 1, 2].map((k) => pg.data.geom_xpos[3 * plate + k]);
      const under = [0, 1, 2].map((k) => pg.data.xpos[3 * bid + k] + BASE_BOTTOM * up[k]);
      const off = [0, 1, 2].map((k) => under[k] - c[k]);
      const faceOff = Math.abs(off[0] * n[0] + off[1] * n[1] + off[2] * n[2]) - 0.003 - 0.05;   // distance of the base underside from the battery's front face (plate 6 mm + battery 50 mm) along the normal
      check('arm base underside is flat on the battery face (cart_dims.py ARM_Y0, 106 mm out of the pipe plane)', Math.abs(faceOff) < 1e-6, String(faceOff));
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

  // Pond #284: the omni cart on the bottom run, hand B on the pipe, hand C open above it, flat, no hinges.
  {
    pg.step();
    const where = (n: string) => { const b = pg.model.body(n), id = b.id; b.delete(); return [0, 1, 2].map((k) => pg.data.xpos[3 * id + k]); };
    const quat = (n: string) => { const b = pg.model.body(n), id = b.id; b.delete(); return [0, 1, 2, 3].map((k) => pg.model.body_quat[4 * id + k]); };
    const hb = where('handB'), hc = where('handC');
    check('pod grab: the cart rides the bottom pipe on hand B (its pipe axis is the track line) and hand C hangs 120 mm above it', Math.abs(hb[1] - PIPE_Y) < 1e-6 && Math.abs(hb[2] - PIPE_Z) < 1e-6 && Math.abs(hc[1] - PIPE_Y) < 1e-6 && Math.abs(hc[2] - PIPE_Z - 0.12) < 1e-6, `${hb} ${hc}`);
    check('pod grab: the free hand (C) has its jaw open 92 degrees, the riding hand (B) is closed', Math.abs(2 * Math.asin(Math.abs(quat('jawC')[3])) * 180 / Math.PI - 92) < 0.1 && Math.abs(quat('jawB')[0] - 1) < 1e-9);
    const nmz = podGrabMjcf();
    check('pod grab: no hinge, worm, tongue or second hand below the pipe: the one plate carries the battery and the arm (cartbase), the arm base is the arm\'s own', !/hinge|worm|tongue/i.test(nmz.replace(/type="hinge"/g, '')) && nmz.includes('name="battery"') && nmz.includes('name="cartbase"') && !nmz.includes('name="armbase"'));
    check('pod grab: the arm base is 106 mm out of the pipe plane (plate 6 + battery 50 on the 50 mm pads) and 60 mm above the pipe', Math.abs(PIPE_Y - ARM_Y - 0.0975) < 1e-9 && Math.abs(CART_Z - PIPE_Z - 0.06) < 1e-9);
    // spine and bracket: the finding of the plan's section 7 (Q6). Clear everywhere but within 95 mm of the spine.
    const xs = [-0.33, -0.2, -0.145, -0.1, 0.1, 0.105, 0.2, 0.28], depths = xs.map((x) => world.probeCart(x).depth);
    check('pod grab: the cart is clear of the spine and the track bracket along the bottom run outside 10 cm of the spine, at the tray end, the store end and in between', depths.every((d) => d === 0), depths.join());
    const inZone = [-0.09, -0.05, 0, 0.05, 0.09].map((x) => world.probeCart(x));
    check('FINDING pod grab: the rigid sleeves hit the spine (53 mm deep at the cart centre) and the track bracket (10 mm) with the cart centre within 9 cm of the spine: the cart cannot cross between the tray and the store', inZone.every((r) => r.depth < -0.001) && inZone[2].depth < -0.03 && inZone.every((r) => r.by.track_bracket < 0 || r.by.spine_tube < 0) && inZone[2].by.track_bracket < -0.005 && inZone[2].by.spine_tube < -0.03, JSON.stringify(inZone));
  }

  // Settled store: every pod rests on its channel, none above the roof or out of its row.
  for (let i = 0; i < 1500; i++) { pg.step(); }
  check('store pods rest in position 0..3 of their row', world.rowCount(0) === STORE_START && world.frontPod(0) >= 0 && world.frontPod(5) >= 0);
  const second = world.rowPods(2)[1], z1 = world.pos(second);

  // One pod: store row 3 -> socket A1; the roof keeps the second pod down, the row behind slides one place.
  let task = new PodTask(world, pgCmd, { jobs: [{ row: 2, slot: 0 }], seed: 1 });
  let zMax = 0, yMove = 0;
  while (!task.done) { task.advance(0.1); const p = world.pos(second); zMax = Math.max(zMax, p[2] - z1[2]); yMove = Math.max(yMove, Math.abs(p[1] - z1[1]) + Math.abs(p[0] - z1[0])); if (world.pods[second].state !== 'store') break; }
  check('first pick: gripper never touched a collar', world.collarHits === 0, world.collarHit);
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
  check('full run: no gripper geom touched any silicone collar', world.collarHits === 0 && !/collar/.test(world.violation), world.collarHit);
  check('pod count conserved: 16 in the tray, the rest in the store', world.trayCount === TRAY_SLOTS && world.storeCount === POD_COUNT - TRAY_SLOTS, `${world.trayCount} ${world.storeCount}`);
  check('every seated pod stands in its collar', task.results.every((r) => r.success && r.posErrMm <= 4), JSON.stringify(task.results.map((r) => r.posErrMm)));

  // A pin that misses the hole fails the job instead of faking success.
  world.reset();
  task = new PodTask(world, pgCmd, { jobs: [{ row: 2, slot: 5 }], seed: 3, noiseMm: 8 });
  while (!task.done) task.advance(0.5);
  check('8 mm of perception error misses the hole', task.failReason.includes('missed'), task.failReason);
  pg.dispose();
}

// --- Transplant seedling scene: the whole trip, every frame posed by IK and checked for contacts -------------------
{
  const tm = mj.MjModel.from_xml_string(transplantMjcf());
  const td = new mj.MjData(tm);
  const bind = new Binder(mj, tm, td);
  const tr = new TransplantRun();
  tr.reset();
  check('transplant: rest pose is clear and reachable', bind.apply(tr.pose) && podContact(tm, td).depth === 0);
  // geometry from the collar CAD: parked plug stands 5 mm further out than a seated one, holder 44 mm under the hole, seat axis through the hole centre
  check('transplant: plug holder is 44 mm below the hole', Math.abs(ZH - ZP - 0.044) < 1e-9);
  const out = (p: number[]) => Math.hypot(p[0], p[1]);   // distance from the pipe axis (the collar is turned about it by PSI)
  check('transplant: parked plug cap top is 5 mm past a seated one (blind floor), at the holder height', Math.abs(out(PARK_CAP_TOP) - (X_TOP - RECESS_T + 0.005 + CAP_T)) < 1e-9 && Math.abs(PARK_CAP_TOP[2] - ZP) < 1e-9);
  check('transplant: seated cap top is 29.7 mm along the 45 degree axis', Math.abs(Math.hypot(SEAT_CAP_TOP[0] - P0[0], SEAT_CAP_TOP[1] - P0[1], SEAT_CAP_TOP[2] - P0[2]) - (U_CAP + CAP_T)) < 1e-9);
  check('transplant: holder floor under the plug', Math.abs(out(PARK_CAP_TOP) - CAP_T - 0.017 - HOLDER_FLOOR_X) < 1e-9);
  check('transplant: seat and plug holder face the same way (azimuth PSI)', Math.abs(Math.atan2(PARK_CAP_TOP[1], PARK_CAP_TOP[0]) - PSI) < 1e-9 && Math.abs(Math.atan2(SEAT_CAP_TOP[1], SEAT_CAP_TOP[0]) - PSI) < 1e-9);
  // ONE track: the unit's loop, 60 mm in front of the pipe, legs 290 mm either side; the cart's hand B rides the +y leg, hand C hangs open (no pipe 120 mm further)
  {
    const names: string[] = [];
    for (let g = 0; g < tm.ngeom; g++) { const n = tm.geom(g).name; if (n) names.push(n); }
    check('transplant: one track loop (two legs, top and bottom run), no second loop', names.filter((n) => /^trackleg/.test(n)).length === 2 && names.filter((n) => /^track(L|R)/.test(n)).length === 0 && names.includes('tracktop') && names.includes('trackbot'));
    check('transplant: track plane 60 mm in front of the pipe axis, legs 290 mm either side, the cart (hand C, 60 mm from the cart centre) on the -y leg', XT === 0.06 && LEG === 0.29 && Math.abs(YC - 0.06 + LEG) < 1e-12);
  }
  // the base of the hand origin from the model matches the IK frame (pose with the hand pointing down)
  tr.pose.tool = { x: TRAY_CAP_TOP[0], y: YC, z: CART_Z0 - 0.2, phi: 0 }; bind.apply(tr.pose);
  { const h = bind.handPos(); check('transplant: IK frame matches the arm model', Math.abs(h[0] - (TRAY_CAP_TOP[0] + 0.011)) < 1e-6 && Math.abs(h[1] - YC) < 1e-6 && Math.abs(h[2] - (CART_Z0 - 0.2 + 0.0785)) < 1e-6, JSON.stringify(h)); }
  tr.reset();
  const dts = 0.004;
  for (let s = 0; s < STEPS.length; s++) {
    let touched = 0, unreachable = 0, worstMm = 0, names = '', minMargin = 90;
    tr.step();
    while (tr.busy) {
      tr.advance(dts);
      if (!bind.apply(tr.pose)) unreachable++;
      const j = ikTool(tr.pose.tool, tr.pose.cartZ);
      if (j) minMargin = Math.min(minMargin, ...(['A', 'B', 'C', 'D'] as const).map((id) => Math.min(j[id] - (id === 'A' ? -110 : id === 'B' ? -100 : id === 'C' ? -97 : -95), (id === 'A' ? 110 : id === 'B' ? 100 : id === 'C' ? 97 : 95) - j[id])));
      const c = podContact(tm, td);
      if (c.depth < 0) { touched++; if (-c.depth * 1000 > worstMm) { worstMm = -c.depth * 1000; names = c.names; } }
    }
    // Pond #230 round 7: the pod holder is straight (cart_pod_holder.py v3, 90 degrees) and the tray is in the tank; every step is in reach and touches nothing.
    const info = `unreachable frames ${unreachable}, touching frames ${touched} ${names} ${worstMm.toFixed(2)} mm, joint margin ${minMargin.toFixed(0)} deg`;
    check(`transplant: ${STEPS[s].title}: no contacts`, touched === 0, info);
    check(`transplant: ${STEPS[s].title}: in reach, inside the joint limits`, unreachable === 0 && minMargin > 5, info);
  }
  check('transplant: all steps done, pod in the hole, plug parked, cart at the hole', tr.done && tr.pose.places.pod === 'seat' && tr.pose.places.plug === 'park' && Math.abs(tr.pose.cartZ - CART_Z1) < 1e-9);
  check('transplant: hole was open once, for under 15 s', tr.holeTimes.length === 1 && tr.holeTimes[0] > 0 && tr.holeTimes[0] < 15, JSON.stringify(tr.holeTimes));
  // Play all gives the same end state
  tr.reset(); tr.playAll(); let guard = 0; while ((tr.busy || tr.next < STEPS.length) && guard++ < 20000) tr.advance(0.05);
  check('transplant: Play all runs the four steps', tr.done && tr.pose.places.pod === 'seat' && tr.pose.places.plug === 'park', `${tr.next}`);
  // the contact check can fail: a plug dragged into the pipe is caught
  tr.reset(); tr.pose.places.plug = 'hand'; tr.pose.cartZ = CART_ZP;
  { const t = toolOf([0.036 * Math.cos(PSI), 0.036 * Math.sin(PSI), ZP - 0.03], [-Math.cos(PSI), -Math.sin(PSI), 0], CART_ZP); tr.pose.tool = { x: t.x, y: t.y, z: t.z, phi: t.phi }; }
  check('transplant: the pipe-wall test pose is in reach', bind.apply(tr.pose));
  check('transplant: a part pushed into the pipe is a contact', podContact(tm, td).depth < -0.002);
  // Pond #284: the omni cart on the -y leg: hand C on the track, hand B beside it with its jaw open, no hinges.
  {
    const xml = transplantMjcf();
    const jb = tm.body('jawB'), jc = tm.body('jawC'), qb = [0, 1, 2, 3].map((k) => tm.body_quat[4 * jb.id + k]), qc = [0, 1, 2, 3].map((k) => tm.body_quat[4 * jc.id + k]); jb.delete(); jc.delete();
    check('transplant: the real omni cart (plate, battery, two three-lobe sleeves with omni wheels and ball cups), no hinge, worm or tongue, and the arm\'s own base (no armbase block)', xml.includes('name="lobeCo"') && xml.includes('name="battery"') && !xml.includes('name="armbase"') && !/worm|tongue/i.test(xml) && !xml.includes('name="hinge'));
    check('transplant: the free hand (B) has its jaw open 92 degrees and the riding hand (C) is closed', Math.abs(2 * Math.asin(Math.abs(qb[3])) * 180 / Math.PI - 92) < 0.1 && Math.abs(qc[0] - 1) < 1e-9);
    check('transplant: the arm base is on the battery front, 106 mm out of the pipe plane (plate face -56, battery 50) and the cup root 18 mm out of the plate face', Math.abs(ARM_CY + 0.106) < 1e-12 && Math.abs(CUP_ROOT[1] + 0.074) < 1e-12);
    // lowest stop: the sleeve's -60 degree lobe touches the track corner just below 0.64 m
    tr.reset();
    const probe = (z: number) => { const p = tr.pose; const was = p.cartZ; p.cartZ = z; bind.apply(p); const d = podContact(tm, td); p.cartZ = was; return d; };
    const lo = probe(CART_Z0), below = probe(CART_Z0 - 0.015);
    check('transplant: the first stop (0.64 m) is the lowest the new sleeve can go on the straight leg: clear there, the lobe touches the track corner 15 mm lower', lo.depth === 0 && below.depth < 0 && /trackc/.test(below.names), `${lo.names} ${below.names}`);
    bind.apply(tr.pose);
  }
  check('transplant: pod holder is where the CAD puts it (not lowered) and the start is the seedling tray height', CUP_DROP === 0 && CART_Z0 < CART_Z1);
  check('transplant: pod holder is straight (90 degrees to the plate: cup axis horizontal) and the tray stands inside the tank, under the lid', D_CUP[2] === 0 && D_CUP[0] === -1 && TRAY_CAP_TOP[2] < LID_TOP);
  td.delete(); tm.delete();
}

// Reach test scene
{
  const { HOLES, PODS, reachMjcf, seatCapTop, podCapTop } = await import('../src/reach/layout.ts');
  const { refStation, stations, toRef } = await import('../src/reach/station.ts');
  const { runReach, summary, Rig, ANGLE_TOL } = await import('../src/reach/test.ts');
  const { checkPass } = await import('../src/reach/pass.ts');
  const { GRIP_TX, GRIP_TZ } = await import('../src/transplant/layout.ts');
  const rm = mj.MjModel.from_xml_string(reachMjcf()), rd = new mj.MjData(rm), rig = new Rig(mj, rm, rd);
  check('reach: 24 holes (3 columns 120 degrees apart, 8 levels 130 mm apart, every other level turned 60) and 16 pods (4 x 4)', HOLES.length === 24 && PODS.length === 16 && new Set(HOLES.map((h) => h.z.toFixed(3))).size === 8 && Math.abs(HOLES[3].z - HOLES[0].z - 0.13) < 1e-9 && Math.abs(HOLES[3].cadDeg - HOLES[0].cadDeg - 60) < 1e-9);
  check('reach: every hole has its plug and every pod its body in the model', HOLES.every((h) => rm.body(`plug${h.n}`).id > 0 && rm.body(`collar${h.n}`).id > 0) && PODS.every((p) => rm.body(`pod${p.n}`).id > 0));
  rig.pose(refStation(0.635), { A: 0, B: 0, C: 0, D: 0, E: 0 });
  check('reach: the folded arm at the lowest cart stop touches nothing (no contacts)', podContact(rm, rd).depth === 0, podContact(rm, rd).names);
  const res = runReach(mj, rm, rd), sm = summary(res);
  check('reach: every hole and pod has a colour, counts add up', res.length === 40 && sm.holes.green + sm.holes.amber + sm.holes.red === 24 && sm.pods.green + sm.pods.amber + sm.pods.red === 16);
  check('reach: red parts say why', res.filter((t) => t.colour === 'red').every((t) => t.direct.reason && t.rolled.reason));
  let bad = '';
  for (const t of res) for (const [rolled, a] of [[false, t.direct], [true, t.rolled]] as const) {
    if (!a.ok) continue;
    rig.pose(a.station!, a.joints!, 30);
    if (a.station!.roll !== (rolled ? 180 : 0)) bad += ` ${t.id}: wrong roll`;
    const hid = rm.body('hand').id, R = [0, 1, 2, 3, 4, 5, 6, 7, 8].map((k) => rd.xmat[9 * hid + k]);
    const tool = [0, 1, 2].map((r) => rd.xpos[3 * hid + r] + R[3 * r] * GRIP_TX + R[3 * r + 2] * GRIP_TZ);
    const miss = Math.hypot(tool[0] - t.pos[0], tool[1] - t.pos[1], tool[2] - t.pos[2]);
    // the target's own geoms are not tested for contacts here (they are gripped), everything else must be clear
    if (miss > 0.002) bad += ` ${t.id}${rolled ? 'r' : ''}: hand ${(miss * 1000).toFixed(1)} mm off`;
  }
  check('reach: for every green or amber part the posed hand really is on the cap-top point (rolled poses too)', bad === '', bad);
  check('reach: amber only when the roll works and the plain pose does not', res.every((t) => (t.colour === 'amber') === (!t.direct.ok && t.rolled.ok)));
  check('reach: the angle tolerance is a few degrees', ANGLE_TOL > 0 && ANGLE_TOL <= 10);
  { const A0 = stations('leg A', 0)[10], A180 = stations('leg A', 180)[10], B0 = stations('leg B', 0)[10], B180 = stations('leg B', 180)[10];
    check('reach: rolling 180 degrees about leg A keeps the sleeve on leg A (leg axis x = 0.06, y = -0.29 is the mid point of the two cart origins); leg B is the mirror on y = +0.29', Math.abs((A0.pos[0] + A180.pos[0]) / 2 - 0.06) < 1e-9 && Math.abs((A0.pos[1] + A180.pos[1]) / 2 + 0.29) < 1e-9 && Math.abs((B0.pos[1] + B180.pos[1]) / 2 - 0.29) < 1e-9);
    const p: [number, number, number] = [0.1, -0.2, 0.5], q = toRef(A180, p);
    check('reach: a target seen from a rolled station and put back by the roll is where it was', Math.abs(q[0] - (2 * 0.06 - p[0])) < 1e-9 && Math.abs(q[1] - (2 * (-0.23 - 0.06) - p[1])) < 1e-9);
    check('reach: stations cover both legs and both runs, 208 heights on a leg (0.635 to 1.67 m, the new sleeve cannot go to 0.63)', stations('leg A', 0).length === 208 && stations('leg B', 180).length === 208 && stations('bottom run', 0).length > 20 && stations('top run', 180).length > 20); }
  check('reach: hole cap-top points are on the 45 degree seat axes', HOLES.every((h) => { const p = seatCapTop(h); return Math.hypot(p[0], p[1]) > 0.05 && p[2] > h.z; }) && podCapTop(PODS[0])[2] < 0.304 && PODS.every((p) => p.x > 0 && p.y < 0));   // the tray is in the tank's front (+x) half, on the leg-A side
  const ps = checkPass(mj, rm, rd, [0, 180]);
  check('reach: the bracket / pipe pass check runs for the top and bottom run, as is and rolled', ps.length === 4 && ps.every((p) => p.steps > 10));
  // OpenPocket #313: the cart turned 90 degrees (roll 270 = 180 + 90 ccw from above) on leg A, the 15-degree sweep, the ghost neighbour
  const { GHOST_DY, setGhostCollide } = await import('../src/reach/layout.ts');
  const { SWEEP_ANGLES, TURN_90, classifier, clashes, runSweep } = await import('../src/reach/sweep.ts');
  const side = classifier(rm);
  setGhostCollide(rm, true); rig.place([0.2, -GHOST_DY, 1.0], [1, 0, 0, 0], { A: 0, B: 0, C: 0, D: 0, E: 0 }, 0);
  check('reach sweep: the ghost neighbour on the left is an obstacle when switched on (cart put into it touches it) and none when off', clashes(rm, rd, side).some((c) => c.scene === 'neighbour unit') && (setGhostCollide(rm, false), rig.place([0.2, -GHOST_DY, 1.0], [1, 0, 0, 0], { A: 0, B: 0, C: 0, D: 0, E: 0 }, 0), !clashes(rm, rd, side).some((c) => c.scene === 'neighbour unit')));
  const sw = await runSweep(mj, rm, rd, [0, 180, TURN_90, 255]);
  const t90 = sw.targets.find((t) => t.id === 'H24')!;
  check('reach sweep: 24 angles in 15 degree steps, the 90 degree turn is 270', SWEEP_ANGLES.length === 24 && SWEEP_ANGLES[1] === 15 && TURN_90 === 270);
  check('reach sweep: as before, nothing is reached with the cart as it is or rolled 180; turned 90 ccw (270) some holes are, no pod', sw.counts[0].holes === 0 && sw.counts[1].holes === 0 && sw.counts[2].holes > 0 && sw.counts[2].pods === 0, JSON.stringify(sw.counts));
  check('reach sweep: every pose that passes touches nothing (all obstacles, neighbour included)', sw.poseClashes === 0 && t90.cell90.withNeighbour.ok);
  check('reach sweep: every part has a colour and the best angle is one that reaches it', sw.targets.length === 40 && sw.targets.every((t) => (t.best === null) === (t.colour90 === 'red') && (!t.best || t.best.own.ok)));
  rd.delete(); rm.delete();
}

// --- Omni-wheel cart model (OpenPocket #281, plan task 265 part 7): src/cart/omni.ts ---------------------------------------------------------------------
{
  const py = (fl: string) => readFileSync(new URL(`../../cad/${fl}`, import.meta.url), 'utf8');
  const num = (src: string, name: string) => {
    const one = src.match(new RegExp(`^${name}\\s*=\\s*(-?[0-9.]+)\\s*(#|$)`, 'm')); if (one) return parseFloat(one[1]);
    for (const mm of src.matchAll(/^([A-Z_0-9]+(?:\s*,\s*[A-Z_0-9]+)+)\s*=\s*(-?[0-9.]+(?:\s*,\s*-?[0-9.]+)+)/gm)) { const ns = mm[1].split(',').map((q) => q.trim()), vs = mm[2].split(',').map(parseFloat), i = ns.indexOf(name); if (i >= 0) return vs[i]; }
    return NaN;
  };
  const cd = py('cart_dims.py'), hs = py('hand_sleeve.py'), co = py('cart_omni.py');
  const bad = [['PIPE_SPACING', cd, OC.PIPE_SPACING], ['PLATE_T', cd, OC.PLATE_T], ['ARM_BASE_W', cd, OC.ARM_BASE_W], ['MOTOR_R', cd, OC.MOTOR_R], ['MOTOR_L', cd, OC.MOTOR_L],
    ['ROW_Z', hs, OC.ROW_Z], ['TUBE_R_MIN', hs, OC.TUBE_R_MIN], ['END_WALL', hs, OC.END_WALL], ['PAD_X0', hs, OC.PAD.x0], ['PAD_X1', hs, OC.PAD.x1], ['PAD_Y0', hs, OC.PAD.y0], ['PAD_Y1', hs, OC.PAD.y1],
    ['PIPE_D', co, 2 * OC.R_PIPE], ['BALL_D', co, OC.BALL_D], ['GB_T', co, OC.GB_T], ['GB_L', co, OC.GB_L]].filter(([n, src, v]) => num(src as string, n as string) !== v).map((x) => x[0]);
  check('omni cart numbers in cart/omni.ts equal cad/cart_dims.py, hand_sleeve.py and cart_omni.py', bad.length === 0, bad.join(','));
  check('derived: sleeve 124 long, outer lobe 61, plate -80..80 and -56..-50, wheel reach 54', OC.SLEEVE_L === 2 * OC.ROW_Z + 2 * OC.OMNI_R + 2 + 2 * OC.END_WALL && OC.R_ARM_OMNI === OC.OMNI_REACH + 3 + OC.END_WALL && OC.PLATE_X0 === -80 && OC.PLATE_X1 === 80 && OC.PLATE_Y0 === -56 && OC.OMNI_REACH === 54);

  const om = mj.MjModel.from_xml_string(OC.omniCartMjcf()), od = new mj.MjData(om);
  const gid = (n: string) => om.geom(n).id;
  check('omni cart: no hinge, worm or tongue geoms and no hinge1/hinge2 joints; rigid base is one body', !/worm|tongue|hinge[12]/i.test(OC.omniCartBody()) && ['hinge1', 'hinge2'].every((n) => { try { om.jnt(n); return false; } catch { return true; } }) && om.body(om.geom_bodyid[gid('plate')]).name === 'base' && om.body(om.geom_bodyid[gid('armbase')]).name === 'base');
  check('omni cart: 6 actuators (2 drive, 2 roll motor, 2 roll joint), 2 roll joints, 4 wheel spin joints, 8 passive ball joints', om.nu === 6 && om.nmocap === 1 && [...Array(om.njnt).keys()].filter((j) => om.jnt_type[j] === 3 && /^roll[BC]$/.test(om.jnt(j).name)).length === 2 && OC.WHEEL_JOINTS.every((n) => om.jnt(n).id >= 0) && [...Array(om.njnt).keys()].filter((j) => om.jnt_type[j] === 1).length === 8);
  const nCon = () => { mj.mj_forward(om, od); return od.ncon; };
  const model = om as unknown as Parameters<typeof OC.setOmniCart>[0];
  const place = (o: Parameters<typeof OC.setOmniCart>[2]) => OC.setOmniCart(model, od as any, o);
  place({ roll: 0 });
  check('omni cart clamped on both pipes at roll 0: no contact (wheels and balls 0.3 mm off the pipes, sleeve bores clear)', nCon() === 0, `ncon ${od.ncon}`);
  const worldXY = (n: string) => [od.geom_xpos[3 * gid(n)], od.geom_xpos[3 * gid(n) + 1]];
  const hit = (staticHand: 'B' | 'C', pipes: { pipeB: boolean; pipeC: boolean }) => {
    const mm = mj.MjModel.from_xml_string(OC.omniCartMjcf(pipes)), dd = new mj.MjData(mm); let worst = 0;
    for (let deg = -360; deg <= 360; deg += 5) { OC.setOmniCart(mm as any, dd as any, { roll: (deg * Math.PI) / 180, staticHand }); mj.mj_forward(mm, dd); worst = Math.max(worst, dd.ncon); }
    mm.delete(); dd.delete(); return worst;
  };
  check('omni cart rolled a full turn both ways about pipe C (hand B released, off its pipe): no contact at any 5 degrees', hit('C', { pipeB: false, pipeC: true }) === 0);
  check('omni cart rolled a full turn both ways about pipe B (hand C released): no contact at any 5 degrees', hit('B', { pipeB: true, pipeC: false }) === 0);
  check('rolling about pipe C with pipe B still clamped drives hand B into it (the contact check does see the swept sleeve)', hit('C', { pipeB: true, pipeC: true }) > 0);
  place({ roll: Math.PI / 2, staticHand: 'C' }); nCon();
  const [px, py_] = worldXY('plate');
  check('roll is about the static pipe axis: the plate (at x 0, y -53) quarter-turns about pipe C (x +60) to x = 60 + 53, y = -60', Math.abs(px - 0.113) < 1e-6 && Math.abs(py_ + 0.06) < 1e-6, `${px},${py_}`);
  place({ roll: Math.PI / 2, staticHand: 'B' }); nCon();
  check('roll about pipe B by +90 deg: plate (relative 60, -53) goes to x = -60 + 53 = -7 mm, y = +60 mm', Math.abs(worldXY('plate')[0] + 0.007) < 1e-6 && Math.abs(worldXY('plate')[1] - 0.06) < 1e-6, String(worldXY('plate')));
  place({ roll: 0 }); nCon();
  const x = (n: string) => od.geom_xpos[3 * gid(n)];
  check('hand C is the true mirror of hand B across x = 0 (outer lobe, +/-60 deg lobes, pad)', ['o', 'p', 'm'].every((k) => Math.abs(x(`lobeB${k}`) + x(`lobeC${k}`)) < 1e-9) && Math.abs(x('padB') + x('padC')) < 1e-9 && Math.abs(x('lobeBo') - (-0.06 - 0.0395)) < 1e-4);
  check('outer lobes face away from the neighbour (B at -x of its pipe, C at +x), pads too', x('lobeBo') < -0.06 && x('lobeCo') > 0.06 && x('padB') < -0.06 && x('padC') > 0.06);
  // omni friction model and roll budget
  const c = OC.omniContact(20);
  check('omni friction: grip along the rolling direction mu x N = 6 N at 20 N, across it 50 times less', Math.abs(c.along - 6) < 1e-9 && c.across * 50 <= c.along + 1e-9);
  const rb = OC.rollBudget();
  check('roll kinematics: a carried motor turns the sleeve at wheelR / pipeR times its speed (71 rpm for 60 rpm), 180 degrees in about 0.4 s', Math.abs(rb.rollRpm - 60 * 19 / 16) < 1e-9 && rb.t180S < 0.5, `${rb.rollRpm} rpm`);
  check('roll torque: motor gives T x pipeR / wheelR = 0.25 N m, friction holds only 0.096 N m at 20 N and mu 0.3: far below the 2.9 N m worst load, so the roll hold stays the plan\'s first risk', Math.abs(rb.motorRollNm - 0.3 * 16 / 19) < 1e-9 && Math.abs(rb.frictionRollNm - 0.0960) < 1e-6 && !rb.wornOk && rb.preloadNeededRollN > 100 * 2);
  // rolling without slipping: wheel spin relative to the sleeve = (pipeR / wheelR) x sleeve angle gives zero contact velocity
  const L = OC.OMNI_AXLE_R, phi = 1, spinRel = phi * OC.rollSpinPerRoll(), abs = phi + spinRel;
  check('roll wheel contact does not slip: absolute wheel spin x wheelR = sleeve angle x lever', Math.abs(abs * OC.OMNI_R - phi * L) < 1e-9);
}

// --- Cart on track with the omni cart (OpenPocket #282, plan task 265 part 8) -------------------------------------------------------------------------------
{
  const tm = mj.MjModel.from_xml_string(omniTrackMjcf()), td = new mj.MjData(tm);
  for (let i = 0; i < tm.ngeom; i++) tm.geom_margin[i] = 0.0002;
  const at = (s: number, rollDeg = 0, trim = NO_TRIM) => { placeOmniCart(tm as any, td as any, s, (rollDeg * Math.PI) / 180, trim); mj.mj_forward(tm, td); return trackContacts(tm as any, td as any); };
  const touch = (c: Record<string, number>) => Math.min(c.rider, c.freehand, c.base);
  check('cart on track: flat, riding on hand B, no contact with the track at every 5 cm on the leg and on the run', [5, 10, 20, 30, 40, 50, 100, 110, 120, 140].every((s) => touch(at(s)) >= -1e-9));
  // the riding pipe axis really sits on the track (hand B body frame)
  at(30); const hb = tm.body('handB').id;
  check('hand B\'s pipe axis is on the track centre line on the leg (x 0, z 0.30)', Math.abs(td.xpos[3 * hb]) < 1e-6 && Math.abs(td.xpos[3 * hb + 2] - 0.3) < 1e-6, `${td.xpos[3 * hb]},${td.xpos[3 * hb + 2]}`);
  at(110); check('and on the run (x past the bend, z = 0.75)', Math.abs(td.xpos[3 * hb + 2] - 0.75) < 1e-6 && td.xpos[3 * hb] > 0.15);
  const rollClear = (dir: 1 | -1, s: number) => sweep(0, dir * 180, 5).every((a) => { const c = at(s, a); return c.rider >= -1e-9 && c.freehand >= -1e-9 && c.base >= -1e-9; });
  check('roll on the leg, both directions, 0 to 180 in 5 degree steps: rider, free hand and base never touch the track (Q3: both clear, + chosen)', rollClear(1, 30) && rollClear(-1, 30) && pickRollDirection({ plus: true, minus: true }).dir === 1);
  check('Q3: if only one direction clears the controller uses that one; if neither does it stops and asks the owner', pickRollDirection({ plus: false, minus: true }).dir === -1 && pickRollDirection({ plus: false, minus: false }).dir === null);
  // roll held through the bend (Q7), free hand and base only
  const heldClear = (dir: 1 | -1) => { for (let s = L_VERT - 4; s <= L_VERT + L_ARC + 4; s += 2) for (let a = 0; a <= 180; a += 30) { const c = at(s, dir * a, bendTrim(s)); if (c.freehand < -1e-9 || c.base < -1e-9) return false; } return true; };
  check('roll held through the bend (Q7), both directions: the free hand and the base clear the curved track at every 2 cm and every 30 degrees', heldClear(1) && heldClear(-1));
  // the bend with the rigid sleeve: the finding of this scene. The straight 124 mm sleeve does not follow the R150 bend: the best trim still hits.
  let worstBend = 0, worstZero = 0;
  for (let s = L_VERT; s <= L_VERT + L_ARC; s += 1) { worstBend = Math.min(worstBend, at(s, 0, bendTrim(s)).rider); worstZero = Math.min(worstZero, at(s, 0).rider); }
  check('bend: the rigid sleeve on R150 hits the pipe even with the best trim (about 4 mm deep; update BEND_TRIM_ROWS and this test when the sleeve or bore changes)', worstBend < -0.003 && worstBend > -0.0045, `${(worstBend * 1000).toFixed(2)} mm`);
  check('bend: the trim rows help (the trimmed worst penetration is smaller than with no trim)', worstBend > worstZero + 0.001, `${(worstZero * 1000).toFixed(2)} mm untrimmed`);
  check('bend trim is zero on the straights and rows run in order', bendTrim(30).dx === 0 && bendTrim(100).yaw === 0 && BEND_TRIM_ROWS.every((r, i, a) => i === 0 || a[i - 1][0] < r[0]));
}
{
  const runStart = L_VERT + L_ARC;
  check('roll allowed on the vertical leg up to 180 degrees, refused beyond', canRoll(30, 180).ok && canRoll(30, -180).ok && !canRoll(30, 181).ok);
  check('Q7: no roll change on the bend; Q8: no roll on the top and bottom runs (cart stays flat)', !canRoll(L_VERT + 5, 20).ok && !canRoll(runStart + 10, 20).ok && !canRoll(runStart + 10, 0).ok);
  check('interlock: flat (within 3 degrees) drives anywhere; rolled without a declared transfer roll does not drive', driveLimit(30, 90, 2, false, runStart).s === 90 && driveLimit(30, 90, 20, false, runStart).s === 30 && ROLL_HOME_TOL_DEG === 3);
  check('interlock: a carried roll goes up the leg and round the bend but stops at the start of the run', driveLimit(30, 50, 90, true, runStart).s === 50 && driveLimit(30, 120, 90, true, runStart).s === runStart);
  const rm = new RollMotion(); rm.moveTo(180); let t = 0; while (!rm.advance(0.01) && t < 5) t += 0.01;
  check('roll motion reaches 180 degrees in about half a second without turning back', rm.roll === 180 && t < 0.6, `${t.toFixed(2)} s`);
  // sensing and homing
  check('hall sensor: the ring is seen at any roll, the point magnet only at roll 0 and its column', hall(RING_CM, 123).ring && !hall(RING_CM + 3, 0).ring && hall(POINT_CM, 2).point && !hall(POINT_CM, 40).point && !hall(POINT_CM + 2, 0).point);
  let homed = 0, worstS = 0, worstR = 0;
  for (const s0 of [0, 3, 12, 25, 40, 55, 70, 100, 140]) for (const r0 of [0, 37, -120, 180]) {
    const r = runHoming(s0, r0, { slip: 0.03, rollSlip: 0.05 });
    if (r.ok) { homed++; worstS = Math.max(worstS, Math.abs(r.sErr)); worstR = Math.max(worstR, Math.abs(r.rollErr)); }
  }
  check('homing from any start (leg, bend, run, rolled any way) finds the ring, then the point, and ends within 0.5 cm and 2 degrees', homed === 36 && worstS <= 0.5 && worstR <= 2, `${homed}/36, worst ${worstS.toFixed(2)} cm ${worstR.toFixed(1)} deg`);
  // the CAD's home station (cad/home_station.py, OpenPocket #286) uses the same ring and point positions as the controller
  {
    const hsPy = readFileSync(new URL('../../cad/home_station.py', import.meta.url), 'utf8');
    const n = (name: string) => parseFloat(hsPy.match(new RegExp(`^${name}\\s*=\\s*(-?[0-9.]+)`, 'm'))?.[1] ?? 'NaN');
    check('CAD home station: ring at RING_CM, point at POINT_CM, tape 10 mm = RING_W_CM, 6 mm point magnet is wider than the sensor window (homing.ts)', n('RING_CM') === RING_CM && n('POINT_CM') === POINT_CM && n('RING_W') === RING_W_CM * 10 && (n('POINT_D') / 16) * 180 / Math.PI > 2 * POINT_WINDOW_DEG, `${n('RING_CM')} ${n('POINT_CM')} ${n('RING_W')}`);
  }
  const lost = runHoming(2, 90);
  check('homing from just below the ring: hits the base end, turns round and finds the ring', lost.ok && lost.steps.some((x) => /turning round/.test(x)));
  // pipe sag (Q1, Q6)
  const rows = sagTable();
  const row = (name: string, span: number) => rows.find((r) => r.pipe.startsWith(name) && r.spanMm === span)!;
  check('sag: 25 mm PVC is NOT stiff enough (creep sag at the end of the straight run over 4 mm, limit 2 mm)', !row('25 mm PVC (1.5', 140).ok && row('25 mm PVC (1.5', 140).creepMm > 4);
  check('sag: 32 mm with the 3 mm wall holds the end of the straight run (creep sag under 2 mm), the 1.8 mm wall is marginal; the corner end needs a support either way', row('32 mm PVC (3.0', 140).ok && !row('32 mm PVC (1.8', 140).ok && !row('32 mm PVC (3.0', 290).ok);
  check('sag: longest unsupported run from a support, long term, is about 138 mm for 32 x 1.8 and about 101 mm for 25 x 1.5 at the cart load', maxCantileverMm(PIPES[0]) > 130 && maxCantileverMm(PIPES[0]) < 145 && maxCantileverMm(PIPES[2]) > 95 && maxCantileverMm(PIPES[2]) < 105 && LOAD_N > 40, `${maxCantileverMm(PIPES[0]).toFixed(0)} / ${maxCantileverMm(PIPES[2]).toFixed(0)} mm`);
  // track supports (OpenPocket #315): sag with the supports, same numbers as docs/bench-test/track_support_sag.py
  const bNo = TS.bottomSag(TS.E_HOT, false), bYes = TS.bottomSag(TS.E_HOT), tNo = TS.topSag(TS.E_HOT, false), tYes = TS.topSag(TS.E_HOT);
  check('supports: bottom run 32 x 1.8, L 300, support at 125: creep sag about 0.19 mm, hot and crept under 1 mm; without it a hot day is at the 1 mm limit', Math.abs(TS.bottomSag() - 0.19) < 0.02 && bYes < TS.BOTTOM_LIMIT_MM && bNo > 0.95, `${TS.bottomSag().toFixed(2)} / ${bYes.toFixed(2)} / ${bNo.toFixed(2)} mm`);
  check('supports: top run L 400 with the brace and the bend on the leg spring: creep about 0.36 mm, hot and crept under 3 mm and below the unbraced run', Math.abs(TS.topSag() - 0.36) < 0.03 && tYes < TS.TOP_LIMIT_MM && tYes < tNo / 3, `${TS.topSag().toFixed(2)} / ${tYes.toFixed(2)} / ${tNo.toFixed(2)} mm`);
  check('supports: the cart passes a support only at roll 0 (within the home tolerance), and the supports are only on runs where the roll is held at 0', TS.passesSupport(0) && TS.passesSupport(2.5) && !TS.passesSupport(10) && !TS.passesSupport(180) && TS.SUPPORTS_ONLY_WHERE_FLAT);
}

// --- Python sims on the omni cart (OpenPocket #283, plan task 265 part 9): sim/unit_change.py and the wet-pipe test of sim/pipe_climb.py, built by python3 and run in this MuJoCo ---
{
  const simDir = new URL('../../sim/', import.meta.url).pathname;
  const py = (code: string) => { try { return execFileSync('python3', ['-c', `import sys, json; sys.path.insert(0, ${JSON.stringify(simDir)})\n${code}`], { encoding: 'utf8', maxBuffer: 1 << 26 }); } catch { return null; } };
  const have = py('print(1)') !== null;
  if (!have) console.log('skip python sims: python3 not available');
  else {
    const uc = py('import unit_change as u; print(json.dumps({"sep": u.SEP, "swing": u.SWING, "xml": u.build()}))'), ucj = uc ? JSON.parse(uc) : null;
    check('sim/unit_change.py builds the omni cart: hands 120 mm apart, roll of 90 degrees, hand jaws, the model compiles with the 10 actuators', !!ucj && Math.abs(ucj.sep - 0.12) < 1e-9 && Math.abs(ucj.swing - Math.PI / 2) < 1e-9 && /hand1_jaw/.test(ucj.xml) && /hand2_jaw/.test(ucj.xml) && (() => { const m = mj.MjModel.from_xml_string(ucj.xml); const ok = m.nu === 10; m.delete(); return ok; })());
    check('sim/unit_change.py: no hinge-era leftovers (no worm, no knuckle), the jaw wedge is the proposed 150 degrees (constants.py) and the plate-side roll opens hand 1 CCW, hand 2 CW', !!ucj && !/worm|knuckle/.test(ucj.xml) && /JAW_A1_PROPOSED_DEG = 150\.0/.test(readFileSync(new URL('../../sim/constants.py', import.meta.url), 'utf8')) && /euler="0 0 -91\.6/.test(ucj.xml));
    const wet = py('import pipe_climb as p; d = {k: v[0] for k, v in p.PARAMS.items()}; out = []\nfor c in p.wet_test():\n    q = dict(d); q.update(c); out.append([c, p.build(**q)])\nprint(json.dumps(out))'), cases = wet ? JSON.parse(wet) as [Record<string, unknown>, string][] : [];
    const hold = (xml: string) => { const m = mj.MjModel.from_xml_string(xml), d = new mj.MjData(m), b = m.body('cart').id; mj.mj_forward(m, d); const z0 = d.xpos[3 * b + 2]; for (let i = 0; i < 3 / m.opt.timestep; i++) mj.mj_step(m, d); const dz = d.xpos[3 * b + 2] - z0; m.delete(); d.delete(); return dz; };
    const find = (surface: string, n: number) => cases.find(([c]) => c.surface === surface && c.spring_preload_n === n)?.[1];
    check('pipe_climb wet_test(): seven omni cases (wet at 20, 40, 60, 100, 140 N, dry at 20 and 50 N), locked drive', cases.length === 7 && cases.every(([c]) => c.wheel === 'omni' && c.drive_rpm === 0 && (c.drive_torque_nm as number) > 1));
    const w20 = find('wet', 20), w140 = find('wet', 140), d50 = find('dry', 50);
    if (w20 && w140 && d50) {
      const a = hold(w20), b = hold(w140), c = hold(d50), sw = hold(w140.replace(/friction="0\.006000 0\.3 /, 'friction="0.3 0.006000 '));
      check('wet pipe, 3 kg cart, drive locked: 20 N preload (the design value) slides all the way down the 0.6 m start height', a < -0.5, `${a.toFixed(3)} m`);
      check('wet pipe: 140 N preload holds (loses under 0.15 m in 3 s), 60 N does not; dry pipe holds at 50 N: grip needs 3 to 7 times the wheel rating, plan risk 1', b > -0.15 && hold(find('wet', 60)!) < -0.5 && c > -0.15, `${b.toFixed(3)} ${c.toFixed(3)}`);
      check('the omni contact is anisotropic the right way round: with the two friction values swapped the 140 N case slides', sw < -0.5 && w140.includes('friction="0.006000 0.3 '), `${sw.toFixed(3)} m`);
    }
    const plain = py('import pipe_climb as p; d = {k: v[0] for k, v in p.PARAMS.items()}; print(p.build(**d))');
    if (plain) { const m = mj.MjModel.from_xml_string(plain), d = new mj.MjData(m); d.ctrl[m.actuator('drive').id] = 2 * Math.PI; const b = m.body('cart').id; mj.mj_forward(m, d); const z0 = d.xpos[3 * b + 2]; for (let i = 0; i < 3 / m.opt.timestep; i++) mj.mj_step(m, d);
      check('pipe_climb default (the old wheels, dry, 30 N) is unchanged: the cart still climbs', d.xpos[3 * b + 2] - z0 > 0.05, (d.xpos[3 * b + 2] - z0).toFixed(3)); m.delete(); d.delete(); }
  }
}

const t0 = performance.now(); run(5); const ms = performance.now() - t0;
console.log(`5 s of sim took ${ms.toFixed(0)} ms in node`);
process.exit(fail ? 1 : 0);
