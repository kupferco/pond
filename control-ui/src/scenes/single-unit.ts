// Placeholder for the "single-unit" scene. Replace with a real scene: its own MJCF model and its own control panel.
import { SCENE_INFOS } from './list.ts';
import { placeholderScene } from './placeholder.ts';

export const singleUnitScene = placeholderScene(SCENE_INFOS.find((s) => s.id === 'single-unit')!);
