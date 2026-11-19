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


def upright_in_unit_frame(path):
    """assembly.glb is built in the CART frame (unit turned by water_assembly.MOVE), so the unit's lid and station lie on their side in a Y-up viewer.
    Turn the root node by the inverse of that move (rotation about Y by +90 deg; a shift does not change how it opens) so the unit's Z (up) becomes glTF +Y, like the other GLBs.
    The root node already carries the usual Z-up to Y-up turn of the OCCT export; this is composed after it."""
    import json, struct
    b = open(path, "rb").read()
    n = struct.unpack("<I", b[12:16])[0]
    j = json.loads(b[20:20 + n])
    root = j["scenes"][0]["nodes"][0]
    qx = j["nodes"][root]["rotation"]                      # [x, y, z, w], -90 deg about X
    h = 0.5 ** 0.5
    qy = (0.0, h, 0.0, h)                                  # +90 deg about Y (inverse of MOVE["rot"] = -90)
    x1, y1, z1, w1 = qx
    x2, y2, z2, w2 = qy
    q = [w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2, w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
         w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2, w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2]
    j["nodes"][root]["rotation"] = q
    js = json.dumps(j, separators=(",", ":")).encode()
    js += b" " * (-len(js) % 4)
    rest = b[20 + n:]
    out = b[:8] + struct.pack("<I", 12 + 8 + len(js) + len(rest)) + struct.pack("<I", len(js)) + b[16:20] + js + rest
    open(path, "wb").write(out)

VIEWS = (("iso", 28, -50), ("front", 0, -90), ("top", 90, -90), ("side", 0, 0))
CART_VIEWS = (("iso", 28, -55), ("front", 0, -90), ("top", 90, -90), ("side", 0, 0))

if __name__ == "__main__":
    ws.scene("unit", door_on=True, cutaway=False).export(os.path.join(R, "water-station.glb"), tolerance=0.2, angularTolerance=0.3)
    print("wrote water-station.glb", flush=True)
    wa.scene("full", door_on=True, cutaway=False).export(os.path.join(R, "assembly.glb"), tolerance=0.5, angularTolerance=0.3)    # coarse mesh like the cart-only GLB (#316)
    upright_in_unit_frame(os.path.join(R, "assembly.glb"))
    print("wrote assembly.glb (upright in the unit frame)", flush=True)
    jobs = (("water-station", ws.scene("unit"), VIEWS, "Water testing station on the unit (door off, cup cut open): flush nozzle socket in the roof above the cup"),
            ("water-station-closeup", ws.scene("close"), VIEWS, "Water testing station: cup, 3 probes, standpipe, flush nozzle socket, drain (door off, cup cut open)"),
            ("water-station-bench", ws.scene("bench"), VIEWS, "Bench rig: same cup, probes and socket on a board, hand syringe, drain to a bucket"),
            ("cart-water-sampler", wa.scene("cart"), CART_VIEWS, "Cart with the water sampler: pump, PU recoil coil, male nozzle parked in the flush socket under the block"),
            ("water-assembly", wa.scene("full", door_on=False, cutaway=True, lid_only=True), CART_VIEWS, "Cart with sampler at the dock beside the water testing station (door off, cup cut open; tank not drawn)"))
    for name, sc, views, title in jobs:
        parts = rl.collect(sc)
        for v, el, az in views:
            rl.draw(parts, el, az, os.path.join(R, "%s-%s.png" % (name, v)), "%s (%s)" % (title, v), note=TRAY_NOTE if name in ("water-station", "water-assembly") else None)
            print("wrote", name, v, flush=True)
    rl.draw(rl.collect(ws.scene("unit", door_on=True, cutaway=False)), 28, -50, os.path.join(R, "water-station-closed-iso.png"),
            "Water testing station, door on (as built)", note=TRAY_NOTE)
