// Transplant scene layout: ONE pipe (the growing pipe, with its collar), the tank it stands on with the seedling tray on the tank lid, and the cart that rides on that same pipe with the arm.
// Metres. World frame: z up, pipe axis at x = y = 0, x from the pipe towards the cart's arm, y along the plate; the arm works in the plane y = 0.
//
// From the CAD (cad/pipe_collar.py, cad/cart_pod_holder.py, cad/cart_dims.py, cad/unit_v3_aframe.py; mm in the CAD, converted here):
//  - tank 700 x 400 x 300 with a 4 mm lid (top at 304 mm); growing pipe 75 mm OD, 3 mm wall, standing in a socket (OD 95) on the lid; hole 45 mm drilled square to the pipe (axis +x) at ZH
//  - collar: pod seat 26 mm bore on an axis 45 degrees UP from +x, through P0 = (RP - 1.5, 0, ZH); seat face at 23.7 mm along the axis, cap underside 21.7, the cap (34 x 8) stands 6 mm proud
//  - plug holder: a straight (horizontal, +x) blind socket of the same shape, 44 mm BELOW the hole, floor at x = 40, seat face at x = 54
//  - pod and plug: body 25 (plug 25.5) x 32 (plug 17), cap 34 x 8
//  - cart: plate 6 mm, battery 70 x 50 x 70 under the arm base, arm base on the plate centre (x = -12 in the CART frame); the arm base stands 102 mm out from the plate; pod holder: a cup of 42 mm / bore 26 mm, 40 mm long, axis 45 degrees out of the plate AND up
//  - the hand's pipe axis to the plate: the CAD hands sit on track pipes 290 mm from the growing pipe (TX in unit_v3_aframe.py). Here the cart has ONE hand, a ring sleeve round the growing pipe itself, and an outrigger from the ring
//    carries the plate so that the plate and arm stand exactly where they stand in the CAD, 290 mm from the pipe axis (XT).
// ASSUMED here (not in the repo): hole height ZH 0.80 m; the ring sleeve (inner R 75, outer R 83, 90 mm long: wide enough to slide over the collar) and its outrigger; the seedling tray (3 cells) on the tank lid;
// the cart is brought up past the collar (the ring slides over it) and works from 100 mm above the hole centre.
import { armMjcf } from '../model.ts';
import { cartInner } from '../cart/transfer-model.ts';
import { CART_COL } from '../cart/model.ts';
import * as D from '../cart/dims.ts';

const f = (n: number) => +n.toFixed(5);
const mm = (v: number) => v / 1000;
type V3 = [number, number, number];
export const S = Math.SQRT1_2;

// --- pod, plug (mm in the CAD)
export const POD_BODY_R = mm(12.5), POD_BODY_L = mm(32), CAP_R = mm(17), CAP_T = mm(8);
export const PLUG_BODY_R = mm(12.75), PLUG_BODY_L = mm(17);
export const BORE_R = mm(13);                         // seat bore 26 mm
export const RECESS_R = mm(17.6), RECESS_T = mm(2);   // cap recess 35.2 mm, 2 mm deep
export const PROUD = CAP_T - RECESS_T;                // 6 mm of cap stand proud of the seat face

// --- central pipe and collar
export const PIPE_RP = mm(37.5), PIPE_WALL = mm(3), PIPE_TOP = 1.55;
export const TANK_L = 0.7, TANK_W = 0.4, LID = 0.304;     // tank 700 x 400, lid top at 304 mm (unit_v3_aframe.py: TH 300 + 4)
export const SOCKET_R = PIPE_RP + mm(10);
export const DRILL_R = mm(22.5);
export const ZH = 0.80;                               // hole centre height (ASSUMED)
export const ZP = ZH - mm(44);                        // plug holder height
export const P0: V3 = [PIPE_RP - mm(1.5), 0, ZH];
export const D_SEAT: V3 = [S, 0, S];                  // pod seat axis, out of the pipe and up
export const U_CAP = mm(21.7), U_FACE = U_CAP + RECESS_T;
export const HOLDER_FLOOR_X = mm(40), X_TOP = mm(54), PARK_DX = mm(5);
const at = (p: V3, d: V3, u: number): V3 => [p[0] + d[0] * u, p[1] + d[1] * u, p[2] + d[2] * u];
/** Cap-top point of a pod or plug seated in the hole's seat (the point the hand grips), and the direction out of the seat. */
export const SEAT_CAP_TOP = at(P0, D_SEAT, U_CAP + CAP_T);
/** Cap-top of the plug parked in the straight holder: it stands PARK_DX further out than a seated one (blind floor). */
export const PARK_CAP_TOP: V3 = [X_TOP - RECESS_T + PARK_DX + CAP_T, 0, ZP];
export const D_PARK: V3 = [1, 0, 0];

// --- the cart (CART frame of cad/cart_dims.py: x across the pipes, y out of the pipe plane, plate on -y, z up the pipes)
export const XT = 0.55;                               // world x of the track pipes (the plane of the plate/hand axes), from the growing pipe axis (ASSUMED: the CAD's 0.29 m leaves the SO-101 out of reach of the collar, see check_transplant_reach.py)
export const ARM_CX = 0;                              // arm base centre across the plate (cad/cart_dims.py ARM_X = 0)
export const ARM_CY = mm(-102);                       // arm base underside (on the battery front)
export const BASE_BOTTOM = 0.0085;                    // the arm model's base origin is 8.5 mm out from the base underside (model.ts)
export const XB = XT + ARM_CY - BASE_BOTTOM;          // world x of the arm base origin; the base axis (z) points along -x
/** World offset (from the cart origin on the arm plane at the pipe plane) of a CART frame point (cx, cy, cz). */
export const cartToWorld = (cx: number, cy: number, cz: number): V3 => [cy, -(cx - ARM_CX), cz];
// pod holder cup (cart_pod_holder.py): axis out of the plate (cart -y) and up (+z), 45 degrees
export const CUP_ROOT: V3 = [ARM_CX, mm(-70), mm(-88)];
export const CUP_DROP = 0;                        // the cup is this much LOWER on the plate than in the CAD: at the CAD position its pod is under the arm base, out of reach
export const CUP_L = mm(40), CUP_R = mm(21);
/** Direction out of the cup, in world coordinates (out of the plate = world -x, and up). */
export const D_CUP: V3 = [-S, 0, S];
/** Cup root point and the cap-top point of a pod in the cup, as offsets from the cart origin (world axes). */
const cupRoot = (): V3 => cartToWorld(CUP_ROOT[0], CUP_ROOT[1], CUP_ROOT[2] - CUP_DROP);
export const CUP_CAP_TOP_REL: V3 = (() => { const r = cupRoot(); return at(r, D_CUP, CUP_L - RECESS_T + CAP_T); })();

// --- seedling tray
export const TRAY_X = XB - 0.19, TRAY_Y: number[] = [-0.06, 0, 0.06], TRAY_T = 0.010;   // on the tank lid, beside the pipe's socket, in the arm plane (ASSUMED)
export const CELL_RIN = mm(13), CELL_H = mm(30);
/** Cap-top of the seedling pod that is picked (middle cell). Standing on the tray, pod axis down. */
export const TRAY_CAP_TOP: V3 = [TRAY_X, 0, LID + TRAY_T + POD_BODY_L + CAP_T + 0.0003];

// --- cart heights (cart origin = arm base axis height), driving range
export const CART_Z0 = 0.60;                          // at the seedling tray
export const CART_Z1 = ZH + 0.10;                     // at the target hole: the ring sleeve rides above the collar (it cannot pass the pod seat)
export const CART_Z_MAX = 1.3;

// --- gripper (the stand-in hand of model.ts): the cap-top point on the pod axis, in the hand frame
export const GRIP_TX = 0.0785, GRIP_TZ = 0.011;
export const JAW_OPEN_DEG = 50, JAW_CAP_DEG = 30;

const rgba = (r: number, g: number, b: number, a = 1) => `rgba="${r} ${g} ${b} ${a}"`;
const OBST = 'contype="1" conaffinity="3" margin="0.001"';
const VIS = 'contype="0" conaffinity="0"';

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
function tube(p0: V3, a: V3, u0: number, u1: number, rIn: number, rOut: number, n: number, attrs: string, opts: { name?: string; chunk?: number; skip?: (px: number, py: number, pz: number) => boolean } = {}): string[] {
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

const GAP = 0.0005;   // seats end this far below a part's resting face, so a part seated or parked is clear of it (the CAD parts rest face to face)
const SILVER = rgba(0.62, 0.66, 0.7), DARK = rgba(0.3, 0.36, 0.45), STEEL = rgba(0.3, 0.32, 0.36);

/** The central pipe, drilled; the collar's two seats; the plug holder. Static, in world coordinates. */
function pipeAndCollar(): string[] {
  const out: string[] = [];
  const rIn = PIPE_RP - PIPE_WALL;
  // the 45 mm hole: slat pieces whose centre lies inside the drilled circle (in the y, z plane, on the +x side) are left out
  const inHole = (x: number, y: number, z: number) => x > 0 && Math.hypot(y, z - ZH) < DRILL_R + 0.0015;
  out.push(...tube([0, 0, LID], [0, 0, 1], 0, PIPE_TOP - LID, rIn, PIPE_RP, 48, `${OBST} ${rgba(0.93, 0.95, 0.97, 0.28)}`, { chunk: 0.003, skip: inHole, name: 'pipe' }).reduce<string[]>((acc, g) => { acc.push(g); return acc; }, []));
  // the tank (700 x 400 x 300, lid on top) and the pipe's socket on the lid
  out.push(`<geom type="box" pos="0 0 ${f((LID - 0.004) / 2)}" size="${TANK_L / 2} ${TANK_W / 2} ${f((LID - 0.004) / 2)}" ${OBST} ${rgba(0.75, 0.77, 0.82, 0.55)}/>`);
  out.push(`<geom type="box" pos="0 0 ${f(LID - 0.002)}" size="${TANK_L / 2} ${TANK_W / 2} 0.002" ${OBST} ${rgba(0.6, 0.62, 0.68)}/>`);
  out.push(...tube([0, 0, LID], [0, 0, 1], 0, 0.025, PIPE_RP + 0.001, SOCKET_R, 32, `${OBST} ${rgba(0.95, 0.6, 0.2)}`));
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
  return out;
}

/** Seedling tray with three cells on the tank lid. */
function tray(): string[] {
  const out: string[] = [];
  out.push(`<geom type="box" pos="${TRAY_X} 0 ${f(LID + TRAY_T / 2)}" size="0.05 0.12 ${TRAY_T / 2}" ${OBST} ${rgba(0.2, 0.62, 0.38)}/>`);
  for (const y of TRAY_Y) out.push(...tube([TRAY_X, y, LID + TRAY_T], [0, 0, 1], 0, CELL_H, CELL_RIN, CELL_RIN + mm(3), 12, `${OBST} ${rgba(0.95, 0.55, 0.2)}`));
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
function cartGeoms(): string[] {
  const out: string[] = [];
  // The real cart (cad/cart_base.py, cart_hinge.py, hand_sleeve.py via cart/transfer-model.ts, exactly as in the Transfer scene): plate, battery, drive motors, hinges, worm drives and
  // the two hands with their wheel pairs and jaws, on the plate frame (CAD x across = world -y, CAD y out of the pipe plane = world x, z up). The arm is the scene's own moving one.
  // The plate-side parts are checked against the arm; the hands ride the track pipes B and C (trackPipes()).
  const plateParts = cartInner(false, 'plate').replaceAll(CART_COL, OBST);
  out.push(`<body name="plate" xyaxes="0 -1 0 1 0 0"><joint name="plate_lock" type="hinge" axis="0 0 1" range="0 0"/>
      ${plateParts}
      ${cartInner(false, 'hands')}
    </body>`);
  // pod holder: the cup on a web from the plate's bottom edge, axis 45 degrees out and up
  const root = cupRoot();
  out.push(...tube(root, D_CUP, 0, CUP_L - RECESS_T - GAP, BORE_R, CUP_R, 16, `${OBST} ${STEEL}`, { name: 'cup' }));
  out.push(...tube(root, D_CUP, CUP_L - RECESS_T - GAP, CUP_L, RECESS_R, CUP_R, 16, `${OBST} ${STEEL}`, { name: 'cup_rim' }));
  out.push(`<geom type="cylinder" pos="${f(root[0] + D_CUP[0] * mm(2))} ${f(root[1])} ${f(root[2] + D_CUP[2] * mm(2))}" size="${CUP_R} 0.002" xyaxes="${(() => { const [e1, e2] = basis(D_CUP); return [...e1, ...e2].map(f).join(' '); })()}" ${OBST} ${STEEL}/>`);
  const [wx, wy, wz] = cartToWorld(ARM_CX, mm(-52) - mm(9), mm(-56) - (CUP_DROP + mm(32)) / 2);
  out.push(`<geom type="box" pos="${f(wx)} ${f(wy)} ${f(wz)}" size="${mm(5)} ${mm(28)} ${f((CUP_DROP + mm(32)) / 2 + mm(1))}" ${VIS} ${STEEL}/>`);
  return out;
}

/** The track: the Cart scene's two pipes B and C (16 mm radius, 120 mm apart, cad/cart_dims.py) running up beside the central pipe, in the track plane x = XT (the straight part only, no bend). */
function trackPipes(): string[] {
  const r = mm(16);
  return [D.PIPE_X.B, D.PIPE_X.C].map((px, i) => `<geom name="track${i ? 'C' : 'B'}" type="cylinder" fromto="${XT} ${f(-mm(px))} 0 ${XT} ${f(-mm(px))} ${PIPE_TOP}" size="${r}" ${OBST} ${rgba(0.62, 0.66, 0.7)}/>`);
}

/** MJCF of the whole scene. */
export function transplantMjcf(): string {
  const [qw, qx, qy, qz] = [1, 0, 0, 0];
  // free bodies (no gravity, never stepped): the scene writes their pose each frame, and having a degree of freedom is what lets MuJoCo test them against the static geoms
  const mocap = (name: string, pos: V3, geoms: string) => `<body name="${name}" pos="${pos.map(f).join(' ')}" quat="${qw} ${qx} ${qy} ${qz}"><joint type="free"/>${geoms}</body>`;
  const world = [
    `<geom name="floor" type="plane" size="1.6 1.2 0.01" pos="0 0 0" ${OBST} ${rgba(0.84, 0.88, 0.92)}/>`,
    ...pipeAndCollar(), ...tray(), ...trackPipes(),
    mocap(BODIES.pod, [0, 0, 2], podGeoms(POD_BODY_R, POD_BODY_L, podColor, false)),
    mocap(BODIES.plug, [0, 0, 2.2], podGeoms(PLUG_BODY_R, PLUG_BODY_L, plugColor, true)),
    mocap(BODIES.other[0], [0, 0, 2.4], podGeoms(POD_BODY_R, POD_BODY_L, podColor, false)),
    mocap(BODIES.other[1], [0, 0, 2.6], podGeoms(POD_BODY_R, POD_BODY_L, podColor, false)),
  ].join('\n    ');
  const base = `pos="${f(ARM_CY - BASE_BOTTOM)} 0 0" xyaxes="0 0 -1 0 -1 0"`;   // base x = down, base y = -y, so the base axis (z) points out of the plate, -x: towards the pipe
  const open = `<body name="cart" mocap="true" pos="${XT} 0 ${CART_Z0}">
      ${cartGeoms().join('\n      ')}`;
  return armMjcf(world, {
    noGround: true,
    option: '<option timestep="0.004" gravity="0 0 0"/>',
    armCollides: true,
    mount: { open, close: '</body>' },
    baseAttrs: base,
  });
}
