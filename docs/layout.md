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
| M8 track rod reach from the pipe surface toward the spine (`track_rod_out_mm`) | 50 mm | `track_joint.py` ROD_OUT; the spine connector (#561) needs 14.5 and its check fails above 50 |
| Bottom track run, axis over the lid top | 210 mm (165 + 45) | derived. Axis at z = 514 mm over the tank floor (the CAD guessed 450, the sim 510) |
| **Central pipe position** (growing pipe 75 mm OD + the 33.7 mm spine on the same axis) | x = 0, y = 0 (tank centre) | **fixed** (#537): no drawing or scene may move it |
| **Track offset** (track pipe axis to central pipe axis) | 66 mm = 16 tube radius + 50 mm rod | the flush track joint, `cad/track_joint.py` `ROD_OUT = 50` (M8 rod from the captive nut in the track pipe, past the lock nut, to the central pipe's axis). The loop plane is y = -66. cad/track_supports.py had a 34 mm free stub, the unit had 60 mm: both disagreed and were changed (#537). ASSUMPTION: "to the spine" is read as to the central pipe's axis |
| Track loop legs / corner radius / top run | x = -/+290, R150, z = 1884 | Viber #97 v2 |
| Cart pipe spacing | 120 mm | `cad/cart_dims.py` |
| **Climbing sleeve** | the TOP sleeve, hand B (pipe B at cart x = -60); the cart body hangs BELOW the track pipe (outside the loop on a leg). The bottom sleeve never climbs | #461 / #537 |

**The check (#537).** `python cad/check_single_source.py` (rule 7) fails if a script or sim scene defines such a number itself, or if the real geometry differs: the central pipe not on (0, 0), the track loop not 66 mm from it, `track_joint.py` / `track_supports.py` / the water station / `complete_unit.py` / `water_assembly.py` / the generated sim numbers / `sim/constants.py` using another value, or the pod-grab scene not taking the layout.

Read by: `cad/layout.py` (`unit_v3_aframe.py`, `unit_v3_dimensioned.py`, `unit_v1_assembly.py`, `track_supports.py`, `complete_unit.py`, `water_station.py`, `water_assembly.py`, the render scripts) and, for the sim, `control-ui/src/layout.ts` (the Pod grab scene, `podgrab/layout.ts`, uses it; the tank height and lid of the Transplant and Reach scenes too). Change a number in the JSON and every drawing, render and GLB follows, and the Pod grab scene.

**Known clash (OpenPocket #376, needs an owner decision).** Every sim scene now reads the bottom run height from the shared layout (514 mm); the old local copy `LOOP_ZB = 0.45` is gone. With the track 64 mm higher, the cart's sleeve lobe (`handC:slC_18`) touches the bottom track corner (`trackc-1-1_6`) 10.77 mm deep at the old lowest cart stop (0.64 m up the leg), so five Transplant/Reach checks fail. They are listed as `KNOWN_CLASH` in `control-ui/test/sim.test.ts` (printed `KNOWN-CLASH`, not hidden, not loosened). Fix options: stop the cart higher (about 0.70 m) and move the seedling tray/arm reach to match; shorten what hangs under the cart so the track can go lower; a smaller sleeve lobe or bigger track corner radius; or cut the ASSUMED 45 mm clearance.

**What moved with the track.** The bottom run went from z 450 to 514 (+64 mm). The water testing station and its socket moved up by the same 64 mm (on longer legs) so the socket is still 7 mm under the track axis, where the arm expects it; the #315 posts under the bottom run are 64 mm taller; the drain tube still ends on the ground.

**The check.** `python cad/water_assembly.py` prints "CART VS TANK (#364)": the lowest cart part, its gap to the lid (45 mm), and a real intersection test of every part within 60 mm of the lid (nozzle, parking block, coil, tail, link) against the tank shell, lid and water at five dock positions along the straight run (x = -140, -70, 0, 100, 140). It stops with an error on any contact, or if the cart is deeper under the track than the layout says. The track curves up at both ends of the run, away from the tank, so the straight run is the worst case.

**Not covered:** the arm in a working pose (reaching down to the tank lid, the sample socket or the seedling tray). The check is for the cart as it travels (arm folded).

## Complete unit: real pod collars, connectors, tray and store (OpenPocket #537 follow-up, 27 Nov 2026)

* **Spine-to-track connector** (task 561, `cad/spine_connector.py`): in the complete unit at the two track runs, x = 0, bottom run 514 mm and top run 1884 mm over the tank floor. The unit's old invented 16 x 30 mm bracket blocks (`spine_brackets`) are not drawn there any more. The rod passes through a drilled hole in the front wall of the central pipe and the spine tube's near wall (the hole size is the joint's `HOLE_D`).
* **No pod place where a connector clamps on.** `connector_keepout_mm` (30, ASSUMED) in `cad/layout.json`: no pod collar may reach closer than that to either connector height. `python cad/complete_unit.py` fails if one does. Before, the generic pod level at z 500 sat on the bottom connector (4 of the 48 places were inside the keep-out).
* **Pod places = the real collar** (`cad/pipe_collar.py`, placed by `cad/parts/pod_collars.py`). It is a clamshell round the whole pipe, 108 mm tall, with ONE pod seat (45 degrees up, drilled 45 mm hole) and one plug holder, so there is one pod place per collar and two collars cannot share a height. The collars face the track (-Y). Also kept clear: the clamp collars of the frame (27 mm) and, above the upper clamp collar, its top triangle legs (65 mm, measured).
* **Real seedling tray and pod store** (`cad/parts/seedling_real.py`): the tray is `cart_arm.py`'s `seed_tray()` (200 x 380 mm, 4 x 4 cells) and the store is the 14 pod rows of `pod_store_reach.py` (pick line, rows shortened round the pipe), both standing on the shelf. The store is moved 4 mm in x and 4 mm in y so it stays inside the tank walls (the study put its edge on the outer wall face).
* **Open question for the owner: how many pod places?** I did not choose a count. Facts: the unit had **48** generic pod places (12 levels of 4, 100 mm pitch), 4 of them on a connector. The real collar allows **one pod per collar** (it wraps the whole pipe, 108 mm tall). Between the lowest hole (400) and the highest (1840), clear of both connectors and both clamp collars, **10 collars fit** (10 pod places); this is what the picture shows, as an upper bound, not a decision. To have more places: collars sharing a height is impossible with this collar, so it would need a shorter collar (e.g. no plug holder) or a longer pipe, or a different layout. Tell me the count and I change one number set in `layout.json`.
* **Open question: the pod store.** `cad/pod_store.py` (concept v1: five 570 mm sticks, 590 x 195 mm) does not fit beside the 200 mm tray in the 692 mm wide tank, so the tank-sized rows of `pod_store_reach.py` (the later version of the same concept) are used. Which one do you want?
* **Not changed:** the dimensioned unit and the water station still draw the stand-in tray and storage from `cad/parts/shelf_items.py`, and the unit drawings other than the complete unit still draw the 16 x 30 mm bracket blocks; the track pipe in the unit is a solid rod, so the connector's nut plate (which belongs inside the real hollow pipe) is not checked against it.
