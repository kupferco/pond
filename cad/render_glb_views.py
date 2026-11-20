# cad/render_glb_views.py: four coloured views (iso, front, top, side) of a finished GLB, with translucent parts (tank, water) drawn see-through (OpenPocket #364).
# Used for the models that are built straight as GLBs (complete_unit.py) and to check what the site's 3D viewer will show.
# Usage: python cad/render_glb_views.py MODEL.glb OUT_PREFIX "Title" [--hide NAME,NAME] [--zmax MM]  -> OUT_PREFIX-{iso,front,top,side}.png
# The GLB is Y up (glTF); drawing is done Z up like render_local.py (x, y, z) = (gx, -gz, gy).
import os
import sys
import numpy as np
import trimesh
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import render_local as rl

VIEWS = (("iso", 28, -50), ("front", 0, -90), ("top", 90, -90), ("side", 0, 0))


def collect(glb, hide=(), zmax=None):
    sc = trimesh.load(glb, force="scene")
    out = []
    for name, geom_names in sc.graph.nodes_geometry and [(n, None) for n in sc.graph.nodes_geometry]:
        T, gname = sc.graph[name]
        g = sc.geometry[gname].copy()
        if any(h and h in (name + " " + gname) for h in hide):
            continue
        g.apply_transform(T)
        v = np.asarray(g.vertices, float)
        v = np.stack([v[:, 0], -v[:, 2], v[:, 1]], axis=1)
        f = np.asarray(g.faces)
        mat = getattr(g.visual, "material", None)
        c = getattr(mat, "baseColorFactor", None)
        col = tuple(np.asarray(c if c is not None else (180, 180, 185, 255), float)[:4] / 255.0)
        t = v[f]
        if col[3] < 1.0:
            t = rl.subdivide(t)
        if zmax is not None:                                   # close-up: only what lies below this height (Z up)
            t = t[t[:, :, 2].max(axis=1) < zmax]
            if not len(t):
                continue
        out.append((t, col))
    return out


if __name__ == "__main__":
    glb, prefix, title = sys.argv[1:4]
    hide = []
    if "--hide" in sys.argv:
        hide = sys.argv[sys.argv.index("--hide") + 1].split(",")
    zmax = float(sys.argv[sys.argv.index("--zmax") + 1]) if "--zmax" in sys.argv else None
    parts = collect(glb, hide, zmax)
    for v, el, az in VIEWS:
        rl.draw(parts, el, az, "%s-%s.png" % (prefix, v), "%s (%s)" % (title, v))
        print("wrote", prefix, v, flush=True)
