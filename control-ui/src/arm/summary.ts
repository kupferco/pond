// Shape of the Firestore run summary. Keep in sync with firestore.rules (it validates exactly these fields).
import type { Attempt } from './attempt.ts';
import { CONTROLLER_VERSION, SCENE_VERSION } from './dims.ts';
import type { RunMeta } from './trajectory.ts';

export interface RunSummary {
  id: string;
  scene: string;
  sceneVersion: string;
  controllerVersion: string;
  batchId: string;
  batchIndex: number;
  batchSize: number;
  seed: number;
  podXmm: number; podYmm: number;
  slotXmm: number; slotYmm: number;
  success: boolean;
  reason: string;
  posErrMm: number;
  tiltErrDeg: number;
  durationS: number;
  samples: number;
  noiseMm: number;
  storagePath: string;
  bytes: number;
}

const mm = (m: number) => Math.round(m * 10000) / 10;

export function attemptSummary(a: Attempt, meta: RunMeta, storagePath: string, bytes: number): RunSummary {
  const r = a.result!;
  return {
    id: meta.runId, scene: 'arm', sceneVersion: SCENE_VERSION, controllerVersion: CONTROLLER_VERSION,
    batchId: meta.batchId, batchIndex: meta.batchIndex, batchSize: meta.batchSize, seed: a.cfg.seed,
    podXmm: mm(a.cfg.pod[0]), podYmm: mm(a.cfg.pod[1]), slotXmm: mm(a.cfg.slot[0]), slotYmm: mm(a.cfg.slot[1]),
    success: r.success, reason: r.reason, posErrMm: r.posErrMm, tiltErrDeg: r.tiltErrDeg, durationS: r.durationS,
    samples: a.samples.length, noiseMm: a.cfg.noiseMm ?? 1.2, storagePath, bytes,
  };
}
