// Exports the Transplant seedling DRAWINGS (OpenPocket #459): for the start and after each of the four steps, a GLB of the whole scene (for the 3D viewer), plus triangle lists (JSON) of those poses and of frames through
// every step, which scripts/render_tris.py turns into PNGs and clips (there is no GPU here, so the pictures are drawn by a small software renderer).
// Usage: node --experimental-strip-types scripts/export-transplant.ts OUT_DIR
//
// The sim (src/transplant) is NOT changed. Its arm choreography is kept (the same cart, arm, pod holder and joint solutions); what differs is where the cart stands round the track leg, and the static unit:
//  - world frame of the drawings: z up, pipe and spine on the z axis, x = the FRONT of the unit (the side where the tank's long face is seen with the spine in the middle and the track loop round it), y to the right in the front view;
//  - the cart (with its arm, pod holder and the pod it carries) is turned about the vertical axis of the track leg it rides: the sim has the arm facing the back (-x), the drawings turn it 180 degrees so that the arm FACES THE FRONT
//    (+x) for the pick, and a further 90 degrees (arm facing the central spine, -y, from the right-hand leg) for the insertion. The sleeves stay on the leg: turning about the leg's axis is turning the cart round the pipe it rides;
//  - the seedling tray is the 4 x 4 tray of the Pod grab scene (podgrab/layout.ts: 16 sockets, rows A to D from the front, 0.24 m to the left of the pipe), so it is at the FRONT LEFT of the lid, as in the sim;
//  - the pod is seated in the collar on the FRONT of the spine; only this one insertion is drawn (no plug holder, no plug).
// Every pose is solved by the sim's own inverse kinematics in the sim frame (the drawing targets are mapped back by the inverse of the cart's turn), so the arm is always a pose the SO-101 model can really take.
import loadMujoco from '@mujoco/mujoco';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import {
  BODIES, CAP_T, CUP_CAP_TOP_REL, D_CUP, DRAWING_PICK, JAW_CAP_DEG, JAW_OPEN_DEG, LEG, PIPE_RP, POD_BODY_L, S, TRAY_TOP, U_CAP, XT, YC, ZH, drawingSocket, transplantMjcf, type V3,
} from '../src/transplant/layout.ts';
import { Binder } from '../src/transplant/apply.ts';
import { handDir, ikTool, stowTool, toolFromJoints, toolOf, type Joints } from '../src/transplant/task.ts';
import { quatZ } from '../src/transplant/layout.ts';
import { MOTORS } from '../src/model.ts';
import { glb as glb0, triangles as triangles0, type Tri } from './tri-export.ts';
const glb = (t: Tri[]) => glb0(t, 'pond control-ui export-transplant');
const RAD = Math.PI / 180;

const out = process.argv[2];
if (!out) throw new Error('usage: export-transplant.ts OUT_DIR');
mkdirSync(out, { recursive: true });

// --- the drawing layout (ASSUMED where the sim and the CAD leave it free)
/** Where the collar faces, round the pipe from +x (the front) towards +y (the cart's side): on the FRONT of the spine, a little to the cart's side so that the cart's arm, pointing at the spine, lies in the plane of the pod's axis. */
const PSI_DEG = Number(process.env.PSI_DEG ?? 0);
const PSI = PSI_DEG * RAD;
const THETA_PICK = 180 * RAD;     // the arm faces the front (+x)
const THETA_INSERT = Number(process.env.THETA_DEG ?? 120) * RAD;   // the arm faces the spine (-y, from the right-hand leg)

const mj = await loadMujoco();
// two copies of the scene: the cart rides the leg with one of its two hands (the other hangs open). Turned 180 degrees about its own centre for the pick, the other hand is the one on the leg.
const mkScene = (free: 'B' | 'C') => { const model = mj.MjModel.from_xml_string(transplantMjcf({ psi: PSI, free })); const data = new mj.MjData(model); return { model, data, bind: new Binder(mj, model, data) }; };
const scenes = { B: mkScene('B'), C: mkScene('C') };

// --- the cart's turn: about the vertical axis of the leg it rides (sim frame: the leg at y = -LEG), then moved to the right-hand leg (dy = 2 LEG) or not
interface Turn { theta: number; dy: number; dx?: number }
const L: [number, number] = [XT, -LEG];
const rot = (v: [number, number], a: number): [number, number] => [v[0] * Math.cos(a) - v[1] * Math.sin(a), v[0] * Math.sin(a) + v[1] * Math.cos(a)];
const toDrawing = (p: V3, t: Turn): V3 => { const r = rot([p[0] - L[0], p[1] - L[1]], t.theta); return [L[0] + r[0] + (t.dx ?? 0), L[1] + r[1] + t.dy, p[2]]; };
const toSim = (p: V3, t: Turn): V3 => { const r = rot([p[0] - L[0] - (t.dx ?? 0), p[1] - L[1] - t.dy], -t.theta); return [L[0] + r[0], L[1] + r[1], p[2]]; };
const dirToSim = (d: V3, t: Turn): V3 => { const r = rot([d[0], d[1]], -t.theta); return [r[0], r[1], d[2]]; };

// --- the static places, in the drawing frame
const cap = (x: number, y: number, z: number): V3 => [x, y, z];
const POD_CAP_Z = TRAY_TOP + 0.0003 + POD_BODY_L + CAP_T;      // cap top of a pod standing in a socket
const [sx, sy] = drawingSocket(DRAWING_PICK[0], DRAWING_PICK[1]);
const TRAY_CAP: V3 = cap(sx, sy, POD_CAP_Z);                    // the picked pod, row A column 1
const DOWN: V3 = [0, 0, -1];
const DSEAT: V3 = [S * Math.cos(PSI), S * Math.sin(PSI), S];   // out of the hole, up
const P0: V3 = [(PIPE_RP - 0.0015) * Math.cos(PSI), (PIPE_RP - 0.0015) * Math.sin(PSI), ZH];
const SEAT_CAP: V3 = [P0[0] + DSEAT[0] * (U_CAP + CAP_T), P0[1] + DSEAT[1] * (U_CAP + CAP_T), P0[2] + DSEAT[2] * (U_CAP + CAP_T)];
const along = (p: V3, d: V3, u: number): V3 => [p[0] + d[0] * u, p[1] + d[1] * u, p[2] + d[2] * u];
const neg = (a: V3): V3 => [-a[0], -a[1], -a[2]];

// --- a pose
type Place = 'tray' | 'hand' | 'cup' | 'seat';
interface Pose { turn: Turn; cartZ: number; j: Joints; jaw: number; pod: Place }
const PICK_TURN: Turn = { theta: THETA_PICK, dy: 0.12, dx: Number(process.env.DX ?? -0.02) };   // 180 degrees about the cart's own centre (= about the leg, then 0.12 back): the cart stays at the leg, its arm faces the front
const INS_TURN: Turn = { theta: THETA_INSERT, dy: 2 * LEG };
let problems = 0;
/** The hand pose that puts the cap-top point p (drawing frame) on a part axis `axisIn` (into the part), for a cart in `turn` at cartZ: the sim's IK in the sim frame. */
function grip(p: V3, axisIn: V3, turn: Turn, cartZ: number, what: string): Joints {
  const ps = toSim(p, turn), as = dirToSim(axisIn, turn), t = toolOf(ps, as, cartZ), j = ikTool(t, cartZ);
  if (!j || t.err > 3.5) { problems++; console.log(`  !! ${what}: ${j ? '' : 'out of reach, '}axis error ${t.err.toFixed(1)} deg (point ${ps.map((v) => v.toFixed(3))}, cart z ${cartZ.toFixed(3)})`); }
  return j ?? ikTool(stowTool(cartZ), cartZ)!;
}
const stowJ = (cartZ: number) => ikTool(stowTool(cartZ), cartZ)!;
/** The folded pose of the pick stops: the hand straight down over the seedling tray (it would hang in front of the tank in the sim's own stow pose, which is made for a cart behind the track). */
const stowTray = () => grip(along(TRAY_CAP, [0, 0, 1], 0.09), DOWN, PICK_TURN, Z0, 'folded over the tray');

// the cart's height at the hole: the height at which the seat axis lies in a plane through the arm's base axis (the SO-101 points its hand only along such planes): scan for the smallest axis error
function holeHeight(): number {
  let best = 0.9, bestErr = 1e9;
  for (let z = 0.66; z < 1.3; z += 0.002) {
    const ps = toSim(SEAT_CAP, INS_TURN), t = toolOf(ps, dirToSim(neg(DSEAT), INS_TURN), z), j = ikTool(t, z);
    const ta = toolOf(toSim(along(SEAT_CAP, DSEAT, 0.06), INS_TURN), dirToSim(neg(DSEAT), INS_TURN), z), ja = ikTool(ta, z);
    if (j && ja && Math.max(t.err, ta.err) < bestErr) { bestErr = Math.max(t.err, ta.err); best = z; }
  }
  console.log(`hole stop: cart at ${best.toFixed(3)} m (axis error ${bestErr.toFixed(2)} deg)`);
  return best;
}
if (process.env.PROBE2) {
  for (const z of [0.58, 0.6, 0.62, 0.64, 0.66]) for (const dx of [-0.01, -0.02, -0.03, -0.04, -0.05]) {
    const th: Turn = { theta: Math.PI, dy: 0.12, dx };
    const rs = [DRAWING_PICK[0]].flatMap(() => [0.07, 0].map((u) => { const t = toolOf(toSim(along(TRAY_CAP, [0, 0, 1], u), th), DOWN, z); return ikTool(t, z) ? t.err.toFixed(1) : 'x'; }));
    console.log(`z ${z} dx ${dx}: ${rs.join(' ')}`);
  }
  process.exit(0);
}
if (process.env.PROBE) {
  // probe: which cart turns and collar azimuths put the pod's axis in the arm's reach
  for (const thd of [60, 75, 90, 105, 120, 135, 150]) for (const psd of [-20, 0, 20, 40, 60, 80]) {
    const th: Turn = { theta: thd * RAD, dy: 2 * LEG }, ps = psd * RAD;
    const D: V3 = [S * Math.cos(ps), S * Math.sin(ps), S];
    const P: V3 = [(PIPE_RP - 0.0015) * Math.cos(ps), (PIPE_RP - 0.0015) * Math.sin(ps), ZH];
    const C: V3 = along(P, D, U_CAP + CAP_T);
    let best = 1e9, bz = 0;
    for (let z = 0.66; z < 1.3; z += 0.004) { const e = Math.max(...[0, 0.06].map((u) => { const t = toolOf(toSim(along(C, D, u), th), dirToSim(neg(D), th), z); return ikTool(t, z) ? t.err : 1e6; })); if (e < best) { best = e; bz = z; } }
    console.log(`theta ${thd} psi ${psd}: err ${best.toFixed(1)} at z ${bz.toFixed(2)}`);
  }
  process.exit(0);
}
const Z0 = Number(process.env.Z0 ?? 0.6), Z1 = holeHeight();
const STOW_TRAY = stowTray();

const poses = {
  start: { turn: PICK_TURN, cartZ: Z0, j: STOW_TRAY, jaw: 0, pod: 'tray' } as Pose,
  trayApproach: { turn: PICK_TURN, cartZ: Z0, j: grip(along(TRAY_CAP, [0, 0, 1], 0.07), DOWN, PICK_TURN, Z0, 'above the tray'), jaw: JAW_OPEN_DEG, pod: 'tray' } as Pose,
  trayGrip: { turn: PICK_TURN, cartZ: Z0, j: grip(TRAY_CAP, DOWN, PICK_TURN, Z0, 'at the tray'), jaw: JAW_CAP_DEG, pod: 'hand' } as Pose,
  trayLift: { turn: PICK_TURN, cartZ: Z0, j: grip(along(TRAY_CAP, [0, 0, 1], 0.07), DOWN, PICK_TURN, Z0, 'lifting from the tray'), jaw: JAW_CAP_DEG, pod: 'hand' } as Pose,
  cupApproach: undefined as unknown as Pose, cupAt: undefined as unknown as Pose,
  picked: { turn: PICK_TURN, cartZ: Z0, j: STOW_TRAY, jaw: 0, pod: 'cup' } as Pose,
  drive: { turn: INS_TURN, cartZ: Z1, j: stowJ(Z1), jaw: 0, pod: 'cup' } as Pose,
  open: { turn: INS_TURN, cartZ: Z1, j: grip(along(SEAT_CAP, DSEAT, 0.06), neg(DSEAT), INS_TURN, Z1, 'at the open hole'), jaw: JAW_OPEN_DEG, pod: 'cup' } as Pose,
  seatApproach: { turn: INS_TURN, cartZ: Z1, j: grip(along(SEAT_CAP, DSEAT, 0.06), neg(DSEAT), INS_TURN, Z1, 'above the seat'), jaw: JAW_CAP_DEG, pod: 'hand' } as Pose,
  seated: { turn: INS_TURN, cartZ: Z1, j: grip(SEAT_CAP, neg(DSEAT), INS_TURN, Z1, 'at the seat'), jaw: JAW_OPEN_DEG, pod: 'seat' } as Pose,
  done: { turn: INS_TURN, cartZ: Z1, j: grip(along(SEAT_CAP, DSEAT, 0.06), neg(DSEAT), INS_TURN, Z1, 'leaving the seat'), jaw: JAW_OPEN_DEG, pod: 'seat' } as Pose,
};
// the cup is where the sim has it, relative to the cart: the hand goes to it in the sim frame (the same joint solutions as the sim's)
{
  const cupCap: V3 = [XT + CUP_CAP_TOP_REL[0], YC + CUP_CAP_TOP_REL[1], Z0 + CUP_CAP_TOP_REL[2]], into: V3 = [-D_CUP[0], -D_CUP[1], -D_CUP[2]];
  const at = (u: number) => ikTool(toolOf(along(cupCap, D_CUP, u), into, Z0), Z0);
  poses.cupApproach = { turn: PICK_TURN, cartZ: Z0, j: at(0.07) ?? poses.start.j, jaw: JAW_CAP_DEG, pod: 'hand' };
  poses.cupAt = { turn: PICK_TURN, cartZ: Z0, j: at(0) ?? poses.start.j, jaw: JAW_CAP_DEG, pod: 'hand' };
  if (!at(0.07) || !at(0)) { problems++; console.log('  !! the pod holder is out of reach'); }
}

// --- writing a pose into the model and reading the triangles
const inCart = (model: typeof scenes.B.model, cartBody: number, b: number): boolean => { for (let k = b; k > 0; k = model.body_parentid[k]) if (k === cartBody) return true; return false; };
const tcol = (t: Tri[], turn: Turn): Tri[] => t.map((r) => {
  const a = toDrawing([r[0], r[1], r[2]], turn), b = toDrawing([r[3], r[4], r[5]], turn), c = toDrawing([r[6], r[7], r[8]], turn);
  return [...a, ...b, ...c, ...r.slice(9)];
});
function render(p: Pose): Tri[] {
  const { model, data, bind } = p.turn.theta > 150 * RAD ? scenes.C : scenes.B;   // turned for the pick: hand C is the open one, hand B rides the leg
  const setFree = (name: string, pos: V3, quat: number[]) => { const q = bind.free[name]; for (let k = 0; k < 3; k++) data.qpos[q + k] = pos[k]; for (let k = 0; k < 4; k++) data.qpos[q + 3 + k] = quat[k]; };
  const cartBody = model.body('cart').id, podBody = model.body(BODIES.pod).id;
  const j = p.j as unknown as Record<string, number>;
  for (const m of MOTORS) if (m.id !== 'F') data.qpos[bind.qpos[m.id]] = (j[m.id] ?? 0) * RAD;
  data.qpos[bind.qpos.F] = p.jaw * RAD;
  const mi = bind.mocap.cart;
  const sim = [XT, YC, p.cartZ];
  for (let k = 0; k < 3; k++) data.mocap_pos[3 * mi + k] = sim[k];
  for (let k = 0; k < 4; k++) data.mocap_quat[4 * mi + k] = [1, 0, 0, 0][k];
  // the pod: in a socket and in the seat it stands in the drawing frame; in the hand and in the holder it is carried (sim frame, turned with the cart)
  const tool = toolFromJoints(p.j, p.cartZ);
  const carried = p.pod === 'hand' || p.pod === 'cup';
  if (p.pod === 'tray') setFree(BODIES.pod, TRAY_CAP, quatZ(DOWN));
  else if (p.pod === 'seat') setFree(BODIES.pod, SEAT_CAP, quatZ(neg(DSEAT)));
  else if (p.pod === 'cup') setFree(BODIES.pod, [XT + CUP_CAP_TOP_REL[0], YC + CUP_CAP_TOP_REL[1], p.cartZ + CUP_CAP_TOP_REL[2]], quatZ([-D_CUP[0], -D_CUP[1], -D_CUP[2]]));
  else setFree(BODIES.pod, [tool.x, tool.y, tool.z], quatZ(handDir(tool, p.cartZ)));
  setFree(BODIES.plug, [0, 0, -50], [1, 0, 0, 0]);
  BODIES.other.forEach((n) => setFree(n, [0, 0, -50], [1, 0, 0, 0]));
  mj.mj_forward(model, data);
  const group = (g: number) => inCart(model, cartBody, model.geom_bodyid[g]) || (carried && model.geom_bodyid[g] === podBody);
  return [...triangles0(mj, model, data, group), ...tcol(triangles0(mj, model, data, (g) => !group(g)), p.turn)];
}
const round = (t: Tri[]) => t.map((r) => r.map((v, i) => (i < 9 ? +v.toFixed(4) : v)));
const lerpPose = (a: Pose, b: Pose, w: number, pod: Place): Pose => ({
  turn: { theta: a.turn.theta + (b.turn.theta - a.turn.theta) * w, dy: a.turn.dy + (b.turn.dy - a.turn.dy) * w, dx: (a.turn.dx ?? 0) + ((b.turn.dx ?? 0) - (a.turn.dx ?? 0)) * w },
  cartZ: a.cartZ + (b.cartZ - a.cartZ) * w,
  j: Object.fromEntries((['A', 'B', 'C', 'D', 'E'] as const).map((k) => [k, a.j[k] + (b.j[k] - a.j[k]) * w])) as unknown as Joints,
  jaw: a.jaw + (b.jaw - a.jaw) * w, pod,
});
/** Frames through a list of key poses (joint space, linear), 3 per leg. */
function clip(keys: Pose[]): Tri[][] {
  const frames: Tri[][] = [];
  for (let i = 0; i + 1 < keys.length; i++) for (let k = 0; k < 3; k++) {
    const w = k / 3;
    frames.push(round(render(lerpPose(keys[i], keys[i + 1], w, keys[w < 0.5 ? i : i + 1].pod))));
  }
  frames.push(round(render(keys[keys.length - 1])));
  return frames;
}

const stages: { id: string; label: string }[] = [];
const stage = (id: string, label: string, p: Pose, frames: Tri[][]) => {
  const t = render(p);
  stages.push({ id, label });
  writeFileSync(join(out, `${id}.glb`), glb(t));
  writeFileSync(join(out, `${id}.json`), JSON.stringify(round(t)));
  if (frames.length) writeFileSync(join(out, `${id}-frames.json`), JSON.stringify(frames));
  console.log(id, label, `${frames.length} frames`);
};
const driveKeys: Pose[] = [poses.picked, { ...poses.picked, cartZ: (Z0 + Z1) / 2, j: stowJ((Z0 + Z1) / 2) }, { ...poses.picked, cartZ: Z1, j: stowJ(Z1) }, poses.drive];
// the drive clip: up the left-hand leg (arm still facing the front), then the cart is turned to the spine and on the right-hand leg
const driveFrames: Tri[][] = [];
for (let k = 0; k <= 5; k++) { const z = Z0 + (Z1 - Z0) * k / 5; driveFrames.push(round(render({ ...poses.picked, cartZ: z, j: STOW_TRAY }))); }
driveFrames.push(round(render(poses.drive)));
void driveKeys;

stage('step0', 'Start', poses.start, []);
stage('step1', '1. Pick a seedling', poses.picked, clip([poses.start, poses.trayApproach, poses.trayGrip, poses.trayLift, poses.cupApproach, poses.cupAt, { ...poses.cupAt, jaw: JAW_OPEN_DEG, pod: 'cup' }, poses.picked]));
stage('step2', '2. Drive to the hole', poses.drive, driveFrames);
stage('step3', '3. Open the hole', poses.open, clip([poses.drive, poses.open]));
stage('step4', '4. Seat the seedling', poses.done, clip([poses.open, { ...poses.open, pod: 'cup' }, poses.seatApproach, poses.seated, poses.done]));
writeFileSync(join(out, 'stages.json'), JSON.stringify({ stages }));
if (problems) console.log(`${problems} pose problem(s)`);
