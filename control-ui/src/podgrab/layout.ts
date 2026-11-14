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
//  - spine: 33.7 mm tube on the tank centre x = 0, y = 0 (unit_v3_dimensioned.py); track bracket 16 x 30 x 30 on the spine
//    side of the bottom pipe, y = -45 (unit_v3_dimensioned.py)
//  - arm on the cart (cart_arm.py, drawing 5): the plate is on the side of the pipe AWAY from the spine (here the front, -y),
//    the SO-101 base is on the plate centre at pipe height (the drawing puts the shoulder about 146 mm over the lid, which is
//    the height of the bottom pipe), its base axis points out of the plate, so the arm works in the vertical plane across the
//    track and the cart does the x motion.
// ASSUMED here (no CAD yet): pod hole 14 mm (pods are gripped from outside by a two-finger claw); tray 4 x 4 cells at 45 mm pitch with silicone collars, in the
// front half of the tray so that the arm reaches them; silicone collars round the lid pick holes; the roof and rails of the
// store; the store placed right of the spine (x >= 50 mm), pick line at the front (y = -145 mm, the arm side), rows rising to the back; the tray and store brackets (flat bars from clamp collars on the spine, 4 mm thick); the spine drawn only
// up to 0.78 m; the bottom pipe drawn straight and longer than the real straight run so the cart can reach the whole store
// and tray; the cart does not collide with the track bracket (the real hands have a gap for it).
//
// The pods stand upright (hole axis vertical, or square to the store slope in the store). The arm points the claw down
// through the silicone pick hole in the lid, closes it on the first pod, takes the pod up and out, drives along
// the track and lowers it into a silicone collar of the horizontal seedling tray.
import { PIPE_D_MM, PLATE_MM, SLEEVE_L_MM, SLEEVE_R_MM } from '../cart/track.ts';
import { armMjcf } from '../model.ts';

const m = (mm: number) => mm / 1000;
const f = (n: number) => +n.toFixed(5);

// --- pod, pin
export const POD_R = 0.0125;
export const POD_LEN = 0.04;
export const HOLE_R = 0.007;
// claw gripper (replaces the pin): two flat fingers either side of the pod, along the hand, closing across the hand y axis (world x
// in the working pose). ASSUMED dimensions: fingers 1.25 mm thick, 12 mm wide, open inner gap 28.6 mm (pod 25), outer 31.1 mm, which passes the 34 mm pick holes.
export const TOOL_X = 0.130;                    // pod centre along the hand from the hand origin when carried
export const CLAW_BASE = 0.07;                  // palm: where the fingers start along the hand
export const CLAW_TIP = TOOL_X + 0.001;         // fingertips: the claw grips the upper half of the pod, so the guide walls of the store channel stay below it
export const CLAW_T = 0.00125, CLAW_W = 0.012;
export const CLAW_OPEN = 0.0143;                // open: half inner gap
export const CLAW_GRIP = CLAW_OPEN - POD_R;     // finger travel from open to touching the pod (1.5 mm)
export const CLAW_ACT = ['claw_l', 'claw_r'];

// --- unit
export const TANK_W = 0.7, TANK_D = 0.4, TANK_H = 0.3, SHELF_Z = 0.155, SHELF_T = 0.004;   // shelf slab z 155..159 (unit_v3_dimensioned.py)
export const SHELF_TOP = SHELF_Z + SHELF_T;
export const LID_Z = TANK_H, LID_T = 0.004;
export const PIPE_Y = 0.015;                    // the track plane. CAD: -60 mm. MOVED 90 mm towards the back so that all 16 sockets are in front of the cart plate and the arm, mounted flat on that plate, reaches them (ASSUMED, see the PR)
export const PIPE_Z = TANK_H + 0.22;            // bottom run of the track, 220 mm over the lid (CAD: 150): raised 70 mm so that the arm on the cart plate reaches the pods in the store and lifts them clear of the lid (ASSUMED, see the PR)
export const PIPE_R = m(PIPE_D_MM) / 2;
export const PIPE_X0 = -0.40, PIPE_X1 = 0.42;
export const CART_X_MIN = -0.33, CART_X_MAX = 0.28;   // arm plane; hand 1 is HAND_DX further along the pipe
export const CART_HOME_X = -0.1;
// spine and brackets
export const SPINE_R = 0.070 / 2, SPINE_TOP = 0.86;   // 70 mm: more than double the 33.7 mm tube of unit_v3_dimensioned.py (follow-up request)
export const SPINE_Y = PIPE_Y + 0.075;          // the spine stays 75 mm behind the track, as before
export const BRACKET_T = 0.004;
export const ROD_R = 0.004;                     // M8 rod (track_joint.py)
export const SHELF_CAP_T = 0.004, SHELF_CAP_H = 0.03;   // ASSUMED shelf end caps
// cart (drawings 1, 2, 4 and 5, placeholders marked). The cart body (mocap) sits on the pipe at the ARM plane: cart x = arm x.
//  - hand 1 (wheel set 1) rides the pipe, HAND_DX along the track from the arm plane (so the arm's forearm does not cross the hand)
//  - the cart base is the plate (drawing 2) on the front (-y) of the hands: its top edge is the top of hand 1, its bottom edge the bottom
//    of hand 2, nothing protrudes along the track beyond the hand length (112 mm)
//  - hand 2 (wheel set 2) dangles straight below hand 1, 100 mm lower, ending just over the tank top
//  - the arm base is bolted flat on the front face of the plate (same vertical plane as the track plane), its axis along the plate
//    normal (out of the plate, -y), pan 0 pointing down the plate; the arm works in the vertical plane through the plate centre
export const HAND_L = m(SLEEVE_L_MM), HAND_R = m(SLEEVE_R_MM), HAND_RIN = 0.022;
export const SLOT_SEG = 0;                      // hand ring: 20 segments of 18 degrees, the one at 0 degrees (+y, towards the spine) left out for the rod
export const SLOT_W = 2 * HAND_R * Math.sin(Math.PI / 20) * 0.98;   // width of that gap at the ring: ~11 mm
export const HAND_DX = 0;                       // hand 1 and the plate are centred on the arm base (the arm base sits on the middle of the cart base)
export const HAND2_DZ = 0.10;                   // ASSUMED: wheel set 2 axis below the pipe (drawing: 280 mm, but that would be inside the tank); its underside stays 14 mm over the lid
export const PLATE_T = 0.006, PLATE_Y = -HAND_R - PLATE_T / 2;       // cart base plate on the front of the hands
export const PLATE_FACE_Y = -HAND_R - PLATE_T;  // cart frame y of the plate's front face, the plane the arm base is bolted to
export const BASE_BOTTOM = 0.0085;               // the base servo's underside, in base coordinates (arm model: servo1 spans z 8.5..43.5 mm)
export const ARM_CZ = 0.01;                      // cart frame z of the arm base origin: the base servo (45 mm along base x) sits on the upper part of the plate, the plate top is at +36 mm
export const ARM_Y = PIPE_Y + PLATE_FACE_Y + BASE_BOTTOM;   // arm base origin, world y: its underside (base z = 8.5 mm) is on the plate face, the arm axis (base z) is the plate normal, pointing out of the plate (-y)
export const ARM_BASE_Z = PIPE_Z + ARM_CZ - 0.004;   // IK reference: the pick/place paths are planned with the points 4 mm above the real ones, so the claw runs a few mm high over the store walls (arm sag)
export const BASE_XYAXES = '0 0 -1 1 0 0';       // base x = world down (pan 0 points down the plate), base y = +x along the track, base z = base x cross base y = -y: out of the plate
export const PAN0 = 0;                          // pan angle (deg): the arm works in the vertical plane through the plate centre, pointing down the plate
/** Arm planar IK frame: r = distance down from the base axis (the arm's "forward", base x), u = distance out of the plate along the base axis (base z, the plate normal). */
export const armR = (z: number) => ARM_BASE_Z - z;
export const armU = (y: number) => ARM_Y - y;

// --- store: rows along y; the pods slide down the slope to the pick line at y = 0
export const STORE_ROWS = 6;
export const STORE_CAP = 13;                     // pod positions per row: the channels run all the way to the back wall of the tank (end stop at y = 183 mm)
export const STORE_START = 10;                  // pods per row at the start
export const POD_PITCH = POD_R * 2 + 0.0005;    // pods rest against each other on the slope
export const ROW_PITCH = 0.035;
export const ROW_X0 = 0.07 + ROW_PITCH / 2;
export const SLOPE = 12 * Math.PI / 180;
export const STORE_Z0 = 0.205;                  // floor of the channel under position 0 (the store stands on legs on the shelf, under the lid)
export const STORE_Y0 = -0.145;                 // y of the channel under position 0 (the pick line)
export const LOAD_CLEAR = 0.5;                  // clear floor needed behind the unit to load the store from the back
export const LIP_H = 0.018;                     // front stop above the channel floor
export const GUIDE_H = 0.017;                   // low guide walls between the rows: the pod stands within 0.5 mm of the row centre, below the fingertips
export const GUIDE_HALF = ROW_PITCH / 2 - (POD_R + 0.0005);   // half thickness of a guide wall on a row boundary
export const RAIL_H = POD_LEN + 0.0015;         // side rails and roof underside above the channel floor
export const rowX = (row: number) => ROW_X0 + row * ROW_PITCH;
const sinT = Math.sin(SLOPE), cosT = Math.cos(SLOPE);
/** Slope frame: s up the slope (away from the pick line, towards the back), h along the channel normal. */
export const slopePoint = (row: number, s: number, h: number): [number, number, number] =>
  [rowX(row), STORE_Y0 + s * cosT - h * sinT, STORE_Z0 + s * sinT + h * cosT];
export const storePos = (row: number, k: number) => slopePoint(row, k * POD_PITCH, POD_LEN / 2);
/** Position along the slope of a point, in the slope frame of any row. */
export const slopeS = (y: number, z: number) => (y - STORE_Y0) * cosT + (z - STORE_Z0) * sinT;
/** The channel normal (pod axis in the store), in world coordinates. */
export const STORE_N: [number, number, number] = [0, -sinT, cosT];
export const STORE_PITCH_DEG = SLOPE * 180 / Math.PI;      // hand pitch (0 = pin straight down) with the pin along -STORE_N

// --- lid pick holes, over position 0 of every row
export const HOLE_HALF = 0.017;
export const COLLAR_H = 0.004;
export const lidMid = LID_Z - LID_T / 2;
export const pickHoleY = storePos(0, 0)[1] - (lidMid - storePos(0, 0)[2]) * Math.tan(SLOPE);

// --- seedling tray: horizontal, 4 x 4 silicone collars
export const TRAY_COLS = 4, TRAY_ROWS = 4;
export const TRAY_CX = -0.24, TRAY_HX = 0.095, TRAY_HY = 0.185;
export const TRAY_Z0 = SHELF_TOP, TRAY_T = 0.004;   // a thin flat tray lying on the shelf (the thick green block under it is gone)
export const TRAY_TOP = TRAY_Z0 + TRAY_T;
export const TRAY_COL_PITCH = 0.045, TRAY_ROW_PITCH = 0.038, TRAY_CY = -0.083;
export const CELL_R = 0.016;                    // inner radius of a silicone collar (pod radius 12.5)
export const CELL_H = 0.016;
// lid over the seedling tray: a plate just above the collars of the cells, a silicone collar round each hole (same as the tank-top lid)
export const TLID_T = 0.004;
export const TLID_Z = TRAY_TOP + CELL_H + 0.001 + TLID_T / 2;   // plate centre
export const TLID_TOP = TLID_Z + TLID_T / 2;
export const TCOLLAR_H = COLLAR_H;               // the same silicone enclosure as the tank-top lid
export const trayX = (col: number) => TRAY_CX + (col - (TRAY_COLS - 1) / 2) * TRAY_COL_PITCH;
export const trayY = (row: number) => TRAY_CY + (row - (TRAY_ROWS - 1) / 2) * TRAY_ROW_PITCH;
/** Pod centre when it stands in a cell. */
export const seatPos = (slot: number): [number, number, number] =>
  [trayX(slot % TRAY_COLS), trayY(Math.floor(slot / TRAY_COLS)), TRAY_TOP + POD_LEN / 2];
export const TRAY_SLOTS = TRAY_COLS * TRAY_ROWS;
export const slotLabel = (slot: number) => `${String.fromCharCode(65 + Math.floor(slot / TRAY_COLS))}${(slot % TRAY_COLS) + 1}`;

/** Ready pose of the arm (deg): claw straight down, pod point 200 mm down the plate from the arm base and 200 mm out of it (an IK pose, so cartesian moves start on the right branch): in front of the tank, over the lid. */
export const READY_POSE: Record<string, number> = { A: PAN0, B: -52, C: 37.3, D: 14.7, E: 0, F: 0 };
export const TRANSIT_Z = 0.35;                  // pin point height while driving with a pod
export const PIN_SPEED = 0.1, SEAT_SPEED = 0.04, CART_SPEED = 0.25; // m/s

export const podName = (i: number) => `pod_${i}`;
export const POD_COUNT = STORE_ROWS * STORE_START;
/** Pod i starts at position (i mod START) of row floor(i / START). */
export const startPos = (i: number) => storePos(Math.floor(i / STORE_START), i % STORE_START);

/** Pod orientation in the store: pod z axis along the channel normal. */
export const STORE_QUAT = [Math.cos(SLOPE / 2), Math.sin(SLOPE / 2), 0, 0];
export const UPRIGHT_QUAT = [1, 0, 0, 0];

const rgba = (r: number, g: number, b: number, a = 1) => `rgba="${r} ${g} ${b} ${a}"`;
const SOLID = 'contype="1" conaffinity="1"';
// fixed unit parts: pods collide with them (bit 1) and so does the arm (bit 2)
const OBST = 'contype="1" conaffinity="3"';
const SLICK = `${OBST} friction="0.05 0.005 0.0001"`;   // store channel: pods slide (MuJoCo takes the larger friction of a pair)
const SILICONE = rgba(0.95, 0.55, 0.2);
// silicone collars are soft: pods collide with them, the arm (claw fingers) just brushes past
const SOFT = 'contype="1" conaffinity="1"';

/** A ring of boxes round the x axis (a hand sleeve): inner radius ri, outer ro, length len, segment k = skip left out (the C-gap). */
function handRing(cx: number, cy: number, cz: number, skip: number | null, color: string): string[] {
  const out: string[] = [];
  const n = 20, rc = (HAND_R + HAND_RIN) / 2, th = (HAND_R - HAND_RIN) / 2;
  for (let k = 0; k < n; k++) {
    if (k === skip) continue;
    const a = 2 * Math.PI * k / n;                      // angle from +y round the x axis
    const half = HAND_R * Math.tan(Math.PI / n);
    out.push(`<geom type="box" pos="${f(cx)} ${f(cy + rc * Math.cos(a))} ${f(cz + rc * Math.sin(a))}" size="${f(HAND_L / 2)} ${f(th)} ${f(half)}" euler="${f(a)} 0 0" ${color}/>`);
  }
  return out;
}

/** The cart (a mocap body at the pipe) with the arm base as a rigid child.
 *  Hand 1 (wheel set 1) rides the pipe, C-gap towards the spine so it passes the track rod. The cart base is a flat plate on top of
 *  hand 1, its top at the arm base. A hanger plate drops from the front edge of the base to hand 2 (wheel set 2), which dangles
 *  100 mm below the pipe, ending just over the tank top. The arm base (the arm's own first body, no second base) sits flat on the front face of the cart base, its axis out of the plate. */
function cartMount(): { open: string; close: string; baseAttrs: string } {
  const steel = rgba(0.25, 0.27, 0.3), green = rgba(0.18, 0.45, 0.35);
  const zTop = HAND_R, zBot = -HAND2_DZ - HAND_R;                      // plate: top of hand 1 to bottom of hand 2
  const px0 = HAND_DX - 0.056, px1 = HAND_DX + 0.056;
  const open = `<body name="cart" mocap="true" pos="${CART_HOME_X} ${PIPE_Y} ${PIPE_Z}">
      ${handRing(HAND_DX, 0, 0, SLOT_SEG, green).join('\n      ')}
      ${handRing(HAND_DX, 0, -HAND2_DZ, null, green).join('\n      ')}
      <geom type="box" pos="${f((px0 + px1) / 2)} ${f(PLATE_Y)} ${f((zTop + zBot) / 2)}" size="${f((px1 - px0) / 2)} ${PLATE_T / 2} ${f((zTop - zBot) / 2)}" ${steel}/>`;
  // no joint and no extra base: the arm's own base body is a fixed child of the cart, its underside flat on the plate face
  const baseAttrs = `pos="0 ${f(PLATE_FACE_Y + BASE_BOTTOM)} ${f(ARM_CZ)}" xyaxes="${BASE_XYAXES}"`;
  return { open, close: '</body>', baseAttrs };
}

/** The spine, the track bracket with its rod, the shelf brackets and the shelf with its end caps. */
function spineGeoms(): string[] {
  const out: string[] = [];
  const dark = rgba(0.35, 0.35, 0.38), brk = rgba(0.2, 0.2, 0.22), shelf = rgba(0.5, 0.52, 0.58);
  out.push(`<geom type="cylinder" fromto="0 ${SPINE_Y} ${f(SHELF_Z - 0.03)} 0 ${SPINE_Y} ${SPINE_TOP}" size="${SPINE_R}" ${OBST} ${dark}/>`);
  const box = (x0: number, x1: number, y0: number, y1: number, z0: number, z1: number, c = brk) =>
    out.push(`<geom type="box" pos="${f((x0 + x1) / 2)} ${f((y0 + y1) / 2)} ${f((z0 + z1) / 2)}" size="${f((x1 - x0) / 2)} ${f((y1 - y0) / 2)} ${f((z1 - z0) / 2)}" ${OBST} ${c}/>`);
  const collar = (z0: number, z1: number) => out.push(`<geom type="cylinder" fromto="0 ${SPINE_Y} ${f(z0)} 0 ${SPINE_Y} ${f(z1)}" size="${f(SPINE_R + 0.005)}" ${OBST} ${brk}/>`);
  // Pillar-to-track bracket (unit_v3_dimensioned.py: 16 x 30 x 30 on the spine side of the pipe): a plate on the spine and an M8 rod
  // (track_joint.py) from it to a clamp ring on the pipe. The hands have a C-gap facing the spine, so the cart passes it.
  const yPlate = PIPE_Y + HAND_R + 0.0005;                      // the plate stays outside the hand ring (radius 36 mm)
  box(-0.008, 0.008, yPlate, SPINE_Y - SPINE_R - 0.001, PIPE_Z - 0.015, PIPE_Z + 0.015);
  out.push(`<geom type="cylinder" fromto="0 ${f(yPlate)} ${PIPE_Z} 0 ${f(PIPE_Y + PIPE_R)} ${PIPE_Z}" size="${ROD_R}" ${OBST} ${rgba(0.75, 0.75, 0.78)}/>`);
  out.push(`<geom type="cylinder" fromto="-0.01 ${PIPE_Y} ${PIPE_Z} 0.01 ${PIPE_Y} ${PIPE_Z}" size="${f(PIPE_R + 0.0015)}" ${OBST} ${brk}/>`);
  // Shelf brackets: a collar on the spine and a flat bar under the shelf to each side, up to the edge of the tray / the store.
  collar(SHELF_Z - 0.014, SHELF_Z - 0.002);
  box(TRAY_CX + TRAY_HX - 0.02, -SPINE_R - 0.005, SPINE_Y - 0.01, SPINE_Y + 0.01, SHELF_Z - BRACKET_T, SHELF_Z);
  box(SPINE_R + 0.005, rowX(STORE_ROWS - 1) + ROW_PITCH / 2 - 0.02, SPINE_Y - 0.01, SPINE_Y + 0.01, SHELF_Z - BRACKET_T, SHELF_Z);
  // The shelf (unit_v3_dimensioned.py: slab 4 mm at z 155) and its end caps: 4 mm plates at the two ends, 30 mm high.
  const hx = TANK_W / 2 - 0.004, hy = TANK_D / 2 - 0.004;
  box(-hx, hx, -hy, hy, SHELF_Z, SHELF_TOP, shelf);
  for (const sx of [-1, 1]) box(sx > 0 ? hx - SHELF_CAP_T : -hx, sx > 0 ? hx : -hx + SHELF_CAP_T, -hy, hy, SHELF_TOP, SHELF_TOP + SHELF_CAP_H, rgba(0.42, 0.44, 0.5));
  // Store legs: cross bars from the shelf up to the channel floor at the front and back ends.
  for (const s of [-POD_R - 0.003, (STORE_CAP - 0.5) * POD_PITCH + 0.004]) {
    const [, y, z] = slopePoint(0, s, -0.004);
    box(rowX(0) - ROW_PITCH / 2, rowX(STORE_ROWS - 1) + ROW_PITCH / 2, y - 0.004, y + 0.004, SHELF_TOP, z, brk);
  }
  return out;
}

function podMjcf(i: number): string {
  const [x, y, z] = startPos(i);
  const lift = 0.0004;                                 // start just above the floor so the pods do not begin in contact
  const q = STORE_QUAT.map(f).join(' ');
  return `<body name="${podName(i)}" pos="${f(x)} ${f(y - lift * sinT)} ${f(z + lift * cosT)}" quat="${q}">
      <joint type="free" damping="0.002"/>
      <geom type="cylinder" size="${POD_R} ${POD_LEN / 2}" mass="0.012" friction="0.05 0.005 0.0001" ${SOLID} ${rgba(0.93, 0.93, 0.9)}/>
      <geom type="cylinder" size="${HOLE_R} ${POD_LEN / 2 + 0.0002}" contype="0" conaffinity="0" ${rgba(0.12, 0.12, 0.14)}/>
    </body>`;
}

/** A box in the slope frame of a row: centre (s, h), half sizes across x, along the slope, along the normal. */
function slopeBox(row: number, s: number, h: number, hx: number, hs: number, hh: number, color: string, extra = SLICK): string {
  const [x, y, z] = slopePoint(row, s, h);
  return `<geom type="box" pos="${f(x)} ${f(y)} ${f(z)}" size="${f(hx)} ${f(hs)} ${f(hh)}" euler="${f(SLOPE)} 0 0" ${extra} ${color}/>`;
}

/** Store rows: channel floor, a front stop, side rails and a roof over every position but the first. */
function storeGeoms(): string[] {
  const out: string[] = [];
  const hw = ROW_PITCH / 2 - 0.0006;
  const sEnd = (STORE_CAP - 0.5) * POD_PITCH + 0.004, sFront = -POD_R - 0.003;
  const blue = rgba(0.35, 0.55, 0.85), red = rgba(0.9, 0.3, 0.25), amber = rgba(0.95, 0.75, 0.2);
  for (let r = 0; r < STORE_ROWS; r++) {
    out.push(slopeBox(r, (sEnd + sFront) / 2, -0.002, hw, (sEnd - sFront) / 2, 0.002, blue));
    out.push(slopeBox(r, -POD_R - 0.0015, LIP_H / 2, hw, 0.0015, LIP_H / 2, blue));
    // the back end: a full-height end gate under the roof, so no pod can roll off the end of the row (the gate is taken out to load the row from behind)
    out.push(slopeBox(r, sEnd + 0.002, (RAIL_H + 0.004) / 2, hw, 0.002, (RAIL_H + 0.004) / 2, amber));
    // the roof: from just behind position 0 to the back end, 1.5 mm over the top of the pods
    const s0 = POD_PITCH / 2;
    out.push(slopeBox(r, (s0 + sEnd) / 2, RAIL_H + 0.001, hw, (sEnd - s0) / 2, 0.001, red));
  }
  for (let r = 0; r <= STORE_ROWS; r++) {
    const x = rowX(0) - ROW_PITCH / 2 + r * ROW_PITCH;
    const [, gy, gz] = slopePoint(0, (sEnd + sFront) / 2, GUIDE_H / 2);
    out.push(`<geom type="box" pos="${f(x)} ${f(gy)} ${f(gz)}" size="${f(GUIDE_HALF)} ${f((sEnd - sFront) / 2)} ${f(GUIDE_H / 2)}" euler="${f(SLOPE)} 0 0" ${SLICK} ${rgba(0.28, 0.45, 0.75)}/>`);
    const [, y, z] = slopePoint(0, (sEnd + sFront) / 2, (RAIL_H + 0.002) / 2);
    out.push(`<geom type="box" pos="${f(x)} ${f(y)} ${f(z)}" size="0.001 ${f((sEnd - sFront) / 2)} ${f((RAIL_H + 0.002) / 2)}" euler="${f(SLOPE)} 0 0" ${SLICK} ${rgba(0.28, 0.45, 0.75)}/>`);
  }
  return out;
}

/** A ring of boxes (a silicone collar) round a vertical axis. */
function ring(cx: number, cy: number, z0: number, rIn: number, thick: number, h: number, color: string, n = 8): string[] {
  const out: string[] = [];
  const half = (rIn + thick) * Math.tan(Math.PI / n) + 0.0005;
  for (let k = 0; k < n; k++) {
    const a = 2 * Math.PI * k / n, rc = rIn + thick / 2;
    out.push(`<geom type="box" pos="${f(cx + rc * Math.cos(a))} ${f(cy + rc * Math.sin(a))} ${f(z0 + h / 2)}" size="${f(half)} ${f(thick / 2)} ${f(h / 2)}" euler="0 0 ${f(a + Math.PI / 2)}" ${SOFT} ${color}/>`);
  }
  return out;
}

/** The lid over the store: a plate with a pick hole over position 0 of each row, each with a silicone collar. */
function lidGeoms(): string[] {
  const out: string[] = [];
  const grey = rgba(0.6, 0.62, 0.66, 0.55);
  const x0 = TRAY_CX + TRAY_HX + 0.005, x1 = TANK_W / 2, y0 = -TANK_D / 2, y1 = TANK_D / 2;
  const plate = (xa: number, xb: number, ya: number, yb: number) => out.push(
    `<geom type="box" pos="${f((xa + xb) / 2)} ${f((ya + yb) / 2)} ${f(lidMid)}" size="${f((xb - xa) / 2)} ${f((yb - ya) / 2)} ${LID_T / 2}" ${OBST} ${grey}/>`);
  plate(x0, x1, y0, pickHoleY - HOLE_HALF);
  plate(x0, x1, pickHoleY + HOLE_HALF, y1);
  plate(x0, rowX(0) - HOLE_HALF, pickHoleY - HOLE_HALF, pickHoleY + HOLE_HALF);
  for (let r = 0; r < STORE_ROWS; r++) plate(rowX(r) + HOLE_HALF, r + 1 < STORE_ROWS ? rowX(r + 1) - HOLE_HALF : x1, pickHoleY - HOLE_HALF, pickHoleY + HOLE_HALF);
  for (let r = 0; r < STORE_ROWS; r++) out.push(...ring(rowX(r), pickHoleY, LID_Z, 0.0155, 0.0015, COLLAR_H, SILICONE));
  return out;
}

function trayGeoms(): string[] {
  const out: string[] = [];
  const box = (xa: number, xb: number, ya: number, yb: number, zc: number, t: number, c: string) => xb - xa > 1e-4 && yb - ya > 1e-4 && out.push(
    `<geom type="box" pos="${f((xa + xb) / 2)} ${f((ya + yb) / 2)} ${f(zc)}" size="${f((xb - xa) / 2)} ${f((yb - ya) / 2)} ${f(t / 2)}" ${OBST} ${c}/>`);
  // the flat tray lies on the shelf
  box(TRAY_CX - TRAY_HX, TRAY_CX + TRAY_HX, -TRAY_HY, TRAY_HY, TRAY_Z0 + TRAY_T / 2, TRAY_T, rgba(0.2, 0.62, 0.38));
  for (let s = 0; s < TRAY_SLOTS; s++) {
    const [x, y] = seatPos(s);
    out.push(...ring(x, y, TRAY_TOP, CELL_R, 0.002, CELL_H, SILICONE));
  }
  // the lid over the whole tray: a plate with a hole over every cell and a silicone collar round each hole (as the tank-top lid)
  const grey = rgba(0.6, 0.62, 0.66, 0.55);
  const xa = TRAY_CX - TRAY_HX, xb = TRAY_CX + TRAY_HX;
  const ys = Array.from({ length: TRAY_ROWS }, (_, r) => trayY(r)), xs = Array.from({ length: TRAY_COLS }, (_, c) => trayX(c));
  let y0 = -TRAY_HY;
  for (const y of ys) {
    box(xa, xb, y0, y - HOLE_HALF, TLID_Z, TLID_T, grey);
    let x0 = xa;
    for (const x of xs) { box(x0, x - HOLE_HALF, y - HOLE_HALF, y + HOLE_HALF, TLID_Z, TLID_T, grey); x0 = x + HOLE_HALF; }
    box(x0, xb, y - HOLE_HALF, y + HOLE_HALF, TLID_Z, TLID_T, grey);
    y0 = y + HOLE_HALF;
  }
  box(xa, xb, y0, TRAY_HY, TLID_Z, TLID_T, grey);
  for (let s = 0; s < TRAY_SLOTS; s++) { const [x, y] = seatPos(s); out.push(...ring(x, y, TLID_TOP, 0.0155, 0.0015, TCOLLAR_H, SILICONE)); }
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
    `<geom type="cylinder" fromto="${PIPE_X0} ${PIPE_Y} ${PIPE_Z} ${PIPE_X1} ${PIPE_Y} ${PIPE_Z}" size="${PIPE_R}" ${OBST} ${rgba(0.62, 0.66, 0.7)}/>`,
    // tank: floor, four walls, the shelf at 155 mm
    wall(0, 0, t / 2, hx, hy, t / 2, 0.5),
    wall(0, -hy + t / 2, TANK_H / 2, hx, t / 2, TANK_H / 2),
    wall(0, hy - t / 2, TANK_H / 2, hx, t / 2, TANK_H / 2),
    wall(-hx + t / 2, 0, TANK_H / 2, t / 2, hy, TANK_H / 2),
    wall(hx - t / 2, 0, TANK_H / 2, t / 2, hy, TANK_H / 2),
    // loading zone behind the unit: 0.5 m of clear floor behind the tank back, where the store is loaded from (no collision)
    `<geom type="box" pos="0 ${f(hy + LOAD_CLEAR / 2)} 0.0015" size="${f(hx)} ${f(LOAD_CLEAR / 2)} 0.0005" contype="0" conaffinity="0" ${rgba(0.95, 0.75, 0.2, 0.35)}/>`,
    ...spineGeoms(), ...lidGeoms(), ...storeGeoms(), ...trayGeoms(),
    ...Array.from({ length: POD_COUNT }, (_, i) => podMjcf(i)),
  ].join('\n    ');
  const gold = rgba(0.95, 0.8, 0.15);
  const finger = (name: string, sgn: number) => `<body name="${name}" pos="0 ${f(sgn * (CLAW_OPEN + CLAW_T / 2))} 0">
        <joint name="${name}" type="slide" axis="0 ${-sgn} 0" range="0 ${CLAW_GRIP * 3}" damping="5" armature="0.001" frictionloss="0"/>
        <geom type="box" pos="${f((CLAW_BASE + CLAW_TIP) / 2)} 0 0" size="${f((CLAW_TIP - CLAW_BASE) / 2)} ${CLAW_T / 2} ${CLAW_W / 2}" mass="0.004" ${gold}/>
      </body>`;
  // palm across the root of the fingers, 24 mm wide so that it passes the 34 mm pick holes with the fingers
  const claw = `<geom name="palm" type="box" pos="${CLAW_BASE - 0.003} 0 0" size="0.003 0.012 ${CLAW_W / 2}" mass="0.01" ${rgba(0.3, 0.3, 0.33)}/>
      ${finger('claw_l', 1)}
      ${finger('claw_r', -1)}`;
  const clawActs = CLAW_ACT.map((n) => `<position name="${n}" joint="${n}" kp="100" ctrlrange="0 ${CLAW_GRIP * 3}"/>`).join('\n    ');
  const cart = cartMount();
  return armMjcf(world, {
    noGround: true,
    // 60 pods with ~350 contacts: a 4 ms step and a lighter solver keep the sim at real time in the browser (it was 1.5 ms of CPU per 2 ms step)
    option: '<option timestep="0.004" gravity="0 0 -9.81" iterations="20" ls_iterations="10"/>',
    armCollides: true,
    sensors: '<contact name="arm_hit" subtree1="base" data="found" num="1"/>',
    mount: { open: cart.open, close: cart.close },
    baseAttrs: cart.baseAttrs,
    handExtra: claw,
    actuators: clawActs,
  });
}
