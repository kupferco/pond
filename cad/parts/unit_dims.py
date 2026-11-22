# cad/parts/unit_dims.py: the unit's shared numbers (mm, Z up, growing pipe at x = y = 0), defined once. Moved from unit_v3_aframe.py,
# where they were copied into complete_unit.py and water_station.py (the latter had the growing pipe at 33.7 mm, which is the spine tube).
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import layout as LAY   # OpenPocket #364: tank, lid and bottom track heights come from the ONE shared layout (cad/layout.json)
TW, TD, TH = 700.0, 400.0, LAY.TANK_H        # tank width (x), depth (y), height (z)
TANK_WALL = 4.0
LID_T = LAY.LID_T
GP = 75.0                                # growing pipe OD
SP = 33.7                                # spine tube OD
LR = 8.0                                 # 16 mm leg rod radius
TX = 290.0                               # track loop half width
TR = 16.0                                # track pipe radius (32 mm OD)
R = 150.0                                # track corner radius
LOOP_Y = -60.0                           # track loop plane (y)
ZB = LAY.TRACK_BOTTOM_Z                          # bottom run axis height
ZT = 1900.0 - TR                         # top run axis height
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
