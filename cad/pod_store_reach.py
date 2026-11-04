# cad/pod_store_reach.py — pod store v2 + arm reach check, concept (4 Nov 2026)
# Rows run front-to-back, loaded from the FRONT, sloping down to a pick line under the
# track plane (y=0). Each row has a roof; only the last spot (a dip) is open, under a pick
# hole in the lid. Seedling tray takes the left ~1/5. Track pipes A (left) and B (right)
# come down near the lid; translucent spheres = arm reach from the shoulder at the cart's
# lowest point on each pipe.
# ASSUMED (all TBC): tank 700 x 400 x 400 mm; lid at z=400; pipes A/B at x=-/+250 in the
# track plane; cart shoulder lowest at z=550; arm reach 350 mm (SO-101-like 116+135+100);
# pod 25 dia, 28 mm pitch, row pitch 35 mm.
import cadquery as cq
import math

TANK = (700.0, 400.0, 400.0)
LID_Z = TANK[2]
POD_D = 25.0; PITCH = 28.0; ROW_P = 35.0
N_ROWS = 14
ROW_LEN = 190.0           # front edge (y=-200) to pick line (y~0)
N_PODS = int(ROW_LEN // PITCH)
SLOPE = 12.0
STORE_X0 = -140.0         # left 1/5 (x -350..-140) = seedling tray
PIPE_X = 250.0; PIPE_D = 32.0
SHOULDER_Z = 550.0; REACH = 350.0

assy = cq.Assembly()

tank = cq.Workplane("XY").box(*TANK, centered=(True, True, False))
tank = tank.cut(cq.Workplane("XY").box(TANK[0] - 8, TANK[1] - 8, TANK[2], centered=(True, True, False)).translate((0, 0, 4)))
assy.add(tank, name="tank", color=cq.Color(0.85, 0.85, 0.9, 0.25))

lid = cq.Workplane("XY").box(TANK[0], TANK[1], 4, centered=(True, True, False)).translate((0, 0, LID_Z))
holes = []
for i in range(N_ROWS):
    x = STORE_X0 + ROW_P / 2 + i * ROW_P
    lid = lid.cut(cq.Workplane("XY").circle(POD_D / 2 + 2).extrude(10).translate((x, 0, LID_Z - 3)))
    holes.append(x)
assy.add(lid, name="lid_with_pick_holes", color=cq.Color(0.6, 0.6, 0.65, 0.5))

seed = cq.Workplane("XY").box(200, 380, 40, centered=(False, True, False)).translate((-345, 0, LID_Z - 60))
assy.add(seed, name="seedling_tray", color=cq.Color(0.3, 0.7, 0.4))

for i, x in enumerate(holes):
    # row channel with roof, sloping down from front (y=-200) to pick line (y=0)
    ch = cq.Workplane("XY").box(ROW_P - 4, ROW_LEN, 34, centered=(True, False, False))
    ch = ch.cut(cq.Workplane("XY").box(ROW_P - 8, ROW_LEN - 2 * PITCH + 4, 28, centered=(True, False, False)).translate((0, 2, 2)))
    ch = ch.rotate((0, 0, 0), (1, 0, 0), SLOPE).translate((x, -200, LID_Z - 110))
    assy.add(ch, name=f"row_{i}", color=cq.Color(0.3, 0.55, 0.85, 0.7))
    for k in range(N_PODS):
        yy = -200 + 4 + POD_D / 2 + k * PITCH
        zz = LID_Z - 108 + (yy + 200) * math.tan(math.radians(-SLOPE)) * -1
        p = cq.Workplane("XZ").circle(POD_D / 2).extrude(-POD_D).translate((x, yy - POD_D / 2, LID_Z - 100 - (yy + 200) * math.tan(math.radians(SLOPE))))
        assy.add(p, name=f"pod_{i}_{k}", color=cq.Color(0.6, 0.45, 0.25))

for name, sx in (("pipe_A", -PIPE_X), ("pipe_B", PIPE_X)):
    pipe = cq.Workplane("XY").circle(PIPE_D / 2).extrude(600).translate((sx, 0, LID_Z + 80))
    assy.add(pipe, name=name, color=cq.Color(0.7, 0.7, 0.72))
    sh = cq.Workplane("XY").sphere(15).translate((sx, 0, SHOULDER_Z))
    assy.add(sh, name=f"shoulder_{name}", color=cq.Color(0.9, 0.2, 0.2))
    reach = cq.Workplane("XY").sphere(REACH).translate((sx, 0, SHOULDER_Z))
    assy.add(reach, name=f"reach_{name}", color=cq.Color(0.9, 0.3, 0.3, 0.12))

worst = 0.0
for x in holes:
    d = min(math.hypot(x - sx, SHOULDER_Z - LID_Z) for sx in (-PIPE_X, PIPE_X))
    worst = max(worst, d)
    print(f"hole x={x:6.1f}: nearest shoulder {d:5.1f} mm  {'OK' if d < REACH - 30 else 'TIGHT' if d < REACH else 'OUT'}")
print(f"rows {N_ROWS} x {N_PODS} pods = {N_ROWS * N_PODS}; worst reach {worst:.0f} of {REACH:.0f} mm")
result = assy
