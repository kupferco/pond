# cad/export_cart_v2_views.py: export the cart base v2 drawings as GLB files and PNG views (Viber #97 follow-up).
# Needed because the Pond Render sandbox runs only single self-contained scripts and cannot import cart_assembly.py.
# Run:  python cad/export_cart_v2_views.py   (from anywhere; writes renders/cart_v2/ at the repo root)
# Extra packages used only here (not project dependencies): cadquery, numpy, pillow.
# The PNGs come from a tiny numpy z-buffer rasteriser (flat shading, part colours), so no GL/display is needed.
# No geometry is changed or redrawn: everything comes from cart_assembly, cart_base and cart_hinge as they are.
import os
import sys
import numpy as np
import cadquery as cq
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cart_assembly as ca
import cart_base as cb
import cart_hinge as ch
from cart_dims import HX

OUT = os.path.join(HERE, "..", "renders", "cart_v2")
W, H = 1600, 1200          # PNG size (px); well over 1200 wide
SS = 2                     # supersampling factor

def parts_of(assy):
    """[(name, tri-vertices (n,3,3), rgb)] for every part of a flat cq.Assembly."""
    out = []
    for ch_ in assy.children:
        shp = ch_.obj.val() if hasattr(ch_.obj, "val") else ch_.obj
        if ch_.loc is not None:
            shp = shp.moved(ch_.loc)
        v, t = shp.tessellate(0.15, 0.3)
        if not t:
            continue
        v = np.array([(p.x, p.y, p.z) for p in v], float)
        t = np.array(t, int)
        c = ch_.color.toTuple() if ch_.color else (0.7, 0.7, 0.7, 1)
        out.append((ch_.name, v[t], np.array(c[:3])))
    return out

def render(parts, cam_dir, up, path, margin=1.08):
    """Orthographic z-buffer render looking along -cam_dir (cam_dir points from the model to the camera)."""
    d = np.array(cam_dir, float); d /= np.linalg.norm(d)
    r = np.cross(up, d); r /= np.linalg.norm(r)
    u = np.cross(d, r)
    tris = np.concatenate([p[1] for p in parts])
    cols = np.concatenate([np.tile(p[2], (len(p[1]), 1)) for p in parts])
    x = tris @ r; y = tris @ u; z = tris @ d            # larger z = nearer the camera
    x0, x1, y0, y1 = x.min(), x.max(), y.min(), y.max()
    s = min(W * SS / (x1 - x0), H * SS / (y1 - y0)) / margin
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    px = (x - cx) * s + W * SS / 2
    py = H * SS / 2 - (y - cy) * s
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    n *= np.sign(n @ d + 1e-9)[:, None]                 # two-sided: flip normals towards the camera
    light = np.array([0.35, -0.5, 0.8]); light = light[0] * r + light[1] * u + light[2] * d
    light /= np.linalg.norm(light)
    shade = 0.35 + 0.65 * np.clip(n @ light, 0, 1)
    img = np.empty((H * SS, W * SS, 3)); img[:] = 1.0
    zb = np.full((H * SS, W * SS), -np.inf)
    for i in range(len(tris)):
        ax, ay, az = px[i], py[i], z[i]
        xa, xb = int(max(np.floor(ax.min()), 0)), int(min(np.ceil(ax.max()), W * SS - 1))
        ya, yb = int(max(np.floor(ay.min()), 0)), int(min(np.ceil(ay.max()), H * SS - 1))
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
        img[ya:yb + 1, xa:xb + 1][m] = np.clip(cols[i] * shade[i], 0, 1)
    img = img.reshape(H, SS, W, SS, 3).mean(axis=(1, 3))
    Image.fromarray((img * 255).astype(np.uint8)).save(path)
    print("wrote", os.path.relpath(path), "%d tris" % len(tris))

def main():
    os.makedirs(OUT, exist_ok=True)
    ca.assy.save(os.path.join(OUT, "cart_assembly.glb"), "GLTF")
    print("wrote renders/cart_v2/cart_assembly.glb")
    cb.result.save(os.path.join(OUT, "cart_base_v2.glb"), "GLTF")
    print("wrote renders/cart_v2/cart_base_v2.glb")

    parts = parts_of(ca.assy)
    up = (0, 0, 1)
    render(parts, (1, -1.1, 0.8), up, os.path.join(OUT, "iso.png"))
    render(parts, (-1, 1.1, 0.8), up, os.path.join(OUT, "iso_back.png"))
    render(parts, (0, -1, 0), up, os.path.join(OUT, "front.png"))
    render(parts, (0, 0, 1), (0, 1, 0), os.path.join(OUT, "top.png"))

    # close-up: hand C's hinge, its sleeve, pipe and servo, plate trimmed to the hinge end
    sgn = 1
    det = cq.Assembly()
    for nm, shp, col in ch.hinge_parts(sgn):
        det.add(shp, name=nm, color=cq.Color(*col))
    det.add(ca.xshift(ca.hs.result, sgn * HX), name="sleeve", color=cq.Color(0.95, 0.75, 0.2, 1))
    det.add(ca.xshift(ca.cyl(ca.hs.R_PIPE, 120, "z", (0, 0, 0)), sgn * HX), name="pipe", color=cq.Color(0.75, 0.78, 0.8, 1))
    dparts = parts_of(det)
    render(dparts, (1, -1.1, 0.8), up, os.path.join(OUT, "hinge_closeup.png"))

if __name__ == "__main__":
    main()
