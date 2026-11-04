# cad/cleanout_section.py — growing pipe cleanout section, draft v1 (4 Nov 2026)
# Bottom section of the growing pipe stack. A window in the wall gives access to the inside
# for cleaning; a sleeve slides up to open it and down to close it. Two O-rings (one above,
# one below the window) seal the sleeve when closed. Male plug at the top joins the next
# section (same flush-joint idea as the track); bottom sits in the socket on the tank lid.
# ASSUMED: growing pipe 75 mm OD, 2.5 mm wall. Nothing checked yet.
import cadquery as cq

OD = 75.0; WALL = 2.5; ID = OD - 2 * WALL
SEC_L = 250.0
WIN_W = 40.0; WIN_H = 70.0; WIN_Z = 90.0      # window centre height
SLEEVE_T = 3.0; SLEEVE_CLEAR = 0.3
SLEEVE_L = WIN_H + 50.0
ORING_CS = 3.0
PLUG_L = 30.0; PLUG_T = 3.0; PLUG_CLEAR = 0.2

R = OD / 2; RI = ID / 2

def tube(ro, ri, z0, h):
    return cq.Workplane("XY").circle(ro).circle(ri).extrude(h).translate((0, 0, z0))

pipe = tube(R, RI, 0, SEC_L)
window = (cq.Workplane("XZ").center(0, WIN_Z).rect(WIN_W, WIN_H).extrude(-R - 5))
pipe = pipe.cut(window)
# O-ring grooves above and below the window
for z in (WIN_Z - WIN_H / 2 - 10, WIN_Z + WIN_H / 2 + 10):
    groove = tube(R + 1, R - ORING_CS * 0.7, z - ORING_CS / 2, ORING_CS)
    pipe = pipe.cut(groove)

plug_r = RI - PLUG_CLEAR
plug = tube(plug_r, plug_r - PLUG_T, SEC_L - PLUG_L, 2 * PLUG_L)

# sleeve shown in the OPEN (raised) position so the window is visible
s_ri = R + SLEEVE_CLEAR
sleeve_z = WIN_Z + WIN_H / 2 + 5
sleeve = tube(s_ri + SLEEVE_T, s_ri, sleeve_z, SLEEVE_L)
grip = tube(s_ri + SLEEVE_T + 3, s_ri, sleeve_z, 10)
sleeve = sleeve.union(grip)

orings = None
for z in (WIN_Z - WIN_H / 2 - 10, WIN_Z + WIN_H / 2 + 10):
    o = cq.Workplane("XY").add(cq.Solid.makeTorus(R - ORING_CS * 0.2, ORING_CS / 2)).translate((0, 0, z))
    orings = o if orings is None else orings.union(o)

assy = cq.Assembly()
assy.add(pipe, name="cleanout_pipe", color=cq.Color(0.75, 0.75, 0.78))
assy.add(plug, name="joint_plug", color=cq.Color(0.95, 0.6, 0.2))
assy.add(sleeve, name="sliding_sleeve", color=cq.Color(0.3, 0.55, 0.85, 0.6))
assy.add(orings, name="o_rings", color=cq.Color(0.1, 0.1, 0.1))
result = assy
