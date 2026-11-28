"""Reach, torque and clearance tables for the 26 Nov pod grab layout (OpenPocket #522 follow-up): sim/pod_grab.py with layout="roll".

    pip install mujoco numpy imageio imageio-ffmpeg
    python3 sim/pod_grab_roll_check.py                 # tables -> docs/pod-grab-reach/results-roll.json and tables-roll.md
    MUJOCO_GL=egl python3 sim/pod_grab_roll_check.py --clip     # the tour clip + tour-roll.json

Cases: (a) tray with the cart rolled 45 degrees, (b) tray with the cart upright, (c) store front row upright. Pods stay vertical; the claw is
"vertical" when it is within `tilt_tol_deg` (3) of straight down. For every cell: reachable or not, margin, joint angles against the limits,
holding torque with the pod and 400 g lettuce against the STS3215 stall, and the smallest distance of the arm and of the cart to everything else.
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
OUT = os.path.join(HERE, "..", "docs", "pod-grab-reach")
DEG = math.degrees
ARM_GEOMS = ("shoulder_housing", "upper_arm", "forearm", "wrist_housing", "gripper_body", "gripper_tip")
CLAW = ("gripper_body", "gripper_tip", "wrist_housing")   # these go down through the pick hole in the lid
CART = ("plate", "battery", "sleeve", "hand_arm")
JN = ("shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex")
CASES = {"tray_rolled": (G.CELLS_TRAY, 45.0), "tray_upright": (G.CELLS_TRAY, 0.0), "store_upright": (G.CELLS_STORE, 0.0)}


def params(**kw):
    p = {k: v[0] for k, v in G.PARAMS.items()}
    p.update(layout="roll")
    p.update(kw)
    return p


def feasible(park, roll, tgt, cap, battery="none"):
    origin, R = G.base_frame(park, roll, battery)
    pan, tx, tz = G.to_plane(R, origin, tgt)
    return bool(G.candidates(R, pan, tx, tz, cap))


def slack_mm(park, roll, tgt, cap, battery="none"):
    """Reachable band along the horizontal line from the arm's pan axis through the target: (mm closer, mm further, miss). Both slacks are 0..250;
    miss is 0 when the target is reachable, else the signed shift (mm, + = further) to the nearest reachable spot."""
    origin, R = G.base_frame(park, roll, battery)
    pan_axis = origin + R @ np.array([G.PAN_X * 1000.0, 0.0, 0.0])
    d = np.array([tgt[0] - pan_axis[0], tgt[1] - pan_axis[1], 0.0])
    d = d / (np.linalg.norm(d) or 1.0)

    def ok(s):
        return feasible(park, roll, tuple(np.array(tgt) + s * d), cap, battery)
    if ok(0):
        out = []
        for sign in (-1, 1):
            s = 0
            while s < 250 and ok(sign * (s + 4)):
                s += 4
            while s < 250 and ok(sign * (s + 1)):
                s += 1
            out.append(float(s))
        return out[0], out[1], 0.0
    for s in range(1, 251):
        for sign in (-1, 1):
            if ok(sign * s):
                return None, None, float(sign * s)
    return None, None, None


def dist(model, data, a, b):
    fromto = np.zeros(6)
    return float(mujoco.mj_geomDistance(model, data, a, b, 1.0, fromto)) * 1000.0


def groups(model):
    """Geom ids: arm, cart, and the environment split by what it is."""
    g = {k: [] for k in ("arm", "cart", "pillar", "station", "lid", "pipe", "tray", "store", "pods")}
    for i in range(model.ngeom):
        n = model.geom(i).name
        if n in ARM_GEOMS:
            g["arm"].append(i)
        elif n in CART:
            g["cart"].append(i)
        elif n == "pillar":
            g["pillar"].append(i)
        elif n.startswith("station"):
            g["station"].append(i)
        elif n == "lid":
            g["lid"].append(i)
        elif n == "track_pipe":
            g["pipe"].append(i)
        elif n == "tray":
            g["tray"].append(i)
        elif n == "store_shelf":
            g["store"].append(i)
        elif n.startswith("pod_") or n.startswith("store_pod"):
            g["pods"].append(i)
    return g


def clearances(model, data, target, grp):
    """Smallest distance (mm; negative = inside) per pair of groups, with the two geoms. The pod being picked is left out (the claw closes on it)."""
    skip = model.geom(f"pod_{target}").id
    res = {}

    def best(A, B, label, drop=()):
        b = (1e9, "")
        for a in A:
            if model.geom(a).name in drop:
                continue
            for e in B:
                if e == skip:
                    continue
                v = dist(model, data, a, e)
                if v < b[0]:
                    b = (v, f"{model.geom(a).name} / {model.geom(e).name}")
        res[label] = {"mm": round(b[0], 1), "between": b[1]}
    arm, cart = grp["arm"], grp["cart"] + grp["pipe"]
    best(arm, cart, "arm_to_cart_and_pipe", drop=("shoulder_housing",))      # the shoulder housing sits on the plate by design
    best(arm, grp["pillar"], "arm_to_pillar")
    best(arm, grp["station"], "arm_to_station")
    best(arm, grp["tray"] + grp["store"], "arm_to_tray_and_store_shelf")
    best(arm, grp["pods"], "arm_to_other_pods")
    best([i for i in arm if model.geom(i).name not in CLAW], grp["lid"], "forearm_upper_arm_shoulder_to_lid")
    best(grp["cart"], grp["lid"], "cart_to_lid")
    best(grp["cart"], grp["pillar"], "cart_to_pillar")
    best(grp["cart"], grp["station"], "cart_to_station")
    best(grp["cart"], grp["tray"] + grp["store"] + grp["pods"], "cart_to_tray_store_pods")
    # the claw through the lid: how deep below the lid top it goes (needs a pick hole at least as wide as the claw)
    res["below_lid_top_mm"] = {model.geom(i).name: round(G.LID_TOP - lowest_z(model, data, i), 1) for i in grp["arm"] if model.geom(i).name in CLAW}
    return res


def lowest_z(model, data, i):
    """Lowest world z (mm) of an arm geom (box or capsule)."""
    pos, mat, size = data.geom_xpos[i], data.geom_xmat[i].reshape(3, 3), model.geom_size[i]
    if model.geom_type[i] == mujoco.mjtGeom.mjGEOM_CAPSULE:
        ends = [pos + mat @ np.array([0, 0, s * size[1]]) for s in (-1, 1)]
        return min(float(e[2]) for e in ends) * 1000.0 - size[0] * 1000.0
    corners = [pos + mat @ (np.array([a, b, c]) * size) for a in (-1, 1) for b in (-1, 1) for c in (-1, 1)]
    return min(float(c[2]) for c in corners) * 1000.0


def set_pose(model, data, park, roll, pose):
    data.qpos[:] = 0
    data.qpos[model.joint("cart_x").qposadr[0]] = (park + G.PARK_X) / 1000.0
    data.qpos[model.joint("roll").qposadr[0]] = math.radians(roll)
    for n, v in zip(JN, pose):
        data.qpos[model.joint(n).qposadr[0]] = v
    mujoco.mj_forward(model, data)


def analyse_cell(p, models, name, roll, tol):
    x, y, z, park = G.cell_target(p, name)
    tgt = (x, y, z)
    bat = p["battery"] if p["battery"] == "under_arm" else "none"
    sol = G.solve(park, roll, tgt, tol, bat)
    out = {"cell": name, "target_mm": [x, y, z], "park_x_mm": park, "roll_deg": roll, "pan_deg": round(DEG(sol["pan"]), 1)}
    best = sol["vertical"] or sol["minimal"]
    out["reachable"] = bool(best)
    out["vertical_claw"] = bool(sol["vertical"])
    out["min_tilt_deg"] = round(best[0], 1) if best else None
    m_v = slack_mm(park, roll, tgt, tol, bat)
    own = max(tol, (best[0] if best else 0.0) + 3.0)               # the claw tilt this cell needs, plus 3 degrees of play
    m_10 = slack_mm(park, roll, tgt, own, bat)
    out["tilt_allowed_for_margin_deg"] = round(own, 1)
    for tag, m in (("vertical", m_v), ("own_tilt_plus_3", m_10)):
        out[f"slack_{tag}_mm"] = {"closer": m[0], "further": m[1], "margin": (min(m[0], m[1]) if m[0] is not None else -abs(m[2]) if m[2] is not None else None)}
    pose = sol["pose"]
    out["joints_deg"] = {n: round(DEG(v), 1) for n, v in zip(JN, pose)}
    out["joint_margin_deg"] = {n: round(DEG(min(v - G.LIMITS[n][0], G.LIMITS[n][1] - v)), 1) for n, v in zip(JN, pose)}
    out["tightest_joint"] = min(out["joint_margin_deg"], key=out["joint_margin_deg"].get)
    out["tightest_joint_margin_deg"] = out["joint_margin_deg"][out["tightest_joint"]]
    if not best:
        out["nearest_pose_miss_mm"] = round(sol["miss_mm"], 1)
    loaded, unloaded = models
    for tag, mdl in (("loaded", loaded), ("unloaded", unloaded)):
        d = mujoco.MjData(mdl)
        set_pose(mdl, d, park, roll, pose)
        out[f"torque_{tag}_nm"] = {n: round(abs(float(d.qfrc_bias[mdl.joint(n).dofadr[0]])), 2) for n in JN}
        if tag == "loaded":
            out["tcp_error_mm"] = round(float(np.linalg.norm(d.site_xpos[mdl.site("tcp").id] * 1000 - np.array(tgt))), 1)
            out["clearance"] = clearances(mdl, d, name, groups(mdl))
    tq = out["torque_loaded_nm"]
    out["max_torque_nm"] = max(tq.values())
    out["max_torque_joint"] = max(tq, key=tq.get)
    out["torque_vs_stall_7v4"] = round(out["max_torque_nm"] / 1.9, 2)
    out["torque_vs_stall_12v"] = round(out["max_torque_nm"] / 2.9, 2)
    return out


def lowest_corner_table():
    """Cart's lowest point over the lid vs roll angle: the plate (CAD 168 x 146), the CAD battery stack and a CAD 'deepest part' stand-in (see the doc)."""
    rows = []
    face, bot = G.FACE_REL, G.PLATE_CZ_REL - G.PLATE_DOWN / 2
    pts = {"plate_bottom_front_corner": (face, bot), "plate_bottom_back_corner": (face + G.PLATE_T, bot),
           "battery_stack_bottom_front": (face - G.BATT[1], G.PLATE_CZ_REL - G.BATT[2] / 2),
           "CAD_deepest_part_standin (165 under the pipe, 90 out)": (-90.0, -165.0)}
    for roll in (0, 15, 30, 45, 60):
        a = math.radians(roll)
        row = {"roll_deg": roll}
        for k, (y, z) in pts.items():
            zz = y * math.sin(a) + z * math.cos(a)                       # height of the point relative to the pipe axis after the roll
            row[k] = {"depth_under_pipe_mm": round(-zz, 1), "gap_to_lid_mm": round(G.PIPE_Z + zz - G.LID_TOP, 1)}
        rows.append(row)
    return rows


def pillar_station_table(p, models):
    """Smallest cart-to-pillar and cart-to-station distance for park x and roll."""
    mdl = models[0]
    grp = groups(mdl)
    rows = []
    for park in (-140.0, -130.0, -120.0, -110.0):
        for roll in (0.0, 45.0):
            d = mujoco.MjData(mdl)
            set_pose(mdl, d, park, roll, (0.0,) + G.SAFE)
            r = {"park_x_mm": park, "roll_deg": roll}
            for lab, B in (("pillar", grp["pillar"]), ("station", grp["station"])):
                b = min((dist(mdl, d, a, e), f"{mdl.geom(a).name} / {mdl.geom(e).name}") for a in grp["cart"] for e in B)
                r[f"cart_to_{lab}_mm"] = round(b[0], 1)
                r[f"cart_to_{lab}_between"] = b[1]
            rows.append(r)
    return rows


def roll_sweep(p, cells):
    """Least claw tilt per cell for roll angles 0..60 (park -130 / +130, brief heights)."""
    out = {}
    for n in cells:
        x, y, z, park = G.cell_target(p, n)
        out[n] = {}
        for roll in (0, 10, 20, 30, 45, 60):
            s = G.solve(park, roll, (x, y, z))
            out[n][roll] = None if s["tilt"] is None else round(s["tilt"], 1)
    return out


def sideways_allowance(p):
    """Upright cart parked at -130: how far to the side (mm) a pod can be from the cart's centre line, per tray row, with the claw within 3 / 10 / 15 degrees of vertical."""
    out = {}
    for i, row in enumerate(G.ROW_NAMES):
        y = G.TRAY_ROWS_Y[i] - float(p["tray_shift_mm"])
        out[row] = {}
        for cap in (3, 10, 15):
            ok = 0
            for d in range(0, 200):
                s = G.solve(-G.PARK_X, 0.0, (-G.PARK_X - d, y, G.TRAY_POD_TOP), cap)
                if s["tilt"] is not None and s["tilt"] <= cap:
                    ok = d
                elif d > ok + 15:
                    break
            out[row][f"{cap}_deg"] = ok
    return out


def summary(p, cells, roll):
    """Reachability only (no MuJoCo): vertical claw / min tilt for each cell."""
    r = {}
    for n in cells:
        x, y, z, park = G.cell_target(p, n)
        s = G.solve(park, roll, (x, y, z), float(p["tilt_tol_deg"]), p["battery"] if p["battery"] == "under_arm" else "none")
        r[n] = None if s["tilt"] is None else round(s["tilt"], 1)
    return r


def run_all():
    res = {"cases": {}, "variants": {}}
    p = params()
    tol = float(p["tilt_tol_deg"])
    models = (mujoco.MjModel.from_xml_string(G.build(**p)), mujoco.MjModel.from_xml_string(G.build(**dict(p, load_kg=0.0))))
    for case, (cells, roll) in CASES.items():
        res["cases"][case] = [analyse_cell(p, models, n, roll, tol) for n in cells]
        print(case, [(c["cell"], c["min_tilt_deg"], c["max_torque_nm"]) for c in res["cases"][case]], flush=True)
    res["lowest_corner"] = lowest_corner_table()
    res["pillar_station"] = pillar_station_table(p, models)
    res["roll_sweep"] = roll_sweep(p, ("A1", "A4", "B2", "D1", "D4", "S1", "S5"))
    res["sideways_allowance_mm"] = sideways_allowance(p)
    for tag, kw in (("tray_shift_10", dict(tray_shift_mm=10.0)), ("pods_30mm_higher_CAD_cell_tops", dict(pod_dz_mm=30.0)), ("battery_under_arm_CAD", dict(battery="under_arm"))):
        pv = params(**kw)
        res["variants"][tag] = {c: summary(pv, cells, roll) for c, (cells, roll) in CASES.items()}
        print(tag, res["variants"][tag], flush=True)
    return res


def intervals(times, gap=0.3):
    """Sample times (s) -> 'a-b s' runs, a new run after a gap longer than `gap`."""
    runs, lo, prev = [], times[0], times[0]
    for t in times[1:]:
        if t - prev > gap:
            runs.append(f"{lo}-{prev} s")
            lo = t
        prev = t
    runs.append(f"{lo}-{prev} s")
    return runs


def tour(p, clip=None, fps=25):
    """Play the tour with torque-limited position servos and the 400 g load. Records closest grip point to each visited cell, peak servo torque and contacts."""
    model = mujoco.MjModel.from_xml_string(G.build(**p))
    data = mujoco.MjData(model)
    ctrl, total = G.make_controls_roll(p)
    sched = [(model.actuator(n).id, steps) for n, steps in ctrl.items()]
    sid = model.site("tcp").id
    grp = groups(model)
    stall = float(p["stall_nm"])
    peak = {n: 0.0 for n in JN}
    sat = {n: 0 for n in JN}
    hits = {}
    cl = {"cart_to_lid_mm": 1e9, "cart_to_pillar_mm": 1e9, "cart_to_station_mm": 1e9}
    writer = renderer = None
    if clip:
        import imageio
        renderer = mujoco.Renderer(model, 270, 480)
        writer = imageio.get_writer(clip, fps=fps, codec="libx264", quality=7, macro_block_size=1)
    idx = [0] * len(sched)
    every = int(round(1.0 / (fps * model.opt.timestep)))
    armset = set(grp["arm"])
    for step in range(int(total / model.opt.timestep)):
        t = data.time
        for k, (aid, steps) in enumerate(sched):
            while idx[k] + 1 < len(steps) and steps[idx[k] + 1][0] <= t:
                idx[k] += 1
            data.ctrl[aid] = steps[idx[k]][1]
        mujoco.mj_step(model, data)
        if step % 10 == 0:
            for n in JN:
                f = abs(float(data.actuator_force[model.actuator(n + "_servo").id]))
                peak[n] = max(peak[n], f)
                sat[n] += f >= 0.98 * stall
            for i in range(data.ncon):
                c = data.contact[i]
                a, b = int(c.geom1), int(c.geom2)
                if (a in armset) != (b in armset):
                    key = f"{model.geom(a if a in armset else b).name} / {model.geom(b if a in armset else a).name}"
                    hits.setdefault(key, []).append(round(t, 2))
        if step % 100 == 0:
            for lab, B in (("lid", grp["lid"]), ("pillar", grp["pillar"]), ("station", grp["station"])):
                cl[f"cart_to_{lab}_mm"] = min(cl[f"cart_to_{lab}_mm"], min(dist(model, data, a, e) for a in grp["cart"] for e in B))
        if writer and step % every == 0:
            tiles = []
            for cn in ("front", "side", "iso", "top"):
                renderer.update_scene(data, camera=cn)
                tiles.append(renderer.render().copy())
            writer.append_data(np.vstack([np.hstack(tiles[:2]), np.hstack(tiles[2:])]))
    if writer:
        writer.close()
    return {"seconds": round(total, 1), "peak_servo_nm": {k: round(v, 2) for k, v in peak.items()}, "saturated_samples": sat,
            "arm_contacts_with_scene": {k: intervals(v) for k, v in hits.items()},
            "cart_min_clearance_mm": {k: round(v, 1) for k, v in cl.items()}}


def main():
    os.makedirs(OUT, exist_ok=True)
    if "--clip" in sys.argv:
        res = {}
        for name in ("tray", "store"):
            res[name] = tour(params(tour=name), clip=os.path.join(OUT, f"pod-grab-roll-tour-{name}.mp4"))
            print(name, res[name])
        json.dump(res, open(os.path.join(OUT, "tour-roll.json"), "w"), indent=1)
        return
    res = run_all()
    json.dump(res, open(os.path.join(OUT, "results-roll.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
