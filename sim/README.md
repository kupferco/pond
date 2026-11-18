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

`t`, tracked body `pos_*`/`vel_*`/`speed`, `roll_deg`/`pitch_deg`/`yaw_deg` (turn about world
X/Y/Z since the start; yaw on `pipe_climb` is how far the cart has rotated around the pipe,
and a full turn reads 360), `contacts` (count) and `contact_normal_N` (sum of normal forces on
the tracked body and its children), `ctrl.<actuator>`, `force.<actuator>`,
`q.<joint>`/`qd.<joint>` for every hinge and slide, `sensor.<name>` for every `<sensor>`, and
`slip.<wheel joint>` (rim speed minus body speed). The summary has min/max/mean/final of each,
plus `climb_m` (height gained) and `max_contacts`.

## Models

- `pipe_climb.py` — test 1 of the ladder: the cart on a single vertical pipe. Params for
  surface/friction, spring preload and stiffness, masses, drive rpm and torque. Baseline
  results on 1 Nov 2026 (2 s runs): dry with 30 N preload climbs; wet (μ 0.3) slides at 30 N
  and holds at 60 N; +1 kg payload stalls the 0.3 N m drive. 15 N preload cannot hold 1 kg.
  Omni cart (OpenPocket #283, `wheel="omni"`): the driven wheel is the 38 mm rubber-roller omni wheel (grip up the pipe, 2 % of it round the pipe, an explicit anisotropic contact pair),
  the idlers are ball cups, the cart is the whole 3 kg. `wet_test()` lists the wet-pipe hold cases (drive locked by the worm: `drive_rpm` 0, `drive_torque_nm` 5). Results (3 s, 3 kg, vertical
  pipe, checked in the control-ui MuJoCo build): wet (mu 0.3) slides at 20, 40, 60, 80 and 100 N preload and only just holds at 140 N (creeps 7 cm); dry (0.8) slides at 20, 30 and 40 N and holds
  at 50 N. So the design preload of 20 N (40 N in tests) cannot hold the cart on the pipe by the drive wheel alone: plan risk 1 is real, grip needs 3 to 5 times the wheel's rating or another
  hold (rubber on the pipe, a rubber-tyred wheel, then the latching brake: plan task 13). The anisotropy is right: with the two friction values swapped the same 140 N case slides.
- `unit_change.py` — the cart crossing three units. Since #283 the cart is the omni cart: hands 12 cm apart on one rigid base, three-lobe sleeves with a jaw wedge, and the cart ROLLS 90 degrees
  on the riding pipe (no hinge) to take the free hand off its pipe. The jaw wedge is drawn to 150 degrees: with the CAD's 110 no roll direction clears (control-ui `scripts/search-swing.ts`).
  `bend_test.py` and `guide_test.py` still model the old 20 x 8 wheels (they read the old constants in `constants.py`, kept for them) and are not updated yet.

Tests 2–5 (curve, handover, corner, arm reach) come later.
