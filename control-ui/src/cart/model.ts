// MJCF for the Cart scene: floor, two-pipe track (straight, bend, straight), the cart and a target marker.
// The cart and the marker are mocap bodies: their poses are set from the path coordinate, not by physics.
import { BEND_R_MM, HORIZONTAL_MM, PIPE_D_MM, PIPE_SPACING_MM, PLATE_MM, SLEEVE_L_MM, SLEEVE_R_MM, VERTICAL_MM } from './track.ts';

const m = (mm: number) => +(mm / 1000).toFixed(5);
const f = (n: number) => +n.toFixed(5);
export const MARKER_HIDDEN_Z = -50;
const ARC_SEGMENTS = 24;

export function cartMjcf(): string {
  const pr = m(PIPE_D_MM) / 2, hy = m(PIPE_SPACING_MM) / 2;
  const lv = m(VERTICAL_MM), lh = m(HORIZONTAL_MM), r = m(BEND_R_MM);
  const pipes = [-hy, hy].map((y, k) => {
    const segs: string[] = [];
    segs.push(`<geom name="pv${k}" type="cylinder" fromto="0 ${y} ${r} 0 ${y} ${f(r + lv)}" size="${pr}" rgba="0.62 0.66 0.70 1"/>`);
    for (let i = 0; i < ARC_SEGMENTS; i++) {
      const a0 = (i / ARC_SEGMENTS) * Math.PI / 2, a1 = ((i + 1) / ARC_SEGMENTS) * Math.PI / 2;
      const p = (a: number) => `${f(r - r * Math.cos(a))} ${y} ${f(r - r * Math.sin(a))}`;
      segs.push(`<geom type="capsule" fromto="${p(a0)} ${p(a1)}" size="${pr}" rgba="0.62 0.66 0.70 1"/>`);
    }
    segs.push(`<geom name="ph${k}" type="cylinder" fromto="${r} ${y} 0 ${f(r + lh)} ${y} 0" size="${pr}" rgba="0.62 0.66 0.70 1"/>`);
    return segs.join('\n    ');
  }).join('\n    ');

  const { alongTrack, across, t, x0, x1 } = PLATE_MM;
  const sr = m(SLEEVE_R_MM);
  // Cart frame: x along the track, y across the two pipes, z out of the bend. Origin on the track centre line, midway between the pipes.
  const plateZ = sr + m(t) / 2;
  const plateY = m(((x0 + x1) / 2));
  const sleeves = [-hy, hy].map((y, k) =>
    `<geom name="sleeve${k}" type="cylinder" fromto="${-m(SLEEVE_L_MM) / 2} ${y} 0 ${m(SLEEVE_L_MM) / 2} ${y} 0" size="${sr}" rgba="0.18 0.45 0.35 1"/>
      <geom type="cylinder" fromto="${-m(SLEEVE_L_MM) / 2} ${y} ${sr * 0.5} ${m(SLEEVE_L_MM) / 2} ${y} ${sr * 0.5}" size="${sr * 0.6}" rgba="0.18 0.45 0.35 1"/>`).join('\n      ');

  return `
<mujoco model="pond_cart">
  <option timestep="0.002" gravity="0 0 -9.81"/>
  <worldbody>
    <geom name="floor" type="plane" pos="0.4 0 -0.05" size="1.4 0.9 0.1" rgba="0.82 0.86 0.9 1"/>
    <geom name="wall" type="box" pos="-0.07 0 ${f((r + lv) / 2)}" size="0.01 0.25 ${f((r + lv) / 2 + 0.05)}" rgba="0.72 0.76 0.8 1"/>
    ${pipes}
    <body name="marker" mocap="true" pos="0 0 ${MARKER_HIDDEN_Z}">
      <geom type="box" size="0.004 ${f(hy + 0.05)} 0.05" rgba="0.93 0.45 0.1 1" contype="0" conaffinity="0"/>
    </body>
    <body name="cart" mocap="true" pos="0 0 0">
      ${sleeves}
      <geom name="plate" type="box" pos="0 ${plateY} ${f(plateZ)}" size="${m(alongTrack) / 2} ${m(across) / 2} ${m(t) / 2}" rgba="0.25 0.27 0.3 1"/>
      <geom name="armmount" type="box" pos="0 ${plateY} ${f(plateZ + m(t) / 2 + 0.02)}" size="0.03 0.03 0.02" rgba="0.9 0.65 0.2 1"/>
    </body>
  </worldbody>
</mujoco>`;
}
