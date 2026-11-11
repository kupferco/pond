"""A small GitHub client for saving files into the Pond repo.

Rules enforced here, not by convention:
- writes go only to branches whose name starts with ``claude/`` (never ``main``);
- writes go only under the allowed top-level folders (docs/, cad/, sim/ by default);
- paths must be relative, normalised and free of ``..``;
- content must be UTF-8 text under the size cap;
- every commit is logged with path, branch, sha and URL.
"""

from __future__ import annotations

import base64
import logging
import posixpath
import re
from dataclasses import dataclass, field

import httpx2 as httpx

log = logging.getLogger(__name__)

API = "https://api.github.com"
PROTECTED_BRANCHES = ("main", "master")


class RepoAccessError(ValueError):
    """The request was refused by policy (bad path, branch or size)."""


class GitHubError(RuntimeError):
    """GitHub returned an error."""


@dataclass(frozen=True)
class RepoPolicy:
    write_branch: str = "claude/drafts"
    write_branch_prefix: str = "claude/"
    allowed_prefixes: tuple[str, ...] = ("docs/", "cad/", "sim/")
    max_bytes: int = 1_048_576
    base_branch: str = "main"

    def check_branch(self, branch: str | None) -> str:
        branch = (branch or self.write_branch).strip()
        if not branch or branch in PROTECTED_BRANCHES or not branch.startswith(self.write_branch_prefix):
            raise RepoAccessError(
                f"writes are only allowed on branches starting with {self.write_branch_prefix!r} "
                f"(default {self.write_branch!r}), never {branch!r}"
            )
        if not re.fullmatch(r"[A-Za-z0-9._/-]+", branch) or "//" in branch or ".." in branch:
            raise RepoAccessError(f"invalid branch name {branch!r}")
        return branch

    def check_write_path(self, path: str) -> str:
        path = normalise_path(path)
        if not path.startswith(self.allowed_prefixes):
            raise RepoAccessError(
                f"writes are only allowed under {', '.join(self.allowed_prefixes)}; got {path!r}"
            )
        if path.endswith("/"):
            raise RepoAccessError("path must name a file, not a folder")
        return path

    def check_content(self, content: str) -> bytes:
        data = content.encode("utf-8")
        if len(data) > self.max_bytes:
            raise RepoAccessError(f"file is {len(data)} bytes; the limit is {self.max_bytes}")
        return data


def normalise_path(path: str) -> str:
    """Clean a repo-relative path; refuse anything that could escape or is not a plain path."""
    raw = (path or "").strip().replace("\\", "/")
    if raw.startswith("/"):
        raw = raw.lstrip("/")
    if not raw:
        raise RepoAccessError("path is empty")
    parts = [p for p in raw.split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        raise RepoAccessError(f"path may not contain '..': {path!r}")
    if any(not re.fullmatch(r"[A-Za-z0-9._ -]+", p) for p in parts):
        raise RepoAccessError(f"path has characters that are not allowed: {path!r}")
    if any(p.startswith(".") for p in parts):
        raise RepoAccessError(f"hidden files and folders are not allowed: {path!r}")
    return posixpath.join(*parts)


def slugify(name: str, *, default: str = "untitled") -> str:
    """Turn a title into a safe file stem: 'Hand sleeve v3' -> 'hand_sleeve_v3'."""
    stem = re.sub(r"[^a-z0-9]+", "_", (name or "").strip().lower()).strip("_")
    stem = re.sub(r"_+", "_", stem)
    return stem[:60] or default


@dataclass
class CommitResult:
    path: str
    branch: str
    sha: str
    commit_sha: str
    url: str
    created: bool


@dataclass
class RepoEntry:
    path: str
    type: str  # "file" | "dir"
    size: int = 0


@dataclass
class GitHubRepo:
    """Minimal GitHub Contents/Refs/Pulls client bound to one repository."""

    token: str
    repo: str  # "owner/name"
    policy: RepoPolicy = field(default_factory=RepoPolicy)
    http: httpx.Client | None = None
    api: str = API

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", self.repo or ""):
            raise ValueError(f"POND_GITHUB_REPO must look like owner/name, got {self.repo!r}")
        if self.http is None:
            self.http = httpx.Client(timeout=30)
        self.http.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "pond-render",
        })

    # ------------------------------------------------------------------ low level

    def _url(self, suffix: str) -> str:
        return f"{self.api}/repos/{self.repo}/{suffix.lstrip('/')}"

    def _request(self, method: str, suffix: str, *, ok=(200,), json: dict | None = None, params: dict | None = None):
        assert self.http is not None
        r = self.http.request(method, self._url(suffix), json=json, params=params)
        if r.status_code in ok:
            return r.json() if r.content else None
        if r.status_code == 404:
            return None
        try:
            msg = r.json().get("message", r.text)
        except ValueError:
            msg = r.text
        raise GitHubError(f"GitHub {method} {suffix}: {r.status_code} {msg}")

    # ------------------------------------------------------------------ reads

    def read_file(self, path: str, ref: str | None = None) -> tuple[bytes, str] | None:
        """Return (content, blob sha) or None when the file does not exist."""
        path = normalise_path(path)
        data = self._request("GET", f"contents/{path}", params={"ref": ref} if ref else None)
        if data is None:
            return None
        if isinstance(data, list):
            raise RepoAccessError(f"{path!r} is a folder; use repo_list")
        if data.get("type") != "file":
            raise RepoAccessError(f"{path!r} is a {data.get('type')}, not a file")
        if data.get("encoding") == "base64" and data.get("content") is not None:
            return base64.b64decode(data["content"]), data["sha"]
        # Files over 1 MB come without inline content.
        raise RepoAccessError(f"{path!r} is too large to read through this tool")

    def list_dir(self, path: str = "", ref: str | None = None) -> list[RepoEntry] | None:
        suffix = "contents" if not path.strip(" /") else f"contents/{normalise_path(path)}"
        data = self._request("GET", suffix, params={"ref": ref} if ref else None)
        if data is None:
            return None
        if isinstance(data, dict):
            raise RepoAccessError(f"{path!r} is a file; use repo_read")
        return [RepoEntry(path=d["path"], type=d["type"], size=int(d.get("size") or 0)) for d in data]

    def branch_sha(self, branch: str) -> str | None:
        data = self._request("GET", f"git/ref/heads/{branch}")
        return data["object"]["sha"] if data else None

    # ------------------------------------------------------------------ writes

    def ensure_branch(self, branch: str) -> str:
        """Create ``branch`` from the base branch when it does not exist; return its head sha."""
        branch = self.policy.check_branch(branch)
        sha = self.branch_sha(branch)
        if sha:
            return sha
        base_sha = self.branch_sha(self.policy.base_branch)
        if not base_sha:
            raise GitHubError(f"base branch {self.policy.base_branch!r} not found in {self.repo}")
        data = self._request("POST", "git/refs", ok=(201,), json={"ref": f"refs/heads/{branch}", "sha": base_sha})
        log.info("github: created branch %s from %s (%s)", branch, self.policy.base_branch, base_sha[:8])
        return data["object"]["sha"]

    def write_file(self, path: str, content: str, message: str, branch: str | None = None) -> CommitResult:
        """Create or update one text file with a single commit on an allowed branch."""
        branch = self.policy.check_branch(branch)
        path = self.policy.check_write_path(path)
        data = self.policy.check_content(content)
        message = (message or "").strip() or f"Update {path}"
        self.ensure_branch(branch)

        existing = self.read_file(path, ref=branch)
        if existing and existing[0] == data:
            sha = existing[1]
            log.info("github: %s on %s unchanged, no commit", path, branch)
            return CommitResult(path=path, branch=branch, sha=sha, commit_sha="", created=False,
                                url=f"https://github.com/{self.repo}/blob/{branch}/{path}")

        body: dict = {
            "message": message[:500],
            "content": base64.b64encode(data).decode("ascii"),
            "branch": branch,
        }
        if existing:
            body["sha"] = existing[1]
        result = self._request("PUT", f"contents/{path}", ok=(200, 201), json=body)
        if result is None:
            raise GitHubError(f"GitHub refused the write to {path} on {branch}")
        commit = result["commit"]
        out = CommitResult(
            path=path, branch=branch, sha=result["content"]["sha"], commit_sha=commit["sha"],
            url=commit.get("html_url") or f"https://github.com/{self.repo}/blob/{branch}/{path}",
            created=existing is None,
        )
        log.info("github: committed %s to %s (%s) %s", out.path, out.branch, out.commit_sha[:8], out.url)
        return out

    def open_pr(self, title: str, body: str = "", head: str | None = None) -> dict:
        """Open a PR from the drafts branch to the base branch, or return the one already open."""
        head = self.policy.check_branch(head)
        owner = self.repo.split("/")[0]
        existing = self._request("GET", "pulls", params={"head": f"{owner}:{head}", "base": self.policy.base_branch, "state": "open"})
        if existing:
            pr = existing[0]
            return {"number": pr["number"], "url": pr["html_url"], "title": pr["title"], "existing": True}
        pr = self._request("POST", "pulls", ok=(201,), json={
            "title": (title or f"Drafts from {head}")[:200], "body": body or "", "head": head, "base": self.policy.base_branch,
        })
        log.info("github: opened PR #%s %s -> %s: %s", pr["number"], head, self.policy.base_branch, pr["html_url"])
        return {"number": pr["number"], "url": pr["html_url"], "title": pr["title"], "existing": False}
