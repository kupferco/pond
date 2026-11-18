// Transfer controller for the omni cart (OpenPocket #283, plan task 265 part 9, owner answers Q3, Q7, Q8). Pure maths and a state machine, no DOM; the scene writes the state into MuJoCo
// with placeTransfer (omni-transfer.ts).
//
// A transfer releases one hand (its jaw opens), rolls the WHOLE cart about the other (static) hand's pipe until the free hand is off its own pipe, drives on the static pipe round the bend with
// the roll held (Q7), rolls back flat at the start of the top run and drives on to the top. Q3: the roll goes the way that clears; if neither does the controller stops and says so.
// The roll angle is positive towards the plate side (the free hand swings to -y, in front of the pipe plane) and negative towards the spine side.
import { ROLL_DEG_S, ROLL_HOME_TOL_DEG, canRoll, driveLimit, pickRollDirection } from './roll.ts';
import { P_BEND_END, P_TOP_CM, ROLL_STATION_CM, S_FLAT_CM, S_MAX_CM, S_MIN_CM, S_START_CM, other } from './omni-transfer.ts';
import type { Hand } from './omni.ts';
export { P_TOP_CM, ROLL_STATION_CM, S_FLAT_CM, S_MAX_CM, S_MIN_CM, S_START_CM, P_BEND_END };

/**
 * The jaw wedge's far edge in degrees (the hinge pin sits there, cad/cart_sleeves.py JAW_A1) and the roll corridors it gives, found by scripts/search-swing.ts (MuJoCo contact detection, jaw open 92 degrees,
 * both trips, both directions, roll angles 0..180 in 1 degree steps, held at every 0.25 cm from the roll station to the roll-back point; test/sim.test.ts probes them again).
 *  - 'cad' = the wedge as drawn (0 to 110 degrees): NEITHER direction clears. The free hand moves along the roll circle, which at first is straight to the plate side or the spine side, and the
 *    fixed part of the sleeve (110 to 340 degrees) is still round the pipe after 2 to 3 degrees of roll. This is the go or no-go finding of the plan: the design does not work as drawn.
 *  - 'wide' = the wedge to 150 degrees: the plate side clears from 35 to 180 degrees (the spine side still does not). A wedge to 140 degrees is the least that works (135 does not).
 */
export type Variant = 'cad' | 'wide';
export const JAW_A1_DEG: Record<Variant, number> = { cad: 110, wide: 150 };
export interface Corridor { plate: [number, number] | null; spine: [number, number] | null }
export const CORRIDORS: Record<Variant, Record<Hand, Corridor>> = {
  cad: { B: { plate: null, spine: null }, C: { plate: null, spine: null } },
  wide: { B: { plate: [35, 180], spine: null }, C: { plate: [35, 180], spine: null } },
};
/** The roll the transfer uses when the corridor allows it: a quarter turn, well inside 35 to 180 degrees (the same swing as sim/unit_change.py). */
export const TRANSFER_ROLL_DEG = 90;

/** Roll plan of a trip where `rider` stays clamped: the direction that clears (Q3, plate side first), the signed roll (deg) and, when neither clears, why. */
export function rollPlan(variant: Variant, rider: Hand): { dir: 1 | -1 | null; roll: number; side: 'plate' | 'spine' | null; reason?: string } {
  const c = CORRIDORS[variant][rider], pick = pickRollDirection({ plus: !!c.plate, minus: !!c.spine });
  if (pick.dir === null) return { dir: null, roll: 0, side: null, reason: pick.reason };
  const [lo, hi] = (pick.dir === 1 ? c.plate : c.spine)!, deg = Math.min(hi, Math.max(lo, TRANSFER_ROLL_DEG));
  return { dir: pick.dir, roll: pick.dir * deg, side: pick.dir === 1 ? 'plate' : 'spine' };
}

export const DEFAULT_SPEED_CM_S = 8, MAX_SPEED_CM_S = 50, DEFAULT_STEP_CM = 5;
export const ROLL_PREVIEW_DEG_S = 60;           // default roll speed in the scene so the roll can be followed; the real limit is ROLL_DEG_S (motor and grip)
export const HAND_MOVE_S = 2;                   // seconds a jaw takes to open or close
export { ROLL_DEG_S };
const EPS = 1e-9;
/** The roll station window on the leg (cm): the rolled sleeve must be clear of the track-joint rods below (the top rod ends at 36.4 cm; the sleeve is 12.4 cm long) and below the bend. */
export const ROLL_WINDOW_CM: [number, number] = [ROLL_STATION_CM - 3, S_MAX_CM];
/** The declared roll at the start of the top run (the roll is held through the bend, Q7, and changes only on straight track): from the end of the bend 5 cm on, where there is no bracket. */
export const RUN_ROLL_WINDOW_CM: [number, number] = [S_FLAT_CM - 0.01, S_FLAT_CM + 5];

export interface CartState { s: number; roll: number; openB: number; openC: number }
export const initialState = (): CartState => ({ s: S_START_CM, roll: 0, openB: 0, openC: 0 });
export const handName = (h: Hand) => h;

export type StepName = 'toStation' | 'release' | 'roll' | 'move' | 'rollBack' | 'moveTop' | 'moveFlat' | 'moveBack' | 'clamp';
/** Label of a step for a transfer that releases hand `free`. */
export function stepLabel(name: StepName, free: Hand = 'B'): string {
  const S = other(free);
  return ({
    toStation: `Driving to the roll station (${ROLL_STATION_CM} cm), both hands clamped`, release: `Releasing hand ${free}: the jaw opens`, roll: `Rolling the whole cart about pipe ${S}'s centre line, hand ${free} swings clear of pipe ${free}`,
    move: `Driving on pipe ${S} round the bend, roll held`, rollBack: 'Rolling back, flat again', moveTop: `Driving flat along pipe ${S}'s top bar`, moveFlat: `Driving back along pipe ${S}'s top bar`,
    moveBack: 'Driving back round the bend, roll held, to the top of the leg', clamp: `Clamping hand ${free} on pipe ${free}`,
  } as Record<StepName, string>)[name];
}
interface Goal { s: number; roll: number; openB: number; openC: number }

/**
 * Cart controller. Every continuous quantity (position along the track, roll, jaw openings) moves towards its goal at its own rate, behind interlocks:
 *  - the roll turns only with the static hand clamped, the free hand's jaw fully open, at the roll station on the leg (or at the declared roll-back point at the start of the top run), and never beyond 180 degrees;
 *  - the cart drives only flat (within 3 degrees of home) or inside a declared transfer roll (free jaw fully open), and a rolled cart never goes onto the top run;
 *  - a jaw opens or closes only on the straight leg with the cart flat; the free hand's jaw can open only while the other is clamped.
 * `start(free)` runs a whole transfer and refuses, saying why, when the roll plan finds no direction that clears (Q3).
 */
export class TransferRun {
  readonly st = initialState();
  goal: Goal = { s: S_START_CM, roll: 0, openB: 0, openC: 0 };
  speed = DEFAULT_SPEED_CM_S;
  rollDegS = ROLL_PREVIEW_DEG_S;
  queue: { name: StepName; goal: Partial<Goal> }[] = [];
  current: StepName | null = null;
  msg = '';
  done = false;
  lastTrip: Hand | null = null;
  /** Which hand a transfer releases when neither is open yet (B: the trip up pipe C). */
  private hint: Hand = 'B';
  variant: Variant;
  constructor(variant: Variant = 'cad') { this.variant = variant; }

  get plan() { return rollPlan(this.variant, other(this.free)); }
  /** The free (released or being released) hand: the more open one; with both clamped, the hand the next transfer releases. */
  get free(): Hand { const { openB: b, openC: c } = this.st; return b > c ? 'B' : c > b ? 'C' : this.hint; }
  /** The static (riding) hand. */
  get rider(): Hand { return other(this.free); }
  open(h: Hand) { return h === 'B' ? this.st.openB : this.st.openC; }
  private key(h: Hand): 'openB' | 'openC' { return h === 'B' ? 'openB' : 'openC'; }
  get rolled() { return Math.abs(this.st.roll) > ROLL_HOME_TOL_DEG; }
  get rolling() { return this.st.roll !== this.goal.roll; }
  get busy() { return this.current !== null; }
  get spanning() { return this.st.openB <= EPS && this.st.openC <= EPS; }
  /** Where the cart is: on the leg (both pipes), the bend or the top run. */
  get where(): 'leg' | 'bend' | 'run' { return this.st.s <= S_MAX_CM + EPS ? 'leg' : this.st.s <= S_FLAT_CM + EPS ? 'bend' : 'run'; }

  private refuse(why: string) { this.msg = why; return false; }
  setSpeed(v: number) { this.speed = Math.min(MAX_SPEED_CM_S, Math.max(0.1, v)); }
  private atStation() { return this.st.s >= ROLL_WINDOW_CM[0] - EPS && this.st.s <= ROLL_WINDOW_CM[1] + EPS; }
  private atRunRoll() { return this.st.s >= RUN_ROLL_WINDOW_CM[0] - EPS && this.st.s <= RUN_ROLL_WINDOW_CM[1] + EPS; }

  /** Step buttons: move the cart along the track by d cm. Both hands clamped: the straight leg only. Free hand released and rolled: round the bend up to S_FLAT_CM; flat and released on the run: along the top bar. */
  nudge(d: number): boolean {
    if (this.busy) return this.refuse('Wait for the running transfer to finish.');
    if (this.rolling) return this.refuse('The cart is mid-roll: finish the roll first.');
    const s = this.st, F = this.free, fo = this.open(F), want = this.goal.s + d;
    if (!this.spanning && fo > EPS && fo < 1 - EPS) return this.refuse(`Hand ${F}'s jaw is moving: wait for it.`);
    const onRun = fo >= 1 - EPS && !this.rolled && s.s > S_MAX_CM + EPS;
    if (this.rolled && fo < 1 - EPS) return this.refuse(`Rolled: hand ${F} must be released (fully open) to drive.`);
    const lo = onRun ? S_FLAT_CM : S_MIN_CM, hi = this.rolled ? driveLimit(s.s, Infinity, s.roll, true, S_FLAT_CM).s : onRun ? P_TOP_CM : S_MAX_CM;
    this.goal.s = Math.min(hi, Math.max(lo, want));
    this.msg = this.goal.s === want ? '' : this.rolled ? 'Rolled: the cart stops at the end of the bend, the run needs roll 0.' : s.s >= S_MAX_CM - EPS && !onRun ? `Roll first (hand ${F} released): the cart drives round the bend only with the roll held.` : '';
    return true;
  }
  /** Open (release) or close (clamp) a hand's jaw. Only on the straight leg with the cart flat, and not both. */
  clampHand(hand: Hand, open: boolean): boolean {
    const o = other(hand);
    if (this.busy) return this.refuse('Wait for the running transfer to finish.');
    if (this.rolling || this.rolled) return this.refuse('Roll back flat first: a jaw only opens or closes on its pipe.');
    if (this.st.s > S_MAX_CM + EPS) return this.refuse(`Hand ${hand} has no pipe to clamp here: pipe ${hand} is behind, on the leg (press Reset).`);
    if (open && (this.open(o) > EPS || this.goal[this.key(o)] > EPS)) return this.refuse(`Hand ${o} is not clamped: releasing hand ${hand} as well would let go of the track.`);
    this.goal[this.key(hand)] = open ? 1 : 0; if (open) this.hint = hand; this.msg = ''; return true;
  }
  /** Roll the cart: `toward` 1 = to the planned roll, 0 = back flat. Refused unless the free hand is released, the static hand clamped and the cart is at a place where it may roll. */
  rollTo(toward: 0 | 1, override?: number): boolean {
    if (this.busy) return this.refuse('Wait for the running transfer to finish.');
    const F = this.free, S = this.rider;
    if (this.open(S) > EPS) return this.refuse(`Hand ${S} must stay clamped: the cart rolls about its pipe.`);
    if (this.open(F) < 1 - EPS) return this.refuse(`Release hand ${F} first.`);
    const target = toward ? override ?? this.plan.roll : 0;   // `override`: try an angle by hand (shows the clash when no direction clears)
    if (toward && override === undefined && this.plan.dir === null) return this.refuse(this.plan.reason ?? 'No roll direction clears.');
    if (!this.atStation() && !this.atRunRoll()) { const v = canRoll(this.st.s, target); return this.refuse(v.ok ? `Drive to the roll station (${ROLL_WINDOW_CM[0]} to ${ROLL_WINDOW_CM[1]} cm) first: the rolled sleeve must clear the track-joint rods.` : v.reason!); }
    this.goal.roll = target; this.msg = ''; return true;
  }
  stop() { this.queue = []; this.current = null; this.goal = { ...this.st }; this.msg = 'Stopped.'; }
  reset(s = S_MAX_CM) { Object.assign(this.st, initialState(), { s }); this.goal = { ...this.st }; this.queue = []; this.current = null; this.done = false; this.msg = ''; this.lastTrip = null; }

  /**
   * Run the whole transfer from where the cart is. Both hands clamped on the leg: drive to the roll station, release hand `release` (default B: the trip up pipe C; C: the trip up pipe B), roll, drive on the other
   * hand's pipe round the bend with the roll held, roll back at the start of the top run, drive to the top. From the top of a pipe with one hand off: the same back, ending with the free hand clamped again.
   * Refuses, with the reason, when the roll plan finds no direction that clears (Q3: stop and ask the owner).
   */
  start(release?: Hand, chain = false): boolean {
    if (this.busy) return this.refuse('A transfer is already running.');
    if (this.rolling || this.rolled) return this.refuse('The cart is rolled: roll it back first.');
    const s = this.st, F = this.free, k = this.key(F), top = s.s > S_MAX_CM + EPS;
    const trip = (R: Hand): { name: StepName; goal: Partial<Goal> }[] => [{ name: 'toStation', goal: { s: ROLL_STATION_CM } }, { name: 'release', goal: { [this.key(R)]: 1 } }, { name: 'roll', goal: { roll: rollPlan(this.variant, other(R)).roll } },
      { name: 'move', goal: { s: S_FLAT_CM } }, { name: 'rollBack', goal: { roll: 0 } }, { name: 'moveTop', goal: { s: P_TOP_CM } }];
    const R: Hand = top ? other(F) : (release ?? 'B');
    if (top && !(this.open(F) >= 1 - EPS && this.goal[k] >= 1 - EPS && this.open(other(F)) <= EPS)) return this.refuse('Press Reset: the cart is not on a top bar with one hand clamped.');
    if (!top && (s.openB > EPS || s.openC > EPS || this.goal.openB > EPS || this.goal.openC > EPS)) return this.refuse('Clamp both hands first (on the leg), or press Reset.');
    const tripOf = top ? F : R;                       // the hand whose pipe is being left or rejoined
    const p = rollPlan(this.variant, other(tripOf));
    if (p.dir === null) return this.refuse(`${p.reason} Jaw wedge ${JAW_A1_DEG[this.variant]} degrees: the free hand cannot leave its pipe in either roll direction.`);
    if (top) {
      this.queue = [{ name: 'moveFlat', goal: { s: S_FLAT_CM } }, { name: 'roll', goal: { roll: p.roll } }, { name: 'moveBack', goal: { s: ROLL_STATION_CM } }, { name: 'rollBack', goal: { roll: 0 } }, { name: 'clamp', goal: { [k]: 0 } }];
      const next = other(F);
      if (chain || release === next) { this.queue.push(...trip(next)); this.lastTrip = next; this.hint = next; }
    } else { this.hint = R; this.lastTrip = R; this.queue = trip(R); }
    this.done = false; this.msg = ''; this.next(); return true;
  }
  /** One button: from rest, the trip up pipe C (first press) or the other pipe than last time; from the top of a pipe, back to rest and straight on up the other pipe. */
  press(): boolean { return this.start(this.lastTrip === 'B' ? 'C' : 'B', this.st.s > S_MAX_CM + EPS); }
  private next() {
    const n = this.queue.shift();
    if (!n) { this.current = null; this.done = true; return; }
    this.current = n.name; Object.assign(this.goal, n.goal);
  }
  private reached() { const g = this.goal, s = this.st; return Math.abs(g.s - s.s) < EPS && Math.abs(g.roll - s.roll) < EPS && Math.abs(g.openB - s.openB) < EPS && Math.abs(g.openC - s.openC) < EPS; }
  private toward(cur: number, goal: number, rate: number, dt: number) { const e = goal - cur, step = rate * dt; return Math.abs(e) <= Math.max(step, EPS) ? goal : cur + Math.sign(e) * step; }

  advance(dt: number) {
    const s = this.st, g = this.goal, F = this.free, S = this.rider;
    s.openB = this.toward(s.openB, g.openB, 1 / HAND_MOVE_S, dt);
    s.openC = this.toward(s.openC, g.openC, 1 / HAND_MOVE_S, dt);
    // the roll: static hand clamped, free hand fully open, at a place where rolling is allowed
    const rollOk = this.open(S) <= EPS && this.open(F) >= 1 - EPS && (this.atStation() || this.atRunRoll());
    if (g.roll !== s.roll) { if (rollOk) s.roll = this.toward(s.roll, g.roll, this.rollDegS, dt); else if (!this.busy) g.roll = s.roll; }
    // driving: not mid-roll, and flat with the free jaw closed or open (not moving), or rolled with the free jaw fully open (the declared transfer roll)
    const fo = this.open(F), flat = !this.rolled && !this.rolling;
    if (g.s !== s.s && !this.rolling && (this.rolled ? fo >= 1 - EPS : fo <= EPS || fo >= 1 - EPS)) {
      const lim = driveLimit(s.s, g.s, s.roll, this.rolled, S_FLAT_CM);
      const target = flat ? g.s : lim.s;
      s.s = this.toward(s.s, target, this.speed, dt);
    }
    if (this.current && this.reached()) { s.s = g.s; this.next(); }
  }
}
