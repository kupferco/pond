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

const t0 = performance.now(); run(5); const ms = performance.now() - t0;
console.log(`5 s of sim took ${ms.toFixed(0)} ms in node`);
process.exit(fail ? 1 : 0);
