// Pod and slot placement: reach region, clamping and seeded randomisation.
import { MIN_SEPARATION, REACH } from './dims.ts';

export type XY = [number, number]; // metres

/** Small seeded PRNG (mulberry32) so every logged run can be replayed from its seed. */
export function rng(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function gauss(rand: () => number): number {
  const u = Math.max(rand(), 1e-12), v = rand();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}

export const inReach = ([x, y]: XY): boolean => {
  const r = Math.hypot(x, y), a = Math.abs(Math.atan2(y, x)) * 180 / Math.PI;
  return r >= REACH.rMin - 1e-9 && r <= REACH.rMax + 1e-9 && a <= REACH.angMax + 1e-9;
};

/** Nearest point inside the reach region. */
export function clampToReach([x, y]: XY): XY {
  let r = Math.hypot(x, y), a = Math.atan2(y, x);
  const am = REACH.angMax * Math.PI / 180;
  r = Math.min(REACH.rMax, Math.max(REACH.rMin, r));
  a = Math.min(am, Math.max(-am, a));
  return [r * Math.cos(a), r * Math.sin(a)];
}

export const farEnough = (pod: XY, slot: XY): boolean => Math.hypot(pod[0] - slot[0], pod[1] - slot[1]) >= MIN_SEPARATION - 1e-9;

/** Random reachable pod and slot, at least MIN_SEPARATION apart. */
export function randomPlacement(seed: number): { pod: XY; slot: XY } {
  const rand = rng(seed);
  const point = (): XY => {
    const r = Math.sqrt(REACH.rMin ** 2 + rand() * (REACH.rMax ** 2 - REACH.rMin ** 2)); // uniform over area
    const a = (rand() * 2 - 1) * REACH.angMax * Math.PI / 180;
    return [r * Math.cos(a), r * Math.sin(a)];
  };
  for (;;) {
    const pod = point(), slot = point();
    if (farEnough(pod, slot)) return { pod, slot };
  }
}
