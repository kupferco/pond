# Pod grab and Transplant seedling on the omni cart (OpenPocket #284, plan task 265 part 10)

Both scenes now carry the real omni cart (rigid plate on two three-lobe sleeves, 38 mm driven omni wheels, ball cups, battery) instead of the hinge-era cart.
Code: `control-ui/src/cart/omni-scene.ts` (the cart as a static body for scenes where it only rides), `src/podgrab/layout.ts` and `task.ts`, `src/transplant/layout.ts`.
Tests: the "Pond #284" blocks in the Pod grab and Transplant parts of `control-ui/test/sim.test.ts`.
Pictures: `cad/renders/podgrab-omni-*` and `cad/renders/transplant-omni-*` (four views each: iso, front, top, side), GLBs `cad/renders/podgrab-assembly.glb`
(also `assembly.glb`) and `cad/renders/transplant-assembly.glb`.

## The answer, in plain words

- **Transplant seedling works on the new cart.** All four steps run, every frame is in reach with at least 5 degrees of joint margin, and nothing touches (arm, cart, track,
  tank, pipe). The cart stops are unchanged (0.64 m at the tray, 1.073 m at the hole, 0.756 m at the plug holder).
- **Pod grab works on the new cart, and the cart can ride the whole bottom run, past the spine (#461).** The sleeves are turned 90 degrees about their pipes (`HAND_TURN` in `podgrab/layout.ts`)
  so the 18 mm slot of each sleeve faces the spine; the spine-to-track bracket (CAD saddle 16 x 10 x 30 mm, 16 mm along the pipe, 10 mm across) passes through the slot. Checked on the CAD
  triangles (`podgrab/clearance.ts`) at every 5 mm from -33 to +28 cm: nothing intersects the spine, the bracket plate, its rod or the pipe, for both hands and the open hand's jaw and motors.
  The spine is the CAD 33.7 mm tube (`cad/parts/unit_dims.py` SP), 60 mm behind the pipe; the sim has no sim-only offsets any more. The hand that hangs open below the pipe has its jaw CLOSED (it takes less room). The pod-grab track is at the shared CAD height; to let the arm (hanging under the pipe on the top sleeve) reach tray rows B to D, `cad/layout.json` `cart_clearance_mm` went from 45 to 110 (smallest tried that works: 45, 65, 85, 105 fail, 110 to 125 pass), so CAD and sim are identical.
  The pod store slope is 7 degrees (`cad/parts/pod_store_dims.py`, was 12): at 12 degrees the back end of the 13-pod channel stood 17 mm through the lid; now the highest point is 6 mm under it. Pod friction in the store is frictionless contact (condim 1) with a little damping, so pods still slide to the pick hole.
  The whole 4 x 4 tray is filled, 16 pods, the arm never touches the spine, the bracket or the pipe.

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
