import cadquery as cq, math
# cad/unit_v3_aframe.py — v4 (7 Nov 2026)
# v4: bulky 180 mm couplings replaced by 50 mm metal clamp collars centred where each leg crosses the
#     pipe wall (pipe drilled, collar gasket seals). Legs 16 mm steel tube. Back strut aimed higher on the
#     spine so it crosses the pipe at the same height as the side legs (one collar). 30 W panel 450 x 350,
#     tilt 23 deg; top bar 400 mm. Growing pipe continuous again.
# v3: single 40 W panel on small top triangle. v2: back strut, feet, V roof. v1: lower A-frame.
TW, TD, TH = 700.0, 400.0, 300.0
GP = 75.0; SP = 33.7; LR = 8.0
TX = 250.0; TR = 16.0; R = 150.0; LOOP_Y = -60.0
ZB = TH + 150.0; ZT = 1900.0 - TR
ZJ1 = 1215.0; ZJ2 = 1547.5; FOOT_X = 340.0; LID = TH + 4; ZBAR = 1900.0; BAR_X = 200.0
RP = GP / 2
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
add(tube(RP + 10, RP + 1, 25, 0, 0, LID), "socket", (0.95, 0.6, 0.2, 1))
add(tube(RP, RP - 3, ZT - LID, 0, 0, LID), "growing_pipe", (0.95, 0.95, 0.95, 0.5))
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

def legs_to(zt, ends):
    # zt: where each leg meets the spine; returns legs, stubs, list of crossing heights
    legs = None; stubs = None; zc = []
    for e in ends:
        d = cq.Vector(e[0], e[1], e[2] - zt); Ld = d.Length; u = d.normalized()
        h = math.hypot(u.x, u.y)
        s_wall = RP / h
        zc.append(zt + u.z * s_wall)
        legs = U(legs, cq.Workplane("XY").add(cq.Solid.makeCylinder(LR, Ld - 18, cq.Vector(u.x * 18, u.y * 18, zt + u.z * 18), u)))
        s1 = (RP + 3) / h
        stubs = U(stubs, tdir(LR + 3, LR, 15, (u.x * s1, u.y * s1, zt + u.z * s1), (u.x, u.y, u.z)))
    return legs, stubs, zc
side = [(-FOOT_X, 0, LID), (FOOT_X, 0, LID)]
legsA, stubsA, zcA = legs_to(ZJ1, side)
zcross = zcA[0]
# back strut: choose spine meeting point so it crosses the pipe wall at the same height
db = cq.Vector(0, 196, 0)
dz_needed = None
# solve: zt_b + uz * (RP/h) = zcross, with direction from (0,0,zt_b) to (0,196,LID)
lo, hi = zcross, ZT
for _ in range(60):
    mid = (lo + hi) / 2
    v = cq.Vector(0, 196, LID - mid).normalized()
    zc_mid = mid + v.z * (RP / abs(v.y))
    if zc_mid < zcross: lo = mid
    else: hi = mid
ZBACK = (lo + hi) / 2
legsB, stubsB, _ = legs_to(ZBACK, [(0, 196, LID)])
legsT, stubsT, zcT = legs_to(ZJ2, [(-BAR_X, 0, ZBAR), (BAR_X, 0, ZBAR)])
collars = tube(RP + 3, RP, 50, 0, 0, zcross - 25).union(tube(RP + 3, RP, 50, 0, 0, zcT[0] - 25))
collars = collars.union(stubsA).union(stubsB).union(stubsT)
add(collars, "metal_collars_50mm", (0.55, 0.57, 0.6, 1))
add(legsA.union(legsB), "lower_aframe_and_back_strut_16mm", (0.95, 0.6, 0.2, 1))
add(legsT, "top_triangle_legs_16mm", (0.95, 0.6, 0.2, 1))
hubs = tube(22, SP / 2, 24, 0, 0, ZJ1 - 12).union(tube(22, SP / 2, 24, 0, 0, ZBACK - 12)).union(tube(22, SP / 2, 24, 0, 0, ZJ2 - 12))
add(hubs, "spine_hubs", (0.15, 0.15, 0.15, 1))
lidp = box(FOOT_X - 50, 20, 15, -(50 + FOOT_X) / 2, 0, LID).union(box(FOOT_X - 50, 20, 15, (50 + FOOT_X) / 2, 0, LID))
lidp = lidp.union(box(50, 30, 5, -(FOOT_X - 10), 0, LID)).union(box(50, 30, 5, FOOT_X - 10, 0, LID)).union(box(30, 40, 5, 0, 180, LID))
add(lidp, "base_bar_and_lid_plates", (0.55, 0.57, 0.6, 1))
add(box(2 * BAR_X + 20, 20, 15, 0, 0, ZBAR), "top_bar", (0.55, 0.57, 0.6, 1))
PW_X, PD_Y, PT, TILT = 450.0, 350.0, 25.0, 23.0
ZPC = 2000.0
t = math.tan(math.radians(TILT))
add(cq.Workplane("XY").box(PW_X, PD_Y, PT).rotate((0, 0, 0), (1, 0, 0), TILT).translate((0, 0, ZPC)), "solar_panel_30W", (0.08, 0.12, 0.35, 1))
mount = None
for x in (-150.0, 150.0):
    mount = U(mount, box(20, 260, 15, x, 0, ZBAR + 15))
    for y in (-110.0, 110.0):
        zu = ZPC + y * t - (PT / 2) / math.cos(math.radians(TILT))
        mount = U(mount, box(15, 15, max(zu - (ZBAR + 30) + 2, 4), x, y, ZBAR + 30))
add(mount, "panel_rails_and_posts", (0.55, 0.57, 0.6, 1))
feet = None; bags = None
for sx in (-1, 1):
    for sy in (-1, 1):
        f = box(50, 220, 6, sx * 325, sy * 310, 0).union(box(50, 6, 80, sx * 325, sy * 203, 0))
        f = f.cut(cyl(5, 12, sx * 325, sy * 395, -3))
        feet = U(feet, f)
        bags = U(bags, box(110, 120, 55, sx * 325, sy * 315, 6))
add(feet, "fold_out_feet", (0.2, 0.2, 0.2, 1))
add(bags, "sandbags", (0.8, 0.7, 0.45, 1))
print("lower collar z", round(zcross, 1), "back strut meets spine z", round(ZBACK, 1), "top collar z", round(zcT[0], 1))
result = assy
