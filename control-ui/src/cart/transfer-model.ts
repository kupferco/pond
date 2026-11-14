// MJCF for the v2 transfer scene: four vertical pipes (A B C D), and the cart as drawn in cad/cart_base.py, cart_hinge.py and hand_sleeve.py:
// one rigid PLATE (a mocap body) with, on it, the arm base and arm, the battery on its shelf and the two drive motors; each of the two HANDS
// hangs on the plate through its own HINGE (axis parallel to the pipe, on the pad edge) and carries its sleeve, wheel pairs, clamp motor and the
// worm wheel of its hinge. The hinge worm and its motor ride on the plate. Frame: x across, y out of the pipe plane (plate on -y), z up the pipes.
import { CART_COL, handInner, rgba } from './model.ts';
import * as D from './dims.ts';

const m = (mm: number) => +(mm / 1000).toFixed(5);
const f = (n: number) => +n.toFixed(5);
const PLATE_COL = rgba([0.35, 0.35, 0.38]), BATT_COL = rgba([0.2, 0.45, 0.85]), MOTOR_COL = rgba([0.85, 0.25, 0.25]);
const HINGE_COL = rgba([0.9, 0.55, 0.15]), PAD_COL = rgba([0.95, 0.75, 0.2]), ARM_COL = rgba([0.88, 0.88, 0.9]);
const HIDDEN = 'rgba="0 0 0 0" contype="0" conaffinity="0"';
/** Heights (m): the hands' mid height at rest (TOP_S), how far the cart lifts on pipe C so the released hand clears its pipe's end (LIFT), and where each pipe ends. B and D end 5 mm above the sleeve top
 *  of a hand clamped at TOP_S; C goes on up past the lifted sleeve, so the hinge worm drives (62+ mm above the hands' mid height) swing over its end. */
export const TOP_S_M = 0.6, LIFT_M = 0.11;
export const PIPE_TOP_M: Record<D.PipeName, number> = { B: TOP_S_M + 0.05, D: TOP_S_M + 0.05, C: 0.9 };

/** Geoms in the plate frame (mm, CAD axes). */
const pbox = (name: string, cx: number, cy: number, cz: number, hx: number, hy: number, hz: number, col: string, extra = CART_COL) =>
  `<geom ${name ? `name="${name}" ` : ''}type="box" pos="${f(m(cx))} ${f(m(cy))} ${f(m(cz))}" size="${f(m(hx))} ${f(m(hy))} ${f(m(hz))}" ${col} ${extra}/>`;
/** A cylinder between two plate-frame points (mm). */
const pcyl = (name: string, a: number[], b: number[], r: number, col: string, extra = CART_COL) =>
  `<geom ${name ? `name="${name}" ` : ''}type="cylinder" fromto="${a.map((v) => f(m(v))).join(' ')} ${b.map((v) => f(m(v))).join(' ')}" size="${f(m(r))}" ${col} ${extra}/>`;

/** Hand-frame helpers: hand axes x_l = world z (along the pipe), y_l = -world y (towards the plate), z_l = world x. Points are given in CAD axes relative to the hand's pipe axis. */
const hbox = (name: string, cx: number, cy: number, cz: number, hx: number, hy: number, hz: number, col: string, extra = CART_COL) =>
  pbox(name, cz, -cy, cx, hz, hy, hx, col, extra);
/** A cylinder along the pipe in the hand frame, from pipe-axis distance a to b (mm), with its axis at CAD (x, y) relative to the pipe. */
const hcyl = (a: number, b: number, x: number, y: number, r: number, col: string, extra = CART_COL) =>
  `<geom type="cylinder" fromto="${f(m(a))} ${f(m(-y))} ${f(m(x))} ${f(m(b))} ${f(m(-y))} ${f(m(x))}" size="${f(m(r))}" ${col} ${extra}/>`;

function plateGeoms(): string {
  const g: string[] = [];
  const plateHx = (D.PLATE_X1 - D.PLATE_X0) / 2, plateCx = (D.PLATE_X1 + D.PLATE_X0) / 2;
  g.push(pbox('plate', plateCx, (D.PLATE_Y0 + D.PLATE_Y1) / 2, 0, plateHx, D.PLATE_T / 2, D.PLATE_ZH, PLATE_COL));
  // Battery shelf: a tongue of the plate above its top rim, and the battery on it, above the arm.
  g.push(pbox('shelf', D.ARM_X, (D.PLATE_Y0 + D.PLATE_Y1) / 2, (D.PLATE_ZH + D.BATT_Z + D.BATT[2] / 2) / 2, D.BATT[0] / 2, D.PLATE_T / 2, (D.BATT_Z + D.BATT[2] / 2 - D.PLATE_ZH) / 2, PLATE_COL));
  g.push(pbox('battery', D.ARM_X, D.PLATE_Y0 - D.BATT[1] / 2, D.BATT_Z, D.BATT[0] / 2, D.BATT[1] / 2, D.BATT[2] / 2, BATT_COL));
  // Drive motors: 28 x 55 mm, axis along the pipe, in saddles on the plate. Stacked one above the other at the plate's hand-2 end (110 of the plate's 112 mm),
  // not in a row as drawn: when the plate swings half a turn its front side faces the pipe plane, and a motor near the hand-1 end would run into hand 1's sleeve.
  for (const [h, zc] of [[1, -D.MOTOR_L / 2 - 1], [2, D.MOTOR_L / 2 + 1]] as const) {
    const x = D.MOTOR_B_X;
    g.push(pcyl(`motor_drive${h}`, [x, D.PLATE_Y0 - D.MOTOR_R, zc - D.MOTOR_L / 2], [x, D.PLATE_Y0 - D.MOTOR_R, zc + D.MOTOR_L / 2], D.MOTOR_R, MOTOR_COL));
    g.push(pbox('', x, D.PLATE_Y0 - D.MOTOR_R / 2, zc, 14, D.MOTOR_R / 2, 4, PLATE_COL));
  }
  // Arm base block (70 x 70 x 8) on the plate and the shoulder column that carries the arm's pivot.
  g.push(pbox('armbase', D.ARM_X, D.PLATE_Y0 - 4, 0, D.ARM_BASE_W / 2, 4, D.ARM_BASE_W / 2, ARM_COL));
  g.push(pbox('armcolumn', D.ARM_X, D.PLATE_Y0 - 8 - (D.SHOULDER_H - 8) / 2, 0, 22, (D.SHOULDER_H - 8) / 2, 24, ARM_COL));
  for (const h of [1, 2] as const) {
    const hx = D.hingeX(h), inward = h === 1 ? -1 : 1;
    // plate leaf (30 x 3 x 31) behind the plate, and its knuckle on the hinge axis
    g.push(pbox(`pleaf${h}`, hx + inward * 15, (D.LEAF_Y1 + D.PLATE_Y1) / 2, 0, 15, D.HINGE_LEAF_T / 2, 15.5, HINGE_COL));
    g.push(pcyl(`pknuckle${h}`, [hx, D.HINGE_Y, -15.5], [hx, D.HINGE_Y, 15.5], D.HINGE_R, HINGE_COL));
    // The worm, its bracket and its 28 x 55 mm motor (cart_hinge.py) are NOT modelled: placed as drawn (worm 24 mm in front of the hinge axis, motor outboard) they run into
    // the pipe when the plate folds back half a turn (the worm 3 mm, the motor 8 to 11 mm). Only the worm wheel on the hinge axis is drawn, on the hand.
  }
  return g.join('\n      ');
}

/** The hand's own parts in the hand frame: mounting pad, lugs to the sleeve wedge, sleeve leaf, its knuckles and the worm wheel of its hinge. */
function handHingeGeoms(h: 1 | 2): string {
  const g: string[] = [], hx = D.hingeX(h) - D.restPipeX(h);   // hinge axis x relative to the pipe
  const padCx = (D.PAD_X0 + D.PAD_X1) / 2, inward = h === 1 ? -1 : 1;
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

/** The arm on its base: shoulder pivot 88 mm out from the plate, three links in three lanes 26 mm apart, so it folds up as drawn in cart_arm.py (stowed). */
function armBodies(): string {
  const y = D.PLATE_Y0 - D.SHOULDER_H, lane = 26;
  const link = (name: string, len: number, col: string) => `<geom name="${name}" type="box" pos="0 0 ${f(m(len / 2))}" size="${f(m(9))} ${f(m(7))} ${f(m(len / 2))}" ${col} ${CART_COL}/>`;
  return `<body name="arm_upper" pos="${f(m(D.ARM_X))} ${f(m(y))} 0"><joint name="arm_lift" type="hinge" axis="1 0 0" range="-3.3 3.3"/>
        ${link('arm_l1', D.L1, ARM_COL)}
        <body name="arm_fore" pos="${f(m(lane))} 0 ${f(m(D.L1))}"><joint name="arm_elbow" type="hinge" axis="1 0 0" range="-3.3 3.3"/>
          ${link('arm_l2', D.L2, rgba([0.7, 0.72, 0.78]))}
          <body name="arm_grip" pos="${f(m(-2 * lane))} 0 ${f(m(D.L2))}"><joint name="arm_wrist" type="hinge" axis="1 0 0" range="-3.3 3.3"/>
            ${link('arm_l3', D.L3, rgba([0.55, 0.57, 0.62]))}
          </body>
        </body>
      </body>`;
}

/**
 * Pairs checked for contact between plate-side parts and the hands (MuJoCo skips parent/child geoms, and the hands are children of the plate, so these
 * are named explicitly): every plate-side solid against each hand's envelope, pad and lug. The hinge and its leaves touch by design and are left out.
 */
const PLATE_SOLIDS = ['plate', 'shelf', 'battery', 'armbase', 'armcolumn', 'arm_l1', 'arm_l2', 'arm_l3', 'motor_drive1', 'motor_drive2'];
export function plateHandPairs(): string {
  const out: string[] = [];
  for (const h of [1, 2]) for (const a of PLATE_SOLIDS) for (const b of [`env${h}`, `pad${h}`]) out.push(`<pair geom1="${a}" geom2="${b}" margin="0"/>`);
  return `<contact>${out.join('')}</contact>`;
}

export function pipesXml(): string {
  const pr = m(D.PIPE_R * 2) / 2;
  return (Object.keys(D.PIPE_X) as D.PipeName[]).map((n) =>
    `<geom name="pipe${n}" type="cylinder" fromto="${f(m(D.PIPE_X[n]))} 0 -0.05 ${f(m(D.PIPE_X[n]))} 0 ${PIPE_TOP_M[n]}" size="${pr}" rgba="0.62 0.66 0.70 1" contype="1" conaffinity="2"/>`).join('\n    ');
}

/** The cart: the plate (mocap) with arm, and the two hands on their hinges. Hand 1 rides the pipe at +x (C), hand 2 the one at -x (B). Neither hand is mirrored (as in the CAD). */
export function transferCartBody(): string {
  const hand = (h: 1 | 2) => {
    const hx = D.hingeX(h) - D.restPipeX(h);
    return `<body name="hand${h}" pos="${f(m(D.restPipeX(h)))} 0 0" xyaxes="0 0 1 0 -1 0">
      <joint name="hinge${h}" type="hinge" pos="0 ${f(m(-D.HINGE_Y))} ${f(m(hx))}" axis="1 0 0" range="-7 7" frictionloss="50" damping="2"/>
      ${handInner(h, false, 1)}
        ${handHingeGeoms(h)}
    </body>`;
  };
  // The mocap body "cart" carries the plate's pose. The plate sits on one locked dummy hinge: MuJoCo skips contacts between geoms that are all welded to the
  // world, so without a degree of freedom the plate-side parts (battery, motors, arm) would never be checked against the pipes.
  return `<body name="cart" mocap="true" pos="0 0 0.5"><body name="plate"><joint name="plate_lock" type="hinge" axis="0 0 1" range="0 0"/>
      ${plateGeoms()}
      ${armBodies()}
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
    <position name="hinge1" joint="hinge1" kp="200" ctrlrange="-7 7"/>
    <position name="hinge2" joint="hinge2" kp="200" ctrlrange="-7 7"/>
    <position name="clamp1" joint="h1p" kp="2000" ctrlrange="-0.006 0.04"/>
    <position name="clamp2" joint="h2p" kp="2000" ctrlrange="-0.006 0.04"/>
  </actuator>`;
}

export function transferMjcf(): string {
  return `
<mujoco model="pond_transfer_v2">
  <option timestep="0.002" gravity="0 0 -9.81"/>
  <worldbody>
    <geom name="floor" type="plane" pos="0 0 -0.05" size="1.2 0.9 0.1" rgba="0.82 0.86 0.9 1"/>
    ${pipesXml()}
    ${transferCartBody()}
  </worldbody>
  ${transferActuators()}
  ${plateHandPairs()}
</mujoco>`;
}
