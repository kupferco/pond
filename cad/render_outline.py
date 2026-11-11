# Gallery renderer for a CadQuery script: black-and-white outline views (the same hidden-line SVG
# projection the render server uses, render-server/pond_render/sandbox/runner.py project_svg) plus the
# coloured GLB for the 3D viewer, in the form the gallery (docs/gallery/renders.json) expects.
# Usage: python cad/render_outline.py cad/cart_sleeves.py ATTR OUT_DIR NAME [--dims]
#   ATTR  name of the cq.Assembly in the script (e.g. pair, exploded)
#   Writes OUT_DIR/NAME.glb and OUT_DIR/NAME-{iso,front,side,top}.png (1100 px wide).
#   --dims adds the key dimensions from the script's DIMS dict (front, side and top views, cart_sleeves.py).
import importlib.util, os, re, runpy, sys
import cadquery as cq

RUNNER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "render-server", "pond_render", "sandbox", "runner.py")
spec = importlib.util.spec_from_file_location("pond_runner", RUNNER)
runner = importlib.util.module_from_spec(spec); spec.loader.exec_module(runner)

W, H = 1100, 700

def dim_svg(s, ty, tx, p0, p1, label, off=(0, 0), horizontal=False):
    """Dimension line between (u,v) points p0 and p1 in view coordinates; label beside it."""
    X = lambda u: s * (u + tx)
    Y = lambda v: -s * (v + ty)
    x0, y0, x1, y1 = X(p0[0]), Y(p0[1]), X(p1[0]), Y(p1[1])
    out = ['<g stroke="#c0392b" stroke-width="1.2" fill="#c0392b" font-family="Helvetica, Arial, sans-serif" font-size="13">']
    out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/>' % (x0, y0, x1, y1))
    for (x, y) in ((x0, y0), (x1, y1)):   # end ticks
        if horizontal:
            out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/>' % (x, y - 5, x, y + 5))
        else:
            out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/>' % (x - 5, y, x + 5, y))
    tx_, ty_ = (x0 + x1) / 2 + off[0], (y0 + y1) / 2 + off[1]
    out.append('<text x="%.1f" y="%.1f" stroke="none">%s</text></g>' % (tx_ + (0 if horizontal else 6), ty_ + (-6 if horizontal else 4), label))
    return "".join(out)

def annotate(svg, view, D, hand_z):
    m = re.search(r'scale\(([\d.eE+-]+), -[\d.eE+-]+\) translate\(([\d.eE+-]+),([\d.eE+-]+)\)', svg)
    s, tx, ty = (float(g) for g in m.groups())
    items = []
    L, R, S = D["sleeve_length"], D["row_spacing"], D["hand_spacing"]
    OD, PD = D["sleeve_od"], D["pipe_od"]
    if view == "front":   # u = X, v = Z
        items += [
            dim_svg(s, ty, tx, (50, hand_z - L / 2), (50, hand_z + L / 2), "%g sleeve" % L),
            dim_svg(s, ty, tx, (50, -hand_z - R / 2), (50, -hand_z + R / 2), "%g rows" % R),
            dim_svg(s, ty, tx, (84, -S / 2), (84, S / 2), "%g hand spacing" % S),
            dim_svg(s, ty, tx, (-OD / 2, 20), (OD / 2, 20), "%g sleeve OD" % OD, horizontal=True),
            dim_svg(s, ty, tx, (-PD / 2, -10), (PD / 2, -10), "%g pipe OD" % PD, horizontal=True),
        ]
    elif view == "side":  # u = Y, v = Z
        items += [dim_svg(s, ty, tx, (-40, 0), (34, 0), "74 pad face to sleeve top", off=(0, -18), horizontal=True),
                  dim_svg(s, ty, tx, (-48, hand_z - L / 2), (-48, hand_z + L / 2), "%g sleeve" % L)]
    elif view == "top":   # u = X, v = Y (looking down the pipe)
        gn, gm = D["gap_narrow"], D["gap_mouth"]
        items += [dim_svg(s, ty, tx, (44, -gn / 2), (44, gn / 2), "%g gap" % gn),
                  dim_svg(s, ty, tx, (60, -gm / 2), (60, gm / 2), "%g funnel mouth" % gm),
                  dim_svg(s, ty, tx, (-OD / 2, -48), (OD / 2, -48), "%g sleeve OD" % OD, horizontal=True)]
    return svg.replace("</svg>", "".join(items) + "</svg>")

def main():
    script, attr, outdir, name = sys.argv[1:5]
    with_dims = "--dims" in sys.argv
    sys.path.insert(0, os.path.dirname(os.path.abspath(script)))
    ns = runpy.run_path(script)
    assy = ns[attr]
    os.makedirs(outdir, exist_ok=True)
    assy.export(os.path.join(outdir, name + ".glb"))
    print("wrote", name + ".glb")
    shape = assy.toCompound()
    bb = shape.BoundingBox()
    size = "%g x %g x %g" % (round(bb.xlen), round(bb.ylen), round(bb.zlen))
    import cairosvg
    for view in ("iso", "front", "side", "top"):
        caption = "%s  ·  %s  ·  bbox %s mm" % (view, runner.VIEW_PRESETS[runner.resolve_view(view)][2], size)
        svg = runner.project_svg(shape, runner.resolve_view(view), width=W, height=H, show_hidden=False, caption=caption)
        if with_dims and view != "iso":
            svg = annotate(svg, view, ns["DIMS"], ns["HAND_Z"])
        out = os.path.join(outdir, "%s-%s.png" % (name, view))
        cairosvg.svg2png(bytestring=svg.encode(), write_to=out, background_color="white")
        print("wrote", os.path.basename(out))

if __name__ == "__main__":
    main()
