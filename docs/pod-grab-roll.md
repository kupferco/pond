# Pod grab, 26 Nov layout: is the 45 degree roll needed? (OpenPocket #522 follow-up)

Sim model: `sim/pod_grab.py` with `layout="roll"` (MuJoCo, real SO-101, STS3215 torque limits). Tables: `sim/pod_grab_roll_check.py` -> `docs/pod-grab-reach/results-roll.json`.
Real cart depth under the pipe: `sim/pod_grab_roll_cad_depth.py` -> `docs/pod-grab-reach/cad-depth-roll.json`. Pictures: `cad/renders/pod-grab-roll-{rolled,upright}-{iso,front,top,side}.png`,
3D models `cad/renders/pod-grab-roll-{rolled,upright}.glb`. Clips: `docs/pod-grab-reach/pod-grab-roll-tour-tray.mp4` (upright A1 and D4, then rolled 45 degrees A1, D1, D4) and
`docs/pod-grab-reach/pod-grab-roll-tour-store.mp4` (upright, S1 and S5). No CAD file was changed. The first round is in `docs/pod-grab-reach.md`.

## The answer, in plain words

**The 45 degree roll is not needed, and it makes the reach worse. Keep the cart upright.**

1. **Rolled 45 degrees (case a): no tray cell can be picked with the claw vertical.** The least claw tilt is 15 degrees (D1) and 44 degrees at worst (C1, C2). Rolling drops the shoulder axis from 265 mm to 169 mm above the pod level and moves it from 233 mm in front of the tray to directly over row B (y -118): the rows nearest the arm (A to C, columns 1 and 2) need the shoulder lift at its -100 degree stop (0.1 to 1.1 degrees from the limit) and the claw
   still ends 38 to 44 degrees off vertical. The arm cannot fold small enough. Only 4 of 16 cells are within 22 degrees. Roll angles from 10 to 60 degrees were swept (table below): 0 is the best or equal best for every corner cell.
2. **Upright (case b): the whole tray is reachable, but only column 1 (nearest the parked cart) with a vertical claw.** The cart parks at x -130, the tray columns are at -133, -171, -209, -247: the arm has to pan sideways, and
   with the cart upright the pan axis is horizontal (it swings the arm like a clock hand in the plane of the plate), so **the claw tilts sideways by about the pan angle**: 2 degrees in column 1, 8 in column 2,
   15 in column 3, **22 degrees in column 4**. All 16 cells are reachable within 22 degrees, 8 within 10 degrees. The far-left corner D4 is reachable at 22 degrees of tilt (pan -22 degrees, shoulder lift 1.3 degrees from its stop).
3. **Store front row, upright (case c): same story.** S1 vertical (59 mm slack), S2 6, S3 12, S4 17, S5 22 degrees of tilt.
4. **Torque is fine everywhere.** Holding a pod with a 400 g lettuce needs at most 1.27 N m (upright D1, shoulder lift) = 67 % of the 1.9 N m stall at 7.4 V (44 % of the 2.9 N m at 12 V). Rolled needs at most 1.10 N m. Nothing is within reach of the stall.
5. **Rolled lowest corner over the lid.** The plate alone has 69 mm to the lid at 45 degrees (66 mm upright). With the real cart CAD (`sampler_parking_socket`, `sampler_pu_coil`) the gap is **22 mm at 30 degrees**
   (the worst angle while rolling) and **29 mm at 45 degrees**, against 45 mm upright. The rough estimate of 11 mm is not reproduced: it would need a part 18 mm deeper than anything in the CAD. The CAD arm envelope
   in its folded pose (base on the battery) is a different story: it reaches the lid from about 22 degrees of roll, so a rolled cart must never carry the arm folded like that.
6. **Pillar and water station.** Station behind the pillar: arm 86 mm or more from it, cart 100 mm (upright) or 49 mm (rolled, plate corner). Pillar: arm 82 mm or more. **The cart is the tight part:** the 146 mm plate end is only
   **19.5 mm from the pillar when rolled at x -130** (29.5 mm at -140; 0 at about -110), and the sleeve end is 35 mm from it upright. The cart cannot pass the pillar on the track at all with this spacing (see "Open questions"), so nothing here moves the cart from the tray to the store.

**Recommendation.** Do not build the 45 degree roll. Upright reaches the whole tray, the store front row and the rest, with the claw sideways-tilted up to about 22 degrees at the outer columns.
If that tilt is too much for a vertical pod, fix the geometry, not the roll: (i) centre the tray columns on the cart stop (4 columns at 38 mm are +-57 mm: the claw then tilts at most about 11 degrees; with the cart at x -130 a vertical
claw only works for pods within 11 to 15 mm of the cart centre line, 10 degrees within 52 mm, 15 degrees within 78 mm), or (ii) let the cart stop once per column pair. Both need a straighter or longer track under the tray: the tray
(x -247 to -133) hangs 69 to 107 mm past the end of the straight run (-140) in columns 3 and 4.
Do not raise the pods: with CAD cell tops (30 mm higher than the brief) a vertical claw already fails for rows B to D in column 1 (9 to 12 degrees).

## What was modelled

World = the sim/unit frame of the first round (mm, X along the track, Y front -, Z up). Track pipe y -60, z 579, r 16; bottom run straight from x -140 to +140. Cart plate front face 56 mm out of the pipe axis, plate centre 60 mm under it.
Arm base straight on the plate, no battery under it (`cad/cart_dims.py`: with the CAD battery stack the base moves 50 mm out, see variants). Roll = turn of the whole cart round the pipe axis, + turns the arm base axis
down and forward. Tray 4 x 4 pods, 38 mm pitch, rows A to D at y -155, -117, -79, -41 (A nearest the arm), columns 1 to 4 from x -133 to -247 (centred at -190), pod top z 224. Store: front row S1 to S5 at x 134 to 246 (28 mm pitch, centred
at 190), y -147, z 225, two queued rows behind it. Carts park at x -130 (tray) and +130 (store). Pillar 75 mm OD at x = y = 0 from the lid up. Lid top z 369 (210 mm under the pipe, `cad/layout.py`).
Water station 200 x 100 x 113 on four legs at x -100 to 100, y 55 to 155 (behind the pillar, assumed: the render gives no numbers).

Where this differs from the brief or the first round:
- **Plate:** `cad/cart_dims.py` gives 168 mm across the pipes (hangs down) and 146 mm along the track (PLATE_ZH 73). The first round had them the other way round. Fixed in the roll layout; the first-round tables are not near enough to the plate to change.
- **Battery:** none on the plate (where it goes is open). `battery="under_arm"` is the CAD stack.
- **Pod heights:** brief numbers (224 / 225). CAD cell tops are 30 mm higher (`pod_dz_mm=30`, see variants).
- **Store front row:** the five stick ends at 28 mm pitch are assumed; the CAD does not give the pick position along the store.
- **The lid:** a solid slab in the distance checks, not in the played tour (the pick holes are not modelled). **The claw, wrist housing and in some poses the forearm go below the lid top** (table in "Collisions"): the pick hole has to be a slot for the claw and wrist, about 70 x 50 mm, not a round 29 mm hole.
- **Wrist roll** is free (it only turns the jaws about the claw axis). The claw is the same envelope as in the first round, not the real jaw.

"Vertical" = claw within 3 degrees of straight down. "Margin" = how far the pod could be further from or closer to the arm along the horizontal line from the pan axis and still be reachable (smaller of the two, mm): first with the claw vertical,
then with the cell's own tilt plus 3 degrees. Negative = how far it would have to move to be reachable. "none within 250" = not reachable for any shift up to 250 mm.

## Case (a): tray, cart rolled 45 degrees

| Cell | Claw | Margin, vertical claw (mm) | Margin at 10 deg tilt (mm) | Pan / lift / elbow / wrist (deg) | Closest joint limit | Worst servo (N m, % of 1.9) | Closest the arm gets to anything solid (mm) |
|---|---|---|---|---|---|---|---|
| A1 | **38 deg tilt** | none within 250 | +24 | -1 / -100 / 34 / 59 | shoulder lift 0.3 deg | 0.52 (27 %) | 8 (tray/shelf) |
| A2 | **40 deg tilt** | none within 250 | +43 | -18 / -100 / 37 / 55 | shoulder lift 0.4 deg | 0.49 (26 %) | 6 (tray/shelf) |
| A3 | **23 deg tilt** | none within 250 | +18 | -32 / -86 / 97 / -67 | elbow flex 0.3 deg | 0.64 (34 %) | 9 (next pod) |
| A4 | **29 deg tilt** | none within 250 | +18 | -43 / -57 / 87 / -84 | elbow flex 9.6 deg | 0.80 (42 %) | 5 (next pod) |
| B1 | **43 deg tilt** | none within 250 | +220 | -1 / -99 / 46 / 51 | shoulder lift 0.9 deg | 0.55 (29 %) | 1 (next pod) |
| B2 | **43 deg tilt** | none within 250 | +252 | -15 / -100 / 50 / 46 | shoulder lift 0.1 deg | 0.53 (28 %) | 1 (next pod) |
| B3 | **19 deg tilt** | none within 250 | +7 | -28 / -56 / 96 / -89 | elbow flex 1.0 deg | 0.86 (45 %) | 6 (next pod) |
| B4 | **26 deg tilt** | none within 250 | +18 | -38 / -41 / 87 / -92 | wrist flex 3.0 deg | 0.90 (47 %) | 5 (next pod) |
| C1 | **44 deg tilt** | none within 250 | +252 | -1 / -99 / 61 / 37 | shoulder lift 1.1 deg | 0.64 (34 %) | 0 (next pod) |
| C2 | **44 deg tilt** | none within 250 | +252 | -13 / -99 / 64 / 32 | shoulder lift 1.1 deg | 0.68 (36 %) | 1 (next pod) |
| C3 | **19 deg tilt** | none within 250 | +17 | -24 / -42 / 94 / -90 | elbow flex 3.4 deg | 1.00 (53 %) | 6 (next pod) |
| C4 | **26 deg tilt** | none within 250 | +18 | -33 / -28 / 85 / -94 | wrist flex 0.9 deg | 0.98 (52 %) | 5 (next pod) |
| D1 | **15 deg tilt** | none within 250 | +7 | -1 / -29 / 94 / -95 | wrist flex 0.1 deg | 1.08 (57 %) | 7 (next pod) |
| D2 | **18 deg tilt** | none within 250 | +16 | -11 / -31 / 92 / -91 | wrist flex 4.1 deg | 1.10 (58 %) | 6 (next pod) |
| D3 | **23 deg tilt** | none within 250 | +17 | -21 / -22 / 87 / -94 | wrist flex 0.8 deg | 1.07 (56 %) | 6 (next pod) |
| D4 | **29 deg tilt** | none within 250 | +24 | -30 / -16 / 80 / -92 | wrist flex 3.1 deg | 1.07 (56 %) | 5 (next pod) |

## Case (b): tray, cart upright (for comparison)

| Cell | Claw | Margin, vertical claw (mm) | Margin at 10 deg tilt (mm) | Pan / lift / elbow / wrist (deg) | Closest joint limit | Worst servo (N m, % of 1.9) | Closest the arm gets to anything solid (mm) |
|---|---|---|---|---|---|---|---|
| A1 | vertical | +118 | +123 | -1 / 39 / 48 / -85 | wrist flex 10.4 deg | 0.95 (50 %) | 13 (next pod) |
| A2 | **8 deg tilt** | -36 | +21 | -8 / 42 / 45 / -87 | wrist flex 7.8 deg | 0.91 (48 %) | 13 (next pod) |
| A3 | **15 deg tilt** | -71 | +18 | -15 / 41 / 42 / -82 | wrist flex 12.6 deg | 0.90 (47 %) | 13 (next pod) |
| A4 | **22 deg tilt** | -108 | +19 | -22 / 44 / 36 / -80 | wrist flex 15.5 deg | 0.84 (44 %) | 12 (next pod) |
| B1 | vertical | +13 | +24 | -1 / 60 / 35 / -93 | wrist flex 2.4 deg | 0.95 (50 %) | 8 (next pod) |
| B2 | **8 deg tilt** | -27 | +15 | -8 / 62 / 32 / -94 | wrist flex 0.8 deg | 0.92 (48 %) | 8 (next pod) |
| B3 | **15 deg tilt** | -65 | +16 | -15 / 61 / 30 / -90 | wrist flex 5.4 deg | 0.91 (48 %) | 8 (next pod) |
| B4 | **22 deg tilt** | -103 | +18 | -22 / 63 / 23 / -86 | wrist flex 9.0 deg | 0.85 (45 %) | 8 (next pod) |
| C1 | vertical | +42 | +47 | -1 / 79 / 18 / -94 | wrist flex 0.5 deg | 0.98 (52 %) | 8 (next pod) |
| C2 | **8 deg tilt** | -40 | +21 | -8 / 80 / 15 / -94 | wrist flex 0.6 deg | 0.98 (52 %) | 8 (next pod) |
| C3 | **15 deg tilt** | -72 | +18 | -15 / 80 / 12 / -91 | wrist flex 3.8 deg | 0.95 (50 %) | 8 (next pod) |
| C4 | **22 deg tilt** | -108 | +19 | -22 / 82 / 5 / -87 | wrist flex 8.0 deg | 0.92 (48 %) | 8 (next pod) |
| D1 | vertical | +3 | +12 | -1 / 98 / -5 / -91 | shoulder lift 2.1 deg | 1.27 (67 %) | 8 (next pod) |
| D2 | **8 deg tilt** | -62 | +14 | -8 / 99 / -8 / -90 | shoulder lift 0.6 deg | 1.27 (67 %) | 8 (next pod) |
| D3 | **15 deg tilt** | -94 | +16 | -15 / 100 / -11 / -87 | shoulder lift 0.5 deg | 1.23 (65 %) | 8 (next pod) |
| D4 | **22 deg tilt** | -122 | +17 | -22 / 99 / -16 / -81 | shoulder lift 1.3 deg | 1.18 (62 %) | 8 (next pod) |

## Case (c): store front row, cart upright

| Cell | Claw | Margin, vertical claw (mm) | Margin at 10 deg tilt (mm) | Pan / lift / elbow / wrist (deg) | Closest joint limit | Worst servo (N m, % of 1.9) | Closest the arm gets to anything solid (mm) |
|---|---|---|---|---|---|---|---|
| S1 | vertical | +59 | +116 | 1 / 43 / 46 / -87 | wrist flex 7.8 deg | 0.95 (50 %) | 3 (next pod) |
| S2 | **6 deg tilt** | -24 | +21 | 6 / 46 / 44 / -90 | wrist flex 5.0 deg | 0.92 (48 %) | 3 (next pod) |
| S3 | **12 deg tilt** | -51 | +18 | 12 / 47 / 42 / -88 | wrist flex 6.7 deg | 0.90 (47 %) | 3 (next pod) |
| S4 | **17 deg tilt** | -78 | +18 | 17 / 46 / 39 / -84 | wrist flex 11.2 deg | 0.89 (47 %) | 3 (next pod) |
| S5 | **22 deg tilt** | -106 | +18 | 22 / 48 / 34 / -82 | wrist flex 13.1 deg | 0.85 (45 %) | 2 (next pod) |

## The specific checks

### Rolled cart, lowest corner over the lid

Depth below the pipe axis and gap to the lid top (the lid is 210 mm under the pipe), by roll angle. "CAD" = the real cart CAD (`cad/water_assembly.py` cart scene: plate, sleeves, sampler pump, coil, parking socket), every vertex rolled
about the pipe axis (`docs/pod-grab-reach/cad-depth-roll.json`, all angles 0 to 60 in steps of 5):

| Roll | CAD lowest part | CAD depth (mm) | CAD gap to lid (mm) | Sim plate bottom corner gap (mm) |
|---|---|---|---|---|
| 0 | sampler parking socket | 165.0 | 45.0 | 66.0 |
| 15 | sampler parking socket | 182.7 | 27.3 | 56.4 |
| 30 | sampler parking socket | 187.9 | **22.1** | 57.3 |
| 45 | sampler coil | 181.3 | **28.7** | 68.6 |
| 60 | sampler coil | 168.8 | 41.2 | -- |

So the lid gap is smallest on the way (22 mm at about 30 degrees), not at 45 degrees. The folded arm envelope of the CAD (arm base on the battery) is 95 mm under the pipe upright and 304 mm at 45 degrees (94 mm *into* the lid): the roll only works with the arm tucked up, not folded down the plate.

### Near tray cells, rolled: too close to fold?

Yes. A1, A2, B1, B2, C1, C2 sit with the shoulder lift at its -100 degree stop (0.1 to 1.1 degrees from it) and the claw still 38 to 44 degrees off vertical. The shoulder axis is only 169 mm above the pods and 37 mm behind row A, so the wrist (160 mm above a vertical claw) would have to sit about 9 mm under the shoulder axis and 37 mm from it: the 116 mm and 135 mm links cannot fold that tight inside the elbow limit. These cells are also where the claw comes within 0.4 to 1.3 mm of the next pod. Column 3 and 4 and row D are better (15 to 29 degrees), but never vertical.

### Far-left tray corner, upright

D4: x -247, 117 mm sideways of the cart, 191 mm from the plate row. Pan -22 degrees, shoulder lift 99, elbow -16, wrist -81 degrees, claw 22 degrees off vertical. Reachable, 1.3 degrees from the shoulder-lift stop, 62 % of the servo stall, 8 mm from the next pod (envelope). With the claw held vertical it is not
reachable by any pose: the cart would have to stand within about 14 mm of its column (x -247, past the straight run).

### Pillar and water station

| Case | Cart to pillar | Cart to station | Arm to pillar | Arm to station |
|---|---|---|---|---|
| Rolled at -130 | 19.5 mm (plate end) | 48.5 mm (plate corner) | 82 mm or more | 109 mm or more |
| Upright at -130 | 35.1 mm (sleeve end) | 100.7 mm | 84 mm or more | 86 mm or more (leg at x -90) |
| Store, upright at +130 | 35.1 mm | 100.7 mm | 134 mm or more | 186 mm or more |

Cart to pillar by park x (rolled plate, x -140 / -130 / -120 / -110): 29.5 / 19.5 / 9.5 / -0.5 mm (touching). Upright (sleeve): 44.6 / 35.1 / 25.9 / 16.9 mm.

### Collisions (poses at grip height, distances between geoms)

| Against | Tray upright | Tray rolled | Store upright |
|---|---|---|---|
| Plate, pipe | 27 mm or more | 85 mm or more | 46 mm or more |
| Next pod (claw envelope) | 7.6 to 13 mm | 0.4 to 13 mm | 2.2 to 3.3 mm |
| Tray or store shelf | 14 mm or more | 5.7 mm or more | 22 mm or more |
| Forearm, upper arm or shoulder vs lid | forearm 5 to 14 mm *below the lid top* | -22 to +1 mm | forearm 5 to 22 mm below the lid top |
| Wrist housing below the lid top | 52 to 64 mm | 61 to 101 mm | 51 to 66 mm |
| Claw body / tip below the lid top | 113 to 123 / 148 to 152 mm | 119 to 141 / 151 to 160 mm | 112 to 121 / 147 to 150 mm |

No contact with the plate, pipe, pillar, station or tray in any working pose. The lid rows are what the pick hole must pass. The tour clips show two short brushes of the claw tip with the tray plate at D4 (upright) and D1 (rolled) on the joint-space
moves between hover and safe poses (`docs/pod-grab-reach/tour-roll.json`); at the pick poses themselves the clearance is as in the table. The tour never moves the cart past the pillar (see below).

### Least claw tilt by roll angle (degrees; park -130 / +130)

| Cell | 0 | 10 | 20 | 30 | 45 | 60 |
|---|---|---|---|---|---|---|
| A1 | 2.1 | 2.1 | 2.1 | 2.1 | 38.0 | 42.1 |
| A4 | 21.6 | 22.8 | 24.2 | 25.9 | 29.1 | 29.5 |
| B2 | 7.9 | 10.2 | 11.2 | 10.6 | 43.1 | 55.1 |
| D1 | 2.1 | 12.0 | 19.0 | 21.0 | 15.0 | 59.0 |
| D4 | 21.7 | 21.7 | 25.5 | 28.3 | 29.1 | 25.1 |
| S1 | 2.1 | 2.2 | 2.2 | 2.2 | 40.0 | 44.2 |
| S5 | 21.5 | 22.6 | 23.9 | 25.4 | 28.2 | 28.9 |

### Variants (least claw tilt, degrees; full lists in the JSON)

- **Tray 10 mm towards the arm (proposal v3):** upright unchanged (A to D col 1: 2 degrees, col 4: 22), rolled D1 13 instead of 15, others within 2 degrees. Not a factor here.
- **Pods 30 mm higher (CAD cell tops):** upright column 1 becomes A 4, B 9, C 12, D 12 degrees, column 4 24 degrees; store S1 5, S5 24. Rolled: 35 to 58 degrees everywhere (worse).
- **Battery stack under the arm base (CAD):** upright rows A, B unchanged, C 5 to 22, D 20 to 30 degrees; rolled 36 to 60 degrees.

## Open questions

1. **Can the claw grip a vertical pod from 15 to 22 degrees off vertical (sideways), and does the jaw clear the next pod?** The recommendation depends on it. The jaw width is not modelled; the envelope is 7.6 mm from the next pod at 38 mm pitch.
2. **Where does the tray go?** It hangs 69 to 107 mm past the straight run in columns 3 and 4 (x -209, -247 against -140). Centring the tray on the cart stop halves the tilt (about 11 degrees).
3. **The cart cannot pass the pillar.** The plate is 19.5 mm from it rolled and the sleeve 35 mm upright at the park positions; the first round (`docs/pod-grab-and-transplant-scenes.md`) already found the hands do not fit past the spine and bracket. Tray and store are on opposite sides. The clips do not move the cart between them.
4. **Pick hole size in the lid:** a slot of about 70 x 50 mm for the claw and wrist, and the forearm dips through the lid plane in some poses (5 to 22 mm).
5. **Where does the battery go** (not on the plate, not under the arm)? Under the arm the far rows fail.

## Sim id

The hosted `run_sim` is not reachable from this session, so there is no hosted sim id. The model is a normal `sim/` generator: `run_sim(model="pod_grab", params={"layout": "roll", "tour": "tray"}, duration_s=45, record=True)` plays the tray clip
(`"tour": "store"` the store clip, `"roll_deg"` sets the roll) once the branch is picked up; the clips above were recorded here with the same generator.

## Re-running

```
pip install mujoco numpy imageio imageio-ffmpeg trimesh scipy
python3 sim/pod_grab_roll_check.py                                                    # docs/pod-grab-reach/results-roll.json
MUJOCO_GL=glfw xvfb-run -a python3 sim/pod_grab_roll_check.py --clip                  # both clips + tour-roll.json (MUJOCO_GL=egl without xvfb)
MUJOCO_GL=glfw xvfb-run -a python3 sim/pod_grab_roll_render.py                        # PNGs and GLBs in cad/renders
pip install cadquery && python3 sim/pod_grab_roll_cad_depth.py                        # docs/pod-grab-reach/cad-depth-roll.json
```
Params: `layout` (`roll`), `roll_deg`, `tour`, `tilt_tol_deg`, `pod_dz_mm`, `tray_shift_mm`, `battery` (`beside` is ignored in this layout: none; `under_arm`), `stall_nm`, `load_kg`.
