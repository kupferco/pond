# Local preview renderer for a CadQuery script that ends in `result` (Workplane, Shape or Assembly).
# Usage: python cad/render_local.py cad/cart_assembly.py OUT_DIR NAME
# Writes OUT_DIR/NAME-iso.png, -front.png, -side.png using matplotlib (painter's algorithm).
import os, runpy, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import cadquery as cq

def tris(shape, color):
    v, t = shape.tessellate(0.4, 0.3)
    V = np.array([(p.x, p.y, p.z) for p in v])
    return V[np.array(t)], color

def collect(res):
    out = []
    if isinstance(res, cq.Assembly):
        for ch in res.children:
            loc = ch.loc
            for o in ch.obj.vals() if hasattr(ch.obj, "vals") else [ch.obj]:
                s = o.moved(loc) if loc else o
                c = ch.color.toTuple() if ch.color else (0.7, 0.7, 0.7, 1)
                out.append(tris(s, c))
    else:
        shapes = res.vals() if hasattr(res, "vals") else [res]
        out.extend(tris(s, (0.7, 0.7, 0.75, 1)) for s in shapes)
    return out

def draw(parts, elev, azim, path, title):
    # Z up. Painter's sort on view-space depth.
    az, el = np.radians(azim), np.radians(elev)
    d = np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])  # towards the camera
    light = np.array([0.4, -0.5, 0.8]); light /= np.linalg.norm(light)
    polys, cols, depth = [], [], []
    allv = np.concatenate([t.reshape(-1, 3) for t, _ in parts])
    for T, c in parts:
        n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
        n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
        shade = 0.45 + 0.55 * np.abs(n @ light)
        for tri, sh in zip(T, shade):
            polys.append(tri); depth.append(tri.mean(axis=0) @ d)
            cols.append((c[0] * sh, c[1] * sh, c[2] * sh, 1))
    order = np.argsort(depth)
    fig = plt.figure(figsize=(8, 8), dpi=110)
    ax = fig.add_subplot(111, projection="3d", computed_zorder=False)
    ax.add_collection3d(Poly3DCollection([polys[i] for i in order], facecolors=[cols[i] for i in order],
                                         edgecolors="none", linewidths=0))
    mid, half = (allv.max(0) + allv.min(0)) / 2, (allv.max(0) - allv.min(0)).max() / 2
    ax.set_xlim(mid[0] - half, mid[0] + half); ax.set_ylim(mid[1] - half, mid[1] + half)
    ax.set_zlim(mid[2] - half, mid[2] + half); ax.set_box_aspect((1, 1, 1), zoom=1.6)
    ax.view_init(elev=elev, azim=azim); ax.set_axis_off(); ax.set_proj_type("ortho")
    fig.subplots_adjust(0, 0, 1, 1); ax.set_title(title, fontsize=11, y=0.93)
    fig.savefig(path, bbox_inches="tight", facecolor="white"); plt.close(fig)

if __name__ == "__main__":
    script, outdir, name = sys.argv[1:4]
    sys.path.insert(0, os.path.dirname(os.path.abspath(script)))
    res = runpy.run_path(script)["result"]
    parts = collect(res)
    os.makedirs(outdir, exist_ok=True)
    for view, el, az in (("iso", 25, -50), ("front", 0, -90), ("side", 0, 0)):
        draw(parts, el, az, os.path.join(outdir, "%s-%s.png" % (name, view)), "%s (%s)" % (name, view))
        print("wrote", view)
