# cad/cart_wheel_pairs.py: the rigid WHEEL PAIRS of a Pond cart hand, v5 (OpenPocket #278, plan task 265 part 4).
# The v4 file (20 x 8 mm wheels, worm drive, hinge cart) is kept as cart_wheel_pairs_v4.py until plan tasks 5 and 6.
#
# Frame: the hand_sleeve.py frame (track pipe along Z, plate on -Y, C-gap on +X). A "pair" is the two wheels at the same angle in the
# hand's two rows (76 mm apart along the pipe), tied by one rigid carrier. A hand has three pairs:
#   DRIVEN pair at 180 deg: the DRIVE omni wheel (top row, rolls along the pipe) and the ROLL omni wheel (bottom row, rolls the sleeve
#     round the pipe), each on a 6 mm motor shaft. Fixed in the sleeve (the sprung pairs push the pipe against it).
#   Two SPRUNG BALL-CUP pairs at +/-60 deg: two printed cups with balls (cart_omni.py) on one rigid carrier, two springs, a cap.
# Models built here:
#   result  : one hand's three pairs on the track pipe (no sleeve), drive and roll motors drawn.
#   corner  : the sleeve and the pairs on a 150 mm radius, 90 deg loop corner (pipe, sleeve, wheels, cups); the check that it still bends.
#   context : both hands on pipes 120 mm apart (no plate), pairs and sleeves.
# The corner result is computed in this file (not simulated): see CORNER below.
import math
import os
import sys
import cadquery as cq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cart_omni as co
import hand_sleeve as hs
from cart_dims import PIPE_SPACING          # 120: pipe B to pipe C

R_PIPE = hs.R_PIPE
ROW_Z = hs.ROW_Z
CORNER_R = hs.BEND_R                        # 150 mm loop corner centreline radius (decision doc, sim/bend_test.py)
TRAVEL = hs.SPRING_TRAVEL
PIPE_L = 220.0
CUP = hs.CUP
GREY, DARK, STEEL, RED = (0.6, 0.6, 0.65, 1), (0.15, 0.15, 0.15, 1), (0.8, 0.8, 0.82, 1), (0.85, 0.1, 0.1, 1)
CARRIER_COL = (0.2, 0.55, 0.85, 1)
CUP_COL = (0.95, 0.5, 0.15, 1)


def rot(shape, ang):
    return shape.rotate((0, 0, 0), (0, 0, 1), ang)


def _box(r0, r1, w, hl, extra=None):
    return cq.Workplane("XY").box(r1 - r0, w, 2 * hl).translate(((r0 + r1) / 2, 0, 0))


def _cap_holes(shape, d):
    for z in (ROW_Z, -ROW_Z):
        shape = shape.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(d / 2, 100, cq.Vector(0, 0, z), cq.Vector(1, 0, 0))))
    return shape


def carrier_parts(ang, tag, cup_shift=0.0):
    """One sprung ball-cup pair at lobe angle ang (hand frame). cup_shift: radial shift (mm, outward) of the whole carrier (spring travel)."""
    out = {}
    sh = (cup_shift, 0, 0)
    carrier = _box(hs.CARRIER_R0, hs.CARRIER_R1, hs.CARRIER_W, hs.CARRIER_HL)
    out["carrier"] = (rot(_cap_holes(carrier, co.DRAIN_D + 0.4).translate(sh), ang), CARRIER_COL)
    cups, balls = None, None
    for z in (ROW_Z, -ROW_Z):
        cup = CUP["cup"].translate((CUP["centre_r"], 0, z)).translate(sh)
        ball = CUP["ball"].translate((CUP["centre_r"], 0, z)).translate(sh)
        cups = cup if cups is None else cups.union(cup)
        balls = ball if balls is None else balls.union(ball)
    out["cups"] = (rot(cups, ang), CUP_COL)
    out["balls"] = (rot(balls, ang), CUP["ball_colour"])
    springs = None
    for z in (hs.SPRING_Z, -hs.SPRING_Z):
        free = hs.SPRING_INST - cup_shift
        sp = (cq.Workplane("YZ", origin=(hs.CARRIER_R1 + cup_shift, 0, z)).circle(hs.SPRING_OD / 2).circle(hs.SPRING_OD / 2 - 1.2).extrude(free))
        springs = sp if springs is None else springs.union(sp)
    out["springs"] = (rot(springs, ang), RED)
    cap = _cap_holes(_box(hs.CAP_R0, hs.CAP_R1, hs.CHAN_W - 0.4, hs.CHAN_HL - 0.2), 4.0)
    out["cap"] = (rot(cap, ang), GREY)
    return {"%s_%s" % (tag, k): v for k, v in out.items()}


def driven_parts():
    """The 180 deg driven pair in the hand frame: drive wheel (top row), roll wheel (bottom row), shafts, both motors."""
    out = {}
    for k, (s, col) in co.omni_parts().items():
        out["drive_wheel_" + k] = (co.place_drive(s, hs.DRIVE_Z, hs.OUTER_ANG), col)
        out["roll_wheel_" + k] = (co.place_roll(s, hs.ROLL_Z, hs.OUTER_ANG), col)
    out.update(co.drive_motor_parts(hs.DRIVE_Z, hs.DRIVE_MOTOR_WALL_Y, hs.OUTER_ANG))
    out.update(co.roll_motor_parts(hs.ROLL_Z, -hs.SLEEVE_L / 2 - hs.ROLL_MOTOR_WALL_Z, hs.OUTER_ANG))
    return out


def pair_parts(cup_shifts=None):
    """All three pairs of one hand in the hand frame: dict name -> (shape, colour)."""
    parts = dict(driven_parts())
    for a, tag in zip(hs.INNER_ANGS, ("p60", "m60")):
        parts.update(carrier_parts(a, tag, (cup_shifts or {}).get(a, 0.0)))
    return parts


def _assembly(parts, pipe=True):
    a = cq.Assembly()
    if pipe:
        a.add(cq.Workplane("XY").add(cq.Solid.makeCylinder(R_PIPE, PIPE_L, cq.Vector(0, 0, -PIPE_L / 2), cq.Vector(0, 0, 1))),
              name="track_pipe", color=cq.Color(0.75, 0.78, 0.8, 1))
    for n, (s, col) in parts.items():
        a.add(s, name=n, color=cq.Color(*col))
    return a


result = _assembly(pair_parts())


# ---------------- Context model: both hands (sleeves and pairs) on two parallel pipes ----------------
def two_hand_model():
    c = cq.Assembly()
    for tag, sgn in (("B", -1), ("C", 1)):
        c.add(cq.Workplane("XY").add(cq.Solid.makeCylinder(R_PIPE, PIPE_L, cq.Vector(sgn * PIPE_SPACING / 2, 0, -PIPE_L / 2), cq.Vector(0, 0, 1))),
              name="pipe_%s" % tag, color=cq.Color(0.75, 0.78, 0.8, 1))
        def put(s):
            return (s.mirror("YZ") if sgn > 0 else s).translate((sgn * PIPE_SPACING / 2, 0, 0))
        c.add(put(hs.result), name="sleeve_%s" % tag, color=cq.Color(0.95, 0.75, 0.2, 1))
        for n, (s, col) in pair_parts().items():
            c.add(put(s), name="%s_%s" % (tag, n), color=cq.Color(*col))
    return c


context = two_hand_model()


# ---------------- Corner model: the hand on a 150 mm radius loop corner ----------------
# Bend in the XZ plane, centre C, pipe curving towards +X (spine side inside). The sleeve is rigid, so the two OUTER omni wheels (180 deg,
# one in each row) set where it sits (centres on the circle R_OUT round C, hand_sleeve.HAND_AXIS_D). The sprung cup pairs must then
# reach the pipe: the carrier moves radially by `idler_travel`, which has to fit the 2.5 mm spring travel.
R_OUT, HAND_AXIS_D = hs.R_OUT, hs.HAND_AXIS_D


def idler_travel(ang):
    """Radial shift (mm, + = away from the pipe axis, compressing the spring) of a cup pair so both balls keep contact with the bent pipe."""
    ca_, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    cr = CUP["centre_r"]

    def dist(s, z):
        x, y = (cr + s) * ca_, (cr + s) * sa
        rr = math.hypot(HAND_AXIS_D - x, z)
        return math.hypot(rr - CORNER_R, y)
    worst = 0.0
    for z in (ROW_Z, -ROW_Z):
        lo, hi = -15.0, 15.0
        for _ in range(60):
            m = (lo + hi) / 2
            if dist(m, z) - (R_PIPE + CUP["ball_r"]) > 0:
                hi = m
            else:
                lo = m
        if abs(m) > abs(worst):
            worst = m
    return worst


IDLER_SHIFT = idler_travel(60.0)                 # the same for -60 by symmetry
CLEARANCE = {z: hs.bore_r(z) - R_PIPE - abs(hs.pipe_offset(z)) for z in (0.0, ROW_Z, hs.SLEEVE_L / 2)}   # bore to bent pipe: mid, rows, end


def bent_pipe():
    """90 deg pipe bend, centreline radius CORNER_R, plus 80 mm straight stubs, in the world XZ plane."""
    r = CORNER_R
    path = (cq.Workplane("XZ").moveTo(0, -80).lineTo(0, 0).radiusArc((r, r), r).lineTo(r + 80, r))
    return cq.Workplane("XY").circle(R_PIPE).sweep(path)


def corner_model():
    c = cq.Assembly()
    c.add(bent_pipe(), name="track_pipe", color=cq.Color(0.75, 0.78, 0.8, 1))
    mid = math.radians(45.0)
    ux, uz = -math.cos(mid), math.sin(mid)
    ox, oz = CORNER_R + HAND_AXIS_D * ux, HAND_AXIS_D * uz

    def place(shape):
        phi = math.degrees(math.atan2(uz, -ux))
        return shape.rotate((0, 0, 0), (0, 1, 0), phi).translate((ox, 0, oz))
    c.add(place(hs.result), name="hand_sleeve", color=cq.Color(0.95, 0.75, 0.2, 1))
    shifts = {a: IDLER_SHIFT for a in hs.INNER_ANGS}
    for n, (s, col) in pair_parts(shifts).items():
        c.add(place(s), name=n, color=cq.Color(*col))
    return c


corner = corner_model()


def corner_report():
    """(idler shift, fits the spring travel?, bore clearance dict)."""
    return IDLER_SHIFT, abs(IDLER_SHIFT) <= TRAVEL, CLEARANCE


if __name__ == "__main__":
    bb = result.toCompound().BoundingBox()
    print("cart_wheel_pairs v5 OK, detail bbox %.0f x %.0f x %.0f mm" % (bb.xlen, bb.ylen, bb.zlen))
    bc = context.toCompound().BoundingBox()
    print("context (two hands, pipes %.0f apart) bbox %.0f x %.0f x %.0f mm" % (PIPE_SPACING, bc.xlen, bc.ylen, bc.zlen))
    sh, ok, cl = corner_report()
    print("corner R %.0f: cup pair shift %.2f mm of %.1f mm travel -> %s" % (CORNER_R, sh, TRAVEL, "bends" if ok else "DOES NOT BEND"))
    for z, g in cl.items():
        print("  bore to bent pipe at z = %4.0f: %5.1f mm %s" % (z, g, "OK" if g > 0 else "TOUCHES"))
