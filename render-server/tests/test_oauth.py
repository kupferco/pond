import base64
import hashlib
import secrets
from urllib.parse import parse_qs, urlparse

import httpx

from mcp import types

from tests.conftest import OAUTH_PASSWORD
from tests.mcp_helpers import call_tool

SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20"><rect width="20" height="20"/></svg>'


def _pkce():
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    return verifier, challenge


def test_full_oauth_flow(oauth_server):
    base = oauth_server.base_url
    mcp_url = oauth_server.mcp_url

    # Discovery, as a Claude custom connector does it.
    prm = httpx.get(base + "/.well-known/oauth-protected-resource/mcp").json()
    assert prm["resource"].rstrip("/") == mcp_url
    assert prm["authorization_servers"][0].rstrip("/") == base
    asm = httpx.get(base + "/.well-known/oauth-authorization-server").json()
    assert asm["registration_endpoint"] and asm["token_endpoint"] and asm["authorization_endpoint"]
    assert "S256" in asm.get("code_challenge_methods_supported", ["S256"])

    # Dynamic client registration.
    redirect_uri = "https://claude.ai/api/mcp/auth_callback"
    reg = httpx.post(asm["registration_endpoint"], json={
        "client_name": "test client", "redirect_uris": [redirect_uri],
        "token_endpoint_auth_method": "none", "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
    })
    assert reg.status_code == 201, reg.text
    client_id = reg.json()["client_id"]

    bad_reg = httpx.post(asm["registration_endpoint"], json={"client_name": "x", "redirect_uris": ["http://evil.example/cb"]})
    assert bad_reg.status_code == 400

    # Authorize -> login page.
    verifier, challenge = _pkce()
    auth = httpx.get(asm["authorization_endpoint"], params={
        "response_type": "code", "client_id": client_id, "redirect_uri": redirect_uri,
        "code_challenge": challenge, "code_challenge_method": "S256", "state": "xyz", "resource": mcp_url,
    }, follow_redirects=False)
    assert auth.status_code in (302, 303, 307), auth.text
    login_url = auth.headers["location"]
    assert login_url.startswith(base + "/login?req=")
    page = httpx.get(login_url)
    assert page.status_code == 200 and 'name="password"' in page.text
    req = parse_qs(urlparse(login_url).query)["req"][0]

    # Wrong password is refused, right password redirects back with a code.
    wrong = httpx.post(base + "/login", data={"req": req, "password": "nope"})
    assert wrong.status_code == 401
    ok = httpx.post(base + "/login", data={"req": req, "password": OAUTH_PASSWORD}, follow_redirects=False)
    assert ok.status_code == 303, ok.text
    cb = urlparse(ok.headers["location"])
    assert ok.headers["location"].startswith(redirect_uri)
    q = parse_qs(cb.query)
    assert q["state"] == ["xyz"]
    code = q["code"][0]

    # Token exchange with PKCE.
    tok = httpx.post(asm["token_endpoint"], data={
        "grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri,
        "client_id": client_id, "code_verifier": verifier, "resource": mcp_url,
    })
    assert tok.status_code == 200, tok.text
    tokens = tok.json()
    assert tokens["token_type"].lower() == "bearer" and tokens["refresh_token"]

    # The code is single-use.
    replay = httpx.post(asm["token_endpoint"], data={
        "grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri,
        "client_id": client_id, "code_verifier": verifier,
    })
    assert replay.status_code == 400

    # The access token works against the MCP endpoint, a bogus one does not.
    result = call_tool(mcp_url, tokens["access_token"], "render_svg", {"svg": SVG})
    assert any(isinstance(c, types.ImageContent) for c in result.content)
    r = httpx.post(mcp_url, json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
                   headers={"Accept": "application/json, text/event-stream", "Authorization": "Bearer nope"})
    assert r.status_code == 401

    # Refresh.
    refreshed = httpx.post(asm["token_endpoint"], data={
        "grant_type": "refresh_token", "refresh_token": tokens["refresh_token"], "client_id": client_id,
    })
    assert refreshed.status_code == 200, refreshed.text
    assert refreshed.json()["access_token"] != tokens["access_token"]
    result = call_tool(mcp_url, refreshed.json()["access_token"], "list_renders", {})
    assert not result.is_error


def test_expired_login_link(oauth_server):
    r = httpx.get(oauth_server.base_url + "/login?req=garbage")
    assert r.status_code == 400
