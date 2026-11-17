# Pictures of the Reach test scene (software renderer of render_tris.py): the coloured result in iso / front / top / side, close-ups of the pipe with its 24 plugs and of the 4 x 4 seedling tray, and one
# example (a green pod reached by the arm). Usage: python3 scripts/render_reach.py TRI_DIR OUT_DIR
import json
import os
import sys

import render_tris as R

R.VIEWS["pipe-front"] = (-90.0, 6.0)      # from -y: the pipe's -y side, where the cart's arm works
R.VIEWS["pipe-back"] = (90.0, 6.0)       # from +y
R.VIEWS["pipe-left"] = (180.0, 6.0)     # from -x
R.VIEWS["pipe-right"] = (0.0, 6.0)      # from +x (the track side)

FULL = {"iso": (0.0, 0.1, 0.98, 1.2, 1.2), "front": (0.0, 0.0, 0.98, 0.75, 1.05), "side": (0.0, 0.0, 0.98, 0.6, 1.05), "top": (0.0, 0.0, 0.0, 0.5, 0.5)}
PIPE = (0.0, 0.0, 1.1, 0.3, 0.62)          # the pipe from the side, the holes between 0.65 and 1.56 m
TRAY_TOP = (-0.11, -0.23, 0.3, 0.2, 0.2)    # from above on the tray, the cart's arm beside it
TRAY_FRONT = (-0.1, -0.2, 0.45, 0.4, 0.33)


def main():
    src, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    for stage, name in (("result", "reach-test-result-v1"), ("example", "reach-test-pod-example-v1")):
        tris = json.load(open(os.path.join(src, stage + ".json")))
        for v, box in FULL.items():
            R.draw(tris, v, box, os.path.join(out, f"{name}-{v}.png"))
        if stage == "result":
            for v in ("pipe-front", "pipe-back", "pipe-left", "pipe-right"):
                R.draw(tris, v, PIPE, os.path.join(out, f"{name}-{v}.png"), px=900)
            R.draw(tris, "top", TRAY_TOP, os.path.join(out, f"{name}-tray-top.png"), px=900)
        else:
            R.draw(tris, "front", TRAY_FRONT, os.path.join(out, f"{name}-closeup.png"))


if __name__ == "__main__":
    main()
