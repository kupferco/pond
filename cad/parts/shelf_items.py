# cad/parts/shelf_items.py: the seedling tray (4 x 4 cells) and the dry pod store (gravity-feed, 7 lanes, 15 deg slope, flat landing at the front) with their pods. They stand
# on the SHELF (cad/parts/shelf.py) inside the tank, UNDER the lid, in front of the growing pipe. The ONLY definition (OpenPocket #531: upright pod-grab layout).
# Every number comes from cad/pod_layout.py (also read by sim/pod_grab.py), so the sim and the drawings cannot drift apart.
import math
import os
import sys
import cadquery as cq
from .common import box, union_all, cyl
from .unit_dims import SHELF_TOP

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import pod_layout as PL   # noqa: E402


def _bxx(x0, x1, y0, y1, z0, z1):
    return box(x1 - x0, y1 - y0, z1 - z0, (x0 + x1) / 2, (y0 + y1) / 2, z0)


def seedling_tray():
    """Shallow tray: a base plate and 3 x 6 cell blocks (35 x 34 x 24, A..C at y -150, -112, -74, columns 1..6 at x -115..-290), each with a round pocket for its pod."""
    x_lo, x_hi = PL.tray_cell_x(PL.TRAY_COLS - 1) - PL.CELL_X / 2, PL.tray_cell_x(0) + PL.CELL_X / 2
    base = _bxx(x_lo, x_hi, PL.TRAY_ROWS_Y[0] - PL.CELL_Y / 2, PL.TRAY_ROWS_Y[-1] + PL.CELL_Y / 2, SHELF_TOP, SHELF_TOP + PL.TRAY_BASE_T)
    z0 = SHELF_TOP + PL.TRAY_BASE_T
    cells = []
    for (x, y, _, _) in PL.tray_cells().values():
        blk = box(PL.CELL_X, PL.CELL_Y, PL.CELL_H, x, y, z0).cut(cyl(PL.POD_D / 2 + 0.5, PL.CELL_H - 4, x, y, z0 + 4))
        cells.append(blk)
    return union_all([base] + cells)


def _lane_profile():
    """Side profile (y, z) of one lane's floor: flat landing, then the ramp rising backwards at SLOPE_DEG."""
    return [(PL.LAND_Y[0], PL.ZL), (PL.LAND_Y[1], PL.ZL), (PL.RAMP_Y1, PL.ZL + PL.ramp_rise())]


def seedling_storage():
    """Dry pod store: a base plate, a wedge ramp sloping down to the front, a stop lip, and a thin rail between lanes."""
    x0, x1 = PL.lane_x(0) - PL.LANE_PITCH / 2, PL.lane_x(PL.LANES - 1) + PL.LANE_PITCH / 2
    base = _bxx(x0, x1, PL.LAND_Y[0] - PL.LIP_T, PL.RAMP_Y1, SHELF_TOP, PL.ZL)
    wedge = cq.Workplane("YZ").polyline(_lane_profile()).close().extrude(x1 - x0).translate((x0, 0, 0))
    lip = _bxx(x0, x1, PL.LAND_Y[0] - PL.LIP_T, PL.LAND_Y[0], PL.ZL, PL.ZL + PL.LIP_H)
    rails = []
    for i in range(PL.LANES + 1):
        xr = x0 + i * PL.LANE_PITCH
        poly = [(PL.LAND_Y[0], PL.ZL), (PL.LAND_Y[1], PL.ZL), (PL.RAMP_Y1, PL.ZL + PL.ramp_rise()),
                (PL.RAMP_Y1, PL.ZL + PL.ramp_rise() + PL.RAIL_H), (PL.LAND_Y[1], PL.ZL + PL.RAIL_H), (PL.LAND_Y[0], PL.ZL + PL.RAIL_H)]
        rails.append(cq.Workplane("YZ").polyline(poly).close().extrude(PL.RAIL_T).translate((xr - PL.RAIL_T / 2, 0, 0)))
    return union_all([base, wedge, lip] + rails)


def pods():
    """All pods: 16 upright in the tray, 7 x 4 in the store (the front one upright on its landing, the 3 behind it standing square on the ramp)."""
    out = [cyl(PL.POD_D / 2, PL.POD_H, x, y, PL.POD_BOTTOM_TRAY) for (x, y, _, _) in PL.tray_cells().values()]
    t = math.tan(math.radians(PL.SLOPE_DEG))
    for i in range(PL.LANES):
        x = PL.lane_x(i)
        out.append(cyl(PL.POD_D / 2, PL.POD_H, x, PL.LAND_CY, PL.ZL))
        for k in range(1, PL.LANE_PODS):
            yc = PL.LAND_Y[1] + PL.POD_D / 2 + 2 + (k - 1) * PL.POD_PITCH_ON_RAMP
            zf = PL.ZL + (yc - PL.LAND_Y[1]) * t
            p = cq.Workplane("XY").circle(PL.POD_D / 2).extrude(PL.POD_H).rotate((0, 0, 0), (1, 0, 0), PL.SLOPE_DEG).translate((x, yc, zf))
            out.append(p)
    return union_all(out)
