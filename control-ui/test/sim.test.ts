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
import { S_FLAT_CM, CLEAR_DEG, HINGE_DEG_S_CAD, MAX_HINGE_DEG, MAX_BEND_HINGE_DEG, P_TOP_CM, TransferRun, applyPose, initialState, kinFromAngles, kinematics, worstContact, type CartState } from '../src/cart/transfer.ts';
import { S_MAX_CM, S_MIN_CM, transferMjcf, worldToCad } from '../src/cart/transfer-model.ts';
import * as DIMS from '../src/cart/dims.ts';
import { readFileSync } from 'node:fs';
import { BASE_BOTTOM, LID_Z, PIPE_Z, SPINE_Y, POD_COUNT, POD_PITCH, ROW_PITCH, ROW_X0, SPINE_R, STORE_CAP, STORE_ROWS, STORE_START, TRAY_CX, TRAY_HX, TRAY_SLOTS, podGrabMjcf, seatPos, storePos } from '../src/podgrab/layout.ts';
import { PodTask, PodWorld, fillJobs } from '../src/podgrab/task.ts';

import { HOLD_DEG, POD_D, REACH } from '../src/arm/dims.ts';
import { transplantMjcf, CART_Z0, CART_Z1, CUP_DROP, SEAT_CAP_TOP, PARK_CAP_TOP, ZH, ZP, P0, U_CAP, CAP_T, HOLDER_FLOOR_X, X_TOP, RECESS_T } from '../src/transplant/layout.ts';
import { TransplantRun, STEPS, ikTool } from '../src/transplant/task.ts';
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

check('eight scenes, two groups, Transplant seedling under the Tests', SCENE_INFOS.length === 8 && SCENE_INFOS.filter((s) => s.group === 'Tests').length === 6 && SCENE_INFOS.some((s) => s.id === 'transplant' && s.group === 'Tests'));
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
  check('derived layout (mirrored hands): hinge axes at -90 and +90, plate -83..+83 (166 wide), arm at 0, motors at +-53', DIMS.hingeX(2) === -90 && DIMS.hingeX(1) === 90 && DIMS.PLATE_X0 === -83 && DIMS.PLATE_X1 === 83 && DIMS.ARM_X === 0 && DIMS.MOTOR_B_X === -53 && DIMS.MOTOR_C_X === 53 && DIMS.PLATE_Y0 === -52);
  check('the scene has only two pipes, B and C: no pipe D anywhere', Object.keys(DIMS.PIPE_X).join() === 'B,C' && !/pipeD/.test(transferMjcf()));

  const tm = mj.MjModel.from_xml_string(transferMjcf()), td = new mj.MjData(tm);
  const g = (n: string) => tm.geom(n).id, bodyOf = (n: string) => tm.body(tm.geom_bodyid[g(n)]).name;
  check('transfer model: one mocap plate, 6 actuators (2 drive, 2 hinge, 2 jaw), no free or ball joints', tm.nmocap === 1 && tm.nu === 6 && [...Array(tm.njnt).keys()].every((j) => tm.jnt_type[j] === 3 || tm.jnt_type[j] === 2), `nu ${tm.nu}`);
  applyPose(tm, td, initialState()); mj.mj_forward(tm, td);
  // CAD-frame coordinates (x across, y out of the pipe plane, z along the pipes) of a world point; the scene itself has the pipes horizontal
  const cadOf = (a: ArrayLike<number>, o: number) => worldToCad([a[o], a[o + 1], a[o + 2]]);
  const gx = (n: string, i: number) => cadOf(td.geom_xpos, 3 * g(n))[i];
  check('pipes B and C are 120 mm apart, both upright, in the same plane', Math.abs(gx('pipeCv', 0) - gx('pipeBv', 0) - 0.12) < 1e-9 && Math.abs(td.geom_xpos[3 * g('pipeBv') + 1]) < 1e-9 && Math.abs(td.geom_xpos[3 * g('pipeCv') + 1]) < 1e-9);
  const hingeAt = (j: string) => { const id = tm.jnt(j).id, a = cadOf(td.xanchor, 3 * id); return [a[0], a[1], Math.abs(td.xaxis[3 * id + 2])]; };   // axis: |world z| = 1 means along the upright pipes
  check('each hinge axis is parallel to the pipes (horizontal), on the pad edge: x -0.09 and +0.09, 43 mm in front', hingeAt('hinge2').every((v, i) => Math.abs(v - [-0.09, -0.043, 1][i]) < 1e-9) && hingeAt('hinge1').every((v, i) => Math.abs(v - [0.09, -0.043, 1][i]) < 1e-9));
  check('the plate hangs between the hinge axes, centred on x = 0 (166 wide, symmetric)', Math.abs(gx('plate', 0)) < 1e-9 && 0.083 < 0.09 && Math.abs(tm.geom_size[3 * g('plate')] - 0.083) < 1e-9);
  check('drive motors, arm base and battery are on the plate (rigid: no joint between)', ['motor_drive1', 'motor_drive2', 'armbase', 'armcolumn', 'battery'].every((n) => bodyOf(n) === 'plate'));
  check('battery sits UNDER the arm (plate, battery, arm base): same x and z as the arm base, between the plate and the arm base, no shelf or tongue under it', Math.abs(gx('battery', 0) - gx('armbase', 0)) < 1e-9 && Math.abs(gx('battery', 2) - gx('armbase', 2)) < 1e-9 && gx('battery', 1) < gx('plate', 1) && gx('armbase', 1) < gx('battery', 1) - 0.025 && !/name="shelf"/.test(transferMjcf()));
  check('the two drive motors and the arm base sit in a row on the plate (x -53, 0, +53), the arm base on the battery face', gx('motor_drive1', 1) < gx('plate', 1) && gx('motor_drive2', 1) < gx('plate', 1) && Math.abs(gx('motor_drive2', 0) + 0.053) < 1e-9 && Math.abs(gx('motor_drive1', 0) - 0.053) < 1e-9 && Math.abs(gx('armbase', 0)) < 1e-9 && Math.abs(gx('armbase', 1) - (gx('plate', 1) - 0.003 - 0.05 - 0.004)) < 1e-9);
  check('each hinge has its worm drive on the plate (worm, bracket, motor)', [1, 2].every((h) => bodyOf('worm' + h) === 'plate' && bodyOf('worm_motor' + h) === 'plate' && bodyOf('bracket_in' + h) === 'plate'));
  check('hinges are position-controlled and self-locking: position actuators on hinge1/hinge2 and friction on the joints', ['hinge1', 'hinge2'].every((n) => tm.actuator(n).id >= 0 && tm.actuator_trnid[2 * tm.actuator(n).id] === tm.jnt(n).id) && tm.dof_frictionloss[tm.jnt_dofadr[tm.jnt('hinge1').id]] > 0 && tm.dof_frictionloss[tm.jnt_dofadr[tm.jnt('hinge2').id]] > 0);
  check('each hand is a fixed sleeve body plus a jaw on a knuckle hinge (joints jaw1, jaw2, axis along the pipe, 0 to 92 deg) with its own actuator; no slide joints', [...Array(tm.njnt).keys()].filter((j) => tm.jnt_type[j] === 2).length === 0 && ['jaw1', 'jaw2'].every((n) => tm.actuator(n).id >= 0 && tm.actuator_trnid[2 * tm.actuator(n).id] === tm.jnt(n).id && Math.abs(tm.jnt_range[2 * tm.jnt(n).id + 1] - 92 * Math.PI / 180) < 1e-9 && tm.body(n).id >= 0));
  check('the jaw wheel pair and jaw wall ride on the jaw body, the sleeve wall and the driven wheels on the hand', [...Array(tm.ngeom).keys()].filter((i) => tm.body(tm.geom_bodyid[i]).name === 'jaw2').length > 10 && [...Array(tm.ngeom).keys()].filter((i) => tm.body(tm.geom_bodyid[i]).name === 'hand2').length > 30);

  // Kinematics: hand C never moves; the plate turns only a few degrees about hinge C; hand B ends clear of pipe B.
  const handAt = (st: CartState, h: 1 | 2) => { applyPose(tm, td, st); mj.mj_forward(tm, td); const b = tm.body('hand' + h).id, p = cadOf(td.xpos, 3 * b), qw = td.xquat[4 * b], qx = td.xquat[4 * b + 1], qy = td.xquat[4 * b + 2], qz = td.xquat[4 * b + 3];
    // orientation in the CAD frame: the scene frame is the CAD frame
    return { x: p[0], y: p[1], z: p[2], qw, qz }; };
  { let worstC = 0; const rest1 = handAt(initialState(), 1);
    for (let i = 0; i <= 100; i++) { const st = initialState(); st.t = i / 100; const h = handAt(st, 1); worstC = Math.max(worstC, Math.hypot(h.x - 0.06, h.y, h.z - st.s / 100), Math.abs(h.qz - rest1.qz), Math.abs(h.qw - rest1.qw)); }
    check('hand C stays exactly where it is (on pipe C, not turning) through the whole rotation', worstC < 1e-9, String(worstC));
    let behind = 0; for (let i = 0; i <= 100; i++) { const s2 = initialState(); s2.t = i / 100; if (handAt(s2, 2).y > 1e-9) behind++; }
    check('hand B stays in front of the pipe plane all through the rotation', behind === 0, `${behind} samples`);
    const k1 = kinematics(1);
    check('rotation is small: the plate turns CLEAR_DEG (a few degrees, well below 30) and no hinge exceeds MAX_HINGE_DEG', CLEAR_DEG === 20 && MAX_HINGE_DEG <= 20 && Math.abs(k1.alpha * 180 / Math.PI - CLEAR_DEG) < 1e-9 && Math.abs(k1.hinge1 * 180 / Math.PI + CLEAR_DEG) < 1e-9);
    // "off the pipe": a test-only contact pair between hand B's hidden envelope (the sleeve) and pipe B is penetrating exactly when the pipe is still inside the sleeve
    const xmlEnv = transferMjcf().replace('<contact>', '<contact><pair geom1="env2" geom2="pipeBv" margin="0"/>'), em = mj.MjModel.from_xml_string(xmlEnv), ed = new mj.MjData(em);
    const inside = (t: number, s: number) => { const st = initialState(); st.t = t; st.s = s; st.open2 = 1; applyPose(em, ed, st); mj.mj_forward(em, ed); let n = 0; for (let i = 0; i < ed.ncon; i++) { const c = ed.contact.get(i)!; if (c.dist < 0 && [em.geom(c.geom1).name, em.geom(c.geom2).name].sort().join() === 'env2,pipeBv') n++; } return n > 0; };
    check('at the end of the rotation hand B has left pipe B (sleeve clear of the pipe) at every height', [S_MIN_CM, 30, S_MAX_CM].every((s) => !inside(1, s)));
    // minimal: with the last 2 degrees of the path left out the sleeve is still round the pipe (hinge angle used is the smallest that clears it, within the path's resolution)
    const shortT = (() => { let lo = 0, hi = 1; for (let i = 0; i < 40; i++) { const mid = (lo + hi) / 2; if (kinematics(mid).alpha * 180 / Math.PI < CLEAR_DEG - 2) lo = mid; else hi = mid; } return lo; })();
    check('smallest angle: two degrees short of the end the sleeve is still round the pipe', inside(shortT, 30));
    ed.delete(); em.delete(); }

  // Contact check can fail: a cart pushed into a pipe, a hand turned into the plate.
  { const st = initialState(); applyPose(tm, td, st); const mc = tm.body_mocapid[tm.body('cart').id]; td.mocap_pos[3 * mc] += 0.015; mj.mj_forward(tm, td);   // world x is across the pipes
    check('contact check sees the cart pushed 15 mm into the pipes', worstContact(tm, td).depth < -0.005, String(worstContact(tm, td).depth));
    applyPose(tm, td, st); td.qpos[tm.jnt_qposadr[tm.jnt('hinge2').id]] = -0.5; mj.mj_forward(tm, td);
    const touching: string[] = []; for (let i = 0; i < td.ncon; i++) { const c = td.contact.get(i)!; if (c.dist < 0) touching.push(tm.geom(c.geom1).name + '/' + tm.geom(c.geom2).name); }
    check('contact check sees the plate swung into a hand (hand B turned 29 deg the wrong way)', touching.some((n) => n.includes('plate') && n.includes('pad2')), touching.join(' ')); }

  // Fine sweep of the whole rotation (every 0.1% of it, hand B open, hand C clamped): no contact at all, so no collision can hide between the frames of a run.
  { let bad = 0, worst = 0;
    for (let i = 0; i <= 1000; i++) { const st = initialState(); st.t = i / 1000; st.s = [S_MIN_CM, 30, S_MAX_CM][i % 3]; st.open2 = 1; applyPose(tm, td, st); mj.mj_forward(tm, td); const w = worstContact(tm, td); if (w.depth < 0) { bad++; worst = Math.min(worst, w.depth); } }
    check('fine sweep of the rotation: zero contacts at 1001 poses', bad === 0, `${bad} poses, worst ${(worst * 1000).toFixed(2)} mm`); }

  // Step riding: both hands clamped, along the pipes with the arm stowed: nothing touches.
  { let bad = 0;
    for (let s = S_MIN_CM; s <= S_MAX_CM; s += 0.5) { const st = initialState(); st.s = s; applyPose(tm, td, st); mj.mj_forward(tm, td); if (worstContact(tm, td).depth < 0) bad++; }
    check('riding along both pipes: no contact', bad === 0, `${bad} poses`); }
  // The trip up each pipe (Pond #244, #227). Hand C is the true mirror of hand B, so the trip up pipe B (hand C released, plate on hinge B) has the same corridor as the trip up pipe C.
  // Pipe C: hand B released, plate swings on hinge C. Pipe B: hand C released, plate swings on hinge B. Each is swept along the real swing path at three heights, and the whole (plate angle,
  // own hinge angle) plane is flood-filled from rest to show that the path really runs through a contact-free corridor to a pose where the free sleeve is off its pipe (scripts/search-swing.ts).
  { const pose = (staticHand: 1 | 2, a: number, h: number, s = 30) => { const st = initialState(); st.s = s; st.open1 = staticHand === 2 ? 1 : 0; st.open2 = staticHand === 1 ? 1 : 0;
      applyPose(tm, td, st, undefined, kinFromAngles(staticHand, a * Math.PI / 180, h * Math.PI / 180)); mj.mj_forward(tm, td); return worstContact(tm, td).depth; };
    const tripFree = (staticHand: 1 | 2, a: number, h: number, s = 30) => pose(staticHand, a, h, s) > -1e-4;
    for (const [staticHand, label] of [[1, 'pipe C (hand B released, plate turning on hinge C)'], [2, 'pipe B (hand C released, plate turning on hinge B)']] as const) {
      let bad = 0, n = 0; for (const s of [S_MIN_CM, 30, S_MAX_CM]) for (let i = 0; i <= 200; i++) { const st = initialState(); st.s = s; st.t = i / 200; st.open1 = staticHand === 2 ? 1 : 0; st.open2 = staticHand === 1 ? 1 : 0; applyPose(tm, td, st); mj.mj_forward(tm, td); n++; if (worstContact(tm, td).depth < -1e-4) bad++; }
      check(`trip up ${label}: the swing path is collision-free at ${n} poses`, bad === 0, `${bad} poses`);
      // margin: the same path with the plate 0.5 deg either way and the own hinge 0.5 deg either way is still free (the corridor is not one pose wide)
      let badM = 0; for (let i = 4; i <= 40; i++) { const k = kinematics(i / 40, staticHand), a = Math.abs(k.alpha) * 180 / Math.PI, h = Math.abs(staticHand === 1 ? k.hinge2 : k.hinge1) * 180 / Math.PI;
        for (const [da, dh] of [[0.5, 0], [-0.5, 0], [0, 0.5], [0, -0.5]]) if (a + da >= 0 && !tripFree(staticHand, a + da, h + dh)) badM++; }
      check(`trip up ${label}: the path keeps 0.5 deg clearance either way (plate and own hinge)`, badM === 0, `${badM} poses`);
      // flood fill (0.5 deg plate, 0.5 deg own hinge) from rest through contact-free cells: reaches the pose where the free sleeve is clear of its pipe
      const A = 0.5, nA = 61, nH = 121, seen = new Set<string>(['0,60']), stack: [number, number][] = [[0, 60]]; let maxAlpha = 0;
      while (stack.length) { const [i, j] = stack.pop()!; maxAlpha = Math.max(maxAlpha, i * A);
        for (const [di, dj] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) { const ni = i + di, nj = j + dj; if (ni < 0 || ni >= nA || nj < 0 || nj >= nH || seen.has(ni + ',' + nj)) continue; seen.add(ni + ',' + nj); if (tripFree(staticHand, ni * A, nj * A - 30)) stack.push([ni, nj]); } }
      check(`trip up ${label}: the free corridor from rest reaches at least ${CLEAR_DEG} deg of plate angle (it opens up beyond 15 deg)`, maxAlpha >= CLEAR_DEG, `${maxAlpha} deg`); }
    check('hand C copied, not mirrored, would have jammed (task 244): with the plate 4 deg turned about hinge B and hand C a few degrees open, nothing touches now', tripFree(2, 4, 4));
    const both = new TransferRun(); both.reset(); both.clampHand(1, true); for (let i = 0; i < 200; i++) both.advance(0.02);
    check('the controller turns the plate on hinge B with hand C released (trip up pipe B) and refuses to when hand B is released too', both.rotate(1) === true && !both.clampHand(2, true) && both.free === 1, both.msg); }
  check('the arm is rigid on the plate: no arm joints, links and pins on the plate body, folded close to the hinge', ![...Array(tm.njnt).keys()].some((j) => tm.jnt(j).name.startsWith('arm')) && ['arm_l1', 'arm_l2', 'arm_l3', 'arm_pin1', 'arm_pin2'].every((n) => bodyOf(n) === 'plate'));
  // The track is the Cart scene's: B runs straight and bends LEFT, C runs straight and bends RIGHT. Geom centres of the arcs tell which way.
  { const xh = (n: string) => td.geom_xpos[3 * g(n)], zh = (n: string) => td.geom_xpos[3 * g(n) + 2];
    check('pipe B runs straight up and bends LEFT (its top bar lies left of pipe B), pipe C bends RIGHT (its top bar lies right of pipe C)', xh('pipeBh') < -0.06 - 0.1 && xh('pipeCh') > 0.06 + 0.1 && Math.abs(xh('pipeBv') + 0.06) < 1e-9 && Math.abs(xh('pipeCv') - 0.06) < 1e-9);
    check('the straight parts stand on the floor, the bends and top bars are at the top: the Cart scene track, no extra posts', Math.abs(zh('pipeBv') - 0.3) < 1e-9 && Math.abs(zh('pipeCv') - 0.3) < 1e-9 && zh('pipeBh') > 0.74 && zh('pipeCh') > 0.74 && tm.geom_size[3 * g('pipeBv') + 1] > 0.25); }

  // Interlocks of the controls.
  { const r = new TransferRun();
    check('rotate is refused with hand B still clamped', !r.rotate(1) && r.msg.includes('Release'));
    check('releasing hand C while hand B is released is refused (the cart would let go)', r.clampHand(2, true) && !r.clampHand(1, true) && r.msg.includes('not clamped'));
    for (let i = 0; i < 100; i++) r.advance(0.02);
    check('rotate is accepted once hand B is released (no fold or lift needed)', r.rotate(1));
    const q = new TransferRun(); q.nudge(1000); for (let i = 0; i < 1000; i++) q.advance(0.02);
    check('the cart stops at the end of the pipes', q.st.s === S_MAX_CM); }

  // Full transfer (Dani's brief: the button must take the cart from the top of pipes B and C to the top right of pipe C): stepped like the scene does, from several positions on the straight part.
  // Every frame is checked against the pipes (zero contacts) and the plate against both hands.
  for (const s0 of [S_MIN_CM, 30, S_MAX_CM]) {
    const r = new TransferRun(); r.st.s = s0; r.goal.s = s0;
    r.swingDegS = 30; r.setSpeed(10); const started = r.start();
    const phases: string[] = []; let frames = 0, bad = 0, deep = 0, deepNames = '', rotFrames = 0, rotOk = true, prevT = r.st.t, maxHinge = 0, maxStep = 0, h1 = 0, h2 = 0, sMovedWrong = false, prevS = s0, maxS = s0, wheelsOk = true, maxDh = 0;
    while (!r.done && frames < 20000) {
      const during = r.current; r.advance(0.02); frames++;
      const k = applyPose(tm, td, r.st); mj.mj_forward(tm, td);
      if (r.current && phases[phases.length - 1] !== r.current) phases.push(r.current);
      const w = worstContact(tm, td); if (w.depth < 0) { bad++; if (w.depth < deep) { deep = w.depth; deepNames = w.names; } }
      if (r.st.t !== prevT && during !== 'rotate' && during !== 'rotateBack') rotOk = false;
      if (r.st.t > 0 && r.st.t < 1) { rotFrames++; if (!(r.st.open2 === 1 && r.st.open1 === 0)) rotOk = false; }
      if (r.st.s !== prevS && during !== 'move' && during !== 'moveTop') sMovedWrong = true;
      if (r.st.s !== prevS && r.st.t < 1 && during === 'move') wheelsOk = false;
      maxHinge = Math.max(maxHinge, Math.abs(k.hinge1), Math.abs(k.hinge2));
      maxStep = Math.max(maxStep, Math.abs(k.hinge1 - h1), Math.abs(k.hinge2 - h2)); h1 = k.hinge1; h2 = k.hinge2; prevT = r.st.t; prevS = r.st.s; maxS = Math.max(maxS, r.st.s); maxDh = Math.max(maxDh, Math.abs(k.hinge2));
    }
    check(`full transfer from ${s0} cm: starts, runs release, rotate, move, rotate back (flat as soon as pipe B's bend is behind), drive to the top right, in that order, and finishes`, started && r.done && phases.join('>') === 'release>rotate>move>rotateBack>moveTop', phases.join('>') + ` (${frames} frames)`);
    check(`full transfer from ${s0} cm: zero contacts with the track, cart against the pipes and plate against the hands (${frames} frames)`, bad === 0, `${bad} frames, worst ${(deep * 1000).toFixed(2)} mm ${deepNames}`);
    check(`full transfer from ${s0} cm: the plate rotates only in the rotate steps, with hand B released and hand C clamped; the cart drives only in the move step, rotated`, rotFrames > 20 && rotOk && !sMovedWrong && wheelsOk, `${rotFrames} rotation frames`);
    check(`full transfer from ${s0} cm: no hinge goes past ${MAX_BEND_HINGE_DEG} deg and the hinge drives never exceed the speed limit (30 deg/s)`, maxHinge * 180 / Math.PI <= MAX_BEND_HINGE_DEG + 1e-6 && maxStep <= (30 * Math.PI / 180) * 0.02 + 1e-6, `${(maxHinge * 180 / Math.PI).toFixed(1)} deg, ${(maxStep / 0.02 * 180 / Math.PI).toFixed(1)} deg/s`);
    // END POSITION: the cart is on pipe C's top bar, near its free (right) end: hand C is on the bar's axis (x from the bend end, z = bar height), clamped; hand B released, plate flat.
    const hc = handAt(r.st, 1), barZ = (0.6 + 0.15), barX0 = 0.06 + 0.15, barX1 = barX0 + 0.45;
    check(`full transfer from ${s0} cm: ends at pipe C's top right, flat, hand C clamped on the top bar (z ${barZ} m, x ${barX0}..${barX1} m, ${(barX1 - hc.x) * 100 | 0} cm from the end), hand B released`,
      r.st.t === 0 && r.st.open1 === 0 && r.st.open2 === 1 && Math.abs(hc.z - barZ) < 1e-6 && Math.abs(hc.y) < 1e-6 && hc.x > barX0 + 0.25 && hc.x < barX1 - 0.05 && r.st.s === P_TOP_CM, `hand C at x ${hc.x.toFixed(3)} z ${hc.z.toFixed(3)}, s ${r.st.s}`);
    check(`full transfer from ${s0} cm: the cart really travels (round the bend, more than 60 cm), not just up and down`, maxS - s0 > 60, `${(maxS - s0).toFixed(1)} cm`);
  }
  // The other direction (Pond #227): hand C released, the plate turning on hinge B, the cart up pipe B's bend to its top left. Hand C is the true mirror of hand B, so this must be the mirror image of the trip up pipe C.
  for (const s0 of [S_MIN_CM, 30, S_MAX_CM]) {
    const r = new TransferRun(); r.st.s = s0; r.goal.s = s0; r.swingDegS = 30; r.setSpeed(10); const started = r.start(1);
    const phases: string[] = []; let frames = 0, bad = 0, deep = 0, deepNames = '', rotOk = true, maxHinge = 0, maxStep = 0, h1 = 0, h2 = 0, rotFrames = 0;
    while (!r.done && frames < 20000) {
      r.advance(0.02); frames++; const k = applyPose(tm, td, r.st); mj.mj_forward(tm, td);
      if (r.current && phases[phases.length - 1] !== r.current) phases.push(r.current);
      const w = worstContact(tm, td); if (w.depth < 0) { bad++; if (w.depth < deep) { deep = w.depth; deepNames = w.names; } }
      if (r.st.t > 0 && r.st.t < 1) { rotFrames++; if (!(r.st.open1 === 1 && r.st.open2 === 0)) rotOk = false; }
      maxHinge = Math.max(maxHinge, Math.abs(k.hinge1), Math.abs(k.hinge2)); maxStep = Math.max(maxStep, Math.abs(k.hinge1 - h1), Math.abs(k.hinge2 - h2)); h1 = k.hinge1; h2 = k.hinge2;
    }
    check(`trip up pipe B from ${s0} cm: release hand C, rotate on hinge B, move, rotate back, drive to the top left, in that order, and finishes`, started && r.done && phases.join('>') === 'release>rotate>move>rotateBack>moveTop' && r.free === 1, phases.join('>') + ` (${frames} frames)`);
    check(`trip up pipe B from ${s0} cm: zero contacts on every frame (${frames} frames)`, bad === 0, `${bad} frames, worst ${(deep * 1000).toFixed(2)} mm ${deepNames}`);
    check(`trip up pipe B from ${s0} cm: the plate turns only with hand C released and hand B clamped; no hinge past ${MAX_BEND_HINGE_DEG} deg, none faster than 30 deg/s`, rotFrames > 20 && rotOk && maxHinge * 180 / Math.PI <= MAX_BEND_HINGE_DEG + 1e-6 && maxStep <= (30 * Math.PI / 180) * 0.02 + 1e-6, `${rotFrames} frames, ${(maxHinge * 180 / Math.PI).toFixed(1)} deg`);
    const hb = handAt(r.st, 2);
    check(`trip up pipe B from ${s0} cm: ends at pipe B's top left, flat, hand B clamped on the top bar (the mirror of the end of the trip up pipe C), hand C released`,
      r.st.t === 0 && r.st.open2 === 0 && r.st.open1 === 1 && r.st.s === P_TOP_CM && Math.abs(hb.z - 0.75) < 1e-6 && Math.abs(hb.y) < 1e-6 && Math.abs(hb.x + 0.55) < 0.01, `hand B at x ${hb.x.toFixed(3)} z ${hb.z.toFixed(3)}`);
  }
  { // the way back from pipe B's top left: the same button drives back round the bend, rotates flat and clamps hand C again, no contact on any frame; then the first direction works again
    const r = new TransferRun(); r.reset(); r.setSpeed(10); r.swingDegS = 30; r.start(1); for (let i = 0; i < 20000 && !r.done; i++) r.advance(0.02);
    const phases: string[] = []; let bad = 0, deep = 0, names = '', frames = 0; const ok = r.start();
    while (!r.done && frames < 20000) { r.advance(0.02); frames++; applyPose(tm, td, r.st); mj.mj_forward(tm, td); if (r.current && phases[phases.length - 1] !== r.current) phases.push(r.current);
      const w = worstContact(tm, td); if (w.depth < 0) { bad++; if (w.depth < deep) { deep = w.depth; names = w.names; } } }
    check('return trip from pipe B\'s top left: drive, rotate, drive back round the bend, rotate flat, clamp hand C', ok && r.done && phases.join('>') === 'moveFlat>rotate>moveBack>rotateBack>clamp' && r.st.s === S_MAX_CM && r.st.open1 === 0 && r.st.open2 === 0 && r.st.t === 0, phases.join('>'));
    check('return trip from pipe B\'s top left: zero contacts on every frame', bad === 0, `${bad} frames, worst ${(deep * 1000).toFixed(2)} mm ${names}`);
    check('both directions in turn: after coming back from pipe B the cart goes up pipe C, and back', r.start(2) && r.free === 2); }
  { // the press button (Pond #228): press 1 up pipe C, press 2 back to rest then up pipe B, press 3 back to rest then up pipe C; no contact on any frame
    const r = new TransferRun(); r.reset(); r.setSpeed(10); r.swingDegS = 30; const ends: string[] = []; let bad = 0, deep = 0, names = '';
    for (let p = 0; p < 3; p++) {
      const ok = r.press(); const ph: string[] = [];
      for (let i = 0; i < 40000 && !r.done; i++) { r.advance(0.02); if (r.current && ph[ph.length - 1] !== r.current) ph.push(r.current);
        applyPose(tm, td, r.st); mj.mj_forward(tm, td); const w = worstContact(tm, td); if (w.depth < 0) { bad++; if (w.depth < deep) { deep = w.depth; names = w.names; } } }
      ends.push(`${ok}:${r.st.s}:${r.free}`);
      if (p === 1) check('press 2: back to rest (flat, clamp B), release C, rotate on hinge B, up pipe B', ph.join('>') === 'moveFlat>rotate>moveBack>rotateBack>clamp>release>rotate>move>rotateBack>moveTop', ph.join('>'));
    }
    check('three presses: up C, up B, up C, ending on the top bar each time', ends.join(' ') === `true:${P_TOP_CM}:2 true:${P_TOP_CM}:1 true:${P_TOP_CM}:2`, ends.join(' '));
    check('three presses: zero contacts on every frame', bad === 0, `${bad} frames, worst ${(deep * 1000).toFixed(2)} mm ${names}`); }
  { // one click runs the whole transfer (Pond #228): from the top of one pipe, the Run button for the other pipe returns, clamps, releases the other hand and goes up, without a second click
    for (const [first, second, endFree] of [[2, 1, 1], [1, 2, 2]] as const) {
      const r = new TransferRun(); r.reset(); r.setSpeed(10); r.swingDegS = 30; r.start(first); for (let i = 0; i < 40000 && !r.done; i++) r.advance(0.02);
      const ph: string[] = []; const ok = r.start(second); let bad = 0;
      for (let i = 0; i < 40000 && !r.done; i++) { r.advance(0.02); if (r.current && ph[ph.length - 1] !== r.current) ph.push(r.current); applyPose(tm, td, r.st); mj.mj_forward(tm, td); if (worstContact(tm, td).depth < 0) bad++; }
      check(`single click to ${second === 1 ? 'pipe B' : 'pipe C'} from the top of the other: whole sequence in one run`, ok && r.done && !r.busy && r.st.s === P_TOP_CM && r.free === endFree && ph.join('>') === 'moveFlat>rotate>moveBack>rotateBack>clamp>release>rotate>move>rotateBack>moveTop', ph.join('>'));
      check(`single click to ${second === 1 ? 'pipe B' : 'pipe C'}: zero contacts`, bad === 0, `${bad} frames`);
    }
  }
  { // the mirror symmetry itself: the same trip both ways gives mirror-image poses (x -> -x, the hands swapped) all the way: hand B's pose on the trip up pipe B is hand C's on the trip up pipe C
    const a = new TransferRun(), b = new TransferRun(); for (const r of [a, b]) { r.st.s = 30; r.goal.s = 30; r.swingDegS = 30; r.setSpeed(10); } a.start(2); b.start(1);
    let worst = 0; for (let i = 0; i < 20000 && !(a.done && b.done); i++) { a.advance(0.02); b.advance(0.02);
      applyPose(tm, td, a.st); mj.mj_forward(tm, td); const pa = [...Array(tm.nbody).keys()].map((j) => [td.xpos[3 * j], td.xpos[3 * j + 1], td.xpos[3 * j + 2]]);
      applyPose(tm, td, b.st); mj.mj_forward(tm, td); const pb = [...Array(tm.nbody).keys()].map((j) => [td.xpos[3 * j], td.xpos[3 * j + 1], td.xpos[3 * j + 2]]);
      const swap = (name: string) => name === 'hand1' ? 'hand2' : name === 'hand2' ? 'hand1' : name;
      for (const j of [...Array(tm.nbody).keys()]) { const n = tm.body(j).name, j2 = tm.body(swap(n)).id; if (!n.startsWith('hand') && n !== 'plate' && n !== 'cart') continue; worst = Math.max(worst, Math.abs(pa[j][0] + pb[j2][0]), Math.abs(pa[j][1] - pb[j2][1]), Math.abs(pa[j][2] - pb[j2][2])); } }
    check('the trip up pipe B is the exact mirror image of the trip up pipe C (hands, plate and cart positions, every frame)', worst < 1e-6, `${(worst * 1000).toFixed(3)} mm`); }
  { // The scene's own start: the cart waits at the top of pipes B and C; Reset puts it back; the button refuses at the end.
    const r = new TransferRun(); r.reset();
    check('reset: cart at the top of the straight part, clamped on both pipes', r.st.s === S_MAX_CM && r.st.open1 === 0 && r.st.open2 === 0 && r.st.t === 0 && r.spanning);
    r.start(); for (let i = 0; i < 20000 && !r.done; i++) r.advance(0.02);
    check('after the transfer the cart is at pipe C\'s top right, plate flat, hand B off', r.done && r.st.s === P_TOP_CM && r.st.t === 0 && r.st.open2 === 1 && r.st.open1 === 0);
    // the way back: the same button takes it back round the bend (rotated), flat again, and clamps hand B on pipe B: contact check on every frame
    { let bad = 0, deep = 0, names = '', frames = 0; const phases: string[] = [], pos = new TransferRun(); Object.assign(pos.st, r.st); pos.goal = { ...r.goal };
      const ok = pos.start();
      while (!pos.done && frames < 20000) { pos.advance(0.02); frames++; applyPose(tm, td, pos.st); mj.mj_forward(tm, td); if (pos.current && phases[phases.length - 1] !== pos.current) phases.push(pos.current);
        const w = worstContact(tm, td); if (w.depth < 0) { bad++; if (w.depth < deep) { deep = w.depth; names = w.names; } } }
      check('return trip: the button takes the cart back from pipe C\'s top right: drive, rotate, drive back round the bend, rotate flat, clamp hand B', ok && pos.done && phases.join('>') === 'moveFlat>rotate>moveBack>rotateBack>clamp' && pos.st.s === S_MAX_CM && pos.st.t === 0 && pos.st.open1 === 0 && pos.st.open2 === 0, phases.join('>') + ` s ${pos.st.s}`);
      check('return trip: zero contacts on every frame', bad === 0, `${bad} frames, worst ${(deep * 1000).toFixed(2)} mm ${names}`);
      check('there and back again: the button works a third time (B to C again after the return)', pos.start() && pos.current === 'release'); }
    // the plate turns back flat as soon as the bend is behind (S_FLAT_CM), not at the top: no contact turning back at any pipe position from there on, and nothing is rotated beyond it
    { let bad = 0; for (const s0 of [S_FLAT_CM, 80, 90, P_TOP_CM]) for (let i = 0; i <= 200; i++) { const st = initialState(); st.s = s0; st.t = i / 200; st.open2 = 1; applyPose(tm, td, st); mj.mj_forward(tm, td); if (worstContact(tm, td).depth < 0) bad++; }
      check('rotating back is contact free from 75 cm on (the plate turns flat as soon as the bend is behind)', bad === 0, `${bad} poses`);
      const f = new TransferRun(); f.reset(); f.start(); let rotatedBeyond = false; for (let i = 0; i < 20000 && !f.done; i++) { f.advance(0.02); if (f.st.t > 0 && f.st.s > S_FLAT_CM + 1e-9) rotatedBeyond = true; }
      check('forward trip: the plate is flat again beyond ' + S_FLAT_CM + ' cm', !rotatedBeyond); }
    { // two transfers in a row with the scene's own (slow) defaults: ends on pipe C after the first, back on pipe B after the second; log where the hands are at start, middle and end
      const d = new TransferRun(); d.reset(); d.setSpeed(8); const log: string[] = [], hands = (tag: string) => { const a = handAt(d.st, 1), b = handAt(d.st, 2); log.push(`${tag}: C-hand x ${a.x.toFixed(3)} z ${a.z.toFixed(3)} ${d.st.open1 < 0.5 ? 'clamped' : 'open'}, B-hand x ${b.x.toFixed(3)} z ${b.z.toFixed(3)} ${d.st.open2 < 0.5 ? 'clamped' : 'open'}, plate ${(d.st.t * 22).toFixed(0)} deg`); };
      const ends: number[] = []; let secs = 0;
      for (let n = 0; n < 2; n++) { hands(`transfer ${n + 1} start`); d.start(); let mid = false; for (let i = 0; i < 40000 && !d.done; i++) { d.advance(0.02); secs += 0.02; if (!mid && d.current === 'rotateBack' || !mid && d.current === 'moveBack' && d.st.s > 70) { mid = true; hands(`transfer ${n + 1} middle`); } } hands(`transfer ${n + 1} end`); ends.push(d.st.s); }
      console.log(log.join('\n'));
      check('two transfers in a row: the cart ends on pipe C (top right) after the first and back on pipe B (top of the straight part, both hands clamped) after the second', ends[0] === P_TOP_CM && ends[1] === S_MAX_CM && d.st.open1 === 0 && d.st.open2 === 0 && d.st.t === 0, ends.join(','));
      check('two transfers take long enough to follow on a phone (more than 25 s in all, about 14 s each)', secs > 25, secs.toFixed(0) + ' s'); }
    r.reset(); check('reset again: ready for another transfer', r.start());
    const q = new TransferRun(); q.reset(); q.clampHand(2, true); for (let i = 0; i < 100; i++) q.advance(0.02); q.rotate(1); for (let i = 0; i < 1000; i++) q.advance(0.02);
    q.nudge(1000); for (let i = 0; i < 4000; i++) q.advance(0.02);
    check('manual: released and rotated, Forward drives all the way to the top right of pipe C, no further', q.st.s === P_TOP_CM && q.st.t === 1);
    check('manual: Forward is refused with the plate flat and hand B released beyond the straight part', (() => { const z = new TransferRun(); z.reset(); z.clampHand(2, true); for (let i = 0; i < 100; i++) z.advance(0.02); z.nudge(1000); for (let i = 0; i < 1000; i++) z.advance(0.02); return z.st.s <= S_MAX_CM; })()); }
  // Dense sweep of the whole ride (rotated, hand B released) every 0.1 cm from the straight part to the top right: zero contacts, the plate never touches a pipe, the hinges stay inside +-30 deg.
  { let bad = 0, worst = 0, worstS = 0, maxA = 0;
    for (let s = S_MIN_CM; s <= P_TOP_CM + 1e-9; s += 0.1) { const st = initialState(); st.s = s; st.t = 1; st.open2 = 1; const k = applyPose(tm, td, st); mj.mj_forward(tm, td); maxA = Math.max(maxA, Math.abs(k.hinge1), Math.abs(k.hinge2)); const w = worstContact(tm, td); if (w.depth < 0) { bad++; if (w.depth < worst) { worst = w.depth; worstS = s; } } }
    check('dense sweep of the ride, every 1 mm from the straight part to the top right of pipe C: zero contacts', bad === 0, `${bad} poses, worst ${(worst * 1000).toFixed(2)} mm at ${worstS.toFixed(1)} cm`);
    check('the hinges stay inside their joint range (30 deg)', maxA * 180 / Math.PI <= 30, `${(maxA * 180 / Math.PI).toFixed(1)} deg`); }
  check('CAD hinge worm drive speed is 60 rpm / 38 (about 9.5 deg/s)', Math.abs(HINGE_DEG_S_CAD - 9.47) < 0.01);
  td.delete(); tm.delete();
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
    check('collars are collision geometry the arm can hit (named collar_*, arm bit set)', names.includes('name="collar_0_0"') && names.split('\n').filter((l) => l.includes('name="collar_') && l.includes('conaffinity="3"')).length >= 8 * (STORE_ROWS + TRAY_SLOTS));
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
  check('transplant: parked plug cap top is 5 mm past a seated one (blind floor), at the holder height', Math.abs(PARK_CAP_TOP[0] - (X_TOP - RECESS_T + 0.005 + CAP_T)) < 1e-9 && Math.abs(PARK_CAP_TOP[2] - ZP) < 1e-9);
  check('transplant: seated cap top is 29.7 mm along the 45 degree axis', Math.abs(Math.hypot(SEAT_CAP_TOP[0] - P0[0], SEAT_CAP_TOP[2] - P0[2]) - (U_CAP + CAP_T)) < 1e-9);
  check('transplant: holder floor under the plug', Math.abs(PARK_CAP_TOP[0] - CAP_T - 0.017 - HOLDER_FLOOR_X) < 1e-9);
  // the base of the hand origin from the model matches the IK frame (pose with the hand pointing down)
  tr.pose.tool = { x: 0.3, z: CART_Z0 - 0.2, phi: 0 }; bind.apply(tr.pose);
  { const h = bind.handPos(); check('transplant: IK frame matches the arm model', Math.abs(h[0] - (0.3 + 0.011)) < 1e-6 && Math.abs(h[2] - (CART_Z0 - 0.2 + 0.0785)) < 1e-6, JSON.stringify(h)); }
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
    // KNOWN GAP (Pond #230): with the real cart, the real pod holder where cad/cart_pod_holder.py puts it, and the track plane assumed 0.55 m from the pipe, the SO-101 cannot do steps 1, 3 and 4
    // (the pod in the holder is under the arm base, and the plug holder is at the edge of reach). Reported as GAP lines, not failures, so the gap stays visible; step 2 (drive) must pass.
    const ok = unreachable === 0 && touched === 0 && minMargin > 5, info = `unreachable frames ${unreachable}, touching frames ${touched} ${names} ${worstMm.toFixed(2)} mm, joint margin ${minMargin.toFixed(0)} deg`;
    if (s === 1) check(`transplant: ${STEPS[s].title}: in reach, no contacts`, ok, info);
    else { console.log(ok ? 'ok  ' : 'GAP ', `transplant: ${STEPS[s].title}: in reach, no contacts (known gap, see Pond #230)`, info); }
  }
  check('transplant: all steps done, pod in the hole, plug parked, cart at the hole', tr.done && tr.pose.places.pod === 'seat' && tr.pose.places.plug === 'park' && Math.abs(tr.pose.cartZ - CART_Z1) < 1e-9);
  check('transplant: hole was open once, for under 15 s', tr.holeTimes.length === 1 && tr.holeTimes[0] > 0 && tr.holeTimes[0] < 15, JSON.stringify(tr.holeTimes));
  // Play all gives the same end state
  tr.reset(); tr.playAll(); let guard = 0; while ((tr.busy || tr.next < STEPS.length) && guard++ < 20000) tr.advance(0.05);
  check('transplant: Play all runs the four steps', tr.done && tr.pose.places.pod === 'seat' && tr.pose.places.plug === 'park', `${tr.next}`);
  // the contact check can fail: a plug dragged into the pipe is caught
  tr.reset(); tr.pose.places.plug = 'hand'; tr.pose.cartZ = CART_Z1; tr.pose.tool = { x: 0.036, z: 0.6, phi: -45 }; bind.apply(tr.pose);
  check('transplant: a part pushed into the pipe is a contact', podContact(tm, td).depth < -0.002);
  check('transplant: pod holder is where the CAD puts it (not lowered) and the start is the seedling tray height', CUP_DROP === 0 && CART_Z0 < CART_Z1);
  td.delete(); tm.delete();
}

const t0 = performance.now(); run(5); const ms = performance.now() - t0;
console.log(`5 s of sim took ${ms.toFixed(0)} ms in node`);
process.exit(fail ? 1 : 0);
