# cad/parts/lid_items.py: things that stand on the tank lid in front of the pipe: seedling storage (box with five pod sticks) and the
# seedling tray (shallow tray with cells). The ONLY definition (was drawn separately in complete_unit.py and water_station.py).
from .common import box, union_all
from .unit_dims import LID


def seedling_storage():
    sticks = [box(230, 14, 36, 190, -125 - 40 + k * 20, LID + 16) for k in range(5)]
    return union_all([box(240, 110, 12, 190, -125, LID + 4)] + sticks)


def seedling_tray():
    cells = [box(25, 18, 24, x, y, LID + 10) for x in range(-290, -80, 35) for y in (-150, -125, -100)]
    return union_all([box(240, 110, 6, -190, -125, LID + 4)] + cells)
