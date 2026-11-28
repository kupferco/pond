import math
import cadquery as cq

# Spine-to-track connector, draft V3 (assembled, nothing exploded).
# Owner decision 28 Nov 2026: track axis 75 mm from the spine axis (was 66), so the v5 cart sleeve
# (reaches 34.5 mm from the track axis on the spine side) clears the 75 mm growing pipe by 5 mm.
# Rod reach past the track pipe surface: 75 - 16 = 59 mm (was 50).
R = 16.0          # track pipe radius (32 OD)
TRACK_WALL = 2.0  # ASSUMED
AXIS = 75.0       # track axis to spine axis
SP_R = 33.7 / 2   # spine tube
SP_WALL = 2.0
GP_R = 75.0 / 2   # growing pipe, concentric with the spine
GP_WALL = 3.0     # ASSUMED
SLEEVE_REACH = 34.5  # v5 hand sleeve tube outer radius (cad/hand_sleeve.py TUBE_R_MIN)
ROD_D = 8.0
AF = 13.0         # M8 nut across flats
NUT_H = 6.5
L = 150.0

def tube_x(r, wall, length):
    return cq.Workplane("YZ").circle(r).circle(r - wall).extrude(length).translate((-length / 2, 0, 0))

def tube_z(r, wall, length, y):
    return cq.Workplane("XY").center(0, y).circle(r).circle(r - wall).extrude(length).translate((0, 0, -length / 2))

def nut_y(y0, y1):
    d = AF / math.cos(math.pi / 6)
    n = cq.Workplane("XZ").polygon(6, d).extrude(-(y1 - y0)).translate((0, y0, 0))
    return n.cut(cq.Workplane("XZ").circle(ROD_D / 2).extrude(-(y1 - y0 + 2)).translate((0, y0 - 1, 0)))

hole_x = cq.Workplane("XZ").circle(4.5).extrude(-(AXIS + 2 * GP_R)).translate((0, -1, 0))
track = tube_x(R, TRACK_WALL, 200).cut(hole_x)
spine = tube_z(SP_R, SP_WALL, L, AXIS).cut(hole_x)
gpipe = tube_z(GP_R, GP_WALL, L, AXIS).cut(hole_x)
rod = cq.Workplane("XZ").circle(ROD_D / 2).extrude(-(AXIS - 4)).translate((0, 4, 0))

inside_track_nut = nut_y(R - TRACK_WALL - NUT_H, R - TRACK_WALL)
lock_nut = nut_y(R, R + NUT_H)
sp_out = AXIS - SP_R
spine_nut_out = nut_y(sp_out - NUT_H, sp_out)
spine_nut_in = nut_y(sp_out + SP_WALL + 0.5, sp_out + SP_WALL + 0.5 + NUT_H)

a = cq.Assembly()
a.add(track, name="track_pipe", color=cq.Color(0.7, 0.7, 0.72, 1))
a.add(rod, name="m8_rod", color=cq.Color(0.3, 0.3, 0.3, 1))
a.add(inside_track_nut, name="captive_nut", color=cq.Color(0.9, 0.2, 0.2, 1))
a.add(lock_nut, name="lock_nut", color=cq.Color(0.2, 0.7, 0.3, 1))
a.add(spine, name="spine_tube", color=cq.Color(0.55, 0.62, 0.7, 1))
a.add(spine_nut_out, name="spine_nut_outside", color=cq.Color(0.2, 0.7, 0.3, 1))
a.add(spine_nut_in, name="spine_nut_inside", color=cq.Color(0.2, 0.7, 0.3, 1))
a.add(gpipe, name="growing_pipe", color=cq.Color(0.95, 0.95, 0.95, 0.35))

print("rod reach past track surface: %.1f mm" % (AXIS - R))
print("track surface to growing pipe surface: %.1f mm" % (AXIS - R - GP_R))
print("v5 sleeve to growing pipe (straight line, worst case): %.1f mm" % (AXIS - GP_R - SLEEVE_REACH))
result = a
