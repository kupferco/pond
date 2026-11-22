# cad/cart_sleeves.py: the two SLEEVE (hand) systems of the Pond cart, v5: omni wheels, ball cups, roll wheel, no hinge
# (OpenPocket #278, plan task 265 part 4, docs/plans/cart-roll-redesign-plan.md). The v4 hinge-cart file is cart_sleeves_v4.py.
#
# What is drawn (all in the hand_sleeve.py frame, hand B on pipe B at x = -60, hand C its TRUE MIRROR on pipe C at x = +60, Pond #227):
#   - the v5 three-lobe sleeve (hand_sleeve.py), split by the jaw wedge into a fixed body and a JAW, as in v4: the jaw carries the +60 deg
#     lobe (one sprung ball-cup pair) and swings 92 deg about a pin on the tube, driven by an N20 micro motor on the +Z end;
#   - the DRIVE omni wheel (top row) and the ROLL omni wheel (bottom row) on the 180 deg lobe, each with its worm motor (cart_omni.py);
#   - a hall sensor board in a pocket in the sleeve wall at the base end (home_station.py, OpenPocket #286);
#   - four passive ball cups on two sprung carriers (cart_wheel_pairs.py);
#   - no hinge leaves, no worm wheel, no worm, no bracket: the plate is a plain rigid plate bolted to both pads (placeholder, task 5 draws it).
# Scenes: clamped (both jaws closed), released (both open, hands still round the pipes), released_off (hand C open and moved off its
# pipe), transfer (one hand STATIC, clamped; the other released, and the whole cart ROLLED about the static pipe's own centre line).
# check() runs the 120 mm spacing interference check, the jaw check and the drain check.
#
# ASSUMED (undecided, each also marked where used): 1. the jaw wedge 0..110 deg, hinge pin on the tube at 110 deg, 92 deg opening (sim
# OPEN 1.6 rad), N20 micro motor on the +Z end (all as v4); 2. the plate placeholder 166 x 6 x 146 mm on the pad faces at y = -50;
# 3. the transfer roll angle drawn (36 deg, roll_swing_estimate.py: about 35.5 deg to clear the free pipe); 4. the released hand drawn
# 70 mm off its pipe; 5. static hand C (hand B released), as the first trip of roll_swing_estimate.py.
import math
import os
import sys
import cadquery as cq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cart_omni as co
import hand_sleeve as hs
import cart_wheel_pairs as cw
import home_station as hst
import home_station as hst
from cart_dims import PIPE_SPACING
from cart_dims import PIPE_STUB_L                  # 330: pipe stub length in the assemblies

HAND_X = PIPE_SPACING / 2                          # hands at x = -/+ 60, one per pipe


def cyl(r, h, axis, c):
    d = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}[axis]
    start = cq.Vector(*[c[i] - d[i] * h / 2 for i in range(3)])
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(r, h, start, cq.Vector(*d)))


def place_hand(shape, sgn):
    """Put a hand-frame shape (hand B as drawn: pad on -X, C-gap facing +X, towards the plate) on pipe sgn (-1 = B, +1 = C).
    Hand C is the TRUE MIRROR of hand B across the cart centre plane x = 0 (Pond #227), not a copy."""
    return (shape.mirror("YZ") if sgn > 0 else shape).translate((sgn * HAND_X, 0, 0))


# ---------------- Jaw (ASSUMED, as v4): sleeve split by a wedge, hinge pin on the tube, actuator ----------------
JAW_A0, JAW_A1 = 0.0, 110.0               # jaw wall from the middle of the C-gap (0 deg) to +110 deg, one connected piece
JAW_OPEN = 92.0                           # deg, = sim OPEN 1.6 rad (sim/unit_change.py)
JAW_LOBE_ANG = 60.0                       # the sprung pair carried by the jaw
JAW_PIVOT_R = hs.TUBE_R_MIN               # hinge pin on the tube's outer surface at the 110 deg edge
JAW_PIVOT = (JAW_PIVOT_R * math.cos(math.radians(JAW_A1)), JAW_PIVOT_R * math.sin(math.radians(JAW_A1)))
JAW_PIN_R = 2.0
JAW_GB_R, JAW_GB_L = 8.0, 12.0            # worm gearbox
JAW_MOTOR_R, JAW_MOTOR_L = 8.0, 30.0      # 16 x 30 mm micro motor
EXIT_DIR_DEG = 40.0                       # direction the pipe leaves through the open jaw (hand frame)
LUG_R, LUG_FIXED_Z = 4.5, 14.0            # knuckle radius; fixed knuckle spans z = -14..+14
LUG_RELIEF_R = LUG_R + 1.0


def _wedge():
    big = 140.0
    pts = [(0, 0)] + [(big * math.cos(math.radians(a)), big * math.sin(math.radians(a))) for a in (JAW_A0, (JAW_A0 + JAW_A1) / 2, JAW_A1)]
    return cq.Workplane("XY").polyline(pts).close().extrude(2 * hs.SLEEVE_L).translate((0, 0, -hs.SLEEVE_L))


def _barrel(r, z0, z1):
    return cyl(r, z1 - z0, "z", (JAW_PIVOT[0], JAW_PIVOT[1], (z0 + z1) / 2))


_W = _wedge()
_FIXED0 = hs.result.cut(_W)
_JAW0 = hs.result.intersect(_W)
_ZE = hs.SLEEVE_L / 2
_ZJ = LUG_FIXED_Z + 1.0                               # jaw knuckles span |z| = 15..62
FIXED_LUG = _barrel(LUG_R, -LUG_FIXED_Z, LUG_FIXED_Z)
JAW_LUGS = _barrel(LUG_R, _ZJ, _ZE).union(_barrel(LUG_R, -_ZE, -_ZJ))
FIXED_BODY = ((_FIXED0.cut(_barrel(LUG_RELIEF_R, _ZJ - 0.5, _ZE + 1)).cut(_barrel(LUG_RELIEF_R, -_ZE - 1, -_ZJ + 0.5)).union(FIXED_LUG)).cut(hst.pocket()))
JAW_BODY = _JAW0.cut(_barrel(LUG_RELIEF_R, -LUG_FIXED_Z - 0.5, LUG_FIXED_Z + 0.5)).union(JAW_LUGS)


def jaw_turn(shape, open_deg):
    """Swing a jaw-side shape about the hinge pin by open_deg (counter-clockwise from +Z = opening)."""
    if not open_deg:
        return shape
    return shape.rotate((JAW_PIVOT[0], JAW_PIVOT[1], 0), (JAW_PIVOT[0], JAW_PIVOT[1], 1), open_deg)


# ---------------- One hand: parts in the hand's own frame (centred at z = 0) ----------------
SLEEVE_COL, JAW_COL = (0.95, 0.75, 0.2, 1), (0.95, 0.5, 0.15, 1)


def hand_parts(jaw_open=0.0):
    """Dict name -> (shape, colour). Frame: sleeve centred on z = 0. Jaw-side parts (the jaw, the +60 deg ball-cup pair, the hinge lugs) turn with
    the jaw. jaw_open: opening in degrees (0 = clamped, JAW_OPEN = released)."""
    parts = {"sleeve": (FIXED_BODY, SLEEVE_COL), "jaw": (jaw_turn(JAW_BODY, jaw_open), JAW_COL)}
    for n, (s, col) in cw.pair_parts().items():
        parts[n] = (jaw_turn(s, jaw_open) if n.startswith("p60_") else s, col)
    parts.update(hst.sensor_parts())      # hall sensor board in the sleeve wall (OpenPocket #286)
    pz0 = -hs.SLEEVE_L / 2 - 2
    pin_len = hs.SLEEVE_L + 4 + JAW_GB_L / 2
    parts["jaw_hinge_pin"] = (cyl(JAW_PIN_R, pin_len, "z", (JAW_PIVOT[0], JAW_PIVOT[1], pz0 + pin_len / 2)), (0.8, 0.8, 0.82, 1))
    zg = hs.SLEEVE_L / 2 + JAW_GB_L / 2
    parts["jaw_gearbox"] = (cyl(JAW_GB_R, JAW_GB_L, "z", (JAW_PIVOT[0], JAW_PIVOT[1], zg)), (0.1, 0.55, 0.3, 1))
    parts["jaw_motor"] = (cyl(JAW_MOTOR_R, JAW_MOTOR_L, "z", (JAW_PIVOT[0], JAW_PIVOT[1], zg + JAW_GB_L / 2 + JAW_MOTOR_L / 2)), (0.1, 0.55, 0.3, 1))
    return parts


# ---------------- Plate placeholder ----------------
PLATE_T = 6.0
PLATE_X1 = HAND_X + abs(hs.PAD_X0)                 # 84: plate ends at the outer pad edges (pad -24..0 on each hand's outer side)
PLATE_HL = hs.SLEEVE_L / 2 + 11.0                  # half height: 11 mm beyond each sleeve end (as v4)
PLATE_Y0 = hs.PAD_Y0                               # plate back face on the pad faces (y = -50), plate front at -56


def plate():
    p = cq.Workplane("XY").box(2 * PLATE_X1, PLATE_T, 2 * PLATE_HL).translate((0, PLATE_Y0 - PLATE_T / 2, 0))
    for sgn in (-1, 1):
        for z in (hs.PAD_HOLE_Z, -hs.PAD_HOLE_Z):
            p = p.cut(cyl(hs.PAD_HOLE_D / 2, PLATE_T + 2, "y", (sgn * (HAND_X + hs.PAD_X0 / 2), PLATE_Y0 - PLATE_T / 2, z)))
    return p


# ---------------- Pair: one hand on each of two parallel pipes ----------------
STATIC_WHEEL_COL = (0.1, 0.35, 0.8, 1)
TAGS = (("B", -1), ("C", 1))                      # (tag, sgn): pipe B at -x, pipe C at +x


def build_pair(static=None, roll=0.0, with_plate=True, jaws=None, off=None):
    """Both hands, each on its own pipe, and the rigid plate.
    static: None or "B"/"C": that hand is STATIC (rollers blue, clamped on its pipe); the whole cart (plate, both sleeves) is ROLLED by
    `roll` degrees about that pipe's own centre line; the pipes stay where they are. roll > 0 turns the free hand towards the plate side
    (-Y, "plate" in roll_swing_estimate.py), roll < 0 towards the spine side.
    jaws: tag -> jaw opening in degrees. off: tag -> mm the hand is moved off its pipe along the exit direction (before the roll)."""
    a = cq.Assembly()
    jaws, off_mm = jaws or {}, off or {}
    sgn_s = dict(TAGS).get(static, 0)
    ax = (sgn_s * HAND_X, 0, 0)

    def rolled(shape):
        return shape.rotate(ax, (ax[0], 0, 1), sgn_s * roll) if (static and roll) else shape
    for tag, sgn in TAGS:
        role = "static" if static == tag else ("released" if static else "hand")
        for name, (shp, col) in hand_parts(jaws.get(tag, 0.0)).items():
            if static == tag and name.startswith(("drive_wheel_rollers", "roll_wheel_rollers")):
                col = STATIC_WHEEL_COL
            d = off_mm.get(tag, 0.0)
            shp = shp.translate((-d * math.cos(math.radians(EXIT_DIR_DEG)), -d * math.sin(math.radians(EXIT_DIR_DEG)), 0))
            a.add(rolled(place_hand(shp, sgn)), name="%s_%s_%s" % (role, tag, name), color=cq.Color(*col))
    if with_plate:
        a.add(rolled(plate()), name="base_plate", color=cq.Color(0.35, 0.35, 0.38, 1))
    return a


OPEN_ALL = {"B": JAW_OPEN, "C": JAW_OPEN}
RELEASE_OFF_MM = 70.0                              # ASSUMED: how far the released hand is drawn off its pipe
TRANSFER_ROLL = 36.0                               # ASSUMED illustration angle (deg), roll_swing_estimate.py: about 35.5 deg to clear the free pipe
STATIC_HAND = "C"                                  # hand B is released, as the first trip of roll_swing_estimate.py

pair = build_pair()
_REL = "B" if STATIC_HAND == "C" else "C"
transfer = build_pair(STATIC_HAND, TRANSFER_ROLL, jaws={_REL: JAW_OPEN})
clamped = build_pair()                             # both jaws closed on their pipes (same as `pair`)
released = build_pair(jaws=OPEN_ALL)               # both jaws open, hands still round their pipes
released_off = build_pair(jaws=OPEN_ALL, off={"C": RELEASE_OFF_MM})
result = pair

DIMS = {
    "pipe_spacing": PIPE_SPACING,
    "sleeve_length": hs.SLEEVE_L,
    "row_spacing": hs.ROW_SPACING,
    "sleeve_od": 2 * hs.WALL_OUT_R,
    "pipe_od": hs.PIPE_D,
    "gap_narrow": hs.OPENING_W,
    "gap_mouth": hs.FUNNEL_MOUTH_W,
}


# ---------------- Checks ----------------
def _hand_solid(sgn, jaw_open=0.0):
    parts = hand_parts(jaw_open)
    shapes = []
    for s, _ in parts.values():
        shapes.extend(s.vals())
    return cq.Compound.makeCompound([place_hand(cq.Workplane("XY").add(cq.Compound.makeCompound(shapes)), sgn).val()])


def spacing_check():
    """The 120 mm pipe spacing with the v5 sleeves (the old assertion PIPE_SPACING - SLEEVE_R - WHEEL_REACH >= 10 fails for a full R61 ring).
    Returns dict: gap between the two hands at roll 0 (all parts), the free pipe's clearance to the swept circle of the static sleeve during
    a roll, and the overlaps with the pipes."""
    hb, hc = _hand_solid(-1), _hand_solid(1)
    gap = hb.distance(hc)
    swept, motor_pts = 0.0, []
    for name, (s, _) in hand_parts().items():
        motor = "motor" in name or "gearbox" in name or "shaft" in name
        for v in s.vals():
            vv, _t = v.tessellate(1.0, 0.5)
            for p in vv:
                if motor:
                    motor_pts.append((p.x, p.y))
                else:
                    swept = max(swept, math.hypot(p.x, p.y))
    # motors, gearboxes and shafts sit beyond the sleeve ends and reach further out: how far can the cart roll before one meets the free pipe?
    first = 180.0
    for x, y in motor_pts:
        rho = math.hypot(x, y)
        k = (rho ** 2 + PIPE_SPACING ** 2 - hs.R_PIPE ** 2) / (2 * PIPE_SPACING * rho) if rho > 0 else 2
        if abs(k) >= 1:
            continue
        al, psi = math.degrees(math.acos(k)), math.degrees(math.atan2(y, x))
        for th in (-al - psi, al - psi):              # edges of the colliding roll interval, wrapped to -180..180
            th = (th + 180.0) % 360.0 - 180.0
            first = min(first, abs(th))
        lo, hi = (-al - psi + 180.0) % 360.0 - 180.0, (al - psi + 180.0) % 360.0 - 180.0
        if lo > hi or lo <= 0 <= hi:                  # interval contains 0: already touching at roll 0
            first = 0.0 if lo <= 0 <= hi and lo <= hi else first
    free_pipe_clear = PIPE_SPACING - swept - hs.R_PIPE      # free pipe against the static sleeve's swept circle during a roll
    pipe_c = cyl(hs.R_PIPE, PIPE_STUB_L, "z", (HAND_X, 0, 0))
    pipe_b = cyl(hs.R_PIPE, PIPE_STUB_L, "z", (-HAND_X, 0, 0))
    over = {}
    for name, h, p in (("hand B vs pipe C", hb, pipe_c), ("hand C vs pipe B", hc, pipe_b)):
        i = cq.Workplane("XY").add(h).intersect(p)
        over[name] = sum(s.Volume() for s in i.solids().vals()) if i.solids().vals() else 0.0
    sleeve_over = {}
    for sgn, tag in ((-1, "B"), (1, "C")):
        i = place_hand(FIXED_BODY.union(JAW_BODY), sgn).intersect(cyl(hs.R_PIPE, PIPE_STUB_L, "z", (sgn * HAND_X, 0, 0)))
        sleeve_over["sleeve %s vs its own pipe" % tag] = sum(s.Volume() for s in i.solids().vals()) if i.solids().vals() else 0.0
    return {"gap_between_hands": gap, "swept_radius": swept, "motor_roll_clear_deg": first, "free_pipe_clearance": free_pipe_clear, "overlaps": over, "sleeve_overlaps": sleeve_over}


def check_jaw():
    """Returns (closed jaw + fixed body == hs.result?, collisions while the pipe leaves through the open jaw and while the jaw swings)."""
    same = abs(_FIXED0.union(_JAW0).val().Volume() - hs.result.val().Volume()) < 1.0
    pipe = cyl(hs.R_PIPE, 250.0, "z", (0, 0, 0))
    jaw_parts = [(n, s) for n, (s, _) in hand_parts(JAW_OPEN).items() if n == "jaw" or n.startswith("p60_")]
    fixed_parts = [(n, s) for n, (s, _) in hand_parts(JAW_OPEN).items() if n == "sleeve" or n.startswith(("m60_", "drive_wheel", "roll_wheel"))]
    hit = []
    for s_mm in range(0, 71, 5):
        p = pipe.translate((s_mm * math.cos(math.radians(EXIT_DIR_DEG)), s_mm * math.sin(math.radians(EXIT_DIR_DEG)), 0))
        for nm, b in jaw_parts[:1] + fixed_parts[:1]:
            i = b.intersect(p)
            if i.vals() and i.val().Volume() > 1e-3:
                hit.append((s_mm, nm))
    fixed = FIXED_BODY
    for d in range(1, int(JAW_OPEN) + 1, 4):
        i = fixed.intersect(jaw_turn(JAW_BODY, d))
        if i.vals() and i.val().Volume() > 1.0:
            hit.append((d, "swing"))
    return same, hit


def check_drain():
    """The five drain holes of each of the four cups (back hole radially outward, four side holes at 90 deg: +/-y round the pipe, +/-z along it)
    must open to the outside of the sleeve: the line from the hole, outward through the lobe, carrier and cap, meets no sleeve material.
    Returns a dict (cup, hole -> blocked volume in mm3, 0 = open). Side holes are tested with a cylinder of the hole's size, DRAIN_SLOT_H wide
    in x at most, from the cup wall (9.4 mm out, past the 9.3 mm cup bore radius) 9.6 mm further, which is past the lobe side (14 mm) and out of the tube wall (R27 at the slot ends); beyond that the water falls free."""
    res = {}
    xc = co.ball_cup(co.BALL_D)["centre_r"]
    for a, tag in zip(hs.INNER_ANGS, ("p60", "m60")):
        for z in (hs.ROW_Z, -hs.ROW_Z):
            lines = {"back": (hs.CARRIER_R0 - 0.5, 0, z, (1, 0, 0))}
            for nm, d in zip(("+y", "+z", "-y", "-z"), co.SIDE_DRAIN_DIRS):
                lines["side " + nm] = (xc, 0, z, d)
            for nm, (x, y, zz, d) in lines.items():
                line = cq.Workplane("XY").add(cq.Solid.makeCylinder(co.DRAIN_D / 2, 200.0, cq.Vector(x, y, zz), cq.Vector(*d)))
                if nm.startswith("side"):      # start at the cup wall, not inside the cup: the cup body itself is not sleeve material
                    line = cq.Workplane("XY").add(cq.Solid.makeCylinder(co.DRAIN_D / 2, 9.6, cq.Vector(x + d[0] * 9.4, y + d[1] * 9.4, zz + d[2] * 9.4), cq.Vector(*d)))
                line = line.rotate((0, 0, 0), (0, 0, 1), a)
                i = hs.result.intersect(line)
                res["%s cup z=%+.0f %s" % (tag, z, nm)] = i.val().Volume() if i.vals() else 0.0
    return res


def drain_angles(step=15):
    """Water level in each cup at every roll angle, for a pipe HORIZONTAL (gravity -Y) and for a pipe VERTICAL (gravity along the pipe, both signs).
    The cup at lobe angle a sits at a + roll round the pipe, its axis (x, back hole) pointing radially outward. The holes are on the cup axis
    (+x) and on +/-y, +/-z (cup frame). Water collects at the lowest point of the seat, the direction of gravity g in the cup frame; the leftover
    crescent is R (1 - cos w), w = angle from g to the nearest hole. Returns (roll, worst angle deg, crescent mm, ml) for a pipe horizontal
    (the worst of the two cup lobes), plus the same for the vertical case. If the cup axis points down (g . x < 0, the cup is on top and the
    seat mouth faces down) the water leaves through the mouth, past the ball, and the row is marked 'mouth'."""
    R = co.ball_cup(co.BALL_D)["seat_r"]
    holes = [(1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
    def worst(g):
        gn = math.sqrt(sum(c * c for c in g))
        return min(math.degrees(math.acos(max(-1.0, min(1.0, sum(a * b for a, b in zip(g, h)) / gn)))) for h in holes)
    rows = []
    for roll in range(0, 360, step):
        w, mouth = 0.0, False
        for a in hs.INNER_ANGS:
            th = math.radians(a + roll)
            g = (-math.sin(th), -math.cos(th), 0.0)      # gravity (0, -1, 0) in the cup frame (x radial, y tangential, z along the pipe)
            if g[0] < -0.5:
                mouth = True
            else:
                w = max(w, worst(g))
        # crescent: spherical cap of height h = R (1 - cos w); volume pi h^2 (3R - h) / 3
        h = R * (1 - math.cos(math.radians(w)))
        rows.append((roll, w, h, math.pi * h * h * (3 * R - h) / 3000.0, mouth))
    vert = max(worst(g) for g in ((0, 0, 1), (0, 0, -1)))
    return rows, vert


def check():
    sp = spacing_check()
    ok_sp = sp["gap_between_hands"] >= 10.0 and sp["free_pipe_clearance"] >= 10.0 and all(v < 1e-3 for v in sp["overlaps"].values())
    same, hit = check_jaw()
    dr = check_drain()
    return {"spacing": sp, "spacing_ok": ok_sp, "jaw_same": same, "jaw_hits": hit, "drain": dr, "drain_ok": all(v < 1e-3 for v in dr.values())}


if __name__ == "__main__":
    r = check()
    sp = r["spacing"]
    print("spacing %.0f mm: gap between the two hands %.1f mm (need >= 10); swept radius of a sleeve with wheels %.1f mm, free pipe clears the swept "
          "circle by %.1f mm during a roll (need >= 10); overlaps with the other pipe %s" % (PIPE_SPACING, sp["gap_between_hands"], sp["swept_radius"],
                                                                                           sp["free_pipe_clearance"], sp["overlaps"]))
    print("motors, gearboxes and shafts (beyond the sleeve ends) meet the free pipe only after a roll of %.0f deg (transfers need about 36)" % sp["motor_roll_clear_deg"])
    print("sleeve vs its own pipe, overlap mm3:", sp["sleeve_overlaps"])
    print("spacing check:", "OK" if r["spacing_ok"] else "FAILS")
    print("closed jaw + fixed body == hs.result:", r["jaw_same"])
    print("pipe leaves through the open jaw and the jaw swings with no collision:", not r["jaw_hits"], r["jaw_hits"])
    print("drain holes open to the outside of the sleeve (blocked volume mm3):", r["drain"], "->", "OK" if r["drain_ok"] else "BLOCKED")
    rows, vert = drain_angles()
    print("drain, horizontal pipe, worst cup lobe per roll (water at seat bottom vs nearest of back hole + 4 side holes):")
    for roll, w, h, ml, mouth in rows:
        print("  roll %3d: worst %4.1f deg from a hole, crescent %.1f mm / %.2f ml%s" % (roll, w, h, ml, "  (the other lobe's cup faces down: drains past the ball)" if mouth else ""))
    print("drain, vertical pipe (gravity along the pipe): %.0f deg from a hole at every roll" % vert)
    for tag, obj in (("pair", pair), ("released", released), ("transfer (static hand %s)" % STATIC_HAND, transfer)):
        bb = obj.toCompound().BoundingBox()
        print("cart_sleeves %s OK, bbox %.0f x %.0f x %.0f mm" % (tag, bb.xlen, bb.ylen, bb.zlen))
