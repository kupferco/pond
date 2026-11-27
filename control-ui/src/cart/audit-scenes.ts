// The scene audit of OpenPocket #447: for every sim scene that carries the CAD cart, where the cart stands against the track leg it rides, and whether that is the CAD's arrangement.
import type { MainModule } from '@mujoco/mujoco';
import { placementOf, type Leg, type Placement, type V3 } from './audit.ts';
import { omniTrackMjcf, placeOmniCart, RIDER } from './omni-track.ts';
import { transferMjcf, placeTransfer } from './omni-transfer.ts';
import { transplantMjcf, YC, XT, CART_Z0 } from '../transplant/layout.ts';
import { podGrabMjcf, PIPE_Y, PIPE_Z, CART_HOME_X } from '../podgrab/layout.ts';
import { CAD_UNIT } from '../generated/cad-sim.ts';

export interface Row { scene: string; p: Placement; expect: string; ok: boolean }
const near = (a: number, b: number, tol: number) => Math.abs(a - b) <= tol;

/** expect: the roll (deg) and free-hand side the scene is meant to have. Off the leg and tilt must be 0 everywhere. */
export function auditScenes(mj: MainModule): Row[] {
  const rows: Row[] = [];
  const add = (scene: string, p: Placement, roll: number, side: string) => rows.push({ scene, p, expect: `roll ${roll}, free ${side}`, ok: near(p.offAxisMm, 0, 0.5) && near(p.tiltDeg, 0, 0.5) && near(Math.abs(p.rollDeg), roll, 1) && p.freeSide === side });
  const make = (xml: string) => { const m = mj.MjModel.from_xml_string(xml); return { m, d: new mj.MjData(m) }; };

  // 1. Cart on the track: the pipe at the origin along z, the loop's middle (the bend) towards +x, the unit towards +y.
  { const { m, d } = make(omniTrackMjcf()); placeOmniCart(m as never, d as never, 30, 0); mj.mj_forward(m, d);
    const leg: Leg = { point: [0, 0, 0], dir: [0, 0, 1], toUnit: [0, 1, 0], outward: [-1, 0, 0] };
    add('cart on track (s 30 cm)', placementOf(m as never, d as never, leg, RIDER), 0, 'outer'); }
  // 2. Transfer: pipes B (x -60, bends -x) and C (x +60, bends +x), the cart rides one; the other pipe is the neighbour unit's leg.
  for (const rider of ['B', 'C'] as const) {
    const { m, d } = make(transferMjcf()); placeTransfer(m as never, d as never, { rider, s: 30, roll: 0, open: 1 }); mj.mj_forward(m, d);
    const x = rider === 'B' ? -0.06 : 0.06;
    const leg: Leg = { point: [x, 0, 0], dir: [0, 0, 1], toUnit: [0, 1, 0], outward: [rider === 'B' ? 1 : -1, 0, 0] };
    add(`transfer, hand ${rider} riding (s 30 cm)`, placementOf(m as never, d as never, leg, rider), 0, 'outer');
  }
  // 3. Transplant: the track plane x = XT, legs at y = -/+0.29, the unit (growing pipe at x = y = 0) towards -x; the cart rides the -y leg, plate towards the unit (rolled 180).
  { const { m, d } = make(transplantMjcf()); mj.mj_forward(m, d);
    const leg: Leg = { point: [XT, -CAD_UNIT.TX / 1000, CART_Z0], dir: [0, 0, 1], toUnit: [-1, 0, 0], outward: [0, -1, 0] };
    add('transplant (leg -y)', placementOf(m as never, d as never, leg, 'C'), 180, 'inner'); void YC; }
  // 4. Pod grab (#537): rides the bottom run (along world x) of the loop at y = PIPE_Y (66 mm in front of the central pipe), z = PIPE_Z, on its TOP sleeve (hand B): the unit (central pipe at y = 0) is towards +y,
  //    the loop's middle above the run, the body and the free hand hang BELOW the pipe (outer), the plate on the front, away from the unit (roll 0): the CAD arrangement of cad/complete_unit.py.
  { const { m, d } = make(podGrabMjcf()); mj.mj_forward(m, d);
    const leg: Leg = { point: [CART_HOME_X, PIPE_Y, PIPE_Z], dir: [1, 0, 0], toUnit: [0, 1, 0], outward: [0, 0, -1] };
    add('pod grab (bottom run)', placementOf(m as never, d as never, leg, 'B'), 0, 'outer'); }
  return rows;
}
