# One shared layout for the unit (OpenPocket #364)

**Why.** The tank height, the height of the bottom track run and how deep the cart hangs under the track were guessed again in every drawing. In the #330 assembly that put the cart's lowest parts (the blue sample tubing coil, the silicone link and the parking block under the cart) 19 mm *below* the top of the tank lid, so they sat inside the tank.

**Where the numbers live now:** `cad/layout.json`. Nothing else is allowed to define them.

| Number | Value | Source |
|---|---|---|
| Tank height | 300 mm | given (30 cm tank) |
| Lid thickness (top of lid at 304) | 4 mm | given |
| Normal water level over the tank floor | 150 mm | owner (about 15 cm) |
| Cart depth under the track axis, towards the tank | 165 mm | **measured** from the CAD (the parking block under the plate; `water_assembly.cart_tank_check()` recomputes it and fails if the real cart is deeper) |
| Air between the lowest cart part and the lid | 45 mm | **ASSUMED**, not given by the owner |
| Bottom track run, axis over the lid top | 210 mm (165 + 45) | derived. Axis at z = 514 mm over the tank floor (the CAD guessed 450, the sim 510) |

Read by: `cad/layout.py` (`unit_v3_aframe.py`, `unit_v3_dimensioned.py`, `unit_v1_assembly.py`, `track_supports.py`, `complete_unit.py`, `water_station.py`, `water_assembly.py`, the render scripts) and, for the sim, `control-ui/src/layout.ts` (the Pod grab scene, `podgrab/layout.ts`, uses it; the tank height and lid of the Transplant and Reach scenes too). Change a number in the JSON and every drawing, render and GLB follows, and the Pod grab scene.

**Exception, needs an owner decision.** The Transplant and Reach sim scenes still have their bottom run at 450 mm (`transplant/layout.ts`, `SCENE_TRACK_BOTTOM_STILL_OLD_MM`). They are tuned to it: the cart can ride down the leg only to 0.64 m, and the seedling tray inside the tank is reached from there. With the bottom run at 514 the corner starts 64 mm higher, the lowest stop becomes about 0.70 m, and the arm would have to reach 64 mm further down through the lid hole to a tray that cannot move up (the lid is at 304). Raising the track so the cart clears the lid in the *assembly* therefore costs reach to the tray in the *sim*. Options: lower the tray rail/move the tray, shorten what hangs under the cart, or let the cart ride a rolled pose there. Not decided here.

**What moved with the track.** The bottom run went from z 450 to 514 (+64 mm). The water testing station and its socket moved up by the same 64 mm (on longer legs) so the socket is still 7 mm under the track axis, where the arm expects it; the #315 posts under the bottom run are 64 mm taller; the drain tube still ends on the ground.

**The check.** `python cad/water_assembly.py` prints "CART VS TANK (#364)": the lowest cart part, its gap to the lid (45 mm), and a real intersection test of every part within 60 mm of the lid (nozzle, parking block, coil, tail, link) against the tank shell, lid and water at five dock positions along the straight run (x = -140, -70, 0, 100, 140). It stops with an error on any contact, or if the cart is deeper under the track than the layout says. The track curves up at both ends of the run, away from the tank, so the straight run is the worst case.

**Not covered:** the arm in a working pose (reaching down to the tank lid, the sample socket or the seedling tray). The check is for the cart as it travels (arm folded).
