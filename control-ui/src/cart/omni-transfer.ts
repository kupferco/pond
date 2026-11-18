// Transfer on the omni cart (OpenPocket #283, plan task 265 part 9, owner answers Q3, Q7, Q8): the model, the placement and the contact check of the roll
// about the static pipe's centre line. Pure maths and MJCF, no DOM. The controller is in omni-transfer-run.ts.
//
// Mechanism: the cart (rigid base on two three-lobe sleeves, src/cart/omni.ts) clamps pipe B (x = -60) and pipe C (x = +60). A transfer releases one hand (its jaw opens 92 degrees), and the
// WHOLE cart rolls about the other (static) pipe on its roll wheel: the free hand swings round the static pipe's centre line and leaves its own pipe, the cart drives on the static pipe round
// the bend with the roll held (Q7), and rolls back flat beyond the bend. No hinges. The roll angle phi is positive when the free hand moves to the PLATE side (towards -y, in front of the
// pipe plane, away from the spine) and negative when it moves to the SPINE side (+y). Q3: the controller always uses the direction that clears.
import { omniCartBody, omniActuators, jawActuatorsXml, setOmniCart, PIPE_X, R_PIPE, OMNI_R, JAW_OPEN_RAD, rgba, type Hand } from './omni.ts';
import { pipeGeoms } from './model.ts';
import { L_ARC, L_VERT, pathAt } from './track.ts';
import { matToQuat } from './omni-track.ts';

const m = (mm: number) => +(mm / 1000).toFixed(5);
const f = (n: number) => +n.toFixed(5);
export const DEG = Math.PI / 180;

// ---------------- The track ----------------
export const TRACK_HORIZ_MM = 450;                     // length of the top bars (as the earlier Transfer scene)
export const S_MIN_CM = 15, S_MAX_CM = 50, S_START_CM = 30;   // where the cart rides on both pipes (cm along the pipe): the straight leg below the roll station
/** The roll station: where the cart rolls, on the straight leg just below the bend (Q8: rolling only on the legs). */
export const ROLL_STATION_CM = S_MAX_CM;
export const P_BEND_START = L_VERT, P_BEND_END = L_VERT + L_ARC;
/** The roll is held through the bend (Q7) and rolled back at the start of the top run, a declared transfer roll (the bend end is the first place it may turn without being on the curve). */
export const S_FLAT_CM = Math.ceil((P_BEND_END + 1) * 10) / 10;
export const P_TOP_CM = P_BEND_END + 34;               // the cart's farthest position on the top bar, clear of the bar's free end
/** M8 track-joint rods and rings (hand_sleeve.py jaw side), at four heights of the leg (cm along the pipe, ASSUMED): none above the roll station, so the rolled cart passes no joint. */
export const JOINT_CM = [6, 16, 26, 36];
const ROD_R = 4, ROD_OUT = 50, RING_R = 17.5, RING_W = 8;
/** The track pipes' own geoms stand on the world: B at -60 bending left, C at +60 bending right (the Cart scene's pipeGeoms). */
export function trackXml(): string {
  const joints = (h: Hand) => JOINT_CM.map((cm, i) => {
    const x = PIPE_X[h], dir = h === 'B' ? 1 : -1, z = cm * 10;     // the rod is on the hand's jaw side: towards the other pipe
    return `<geom name="rod${h}${i}" type="cylinder" fromto="${f(m(x + dir * R_PIPE))} 0 ${f(m(z))} ${f(m(x + dir * (R_PIPE + ROD_OUT)))} 0 ${f(m(z))}" size="${f(m(ROD_R))}" ${rgba([0.5, 0.5, 0.55])} contype="1" conaffinity="2"/>
    <geom name="ring${h}${i}" type="cylinder" fromto="${f(m(x))} 0 ${f(m(z - RING_W / 2))} ${f(m(x))} 0 ${f(m(z + RING_W / 2))}" size="${f(m(RING_R))}" ${rgba([0.5, 0.5, 0.55])} contype="1" conaffinity="2"/>`;
  }).join('\n    ');
  return [pipeGeoms(m(PIPE_X.B), -1, TRACK_HORIZ_MM, 'pipeB'), pipeGeoms(m(PIPE_X.C), 1, TRACK_HORIZ_MM, 'pipeC'), joints('B'), joints('C')].join('\n    ');
}
/** The Transfer scene's MJCF: floor, both track pipes, the cart on a mocap body with both jaws and the roll, drive and jaw actuators. */
export function transferMjcf(o: { jawA1?: number } = {}): string {
  return `
<mujoco model="pond_omni_transfer">
  <option timestep="0.002" gravity="0 0 -9.81"/>
  <worldbody>
    <geom name="floor" type="plane" pos="0.05 0 -0.05" size="1.4 0.9 0.1" rgba="0.82 0.86 0.9 1"/>
    ${trackXml()}
    <body name="omnicart" mocap="true" pos="0 0 0.3">
      ${omniCartBody(o)}
    </body>
  </worldbody>
  ${omniActuators().replace('</actuator>', `${jawActuatorsXml()}\n  </actuator>`)}
</mujoco>`;
}

// ---------------- Placement ----------------
/** Trim of the rigid cart on the bend, in the riding pipe's own sense: dx (mm) shifts the cart towards the bend's centre, yaw (deg) turns its axis towards the centre. Zero on the straights. */
export interface Trim { dx: number; yaw: number }
export const NO_TRIM: Trim = { dx: 0, yaw: 0 };
/** Rows [s cm, dx mm, yaw deg] of the best trim of the cart riding pipe C's bend (scripts/search-swing.ts bend mode: the least penetration of the riding sleeve; worst 4.01 mm in the middle of the bend, the same finding as the cart on track scene). The same rows serve hand B on pipe B (mirror). */
export const TRIM_ROWS: [number, number, number][] = [
  [56, 0, 0], [57, 0.5, 1], [58, 1.5, 2.5], [59, 2.5, 4.5], [60, 4.5, 6], [61, 5.5, 4.5], [62, 7, 3], [63, 7.5, 2],
  [64, 8, 1], [65, 8.5, 0.5], [66, 9, 0], [67, 9, 0], [68, 9, 0], [69, 9, 0], [70, 9, 0], [71, 9, 0],
  [72, 9, 0], [73, 9, 0], [74, 9, 0], [75, 9, 0], [76, 9, 0], [77, 9, 0], [78, 9, 0], [79, 8.5, -1],
  [80, 8, -1.5], [81, 7, -2.5], [82, 6.5, -3.5], [83, 5, -5.5], [84, 3, -5.5], [85, 2, -3.5], [86, 1, -2], [87, 0.5, -0.5],
];
export function trimAt(sCm: number, rows: [number, number, number][] = TRIM_ROWS): Trim {
  if (sCm <= rows[0][0] || sCm >= rows[rows.length - 1][0]) return NO_TRIM;
  let i = 0;
  while (rows[i + 1][0] < sCm) i++;
  const k = (sCm - rows[i][0]) / (rows[i + 1][0] - rows[i][0]);
  return { dx: rows[i][1] + k * (rows[i + 1][1] - rows[i][1]), yaw: rows[i][2] + k * (rows[i + 1][2] - rows[i][2]) };
}
export const other = (h: Hand): Hand => (h === 'B' ? 'C' : 'B');
/** The hand that rides pipe C is hand C; the trip up pipe C releases hand B. */
export const pipeOf = (h: Hand) => h;

/**
 * Pose of the cart when hand `rider` has its pipe axis at path position s (cm) of its own pipe: position (m) and quaternion (w x y z) of the cart origin.
 * Cart frame (omni.ts): z along the pipe, x from pipe B to pipe C, y out of the pipe plane, plate on -y. Hand C rides pipe C's right-bending path; hand B rides pipe B's left-bending path, the mirror image.
 */
export function transferPose(rider: Hand, sCm: number, trim: Trim = NO_TRIM): { pos: [number, number, number]; quat: [number, number, number, number] } {
  const p = pathAt(sCm), sg = rider === 'C' ? 1 : -1;
  const t: [number, number] = [sg * p.tx, p.tz], n: [number, number] = [sg * p.tz, -p.tx];   // tangent and inward normal (towards the bend's centre) in world (x, z)
  const yaw = (trim.yaw * DEG), c = Math.cos(yaw), sn = Math.sin(yaw);
  const zc: [number, number] = [c * t[0] + sn * n[0], c * t[1] + sn * n[1]], xi: [number, number] = [c * n[0] - sn * t[0], c * n[1] - sn * t[1]];
  const xc: [number, number] = [sg * xi[0], sg * xi[1]];   // cart +x points from B to C: inward for C, outward for B
  const R = [[xc[0], 0, zc[0]], [0, 1, 0], [xc[1], 0, zc[1]]];
  const lx = (PIPE_X[rider] - sg * trim.dx) / 1000;
  const off = [R[0][0] * lx, 0, R[2][0] * lx];
  return { pos: [PIPE_X[rider] / 1000 + sg * p.x - off[0], 0, p.z - off[2]], quat: matToQuat(R) };
}

/** State of the cart in the scene: the riding (static) hand, position along its pipe (cm), the roll (deg, positive = free hand to the plate side), the free hand's jaw (0 closed .. 1 open). */
export interface PoseState { rider: Hand; s: number; roll: number; open: number; trim?: Trim; riderOpen?: number }
type Mdl = Parameters<typeof setOmniCart>[0] & { body(name: string): { id: number }; body_mocapid: ArrayLike<number> };
type Dt = Parameters<typeof setOmniCart>[1] & { mocap_pos: { [i: number]: number }; mocap_quat: { [i: number]: number } };
/** The roll about the static pipe in the cart frame: positive about +z (x towards y). Hand C is the static one when the free hand B is on -x: + turns B towards -y, the plate side. For hand B it is the other way round. */
export const cartRoll = (rider: Hand, rollDeg: number) => (rider === 'C' ? rollDeg : -rollDeg) * DEG;
export function placeTransfer(model: Mdl, data: Dt, st: PoseState, driveAngle = 0): void {
  const mc = model.body_mocapid[model.body('omnicart').id], { pos, quat } = transferPose(st.rider, st.s, st.trim ?? trimAt(st.s));
  for (let k = 0; k < 3; k++) data.mocap_pos[3 * mc + k] = pos[k];
  for (let k = 0; k < 4; k++) data.mocap_quat[4 * mc + k] = quat[k];
  setOmniCart(model, data, { roll: cartRoll(st.rider, st.roll), staticHand: st.rider, driveAngle });
  const jaw = (h: Hand, open: number) => { data.qpos[model.jnt_qposadr[model.jnt('jaw' + h).id]] = open * JAW_OPEN_RAD; data.ctrl[model.actuator('jaw' + h).id] = open * JAW_OPEN_RAD; };
  jaw(other(st.rider), st.open); jaw(st.rider, st.riderOpen ?? 0);
}

// ---------------- Contacts ----------------
export type Owner = 'rider' | 'free' | 'base';
export type Env = 'pipe' | 'rod' | 'ring';
export type Depths = Record<`${Owner}:${Env}`, number>;
type Cm = { ngeom: number; geom_bodyid: ArrayLike<number>; body(i: number): { name: string; delete?(): void }; geom(i: number): { name: string; delete?(): void } };
type Cd = { ncon: number; contact: { get(i: number): { geom1: number; geom2: number; dist: number; delete?(): void } | undefined; delete?(): void } };
const ownerOfBody = (body: string, rider: Hand): Owner | null => {
  if (body === 'base') return 'base';
  const mm = /^(?:hand|drive|rollwheel|ball|jaw)([BC])/.exec(body);
  return mm ? (mm[1] === rider ? 'rider' : 'free') : null;
};
/** Smallest gap (m, negative = penetration; 0 when nothing is within the model's margin) of each part of the cart against each kind of track part. Call after mj_forward. */
export function transferContacts(model: Cm, data: Cd, rider: Hand): Depths {
  const out = { 'rider:pipe': 0, 'rider:rod': 0, 'rider:ring': 0, 'free:pipe': 0, 'free:rod': 0, 'free:ring': 0, 'base:pipe': 0, 'base:rod': 0, 'base:ring': 0 } as Depths, con = data.contact;
  const bodyName = (g: number) => { const b = model.body(model.geom_bodyid[g]), n = b.name; b.delete?.(); return n; };
  const geomName = (g: number) => { const gm = model.geom(g), n = gm.name; gm.delete?.(); return n; };
  for (let i = 0; i < data.ncon; i++) {
    const c = con.get(i)!, b1 = bodyName(c.geom1), b2 = bodyName(c.geom2), cart = b1 === 'world' ? c.geom2 : c.geom1, env = b1 === 'world' ? c.geom1 : c.geom2;
    if (b1 === 'world' || b2 === 'world') {
      const o = ownerOfBody(bodyName(cart), rider), en = geomName(env), kind: Env = en.startsWith('rod') ? 'rod' : en.startsWith('ring') ? 'ring' : 'pipe';
      if (o) { const k = `${o}:${kind}` as keyof Depths; out[k] = Math.min(out[k], c.dist); }
    }
    c.delete?.();
  }
  con.delete?.();
  return out;
}
/** The depth that counts as a collision of the transfer: everything except the riding sleeve against the pipe it rides, and the sleeves against the 1.5 mm joint rings (the wheels stand 0.3 mm off the pipe and ride over the rings, plan section 7; the bore is R20 against the ring's R17.5). The base is checked against the rings too. */
export const worstOf = (d: Depths) => Math.min(d['free:pipe'], d['free:rod'], d['base:pipe'], d['base:rod'], d['base:ring'], d['rider:rod']);
export const blockedBy = (d: Depths, clear = 0): string => (Object.entries(d) as [string, number][]).filter(([k, v]) => v !== 0 && v < clear - 1e-9 && k !== 'rider:pipe' && k !== 'rider:ring' && k !== 'free:ring').map(([k]) => k).join(' ');
export { OMNI_R };
export const PIPE_SPACING_NOTE = 'Pipes B and C are 120 mm apart (cad/cart_dims.py).';
