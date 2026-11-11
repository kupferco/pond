# Renders cad/cart_wheel_pairs.py for the gallery, in the same style as the render server's other drawings:
# a GLB (for the 3D viewer) and black-and-white hidden-line outline PNGs (iso, side, section) with key dimensions.
# Usage: python cad/render_cart_wheel_pairs.py OUT_DIR
# Needs cadquery and cairosvg (install into a venv outside the repo). The outline code is the render server's own
# project_svg (render-server/pond_render/sandbox/runner.py), so the look matches the other gallery entries.
import importlib.util
import math
import os
import re
import sys
import cadquery as cq
import cairosvg

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cart_wheel_pairs as cw
hs = cw.hs

spec = importlib.util.spec_from_file_location(
    "pond_runner", os.path.join(HERE, "..", "render-server", "pond_render", "sandbox", "runner.py"))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

W, H = 1000, 760

def basis(view):
    cam, up, _ = runner.VIEW_PRESETS[view]
    n = runner._normalize(cam)
    upp = tuple(u - runner._dot(up, n) * c for u, c in zip(up, n))
    if math.sqrt(runner._dot(upp, upp)) < 1e-9:
        upp = (0, 1, 0)
    u = runner._normalize(upp)
    r = runner._cross(u, n)
    return r, u

def outline(shape, view, name, outdir, dims, caption, notes=()):
    svg = runner.project_svg(shape, view, width=W, height=H, show_hidden=False, caption=caption)
    m = re.search(r"scale\(([-\d.e]+), -?([-\d.e]+)\) translate\(([-\d.e]+),([-\d.e]+)\)", svg)
    s, tx, ty = float(m.group(1)), float(m.group(3)), float(m.group(4))
    r, u = basis(view)
    def scr(p):
        return (s * (sum(a * b for a, b in zip(p, r)) + tx), -s * (sum(a * b for a, b in zip(p, u)) + ty))
    g = ['<g font-family="Helvetica, Arial, sans-serif" font-size="14" fill="#b00020" stroke="#b00020" stroke-width="1.2">']
    for p1, p2, label, off in dims:
        a, b = scr(p1), scr(p2)
        a2, b2 = (a[0] + off[0], a[1] + off[1]), (b[0] + off[0], b[1] + off[1])
        g.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke-width="0.6"/>' % (a[0], a[1], a2[0], a2[1]))
        g.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke-width="0.6"/>' % (b[0], b[1], b2[0], b2[1]))
        g.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/>' % (a2[0], a2[1], b2[0], b2[1]))
        for q, d in ((a2, 1), (b2, -1)):
            dx, dy = b2[0] - a2[0], b2[1] - a2[1]
            L = math.hypot(dx, dy) or 1
            dx, dy = dx / L * d, dy / L * d
            g.append('<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f" stroke="none"/>' % (
                q[0], q[1], q[0] + 9 * dx - 3 * dy, q[1] + 9 * dy + 3 * dx, q[0] + 9 * dx + 3 * dy, q[1] + 9 * dy - 3 * dx))
        mx, my = (a2[0] + b2[0]) / 2, (a2[1] + b2[1]) / 2
        g.append('<text x="%.1f" y="%.1f" stroke="none" text-anchor="middle" paint-order="stroke">%s</text>' % (mx, my - 5, label))
    for p, text, anchor in notes:
        q = scr(p)
        for i, line in enumerate(text.split("\n")):
            g.append('<text x="%.1f" y="%.1f" stroke="none" text-anchor="%s">%s</text>' % (q[0], q[1] + 17 * i, anchor, line))
    g.append("</g>")
    svg = svg.replace("</svg>", "".join(g) + "\n</svg>")
    cairosvg.svg2png(bytestring=svg.encode(), write_to=os.path.join(outdir, name), output_width=W)
    print("wrote", name)

def compound(assy, skip=()):
    shapes = []
    for ch in assy.children:
        if ch.name in skip:
            continue
        for o in ch.obj.vals() if hasattr(ch.obj, "vals") else [ch.obj]:
            shapes.append(o.moved(ch.loc) if ch.loc else o)
    return cq.Compound.makeCompound(shapes)

def clip(shape, axis, value, keep_below=True):
    big = 1000.0
    c = [0, 0, 0]
    c[axis] = value + (-big / 2 if keep_below else big / 2)
    sz = [big, big, big]
    return shape.intersect(cq.Workplane("XY").box(*sz).translate(c).val())

def main(outdir):
    os.makedirs(outdir, exist_ok=True)
    pn = "cart-wheel-pairs-v1"
    cn = "cart-wheel-corner-v1"
    cw.assy.export(os.path.join(outdir, pn + ".glb"))
    cw.corner.export(os.path.join(outdir, cn + ".glb"))
    print("wrote GLBs")

    det = compound(cw.assy)
    R = cw.AXLE_R
    # ---- detail: iso with the key dimensions along the pipe ----
    z0, z1 = cw.ROW_Z, -cw.ROW_Z
    outline(det, "iso", pn + "-iso.png", outdir, [
        ((0, 0, z1), (0, 0, z0), "60 row spacing", (-150, 0)),
    ], "Wheel pairs on the 32 mm pipe: driven pair (-X, worm drive) and two spring idler pairs. DRAFT")
    # ---- detail: side (looking along -X, front of the pair) ----
    outline(det, "front", pn + "-side.png", outdir, [
        ((-R - 10, 0, z1), (-R - 10, 0, z0), "60 between wheel rows", (-110, 0)),
        ((-R - 10, 0, z0 - 10), (-R - 10, 0, z0 + 10), "20 wheel dia", (-50, 0)),
        ((-cw.R_PIPE, 0, -105), (cw.R_PIPE, 0, -105), "32 pipe", (0, 0)),
        ((-cw.WORM_X - cw.MOTOR_R, 0, cw.SLEEVE_HL + 8), (-cw.WORM_X - cw.MOTOR_R, 0, cw.SLEEVE_HL + 8 + cw.MOTOR_L), "55 motor", (-40, 0)),
    ], "Front view (X right, Z up). Driven pair left with worm shaft and motor; idler pairs and springs right. DRAFT")
    # ---- detail: section across a wheel row (z = +30), sleeve and worm groove included ----
    sleeve = hs.result.translate((0, 0, 0))
    groove = cw.cyl(5.0, 120, "z", (-cw.WORM_X, -cw.GEAR_Y, 0))
    sleeve = sleeve.cut(groove)
    pieces = compound(cw.assy).fuse(sleeve.val()) if False else cq.Compound.makeCompound(list(det.Solids()) + list(sleeve.vals()))
    sec = clip(pieces, 2, cw.ROW_Z, keep_below=True)
    outline(sec, "top", pn + "-section.png", outdir, [
        ((-R, 0, cw.ROW_Z), (0, 0, cw.ROW_Z), "R26 wheel centre", (0, 150)),
        ((-cw.R_PIPE, 0, cw.ROW_Z), (cw.R_PIPE, 0, cw.ROW_Z), "32 pipe", (0, -120)),
        ((-hs.WALL_OUT_R, 0, cw.ROW_Z), (hs.WALL_OUT_R, 0, cw.ROW_Z), "68 sleeve", (0, 195)),
    ], "Section across one wheel row, looking down the pipe (hand_sleeve.py sleeve with worm groove). DRAFT")

    # ---- corner ----
    cor = compound(cw.corner)
    outline(cor, "iso", cn + "-iso.png", outdir, [], "Hand on a 150 mm radius loop corner: sleeve, driven pair and idler pairs. DRAFT")
    cut = clip(cor, 1, 0.0, keep_below=False)    # keep y >= 0, looked at from -Y: section through the bend plane
    mid = (cw.CORNER_R * (1 - math.cos(math.radians(45))) - 95, 0, cw.CORNER_R * math.sin(math.radians(45)) + 60)
    outline(cut, "front", cn + "-section.png", outdir, [], "Section through the bend plane: 150 mm centreline radius, 90 mm sleeve. DRAFT", notes=[
        ((cw.CORNER_R + 20, 0, 40), "Bore gap to pipe (4 mm when straight):\n+1.4 mm mid sleeve, +3.5 mm at the wheel rows,\n-0.3 mm at the sleeve ends (touches).\nIdler pairs shift %.1f of 2.5 mm travel." % abs(cw.IDLER_SHIFT), "start")])

if __name__ == "__main__":
    main(sys.argv[1])
