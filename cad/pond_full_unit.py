# cad/pond_full_unit.py: THE full Pond unit assembly, the single one every render, GLB and sim scene imports (OpenPocket #531, owner decision 26 Nov 2026).
# Nothing is drawn here that has a part file: the unit is cad/parts/unit.py, the pods in the growing pipe are cad/parts/pods.py, the shelf, tray, dry pod store and pods are
# cad/parts/shelf_items.py, the lid with its pick slots is cad/parts/tank.py, the water station is cad/water_station.py, the carts are the real cart (cad/cart_assembly.py with the
# water sampler cad/water_sampler.py). The layout numbers (tray, store, slope, slots, parking spots) are cad/pod_layout.py, which sim/pod_grab.py reads too.
#
# THE LAYOUT (upright pod grab, see docs/pod-grab.md)
#   * Two carts, BOTH UPRIGHT (no roll) on the bottom run of the track, track height unchanged: one parked over the seedling tray (x -130), one at the dry pod store (x +135).
#     Hand C rides the track, the plate hangs below it, the free hand B hangs 120 mm under the track, the deepest cart part is 165 mm under the track axis.
#   * The real SO-101 arm (upper arm 116, forearm 135, wrist flex to grip 159.5) is bolted straight on the plate (cad/cart_dims.py v4); the battery stands on its edge beside it.
#     Each arm is drawn in the pick pose the sim solves (sim/pod_grab.py), so the picture and the sim cannot disagree.
#   * Seedling tray 6 x 3 cells; dry pod store: 7 lanes sloping SLOPE_DEG towards the front (cad/pod_layout.py, the one parameter), each ending in a flat landing with a stop lip, 4 pods a lane.
#   * Lid slots over every tray cell and every store landing (cad/pod_slots.json, measured by the sim from the claw and wrist footprint, never smaller than 70 x 50).
#
#   python cad/pond_full_unit.py            -> prints the checks
#   python cad/render_full_unit.py          -> renders (full unit and bottom section, iso / front / top / side) and the GLBs
# Frame: mm, Z up, tank floor z = 0, growing pipe at x = y = 0, front = -Y. The scene is built by build(); `result` is the default scene (a cq.Assembly).
import importlib.util
import math
import os
import sys
import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pod_layout as PL                                    # noqa: E402
from parts.unit import unit_parts                          # noqa: E402
from parts.pods import pods_and_caps                       # noqa: E402
from parts.shelf_items import seedling_tray, seedling_storage, pods as store_and_tray_pods   # noqa: E402
from parts.cart import cart_children                       # noqa: E402
from parts.common import box, cyl                          # noqa: E402
from parts.unit_dims import LOOP_Y, ZB                     # noqa: E402
import water_station as ws                                 # noqa: E402
import water_sampler as wsa                                # noqa: E402

_spec = importlib.util.spec_from_file_location("pod_grab", os.path.join(HERE, "..", "sim", "pod_grab.py"))
G = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(G)                                # the sim: the arm poses come from here (it reads cad/pod_layout.py too)

ZCROP = 750.0                                              # bottom section: everything above this is cut off
DEFAULT_PICKS = {"tray": "C6", "store": "S4"}              # the far-left back corner of the tray (the hardest), a middle landing at the store
ARM_COL = (0.9, 0.15, 0.15, 1)
ARM_COL2 = (0.2, 0.5, 0.9, 1)


def cart_location(x0):
    """Cart frame -> unit frame for the upright cart parked at x0: cart x (across the pipes) -> up, cart y (out of the plate) -> y, cart z (along the pipes) -> -X.
    Hand C (cart x +60) is on the bottom track (x0, LOOP_Y, ZB); the plate hangs below it. A turn of -90 deg about Y and a plain translation, no mirroring."""
    return cq.Location(cq.Vector(x0, LOOP_Y, ZB - 60.0), cq.Vector(0, 1, 0), -90.0)


def _vec(a):
    return cq.Vector(float(a[0]), float(a[1]), float(a[2]))


def _rod(p0, p1, r):
    v = _vec(p1) - _vec(p0)
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(r, v.Length, _vec(p0), v.normalized()))


def _obox(c, ex, ey, ez, sx, sy, sz):
    """Box of size sx, sy, sz along the unit vectors ex, ey, ez, centred on c."""
    pl = cq.Plane(origin=_vec(c), xDir=_vec(ex), normal=_vec(ez))
    return cq.Workplane(pl).box(sx, sy, sz)


def arm_shapes(cell):
    """The SO-101 in its pick pose for a cell: {part name: shape}, in unit coordinates, built from the sim's own solution."""
    import numpy as np
    rec = G.pick_pose(cell, 0.0, collide=True)
    park = rec["park_x_mm"]
    pose = rec["pose"]
    pts, origin, R = G.chain_world(park, pose)
    s0, e, w, t = [np.array(p) for p in pts]
    pan, q1, q2, q3 = pose
    phi = q1 + q2 + q3
    ex = R @ np.array([math.cos(phi) * math.cos(pan), math.cos(phi) * math.sin(pan), -math.sin(phi)])      # claw axis
    ey = R @ np.array([-math.sin(pan), math.cos(pan), 0.0])                                                 # sideways of the arm plane
    ez = np.cross(ex, ey)
    out = {}
    out["arm_base"] = _obox(origin + R @ np.array([20.0, 0.0, 33.0]), R[:, 0], R[:, 1], R[:, 2], 90.0, 70.0, 66.0)
    out["arm_shoulder"] = _obox(origin + R @ np.array([77.0 * math.cos(pan), 77.0 * math.sin(pan), 88.0]), R[:, 0], R[:, 1], R[:, 2], 52.0, 66.0, 68.0)
    out["arm_upper"] = _rod(s0, e, 20.0)
    out["arm_forearm"] = _rod(e, w, 20.0)
    out["arm_wrist"] = _obox(w + ex * 30.0, ex, ey, ez, 70.0, 40.0, 50.0)
    out["arm_gripper"] = _obox(w + ex * 88.5, ex, ey, ez, 75.0, 44.0, 32.0)
    out["arm_jaw"] = _obox(w + ex * 143.0, ex, ey, ez, 35.0, 24.0, 20.0)
    joints = None
    for nm, p in (("arm_joint_shoulder", s0), ("arm_joint_elbow", e), ("arm_joint_wrist", w)):
        joints = cq.Workplane("XY").sphere(22.0).translate(tuple(float(v) for v in p)) if joints is None else joints.union(cq.Workplane("XY").sphere(22.0).translate(tuple(float(v) for v in p)))
    out["arm_joints"] = joints
    return out, rec


def _moved(obj, loc):
    """A Workplane or Shape moved by a Location, as a Workplane."""
    sh = obj.val() if hasattr(obj, "val") else obj
    return cq.Workplane("XY").add(sh.moved(loc))


def cart_shapes(x0):
    """[(name, shape, colour)] of the real cart (without its folded-arm envelope: the posed arm replaces it) with the water sampler, placed at x0."""
    loc = cart_location(x0)
    out = []
    for ch in cart_children(skip=("so101_arm_envelope",)):
        col = ch.color.toTuple() if ch.color else (0.6, 0.6, 0.6, 1)
        out.append(("cart_" + ch.name, _moved(ch.obj, loc * ch.loc if ch.loc else loc), col))
    for n, (s, c) in wsa.parts().items():
        out.append((n, _moved(s, loc), c))
    return out


def unit_shapes(crop=False):
    """[(name, shape, colour)] of the unit and everything on and in it (no carts)."""
    out = [(n, s, c) for n, s, c in unit_parts()]
    pods, caps = pods_and_caps()
    out += [("pods_in_growing_pipe", pods, (0.24, 0.67, 0.31, 1)), ("pod_caps", caps, (0.12, 0.12, 0.12, 1)),
            ("seedling_tray", seedling_tray(), (0.59, 0.43, 0.27, 1)), ("dry_pod_store", seedling_storage(), (0.35, 0.5, 0.75, 1)),
            ("pods_tray_and_store", store_and_tray_pods(), (0.95, 0.6, 0.2, 1))]
    for n, (s, c) in ws.station_parts(door_on=False, cutaway=False).items():
        out.append((n, s, c))
    for n, (s, c) in ws.unit_socket().items():
        out.append((n, s, c))
    if crop:
        keep = box(2000, 2000, ZCROP, 0, 0, -1)
        cut = []
        for n, s, c in out:
            bb = s.val().BoundingBox() if hasattr(s, "val") else s.BoundingBox()
            if bb.zmin > ZCROP:
                continue
            cut.append((n, s if bb.zmax <= ZCROP else s.intersect(keep), c))
        out = cut
    return out


def build(picks=None, crop=False, carts=True):
    """The full unit. picks = {"tray": cell, "store": cell}: where each arm is. crop=True: the bottom section only (cut at z 750). Returns a cq.Assembly."""
    picks = dict(DEFAULT_PICKS, **(picks or {}))
    a = cq.Assembly()
    for n, s, c in unit_shapes(crop):
        a.add(s, name=n, color=cq.Color(*c))
    if carts:
        for tag, x0, col in (("tray", PL.PARK_TRAY, ARM_COL), ("store", PL.PARK_STORE, ARM_COL2)):
            for n, s, c in cart_shapes(x0):
                a.add(s, name="%s_%s" % (tag, n), color=cq.Color(*c))
            arm, _ = arm_shapes(picks[tag])
            for n, s in arm.items():
                a.add(s, name="%s_%s" % (tag, n), color=cq.Color(*col))
    return a


result = build()


def solids_of(a):
    """{name: Workplane in unit coordinates} of an assembly (locations applied)."""
    out = {}
    for ch in a.children:
        sh = ch.obj.val() if hasattr(ch.obj, "val") else ch.obj
        out[ch.name] = cq.Workplane("XY").add(sh.moved(ch.loc) if ch.loc else sh)
    return out


def check():
    """The cart and the arm of each side against every unit part: the clash volumes in mm3 (nothing but the arm base on its plate and the arm tip on its pod may touch)."""
    from parts.common import inter
    parts = solids_of(build())
    res = {}
    carts = {n: s for n, s in parts.items() if n.startswith(("tray_cart_", "store_cart_", "tray_arm_", "store_arm_", "tray_sampler", "store_sampler"))}
    unit = {n: s for n, s in parts.items() if n not in carts}
    for cn, cs in carts.items():
        for un, us in unit.items():
            v = inter(cs, us)
            if v > 1.0:
                res["%s vs %s" % (cn, un)] = round(v, 1)
    return res


if __name__ == "__main__":
    import json
    bb = result.toCompound().BoundingBox()
    print("full unit: %d parts, bbox %.0f x %.0f x %.0f mm" % (len(result.children), bb.xlen, bb.ylen, bb.zlen))
    print("clashes of cart and arm with the unit (mm3):", json.dumps(check(), indent=1))
