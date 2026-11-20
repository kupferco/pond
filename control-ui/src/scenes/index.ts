import type { Scene } from './scene.ts';
import { armScene } from './arm.ts';
import { cartScene } from './cart.ts';
import { transferScene } from './transfer.ts';
import { podGrabScene } from './pod-grab.ts';
import { pillarScene } from './pillar.ts';
import { transplantScene } from './transplant.ts';
import { reachScene } from './reach-test.ts';
import { waterSampleScene } from './water-sample.ts';
import { singleUnitScene } from './single-unit.ts';
import { fourUnitsScene } from './four-units.ts';

export const SCENES: readonly Scene[] = [armScene, cartScene, transferScene, podGrabScene, pillarScene, transplantScene, reachScene, waterSampleScene, singleUnitScene, fourUnitsScene];
