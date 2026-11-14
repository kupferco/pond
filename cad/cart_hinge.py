# cad/cart_hinge.py: the plate hinge and rotation servo of each hand (DRAFT v1, 14 Nov 2026, Viber #97).
# Shared by cart_base.py (drawn and labelled there), cart_assembly.py and cart_arm.py. Not production geometry.
#
# Idea: the sleeve stays clamped on its pipe. A hinge on the sleeve's pad edge, axis parallel to the pipe, lets the
# plate swing out (to -Y) like a door. One servo per hand is bolted to the PLATE, its output shaft on the hinge axis,
# coupled to a horn that is bolted to the sleeve's top knuckle, so the servo turns the plate against the sleeve.
# Nothing goes round the pipe. Hand B's hinge is on the pad's -X edge, hand C's on its +X edge (cart_dims.py).
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
#  5. Servo: 45.2 x 24.7 x 35.5 mm body, shaft 11 mm from the outer end, body bottom at z = 60, held in a window of
#     a plate tongue (4 M3 ear screws shown). Real servo (SO-101 STS3215 class) ears and torque are not sized:
#     opening the plate against its own weight, the arm and the battery needs a gear stage not drawn here.
#  6. Horn: 20 mm disc, 3 mm, on four M2.5 screws on a 14 mm circle into the top sleeve knuckle; coupler 6 mm round
#     from the horn to the servo shaft.
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
EAR_M3 = ((5.0, 6.0), (5.0, SERVO[2] - 6.0))  # ASSUMED: ear screws, offsets from the servo's two ends / bottom


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


def servo_x_range(sgn):
    xh, d = _x(sgn)
    return (xh - SERVO_SHAFT_OFF, xh - SERVO_SHAFT_OFF + SERVO[0]) if d > 0 else (xh + SERVO_SHAFT_OFF - SERVO[0], xh + SERVO_SHAFT_OFF)


def servo(sgn):
    x0, x1 = servo_x_range(sgn)
    return box(SERVO[0], SERVO[1], SERVO[2], ((x0 + x1) / 2, HINGE_Y, SERVO_Z0 + SERVO[2] / 2))


def horn_and_coupler(sgn):
    xh, d = _x(sgn)
    horn = cyl(HORN_R, HORN_T, "z", (xh, HINGE_Y, KNUCKLE_Z + HORN_T / 2))
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        horn = horn.union(cyl(1.25, HORN_T + 3.0, "z", (xh + 7.0 * math.cos(a), HINGE_Y + 7.0 * math.sin(a), KNUCKLE_Z + HORN_T / 2 - 1.5)))
    coupler = cyl(3.0, SERVO_Z0 - (KNUCKLE_Z + HORN_T), "z", (xh, HINGE_Y, (SERVO_Z0 + KNUCKLE_Z + HORN_T) / 2))
    return horn.union(coupler)


def servo_ear_screws(sgn):
    """Four M3 screws through the tongue frame into the servo ears (drawn as short pins along Y)."""
    x0, x1 = servo_x_range(sgn)
    out = None
    for ex in (x0 - FRAME_W / 2, x1 + FRAME_W / 2):
        for z in (SERVO_Z0 + 6.0, SERVO_Z0 + SERVO[2] - 6.0):
            s = cyl(1.7, PLATE_T + 6.0, "y", (ex, PLATE_Y1 - PLATE_T / 2, z))
            out = s if out is None else out.union(s)
    return out


def tongue_holes():
    """M3 holes through the tongue frames for the ear screws (cut into the plate by cart_base.py)."""
    out = []
    for sgn in (-1, 1):
        x0, x1 = servo_x_range(sgn)
        for ex in (x0 - FRAME_W / 2, x1 + FRAME_W / 2):
            for z in (SERVO_Z0 + 6.0, SERVO_Z0 + SERVO[2] - 6.0):
                out.append((ex, z))
    return out


def hinge_parts(sgn):
    """(name, shape, colour) list for one hand's hinge and rotation servo, for the assemblies."""
    return [("sleeve_leaf_knuckles", sleeve_half(sgn), (0.95, 0.75, 0.2, 1)),
            ("sleeve_leaf_screws", sleeve_screws(sgn), (0.3, 0.3, 0.3, 1)),
            ("plate_leaf_knuckle", plate_half(sgn), (0.55, 0.6, 0.65, 1)),
            ("plate_leaf_screws", plate_screws(sgn), (0.3, 0.3, 0.3, 1)),
            ("pin", pin(sgn), (0.15, 0.15, 0.15, 1)),
            ("horn_coupler", horn_and_coupler(sgn), (0.9, 0.9, 0.9, 1)),
            ("rotation_servo", servo(sgn), (0.2, 0.7, 0.3, 1)),
            ("servo_ear_screws", servo_ear_screws(sgn), (0.3, 0.3, 0.3, 1))]
