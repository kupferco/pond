import cadquery as cq
import math
# Pod grab layout on the REAL unit (26 Nov 2026). Numbers copied from main: cad/layout.json, cad/parts/unit_dims.py, tank.py, shelf.py,
# shelf_items.py, track.py, water_station.py (the sandbox cannot import them; keep in sync).
# Unit frame: mm, Z up, tank floor z 0, growing pipe (pillar) at x = y = 0. Cropped at z 950 (track top run at 1884 not drawn).
# Cart: rolled 45 deg about the track pipe over the seedling tray (x < 0), upright at the pod store (x > 0). Pods vertical.
# Cart and arm are SIMPLIFIED blocks placed off the track axis as in the pod-grab layout (plate front face 56 out, centre 60 under the
# axis, SO-101 shoulder 144 out / 60 under); arm L1 116 / L2 135, claw 100 straight down. ASSUMED where not from the files above.

# ---- unit (from the repo) ----
TW, TD, TH, WALL, LID_T = 700.0, 400.0, 300.0, 4.0, 4.0
LID = TH + LID_T                      # 304
GP, SP = 75.0, 33.7                   # growing pipe (pillar) OD, spine OD
TX, TR, RC, LOOP_Y = 290.0, 16.0, 150.0, -60.0
ZB = 514.0                            # bottom run axis = lid 304 + 165 + 45
SHELF_Z, SHELF_T = 155.0, 4.0
SHELF_TOP = SHELF_Z + SHELF_T         # 159
ZCROP = 950.0
# water station (water_station.py, OFF_Y 50, DZ 64)
ST = dict(x0=60.0, x1=260.0, y0=14.0, y1=108.0, z0=394.0, z1=507.0)

def box(sx, sy, sz, cx, cy, z0):
    return cq.Workplane("XY").box(sx, sy, sz, centered=(True, True, False)).translate((cx, cy, z0))
def bxx(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))
def cyl(r, h, x, y, z0):
    return cq.Workplane("XY").circle(r).extrude(h).translate((x, y, z0))
def rod(p0, p1, r):
    v = cq.Vector(*p1) - cq.Vector(*p0)
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(r, v.Length, cq.Vector(*p0), v.normalized()))
def union_all(ps):
    o = None
    for p in ps:
        o = p if o is None else o.union(p)
    return o

tank = box(TW, TD, TH, 0, 0, 0).cut(box(TW - 2 * WALL, TD - 2 * WALL, TH, 0, 0, WALL))
shelf = box(TW - 2 * WALL, TD - 2 * WALL, SHELF_T, 0, 0, SHELF_Z).cut(cyl(SP / 2 + 1, SHELF_T + 2, 0, 0, SHELF_Z - 1))

# seedling tray (shelf_items.py): 240 x 110 base at x -190, y -125; cells 25 x 18 x 24, x -290..-115 step 35, rows y -150 / -125 / -100
TRAY_XS = list(range(-290, -80, 35)); TRAY_YS = (-150, -125, -100)
tray = union_all([box(240, 110, 6, -190, -125, SHELF_TOP)] + [box(25, 18, 24, x, y, SHELF_TOP + 6) for x in TRAY_XS for y in TRAY_YS])
# storage (shelf_items.py): 240 x 110 x 12 base at x 190, y -125, five 14 mm sticks y -165..-85. Owner: only the FRONT row (y -165) is used.
storage = union_all([box(240, 110, 12, 190, -125, SHELF_TOP)] + [box(230, 14, 36, 190, -165 + 20 * k, SHELF_TOP + 12) for k in range(5)])
STORE_XS = [100 + 30 * i for i in range(7)]; STORE_Y = -165.0

POD_D, POD_H = 25.0, 40.0
TRAY_POD_TOP = SHELF_TOP + 6 + POD_H          # pods standing in the cells: top 205
STORE_POD_TOP = SHELF_TOP + 12 + 36           # pods on the front stick: top 207
pods = union_all([cyl(POD_D / 2, POD_H, x, y, TRAY_POD_TOP - POD_H) for x in TRAY_XS for y in TRAY_YS] +
                 [cyl(POD_D / 2, POD_H, x, STORE_Y, STORE_POD_TOP - POD_H) for x in STORE_XS])

# lid with 32 mm pick holes over every tray cell and the store front row, and the pillar socket hole
lid = box(TW, TD, LID_T, 0, 0, TH)
for x in TRAY_XS:
    for y in TRAY_YS:
        lid = lid.cut(cyl(16, 10, x, y, TH - 1))
for x in STORE_XS:
    lid = lid.cut(cyl(16, 10, x, STORE_Y, TH - 1))

pillar = cyl(GP / 2, ZCROP - LID, 0, 0, LID).cut(cyl(GP / 2 - 2.5, ZCROP, 0, 0, LID - 1))
socket = cyl(GP / 2 + 10, 25, 0, 0, LID).cut(cyl(GP / 2 + 0.5, 30, 0, 0, LID - 1))
spine = cyl(SP / 2, LID, 0, 0, 0)

# track loop (track.py): bottom run x -140..140 at z 514, R150 corners, verticals at x +-290 (cropped)
track = cq.Workplane("YZ").circle(TR).extrude(2 * (TX - RC)).translate((-(TX - RC), LOOP_Y, ZB))
for sx in (-1, 1):
    cx, cz = sx * (TX - RC), ZB + RC
    tor = cq.Workplane("XY").add(cq.Solid.makeTorus(RC, TR, pnt=cq.Vector(cx, LOOP_Y, cz), dir=cq.Vector(0, 1, 0)))
    clip = bxx(cx if sx > 0 else cx - RC - TR - 2, cx + RC + TR + 2 if sx > 0 else cx, LOOP_Y - 40, LOOP_Y + 40, cz - RC - TR - 2, cz)
    track = track.union(tor.intersect(clip)).union(cyl(TR, ZCROP - cz, sx * TX, LOOP_Y, cz).rotate((0, 0, 0), (0, 0, 1), 0)
                                                    .translate((0, 0, 0)) if False else cq.Workplane("XY").circle(TR).extrude(ZCROP - cz).translate((sx * TX, LOOP_Y, cz)))

# water station (behind the pillar): shell, roof, four legs to the lid
station = bxx(ST["x0"], ST["x1"], ST["y0"], ST["y1"], ST["z0"], ST["z1"] - 3)
roof = bxx(ST["x0"] - 8, ST["x1"] + 8, ST["y0"], ST["y1"] + 8, ST["z1"] - 3, ST["z1"])
legs = union_all([bxx(x0, x0 + 20, y0, y0 + 20, LID, ST["z0"]) for x0 in (60, 240) for y0 in (22, 80)])

# ---- cart + arm ----
L1, L2, CLAW = 116.0, 135.0, 100.0
def roll(y, z, deg):
    a = math.radians(deg); dy, dz = y - LOOP_Y, z - ZB
    return LOOP_Y + dy * math.cos(a) - dz * math.sin(a), ZB + dy * math.sin(a) + dz * math.cos(a)

def cart(x0, deg):
    plate = box(168, 6, 146, x0, LOOP_Y - 53, ZB - 60 - 73)
    base = box(70, 50, 70, x0, LOOP_Y - 81, ZB - 60 - 35)
    batt = box(50, 70, 70, x0 + 59, LOOP_Y - 91, ZB - 60 - 35)
    pad = box(124, 44, 30, x0, LOOP_Y - 28, ZB - 34)
    parts = plate.union(base).union(batt).union(pad).rotate((0, LOOP_Y, ZB), (1, LOOP_Y, ZB), deg)
    sleeve = cq.Workplane("YZ").circle(61).circle(TR + 1).extrude(124).translate((x0 - 62, LOOP_Y, ZB))
    return parts.union(sleeve)

def shoulder(x0, deg):
    y, z = roll(LOOP_Y - 144, ZB - 60, deg)
    return (x0, y, z)

def arm(S, grip):
    W = (grip[0], grip[1], grip[2] + CLAW)
    hx, hy = W[0] - S[0], W[1] - S[1]; hu = math.hypot(hx, hy); dz = W[2] - S[2]
    d = math.hypot(hu, dz)
    a = math.atan2(dz, hu); b = math.acos(max(-1, min(1, (L1**2 + d**2 - L2**2) / (2 * L1 * d))))
    best = None
    for s in (1, -1):
        u, z = L1 * math.cos(a + s * b), L1 * math.sin(a + s * b)
        if best is None or z > best[1]:
            best = (u, z)
    ex, ey = (hx / hu, hy / hu) if hu > 1e-6 else (0, -1)
    E = (S[0] + ex * best[0], S[1] + ey * best[0], S[2] + best[1])
    shape = rod(S, E, 10).union(rod(E, W, 9)).union(rod(W, grip, 6))
    for p in (S, E, W):
        shape = shape.union(cq.Workplane("XY").sphere(13).translate(p))
    return shape, d

CART_TRAY_X, CART_STORE_X = -130.0, 130.0      # ASSUMED: carts parked at the ends of the straight bottom run (it curves up past x +-140)
S_roll = shoulder(CART_TRAY_X, 45.0)
S_up = shoulder(CART_STORE_X, 0.0)
S_up_tray = shoulder(CART_TRAY_X, 0.0)
lim = L1 + L2
print("shoulder to wrist (limit %.0f), claw straight down, wrist 100 over the pod top" % lim)
for y in TRAY_YS:
    for x in (TRAY_XS[0], -190, TRAY_XS[-1]):
        g = (x, y, TRAY_POD_TOP)
        dr = math.dist(S_roll, (x, y, g[2] + CLAW)); du = math.dist(S_up_tray, (x, y, g[2] + CLAW))
        print("  tray x %4d y %4d: rolled 45 %4.0f   upright %4.0f" % (x, y, dr, du))
for x in (STORE_XS[0], STORE_XS[3], STORE_XS[-1]):
    print("  store front row x %4d: upright %4.0f" % (x, math.dist(S_up, (x, STORE_Y, STORE_POD_TOP + CLAW))))
arm_roll, _ = arm(S_roll, (-190.0, -100.0, TRAY_POD_TOP))
arm_up, _ = arm(S_up, (190.0, STORE_Y, STORE_POD_TOP))
print("lowest cart point rolled (approx):", round(min(roll(LOOP_Y - 126, ZB - 155, 45)[1], roll(LOOP_Y - 56, ZB - 133, 45)[1])), "vs lid", LID)

C = cq.Color
assy = cq.Assembly()
assy.add(tank, name="tank_700x400x300", color=C(0.75, 0.75, 0.8, 0.25))
assy.add(shelf, name="shelf_z155", color=C(0.5, 0.5, 0.55, 0.35))
assy.add(lid, name="lid_with_pick_holes", color=C(0.6, 0.6, 0.65, 0.35))
assy.add(tray, name="seedling_tray", color=C(0.59, 0.43, 0.27))
assy.add(storage, name="pod_storage", color=C(0.35, 0.5, 0.75))
assy.add(pods, name="pods_vertical", color=C(0.24, 0.67, 0.31))
assy.add(pillar, name="growing_pipe_pillar", color=C(0.95, 0.95, 0.95, 0.7))
assy.add(socket, name="pillar_socket", color=C(0.95, 0.6, 0.2))
assy.add(spine, name="spine_tube", color=C(0.35, 0.35, 0.35))
assy.add(track, name="track_loop_bottom_and_corners", color=C(0.7, 0.7, 0.72))
assy.add(station, name="water_station", color=C(0.93, 0.93, 0.9))
assy.add(roof, name="water_station_roof", color=C(0.82, 0.82, 0.78))
assy.add(legs, name="water_station_legs", color=C(0.55, 0.57, 0.6))
assy.add(cart(CART_TRAY_X, 45.0), name="cart_rolled_45_over_tray", color=C(0.25, 0.25, 0.3))
assy.add(arm_roll, name="arm_rolled", color=C(0.9, 0.15, 0.15))
assy.add(cart(CART_STORE_X, 0.0), name="cart_upright_at_store", color=C(0.25, 0.25, 0.3))
assy.add(arm_up, name="arm_upright", color=C(0.9, 0.15, 0.15))
result = assy
