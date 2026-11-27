# cad/layout.py: the ONE shared layout of the unit (OpenPocket #364). Tank height, lid, bottom track height and the room the cart needs under the track
# come from layout.json and nowhere else. unit_v3_*.py, complete_unit.py, track_supports.py, water_station.py, water_assembly.py, the render scripts
# and the sim (control-ui/src/layout.ts reads the same JSON) import these, so a tank or track height cannot be guessed separately in each drawing.
# Everything marked ASSUMED in layout.json (cart_clearance_mm) is not given by the owner. mm, Z up, tank floor z = 0.
import json
import os

_D = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "layout.json")))
TANK_H = float(_D["tank_h_mm"])
LID_T = float(_D["lid_t_mm"])
LID_TOP = TANK_H + LID_T                                            # 304: top of the tank lid
WATER_LEVEL = float(_D["water_level_mm"])                           # 150: normal water level over the tank floor
CART_BELOW_TRACK = float(_D["cart_below_track_mm"])                 # how far the cart (and what is mounted on it) reaches past the track axis, towards the tank
CART_CLEARANCE = float(_D["cart_clearance_mm"])                     # ASSUMED air gap between the lowest cart part and the lid
TRACK_BOTTOM_ABOVE_LID = CART_BELOW_TRACK + CART_CLEARANCE          # 210: bottom track axis above the lid top
TRACK_BOTTOM_Z = LID_TOP + TRACK_BOTTOM_ABOVE_LID                   # 514: bottom track run axis (was guessed as 450 = lid + 146)
OLD_TRACK_BOTTOM_Z = TANK_H + 150.0                                 # what unit_v3_aframe.py used before (the water station was drawn against it)
TRACK_RISE = TRACK_BOTTOM_Z - OLD_TRACK_BOTTOM_Z                    # how far everything that is positioned off the track moved up
TRACK_ROD_OUT = float(_D["track_rod_out_mm"])                      # 50: reach of the M8 rod from the track pipe surface towards the spine (track_joint.py ROD_OUT)
