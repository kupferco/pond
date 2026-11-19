// Pipe supports on the track (OpenPocket #315, part 1 of plan #295). Pure maths, no MuJoCo or DOM. Mirror of docs/bench-test/track_support_sag.py
// (same numbers, the test compares them) and of cad/track_supports.py (positions).
// Supports use the track-joint rod system: an M8 rod through the +Y (C-gap) side of the pipe into a post or block. The cart passes them only at roll 0.
import { ROLL_HOME_TOL_DEG, MAX_ROLL_DEG, angDiff } from './roll.ts';
import { G } from './track-sag.ts';

export const SUPPORT_X_MM = 125;                 // from the centre bracket, 15 mm before the bend starts (the straight part is 140 mm)
export const BOTTOM_SPAN_MM = 300, TOP_SPAN_MM = 400;   // owner answer Q1 (the bend is a pinned end)
export const BOTTOM_LIMIT_MM = 1, TOP_LIMIT_MM = 3;     // owner answer Q2
export const WALL_MM = 1.8, OD_MM = 32;                 // owner answer Q3
const E_ROD = 200000, D_ROD = 6.5, STUB_MM = 34, LEG_MM = 1466;
const I_PIPE = (Math.PI / 64) * (OD_MM ** 4 - (OD_MM - 2 * WALL_MM) ** 4), A_PIPE = (Math.PI / 4) * (OD_MM ** 2 - (OD_MM - 2 * WALL_MM) ** 2);
export const K_STUB = (3 * E_ROD * (Math.PI / 64) * D_ROD ** 4) / STUB_MM ** 3;   // N/mm, M8 stub as a cantilever
export const LOAD_N = 3 * G * 1.5;
/** Vertical stiffness (N/mm) of the diagonal M8 brace seen at the block. vec = brace vector (dx, dy, dz) in mm. */
export function braceK(vec: [number, number, number]): number {
  const lb = Math.hypot(...vec), s = vec[2] / lb;
  return ((E_ROD * (Math.PI / 4) * D_ROD ** 2) / lb) * s * s;
}
export const BRACE_OWNER: [number, number, number] = [190, 40, 314];
const series = (...k: number[]) => 1 / k.reduce((a, b) => a + 1 / b, 0);

/** Largest deflection (mm) under the cart load swept along the run. Centre clamped at x = 0; far end pinned (endK undefined) or on a spring. */
export function runSag(spanMm: number, eMpa: number, supports: { x: number; k: number }[], endK?: number, h = 2): number {
  const n = Math.round(spanMm / h), EI = eMpa * I_PIPE, N = n + 1;
  const K = Array.from({ length: 2 * N }, () => new Array(2 * N).fill(0));
  const ke = [[12, 6 * h, -12, 6 * h], [6 * h, 4 * h * h, -6 * h, 2 * h * h], [-12, -6 * h, 12, -6 * h], [6 * h, 2 * h * h, -6 * h, 4 * h * h]];
  for (let e = 0; e < n; e++) for (let a = 0; a < 4; a++) for (let b = 0; b < 4; b++) K[2 * e + a][2 * e + b] += (EI / h ** 3) * ke[a][b];
  if (endK !== undefined) K[2 * n][2 * n] += endK;
  for (const s of supports) K[2 * Math.round(s.x / h)][2 * Math.round(s.x / h)] += s.k;
  const free: number[] = [];
  for (let d = 2; d < 2 * N; d++) if (!(endK === undefined && d === 2 * n)) free.push(d);
  const m = free.length, A = free.map((r) => free.map((c) => K[r][c]));
  // invert by Gauss-Jordan (a few hundred unknowns)
  const inv = Array.from({ length: m }, (_, i) => Array.from({ length: m }, (_, j) => (i === j ? 1 : 0)));
  for (let i = 0; i < m; i++) {
    let p = i; for (let r = i + 1; r < m; r++) if (Math.abs(A[r][i]) > Math.abs(A[p][i])) p = r;
    [A[i], A[p]] = [A[p], A[i]]; [inv[i], inv[p]] = [inv[p], inv[i]];
    const d = A[i][i];
    for (let c = 0; c < m; c++) { A[i][c] /= d; inv[i][c] /= d; }
    for (let r = 0; r < m; r++) if (r !== i && A[r][i] !== 0) { const f = A[r][i]; for (let c = 0; c < m; c++) { A[r][c] -= f * A[i][c]; inv[r][c] -= f * inv[i][c]; } }
  }
  let best = 0;
  free.forEach((dof, i) => { if (dof % 2 === 0 && dof > 0 && dof < 2 * n) best = Math.max(best, inv[i][i] * LOAD_N); });
  return best;
}
const E_CREEP = 1000, E_HOT = 600;
export const bottomSag = (eMpa = E_CREEP, withSupport = true) => runSag(BOTTOM_SPAN_MM, eMpa, withSupport ? [{ x: SUPPORT_X_MM, k: K_STUB }] : []);
/** Top run with the brace, bend standing on the leg's axial spring (bottom locked). */
export const topSag = (eMpa = E_CREEP, withBrace = true) =>
  runSag(TOP_SPAN_MM, eMpa, withBrace ? [{ x: TOP_SPAN_MM / 2, k: series(braceK(BRACE_OWNER), K_STUB) }] : [], (eMpa * A_PIPE) / LEG_MM);
export { E_CREEP, E_HOT };

/** The cart may pass a support only with the C-gap facing it: roll within the home tolerance (same interlock as the joint rods). */
export const passesSupport = (rollDeg: number) => Math.abs(angDiff(rollDeg, 0)) <= ROLL_HOME_TOL_DEG;
/** The supports are on the runs only, where the cart is held at roll 0 already (MAX_ROLL_DEG), so the interlock is always met on the way to them. */
export const SUPPORTS_ONLY_WHERE_FLAT = MAX_ROLL_DEG.horizontal === 0;
