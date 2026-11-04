# cad/cleanout_section_door.py — comparison option (4 Nov 2026)
# Same cleanout window as cleanout_section.py, but closed by a curved door that slides
# sideways (around the pipe) in two printed rails, one above and one below the window.
# Door shown half open. Needs custom parts: two rail rings + curved door (3D print / mould).
# ASSUMED: growing pipe 75 mm OD, 2.5 mm wall.
import cadquery as cq
import math

OD = 75.0; WALL = 2.5; ID = OD - 2 * WALL
SEC_L = 250.0
WIN_W = 40.0; WIN_H = 70.0; WIN_Z = 90.0
R = OD / 2; RI = ID / 2
DOOR_T = 2.5; DOOR_CLEAR = 0.3
RAIL_H = 8.0; RAIL_LIP = 3.0
DOOR_ANG = 80.0          # angular width of door
OPEN_ROT = 35.0          # how far it's slid round (shown part open)

def tube(ro, ri, z0, h):
    return cq.Workplane("XY").circle(ro).circle(ri).extrude(h).translate((0, 0, z0))

def arc(ro, ri, ang, z0, h, rot):
    a = math.radians(ang / 2)
    w = (cq.Workplane("XY")
         .moveTo(ri * math.cos(-a), ri * math.sin(-a))
         .lineTo(ro * math.cos(-a), ro * math.sin(-a))
         .threePointArc((ro, 0), (ro * math.cos(a), ro * math.sin(a)))
         .lineTo(ri * math.cos(a), ri * math.sin(a))
         .threePointArc((ri, 0), (ri * math.cos(-a), ri * math.sin(-a)))
         .close().extrude(h).translate((0, 0, z0)))
    return w.rotate((0, 0, 0), (0, 0, 1), rot)

pipe = tube(R, RI, 0, SEC_L)
window = cq.Workplane("YZ").center(0, WIN_Z).rect(WIN_W, WIN_H).extrude(R + 5)
pipe = pipe.cut(window)

d_ri = R + DOOR_CLEAR
d_ro = d_ri + DOOR_T
door_z0 = WIN_Z - WIN_H / 2 - 4
door_h = WIN_H + 8
door = arc(d_ro, d_ri, DOOR_ANG, door_z0, door_h, OPEN_ROT)
knob = (cq.Workplane("XY").box(6, 10, 20)
        .translate((d_ro + 3, 0, WIN_Z))
        .rotate((0, 0, 0), (0, 0, 1), OPEN_ROT + DOOR_ANG / 2 - 8))
door = door.union(knob)

# rails: a ring below and above the door, each with an L lip that traps the door edge
rail_ro = d_ro + RAIL_LIP
def rail(z0, lip_up):
    base = tube(rail_ro, R, z0, RAIL_H)
    lip_z = z0 + RAIL_H if lip_up else z0 - 3
    lip = tube(rail_ro, d_ro + 0.3, lip_z, 3)
    return base.union(lip)
rail_lo = rail(door_z0 - RAIL_H, True)
rail_hi = rail(door_z0 + door_h, False)

assy = cq.Assembly()
assy.add(pipe, name="cleanout_pipe", color=cq.Color(0.75, 0.75, 0.78))
assy.add(rail_lo, name="rail_lower", color=cq.Color(0.95, 0.6, 0.2))
assy.add(rail_hi, name="rail_upper", color=cq.Color(0.95, 0.6, 0.2))
assy.add(door, name="sliding_door", color=cq.Color(0.3, 0.55, 0.85))
result = assy
