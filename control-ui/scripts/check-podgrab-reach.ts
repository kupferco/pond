// Pod grab: reach table (OpenPocket #461). For the store pick and for every tray cell: the shoulder-to-wrist distance, the joint margin (degrees to the nearest joint limit)
// and whether the arm reaches, at every waypoint the pick-and-place cycle uses (above the pod, in the pod, over the lid, over the socket, in the socket).
// A waypoint that does not reach says how far the cart (track) would have to be raised for it to (the smallest fix that does not move the arm).
// Usage: node --experimental-strip-types scripts/check-podgrab-reach.ts
import { probe } from '../src/podgrab/reach.ts';
import { armR, armU, storePos, seatPos, TRAY_SLOTS, slotLabel, STORE_N, STORE_PITCH_DEG, TRANSIT_Z } from '../src/podgrab/layout.ts';

const APPROACH = 0.1;   // as in podgrab/task.ts
/** Smallest raise (mm) of the arm base over the unit, in 1 mm steps, with which the waypoint reaches; null if none up to 200 mm. */
function raiseNeeded(zw: number, yw: number, pitch: number) {
  for (let r = 0; r <= 200; r++) if (probe(armR(zw) + r / 1000, armU(yw), pitch).ok) return r;
  return null;
}
interface Wp { name: string; z: number; y: number; pitch: number }
const rows: string[] = [];
const show = (label: string, w: Wp) => {
  const p = probe(armR(w.z), armU(w.y), w.pitch), r = p.ok ? 0 : raiseNeeded(w.z, w.y, w.pitch);
  rows.push(`| ${label} | ${w.name} | ${(p.d * 1000).toFixed(0)} | ${p.margin === -999 ? 'out of range' : p.margin.toFixed(1)} | ${p.ok ? 'yes' : 'NO'} | ${p.ok ? '' : r === null ? 'more than 200' : '+' + r} |`);
  return p.ok;
};
const T = storePos(0, 0);
const A: [number, number, number] = [T[0], T[1] + APPROACH * STORE_N[1], T[2] + APPROACH * STORE_N[2]];
let all = true;
for (const w of [
  { name: 'in the pod (claw round it)', z: T[2], y: T[1], pitch: STORE_PITCH_DEG },
  { name: 'pod lifted clear of the store', z: A[2], y: A[1], pitch: STORE_PITCH_DEG },
  { name: 'over the lid (transit height)', z: TRANSIT_Z, y: A[1], pitch: 0 },
]) all = show('store pick (rows 1-6, same for every row)', w) && all;
for (let s = 0; s < TRAY_SLOTS; s++) {
  const S = seatPos(s);
  for (const w of [
    { name: 'over the socket (transit height)', z: TRANSIT_Z, y: S[1], pitch: 0 },
    { name: 'pod seated in the collar', z: S[2], y: S[1], pitch: 0 },
  ]) all = show(`tray ${slotLabel(s)}`, w) && all;
}
console.log('| target | waypoint | shoulder to wrist (mm) | joint margin (deg) | reached | track raise that fixes it (mm) |\n|---|---|---|---|---|---|\n' + rows.join('\n'));
console.log(all ? 'every waypoint reached' : 'some waypoints are NOT reached');
