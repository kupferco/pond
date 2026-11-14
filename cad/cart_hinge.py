# cad/cart_hinge.py: the plate hinge and its worm-gear rotation drive of each hand (DRAFT v3, 14 Nov 2026, Viber #97).
# Shared by cart_base.py (drawn and labelled there), cart_assembly.py and cart_arm.py. Not production geometry.
#
# DRAFT v3 (14 Nov 2026), change from v1/v2: the direct-drive servo is replaced by a WORM GEAR drive. A brass worm
# wheel (module 1, 38 teeth) sits on the hinge axis above the sleeve, fixed to the sleeve's top knuckle by a hub. A steel
# worm (module 1, 10 mm pitch dia, single start, self-locking) is carried by the plate in a bracket, and driven by a
# 28 x 55 mm worm-gear motor (the same part as the hand drives). Turning the worm walks the plate round the wheel
# at 38:1. Torque budget and the folded arm pose: cart_dims.py (torque_budget()).
# Rotation only happens during a transfer: the other hand is released from its pipe, this hand's motor swings the plate.
#
# Idea: the sleeve stays clamped on its pipe. A hinge on the sleeve's pad edge, axis parallel to the pipe, lets the
# plate swing out (to -Y) like a door. Nothing goes round the pipe. Hand B's hinge is on the pad's -X edge, hand C's on
# its +X edge (cart_dims.py).
#
# Stack, out from the pad (-Y): pad | sleeve leaf 3 | plate leaf 3 | plate 6. Hinge axis on the leaf-to-leaf face.
# ASSUMED (everything below; real parts not chosen):
#  1. Barrel 10 mm OD (HINGE_R 5), pin 4 mm steel, leaves 3 mm aluminium, one hinge per hand 90 mm long.
#  2. Three knuckles per hinge: two on the sleeve leaf (z 16.5..45 and -45..-16.5), one on the plate leaf
#     (z -15.5..15.5), 1 mm gaps. Pin has a 6 mm head at the bottom and ends level with the top knuckle.
#  3. Sleeve leaf: 30 mm wide, bolted to the pad's two M4 holes (x pad centre, z +/-15) with M4 countersunk screws
#     (flush, so the plate leaf lies on it); the pad holes are 4.3 mm clearance holes, so the screws need nuts or
#     inserts in the sleeve wall: not designed.
#  4. Plate leaf: 31 wide (Z) x 30 (X), bolted to the plate with two M4 countersunk screws at x = hinge + 20 inwards,
#     z +/-8 (flush with the plate front, so the motors can sit beside them).
#  5. Worm wheel: brass, module 1, 38 teeth (40 mm OD), 8 mm wide, z 62..70, on a 6 mm hub from the top knuckle
#     (z 45) to the wheel, a 20 mm flange on four M2.5 screws into the knuckle (the wheel is fixed to the SLEEVE).
#  6. Worm: steel, 10 mm pitch dia, 12 mm OD, 24 mm long, on a 5 mm shaft, axis along X, 24 mm in front of the hinge
#     axis (y = -67), z = 66. Single start, lead angle 5.7 deg, so it holds the plate with the motor off.
#  7. Plate tongue above the plate's top rim, starting 21 mm from the hinge axis (clear of the wheel), carries a bolted
#     bracket: a bridge over the wheel (z 72..80), a bearing block on the tongue side and the motor face plate on the
#     other. Plate and bracket 6 mm aluminium. The motor (28 x 55 mm) hangs outboard of the hinge, axis on the worm axis.
#     Bearings, shaft coupling, lubrication and limit switches are not designed.
import math
import os
import sys
import cadquery as cq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hand_sleeve as hs
from cart_dims import *   # noqa: F401,F403


def box(sx, sy, sz, c):
    return cq.Workplane("XY").box(sx, sy, sz).translate(c)


def cyl(r, h, axis, c):
    d = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}[axis]
    start = cq.Vector(*[c[i] - d[i] * h / 2 for i in range(3)])
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(r, h, start, cq.Vector(*d)))


LEAF_W = 30.0                       # ASSUMED: leaf width (X)
KN_GAP = 1.0                        # ASSUMED
MID_HZ = hs.SLEEVE_L / 6 - KN_GAP / 2      # plate knuckle half length: 14.5
SLEEVE_KN_Z0 = MID_HZ + KN_GAP              # sleeve knuckles run from here to the sleeve end (z 15.5..45)
PIN_R = 2.0
SCREW_R, CSK_R, CSK_H = 2.0, 4.0, 2.2       # M4 countersunk
PLATE_SCREW_DX, PLATE_SCREW_DZ = 20.0, 8.0  # ASSUMED plate-leaf screw pattern (from the hinge axis inwards, +/- z)


def _x(sgn):
    return hinge_x(sgn), -sgn         # hinge axis x, direction towards the plate (+1 for B, -1 for C)


def csk_cut(x, y_face, z):
    """Countersink cone to cut into a leaf or plate where a countersunk head sits (flush at y_face)."""
    return cq.Workplane("XY").add(cq.Solid.makeCone(CSK_R + 0.1, SCREW_R + 0.1, CSK_H + 0.1, cq.Vector(x, y_face - 0.1, z), cq.Vector(0, 1, 0)))


def _csk(x, y_face, z, length):
    """Countersunk screw seen as a shank + cone head, head flush at y_face, shank going to +Y (towards the pad)."""
    shank = cyl(SCREW_R, length, "y", (x, y_face + length / 2, z))
    head = cq.Workplane("XY").add(cq.Solid.makeCone(CSK_R, SCREW_R, CSK_H, cq.Vector(x, y_face, z), cq.Vector(0, 1, 0)))
    return shank.union(head)


def sleeve_half(sgn):
    """Sleeve leaf with its two end knuckles. In cart coordinates, hand at pipe sgn."""
    xh, d = _x(sgn)
    xc = xh + d * (6.0 + (LEAF_W - 6.0) / 2)                       # leaf spans xh+6*d .. xh+LEAF_W*d
    # leaf occupies y from LEAF_Y1 (-43) to the pad face (-40)
    leaf = box(LEAF_W - 6.0, HINGE_LEAF_T, hs.SLEEVE_L, (xc, (LEAF_Y1 + hs.PAD_Y0) / 2, 0.0))
    for z0, z1 in ((SLEEVE_KN_Z0, KNUCKLE_Z), (-KNUCKLE_Z, -SLEEVE_KN_Z0)):
        zc, l = (z0 + z1) / 2, z1 - z0
        barrel = cyl(HINGE_R, l, "z", (xh, HINGE_Y, zc))
        neck = box(7.0, hs.PAD_Y0 - HINGE_Y + HINGE_R, l, (xh + d * 3.5, (HINGE_Y - HINGE_R + hs.PAD_Y0) / 2, zc))
        leaf = leaf.union(barrel).union(neck)
    for z0, z1 in ((SLEEVE_KN_Z0, KNUCKLE_Z), (-KNUCKLE_Z, -SLEEVE_KN_Z0)):
        leaf = leaf.cut(cyl(PIN_R + 0.1, z1 - z0 + 2, "z", (xh, HINGE_Y, (z0 + z1) / 2)))
    # screw holes for the two M4 pad screws (through the leaf, countersunk on the front face)
    px = sgn * HX + (hs.PAD_X0 + hs.PAD_X1) / 2
    for dz in (hs.PAD_HOLE_Z, -hs.PAD_HOLE_Z):
        leaf = leaf.cut(cyl(hs.PAD_HOLE_D / 2, 10.0, "y", (px, LEAF_Y1 + 1.5, dz))).cut(csk_cut(px, LEAF_Y1, dz))
    return leaf


def sleeve_screws(sgn):
    px = sgn * HX + (hs.PAD_X0 + hs.PAD_X1) / 2
    out = None
    for dz in (hs.PAD_HOLE_Z, -hs.PAD_HOLE_Z):
        s = _csk(px, LEAF_Y1, dz, 12.0)     # M4 x 12: leaf 3 + into the pad 9
        out = s if out is None else out.union(s)
    return out


def plate_half(sgn):
    """Plate leaf with the middle knuckle. Lies on the plate's rear face (y -46 .. -43)."""
    xh, d = _x(sgn)
    xc = xh + d * LEAF_W / 2
    leaf = box(LEAF_W, HINGE_LEAF_T, 2 * MID_HZ, (xc, LEAF_Y1 - HINGE_LEAF_T / 2, 0.0))
    barrel = cyl(HINGE_R, 2 * MID_HZ, "z", (xh, HINGE_Y, 0.0))
    leaf = leaf.union(barrel).cut(cyl(PIN_R + 0.1, 2 * MID_HZ + 2, "z", (xh, HINGE_Y, 0.0)))
    for dz in (PLATE_SCREW_DZ, -PLATE_SCREW_DZ):
        leaf = leaf.cut(cyl(SCREW_R - 0.4, 8.0, "y", (xh + d * PLATE_SCREW_DX, LEAF_Y1 - 1.5, dz)))   # tapped (core) hole
    return leaf


def plate_screws(sgn):
    """Countersunk M4 screws through the plate into the plate leaf, flush with the plate front (y -52)."""
    xh, d = _x(sgn)
    out = None
    for dz in (PLATE_SCREW_DZ, -PLATE_SCREW_DZ):
        s = _csk(xh + d * PLATE_SCREW_DX, PLATE_Y0, dz, 9.0)   # M4 x 10: plate 6 + leaf 3, tapped in the plate leaf
        out = s if out is None else out.union(s)
    return out


def pin(sgn):
    xh, d = _x(sgn)
    p = cyl(PIN_R, 2 * KNUCKLE_Z, "z", (xh, HINGE_Y, 0.0))
    return p.union(cyl(3.0, 2.0, "z", (xh, HINGE_Y, -KNUCKLE_Z - 1.0)))      # 6 mm head under the bottom knuckle


def out_dir(sgn):
    """+1/-1: direction in X pointing AWAY from the plate (outboard) at this hand's hinge."""
    return sgn


def worm_wheel(sgn):
    """Hub (z 45..62), flange on the knuckle and the 38-tooth wheel (drawn as a toothed-looking disc: root + tip rings)."""
    xh, d = _x(sgn)
    flange = cyl(HORN_R, HORN_T, "z", (xh, HINGE_Y, KNUCKLE_Z + HORN_T / 2))
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        flange = flange.union(cyl(1.25, HORN_T + 3.0, "z", (xh + 7.0 * math.cos(a), HINGE_Y + 7.0 * math.sin(a), KNUCKLE_Z + HORN_T / 2 - 1.5)))
    hub = cyl(3.0, WHEEL_Z0 - (KNUCKLE_Z + HORN_T) + 1.0, "z", (xh, HINGE_Y, (WHEEL_Z0 + KNUCKLE_Z + HORN_T) / 2))
    wheel = cyl(WHEEL_OD / 2, WHEEL_T, "z", (xh, HINGE_Y, WORM_ZC))
    # tooth gaps: 38 small slots cut round the rim (depth 2 mm, width 1.5 mm)
    for k in range(WHEEL_Z):
        a = 2 * math.pi * k / WHEEL_Z
        gap = box(2.2, 1.5, WHEEL_T + 2, (xh + (WHEEL_OD / 2 - 1.0) * math.cos(a), HINGE_Y + (WHEEL_OD / 2 - 1.0) * math.sin(a), WORM_ZC))
        wheel = wheel.cut(gap.rotate((xh, HINGE_Y, 0), (xh, HINGE_Y, 1), math.degrees(a)))
    return flange.union(hub).union(wheel)


def worm_axis_y():
    return HINGE_Y - CENTRE_DIST


def worm(sgn):
    """Worm with its 5 mm shaft (x), ending at the motor face plate."""
    xh, d = _x(sgn)
    o = out_dir(sgn)
    y, z = worm_axis_y(), WORM_ZC
    w = cyl(WORM_OD / 2, WORM_L, "x", (xh, y, z))
    shaft = cyl(2.5, 2 * 26.0, "x", (xh, y, z))
    out = w.union(shaft)
    for k in range(5):                      # thread rings (single start, drawn as grooves)
        out = out.cut(cyl(WORM_OD / 2 + 1, 1.2, "x", (xh - 8.0 + 4.0 * k, y, z)).cut(cyl(WORM_PD / 2 - 0.5, 1.2, "x", (xh - 8.0 + 4.0 * k, y, z))))
    return out


BRK_T = 5.0                          # ASSUMED bracket plate thickness
BRK_Y0, BRK_Y1 = -52.0, -82.0        # bracket y range: from the tongue front face (plate front, -52) out to -82
BRK_Z0, BRK_Z1 = WORM_ZC - 14.0, WORM_ZC + 14.0   # 52..80 (28 mm, as the motor)


def bracket_xs(sgn):
    """(x of the inboard bearing block centre, x of the motor face plate centre, x of the motor face)"""
    xh, d = _x(sgn)
    return xh + d * (TONGUE_DX0 + BRK_T / 2), xh - d * (TONGUE_DX0 + BRK_T / 2), xh - d * (TONGUE_DX0 + BRK_T)


def worm_bracket(sgn):
    """Aluminium bracket: bearing block (tongue side), motor face plate (outboard) and a bridge over the wheel."""
    xh, d = _x(sgn)
    xi, xo, _ = bracket_xs(sgn)
    yc, ylen = (BRK_Y0 + BRK_Y1) / 2, abs(BRK_Y1 - BRK_Y0)
    block_in = box(BRK_T, ylen, BRK_Z1 - BRK_Z0, (xi, yc, (BRK_Z0 + BRK_Z1) / 2))
    block_out = box(BRK_T, ylen, BRK_Z1 - BRK_Z0, (xo, yc, (BRK_Z0 + BRK_Z1) / 2))
    x0, x1 = sorted((xi, xo))
    bridge = box(x1 - x0 + BRK_T, ylen, 4.0, ((x0 + x1) / 2, yc, BRK_Z1 - 2.0))     # z 76..80, over the wheel (top at 70)
    br = block_in.union(block_out).union(bridge)
    for blk in (xi, xo):                                                            # 5 mm shaft bores
        br = br.cut(cyl(2.7, BRK_T + 2, "x", (blk, worm_axis_y(), WORM_ZC)))
    return br


def worm_motor(sgn):
    """28 x 55 mm worm-gear motor (same placeholder as the hand drives), outboard of the motor face plate."""
    xh, d = _x(sgn)
    _, _, xf = bracket_xs(sgn)
    o = -d                              # outboard direction in X
    xc = xf + o * MOTOR_L / 2
    m = cyl(MOTOR_R, MOTOR_L, "x", (xc, worm_axis_y(), WORM_ZC))
    return m.union(cyl(2.5, 8.0, "x", (xf - o * 2.0, worm_axis_y(), WORM_ZC)))


def bracket_screws(sgn):
    """Two M4 screws from the tongue into the inboard bearing block (drawn as pins along Y)."""
    xi, _, _ = bracket_xs(sgn)
    out = None
    for dz in (-8.0, 8.0):
        s = cyl(2.0, 14.0, "y", (xi, PLATE_Y0 - 3.0, WORM_ZC + dz))
        out = s if out is None else out.union(s)
    return out


def tongue_x_range(sgn):
    xh, d = _x(sgn)
    a, b = xh + d * TONGUE_DX0, xh + d * (TONGUE_DX0 + TONGUE_W)
    return (min(a, b), max(a, b))


def tongue_holes():
    """M4 holes through the plate tongue for the bracket screws: [(x, z)]."""
    out = []
    for sgn in (-1, 1):
        xi, _, _ = bracket_xs(sgn)
        for dz in (-8.0, 8.0):
            out.append((xi, WORM_ZC + dz))
    return out


def hinge_parts(sgn):
    """(name, shape, colour) list for one hand's hinge and worm drive, for the assemblies."""
    return [("sleeve_leaf_knuckles", sleeve_half(sgn), (0.95, 0.75, 0.2, 1)),
            ("sleeve_leaf_screws", sleeve_screws(sgn), (0.3, 0.3, 0.3, 1)),
            ("plate_leaf_knuckle", plate_half(sgn), (0.55, 0.6, 0.65, 1)),
            ("plate_leaf_screws", plate_screws(sgn), (0.3, 0.3, 0.3, 1)),
            ("pin", pin(sgn), (0.15, 0.15, 0.15, 1)),
            ("worm_wheel_hub", worm_wheel(sgn), (0.85, 0.65, 0.2, 1)),
            ("worm", worm(sgn), (0.7, 0.7, 0.75, 1)),
            ("worm_bracket", worm_bracket(sgn), (0.5, 0.55, 0.6, 1)),
            ("bracket_screws", bracket_screws(sgn), (0.3, 0.3, 0.3, 1)),
            ("worm_motor", worm_motor(sgn), (0.85, 0.25, 0.25, 1))]
