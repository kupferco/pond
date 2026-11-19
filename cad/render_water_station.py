# OpenPocket #330: renders of the shared water testing station and the cart's water sampler (cad/water_station.py, cad/water_sampler.py, cad/water_assembly.py).
# Usage: python cad/render_water_station.py   writes in cad/renders/
#   water-station-{iso,front,top,side}.png          station on the unit (door off, front of cup cut away), unit socket on the lid
#   water-station-closeup-*.png                      station only on the lid
#   water-station-closed-iso.png                     door on
#   water-station-bench-*.png                        bench rig
#   cart-water-sampler-*.png                         the cart with the pump, recoil coil, nozzle and parking socket
#   water-assembly-*.png                             cart + sampler + first unit's lid corner + station (door off, cup cut open)
#   water-station.glb                                station-only model (unit corner + station), kept as the station-only model
#   assembly.glb                                     the FULL assembly: cart (layout B from #312) + sampler + unit corner + station. Do not overwrite it with the station alone.
# Run cad/render_omni_sleeve.py BEFORE this if you want both: it writes assembly.glb too (cart only); this script then replaces it with the full one.
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import render_local as rl
import water_station as ws
import water_assembly as wa

TRAY_NOTE = "Blue flat box on the lid = the unit's seedling storage tray (existing part of the unit, not part of the station). Box stands on 4 legs on the lid."
R = os.path.join(HERE, "renders")
VIEWS = (("iso", 28, -50), ("front", 0, -90), ("top", 90, -90), ("side", 0, 0))
CART_VIEWS = (("iso", 28, -55), ("front", 0, -90), ("top", 90, -90), ("side", 0, 0))

if __name__ == "__main__":
    ws.scene("unit", door_on=True, cutaway=False).export(os.path.join(R, "water-station.glb"), tolerance=0.2, angularTolerance=0.3)
    print("wrote water-station.glb", flush=True)
    wa.scene("full", door_on=True, cutaway=False).export(os.path.join(R, "assembly.glb"), tolerance=0.5, angularTolerance=0.3)    # coarse mesh like the cart-only GLB (#316)
    print("wrote assembly.glb", flush=True)
    jobs = (("water-station", ws.scene("unit"), VIEWS, "Water testing station on the unit (door off, cup cut open): nozzle socket above the cup"),
            ("water-station-closeup", ws.scene("close"), VIEWS, "Water testing station: cup, 3 probes, standpipe, nozzle socket, drain (door off, cup cut open)"),
            ("water-station-bench", ws.scene("bench"), VIEWS, "Bench rig: same cup, probes and socket on a board, hand syringe, drain to a bucket"),
            ("cart-water-sampler", wa.scene("cart"), CART_VIEWS, "Cart with the water sampler: pump, PU recoil coil, nozzle parked in its socket"),
            ("water-assembly", wa.scene("full", door_on=False, cutaway=True, lid_only=True), CART_VIEWS, "Cart with sampler at the dock beside the water testing station (door off, cup cut open; tank not drawn)"))
    for name, sc, views, title in jobs:
        parts = rl.collect(sc)
        for v, el, az in views:
            rl.draw(parts, el, az, os.path.join(R, "%s-%s.png" % (name, v)), "%s (%s)" % (title, v), note=TRAY_NOTE if name in ("water-station", "water-assembly") else None)
            print("wrote", name, v, flush=True)
    rl.draw(rl.collect(ws.scene("unit", door_on=True, cutaway=False)), 28, -50, os.path.join(R, "water-station-closed-iso.png"),
            "Water testing station, door on (as built)", note=TRAY_NOTE)
