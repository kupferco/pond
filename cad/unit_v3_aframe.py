import cadquery as cq, math
# cad/unit_v3_aframe.py — v1 (7 Nov 2026)
# Unit v3 (simplified) plus an A-frame brace in the spine plane (y=0), behind the track (y=-60).
# Base bar across the lid, legs in angled lid sleeves, meeting the spine at the 2nd pipe joint (z=1215)
# through a coupling with downward sleeves + gaskets.
TW, TD, TH = 700.0, 400.0, 300.0
GP = 75.0; SP = 33.7
TX = 250.0; TR = 16.0; R = 150.0; LOOP_Y = -60.0
ZB = TH + 150.0; ZT = 1900.0 - TR
ZJ = 1215.0; FOOT_X = 340.0; FOOT_Z = TH + 4
def box(sx, sy, sz, cx, cy, z0):
    return cq.Workplane("XY").box(sx, sy, sz, centered=(True, True, False)).translate((cx, cy, z0))
def cyl(r, h, x, y, z0):
    return cq.Workplane("XY").circle(r).extrude(h).translate((x, y, z0))
def tube(ro, ri, h, x, y, z0):
    return cyl(ro, h, x, y, z0).cut(cyl(ri, h + 2, x, y, z0 - 1))
def tdir(ro, ri, L, p, d):
    p = cq.Vector(*p); d = cq.Vector(*d).normalized()
    o = cq.Solid.makeCylinder(ro, L, p, d); i = cq.Solid.makeCylinder(ri, L + 2, p - d, d)
    return cq.Workplane("XY").add(o.cut(i))
assy = cq.Assembly()
def add(o, n, c): assy.add(o, name=n, color=cq.Color(*c))
add(box(TW, TD, TH, 0, 0, 0).cut(box(TW - 8, TD - 8, TH, 0, 0, 4)), "tank", (0.75, 0.75, 0.8, 0.35))
add(box(TW, TD, 4, 0, 0, TH), "lid", (0.6, 0.6, 0.65, 0.6))
add(tube(GP / 2 + 10, GP / 2 + 1, 25, 0, 0, TH + 4), "socket", (0.95, 0.6, 0.2, 1))
add(tube(GP / 2, GP / 2 - 3, ZJ - 140 - (TH + 4), 0, 0, TH + 4), "pipe_lower", (0.95, 0.95, 0.95, 0.5))
add(tube(GP / 2, GP / 2 - 3, ZT - (ZJ + 40), 0, 0, ZJ + 40), "pipe_upper", (0.95, 0.95, 0.95, 0.5))
add(tube(SP / 2, SP / 2 - 2, ZT, 0, 0, 0), "spine_tube", (0.35, 0.35, 0.35, 1))
L = (ZT - R) - (ZB + R)
track = cyl(TR, L, -TX, LOOP_Y, ZB + R).union(cyl(TR, L, TX, LOOP_Y, ZB + R))
track = track.union(cq.Workplane("YZ").circle(TR).extrude(2 * (TX - R)).translate((-(TX - R), LOOP_Y, ZT)))
track = track.union(cq.Workplane("YZ").circle(TR).extrude(2 * (TX - R)).translate((-(TX - R), LOOP_Y, ZB)))
def corner(cx, cz, qx, qz):
    t = cq.Workplane("XY").add(cq.Solid.makeTorus(R, TR, pnt=cq.Vector(cx, LOOP_Y, cz), dir=cq.Vector(0, 1, 0)))
    clip = box(R + TR + 2, 4 * TR, R + TR + 2, cx + qx * (R + TR + 2) / 2, LOOP_Y, cz if qz > 0 else cz - (R + TR + 2))
    return t.intersect(clip)
for cx, cz, qx, qz in [(-TX + R, ZT - R, -1, 1), (TX - R, ZT - R, 1, 1), (TX - R, ZB + R, 1, -1), (-TX + R, ZB + R, -1, -1)]:
    track = track.union(corner(cx, cz, qx, qz))
add(track, "track_loop", (0.7, 0.7, 0.72, 1))
add(box(16, 30, 30, 0, -45, ZT - 15).union(box(16, 30, 30, 0, -45, ZB - 15)), "spine_brackets", (0.2, 0.2, 0.2, 1))
add(box(70, 90, 110, TX, LOOP_Y, ZB + R + 50), "cart", (0.9, 0.2, 0.2, 1))
# A-frame
coup = tube(GP / 2 + 5, GP / 2, 180, 0, 0, ZJ - 140)
legs = None; lidparts = None
for sx in (-1, 1):
    d = cq.Vector(sx * FOOT_X, 0, FOOT_Z - ZJ); Ld = d.Length; u = d.normalized()
    s0 = 40.0 * Ld / FOOT_X
    coup = coup.union(tdir(16, 12.5, 50, (u.x * s0, 0, ZJ + u.z * s0), (u.x, 0, u.z)))
    leg = cq.Workplane("XY").add(cq.Solid.makeCylinder(12.5, Ld - 22, cq.Vector(u.x * 22, 0, ZJ + u.z * 22), u))
    legs = leg if legs is None else legs.union(leg)
    up = (-u.x, 0, -u.z)
    lp = tdir(16, 12.5, 70, (sx * FOOT_X, 0, FOOT_Z), up).union(box(70, 40, 6, sx * (FOOT_X - 20), 0, FOOT_Z))
    lp = lp.union(box(FOOT_X - 50, 30, 20, sx * (50 + FOOT_X) / 2, 0, FOOT_Z))
    lidparts = lp if lidparts is None else lidparts.union(lp)
add(coup, "aframe_coupling", (0.2, 0.4, 0.8, 1))
add(legs, "aframe_legs", (0.95, 0.6, 0.2, 1))
add(lidparts, "base_bar_and_lid_sleeves", (0.2, 0.4, 0.8, 1))
add(tube(24, SP / 2, 30, 0, 0, ZJ - 15), "spine_hub", (0.15, 0.15, 0.15, 1))
result = assy
