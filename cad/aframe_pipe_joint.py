import cadquery as cq, math
# cad/aframe_pipe_joint.py — v1 (7 Nov 2026)
# Close-up: growing-pipe coupling where the A-frame legs pass through to the spine.
# Legs angle down-outward; short sleeves on the coupling point down along the legs, with gaskets.
FX, FZ, ZJ = 340.0, -911.0, 0.0   # leg direction (to foot on lid) from the spine meeting point
def tube(ro, ri, h, z0):
    return cq.Workplane("XY").circle(ro).circle(ri).extrude(h).translate((0, 0, z0))
def tdir(ro, ri, L, p, d):
    p = cq.Vector(*p); d = cq.Vector(*d).normalized()
    o = cq.Solid.makeCylinder(ro, L, p, d); i = cq.Solid.makeCylinder(ri, L + 2, p - d, d)
    return cq.Workplane("XY").add(o.cut(i))
def rod(r, s0, s1, u):
    p = cq.Vector(*u) * s0
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(r, s1 - s0, p, cq.Vector(*u)))
assy = cq.Assembly()
def add(o, n, c): assy.add(o, name=n, color=cq.Color(*c))
add(tube(37.5, 34.5, 200, 40), "pipe_above", (0.95, 0.95, 0.95, 0.35))
add(tube(37.5, 34.5, 200, -340), "pipe_below", (0.95, 0.95, 0.95, 0.35))
coup = tube(42.5, 37.5, 180, -140)
L = math.hypot(FX, FZ)
for sx in (-1, 1):
    u = (sx * FX / L, 0, FZ / L)
    s0 = 40.0 * L / FX
    coup = coup.union(tdir(16, 12.5, 50, (u[0] * s0, 0, u[2] * s0), u))
    coup = coup.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(12.5, 200, cq.Vector(0, 0, 0), cq.Vector(*u))))
    add(tdir(18, 12.5, 5, (u[0] * (s0 + 50), 0, u[2] * (s0 + 50)), u), f"gasket_{sx}", (0.1, 0.1, 0.1, 1))
    add(rod(12.5, 22, 420, u), f"leg_{sx}", (0.95, 0.6, 0.2, 1))
add(coup, "coupling_with_sleeves", (0.2, 0.4, 0.8, 1))
add(tube(16.85, 14.85, 580, -340), "spine_tube", (0.35, 0.35, 0.35, 1))
add(tube(24, 16.85, 30, -15), "spine_hub", (0.15, 0.15, 0.15, 1))
result = assy
