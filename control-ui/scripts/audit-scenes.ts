// Where the cart stands in every sim scene, against the CAD's Complete unit (OpenPocket #447). Run: node --experimental-strip-types scripts/audit-scenes.ts
// Prints one row per scene: rider hand, distance of its pipe axis from the leg it rides (mm), tilt of the cart (deg), roll about the leg from the CAD travel pose (deg), side of the free hand.
import loadMujoco from '@mujoco/mujoco';
import { auditScenes } from '../src/cart/audit-scenes.ts';
const mj = await loadMujoco();
for (const r of auditScenes(mj)) console.log(r.scene.padEnd(34), 'rider', r.p.rider, '| off the leg', r.p.offAxisMm.toFixed(2), 'mm | tilt', r.p.tiltDeg.toFixed(2), '| roll', r.p.rollDeg.toFixed(1), '| free hand', r.p.freeSide, r.p.freeDistMm.toFixed(0), 'mm | expected', r.expect, r.ok ? 'OK' : 'DIFFERS');
