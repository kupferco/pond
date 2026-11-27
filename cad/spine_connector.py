# cad/spine_connector.py: the SPINE-TO-TRACK CONNECTOR (OpenPocket #561, redrawn in the follow-up of 27 Nov 2026 to match the approved sketch).
# It shows ONLY this, nothing else:
#   1. The real flush track joint of cad/track_joint.py, coloured as that script colours it: pipe stubs, joint tube, plugs, the curved nut plate with its
#      captive M8 nut INSIDE the 32 mm track pipe, the M8 rod through the pipe wall, the lock nut OUTSIDE. Nothing stands proud, so the cart sleeve passes.
#      The rod runs ROD_OUT (50 mm) past the track pipe surface, which is the axis of the central pipe (the spine).
#   2. The track pipe lies HORIZONTAL (along X); the rod is horizontal too (along Y); the spine is the vertical tube (along Z) the rod ends in.
#   3. PROPOSAL (the owner's idea, not from an existing drawing): the spine end of the rod is locked too, one M8 nut on each side of the spine tube wall
#      (outside and inside), so nothing spins.
# No collars, no pods, no clamp ring, no arm, no growing pipe. Anything that is missing is an open question in docs/spine-connector.md, not drawn.
#   python cad/spine_connector.py      -> check() report + cad/renders/spine-connector*.glb   (pictures: cad/render_spine_connector.py)
import math
import os
import runpy
import sys

import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import layout as LAY
from parts.unit_dims import SP, ZB, ZT

_tj = runpy.run_path(os.path.join(HERE, "track_joint.py"))        # the real joint: its parts, numbers and colours are taken from there, not copied
R, RI, ROD_D, ROD_OUT, HOLE_D = (_tj[k] for k in ("R", "RI", "ROD_D", "ROD_OUT", "HOLE_D"))
LOCKNUT_AF, LOCKNUT_H = _tj["LOCKNUT_AF"], _tj["LOCKNUT_H"]
JOINT_PARTS = [("pipe_a", (0.7, 0.7, 0.72)), ("pipe_b", (0.7, 0.7, 0.72)), ("joint_tube", (0.45, 0.6, 0.8)), ("plug_a", (0.95, 0.6, 0.2)),
               ("plug_b", (0.95, 0.6, 0.2)), ("nut_plate", (0.9, 0.2, 0.2)), ("m8_rod", (0.3, 0.3, 0.3)), ("lock_nut", (0.2, 0.7, 0.3))]

SP_R = SP / 2                       # 16.85 spine tube
SP_WALL = 2.0                       # spine tube wall (cad/parts/unit_frame.py spine_tube)
NUT_H = LOCKNUT_H                   # the proposal's two spine nuts are the same M8 nut as the lock nut
AXIS = R + ROD_OUT                  # 66: distance from the track pipe axis to the spine axis = where the rod ends
ZONES = {"bottom": ZB, "top": ZT}   # heights of the two track runs over the tank floor (layout); the joint is drawn once, at the origin
SPINE_LEN = 150.0                   # length of spine tube drawn round the rod (a cut-out section of the real spine, same OD and wall)


def to_horizontal(w):
    """The joint script has the pipe along Z and the rod along X. Turn x -> y, y -> z, z -> x: the pipe lies along X (horizontal), the rod along Y."""
    return w.rotate((0, 0, 0), (1, 1, 1), 120)


def hex_nut(x0, x1):
    """Hex M8 nut (13 AF) between rod positions x0 and x1 (joint frame, along the rod), flats facing the tube wall."""
    d = LOCKNUT_AF / math.cos(math.pi / 6)
    n = cq.Workplane("YZ").polygon(6, d).extrude(x1 - x0).translate((x0, 0, 0))
    return n.cut(cq.Workplane("YZ").circle(ROD_D / 2).extrude(x1 - x0 + 2).translate((x0 - 1, 0, 0)))


def spine_parts():
    """Spine side: the vertical tube with the rod hole (final frame), the outside nut and the inside nut (joint frame, along the rod)."""
    # the tube is built in the FINAL frame (the spine is vertical, along Z, at y = AXIS; the rod and the nuts are turned by to_horizontal)
    tube = cq.Workplane("XY").center(0, AXIS).circle(SP_R).circle(SP_R - SP_WALL).extrude(SPINE_LEN).translate((0, 0, -SPINE_LEN / 2))
    tube = tube.cut(cq.Workplane("XZ").circle(HOLE_D / 2).extrude(-(2 * SP_R + 4)).translate((0, AXIS - SP_R - 2, 0)))
    x_out = AXIS - SP_R                                  # outer surface of the near wall (track side)
    x_in = x_out + SP_WALL                               # inner surface of the near wall
    ri = SP_R - SP_WALL
    c = LOCKNUT_AF / math.cos(math.pi / 6) / 2           # nut corner radius
    sag = ri - math.sqrt(ri * ri - c * c)                # the inner wall curves away from a flat nut: keep it clear of the wall
    outside = hex_nut(x_out - NUT_H, x_out)
    inside = hex_nut(x_in + sag, x_in + sag + NUT_H)
    return tube, outside, inside, x_in + sag + NUT_H


def joint_assembly():
    """The scene: track joint (as track_joint.py) + the spine tube with the proposed nuts, all turned so the track is horizontal. Rod is cut at the spine axis."""
    a = cq.Assembly()
    src = {c.name: c for c in _tj["assy"].children}
    for n, col in JOINT_PARTS:
        shape = src[n].obj
        a.add(to_horizontal(shape), name=n, color=cq.Color(*col, 1))
    tube, outside, inside, nut_end = spine_parts()
    a.add(tube, name="spine_tube", color=cq.Color(0.55, 0.62, 0.7, 0.55))
    a.add(to_horizontal(outside), name="PROPOSAL_spine_nut_outside", color=cq.Color(0.2, 0.7, 0.3, 1))
    a.add(to_horizontal(inside), name="PROPOSAL_spine_nut_inside", color=cq.Color(0.2, 0.7, 0.3, 1))
    return a


def inter_vol(a, b):
    r = a.intersect(b)
    return sum(s.Volume() for s in r.solids().vals()) if r.solids().vals() else 0.0


def check():
    """Fails (AssertionError) on a real fit problem."""
    msgs = []
    assert ROD_OUT <= LAY.TRACK_ROD_OUT + 1e-9, "joint rod reach %.1f exceeds track_rod_out_mm %.1f" % (ROD_OUT, LAY.TRACK_ROD_OUT)
    msgs.append("rod reach from the track pipe surface %.1f mm = track_rod_out_mm %.1f; it ends on the spine axis (%.1f mm from the track axis)" % (ROD_OUT, LAY.TRACK_ROD_OUT, AXIS))
    tube, outside, inside, nut_end = spine_parts()
    ri = SP_R - SP_WALL
    assert nut_end < AXIS + ri, "inside nut does not fit in the spine tube"
    for n, s in (("outside nut", outside), ("inside nut", inside)):
        v = inter_vol(to_horizontal(s), tube)
        assert v < 1e-3, "%s overlaps the spine tube wall by %.2f mm3" % (n, v)
    rod_end = AXIS
    assert rod_end - (AXIS - SP_R) >= 2 * NUT_H, "rod too short for the nuts"
    msgs.append("spine end: nut outside the wall and nut inside the wall (%.1f mm tube wall between), rod ends on the spine axis, nuts clear of the wall" % SP_WALL)
    return msgs


def positions_scene():
    """Where the connectors sit: the spine and the track as in the unit, plus one plain flat ring marker per connector height. No pods, nothing else."""
    from parts.unit import unit_parts
    a = cq.Assembly()
    parts = {n: (s, c) for n, s, c in unit_parts(water=False)}
    for n in ("spine_tube", "track_loop"):
        s, c = parts[n]
        a.add(s, name=n, color=cq.Color(*c))
    for k, zc in ZONES.items():
        ring = cq.Workplane("XY").circle(SP_R + 20).circle(SP_R + 1).extrude(12).translate((0, 0, zc - 6))
        a.add(ring, name="marker_%s_connector" % k, color=cq.Color(0.85, 0.1, 0.1, 1))
    return a


if __name__ == "__main__":
    for m in check():
        print("OK  ", m)
    for k, zc in ZONES.items():
        print("connector %-6s: track run axis z = %.0f mm, spine axis x = 0 (same joint at both)" % (k, zc))
    a = joint_assembly()
    out = os.path.join(HERE, "renders")
    os.makedirs(out, exist_ok=True)
    a.export(os.path.join(out, "spine-connector.glb"), tolerance=0.3, angularTolerance=0.2)
    positions_scene().export(os.path.join(out, "spine-connector-positions.glb"), tolerance=0.5, angularTolerance=0.3)
    print("wrote cad/renders/spine-connector.glb, spine-connector-positions.glb")

