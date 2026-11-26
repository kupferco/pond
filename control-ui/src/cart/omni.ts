// The omni-wheel cart for MuJoCo (OpenPocket #281, plan task 265 part 7, docs/plans/cart-roll-redesign-plan.md sections 3 to 5 and 10).
// It replaces the hinge-era cart in model.ts / dims.ts, which stay in place only until the scene parts of the plan (cart on track, transfer,
// pod grab, transplant) move over to this file; they are marked LEGACY and are deleted with the last scene that uses them.
//
// What it models, from the CAD (cad/hand_sleeve.py v5, cad/cart_omni.py, cad/cart_dims.py v3; the Python files are the source of truth,
// test/sim.test.ts reads them and fails if a number here drifts):
//  - a RIGID base: plate bolted flat on both sleeve pads, battery and arm base on it. No hinges, no tongues, no worm drives.
//  - two three-lobe sleeves, hand B on pipe B (x = -60) and hand C its true mirror on pipe C (x = +60): one outer lobe (180 deg for B) with the two
//    driven 38 mm omni wheels (DRIVE wheel top row, ROLL wheel bottom row, axle along the pipe), two +/-60 deg lobes with four passive ball cups.
//  - a ROLL joint per sleeve (about that pipe's axis) with a roll actuator, and a spin joint with an actuator for each driven wheel.
// Frame (the CAD hand frame): pipes along z (up), x across (pipe B at -60, pipe C at +60), y out of the pipe plane, the plate on the -y side.
//
// Omni friction model. MuJoCo's contact friction is isotropic (one sliding coefficient per contact, no per-geom roller axis), so the omni wheel is
// split in two: in the MJCF the driven wheels are cylinders with the grip coefficient and the passive balls nearly frictionless, and the
// anisotropy (grip in the rolling direction, almost none across it) is the function omniContact() below, which the scenes and tests use for
// every traction question. This part does not simulate the traction as a contact force: the cart is a mocap body like the legacy one and the scenes
// set the joints, as before. A force level traction sim is the render-server work (plan task 12, sim/pipe_climb.py).
import { CAD_CONSTANTS } from '../generated/cad-sim.ts';
import { cartMeshGeoms, withCartAssets } from './cad-cart.ts';
const m = (mm: number) => +(mm / 1000).toFixed(5);
const f = (n: number) => +n.toFixed(5);
const rad = (deg: number) => (deg * Math.PI) / 180;

// ---------------- Numbers from the CAD (mm) ----------------
// Every number below is READ from the CAD sources by cad/export_sim_model.py (control-ui/src/generated/cad-sim.ts), not typed in here (OpenPocket #447):
// change the CAD, re-run the export, and the sim follows. cad/check_sim_matches_cad.py and test/sim.test.ts fail if the generated file or this block drifts.
const HS = CAD_CONSTANTS.hand_sleeve, CD = CAD_CONSTANTS.cart_dims, CO = CAD_CONSTANTS.cart_omni, CSL = CAD_CONSTANTS.cart_sleeves;
export const PIPE_SPACING: number = CD.PIPE_SPACING;
export const HX = PIPE_SPACING / 2;
export const R_PIPE: number = CO.R_PIPE;            // 32 mm track pipe
export const OMNI_R: number = CO.OMNI_R;            // 38 mm driven omni wheel
export const OMNI_W: number = CO.OMNI_W;            // hub width
export const OMNI_AXLE_R = R_PIPE + OMNI_R;         // 35: wheel centre from the pipe axis
export const OMNI_REACH = OMNI_AXLE_R + OMNI_R;     // 54
export const ROW_Z: number = HS.ROW_Z;              // wheel rows at z = +/-38 (76 apart)
export const DRIVE_Z: number = HS.DRIVE_Z, ROLL_Z: number = HS.ROLL_Z;   // drive wheel in the top row, roll wheel in the bottom row
export const SLEEVE_L: number = HS.SLEEVE_L;
export const R_BORE: number = HS.R_BORE, TUBE_R_MIN: number = HS.TUBE_R_MIN, END_WALL: number = HS.END_WALL;
export const R_ARM_OMNI: number = HS.R_ARM_OMNI, ARM_W_OMNI: number = HS.ARM_W_OMNI;    // outer lobe (180 deg): wheels, 61 mm outer radius
export const R_ARM_CUP: number = HS.R_ARM_CUP, ARM_W_CUP: number = HS.ARM_W_CUP;        // the +/-60 deg lobes
export const INNER_ANG: number = HS.INNER_ANGS[0];  // deg, the two ball-cup lobes either side of the C gap (+X for hand B)
export const BALL_D: number = CO.BALL_D, CUP_R = HS.BORE_CUP_D / 2 - 0.3, CUP_BACK: number = HS.CARRIER_R0, BALL_CENTRE_R = R_PIPE + BALL_D / 2, FACE_R = R_PIPE + CO.FACE_GAP;
export const JAW_A0: number = CSL.JAW_A0, JAW_A1: number = CSL.JAW_A1, JAW_OPEN_DEG: number = CSL.JAW_OPEN;   // cart_sleeves.py: the jaw wall from the middle of the C gap (0) to 110 deg swings open 92 deg on a pin at the 110 deg edge
export const JAW_OPEN_RAD = (JAW_OPEN_DEG * Math.PI) / 180;
export const GAP_HALF_DEG = 20;                     // the C gap in the tube ring: 18 mm wide at its narrow middle (hand_sleeve.py OPENING_W)
export const PAD = { x0: HS.PAD_X0 as number, x1: HS.PAD_X1 as number, y0: HS.PAD_Y0 as number, y1: HS.PAD_Y1 as number };   // hand B's pad: on the -X / -Y side
export const PLATE_T: number = CD.PLATE_T, PLATE_Y1: number = CD.PLATE_Y1, PLATE_Y0: number = CD.PLATE_Y0;   // plate front face -56
export const PLATE_X0: number = CD.PLATE_X0, PLATE_X1: number = CD.PLATE_X1;                                    // -80 .. +80
export const PLATE_ZH: number = CD.PLATE_ZH;        // 73
export const ARM_BASE_W: number = CD.ARM_BASE_W, BATT = CD.BATT as readonly [number, number, number], ARM_BASE_T = 20, ARM_X: number = CD.ARM_X, BATT_X: number = CD.BATT_X, BATT_Z: number = CD.BATT_Z, ARM_Y0: number = CD.ARM_Y0;   // arm base 70 x 70 footprint (ARM_BASE_T ASSUMED, the sim's stand-in block)
export const MOTOR_R: number = CO.MOTOR_R, MOTOR_L: number = CO.MOTOR_L, GB_L: number = CO.GB_L, GB_T: number = CO.GB_T;   // worm motor placeholder
export const DRIVE_MOTOR_FACE_Y = HS.DRIVE_MOTOR_WALL_Y + 1, ROLL_MOTOR_GAP_Z: number = HS.ROLL_MOTOR_WALL_Z;       // layout B standoffs
export const MOTOR_RPM: number = CD.MOTOR_RPM, MOTOR_RATED_NM: number = CD.MOTOR_RATED_NM;
export const WHEEL_RATING_N: number = CD.WHEEL_RATING_N, MU_WET: number = CD.MU_WET;
export const PRELOAD_N: number = HS.SPRING_PRELOAD_N;
export const CART_MASS_KG: number = CD.CART_MASS_KG;

export type Hand = 'B' | 'C';
/** +1 for hand B (as drawn in the CAD), -1 for hand C (its mirror across x = 0). */
const SG: Record<Hand, 1 | -1> = { B: 1, C: -1 };
/** x of each hand's pipe axis in the cart frame (mm). */
export const PIPE_X: Record<Hand, number> = { B: -HX, C: HX };
export const CART_COL = 'contype="2" conaffinity="0"';   // cart geoms collide with pipes only (pipes: contype 1, conaffinity 2), as the legacy cart
const VISUAL = 'contype="0" conaffinity="0"';
/** Closed wheels and balls sit this far (mm) off the pipe so a straight pipe has no contact at all. */
export const CONTACT_CLEAR_MM = 0.3;

export const rgba = (c: [number, number, number, number?]) => `rgba="${c[0]} ${c[1]} ${c[2]} ${c[3] ?? 1}"`;
// The primitive geoms below are the COLLISION shapes (numbers from the CAD, see above); they are drawn invisible and the CAD meshes (cad-cart.ts) are what shows.
const HIDDEN = rgba([0.5, 0.5, 0.5, 0]);
const GREY = HIDDEN, STEEL = HIDDEN, SLEEVEC = HIDDEN, PLATEC = HIDDEN, PADC = HIDDEN;

// ---------------- Roll kinematics and budget ----------------
/**
 * Roll wheel kinematics. The wheel (radius wheelR) rolls on the pipe without slipping, its axle along the pipe, and its MOTOR IS CARRIED by the sleeve
 * that rolls. The sleeve angle about the pipe is phi; the wheel spins relative to the sleeve by (pipeR / wheelR) * phi (a coin rolled round a coin turns
 * (1 + R/r) times absolutely, R/r times relative to the carrier). So the shaft speed turns the sleeve at wheelR / pipeR times its own speed: FASTER, not
 * slower (cad/cart_dims.py roll_budget() uses the lever 35 here, which is right for a motor fixed to the pipe, not for a carried one).
 */
export const rollSpinPerRoll = (wheelR = OMNI_R, pipeR = R_PIPE) => pipeR / wheelR;

/** Anisotropic friction of an omni wheel: tangential force limits (N) along the rolling direction and across it, for a normal force n. */
export function omniContact(normalN: number, mu = MU_WET, crossFactor = 0.02): { along: number; across: number } {
  return { along: mu * normalN, across: mu * crossFactor * normalN };
}

export interface RollBudget {
  rollRpm: number; rollDegS: number; t180S: number; motorRollNm: number; frictionRollNm: number; holdRollNm: number;
  requiredNm: number; marginMotor: number; marginHold: number; preloadNeededRollN: number; preloadNeededAlongN: number; alongMargin: number; wornOk: boolean;
}
/**
 * Roll and drive budget of the omni cart, with the CARRIED-motor kinematics of rollSpinPerRoll. Torque the motor can put on the cart is
 * T * pipeR / wheelR (the contact force F = T / wheelR acts on the pipe at its surface, radius pipeR). The same radius (not the 35 mm
 * lever) turns the friction limit mu * N into a holding torque. loadNm = roll load about the pipe axis (cart_dims.py ROLL_LOAD_ITEMS: about 3 N m
 * with the pipe horizontal, worst case).
 */
export function rollBudget(loadNm = 2.9, o: { wheelR?: number; pipeR?: number; mu?: number; motorNm?: number; motorRpm?: number; preloadN?: number; ratingN?: number; massKg?: number } = {}): RollBudget {
  const { wheelR = OMNI_R, pipeR = R_PIPE, mu = MU_WET, motorNm = MOTOR_RATED_NM, motorRpm = MOTOR_RPM, preloadN = PRELOAD_N, massKg = CART_MASS_KG } = o;
  const k = pipeR / wheelR;
  const rollRpm = motorRpm / k;
  const motorForce = motorNm / (wheelR / 1000);
  const frictionForce = mu * preloadN;
  const motorRollNm = motorForce * (pipeR / 1000), frictionRollNm = frictionForce * (pipeR / 1000);
  const holdRollNm = Math.min(motorRollNm, frictionRollNm);
  const weightN = massKg * 9.81;
  return {
    rollRpm, rollDegS: rollRpm * 6, t180S: 30 / rollRpm, motorRollNm, frictionRollNm, holdRollNm, requiredNm: loadNm,
    marginMotor: motorRollNm / loadNm, marginHold: holdRollNm / loadNm,
    preloadNeededRollN: loadNm / (mu * pipeR / 1000), preloadNeededAlongN: weightN / mu, alongMargin: Math.min(motorForce, frictionForce) / weightN,
    wornOk: frictionRollNm >= loadNm,
  };
}

// ---------------- MJCF ----------------
const n3 = (x: number, y: number, z: number) => `${f(m(x))} ${f(m(y))} ${f(m(z))}`;

/** Hand h's geoms and wheel bodies, relative to its own pipe axis. B-frame numbers are mirrored in x for hand C. */
function handInner(h: Hand, jawA1 = JAW_A1, jawOpen = 0): string {
  const s = SG[h], clear = CONTACT_CLEAR_MM;
  const P = (x: number, y: number, z: number) => n3(s * x, y, z);                              // a B-frame point, mirrored for C
  const g: string[] = [], jg: string[] = [];   // jg: what rides on the jaw (ring sector 20..110 deg, the +60 deg lobe, its two ball cups)
  const box = (name: string, x: number, y: number, z: number, hx: number, hy: number, hz: number, col: string, vis = CART_COL) =>
    g.push(`<geom ${name ? `name="${name}" ` : ''}type="box" pos="${P(x, y, z)}" size="${f(m(hx))} ${f(m(hy))} ${f(m(hz))}" ${col} ${vis}/>`);
  // Tube ring: bore R20, outer 34.5, open at the C gap (+X for B).
  const N = 20, seg = (2 * Math.PI) / N, rc = (R_BORE + TUBE_R_MIN) / 2;
  for (let i = 0; i < N; i++) {
    const a = (i + 0.5) * seg, deg = (a * 180) / Math.PI, d = Math.min(deg, 360 - deg);
    if (d < GAP_HALF_DEG - 1) continue;                                                         // the gap (centre segments at 9 deg are skipped)
    const ux = Math.cos(a), uy = Math.sin(a);
    (deg > JAW_A0 && deg < jawA1 ? jg : g).push(`<geom name="sl${h}_${i}" type="box" pos="${P(rc * ux, rc * uy, 0)}" xyaxes="${f(s * ux)} ${f(uy)} 0 ${f(-uy)} ${f(s * ux)} 0" size="${f(m(TUBE_R_MIN - R_BORE) / 2)} ${f(m(rc) * Math.tan(seg / 2))} ${f(m(SLEEVE_L) / 2)}" ${SLEEVEC} ${CART_COL}/>`);
  }
  // Lobes: a radial bar at angle ang from r0 to r1, w wide, the full sleeve length. Outer lobe at 180 deg, ball-cup lobes at +/-60 deg.
  const lobe = (name: string, angDeg: number, r0: number, r1: number, w: number) => {
    const a = rad(angDeg), ux = Math.cos(a), uy = Math.sin(a), rm = (r0 + r1) / 2;
    (angDeg === INNER_ANG ? jg : g).push(`<geom name="${name}" type="box" pos="${P(rm * ux, rm * uy, 0)}" xyaxes="${f(s * ux)} ${f(uy)} 0 ${f(-uy)} ${f(s * ux)} 0" size="${f(m(r1 - r0) / 2)} ${f(m(w) / 2)} ${f(m(SLEEVE_L) / 2)}" ${SLEEVEC} ${CART_COL}/>`);
  };
  lobe(`lobe${h}o`, 180, R_BORE - 2, R_ARM_OMNI, ARM_W_OMNI);
  lobe(`lobe${h}p`, INNER_ANG, R_BORE - 2, R_ARM_CUP, ARM_W_CUP);
  lobe(`lobe${h}m`, -INNER_ANG, R_BORE - 2, R_ARM_CUP, ARM_W_CUP);
  // Mounting pad (on -X / -Y for B): carries the plate. Rigid with the sleeve.
  box(`pad${h}`, (PAD.x0 + PAD.x1) / 2, (PAD.y0 + PAD.y1) / 2, 0, (PAD.x1 - PAD.x0) / 2, (PAD.y1 - PAD.y0) / 2, SLEEVE_L / 2, PADC);

  // Driven omni wheels, on the 180 deg lobe: centre at x = -(OMNI_AXLE_R + clear), a spin joint each.
  const wx = -(OMNI_AXLE_R + clear);
  const wheelDisc = (name: string, axis: 'y' | 'z', z: number) => {
    const half = OMNI_W / 2, jaxis = axis === 'y' ? '0 1 0' : '0 0 1';
    const from = axis === 'y' ? P(wx, -half, z) : P(wx, 0, z - half), to = axis === 'y' ? P(wx, half, z) : P(wx, 0, z + half);
    const jpos = P(wx, 0, z);
    return `<body name="${name}"><joint name="${name}" type="hinge" pos="${jpos}" axis="${jaxis}" range="-100000 100000"/>
        <geom type="cylinder" fromto="${from} ${to}" size="${f(m(OMNI_R))}" ${GREY} friction="${MU_WET} 0.005 0.0001" ${CART_COL}/>
        ${cartMeshGeoms(h, name.startsWith('drive') ? 'drive' : 'roll', [PIPE_X[h], 0, 0])}
      </body>`;
  };
  const jbodies: string[] = [];
  const bodies: string[] = [wheelDisc(`drive${h}`, 'y', DRIVE_Z), wheelDisc(`rollwheel${h}`, 'z', ROLL_Z)];
  // Passive ball cups on the +/-60 deg lobes, rows +/-38: a printed cup (drawn, fixed) with a ball that spins freely on a ball joint.
  for (const sa of [1, -1]) {
    const a = rad(sa * INNER_ANG), ux = Math.cos(a), uy = Math.sin(a);
    for (const z of [ROW_Z, -ROW_Z]) {
      const nm = `ball${h}${sa > 0 ? 'p' : 'm'}${z > 0 ? 'f' : 'b'}`;
      const rb = BALL_CENTRE_R + clear;
      (sa > 0 ? jbodies : bodies).push(`<body name="${nm}" pos="${P(ux * rb, uy * rb, z)}"><joint name="${nm}" type="ball" pos="0 0 0"/>
        <geom type="sphere" size="${f(m(BALL_D / 2))}" ${STEEL} friction="0.05 0.002 0.0001" ${CART_COL}/>
      </body>`);
    }
  }
  // The CAD meshes of this hand (cad/cart_assembly.py: sleeve, drive and roll motors, wheels' hubs, rollers, shafts, springs, cups, Hall sensor ...): the rigid parts here, the jaw group on the jaw below.
  g.push(cartMeshGeoms(h, 'static', [PIPE_X[h], 0, 0]));
  jg.push(cartMeshGeoms(h, 'jaw', [PIPE_X[h], 0, 0]));
  // The jaw: a hinge about an axis along the pipe at the 110 deg edge of the tube (hand_sleeve.py), 0 = closed round the pipe, JAW_OPEN_RAD = released.
  const pa = rad(jawA1), pivot = P(TUBE_R_MIN * Math.cos(pa), TUBE_R_MIN * Math.sin(pa), 0);
  // jawOpen > 0 (rad): the jaw is built already swung open, with no joint (the static scenes: pod grab, transplant), by turning its body about the pivot.
  const px = s * m(TUBE_R_MIN * Math.cos(pa)), py = m(TUBE_R_MIN * Math.sin(pa)), th = s * jawOpen, ct = Math.cos(th), st = Math.sin(th);
  const jawHead = jawOpen > 0
    ? `<body name="jaw${h}" pos="${f(px - (ct * px - st * py))} ${f(py - (st * px + ct * py))} 0" quat="${f(Math.cos(th / 2))} 0 0 ${f(Math.sin(th / 2))}">`
    : `<body name="jaw${h}"><joint name="jaw${h}" type="hinge" pos="${pivot}" axis="0 0 ${s}" range="0 ${JAW_OPEN_DEG}" damping="0.05"/>`;
  const jaw = `${jawHead}
      ${jg.join('\n      ')}
      ${jbodies.join('\n      ')}
    </body>`;
  return `${g.join('\n      ')}\n      ${bodies.join('\n      ')}\n      ${jaw}`;
}

/** Plate, battery and arm base: the rigid base the sleeves carry, in the cart frame (x across, y out, z along the pipes). */
function baseGeoms(): string {
  const g: string[] = [];
  const box = (name: string, x: number, y: number, z: number, hx: number, hy: number, hz: number, col: string) =>
    g.push(`<geom ${name ? `name="${name}" ` : ''}type="box" pos="${n3(x, y, z)}" size="${f(m(hx))} ${f(m(hy))} ${f(m(hz))}" ${col} ${CART_COL}/>`);
  box('plate', (PLATE_X0 + PLATE_X1) / 2, PLATE_Y0 + PLATE_T / 2, 0, (PLATE_X1 - PLATE_X0) / 2, PLATE_T / 2, PLATE_ZH, PLATEC);
  box('battery', BATT_X, PLATE_Y0 - BATT[1] / 2, BATT_Z, BATT[0] / 2, BATT[1] / 2, BATT[2] / 2, HIDDEN);
  g.push(cartMeshGeoms('base', 'static'));
  box('armbase', ARM_X, ARM_Y0 - ARM_BASE_T / 2, 0, ARM_BASE_W / 2, ARM_BASE_T / 2, ARM_BASE_W / 2, rgba([0.9, 0.65, 0.2]));
  return g.join('\n      ');
}

const INERTIAL = '<inertial pos="0 0 0" mass="0.1" diaginertia="0.001 0.001 0.001"/>';
/**
 * The cart as a nested body, in the CAD frame with the cart centre at the origin. Two roll joints in series, one per pipe, each about that pipe's axis:
 * rollB and rollC. Only the STATIC hand's joint turns; the other holds zero (the controller's interlock, as the old hinge). Everything below the
 * second joint is rigid: sleeves, wheels, plate, battery, arm base. Wrap it in a mocap body to place it in a scene.
 */
export function omniCartBody(o: { jawA1?: number; jawOpen?: Partial<Record<Hand, number>>; handTurn?: Partial<Record<Hand, number>> } = {}): string {
  const jnt = (n: string, x: number) => `<joint name="${n}" type="hinge" pos="${n3(x, 0, 0)}" axis="0 0 1" range="-6.4 6.4"/>`;
  // handTurn (rad, about the hand's own pipe axis z): the whole sleeve (jaw, wheels, motors, cups) turned on the plate, so the C gap points where the scene needs it (Pod grab: at the track bracket, #461).
  const hand = (h: Hand) => `<body name="hand${h}" pos="${n3(PIPE_X[h], 0, 0)}"${o.handTurn?.[h] ? ` quat="${f(Math.cos(o.handTurn[h]! / 2))} 0 0 ${f(Math.sin(o.handTurn[h]! / 2))}"` : ''}>
      ${handInner(h, o.jawA1, o.jawOpen?.[h] ?? 0)}
    </body>`;
  return `<body name="rollB">${INERTIAL}${jnt('rollB', PIPE_X.B)}
   <body name="rollC">${INERTIAL}${jnt('rollC', PIPE_X.C)}
    ${hand('B')}
    ${hand('C')}
    <body name="base">
      ${baseGeoms()}
    </body>
   </body>
  </body>`;
}

/** Wheel spin joints per hand: drive wheel and roll wheel. */
export const WHEEL_JOINTS = ['driveB', 'rollwheelB', 'driveC', 'rollwheelC'] as const;
export const ROLL_JOINTS = ['rollB', 'rollC'] as const;
/** The actuators: the drive and roll-wheel motors of each sleeve (4 motors, as the part list: 2 drive, 2 roll) and a roll joint holder per pipe. */
export const JAW_JOINTS = ['jawB', 'jawC'] as const;
export const OMNI_ACTUATORS = ['driveB', 'driveC', 'rollmotorB', 'rollmotorC', 'rollB', 'rollC'] as const;
export function omniActuators(): string {
  return `<actuator>
    <position name="driveB" joint="driveB" kp="2" ctrlrange="-100000 100000"/>
    <position name="driveC" joint="driveC" kp="2" ctrlrange="-100000 100000"/>
    <position name="rollmotorB" joint="rollwheelB" kp="2" ctrlrange="-100000 100000"/>
    <position name="rollmotorC" joint="rollwheelC" kp="2" ctrlrange="-100000 100000"/>
    <position name="rollB" joint="rollB" kp="20" ctrlrange="-6.4 6.4"/>
    <position name="rollC" joint="rollC" kp="20" ctrlrange="-6.4 6.4"/>
  </actuator>`;
}

/** Position actuators of the two jaws (the transfer scene adds them to omniActuators(); the cart scenes keep the jaws closed and need none). */
export const jawActuatorsXml = () => JAW_JOINTS.map((j) => `<position name="${j}" joint="${j}" kp="2" ctrlrange="0 ${f(JAW_OPEN_RAD)}"/>`).join('\n    ');

type Mdl = { jnt(name: string): { id: number }; jnt_qposadr: ArrayLike<number>; actuator(name: string): { id: number } };
/**
 * Set the cart's joints. roll: sleeve angle (rad) about the STATIC hand's pipe (the other hand's joint holds zero). driveAngle: spin of both drive wheels
 * (rad), set by the scene from the distance driven (distance / OMNI_R). The roll wheel of the rolling hand is turned by roll * rollSpinPerRoll();
 * the other hand's roll wheel stays put (its sleeve is released and not rolling on it).
 */
export function setOmniCart(model: Mdl, data: { qpos: { [i: number]: number }; ctrl: { [i: number]: number } }, o: { roll?: number; staticHand?: Hand; driveAngle?: number } = {}): void {
  const { roll = 0, staticHand = 'C', driveAngle = 0 } = o;
  const set = (name: string, v: number) => { data.qpos[model.jnt_qposadr[model.jnt(name).id]] = v; };
  const cmd = (name: string, v: number) => { data.ctrl[model.actuator(name).id] = v; };
  const other: Hand = staticHand === 'B' ? 'C' : 'B';
  const spin = roll * rollSpinPerRoll();
  set('roll' + staticHand, roll); set('roll' + other, 0);
  cmd('roll' + staticHand, roll); cmd('roll' + other, 0);
  set('rollwheel' + staticHand, spin); set('rollwheel' + other, 0);
  cmd('rollmotor' + staticHand, spin); cmd('rollmotor' + other, 0);
  for (const h of ['B', 'C'] as const) { set('drive' + h, driveAngle); cmd('drive' + h, driveAngle); }
}

/** Standalone model: floor, the two vertical pipes B and C (0.7 m), and the cart on a mocap body at the origin. For tests and the future scenes' starting point. */
export function omniCartMjcf(o: { pipeB?: boolean; pipeC?: boolean } = {}): string {
  const { pipeB = true, pipeC = true } = o;
  const col = 'rgba="0.62 0.66 0.70 1" contype="1" conaffinity="2"';
  const pipe = (h: Hand) => `<geom name="pipe${h}" type="cylinder" fromto="${n3(PIPE_X[h], 0, -350)} ${n3(PIPE_X[h], 0, 350)}" size="${f(m(R_PIPE))}" ${col}/>`;
  return withCartAssets(`
<mujoco model="pond_omni_cart">
  <option timestep="0.002" gravity="0 0 -9.81"/>
  <worldbody>
    ${pipeB ? pipe('B') : ''}
    ${pipeC ? pipe('C') : ''}
    <body name="omnicart" mocap="true" pos="0 0 0">
      ${omniCartBody()}
    </body>
  </worldbody>
  ${omniActuators()}
</mujoco>`);
}
