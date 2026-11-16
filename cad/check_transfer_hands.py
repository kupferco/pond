# cad/check_transfer_hands.py: is hand B a true mirror of hand C across the cart centre plane (x = 0)? (Pond #227)
# Read-only check, changes no geometry. Run: python cad/check_transfer_hands.py
import os
import sys
import cadquery as cq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cart_sleeves as csl
import cart_hinge as ch
import cart_dims as cd
import hand_sleeve as hs


def vol(w):
    return sum(s.Volume() for s in w.solids().vals()) if w.vals() else 0.0


def placed(tag, name):
    """A hand part as placed in the cart (x = pipe position)."""
    sgn = dict(csl.TAGS)[tag]
    return csl.hand_parts()[name][0].translate((sgn * csl.HAND_X, 0, 0))


def mirror_x(w):
    return w.mirror("YZ")


print("pipes: B at x=%+.0f, C at x=%+.0f (CAD; front = -Y where the plate hangs, so B is on the LEFT seen from the front)" % (-cd.HX, cd.HX))
print("hinge axes: B x=%+.0f, C x=%+.0f   (mirror needs B = -C)" % (cd.hinge_x(-1), cd.hinge_x(1)))
print("plate x: %+.0f .. %+.0f (centre %+.0f; symmetric needs centre 0)" % (cd.PLATE_X0, cd.PLATE_X1, (cd.PLATE_X0 + cd.PLATE_X1) / 2))
bad = 0
for name in ("sleeve", "jaw", "wheels", "worm", "drive_motor", "jaw_motor", "jaw_hinge_pin"):
    c, b = placed("C", name), placed("B", name)
    v = vol(c)
    common = vol(mirror_x(c).intersect(b))
    miss = 100.0 * (1 - common / v)
    bad += miss > 1.0
    print("  %-14s B shares %5.1f %% of its volume with mirror(C)" % (name, 100 - miss))
for tag, sgn in csl.TAGS:
    sleeve = csl.hand_parts()["sleeve"][0].translate((sgn * csl.HAND_X, 0, 0))
    jaw = csl.hand_parts()["jaw"][0].translate((sgn * csl.HAND_X, 0, 0))
    hand = sleeve.union(jaw)
    for ptag, psgn in csl.TAGS:
        pipe = csl.cyl(hs.R_PIPE, 200.0, "z", (psgn * csl.HAND_X, 0, 0))
        print("  hand %s clamped vs pipe %s: overlap %.2f mm3 (own pipe: must be 0; neighbour: must be 0)" % (tag, ptag, vol(hand.intersect(pipe))))
print("TRUE MIRROR:", "yes" if bad == 0 and abs(cd.hinge_x(-1) + cd.hinge_x(1)) < 1e-6 else "NO")
print("a mirrored B hand would need the plate to be %.0f mm wide (hinges at +/-%.0f) but the arm + motors need %.0f mm"
      % (2 * (cd.HX + cd.HINGE_OFF_C) - 2 * (cd.HINGE_R + cd.HINGE_CLEAR), cd.HX + cd.HINGE_OFF_C, cd.NEEDED_PLATE_W))
