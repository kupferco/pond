// Pod-grab scene layout: a close-up of the bottom of a unit. The cart rides the bottom pipe (along world X),
// the arm stands on a shelf on the cart and reaches into the tank, where a pod store (sloped rows) and the
// 4 x 4 seedling tray (pegs) stand. Pure data and MJCF text, no MuJoCo or DOM. Metres; x along the pipe,
// y away from the pipe into the tank, z up.
//
// A pod is a silicone pot with a hole through it; the hole axis runs along y (towards the arm). The arm carries
// a pin that goes through the hole, hooks the top of the hole and lifts the pod off. In the store the pods lie
// in a channel on a 5 degree slope (low end towards the arm); on the tray the pod slides onto a peg through
// the same hole. ASSUMED sizes (no pod CAD yet): pod 25 mm diameter x 30 mm long, hole 14 mm, 34 mm pitch in a row.
import { PIPE_D_MM, PLATE_MM, SLEEVE_L_MM, SLEEVE_R_MM } from '../cart/track.ts';
import { SHOULDER_Z } from '../arm/kinematics.ts';
import { armMjcf } from '../model.ts';

const m = (mm: number) => mm / 1000;
const f = (n: number) => +n.toFixed(5);

// --- pod, pin, peg
export const POD_R = 0.0125;
export const POD_LEN = 0.03;
export const HOLE_R = 0.007;
export const PIN_R = 0.003;
export const PEG_R = 0.003;
export const PEG_LEN = 0.02;
export const HOOK = HOLE_R - PIN_R;             // 4 mm: pin top touches the hole top, pod centre hangs this far below the pin axis
export const TOOL_X = 0.105;                    // pin axis point along the hand from the hand origin (pod centre when carried)
export const PIN_TIP = POD_LEN / 2 - 0.0005;    // pin tip beyond the pod centre when the pod is on the pin

// --- cart and arm (world)
export const PIPE_Z = 0.42;
export const PIPE_R = m(PIPE_D_MM) / 2;
export const PIPE_X0 = -0.12, PIPE_X1 = 0.9;
export const CART_X_MIN = 0.02, CART_X_MAX = 0.8;
export const CART_HOME_X = 0.2;
export const ARM_Y = 0.10;                      // arm axis, world y
export const ARM_DZ = -0.156;                   // arm base height relative to the pipe (shelf on the cart plate)
export const ARM_BASE_Z = PIPE_Z + ARM_DZ;
export const SHOULDER_WORLD_Z = ARM_BASE_Z + SHOULDER_Z;

// --- pin reach (r = distance from the arm axis along y)
export const R_SEAT = 0.32;                     // pod centre in the store's front position and on a peg
export const R_CLEAR = 0.28;                    // pod carried / pin backed out
export const PIN_SPEED = 0.1, SEAT_SPEED = 0.04, CART_SPEED = 0.25; // m/s

// --- store: rows along y on a slope, one pod at a time leaves position 0
export const STORE_ROWS = 6;
export const STORE_CAP = 5;                     // pod positions per row
export const STORE_START = 4;                   // pods per row at the start
export const STORE_PITCH = 0.034;               // between pods along the slope
export const ROW_PITCH = 0.036;                 // between rows along x
export const ROW_X0 = 0.12;
export const SLOPE = 5 * Math.PI / 180;
export const STORE_Z0 = 0.35;                   // pod centre height at position 0
export const LIP_H = 0.006;                     // front lip above the channel floor
export const rowX = (row: number) => ROW_X0 + row * ROW_PITCH;
export const storePos = (row: number, k: number): [number, number, number] =>
  [rowX(row), ARM_Y + R_SEAT + k * STORE_PITCH * Math.cos(SLOPE), STORE_Z0 + k * STORE_PITCH * Math.sin(SLOPE)];

// --- seedling tray: 4 x 4 pegs on a board, pegs point towards the arm
export const TRAY_COLS = 4, TRAY_ROWS = 4;
export const TRAY_X0 = 0.52, TRAY_COL_PITCH = 0.045;
export const TRAY_Z0 = SHOULDER_WORLD_Z - 1.5 * 0.045, TRAY_ROW_PITCH = 0.045; // peg axis heights
export const BOARD_T = 0.008;
export const BOARD_Y = ARM_Y + R_SEAT + POD_LEN / 2;  // front face of the board = back face of a seated pod
export const trayX = (col: number) => TRAY_X0 + col * TRAY_COL_PITCH;
export const pegZ = (row: number) => TRAY_Z0 + row * TRAY_ROW_PITCH;
/** Seated pod centre: resting on the peg inside the hole, so HOOK above the peg axis. */
export const seatPos = (slot: number): [number, number, number] =>
  [trayX(slot % TRAY_COLS), ARM_Y + R_SEAT, pegZ(Math.floor(slot / TRAY_COLS)) + HOOK];
export const TRAY_SLOTS = TRAY_COLS * TRAY_ROWS;
export const slotLabel = (slot: number) => `${String.fromCharCode(65 + Math.floor(slot / TRAY_COLS))}${(slot % TRAY_COLS) + 1}`;

export const podName = (i: number) => `pod_${i}`;
export const POD_COUNT = STORE_ROWS * STORE_START;
/** Pod i starts at position (i mod START) of row floor(i / START). */
export const startPos = (i: number) => storePos(Math.floor(i / STORE_START), i % STORE_START);

/** Cart-frame position of the arm base (x along the track). */
export const armBasePos = (cartX: number): [number, number, number] => [cartX, ARM_Y, ARM_BASE_Z];

const YAW = Math.PI / 2;
export const YAW_QUAT = [Math.SQRT1_2, 0, 0, Math.SQRT1_2];

const rgba = (r: number, g: number, b: number) => `rgba="${r} ${g} ${b} 1"`;

function cartBody(): string {
  const sr = m(SLEEVE_R_MM), sl = m(SLEEVE_L_MM);
  const { alongTrack, across, t } = PLATE_MM;
  const plateY = sr + m(t) / 2, plateZ = -(m(across) / 2 - 0.05);
  const shelfY = ARM_Y - plateY;
  return `<body name="cart" mocap="true" pos="${CART_HOME_X} 0 ${PIPE_Z}">
      <geom type="cylinder" fromto="${-sl / 2} 0 0 ${sl / 2} 0 0" size="${sr}" ${rgba(0.18, 0.45, 0.35)}/>
      <geom type="box" pos="0 ${f(plateY)} ${f(plateZ)}" size="${m(alongTrack) / 2} ${m(t) / 2} ${m(across) / 2}" ${rgba(0.25, 0.27, 0.3)}/>
      <geom type="box" pos="0 ${f(plateY + shelfY / 2)} ${f(ARM_DZ - 0.004)}" size="0.06 ${f(shelfY / 2 + 0.01)} 0.004" ${rgba(0.9, 0.65, 0.2)}/>
    </body>`;
}

function podMjcf(i: number): string {
  const [x, y, z] = startPos(i);
  return `<body name="${podName(i)}" mocap="true" pos="${f(x)} ${f(y)} ${f(z)}" quat="${YAW_QUAT.map(f).join(' ')}">
      <geom type="cylinder" fromto="${-POD_LEN / 2} 0 0 ${POD_LEN / 2} 0 0" size="${POD_R}" ${rgba(0.93, 0.93, 0.9)}/>
      <geom type="cylinder" fromto="${-POD_LEN / 2 - 0.0002} 0 0 ${POD_LEN / 2 + 0.0002} 0 0" size="${HOLE_R}" ${rgba(0.12, 0.12, 0.14)}/>
    </body>`;
}

/** Store rows: a channel floor on the slope, a front lip, side rails and a roof over every position but the first. */
function storeGeoms(): string[] {
  const out: string[] = [];
  const c = Math.cos(SLOPE), s = Math.sin(SLOPE);
  const along = (row: number, k: number, up: number): string => {
    const [x, y, z] = storePos(row, k);
    return `${f(x)} ${f(y - up * s)} ${f(z + up * c)}`;
  };
  const len = (STORE_CAP + 0.5) * STORE_PITCH;
  const kMid = (STORE_CAP - 1) / 2 + 0.25;
  for (let r = 0; r < STORE_ROWS; r++) {
    const halfW = ROW_PITCH / 2 - 0.002;
    const euler = `${f(SLOPE)} 0 0`;
    out.push(`<geom type="box" pos="${along(r, kMid, -POD_R - 0.002)}" size="${f(halfW)} ${f(len / 2)} 0.002" euler="${euler}" ${rgba(0.35, 0.55, 0.85)}/>`);
    // front lip, just in front of the pod in position 0
    out.push(`<geom type="box" pos="${along(r, -0.5 - 0.03, -POD_R + LIP_H / 2 - 0.002)}" size="${f(halfW)} 0.0015 ${f(LIP_H / 2 + 0.002)}" euler="${euler}" ${rgba(0.35, 0.55, 0.85)}/>`);
    // roof from between positions 0 and 1 to the back, held by two posts
    const rk = (0.5 + STORE_CAP - 0.5) / 2 + 0.1;
    out.push(`<geom type="box" pos="${along(r, rk, POD_R + 0.006)}" size="${f(halfW)} ${f(((STORE_CAP - 1) * STORE_PITCH + 0.03) / 2)} 0.0015" euler="${euler}" ${rgba(0.9, 0.35, 0.25)}/>`);
  }
  // side rails between the rows (one per row boundary)
  for (let r = 0; r <= STORE_ROWS; r++) {
    const x = rowX(0) - ROW_PITCH / 2 + r * ROW_PITCH;
    const [, y, z] = storePos(0, kMid);
    out.push(`<geom type="box" pos="${f(x)} ${f(y - 0.0125 * s)} ${f(z - POD_R * c + 0.012)}" size="0.0015 ${f(len / 2)} 0.014" euler="${f(SLOPE)} 0 0" ${rgba(0.28, 0.45, 0.75)}/>`);
  }
  return out;
}

function trayGeoms(): string[] {
  const out: string[] = [];
  const w = (TRAY_COLS - 1) * TRAY_COL_PITCH / 2 + 0.03, h = (TRAY_ROWS - 1) * TRAY_ROW_PITCH / 2 + 0.03;
  const cx = trayX(0) + (TRAY_COLS - 1) * TRAY_COL_PITCH / 2, cz = pegZ(0) + (TRAY_ROWS - 1) * TRAY_ROW_PITCH / 2;
  out.push(`<geom type="box" pos="${f(cx)} ${f(BOARD_Y + BOARD_T / 2)} ${f(cz)}" size="${f(w)} ${BOARD_T / 2} ${f(h)}" ${rgba(0.15, 0.4, 0.28)}/>`);
  for (let s = 0; s < TRAY_SLOTS; s++) {
    const x = trayX(s % TRAY_COLS), z = pegZ(Math.floor(s / TRAY_COLS));
    out.push(`<geom type="cylinder" fromto="${f(x)} ${f(BOARD_Y)} ${f(z)} ${f(x)} ${f(BOARD_Y - PEG_LEN)} ${f(z)}" size="${PEG_R}" ${rgba(0.85, 0.85, 0.88)}/>`);
  }
  return out;
}

/** MJCF: the arm on its cart, pipe, tank, store, tray and all pods. */
export function podGrabMjcf(): string {
  const tankX0 = 0.05, tankX1 = 0.74, tankY0 = ARM_Y + 0.25, tankY1 = ARM_Y + 0.55;
  const floorZ = STORE_Z0 - 0.06;
  const wall = (x: number, y: number, z: number, sx: number, sy: number, sz: number) =>
    `<geom type="box" pos="${f(x)} ${f(y)} ${f(z)}" size="${f(sx)} ${f(sy)} ${f(sz)}" ${rgba(0.72, 0.8, 0.86)}/>`;
  const tx = (tankX0 + tankX1) / 2, ty = (tankY0 + tankY1) / 2, hx = (tankX1 - tankX0) / 2, hy = (tankY1 - tankY0) / 2;
  const wallH = 0.14;
  const world = [
    `<geom name="floor" type="plane" size="1.2 0.9 0.01" pos="0.4 0.3 0" ${rgba(0.82, 0.86, 0.9)}/>`,
    // bottom pipe on two legs
    `<geom type="cylinder" fromto="${PIPE_X0} 0 ${PIPE_Z} ${PIPE_X1} 0 ${PIPE_Z}" size="${PIPE_R}" ${rgba(0.62, 0.66, 0.7)}/>`,
    `<geom type="box" pos="${PIPE_X0 + 0.02} 0 ${PIPE_Z / 2}" size="0.02 0.02 ${PIPE_Z / 2}" ${rgba(0.5, 0.54, 0.58)}/>`,
    `<geom type="box" pos="${PIPE_X1 - 0.02} 0 ${PIPE_Z / 2}" size="0.02 0.02 ${PIPE_Z / 2}" ${rgba(0.5, 0.54, 0.58)}/>`,
    // tank (open at the front and top so the inside shows), raised on a plinth
    wall(tx, ty, floorZ / 2, hx, hy, floorZ / 2),
    wall(tx, tankY1 - 0.004, floorZ + wallH / 2, hx, 0.004, wallH / 2),
    wall(tankX0 + 0.004, ty, floorZ + wallH / 2, 0.004, hy, wallH / 2),
    wall(tankX1 - 0.004, ty, floorZ + wallH / 2, 0.004, hy, wallH / 2),
    ...storeGeoms(), ...trayGeoms(),
    cartBody(),
    ...Array.from({ length: POD_COUNT }, (_, i) => podMjcf(i)),
  ].join('\n    ');
  const pin = `<geom name="pin" type="cylinder" fromto="0.07 0 0 ${f(TOOL_X + PIN_TIP)} 0 0" size="${PIN_R}" ${rgba(0.95, 0.8, 0.15)}/>`;
  return armMjcf(world, {
    noGround: true,
    baseAttrs: `mocap="true" pos="${CART_HOME_X} ${ARM_Y} ${f(ARM_BASE_Z)}" euler="0 0 ${f(YAW)}"`,
    handExtra: pin,
  });
}
