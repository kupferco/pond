import json

import httpx

from mcp import types

from tests.conftest import API_TOKEN
from tests.mcp_helpers import call_tool, list_tools

SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="120" height="60"><circle cx="60" cy="30" r="25" fill="tomato"/></svg>'
BOX = 'result = cq.Workplane("XY").box(40, 20, 30).faces(">Z").workplane().hole(8)\n'


def _texts(result):
    return [c.text for c in result.content if isinstance(c, types.TextContent)]


def _images(result):
    return [c for c in result.content if isinstance(c, types.ImageContent)]


def test_mcp_requires_token(token_server):
    r = httpx.post(token_server.mcp_url, json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
                   headers={"Accept": "application/json, text/event-stream"})
    assert r.status_code == 401
    assert "resource_metadata" in r.headers.get("www-authenticate", "")
    r = httpx.post(token_server.mcp_url, json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
                   headers={"Accept": "application/json, text/event-stream", "Authorization": "Bearer wrong"})
    assert r.status_code == 401


def test_healthz_and_index_open(token_server):
    assert httpx.get(token_server.base_url + "/health").json()["ok"] is True
    assert "MCP endpoint" in httpx.get(token_server.base_url + "/").text


def test_tools_listed(token_server):
    tools = list_tools(token_server.mcp_url, API_TOKEN)
    assert {t.name for t in tools.tools} == {"render_svg", "render_cad", "list_renders", "get_render"}


def test_render_svg_tool(token_server):
    result = call_tool(token_server.mcp_url, API_TOKEN, "render_svg", {"svg": SVG, "title": "circle"})
    assert not result.is_error
    images = _images(result)
    assert len(images) == 1 and images[0].mime_type == "image/png"
    summary = json.loads(_texts(result)[0])
    assert summary["status"] == "ok" and summary["title"] == "circle"
    assert set(summary["files"]) == {"image.svg", "image.png"}


def test_render_svg_failure_is_text(token_server):
    result = call_tool(token_server.mcp_url, API_TOKEN, "render_svg", {"svg": "<nope"})
    assert "RENDER FAILED" in _texts(result)[0]


def test_render_cad_roundtrip(token_server):
    result = call_tool(token_server.mcp_url, API_TOKEN, "render_cad", {"script": BOX, "views": ["front", "top", "side", "iso"]})
    assert not result.is_error, result
    images = _images(result)
    assert len(images) == 4
    assert all(i.mime_type == "image/png" for i in images)
    summary = json.loads(_texts(result)[0])
    assert summary["status"] == "ok"
    assert summary["bbox_mm"]["size"] == [40.0, 20.0, 30.0]
    assert {"model.step", "model.stl", "model.glb", "script.py", "front.png", "top.png", "right.png", "iso.png"} <= set(summary["files"])
    render_id = summary["id"]

    listing = json.loads(_texts(call_tool(token_server.mcp_url, API_TOKEN, "list_renders", {}))[0])
    assert listing[0]["id"] == render_id

    fetched = call_tool(token_server.mcp_url, API_TOKEN, "get_render", {"render_id": render_id, "include_script": True})
    assert len(_images(fetched)) == 4
    assert json.loads(_texts(fetched)[0])["script"] == BOX

    missing = call_tool(token_server.mcp_url, API_TOKEN, "get_render", {"render_id": "nope"})
    assert "No render" in _texts(missing)[0]


def test_render_cad_error_returns_traceback(token_server):
    result = call_tool(token_server.mcp_url, API_TOKEN, "render_cad", {"script": "import os\n"})
    text = _texts(result)[0]
    assert "RENDER FAILED" in text and "not allowed" in text
    assert not _images(result)


def test_viewer_page(token_server):
    base = token_server.base_url
    src = "https://storage.googleapis.com/pond-render-kupfer-renders/renders/x/model.glb?X-Goog-Signature=abc"
    r = httpx.get(base + "/viewer", params={"src": src, "title": "Hand <sleeve>"})
    assert r.status_code == 200 and "text/html" in r.headers["content-type"]
    assert "<model-viewer" in r.text and "model-viewer.min.js" in r.text
    assert "Hand &lt;sleeve&gt;" in r.text and src.replace("&", "&amp;") in r.text
    # only our storage hosts, only https
    assert httpx.get(base + "/viewer", params={"src": "https://evil.example/x.glb"}).status_code == 400
    assert httpx.get(base + "/viewer", params={"src": "http://storage.googleapis.com/x.glb"}).status_code == 400
    assert httpx.get(base + "/viewer").status_code == 400


def test_viewer_link_only_for_browser_loadable_glb(token_server):
    # local file:// URLs can't be loaded by a browser page, so no viewer link is offered
    result = call_tool(token_server.mcp_url, API_TOKEN, "render_cad", {"script": BOX, "views": ["iso"]})
    summary = json.loads(_texts(result)[0])
    assert "model.glb" in summary["files"] and "viewer" not in summary
