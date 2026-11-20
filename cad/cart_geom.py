# cad/cart_geom.py: small shared helpers and the base plate of the cart (Viber #109, 15 Nov 2026; Pond #279: rigid plate, hinge references removed).
# Moved out of cart_assembly.py unchanged so that cart_sleeves.py (hand with clamp jaw) and cart_assembly.py can both
# import them without a circular import (cart_assembly now imports the clamp hand from cart_sleeves). No geometry change.
import os
import sys
import cadquery as cq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hand_sleeve as hs
from cart_dims import *   # noqa: F401,F403
PLATE_CY = (PLATE_Y0 + PLATE_Y1) / 2

def pad_x(sgn):
    """x of the centre of the pad (and its two bolt holes) of the hand on pipe B (sgn -1) or pipe C (sgn +1): on the outer side of the pipe."""
    return sgn * (HX - (hs.PAD_X0 + hs.PAD_X1) / 2)

def box(sx, sy, sz, c):
    return cq.Workplane("XY").box(sx, sy, sz).translate(c)

def cyl(r, h, axis, c):
    d = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}[axis]
    start = cq.Vector(*[c[i] - d[i] * h / 2 for i in range(3)])
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(r, h, start, cq.Vector(*d)))

def window(x0, x1, z0, z1):
    return box(x1 - x0, PLATE_T + 2, z1 - z0, ((x0 + x1) / 2, PLATE_CY, (z0 + z1) / 2))

def build_plate():
    """The rigid base plate: a plain PLATE_T mm slab from the outer edge of pad B to the outer edge of pad C, lying on the front
    faces of both sleeve pads (Pond #279: no hinges, no worm-bracket tongues, no notches). Two M4 clearance holes per pad, on the
    pad's hole pattern (hs.PAD_HOLE_Z), bolt it to both sleeves. Battery, arm and cable holes are added in cart_base.py."""
    p = box(PLATE_X1 - PLATE_X0, PLATE_T, 2 * PLATE_ZH, ((PLATE_X0 + PLATE_X1) / 2, PLATE_CY, 0))
    for sgn in (-1, 1):
        for z in (hs.PAD_HOLE_Z, -hs.PAD_HOLE_Z):
            p = p.cut(cyl(hs.PAD_HOLE_D / 2, PLATE_T + 2, "y", (pad_x(sgn), PLATE_CY, z)))
    return p

plate = build_plate()

def track_pipe(x, length, zc=0.0):
    """The track pipe stub the cart clamps (32 mm OD, along Z, at cart x), defined once: cart_assembly.py and cart_arm.py both use it."""
    return cyl(hs.R_PIPE, length, "z", (x, 0, zc))
