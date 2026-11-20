# cad/parts/pods.py: simplified pods in the growing pipe's holes (4 per level, 100 mm apart, turning 45 degrees each level, ASSUMED), each a cup
# tilted 45 degrees up out of its hole with a dark cap. Moved from complete_unit.py (OpenPocket #311). Not detailed; see pipe_collar.py for a real pod.
import math
import cadquery as cq
from .common import union_all
from .unit_dims import GP, ZC1, ZC2

HOLE_PITCH, POD_D = 100.0, 25.0


def _rod(p, d, length, r):
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(r, length, cq.Vector(*p), cq.Vector(*d)))


def hole_levels():
    z, out = 400.0, []
    while z < 1840.0:
        if abs(z - ZC1) > 60 and abs(z - ZC2) > 60:
            out.append(z)
        z += HOLE_PITCH
    return out


def pods_and_caps():
    """(pods, caps) as two shapes; 4 holes per level."""
    pods, caps = [], []
    for i, z in enumerate(hole_levels()):
        for k in range(4):
            az = math.radians(90 * k + 45 * (i % 2) + 45)
            rad = (math.cos(az), math.sin(az), 0.0)
            c45, s45 = math.cos(math.radians(45)), math.sin(math.radians(45))
            d = (rad[0] * c45, rad[1] * c45, s45)
            p0 = (rad[0] * (GP / 2 - 6), rad[1] * (GP / 2 - 6), z)
            pods.append(_rod(p0, d, 50, POD_D / 2))
            p1 = tuple(p0[j] + d[j] * 50 for j in range(3))
            caps.append(_rod(p1, d, 16, POD_D / 2 + 4))
    return union_all(pods), union_all(caps)
