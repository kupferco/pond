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
