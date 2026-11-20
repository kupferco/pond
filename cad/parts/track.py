# cad/parts/track.py: the track loop (one 32 mm pipe round a rounded rectangle in the XZ plane at y = LOOP_Y). The ONLY definition.
# Modelled as a solid cylinder (the real pipe is 32 x 1.8; track_supports.py cuts the local bore for its nut plates).
import cadquery as cq
from .common import box, cyl
from .unit_dims import TX, TR, R, LOOP_Y, ZB, ZT

COLOR_TRACK = (0.7, 0.7, 0.72, 1)


def _corner(cx, cz, qx, qz):
    t = cq.Workplane("XY").add(cq.Solid.makeTorus(R, TR, pnt=cq.Vector(cx, LOOP_Y, cz), dir=cq.Vector(0, 1, 0)))
    clip = box(R + TR + 2, 4 * TR, R + TR + 2, cx + qx * (R + TR + 2) / 2, LOOP_Y, cz if qz > 0 else cz - (R + TR + 2))
    return t.intersect(clip)


def track_loop():
    L = (ZT - R) - (ZB + R)
    track = cyl(TR, L, -TX, LOOP_Y, ZB + R).union(cyl(TR, L, TX, LOOP_Y, ZB + R))
    for z in (ZT, ZB):
        track = track.union(cq.Workplane("YZ").circle(TR).extrude(2 * (TX - R)).translate((-(TX - R), LOOP_Y, z)))
    for cx, cz, qx, qz in [(-TX + R, ZT - R, -1, 1), (TX - R, ZT - R, 1, 1), (TX - R, ZB + R, 1, -1), (-TX + R, ZB + R, -1, -1)]:
        track = track.union(_corner(cx, cz, qx, qz))
    return track
