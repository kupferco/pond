# cad/render_transfer_hands.py: renders of the cart with BOTH transfer hands (hand C is the true mirror of hand B, Pond #227):
# at rest, and at the swing pose of each trip (release hand B and swing the plate on hinge C = trip up pipe C; release hand C and swing it on hinge B =
# trip up pipe B), each in a front, a top and an iso view. The swing pose is the end of the sim's swing path (control-ui/src/cart/transfer.ts SWING_PATH:
# plate 20 deg, released hand 9 deg on its own hinge, its jaw open 92 deg). Plate, battery, motors and the folded arm envelope turn with the plate.
# Run: python cad/render_transfer_hands.py   (writes renders/transfer_hands/*.png; needs cadquery, numpy, pillow)
import os
import sys
import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cart_assembly as ca
import cart_hinge as ch
import cart_sleeves as csl
from export_cart_v2_views import parts_of, render

OUT = os.path.join(HERE, "..", "renders", "transfer_hands")
SWING_DEG, OWN_DEG = 20.0, 9.0        # end of the sim's swing path (SWING_PATH in control-ui/src/cart/transfer.ts)
VIEWS = (("front", (0, -1, 0), (0, 0, 1)), ("top", (0, 0, 1), (0, 1, 0)), ("iso", (1, -1.1, 0.8), (0, 0, 1)))


def scene(static=None):
    """static: None (at rest) or "C" / "B": that hand stays clamped, the other is released and the plate swings on the static hinge."""
    rel = {"C": "B", "B": "C"}.get(static)
    a = csl.build_pair(static, SWING_DEG if static else 0.0, jaws={rel: csl.JAW_OPEN} if rel else None, own=OWN_DEG if static else 0.0)
    sgn = dict(csl.TAGS).get(static, 0)
    ax = ch.hinge_x(sgn) if sgn else 0.0
    for nm, shp, col in (("battery", ca.battery, (0.2, 0.45, 0.85, 1)), ("drive_motors", ca.motors, (0.85, 0.25, 0.25, 1)), ("arm_envelope", ca.arm, (0.88, 0.88, 0.9, 1))):
        a.add(shp.rotate((ax, 0, 0), (ax, 0, 1), sgn * SWING_DEG) if sgn else shp, name=nm, color=cq.Color(*col))
    return a


def main():
    os.makedirs(OUT, exist_ok=True)
    for tag, static in (("rest", None), ("swing-pipe-c", "C"), ("swing-pipe-b", "B")):
        parts = parts_of(scene(static))
        for view, cam, up in VIEWS:
            render(parts, cam, up, os.path.join(OUT, "mirror-hands-%s-%s.png" % (tag, view)))


if __name__ == "__main__":
    main()
