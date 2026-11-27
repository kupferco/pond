# cad/spine_connector.py: the SPINE-TO-TRACK CONNECTOR (OpenPocket #561). The bracket that joins the central spine to the track.
# Until now the unit drew the track floating 60 mm in front of the growing pipe (only two 16 x 30 x 30 stand-in blocks, "spine_brackets", in
# cad/parts/unit_frame.py), and a pod place sat exactly where the bracket has to clamp onto the spine. This file is the real part.
#
# Built only from numbers that already exist (nothing new is invented; what is missing is marked ASSUMED below and listed in docs/spine-connector.md):
#   layout / unit:  cad/layout.json + cad/parts/unit_dims.py: spine 33.7 OD at x = y = 0, growing pipe 75 OD (3 mm wall), track pipe 32 OD at y = LOOP_Y = -60,
#                   bottom run z = ZB (layout), top run z = ZT, track_rod_out_mm (reach of the M8 rod).
#   track side:     the SAME M8 rod system as the flush track joint (cad/track_joint.py) and the track supports (cad/track_supports.py): nut plate
#                   inside the track pipe, rod out of the 8.5 mm hole on the spine side, lock nut on the pipe, then the bracket. Nut plate, lock nut and
#                   the numbers are taken from track_supports.py, not copied.
#   spine side:     a split ring clamped on the spine, 16 x 30 arm (the width and height of the stand-in blocks it replaces) through a window in the
#                   growing pipe to the rod.
# Where along the spine: one connector on each run of the track at x = 0, at the run's axis height (bottom z = ZB, top z = ZT), the places where
# the stand-in blocks already were. No pod place may occupy a connector position: check() lists every pod place that does today.
# This task does NOT change the complete unit or the pods (that is task 537): the scene here is a copy with the growing pipe windows cut.
#   python cad/spine_connector.py      -> check() report + cad/renders/spine-connector*.glb   (pictures: cad/render_spine_connector.py)
import os
import runpy
import sys

import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import layout as LAY
from parts.common import box, tube, inter, vol
from parts.unit import unit_parts
from parts.unit_dims import SP, GP, TR, LOOP_Y, ZB, ZT, RP
from parts.pods import pods_and_caps, POD_D

_ts = runpy.run_path(os.path.join(HERE, "track_supports.py"))     # the supports' nut plate, lock nut, rod numbers and the pipe-local -> run placing
RI, ROD_D, HOLE_D, LOCKNUT_H, ROD_X0 = (_ts[k] for k in ("RI", "ROD_D", "HOLE_D", "LOCKNUT_H", "ROD_X0"))

# --- numbers
SP_R = SP / 2                       # 16.85 spine
PIPE_IN = RP - 3.0                  # 34.5 growing pipe inside radius (parts/unit_frame.py: 3 mm wall)
ARM_W, ARM_H = 16.0, 30.0           # the stand-in blocks' width and height (unit_frame.spine_brackets)
RING_WALL = 6.0                     # ASSUMED: wall of the split ring on the spine
RING_H = 30.0                       # ASSUMED = ARM_H
SLIT = 2.0                          # ASSUMED: gap of the split ring (back, +Y side); the clamp screw across it is NOT drawn (open question)
WIN_PAD = 2.0                       # ASSUMED: air each side and above/below the arm in the growing pipe window
ARM_END_Y = LOOP_Y + TR + LOCKNUT_H # -37.5: arm face = track surface + the lock nut (same stack as the supports' posts)
ROD_IN_ARM = 8.0                    # the supports' rods end 8 mm inside the block: same here
TOUCH = 1.0                         # mm3: overlaps smaller than this are surface touching, not a pod in the way
ZONES = {"bottom": ZB, "top": ZT}   # connector positions on the spine (height over the tank floor, mm)


def connector_body(zc):
    """Split ring on the spine + the arm to the rod, for a connector whose rod axis is at height zc."""
    ro = SP_R + RING_WALL
    ring = tube(ro, SP_R, RING_H, 0, 0, zc - RING_H / 2).cut(box(SLIT, ro + 2, RING_H + 2, 0, ro / 2 + 0.5, zc - RING_H / 2 - 1))
    y0, y1 = ARM_END_Y, -(ro - 2.0)                                                    # from the lock nut face to 2 mm inside the ring wall
    arm = box(ARM_W, y1 - y0, ARM_H, 0, (y0 + y1) / 2, zc - ARM_H / 2)
    body = ring.union(arm)
    return body.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(HOLE_D / 2, ROD_IN_ARM + 2, cq.Vector(0, ARM_END_Y - 1, zc), cq.Vector(0, 1, 0))))


def connector_hardware(zc):
    """(nut plate inside the track pipe, M8 rod, lock nut) at height zc (x = 0, jaw side towards the spine)."""
    plate = _ts["to_run"](_ts["nut_plate"](), 0, zc)
    rod = _ts["to_run"](cq.Workplane("YZ").circle(ROD_D / 2).extrude((TR + LOCKNUT_H + ROD_IN_ARM) - ROD_X0).translate((ROD_X0, 0, 0)), 0, zc)
    nut = _ts["to_run"](_ts["locknut"](), 0, zc)
    return plate, rod, nut


def connector_window(zc):
    """The opening in the growing pipe's front wall the arm passes through (cut in the scene's copy of the pipe only)."""
    return box(ARM_W + 2 * WIN_PAD, 2 * RP, ARM_H + 2 * WIN_PAD, 0, -RP, zc - ARM_H / 2 - WIN_PAD)


def connector_envelope(zc):
    """Everything the connector fills: ring, arm, rod, nut and plate. A pod place that touches it is not allowed."""
    p, r, n = connector_hardware(zc)
    return connector_body(zc).union(p).union(r).union(n)


def connector_pod_conflicts(zc):
    """Pod places (simplified pod cups of cad/parts/pods.py) that touch the connector at height zc: [(centre z, overlap mm3)]."""
    env = connector_envelope(zc)
    pods, caps = pods_and_caps()
    out = []
    for s in list(pods.solids().vals()) + list(caps.solids().vals()):
        w = cq.Workplane("XY").add(s)
        v = inter(env, w)
        if v > TOUCH:
            out.append((round(s.Center().z, 1), round(v, 1)))
    return out


def connector_scene(cut_unit=True):
    """The unit's spine, growing pipe, track and pods, with both connectors and the pipe windows / track pockets they need.
    Returns (assembly, conflicting pod solids). A COPY: the unit parts themselves are not changed (task 537)."""
    a = cq.Assembly()
    parts = {n: (s, c) for n, s, c in unit_parts(water=False)}
    for n in ("spine_tube", "growing_pipe", "track_loop"):
        s, c = parts[n]
        if cut_unit:
            for zc in ZONES.values():
                if n == "growing_pipe":
                    s = s.cut(connector_window(zc))
                if n == "track_loop":
                    s = s.cut(_ts["to_run"](_ts["bore"](), 0, zc))
        a.add(s, name=n, color=cq.Color(*c))
    for k, zc in ZONES.items():
        plate, rod, nut = connector_hardware(zc)
        a.add(connector_body(zc), name="connector_%s_bracket" % k, color=cq.Color(0.95, 0.6, 0.2, 1))
        a.add(plate, name="connector_%s_nut_plate" % k, color=cq.Color(0.9, 0.2, 0.2, 1))
        a.add(rod, name="connector_%s_m8_rod" % k, color=cq.Color(0.3, 0.3, 0.3, 1))
        a.add(nut, name="connector_%s_lock_nut" % k, color=cq.Color(0.2, 0.7, 0.3, 1))
    pods, caps = pods_and_caps()
    bad, ok = [], []
    envs = [connector_envelope(zc) for zc in ZONES.values()]
    for s in list(pods.solids().vals()) + list(caps.solids().vals()):
        w = cq.Workplane("XY").add(s)
        (bad if any(inter(e, w) > TOUCH for e in envs) else ok).append(s)
    if ok:
        a.add(cq.Workplane("XY").add(cq.Compound.makeCompound(ok)), name="pod_places_free", color=cq.Color(0.24, 0.67, 0.31, 1))
    if bad:
        a.add(cq.Workplane("XY").add(cq.Compound.makeCompound(bad)), name="pod_places_IN_CONNECTOR_POSITION", color=cq.Color(0.85, 0.1, 0.1, 1))
    return a, bad


def check():
    """Fails (AssertionError) on a real fit problem; lists the pod places that must go (reported, not failed: removing them is task 537)."""
    msgs = []
    reach = ARM_END_Y + ROD_IN_ARM - (LOOP_Y + TR)                   # rod end past the track surface: 14.5
    assert reach <= LAY.TRACK_ROD_OUT, "rod needs %.1f mm out of the track pipe, layout allows %.1f" % (reach, LAY.TRACK_ROD_OUT)
    msgs.append("rod reach from the track surface %.1f mm <= track_rod_out_mm %.1f" % (reach, LAY.TRACK_ROD_OUT))
    ro = SP_R + RING_WALL
    assert ro < PIPE_IN - 4, "ring (r %.1f) does not fit inside the growing pipe (r %.1f)" % (ro, PIPE_IN)
    msgs.append("clamp ring r %.1f inside growing pipe r %.1f (%.1f mm air)" % (ro, PIPE_IN, PIPE_IN - ro))
    # arm against the spine tube and the track: touches nothing but its own ring and rod (the spine is clamped by the ring, not cut)
    a, bad = connector_scene()
    sp = {n: s for n, s, c in unit_parts(water=False)}
    for k, zc in ZONES.items():
        body = connector_body(zc)
        for other in ("spine_tube",):
            v = inter(body, sp[other])
            assert v < 1e-3, "%s connector bracket overlaps %s by %.2f mm3" % (k, other, v)
        gp = sp["growing_pipe"].cut(connector_window(zc))
        v = inter(body, gp)
        assert v < 1e-3, "%s connector bracket overlaps the growing pipe by %.2f mm3 (window too small)" % (k, v)
        tr = sp["track_loop"]
        v = inter(body, tr)
        assert v < 1e-3, "%s connector bracket overlaps the track pipe by %.2f mm3" % (k, v)
    msgs.append("brackets clear of the spine, the (windowed) growing pipe and the track pipe")
    conf = {k: connector_pod_conflicts(zc) for k, zc in ZONES.items()}
    return msgs, conf


if __name__ == "__main__":
    msgs, conf = check()
    for m in msgs:
        print("OK  ", m)
    for k, zc in ZONES.items():
        print("connector %-6s on the spine at z = %.0f mm (track axis z = %.0f, x = 0)" % (k, zc, zc))
        print("   pod places in the way (to be left out in task 537):", conf[k] or "none")
    a, bad = connector_scene()
    out = os.path.join(HERE, "renders")
    os.makedirs(out, exist_ok=True)
    a.export(os.path.join(out, "spine-connector-positions.glb"), tolerance=0.5, angularTolerance=0.3)
    print("wrote cad/renders/spine-connector-positions.glb;", len(bad), "pod solids in a connector position")
