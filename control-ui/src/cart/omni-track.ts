// The omni-wheel cart on ONE track pipe (OpenPocket #282, plan task 265 part 8): placement on the path, bend trim, roll limits.
// Cart frame = CAD hand frame of src/cart/omni.ts: z along the pipe, x across (hand B at -60, hand C at +60), y out of the track plane, plate on -y.
// The cart rides on hand B; hand C is released and hangs beside the track on the INSIDE of the bend (cart +x = towards the bend's centre).
// Mapping to the track (pathAt: x right, z up, pipe at y = 0): cart z = tangent t, cart x = inward normal n = (tz, 0, -tx), cart y = world +Y.
import { omniCartBody, omniActuators, setOmniCart, PIPE_X, type Hand } from './omni.ts';
import { pipeGeoms } from './model.ts';
import { pathAt, type PathPoint } from './track.ts';

export const RIDER: Hand = 'B';
export const DEG = Math.PI / 180;

/** Pose of the cart on the track: the path point (cm), a trim in the cart frame (mm, mm, deg): dx across (+ = inward), dy out of the plane, yaw about the cart y axis. */
export interface BendTrim { dx: number; dy: number; yaw: number }
export const NO_TRIM: BendTrim = { dx: 0, dy: 0, yaw: 0 };

/**
 * Rows [s cm, dx mm, yaw deg] of the best trim of the RIGID cart through the R150 bend, from scripts/search-roll.ts (max of the least clearance over dx and yaw, 1 cm steps).
 * The straight sleeve (124 mm) does NOT clear the bend: the best trim still leaves up to 3.99 mm of penetration in the middle of the bend (plan section 13 risk 5).
 * Outside the rows (the straights) the trim is zero.
 */
export const BEND_TRIM_ROWS: [number, number, number][] = [
  [58, 0.5, 1.5], [59, 1, 3.5], [60, 2, 6], [61, 3, 4.5], [62, 4, 3], [63, 4.5, 2], [64, 5, 1], [65, 5.5, 0.5], [66, 6, 0.5], [67, 6, 0], [68, 6, 0], [69, 6, 0],
  [70, 6, 0], [71, 6, 0], [72, 6, 0], [73, 6, 0], [74, 6, 0], [75, 6, 0], [76, 6, 0], [77, 6, 0], [78, 6, 0], [79, 5.5, -1], [80, 5, -1.5], [81, 4, -2.5],
  [82, 3.5, -3.5], [83, 2, -5.5], [84, 0.5, -5.5], [85, 0, -3], [86, 0, -1],
];
/** The bend trim at path position s (cm), linearly interpolated between the rows, zero outside them. */
export function bendTrim(sCm: number): BendTrim {
  const R = BEND_TRIM_ROWS;
  if (sCm <= R[0][0] || sCm >= R[R.length - 1][0]) return NO_TRIM;
  let i = 0;
  while (R[i + 1][0] < sCm) i++;
  const f = (sCm - R[i][0]) / (R[i + 1][0] - R[i][0]);
  return { dx: R[i][1] + f * (R[i + 1][1] - R[i][1]), dy: 0, yaw: R[i][2] + f * (R[i + 1][2] - R[i][2]) };
}

/** World position (m) and MuJoCo quaternion (w x y z) of the cart origin when the riding hand's pipe axis sits on the track at s (cm), with a trim. */
export function cartPose(sCm: number, trim: BendTrim = NO_TRIM): { pos: [number, number, number]; quat: [number, number, number, number] } {
  const p: PathPoint = pathAt(sCm);
  const yaw = trim.yaw * DEG, c = Math.cos(yaw), sn = Math.sin(yaw);
  // tangent and inward normal of the track, then the cart axes turned by the trim yaw about y (z' = c z + sn x, x' = c x - sn z)
  const t: [number, number] = [p.tx, p.tz], n: [number, number] = [p.tz, -p.tx];
  const zx = c * t[0] + sn * n[0], zz = c * t[1] + sn * n[1];
  const xx = c * n[0] - sn * t[0], xz = c * n[1] - sn * t[1];
  // rotation matrix columns: cart x, y, z in world
  const R = [[xx, 0, zx], [0, 1, 0], [xz, 0, zz]];
  const quat = matToQuat(R);
  // the riding pipe axis is at cart (PIPE_X[B], 0, 0): put it on the track point, shifted by the trim
  const local: [number, number, number] = [PIPE_X[RIDER] / 1000 - trim.dx / 1000, -trim.dy / 1000, 0];
  const off = [R[0][0] * local[0] + R[0][1] * local[1] + R[0][2] * local[2], R[1][0] * local[0] + R[1][1] * local[1] + R[1][2] * local[2], R[2][0] * local[0] + R[2][1] * local[1] + R[2][2] * local[2]];
  return { pos: [p.x - off[0], -off[1], p.z - off[2]], quat };
}

export function matToQuat(R: number[][]): [number, number, number, number] {
  const tr = R[0][0] + R[1][1] + R[2][2];
  let w: number, x: number, y: number, z: number;
  if (tr > 0) { const s = Math.sqrt(tr + 1) * 2; w = s / 4; x = (R[2][1] - R[1][2]) / s; y = (R[0][2] - R[2][0]) / s; z = (R[1][0] - R[0][1]) / s; }
  else if (R[0][0] > R[1][1] && R[0][0] > R[2][2]) { const s = Math.sqrt(1 + R[0][0] - R[1][1] - R[2][2]) * 2; w = (R[2][1] - R[1][2]) / s; x = s / 4; y = (R[0][1] + R[1][0]) / s; z = (R[0][2] + R[2][0]) / s; }
  else if (R[1][1] > R[2][2]) { const s = Math.sqrt(1 + R[1][1] - R[0][0] - R[2][2]) * 2; w = (R[0][2] - R[2][0]) / s; x = (R[0][1] + R[1][0]) / s; y = s / 4; z = (R[1][2] + R[2][1]) / s; }
  else { const s = Math.sqrt(1 + R[2][2] - R[0][0] - R[1][1]) * 2; w = (R[1][0] - R[0][1]) / s; x = (R[0][2] + R[2][0]) / s; y = (R[1][2] + R[2][1]) / s; z = s / 4; }
  return [w, x, y, z];
}

/** The cart on the track: floor-free scene with the track pipe and the cart on a mocap body (hand B rides, hand C is released). */
export function omniTrackMjcf(): string {
  return `
<mujoco model="pond_omni_cart_on_track">
  <option timestep="0.002" gravity="0 0 -9.81"/>
  <worldbody>
    <geom name="floor" type="plane" pos="0.4 0 -0.05" size="1.4 0.9 0.1" rgba="0.82 0.86 0.9 1"/>
    ${pipeGeoms()}
    <body name="marker" mocap="true" pos="0 0 -50">
      <geom type="box" size="0.004 0.06 0.05" rgba="0.93 0.45 0.1 1" contype="0" conaffinity="0"/>
    </body>
    <body name="omnicart" mocap="true" pos="0 0 0">
      ${omniCartBody()}
    </body>
  </worldbody>
  ${omniActuators()}
</mujoco>`;
}

type Mj = Parameters<typeof setOmniCart>[0] & { body(name: string): { id: number }; body_mocapid: ArrayLike<number> };
type Dt = Parameters<typeof setOmniCart>[1] & { mocap_pos: { [i: number]: number }; mocap_quat: { [i: number]: number } };

/** Put the cart at path position s (cm) with roll (rad) about the riding pipe and the drive wheels turned to match, and the bend trim. */
export function placeOmniCart(model: Mj, data: Dt, sCm: number, rollRad: number, trim: BendTrim = NO_TRIM, driveAngle = 0): void {
  const mc = model.body_mocapid[model.body('omnicart').id];
  const { pos, quat } = cartPose(sCm, trim);
  for (let k = 0; k < 3; k++) data.mocap_pos[3 * mc + k] = pos[k];
  for (let k = 0; k < 4; k++) data.mocap_quat[4 * mc + k] = quat[k];
  setOmniCart(model, data, { roll: rollRad, staticHand: RIDER, driveAngle });
}

export type Owner = 'rider' | 'freehand' | 'base' | 'other';
/** Which part of the cart a body belongs to: the riding hand B (sleeve, wheels, balls), the released hand C, or the rigid base (plate, battery, arm base). */
export const ownerOf = (body: string): Owner => /^(handC|driveC|rollwheelC|ballC|jawC)/.test(body) ? 'freehand' : body === 'base' ? 'base' : /^(handB|driveB|rollwheelB|ballB|jawB)/.test(body) ? 'rider' : 'other';
type Cm = { ngeom: number; geom_bodyid: ArrayLike<number>; body(i: number): { name: string; delete?(): void } };
type Cd = { ncon: number; contact: { get(i: number): { geom1: number; geom2: number; dist: number; delete?(): void } | undefined; delete?(): void } };
/** Deepest penetration (m, negative; 0 = none) of each part of the cart against the track pipe. Call after mj_forward. */
export function trackContacts(model: Cm, data: Cd): Record<Owner, number> {
  const out: Record<Owner, number> = { rider: 0, freehand: 0, base: 0, other: 0 }, con = data.contact;
  for (let i = 0; i < data.ncon; i++) {
    const c = con.get(i)!;
    const nm = (g: number) => { const b = model.body(model.geom_bodyid[g]); const n = b.name; b.delete?.(); return n; };
    const b1 = nm(c.geom1), b2 = nm(c.geom2), o = ownerOf(b1 === 'world' ? b2 : b1);
    out[o] = Math.min(out[o], c.dist);
    c.delete?.();
  }
  con.delete?.();
  return out;
}
