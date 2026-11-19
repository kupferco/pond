# Cart redesign: motors inward, clear of lettuce (OpenPocket #312)

Status: PLAN ONLY. Nothing in the sim, the CAD or the drawings is changed. Waiting for the owner to answer section 6 and pick a layout.
Picture: `docs/plans/img/cart-motors-layouts.svg` (cross-section looking down the pipe: today, layout A, layout B; red = motor, green dashed = sleeve silhouette).
Numbers come from `cad/cart_omni.py`, `cad/hand_sleeve.py`, `cad/cart_dims.py` (roll_budget) and the #277 finding. Anything not in the repo is marked ASSUMED.

## 1. What sticks out today

Both driven wheels sit on the outer lobe (the side away from the other hand). The 28 x 55 mm worm motors are mounted on the outside of that lobe, bodies pointing sideways:
- Drive motor: on the spine (plant) side of the lobe, body from 51 to 106 mm out of the pipe axis, 13 to 41 mm towards the spine. The sleeve itself only reaches 61 mm, so it sticks out 45 mm.
- Roll motor: below the lower end of the sleeve (23 mm past it), body also out to 106 mm.
- So each hand is about 106 mm wide outboard, the whole cart about 330 mm wide, and the released hand's motors swing a 226 mm radius round the static pipe during a roll (the sleeve alone would be 181 mm).

Nothing can be closer to the plants than the wheels themselves (the +/-60 degree lobes reach 54 mm, the outer lobe 61 mm). So the clean rule is: **no motor, bolt or cable outside the sleeve silhouette (R61 about the pipe, seen along the pipe)**.

## 2. Lettuce head envelope (ASSUMED, please confirm, question 1)

Repo has no head size. I assume a mature head 200 mm across and 150 mm out from its cup (butterhead or looseleaf). Note the track tube is only 22.5 mm from the growing pipe's surface (track plane 60 mm in front of the spine axis, pipe R37.5), so a mature head reaches the track tube and any sleeve on it no matter where the motors are. Motors only matter for plants that are still smaller, or if the cart is meant to pass mature heads. Question 1 asks which.

## 3. Three layouts

| | Today | A. Along the pipe (tucked) | B. Flip to the plate side | C. One motor per hand |
|---|---|---|---|---|
| Idea | motors beside the lobe, pointing sideways | motor bodies lie parallel to the pipe, inside the lobe width (30.8 mm lobe, 28 mm motor): drive motor continues up from the drive wheel, roll motor down from the roll wheel | same as today but mirrored onto the plate (arm) side of the lobe | one motor per hand drives both wheels through a printed dog clutch (drive or roll, never both) |
| Furthest point from the pipe axis, spine side | 114 mm | 54 mm (nothing past the lobe) | 54 mm (spine side clean) | 54 to 61 mm |
| Furthest point, plate side | 61 | 61 | 114 (under and beside the plate, away from plants) | 61 |
| Sticks out sideways | 45 mm | 0 | 45 mm | 0 |
| Sticks out along the pipe | 23 mm below | about 47 mm each end | 23 mm below | about 47 mm one end |
| Released hand's swing radius in a roll (static pipe to far point) | 226 | 181 | 226 | 181 |
| Motor mass lever on the roll (ASSUMED 0.2 kg per motor) | about 80 mm | about 35 to 41 mm | about 80 mm | about 40 mm |
| Roll load saved (of about 2.6 Nm) | 0 | about 0.17 Nm (7 %) | 0 | about 0.25 Nm and 0.4 kg less on the cart |
| Printability | now | cradle prints flat, no new overhang; gearbox clamp on the lobe wall | same as today | dog clutch and shift fork are fiddly in PETG; most risk |
| Bend (R150) | sleeve 124 long, 13 mm sagitta | overall about 218 long: the motors at 35 mm offset would need a bend sweep check (about 40 mm sagitta at the ends) | as today | as A on one end |
| Parts | 4 motors | 4 motors | 4 motors | 2 motors + clutch |

Each layout in one line:
- **A** removes the sideways protrusion completely and cuts the roll lever. The price is length along the pipe and the bend check.
- **B** is the cheapest change (a mirror) but still sticks out 45 mm sideways, only on the side without plants, and does nothing for roll swing.
- **C** is best on mass and protrusion but adds a mechanism that must be bench-tested; keep as a later upgrade.

## 4. What the 277 roll-budget finding says about this

Re-running the roll_budget numbers by hand (cadquery is not installed here, so `roll_budget()` itself was not run): the roll load is about 2.3 Nm without the sleeve motors, about 2.6 Nm with them (the budget leaves the own-hand motors out). Holding that on a 35 mm lever at mu 0.3 needs about 250 N of preload; the design gives 20 N, which holds about 0.21 Nm, roughly 12 times too little. Moving the motors changes this by 7 % at best (A) and about 10 % (C). **Motor position cannot fix the roll-hold problem; it needs its own answer** (a pin or sprung latch brake on the sleeve, rubber or ribs on the pipe where the cart parks, or a bigger wheel). Question 3.
Rolling towards the spine and hitting the free pipe at about 13 degrees is caused by the plate, battery and arm boxes (`cad/roll_swing_estimate.py`), not by the motors, so no layout here changes it. A and C do shrink the released hand's swing radius, which helps the sweep against the spine.
Drive along a vertical pipe has the same friction issue (the cart's 30 N weight against 6 N of friction at 20 N preload); also unchanged by motor position.

## 5. Recommendation

**Layout A** now, with C kept as a later upgrade. Reasons: nothing leaves the sleeve silhouette towards the plants; the only cost is length, which can be checked in CAD before committing; the printed parts stay simple. B is only worth it if the bend check fails and the plants are known to grow on the spine side only.

## 6. Questions for the owner (answer before anything is built)

1. Plants: which way do heads grow relative to the track, and how big do they get (I assumed 200 mm wide, 150 mm out)? Does the cart ever have to pass mature heads, or only seedlings and gaps?
2. Is a longer cart acceptable (about 218 mm instead of 124 on the pipe)? It affects the bend, the lowest stop at 0.64 m, and the spine bracket.
3. Roll hold: may I plan a separate latch or brake for the roll (needed whatever the motors do), or do you prefer rubber on the pipe?
4. Do you know the real motor weight and size you will buy (I assumed 28 x 55 mm worm gearmotor, 0.2 kg)?
5. Layout A, B or C (or "A first, C later")?

## 7. After the pick (not started)

Edit `cart_omni.py` motor placement, `hand_sleeve.py` (cradle, lobe), then the sim (`control-ui/src/cart/omni.ts`) and the drawings; re-run `check()` in `cart_assembly.py`, the reach and swing checks; render iso, front, top, side and the GLB.
