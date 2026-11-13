// Transfer scene maths: two neighbouring units' pipes B and C, and the cart handing over between them. No MuJoCo or DOM.
// B is the right-hand pipe of unit 1 (its top bar runs LEFT); C is the left-hand pipe of unit 2 (its top bar runs RIGHT).
// The hands are 14 cm apart, so B and C are 14 cm apart. The cart rides on one pipe and its free hand hangs towards the other.
import { CartMotion, L_ARC, clampS, distToPath, frameQuat, pathAt, L_VERT, type PathPoint } from './track.ts';
import { handTrims, setCart, setMotors, type Vec3 } from './model.ts';

/** Sign of the rotation-motor hinge for a swing away from the track, riding B (rolled half a turn) and C. */
export const SB = -1, SC = 1;
export const HAND_SPACING_MM = 140;
export const PIPE_GAP_M = HAND_SPACING_MM / 1000;
export const TRANSFER_HORIZ_MM = 450;    // shortened top bars: enough to show them
export const TRANSFER_MIN_CM = 15;       // lowest point of the vertical section where a transfer is allowed
export const TRANSFER_MAX_HANDOVER_CM = L_VERT - 5;  // highest point of the vertical section where a hand-over may start: the tracks are still parallel here
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

export const canTransfer = (s: number) => s >= TRANSFER_MIN_CM && s <= TRANSFER_MAX_HANDOVER_CM;

type Quat = [number, number, number, number];
/** Rotation matrix columns (cart x, y, z in the world) to a quaternion (w x y z). */
function quatFromAxes(ex: Vec3, ey: Vec3, ez: Vec3): Quat {
  const m00 = ex[0], m10 = ex[1], m20 = ex[2], m01 = ey[0], m11 = ey[1], m21 = ey[2], m02 = ez[0], m12 = ez[1], m22 = ez[2];
  const tr = m00 + m11 + m22;
  let q: Quat;
  if (tr > 0) { const S = Math.sqrt(tr + 1) * 2; q = [S / 4, (m21 - m12) / S, (m02 - m20) / S, (m10 - m01) / S]; }
  else if (m00 > m11 && m00 > m22) { const S = Math.sqrt(1 + m00 - m11 - m22) * 2; q = [(m21 - m12) / S, S / 4, (m01 + m10) / S, (m02 + m20) / S]; }
  else if (m11 > m22) { const S = Math.sqrt(1 + m11 - m00 - m22) * 2; q = [(m02 - m20) / S, (m01 + m10) / S, S / 4, (m12 + m21) / S]; }
  else { const S = Math.sqrt(1 + m22 - m00 - m11) * 2; q = [(m10 - m01) / S, (m02 + m20) / S, (m12 + m21) / S, S / 4]; }
  return q;
}

/** Which of the cart's two hands rides pipe p: hand 1 on C, hand 2 on B (the cart is mirror-symmetric, so B is the mirror image of C). */
export const riderHand = (p: Pipe): 1 | 2 => (p === 'B' ? 2 : 1);
/** Put a value for the riding hand and one for the free hand in hand 1 / hand 2 order. */
export const byHand = <T>(p: Pipe, rider: T, free: T): [T, T] => (p === 'B' ? [free, rider] : [rider, free]);

/**
 * Cart pose on the pipe. On C hand 1 rides the pipe (origin on its axis) and hand 2 hangs towards B. B is the exact mirror image of C about the
 * plane half way between them, and the cart is symmetric under that mirror, so on B hand 2 rides the pipe and hand 1 hangs towards C: same
 * orientation at the straights, no roll, the plate on the same world side. The same wheel pair is the clamp pair on both.
 * plateSide is the cart-y side the plate slides to (the same on both pipes).
 */
export function cartPose(p: Pipe, s: number): { x: number; z: number; q: Quat; plateSide: 1 | -1 } {
  const pt = pipePoint(p, s);
  const th = Math.atan2(-pt.tz, p === 'B' ? -pt.tx : pt.tx);       // C-frame angle of the (mirrored back) tangent, see frameQuat
  const ex: Vec3 = [Math.cos(th), 0, -Math.sin(th)], ey: Vec3 = [0, -1, 0], ez: Vec3 = [-Math.sin(th), 0, -Math.cos(th)];
  if (p === 'C') return { x: pt.x, z: pt.z, q: quatFromAxes(ex, ey, ez), plateSide: 1 };
  // mirror x of the C frame: (m ex, m ey, -m ez); hand 2 is on the pipe, so the origin (hand 1) is one hand spacing along z' from it
  const mx: Vec3 = [-ex[0], ex[1], ex[2]], my: Vec3 = [-ey[0], ey[1], ey[2]], mz: Vec3 = [ez[0], -ez[1], -ez[2]];
  return { x: pt.x + PIPE_GAP_M * mz[0], z: pt.z + PIPE_GAP_M * mz[2], q: quatFromAxes(mx, my, mz), plateSide: 1 };
}

/** Phases of a transfer: drive in-plane to the straight part, close the free hand on the other pipe, release the old hand, then drive to the top. */
export type XferPhase = 'approach' | 'grip' | 'release' | 'climb';
export const HAND_MOVE_S = 1; // seconds each clamp takes to close or open
export const SWING_RATE = 1.2;                       // rotation motor speed, rad/s
export const SWING_STEP_DEG = 15;
export const SWING_MAX_RAD = Math.PI;
export const SWING_MAX_NEEDED_RAD = (100 * Math.PI) / 180;   // the most the rotation motors ever need to swing the cart to clear the other track
const SWING_GRID_RAD = (2.5 * Math.PI) / 180, SWING_MARGIN_RAD = (3 * Math.PI) / 180;
const TABLE_STEP_CM = 0.5, TABLE_WINDOW = 3;         // the needed swing is held 1.5 cm either side of where it is needed, so the rotation motors are ready in time
const WHEEL_R_MM = 10;                               // CAD wheel radius, to turn travel into wheel spin

/** Whether the cart riding pipe p at path coordinate s (cm), its free hand open and swung away from the track by `swing` rad, touches the track (false) or not (true). */
export type ClearCheck = (p: Pipe, s: number, swing: number) => boolean;
/** The smallest swing (rad) that clears the other track at each path coordinate: [pipe][round(s / TABLE_STEP_CM)]. Zero where the plane of the tracks is already clear. */
export type SwingTable = Record<Pipe, number[]>;

export function buildSwingTable(clear: ClearCheck): SwingTable {
  const out = {} as SwingTable;
  for (const p of ['B', 'C'] as Pipe[]) {
    const raw: number[] = [];
    for (let i = 0; i * TABLE_STEP_CM <= TRANSFER_MAX_S + 1e-9; i++) {
      const s = i * TABLE_STEP_CM;
      let th = 0;
      // first angle that is clear, including the margin on both sides, so the swing never rides along the edge of a collision
      while (th < SWING_MAX_NEEDED_RAD && !(clear(p, s, th) && clear(p, s, th + SWING_MARGIN_RAD) && (th === 0 || clear(p, s, th - SWING_MARGIN_RAD)))) th += SWING_GRID_RAD;
      raw.push(Math.min(th, SWING_MAX_NEEDED_RAD));
    }
    out[p] = raw.map((_, i) => Math.max(...raw.slice(Math.max(0, i - TABLE_WINDOW), i + TABLE_WINDOW + 1)));
  }
  return out;
}

/** Swing (rad) needed at path coordinate s, taking the larger of the two table cells around it. */
export function swingNeeded(t: SwingTable | null, p: Pipe, s: number): number {
  if (!t) return 0;
  const a = t[p], f = Math.min(a.length - 1, Math.max(0, s / TABLE_STEP_CM)), i = Math.floor(f);
  return Math.max(a[i], a[Math.min(a.length - 1, i + 1)]);
}

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

/** Radial wheel adjustments for both hands at this pose (see handTrims): the riding hand follows pipe p, the other hangs on the other pipe. In hand 1 / hand 2 order. */
export function cartTrims(p: Pipe, pose: { x: number; z: number; q: Quat }, swing = 0): { hand1: number[]; hand2: number[] } {
  const c = Math.cos(swing), sn = Math.sin(swing);   // the rotation motors swing the cart about the pipe axis (cart x) before the pose is applied
  const pz = p === 'B' ? -PIPE_GAP_M : 0;             // the pivot is the riding hand's pipe axis: hand 2 on B
  const toWorld = (v: Vec3): Vec3 => { const y = v[1], z = v[2] - pz; const r = rotate(pose.q, [v[0], y * c - z * sn, y * sn + z * c + pz]); return [pose.x + r[0], r[1], pose.z + r[2]]; };
  const [on1, on2] = byHand<Pipe>(p, p, other(p));
  return {
    hand1: handTrims(1, HAND_SPACING_MM, toWorld, (w) => distToPipe(on1, w)),
    hand2: handTrims(2, HAND_SPACING_MM, toWorld, (w) => distToPipe(on2, w)),
  };
}

/**
 * Put the whole cart into the model for the run state: the clamp openings, wheel spins and swing hinge, with the hands swapped for the pipe it rides.
 * `open` is the opening per pipe, `spin` the wheel spin of the riding hand then the free one, `hinge` the rotation-motor angle.
 */
export function applyCart(model: Parameters<typeof setCart>[0] & Parameters<typeof setMotors>[0], data: Parameters<typeof setMotors>[1], pipe: Pipe,
  pose: { plateSide: 1 | -1 }, tr: { hand1: number[]; hand2: number[] }, open: Record<Pipe, number>, spin: number[], hinge: number): void {
  const [o1, o2] = byHand(pipe, open[pipe], open[other(pipe)]), [s1, s2] = byHand(pipe, spin[0], spin[1]);
  setCart(model, data.qpos, o1, o2, pose.plateSide, tr.hand1, tr.hand2);
  setMotors(model, data, s1, s2, hinge, riderHand(pipe));
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
  /** Rotation motors: cart swing about the pipe (rad, away from the track = positive on either pipe) and its goal. The motors hold the goal the whole time. */
  swingW = 0;
  swingGoal = 0;
  /** The hinge angle of the rotation motors in the cart frame. The cart is rolled half a turn on B, so the same swing away from the track is the opposite hinge angle there. */
  get swing() { return (this.pipe === 'B' ? SB : SC) * this.swingW; }
  /** Drive motors: wheel spin angle (rad) of hand 1 (on the riding pipe) and hand 2. Only a closed clamp's wheels turn. */
  readonly spin = [0, 0];
  private lastS = NaN;
  /** Manual rotation from the Step tab: step the swing goal (rad), clamped. */
  manualSwing = 0;
  turn(d: number) { if (!this.xfer) this.manualSwing = Math.min(SWING_MAX_RAD, Math.max(-SWING_MAX_RAD, this.manualSwing + d)); }
  readonly table: SwingTable | null;
  constructor(table: SwingTable | null = null) { this.table = table; }
  private need = (s: number) => swingNeeded(this.table, this.pipe, s);
  private moveSwing(dt: number) {
    const e = this.swingGoal - this.swingW, st = SWING_RATE * dt;
    this.swingW = Math.abs(e) <= st ? this.swingGoal : this.swingW + Math.sign(e) * st;
  }
  /**
   * Drive along the pipe in the plane of the tracks. The cart rotates only where the other track is in the way (round the bend) and exactly as far
   * as it needs, and turns back as soon as it is clear. If the rotation motors are not yet at the angle the next step needs, the cart waits for them.
   */
  private ride(dt: number) {
    const m = this.motion, ahead = m.s + Math.sign(m.goal - m.s) * Math.min(Math.abs(m.goal - m.s), Math.max(0, m.speed) * dt);
    const need = m.moving ? Math.max(this.need(m.s), this.need(ahead)) : this.need(m.s);
    this.swingGoal = this.xfer ? need : Math.max(need, this.manualSwing);
    if (this.swingW >= need - 1e-9) m.advance(dt);
    this.roll();
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
    this.xfer = { from: this.pipe, phase: 'approach', t: 0 };
    this.goTo(handoverHeight(this.motion.s));
    return true;
  }
  /** Stop moving; the hand-over itself (grip, release) always finishes. */
  stop() {
    if (this.xfer && this.xfer.phase !== 'approach' && this.xfer.phase !== 'climb') return;
    this.xfer = null; this.motion.goal = this.motion.s;
  }
  advance(dt: number) {
    this.moveSwing(dt);
    const x = this.xfer;
    if (!x) { this.ride(dt); return; }
    if (Number.isNaN(this.lastS)) this.lastS = this.motion.s;
    const k = Math.min(1, (x.t += dt) / HAND_MOVE_S);
    const go = (phase: XferPhase) => { x.phase = phase; x.t = 0; };
    switch (x.phase) {
      case 'approach':
        this.ride(dt);
        if (!this.motion.moving && this.swingW === 0) go('grip');
        break;
      case 'grip':
        this.open[other(x.from)] = 1 - k;
        if (k >= 1) go('release');
        break;
      case 'release':
        this.open[x.from] = k;
        if (k >= 1) { this.pipe = other(x.from); this.goTo(TRANSFER_MAX_S); go('climb'); }
        break;
      case 'climb':
        this.ride(dt);
        if (!this.motion.moving && this.swingW === 0) { this.xfer = null; this.done = true; }
        break;
    }
  }
}
