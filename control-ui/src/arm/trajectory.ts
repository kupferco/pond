// Trajectory file for one run: columnar JSON, gzip-compressed. Pure functions, no Firebase.
import { PHASE_NAMES, type Attempt } from './attempt.ts';
import { CONTROLLER_VERSION, SCENE_VERSION, SLOT_SEAT_Z } from './dims.ts';
import { MOTORS } from '../model.ts';

export interface RunMeta { runId: string; batchId: string; batchIndex: number; batchSize: number; startedAt: string }

export function trajectoryJson(a: Attempt, meta: RunMeta) {
  const s = a.samples;
  return {
    format: 'pond-arm-trajectory-v1',
    ...meta,
    sceneVersion: SCENE_VERSION,
    controllerVersion: CONTROLLER_VERSION,
    seed: a.cfg.seed,
    perceptionNoiseMm: a.cfg.noiseMm ?? 1.2,
    result: a.result,
    units: { t: 's', q: 'deg', cmd: 'deg', pod: 'm, quaternion w x y z', slot: 'm, deg' },
    joints: MOTORS.map((m) => m.id),
    phases: PHASE_NAMES,
    // The slot never moves during a run, so its pose is stored once: x, y, seat height of a pod, yaw.
    slot: [a.cfg.slot[0], a.cfg.slot[1], SLOT_SEAT_Z, 0],
    sampleCount: s.length,
    t: s.map((x) => x.t),
    q: s.map((x) => x.q),
    cmd: s.map((x) => x.cmd),
    pod: s.map((x) => x.pod),
    phase: s.map((x) => x.ph),
    held: s.map((x) => (x.held ? 1 : 0)),
  };
}

export async function gzipJson(obj: unknown): Promise<Blob> {
  const stream = new Blob([JSON.stringify(obj)]).stream().pipeThrough(new CompressionStream('gzip'));
  return new Response(stream).blob();
}
