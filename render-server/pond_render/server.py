"""The MCP server: tools render_svg, render_cad, list_renders and get_render."""

from __future__ import annotations

import json
import logging
import shutil
import tempfile
from datetime import datetime, timezone
from functools import partial
from html import escape
from pathlib import Path
from urllib.parse import quote, urlparse

import anyio
from pydantic import AnyHttpUrl
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response

from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions
from mcp.server.mcpserver import Image, MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from . import __version__
from .auth import BuiltinOAuthProvider, StaticTokenVerifier
from .config import Settings
from .github import GitHubError, GitHubRepo, RepoAccessError, RepoPolicy, slugify
from .renders import RenderRecord, file_key, list_records, load_record, new_render_id, save_record
from .sandbox.host import DEFAULT_VIEWS, run_cad_script
from .sandbox.runner import VIEW_PRESETS, resolve_view
from .storage import Store, open_store
from .svg_render import SvgRenderError, svg_to_png

log = logging.getLogger(__name__)

INSTRUCTIONS = """Pond render server. Use it to see your own drawings and CAD parts.

render_cad runs a CadQuery script in a sandbox and returns PNG views so you can check the
geometry and fix the script. Conventions:
- Units are millimetres. Z is up; the "front" view looks along +Y (X right, Z up).
- Assign the finished object to a variable named `result` (a cq.Workplane, cq.Shape or
  cq.Assembly), or call show_object(obj). `cq` and `math` are pre-imported.
- Only these modules can be imported: cadquery, math, cmath, itertools, functools, operator,
  typing, dataclasses, collections, enum, copy, random, statistics, numpy. No file or
  network access. Scripts are killed after the timeout.
- Views are hidden-line drawings; the caption on each image says which way you are looking.
Every render is stored with STEP, STL and GLB files and can be fetched again with get_render.
render_svg turns SVG markup into a PNG so you can check a 2D drawing or diagram.
When the GitHub tools are present, a successful render_cad also commits its script to
cad/<name>.py on the drafts branch; pass a stable `name` (e.g. "hand_sleeve") so iterations
of one part build up a history of one file. repo_write/repo_read/repo_list work on the same
repo; writes only ever go to claude/* branches, and Dani merges them to main."""

_cad_slots = anyio.Semaphore(2)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _text(obj: object) -> str:
    return json.dumps(obj, indent=2, default=str)


VIEWER_HOSTS = {"storage.googleapis.com", "storage.cloud.google.com"}
MODEL_VIEWER_JS = "https://cdn.jsdelivr.net/npm/@google/model-viewer@4.0.0/dist/model-viewer.min.js"


def _viewer_src_ok(src: str) -> bool:
    u = urlparse(src)
    return u.scheme == "https" and (u.hostname or "") in VIEWER_HOSTS


def _add_viewer(summary: dict, settings: Settings) -> dict:
    """Add a one-tap 3D viewer link when the GLB has a browser-loadable URL."""
    glb = (summary.get("files") or {}).get("model.glb")
    if glb and _viewer_src_ok(glb):
        title = summary.get("title") or summary.get("id") or "model"
        summary["viewer"] = f"{settings.public_url}/viewer?src={quote(glb, safe='')}&title={quote(str(title))}"
    return summary


def _viewer_page(src: str, title: str) -> str:
    t = escape(title or "Pond render")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{t}</title>
<script type="module" src="{MODEL_VIEWER_JS}"></script>
<style>
  html, body {{ margin: 0; height: 100%; background: #1d1f24; color: #e6e6e6; font: 14px/1.4 system-ui, sans-serif; }}
  model-viewer {{ width: 100%; height: 100%; background: #1d1f24; --poster-color: #1d1f24; }}
  .bar {{ position: fixed; top: 0; left: 0; right: 0; padding: 10px 14px; display: flex; gap: 12px;
         align-items: center; background: rgba(0,0,0,.35); pointer-events: none; }}
  .bar a, .bar span {{ pointer-events: auto; color: #e6e6e6; }}
  .bar strong {{ font-weight: 600; }}
  .hint {{ position: fixed; bottom: 10px; left: 0; right: 0; text-align: center; opacity: .6; font-size: 12px; }}
</style></head>
<body>
<model-viewer src="{escape(src, quote=True)}" alt="{t}" camera-controls auto-rotate shadow-intensity="1"
  exposure="1" touch-action="pan-y" interaction-prompt="none"></model-viewer>
<div class="bar"><strong>{t}</strong><span>·</span><a href="{escape(src, quote=True)}" download>download GLB</a></div>
<div class="hint">drag to orbit · scroll or pinch to zoom · Z is up in the part, shown as Y here</div>
</body></html>"""


def open_github(settings: Settings) -> GitHubRepo | None:
    """The GitHub client, or None when POND_GITHUB_TOKEN/POND_GITHUB_REPO are not set."""
    if not settings.github_enabled:
        return None
    policy = RepoPolicy(
        write_branch=settings.github_branch,
        allowed_prefixes=settings.github_write_prefixes,
        max_bytes=settings.github_max_bytes,
    )
    return GitHubRepo(token=settings.github_token or "", repo=settings.github_repo or "", policy=policy)


def build_server(settings: Settings, store: Store, github: GitHubRepo | None = None) -> MCPServer:
    token_verifier = None
    provider: BuiltinOAuthProvider | None = None
    auth_settings = None

    if settings.auth_mode == "token":
        token_verifier = StaticTokenVerifier(settings.api_token or "")
        auth_settings = AuthSettings(
            issuer_url=AnyHttpUrl(settings.public_url),
            resource_server_url=AnyHttpUrl(settings.mcp_url),
            validate_token_resource=False,
        )
    elif settings.auth_mode == "oauth":
        provider = BuiltinOAuthProvider(
            store,
            issuer=settings.public_url,
            password=settings.oauth_password or "",
            signing_secret=settings.oauth_signing_secret or "",
            resource_url=settings.mcp_url,
        )
        auth_settings = AuthSettings(
            issuer_url=AnyHttpUrl(settings.public_url),
            resource_server_url=AnyHttpUrl(settings.mcp_url),
            client_registration_options=ClientRegistrationOptions(enabled=True),
            validate_token_resource=True,
        )

    server = MCPServer(
        name="pond-render",
        title="Pond render server",
        instructions=INSTRUCTIONS,
        version=__version__,
        auth_server_provider=provider,
        token_verifier=token_verifier,
        auth=auth_settings,
    )

    # ------------------------------------------------------------------ tools

    @server.tool()
    async def render_svg(svg: str, width: int | None = None, title: str | None = None) -> list[Image | str]:
        """Render SVG markup to a PNG image you can look at.

        Args:
            svg: A complete SVG document (<svg xmlns="http://www.w3.org/2000/svg" ...>...</svg>).
            width: Output width in pixels (default: the SVG's own size; max 4096).
            title: Optional label stored with the render.
        Returns the image, plus the render id and file links.
        """
        render_id = new_render_id()
        try:
            png = await anyio.to_thread.run_sync(
                partial(svg_to_png, svg, width=width, max_bytes=settings.max_svg_bytes)
            )
        except SvgRenderError as exc:
            record = RenderRecord(id=render_id, kind="svg", created_at=_now(), status="error", title=title, error=str(exc))
            await anyio.to_thread.run_sync(_persist_svg, store, record, svg, None)
            return [f"RENDER FAILED (id {render_id}): {exc}"]

        record = RenderRecord(id=render_id, kind="svg", created_at=_now(), status="ok", title=title, views=["image"])
        await anyio.to_thread.run_sync(_persist_svg, store, record, svg, png)
        return [_text(record.summary(store)), Image(data=png, format="png")]

    @server.tool()
    async def render_cad(
        script: str,
        views: list[str] | None = None,
        show_hidden: bool = False,
        title: str | None = None,
        name: str | None = None,
        save_to_repo: bool = True,
    ) -> list[Image | str]:
        """Run a CadQuery script in a sandbox and return PNG views of the result.

        Args:
            script: Python source using CadQuery. End with `result = <Workplane|Shape|Assembly>`
                or call show_object(obj). Units mm, Z up.
            views: Any of front, back, top, bottom, right (alias side), left, iso, iso_back.
                Default: front, top, right, iso.
            show_hidden: Draw hidden edges as dashed lines.
            title: Optional label stored with the render.
            name: File stem for the auto-saved script, e.g. "hand_sleeve" -> cad/hand_sleeve.py.
                Keep it the same across iterations of one part. Defaults to a slug of `title`.
            save_to_repo: Commit the script to the GitHub drafts branch on success (when the
                GitHub tools are configured). Set false for throwaway experiments.
        Returns a summary (render id, bounding box, volume, file links for STEP/STL/GLB,
        script output, repo commit) followed by one image per view. If the script fails,
        returns the traceback so you can fix the script and call again.
        """
        if len(script.encode("utf-8")) > settings.max_script_bytes:
            return [f"RENDER FAILED: script is larger than {settings.max_script_bytes} bytes"]
        try:
            view_names = [resolve_view(v) for v in (views or DEFAULT_VIEWS)] or list(DEFAULT_VIEWS)
        except ValueError as exc:
            return [f"RENDER FAILED: {exc}"]
        seen: list[str] = []
        for v in view_names:
            if v not in seen:
                seen.append(v)
        view_names = seen[:8]

        render_id = new_render_id()
        tmp = Path(tempfile.mkdtemp(prefix="pond-cad-"))
        try:
            async with _cad_slots:
                result = await anyio.to_thread.run_sync(
                    partial(
                        run_cad_script,
                        script,
                        out_dir=tmp,
                        views=view_names,
                        timeout_s=settings.cad_timeout_s,
                        memory_mb=settings.cad_memory_mb,
                        show_hidden=show_hidden,
                        width=settings.image_width,
                    )
                )

            record = RenderRecord(
                id=render_id,
                kind="cad",
                created_at=_now(),
                status="ok" if result.ok else "error",
                title=title,
                bbox=result.bbox,
                volume_mm3=result.volume,
                solids=result.solids,
                faces=result.faces,
                views=view_names if result.ok else [],
                error=result.error,
                log=result.log or None,
                duration_s=result.duration_s,
            )
            record.files["script.py"] = file_key(render_id, "script.py")
            store.put(record.files["script.py"], script.encode("utf-8"), "text/x-python")

            images: list[Image | str] = []
            if result.ok:
                for fname, path in result.files.items():
                    key = file_key(render_id, fname)
                    await anyio.to_thread.run_sync(store.put_file, key, path)
                    record.files[fname] = key
                for view in view_names:
                    svg_path = result.svgs.get(view)
                    if not svg_path:
                        continue
                    png = await anyio.to_thread.run_sync(partial(svg_to_png, svg_path.read_text(encoding="utf-8")))
                    key = file_key(render_id, f"{view}.png")
                    await anyio.to_thread.run_sync(store.put, key, png, "image/png")
                    record.files[f"{view}.png"] = key
                    images.append(Image(data=png, format="png"))
            await anyio.to_thread.run_sync(save_record, store, record)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        if not result.ok:
            text = f"RENDER FAILED (id {render_id}, {result.duration_s} s)\n\n{result.error}"
            if result.log.strip():
                text += f"\n\nScript output:\n{result.log.strip()[-4000:]}"
            return [text]

        summary = _add_viewer(record.summary(store), settings)
        summary["duration_s"] = result.duration_s
        if result.log.strip():
            summary["script_output"] = result.log.strip()[-4000:]
        if github is not None:
            summary["repo"] = await anyio.to_thread.run_sync(
                partial(_auto_save, github, "cad", script, name=name, title=title, render_id=render_id, enabled=save_to_repo)
            )
        return [_text(summary), *images]

    @server.tool()
    async def list_renders(limit: int = 20) -> str:
        """List recent renders (newest first) with their ids, status, bounding boxes and file links."""
        records = await anyio.to_thread.run_sync(list_records, store, max(1, min(limit, 100)))
        return _text([_add_viewer(r.summary(store), settings) for r in records])

    @server.tool()
    async def get_render(render_id: str, include_images: bool = True, include_script: bool = False) -> list[Image | str]:
        """Fetch a past render by id: its summary, file links, and (optionally) its images and script."""
        record = await anyio.to_thread.run_sync(load_record, store, render_id)
        if not record:
            return [f"No render with id {render_id!r}"]
        summary = _add_viewer(record.summary(store), settings)
        if record.log:
            summary["script_output"] = record.log[-4000:]
        out: list[Image | str] = []
        if include_script and "script.py" in record.files:
            script = await anyio.to_thread.run_sync(store.get, record.files["script.py"])
            if script:
                summary["script"] = script.decode("utf-8", errors="replace")
        out.append(_text(summary))
        if include_images:
            png_names = [f"{v}.png" for v in record.views] if record.kind == "cad" else ["image.png"]
            for name in png_names:
                key = record.files.get(name)
                data = await anyio.to_thread.run_sync(store.get, key) if key else None
                if data:
                    out.append(Image(data=data, format="png"))
        return out

    # ------------------------------------------------------------------ GitHub tools

    if github is not None:
        gh = github
        branch = gh.policy.write_branch
        folders = ", ".join(gh.policy.allowed_prefixes)

        @server.tool()
        async def repo_write(path: str, content: str, message: str, branch: str | None = None) -> str:
            """Save one text file to the Pond GitHub repo as a single commit.

            Args:
                path: Repo-relative path. Writes are only allowed under the docs/, cad/ and sim/ folders.
                content: The complete file contents (UTF-8 text, max 1 MB). Replaces the file if it exists.
                message: Commit message, one line saying what changed and why.
                branch: Branch to commit to. Defaults to the drafts branch; must start with claude/.
                    Never main: Dani reviews and merges.
            Returns the commit URL and whether the file was created or updated.
            """
            try:
                res = await anyio.to_thread.run_sync(partial(gh.write_file, path, content, message, branch))
            except RepoAccessError as exc:
                return f"WRITE REFUSED: {exc}"
            except GitHubError as exc:
                return f"WRITE FAILED: {exc}"
            if not res.commit_sha:
                return _text({"path": res.path, "branch": res.branch, "changed": False, "url": res.url,
                              "note": "file already had this exact content; nothing committed"})
            return _text({"path": res.path, "branch": res.branch, "changed": True,
                          "created": res.created, "commit": res.commit_sha[:12], "url": res.url})

        @server.tool()
        async def repo_read(path: str, ref: str | None = None) -> str:
            """Read one text file from the Pond GitHub repo.

            Args:
                path: Repo-relative file path, e.g. cad/hand_sleeve.py or docs/sim-server-plan.md.
                ref: Branch, tag or commit to read from. Defaults to the drafts branch, falling
                    back to main when the file is not there.
            """
            try:
                found = await anyio.to_thread.run_sync(partial(gh.read_file, path, ref or branch))
                used = ref or branch
                if found is None and not ref:
                    found = await anyio.to_thread.run_sync(partial(gh.read_file, path, gh.policy.base_branch))
                    used = gh.policy.base_branch
            except RepoAccessError as exc:
                return f"READ REFUSED: {exc}"
            except GitHubError as exc:
                return f"READ FAILED: {exc}"
            if found is None:
                return f"No file {path!r} on {ref or branch} or {gh.policy.base_branch}"
            data, _sha = found
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                return f"READ REFUSED: {path!r} is not a text file"
            return f"# {path} @ {used}\n{text}"

        @server.tool()
        async def repo_list(dir: str = "", ref: str | None = None) -> str:
            """List a folder in the Pond GitHub repo (files and sub-folders, one per line).

            Args:
                dir: Folder path, e.g. cad or docs. Empty for the repo root.
                ref: Branch, tag or commit. Defaults to the drafts branch.
            """
            try:
                entries = await anyio.to_thread.run_sync(partial(gh.list_dir, dir, ref or branch))
                used = ref or branch
                if entries is None and not ref:
                    entries = await anyio.to_thread.run_sync(partial(gh.list_dir, dir, gh.policy.base_branch))
                    used = gh.policy.base_branch
            except RepoAccessError as exc:
                return f"LIST REFUSED: {exc}"
            except GitHubError as exc:
                return f"LIST FAILED: {exc}"
            if entries is None:
                return f"No folder {dir!r} on {ref or branch} or {gh.policy.base_branch}"
            lines = [f"# {dir or '/'} @ {used}"]
            for e in sorted(entries, key=lambda e: (e.type != "dir", e.path)):
                lines.append(f"{e.path}/" if e.type == "dir" else f"{e.path}  ({e.size} bytes)")
            return "\n".join(lines)

        @server.tool()
        async def repo_open_pr(title: str, body: str = "") -> str:
            """Open a pull request from the drafts branch to main so Dani can review and merge.

            If a PR from the drafts branch is already open, returns that one instead.
            Args:
                title: Short PR title.
                body: What changed and anything Dani should check before merging.
            """
            try:
                pr = await anyio.to_thread.run_sync(partial(gh.open_pr, title, body, branch))
            except RepoAccessError as exc:
                return f"PR REFUSED: {exc}"
            except GitHubError as exc:
                return f"PR FAILED: {exc}"
            return _text(pr)

        log.info("GitHub tools enabled: repo %s, branch %s, folders %s", gh.repo, branch, folders)

    # ------------------------------------------------------------------ plain HTTP routes

    @server.custom_route("/health", methods=["GET"])
    async def healthz(request: Request) -> Response:
        return JSONResponse({"ok": True, "version": __version__, "storage": store.describe()})

    @server.custom_route("/viewer", methods=["GET"])
    async def viewer(request: Request) -> Response:
        """A static page that shows one GLB in the browser. Holds no data itself: the model comes
        from the (time-limited, signed) storage URL in `src`, which must point at our bucket host."""
        src = request.query_params.get("src", "")
        if not _viewer_src_ok(src):
            return PlainTextResponse("src must be an https URL on " + ", ".join(sorted(VIEWER_HOSTS)), status_code=400)
        return HTMLResponse(_viewer_page(src, request.query_params.get("title", "")[:120]))

    @server.custom_route("/", methods=["GET"])
    async def index(request: Request) -> Response:
        return PlainTextResponse(
            f"Pond render server {__version__}\nMCP endpoint: {settings.mcp_url}\nAuth: {settings.auth_mode}\n"
        )

    if provider is not None:

        @server.custom_route("/login", methods=["GET"])
        async def login_get(request: Request) -> Response:
            return await provider.login_get(request)

        @server.custom_route("/login", methods=["POST"])
        async def login_post(request: Request) -> Response:
            return await provider.login_post(request)

    return server


def _auto_save(
    github: GitHubRepo, folder: str, script: str, *, name: str | None, title: str | None,
    render_id: str, enabled: bool,
) -> dict:
    """Commit a successful render's script to <folder>/<name>.py on the drafts branch.

    Never raises: the render already succeeded, so a failed commit is reported, not fatal.
    """
    if not enabled:
        return {"saved": False, "note": "save_to_repo was false"}
    stem = slugify(name or title or "", default="")
    if not stem:
        return {"saved": False, "note": "give a `name` (or `title`) to save the script to the repo"}
    path = f"{folder}/{stem}.py"
    message = f"render {render_id}: {title or stem}"
    try:
        res = github.write_file(path, script, message)
    except (RepoAccessError, GitHubError) as exc:
        log.warning("auto-save of %s failed: %s", path, exc)
        return {"saved": False, "path": path, "error": str(exc)}
    except Exception as exc:  # noqa: BLE001 - network hiccups must not fail the render
        log.warning("auto-save of %s failed: %s", path, exc)
        return {"saved": False, "path": path, "error": f"{type(exc).__name__}: {exc}"}
    if not res.commit_sha:
        return {"saved": True, "path": res.path, "branch": res.branch, "changed": False, "url": res.url}
    return {"saved": True, "path": res.path, "branch": res.branch, "changed": True,
            "commit": res.commit_sha[:12], "url": res.url}


def _persist_svg(store: Store, record: RenderRecord, svg: str, png: bytes | None) -> None:
    record.files["image.svg"] = file_key(record.id, "image.svg")
    store.put(record.files["image.svg"], svg.encode("utf-8"), "image/svg+xml")
    if png is not None:
        record.files["image.png"] = file_key(record.id, "image.png")
        store.put(record.files["image.png"], png, "image/png")
    save_record(store, record)


def build_app(
    settings: Settings | None = None, store: Store | None = None, github: GitHubRepo | None = None
) -> Starlette:
    settings = settings or Settings.from_env()
    store = store or open_store(settings.storage)
    github = github or open_github(settings)
    log.info("Pond render server %s; storage: %s; auth: %s; public URL: %s; github: %s",
             __version__, store.describe(), settings.auth_mode, settings.public_url,
             github.repo if github else "off")
    server = build_server(settings, store, github)

    host = settings.public_host
    allowed_hosts = sorted({host, f"{host}:*", "localhost:*", "127.0.0.1:*", "localhost", "127.0.0.1"})
    transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=allowed_hosts,
        allowed_origins=sorted({settings.public_url, "http://localhost:*", "http://127.0.0.1:*"}),
    )
    return server.streamable_http_app(
        streamable_http_path="/mcp",
        stateless_http=settings.stateless,
        json_response=True,
        transport_security=transport_security,
        host=settings.host,
    )
