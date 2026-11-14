import cadquery as cq
import math
# cad/unit_v1_assembly.py — v3 (6 Nov 2026)
# v4 (14 Nov 2026, Viber #97): track loop widened, TX 250 -> 290 (pipes 60 mm in from the tank edge).
# v3: tank 300 tall (water 155 / store 145), top of track 1900, loop bottom run 150 above lid.
#     Spine is a 33.7 OD tube ending level with the top-run centreline; top and bottom brackets.
#     Track long sides in 3 x 378 pieces (joint rings shown). Growing pipe in 4 sections.
# Other sizes ASSUMED as before.
TW, TD, TH = 700.0, 400.0, 300.0
SHELF = 155.0; GP = 75.0; SP = 33.7
TX = 290.0; TR = 16.0; R = 150.0; LOOP_Y = -60.0
ZB = TH + 150.0; ZT = 1900.0 - TR
SLOPE = 12.0

def box(sx, sy, sz, cx, cy, z0):
    return cq.Workplane("XY").box(sx, sy, sz, centered=(True, True, False)).translate((cx, cy, z0))
def cyl(r, h, x, y, z0):
    return cq.Workplane("XY").circle(r).extrude(h).translate((x, y, z0))
def tube(ro, ri, h, x, y, z0):
    return cyl(ro, h, x, y, z0).cut(cyl(ri, h + 2, x, y, z0 - 1))
def many(fn, pts):
    out = None
    for p in pts:
        s = fn(*p); out = s if out is None else out.union(s)
    return out

assy = cq.Assembly()
def add(o, n, c): assy.add(o, name=n, color=cq.Color(*c))

add(box(TW, TD, TH, 0, 0, 0).cut(box(TW - 8, TD - 8, TH, 0, 0, 4)), "tank", (0.75, 0.75, 0.8, 0.35))
add(box(196, TD - 12, 150, -246, 0, 4).cut(box(190, TD - 18, 150, -246, 0, 7)), "clean_bucket", (0.5, 0.75, 1.0, 0.6))
add(box(486, TD - 12, 150, 101, 0, 4).cut(box(480, TD - 18, 150, 101, 0, 7)), "nutrient_bucket", (0.4, 0.75, 0.5, 0.6))
add(box(TW - 8, TD - 8, 4, 0, 0, SHELF), "shelf", (0.5, 0.5, 0.55, 0.6))
add(box(190, 360, 35, -245, 0, 230), "seedling_tray", (0.3, 0.7, 0.4, 1))

row_xs = [-140 + 17.5 + 35 * i for i in range(14)]
long_x = [x for x in row_xs if abs(x) >= 77.5]
short_x = [x for x in row_xs if abs(x) < 77.5]
def row(x, y_end, L):
    yc = y_end - L / 2
    zc = 190.0 + (L / 2) * math.tan(math.radians(SLOPE))
    b = cq.Workplane("XY").box(31, L, 30).translate((x, yc, zc))
    return b.rotate((x, yc, zc), (x + 1, yc, zc), -SLOPE)
add(many(row, [(x, 0, 190) for x in long_x] + [(x, -70, 130) for x in short_x]), "store_rows_sloped", (0.3, 0.55, 0.85, 1))
add(box(TW, TD, 4, 0, 0, TH), "lid", (0.6, 0.6, 0.65, 0.6))

add(tube(GP / 2 + 10, GP / 2 + 1, 25, 0, 0, TH + 4), "socket", (0.95, 0.6, 0.2, 1))
add(tube(GP / 2, GP / 2 - 3, 250, 0, 0, TH + 4), "cleanout_section", (0.8, 0.8, 0.82, 1))
add(tube(GP / 2 + 4, GP / 2 + 0.5, 100, 0, 0, TH + 140), "sleeve", (0.3, 0.55, 0.85, 1))
z0 = TH + 254
add(tube(GP / 2, GP / 2 - 3, ZT - z0, 0, 0, z0), "growing_pipe", (0.95, 0.95, 0.95, 1))
seg = (ZT - z0) / 4
add(many(lambda z: tube(GP / 2 + 3, GP / 2, 8, 0, 0, z), [(z0 - 4 + i * seg,) for i in range(4)]), "pipe_joints", (0.95, 0.6, 0.2, 1))
sites = []
n_lv = int((ZT - z0 - 150) // 130)
for k in range(n_lv):
    for j in range(3):
        a = math.radians(j * 120 + (60 if k % 2 else 0))
        sites.append((GP / 2 * math.cos(a), GP / 2 * math.sin(a), z0 + 100 + k * 130))
add(many(lambda x, y, z: box(26, 26, 26, x, y, z - 13), sites), "pod_sites", (0.4, 0.75, 0.3, 1))
add(tube(SP / 2, SP / 2 - 2, ZT, 0, 0, 0), "spine_tube", (0.35, 0.35, 0.35, 1))

straights = [
    cyl(TR, (ZT - R) - (ZB + R), -TX, LOOP_Y, ZB + R),
    cyl(TR, (ZT - R) - (ZB + R), TX, LOOP_Y, ZB + R),
    cq.Workplane("YZ").circle(TR).extrude(2 * (TX - R)).translate((-(TX - R), LOOP_Y, ZT)),
    cq.Workplane("YZ").circle(TR).extrude(2 * (TX - R)).translate((-(TX - R), LOOP_Y, ZB)),
]
track = straights[0]
for s in straights[1:]:
    track = track.union(s)
def corner(cx, cz, start_deg):
    t = cq.Solid.makeTorus(R, TR, pnt=cq.Vector(cx, LOOP_Y, cz), dir=cq.Vector(0, 1, 0))
    tw = cq.Workplane("XY").add(t)
    qx = 1 if start_deg in (0, 270) else -1
    qz = 1 if start_deg in (0, 90) else -1
    clip = box(R + TR + 2, 4 * TR, R + TR + 2, cx + qx * (R + TR + 2) / 2, LOOP_Y, cz if qz > 0 else cz - (R + TR + 2))
    return tw.intersect(clip)
track = track.union(corner(-TX + R, ZT - R, 90)).union(corner(TX - R, ZT - R, 0)) \
             .union(corner(TX - R, ZB + R, 270)).union(corner(-TX + R, ZB + R, 180))
add(track, "track_loop", (0.7, 0.7, 0.72, 1))
long_len = (ZT - R) - (ZB + R)
jz = [ZB + R + long_len * f for f in (0.0, 1/3, 2/3, 1.0)]
add(many(lambda x, z: cq.Workplane("XY").circle(TR + 1.5).circle(TR).extrude(6).translate((x, LOOP_Y, z - 3)),
         [(x, z) for x in (-TX, TX) for z in jz]), "track_joints", (0.95, 0.6, 0.2, 1))
add(many(lambda z: box(16, abs(LOOP_Y) - GP / 2 + 4, 40, 0, LOOP_Y / 2 - GP / 4 - 2, z - 20) if False else
         box(16, abs(LOOP_Y) - GP / 2 + 6, 30, 0, -(GP / 2 + (abs(LOOP_Y) - GP / 2) / 2), z - 15), [(ZT,), (ZB,)]),
    "spine_brackets", (0.2, 0.2, 0.2, 1))
add(box(70, 90, 110, TX, LOOP_Y, ZB + R + 50), "cart_low_on_B", (0.9, 0.2, 0.2, 1))
result = assy
