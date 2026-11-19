# Renders for cad/track_supports.py (OpenPocket #315): four views (iso, front, top, side) of the whole unit and of a close-up
# of each kind of support, plus the GLB of the assembly.
# Usage: python cad/render_track_supports.py   -> cad/renders/track-supports-*.png, track-supports-assembly.glb, assembly.glb (unit + cart)
import os, runpy, sys
import cadquery as cq
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import render_local as rl

OUT = os.path.join(HERE, "renders")
ns = runpy.run_path(os.path.join(HERE, "track_supports.py"))
assy = ns["result"]
SUP_X, ZB, ZT, LOOP_Y, ZC2 = ns["SUP_X"], ns["ZB"], ns["ZT"], ns["LOOP_Y"], ns["ZC2"]

VIEWS = (("iso", 25, -50), ("front", 0, -90), ("top", 90, -90), ("side", 0, 0))

def cropped(cx, cy, cz, hx, hy, hz):
    """Parts of the assembly inside a box (so a close-up shows only the support and what it sits on)."""
    cut = cq.Workplane("XY").box(2 * hx, 2 * hy, 2 * hz).translate((cx, cy, cz))
    parts = []
    sub = cq.Assembly()
    for ch in assy.children:
        try:
            s = ch.obj.intersect(cut)
            if not s.vals() or s.val().Volume() < 1e-3:
                continue
        except Exception:
            continue
        parts.extend(rl.tris(v, ch.color.toTuple() if ch.color else (0.7, 0.7, 0.7, 1)) for v in s.vals())
        sub.add(s, name=ch.name, color=ch.color)
    return parts, sub

def write(parts, name):
    for v, el, az in VIEWS:
        rl.draw(parts, el, az, os.path.join(OUT, f"{name}-{v}.png"), f"{name} ({v})")
    print("wrote", name)

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    write(rl.collect(assy), "track-supports-assembly")
    for name, box_ in (("track-supports-bottom", (SUP_X, LOOP_Y / 2, (ZB + 304) / 2, 110, 60, 100)),
                       ("track-supports-top", (SUP_X, LOOP_Y / 2, ZT - 40, 110, 60, 110))):
        parts, sub = cropped(*box_)
        write(parts, name)
        sub.export(os.path.join(OUT, name + ".glb"))
    assy.export(os.path.join(OUT, "track-supports-assembly.glb"))
    # assembly.glb = the unit with the track supports + the cart assembly (cup drain holes from #316), cart set beside the unit
    import cart_assembly as ca
    both = cq.Assembly()
    both.add(assy, name="unit_with_track_supports")
    both.add(ca.result, name="cart", loc=cq.Location(cq.Vector(700, 0, 0)))
    both.export(os.path.join(OUT, "assembly.glb"), tolerance=0.1, angularTolerance=0.2)
    print("wrote GLBs")
