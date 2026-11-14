# cad/pod_store_reach.py — pod store v3 (4 Nov 2026)
# v3: adds the central growing pipe (75 mm OD, ASSUMED) standing in its socket on the lid,
# with the return mesh, running down into the water. Keep-out zone round it: the 4 rows that
# would hit it are shortened and their pick holes moved forward to stop in front of the
# socket. Other rows unchanged (pick line under the track plane, y=0).
# ASSUMED (TBC): tank 700 x 400 x 400; pipes A/B at x=-/+290 (was 250, Viber #97: tighter spacing); shoulder lowest z=550;
# reach 350; pod 25 dia, 28 pitch; row pitch 35; spine not drawn (position TBC).
import cadquery as cq
import math

TW, TD, TH = 700.0, 400.0, 400.0
POD_D = 25.0; PITCH = 28.0; ROW_P = 35.0; N_ROWS = 14
FRONT_Y = -200.0
STORE_X0 = -140.0
PIPE_X = 290.0; SHOULDER_Z = 550.0; REACH = 350.0
GP_OD = 75.0; SOCKET_OD = 95.0; KEEP_R = 60.0   # growing pipe, socket, keep-out radius

tank = cq.Workplane("XY").box(TW, TD, TH, centered=(True, True, False)).faces(">Z").shell(-4)
lid = cq.Workplane("XY").box(TW, TD, 4, centered=(True, True, False)).translate((0, 0, TH))
lid = lid.cut(cq.Workplane("XY").circle(GP_OD / 2 - 2).extrude(20).translate((0, 0, TH - 5)))

rows = cq.Workplane("XY")
picks = []
for i in range(N_ROWS):
    x = STORE_X0 + ROW_P / 2 + i * ROW_P
    clash = abs(x) < KEEP_R + ROW_P / 2
    end_y = -(KEEP_R + 10) if clash else 0.0
    length = end_y - FRONT_Y
    r = (cq.Workplane("XY").box(ROW_P - 4, length, 30, centered=(True, False, False))
         .rotate((0, 0, 0), (1, 0, 0), -12).translate((x, FRONT_Y, TH - 70)))
    rows = rows.union(r)
    lid = lid.cut(cq.Workplane("XY").circle(POD_D / 2 + 2).extrude(20).translate((x, end_y, TH - 5)))
    picks.append((x, end_y, int(length // PITCH)))

seed = cq.Workplane("XY").box(200, 380, 40, centered=(False, True, False)).translate((-345, 0, TH - 60))

grow = cq.Workplane("XY").circle(GP_OD / 2).circle(GP_OD / 2 - 2.5).extrude(1400).translate((0, 0, TH))
socket = cq.Workplane("XY").circle(SOCKET_OD / 2).circle(GP_OD / 2 + 0.5).extrude(25).translate((0, 0, TH + 4))
mesh = cq.Workplane("XY").circle(GP_OD / 2 - 2).extrude(2).translate((0, 0, TH - 2))
drop = cq.Workplane("XY").circle(GP_OD / 2 - 6).circle(GP_OD / 2 - 8).extrude(TH - 60).translate((0, 0, 60))

pipes = cq.Workplane("XY").pushPoints([(-PIPE_X, 0), (PIPE_X, 0)]).circle(16).extrude(500).translate((0, 0, TH + 80))
shoulders = cq.Workplane("XY").pushPoints([(-PIPE_X, 0), (PIPE_X, 0)]).sphere(15).translate((0, 0, SHOULDER_Z))
reach = (cq.Workplane("XZ").pushPoints([(-PIPE_X, SHOULDER_Z), (PIPE_X, SHOULDER_Z)])
         .circle(REACH).extrude(1).translate((0, 0.5, 0)))

total = sum(n for _, _, n in picks)
worst = 0.0
for x, y, n in picks:
    d = min(math.sqrt((x - sx) ** 2 + y ** 2 + (SHOULDER_Z - TH) ** 2) for sx in (-PIPE_X, PIPE_X))
    worst = max(worst, d)
print("pods per row:", [n for _, _, n in picks])
print(f"total {total} pods; worst pick distance {worst:.0f} mm vs reach {REACH:.0f}")

assy = cq.Assembly()
assy.add(tank, name="tank", color=cq.Color(0.85, 0.85, 0.9, 0.3))
assy.add(lid, name="lid_pick_holes", color=cq.Color(0.6, 0.6, 0.65, 0.5))
assy.add(rows, name="pod_rows", color=cq.Color(0.3, 0.55, 0.85))
assy.add(seed, name="seedling_tray", color=cq.Color(0.3, 0.7, 0.4))
assy.add(grow, name="growing_pipe", color=cq.Color(0.95, 0.95, 0.95, 0.8))
assy.add(socket, name="socket", color=cq.Color(0.95, 0.6, 0.2))
assy.add(mesh, name="return_mesh", color=cq.Color(0.2, 0.2, 0.2))
assy.add(drop, name="return_drop", color=cq.Color(0.7, 0.85, 0.95, 0.5))
assy.add(pipes, name="track_pipes_A_B", color=cq.Color(0.7, 0.7, 0.72))
assy.add(shoulders, name="arm_shoulders", color=cq.Color(0.9, 0.1, 0.1))
assy.add(reach, name="arm_reach", color=cq.Color(0.95, 0.4, 0.4, 0.25))
result = assy
