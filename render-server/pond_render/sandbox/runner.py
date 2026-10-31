"""CadQuery sandbox runner. Executed as a separate process by host.py:

    python -I runner.py <job.json>

Self-contained on purpose: with `-I` the interpreter ignores PYTHONPATH and the script
directory, so nothing from the server package is importable here. The job file says what
to run; results go to <out_dir>/result.json. The process gets no credentials, a scrubbed
environment, a temp working directory and resource limits (see host.py).

The in-process restrictions (import allow-list, trimmed builtins) are a tripwire for
honest mistakes. They are not a security boundary on their own; the process boundary is.
"""

from __future__ import annotations

import builtins
import io
import json
import math
import os
import sys
import time
import traceback

SCRIPT_NAME = "__pond_script__"
SCRIPT_FILENAME = "<cad_script>"

ALLOWED_MODULES = frozenset(
    {
        "cadquery",
        "math",
        "cmath",
        "itertools",
        "functools",
        "operator",
        "typing",
        "dataclasses",
        "collections",
        "enum",
        "copy",
        "random",
        "statistics",
        "numpy",
    }
)

REMOVED_BUILTINS = (
    "open",
    "exec",
    "eval",
    "compile",
    "input",
    "breakpoint",
    "exit",
    "quit",
    "help",
    "memoryview",
)

# Camera presets: name -> (direction the camera sits in, screen-up vector). Z is up.
VIEW_PRESETS: dict[str, tuple[tuple[float, float, float], tuple[float, float, float], str]] = {
    "front": ((0, -1, 0), (0, 0, 1), "looking along +Y: X right, Z up"),
    "back": ((0, 1, 0), (0, 0, 1), "looking along -Y: X left, Z up"),
    "top": ((0, 0, 1), (0, 1, 0), "looking down -Z: X right, Y up"),
    "bottom": ((0, 0, -1), (0, 1, 0), "looking up +Z: X left, Y up"),
    "right": ((1, 0, 0), (0, 0, 1), "looking along -X: Y right, Z up"),
    "left": ((-1, 0, 0), (0, 0, 1), "looking along +X: Y left, Z up"),
    "iso": ((1, -1, 1), (0, 0, 1), "from front-right-top, Z up"),
    "iso_back": ((-1, 1, 1), (0, 0, 1), "from back-left-top, Z up"),
}
VIEW_ALIASES = {"side": "right", "isometric": "iso", "perspective": "iso", "above": "top", "below": "bottom"}


def resolve_view(name: str) -> str:
    key = name.strip().lower().replace("-", "_")
    key = VIEW_ALIASES.get(key, key)
    if key not in VIEW_PRESETS:
        raise ValueError(f"Unknown view {name!r}. Known views: {', '.join(VIEW_PRESETS)} (side = right)")
    return key


# ----------------------------------------------------------------------------- limits


def apply_limits(memory_mb: int, cpu_s: int) -> None:
    try:
        import resource
    except ImportError:  # pragma: no cover - Windows
        return

    def _set(name: str, soft: int, hard: int | None = None) -> None:
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
        # Address-space limits are reliable on Linux; macOS ignores them in practice.
        _set("RLIMIT_AS", memory_mb * 1024 * 1024)


# ----------------------------------------------------------------------------- sandboxing


def install_import_guard() -> None:
    real_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        importer = (globals or {}).get("__name__")
        if importer == SCRIPT_NAME:
            if level != 0:
                raise ImportError("Relative imports are not allowed in CAD scripts")
            top = name.split(".", 1)[0]
            if top not in ALLOWED_MODULES:
                raise ImportError(
                    f"Importing {name!r} is not allowed in the CAD sandbox. "
                    f"Allowed modules: {', '.join(sorted(ALLOWED_MODULES))}"
                )
        return real_import(name, globals, locals, fromlist, level)

    builtins.__import__ = guarded_import


def make_script_builtins() -> dict:
    safe = dict(vars(builtins))
    for name in REMOVED_BUILTINS:
        safe.pop(name, None)
    return safe


# ----------------------------------------------------------------------------- geometry


def shape_from_object(cq, obj):
    """Turn whatever the script produced into a cq.Shape (and the Assembly, if it was one)."""
    if isinstance(obj, cq.Assembly):
        return obj.toCompound(), obj
    if isinstance(obj, cq.Workplane):
        vals = [v for v in obj.vals() if isinstance(v, cq.Shape)]
        if not vals:
            raise ValueError("The Workplane has no solid geometry on its stack (did you finish with .extrude()/.cut() etc.?)")
        return (vals[0] if len(vals) == 1 else cq.Compound.makeCompound(vals)), None
    if isinstance(obj, cq.Shape):
        return obj, None
    if isinstance(obj, cq.Sketch):
        raise ValueError("A Sketch cannot be rendered on its own; place it on a Workplane and extrude it.")
    raise ValueError(f"Cannot render an object of type {type(obj).__name__}; expected Workplane, Shape or Assembly")


def _normalize(v):
    n = math.sqrt(sum(c * c for c in v))
    return tuple(c / n for c in v)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def project_svg(shape, view: str, *, width: int, height: int, show_hidden: bool, caption: str) -> str:
    """Hidden-line projection of `shape` to an SVG string, with a controlled screen orientation.

    Mirrors cadquery.occ_impl.exporters.svg.getSVG but builds the projector frame with an
    explicit X direction so each named view has a predictable up/right.
    """
    from cadquery import Compound, Shape
    from cadquery.occ_impl.exporters.svg import PATHTEMPLATE, getPaths
    from OCP.BRepLib import BRepLib
    from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt
    from OCP.HLRAlgo import HLRAlgo_Projector
    from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape

    cam, up, _ = VIEW_PRESETS[view]
    n = _normalize(cam)
    # Screen-up must be perpendicular to the view direction.
    up_proj = tuple(u - _dot(up, n) * c for u, c in zip(up, n))
    if math.sqrt(_dot(up_proj, up_proj)) < 1e-9:
        up_proj = (0, 1, 0)
    u = _normalize(up_proj)
    r = _cross(u, n)  # screen-right, so that right x up = toward viewer

    frame = gp_Ax2(gp_Pnt(), gp_Dir(*n), gp_Dir(*r))
    hlr = HLRBRep_Algo()
    hlr.Add(shape.wrapped)
    hlr.Projector(HLRAlgo_Projector(frame))
    hlr.Update()
    hlr.Hide()
    hlr_shapes = HLRBRep_HLRToShape(hlr)

    visible, hidden = [], []
    for getter in (hlr_shapes.VCompound, hlr_shapes.Rg1LineVCompound, hlr_shapes.OutLineVCompound):
        s = getter()
        if not s.IsNull():
            visible.append(s)
    for getter in (hlr_shapes.HCompound, hlr_shapes.OutLineHCompound):
        s = getter()
        if not s.IsNull():
            hidden.append(s)
    for el in visible + hidden:
        BRepLib.BuildCurves3d_s(el, 1e-6)

    visible = [Shape(s) for s in visible]
    hidden = [Shape(s) for s in hidden]
    hidden_paths, visible_paths = getPaths(visible, hidden)
    if not visible_paths and not hidden_paths:
        raise ValueError("Nothing to draw: the projected shape has no edges")

    bb = Compound.makeCompound(hidden + visible).BoundingBox()
    xlen = max(bb.xlen, 1e-6)
    ylen = max(bb.ylen, 1e-6)
    margin = 0.08
    unit_scale = min(width * (1 - 2 * margin) / xlen, height * (1 - 2 * margin) / ylen)
    draw_w, draw_h = xlen * unit_scale, ylen * unit_scale
    x_translate = -bb.xmin + (width - draw_w) / 2 / unit_scale
    y_translate = -bb.ymax - (height - draw_h) / 2 / unit_scale
    stroke = 1.2 / unit_scale

    hidden_content = "".join(PATHTEMPLATE % p for p in hidden_paths) if show_hidden else ""
    visible_content = "".join(PATHTEMPLATE % p for p in visible_paths)
    caption_h = 28
    caption_safe = caption.replace("&", "&amp;").replace("<", "&lt;")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height + caption_h}" viewBox="0 0 {width} {height + caption_h}">
  <rect width="100%" height="100%" fill="white"/>
  <g transform="scale({unit_scale}, -{unit_scale}) translate({x_translate},{y_translate})" stroke-width="{stroke}" fill="none" stroke-linecap="round" stroke-linejoin="round">
    <g stroke="rgb(150,150,150)" stroke-dasharray="{stroke * 3},{stroke * 2}">
{hidden_content}    </g>
    <g stroke="rgb(20,20,20)">
{visible_content}    </g>
  </g>
  <rect x="0" y="{height}" width="{width}" height="{caption_h}" fill="#f2f2f2"/>
  <text x="10" y="{height + 19}" font-family="Helvetica, Arial, sans-serif" font-size="13" fill="#222">{caption_safe}</text>
</svg>
"""


# ----------------------------------------------------------------------------- main


def trimmed_traceback(exc: BaseException) -> str:
    """Traceback showing only frames from the user's script plus the error line."""
    frames = [f for f in traceback.extract_tb(exc.__traceback__) if f.filename == SCRIPT_FILENAME]
    lines = []
    if frames:
        lines.append("Traceback (most recent call last):\n")
        lines.extend(traceback.format_list(frames))
    lines.extend(traceback.format_exception_only(type(exc), exc))
    return "".join(lines).rstrip()


def run(job: dict) -> dict:
    started = time.monotonic()
    out_dir = job["out_dir"]
    views = [resolve_view(v) for v in job.get("views", ["front", "top", "right", "iso"])]
    width = int(job.get("width", 800))
    height = int(job.get("height", width * 3 // 4))
    show_hidden = bool(job.get("show_hidden", False))
    exports = list(job.get("exports", ["step", "stl", "glb"]))

    import cadquery as cq

    log_buffer = io.StringIO()
    shown: list = []

    def show_object(obj, name=None, options=None):
        shown.append(obj)

    install_import_guard()  # before copying builtins, so the copy holds the guarded __import__
    script_globals = {
        "__name__": SCRIPT_NAME,
        "__builtins__": make_script_builtins(),
        "cq": cq,
        "cadquery": cq,
        "math": math,
        "show_object": show_object,
    }
    real_stdout, real_stderr = sys.stdout, sys.stderr
    sys.stdout = sys.stderr = log_buffer
    try:
        code = compile(job["script"], SCRIPT_FILENAME, "exec")
        exec(code, script_globals)
    except BaseException as exc:  # noqa: BLE001 - report everything back to the caller
        sys.stdout, sys.stderr = real_stdout, real_stderr
        return {"ok": False, "error": trimmed_traceback(exc), "log": log_buffer.getvalue()[-20000:]}
    finally:
        sys.stdout, sys.stderr = real_stdout, real_stderr

    try:
        candidates = shown or ([script_globals["result"]] if "result" in script_globals else [])
        if not candidates:
            raise ValueError(
                "The script produced nothing to render. Assign the final object to a variable named "
                "`result` (a cq.Workplane, cq.Shape or cq.Assembly), or call show_object(obj)."
            )
        assembly = None
        shapes = []
        for obj in candidates:
            shape, asm = shape_from_object(cq, obj)
            shapes.append(shape)
            assembly = assembly or asm
        shape = shapes[0] if len(shapes) == 1 else cq.Compound.makeCompound(shapes)

        bb = shape.BoundingBox()
        bbox = {
            "x": [round(bb.xmin, 3), round(bb.xmax, 3)],
            "y": [round(bb.ymin, 3), round(bb.ymax, 3)],
            "z": [round(bb.zmin, 3), round(bb.zmax, 3)],
            "size": [round(bb.xlen, 3), round(bb.ylen, 3), round(bb.zlen, 3)],
        }
        solids = len(shape.Solids())
        faces = len(shape.Faces())
        try:
            volume = float(shape.Volume())
        except Exception:
            volume = None

        files = {}
        if "step" in exports:
            cq.exporters.export(shape, os.path.join(out_dir, "model.step"), "STEP")
            files["model.step"] = "model.step"
        if "stl" in exports:
            cq.exporters.export(shape, os.path.join(out_dir, "model.stl"), "STL", tolerance=0.05, angularTolerance=0.1)
            files["model.stl"] = "model.stl"
        if "glb" in exports:
            try:
                (assembly or cq.Assembly(shape, name="part")).export(os.path.join(out_dir, "model.glb"))
                files["model.glb"] = "model.glb"
            except Exception as exc:  # GLB is a nice-to-have
                log_buffer.write(f"\n[glb export skipped: {exc}]\n")

        size_txt = " x ".join(f"{v:g}" for v in bbox["size"])
        svgs = {}
        for view in views:
            caption = f"{view}  ·  {VIEW_PRESETS[view][2]}  ·  bbox {size_txt} mm"
            svg = project_svg(shape, view, width=width, height=height, show_hidden=show_hidden, caption=caption)
            name = f"{view}.svg"
            with open(os.path.join(out_dir, name), "w", encoding="utf-8") as fh:
                fh.write(svg)
            svgs[view] = name

        return {
            "ok": True,
            "bbox": bbox,
            "volume": volume,
            "solids": solids,
            "faces": faces,
            "files": files,
            "svgs": svgs,
            "log": log_buffer.getvalue()[-20000:],
            "duration_s": round(time.monotonic() - started, 2),
        }
    except BaseException as exc:  # noqa: BLE001
        return {"ok": False, "error": trimmed_traceback(exc), "log": log_buffer.getvalue()[-20000:]}


def main() -> int:
    job_path = sys.argv[1]
    with open(job_path, encoding="utf-8") as fh:
        job = json.load(fh)
    apply_limits(int(job.get("memory_mb", 3072)), int(job.get("timeout_s", 60)))
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
