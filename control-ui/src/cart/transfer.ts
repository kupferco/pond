// Transfer scene logic (v2 cart, cad/cart_base.py): the plate hangs on a hinge at each hand and ONE rigid plate swings on the hand that stays clamped.
// Pure maths and a state machine, no DOM; applyPose writes a state into a MuJoCo model.
//
// Mechanism (lengths in mm, CAD axes: x across, y out of the pipe plane, z along the pipes; the hinge axes and the pipes are all parallel, so the rotation is planar; the scene
// is used as it is: pipes upright, B on the left bending left, C bending right). At rest the hands clamp pipe B (hand 2) and pipe C (hand 1), 120 mm apart. Hinge 1 is on the far side of C,
// hinge 2 on the far side of B, 156 mm apart and 43 mm in front of the pipe plane. Transfer (decided by Dani): ONLY THE HINGE MOVES, and only a little. Hand 2 releases B; the plate rotates
// a few degrees about hinge 1 (just enough for hand 2 to leave the pipe and clear its curved part, CLEAR_DEG); the cart moves along pipe C past the curve; the plate rotates back;
// hand 2 clamps again. The arm stays stowed on the plate throughout. A hand swung the other way (hand 1 about hinge 2) is not supported.
import { HINGE_Y, hingeX, HINGE_DEG_S_CAD } from './dims.ts';
import { JAW_OPEN_RAD, S_MAX_CM, S_MIN_CM, S_START_CM } from './transfer-model.ts';
import { L_ARC, L_VERT, pathAt } from './track.ts';

export type Vec3 = [number, number, number];
type Quat = [number, number, number, number];
/** Rotate v by the quaternion q (w x y z). */
export function rotate(q: Quat, v: Vec3): Vec3 {
  const [w, x, y, z] = q;
  const t = [2 * (y * v[2] - z * v[1]), 2 * (z * v[0] - x * v[2]), 2 * (x * v[1] - y * v[0])];
  return [v[0] + w * t[0] + (y * t[2] - z * t[1]), v[1] + w * t[1] + (z * t[0] - x * t[2]), v[2] + w * t[2] + (x * t[1] - y * t[0])];
}

export const SWING_RATE_DEG_S = 15;           // default hinge speed for the preview; the CAD worm drive gives HINGE_DEG_S_CAD (about 9.5)
export const DEFAULT_SPEED_CM_S = 8, MAX_SPEED_CM_S = 50, DEFAULT_STEP_CM = 5;
export const HAND_MOVE_S = 2;                 // seconds each clamp takes to close or open
export { S_MAX_CM, S_MIN_CM, S_START_CM };
const WHEEL_R_MM = 10;                        // CAD wheel radius, to turn travel into wheel spin
export { HINGE_DEG_S_CAD };

/** Rotation coordinate t: 0 = at rest (hands on B and C), 1 = plate rotated CLEAR_DEG about hinge 1, hand 2 clear of pipe B. */
export interface Kin { alpha: number; ox: number; oy: number; hinge1: number; hinge2: number }

/**
 * Rotation path as (plate angle alpha, hand 2's own hinge angle) in degrees. Found by searching the (alpha, hinge 2) plane of the model with contact detection (jaw open, 92 deg):
 * the sleeve is only 8 mm bigger than the pipe, so hand 2 has to turn a few degrees on its own hinge while the plate rotates; the corridor is narrow, so the path follows its middle.
 * The last point is the smallest plate angle at which hand 2's sleeve is completely off pipe B (22 deg, checked at 1 deg steps): CLEAR_DEG.
 */
export const SWING_PATH: readonly (readonly [number, number])[] = [[0, 0], [2, 2], [4, 4], [6, 6], [8, 8], [12, 8], [16, 8], [22, 8]];
/**
 * NOT a usable path: the mirror case (hand 2 static on pipe B, hand 1 released, plate turning on hinge B). Both hands are copies, not mirrors (cad/check_transfer_hands.py), so hand C's
 * C gap faces +x, away from the plate, and a swing about hinge B (x -90) pushes pipe C into hand C's -x wall. Searched with contact detection (test/sim.test.ts): the plate can turn
 * at most 4 deg before hand C's sleeve hits pipe C, whatever hand C's own hinge does (+-30 deg), and 14 deg is the least that would free it. TransferRun refuses this case.
 */
export const SWING_PATH_B: (readonly [number, number])[] = [[0, 0], [22, 8]];
export const CLEAR_DEG = SWING_PATH[SWING_PATH.length - 1][0];
/** The largest hinge angle (deg) either hinge uses. */
export const MAX_HINGE_DEG = Math.max(...SWING_PATH.map(([a, h]) => Math.max(Math.abs(a), Math.abs(h))));
const pathOf = (hand: StaticHand) => (hand === 1 ? SWING_PATH : SWING_PATH_B);
/** Path length in degrees (the larger of the two hinges' travel on each leg: the time at the hinge speed limit in seconds per deg/s). */
const legs = (path: readonly (readonly [number, number])[]) => path.slice(1).map(([a, h], i) => Math.max(Math.abs(a - path[i][0]), Math.abs(h - path[i][1])));
export const swingDeg = (hand: StaticHand = 1) => legs(pathOf(hand)).reduce((x, y) => x + y, 0);
export const SWING_DEG = swingDeg(1);
const swingAt = (u: number, hand: StaticHand = 1): [number, number] => {
  const path = pathOf(hand), LEG = legs(path);
  let d = Math.min(1, Math.max(0, u)) * swingDeg(hand), i = 0;
  while (i < LEG.length - 1 && d > LEG[i]) { d -= LEG[i]; i++; }
  const f = LEG[i] > 0 ? Math.min(1, d / LEG[i]) : 1, [a0, h0] = path[i], [a1, h1] = path[i + 1];
  return [a0 + (a1 - a0) * f, h0 + (h1 - h0) * f];
};
/** The hand that stays clamped while the other one is released and the plate rotates: hand 1 on pipe C or hand 2 on pipe B. */
export type StaticHand = 1 | 2;
export function kinematics(t: number, hand: StaticHand = 1, extra = 0, extraTurn = 0): Kin {
  const [ad, hd] = swingAt(t, hand);
  return kinFromAngles(hand, (ad * Math.PI) / 180 + (t >= 1 - 1e-9 ? extra : 0), (hd * Math.PI) / 180 + (t >= 1 - 1e-9 ? extraTurn : 0));
}
/** Plate swing `alpha` and the free hand's own hinge angle `turn` (rad, both positive towards the free hand leaving its pipe) about the static hand's hinge. */
export function kinFromAngles(hand: StaticHand, alpha: number, turn: number): Kin {
  const hx = hingeX(hand) / 1000, hy = HINGE_Y / 1000;
  // the plate is rotated by phi about the static hand's hinge point: origin O = h - R h. About hinge 1 it turns by +alpha, about hinge 2 by -alpha (the mirror image, so the free hand always swings out to the plate side).
  const phi = hand === 1 ? alpha : -alpha, c = Math.cos(phi), s = Math.sin(phi);
  const ox = hx - (c * hx - s * hy), oy = hy - (s * hx + c * hy);
  return hand === 1 ? { alpha: phi, ox, oy, hinge1: -phi, hinge2: turn } : { alpha: phi, ox, oy, hinge1: turn, hinge2: -phi };
}

type ModelLike = { jnt(name: string): { id: number }; jnt_qposadr: ArrayLike<number>; actuator(name: string): { id: number }; body(name: string): { id: number }; body_mocapid: ArrayLike<number> };
type DataLike = { qpos: { [i: number]: number }; ctrl: { [i: number]: number }; mocap_pos: { [i: number]: number }; mocap_quat: { [i: number]: number } };

/** The cart: position along the pipes (cm, the hands' mid point), swing t, clamp openings (0 closed .. 1 open), wheel spins (rad). */
export interface CartState { s: number; t: number; open1: number; open2: number; spin1: number; spin2: number }
export const initialState = (): CartState => ({ s: S_START_CM, t: 0, open1: 0, open2: 0, spin1: 0, spin2: 0 });

/** Which hand is the static one for a state: the clamped one while the other is (being) released; both clamped counts as hand 1 (the poses coincide on the straight part). */
export const staticHand = (st: { open1: number; open2: number }): StaticHand => (st.open1 > st.open2 ? 2 : 1);

/** Path length (cm) from the pipe's foot to the end of the straight part, to the end of the bend, and the hand's farthest position on the top bar (clear of the bar's free end). */
export const P_STRAIGHT_END = L_VERT, P_BEND_END = L_VERT + L_ARC;
export const P_TOP_CM = P_BEND_END + 34;
/** Where the plate can turn back flat while hand B is off: beyond the bend's trim rows (all hinge extras are 0 from here) and clear of pipe B's bend; checked in test/sim.test.ts. */
export const S_FLAT_CM = 75;
/** The sleeve is a rigid 90 mm tube on a 150 mm radius bend: its axis is laid along the chord, shifted this far (mm) towards the inside of the bend (half the sagitta of the sleeve length; the wheels' 4 mm clearance covers the rest). */
export const BEND_CHORD_MM = 3.4;
/** Lateral shift (mm, towards the inside of the bend) and extra yaw (rad) that lay the rigid sleeve on the bend without touching it, by path position (cm). Searched with the contact check. */
export interface BendTrim { dx: number; dy: number; yaw: number; eps: number; da: number; dh: number }
const DEG = Math.PI / 180;
/** Rows [s cm, dx mm, dy mm, yaw deg, eps deg, da deg, dh deg]; contact-free with the plate rotated and hand B released, checked every 0.25 cm (test/sim.test.ts). The released hand B needs the extra turn at the start of the bend, where pipe B starts to curve away behind its open jaw. */
const BEND_ROWS: readonly (readonly number[])[] = [
  [0, 0, 0, 0, 0, 0, 0], [50, 0, 0, 0, 0, 0, 0], [57, 0, 0, 0, 0, 3, 8], [58, 0, 0, 0, 1, 5, 12], [59, 0.5, -0.5, 1, 2, 7, 16], [60, 1, -1, 2, 4, 7, 16], [60.5, 1.5, -1, 2, 4, 7, 16], [62, 2, -1, 1, 4, 7, 16], [64, 2.5, -2, 0, 6, 7, 16], [67, 2.5, -2, 0, 6, 7, 16],
  [75, 2.5, -2, 0, 6, 0, 0], [80, 2.5, -2, 0, 6, 0, 0], [82, 1.5, -1, -2, 4, 0, 0], [83, 1.5, -0.5, -2, 2, 0, 0], [83.3, 1.5, -0.5, -2, 2, 0, 0], [83.5, 1.5, -0.5, -3, 2, 0, 0], [84, 1, 0, -2, 0, 0, 0], [85, 0, 0, -1, 0, 0, 0], [86, 0, 0, 0, 0, 0, 0], [1000, 0, 0, 0, 0, 0, 0],
];
/** The largest hinge angle (deg) of either hinge anywhere in a full transfer, including the extra turn round the start of the bend. */
export const MAX_BEND_HINGE_DEG = Math.max(...BEND_ROWS.map((r) => Math.max(CLEAR_DEG + r[5], SWING_PATH[SWING_PATH.length - 1][1] + r[6])));
export const BEND_TRIM: readonly (readonly number[])[] = BEND_ROWS.map(([s, dx, dy, yaw, eps, da, dh]) => [s, dx, dy, yaw * DEG, eps * DEG, da * DEG, dh * DEG]);
export function bendTrim(s: number): BendTrim {
  const T = BEND_TRIM, at = (r: readonly number[]): BendTrim => ({ dx: r[1], dy: r[2], yaw: r[3], eps: r[4], da: r[5], dh: r[6] });
  if (s <= T[0][0]) return at(T[0]);
  for (let i = 1; i < T.length; i++) if (s <= T[i][0]) { const f = (s - T[i - 1][0]) / (T[i][0] - T[i - 1][0]); return at(T[i - 1].map((v, j) => v + f * (T[i][j] - v))); }
  return at(T[T.length - 1]);
}

/** Pose of the static hand's pipe point: world position (m) and the turn about world y that lays the hand's along-pipe axis on the track tangent (B bends left, C bends right). */
export function pathPose(hand: StaticHand, s: number): { x: number; z: number; theta: number; bend: number } {
  const p = pathAt(Math.min(P_TOP_CM, s)), sign = hand === 1 ? 1 : -1, theta = sign * Math.atan2(p.tx, p.tz);
  return { x: (hand === 1 ? HX_C : HX_B) + sign * p.x, z: p.z, theta, bend: p.section === 'curve' ? 1 : 0 };
}
const HX_C = 0.06, HX_B = -0.06;

/** Plate pose in the world for a state: the static hand rides its pipe's path, the plate is rotated by the swing about that hand's hinge. Returns position, quaternion (w x y z) and the Kin. */
export function platePose(st: CartState, trim?: BendTrim, kinOverride?: Kin): { pos: Vec3; quat: Quat; kin: Kin; hand: StaticHand; eps: number } {
  const hand = staticHand(st), tr = trim ?? bendTrim(st.s), k = kinOverride ?? kinematics(st.t, hand, tr.da, tr.dh), pp = pathPose(hand, st.s);
  pp.theta += (hand === 1 ? 1 : -1) * tr.yaw;
  const cy = Math.cos(pp.theta / 2), sy = Math.sin(pp.theta / 2), cz = Math.cos(k.alpha / 2), sz = Math.sin(k.alpha / 2);
  // plate = Ry(theta) * Rz(alpha); the plate origin in the hand's own frame (hand axis at x = 0 on the pipe, z = 0 at the hand's mid point) is (ox - pipe x, oy, 0)
  const pipeX = hand === 1 ? HX_C : HX_B, local: Vec3 = [k.ox - pipeX, k.oy, 0];
  local[0] += (tr.dx / 1000) * (hand === 1 ? 1 : -1); local[1] += tr.dy / 1000;   // towards the inside of the bend, in the hand frame's x
  const q: Quat = [cy * cz, sy * sz, sy * cz, cy * sz];   // Ry(theta) * Rz(alpha)
  const r = rotate([cy, 0, sy, 0], local);
  return { pos: [pp.x + r[0], r[1], pp.z + r[2]], quat: q, kin: k, hand, eps: tr.eps };
}

/** Write a cart state into the model: the plate's mocap pose, both hinges, both clamps and the drive wheels, and the matching actuator targets. */
export function applyPose(model: ModelLike, data: DataLike, st: CartState, trim?: BendTrim, kinOverride?: Kin): Kin {
  const { pos, quat, kin: k, hand, eps } = platePose(st, trim, kinOverride), mc = model.body_mocapid[model.body('cart').id];
  for (let i = 0; i < 3; i++) data.mocap_pos[3 * mc + i] = pos[i];
  for (let i = 0; i < 4; i++) data.mocap_quat[4 * mc + i] = quat[i];
  const q = (n: string) => model.jnt_qposadr[model.jnt(n).id], a = (n: string) => model.actuator(n).id;
  const clamp = (open: number) => Math.min(1, Math.max(0, open)) * JAW_OPEN_RAD;   // jaw angle: 0 clamped .. JAW_OPEN (92 deg) released
  const c1 = clamp(st.open1) + (hand === 1 ? eps : 0), c2 = clamp(st.open2) + (hand === 2 ? eps : 0);   // eps: the static hand's jaw cracks open a little on a bend
  data.qpos[q('hinge1')] = k.hinge1; data.qpos[q('hinge2')] = k.hinge2;
  data.qpos[q('jaw1')] = c1; data.qpos[q('jaw2')] = c2;
  for (const w of ['w1f', 'w1b']) data.qpos[q(w)] = st.spin1;
  for (const w of ['w2f', 'w2b']) data.qpos[q(w)] = st.spin2;
  data.ctrl[a('hinge1')] = k.hinge1; data.ctrl[a('hinge2')] = k.hinge2; data.ctrl[a('jaw1')] = c1; data.ctrl[a('jaw2')] = c2;
  data.ctrl[a('drive1')] = st.spin1; data.ctrl[a('drive2')] = st.spin2;
  return k;
}

export type StepName = 'release' | 'rotate' | 'move' | 'rotateBack' | 'moveTop' | 'moveBack' | 'moveFlat' | 'clamp';
export const STEP_LABEL: Record<StepName, string> = {
  release: 'Releasing hand B', rotate: 'Rotating the plate on hand C\'s hinge, clear of pipe B', move: 'Driving on pipe C round the bend, plate rotated', rotateBack: 'Rotating the plate back, flat again',
  moveTop: 'Driving flat along pipe C\'s top bar to its top right', moveBack: 'Driving back round the bend, plate rotated, to the top of pipes B and C', moveFlat: 'Driving back along pipe C\'s top bar',
  clamp: 'Clamping hand B on pipe B',
};
const EPS = 1e-9;
interface Goal { s: number; t: number; open1: number; open2: number }

/**
 * Cart controller. Every continuous quantity (position along the track, swing, clamp openings) moves towards its goal at its own rate, behind interlocks:
 * the plate swings only with hand 2 open and hand 1 closed; nothing else moves mid-swing. A full transfer starts with both hands clamped on pipes B and C (anywhere on the straight part)
 * and is a queue of four goals run one after the other: release hand B, rotate the plate on hand C's hinge (CLEAR_DEG), drive on pipe C round its bend to the top right (P_TOP_CM),
 * rotate back. The cart ends on pipe C, hand C clamped, hand B released and free. `msg` carries the reason when an interlock refuses something.
 */
export class TransferRun {
  readonly st = initialState();
  goal: Goal = { s: S_START_CM, t: 0, open1: 0, open2: 0 };
  speed = DEFAULT_SPEED_CM_S;                 // cm/s
  swingDegS = SWING_RATE_DEG_S;               // top speed (deg/s) of either hinge's output, the worm drive's limit
  queue: { name: StepName; goal: Partial<Goal> }[] = [];
  current: StepName | null = null;
  msg = '';
  done = false;
  /** Hinge angles (rad) of both hinges last frame, to check the worm drives never exceed their speed. */
  private prev = { h1: 0, h2: 0 };
  maxHingeStep = 0;

  /** Back to the start: both hands clamped on pipes B and C at the top of the straight part (the cart waits there for a transfer). */
  reset(s = S_MAX_CM) {
    Object.assign(this.st, initialState(), { s });
    this.goal = { s, t: 0, open1: 0, open2: 0 }; this.queue = []; this.current = null; this.done = false; this.msg = '';
  }
  /** Swing progress per second: paced so the faster of the two hinges runs at `swingDegS` on every leg of SWING_PATH. */
  get swingRate() { return this.swingDegS / swingDeg(staticHand(this.st)); }
  get swinging() { return this.st.t > EPS && this.st.t < 1 - EPS; }
  get atEnd(): 0 | 1 | null { return this.st.t <= EPS ? 0 : this.st.t >= 1 - EPS ? 1 : null; }
  get busy() { return this.current !== null; }
  /** Both hands clamped: the cart rides both pipes, only on the straight part. */
  get spanning() { return this.st.open1 <= EPS && this.st.open2 <= EPS; }

  private refuse(why: string) { this.msg = why; return false; }
  setSpeed(v: number) { this.speed = Math.min(MAX_SPEED_CM_S, Math.max(0.1, v)); }

  /** Step buttons: move the cart along the track by d cm. On both pipes: the straight part only; with hand B released and the plate rotated: all the way round pipe C's bend. */
  nudge(d: number): boolean {
    if (this.busy) return this.refuse('Wait for the running transfer to finish.');
    if (this.swinging) return this.refuse('The plate is mid-rotation: finish the rotation first.');
    const s = this.st, rotatedClear = s.open2 >= 1 - EPS && s.t >= 1 - EPS;
    if (!this.spanning && !rotatedClear && s.open2 > EPS && s.open2 < 1 - EPS) return this.refuse('Hand B is moving: wait for it.');
    const flatFree = s.open2 >= 1 - EPS && s.t <= EPS && s.s >= S_FLAT_CM - EPS;   // on the top bar, plate flat, hand B off
    if (s.s > S_MAX_CM + EPS && !rotatedClear && !flatFree) return this.refuse('Rotate the plate first (hand B released): the cart only drives round the bend with the plate rotated.');
    const lo = flatFree ? S_FLAT_CM : S_MIN_CM, hi = rotatedClear || flatFree ? P_TOP_CM : S_MAX_CM;
    this.goal.s = Math.min(hi, Math.max(lo, this.goal.s + d)); this.msg = ''; return true;
  }
  /** hand 1 or 2: open (release) or close (clamp). A hand only opens or closes on its pipe, on the straight part. */
  clampHand(hand: 1 | 2, open: boolean): boolean {
    if (this.busy) return this.refuse('Wait for the running transfer to finish.');
    if (this.swinging) return this.refuse('The plate is mid-rotation: a hand cannot open or close in the air.');
    if (this.st.t > EPS) return this.refuse('Rotate the plate back first: a hand can only open or close on its pipe.');
    if (this.st.s > S_MAX_CM + EPS) return this.refuse('Hand B has no pipe to clamp here: pipe B is behind, on the straight part (press Reset).');
    if (open && hand === 1 && (this.st.open2 > EPS || this.goal.open2 > EPS)) return this.refuse('Hand B is not clamped: releasing hand C as well would let go of the track.');
    if (open && hand === 2 && (this.st.open1 > EPS || this.goal.open1 > EPS)) return this.refuse('Hand C is not clamped: releasing hand B as well would let go of the track.');
    this.goal[hand === 1 ? 'open1' : 'open2'] = open ? 1 : 0; this.msg = ''; return true;
  }
  /** Rotate: turn the plate on hand C's hinge (toward = 1: clear of pipe B, 0: back). */
  rotate(toward: 0 | 1): boolean {
    if (this.busy) return this.refuse('Wait for the running transfer to finish.');
    if (this.st.open1 > EPS) return this.refuse('Hand C must stay clamped: the plate rotates on its hinge. (The other way round does not work: hand C\'s gap faces away from the plate, so its sleeve hits pipe C after 4 degrees.)');
    if (this.st.open2 < 1 - EPS) return this.refuse('Release hand B first.');
    if (!toward && this.st.s > S_MAX_CM + EPS && this.st.s < S_FLAT_CM - EPS) return this.refuse(`Drive on to ${S_FLAT_CM} cm first: the plate can only turn back flat beyond pipe B's bend.`);
    this.goal.t = toward; this.msg = ''; return true;
  }
  stop() { this.queue = []; this.current = null; this.goal = { s: this.st.s, t: this.st.t, open1: this.st.open1, open2: this.st.open2 }; this.msg = 'Stopped.'; }

  /**
   * Run the whole transfer from where the cart is. Both hands clamped on the straight part: B to C: release hand B, rotate the plate on hand C's hinge, drive on pipe C round the bend to
   * S_FLAT_CM, rotate back flat as soon as pipe B's bend is behind, drive on to the top right. The cart on pipe C's top bar with hand B off: the same back: drive to S_FLAT_CM, rotate, drive
   * back round the bend, rotate flat, clamp hand B on pipe B again.
   */
  start(): boolean {
    if (this.busy) return this.refuse('A transfer is already running.');
    if (this.swinging || this.st.t > EPS) return this.refuse('The plate is rotated: rotate it back first.');
    const s = this.st;
    if (s.open1 <= EPS && s.open2 >= 1 - EPS && s.s > S_MAX_CM + EPS && this.goal.open2 >= 1 - EPS) {
      this.queue = [{ name: 'moveFlat', goal: { s: S_FLAT_CM } }, { name: 'rotate', goal: { t: 1 } }, { name: 'moveBack', goal: { s: S_MAX_CM } }, { name: 'rotateBack', goal: { t: 0 } }, { name: 'clamp', goal: { open2: 0 } }];
    } else {
      if (s.open1 > EPS || s.open2 > EPS || this.goal.open1 > EPS || this.goal.open2 > EPS) return this.refuse('Clamp both hands first (on the straight part), or press Reset.');
      if (s.s > S_MAX_CM + EPS) return this.refuse('Press Reset: hand B has no pipe to clamp here.');
      this.queue = [{ name: 'release', goal: { open2: 1 } }, { name: 'rotate', goal: { t: 1 } }, { name: 'move', goal: { s: S_FLAT_CM } }, { name: 'rotateBack', goal: { t: 0 } }, { name: 'moveTop', goal: { s: P_TOP_CM } }];
    }
    this.done = false; this.msg = ''; this.next(); return true;
  }
  private next() {
    const n = this.queue.shift();
    if (!n) { this.current = null; this.done = true; return; }
    this.current = n.name; Object.assign(this.goal, n.goal);
  }
  private reached() { const g = this.goal, s = this.st; return Math.abs(g.s - s.s) < EPS && Math.abs(g.t - s.t) < EPS && Math.abs(g.open1 - s.open1) < EPS && Math.abs(g.open2 - s.open2) < EPS; }

  private toward(cur: number, goal: number, rate: number, dt: number) { const e = goal - cur, step = rate * dt; return Math.abs(e) <= Math.max(step, EPS) ? goal : cur + Math.sign(e) * step; }
  advance(dt: number) {
    const s = this.st, g = this.goal;
    // clamps
    s.open1 = this.toward(s.open1, g.open1, 1 / HAND_MOVE_S, dt);
    s.open2 = this.toward(s.open2, g.open2, 1 / HAND_MOVE_S, dt);
    // the swing: hinge speed limited, and only with hand 2 open and hand 1 clamped
    const swingOk = s.open1 <= EPS && s.open2 >= 1 - EPS;
    if (g.t !== s.t) { if (swingOk) s.t = this.toward(s.t, g.t, this.swingRate, dt); else if (!this.busy) { g.t = s.t; } }
    // driving along the pipes: not mid-rotation, and with hand 2 either clamped on B (plate flat) or fully off it (plate rotated clear); the clamped hands' drive wheels roll the cart
    if (!this.swinging && g.s !== s.s && (s.t >= 1 - EPS ? s.open2 >= 1 - EPS : s.open2 <= EPS || s.open2 >= 1 - EPS)) {
      let ds = this.toward(s.s, g.s, this.speed, dt) - s.s;
      // the extra hinge turn round the start of the bend (bendTrim) is part of the worm drives' work: slow the drive so neither hinge exceeds its speed limit
      if (s.t >= 1 - EPS) {
        const a = bendTrim(s.s), b = bendTrim(s.s + ds), dHinge = Math.max(Math.abs(b.da - a.da), Math.abs(b.dh - a.dh)) / DEG, lim = this.swingDegS * dt;
        if (dHinge > lim) ds *= lim / dHinge;
      }
      s.s += ds;
      if (s.open1 < 0.5) s.spin1 -= (ds * 10) / WHEEL_R_MM;
      if (s.open2 < 0.5) s.spin2 -= (ds * 10) / WHEEL_R_MM;
    }
    if (this.current && this.reached()) { s.s = g.s; this.next(); }
  }
  /** Hinge speed bookkeeping for the tests: call with the hinge angles written this frame. */
  track(h1: number, h2: number) { this.maxHingeStep = Math.max(this.maxHingeStep, Math.abs(h1 - this.prev.h1), Math.abs(h2 - this.prev.h2)); this.prev = { h1, h2 }; }
}

/** Deepest penetration (m, negative) among the current contacts and the first pair's geom names, or 0 when nothing touches. */
export function worstContact(model: { geom(id: number): { name: string }; body(id: number): { name: string }; geom_bodyid: ArrayLike<number> }, data: { ncon: number; contact: { get(i: number): { dist: number; geom1: number; geom2: number } | undefined } }): { depth: number; names: string } {
  let depth = 0, names = '';
  for (let i = 0; i < data.ncon; i++) {
    const c = data.contact.get(i);
    if (c && c.dist < depth) { depth = c.dist; names = [c.geom1, c.geom2].map((g: number) => model.geom(g).name || model.body(model.geom_bodyid[g]).name).join(' / '); }
    (c as { delete?: () => void } | undefined)?.delete?.();   // embind wrapper: free it (thousands of contact frames would fill the wasm heap)
  }
  return { depth, names };
}
