# Pond – Render server build plan

Phase 1, step 1. Written 31 Oct 2026, to hand to Claude Code.

## Goal

A remote MCP server that Claude (including voice mode) can call to turn CAD code or SVG into images, so Claude can see and fix its own drawings. It's the first piece of the bigger Pond server (task queue, MuJoCo twin and robot come later).

## Stack decisions

- Python, not Node. CadQuery is Python, so one runtime keeps it simple.
- MCP: the official MCP Python SDK, over the Streamable HTTP transport (needed for a Claude custom connector).
- Hosting: GCP Cloud Run (scales to zero, so it costs almost nothing when idle). Later, the MuJoCo VM sits behind the same front door.
- Storage: a GCS bucket for outputs (or a Drive folder: Pond/Renders).

## Steps

1. Create a GitHub repo, `pond`, with a monorepo layout: `/render-server`, `/cad` (part scripts), `/docs`.
2. Create a GCP project, `pond`. Enable Cloud Run, Artifact Registry, Cloud Storage and Secret Manager. Check new-account free credits.
3. Local dev environment: Python 3.11+, cadquery, cairosvg (SVG to PNG), mcp SDK, uvicorn. Note that CadQuery is easiest via conda/mamba, or the cadquery-ocp wheels.
4. Implement the MCP tools:
   - `render_svg(svg_code)`: returns a PNG.
   - `render_cad(cadquery_script, views=[front, top, side, iso])`: runs the script, exports STEP + STL (+ GLB), renders PNG views, uploads everything, and returns the images inline plus file links.
   - `list_renders()` / `get_render(id)`: fetch past outputs.
   - Return images as MCP image content, so Claude sees them directly.
5. Sandbox the CAD runner (it executes arbitrary Python):
   - Run it in a subprocess with a timeout (~60 s) and memory limits.
   - Keep no secrets or credentials in the runner's environment.
   - Allow only the needed imports (cadquery, math), with no network or file access outside a temp directory.
6. Auth: protect the connector (OAuth, which Claude custom connectors support). Never leave it open, since it runs code.
7. Write a Dockerfile, deploy to Cloud Run, and get the HTTPS URL.
8. In Claude, go to Settings → Connectors → add a custom connector with that URL.
9. Test loop: ask Claude in voice to render a simple test part (e.g. a 32 mm pipe with a C-clamp sleeve). Claude checks the PNGs, fixes them, and re-renders.
10. Commit the first real part script to `/cad` (e.g. `hand_sleeve.py`).

## Later (not tonight)

- `start_twin` / `stop_twin` tools to boot or stop the MuJoCo VM, with idle auto-shutdown.
- `submit_task` / `get_result`: the headless Claude Code runner.
- Robot bridge via the Raspberry Pi (Phase 2).

## Prompt for Claude Code

"Read docs/render-server-plan.md. Build the render-server as a Python MCP server (Streamable HTTP) with the tools listed, a sandboxed CadQuery runner, a Dockerfile and Cloud Run deploy instructions. Start with render_svg and render_cad, and test locally first."
