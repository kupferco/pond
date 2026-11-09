import cadquery as cq, math
# cad/clamp_collar.py — v2 (9 Nov 2026)
# Hinged clamp collar for the bracing legs. Clamps OUTSIDE the 75 mm growing pipe: no holes in the PVC.
# Big C-half carries all three leg sleeves (left, right, back); a small front gate closes it.
# Hinge pin at 225 deg, wing-nut bolt through two tabs at 315 deg (both on the front, between sleeves).
# 2 mm rubber liner inside. Height 50 mm. Shown closed (left) and open (right, gate swung 100 deg).
# v2: sleeves moved outward so they sit on the OUTSIDE of the collar wall, with a 6 mm closed cap at the top
#     (the leg pushes up into the sleeve and bottoms out). The bore is cut clean afterwards, so nothing
#     reaches into the liner or the pipe. In v1 the sleeves poked through the wall into the pipe.
RP = 37.5; LIN = 2.0; WALL = 4.0; H = 50.0
RI = RP + LIN; RO = RI + WALL
LR = 8.0                      # leg radius (16 mm steel tube)
SW = 3.0                      # sleeve wall
AXIS_OUT = 9.5                # sleeve axis distance outside RO, so the sleeve just overlaps the wall
def ring_sector(r_out, r_in, a0, a1, h):
    pts_o = [(r_out * math.cos(math.radians(a)), r_out * math.sin(math.radians(a))) for a in [a0 + (a1 - a0) * i / 24 for i in range(25)]]
    pts_i = [(r_in * math.cos(math.radians(a)), r_in * math.sin(math.radians(a))) for a in [a1 - (a1 - a0) * i / 24 for i in range(25)]]
    return cq.Workplane("XY").polyline(pts_o + pts_i).close().extrude(h)
def at(a, r): return (r * math.cos(math.radians(a)), r * math.sin(math.radians(a)))
def sleeve(a, down_deg):
    x, y = at(a, RO + AXIS_OUT)
    d = cq.Vector(math.cos(math.radians(a)) * math.cos(math.radians(down_deg)),
                  math.sin(math.radians(a)) * math.cos(math.radians(down_deg)),
                  -math.sin(math.radians(down_deg)))
    p = cq.Vector(x, y, H / 2)
    outer = cq.Solid.makeCylinder(LR + SW, 66, p - d * 6, d)      # 6 mm cap above the hole
    hole = cq.Solid.makeCylinder(LR + 0.3, 64, p, d)               # open at the bottom only
    return cq.Workplane("XY").add(outer.cut(hole))
def collar(open_deg=0.0, ox=0.0):
    a_h, a_n = 225.0, 315.0
    big = ring_sector(RO, RI, a_n + 1, a_h + 360 - 1, H)
    for a, dd in ((0, 70), (180, 70), (90, 75)):
        big = big.union(sleeve(a, dd))
    hx, hy = at(a_h, RO + 4)
    big = big.union(cq.Workplane("XY").circle(5).extrude(14).translate((hx, hy, 0)))
    big = big.union(cq.Workplane("XY").circle(5).extrude(14).translate((hx, hy, H - 14)))
    nx, ny = at(a_n, RO)
    tab_dir = cq.Vector(math.cos(math.radians(a_n)), math.sin(math.radians(a_n)), 0)
    tan = cq.Vector(-tab_dir.y, tab_dir.x, 0)
    def tab(sign):
        c = cq.Vector(nx, ny, 0) + tab_dir * 9 + tan * (sign * 4)
        return cq.Workplane("XY").box(4, 18, 30).rotate((0, 0, 0), (0, 0, 1), a_n).translate((c.x, c.y, H / 2))
    big = big.union(tab(-1))
    # Clean bore: nothing may reach inside the collar's inner radius.
    bore = cq.Workplane("XY").circle(RI).extrude(400).translate((0, 0, -200))
    big = big.cut(bore)
    gate = ring_sector(RO, RI, a_h + 1, a_n - 1, H)
    gate = gate.union(cq.Workplane("XY").circle(5).extrude(H - 30).translate((hx, hy, 15)))
    gate = gate.union(tab(1))
    liner = ring_sector(RI, RP, a_n + 1, a_h + 359, H).union(ring_sector(RI, RP, a_h + 1, a_n - 1, H))
    bc = cq.Vector(nx, ny, 0) + tab_dir * 12
    bolt = cq.Workplane("XY").add(cq.Solid.makeCylinder(3, 26, cq.Vector(bc.x, bc.y, H / 2) - tan * 11, tan))
    wing = cq.Workplane("XY").add(cq.Solid.makeCylinder(6, 6, cq.Vector(bc.x, bc.y, H / 2) + tan * 7, tan))
    wing = wing.union(cq.Workplane("XY").box(4, 4, 30).translate((bc.x + tan.x * 10, bc.y + tan.y * 10, H / 2)))
    if open_deg:
        gate = gate.rotate((hx, hy, 0), (hx, hy, 1), -open_deg)
    parts = [(big, "collar_body_with_sleeves", (0.55, 0.57, 0.6, 1)), (gate, "gate", (0.4, 0.45, 0.55, 1)),
             (cq.Workplane("XY").circle(2.5).extrude(H).translate((hx, hy, 0)), "hinge_pin", (0.2, 0.2, 0.2, 1))]
    if not open_deg:
        parts += [(liner, "rubber_liner", (0.1, 0.1, 0.1, 1)), (bolt, "bolt_M6", (0.3, 0.3, 0.3, 1)), (wing, "wing_nut", (0.85, 0.65, 0.2, 1))]
    return [(p.translate((ox, 0, 0)), n, c) for p, n, c in parts]
assy = cq.Assembly()
for i, (p, n, c) in enumerate(collar(0, 0) + collar(100, 240)):
    assy.add(p, name=f"{n}_{i}", color=cq.Color(*c))
pipe = cq.Workplane("XY").circle(RP).circle(RP - 3).extrude(140).translate((0, 0, -45))
assy.add(pipe, name="growing_pipe_stub", color=cq.Color(0.95, 0.95, 0.95, 0.35))
result = assy
