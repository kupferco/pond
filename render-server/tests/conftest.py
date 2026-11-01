from __future__ import annotations

import socket
import threading
import time
from pathlib import Path

import httpx
import pytest
import uvicorn

from pond_render.config import Settings
from pond_render.server import build_app

OAUTH_PASSWORD = "correct-horse-battery"
OAUTH_SECRET = "0123456789abcdef0123456789abcdef0123456789abcdef"
API_TOKEN = "test-token-123"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def make_settings(tmp_path: Path, port: int, **overrides) -> Settings:
    base = dict(
        public_url=f"http://127.0.0.1:{port}",
        host="127.0.0.1",
        port=port,
        storage=f"local:{tmp_path / 'renders'}",
        auth_mode="token",
        api_token=API_TOKEN,
        oauth_password=None,
        oauth_signing_secret=None,
        cad_timeout_s=120,
        cad_memory_mb=3072,
        max_script_bytes=200_000,
        max_svg_bytes=2_000_000,
        image_width=800,
        stateless=True,
        log_level="WARNING",
    )
    base.update(overrides)
    settings = Settings(**base)
    settings.validate()
    return settings


class RunningServer:
    def __init__(self, settings: Settings, github=None):
        self.settings = settings
        self.base_url = settings.public_url
        self.mcp_url = settings.mcp_url
        config = uvicorn.Config(build_app(settings, github=github), host=settings.host, port=settings.port, log_level="warning")
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(target=self._server.run, daemon=True)

    def start(self) -> "RunningServer":
        self._thread.start()
        deadline = time.time() + 20
        while time.time() < deadline:
            try:
                if httpx.get(self.base_url + "/health", timeout=1).status_code == 200:
                    return self
            except httpx.HTTPError:
                time.sleep(0.1)
        raise RuntimeError("server did not start")

    def stop(self) -> None:
        self._server.should_exit = True
        self._thread.join(timeout=10)


@pytest.fixture
def token_server(tmp_path):
    srv = RunningServer(make_settings(tmp_path, _free_port())).start()
    yield srv
    srv.stop()


@pytest.fixture
def github_server(tmp_path):
    """Token-auth server with the GitHub tools wired to an in-memory fake GitHub."""
    from tests.fake_github import FakeGitHub

    fake = FakeGitHub()
    settings = make_settings(tmp_path, _free_port(), github_token=fake.token, github_repo=fake.repo)
    srv = RunningServer(settings, github=fake.client()).start()
    srv.fake = fake
    yield srv
    srv.stop()


@pytest.fixture
def oauth_server(tmp_path):
    settings = make_settings(
        tmp_path, _free_port(), auth_mode="oauth", api_token=None,
        oauth_password=OAUTH_PASSWORD, oauth_signing_secret=OAUTH_SECRET,
    )
    srv = RunningServer(settings).start()
    yield srv
    srv.stop()
