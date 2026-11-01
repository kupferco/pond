"""An in-memory stand-in for the GitHub REST API, mounted on an httpx2 MockTransport."""

from __future__ import annotations

import base64
import hashlib
import json
import re

import httpx2 as httpx

from pond_render.github import GitHubRepo, RepoPolicy


def _sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


class FakeGitHub:
    """Enough of the contents/refs/pulls API for the tools: one repo, many branches."""

    def __init__(self, repo: str = "kupferco/pond", token: str = "ghp_test"):
        self.repo = repo
        self.token = token
        self.branches: dict[str, dict[str, bytes]] = {"main": {"README.md": b"# pond\n", "cad/pipe.py": b"result = 1\n"}}
        self.commits: list[dict] = []
        self.pulls: list[dict] = []
        self.requests: list[tuple[str, str]] = []

    # ------------------------------------------------------------------ client

    def client(self, policy: RepoPolicy | None = None) -> GitHubRepo:
        http = httpx.Client(transport=httpx.MockTransport(self.handle))
        return GitHubRepo(token=self.token, repo=self.repo, policy=policy or RepoPolicy(), http=http)

    # ------------------------------------------------------------------ handler

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append((request.method, request.url.path))
        if request.headers.get("Authorization") != f"Bearer {self.token}":
            return httpx.Response(401, json={"message": "Bad credentials"})
        prefix = f"/repos/{self.repo}/"
        path = request.url.path
        if not path.startswith(prefix):
            return httpx.Response(404, json={"message": "Not Found"})
        rest = path[len(prefix):]
        params = dict(request.url.params)
        body = json.loads(request.content) if request.content else {}

        if m := re.fullmatch(r"git/ref/heads/(.+)", rest):
            name = m.group(1)
            if name not in self.branches:
                return httpx.Response(404, json={"message": "Not Found"})
            return httpx.Response(200, json={"ref": f"refs/heads/{name}", "object": {"sha": self._head(name)}})

        if rest == "git/refs" and request.method == "POST":
            name = body["ref"].removeprefix("refs/heads/")
            base = next((b for b in self.branches if self._head(b) == body["sha"]), None)
            if base is None:
                return httpx.Response(422, json={"message": "Object does not exist"})
            self.branches[name] = dict(self.branches[base])
            return httpx.Response(201, json={"ref": body["ref"], "object": {"sha": self._head(name)}})

        if rest == "contents" or rest.startswith("contents/"):
            fpath = rest.removeprefix("contents").lstrip("/")
            ref = params.get("ref") or body.get("branch") or "main"
            if request.method == "GET":
                return self._get_contents(fpath, ref)
            if request.method == "PUT":
                return self._put_contents(fpath, body)

        if rest == "pulls":
            if request.method == "GET":
                head = params.get("head")
                found = [p for p in self.pulls if p["state"] == "open" and f"{self.repo.split('/')[0]}:{p['head']['ref']}" == head]
                return httpx.Response(200, json=found)
            if request.method == "POST":
                if body["head"] not in self.branches:
                    return httpx.Response(422, json={"message": "head branch not found"})
                number = len(self.pulls) + 1
                pr = {"number": number, "state": "open", "title": body["title"], "body": body.get("body", ""),
                      "head": {"ref": body["head"]}, "base": {"ref": body["base"]},
                      "html_url": f"https://github.com/{self.repo}/pull/{number}"}
                self.pulls.append(pr)
                return httpx.Response(201, json=pr)

        return httpx.Response(404, json={"message": f"unhandled {request.method} {rest}"})

    # ------------------------------------------------------------------ helpers

    def _head(self, branch: str) -> str:
        return hashlib.sha1(json.dumps(sorted(self.branches[branch].items()), default=str).encode()).hexdigest()

    def _get_contents(self, fpath: str, ref: str) -> httpx.Response:
        files = self.branches.get(ref)
        if files is None:
            return httpx.Response(404, json={"message": "No commit found for the ref"})
        if fpath in files:
            data = files[fpath]
            return httpx.Response(200, json={
                "type": "file", "path": fpath, "sha": _sha(data), "size": len(data),
                "encoding": "base64", "content": base64.b64encode(data).decode(),
            })
        prefix = f"{fpath}/" if fpath else ""
        entries: dict[str, dict] = {}
        for p, data in files.items():
            if not p.startswith(prefix):
                continue
            rel = p[len(prefix):]
            if "/" in rel:
                d = rel.split("/")[0]
                entries.setdefault(d, {"type": "dir", "path": prefix + d, "size": 0, "name": d})
            else:
                entries[rel] = {"type": "file", "path": p, "size": len(data), "name": rel}
        if not entries:
            return httpx.Response(404, json={"message": "Not Found"})
        return httpx.Response(200, json=list(entries.values()))

    def _put_contents(self, fpath: str, body: dict) -> httpx.Response:
        branch = body.get("branch", "main")
        files = self.branches.get(branch)
        if files is None:
            return httpx.Response(404, json={"message": "Branch not found"})
        data = base64.b64decode(body["content"])
        if fpath in files:
            if body.get("sha") != _sha(files[fpath]):
                return httpx.Response(409, json={"message": "sha does not match"})
        elif body.get("sha"):
            return httpx.Response(422, json={"message": "sha given for a new file"})
        files[fpath] = data
        commit_sha = hashlib.sha1(f"{branch}:{fpath}:{len(self.commits)}".encode()).hexdigest()
        self.commits.append({"branch": branch, "path": fpath, "message": body["message"], "sha": commit_sha})
        return httpx.Response(200 if body.get("sha") else 201, json={
            "content": {"path": fpath, "sha": _sha(data)},
            "commit": {"sha": commit_sha, "html_url": f"https://github.com/{self.repo}/commit/{commit_sha}"},
        })
