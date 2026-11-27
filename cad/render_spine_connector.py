# Renders for cad/spine_connector.py (OpenPocket #561): four views (iso, front, top, side) of
#   spine-connector            the flush track joint (track horizontal) with the M8 rod to the spine tube and the PROPOSAL nuts either side of the spine wall
#   spine-connector-positions  the spine and the track with a plain red ring marker at each connector height (no pods)
# plus the GLB of each. Usage: python cad/render_spine_connector.py -> cad/renders/spine-connector*.png / .glb
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import render_local as rl
import spine_connector as sc

OUT = os.path.join(HERE, "renders")
VIEWS = (("iso", 25, -50), ("front", 0, -90), ("top", 90, -90), ("side", 0, 0))


def write_views(parts, name, note):
    for v, el, az in VIEWS:
        rl.draw(parts, el, az, os.path.join(OUT, "%s-%s.png" % (name, v)), "%s (%s)" % (name, v), note)
    print("wrote", name)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    assy = sc.joint_assembly()
    write_views(rl.collect(assy), "spine-connector",
                "PROPOSAL (spine-end nuts): flush track joint, track pipe horizontal, M8 rod to the spine, nut each side of the spine wall")
    assy.export(os.path.join(OUT, "spine-connector.glb"), tolerance=0.3, angularTolerance=0.2)
    pos = sc.positions_scene()
    write_views(rl.collect(pos), "spine-connector-positions",
                "connector heights on the spine: z = %.0f (bottom run) and z = %.0f (top run), x = 0. Red rings are plain markers" % (sc.ZONES["bottom"], sc.ZONES["top"]))
    pos.export(os.path.join(OUT, "spine-connector-positions.glb"), tolerance=0.5, angularTolerance=0.3)
    print("wrote GLBs")
