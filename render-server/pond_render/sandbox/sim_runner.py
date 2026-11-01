"""MuJoCo sandbox runner. Executed as a separate process by host.py:

    python -I sim_runner.py <job.json>

Self-contained on purpose (like runner.py): with `-I` nothing from the server package is
importable. The job carries either a finished MJCF string or a Python *generator* (a
`sim/<name>.py` from the repo) plus params; the generator runs under the same import
guard as CAD scripts and must return the MJCF from `build(**params)`.

Outputs in <out_dir>: model.xml, signals.csv, sheet_<camera>.png (a grid of snapshots),
clip_<camera>.mp4 when recording, and result.json with a summary of every logged signal.
"""

from __future__ import annotations

import builtins
import csv
import io
import json
import math
import os
import re
import sys
import time
import traceback

SCRIPT_NAME = "__pond_script__"
SCRIPT_FILENAME = "<sim_model>"

ALLOWED_MODULES = frozenset(
    {
        "math", "cmath", "itertools", "functools", "operator", "typing", "dataclasses",
        "collections", "enum", "copy", "random", "statistics", "numpy", "json",
        "xml", "xml.etree", "xml.etree.ElementTree", "textwrap", "string",
    }
)
REMOVED_BUILTINS = ("open", "exec", "eval", "compile", "input", "breakpoint", "exit", "quit", "help", "memoryview")

FORBIDDEN_XML = (
    (re.compile(r"<\s*include\b", re.I), "<include> is not allowed; put everything in one MJCF string"),
    (re.compile(r"\bfile\s*=", re.I), "file= attributes are not allowed; use primitive geoms (mesh/texture files come later)"),
    (re.compile(r"\bmeshdir\s*=|\btexturedir\s*=|\bassetdir\s*=", re.I), "asset directories are not allowed"),
    (re.compile(r"<\s*plugin\b", re.I), "plugins are not allowed"),
)

MAX_SIM_SECONDS = 60.0
MAX_VIDEO_FRAMES = 1800
LOG_HZ = 100.0


# ----------------------------------------------------------------------------- limits / guard


def apply_limits(memory_mb: int, cpu_s: int) -> None:
    try:
        import resource
    except ImportError:  # pragma: no cover
        return

    def _set(name, soft, hard=None):
        limit = getattr(resource, name, None)
        if limit is None:
            return
        try:
            cur_soft, cur_hard = resource.getrlimit(limit)
            hard_val = hard if hard is not None else soft
            if cur_hard != resource.RLIM_INFINITY:
                soft = min(soft, cur_hard)
                hard_val = min(hard_val, cur_hard)
            resource.setrlimit(limit, (soft, hard_val))
        except (ValueError, OSError):
            pass

    _set("RLIMIT_CORE", 0, 0)
    _set("RLIMIT_CPU", cpu_s, cpu_s + 5)
    _set("RLIMIT_FSIZE", 512 * 1024 * 1024)
    if sys.platform.startswith("linux"):
        _set("RLIMIT_AS", memory_mb * 1024 * 1024)


SUPPORT_MODULES: set[str] = set()


def register_support_modules(sources: dict) -> None:
    """Make repo helper files (e.g. sim/constants.py) importable by the generator by name."""
    import types

    for name, source in (sources or {}).items():
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            raise ValueError(f"bad support module name {name!r}")
        mod = types.ModuleType(name)
        mod.__dict__["__builtins__"] = make_script_builtins()
        exec(compile(source, f"<{name}>", "exec"), mod.__dict__)
        sys.modules[name] = mod
        SUPPORT_MODULES.add(name)


def install_import_guard() -> None:
    real_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        importer = (globals or {}).get("__name__")
        if importer == SCRIPT_NAME:
            if level != 0:
                raise ImportError("Relative imports are not allowed in sim models")
            top = name.split(".", 1)[0]
            if name in SUPPORT_MODULES:
                return real_import(name, globals, locals, fromlist, level)
            if name not in ALLOWED_MODULES and top not in ALLOWED_MODULES:
                raise ImportError(
                    f"Importing {name!r} is not allowed in a sim model. Allowed: {', '.join(sorted(ALLOWED_MODULES))}"
                )
        return real_import(name, globals, locals, fromlist, level)

    builtins.__import__ = guarded_import


def make_script_builtins() -> dict:
    safe = dict(vars(builtins))
    for name in REMOVED_BUILTINS:
        safe.pop(name, None)
    return safe


def trimmed_traceback(exc: BaseException) -> str:
    frames = [f for f in traceback.extract_tb(exc.__traceback__) if f.filename == SCRIPT_FILENAME]
    lines = []
    if frames:
        lines.append("Traceback (most recent call last):\n")
        lines.extend(traceback.format_list(frames))
    lines.extend(traceback.format_exception_only(type(exc), exc))
    return "".join(lines).rstrip()


# ----------------------------------------------------------------------------- generator


def build_from_generator(source: str, params: dict, log_buffer: io.StringIO, support: dict | None = None) -> tuple[str, dict]:
    """Run a sim model script and return (mjcf, defaults). The script defines PARAMS and build()."""
    install_import_guard()
    g = {"__name__": SCRIPT_NAME, "__builtins__": make_script_builtins(), "math": math}
    register_support_modules(support)
    real_stdout, real_stderr = sys.stdout, sys.stderr
    sys.stdout = sys.stderr = log_buffer
    try:
        exec(compile(source, SCRIPT_FILENAME, "exec"), g)
        build = g.get("build")
        if not callable(build):
            raise ValueError("The sim model must define `def build(**params) -> str` returning MJCF XML")
        raw = g.get("PARAMS") or {}
        defaults = {k: (v[0] if isinstance(v, (tuple, list)) else v) for k, v in raw.items()}
        unknown = sorted(set(params) - set(defaults))
        if unknown:
            raise ValueError(f"Unknown params {unknown}; this model takes {sorted(defaults)}")
        merged = {**defaults, **params}
        xml = build(**merged)
        if not isinstance(xml, str) or "<mujoco" not in xml:
            raise ValueError("build() must return an MJCF XML string containing <mujoco>")
        controls = g.get("DEFAULT_CONTROLS") or {}
        cameras = list(g.get("CAMERAS") or [])
        track = g.get("TRACK_BODY")
        return xml, {"params": merged, "controls": controls, "cameras": cameras, "track_body": track}
    finally:
        sys.stdout, sys.stderr = real_stdout, real_stderr


# ----------------------------------------------------------------------------- simulation


def check_xml(xml: str) -> None:
    for pattern, message in FORBIDDEN_XML:
        if pattern.search(xml):
            raise ValueError(message)
    if len(xml) > 2_000_000:
        raise ValueError("MJCF is larger than 2 MB")


class ControlSchedule:
    """ctrl per actuator: a constant, or [[t, value], ...] held piecewise-constant."""

    def __init__(self, model, spec: dict, mujoco):
        self.entries = []
        for name, value in (spec or {}).items():
            aid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, str(name))
            if aid < 0:
                names = [model.actuator(i).name for i in range(model.nu)]
                raise ValueError(f"No actuator named {name!r}; actuators: {names}")
            if isinstance(value, (int, float)):
                steps = [(0.0, float(value))]
            else:
                steps = sorted((float(t), float(v)) for t, v in value)
            self.entries.append((aid, steps))

    def apply(self, data, t: float) -> None:
        for aid, steps in self.entries:
            val = steps[0][1]
            for ts, v in steps:
                if t >= ts:
                    val = v
                else:
                    break
            data.ctrl[aid] = val


def make_camera(model, name: str, track_body_id: int, mujoco):
    cam = mujoco.MjvCamera()
    extent = float(model.stat.extent) or 1.0
    center = [float(c) for c in model.stat.center]
    if name == "track" and track_body_id >= 0:
        cam.type = mujoco.mjtCamera.mjCAMERA_TRACKING
        cam.trackbodyid = track_body_id
        cam.distance = 2.0 * extent
        cam.azimuth, cam.elevation = 135.0, -15.0
        return cam
    if name in ("free", "overview", "track"):
        cam.type = mujoco.mjtCamera.mjCAMERA_FREE
        cam.lookat[:] = center
        cam.distance = 2.2 * extent
        cam.azimuth, cam.elevation = 135.0, -20.0
        return cam
    cid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_CAMERA, name)
    if cid < 0:
        names = [model.camera(i).name for i in range(model.ncam)]
        raise ValueError(f"No camera named {name!r}; model cameras: {names}; built-ins: track, free")
    cam.type = mujoco.mjtCamera.mjCAMERA_FIXED
    cam.fixedcamid = cid
    return cam


def contact_sheet(frames: list, cols: int | None = None):
    import numpy as np

    if not frames:
        return None
    cols = cols or (2 if len(frames) <= 4 else 3)
    h, w, _ = frames[0].shape
    rows = math.ceil(len(frames) / cols)
    sheet = np.full((rows * h + (rows - 1) * 2, cols * w + (cols - 1) * 2, 3), 40, dtype=np.uint8)
    for i, f in enumerate(frames):
        r, c = divmod(i, cols)
        y, x = r * (h + 2), c * (w + 2)
        sheet[y:y + h, x:x + w] = f
        # a thin time bar along the bottom of each tile: filled proportion = i / (n-1)
        fill = int(w * (i / max(1, len(frames) - 1)))
        sheet[y + h - 4:y + h, x:x + fill] = (90, 200, 255)
    return sheet


def simulate(job: dict, xml: str, meta: dict, log_buffer: io.StringIO) -> dict:
    import mujoco
    import numpy as np

    out_dir = job["out_dir"]
    check_xml(xml)
    model = mujoco.MjModel.from_xml_string(xml)
    data = mujoco.MjData(model)
    with open(os.path.join(out_dir, "model.xml"), "w", encoding="utf-8") as fh:
        fh.write(xml)

    duration = min(float(job.get("duration_s") or 5.0), MAX_SIM_SECONDS)
    track_name = job.get("track_body") or meta.get("track_body") or (model.body(1).name if model.nbody > 1 else "world")
    track_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, track_name)
    if track_id < 0:
        names = [model.body(i).name for i in range(model.nbody)]
        raise ValueError(f"No body named {track_name!r} to track; bodies: {names}")
    controls = job.get("controls") or meta.get("controls") or {}
    schedule = ControlSchedule(model, controls, mujoco)
    cameras = list(job.get("cameras") or meta.get("cameras") or ["track"])[:4]
    width, height = int(job.get("width", 480)), int(job.get("height", 360))
    n_frames = max(2, min(int(job.get("frames", 6)), 12))
    record = bool(job.get("record", False))
    fps = max(5, min(int(job.get("fps", 30)), 60))

    # ----- signal columns
    names_act = [model.actuator(i).name or f"act{i}" for i in range(model.nu)]
    HINGE, SLIDE = int(mujoco.mjtJoint.mjJNT_HINGE), int(mujoco.mjtJoint.mjJNT_SLIDE)
    joints = [(j, model.joint(j).name or f"j{j}") for j in range(model.njnt) if int(model.jnt_type[j]) in (HINGE, SLIDE)]
    sensors = []
    for s in range(model.nsensor):
        nm = model.sensor(s).name or f"sensor{s}"
        adr, dim = int(model.sensor_adr[s]), int(model.sensor_dim[s])
        if dim == 1:
            sensors.append((nm, adr))
        else:
            for k in range(dim):
                sensors.append((f"{nm}[{k}]", adr + k))
    wheel_r = None
    for i in range(model.nnumeric):
        if model.numeric(i).name == "wheel_radius":
            wheel_r = float(model.numeric_data[model.numeric_adr[i]])
    wheel_joints = [(j, nm) for j, nm in joints if nm.startswith("wheel") and int(model.jnt_type[j]) == HINGE]
    track_geoms = {g for g in range(model.ngeom) if model.geom_bodyid[g] == track_id}
    # include geoms of child bodies (wheels hang off the cart)
    for b in range(model.nbody):
        bb = b
        while bb > 0 and bb != track_id:
            bb = int(model.body_parentid[bb])
        if bb == track_id:
            track_geoms.update(g for g in range(model.ngeom) if model.geom_bodyid[g] == b)

    columns = ["t", "pos_x", "pos_y", "pos_z", "vel_x", "vel_y", "vel_z", "speed", "contacts", "contact_normal_N"]
    columns += [f"ctrl.{n}" for n in names_act] + [f"force.{n}" for n in names_act]
    columns += [f"q.{n}" for _, n in joints] + [f"qd.{n}" for _, n in joints]
    columns += [f"sensor.{n}" for n, _ in sensors]
    if wheel_r is not None:
        columns += [f"slip.{n}" for _, n in wheel_joints]

    rows: list[list[float]] = []
    frames_by_cam: dict[str, list] = {c: [] for c in cameras}
    video_frames: list = []
    cams = {c: make_camera(model, c, track_id, mujoco) for c in cameras}  # bad names are the caller's error
    renderer = None
    try:
        renderer = mujoco.Renderer(model, height, width)
    except Exception as exc:  # no GL backend: rendering is optional, signals still count
        log_buffer.write(f"[rendering disabled: {exc}]\n")
        renderer = None

    dt = float(model.opt.timestep)
    n_steps = int(round(duration / dt))
    log_every = max(1, int(round(1.0 / (LOG_HZ * dt))))
    snap_steps = sorted({int(round(i * n_steps / (n_frames - 1))) for i in range(n_frames)})
    video_every = max(1, int(round(1.0 / (fps * dt))))
    f6 = np.zeros(6)
    wall0 = time.monotonic()
    wall_budget = float(job.get("wall_budget_s", 90.0))

    def render(cam_name):
        renderer.update_scene(data, camera=cams[cam_name])
        return renderer.render().copy()

    def log_row():
        pos = data.xpos[track_id]
        vel = _body_linvel(model, data, track_id, mujoco)
        speed = float(np.linalg.norm(vel))
        n_c, fn = 0, 0.0
        for ci in range(data.ncon):
            c = data.contact[ci]
            if c.geom1 in track_geoms or c.geom2 in track_geoms:
                n_c += 1
                mujoco.mj_contactForce(model, data, ci, f6)
                fn += abs(float(f6[0]))
        row = [data.time, *map(float, pos), *map(float, vel), speed, n_c, fn]
        row += [float(data.ctrl[i]) for i in range(model.nu)] + [float(data.actuator_force[i]) for i in range(model.nu)]
        row += [float(data.qpos[model.jnt_qposadr[j]]) for j, _ in joints] + [float(data.qvel[model.jnt_dofadr[j]]) for j, _ in joints]
        row += [float(data.sensordata[adr]) for _, adr in sensors]
        if wheel_r is not None:
            for j, _ in wheel_joints:
                rim = float(data.qvel[model.jnt_dofadr[j]]) * wheel_r
                row.append(abs(rim) - speed)
        rows.append(row)

    mujoco.mj_forward(model, data)  # positions and contacts are valid before the first log/snapshot
    step = 0
    while True:
        if step % log_every == 0:
            log_row()
        if renderer is not None:
            if step in snap_steps:
                for c in cameras:
                    frames_by_cam[c].append(render(c))
            if record and step % video_every == 0 and len(video_frames) < MAX_VIDEO_FRAMES:
                video_frames.append(render(cameras[0]))
        if step >= n_steps:
            break
        schedule.apply(data, data.time)
        mujoco.mj_step(model, data)
        step += 1
        if (step & 255) == 0 and time.monotonic() - wall0 > wall_budget:
            log_buffer.write(f"[stopped early at t={data.time:.2f}s: wall-clock budget {wall_budget}s]\n")
            break
    sim_wall = time.monotonic() - wall0

    # ----- outputs
    files: dict[str, str] = {"model.xml": "model.xml"}
    with open(os.path.join(out_dir, "signals.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(columns)
        for r in rows:
            w.writerow([f"{v:.6g}" if isinstance(v, float) else v for v in r])
    files["signals.csv"] = "signals.csv"

    sheets: dict[str, str] = {}
    if renderer is not None:
        import imageio.v3 as iio

        for c, frs in frames_by_cam.items():
            sheet = contact_sheet(frs)
            if sheet is not None:
                rel = f"sheet_{_safe(c)}.png"
                iio.imwrite(os.path.join(out_dir, rel), sheet)
                files[rel] = rel
                sheets[c] = rel
        if record and video_frames:
            import imageio

            rel = f"clip_{_safe(cameras[0])}.mp4"
            with imageio.get_writer(os.path.join(out_dir, rel), fps=fps, codec="libx264", quality=7,
                                    macro_block_size=None) as vw:
                for f in video_frames:
                    vw.append_data(f)
            files[rel] = rel

    arr = np.array(rows, dtype=float) if rows else np.zeros((0, len(columns)))
    signals = {}
    for k, col in enumerate(columns):
        if col == "t" or arr.shape[0] == 0:
            continue
        v = arr[:, k]
        signals[col] = {"min": _r(v.min()), "max": _r(v.max()), "mean": _r(v.mean()), "final": _r(v[-1])}
    summary = {
        "track_body": track_name,
        "sim_time_s": _r(data.time),
        "timestep_s": dt,
        "steps": step,
        "wall_s": _r(sim_wall),
        "realtime_factor": _r(data.time / sim_wall) if sim_wall > 0 else None,
        "controls": controls,
        "cameras": cameras,
        "snapshot_times_s": [_r(s * dt) for s in snap_steps],
        "start_pos": [_r(x) for x in arr[0, 1:4]] if arr.shape[0] else None,
        "end_pos": [_r(x) for x in arr[-1, 1:4]] if arr.shape[0] else None,
        "climb_m": _r(arr[-1, 3] - arr[0, 3]) if arr.shape[0] else None,
        "max_contacts": int(arr[:, 8].max()) if arr.shape[0] else 0,
        "actuators": names_act,
        "joints": [n for _, n in joints],
        "sensors": [n for n, _ in sensors],
        "wheel_radius_m": wheel_r,
        "signals": signals,
    }
    return {"files": files, "sheets": sheets, "summary": summary}


def _body_linvel(model, data, body_id, mujoco):
    import numpy as np

    v = np.zeros(6)
    mujoco.mj_objectVelocity(model, data, mujoco.mjtObj.mjOBJ_BODY, body_id, v, 0)
    return v[3:6]


def _safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", name)[:40] or "cam"


def _r(x, nd=4):
    try:
        return round(float(x), nd)
    except (TypeError, ValueError):
        return None


# ----------------------------------------------------------------------------- entry


def run(job: dict) -> dict:
    started = time.monotonic()
    log_buffer = io.StringIO()
    meta: dict = {}
    try:
        if job.get("generator"):
            xml, meta = build_from_generator(job["generator"], dict(job.get("params") or {}), log_buffer, job.get("support") or {})
        elif job.get("mjcf"):
            xml = job["mjcf"]
        else:
            raise ValueError("Give either `mjcf_xml` or a model generator")
        if job.get("describe"):
            return {"ok": True, "meta": meta, "log": log_buffer.getvalue()[-20000:]}
        result = simulate(job, xml, meta, log_buffer)
    except BaseException as exc:  # noqa: BLE001
        err = trimmed_traceback(exc) if _from_script(exc) else "".join(traceback.format_exception_only(type(exc), exc)).strip()
        return {"ok": False, "error": err, "log": log_buffer.getvalue()[-20000:]}
    result.update(ok=True, meta=meta, log=log_buffer.getvalue()[-20000:], duration_s=round(time.monotonic() - started, 2))
    return result


def _from_script(exc: BaseException) -> bool:
    return any(f.filename == SCRIPT_FILENAME for f in traceback.extract_tb(exc.__traceback__))


def main() -> int:
    with open(sys.argv[1], encoding="utf-8") as fh:
        job = json.load(fh)
    apply_limits(int(job.get("memory_mb", 2048)), int(job.get("timeout_s", 120)))
    os.chdir(job["out_dir"])
    try:
        result = run(job)
    except BaseException as exc:  # noqa: BLE001
        result = {"ok": False, "error": "".join(traceback.format_exception_only(type(exc), exc)).strip(), "log": ""}
    with open(os.path.join(job["out_dir"], "result.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh)
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
