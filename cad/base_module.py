import cadquery as cq
# cad/base_module.py — v1 (7 Nov 2026)
# Exploded view of the lower spine build:
#  A) tank spine piece: floor socket -> lid (0..304), separate.
#  B) PRE-ASSEMBLED MODULE (factory-wired): ~380 spine piece (304..684) with the cleanout pipe section
#     and the lower growing-pipe stub, bottom-bracket boss + hollow rod + grommet + lock nut, dock cable
#     inside the spine with a plug at the bottom. Spine top ends FLUSH with the pipe section top.
#  C) short bottom track piece with the two charging plates: bolts to the rod on site, one plug.
GP = 75.0; SP = 33.7; TR = 16.0; LOOP_Y = -60.0
LID = 304.0; TOP = 684.0; ZBR = 570.0; GAP = 120.0
def box(sx, sy, sz, cx, cy, cz):
    return cq.Workplane("XY").box(sx, sy, sz).translate((cx, cy, cz))
def zt(ro, ri, z0, z1):
    return cq.Workplane("XY").circle(ro).circle(ri).extrude(z1 - z0).translate((0, 0, z0))
def ycyl(r, y0, y1, z, ri=0):
    w = cq.Workplane("XZ").circle(r)
    if ri: w = w.circle(ri)
    return w.extrude(-(y1 - y0)).translate((0, y0, z))
assy = cq.Assembly()
def add(o, n, c): assy.add(o, name=n, color=cq.Color(*c))
# A
add(zt(SP / 2, SP / 2 - 2, 0, LID), "A_tank_spine_piece", (0.35, 0.35, 0.35, 1))
add(zt(30, SP / 2 + 0.5, 0, 25), "A_floor_socket", (0.95, 0.6, 0.2, 1))
add(box(160, 160, 4, 0, 0, LID + 2).cut(zt(GP / 2 + 1, 0, LID - 2, LID + 6)), "lid_cutaway", (0.6, 0.6, 0.65, 0.4))
add(zt(GP / 2 + 10, GP / 2 + 1, LID + 4, LID + 29), "pipe_socket_on_lid", (0.95, 0.6, 0.2, 1))
# B (lifted by GAP)
g = GAP
add(zt(SP / 2, SP / 2 - 2, LID + g, TOP + g), "B_module_spine", (0.35, 0.35, 0.35, 1))
add(zt(GP / 2, GP / 2 - 3, LID + 4 + g, TOP + g), "B_cleanout_and_pipe_section", (0.95, 0.95, 0.95, 0.45))
add(zt(GP / 2 + 4, GP / 2 + 0.5, LID + 140 + g, LID + 240 + g), "B_cleanout_sleeve", (0.3, 0.55, 0.85, 1))
add(ycyl(9, -(SP / 2 + 12), -(SP / 2 - 1), ZBR + g, ri=4), "B_welded_boss", (0.55, 0.57, 0.6, 1))
add(ycyl(6, LOOP_Y + TR, -(SP / 2 + 10), ZBR + g, ri=4), "B_hollow_rod", (0.95, 0.6, 0.2, 1))
add(ycyl(10, -(GP / 2 + 2), -(GP / 2 - 4), ZBR + g, ri=6), "B_grommet", (0.1, 0.1, 0.1, 1))
add(ycyl(10, -(GP / 2 + 9), -(GP / 2 + 3), ZBR + g, ri=6), "B_lock_nut", (0.4, 0.4, 0.4, 1))
add(box(16, 10, 30, 0, LOOP_Y + TR + 3, ZBR + g), "B_bracket_saddle", (0.2, 0.2, 0.2, 1))
cab = ycyl(2.5, LOOP_Y + 8, 0, ZBR + g).union(zt(2.5, 0, LID + g - 30, ZBR + g))
add(cab, "B_dock_cable", (0.9, 0.1, 0.1, 1))
add(box(14, 14, 20, 0, 0, LID + g - 40), "B_cable_plug", (0.9, 0.1, 0.1, 1))
# C (pulled forward)
fy = -90.0
track = cq.Workplane("YZ").circle(TR).extrude(200).translate((-100, LOOP_Y + fy, ZBR + g))
add(track, "C_bottom_track_piece", (0.7, 0.7, 0.72, 1))
for x, n, col in ((-28, "plus", (0.85, 0.5, 0.2, 1)), (28, "minus", (0.6, 0.35, 0.15, 1))):
    pl = cq.Workplane("YZ").circle(TR + 3).circle(TR).extrude(30).translate((x - 15, LOOP_Y + fy, ZBR + g))
    pl = pl.intersect(box(40, 20, 40, x, LOOP_Y + fy + 10, ZBR + g))
    add(pl, f"C_plate_{n}", col)
result = assy
