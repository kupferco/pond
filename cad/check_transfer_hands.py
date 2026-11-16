# cad/check_transfer_hands.py: is hand B a true mirror of hand C across the cart centre plane (x = 0)? (Pond #227)
# Read-only check, changes no geometry. Run: python cad/check_transfer_hands.py
# Compares every part of hand C AS PLACED on the cart (hand, hinge leaves, worm wheel, worm, bracket, motors) with the mirror
# image of hand B, plus the plate, the plate-side layout, the C-gap direction, and that each clamped hand clears both pipes.
import os
import sys
import cadquery as cq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cart_sleeves as csl
import cart_hinge as ch
import cart_dims as cd
import cart_geom as cg
import hand_sleeve as hs


def vol(w):
    return sum(s.Volume() for s in w.solids().vals()) if w.vals() else 0.0


def placed(sgn, name):
    """A hand part as placed in the cart."""
    return csl.place_hand(csl.hand_parts()[name][0], sgn)


def mirror_x(w):
    return w.mirror("YZ")


def same_after_mirror(a, b):
    """Percent of a's volume shared with the mirror image of b, and of b's volume shared with mirror(a)."""
    m = mirror_x(b)
    return 100.0 * vol(a.intersect(m)) / vol(a), 100.0 * vol(a.intersect(m)) / vol(m)


bad = 0
print("pipes: B at x=%+.0f, C at x=%+.0f (front = -Y where the plate hangs, so B is on the LEFT seen from the front)" % (-cd.HX, cd.HX))
print("hinge axes: B x=%+.0f, C x=%+.0f   (mirror needs B = -C)" % (cd.hinge_x(-1), cd.hinge_x(1)))
print("plate x: %+.0f .. %+.0f, %.0f mm wide (centre %+.0f; symmetric needs centre 0)" % (cd.PLATE_X0, cd.PLATE_X1, cd.PLATE_X1 - cd.PLATE_X0, (cd.PLATE_X0 + cd.PLATE_X1) / 2))
print("arm x %+.0f, motors x %+.0f / %+.0f" % (cd.ARM_X, cd.MOTOR_XS[-1], cd.MOTOR_XS[1]))
# C-gap direction: the hand-frame gap faces +X (B, towards the plate); on C it must face -X (towards the plate)
gap_b = placed(-1, "sleeve").intersect(csl.box(40, 6, 20, (-60 + 34, 0, 0)))
gap_c = placed(1, "sleeve").intersect(csl.box(40, 6, 20, (60 - 34, 0, 0)))
print("C-gap faces the plate: B (wall in its +X mouth probe %.0f mm3), C (wall in its -X mouth probe %.0f mm3); must both be 0" % (vol(gap_b), vol(gap_c)))
bad += vol(gap_b) > 1 or vol(gap_c) > 1
bad += not (cd.hinge_x(-1) < -cd.HX and cd.hinge_x(1) > cd.HX)         # both hinges on the outer side of their pipes
print("hinges on the outer side of their pipes:", cd.hinge_x(-1) < -cd.HX and cd.hinge_x(1) > cd.HX)
for name in ("sleeve", "jaw", "wheels", "axle_pins", "jaw_wheels", "worm", "worm_wheels", "bearing_blocks", "gearbox", "drive_motor", "jaw_gearbox", "jaw_motor", "jaw_hinge_pin"):
    c, b = placed(1, name), placed(-1, name)
    pc, pb = same_after_mirror(c, b)
    bad += min(pc, pb) < 99.0
    print("  hand part %-14s C shares %5.1f %% with mirror(B)" % (name, pc))
for nm, _, _ in ch.hinge_parts(-1):
    b = dict((n, s) for n, s, _ in ch.hinge_parts(-1))[nm]
    c = dict((n, s) for n, s, _ in ch.hinge_parts(1))[nm]
    pc, pb = same_after_mirror(c, b)
    bad += min(pc, pb) < 99.0
    print("  hinge part %-20s C shares %5.1f %% with mirror(B)" % (nm, pc))
pc, pb = same_after_mirror(cg.plate, cg.plate)
bad += pc < 99.0
print("  plate (with tongues + notches) shares %5.1f %% with its own mirror" % pc)
for tag, sgn in csl.TAGS:
    hand = placed(sgn, "sleeve").union(placed(sgn, "jaw"))
    for ptag, psgn in csl.TAGS:
        pipe = csl.cyl(hs.R_PIPE, 200.0, "z", (psgn * csl.HAND_X, 0, 0))
        ov = vol(hand.intersect(pipe))
        bad += ov > 1e-3
        print("  hand %s clamped vs pipe %s: overlap %.2f mm3 (must be 0)" % (tag, ptag, ov))
print("plate needs %.0f mm for motor + arm + motor, has %.0f mm" % (cd.NEEDED_PLATE_W, cd.PLATE_X1 - cd.PLATE_X0))
print("TRUE MIRROR:", "yes" if bad == 0 and abs(cd.hinge_x(-1) + cd.hinge_x(1)) < 1e-6 else "NO")
