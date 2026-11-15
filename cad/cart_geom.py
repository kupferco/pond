# cad/cart_geom.py: small shared helpers and the base plate of the cart (Viber #109, 15 Nov 2026).
# Moved out of cart_assembly.py unchanged so that cart_sleeves.py (hand with clamp jaw) and cart_assembly.py can both
# import them without a circular import (cart_assembly now imports the clamp hand from cart_sleeves). No geometry change.
import os
import sys
import cadquery as cq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cart_hinge as ch
from cart_dims import *   # noqa: F401,F403
PLATE_CY = (PLATE_Y0 + PLATE_Y1) / 2

def box(sx, sy, sz, c):
    return cq.Workplane("XY").box(sx, sy, sz).translate(c)

def cyl(r, h, axis, c):
    d = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}[axis]
    start = cq.Vector(*[c[i] - d[i] * h / 2 for i in range(3)])
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(r, h, start, cq.Vector(*d)))

def window(x0, x1, z0, z1):
    return box(x1 - x0, PLATE_T + 2, z1 - z0, ((x0 + x1) / 2, PLATE_CY, (z0 + z1) / 2))

def build_plate():
    """Plate hung between the two hinge axes: a solid 142 x 112 x 6 mm plate (at this width there is nothing left to
    open up), a worm-bracket tongue above each hinge, and a notch at each hinge
    end where the worm wheel flange sits. Holes and cable slots are added in cart_base.py."""
    plate = box(PLATE_X1 - PLATE_X0, PLATE_T, 2 * PLATE_ZH, ((PLATE_X0 + PLATE_X1) / 2, PLATE_CY, 0))
    top = PLATE_ZH
    for sgn in (-1, 1):
        xh, d = hinge_x(sgn), -sgn
        # worm-bracket tongue: starts 21 mm from the hinge axis (clear of the worm wheel), from the top rim up to TONGUE_Z1
        tx0, tx1 = ch.tongue_x_range(sgn)
        plate = plate.union(box(tx1 - tx0, PLATE_T, TONGUE_Z1 - top + 1.0, ((tx0 + tx1) / 2, PLATE_CY, (TONGUE_Z1 + top - 1.0) / 2)))
        # notch at the hinge end for the worm wheel flange (below the tongue)
        n0, n1 = sorted((xh + d * (HINGE_R + HINGE_CLEAR - 1.0), xh + d * (HORN_R + 2.0)))
        plate = plate.cut(box(n1 - n0, PLATE_T + 2, top - (KNUCKLE_Z - 2.0), ((n0 + n1) / 2, PLATE_CY, (top + KNUCKLE_Z - 2.0) / 2)))
    return plate

plate = build_plate()
