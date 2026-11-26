"""Reach and collision check for the upright pod-grab layout (OpenPocket #531): EVERY seedling tray cell and EVERY dry pod store landing.

    pip install mujoco numpy
    python3 sim/pod_grab_check.py                 # table -> docs/pod-grab/results.json and docs/pod-grab/tables.md; exit 1 if a pick fails
    python3 sim/pod_grab_check.py --write-slots   # measure the claw footprint at the lid and write cad/pod_slots.json (the CAD lid reads it), then run the check
    python3 sim/pod_grab_check.py --verify-slots  # fail if cad/pod_slots.json is not what the sim measures now (the CAD lid would not match the sim)
    python3 sim/pod_grab_check.py --slope 20      # try another store slope (the 15 deg is a guess: cad/pod_layout.py SLOPE_DEG)

For every cell: is the target reachable inside the SO-101 joint limits, with the claw vertical or how far it has to tilt sideways, the reach (shoulder to wrist axis against the
251 mm of the two links), joint angles against the limits, the wrist height above the lid, holding torque with the pod and 400 g lettuce against the STS3215 stall, the hover pose 50 mm higher,
and the smallest distance of the arm (and of the cart) to the lid with its slots, the plate, the battery, the pillar, the water station, the tray, the store and every other pod.
A pose counts as collision free with at least CLEAR_MIN_MM (1 mm) of air everywhere.
"""
import importlib.util
import json
import math
import os
import sys

import mujoco
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("pod_grab", os.path.join(HERE, "pod_grab.py"))
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)
PL = G.PL
OUT = os.path.join(HERE, "..", "docs", "pod-grab")
DEG = math.degrees
JN = G.LIMIT_NAMES


def params(**kw):
    p = {k: v[0] for k, v in G.PARAMS.items()}
    p.update(kw)
    return p


def analyse(name, p, model, loaded, unloaded):
    x, y, z, park = G.cell_target(name)
    rec = G.pick_pose(name, 0.0, p)
    out = {"cell": name, "target_mm": [round(x, 1), round(y, 1), round(z, 1)], "park_x_mm": park, "reachable": rec["reachable"], "pan_deg": rec["pan_deg"]}
    if not rec["reachable"]:
        out["collision_free"] = False
        return out
    pose = rec["pose"]
    out.update(collision_free=rec["collision_free"], tilt_deg=round(rec["tilt"], 1), vertical_claw=rec["tilt"] <= float(p["tilt_tol_deg"]))
    out["joints_deg"] = {n: round(DEG(v), 1) for n, v in zip(JN, pose)}
    out["joint_margin_deg"] = {n: round(DEG(min(v - G.LIMITS[n][0], G.LIMITS[n][1] - v)), 1) for n, v in zip(JN, pose)}
    out["tightest_joint"] = min(out["joint_margin_deg"], key=out["joint_margin_deg"].get)
    out["tightest_joint_margin_deg"] = out["joint_margin_deg"][out["tightest_joint"]]
    pts, _, _ = G.chain_world(park, pose)
    out["reach_mm"] = round(float(np.linalg.norm(pts[2] - pts[0])), 0)                 # shoulder_lift axis to wrist_flex axis, against 116 + 135 = 251
    out["reach_limit_mm"] = 251
    out["wrist_above_lid_mm"] = round(float(pts[2][2]) - PL.LID_TOP, 0)
    out["grip_point_error_mm"] = None
    hov = G.pick_pose(name, float(p["hover_mm"]), p)
    out["hover_reachable"] = hov["reachable"]
    out["hover_collision_free"] = hov["collision_free"]
    for tag, mdl in (("loaded", loaded), ("unloaded", unloaded)):
        d = mujoco.MjData(mdl)
        G.set_pose(mdl, d, park, pose)
        out[f"torque_{tag}_nm"] = {n: round(abs(float(d.qfrc_bias[mdl.joint(n).dofadr[0]])), 2) for n in JN}
        if tag == "loaded":
            out["grip_point_error_mm"] = round(float(np.linalg.norm(d.site_xpos[mdl.site("tcp").id] * 1000 - np.array([x, y, z]))), 1)
    tq = out["torque_loaded_nm"]
    out["max_torque_nm"] = max(tq.values())
    out["max_torque_joint"] = max(tq, key=tq.get)
    out["torque_vs_stall_7v4"] = round(out["max_torque_nm"] / 1.9, 2)
    out["clearance"] = rec["clearance"]
    out["arm_worst_mm"] = round(G.worst_mm(rec["clearance"]), 1)
    worst = min((v["mm"], k, v["between"]) for k, v in rec["clearance"].items() if k.startswith("arm_to"))
    out["arm_worst_between"] = f"{worst[1][7:]}: {worst[2]}"
    out["slot_mm"] = list(PL.slot_rects()[name])
    return out


def run_all(p):
    loaded = mujoco.MjModel.from_xml_string(G.build(**p))
    unloaded = mujoco.MjModel.from_xml_string(G.build(**dict(p, load_kg=0.0)))
    model = G.model_for(**{k: v for k, v in p.items()})
    res = {"params": {k: p[k] for k in ("slope_deg", "stall_nm", "load_kg", "tilt_tol_deg", "max_tilt_deg")}, "tray": [], "store": []}
    for n in G.CELLS_TRAY:
        res["tray"].append(analyse(n, p, model, loaded, unloaded))
    for n in G.CELLS_STORE:
        res["store"].append(analyse(n, p, model, loaded, unloaded))
    both = res["tray"] + res["store"]
    # cart against the rest at the two parking spots (the pose does not matter: the cart is rigid)
    d = mujoco.MjData(model)
    grp = G.groups(model)
    cart = {}
    for lab, park in (("tray_park_-130", PL.PARK_TRAY), ("store_park_+135", PL.PARK_STORE)):
        G.set_pose(model, d, park, (0.0,) + G.SAFE)
        cl = G.clearances(model, d, "A1", grp)
        cart[lab] = {k: v for k, v in cl.items() if k.startswith("cart_to")}
    res["cart"] = cart
    res["summary"] = {"targets": len(both), "reachable": sum(c["reachable"] for c in both), "collision_free": sum(bool(c.get("collision_free")) for c in both),
                      "vertical_claw": sum(bool(c.get("vertical_claw")) for c in both), "max_tilt_deg": max((c.get("tilt_deg") or 0) for c in both),
                      "max_reach_mm": max((c.get("reach_mm") or 0) for c in both), "max_torque_nm": max((c.get("max_torque_nm") or 0) for c in both),
                      "hover_reachable": sum(bool(c.get("hover_reachable")) for c in both), "min_arm_clearance_mm": min((c.get("arm_worst_mm", -99) for c in both))}
    return res


def table_md(res):
    def rows(cells, title):
        out = [f"### {title}", "", "| Cell | Claw tilt | Pan | Reach / 251 mm | Wrist over lid | Tightest joint | Worst servo (N m, % of 1.9) | Closest the arm gets (mm) | Slot x0..x1, y0..y1 (mm) |",
               "|---|---|---|---|---|---|---|---|---|"]
        for c in cells:
            if not c["reachable"]:
                out.append(f"| {c['cell']} | **NOT REACHABLE** | | | | | | | |")
                continue
            tilt = "vertical" if c["vertical_claw"] else f"{c['tilt_deg']:.0f} deg"
            ok = "" if c["collision_free"] else " **COLLIDES**"
            out.append(f"| {c['cell']} | {tilt} | {c['pan_deg']:.0f} | {c['reach_mm']:.0f} | {c['wrist_above_lid_mm']:.0f} | {c['tightest_joint'].replace('_', ' ')} {c['tightest_joint_margin_deg']:.0f} deg | "
                       f"{c['max_torque_nm']:.2f} ({c['torque_vs_stall_7v4'] * 100:.0f} %) | {c['arm_worst_mm']:.0f} ({c['arm_worst_between']}){ok} | "
                       f"{c['slot_mm'][0]:.0f}..{c['slot_mm'][1]:.0f}, {c['slot_mm'][2]:.0f}..{c['slot_mm'][3]:.0f} |")
        return out
    s = res["summary"]
    lines = [f"Generated by `python3 sim/pod_grab_check.py` (store slope {res['params']['slope_deg']:.0f} deg). {s['targets']} targets: {s['reachable']} reachable, {s['collision_free']} collision free "
             f"(at least {G.CLEAR_MIN_MM:.0f} mm of air to everything), {s['vertical_claw']} with a vertical claw, largest sideways tilt {s['max_tilt_deg']:.0f} deg, "
             f"largest reach {s['max_reach_mm']:.0f} of 251 mm, worst servo torque {s['max_torque_nm']:.2f} N m, smallest arm clearance {s['min_arm_clearance_mm']:.1f} mm.", ""]
    lines += rows(res["tray"], "Seedling tray (18 cells, cart parked at x -130)") + [""] + rows(res["store"], "Dry pod store (7 landings, cart parked at x +135)") + ["", "### Cart clearance (mm)", ""]
    for lab, d in res["cart"].items():
        lines.append(f"- {lab}: " + ", ".join(f"{k[8:]} {v['mm']:.0f}" for k, v in d.items()))
    return "\n".join(lines) + "\n"


def write_slots(p):
    slots = {}
    for n in G.CELLS_TRAY + G.CELLS_STORE:
        r = G.slot_for(n, p)
        if r is None:
            sys.exit(f"{n}: no reachable pose, no slot")
        slots[n] = list(r)
    json.dump({"_about": "Written by sim/pod_grab_check.py --write-slots: the claw and wrist footprint at the lid for the pick pose of every target, plus 4 mm, at least 70 x 50. Do not edit by hand. mm, CAD frame: x0, x1, y0, y1.",
               "slots": slots}, open(PL.SLOTS_JSON, "w"), indent=1)
    print("wrote", PL.SLOTS_JSON)


def verify_slots(p):
    bad = []
    for n in G.CELLS_TRAY + G.CELLS_STORE:
        r = G.slot_for(n, p)
        have = PL.slot_rects().get(n)
        if have is None or r is None or any(abs(a - b) > 1.0 for a, b in zip(r, have)):
            bad.append((n, have, r))
    return bad


def main():
    os.makedirs(OUT, exist_ok=True)
    slope = float(sys.argv[sys.argv.index("--slope") + 1]) if "--slope" in sys.argv else PL.SLOPE_DEG
    p = params(slope_deg=slope)
    if "--write-slots" in sys.argv:
        write_slots(p)
        G._MODELS.clear()
        importlib.reload(importlib.util.module_from_spec(spec)) if False else None
    if "--verify-slots" in sys.argv:
        bad = verify_slots(p)
        for b in bad:
            print("slot differs", b)
        print("slots match the sim" if not bad else "SLOTS DO NOT MATCH THE SIM: run python3 sim/pod_grab_check.py --write-slots")
        sys.exit(1 if bad else 0)
    if "--write-slots" in sys.argv:
        # the lid in the sim was built before the new slots were written: rebuild by running the check in a fresh process
        os.execv(sys.executable, [sys.executable, os.path.abspath(__file__)] + [a for a in sys.argv[1:] if a != "--write-slots"])
    res = run_all(p)
    json.dump(res, open(os.path.join(OUT, "results.json" if slope == PL.SLOPE_DEG else f"results-slope{slope:.0f}.json"), "w"), indent=1)
    md = table_md(res)
    if slope == PL.SLOPE_DEG:
        open(os.path.join(OUT, "tables.md"), "w").write(md)
    print(md)
    s = res["summary"]
    ok = s["reachable"] == s["targets"] and s["collision_free"] == s["targets"]
    print("ALL PICKS REACHABLE AND COLLISION FREE" if ok else "SOME PICKS FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
