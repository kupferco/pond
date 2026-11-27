# cad/parts/pod_collars.py: where the pods go on the central pipe, with the REAL pod collar (OpenPocket #537, follow-up of 27 Nov 2026). Replaces the generic
# pod places (cad/parts/pods.py: 4 plain cups per level) in the complete unit. Nothing is drawn here: the collar, its pod, the drilled hole and every collar
# number come from cad/pipe_collar.py; the heights, keep-out and zone come from cad/layout.json (via cad/layout.py).
# A pod collar is a clamshell round the WHOLE pipe, pipe_collar.H tall, with ONE pod seat (45 degrees up) and one plug holder: one pod place per collar, and two
# collars cannot share a height. The hole axis (+X in pipe_collar.py) is turned to -Y here, towards the track and the cart.
# No collar may reach into the keep-out round a spine-to-track connector (cad/spine_connector.py) or round a clamp collar of the frame.
import math
import os
import sys

import cadquery as cq

_CAD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _CAD)
import layout as LAY
import pipe_collar as pc
from .unit_dims import ZB, ZT, ZC1, ZC2

FACING_DEG = -90.0           # the collar's +X seat axis turned to -Y (the track side)
CONNECTOR_Z = (ZB, ZT)


def keepouts():
    """[(z_lo, z_hi, why)] over the tank floor where no pod collar may be."""
    k = [(z - LAY.CONNECTOR_KEEPOUT, z + LAY.CONNECTOR_KEEPOUT, "connector") for z in CONNECTOR_Z]
    k += [(ZC1 - LAY.CLAMP_COLLAR_KEEPOUT, ZC1 + LAY.CLAMP_COLLAR_KEEPOUT, "clamp collar"),
          (ZC2 - LAY.CLAMP_COLLAR_KEEPOUT, ZC2 + LAY.UPPER_CLAMP_LEGS_KEEPOUT, "upper clamp collar and its top triangle legs")]
    return sorted(k)


def collar_bottoms():
    """Bottom edge z of every pod collar: stacked from the first pod hole (layout POD_ZONE_BOTTOM) as close as the collar allows (collar height + gap), jumping over
    the keep-outs, up to the last pod hole (POD_ZONE_TOP). This is what the real collar ALLOWS, not a chosen count (docs/layout.md, open question)."""
    out, zb = [], LAY.POD_ZONE_BOTTOM - pc.ZH
    ko = keepouts()
    while zb + pc.ZH <= LAY.POD_ZONE_TOP + 1e-9:
        hit = [k for k in ko if zb < k[1] and zb + pc.H > k[0]]
        if hit:
            zb = max(k[1] for k in hit)
            continue
        out.append(zb)
        zb += pc.H + LAY.POD_COLLAR_GAP
    return out


def hole_heights():
    return [zb + pc.ZH for zb in collar_bottoms()]


def old_pod_places():
    """The generic pod places this replaces (cad/parts/pods.py): (count, heights of the levels, number of places inside a connector keep-out)."""
    from .pods import hole_levels
    lv = hole_levels()
    clash = [z for z in lv if any(abs(z - c) <= LAY.CONNECTOR_KEEPOUT for c in CONNECTOR_Z)]
    return 4 * len(lv), lv, 4 * len(clash)


def collar_parts():
    """The collar's parts in pipe_collar.py's own frame (pipe axis Z, collar bottom z = 0, seat axis +X) as [(name, shape, rgba)], with the pod seated."""
    front, back = pc.collar_halves()
    parts = [("collar_front_half", front, pc.C_COLLAR), ("collar_back_half", back, pc.C_BACK), ("hinge_pin", pc.pin(), pc.C_METAL)]
    for i, z in enumerate(pc.MAG_ZS):
        parts.append(("magnet_front_%d" % (i + 1), pc.magnet(1, z), pc.C_MAG_N if i == 0 else pc.C_MAG_S))
        parts.append(("magnet_back_%d" % (i + 1), pc.magnet(-1, z), pc.C_MAG_S if i == 0 else pc.C_MAG_N))
    parts += [("gasket_EPDM", pc.gasket(), pc.C_SEAL), ("seat_oring_24x2", pc.seat_orings(), pc.C_SEAL), ("pod", pc.pod(), pc.C_POD)]
    return parts


def location(zb):
    return cq.Location(cq.Vector(0, 0, zb), cq.Vector(0, 0, 1), FACING_DEG)


def drill_holes(z_holes):
    """The 45 mm holes drilled through the FRONT wall of the central pipe (square to it, towards -Y), one per collar, as one solid to cut from the pipe."""
    cut = None
    for z in z_holes:
        c = cq.Workplane("XZ").circle(pc.DRILL_D / 2).extrude(pc.RP + 5).translate((0, 0, z))     # XZ extrudes towards -Y
        cut = c if cut is None else cut.union(c)
    return cut


def add_collars(assembly, prefix="podcollar"):
    """Add every collar (shared shapes, one location each) to a cq.Assembly."""
    parts = collar_parts()
    for i, zb in enumerate(collar_bottoms()):
        for n, s, col in parts:
            assembly.add(s, name="%s_%02d_%s" % (prefix, i + 1, n), color=cq.Color(*col), loc=location(zb))
