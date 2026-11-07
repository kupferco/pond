import cadquery as cq
# cad/bottom_bracket.py — v1 (7 Nov 2026)
# Bottom track bracket, moved just above the cleanout section (z ~570, was 450 and clashed with the hatch).
# Threaded boss welded to the spine, drilled through into the spine bore. Hollow 12 mm rod screws in from
# outside through a grommeted hole in the PVC growing pipe, lock nut; the dock cable runs inside the rod,
# into the spine, down to the controller on the tank shelf.
# Charging plates on the track right beside the bracket, in the strip next to the hand's funnel gap.
# Section view: front half of the growing pipe cut away. Local origin at bracket height.
GP = 75.0; SP = 33.7; TR = 16.0; LOOP_Y = -60.0
def box(sx, sy, sz, cx, cy, cz):
    return cq.Workplane("XY").box(sx, sy, sz).translate((cx, cy, cz))
def ycyl(r, y0, y1, x=0, z=0, ri=0):
    w = cq.Workplane("XZ").circle(r)
    if ri: w = w.circle(ri)
    return w.extrude(-(y1 - y0)).translate((x, y0, z))
assy = cq.Assembly()
def add(o, n, c): assy.add(o, name=n, color=cq.Color(*c))
spine = cq.Workplane("XY").circle(SP / 2).circle(SP / 2 - 2).extrude(260).translate((0, 0, -130))
spine = spine.cut(ycyl(4, -20, 0))
add(spine, "spine_tube", (0.35, 0.35, 0.35, 1))
pipe = cq.Workplane("XY").circle(GP / 2).circle(GP / 2 - 3).extrude(260).translate((0, 0, -130))
pipe = pipe.cut(box(100, 50, 270, 0, -25, 0).cut(box(30, 50, 40, 0, -25, 0)))
pipe = pipe.cut(ycyl(9, -45, -25))
add(pipe, "growing_pipe_section_cut", (0.95, 0.95, 0.95, 0.4))
add(cq.Workplane("XY").circle(GP / 2 + 4).circle(GP / 2 + 0.5).extrude(100).translate((0, 0, -230)), "cleanout_sleeve_below", (0.3, 0.55, 0.85, 1))
add(ycyl(9, -(SP / 2 + 12), -(SP / 2 - 1), ri=4), "welded_threaded_boss", (0.55, 0.57, 0.6, 1))
add(ycyl(6, LOOP_Y + TR, -(SP / 2 + 10), ri=4), "hollow_rod_12mm", (0.95, 0.6, 0.2, 1))
add(ycyl(10, -(GP / 2 + 2), -(GP / 2 - 4), ri=6), "grommet", (0.1, 0.1, 0.1, 1))
add(ycyl(10, -(GP / 2 + 9), -(GP / 2 + 3), ri=6), "lock_nut", (0.4, 0.4, 0.4, 1))
add(box(16, 10, 30, 0, LOOP_Y + TR + 3, 0), "bracket_saddle", (0.2, 0.2, 0.2, 1))
track = cq.Workplane("YZ").circle(TR).extrude(400).translate((-200, LOOP_Y, 0))
add(track, "track_bottom_run", (0.7, 0.7, 0.72, 1))
for x, n, col in ((-28, "plus", (0.85, 0.5, 0.2, 1)), (28, "minus", (0.6, 0.35, 0.15, 1))):
    pl = cq.Workplane("YZ").circle(TR + 3).circle(TR).extrude(30).translate((x - 15, LOOP_Y, 0))
    pl = pl.intersect(box(40, 20, 40, x, LOOP_Y + 10, 0))
    add(pl, f"plate_{n}", col)
c1 = ycyl(2.5, LOOP_Y + 8, 0)
c2 = cq.Workplane("XY").circle(2.5).extrude(125).translate((0, 0, -125))
add(c1.union(c2), "dock_cable_to_controller", (0.9, 0.1, 0.1, 1))
result = assy
