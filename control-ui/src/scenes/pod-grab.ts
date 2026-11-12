// Placeholder for the "pod-grab" scene. Replace with a real scene: its own MJCF model and its own control panel.
import { SCENE_INFOS } from './list.ts';
import { placeholderScene } from './placeholder.ts';

export const podGrabScene = placeholderScene(SCENE_INFOS.find((s) => s.id === 'pod-grab')!);
