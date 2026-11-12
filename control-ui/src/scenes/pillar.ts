// Placeholder for the "pillar" scene. Replace with a real scene: its own MJCF model and its own control panel.
import { SCENE_INFOS } from './list.ts';
import { placeholderScene } from './placeholder.ts';

export const pillarScene = placeholderScene(SCENE_INFOS.find((s) => s.id === 'pillar')!);
