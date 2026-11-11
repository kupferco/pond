# Gallery drawings for a CadQuery script that ends in `result`: the same black-and-white hidden-line
# outline the render server makes (render-server/pond_render/sandbox/runner.py project_svg), plus the
# GLB for the 3D viewer. Top and side views get dimension lines.
# Usage: python cad/render_outline.py cad/cart_base.py OUT_DIR NAME
# Writes OUT_DIR/NAME-iso.png (gallery thumbnail), NAME-plan.png (the 'top' view, plate seen square-on), NAME-side.png, NAME.glb.
# Dimensions are given in DIMS below as (view, label, kind, a, b, offset) in model mm.
import importlib.util, os, runpy, sys
import cairosvg
import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("runner", os.path.join(HERE, "..", "render-server", "pond_render", "sandbox", "runner.py"))
runner = importlib.util.module_from_spec(spec); spec.loader.exec_module(runner)

W, H = 1000, 750
PAD = 110          # canvas padding for dimension lines

def dim_svg(inner, shape, view, dims):
    """Wrap a project_svg drawing in a larger canvas and add dimension lines (plan = looking at the plate from -Y: X right, Z up; side = looking along -X: Y right, Z up)."""
    bb = shape.BoundingBox()
    lo = {"plan": (bb.xmin, bb.zmin), "side": (bb.ymin, bb.zmin)}[view]
    hi = {"plan": (bb.xmax, bb.zmax), "side": (bb.ymax, bb.zmax)}[view]
    xlen, ylen = hi[0] - lo[0], hi[1] - lo[1]
    s = min(W * 0.84 / xlen, H * 0.84 / ylen)          # same fit as project_svg (8 % margin)
    ox, oy = PAD, PAD
    def sx(u): return ox + (W - xlen * s) / 2 + (u - lo[0]) * s
    def sy(v): return oy + (H - ylen * s) / 2 + (hi[1] - v) * s
    out = []
    for label, kind, a, b, off in dims:
        if kind == "h":      # horizontal dimension from u=a to u=b, line at v=off
            y = sy(off)
            x1, x2 = sx(a), sx(b)
            out.append(f'<line x1="{x1}" y1="{y-6}" x2="{x1}" y2="{y+6}"/><line x1="{x2}" y1="{y-6}" x2="{x2}" y2="{y+6}"/>'
                       f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" marker-start="url(#a)" marker-end="url(#a)"/>'
                       f'<text x="{(x1+x2)/2}" y="{y-8}" text-anchor="middle">{label}</text>')
        else:                # vertical dimension from v=a to v=b, line at u=off
            x = sx(off)
            y1, y2 = sy(a), sy(b)
            out.append(f'<line x1="{x-6}" y1="{y1}" x2="{x+6}" y2="{y1}"/><line x1="{x-6}" y1="{y2}" x2="{x+6}" y2="{y2}"/>'
                       f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2}" marker-start="url(#a)" marker-end="url(#a)"/>'
                       f'<text x="{x-8}" y="{(y1+y2)/2}" text-anchor="end" transform="rotate(-90 {x-8} {(y1+y2)/2})" dy="-2">{label}</text>')
    inner_body = inner[inner.index(">") + 1: inner.rindex("</svg>")]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W+2*PAD}" height="{H+2*PAD+28}" viewBox="0 0 {W+2*PAD} {H+2*PAD+28}">'
            f'<rect width="100%" height="100%" fill="white"/>'
            f'<svg x="{ox}" y="{oy}" width="{W}" height="{H+28}" viewBox="0 0 {W} {H+28}">{inner_body}</svg>'
            f'<defs><marker id="a" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto-start-reverse"><path d="M0,4 L8,1 L8,7 z" fill="#b00020"/></marker></defs>'
            f'<g stroke="#b00020" stroke-width="1.2" fill="#b00020" font-family="Helvetica, Arial, sans-serif" font-size="15">{"".join(out)}</g></svg>')

def main(script, outdir, name, dims):
    sys.path.insert(0, os.path.dirname(os.path.abspath(script)))
    res = runpy.run_path(script)["result"]
    asm = res if isinstance(res, cq.Assembly) else cq.Assembly(res, name="part")
    shape = asm.toCompound()
    os.makedirs(outdir, exist_ok=True)
    asm.export(os.path.join(outdir, name + ".glb"))
    bb = shape.BoundingBox()
    size = " x ".join("%g" % round(v, 1) for v in (bb.xlen, bb.ylen, bb.zlen))
    # NB: 'top' in the runner's presets looks down the pipe axis, which is end-on for this long part;
    # the plan view of a cart part is the one looking at the plate, so it is rendered from -Y ("front").
    for view, label in (("iso", "iso"), ("front", "top (plan)"), ("right", "side")):
        svg = runner.project_svg(shape, view, width=W, height=H, show_hidden=False,
                                 caption=f"{name}  ·  {label}  ·  bbox {size} mm")
        tag = {"right": "side", "front": "plan"}.get(view, view)
        if tag in dims:
            svg = dim_svg(svg, shape, tag, dims[tag])
        cairosvg.svg2png(bytestring=svg.encode(), write_to=os.path.join(outdir, f"{name}-{tag}.png"), output_width=1400 if tag != "iso" else 1000)
        print("wrote", tag)

if __name__ == "__main__":
    script, outdir, name = sys.argv[1:4]
    DIMS = {}
    if len(sys.argv) > 4:   # optional python file defining DIMS
        DIMS = runpy.run_path(sys.argv[4])["DIMS"]
    main(script, outdir, name, DIMS)
