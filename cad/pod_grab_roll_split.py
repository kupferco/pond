import cadquery as cq
import math
# Pod grab concept: cart ROLLED 45 deg over the seedling tray, UPRIGHT at the pod store. Pods vertical everywhere.
# Frame (sim/unit, mm): X along the track, Y front(-)/back(+), Z up. One track pipe at y -60, z 579, r 16.
# Cart (from the pod-grab layout): plate 168 x 146 x 6, front face y -116, centre z 519; SO-101 shoulder 88 mm out (y -204, z 519).
# Arm links L1 116 / L2 135, wrist 100 above the grip, claw straight down. Tray rows A-D at y -155/-117/-79/-41, pod tops z 224.
# Store front row pick at y -147. ASSUMED: tray at x -330..-110, store at x 110..330, water station box over the store (position TBC).
# Roll is about the pipe axis, +45 deg = plate bottom swings back, arm points down-forward.
PY, PZ, PR = -60.0, 579.0, 16.0
L1, L2, CLAW = 116.0, 135.0, 100.0
POD_D, POD_H, POD_TOP = 25.0, 40.0, 224.0
LID_Z = 214.0
TRAY_X = (-330.0, -110.0); STORE_X = (110.0, 330.0)
CART_TRAY_X, CART_STORE_X = -220.0, 220.0

def roll(y, z, deg):
    a = math.radians(deg); dy, dz = y - PY, z - PZ
    return PY + dy * math.cos(a) - dz * math.sin(a), PZ + dy * math.sin(a) + dz * math.cos(a)

def rod(p0, p1, r):
    v = cq.Vector(*p1) - cq.Vector(*p0)
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(r, v.Length, cq.Vector(*p0), v.normalized()))

def ik(sh, tgt):
    dy, dz = tgt[0] - sh[0], tgt[1] - sh[1]; d = math.hypot(dy, dz)
    a = math.atan2(dz, dy); b = math.acos(max(-1, min(1, (L1**2 + d**2 - L2**2) / (2 * L1 * d))))
    cands = [(sh[0] + L1 * math.cos(a + s * b), sh[1] + L1 * math.sin(a + s * b)) for s in (1, -1)]
    return max(cands, key=lambda e: e[1]), d

def cart(x0, deg):
    plate = cq.Workplane("XY").box(168, 6, 146).translate((x0, -113, 519))
    base = cq.Workplane("XY").box(70, 50, 70).translate((x0, -141, 519))
    batt = cq.Workplane("XY").box(50, 70, 70).translate((x0 + 59, -151, 519))
    pad = cq.Workplane("XY").box(124, 44, 30).translate((x0, -88, 560))
    parts = plate.union(base).union(batt).union(pad)
    parts = parts.rotate((0, PY, PZ), (1, PY, PZ), deg)
    sleeve = cq.Workplane("YZ").circle(61).circle(PR + 1).extrude(124).translate((x0 - 62, PY, PZ))
    return parts.union(sleeve)

def arm(x0, deg, grip):
    sh = roll(-204.0, 519.0, deg)
    wrist = (grip[0], grip[1] + CLAW)
    el, d = ik(sh, wrist)
    P = lambda p: (x0, p[0], p[1])
    a = rod(P(sh), P(el), 10).union(rod(P(el), P(wrist), 9)).union(rod(P(wrist), P(grip), 7))
    for p in (sh, el, wrist):
        a = a.union(cq.Workplane("XY").sphere(13).translate(P(p)))
    return a, d

def pods(xs, ys):
    w = None
    for x in xs:
        for y in ys:
            c = cq.Workplane("XY").circle(POD_D / 2).extrude(POD_H).translate((x, y, POD_TOP - POD_H))
            w = c if w is None else w.union(c)
    return w

pipe = cq.Workplane("YZ").circle(PR).extrude(800).translate((-400, PY, PZ))
lid = cq.Workplane("XY").box(760, 260, 4, centered=(True, True, False)).translate((0, -90, LID_Z - 4))
tray = cq.Workplane("XY").box(TRAY_X[1] - TRAY_X[0], 150, 30, centered=(False, True, False)).translate((TRAY_X[0], -98, LID_Z))
tray_pods = pods([TRAY_X[0] + 30 + 40 * i for i in range(5)], [-155, -117, -79, -41])
store = cq.Workplane("XY").box(STORE_X[1] - STORE_X[0], 120, 30, centered=(False, True, False)).translate((STORE_X[0], -120, LID_Z))
store_pods = pods([STORE_X[0] + 20 + 28 * i for i in range(7)], [-147, -112, -77])
station = cq.Workplane("XY").box(200, 100, 113, centered=(False, True, False)).translate((STORE_X[0] + 10, -30, 300))

grip_z = POD_TOP + 5
arm_t, d_t = arm(CART_TRAY_X, 45.0, (-41.0, grip_z))      # rolled cart reaching the far tray row D
arm_s, d_s = arm(CART_STORE_X, 0.0, (-147.0, grip_z))     # upright cart at the store front row
print(f"shoulder to wrist: rolled 45 over tray row D {d_t:.0f} mm, upright at store front row {d_s:.0f} mm (limit {L1 + L2:.0f})")
for row, y in zip("ABCD", (-155, -117, -79, -41)):
    sh = roll(-204.0, 519.0, 45.0)
    print(f"  rolled, row {row}: {math.hypot(y - sh[0], grip_z + CLAW - sh[1]):.0f} mm")

assy = cq.Assembly()
assy.add(pipe, name="track_pipe", color=cq.Color(0.7, 0.7, 0.72))
assy.add(lid, name="tank_lid", color=cq.Color(0.6, 0.6, 0.65, 0.4))
assy.add(tray, name="seedling_tray", color=cq.Color(0.3, 0.7, 0.4))
assy.add(tray_pods, name="tray_pods_vertical", color=cq.Color(0.6, 0.45, 0.25))
assy.add(store, name="pod_store", color=cq.Color(0.3, 0.55, 0.85))
assy.add(store_pods, name="store_pods_vertical", color=cq.Color(0.6, 0.45, 0.25))
assy.add(station, name="water_station_ASSUMED", color=cq.Color(0.9, 0.6, 0.2, 0.35))
assy.add(cart(CART_TRAY_X, 45.0), name="cart_rolled_45_over_tray", color=cq.Color(0.25, 0.25, 0.3))
assy.add(arm_t, name="arm_rolled", color=cq.Color(0.9, 0.15, 0.15))
assy.add(cart(CART_STORE_X, 0.0), name="cart_upright_at_store", color=cq.Color(0.25, 0.25, 0.3))
assy.add(arm_s, name="arm_upright", color=cq.Color(0.9, 0.15, 0.15))
result = assy
