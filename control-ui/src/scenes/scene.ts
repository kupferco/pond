import type { MainModule } from '@mujoco/mujoco';
import type { SceneInfo } from './list.ts';

export interface SceneContext {
  mujoco: MainModule;
  view: HTMLElement;   // 3D area
  panel: HTMLElement;  // control panel
  status: HTMLElement; // centred message over the 3D area
}

export interface SceneInstance {
  /** Called every animation frame with wall-clock seconds since the last frame. */
  frame(dt: number): void;
  /** Free everything the scene created (MuJoCo model/data, WebGL, DOM, listeners). */
  dispose(): void;
}

/** One scene = one module: its own model, its own control panel. */
export interface Scene extends SceneInfo {
  load(ctx: SceneContext): Promise<SceneInstance>;
}
