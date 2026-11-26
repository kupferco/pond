// Exact clearance of the cart's CAD shapes against the spine, the track bracket and the track pipe (OpenPocket #461).
// MuJoCo's mj_geomDistance on a mesh geom uses its CONVEX HULL, which fills the sleeve's C gap and the jaw cut-outs, so it cannot say whether the bracket really passes through the slot.
// Here the CAD triangles themselves are sampled (every point at most STEP apart) in the cart frame once, and each point is tested against the obstacle solids.
import type { SimDriver } from '../drivers/simDriver.ts';
import { PIPE_R, PIPE_Y, PIPE_Z, COLUMN_R, SPINE_Y, BRACKET_PLATE_Y, BRACKET_HX, BRACKET_HZ, ROD_R, STATION, LID_Z, COLLAR_H } from './layout.ts';

const STEP = 0.0025;                        // m: sample spacing on the CAD surfaces
export type Obstacle = 'spine' | 'bracket' | 'rod' | 'pipe' | 'station' | 'lid';
export interface Cloud { pts: Float32Array; part: string[]; owner: Uint32Array }   // world points with the cart at x = 0, the geom name of each

/** Surface samples (world frame, cart at x = 0) of every CAD mesh geom under the body `cart`, except those under the body `base` (the arm). */
export function cartCloud(sim: SimDriver, minY = -Infinity): Cloud {
  const m = sim.model, d = sim.data;
  const cb = m.body('cart'), ab = m.body('base'), cartId = cb.id, armId = ab.id; cb.delete(); ab.delete();
  const under = (b: number, id: number) => { for (; b > 0; b = m.body_parentid[b]) if (b === id) return true; return false; };
  const out: number[] = [], owner: number[] = [], names: string[] = [];
  const cx = d.xpos[3 * cartId];   // the cart body, from the same kinematics pass as the geom poses
  for (let g = 0; g < m.ngeom; g++) {
    if (m.geom_type[g] !== 7 || !under(m.geom_bodyid[g], cartId) || under(m.geom_bodyid[g], armId)) continue;
    const mi = m.geom_dataid[g], va = m.mesh_vertadr[mi], fa = m.mesh_faceadr[mi], fn = m.mesh_facenum[mi];
    const P = [0, 1, 2].map((k) => d.geom_xpos[3 * g + k]), R = Array.from({ length: 9 }, (_, k) => d.geom_xmat[9 * g + k]);
    const w = (i: number): [number, number, number] => {
      const v = [0, 1, 2].map((k) => m.mesh_vert[3 * (va + i) + k]);
      return [0, 1, 2].map((r) => P[r] + R[3 * r] * v[0] + R[3 * r + 1] * v[1] + R[3 * r + 2] * v[2]) as [number, number, number];
    };
    names.push(String(g));
    for (let t = 0; t < fn; t++) {
      const A = w(m.mesh_face[3 * (fa + t)]), B = w(m.mesh_face[3 * (fa + t) + 1]), C = w(m.mesh_face[3 * (fa + t) + 2]);
      const e = Math.max(dist(A, B), dist(B, C), dist(C, A)), n = Math.max(1, Math.ceil(e / STEP));
      for (let i = 0; i <= n; i++) for (let j = 0; j <= n - i; j++) {
        const u = i / n, v = j / n, q = 1 - u - v;
        const py = q * A[1] + u * B[1] + v * C[1];
        if (py < minY) continue;
        out.push(q * A[0] + u * B[0] + v * C[0] - cx, q * A[1] + u * B[1] + v * C[1] - 0, q * A[2] + u * B[2] + v * C[2]);
        owner.push(names.length - 1);
      }
    }
  }
  return { pts: Float32Array.from(out), part: names, owner: Uint32Array.from(owner) };
}
const dist = (a: number[], b: number[]) => Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);

/** Penetration depth (m, > 0 inside) of a world point into one obstacle solid (the solids of spineGeoms() in layout.ts). */
export function depthIn(o: Obstacle, px: number, py: number, pz: number): number {
  if (o === 'spine') return COLUMN_R - Math.hypot(px, py - SPINE_Y);
  if (o === 'station') return Math.min(px - STATION.x0, STATION.x1 - px, py - STATION.y0, STATION.y1 - py, pz - STATION.z0, STATION.z1 - pz);   // the water testing station block (its four legs lie inside the same footprint below it)
  if (o === 'lid') return LID_Z + COLLAR_H - pz;   // the lid top with its silicone collars
  if (o === 'pipe') return PIPE_R - Math.hypot(py - PIPE_Y, pz - PIPE_Z);
  if (o === 'rod') return Math.min(ROD_R - Math.hypot(px, pz - PIPE_Z), py - (PIPE_Y + PIPE_R), BRACKET_PLATE_Y - py);
  return Math.min(BRACKET_HX - Math.abs(px), BRACKET_HZ - Math.abs(pz - PIPE_Z), py - BRACKET_PLATE_Y, SPINE_Y - COLUMN_R - 0.001 - py);   // the bracket plate
}

export interface Clash { obstacle: Obstacle; depth: number; part: string; x: number }
const OBS: Obstacle[] = ['spine', 'bracket', 'rod'];
/** Deepest penetration of the cart's CAD shapes into each obstacle with the cart centre at x along the track (pipe: x independent, pass 'pipe' in `obs`). Depths below `tol` are ignored (a wheel touching the pipe). */
export function clashesAt(c: Cloud, x: number, obs: Obstacle[] = OBS, tol = 0.0005): Clash[] {
  const worst = new Map<Obstacle, { depth: number; own: number }>();
  const p = c.pts;
  for (let i = 0; i < p.length; i += 3) {
    const px = p[i] + x, py = p[i + 1], pz = p[i + 2];
    for (const o of obs) {
      const dp = depthIn(o, px, py, pz);
      if (dp > tol && dp > (worst.get(o)?.depth ?? 0)) worst.set(o, { depth: dp, own: c.owner[i / 3] });
    }
  }
  return [...worst].map(([obstacle, w]) => ({ obstacle, depth: w.depth, part: c.part[w.own], x }));
}
