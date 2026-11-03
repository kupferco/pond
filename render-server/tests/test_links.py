"""Short file links: the code format, and the /s and /v routes on a running server."""

import json
from pathlib import Path

import httpx
import pytest

from mcp import types

from pond_render.links import ShortLinks
from pond_render.storage import LocalStore
from tests.conftest import API_TOKEN, RunningServer, _free_port, make_settings
from tests.mcp_helpers import call_tool

FAKE_BUCKET = "https://storage.googleapis.com/fake-bucket/"
BOX = "result = cq.Workplane('XY').box(10, 10, 10)"


class FakeWebStore(LocalStore):
    """Local files, but URLs that look like signed bucket links, as GCS gives in production."""

    web_links = True

    def url(self, key: str) -> str:
        return FAKE_BUCKET + key + "?X-Goog-Signature=" + "a" * 500


@pytest.fixture
def web_server(tmp_path):
    settings = make_settings(tmp_path, _free_port())
    srv = RunningServer(settings, store=FakeWebStore(Path(tmp_path / "renders"))).start()
    yield srv
    srv.stop()


def test_code_roundtrip_and_tamper():
    links = ShortLinks("secret-one", "https://x.run.app/")
    code = links.code("20261103-091500-c0de", "clip_side.mp4")
    assert code and len(code) <= 16
    assert links.resolve(code, "clip_side.mp4") == "20261103-091500-c0de"
    assert links.file_url("20261103-091500-c0de", "a.png").startswith("https://x.run.app/s/")
    assert links.resolve(code, "model.glb") is None  # the hash covers the file name
    assert ShortLinks("secret-two", "https://x.run.app").resolve(code, "clip_side.mp4") is None
    flipped = code[:-1] + ("A" if code[-1] != "A" else "B")
    assert links.resolve(flipped, "clip_side.mp4") is None
    for bad in ("", "!!!!!!!!!", "z" * 24, "abc"):
        assert links.resolve(bad, "clip_side.mp4") is None
    assert links.code("not-an-id", "a.png") is None and links.code("20261103-091500-c0de", "../x") is None


def test_short_links_in_summaries_and_redirects(web_server):
    base = web_server.base_url
    result = call_tool(web_server.mcp_url, API_TOKEN, "render_svg", {"svg": '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"/>'})
    summary = json.loads([c.text for c in result.content if isinstance(c, types.TextContent)][0])
    png = summary["files"]["image.png"]
    assert png.startswith(base + "/s/") and png.endswith("/image.png") and len(png) < 80

    r = httpx.get(png, follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"].startswith(FAKE_BUCKET + "renders/" + summary["id"] + "/image.png")
    assert r.headers["cache-control"] == "no-store"

    code = png.split("/s/")[1].split("/")[0]
    assert httpx.get(f"{base}/s/{code}/image.svg").status_code == 404  # code is for image.png only
    assert httpx.get(f"{base}/s/{code[:-1]}x/image.png").status_code == 404
    assert httpx.get(f"{base}/s/{code}/nope.png").status_code == 404


def test_short_viewer_link(web_server):
    base = web_server.base_url
    result = call_tool(web_server.mcp_url, API_TOKEN, "render_cad", {"script": BOX, "views": ["iso"], "title": "Little <box>"})
    summary = json.loads([c.text for c in result.content if isinstance(c, types.TextContent)][0])
    assert summary["viewer"].startswith(base + "/v/") and len(summary["viewer"]) < 60
    page = httpx.get(summary["viewer"])
    assert page.status_code == 200 and "<model-viewer" in page.text and "Little &lt;box&gt;" in page.text
    assert (FAKE_BUCKET + "renders/" + summary["id"] + "/model.glb") in page.text
    assert httpx.get(base + "/v/AAAAAAAAAAAA").status_code == 404


def test_no_short_links_for_local_storage(token_server):
    result = call_tool(token_server.mcp_url, API_TOKEN, "render_svg", {"svg": '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"/>'})
    summary = json.loads([c.text for c in result.content if isinstance(c, types.TextContent)][0])
    assert summary["files"]["image.png"].startswith("file://")
    assert httpx.get(token_server.base_url + "/s/AAAAAAAAAAAA/image.png").status_code == 404
