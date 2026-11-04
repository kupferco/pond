# cad/pod_store.py — dry pod store, concept v1 (4 Nov 2026)
# Five removable "sticks" (channels) of 20 pods each sit side by side on a slight slope.
# Gravity slides pods to the low (front) end, where the robot picks through one narrow
# door along the front edge. Refill = lift an empty stick out, drop a full one in.
# One stick (the middle one) is shown lifted out mid-swap.
# ASSUMED: pod 25 mm dia x 40 mm, 28 mm pitch -> stick ~570 mm long. Store box sized to the
# right 4/5 of a ~70 x 40 cm tank. Slope 5 deg. Lid and seals not drawn.
import cadquery as cq
import math

POD_D = 25.0; POD_H = 40.0; PITCH = 28.0; N = 20
STICK_W = POD_D + 6; WALL = 2.0
STICK_L = N * PITCH + 10
STICK_H = POD_H * 0.6
N_STICKS = 5; GAP = 4.0
SLOPE = 5.0
BOX_L = STICK_L + 20; BOX_W = N_STICKS * (STICK_W + GAP) + 20; BOX_H = 70.0

def stick(with_pods=True, n=N):
    outer = cq.Workplane("XY").box(STICK_L, STICK_W, STICK_H, centered=(False, True, False))
    inner = (cq.Workplane("XY").box(STICK_L - 2 * WALL, STICK_W - 2 * WALL, STICK_H,
             centered=(False, True, False)).translate((WALL, 0, WALL)))
    s = outer.cut(inner)
    # finger tab at the back end for lifting
    s = s.union(cq.Workplane("XY").box(10, STICK_W, STICK_H + 15, centered=(False, True, False))
                .translate((STICK_L - 10, 0, 0)))
    pods = None
    if with_pods:
        for i in range(n):
            p = (cq.Workplane("XY").circle(POD_D / 2).extrude(POD_H)
                 .translate((WALL + POD_D / 2 + 1 + i * PITCH, 0, WALL)))
            pods = p if pods is None else pods.union(p)
    return s, pods

assy = cq.Assembly()

# store box (open top), front at x=0 is the LOW end
box = cq.Workplane("XY").box(BOX_L, BOX_W, BOX_H, centered=(False, True, False))
box = box.cut(cq.Workplane("XY").box(BOX_L - 6, BOX_W - 6, BOX_H, centered=(False, True, False))
              .translate((3, 0, 3)))
# front pick door slot (narrow, along the front edge)
door = cq.Workplane("XY").box(PITCH + 6, BOX_W - 20, 4, centered=(False, True, False)).translate((3, 0, BOX_H))
assy.add(box, name="store_box", color=cq.Color(0.85, 0.85, 0.88, 0.35))
assy.add(door, name="pick_door_open", color=cq.Color(0.9, 0.2, 0.2))

tilt = lambda w: w.rotate((0, 0, 0), (0, 1, 0), -SLOPE).translate((5, 0, 8))
y0 = -(N_STICKS - 1) / 2 * (STICK_W + GAP)
for k in range(N_STICKS):
    y = y0 + k * (STICK_W + GAP)
    n = [20, 14, 20, 6, 20][k]
    s, pods = stick(True, n)
    if k == 2:
        # middle stick lifted out mid-swap
        s = s.rotate((0, 0, 0), (0, 1, 0), -20).translate((40, y, 150))
        pods = pods.rotate((0, 0, 0), (0, 1, 0), -20).translate((40, y, 150))
        assy.add(s, name=f"stick_{k}_lifted", color=cq.Color(0.3, 0.6, 0.3))
        assy.add(pods, name=f"pods_{k}", color=cq.Color(0.6, 0.45, 0.25))
    else:
        assy.add(tilt(s).translate((0, y, 0)), name=f"stick_{k}", color=cq.Color(0.3, 0.55, 0.85))
        assy.add(tilt(pods).translate((0, y, 0)), name=f"pods_{k}", color=cq.Color(0.6, 0.45, 0.25))

result = assy
