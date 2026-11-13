// Pod-grab scene layout: a close-up of the bottom of a real Pond unit v3, in the unit frame of cad/unit_v3_dimensioned.py
// and cad/pod_store_reach.py. Metres; x along the bottom track, y front (-) to back (+) of the tank, z up from the floor.
//
// From the CAD (DECIDED unless marked ASSUMED):
//  - tank 700 x 400 x 300 centred on x = 0, y = 0; lid at z = 300; shelf at z = 155 (unit_v3_dimensioned.py)
//  - bottom track pipe at z = ZB = 450 (lid + 150), in the track plane y = -60 (unit_v3_dimensioned.py)
//  - store rows under the lid, row pitch 35, first row at x = -140 (pod_store_reach.py); the rows slope DOWN towards
//    the pick line y = 0, where the pick holes in the lid are; 12 degrees (pod_store_reach.py)
//  - seedling tray 190 x 360 x 35 at x = -245, z 230..265, horizontal, under an access opening in the lid (cart_arm.py, 5)
//  - pod 25 mm diameter, 40 mm tall, 28 mm pitch (pod_store.py ASSUMED)
// ASSUMED here (no CAD yet): pod hole 14 mm and a 6 mm pin; tray 4 x 4 cells at 45 mm pitch with silicone collars;
// silicone collars round the lid pick holes; the arm shelf on the cart plate 100 mm under the track pipe (shoulder about
// 146 mm over the lid, as pod_store_reach.py), 30 mm out from the plate face; the roof and rails of the store;
// the bottom pipe drawn straight and longer than the real straight run so the cart can reach the whole store and tray.
//
// The pods stand upright (hole axis vertical, or square to the store slope in the store). The arm points the pin down
// through the silicone pick hole in the lid and the hole of the first pod, takes the pod up and out, drives along
// the track and lowers it into a silicone collar of the horizontal seedling tray.
import { PIPE_D_MM, PLATE_MM, SLEEVE_L_MM, SLEEVE_R_MM } from '../cart/track.ts';
import { SHOULDER_Z } from '../arm/kinematics.ts';
import { armMjcf } from '../model.ts';

const m = (mm: number) => mm / 1000;
const f = (n: number) => +n.toFixed(5);

// --- pod, pin
export const POD_R = 0.0125;
export const POD_LEN = 0.04;
export const HOLE_R = 0.007;
export const PIN_R = 0.003;
export const TOOL_X = 0.105;                    // pin axis point along the hand from the hand origin (pod centre when carried)
export const PIN_TIP = POD_LEN / 2 - 0.0005;    // pin tip beyond the pod centre when the pod is on the pin

// --- unit
export const TANK_W = 0.7, TANK_D = 0.4, TANK_H = 0.3, SHELF_Z = 0.155;
export const LID_Z = TANK_H, LID_T = 0.004;
export const PIPE_Y = -0.06;                    // the track plane
export const PIPE_Z = TANK_H + 0.15;            // bottom run of the track, 150 mm over the lid
export const PIPE_R = m(PIPE_D_MM) / 2;
export const PIPE_X0 = -0.42, PIPE_X1 = 0.12;
export const CART_X_MIN = -0.33, CART_X_MAX = 0.07;
export const CART_HOME_X = -0.1;
export const ARM_Y = -0.13;                     // arm axis, world y (on the shelf of the cart plate, in front of it)
export const ARM_DZ = -0.10;                    // arm base height relative to the pipe
export const ARM_BASE_Z = PIPE_Z + ARM_DZ;
export const SHOULDER_WORLD_Z = ARM_BASE_Z + SHOULDER_Z;

// --- store: rows along y; the pods slide down the slope to the pick line at y = 0
export const STORE_ROWS = 6;
export const STORE_CAP = 5;                     // pod positions per row
export const STORE_START = 4;                   // pods per row at the start
export const POD_PITCH = POD_R * 2 + 0.0005;    // pods rest against each other on the slope
export const ROW_PITCH = 0.035;
export const ROW_X0 = -0.14 + ROW_PITCH / 2;
export const SLOPE = 12 * Math.PI / 180;
export const STORE_Z0 = 0.22;                   // floor of the channel under position 0
export const LIP_H = 0.012;                     // front stop above the channel floor
export const RAIL_H = POD_LEN + 0.0015;         // side rails and roof underside above the channel floor
export const rowX = (row: number) => ROW_X0 + row * ROW_PITCH;
const sinT = Math.sin(SLOPE), cosT = Math.cos(SLOPE);
/** Slope frame: s up the slope (away from the pick line), h along the channel normal. */
export const slopePoint = (row: number, s: number, h: number): [number, number, number] =>
  [rowX(row), -s * cosT + h * sinT, STORE_Z0 + s * sinT + h * cosT];
export const storePos = (row: number, k: number) => slopePoint(row, k * POD_PITCH, POD_LEN / 2);
/** Position along the slope of a point, in the slope frame of any row. */
export const slopeS = (y: number, z: number) => -y * cosT + (z - STORE_Z0) * sinT;
/** The channel normal (pod axis in the store), in world coordinates. */
export const STORE_N: [number, number, number] = [0, sinT, cosT];
export const STORE_PITCH_DEG = 90 + SLOPE * 180 / Math.PI;      // hand pitch with the pin along -STORE_N

// --- lid pick holes, over position 0 of every row
export const HOLE_HALF = 0.0165;
export const COLLAR_H = 0.008;
export const lidMid = LID_Z - LID_T / 2;
export const pickHoleY = storePos(0, 0)[1] + (lidMid - storePos(0, 0)[2]) * Math.tan(SLOPE);

// --- seedling tray: horizontal, 4 x 4 silicone collars
export const TRAY_COLS = 4, TRAY_ROWS = 4;
export const TRAY_CX = -0.245, TRAY_HX = 0.095, TRAY_HY = 0.18;
export const TRAY_Z0 = 0.23, TRAY_T = 0.035;
export const TRAY_TOP = TRAY_Z0 + TRAY_T;
export const TRAY_COL_PITCH = 0.045, TRAY_ROW_PITCH = 0.045, TRAY_CY = 0.04;
export const CELL_R = 0.016;                    // inner radius of a silicone collar (pod radius 12.5)
export const CELL_H = 0.022;
export const trayX = (col: number) => TRAY_CX + (col - (TRAY_COLS - 1) / 2) * TRAY_COL_PITCH;
export const trayY = (row: number) => TRAY_CY + (row - (TRAY_ROWS - 1) / 2) * TRAY_ROW_PITCH;
/** Pod centre when it stands in a cell. */
export const seatPos = (slot: number): [number, number, number] =>
  [trayX(slot % TRAY_COLS), trayY(Math.floor(slot / TRAY_COLS)), TRAY_TOP + POD_LEN / 2];
export const TRAY_SLOTS = TRAY_COLS * TRAY_ROWS;
export const slotLabel = (slot: number) => `${String.fromCharCode(65 + Math.floor(slot / TRAY_COLS))}${(slot % TRAY_COLS) + 1}`;

export const TRANSIT_Z = 0.37;                  // pin point height while driving with a pod
export const PIN_SPEED = 0.1, SEAT_SPEED = 0.04, CART_SPEED = 0.25; // m/s

export const podName = (i: number) => `pod_${i}`;
export const POD_COUNT = STORE_ROWS * STORE_START;
/** Pod i starts at position (i mod START) of row floor(i / START). */
export const startPos = (i: number) => storePos(Math.floor(i / STORE_START), i % STORE_START);

/** Arm base position for a cart position (x along the track). */
export const armBasePos = (cartX: number): [number, number, number] => [cartX, ARM_Y, ARM_BASE_Z];

export const YAW_QUAT = [Math.SQRT1_2, 0, 0, Math.SQRT1_2];
/** Pod orientation in the store: pod z axis along the channel normal. */
export const STORE_QUAT = [Math.cos(SLOPE / 2), -Math.sin(SLOPE / 2), 0, 0];
export const UPRIGHT_QUAT = [1, 0, 0, 0];

const rgba = (r: number, g: number, b: number, a = 1) => `rgba="${r} ${g} ${b} ${a}"`;
const SOLID = 'contype="1" conaffinity="1"';
const SLICK = `${SOLID} friction="0.05 0.005 0.0001"`;   // store channel: pods slide (MuJoCo takes the larger friction of a pair)
const SILICONE = rgba(0.95, 0.55, 0.2);

function cartBody(): string {
  const sr = m(SLEEVE_R_MM), sl = m(SLEEVE_L_MM);
  const { alongTrack, across, t } = PLATE_MM;
  const plateY = -(sr + m(t) / 2);
  const plateZ = ARM_DZ - 0.03 + m(across) / 2;       // plate bottom 30 mm under the arm base, clear of the lid
  const shelfY = (ARM_Y - plateY) / 2;
  return `<body name="cart" mocap="true" pos="${CART_HOME_X} ${PIPE_Y} ${PIPE_Z}">
      <geom type="cylinder" fromto="${-sl / 2} 0 0 ${sl / 2} 0 0" size="${sr}" ${rgba(0.18, 0.45, 0.35)}/>
      <geom type="box" pos="0 ${f(plateY)} ${f(plateZ)}" size="${m(alongTrack) / 2} ${m(t) / 2} ${m(across) / 2}" ${rgba(0.25, 0.27, 0.3)}/>
      <geom type="box" pos="0 ${f(plateY + shelfY)} ${f(ARM_DZ - 0.004)}" size="0.05 ${f(Math.abs(shelfY) + 0.02)} 0.004" ${rgba(0.9, 0.65, 0.2)}/>
    </body>`;
}

function podMjcf(i: number): string {
  const [x, y, z] = startPos(i);
  const lift = 0.0004;                                 // start just above the floor so the pods do not begin in contact
  const q = STORE_QUAT.map(f).join(' ');
  return `<body name="${podName(i)}" pos="${f(x)} ${f(y + lift * sinT)} ${f(z + lift * cosT)}" quat="${q}">
      <joint type="free" damping="0.002"/>
      <geom type="cylinder" size="${POD_R} ${POD_LEN / 2}" mass="0.012" friction="0.05 0.005 0.0001" ${SOLID} ${rgba(0.93, 0.93, 0.9)}/>
      <geom type="cylinder" size="${HOLE_R} ${POD_LEN / 2 + 0.0002}" ${rgba(0.12, 0.12, 0.14)}/>
    </body>`;
}

/** A box in the slope frame of a row: centre (s, h), half sizes across x, along the slope, along the normal. */
function slopeBox(row: number, s: number, h: number, hx: number, hs: number, hh: number, color: string, extra = SLICK): string {
  const [x, y, z] = slopePoint(row, s, h);
  return `<geom type="box" pos="${f(x)} ${f(y)} ${f(z)}" size="${f(hx)} ${f(hs)} ${f(hh)}" euler="${f(Math.PI - SLOPE)} 0 0" ${extra} ${color}/>`;
}

/** Store rows: channel floor, a front stop, side rails and a roof over every position but the first. */
function storeGeoms(): string[] {
  const out: string[] = [];
  const hw = ROW_PITCH / 2 - 0.0006;
  const sEnd = (STORE_CAP - 0.5) * POD_PITCH + 0.004, sFront = -POD_R - 0.003;
  const blue = rgba(0.35, 0.55, 0.85), red = rgba(0.9, 0.3, 0.25);
  for (let r = 0; r < STORE_ROWS; r++) {
    out.push(slopeBox(r, (sEnd + sFront) / 2, -0.002, hw, (sEnd - sFront) / 2, 0.002, blue));
    out.push(slopeBox(r, -POD_R - 0.0015, LIP_H / 2, hw, 0.0015, LIP_H / 2, blue));
    // the roof: from just behind position 0 to the back end, 1.5 mm over the top of the pods
    const s0 = POD_PITCH / 2;
    out.push(slopeBox(r, (s0 + sEnd) / 2, RAIL_H + 0.001, hw, (sEnd - s0) / 2, 0.001, red));
  }
  for (let r = 0; r <= STORE_ROWS; r++) {
    const x = rowX(0) - ROW_PITCH / 2 + r * ROW_PITCH;
    const [, y, z] = slopePoint(0, (sEnd + sFront) / 2, (RAIL_H + 0.002) / 2);
    out.push(`<geom type="box" pos="${f(x)} ${f(y)} ${f(z)}" size="0.001 ${f((sEnd - sFront) / 2)} ${f((RAIL_H + 0.002) / 2)}" euler="${f(Math.PI - SLOPE)} 0 0" ${SLICK} ${rgba(0.28, 0.45, 0.75)}/>`);
  }
  return out;
}

/** A ring of boxes (a silicone collar) round a vertical axis. */
function ring(cx: number, cy: number, z0: number, rIn: number, thick: number, h: number, color: string, n = 8): string[] {
  const out: string[] = [];
  const half = (rIn + thick) * Math.tan(Math.PI / n) + 0.0005;
  for (let k = 0; k < n; k++) {
    const a = 2 * Math.PI * k / n, rc = rIn + thick / 2;
    out.push(`<geom type="box" pos="${f(cx + rc * Math.cos(a))} ${f(cy + rc * Math.sin(a))} ${f(z0 + h / 2)}" size="${f(half)} ${f(thick / 2)} ${f(h / 2)}" euler="0 0 ${f(a + Math.PI / 2)}" ${SOLID} ${color}/>`);
  }
  return out;
}

/** The lid over the store: a plate with a pick hole over position 0 of each row, each with a silicone collar. */
function lidGeoms(): string[] {
  const out: string[] = [];
  const grey = rgba(0.6, 0.62, 0.66, 0.55);
  const x0 = TRAY_CX + TRAY_HX + 0.005, x1 = TANK_W / 2, y0 = -TANK_D / 2, y1 = TANK_D / 2;
  const plate = (xa: number, xb: number, ya: number, yb: number) => out.push(
    `<geom type="box" pos="${f((xa + xb) / 2)} ${f((ya + yb) / 2)} ${f(lidMid)}" size="${f((xb - xa) / 2)} ${f((yb - ya) / 2)} ${LID_T / 2}" ${SOLID} ${grey}/>`);
  plate(x0, x1, y0, pickHoleY - HOLE_HALF);
  plate(x0, x1, pickHoleY + HOLE_HALF, y1);
  plate(x0, rowX(0) - HOLE_HALF, pickHoleY - HOLE_HALF, pickHoleY + HOLE_HALF);
  for (let r = 0; r < STORE_ROWS; r++) plate(rowX(r) + HOLE_HALF, r + 1 < STORE_ROWS ? rowX(r + 1) - HOLE_HALF : x1, pickHoleY - HOLE_HALF, pickHoleY + HOLE_HALF);
  for (let r = 0; r < STORE_ROWS; r++) out.push(...ring(rowX(r), pickHoleY, LID_Z, 0.0155, 0.0015, COLLAR_H, SILICONE));
  return out;
}

function trayGeoms(): string[] {
  const out: string[] = [];
  out.push(`<geom type="box" pos="${TRAY_CX} 0 ${f(TRAY_Z0 + TRAY_T / 2)}" size="${TRAY_HX} ${TRAY_HY} ${TRAY_T / 2}" ${SOLID} ${rgba(0.2, 0.62, 0.38)}/>`);
  for (let s = 0; s < TRAY_SLOTS; s++) {
    const [x, y] = seatPos(s);
    out.push(...ring(x, y, TRAY_TOP, CELL_R, 0.002, CELL_H, SILICONE));
  }
  return out;
}

/** MJCF: the arm on its cart, the track, the tank with lid, store and tray, and all pods. */
export function podGrabMjcf(): string {
  const wall = (x: number, y: number, z: number, sx: number, sy: number, sz: number, a = 0.22) =>
    `<geom type="box" pos="${f(x)} ${f(y)} ${f(z)}" size="${f(sx)} ${f(sy)} ${f(sz)}" ${rgba(0.72, 0.8, 0.86, a)}/>`;
  const hx = TANK_W / 2, hy = TANK_D / 2, t = 0.004;
  const world = [
    `<geom name="floor" type="plane" size="1.2 0.9 0.01" pos="0 0 0" ${SOLID} ${rgba(0.82, 0.86, 0.9)}/>`,
    // the bottom track pipe: floating in the track plane, no supports
    `<geom type="cylinder" fromto="${PIPE_X0} ${PIPE_Y} ${PIPE_Z} ${PIPE_X1} ${PIPE_Y} ${PIPE_Z}" size="${PIPE_R}" ${rgba(0.62, 0.66, 0.7)}/>`,
    // tank: floor, four walls, the shelf at 155 mm
    wall(0, 0, t / 2, hx, hy, t / 2, 0.5),
    wall(0, -hy + t / 2, TANK_H / 2, hx, t / 2, TANK_H / 2),
    wall(0, hy - t / 2, TANK_H / 2, hx, t / 2, TANK_H / 2),
    wall(-hx + t / 2, 0, TANK_H / 2, t / 2, hy, TANK_H / 2),
    wall(hx - t / 2, 0, TANK_H / 2, t / 2, hy, TANK_H / 2),
    wall(0, 0, SHELF_Z, hx - t, hy - t, t / 2, 0.45),
    ...lidGeoms(), ...storeGeoms(), ...trayGeoms(),
    cartBody(),
    ...Array.from({ length: POD_COUNT }, (_, i) => podMjcf(i)),
  ].join('\n    ');
  const pin = `<geom name="pin" type="cylinder" fromto="0.07 0 0 ${f(TOOL_X + PIN_TIP)} 0 0" size="${PIN_R}" ${rgba(0.95, 0.8, 0.15)}/>`;
  return armMjcf(world, {
    noGround: true,
    baseAttrs: `mocap="true" pos="${CART_HOME_X} ${ARM_Y} ${f(ARM_BASE_Z)}" euler="0 0 ${f(Math.PI / 2)}"`,
    handExtra: pin,
  });
}
