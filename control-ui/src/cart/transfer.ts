// Transfer scene maths: two neighbouring units' pipes B and C, and the cart handing over between them. No MuJoCo or DOM.
// B is the right-hand pipe of unit 1 (its top bar runs LEFT); C is the left-hand pipe of unit 2 (its top bar runs RIGHT).
// The hands are 14 cm apart, so B and C are 14 cm apart. The cart rides on one pipe and its free hand hangs towards the other.
import { CartMotion, L_ARC, clampS, distToPath, frameQuat, pathAt, L_VERT, type PathPoint } from './track.ts';
import { handTrims, type Vec3 } from './model.ts';

export const HAND_SPACING_MM = 140;
export const PIPE_GAP_M = HAND_SPACING_MM / 1000;
export const TRANSFER_HORIZ_MM = 450;    // shortened top bars: enough to show them
export const TRANSFER_MIN_CM = 15;       // lowest point of the vertical section where a transfer is allowed
export const TRANSFER_DEFAULT_CM = 40;   // transfers happen below the bend; the verticals carry no brackets

export type Pipe = 'B' | 'C';
export const other = (p: Pipe): Pipe => (p === 'B' ? 'C' : 'B');

/** B at x = 0 bends left, C at x = 14 cm bends right. */
export const pipeX = (p: Pipe) => (p === 'B' ? 0 : PIPE_GAP_M);
const dir = (p: Pipe) => (p === 'B' ? -1 : 1);

/** Pipe centre line at path distance s (cm), in world X/Z. */
export function pipePoint(p: Pipe, s: number): PathPoint {
  const q = pathAt(s);
  return { ...q, x: pipeX(p) + dir(p) * q.x, tx: dir(p) * q.tx };
}

export const canTransfer = (s: number) => s >= TRANSFER_MIN_CM && s <= L_VERT;

type Quat = [number, number, number, number];
const mul = (a: Quat, b: Quat): Quat => [
  a[0] * b[0] - a[1] * b[1] - a[2] * b[2] - a[3] * b[3],
  a[0] * b[1] + a[1] * b[0] + a[2] * b[3] - a[3] * b[2],
  a[0] * b[2] - a[1] * b[3] + a[2] * b[0] + a[3] * b[1],
  a[0] * b[3] + a[1] * b[2] - a[2] * b[1] + a[3] * b[0],
];

/**
 * Cart pose on the pipe. C uses the Cart-scene frame (free hand on the outer side, facing B). On B the cart is rolled half a turn about its own
 * track axis, so its free hand faces C. The cart is symmetric (two identical hands, plate centred between them), so the two poses put the cart
 * in the same place in the world: a hand-over needs no body motion, only the hands change role.
 * plateSide is the cart-y side the plate slides to, so the plate stays on the same side of the track plane on both pipes.
 */
export function cartPose(p: Pipe, s: number): { x: number; z: number; q: Quat; plateSide: 1 | -1 } {
  const pt = pipePoint(p, s);
  const base = frameQuat({ ...pt, tx: Math.abs(pt.tx) < 1e-9 ? 0 : pt.tx });
  return { x: pt.x, z: pt.z, q: p === 'B' ? mul(base, [0, 1, 0, 0]) : base, plateSide: p === 'B' ? -1 : 1 };
}

/** Phases of a transfer: get to the straight part, close the free hand on the other pipe, release the old hand, then climb to the top. */
export type XferPhase = 'swingout' | 'approach' | 'swingin' | 'grip' | 'release' | 'swingout2' | 'climb' | 'swingin2';
export const HAND_MOVE_S = 1; // seconds each clamp takes to close or open
export const SWING_OUT_RAD = (95 * Math.PI) / 180; // how far the rotation motors swing the cart off the pipe during travel
export const SWING_RATE = 1.2;                       // rotation motor speed, rad/s
export const SWING_STEP_DEG = 15;
export const SWING_MAX_RAD = Math.PI;
/** Over this stretch of the path (cm) the two pipes diverge round their bends, so the free clamp has to be swung off the pipe to clear the other track. */
export const CLEAR_FROM_CM = 45, CLEAR_TO_CM = 100;
const WHEEL_R_MM = 10;                               // CAD wheel radius, to turn travel into wheel spin

/** The straight-part height to start the hand-over from, given where the cart is (cm). */
export const handoverHeight = (s: number) => (canTransfer(s) ? s : TRANSFER_DEFAULT_CM);

/** Rotate v by the quaternion q (w x y z). */
export function rotate(q: Quat, v: Vec3): Vec3 {
  const [w, x, y, z] = q;
  const t = [2 * (y * v[2] - z * v[1]), 2 * (z * v[0] - x * v[2]), 2 * (x * v[1] - y * v[0])];
  return [v[0] + w * t[0] + (y * t[2] - z * t[1]), v[1] + w * t[1] + (z * t[0] - x * t[2]), v[2] + w * t[2] + (x * t[1] - y * t[0])];
}

/** Distance (m) from a world point to pipe p's centre line. */
export function distToPipe(p: Pipe, pt: Vec3, horizMm = TRANSFER_HORIZ_MM): number {
  return Math.hypot(distToPath(dir(p) * (pt[0] - pipeX(p)), pt[2], horizMm), pt[1]);
}

/** Radial wheel adjustments for both hands at this pose: hand 1 rides pipe p, hand 2 hangs on the other pipe (see handTrims). */
export function cartTrims(p: Pipe, pose: { x: number; z: number; q: Quat }, swing = 0): { hand1: number[]; hand2: number[] } {
  const c = Math.cos(swing), sn = Math.sin(swing);   // the rotation motors swing the cart about the pipe axis (cart x) before the pose is applied
  const toWorld = (v: Vec3): Vec3 => { const r = rotate(pose.q, [v[0], v[1] * c - v[2] * sn, v[1] * sn + v[2] * c]); return [pose.x + r[0], r[1], pose.z + r[2]]; };
  return {
    hand1: handTrims(1, HAND_SPACING_MM, toWorld, (w) => distToPipe(p, w)),
    hand2: handTrims(2, HAND_SPACING_MM, toWorld, (w) => distToPipe(other(p), w)),
  };
}

/** End of the (shortened) top bar: the highest path coordinate on a transfer track (cm). */
export const TRANSFER_MAX_S = L_VERT + L_ARC + TRANSFER_HORIZ_MM / 10;

/**
 * The transfer sequence as a state machine (no MuJoCo, no DOM): which pipe the cart rides, how far each clamp is open, and the
 * approach / grip / release / climb phases. The cart's pose (cartPose) is driven from the path coordinate on every step, so the
 * cart rotation is held the whole time; the pipe switch swaps the hands' roles without moving the body.
 */
export class TransferRun {
  readonly motion = new CartMotion();
  pipe: Pipe = 'B';
  xfer: { from: Pipe; phase: XferPhase; t: number } | null = null;
  /** Clamp opening per pipe: 0 closed on it, 1 open. The free hand waits open around the other pipe. */
  readonly open: Record<Pipe, number> = { B: 0, C: 1 };
  done = false;
  /** Rotation motors: cart swing about the pipe (rad, away from the track = SWING_OUT_RAD on either pipe) and its goal. The motors hold the goal the whole time. */
  swingW = 0;
  swingGoal = 0;
  /** The hinge angle of the rotation motors in the cart frame. The cart is rolled half a turn on B, so the same swing away from the track is the opposite hinge angle there. */
  get swing() { return this.pipe === 'B' ? -this.swingW : this.swingW; }
  /** Drive motors: wheel spin angle (rad) of hand 1 (on the riding pipe) and hand 2. Only a closed clamp's wheels turn. */
  readonly spin = [0, 0];
  private lastS = NaN;
  private swingTo(g: number) { this.swingGoal = g; }
  private get swung() { return this.swingW === this.swingGoal; }
  /** Manual rotation: step the swing goal (rad), clamped. */
  manualSwing = 0;
  turn(d: number) { if (!this.xfer) this.manualSwing = Math.min(SWING_MAX_RAD, Math.max(-SWING_MAX_RAD, this.manualSwing + d)); }
  /** Free riding (no transfer): hold the manual swing, but swing out whenever the cart's travel crosses the diverging bends, and wait for it before entering them. */
  private freeRide(dt: number) {
    const m = this.motion, lo = Math.min(m.s, m.goal), hi = Math.max(m.s, m.goal);
    const need = hi >= CLEAR_FROM_CM && lo <= CLEAR_TO_CM;
    this.swingGoal = need ? SWING_OUT_RAD : this.manualSwing;
    const g = m.goal;
    if (need && this.swingW !== SWING_OUT_RAD) {
      if (m.s < CLEAR_FROM_CM) m.goal = Math.min(g, CLEAR_FROM_CM);
      else if (m.s > CLEAR_TO_CM) m.goal = Math.max(g, CLEAR_TO_CM);
    }
    m.advance(dt);
    m.goal = g;
    this.roll();
  }
  private moveSwing(dt: number) {
    const e = this.swingGoal - this.swingW, st = SWING_RATE * dt;
    this.swingW = Math.abs(e) <= st ? this.swingGoal : this.swingW + Math.sign(e) * st;
  }
  private roll() {
    const ds = Number.isNaN(this.lastS) ? 0 : this.motion.s - this.lastS; this.lastS = this.motion.s;
    if (this.open[this.pipe] < 0.5) this.spin[0] -= (ds * 10) / WHEEL_R_MM;
    if (this.open[other(this.pipe)] < 0.5) this.spin[1] -= (ds * 10) / WHEEL_R_MM;
  }

  clamp = (s: number) => Math.min(TRANSFER_MAX_S, clampS(s));
  goTo(s: number, speed?: number) { if (speed !== undefined) this.motion.speed = speed; this.motion.goal = this.clamp(s); }
  nudge(d: number, speed?: number) { if (!this.xfer) this.goTo(this.motion.goal + d, speed); }
  start() {
    if (this.xfer) return false;
    this.done = false;
    this.manualSwing = 0;
    this.xfer = { from: this.pipe, phase: 'swingout', t: 0 };
    this.swingTo(SWING_OUT_RAD);   // swing the clamp clear of the track before the cart travels
    return true;
  }
  /** Stop moving; the hand-over itself (grip, release) and the swings always finish. */
  stop() {
    if (this.xfer && this.xfer.phase !== 'approach' && this.xfer.phase !== 'climb') return;
    this.xfer = null; this.motion.goal = this.motion.s;
  }
  advance(dt: number) {
    this.moveSwing(dt);
    const x = this.xfer;
    if (!x) { this.freeRide(dt); return; }
    if (Number.isNaN(this.lastS)) this.lastS = this.motion.s;
    const k = Math.min(1, (x.t += dt) / HAND_MOVE_S);
    const go = (phase: XferPhase) => { x.phase = phase; x.t = 0; };
    switch (x.phase) {
      case 'swingout':
        if (this.swung) { this.goTo(handoverHeight(this.motion.s)); go('approach'); }
        break;
      case 'approach':
        this.motion.advance(dt); this.roll();
        if (!this.motion.moving) { this.swingTo(0); go('swingin'); }
        break;
      case 'swingin':
        if (this.swung) go('grip');
        break;
      case 'grip':
        this.open[other(x.from)] = 1 - k;
        if (k >= 1) go('release');
        break;
      case 'release':
        this.open[x.from] = k;
        if (k >= 1) { this.pipe = other(x.from); this.swingTo(SWING_OUT_RAD); go('swingout2'); }
        break;
      case 'swingout2':
        if (this.swung) { this.goTo(TRANSFER_MAX_S); go('climb'); }
        break;
      case 'climb':
        this.motion.advance(dt); this.roll();
        if (!this.motion.moving) { this.swingTo(0); go('swingin2'); }
        break;
      case 'swingin2':
        if (this.swung) { this.xfer = null; this.done = true; }
        break;
    }
  }
}
