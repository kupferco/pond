# cad/parts/unit_dims.py: the unit's shared numbers (mm, Z up, growing pipe at x = y = 0), defined once. Moved from unit_v3_aframe.py,
# where they were copied into complete_unit.py and water_station.py (the latter had the growing pipe at 33.7 mm, which is the spine tube).
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import layout as LAY   # OpenPocket #364: tank, lid and bottom track heights come from the ONE shared layout (cad/layout.json)
TW, TD, TH = 700.0, 400.0, LAY.TANK_H        # tank width (x), depth (y), height (z)
TANK_WALL = 4.0
LID_T = LAY.LID_T
GP = LAY.GROWING_PIPE_OD                 # growing pipe OD (the central pipe, on x = y = 0)
SP = LAY.SPINE_OD                        # spine tube OD
LR = 8.0                                 # 16 mm leg rod radius
TX = LAY.TRACK_HALF_WIDTH                # track loop half width
TR = LAY.TRACK_PIPE_R                    # track pipe radius (32 mm OD)
R = LAY.TRACK_CORNER_R                   # track corner radius
LOOP_Y = LAY.TRACK_LOOP_Y                # track loop plane (y): 66 mm in front of the central pipe (16 tube radius + 50 rod, track_joint.py ROD_OUT); was -60 (#537)
TRACK_OFFSET = LAY.TRACK_OFFSET          # track axis to central pipe axis
CENTRAL_X, CENTRAL_Y = LAY.CENTRAL_PIPE_XY   # the central pipe: never moves
ZB = LAY.TRACK_BOTTOM_Z                          # bottom run axis height
ZT = LAY.TRACK_TOP_Z                     # top run axis height (1900 top bar - 16)
ZC1, ZC2 = 1215.0, 1547.5                # lower / upper clamp collar heights
FOOT_X = 340.0
LID = TH + LID_T                         # lid top
ZBAR = 1900.0                            # top bar
BAR_X = 200.0
RP = GP / 2
RC = RP + 3
WATER_LEVEL = LAY.WATER_LEVEL                      # normal water level in the tank, measured from the tank floor (owner: about 15 cm)
# The shelf inside the tank (OpenPocket #447: restored; #365 had taken it out as "not in the current design", which was wrong). A 4 mm plate resting on the
# tank walls, 5 mm above the normal water level so the seedling tray and storage on it stay dry, and under the lid with the rest of the tank height to spare.
SHELF_T = 4.0
SHELF_Z = WATER_LEVEL + 5.0                        # shelf underside: 155 (the 155 mm shelf of the older drawings and of the sim's pod grab / transplant scenes)
SHELF_TOP = SHELF_Z + SHELF_T                      # 159: what the seedling tray and storage stand on
