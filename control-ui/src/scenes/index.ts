import type { Scene } from './scene.ts';
import { armScene } from './arm.ts';
import { cartScene } from './cart.ts';
import { transferScene } from './transfer.ts';
import { podGrabScene } from './pod-grab.ts';
import { pillarScene } from './pillar.ts';
import { singleUnitScene } from './single-unit.ts';
import { fourUnitsScene } from './four-units.ts';

export const SCENES: readonly Scene[] = [armScene, cartScene, transferScene, podGrabScene, pillarScene, singleUnitScene, fourUnitsScene];
