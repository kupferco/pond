import os, sys
import cadquery as cq
# cad/unit_v3_dimensioned.py — v1 (7 Nov 2026)
# v2 (14 Nov 2026, Viber #97): track loop widened, TX 250 -> 290 (pipes 60 mm in from the tank edge, so two touching
# tanks put pipe B and pipe C 120 mm apart); loop label 532 -> 612.
# v3 (20 Nov 2026, OpenPocket #365): single-source. Tank, lid, track, spine, growing pipe and the rest come from cad/parts/ (no copies here).
# The old 155 mm "shelf" and its seedling tray, and the red cart stand-in box, are gone (not in the current design); the water volume
# (normal level 150 mm) is drawn instead, with a "150 water" dimension.
# Unit v3 (simplified: no store rows, buckets, pod sites) with 3D dimension lines and labels in blue.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parts.unit_dims import *   # noqa: F401,F403
from parts.common import box
from parts.unit import unit_parts

KEEP = ("tank", "water_volume", "lid", "socket", "growing_pipe", "spine_tube", "track_loop", "spine_brackets")
assy = cq.Assembly()
def add(o, n, c): assy.add(o, name=n, color=cq.Color(*c))
for _n, _s, _c in unit_parts():
    if _n in KEEP:
        add(_s, _n, _c)
B = (0.1, 0.35, 0.85, 1)
YF = -260.0
def vdim(x, za, zb, label, side=1):
    g = box(4, 4, zb - za, x, YF, za).union(box(40, 4, 4, x, YF, za - 2)).union(box(40, 4, 4, x, YF, zb - 2))
    t = cq.Workplane("XZ").text(label, 45, 4, halign="left" if side > 0 else "right").translate((x + side * 30, YF, (za + zb) / 2))
    return g.union(t)
def hdim(xa, xb, z, label):
    g = box(xb - xa, 4, 4, (xa + xb) / 2, YF, z).union(box(4, 4, 40, xa, YF, z - 18)).union(box(4, 4, 40, xb, YF, z - 18))
    t = cq.Workplane("XZ").text(label, 45, 4).translate(((xa + xb) / 2, YF, z + 45))
    return g.union(t)
dims = vdim(480, 0, 1900, "1900")
dims = dims.union(vdim(-430, 0, TH, "300", -1))
dims = dims.union(vdim(-430, TH, ZB, "150", -1))
dims = dims.union(vdim(-520, 0, WATER_LEVEL, "150 water", -1))
dims = dims.union(vdim(-430, ZB - TR, ZT + TR, "1466 loop", -1))
dims = dims.union(hdim(-350, 350, -90, "700"))
dims = dims.union(hdim(-TX - TR, TX + TR, 1990, "612 loop"))
dims = dims.union(box(4, 400, 4, 420, 0, -40))
add(dims, "dimensions", B)
result = assy
