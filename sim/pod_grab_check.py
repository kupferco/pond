"""Reach table for sim/pod_grab.py (OpenPocket #522). Not a sandbox model: run it on your machine.

    pip install mujoco numpy imageio imageio-ffmpeg
    python3 sim/pod_grab_check.py [out_dir]          # table + docs/pod-grab-reach/results.json; clip with --clip

For every tray row (A..D) and the store pick (S), for tray shift 0 (today) and 10 mm (proposal v3), it drives the real SO-101
(planar inverse kinematics in sim/pod_grab.py, joint limits from the URDF) to grip height with the claw straight down and with a tilt,
then loads the same pose into the MuJoCo model and reads: joint angles against the limits, servo holding torque with the pod and
lettuce in the claw against the STS3215 stall torque, and every arm geom against the cart plate, pipe, battery, water station, tray
and neighbouring pods (contact or clearance in mm).
"""
import importlib.util
import json
import math
import os
import sys

import mujoco

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("pod_grab", os.path.join(HERE, "pod_grab.py"))
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)

ARM_GEOMS = ("shoulder_housing", "upper_arm", "forearm", "wrist_housing", "gripper_body", "gripper_tip")
ENV_PREFIX_SKIP = ("lettuce", "load", "lid", "floor")
DEG = math.degrees


def defaults(**kw):
    p = {k: v[0] for k, v in G.PARAMS.items()}
    p.update(kw)
    return p


def feasible(p, y, z, phi):
    tx, tz = G.target_plane(p, y, z)
    return G.ik(tx, tz, phi)


def window_mm(p, y, z, phi):
    """The reachable band along Y for this tool angle: (slack towards the arm, slack away from it), mm, when the target is reachable;
    otherwise (None, None) and the signed distance to the nearest reachable spot as the third value (negative = move towards the arm)."""
    def ok(s):
        return feasible(p, y + s, z, phi) is not None
    if ok(0):
        a = 0
        while a < 250 and ok(-a - 1):
            a += 1
        b = 0
        while b < 250 and ok(b + 1):
            b += 1
        return float(a), float(b), 0.0
    for s in range(1, 251):
        if ok(-s):
            return None, None, -float(s)
        if ok(s):
            return None, None, float(s)
    return None, None, None


def margin_mm(p, y, z, phi):
    """Smallest slack to either edge of the reachable band (mm); negative = how far the target must move to get into it."""
    a, b, miss = window_mm(p, y, z, phi)
    return min(a, b) if a is not None else (-abs(miss) if miss is not None else None)


def min_tilt(p, y, z, want=5.0):
    """Smallest claw tilt (deg, either sign) that reaches the target with at least `want` mm of slack on both sides."""
    for a in range(0, 61):
        for sgn in (1, -1):
            m = margin_mm(p, y, z, math.radians(sgn * a))
            if m is not None and m >= want:
                return sgn * a, m
    return None


def analyse(p, name, tilt_deg):
    pp = dict(p, tilt_deg=float(tilt_deg), pod_contact=1)
    x, y, z = G.targets(pp)[name]
    q, ok = G.pose_for(pp, y, z)
    model = mujoco.MjModel.from_xml_string(G.build(**pp))
    unloaded = mujoco.MjModel.from_xml_string(G.build(**dict(pp, load_kg=0.0)))
    out = {"target": name, "tilt_deg": tilt_deg, "reachable": ok, "margin_mm": margin_mm(pp, y, z, math.radians(tilt_deg)),
           "joints_deg": {n: round(DEG(v), 1) for n, v in zip(("shoulder_lift", "elbow_flex", "wrist_flex"), q)}}
    out["joint_margin_deg"] = round(DEG(G.joint_margin(q)), 1)
    t = G.fk(*q)[2]
    tx, tz = G.target_plane(pp, y, z)
    out["tip_error_mm"] = round(1000 * math.hypot(t[0] - tx, t[1] - tz), 1)
    out["tool_angle_deg"] = round(DEG(sum(q)), 1)
    names = ("shoulder_lift", "elbow_flex", "wrist_flex")
    for tag, mdl in (("loaded", model), ("unloaded", unloaded)):
        d = mujoco.MjData(mdl)
        for n, v in zip(names, q):
            d.qpos[mdl.joint(n).qposadr[0]] = v
        d.qpos[mdl.joint("cart_x").qposadr[0]] = (x - G.TRAY_X) / 1000.0   # the cart stops at the target's X
        mujoco.mj_forward(mdl, d)
        out[f"torque_{tag}_nm"] = {n: round(abs(float(d.qfrc_bias[mdl.joint(n).dofadr[0]])), 2) for n in names}
        if tag == "loaded":
            out["collisions"], out["clearance_mm"], out["closest"] = contacts(mdl, d, name)
    stall = float(pp["stall_nm"])
    out["max_torque_loaded_nm"] = max(out["torque_loaded_nm"].values())
    out["torque_ok"] = out["max_torque_loaded_nm"] <= stall
    return out


def contacts(model, data, target):
    """(names of arm geoms that touch something other than the target pod, smallest clearance in mm and what it is to)."""
    arm = {model.geom(n).id for n in ARM_GEOMS}
    env = [g for g in range(model.ngeom) if g not in arm and model.geom_contype[g] == 2
           and model.geom(g).name != ("pod_S" if target == "S" else f"pod_{target}1") and not model.geom(g).name.startswith(ENV_PREFIX_SKIP)]
    hits, best = [], (1e9, "")
    import numpy as np
    fromto = np.zeros(6)
    for a in arm:
        for e in env:
            dist = mujoco.mj_geomDistance(model, data, a, e, 0.1, fromto)
            if dist < best[0]:
                best = (dist, f"{model.geom(a).name} / {model.geom(e).name}")
            if dist < 0:
                hits.append(f"{model.geom(a).name} / {model.geom(e).name} ({-dist * 1000:.0f} mm into)")
    return hits, round(best[0] * 1000, 1) if best[0] < 1e8 else None, best[1]


def run_all():
    rows = []
    for battery in ("beside", "under_arm"):
        for shift in (0.0, 10.0):
            p = defaults(tray_shift_mm=shift, battery=battery)
            for name in ("A", "B", "C", "D", "S"):
                x, y, z = G.targets(p)[name]
                straight = analyse(p, name, 0)
                mt = min_tilt(p, y, z)
                rows.append({"battery": battery, "tray_shift_mm": shift, "straight": straight,
                             "tilts": {str(a): analyse(p, name, a) for a in (5, 10, 15, 20)},
                             "min_tilt": ({"tilt_deg": mt[0], **analyse(p, name, mt[0])} if mt else None)})
    # reading of the brief: the water station box over the store pick (CAD has it 160 mm behind it, y 14..114)
    for shift in (0.0, 10.0):
        p = defaults(tray_shift_mm=shift, station_y0_mm=-197.0)
        x, y, z = G.targets(p)["S"]
        rows.append({"battery": "beside", "tray_shift_mm": shift, "station_over_store": True, "straight": analyse(p, "S", 0),
                     "tilts": {str(a): analyse(p, "S", a) for a in (5, 10, 15, 20)}, "min_tilt": None})
    return rows


def rough_check():
    """The brief's rough numbers (120/130/100, claw straight down, shoulder 88 out at y -204, z 519), for comparison."""
    out = {}
    for shift in (0.0, 10.0):
        for i, n in enumerate("ABCD"):
            y = G.TRAY_ROWS_Y[i] - shift
            out[f"{n}@{int(shift)}"] = round(math.hypot(y - (-204.0), (G.TRAY_POD_TOP + 100) - 519.0), 1)
    return out


def tour(p, clip=None, fps=25):
    """Play the whole tour in MuJoCo (position servos, torque-limited, 400 g load): closest approach of the grip point to each target,
    peak servo torque, arm contacts with anything but the target pods, and optionally a 2 x 2 clip (front, side, iso, top)."""
    import numpy as np
    xml = G.build(**p)
    model = mujoco.MjModel.from_xml_string(xml)
    data = mujoco.MjData(model)
    ctrl, total = G.make_controls(p)
    sched = []
    for n, steps in ctrl.items():
        sched.append((model.actuator(n).id, steps))
    tg = G.targets(p)
    sid = model.site("tcp").id
    arm = {model.geom(n).id for n in ARM_GEOMS}
    stall = float(p["stall_nm"])
    best = {k: 1e9 for k in tg}
    peak = {n: 0.0 for n in ("shoulder_lift", "elbow_flex", "wrist_flex")}
    sat = {n: 0 for n in peak}
    hits = {}
    renderer = writer = None
    cams = ("front", "side", "iso", "top")
    if clip:
        import imageio
        renderer = mujoco.Renderer(model, 270, 480)
        writer = imageio.get_writer(clip, fps=fps, codec="libx264", quality=7, macro_block_size=1)
    idx = [0] * len(sched)
    n_steps = int(total / model.opt.timestep)
    every = int(round(1.0 / (fps * model.opt.timestep)))
    for step in range(n_steps):
        t = data.time
        for k, (aid, steps) in enumerate(sched):
            while idx[k] + 1 < len(steps) and steps[idx[k] + 1][0] <= t:
                idx[k] += 1
            data.ctrl[aid] = steps[idx[k]][1]
        mujoco.mj_step(model, data)
        if step % 10 == 0:
            tcp = data.site_xpos[sid] * 1000
            for k, (x, y, z) in tg.items():
                best[k] = min(best[k], float(np.linalg.norm(tcp - np.array([x, y, z]))))
            for n in peak:
                f = abs(float(data.actuator_force[model.actuator(n + "_servo").id]))
                peak[n] = max(peak[n], f)
                sat[n] += f >= 0.98 * stall
            for i in range(data.ncon):
                c = data.contact[i]
                a, b = int(c.geom1), int(c.geom2)
                if (a in arm) != (b in arm):
                    o = model.geom(b if a in arm else a).name
                    if not o.startswith("pod_"):
                        key = f"{model.geom(a if a in arm else b).name} / {o}"
                        lo, hi, n = hits.get(key, (t, t, 0))
                        hits[key] = (lo, t, n + 1)
        if writer and step % every == 0:
            tiles = []
            for cn in cams:
                renderer.update_scene(data, camera=cn)
                tiles.append(renderer.render().copy())
            writer.append_data(np.vstack([np.hstack(tiles[:2]), np.hstack(tiles[2:])]))
    if writer:
        writer.close()
    return {"closest_to_target_mm": {k: round(v, 1) for k, v in best.items()},
            "peak_servo_nm": {k: round(v, 2) for k, v in peak.items()},
            "saturated_samples": sat, "arm_contacts_with_scene": {k: f"{v[0]:.1f}-{v[1]:.1f} s, {v[2]} samples" for k, v in hits.items()}, "seconds": round(total, 1)}


def main():
    if "--clip" in sys.argv:
        out_dir = os.path.join(HERE, "..", "docs", "pod-grab-reach")
        os.makedirs(out_dir, exist_ok=True)
        res = {}
        only = sys.argv[sys.argv.index("--clip") + 1] if len(sys.argv) > sys.argv.index("--clip") + 1 else None
        for name, shift, tilt in (("proposal-straight-down", 10.0, 0.0), ("proposal-tilt-10", 10.0, 10.0), ("today-tilt-10", 0.0, 10.0)):
            if only and only != name:
                continue
            p = defaults(tray_shift_mm=shift, tilt_deg=tilt)
            res[name] = tour(p, clip=os.path.join(out_dir, f"pod-grab-{name}.mp4"))
            print(name, res[name])
        with open(os.path.join(out_dir, f"tour-{only or 'all'}.json"), "w") as fh:
            json.dump(res, fh, indent=1)
        return
    rows = run_all()
    out_dir = os.path.join(HERE, "..", "docs", "pod-grab-reach")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "results.json"), "w") as fh:
        json.dump({"rough_check_brief": rough_check(), "rows": rows}, fh, indent=1)
    print("brief's rough reach (120/130/100):", rough_check())
    for r in rows:
        for tag, a in [("straight", r["straight"])] + [(f"tilt{k}", v) for k, v in r["tilts"].items()] + [("min", r["min_tilt"])]:
            if a is None:
                print(r["battery"], r["tray_shift_mm"], tag, "no tilt reaches")
                continue
            print(r["battery"], int(r["tray_shift_mm"]), a["target"], tag, f"tilt {a['tilt_deg']}", "REACH" if a["reachable"] else "no",
                  f"margin {a['margin_mm']}", a["joints_deg"], f"jm {a['joint_margin_deg']}", f"err {a['tip_error_mm']}",
                  f"tq {a['max_torque_loaded_nm']}", "coll", a["collisions"], "clr", a["clearance_mm"], a["closest"])


if __name__ == "__main__":
    main()
