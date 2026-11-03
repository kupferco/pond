# cad/track_joint.py — flush track joint, draft v1 (3 Nov 2026)
# A 100 mm joint tube (same OD as the track pipe) joins two pipes via internal plastic plugs,
# so the outside stays flush at 32 mm for the wheels. A narrow bracket stem sits on the +X
# (jaw) side, held by an M5 screw through the tube wall into a curved inner plate with a
# captive nut facing inwards. Bracket stem width must stay under the hand's 14 mm jaw.
import cadquery as cq
import math

PIPE_OD = 32.0; PIPE_WALL = 2.0          # assumed
PIPE_ID = PIPE_OD - 2 * PIPE_WALL
JOINT_L = 100.0                          # joint tube length
PLUG_IN = 30.0                           # plug depth into joint tube and into each pipe
PLUG_CLEAR = 0.15
PIPE_STUB = 60.0                         # length of track pipe shown each side
STEM_W = 12.0                            # bracket width (< 14 mm jaw OPENING_W)
SADDLE_L = 30.0                          # bracket foot length along the pipe
SADDLE_T = 3.0
STEM_OUT = 40.0                          # stem reach out towards the spine
PLATE_T = 3.0; PLATE_ANG = 50.0          # inner plate thickness, arc span (deg)
NUT_BOSS_D = 10.0; NUT_BOSS_H = 5.0
SCREW_D = 5.5                            # M5 clearance

R = PIPE_OD / 2; RI = PIPE_ID / 2

def tube(r_out, r_in, z0, length):
    return cq.Workplane("XY").circle(r_out).circle(r_in).extrude(length).translate((0, 0, z0))

joint = tube(R, RI, -JOINT_L / 2, JOINT_L)
pipe_a = tube(R, RI, JOINT_L / 2, PIPE_STUB)
pipe_b = tube(R, RI, -JOINT_L / 2 - PIPE_STUB, PIPE_STUB)

plug_r = RI - PLUG_CLEAR
plug_a = cq.Workplane("XY").circle(plug_r).circle(plug_r - 3).extrude(2 * PLUG_IN).translate((0, 0, JOINT_L / 2 - PLUG_IN))
plug_b = cq.Workplane("XY").circle(plug_r).circle(plug_r - 3).extrude(2 * PLUG_IN).translate((0, 0, -JOINT_L / 2 - PLUG_IN))

# curved inner plate on +X, centred, with nut boss pointing inward
half = math.radians(PLATE_ANG / 2)
def arc_seg(r_out, r_in, ang, length, z0):
    a = math.radians(ang / 2)
    w = (cq.Workplane("XY")
         .moveTo(r_in * math.cos(a), -r_in * math.sin(a))
         .lineTo(r_out * math.cos(a), -r_out * math.sin(a))
         .threePointArc((r_out, 0), (r_out * math.cos(a), r_out * math.sin(a)))
         .lineTo(r_in * math.cos(a), r_in * math.sin(a))
         .threePointArc((r_in, 0), (r_in * math.cos(a), -r_in * math.sin(a)))
         .close().extrude(length).translate((0, 0, z0)))
    return w

plate = arc_seg(RI - 0.1, RI - 0.1 - PLATE_T, PLATE_ANG, 30.0, -15.0)
boss = cq.Workplane("YZ").circle(NUT_BOSS_D / 2).extrude(NUT_BOSS_H).translate((RI - 0.1 - PLATE_T - NUT_BOSS_H, 0, 0))
plate = plate.union(boss)

# bracket: curved saddle on outside +X, plus stem out along +X
s_ang = math.degrees(2 * math.asin((STEM_W / 2) / R))
saddle = arc_seg(R + SADDLE_T, R + 0.05, s_ang, SADDLE_L, -SADDLE_L / 2)
stem = cq.Workplane("XY").box(STEM_OUT, STEM_W, SADDLE_L).translate((R + SADDLE_T + STEM_OUT / 2 - 2, 0, 0))
bracket = saddle.union(stem)
bracket = bracket.cut(cq.Workplane("XY").box(10, 20, 6).translate((R + SADDLE_T + STEM_OUT - 8, 0, 0)))  # slot to spine

screw = cq.Workplane("YZ").circle(SCREW_D / 2).extrude(R + SADDLE_T + 20).translate((RI - PLATE_T - NUT_BOSS_H - 1, 0, 0))
joint = joint.cut(screw); plate = plate.cut(cq.Workplane("YZ").circle(4.2 / 2).extrude(30).translate((0, 0, 0)))
bracket = bracket.cut(screw)
# relieve inner side of plugs where the plate sits (plugs stop short of middle anyway)

assy = cq.Assembly()
assy.add(pipe_a, name="pipe_a", color=cq.Color(0.7, 0.7, 0.72))
assy.add(pipe_b, name="pipe_b", color=cq.Color(0.7, 0.7, 0.72))
assy.add(joint, name="joint_tube", color=cq.Color(0.45, 0.6, 0.8))
assy.add(plug_a, name="plug_a", color=cq.Color(0.95, 0.6, 0.2))
assy.add(plug_b, name="plug_b", color=cq.Color(0.95, 0.6, 0.2))
assy.add(plate, name="nut_plate", color=cq.Color(0.9, 0.2, 0.2))
assy.add(bracket, name="bracket", color=cq.Color(0.2, 0.7, 0.3))
result = assy
print(f"pipe ID {PIPE_ID} mm, stem {STEM_W} mm (jaw 14), saddle arc {s_ang:.1f} deg")
