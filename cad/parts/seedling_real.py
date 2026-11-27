# cad/parts/seedling_real.py: the REAL seedling tray and the REAL pod store, for the complete unit (OpenPocket #537, follow-up of 27 Nov 2026). They replace the
# stand-in boxes of cad/parts/shelf_items.py in the complete unit. Nothing is redrawn: the tray is cart_arm.py's seed_tray() (200 x 380 mm, 4 x 4 cell pockets,
# put back in the tank frame) and the store is pod_store_reach.py's 14 pod rows (their pick line, shortened round the pipe), the tank-sized version of the concept
# in cad/pod_store.py (that concept is five 570 mm sticks, 590 x 195 mm, which do not fit beside the 200 mm tray in the 692 mm wide tank: open question).
# Both stand on the shelf (cad/parts/shelf.py) under the lid, at the x/y the study scripts give them; only their height is moved onto the shelf top.
import contextlib
import io
import os
import runpy
import sys

import cadquery as cq

_CAD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _CAD)
import layout as LAY
from .unit_dims import SHELF_TOP, TW as LAY_TW

COLOR_TRAY = (0.3, 0.7, 0.4, 1)
COLOR_STORE = (0.3, 0.55, 0.85, 1)
_cache = {}


def _on_shelf(shape):
    zmin = shape.val().BoundingBox().zmin
    return shape.translate((0, 0, SHELF_TOP - zmin))


def seedling_tray_real():
    if "tray" not in _cache:
        import cart_arm as ca
        # seed_tray() is in the cart frame; store_to_cart(x, y, z) = (y - YC, -(x - PIPE_XW), z - SHOULDER_Z): turn it back by +90 degrees about Z and translate
        t = ca.seed_tray().rotate((0, 0, 0), (0, 0, 1), 90).translate((ca.PIPE_XW, ca.YC, ca.SHOULDER_Z))
        _cache["tray"] = _on_shelf(t)
    return _cache["tray"]


def pod_store_real():
    if "store" not in _cache:
        with contextlib.redirect_stdout(io.StringIO()):
            ns = runpy.run_path(os.path.join(_CAD, "pod_store_reach.py"))
        rows = ns["rows"].translate((0, 0, LAY.TANK_H - ns["TH"]))     # the study tank was 400 high; the unit's is layout TANK_H
        # the study puts the rows' outer edge at x = 350 and the front at y = -200: inside the 4 mm tank walls (inner faces at +-346 / -196). Move them in by exactly that
        # (4 mm in x, 4 mm in y); the pick line (y about 0) and the row pitch are unchanged.
        rows = rows.translate((-(350.0 - (LAY_TW / 2 - 4.0)), 4.0, 0))
        _cache["store"] = _on_shelf(rows)
    return _cache["store"]
