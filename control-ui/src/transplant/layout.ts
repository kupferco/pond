// Transplant scene layout: ONE pipe (the growing pipe, with its collar), the tank it stands on with the seedling tray INSIDE the tank (under an opening in the lid), ONE track (the unit's rounded-corner portrait loop, joined to the spine
// by its top and bottom brackets) and the cart that rides that track with ONE hand (sleeve) and carries the arm.
// Metres. World frame: z up, pipe axis (and spine) at x = y = 0. The unit CAD's frame turned a quarter turn: world x = -CAD y (the unit's front, where the track stands, is +x), world y = CAD x (along the tank's 700 mm).
//
// From the CAD (cad/pipe_collar.py, cad/cart_pod_holder.py, cad/cart_dims.py, cad/unit_v3_aframe.py; mm in the CAD, converted here):
//  - tank 700 x 400 x 300 with a 4 mm lid (top at 304 mm); growing pipe 75 mm OD, 3 mm wall, standing in a socket (OD 95) on the lid; hole 45 mm drilled square to the pipe (axis +x) at ZH
//  - collar: pod seat 26 mm bore on an axis 45 degrees UP from +x, through P0 = (RP - 1.5, 0, ZH); seat face at 23.7 mm along the axis, cap underside 21.7, the cap (34 x 8) stands 6 mm proud
//  - plug holder: a straight (horizontal, +x) blind socket of the same shape, 44 mm BELOW the hole, floor at x = 40, seat face at x = 54
//  - pod and plug: body 25 (plug 25.5) x 32 (plug 17), cap 34 x 8
//  - cart (the omni cart, Pond #284): plate 6 mm on the sleeve pads (plate face at cart y -56), battery 70 x 50 x 70 under the arm base, arm base on the plate centre; the arm base underside is 106 mm out of the pipe plane (cart y -106); pod holder: a cup of 42 mm / bore 26 mm, 40 mm long, axis 45 degrees out of the plate AND up
//  - track (cad/unit_v3_dimensioned.py, unit_v1_assembly.py): ONE loop, tube radius 16, corner radius 150, legs 580 mm apart (x = -/+290), bottom run from the shared layout (cad/layout.json, 514), top run at 1884, in the plane 60 mm in front of the pipe axis (LOOP_Y = -60);
//    spine 33.7 x 2 tube on the pipe axis up to 1884, and two brackets (16 x 30 x 30) joining the top and the bottom run to it at x = 0; joint rings (6 mm, r 17.5) at four heights on each leg
//  - the cart rides the track with ONE of its two hands (hand C, on the leg at y = -0.29 here); the other hand (B) hangs open beside it, its jaw open 92 degrees, and is only used for transfers between pipes (Transfer scene)
// ASSUMED here (not in the repo): hole height ZH 0.80 m and the collar's azimuth round the pipe (PSI); the seedling tray (3 cells) inside the tank, 240 mm over its floor; the three heights the cart stops at (the arm reaches only inside its own plane,
// which fixes them, see check below).
import { armMjcf } from '../model.ts';
import * as LAYOUT from '../layout.ts';   // the ONE shared layout (cad/layout.json): tank, lid and bottom track heights
import { staticOmniCart, CART } from '../cart/omni-scene.ts';
import { CAD_UNIT, CAD_CONSTANTS } from '../generated/cad-sim.ts';
const CAD_UNIT_DIMS = CAD_CONSTANTS.unit_dims;
import { withCartAssets } from '../cart/cad-cart.ts';
import { HX } from '../cart/omni.ts';

/** Which leg of the track the cart rides: -1 = the leg at world y = -0.29. The seedling tray is in the tank's back corner on that same side (the arm works along its base axis, towards the back), so the pods are
 *  in the corner opposite to where they were (v5: +y leg, tray at +y). */
export const SIDE = -1;
export const f = (n: number) => +n.toFixed(5);
const mm = (v: number) => v / 1000;
export type V3 = [number, number, number];
export const S = Math.SQRT1_2;

// --- pod, plug (mm in the CAD)
export const POD_BODY_R = mm(12.5), POD_BODY_L = mm(32), CAP_R = mm(17), CAP_T = mm(8);
export const PLUG_BODY_R = mm(12.75), PLUG_BODY_L = mm(17);
export const BORE_R = mm(13);                         // seat bore 26 mm
export const RECESS_R = mm(17.6), RECESS_T = mm(2);   // cap recess 35.2 mm, 2 mm deep
export const PROUD = CAP_T - RECESS_T;                // 6 mm of cap stand proud of the seat face

// --- central pipe and collar
export const PIPE_RP = mm(CAD_UNIT_DIMS.GP / 2), PIPE_WALL = mm(3), ZT = CAD_UNIT.ZT / 1000, PIPE_TOP = ZT;   // growing pipe OD 75 and the top run height: cad/parts/unit_dims.py GP, ZT   // the growing pipe and the spine run up to the top run's height (unit_v3_dimensioned.py)
export const TANK_L = 0.7, TANK_W = 0.4, LID = LAYOUT.LID_TOP;     // tank 700 (along world y) x 400 (along x), lid top at 304 mm (unit_v3_aframe.py: TH 300 + 4)
export const SOCKET_R = PIPE_RP + mm(10);
export const DRILL_R = mm(22.5);
export const ZH = 0.80;                               // hole centre height (ASSUMED)
export const ZP = ZH - mm(44);                        // plug holder height
/** The collar's azimuth round the pipe, from world +x towards +y (ASSUMED, the CAD leaves it free): chosen so that the pod seat axis lies in a plane through the arm's base axis (the SO-101 can only point
 *  its hand along such a plane) when the cart stands about 0.2 m above the hole, see ../../scripts/check-transplant-reach.ts. */
export const PSI = SIDE * 132 * Math.PI / 180;
const CP = Math.cos(PSI), SP = Math.sin(PSI);
/** Turn a vector given in the collar's own frame (+x = out of the hole) about the pipe axis into the world frame. */
export const rz = (v: V3): V3 => [v[0] * CP - v[1] * SP, v[0] * SP + v[1] * CP, v[2]];
export const P0: V3 = rz([PIPE_RP - mm(1.5), 0, ZH]);
export const D_SEAT: V3 = rz([S, 0, S]);              // pod seat axis, out of the pipe and up
export const U_CAP = mm(21.7), U_FACE = U_CAP + RECESS_T;
export const HOLDER_FLOOR_X = mm(40), X_TOP = mm(54), PARK_DX = mm(5);
const at = (p: V3, d: V3, u: number): V3 => [p[0] + d[0] * u, p[1] + d[1] * u, p[2] + d[2] * u];
/** Cap-top point of a pod or plug seated in the hole's seat (the point the hand grips), and the direction out of the seat. */
export const SEAT_CAP_TOP = at(P0, D_SEAT, U_CAP + CAP_T);
/** Cap-top of the plug parked in the straight holder: it stands PARK_DX further out than a seated one (blind floor). */
export const PARK_CAP_TOP: V3 = rz([X_TOP - RECESS_T + PARK_DX + CAP_T, 0, ZP]);
export const D_PARK: V3 = rz([1, 0, 0]);

// --- the cart (CART frame of cad/cart_dims.py: x across the pipes, y out of the pipe plane, plate on -y, z up the pipes)
export const XT = -CAD_UNIT.LOOP_Y / 1000;            // world x of the track plane: 60 mm in front of the pipe axis (cad/parts/unit_dims.py LOOP_Y = -60; sim x = -CAD y)
export const LEG = CAD_UNIT.TX / 1000;                // the track's legs stand at world y = -/+ 0.29 (cad/parts/unit_dims.py TX = 290; sim y = CAD x)
/** The cart rides the leg at SIDE * LEG with the hand on that side (hand B, cart x = -60 mm, on the +y leg; hand C, cart x = +60 mm, on the -y leg, see cart/omni.ts): the cart origin is 60 mm towards the pipe plane from it. */
export const YC = SIDE * (LEG - HX / 1000);
export const ARM_CX = 0;                              // arm base centre across the plate (cad/cart_dims.py ARM_X = 0)
export const ARM_CY = mm(CART.battFaceY);             // arm base underside (on the battery front): cart y -106 (plate face -56, battery 50 thick; cad/cart_dims.py ARM_Y0)
export const BASE_BOTTOM = 0.0085;                    // the arm model's base origin is 8.5 mm out from the base underside (model.ts)
export const XB = XT + ARM_CY - BASE_BOTTOM;          // world x of the arm base origin; the base axis (z) points along -x
/** World offset (from the cart origin on the arm plane at the pipe plane) of a CART frame point (cx, cy, cz). */
export const cartToWorld = (cx: number, cy: number, cz: number): V3 => [cy, -(cx - ARM_CX), cz];
// pod holder cup (cart_pod_holder.py v3): axis out of the plate (cart -y), square to it, no tilt
export const CUP_ROOT: V3 = [ARM_CX, mm(CART.plateFaceY - 18), mm(-88)];   // cart_pod_holder.py: root 18 mm out from the plate face (-56), z -88
export const CUP_DROP = 0;                        // the pod holder sits exactly where cad/cart_pod_holder.py puts it (v3: straight, 90 degrees to the plate)
export const CUP_L = mm(40), CUP_R = mm(21);
/** Direction out of the cup, in world coordinates (out of the plate = world -x; horizontal, 90 degrees to the plate). */
export const D_CUP: V3 = [-1, 0, 0];
/** Cup root point and the cap-top point of a pod in the cup, as offsets from the cart origin (world axes). */
const cupRoot = (): V3 => cartToWorld(CUP_ROOT[0], CUP_ROOT[1], CUP_ROOT[2] - CUP_DROP);
export const CUP_CAP_TOP_REL: V3 = (() => { const r = cupRoot(); return at(r, D_CUP, CUP_L - RECESS_T + CAP_T); })();

// --- seedling tray
// Inside the tank, as in the Pod grab scene (podgrab/layout.ts): a thin tray 240 mm over the tank floor (TRAY_Z0, on two rails over the 155 mm shelf; the Pod grab scene has it at 200 mm, 40 mm higher here because the cart cannot ride lower than 0.63 m on the straight leg and the SO-101 cannot reach further down from there), under an opening in the lid; the pods stand in it, caps up, 20 mm under the lid.
export const TRAY_X = XB - 0.10, TRAY_Y: number[] = [YC - 0.06, YC, YC + 0.06], TRAY_T = 0.004, TRAY_Z0 = 0.24, TRAY_TOP = TRAY_Z0 + TRAY_T;
export const WALL = 0.004, SHELF_Z = 0.155, SHELF_T = 0.004;
export const OPEN_HX = 0.04, OPEN_HY = 0.095;   // the lid opening over the tray: half size along x and y
export const CELL_RIN = mm(13), CELL_H = mm(30);
/** Cap-top of the seedling pod that is picked (middle cell). Standing on the tray, pod axis down. */
export const TRAY_CAP_TOP: V3 = [TRAY_X, YC, TRAY_TOP + POD_BODY_L + CAP_T + 0.0003];

// --- cart heights (cart origin = arm base axis height), driving range
export const CART_Z0 = 0.64;                          // stop 1, at the seedling tray: as low as the hand can go on the straight part of the leg (below 0.63 m the sleeve touches the track corner)
/** Stop 2, at the hole: the height at which the pod seat's axis lies in the plane through the arm's base axis and the seat (the SO-101 can only point its hand along such a plane): the cart is about 0.2 m above the hole. */
export const CART_Z1 = SEAT_CAP_TOP[2] - (SEAT_CAP_TOP[1] - YC) * D_SEAT[2] / D_SEAT[1];
/** Stop 3, at the plug holder: its horizontal axis is in such a plane only when the cart is level with the holder. */
export const CART_ZP = PARK_CAP_TOP[2];
export const CART_Z_MAX = 1.3;

// --- gripper (the stand-in hand of model.ts): the cap-top point on the pod axis, in the hand frame
export const GRIP_TX = 0.0785, GRIP_TZ = 0.011;
export const JAW_OPEN_DEG = 50, JAW_CAP_DEG = 30;

export const rgba = (r: number, g: number, b: number, a = 1) => `rgba="${r} ${g} ${b} ${a}"`;
export const OBST = 'contype="1" conaffinity="3" margin="0.001"';
export const VIS = 'contype="0" conaffinity="0"';

const dot = (a: V3, b: V3) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const cross = (a: V3, b: V3): V3 => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const norm = (a: V3): V3 => { const l = Math.hypot(...a); return [a[0] / l, a[1] / l, a[2] / l]; };
const basis = (a: V3): [V3, V3] => {
  const e1 = norm(cross(a, Math.abs(a[1]) > 0.9 ? [1, 0, 0] : [0, 1, 0]));
  return [e1, cross(a, e1)];
};
/** Quaternion (w x y z) whose z axis is `a`. */
export function quatZ(a: V3): [number, number, number, number] {
  const z: V3 = [0, 0, 1], c = dot(z, a);
  if (c > 1 - 1e-12) return [1, 0, 0, 0];
  if (c < -1 + 1e-12) return [0, 1, 0, 0];
  const ax = norm(cross(z, a)), h = Math.acos(c) / 2, s = Math.sin(h);
  return [Math.cos(h), ax[0] * s, ax[1] * s, ax[2] * s];
}

/** A tube of box slats round the axis a through p0, from u0 to u1 along it, inner radius rIn, outer rOut. skip(angle, u) leaves a slat piece out. */
export function tube(p0: V3, a: V3, u0: number, u1: number, rIn: number, rOut: number, n: number, attrs: string, opts: { name?: string; chunk?: number; skip?: (px: number, py: number, pz: number) => boolean } = {}): string[] {
  const out: string[] = [], [e1, e2] = basis(a);
  const th = (rOut - rIn) / 2, rc = (rIn + rOut) / 2, half = rOut * Math.tan(Math.PI / n) + 0.0003;
  const chunk = opts.chunk ?? (u1 - u0);
  const m = Math.max(1, Math.ceil((u1 - u0) / chunk - 1e-9));
  for (let k = 0; k < n; k++) {
    const al = 2 * Math.PI * k / n, rad: V3 = [Math.cos(al) * e1[0] + Math.sin(al) * e2[0], Math.cos(al) * e1[1] + Math.sin(al) * e2[1], Math.cos(al) * e1[2] + Math.sin(al) * e2[2]];
    const tan: V3 = [-Math.sin(al) * e1[0] + Math.cos(al) * e2[0], -Math.sin(al) * e1[1] + Math.cos(al) * e2[1], -Math.sin(al) * e1[2] + Math.cos(al) * e2[2]];
    let run: number | null = null;   // merge consecutive kept chunks into one slat
    const flush = (end: number) => {
      if (run === null) return;
      const ua = u0 + run * chunk, ub = Math.min(u1, u0 + end * chunk), um = (ua + ub) / 2;
      const c: V3 = [p0[0] + a[0] * um + rad[0] * rc, p0[1] + a[1] * um + rad[1] * rc, p0[2] + a[2] * um + rad[2] * rc];
      out.push(`<geom ${opts.name ? `name="${opts.name}_${k}_${run}"` : ''} type="box" pos="${f(c[0])} ${f(c[1])} ${f(c[2])}" size="${f(th)} ${f(half)} ${f((ub - ua) / 2)}" xyaxes="${rad.map(f).join(' ')} ${tan.map(f).join(' ')}" ${attrs}/>`);
      run = null;
    };
    for (let i = 0; i < m; i++) {
      const um = u0 + (i + 0.5) * chunk;
      const c: V3 = [p0[0] + a[0] * um + rad[0] * rc, p0[1] + a[1] * um + rad[1] * rc, p0[2] + a[2] * um + rad[2] * rc];
      if (opts.skip && opts.skip(c[0], c[1], c[2])) flush(i); else if (run === null) run = i;
    }
    flush(m);
  }
  return out;
}

export const GAP = 0.0005;   // seats end this far below a part's resting face, so a part seated or parked is clear of it (the CAD parts rest face to face)
const SILVER = rgba(0.62, 0.66, 0.7), DARK = rgba(0.3, 0.36, 0.45), STEEL = rgba(0.3, 0.32, 0.36);

/** The central pipe, drilled; the collar's two seats; the plug holder. Static, in world coordinates. */
function pipeAndCollar(): string[] {
  const out: string[] = [];
  const rIn = PIPE_RP - PIPE_WALL;
  // the 45 mm hole: slat pieces whose centre lies inside the drilled circle (in the y, z plane, on the +x side) are left out
  const inHole = (x: number, y: number, z: number) => x > 0 && Math.hypot(y, z - ZH) < DRILL_R + 0.0015;
  // the tank (700 along y x 400 along x x 300, lid on top) and the pipe's socket on the lid: static, in the world frame
  const world: string[] = [];
  world.push(...tank());
  world.push(...tube([0, 0, LID], [0, 0, 1], 0, 0.025, PIPE_RP + 0.001, SOCKET_R, 32, `${OBST} ${rgba(0.95, 0.6, 0.2)}`));
  // the pipe, the collar and the plug holder are built with the hole facing +x and turned by PSI about the pipe axis (a static body)
  out.push(...tube([0, 0, LID], [0, 0, 1], 0, PIPE_TOP - LID, rIn, PIPE_RP, 48, `${OBST} ${rgba(0.93, 0.95, 0.97, 0.28)}`, { chunk: 0.003, skip: inHole, name: 'pipe' }));
  // collar front half and back half as a shell round the pipe (shown only: the seat tubes below are what the arm and the pod must clear)
  const H = mm(108), RI = PIPE_RP + 0.0001, RO = RI + mm(5), z0 = ZH - mm(68);
  out.push(...tube([0, 0, z0], [0, 0, 1], 0, H, RI, RO, 36, `${VIS} ${rgba(0.55, 0.6, 0.68, 0.38)}`));
  // seat tube along the 45 degree axis: a narrow part through the drilled hole, the boss (R 20) outside the pipe, then the cap rim (recess)
  out.push(...tube(P0, D_SEAT, -mm(10), mm(12), BORE_R, mm(15), 16, `${OBST} ${DARK}`, { name: 'seat_spigot' }));
  out.push(...tube(P0, D_SEAT, mm(12), U_CAP - GAP, BORE_R, mm(20), 16, `${OBST} ${DARK}`, { name: 'seat_boss' }));
  out.push(...tube(P0, D_SEAT, U_CAP - GAP, U_FACE, RECESS_R, mm(20), 16, `${OBST} ${DARK}`, { name: 'seat_rim' }));
  // the plug holder: straight, horizontal, blind (a floor disc), 44 mm below the hole
  const pp: V3 = [0, 0, ZP];
  out.push(...tube(pp, [1, 0, 0], HOLDER_FLOOR_X - GAP, X_TOP - RECESS_T - GAP, BORE_R, mm(20), 16, `${OBST} ${DARK}`, { name: 'holder_boss' }));
  out.push(...tube(pp, [1, 0, 0], X_TOP - RECESS_T - GAP, X_TOP, RECESS_R, mm(20), 16, `${OBST} ${DARK}`, { name: 'holder_rim' }));
  out.push(`<geom type="cylinder" pos="${f(HOLDER_FLOOR_X - GAP - 0.002)} 0 ${f(ZP)}" size="${mm(20)} 0.002" euler="0 1.5708 0" ${OBST} ${DARK}/>`);
  // web between the two bosses (shown only)
  out.push(`<geom type="box" pos="${f(mm(40))} 0 ${f((ZH + ZP) / 2 - mm(8))}" size="${mm(10)} ${mm(18)} ${f((ZH - ZP) / 2)}" ${VIS} ${DARK}/>`);
  return [...world, `<body name="collar_frame" euler="0 0 ${f(PSI)}">`, ...out, '</body>'];
}

/** The tank as in the Pod grab scene: 700 (along y) x 400 (along x) x 300, hollow (4 mm walls and floor), a 4 mm lid with an access opening over the seedling tray, the 155 mm shelf, and the tray on two rails. */
function tank(): string[] {
  const out: string[] = [], hx = TANK_W / 2, hy = TANK_L / 2, glass = rgba(0.75, 0.77, 0.82, 0.35), lid = rgba(0.6, 0.62, 0.68);
  const box = (x0: number, x1: number, y0: number, y1: number, z0: number, z1: number, c: string) =>
    out.push(`<geom type="box" pos="${f((x0 + x1) / 2)} ${f((y0 + y1) / 2)} ${f((z0 + z1) / 2)}" size="${f((x1 - x0) / 2)} ${f((y1 - y0) / 2)} ${f((z1 - z0) / 2)}" ${OBST} ${c}/>`);
  const zl = LID - 0.004;
  box(-hx, hx, -hy, hy, 0, WALL, glass);                                                    // floor
  box(-hx, -hx + WALL, -hy, hy, WALL, zl, glass); box(hx - WALL, hx, -hy, hy, WALL, zl, glass);   // walls along y (at x = -/+ 0.2)
  box(-hx + WALL, hx - WALL, -hy, -hy + WALL, WALL, zl, glass); box(-hx + WALL, hx - WALL, hy - WALL, hy, WALL, zl, glass);   // walls along x
  box(-hx + WALL, hx - WALL, -hy + WALL, hy - WALL, SHELF_Z, SHELF_Z + SHELF_T, glass);       // shelf
  // lid: four slabs round the opening over the tray
  const ox0 = TRAY_X - OPEN_HX, ox1 = TRAY_X + OPEN_HX, oy0 = YC - OPEN_HY, oy1 = YC + OPEN_HY;
  box(-hx, ox0, -hy, hy, zl, LID, lid); box(ox1, hx, -hy, hy, zl, LID, lid);
  box(ox0, ox1, -hy, oy0, zl, LID, lid); box(ox0, ox1, oy1, hy, zl, LID, lid);
  // seedling tray: a thin plate on two rails over the shelf, three cells
  const trh = 0.045, tyh = 0.10;
  box(TRAY_X - trh, TRAY_X + trh, YC - tyh, YC + tyh, TRAY_Z0, TRAY_TOP, rgba(0.2, 0.62, 0.38));
  for (const sx of [-1, 1]) box(TRAY_X + sx * (trh - 0.006) - 0.004, TRAY_X + sx * (trh - 0.006) + 0.004, YC - tyh, YC + tyh, SHELF_Z + SHELF_T, TRAY_Z0, rgba(0.2, 0.62, 0.38));
  for (const y of TRAY_Y) out.push(...tube([TRAY_X, y, TRAY_TOP], [0, 0, 1], 0, CELL_H, CELL_RIN, CELL_RIN + mm(3), 12, `${OBST} ${rgba(0.95, 0.55, 0.2)}`));
  return out;
}

/** A pod or plug as geoms in its own frame: origin at the cap top, z axis into the pod. */
function podGeoms(bodyR: number, bodyL: number, color: string, dimple: boolean): string {
  return `<geom type="cylinder" pos="0 0 ${f(CAP_T / 2)}" size="${CAP_R} ${f(CAP_T / 2)}" contype="2" conaffinity="0" ${color}/>
      <geom type="cylinder" pos="0 0 ${f(CAP_T + bodyL / 2)}" size="${bodyR} ${f(bodyL / 2)}" contype="2" conaffinity="0" ${color}/>
      ${dimple ? `<geom type="cylinder" pos="0 0 0.0005" size="0.008 0.0006" ${VIS} ${rgba(0.05, 0.05, 0.06)}/>` : ''}`;
}
export const BODIES = { pod: 'seedling_pod', plug: 'plug', other: ['seedling_a', 'seedling_c'] } as const;
const podColor = rgba(0.85, 0.65, 0.3), plugColor = rgba(0.12, 0.12, 0.14);

/** The cart and what it carries (cart frame -> world axes), as the text to put inside the cart body. */
export function cartGeoms(): string[] {
  const out: string[] = [];
  // The real omni cart (cad/cart_base.py, hand_sleeve.py v5, cart_omni.py via cart/omni-scene.ts, exactly as in the Transfer scene, Pond #284): plate, battery, the two three-lobe sleeves with their omni wheels,
  // ball cups, motors and jaws, on the plate frame (CAD x across = world -y, CAD y out of the pipe plane = world x, z up). The arm is the scene's own moving one.
  // The cart is checked against the arm and the track: hand C rides the track leg, hand B hangs beside it with its jaw open. No hinges, nothing swings: the base is rigid on both sleeves.
  const cartParts = staticOmniCart({ free: 'B', col: OBST });
  out.push(`<body name="plate" xyaxes="0 -1 0 1 0 0"><joint name="plate_lock" type="hinge" axis="0 0 1" range="0 0"/>
      ${cartParts}
    </body>`);
  // pod holder: the cup on a web from the plate's bottom edge, axis 45 degrees out and up
  const root = cupRoot();
  out.push(...tube(root, D_CUP, 0, CUP_L - RECESS_T - GAP, BORE_R, CUP_R, 16, `${OBST} ${STEEL}`, { name: 'cup' }));
  out.push(...tube(root, D_CUP, CUP_L - RECESS_T - GAP, CUP_L, RECESS_R, CUP_R, 16, `${OBST} ${STEEL}`, { name: 'cup_rim' }));
  out.push(`<geom type="cylinder" pos="${f(root[0] + D_CUP[0] * mm(2))} ${f(root[1])} ${f(root[2] + D_CUP[2] * mm(2))}" size="${CUP_R} 0.002" xyaxes="${(() => { const [e1, e2] = basis(D_CUP); return [...e1, ...e2].map(f).join(' '); })()}" ${OBST} ${STEEL}/>`);
  const [wx, wy, wz] = cartToWorld(ARM_CX, mm(CART.plateFaceY - 12), mm(-75) - CUP_DROP / 2);
  out.push(`<geom type="box" pos="${f(wx)} ${f(wy)} ${f(wz)}" size="${mm(8)} ${mm(5)} ${f(mm(19) + CUP_DROP / 2)}" ${VIS} ${STEEL}/>`);
  return out;
}

/** The track: the unit's ONE track loop of cad/unit_v3_dimensioned.py, a rounded-corner PORTRAIT rectangle (tube radius 16 mm, corner radius 150 mm, legs 580 mm apart, bottom run at 514 mm (shared layout), top run at 1884 mm) standing
 *  in front of the central pipe, in the plane x = XT; plus what joins it to the spine: the spine tube (33.7 x 2, on the pipe axis, inside the growing pipe, up to the top run) and the two spine brackets (16 x 30 x 30 mm,
 *  at the top and at the bottom run, on the pipe's centre line), and the joint rings of cad/unit_v1_assembly.py (6 mm, r 17.5, at four heights on each leg; shown only, the wheel pairs ride over them flush). */
// OpenPocket #376: the bottom run is at the shared layout height (cad/layout.json: 514 mm), no local copy any more (it was 0.45, a guess). The scene was tuned to 0.45: the new height makes the sleeve lobe touch the bottom
// track corner at the old lowest stop and puts the seedling tray out of reach; sim.test.ts lists those checks as KNOWN_CLASH (see the pull request).
export const LOOP_TX = LEG, LOOP_R = CAD_UNIT.R / 1000, LOOP_ZB = CAD_UNIT.ZB / 1000, LOOP_ZT = CAD_UNIT.ZT / 1000, LOOP_TR = CAD_UNIT.TR / 1000;   // cad/parts/unit_dims.py (R 150, ZB = the shared layout's bottom run, ZT, TR 16)
export function track(): string[] {
  const out: string[] = [], r = LOOP_TR;
  const seg = (name: string, a: V3, b: V3) => out.push(`<geom name="${name}" type="cylinder" fromto="${a.map(f).join(' ')} ${b.map(f).join(' ')}" size="${r}" ${OBST} ${rgba(0.62, 0.66, 0.7)}/>`);
  for (const e of [-1, 1]) seg(`trackleg${e}`, [XT, e * LOOP_TX, LOOP_ZB + LOOP_R], [XT, e * LOOP_TX, LOOP_ZT - LOOP_R]);
  seg('tracktop', [XT, -LOOP_TX + LOOP_R, LOOP_ZT], [XT, LOOP_TX - LOOP_R, LOOP_ZT]);
  seg('trackbot', [XT, -LOOP_TX + LOOP_R, LOOP_ZB], [XT, LOOP_TX - LOOP_R, LOOP_ZB]);
  const N = 10;
  for (const [ex, ez] of [[1, 1], [-1, 1], [1, -1], [-1, -1]]) {   // four quarter-circle corners, N straight pieces each
    const ccy = ex * (LOOP_TX - LOOP_R), ccz = ez > 0 ? LOOP_ZT - LOOP_R : LOOP_ZB + LOOP_R;
    const pt = (k: number): V3 => [XT, ccy + ex * LOOP_R * Math.sin(k / N * Math.PI / 2), ccz + ez * LOOP_R * Math.cos(k / N * Math.PI / 2)];
    for (let k = 0; k < N; k++) seg(`trackc${ex}${ez}_${k}`, pt(k), pt(k + 1));
  }
  // joint rings: four per leg, from the bottom corner's end to the top one's (unit_v1_assembly.py jz)
  const zl = LOOP_ZB + LOOP_R, zh = LOOP_ZT - LOOP_R;
  for (const e of [-1, 1]) for (const k of [0, 1, 2, 3]) {
    const z = zl + (zh - zl) * k / 3;
    out.push(`<geom type="cylinder" fromto="${f(XT)} ${f(e * LOOP_TX)} ${f(z - 0.003)} ${f(XT)} ${f(e * LOOP_TX)} ${f(z + 0.003)}" size="${mm(17.5)}" ${VIS} ${rgba(0.95, 0.6, 0.2)}/>`);
  }
  // spine tube and the two brackets joining the track's top and bottom run to it
  out.push(...tube([0, 0, 0], [0, 0, 1], 0, ZT, mm(CAD_UNIT_DIMS.SP / 2 - 2), mm(CAD_UNIT_DIMS.SP / 2), 24, `${VIS} ${rgba(0.35, 0.35, 0.35)}`));
  for (const z of [LOOP_ZT, LOOP_ZB]) out.push(`<geom name="bracket${z === LOOP_ZT ? 'top' : 'bot'}" type="box" pos="${f(XT - mm(15))} 0 ${f(z)}" size="${mm(15)} ${mm(8)} ${mm(15)}" ${OBST} ${rgba(0.2, 0.2, 0.2)}/>`);
  return out;
}

/** MJCF of the whole scene. */
export function transplantMjcf(): string {
  const [qw, qx, qy, qz] = [1, 0, 0, 0];
  // free bodies (no gravity, never stepped): the scene writes their pose each frame, and having a degree of freedom is what lets MuJoCo test them against the static geoms
  const mocap = (name: string, pos: V3, geoms: string) => `<body name="${name}" pos="${pos.map(f).join(' ')}" quat="${qw} ${qx} ${qy} ${qz}"><joint type="free"/>${geoms}</body>`;
  const world = [
    `<geom name="floor" type="plane" size="1.6 1.2 0.01" pos="0 0 0" ${OBST} ${rgba(0.84, 0.88, 0.92)}/>`,
    ...pipeAndCollar(), ...track(),
    mocap(BODIES.pod, [0, 0, 2], podGeoms(POD_BODY_R, POD_BODY_L, podColor, false)),
    mocap(BODIES.plug, [0, 0, 2.2], podGeoms(PLUG_BODY_R, PLUG_BODY_L, plugColor, true)),
    mocap(BODIES.other[0], [0, 0, 2.4], podGeoms(POD_BODY_R, POD_BODY_L, podColor, false)),
    mocap(BODIES.other[1], [0, 0, 2.6], podGeoms(POD_BODY_R, POD_BODY_L, podColor, false)),
  ].join('\n    ');
  const base = `pos="${f(ARM_CY - BASE_BOTTOM)} 0 0" xyaxes="0 0 -1 0 -1 0"`;   // base x = down, base y = -y, so the base axis (z) points out of the plate, -x: towards the pipe
  const open = `<body name="cart" mocap="true" pos="${XT} ${YC} ${CART_Z0}">
      ${cartGeoms().join('\n      ')}`;
  return withCartAssets(armMjcf(world, {
    noGround: true,
    option: '<option timestep="0.004" gravity="0 0 0"/>',
    armCollides: true,
    mount: { open, close: '</body>' },
    baseAttrs: base,
  }));
}
