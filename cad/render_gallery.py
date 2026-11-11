# Gallery output for cad/cart_arm.py, in the same form as the render server's render_cad output:
# a GLB model for the 3D viewer plus black-and-white hidden-line outline drawings (SVG, and PNG when cairosvg
# is installed). The outline code is the render server's own project_svg (render-server/pond_render/sandbox/
# runner.py), loaded from the repo so the style is identical; joint letters and target tags are added on top.
# Usage: python cad/render_gallery.py OUT_DIR [arm|assembly|all]   (default: arm)
import importlib.util
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cadquery as cq
import cart_arm as arm
import cart_assembly as cart

RUNNER = os.path.join(HERE, "..", "render-server", "pond_render", "sandbox", "runner.py")
spec = importlib.util.spec_from_file_location("pond_runner", RUNNER)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

W, H = 800, 600

def basis(view):
    cam, up, _ = runner.VIEW_PRESETS[view]
    n = runner._normalize(cam)
    up_proj = tuple(u - runner._dot(up, n) * c for u, c in zip(up, n))
    u = runner._normalize(up_proj)
    r = runner._cross(u, n)
    return r, u

def overlay(svg, view, labels):
    """Add (text, 3D point, dx, dy, kind) labels. Uses the drawing's own scale/translate."""
    m = re.search(r"scale\(([-\d.e]+), -([-\d.e]+)\) translate\(([-\d.e]+),([-\d.e]+)\)", svg)
    s, tx, ty = float(m.group(1)), float(m.group(3)), float(m.group(4))
    r, u = basis(view)
    out = []
    for text, p, dx, dy, kind in labels:
        X, Y = sum(a * b for a, b in zip(p, r)), sum(a * b for a, b in zip(p, u))
        x, y = s * (X + tx), -s * (Y + ty)
        if kind == "joint":
            out.append('<circle cx="%.1f" cy="%.1f" r="10" fill="white" stroke="rgb(20,20,20)" stroke-width="1.5"/>'
                       '<text x="%.1f" y="%.1f" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" '
                       'font-size="13" font-weight="bold" fill="#111">%s</text>' % (x + dx, y + dy, x + dx, y + dy + 4.5, text))
            out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="rgb(20,20,20)" stroke-width="1"/>'
                       % (x, y, x + dx, y + dy))
        else:
            out.append('<circle cx="%.1f" cy="%.1f" r="4" fill="rgb(20,20,20)"/>'
                       '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="rgb(20,20,20)" stroke-width="1"/>'
                       '<text x="%.1f" y="%.1f" font-family="Helvetica, Arial, sans-serif" font-size="12" '
                       'text-anchor="%s" fill="#111">%s</text>'
                       % (x, y, x, y, x + dx, y + dy, x + dx + (-3 if dx < 0 else 3), y + dy + 4,
                          "end" if dx < 0 else "start", text))
    return svg.replace("</svg>", "\n".join(out) + "\n</svg>")

def draw(assy, info, name, outdir, labels_for_view):
    shape = arm.outline_parts(assy).toCompound()
    bb = shape.BoundingBox()
    size_txt = " x ".join("%g" % round(v, 1) for v in (bb.xlen, bb.ylen, bb.zlen))
    files = []
    for view in ("iso", "right", "top"):
        cap = "%s  ·  %s  ·  bbox %s mm  ·  DRAFT" % (name, {"right": "side"}.get(view, view), size_txt)
        svg = runner.project_svg(shape, view, width=W, height=H, show_hidden=False, caption=cap)
        svg = overlay(svg, view, labels_for_view(view, info))
        label = {"iso": "iso", "right": "side", "top": "top"}[view]
        path = os.path.join(outdir, "%s-%s.svg" % (name, label))
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(svg)
        files.append(path)
        try:
            import cairosvg
            cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=path[:-4] + ".png", output_width=W)
            files.append(path[:-4] + ".png")
        except Exception as exc:
            print("png skipped:", exc)
    glb = os.path.join(outdir, name + ".glb")
    assy.export(glb)
    files.append(glb)
    return files

# label offsets per view (screen pixels): joints fan out so letters do not sit on each other
OFFS = {"iso": {"A": (-34, 18), "B": (-38, -14), "C": (26, -34), "D": (34, -14), "E": (34, 16), "F": (-8, 36)},
        "right": {"A": (-34, 20), "B": (-36, -16), "C": (30, -30), "D": (34, -4), "E": (34, 22), "F": (-6, 36)},
        "top": {"A": (-30, 20), "B": (-34, -14), "C": (28, -30), "D": (34, -4), "E": (34, 22), "F": (-6, 34)}}

TAGS = {"iso": {"D1": (50, 62), "A2": (-110, 40)}, "right": {"D1": (40, 50), "A2": (-70, 56)},
        "top": {"D1": (90, 46), "A2": (-100, -34)}}
STOW_OFFS = {"iso": {"A": (34, 24), "B": (-30, 26), "C": (34, -10), "D": (-38, -24), "E": (-44, 10), "F": (-34, -14)},
             "right": {"A": (-34, 20), "B": (-36, -22), "C": (34, -12), "D": (38, -22), "E": (40, 22), "F": (-34, -24)},
             "top": {"A": (40, -10), "B": (30, -26), "C": (-34, -26), "D": (40, -24), "E": (44, 8), "F": (-34, -26)}}

def working_labels(view, info):
    lab = []
    for k, p in info["joints"].items():
        dx, dy = OFFS[view][k]
        lab.append((k, p, dx, dy, "joint"))
    lab.append(("D1 pick hole", arm.D1_C, *TAGS[view]["D1"], "tag"))
    lab.append(("A2 tray cell", arm.CELL_C, *TAGS[view]["A2"], "tag"))
    return lab

def stowed_labels(view, info):
    return [(k, p, *STOW_OFFS[view][k], "joint") for k, p in info["joints"].items()]

if __name__ == "__main__":
    outdir = sys.argv[1]
    which = sys.argv[2] if len(sys.argv) > 2 else "arm"
    os.makedirs(outdir, exist_ok=True)
    out = []
    if which in ("arm", "all"):
        out += draw(arm.result, arm.INFO, "cart-arm-v2", outdir, working_labels)
        out += draw(arm.result_stowed, arm.INFO_STOWED, "cart-arm-stowed-v2", outdir, stowed_labels)
    if which in ("assembly", "all"):
        out += draw(cart.result, None, "cart-assembly-v3", outdir, lambda view, info: [])
    for f in out:
        print("wrote", f)
