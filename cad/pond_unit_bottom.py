import cadquery as cq
import math
# POND UNIT, BOTTOM ONLY (cropped at z 750), detailed cart (26 Nov 2026, v2).
# LEFT cart (over the seedling tray) ROLLED 45 deg about the track axis, RIGHT cart (at the pod store) upright, to compare the reach.
# Unit numbers from main (layout.json, unit_dims.py, unit_frame.py, track.py, tank.py, shelf.py, shelf_items.py, water_station.py).
# Cart follows cart_assembly.py / cart_dims.py sizes: two clamp/jaw hands (90 mm sleeve, R34, jaw lobe, motor 28 x 55),
# pads, hinge, plate 166 x 112 x 6, battery 70 x 50 x 70 under the arm, SO-101 arm (servos 45 x 24 x 35, two-finger gripper).
# Arm links L1 116 / L2 135 (ASSUMED shoulder 144 out from the track axis, 60 under it); elbow kept on the side away from the cart.
ZCROP = 750.0
TW, TD, TH, WALL, LID_T = 700.0, 400.0, 300.0, 4.0, 4.0
LID = TH + LID_T
GP, SP, LR = 75.0, 33.7, 8.0
RP = GP / 2; RC = RP + 3
TX, TR, R, LOOP_Y = 290.0, 16.0, 150.0, -60.0
ZB = 514.0
ZC1, FOOT_X = 1215.0, 340.0
SHELF_Z, SHELF_T = 155.0, 4.0; SHELF_TOP = SHELF_Z + SHELF_T
ROLL_LEFT = 45.0

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
def roll(shape, deg):
    return shape.rotate((0, LOOP_Y, ZB), (1, LOOP_Y, ZB), deg) if deg else shape
def roll_pt(p, deg):
    a = math.radians(deg); dy, dz = p[1] - LOOP_Y, p[2] - ZB
    return (p[0], LOOP_Y + dy * math.cos(a) - dz * math.sin(a), ZB + dy * math.sin(a) + dz * math.cos(a))
CROP = box(2000, 2000, ZCROP, 0, 0, -1)

# ---------- tank, lid, shelf, tray, store, pods ----------
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

# ---------- frame, bottom part ----------
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

# ---------- detailed cart ----------
def hand(xc, deg):
    body = xcyl(34, 90, xc, LOOP_Y, ZB).cut(xcyl(TR + 2, 92, xc, LOOP_Y, ZB)).cut(box(92, 30, 40, xc, LOOP_Y + 24, ZB - 20))
    jaw = xcyl(10, 90, xc, LOOP_Y + 30, ZB + 18)
    wheels = U([xcyl(9, 14, xc + s, LOOP_Y + dy, ZB + dz) for s in (-30, 30)
                for dy, dz in ((0, -TR - 9 + 2), (-14, TR + 4), (14, TR + 4))]).cut(xcyl(TR, 200, xc, LOOP_Y, ZB))
    motor = ycyl(14, 55, xc, LOOP_Y - 34 - 27, ZB + 8)
    pad = box(40, 14, 40, xc, LOOP_Y - 41, ZB - 20)
    return roll(body, deg), roll(jaw.union(wheels), deg), roll(motor, deg), roll(pad, deg)

def cart(x0, deg):
    parts = [hand(x0 + s, deg) for s in (-60, 60)]
    hinge = roll(xcyl(5, 166, x0, LOOP_Y - 50, ZB - 4), deg)
    plate = roll(box(166, 6, 112, x0, LOOP_Y - 53, ZB - 120), deg)
    batt = roll(box(70, 50, 70, x0, LOOP_Y - 81, ZB - 60 - 35), deg)
    return (U([p[0] for p in parts]), U([p[1] for p in parts]), U([p[2] for p in parts]),
            U([p[3] for p in parts]).union(hinge), plate, batt)

def cart_body(x0, deg):
    return roll(box(166, 6, 112, x0, LOOP_Y - 53, ZB - 120).union(box(70, 50, 70, x0, LOOP_Y - 81, ZB - 60 - 35)), deg)

L1, L2, CLAW = 116.0, 135.0, 100.0
def servo_at(p, along):
    return bxc(*({"x": (45, 35, 24), "y": (24, 45, 35), "z": (24, 35, 45)}[along]), p)

def ik(S, W):
    hx, hy = W[0] - S[0], W[1] - S[1]; hu = math.hypot(hx, hy) or 1e-6; dz = W[2] - S[2]; d = math.hypot(hu, dz)
    a = math.atan2(dz, hu); b = math.acos(max(-1, min(1, (L1**2 + d**2 - L2**2) / (2 * L1 * d))))
    cands = [(S[0] + hx / hu * L1 * math.cos(a + s * b), S[1] + hy / hu * L1 * math.cos(a + s * b), S[2] + L1 * math.sin(a + s * b)) for s in (1, -1)]
    return min(cands, key=lambda e: e[1]), d

def arm(x0, grip, deg):
    S = roll_pt((x0, LOOP_Y - 144, ZB - 60), deg)
    W = (grip[0], grip[1], grip[2] + CLAW)
    E, d = ik(S, W)
    base_plate = roll(box(70, 8, 70, x0, LOOP_Y - 110, ZB - 95), deg)
    base_servo = roll(bxc(35, 26, 45, (x0, LOOP_Y - 127, ZB - 60)), deg)
    shoulder = roll(bxc(50, 18, 40, (x0, LOOP_Y - 149, ZB - 60)), deg).union(servo_at(S, "x"))
    servos = U([base_servo, shoulder, servo_at(E, "x"), servo_at(W, "z"), servo_at((W[0], W[1], W[2] - 32), "x"),
                bxc(30, 24, 30, (grip[0], grip[1], grip[2] + 50))])
    links = rod(S, E, 11).union(rod(E, W, 9))
    fingers = U([bxc(6, 18, 45, (grip[0] + s, grip[1], grip[2] + 18)) for s in (-14, 14)])
    return base_plate, servos, links, fingers, d, S, E

lim = L1 + L2
print("shoulder->wrist (limit %.0f, min fold about %.0f); clash = arm links inside cart plate/battery or the lid" % (lim, L2 - L1 + 40))
for tag, x0, deg in (("ROLLED 45 over tray", -130.0, ROLL_LEFT), ("upright over tray", -130.0, 0.0)):
    for y in TRAY_YS:
        for x in (TRAY_XS[0], -185, TRAY_XS[-1]):
            _, _, links, _, d, S, E = arm(x0, (x, y, POD_TOP_T), deg)
            cl = links.intersect(cart_body(x0, deg)).val().Volume() + links.intersect(lid).val().Volume()
            print("  %-20s cell x %4d y %4d: %4.0f mm  %s" % (tag, x, y, d, "CLASH" if cl > 1 else "clear"))
    print("  %-20s shoulder at y %.0f z %.0f; lowest cart point z %.0f (lid %.0f)" % (
        tag, S[1], S[2], min(roll_pt((x0, LOOP_Y - 56, ZB - 120), deg)[2], roll_pt((x0, LOOP_Y - 106, ZB - 95), deg)[2],
                             roll_pt((x0, LOOP_Y - 56, ZB - 8), deg)[2]), LID))

C = cq.Color
assy = cq.Assembly()
for obj, name, col in [
    (tank, "tank", C(0.75, 0.75, 0.8, 0.25)), (shelf, "shelf", C(0.5, 0.5, 0.55, 0.4)), (lid, "lid_with_pick_holes", C(0.6, 0.6, 0.65, 0.5)),
    (tray, "seedling_tray", C(0.59, 0.43, 0.27)), (storage, "pod_storage", C(0.35, 0.5, 0.75)), (pods, "pods", C(0.24, 0.67, 0.31)),
    (pillar, "growing_pipe", C(0.95, 0.95, 0.95, 0.8)), (socket, "pillar_socket", C(0.95, 0.6, 0.2)), (spine, "spine", C(0.35, 0.35, 0.35)),
    (bracket, "pillar_to_track_bracket", C(0.95, 0.6, 0.2)), (legs, "a_frame_legs", C(0.55, 0.57, 0.6)), (lid_plates, "lid_plates", C(0.55, 0.57, 0.6)),
    (feet, "feet", C(0.4, 0.4, 0.42)), (track, "track", C(0.75, 0.75, 0.77)),
    (station, "water_station", C(0.93, 0.93, 0.9)), (st_legs, "water_station_legs", C(0.55, 0.57, 0.6))]:
    assy.add(obj, name=name, color=col)

for tag, x0, grip, deg in (("tray_rolled45", -130.0, (-185.0, -125.0, POD_TOP_T), ROLL_LEFT),
                           ("store_upright", 130.0, (190.0, STORE_Y, POD_TOP_S), 0.0)):
    sleeves, jaws, motors, pads, plate, batt = cart(x0, deg)
    bp, servos, links, fingers, d, S, E = arm(x0, grip, deg)
    for obj, name, col in [(sleeves, "sleeves", C(0.18, 0.2, 0.26)), (jaws, "jaws_wheels", C(0.35, 0.37, 0.42)), (motors, "motors", C(0.75, 0.55, 0.2)),
                           (pads, "pads_hinge", C(0.45, 0.45, 0.5)), (plate, "plate", C(0.35, 0.35, 0.38)), (batt, "battery", C(0.2, 0.45, 0.85)),
                           (bp, "arm_base", C(0.85, 0.85, 0.88)), (servos, "arm_servos", C(0.12, 0.12, 0.14)), (links, "arm_links", C(0.92, 0.92, 0.94)),
                           (fingers, "gripper", C(0.9, 0.15, 0.15))]:
        assy.add(obj, name="cart_%s_%s" % (tag, name), color=col)
result = assy
