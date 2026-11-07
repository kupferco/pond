import cadquery as cq, math
# cad/unit_v3_aframe.py — v2 (7 Nov 2026)
# v2: adds back strut (lid back edge -> lower joint), inverted A-frame on top (top bar -> 3rd pipe joint),
#     V solar roof (2 x ~50 W panels, 700 x 540, 30 deg pitch) on the top bar, and 4 fold-out L feet
#     (depth 840 overall) with bolt/peg holes and sandbags.
# v1: lower A-frame in the spine plane (y=0) behind the track (y=-60), legs meet spine at z=1215.
TW, TD, TH = 700.0, 400.0, 300.0
GP = 75.0; SP = 33.7
TX = 250.0; TR = 16.0; R = 150.0; LOOP_Y = -60.0
ZB = TH + 150.0; ZT = 1900.0 - TR
ZJ1 = 1215.0; ZJ2 = 1547.5; FOOT_X = 340.0; LID = TH + 4; ZBAR = 1900.0
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
def U(a, b):
    if a is None: return b
    return a.union(b)
assy = cq.Assembly()
def add(o, n, c): assy.add(o, name=n, color=cq.Color(*c))
add(box(TW, TD, TH, 0, 0, 0).cut(box(TW - 8, TD - 8, TH, 0, 0, 4)), "tank", (0.75, 0.75, 0.8, 0.35))
add(box(TW, TD, 4, 0, 0, TH), "lid", (0.6, 0.6, 0.65, 0.6))
add(tube(GP / 2 + 10, GP / 2 + 1, 25, 0, 0, LID), "socket", (0.95, 0.6, 0.2, 1))
c1a, c1b = ZJ1 - 140, ZJ1 + 40
c2a, c2b = ZJ2 - 40, ZJ2 + 140
pipe = tube(GP / 2, GP / 2 - 3, c1a - LID, 0, 0, LID)
pipe = pipe.union(tube(GP / 2, GP / 2 - 3, c2a - c1b, 0, 0, c1b))
pipe = pipe.union(tube(GP / 2, GP / 2 - 3, ZT - c2b, 0, 0, c2b))
add(pipe, "growing_pipe", (0.95, 0.95, 0.95, 0.5))
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

def brace(zj, ends, ca, cb):
    coup = tube(GP / 2 + 5, GP / 2, cb - ca, 0, 0, ca)
    legs = None
    for e in ends:
        d = cq.Vector(e[0], e[1], e[2] - zj); Ld = d.Length; u = d.normalized()
        s0 = 40.0 / math.hypot(u.x, u.y)
        coup = coup.union(tdir(16, 12.5, 50, (u.x * s0, u.y * s0, zj + u.z * s0), (u.x, u.y, u.z)))
        legs = U(legs, cq.Workplane("XY").add(cq.Solid.makeCylinder(12.5, Ld - 22, cq.Vector(u.x * 22, u.y * 22, zj + u.z * 22), u)))
    return coup, legs
low_ends = [(-FOOT_X, 0, LID), (FOOT_X, 0, LID), (0, 196, LID)]
coup1, legs1 = brace(ZJ1, low_ends, c1a, c1b)
top_ends = [(-FOOT_X, 0, ZBAR), (FOOT_X, 0, ZBAR)]
coup2, legs2 = brace(ZJ2, top_ends, c2a, c2b)
add(coup1.union(coup2), "brace_couplings", (0.2, 0.4, 0.8, 1))
add(legs1, "lower_aframe_and_back_strut", (0.95, 0.6, 0.2, 1))
add(legs2, "upper_inverted_aframe", (0.95, 0.6, 0.2, 1))
hubs = tube(24, SP / 2, 30, 0, 0, ZJ1 - 15).union(tube(24, SP / 2, 30, 0, 0, ZJ2 - 15))
add(hubs, "spine_hubs", (0.15, 0.15, 0.15, 1))
lidp = box(FOOT_X - 50, 30, 20, -(50 + FOOT_X) / 2, 0, LID).union(box(FOOT_X - 50, 30, 20, (50 + FOOT_X) / 2, 0, LID))
lidp = lidp.union(box(70, 40, 6, -(FOOT_X - 20), 0, LID)).union(box(70, 40, 6, FOOT_X - 20, 0, LID)).union(box(40, 50, 6, 0, 175, LID))
add(lidp, "base_bar_and_lid_plates", (0.2, 0.4, 0.8, 1))
add(box(2 * FOOT_X + 40, 30, 20, 0, 0, ZBAR), "top_bar", (0.2, 0.4, 0.8, 1))

# solar roof: ridge along x, slopes front and back
PL, PW, PT, PITCH = 700.0, 540.0, 35.0, 30.0
ZE = ZBAR + 20
zr = ZE + PW * math.sin(math.radians(PITCH))
posts = box(20, 20, zr - ZE, -300, 0, ZE).union(box(20, 20, zr - ZE, 300, 0, ZE)).union(box(PL, 30, 30, 0, 0, zr - 30))
add(posts, "roof_posts_and_ridge", (0.2, 0.4, 0.8, 1))
panels = None
for sy, ang in ((-1, PITCH), (1, -PITCH)):
    p = cq.Workplane("XY").box(PL, PW, PT).rotate((0, 0, 0), (1, 0, 0), ang)
    yc = sy * (PW / 2) * math.cos(math.radians(PITCH))
    zc = zr - (PW / 2) * math.sin(math.radians(PITCH)) + 10
    panels = U(panels, p.translate((0, yc, zc)))
add(panels, "solar_panels", (0.08, 0.12, 0.35, 1))

# fold-out L feet with bolt / peg holes, sandbags on top
feet = None; bags = None
for sx in (-1, 1):
    for sy in (-1, 1):
        f = box(50, 220, 6, sx * 325, sy * 310, 0).union(box(50, 6, 80, sx * 325, sy * 203, 0))
        f = f.cut(cyl(5, 12, sx * 325, sy * 395, -3))
        feet = U(feet, f)
        bags = U(bags, box(110, 120, 55, sx * 325, sy * 315, 6))
add(feet, "fold_out_feet", (0.2, 0.2, 0.2, 1))
add(bags, "sandbags", (0.8, 0.7, 0.45, 1))
result = assy
