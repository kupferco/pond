# Cart roll redesign plan (Pond task 265)

Status: PLAN ONLY, nothing is built. Written 17 Nov 2026 from Dani's decision of the same day.
Reference sketch: `cad/cart_roll_option_a.py` on `origin/claude/drafts` (rough, not final dimensions).
Other plans read before writing: there are no other files in `docs/plans/` on `main` or on any open branch
(`git fetch origin` run; the only related docs are `docs/render-server-plan.md` and `docs/sim-server-plan.md`, which do not
touch the cart). So nothing here contradicts another plan. It does build on Pond #262 (reach test) and #227 (mirrored hands).

## 1. What changes, in one paragraph

Today the plate hangs on a hinge at each hand (`cad/cart_hinge.py`, `cad/cart_base.py`), turned by a worm drive per hinge. During a transfer the free hand
lets go, the plate swings about the static hand's hinge (hinge axis 30 mm beside the pipe) plus a few degrees on the free hand's own hinge
(`SWING_PATH` in `control-ui/src/cart/transfer.ts`), the cart drives round the bend, and the plate swings back. The new design removes both hinges and both hinge motors.
Each sleeve instead carries wheels on the pipe: 38 mm rubber-roller omni wheels only where a motor drives them, cheap passive rollers everywhere else (owner decision on cost, section 3a). One driven wheel rolls the cart along the pipe. One omni wheel turned 90 degrees (the roll wheel) rolls the whole sleeve, and so
the plate, round the pipe. The plate is now rigidly bolted to both sleeves; the swing is a roll about the static pipe's own centre line.

## 2. What the repo says today (facts the plan relies on)

- Track tube is 32 mm OD (R16): `PIPE_D` in `cad/hand_sleeve.py`, `LOOP_TR = mm(16)` (a radius) in the Transplant layout. The draft `cart_roll_option_a.py` uses `PIPE_R = 8`, i.e. a 16 mm tube. See Q1.
- Current sleeve: R34 outer, R20 bore, 90 mm long, 20 x 8 mm wheels at wheel-centre radius 26, two rows 60 mm apart, six wheels, split jaw with a motor, C-gap 18 mm (30 mm mouth) on the +X side for the M8 track-joint rod and the spine bracket, 60 N preload per spring wheel.
- Pipes of the two hands are 120 mm apart (two tanks touching, pipes 60 mm from the edge), plate 166 x 112 x 6, battery 70 x 50 x 70 under the arm, arm base on the battery.
- Track (Transplant layout): one loop, tube R16, corner radius 150 mm, legs 580 mm apart, track plane 60 mm in front of the spine axis, growing pipe 75 mm OD (R37.5) on the spine axis, two spine brackets (16 x 30 x 30) at x = 0 joining the top and bottom runs, joint rings (R17.5) at four heights per leg, M8 joint rod on the +X (jaw) side.
- Reach test (#262): the cart is already tried "as it is" and "turned 180 degrees about the pipe's own axis" at every station, with ONE sleeve on leg A. That is purely kinematic today (no mechanism), so it stays valid. It needs a real roll mechanism to back the amber results.
- Placeholder scenes (`single-unit`, `four-units`, `pillar`) have no model yet.

## 3. How the roll works, and what it cannot do

Kinematics: the plate is rigid on both sleeves, so it can only roll about ONE pipe at a time: the other hand must be released (jaw open, off its pipe). That is exactly the transfer case.
The reach-test 180 degree roll has only one sleeve on the pipe, so it is fine there. Normal riding with both hands clamped means both roll motors are locked and unused.
Both sleeves carry a roll wheel because transfers go both ways (trip up pipe C releases B and rolls about C, and the other way round). The two sleeves stay true mirrors (check in `check_transfer_hands.py`).

Wheel layout per sleeve, from the draft: top row 3 drive-direction wheels at 120 degrees, bottom row 2 drive-direction wheels plus 1 roll wheel (axle along the pipe).
Wheels (owner decision, 17 Nov, cost: 12 omni wheels at about GBP 10 is too expensive): only the 2 driven wheels per sleeve (the drive wheel and the roll wheel, 4 per cart) are 38 mm rubber-roller omni wheels. The other 4 wheels per sleeve (8 per cart) are cheap passive rollers, see section 3a. Motors: per sleeve one driven drive wheel and the roll wheel. Four motors total, the same count as today (2 drive + 2 hinge worm drives become 2 drive + 2 roll).

Speed and torque, rough (CAD task 1 turns this into a `roll_budget()` next to `torque_budget()` in `cart_dims.py`):
- Roll ratio is poor. A wheel of R19 on a pipe of R16 turns the sleeve at only 19/35 of its own speed. A 0.3 N m worm motor at 60 rpm gives about 16 N at the pipe surface, which is only about 0.55 N m of roll torque (the old 38:1 hinge worm gave about 4 N m). Roll speed is about 33 rpm, fast enough.
- On a vertical pipe (the legs) rolling the plate costs almost nothing (gravity is along the axis). On a tilted or horizontal pipe, a plate cantilevered 150 to 170 mm off the axis carrying about 2 kg of arm and battery needs up to about 3 N m to turn or hold. The transfer rolls the plate before the bend and rides the bend rolled, so the axis tilts while the plate is held rolled.
- Holding is friction, not the gear. The worm locks the roll wheel's shaft, but the sleeve then holds only by that one wheel's contact on the pipe: roughly mu x preload x radius ratio. At 3 N m that is about 100 N of tangential force at the contact, which at mu 0.3 wet needs hundreds of newtons of preload. This is the biggest risk in the redesign (Q4, Q5).
- Along the pipe the same holds: the cart weighs about 3 kg (30 N), held only at the driven wheel's contact. Needs about 100 N preload on that wheel at mu 0.3.
- The 38 mm omni wheels (now only the 4 driven ones) are rated 2 kg (about 20 N) each. The current design uses 60 N per wheel. Preload is therefore limited by the wheel rating, not by the design.

## 3a. Driven omni wheels, passive rollers (owner decision, cost)

Reason: an undriven omni wheel freewheels anyway, so it never helped hold the roll. Grip matters only on the driven wheels, so only those need rubber-roller omni wheels.

- Driven, 38 mm rubber-roller omni: 1 drive wheel and 1 roll wheel per sleeve, 4 per cart (about GBP 40 instead of GBP 120).
- Passive, 4 per sleeve, 8 per cart: either (a) ball transfer units, or (b) rubber-coated skate bearings (a bearing with a rubber tyre, on a fixed axle). Not decided: the bench test compares them.
- Ball transfer: rolls in any direction, so it suits a passive wheel that must let the sleeve move both along and round the pipe. Risk outdoors: dirt and rain can make the ball stick.
- Skate bearing with rubber tyre: sealed, so better in dirt and rain, but it rolls in one direction only. Across that direction it drags, so each one must be mounted in the direction it can roll and the pair of motions checked (a drag across the roll would work against the drive or the roll wheel). May need a rubber tyre with a crowned profile to skid sideways easily.
- The passive rollers carry the preload and keep the sleeve centred only; the driven wheels carry the traction. Preload on the driven wheels stays as in section 5.
- Their size differs from 38 mm, so the wheel centre radius and pocket depth differ per wheel type: the sleeve is no longer one repeated pocket (see sections 4 and 9).
- Both options must be easy to buy in Brazil (Q9).

## 4. Sleeve dimensions with 38 mm wheels (ASSUMED, to be fixed in CAD task 1)

| Item | Today | Proposed | Note |
|---|---|---|---|
| Wheel | 20 x 8 | driven: 38 x 12 (double row omni); passive: ball transfer unit or skate-bearing roller, smaller (size set by the chosen part) | draft: R19, width 12, hub R13 for the omni; the 54 mm reach below applies to the omni wheels only, passive rollers reach less, so the sleeve can be smaller where only they are |
| Wheel centre radius | 26 | 35 (= 16 + 19) | on the 32 mm tube; 27 if the tube were 16 mm (Q1) |
| Furthest wheel point from the pipe axis | 36 | 54 | radial, because the wheel stands on its edge |
| Sleeve outer radius | 34 | about 61 (54 + 3 clearance + 4 wall) as a full ring | but see "spacing" |
| Row spacing | 60 | about 76 (draft: wheels at z = +/-38) | pocket 40 high + 12 wall |
| Sleeve length | 90 | about 125 | draft housing 130 |
| Roll wheel | none | one in the lower row, axle along the pipe, at 90 degrees round from the plate side | |

Spacing problem to solve first. Two full rings of R61 on pipes 120 mm apart overlap (122 > 120), and the old assertion `PIPE_SPACING - SLEEVE_R - WHEEL_REACH >= 10` fails. The 120 mm is decided
(tanks touching), so the sleeve must not be a full ring. Proposed: a three-lobe frame, wheels at the same angles as today (one on the outside, two at plus and minus 60 degrees towards the spine). At roll 0 the
wheels near the neighbour pipe reach only about 27 mm in X (wheel at 60 degrees: 17.5 + 19 x cos 60), about 35 mm with their carriers, so two hands need about 70 of the 120 mm. During a roll the neighbour hand is
released and the neighbour pipe is at least 120 - 58 = 62 mm clear of the swept circle, which is more than its R16. CAD task 1 proves this by interference check (Q2).

The jaw: today the sleeve splits and the jaw opens 92 degrees so a hand can leave its pipe sideways. With wheels on the jaw (omni wheels are bigger) the jaw lobe carries one wheel pair
and its motor; the jaw-motor stays (N20). Its wedge and knuckle move out with the wheels. The C-gap for the track-joint rod and spine bracket must stay open at the sleeve's home roll angle.

## 5. Grip and preload

- Three wheel positions per row at 120 degrees around the pipe, one fixed, two on spring carriers. Driven omni wheels sit on the carriers that give the most contact; passive rollers fill the other positions (rigid pairs as in `cart_wheel_pairs.py`, rows now 76 mm apart; with passive rollers the pairs mix a driven omni wheel and a passive roller).
- Target preload per wheel is capped by the wheel rating: aim for 20 N, test up to 40 N, never the 60 N of today. Total clamp across a row is then 20 to 40 N per wheel.
- Springs sized for 2.5 mm travel as today. Omni rollers have gaps, so preload is measured per contact with a spring scale in CAD task 3, not assumed.
- Grip is tested statically first (cart on a vertical pipe, power off): along the pipe with 3 kg, and round the pipe with a 150 mm lever and 2 kg (Q4).

## 6. Wet pipe outdoors

- Pipe wet: mu drops to about 0.3 (sim `pipe_climb.py` baseline, 1 Nov: 30 N wet slid, 60 N held). Hold along and around the pipe both depend on one wheel each, so both are the weak points when wet. Rubber rollers on a smooth PVC or steel tube are the design assumption: not tested.
- Plan: a wet-pipe test in the sim first (`sim/pipe_climb.py` extended with an omni wheel contact model: friction along the roll direction, near zero across it), then a bench test with real wheels and a watered pipe.
- Options if it slips (not decided): rubber sleeve or rubber-wrapped section on the pipe where the cart parks; knurled or rubber-tyred roll wheel; the latching solenoid brake that Dani already named as the fallback (draft shows it: solenoid, rod, pad on the pipe). Add the brake only if testing shows the worm gears cannot hold.

## 7. Roll clearance past the spine-to-track bracket, joints and growing pipe

- Track plane is 60 mm in front of the spine axis, growing pipe R37.5, so the surface is 22.5 mm from the track tube centre. Any sleeve of R54 or more at roll 0 or rolled hits the growing pipe if it is ever driven along the top or bottom run near x = 0. Today's R34 sleeve already cannot. The cart reaches the runs only near the corners (leg to bend to run: P_TOP_CM = bend end + 34 cm), so that is acceptable, but the plan makes it a rule: the cart stays within 500 mm of the legs (to be confirmed in task 7, Q6).
- Spine brackets (16 x 30 x 30, at x = 0 on the top and bottom run): the cart never reaches them under the rule above.
- Track-joint rod (M8, +X side) and joint rings (R17.5 on a R16 tube, 1.5 mm proud): the wheels pass the rings (their own 38 mm diameter spans 1.5 mm easily). The rod and nut pass only through the C-gap, so the roll angle must be 0 (home) while the cart passes a joint. Software interlock: no drive along the pipe unless roll is within 3 degrees of home, except inside the declared transfer rolls.
- Roll sweep: when rolled, the sleeve and plate sweep a circle round the pipe. The plate is 52 mm in front of the pipe plane (y = -52) and the arm 100 mm further out. Swept against: the tank lid, the growing pipe, the opposite leg's hand, the spine. The 180 degree roll for the reach test needs the arm to clear the tank at both ends: checked per station in the reach test (collision reason column).

## 8. Transfer scene check: swinging about the pipe centre must clear the curved track, both directions

Why it changes. The old swing turned about a hinge 30 mm beside the pipe and 43 mm in front, with the free hand 180 mm from that axis, and the free hand also turned about 9 degrees on its own hinge (`SWING_PATH` ends at plate 20 degrees, own hinge 9). Now the axis is the static pipe's centre, the free hand is 120 mm from it, and there is no own hinge: the free hand's sleeve is rigid on the plate.
First estimate: to move the free hand 60 mm sideways needs about 30 degrees of roll, against 20 now, and the bend start needs more (the released hand needs the extra turn `da` up to 5.7 degrees and `dh` 15 degrees at 62 to 68 cm). The sleeve is bigger (R54 against R34), so the margin on the pipe's curved part is smaller. It may not clear at all. Hence the check goes first.

Check method (CAD task 1 produces the numbers, scene task 8 proves them):
1. New `control-ui/scripts/search-swing.ts` mode: search the one-dimensional roll angle about the static pipe's centre at each path position `s` (0.25 cm steps through the bend) with contact detection against the free hand's pipe, the curved part, the joint rods and rings, in BOTH roll directions: plate side (front, away from the spine) and spine side (towards the growing pipe, which is the likely blocker), and for BOTH trips (up pipe C releasing hand B, up pipe B releasing hand C).
2. Result per (trip, direction): the corridor of roll angles that clears, or "none". If only one direction clears, the controller picks it (the plan allows this, Q3). If neither clears, the sleeve shape (task 1) or the clearance (track bend radius 150 mm) is revisited before anything else is built.
3. `check-swing` test in `test/sim.test.ts`: both directions, both trips, every 0.25 cm, no contact; replaces the `SWING_PATH` and `BEND_ROWS` tests.

## 9. CAD files that change (build order inside this table)

| # | File | Change |
|---|---|---|
| 1 | new `cad/cart_omni.py` | One shared 38 mm double-row omni wheel (from the draft) for the 4 driven wheels, the motor placeholder and place_drive / place_roll helpers. Also the two passive roller options (ball transfer unit, rubber-coated skate bearing) as swappable parts with their own size, so the sleeve can be drawn with either. No numbers duplicated elsewhere. |
| 1 | `cad/hand_sleeve.py` | New sleeve: 38 mm pockets for the 2 driven wheels, smaller seats for the 4 passive rollers (swappable between ball transfer and skate bearing), three-lobe shape, about 125 mm long, 76 mm rows, roll-wheel pocket, C-gap kept, pad kept or moved (see plate). Version bump v5. |
| 1 | `cad/cart_sleeves.py` | Redraw the hand around the new sleeve; jaw and its wedge re-cut for the bigger wheels; remove hinge leaves, worm wheel, worm and bracket; add the drive motor and roll motor on each sleeve; scenes clamped / released / released_off / transfer updated (transfer shows the roll). |
| 1 | `cad/cart_wheel_pairs.py` | Rigid pairs now carry a driven omni wheel (38 x 12) and passive rollers; the roll wheel is a single driven omni. `corner` model (150 mm bend) redone with the bigger rigid sleeve: check it still bends (sagitta of a 125 mm sleeve on R150 is about 13 mm, so the wheel clearance must grow). |
| 2 | `cad/cart_hinge.py` | Retired: delete after the last import is gone (cart_sleeves, cart_assembly, check_transfer_hands). |
| 2 | `cad/cart_dims.py` | Delete hinge and worm-drive constants (`HINGE_*`, `WORM_*`, `WHEEL_Z*`, `KNUCKLE_Z`, `TONGUE_*`, `torque_budget`), new sleeve numbers, `PLATE_X0/X1` from pipe spacing and sleeve pad (no hinge offset), new `roll_budget()`, spacing asserts rewritten. `control-ui/src/cart/dims.ts` mirrors these (see scenes). |
| 2 | `cad/cart_base.py` | Plate rigidly bolted to both sleeve pads: no leaves, no tongues; plate edges and widths from the new pad position; stays 6 mm. |
| 2 | `cad/cart_geom.py` | Plate helpers only: remove hinge references. |
| 3 | `cad/cart_assembly.py` | Whole cart: new sleeves, rigid plate, motors, no hinges. |
| 3 | `cad/cart_arm.py` | Arm on cart: base position and folded pose unchanged unless the plate moves; torque and reach lines recomputed; check clearances to the bigger sleeve. |
| 3 | `cad/cart_pod_holder.py` | Fit: cup hangs from the plate's bottom edge at z = -88 and the sleeves ended at z = -45; the new sleeves end at about z = -62, so the clearance drops from 43 mm to about 26 mm, and the bigger lobes may enter the cup's x band. Re-run its `check()` (pod and O-ring squeeze, distances to arm, battery, motors). Straight 90 degree cup is kept. |
| 3 | `cad/check_transfer_hands.py` | Mirror check updated to the new parts (sleeve, roll wheel, motors); hinge-leaf checks removed. |
| 3 | `cad/render_transfer_hands.py`, `cad/export_cart_v2_views.py`, `cad/render_base_gallery.py`, `cad/render_cart_wheel_pairs.py` | Update to the new models (they import the files above). |
| 3 | `cad/hand_sleeve.py` consumers `cad/track_joint.py`, `cad/spine_joint.py` | No change expected; re-check rod and nut still pass the C-gap (the gap is now narrower in relation to the sleeve). |
| 3 | drawings (`docs/drawings/`) | Re-export the drawings that include the cart; old v4 hinge drawings kept in history. |
| - | `cad/pipe_collar.py`, `cad/clamp_collar.py`, `cad/pick_hole_*.py` | Match on the word "hinge" but are about collars and membranes: no change. |

## 10. MuJoCo scenes that use the cart (after the CAD is done)

The scene geometry is written by hand in TypeScript (it does not read the CAD), so each scene is updated from the new CAD numbers.

| # | Scene | Files | Change |
|---|---|---|---|
| 4 | shared cart model | `control-ui/src/cart/dims.ts`, `model.ts`, `transfer-model.ts`, `track.ts` | New sleeve, wheel and plate numbers; delete hinge, worm, tongue and bracket geoms and `hinge1/hinge2` joints and actuators; add a roll joint per sleeve (about the pipe axis) with a roll actuator; wheels modelled as cylinders with anisotropic friction (high rolling direction, near zero across it) to stand in for omni wheels. The `plateflip` joint in `model.ts` and the rotation motors `bh1/bh2`, `rot1/rot2` (the old "swing about the pipe axis" in the Cart scene) are replaced by the roll joint. |
| 5 | Cart on track | `scenes/cart.ts` | Drive along the track with the new sleeve; the existing "swing" control becomes "roll"; the bend (150 mm) check with the bigger rigid sleeve (the `BEND_CHORD_MM` of 3.4 becomes about 13 mm and the clearances are re-searched). |
| 6 | Transfer | `scenes/transfer.ts`, `cart/transfer.ts`, `scripts/search-swing.ts`, `scripts/search-bend.ts` | The roll about the pipe centre in both directions (section 8); `SWING_PATH`, `BEND_ROWS`, `CLEAR_DEG`, `SWING_DEG`, the hinge speed limit (`HINGE_DEG_S_CAD`) become roll corridor, roll speed (about 33 rpm of the sleeve, limited by the motor) and the roll angle at home. Controller interlocks stay (roll only with the free hand open and the static hand closed). |
| 7 | Pod grab | `scenes/pod-grab.ts`, `podgrab/*` | Uses the cart with the pod holder cup on the plate: new plate and sleeve positions, new cup clearance, the arm base pose; re-check the pick and place trajectories. |
| 7 | Transplant seedling | `scenes/transplant.ts`, `transplant/layout.ts`, `transplant/task.ts`, `transplant/apply.ts` | Uses "the real cart exactly as in the Transfer scene" (comment at `layout.ts:215`): update with the cart; the one sleeve is bigger so the arm base `XB` and the track plane distance (60 mm in front of the pipe axis) are re-checked against the tank lid and collar. Re-run `check-transplant-reach`. |
| 8 | Reach test | `scenes/reach-test.ts`, `reach/*`, `scripts/check-reach.ts`, `export-reach.ts`, `reach-variants.ts` | Stations: the roll 0 and roll 180 are now real mechanism states, so add the roll sweep clearance (the arm and plate swept between 0 and 180 must not hit the tank or lid; this is the new "collision" test of the move, not just the end pose). Re-run all 24 holes and 16 pods and compare with the #262 colours (round 3 results). The mount study from #262 is redone for the larger sleeve. |
| 9 | Full unit scenes | `scenes/single-unit.ts`, `four-units.ts`, `pillar.ts` | Placeholders (no model yet): nothing to change; the note is that they must use the new cart. |
| 9 | Render-server sims | `sim/unit_change.py`, `sim/pipe_climb.py`, `sim/bend_test.py`, `sim/guide_test.py`, `sim/arm_pod_pull.py` | The Python sims model the old wheels and hinge. Update the ones that include the cart's wheels or hinge (`unit_change`, `pipe_climb` for the wet test); the rest only if their numbers (preload, wheel size) feed from `sim/constants.py`. |
| 9 | Tests | `control-ui/test/sim.test.ts` | Hinge, worm and swing-path tests replaced by the roll and clearance tests above. |

## 11. Parts list update (`docs/part-list/part-list.json`)

- Add: 38 mm double-row rubber-roller omni wheels, 4 (2 drive + 2 roll), about GBP 10 each (GBP 40), rated 2 kg each. Check the bore and the hub (the draft hub R13). Buy 2 extra for the grip tests (6 in total).
- Add: passive rollers, 8 (4 per sleeve): ball transfer units or rubber-coated skate bearings, whichever the bench test prefers outdoors (dirt and rain can make ball transfers stick). Not decided, so buy a few of each to compare now (for example 4 ball transfer units and 4 skate bearings with rubber tyres, a few pounds in all); the final line is 8 of the winner.
- Change: "Cart drive and hinge motors" (4, 12 V worm-gear motor with Hall encoder) becomes "Cart drive and roll motors", "Cart: 2 pipe drives + 2 roll drives". Count stays 4. The wheel on each shaft is now a 38 mm omni wheel on a hub that fits the motor's D-shaft: add 4 shaft hubs (6 mm D-shaft to the wheel bore, check which shaft the listing has).
- Remove: the brass worm wheels (38 teeth, module 1), the steel worms, hinge pins and knuckles, and any bearing for the worm blocks, if they are listed (the part list has no separate lines for them today: only the motors; the CAD has them as parts, so confirm when the BOM is next checked).
- Drivers: 4 x DRV8871 stays (one per 28 mm motor). The roll motors can stall while holding a load; the DRV8871 handles 3.6 A peak against 1.5 to 3 A stalled, so no change, but the stall current is to be measured in task 3.
- Fuses and wire: unchanged unless the stall test shows more than the assumed 3 A.
- Optional (only if the brake is needed): 2 latching solenoids (one per sleeve) and a driver channel each. Not bought now.
- Weight: the 4 omni wheels, 8 passive rollers and the bigger sleeves add about 0.5 kg (to be measured); the note in the part list about motor lengths (real motors are 60 to 75 mm, shaft at right angle) matters more now: the motor sits beside the wheel inside the sleeve, so it decides the sleeve's real width. Order one motor early (task 1 depends on it).

## 12. Build order

1. Sleeve and wheel CAD (the shared omni file, `hand_sleeve.py`, `cart_sleeves.py`, `cart_wheel_pairs.py`) with the spacing interference check, the swing corridor estimate in 2D and the torque and traction budget.
2. Hinge removal and plate (`cart_hinge.py` retired, `cart_dims.py`, `cart_base.py`, `cart_geom.py`).
3. Cart assembly, arm, pod holder, transfer-hands check and drawings.
4. Shared MuJoCo cart model (`control-ui/src/cart/*`) and the omni friction model.
5. Cart on track scene.
6. Transfer scene with the two-direction roll check (the gate for the whole design).
7. Pod grab and Transplant seedling.
8. Reach test.
9. Placeholders, render-server sims, tests, parts list.

Parts list (item 11) and the 2D swing check can start now in parallel with step 1 (they do not depend on the sleeve drawing). A bench grip test with two real wheels on a pipe can also start now.

## 13. Risks, in the order they could stop the plan

1. Traction: holding the cart along the pipe and the plate rolled against gravity rests on one wheel's friction each, at a preload the wheels are rated for only a fifth of (section 3). If the bench test fails, the brake is needed (and perhaps a pin lock), or a rubber pipe segment.
2. Roll clearance: the free hand may not clear the curved track with only a 120 mm radius and a bigger sleeve (section 8).
3. Sleeve versus 120 mm spacing (section 4).
4. Real motor size inside the sleeve (the worm motor with the shaft at a right angle).
5. Omni wheels on the bend: the bigger rigid sleeve on R150.

## Suggested tasks
1. Bench test: two real 38 mm omni wheels plus a few passive roller options (ball transfer units and rubber-coated skate bearings) on a 32 mm pipe; measure hold along and round the pipe, dry and wet, at 20, 40 and 60 N preload, and compare the passive rollers dry, wet and with dirt for sticking and sideways drag: gives the data for Q4 and Q5 and the passive roller choice (no CAD needed, can start now).
2. Parts list: add the 4 driven 38 mm omni wheels, the passive rollers, hubs and rename the cart motors to drive and roll, remove the hinge worm parts: edits `docs/part-list/part-list.json` only (can start now).
3. Roll budget and swing estimate: a `roll_budget()` (torque, traction, speed) in `cart_dims.py` plus a 2D script that estimates the roll angle needed to clear the curved track in both directions: numbers only, no drawing change (can start now; answers Q2 and Q3 early).
4. Omni wheel module and new sleeve: `cart_omni.py`, `hand_sleeve.py` v5, `cart_sleeves.py`, `cart_wheel_pairs.py`, with the spacing interference check and the roll wheel and motors drawn (after 3).
5. Remove the hinges: retire `cart_hinge.py`, update `cart_dims.py`, `cart_base.py`, `cart_geom.py` for a rigid plate (after 4).
6. Cart assembly, arm, pod holder fit, mirror check, renders and drawings (after 5).
7. MuJoCo cart model: new sleeve, omni friction model, roll joints and actuators in `control-ui/src/cart/*` (after 6).
8. Cart on track scene: roll control, bend clearance with the rigid sleeve (after 7).
9. Transfer scene: two-direction roll clearance search, new controller path and interlocks, tests (after 7; this is the go or no-go for the design).
10. Pod grab and Transplant seedling scenes on the new cart (after 8).
11. Reach test on the new cart: real roll mechanism, roll sweep collision, rerun all 40 targets (after 10).
12. Python sims and test clean-up: `sim/unit_change.py`, `sim/pipe_climb.py` wet test, `test/sim.test.ts` (after 9).
13. Latching solenoid brake (only if the bench or sim test shows the worm gears cannot hold): CAD and parts list (after 12 or earlier if task 1 fails).

## Open questions
### Q1. Is the track tube 32 mm (as in the repo) or 16 mm (as in the draft sketch)?
Context: the draft `cart_roll_option_a.py` uses a pipe radius of 8, but `hand_sleeve.py`, the track and the Transplant layout all use 32 mm OD. The wheel centre radius, the sleeve size and the roll ratio all follow from this.
Assumed: 32 mm (the repo), and the draft's 8 mm radius is a sketch slip.
Answer: 32 mm, a standard PVC pipe easy to buy off the shelf in both the UK and Brazil. The draft's 8 mm radius is a sketch slip. The goal is the thinnest standard pipe that won't bend: work out the sag with the real span between supports and the cart's weight (allowing for plastic creep over time), and flag it if a standard 25 mm pipe would be stiff enough.

### Q2. May the sleeve be a three-lobe frame instead of a full ring, so the 120 mm pipe spacing stays?
Context: a full ring around 38 mm wheels is about 122 mm across and the two hands are only 120 mm apart; a lobed frame fits but is less stiff and leaves the wheels less enclosed.
Assumed: yes, three-lobe frame, spacing stays 120 mm.
Answer: yes, three-lobe frame, spacing stays 120 mm.

### Q3. If the free hand clears the curved track in only one roll direction, is it fine for the controller to always use that direction?
Context: the Transfer check (section 8) may show the spine side is blocked by the growing pipe; the brief asks for both directions to be checked, not necessarily both to work.
Assumed: yes, use the one that clears; if neither does, stop and come back to you.
Answer: Yes, always use the roll direction that clears; if neither does, stop and come back to the owner. Note on terms: the hinges are gone in the new design and the whole cart (the base) spins around the pipe on the omni wheels, so call it the base or cart, not a new 'plate'. Add angle and position sensing to the plan: the controller tracks roll angle and position along the pipe by counting the omni wheel / drive motor turns, and corrects drift at a home station near the base of the track: a ring of magnet tape all the way round the pipe (can't be missed, means 'you are at home'), then shortly after it a single point magnet that marks zero (both zero roll angle and zero position). A hall sensor on the cart reads them. If the cart gets lost, it drives until it hits the ring, moves on to the point and rolls until it finds it. Optionally point magnets at other stations (corners, legs) as position checkpoints, and an accelerometer/IMU (e.g. BNO055) for absolute roll on horizontal sections. The cart can roll a full turn to find zero.

### Q4. Can the omni wheels be preloaded above their 2 kg (about 20 N) rating, say up to 60 N like today?
Context: holding a 3 kg cart on a wet pipe by one wheel's friction needs far more than 20 N; the rating is probably a static load figure, but it is not known.
Assumed: allow up to 40 N in tests, and treat 20 N as the design value until the bench test says otherwise.
Answer: allow up to 40 N in tests, and treat 20 N as the design value until the bench test says otherwise.

### Q5. If the worm gears alone cannot hold the plate rolled on a tilted pipe, do we go straight to the latching brake?
Context: the decision was "no brake at first"; the rough budget in section 3 suggests friction at the roll wheel is not enough when the pipe is not vertical (during the bend).
Assumed: yes, build the brake then (suggested task 13), and before that try the cheaper options (rubber on the pipe, a rubber-tyred roll wheel).
Answer: First choice: use omni wheels with rubber rollers (not hard plastic) so they grip the smooth PVC. If the worm gears plus rubber-roller omni wheels still cannot hold the cart rolled on a tilted pipe, try the other cheap options (rubber on the pipe, a rubber-tyred roll wheel), and only then build the latching brake (suggested task 13). Choose a common omni wheel size (e.g. 48 or 58 mm) easy to buy in both the UK and Brazil (Mercado Livre, AliExpress), not one exact model.

### Q6. May the rule "the cart stays within 500 mm of the legs, never on the middle of the top or bottom run" be written down?
Context: an R54 wheel ring does not fit between the track and the growing pipe (22.5 mm gap), and the spine brackets sit mid-run; today's R34 sleeve already cannot pass either.
Assumed: yes, the cart only works on the legs and corners; the middle of the runs is off limits.
Answer: No, not as written. The pipe runs are secured in the centre, so the middle of a run is the stiffest part and any sag is at the ends (towards the corners), not the middle. The cart must be able to work along the whole bottom run: that is where it moves the seedlings. Check the sag at the run ends with the real cart weight, and add supports near the ends if needed. The top run can be off limits for work: the cart only needs to travel through it.

### Q7. During a transfer, is the roll allowed to be held while the pipe tilts through the bend, or must the plate be rolled back flat before the bend?
Context: today the plate is held rotated through the bend (rotate, drive round the bend, rotate back at 75 cm). Holding rolled while the axis tilts loads the roll wheel with gravity; rolling back first would remove that load but the hand cannot then clear the curve.
Assumed: held through the bend, as today.
Answer: held through the bend, as today.

### Q8. Should the 180 degree roll for the reach test be allowed only on the vertical legs?
Context: on a tilted pipe the roll with the arm carries up to about 3 N m, more than the roll motor gives (about 0.55 N m); on the legs it carries almost nothing.
Assumed: yes, legs only (the reach test stations are already on the legs and the runs; the run stations would then count as "roll 0 only").
Answer: Yes, the 180 degree roll is allowed on the vertical legs only. On the top and bottom runs the cart stays flat (roll 0, parallel to the track plane) so it can pass the brackets that hold the track; run stations count as roll 0 only.

### Q9. Is it acceptable to order one real worm motor and one pair of omni wheels now, before the CAD is final?
Context: real 28 mm worm motors are 60 to 75 mm long with the shaft at a right angle, and the omni wheels' real hub and bore are unknown; both decide the sleeve's real width and the traction answer. About GBP 30 in total.
Assumed: yes, order two wheels and one motor now.
Answer: Yes, order now for a bench test (grip on real PVC, preload, worm hold on a tilt, exact sizes for the CAD): one worm motor and the rubber-roller omni wheels. The owner is happy to buy all the wheels needed for the prototype in the UK now, as they're cheap and light there. Later production units will be built in Brazil, so the chosen wheel and motor must also be easy to buy there.

Update (17 Nov, owner decision on wheel cost, see section 3a): the bench test order for Q9 is now one worm motor, the driven rubber-roller omni wheels (2 for the bench test, 4 are needed per cart), plus a few passive roller options to compare: ball transfer units and rubber-coated skate bearings, tested wet and dirty for sticking. The answer above is unchanged.
