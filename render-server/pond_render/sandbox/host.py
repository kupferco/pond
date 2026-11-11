"""Spawn runner.py in a limited subprocess and collect its results."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

RUNNER = Path(__file__).with_name("runner.py")
SIM_RUNNER = Path(__file__).with_name("sim_runner.py")
_PASSTHROUGH_ENV = ("MUJOCO_GL", "PYOPENGL_PLATFORM", "DYLD_FALLBACK_LIBRARY_PATH")
DEFAULT_VIEWS = ["front", "top", "right", "iso"]
_ALLOWED_PATH = "/usr/local/bin:/usr/bin:/bin"


@dataclass
class CadRunResult:
    ok: bool
    error: str | None = None
    log: str = ""
    timed_out: bool = False
    bbox: dict | None = None
    volume: float | None = None
    solids: int | None = None
    faces: int | None = None
    files: dict[str, Path] = field(default_factory=dict)
    svgs: dict[str, Path] = field(default_factory=dict)
    duration_s: float = 0.0


@dataclass
class SimRunResult:
    ok: bool
    error: str | None = None
    log: str = ""
    timed_out: bool = False
    summary: dict | None = None
    meta: dict | None = None
    files: dict[str, Path] = field(default_factory=dict)
    sheets: dict[str, Path] = field(default_factory=dict)  # camera -> png path
    duration_s: float = 0.0


def run_cad_script(
    script: str,
    *,
    out_dir: Path,
    views: list[str] | None = None,
    timeout_s: int = 60,
    memory_mb: int = 3072,
    show_hidden: bool = False,
    width: int = 800,
    exports: tuple[str, ...] = ("step", "stl", "glb"),
) -> CadRunResult:
    """Run a CadQuery script in a fresh, locked-down interpreter.

    The child gets: no inherited environment (so no credentials), its own temp dir as
    cwd/HOME/TMPDIR, `python -I` (ignores env and user site), rlimits, a wall-clock
    timeout after which its whole process group is killed.
    """
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    job = {
        "script": script,
        "out_dir": str(out_dir),
        "views": views or DEFAULT_VIEWS,
        "timeout_s": timeout_s,
        "memory_mb": memory_mb,
        "show_hidden": show_hidden,
        "width": width,
        "exports": list(exports),
    }
    job_path = out_dir / "job.json"
    job_path.write_text(json.dumps(job), encoding="utf-8")

    proc, stdout_text, timed_out, duration = _spawn(RUNNER, job_path, out_dir, timeout_s)

    if timed_out:
        return CadRunResult(
            ok=False,
            timed_out=True,
            error=f"The CAD script was killed after {timeout_s} s. Simplify the geometry or reduce loops.",
            log=stdout_text[-20000:],
            duration_s=duration,
        )

    result_path = out_dir / "result.json"
    if not result_path.is_file():
        return CadRunResult(
            ok=False,
            error=f"The CAD runner exited with code {proc.returncode} without producing a result.\n{stdout_text[-4000:]}",
            log=stdout_text[-20000:],
            duration_s=duration,
        )
    data = json.loads(result_path.read_text(encoding="utf-8"))
    log = (data.get("log") or "") + (("\n[runner stderr]\n" + stdout_text) if stdout_text.strip() else "")
    if not data.get("ok"):
        return CadRunResult(ok=False, error=data.get("error") or "unknown error", log=log[-20000:], duration_s=duration)

    return CadRunResult(
        ok=True,
        log=log[-20000:],
        bbox=data.get("bbox"),
        volume=data.get("volume"),
        solids=data.get("solids"),
        faces=data.get("faces"),
        files={name: out_dir / rel for name, rel in (data.get("files") or {}).items()},
        svgs={view: out_dir / rel for view, rel in (data.get("svgs") or {}).items()},
        duration_s=duration,
    )


def _spawn(runner: Path, job_path: Path, out_dir: Path, timeout_s: int) -> tuple[subprocess.Popen, str, bool, float]:
    """Run a sandbox runner with a scrubbed environment; return (proc, stdout, timed_out, seconds)."""
    env = {
        "PATH": _ALLOWED_PATH,
        "HOME": str(out_dir),
        "TMPDIR": str(out_dir),
        "TMP": str(out_dir),
        "TEMP": str(out_dir),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "OMP_NUM_THREADS": "2",
    }
    for key in _PASSTHROUGH_ENV:  # rendering backend selection, no secrets
        if os.environ.get(key):
            env[key] = os.environ[key]
    cmd = [sys.executable, "-I", "-u", str(runner), str(job_path)]
    started = time.monotonic()
    proc = subprocess.Popen(
        cmd,
        cwd=str(out_dir),
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    timed_out = False
    try:
        output, _ = proc.communicate(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        timed_out = True
        _kill_group(proc)
        output, _ = proc.communicate()
    duration = round(time.monotonic() - started, 2)
    return proc, (output or b"").decode("utf-8", errors="replace"), timed_out, duration


def run_sim_job(
    *,
    out_dir: Path,
    mjcf: str | None = None,
    generator: str | None = None,
    support: dict[str, str] | None = None,
    params: dict | None = None,
    duration_s: float = 5.0,
    controls: dict | None = None,
    cameras: list[str] | None = None,
    record: bool = False,
    frames: int = 6,
    width: int = 480,
    height: int = 360,
    track_body: str | None = None,
    describe: bool = False,
    timeout_s: int = 120,
    memory_mb: int = 3072,
) -> SimRunResult:
    """Run a MuJoCo simulation (or just describe a model generator) in a locked-down subprocess."""
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    job = {
        "out_dir": str(out_dir),
        "mjcf": mjcf,
        "generator": generator,
        "support": support or {},
        "params": params or {},
        "duration_s": duration_s,
        "controls": controls,
        "cameras": cameras,
        "record": record,
        "frames": frames,
        "width": width,
        "height": height,
        "track_body": track_body,
        "describe": describe,
        "timeout_s": timeout_s,
        "memory_mb": memory_mb,
        "wall_budget_s": max(10, timeout_s - 20),
    }
    job_path = out_dir / "job.json"
    job_path.write_text(json.dumps(job), encoding="utf-8")
    proc, stdout_text, timed_out, duration = _spawn(SIM_RUNNER, job_path, out_dir, timeout_s)
    if timed_out:
        return SimRunResult(ok=False, timed_out=True, duration_s=duration, log=stdout_text[-20000:],
                            error=f"The simulation was killed after {timeout_s} s. Shorten duration_s or simplify the model.")
    result_path = out_dir / "result.json"
    if not result_path.is_file():
        return SimRunResult(ok=False, duration_s=duration, log=stdout_text[-20000:],
                            error=f"The sim runner exited with code {proc.returncode} without producing a result.\n{stdout_text[-4000:]}")
    data = json.loads(result_path.read_text(encoding="utf-8"))
    log = (data.get("log") or "") + (("\n[runner stderr]\n" + stdout_text) if stdout_text.strip() else "")
    if not data.get("ok"):
        return SimRunResult(ok=False, error=data.get("error") or "unknown error", log=log[-20000:], duration_s=duration)
    return SimRunResult(
        ok=True,
        log=log[-20000:],
        summary=data.get("summary"),
        meta=data.get("meta"),
        files={name: out_dir / rel for name, rel in (data.get("files") or {}).items()},
        sheets={cam: out_dir / rel for cam, rel in (data.get("sheets") or {}).items()},
        duration_s=duration,
    )


def _kill_group(proc: subprocess.Popen) -> None:
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        try:
            proc.kill()
        except ProcessLookupError:
            pass
