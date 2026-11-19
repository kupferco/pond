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
TRAY_TOP = (0.1, -0.24, 0.3, 0.2, 0.2)      # from above on the tray with its 16 pods (the lid is drawn: the pods show through the pick holes)
TRAY_ISO = (0.1, -0.24, 0.25, 0.25, 0.2)
CART = (0.0, -0.2, 0.0, 0.45, 0.45)         # from above on the cart on leg A and the pipe: which way the arm faces
CART_FRONT = (0.0, 0.0, 0.85, 0.55, 0.45)


# the roll sweep round (OpenPocket #313): the ghost neighbour stands 0.75 m to the left (-y), so the pictures are framed on both units
GHOST = {"iso": (0.0, -0.35, 0.98, 1.45, 1.45), "front": (0.0, 0.0, 0.98, 0.75, 1.05), "side": (0.0, -0.35, 0.98, 0.9, 1.05), "top": (0.0, -0.35, 0.0, 0.55, 0.8)}


def sweep_main(src, out):
    R.FLOOR = (-0.7, 0.8, -1.3, 0.6)
    for stage, name in (("turn90", "reach-test-turn90-v1"), ("turn90-example", "reach-test-turn90-example-v1")):
        tris = json.load(open(os.path.join(src, stage + ".json")))
        for v, box in GHOST.items():
            R.draw(tris, v, box, os.path.join(out, f"{name}-{v}.png"))
        if stage == "turn90-example":
            R.draw(tris, "hole", (0.0, 0.0, 1.05, 0.4, 0.4), os.path.join(out, f"{name}-closeup.png"))


def main():
    src, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    if len(sys.argv) > 3 and sys.argv[3] == "sweep":
        return sweep_main(src, out)
    for stage, name in (("result", "reach-test-result-v3"), ("example", "reach-test-example-v3"), ("cart-asis", "reach-test-cart-asis-v3"), ("cart-rolled", "reach-test-cart-rolled-v3")):
        tris = json.load(open(os.path.join(src, stage + ".json")))
        if stage == "result":
            for v, box in FULL.items():
                R.draw(tris, v, box, os.path.join(out, f"{name}-{v}.png"))
            for v in ("pipe-front", "pipe-back", "pipe-left", "pipe-right"):
                R.draw(tris, v, PIPE, os.path.join(out, f"{name}-{v}.png"), px=900)
            R.draw(tris, "top", TRAY_TOP, os.path.join(out, f"{name}-tray-top.png"), px=900)
            R.draw(tris, "iso", TRAY_ISO, os.path.join(out, f"{name}-tray-iso.png"), px=900)
        elif stage == "example":
            for v, box in FULL.items():
                R.draw(tris, v, box, os.path.join(out, f"{name}-{v}.png"))
            R.draw(tris, "hole", (0.0, 0.0, 1.05, 0.4, 0.4), os.path.join(out, f"{name}-closeup.png"))
        else:
            R.draw(tris, "top", CART, os.path.join(out, f"{name}-top.png"))
            R.draw(tris, "front", CART_FRONT, os.path.join(out, f"{name}-front.png"))


if __name__ == "__main__":
    main()
