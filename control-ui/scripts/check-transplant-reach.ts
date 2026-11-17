// Reach check for the Transplant scene: for every place the hand has to go to (tray, cart holder, hole's seat, plug holder) at the cart's three stops, prints whether the SO-101 can point its hand
// along the part's axis (the hand can only point along a plane through the arm's base axis: "plane error"), the joint angles and their margin to the limits. Usage: node --experimental-strip-types scripts/check-transplant-reach.ts
import { CART_Z0, CART_Z1, CART_ZP, PSI } from '../src/transplant/layout.ts';
import { ikTool, toolOf, placePose, type Place } from '../src/transplant/task.ts';

const lim: Record<string, [number, number]> = { A: [-110, 110], B: [-100, 100], C: [-97, 97], D: [-95, 95] };
const row = (place: Exclude<Place, 'hand'>, z: number, out = 0) => {
  const p = placePose(place, z), o: [number, number, number] = [p.pos[0] - p.axis[0] * out, p.pos[1] - p.axis[1] * out, p.pos[2] - p.axis[2] * out];
  const t = toolOf(p.pos, p.axis, z), j = ikTool(t, z);
  let margin = 0;
  if (j) margin = Math.min(...(['A', 'B', 'C', 'D'] as const).map((k) => Math.min(j[k] - lim[k][0], lim[k][1] - j[k])));
  console.log(`${place.padEnd(5)} cart ${z.toFixed(3)}  plane error ${t.err.toFixed(2)} deg  ${j ? `joints A ${j.A.toFixed(0)} B ${j.B.toFixed(0)} C ${j.C.toFixed(0)} D ${j.D.toFixed(0)}, margin ${margin.toFixed(0)} deg` : 'OUT OF REACH'}`);
};
console.log(`collar azimuth ${(PSI * 180 / Math.PI).toFixed(0)} deg`);
for (const z of [CART_Z0, CART_Z1, CART_ZP]) { console.log('--'); for (const pl of ['tray', 'cup', 'seat', 'park'] as const) row(pl, z); }
