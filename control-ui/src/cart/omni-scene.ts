// The omni-wheel cart as a STATIC body for the scenes where the cart only rides and carries the arm (Pod grab, Transplant seedling; OpenPocket #284, plan task 265 part 10).
// It is the cart of src/cart/omni.ts (rigid base on two three-lobe sleeves, 38 mm driven omni wheels, ball cups) with every joint taken out: the roll, wheel, ball and jaw
// joints are not needed while the cart rides, and a free joint would let the cart sag in a scene with gravity. The free hand's jaw is built already open (the cart rides
// the track with ONE hand, the other hangs open, as the Transfer scene shows it).
// Two things differ from the cart in omni.ts: the arm base block ('armbase') is left out, because these scenes bolt the real SO-101 base to the battery themselves, and
// the plate body is called 'cartbase', because the arm's own first body is 'base'.
import { omniCartBody, JAW_OPEN_RAD, BATT, PLATE_Y0, PLATE_Y1, PLATE_X0, PLATE_X1, PLATE_ZH, PLATE_T, ARM_BASE_W, type Hand } from './omni.ts';

/** Where things are on the cart, cart frame (mm): x across the pipes, y out of the pipe plane (the plate is on -y), z along the pipes. From cad/cart_dims.py. */
export const CART = {
  plateFaceY: PLATE_Y0,                        // -56: front face of the plate
  plateBackY: PLATE_Y1,                        // -50: on the sleeve pads
  battFaceY: PLATE_Y0 - BATT[1],               // -106: front face of the battery, where the arm base is bolted (cart_dims.py ARM_Y0)
  plateX: [PLATE_X0, PLATE_X1] as const,       // -84 .. 84
  plateZH: PLATE_ZH,                           // 73: the plate is 146 mm along the pipes
  plateT: PLATE_T,
  armBaseW: ARM_BASE_W,
};

/**
 * MJCF of the static omni cart (cart frame, origin at the cart centre, metres) to put inside a body of the scene.
 * free: the hand that is NOT on the track; its jaw is open. col: collision attributes for every cart geom, colBattery for the battery alone. The cart is built as plain jointless bodies, so wrap it in a
 * body that has a (locked) joint if the scene has to test it against the static parts.
 */
export function staticOmniCart(o: { free: Hand; col: string; colBattery?: string; jawOpenRad?: number }): string {
  const x = omniCartBody({ jawOpen: { [o.free]: o.jawOpenRad ?? JAW_OPEN_RAD } });
  const noArm = x
    .replace(/<joint [^>]*\/>/g, '')
    .replace(/<geom name="armbase"[^>]*\/>/, '')
    .replace('<body name="base">', '<body name="cartbase">')
    .replace(/(<geom name="battery"[^>]*?)contype="2" conaffinity="0"/, `$1${o.colBattery ?? o.col}`);   // the arm base is flush on the battery: it may need other collision bits
  return noArm.replaceAll('contype="2" conaffinity="0"', o.col).replaceAll('<body ', '<body gravcomp="1" ');
}
