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

export type Vec3 = [number, number, number];
type Quat = [number, number, number, number];
/** Rotate v by the quaternion q (w x y z). */
export function rotate(q: Quat, v: Vec3): Vec3 {
  const [w, x, y, z] = q;
  const t = [2 * (y * v[2] - z * v[1]), 2 * (z * v[0] - x * v[2]), 2 * (x * v[1] - y * v[0])];
  return [v[0] + w * t[0] + (y * t[2] - z * t[1]), v[1] + w * t[1] + (z * t[0] - x * t[2]), v[2] + w * t[2] + (x * t[1] - y * t[0])];
}

export const SWING_RATE_DEG_S = 30;           // default hinge speed for the preview; the CAD worm drive gives HINGE_DEG_S_CAD (about 9.5)
export const DEFAULT_SPEED_CM_S = 10, MAX_SPEED_CM_S = 50, DEFAULT_STEP_CM = 5;
export const HAND_MOVE_S = 1;                 // seconds each clamp takes to close or open
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
export const CLEAR_DEG = SWING_PATH[SWING_PATH.length - 1][0];
/** The largest hinge angle (deg) either hinge uses. */
export const MAX_HINGE_DEG = Math.max(...SWING_PATH.map(([a, h]) => Math.max(Math.abs(a), Math.abs(h))));
/** Path length in degrees (the larger of the two hinges' travel on each leg: the time at the hinge speed limit in seconds per deg/s). */
const LEG = SWING_PATH.slice(1).map(([a, h], i) => Math.max(Math.abs(a - SWING_PATH[i][0]), Math.abs(h - SWING_PATH[i][1])));
export const SWING_DEG = LEG.reduce((x, y) => x + y, 0);
const swingAt = (u: number): [number, number] => {
  let d = Math.min(1, Math.max(0, u)) * SWING_DEG, i = 0;
  while (i < LEG.length - 1 && d > LEG[i]) { d -= LEG[i]; i++; }
  const f = LEG[i] > 0 ? Math.min(1, d / LEG[i]) : 1, [a0, h0] = SWING_PATH[i], [a1, h1] = SWING_PATH[i + 1];
  return [a0 + (a1 - a0) * f, h0 + (h1 - h0) * f];
};
export function kinematics(t: number): Kin {
  const [ad, hd] = swingAt(t), alpha = (ad * Math.PI) / 180, turn = (hd * Math.PI) / 180;
  const hx = hingeX(1) / 1000, hy = HINGE_Y / 1000, c = Math.cos(alpha), s = Math.sin(alpha);
  // the plate is rotated by alpha about hand 1's hinge point: origin O = h - R h
  const ox = hx - (c * hx - s * hy), oy = hy - (s * hx + c * hy);
  return { alpha, ox, oy, hinge1: -alpha, hinge2: turn };
}

type ModelLike = { jnt(name: string): { id: number }; jnt_qposadr: ArrayLike<number>; actuator(name: string): { id: number }; body(name: string): { id: number }; body_mocapid: ArrayLike<number> };
type DataLike = { qpos: { [i: number]: number }; ctrl: { [i: number]: number }; mocap_pos: { [i: number]: number }; mocap_quat: { [i: number]: number } };

/** The cart: position along the pipes (cm, the hands' mid point), swing t, clamp openings (0 closed .. 1 open), wheel spins (rad). */
export interface CartState { s: number; t: number; open1: number; open2: number; spin1: number; spin2: number }
export const initialState = (): CartState => ({ s: S_START_CM, t: 0, open1: 0, open2: 0, spin1: 0, spin2: 0 });

/** Write a cart state into the model: the plate's mocap pose, both hinges, both clamps and the drive wheels, and the matching actuator targets. */
export function applyPose(model: ModelLike, data: DataLike, st: CartState): Kin {
  const k = kinematics(st.t), mc = model.body_mocapid[model.body('cart').id];
  // plate pose: origin (ox, oy, s), turned by alpha about the pipe direction (the world frame is the CAD frame)
  data.mocap_pos[3 * mc] = k.ox; data.mocap_pos[3 * mc + 1] = k.oy; data.mocap_pos[3 * mc + 2] = st.s / 100;
  const h = k.alpha / 2;
  data.mocap_quat[4 * mc] = Math.cos(h); data.mocap_quat[4 * mc + 1] = 0; data.mocap_quat[4 * mc + 2] = 0; data.mocap_quat[4 * mc + 3] = Math.sin(h);
  const q = (n: string) => model.jnt_qposadr[model.jnt(n).id], a = (n: string) => model.actuator(n).id;
  const clamp = (open: number) => Math.min(1, Math.max(0, open)) * JAW_OPEN_RAD;   // jaw angle: 0 clamped .. JAW_OPEN (92 deg) released
  const c1 = clamp(st.open1), c2 = clamp(st.open2);
  data.qpos[q('hinge1')] = k.hinge1; data.qpos[q('hinge2')] = k.hinge2;
  data.qpos[q('jaw1')] = c1; data.qpos[q('jaw2')] = c2;
  for (const w of ['w1f', 'w1b']) data.qpos[q(w)] = st.spin1;
  for (const w of ['w2f', 'w2b']) data.qpos[q(w)] = st.spin2;
  data.ctrl[a('hinge1')] = k.hinge1; data.ctrl[a('hinge2')] = k.hinge2; data.ctrl[a('jaw1')] = c1; data.ctrl[a('jaw2')] = c2;
  data.ctrl[a('drive1')] = st.spin1; data.ctrl[a('drive2')] = st.spin2;
  return k;
}

export type StepName = 'release' | 'rotate' | 'move' | 'rotateBack' | 'clamp';
export const STEP_LABEL: Record<StepName, string> = {
  release: 'Releasing hand B', rotate: 'Rotating the plate on hand C\'s hinge to clear the curve', move: 'Moving past the curve on hand C',
  rotateBack: 'Rotating the plate back', clamp: 'Clamping hand B',
};
const EPS = 1e-9;
interface Goal { s: number; t: number; open1: number; open2: number }

/**
 * Cart controller. Every continuous quantity (position along the pipes, swing, clamp openings) moves towards its goal at its own rate, behind interlocks:
 * the plate swings only with hand 2 open and hand 1 closed; nothing else moves mid-swing. A full transfer is a queue of five goals (release, rotate, move, rotate back, clamp), run one after the
 * other: only the hinge rotates the plate, by CLEAR_DEG at most. `msg` carries the reason when an interlock refuses something.
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

  /** Swing progress per second: paced so the faster of the two hinges runs at `swingDegS` on every leg of SWING_PATH. */
  get swingRate() { return this.swingDegS / SWING_DEG; }
  get swinging() { return this.st.t > EPS && this.st.t < 1 - EPS; }
  get atEnd(): 0 | 1 | null { return this.st.t <= EPS ? 0 : this.st.t >= 1 - EPS ? 1 : null; }
  get busy() { return this.current !== null; }

  private refuse(why: string) { this.msg = why; return false; }
  setSpeed(v: number) { this.speed = Math.min(MAX_SPEED_CM_S, Math.max(0.1, v)); }

  /** Step buttons: move the cart along the pipes by d cm. */
  nudge(d: number): boolean {
    if (this.busy) return this.refuse('Wait for the running transfer to finish.');
    if (this.swinging) return this.refuse('The plate is mid-rotation: finish the rotation first.');
    this.goal.s = Math.min(S_MAX_CM, Math.max(S_MIN_CM, this.goal.s + d)); this.msg = ''; return true;
  }
  /** hand 1 or 2: open (release) or close (clamp). */
  clampHand(hand: 1 | 2, open: boolean): boolean {
    if (this.busy) return this.refuse('Wait for the running transfer to finish.');
    if (this.swinging) return this.refuse('The plate is mid-rotation: a hand cannot open or close in the air.');
    if (this.st.t > EPS) return this.refuse('Rotate the plate back first: a hand can only open or close on its pipe.');
    if (open && hand === 1 && (this.st.open2 > EPS || this.goal.open2 > EPS)) return this.refuse('Hand B is not clamped: releasing hand C as well would let go of the track.');
    if (open && hand === 2 && (this.st.open1 > EPS || this.goal.open1 > EPS)) return this.refuse('Hand C is not clamped: releasing hand B as well would let go of the track.');
    this.goal[hand === 1 ? 'open1' : 'open2'] = open ? 1 : 0; this.msg = ''; return true;
  }
  /** Rotate: turn the plate on hand C's hinge (toward = 1: to clear the curve, 0: back). */
  rotate(toward: 0 | 1): boolean {
    if (this.busy) return this.refuse('Wait for the running transfer to finish.');
    if (this.st.open1 > EPS) return this.refuse('Hand C must stay clamped: the plate rotates on its hinge.');
    if (this.st.open2 < 1 - EPS) return this.refuse('Release hand B first.');
    this.goal.t = toward; this.msg = ''; return true;
  }
  stop() { this.queue = []; this.current = null; this.goal = { s: this.st.s, t: this.st.t, open1: this.st.open1, open2: this.st.open2 }; this.msg = 'Stopped.'; }

  /** Run the whole transfer from where the cart is: release, rotate to clear the curve, move past it (to the far end of the straight part), rotate back, clamp. Needs the cart at rest, both hands clamped. */
  start(): boolean {
    if (this.busy) return this.refuse('A transfer is already running.');
    if (this.swinging || this.st.t > EPS) return this.refuse('The plate is rotated: rotate it back first.');
    if (this.st.open1 > EPS || this.st.open2 > EPS) return this.refuse('Clamp both hands first.');
    const to = this.st.s < (S_MIN_CM + S_MAX_CM) / 2 ? S_MAX_CM : S_MIN_CM;
    this.queue = [{ name: 'release', goal: { open2: 1 } }, { name: 'rotate', goal: { t: 1 } }, { name: 'move', goal: { s: to } }, { name: 'rotateBack', goal: { t: 0 } }, { name: 'clamp', goal: { open2: 0 } }];
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
      const ds = this.toward(s.s, g.s, this.speed, dt) - s.s;
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
  }
  return { depth, names };
}

