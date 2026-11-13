// Scene catalogue: plain data only (no MuJoCo/three imports) so it is cheap to test.
export type SceneGroup = 'Tests' | 'Systems';

export interface SceneInfo {
  id: string;
  name: string;
  group: SceneGroup;
  description: string;
}

export const SCENE_INFOS: readonly SceneInfo[] = [
  { id: 'arm', name: '1. Arm', group: 'Tests', description: 'The five-motor arm, driven joint by joint.' },
  { id: 'cart', name: '2. Cart', group: 'Tests', description: 'The cart moving along the track system.' },
  { id: 'transfer', name: '3. Transfer', group: 'Tests', description: 'Handing over from one unit to another.' },
  { id: 'pod-grab', name: '4. Pod grab', group: 'Tests', description: 'Grab a pod inside the tank and move it to the seedling tray.' },
  { id: 'pillar', name: '5. Pillar', group: 'Tests', description: 'Push pods into and pull them out of the central pillar, including the blank plug.' },
  { id: 'single-unit', name: '6. Single unit', group: 'Systems', description: 'One complete unit in isolation, with full control.' },
  { id: 'four-units', name: '7. Four units', group: 'Systems', description: 'Four complete units with full tracks, one unit placed at an angle; the robot drives along the tracks and grabs pods.' },
];

export const GROUPS: readonly SceneGroup[] = ['Tests', 'Systems'];
export const DEFAULT_SCENE = 'arm';
export const STORAGE_KEY = 'pond.sim.scene';

export const isSceneId = (id: unknown): id is string => typeof id === 'string' && SCENE_INFOS.some((s) => s.id === id);

/** URL (?scene=) wins over the remembered choice; anything unknown falls back to the default. */
export function resolveSceneId(search: string, stored: string | null): string {
  const fromUrl = new URLSearchParams(search).get('scene');
  if (isSceneId(fromUrl)) return fromUrl;
  if (isSceneId(stored)) return stored;
  return DEFAULT_SCENE;
}
