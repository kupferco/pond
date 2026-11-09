# Pond – Infrastructure Plan & Bill of Materials (29 Oct 2026)

Walk notes.

## Architecture

- **Two cameras:** a wrist camera on the hand for precision, plus a fixed outside camera watching the whole robot to judge success or failure and to record training demos.
- **Server in the middle (GCP):** the robot (via the Raspberry Pi) acts as a client, pulls instructions, executes them, and uploads clips, snapshots and logs.
- **Voice-driven dev loop:** a custom MCP connector added to Claude. On walks, Claude (voice) sends agreed tasks to the server, the server runs Claude Code headlessly, and the code is edited, pushed to GitHub and tested. Claude then fetches the results and images to review together.
- **Digital twin:** MuJoCo (free, open source, CPU-friendly). Start from the SO-100/101 model in Google DeepMind's MuJoCo Menagerie. Own parts are designed in CAD, exported as meshes and referenced in the XML. Offscreen rendering produces snapshots/clips without a viewer. For live 3D on the phone, use a browser viewer like MeshCat or Rerun.
- **On/off by voice:** a tiny always-on front door on Cloud Run hosts the MCP connector, with "start" and "stop" tools that boot or shut down the MuJoCo VM. Auto-shutdown after ~30 idle minutes as a safety net.
- **Security:** proper auth on the MCP server, since it can move a real robot.

## Cloud vs Mac Mini (decision: cloud first)

- Mac Mini M6 from £899 (UK). Cheaper long-term, but expensive in Brazil and could be obsolete in 2–3 years.
- Cloud VM (no GPU) is ~£20–50/month if always on, but only a few pounds/month when switched on just for walk sessions (per-second billing).
- Cons of cloud: needs the Pi as a local bridge to the real arm; slower rendering without a GPU; bills creep if left on; GPU training is rented occasionally either way.

## Phase 1 – Purely digital (~1 month)

1. Create a GitHub repo for Pond.
2. Set up a GCP account (check new-account free credits).
3. Create a small VM for MuJoCo, plus a Cloud Run front door.
4. Build the MCP connector (start/stop VM, submit task, fetch results/images) and add it to Claude as a custom connector.
5. Set up the headless Claude Code runner on the VM.
6. Load the SO-101 twin in MuJoCo, with offscreen snapshots from virtual wrist and overhead cameras.
7. Design pipe joints, cart (3 spring-loaded wheels, underside no-wheels zone, flush joints) and pod holders in CAD, then test in the sim.
8. Review progress and appetite in December, then decide on Phase 2.

## Phase 2 – Hardware (decide ~December, order before flying)

| Item | Approx. cost | Notes |
|---|---|---|
| SO-101 leader + follower pair | £250–400 | e.g. MakerMods kit $300 (~£230 + shipping/import). Could buy motor kits only and print parts. Some ship from China, so allow ~2 weeks. |
| Raspberry Pi 5 + PSU + SD card | £60–80 | Bridge between the real arm and the server |
| 2 USB cameras | small | If not included in the arm kit |
| 3D printer | £0 or ~£200 | Already own a Creality Ender 3. Optional upgrade: Bambu Lab A1 mini. Print in PETG/ASA, not PLA. (Superseded 9 Nov: plain Bambu Lab A1, bought in Brazil.) |
| Mac Mini | £899 | Deferred – not needed with the cloud-first approach |

**Rough Phase 2 total:** ~£320–470 without a new printer, ~£520–670 with the A1 mini.

## Brazil customs notes

- The duty-free allowance is US$1,000 for arrivals by air, usable once a month. Used items for strictly personal use don't count.
- Any excess is taxed under the simplified traveller's regime; undeclared items that customs rejects as personal attract a penalty on top.
- Goods must be for personal use, not commercial. Unbox and use everything before flying, and carry the receipts.
- The planned kit (Pi + arm pair + optional A1 mini) should be roughly US$430–900, so under the allowance. Check exact prices.
- The arms have no batteries (mains PSU), so they're fine in hold or hand luggage.
