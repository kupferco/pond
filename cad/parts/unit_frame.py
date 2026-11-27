# cad/parts/unit_frame.py: the unit's frame parts (growing pipe, spine, clamp collars and legs, lid plates, top bar, solar panel and mount, feet,
# sandbags). The ONLY definition; moved unchanged from unit_v3_aframe.py (v6, Viber #97), which now only assembles them.
import math
import cadquery as cq
from .common import box, cyl, tube, tdir, union_all
from .unit_dims import (GP, SP, LR, TX, ZT, ZB, ZC1, ZC2, FOOT_X, LID, ZBAR, BAR_X, RP, RC, LOOP_Y)

PW_X, PD_Y, PT, TILT = 450.0, 350.0, 25.0, 23.0     # 30 W panel
ZPC = 2000.0


def pipe_socket():
    return tube(RP + 10, RP + 1, 25, 0, 0, LID)


def growing_pipe():
    return tube(RP, RP - 3, ZT - LID, 0, 0, LID)


def spine_tube():
    return tube(SP / 2, SP / 2 - 2, ZT, 0, 0, 0)


def spine_brackets():
    # from the central pipe's surface (1.5 mm into it) out to the track axis (#537: the track is LOOP_Y = -66, was a 30 mm block at y -60..-30)
    d = -LOOP_Y - (RP - 1.5)
    yc = -(RP - 1.5) - d / 2                      # centre of the block between the two
    return box(16, d, 30, 0, yc, ZT - 15).union(box(16, d, 30, 0, yc, ZB - 15))


def _collar(zc, ends):
    c = tube(RC, RP, 50, 0, 0, zc - 25)
    legs = []
    for e in ends:
        h = math.hypot(e[0], e[1])
        px, py = e[0] / h * (RC - 4), e[1] / h * (RC - 4)
        P = cq.Vector(px, py, zc)
        d = cq.Vector(e[0], e[1], e[2]) - P
        Ld = d.Length
        u = d.normalized()
        c = c.union(tdir(LR + 3, LR, 60, (P.x, P.y, P.z), (u.x, u.y, u.z)))
        s = P + u * 12
        legs.append(cq.Workplane("XY").add(cq.Solid.makeCylinder(LR, Ld - 12, s, u)))
    return c, union_all(legs)


def collars_and_legs():
    """((lower collar, lower A-frame legs + back strut), (upper collar, top triangle legs))."""
    return (_collar(ZC1, [(-FOOT_X, 0, LID), (FOOT_X, 0, LID), (0, 180, LID)]),
            _collar(ZC2, [(-BAR_X, 0, ZBAR), (BAR_X, 0, ZBAR)]))


def internal_spacers():
    return tube(RP - 3, SP / 2, 50, 0, 0, ZC1 - 25).union(tube(RP - 3, SP / 2, 50, 0, 0, ZC2 - 25))


def lid_plates():
    p = box(FOOT_X - 50, 20, 15, -(50 + FOOT_X) / 2, 0, LID).union(box(FOOT_X - 50, 20, 15, (50 + FOOT_X) / 2, 0, LID))
    return (p.union(box(50, 30, 5, -(FOOT_X - 10), 0, LID)).union(box(50, 30, 5, FOOT_X - 10, 0, LID))
            .union(box(30, 40, 5, 0, 175, LID)))


def top_bar():
    return box(2 * BAR_X + 20, 20, 15, 0, 0, ZBAR)


def solar_panel():
    return cq.Workplane("XY").box(PW_X, PD_Y, PT).rotate((0, 0, 0), (1, 0, 0), TILT).translate((0, 0, ZPC))


def panel_mount():
    t = math.tan(math.radians(TILT))
    out = []
    for x in (-150.0, 150.0):
        out.append(box(20, 260, 15, x, 0, ZBAR + 15))
        for y in (-110.0, 110.0):
            zu = ZPC + y * t - (PT / 2) / math.cos(math.radians(TILT))
            out.append(box(15, 15, max(zu - (ZBAR + 30) + 2, 4), x, y, ZBAR + 30))
    return union_all(out)


def fold_out_feet():
    out = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            f = box(50, 220, 6, sx * 325, sy * 310, 0).union(box(50, 6, 80, sx * 325, sy * 203, 0))
            out.append(f.cut(cyl(5, 12, sx * 325, sy * 395, -3)))
    return union_all(out)


def sandbags():
    return union_all([box(110, 120, 55, sx * 325, sy * 315, 6) for sx in (-1, 1) for sy in (-1, 1)])
