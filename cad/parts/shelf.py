# cad/parts/shelf.py: the shelf inside the tank, under the lid, above the water (OpenPocket #447). The ONLY definition. The seedling tray and the seedling
# storage (the blue part) stand on it: cad/parts/shelf_items.py. Plate across the whole inside of the tank, resting on the walls, with a hole where the spine
# tube goes down to the tank floor (the growing pipe stops at the lid).
from .common import box, cyl
from .unit_dims import TW, TD, TANK_WALL, SHELF_T, SHELF_Z, SP

COLOR_SHELF = (0.5, 0.5, 0.55, 0.6)
SPINE_HOLE_CLEARANCE = 1.0


def shelf():
    return box(TW - 2 * TANK_WALL, TD - 2 * TANK_WALL, SHELF_T, 0, 0, SHELF_Z).cut(cyl(SP / 2 + SPINE_HOLE_CLEARANCE, SHELF_T + 2, 0, 0, SHELF_Z - 1))
