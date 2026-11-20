// Water sampling job: where things are, in metres, and the named arm poses (OpenPocket #357, plan 307, design from #356 / docs/water-station/README.md).
//
// Frame of this scene: world z up, the cart rides the track along world y. The arm base origin is on the cart, at the cart's origin, pan 0 points along +x (towards the units' lids).
// Every "rel" point below is in that cart/arm frame while the cart stands at its stop; the unit and the station are at fixed world places, so the same arm poses work at every stop.
//
// ASSUMED (the CAD frames differ, see docs/water-station/arm-sample-run.md): the SO-101 stand-in is mounted standing up, 40 mm higher over the lid than the CAD cart, so that it reaches the station roof
// with the hand pointing straight down (the CAD reach check had the station socket at 88 percent of reach, only with a tilted gripper). Distances from the arm: parking socket 157 mm, unit socket 175 mm, station socket ~200 mm.
import { OPEN_DEG, GRASP_Z } from '../arm/dims.ts';
import { solveTool } from '../arm/kinematics.ts';

export type V3 = [number, number, number];
export const f = (n: number) => +n.toFixed(5);

// --- the hydraulics (ASSUMED, to measure on the bench: docs/water-station/README.md)
export const SAMPLE_ML = 70;           // wanted sample: the tube holds about 73 ml (6 mm bore, 2.6 m)
export const TUBE_ML = 73;             // what the coiled tube can hold
export const ML_PER_TURN = 1.0;        // pump: ml per rotor turn, either way. ASSUMED: measure it
export const TURNS_PER_S = 2;          // pump speed
export const HEEL_ML = 91;             // what stays in the sample cup over the standpipe
export const CUP_ML = 190;             // the cup
export const READ_S = 60;              // the pH reading settles for 60 s
export const DEFAULT_INTERVAL_DAYS = 1; // daily by default, adjustable

// --- the nozzle (cad/water_connector.py): collar 13 mm, spigot 14 mm long; the hand holds the collar
export const NOZ_COLLAR_R = 0.0065, NOZ_COLLAR_HL = 0.010;   // collar half length 10 mm
export const NOZ_SPIGOT_R = 0.0022, NOZ_SPIGOT_L = 0.014;
export const NOZ_TIP = NOZ_COLLAR_HL + NOZ_SPIGOT_L;         // 24 mm: nozzle body origin (collar centre) to the tip
export const TOOL_TX = 0.100;                                // tip point along the hand (collar centre at 76 mm)
export const TOOL_TZ = GRASP_Z;
export const PLUG_DEPTH = 0.014;                             // the spigot goes in all the way
export const CLEAR = 0.020;                                  // tip height over the mouth for the "above" poses (6 mm clear of the spigot)
export const PLUG_TOL = 0.0025;                              // m sideways, for "plugged in"
export const AXIS_TOL_DEG = 4;                               // the nozzle must go in straight
export const HOLD_F = 13;                                    // gripper (deg) closed on the collar
export const OPEN_F = OPEN_DEG;

// --- the track stops: where the cart stands (world y)
export const STOPS = { unit: 0, station: 1.0 } as const;
export type Stop = keyof typeof STOPS;
export const CART_SPEED = 0.25;                              // m/s

// --- the sockets, rel to the cart at its stop (mouth centre, all face up)
export const PARK_REL: V3 = [0, 0.157, 0.03];                // parking socket: on a block on the cart deck
export const UNIT_REL: V3 = [0.14, 0.09, -0.06];             // flush in the unit's lid
export const STATION_REL: V3 = [0.20, 0, 0.053];             // flush in the station roof

// --- the unit and the station (rel, same frame)
export const LID_X0 = 0.09, LID_X1 = 0.40, LID_Z = -0.06, LID_T = 0.004, TANK_H = 0.30, UNIT_HY = 0.35;
export const STN_X0 = 0.12, STN_X1 = 0.30, STN_HY = 0.10, STN_ROOF = STATION_REL[2];
export const CUP_X = 0.21, CUP_R = 0.04, CUP_Z0 = -0.03, CUP_H = 0.06;

export const stopY = (s: Stop) => STOPS[s];
export const worldOf = (rel: V3, s: Stop): V3 => [rel[0], rel[1] + STOPS[s], rel[2]];
export const levelZ = (ml: number) => CUP_Z0 + CUP_H * Math.min(1, ml / CUP_ML);

// --- poses (joint angles in degrees by motor id, from inverse kinematics with the hand straight down)
export type PoseName = 'rest' | 'park_above' | 'park_in' | 'unit_above' | 'unit_in' | 'station_above' | 'station_in';
export const POSE_NAMES: readonly PoseName[] = ['rest', 'park_above', 'park_in', 'unit_above', 'unit_in', 'station_above', 'station_in'];
export type Joints6 = Record<'A' | 'B' | 'C' | 'D' | 'E' | 'F', number>;

const tipAt = (mouth: V3, dz: number) => solveTool(mouth[0], mouth[1], mouth[2] + dz, TOOL_TX, TOOL_TZ, 90);
/** Joint angles (A to E) that put the nozzle tip dz over a socket mouth with the nozzle straight down, or null when out of reach. */
export function poseAt(mouth: V3, dz: number) {
  const j = tipAt(mouth, dz);
  return j ? { A: j.A, B: j.B, C: j.C, D: j.D, E: 0 } : null;
}
const need = (name: string, mouth: V3, dz: number) => {
  const j = poseAt(mouth, dz);
  if (!j) throw new Error(`Pose ${name}: out of reach`);
  return j;
};
/** Arm joints A to E of every named pose (the gripper is its own command). */
export const POSES: Record<PoseName, { A: number; B: number; C: number; D: number; E: number }> = {
  rest: { A: 0, B: -52, C: 37.3, D: 14.7, E: 0 },            // folded over the cart deck, hand clear of everything
  park_above: need('park_above', PARK_REL, CLEAR),
  park_in: need('park_in', PARK_REL, -PLUG_DEPTH),
  unit_above: need('unit_above', UNIT_REL, CLEAR),
  unit_in: need('unit_in', UNIT_REL, -PLUG_DEPTH),
  station_above: need('station_above', STATION_REL, CLEAR),
  station_in: need('station_in', STATION_REL, -PLUG_DEPTH),
};
/** Where each pose puts the nozzle tip, rel to the cart: for the reach table in the docs and for the tests. */
export const POSE_TARGETS: Partial<Record<PoseName, { mouth: V3; dz: number }>> = {
  park_above: { mouth: PARK_REL, dz: CLEAR }, park_in: { mouth: PARK_REL, dz: -PLUG_DEPTH },
  unit_above: { mouth: UNIT_REL, dz: CLEAR }, unit_in: { mouth: UNIT_REL, dz: -PLUG_DEPTH },
  station_above: { mouth: STATION_REL, dz: CLEAR }, station_in: { mouth: STATION_REL, dz: -PLUG_DEPTH },
};
