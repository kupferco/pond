# Renders cad/omni_wheel.py: STLs for printing, a GLB of the assembly, and PNG views (iso, front, top, side).
# Usage: python cad/render_omni_wheel.py   (writes cad/renders/ and cad/stl/)
import os, sys
import cadquery as cq
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import omni_wheel as w
import render_local as rl

R = os.path.join(HERE, "renders")
S = os.path.join(HERE, "stl")
os.makedirs(R, exist_ok=True)
os.makedirs(S, exist_ok=True)

def views(assy, name, title):
    parts = rl.collect(assy)
    for view, el, az in (("iso", 28, -55), ("front", 0, -90), ("top", 90, -90), ("side", 0, 0)):
        rl.draw(parts, el, az, os.path.join(R, "%s-%s.png" % (name, view)), "%s (%s)" % (title, view))

def exploded():
    A, B, Rl = w.build("oring")
    assy = cq.Assembly(name="exploded")
    assy.add(A.translate((0, 0, -22)), name="A", color=cq.Color(0.20, 0.45, 0.70))
    assy.add(B.translate((0, 0, 22)), name="B", color=cq.Color(0.30, 0.65, 0.85))
    for row in (1, 2):
        for k, (a, z, rr) in enumerate(w.place_row(Rl, row)):
            assy.add(rr.translate((0, 0, 0)), name="r%d_%d" % (row, k), color=cq.Color(0.15, 0.15, 0.15))
    return assy

if __name__ == "__main__":
    w.os.makedirs(S, exist_ok=True)
    sys.argv = [sys.argv[0], S]
    A, B, Ro = w.build("oring")
    cq.exporters.export(A, os.path.join(S, "omni_hub_A.stl"))
    cq.exporters.export(B.rotate((0, 0, 0), (1, 0, 0), 180), os.path.join(S, "omni_hub_B.stl"))
    cq.exporters.export(Ro.rotate((0, 0, 0), (0, 1, 0), 90), os.path.join(S, "omni_roller_oring.stl"))
    cq.exporters.export(w.roller("tube").rotate((0, 0, 0), (0, 1, 0), 90), os.path.join(S, "omni_roller_tube.stl"))
    print("STLs done")
    oring = w.assembly("oring")
    oring.export(os.path.join(R, "assembly.glb"))
    print("GLB done")
    views(oring, "omni-wheel-oring", "Omni wheel 38 mm, O-ring variant, on the 32 mm pipe")
    views(w.assembly("tube"), "omni-wheel-tube", "Omni wheel 38 mm, silicone tube variant")
    views(exploded(), "omni-wheel-exploded", "Hub halves and rollers, exploded")
