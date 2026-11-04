# cad/pod_store_reach.py — pod store v2 + arm reach check, concept (4 Nov 2026)
# Rows run front-to-back, loaded from the FRONT, sloping down to a pick line under the
# track plane (y=0). Pick holes in the lid along that line. Seedling tray = left ~1/5.
# Red spheres = shoulder at the cart's lowest point on pipes A and B; pink discs = arm reach
# (350 mm) drawn in the track plane.
# ASSUMED (TBC): tank 700 x 400 x 400; pipes A/B at x=-/+250; shoulder lowest z=550;
# reach 350 mm; pod 25 dia, 28 pitch; row pitch 35.
import cadquery as cq
import math

TW, TD, TH = 700.0, 400.0, 400.0
POD_D = 25.0; PITCH = 28.0; ROW_P = 35.0; N_ROWS = 14
ROW_LEN = 190.0; N_PODS = int(ROW_LEN // PITCH)
STORE_X0 = -140.0
PIPE_X = 250.0; SHOULDER_Z = 550.0; REACH = 350.0

tank = (cq.Workplane("XY").box(TW, TD, TH, centered=(True, True, False))
        .faces(">Z").shell(-4))
lid = cq.Workplane("XY").box(TW, TD, 4, centered=(True, True, False)).translate((0, 0, TH))
holes = [STORE_X0 + ROW_P / 2 + i * ROW_P for i in range(N_ROWS)]
for x in holes:
    lid = lid.cut(cq.Workplane("XY").circle(POD_D / 2 + 2).extrude(20).translate((x, 0, TH - 5)))

rows = cq.Workplane("XY")
for x in holes:
    r = (cq.Workplane("XY").box(ROW_P - 4, ROW_LEN, 30, centered=(True, False, False))
         .rotate((0, 0, 0), (1, 0, 0), -12).translate((x, -200, TH - 70)))
    rows = rows.union(r)

seed = cq.Workplane("XY").box(200, 380, 40, centered=(False, True, False)).translate((-345, 0, TH - 60))

pipes = (cq.Workplane("XY").pushPoints([(-PIPE_X, 0), (PIPE_X, 0)]).circle(16).extrude(500)
         .translate((0, 0, TH + 80)))
shoulders = (cq.Workplane("XY").pushPoints([(-PIPE_X, 0), (PIPE_X, 0)]).sphere(15)
             .translate((0, 0, SHOULDER_Z)))
reach = (cq.Workplane("XZ").pushPoints([(-PIPE_X, SHOULDER_Z), (PIPE_X, SHOULDER_Z)])
         .circle(REACH).extrude(1).translate((0, 0.5, 0)))

worst = 0.0
for x in holes:
    d = min(math.hypot(x - sx, SHOULDER_Z - TH) for sx in (-PIPE_X, PIPE_X))
    worst = max(worst, d)
print(f"rows {N_ROWS} x {N_PODS} pods = {N_ROWS * N_PODS}; worst hole distance {worst:.0f} mm vs reach {REACH:.0f}")

assy = cq.Assembly()
assy.add(tank, name="tank", color=cq.Color(0.85, 0.85, 0.9, 0.3))
assy.add(lid, name="lid_pick_holes", color=cq.Color(0.6, 0.6, 0.65, 0.5))
assy.add(rows, name="pod_rows", color=cq.Color(0.3, 0.55, 0.85))
assy.add(seed, name="seedling_tray", color=cq.Color(0.3, 0.7, 0.4))
assy.add(pipes, name="track_pipes_A_B", color=cq.Color(0.7, 0.7, 0.72))
assy.add(shoulders, name="arm_shoulders", color=cq.Color(0.9, 0.1, 0.1))
assy.add(reach, name="arm_reach", color=cq.Color(0.95, 0.4, 0.4, 0.25))
result = assy
