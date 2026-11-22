# cad/water_assembly.py: the FULL assembly with the water sampling in it (OpenPocket #330 follow-up, 19 Nov 2026).
# The whole cart of cart_assembly.py (layout B from #312 is whatever cart_assembly.py draws on main: not changed here), plus the cart's water sampler
# (water_sampler.py), plus the first unit's lid corner with the shared water testing station and the unit's passive socket (water_station.py).
# The two files use different frames, so the unit is moved into the cart frame by ONE rigid move (a proper rotation, no mirroring):
#   unit track bottom run (along X at y = -60, z = 450) becomes the cart's pipe B (along Z at x = -60, y = 0), dock (unit x = 100) at cart z = 0,
#   unit "down" (-Z, towards the lid) becomes cart +X (towards the other sleeve and past it), unit "inboard" (+Y) becomes cart +Y (the side AWAY from the plate).
# 19 Nov follow-up 2 (owner): the cart clamps the track with the TOP sleeve (hand B, the upper one when the unit stands upright, lid below), and that sleeve is back.
# Before, the track was pipe C and only the bottom sleeve (hand C) was drawn, clamped on it. Now hand B is closed on the track and the bottom sleeve (hand C) is
# NOT drawn: pipe C, 120 mm below the track, is at the height of the lid, the #315 posts and the station box (unit z 330), so a bottom sleeve there would sit inside them
# (check() measures it: "bottom_sleeve_open_vs_unit_mm3"). Its pipe would be the neighbour unit's track, which is not drawn either, so no clamp hangs in the air.
# The cart carries no pipe (#447): the track here is the unit's own track_loop (cad/parts/track.py), cropped to the station window. The dock plates and the ground are left out.
# This is only a drawing of where the parts sit relative to each other; it does not say the cart can drive there or the arm can reach.
import os
import sys
import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cart_assembly as ca
import layout as LAY
from parts.cart import add_cart
import water_sampler as wsa
import water_station as ws

TRACK_X = -60.0                     # the track is pipe B, the top one
MOVE = dict(rot=-90.0, shift=(LAY.TRACK_BOTTOM_Z + TRACK_X, 60.0, -ws.DOCK_X))   # #364: the track is at the shared layout height (was 450)
SKIP = ("dock_plate_minus", "dock_plate_plus", "ground")


OPEN_DEG = ca.csl.JAW_OPEN   # jaw angle of the free (bottom) sleeve, fully released
ROLL_DEG = 0.0    # turn of the unit about the track axis. 0 keeps the layout of the earlier rounds (lid outward, station on the arm's side of the cart).
                  # Finding (see README / PR): main's clamp C-gap faces the plate (-X) but the #315 rods leave the track on the unit's spine side (+Y here), so at roll 0
                  # the CLOSED jaw overlaps the rod at the dock. Only ROLL_DEG = 90 gives zero rod/nut vs clamp overlap (every other 30 deg step: 696 to 1809 mm3), but it moves the
                  # unit to the +Y side, over the empty pipe-B side, so it is NOT applied without the owner's say-so.


def to_cart(shape):
    return shape.rotate((0, 0, 0), (0, 1, 0), MOVE["rot"]).translate(MOVE["shift"]).rotate((TRACK_X, 0, 0), (TRACK_X, 0, 1), ROLL_DEG)


def track_support_parts():
    """Main's #315 track supports on the bottom run (nut plate, M8 rod, lock nut, post, base plate) inside the station window, UNIT frame.
    The unit's track loop itself comes from scene_parts() (context_parts), the one and only track pipe in this assembly."""
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


def scene_parts(door_on=True, cutaway=False, lid_only=False, dy=None):
    """name -> (shape in the cart frame, colour): lid corner, station, unit socket."""
    p = {}
    for n, (s, c) in ws.context_parts().items():
        if n not in SKIP:
            if n in ("tank", "water_volume", "lid") and lid_only:                                   # pictures only: the tank is left out (seen from the cart it is a wall that hides the station)
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
    # ONE track pipe only: pipe B (the top one) of the cart IS the unit's track (the #315 supports sit on it, see check()). Pipe C would be the neighbour unit's
    # track (not drawn) and its hand is left out too, see the note at the top and check(). The cart comes from cad/parts/cart.py (not copied here).
    add_cart(a, "cart_", drop_pipe="C", drop_hand=True)   # the water-station pictures and the #364 tank clearance are for the top sleeve only (see the note above)

    for n, (s, c) in wsa.parts().items():
        a.add(s, name=n, color=cq.Color(*c))
    if kind == "full":
        for n, (s, c) in scene_parts(door_on, cutaway, lid_only).items():
            a.add(s, name=n, color=cq.Color(*c))
    return a


def track_check(up):
    """The one track pipe is main's cart pipe C. Checks: it is where the unit's track maps to; clamp C touches it with no gap and no clash;
    the #315 supports sit on it; nothing is left of pipe B or its clamp in the scene."""
    out = {}
    # the unit's track (cad/parts/track.py), its straight bottom run (|x| <= 140, where the corners start), moved into the cart frame
    pipe = to_cart(ws.context_parts()["track_loop"][0].intersect(ws.box(-140.0, 140.0, -200.0, 200.0, 0.0, 2000.0)))
    pb = pipe.val().BoundingBox()
    out["track_pipe_axis_xy_mm"] = ((pb.xmin + pb.xmax) / 2, (pb.ymin + pb.ymax) / 2)
    tr = to_cart(cq.Workplane("XY").add(cq.Vector(0, ws.TRACK_Y, ws.TRACK_Z)).val() if False else cq.Workplane("XY").sphere(0.1).translate((0, ws.TRACK_Y, ws.TRACK_Z)))
    tb = tr.val().BoundingBox()
    out["unit_track_axis_maps_to_xy_mm"] = ((tb.xmin + tb.xmax) / 2, (tb.ymin + tb.ymax) / 2)
    out["pipe_vs_unit_track_axis_offset_mm"] = round(((pb.xmin + pb.xmax) / 2 - (tb.xmin + tb.xmax) / 2) ** 2 + ((pb.ymin + pb.ymax) / 2 - (tb.ymin + tb.ymax) / 2) ** 2, 6) ** 0.5
    pipe_s = cq.Compound.makeCompound(pipe.solids().vals())
    clamp_gap, clamp_clash = {}, {}
    for nm, shp, col in ca.clamp_hand_parts():
        h = ca.csl.place_hand(shp, -1)
        clamp_gap[nm] = round(cq.Compound.makeCompound(h.solids().vals()).distance(pipe_s), 2)
        v = ws.inter(h, pipe)
        if v > 1e-3:
            clamp_clash[nm] = round(v, 2)
    out["clamp_B_top_sleeve_gap_to_track_pipe_mm (0 = touching)"] = clamp_gap
    out["clamp_B_top_sleeve_vs_track_pipe_clash_mm3"] = clamp_clash
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
    out["pipes_in_scene"] = sorted(c.name for c in scn.children if "track_pipe" in c.name or c.name == "track_loop")
    out["top_sleeve_parts_in_scene (closed on the track)"] = sum(1 for c in scn.children if c.name.startswith("cart_hand_on_pipe_B_"))
    out["bottom_sleeve_parts_in_scene (not drawn)"] = sum(1 for c in scn.children if c.name.startswith("cart_hand_on_pipe_C"))
    out["top_sleeve_x_mm / bottom_sleeve_x_mm"] = (ca.csl.HAND_X * -1, ca.csl.HAND_X)
    out["top_sleeve_closed_axis_is_the_track (axis x mm)"] = TRACK_X
    return out


def cart_tank_check(positions=(-140.0, -70.0, 0.0, 100.0, 140.0)):
    """OpenPocket #364: the cart, and everything mounted on it (plate, battery, arm, hands, motors, pump, coil, tube, nozzle, parking block), must not touch the tank
    anywhere along the track. The cart hangs under the bottom run with the top sleeve closed on the track (roll 0), so its depth under the track axis is constant along the
    straight run (|x| <= 140; past that the track curves UP, away from the tank). The shared layout (layout.json) says how deep the cart may be (cart_below_track_mm) and how
    much air there is under it (cart_clearance_mm, ASSUMED). This measures the REAL cart: lowest point of every part, a real boolean intersection with the tank (shell, lid
    and the water) wherever a part comes within 60 mm of it, at each dock position, and fails (AssertionError) on any contact or if the cart is deeper than the layout allows."""
    out = {}
    cart = scene("cart")
    parts = []
    for ch in cart.children:
        for o in (ch.obj.vals() if hasattr(ch.obj, "vals") else [ch.obj]):
            parts.append((ch.name, o.moved(ch.loc) if ch.loc else o))
    tank = {n: s for n, (s, c) in ws.context_parts().items() if n in ("tank", "tank_water")}
    tank_c = {n: to_cart(s) for n, s in tank.items()}              # tank, lid and water in the CART frame (unit -> cart)
    lid_c = to_cart(cq.Workplane("XY").box(2, 2, 0.1, centered=(True, True, False)).translate((0, 0, LAY.LID_TOP - 0.1)))
    lid_x = lid_c.val().BoundingBox().xmax                        # cart x of the lid top plane (the tank is at x >= this; unit z decreases with cart x)
    lowest_x, lowest_name = max(((p.BoundingBox().xmax, n) for n, p in parts))
    track_x = TRACK_X
    out["cart_deepest_part"] = lowest_name
    out["cart_depth_under_track_axis_mm (real CAD)"] = round(lowest_x - track_x, 2)
    out["layout_cart_below_track_mm (layout.json)"] = LAY.CART_BELOW_TRACK
    out["layout_track_bottom_z_mm / lid_top_z_mm"] = (LAY.TRACK_BOTTOM_Z, LAY.LID_TOP)
    out["gap_lowest_cart_part_to_lid_mm"] = round(lid_x - lowest_x, 2)
    out["gap_assumed_in_layout_mm (ASSUMED)"] = LAY.CART_CLEARANCE
    assert lowest_x - track_x <= LAY.CART_BELOW_TRACK + 1e-6, "the cart is deeper under the track (%.1f mm) than layout.json says (%.1f mm): raise cart_below_track_mm" % (lowest_x - track_x, LAY.CART_BELOW_TRACK)
    clash = {}
    near = [(n, p) for n, p in parts if lid_x - p.BoundingBox().xmax < 60.0]
    for pos in positions:                                         # dock positions along the straight run (unit x); the cart moves along cart z
        dz = pos - ws.DOCK_X
        for n, p in near:
            q = p.translate(cq.Vector(0, 0, dz))
            for tn, t in tank_c.items():
                v = ws.inter(cq.Workplane("XY").add(q), t)
                if v > 1e-3:
                    clash["%s vs %s at x=%g" % (n, tn, pos)] = round(v, 2)
    out["cart_parts_within_60mm_of_the_lid"] = sorted(n for n, p in near)
    out["positions_checked_along_the_run_x_mm"] = list(positions)
    out["cart_vs_tank_clash_mm3 (must be empty)"] = clash
    assert not clash, "the cart or something mounted on it intersects the tank: %s" % clash
    assert lid_x - lowest_x > 0, "the cart reaches the lid plane"
    return out


def arm_reach_check(dy=None):
    """Arm reach (cart_arm.py, REACH 350 from the shoulder) to the three places the gripper must go: the parked nozzle, the unit's lid socket, the station socket.
    Only the end point is tested (solve_pose over gripper angles 0..180); the path between them and the recoil tube's stretch (up to about 2 m) are not."""
    import math
    import cart_arm as carm
    dy = ws.OFF_Y if dy is None else dy
    park = wsa.parts()["sampler_nozzle"][0].val().BoundingBox()
    pts = {"parked_nozzle_collar": ((park.xmin + park.xmax) / 2, (park.ymin + park.ymax) / 2, park.zmin + wsa.wc.COLLAR_L / 2)}
    for nm, p in (("unit_lid_socket", (ws.UNIT_SOCKET[0], ws.UNIT_SOCKET[1], ws.LID + 40.0)), ("station_socket", (ws.CX, ws.CY + dy, ws.SOCKET_Z_TOP))):
        b = to_cart(cq.Workplane("XY").box(0.01, 0.01, 0.01).translate(p)).val().BoundingBox()
        pts[nm] = ((b.xmin + b.xmax) / 2, (b.ymin + b.ymax) / 2, (b.zmin + b.zmax) / 2)
    out = {}
    for nm, c in pts.items():
        ok = []
        for a3 in range(0, 181, 5):
            try:
                carm.solve_pose(c, a3_deg=a3)
                ok.append(a3)
            except ValueError:
                pass
        out[nm] = {"cart_xyz_mm": tuple(round(v, 1) for v in c), "shoulder_to_point_mm": round(math.dist(c, carm.S_CART), 1),
                   "percent_of_reach": round(100 * math.dist(c, carm.S_CART) / carm.REACH), "gripper_angles_that_work_deg": (min(ok), max(ok)) if ok else None, "reachable": bool(ok)}
    return out


def check(dy=None):
    out = {}
    out["arm_reach_to_sampler_points"] = arm_reach_check(dy)
    up = scene_parts(True, False, dy=dy)
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
        for side, sgn in (("B", -1),):                # B = top sleeve closed on the track
            h = ca.csl.place_hand(shp, sgn)
            for n, (s, c) in up.items():
                if n in ("tank", "water_volume", "lid", "base_bar_and_lid_plates", "seedling_storage", "shelf", "growing_pipe", "lower_aframe_and_back_strut_16mm"):
                    continue
                v = ws.inter(s, h)
                if v > 1e-3:
                    hits["%s vs hand_%s_%s" % (n, side, nm)] = round(v, 2)
    out["station_vs_cart_hands_clashes_mm3"] = hits
    cs = {}                                       # info only: the bottom sleeve (hand C, jaw released) is where the unit's lid parts are, which is why it is not drawn
    open_parts = {k: sh for k, sh, _ in ca.clamp_hand_parts(OPEN_DEG)}
    for n, (s, c) in up.items():
        if n in ("tank", "water_volume", "lid", "base_bar_and_lid_plates", "seedling_storage", "shelf", "growing_pipe", "lower_aframe_and_back_strut_16mm"):
            continue
        v = sum(ws.inter(s, ca.csl.place_hand(sh, 1)) for sh in open_parts.values())
        if v > 1e-3:
            cs[n] = round(v, 1)
    out["bottom_sleeve_open_vs_unit_mm3 (not drawn)"] = cs
    pl = {}
    for n, (s, c) in st.items():
        for m, o in (("base_plate", ca.plate), ("battery", ca.battery), ("arm", ca.arm)):
            v = ws.inter(s, o)
            if v > 1e-3:
                pl["%s vs %s" % (n, m)] = round(v, 2)
    out["station_vs_plate_battery_arm_clashes_mm3"] = pl
    out.update(track_check(up))
    out["CART VS TANK (#364)"] = cart_tank_check()
    bb = wsa.parts()["sampler_nozzle"][0].val().BoundingBox()
    sk = up["ws_socket"][0].val().BoundingBox()
    out["parked_nozzle_xyz_mm"] = ((bb.xmin + bb.xmax) / 2, (bb.ymin + bb.ymax) / 2, bb.zmax)
    out["test_socket_mouth_xyz_mm (cart frame; the flush top face is at the smallest x)"] = ((sk.xmin + sk.xmax) / 2, (sk.ymin + sk.ymax) / 2, sk.xmin)
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(check(), indent=1, default=str))
