// Pod-grab world and controller. Everything steps in simulated time, so a run is repeatable from its seed.
//
// Sim assumptions:
//  - The cart and the arm base are mocap bodies; the pods are free bodies with real contact: they slide down the store
//    slope under gravity, stop at the front stop, are held back by the rails and the roof, and stand in the silicone
//    collars of the tray when they are let go.
//  - Hooking is kinematic: when the pin has been pushed through the hole of the pod in position 0 (within HOLE_TOL of
//    the hole axis) the pod hangs on the pin (an expanding collet at the pin tip in the real hand) and the pod pose is
//    written from the hand every step, with its velocity, so it pushes what it touches.
//  - Perception noise: the controller sees hole and cell positions with a Gaussian error (default 0.8 mm per axis).
import type { CommandLayer } from '../commands.ts';
import type { SimDriver } from '../drivers/simDriver.ts';
import { MOTORS } from '../model.ts';
import { solveTool, toolPoint, type Joints } from '../arm/kinematics.ts';
import { gauss, rng } from '../arm/placement.ts';
import {
  ARM_BASE_Z, ARM_Y, CART_HOME_X, CART_SPEED, CART_X_MAX, CART_X_MIN, PIN_SPEED, PIPE_Y, PIPE_Z, POD_COUNT, POD_LEN, POD_R,
  POD_PITCH, ROW_PITCH, SEAT_SPEED, TOOL_X, STORE_CAP, STORE_N, STORE_PITCH_DEG, STORE_ROWS, STORE_START, TRANSIT_Z, TRAY_SLOTS, CELL_R,
  YAW_QUAT, armBasePos, podName, rowX, seatPos, slopeS, slotLabel, startPos, STORE_QUAT, UPRIGHT_QUAT,
} from './layout.ts';

export const HOLE_TOL = 0.0035;   // m, pin axis to hole axis (hole 7 mm radius, pin 3 mm radius, 0.5 mm margin)
export const COLLAR_TOL = CELL_R - POD_R - 0.0004; // m, pod axis to the collar axis when it is lowered into the cell
const APPROACH = 0.09;            // m above the pod, along its axis, where the pin waits before it goes in

type V3 = [number, number, number];
type Mat = number[];
const mulV = (R: Mat, v: number[]): V3 => [
  R[0] * v[0] + R[1] * v[1] + R[2] * v[2], R[3] * v[0] + R[4] * v[1] + R[5] * v[2], R[6] * v[0] + R[7] * v[1] + R[8] * v[2]];
const quatOf = (R: Mat): number[] => {
  const t = R[0] + R[4] + R[8];
  if (t > 0) { const s = Math.sqrt(t + 1) * 2; return [s / 4, (R[7] - R[5]) / s, (R[2] - R[6]) / s, (R[3] - R[1]) / s]; }
  if (R[0] > R[4] && R[0] > R[8]) { const s = Math.sqrt(1 + R[0] - R[4] - R[8]) * 2; return [(R[7] - R[5]) / s, s / 4, (R[1] + R[3]) / s, (R[2] + R[6]) / s]; }
  if (R[4] > R[8]) { const s = Math.sqrt(1 + R[4] - R[0] - R[8]) * 2; return [(R[2] - R[6]) / s, (R[1] + R[3]) / s, s / 4, (R[5] + R[7]) / s]; }
  const s = Math.sqrt(1 + R[8] - R[0] - R[4]) * 2; return [(R[3] - R[1]) / s, (R[2] + R[6]) / s, (R[5] + R[7]) / s, s / 4];
};

type State = 'store' | 'held' | 'tray' | 'lost';
interface Pod { state: State; slot: number }

/** Pods (free bodies in the sim), the cart position and the bookkeeping of where each pod is. */
export class PodWorld {
  readonly pods: Pod[] = [];
  cartX = CART_HOME_X;
  private last: V3 | null = null;

  readonly sim: SimDriver;
  constructor(sim: SimDriver) { this.sim = sim; this.reset(); }

  reset() {
    this.sim.reset();
    this.cartX = CART_HOME_X;
    this.last = null;
    this.pods.length = 0;
    for (let i = 0; i < POD_COUNT; i++) this.pods.push({ state: 'store', slot: -1 });
    this.write();
  }

  /** Current pod centre, from the sim. */
  pos(i: number): V3 { return this.sim.bodyPose(podName(i)).pos as V3; }
  /** Position of a pod along the store slope: 0 at the pick line, one pitch per pod. */
  slopePos(i: number): number { const p = this.pos(i); return slopeS(p[1], p[2]); }

  /** Pod ids in a store row, front (pick line) first. */
  rowPods(row: number): number[] {
    const ids: number[] = [];
    this.pods.forEach((p, i) => {
      if (p.state === 'store' && Math.abs(this.pos(i)[0] - rowX(row)) < ROW_PITCH / 2 && this.pos(i)[2] > 0.2) ids.push(i);
    });
    return ids.sort((a, b) => this.slopePos(a) - this.slopePos(b));
  }
  rowCount(row: number): number { return this.rowPods(row).length; }
  /** The pod resting in position 0 of a row (against the front stop), or -1. */
  frontPod(row: number): number {
    const ids = this.rowPods(row);
    return ids.length > 0 && Math.abs(this.slopePos(ids[0])) < 0.004 ? ids[0] : -1;
  }
  trayPod(slot: number): number { return this.pods.findIndex((p) => p.state === 'tray' && p.slot === slot); }
  get trayCount(): number { return this.pods.filter((p) => p.state === 'tray').length; }
  get storeCount(): number { return this.pods.filter((p) => p.state === 'store').length; }

  setCart(x: number) { this.cartX = Math.min(CART_X_MAX, Math.max(CART_X_MIN, x)); }

  /** The pod on the pin follows the hand (pose and velocity), pod axis along the pin. */
  carry(i: number, h: number) {
    const R = this.sim.bodyPose('hand').rot, hp = this.sim.bodyPose('hand').pos;
    const o = mulV(R, [TOOL_X, 0, 0]);
    const pos: V3 = [hp[0] + o[0], hp[1] + o[1], hp[2] + o[2]];
    const RQ = [-R[2], R[1], R[0], -R[5], R[4], R[3], -R[8], R[7], R[6]];
    const vel = this.last ? pos.map((v, k) => (v - this.last![k]) / h) : [0, 0, 0];
    this.last = pos;
    this.sim.setFreeBody(podName(i), pos, quatOf(RQ), vel);
  }
  /** Let go of a carried pod: it is a free body again. */
  release() { this.last = null; }

  tick(_h: number) { this.write(); }

  write() {
    this.sim.setMocap('cart', [this.cartX, PIPE_Y, PIPE_Z]);
    this.sim.setMocap('base', armBasePos(this.cartX), YAW_QUAT);
  }

  /** Pin axis point in world coordinates, from the real hand pose. */
  pin(): V3 {
    const h = this.sim.bodyPose('hand');
    const o = mulV(h.rot, [TOOL_X, 0, 0]);
    return [h.pos[0] + o[0], h.pos[1] + o[1], h.pos[2] + o[2]];
  }
}

// --- controller --------------------------------------------------------------------------------------------------------
const CTRL_STEPS = 10;         // control tick every 10 physics steps = 50 Hz at 2 ms
const JOINT_SPEED = 60;        // deg/s (joint-space move)
const TRACK_TOL = 0.4;         // deg, "arrived" band for the arm joints
const DWELL_TICKS = 3;
const MOVE_TIMEOUT = 10;       // s
const RUN_TIMEOUT = 900;       // s

export interface Job { row: number; slot: number }
export interface JobResult { job: Job; success: boolean; reason: string; posErrMm: number; durationS: number }

interface Move {
  label: string;
  /** Goal: cart x, pin reach r (from the arm axis) and pin height z (world). Missing = keep. */
  x?: number; r?: number; z?: number; pitch?: number;  // pitch: hand pitch in degrees, 90 = pin straight down
  wait?: number;              // s to stay at the goal (lets a released pod settle)
  joint?: boolean;            // joint-space move to the IK pose of the goal
  speed?: number;             // pin speed m/s
  after?: () => string | void; // runs when the move has finished; a string fails the job
}

export interface TaskConfig { jobs: Job[]; seed: number; noiseMm?: number }

/** Plans and runs a list of pick-and-place jobs: store row -> tray socket. */
export class PodTask {
  readonly results: JobResult[] = [];
  done = false;
  failReason = '';

  private moves: Move[] = [];
  private mi = 0;
  private ji = 0;
  private startOfMove = true;
  private moveTime = 0;
  private dwell = 0;
  private steps = 0;
  private cmdJ: number[] = [0, 0, 0, 0, 0];
  private integ = [0, 0, 0, 0, 0];
  private from = { x: 0, r: 0, z: 0, p: 90 };
  private goal = { x: 0, r: 0, z: 0, p: 90 };
  private goalJ: Joints | null = null;
  private dur = 0;
  private rand: () => number;
  private podId = -1;
  private jobStart = 0;
  private inited = false;

  readonly world: PodWorld;
  readonly cfg: TaskConfig;
  private cmd: CommandLayer;

  constructor(world: PodWorld, cmd: CommandLayer, cfg: TaskConfig) {
    this.world = world; this.cmd = cmd; this.cfg = cfg;
    this.rand = rng(cfg.seed ^ 0x9e3779b9);
    if (cfg.jobs.length === 0) { this.done = true; return; }
    this.planJob();
  }

  get time(): number { return this.steps * this.world.sim.model.opt.timestep; }
  get jobIndex(): number { return Math.min(this.ji, this.cfg.jobs.length - 1); }
  get job(): Job { return this.cfg.jobs[this.jobIndex]; }
  get label(): string { return this.done ? 'Done' : this.moves[this.mi].label; }

  advance(maxSimSeconds: number): boolean {
    const sim = this.world.sim, h = sim.model.opt.timestep;
    const n = Math.max(1, Math.round(maxSimSeconds / h));
    for (let i = 0; i < n && !this.done; i++) {
      if (this.steps % CTRL_STEPS === 0) this.control();
      if (this.done) break;
      sim.step();
      this.steps++;
      if (this.podId >= 0) this.world.carry(this.podId, h);
      this.world.tick(h);
      if (this.time > RUN_TIMEOUT) this.fail('timeout (run)');
    }
    return this.done;
  }

  // --- planning
  private noise(): number { return gauss(this.rand) * (this.cfg.noiseMm ?? 0.8) / 1000; }

  private planJob() {
    const { row, slot } = this.cfg.jobs[this.ji];
    const w = this.world;
    const front = w.frontPod(row);
    if (front < 0) return this.fail(`store row ${row + 1} is empty`);
    if (w.trayPod(slot) >= 0) return this.fail(`socket ${slotLabel(slot)} is already filled`);
    this.jobStart = this.time;
    const hole = w.pos(front), seat = seatPos(slot);
    // What the controller sees: the pod and the cell with a little noise.
    const T: V3 = [hole[0] + this.noise(), hole[1] + this.noise(), hole[2] + this.noise()];
    const S: V3 = [seat[0] + this.noise(), seat[1] + this.noise(), seat[2] + this.noise()];
    const A: V3 = [T[0], T[1] + APPROACH * STORE_N[1], T[2] + APPROACH * STORE_N[2]];   // above the pod, on its axis
    const id = front;
    const r = (y: number) => y - ARM_Y;
    const pin = (): V3 => w.pin();
    this.moves = [
      { label: 'Raising the arm', joint: true, r: r(A[1]), z: A[2], pitch: STORE_PITCH_DEG },
      { label: `Driving to store row ${row + 1}`, x: T[0], r: r(A[1]), z: A[2] },
      {
        label: 'Pin down through the lid and the pod hole', r: r(T[1]), z: T[2], speed: SEAT_SPEED,
        after: () => {
          const p = pin(), c = w.pos(id), d = [p[0] - c[0], p[1] - c[1], p[2] - c[2]];
          const along = d[0] * STORE_N[0] + d[1] * STORE_N[1] + d[2] * STORE_N[2];
          const lat = Math.hypot(d[0] - along * STORE_N[0], d[1] - along * STORE_N[1], d[2] - along * STORE_N[2]);
          if (lat > HOLE_TOL) return 'missed the pod hole in the store';
          if (Math.abs(along) > POD_LEN / 2) return 'pin not through the pod';
          this.podId = id; w.pods[id].state = 'held';
        },
      },
      { label: 'Lifting the pod up through the lid', r: r(A[1]), z: A[2], speed: SEAT_SPEED },
      { label: 'Clearing the lid', r: r(A[1]), z: TRANSIT_Z, pitch: 90, speed: PIN_SPEED },
      { label: `Driving to socket ${slotLabel(slot)}`, x: S[0], r: r(S[1]), z: TRANSIT_Z },
      {
        label: 'Lowering the pod into the silicone collar', z: S[2], speed: SEAT_SPEED,
        after: () => {
          const c = w.pos(id), e = Math.hypot(c[0] - seat[0], c[1] - seat[1]);
          if (e > COLLAR_TOL) return `missed the collar of socket ${slotLabel(slot)} (${(e * 1000).toFixed(1)} mm off)`;
          this.podId = -1; w.release(); w.pods[id].state = 'lost';
        },
      },
      { label: 'Backing the pin out', z: TRANSIT_Z, speed: PIN_SPEED },
      {
        label: 'Letting the pod settle', wait: 0.5,
        after: () => {
          const c = w.pos(id), err = Math.hypot(c[0] - seat[0], c[1] - seat[1]);
          if (err > 0.004 || Math.abs(c[2] - seat[2]) > 0.004) return `pod did not stay in the collar of socket ${slotLabel(slot)}`;
          w.pods[id].state = 'tray'; w.pods[id].slot = slot;
          this.results.push({ job: this.cfg.jobs[this.ji], success: true, reason: 'seated', posErrMm: Math.round(err * 10000) / 10, durationS: 0 });
        },
      },
    ];
    this.mi = 0;
    this.startOfMove = true;
  }

  private fail(reason: string) {
    if (this.done) return;
    this.failReason = reason;
    this.done = true;
    if (this.podId >= 0) this.podId = -1;
  }

  // --- control
  private measured(): number[] {
    const j = this.cmd.readJoints() ?? {};
    return MOTORS.map((m) => j[m.id] ?? 0);
  }

  private send(q: number[]) { MOTORS.forEach((m, i) => { this.cmd.setJointTarget(m.id, q[i] ?? 0); }); }

  /** Planar IK for the pin point at (r, z) with the hand pitched by `pitch` degrees (90 = pin straight down). */
  private ik(r: number, z: number, pitch: number): Joints | null {
    return solveTool(r, 0, z - ARM_BASE_Z, TOOL_X, 0, pitch);
  }

  private control() {
    const dt = CTRL_STEPS * this.world.sim.model.opt.timestep;
    const q = this.measured();
    const mv = this.moves[this.mi];

    if (this.startOfMove) {
      this.startOfMove = false;
      this.moveTime = 0; this.dwell = 0;
      if (!this.inited) { this.inited = true; this.cmdJ = q.slice(0, 5); this.integ = [0, 0, 0, 0, 0]; }
      const p = toolPoint({ A: this.cmdJ[0], B: this.cmdJ[1], C: this.cmdJ[2], D: this.cmdJ[3] }, TOOL_X, 0);
      this.from = { x: this.world.cartX, r: p[0], z: p[2] + ARM_BASE_Z, p: this.cmdJ[1] + this.cmdJ[2] + this.cmdJ[3] };
      this.goal = { x: mv.x ?? this.from.x, r: mv.r ?? this.from.r, z: mv.z ?? this.from.z, p: mv.pitch ?? this.from.p };
      if (mv.joint) { this.goal.r = mv.r ?? this.from.r; }
      this.goalJ = this.ik(this.goal.r, this.goal.z, this.goal.p);
      if (!this.goalJ) return this.fail(`unreachable (${mv.label})`);
      const dArm = Math.hypot(this.goal.r - this.from.r, this.goal.z - this.from.z);
      const dCart = Math.abs(this.goal.x - this.from.x);
      this.dur = Math.max(dArm / (mv.speed ?? PIN_SPEED), dCart / CART_SPEED, mv.wait ?? 0, 1e-3);
    }
    this.moveTime += dt;
    const u = Math.min(1, this.moveTime / this.dur);
    let arrived = u >= 1;
    this.world.setCart(this.from.x + (this.goal.x - this.from.x) * u);
    if (mv.joint && this.goalJ) {
      const gj = [this.goalJ.A, this.goalJ.B, this.goalJ.C, this.goalJ.D, this.goalJ.E];
      arrived = true;
      for (let i = 0; i < 5; i++) {
        const d = gj[i] - this.cmdJ[i], s = JOINT_SPEED * dt;
        this.cmdJ[i] += Math.abs(d) <= s ? d : Math.sign(d) * s;
        if (Math.abs(gj[i] - this.cmdJ[i]) > 1e-6) arrived = false;
      }
      if (this.world.cartX !== this.goal.x) arrived = false;
    } else {
      const j = this.ik(this.from.r + (this.goal.r - this.from.r) * u, this.from.z + (this.goal.z - this.from.z) * u, this.from.p + (this.goal.p - this.from.p) * u);
      if (!j) return this.fail(`unreachable (${mv.label})`);
      this.cmdJ = [j.A, j.B, j.C, j.D, j.E];
    }

    // Gravity / tracking integrator on the arm joints (a servo with only P gain sags under load).
    for (let i = 0; i < 5; i++) {
      this.integ[i] += 4 * (this.cmdJ[i] - q[i]) * dt;
      this.integ[i] = Math.max(-8, Math.min(8, this.integ[i]));
    }
    this.send([...this.cmdJ.map((v, i) => v + this.integ[i]), 0]);

    let settled = arrived;
    if (settled) for (let i = 0; i < 4; i++) if (Math.abs(q[i] - this.cmdJ[i]) > TRACK_TOL) settled = false;
    this.dwell = settled ? this.dwell + 1 : 0;
    if (this.moveTime > MOVE_TIMEOUT + this.dur) return this.fail(`timeout (${mv.label})`);
    if (this.dwell < DWELL_TICKS) return;

    const err = mv.after?.();
    if (typeof err === 'string') return this.fail(err);
    this.mi++;
    this.startOfMove = true;
    if (this.mi >= this.moves.length) {
      const r = this.results[this.results.length - 1];
      if (r) r.durationS = Math.round((this.time - this.jobStart) * 10) / 10;
      this.ji++;
      if (this.ji >= this.cfg.jobs.length) { this.done = true; return; }
      this.planJob();
    }
  }
}

/** Jobs that fill the tray (sockets in order A1..D4), taking pods from the store row by row, nearest row first. */
export function fillJobs(world: PodWorld): Job[] {
  const jobs: Job[] = [];
  const left = Array.from({ length: STORE_ROWS }, (_, r) => world.rowCount(r));
  for (let s = 0; s < TRAY_SLOTS; s++) {
    if (world.trayPod(s) >= 0) continue;
    const row = left.findIndex((n) => n > 0);
    if (row < 0) break;
    left[row]--;
    jobs.push({ row, slot: s });
  }
  return jobs;
}
