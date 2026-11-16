# Renders for pipe_collar.py and cart_pod_holder.py: python cad/render_pipe_collar.py renders/pipe_collar
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cadquery as cq
import render_local as rl
import pipe_collar as pc
import cart_pod_holder as ch

def parts_of(assy, section=None):
    out = []
    for c in assy.children:
        objs = c.obj.vals() if hasattr(c.obj, "vals") else [c.obj]
        col = c.color.toTuple() if c.color else (0.7, 0.7, 0.7, 1)
        for o in objs:
            if section is not None:
                o = cq.Workplane("XY").add(o).cut(section).val()
                if o.isNull() or o.Volume() < 1e-6:
                    continue
            t = rl.tris(o, col)
            if len(t[0]):
                out.append(t)
    return out

def one(shape_wp, color):
    return [rl.tris(v, color) for v in shape_wp.vals()]

if __name__ == "__main__":
    outdir = sys.argv[1]
    os.makedirs(outdir, exist_ok=True)
    f, b = pc.collar_halves()
    views = (("iso", 25, -50), ("front", 0, -90), ("side", 0, 0), ("top", 90, -90))
    def shoot(name, parts, vs=views[:3], title=None):
        for v, el, az in vs:
            rl.draw(parts, el, az, os.path.join(outdir, "%s-%s.png" % (name, v)), title or ("%s (%s)" % (name, v)))
        print("wrote", name)
    shoot("collar-front-half", one(f, pc.C_COLLAR), views[:3])
    shoot("collar-back-half", one(b, pc.C_BACK), views[:3])
    shoot("plug", one(pc.plug_alone(), pc.C_PLUG), views[:3])
    cv = (("iso", -25, -125), ("front", 0, -90), ("side", 0, 0))
    shoot("cart-pod-holder", one(ch.holder(), pc.C_COLLAR), views[:3])
    shoot("cart-pod-holder-on-cart", parts_of(ch.scene(False)), cv)
    shoot("cart-pod-holder-with-pod", parts_of(ch.scene(True)), cv)
    # collar on the pipe, from the hole side (azimuth 0 looks at +X face) and iso
    hv = (("iso", 22, 35), ("side", 0, 0), ("top", 90, 0))
    cut = cq.Workplane("XY").box(400, 200, 400).translate((0, 100, 46))      # removes y > 0: section through the hole axis
    for content, name in (("empty", "collar-on-pipe"), ("pod", "collar-with-pod"), ("plug", "collar-with-plug"),
                          ("parked", "collar-plug-parked")):
        a = pc.scene(content)
        shoot(name, parts_of(a), hv)
        shoot(name + "-section", parts_of(a, cut), (("iso", 22, 35), ("side", 0, 0), ("top", 90, 0)))
