"""The MCP server: tools render_svg, render_cad, list_renders and get_render."""

from __future__ import annotations

import json
import logging
import shutil
import tempfile
from datetime import datetime, timezone
from functools import partial
from pathlib import Path

import anyio
from pydantic import AnyHttpUrl
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse, Response

from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions
from mcp.server.mcpserver import Image, MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from . import __version__
from .auth import BuiltinOAuthProvider, StaticTokenVerifier
from .config import Settings
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
render_svg turns SVG markup into a PNG so you can check a 2D drawing or diagram."""

_cad_slots = anyio.Semaphore(2)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _text(obj: object) -> str:
    return json.dumps(obj, indent=2, default=str)


def build_server(settings: Settings, store: Store) -> MCPServer:
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
    ) -> list[Image | str]:
        """Run a CadQuery script in a sandbox and return PNG views of the result.

        Args:
            script: Python source using CadQuery. End with `result = <Workplane|Shape|Assembly>`
                or call show_object(obj). Units mm, Z up.
            views: Any of front, back, top, bottom, right (alias side), left, iso, iso_back.
                Default: front, top, right, iso.
            show_hidden: Draw hidden edges as dashed lines.
            title: Optional label stored with the render.
        Returns a summary (render id, bounding box, volume, file links for STEP/STL/GLB,
        script output) followed by one image per view. If the script fails, returns the
        traceback so you can fix the script and call again.
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
                for name, path in result.files.items():
                    key = file_key(render_id, name)
                    await anyio.to_thread.run_sync(store.put_file, key, path)
                    record.files[name] = key
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

        summary = record.summary(store)
        summary["duration_s"] = result.duration_s
        if result.log.strip():
            summary["script_output"] = result.log.strip()[-4000:]
        return [_text(summary), *images]

    @server.tool()
    async def list_renders(limit: int = 20) -> str:
        """List recent renders (newest first) with their ids, status, bounding boxes and file links."""
        records = await anyio.to_thread.run_sync(list_records, store, max(1, min(limit, 100)))
        return _text([r.summary(store) for r in records])

    @server.tool()
    async def get_render(render_id: str, include_images: bool = True, include_script: bool = False) -> list[Image | str]:
        """Fetch a past render by id: its summary, file links, and (optionally) its images and script."""
        record = await anyio.to_thread.run_sync(load_record, store, render_id)
        if not record:
            return [f"No render with id {render_id!r}"]
        summary = record.summary(store)
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

    # ------------------------------------------------------------------ plain HTTP routes

    @server.custom_route("/healthz", methods=["GET"])
    async def healthz(request: Request) -> Response:
        return JSONResponse({"ok": True, "version": __version__, "storage": store.describe()})

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


def _persist_svg(store: Store, record: RenderRecord, svg: str, png: bytes | None) -> None:
    record.files["image.svg"] = file_key(record.id, "image.svg")
    store.put(record.files["image.svg"], svg.encode("utf-8"), "image/svg+xml")
    if png is not None:
        record.files["image.png"] = file_key(record.id, "image.png")
        store.put(record.files["image.png"], png, "image/png")
    save_record(store, record)


def build_app(settings: Settings | None = None, store: Store | None = None) -> Starlette:
    settings = settings or Settings.from_env()
    store = store or open_store(settings.storage)
    log.info("Pond render server %s; storage: %s; auth: %s; public URL: %s",
             __version__, store.describe(), settings.auth_mode, settings.public_url)
    server = build_server(settings, store)

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
