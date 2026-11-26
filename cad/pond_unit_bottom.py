import cadquery as cq
import math
# POND UNIT, BOTTOM ONLY (cropped at z 750), detailed cart (26 Nov 2026, v5).
# v5: the DRY POD STORE is a gravity-feed tray: 7 lanes sloping down toward the front, so when the arm lifts the front pod the next one
# slides forward into the pick spot. Each lane ends in a short FLAT landing at the front row (y -165) so the pod being picked stands vertical,
# with a stop lip in front. Slope 15 deg (ASSUMED: enough for a dry plastic net pot to slide; test with the real pots).
# Both carts upright, real 160 mm SO-101 claw (no tilt: v4 check, 18/18 tray cells and the store front row reachable, lid clear).
ZCROP = 750.0
TW, TD, TH, WALL, LID_T = 700.0, 400.0, 300.0, 4.0, 4.0
LID = TH + LID_T
GP, SP, LR = 75.0, 33.7, 8.0
RP = GP / 2; RC = RP + 3
TX, TR, R, LOOP_Y = 290.0, 16.0, 150.0, -60.0
ZB = 514.0
ZC1, FOOT_X = 1215.0, 340.0
SHELF_Z, SHELF_T = 155.0, 4.0; SHELF_TOP = SHELF_Z + SHELF_T
L1, L2, CLAW = 116.0, 135.0, 160.0
SLOPE = 15.0

def box(sx, sy, sz, cx, cy, z0):
    return cq.Workplane("XY").box(sx, sy, sz, centered=(True, True, False)).translate((cx, cy, z0))
def bxc(sx, sy, sz, c):
    return cq.Workplane("XY").box(sx, sy, sz).translate(c)
def bxx(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))
def cyl(r, h, x, y, z0):
    return cq.Workplane("XY").circle(r).extrude(h).translate((x, y, z0))
def tube(ro, ri, h, x, y, z0):
    return cq.Workplane("XY").circle(ro).circle(ri).extrude(h).translate((x, y, z0))
def rod(p0, p1, r):
    v = cq.Vector(*p1) - cq.Vector(*p0)
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(r, v.Length, cq.Vector(*p0), v.normalized()))
def xcyl(r, L, cx, cy, cz):
    return cq.Workplane("YZ").circle(r).extrude(L).translate((cx - L / 2, cy, cz))
def ycyl(r, L, cx, cy, cz):
    return cq.Workplane("XZ").circle(r).extrude(L).translate((cx, cy + L / 2, cz))
def U(ps):
    o = None
    for p in ps:
        o = p if o is None else o.union(p)
    return o
CROP = box(2000, 2000, ZCROP, 0, 0, -1)

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
POD_TOP_T = SHELF_TOP + 46
tray_pods = U([cyl(12.5, 40, x, y, POD_TOP_T - 40) for x in TRAY_XS for y in TRAY_YS])

# ---------- gravity-feed dry pod store ----------
BASE_T = 12.0
LAND_Y0, LAND_Y1 = -180.0, -152.0          # flat landing (front pick spot centred at y -165)
RAMP_Y1 = -62.0                            # back of the ramp
t15 = math.tan(math.radians(SLOPE))
ZL = SHELF_TOP + BASE_T                    # landing floor height (171)
ramp_len = RAMP_Y1 - LAND_Y1
ramp_rise = ramp_len * t15
X0, X1 = 80.0, 300.0
base = bxx(X0, X1, LAND_Y0 - 6, RAMP_Y1, SHELF_TOP, ZL)
# ramp: a wedge from the landing back edge rising to the back
wedge = (cq.Workplane("YZ").polyline([(LAND_Y1, ZL), (RAMP_Y1, ZL), (RAMP_Y1, ZL + ramp_rise)]).close()
         .extrude(X1 - X0).translate((X0, 0, 0)))
stop_lip = bxx(X0, X1, LAND_Y0 - 6, LAND_Y0, ZL, ZL + 14)
rails = []
for i in range(len(STORE_XS) + 1):
    xr = STORE_XS[0] - 15 + 30 * i
    r = (cq.Workplane("YZ").polyline([(LAND_Y0, ZL), (LAND_Y1, ZL), (RAMP_Y1, ZL + ramp_rise), (RAMP_Y1, ZL + ramp_rise + 22),
                                       (LAND_Y1, ZL + 22), (LAND_Y0, ZL + 22)]).close().extrude(3).translate((xr - 1.5, 0, 0)))
    rails.append(r)
store = U([base, wedge, stop_lip] + rails)
# pods: the front one stands vertical on the landing, the queue behind it leans with the 15 deg ramp
store_pods = []
for x in STORE_XS:
    store_pods.append(cyl(12.5, 40, x, STORE_Y, ZL))
    for k in range(1, 4):
        yc = LAND_Y1 + 12.5 + (k - 1) * 26 + 2
        zf = ZL + (yc - LAND_Y1) * t15
        p = cq.Workplane("XY").circle(12.5).extrude(40).rotate((0, 0, 0), (1, 0, 0), SLOPE).translate((x, yc, zf))
        store_pods.append(p)
store_pods = U(store_pods)
POD_TOP_S = ZL + 40

pillar = tube(RP, RP - 3, ZCROP - LID, 0, 0, LID)
socket = tube(RP + 10, RP + 1, 25, 0, 0, LID)
spine = tube(SP / 2, SP / 2 - 2, ZCROP, 0, 0, 0)
bracket = box(16, 30, 30, 0, -45, ZB - 15)
legs = U([rod((e[0] / math.hypot(e[0], e[1]) * (RC - 4), e[1] / math.hypot(e[0], e[1]) * (RC - 4), ZC1), e, LR)
          for e in [(-FOOT_X, 0, LID), (FOOT_X, 0, LID), (0, 180, LID)]]).intersect(CROP)
lid_plates = U([box(FOOT_X - 50, 20, 15, -(50 + FOOT_X) / 2, 0, LID), box(FOOT_X - 50, 20, 15, (50 + FOOT_X) / 2, 0, LID),
                box(50, 30, 5, -(FOOT_X - 10), 0, LID), box(50, 30, 5, FOOT_X - 10, 0, LID), box(30, 40, 5, 0, 175, LID)])
feet = U([box(50, 220, 6, sx * 325, sy * 310, 0).union(box(50, 6, 80, sx * 325, sy * 203, 0)) for sx in (-1, 1) for sy in (-1, 1)])

def corner(cx, cz, qx):
    tor = cq.Workplane("XY").add(cq.Solid.makeTorus(R, TR, pnt=cq.Vector(cx, LOOP_Y, cz), dir=cq.Vector(0, 1, 0)))
    clip = box(R + TR + 2, 4 * TR, R + TR + 2, cx + qx * (R + TR + 2) / 2, LOOP_Y, cz - (R + TR + 2))
    return tor.intersect(clip)
track = xcyl(TR, 2 * (TX - R), 0, LOOP_Y, ZB)
for sx in (-1, 1):
    track = track.union(corner(sx * (TX - R), ZB + R, sx)).union(cyl(TR, ZCROP - (ZB + R), sx * TX, LOOP_Y, ZB + R))

station = bxx(60, 260, 14, 108, 394, 504).union(bxx(52, 268, 14, 116, 504, 507))
st_legs = U([bxx(x0, x0 + 20, y0, y0 + 20, LID, 394) for x0 in (60, 240) for y0 in (22, 80)])

def hand(xc):
    body = xcyl(34, 90, xc, LOOP_Y, ZB).cut(xcyl(TR + 2, 92, xc, LOOP_Y, ZB)).cut(box(92, 30, 40, xc, LOOP_Y + 24, ZB - 20))
    jaw = xcyl(10, 90, xc, LOOP_Y + 30, ZB + 18)
    wheels = U([xcyl(9, 14, xc + s, LOOP_Y + dy, ZB + dz) for s in (-30, 30)
                for dy, dz in ((0, -TR - 9 + 2), (-14, TR + 4), (14, TR + 4))]).cut(xcyl(TR, 200, xc, LOOP_Y, ZB))
    motor = ycyl(14, 55, xc, LOOP_Y - 34 - 27, ZB + 8)
    pad = box(40, 14, 40, xc, LOOP_Y - 41, ZB - 20)
    return body, jaw.union(wheels), motor, pad

def cart(x0):
    parts = [hand(x0 + s) for s in (-60, 60)]
    hinge = xcyl(5, 166, x0, LOOP_Y - 50, ZB - 4)
    plate = box(166, 6, 112, x0, LOOP_Y - 53, ZB - 120)
    batt = box(70, 50, 70, x0, LOOP_Y - 81, ZB - 60 - 35)
    return (U([p[0] for p in parts]), U([p[1] for p in parts]), U([p[2] for p in parts]),
            U([p[3] for p in parts]).union(hinge), plate, batt)

def cart_body(x0):
    return box(166, 6, 112, x0, LOOP_Y - 53, ZB - 120).union(box(70, 50, 70, x0, LOOP_Y - 81, ZB - 60 - 35))

def servo_at(p, along):
    return bxc(*({"x": (45, 35, 24), "y": (24, 45, 35), "z": (24, 35, 45)}[along]), p)

def ik(S, W):
    hx, hy = W[0] - S[0], W[1] - S[1]; hu = math.hypot(hx, hy) or 1e-6; dz = W[2] - S[2]; d = math.hypot(hu, dz)
    a = math.atan2(dz, hu); b = math.acos(max(-1, min(1, (L1**2 + d**2 - L2**2) / (2 * L1 * d))))
    cands = [(S[0] + hx / hu * L1 * math.cos(a + s * b), S[1] + hy / hu * L1 * math.cos(a + s * b), S[2] + L1 * math.sin(a + s * b)) for s in (1, -1)]
    return min(cands, key=lambda e: e[1]), d

def arm(x0, grip):
    S = (x0, LOOP_Y - 144, ZB - 60)
    W = (grip[0], grip[1], grip[2] + CLAW)
    E, d = ik(S, W)
    base_plate = box(70, 8, 70, x0, LOOP_Y - 110, ZB - 95)
    base_servo = bxc(35, 26, 45, (x0, LOOP_Y - 127, ZB - 60))
    shoulder = bxc(50, 18, 40, (x0, LOOP_Y - 149, ZB - 60)).union(servo_at(S, "x"))
    wristp = U([servo_at(W, "z"), servo_at((W[0], W[1], W[2] - 32), "x")])
    claw = rod((W[0], W[1], W[2] - 44), (grip[0], grip[1], grip[2] + 60), 9).union(bxc(26, 22, 40, (grip[0], grip[1], grip[2] + 40)))
    fingers = U([bxc(5, 16, 45, (grip[0] + s, grip[1], grip[2] + 2)) for s in (-11, 11)])
    servos = U([base_servo, shoulder, servo_at(E, "x"), wristp])
    links = rod(S, E, 11).union(rod(E, W, 9))
    return base_plate, servos, links, claw, fingers, d, E, W

lim = L1 + L2
ok = 0
for x in STORE_XS:
    _, _, links, claw, fingers, d, E, W = arm(130.0, (x, STORE_Y, POD_TOP_S))
    moving = links.union(claw).union(fingers).union(servo_at(E, "x")).union(servo_at(W, "z"))
    ok += d <= lim and links.intersect(cart_body(130.0)).val().Volume() < 1 and moving.intersect(lid).val().Volume() < 1
print("gravity store: slope %.0f deg, ramp %.0f mm long rising %.0f mm; back pod top z %.0f vs lid underside %.0f" % (
    SLOPE, ramp_len, ramp_rise, ZL + ramp_rise + 40 * math.cos(math.radians(SLOPE)), TH))
print("store front (pick) row: %d of %d lanes reachable upright, lid and cart clear" % (ok, len(STORE_XS)))
print("each lane holds 4 pods (1 on the landing + 3 queued) = %d pods" % (4 * len(STORE_XS)))

C = cq.Color
assy = cq.Assembly()
for obj, name, col in [
    (tank, "tank", C(0.75, 0.75, 0.8, 0.25)), (shelf, "shelf", C(0.5, 0.5, 0.55, 0.4)), (lid, "lid_with_pick_holes", C(0.6, 0.6, 0.65, 0.45)),
    (tray, "seedling_tray", C(0.59, 0.43, 0.27)), (tray_pods, "seedling_pods", C(0.24, 0.67, 0.31)),
    (store, "gravity_pod_store", C(0.35, 0.5, 0.75)), (store_pods, "dry_pods", C(0.85, 0.75, 0.5)),
    (pillar, "growing_pipe", C(0.95, 0.95, 0.95, 0.8)), (socket, "pillar_socket", C(0.95, 0.6, 0.2)), (spine, "spine", C(0.35, 0.35, 0.35)),
    (bracket, "pillar_to_track_bracket", C(0.95, 0.6, 0.2)), (legs, "a_frame_legs", C(0.55, 0.57, 0.6)), (lid_plates, "lid_plates", C(0.55, 0.57, 0.6)),
    (feet, "feet", C(0.4, 0.4, 0.42)), (track, "track", C(0.75, 0.75, 0.77)),
    (station, "water_station", C(0.93, 0.93, 0.9)), (st_legs, "water_station_legs", C(0.55, 0.57, 0.6))]:
    assy.add(obj, name=name, color=col)
for tag, x0, grip in (("tray_far_corner", -130.0, (-290.0, -100.0, POD_TOP_T)), ("store_front", 130.0, (190.0, STORE_Y, POD_TOP_S))):
    sleeves, jaws, motors, pads, plate, batt = cart(x0)
    bp, servos, links, claw, fingers, d, E, W = arm(x0, grip)
    for obj, name, col in [(sleeves, "sleeves", C(0.18, 0.2, 0.26)), (jaws, "jaws_wheels", C(0.35, 0.37, 0.42)), (motors, "motors", C(0.75, 0.55, 0.2)),
                           (pads, "pads_hinge", C(0.45, 0.45, 0.5)), (plate, "plate", C(0.35, 0.35, 0.38)), (batt, "battery", C(0.2, 0.45, 0.85)),
                           (bp, "arm_base", C(0.85, 0.85, 0.88)), (servos, "arm_servos", C(0.12, 0.12, 0.14)), (links, "arm_links", C(0.92, 0.92, 0.94)),
                           (claw, "claw", C(0.12, 0.12, 0.14)), (fingers, "gripper_fingers", C(0.9, 0.15, 0.15))]:
        assy.add(obj, name="cart_%s_%s" % (tag, name), color=col)
result = assy
