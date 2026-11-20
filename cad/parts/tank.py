# cad/parts/tank.py: the water tank (open box) and its lid. The ONLY definition; unit_v3_aframe.py, water_station.py, complete_unit.py import it.
from .common import box
from .unit_dims import TW, TD, TH, TANK_WALL, LID_T

COLOR_TANK = (0.75, 0.75, 0.8, 0.35)
COLOR_LID = (0.6, 0.6, 0.65, 0.6)


def tank_shell():
    """Open-top box 700 x 400 x 300, 4 mm walls and floor."""
    return box(TW, TD, TH, 0, 0, 0).cut(box(TW - 2 * TANK_WALL, TD - 2 * TANK_WALL, TH, 0, 0, TANK_WALL))


def tank_lid():
    """Flat lid on top of the tank (plain slab; the station's socket pocket is cut by water_station.py)."""
    return box(TW, TD, LID_T, 0, 0, TH)
