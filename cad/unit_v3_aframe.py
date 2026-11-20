import os, sys
import cadquery as cq, math
# cad/unit_v3_aframe.py — v5 (7 Nov 2026)
# v6 (14 Nov 2026, Viber #97): track loop widened, TX 250 -> 290 (pipes 60 mm in from the tank edge).
# v5: legs no longer pass through the PVC. 50 mm metal clamp collars sit OUTSIDE the growing pipe with
#     long angled sleeves (60 mm) that take the 16 mm legs. Inside the pipe at each collar height, a spacer
#     ring between pipe and spine carries the load to the spine. Lower collar z=1215 (side legs + back strut),
#     top collar z=1547.5. 30 W panel 450 x 350 at 23 deg on a 400 mm top bar.
# v4: short collars but legs through drilled pipe. v3: single panel. v2: strut, feet, V roof. v1: lower A-frame.
# 20 Nov 2026 (OpenPocket #365): single-source. Every part now lives in cad/parts/ (see docs/cad-structure.md); this file only assembles them,
# adds the water volume (normal level 150 mm, translucent blue, separate part "water_volume") and keeps the old names (box, cyl, ... and the dimensions) for its users.
# The red "cart" stand-in box is gone: the real cart (cad/parts/cart.py) is placed on the track by cad/complete_unit.py.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parts.unit_dims import *   # noqa: F401,F403
from parts.common import box, cyl, tube, tdir   # noqa: F401
from parts.unit import unit_parts

PW_X, PD_Y, PT, TILT, ZPC = 450.0, 350.0, 25.0, 23.0, 2000.0
assy = cq.Assembly()
for _n, _s, _c in unit_parts():
    assy.add(_s, name=_n, color=cq.Color(*_c))
result = assy
