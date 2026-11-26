"""How deep the REAL cart CAD hangs under the track pipe when it rolls about the pipe, against the lid (OpenPocket #522 follow-up).

    pip install cadquery        # slow, heavy; the numbers it prints are stored in docs/pod-grab-reach/cad-depth-roll.json
    python3 sim/pod_grab_roll_cad_depth.py

Loads cad/water_assembly.py's cart scene (plate, sleeves, battery, sampler, the arm ENVELOPE of cart_arm/cart_assembly), takes every vertex in the plane across
the pipe and rolls it by 0..60 degrees. depth = how far below the pipe axis the vertex ends up; the lid top is 210 mm under the pipe (cad/layout.py).
The sim's own cart (plate and sleeve only) is in pod_grab_roll_check.py. Does not change any CAD file.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "cad"))
import water_assembly as wa  # noqa: E402

LID_GAP_BASE = 210.0   # cad/layout.py TRACK_BOTTOM_ABOVE_LID

cart = wa.scene("cart")
pts = {}
for ch in cart.children:
    for o in (ch.obj.vals() if hasattr(ch.obj, "vals") else [ch.obj]):
        o = o.moved(ch.loc) if ch.loc else o
        verts, _ = o.tessellate(1.0)
        pts.setdefault(ch.name, []).extend((v.y, -(v.x - wa.TRACK_X)) for v in verts)   # (out of the pipe plane, height under the pipe axis; negative = below)
out = {"note": "depth below the pipe axis (mm) of the lowest vertex per roll angle; gap = 210 - depth. + roll turns the plate down and back, as in pod_grab.py layout roll",
       "lowest_part_without_arm": {}, "arm_envelope_depth": {}}
for roll in range(0, 65, 5):
    a = math.radians(roll)
    depth = {n: -min(y * math.sin(a) + z * math.cos(a) for y, z in p) for n, p in pts.items()}
    worst = max((d, n) for n, d in depth.items() if "arm" not in n)
    out["lowest_part_without_arm"][roll] = {"part": worst[1], "depth_mm": round(worst[0], 1), "gap_to_lid_mm": round(LID_GAP_BASE - worst[0], 1)}
    arm = max((d, n) for n, d in depth.items() if "arm" in n)
    out["arm_envelope_depth"][roll] = {"part": arm[1], "depth_mm": round(arm[0], 1), "gap_to_lid_mm": round(LID_GAP_BASE - arm[0], 1)}
json.dump(out, open(os.path.join(HERE, "..", "docs", "pod-grab-reach", "cad-depth-roll.json"), "w"), indent=1)
for k, v in out["lowest_part_without_arm"].items():
    print(k, v, out["arm_envelope_depth"][k])
