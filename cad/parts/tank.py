# cad/parts/tank.py: the water tank (open box) and its lid. The ONLY definition; unit_v3_aframe.py, water_station.py, complete_unit.py import it.
import os
import sys
from .common import box
from .unit_dims import TW, TD, TH, TANK_WALL, LID_T

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import pod_layout as PL   # noqa: E402

COLOR_TANK = (0.75, 0.75, 0.8, 0.35)
COLOR_LID = (0.6, 0.6, 0.65, 0.6)


def tank_shell():
    """Open-top box 700 x 400 x 300, 4 mm walls and floor."""
    return box(TW, TD, TH, 0, 0, 0).cut(box(TW - 2 * TANK_WALL, TD - 2 * TANK_WALL, TH, 0, 0, TANK_WALL))


def tank_lid():
    """Flat lid on top of the tank (the station's socket pocket is cut by water_station.py). OpenPocket #531: a pick slot (at least 70 x 50, rounded corners, sized to the claw's lean by the sim: cad/pod_slots.json) over every
    seedling tray cell and every pod store landing, for the claw and the wrist (cad/pod_layout.py). On the 38 mm cell pitch the tray slots overlap into one window."""
    lid = box(TW, TD, LID_T, 0, 0, TH)
    cutters = [box(x1 - x0, y1 - y0, LID_T + 2, (x0 + x1) / 2, (y0 + y1) / 2, TH - 1).edges("|Z").fillet(PL.SLOT_R) for x0, x1, y0, y1 in PL.slot_rects().values()]
    for c in cutters:
        lid = lid.cut(c)
    return lid
