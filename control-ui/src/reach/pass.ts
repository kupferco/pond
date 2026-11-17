// Can the cart pass the spine bracket (and the pipe it is joined to) on the track's top and bottom run, and does rolling the cart about the track pipe's own axis make the difference?
// The cart rides the horizontal run on the loop's inside (its origin 60 mm from the tube towards the loop's middle, the arm base axis pointing -x at the pipe); on the way round the corner its up axis turns to
// point along the run. Rolled by an angle: the whole cart turned about the tube's own axis (the run) by that angle (180 degrees: the plate and the arm on the far side of the tube from the pipe). The cart is driven
// along the straight part of the run in 5 mm steps and every pose is checked for contacts (arm stowed) with the spine bracket, the pipe and the rest of the scene separately.
import type { MainModule, MjData, MjModel } from '@mujoco/mujoco';
import { LOOP_R, LOOP_TX, LOOP_ZB, LOOP_ZT, XT } from '../transplant/layout.ts';
import { Rig } from './test.ts';

type Q = [number, number, number, number];
const mul = (a: Q, b: Q): Q => [a[0] * b[0] - a[1] * b[1] - a[2] * b[2] - a[3] * b[3], a[0] * b[1] + a[1] * b[0] + a[2] * b[3] - a[3] * b[2], a[0] * b[2] - a[1] * b[3] + a[2] * b[0] + a[3] * b[1], a[0] * b[3] + a[1] * b[2] - a[2] * b[1] + a[3] * b[0]];
const rotX = (deg: number): Q => { const h = deg * Math.PI / 360; return [Math.cos(h), Math.sin(h), 0, 0]; };
const rotY = (deg: number): Q => { const h = deg * Math.PI / 360; return [Math.cos(h), 0, Math.sin(h), 0]; };
const YMAX = LOOP_TX - LOOP_R - 0.06;   // the straight part of the run, less the 60 mm the sleeve (half 45 mm long plus wheels) needs before the corner
export interface PassResult { run: 'top' | 'bottom'; roll: number; bracket: boolean; pipe: boolean; other: boolean; worst: number; names: string; bracketWorst: number; bracketNames: string; steps: number }

/** Names of the contacts that penetrate, grouped: the spine bracket, the pipe (and its collars), anything else. */
function hits(model: MjModel, data: MjData) {
  let bracket = 0, pipe = 0, other = 0, worst = 0, names = '', bw = 0, bn = '';
  const contacts = data.contact;
  for (let i = 0; i < data.ncon; i++) {
    const c = contacts.get(i);
    if (c && c.dist < 0) {
      const nm = (g: number) => { const geom = model.geom(g), n = geom.name, b = model.body(model.geom_bodyid[g]), bn = b.name; geom.delete?.(); b.delete?.(); return { g: n, b: bn }; };
      const a = nm(c.geom1), b = nm(c.geom2), all = [a.g, b.g, a.b, b.b].join(' ');
      if (/bracket(top|bot)/.test(all)) bracket++; else if (/pipe|seat|holder|collar|plug|pod/.test(all)) pipe++; else other++;
      const label = `${a.b}${a.g ? ':' + a.g : ''} / ${b.b}${b.g ? ':' + b.g : ''}`;
      if (c.dist < worst) { worst = c.dist; names = label; }
      if (/bracket(top|bot)/.test(all) && c.dist < bw) { bw = c.dist; bn = label; }
    }
    (c as { delete?: () => void } | undefined)?.delete?.();
  }
  (contacts as { delete?: () => void }).delete?.();
  return { bracket, pipe, other, worst, names, bw, bn };
}

export function checkPass(mujoco: MainModule, model: MjModel, data: MjData, rolls = [0, 90, 180, 270]): PassResult[] {
  const rig = new Rig(mujoco, model, data), out: PassResult[] = [];
  for (const run of ['top', 'bottom'] as const) for (const roll of rolls) {
    const zRun = run === 'top' ? LOOP_ZT : LOOP_ZB, inward = run === 'top' ? -1 : 1;   // the loop's middle is below the top run and above the bottom one
    const th = roll * Math.PI / 180, off = inward * 0.06;
    let bracket = false, pipe = false, other = false, worst = 0, names = '', steps = 0, bw = 0, bn = '';
    for (let y = -YMAX; y <= YMAX + 1e-9; y += 0.005) {
      const q = mul(rotY(roll), rotX(run === 'top' ? -90 : 90)), pos: [number, number, number] = [XT + off * Math.sin(th), y, zRun + off * Math.cos(th)];
      rig.place(pos, q, { A: 0, B: 0, C: 0, D: 0, E: 0 }, 0);
      const h = hits(model, data); steps++;
      bracket ||= h.bracket > 0; pipe ||= h.pipe > 0; other ||= h.other > 0;
      if (h.worst < worst) { worst = h.worst; names = h.names; }
      if (h.bw < bw) { bw = h.bw; bn = h.bn; }
    }
    out.push({ run, roll, bracket, pipe, other, worst, names, bracketWorst: bw, bracketNames: bn, steps });
  }
  return out;
}
