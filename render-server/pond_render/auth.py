"""Authentication for the render server.

Two modes:

* token  - a static bearer token (POND_API_TOKEN). Good for local tests, scripts and the
           Claude API's MCP connector, which can send a fixed Authorization header.
* oauth  - a small built-in OAuth 2.1 authorization server, which is what a Claude.ai
           custom connector needs. It supports dynamic client registration and PKCE.
           When Claude connects, the browser shows a password prompt; the password is
           POND_OAUTH_PASSWORD. Tokens are signed JWTs (HS256, POND_OAUTH_SIGNING_SECRET),
           so no token state has to survive a Cloud Run cold start. Registered clients are
           kept in the store (auth/clients/<id>.json). Rotating the signing secret logs
           every client out.
"""

from __future__ import annotations

import hmac
import logging
import re
import secrets
import time
from html import escape
from typing import Any
from urllib.parse import urlparse

import anyio
import jwt
from pydantic import AnyUrl
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    IdentityAssertionParams,
    RefreshToken,
    RegistrationError,
    TokenError,
    TokenVerifier,
    construct_redirect_uri,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

from .storage import Store

log = logging.getLogger(__name__)

AUDIENCE = "pond-render"
ACCESS_TTL_S = 60 * 60
REFRESH_TTL_S = 30 * 24 * 60 * 60
CODE_TTL_S = 5 * 60
LOGIN_TTL_S = 10 * 60
_CLIENT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,128}$")


class StaticTokenVerifier(TokenVerifier):
    def __init__(self, token: str):
        self._token = token

    async def verify_token(self, token: str) -> AccessToken | None:
        if hmac.compare_digest(token.encode(), self._token.encode()):
            return AccessToken(token=token, client_id="static-token", scopes=["render"])
        return None


class BuiltinOAuthProvider:
    """OAuthAuthorizationServerProvider + TokenVerifier for a single-owner server."""

    def __init__(self, store: Store, *, issuer: str, password: str, signing_secret: str, resource_url: str):
        self.store = store
        self.issuer = issuer.rstrip("/")
        self.password = password
        self.secret = signing_secret
        self.resource_url = resource_url
        self._used_codes: dict[str, float] = {}

    # --- JWT helpers -------------------------------------------------------------------

    def _sign(self, typ: str, claims: dict[str, Any], ttl_s: int) -> str:
        now = int(time.time())
        payload = {**claims, "typ": typ, "iss": self.issuer, "aud": AUDIENCE, "iat": now, "exp": now + ttl_s,
                   "jti": secrets.token_hex(8)}
        return jwt.encode(payload, self.secret, algorithm="HS256")

    def _verify(self, token: str | None, typ: str) -> dict[str, Any] | None:
        if not token:
            return None
        try:
            data = jwt.decode(token, self.secret, algorithms=["HS256"], audience=AUDIENCE, issuer=self.issuer)
        except jwt.PyJWTError:
            return None
        return data if data.get("typ") == typ else None

    def _issue(self, client_id: str, scopes: list[str], resource: str | None) -> OAuthToken:
        claims = {"client_id": client_id, "scopes": scopes, "resource": resource or self.resource_url}
        return OAuthToken(
            access_token=self._sign("access", claims, ACCESS_TTL_S),
            token_type="Bearer",
            expires_in=ACCESS_TTL_S,
            scope=" ".join(scopes) or None,
            refresh_token=self._sign("refresh", claims, REFRESH_TTL_S),
        )

    # --- client registry ---------------------------------------------------------------

    def _client_key(self, client_id: str) -> str:
        if not _CLIENT_ID_RE.match(client_id or ""):
            raise ValueError("invalid client id")
        return f"auth/clients/{client_id}.json"

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        try:
            key = self._client_key(client_id)
        except ValueError:
            return None
        raw = await anyio.to_thread.run_sync(self.store.get, key)
        return OAuthClientInformationFull.model_validate_json(raw) if raw else None

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        for uri in client_info.redirect_uris or []:
            parsed = urlparse(str(uri))
            local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
            if parsed.scheme != "https" and not (parsed.scheme == "http" and local):
                raise RegistrationError(
                    error="invalid_redirect_uri",
                    error_description=f"redirect_uri must use https (or http on localhost): {uri}",
                )
        key = self._client_key(client_info.client_id)
        log.info("Registered OAuth client %s (%s)", client_info.client_id, client_info.client_name)
        await anyio.to_thread.run_sync(
            self.store.put, key, client_info.model_dump_json(exclude_none=True).encode(), "application/json"
        )

    # --- authorization code flow -------------------------------------------------------

    async def authorize(self, client: OAuthClientInformationFull, params: AuthorizationParams) -> str:
        req = self._sign(
            "login",
            {
                "client_id": client.client_id,
                "state": params.state,
                "scopes": params.scopes or [],
                "code_challenge": params.code_challenge,
                "redirect_uri": str(params.redirect_uri),
                "explicit": params.redirect_uri_provided_explicitly,
            },
            LOGIN_TTL_S,
        )
        return f"{self.issuer}/login?req={req}"

    async def load_authorization_code(self, client: OAuthClientInformationFull, authorization_code: str) -> AuthorizationCode | None:
        data = self._verify(authorization_code, "code")
        if not data or data.get("client_id") != client.client_id:
            return None
        self._expire_used_codes()
        if data["jti"] in self._used_codes:
            return None
        return AuthorizationCode(
            code=authorization_code,
            scopes=data.get("scopes") or [],
            expires_at=float(data["exp"]),
            client_id=client.client_id,
            code_challenge=data["code_challenge"],
            redirect_uri=AnyUrl(data["redirect_uri"]),
            redirect_uri_provided_explicitly=bool(data.get("explicit")),
            resource=self.resource_url,
        )

    async def exchange_authorization_code(self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode) -> OAuthToken:
        data = self._verify(authorization_code.code, "code") or {}
        if data.get("jti"):
            self._used_codes[data["jti"]] = time.time() + CODE_TTL_S
        return self._issue(client.client_id, authorization_code.scopes, authorization_code.resource)

    async def load_refresh_token(self, client: OAuthClientInformationFull, refresh_token: str) -> RefreshToken | None:
        data = self._verify(refresh_token, "refresh")
        if not data or data.get("client_id") != client.client_id:
            return None
        return RefreshToken(
            token=refresh_token,
            client_id=client.client_id,
            scopes=data.get("scopes") or [],
            expires_at=int(data["exp"]),
            resource=data.get("resource") or self.resource_url,
        )

    async def exchange_refresh_token(self, client: OAuthClientInformationFull, refresh_token: RefreshToken, scopes: list[str]) -> OAuthToken:
        return self._issue(client.client_id, scopes or refresh_token.scopes, refresh_token.resource)

    async def load_access_token(self, token: str) -> AccessToken | None:
        data = self._verify(token, "access")
        if not data:
            return None
        return AccessToken(
            token=token,
            client_id=data.get("client_id", ""),
            scopes=data.get("scopes") or [],
            expires_at=int(data["exp"]),
            resource=data.get("resource") or self.resource_url,
            claims={"iss": data.get("iss")},
        )

    async def verify_token(self, token: str) -> AccessToken | None:
        return await self.load_access_token(token)

    async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
        log.info("Token revocation requested for client %s; tokens are stateless, rotate the signing secret to revoke all", token.client_id)

    async def exchange_identity_assertion(self, client: OAuthClientInformationFull, params: IdentityAssertionParams) -> OAuthToken:
        raise TokenError(error="unsupported_grant_type", error_description="identity assertion is not supported")

    def _expire_used_codes(self) -> None:
        now = time.time()
        for jti, until in list(self._used_codes.items()):
            if until < now:
                del self._used_codes[jti]

    # --- login page --------------------------------------------------------------------

    def _login_page(self, req: str, error: str | None = None, status: int = 200) -> Response:
        error_html = f'<p class="err">{escape(error)}</p>' if error else ""
        html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pond render server</title>
<style>
 body {{ font-family: -apple-system, system-ui, sans-serif; background:#f5f6f8; color:#1b1f24; display:flex; justify-content:center; padding:48px 16px; }}
 form {{ background:#fff; padding:28px; border-radius:12px; box-shadow:0 2px 12px rgba(0,0,0,.08); width:100%; max-width:360px; }}
 h1 {{ font-size:20px; margin:0 0 6px; }} p {{ margin:0 0 18px; color:#555; font-size:14px; }}
 input[type=password] {{ width:100%; padding:10px; font-size:16px; border:1px solid #c9ccd1; border-radius:8px; box-sizing:border-box; }}
 button {{ margin-top:14px; width:100%; padding:10px; font-size:16px; border:0; border-radius:8px; background:#2563eb; color:#fff; }}
 .err {{ color:#b91c1c; }}
</style></head><body>
<form method="post" action="/login">
 <h1>Pond render server</h1>
 <p>A client is asking to connect. Enter the server password to allow it.</p>
 {error_html}
 <input type="hidden" name="req" value="{escape(req)}">
 <input type="password" name="password" autofocus autocomplete="current-password" placeholder="Password">
 <button type="submit">Allow access</button>
</form></body></html>"""
        return HTMLResponse(html, status_code=status)

    async def login_get(self, request: Request) -> Response:
        req = request.query_params.get("req")
        if not self._verify(req, "login"):
            return HTMLResponse("<p>This login link is invalid or has expired. Start the connection again.</p>", status_code=400)
        return self._login_page(req)

    async def login_post(self, request: Request) -> Response:
        form = await request.form()
        req = str(form.get("req") or "")
        data = self._verify(req, "login")
        if not data:
            return HTMLResponse("<p>This login link is invalid or has expired. Start the connection again.</p>", status_code=400)
        password = str(form.get("password") or "")
        if not hmac.compare_digest(password.encode(), self.password.encode()):
            await anyio.sleep(1.5)  # slow down guessing
            log.warning("Failed login attempt for client %s", data.get("client_id"))
            return self._login_page(req, error="Wrong password.", status=401)
        code = self._sign(
            "code",
            {
                "client_id": data["client_id"],
                "scopes": data.get("scopes") or [],
                "code_challenge": data["code_challenge"],
                "redirect_uri": data["redirect_uri"],
                "explicit": data.get("explicit", False),
            },
            CODE_TTL_S,
        )
        url = construct_redirect_uri(data["redirect_uri"], code=code, state=data.get("state"))
        log.info("Authorized client %s", data["client_id"])
        return RedirectResponse(url, status_code=303)
