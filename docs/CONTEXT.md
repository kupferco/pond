# Pond: start here

Read this file first in every new session. It holds the big picture only. For anything that changes often, follow the links; never copy it here.

## What Pond is

An open-source, autonomous communal urban farming unit, aimed first at São Paulo (MVP "Pond 2027"). A hydroponic growing tower with a pipe-climbing robot cart and a small arm (SO-101 follower, STS3215 servos). The robot's main job is constant monitoring (catching pump failures, sick plants) plus planting pods and clearing failed plants, not heavy labour. Solar powered, flat-packs into its own tank. Target market: schools, councils, green-economy grants, and households; designs open-source for self-builders.

## Current phase

Phase 1 moving into the first hardware: the arm is being built in the UK (two months before Dani goes to Brazil), while the cart and unit stay in digital design and simulation (CAD with CadQuery, MuJoCo sims). Software (the control UI) now runs ahead in sim, independent of hardware. V1 should be simple: build it, run it, let real problems surface.

## Where things live (sources of truth)

- **Now / next / later:** `docs/roadmap/roadmap.json`
- **What's been done, by date:** `docs/history/history.json`
- **Decisions (why things are the way they are):** `docs/decisions/` (index in `docs.json`)
- **Working notes:** `docs/notes/`
- **Drawings:** `docs/gallery/` (built from `renders.json`)
- **Shopping list and costs:** `docs/shopping/shopping.json`
- **Live site:** https://kupferco.github.io/pond/ (moving to Firebase project `pond-grow`, pond-grow.web.app, once set up)
- Google Drive ("Pond 2027") is an archive only.

## Key design facts (stable)

- Unit v3: 30 cm tank (15 cm water, 15 cm store), track top at 1.9 m, reachable by a 1.6 m person.
- Spine: hidden 33.7 mm stainless tube; water runs in a separate tube inside it; spigot joints with anti-twist key and shock cord.
- Cart: six wheels per hand in rigid pairs, passes 150 mm loop corners in sim.
- Power: one 30 W panel, battery in base and on cart, charging dock on the track's bottom run.
- Arm V1: follower arm only, six 12 V STS3215 servos on one Waveshare board, driven over USB from a laptop (later a Raspberry Pi on the cart battery). Scripted poses, no camera and no leader arm for now.
- Control UI: one web page, live MuJoCo (WebAssembly) on one side, commands on the other, Sim/Real toggle over one command layer; Real uses Web Serial. Page at /sim in the hub. See `docs/decisions/2026-11-10-control-ui.md` and `docs/notes/2026-11-10-command-language.md`.
- Naming: dry store rows D1…, seedling tray cells A1…, pipe slots P1…; counts are configurable.
- Sourcing: small valuable electronics bought in the UK (cabin bag); bulky generic parts bought in Brazil.
- Prefer eco-friendly, low-plastic materials when cost is similar. Target about $100 material cost per unit in production.

## Open questions

- Servos: Amazon UK came in over £135 (£32.22 each; a £23 ST3215 listing is about £138 for six, voltage unconfirmed). ArmDojo about £126 with VAT before the board. Final check with Claude in Chrome on the desktop, then order. ArmDojo delivery time to check.
- Is there enough filament? Dani to weigh the current spool.
- Is there a 12 V, 5 A supply at home?
- Firebase: Dani to create project `pond-grow` and deploy permissions (Viber #47 owner step).
- Hub speed: wait for Viber #46 before moving the whole hub off GitHub Pages.
- Seedling tray grid: 4 × 4 or 3 × 5. Pipe slot count and order.
- Dimensioned isometric drawing of unit v3 not done yet.

## How we work

- Dani often works by voice, on walks and on the bike: short turns, don't guess ahead, let him finish. English, not Portuguese.
- Don't drop new topics in passing; raise them one at a time.
- Dani checks numbers against his own mental model; show the working.
- Claude writes only to the `claude/drafts` branch under `docs/`, `cad/` and `sim/`; Dani merges to `main` when home (not from the phone). Website and code jobs go through Viber; CAD drawings can go through Viber too when Dani can't stay on the call.
- CAD renders are shared as viewer links.

## End-of-session rule

Before wrapping up: update `roadmap.json` and `history.json`, add a decision doc if something was decided, and update the open questions above. Edit the rest of this file only when the big picture changes.
