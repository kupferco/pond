// Placeholder for the "transfer" scene. Replace with a real scene: its own MJCF model and its own control panel.
import { SCENE_INFOS } from './list.ts';
import { placeholderScene } from './placeholder.ts';

export const transferScene = placeholderScene(SCENE_INFOS.find((s) => s.id === 'transfer')!);
