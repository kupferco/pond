// Roll sweep and the "cart turned 90 degrees" option of the reach test (OpenPocket #313).
// The omni wheels let the cart turn about the pipe it rides. On leg A (vertical) that is a turn about the vertical axis; seen from above, a positive roll is COUNTERCLOCKWISE. The cart as the reach test shows it
// is rolled 180 degrees, so "90 degrees counterclockwise from its current position" is a roll of 270 degrees (180 + 90). The roll of 90 degrees (from the cart as it is, roll 0) is tried as well, and every roll in 15-degree steps.
// For every roll and every hole and pod: the cart at every height of leg A's straight part (5 mm steps), arm joints inside their limits, hand within ANGLE_TOL of the part's axis, no contact at the grip pose or the waiting
// pose (60 mm out) with anything of this unit, and, as a second pass, with the ghost neighbour on the left switched on. Clashes are named by what touches what (cart body, motors, open clamp, arm / the other leg or free pipe,
// the spine and collars, pods and plugs, the tank, the neighbour).
import type { MainModule, MjData, MjModel } from '@mujoco/mujoco';
import { podCapTop, seatCapTop, seatDir, HOLES, PODS, setGhostCollide } from './layout.ts';
import { Rig, attempt, setTargetCollide, type Attempt } from './test.ts';
import { stations } from './station.ts';
import { JAW_CAP_DEG } from '../transplant/layout.ts';

export const SWEEP_ANGLES = Array.from({ length: 24 }, (_, i) => i * 15);
/** The option asked for: the cart turned 90 degrees counterclockwise (seen from above) from the 180-degree roll it is shown in. */
export const TURN_90 = 270;
/** For comparison: a roll of +90 from the cart as it is. */
export const TURN_90_FROM_ZERO = 90;

export type CartPart = 'cart body' | 'motors' | 'open clamp' | 'arm';
export type Scenery = 'this unit: other leg and track' | 'spine and brackets' | 'growing pipe and collars' | 'pods and plugs' | 'tank, lid and tray' | 'riding leg' | 'floor' | 'neighbour unit';
export const SCENERY: Scenery[] = ['this unit: other leg and track', 'spine and brackets', 'growing pipe and collars', 'pods and plugs', 'tank, lid and tray', 'riding leg', 'floor', 'neighbour unit'];

/** Category of every geom: the cart side (cart body, motors, clamp, arm) or the scenery side; built once per model. */
export function classifier(model: MjModel) {
  const cartId = model.body('cart').id, side: Array<{ cart?: CartPart; scene?: Scenery }> = [];
  for (let g = 0; g < model.ngeom; g++) {
    const b = model.body(model.geom_bodyid[g]), bn = b.name, gn = model.geom(g).name, root = model.body_rootid[model.geom_bodyid[g]];
    if (root === cartId) {
      side.push({ cart: /^servo/.test(gn) ? 'motors' : /^jaw_|^servo6/.test(gn) || bn === 'jaw' ? 'open clamp' : ['base', 'turntable', 'shoulder', 'elbow', 'wrist', 'hand'].includes(bn) ? 'arm' : 'cart body' });
    } else {
      let sc: Scenery;
      if (bn === 'ghost') sc = 'neighbour unit';
      else if (/^collar/.test(bn)) sc = 'growing pipe and collars';
      else if (/^(plug|pod)\d+/.test(bn)) sc = 'pods and plugs';
      else if (gn === 'floor') sc = 'floor';
      else if (/^pipe_/.test(gn)) sc = 'growing pipe and collars';
      else if (gn === 'trackleg-1' || /^trackc-1/.test(gn)) sc = 'riding leg';
      else if (/^trackleg|^track(top|bot|c)/.test(gn)) sc = 'this unit: other leg and track';
      else if (/^bracket/.test(gn)) sc = 'spine and brackets';
      else if (gn === '' && Math.hypot(model.geom_pos[3 * g], model.geom_pos[3 * g + 1]) < 0.025 && model.geom_size[3 * g + 2] > 0.5) sc = 'spine and brackets';
      else sc = 'tank, lid and tray';
      side.push({ scene: sc });
    }
  }
  return side;
}
export interface Clash { part: CartPart | 'both parts of the cart'; scene: Scenery; depth: number }
/** Every penetrating contact of the pose now in the model, as the deepest one per (cart part, scenery) pair. */
export function clashes(model: MjModel, data: MjData, side: ReturnType<typeof classifier>): Clash[] {
  const best = new Map<string, Clash>(), contacts = data.contact;
  for (let i = 0; i < data.ncon; i++) {
    const c = contacts.get(i);
    if (c && c.dist < 0) {
      const a = side[c.geom1], b = side[c.geom2], part = a.cart ?? b.cart, scene = a.scene ?? b.scene;
      if (part && scene) { const k = part + '|' + scene, o = best.get(k); if (!o || c.dist < o.depth) best.set(k, { part, scene, depth: c.dist }); }
    }
    (c as { delete?: () => void } | undefined)?.delete?.();
  }
  (contacts as { delete?: () => void }).delete?.();
  return [...best.values()];
}
export const clashWords = (cl: Clash[]) => cl.map((c) => `${c.part} on ${c.scene} (${(-c.depth * 1000).toFixed(0)} mm)`).join(', ');

export interface RollCell { roll: number; own: Attempt; withNeighbour: Attempt }
export interface SweepTarget { id: string; kind: 'hole' | 'pod'; label: string; cells: RollCell[]; best: RollCell | null; bestAngle: number | null; colour90: 'green' | 'amber' | 'red'; cell90: RollCell }
export interface Travel { roll: number; touches: Scenery[]; worst: number; where: string }
export interface Sweep { angles: number[]; targets: SweepTarget[]; counts: Array<{ roll: number; holes: number; pods: number; holesClear: number; podsClear: number }>; mostRoll: number; travel: Travel[]; poseClashes: number }

/** Drives the cart (arm folded) up and down leg A at every roll and lists what it touches on the way. */
export function travelCheck(rig: Rig, side: ReturnType<typeof classifier>, rolls: number[]): Travel[] {
  const out: Travel[] = [];
  for (const roll of rolls) {
    const set = new Set<Scenery>(); let worst = 0, where = '';
    for (const st of stations('leg A', roll)) {
      rig.pose(st, { A: 0, B: 0, C: 0, D: 0, E: 0 }, 0);
      for (const c of clashes(rig.model, rig.data, side)) { if (c.scene !== 'riding leg') set.add(c.scene); if (c.scene !== 'riding leg' && c.depth < worst) { worst = c.depth; where = `${c.part} on ${c.scene} at ${st.at.toFixed(2)} m`; } }
    }
    out.push({ roll, touches: SCENERY.filter((s) => set.has(s)), worst, where });
  }
  return out;
}

/** The whole sweep; `onProgress` is called after each roll angle. */
export async function runSweep(mujoco: MainModule, model: MjModel, data: MjData, angles = SWEEP_ANGLES, onProgress?: (done: number, total: number) => Promise<void> | void): Promise<Sweep> {
  const rig = new Rig(mujoco, model, data), saved = new Map<number, [number, number]>(), side = classifier(model);
  const targets = [
    ...HOLES.map((h) => { const d = seatDir(h); return { id: h.id, kind: 'hole' as const, label: `Hole ${h.n}`, pos: seatCapTop(h), axis: [-d[0], -d[1], -d[2]] as [number, number, number], out: d, body: `plug${h.n}` }; }),
    ...PODS.map((p) => ({ id: p.id, kind: 'pod' as const, label: `Pod ${p.n}`, pos: podCapTop(p), axis: [0, 0, -1] as [number, number, number], out: [0, 0, 1] as [number, number, number], body: `pod${p.n}` })),
  ];
  const res: SweepTarget[] = targets.map((t) => ({ id: t.id, kind: t.kind, label: t.label, cells: [], best: null, bestAngle: null, colour90: 'red', cell90: null as unknown as RollCell }));
  let done = 0;
  for (const roll of angles) {
    const sts = stations('leg A', roll);
    targets.forEach((t, i) => {
      setTargetCollide(model, [t.body], false, saved);
      setGhostCollide(model, false); const own = attempt(rig, sts, t.pos, t.axis, t.out);
      setGhostCollide(model, true); const withNeighbour = own.ok ? attempt(rig, sts, t.pos, t.axis, t.out) : own;
      setGhostCollide(model, false);
      setTargetCollide(model, [t.body], true, saved);
      res[i].cells.push({ roll, own, withNeighbour });
    });
    await onProgress?.(++done, angles.length);
  }
  for (const t of res) {
    const ok = t.cells.filter((c) => c.withNeighbour.ok).sort((a, b) => b.withNeighbour.margin! - a.withNeighbour.margin!);
    const okOwn = t.cells.filter((c) => c.own.ok).sort((a, b) => b.own.margin! - a.own.margin!);
    t.best = ok[0] ?? okOwn[0] ?? null; t.bestAngle = t.best ? t.best.roll : null;
    t.cell90 = t.cells.find((c) => c.roll === TURN_90)!;
    t.colour90 = t.cell90?.withNeighbour.ok ? 'green' : t.best ? 'amber' : 'red';
  }
  const counts = angles.map((roll) => { const cs = res.map((t) => t.cells.find((c) => c.roll === roll)!); const n = (k: 'hole' | 'pod', f: (c: RollCell) => boolean) => res.filter((t, i) => t.kind === k && f(cs[i])).length;
    return { roll, holes: n('hole', (c) => c.own.ok), pods: n('pod', (c) => c.own.ok), holesClear: n('hole', (c) => c.withNeighbour.ok), podsClear: n('pod', (c) => c.withNeighbour.ok) }; });
  const mostRoll = counts.reduce((a, b) => (b.holesClear + b.podsClear > a.holesClear + a.podsClear ? b : a)).roll;
  // check every found pose again, everything switched on: nothing may touch
  setGhostCollide(model, true);
  let poseClashes = 0;
  for (const t of res) for (const c of t.cells) if (c.withNeighbour.ok) {
    const tt = targets.find((x) => x.id === t.id)!;
    setTargetCollide(model, [tt.body], false, saved);
    rig.pose(c.withNeighbour.station!, c.withNeighbour.joints!, JAW_CAP_DEG);
    if (clashes(model, data, side).length) poseClashes++;
    setTargetCollide(model, [tt.body], true, saved);
  }
  setGhostCollide(model, false);
  const travel = travelCheck(rig, side, angles);
  setGhostCollide(model, true);
  const travelWith = travelCheck(rig, side, angles);
  setGhostCollide(model, false);
  travel.forEach((t, i) => { t.touches = SCENERY.filter((s) => t.touches.includes(s) || travelWith[i].touches.includes(s)); if (travelWith[i].worst < t.worst) { t.worst = travelWith[i].worst; t.where = travelWith[i].where; } });
  return { angles, targets: res, counts, mostRoll, travel, poseClashes };
}
