// Roll control of the omni cart on the track (OpenPocket #282, plan task 265 part 8, owner answers Q3, Q7, Q8). Pure maths, no MuJoCo or DOM.
// The whole base (cart) spins round the riding pipe on the omni wheels: the roll angle is 0 when the base is flat (parallel to the track plane, the
// free hand on the inside of the bend), + turns the plate side up out of the plane one way, - the other way.
import { sectionAt, type Section } from './track.ts';
import { rollBudget } from './omni.ts';

/** The roll must be within this of home (0) to drive along the pipe, except inside a declared transfer roll (plan section 7). */
export const ROLL_HOME_TOL_DEG = 3;
/** Q8: 180 degrees only on the vertical legs; on the runs the cart stays flat so it passes the brackets that hold the track. */
export const MAX_ROLL_DEG: Record<Section, number> = { vertical: 180, curve: 0, horizontal: 0 };
/** Roll speed of the sleeve (deg/s) from the roll budget (motor limited, plan section 3). */
export const ROLL_DEG_S = rollBudget().rollDegS;

export type Zone = Section;
export const zoneAt = (sCm: number): Zone => sectionAt(sCm);
export const angDiff = (a: number, b: number) => ((((a - b) % 360) + 540) % 360) - 180;   // a - b wrapped to (-180, 180]

export interface Verdict { ok: boolean; reason?: string }
const ok = (): Verdict => ({ ok: true });
const no = (reason: string): Verdict => ({ ok: false, reason });

/** May the roll be changed here? Only on the vertical legs, and never beyond 180 degrees. Q7: on the bend the roll is held, not changed. */
export function canRoll(sCm: number, targetDeg: number): Verdict {
  const z = zoneAt(sCm);
  if (z === 'curve') return no('The roll is held through the bend: roll on the leg before it.');
  if (z === 'horizontal') return no('On the top and bottom runs the cart stays flat (roll 0) to pass the track brackets.');
  if (Math.abs(targetDeg) > MAX_ROLL_DEG.vertical + 1e-9) return no(`The roll is limited to ${MAX_ROLL_DEG.vertical} degrees.`);
  return ok();
}

/**
 * How far along may the cart drive from s towards goal (cm) at this roll? Returns the reachable position and why it stops short.
 * - flat (within 3 degrees of home): free, anywhere.
 * - rolled: only with a declared transfer roll (`carry`), along the leg and round the bend, never onto a run (the run needs roll 0, Q8).
 */
export function driveLimit(sCm: number, goalCm: number, rollDeg: number, carry: boolean, runStartCm: number): { s: number; reason?: string } {
  const flat = Math.abs(angDiff(rollDeg, 0)) <= ROLL_HOME_TOL_DEG;
  if (flat) return { s: goalCm };
  if (!carry) return { s: sCm, reason: `Rolled ${rollDeg.toFixed(0)} degrees: roll back to within ${ROLL_HOME_TOL_DEG} degrees of home before driving.` };
  if (goalCm > runStartCm && sCm <= runStartCm) return { s: Math.min(goalCm, runStartCm), reason: 'Rolled: stops at the end of the bend, the run needs roll 0.' };
  return { s: goalCm };
}

/**
 * Q3: which roll direction clears? `clears` says, for each signed direction, whether the whole swept corridor is free of contact.
 * Always use the one that clears (the + side first when both do); if neither does, stop and ask the owner.
 */
export function pickRollDirection(clears: { plus: boolean; minus: boolean }): { dir: 1 | -1 | null; reason?: string } {
  if (clears.plus) return { dir: 1 };
  if (clears.minus) return { dir: -1 };
  return { dir: null, reason: 'Neither roll direction clears the track: stop and ask the owner.' };
}

/** Roll as a motion, like CartMotion: moves the roll angle (deg) to a goal at a set speed, always the way chosen (no shortcut through the other side). */
export class RollMotion {
  roll = 0;
  goal = 0;
  speed = ROLL_DEG_S;
  get moving() { return this.goal !== this.roll; }
  moveTo(goalDeg: number) { this.goal = goalDeg; }
  advance(dt: number): boolean {
    if (!this.moving) return false;
    const d = this.goal - this.roll, step = this.speed * dt;
    if (Math.abs(d) <= step) { this.roll = this.goal; return true; }
    this.roll += Math.sign(d) * step;
    return false;
  }
}

/** Bounds of the roll motion: the part of -180..180 the roll may move through when it starts at `fromDeg` and turns to `toDeg` in direction dir (sweep samples, deg). */
export function sweep(fromDeg: number, toDeg: number, stepDeg = 5): number[] {
  const out: number[] = [], n = Math.max(1, Math.ceil(Math.abs(toDeg - fromDeg) / stepDeg));
  for (let i = 0; i <= n; i++) out.push(fromDeg + ((toDeg - fromDeg) * i) / n);
  return out;
}
