# cad/render_unit_views.py: the whole unit (unit_v3_aframe.py) on the shared layout, with the water in the tank (OpenPocket #364).
#   cad/renders/unit-v3-{iso,front,top,side}.png        the whole unit, tank see-through with the water (translucent blue part "tank_water")
#   cad/renders/unit-v3-lower-{iso,front,top,side}.png   the same, only the part under 760 mm: tank, water, lid, bottom track run, the cart's block on the track
#   cad/renders/unit-v3.glb                              the unit, upright (Z up in the CAD = glTF +Y)
# Usage: python cad/render_unit_views.py
import os
import runpy
import sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import render_local as rl

R = os.path.join(HERE, "renders")
VIEWS = (("iso", 28, -50), ("front", 0, -90), ("top", 90, -90), ("side", 0, 0))

if __name__ == "__main__":
    unit = runpy.run_path(os.path.join(HERE, "unit_v3_aframe.py"))["result"]
    unit.export(os.path.join(R, "unit-v3.glb"), tolerance=0.5, angularTolerance=0.3)
    print("wrote unit-v3.glb", flush=True)
    parts = rl.collect(unit)
    lower = []
    for T, c in parts:
        T2 = T[T[:, :, 2].max(axis=1) < 760.0]
        if len(T2):
            lower.append((T2, c))
    for name, ps, title in (("unit-v3", parts, "Unit v3 on the shared layout: tank with water, bottom track run 210 mm over the lid"),
                            ("unit-v3-lower", lower, "Unit v3, lower part: tank with water, lid, bottom track run, cart on the track")):
        for v, el, az in VIEWS:
            rl.draw(ps, el, az, os.path.join(R, "%s-%s.png" % (name, v)), "%s (%s)" % (title, v))
            print("wrote", name, v, flush=True)
