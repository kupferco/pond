# cad/pick_hole_cap.py — pick-hole twist cap, concept v1 (4 Nov 2026)
# A cap can't uncover a hole by spinning on the hole's own axis, so the pivot sits beside
# the hole (like a keyhole cover). The robot grips the knob on top of the pivot and twists
# it a quarter turn: the cover swings off the hole. Twist back to close; an O-ring in the lid
# under the cover seals it, and a small bump/dimple detent holds it shut.
# Left: CLOSED. Right: OPEN (swung 90 deg).
# ASSUMED: pod 25 mm -> hole 29 mm; lid 4 mm; pivot 30 mm from hole centre.
import cadquery as cq
import math

HOLE_D = 29.0; LID_T = 4.0
PIVOT_OFF = 30.0
COVER_D = 40.0; COVER_T = 3.0
ARM_W = 14.0
PIN_D = 6.0; KNOB_D = 14.0; KNOB_H = 14.0; KNOB_FLATS = 10.0
ORING_CS = 2.0
SPACING = 110.0

def station(x0, angle_deg):
    lid = cq.Workplane("XY").box(100, 80, LID_T, centered=(True, True, False)).translate((x0, 0, -LID_T))
    lid = lid.cut(cq.Workplane("XY").circle(HOLE_D / 2).extrude(10).translate((x0, 0, -LID_T - 1)))
    groove = (cq.Workplane("XY").circle(HOLE_D / 2 + 4 + ORING_CS / 2).circle(HOLE_D / 2 + 4 - ORING_CS / 2)
              .extrude(ORING_CS * 0.7).translate((x0, 0, -ORING_CS * 0.7)))
    lid = lid.cut(groove)
    oring = (cq.Workplane("XY").add(cq.Solid.makeTorus(HOLE_D / 2 + 4, ORING_CS / 2))
             .translate((x0, 0, -ORING_CS * 0.35)))
    px = x0 - PIVOT_OFF
    pin = cq.Workplane("XY").circle(PIN_D / 2).extrude(LID_T + COVER_T + 2).translate((px, 0, -LID_T))
    # cover = disc over the hole + arm back to the pivot, built closed then rotated about pivot
    cover = (cq.Workplane("XY").circle(COVER_D / 2).extrude(COVER_T).translate((x0, 0, 0.3))
             .union(cq.Workplane("XY").box(PIVOT_OFF, ARM_W, COVER_T, centered=(False, True, False))
                    .translate((px, 0, 0.3)))
             .union(cq.Workplane("XY").circle(ARM_W / 2 + 2).extrude(COVER_T).translate((px, 0, 0.3))))
    knob = (cq.Workplane("XY").circle(KNOB_D / 2).extrude(KNOB_H).translate((px, 0, 0.3 + COVER_T))
            .cut(cq.Workplane("XY").rect(KNOB_D + 2, KNOB_D + 2).rect(KNOB_D + 2, KNOB_FLATS)
                 .extrude(KNOB_H).translate((px, 0, 0.3 + COVER_T + 4))))
    cover = cover.union(knob)
    cover = cover.rotate((px, 0, 0), (px, 0, 1), angle_deg)
    return lid, oring, pin, cover

assy = cq.Assembly()
for name, x0, ang in (("closed", -SPACING / 2, 0.0), ("open", SPACING / 2, 90.0)):
    lid, oring, pin, cover = station(x0, ang)
    assy.add(lid, name=f"lid_{name}", color=cq.Color(0.6, 0.6, 0.65, 0.6))
    assy.add(oring, name=f"oring_{name}", color=cq.Color(0.1, 0.1, 0.1))
    assy.add(pin, name=f"pivot_{name}", color=cq.Color(0.3, 0.3, 0.3))
    assy.add(cover, name=f"cover_{name}", color=cq.Color(0.95, 0.6, 0.2))
# a pod sitting in the open hole's dip, for scale
pod = cq.Workplane("XZ").circle(12.5).extrude(-25).translate((SPACING / 2, -12.5, -30))
assy.add(pod, name="pod", color=cq.Color(0.6, 0.45, 0.25))
result = assy
