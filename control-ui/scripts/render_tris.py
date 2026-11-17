# Software renderer for the Transplant scene pictures (no GPU here): draws the triangle lists written by export-transplant.ts
# with an orthographic camera and a painter's algorithm (matplotlib), and makes the PNG views and the step clips (GIF).
# Usage: python3 scripts/render_tris.py TRI_DIR OUT_DIR
import json
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from PIL import Image

LIGHT = np.array([0.35, -0.5, 0.8]); LIGHT /= np.linalg.norm(LIGHT)
VIEWS = {  # name: (azimuth, elevation) of the camera, degrees; z is up
    "iso": (-55.0, 28.0),
    "front": (-90.0, 0.0),     # from -y: x to the right, z up: the plane the arm works in
    "side": (0.0, 0.0),        # from +x (from the track towards the pipe): y to the right
    "top": (-90.0, 90.0),      # from above: x to the right, y up
    "hole": (-132.0, 12.0),    # from the way the collar's hole faces (azimuth -132 deg round the pipe, layout.ts PSI): the seat, the hole and the plug holder face the camera
}
FLOOR = (-0.7, 0.8, -0.6, 0.6)


def basis(az, el):
    a, e = np.radians(az), np.radians(el)
    f = -np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])
    up0 = np.array([0.0, 1.0, 0.0]) if abs(f[2]) > 0.99 else np.array([0.0, 0.0, 1.0])
    right = np.cross(f, up0); right /= np.linalg.norm(right)
    up = np.cross(right, f)
    return f, right, up


def draw(tris, view, box, path, px=1100, floor=True):
    """box = (cx, cy, cz, half_w, half_h): the world point the camera looks at and the half size of the picture."""
    arr = np.asarray(tris, dtype=float).reshape(-1, 13)
    P = arr[:, :9].reshape(-1, 3, 3)
    rgb0 = arr[:, 9:12]; alpha = arr[:, 12]
    az, el = VIEWS[view]
    f, right, up = basis(az, el)
    cx, cy, cz, hw, hh = box
    c = np.array([cx, cy, cz])
    n = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
    n = n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    n = np.where((n @ f)[:, None] > 0, -n, n)
    shade = 0.5 + 0.5 * np.clip(n @ LIGHT, 0, 1)
    rgb = np.clip(rgb0 * shade[:, None], 0, 1)
    X = (P - c) @ right; Y = (P - c) @ up; D = (P - c) @ f
    order = np.argsort(-D.mean(axis=1))          # far first
    polys = np.stack([X, Y], axis=-1)[order]
    fc = np.concatenate([rgb[order], alpha[order][:, None]], axis=1)
    fig = plt.figure(figsize=(px / 100, px / 100 * hh / hw), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(-hw, hw); ax.set_ylim(-hh, hh); ax.axis("off")
    fig.patch.set_facecolor("#f6f9fc")
    if floor and abs(f[2]) > 0.01:
        x0, x1, y0, y1 = FLOOR
        q = np.array([[x0, y0, 0], [x1, y0, 0], [x1, y1, 0], [x0, y1, 0]], dtype=float)
        ax.add_collection(PolyCollection([np.stack([(q - c) @ right, (q - c) @ up], axis=-1)], facecolors=[(0.86, 0.9, 0.94, 1)], edgecolors="none"))
    ax.add_collection(PolyCollection(polys, facecolors=fc, edgecolors=fc, linewidths=0.3))
    fig.savefig(path, dpi=100, facecolor=fig.get_facecolor())
    plt.close(fig)


# framing: (centre x, y, z, half width, half height) per view. The unit stands at the origin: pipe and spine on the z axis, the track loop in the plane x = 0.06 (the cart rides the leg at y = -0.29) (in front of the pipe), the tank 0.4 (x) by 0.7 (y).
FULL = {"iso": (0.0, 0.1, 0.98, 1.2, 1.2), "front": (0.0, 0.0, 0.98, 0.75, 1.05), "side": (0.0, 0.0, 0.98, 0.6, 1.05), "top": (0.0, 0.0, 0.0, 0.5, 0.5)}
HOLE = (-0.04, -0.12, 0.88, 0.34, 0.27)   # round the collar, the cart's hand on the track, the pod holder and the arm, steps 3 and 4
COLLAR = (-0.03, -0.04, 0.82, 0.11, 0.09)   # right on the collar: seat, hole, plug holder
TRAY = (-0.1, -0.2, 0.45, 0.4, 0.33)   # front view round the seedling tray on the tank, the arm and the pod holder, step 1


def main():
    src, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    stages = json.load(open(os.path.join(src, "stages.json")))["stages"]
    names = {"step0": "start", "step1": "step1-pick", "step2": "step2-drive", "step3": "step3-plug", "step4": "step4-seat"}
    for st in stages:
        tris = json.load(open(os.path.join(src, st["id"] + ".json")))
        base = "transplant-seedling-" + names[st["id"]] + "-v6"
        for v, box in FULL.items():
            draw(tris, v, box, os.path.join(out, f"{base}-{v}.png"))
        close = TRAY if st["id"] in ("step0", "step1") else HOLE
        draw(tris, "front" if st["id"] in ("step0", "step1") else "hole", close, os.path.join(out, f"{base}-closeup.png"))
        if st["id"] in ("step2", "step3", "step4"):
            draw(tris, "hole", COLLAR, os.path.join(out, f"{base}-collar.png"), px=900)
    # clips: one GIF per step from the frames of the run (front view, framed on where the action is)
    for i, view, box in ((1, "front", TRAY), (2, "side", (0.0, 0.0, 0.95, 0.5, 0.75)), (3, "hole", HOLE), (4, "hole", HOLE)):
        frames = json.load(open(os.path.join(src, f"step{i}-frames.json")))
        imgs = []
        for k, tris in enumerate(frames):
            p = os.path.join(out, f"_f{i}_{k}.png")
            draw(tris, view, box, p, px=640)
            imgs.append(Image.open(p).convert("P", palette=Image.ADAPTIVE, colors=64))
        imgs[0].save(os.path.join(out, f"transplant-seedling-{names['step' + str(i)]}-v6-clip.gif"), save_all=True, append_images=imgs[1:], duration=250, loop=0, optimize=True)
        for k in range(len(frames)):
            os.remove(os.path.join(out, f"_f{i}_{k}.png"))


if __name__ == "__main__":
    main()
