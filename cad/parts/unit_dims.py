# cad/parts/unit_dims.py: the unit's shared numbers (mm, Z up, growing pipe at x = y = 0), defined once. Moved from unit_v3_aframe.py,
# where they were copied into complete_unit.py and water_station.py (the latter had the growing pipe at 33.7 mm, which is the spine tube).
TW, TD, TH = 700.0, 400.0, 300.0        # tank width (x), depth (y), height (z)
TANK_WALL = 4.0
LID_T = 4.0
GP = 75.0                                # growing pipe OD
SP = 33.7                                # spine tube OD
LR = 8.0                                 # 16 mm leg rod radius
TX = 290.0                               # track loop half width
TR = 16.0                                # track pipe radius (32 mm OD)
R = 150.0                                # track corner radius
LOOP_Y = -60.0                           # track loop plane (y)
ZB = TH + 150.0                          # bottom run axis height
ZT = 1900.0 - TR                         # top run axis height
ZC1, ZC2 = 1215.0, 1547.5                # lower / upper clamp collar heights
FOOT_X = 340.0
LID = TH + LID_T                         # lid top
ZBAR = 1900.0                            # top bar
BAR_X = 200.0
RP = GP / 2
RC = RP + 3
WATER_LEVEL = 150.0                      # normal water level in the tank, measured from the tank floor (owner: about 15 cm)
