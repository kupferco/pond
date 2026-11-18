# Pod grab and Transplant seedling on the omni cart (OpenPocket #284, plan task 265 part 10)

Both scenes now carry the real omni cart (rigid plate on two three-lobe sleeves, 38 mm driven omni wheels, ball cups, battery) instead of the hinge-era cart.
Code: `control-ui/src/cart/omni-scene.ts` (the cart as a static body for scenes where it only rides), `src/podgrab/layout.ts` and `task.ts`, `src/transplant/layout.ts`.
Tests: the "Pond #284" blocks in the Pod grab and Transplant parts of `control-ui/test/sim.test.ts`.
Pictures: `cad/renders/podgrab-omni-*` and `cad/renders/transplant-omni-*` (four views each: iso, front, top, side), GLBs `cad/renders/podgrab-assembly.glb`
(also `assembly.glb`) and `cad/renders/transplant-assembly.glb`.

## The answer, in plain words

- **Transplant seedling works on the new cart.** All four steps run, every frame is in reach with at least 5 degrees of joint margin, and nothing touches (arm, cart, track,
  tank, pipe). The cart stops are unchanged (0.64 m at the tray, 1.073 m at the hole, 0.756 m at the plug holder).
- **Pod grab works on the new cart, but the cart cannot get from the tray to the store.** The sleeves do not fit past the spine and its track bracket. The scene still runs
  (the whole 4 x 4 tray is filled, 16 pods, nothing teleported, the arm hits nothing) because the cart is measured against the spine, not simulated against it; the screen says
  "the sleeves touch the spine" while that happens. Everywhere else on the bottom run the cart is clear, including at the tray end and at the store end.
- **This breaks the plan's rule that the cart works along the whole bottom run (owner answer Q6).** It needs a CAD decision, see below.

## What changed in the scenes

### Transplant seedling
- The cart is `staticOmniCart()` in the same plate frame as before; hand C rides the -y leg, hand B hangs beside it on the inside with its jaw open 92 degrees (built open, no joint).
  The old plate, hinges, worm drives, tongues and drive motors on the plate are gone, as are the old hands.
- The arm base is bolted on the battery front, now **106 mm out of the pipe plane** (was 102 mm): plate face at -56, battery 50 thick (`cad/cart_dims.py` `ARM_Y0`). `XB`, and with it the tray
  and everything placed from it, moved 4 mm. The pod holder cup root is 18 mm out of the new plate face (cart y -74, z -88, `cad/cart_pod_holder.py` v4); its web moved with it.
- Lowest stop: the first stop stays 0.64 m. The new sleeve's -60 degree lobe touches the track corner at 0.63 m, so 0.64 m is still the lowest the cart can go on the straight leg
  (tested: clear at 0.64 m, touching at 0.625 m).
- `check-transplant-reach.ts` gives the same reach table as before (the arm only moved 4 mm along its own base axis).
- The Reach test scene shares `cartGeoms()` and `XB` with this scene, so it now draws the new cart too. Its own conversion (real roll mechanism, roll sweep, the 40 targets) is part 11. One consequence is already in: the lowest cart height of its table is now **0.635 m** (was 0.63; at 0.63 the new sleeve's lobe touches the lower corner by 0.05 mm); the top stays 1.67 m (the new sleeve is clear up to 1.70 m). The 40 results themselves were not re-run or compared here.

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

## Finding: the sleeves do not fit past the spine and the track bracket (plan section 7, Q6)

Cart at the spine, from `probeCart` (negative = into it):

| Cart centre | Into the spine | Into the track bracket |
|---|---|---|
| within 10 cm of the spine | 7 mm at 9 cm, 17 mm at 8 cm, 27 mm at 7 cm, up to 53 mm at 4 cm to 0 | 10 mm at the spine |
| 10 cm or more away (tray end -0.33 to -0.145 m, store end 0.105 to 0.28 m) | none | none |

Why: how far each part reaches towards the spine from the pipe axis (measured on the model): the riding hand's jaw lobe **45 mm**, the free hand's open jaw **78 mm**, the sleeve ring 34 mm.
The spine surface is 25 mm from the track tube centre in the CAD (growing pipe R37.5 on the spine axis, track 60 mm in front, plan section 7), 21 mm in this scene. The bracket sits on
the spine side too, but the sleeve's gap faces the other hand, not the spine, so it does not pass the bracket either.

The tray (x = -0.335 to -0.145) and the store (x from 0.105) are on opposite sides of the spine, so a real cart could not drive from one to the other. Options for the owner (none built):
1. Move the track plane further in front of the spine: at least 45 mm of sleeve reach plus clearance (about 55 mm from the pipe axis to the spine surface), more if the free jaw opens towards the spine.
   With a 70 mm spine that means the track about 90 mm in front of the spine axis instead of 60 mm.
2. Open the free hand's jaw towards the plate side (-y), not the spine side, so the 78 mm reach goes away, and still do 1.
3. Cut the jaw lobe and the ring at the spine side, or put the bracket on the sleeve's gap side. That changes `hand_sleeve.py` and the free hand's room.
4. Give up working across the middle: separate the tray and the store by hand or with two carts.

The Transplant scene is not affected (it rides a leg: no bracket, no growing-pipe crossing).

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
