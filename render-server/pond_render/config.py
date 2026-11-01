"""Settings, read from POND_* environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(f"POND_{name}")
    if value is None or value == "":
        return default
    return value


def _env_int(name: str, default: int) -> int:
    raw = _env(name)
    return int(raw) if raw is not None else default


def _env_bool(name: str, default: bool) -> bool:
    raw = _env(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    public_url: str
    host: str
    port: int
    storage: str
    auth_mode: str  # "none" | "token" | "oauth"
    api_token: str | None
    oauth_password: str | None
    oauth_signing_secret: str | None
    cad_timeout_s: int
    cad_memory_mb: int
    max_script_bytes: int
    max_svg_bytes: int
    image_width: int
    stateless: bool
    log_level: str
    github_token: str | None = None
    github_repo: str | None = None  # "owner/name"
    github_branch: str = "claude/drafts"
    github_write_prefixes: tuple[str, ...] = ("docs/", "cad/", "sim/")
    github_max_bytes: int = 1_048_576

    @property
    def github_enabled(self) -> bool:
        return bool(self.github_token and self.github_repo)

    @classmethod
    def from_env(cls) -> "Settings":
        port = int(os.environ.get("PORT") or _env("PORT", "8080"))  # Cloud Run sets PORT
        settings = cls(
            public_url=(_env("PUBLIC_URL", f"http://localhost:{port}") or "").rstrip("/"),
            host=_env("HOST", "127.0.0.1") or "127.0.0.1",
            port=port,
            storage=_env("STORAGE", "local:./renders") or "local:./renders",
            auth_mode=(_env("AUTH_MODE", "token") or "token").lower(),
            api_token=_env("API_TOKEN"),
            oauth_password=_env("OAUTH_PASSWORD"),
            oauth_signing_secret=_env("OAUTH_SIGNING_SECRET"),
            cad_timeout_s=_env_int("CAD_TIMEOUT_S", 60),
            cad_memory_mb=_env_int("CAD_MEMORY_MB", 3072),
            max_script_bytes=_env_int("MAX_SCRIPT_BYTES", 200_000),
            max_svg_bytes=_env_int("MAX_SVG_BYTES", 2_000_000),
            image_width=_env_int("IMAGE_WIDTH", 800),
            stateless=_env_bool("STATELESS", True),
            log_level=(_env("LOG_LEVEL", "INFO") or "INFO").upper(),
            github_token=_env("GITHUB_TOKEN"),
            github_repo=_env("GITHUB_REPO"),
            github_branch=_env("GITHUB_BRANCH", "claude/drafts") or "claude/drafts",
            github_write_prefixes=tuple(
                p.strip().strip("/") + "/"
                for p in (_env("GITHUB_WRITE_PREFIXES", "docs,cad,sim") or "").split(",")
                if p.strip().strip("/")
            ),
            github_max_bytes=_env_int("GITHUB_MAX_BYTES", 1_048_576),
        )
        settings.validate()
        return settings

    @property
    def public_host(self) -> str:
        return urlparse(self.public_url).hostname or "localhost"

    @property
    def is_local(self) -> bool:
        return self.public_host in LOCAL_HOSTS

    @property
    def mcp_url(self) -> str:
        return f"{self.public_url}/mcp"

    def validate(self) -> None:
        if self.auth_mode not in {"none", "token", "oauth"}:
            raise ValueError("POND_AUTH_MODE must be none, token or oauth")
        if self.auth_mode == "none" and not self.is_local:
            raise ValueError(
                "POND_AUTH_MODE=none is only allowed when POND_PUBLIC_URL is localhost. "
                "This server runs arbitrary CadQuery scripts; never expose it without auth."
            )
        if self.auth_mode == "token" and not self.api_token:
            raise ValueError("POND_AUTH_MODE=token needs POND_API_TOKEN")
        if self.auth_mode == "oauth":
            if not self.oauth_password or not self.oauth_signing_secret:
                raise ValueError("POND_AUTH_MODE=oauth needs POND_OAUTH_PASSWORD and POND_OAUTH_SIGNING_SECRET")
            if len(self.oauth_signing_secret) < 32:
                raise ValueError("POND_OAUTH_SIGNING_SECRET should be at least 32 characters (try: openssl rand -hex 32)")
            if len(self.oauth_password) < 12:
                raise ValueError("POND_OAUTH_PASSWORD should be at least 12 characters")
        if not self.public_url.startswith(("http://", "https://")):
            raise ValueError("POND_PUBLIC_URL must start with http:// or https://")
        if bool(self.github_token) != bool(self.github_repo):
            raise ValueError("POND_GITHUB_TOKEN and POND_GITHUB_REPO must be set together")
        if self.github_enabled:
            if self.github_branch in {"main", "master"} or not self.github_branch.startswith("claude/"):
                raise ValueError("POND_GITHUB_BRANCH must start with claude/ (never main)")
            if not self.github_write_prefixes:
                raise ValueError("POND_GITHUB_WRITE_PREFIXES must name at least one folder")
