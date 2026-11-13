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
const WALL_OUT_R = 34, R_BORE = PIPE_D_MM / 2 + 4;                          // hand_sleeve.py sleeve body
const PAD = { z0: -24, z1: 0, y0: 21, y1: 40 };                            // hand_sleeve.py mounting pad (cart y 21..40, on the plate side)
const PLATE_Y_MM = PAD.y1 + PLATE_MM.t / 2;                                // plate sits on the pads' outer face
/** Closed wheels sit 0.3 mm off the CAD 26 mm radius so they never touch the pipe model. */
export const CLEAR_M = 0.0003;
export const WHEEL_OPEN_M = 0.010;     // ASSUMED: how far each pair backs off the pipe when the hand is open
export const PAIR_ANGLES = { d: 180, p: 60, m: -60 } as const;  // driven, +60 idler, -60 idler (CAD angle from the gap, +X)
type Pair = keyof typeof PAIR_ANGLES;
const PAIRS: Pair[] = ['d', 'p', 'm'];
const JOINTS = ['h1d', 'h1p', 'h1m', 'h2d', 'h2p', 'h2m'] as const;
export type Vec3 = [number, number, number];
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
    cyl(z, AXLE_R, -WHEEL_W / 2, z, AXLE_R, WHEEL_W / 2, WHEEL_R, GREY);               // tyre
    cyl(z, AXLE_R, -WHEEL_W / 2 - 0.3, z, AXLE_R, WHEEL_W / 2 + 0.3, HUB_R, GOLD);     // hub with its two 623ZZ bearings
    const t1 = driven ? GEAR_Y + 2.5 : RAIL_Y0 + RAIL_T;                                 // axle: fixed on idlers, rotating and carrying a worm wheel on the driven pair
    cyl(z, AXLE_R, -(RAIL_Y0 + rt), z, AXLE_R, t1, 1.5, STEEL);
    if (driven) {
      cyl(z, AXLE_R, GEAR_Y - 2, z, AXLE_R, GEAR_Y + 2, GEAR_R + 1, rgba([0.9, 0.55, 0.15]));  // worm wheel
      cyl(z - 4, WORM_X, GEAR_Y, z + 4, WORM_X, GEAR_Y, WORM_R + 1, rgba([0.9, 0.55, 0.15])); // worm
    }
  }
  for (const sg of [1, -1]) box(0, (RAIL_X0 + RAIL_X1) / 2, sg * (RAIL_Y0 + rt / 2), RAIL_HL, (RAIL_X1 - RAIL_X0) / 2, rt / 2, BLUE); // carrier rails
  box(0, (BAR_X0 + BAR_X1) / 2, 0, BAR_HL, (BAR_X1 - BAR_X0) / 2, BAR_W / 2, BLUE);                                                    // cross bar between the rows
  if (driven) {
    cyl(-42, WORM_X, GEAR_Y, 50, WORM_X, GEAR_Y, 1.5, rgba([0.9, 0.55, 0.15]));        // worm shaft
    cyl(45 + 8, WORM_X, GEAR_Y, 45 + 8 + MOTOR_L, WORM_X, GEAR_Y, MOTOR_R, rgba([0.85, 0.25, 0.25])); // drive motor beyond the sleeve end
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
      const uy = -Math.sin(a), uz = zs * Math.cos(a);
      g.push(`<geom type="box" pos="${f(m((x0 + x1) / 2))} ${f(m(rc) * uy)} ${f(m(rc) * uz)}" xyaxes="1 0 0 0 ${f(uy)} ${f(uz)}" size="${f(m(x1 - x0) / 2)} ${f(m(WALL_OUT_R - R_BORE) / 2)} ${f(m(rc) * Math.tan(seg / 2))}" rgba="0.95 0.75 0.2 0.45" ${CART_COL}/>`);
    }
  };
  ring(-45, -41, false); ring(41, 45, false);   // end walls
  ring(-41, -19, true); ring(19, 41, true);     // wheel rows: open at the pockets and the gap
  ring(-19, 19, false);                          // middle, closed except the gap
  return g.join('\n      ').replace(/\n\s*$/, '');
}

/** The cart mocap body (see frame notes below). Two identical hands, 'spacingMm' apart, with the plate centred between them. */
export function cartBody(spacingMm = PIPE_SPACING_MM): string {
  const hy = m(spacingMm);
  const { across, t } = PLATE_MM;
  // Cart frame: x along the track, z toward the inside of the bend, -z the outer side. Origin on the engaged hand's pipe centre line.
  // The plate lies parallel to the track plane, to one side of the pipes (cart y), and is centred between the two hands, so each hand
  // sits the same distance from its end. Hand 2 is the mirror image of hand 1 (gap and wheels), so the whole cart is symmetric.
  const plateZ = -hy / 2, plateY = m(PLATE_Y_MM);
  const hand = (h: 1 | 2) => `<body name="hand${h}" pos="0 0 ${f(handZ(h, spacingMm))}">
      ${sleeveGeoms(h)}
      ${PAIRS.map((p) => {
        const [uy, uz] = radialDir(h, p);
        return `<body name="h${h}${p}" ><joint name="h${h}${p}" type="slide" axis="0 ${f(uy)} ${f(uz)}" range="-0.02 0.05"/>
        ${pairGeoms(h, p)}
      </body>`;
      }).join('\n      ')}
    </body>`;
  return `<body name="cart" mocap="true" pos="0 0 0">
    ${hand(1)}
    ${hand(2)}
    <body name="padside"><joint name="padside" type="slide" axis="0 1 0" range="-1 1"/>
      <geom type="box" pos="${f(m(0))} ${f(m((PAD.y0 + PAD.y1) / 2))} ${f(m((PAD.z0 + PAD.z1) / 2))}" size="${m(45)} ${m((PAD.y1 - PAD.y0) / 2)} ${m((PAD.z1 - PAD.z0) / 2)}" rgba="0.95 0.75 0.2 1" ${CART_COL}/>
      <geom type="box" pos="0 ${f(m((PAD.y0 + PAD.y1) / 2))} ${f(-hy - m((PAD.z0 + PAD.z1) / 2))}" size="${m(45)} ${m((PAD.y1 - PAD.y0) / 2)} ${m((PAD.z1 - PAD.z0) / 2)}" rgba="0.95 0.75 0.2 1" ${CART_COL}/>
    </body>
    <body name="plateside"><joint name="plateside" type="slide" axis="0 1 0" range="-1 1"/>
      <geom name="plate" type="box" pos="0 ${f(plateY)} ${f(plateZ)}" size="${m(PLATE_MM.alongTrack) / 2} ${m(t) / 2} ${m(across) / 2}" rgba="0.25 0.27 0.3 1" ${CART_COL}/>
      <geom name="armmount" type="box" pos="0 ${f(plateY + m(t) / 2 + 0.02)} ${f(plateZ)}" size="0.03 0.02 0.03" rgba="0.9 0.65 0.2 1" ${CART_COL}/>
    </body>
  </body>`;
}

/**
 * Set the openings (0 closed on the pipe .. 1 open) of the cart's two hands and which side of the track plane the plate is on (cart y, +1 or -1).
 * trims1/trims2: per-pair radial adjustments from handTrims (driven, +60, -60), used while a hand is closed.
 */
export function setCart(model: { jnt(name: string): { id: number }; jnt_qposadr: ArrayLike<number> }, qpos: { [i: number]: number },
  hand1Open: number, hand2Open: number, plateSide: 1 | -1 = 1, trims1: number[] = [CLEAR_M, CLEAR_M, CLEAR_M], trims2: number[] = [CLEAR_M, CLEAR_M, CLEAR_M]): void {
  const set = (name: string, v: number) => { qpos[model.jnt_qposadr[model.jnt(name).id]] = v; };
  const pos = (open: number, trim: number) => { const o = Math.min(1, Math.max(0, open)); return (1 - o) * trim + o * WHEEL_OPEN_M; };
  JOINTS.forEach((n, i) => set(n, i < 3 ? pos(hand1Open, trims1[i]) : pos(hand2Open, trims2[i - 3])));
  set('plateside', plateSide === 1 ? 0 : -2 * m(PLATE_Y_MM));
  set('padside', plateSide === 1 ? 0 : -2 * m((PAD.y0 + PAD.y1) / 2));
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
</mujoco>`;
}
