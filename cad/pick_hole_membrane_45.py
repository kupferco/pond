import cadquery as cq
# Pick hole membrane tilted 45 deg with the pod axis (26 Nov 2026, concept)
# Membrane square to the pod axis so the 32 mm hole stays round to the gripper.
# + drain notch in the snap ring at the LOW edge (water runs off, never pools behind the lip)
# + small hood over the HIGH edge (keeps rain and light off the slits)
# Built flat (axis = Z), then the whole thing rolled 45 deg about X. +Y = high side.
HOLE_D = 32.0; LID_T = 4.0
MEM_T = 1.5; MEM_D = HOLE_D + 8
RING_OD = MEM_D + 6; RING_T = 3.0
POD_D = 25.0; POD_H = 40.0
SLIT_W = 0.8
TILT = 45.0

lid = cq.Workplane("XY").box(90, 90, LID_T, centered=(True, True, False)).translate((0, 0, -LID_T))
lid = lid.cut(cq.Workplane("XY").circle(HOLE_D / 2).extrude(10).translate((0, 0, -LID_T - 1)))

mem = cq.Workplane("XY").circle(MEM_D / 2).extrude(MEM_T)
for ang in (0, 90):
    mem = mem.cut(cq.Workplane("XY").box(HOLE_D * 0.8, SLIT_W, MEM_T + 1)
                  .rotate((0, 0, 0), (0, 0, 1), ang).translate((0, 0, MEM_T / 2)))

ring = cq.Workplane("XY").circle(RING_OD / 2).circle(HOLE_D / 2).extrude(RING_T).translate((0, 0, MEM_T))
# drain notch at the low edge (-Y) only
notch = cq.Workplane("XY").box(8, 12, RING_T + 1, centered=(True, False, False)).translate((0, -RING_OD / 2 - 2, MEM_T - 0.5))
ring = ring.cut(notch)

# hood over the high half (+Y), open on the low side
hood_r_in = RING_OD / 2 + 1; hood_t = 2.0; hood_h = 14.0
half = cq.Workplane("XY").box(200, 200, 100, centered=(True, False, True)).translate((0, -200, 0))
hood = cq.Workplane("XY").circle(hood_r_in + hood_t).circle(hood_r_in).extrude(hood_h).cut(half)
cap = cq.Workplane("XY").circle(hood_r_in + hood_t).extrude(hood_t).translate((0, 0, hood_h)).cut(half.translate((0, 8, 0)))
hood = hood.union(cap)

pod = cq.Workplane("XY").circle(POD_D / 2).extrude(POD_H).translate((0, 0, -LID_T - 6 - POD_H))

assy = cq.Assembly()
def add(o, n, c):
    assy.add(o.rotate((0, 0, 0), (1, 0, 0), TILT), name=n, color=cq.Color(*c))
add(lid, "lid", (0.6, 0.6, 0.65, 0.5))
add(mem, "membrane", (0.95, 0.35, 0.35, 1))
add(ring, "snap_ring_with_drain", (0.3, 0.3, 0.3, 1))
add(hood, "hood", (0.3, 0.55, 0.9, 0.8))
add(pod, "pod_on_axis", (0.6, 0.45, 0.25, 1))
result = assy
