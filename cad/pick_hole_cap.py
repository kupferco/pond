# cad/pick_hole_cap.py — pick-hole twist cap, concept v2 (4 Nov 2026)
# v2 sealing: the cover no longer wipes across the O-ring.
#  - An arc-shaped RAMP rail on the lid (green) runs round the pivot under the cover's outer
#    edge. A small bump under the cover rides on it. Over most of the swing the rail holds the
#    cover ~2 mm up, clear of the O-ring. In the last ~20 deg before CLOSED the rail ramps
#    down to zero, so the cover drops straight onto the O-ring (cam-lock action).
#  - A compression spring on the pivot (blue) pushes the cover down onto the ring.
#  - A second small O-ring seals the pivot pin where it passes through the lid.
# Left: CLOSED (bump at bottom of ramp, cover pressed on O-ring). Right: OPEN (on top of rail).
# ASSUMED: pod 25 x 40 mm; hole 29 mm; lid 4 mm; pivot 30 mm from hole centre.
import cadquery as cq
import math

HOLE_D = 29.0; LID_T = 4.0
PIVOT_OFF = 30.0
COVER_D = 40.0; COVER_T = 3.0; ARM_W = 14.0
PIN_D = 6.0; KNOB_D = 14.0; KNOB_H = 14.0; KNOB_FLATS = 10.0
ORING_CS = 2.0
LIFT = 2.0                      # how far the rail lifts the cover off the ring
RAMP_R = PIVOT_OFF + COVER_D / 2 - 4   # radius (from pivot) of rail/bump track
RAMP_W = 4.0
SWING = 90.0; RAMP_DEG = 20.0
SPRING_OD = 11.0; SPRING_H = 10.0
SPACING = 130.0
POD_D = 25.0; POD_H = 40.0

def rail(px):
    # stepped arc: height 0 at 0 deg (closed), rising to LIFT by RAMP_DEG, flat to SWING+10
    segs = None
    n = 40
    for i in range(n):
        a0 = -5 + i * (SWING + 15) / n
        a1 = a0 + (SWING + 15) / n
        am = (a0 + a1) / 2
        h = 0.3 if am <= 0 else min(LIFT, LIFT * am / RAMP_DEG) + 0.3
        seg = (cq.Workplane("XY").box(RAMP_R * math.radians(a1 - a0) + 0.4, RAMP_W, h,
                                      centered=(True, True, False))
               .translate((RAMP_R, 0, 0)).rotate((0, 0, 0), (0, 0, 1), am).translate((px, 0, 0)))
        segs = seg if segs is None else segs.union(seg)
    return segs

def station(x0, angle_deg):
    lift = 0.0 if angle_deg < 1 else LIFT
    lid = cq.Workplane("XY").box(120, 100, LID_T, centered=(True, True, False)).translate((x0, 0, -LID_T))
    lid = lid.cut(cq.Workplane("XY").circle(HOLE_D / 2).extrude(10).translate((x0, 0, -LID_T - 1)))
    lid = lid.cut(cq.Workplane("XY").circle(HOLE_D / 2 + 4 + ORING_CS / 2).circle(HOLE_D / 2 + 4 - ORING_CS / 2)
                  .extrude(ORING_CS * 0.7).translate((x0, 0, -ORING_CS * 0.7)))
    px = x0 - PIVOT_OFF
    lid = lid.cut(cq.Workplane("XY").circle(PIN_D / 2 + ORING_CS * 0.7).extrude(ORING_CS).translate((px, 0, -ORING_CS)))
    oring = cq.Workplane("XY").add(cq.Solid.makeTorus(HOLE_D / 2 + 4, ORING_CS / 2)).translate((x0, 0, -ORING_CS * 0.35))
    pin_oring = cq.Workplane("XY").add(cq.Solid.makeTorus(PIN_D / 2 + ORING_CS / 2, ORING_CS / 2)).translate((px, 0, -ORING_CS / 2))
    pin = cq.Workplane("XY").circle(PIN_D / 2).extrude(LID_T + COVER_T + KNOB_H + SPRING_H + 6).translate((px, 0, -LID_T))
    head = cq.Workplane("XY").circle(SPRING_OD / 2 + 1).extrude(2).translate((px, 0, COVER_T + KNOB_H + SPRING_H + 2))
    z0 = 0.3 + lift
    cover = (cq.Workplane("XY").circle(COVER_D / 2).extrude(COVER_T).translate((x0, 0, z0))
             .union(cq.Workplane("XY").box(PIVOT_OFF, ARM_W, COVER_T, centered=(False, True, False)).translate((px, 0, z0)))
             .union(cq.Workplane("XY").circle(ARM_W / 2 + 2).extrude(COVER_T).translate((px, 0, z0))))
    bump = cq.Workplane("XY").circle(2.0).extrude(0.6).translate((px + RAMP_R, 0, z0 - 0.3))
    cover = cover.union(bump)
    knob = (cq.Workplane("XY").circle(KNOB_D / 2).circle(PIN_D / 2 + 0.3).extrude(KNOB_H).translate((px, 0, z0 + COVER_T))
            .cut(cq.Workplane("XY").rect(KNOB_D + 2, KNOB_D + 2).rect(KNOB_D + 2, KNOB_FLATS)
                 .extrude(KNOB_H).translate((px, 0, z0 + COVER_T + 4))))
    cover = cover.union(knob).rotate((px, 0, 0), (px, 0, 1), angle_deg)
    sb = z0 + COVER_T + KNOB_H
    spring = cq.Workplane("XY").circle(SPRING_OD / 2).circle(SPRING_OD / 2 - 1.2).extrude(COVER_T + KNOB_H + SPRING_H + 2 - sb).translate((px, 0, sb))
    pod = cq.Workplane("XY").circle(POD_D / 2).extrude(POD_H).translate((x0, 0, -LID_T - 6 - POD_H))
    return dict(lid=lid, oring=oring, pin_oring=pin_oring, pin=pin.union(head), cover=cover,
                spring=spring, ramp=rail(px), pod=pod)

colors = dict(lid=(0.6, 0.6, 0.65, 0.6), oring=(0.1, 0.1, 0.1, 1), pin_oring=(0.1, 0.1, 0.1, 1),
              pin=(0.3, 0.3, 0.3, 1), cover=(0.95, 0.6, 0.2, 1), spring=(0.3, 0.55, 0.9, 1),
              ramp=(0.3, 0.75, 0.4, 1), pod=(0.6, 0.45, 0.25, 1))
assy = cq.Assembly()
for name, x0, ang in (("closed", -SPACING / 2, 0.0), ("open", SPACING / 2, SWING)):
    parts = station(x0, ang)
    for k, v in parts.items():
        assy.add(v, name=f"{k}_{name}", color=cq.Color(*colors[k]))
result = assy
