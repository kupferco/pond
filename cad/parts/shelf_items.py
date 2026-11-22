# cad/parts/shelf_items.py: the seedling storage (the blue part: a box with five pod sticks) and the seedling tray (shallow tray with cells). They stand on the
# SHELF (cad/parts/shelf.py) inside the tank, UNDER the lid (OpenPocket #447; they used to be drawn on top of the lid by mistake), in front of the growing pipe.
# The ONLY definition (was drawn separately in complete_unit.py and water_station.py).
from .common import box, union_all
from .unit_dims import SHELF_TOP


def seedling_storage():
    sticks = [box(230, 14, 36, 190, -125 - 40 + k * 20, SHELF_TOP + 12) for k in range(5)]
    return union_all([box(240, 110, 12, 190, -125, SHELF_TOP)] + sticks)


def seedling_tray():
    cells = [box(25, 18, 24, x, y, SHELF_TOP + 6) for x in range(-290, -80, 35) for y in (-150, -125, -100)]
    return union_all([box(240, 110, 6, -190, -125, SHELF_TOP)] + cells)
