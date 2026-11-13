// Pod-grab scene layout: a pod store (one stick with pods in a row) and a seedling tray (2 x 2 sockets), both in the arm's reach.
// Pure data and MJCF text, no MuJoCo or DOM. Positions in metres from the arm base (x forward, y left).
import { armMjcf, podBody, slotBody } from '../model.ts';
import type { XY } from '../arm/placement.ts';

const RAD = Math.PI / 180;
const polar = (r: number, deg: number): XY => [r * Math.cos(deg * RAD), r * Math.sin(deg * RAD)];

/** The store stick lies along this bearing (degrees from forward, negative = right); the pods sit on it, 28 mm apart (cad/pod_store.py). */
export const STORE_BEARING = -45;
export const STORE_PITCH = 0.028;
export const STORE_R0 = 0.125;
export const STORE_COUNT = 3;
export const STORE_PODS: readonly XY[] = Array.from({ length: STORE_COUNT }, (_, i) => polar(STORE_R0 + i * STORE_PITCH, STORE_BEARING));

/** Seedling tray: 2 x 2 sockets, 45 mm apart, centred 160 mm out on a bearing of +40 degrees. */
export const TRAY_BEARING = 40;
export const TRAY_CENTRE_R = 0.16;
export const TRAY_PITCH = 0.045;
const trayC = polar(TRAY_CENTRE_R, TRAY_BEARING);
export const TRAY_SLOTS: readonly XY[] = [[-1, -1], [-1, 1], [1, -1], [1, 1]].map(([i, j]): XY => {
  // i runs along the bearing, j across it
  const a = TRAY_BEARING * RAD, u = [Math.cos(a), Math.sin(a)], v = [-Math.sin(a), Math.cos(a)];
  return [trayC[0] + (i * u[0] + j * v[0]) * TRAY_PITCH / 2, trayC[1] + (i * u[1] + j * v[1]) * TRAY_PITCH / 2];
});

export const podName = (i: number) => `store_pod_${i}`;
export const slotName = (i: number) => `tray_slot_${i}`;
export const MARK_POD = 'mark_pod';
export const MARK_SLOT = 'mark_slot';
export const MARK_Z = 0.07;
export const MARK_HIDDEN_Z = -50;

const f = (n: number) => +n.toFixed(5);

/** MJCF: the arm, the store (rails + pods), the tray (sockets + plate) and two markers for the picked pod and the target socket. */
export function podGrabMjcf(): string {
  const a = STORE_BEARING * RAD;
  const len = STORE_COUNT * STORE_PITCH + 0.03, mid = STORE_R0 + ((STORE_COUNT - 1) * STORE_PITCH) / 2;
  const [cx, cy] = polar(mid, STORE_BEARING);
  const lat = 0.0185, off = [-Math.sin(a) * lat, Math.cos(a) * lat];
  const rail = (sgn: number) => `<geom type="box" size="${f(len / 2)} 0.002 0.006" pos="${f(cx + sgn * off[0])} ${f(cy + sgn * off[1])} 0.006" euler="0 0 ${f(a)}" rgba="0.85 0.85 0.88 1"/>`;
  const stop = polar(STORE_R0 - STORE_PITCH / 2 - 0.004, STORE_BEARING);
  const stopGeom = `<geom type="box" size="0.002 0.0205 0.006" pos="${f(stop[0])} ${f(stop[1])} 0.006" euler="0 0 ${f(a)}" rgba="0.85 0.85 0.88 1"/>`;
  const plateSize = TRAY_PITCH / 2 + 0.0205 + 0.006;
  const plate = `<geom type="box" size="${f(plateSize)} ${f(plateSize)} 0.0015" pos="${f(trayC[0])} ${f(trayC[1])} 0.0015" euler="0 0 ${f(TRAY_BEARING * RAD)}" rgba="0.12 0.3 0.2 1"/>`;
  const mark = (name: string) => `<body name="${name}" mocap="true" pos="0 0 ${MARK_HIDDEN_Z}"><geom type="sphere" size="0.006" rgba="0.93 0.45 0.1 1"/></body>`;
  const world = [
    rail(1), rail(-1), stopGeom, plate,
    ...STORE_PODS.map(([x, y], i) => podBody(podName(i), f(x), f(y))),
    ...TRAY_SLOTS.map(([x, y], i) => slotBody(slotName(i), f(x), f(y))),
    mark(MARK_POD), mark(MARK_SLOT),
  ].join('\n    ');
  return armMjcf(world);
}
