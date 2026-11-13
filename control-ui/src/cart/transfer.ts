// Transfer scene maths: two neighbouring units' pipes B and C, and the cart handing over between them. No MuJoCo or DOM.
// B is the right-hand pipe of unit 1 (its top bar runs LEFT); C is the left-hand pipe of unit 2 (its top bar runs RIGHT).
// The hands are 14 cm apart, so B and C are 14 cm apart. The cart rides on one pipe and its free hand hangs towards the other.
import { frameQuat, pathAt, L_VERT, type PathPoint } from './track.ts';

export const HAND_SPACING_MM = 140;
export const PIPE_GAP_M = HAND_SPACING_MM / 1000;
export const TRANSFER_HORIZ_MM = 450;    // shortened top bars: enough to show them
export const TRANSFER_MIN_CM = 15;       // lowest point of the vertical section where a transfer is allowed
export const TRANSFER_DEFAULT_CM = 40;   // transfers happen below the bend; the verticals carry no brackets
export const TRANSFER_S = 2;             // seconds a hand-over takes

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
 * track axis, so its free hand faces C. roll (radians about the cart x axis) is added on top, for the hand-over.
 */
export function cartPose(p: Pipe, s: number, rollRad = 0): { x: number; z: number; q: Quat } {
  const pt = pipePoint(p, s);
  const base = frameQuat({ ...pt, tx: Math.abs(pt.tx) < 1e-9 ? 0 : pt.tx });
  const half = (p === 'B' ? Math.PI : 0) + rollRad;
  return { x: pt.x, z: pt.z, q: mul(base, [Math.cos(half / 2), Math.sin(half / 2), 0, 0]) };
}

/** A hand-over between pipes at height s (cm): the cart rolls over and shifts 14 cm across. progress 0..1. */
export function transferPose(from: Pipe, s: number, progress: number) {
  const k = Math.min(1, Math.max(0, progress));
  const eased = k * k * (3 - 2 * k);
  const a = pipeX(from), b = pipeX(other(from));
  const start = cartPose(from, s);
  // Roll from the 'from' orientation to the 'to' orientation (half a turn either way), starting from the base frame of the from pipe.
  const roll = Math.PI * eased * (from === 'B' ? 1 : -1);
  const pose = cartPose(from, s, roll);
  return { x: a + (b - a) * eased, z: start.z, q: pose.q };
}
