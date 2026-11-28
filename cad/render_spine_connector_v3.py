# Renders for cad/spine_connector_v3.py (OpenPocket #581): four views (iso, front, top, side) and a GLB of the assembled connector.
# Usage: python cad/render_spine_connector_v3.py -> cad/renders/spine-connector-v3-*.png / .glb
import os
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import render_local as rl

OUT = os.path.join(HERE, "renders")
VIEWS = (("iso", 25, -50), ("front", 0, -90), ("top", 90, -90), ("side", 0, 0))
NAME = "spine-connector-v3"
NOTE = "Track axis 75 mm from the spine axis; rod reaches 59 mm past the track surface; growing pipe shown translucent"

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    assy = runpy.run_path(os.path.join(HERE, "spine_connector_v3.py"))["result"]
    parts = rl.collect(assy)
    for v, el, az in VIEWS:
        rl.draw(parts, el, az, os.path.join(OUT, "%s-%s.png" % (NAME, v)), "%s (%s)" % (NAME, v), NOTE)
    assy.export(os.path.join(OUT, NAME + ".glb"), tolerance=0.3, angularTolerance=0.2)
    print("wrote", NAME)
