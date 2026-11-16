# Drawings page export for #229: python cad/export_pipe_collar_drawings.py docs/drawings/renders
# Writes front/top/side/iso PNGs + a GLB per assembly, and a close-up of the pod seated in the collar.
import os, sys
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
# close-up: section through the hole axis, pod seated, zoomed on the collar boss
zone = cq.Workplane("XY").box(200, 200, 52, centered=(True, True, False)).translate((0, 0, -2))
keep = []
for c in pc.scene("pod").children:
    objs = c.obj.vals() if hasattr(c.obj, "vals") else [c.obj]
    col = c.color.toTuple() if c.color else (0.7, 0.7, 0.7, 1)
    for o in objs:
        o = cq.Workplane("XY").add(o).cut(cut).intersect(zone).val()   # half-section, lower zone only
        if o.isNull() or o.Volume() < 1e-6: continue
        keep.append(rl.tris(o, col))
for v, el, az in (("section", 0, 90), ("section-iso", 22, 35)):
    rl.draw(keep, el, az, os.path.join(out, "pipe-collar-pod-closeup-v1-%s.png" % v), "Pod seated in the collar (cut through the hole)")
print("wrote closeup")
