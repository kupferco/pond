// Transfer scene logic (v2 cart, cad/cart_base.py): the plate hangs on a hinge at each hand and ONE rigid plate swings on the hand that stays clamped.
// Pure maths and a state machine, no DOM; applyPose writes a state into a MuJoCo model.
//
// Mechanism (lengths in mm, CAD axes: x across, y out of the pipe plane, z up the pipes; the hinge axes and the pipes are all parallel to z, so the swing is planar).
// At rest the hands clamp pipe B (hand 2) and pipe C (hand 1), 120 mm apart. Hinge 1 is on the far side of C, hinge 2 on the far side of B, 156 mm apart and 43 mm in
// front of the pipe plane. Transfer (decided by Dani): the arm folds in; hand 2 releases B; the cart lifts on pipe C (hand 1's drive wheels) until hand 2 is above
// the end of B; the plate swings half a turn about hinge 1, OUT TO -y, hand 2 following it round (its own hinge turns it back so it arrives the way it left);
// the cart lowers, hand 2 drops over the end of pipe D, which is where its pipe offset lands (252 mm: hinge 1 + 156 + 30); hand 2 clamps D.
// Going back is the same in reverse. A hand swung the other way (hand 1 about hinge 2) is not supported: see the notes in the pull request.
import { HINGE_Y, hingeX, HINGE_DEG_S_CAD } from './dims.ts';
import { CLEAR_M } from './model.ts';
import { TOP_S_M, LIFT_M } from './transfer-model.ts';

export type Vec3 = [number, number, number];
type Quat = [number, number, number, number];
/** Rotate v by the quaternion q (w x y z). */
export function rotate(q: Quat, v: Vec3): Vec3 {
  const [w, x, y, z] = q;
  const t = [2 * (y * v[2] - z * v[1]), 2 * (z * v[0] - x * v[2]), 2 * (x * v[1] - y * v[0])];
  return [v[0] + w * t[0] + (y * t[2] - z * t[1]), v[1] + w * t[1] + (z * t[0] - x * t[2]), v[2] + w * t[2] + (x * t[1] - y * t[0])];
}

/** How far the clamp pair backs off (m) when a hand is open: the hand then drops over a pipe end with the fixed pairs 4 mm clear all round. */
export const WHEEL_OPEN_V2_M = 0.03;
export const TOP_S_CM = TOP_S_M * 100, LIFT_CM = LIFT_M * 100;
export const SWING_RATE_DEG_S = 30;           // default hinge speed for the preview; the CAD worm drive gives HINGE_DEG_S_CAD (about 9.5)
export const DEFAULT_SPEED_CM_S = 10, MAX_SPEED_CM_S = 50, DEFAULT_STEP_CM = 5, MIN_S_CM = 15;
export const ARM_FOLD_S = 3;                  // seconds the arm takes to fold or unfold
export const HAND_MOVE_S = 1;                 // seconds each clamp takes to close or open
const WHEEL_R_MM = 10;                        // CAD wheel radius, to turn travel into wheel spin
export { HINGE_DEG_S_CAD };

/** Swing coordinate t: 0 = at rest (hands on B and C), 1 = hand 2 swung about hinge 1 onto D. */
export interface Kin { alpha: number; ox: number; oy: number; hinge1: number; hinge2: number; freeYaw: number }
const smooth = (u: number) => u * u * (3 - 2 * u);

/** Swing coordinate t: 0 = at rest (hands on B and C), 1 = hand 2 swung about hinge 1 onto D. */
export interface Kin { alpha: number; ox: number; oy: number; hinge1: number; hinge2: number; freeYaw: number }
export const HAND_NODES = [0, 0.04, 0.08, 0.12, 0.16, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.84, 0.88, 0.92, 0.96, 1];
export const HAND_TURNS = [0, 0.004, 0.01, 0.02, 0.03, 0.05, 0.08, 0.2, 0.4, 0.6, 0.78, 0.9, 0.93, 0.96, 0.98, 0.995, 1];
export function handTurn(u: number, knots = HAND_TURNS): number {
  const n = HAND_NODES, k = Math.min(1, Math.max(0, u));
  let i = 0; while (i < n.length - 2 && k > n[i + 1]) i++;
  const h = (j: number) => n[j + 1] - n[j], d = (j: number) => (knots[j + 1] - knots[j]) / h(j);
  const slope = (j: number) => { if (j === 0 || j === n.length - 1) return 0; const a = d(j - 1), b = d(j); return a * b <= 0 ? 0 : (2 * a * b) / (a + b); };
  const x = (k - n[i]) / h(i), x2 = x * x, x3 = x2 * x;
  return (2 * x3 - 3 * x2 + 1) * knots[i] + (x3 - 2 * x2 + x) * h(i) * slope(i) + (-2 * x3 + 3 * x2) * knots[i + 1] + (x3 - x2) * h(i) * slope(i + 1);
}
export function kinematics(t: number): Kin {
  const u = Math.min(1, Math.max(0, t)), alpha = Math.PI * u;
  const hx = hingeX(1) / 1000, hy = HINGE_Y / 1000, c = Math.cos(alpha), s = Math.sin(alpha);
  // the plate is rotated by alpha about hand 1's hinge point: origin O = h - R h
  const ox = hx - (c * hx - s * hy), oy = hy - (s * hx + c * hy);
  // hand 2's own hinge turns it half a turn the other way round the plate as the plate turns half a turn: its yaw in the world goes from 0 to a full turn, so it arrives as it left
  const turn = Math.PI * smooth(u);
  return { alpha, ox, oy, hinge1: -alpha, hinge2: turn, freeYaw: alpha + turn };
}

type ModelLike = { jnt(name: string): { id: number }; jnt_qposadr: ArrayLike<number>; actuator(name: string): { id: number }; body(name: string): { id: number }; body_mocapid: ArrayLike<number> };
type DataLike = { qpos: { [i: number]: number }; ctrl: { [i: number]: number }; mocap_pos: { [i: number]: number }; mocap_quat: { [i: number]: number } };

/** The cart: height (cm, the hands' mid height), swing t, clamp openings (0 closed .. 1 open), arm fold (0 out .. 1 stowed), wheel spins (rad). */
export interface CartState { s: number; t: number; open1: number; open2: number; fold: number; spin1: number; spin2: number }
export const initialState = (): CartState => ({ s: TOP_S_CM, t: 0, open1: 0, open2: 0, fold: 0, spin1: 0, spin2: 0 });

/** Write a cart state into the model: the plate's mocap pose, both hinges, both clamps, the arm and the drive wheels, and the matching actuator targets. */
export function applyPose(model: ModelLike, data: DataLike, st: CartState): Kin {
  const k = kinematics(st.t), mc = model.body_mocapid[model.body('cart').id];
  data.mocap_pos[3 * mc] = k.ox; data.mocap_pos[3 * mc + 1] = k.oy; data.mocap_pos[3 * mc + 2] = st.s / 100;
  data.mocap_quat[4 * mc] = Math.cos(k.alpha / 2); data.mocap_quat[4 * mc + 1] = 0; data.mocap_quat[4 * mc + 2] = 0; data.mocap_quat[4 * mc + 3] = Math.sin(k.alpha / 2);
  const q = (n: string) => model.jnt_qposadr[model.jnt(n).id], a = (n: string) => model.actuator(n).id;
  const clamp = (open: number) => { const o = Math.min(1, Math.max(0, open)); return (1 - o) * CLEAR_M + o * WHEEL_OPEN_V2_M; };
  const c1 = clamp(st.open1), c2 = clamp(st.open2);
  data.qpos[q('hinge1')] = k.hinge1; data.qpos[q('hinge2')] = k.hinge2;
  data.qpos[q('h1p')] = c1; data.qpos[q('h2p')] = c2;
  data.qpos[q('arm_lift')] = 0; data.qpos[q('arm_elbow')] = Math.PI * st.fold; data.qpos[q('arm_wrist')] = -Math.PI * st.fold;
  for (const w of ['w1f', 'w1b']) data.qpos[q(w)] = st.spin1;
  for (const w of ['w2f', 'w2b']) data.qpos[q(w)] = st.spin2;
  data.ctrl[a('hinge1')] = k.hinge1; data.ctrl[a('hinge2')] = k.hinge2; data.ctrl[a('clamp1')] = c1; data.ctrl[a('clamp2')] = c2;
  data.ctrl[a('drive1')] = st.spin1; data.ctrl[a('drive2')] = st.spin2;
  return k;
}

/** Where the cart is, as a name for the display: the pipe each hand is on (or over). */
export const pipeOf = (hand: 1 | 2, t: number) => (hand === 1 ? 'C' : t >= 0.5 ? 'D' : 'B');

export type StepName = 'fold' | 'release' | 'lift' | 'swing' | 'lower' | 'clamp' | 'unfold';
export const STEP_LABEL: Record<StepName, string> = {
  fold: 'Folding the arm in close to the hinge', release: 'Releasing the free hand', lift: 'Lifting the cart on pipe C so the free hand clears its pipe',
  swing: 'Swinging the plate on hand C\'s hinge', lower: 'Lowering the free hand onto the new pipe', clamp: 'Clamping the free hand', unfold: 'Unfolding the arm',
};
const EPS = 1e-9;
interface Goal { s: number; t: number; open1: number; open2: number; fold: number }

/**
 * Cart controller. Every continuous quantity (height, swing, clamp openings, arm fold) moves towards its goal at its own rate, behind interlocks:
 * the plate swings only with the arm folded, hand 2 open, hand 1 closed and the cart lifted; nothing else moves mid-swing; hand 2 closes only over a pipe end.
 * A full transfer is a queue of goals, run one after the other. `msg` carries the reason when an interlock refuses something.
 */
export class TransferRun {
  readonly st = initialState();
  goal: Goal = { s: TOP_S_CM, t: 0, open1: 0, open2: 0, fold: 0 };
  speed = DEFAULT_SPEED_CM_S;                 // cm/s
  swingDegS = SWING_RATE_DEG_S;               // top speed (deg/s) of either hinge's output, the worm drive's limit
  queue: { name: StepName; goal: Partial<Goal> }[] = [];
  current: StepName | null = null;
  msg = '';
  done = false;
  /** Hinge angles (rad) of both hinges last frame, to check the worm drives never exceed their speed. */
  private prev = { h1: 0, h2: 0 };
  maxHingeStep = 0;

  /** Swing progress per second: hinge 2 turns up to 1.5 times as fast as the plate (it also turns the hand back round), so the swing is paced by that hinge and neither exceeds `swingDegS`. */
  get swingRate() { return (this.swingDegS * Math.PI) / 180 / (1.5 * Math.PI); }
  get swinging() { return this.st.t > EPS && this.st.t < 1 - EPS; }
  get atEnd(): 0 | 1 | null { return this.st.t <= EPS ? 0 : this.st.t >= 1 - EPS ? 1 : null; }
  get busy() { return this.current !== null; }
  /** Highest height the cart may be at: with hand 2 clamped on its pipe it must stay over the pipe end; with hand 2 open it may lift over it. */
  get maxS() { return this.st.open2 >= 1 - EPS || this.goal.open2 >= 1 ? TOP_S_CM + LIFT_CM : TOP_S_CM; }

  private refuse(why: string) { this.msg = why; return false; }
  setSpeed(v: number) { this.speed = Math.min(MAX_SPEED_CM_S, Math.max(0.1, v)); }

  /** Step buttons: move the cart up or down the pipes by d cm. */
  nudge(d: number): boolean {
    if (this.busy) return this.refuse('Wait for the running transfer to finish.');
    if (this.swinging) return this.refuse('The plate is mid-swing: finish the rotation first.');
    const top = this.st.open2 >= 1 - EPS ? TOP_S_CM + LIFT_CM : TOP_S_CM;
    if (d > 0 && this.st.open2 < 1 - EPS && this.st.s >= TOP_S_CM - EPS) return this.refuse('Hand ' + pipeOf(2, this.st.t) + ' is clamped and the pipe ends here: release it to lift the cart higher.');
    this.goal.s = Math.min(top, Math.max(MIN_S_CM, this.goal.s + d)); this.msg = ''; return true;
  }
  fold(on: boolean): boolean {
    if (this.busy) return this.refuse('Wait for the running transfer to finish.');
    if (this.swinging) return this.refuse('The plate is mid-swing.');
    this.goal.fold = on ? 1 : 0; this.msg = ''; return true;
  }
  /** hand 1 or 2: open (release) or close (clamp). */
  clampHand(hand: 1 | 2, open: boolean): boolean {
    if (this.busy) return this.refuse('Wait for the running transfer to finish.');
    if (this.swinging) return this.refuse('The plate is mid-swing: a hand cannot open or close in the air.');
    if (open && hand === 1 && (this.st.open2 > EPS || this.goal.open2 > EPS)) return this.refuse('Hand 2 is not clamped: releasing hand C as well would let go of the track.');
    if (open && hand === 2 && (this.st.open1 > EPS || this.goal.open1 > EPS)) return this.refuse('Hand C is not clamped: releasing hand ' + pipeOf(2, this.st.t) + ' as well would let go of the track.');
    if (!open && hand === 2 && this.st.s > TOP_S_CM + EPS) return this.refuse('Hand ' + pipeOf(2, this.st.t) + ' is above its pipe end: lower the cart first.');
    this.goal[hand === 1 ? 'open1' : 'open2'] = open ? 1 : 0; this.msg = ''; return true;
  }
  /** Rotate: swing the plate to the other end (toward = 1: hand 2 over onto D, 0: back to B). */
  rotate(toward: 0 | 1): boolean {
    if (this.busy) return this.refuse('Wait for the running transfer to finish.');
    if (this.st.fold < 1 - EPS) return this.refuse('Fold the arm in first: the plate swings with the arm on it.');
    if (this.st.open1 > EPS) return this.refuse('Hand C must stay clamped: the plate swings on its hinge.');
    if (this.st.open2 < 1 - EPS) return this.refuse('Release the free hand (hand ' + pipeOf(2, this.st.t) + ') first.');
    if (this.st.s < TOP_S_CM + LIFT_CM - EPS) return this.refuse('Lift the cart so the free hand clears its pipe end first.');
    this.goal.t = toward; this.msg = ''; return true;
  }
  stop() { this.queue = []; this.current = null; this.goal = { s: this.st.s, t: this.st.t, open1: this.st.open1, open2: this.st.open2, fold: this.st.fold }; this.msg = 'Stopped.'; }

  /** Run the whole transfer from where the cart is: to the other pipe, whichever end it is at. Needs the cart at rest at one end. */
  start(): boolean {
    if (this.busy) return this.refuse('A transfer is already running.');
    const end = this.atEnd;
    if (end === null) return this.refuse('The plate is mid-swing: finish the rotation first.');
    if (this.st.open1 > EPS || this.st.open2 > EPS) return this.refuse('Clamp both hands first.');
    const to: 0 | 1 = end === 0 ? 1 : 0, top = TOP_S_CM + LIFT_CM;
    this.queue = [
      { name: 'fold', goal: { fold: 1 } }, { name: 'release', goal: { s: TOP_S_CM, open2: 1 } }, { name: 'lift', goal: { s: top } },
      { name: 'swing', goal: { t: to } }, { name: 'lower', goal: { s: TOP_S_CM } }, { name: 'clamp', goal: { open2: 0 } }, { name: 'unfold', goal: { fold: 0 } },
    ];
    if (this.st.s < TOP_S_CM - EPS) this.queue.splice(1, 0, { name: 'lift', goal: { s: TOP_S_CM } });   // from lower down: ride up to the pipe end first
    this.done = false; this.msg = ''; this.next(); return true;
  }
  private next() {
    const n = this.queue.shift();
    if (!n) { this.current = null; this.done = true; return; }
    this.current = n.name; Object.assign(this.goal, n.goal);
  }
  private reached() { const g = this.goal, s = this.st; return Math.abs(g.s - s.s) < EPS && Math.abs(g.t - s.t) < EPS && Math.abs(g.open1 - s.open1) < EPS && Math.abs(g.open2 - s.open2) < EPS && Math.abs(g.fold - s.fold) < EPS; }

  private toward(cur: number, goal: number, rate: number, dt: number) { const e = goal - cur, step = rate * dt; return Math.abs(e) <= step ? goal : cur + Math.sign(e) * step; }
  advance(dt: number) {
    const s = this.st, g = this.goal;
    // arm and clamps
    s.fold = this.toward(s.fold, g.fold, 1 / ARM_FOLD_S, dt);
    s.open1 = this.toward(s.open1, g.open1, 1 / HAND_MOVE_S, dt);
    s.open2 = this.toward(s.open2, g.open2, 1 / HAND_MOVE_S, dt);
    // the swing: hinge speed limited, and only with everything in place
    const swingOk = s.fold >= 1 - EPS && s.open1 <= EPS && s.open2 >= 1 - EPS && s.s >= TOP_S_CM + LIFT_CM - EPS;
    if (g.t !== s.t) { if (swingOk) s.t = this.toward(s.t, g.t, this.swingRate, dt); else if (!this.busy) { g.t = s.t; } }
    // driving up or down the pipes: not mid-swing, and the hand over its pipe end must not be clamped while above it
    if (!this.swinging && g.s !== s.s) {
      const ds = this.toward(s.s, Math.min(g.s, this.maxS), this.speed, dt) - s.s;
      s.s += ds;
      if (s.open1 < 0.5) s.spin1 -= (ds * 10) / WHEEL_R_MM;   // hand 1's drive wheels roll it up the tall pipe
      if (s.open2 < 0.5) s.spin2 -= (ds * 10) / WHEEL_R_MM;
    }
    if (this.current && this.reached()) this.next();
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

