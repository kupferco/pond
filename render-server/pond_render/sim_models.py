"""Where sim model generators come from: the repo's /sim folder, via GitHub or a local checkout.

A model is `sim/<name>.py` defining PARAMS, build(**params) -> MJCF, and optionally
TRACK_BODY, CAMERAS and DEFAULT_CONTROLS. Helper files it imports (`constants.py`) are sent
to the sandbox alongside it. Listing parses the files statically (ast), never executing them.
"""

from __future__ import annotations

import ast
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from .github import GitHubRepo, RepoAccessError

log = logging.getLogger(__name__)

SIM_PREFIX = "sim/"
NAME_RE = re.compile(r"[a-z][a-z0-9_]{0,60}")
SUPPORT_NAMES = ("constants",)  # helper modules shipped with every generator


@dataclass
class SimModel:
    name: str
    source: str
    support: dict[str, str] = field(default_factory=dict)
    origin: str = ""  # "local:<path>" or "github:<ref>"


@dataclass
class SimModelInfo:
    name: str
    doc: str
    params: dict  # name -> {"default": ..., "help": ...}
    origin: str


class SimModelSource:
    """Reads sim/*.py from GitHub (drafts branch, then main) when configured, else from a local folder."""

    def __init__(self, github: GitHubRepo | None, local_dir: Path | None):
        self.github = github
        self.local_dir = Path(local_dir) if local_dir else None

    # ------------------------------------------------------------------ reading

    def _read(self, filename: str) -> tuple[str, str] | None:
        """Return (source, origin) for sim/<filename>, or None."""
        if self.github is not None:
            for ref in (self.github.policy.write_branch, self.github.policy.base_branch):
                try:
                    found = self.github.read_file(SIM_PREFIX + filename, ref=ref)
                except RepoAccessError:
                    found = None
                if found:
                    return found[0].decode("utf-8", errors="replace"), f"github:{ref}"
            return None
        if self.local_dir is not None:
            path = self.local_dir / filename
            if path.is_file():
                return path.read_text(encoding="utf-8"), f"local:{path}"
        return None

    def _names(self) -> list[str]:
        names: set[str] = set()
        if self.github is not None:
            for ref in (self.github.policy.write_branch, self.github.policy.base_branch):
                try:
                    entries = self.github.list_dir("sim", ref=ref) or []
                except RepoAccessError:
                    entries = []
                names.update(Path(e.path).stem for e in entries if e.type == "file" and e.path.endswith(".py"))
        elif self.local_dir is not None and self.local_dir.is_dir():
            names.update(p.stem for p in self.local_dir.glob("*.py"))
        return sorted(n for n in names if NAME_RE.fullmatch(n) and n not in SUPPORT_NAMES and not n.startswith("_"))

    # ------------------------------------------------------------------ API

    def load(self, name: str) -> SimModel:
        if not NAME_RE.fullmatch(name or ""):
            raise ValueError(f"bad model name {name!r}; use the names from list_models")
        found = self._read(f"{name}.py")
        if not found:
            raise FileNotFoundError(f"no sim model {name!r} (looked for sim/{name}.py); see list_models")
        source, origin = found
        support = {}
        for helper in SUPPORT_NAMES:
            got = self._read(f"{helper}.py")
            if got:
                support[helper] = got[0]
        return SimModel(name=name, source=source, support=support, origin=origin)

    def list(self) -> list[SimModelInfo]:
        out = []
        for name in self._names():
            found = self._read(f"{name}.py")
            if not found:
                continue
            source, origin = found
            try:
                doc, params = describe_source(source)
            except SyntaxError as exc:
                doc, params = f"(does not parse: {exc})", {}
            out.append(SimModelInfo(name=name, doc=doc, params=params, origin=origin))
        return out


def describe_source(source: str) -> tuple[str, dict]:
    """First docstring paragraph and the PARAMS table, read statically with ast."""
    tree = ast.parse(source)
    doc = (ast.get_docstring(tree) or "").strip().split("\n\n")[0].replace("\n", " ")
    params: dict = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "PARAMS" for t in node.targets):
            if isinstance(node.value, ast.Dict):
                for k, v in zip(node.value.keys, node.value.values):
                    key = _lit(k)
                    if not isinstance(key, str):
                        continue
                    if isinstance(v, (ast.Tuple, ast.List)) and v.elts:
                        default = _lit(v.elts[0])
                        help_ = _lit(v.elts[1]) if len(v.elts) > 1 else ""
                    else:
                        default, help_ = _lit(v), ""
                    params[key] = {"default": default, "help": help_ if isinstance(help_, str) else ""}
    return doc, params


def _lit(node):
    """A literal's value, or the source expression as text when it is a name (e.g. a constant)."""
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError):
        return ast.unparse(node)
