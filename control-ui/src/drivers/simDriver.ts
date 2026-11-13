import type { MainModule, MjModel, MjData } from '@mujoco/mujoco';
import type { RobotDriver } from '../commands.ts';
import { MJCF, MOTORS } from '../model.ts';

const RAD = Math.PI / 180;
const DEG = 180 / Math.PI;

export class SimDriver implements RobotDriver {
  readonly mode = 'sim' as const;
  readonly mujoco: MainModule;
  readonly model: MjModel;
  readonly data: MjData;
  private qposAdr: Record<string, number> = {};
  private ctrlIdx: Record<string, number> = {};
  private acc = 0;

  constructor(mujoco: MainModule, mjcf: string = MJCF) {
    this.mujoco = mujoco;
    this.model = mujoco.MjModel.from_xml_string(mjcf);
    this.data = new mujoco.MjData(this.model);
    for (const m of MOTORS) {
      this.qposAdr[m.id] = this.model.jnt_qposadr[this.model.jnt(m.joint).id];
      this.ctrlIdx[m.id] = this.model.actuator(m.joint).id;
    }
    this.home();
    mujoco.mj_forward(this.model, this.data);
  }

  async connect(): Promise<void> {}

  setJointTarget(motorId: string, degrees: number): void {
    this.data.ctrl[this.ctrlIdx[motorId]] = degrees * RAD;
  }
  home(): void {
    for (const m of MOTORS) this.setJointTarget(m.id, m.home);
  }
  readJoints(): Record<string, number> {
    const out: Record<string, number> = {};
    for (const m of MOTORS) out[m.id] = this.data.qpos[this.qposAdr[m.id]] * DEG;
    return out;
  }
  targets(): Record<string, number> {
    const out: Record<string, number> = {};
    for (const m of MOTORS) out[m.id] = this.data.ctrl[this.ctrlIdx[m.id]] * DEG;
    return out;
  }

  /** Back to the initial state (arm home, mocap bodies at their model positions). */
  reset(): void {
    this.mujoco.mj_resetData(this.model, this.data);
    this.home();
    this.mujoco.mj_forward(this.model, this.data);
    this.acc = 0;
  }

  /** One physics step of exactly model.opt.timestep seconds (no wall-clock involved). */
  step(): void { this.mujoco.mj_step(this.model, this.data); }

  /** World position and row-major 3x3 rotation of a body, copied out of the sim. */
  bodyPose(name: string): { pos: number[]; rot: number[] } {
    const id = this.model.body(name).id;
    const x = this.data.xpos, r = this.data.xmat;
    return { pos: [x[3 * id], x[3 * id + 1], x[3 * id + 2]], rot: Array.from({ length: 9 }, (_, k) => r[9 * id + k]) };
  }

  /** Place a mocap body (position metres, quaternion w x y z). */
  setMocap(name: string, pos: number[], quat: number[] = [1, 0, 0, 0]): void {
    const i = this.model.body_mocapid[this.model.body(name).id];
    for (let k = 0; k < 3; k++) this.data.mocap_pos[3 * i + k] = pos[k];
    for (let k = 0; k < 4; k++) this.data.mocap_quat[4 * i + k] = quat[k];
  }

  /** Place a free-joint body and give it a world-frame linear velocity (zero spin). For a body the scene carries by hand. */
  setFreeBody(name: string, pos: number[], quat: number[], vel: number[] = [0, 0, 0]): void {
    const jid = this.model.body_jntadr[this.model.body(name).id];
    const q = this.model.jnt_qposadr[jid], v = this.model.jnt_dofadr[jid];
    for (let k = 0; k < 3; k++) { this.data.qpos[q + k] = pos[k]; this.data.qvel[v + k] = vel[k]; this.data.qvel[v + 3 + k] = 0; }
    for (let k = 0; k < 4; k++) this.data.qpos[q + 3 + k] = quat[k];
  }

  dispose(): void {
    this.data.delete();
    this.model.delete();
  }

  /** Advance the sim by wall-clock dt seconds (real time), capped so a stalled tab does not spiral. */
  advance(dt: number): void {
    this.acc += Math.min(dt, 0.1);
    const h = this.model.opt.timestep;
    while (this.acc >= h) {
      this.mujoco.mj_step(this.model, this.data);
      this.acc -= h;
    }
  }
}
