// One command layer, two drivers. Later commands (cart moves, "pick pod B5 -> F4") are added to
// RobotDriver and built from these primitives, so the UI never talks to MuJoCo or the serial port.
import { MOTORS, type MotorSpec } from './model.ts';
import { POSES, type PoseName } from './sample/layout.ts';

export type Mode = 'sim' | 'real';

export interface RobotDriver {
  readonly mode: Mode;
  /** Resolves when ready; rejects with a user-readable message if it cannot be used. */
  connect(): Promise<void>;
  setJointTarget(motorId: string, degrees: number): void;
  home(): void;
  /** Current joint angles in degrees by motor id, or null when unavailable. */
  readJoints(): Record<string, number> | null;
  /** Latest targets in degrees by motor id. */
  targets(): Record<string, number>;
  /** Run the sampling pump by this many rotor turns: positive draws (nozzle to tube), negative runs in reverse (tube to nozzle). */
  pump(turns: number): void;
  /** Net rotor turns since start (positive = drawn in): what the pump has been told to do. */
  pumpTurns(): number;
}

export function motorById(id: string): MotorSpec {
  const m = MOTORS.find((x) => x.id === id);
  if (!m) throw new Error(`Unknown motor ${id}`);
  return m;
}

export function clampDegrees(motorId: string, degrees: number): number {
  const m = motorById(motorId);
  return Math.min(m.max, Math.max(m.min, degrees));
}

export class CommandLayer {
  private drivers: Record<Mode, RobotDriver>;
  private current: Mode = 'sim';
  constructor(sim: RobotDriver, real: RobotDriver) {
    this.drivers = { sim, real };
  }
  get mode(): Mode { return this.current; }
  get driver(): RobotDriver { return this.drivers[this.current]; }
  /** Switch driver. Throws (and stays on the old one) if the new one cannot connect. */
  async setMode(mode: Mode): Promise<void> {
    if (mode === this.current) return;
    await this.drivers[mode].connect();
    this.current = mode;
  }
  setJointTarget(motorId: string, degrees: number): number {
    const d = clampDegrees(motorId, degrees);
    this.driver.setJointTarget(motorId, d);
    return d;
  }
  setAllTargets(pose: Record<string, number>): void {
    for (const [id, deg] of Object.entries(pose)) this.setJointTarget(id, deg);
  }
  home(): void { this.driver.home(); }
  /** Move the arm to a named pose of the sampling job (joints A to E; the gripper is separate). */
  pose(name: PoseName): void { this.setAllTargets(POSES[name]); }
  /** Gripper open (true) or closed on the nozzle collar (false). */
  gripper(open: boolean, openDeg: number, holdDeg: number): void { this.setJointTarget('F', open ? openDeg : holdDeg); }
  pump(turns: number): void { this.driver.pump(turns); }
  readJoints() { return this.driver.readJoints(); }
}
