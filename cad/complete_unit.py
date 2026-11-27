# cad/complete_unit.py: the COMPLETE UNIT model (OpenPocket #311, rebuilt single-source in #365). Nothing is drawn here: every part is imported.
#   unit (tank, WATER VOLUME, lid, growing pipe, spine, track, frame, panel, feet): cad/parts/unit.py
#   (OpenPocket #537, 27 Nov 2026) the pods sit in the REAL pod collars (cad/pipe_collar.py, placed by cad/parts/pod_collars.py), none where a connector clamps on;
#   the spine-to-track connector (cad/spine_connector.py) at the bottom and the top track run; the REAL seedling tray (cart_arm.py) and pod store rows
#   (pod_store_reach.py) on the shelf: cad/parts/seedling_real.py. The generic pod places (parts/pods.py) and the stand-in trays (parts/shelf_items.py) are no longer used here.
#   the REAL cart (motors inward, #312) with its sample tubing coil (#330): cad/parts/cart.py + cad/water_sampler.py, clamped on the right vertical track run.
#   the shelf (z 155..159, above the water) with the tray and the store on it, under the lid: cad/parts/shelf.py
# The cart carries no pipe of its own (#447): the only track is the unit's track_loop (cad/parts/track.py); hand B closes on it, hand C is where the neighbour's track would be. Z up, mm; the GLB is Y up like the others.
#   python cad/complete_unit.py   -> cad/renders/complete-unit.glb   (+ PNGs with cad/render_unit.py)
import os
import sys
import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import layout as LAY   # the ONE layout (cad/layout.json): the track offset, the climbing sleeve
from parts.unit import unit_parts
from parts.unit_dims import TX, LOOP_Y
from parts import pod_collars as pcol
from parts.seedling_real import seedling_tray_real, pod_store_real, COLOR_TRAY, COLOR_STORE
import spine_connector as sc
from parts.cart import add_cart
import water_sampler as wsa

CART_Z = 1000.0                  # cart centre height on the right run (ASSUMED: mid-height)
CART_SHIFT = (TX + LAY.CART_PIPE_SPACING / 2, LOOP_Y, CART_Z)   # cart pipe B (x -60, y 0) onto the track (x TX, y LOOP_Y): a plain translation, no rotation, plate on the front (-Y) side


def to_unit(shape):
    return shape.translate(CART_SHIFT)


def connector_holes():
    """Cut-outs for the rod at each connector height: through the track pipe wall (spine side), the central pipe's front wall and the spine tube's near wall."""
    import cadquery as cq
    out = {}
    d = sc.HOLE_D
    for z in (sc.ZONES["bottom"], sc.ZONES["top"]):
        rod = cq.Workplane("XZ").circle(d / 2).extrude(LAY.TRACK_OFFSET + 4).translate((0, 0, z))      # XZ extrudes towards -Y: from y = 0 to the track's far wall
        out[z] = rod
    return out


def unit_with_connector_holes(water=True):
    """unit_parts with the drilled holes: the pod collars' 45 mm holes and the connectors' rod holes in the central pipe, the rod holes in the spine tube and the track."""
    import cadquery as cq
    holes = connector_holes()
    rod_cut = None
    for r in holes.values():
        rod_cut = r if rod_cut is None else rod_cut.union(r)
    out = []
    for n, s, c in unit_parts(water=water):
        if n == "growing_pipe":
            s = s.cut(pcol.drill_holes(pcol.hole_heights())).cut(rod_cut)
        elif n in ("spine_tube", "track_loop"):
            s = s.cut(rod_cut)
        elif n == "spine_brackets":
            continue            # the invented 16 x 30 mm block at each track run is replaced by the real connector (cad/spine_connector.py)
        out.append((n, s, c))
    return out


def connector_shift(z):
    return (0.0, LOOP_Y, z)       # the joint's track axis (origin of spine_connector.connector_parts) onto the unit's track run at height z; the spine is then at y = 0


def scene(with_cart=True, water=True):
    a = cq.Assembly()
    for n, s, c in unit_with_connector_holes(water=water):
        a.add(s, name=n, color=cq.Color(*c))
    pcol.add_collars(a)                                                     # the real pod collars, each with its pod (cad/pipe_collar.py)
    for k, z in sc.ZONES.items():                                           # the spine-to-track connector at the bottom and the top track run (#561)
        for n, s, col in sc.connector_parts():
            a.add(s.translate(connector_shift(z)), name="connector_%s_%s" % (k, n), color=cq.Color(*col, 1))
    a.add(seedling_tray_real(), name="seedling_tray", color=cq.Color(*COLOR_TRAY))
    a.add(pod_store_real(), name="pod_store", color=cq.Color(*COLOR_STORE))
    if with_cart:
        # the unit's track pipe IS the pipe hand B clamps; BOTH hands stay (hand C is on the neighbour unit's track, which is not drawn)
        add_cart(a, "cart_", shift=CART_SHIFT)
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
    unit = {n: s for n, s, c in unit_with_connector_holes()}
    for un, us in unit.items():
        for cn, cs in cart.items():
            v = inter(us, cs)
            if v > 1e-3:
                out["%s vs %s" % (un, cn)] = round(v, 2)
    return out


def check_items():
    """Clashes (mm3) of the pod collars with their pods, the connector parts, the tray and the pod store against every unit part. The track pipe is drawn as a solid
    rod (cad/parts/track.py), so the connector's nut plate, which sits inside the real hollow pipe, is left out against it."""
    from parts.common import inter
    unit = {n: s for n, s, c in unit_with_connector_holes()}
    out = {}
    for ch in result.children:
        if not (ch.name.startswith(("podcollar_", "connector_")) or ch.name in ("seedling_tray", "pod_store")):
            continue
        sh = ch.obj.val() if hasattr(ch.obj, "val") else ch.obj
        w = cq.Workplane("XY").add(sh.moved(ch.loc) if ch.loc else sh)
        for un, us in unit.items():
            if un == "water_volume" or (un == "track_loop" and ch.name.endswith("nut_plate")):
                continue
            if ch.name.startswith(("podcollar_", "connector_")) and un == "tank":
                continue
            v = inter(us, w)
            if v > 1e-3:
                out["%s vs %s" % (ch.name, un)] = round(v, 2)
    return out


def check_pods():
    """No pod place where a connector clamps on, and the collars clear each other and the clamp collars; returns the report lines. Fails (AssertionError) otherwise."""
    msgs = []
    bottoms = pcol.collar_bottoms()
    for zb in bottoms:
        for lo, hi, why in pcol.keepouts():
            assert not (zb < hi and zb + pcol.pc.H > lo), "pod collar z %.1f..%.1f reaches into the %s keep-out %.1f..%.1f" % (zb, zb + pcol.pc.H, why, lo, hi)
    for a_, b_ in zip(bottoms, bottoms[1:]):
        assert b_ - a_ >= pcol.pc.H, "pod collars at %.1f and %.1f overlap" % (a_, b_)
    n_old, levels, n_clash = pcol.old_pod_places()
    msgs.append("pod collars: %d real collars (pipe_collar.py, %.0f mm tall, one pod place each); the old generic places: %d (%d levels of 4), %d of them inside a connector keep-out (connector heights %s, keep-out +-%.0f mm)"
                % (len(bottoms), pcol.pc.H, n_old, len(levels), n_clash, ", ".join("%.0f" % z for z in pcol.CONNECTOR_Z), LAY.CONNECTOR_KEEPOUT))
    return msgs


if __name__ == "__main__":
    import json
    for m in check_pods():
        print(m)
    out = os.path.join(HERE, "renders", "complete-unit.glb")
    result.export(out, tolerance=0.5, angularTolerance=0.3)
    print("wrote", os.path.relpath(out), "cart clashes:", json.dumps(check()))
    items = check_items()
    print("pod collars, connectors, tray and pod store vs the unit parts, clashes:", json.dumps(items))
    assert not items, "the complete unit has clashes: %s" % items
