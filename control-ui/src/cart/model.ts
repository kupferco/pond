// MJCF for the Cart scene: floor, a single pipe (up, bend, right), the cart and a target marker.
// The cart and the marker are mocap bodies: their poses are set from the path coordinate, not by physics.
import { BEND_R_MM, HORIZONTAL_MM, PIPE_D_MM, PIPE_SPACING_MM, PLATE_MM, SLEEVE_L_MM, SLEEVE_R_MM, VERTICAL_MM } from './track.ts';

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
  segs.push(`<geom name="${name}v" type="cylinder" fromto="${X(0)} 0 0 ${X(0)} 0 ${f(lv)}" size="${pr}" rgba="0.62 0.66 0.70 1"/>`);
  for (let i = 0; i < ARC_SEGMENTS; i++) {
    const a0 = (i / ARC_SEGMENTS) * Math.PI / 2, a1 = ((i + 1) / ARC_SEGMENTS) * Math.PI / 2;
    const p = (a: number) => `${X(r - r * Math.cos(a))} 0 ${f(lv + r * Math.sin(a))}`;
    segs.push(`<geom type="capsule" fromto="${p(a0)} ${p(a1)}" size="${pr}" rgba="0.62 0.66 0.70 1"/>`);
  }
  segs.push(`<geom name="${name}h" type="cylinder" fromto="${X(r)} 0 ${f(lv + r)} ${X(r + lh)} 0 ${f(lv + r)}" size="${pr}" rgba="0.62 0.66 0.70 1"/>`);
  return segs.join('\n    ');
}

export const JAW_OPEN_M = 0.019;   // how far each jaw slides out from the pipe
const JAW_T = 0.01;                // jaw thickness across the pipe
const JOINTS = ['h1a', 'h1b', 'h2a', 'h2b', 'plateside'] as const;

/** The cart mocap body (see frame notes below). Two identical clamp hands, 'spacingMm' apart, with the plate centred between them. */
export function cartBody(spacingMm = PIPE_SPACING_MM): string {
  const hy = m(spacingMm);
  const { across, t } = PLATE_MM;
  const sr = m(SLEEVE_R_MM), sl = m(SLEEVE_L_MM), pr = m(PIPE_D_MM) / 2;
  // Cart frame: x along the track, z toward the inside of the bend, -z the outer side. Origin on the engaged hand's pipe centre line.
  // The plate lies parallel to the track plane, to one side of the pipes (cart y), and is centred between the two hands, so each hand
  // sits the same distance from its end. Each hand is two jaws that slide across the pipe: closed they grip it, open they release it.
  const plateY = sr + m(t) / 2;
  const plateZ = -hy / 2;
  const jawC = pr + JAW_T / 2; // closed jaw centre distance from the pipe axis
  const jaw = (name: string, zc: number, sign: 1 | -1) =>
    `<body name="${name}" pos="0 0 ${f(zc)}"><joint name="${name}" type="slide" axis="0 0 ${sign}" range="0 ${JAW_OPEN_M}"/>` +
    `<geom type="box" pos="0 ${f((sr - 0.02) / 2)} ${f(sign * jawC)}" size="${f(sl / 2)} ${f((sr + 0.02) / 2)} ${JAW_T / 2}" rgba="0.18 0.45 0.35 1"/></body>`;
  return `<body name="cart" mocap="true" pos="0 0 0">
      ${jaw('h1a', 0, 1)}
      ${jaw('h1b', 0, -1)}
      ${jaw('h2a', -hy, 1)}
      ${jaw('h2b', -hy, -1)}
      <body name="plateside"><joint name="plateside" type="slide" axis="0 1 0" range="-1 1"/>
        <geom name="plate" type="box" pos="0 ${f(plateY)} ${f(plateZ)}" size="${m(PLATE_MM.alongTrack) / 2} ${m(t) / 2} ${m(across) / 2}" rgba="0.25 0.27 0.3 1"/>
        <geom name="armmount" type="box" pos="0 ${f(plateY + m(t) / 2 + 0.02)} ${f(plateZ)}" size="0.03 0.02 0.03" rgba="0.9 0.65 0.2 1"/>
      </body>
    </body>`;
}

/** Set the clamp openings (0 closed on the pipe .. 1 open) of the cart's two hands and which side of the track plane the plate is on (cart y, +1 or -1). */
export function setCart(model: { jnt(name: string): { id: number }; jnt_qposadr: ArrayLike<number> }, qpos: { [i: number]: number },
  hand1Open: number, hand2Open: number, plateSide: 1 | -1 = 1): void {
  const v = [hand1Open, hand1Open, hand2Open, hand2Open].map((o) => Math.min(1, Math.max(0, o)) * JAW_OPEN_M);
  JOINTS.forEach((n, i) => { qpos[model.jnt_qposadr[model.jnt(n).id]] = i < 4 ? v[i] : (plateSide === 1 ? 0 : -2 * (m(SLEEVE_R_MM) + m(PLATE_MM.t) / 2)); });
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
