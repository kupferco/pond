# Pond render server

An MCP server (Streamable HTTP) that turns CadQuery scripts and SVG into PNG images so
Claude can see and fix its own drawings. Plan: [../docs/render-server-plan.md](../docs/render-server-plan.md).
Deploying: [../docs/deploy-cloud-run.md](../docs/deploy-cloud-run.md).

## Tools

| Tool | What it does |
| --- | --- |
| `render_svg(svg, width?, title?)` | SVG markup → PNG, returned inline as an image. |
| `render_cad(script, views?, show_hidden?, title?, name?, save_to_repo?)` | Runs a CadQuery script in a sandbox, exports STEP/STL/GLB, returns one PNG per view (`front`, `back`, `top`, `bottom`, `right`/`side`, `left`, `iso`, `iso_back`) plus a summary with bounding box, volume and file links. Script errors come back as a trimmed traceback, so Claude can fix the script and retry. With GitHub configured, a successful render also commits the script to `cad/<name>.py` on the drafts branch (`save_to_repo=false` opts out). |
| `list_renders(limit?)` | Recent renders, newest first. |
| `/viewer?src=<glb url>` (HTTP page, not a tool) | One-tap 3D view of a render's GLB in the browser, linked as `viewer` in every summary when the files live in GCS. |
| `get_render(render_id, include_images?, include_script?)` | A past render's summary, links, images and script. |
| `list_models()` | The MuJoCo model generators in the repo's `sim/` folder, with their params and defaults (parsed statically). |
| `run_sim(model?, params?, mjcf_xml?, duration_s?, controls?, cameras?, record?, frames?, track_body?, title?, name?, save_to_repo?)` | Simulates a named `sim/` model (or raw MJCF) in a sandbox. Returns one snapshot sheet per camera, a summary of every logged signal (height, speed, contact force, actuator torque, wheel slip, joint travel), `signals.csv`, `model.xml` and an MP4 when `record=true`. |
| `get_sim(sim_id, include_images?)` | A past simulation's summary, links and sheets. |
| `repo_write(path, content, message, branch?)` | Commits one text file to the Pond repo. Only under `docs/`, `cad/`, `sim/`; only on `claude/*` branches (default `claude/drafts`), never `main`; max 1 MB. Present only when GitHub is configured. |
| `repo_read(path, ref?)` / `repo_list(dir?, ref?)` | Read a file or list a folder, from the drafts branch with fallback to `main`. |
| `repo_open_pr(title, body?)` | Opens (or returns the existing) PR from the drafts branch to `main` for review. |

Script conventions: millimetres, Z up, end with `result = <Workplane | Shape | Assembly>` or
call `show_object(obj)`. `cq` and `math` are pre-imported.

Exports: STEP and STL are Z-up as modelled. The GLB is Y-up as glTF requires; CadQuery's
exporter already does that with a rotation on the root node, so viewers show parts upright.
`tests/test_sandbox.py` guards this by measuring the GLB's world-space extents.

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
| `POND_GITHUB_TOKEN` | | Fine-grained GitHub token (Contents + Pull requests read/write on the one repo). Enables the `repo_*` tools and render auto-save. |
| `POND_GITHUB_REPO` | | `owner/name` of the repo the token may write to. |
| `POND_GITHUB_BRANCH` | `claude/drafts` | Branch that writes go to; must start with `claude/`. Created from `main` on first use. |
| `POND_GITHUB_WRITE_PREFIXES` | `docs,cad,sim` | Top-level folders writes are allowed in. |
| `POND_GITHUB_MAX_BYTES` | `1048576` | Size cap per file. |
| `POND_SIM_TIMEOUT_S` | `120` | Wall-clock limit for a simulation subprocess. |
| `POND_SIM_MEMORY_MB` | `3072` | Address-space limit for the sim subprocess (Linux). The software GL renderer needs about this much. |
| `POND_SIM_MAX_DURATION_S` | `30` | Cap on simulated seconds per run. |
| `POND_SIM_DIR` | `<repo>/sim` if present | Local folder of model generators, used when GitHub is not configured. |
| `MUJOCO_GL` | | Set to `osmesa` in the Docker image for headless rendering; unset on a Mac. |

## Simulations

`run_sim` runs `pond_render/sandbox/sim_runner.py` in the same kind of subprocess as the CAD
runner. A model is a generator script from the repo's `sim/` folder (read from GitHub, drafts
branch first, or from a local checkout) that builds MJCF from params; it runs under the import
guard with `sim/constants.py` importable. The MJCF may not reference files. The runner logs
signals at 100 Hz, renders snapshot sheets with MuJoCo's offscreen renderer (OSMesa in Docker)
and writes an MP4 with imageio-ffmpeg. See `sim/README.md` for the model contract.

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

## GitHub writes

With `POND_GITHUB_TOKEN` and `POND_GITHUB_REPO` set, Claude can save files into the repo.
`pond_render/github.py` enforces the rules in code: writes go only to branches starting
with `claude/` (`main` is refused before any request is made), only under the allowed
folders, only as UTF-8 text under the size cap, and paths are normalised with `..` and
hidden files refused. Every commit is logged with path, branch, sha and URL. Reads fall
back from the drafts branch to `main`. Merging to `main` is always a human action.

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
  github.py        GitHub client with the write policy (claude/* branches, docs/cad/sim only)
  sim_models.py    where sim generators come from (GitHub or local sim/), static param listing
  sandbox/sim_runner.py  MuJoCo child process: build MJCF, simulate, log, render
tests/             pytest: svg, sandbox, MCP end-to-end, OAuth flow
Dockerfile
```
