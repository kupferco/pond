import type { RobotDriver } from '../commands.ts';

/**
 * Stub. Later: Web Serial to the Waveshare Bus Servo Adapter A (1 Mbaud, Feetech STS protocol,
 * servo IDs 1..6 = motors A..F). For now it only reports that it is not connected.
 */
export class RealDriver implements RobotDriver {
  readonly mode = 'real' as const;
  async connect(): Promise<void> {
    throw new Error('Real arm: not connected yet (Web Serial driver is not written).');
  }
  setJointTarget(): void { throw new Error('Real arm: not connected yet'); }
  home(): void { throw new Error('Real arm: not connected yet'); }
  readJoints() { return null; }
  targets() { return {}; }
}
