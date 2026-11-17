// Position and roll sensing of the cart and the home station (OpenPocket #282, owner answer Q3 addendum). Pure maths, no MuJoCo or DOM.
// The controller counts drive-wheel and roll-wheel turns (odometry, it drifts with wheel slip) and corrects the drift at a home station near the
// base of the track: a RING of magnet tape all the way round the pipe ("you are at home", cannot be missed), and a little further up a single POINT
// magnet that marks zero (roll 0 and position zero for the roll). A hall sensor on the cart reads them.
// Lost cart: drive until the ring is hit, move on to the point and roll until the point is found (a full turn at most). Optional checkpoints
// (point magnets at corners and legs) correct the position only.
import { OMNI_R, R_PIPE } from './omni.ts';
import { TRACK_LENGTH_CM } from './track.ts';

export const RING_CM = 10;               // centre of the ring of magnet tape, from the bottom of the leg (ASSUMED, set when the track is built)
export const RING_W_CM = 1.0;            // width of the tape
export const POINT_CM = 16;              // the point magnet, 6 cm beyond the ring centre (ASSUMED)
export const POINT_WINDOW_DEG = 6;       // the hall sensor sees the point magnet within +/- this roll (6 mm magnet on the R16 pipe is 21 deg wide, the sensor threshold narrows it)
export const POINT_WINDOW_CM = 0.5;      // and within +/- this along the pipe
export const HALL_SEEN_STEP_CM = 0.05;   // the controller samples the hall sensor at least this often along the pipe (and 1 degree in the roll), so no edge is missed
export const ENC_COUNTS_PER_REV = 1440;  // encoder counts per wheel turn at the wheel (ASSUMED: motor encoder through the worm)
export const CHECKPOINTS_CM: number[] = [];   // optional extra point magnets (corners, legs); none fitted yet

/** What the hall sensor on the cart reads at true position s (cm) and true roll (deg). */
export function hall(sCm: number, rollDeg: number): { ring: boolean; point: boolean } {
  const ang = ((((rollDeg % 360) + 540) % 360) - 180);
  return { ring: Math.abs(sCm - RING_CM) <= RING_W_CM / 2, point: Math.abs(sCm - POINT_CM) <= POINT_WINDOW_CM && Math.abs(ang) <= POINT_WINDOW_DEG };
}

/** Dead reckoning by counting wheel turns. `slip` is the fraction of the commanded drive distance lost to slip (the estimate does not know it). */
export class Odometry {
  /** estimate: position along the track (cm) and roll (deg), or null when lost */
  s: number | null = null;
  roll: number | null = null;
  slip: number;
  rollSlip: number;
  constructor(slip = 0, rollSlip = 0) { this.slip = slip; this.rollSlip = rollSlip; }
  setKnown(s: number, roll: number) { this.s = s; this.roll = roll; }
  /** The wheels turned by dsTrue cm of travel (true), the encoders counted it quantised, the estimate adds what the encoders say (slip included: the wheel turned, the cart moved less). */
  drive(dsCmWheel: number) {
    const turns = dsCmWheel / (2 * Math.PI * (OMNI_R / 10));
    const counts = Math.round(turns * ENC_COUNTS_PER_REV);
    const est = (counts / ENC_COUNTS_PER_REV) * 2 * Math.PI * (OMNI_R / 10);
    if (this.s !== null) this.s += est;
    return dsCmWheel * (1 - this.slip);   // the true travel
  }
  /** The roll wheel turned by dRollWheelDeg of wheel angle; the sleeve rolls wheelR / pipeR times as much (omni.ts rollSpinPerRoll). */
  rollTurn(dWheelDeg: number) {
    const counts = Math.round((dWheelDeg / 360) * ENC_COUNTS_PER_REV);
    const est = (counts / ENC_COUNTS_PER_REV) * 360 * (OMNI_R / R_PIPE);
    if (this.roll !== null) this.roll += est;
    return dWheelDeg * (OMNI_R / R_PIPE) * (1 - this.rollSlip);   // true sleeve roll (deg)
  }
}

export interface HomingResult { ok: boolean; reason?: string; sErr: number; rollErr: number; travelCm: number; rollDeg: number; steps: string[] }

/**
 * Homing by the owner's recipe, run on a true cart (trueS cm, trueRoll deg) with an odometry that drifts. Steps:
 *  1. lost: drive down until the ring is hit (if the base end is reached first, turn round: the ring is above); the middle of the ring's two edges is RING_CM.
 *  2. the position is known: drive on up to the point magnet by counting wheel turns (the slip adds a small error over these few cm).
 *  3. roll until the point is found (a full turn at most); the middle of its window is roll zero.
 * Returns what is left of the error of the cart's estimate against the truth (only the test and the scene know the truth).
 */
export function runHoming(trueS: number, trueRoll: number, o: { slip?: number; rollSlip?: number; stepCm?: number; stepDeg?: number } = {}): HomingResult {
  const { slip = 0.03, rollSlip = 0.05, stepCm = HALL_SEEN_STEP_CM, stepDeg = 1 } = o;
  const od = new Odometry(slip, rollSlip);
  let s = trueS, roll = trueRoll, travel = 0, rolled = 0;
  const steps: string[] = [];
  /** one drive step of dsWheel cm of wheel travel (sign = direction); returns false when the cart is stopped by an end of the track */
  const drive = (dsWheel: number): boolean => {
    const dTrue = od.drive(dsWheel);
    const next = Math.min(TRACK_LENGTH_CM, Math.max(0, s + dTrue));
    const moved = next !== s || dTrue === 0;
    travel += Math.abs(next - s); s = next;
    return moved;
  };
  // 1. find the ring
  let dir: 1 | -1 = -1, edges: number[] = [], found = false;
  for (let leg = 0; leg < 2 && !found; leg++) {
    for (let guard = 0; guard < (2 * TRACK_LENGTH_CM) / stepCm; guard++) {
      if (!drive(dir * stepCm)) { steps.push(dir < 0 ? 'hit the base end, turning round' : 'hit the far end'); break; }
      if (hall(s, roll).ring) edges.push(s);
      else if (edges.length) { found = true; break; }
    }
    if (!found) { dir = 1; edges = []; }
  }
  if (!found) return { ok: false, reason: 'Never found the ring: stop and ask the owner.', sErr: NaN, rollErr: NaN, travelCm: travel, rollDeg: rolled, steps };
  const ringMid = (edges[0] + edges[edges.length - 1]) / 2;
  steps.push(`ring found, middle ${ringMid.toFixed(2)} cm`);
  od.s = RING_CM + (s - ringMid);   // the estimate is corrected: the cart stands (s - ringMid) past the ring's middle
  // 2. on to the point column
  let guard = 0;
  while (od.s < POINT_CM - 0.01 &&   // one encoder count is 0.008 cm: a smaller step would not count
     guard++ < 10000) { if (!drive(Math.min(stepCm, POINT_CM - od.s))) break; }
  steps.push('at the point magnet column');
  // 3. roll for the point
  // already inside the point's window? back out of it first, so both edges are seen
  for (let i = 0; i < 40 && hall(s, roll).point; i++) { const dRoll = od.rollTurn(-stepDeg * (R_PIPE / OMNI_R)); roll += dRoll; rolled += Math.abs(dRoll); }
  const win: number[] = [];
  let rollFound = false;
  for (let i = 0; i <= (360 + 2 * POINT_WINDOW_DEG) / stepDeg + 2; i++) {
    if (hall(s, roll).point) win.push(roll);
    else if (win.length) { rollFound = true; break; }
    const dRoll = od.rollTurn(stepDeg * (R_PIPE / OMNI_R)); roll += dRoll; rolled += Math.abs(dRoll);
  }
  if (!rollFound) return { ok: false, reason: 'The point magnet was not found within a full turn: stop and ask the owner.', sErr: s - POINT_CM, rollErr: NaN, travelCm: travel, rollDeg: rolled, steps };
  const mid = (win[0] + win[win.length - 1]) / 2;
  steps.push(`point found, window middle at roll ${mid.toFixed(1)} deg`);
  // after rolling back to the window middle the cart's roll is `mid` in the pipe frame (the point magnet is the pipe's roll 0): that is the roll error left
  return { ok: true, sErr: s - POINT_CM, rollErr: angNorm(mid), travelCm: travel, rollDeg: rolled, steps };
}
const angNorm = (a: number) => ((((a % 360) + 540) % 360) - 180);
