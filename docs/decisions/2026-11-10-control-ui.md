# Control UI: sim in the browser, one command layer, Firebase (10 Nov 2026)

## Decided

- **One page, two halves:** a live MuJoCo view of the robot and a command panel. Start with single motor commands (motor A to 25°, Go); grow to poses, cart moves and tasks (pick D3, place B5). See `docs/notes/2026-11-10-command-language.md`.
- **Sim runs in the browser:** the official MuJoCo WebAssembly build, drawn with three.js. Nothing to install, no sim server for this. A server (Cloud Run) is only for heavy offline work such as many training runs.
- **One command layer, two drivers:** Sim (MuJoCo) and Real (Web Serial to the Waveshare Bus Servo Adapter A, Feetech protocol), behind a Sim/Real toggle. This replaces the separate "arm dev tool": the same page drives the real arm once it is built. Settles the open Web Serial question.
- **Stack:** TypeScript + Vite, static build.
- **Hosting:** a new Firebase project, `pond-grow` (pond-grow.web.app), hosting the whole Pond hub with the sim at `/sim`. Firebase can send the COOP/COEP headers that multi-threaded MuJoCo needs; GitHub Pages cannot. GitHub Pages stays on until Viber #46 reports on hub speed.
- **Deploy:** GitHub Actions with the official Firebase hosting action, a preview per pull request. Dani creates the project and deploy permissions at home (Viber #47 owner step).
- **Spike scope:** SO-101 arm only. Cart added after, with full wheel physics if the browser copes, otherwise a simple track joint for the UI.
- **Layout numbers are configurable:** dry rows (14 in v3), seedling tray grid (4 × 4 or 3 × 5), pipe slots (about 24).

## Why

Software can progress fully in sim before any part is printed or bought; expect a tuning stage on real hardware (servo slop, calibration, friction).
