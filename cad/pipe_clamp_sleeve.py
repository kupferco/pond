"""Test part: a C-clamp sleeve for a 32 mm pipe.

A split ring that slips over the pipe, with two ears either side of the slit and a
through-bolt that pinches it closed. All dimensions in mm, Z along the pipe axis.
Render it with the Pond `render_cad` tool (it reads the `result` variable).
"""

import math

import cadquery as cq

# ---- parameters ---------------------------------------------------------------
PIPE_OD = 32.0      # pipe outer diameter
CLEARANCE = 0.3     # radial clearance between pipe and bore
WALL = 4.0          # ring wall thickness
LENGTH = 40.0       # sleeve length along the pipe
GAP = 4.0           # width of the slit between the ears
EAR_T = 8.0         # ear thickness (each ear, across the slit)
EAR_L = 12.0        # how far the ears stick out radially
EAR_H = 16.0        # ear height along the pipe axis
BOLT_D = 5.5        # clearance hole for an M5 bolt
FILLET = 1.0

# ---- derived ------------------------------------------------------------------
BORE_D = PIPE_OD + 2 * CLEARANCE
RING_OD = BORE_D + 2 * WALL
EAR_Y0 = -(RING_OD / 2 + EAR_L)      # outer edge of the ears (−Y side)
EAR_Y1 = -(BORE_D / 2)               # ears reach in to the bore edge, so they fuse with the ring
EAR_LEN = EAR_Y1 - EAR_Y0
EAR_Z0 = (LENGTH - EAR_H) / 2

# ---- build --------------------------------------------------------------------
ring = cq.Workplane("XY").circle(RING_OD / 2).circle(BORE_D / 2).extrude(LENGTH)

# Slit through the wall on the −Y side, full length.
slit = (
    cq.Workplane("XY")
    .box(GAP, RING_OD, LENGTH + 2, centered=(True, False, False))
    .translate((0, -RING_OD, -1))
)
ring = ring.cut(slit)


def ear(x_sign: float) -> cq.Workplane:
    x0 = x_sign * GAP / 2
    x1 = x_sign * (GAP / 2 + EAR_T)
    return (
        cq.Workplane("XY")
        .box(EAR_T, EAR_LEN, EAR_H, centered=False)
        .translate((min(x0, x1), EAR_Y0, EAR_Z0))
    )


part = ring.union(ear(+1)).union(ear(-1))

# Bolt hole through both ears, along X.
bolt = (
    cq.Workplane("YZ")
    .center((EAR_Y0 + (-RING_OD / 2)) / 2, LENGTH / 2)
    .circle(BOLT_D / 2)
    .extrude(RING_OD, both=True)
)
part = part.cut(bolt)

try:
    part = part.edges("|Z").fillet(FILLET)
except Exception:
    pass  # fillets are cosmetic; keep the part valid if OCC refuses

result = part

print(f"bore {BORE_D:.1f} mm, ring OD {RING_OD:.1f} mm, bolt centre at y={(EAR_Y0 + (-RING_OD / 2)) / 2:.1f}")
