# Black and white isometric LINE drawings from GLB files (OpenPocket #311). One style for every Drawings thumbnail:
# white faces, black lines where the surface folds (> 35 degrees), where two parts meet, and round the outline. Hidden lines
# are hidden (z-buffer), so it reads as a clean wireframe-style drawing, not a render.
#
# Usage:
#   python cad/render_line_thumbs.py            # every entry of docs/drawings/renders.json -> docs/drawings/renders/<id>-line.png
#   python cad/render_line_thumbs.py only-missing   # skip thumbnails that already exist
#   python cad/render_line_thumbs.py views ID...   # also -front, -top, -side for these ids
# Extra packages (not project dependencies): numpy, pillow, trimesh.
import json
import os
import sys

import numpy as np
import trimesh
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(HERE, "..", "docs", "drawings")
W, H, SS = 800, 600, 3            # output size (px, 4:3 like the cards) and supersampling
FOLD_DEG = 35.0
VIEWS = {                          # direction from the model towards the camera (glTF is Y up)
    "line": (1.0, 1.0, 1.0),       # true isometric
    "front": (0.0, 0.0, 1.0),
    "top": (0.0, 1.0, 0.0),
    "side": (1.0, 0.0, 0.0),
}


def load_tris(path):
    scene = trimesh.load(path, force="scene")
    tris, part = [], []
    for i, m in enumerate(scene.dump()):
        if not hasattr(m, "faces") or len(m.faces) == 0:
            continue
        tris.append(np.asarray(m.vertices, float)[np.asarray(m.faces)])
        part.append(np.full(len(m.faces), i, np.int32))
    return np.concatenate(tris), np.concatenate(part)


def draw(tris, part, view, out):
    d = np.array(VIEWS[view], float)
    d /= np.linalg.norm(d)
    up = np.array([0, 1.0, 0]) if abs(d[1]) < 0.99 else np.array([0, 0, -1.0])
    r = np.cross(up, d); r /= np.linalg.norm(r)
    u = np.cross(d, r)
    x, y, z = tris @ r, tris @ u, tris @ d            # larger z = nearer the camera
    x0, x1, y0, y1 = x.min(), x.max(), y.min(), y.max()
    margin = 1.12
    s = min(W * SS / max(x1 - x0, 1e-9), H * SS / max(y1 - y0, 1e-9)) / margin
    px = (x - (x0 + x1) / 2) * s + W * SS / 2
    py = H * SS / 2 - (y - (y0 + y1) / 2) * s
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    n *= np.where(n @ d >= 0, 1.0, -1.0)[:, None]      # two-sided: flip towards the camera
    w, h = W * SS, H * SS
    zb = np.full((h, w), -np.inf, np.float32)
    ib = np.full((h, w), -1, np.int32)
    for i in range(len(tris)):
        ax, ay, az = px[i], py[i], z[i]
        xa, xb = int(max(np.floor(ax.min()), 0)), int(min(np.ceil(ax.max()), w - 1))
        ya, yb = int(max(np.floor(ay.min()), 0)), int(min(np.ceil(ay.max()), h - 1))
        if xb < xa or yb < ya:
            continue
        den = (ay[1] - ay[2]) * (ax[0] - ax[2]) + (ax[2] - ax[1]) * (ay[0] - ay[2])
        if abs(den) < 1e-12:
            continue
        gx, gy = np.meshgrid(np.arange(xa, xb + 1) + 0.5, np.arange(ya, yb + 1) + 0.5)
        l0 = ((ay[1] - ay[2]) * (gx - ax[2]) + (ax[2] - ax[1]) * (gy - ay[2])) / den
        l1 = ((ay[2] - ay[0]) * (gx - ax[2]) + (ax[0] - ax[2]) * (gy - ay[2])) / den
        l2 = 1 - l0 - l1
        m = (l0 >= -1e-6) & (l1 >= -1e-6) & (l2 >= -1e-6)
        zz = l0 * az[0] + l1 * az[1] + l2 * az[2]
        sub = zb[ya:yb + 1, xa:xb + 1]
        m &= zz > sub
        sub[m] = zz[m]
        ib[ya:yb + 1, xa:xb + 1][m] = i
    # edges between neighbouring pixels (right and below)
    edge = np.zeros((h, w), bool)
    zrange = float(z.max() - z.min()) or 1.0
    cos_fold = np.cos(np.radians(FOLD_DEG))
    for sl_a, sl_b in (((slice(None), slice(0, -1)), (slice(None), slice(1, None))),
                       ((slice(0, -1), slice(None)), (slice(1, None), slice(None)))):
        ia, ibb = ib[sl_a], ib[sl_b]
        both = (ia >= 0) & (ibb >= 0)
        e = (ia >= 0) != (ibb >= 0)                                    # outline
        same = both & (ia != ibb)
        pa, pb = part[np.maximum(ia, 0)], part[np.maximum(ibb, 0)]
        e |= same & (pa != pb)                                         # two parts meet
        dots = np.einsum("ij,ij->i", n[np.maximum(ia, 0).ravel()], n[np.maximum(ibb, 0).ravel()]).reshape(ia.shape)
        e |= same & (dots < cos_fold)                                  # fold
        with np.errstate(invalid="ignore"):
            dz = np.abs(zb[sl_a] - zb[sl_b])
        e |= both & (dz > 0.02 * zrange)                               # depth jump (one thing in front of another)
        edge[sl_a] |= e
        edge[sl_b] |= e
    edge = ndimage.binary_dilation(edge, iterations=1)
    img = np.where(edge, 0.0, 1.0).reshape(H, SS, W, SS).mean(axis=(1, 3))
    Image.fromarray((img * 255).astype(np.uint8)).save(out, optimize=True)


def main():
    args = sys.argv[1:]
    skip = "only-missing" in args
    views = ("line",)
    ids = [a for a in args if a not in ("only-missing", "views")]
    if "views" in args:
        views = tuple(VIEWS)
    data = json.load(open(os.path.join(DOCS, "renders.json")))
    for r in data["renders"]:
        if ids and r["id"] not in ids:
            continue
        m = r.get("viewer", "")
        src = m.split("src=")[1].split("&")[0] if "src=" in m else None
        if not src:
            print("no GLB for", r["id"]); continue
        from urllib.parse import unquote
        glb = os.path.join(DOCS, unquote(src))
        tris = None
        for v in views:
            out = os.path.join(DOCS, "renders", "%s-%s.png" % (r["id"], v))
            if skip and os.path.exists(out):
                continue
            if tris is None:
                tris, part = load_tris(glb)
            draw(tris, part, v, out)
            print("wrote", os.path.relpath(out, DOCS), len(tris), "tris", flush=True)


if __name__ == "__main__":
    main()
