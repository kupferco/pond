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

  constructor(mujoco: MainModule) {
    this.mujoco = mujoco;
    this.model = mujoco.MjModel.from_xml_string(MJCF);
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
