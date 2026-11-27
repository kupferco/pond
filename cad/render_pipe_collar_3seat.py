# Renders for cad/pipe_collar_3seat.py (OpenPocket #563): four views (iso, front, top, side) and a GLB of each:
#   pipe-collar-3seat-piece      the one piece (seat at 0 degrees, tabs at -60 and +60) on the pipe
#   pipe-collar-3seat-assembled  the three pieces round the pipe and the spine, empty holes (top view = plan view of the reference drawing)
#   pipe-collar-3seat-pods       the same with a pod in every seat and one plug parked in the holder of seat 1
#   pipe-collar-3seat-exploded   the three pieces pulled 60 mm out along their seat directions
# Usage: python cad/render_pipe_collar_3seat.py -> cad/renders/pipe-collar-3seat-*.png / .glb
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import render_local as rl
import pipe_collar_3seat as p3

OUT = os.path.join(HERE, "renders")
VIEWS = (("iso", 25, -50), ("front", 0, -90), ("top", 90, -90), ("side", 0, 0))
SCENES = (
    ("pipe-collar-3seat-piece", dict(content="piece", with_spine=False), "One piece (printed three times): seat at 0 degrees, tabs at -60 and +60"),
    ("pipe-collar-3seat-assembled", dict(content="empty"), "Three identical pieces: seats at 0/120/240, magnet joints at 60/180/300"),
    ("pipe-collar-3seat-pods", dict(content="pods"), "A pod in every seat, one plug parked in the holder of seat 1"),
    ("pipe-collar-3seat-exploded", dict(content="empty", explode=p3.EXPLODE), "Exploded 60 mm along the seat directions"),
)

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name, kw, note in SCENES:
        assy = p3.scene(**kw)
        parts = rl.collect(assy)
        for v, el, az in VIEWS:
            rl.draw(parts, el, az, os.path.join(OUT, "%s-%s.png" % (name, v)), "%s (%s)" % (name, v), note)
        assy.export(os.path.join(OUT, name + ".glb"), tolerance=0.3, angularTolerance=0.2)
        print("wrote", name)
