// The v2 cart's layout numbers (mm), mirrored from cad/cart_dims.py and cad/hand_sleeve.py (Viber #97). The Python file is the source of truth:
// test/sim.test.ts reads cad/cart_dims.py and fails if any number here drifts from it.
// CAD frame, also the transfer scene's world frame: x across (pipes in a row), y out of the pipe plane (the plate is on the -y side), z along the pipes (up).
export const PIPE_SPACING = 120;                 // cart_dims.py PIPE_SPACING: pipe B to pipe C
export const HX = PIPE_SPACING / 2;
export const PIPE_R = 16;                        // hand_sleeve.py R_PIPE
export const SLEEVE_R = 34, SLEEVE_L = 90;       // hand_sleeve.py WALL_OUT_R, SLEEVE_L
export const PAD_X0 = -24, PAD_X1 = 0, PAD_Y0 = -40, PAD_Y1 = -21;
export const HINGE_R = 5, HINGE_LEAF_T = 3, PLATE_T = 6, HINGE_CLEAR = 2;
export const HINGE_OFF_B = PAD_X0 - 6;           // -30: hand B's hinge axis, relative to its pipe
export const HINGE_OFF_C = PAD_X1 + 6;           // +6: hand C's
export const LEAF_Y1 = PAD_Y0 - HINGE_LEAF_T;    // -43
export const HINGE_Y = LEAF_Y1;                  // hinge axis y
export const PLATE_Y1 = LEAF_Y1 - HINGE_LEAF_T, PLATE_Y0 = PLATE_Y1 - PLATE_T;   // plate -46 .. -52
export const PLATE_X0 = -HX + HINGE_OFF_B + HINGE_R + HINGE_CLEAR;   // -83
export const PLATE_X1 = HX + HINGE_OFF_C - HINGE_R - HINGE_CLEAR;    // +59
export const PLATE_ZH = (SLEEVE_L + 22) / 2;     // 56
export const MOTOR_R = 14, MOTOR_L = 55, PART_GAP = 4, END_GAP = 4, ARM_BASE_W = 70;
// Parts on the plate, left to right (x): the hand-B motor, the arm, the hand-C motor.
export const MOTOR_B_X = PLATE_X0 + END_GAP + MOTOR_R;                 // -65
export const ARM_X = MOTOR_B_X + MOTOR_R + PART_GAP + ARM_BASE_W / 2;   // -12
export const MOTOR_C_X = ARM_X + ARM_BASE_W / 2 + PART_GAP + MOTOR_R;   // +41
export const BATT = [70, 50, 70] as const;
export const BATT_Z = PLATE_ZH + 6 + BATT[2] / 2;                       // 97
export const WHEEL_Z = 38, WORM_M = 1, WHEEL_OD = WORM_M * WHEEL_Z + 2 * WORM_M;   // 40
export const WHEEL_Z0 = 62, WHEEL_T = 8, CENTRE_DIST = 24, WORM_ZC = WHEEL_Z0 + WHEEL_T / 2;
export const KNUCKLE_Z = 45, TONGUE_DX0 = 21, TONGUE_W = 30, TONGUE_Z1 = 86;
export const SHOULDER_H = 88, L1 = 120, L2 = 130, L3 = 100;               // cart_arm.py: shoulder height above the arm base plate, link lengths
export const HINGE_RATIO = WHEEL_Z;                                       // 38:1 worm gear
export const MOTOR_RPM = 60;
/** Hinge output speed of the worm drive: 60 rpm / 38, in deg/s (cart_dims.py: 90 deg in about 9.5 s). */
export const HINGE_DEG_S_CAD = (MOTOR_RPM / HINGE_RATIO) * 6;

/** x of the hinge axis of hand 1 (on pipe C, +x) or hand 2 (on pipe B, -x), at rest. */
export const hingeX = (hand: 1 | 2) => (hand === 1 ? HX + HINGE_OFF_C : -HX + HINGE_OFF_B);
/** x of the pipe the hand sits on at rest. */
export const restPipeX = (hand: 1 | 2) => (hand === 1 ? HX : -HX);
/** The pipes of the transfer scene. B and C are the pair the cart hangs on at rest, 120 mm apart. A hand swung half a turn about the OTHER hand's hinge lands where its
 *  own pipe offset from its hinge (30 mm for hand 2) lands on the far side of that hinge: hinge 1 + (hinge 1 - hinge 2) + 30 = 252, so pipe D is 192 mm from C. */
const REACH = hingeX(1) - hingeX(2);   // 156: hinge axis to hinge axis
export const PIPE_X = {
  B: restPipeX(2), C: restPipeX(1),
  D: hingeX(1) + REACH + (restPipeX(2) - hingeX(2)),   // hand 2 swung about hinge 1: +252
} as const;
export type PipeName = keyof typeof PIPE_X;
