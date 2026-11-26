# OpenPocket #531: renders and GLBs of the full Pond unit (cad/pond_full_unit.py, the single shared assembly) in the upright pod-grab layout.
#   python cad/render_full_unit.py [full-unit] [bottom-section] [bottom-tray] [bottom-store]
#   pond-full-unit-{iso,front,top,side}.png + pond-full-unit.glb               the whole unit, both carts upright, the arm at the far-left back tray corner (C6) and at store landing S4
#   pond-bottom-section-{iso,front,top,side}.png + pond-bottom-section.glb     the same cut at z 750: tank, lid with its pick slots, tray, dry pod store, carts, arms, station
# The views follow cad/render_unit.py (software renderer, a few minutes each).
import os
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import render_local as rl                                  # noqa: E402
import pond_full_unit as pfu                               # noqa: E402

R = os.path.join(HERE, "renders")
VIEWS = (("iso", 25, -50), ("front", 0, -90), ("top", 90, -90), ("side", 0, 0))
JOBS = {
    "pond-full-unit": (lambda: pfu.build(), "Full Pond unit, both carts upright: arm at tray corner C6 (left), at store landing S4 (right)"),
    "pond-bottom-section": (lambda: pfu.build(crop=True), "Pond unit bottom section (cut at z 750): lid slots, tray, gravity-feed dry pod store, upright carts and arms"),
}

if __name__ == "__main__":
    want = sys.argv[1:] or list(JOBS)
    for name in want:
        fn, title = JOBS[name]
        sc = fn()
        sc.export(os.path.join(R, name + ".glb"), tolerance=0.5, angularTolerance=0.3)
        print("wrote", name + ".glb", flush=True)
        parts = rl.collect(sc)
        for v, el, az in VIEWS:
            rl.draw(parts, el, az, os.path.join(R, "%s-%s.png" % (name, v)), "%s (%s)" % (title, v))
            print("wrote", name, v, flush=True)
