# Pond sim models

MuJoCo models of the cart and track, as Python generators the render server runs on request:
`run_sim(model="pipe_climb", params={...})`. Claude edits them with `repo_write`; the next
`run_sim` picks the new file up from the `claude/drafts` branch (then `main`), no redeploy.

## Writing a model

```python
"""One-line summary shown by list_models.

Longer description...
"""
from constants import PIPE_R, WHEEL_R   # sim/constants.py is importable
import math

PARAMS = {                               # name: (default, help) — overridable from run_sim
    "surface": ("dry", "dry or wet"),
    "payload_kg": (0.4, "extra mass carried"),
}
TRACK_BODY = "cart"                      # body whose height/speed/contacts are logged
CAMERAS = ["side", "track"]              # model cameras, plus built-ins "track" and "free"
DEFAULT_CONTROLS = {"drive": 6.28}       # ctrl per actuator when run_sim gets no controls

def build(**p) -> str:
    return f"""<mujoco> ... </mujoco>"""   # SI units: metres, kg, seconds
```

Rules inside the sandbox: only `math`, `numpy`, `json`, `xml.etree`, the stdlib data helpers
and `constants`; no files (`file=`, `<include>`, `meshdir`), so geometry is primitives for now.
Name wheel hinges `wheel_*` and add `<custom><numeric name="wheel_radius" data="0.01"/></custom>`
to get slip logged per wheel.

## What the runner logs (100 Hz, `signals.csv`)

`t`, tracked body `pos_*`/`vel_*`/`speed`, `contacts` (count) and `contact_normal_N` (sum of
normal forces on the tracked body and its children), `ctrl.<actuator>`, `force.<actuator>`,
`q.<joint>`/`qd.<joint>` for every hinge and slide, `sensor.<name>` for every `<sensor>`, and
`slip.<wheel joint>` (rim speed minus body speed). The summary has min/max/mean/final of each,
plus `climb_m` (height gained) and `max_contacts`.

## Models

- `pipe_climb.py` — test 1 of the ladder: the cart on a single vertical pipe. Params for
  surface/friction, spring preload and stiffness, masses, drive rpm and torque. Baseline
  results on 1 Nov 2026 (2 s runs): dry with 30 N preload climbs; wet (μ 0.3) slides at 30 N
  and holds at 60 N; +1 kg payload stalls the 0.3 N m drive. 15 N preload cannot hold 1 kg.

Tests 2–5 (curve, handover, corner, arm reach) come later.
