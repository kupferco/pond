// Searches the (plate angle, free hand's own hinge angle) plane of the transfer model with contact detection, for the trip up pipe C (hand B released, plate on hinge C)
// or up pipe B (hand C released, plate on hinge B), and prints the corridor and a path through its middle (Pond #227).
// Run: node --experimental-strip-types scripts/search-swing.ts [1|2]   (static hand: 1 = trip up pipe C, 2 = trip up pipe B)
import loadMujoco from '@mujoco/mujoco';
import { transferMjcf } from '../src/cart/transfer-model.ts';
import { applyPose, initialState, kinFromAngles, worstContact } from '../src/cart/transfer.ts';

const mj = await loadMujoco();
const stat = (Number(process.argv[2]) || 1) as 1 | 2, free = 3 - stat as 1 | 2;
const pipe = free === 2 ? 'pipeBv' : 'pipeCv';
const xml = transferMjcf().replace('<contact>', `<contact><pair geom1="env${free}" geom2="${pipe}" margin="0"/>`);
const m = mj.MjModel.from_xml_string(xml), d = new mj.MjData(m);
const gname = [...Array(m.ngeom).keys()].map((i) => { const g = m.geom(i), n = g.name; (g as any).delete?.(); return n; });
const D2R = Math.PI / 180, A = 0.5, NA = 100, NH = 121;
const eval1 = (a: number, h: number, s: number) => {
  const st = initialState(); st.s = s; st.open1 = stat === 2 ? 1 : 0; st.open2 = stat === 1 ? 1 : 0;
  applyPose(m, d, st, undefined, kinFromAngles(stat, a * D2R, h * D2R)); mj.mj_forward(m, d);
  let envIn = false, other = 0;
  const con = d.contact;
  for (let i = 0; i < d.ncon; i++) { const c = con.get(i)!; const names = [gname[c.geom1], gname[c.geom2]].sort().join(); if (c.dist < -1e-4 || (c.dist < 0 && names.startsWith('env'))) { if (names === [`env${free}`, pipe].sort().join()) envIn = true; else other++; } (c as any).delete?.(); }
  (con as any).delete?.();
  // contacts with the env pair count as "still round the pipe"; everything else must be < 0.1 mm deep
  return { free: other === 0, off: !envIn };
};
const S = [15, 30, 50];
const cell = (i: number, j: number) => { const a = i * A, h = j * A - 30; const r = S.map((s) => eval1(a, h, s)); return { free: r.every((x) => x.free), off: r.every((x) => x.off) }; };
const grid: { free: boolean; off: boolean }[][] = [];
for (let i = 0; i < NA; i++) { grid.push([]); for (let j = 0; j < NH; j++) grid[i].push(cell(i, j)); }
// flood fill from rest (0, 0 deg)
const j0 = 60, seen = new Set<string>([`0,${j0}`]), q: [number, number][] = [[0, j0]], par = new Map<string, string>();
while (q.length) { const [i, j] = q.shift()!; for (const [di, dj] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) { const ni = i + di, nj = j + dj; const k = `${ni},${nj}`; if (ni < 0 || ni >= NA || nj < 0 || nj >= NH || seen.has(k) || !grid[ni][nj].free) continue; seen.add(k); par.set(k, `${i},${j}`); q.push([ni, nj]); } }
let best: [number, number] | null = null;
for (const k of seen) { const [i, j] = k.split(',').map(Number); if (grid[i][j].off && (!best || i < best[0])) best = [i, j]; }
console.log(`static hand ${stat}: reachable cells ${seen.size}; smallest plate angle with the free sleeve off ${pipe}: ${best ? best[0] * A + ' deg (hinge ' + (best[1] * A - 30) + ')' : 'none'}`);
// corridor per plate angle: min/max own hinge among reachable cells
for (let i = 0; i < NA; i += 2) { const js = [...seen].map((k) => k.split(',').map(Number)).filter(([ii]) => ii === i).map(([, j]) => j * A - 30); if (js.length) console.log(`  alpha ${(i * A).toFixed(1)}: hinge ${Math.min(...js)}..${Math.max(...js)}${(() => { const o = grid[i].map((c, j) => (c.off && seen.has(`${i},${j}`) ? j * A - 30 : null)).filter((v) => v !== null) as number[]; return o.length ? `  off at hinge ${Math.min(...o)}..${Math.max(...o)}` : ''; })()}`); }
// path: from rest to the nearest "off" cell with the greatest clearance from non-free cells, by Dijkstra with a cost that grows near obstacles
if (best) {
  const clr = (i: number, j: number) => { let r = 0; for (; r < 12; r++) { for (let di = -r; di <= r; di++) for (let dj = -r; dj <= r; dj++) { const a = i + di, b = j + dj; if (Math.max(Math.abs(di), Math.abs(dj)) === r && (a < 0 || a >= NA || b < 0 || b >= NH || !grid[a][b].free)) return r; } } return r; };
  const cost = (i: number, j: number) => 1 + 30 / (1 + clr(i, j));
  const dist = new Map<string, number>([[`0,${j0}`, 0]]), prev = new Map<string, string>(), pq: [number, string][] = [[0, `0,${j0}`]];
  while (pq.length) { pq.sort((x, y) => x[0] - y[0]); const [dd, k] = pq.shift()!; if (dd > (dist.get(k) ?? 1e9)) continue; const [i, j] = k.split(',').map(Number);
    for (const [di, dj] of [[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [1, -1]]) { const ni = i + di, nj = j + dj, nk = `${ni},${nj}`; if (!seen.has(nk)) continue; const nd = dd + cost(ni, nj) * Math.hypot(di, dj); if (nd < (dist.get(nk) ?? 1e9)) { dist.set(nk, nd); prev.set(nk, k); pq.push([nd, nk]); } } }
  // end: smallest alpha cell with off, then a little margin of clearance
  const ends = [...seen].map((k) => k.split(',').map(Number) as [number, number]).filter(([i, j]) => grid[i][j].off && i === best![0]);
  const end = ends.sort((x, y) => clr(y[0], y[1]) - clr(x[0], x[1]))[0];
  const path: [number, number][] = []; for (let k: string | undefined = `${end[0]},${end[1]}`; k; k = prev.get(k)) { const [i, j] = k.split(',').map(Number); path.unshift([i * A, j * A - 30]); }
  // thin the path: keep points where the direction changes
  const thin = path.filter((p, n) => n === 0 || n === path.length - 1 || (path[n + 1][0] - p[0]) * (p[1] - path[n - 1][1]) !== (path[n + 1][1] - p[1]) * (p[0] - path[n - 1][0]));
  console.log('path (plate deg, own hinge deg):', JSON.stringify(thin));
}
