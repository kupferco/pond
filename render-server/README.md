# Pond render server

An MCP server (Streamable HTTP) that turns CadQuery scripts and SVG into PNG images so
Claude can see and fix its own drawings. Plan: [../docs/render-server-plan.md](../docs/render-server-plan.md).
Deploying: [../docs/deploy-cloud-run.md](../docs/deploy-cloud-run.md).

## Tools

| Tool | What it does |
| --- | --- |
| `render_svg(svg, width?, title?)` | SVG markup → PNG, returned inline as an image. |
| `render_cad(script, views?, show_hidden?, title?)` | Runs a CadQuery script in a sandbox, exports STEP/STL/GLB, returns one PNG per view (`front`, `back`, `top`, `bottom`, `right`/`side`, `left`, `iso`, `iso_back`) plus a summary with bounding box, volume and file links. Script errors come back as a trimmed traceback, so Claude can fix the script and retry. |
| `list_renders(limit?)` | Recent renders, newest first. |
| `get_render(render_id, include_images?, include_script?)` | A past render's summary, links, images and script. |

Script conventions: millimetres, Z up, end with `result = <Workplane | Shape | Assembly>` or
call `show_object(obj)`. `cq` and `math` are pre-imported.

## Local development

```bash
cd render-server
/usr/local/bin/python3.12 -m venv .venv            # 3.11 or 3.12 (cadquery-ocp wheels)
.venv/bin/pip install -r requirements.txt -e ".[dev]"
brew install cairo                                 # macOS only; Linux: apt install libcairo2

cp .env.example .env && $EDITOR .env               # token mode is fine locally
set -a; source .env; set +a
.venv/bin/python -m pond_render                    # http://localhost:8080/mcp
```

Tests spin up the real server on a free port and talk to it over Streamable HTTP, including
the OAuth flow:

```bash
.venv/bin/python -m pytest -q
```

First import of CadQuery on macOS can take a minute or two while the OS checks the
OpenCascade dylibs; after that it is about two seconds per render subprocess.

## Configuration (environment)

| Variable | Default | Meaning |
| --- | --- | --- |
| `POND_PUBLIC_URL` | `http://localhost:8080` | Public base URL; OAuth issuer and resource URL derive from it. |
| `POND_HOST` / `PORT` | `127.0.0.1` / `8080` | Bind address. Cloud Run sets `PORT`. |
| `POND_STORAGE` | `local:./renders` | `local:<dir>` or `gs://<bucket>[/<prefix>]`. |
| `POND_AUTH_MODE` | `token` | `token` (static bearer), `oauth` (built-in OAuth server for Claude.ai), `none` (localhost only). |
| `POND_API_TOKEN` | | Bearer token for `token` mode. |
| `POND_OAUTH_PASSWORD` | | Password typed in the browser when a client connects (`oauth` mode). |
| `POND_OAUTH_SIGNING_SECRET` | | HS256 secret for tokens (`oauth` mode); rotate to revoke everything. |
| `POND_CAD_TIMEOUT_S` | `60` | Wall-clock limit for a CAD script. |
| `POND_CAD_MEMORY_MB` | `3072` | Address-space limit for the CAD subprocess (enforced on Linux). |
| `POND_IMAGE_WIDTH` | `800` | Width of rendered views. |
| `POND_STATELESS` | `true` | Stateless Streamable HTTP (right for Cloud Run). |

## How the sandbox works

Every `render_cad` call spawns `python -I pond_render/sandbox/runner.py` with:

- a scrubbed environment (no inherited variables, so no credentials), `HOME`/`TMPDIR`/cwd
  set to a fresh temp directory that is deleted afterwards;
- rlimits: CPU time, address space (Linux), file size, no core dumps; the whole process
  group is killed at the wall-clock timeout;
- inside the interpreter, an import allow-list (cadquery, math, numpy and a few stdlib
  helpers) and no `open`/`exec`/`eval`/`compile`/`input`.

The in-process checks catch mistakes and casual misuse; the process boundary plus Cloud
Run's gVisor sandbox and a least-privilege service account are the real security line.
The MCP endpoint is never exposed without auth (the config refuses `none` off localhost).

## Auth modes

- **token**: send `Authorization: Bearer <POND_API_TOKEN>`. Use for local tests, scripts,
  or the Claude API's MCP connector.
- **oauth**: a built-in OAuth 2.1 authorization server (dynamic client registration, PKCE,
  refresh tokens) that Claude.ai custom connectors can use directly. Clients are stored
  under `auth/clients/` in the store; tokens are stateless signed JWTs, so nothing has to
  survive a Cloud Run cold start. Authorization shows a one-field password page.

## Layout

```
pond_render/
  server.py        MCP tools + HTTP routes, build_app()
  auth.py          static token verifier, built-in OAuth provider + login page
  sandbox/host.py  spawns the runner subprocess, timeouts, result collection
  sandbox/runner.py the sandboxed child: limits, import guard, CadQuery exports, HLR views
  svg_render.py    SVG → PNG via cairosvg (data: URLs only)
  storage.py       LocalStore / GCSStore
  renders.py       render records (renders/<id>/meta.json)
  config.py        POND_* settings
tests/             pytest: svg, sandbox, MCP end-to-end, OAuth flow
Dockerfile
```
