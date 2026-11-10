# Pond control UI (spike)

Page at /sim in the Pond hub (hub header, light theme). Web page: MuJoCo (official WASM build) + three.js on the left, command panel on the right.
Commands go through `src/commands.ts` (`CommandLayer`) to a driver: `SimDriver` (working) or
`RealDriver` (stub; Web Serial + Feetech STS later). Add cart / pick-pod commands on the same layer.

```
npm ci
npm run dev      # http://localhost:5173
npm run build    # typecheck + static build into dist/
npm test         # headless sim + command layer check (node)
```

Model: `src/model.ts` (SO-101, six STS3215, primitives, limits, 2.9 N·m stall).

## Hosting: owner steps ("Fix on the computer")

See `docs/notes/2026-11-10-control-ui-spike.md`, section "Fix on the computer".
