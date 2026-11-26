import cadquery as cq
# Pick hole membrane at 45 deg on a FLAT lid (26 Nov 2026, concept v2)
# Lid stays flat. A short angled collar is moulded on the lid; its top face is square to the
# pod axis, so the membrane and 32 mm hole are round to the gripper coming in at 45 deg.
# The collar meets the flat lid in an oval cut. No hood (it blocked the pod's way out).
# Drain notch in the snap ring at the LOW edge so rain runs off the tilted membrane.
HOLE_D = 32.0; LID_T = 4.0
COLLAR_OD = 46.0; COLLAR_TOP = 22.0     # collar top face, measured along the pod axis
MEM_T = 1.5; MEM_D = HOLE_D + 8
RING_OD = MEM_D + 6; RING_T = 3.0
POD_D = 25.0; POD_H = 40.0
SLIT_W = 0.8
TILT = 45.0
AX = ((0, 0, 0), (1, 0, 0), TILT)       # rotate axis-frame parts into the world

lid = cq.Workplane("XY").box(140, 110, LID_T, centered=(True, True, False)).translate((0, 0, -LID_T))

collar = cq.Workplane("XY").circle(COLLAR_OD / 2).extrude(COLLAR_TOP + 40).translate((0, 0, -40)).rotate(*AX)
below = cq.Workplane("XY").box(300, 300, 200, centered=(True, True, False)).translate((0, 0, -LID_T - 200))
collar = collar.cut(below)

body = lid.union(collar)
bore = cq.Workplane("XY").circle(HOLE_D / 2).extrude(200).translate((0, 0, -100)).rotate(*AX)
body = body.cut(bore)

mem = cq.Workplane("XY").circle(MEM_D / 2).extrude(MEM_T)
for ang in (0, 90):
    mem = mem.cut(cq.Workplane("XY").box(HOLE_D * 0.8, SLIT_W, MEM_T + 1)
                  .rotate((0, 0, 0), (0, 0, 1), ang).translate((0, 0, MEM_T / 2)))
mem = mem.translate((0, 0, COLLAR_TOP)).rotate(*AX)

ring = cq.Workplane("XY").circle(RING_OD / 2).circle(HOLE_D / 2).extrude(RING_T).translate((0, 0, MEM_T))
notch = cq.Workplane("XY").box(8, 12, RING_T + 1, centered=(True, False, False)).translate((0, -RING_OD / 2 - 2, MEM_T - 0.5))
ring = ring.cut(notch).translate((0, 0, COLLAR_TOP)).rotate(*AX)   # -Y = low side after the tilt

pod = cq.Workplane("XY").circle(POD_D / 2).extrude(POD_H).translate((0, 0, -30 - POD_H)).rotate(*AX)

assy = cq.Assembly()
assy.add(body, name="flat_lid_with_45deg_collar", color=cq.Color(0.6, 0.6, 0.65, 0.6))
assy.add(mem, name="membrane", color=cq.Color(0.95, 0.35, 0.35))
assy.add(ring, name="snap_ring_drain_at_low_edge", color=cq.Color(0.3, 0.3, 0.3))
assy.add(pod, name="pod_on_45deg_axis", color=cq.Color(0.6, 0.45, 0.25))
result = assy
