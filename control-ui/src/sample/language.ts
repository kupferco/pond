// The sampling part of the command language: named arm poses, the gripper, the cart stops and the pump, as text lines
// ("pose unit_in", "pump in 70") and as data. Sim and Real run the same list. Pure data: no MuJoCo here.
import { DEFAULT_INTERVAL_DAYS, ML_PER_TURN, POSE_NAMES, READ_S, SAMPLE_ML, type PoseName, type Stop } from './layout.ts';

export type SampleCommand =
  | { op: 'pose'; name: PoseName }
  | { op: 'gripper'; state: 'open' | 'close' }
  | { op: 'cart'; to: Stop }
  | { op: 'pump'; dir: 'in' | 'out'; turns: number }
  | { op: 'wait'; s: number };

export function formatCommand(c: SampleCommand): string {
  switch (c.op) {
    case 'pose': return `pose ${c.name}`;
    case 'gripper': return `gripper ${c.state}`;
    case 'cart': return `cart to ${c.to}`;
    case 'pump': return `pump ${c.dir} ${c.turns}`;
    case 'wait': return `wait ${c.s}`;
  }
}

/** One line to one command; throws a message a person can read. */
export function parseCommand(line: string): SampleCommand {
  const w = line.trim().toLowerCase().split(/\s+/);
  const bad = (why: string) => new Error(`"${line.trim()}": ${why}`);
  const num = (s: string | undefined, what: string) => { const v = Number(s); if (s === undefined || !Number.isFinite(v) || v <= 0) throw bad(`${what} must be a number above 0`); return v; };
  if (w[0] === 'pose') {
    if (!(POSE_NAMES as readonly string[]).includes(w[1])) throw bad(`unknown pose (known: ${POSE_NAMES.join(', ')})`);
    return { op: 'pose', name: w[1] as PoseName };
  }
  if (w[0] === 'gripper') {
    if (w[1] !== 'open' && w[1] !== 'close') throw bad('use gripper open or gripper close');
    return { op: 'gripper', state: w[1] };
  }
  if (w[0] === 'cart' && w[1] === 'to') {
    if (w[2] !== 'unit' && w[2] !== 'station') throw bad('use cart to unit or cart to station');
    return { op: 'cart', to: w[2] };
  }
  if (w[0] === 'pump') {
    if (w[1] !== 'in' && w[1] !== 'out') throw bad('use pump in <turns> (draw) or pump out <turns> (reverse)');
    return { op: 'pump', dir: w[1], turns: num(w[2], 'turns') };
  }
  if (w[0] === 'wait') return { op: 'wait', s: num(w[1], 'seconds') };
  throw bad('unknown command (pose, gripper, cart to, pump, wait)');
}

/** A script: one command per line; blank lines and "#" comments are ignored. */
export const parseScript = (text: string): SampleCommand[] =>
  text.split('\n').map((l) => l.replace(/#.*/, '').trim()).filter(Boolean).map(parseCommand);

export interface SampleConfig {
  /** Run every this many days (1 = daily, the default). */
  intervalDays: number;
  sampleMl: number;
  mlPerTurn: number;
  readS: number;
}
export const DEFAULT_CONFIG: SampleConfig = { intervalDays: DEFAULT_INTERVAL_DAYS, sampleMl: SAMPLE_ML, mlPerTurn: ML_PER_TURN, readS: READ_S };

export const turnsFor = (ml: number, mlPerTurn: number) => +(ml / mlPerTurn).toFixed(3);

const c = (op: string, rest: Record<string, unknown> = {}) => ({ op, ...rest }) as SampleCommand;
const takeNozzle: SampleCommand[] = [c('gripper', { state: 'open' }), c('pose', { name: 'park_above' }), c('pose', { name: 'park_in' }), c('gripper', { state: 'close' }), c('pose', { name: 'park_above' })];
const parkNozzle: SampleCommand[] = [c('pose', { name: 'park_above' }), c('pose', { name: 'park_in' }), c('gripper', { state: 'open' }), c('pose', { name: 'park_above' }), c('pose', { name: 'rest' }), c('gripper', { state: 'close' })];

/** The whole sampling run: collect at a unit, then test at the station. */
export function samplePlan(cfg: SampleConfig = DEFAULT_CONFIG): SampleCommand[] {
  const turns = turnsFor(cfg.sampleMl, cfg.mlPerTurn);
  return [
    c('cart', { to: 'unit' }),
    ...takeNozzle,
    c('pose', { name: 'unit_above' }), c('pose', { name: 'unit_in' }),
    c('pump', { dir: 'in', turns }),                         // the tube draws the sample
    c('pose', { name: 'unit_above' }),
    ...parkNozzle,
    c('cart', { to: 'station' }),
    ...takeNozzle,
    c('pose', { name: 'station_above' }), c('pose', { name: 'station_in' }),
    c('pump', { dir: 'out', turns }),                        // reverse: the old sample is flushed out over the standpipe, the new one stays in the cup
    c('pose', { name: 'station_above' }),
    ...parkNozzle,
    c('wait', { s: cfg.readS }),                              // the station reads pH, EC and temperature
  ];
}

/** Daily by default: is a run due? `lastRunMs` null = never ran. */
export function runDue(lastRunMs: number | null, nowMs: number, intervalDays: number): boolean {
  if (!(intervalDays > 0)) throw new Error('The interval must be above 0 days');
  return lastRunMs === null || nowMs - lastRunMs >= intervalDays * 86_400_000;
}
export const nextRunMs = (lastRunMs: number, intervalDays: number) => lastRunMs + intervalDays * 86_400_000;
