# Renders for cad/spine_connector.py (OpenPocket #561): four views (iso, front, top, side) of
#   spine-connector            the bottom connector close up, in its assembly context (spine, growing pipe with its window, track pipe, pods near it)
#   spine-connector-positions  the whole spine with BOTH connectors and every pod place (red = a pod place that sits in a connector position)
# plus the GLB of each. Usage: python cad/render_spine_connector.py -> cad/renders/spine-connector*.png / .glb
import os
import sys

import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import render_local as rl
import spine_connector as sc

OUT = os.path.join(HERE, "renders")
VIEWS = (("iso", 25, -50), ("front", 0, -90), ("top", 90, -90), ("side", 0, 0))


def crop(assy, cx, cy, cz, hx, hy, hz):
    cut = cq.Workplane("XY").box(2 * hx, 2 * hy, 2 * hz).translate((cx, cy, cz))
    parts, sub = [], cq.Assembly()
    for ch in assy.children:
        try:
            s = ch.obj.intersect(cut)
            if not s.vals() or sum(v.Volume() for v in s.vals()) < 1e-3:
                continue
        except Exception:
            continue
        c = ch.color.toTuple() if ch.color else (0.7, 0.7, 0.7, 1)
        parts.extend(rl.tris(v, c) for v in s.vals())
        sub.add(s, name=ch.name, color=ch.color)
    return parts, sub


def write_views(parts, name, note):
    for v, el, az in VIEWS:
        rl.draw(parts, el, az, os.path.join(OUT, "%s-%s.png" % (name, v)), "%s (%s)" % (name, v), note)
    print("wrote", name)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    assy, bad = sc.connector_scene()
    zb, zt = sc.ZONES["bottom"], sc.ZONES["top"]
    parts, sub = crop(assy, 0, sc.LOOP_Y / 2, zb, 90, 60, 80)
    write_views(parts, "spine-connector", "bottom connector, spine z %.0f: clamp ring on the spine, arm through the pipe window, M8 rod into the track pipe. Red pod = must go" % zb)
    sub.export(os.path.join(OUT, "spine-connector.glb"), tolerance=0.3, angularTolerance=0.2)
    write_views(rl.collect(assy), "spine-connector-positions",
          "connectors on the spine at z = %.0f (bottom run) and z = %.0f (top run), x = 0. Red = pod place in a connector position" % (zb, zt))
    assy.export(os.path.join(OUT, "spine-connector-positions.glb"), tolerance=0.5, angularTolerance=0.3)
    print("wrote GLBs")
