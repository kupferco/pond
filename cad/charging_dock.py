import cadquery as cq
# cad/charging_dock.py — v1 (7 Nov 2026)
# Charging dock on the bottom run of the track (horizontal, 32 mm tube along X).
# Two copper plates (+ and -), 3 mm proud of the pipe, on the FRONT face (-Y) where no wheels run.
# Cart carries two spring-loaded conductive-brush pads that hover 1.5 mm off the bare pipe,
# so they only touch (and compress 1.5 mm) when the cart parks over the plates.
TR = 16.0
def box(sx, sy, sz, cx, cy, cz):
    return cq.Workplane("XY").box(sx, sy, sz).translate((cx, cy, cz))
assy = cq.Assembly()
def add(o, n, c): assy.add(o, name=n, color=cq.Color(*c))
pipe = cq.Workplane("YZ").circle(TR).extrude(500).translate((-250, 0, 0))
add(pipe, "track_bottom_run", (0.7, 0.7, 0.72, 1))
# plates: curved strips wrapping the front of the pipe, 3 mm proud, insulated base
for x, n, col in ((-40, "plate_plus", (0.85, 0.5, 0.2, 1)), (40, "plate_minus", (0.6, 0.35, 0.15, 1))):
    ins = cq.Workplane("YZ").circle(TR + 1.5).circle(TR).extrude(50).translate((x - 25, 0, 0))
    ins = ins.intersect(box(60, 40, 24, x, -20, 0))
    add(ins, n + "_insulator", (0.1, 0.1, 0.1, 1))
    pl = cq.Workplane("YZ").circle(TR + 3).circle(TR + 1.5).extrude(40).translate((x - 20, 0, 0))
    pl = pl.intersect(box(50, 40, 20, x, -20, 0))
    add(pl, n, col)
# cart hand (simplified C sleeve) parked over the dock, with wheel rows top and bottom
sleeve = cq.Workplane("YZ").circle(TR + 22).circle(TR + 12).extrude(220).translate((-110, 0, 0))
sleeve = sleeve.cut(box(240, 30, 26, 0, 30, 0))
add(sleeve, "cart_hand_simplified", (0.9, 0.2, 0.2, 0.35))
for x in (-90, 90):
    for z in (TR + 6, -(TR + 6)):
        add(cq.Workplane("XZ").circle(6).extrude(10).translate((x, 5, z)), f"wheel_{x}_{z}", (0.2, 0.2, 0.2, 1))
# spring-loaded brush pads on the front of the hand
for x, n in ((-40, "plus"), (40, "minus")):
    gap_y = -(TR + 3)          # touching the plate face (pipe+3 mm); off the plates it hovers 1.5 mm above bare pipe
    pad = box(30, 4, 14, x, gap_y - 2, 0)
    add(pad, f"brush_pad_{n}", (0.95, 0.85, 0.3, 1))
    spring = cq.Workplane("XZ").circle(4).circle(3).extrude(10).translate((x, gap_y - 4, 0))
    add(spring, f"spring_{n}", (0.6, 0.6, 0.65, 1))
    add(box(36, 4, 20, x, -(TR + 19), 0), f"pad_holder_{n}", (0.3, 0.3, 0.3, 1))
result = assy
