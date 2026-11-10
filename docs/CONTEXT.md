# Pond: start here

Read this file first in every new session. It holds the big picture only. For anything that changes often, follow the links; never copy it here.

## What Pond is

An open-source, autonomous communal urban farming unit, aimed first at São Paulo (MVP "Pond 2027"). A hydroponic growing tower with a pipe-climbing robot cart and a small arm (SO-101 style, STS3215 servos). The robot's main job is constant monitoring (catching pump failures, sick plants) plus planting pods and clearing failed plants, not heavy labour. Solar powered, flat-packs into its own tank. Target market: schools, councils, green-economy grants, and households; designs open-source for self-builders.

## Current phase

Phase 1: digital design and simulation (CAD with CadQuery, MuJoCo sims) before buying and building hardware. V1 should be simple: build it, run it, let real problems surface.

## Where things live (sources of truth)

- **Now / next / later:** `docs/roadmap/roadmap.json`
- **What's been done, by date:** `docs/history/history.json`
- **Decisions (why things are the way they are):** `docs/decisions/` (index in `docs.json`)
- **Working notes:** `docs/notes/`
- **Drawings:** `docs/gallery/` (built from `renders.json`)
- **Shopping list and costs:** `docs/shopping/`
- **Live site:** https://kupferco.github.io/pond/
- Google Drive ("Pond 2027") is an archive only.

## Key design facts (stable)

- Unit v3: 30 cm tank (15 cm water, 15 cm store), track top at 1.9 m, reachable by a 1.6 m person.
- Spine: hidden 33.7 mm stainless tube; water runs in a separate tube inside it; spigot joints with anti-twist key and shock cord.
- Cart: six wheels per hand in rigid pairs, passes 150 mm loop corners in sim.
- Power: one 30 W panel, battery in base and on cart, charging dock on the track's bottom run.
- Sourcing: small valuable electronics bought in the UK (cabin bag); bulky generic parts bought in Brazil.
- Prefer eco-friendly, low-plastic materials when cost is similar. Target about $100 material cost per unit in production.

## Open questions

- SO-101 ready-made kit versus parts plus printing (check kit prices).
- Shop links on the shopping list still empty.
- Dimensioned isometric drawing of unit v3 not done yet.

## How we work

- Dani often works by voice: short turns, don't guess ahead, let him finish. English, not Portuguese.
- Dani checks numbers against his own mental model; show the working.
- Claude writes only to the `claude/drafts` branch under `docs/`, `cad/` and `sim/`; Dani reviews and merges to `main`.
- CAD renders are shared as viewer links.

## End-of-session rule

Before wrapping up: update `roadmap.json` and `history.json`, add a decision doc if something was decided, and update the open questions above. Edit the rest of this file only when the big picture changes.
