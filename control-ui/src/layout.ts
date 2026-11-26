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

// ---- OpenPocket #537: the rest of the unit's layout, from the same JSON (cad/layout.py derives the same numbers) ----
export const CENTRAL_PIPE_X = mm(layout.central_pipe_x_mm);       // 0: the central pipe (growing pipe + spine) stands on the tank centre and never moves
export const CENTRAL_PIPE_Y = mm(layout.central_pipe_y_mm);       // 0
export const GROWING_PIPE_OD = mm(layout.growing_pipe_od_mm);     // 0.075
export const SPINE_OD = mm(layout.spine_od_mm);                   // 0.0337
export const TRACK_PIPE_R = mm(layout.track_pipe_od_mm) / 2;      // 0.016
export const TRACK_ROD_OUT = mm(layout.track_rod_out_mm);         // 0.050: track_joint.py ROD_OUT, tube surface to the central pipe's axis
export const TRACK_OFFSET = TRACK_PIPE_R + TRACK_ROD_OUT;         // 0.066: track pipe axis to the central pipe axis
export const TRACK_LOOP_Y = CENTRAL_PIPE_Y - TRACK_OFFSET;        // -0.066: the track plane in the unit frame (x along the track, y front (-) to back (+)), CAD y
export const CART_PIPE_SPACING = mm(layout.cart_pipe_spacing_mm); // 0.120
/** The sleeve that rides the track: "B", the TOP one. The cart body hangs BELOW it (CART_DZ below the pipe on a horizontal run); the bottom sleeve never climbs or clamps. */
export const CART_CLIMB_SLEEVE = layout.cart_climb_sleeve as 'B' | 'C';
