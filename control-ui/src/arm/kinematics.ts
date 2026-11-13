// Analytic inverse kinematics for the SO-101 stand-in, for a top-down grasp: the hand points straight down,
// pan turns the arm towards the target and shoulder lift / elbow / wrist flex solve a planar problem.
// Link lengths and offsets mirror the MJCF in model.ts.
import { MOTORS } from '../model.ts';
import { GRASP_X, GRASP_Z, WRIST_TO_HAND } from './dims.ts';

const RAD = Math.PI / 180;
const DEG = 180 / Math.PI;
export const SHOULDER_Z = 0.048 + 0.047; // turntable + shoulder offset
export const L1 = 0.115;                 // shoulder -> elbow
export const L2 = 0.135;                 // elbow -> wrist
/** Tool pitch for "hand pointing straight down" (sum of lift + elbow + wrist flex, degrees). */
export const DOWN_PITCH = 90;

export interface Joints { A: number; B: number; C: number; D: number; E: number }

const limits = (id: string) => MOTORS.find((m) => m.id === id)!;

/** A tool point (tx forward along the hand, tz across it) in world coordinates for the given pan/lift/elbow/wrist angles (degrees). */
export function toolPoint(j: { A: number; B: number; C: number; D: number }, tx: number, tz: number): [number, number, number] {
  const al = j.B * RAD, th2 = -(j.B + j.C) * RAD, phi = (j.B + j.C + j.D) * RAD;
  const r = L1 * Math.sin(al) + L2 * Math.cos(th2) + WRIST_TO_HAND * Math.cos(phi)
    + tx * Math.cos(phi) + tz * Math.sin(phi);
  const z = SHOULDER_Z + L1 * Math.cos(al) + L2 * Math.sin(th2) - WRIST_TO_HAND * Math.sin(phi)
    - tx * Math.sin(phi) + tz * Math.cos(phi);
  const p = j.A * RAD;
  return [r * Math.cos(p), r * Math.sin(p), z];
}

/** Grasp point (centre between the jaws) in world coordinates for the given pan/lift/elbow/wrist angles (degrees). */
export const graspPoint = (j: { A: number; B: number; C: number; D: number }) => toolPoint(j, GRASP_X, GRASP_Z);

/**
 * Joint angles (degrees) that put the tool point (tx forward along the hand, tz across it) at (x, y, z)
 * with the hand pitched by `pitch` degrees (0 = horizontal, 90 = straight down), elbow up.
 * Returns null when the point is out of reach or needs a joint beyond its limit.
 */
export function solveTool(x: number, y: number, z: number, tx: number, tz: number, pitch: number): Joints | null {
  const pan = Math.atan2(y, x) * DEG;
  const rG = Math.hypot(x, y);
  const phi = pitch * RAD;
  // Wrist joint = tool point minus the tool offsets rotated by the tool pitch.
  const wr = rG - (tx * Math.cos(phi) + tz * Math.sin(phi)) - WRIST_TO_HAND * Math.cos(phi);
  const wz = z - (-tx * Math.sin(phi) + tz * Math.cos(phi)) + WRIST_TO_HAND * Math.sin(phi);
  const dr = wr, dz = wz - SHOULDER_Z;
  const d = Math.hypot(dr, dz);
  if (d > L1 + L2 - 1e-4 || d < Math.abs(L1 - L2) + 1e-4) return null;
  const delta = Math.acos((L1 * L1 + d * d - L2 * L2) / (2 * L1 * d));
  const theta1 = Math.atan2(dz, dr) + delta;       // upper arm direction, elbow up
  const er = L1 * Math.cos(theta1), ez = L1 * Math.sin(theta1);
  const theta2 = Math.atan2(dz - ez, dr - er);     // forearm direction
  const lift = 90 - theta1 * DEG;
  const elbow = -theta2 * DEG - lift;
  const wrist = pitch - lift - elbow;
  const out: Joints = { A: pan, B: lift, C: elbow, D: wrist, E: 0 };
  for (const id of ['A', 'B', 'C', 'D'] as const) {
    const m = limits(id);
    if (out[id] < m.min + 0.5 || out[id] > m.max - 0.5) return null;
  }
  return out;
}

/** Top-down grasp: the hand points straight down with the grasp point at (x, y, z). */
export const solveDown = (x: number, y: number, z: number): Joints | null => solveTool(x, y, z, GRASP_X, GRASP_Z, DOWN_PITCH);
