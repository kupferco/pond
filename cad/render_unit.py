# OpenPocket #365: renders and GLBs of the whole unit and its parts in assembly context, all from the single-source parts (cad/parts/).
#   python cad/render_unit.py [name ...]     (no names = everything)
#   complete-unit-{iso,front,top,side}.png + complete-unit.glb   whole unit: tank with WATER, frame, panel, pods, trays, cart (motors inward) with sample coil on the track
#   unit-water-{iso,front,top,side}.png + unit-water.glb         the unit's structure with the water volume (tank and water are separate named parts)
#   unit-dimensioned-{...} + .glb                                unit v3 with the blue dimension lines (cad/unit_v3_dimensioned.py), now with the water level
#   tank-water-{iso,front,top,side}.png + tank-water.glb         tank (lid off) and water volume only, so the 15 cm water level shows
#   sample-coil-{iso,front,top,side}.png + sample-coil.glb       the cart with the pump, sample tubing coil, tail and parked nozzle (cart context)
import os, runpy, sys
import cadquery as cq
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import render_local as rl
R = os.path.join(HERE, "renders")
VIEWS = (("iso", 25, -50), ("front", 0, -90), ("top", 90, -90), ("side", 0, 0))


def unit_water():
    return runpy.run_path(os.path.join(HERE, "unit_structure_drawing.py"))["result"]


def tank_water():
    from parts.tank import tank_shell, COLOR_TANK
    from parts.water_volume import water_volume, COLOR_WATER
    a = cq.Assembly()
    a.add(tank_shell(), name="tank", color=cq.Color(*COLOR_TANK))
    a.add(water_volume(), name="water_volume", color=cq.Color(*COLOR_WATER))
    return a


def sample_coil():
    import cart_assembly as ca
    import water_sampler as wsa
    from parts.cart import add_cart
    a = cq.Assembly()
    add_cart(a, "cart_")
    for n, (s, c) in wsa.parts().items():
        a.add(s, name=n, color=cq.Color(*c))
    return a


def complete_unit():
    return runpy.run_path(os.path.join(HERE, "complete_unit.py"))["result"]


def unit_dimensioned():
    return runpy.run_path(os.path.join(HERE, "unit_v3_dimensioned.py"))["result"]


JOBS = {"complete-unit": (complete_unit, "Complete unit: tank with water, frame, panel, pods, trays, cart (motors inward) with sample coil on the track"),
        "unit-dimensioned": (unit_dimensioned, "Unit v3 dimensioned (water 15 cm, shelf 155 with seedling items)"),
        "unit-water": (unit_water, "Unit structure with the water volume (normal level 15 cm, translucent blue)"),
        "tank-water": (tank_water, "Tank (lid off) and water volume at the normal level (15 cm)"),
        "sample-coil": (sample_coil, "Cart with the water-test sample tubing: pump, silicone link, PU recoil coil, tail, parked nozzle")}

if __name__ == "__main__":
    want = sys.argv[1:] or list(JOBS)
    for name in want:
        fn, title = JOBS[name]
        sc = fn()
        sc.export(os.path.join(R, name + ".glb"), tolerance=0.5, angularTolerance=0.3)
        print("wrote", name + ".glb", flush=True)
        parts = rl.collect(sc)
        for v, el, az in VIEWS:
            rl.draw(parts, el, az, os.path.join(R, "%s-%s.png" % (name, v)), "%s (%s)" % (title, v))
            print("wrote", name, v, flush=True)
