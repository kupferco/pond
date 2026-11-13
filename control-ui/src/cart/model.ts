// MJCF for the Cart scene: floor, a single pipe (up, bend, right), the cart and a target marker.
// The cart and the marker are mocap bodies: their poses are set from the path coordinate, not by physics.
import { BEND_R_MM, HORIZONTAL_MM, PIPE_D_MM, PIPE_SPACING_MM, PLATE_MM, VERTICAL_MM } from './track.ts';

const m = (mm: number) => +(mm / 1000).toFixed(5);
const f = (n: number) => +n.toFixed(5);
export const MARKER_HIDDEN_Z = -50;
const ARC_SEGMENTS = 24;

/** One pipe (up, bend, then horizontal) as MJCF geoms. x0 = x of the vertical section (m); dir = +1 bends right, -1 bends left; horizMm shortens the horizontal bar. */
export function pipeGeoms(x0 = 0, dir: 1 | -1 = 1, horizMm = HORIZONTAL_MM, name = 'p'): string {
  const pr = m(PIPE_D_MM) / 2;
  const lv = m(VERTICAL_MM), lh = m(horizMm), r = m(BEND_R_MM);
  const X = (x: number) => f(x0 + dir * x);
  const segs: string[] = [];
  segs.push(`<geom name="${name}v" type="cylinder" fromto="${X(0)} 0 0 ${X(0)} 0 ${f(lv)}" size="${pr}" rgba="0.62 0.66 0.70 1" contype="1" conaffinity="2"/>`);
  for (let i = 0; i < ARC_SEGMENTS; i++) {
    const a0 = (i / ARC_SEGMENTS) * Math.PI / 2, a1 = ((i + 1) / ARC_SEGMENTS) * Math.PI / 2;
    const p = (a: number) => `${X(r - r * Math.cos(a))} 0 ${f(lv + r * Math.sin(a))}`;
    segs.push(`<geom type="capsule" fromto="${p(a0)} ${p(a1)}" size="${pr}" rgba="0.62 0.66 0.70 1" contype="1" conaffinity="2"/>`);
  }
  segs.push(`<geom name="${name}h" type="cylinder" fromto="${X(r)} 0 ${f(lv + r)} ${X(r + lh)} 0 ${f(lv + r)}" size="${pr}" rgba="0.62 0.66 0.70 1" contype="1" conaffinity="2"/>`);
  return segs.join('\n    ');
}

// ---- The cart's two hands, built from cad/cart_wheel_pairs.py (DRAFT drawing 4) and cad/hand_sleeve.py.
// Each hand is a sleeve round the pipe with six wheels in three rigid pairs (two rows 60 mm apart along the pipe): one DRIVEN pair
// at 180 deg (towards the other hand, with its worm wheels and motor) and two SPRING IDLER pairs at +/-60 deg either side of the C gap
// (which faces away from the other hand). A pair slides radially: closed, its wheels touch the pipe; open, they back off and release it.
// Dimensions in mm, DECIDED unless marked ASSUMED, same as the CAD file.
const WHEEL_R = 10, WHEEL_W = 8, AXLE_R = 26, ROW_Z = 30, HUB_R = 5;      // DECIDED: 20 x 8 wheels on a 26 mm radius, rows 60 mm apart
const RAIL_Y0 = WHEEL_W / 2 + 0.5, RAIL_T = 3, RAIL_T_DRIVEN = 4;          // ASSUMED carrier rails either side of each wheel row
const RAIL_X0 = AXLE_R - 5, RAIL_X1 = AXLE_R + 7, RAIL_HL = ROW_Z + 7;
const BAR_X0 = 22, BAR_X1 = 26, BAR_W = 16, BAR_HL = 16, SPR_Z = 14, SPR_OD = 8, SPR_INST = 7.5, CAP_T = 2.5;  // ASSUMED cross bar, springs, cap
const GEAR_R = 7, WORM_R = 3.5, WORM_X = AXLE_R + GEAR_R + WORM_R, GEAR_Y = RAIL_Y0 + RAIL_T_DRIVEN + 3; // ASSUMED worm drive
const MOTOR_R = 14, MOTOR_L = 55;                                          // ASSUMED motor placeholder
const WALL_OUT_R = 34, R_BORE = PIPE_D_MM / 2 + 8;                          // hand_sleeve.py sleeve body
const PAD = { z0: -WALL_OUT_R, z1: WALL_OUT_R, y0: R_BORE, y1: 40 };               // hand_sleeve.py mounting pad (cart y 21..40 in the CAD; its inner face starts at the bore so it clears the pipe on the bends). Spans the sleeve's full width so it is bolted to both sleeve wedges
const LUG_Z0 = 25, LUG_Y0 = 8;                                              // ASSUMED: bolted lugs from the pad down onto the sleeve wedges either side of the pipe
const GUIDE_X = 10, GUIDE_R0 = 22, GUIDE_R0_IDLER = 34, STRUT_R = 38, GUIDE_R1 = 60, GUIDE_R = 2;               // ASSUMED: two guide pins per wheel pair, fixed in the sleeve, that the pair slides on
const PLATE_Y_MM = PAD.y1 + PLATE_MM.t / 2;                                // plate sits on the pads' outer face
const ARM_Y_MM = PLATE_Y_MM + PLATE_MM.t / 2 + 20;                          // arm base block: its centre 20 mm above the plate's outer face
/** Closed wheels sit 0.3 mm off the CAD 26 mm radius so they never touch the pipe model. */
export const CLEAR_M = 0.0003;
export const WHEEL_OPEN_M = 0.032;     // ASSUMED: how far each pair backs off when the hand is open: far enough that the pipe slides out sideways between the wheels
const SLOT_DEG = 60;                    // ASSUMED: the sleeve is slotted either side (cart +y and -y), so an open hand can swing off a pipe sideways
export const PAIR_ANGLES = { d: 180, p: 60, m: -60 } as const;  // driven, +60 idler, -60 idler (CAD angle from the gap, +X)
type Pair = keyof typeof PAIR_ANGLES;
const PAIRS: Pair[] = ['d', 'p', 'm'];
/** Name of a driven wheel's spin joint (hand 1 or 2, row +1 or -1 along the pipe). */
const wheelName = (hand: 1 | 2, z: number) => `w${hand}${z > 0 ? 'f' : 'b'}`;
const WHEEL_JOINTS = [wheelName(1, 1), wheelName(1, -1), wheelName(2, 1), wheelName(2, -1)];
/** Per wheel system exactly ONE of the three pairs is on the clamp joint (it slides towards / away from the pipe); the other two are rigid on the frame. */
export const CLAMP_PAIR: Record<1 | 2, Pair> = { 1: 'p', 2: 'p' };   // the cart is mirror-symmetric (hand 2 is hand 1 mirrored): the same pair is the clamp pair on both hands, so riding B (hand 2) mirrors riding C (hand 1)
/** Fixed radial offset (m, + = away from the pipe) of the two rigid pairs from the CAD 26 mm radius: enough that they clear the curved pipe all the way round the bend. */
export const FIXED_PAIR_TRIM_M = 0.0045;
export type Vec3 = [number, number, number];
export const ROT_MAX_RAD = Math.PI / 2;   // rotation motors: swing range about the pipe (rad)
const CART_COL = 'contype="2" conaffinity="0"';   // cart geoms collide with pipes only (pipes: contype 1, conaffinity 2)

/** Unit radial direction (cart y, z) of a pair on hand 1 or 2. Cart z points to hand 1's gap side; hand 2 is the mirror image, so the cart is symmetric. */
function radialDir(hand: 1 | 2, pair: Pair): [number, number] {
  const a = (PAIR_ANGLES[pair] * Math.PI) / 180, zs = hand === 1 ? 1 : -1;
  return [-Math.sin(a), zs * Math.cos(a)];
}
const handZ = (hand: 1 | 2, spacingMm: number) => (hand === 1 ? 0 : -m(spacingMm));

/** Centre of one wheel in the cart frame (m): row = +1 or -1 along the pipe, radial = distance from the pipe axis. */
export function wheelLocal(hand: 1 | 2, spacingMm: number, pair: Pair, row: 1 | -1, radial = m(AXLE_R) + CLEAR_M): Vec3 {
  const [uy, uz] = radialDir(hand, pair);
  return [row * m(ROW_Z), uy * radial, handZ(hand, spacingMm) + uz * radial];
}

/**
 * How far (m, + = away from the pipe) each pair of a hand has to sit from the CAD 26 mm wheel radius so no wheel is inside its pipe (0.3 mm on a straight).
 * On the bend a straight hand meets a curved pipe, and the springs (CAD: 2.5 mm travel) and clearance take up the difference.
 * toWorld puts a cart-frame point in the world; dist gives that point's distance to the pipe's centre line (Infinity: no pipe there).
 * Result order: driven, +60, -60.
 */
export function handTrims(hand: 1 | 2, spacingMm: number, toWorld: (v: Vec3) => Vec3, dist: (p: Vec3) => number): number[] {
  const need = m(PIPE_D_MM) / 2 + m(WHEEL_R) + CLEAR_M;
  return PAIRS.map((pair) => {
    let worst = 0;
    for (const row of [1, -1] as const) {
      const d = (s: number) => dist(toWorld(wheelLocal(hand, spacingMm, pair, row, m(AXLE_R) + s)));
      let lo = -0.006, hi = 0.03;
      if (!Number.isFinite(d(0))) return CLEAR_M;
      if (d(lo) >= need) { worst = Math.max(worst, lo); continue; }
      for (let i = 0; i < 40; i++) { const mid = (lo + hi) / 2; if (d(mid) >= need) hi = mid; else lo = mid; }
      worst = Math.max(worst, hi);
    }
    return worst;
  });
}

/** Deepest clamp–track penetration (m, negative) among the current contacts, or 0 when the clamps and wheels clear the track. */
export function clampTrackContacts(data: { ncon: number; contact: { get(i: number): { dist: number } | undefined } }, tolM = CONTACT_TOL_M): number {
  let worst = 0;
  for (let i = 0; i < data.ncon; i++) { const d = data.contact.get(i)?.dist ?? 0; if (d < -tolM) worst = Math.min(worst, d); }
  return worst;
}
export const CONTACT_TOL_M = 0;   // the wheels sit 0.3 mm off the pipe, so ANY penetration of the track is a collision

const rgba = (c: [number, number, number, number?]) => `rgba="${c[0]} ${c[1]} ${c[2]} ${c[3] ?? 1}"`;
const GREY = rgba([0.12, 0.12, 0.12]), STEEL = rgba([0.75, 0.75, 0.78]), GOLD = rgba([0.85, 0.7, 0.2]), BLUE = rgba([0.2, 0.55, 0.85]);

/** One pair's geoms, relative to the hand origin, in the cart frame. Radial u = (0, uy, uz); tangent t = (0, -uz, uy); box local axes = (x along pipe, y radial, z tangent). */
function pairGeoms(hand: 1 | 2, pair: Pair): string {
  const [uy, uz] = radialDir(hand, pair), ty = -uz, tz = uy;
  const at = (x: number, r: number, t: number) => `${f(m(x))} ${f(m(r) * uy + m(t) * ty)} ${f(m(r) * uz + m(t) * tz)}`;
  const axes = `xyaxes="1 0 0 0 ${f(uy)} ${f(uz)}"`;
  const driven = pair === 'd', rt = driven ? RAIL_T_DRIVEN : RAIL_T;
  const g: string[] = [];
  const cyl = (x0: number, r0: number, t0: number, x1: number, r1: number, t1: number, size: number, col: string) =>
    g.push(`<geom type="cylinder" fromto="${at(x0, r0, t0)} ${at(x1, r1, t1)}" size="${f(m(size))}" ${col} ${CART_COL}/>`);
  const box = (x: number, r: number, t: number, hx: number, hr: number, ht: number, col: string) =>
    g.push(`<geom type="box" pos="${at(x, r, t)}" ${axes} size="${f(m(hx))} ${f(m(hr))} ${f(m(ht))}" ${col} ${CART_COL}/>`);
  for (const z of [ROW_Z, -ROW_Z]) {
    if (driven) g.push(`<body name="${wheelName(hand, z)}"><joint name="${wheelName(hand, z)}" type="hinge" pos="${at(z, AXLE_R, 0)}" axis="${f(0)} ${f(-uz)} ${f(uy)}" range="-100000 100000"/>`);
    cyl(z, AXLE_R, -WHEEL_W / 2, z, AXLE_R, WHEEL_W / 2, WHEEL_R, GREY);               // tyre
    cyl(z, AXLE_R, -WHEEL_W / 2 - 0.3, z, AXLE_R, WHEEL_W / 2 + 0.3, HUB_R, GOLD);     // hub with its two 623ZZ bearings
    const t1 = driven ? GEAR_Y + 2.5 : RAIL_Y0 + RAIL_T;                                 // axle: fixed on idlers, rotating and carrying a worm wheel on the driven pair
    cyl(z, AXLE_R, -(RAIL_Y0 + rt), z, AXLE_R, t1, 1.5, STEEL);
    if (driven) {
      cyl(z, AXLE_R, GEAR_Y - 2, z, AXLE_R, GEAR_Y + 2, GEAR_R + 1, rgba([0.9, 0.55, 0.15]));  // worm wheel
    }
    if (driven) g.push('</body>');
  }
  if (driven) for (const z of [ROW_Z, -ROW_Z]) cyl(z - 4, WORM_X, GEAR_Y, z + 4, WORM_X, GEAR_Y, WORM_R + 1, rgba([0.9, 0.55, 0.15])); // worms (fixed with the motor)
  for (const sg of [1, -1]) box(0, (RAIL_X0 + RAIL_X1) / 2, sg * (RAIL_Y0 + rt / 2), RAIL_HL, (RAIL_X1 - RAIL_X0) / 2, rt / 2, BLUE); // carrier rails
  box(0, (BAR_X0 + BAR_X1) / 2, 0, BAR_HL, (BAR_X1 - BAR_X0) / 2, BAR_W / 2, BLUE);                                                    // cross bar between the rows
  if (driven) {
    cyl(-42, WORM_X, GEAR_Y, 56, WORM_X, GEAR_Y, 1.5, rgba([0.9, 0.55, 0.15]));        // worm shaft
    // Drive motor: a body bolted to the wheel system's frame (no joint); only its output, the worm and wheels, spins.
    g.push(`<body name="motor_drive${hand}">`);
    cyl(45 + 8, WORM_X, GEAR_Y, 45 + 8 + MOTOR_L, WORM_X, GEAR_Y, MOTOR_R, rgba([0.85, 0.25, 0.25]));
    cyl(45 + 8 + MOTOR_L, WORM_X, GEAR_Y, 45 + 8 + MOTOR_L + 6, WORM_X, GEAR_Y, MOTOR_R - 3, rgba([0.3, 0.3, 0.32])); // rear cap
    g.push('</body>');
  } else {
    for (const z of [SPR_Z, -SPR_Z]) cyl(z, BAR_X1, 0, z, BAR_X1 + SPR_INST, 0, SPR_OD / 2, rgba([0.9, 0.2, 0.2])); // two compression springs
    box(0, BAR_X1 + SPR_INST + CAP_T / 2, 0, BAR_HL + 4 + 25, CAP_T / 2, BAR_W / 2 + 3, rgba([0.6, 0.6, 0.62]));        // spring cap
  }
  return g.join('\n        ');
}

/** The sleeve of a hand (hand_sleeve.py): a tube round the pipe with a C gap facing away from the other hand and pockets for the six wheels. Drawn translucent. */
function sleeveGeoms(hand: 1 | 2): string {
  const g: string[] = [], N = 24, seg = (2 * Math.PI) / N, rc = (R_BORE + WALL_OUT_R) / 2;
  const pocketAngs = [PAIR_ANGLES.d, PAIR_ANGLES.p, PAIR_ANGLES.m, 0]; // 0 is the C gap
  const near = (deg: number, lim: number) => pocketAngs.some((p) => { const d = Math.abs(((deg - p + 540) % 360) - 180); return 180 - d < lim; });
  const zs = hand === 1 ? 1 : -1;
  const ring = (x0: number, x1: number, skipPockets: boolean) => {
    for (let i = 0; i < N; i++) {
      const a = (i + 0.5) * seg, deg = (a * 180) / Math.PI;
      if (skipPockets && near(deg, 17)) continue;
      if (Math.abs(deg - 90) < SLOT_DEG || Math.abs(deg - 270) < SLOT_DEG) continue;   // side slots
      const uy = -Math.sin(a), uz = zs * Math.cos(a);
      g.push(`<geom type="box" pos="${f(m((x0 + x1) / 2))} ${f(m(rc) * uy)} ${f(m(rc) * uz)}" xyaxes="1 0 0 0 ${f(uy)} ${f(uz)}" size="${f(m(x1 - x0) / 2)} ${f(m(WALL_OUT_R - R_BORE) / 2)} ${f(m(rc) * Math.tan(seg / 2))}" rgba="0.95 0.75 0.2 0.45" ${CART_COL}/>`);
    }
  };
  ring(-45, -41, false); ring(41, 45, false);   // end walls
  ring(-41, -19, true); ring(19, 41, true);     // wheel rows: open at the pockets and the gap
  ring(-19, 19, false);                          // middle, closed except the gap
  // Guide pins: each wheel pair slides on two pins fixed in the sleeve, so an open pair stays on the clamp. The two idler pairs sit in the
  // side slots, so their pins stand on struts that run back to the sleeve wedge beside the C gap.
  const cyl = (a: Vec3, b: Vec3, r: number) => g.push(`<geom type="cylinder" fromto="${a.map((v) => f(m(v))).join(' ')} ${b.map((v) => f(m(v))).join(' ')}" size="${f(m(r))}" ${STEEL} ${CART_COL}/>`);
  for (const pair of PAIRS) {
    const [uy, uz] = radialDir(hand, pair), a = PAIR_ANGLES[pair];
    for (const x of [GUIDE_X, -GUIDE_X]) {
      const r0 = pair === 'd' ? GUIDE_R0 : GUIDE_R0_IDLER;
      cyl([x, r0 * uy, r0 * uz], [x, GUIDE_R1 * uy, GUIDE_R1 * uz], GUIDE_R);
      if (pair !== 'd') {   // strut back to the wedge, kept outside the 16 mm pipe's path out through the side slot
        const wa = ((a > 0 ? 22.5 : -22.5) * Math.PI) / 180, wy = -Math.sin(wa) * rc, wz = zs * Math.cos(wa) * rc;   // the wedge piece next to the gap
        cyl([x, STRUT_R * uy, STRUT_R * uz], [x, wy, wz], GUIDE_R);
      }
    }
  }
  return g.join('\n      ').replace(/\n\s*$/, '');
}

/**
 * Pads, lugs, plate and arm base: ONE rigid body ("plateflip") hinged on the cart about the line through the plate's centre, so the plate can sit on either
 * side of the track plane (the cart is rolled half a turn on pipe B) without any part moving relative to another. Coordinates are relative to the plate
 * centre (local z = cart z + spacing / 2); every piece is touching its neighbour: arm base on plate, plate on both pads, pads bolted to the sleeve wedges by lugs.
 */
function plateGeoms(hy: number): string {
  const across = hy * 1000 + 2 * WALL_OUT_R;   // outer edge of one clamp sleeve to the outer edge of the other: nothing sticks out beyond them
  const g: string[] = [];
  const box = (name: string, y: number, z: number, hx: number, hy_: number, hz: number, col: string) =>
    g.push(`<geom ${name ? `name="${name}" ` : ''}type="box" pos="0 ${f(m(y))} ${f(m(z))}" size="${f(m(hx))} ${f(m(hy_))} ${f(m(hz))}" ${col} ${CART_COL}/>`);
  for (const zc of [hy * 500, -hy * 500]) {   // each hand's centre, relative to the plate centre
    box('', (PAD.y0 + PAD.y1) / 2, zc, 45, (PAD.y1 - PAD.y0) / 2, (PAD.z1 - PAD.z0) / 2, rgba([0.95, 0.75, 0.2]));
    for (const sg of [1, -1]) box('', (LUG_Y0 + PAD.y0) / 2, zc + sg * (LUG_Z0 + PAD.z1) / 2, 45, (PAD.y0 - LUG_Y0) / 2, (PAD.z1 - LUG_Z0) / 2, rgba([0.95, 0.75, 0.2]));
  }
  box('plate', PLATE_Y_MM, 0, PLATE_MM.alongTrack / 2, PLATE_MM.t / 2, across / 2, rgba([0.25, 0.27, 0.3]));
  box('armmount', ARM_Y_MM, 0, 30, 20, 30, rgba([0.9, 0.65, 0.2]));
  return g.join('\n      ');
}

const VISUAL = 'contype="0" conaffinity="0"';   // motor housings are drawn only: the clamp–track check is about the clamp and wheels
/** A hollow-shaft ring (a rotation motor's housing or rotor) round the pipe axis from x0 to x1 (mm), as boxes. */
function ringGeoms(x0: number, x1: number, rIn: number, rOut: number, col: string, N = 16): string {
  const g: string[] = [], seg = (2 * Math.PI) / N, rc = (rIn + rOut) / 2;
  for (let i = 0; i < N; i++) {
    const a = (i + 0.5) * seg, uy = -Math.sin(a), uz = Math.cos(a);
    g.push(`<geom type="box" pos="${f(m((x0 + x1) / 2))} ${f(m(rc) * uy)} ${f(m(rc) * uz)}" xyaxes="1 0 0 0 ${f(uy)} ${f(uz)}" size="${f(m(x1 - x0) / 2)} ${f(m(rOut - rIn) / 2)} ${f(m(rc) * Math.tan(seg / 2))}" ${col} ${VISUAL}/>`);
  }
  return g.join('\n      ');
}
const ROT_MOTOR = { x0: -90, x1: -52, rIn: 22, rOut: 46 };   // ASSUMED: hollow-shaft servo ring at the sleeve's far end from the drive motor; its rotor ring bolts to the sleeve end wall
const ROT_COL = rgba([0.1, 0.65, 0.6]), ROT_ROTOR_COL = rgba([0.95, 0.95, 0.95]);

/** The rotation motor's servo: a block on the ring's outside (cart +y, the plate side) with a dark cap, so the motor that turns the base reads as a motor. */
function rotServoBox(): string {
  const b = (x: number, y: number, hx: number, hy: number, hz: number, col: string) =>
    `<geom type="box" pos="${f(m(x))} ${f(m(y))} 0" size="${f(m(hx))} ${f(m(hy))} ${f(m(hz))}" ${col} ${VISUAL}/>`;
  const xm = (ROT_MOTOR.x0 + ROT_MOTOR.x1) / 2;
  return [b(xm, ROT_MOTOR.rOut + 14, 19, 14, 17, ROT_COL), b(xm, ROT_MOTOR.rOut + 30, 14, 2, 12, rgba([0.15, 0.15, 0.17]))].join('\n      ');
}
/** The clamp motor of a hand: a housing bolted to the sleeve frame at the end of the clamp pair's guide pins, with a lead screw down to the pair. */
const CLAMP_MOTOR = { r0: 82, r1: 118, rad: 13 };
const CLAMP_COL = rgba([0.55, 0.3, 0.8]);
function clampMotorGeoms(hand: 1 | 2): string {
  const [uy, uz] = radialDir(hand, CLAMP_PAIR[hand]);
  const at = (x: number, r: number) => `${f(m(x))} ${f(m(r) * uy)} ${f(m(r) * uz)}`;
  const cyl = (r0: number, r1: number, size: number, col: string) => `<geom type="cylinder" fromto="${at(0, r0)} ${at(0, r1)}" size="${f(m(size))}" ${col} ${VISUAL}/>`;
  return [cyl(CLAMP_MOTOR.r0, CLAMP_MOTOR.r1, CLAMP_MOTOR.rad, CLAMP_COL), cyl(CLAMP_MOTOR.r1, CLAMP_MOTOR.r1 + 6, CLAMP_MOTOR.rad - 4, rgba([0.2, 0.2, 0.22])),
    // bracket: two struts continue the guide pins up to the motor
    ...[GUIDE_X, -GUIDE_X].map((x) => `<geom type="cylinder" fromto="${at(x, GUIDE_R1)} ${at(x, CLAMP_MOTOR.r0)}" size="${f(m(GUIDE_R))}" ${STEEL} ${VISUAL}/>`),
    `<geom type="box" pos="${at(0, CLAMP_MOTOR.r0)}" xyaxes="1 0 0 0 ${f(uy)} ${f(uz)}" size="${f(m(16))} ${f(m(2))} ${f(m(16))}" ${STEEL} ${VISUAL}/>`,
  ].join('\n      ');
}
/** The clamp pair's lead screw: part of the moving pair (driven by the clamp motor), from the spring cap out into the motor. */
function clampScrewGeom(hand: 1 | 2): string {
  const [uy, uz] = radialDir(hand, CLAMP_PAIR[hand]);
  const at = (r: number) => `0 ${f(m(r) * uy)} ${f(m(r) * uz)}`;
  return `<geom type="cylinder" fromto="${at(BAR_X1 + SPR_INST + CAP_T)} ${at(CLAMP_MOTOR.r0 + 10)}" size="${f(m(2.5))}" ${STEEL} ${VISUAL}/>`;
}

/** The cart mocap body (see frame notes below). Two identical hands, 'spacingMm' apart, with the plate centred between them. */
export function cartBody(spacingMm = PIPE_SPACING_MM): string {
  const hy = m(spacingMm);
  // Cart frame: x along the track, z toward the inside of the bend, -z the outer side. Origin on the engaged hand's pipe centre line.
  // The plate lies parallel to the track plane, to one side of the pipes (cart y), and is centred between the two hands, so each hand
  // sits the same distance from its end. Hand 2 is the mirror image of hand 1 (gap and wheels), so the whole cart is symmetric.
  const hand = (h: 1 | 2) => `<body name="hand${h}" pos="0 0 ${f(handZ(h, spacingMm))}">
      ${sleeveGeoms(h)}
      ${ringGeoms(ROT_MOTOR.x1, -45, ROT_MOTOR.rIn, ROT_MOTOR.rOut - 4, ROT_ROTOR_COL)}
      <body name="motor_clamp${h}">
      ${clampMotorGeoms(h)}
      </body>
      ${PAIRS.map((p) => {
        const [uy, uz] = radialDir(h, p);
        const clamp = p === CLAMP_PAIR[h];   // the clamp pair slides on its guide pins; the other two are welded to the frame, set back by the fixed trim
        return `<body name="h${h}${p}" ${clamp ? '' : `pos="0 ${f(uy * FIXED_PAIR_TRIM_M)} ${f(uz * FIXED_PAIR_TRIM_M)}"`}>${clamp ? `<joint name="h${h}${p}" type="slide" axis="0 ${f(uy)} ${f(uz)}" range="-0.02 0.05"/>` : ''}
        ${pairGeoms(h, p)}
        ${clamp ? clampScrewGeom(h) : ''}
      </body>`;
      }).join('\n      ')}
    </body>`;
  // Two rotation motors (one per wheel set): hinges about the engaged pipe's axis (cart x), in series, carrying the whole assembly (both
  // hands, pads, plate, arm base) as one rigid body. Each motor turns the cart about its own hand's pipe axis; the riding hand's motor turns it, the other holds zero. The motors/drive motors are rigid parts of the cart.
  // The rotation motors' stators are bodies on the cart frame itself (which does not turn); their rotors are rings on the hands, which do.
  const stator = (h: 1 | 2) => `<body name="motor_rot${h}" pos="0 0 ${f(handZ(h, spacingMm))}">
      ${ringGeoms(ROT_MOTOR.x0, ROT_MOTOR.x1, ROT_MOTOR.rIn, ROT_MOTOR.rOut, ROT_COL)}
      ${rotServoBox()}
    </body>`;
  return `<body name="cart" mocap="true" pos="0 0 0">
   ${stator(1)}
   ${stator(2)}
   <body name="rot1"><inertial pos="0 0 0" mass="0.1" diaginertia="0.001 0.001 0.001"/><joint name="rot1" type="hinge" pos="0 0 ${f(handZ(1, spacingMm))}" axis="1 0 0" range="-3.2 3.2"/>
   <body name="rot2"><inertial pos="0 0 0" mass="0.1" diaginertia="0.001 0.001 0.001"/><joint name="rot2" type="hinge" pos="0 0 ${f(handZ(2, spacingMm))}" axis="1 0 0" range="-3.2 3.2"/>
    ${hand(1)}
    ${hand(2)}
    <body name="plateflip" pos="0 0 ${f(-hy / 2)}"><joint name="plateflip" type="hinge" axis="1 0 0" range="-4 4"/>
      ${plateGeoms(hy)}
    </body>
   </body>
   </body>
  </body>`;
}

/**
 * Set the openings (0 closed on the pipe .. 1 open) of the cart's two hands and which side of the track plane the plate is on (cart y, +1 or -1).
 * trims1/trims2: per-pair radial adjustments from handTrims (driven, +60, -60), used while a hand is closed.
 */
export function setCart(model: { jnt(name: string): { id: number }; jnt_qposadr: ArrayLike<number> }, qpos: { [i: number]: number },
  hand1Open: number, hand2Open: number, plateSide: 1 | -1 = 1, trims1: number[] = [CLEAR_M, CLEAR_M, CLEAR_M], trims2: number[] = [CLEAR_M, CLEAR_M, CLEAR_M],
  ctrl?: { model: { actuator(name: string): { id: number } }; data: { [i: number]: number } }): void {
  const set = (name: string, v: number) => { qpos[model.jnt_qposadr[model.jnt(name).id]] = v; };
  const pos = (open: number, trim: number) => { const o = Math.min(1, Math.max(0, open)); return (1 - o) * trim + o * WHEEL_OPEN_M; };
  // only each hand's clamp pair has a joint; trims for the rigid pairs are ignored
  const c1 = pos(hand1Open, trims1[PAIRS.indexOf(CLAMP_PAIR[1])]), c2 = pos(hand2Open, trims2[PAIRS.indexOf(CLAMP_PAIR[2])]);
  set('h1' + CLAMP_PAIR[1], c1);
  set('h2' + CLAMP_PAIR[2], c2);
  if (ctrl) { ctrl.data[ctrl.model.actuator('clamp1').id] = c1; ctrl.data[ctrl.model.actuator('clamp2').id] = c2; }   // clamp motors C hold the pair where it is put
  set('plateflip', plateSide === 1 ? 0 : Math.PI);   // pads, plate and arm base turn together, so the arm base stays on the same world side, on top of the plate
}

/** The six actuators, three per wheel system: A drive (spins the wheels), B rotation (swings the base about the pipe), C clamp (slides the one clamp pair). */
export const ACTUATORS = ['drive1', 'drive2', 'rot1', 'rot2', 'clamp1', 'clamp2'] as const;
export function cartActuators(): string {
  const tendon = (n: string, j: string[]) => `<fixed name="${n}">${j.map((x) => `<joint joint="${x}" coef="0.5"/>`).join('')}</fixed>`;   // mean spin of the set's two wheels
  return `<tendon>
    ${tendon('drive1', WHEEL_JOINTS.slice(0, 2))}
    ${tendon('drive2', WHEEL_JOINTS.slice(2))}
  </tendon>
  <actuator>
    <position name="drive1" tendon="drive1" kp="2" ctrlrange="-100000 100000"/>
    <position name="drive2" tendon="drive2" kp="2" ctrlrange="-100000 100000"/>
    <position name="rot1" joint="rot1" kp="20" ctrlrange="-3.2 3.2"/>
    <position name="rot2" joint="rot2" kp="20" ctrlrange="-3.2 3.2"/>
    <position name="clamp1" joint="h1${CLAMP_PAIR[1]}" kp="2000" ctrlrange="-0.02 0.05"/>
    <position name="clamp2" joint="h2${CLAMP_PAIR[2]}" kp="2000" ctrlrange="-0.02 0.05"/>
  </actuator>`;
}

/**
 * Command the motors and place their joints: wheel spin angles (rad) for hand 1 / hand 2, and the cart swing angle (rad). The swing is turned by the
 * rotation motor of the hand that rides the pipe (`rider`): it pivots about that hand's pipe axis. The other rotation motor holds zero.
 */
export function setMotors(model: { jnt(name: string): { id: number }; jnt_qposadr: ArrayLike<number>; actuator(name: string): { id: number } },
  data: { qpos: { [i: number]: number }; ctrl: { [i: number]: number } }, spin1: number, spin2: number, swing: number, rider: 1 | 2 = 1): void {
  const set = (name: string, v: number) => { data.qpos[model.jnt_qposadr[model.jnt(name).id]] = v; };
  const cmd = (name: string, v: number) => { data.ctrl[model.actuator(name).id] = v; };
  WHEEL_JOINTS.forEach((j, i) => set(j, i < 2 ? spin1 : spin2));
  cmd('drive1', spin1); cmd('drive2', spin2);
  const r1 = rider === 1 ? swing : 0, r2 = rider === 2 ? swing : 0;
  set('rot1', r1); set('rot2', r2); cmd('rot1', r1); cmd('rot2', r2);
}

export function cartMjcf(): string {
  const pipes = pipeGeoms();
  return `
<mujoco model="pond_cart">
  <option timestep="0.002" gravity="0 0 -9.81"/>
  <worldbody>
    <geom name="floor" type="plane" pos="0.4 0 -0.05" size="1.4 0.9 0.1" rgba="0.82 0.86 0.9 1"/>
    ${pipes}
    <body name="marker" mocap="true" pos="0 0 ${MARKER_HIDDEN_Z}">
      <geom type="box" size="0.004 0.06 0.05" rgba="0.93 0.45 0.1 1" contype="0" conaffinity="0"/>
    </body>
    ${cartBody()}
  </worldbody>
  ${cartActuators()}
</mujoco>`;
}
