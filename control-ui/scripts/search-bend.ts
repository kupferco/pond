// Searches the bend trim rows (BEND_ROWS in src/cart/transfer.ts) for a trip round the bend with the plate rotated and the free hand off (Pond #227).
// Greedy along the track: at every 0.25 cm step keep the previous trim if it is contact free, else the nearest contact-free trim within a small box around it.
// Run: node --experimental-strip-types scripts/search-bend.ts [1|2] [from_cm] [to_cm]   (static hand; 1 = trip up pipe C)
import loadMujoco from '@mujoco/mujoco';
import { transferMjcf } from '../src/cart/transfer-model.ts';
import { applyPose, initialState, worstContact, type BendTrim, CLEAR_DEG } from '../src/cart/transfer.ts';

const mj = await loadMujoco();
const round2 = (v: number) => Math.round(v * 100) / 100;
const stat = (Number(process.argv[2]) || 1) as 1 | 2, free = 3 - stat as 1 | 2;
const from = Number(process.argv[3]) || 48, to = Number(process.argv[4]) || 90;
const m = mj.MjModel.from_xml_string(transferMjcf()), d = new mj.MjData(m);
const gname = [...Array(m.ngeom).keys()].map((i) => { const g = m.geom(i), n = g.name; (g as any).delete?.(); return n; });
const DEG = Math.PI / 180;
type P = [number, number, number, number, number, number];   // dx mm, dy mm, yaw deg, eps deg, da deg, dh deg
const toTrim = (p: P): BendTrim => ({ dx: p[0], dy: p[1], yaw: p[2] * DEG, eps: p[3] * DEG, da: p[4] * DEG, dh: p[5] * DEG });
for (let i = 0; i < m.ngeom; i++) m.geom_margin[i] = 0.0002;   // contacts are reported within 0.4 mm (2 x 0.2), so the search can demand a clearance
const CLEAR = 0.00005;   // required clearance (m) on the bend
const depth = (s: number, p: P, t = 1) => { const st = initialState(); st.s = s; st.t = t; st.open1 = free === 1 ? 1 : 0; st.open2 = free === 2 ? 1 : 0; applyPose(m, d, st, toTrim(p)); mj.mj_forward(m, d); return nearest(); };
const nearest = (): { depth: number; names: string } => {   // smallest contact distance (negative = penetrating), minus the clearance we require
  let dmin = 1, a = -1, b = -1; const con = d.contact;
  for (let i = 0; i < d.ncon; i++) { const c = con.get(i)!; if (c.dist < dmin) { dmin = c.dist; a = c.geom1; b = c.geom2; } (c as any).delete?.(); }
  (con as any).delete?.();
  return { depth: dmin === 1 ? 1 : dmin - CLEAR, names: a < 0 ? '' : gname[a] + ' / ' + gname[b] }; };
const STEP = [0.5, 0.5, 0.5, 0.5, 1, 1], LIM = [8, 8, 8, 12, 8, 15];
let rng = 12345; const rnd = () => ((rng = (rng * 1664525 + 1013904223) >>> 0) / 4294967296);
let p: P = [0, 0, 0, 0, 0, 0];
const rows: [number, ...P][] = [];
let stuck = -1;
const FLAT = 75, UNWIND_END = 86;   // from FLAT on the plate is flat again (da = dh = 0); every trim is back to 0 by UNWIND_END
let base: P | null = null;   // the trim at 68 cm: da and dh ramp down to 0 from there to FLAT (the plate turns flat at FLAT, where the extras of the rotated pose must already be 0)
const pinned = (s: number, q: P): P => {
  q = [q[0], q[1], q[2], Math.max(0, q[3]), q[4], q[5]];   // the static jaw can only crack OPEN (eps >= 0)
  if (s >= FLAT) return [q[0], q[1], q[2], q[3], 0, 0];
  if (s > 68 && base) { const f = (FLAT - s) / (FLAT - 68); return [q[0], q[1], q[2], q[3], Math.min(q[4], Math.max(0, base[4]) * f), Math.min(q[5], Math.max(0, base[5]) * f)]; }
  return q; };
const ok = (s: number, q: P) => depth(s, q).depth >= -1e-9;
for (let s = from; s <= to + 1e-9; s += 0.1) {
  if (s >= 68 && !base) base = [...p] as P;
  // pull towards zero where allowed (late in the bend), as far as one box step: the least trim that is contact free
  const pull = (q: P): P => q.map((v, i) => (s >= 70 ? v - Math.sign(v) * Math.min(Math.abs(v), STEP[i]) : v)) as P;
  let cand = pinned(s, pull(p));
  if (s >= UNWIND_END) cand = [0, 0, 0, 0, 0, 0];
  if (ok(s, cand)) { p = cand; rows.push([s, ...p]); continue; }
  if (ok(s, pinned(s, p))) { p = pinned(s, p); rows.push([s, ...p]); continue; }
  let best: P | null = null, bestCost = 1e9;
  for (let it = 0; it < 6000; it++) {
    const r = 1 + Math.floor(it / 1000);   // widen the box slowly
    const q = pinned(s, p.map((v, i) => Math.max(-LIM[i], Math.min(LIM[i], v + (rnd() * 2 - 1) * STEP[i] * r * (rnd() < 0.5 ? 1 : 0.2)))) as P);
    q.forEach((v, i) => { q[i] = round2(v); });
    if (!ok(s, q)) continue;
    const cost = q.reduce((a, v, i) => a + ((v - p[i]) / STEP[i]) ** 2 + (s >= 70 ? 0.2 * (v / STEP[i]) ** 2 : 0), 0);
    if (cost < bestCost) { bestCost = cost; best = q; }
    if (it > 1000 && best) break;
  }
  if (!best) { const w = depth(s, p); console.log(`STUCK at ${s} cm, worst ${w.depth * 1000} mm ${w.names}, trim ${JSON.stringify(p)}`); stuck = s; break; }
  p = best; rows.push([s, ...p]);
}
console.log(stuck < 0 ? 'found a contact-free trim all the way' : 'stopped');
// thin: keep the fewest rows such that linear interpolation (as bendTrim does) stays contact free every 0.1 cm
const interp = (a: [number, ...P], b: [number, ...P], s: number): P => { const f = (s - a[0]) / (b[0] - a[0]); return a.slice(1).map((v, k) => v + f * ((b as number[])[k + 1] - v)) as P; };
const kept: typeof rows = [rows[0]]; let i = 0;
while (i < rows.length - 1) {
  let j = rows.length - 1; const mand = rows.findIndex((r) => Math.abs(r[0] - FLAT) < 1e-9); if (mand > i) j = mand;
  for (; j > i + 1; j--) { let good = true; for (let s = rows[i][0]; s <= rows[j][0] + 1e-9 && good; s += 0.01) good = ok(s, interp(rows[i], rows[j], s)); if (good) break; }
  kept.push(rows[j]); i = j;
}
for (const r of kept) console.log(`  [${+r[0].toFixed(2)}, ${r.slice(1).map((v) => +v.toFixed(2)).join(', ')}],`);
