// Reach test scene layout: the Transplant scene's unit (ONE track joined to the spine, the cart riding its -y leg with one sleeve, the straight 90-degree pod holder, the tank with the seedling tray
// inside it) with the central pipe filled with ALL 24 planting holes (each with its collar, seat, plug holder and plug) and the seedling tray filled with all 16 pods (4 x 4, as in the Pod grab scene).
//
// Where the 24 holes come from: cad/unit_v1_assembly.py "pod_sites" (the unit's own site rule, kept in unit_v3_dimensioned.py's geometry): THREE columns 120 degrees apart round the growing pipe, every other level
// turned 60 degrees (a staggered spiral), a vertical pitch of 130 mm, the lowest at 100 mm above the pipe's lower end (z0 = tank 300 + 254 = 554 mm, so z = 654 mm). The CAD rule would give nine levels (27 sites)
// with today's 1884 mm top; the brief names 24, so the lowest EIGHT levels (3 x 8) are used and the ninth (1694 mm) is left out. Azimuths: the CAD frame (x along the tank) is turned a quarter turn in this scene
// (world x = -CAD y, world y = CAD x), so the CAD azimuth a is world azimuth a + 90 degrees. Collar, hole, seat, plug holder and plug are those of cad/pipe_collar.py as in the Transplant scene (layout.ts).
import { armMjcf } from '../model.ts';
import {
  BORE_R, CAP_R, CAP_T, CELL_H, CELL_RIN, DRILL_R, HOLDER_FLOOR_X, LID, OBST, P0, PIPE_RP, PIPE_TOP, PIPE_WALL, PLUG_BODY_L, PLUG_BODY_R, POD_BODY_L, POD_BODY_R, RECESS_R, RECESS_T, S, SHELF_T, SHELF_Z,
  SOCKET_R, TANK_L, TANK_W, TRAY_T, TRAY_Z0, U_CAP, U_FACE, VIS, WALL, X_TOP, XB, XT, YC, GAP, SIDE, LEG, ZH, ZP, cartGeoms, f, quatZ, rgba, track, tube, type V3,
} from '../transplant/layout.ts';

const mm = (v: number) => v / 1000;
const PITCH_MM = 45;
export const TRAY_PITCH = mm(PITCH_MM);

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

// --- the seedling tray: 4 x 4 pods at 45 mm pitch inside the tank (Pod grab: tray 190 wide, 4 x 45 mm cells), under an opening in the lid. Rows along world x (into the tank), columns along y.
export const TRAY_CX = -0.11, TRAY_N = 4;
export const TRAY_HALF = 0.0835;
export interface PodSpec { id: string; n: number; row: number; col: number; x: number; y: number }
export const PODS: PodSpec[] = [];
for (let r = 0; r < TRAY_N; r++) for (let c = 0; c < TRAY_N; c++) PODS.push({ id: `P${PODS.length + 1}`, n: PODS.length + 1, row: r + 1, col: c + 1, x: TRAY_CX + (r - 1.5) * TRAY_PITCH, y: YC + (c - 1.5) * TRAY_PITCH });
export const TRAY_TOP = TRAY_Z0 + TRAY_T;
export const podCapTop = (p: PodSpec): V3 => [p.x, p.y, TRAY_TOP + POD_BODY_L + CAP_T + 0.0003];

// --- cart: heights it can ride to on the straight part of the leg (below 0.63 m the sleeve touches the lower corner, above 1.67 m the upper one), and the 180-degree roll about the leg's own axis
export const CART_MIN = 0.63, CART_MAX = 1.67, CART_STEP = 0.005;
export const LEG_Y = SIDE * LEG;
/** World point of the rolled cart's counterpart: turning the cart 180 degrees about the leg's own axis (x = XT, y = LEG_Y, vertical) is the same, for the arm, as turning the TARGET the other way. */
export const rollPoint = (p: V3): V3 => [2 * XT - p[0], 2 * LEG_Y - p[1], p[2]];
export const rollDir = (d: V3): V3 => [-d[0], -d[1], d[2]];
/** Pose of the cart body: origin (m) and quaternion (w x y z). Rolled: 180 degrees about the vertical axis through the leg. */
export const cartPose = (rolled: boolean, z: number): { pos: V3; quat: [number, number, number, number] } =>
  rolled ? { pos: [XT, 2 * LEG_Y - YC, z], quat: [0, 0, 0, 1] } : { pos: [XT, YC, z], quat: [1, 0, 0, 0] };

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

/** The tank as in the Transplant scene, with the 4 x 4 seedling tray (inside, on two rails over the 155 mm shelf, under a larger opening in the lid). */
function tank(): string[] {
  const out: string[] = [], hx = TANK_W / 2, hy = TANK_L / 2, glass = rgba(0.75, 0.77, 0.82, 0.35), lid = rgba(0.6, 0.62, 0.68), green = rgba(0.2, 0.62, 0.38);
  const box = (x0: number, x1: number, y0: number, y1: number, z0: number, z1: number, c: string) =>
    out.push(`<geom type="box" pos="${f((x0 + x1) / 2)} ${f((y0 + y1) / 2)} ${f((z0 + z1) / 2)}" size="${f((x1 - x0) / 2)} ${f((y1 - y0) / 2)} ${f((z1 - z0) / 2)}" ${OBST} ${c}/>`);
  const zl = LID - 0.004;
  box(-hx, hx, -hy, hy, 0, WALL, glass);
  box(-hx, -hx + WALL, -hy, hy, WALL, zl, glass); box(hx - WALL, hx, -hy, hy, WALL, zl, glass);
  box(-hx + WALL, hx - WALL, -hy, -hy + WALL, WALL, zl, glass); box(-hx + WALL, hx - WALL, hy - WALL, hy, WALL, zl, glass);
  box(-hx + WALL, hx - WALL, -hy + WALL, hy - WALL, SHELF_Z, SHELF_Z + SHELF_T, glass);
  const ox0 = -hx + WALL + 0.001, ox1 = TRAY_CX + 0.0825 + 0.002, oy0 = YC - 0.095, oy1 = YC + 0.095;   // the lid opening over the tray
  box(-hx, ox0, -hy, hy, zl, LID, lid); box(ox1, hx, -hy, hy, zl, LID, lid);
  box(ox0, ox1, -hy, oy0, zl, LID, lid); box(ox0, ox1, oy1, hy, zl, LID, lid);
  box(TRAY_CX - TRAY_HALF, TRAY_CX + TRAY_HALF, YC - 0.095, YC + 0.095, TRAY_Z0, TRAY_TOP, green);
  for (const sx of [-1, 1]) box(TRAY_CX + sx * (TRAY_HALF - 0.01) - 0.004, TRAY_CX + sx * (TRAY_HALF - 0.01) + 0.004, YC - 0.095, YC + 0.095, SHELF_Z + SHELF_T, TRAY_Z0, green);
  for (const p of PODS) out.push(...tube([p.x, p.y, TRAY_TOP], [0, 0, 1], 0, CELL_H, CELL_RIN, CELL_RIN + mm(3), 12, `${OBST} ${rgba(0.95, 0.55, 0.2)}`));
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
