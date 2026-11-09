import cadquery as cq, math
# cad/clamp_collar.py — v3 (9 Nov 2026)
# Hinged clamp collar for the bracing legs. Clamps OUTSIDE the 75 mm growing pipe: no holes in the PVC.
# Big C-half carries all three leg sleeves (left, right, back); a small front gate closes it.
# Hinge pin at 225 deg, wing-nut bolt through two tabs at 315 deg. 2 mm rubber liner. Height 50 mm.
# Shown closed (left) and open (right, gate swung 100 deg).
# v2: sleeves moved outside the wall; bore cut clean so nothing reaches the pipe.
# v3: (1) clamp tabs grow straight out of the collar wall (in v2 they floated ~7 mm off it),
#         one on each side of the split, with a bolt hole and a 4 mm clamping gap between them.
#     (2) sleeves are angle-cut along the collar: each runs the full collar height and is trimmed
#         by the top face and the bore, so it is bonded along its whole length, not at one small patch.
#         The leg hole starts at mid-height and stays outside the wall, so the leg never touches the pipe.
#     Ring sectors are now true arcs (annulus x wedge), not faceted polylines, for robust booleans.
RP = 37.5; LIN = 2.0; WALL = 4.0; H = 50.0
RI = RP + LIN; RO = RI + WALL
LR = 8.0
SW = 3.0
AXIS_OUT = 8.0
def at(a, r): return (r * math.cos(math.radians(a)), r * math.sin(math.radians(a)))
def ring_sector(r_out, r_in, a0, a1, h):
    ann = cq.Workplane("XY").circle(r_out).circle(r_in).extrude(h)
    n = 12
    pts = [(0.0, 0.0)] + [at(a0 + (a1 - a0) * i / n, r_out * 2.5) for i in range(n + 1)]
    wedge = cq.Workplane("XY").polyline(pts).close().extrude(h + 2).translate((0, 0, -1))
    return ann.intersect(wedge)
def sleeve(a, down_deg):
    x, y = at(a, RO + AXIS_OUT)
    s, c = math.sin(math.radians(down_deg)), math.cos(math.radians(down_deg))
    d = cq.Vector(math.cos(math.radians(a)) * c, math.sin(math.radians(a)) * c, -s)
    p = cq.Vector(x, y, H / 2)
    k = (H / 2 + LR + SW + 2) / s
    outer = cq.Workplane("XY").add(cq.Solid.makeCylinder(LR + SW, k + 60, p - d * k, d))
    hole = cq.Workplane("XY").add(cq.Solid.makeCylinder(LR + 0.3, 64, p, d))
    return outer, hole
def collar(open_deg=0.0, ox=0.0):
    a_h, a_n = 225.0, 315.0
    big = ring_sector(RO, RI, a_n + 1, a_h + 360 - 1, H)
    holes = []
    for a, dd in ((0, 70), (180, 70), (90, 75)):
        o, h = sleeve(a, dd)
        big = big.union(o); holes.append(h)
    big = big.intersect(cq.Workplane("XY").box(600, 600, 400).translate((0, 0, H - 200)))
    for h in holes:
        big = big.cut(h)
    hx, hy = at(a_h, RO + 4)
    big = big.union(cq.Workplane("XY").circle(5).extrude(14).translate((hx, hy, 0)))
    big = big.union(cq.Workplane("XY").circle(5).extrude(14).translate((hx, hy, H - 14)))
    tab_dir = cq.Vector(math.cos(math.radians(a_n)), math.sin(math.radians(a_n)), 0)
    tan = cq.Vector(-tab_dir.y, tab_dir.x, 0)
    nx, ny = at(a_n, RO)
    def tab(sign):
        cen = cq.Vector(nx, ny, 0) + tab_dir * 6 + tan * (sign * 4)
        return cq.Workplane("XY").box(14, 4, 30).rotate((0, 0, 0), (0, 0, 1), a_n).translate((cen.x, cen.y, H / 2))
    bc = cq.Vector(nx, ny, 0) + tab_dir * 8
    bolt_hole = cq.Workplane("XY").add(cq.Solid.makeCylinder(3.2, 40, cq.Vector(bc.x, bc.y, H / 2) - tan * 20, tan))
    big = big.union(tab(+1)).cut(bolt_hole)
    bore = cq.Workplane("XY").circle(RI).extrude(H + 40).translate((0, 0, -20))
    big = big.cut(bore)
    gate = ring_sector(RO, RI, a_h + 1, a_n - 1, H)
    gate = gate.union(cq.Workplane("XY").circle(5).extrude(H - 30).translate((hx, hy, 15)))
    gate = gate.union(tab(-1)).cut(bolt_hole).cut(bore)
    liner = cq.Workplane("XY").circle(RI).circle(RP).extrude(H)
    bolt = cq.Workplane("XY").add(cq.Solid.makeCylinder(3, 26, cq.Vector(bc.x, bc.y, H / 2) - tan * 12, tan))
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
