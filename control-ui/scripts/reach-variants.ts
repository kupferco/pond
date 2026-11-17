// What smallest change of the cart's mount would let the arm reach the holes? A kinematic-only study (distance, angle, joint limits; no collision test, so it is an upper bound):
// the arm base is put at (bx, by) from the track leg's axis (world x = XT + bx, y = leg + by towards the pipe plane) and points along -x (turn 0) or +x (turn 180, towards the front of the tank),
// the cart is moved along both legs (20 mm steps) and every one of the 24 holes / 16 pods is tried. As is: bx = -108.5 mm, by = 60 mm, turn 0. Rolled 180 about the leg: bx = +108.5, by = -60, turn 180.
// Usage: node --experimental-strip-types scripts/reach-variants.ts
import { XB, XT, YC } from '../src/transplant/layout.ts';
import { HOLES, PODS, CART_MAX, CART_MIN } from '../src/reach/layout.ts';
import { attempt } from '../src/reach/test.ts';
import { LEG_A_Y, LEG_B_Y, Rz, quatOf, type Station } from '../src/reach/station.ts';
import { podCapTop, seatCapTop, seatDir } from '../src/reach/layout.ts';

type V3 = [number, number, number];
const mk = (turn: number, bx: number, by: number, leg: 'A' | 'B'): Station[] => {
  const out: Station[] = [], sgn = leg === 'A' ? 1 : -1, legY = leg === 'A' ? LEG_A_Y : LEG_B_Y;
  for (let z = CART_MIN; z <= CART_MAX + 1e-9; z += 0.02) {
    const R = Rz(turn);
    out.push({ kind: leg === 'A' ? 'leg A' : 'leg B', roll: turn, at: z, R, W: [XT + bx, legY + sgn * by, z], H: [XB, YC, 0], pos: [0, 0, 0], quat: quatOf(R), label: `leg ${leg}, ${z.toFixed(2)} m` });
  }
  return out;
};
export function count(turn: number, bx: number, by: number) {
  const sts = [...mk(turn, bx, by, 'A'), ...mk(turn, bx, by, 'B')];
  let h = 0, p = 0; const hs: number[] = [];
  for (const x of HOLES) { const d = seatDir(x); if (attempt(null, sts, seatCapTop(x), [-d[0], -d[1], -d[2]], d).ok) { h++; hs.push(x.n); } }
  for (const x of PODS) if (attempt(null, sts, podCapTop(x), [0, 0, -1] as V3, [0, 0, 1] as V3).ok) p++;
  return { h, p, hs };
}
const asIs = count(0, XB - XT, YC - LEG_A_Y), rolled = count(180, XT - XB, -(YC - LEG_A_Y));
console.log('as is  ', JSON.stringify({ h: asIs.h, p: asIs.p }), ' rolled 180 about the leg', JSON.stringify({ h: rolled.h, p: rolled.p }));
const rows: { turn: number; bx: number; by: number; h: number; p: number }[] = [];
for (const turn of [0, 180]) for (let bx = -0.3; bx <= 0.3001; bx += 0.025) for (let by = -0.3; by <= 0.3001; by += 0.025) { const r = count(turn, bx, by); rows.push({ turn, bx: +bx.toFixed(3), by: +by.toFixed(3), h: r.h, p: r.p }); }
rows.sort((a, b) => b.h + b.p - (a.h + a.p));
for (const r of rows.slice(0, 25)) console.log(JSON.stringify(r));
console.log('best with the arm pointing at the pipe side (turn 0):'); for (const r of rows.filter((x) => x.turn === 0).slice(0, 5)) console.log(JSON.stringify(r));
console.log('best with turn 180:'); for (const r of rows.filter((x) => x.turn === 180).slice(0, 5)) console.log(JSON.stringify(r));
