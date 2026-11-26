// Pod grab: reach table (OpenPocket #461). For every store lane (front row pick) and every tray cell: the cart stop on its straight run, the sideways reach the pan joint takes, the largest
// shoulder-to-wrist distance of the cycle's waypoints, the joint margin (degrees to the nearest joint limit of the real SO-101 model) and whether the arm reaches at every waypoint
// (above the pod, in the pod, over the lid, over the cell, in the cell). A waypoint that does not reach says how far the arm base would have to be raised for it to.
// Usage: node --experimental-strip-types scripts/check-podgrab-reach.ts
import { probe } from '../src/podgrab/reach.ts';
import { armR, armU, storePos, seatPos, TRAY_SLOTS, slotLabel, STORE_PITCH_DEG, TRANSIT_Z, TRANSIT_PITCH, STORE_ROWS, CART_X_MIN, CART_X_MAX } from '../src/podgrab/layout.ts';

const APPROACH = 0.03;  // as in podgrab/task.ts
interface Wp { name: string; z: number; y: number; pitch: number }
function raiseNeeded(w: Wp, lat: number) {
  for (let r = 0; r <= 200; r++) if (probe(armR(w.z) + r / 1000, armU(w.y), w.pitch, lat).ok) return r;
  return null;
}
const rows: string[] = [];
/** The straight path between the over-the-lid pose and a pod pose (height and tilt interpolated, as the task does), sampled every tenth. */
const path = (z: number, y: number, pitch: number, tp: number): Wp[] => Array.from({ length: 9 }, (_, i) => { const u = (i + 1) / 10; return { name: `path to/from the lid (${(u * 100).toFixed(0)}%)`, z: TRANSIT_Z + (z - TRANSIT_Z) * u, y, pitch: tp + (pitch - tp) * u }; });
function target(label: string, x: number, wps: Wp[]) {
  const cx = Math.min(CART_X_MAX, Math.max(CART_X_MIN, x)), lat = x - cx;
  let dmax = 0, mmin = 999, ok = true; const bad: string[] = []; let raise = 0;
  for (const w of wps) {
    const p = probe(armR(w.z), armU(w.y), w.pitch, lat);
    dmax = Math.max(dmax, p.d); if (p.margin !== -999) mmin = Math.min(mmin, p.margin);
    if (!p.ok) { ok = false; bad.push(w.name); const r = raiseNeeded(w, lat); raise = Math.max(raise, r ?? 999); }
  }
  rows.push(`| ${label} | ${(cx * 1000).toFixed(0)} | ${(lat * 1000).toFixed(0)} | ${(dmax * 1000).toFixed(0)} | ${mmin === 999 ? 'out of range' : mmin.toFixed(1)} | ${ok ? 'yes' : 'NO'} | ${ok ? '' : bad.join('; ') + (raise ? ` (base +${raise >= 999 ? '>200' : raise} mm)` : '')} |`);
  return ok;
}
let all = true, nStore = 0, nTray = 0;
for (let r = 0; r < STORE_ROWS; r++) {
  const T = storePos(r, 0);
  const ok = target(`store lane ${r + 1} (x ${(T[0] * 1000).toFixed(0)})`, T[0], [
    { name: 'in the pod', z: T[2], y: T[1], pitch: STORE_PITCH_DEG },
    { name: 'claw waiting over the pod', z: T[2] + APPROACH, y: T[1], pitch: STORE_PITCH_DEG },
    { name: 'over the lid (claw tilted)', z: TRANSIT_Z, y: T[1], pitch: TRANSIT_PITCH },
    ...path(T[2], T[1], STORE_PITCH_DEG, TRANSIT_PITCH),
  ]);
  all = ok && all; if (ok) nStore++;
}
for (let s = 0; s < TRAY_SLOTS; s++) {
  const S = seatPos(s);
  const ok = target(`tray ${slotLabel(s)} (x ${(S[0] * 1000).toFixed(0)}, y ${(S[1] * 1000).toFixed(0)})`, S[0], [
    { name: 'over the cell (claw tilted)', z: TRANSIT_Z, y: S[1], pitch: TRANSIT_PITCH },
    { name: 'pod seated', z: S[2], y: S[1], pitch: 0 },
    ...path(S[2], S[1], 0, TRANSIT_PITCH),
  ]);
  all = ok && all; if (ok) nTray++;
}
console.log('| target | cart stop x (mm) | pan reach (mm) | max shoulder to wrist (mm) | min joint margin (deg) | reached | failing waypoint |\n|---|---|---|---|---|---|---|\n' + rows.join('\n'));
console.log(`store spots reached: ${nStore}/${STORE_ROWS}; tray cells reached: ${nTray}/${TRAY_SLOTS}`);
console.log(all ? 'every waypoint reached' : 'some waypoints are NOT reached');
