# Pond – MuJoCo sim server build plan v2

Phase 1, step 2. Written 1 Nov 2026, to hand to Claude Code. Replaces v1 (adds GitHub tools and a fuller prompt).

## Before you start

Copy this doc into the repo as `docs/sim-server-plan.md`, so Claude Code can read it.

## Step A: GitHub tools (do this first)

Goal: Claude (including in voice) can save files to the Pond repo directly, so GitHub becomes the main store, not just Drive.

- Create a fine-grained GitHub token with access to the pond repo only, with Contents read/write. Store it in Secret Manager, never in code.
- New MCP tools:
  - `repo_write(path, content, message)`: commits one file to a branch (default `claude/drafts`, never `main`).
  - `repo_read(path)` / `repo_list(dir)`: read files and folders.
  - Optional: `repo_open_pr(title, body)`: opens a PR from `claude/drafts` to `main` for Dani to review.
- Safety:
  - Allow writes only under `/docs`, `/cad`, `/sim`.
  - Cap file size (e.g. 1 MB).
  - Log every commit.
  - Never push to `main`; Dani merges.
- Auto-save renders: every successful `render_cad` / `run_sim` also commits its script to `/cad/<name>.py` or `/sim/<name>.py` (opt-out flag), so the CAD history lives in Git.

## Step B: Quick fixes (render server)

- GLB orientation: CadQuery is Z-up and glTF is Y-up, so rotate −90° about X on GLB export, so models stand upright in viewers.
  - *Checked 1 Nov 2026: CadQuery's exporter already does this (a −90° X rotation on the glTF root node); the live GLBs measure Y-up. No change needed; regression tests added instead.*
- Optional: a simple hosted viewer page (e.g. `<model-viewer>`), so one tap opens the model.

## Step C: MuJoCo sim tool

- `mujoco` Python package with headless OSMesa rendering (no GPU on Cloud Run); imageio/ffmpeg for clips.
- Raise the Cloud Run timeout/memory for sims, or run them on the MuJoCo VM later.
- New tools:
  - `run_sim(mjcf_xml, duration_s, controls, cameras, record)`: returns snapshots, an optional clip, and logged signals (cart height, wheel slip, contact forces, joint torques).
  - `get_sim(id)`, `list_models()`.
- Same sandboxing as `render_cad`: subprocess, timeout, memory limit, no network or secrets.

### Model approach

- Collision = simple primitives (capsules for the pipes, cylinders for the wheels, boxes for the hands). Visuals = STL meshes from the CadQuery parts.
- Curved loop: a chain of short capsule segments.
- Cart:
  - Rocking wheel pairs: hinge joints.
  - Driven wheels: velocity actuators.
  - Spring idlers: slide joints with stiffness.
  - Jaw: hinge + position actuator.
  - Swivels: hinge + position actuator.
- Arm: start from the SO-ARM100 in MuJoCo Menagerie (check it exists). Stretch the links to ~200 mm each, with 12V STS3215 limits (30 kg·cm stall).
- Models live in `/sim`, parameterised in Python, sharing constants with the CAD.

### Test ladder (one at a time)

1. Climb: the cart on a single vertical pipe. Does it hold and climb? Measure slip versus spring force and friction, with dry and wet values.
2. Curve: a 150 mm bend. Do the rocking pairs stay in contact without binding?
3. Handover: two pipes 140 mm apart. Clamp, then release, in the right order; check the cart never drops.
4. Corner: the unit-3 pivot at pipe E, riding sideways up E, then swivelling on the top bar.
5. Arm reach: the 40 cm arm reaching each pod; check the torque margin holding 400 g.

## Prompt for Claude Code

"Read docs/sim-server-plan.md. This extends the existing Pond render server (Python MCP on Cloud Run).

Work in this order, and stop after each step for me to check:

- Step A: add the GitHub tools (repo_write / repo_read / repo_list, optional repo_open_pr), using a fine-grained token from Secret Manager, writing only to the claude/drafts branch and only under /docs, /cad and /sim. Add auto-save of render scripts.
- Step B: fix GLB export to Y-up.
- Step C: add run_sim with MuJoCo + OSMesa, returning PNG snapshots, an optional MP4 and logged signals. Build test 1 only (cart climbing a single vertical pipe) as a parameterised MJCF generator in /sim.

Before changing any code, write a short plan and wait for my OK. Test everything locally before deploying. Don't move on to tests 2–5."
