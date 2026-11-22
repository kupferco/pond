# cad/export_sim_model.py: the MuJoCo sim's geometry comes from the CAD parts (OpenPocket #447).
#   python cad/export_sim_model.py            writes control-ui/src/generated/cad-sim.ts and cad-sim-cart.ts
#   python cad/export_sim_model.py --check    fails if the committed files differ from what the CAD sources give now (used by check_sim_matches_cad.py)
#
# What is exported, all read from the single sources, nothing typed in twice:
#   * every numeric constant (UPPER_CASE) of hand_sleeve.py, cart_dims.py, cart_omni.py, cart_sleeves.py, cart_base.py, cart_geom.py, parts/unit_dims.py and layout.py: the sim's
#     omni cart, track loop and heights import them (control-ui/src/cart/omni.ts, scenes) instead of keeping their own copies;
#   * the cart's meshes: every child of cart_assembly.result (the SAME cart that cad/parts/cart.py add_cart() gives the Complete unit), in the cart frame (x across the pipes,
#     y out of the pipe plane, z along the pipes), grouped by what moves in the sim: the jaw, the drive wheel, the roll wheel, the rest of the hand, the rigid base (plate, battery);
#   * where the cart sits on the unit in the Complete unit (parts/unit_dims + complete_unit.CART_SHIFT) and how the sim's world axes map to the CAD's.
# Meshes are welded and thinned by vertex clustering (the CAD has 150 000 triangles on the cart; the sim needs the shapes, not the screw threads), then stored as base64.
import base64
import hashlib
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
OUT_DIR = os.path.join(HERE, "..", "control-ui", "src", "generated")
CLUSTER_MM = 0.9            # vertex clustering cell: the finest thinning tolerance
MAX_TRIS = 1200             # most triangles kept per part: the cell grows until a part fits
MODULES = ["hand_sleeve", "cart_dims", "cart_omni", "cart_sleeves", "cart_base", "cart_geom", "parts.unit_dims", "layout"]


def _num(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return round(float(v), 6)
    if isinstance(v, (tuple, list)) and v and all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in v):
        return [round(float(x), 6) for x in v]
    return None


def constants():
    import importlib
    out = {}
    for name in MODULES:
        mod = importlib.import_module(name)
        d = {}
        for k in sorted(vars(mod)):
            if k.isupper() and not k.startswith("_"):
                v = _num(getattr(mod, k))
                if v is not None:
                    d[k] = v
        out[name.split(".")[-1]] = d
    return out


def group_of(name):
    """(body, group) of a cart child by its name. body: 'B', 'C' (the hands) or 'base'; group: what moves as one in the sim."""
    if name in ("base_plate", "battery"):
        return "base", "static"
    if name == "so101_arm_envelope":
        return None          # the sim has its own moving SO-101 (src/model.ts); the envelope is a folded stand-in
    if not name.startswith("hand_on_pipe_"):
        raise SystemExit("export_sim_model: unknown cart child %r; teach group_of() where it goes" % name)
    hand, part = name[len("hand_on_pipe_"):].split("_", 1)
    if part in ("jaw", "jaw_hinge_pin") or part.startswith("p60_"):
        return hand, "jaw"
    if part.startswith("drive_wheel") or part == "drive_shaft":
        return hand, "drive"
    if part.startswith("roll_wheel") or part == "roll_shaft":
        return hand, "roll"
    return hand, "static"


def cluster(v, f, cell):
    """Weld and thin a triangle mesh by snapping vertices to a grid of `cell` mm; drops degenerate triangles."""
    v = np.asarray(v, float)
    f = np.asarray(f, int)
    key = np.round(v / cell).astype(np.int64)
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    inv = inv.reshape(-1)
    nv = np.zeros((len(first), 3))
    cnt = np.bincount(inv)
    for k in range(3):
        nv[:, k] = np.bincount(inv, weights=v[:, k]) / cnt
    nf = inv[f]
    ok = (nf[:, 0] != nf[:, 1]) & (nf[:, 1] != nf[:, 2]) & (nf[:, 0] != nf[:, 2])
    nf = nf[ok]
    srt = np.sort(nf, axis=1)
    _, ui = np.unique(srt, axis=0, return_index=True)
    return nv, nf[np.sort(ui)]


def tess(child):
    import cadquery as cq
    o = child.obj
    sh = o.val() if hasattr(o, "val") else o
    if child.loc:
        sh = sh.moved(child.loc)
    v, f = sh.tessellate(0.5, 0.3)
    v = np.array([[p.x, p.y, p.z] for p in v])
    bb = sh.BoundingBox()
    vol = sh.Volume()
    return v, np.array(f), [bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax], vol


def cart_parts():
    import cart_assembly as ca
    parts = []
    for ch in ca.result.children:
        g = group_of(ch.name)
        if g is None:
            continue
        v, f, bb, vol = tess(ch)
        col = ch.color.toTuple() if ch.color else (0.6, 0.6, 0.6, 1)
        parts.append(dict(name=ch.name, body=g[0], group=g[1], rgba=[round(c, 3) for c in col], bbox=[round(x, 2) for x in bb], volume=round(vol, 1), v=v, f=f))
    return parts


def unit_placement():
    import complete_unit as cu
    from parts import unit_dims as ud
    return dict(CART_SHIFT=list(cu.CART_SHIFT), CART_Z=cu.CART_Z, TX=ud.TX, TR=ud.TR, R=ud.R, LOOP_Y=ud.LOOP_Y, ZB=ud.ZB, ZT=ud.ZT,
                note="sim world (x, y, z) = (-cad_y, cad_x, cad_z): the sim's track plane is x = -LOOP_Y, its two legs stand at y = -TX and +TX; the cart origin of the Complete unit is CART_SHIFT (hand B on the leg at TX)")


def build():
    consts = constants()
    parts = cart_parts()
    meta, blobs = [], {}
    for p in parts:
        cell = CLUSTER_MM
        v, f = cluster(p["v"], p["f"], cell)
        while len(f) > MAX_TRIS:
            cell *= 1.25
            v, f = cluster(p["v"], p["f"], cell)
        meta.append(dict(name=p["name"], body=p["body"], group=p["group"], rgba=p["rgba"], bbox=p["bbox"], volume=p["volume"], nv=len(v), nf=len(f)))
        blobs[p["name"]] = (base64.b64encode(np.asarray(v, "<f4").tobytes()).decode(), base64.b64encode(np.asarray(f, "<u4").tobytes()).decode())
    return consts, unit_placement(), meta, blobs


HEADER = "// GENERATED by cad/export_sim_model.py from the CAD sources (OpenPocket #447). Do not edit: change the CAD and run `python cad/export_sim_model.py`.\n"


def render(consts, placement, meta, blobs):
    a = HEADER + "export const CAD_CONSTANTS = " + json.dumps(consts, indent=1) + " as const;\n\n"
    a += "export const CAD_UNIT = " + json.dumps(placement, indent=1) + " as const;\n\n"
    a += "/** One row per cart part of cad/cart_assembly.py: where it sits in the sim (body B | C | base, moving group), its colour, and the CAD's own bounding box (mm) and volume (mm3) for the drift check. */\n"
    a += "export const CAD_CART_PARTS = " + json.dumps(meta) + " as const;\n"
    b = HEADER + "// Cart meshes (cart frame, mm, float32 vertices x y z and uint32 triangle indices, base64), keyed by the CAD part name.\n"
    b += "export const CAD_CART_MESHES: Record<string, { v: string; f: string }> = {\n"
    for k in sorted(blobs):
        b += " %s: { v: '%s', f: '%s' },\n" % (json.dumps(k), blobs[k][0], blobs[k][1])
    b += "};\n"
    return a, b


def main():
    consts, placement, meta, blobs = build()
    a, b = render(consts, placement, meta, blobs)
    pa, pb = os.path.join(OUT_DIR, "cad-sim.ts"), os.path.join(OUT_DIR, "cad-sim-cart.ts")
    if "--check" in sys.argv:
        # the numbers and the part list must be identical; the mesh blob is compared through the part list (bounding boxes and volumes are in it), so a different
        # tessellator version does not fail the check, a changed part does.
        have = open(pa).read() if os.path.exists(pa) else ""
        if have != a:
            print("the sim model is out of date with the CAD: run python cad/export_sim_model.py and commit control-ui/src/generated/")
            return 1
        print("sim model matches the CAD (%d constants, %d cart parts)" % (sum(len(v) for v in consts.values()), len(meta)))
        return 0
    os.makedirs(OUT_DIR, exist_ok=True)
    open(pa, "w").write(a)
    open(pb, "w").write(b)
    print("wrote", os.path.relpath(pa), os.path.relpath(pb), "%d parts, %d triangles, %.0f KB" % (len(meta), sum(m["nf"] for m in meta), len(b) / 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
