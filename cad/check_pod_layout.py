# cad/check_pod_layout.py: fails if the CAD and the sim disagree about the pod-grab layout (OpenPocket #531).   python cad/check_pod_layout.py
#   1. cad/pod_layout.py (read by the sim too) equals the CAD sources it copies: cart_dims (arm and battery on the plate, plate size), unit_dims (shelf, track), layout.json
#   2. the CAD lid has a slot over every tray cell and every store landing (and solid lid between them), and every pod can leave straight up through its slot
#   3. the CAD tray and store hold a pod at every cell and landing, standing on the shelf under the lid; the store lanes slope by SLOPE_DEG and end in a flat landing
#   4. the sim's slots (cad/pod_slots.json) are what the sim measures now (needs mujoco; skipped with a note if it is not installed)
import os
import subprocess
import sys
import math

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pod_layout as PL                          # noqa: E402
import cart_dims as cd                           # noqa: E402
from parts import unit_dims as ud                # noqa: E402
from parts.tank import tank_lid                  # noqa: E402
from parts.shelf_items import seedling_tray, seedling_storage, pods   # noqa: E402
import cadquery as cq                            # noqa: E402


def inside(wp, p):
    return wp.val().isInside(cq.Vector(*p))


def main():
    bad = []

    def need(ok, msg):
        if not ok:
            bad.append(msg)
    # 1. numbers copied from the CAD
    need(abs(PL.ARM_X - cd.ARM_X) < 1e-6 and abs(PL.ARM_Z - cd.ARM_Z) < 1e-6, "ARM_X / ARM_Z differ from cart_dims")
    need(tuple(PL.BATT) == tuple(cd.BATT) and abs(PL.BATT_X - cd.BATT_X) < 1e-6, "BATT / BATT_X differ from cart_dims")
    need(abs(PL.PLATE_Y0 - cd.PLATE_Y0) < 1e-6 and abs(PL.PLATE_T - cd.PLATE_T) < 1e-6, "plate face / thickness differ from cart_dims")
    need(abs(PL.PLATE_ALONG - 2 * cd.PLATE_ZH) < 1e-6 and abs(PL.PLATE_DOWN - (cd.PLATE_X1 - cd.PLATE_X0)) < 1e-6, "plate size differs from cart_dims")
    need(abs(PL.PLATE_CZ_REL + cd.HX) < 1e-6, "the plate centre is not HX below the riding pipe")
    need(abs(PL.SHELF_TOP - ud.SHELF_TOP) < 1e-6 and abs(PL.TRACK_Z - ud.ZB) < 1e-6 and abs(PL.TRACK_Y - ud.LOOP_Y) < 1e-6 and abs(PL.TRACK_R - ud.TR) < 1e-6, "shelf / track numbers differ from unit_dims")
    need(abs(PL.LID_TOP - (ud.TH + ud.LID_T)) < 1e-6, "lid top differs from unit_dims")
    need(PL.queue_ok(), "the queued pods do not fit on the ramp")
    # 2. lid slots
    lid = tank_lid()
    zl = ud.TH + ud.LID_T / 2
    for name, (x, y, _, _) in list(PL.tray_cells().items()) + list(PL.store_cells().items()):
        x0, x1, y0, y1 = PL.slot_rects()[name]
        need(not inside(lid, (x, y, zl)), "%s: the lid is solid over the pod" % name)
        need(x0 <= x - PL.POD_D / 2 and x + PL.POD_D / 2 <= x1 and y0 <= y - PL.POD_D / 2 and y + PL.POD_D / 2 <= y1, "%s: the pod cannot leave straight up through its slot" % name)
        need(x1 - x0 >= PL.SLOT_X - 1 and y1 - y0 >= PL.SLOT_Y - 1, "%s: slot smaller than %g x %g" % (name, PL.SLOT_X, PL.SLOT_Y))
    need(inside(lid, (-300.0, 100.0, zl)) and inside(lid, (0.0, 150.0, zl)), "the lid lost material away from the slots")
    # 3. tray, store, pods
    tray, store, allp = seedling_tray(), seedling_storage(), pods()
    for name, (x, y, z, _) in PL.tray_cells().items():
        need(inside(allp, (x, y, z - 1)), "%s: no pod in the CAD tray" % name)
        need(inside(tray, (x + PL.CELL_X / 2 - 1, y, PL.POD_BOTTOM_TRAY + 8)), "%s: no cell block in the CAD tray" % name)
    for name, (x, y, z, _) in PL.store_cells().items():
        need(inside(allp, (x, y, z - 1)), "%s: no pod on the landing" % name)
        need(not inside(allp, (x, y, z + 1)), "%s: the pod on the landing is taller than the grip height" % name)
        need(inside(store, (x, y, PL.ZL - 1)), "%s: no floor under the landing" % name)
    bt, bs = tray.val().BoundingBox(), store.val().BoundingBox()
    for nm, bb in (("tray", bt), ("store", bs), ("pods", allp.val().BoundingBox())):
        need(abs(bb.zmin - (PL.SHELF_TOP if nm != "pods" else PL.POD_BOTTOM_TRAY)) < 1e-6 and bb.zmax < PL.LID_TOP - PL.LID_T, "%s must stand on the shelf and stay under the lid" % nm)
    rise = PL.ramp_rise()
    top_back = max(p.Z for p in store.val().Vertices() if abs(p.Y - PL.RAMP_Y1) < 1e-6 and p.Z < PL.ZL + rise + 1)
    need(abs(top_back - (PL.ZL + rise)) < 0.5, "the ramp does not rise by ramp_rise() (slope %.1f deg)" % PL.SLOPE_DEG)
    need(abs(math.degrees(math.atan2(rise, PL.RAMP_Y1 - PL.LAND_Y[1])) - PL.SLOPE_DEG) < 1e-6, "slope != SLOPE_DEG")
    # 4. the sim's slots
    try:
        import mujoco  # noqa: F401
        r = subprocess.run([sys.executable, os.path.join(HERE, "..", "sim", "pod_grab_check.py"), "--verify-slots"], capture_output=True, text=True)
        print(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-300:])
        need(r.returncode == 0, "cad/pod_slots.json is not what the sim measures: run python sim/pod_grab_check.py --write-slots")
    except ImportError:
        print("note: mujoco not installed, the sim-slot comparison was skipped")
    if bad:
        print("POD LAYOUT CHECK FAILED:")
        for b in bad:
            print(" -", b)
        return 1
    print("pod layout OK: %d tray cells, %d store landings, slope %.0f deg, slots over every target, CAD and sim numbers equal" % (len(PL.tray_cells()), len(PL.store_cells()), PL.SLOPE_DEG))
    return 0


if __name__ == "__main__":
    sys.exit(main())
