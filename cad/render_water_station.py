# OpenPocket #330: renders of the shared water testing station (cad/water_station.py).
# Usage: python cad/render_water_station.py   writes cad/renders/water-station-{iso,front,top,side}.png (on the unit, door off, front of cup cut away),
#   water-station-closeup-*.png (station only on the lid), water-station-closed-iso.png (door on), water-station-bench-*.png (bench rig),
#   water-station.glb and a copy as assembly.glb (the viewer opens assembly.glb).
import os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import render_local as rl
import water_station as ws

R = os.path.join(HERE, "renders")
VIEWS = (("iso", 28, -50), ("front", 0, -90), ("top", 90, -90), ("side", 0, 0))

if __name__ == "__main__":
    unit = ws.scene("unit")
    unit.export(os.path.join(R, "water-station.glb"), tolerance=0.2, angularTolerance=0.3)
    shutil.copyfile(os.path.join(R, "water-station.glb"), os.path.join(R, "assembly.glb"))
    jobs = (("water-station", unit, "Shared water testing station on the unit, next to the dock (door off, cup cut open)"),
            ("water-station-closeup", ws.scene("close"), "Water testing station: sample cup, 3 probes, rinse pump, drain (door off, cup cut open)"),
            ("water-station-bench", ws.scene("bench"), "Bench rig: same cup, probes and pump on a board, drain to a bucket"))
    for name, sc, title in jobs:
        parts = rl.collect(sc)
        for v, el, az in VIEWS:
            rl.draw(parts, el, az, os.path.join(R, "%s-%s.png" % (name, v)), "%s (%s)" % (title, v))
            print("wrote", name, v, flush=True)
    rl.draw(rl.collect(ws.scene("unit", door_on=True, cutaway=False)), 28, -50, os.path.join(R, "water-station-closed-iso.png"),
            "Water testing station, door on (as built)")
