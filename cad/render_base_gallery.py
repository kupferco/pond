# Gallery output for cad/cart_base.py: GLB for the 3D viewer plus black-and-white hidden-line outline drawings
# (iso, front = plate seen face-on, top, side) with key dimensions. Uses the render server's own project_svg,
# as cad/render_gallery.py does for cart_arm.py.
# Usage: python cad/render_base_gallery.py OUT_DIR
import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cadquery as cq
import cart_base as cb

RUNNER = os.path.join(HERE, "..", "render-server", "pond_render", "sandbox", "runner.py")
spec = importlib.util.spec_from_file_location("pond_runner", RUNNER)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

W, H = 800, 600
NAME = "cart-base-v1"
INK = "rgb(20,20,20)"

def basis(view):
    cam, up, _ = runner.VIEW_PRESETS[view]
    n = runner._normalize(cam)
    up_proj = tuple(u - runner._dot(up, n) * c for u, c in zip(up, n))
    u = runner._normalize(up_proj)
    return runner._cross(u, n), u

def dim_line(x0, y0, x1, y1, text, off=0):
    """Screen-space dimension line with end ticks and a label above its middle."""
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    horiz = abs(y1 - y0) < abs(x1 - x0)
    tick = 5
    t = ('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1"/>' % (x0, y0, x1, y1, INK))
    for (x, y) in ((x0, y0), (x1, y1)):
        if horiz:
            t += '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1"/>' % (x, y - tick, x, y + tick, INK)
        else:
            t += '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1"/>' % (x - tick, y, x + tick, y, INK)
    if horiz:
        t += ('<text x="%.1f" y="%.1f" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="12" '
              'fill="#111">%s</text>' % (mx, my - 5, text))
    else:
        t += ('<text x="%.1f" y="%.1f" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="12" '
              'fill="#111" transform="rotate(-90 %.1f %.1f)">%s</text>' % (mx - 6, my, mx - 6, my, text))
    return t

def tag(x, y, dx, dy, text):
    anchor = "end" if dx < 0 else "start"
    return ('<circle cx="%.1f" cy="%.1f" r="3.5" fill="%s"/><line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
            'stroke-width="1"/><text x="%.1f" y="%.1f" font-family="Helvetica, Arial, sans-serif" font-size="12" '
            'text-anchor="%s" fill="#111">%s</text>'
            % (x, y, INK, x, y, x + dx, y + dy, INK, x + dx + (-3 if dx < 0 else 3), y + dy + 4, anchor, text))

# Dimensions per view: ("dim", p0, p1, offset_px_perpendicular, text) in 3D points; ("tag", point, dx, dy, text)
X0, X1, ZH = cb.PLATE_X0, cb.PLATE_X1, cb.PLATE_ZH
HX = cb.HX
YF = cb.PLATE_Y0
OVERLAYS = {
    "front": [
        ("dim", (X0, YF, -ZH), (X1, YF, -ZH), 66, "plate 142 (ASSUMED)"),
        ("dim", (-HX, YF, -ZH), (HX, YF, -ZH), 88, "pipes 120 apart (ASSUMED)"),
        ("dim", (X1, YF, -ZH), (X1, YF, ZH), 40, "112"),
        ("tag", (cb.ca.hinge_x(-1), YF, 15), -50, -128, "hinge B: pad -X edge"),
        ("tag", (cb.ca.hinge_x(1), YF, 15), 50, -128, "hinge C: pad +X edge"),
        ("tag", (cb.ARM_X + 25, YF, 25), 60, -78, "arm M4 square 50 (ASSUMED)"),
        ("tag", (cb.BATT_C, YF, cb.BATT_Z), 30, 96, "battery shelf + strap slots (ASSUMED)"),
        ("tag", (cb.MOTOR_XS[-1], YF, -20), 30, 70, "motor saddles (ASSUMED)"),
        ("tag", (cb.ch.servo_x_range(-1)[0] + 6, YF, cb.ch.SERVO_Z0 + 18), -50, -20, "rotation servo B on hinge axis (ASSUMED)"),
        ("tag", (cb.ch.servo_x_range(1)[1] - 6, YF, cb.ch.SERVO_Z0 + 18), 50, -20, "rotation servo C (ASSUMED)"),
    ],
    "top": [
        ("dim", (X0, YF, 0), (X1, YF, 0), 0, "142"),
    ],
    "right": [
        ("dim", (0, YF - cb.BATT[1], -ZH), (0, YF, -ZH), 30, "battery 50 out (ASSUMED)"),
        ("dim", (0, YF, ZH), (0, cb.PLATE_Y1, ZH), -22, "plate 6"),
    ],
    "iso": [],
}

def overlay(svg, view):
    m = re.search(r"scale\(([-\d.e]+), -([-\d.e]+)\) translate\(([-\d.e]+),([-\d.e]+)\)", svg)
    s, tx, ty = float(m.group(1)), float(m.group(3)), float(m.group(4))
    r, u = basis(view)
    def scr(p):
        X, Y = sum(a * b for a, b in zip(p, r)), sum(a * b for a, b in zip(p, u))
        return s * (X + tx), -s * (Y + ty)
    out = []
    for item in OVERLAYS[view]:
        if item[0] == "dim":
            _, p0, p1, off, text = item
            (a, b), (c, d) = scr(p0), scr(p1)
            if abs(d - b) < abs(c - a):
                b += off; d += off
            else:
                a += off; c += off
            out.append(dim_line(a, b, c, d, text))
        else:
            _, p, dx, dy, text = item
            x, y = scr(p)
            out.append(tag(x, y, dx, dy, text))
    return svg.replace("</svg>", "\n".join(out) + "\n</svg>")

def main(outdir):
    os.makedirs(outdir, exist_ok=True)
    assy = cb.result
    shape = assy.toCompound()
    bb = shape.BoundingBox()
    size_txt = " x ".join("%g" % round(v, 1) for v in (bb.xlen, bb.ylen, bb.zlen))
    files = []
    for view, label in (("iso", "iso"), ("front", "plan"), ("top", "top"), ("right", "side")):
        cap = "%s  ·  %s  ·  bbox %s mm  ·  DRAFT" % (NAME, label, size_txt)
        svg = runner.project_svg(shape, view, width=W, height=H, show_hidden=False, caption=cap)
        svg = overlay(svg, view)
        path = os.path.join(outdir, "%s-%s.svg" % (NAME, label))
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(svg)
        files.append(path)
        try:
            import cairosvg
            cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=path[:-4] + ".png", output_width=W)
            files.append(path[:-4] + ".png")
        except Exception as exc:
            print("png skipped:", exc)
    glb = os.path.join(outdir, NAME + ".glb")
    assy.export(glb)
    files.append(glb)
    for f in files:
        print("wrote", f)

if __name__ == "__main__":
    main(sys.argv[1])
