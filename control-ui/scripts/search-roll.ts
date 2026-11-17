// Cart on track (OpenPocket #282): bend clearance of the rigid sleeve and the roll corridors, by MuJoCo contact.
// 1. Bend: at every cm through the bend the best trim (dx across, yaw) of the rigid cart on the R150 pipe, and the clearance it leaves (negative = the sleeve hits the pipe).
// 2. Roll: with the cart flat on the leg, roll both ways (+ and -) in 5 degree steps to +/-180 and list the angles where the free hand or the base touches the track (Q3).
// Run: node --experimental-strip-types scripts/search-roll.ts
import loadMujoco from '@mujoco/mujoco';
import { omniTrackMjcf, placeOmniCart, trackContacts, type BendTrim } from '../src/cart/omni-track.ts';
import { L_ARC, L_VERT } from '../src/cart/track.ts';

const mj = await loadMujoco();
const m = mj.MjModel.from_xml_string(omniTrackMjcf()), d = new mj.MjData(m);
for (let i = 0; i < m.ngeom; i++) m.geom_margin[i] = 0.0002;
/** deepest penetration (m, negative) per part of the cart touching the track */
const contacts = (s: number, roll: number, trim: BendTrim) => {
  placeOmniCart(m as any, d as any, s, (roll * Math.PI) / 180, trim); mj.mj_forward(m, d);
  return trackContacts(m as any, d as any);
};
const worst = (o: Record<string, number>) => Math.min(0, ...Object.values(o));

console.log('--- bend: best trim of the rigid cart at roll 0 (clearance in mm, < 0 = hits the pipe)');
const bend0 = L_VERT, bend1 = L_VERT + L_ARC;
const rows: string[] = [];
let worstBend = 0;
for (let s = bend0 - 6; s <= bend1 + 6 + 1e-9; s += 1) {
  let best = -9, bt: BendTrim = { dx: 0, dy: 0, yaw: 0 };
  for (let dx = -14; dx <= 14; dx += 0.5) for (let yaw = -6; yaw <= 6; yaw += 0.5) { const w = worst(contacts(s, 0, { dx, dy: 0, yaw })); if (w > best) { best = w; bt = { dx, dy: 0, yaw }; } }
  worstBend = Math.min(worstBend, best);
  rows.push(`  [${s.toFixed(0)}, ${bt.dx}, ${bt.yaw}],   // ${(best * 1000).toFixed(2)} mm`);
}
console.log(rows.join('\n'));
console.log(`worst clearance through the bend with the best trim: ${(worstBend * 1000).toFixed(2)} mm`);

console.log('--- roll on the leg (s = 30 cm, straight): free hand and base against the track, both directions');
for (const dir of [1, -1]) {
  const bad: number[] = [];
  for (let a = 0; a <= 180; a += 5) { const o = contacts(30, dir * a, { dx: 0, dy: 0, yaw: 0 }); if (worst(o) < -1e-9) bad.push(dir * a); }
  console.log(dir > 0 ? '+ (plate out of the plane, one way)' : '- (the other way)', bad.length ? 'touches at ' + bad.join(' ') : 'clear from 0 to 180');
}

console.log('--- roll held through the bend (Q7): free hand + base against the track, per roll angle, trim = best at roll 0 for that s (rows above)');
const bestTrim = (s: number): BendTrim => {
  let best = -9, bt: BendTrim = { dx: 0, dy: 0, yaw: 0 };
  for (let dx = -14; dx <= 14; dx += 1) for (let yaw = -6; yaw <= 6; yaw += 1) { const w = worst(contacts(s, 0, { dx, dy: 0, yaw })); if (w > best) { best = w; bt = { dx, dy: 0, yaw }; } }
  return bt;
};
for (const dir of [1, -1]) {
  const clearAngles = new Set<number>(); const all: number[] = [];
  for (let a = 0; a <= 180; a += 15) all.push(a), clearAngles.add(a);
  for (let s = bend0 - 4; s <= bend1 + 4 + 1e-9; s += 2) {
    const t = bestTrim(s);
    for (const a of all) { const o = contacts(s, dir * a, t); if ((o.freehand ?? 0) < -1e-9 || (o.base ?? 0) < -1e-9) clearAngles.delete(a); }
  }
  console.log(dir > 0 ? '+' : '-', 'roll angles (deg) at which the free hand and the base clear the bend at every 2 cm:', [...clearAngles].map((a) => dir * a).join(' ') || 'none');
}
