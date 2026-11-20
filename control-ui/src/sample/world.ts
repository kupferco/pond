// Sampling world and runner. Kinematic, like the Transplant scene: the arm is put exactly on each interpolated pose, the cart on its stop, and every tick is checked
// (arm against the cart, the unit and the station; the nozzle against the sockets; the pump against what is plugged in; the water that goes in and out).
// Water ledger (ASSUMED, bench numbers to come): the tube holds the sample, the cup always sits at its heel over the standpipe, new water pushes the same amount over the standpipe, perfectly mixed.
import type { CommandLayer } from '../commands.ts';
import type { SimDriver } from '../drivers/simDriver.ts';
import { armMjcf } from '../model.ts';
import { worstContact } from '../transplant/apply.ts';
import {
  AXIS_TOL_DEG, CART_SPEED, CUP_H, CUP_R, CUP_X, CUP_Z0, HEEL_ML, HOLD_F, LID_T, LID_X0, LID_X1, LID_Z, NOZ_COLLAR_HL, NOZ_COLLAR_R, NOZ_SPIGOT_L, NOZ_SPIGOT_R, NOZ_TIP,
  OPEN_F, PARK_REL, PLUG_DEPTH, PLUG_TOL, POSES, STATION_REL, STN_HY, STN_X0, STN_X1, STOPS, TANK_H, TOOL_TX, TOOL_TZ, TUBE_ML, TURNS_PER_S, UNIT_HY, UNIT_REL,
  f, levelZ, type Stop, type V3,
} from './layout.ts';
import type { SampleCommand } from './language.ts';
import { formatCommand } from './language.ts';

const rgba = (r: number, g: number, b: number, a = 1) => `rgba="${r} ${g} ${b} ${a}"`;
const OBST = 'contype="1" conaffinity="2"';     // the unit and the station: the arm (contype 2) collides with them
const CART_COL = 'contype="4" conaffinity="2"'; // the cart's parts
const VIS = 'contype="0" conaffinity="0"';
const TUBE_N = 18;                               // capsule segments of the tube
export const PUMP_PORT: V3 = [-0.07, 0, 0.03];   // where the tube leaves the pump on the cart (rel)

/** MJCF: the arm on a cart (mocap body 'cart'), the track, two units (the sampled one and the one with the station), nozzle, tube, water. */
export function sampleMjcf(): string {
  const box = (n: string, c: V3, h: V3, col: string, attrs = OBST) => `<geom ${n ? `name="${n}" ` : ''}type="box" pos="${c.map(f).join(' ')}" size="${h.map(f).join(' ')}" ${attrs} ${col}/>`;
  const unit = (y0: number, withStation: boolean) => {
    const out: string[] = [];
    const xc = (LID_X0 + LID_X1) / 2, hx = (LID_X1 - LID_X0) / 2;
    out.push(box('', [xc, y0, LID_Z - LID_T / 2], [hx, UNIT_HY, LID_T / 2], rgba(0.6, 0.62, 0.66)));
    out.push(box('', [xc, y0, LID_Z - TANK_H / 2], [hx, UNIT_HY, TANK_H / 2], rgba(0.72, 0.8, 0.86, 0.2), VIS));
    out.push(box('', [xc, y0, LID_Z - TANK_H * 0.35], [hx - 0.004, UNIT_HY - 0.004, TANK_H * 0.35 - 0.004], rgba(0.25, 0.55, 0.9, 0.35), VIS));
    if (!withStation) {
      // the unit's lid socket: flush round insert, dip tube below
      out.push(`<geom type="cylinder" fromto="${UNIT_REL[0]} ${f(y0 + UNIT_REL[1])} ${LID_Z} ${UNIT_REL[0]} ${f(y0 + UNIT_REL[1])} ${f(LID_Z + 0.0008)}" size="0.0065" ${VIS} ${rgba(0.1, 0.1, 0.12)}/>`);
      out.push(`<geom type="cylinder" fromto="${UNIT_REL[0]} ${f(y0 + UNIT_REL[1])} ${LID_Z} ${UNIT_REL[0]} ${f(y0 + UNIT_REL[1])} ${f(LID_Z - TANK_H + 0.008)}" size="0.003" ${VIS} ${rgba(0.3, 0.3, 0.35)}/>`);
    } else {
      // the station: a box on the lid with the nozzle socket in the roof, the sample cup inside (the front of the box is see-through here)
      out.push(box('station_box', [(STN_X0 + STN_X1) / 2, y0, (LID_Z + STATION_REL[2]) / 2 - 0.0015], [(STN_X1 - STN_X0) / 2, STN_HY, (STATION_REL[2] - LID_Z) / 2 - 0.0015], rgba(0.8, 0.78, 0.7, 0.28)));
      out.push(box('', [(STN_X0 + STN_X1) / 2, y0, STATION_REL[2] - 0.0015], [(STN_X1 - STN_X0) / 2, STN_HY, 0.0015], rgba(0.55, 0.5, 0.42)));
      out.push(`<geom type="cylinder" fromto="${STATION_REL[0]} ${f(y0 + STATION_REL[1])} ${STATION_REL[2] - 0.003} ${STATION_REL[0]} ${f(y0 + STATION_REL[1])} ${f(STATION_REL[2] + 0.0008)}" size="0.0065" ${VIS} ${rgba(0.1, 0.1, 0.12)}/>`);
      out.push(`<geom type="cylinder" fromto="${CUP_X} ${f(y0)} ${CUP_Z0} ${CUP_X} ${f(y0)} ${f(CUP_Z0 + CUP_H)}" size="${CUP_R}" ${VIS} ${rgba(0.85, 0.9, 0.95, 0.35)}/>`);
      out.push(`<geom type="cylinder" fromto="${CUP_X} ${f(y0)} ${f(CUP_Z0 - 0.002)} ${CUP_X} ${f(y0)} ${CUP_Z0}" size="${CUP_R}" ${VIS} ${rgba(0.4, 0.42, 0.46)}/>`);
      out.push(`<geom type="cylinder" fromto="${f(CUP_X + 0.075)} ${f(y0 + 0.06)} ${LID_Z} ${f(CUP_X + 0.075)} ${f(y0 + 0.06)} ${f(LID_Z + 0.05)}" size="0.003" ${VIS} ${rgba(0.9, 0.3, 0.3)}/>`); // the drain over the standpipe (marker)
    }
    return out;
  };
  const tube = Array.from({ length: TUBE_N }, (_, i) => `<body name="tube_${i}" mocap="true" pos="0 0 0.1"><geom type="capsule" size="0.0035 0.01" ${VIS} ${rgba(0.55, 0.55, 0.6, 0.9)}/></body>`);
  const world = [
    `<geom name="floor" type="plane" size="1.6 1.6 0.01" pos="0 0.5 -0.62" ${VIS} ${rgba(0.86, 0.88, 0.9)}/>`,
    // the track pipe (a real pipe, along y, under the cart)
    `<geom type="cylinder" fromto="-0.14 -0.7 -0.06 -0.14 1.7 -0.06" size="0.0168" ${VIS} ${rgba(0.62, 0.66, 0.7)}/>`,
    ...unit(STOPS.unit, false), ...unit(STOPS.station, true),
    // water level discs: the sample cup (moves with the water), the sampled unit's tank water is the blue box
    `<body name="cup_water" mocap="true" pos="${CUP_X} ${STOPS.station} ${f(levelZ(HEEL_ML))}"><geom type="cylinder" size="${CUP_R - 0.002} 0.0015" ${VIS} ${rgba(0.2, 0.55, 0.95, 0.9)}/></body>`,
    // the nozzle: collar and spigot, body z axis along the spigot, origin at the collar centre
    `<body name="nozzle" mocap="true" pos="0 0 0.3">
      <geom type="cylinder" size="${NOZ_COLLAR_R} ${NOZ_COLLAR_HL}" ${VIS} ${rgba(0.95, 0.5, 0.1)}/>
      <geom type="cylinder" pos="0 0 ${f(NOZ_COLLAR_HL + NOZ_SPIGOT_L / 2)}" size="${NOZ_SPIGOT_R} ${NOZ_SPIGOT_L / 2}" ${VIS} ${rgba(0.85, 0.85, 0.88)}/>
    </body>`,
    ...tube,
    // pump rotor (a mocap disc that turns with the pump turns)
    `<body name="rotor" mocap="true" pos="${PUMP_PORT[0]} ${PUMP_PORT[1]} ${PUMP_PORT[2] + 0.012}"><geom type="box" size="0.017 0.004 0.003" ${VIS} ${rgba(0.95, 0.95, 0.2)}/></body>`,
  ].join('\n    ');
  const cart = `<body name="cart" mocap="true" pos="0 ${STOPS.unit} 0">
      ${box('deck', [0, 0.07, -0.015], [0.08, 0.15, 0.015], rgba(0.45, 0.47, 0.52), CART_COL)}
      ${box('pump', [PUMP_PORT[0], PUMP_PORT[1], 0.012], [0.025, 0.035, 0.012], rgba(0.25, 0.3, 0.55), CART_COL)}
      <geom type="cylinder" fromto="-0.04 0.12 0.01 -0.04 0.12 0.07" size="0.026" ${VIS} ${rgba(0.4, 0.45, 0.6, 0.5)}/>
      ${box('park_block', [PARK_REL[0], PARK_REL[1], PARK_REL[2] / 2], [0.02, 0.02, PARK_REL[2] / 2], rgba(0.7, 0.7, 0.75), CART_COL)}
      <geom type="cylinder" fromto="${PARK_REL[0]} ${PARK_REL[1]} ${PARK_REL[2] - 0.003} ${PARK_REL[0]} ${PARK_REL[1]} ${PARK_REL[2] + 0.0008}" size="0.0065" ${VIS} ${rgba(0.1, 0.1, 0.12)}/>
      <geom type="box" pos="-0.14 0 -0.045" size="0.03 0.1 0.012" ${VIS} ${rgba(0.35, 0.37, 0.4)}/>
    `;
  return armMjcf(world, { noGround: true, armCollides: true, mount: { open: cart, close: '</body>' }, option: '<option timestep="0.004" gravity="0 0 0"/>' });
}

// ---------------------------------------------------------------------------------------------------------------------
type M = number[];
const quatOf = (R: M): number[] => {
  const t = R[0] + R[4] + R[8];
  if (t > 0) { const s = Math.sqrt(t + 1) * 2; return [s / 4, (R[7] - R[5]) / s, (R[2] - R[6]) / s, (R[3] - R[1]) / s]; }
  if (R[0] > R[4] && R[0] > R[8]) { const s = Math.sqrt(1 + R[0] - R[4] - R[8]) * 2; return [(R[7] - R[5]) / s, s / 4, (R[1] + R[3]) / s, (R[2] + R[6]) / s]; }
  if (R[4] > R[8]) { const s = Math.sqrt(1 + R[4] - R[0] - R[8]) * 2; return [(R[2] - R[6]) / s, (R[1] + R[3]) / s, s / 4, (R[5] + R[7]) / s]; }
  const s = Math.sqrt(1 + R[8] - R[0] - R[4]) * 2; return [(R[3] - R[1]) / s, (R[2] + R[6]) / s, (R[5] + R[7]) / s, s / 4];
};
/** Quaternion that turns the body z axis onto the direction d. */
const quatZTo = (d: V3): number[] => {
  const n = Math.hypot(...d), z = d[2] / n;
  if (z < -0.999999) return [0, 1, 0, 0];
  const ax = [-d[1] / n, d[0] / n, 0], s = Math.sqrt((1 + z) * 2);   // cross(z, d) / ...
  return [s / 2, ax[0] / s, ax[1] / s, 0];
};

export type Where = 'parked' | 'held';
export interface Plug { socket: 'park' | 'unit' | 'station' | null; offMm: number; depthMm: number; tiltDeg: number }

export class SampleWorld {
  readonly sim: SimDriver;
  cartY: number = STOPS.unit;
  where: Where = 'parked';
  gripOpen = false;
  tubeMl = 0;
  cupMl = HEEL_ML;
  oldFraction = 1;     // share of the old sample in the cup
  drainedMl = 0;       // went over the standpipe
  drawnMl = 0;         // taken from the unit
  rotorTurns = 0;
  violation = '';
  contactCount = 0;
  private handId = -1;

  constructor(sim: SimDriver) { this.sim = sim; this.reset(); }

  reset() {
    this.sim.reset();
    this.cartY = STOPS.unit; this.where = 'parked'; this.gripOpen = false;
    this.tubeMl = 0; this.cupMl = HEEL_ML; this.oldFraction = 1; this.drainedMl = 0; this.drawnMl = 0; this.rotorTurns = 0; this.violation = ''; this.contactCount = 0;
    this.sim.setJointsKinematic({ ...POSES.rest, F: HOLD_F });
    this.write();
  }

  /** Stop the cart is at (or null while it is between stops). */
  get stop(): Stop | null { for (const s of Object.keys(STOPS) as Stop[]) if (Math.abs(this.cartY - STOPS[s]) < 1e-6) return s; return null; }
  /** New sample in the cup, ml. */
  get newInCup(): number { return this.cupMl * (1 - this.oldFraction); }

  hand(): { pos: V3; rot: M } {
    if (this.handId < 0) { const b = this.sim.model.body('hand'); this.handId = b.id; b.delete(); }
    const x = this.sim.data.xpos, r = this.sim.data.xmat, id = this.handId;
    return { pos: [x[3 * id], x[3 * id + 1], x[3 * id + 2]], rot: Array.from({ length: 9 }, (_, k) => r[9 * id + k]) };
  }
  /** The held nozzle: tip, axis (tip direction) and collar centre, world, from the hand pose. */
  heldNozzle(): { tip: V3; axis: V3; centre: V3 } {
    const { pos, rot } = this.hand();
    const at = (tx: number): V3 => [pos[0] + rot[0] * tx + rot[2] * TOOL_TZ, pos[1] + rot[3] * tx + rot[5] * TOOL_TZ, pos[2] + rot[6] * tx + rot[8] * TOOL_TZ];
    return { tip: at(TOOL_TX), centre: at(TOOL_TX - NOZ_TIP), axis: [rot[0], rot[3], rot[6]] };
  }
  /** Where a nozzle parked in the cart's parking socket stands: tip PLUG_DEPTH in, straight down. */
  parkedNozzle(): { tip: V3; axis: V3; centre: V3 } {
    const tip: V3 = [PARK_REL[0], PARK_REL[1] + this.cartY, PARK_REL[2] - PLUG_DEPTH];
    return { tip, axis: [0, 0, -1], centre: [tip[0], tip[1], tip[2] + NOZ_TIP] };
  }
  nozzle() { return this.where === 'held' ? this.heldNozzle() : this.parkedNozzle(); }

  /** Which socket the nozzle is plugged into (spigot straight in, within PLUG_TOL), or null. */
  plug(): Plug {
    const n = this.nozzle();
    const targets: [Plug['socket'] & string, V3][] = [['park', PARK_REL], ['unit', UNIT_REL], ['station', STATION_REL]];
    let best: Plug = { socket: null, offMm: Infinity, depthMm: 0, tiltDeg: 0 };
    const tilt = Math.acos(Math.max(-1, Math.min(1, -n.axis[2]))) * 180 / Math.PI;
    for (const [name, rel] of targets) {
      const m: V3 = [rel[0], rel[1] + (name === 'park' ? this.cartY : STOPS[name]), rel[2]];
      const off = Math.hypot(n.tip[0] - m[0], n.tip[1] - m[1]), depth = m[2] - n.tip[2];
      if (off < best.offMm) best = { socket: name, offMm: off * 1000, depthMm: depth * 1000, tiltDeg: tilt };
    }
    const ok = best.offMm / 1000 <= PLUG_TOL && best.depthMm >= (PLUG_DEPTH - 0.004) * 1000 && best.depthMm <= (PLUG_DEPTH + 0.002) * 1000 && best.tiltDeg <= AXIS_TOL_DEG;
    return ok ? best : { ...best, socket: null };
  }

  private bad(msg: string) { if (!this.violation) { this.violation = msg; console.error(`[sample] ${msg}`); } return this.violation; }

  setCartY(y: number) { this.cartY = y; this.write(); }

  /** Put the arm on these joints (A to E; F is the gripper). */
  setArm(j: Record<string, number>) { this.sim.setJointsKinematic({ ...j, F: this.gripOpen ? OPEN_F : HOLD_F }); this.write(); }

  /** Pump this many ml (positive draws, negative pushes) at the nozzle's present place: moves water, or fails. */
  pumpMl(ml: number) {
    if (ml === 0 || this.violation) return;
    const p = this.plug();
    if (p.socket === null) { this.bad(`the pump ran with the nozzle not plugged into a socket (nearest socket: ${p.offMm.toFixed(1)} mm sideways, ${p.depthMm.toFixed(1)} mm in, ${p.tiltDeg.toFixed(0)}° tilt): it would draw air or spray`); return; }
    if (this.where !== 'held') { this.bad('the pump ran with the nozzle parked: it would draw air'); return; }
    if (ml > 0) {
      if (p.socket !== 'unit') { this.bad(`the pump drew from the ${p.socket === 'park' ? 'parking' : p.socket} socket: only the unit's lid socket has water to draw`); return; }
      if (this.tubeMl + ml > TUBE_ML + 1e-6) { this.bad(`the tube is full (${TUBE_ML} ml): the pump drew more than it holds`); return; }
      this.tubeMl += ml; this.drawnMl += ml;
    } else {
      if (p.socket !== 'station') { this.bad(`the pump pushed into the ${p.socket === 'park' ? 'parking' : p.socket} socket: only the station socket leads to the cup`); return; }
      const out = -ml;
      if (out > this.tubeMl + 1e-6) { this.bad('the pump ran dry: it pushed air into the cup'); return; }
      this.tubeMl = Math.max(0, this.tubeMl - out);
      // perfect mixing: new water in, the same amount over the standpipe, the cup stays at its heel
      const total = this.cupMl + out;
      this.oldFraction = this.oldFraction * this.cupMl / total;
      const over = Math.max(0, total - HEEL_ML);
      this.drainedMl += over; this.cupMl = total - over;
    }
  }

  /** Tick bookkeeping: contacts of the arm and the cart, then the mocap bodies. */
  audit() {
    if (this.violation) return;
    const { depth, names } = worstContact(this.sim.model, this.sim.data);
    if (depth < -0.0005) { this.contactCount++; this.bad(`the arm touched the cart or the unit (${names}, ${(-depth * 1000).toFixed(1)} mm)`); }
  }

  /** Write the cart, nozzle, tube, rotor and water level into the sim bodies. */
  write() {
    const sim = this.sim, mj = sim.mujoco;
    sim.setMocap('cart', [0, this.cartY, 0]);
    mj.mj_forward(sim.model, sim.data);   // the hand pose follows the cart
    const n = this.nozzle();
    const R = this.where === 'held' ? this.hand().rot : null;
    const q = R ? quatOf([R[1], R[2], R[0], R[4], R[5], R[3], R[7], R[8], R[6]]) : quatZTo(n.axis);
    sim.setMocap('nozzle', n.centre, q);
    // tube: from the pump port to the top of the collar, with a sag
    const a: V3 = [PUMP_PORT[0], PUMP_PORT[1] + this.cartY, PUMP_PORT[2] + 0.02];
    const b: V3 = [n.centre[0] - n.axis[0] * NOZ_COLLAR_HL, n.centre[1] - n.axis[1] * NOZ_COLLAR_HL, n.centre[2] - n.axis[2] * NOZ_COLLAR_HL];
    const len = Math.hypot(b[0] - a[0], b[1] - a[1], b[2] - a[2]);
    const pt = (s: number): V3 => [a[0] + (b[0] - a[0]) * s, a[1] + (b[1] - a[1]) * s, a[2] + (b[2] - a[2]) * s + 0.045 * Math.sin(Math.PI * s) * Math.min(1, 0.12 + len)];
    for (let i = 0; i < TUBE_N; i++) {
      const p0 = pt(i / TUBE_N), p1 = pt((i + 1) / TUBE_N), d: V3 = [p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]];
      sim.setMocap(`tube_${i}`, [(p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2, (p0[2] + p1[2]) / 2], quatZTo(d));
    }
    const ang = this.rotorTurns * 2 * Math.PI;
    sim.setMocap('rotor', [PUMP_PORT[0], PUMP_PORT[1] + this.cartY, PUMP_PORT[2] + 0.012], [Math.cos(ang / 2), 0, 0, Math.sin(ang / 2)]);
    sim.setMocap('cup_water', [CUP_X, STOPS.station, levelZ(this.cupMl)]);
    mj.mj_forward(sim.model, sim.data);
  }
}

// ---------------------------------------------------------------------------------------------------------------------
const JOINT_SPEED = 45;        // deg/s
const MIN_MOVE_S = 0.4;
const GRIP_S = 0.6;
const ARM_IDS = ['A', 'B', 'C', 'D', 'E'] as const;
const TICK = 0.05;             // s of sim time per check

export interface StepLog { command: string; t0: number; t1: number }
export interface SampleResult { ok: boolean; reason: string; time: number; drawnMl: number; drainedMl: number; newInCupMl: number; cupMl: number; oldPct: number; steps: StepLog[] }

/** Runs a list of commands against the world, in sim time. `cmd` carries the same commands to the driver (the sim here; the Real driver later). */
export class SampleRun {
  done = false;
  failReason = '';
  time = 0;
  readonly log: StepLog[] = [];
  private i = -1;
  private cur: { c: SampleCommand; t: number; dur: number; from?: Record<string, number>; to?: Record<string, number>; fromY?: number; toY?: number; turns0?: number; done0?: number } | null = null;
  readonly world: SampleWorld;
  private cmd: CommandLayer;
  readonly commands: SampleCommand[];
  readonly mlPerTurn: number;

  constructor(world: SampleWorld, cmd: CommandLayer, commands: SampleCommand[], mlPerTurn: number) {
    this.world = world; this.cmd = cmd; this.commands = commands; this.mlPerTurn = mlPerTurn;
    if (commands.length === 0) this.done = true;
  }
  get index() { return Math.max(0, Math.min(this.i, this.commands.length - 1)); }
  get label() { return this.done ? (this.failReason ? 'Failed' : 'Done') : formatCommand(this.commands[this.index]); }
  get progress() { return this.done ? 1 : (this.i + (this.cur ? Math.min(1, this.cur.t / Math.max(1e-6, this.cur.dur)) : 0)) / this.commands.length; }

  private fail(msg: string) { this.failReason = msg; this.done = true; }

  private currentArm(): Record<string, number> {
    const j = this.world.sim.readJoints(); const out: Record<string, number> = {};
    for (const id of ARM_IDS) out[id] = j[id];
    return out;
  }

  private begin(c: SampleCommand) {
    const w = this.world;
    const cur: NonNullable<SampleRun['cur']> = { c, t: 0, dur: 0 };
    switch (c.op) {
      case 'pose': {
        cur.from = this.currentArm(); cur.to = { ...this.cmdPose(c.name) };
        cur.dur = Math.max(MIN_MOVE_S, Math.max(...ARM_IDS.map((id) => Math.abs(cur.to![id] - cur.from![id]))) / JOINT_SPEED);
        break;
      }
      case 'gripper': cur.dur = GRIP_S; break;
      case 'cart': {
        if (w.where === 'held') return this.fail('the cart was told to drive with the nozzle still in the hand: it must be parked first');
        if (this.armAway() === false) return this.fail('the cart was told to drive with the arm out of its rest pose');
        cur.fromY = w.cartY; cur.toY = STOPS[c.to]; cur.dur = Math.max(0.3, Math.abs(cur.toY - cur.fromY) / CART_SPEED);
        break;
      }
      case 'pump': cur.dur = c.turns / TURNS_PER_S; cur.done0 = 0; break;
      case 'wait': cur.dur = c.s; break;
    }
    this.cur = cur;
    this.log.push({ command: formatCommand(c), t0: this.time, t1: this.time });
  }
  private cmdPose(name: keyof typeof POSES) { this.cmd.pose(name); return POSES[name]; }
  private armAway(): boolean { const j = this.currentArm(), r = POSES.rest; return ARM_IDS.every((id) => Math.abs(j[id] - r[id]) < 1); }

  private finish(c: SampleCommand) {
    const w = this.world;
    if (c.op === 'gripper') {
      const open = c.state === 'open';
      if (open && w.where === 'held') {
        // letting go: only in the parking socket
        const p = w.plug();
        if (p.socket !== 'park') return this.fail(`the nozzle was let go away from the parking socket (${p.socket ? 'in the ' + p.socket + ' socket' : `${p.offMm.toFixed(0)} mm off the nearest socket`}): it would fall`);
        w.where = 'parked';
      }
      if (!open && w.where === 'parked') {
        // taking: the closed fingers must be on the collar
        const h = w.heldNozzle(), p = w.parkedNozzle();
        const off = Math.hypot(h.centre[0] - p.centre[0], h.centre[1] - p.centre[1], h.centre[2] - p.centre[2]);
        if (off < 0.004) w.where = 'held';
      }
      w.gripOpen = open;
      w.setArm(this.currentArm());
    }
    if (c.op === 'cart') w.setCartY(STOPS[c.to]);
    this.log[this.log.length - 1].t1 = this.time;
  }

  /** Advance by this many sim seconds. Returns true while there is more to do. */
  advance(maxS: number): boolean {
    let left = maxS;
    while (left > 1e-9 && !this.done) {
      if (!this.cur) {
        this.i++;
        if (this.i >= this.commands.length) { this.done = true; break; }
        this.begin(this.commands[this.i]);
        if (this.done) break;
      }
      const cur = this.cur!, w = this.world;
      const dt = Math.min(left, TICK, cur.dur - cur.t);
      cur.t += dt; this.time += dt; left -= dt;
      const s = cur.dur > 0 ? Math.min(1, cur.t / cur.dur) : 1, e = s * s * (3 - 2 * s);   // smooth start and stop
      const c = cur.c;
      if (c.op === 'pose') {
        const j: Record<string, number> = {};
        for (const id of ARM_IDS) j[id] = cur.from![id] + (cur.to![id] - cur.from![id]) * e;
        w.setArm(j);
        if (w.where === 'held') w.write();
      } else if (c.op === 'cart') {
        w.setCartY(cur.fromY! + (cur.toY! - cur.fromY!) * e);
      } else if (c.op === 'pump') {
        const want = c.turns * s, step = want - (cur.done0 ?? 0); cur.done0 = want;
        const signed = c.dir === 'in' ? step : -step;
        this.cmd.pump(signed);
        w.rotorTurns += signed;
        w.pumpMl(signed * this.mlPerTurn);
        w.write();
      }
      w.audit();
      if (w.violation) { this.fail(w.violation); break; }
      this.log[this.log.length - 1].t1 = this.time;
      if (cur.t >= cur.dur - 1e-9) { this.finish(c); this.cur = null; if (w.violation) this.fail(w.violation); }
    }
    return !this.done;
  }

  result(): SampleResult {
    const w = this.world;
    return { ok: this.failReason === '', reason: this.failReason, time: this.time, drawnMl: w.drawnMl, drainedMl: w.drainedMl, newInCupMl: w.newInCup, cupMl: w.cupMl, oldPct: w.oldFraction * 100, steps: this.log };
  }
}
