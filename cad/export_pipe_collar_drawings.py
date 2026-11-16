# Drawings page export for #229: python cad/export_pipe_collar_drawings.py docs/drawings/renders
# Writes front/top/side/iso PNGs + a GLB per assembly, and a close-up of the pod seated in the collar.
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cadquery as cq
import render_local as rl
import render_pipe_collar as rp
import pipe_collar as pc
import cart_pod_holder as ch

out = sys.argv[1]
os.makedirs(out, exist_ok=True)
V_COLLAR = (("iso", 22, 35), ("front", 0, 0), ("side", 0, 90), ("top", 90, 0))   # hole axis is +X: "front" looks at the hole
V_CART = (("iso", -25, -125), ("front", 0, -90), ("side", 0, 0), ("top", 90, -90))
cut = cq.Workplane("XY").box(400, 200, 400).translate((0, 100, 46))

def go(name, assy, views, title):
    for v, el, az in views:
        rl.draw(rp.parts_of(assy), el, az, os.path.join(out, "%s-%s.png" % (name, v)), "%s (%s)" % (title, v))
    assy.save(os.path.join(out, name + ".glb"), "GLTF")
    print("wrote", name)

go("pipe-collar-with-pod-v1", pc.scene("pod"), V_COLLAR, "Collar on the central pipe, pod seated")
go("pipe-collar-with-plug-v1", pc.scene("plug"), V_COLLAR, "Collar, plug in the hole")
go("pipe-collar-plug-parked-v1", pc.scene("parked"), V_COLLAR, "Collar, plug parked in its holder")
go("cart-pod-holder-v1", ch.scene(True), V_CART, "Cart pod holder with pod, on the cart plate")
# close-up: section through the hole axis, pod seated at 45 degrees, spine tube and the water film on the inner wall
zone = cq.Workplane("XY").box(200, 200, 120, centered=(True, True, False)).translate((0, 0, 10))
def section_parts(assy):
    keep = []
    for c in assy.children:
        objs = c.obj.vals() if hasattr(c.obj, "vals") else [c.obj]
        col = c.color.toTuple() if c.color else (0.7, 0.7, 0.7, 1)
        for o in objs:
            o = cq.Workplane("XY").add(o).cut(cut).intersect(zone).val()   # half-section: y > 0 removed
            if o.isNull() or o.Volume() < 1e-6: continue
            keep.append(rl.tris(o, col))
    return keep
k = pc.checks()
title = ("Pod at 45 deg, section through the hole. Gap to spine %.1f mm, tip %.1f mm inside the wall" % (k["spine_gap_mm"], k["tip_below_wall_at_edge_mm"]))
keep = section_parts(pc.scene("pod", spine=True))
for v, el, az in (("section", 0, 90), ("section-iso", 22, 35)):
    rl.draw(keep, el, az, os.path.join(out, "pipe-collar-pod-closeup-v1-%s.png" % v), title)
# plan section at the height of the pod's inner end: pipe wall, spine, water film (blue), the pod tip poking into the film
zt = pc.ZH + (pc.U_CAP - pc.POD_BODY_L) * math.sin(math.radians(pc.TILT))
slab = cq.Workplane("XY").box(200, 200, 3, centered=(True, True, False)).translate((0, 0, zt - 1.5))
plan = []
for c in pc.scene("pod", spine=True, water=True, with_pipe=True).children:
    objs = c.obj.vals() if hasattr(c.obj, "vals") else [c.obj]
    col = c.color.toTuple() if c.color else (0.7, 0.7, 0.7, 1)
    col = (col[0], col[1], col[2], 1)
    for o in objs:
        o = cq.Workplane("XY").add(o).intersect(slab).val()
        if o.isNull() or o.Volume() < 1e-6: continue
        plan.append(rl.tris(o, col))
rl.draw(plan, 90, 0, os.path.join(out, "pipe-collar-pod-closeup-v1-plan.png"),
        "Plan section at the pod's inner end (z %.0f): water film blue, spine tube, pod tip %.1f mm inside the wall" % (zt, k["tip_below_wall_at_edge_mm"]))
print("wrote closeup")
# magnet closure: horizontal section through the first magnet pair (z = 38), seen from above, plus a 3D cut-away
zc = cq.Workplane("XY").box(200, 200, 12, centered=(True, True, False)).translate((0, 0, pc.MAG_ZS[0] - 12))
mk = []
for c in pc.scene("empty", with_pipe=False).children:
    objs = c.obj.vals() if hasattr(c.obj, "vals") else [c.obj]
    col = c.color.toTuple() if c.color else (0.7, 0.7, 0.7, 1)
    for o in objs:
        o = cq.Workplane("XY").add(o).intersect(zc).val()
        if o.isNull() or o.Volume() < 1e-6: continue
        mk.append(rl.tris(o, col))
for v, el, az in (("top", 90, 0), ("iso", 35, 60)):
    rl.draw(mk, el, az, os.path.join(out, "pipe-collar-magnet-closure-v1-%s.png" % v), "Magnet closure: section through a magnet pair (red N, blue S)")
print("wrote magnets")
