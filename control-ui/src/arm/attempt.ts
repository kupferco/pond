// One pick-and-place attempt: scripted controller (IK + phases), pod/slot world rules, trajectory recording.
// Everything steps in simulated time (no wall clock), so the same seed gives the same run in the
// browser, in the node test and when auto-running 50 attempts back to back.
//
// Sim assumptions (the model has no contact physics, see model.ts):
//  - Grasp is kinematic: when the jaws have closed to the pod width and the pod centre is within
//    GRASP_TOL of the grasp point, the pod is rigidly attached to the hand (jaws centre it across the gap).
//  - Release is kinematic: the pod falls straight down. It is captured by the socket (lead-in chamfer, not
//    drawn) if its centre is within CAPTURE of the slot centre and it is within 10 degrees of upright;
//    inside the socket it settles within the 2 mm play. Otherwise it lands on the floor where it fell.
//  - Perception noise: the controller sees pod and slot positions with a Gaussian error (default 1.2 mm per axis).
import type { CommandLayer } from '../commands.ts';
import type { SimDriver } from '../drivers/simDriver.ts';
import { MOTORS } from '../model.ts';
import {
  CONTROLLER_VERSION, GRASP_X, GRASP_Z, HOLD_DEG, OPEN_DEG, POD_REST_Z, SCENE_VERSION, SLOT_PLAY, SLOT_SEAT_Z,
} from './dims.ts';
import { graspPoint, solveDown, type Joints } from './kinematics.ts';
import { gauss, rng, type XY } from './placement.ts';

export { CONTROLLER_VERSION, SCENE_VERSION };

// Success tolerances: pod seated in the socket, and the final pose within these of the seat pose.
export const POS_TOL_MM = 3;
export const TILT_TOL_DEG = 5;
const GRASP_TOL = 0.008;       // m, pod centre to grasp point when the jaws close
const CAPTURE = 0.004;         // m, horizontal offset the socket lead-in still catches
const CAPTURE_TILT = 10;       // deg
const SETTLED_TILT = 4;        // deg, a seated pod cannot lean more than the socket play allows

const CTRL_STEPS = 10;         // control tick every 10 physics steps = 50 Hz at 2 ms
const REC_STEPS = 25;          // record at 20 Hz
const MAX_SAMPLES = 2400;
const CART_SPEED = 0.12;       // m/s
const JOINT_SPEED = 60;        // deg/s (joint-space approach move)
const GRIP_SPEED = 150;        // deg/s
const TRACK_TOL = 0.4;         // deg, "arrived" band for the arm joints
const DWELL_TICKS = 3;
const PHASE_TIMEOUT = 8;       // s
const RUN_TIMEOUT = 60;        // s
const Z_HOVER = 0.09, Z_CARRY = 0.08, Z_RELEASE = 0.056, Z_RETREAT = 0.09;

type V3 = [number, number, number];
interface PhaseSpec { name: string; joint?: boolean; goal?: (c: Ctx) => V3; grip: number }
interface Ctx { podEst: XY; slotEst: XY }

export const PHASES: readonly PhaseSpec[] = [
  { name: 'approach', joint: true, goal: (c) => [c.podEst[0], c.podEst[1], Z_HOVER], grip: OPEN_DEG },
  { name: 'descend', goal: (c) => [c.podEst[0], c.podEst[1], POD_REST_Z], grip: OPEN_DEG },
  { name: 'grasp', grip: HOLD_DEG },
  { name: 'lift', goal: (c) => [c.podEst[0], c.podEst[1], Z_CARRY], grip: HOLD_DEG },
  { name: 'move', goal: (c) => [c.slotEst[0], c.slotEst[1], Z_CARRY], grip: HOLD_DEG },
  { name: 'lower', goal: (c) => [c.slotEst[0], c.slotEst[1], Z_RELEASE], grip: HOLD_DEG },
  { name: 'release', grip: OPEN_DEG },
  { name: 'retreat', goal: (c) => [c.slotEst[0], c.slotEst[1], Z_RETREAT], grip: OPEN_DEG },
];
export const PHASE_NAMES = PHASES.map((p) => p.name);

export interface Sample {
  t: number;
  q: number[];     // measured joint angles A..F, degrees
  cmd: number[];   // targets sent to the motors A..F, degrees
  pod: number[];   // x y z (m), quaternion w x y z
  ph: number;      // index into PHASE_NAMES, -1 once finished
  held: boolean;
}

export interface AttemptResult {
  success: boolean;
  reason: string;          // 'seated' or why it failed
  posErrMm: number;        // 3-D distance of the pod from the seated pose
  tiltErrDeg: number;      // pod axis against the slot axis (vertical)
  durationS: number;       // simulated seconds from start to finish
}

export interface AttemptConfig {
  pod: XY; slot: XY;
  seed: number;
  noiseMm?: number;
  /** Cap on how many samples to keep (default 2400 = 120 s). */
  maxSamples?: number;
}

type Mat = number[];
const mulV = (R: Mat, v: number[]): V3 => [
  R[0] * v[0] + R[1] * v[1] + R[2] * v[2], R[3] * v[0] + R[4] * v[1] + R[5] * v[2], R[6] * v[0] + R[7] * v[1] + R[8] * v[2]];
const mulTV = (R: Mat, v: number[]): V3 => [
  R[0] * v[0] + R[3] * v[1] + R[6] * v[2], R[1] * v[0] + R[4] * v[1] + R[7] * v[2], R[2] * v[0] + R[5] * v[1] + R[8] * v[2]];
const mulM = (A: Mat, B: Mat): Mat => {
  const o: number[] = [];
  for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) o.push(A[3 * i] * B[j] + A[3 * i + 1] * B[3 + j] + A[3 * i + 2] * B[6 + j]);
  return o;
};
const IDENT: Mat = [1, 0, 0, 0, 1, 0, 0, 0, 1];
const quatOf = (R: Mat): number[] => {
  const t = R[0] + R[4] + R[8];
  let w: number, x: number, y: number, z: number;
  if (t > 0) { const s = Math.sqrt(t + 1) * 2; w = s / 4; x = (R[7] - R[5]) / s; y = (R[2] - R[6]) / s; z = (R[3] - R[1]) / s; }
  else if (R[0] > R[4] && R[0] > R[8]) { const s = Math.sqrt(1 + R[0] - R[4] - R[8]) * 2; w = (R[7] - R[5]) / s; x = s / 4; y = (R[1] + R[3]) / s; z = (R[2] + R[6]) / s; }
  else if (R[4] > R[8]) { const s = Math.sqrt(1 + R[4] - R[0] - R[8]) * 2; w = (R[2] - R[6]) / s; x = (R[1] + R[3]) / s; y = s / 4; z = (R[5] + R[7]) / s; }
  else { const s = Math.sqrt(1 + R[8] - R[0] - R[4]) * 2; w = (R[3] - R[1]) / s; x = (R[2] + R[6]) / s; y = (R[5] + R[7]) / s; z = s / 4; }
  return [w, x, y, z];
};
/** Rotation that tilts the vertical axis by `deg` towards the horizontal direction (ux, uy). */
const tiltRot = (deg: number, ux: number, uy: number): Mat => {
  const a = deg * Math.PI / 180, c = Math.cos(a), s = Math.sin(a);
  const kx = -uy, ky = ux; // axis = z x u
  const C = 1 - c;
  return [c + kx * kx * C, kx * ky * C, ky * s, kx * ky * C, c + ky * ky * C, -kx * s, -ky * s, kx * s, c];
};
const tiltDeg = (R: Mat) => Math.acos(Math.min(1, Math.max(-1, R[8]))) * 180 / Math.PI; // pod axis z . world z

const round = (v: number, d: number) => { const k = 10 ** d; return Math.round(v * k) / k; };

export class Attempt {
  readonly cfg: AttemptConfig;
  readonly samples: Sample[] = [];
  result: AttemptResult | null = null;
  done = false;

  private sim: SimDriver;
  private cmd: CommandLayer;
  private ctx: Ctx;
  private ph = 0;
  private phTime = 0;
  private dwell = 0;
  private steps = 0;
  private startOfPhase = true;
  private cmdG: V3 = [0, 0, 0];
  private cmdJ: number[] = [0, 0, 0, 0, 0];     // A..E, before the gravity integrator
  private goalJ: Joints | null = null;
  private goalG: V3 | null = null;
  private integ = [0, 0, 0, 0, 0];
  private grip = 0;
  private lastSent: number[] = MOTORS.map((m) => m.home);

  // pod world state
  private podPos: V3;
  private podRot: Mat = IDENT;
  private held = false;
  private rel: { pos: V3; rot: Mat } | null = null;
  private falling: { vz: number; restZ: number; settle: XY | null; settleRot: Mat | null } | null = null;
  private captured = false;
  private releaseTilt = 0;
  private released = false;
  private failReason = '';

  constructor(sim: SimDriver, cmd: CommandLayer, cfg: AttemptConfig) {
    this.sim = sim; this.cmd = cmd; this.cfg = cfg;
    sim.reset();
    const rand = rng(cfg.seed ^ 0x9e3779b9);
    const n = (cfg.noiseMm ?? 1.2) / 1000;
    this.ctx = {
      podEst: [cfg.pod[0] + gauss(rand) * n, cfg.pod[1] + gauss(rand) * n],
      slotEst: [cfg.slot[0] + gauss(rand) * n, cfg.slot[1] + gauss(rand) * n],
    };
    this.podPos = [cfg.pod[0], cfg.pod[1], POD_REST_Z];
    this.writeScene();
    sim.mujoco.mj_forward(sim.model, sim.data);
    this.grip = 0;
  }

  get phaseName(): string { return this.done ? 'done' : PHASES[this.ph].name; }
  get time(): number { return this.steps * this.sim.model.opt.timestep; }

  /** Advance by up to maxSimSeconds of simulated time. Returns true when the attempt has finished. */
  advance(maxSimSeconds: number): boolean {
    const n = Math.max(1, Math.round(maxSimSeconds / this.sim.model.opt.timestep));
    for (let i = 0; i < n && !this.done; i++) {
      if (this.steps % CTRL_STEPS === 0) this.control();
      if (this.done) break;
      this.sim.step();
      this.steps++;
      this.updatePod();
      if (this.steps % REC_STEPS === 0) this.record();
      if (this.time > RUN_TIMEOUT) this.fail('timeout (run)');
    }
    return this.done;
  }

  // --- pod world -----------------------------------------------------------
  private writeScene() {
    this.sim.setMocap('pod', this.podPos, quatOf(this.podRot));
    this.sim.setMocap('slot', [this.cfg.slot[0], this.cfg.slot[1], 0]);
  }

  private updatePod() {
    if (this.held && this.rel) {
      const h = this.sim.bodyPose('hand');
      const o = mulV(h.rot, this.rel.pos);
      this.podPos = [h.pos[0] + o[0], h.pos[1] + o[1], h.pos[2] + o[2]];
      this.podRot = mulM(h.rot, this.rel.rot);
    } else if (this.falling) {
      const f = this.falling, h = this.sim.model.opt.timestep;
      f.vz -= 9.81 * h;
      this.podPos[2] += f.vz * h;
      if (this.podPos[2] <= f.restZ) {
        this.podPos[2] = f.restZ;
        if (f.settle) { this.podPos[0] = f.settle[0]; this.podPos[1] = f.settle[1]; }
        this.podRot = f.settleRot ?? IDENT;
        this.falling = null;
      }
    } else return;
    this.writeScene();
  }

  private tryGrasp(): boolean {
    const h = this.sim.bodyPose('hand');
    const L = mulTV(h.rot, [this.podPos[0] - h.pos[0], this.podPos[1] - h.pos[1], this.podPos[2] - h.pos[2]]);
    const off = Math.hypot(L[0] - GRASP_X, L[1], L[2] - GRASP_Z);
    if (off > GRASP_TOL) return false;
    this.rel = { pos: [L[0], L[1], GRASP_Z], rot: mulTM(h.rot, this.podRot) };
    this.held = true;
    return true;
  }

  private release() {
    this.held = false;
    this.released = true;
    const tilt = tiltDeg(this.podRot);
    this.releaseTilt = tilt;
    const dx = this.podPos[0] - this.cfg.slot[0], dy = this.podPos[1] - this.cfg.slot[1];
    const d = Math.hypot(dx, dy);
    this.captured = d <= CAPTURE && tilt <= CAPTURE_TILT;
    if (this.captured) {
      const k = d > SLOT_PLAY ? SLOT_PLAY / d : 1;
      this.falling = {
        vz: 0, restZ: SLOT_SEAT_Z,
        settle: [this.cfg.slot[0] + dx * k, this.cfg.slot[1] + dy * k],
        settleRot: this.leanRot(Math.min(tilt, SETTLED_TILT)),
      };
    } else {
      this.falling = { vz: 0, restZ: POD_REST_Z, settle: null, settleRot: null };
    }
  }

  /** Orientation after settling: keep the lean direction of the carried pod, limited to what the socket allows. */
  private leanRot(deg: number): Mat {
    const ax = this.podRot[2], ay = this.podRot[5]; // pod z axis horizontal part = lean direction
    const m = Math.hypot(ax, ay);
    return m < 1e-9 ? IDENT : tiltRot(deg, ax / m, ay / m);
  }

  // --- controller ----------------------------------------------------------
  private measured(): number[] {
    const j = this.cmd.readJoints() ?? {};
    return MOTORS.map((m) => j[m.id] ?? 0);
  }

  private send(q: number[]) {
    const sent: number[] = [];
    MOTORS.forEach((m, i) => { sent.push(this.cmd.setJointTarget(m.id, q[i])); });
    this.lastSent = sent;
  }

  private fail(reason: string) {
    if (this.done) return;
    this.failReason = reason;
    this.finish();
  }

  private control() {
    const dt = CTRL_STEPS * this.sim.model.opt.timestep;
    const q = this.measured();
    const spec = PHASES[this.ph];

    if (this.startOfPhase) {
      this.startOfPhase = false;
      this.phTime = 0; this.dwell = 0;
      this.goalG = spec.goal ? spec.goal(this.ctx) : null;
      this.goalJ = this.goalG ? solveDown(...this.goalG) : null;
      if (this.goalG && !this.goalJ) return this.fail(`unreachable (${spec.name})`);
      if (this.ph === 0) {
        this.cmdJ = q.slice(0, 5);
        this.grip = q[5];
        this.cmdG = graspPoint({ A: q[0], B: q[1], C: q[2], D: q[3] });
      }
    }
    this.phTime += dt;

    // Move the commanded pose towards the phase goal.
    let arrived = true;
    if (this.goalJ && this.goalG) {
      if (spec.joint) {
        const gj = [this.goalJ.A, this.goalJ.B, this.goalJ.C, this.goalJ.D, this.goalJ.E];
        for (let i = 0; i < 5; i++) {
          const d = gj[i] - this.cmdJ[i], s = JOINT_SPEED * dt;
          this.cmdJ[i] += Math.abs(d) <= s ? d : Math.sign(d) * s;
          if (Math.abs(gj[i] - this.cmdJ[i]) > 1e-6) arrived = false;
        }
        this.cmdG = graspPoint({ A: this.cmdJ[0], B: this.cmdJ[1], C: this.cmdJ[2], D: this.cmdJ[3] });
      } else {
        // Straight line in (radius, pan angle, height): keeps clear of the dead zone near the base
        // that a straight line in x/y would cut through when pod and slot are far apart in angle.
        const [r0, a0] = [Math.hypot(this.cmdG[0], this.cmdG[1]), Math.atan2(this.cmdG[1], this.cmdG[0])];
        const [r1, a1] = [Math.hypot(this.goalG[0], this.goalG[1]), Math.atan2(this.goalG[1], this.goalG[0])];
        const dist = Math.hypot(r1 - r0, ((r0 + r1) / 2) * (a1 - a0), this.goalG[2] - this.cmdG[2]), s = CART_SPEED * dt;
        if (dist <= s) this.cmdG = [...this.goalG];
        else {
          const k = s / dist, r = r0 + (r1 - r0) * k, a = a0 + (a1 - a0) * k;
          this.cmdG = [r * Math.cos(a), r * Math.sin(a), this.cmdG[2] + (this.goalG[2] - this.cmdG[2]) * k];
          arrived = false;
        }
        const j = solveDown(...this.cmdG);
        if (!j) return this.fail(`unreachable (${spec.name})`);
        this.cmdJ = [j.A, j.B, j.C, j.D, j.E];
      }
    }
    const gd = spec.grip - this.grip, gs = GRIP_SPEED * dt;
    this.grip += Math.abs(gd) <= gs ? gd : Math.sign(gd) * gs;
    if (Math.abs(spec.grip - this.grip) > 1e-6) arrived = false;

    // Gravity / tracking integrator on the arm joints (a servo with only P gain sags under load).
    for (let i = 0; i < 5; i++) {
      this.integ[i] += 4 * (this.cmdJ[i] - q[i]) * dt;
      this.integ[i] = Math.max(-8, Math.min(8, this.integ[i]));
    }
    this.send([...this.cmdJ.map((v, i) => v + this.integ[i]), this.grip]);

    // Phase complete when the commanded motion is done and the joints have really got there.
    let settled = arrived;
    if (settled) for (let i = 0; i < 4; i++) if (Math.abs(q[i] - this.cmdJ[i]) > TRACK_TOL) settled = false;
    if (settled && Math.abs(q[5] - spec.grip) > 2) settled = false;
    this.dwell = settled ? this.dwell + 1 : 0;
    if (this.phTime > PHASE_TIMEOUT) return this.fail(`timeout (${spec.name})`);
    if (this.dwell < DWELL_TICKS) return;

    if (spec.name === 'grasp' && !this.tryGrasp()) return this.fail('missed pod');
    if (spec.name === 'release') this.release();
    this.ph++;
    this.startOfPhase = true;
    if (this.ph >= PHASES.length) this.finish();
  }

  private record() {
    if (this.samples.length >= (this.cfg.maxSamples ?? MAX_SAMPLES)) return;
    const q = this.measured();
    this.samples.push({
      t: round(this.time, 3),
      q: q.map((v) => round(v, 2)),
      cmd: this.lastSent.map((v) => round(v, 2)),
      pod: [...this.podPos.map((v) => round(v, 5)), ...quatOf(this.podRot).map((v) => round(v, 4))],
      ph: this.done ? -1 : this.ph,
      held: this.held,
    });
  }

  private finish() {
    this.done = true;
    // Let a pod that is still falling land (it is at most a few cm up) before measuring.
    while (this.falling) this.updatePodForce();
    const seat: V3 = [this.cfg.slot[0], this.cfg.slot[1], SLOT_SEAT_Z];
    const posErr = Math.hypot(this.podPos[0] - seat[0], this.podPos[1] - seat[1], this.podPos[2] - seat[2]) * 1000;
    const tilt = this.released && !this.captured ? Math.max(this.releaseTilt, tiltDeg(this.podRot)) : tiltDeg(this.podRot);
    let reason = this.failReason;
    let success = false;
    if (!reason) {
      if (!this.captured) reason = 'missed slot';
      else if (posErr > POS_TOL_MM || tilt > TILT_TOL_DEG) reason = 'out of tolerance';
      else { success = true; reason = 'seated'; }
    }
    this.result = { success, reason, posErrMm: round(posErr, 2), tiltErrDeg: round(tilt, 2), durationS: round(this.time, 2) };
    this.record();
  }

  private updatePodForce() {
    const f = this.falling!;
    this.podPos[2] = f.restZ;
    if (f.settle) { this.podPos[0] = f.settle[0]; this.podPos[1] = f.settle[1]; }
    this.podRot = f.settleRot ?? IDENT;
    this.falling = null;
    this.writeScene();
  }
}

/** Rᵀ·B for row-major 3x3 matrices. */
function mulTM(A: Mat, B: Mat): Mat {
  const o: number[] = [];
  for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) o.push(A[i] * B[j] + A[3 + i] * B[3 + j] + A[6 + i] * B[6 + j]);
  return o;
}
