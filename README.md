# pond

Pond is a small remote toolbox for Claude: render CAD and SVG so it can see its own work,
later a MuJoCo twin and a robot bridge.

```
render-server/   MCP server (Python, Streamable HTTP, Cloud Run): render_svg, render_cad, run_sim, repo_* and friends
cad/             part scripts (CadQuery), rendered through the server
sim/             MuJoCo model generators, simulated through the server (see sim/README.md)
docs/            plans and runbooks
```

- Build plan: [docs/render-server-plan.md](docs/render-server-plan.md)
- Sim server plan: [docs/sim-server-plan.md](docs/sim-server-plan.md)
- Server README: [render-server/README.md](render-server/README.md)
- Deploy to Cloud Run: [docs/deploy-cloud-run.md](docs/deploy-cloud-run.md)
