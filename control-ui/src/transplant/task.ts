// Transplant scene logic: a scripted, kinematic choreography (like the Transfer scene), no physics. The arm is posed by analytic IK, the cart and the pods are placed,
// and every frame a contact check (mj_forward) must find nothing touching.
// One trip, four steps (decided with Dani): 1 pick a seedling pod from the tray and put it in the cart's pod holder, 2 the cart drives up to the target hole,
// 3 the arm pulls the plug out of the collar and parks it in the plug holder, 4 the arm takes the pod from the holder and seats it in the hole.
// The hole is open from the moment the plug leaves its seat until the pod is seated; step 3 ends with the hand already waiting at the holder so step 4 starts straight on the pod.
import { solvePlanar, toolPoint } from '../arm/kinematics.ts';
import {
  BODIES, CART_Z0, CART_Z1, CUP_CAP_TOP_REL, D_CUP, D_PARK, D_SEAT, GRIP_TX, GRIP_TZ, JAW_CAP_DEG, JAW_OPEN_DEG, PARK_CAP_TOP, S, SEAT_CAP_TOP, TRAY_CAP_TOP, TRAY_T, TRAY_Y, XB, XT, quatZ,
  POD_BODY_L, CAP_T,
} from './layout.ts';

type V3 = [number, number, number];
const DEG = 180 / Math.PI;

/** Hand pose in world terms: the cap-top point (x, z; y is 0, the arm plane) and the pitch phi: the hand points along (sin phi, -cos phi) in (x, z). phi 0 = straight down, -45 = down and towards the pipe, -90 = horizontal towards the pipe, +45 = down and towards the cart. */
export interface Tool { x: number; z: number; phi: number }
export const toolOf = (p: V3, axisIn: V3): Tool => ({ x: p[0], z: p[2], phi: Math.atan2(axisIn[0], -axisIn[2]) * DEG });
/** Unit vector the hand points along, in world coordinates. */
export const handDir = (phi: number): V3 => [Math.sin(phi / DEG), 0, -Math.cos(phi / DEG)];
const add = (a: V3, b: V3, k = 1): V3 => [a[0] + b[0] * k, a[1] + b[1] * k, a[2] + b[2] * k];
const neg = (a: V3): V3 => [-a[0], -a[1], -a[2]];

export interface Joints { A: number; B: number; C: number; D: number; E: number }
/** Joint angles (deg) that put the cap-top point at the tool pose with the cart at height cartZ; null when out of reach or past a joint limit. */
export function ikTool(t: Tool, cartZ: number): Joints | null {
  return solvePlanar(0, cartZ - t.z, XB - t.x, GRIP_TX, GRIP_TZ, t.phi);
}

// --- the places a pod or plug can be
export type Place = 'tray' | 'cup' | 'seat' | 'park' | 'hand';
export interface Obj { place: Place }
export const OBJECTS = ['pod', 'plug'] as const;
export type ObjName = typeof OBJECTS[number];

/** Cap-top point and axis (into the part) of a part at a fixed place, for a cart at cartZ. */
export function placePose(place: Exclude<Place, 'hand'>, cartZ: number): { pos: V3; axis: V3 } {
  switch (place) {
    case 'tray': return { pos: TRAY_CAP_TOP, axis: [0, 0, -1] };
    case 'cup': return { pos: [XT + CUP_CAP_TOP_REL[0], CUP_CAP_TOP_REL[1], cartZ + CUP_CAP_TOP_REL[2]], axis: neg(D_CUP) };
    case 'seat': return { pos: SEAT_CAP_TOP, axis: neg(D_SEAT) };
    case 'park': return { pos: PARK_CAP_TOP, axis: neg(D_PARK) };
  }
}

// --- speeds
export const V_FREE = 0.15, V_SLOW = 0.05, W_DEG_S = 60, JAW_DEG_S = 120, CART_M_S = 0.25;
export const OPEN_BOOST = 2;       // speed-up of the free moves while the hole is open (the slow insertions stay slow)
export const APPROACH = 0.07;      // m: where the hand waits in front of a seat, along its axis
export const SLOW_LEN = 0.035;     // m: the last stretch into a seat and the first out of it are done slowly

type Action =
  | { t: 'move'; to: Tool; slow?: boolean; free?: boolean }
  | { t: 'jaw'; deg: number }
  | { t: 'attach'; obj: ObjName }
  | { t: 'place'; obj: ObjName; at: Exclude<Place, 'hand'> }
  | { t: 'cart'; z: number }
  | { t: 'mark'; what: 'open' | 'closed' };

export interface StepInfo { id: string; title: string; text: string }
export const STEPS: readonly StepInfo[] = [
  { id: 'pick', title: '1. Pick a seedling', text: 'At the seedling tray the arm picks a seedling pod by its cap, lifts it out and puts it in the pod holder on the cart.' },
  { id: 'drive', title: '2. Drive to the hole', text: 'The cart drives up the track to the target hole on the central pipe, the arm folded.' },
  { id: 'plug', title: '3. Park the plug', text: 'The arm pulls the plug out of the hole, tilts it from 45° to horizontal and parks it in the collar\'s plug holder, then waits at the pod holder.' },
  { id: 'insert', title: '4. Seat the seedling', text: 'The arm takes the seedling pod from the cart holder and pushes it into the hole.' },
];

const at = (p: V3, d: V3, u: number): V3 => add(p, d, u);
/** The hand pose for a part at a place, and for the approach point `APPROACH` out along its seat axis `out`. */
const gripAt = (place: Exclude<Place, 'hand'>, cartZ: number): Tool => { const p = placePose(place, cartZ); return toolOf(p.pos, p.axis); };
const OUT: Record<Exclude<Place, 'hand'>, V3> = { tray: [0, 0, 1], cup: D_CUP, seat: D_SEAT, park: D_PARK };
const APPROACH_AT: Record<Exclude<Place, 'hand'>, number> = { tray: 0.07, cup: 0.07, seat: 0.06, park: 0.05 };   // park is shorter: the arm is nearly stretched out horizontally there
const approachAt = (place: Exclude<Place, 'hand'>, cartZ: number, dist = APPROACH_AT[place]): Tool => {
  const p = placePose(place, cartZ), a = toolOf(p.pos, p.axis), o = at(p.pos, OUT[place], dist);
  return { x: o[0], z: o[2], phi: a.phi };
};
/** The folded pose the arm rests in while it drives: above the seedling tray, hand straight down. */
export const STOW_Z_ABOVE = 0.07;
const stow = (cartZ: number): Tool => ({ x: TRAY_CAP_TOP[0], z: cartZ - 0.15, phi: 0 });
export const stowTool = stow;

/** A free point between the cup's approach and the collar's, where the hand has turned most of the way (found by searching the transit with the contact check: the straight joint-space move grazes the collar's rim). */
const VIA_SEAT: Tool = { x: 0.16, z: 0.92, phi: -20 };

/** Actions of step i (0..3). */
export function planStep(i: number): Action[] {
  const z0 = CART_Z0, z1 = CART_Z1, A: Action[] = [];
  /** A straight line of the hand (slow ones go into or out of a seat) or, with free, a move in joint space between two poses that is checked for contacts instead. */
  const m = (to: Tool, slow = false, free = false) => A.push({ t: 'move', to, slow, free });
  if (i === 0) {
    A.push({ t: 'jaw', deg: JAW_OPEN_DEG });
    m(approachAt('tray', z0)); m(gripAt('tray', z0), true);
    A.push({ t: 'jaw', deg: JAW_CAP_DEG }, { t: 'attach', obj: 'pod' });
    m(approachAt('tray', z0), true);
    m(approachAt('cup', z0, 0.1), false, true);
    m(approachAt('cup', z0)); m(gripAt('cup', z0), true);
    A.push({ t: 'place', obj: 'pod', at: 'cup' }, { t: 'jaw', deg: JAW_OPEN_DEG });
    m(approachAt('cup', z0), true); m(approachAt('cup', z0, 0.1));
    m(stow(z0), false, true);
    A.push({ t: 'jaw', deg: 0 });
  } else if (i === 1) {
    A.push({ t: 'cart', z: z1 });
  } else if (i === 2) {
    A.push({ t: 'jaw', deg: JAW_OPEN_DEG });
    m(approachAt('seat', z1)); m(gripAt('seat', z1), true);
    A.push({ t: 'jaw', deg: JAW_CAP_DEG }, { t: 'attach', obj: 'plug' }, { t: 'mark', what: 'open' });
    m(approachAt('seat', z1), true);
    m(approachAt('park', z1));
    m(gripAt('park', z1), true);
    A.push({ t: 'place', obj: 'plug', at: 'park' }, { t: 'jaw', deg: JAW_OPEN_DEG });
    m(approachAt('park', z1), true);
    m(approachAt('cup', z1, 0.1), false, true);
    m(approachAt('cup', z1));
  } else {
    m(gripAt('cup', z1), true);
    A.push({ t: 'jaw', deg: JAW_CAP_DEG }, { t: 'attach', obj: 'pod' });
    m(approachAt('cup', z1), true);
    m(VIA_SEAT, false, true);
    m(approachAt('seat', z1));
    m(gripAt('seat', z1), true);
    A.push({ t: 'mark', what: 'closed' }, { t: 'place', obj: 'pod', at: 'seat' }, { t: 'jaw', deg: JAW_OPEN_DEG });
    m(approachAt('seat', z1), true);
    m(stow(z1), false, true);
    A.push({ t: 'jaw', deg: 0 });
  }
  return A;
}

export interface Pose { cartZ: number; tool: Tool; jaw: number; places: Record<ObjName, Place> }
export const initialPose = (): Pose => ({ cartZ: CART_Z0, tool: stow(CART_Z0), jaw: 0, places: { pod: 'tray', plug: 'seat' } });

/** Where a part is in the world, for a pose. */
export function objectPose(p: Pose, o: ObjName): { pos: V3; axis: V3 } {
  const pl = p.places[o];
  if (pl !== 'hand') return placePose(pl, p.cartZ);
  return { pos: [p.tool.x, 0, p.tool.z], axis: handDir(p.tool.phi) };
}
export const objectQuat = (p: Pose, o: ObjName) => quatZ(objectPose(p, o).axis);

/** Runs the four steps one at a time or all together. Times are simulated seconds; `speed` scales them. */
export class TransplantRun {
  pose: Pose = initialPose();
  next = 0;                       // the step to run next
  speed = 1;
  /** seconds the hole was open (plug out of its seat, pod not yet in), and since when */
  holeOpenS = 0;
  holeOpen = false;
  holeTimes: number[] = [];       // seconds per completed open period
  private queue: Action[] = [];
  private seg: { from: Tool; to: Tool; dur: number; t: number; j?: [Joints, Joints] } | null = null;
  private wait: { until: number; t: number; from: number; to: number } | null = null;
  private cartSeg: { from: number; to: number; dur: number; t: number } | null = null;
  private playing = false;
  /** Set when the IK could not reach a pose (the scene shows it as a failure). */
  unreachable = '';
  label = 'Ready';

  get busy() { return this.queue.length > 0 || this.seg !== null || this.wait !== null || this.cartSeg !== null; }
  get done() { return this.next >= STEPS.length && !this.busy; }

  reset() {
    this.pose = initialPose(); this.next = 0; this.queue = []; this.seg = null; this.wait = null; this.cartSeg = null; this.playing = false;
    this.holeOpenS = 0; this.holeOpen = false; this.holeTimes = []; this.unreachable = ''; this.label = 'Ready';
  }
  /** Run the next step (one press). */
  step() { if (!this.busy && this.next < STEPS.length) { this.queue = planStep(this.next); this.label = STEPS[this.next].title; this.next++; } }
  /** Run everything that is left. */
  playAll() { this.playing = true; this.step(); }
  stop() { this.queue = []; this.seg = null; this.wait = null; this.cartSeg = null; this.playing = false; }

  private start(a: Action) {
    const p = this.pose;
    if (a.t === 'move') {
      const d = Math.hypot(a.to.x - p.tool.x, a.to.z - p.tool.z);
      const boost = this.holeOpen ? OPEN_BOOST : 1;   // the hole is open: the arm moves faster
      let dur = Math.max(d / ((a.slow ? V_SLOW : V_FREE) * (a.slow ? 1 : boost)), Math.abs(a.to.phi - p.tool.phi) / (W_DEG_S * boost), 0.05);
      let j: [Joints, Joints] | undefined;
      if (a.free) {
        const j0 = ikTool(p.tool, p.cartZ), j1 = ikTool(a.to, p.cartZ);
        if (j0 && j1) { j = [j0, j1]; dur = Math.max(dur, ...(['B', 'C', 'D'] as const).map((k) => Math.abs(j1[k] - j0[k]) / (W_DEG_S * boost))); }
      }
      this.seg = { from: { ...p.tool }, to: a.to, dur, t: 0, j };
    } else if (a.t === 'jaw') {
      this.wait = { until: Math.abs(a.deg - p.jaw) / JAW_DEG_S, t: 0, from: p.jaw, to: a.deg };
    } else if (a.t === 'cart') {
      this.cartSeg = { from: p.cartZ, to: a.z, dur: Math.abs(a.z - p.cartZ) / CART_M_S, t: 0 };
    } else if (a.t === 'attach') p.places[a.obj] = 'hand';
    else if (a.t === 'place') p.places[a.obj] = a.at;
    else if (a.t === 'mark') {
      if (a.what === 'open') { this.holeOpen = true; this.holeOpenS = 0; } else if (this.holeOpen) { this.holeOpen = false; this.holeTimes.push(this.holeOpenS); }
    }
  }

  /** Advance by dt seconds of wall clock (scaled by `speed`). */
  advance(dt: number) {
    let left = dt * this.speed;
    for (let guard = 0; guard < 1000 && left > 1e-9; guard++) {
      if (!this.seg && !this.wait && !this.cartSeg) {
        const a = this.queue.shift();
        if (!a) {
          if (this.playing && this.next < STEPS.length) { this.step(); continue; }
          this.playing = false; if (this.next >= STEPS.length) this.label = 'Done'; else this.label = 'Ready';
          return;
        }
        this.start(a);
        continue;
      }
      if (this.seg) {
        const s = this.seg, use = Math.min(left, s.dur - s.t);
        s.t += use; left -= use; if (this.holeOpen) this.holeOpenS += use;
        const k = s.dur > 0 ? s.t / s.dur : 1;
        if (s.j) {
          const [j0, j1] = s.j, q = { A: 0, B: j0.B + (j1.B - j0.B) * k, C: j0.C + (j1.C - j0.C) * k, D: j0.D + (j1.D - j0.D) * k };
          const [r, , zb] = toolPoint(q, GRIP_TX, GRIP_TZ);
          this.pose.tool = { x: XB - zb, z: this.pose.cartZ - r, phi: q.B + q.C + q.D };
        } else this.pose.tool = { x: s.from.x + (s.to.x - s.from.x) * k, z: s.from.z + (s.to.z - s.from.z) * k, phi: s.from.phi + (s.to.phi - s.from.phi) * k };
        if (s.t >= s.dur - 1e-12) { this.pose.tool = { ...s.to }; this.seg = null; }
      } else if (this.wait) {
        const w = this.wait, use = Math.min(left, w.until - w.t);
        w.t += use; left -= use; if (this.holeOpen) this.holeOpenS += use;
        const k = w.until > 0 ? w.t / w.until : 1;
        this.pose.jaw = w.from + (w.to - w.from) * k;
        if (w.t >= w.until - 1e-12) { this.pose.jaw = w.to; this.wait = null; }
      } else if (this.cartSeg) {
        const c = this.cartSeg, use = Math.min(left, c.dur - c.t);
        c.t += use; left -= use;
        const prev = this.pose.cartZ;
        this.pose.cartZ = c.dur > 0 ? c.from + (c.to - c.from) * (c.t / c.dur) : c.to;
        this.pose.tool = { ...this.pose.tool, z: this.pose.tool.z + (this.pose.cartZ - prev) };   // the arm is folded and rides with the cart: the hand keeps its place on the cart
        if (c.t >= c.dur - 1e-12) { this.pose.cartZ = c.to; this.cartSeg = null; }
      }
    }
  }
}

export { S, TRAY_T, TRAY_Y, POD_BODY_L, CAP_T, BODIES };
