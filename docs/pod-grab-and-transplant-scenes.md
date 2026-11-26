# Pod grab and Transplant seedling on the omni cart (OpenPocket #284, plan task 265 part 10)

Both scenes now carry the real omni cart (rigid plate on two three-lobe sleeves, 38 mm driven omni wheels, ball cups, battery) instead of the hinge-era cart.
Code: `control-ui/src/cart/omni-scene.ts` (the cart as a static body for scenes where it only rides), `src/podgrab/layout.ts` and `task.ts`, `src/transplant/layout.ts`.
Tests: the "Pond #284" blocks in the Pod grab and Transplant parts of `control-ui/test/sim.test.ts`.
Pictures: `cad/renders/podgrab-omni-*` and `cad/renders/transplant-omni-*` (four views each: iso, front, top, side), GLBs `cad/renders/podgrab-assembly.glb`
(also `assembly.glb`) and `cad/renders/transplant-assembly.glb`.

## The answer, in plain words

- **Transplant seedling works on the new cart.** All four steps run, every frame is in reach with at least 5 degrees of joint margin, and nothing touches (arm, cart, track,
  tank, pipe). The cart stops are unchanged (0.64 m at the tray, 1.073 m at the hole, 0.756 m at the plug holder).
- **Pod grab is built on the real unit (#461, round 8) and the real unit does NOT work for it.** No pod-grab spine, tank or track of its own: the scene takes the unit from the CAD (`cad/parts/unit_dims.py`, `cad/layout.json`, same numbers as the Transplant drawings): the 75 mm growing pipe on its 95 mm socket at the tank centre (x = y = 0) with the 33.7 mm spine tube inside it, the track plane at LOOP_Y = -60 mm, the loop (legs 580 apart, corner radius 150, top run at 1884) and the spine-to-track bracket (16 x 10 mm through the 18 mm sleeve slot). The old sim-only +164 mm move of the track and spine to the back is gone.
  Measured (`node --experimental-strip-types scripts/check-podgrab.ts`):
  * Cart against the column: the sleeves cut into the 75 mm growing pipe by up to **11.5 mm**, for cart centre x from **-8.5 to +8.5 cm** (2.7 mm at -8.5, 11.5 mm at 0). The slot passes the bracket (0 mm) but not the wider pipe. So the cart cannot cross the centre; the store (right) and the tray (left) are on opposite sides.
  * Reach: the arm base is 157.5 mm in front of the tank centre (y = -157.5 mm), the pick holes are at y = -145 mm, **12.5 mm BEHIND the base plane** (tray rows A to D at y = -155 to +16 mm: 2 to 174 mm behind it). The arm works only out of the plate, towards the front, and needs the targets about 150 mm in front of its base (that is how far they were when it worked, with the track moved back 164 mm). So every store row misses by about 163 mm and the tray rows A to D by 154 to 326 mm: **0/16 sockets, 0/60 pods** (single picks to each of A1..D4 all report unreachable; "Fill the whole tray" 0/16).
  * The straight bottom run is only -14 to +14 cm (the loop corners start there); the old scene drew a straight pipe from -40 to +42 cm. The tray (-33.5 to -14.5 cm) and the store (+5 to +26 cm) are mostly out on or past the corners, so the cart would also have to roll up the corners.
  Options (not done, the owner said not to shrink or move the spine): (a) move the pick line and the tray in the CAD towards the back of the tank so the targets are in front of the arm base (about 160 mm, only possible by moving the base: the tank is 400 deep); (b) a longer straight bottom run (loop legs wider, which changes every drawing); (c) a cart with the plate on the spine side and the arm base on the tank side of the pipe (needs the slot and the cart to pass the 75 mm column, or a narrower column at the track height); (d) a different arm mount. `control-ui/test/sim.test.ts` lists the failing pod-grab checks as KNOWN-CLASH (they are not loosened).

## What changed in the scenes

### Transplant seedling
- The cart is `staticOmniCart()` in the same plate frame as before; hand C rides the -y leg, hand B hangs beside it on the inside with its jaw open 92 degrees (built open, no joint).
  The old plate, hinges, worm drives, tongues and drive motors on the plate are gone, as are the old hands.
- The arm base is bolted on the battery front, now **106 mm out of the pipe plane** (was 102 mm): plate face at -56, battery 50 thick (`cad/cart_dims.py` `ARM_Y0`). `XB`, and with it the tray
  and everything placed from it, moved 4 mm. The pod holder cup root is 18 mm out of the new plate face (cart y -74, z -88, `cad/cart_pod_holder.py` v4); its web moved with it.
- Lowest stop: the first stop stays 0.64 m. The new sleeve's -60 degree lobe touches the track corner at 0.63 m, so 0.64 m is still the lowest the cart can go on the straight leg
  (tested: clear at 0.64 m, touching at 0.625 m).
- `check-transplant-reach.ts` gives the same reach table as before (the arm only moved 4 mm along its own base axis).

### Pod grab
- The cart rides the **bottom run on hand B**; hand C, its mirror, hangs open on the inside of the loop, **above the pipe**. The cart centre, the plate centre and the arm base are therefore
  **60 mm above the pipe**. Nothing dangles below the pipe any more (the old cart hung a second hand 100 mm lower). The cart stays flat (roll 0, parallel to the track plane), as Q8 says for the runs.
- To keep every pick and place path as it was, the arm base stays exactly where it was in the world. That moved the track: the track plane is now **y = 0.104** (was 0.040) and the bottom
  run is **210 mm over the lid** (was 320; the CAD says 150), because the battery pushes the arm base 50 mm further out of the plate and the cart centre is 60 mm above its pipe.
  The spine axis is 60 mm behind the track plane (CAD `LOOP_Y = -60`; the scene had 75 mm) so it stays inside the tank's back wall.
- Collisions: the cart's parts collide with the arm only (so the arm is checked against the bigger sleeve, plate and battery; the arm base sits flush on the battery, which is left out of
  that check). Against the spine and the bracket the cart is measured with `mj_geomDistance` in the zone around the spine (`PodWorld.scanCart` / `probeCart`), because a 53 mm overlap
  in the physics throws the parts about and teleported a pod in the store (found and fixed in this part).
- Result: the first pick (store row 3 to socket A1), a full 16 pod fill, and the 8 mm perception error test all behave as before.

## Resolved (#461): the sleeves cross the spine through their slot

Earlier finding (#284): with the sleeves' C gap facing the other hand, the cart hit the spine (up to 53 mm) and the track bracket (10 mm) within 10 cm of the spine. Owner decision: the bracket
is MEANT to pass through the slot, the sleeves were oriented wrongly. Both sleeves (with their jaws, wheels and motors) are now turned about their pipes so the slot faces the spine
(hand B +90 deg, its mirror C -90 deg); the bracket's thin sides go through the slot (16 mm along the pipe, 10 mm across; the 30 mm side points from the pipe to the spine).
`control-ui/src/podgrab/clearance.ts` samples the CAD triangles (mj_geomDistance would use convex hulls, which fill the slot and report a false clash).

The Transplant scene is not affected (it rides a leg: no bracket, no growing-pipe crossing).

## Round 9 (#461): CAD v4 cart, water station, tray 10 mm nearer

- `cad/cart_dims.py` v4 (kupferco/pond commit 30b8e2d, 25 Nov): the SO-101 base is bolted straight on the plate (`ARM_Y0` = -56, no battery under it) and the 70 x 50 x 70 battery stands on its 50 mm edge beside it
  on the riding-hand side (`BATT_X` +59, flush with the plate edge, 4 mm from the arm base). `ARM_X` is -5 in that file (the arm base is 5 mm off the plate centre, so that the 4 mm gap and the flush battery both hold); the brief
  said "centred", the file is followed. The sim reads all of it from the generated constants (no `ARM_SLIDE` any more; `batteryX` removed from `staticOmniCart`).
  The same cart is the cart of the Transplant scene, whose arm base is therefore 50 mm closer to the plate too: its step 4 reach check now fails (listed as KNOWN-CLASH in the tests) and needs its own re-plan.
- Water testing station: a solid block on four legs, from `cad/water_station.py` (exported by `export_sim_model.py`): x 60..260, y 14..108 (74 mm behind the track axis), z 394..507; the arm collides with it in the physics
  and `clearance.ts` tests the cart's CAD triangles against it and against the lid.
- Seedling tray `TRAY_CY` -0.098 -> -0.108 (rows A..D at y -165, -127, -89, -51 mm), still ASSUMED. The layout stays `cart_clearance_mm` 45 (the CAD value); the 110 of the earlier rounds is gone.
- Reach (`scripts/check-podgrab-reach.ts`): the arm does NOT reach with the claw upright. Lifting a pod out of the store needs +52 mm of track height, the carry over the lid +104 (store) to +149 (row D),
  seating in rows B, C, D needs +32, +46, +47. With the claw allowed to tilt while it carries (not implemented), the window is +55 to +80 mm of track height (clearance 100..125). Nothing was changed in the CAD for this.

## Round 10 (#461): the owner's drawing layout (`cad/pond_unit_bottom.py`, 26 Nov)

The pod-grab scene now follows `cad/pond_unit_bottom.py` (brought over from `claude/drafts`; it imports `parts/unit_dims.py` and `parts/pod_store_dims.py` instead of copying their numbers):
cart upright (roll 0, track NOT raised, z 514), real 160 mm claw, a gravity-feed pod store of 7 lanes (pitch 30 mm from x 100) with a 15 degree ramp and a flat landing with a stop lip at the front row (y -165),
a 6 x 3 seedling tray (35 x 25 mm pitch, x -290..-115, y -150..-100, pods vertical) and slots in the lid. `STORE_SLOPE_DEG` is 15 in the CAD and the sim reads it from the generated constants.

- The arm now pans: the cart's straight run is x +/-140 mm, the store reaches to x 280 and the tray to x -290, so the pan joint takes the rest (`task.ts`, `reach.ts`).
- With the claw straight down the SO-101 cannot hold the claw tip higher than about 225 mm, the lid is at 304: over the lid the claw is tilted (`TRANSIT_PITCH` 70 degrees) and straightens as it goes down through the slot.
- Lid slots 70 x 50 mm (50 along x): at 35 mm (tray) and 30 mm (store) pitch they overlap, so the lid over the tray is one window 225 x 135 mm (its front edge is opened out to the lid edge, because the tilted claw cuts the 15 mm strip in front of the slots) and over the store one window 230 x 70 mm: there are NO webs between the cells. For webs the pitch would have to be above 50 mm (x) or 70 mm (y) or the slots smaller than the 31 mm claw allows.
- No silicone collars (a 25 mm pod at 25 mm pitch leaves no room for a ring). Low 12 mm guide walls between the lanes (the open claw, 31 mm across, does not fit beside a pod between 3 mm rails at a 30 mm pitch).
- Reach and cycle results: see the pull request (`scripts/check-podgrab-reach.ts`, `scripts/check-podgrab.ts`).

## Other points to know
- Hand C on the loop interior (above the pipe) matches the Transplant scene (free hand on the interior side). The plate is on the spine side in the Transplant scene (the arm works towards the pipe) and on
  the front, away from the spine, in the Pod grab scene (the arm works into the tank). Both are as the scenes were; the plan does not say which side the real cart uses.
- Drain holes, grip and brake are not touched by this part.
- Legacy files `src/cart/dims.ts`, `model.ts`, `transfer-model.ts` are no longer used by these two scenes (the Cart scene and the tests still read parts of them); they go in the clean-up (part 12).

## Re-running
```
cd control-ui
npm run typecheck && npm test
node --experimental-strip-types scripts/check-transplant-reach.ts
node --experimental-strip-types scripts/export-podgrab.ts OUT_DIR   # then: python3 scripts/render_scene_stages.py OUT_DIR cad/renders podgrab-omni
node --experimental-strip-types scripts/export-transplant.ts OUT_DIR2
```
