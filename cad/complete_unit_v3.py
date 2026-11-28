# cad/complete_unit_v3.py: COMPLETE UNIT V3 (OpenPocket #574). Builds docs/drawings/renders/complete-unit-v3.glb. Nothing is drawn here: every part is imported.
#   = complete unit V2 (cad/complete_unit.py scene) with three changes:
#   1. the pod-shaped stand-in blocks ("spine_brackets") where the track meets the spine are removed;
#   2. the real spine-to-track connector (cad/spine_connector.py: track joint tube, plugs, nut plate, M8 rod, lock nut, and the two spine nuts) is placed
#      at both track runs (bottom ZB, top ZT), track axis on the loop plane y = LOOP_Y, rod pointing at the spine;
#   3. the old simplified pods (round cylinders with black caps, cad/parts/pods.py) are replaced by the LATEST pod: pipe_collar.pod() as shown in the
#      three-seat collar drawing (draft V2, #563), in that drawing's colour pipe_collar.C_POD. Same holes as before (4 per level, same heights and angles).
#   python cad/complete_unit_v3.py   -> docs/drawings/renders/complete-unit-v3.glb   (check pictures: cad/render_glb_views.py)
import math
import os
import sys

import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import complete_unit as cu
import pipe_collar as pc
import spine_connector as sc
from parts.pods import hole_levels
from parts.unit_dims import LOOP_Y

OUT = os.path.join(HERE, "..", "docs", "drawings", "renders", "complete-unit-v3.glb")
CONNECTOR_PARTS = ("joint_tube", "plug_a", "plug_b", "nut_plate", "m8_rod", "lock_nut")   # the unit's own track_loop and spine_tube replace pipe_a/pipe_b/spine_tube
REPLACED = ("spine_brackets", "pods", "pod_caps")


def pods():
    """The latest pod, one per hole: seat 1 of the collar drawing is at +X, hole height pc.ZH; turned to each hole's angle and moved to its level."""
    out = None
    one = pc.pod()
    for i, z in enumerate(hole_levels()):
        for k in range(4):
            deg = 90 * k + 45 * (i % 2) + 45
            p = one.rotate((0, 0, 0), (0, 0, 1), deg).translate((0, 0, z - pc.ZH))
            out = p if out is None else out.union(p, clean=False)
    return out


def scene():
    old = cu.scene()
    a = cq.Assembly()
    for ch in old.children:
        if ch.name in REPLACED:
            continue
        a.add(ch.obj, name=ch.name, loc=ch.loc, color=ch.color)
    a.add(pods(), name="pods", color=cq.Color(*pc.C_POD))
    src = {c.name: c for c in sc.joint_assembly().children}
    cols = dict(sc.JOINT_PARTS)
    cols["PROPOSAL_spine_nut_outside"] = cols["PROPOSAL_spine_nut_inside"] = (0.2, 0.7, 0.3)
    tube, outside, inside, _ = sc.spine_parts()
    for zone, zc in sc.ZONES.items():
        move = lambda s: s.translate((0, LOOP_Y, zc))
        for n in CONNECTOR_PARTS:
            a.add(move(src[n].obj), name="spine_connector_%s_%s" % (zone, n), color=cq.Color(*cols[n], 1))
        for n, s in (("PROPOSAL_spine_nut_outside", outside), ("PROPOSAL_spine_nut_inside", inside)):
            a.add(move(sc.to_horizontal(s)), name="spine_connector_%s_%s" % (zone, n), color=cq.Color(*cols[n], 1))
    return a


if __name__ == "__main__":
    scene().export(OUT, tolerance=0.5, angularTolerance=0.3)
    print("wrote", os.path.relpath(OUT))
