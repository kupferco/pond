import cadquery as cq, math
# cad/unit_v3_aframe.py — v5 (7 Nov 2026)
# v5: legs no longer pass through the PVC. 50 mm metal clamp collars sit OUTSIDE the growing pipe with
#     long angled sleeves (60 mm) that take the 16 mm legs. Inside the pipe at each collar height, a spacer
#     ring between pipe and spine carries the load to the spine. Lower collar z=1215 (side legs + back strut),
#     top collar z=1547.5. 30 W panel 450 x 350 at 23 deg on a 400 mm top bar.
# v4: short collars but legs through drilled pipe. v3: single panel. v2: strut, feet, V roof. v1: lower A-frame.
TW, TD, TH = 700.0, 400.0, 300.0
GP = 75.0; SP = 33.7; LR = 8.0
TX = 250.0; TR = 16.0; R = 150.0; LOOP_Y = -60.0
ZB = TH + 150.0; ZT = 1900.0 - TR
ZC1 = 1215.0; ZC2 = 1547.5; FOOT_X = 340.0; LID = TH + 4; ZBAR = 1900.0; BAR_X = 200.0
RP = GP / 2; RC = RP + 3
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

def collar(zc, ends):
    c = tube(RC, RP, 50, 0, 0, zc - 25)
    legs = None
    for e in ends:
        h = math.hypot(e[0], e[1])
        px, py = e[0] / h * (RC - 4), e[1] / h * (RC - 4)
        P = cq.Vector(px, py, zc)
        d = cq.Vector(e[0], e[1], e[2]) - P; Ld = d.Length; u = d.normalized()
        c = c.union(tdir(LR + 3, LR, 60, (P.x, P.y, P.z), (u.x, u.y, u.z)))
        s = P + u * 12
        legs = U(legs, cq.Workplane("XY").add(cq.Solid.makeCylinder(LR, Ld - 12, s, u)))
    return c, legs
cA, legsA = collar(ZC1, [(-FOOT_X, 0, LID), (FOOT_X, 0, LID), (0, 180, LID)])
cB, legsB = collar(ZC2, [(-BAR_X, 0, ZBAR), (BAR_X, 0, ZBAR)])
add(cA.union(cB), "clamp_collars_50mm", (0.55, 0.57, 0.6, 1))
add(legsA, "lower_aframe_and_back_strut_16mm", (0.95, 0.6, 0.2, 1))
add(legsB, "top_triangle_legs_16mm", (0.95, 0.6, 0.2, 1))
spacers = tube(RP - 3, SP / 2, 50, 0, 0, ZC1 - 25).union(tube(RP - 3, SP / 2, 50, 0, 0, ZC2 - 25))
add(spacers, "internal_spacers", (0.1, 0.1, 0.1, 1))
lidp = box(FOOT_X - 50, 20, 15, -(50 + FOOT_X) / 2, 0, LID).union(box(FOOT_X - 50, 20, 15, (50 + FOOT_X) / 2, 0, LID))
lidp = lidp.union(box(50, 30, 5, -(FOOT_X - 10), 0, LID)).union(box(50, 30, 5, FOOT_X - 10, 0, LID)).union(box(30, 40, 5, 0, 175, LID))
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
result = assy
