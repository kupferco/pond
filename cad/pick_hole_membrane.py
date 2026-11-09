# cad/pick_hole_membrane.py — pick hole with cross-slit silicone membrane (4 Nov 2026)
# Off-the-shelf alternative to the twist cap: a soft silicone disc with a cross cut, clamped
# in the lid hole by a snap ring. The gripper pushes down through the slit, grabs the pod,
# lifts it out; the four petals spring shut behind it. No moving parts.
# Left: CLOSED. Right: OPEN with a pod being lifted through (petals bent up).
# ASSUMED: pod 25 x 40 mm; hole 32 mm; membrane 1.5 mm silicone.
import cadquery as cq
import math

HOLE_D = 32.0; LID_T = 4.0
MEM_T = 1.5; MEM_D = HOLE_D + 8
RING_OD = MEM_D + 6; RING_T = 3.0
POD_D = 25.0; POD_H = 40.0
SPACING = 90.0
SLIT_W = 0.6

def lid_and_ring(x0):
    lid = cq.Workplane("XY").box(80, 70, LID_T, centered=(True, True, False)).translate((x0, 0, -LID_T))
    lid = lid.cut(cq.Workplane("XY").circle(HOLE_D / 2).extrude(10).translate((x0, 0, -LID_T - 1)))
    ring = (cq.Workplane("XY").circle(RING_OD / 2).circle(HOLE_D / 2).extrude(RING_T)
            .translate((x0, 0, MEM_T)))
    return lid, ring

def membrane_closed(x0):
    m = cq.Workplane("XY").circle(MEM_D / 2).extrude(MEM_T).translate((x0, 0, 0))
    for ang in (0, 90):
        slit = (cq.Workplane("XY").box(HOLE_D * 0.8, SLIT_W, MEM_T + 1)
                .rotate((0, 0, 0), (0, 0, 1), ang).translate((x0, 0, MEM_T / 2)))
        m = m.cut(slit)
    return m

def membrane_open(x0):
    # outer clamped rim + four petals bent up ~70 deg
    rim = cq.Workplane("XY").circle(MEM_D / 2).circle(HOLE_D / 2 - 1).extrude(MEM_T).translate((x0, 0, 0))
    petals = None
    r_in = HOLE_D / 2 - 1
    for k in range(4):
        a = 45 + 90 * k
        p = (cq.Workplane("XY").moveTo(0, 0).lineTo(r_in, -r_in * math.tan(math.radians(40)))
             .lineTo(r_in, r_in * math.tan(math.radians(40))).close().extrude(MEM_T))
        # hinge at r_in: move tip so the hinge line sits at origin, bend up, move back
        p = (p.translate((-r_in, 0, 0)).rotate((0, 0, 0), (0, 1, 0), 70)
             .translate((r_in, 0, 0)).rotate((0, 0, 0), (0, 0, 1), a + 180).translate((x0, 0, 0)))
        petals = p if petals is None else petals.union(p)
    return rim, petals

assy = cq.Assembly()
grey = cq.Color(0.6, 0.6, 0.65, 0.5)
sil = cq.Color(0.95, 0.35, 0.35)
xc, xo = -SPACING / 2, SPACING / 2
lid, ring = lid_and_ring(xc)
assy.add(lid, name="lid_closed", color=grey)
assy.add(ring, name="snap_ring_closed", color=cq.Color(0.3, 0.3, 0.3))
assy.add(membrane_closed(xc), name="membrane_closed", color=sil)
assy.add(cq.Workplane("XY").circle(POD_D / 2).extrude(POD_H).translate((xc, 0, -LID_T - 6 - POD_H)),
         name="pod_waiting", color=cq.Color(0.6, 0.45, 0.25))

lid, ring = lid_and_ring(xo)
assy.add(lid, name="lid_open", color=grey)
assy.add(ring, name="snap_ring_open", color=cq.Color(0.3, 0.3, 0.3))
rim, petals = membrane_open(xo)
assy.add(rim, name="membrane_rim_open", color=sil)
assy.add(petals, name="membrane_petals_open", color=sil)
assy.add(cq.Workplane("XY").circle(POD_D / 2).extrude(POD_H).translate((xo, 0, -POD_H / 2)),
         name="pod_lifting", color=cq.Color(0.6, 0.45, 0.25))
result = assy
