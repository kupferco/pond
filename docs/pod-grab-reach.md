# Pod grab reach: does the 10 mm tray move work? (OpenPocket #522)

Sim model: `sim/pod_grab.py` (MuJoCo, run it as `run_sim(model="pod_grab", duration_s=40, record=True)`).
Check script and tables: `sim/pod_grab_check.py` (writes `docs/pod-grab-reach/results.json`, `--clip <name>` writes the clips).
Pictures: `cad/renders/pod-grab-reach-{iso,front,top,side}.png`, 3D model `cad/renders/pod-grab-reach.glb`.
No CAD file was changed.

## The answer, in plain words

1. **The rough check used the wrong arm.** The real SO-101 has 116 mm (upper arm), 135 mm (forearm) and about **160 mm** from the wrist
   joint to the grip point, not 120/130/100. The extra 60 mm makes the wrist sit 160 mm above the pod with the claw straight down.
   Every number in the rough check changes (see "Which dimensions are right").
2. **With the claw exactly straight down, the 10 mm move helps but does not fix the layout.** Row B and D become reachable (6 and 8 mm of
   slack) but only with the wrist at 94 degrees of its 95 degree limit, and **row C is not reachable at all** straight down, today or moved.
   The limit that bites is the wrist flex (95 degrees), not only the 250 mm reach.
3. **A claw tilt of 5 to 10 degrees fixes every row, with or without the move.** At 10 degrees every row and the store pick are reached with
   at least 10 degrees of margin on every joint, and row D has 25 mm of slack today and 35 mm with the tray moved 10 mm.
4. **Servo torque is fine.** Holding a pod with a 400 g lettuce needs at most 1.3 N m (shoulder) against the 1.9 N m stall of the STS3215 at
   7.4 V (67 %). Nothing hits the cart plate, battery, track pipe or water station in the working poses.
5. **One thing in the CAD kills it:** the real cart puts the arm base on the 50 mm battery (`cad/cart_dims.py`, `ARM_Y0`). That moves the shoulder
   50 mm further from the tray. Then straight down reaches nothing, and even at 10 degrees of tilt row D is out of reach (25 mm short today,
   15 mm short moved). Keep the arm base on the plate (battery beside or above it, as in the brief), or the 10 mm move is not enough.

**Recommendation:** move the tray 10 mm as proposed (cheap, adds 10 mm of slack on row D) **and** plan the pick with the claw tilted about
10 degrees. Do not rely on "straight down". Keep the arm base straight on the plate. A larger tray move (20 to 40 mm) does not help row C
straight down and is not needed once the claw may tilt.

## Which dimensions are right (task step 1)

From the official SO-101 URDF (TheRobotStudio/SO-ARM100, `Simulation/SO101/so101_new_calib.urdf`), in the plane of the arm:

| Part | Value | Source line |
|---|---|---|
| Pan axis above the base mounting face | 62.4 mm | `shoulder_pan` origin z |
| Shoulder lift axis | 116.6 mm above the face, 30.4 mm beside the pan axis, 18.3 mm sideways | `shoulder_lift` origin |
| Upper arm (shoulder to elbow) | **116 mm** (28.0 across, 112.6 along; leaning 14 degrees) | `elbow_flex` origin (-0.11257, -0.028) |
| Forearm (elbow to wrist flex) | **135 mm** (2.2 degrees off the straight) | `wrist_flex` origin (-0.1349, 0.0052) |
| Wrist flex axis to the grip point | **159.5 mm** (61 mm to the roll axis, then 98 mm to the jaw tip frame) | `wrist_roll` and `gripper_frame_joint` origins |
| Joint limits | pan +-110, shoulder lift +-100, elbow +-96.8, wrist flex +-95, wrist roll -157..163 degrees | `<limit>` lines |
| Masses | base 147, shoulder 100, upper arm 103, forearm 104, wrist 79, gripper 87 + jaw 12 g | `<mass>` |

So **`arm_pod_pull.py`'s 116/135 are right** (the 120/130 of the older CAD notes and the rough check are rounded) and **100 mm is wrong**:
the wrist-to-grip-point distance is 160 mm. The one set above is used everywhere in `pod_grab.py`. `arm_pod_pull.py` and `cad/cart_arm.py` still carry the old
100 mm and were not touched (task rule: only add the sim and this doc). The grip point is the URDF `gripper_frame_link` (between the jaw tips); the zero pose of the
URDF (upper arm along the base axis, forearm and gripper along +x) is the model's zero. STS3215: stall 1.9 N m at 7.4 V (the model's default), about 2.9 N m at 12 V.

The rough numbers do reproduce with the old dimensions: row A/B/C/D 199/210/226/248 mm moved (254 today for D, 4 mm over the 250 limit) matches the brief.

## Layout used (sim/unit frame, mm)

As in the brief: one track pipe at y -60, z 579, r 16; plate front face y -116, centre z 519; pan axis on the plate centre; tray rows at y -155, -117, -79, -41
(today) or -165, -127, -89, -51 (moved), pod top z 224; store pick at y -147, z 225; water station 200 x 100 x 113 on four legs at x 60..260.
The arm is mounted with its base axis out of the plate and its pan zero pointing down, so at pan 0 it works in the vertical plane through the cart.

Where the sources differ from the brief:
- **Shoulder out of the plate:** the real shoulder-lift axis is 116.6 mm from the mounting face, not ~88 (CAD `SHOULDER_H = 88` in `cad/cart_arm.py`). With the base on the plate it sits at y -232.6, not -204.
- **Battery:** the CAD (`cad/cart_dims.py`) has the battery 70 x 50 x 70 between plate and arm base; the brief has the base straight on the plate. Both are run (`battery="beside"` is the brief, `"under_arm"` the CAD). In the brief case the battery's position beside the arm is assumed (x +78).
- **Water station:** the CAD (`cad/water_station.py`, `OFF_Y = 50`) puts the box at y 14..114, z 395..508 (330..443 plus the 64 mm track rise), i.e. 160 mm behind the store pick, not over it. That is the default. The brief says "under the water station": that reading (box at y -197..-97) is the `station_y0_mm=-197` variant, and the box then sits in the cart and arm (shoulder housing 27 mm and forearm 10 mm inside it): it cannot be built like that.
- **Tray column, store x, tray size, pod size:** the brief gives only y and z. The cart stops at x -209 (tray, 38 mm pitch, pods 25 mm) and x 160 (store, 28 mm pod pitch); not from the CAD.
- **Not modelled:** the tank lid with its pick holes (the claw and forearm must pass through them: the grip point is about 144 mm under the lid top at 368), the spine and the cart's two sleeves beyond a plain ring. The claw is an envelope (a 75 x 44 x 32 mm body and a 35 x 24 x 20 mm tip), not the real jaw.

## Result per row (battery beside, as in the brief)

"Slack" = how far the target could move along Y before it leaves the reachable band (the smaller of the two sides); negative = how far it must move to become reachable.
"Wrist" = wrist flex angle needed (limit 95). "Torque" = worst joint holding the pod and 400 g lettuce (stall 1.9 N m). Collision column: arm against plate, battery, pipe, station, tray and the neighbouring pods.

### Claw straight down

| Target | Today (tray as is) | Moved 10 mm |
|---|---|---|
| Row A | reachable, slack 34 mm, wrist 88.3 degrees | reachable, slack 44 mm, wrist 85.3 |
| Row B | **no**, 4 mm short, wrist at the 95 limit | reachable, slack 6 mm, **wrist 94.2 (0.8 degrees from the limit)** |
| Row C | **no**, wrist at the 95 limit (needs 2 degrees of tilt) | **no**, same (needs 2 degrees of tilt) |
| Row D | **no**, 2 mm short, shoulder at its 100 limit | reachable, slack 8 mm, wrist 93.9, shoulder 95.6 (1 degree from limits) |
| Store pick | reachable, slack 22 mm, wrist 90.8 | same (the store does not move) |
| Torque | 0.9 to 1.3 N m (D worst) | 0.9 to 1.2 N m |
| Collisions | none (closest: 5 to 13 mm to a neighbouring pod) | none (closest 7 to 8 mm) |

### Claw tilted 5 and 10 degrees (tilted so the wrist is further out; the tip leans towards the plate)

| Target | Today, 5 deg | Moved, 5 deg | Today, 10 deg | Moved, 10 deg |
|---|---|---|---|---|
| Row A | yes, slack 126 | yes, 136 | yes, 139, joints 27 deg from a limit | yes, 149, 32 deg |
| Row B | yes, 88 | yes, 98 | yes, 101, 16 deg | yes, 111, 18 deg |
| Row C | yes, 50 (3.8 deg to a limit) | yes, 60 (4.1 deg) | yes, 63, 10 deg | yes, 73, 11 deg |
| Row D | yes, 12 (6 deg) | yes, 22 (5 deg) | yes, 25, 11 deg | yes, 35, 10 deg |
| Store pick | yes, 118 | yes, 118 | yes, 131, 24 deg | yes, 131, 24 deg |
| Torque (worst row) | 1.25 | 1.17 | 1.21 | 1.13 |

The first column to read is the 10 degree one: nothing is within 10 degrees of a joint limit and every row has at least 25 mm of slack.
Torque numbers are static holding torque with the pod in the claw (no acceleration); the unloaded arm needs 0.3 to 0.5 N m.

### Collisions and clearance (working poses, moved tray)

Smallest gap from any arm part to: cart plate 44 to 54 mm, battery 19 mm, track pipe 111 mm, tray base 16 to 19 mm, store shelf 23 to 26 mm, water station box 144 mm
(at the store) or more (CAD position). No contact in any pose (with the 10 degree tilt and straight down). The arm never goes near the pipe.
The only things the claw gets close to are the neighbouring pods (3 to 8 mm in the envelope model): the real jaw width will decide that, see the open questions.

### The CAD variant: arm base on the 50 mm battery (`battery="under_arm"`)

| | Straight down | 10 degrees |
|---|---|---|
| Today | no row reachable (A 16 mm short, B 8 mm, C 14 mm, D 52 mm, store 28 mm) | A, B, C, store yes (C has only 13 mm slack); **D no, 25 mm short** |
| Moved 10 mm | no row reachable (A 6 short, B 18, C 4, D 42, store 28) | A, B, C, store yes; **D no, 15 mm short** (needs about 18 degrees of tilt) |

## Played in the sim (the tour clips)

`sim/pod_grab.py` drives the arm through rows A, B, C, D (50 mm hover, down to grip height, hold, up), slides the cart to the store and picks there. The servos are
position servos limited to 1.9 N m with the 0.42 kg load on the claw, so what you see is what the real servo torque allows. Clips (2 x 2: front, side, iso, top):

- `docs/pod-grab-reach/pod-grab-proposal-straight-down.mp4`: the proposal as drawn (tray moved 10 mm, claw straight down).
- `docs/pod-grab-reach/pod-grab-proposal-tilt-10.mp4`: tray moved 10 mm, claw tilted 10 degrees.
- `docs/pod-grab-reach/pod-grab-today-tilt-10.mp4`: tray as it is today, claw tilted 10 degrees.

What the three runs measured (grip point against each target, whole 37 s tour, no clipping):

| Run | Closest grip point to A / B / C / D / store | Arm touching plate, pipe, battery, tray, shelf or station |
|---|---|---|
| proposal, straight down | 1.6 / 2.1 / 2.8 / 2.6 / 1.8 mm | none |
| proposal, 10 degrees | 1.8 / 2.1 / 2.3 / 2.9 / 1.8 mm | none |
| today, 10 degrees | 1.8 / 0.5 / 2.3 / 2.9 / 1.8 mm | none |

The 1 to 3 mm is servo droop under the load. In the straight-down clip row C is only reached because the pose is allowed to be 1.4 degrees off vertical (wrist at its stop): strictly straight down it is out of reach, as in the table.

Peak torque reaches the 1.9 N m limit only while the arm accelerates between poses (a few percent of the time); the holding poses stay at 0.9 to 1.3 N m.
**Sim id:** this session cannot call the hosted `run_sim`, so there is no hosted sim id. The model is a normal `sim/` generator (`run_sim(model="pod_grab", ...)` runs it once it is on `main` or the draft branch)
and the three clips above were recorded here with the same generator and controls.

## Open questions for the owner

1. **Can the pick use a tilted claw?** The recommendation depends on it. Straight down is only possible on rows A and S (and B, D with 1 degree of wrist margin).
2. **The arm base on the battery** (CAD, 50 mm out) makes row D unreachable even at 10 degrees. Is the battery moving beside or above the arm base?
3. **The tank lid:** at the pick the claw is about 144 mm below the lid top. The pick holes in the lid must let a tilted claw and the forearm through.
4. **Jaw width.** Neighbouring pods are 13 mm (tray rows 38 mm apart, pods 25 mm) from the claw envelope; the real SO-101 jaw has to straddle the pod across the row direction.
5. The tray column and store positions along X are assumed (the cart stops at x -209 and 160).

## Re-running

```
pip install mujoco numpy imageio imageio-ffmpeg trimesh scipy
python3 sim/pod_grab_check.py                       # tables, docs/pod-grab-reach/results.json
MUJOCO_GL=egl python3 sim/pod_grab_check.py --clip proposal-tilt-10
MUJOCO_GL=egl python3 sim/pod_grab_render.py 10 10 D    # PNGs and GLB in cad/renders
```
Params of the model: `tray_shift_mm` (0 or 10), `tilt_deg`, `battery` (beside or under_arm), `station_y0_mm`, `stall_nm` (1.9 or 2.9), `load_kg`, `kp`, `pod_contact`.
