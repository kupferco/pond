// The reach test: can the SO-101 stand-in on the cart bring its hand to every one of the 24 plugs (planting holes) and every one of the 16 seedling pods? The cart is tried at EVERY station of the track
// (station.ts): leg A (the leg it stands on, y = -0.29) and leg B (y = +0.29) at every height of their straight part (5 mm steps), and the straight part of the bottom and of the top run (5 mm steps),
// each as it is (roll 0) and turned 180 degrees about the pipe's own axis. (Every other roll in 30-degree steps is tried as well, on every station, and reported separately: it never changes the colour.) A station passes when
//  1. the hand can be at the cap-top point of the part with the arm inside its joint limits (else "distance" when the point is out of the arm's reach, "joint limit" when a joint would pass its limit),
//  2. the hand can point along the part's axis to within ANGLE_TOL degrees (the SO-101 points its hand only along a plane through its base axis, so the station has to put the part in the right plane; else "angle"),
//  3. the same two things hold APPROACH metres out along the axis (the hand waits there before it goes in and pulls the part out through it), and
//  4. nothing touches at either pose (arm, cart, the gripped part itself against pipe, collars, other plugs and pods, tank, lid, track and its brackets; else "collision").
// Green = passes at some station with roll 0, amber = passes only rolled 180 degrees, red = never. For each target and roll the best station is kept (the one with the most joint margin), or, when none passes, the nearest miss.
import type { MainModule, MjData, MjModel } from '@mujoco/mujoco';
import { MOTORS } from '../model.ts';
import { L1, L2, SHOULDER_Z, solvePlanar } from '../arm/kinematics.ts';
import { WRIST_TO_HAND } from '../arm/dims.ts';
import { GRIP_TX, GRIP_TZ, JAW_CAP_DEG, XB, YC } from '../transplant/layout.ts';
import { ikTool, toolOf, type Joints, type Tool } from '../transplant/task.ts';
import { worstContact } from '../transplant/apply.ts';
import { HOLES, PODS, podCapTop, seatCapTop, seatDir, type HoleSpec, type PodSpec } from './layout.ts';
import { dirToRef, refStation, stations, toRef, type Station } from './station.ts';

type V3 = [number, number, number];
const RAD = Math.PI / 180, DEG = 180 / Math.PI;
export const ANGLE_TOL = 5;        // degrees between the part's axis and the way the hand points
export const APPROACH = 0.06;      // m out along the axis
export type Reason = 'distance' | 'joint limit' | 'angle' | 'collision';
export type Colour = 'green' | 'amber' | 'red';
export interface Attempt {
  ok: boolean;
  station?: Station;                  // the station that works (the one with the most joint margin), or the nearest miss
  cartZ?: number;                     // = station.at when it is on a leg
  margin?: number;                    // deg to the nearest joint limit at that height, grip pose
  joints?: Joints;                    // grip pose
  reason?: Reason; detail?: string;   // why the best try failed
  looseErr?: number; looseZ?: number; // the best angle error (deg), at cart height looseZ, of a pose that reaches the point clear of everything (hand angle ignored); undefined = the point cannot be reached at all
}
export interface Target { id: string; kind: 'hole' | 'pod'; label: string; pos: V3; out: V3; z: number; direct: Attempt; rolled: Attempt; other: Attempt; colour: Colour }

const LIM: Record<string, [number, number]> = {};
for (const m of MOTORS) LIM[m.id] = [m.min, m.max];

/** Why the hand cannot be at tool pose t with the cart at cartZ: 'distance' (the wrist target is out of the two links' reach) or the joint that would pass its limit; null when it can. */
function ikWhy(t: Tool, cartZ: number): { reason: Reason; mag: number; detail: string } | null {
  if (ikTool(t, cartZ)) return null;
  const b: V3 = [cartZ - t.z, -(t.y - YC), XB - t.x];
  const pan = Math.atan2(b[1], b[0]) * DEG, rG = Math.hypot(b[0], b[1]), phi = t.phi * RAD;
  const wr = rG - (GRIP_TX * Math.cos(phi) + GRIP_TZ * Math.sin(phi)) - WRIST_TO_HAND * Math.cos(phi);
  // planar problem in the arm's plane, as in ikTool: radial reach rG, height b[2] (the base frame's third axis)
  const hh = b[2];
  const wh = hh - (-GRIP_TX * Math.sin(phi) + GRIP_TZ * Math.cos(phi)) + WRIST_TO_HAND * Math.sin(phi);
  const d = Math.hypot(wr, wh - SHOULDER_Z);
  if (d > L1 + L2 - 1e-4) return { reason: 'distance', mag: d - (L1 + L2), detail: `${((d - (L1 + L2)) * 1000).toFixed(0)} mm too far` };
  if (d < Math.abs(L1 - L2) + 1e-4) return { reason: 'distance', mag: Math.abs(L1 - L2) - d, detail: `${((Math.abs(L1 - L2) - d) * 1000).toFixed(0)} mm too close` };
  // inside the reach: some joint passes its limit. Solve with the limits opened up and see which one.
  const saved = MOTORS.map((m) => [m.min, m.max] as [number, number]);
  let j: Joints | null = null;
  try { for (const m of MOTORS) { m.min = -720; m.max = 720; } j = solvePlanar(pan, rG, hh, GRIP_TX, GRIP_TZ, t.phi); } finally { MOTORS.forEach((m, i) => { m.min = saved[i][0]; m.max = saved[i][1]; }); }
  if (!j) return { reason: 'distance', mag: 0, detail: 'no solution' };
  let worst = ['', 0] as [string, number];
  for (const k of ['A', 'B', 'C', 'D'] as const) { const over = Math.max(LIM[k][0] - j[k], j[k] - LIM[k][1]); if (over > worst[1]) worst = [k, over]; }
  if (!worst[0]) return { reason: 'joint limit', mag: 0, detail: 'no elbow pose inside the limits' };
  const name = (k: string) => MOTORS.find((m) => m.id === k)!.label.split(' (')[0].toLowerCase();
  return { reason: 'joint limit', mag: worst[1], detail: `${name(worst[0])} ${worst[1].toFixed(0)}° past its limit` };
}
const margin = (j: Joints) => Math.min(...(['A', 'B', 'C', 'D'] as const).map((k) => Math.min(j[k] - LIM[k][0], LIM[k][1] - j[k])));

/** Poses the cart and the arm in the model and returns the deepest contact. */
export class Rig {
  readonly qpos: Record<string, number> = {};
  readonly mocap: number;
  readonly mujoco: MainModule; readonly model: MjModel; readonly data: MjData;
  constructor(mujoco: MainModule, model: MjModel, data: MjData) {
    this.mujoco = mujoco; this.model = model; this.data = data;
    for (const m of MOTORS) this.qpos[m.id] = model.jnt_qposadr[model.jnt(m.joint).id];
    this.mocap = model.body_mocapid[model.body('cart').id];
  }
  pose(st: Station, j: Joints | null, jaw = 0) { this.place(st.pos, st.quat, j, jaw); }
  /** Cart body at any pose (origin, quaternion w x y z), arm at joints j. */
  place(pos: V3, quat: [number, number, number, number], j: Joints | null, jaw = 0) {
    for (let k = 0; k < 3; k++) this.data.mocap_pos[3 * this.mocap + k] = pos[k];
    for (let k = 0; k < 4; k++) this.data.mocap_quat[4 * this.mocap + k] = quat[k];
    if (j) for (const m of MOTORS) if (m.id !== 'F') this.data.qpos[this.qpos[m.id]] = ((j as unknown as Record<string, number>)[m.id] ?? 0) * RAD;
    this.data.qpos[this.qpos.F] = jaw * RAD;
    this.mujoco.mj_forward(this.model, this.data);
  }
  contact() { return worstContact(this.model, this.data); }
}

const FOLD: Joints = { A: 0, B: 0, C: 0, D: 0, E: 0 };

/** Switches the collisions of every geom of the bodies of the target on or off (they are gripped: the hand is meant to touch them). */
function setTargetCollide(model: MjModel, bodies: string[], on: boolean, saved: Map<number, [number, number]>) {
  for (const b of bodies) {
    const id = model.body(b).id;
    for (let g = 0; g < model.ngeom; g++) if (model.geom_bodyid[g] === id) {
      if (on) { const s = saved.get(g); if (s) { model.geom_contype[g] = s[0]; model.geom_conaffinity[g] = s[1]; } } else { saved.set(g, [model.geom_contype[g], model.geom_conaffinity[g]]); model.geom_contype[g] = 0; model.geom_conaffinity[g] = 0; }
    }
  }
}

interface Try { fail?: { reason: Reason; mag: number; detail: string }; joints?: Joints; margin?: number }
const RANK: Record<Reason, number> = { distance: 0, 'joint limit': 1, angle: 2, collision: 3 };

export function attempt(rig: Rig | null, sts: Station[], pos: V3, axisIn: V3, out: V3): Attempt {
  // The cart at station st reaches the point p as the reference cart (hand C on leg A, height 0) reaches the point as seen from the station.
  let best: { st: Station; j: Joints; m: number } | null = null, loose: { st: Station; err: number } | null = null, worst: { rank: number; mag: number; reason: Reason; detail: string; st: Station } | null = null;
  for (const st of sts) {
    const p = toRef(st, pos), a = dirToRef(st, axisIn), o = dirToRef(st, out);
    const note = (f: { reason: Reason; mag: number; detail: string }) => { const r = RANK[f.reason]; if (!worst || r > worst.rank || (r === worst.rank && f.mag < worst.mag)) worst = { rank: r, mag: f.mag, reason: f.reason, detail: f.detail, st }; };
    const t = toolOf(p, a, 0);
    const g = ikWhy(t, 0); if (g) { note(g); continue; }
    const ap: Tool = { x: p[0] + o[0] * APPROACH, y: p[1] + o[1] * APPROACH, z: p[2] + o[2] * APPROACH, phi: t.phi };
    const g2 = ikWhy(ap, 0); if (g2) { note({ ...g2, detail: g2.detail + ' (waiting point)' }); continue; }
    const angleOk = t.err <= ANGLE_TOL;
    if (!angleOk) note({ reason: 'angle', mag: t.err, detail: `hand ${t.err.toFixed(0)}° off the part's axis` });
    const j = ikTool(t, 0)!, ja = ikTool(ap, 0)!;
    let hit = 0, names = '';
    if (rig) for (const jj of [j, ja]) { rig.pose(st, jj, JAW_CAP_DEG); const c = rig.contact(); if (c.depth < hit) { hit = c.depth; names = c.names; } }
    if (hit < 0) { if (angleOk) note({ reason: 'collision', mag: -hit, detail: `${names} (${(-hit * 1000).toFixed(1)} mm)` }); continue; }
    if (!loose || t.err < loose.err) loose = { st, err: t.err };   // the point can be reached, clear of everything, with the hand this far off the axis
    if (!angleOk) continue;
    const m = Math.min(margin(j), margin(ja));
    if (!best || m > best.m) best = { st, j, m };
  }
  const l = loose ? { looseErr: loose.err, looseZ: loose.st.at } : {};
  if (best) return { ok: true, station: best.st, cartZ: best.st.at, margin: best.m, joints: best.j, ...l };
  const w = worst!;
  return { ok: false, station: w.st, reason: w.reason, detail: `${w.detail} at best, ${w.st.label}`, ...l };
}

const KINDS: Station['kind'][] = ['leg A', 'leg B', 'bottom run', 'top run'];
const sets = (rolls: number[], kinds: Station['kind'][] = KINDS) => rolls.flatMap((r) => kinds.flatMap((k) => stations(k, r)));
const NOT_TRIED: Attempt = { ok: false, reason: 'distance', detail: 'not tried' };

/** Runs the whole test on a model made by reachMjcf(). */
export function runReach(mujoco: MainModule, model: MjModel, data: MjData): Target[] {
  const rig = new Rig(mujoco, model, data), saved = new Map<number, [number, number]>(), out: Target[] = [];
  const S0 = sets([0]), S180 = sets([180]), SOTHER = sets([30, 60, 90, 120, 150, 210, 240, 270, 300, 330]);
  const one = (id: string, kind: 'hole' | 'pod', label: string, pos: V3, axisIn: V3, outDir: V3, body: string) => {
    setTargetCollide(model, [body], false, saved);
    const direct = attempt(rig, S0, pos, axisIn, outDir), rolled = attempt(rig, S180, pos, axisIn, outDir);
    const other = direct.ok || rolled.ok ? NOT_TRIED : attempt(rig, SOTHER, pos, axisIn, outDir);
    setTargetCollide(model, [body], true, saved);
    out.push({ id, kind, label, pos, out: outDir, z: pos[2], direct, rolled, other, colour: direct.ok ? 'green' : rolled.ok ? 'amber' : 'red' });
  };
  for (const h of HOLES) { const d = seatDir(h); one(h.id, 'hole', holeLabel(h), seatCapTop(h), [-d[0], -d[1], -d[2]], d, `plug${h.n}`); }
  for (const p of PODS) one(p.id, 'pod', podLabel(p), podCapTop(p), [0, 0, -1], [0, 0, 1], `pod${p.n}`);
  rig.pose(refStation(0.63), FOLD);
  return out;
}
export const holeLabel = (h: HoleSpec) => `Hole ${h.n} (level ${h.level}, column ${h.col}, ${h.z.toFixed(3)} m)`;
export const podLabel = (p: PodSpec) => `Pod ${p.n} (row ${p.row}, column ${p.col})`;

export function summary(t: Target[]) {
  const count = (kind: 'hole' | 'pod', c: Colour) => t.filter((x) => x.kind === kind && x.colour === c).length;
  const row = (kind: 'hole' | 'pod') => ({ position: t.filter((x) => x.kind === kind && (x.direct.looseErr !== undefined || x.rolled.looseErr !== undefined)).length, green: count(kind, 'green'), amber: count(kind, 'amber'), red: count(kind, 'red'), total: t.filter((x) => x.kind === kind).length });
  return { holes: row('hole'), pods: row('pod') };
}
/** A one-line reason for a red target: the best try of each orientation. */
export const whyRed = (x: Target) => `as is: ${x.direct.reason} (${x.direct.detail}); rolled 180°: ${x.rolled.reason} (${x.rolled.detail})`;

/** Colours of the result: plug and pod (cap and body) of every target, in the model (before a viewer is made from it). */
export const RESULT_RGB: Record<Colour, [number, number, number]> = { green: [0.18, 0.72, 0.3], amber: [0.98, 0.7, 0.1], red: [0.86, 0.2, 0.18] };
export function colourParts(model: MjModel, results: Target[]) {
  for (const t of results) {
    const id = model.body(t.kind === 'hole' ? `plug${t.id.slice(1)}` : `pod${t.id.slice(1)}`).id, c = RESULT_RGB[t.colour];
    for (let g = 0; g < model.ngeom; g++) if (model.geom_bodyid[g] === id && model.geom_rgba[4 * g + 3] === 1 && model.geom_size[3 * g] > 0.009) { model.geom_rgba[4 * g] = c[0]; model.geom_rgba[4 * g + 1] = c[1]; model.geom_rgba[4 * g + 2] = c[2]; }
  }
}
