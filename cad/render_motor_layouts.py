# cad/render_motor_layouts.py: before / after picture for OpenPocket #312 (cart motors inward, layout B, docs/plans/cart-motors-inward-plan.md).
# One hand on its pipe, motors as TODAY (beside the lobe on the plant side, pointing out sideways) and as LAYOUT B (plate side, body along the pipe
# / towards the plate). Views: iso, and looking along the pipe (the cross-section the plan's SVG shows). Writes cad/renders/cart-motors-before-after.png
# and cart-motors-before-*.png / cart-motors-after-*.png.  Usage: python cad/render_motor_layouts.py
import os
import sys
import cadquery as cq
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.image import imread
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import render_local as rl
import cart_omni as co
import hand_sleeve as hs
import cart_sleeves as cs

R = os.path.join(HERE, "renders")
MOTOR_KEYS = ("drive_gearbox", "drive_motor", "drive_shaft", "roll_gearbox", "roll_motor", "roll_shaft")


def hand(layout):
    parts = dict(cs.hand_parts())
    for k in MOTOR_KEYS:
        parts.pop(k, None)
    wy = hs.DRIVE_MOTOR_WALL_Y if layout == "B" else hs.ARM_W_OMNI / 2
    wz = -hs.SLEEVE_L / 2 - (hs.ROLL_MOTOR_WALL_Z if layout == "B" else 0.0)
    parts.update(co.drive_motor_parts(hs.DRIVE_Z, wy, hs.OUTER_ANG, layout=layout))
    parts.update(co.roll_motor_parts(hs.ROLL_Z, wz, hs.OUTER_ANG, layout=layout))
    a = cq.Assembly()
    a.add(cs.cyl(hs.R_PIPE, 250.0, "z", (0, 0, 0)), name="track_pipe", color=cq.Color(0.75, 0.78, 0.8, 1))
    for n, (s, col) in parts.items():
        a.add(s, name=n, color=cq.Color(*col))
    return a


if __name__ == "__main__":
    views = (("iso", 28, -55), ("top", 90, -90), ("side", 0, 0))
    for tag, layout, title in (("before", "today", "BEFORE: motors beside the lobe, out sideways"), ("after", "B", "AFTER (layout B): motors on the plate side, inward")):
        col = rl.collect(hand(layout))
        for v, el, az in views:
            rl.draw(col, el, az, os.path.join(R, "cart-motors-%s-%s.png" % (tag, v)), "%s (%s)" % (title, v))
            print("wrote", tag, v, flush=True)
    fig, axs = plt.subplots(len(views), 2, figsize=(12, 6 * len(views)))
    for j, tag in enumerate(("before", "after")):
        for i, (v, _, _) in enumerate(views):
            axs[i, j].imshow(imread(os.path.join(R, "cart-motors-%s-%s.png" % (tag, v)))); axs[i, j].axis("off")
    fig.suptitle("Hand with its drive and roll motors: before (left) and after, layout B (right). Top view: plants are up the page (+Y), plate down (-Y).", fontsize=12)
    fig.tight_layout(); fig.savefig(os.path.join(R, "cart-motors-before-after.png"), dpi=80)
    print("wrote cart-motors-before-after.png")
