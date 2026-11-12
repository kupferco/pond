// Cart track: ONE pipe that goes up, bends and runs to the right, and the cart's motion along it.
// Pure maths, no MuJoCo or DOM. Track plane is X (right) and Z (up, MuJoCo); the pipe sits at y = 0.
// Path coordinate s is in cm from the bottom of the vertical section to the end of the horizontal section.

// Dimensions in mm. DECIDED numbers come from cad/hand_sleeve.py and cad/cart_dims.py; the rest are ASSUMED placeholders.
export const PIPE_D_MM = 32;             // DECIDED (hand_sleeve.py PIPE_D)
export const PIPE_SPACING_MM = 280;      // ASSUMED in cart_dims.py: distance from the clamped (engaged) wheel to the free wheel across the cart
export const BEND_R_MM = 150;            // DECIDED in cart_wheel_pairs.py (loop corner centreline radius)
export const VERTICAL_MM = 600;          // ASSUMED: vertical section length
export const HORIZONTAL_MM = 600;        // ASSUMED: horizontal section length
export const SLEEVE_L_MM = 90;           // hand_sleeve.py SLEEVE_L
export const SLEEVE_R_MM = 36;           // wheel centre radius 26 + wheel radius 10 (hand_sleeve.py)
export const PLATE_MM = { alongTrack: 112, across: 380, t: 6, x0: -202, x1: 178 }; // cart_dims.py: 112 x 380 x 6 open frame, x0/x1 relative to the cart centre line (-spacing/2 - 62 to +spacing/2 + 38)

export type Section = 'vertical' | 'curve' | 'horizontal';
export interface PathPoint { x: number; z: number; tx: number; tz: number; section: Section }

const cm = (mm: number) => mm / 10;
export const L_VERT = cm(VERTICAL_MM);
export const L_ARC = (Math.PI / 2) * cm(BEND_R_MM);
export const L_HORIZ = cm(HORIZONTAL_MM);
export const TRACK_LENGTH_CM = L_VERT + L_ARC + L_HORIZ;
export const DEFAULT_STEP_CM = 5;
export const DEFAULT_SPEED_CM_S = 10;
export const MAX_SPEED_CM_S = 100;
export const ARRIVE_TOL_CM = 0.05;

export const clampS = (s: number) => Math.min(TRACK_LENGTH_CM, Math.max(0, s));

/**
 * Position (metres) and unit tangent of the track centre line at path distance s (cm). Clamped to the ends.
 * s = 0 is the bottom of the vertical section; the cart goes UP the pipe, round the bend, then to the RIGHT (+X).
 * The vertical section lies on x = 0 from z = 0 up; the bend centre is at (r, lengthV); the horizontal section lies on z = lengthV + r.
 */
export function pathAt(sCm: number): PathPoint {
  const s = clampS(sCm) / 100;
  const lv = L_VERT / 100, la = L_ARC / 100, r = cm(BEND_R_MM) / 100;
  if (s <= lv) return { x: 0, z: s, tx: 0, tz: 1, section: 'vertical' };
  if (s <= lv + la) {
    const a = (s - lv) / r; // turned angle, 0..90 deg
    return { x: r - r * Math.cos(a), z: lv + r * Math.sin(a), tx: Math.sin(a), tz: Math.cos(a), section: 'curve' };
  }
  return { x: r + (s - lv - la), z: lv + r, tx: 1, tz: 0, section: 'horizontal' };
}

export const sectionAt = (sCm: number): Section => pathAt(sCm).section;

/**
 * MuJoCo quaternion (w x y z) for the cart frame: x along the tangent, z toward the INSIDE of the bend (the cart body sits inside the bend),
 * so -z is the outer side of the track, where the free wheel is. y = -world Y.
 * Built as a rotation about +Y by th (x along the tangent) followed by a half turn about the cart x axis.
 */
export function frameQuat(p: PathPoint): [number, number, number, number] {
  const th = Math.atan2(-p.tz, p.tx);
  return [0, Math.cos(th / 2), 0, -Math.sin(th / 2)];
}

export type MoveResult = { arrived: boolean };

/** The cart's motion along the path: moves its coordinate toward a goal at a set speed, clamped at the track ends. */
export class CartMotion {
  s = 0;
  goal = 0;
  speed = DEFAULT_SPEED_CM_S;

  /** Set a new goal (cm), clamped to the track. Returns the clamped goal. */
  moveTo(goalCm: number): number { this.goal = clampS(goalCm); return this.goal; }
  /** Move the goal by delta (cm) from the current goal (cumulative taps). */
  nudge(deltaCm: number): number { return this.moveTo(this.goal + deltaCm); }
  get moving() { return this.goal !== this.s; }

  advance(dt: number): MoveResult {
    if (!this.moving) return { arrived: false };
    const d = this.goal - this.s;
    const step = Math.max(0, this.speed) * dt;
    if (Math.abs(d) <= step) { this.s = this.goal; return { arrived: true }; }
    this.s += Math.sign(d) * step;
    return { arrived: false };
  }
}

/** Deterministic pseudo-random target in [0, length] from a seed (mulberry32). */
export function randomTarget(seed: number): number {
  let t = (seed + 0x6d2b79f5) | 0;
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  const u = ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  return Math.round(u * TRACK_LENGTH_CM * 10) / 10;
}
