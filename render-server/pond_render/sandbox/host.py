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
    cmd = [sys.executable, "-I", "-u", str(RUNNER), str(job_path)]
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
    stdout_text = (output or b"").decode("utf-8", errors="replace")

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


def _kill_group(proc: subprocess.Popen) -> None:
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        try:
            proc.kill()
        except ProcessLookupError:
            pass
