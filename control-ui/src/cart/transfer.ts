// Transfer scene maths: two neighbouring units' pipes B and C, and the cart handing over between them. No MuJoCo or DOM.
// B is the right-hand pipe of unit 1 (its top bar runs LEFT); C is the left-hand pipe of unit 2 (its top bar runs RIGHT).
// The hands are 14 cm apart, so B and C are 14 cm apart. The cart rides on one pipe and its free hand hangs towards the other.
import { distToPath, frameQuat, pathAt, L_VERT, type PathPoint } from './track.ts';
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
export type XferPhase = 'approach' | 'grip' | 'release' | 'climb';
export const HAND_MOVE_S = 1; // seconds each clamp takes to close or open

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
export function cartTrims(p: Pipe, pose: { x: number; z: number; q: Quat }): { hand1: number[]; hand2: number[] } {
  const toWorld = (v: Vec3): Vec3 => { const r = rotate(pose.q, v); return [pose.x + r[0], r[1], pose.z + r[2]]; };
  return {
    hand1: handTrims(1, HAND_SPACING_MM, toWorld, (w) => distToPipe(p, w)),
    hand2: handTrims(2, HAND_SPACING_MM, toWorld, (w) => distToPipe(other(p), w)),
  };
}
