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

/** The cart mocap body (see frame notes below). */
export function cartBody(spacingMm = PIPE_SPACING_MM): string {
  const hy = m(spacingMm);
  const { alongTrack, across, t } = PLATE_MM;
  const sr = m(SLEEVE_R_MM), sl = m(SLEEVE_L_MM);
  // Cart frame: x along the track, z toward the inside of the bend, -z the outer side. Origin on the pipe centre line.
  // The plate lies parallel to the track plane (the X-Z plane the pipe is in), offset to one side of the pipe (cart y).
  // The engaged (clamping) wheel sleeve is at the plate's inner edge, around the pipe; the plate extends to the outer side (-z).
  // The free wheel hangs on the far outer edge, on the other side of the track plane, and never touches the pipe.
  const plateY = sr + m(t) / 2;
  const plateZ = -(m(across) / 2 - 0.05);
  const fw = 0.03;
  return `<body name="cart" mocap="true" pos="0 0 0">
      <geom name="sleeve" type="cylinder" fromto="${-sl / 2} 0 0 ${sl / 2} 0 0" size="${sr}" rgba="0.18 0.45 0.35 1"/>
      <geom name="plate" type="box" pos="0 ${f(plateY)} ${f(plateZ)}" size="${m(alongTrack) / 2} ${m(t) / 2} ${m(across) / 2}" rgba="0.25 0.27 0.3 1"/>
      <geom name="armmount" type="box" pos="0 ${f(plateY + m(t) / 2 + 0.02)} ${f(plateZ)}" size="0.03 0.02 0.03" rgba="0.9 0.65 0.2 1"/>
      <geom name="freebracket" type="box" pos="0 ${f((plateY - fw) / 2)} ${f(-hy)}" size="0.01 ${f((plateY + fw) / 2)} 0.005" rgba="0.25 0.27 0.3 1"/>
      <geom name="freewheel" type="cylinder" fromto="0 ${-fw} ${f(-hy + 0.012)} 0 ${-fw} ${f(-hy - 0.012)}" size="${fw}" rgba="0.18 0.45 0.35 1"/>
    </body>`;
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
