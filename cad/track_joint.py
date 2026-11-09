# cad/track_joint.py — flush track joint, draft v2 (3 Nov 2026)
# v2: bracket replaced by a single M8 threaded rod. The rod screws into a captive nut on a
# curved inner plate, a lock nut clamps it against the joint tube, and the far end goes to
# the spine. One rod per joint is enough: each pipe is held top and bottom, so it can't
# swivel. Rod and nut sit on the +X (jaw) side, well under the hand's 14 mm jaw.
import cadquery as cq
import math

PIPE_OD = 32.0; PIPE_WALL = 2.0          # assumed standard pipe
PIPE_ID = PIPE_OD - 2 * PIPE_WALL
JOINT_L = 100.0
PLUG_IN = 30.0
PLUG_CLEAR = 0.15
PIPE_STUB = 60.0
ROD_D = 8.0                              # M8 threaded rod
ROD_OUT = 50.0                           # reach from tube surface to spine
LOCKNUT_AF = 13.0; LOCKNUT_H = 6.5       # M8 nut
PLATE_T = 3.0; PLATE_ANG = 50.0; PLATE_L = 30.0
NUT_BOSS_D = 14.0; NUT_BOSS_H = 6.5      # captive M8 nut, facing inward
HOLE_D = 8.5

R = PIPE_OD / 2; RI = PIPE_ID / 2

def tube(r_out, r_in, z0, length):
    return cq.Workplane("XY").circle(r_out).circle(r_in).extrude(length).translate((0, 0, z0))

def arc_seg(r_out, r_in, ang, length, z0):
    a = math.radians(ang / 2)
    return (cq.Workplane("XY")
            .moveTo(r_in * math.cos(a), -r_in * math.sin(a))
            .lineTo(r_out * math.cos(a), -r_out * math.sin(a))
            .threePointArc((r_out, 0), (r_out * math.cos(a), r_out * math.sin(a)))
            .lineTo(r_in * math.cos(a), r_in * math.sin(a))
            .threePointArc((r_in, 0), (r_in * math.cos(a), -r_in * math.sin(a)))
            .close().extrude(length).translate((0, 0, z0)))

hole = cq.Workplane("YZ").circle(HOLE_D / 2).extrude(40).translate((0, 0, 0))

joint = tube(R, RI, -JOINT_L / 2, JOINT_L).cut(hole)
pipe_a = tube(R, RI, JOINT_L / 2, PIPE_STUB)
pipe_b = tube(R, RI, -JOINT_L / 2 - PIPE_STUB, PIPE_STUB)

pr = RI - PLUG_CLEAR
plug_a = cq.Workplane("XY").circle(pr).circle(pr - 3).extrude(2 * PLUG_IN).translate((0, 0, JOINT_L / 2 - PLUG_IN))
plug_b = cq.Workplane("XY").circle(pr).circle(pr - 3).extrude(2 * PLUG_IN).translate((0, 0, -JOINT_L / 2 - PLUG_IN))

plate_in = RI - 0.1 - PLATE_T
plate = arc_seg(RI - 0.1, plate_in, PLATE_ANG, PLATE_L, -PLATE_L / 2)
nut_in = (cq.Workplane("YZ").polygon(6, NUT_BOSS_D).extrude(NUT_BOSS_H)
          .translate((plate_in - NUT_BOSS_H + 0.5, 0, 0)))
plate = plate.union(nut_in).cut(cq.Workplane("YZ").circle(ROD_D / 2).extrude(30).translate((-5, 0, 0)))

rod_x0 = plate_in - NUT_BOSS_H + 1
rod = cq.Workplane("YZ").circle(ROD_D / 2).extrude(R + ROD_OUT - rod_x0).translate((rod_x0, 0, 0))
locknut = (cq.Workplane("YZ").polygon(6, LOCKNUT_AF / math.cos(math.pi / 6)).extrude(LOCKNUT_H)
           .translate((R, 0, 0)).cut(cq.Workplane("YZ").circle(ROD_D / 2).extrude(20).translate((R - 1, 0, 0))))

assy = cq.Assembly()
for n, s, c in [("pipe_a", pipe_a, (0.7, 0.7, 0.72)), ("pipe_b", pipe_b, (0.7, 0.7, 0.72)),
                ("joint_tube", joint, (0.45, 0.6, 0.8)), ("plug_a", plug_a, (0.95, 0.6, 0.2)),
                ("plug_b", plug_b, (0.95, 0.6, 0.2)), ("nut_plate", plate, (0.9, 0.2, 0.2)),
                ("m8_rod", rod, (0.3, 0.3, 0.3)), ("lock_nut", locknut, (0.2, 0.7, 0.3))]:
    assy.add(s, name=n, color=cq.Color(*c))
result = assy
print(f"rod M8, lock nut across corners {LOCKNUT_AF / math.cos(math.pi/6):.1f} mm vs jaw 14 mm")
