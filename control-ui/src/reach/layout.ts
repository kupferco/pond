// Reach test scene layout: the Transplant scene's unit (ONE track joined to the spine, the cart riding its -y leg with one sleeve, the straight 90-degree pod holder) in the tank of the Pod grab scene (podgrab/layout.ts:
// the 4 x 4 seedling tray flat under the lid in the FRONT half of the tank, reached through 16 pick holes in the lid with silicone collars, and the sloping pod store with its 6 lid pick holes) with the central pipe filled with ALL 24 planting holes (each with its collar, seat, plug holder and plug) and the seedling tray filled with all 16 pods (4 x 4, as in the Pod grab scene).
//
// Where the 24 holes come from: cad/unit_v1_assembly.py "pod_sites" (the unit's own site rule, kept in unit_v3_dimensioned.py's geometry): THREE columns 120 degrees apart round the growing pipe, every other level
// turned 60 degrees (a staggered spiral), a vertical pitch of 130 mm, the lowest at 100 mm above the pipe's lower end (z0 = tank 300 + 254 = 554 mm, so z = 654 mm). The CAD rule would give nine levels (27 sites)
// with today's 1884 mm top; the brief names 24, so the lowest EIGHT levels (3 x 8) are used and the ninth (1694 mm) is left out. Azimuths: the CAD frame (x along the tank) is turned a quarter turn in this scene
// (world x = -CAD y, world y = CAD x), so the CAD azimuth a is world azimuth a + 90 degrees. Collar, hole, seat, plug holder and plug are those of cad/pipe_collar.py as in the Transplant scene (layout.ts).
import { armMjcf } from '../model.ts';
import {
  BORE_R, CAP_R, CAP_T, DRILL_R, HOLDER_FLOOR_X, LID, OBST, P0, PIPE_RP, PIPE_TOP, PIPE_WALL, PLUG_BODY_L, PLUG_BODY_R, POD_BODY_L, POD_BODY_R, RECESS_R, RECESS_T, S, SHELF_T, SHELF_Z,
  SOCKET_R, TANK_L, TANK_W, U_CAP, U_FACE, VIS, WALL, X_TOP, XB, XT, YC, GAP, SIDE, LEG, ZH, ZP, cartGeoms, f, quatZ, rgba, track, tube, type V3,
} from '../transplant/layout.ts';

const mm = (v: number) => v / 1000;

// --- the 24 holes
export const LEVELS = 8, COLS = 3, Z_PITCH = 0.13, Z_FIRST = 0.3 + 0.254 + 0.1;
export interface HoleSpec { id: string; n: number; level: number; col: number; cadDeg: number; psi: number; z: number }
export const HOLES: HoleSpec[] = [];
for (let k = 0; k < LEVELS; k++) for (let j = 0; j < COLS; j++) {
  const cadDeg = j * 120 + (k % 2 ? 60 : 0);
  HOLES.push({ id: `H${HOLES.length + 1}`, n: HOLES.length + 1, level: k + 1, col: j + 1, cadDeg, psi: (cadDeg + 90) * Math.PI / 180, z: Z_FIRST + k * Z_PITCH });
}
const rotZ = (psi: number, v: V3): V3 => [v[0] * Math.cos(psi) - v[1] * Math.sin(psi), v[0] * Math.sin(psi) + v[1] * Math.cos(psi), v[2]];
/** Pod seat axis out of the hole, in the world (out of the pipe and 45 degrees up). */
export const seatDir = (h: HoleSpec): V3 => rotZ(h.psi, [S, 0, S]);
export const seatCapTop = (h: HoleSpec): V3 => { const p0 = rotZ(h.psi, [P0Local[0], 0, 0]), d = seatDir(h), u = U_CAP + CAP_T; return [p0[0] + d[0] * u, p0[1] + d[1] * u, h.z + d[2] * u]; };
const P0Local: V3 = [PIPE_RP - mm(1.5), 0, 0];

// --- the seedling tray, as in the Pod grab scene (podgrab/layout.ts), turned into this scene's frame (Pod grab x = along the tank, y front (-) to back; here world y = Pod grab x and world x = -Pod grab y, so the tank's FRONT is +x,
// the side the track stands on): 4 x 4 cells, 45 mm between columns (along y), 38 mm between rows (along x), tray plate 190 x 370 mm, flat on two rails 200 mm over the tank floor, in the front half of the tank, centred at Pod grab (-0.24, -0.098).
export const TRAY_N = 4, TRAY_CAD_CX = -0.24, TRAY_CAD_CY = -0.098, TRAY_COL_PITCH = 0.045, TRAY_ROW_PITCH = 0.038;
export const TRAY_HX = 0.095, TRAY_HY = 0.185;      // half size of the plate in Pod grab x and y
export const TRAY_Z0 = 0.2, TRAY_T = 0.004;         // plate 200 .. 204 mm (Pod grab values; the Transplant scene had it 40 mm higher)
export const TRAY_TOP = TRAY_Z0 + TRAY_T;
export const HOLE_HALF = 0.017, COLLAR_H = 0.004, COLLAR_IN = 0.017;   // lid pick holes (34 mm) and their silicone collars
export const CELL_R = 0.016, CELL_HT = 0.016;                          // silicone collar round a pod in the tray
export interface PodSpec { id: string; n: number; row: number; col: number; x: number; y: number }
export const PODS: PodSpec[] = [];
for (let r = 0; r < TRAY_N; r++) for (let c = 0; c < TRAY_N; c++) PODS.push({ id: `P${PODS.length + 1}`, n: PODS.length + 1, row: r + 1, col: c + 1, x: -(TRAY_CAD_CY + (r - 1.5) * TRAY_ROW_PITCH), y: TRAY_CAD_CX + (c - 1.5) * TRAY_COL_PITCH });
export const podCapTop = (p: PodSpec): V3 => [p.x, p.y, TRAY_TOP + POD_BODY_L + CAP_T + 0.0003];

// --- the pod store (Pod grab: 6 rows 35 mm apart from x = 70 mm, channels sloping DOWN 12 degrees towards the pick line at the front, floor 205 mm at the pick line, one 34 mm pick hole in the lid over each row)
export const STORE_ROWS = 6, ROW_PITCH = 0.035, ROW_X0 = 0.07 + ROW_PITCH / 2, SLOPE = 12 * Math.PI / 180, STORE_Z0 = 0.205, STORE_CAD_Y0 = -0.145, STORE_LEN = 0.33, RAIL_H = 0.0415;

// --- cart: heights it can ride to on the straight part of a leg (below 0.635 m the omni sleeve's -60 degree lobe touches the lower corner (0.63 m with the old hands), above 1.70 m the upper one; the table stops at 1.67 m as before)
export const CART_MIN = 0.635, CART_MAX = 1.67, CART_STEP = 0.005;

const DARK = rgba(0.3, 0.36, 0.45);
const GREY = rgba(0.62, 0.66, 0.7);

/** Pod or plug in its own frame (origin at the cap top, z into the part). `attrs` sets what it collides with. */
function partGeoms(bodyR: number, bodyL: number, color: string, attrs: string, dimple: boolean): string {
  return `<geom type="cylinder" pos="0 0 ${f(CAP_T / 2)}" size="${CAP_R} ${f(CAP_T / 2)}" ${attrs} ${color}/>
      <geom type="cylinder" pos="0 0 ${f(CAP_T + bodyL / 2)}" size="${bodyR} ${f(bodyL / 2)}" ${attrs} ${color}/>
      ${dimple ? `<geom type="cylinder" pos="0 0 0.0005" size="0.008 0.0006" ${VIS} ${rgba(0.05, 0.05, 0.06)}/>` : ''}`;
}
export const PLUG_COLOR = rgba(0.12, 0.12, 0.14), POD_COLOR = rgba(0.85, 0.65, 0.3);

/** One collar on the pipe: the seat, the plug holder 44 mm below, the shell, and the plug seated. Built with the hole facing +x and turned by the hole's azimuth about the pipe axis. */
function collar(h: HoleSpec): string[] {
  const out: string[] = [], nm = (s: string) => `${s}${h.n}`;
  const zh = h.z, zp = zh - mm(44), p0: V3 = [P0Local[0], 0, zh], dSeat: V3 = [S, 0, S];
  const H = mm(108), RI = PIPE_RP + 0.0001, RO = RI + mm(5), z0 = zh - mm(68);
  out.push(...tube([0, 0, z0], [0, 0, 1], 0, H, RI, RO, 36, `${VIS} ${rgba(0.55, 0.6, 0.68, 0.38)}`));
  out.push(...tube(p0, dSeat, -mm(10), mm(12), BORE_R, mm(15), 16, `${OBST} ${DARK}`, { name: nm('seat_spigot') }));
  out.push(...tube(p0, dSeat, mm(12), U_CAP - GAP, BORE_R, mm(20), 16, `${OBST} ${DARK}`, { name: nm('seat_boss') }));
  out.push(...tube(p0, dSeat, U_CAP - GAP, U_FACE, RECESS_R, mm(20), 16, `${OBST} ${DARK}`, { name: nm('seat_rim') }));
  const pp: V3 = [0, 0, zp];
  out.push(...tube(pp, [1, 0, 0], HOLDER_FLOOR_X - GAP, X_TOP - RECESS_T - GAP, BORE_R, mm(20), 16, `${OBST} ${DARK}`, { name: nm('holder_boss') }));
  out.push(...tube(pp, [1, 0, 0], X_TOP - RECESS_T - GAP, X_TOP, RECESS_R, mm(20), 16, `${OBST} ${DARK}`, { name: nm('holder_rim') }));
  out.push(`<geom type="cylinder" pos="${f(HOLDER_FLOOR_X - GAP - 0.002)} 0 ${f(zp)}" size="${mm(20)} 0.002" euler="0 1.5708 0" ${OBST} ${DARK}/>`);
  out.push(`<geom type="box" pos="${f(mm(40))} 0 ${f((zh + zp) / 2 - mm(8))}" size="${mm(10)} ${mm(18)} ${f((zh - zp) / 2)}" ${VIS} ${DARK}/>`);
  // the plug, seated: cap top at U_CAP + CAP_T along the seat axis, its axis into the part is -dSeat
  const u = U_CAP + CAP_T, cap: V3 = [p0[0] + dSeat[0] * u, 0, zh + dSeat[2] * u], q = quatZ([-dSeat[0], -dSeat[1], -dSeat[2]]);
  out.push(`<body name="${nm('plug')}" pos="${cap.map(f).join(' ')}" quat="${q.map(f).join(' ')}">${partGeoms(PLUG_BODY_R, PLUG_BODY_L, PLUG_COLOR, OBST, true)}</body>`);
  return [`<body name="collar${h.n}" euler="0 0 ${f(h.psi)}">`, ...out, '</body>'];
}

/** The central pipe with all 24 holes drilled, the socket on the lid and the 24 collars. */
function pipeAndCollars(): string[] {
  const out: string[] = [], rIn = PIPE_RP - PIPE_WALL;
  const inHole = (x: number, y: number, z: number) => HOLES.some((h) => {
    if (Math.abs(z - h.z) > DRILL_R + 0.003) return false;
    const u = x * Math.cos(h.psi) + y * Math.sin(h.psi), v = -x * Math.sin(h.psi) + y * Math.cos(h.psi);
    return u > 0 && Math.hypot(v, z - h.z) < DRILL_R + 0.0015;
  });
  out.push(...tank());
  out.push(...tube([0, 0, LID], [0, 0, 1], 0, 0.025, PIPE_RP + 0.001, SOCKET_R, 32, `${OBST} ${rgba(0.95, 0.6, 0.2)}`));
  out.push(...tube([0, 0, LID], [0, 0, 1], 0, PIPE_TOP - LID, rIn, PIPE_RP, 48, `${OBST} ${rgba(0.93, 0.95, 0.97, 0.28)}`, { chunk: 0.003, skip: inHole, name: 'pipe' }));
  for (const h of HOLES) out.push(...collar(h));
  return out;
}

/** A flat plate (z0..z1) over x0..x1 x y0..y1 with square holes (centre, half side) cut out, as boxes. */
function plateWithHoles(x0: number, x1: number, y0: number, y1: number, z0: number, z1: number, holes: [number, number][], h: number, c: string, add: (s: string) => void) {
  const box = (xa: number, xb: number, ya: number, yb: number) => { if (xb - xa > 1e-6 && yb - ya > 1e-6) add(`<geom type="box" pos="${f((xa + xb) / 2)} ${f((ya + yb) / 2)} ${f((z0 + z1) / 2)}" size="${f((xb - xa) / 2)} ${f((yb - ya) / 2)} ${f((z1 - z0) / 2)}" ${OBST} ${c}/>`); };
  const ys = [...new Set([y0, y1, ...holes.flatMap(([, y]) => [y - h, y + h])])].sort((a, b) => a - b);
  for (let i = 0; i + 1 < ys.length; i++) {
    const ya = ys[i], yb = ys[i + 1], mid = (ya + yb) / 2;
    const cuts = holes.filter(([, y]) => Math.abs(mid - y) < h).map(([x]) => [x - h, x + h]).sort((a, b) => a[0] - b[0]);
    let xa = x0; for (const [cx0, cx1] of cuts) { box(xa, cx0, ya, yb); xa = cx1; } box(xa, x1, ya, yb);
  }
}

/** The tank as in the Pod grab scene: 700 (along y) x 400 (along x) x 300, hollow (4 mm walls and floor), the 155 mm shelf, a 4 mm lid with a 34 mm pick hole and silicone collar over every one of the 16 tray cells and over every store row,
 *  the tray flat on two rails, and the sloping store (floor and a guide wall between rows). */
function tank(): string[] {
  const out: string[] = [], hx = TANK_W / 2, hy = TANK_L / 2, glass = rgba(0.75, 0.77, 0.82, 0.35), lid = rgba(0.6, 0.62, 0.68), green = rgba(0.2, 0.62, 0.38), silicone = rgba(0.95, 0.55, 0.2), steel = rgba(0.42, 0.44, 0.5);
  const box = (x0: number, x1: number, y0: number, y1: number, z0: number, z1: number, c: string) =>
    out.push(`<geom type="box" pos="${f((x0 + x1) / 2)} ${f((y0 + y1) / 2)} ${f((z0 + z1) / 2)}" size="${f((x1 - x0) / 2)} ${f((y1 - y0) / 2)} ${f((z1 - z0) / 2)}" ${OBST} ${c}/>`);
  const zl = LID - 0.004;
  box(-hx, hx, -hy, hy, 0, WALL, glass);
  box(-hx, -hx + WALL, -hy, hy, WALL, zl, glass); box(hx - WALL, hx, -hy, hy, WALL, zl, glass);
  box(-hx + WALL, hx - WALL, -hy, -hy + WALL, WALL, zl, glass); box(-hx + WALL, hx - WALL, hy - WALL, hy, WALL, zl, glass);
  box(-hx + WALL, hx - WALL, -hy + WALL, hy - WALL, SHELF_Z, SHELF_Z + SHELF_T, glass);
  // lid: pick holes over the 16 cells and over each store row (over position 0 of the row: the channel floor's pick point, a little further out along the slope's tilt, see podgrab pickHoleY)
  const pickX = -(STORE_CAD_Y0 - (zl + 0.002 - (STORE_Z0 + 0.02)) * Math.tan(SLOPE));
  const holes: [number, number][] = [...PODS.map((p) => [p.x, p.y] as [number, number]), ...Array.from({ length: STORE_ROWS }, (_, r) => [pickX, ROW_X0 + r * ROW_PITCH] as [number, number])];
  plateWithHoles(-hx, hx, -hy, hy, zl, LID, holes, HOLE_HALF, lid, (g) => out.push(g));
  for (const [x, y] of holes) out.push(...tube([x, y, LID], [0, 0, 1], 0, COLLAR_H, COLLAR_IN, COLLAR_IN + 0.0005, 8, `${OBST} ${silicone}`));
  // the tray: a thin plate on two rails over the shelf, the cells' silicone collars
  box(-TRAY_HY, TRAY_HY, TRAY_CAD_CX - TRAY_HX, TRAY_CAD_CX + TRAY_HX, TRAY_Z0, TRAY_TOP, green);
  for (const sy of [-1, 1]) box(-TRAY_HY, TRAY_HY, TRAY_CAD_CX + sy * (TRAY_HX - 0.01) - 0.01, TRAY_CAD_CX + sy * (TRAY_HX - 0.01) + 0.01, SHELF_Z + SHELF_T, TRAY_Z0, steel);
  for (const p of PODS) out.push(...tube([p.x, p.y, TRAY_TOP], [0, 0, 1], 0, CELL_HT, CELL_R, CELL_R + mm(3), 12, `${OBST} ${silicone}`));
  // the store: per row a floor and, on the boundaries, a guide wall, in the tilted frame (slope runs to -x and up; the pick line at x = +0.145)
  const sT = Math.sin(SLOPE), cT = Math.cos(SLOPE), ax = `xyaxes="${f(-cT)} 0 ${f(sT)} 0 -1 0"`;
  const at = (s: number, h: number): V3 => [-STORE_CAD_Y0 - s * cT + h * sT, 0, STORE_Z0 + s * sT + h * cT];
  for (let r = 0; r < STORE_ROWS; r++) { const p = at(STORE_LEN / 2 - 0.03, -0.002); out.push(`<geom type="box" pos="${f(p[0])} ${f(ROW_X0 + r * ROW_PITCH)} ${f(p[2])}" size="${f(STORE_LEN / 2)} ${f(ROW_PITCH / 2 - 0.002)} 0.002" ${ax} ${OBST} ${steel}/>`); }
  for (let r = 0; r <= STORE_ROWS; r++) { const p = at(STORE_LEN / 2 - 0.03, RAIL_H / 2), y = ROW_X0 + (r - 0.5) * ROW_PITCH; out.push(`<geom type="box" pos="${f(p[0])} ${f(y)} ${f(p[2])}" size="${f(STORE_LEN / 2)} 0.002 ${f(RAIL_H / 2)}" ${ax} ${OBST} ${steel}/>`); }
  return out;
}

/** MJCF of the reach test scene. Every plug (body plug<n>) and pod (body pod<n>) is a static collidable part; the reach test switches the target's own geoms off while it is gripped. */
export function reachMjcf(): string {
  const pods = PODS.map((p) => `<body name="pod${p.n}" pos="${podCapTop(p).map(f).join(' ')}" quat="0 1 0 0">${partGeoms(POD_BODY_R, POD_BODY_L, POD_COLOR, OBST, false)}</body>`);
  const world = [`<geom name="floor" type="plane" size="1.6 1.2 0.01" pos="0 0 0" ${OBST} ${rgba(0.84, 0.88, 0.92)}/>`, ...pipeAndCollars(), ...track(), ...pods].join('\n    ');
  const base = `pos="${f(-mm(102) - 0.0085)} 0 0" xyaxes="0 0 -1 0 -1 0"`;
  const open = `<body name="cart" mocap="true" pos="${XT} ${YC} ${CART_MIN}">
      ${cartGeoms().join('\n      ')}`;
  return armMjcf(world, { noGround: true, option: '<option timestep="0.004" gravity="0 0 0"/>', armCollides: true, mount: { open, close: '</body>' }, baseAttrs: base });
}
export { GREY, ZH, ZP, XB };
