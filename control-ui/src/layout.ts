// The ONE shared layout of the unit for the sim (OpenPocket #364): the same numbers as cad/layout.py, read from the same file (cad/layout.json), in metres.
// Tank height, lid, the bottom track height above the lid and the room the cart needs under the track are defined there and nowhere else.
// cart_clearance_mm is ASSUMED (not given by the owner): see cad/layout.json.
import layout from '../../cad/layout.json' with { type: 'json' };

const mm = (v: number) => v / 1000;
export const TANK_H = mm(layout.tank_h_mm);                       // 0.300
export const LID_T = mm(layout.lid_t_mm);                         // 0.004
export const LID_TOP = TANK_H + LID_T;                            // 0.304
export const WATER_LEVEL = mm(layout.water_level_mm);             // 0.150: normal water level over the tank floor
export const CART_BELOW_TRACK = mm(layout.cart_below_track_mm);   // how far the cart (and what is mounted on it) reaches past the track axis, towards the tank
export const CART_CLEARANCE = mm(layout.cart_clearance_mm);       // ASSUMED air gap between the lowest cart part and the lid
export const TRACK_BOTTOM_ABOVE_LID = CART_BELOW_TRACK + CART_CLEARANCE;   // 0.210
export const TRACK_BOTTOM_Z = LID_TOP + TRACK_BOTTOM_ABOVE_LID;   // 0.514: bottom run axis over the tank floor
