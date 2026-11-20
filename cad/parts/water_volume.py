# cad/parts/water_volume.py: the water in the tank at its normal level (owner: about 15 cm), a separate named part so a viewer can hide it.
# It fills the inside of tank_shell() from the floor up to WATER_LEVEL, so it never overlaps the tank walls.
from .common import box
from .unit_dims import TW, TD, TANK_WALL, WATER_LEVEL

COLOR_WATER = (0.2, 0.45, 0.95, 0.45)       # translucent blue
PART_NAME = "water_volume"


def water_volume():
    return box(TW - 2 * TANK_WALL, TD - 2 * TANK_WALL, WATER_LEVEL - TANK_WALL, 0, 0, TANK_WALL)


def litres():
    return (TW - 2 * TANK_WALL) * (TD - 2 * TANK_WALL) * (WATER_LEVEL - TANK_WALL) / 1e6
