"""Make cairosvg importable on macOS with a Homebrew-installed cairo.

python.org builds of Python do not search /opt/homebrew/lib for dylibs. ctypes' macOS
loader reads DYLD_FALLBACK_LIBRARY_PATH from os.environ at lookup time, so setting it
here before the first `import cairosvg` is enough. On Linux (the Docker image) the
system libcairo2 package is found without help.
"""

from __future__ import annotations

import os
import sys

_HOMEBREW_LIB_DIRS = ("/opt/homebrew/lib", "/usr/local/lib")


def ensure_cairo() -> None:
    if sys.platform != "darwin":
        return
    existing = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "")
    parts = [p for p in existing.split(":") if p]
    for d in _HOMEBREW_LIB_DIRS:
        if os.path.isdir(d) and d not in parts:
            parts.append(d)
    os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = ":".join(parts)
