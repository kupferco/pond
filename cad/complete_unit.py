# cad/complete_unit.py: the COMPLETE UNIT model (OpenPocket #311, rebuilt single-source in #365). Nothing is drawn here: every part is imported.
#   unit (tank, WATER VOLUME, lid, growing pipe, spine, track, frame, panel, feet): cad/parts/unit.py
#   pods in the growing pipe's holes (simplified): cad/parts/pods.py;  seedling tray and storage: cad/parts/lid_items.py
#   the REAL cart (motors inward, #312) with its sample tubing coil (#330): cad/parts/cart.py + cad/water_sampler.py, clamped on the right vertical track run.
# The cart's own pipe stub stands in for the track there (hand and stub of pipe C left out), so there is ONE track pipe. Z up, mm; the GLB is Y up like the others.
#   python cad/complete_unit.py   -> cad/renders/complete-unit.glb   (+ PNGs with cad/render_unit.py)
import os
import sys
import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from parts.unit import unit_parts
from parts.unit_dims import TX, LOOP_Y
from parts.pods import pods_and_caps
from parts.lid_items import seedling_storage, seedling_tray
from parts.cart import add_cart
import water_sampler as wsa

CART_Z = 1000.0                  # cart centre height on the right run (ASSUMED: mid-height)
CART_SHIFT = (TX + 60.0, LOOP_Y, CART_Z)   # cart pipe B (x -60, y 0) onto the track (x TX, y LOOP_Y): a plain translation, no rotation, plate on the front (-Y) side


def to_unit(shape):
    return shape.translate(CART_SHIFT)


def scene(with_cart=True, water=True):
    a = cq.Assembly()
    for n, s, c in unit_parts(water=water):
        a.add(s, name=n, color=cq.Color(*c))
    pods, caps = pods_and_caps()
    a.add(pods, name="pods", color=cq.Color(0.24, 0.67, 0.31, 1))
    a.add(caps, name="pod_caps", color=cq.Color(0.12, 0.12, 0.12, 1))
    a.add(seedling_tray(), name="seedling_tray", color=cq.Color(0.59, 0.43, 0.27, 1))
    a.add(seedling_storage(), name="seedling_storage", color=cq.Color(0.35, 0.5, 0.75, 1))
    if with_cart:
        # the unit's track pipe IS the pipe hand B clamps: the cart's pipe B stub is left out; BOTH hands stay (hand C clamps the neighbour's track, its pipe C stub is shown)
        add_cart(a, "cart_", drop_pipe="B", shift=CART_SHIFT)
        for n, (s, c) in wsa.parts().items():
            a.add(to_unit(s), name=n, color=cq.Color(*c))
    return a


result = scene()


def check():
    """Clashes of the cart (with sampler) against every unit part, mm3 (0 = clear)."""
    from parts.common import inter
    out = {}
    cart = {}
    for ch in result.children:
        if ch.name.startswith("cart_") or ch.name.startswith("sampler_"):
            sh = ch.obj.val() if hasattr(ch.obj, "val") else ch.obj
            cart[ch.name] = cq.Workplane("XY").add(sh.moved(ch.loc) if ch.loc else sh)
    unit = {n: s for n, s, c in unit_parts()}
    for un, us in unit.items():
        for cn, cs in cart.items():
            v = inter(us, cs)
            if v > 1e-3:
                out["%s vs %s" % (un, cn)] = round(v, 2)
    return out


if __name__ == "__main__":
    import json
    out = os.path.join(HERE, "renders", "complete-unit.glb")
    result.export(out, tolerance=0.5, angularTolerance=0.3)
    print("wrote", os.path.relpath(out), "clashes:", json.dumps(check()))
