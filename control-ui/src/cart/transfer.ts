// Transfer scene maths: two neighbouring units' pipes B and C, and the cart handing over between them. No MuJoCo or DOM.
// B is the right-hand pipe of unit 1 (its top bar runs LEFT); C is the left-hand pipe of unit 2 (its top bar runs RIGHT).
// The hands are 14 cm apart, so B and C are 14 cm apart. The cart rides on one pipe and its free hand hangs towards the other.
import { frameQuat, pathAt, L_VERT, type PathPoint } from './track.ts';

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
