// Pod-grab world and controller. Everything steps in simulated time, so a run is repeatable from its seed.
//
// Sim assumptions (the model has no contact physics, see model.ts):
//  - Pods, the cart and the arm base are mocap bodies; their poses are set from state kept here.
//  - Hooking is kinematic: when the pin has been pushed through the hole of the pod in position 0 (within HOLE_TOL of
//    the hole axis) and raised until it touches the top of the hole, the pod hangs on the pin.
//  - Seating is kinematic: pushed onto a peg within PEG_TOL, the pod rests on the peg and the pin backs out of it.
//  - Pods behind a lifted pod slide down the 5 degree slope under gravity, one position forward.
//  - Perception noise: the controller sees hole and peg positions with a Gaussian error (default 0.8 mm per axis).
import type { CommandLayer } from '../commands.ts';
import type { SimDriver } from '../drivers/simDriver.ts';
import { MOTORS } from '../model.ts';
import { solveTool, toolPoint, type Joints } from '../arm/kinematics.ts';
import { gauss, rng } from '../arm/placement.ts';
import {
  ARM_BASE_Z, CART_HOME_X, CART_SPEED, CART_X_MAX, CART_X_MIN, HOOK, PIN_SPEED, PIPE_Z, POD_COUNT, POD_LEN, R_CLEAR, R_SEAT,
  SEAT_SPEED, SLOPE, STORE_ROWS, STORE_START, TOOL_X, TRAY_SLOTS, YAW_QUAT, armBasePos, podName,
  seatPos, slotLabel, startPos, storePos,
} from './layout.ts';

export const HOLE_TOL = 0.0035;   // m, pin axis to hole axis (hole 7 mm radius, pin 3 mm radius, 0.5 mm margin)
export const PEG_TOL = 0.0035;    // m, pod centre to its seat when pushed onto a peg (hole 7 mm radius, peg 3 mm radius)

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

type Where = { kind: 'store'; row: number; k: number } | { kind: 'held' } | { kind: 'tray'; slot: number };
interface Pod { where: Where; pos: V3; quat: number[]; vel: number; dirty: boolean }

/** Pods, cart position and the gravity slide in the store. */
export class PodWorld {
  readonly pods: Pod[] = [];
  cartX = CART_HOME_X;

  readonly sim: SimDriver;
  constructor(sim: SimDriver) { this.sim = sim; this.reset(); }

  reset() {
    this.sim.reset();
    this.cartX = CART_HOME_X;
    this.pods.length = 0;
    for (let i = 0; i < POD_COUNT; i++) {
      this.pods.push({ where: { kind: 'store', row: Math.floor(i / STORE_START), k: i % STORE_START }, pos: startPos(i), quat: YAW_QUAT, vel: 0, dirty: true });
    }
    this.write();
  }

  /** Pod ids in a store row, front first. */
  rowPods(row: number): number[] {
    const ids: number[] = [];
    this.pods.forEach((p, i) => { if (p.where.kind === 'store' && p.where.row === row) ids.push(i); });
    return ids.sort((a, b) => (this.pods[a].where as { k: number }).k - (this.pods[b].where as { k: number }).k);
  }
  rowCount(row: number): number { return this.rowPods(row).length; }
  /** The pod in position 0 of a row, or -1. */
  frontPod(row: number): number {
    return this.pods.findIndex((p) => p.where.kind === 'store' && p.where.row === row && p.where.k === 0);
  }
  trayPod(slot: number): number { return this.pods.findIndex((p) => p.where.kind === 'tray' && p.where.slot === slot); }
  get trayCount(): number { return this.pods.filter((p) => p.where.kind === 'tray').length; }
  get storeCount(): number { return this.pods.filter((p) => p.where.kind === 'store').length; }

  setCart(x: number) { this.cartX = Math.min(CART_X_MAX, Math.max(CART_X_MIN, x)); }

  /** Let the pods behind a removed one slide forward one position (they keep sliding in tick()). */
  shiftRow(row: number) {
    for (const i of this.rowPods(row)) {
      const w = this.pods[i].where as { kind: 'store'; row: number; k: number };
      if (w.k > 0 && !this.rowPods(row).some((j) => (this.pods[j].where as { k: number }).k === w.k - 1)) w.k -= 1;
    }
  }

  /** Advance the pods that slide towards their store position, and write all poses. */
  tick(h: number) {
    for (const p of this.pods) {
      if (p.where.kind === 'store') {
        const goal = storePos(p.where.row, p.where.k);
        const dy = goal[1] - p.pos[1];
        if (Math.abs(dy) > 1e-6 || Math.abs(goal[2] - p.pos[2]) > 1e-6) {
          p.vel += 9.81 * Math.sin(SLOPE) * h;
          const step = p.vel * h * Math.cos(SLOPE);
          if (step >= -dy) { p.pos = goal; p.vel = 0; } else {
            const k = step / -dy;
            p.pos = [goal[0], p.pos[1] - step, p.pos[2] + (goal[2] - p.pos[2]) * k];
          }
          p.dirty = true;
        }
      }
    }
    this.write();
  }

  /** The pod on the pin follows the hand. */
  carry(i: number) {
    const h = this.sim.bodyPose('hand');
    const o = mulV(h.rot, [TOOL_X, 0, -HOOK]);
    this.pods[i].pos = [h.pos[0] + o[0], h.pos[1] + o[1], h.pos[2] + o[2]];
    this.pods[i].quat = quatOf(h.rot);
    this.pods[i].dirty = true;
  }

  write() {
    this.sim.setMocap('cart', [this.cartX, 0, PIPE_Z]);
    this.sim.setMocap('base', armBasePos(this.cartX), YAW_QUAT);
    this.pods.forEach((p, i) => { if (p.dirty) { this.sim.setMocap(podName(i), p.pos, p.quat); p.dirty = false; } });
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
const LIFT = 0.008;            // pin height above the hook point: clears the channel lip

export interface Job { row: number; slot: number }
export interface JobResult { job: Job; success: boolean; reason: string; posErrMm: number; durationS: number }

interface Move {
  label: string;
  /** Goal: cart x, pin reach r (from the arm axis) and pin height z (world). Missing = keep. */
  x?: number; r?: number; z?: number;
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
  private from = { x: 0, r: 0, z: 0 };
  private goal = { x: 0, r: 0, z: 0 };
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
      if (this.podId >= 0) this.world.carry(this.podId);
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
    const hole = w.pods[front].pos, seat = seatPos(slot);
    const hx = hole[0] + this.noise(), hz = hole[2] + this.noise();
    const sx = seat[0] + this.noise(), sz = seat[2] + this.noise();
    const id = front;
    const pin = (): V3 => w.pin();
    this.moves = [
      { label: 'Raising the arm', joint: true, r: R_CLEAR, z: hz + 0.01 },
      { label: `Driving to store row ${row + 1}`, x: hx, r: R_CLEAR, z: hz },
      {
        label: 'Pin through the pod hole', r: R_SEAT, speed: SEAT_SPEED,
        after: () => {
          const p = pin(), t = w.pods[id].pos;
          if (Math.hypot(p[0] - t[0], p[2] - t[2]) > HOLE_TOL) return 'missed the pod hole in the store';
          if (Math.abs(p[1] - t[1]) > POD_LEN / 2) return 'pin not through the pod';
        },
      },
      {
        label: 'Hooking the pod', z: hz + HOOK, speed: SEAT_SPEED,
        after: () => { this.podId = id; w.pods[id].where = { kind: 'held' }; },
      },
      { label: 'Lifting it off the channel', z: hz + HOOK + LIFT, speed: SEAT_SPEED, after: () => { w.shiftRow(row); } },
      { label: 'Pulling the pod out', r: R_CLEAR, speed: SEAT_SPEED },
      { label: `Driving to socket ${slotLabel(slot)}`, x: sx, z: sz + HOOK },
      {
        label: 'Pushing the pod onto the peg', r: R_SEAT, speed: SEAT_SPEED,
        after: () => {
          const pod = w.pods[id].pos;
          const err = Math.hypot(pod[0] - seat[0], pod[1] - seat[1], pod[2] - seat[2]);
          this.podId = -1;
          if (err > PEG_TOL) { w.pods[id].where = { kind: 'held' }; return `missed the peg of socket ${slotLabel(slot)} (${(err * 1000).toFixed(1)} mm off)`; }
          w.pods[id].where = { kind: 'tray', slot };
          w.pods[id].pos = [...seat] as V3;
          w.pods[id].quat = YAW_QUAT;
          w.pods[id].dirty = true;
          this.results.push({ job: this.cfg.jobs[this.ji], success: true, reason: 'seated', posErrMm: Math.round(err * 10000) / 10, durationS: 0 });
        },
      },
      { label: 'Backing the pin out', r: R_CLEAR, speed: SEAT_SPEED },
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

  /** Planar IK for the pin point at (r, z) with the pin horizontal. */
  private ik(r: number, z: number): Joints | null {
    return solveTool(r, 0, z - ARM_BASE_Z, TOOL_X, 0, 0);
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
      this.from = { x: this.world.cartX, r: p[0], z: p[2] + ARM_BASE_Z };
      this.goal = { x: mv.x ?? this.from.x, r: mv.r ?? this.from.r, z: mv.z ?? this.from.z };
      if (mv.joint) { this.goal.r = mv.r ?? this.from.r; }
      this.goalJ = this.ik(this.goal.r, this.goal.z);
      if (!this.goalJ) return this.fail(`unreachable (${mv.label})`);
      const dArm = Math.hypot(this.goal.r - this.from.r, this.goal.z - this.from.z);
      const dCart = Math.abs(this.goal.x - this.from.x);
      this.dur = Math.max(dArm / (mv.speed ?? PIN_SPEED), dCart / CART_SPEED, 1e-3);
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
      const j = this.ik(this.from.r + (this.goal.r - this.from.r) * u, this.from.z + (this.goal.z - this.from.z) * u);
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
