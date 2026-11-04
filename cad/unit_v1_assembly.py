# cad/unit_v1_assembly.py — MVP draft v1 whole-unit concept, v2 (4 Nov 2026)
# v2: track is a CLOSED loop with 150 mm radius corners, bottom run ~15 cm above the tank lid.
#     The loop plane is set 60 mm in FRONT of the growing pipe (y=-60) so the bottom and top
#     runs clear the pipe and spine (ASSUMED - real offset TBC).
#     Store rows now slope 12 deg, high at the front (loading), low at the pick line.
# Height 1.80 m (decided). Other sizes ASSUMED.
import cadquery as cq
import math

TW, TD, TH = 700.0, 400.0, 400.0
H = 1800.0; GP = 75.0; TX = 250.0
TR = 16.0; BEND_R = 150.0
LOOP_Y = -60.0
ZB = TH + 150.0; ZT = H - 40.0
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
        s = fn(*p)
        out = s if out is None else out.union(s)
    return out

assy = cq.Assembly()
def add(o, n, c):
    assy.add(o, name=n, color=cq.Color(*c))

tank = box(TW, TD, TH, 0, 0, 0).cut(box(TW - 8, TD - 8, TH, 0, 0, 4))
add(tank, "tank", (0.75, 0.75, 0.8, 0.35))
add(box(TW - 8, TD - 8, 4, 0, 0, 200), "shelf", (0.5, 0.5, 0.55, 0.6))
add(box(200, TD - 8, 150, -246, 0, 4), "clean_water", (0.5, 0.75, 1.0, 0.6))
add(box(480, TD - 8, 150, 106, 0, 4), "dosed_water", (0.4, 0.75, 0.5, 0.6))
add(box(190, 360, 35, -245, 0, 330), "seedling_tray", (0.3, 0.7, 0.4, 1))

# sloped store rows: high at front (y=-190), low at pick end
row_xs = [-140 + 17.5 + 35 * i for i in range(14)]
long_x = [x for x in row_xs if abs(x) >= 77.5]
short_x = [x for x in row_xs if abs(x) < 77.5]
def row(x, y_end, L):
    yc = y_end - L / 2
    zc = 290.0 + (L / 2) * math.tan(math.radians(SLOPE))
    b = cq.Workplane("XY").box(31, L, 30).translate((x, yc, zc))
    return b.rotate((x, yc, zc), (x + 1, yc, zc), -SLOPE)
rows = many(row, [(x, 0, 190) for x in long_x] + [(x, -70, 130) for x in short_x])
add(rows, "store_rows_sloped", (0.3, 0.55, 0.85, 1))

pts = [(x, 0) for x in long_x] + [(x, -70) for x in short_x] + \
      [(-312 + 45 * i, -105 + 70 * j) for i in range(4) for j in range(4)]
add(box(TW, TD, 4, 0, 0, TH), "lid", (0.6, 0.6, 0.65, 0.6))
add(many(lambda x, y: cyl(18, 12, x, y, TH + 4), pts), "membranes_on_collars", (0.95, 0.35, 0.35, 1))

add(box(470, 6, 110, 105, -TD / 2 - 6, 270), "front_flap", (0.95, 0.75, 0.3, 1))
add(many(lambda x, y: box(24, 10, 14, x, y, 360), [(-60, -TD / 2 - 14), (270, -TD / 2 - 14)]), "latches", (0.2, 0.2, 0.2, 1))

add(tube(GP / 2 + 10, GP / 2 + 1, 25, 0, 0, TH + 4), "socket", (0.95, 0.6, 0.2, 1))
add(tube(GP / 2, GP / 2 - 3, 250, 0, 0, TH + 4), "cleanout_section", (0.8, 0.8, 0.82, 1))
add(tube(GP / 2 + 4, GP / 2 + 0.5, 100, 0, 0, TH + 140), "sleeve", (0.3, 0.55, 0.85, 1))
z0 = TH + 254
add(tube(GP / 2, GP / 2 - 3, H - z0, 0, 0, z0), "growing_pipe", (0.95, 0.95, 0.95, 1))
add(many(lambda z: tube(GP / 2 + 3, GP / 2, 8, 0, 0, z), [(z0 - 4,), (z0 + 376,), (z0 + 756,)]), "joints", (0.95, 0.6, 0.2, 1))
sites = []
for k in range(8):
    for j in range(3):
        a = math.radians(j * 120 + (60 if k % 2 else 0))
        sites.append((GP / 2 * math.cos(a), GP / 2 * math.sin(a), z0 + 100 + k * 130))
add(many(lambda x, y, z: box(26, 26, 26, x, y, z - 13), sites), "pod_sites_24", (0.4, 0.75, 0.3, 1))
add(cyl(10, H, 0, 0, 0), "spine", (0.35, 0.35, 0.35, 1))

# closed track loop with rounded corners, built from straights + quarter-torus corners
R = BEND_R
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
    # keep one quadrant
    qx = 1 if start_deg in (0, 270) else -1
    qz = 1 if start_deg in (0, 90) else -1
    clip = box(R + TR + 2, 4 * TR, R + TR + 2, cx + qx * (R + TR + 2) / 2, LOOP_Y, cz if qz > 0 else cz - (R + TR + 2))
    return tw.intersect(clip)
track = track.union(corner(-TX + R, ZT - R, 90)).union(corner(TX - R, ZT - R, 0)) \
             .union(corner(TX - R, ZB + R, 270)).union(corner(-TX + R, ZB + R, 180))
add(track, "track_loop_closed", (0.7, 0.7, 0.72, 1))
add(box(70, 90, 110, TX, LOOP_Y, ZB + R + 50), "cart_low_on_B", (0.9, 0.2, 0.2, 1))

result = assy
