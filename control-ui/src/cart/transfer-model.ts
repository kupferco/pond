// MJCF for the v2 transfer scene: the Cart scene's track (pipe B bending left, pipe C bending right), and the cart as drawn in cad/cart_base.py, cart_hinge.py and hand_sleeve.py:
// one rigid PLATE (a mocap body) with, on it, the arm base and arm, the battery on its shelf and the two drive motors; each of the two HANDS
// hangs on the plate through its own HINGE (axis parallel to the pipe, on the pad edge) and carries its sleeve, wheel pairs, clamp motor and the
// worm wheel of its hinge. The hinge worm and its motor ride on the plate. Frame: x across, y out of the pipe plane (plate on -y), z up the pipes.
import { CART_COL, pipeGeoms, rgba } from './model.ts';
import * as D from './dims.ts';

const m = (mm: number) => +(mm / 1000).toFixed(5);
const f = (n: number) => +n.toFixed(5);
const PLATE_COL = rgba([0.35, 0.35, 0.38]), BATT_COL = rgba([0.2, 0.45, 0.85]), MOTOR_COL = rgba([0.85, 0.25, 0.25]);
const HINGE_COL = rgba([0.9, 0.55, 0.15]), PAD_COL = rgba([0.95, 0.75, 0.2]), ARM_COL = rgba([0.88, 0.88, 0.9]);
const HIDDEN = 'rgba="0 0 0 0" contype="0" conaffinity="0"';
/** World frame of the scene: the CAD frame as it is. The pipes stand upright as in the Cart scene (CAD x across the pipes is world x, B on the left, CAD y out of the pipe plane is
 *  world y, the plate hangs on the -y side, CAD z along the pipes is world z). The track is the Cart scene's own: pipe B bends LEFT at the top, pipe C bends RIGHT (pipeGeoms). */
export const S_MIN_CM = 15, S_MAX_CM = 50, S_START_CM = 30;   // where the hands' mid point may be along the pipes (cm): the straight parts; S_MAX_CM is the top of the straight part, just below the start of the bends (where the cart waits, hands at the top of pipes B and C)
export const TRACK_HORIZ_MM = 450;                            // length of the top bars (shortened, as in the earlier Transfer scene)
/** CAD-frame point (m) to world. */
export const cadToWorld = (v: [number, number, number]): [number, number, number] => [v[0], v[1], v[2]];
/** World point back to the CAD frame (m). */
export const worldToCad = (v: ArrayLike<number>): [number, number, number] => [v[0], v[1], v[2]];

/** Geoms in the plate frame (mm, CAD axes). */
const pbox = (name: string, cx: number, cy: number, cz: number, hx: number, hy: number, hz: number, col: string, extra = CART_COL) =>
  `<geom ${name ? `name="${name}" ` : ''}type="box" pos="${f(m(cx))} ${f(m(cy))} ${f(m(cz))}" size="${f(m(hx))} ${f(m(hy))} ${f(m(hz))}" ${col} ${extra}/>`;
/** A cylinder between two plate-frame points (mm). */
const pcyl = (name: string, a: number[], b: number[], r: number, col: string, extra = CART_COL) =>
  `<geom ${name ? `name="${name}" ` : ''}type="cylinder" fromto="${a.map((v) => f(m(v))).join(' ')} ${b.map((v) => f(m(v))).join(' ')}" size="${f(m(r))}" ${col} ${extra}/>`;

/** Hand C is the TRUE MIRROR of hand B across x = 0 (cad/cart_sleeves.py place_hand, Pond #227). Every hand is built as hand B (pad on -x, C gap towards +x, i.e. towards the plate); for hand C
 *  the generators below flip the hand frame's z (= CAD x) through MZ, which is set by the caller for the hand being built (1 = hand B, -1 = hand C). */
let MZ = 1;
/** Hand-frame helpers: hand axes x_l = world z (along the pipe), y_l = -world y (towards the plate), z_l = world x. Points are given in CAD axes relative to the hand's pipe axis. */
const hbox = (name: string, cx: number, cy: number, cz: number, hx: number, hy: number, hz: number, col: string, extra = CART_COL) =>
  pbox(name, cz * MZ, -cy, cx, hz, hy, hx, col, extra);
/** A cylinder along the pipe in the hand frame, from pipe-axis distance a to b (mm), with its axis at CAD (x, y) relative to the pipe. */
const hcyl = (a: number, b: number, x: number, y: number, r: number, col: string, extra = CART_COL) =>
  `<geom type="cylinder" fromto="${f(m(a))} ${f(m(-y))} ${f(m(x * MZ))} ${f(m(b))} ${f(m(-y))} ${f(m(x * MZ))}" size="${f(m(r))}" ${col} ${extra}/>`;

function plateGeoms(): string {
  const g: string[] = [];
  const plateHx = (D.PLATE_X1 - D.PLATE_X0) / 2, plateCx = (D.PLATE_X1 + D.PLATE_X0) / 2, plateCy = (D.PLATE_Y0 + D.PLATE_Y1) / 2;
  // v4 plate (cad/cart_base.py): a plain rectangle (no battery tongue), plus a small tongue above its top rim at each hinge that carries the worm bracket.
  g.push(pbox('plate', plateCx, plateCy, 0, plateHx, D.PLATE_T / 2, D.PLATE_ZH, PLATE_COL));
  // Stack out from the plate (cart_dims.py, v3): plate | battery | SO-101 arm base. The battery sits UNDER the arm, same x and z as the arm base.
  g.push(pbox('battery', D.BATT_X, D.PLATE_Y0 - D.BATT[1] / 2, D.BATT_Z, D.BATT[0] / 2, D.BATT[1] / 2, D.BATT[2] / 2, BATT_COL));
  // Drive motors: 28 x 55 mm, axis along the pipe, in a row with the arm as drawn (motor B at x -53, motor C at x +53), in saddles on the plate.
  for (const [h, x] of [[2, D.MOTOR_B_X], [1, D.MOTOR_C_X]] as const) {
    g.push(pcyl(`motor_drive${h}`, [x, D.PLATE_Y0 - D.MOTOR_R, -D.MOTOR_L / 2], [x, D.PLATE_Y0 - D.MOTOR_R, D.MOTOR_L / 2], D.MOTOR_R, MOTOR_COL));
    g.push(pbox('', x, D.PLATE_Y0 - D.MOTOR_R / 2, 0, 14, D.MOTOR_R / 2, 20, PLATE_COL));
  }
  // Arm base block (70 x 70 x 8) bolted to the battery's front face, and the shoulder column that carries the arm's pivot.
  g.push(pbox('armbase', D.ARM_X, D.ARM_Y0 - 4, 0, D.ARM_BASE_W / 2, 4, D.ARM_BASE_W / 2, ARM_COL));
  g.push(pbox('armcolumn', D.ARM_X, D.ARM_Y0 - 8 - (D.SHOULDER_H - 8) / 2, 0, 22, (D.SHOULDER_H - 8) / 2, 24, ARM_COL));
  for (const h of [1, 2] as const) {
    const hx = D.hingeX(h), inward = h === 1 ? -1 : 1;   // inward: towards the plate along x (+1 for hand B's hinge, -1 for C's)
    // plate leaf (30 x 3 x 31) behind the plate, and its knuckle on the hinge axis
    g.push(pbox(`pleaf${h}`, hx + inward * 15, (D.LEAF_Y1 + D.PLATE_Y1) / 2, 0, 15, D.HINGE_LEAF_T / 2, 15.5, HINGE_COL));
    g.push(pcyl(`pknuckle${h}`, [hx, D.HINGE_Y, -15.5], [hx, D.HINGE_Y, 15.5], D.HINGE_R, HINGE_COL));
    // Worm drive of this hinge (cart_hinge.py): tongue on the plate above its top rim, bracket (inboard bearing block, outboard motor face plate, bridge over the wheel),
    // the worm on its axis along x 24 mm in front of the hinge axis, and the 28 x 55 mm worm motor outboard. The worm wheel is on the hand (handHingeGeoms).
    const x0 = hx + inward * D.TONGUE_DX0, wy = D.HINGE_Y - D.CENTRE_DIST, brkY0 = D.PLATE_Y0, brkY1 = -82, brkT = 5;
    const xi = hx + inward * (D.TONGUE_DX0 + brkT / 2), xo = hx - inward * (D.TONGUE_DX0 + brkT / 2), xf = hx - inward * (D.TONGUE_DX0 + brkT);
    g.push(pbox(`tongue${h}`, x0 + inward * D.TONGUE_W / 2, plateCy, (D.PLATE_ZH + D.TONGUE_Z1) / 2, D.TONGUE_W / 2, D.PLATE_T / 2, (D.TONGUE_Z1 - D.PLATE_ZH) / 2, PLATE_COL));
    const bz0 = D.WORM_ZC - 14, bz1 = D.WORM_ZC + 14, by = (brkY0 + brkY1) / 2, bhy = Math.abs(brkY1 - brkY0) / 2;
    g.push(pbox(`bracket_in${h}`, xi, by, (bz0 + bz1) / 2, brkT / 2, bhy, (bz1 - bz0) / 2, HINGE_COL));
    g.push(pbox(`bracket_out${h}`, xo, by, (bz0 + bz1) / 2, brkT / 2, bhy, (bz1 - bz0) / 2, HINGE_COL));
    g.push(pbox(`bracket_bridge${h}`, (xi + xo) / 2, by, bz1 - 2, Math.abs(xi - xo) / 2 + brkT / 2, bhy, 2, HINGE_COL));
    g.push(pcyl(`worm${h}`, [Math.min(xi, xo) + 2, wy, D.WORM_ZC], [Math.max(xi, xo) - 2, wy, D.WORM_ZC], D.WORM_OD / 2, rgba([0.7, 0.7, 0.75])));
    g.push(pcyl(`worm_motor${h}`, [xf, wy, D.WORM_ZC], [xf - inward * D.MOTOR_L, wy, D.WORM_ZC], D.MOTOR_R, MOTOR_COL));
  }
  return g.join('\n      ');
}

/** The hand's own parts in the hand frame: mounting pad, lugs to the sleeve wedge, sleeve leaf, its knuckles and the worm wheel of its hinge. */
function handHingeGeoms(h: 1 | 2): string {
  const g: string[] = [], hx = D.HINGE_OFF_B;   // hinge axis x relative to the pipe, in hand B's frame (hand C is built mirrored through MZ)
  const padCx = (D.PAD_X0 + D.PAD_X1) / 2, inward = 1;
  g.push(hbox(`pad${h}`, padCx, (D.PAD_Y0 + D.PAD_Y1) / 2, 0, (D.PAD_X1 - D.PAD_X0) / 2, (D.PAD_Y1 - D.PAD_Y0) / 2, D.SLEEVE_L / 2, PAD_COL));
  g.push(hbox(`lug${h}`, D.PAD_X0 - 5, -16, 0, 5, 8, D.SLEEVE_L / 2, PAD_COL));   // bolted lug from the pad's inner edge down onto the sleeve wedge
  g.push(hbox(`leaf${h}`, hx + inward * 15, (D.LEAF_Y1 + D.PAD_Y0) / 2, 0, 15, D.HINGE_LEAF_T / 2, D.KNUCKLE_Z, HINGE_COL));
  // sleeve knuckles (along the pipe 16.5..45 and -45..-16.5) and the worm wheel on the hinge axis above the sleeve, fixed to the top knuckle by its hub
  g.push(hcyl(16.5, D.KNUCKLE_Z, hx, D.HINGE_Y, D.HINGE_R, HINGE_COL), hcyl(-D.KNUCKLE_Z, -16.5, hx, D.HINGE_Y, D.HINGE_R, HINGE_COL));
  g.push(hcyl(D.KNUCKLE_Z, D.WHEEL_Z0, hx, D.HINGE_Y, 3, HINGE_COL), hcyl(D.WHEEL_Z0, D.WHEEL_Z0 + D.WHEEL_T, hx, D.HINGE_Y, D.WHEEL_OD / 2, rgba([0.85, 0.7, 0.2])));
  // envelope of the hand for plate-versus-hand checks (never drawn): the sleeve cylinder
  g.push(`<geom name="env${h}" type="cylinder" fromto="${f(m(-D.SLEEVE_L / 2))} 0 0 ${f(m(D.SLEEVE_L / 2))} 0 0" size="${f(m(D.SLEEVE_R))}" ${HIDDEN}/>`);
  return g.join('\n        ');
}

// ---- The hand (cad/cart_sleeves.py v4): the sleeve split by a wedge into a FIXED BODY and a JAW on a knuckle hinge (pin along the pipe at the wedge's 110 deg edge), the jaw
// carrying the +60 deg idler pair and driven by its own micro motor on the +x end. Six wheels: driven pair at 180 deg (spins under the drive motor), idler pair at -60 deg
// (fixed), idler pair at +60 deg (on the jaw). Angles are CAD angles from +X (the C gap), points are given in the hand frame (x along the pipe, y = -CAD y, z = CAD x).
const WALL = rgba([0.95, 0.75, 0.2, 0.45]), JAW_COL = rgba([0.95, 0.5, 0.15, 0.55]), TYRE = rgba([0.12, 0.12, 0.12]), STEELC = rgba([0.8, 0.8, 0.82]), JMOTOR = rgba([0.1, 0.55, 0.3]);
const SEG_DEG = 10, GAP_A = 340;                                   // sleeve wall boxes are 10 deg wide; the C gap is 340..20 deg (the funnel mouth, ~18 mm at the narrow middle)
const radial = (deg: number): [number, number] => [-Math.sin((deg * Math.PI) / 180), MZ * Math.cos((deg * Math.PI) / 180)];   // (y, z) of the radial direction in the hand frame
const JAW_PIVOT: [number, number] = [D.SLEEVE_R * Math.cos((D.JAW_A1 * Math.PI) / 180), D.SLEEVE_R * Math.sin((D.JAW_A1 * Math.PI) / 180)];   // CAD (x, y) of the jaw pin
/** The sleeve wall of the angle range [a0, a1) (deg) as boxes, open at the wheel pockets (near `pockets` angles) and in the end walls closed. */
function wallGeoms(a0: number, a1: number, pockets: number[], col: string): string[] {
  const g: string[] = [], rc = (D.R_BORE + D.SLEEVE_R) / 2, half = D.SLEEVE_L / 2;
  const near = (deg: number) => pockets.some((p) => Math.abs(((deg - p + 540) % 360) - 180) > 180 - 17);
  const ring = (x0: number, x1: number, skip: boolean) => {
    for (let a = a0; a < a1 - 1e-9; a += SEG_DEG) {
      const mid = a + SEG_DEG / 2; if (skip && near(mid)) continue;
      const [uy, uz] = radial(mid);
      g.push(`<geom type="box" pos="${f(m((x0 + x1) / 2))} ${f(m(rc) * uy)} ${f(m(rc) * uz)}" xyaxes="1 0 0 0 ${f(uy)} ${f(uz)}" size="${f(m(x1 - x0) / 2)} ${f(m(D.SLEEVE_R - D.R_BORE) / 2)} ${f(m(rc) * Math.tan((SEG_DEG * Math.PI) / 360))}" ${col} ${CART_COL}/>`);
    }
  };
  ring(-half, -41, false); ring(41, half, false); ring(-41, -19, true); ring(19, 41, true); ring(-19, 19, false);
  return g;
}
/** One wheel pair at CAD angle `deg`: two wheels (rows +-30) with axle pins out to the sleeve wall. spin = joint name prefix to make the pair spin (driven pair), else rigid. */
function wheelPairGeoms(h: number, deg: number, spin: boolean): string[] {
  const [uy, uz] = radial(deg), ty = -uz, tz = uy, r = D.AXLE_R_POS + 0.3;
  const at = (x: number, rr: number, t: number) => `${f(m(x))} ${f(m(rr * uy + t * ty))} ${f(m(rr * uz + t * tz))}`;
  const out: string[] = [];
  for (const row of [D.RING_Z, -D.RING_Z]) {
    const name = `w${h}${row > 0 ? 'f' : 'b'}`;
    const geoms = [`<geom type="cylinder" fromto="${at(row, r, -D.WHEEL_W / 2)} ${at(row, r, D.WHEEL_W / 2)}" size="${f(m(D.WHEEL_R))}" ${TYRE} ${CART_COL}/>`,
      `<geom type="cylinder" fromto="${at(row, r, -11)} ${at(row, r, 11)}" size="${f(m(1.6))}" ${STEELC} ${CART_COL}/>`];   // axle pin, 11 mm each side: it reaches the pocket walls
    out.push(spin ? `<body name="${name}"><joint name="${name}" type="hinge" pos="${at(row, r, 0)}" axis="0 ${f(-uz)} ${f(uy)}" range="-100000 100000"/>${geoms.join('')}</body>` : geoms.join(''));
  }
  return out;
}
/** Hand h's sleeve, wheels and jaw, in the hand frame (child geoms of body hand<h>, with the jaw as a child body on its hinge). */
function sleeveJawGeoms(h: 1 | 2): string {
  const half = D.SLEEVE_L / 2, p = JAW_PIVOT, py = -p[1], pz = p[0] * MZ;   // hand-frame (y, z) of the jaw pin
  const knuckle = (x0: number, x1: number, r: number, col: string) => `<geom type="cylinder" fromto="${f(m(x0))} ${f(m(py))} ${f(m(pz))} ${f(m(x1))} ${f(m(py))} ${f(m(pz))}" size="${f(m(r))}" ${col} ${CART_COL}/>`;
  const fixed = [...wallGeoms(D.JAW_A1, GAP_A, [180, -60], WALL),
    ...wheelPairGeoms(h, 180, true), ...wheelPairGeoms(h, -60, false),
    knuckle(-D.LUG_FIXED_Z, D.LUG_FIXED_Z, D.LUG_R, HINGE_COL),
    // jaw actuator (cart_sleeves.py item 11): gearbox and micro motor coaxial with the pin on the +x end, rigid with the fixed body (the shaft turns the jaw)
    knuckle(half, half + D.JAW_GB_L, D.JAW_GB_R, JMOTOR), knuckle(half + D.JAW_GB_L, half + D.JAW_GB_L + D.JAW_MOTOR_L, D.JAW_MOTOR_R, JMOTOR)];
  const jaw = [...wallGeoms(20, D.JAW_A1, [D.JAW_WHEEL_ANG], JAW_COL), ...wheelPairGeoms(h, D.JAW_WHEEL_ANG, false),
    knuckle(D.LUG_FIXED_Z + 1, half, D.LUG_R, HINGE_COL), knuckle(-half, -D.LUG_FIXED_Z - 1, D.LUG_R, HINGE_COL),
    knuckle(-half - 2, half + 2, D.JAW_PIN_R, STEELC)];
  return `${fixed.join('\n        ')}
        <body name="jaw${h}"><joint name="jaw${h}" type="hinge" pos="0 ${f(m(py))} ${f(m(pz))}" axis="${MZ} 0 0" range="0 ${D.JAW_OPEN}" frictionloss="5" damping="0.2"/>
        ${jaw.join('\n        ')}
        </body>`;
}
export const JAW_OPEN_RAD = (D.JAW_OPEN * Math.PI) / 180;

/**
 * The arm on its base, stowed as drawn in cart_arm.py (shoulder pivot 88 mm out from the plate, three links in three lanes 26 mm apart, folded up). Rigid on the plate:
 * the arm does not move in a transfer, so it is plain geoms (no joints), with the elbow and wrist pins joining the lanes so nothing floats.
 */
function armGeoms(): string {
  const y = D.ARM_Y0 - D.SHOULDER_H, lane = 26, x0 = D.ARM_X;
  const link = (name: string, x: number, z0: number, z1: number, col: string) => pbox(name, x, y, (z0 + z1) / 2, 9, 7, Math.abs(z1 - z0) / 2, col);
  const pin = (name: string, xa: number, xb: number, z: number) => pcyl(name, [xa, y, z], [xb, y, z], 6, ARM_COL);
  return [
    link('arm_l1', x0, 0, D.L1, ARM_COL),
    link('arm_l2', x0 + lane, D.L1 - D.L2, D.L1, rgba([0.7, 0.72, 0.78])),
    link('arm_l3', x0 - lane, D.L1 - D.L2, D.L1 - D.L2 + D.L3, rgba([0.55, 0.57, 0.62])),
    pin('arm_pin1', x0 - 9, x0 + lane + 9, D.L1),            // elbow: joins links 1 and 2
    pin('arm_pin2', x0 - lane - 9, x0 + lane + 9, D.L1 - D.L2),   // wrist: joins links 2 and 3
  ].join('\n      ');
}

/**
 * Pairs checked for contact between plate-side parts and the hands (MuJoCo skips parent/child geoms, and the hands are children of the plate, so these
 * are named explicitly): every plate-side solid against each hand's envelope, pad and lug. The hinge and its leaves touch by design and are left out.
 */
const PLATE_SOLIDS = ['plate', 'battery', 'armbase', 'armcolumn', 'arm_l1', 'arm_l2', 'arm_l3', 'arm_pin1', 'arm_pin2', 'motor_drive1', 'motor_drive2'];
export function plateHandPairs(): string {
  const out: string[] = [];
  for (const h of [1, 2]) for (const a of PLATE_SOLIDS) for (const b of [`env${h}`, `pad${h}`]) out.push(`<pair geom1="${a}" geom2="${b}" margin="0"/>`);
  return `<contact>${out.join('')}</contact>`;
}

/** The track, from the Cart scene's pipeGeoms: pipe B runs up and bends LEFT, pipe C runs up and bends RIGHT (both with their top bars). Only these two pipes exist. */
export function pipesXml(): string {
  return [pipeGeoms(m(D.PIPE_X.B), -1, TRACK_HORIZ_MM, 'pipeB'), pipeGeoms(m(D.PIPE_X.C), 1, TRACK_HORIZ_MM, 'pipeC')].join('\n    ');
}

/** The cart: the plate (mocap) with arm, and the two hands on their hinges. Hand 1 rides the pipe at +x (C), hand 2 the one at -x (B). Hand C is the true mirror of hand B (as in the CAD since Pond #227). */
export function transferCartBody(): string {
  const hand = (h: 1 | 2) => {
    const hx = D.hingeX(h) - D.restPipeX(h);
    MZ = h === 1 ? -1 : 1;   // hand C (1) is built as the mirror of hand B (2)
    const body = `<body name="hand${h}" pos="${f(m(D.restPipeX(h)))} 0 0" xyaxes="0 0 1 0 -1 0">
      <joint name="hinge${h}" type="hinge" pos="0 ${f(m(-D.HINGE_Y))} ${f(m(hx))}" axis="1 0 0" range="-30 30" frictionloss="50" damping="2"/>
      ${sleeveJawGeoms(h)}
        ${handHingeGeoms(h)}
    </body>`;
    MZ = 1;
    return body;
  };
  // The mocap body "cart" carries the plate's pose. The plate sits on one locked dummy hinge: MuJoCo skips contacts between geoms that are all welded to the
  // world, so without a degree of freedom the plate-side parts (battery, motors, arm) would never be checked against the pipes.
  return `<body name="cart" mocap="true" pos="0 0 0.5"><body name="plate"><joint name="plate_lock" type="hinge" axis="0 0 1" range="0 0"/>
      ${plateGeoms()}
      ${armGeoms()}
      ${hand(1)}
      ${hand(2)}
    </body></body>`;
}

export function transferActuators(): string {
  const tendon = (n: string, j: string[]) => `<fixed name="${n}">${j.map((x) => `<joint joint="${x}" coef="0.5"/>`).join('')}</fixed>`;
  return `<tendon>
    ${tendon('drive1', ['w1f', 'w1b'])}
    ${tendon('drive2', ['w2f', 'w2b'])}
  </tendon>
  <actuator>
    <position name="drive1" tendon="drive1" kp="2" ctrlrange="-100000 100000"/>
    <position name="drive2" tendon="drive2" kp="2" ctrlrange="-100000 100000"/>
    <position name="hinge1" joint="hinge1" kp="200" ctrlrange="-0.6 0.6"/>
    <position name="hinge2" joint="hinge2" kp="200" ctrlrange="-0.6 0.6"/>
    <position name="jaw1" joint="jaw1" kp="2" ctrlrange="0 ${JAW_OPEN_RAD}"/>
    <position name="jaw2" joint="jaw2" kp="2" ctrlrange="0 ${JAW_OPEN_RAD}"/>
  </actuator>`;
}

export function transferMjcf(): string {
  return `
<mujoco model="pond_transfer_v2">
  <option timestep="0.002" gravity="0 0 -9.81"/>
  <worldbody>
    <geom name="floor" type="plane" pos="0.05 0 -0.05" size="1.4 0.9 0.1" rgba="0.82 0.86 0.9 1"/>
    ${pipesXml()}
    ${transferCartBody()}
  </worldbody>
  ${transferActuators()}
  ${plateHandPairs()}
</mujoco>`;
}
