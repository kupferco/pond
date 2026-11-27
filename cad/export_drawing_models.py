# cad/export_drawing_models.py: bring the Drawings page models up to date with the CURRENT CAD (OpenPocket #364). Writes docs/drawings/renders/<name>.glb, one new version per drawing,
# straight from the CadQuery scripts as they are on this branch (cart with the motors inward #312, the water sampler and station #330, the shared layout cad/layout.json, water in the tank).
# Usage: python cad/export_drawing_models.py [name ...]      (no names = all). Then: python cad/render_line_thumbs.py views <id> ...   (line drawings of the new GLBs).
# Cart models are exported with a coarser mesh (tolerance 1.0) so each stays a few MB; the orientation is the one the scripts have (cart frame like cart-assembly-v4.glb, unit frame upright like complete-unit-v1.glb).
import os
import sys
import time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
OUT = os.path.join(HERE, "..", "docs", "drawings", "renders")


def cart_models():
    import cart_sleeves as cs
    import cart_wheel_pairs as cw
    import cart_arm as arm
    import cart_base as cb
    import cart_pod_holder as ph
    import hand_sleeve as hs
    import water_assembly as wa
    import cadquery as cq
    hand = cq.Assembly()
    hand.add(cs.cyl(hs.R_PIPE, 250.0, "z", (0, 0, 0)), name="track_pipe", color=cq.Color(0.75, 0.78, 0.8, 1))
    for n, (s, col) in cs.hand_parts().items():
        hand.add(s, name=n, color=cq.Color(*col))
    import cart_assembly as ca
    import water_sampler as wsa

    def whole_cart():
        a = cq.Assembly()                                              # the whole cart: both hands on both pipes (motors inward, #312) + the water sampler (#330)
        for ch in ca.result.children:
            a.add(ch.obj, name=ch.name, loc=ch.loc, color=ch.color)
        for n, (s, c) in wsa.parts().items():
            a.add(s, name=n, color=cq.Color(*c))
        return a
    return {
        "cart-assembly-v5": whole_cart,
        "cart-arm-stowed-v4": lambda: arm.result_stowed,
        "cart-arm-v4": lambda: arm.result,
        "cart-base-v3": lambda: cb.result,
        "cart-pod-holder-v3": lambda: ph.scene(True, show=("plate", "battery", "arm_base")),
        "cart-sleeves-v3": lambda: cs.clamped,
        "cart-wheel-two-hands-v2": lambda: cw.context,
        "cart-wheel-pairs-v2": lambda: cw.result,
        "cart-wheel-corner-v2": lambda: cw.corner,
        "hand-sleeve-v5": lambda: hand,
    }


def unit_models():
    import runpy
    def run(f):
        return lambda: runpy.run_path(os.path.join(HERE, f))["result"]
    return {
        "unit-bracing-v6": run("unit_structure_drawing.py"),                # tank with water, shared layout track height
        "unit-v3-dimensioned-v3": run("unit_v3_dimensioned.py"),
        "unit-full-v4": run("complete_unit.py"),               # OpenPocket #376: from cad/parts/ (real cart, sampler, unit), not from the old study
        "track-supports-assembly-v2": run("track_supports.py"),
    }


def main():
    want = sys.argv[1:]
    models = {}
    models.update(unit_models())
    models.update(cart_models())
    for name, make in models.items():
        if want and name not in want:
            continue
        t = time.time()
        a = make()
        coarse = name.startswith(("cart", "hand"))
        a.export(os.path.join(OUT, name + ".glb"), tolerance=1.0 if coarse else 0.5, angularTolerance=0.5 if coarse else 0.3)
        print("wrote", name + ".glb", "%.0f s" % (time.time() - t), os.path.getsize(os.path.join(OUT, name + ".glb")) // 1024, "kB", flush=True)


if __name__ == "__main__":
    main()
