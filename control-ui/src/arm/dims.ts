// Dimensions for the Arm scene objects (metres) and version tags written to every logged run.
// No imports here: model.ts (MJCF) and the controller both read these, so this file must stay a leaf.

/** Bump when the MJCF, pod/slot geometry or physics changes, so logged runs stay comparable. */
export const SCENE_VERSION = 'arm-scene-v1';
/** Bump when the scripted controller (IK, phases, speeds, tolerances) changes. */
export const CONTROLLER_VERSION = 'scripted-ik-v1';

// Pod: ASSUMED 25 mm diameter x 40 mm, the pod size used in cad/pod_store.py (no pod CAD model in the repo yet).
export const POD_D = 0.025;
export const POD_H = 0.040;
export const POD_R = POD_D / 2;
export const POD_REST_Z = POD_H / 2; // centre height when standing on the floor

// Slot: one seedling-tray socket. Square 29 mm opening (2 mm play per side around the pod),
// 4 mm walls, base plate 6 mm, walls up to 30 mm. ASSUMED sizes, no tray model in the repo yet.
export const SLOT_OPEN = 0.029;
export const SLOT_WALL = 0.004;
export const SLOT_BASE = 0.006;
export const SLOT_RIM_Z = 0.030;
export const SLOT_SEAT_Z = SLOT_BASE + POD_H / 2; // pod centre height when seated
export const SLOT_PLAY = (SLOT_OPEN - POD_D) / 2; // 2 mm
/** Footprint radius of the slot incl. walls, used to keep pod and slot apart. */
export const SLOT_OUTER = SLOT_OPEN / 2 + SLOT_WALL;

// Gripper (see model.ts): fixed pad plus a jaw hinged at JAW_PIVOT_X, pod centred at GRASP_X.
export const JAW_PIVOT_X = 0.02;
export const PAD_END_X = 0.083;
export const GRASP_X = 0.068;
export const GRASP_Z = 0.0065; // half gap of the fixed pad's inner face to the pod axis
export const WRIST_TO_HAND = 0.03;
/** Jaw angle (deg) at which the jaw faces touch a pod of POD_D. */
export const HOLD_DEG = Math.asin(POD_D / (GRASP_X - JAW_PIVOT_X)) * 180 / Math.PI;
export const OPEN_DEG = 75;

// Where pods and slots may be placed: polar region in front of the base (metres, degrees).
export const REACH = { rMin: 0.12, rMax: 0.20, angMax: 80 };
export const MIN_SEPARATION = 0.065; // pod centre to slot centre
