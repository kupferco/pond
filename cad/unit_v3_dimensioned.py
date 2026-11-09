import cadquery as cq
# cad/unit_v3_dimensioned.py — v1 (7 Nov 2026)
# Unit v3 (simplified: no store rows, buckets, pod sites) with 3D dimension lines and labels in blue.
TW, TD, TH = 700.0, 400.0, 300.0
SHELF = 155.0; GP = 75.0; SP = 33.7
TX = 250.0; TR = 16.0; R = 150.0; LOOP_Y = -60.0
ZB = TH + 150.0; ZT = 1900.0 - TR
def box(sx, sy, sz, cx, cy, z0):
    return cq.Workplane("XY").box(sx, sy, sz, centered=(True, True, False)).translate((cx, cy, z0))
def cyl(r, h, x, y, z0):
    return cq.Workplane("XY").circle(r).extrude(h).translate((x, y, z0))
def tube(ro, ri, h, x, y, z0):
    return cyl(ro, h, x, y, z0).cut(cyl(ri, h + 2, x, y, z0 - 1))
assy = cq.Assembly()
def add(o, n, c): assy.add(o, name=n, color=cq.Color(*c))
add(box(TW, TD, TH, 0, 0, 0).cut(box(TW - 8, TD - 8, TH, 0, 0, 4)), "tank", (0.75, 0.75, 0.8, 0.35))
add(box(TW - 8, TD - 8, 4, 0, 0, SHELF), "shelf", (0.5, 0.5, 0.55, 0.6))
add(box(190, 360, 35, -245, 0, 230), "seedling_tray", (0.3, 0.7, 0.4, 1))
add(box(TW, TD, 4, 0, 0, TH), "lid", (0.6, 0.6, 0.65, 0.6))
add(tube(GP / 2 + 10, GP / 2 + 1, 25, 0, 0, TH + 4), "socket", (0.95, 0.6, 0.2, 1))
add(tube(GP / 2, GP / 2 - 3, 250, 0, 0, TH + 4), "cleanout_section", (0.8, 0.8, 0.82, 1))
add(tube(GP / 2 + 4, GP / 2 + 0.5, 100, 0, 0, TH + 140), "sleeve", (0.3, 0.55, 0.85, 1))
z0 = TH + 254
add(tube(GP / 2, GP / 2 - 3, ZT - z0, 0, 0, z0), "growing_pipe", (0.95, 0.95, 0.95, 1))
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
dims = dims.union(vdim(-430, ZB - TR, ZT + TR, "1466 loop", -1))
dims = dims.union(hdim(-350, 350, -90, "700"))
dims = dims.union(hdim(-TX - TR, TX + TR, 1990, "532 loop"))
dims = dims.union(box(4, 400, 4, 420, 0, -40))
add(dims, "dimensions", B)
result = assy
