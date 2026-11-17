// Writes a Pose into the MuJoCo model (joint angles, cart height, part placements) and checks it for contacts.
import type { MjData, MjModel, MainModule } from '@mujoco/mujoco';
import { MOTORS } from '../model.ts';
import { BODIES, CART_Z0, TRAY_CAP_TOP, TRAY_Y, XT, YC, quatZ } from './layout.ts';
import { OBJECTS, ikTool, objectPose, type Pose, type Tool } from './task.ts';

const RAD = Math.PI / 180;

export class Binder {
  readonly qpos: Record<string, number> = {};
  readonly mocap: Record<string, number> = {};
  readonly free: Record<string, number> = {};
  /** The last hand pose the arm could reach: where the arm stays, and what an attached part rides with, while a commanded pose is out of reach. */
  private lastTool: Tool | null = null;
  readonly mujoco: MainModule; readonly model: MjModel; readonly data: MjData;
  constructor(mujoco: MainModule, model: MjModel, data: MjData) {
    this.mujoco = mujoco; this.model = model; this.data = data;
    for (const m of MOTORS) { const j = model.jnt(m.joint); this.qpos[m.id] = model.jnt_qposadr[j.id]; }
    this.mocap.cart = model.body_mocapid[model.body('cart').id];
    for (const n of [BODIES.pod, BODIES.plug, ...BODIES.other]) this.free[n] = model.jnt_qposadr[model.body_jntadr[model.body(n).id]];
  }
  private setMocap(name: string, pos: number[], quat: number[]) {
    if (name in this.free) {
      const q = this.free[name];
      for (let k = 0; k < 3; k++) this.data.qpos[q + k] = pos[k];
      for (let k = 0; k < 4; k++) this.data.qpos[q + 3 + k] = quat[k];
      return;
    }
    const i = this.mocap[name];
    for (let k = 0; k < 3; k++) this.data.mocap_pos[3 * i + k] = pos[k];
    for (let k = 0; k < 4; k++) this.data.mocap_quat[4 * i + k] = quat[k];
  }
  /** Pose everything, run forward kinematics. Returns false (and leaves the arm where it was) when the hand pose is out of reach. */
  apply(p: Pose): boolean {
    const j = ikTool(p.tool, p.cartZ);
    if (j) this.lastTool = { ...p.tool };
    else if (this.lastTool) p = { ...p, tool: { ...this.lastTool } };   // out of reach: the arm stays where it was and a part in the hand stays with it (it is not dragged through the cart)
    if (j) for (const m of MOTORS) { if (m.id !== 'F') this.data.qpos[this.qpos[m.id]] = (j[m.id as keyof typeof j] ?? 0) * RAD; }
    this.data.qpos[this.qpos.F] = p.jaw * RAD;
    this.setMocap('cart', [XT, YC, p.cartZ], [1, 0, 0, 0]);
    for (const o of OBJECTS) { const { pos, axis } = objectPose(p, o); this.setMocap(BODIES[o], pos, quatZ(axis)); }
    BODIES.other.forEach((n, i) => this.setMocap(n, [TRAY_CAP_TOP[0], TRAY_Y[i * 2], TRAY_CAP_TOP[2]], quatZ([0, 0, -1])));
    this.mujoco.mj_forward(this.model, this.data);
    return j !== null;
  }
  /** Position of the hand body origin, for checking the IK mapping. */
  handPos(): number[] { const id = this.model.body('hand').id; return [this.data.xpos[3 * id], this.data.xpos[3 * id + 1], this.data.xpos[3 * id + 2]]; }
}

/** The deepest contact (negative = penetrating) and the geoms involved. Contacts within the 1 mm margin but not touching are ignored. */
export function worstContact(model: MjModel, data: MjData): { depth: number; names: string } {
  let depth = 0, g1 = -1, g2 = -1;
  const contacts = data.contact;   // one wrapper for the whole scan (each access of data.contact makes a new one)
  for (let i = 0; i < data.ncon; i++) {
    const c = contacts.get(i);
    if (c && c.dist < depth) { depth = c.dist; g1 = c.geom1; g2 = c.geom2; }
    (c as { delete?: () => void } | undefined)?.delete?.();   // embind wrapper: free it, or thousands of frames fill the wasm heap
  }
  (contacts as { delete?: () => void }).delete?.();
  if (g1 < 0) return { depth: 0, names: '' };
  const nm = (g: number) => { const geom = model.geom(g), name = geom.name; const b = model.body(model.geom_bodyid[g]), bn = b.name; geom.delete?.(); b.delete?.(); return `${bn}${name ? ':' + name : ''}`; };
  return { depth, names: `${nm(g1)} / ${nm(g2)}` };
}

export { CART_Z0 };
