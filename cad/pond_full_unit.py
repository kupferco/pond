import cadquery as cq
import math
# FULL POND UNIT, one assembly (26 Nov 2026, v2: elbow OUT, away from the cart; clash check arm vs cart).
# Every number copied from main: cad/layout.json, cad/parts/unit_dims.py, unit_frame.py, track.py, tank.py, shelf.py, shelf_items.py,
# water_station.py (the render sandbox cannot import them; keep in sync).
# Cart: upright (the pod grab sim #522 rejected the 45 deg roll). Cart/arm simplified to cart_assembly.py sizes: plate 166 x 112 x 6,
# two 90 mm sleeves (R34) on the track, battery 70x50x70, SO-101 arm L1 116 / L2 135 (ASSUMED shoulder 144 out, 60 under the track axis).
# Shown twice on the bottom run: over the seedling tray (x -130) and at the pod store (x +130), the ends of the straight run.

TW, TD, TH, WALL, LID_T = 700.0, 400.0, 300.0, 4.0, 4.0
LID = TH + LID_T
GP, SP, LR = 75.0, 33.7, 8.0
RP = GP / 2; RC = RP + 3
TX, TR, R, LOOP_Y = 290.0, 16.0, 150.0, -60.0
ZB = 514.0; ZT = 1900.0 - TR
ZC1, ZC2 = 1215.0, 1547.5
FOOT_X, ZBAR, BAR_X = 340.0, 1900.0, 200.0
SHELF_Z, SHELF_T = 155.0, 4.0; SHELF_TOP = SHELF_Z + SHELF_T

def box(sx, sy, sz, cx, cy, z0):
    return cq.Workplane("XY").box(sx, sy, sz, centered=(True, True, False)).translate((cx, cy, z0))
def bxx(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))
def cyl(r, h, x, y, z0):
    return cq.Workplane("XY").circle(r).extrude(h).translate((x, y, z0))
def tube(ro, ri, h, x, y, z0):
    return cq.Workplane("XY").circle(ro).circle(ri).extrude(h).translate((x, y, z0))
def rod(p0, p1, r):
    v = cq.Vector(*p1) - cq.Vector(*p0)
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(r, v.Length, cq.Vector(*p0), v.normalized()))
def U(ps):
    o = None
    for p in ps:
        o = p if o is None else o.union(p)
    return o

tank = box(TW, TD, TH, 0, 0, 0).cut(box(TW - 2 * WALL, TD - 2 * WALL, TH, 0, 0, WALL))
shelf = box(TW - 2 * WALL, TD - 2 * WALL, SHELF_T, 0, 0, SHELF_Z).cut(cyl(SP / 2 + 1, SHELF_T + 2, 0, 0, SHELF_Z - 1))
TRAY_XS = list(range(-290, -80, 35)); TRAY_YS = (-150, -125, -100)
STORE_XS = [100 + 30 * i for i in range(7)]; STORE_Y = -165.0
lid = box(TW, TD, LID_T, 0, 0, TH)
for x in TRAY_XS:
    for y in TRAY_YS:
        lid = lid.cut(cyl(16, 10, x, y, TH - 1))
for x in STORE_XS:
    lid = lid.cut(cyl(16, 10, x, STORE_Y, TH - 1))
lid = lid.cut(cyl(RP + 1, 10, 0, 0, TH - 1))
tray = U([box(240, 110, 6, -190, -125, SHELF_TOP)] + [box(25, 18, 24, x, y, SHELF_TOP + 6) for x in TRAY_XS for y in TRAY_YS])
storage = U([box(240, 110, 12, 190, -125, SHELF_TOP)] + [box(230, 14, 36, 190, -165 + 20 * k, SHELF_TOP + 12) for k in range(5)])
POD_TOP_T, POD_TOP_S = SHELF_TOP + 46, SHELF_TOP + 48
pods = U([cyl(12.5, 40, x, y, POD_TOP_T - 40) for x in TRAY_XS for y in TRAY_YS] +
         [cyl(12.5, 40, x, STORE_Y, POD_TOP_S - 40) for x in STORE_XS])

pillar = tube(RP, RP - 3, ZT - LID, 0, 0, LID)
socket = tube(RP + 10, RP + 1, 25, 0, 0, LID)
spine = tube(SP / 2, SP / 2 - 2, ZT, 0, 0, 0)
brackets = box(16, 30, 30, 0, -45, ZT - 15).union(box(16, 30, 30, 0, -45, ZB - 15))

def collar(zc, ends):
    c = tube(RC, RP, 50, 0, 0, zc - 25); legs = []
    for e in ends:
        h = math.hypot(e[0], e[1]); P = (e[0] / h * (RC - 4), e[1] / h * (RC - 4), zc)
        legs.append(rod(P, e, LR))
    return c, U(legs)
c1, legs1 = collar(ZC1, [(-FOOT_X, 0, LID), (FOOT_X, 0, LID), (0, 180, LID)])
c2, legs2 = collar(ZC2, [(-BAR_X, 0, ZBAR), (BAR_X, 0, ZBAR)])
lid_plates = U([box(FOOT_X - 50, 20, 15, -(50 + FOOT_X) / 2, 0, LID), box(FOOT_X - 50, 20, 15, (50 + FOOT_X) / 2, 0, LID),
                box(50, 30, 5, -(FOOT_X - 10), 0, LID), box(50, 30, 5, FOOT_X - 10, 0, LID), box(30, 40, 5, 0, 175, LID)])
top_bar = box(2 * BAR_X + 20, 20, 15, 0, 0, ZBAR)
feet = U([box(50, 220, 6, sx * 325, sy * 310, 0).union(box(50, 6, 80, sx * 325, sy * 203, 0)) for sx in (-1, 1) for sy in (-1, 1)])
TILT, ZPC = 23.0, 2000.0
panel = cq.Workplane("XY").box(450, 350, 25).rotate((0, 0, 0), (1, 0, 0), TILT).translate((0, 0, ZPC))
t = math.tan(math.radians(TILT)); mounts = []
for x in (-150.0, 150.0):
    mounts.append(box(20, 260, 15, x, 0, ZBAR + 15))
    for y in (-110.0, 110.0):
        zu = ZPC + y * t - 12.5 / math.cos(math.radians(TILT))
        mounts.append(box(15, 15, max(zu - (ZBAR + 30) + 2, 4), x, y, ZBAR + 30))
mounts = U(mounts)

def corner(cx, cz, qx, qz):
    tor = cq.Workplane("XY").add(cq.Solid.makeTorus(R, TR, pnt=cq.Vector(cx, LOOP_Y, cz), dir=cq.Vector(0, 1, 0)))
    clip = box(R + TR + 2, 4 * TR, R + TR + 2, cx + qx * (R + TR + 2) / 2, LOOP_Y, cz if qz > 0 else cz - (R + TR + 2))
    return tor.intersect(clip)
L = (ZT - R) - (ZB + R)
track = cyl(TR, L, -TX, LOOP_Y, ZB + R).union(cyl(TR, L, TX, LOOP_Y, ZB + R))
for z in (ZT, ZB):
    track = track.union(cq.Workplane("YZ").circle(TR).extrude(2 * (TX - R)).translate((-(TX - R), LOOP_Y, z)))
for cx, cz, qx, qz in [(-TX + R, ZT - R, -1, 1), (TX - R, ZT - R, 1, 1), (TX - R, ZB + R, 1, -1), (-TX + R, ZB + R, -1, -1)]:
    track = track.union(corner(cx, cz, qx, qz))

station = bxx(60, 260, 14, 108, 394, 504)
st_roof = bxx(52, 268, 14, 116, 504, 507)
st_legs = U([bxx(x0, x0 + 20, y0, y0 + 20, LID, 394) for x0 in (60, 240) for y0 in (22, 80)])

# ---------------- cart + SO-101 arm (upright) ----------------
L1, L2, CLAW = 116.0, 135.0, 100.0
def cart(x0):
    sleeves = U([cq.Workplane("YZ").circle(34).circle(TR + 1).extrude(90).translate((x0 + s - 45, LOOP_Y, ZB)) for s in (-60, 60)])
    pads = U([box(40, 20, 40, x0 + s, LOOP_Y - 40, ZB - 20) for s in (-60, 60)])
    plate = box(166, 6, 112, x0, LOOP_Y - 53, ZB - 60 - 56)
    batt = box(70, 50, 70, x0, LOOP_Y - 81, ZB - 60 - 35)
    base = box(70, 30, 70, x0, LOOP_Y - 121, ZB - 60 - 35)
    return sleeves.union(pads).union(plate).union(batt).union(base)

def arm(x0, grip):
    """2-link IK in the vertical plane through shoulder and wrist; elbow chosen on the side AWAY from the cart (most negative y)."""
    S = (x0, LOOP_Y - 144, ZB - 60)
    W = (grip[0], grip[1], grip[2] + CLAW)
    hx, hy = W[0] - S[0], W[1] - S[1]; hu = math.hypot(hx, hy); dz = W[2] - S[2]; d = math.hypot(hu, dz)
    a = math.atan2(dz, hu); b = math.acos(max(-1, min(1, (L1**2 + d**2 - L2**2) / (2 * L1 * d))))
    cands = []
    for s in (1, -1):
        u, z = L1 * math.cos(a + s * b), L1 * math.sin(a + s * b)
        cands.append((S[0] + hx / hu * u, S[1] + hy / hu * u, S[2] + z))
    E = min(cands, key=lambda e: e[1])
    links = rod(S, E, 12).union(rod(E, W, 10))
    shp = links.union(rod(W, grip, 7))
    for p in (S, E, W):
        shp = shp.union(cq.Workplane("XY").sphere(15).translate(p))
    return shp, links, d, E, W

cart_t, cart_s = cart(-130.0), cart(130.0)
# cart solids the arm must not pass through (its own base, where the shoulder sits, is excluded)
def body(x0):
    return box(166, 6, 112, x0, LOOP_Y - 53, ZB - 60 - 56).union(box(70, 50, 70, x0, LOOP_Y - 81, ZB - 60 - 35))
lim = L1 + L2
for label, x0, grip in [("tray middle cell", -130.0, (-185.0, -125.0, POD_TOP_T + 5)),
                        ("tray near row", -130.0, (-115.0, -100.0, POD_TOP_T + 5)),
                        ("tray far corner", -130.0, (-290.0, -150.0, POD_TOP_T + 5)),
                        ("store front row", 130.0, (190.0, STORE_Y, POD_TOP_S + 5))]:
    _, links, d, E, W = arm(x0, grip)
    clash = links.intersect(body(x0)).val().Volume() if True else 0
    lidhit = links.intersect(lid).val().Volume()
    print("%-17s reach %4.0f/%.0f  elbow y %5.0f z %4.0f  wrist z %4.0f  clash with cart %6.0f mm3  with lid %6.0f mm3" %
          (label, d, lim, E[1], E[2], W[2], clash, lidhit))

arm_t, *_ = arm(-130.0, (-185.0, -125.0, POD_TOP_T + 5))
arm_s, *_ = arm(130.0, (190.0, STORE_Y, POD_TOP_S + 5))

C = cq.Color
assy = cq.Assembly()
for obj, name, col in [
    (tank, "tank", C(0.75, 0.75, 0.8, 0.25)), (shelf, "shelf", C(0.5, 0.5, 0.55, 0.4)), (lid, "lid_with_pick_holes", C(0.6, 0.6, 0.65, 0.55)),
    (tray, "seedling_tray", C(0.59, 0.43, 0.27)), (storage, "pod_storage", C(0.35, 0.5, 0.75)), (pods, "pods", C(0.24, 0.67, 0.31)),
    (pillar, "growing_pipe", C(0.95, 0.95, 0.95, 0.8)), (socket, "pillar_socket", C(0.95, 0.6, 0.2)), (spine, "spine", C(0.35, 0.35, 0.35)),
    (brackets, "pillar_to_track_brackets", C(0.95, 0.6, 0.2)), (c1, "lower_collar", C(0.95, 0.6, 0.2)), (legs1, "a_frame_legs", C(0.55, 0.57, 0.6)),
    (c2, "upper_collar", C(0.95, 0.6, 0.2)), (legs2, "top_triangle_legs", C(0.55, 0.57, 0.6)), (lid_plates, "lid_plates", C(0.55, 0.57, 0.6)),
    (top_bar, "top_bar", C(0.55, 0.57, 0.6)), (feet, "feet", C(0.4, 0.4, 0.42)), (panel, "solar_panel", C(0.15, 0.2, 0.4)),
    (mounts, "panel_mount", C(0.55, 0.57, 0.6)), (track, "track_loop", C(0.7, 0.7, 0.72)),
    (station, "water_station", C(0.93, 0.93, 0.9)), (st_roof, "water_station_roof", C(0.82, 0.82, 0.78)), (st_legs, "water_station_legs", C(0.55, 0.57, 0.6)),
    (cart_t, "cart_over_tray", C(0.25, 0.25, 0.3)), (arm_t, "arm_over_tray", C(0.9, 0.15, 0.15)),
    (cart_s, "cart_at_store", C(0.25, 0.25, 0.3)), (arm_s, "arm_at_store", C(0.9, 0.15, 0.15))]:
    assy.add(obj, name=name, color=col)
result = assy
