// Planar reach probe of the pod-grab arm (OpenPocket #461): shoulder-to-wrist distance, joint margin and joints of a pin point (dn down the plate, out out of it) with the hand pitched by pitchDeg.
import { solvePlanar, L1, L2, SHOULDER_Z } from '../arm/kinematics.ts';
import { WRIST_TO_HAND } from '../arm/dims.ts';
import { MOTORS } from '../model.ts';
import { TOOL_X, PAN0 } from './layout.ts';

const lim = (id: string) => MOTORS.find((m) => m.id === id)!;
/** Joint margin (deg) of the planar solution (negative: beyond a limit) and the shoulder-to-wrist distance; null when the wrist cannot be at that distance at all. */
export function probe(dn: number, out: number, pitchDeg: number, lat = 0) {
  const pan = PAN0 + Math.atan2(lat, dn) * 180 / Math.PI, rr = Math.hypot(dn, lat);   // beyond the cart's straight run the pan joint turns
  dn = rr;
  const phi = pitchDeg * Math.PI / 180, RAD = Math.PI / 180, DEG = 180 / Math.PI;
  const wr = dn - TOOL_X * Math.cos(phi) - WRIST_TO_HAND * Math.cos(phi);
  const wz = out + TOOL_X * Math.sin(phi) + WRIST_TO_HAND * Math.sin(phi);
  const dr = wr, dz = wz - SHOULDER_Z, d = Math.hypot(dr, dz);
  if (d > L1 + L2 - 1e-4 || d < Math.abs(L1 - L2) + 1e-4) return { d, margin: -999, ok: false, joints: null as Record<string, number> | null };
  const delta = Math.acos((L1 * L1 + d * d - L2 * L2) / (2 * L1 * d)), th1 = Math.atan2(dz, dr) + delta;
  const er = L1 * Math.cos(th1), ez = L1 * Math.sin(th1), th2 = Math.atan2(dz - ez, dr - er);
  const lift = 90 - th1 * DEG, elbow = -th2 * DEG - lift, wrist = pitchDeg - lift - elbow;
  const j: Record<string, number> = { A: pan, B: lift, C: elbow, D: wrist };
  let margin = 999;
  for (const id of ['A', 'B', 'C', 'D']) { const m = lim(id); margin = Math.min(margin, j[id] - m.min, m.max - j[id]); }
  return { d, margin, ok: margin >= 0.5 && !!solvePlanar(pan, dn, out, TOOL_X, 0, pitchDeg), joints: j };
}
