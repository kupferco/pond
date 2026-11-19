# cad/water_assembly.py: the FULL assembly with the water sampling in it (OpenPocket #330 follow-up, 19 Nov 2026).
# The whole cart of cart_assembly.py (layout B from #312 is whatever cart_assembly.py draws on main: not changed here), plus the cart's water sampler
# (water_sampler.py), plus the first unit's lid corner with the shared water testing station and the unit's passive socket (water_station.py).
# The two files use different frames, so the unit is moved into the cart frame by ONE rigid move (a proper rotation, no mirroring):
#   unit track bottom run (along X at y = -60, z = 450) becomes the cart's pipe C (along Z at x = +60, y = 0), dock (unit x = 100) at cart z = 0,
#   unit "down" (-Z, towards the lid) becomes cart +X (outward, away from the cart centre), unit "inboard" (+Y) becomes cart +Y (the side AWAY from the plate).
# The cart's own pipe stub stands in for the unit's track, so the unit's track pieces and ground are left out here.
# This is only a drawing of where the parts sit relative to each other; it does not say the cart can drive there or the arm can reach.
import os
import sys
import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cart_assembly as ca
import water_sampler as wsa
import water_station as ws

MOVE = dict(rot=-90.0, shift=(60.0 + 450.0, 60.0, -ws.DOCK_X))
SKIP = ("track_bottom_run", "track_corner", "dock_plate_minus", "dock_plate_plus", "ground")


ROLL_DEG = 0.0    # turn of the unit about the track axis. 0 keeps the layout of the earlier rounds (lid outward, station on the arm's side of the cart).
                  # Finding (see README / PR): main's clamp C-gap faces the plate (-X) but the #315 rods leave the track on the unit's spine side (+Y here), so at roll 0
                  # the CLOSED jaw overlaps the rod at the dock. Only ROLL_DEG = 90 gives zero rod/nut vs clamp overlap (every other 30 deg step: 696 to 1809 mm3), but it moves the
                  # unit to the +Y side, over the empty pipe-B side, so it is NOT applied without the owner's say-so.


def to_cart(shape):
    return shape.rotate((0, 0, 0), (0, 1, 0), MOVE["rot"]).translate(MOVE["shift"]).rotate((60, 0, 0), (60, 0, 1), ROLL_DEG)


def track_support_parts():
    """Main's #315 track supports on the bottom run (nut plate, M8 rod, lock nut, post, base plate) inside the station window, UNIT frame.
    The unit's track loop itself is NOT taken: the cart's pipe stub is the one and only track pipe in this assembly."""
    import runpy
    ts = runpy.run_path(os.path.join(HERE, "track_supports.py"))
    out = {}
    for ch in ts["result"].children:
        if not (ch.name.startswith("support_") or ch.name.startswith("bottom_support")):
            continue
        t = ch.obj.intersect(ws.WIN)
        if t.solids().vals():
            out[ch.name] = (t, ch.color.toTuple())
    return out


def unit_parts(door_on=True, cutaway=False, lid_only=False, dy=None):
    """name -> (shape in the cart frame, colour): lid corner, station, unit socket."""
    p = {}
    for n, (s, c) in ws.context_parts().items():
        if n not in SKIP:
            if n == "tank" and lid_only:                                   # pictures only: the tank is left out (seen from the cart it is a wall that hides the station)
                continue
            p[n] = (to_cart(s), c)
    for n, (s, c) in track_support_parts().items():
        p[n] = (to_cart(s), c)
    for n, (s, c) in ws.station_parts(door_on, cutaway, dy=dy).items():
        p[n] = (to_cart(s), c)
    for n, (s, c) in ws.unit_socket().items():
        p[n] = (to_cart(s), c)
    return p


def scene(kind="full", door_on=True, cutaway=False, lid_only=False):
    """kind: 'full' (cart + sampler + unit corner + station), 'cart' (cart + sampler only)."""
    a = cq.Assembly()
    for ch in ca.result.children:                      # ONE track pipe only: pipe C of main's cart_assembly.py IS the unit's track (the #315 supports sit on it, see check()).
        if ch.name == "track_pipe_B" or ch.name.startswith("hand_on_pipe_B_"):   # Pipe B is the neighbouring unit's track (not drawn), so the clamp that grips it is left out too: no clamp hangs in the air
            continue
        # flat copy of the cart's parts (a nested assembly would not render in render_local.collect)
        a.add(ch.obj, name="cart_" + ch.name, loc=ch.loc, color=ch.color)
    for n, (s, c) in wsa.parts().items():
        a.add(s, name=n, color=cq.Color(*c))
    if kind == "full":
        for n, (s, c) in unit_parts(door_on, cutaway, lid_only).items():
            a.add(s, name=n, color=cq.Color(*c))
    return a


def track_check(up):
    """The one track pipe is main's cart pipe C. Checks: it is where the unit's track maps to; clamp C touches it with no gap and no clash;
    the #315 supports sit on it; nothing is left of pipe B or its clamp in the scene."""
    out = {}
    pipe = {ch.name: ch for ch in ca.result.children}["track_pipe_C"].obj
    pb = pipe.val().BoundingBox()
    out["track_pipe_axis_xy_mm"] = ((pb.xmin + pb.xmax) / 2, (pb.ymin + pb.ymax) / 2)
    tr = to_cart(cq.Workplane("XY").add(cq.Vector(0, ws.TRACK_Y, ws.TRACK_Z)).val() if False else cq.Workplane("XY").sphere(0.1).translate((0, ws.TRACK_Y, ws.TRACK_Z)))
    tb = tr.val().BoundingBox()
    out["unit_track_axis_maps_to_xy_mm"] = ((tb.xmin + tb.xmax) / 2, (tb.ymin + tb.ymax) / 2)
    out["pipe_vs_unit_track_axis_offset_mm"] = round(((pb.xmin + pb.xmax) / 2 - (tb.xmin + tb.xmax) / 2) ** 2 + ((pb.ymin + pb.ymax) / 2 - (tb.ymin + tb.ymax) / 2) ** 2, 6) ** 0.5
    pipe_s = cq.Compound.makeCompound(pipe.solids().vals())
    clamp_gap, clamp_clash = {}, {}
    for nm, shp, col in ca.clamp_hand_parts():
        h = ca.csl.place_hand(shp, 1)
        clamp_gap[nm] = round(cq.Compound.makeCompound(h.solids().vals()).distance(pipe_s), 2)
        v = ws.inter(h, pipe)
        if v > 1e-3:
            clamp_clash[nm] = round(v, 2)
    out["clamp_C_gap_to_pipe_mm (0 = touching)"] = clamp_gap
    out["clamp_C_vs_pipe_clash_mm3"] = clamp_clash
    sg, sc = {}, {}
    for n, (s, c) in up.items():
        if n.startswith("support_") or n.startswith("bottom_support"):
            sg[n] = round(cq.Compound.makeCompound(s.solids().vals()).distance(pipe_s), 2)
            v = ws.inter(s, pipe)
            if v > 1e-3:
                sc[n] = round(v, 2)
    out["track_support_gap_to_pipe_mm (rod/nut touch, post is 34 mm out on the rod)"] = sg
    out["track_support_vs_pipe_clash_mm3 (nut plate/rod sit in the pipe bore in real life)"] = sc
    scn = scene("full")
    out["pipes_in_scene"] = [n for n in (c[0] for c in scn.traverse()) if "track_pipe" in n] if False else sorted(c.name for c in scn.children if "track_pipe" in c.name)
    out["pipe_B_clamp_parts_in_scene"] = sum(1 for c in scn.children if c.name.startswith("cart_hand_on_pipe_B_"))
    return out


def check(dy=None):
    out = {}
    up = unit_parts(True, False, dy=dy)
    st = {n: v for n, v in up.items() if n.startswith("ws_") or n.startswith("unit_")}
    ctx = {n: v for n, v in up.items() if n not in st}
    out["dock_x_unit_maps_to_cart_z_mm"] = 0.0
    # nozzle parked on the cart vs the station: nothing overlaps
    cart_things = {n: s for n, (s, c) in wsa.parts().items()}
    clash = {}
    for n, (s, c) in st.items():
        for m, o in cart_things.items():
            v = ws.inter(s, o)
            if v > 1e-3:
                clash["%s vs %s" % (n, m)] = round(v, 2)
    out["station_vs_sampler_clashes_mm3"] = clash
    hits = {}
    for nm, shp, col in ca.clamp_hand_parts():
        for side, sgn in (("C", 1),):                 # hand B is not drawn (pipe B is the neighbour unit's track)
            h = ca.csl.place_hand(shp, sgn)
            for n, (s, c) in up.items():
                if n in ("tank", "lid_bar", "lid_back_strut", "seedling_storage", "growing_pipe") or n.startswith("brace"):
                    continue
                v = ws.inter(s, h)
                if v > 1e-3:
                    hits["%s vs hand_%s_%s" % (n, side, nm)] = round(v, 2)
    out["station_vs_cart_hands_clashes_mm3"] = hits
    pl = {}
    for n, (s, c) in st.items():
        for m, o in (("base_plate", ca.plate), ("battery", ca.battery), ("arm", ca.arm)):
            v = ws.inter(s, o)
            if v > 1e-3:
                pl["%s vs %s" % (n, m)] = round(v, 2)
    out["station_vs_plate_battery_arm_clashes_mm3"] = pl
    out.update(track_check(up))
    bb = wsa.parts()["sampler_nozzle"][0].val().BoundingBox()
    sk = up["ws_socket"][0].val().BoundingBox()
    out["parked_nozzle_xyz_mm"] = ((bb.xmin + bb.xmax) / 2, (bb.ymin + bb.ymax) / 2, bb.zmax)
    out["test_socket_mouth_xyz_mm"] = ((sk.xmin + sk.xmax) / 2, (sk.ymin + sk.ymax) / 2, sk.xmax)
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(check(), indent=1, default=str))
