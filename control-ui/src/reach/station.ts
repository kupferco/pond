// Where the cart can stand on the track, and the maths to test the arm from there.
// The arm is fixed on the cart, so "the cart stands at station S" is the same, for the arm, as "the cart stands in its REFERENCE pose (hand C on the track leg at y = -0.29, cart height 0) and the target is moved by the
// inverse of S". A station is therefore a rigid turn R and a point W: the hand's axis line passes through W (a point on the track pipe) and the whole cart is turned by R about it.
//   world point  = R (ref point - H) + W         H = where the riding hand's axis is in the reference pose (hand C: the leg at y = -0.29; hand B: 120 mm further +y)
//   ref point    = R^T (world point - W) + H
// Legs: the cart rides leg A (y = -0.29, hand C) or leg B (y = +0.29, hand B, the other hand of the same cart, the cart not turned), at any height of the straight part, as it is (roll 0) or turned 180 degrees about the
// leg's own axis (roll 180). Runs: the straight part of the bottom or the top run (hand C), roll angle about the run's own axis (0 = the cart's up axis along the run with the plate facing the pipe plane as on a leg).
import { LOOP_TX, LOOP_ZB, LOOP_ZT, XT, YC } from '../transplant/layout.ts';
import { CART_MAX, CART_MIN, CART_STEP } from './layout.ts';

export type V3 = [number, number, number];
export type Mat = [V3, V3, V3];
export type Q = [number, number, number, number];
const c = (d: number) => Math.cos(d * Math.PI / 180), s = (d: number) => Math.sin(d * Math.PI / 180);
export const Rz = (d: number): Mat => [[c(d), -s(d), 0], [s(d), c(d), 0], [0, 0, 1]];
export const Rx = (d: number): Mat => [[1, 0, 0], [0, c(d), -s(d)], [0, s(d), c(d)]];
export const Ry = (d: number): Mat => [[c(d), 0, s(d)], [0, 1, 0], [-s(d), 0, c(d)]];
export const mmul = (a: Mat, b: Mat): Mat => a.map((r) => [0, 1, 2].map((j) => r[0] * b[0][j] + r[1] * b[1][j] + r[2] * b[2][j])) as Mat;
export const mv = (a: Mat, v: V3): V3 => [a[0][0] * v[0] + a[0][1] * v[1] + a[0][2] * v[2], a[1][0] * v[0] + a[1][1] * v[1] + a[1][2] * v[2], a[2][0] * v[0] + a[2][1] * v[1] + a[2][2] * v[2]];
export const mT = (a: Mat): Mat => [[a[0][0], a[1][0], a[2][0]], [a[0][1], a[1][1], a[2][1]], [a[0][2], a[1][2], a[2][2]]];
const sub = (a: V3, b: V3): V3 => [a[0] - b[0], a[1] - b[1], a[2] - b[2]], add = (a: V3, b: V3): V3 => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
export function quatOf(m: Mat): Q {
  const t = m[0][0] + m[1][1] + m[2][2];
  let q: Q;
  if (t > 0) { const r = Math.sqrt(1 + t) * 2; q = [r / 4, (m[2][1] - m[1][2]) / r, (m[0][2] - m[2][0]) / r, (m[1][0] - m[0][1]) / r]; }
  else if (m[0][0] > m[1][1] && m[0][0] > m[2][2]) { const r = Math.sqrt(1 + m[0][0] - m[1][1] - m[2][2]) * 2; q = [(m[2][1] - m[1][2]) / r, r / 4, (m[0][1] + m[1][0]) / r, (m[0][2] + m[2][0]) / r]; }
  else if (m[1][1] > m[2][2]) { const r = Math.sqrt(1 + m[1][1] - m[0][0] - m[2][2]) * 2; q = [(m[0][2] - m[2][0]) / r, (m[0][1] + m[1][0]) / r, r / 4, (m[1][2] + m[2][1]) / r]; }
  else { const r = Math.sqrt(1 + m[2][2] - m[0][0] - m[1][1]) * 2; q = [(m[1][0] - m[0][1]) / r, (m[0][2] + m[2][0]) / r, (m[1][2] + m[2][1]) / r, r / 4]; }
  return q;
}

export const LEG_A_Y = -LOOP_TX, LEG_B_Y = LOOP_TX;
const O: V3 = [XT, YC, 0];                              // the reference cart origin
const H_C: V3 = [XT, YC - 0.06, 0], H_B: V3 = [XT, YC + 0.06, 0];
const YRUN = 0.08, RUN_STEP = 0.005;                    // straight part of a run (LOOP_TX - corner radius 0.15 - 0.06 for the sleeve)
const ZB = LOOP_ZB, ZT = LOOP_ZT;                      // run heights: the unit's (transplant/layout.ts, bottom run from the shared layout cad/layout.json; was a separate copy of 0.45)

export interface Station { kind: 'leg A' | 'leg B' | 'bottom run' | 'top run'; roll: number; at: number; R: Mat; W: V3; H: V3; pos: V3; quat: Q; label: string }
function make(kind: Station['kind'], roll: number, at: number, R: Mat, W: V3, H: V3): Station {
  const pos = add(mv(R, sub(O, H)), W);
  const unit = kind.startsWith('leg') ? 'm high' : 'm along the run (y)';
  return { kind, roll, at, R, W, H, pos, quat: quatOf(R), label: `${kind}, ${at.toFixed(3)} ${unit}, rolled ${roll}°` };
}
/** The reference station: leg A, cart as it is, at height z. */
export const refStation = (z: number) => make('leg A', 0, z, Rz(0), [XT, LEG_A_Y, z], H_C);
/** Every station of one kind and roll. */
export function stations(kind: Station['kind'], roll: number): Station[] {
  const out: Station[] = [];
  if (kind === 'leg A' || kind === 'leg B') for (let z = CART_MIN; z <= CART_MAX + 1e-9; z += CART_STEP) out.push(make(kind, roll, z, Rz(roll), [XT, kind === 'leg A' ? LEG_A_Y : LEG_B_Y, z], kind === 'leg A' ? H_C : H_B));
  else for (let y = -YRUN; y <= YRUN + 1e-9; y += RUN_STEP) out.push(make(kind, roll, y, mmul(Ry(roll), Rx(kind === 'top run' ? -90 : 90)), [XT, y, kind === 'top run' ? ZT : ZB], H_C));
  return out;
}
/** The target (point p, direction d) as the reference cart sees it when the cart stands at st. */
export const toRef = (st: Station, p: V3): V3 => add(mv(mT(st.R), sub(p, st.W)), st.H);
export const dirToRef = (st: Station, d: V3): V3 => mv(mT(st.R), d);
