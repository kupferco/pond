// Where the cart stands in a sim scene, measured against the track leg it rides, so every scene can be compared with the CAD's Complete unit (OpenPocket #447).
// The CAD (cad/complete_unit.py): the cart's riding hand B clamps the unit's right track leg, the pipe axis exactly on the leg's axis, the cart upright (its z along the leg),
// the plate on the side away from the unit (roll 0), and the other hand C hangs on the OUTER side of the leg, where the neighbour unit's leg is.
// A sim scene may roll the cart about the leg (the working pose of the transplant scenes is rolled 180 degrees, the plate towards the unit); this reports the roll, it does not forbid it.
// Frame helpers are pure: pass a posed MuJoCo model and data (after mj_forward) and the leg.
import type { Hand } from './omni.ts';

export type V3 = [number, number, number];
export interface Leg {
  /** A point on the leg's axis (m, sim world). */
  point: V3;
  /** Unit direction along the leg (sim world). */
  dir: V3;
  /** Unit direction from the leg towards the middle of the unit (where the growing pipe stands), perpendicular to dir: in the CAD travel pose the cart's +y points this way. */
  toUnit: V3;
  /** Unit direction along the track plane, perpendicular to dir and toUnit, pointing OUT of the loop (away from the loop's middle). */
  outward: V3;
}
export interface Placement {
  rider: Hand;
  /** Distance (mm) of the riding hand's pipe axis from the leg's axis: 0 when the hand is clamped on the leg. */
  offAxisMm: number;
  /** Angle (deg) between the cart's z axis and the leg's direction: 0 when the cart stands upright on the leg (0 or 180, by sign of the sign). */
  tiltDeg: number;
  /** Roll of the cart about the leg (deg) from the CAD travel pose (plate away from the unit): 0 = as in the Complete unit, 180 = plate towards the unit. */
  rollDeg: number;
  /** Where the free hand's pipe axis is, relative to the leg, as a side: 'outer' (CAD travel pose) or 'inner' (over the unit). */
  freeSide: 'outer' | 'inner' | 'same';
  /** Distance (mm) from the leg's axis to the free hand's pipe axis (120 for a straight cart). */
  freeDistMm: number;
}
type Mdl = { body(name: string): { id: number } };
type Dt = { xpos: ArrayLike<number>; xmat: ArrayLike<number> };
const dot = (a: V3, b: V3) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const sub = (a: V3, b: V3): V3 => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const norm = (a: V3) => Math.sqrt(dot(a, a));

/** Measure a cart whose hand bodies are called hand<B|C> (the omni cart of omni.ts). axes: cart x, y, z in the world are the columns of the hand body's rotation. */
export function placementOf(model: Mdl, data: Dt, leg: Leg, rider: Hand): Placement {
  const pos = (h: Hand): V3 => { const i = model.body('hand' + h).id; return [data.xpos[3 * i], data.xpos[3 * i + 1], data.xpos[3 * i + 2]]; };
  const i0 = model.body('hand' + rider).id;
  const col = (c: number): V3 => [data.xmat[9 * i0 + c], data.xmat[9 * i0 + 3 + c], data.xmat[9 * i0 + 6 + c]];   // body x, y, z axes in the world
  const cy = col(1), cz = col(2);
  const p = pos(rider), q = pos(rider === 'B' ? 'C' : 'B');
  const perp = (v: V3): V3 => { const t = dot(v, leg.dir); return [v[0] - t * leg.dir[0], v[1] - t * leg.dir[1], v[2] - t * leg.dir[2]]; };
  const r = perp(sub(p, leg.point));
  const tilt = (Math.acos(Math.max(-1, Math.min(1, Math.abs(dot(cz, leg.dir))))) * 180) / Math.PI;
  const yPerp = perp(cy);
  const rollDeg = (Math.atan2(dot(yPerp, leg.outward), dot(yPerp, leg.toUnit)) * 180) / Math.PI;   // 0 when cart y points to the unit (plate away from it)
  const free = perp(sub(q, leg.point));
  const side = dot(free, leg.outward);
  return {
    rider, offAxisMm: norm(r) * 1000, tiltDeg: tilt, rollDeg,
    freeSide: Math.abs(norm(free) - norm(r)) < 1e-6 ? 'same' : side > 1e-4 ? 'outer' : side < -1e-4 ? 'inner' : 'same',
    freeDistMm: norm(sub(q, p)) * 1000,
  };
}
