# Cart redesign: motors inward, clear of lettuce (OpenPocket #312)

Status: OWNER PICKED LAYOUT B (2026-11-19). Section 6 now holds the answers; the CAD, sim and drawings are updated for layout B (section 7). Sections 1 to 5 are the original plan and are left as written.
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

## 6. Owner's answers and what was built (layout B)

Decision: **layout B**. Both motors of each hand go on the plate (arm) side, tucked under the plate and pointing inward, so nothing points out towards the plants. The cart stays its current length (sleeve 124 mm, pad and plate length unchanged).

| # | Question | Answer |
|---|---|---|
| 1 | Plants and head size | ASSUMPTION kept: mature head 200 mm across, 150 mm out of its cup. Not confirmed with real plants. With layout B no motor, bolt or cable is on the plant side of the lobe any more; the wheels (R54) and sleeve (R61) are unchanged, so a mature head still reaches the track tube (section 2). |
| 2 | Longer cart | Not needed. Layout B keeps the 124 mm sleeve and the 146 mm plate. |
| 3 | Roll hold | Separate later fix. The roll brake (latch, brake or rubber) is NOT part of this change; motor position cannot fix the roll-hold problem (section 4). |
| 4 | Motor size | ASSUMPTION kept: 28 mm x 55 mm worm gearmotor, 0.2 kg each (gearbox 30 x 28 x 22 mm). Real motor still to be bought and measured. |
| 5 | Layout | B. |

How layout B is built (hand frame: pipe along Z, plate on -Y, outer lobe on -X, wheels 35 mm off the pipe axis):
- **Drive motor:** gearbox on the plate side of the outer lobe (y -29.5 to -51.5), its body lying along the pipe and pointing inward, towards the sleeve middle (z 22 down to -33). Nothing on the plant (+Y) side, nothing sticking out sideways.
- **Roll motor:** below the sleeve end as before (3 mm lower than before), body pointing towards the plate (-Y), so it sits under the plate's lower edge.
- Widest point of a hand from the pipe axis on the plant side: 61 mm (the sleeve), was 114 mm. Sideways (-X): 61 mm, was 106 mm.
- Two new numbers needed to make it fit, both ASSUMED: (a) the drive gearbox stands 29.5 mm off the pipe axis so its corner clears the sleeve tube (R34.5), so the output shaft is about 14 mm longer or has a printed spacer; (b) the mounting pad is 20 mm wide instead of 24 so the motors clear it; the plate is 160 mm wide instead of 168 (the arm base needs 86). Both need a bench check.

**Spine-side roll check** (`cad/roll_swing_estimate.py`, now with the motors as boxes; roll about the static pipe, free hand released, straight leg):
- Rolling towards the spine, the first thing the free pipe meets is still the plate, at **15.0 degrees**, the same as before. The motors alone never touch the free pipe in either roll direction up to the 35.5 degrees the free hand needs to get off its pipe (today's motors did not either). So the motors under the plate do **not** make the clash worse.
- On the bend the clash is at **13.0 degrees** (12.2 before). The 0.8 degree gain comes only from the narrower plate (pad 24 to 20 mm), not from the motors.
- The 3D check in `cad/cart_sleeves.py` (motors against the free pipe, any roll) agrees: the motors never meet the free pipe in a full turn (before: 151 degrees), and the other checks there (spacing, jaw swing, drain) still pass.
- Rolling towards the plate: clears with no contact, as before.
- The 15 degree clash is still far below the 35.5 degrees needed: the plate, battery and arm still block a release by rolling towards the spine (finding #277 stands). Rolling towards the plate works.
- Limit of this estimate: it is a 2D section. On a bend, motors that stand beyond the sleeve ends (the roll motor, today's and layout B's alike) meet a pipe that curves away, so the bend is not modelled for motors; it needs the 3D check later.

Still open (not part of this task): roll brake; real motor dimensions; real head size; the shaft support for the 14 mm longer drive shaft.

## 7. What changed

`cad/cart_omni.py` (motor placement, `LAYOUT`), `cad/hand_sleeve.py` (pad 20 mm, shaft hole through the plate side, standoffs), `cad/cart_wheel_pairs.py`, `cad/roll_swing_estimate.py` (motor boxes), `control-ui/src/cart/omni.ts` (sim motors), then renders in `cad/renders/` (`cart-motors-before-after.png` shows before and after, plus the usual iso, front, top and side of every changed part and `assembly.glb`). `cad/render_motor_layouts.py` makes the before/after picture.
